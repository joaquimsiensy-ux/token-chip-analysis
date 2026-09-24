#!/usr/bin/env python3
"""Batch 8 scale regressions: key-neutral resume, pool failover and streaming."""

from __future__ import annotations

import hashlib
import inspect
import json
import sys
import tempfile
import threading
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.solana import sqd_gap_repair as repair  # noqa: E402
import test_sqd_gap_repair as legacy  # noqa: E402


MINT = legacy.MINT
ZERO = legacy.ZERO


class SimulatedLiveState:
    """Thread-safe, deliberately out-of-order transport state."""

    def __init__(self, slots, transactions, *, quota=None, disorder=False):
        self.transactions = dict(zip(slots, transactions))
        self.quota = quota or (lambda _endpoint, _slot: False)
        self.disorder = disorder
        self.lock = threading.Lock()
        self.calls = []
        self.active = 0
        self.max_active = 0

    def call(self, endpoint, kind, body):
        slot = (body["params"][0] if kind == "reference-getBlock"
                else body["fromBlock"])
        with self.lock:
            self.calls.append((kind, slot, endpoint))
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if self.disorder and kind == "reference-getBlock":
                time.sleep((7 - slot % 7) * 0.001)
            if kind == "reference-getBlock" and self.quota(endpoint, slot):
                return repair.net.Result(ok=False, error={
                    "category": "quota", "message": "payment required",
                    "http_status": 402, "retryable": False})
            if kind == "sqd-probe":
                return repair.net.Result(ok=True, value=[{
                    "header": {"number": slot}, "instructions": []}])
            present_signature = f"PresentSignature{slot}"
            if kind == "sqd-census":
                return repair.net.Result(ok=True, value=[{
                    "header": {"number": slot, "hash": f"blockhash-{slot}",
                               "parentSlot": slot - 1},
                    "instructions": [],
                    "transactions": [{"transactionIndex": 0,
                                      "signatures": [present_signature],
                                      "err": None}],
                }])
            present_tx = {
                "transaction": {"signatures": [present_signature],
                                "message": {"accountKeys": ["PresentAccount"],
                                            "instructions": []}},
                "meta": {"err": None, "loadedAddresses": {},
                         "preTokenBalances": [], "postTokenBalances": []},
            }
            block = {
                "blockhash": f"blockhash-{slot}", "parentSlot": slot - 1,
                "blockTime": 1_700_000_000 + slot,
                "transactions": [present_tx, self.transactions[slot]],
            }
            return repair.net.Result(ok=True, value={
                "jsonrpc": "2.0", "id": slot, "result": block})
        finally:
            with self.lock:
                self.active -= 1


class SimulatedLiveTransport:
    def __init__(self, endpoint, state):
        self.endpoint = endpoint
        self.state = state

    def call(self, kind, body):
        return self.state.call(self.endpoint, kind, body)


@contextmanager
def simulated_live(state):
    original = repair.RepairLiveTransport
    repair.RepairLiveTransport = lambda endpoint: SimulatedLiveTransport(
        endpoint, state)
    try:
        yield
    finally:
        repair.RepairLiveTransport = original


def endpoint(key):
    return f"https://mainnet.helius-rpc.com/?api-key={key}"


def plan_for(fingerprint):
    plan = {
        "base": {"edge_sha256": "a" * 64, "meta_sha256": "b" * 64},
        "coverage": {"probe_id": "probe", "map_sha256": "c" * 64},
        "candidate_slots": [1, 2],
        "mode": "formal",
        "reference": {"kind": "helius-getBlock", "source": "live",
                      "endpoint_fingerprint": fingerprint},
        "producer": {"sha256": "d" * 64},
    }
    plan["plan_digest"] = repair.compute_plan_digest(plan)
    return plan


def test_key_neutral_identity():
    key_a = "KEY_A_MUST_NOT_ENTER_IDENTITY"
    key_b = "KEY_B_MUST_NOT_ENTER_IDENTITY"
    identity_a = repair.reference_endpoint_identity(endpoint(key_a))
    identity_b = repair.reference_endpoint_identity(endpoint(key_b))
    assert identity_a == identity_b
    assert key_a not in identity_a["fingerprint_input"]
    assert key_b not in identity_b["fingerprint_input"]
    assert plan_for(identity_a["sha256"])["plan_digest"] == plan_for(
        identity_b["sha256"])["plan_digest"]
    custom_a = repair.reference_endpoint_identity(
        "https://user:secret@rpc.example/v1/token-a?q=one#frag")
    custom_b = repair.reference_endpoint_identity(
        "https://rpc.example/v1/token-b?q=two")
    assert custom_a == custom_b
    fixture = repair.reference_endpoint_identity("fixture://helius?key=a")
    assert fixture == repair.reference_endpoint_identity("fixture://helius?key=b")


def test_key_file_precedence():
    with tempfile.TemporaryDirectory(prefix="batch8-keys-", dir="/private/tmp") as td:
        root = Path(td)
        cli = root / "cli"
        default = root / "default"
        single = root / "single"
        cli.write_text("cli-a\n\n cli-b \n", encoding="utf-8")
        default.write_text("default-a\n", encoding="utf-8")
        single.write_text("single-a\n", encoding="utf-8")
        assert repair.load_reference_endpoints(
            reference_keys_file=cli, keys_file=default, key_file=single) == [
                endpoint("cli-a"), endpoint("cli-b")]
        assert repair.load_reference_endpoints(
            keys_file=default, key_file=single) == [endpoint("default-a")]
        default.write_text("\n \n", encoding="utf-8")
        assert repair.load_reference_endpoints(
            keys_file=default, key_file=single) == [endpoint("single-a")]
        assert repair.load_reference_endpoints(
            reference_rpc="fixture://custom", reference_keys_file=cli,
            keys_file=default, key_file=single) == ["fixture://custom"]
    parsed = repair.build_parser().parse_args([
        "plan", "--mint", MINT, "--case-root", "/private/tmp",
        "--reference-rpc", "fixture://custom"])
    assert parsed.workers == 1


def direct_stream(root, slots, state, endpoints, *, workers=1):
    pending = Path(root) / "pending"
    pending.mkdir()
    fingerprint = repair.reference_endpoint_identity(endpoints[0])["sha256"]
    plan = {"plan_digest": "a" * 64,
            "reference": {"kind": "helius-getBlock",
                          "endpoint_fingerprint": fingerprint}}
    args = SimpleNamespace(
        transport_fixture=None, mint=MINT, workers=workers)
    with simulated_live(state):
        stream = repair._live_payloads(
            args, slots, endpoints, fingerprint, pending=pending, plan=plan,
            coverage_states={slot: "DEFECT_CANDIDATE" for slot in slots},
            beta_slots=set())
        assert inspect.isgenerator(stream)
        payloads = list(stream)
    return pending, plan, payloads


def test_concurrent_order_and_hot_failover(transactions):
    slots = list(range(10_000, 10_020))
    with tempfile.TemporaryDirectory(prefix="batch8-concurrent-",
                                     dir="/private/tmp") as td:
        state = SimulatedLiveState(slots, transactions, disorder=True)
        pending, plan, payloads = direct_stream(
            td, slots, state, [endpoint("key-a"), endpoint("key-b")], workers=4)
        assert [row["slot"] for row in payloads] == slots
        rows = [json.loads(line) for line in
                (pending / "rpc_ledger.jsonl").read_text().splitlines()]
        assert [row["seq"] for row in rows[1:]] == list(range(len(slots)))
        assert [row["slot"] for row in rows[1:]] == slots
        assert len(list((pending / "evidence").glob("*.json"))) == 2 * len(slots)
        completed, _ledger = repair.load_resume_slots(
            pending, repair._ledger_header(plan))
        assert completed == set(slots)
        assert state.max_active > 1
        reference_counts = Counter(
            item[2] for item in state.calls if item[0] == "reference-getBlock")
        assert reference_counts == Counter({endpoint("key-a"): 10,
                                            endpoint("key-b"): 10})

    with tempfile.TemporaryDirectory(prefix="batch8-failover-",
                                     dir="/private/tmp") as td:
        bad = endpoint("quota-key")
        good = endpoint("good-key")
        state = SimulatedLiveState(
            slots, transactions,
            quota=lambda candidate, _slot: candidate == bad)
        pending, _plan_value, payloads = direct_stream(
            td, slots, state, [bad, good], workers=1)
        assert [row["slot"] for row in payloads] == slots
        ledger = [json.loads(line) for line in
                  (pending / "rpc_ledger.jsonl").read_text().splitlines()[1:]]
        assert ledger[0]["attempt"] == 2
        assert all(row["attempt"] >= 1 for row in ledger)
        reference_endpoints = [item[2] for item in state.calls
                               if item[0] == "reference-getBlock"]
        assert reference_endpoints.count(bad) == 1
        assert reference_endpoints.count(good) == len(slots)


def build_case(root, slots):
    return legacy.build_batch3b_case(root, set(slots), [
        [1_700_000_000 + i, slot, 0, -1, ZERO, f"Base{i}", 1]
        for i, slot in enumerate(slots)])


def test_all_quota_receipt_and_cross_key_resume(transactions):
    slots = list(range(10_000, 10_020))
    key_hash = hashlib.sha256(MINT.encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="batch8-quota-", dir="/private/tmp") as td:
        root = Path(td)
        case = build_case(root / "all-quota", slots)
        keys = root / "quota.keys"
        keys.write_text("quota-a\nquota-b\n", encoding="utf-8")
        state = SimulatedLiveState(
            slots, transactions, quota=lambda _endpoint, _slot: True)
        with simulated_live(state):
            rc = repair.main([
                "repair", "--mint", MINT, "--case-root", str(case),
                "--reference-keys-file", str(keys)])
        assert rc == 3
        parent = case / f"data/sqd_repair/{key_hash}"
        pending = next(parent.glob("pending-*"))
        stopped = json.loads((pending / "STOPPED.json").read_text())
        assert stopped["cursor"] == slots[0]
        assert stopped["completed_slots"] == []

        case = build_case(root / "resume", slots)
        first_keys = root / "first.keys"
        second_keys = root / "second.keys"
        first_keys.write_text("first-key\n", encoding="utf-8")
        second_keys.write_text("second-key\n", encoding="utf-8")
        split = slots[len(slots) // 2]
        first = SimulatedLiveState(
            slots, transactions,
            quota=lambda _endpoint, slot: slot >= split)
        with simulated_live(first):
            assert repair.main([
                "repair", "--mint", MINT, "--case-root", str(case),
                "--reference-keys-file", str(first_keys)]) == 3
        parent = case / f"data/sqd_repair/{key_hash}"
        pending_before = next(parent.glob("pending-*"))
        first_reference_slots = [slot for kind, slot, _endpoint in first.calls
                                 if kind == "reference-getBlock" and slot < split]
        assert first_reference_slots == slots[:len(slots) // 2]

        second = SimulatedLiveState(slots, transactions)
        with simulated_live(second):
            assert repair.main([
                "repair", "--mint", MINT, "--case-root", str(case),
                "--reference-keys-file", str(second_keys), "--resume"]) == 0
        second_reference_slots = [slot for kind, slot, _endpoint in second.calls
                                  if kind == "reference-getBlock"]
        assert second_reference_slots == slots[len(slots) // 2:]
        assert not pending_before.exists()
        assert (parent / "CURRENT.json").is_file()


def test_streaming_structure():
    assert inspect.isgeneratorfunction(repair._live_payloads)
    source = inspect.getsource(repair._live_payloads)
    assert "payloads = []" not in source
    produce_source = inspect.getsource(repair._produce_blocks)
    assert "payloads, rpc_rows = _live_payloads" not in produce_source


def test_sqd_retry_schedule():
    class FlakySQD:
        def __init__(self):
            self.calls = 0

        def call(self, _kind, _body):
            self.calls += 1
            if self.calls <= 3:
                return repair.net.Result(ok=False, error={
                    "category": "http_status", "message": "overloaded",
                    "http_status": 529, "retryable": True})
            return repair.net.Result(ok=True, value=[])

    for kind, body, failure in (
            ("sqd-probe", repair.sqd_query_body(1, 1), "SQD coverage-state recheck failed"),
            ("sqd-census", repair._census_body(1), "SQD census failed")):
        transport = FlakySQD()
        delays = []
        with patch.object(repair.time, "sleep", delays.append):
            assert repair._sqd_call_with_backoff(transport, kind, body, 1, failure) == []
        assert transport.calls == 4
        assert delays == [2, 4, 8]


def test_w4_fault_order_and_prefix():
    """A failing SQD census wins over quota; successful census reaches STOPPED."""
    slots = [19_998, 19_999]
    transactions = [legacy.w4_missing_transaction(slot) for slot in slots]

    class FaultState(SimulatedLiveState):
        def call(self, endpoint, kind, body):
            result = super().call(endpoint, kind, body)
            if kind == "sqd-census" and body["fromBlock"] == slots[1]:
                if fault == "sqd-exhausted":
                    return repair.net.Result(ok=False, error={
                        "category": "http_status", "message": "overloaded",
                        "http_status": 529, "retryable": True})
                if fault == "duplicate":
                    return repair.net.Result(ok=True, value=result.value * 2)
            return result

    for fault in ("sqd-exhausted", "duplicate", "helius-quota"):
        with tempfile.TemporaryDirectory(prefix="w4-fault-") as td:
            root = Path(td).resolve()
            case = build_case(root, slots)
            state = FaultState(slots, transactions, quota=lambda _ep, slot: slot == slots[1])
            delays = []
            args = ["repair", "--mint", MINT, "--case-root", str(case),
                    "--reference-rpc", endpoint("w4-fixture-key")]
            with simulated_live(state), patch.object(repair.time, "sleep", delays.append):
                rc = repair.main(args)
            parent, current, _ = repair.sqd_repair_paths(case, MINT)
            pending = next(parent.glob("pending-*"))
            rows = repair._parse_ledger_prefix((pending / "rpc_ledger.jsonl").read_bytes())
            assert [row["slot"] for row in rows[1:]] == slots[:1]
            assert not current.exists()
            assert not (pending / f"evidence/{slots[1]}.sqd.json").exists()
            assert not (pending / f"evidence/{slots[1]}.ref.json").exists()
            calls = [(kind, slot) for kind, slot, _ in state.calls]
            attempts = 4 if fault == "sqd-exhausted" else 1
            expected = [("sqd-census", slots[0]), ("reference-getBlock", slots[0])]
            expected += [("sqd-census", slots[1])] * attempts
            if fault == "helius-quota":
                expected.append(("reference-getBlock", slots[1]))
                assert rc == 3
                stopped = json.loads((pending / "STOPPED.json").read_text())
                assert stopped["cursor"] == slots[1]
                assert stopped["completed_slots"] == slots[:1]
                before = {p.name: p.read_bytes() for p in (pending / "evidence").glob("*.json")}
                resumed = SimulatedLiveState(slots, transactions)
                with simulated_live(resumed):
                    assert repair.main(args + ["--resume"]) == 0
                assert [(kind, slot) for kind, slot, _ in resumed.calls] == [
                    ("sqd-census", slots[1]), ("reference-getBlock", slots[1])]
                gen = parent / f"gen-{json.loads(current.read_text())['gid']}"
                for name, content in before.items():
                    assert (gen / "evidence" / name).read_bytes() == content
            else:
                assert rc == 2
                assert not (pending / "STOPPED.json").exists()
            assert calls == expected
            assert delays == ([2, 4, 8] if fault == "sqd-exhausted" else [])
    print("PASS W4 SQD failure precedes quota; rc=2/3; STOPPED/success prefix/resume")


def test_w4_self_contained_scale():
    transactions = [legacy.w4_missing_transaction(slot) for slot in range(10_000, 10_020)]
    test_concurrent_order_and_hot_failover(transactions)
    test_all_quota_receipt_and_cross_key_resume(transactions)
    print("PASS W4 self-contained concurrent order/hot failover/all-quota/cross-key resume")


def main():
    test_w4_fault_order_and_prefix()
    test_w4_self_contained_scale()
    test_key_neutral_identity()
    test_key_file_precedence()
    transactions = legacy.staged_missing_transactions(20)
    test_concurrent_order_and_hot_failover(transactions)
    test_all_quota_receipt_and_cross_key_resume(transactions)
    test_streaming_structure()
    test_sqd_retry_schedule()
    print("PASS batch8: key-neutral identity/pool failover/ordered workers/resume/streaming")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
