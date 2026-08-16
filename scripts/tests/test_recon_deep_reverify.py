#!/usr/bin/env python3
"""F-07 deep re-verification regressions for all reconciliation sub-receipts."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts" / "lib"), str(ROOT / "scripts" / "report")]

from receipt_kernel import build_envelope, finalize_envelope
import net
import shared_release_receipt as shared


TARGET = {
    "chain": "eth",
    "token": "0x1111111111111111111111111111111111111111",
    "as_of_block": 123,
}
HOLDERS = [f"0x{value:040x}" for value in (2, 3, 4)]
BALANCES = {HOLDERS[0]: 60, HOLDERS[1]: 30, HOLDERS[2]: 10}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(path: Path, root: Path) -> dict:
    return {"path": path.relative_to(root).as_posix(), "size": path.stat().st_size,
            "sha256": _sha(path)}


def _item(path: Path, root: Path) -> dict:
    return {"receipt": _ref(path, root), "status": "PASS", "exit_code": 0}


def _expect_error(fn, needle: str = "") -> None:
    try:
        fn()
    except ValueError as exc:
        if needle and needle not in str(exc):
            raise AssertionError(f"expected {needle!r}, got {exc!r}") from exc
        return
    raise AssertionError("tampered receipt unexpectedly passed deep validation")


def _mutate_receipt(root: Path, original: dict, name: str, mutate) -> dict:
    changed = copy.deepcopy(original)
    mutate(changed)
    path = _write_json(root / name, changed)
    return _item(path, root)


class _ReconPool:
    def attest(self):
        return 1

    def call(self, method, params):
        assert method == "eth_call"
        address = "0x" + params[0]["data"][-40:]
        return {"ok": True, "result": hex(BALANCES[address])}


def _produce_recon(root: Path):
    producer = _load(ROOT / "scripts" / "evm" / "verify_recon.py", "f07_verify")
    config = _write_json(root / "config.json", {
        "token": TARGET["token"], "decimals": 0, "total_supply_human": "100",
        "alchemy": {"url": "http://offline/", "key": "fixture"},
    })
    balances = _write_json(root / "balances.json", {k: str(v) for k, v in BALANCES.items()})
    stats = _write_json(root / "replay_stats.json", {
        "max_block": 123, "mint_total_raw": "100", "burn_total_raw": "0",
    })
    gmgn = root / "gmgn.csv"
    gmgn.write_text(
        "address,pct\n" + "\n".join(
            f"{address},{DecimalValue}" for address, DecimalValue in
            ((HOLDERS[0], "0.6"), (HOLDERS[1], "0.3"), (HOLDERS[2], "0.1"))) + "\n",
        encoding="utf-8")
    out = root / "verify_recon.json"
    args = ["--config", str(config), "--balances", str(balances),
            "--replay-stats", str(stats), "--gmgn", str(gmgn), "--chain", "eth",
            "--token", TARGET["token"], "--end-block", "123", "--top-n", "3",
            "--rpc", "http://offline/", "--out", str(out)]
    with mock.patch.object(producer, "attested_rpc_pool", return_value=_ReconPool()):
        assert producer.main(args) == 0
    receipt = json.loads(out.read_text(encoding="utf-8"))
    shared.validate_reconciliation_check(root, "balance", _item(out, root), TARGET, "evm")
    shared.validate_reconciliation_check(root, "supply", _item(out, root), TARGET, "evm")
    return out, receipt


def _test_recon_mutations(root: Path, out: Path, receipt: dict) -> None:
    validate_supply = lambda item: shared.validate_reconciliation_check(
        root, "supply", item, TARGET, "evm")
    validate_balance = lambda item: shared.validate_reconciliation_check(
        root, "balance", item, TARGET, "evm")

    bad_balances = _write_json(root / "balances_bad.json", {
        HOLDERS[0]: "50", HOLDERS[1]: "30", HOLDERS[2]: "10",
    })
    supply_item = _mutate_receipt(
        root, receipt, "bad_supply.json",
        lambda value: value["inputs"].__setitem__("balances", _ref(bad_balances, root)))
    _expect_error(lambda: validate_supply(supply_item), "balance_sum_raw")

    mutations = [
        ("missing_row.json", lambda v: v["observations"]["balance_reconciliation"]["rows"].pop(),
         "address sequence"),
        ("bad_replay.json", lambda v: v["observations"]["balance_reconciliation"]["rows"][0].__setitem__("replay_raw", "59"),
         "replay_raw"),
        ("bad_matched.json", lambda v: v["observations"]["balance_reconciliation"].__setitem__("matched", 99),
         "matched"),
        ("missing_top_n.json", lambda v: v["observations"]["balance_reconciliation"].pop("requested_top_n"),
         "requested_top_n"),
        ("bad_order.json", lambda v: v["observations"]["balance_reconciliation"]["rows"].reverse(),
         "address sequence"),
        ("bad_gmgn_count.json", lambda v: v["observations"]["gmgn_comparison"].__setitem__("diff_count", 1),
         "diff_count"),
        ("missing_transcript.json", lambda v: v["inputs"].pop("transcript"),
         "transcript"),
        ("old_schema.json", lambda v: v.__setitem__("schema", "evm-reconciliation-receipt/v2"),
         "verify_recon v3"),
    ]
    for name, mutate, needle in mutations:
        _expect_error(lambda item=_mutate_receipt(root, receipt, name, mutate):
                      validate_balance(item), needle)

    transcript_path = root / receipt["inputs"]["transcript"]["path"]
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    transcript[0]["result"] = hex(59)
    bad_transcript = _write_json(root / "bad_transcript.json", transcript)
    transcript_item = _mutate_receipt(
        root, receipt, "bad_transcript_receipt.json",
        lambda value: value["inputs"].__setitem__("transcript", _ref(bad_transcript, root)))
    _expect_error(lambda: validate_balance(transcript_item), "chain_raw")


def _plan_fixture(root: Path):
    raw_input = root / "merged.csv"
    raw_input.write_text("block,tx,from,to,value\n", encoding="utf-8")
    identity = {"kind": "file", "path": str(raw_input.resolve()),
                "size": raw_input.stat().st_size, "sha256": _sha(raw_input)}
    manifest = _write_json(root / "anchor_plan.input.json", {
        "schema": "anchor-plan-input/v1", "input": identity, "files": [identity],
    })
    plan_envelope = build_envelope(
        "anchor-plan-receipt/v2", TARGET, ROOT / "scripts" / "lib" / "anchor_plan.py",
        "formal", inputs={"input_manifest": manifest})
    plan = {
        "schema": "anchor-plan/v2", "generated_at": "2026-08-15T00:00:00Z",
        "target": TARGET, "input": identity, "chain": "eth", "token": TARGET["token"],
        "final_block": 123, "producer": plan_envelope["producer"],
        "input_manifest": plan_envelope["inputs"]["input_manifest"],
        "matrix_points": [{"kind": "matrix", "addr": HOLDERS[0],
                           "day_end_block": 100, "expected_balance_raw": "60"}],
        "forced_points": [{"kind": "largest_tx", "tx": "0xabc", "from": HOLDERS[1],
                           "to": HOLDERS[2], "block": 110, "expected_value_raw": "7"}],
    }
    plan_path = _write_json(root / "anchor_plan.json", plan)
    plan_receipt = finalize_envelope(
        plan_envelope, "PASS", 0, plan_schema="anchor-plan/v2",
        generated_at=plan["generated_at"], input_identity=identity, probe_count=2,
        output={"path": str(plan_path.resolve()), "size": plan_path.stat().st_size,
                "sha256": _sha(plan_path)})
    plan_receipt_path = _write_json(root / "anchor_plan.receipt.json", plan_receipt)
    return raw_input, plan_path, plan_receipt_path


class _TimePool:
    def call_many(self, calls):
        assert len(calls) == 2
        log = {"address": TARGET["token"],
               "topics": [
                   "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                   "0x" + "0" * 24 + HOLDERS[1][2:],
                   "0x" + "0" * 24 + HOLDERS[2][2:]],
               "data": hex(7)}
        return [{"ok": True, "result": hex(60)},
                {"ok": True, "result": {"blockNumber": hex(110), "logs": [log]}}]


def _produce_time(root: Path):
    producer = _load(ROOT / "scripts" / "lib" / "time_spotcheck.py", "f07_time")
    raw_input, plan, plan_receipt = _plan_fixture(root)
    out = root / "time_spotcheck.json"
    argv = ["time_spotcheck.py", "--plan", str(plan), "--plan-receipt", str(plan_receipt),
            "--input", str(raw_input), "--chain", "eth", "--token", TARGET["token"],
            "--rpc", "http://offline/", "--out", str(out), "--final-block", "123"]
    with mock.patch.object(producer, "validate_semantic_replay", return_value=None), \
            mock.patch.object(net, "attested_rpc_pool", return_value=_TimePool()), \
            mock.patch.object(sys, "argv", argv):
        assert producer.main() == 0
    receipt = json.loads(out.read_text(encoding="utf-8"))
    shared.validate_reconciliation_check(root, "time", _item(out, root), TARGET, "evm")
    return out, receipt


def _time_authority_variant(root: Path, receipt: dict, name: str, *,
                            mutate_plan=None, mutate_plan_receipt=None,
                            bind_output=True, one_point=False, mutate_time=None) -> dict:
    """Build one H-vector while keeping every unrelated binding internally valid."""
    plan_source = root / receipt["inputs"]["plan"]["path"]
    plan_receipt_source = root / receipt["inputs"]["plan_receipt"]["path"]
    transcript_source = root / receipt["inputs"]["transcript"]["path"]
    plan = json.loads(plan_source.read_text(encoding="utf-8"))
    plan_receipt = json.loads(plan_receipt_source.read_text(encoding="utf-8"))
    changed = copy.deepcopy(receipt)

    if mutate_plan:
        mutate_plan(plan)
    plan_path = _write_json(root / f"{name}_plan.json", plan)
    if bind_output:
        plan_receipt["output"] = _ref(plan_path, root)
    if mutate_plan_receipt:
        mutate_plan_receipt(plan_receipt)
    plan_receipt_path = _write_json(root / f"{name}_plan_receipt.json", plan_receipt)
    changed["inputs"]["plan"] = _ref(plan_path, root)
    changed["inputs"]["plan_receipt"] = _ref(plan_receipt_path, root)

    if one_point:
        changed["rows"] = changed["rows"][:1]
        changed.update({
            "points": 1, "balance_points": 1, "tx_points": 0,
            "exact_match": 1, "mismatch": 0, "rpc_err": 0,
        })
        transcript = json.loads(transcript_source.read_text(encoding="utf-8"))[:1]
        transcript_path = _write_json(root / f"{name}_transcript.json", transcript)
        changed["inputs"]["transcript"] = _ref(transcript_path, root)
    if mutate_time:
        mutate_time(changed)
    path = _write_json(root / f"{name}_time_receipt.json", changed)
    return _item(path, root)


def _test_time_authority_vectors(root: Path, receipt: dict) -> None:
    """H1-H6/H10 authority-chain attacks and H40 bool counters must fail closed."""
    validate = lambda item: shared.validate_reconciliation_check(
        root, "time", item, TARGET, "evm")

    def one_point(plan):
        plan["forced_points"] = []

    other_plan = copy.deepcopy(json.loads(
        (root / receipt["inputs"]["plan"]["path"]).read_text(encoding="utf-8")))
    other_plan["forced_points"] = []
    other_plan_path = _write_json(root / "h3_other_plan.json", other_plan)

    other_input = root / "h6_same_bytes_other_input.csv"
    original_input = root / receipt["inputs"]["input"]["path"]
    other_input.write_bytes(original_input.read_bytes())
    other_identity = {
        "kind": "file", "path": str(other_input.resolve()),
        "size": other_input.stat().st_size, "sha256": _sha(other_input),
    }

    fake_producer = {
        "path": "scripts/lib/time_spotcheck.py",
        "sha256": _sha(ROOT / "scripts" / "lib" / "time_spotcheck.py"),
    }
    wrong_target = {
        "chain": "bsc", "token": "0x" + "f" * 40, "as_of_block": 999,
    }
    vectors = [
        ("H1 self-written one-point plan with another signed receipt",
         _time_authority_variant(root, receipt, "h1", mutate_plan=one_point,
                                 bind_output=False, one_point=True)),
        ("H2 probe_count differs from the one-point plan",
         _time_authority_variant(root, receipt, "h2", mutate_plan=one_point,
                                 one_point=True)),
        ("H3 receipt output binds a different plan",
         _time_authority_variant(
             root, receipt, "h3",
             mutate_plan_receipt=lambda value: value.__setitem__(
                 "output", _ref(other_plan_path, root)))),
        ("H4 plan schema is not anchor-plan/v2",
         _time_authority_variant(
             root, receipt, "h4",
             mutate_plan=lambda value: value.__setitem__("schema", "attacker-freestyle/v9"))),
        ("H5 plan target differs from the signed receipt target",
         _time_authority_variant(
             root, receipt, "h5",
             mutate_plan=lambda value: value.__setitem__("target", wrong_target))),
        ("H6 plan identity is rebound to a different same-content input",
         _time_authority_variant(
             root, receipt, "h6",
             mutate_plan=lambda value: value.__setitem__("input", other_identity),
             mutate_plan_receipt=lambda value: value.__setitem__(
                 "input_identity", other_identity))),
        ("H10 unrelated repository script impersonates the plan producer",
         _time_authority_variant(
             root, receipt, "h10",
             mutate_plan=lambda value: value.__setitem__("producer", fake_producer),
             mutate_plan_receipt=lambda value: value.__setitem__(
                 "producer", fake_producer))),
    ]

    accepted = []
    for label, item in vectors:
        try:
            validate(item)
        except ValueError as exc:
            if "time plan authority chain broken" not in str(exc):
                raise AssertionError(
                    f"{label}: expected authority-chain rejection, got {exc!r}") from exc
        else:
            accepted.append(label)

    bool_fields = ("points", "balance_points", "tx_points",
                   "exact_match", "mismatch", "rpc_err")
    for field in bool_fields:
        bool_item = _time_authority_variant(
            root, receipt, f"h40_{field}", mutate_plan=one_point,
            mutate_plan_receipt=lambda value: value.__setitem__("probe_count", 1),
            one_point=True,
            mutate_time=lambda value, field=field: value.__setitem__(
                field, bool(value[field])))
        try:
            validate(bool_item)
        except ValueError as exc:
            if "boolean" not in str(exc):
                raise AssertionError(
                    f"H40 {field}: expected boolean rejection, got {exc!r}") from exc
        else:
            accepted.append(f"H40 boolean counter {field}")

    if accepted:
        raise AssertionError("authority mutation unexpectedly passed: " + "; ".join(accepted))


def _test_time_mutations(root: Path, receipt: dict) -> None:
    validate = lambda item: shared.validate_reconciliation_check(
        root, "time", item, TARGET, "evm")
    mutations = [
        ("time_bad_plan_row.json", lambda v: v["rows"][0].__setitem__("addr", HOLDERS[1]),
         "one-to-one"),
        ("time_bad_from.json", lambda v: v["rows"][1].__setitem__("from", HOLDERS[0]),
         "one-to-one"),
        ("time_bad_count.json", lambda v: v.__setitem__("exact_match", 99), "counters"),
        ("time_no_plan_receipt.json", lambda v: v["inputs"].pop("plan_receipt"),
         "plan receipt"),
        ("time_old_schema.json", lambda v: v.__setitem__("schema", "time-spotcheck/v2"),
         "time_spotcheck v3"),
    ]
    for name, mutate, needle in mutations:
        _expect_error(lambda item=_mutate_receipt(root, receipt, name, mutate):
                      validate(item), needle)


def _anchor_fixture(root: Path):
    target = {"chain": "solana", "token": "mintfixture", "as_of_block": 500}
    config = _write_json(root / "sol_config.json", {"mint": "mintfixture"})
    output = root / "anchors.jsonl"
    rows = [
        {"date": day, "chain": "solana", "mint": "mintfixture",
         "endpoint": "https://portal.sqd.dev", "as_of_slot": 500,
         "from_slot": 10 + index, "to_slot": 20 + index, "n_rows": 1, "accounts": {}}
        for index, day in enumerate(("2026-08-14", "2026-08-15"))
    ]
    output.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    envelope = build_envelope(
        "solana-anchor-sampler-receipt/v2", target,
        ROOT / "scripts" / "solana" / "anchor_sampler.py", "formal",
        inputs={"config": config}, input_base=root)
    receipt = finalize_envelope(
        envelope, "PASS", 0, date_range={"start": "2026-08-14", "end": "2026-08-15"},
        output=_ref(output, root),
        coverage={"requested_days": 2, "covered_days": 2, "failed_days": 0}, failures=[])
    path = _write_json(root / "anchor_receipt.json", receipt)
    item = _item(path, root)
    shared.validate_reconciliation_check(root, "balance", item, target, "solana")
    return target, receipt


def _test_anchor_mutations(root: Path, target: dict, receipt: dict) -> None:
    validate = lambda item: shared.validate_reconciliation_check(
        root, "balance", item, target, "solana")
    source = root / receipt["output"]["path"]
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    short = root / "anchors_short.jsonl"
    short.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    short_item = _mutate_receipt(
        root, receipt, "anchor_short_receipt.json",
        lambda value: value.__setitem__("output", _ref(short, root)))
    _expect_error(lambda: validate(short_item), "row count")
    duplicate = root / "anchors_duplicate.jsonl"
    duplicate.write_text(json.dumps(rows[0]) + "\n" + json.dumps(rows[0]) + "\n",
                         encoding="utf-8")
    duplicate_item = _mutate_receipt(
        root, receipt, "anchor_duplicate_receipt.json",
        lambda value: value.__setitem__("output", _ref(duplicate, root)))
    _expect_error(lambda: validate(duplicate_item), "duplicate dates")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="f07-deep-reverify-") as raw:
        root = Path(raw).resolve()
        recon_dir = root / "recon"; recon_dir.mkdir()
        recon_out, recon_receipt = _produce_recon(recon_dir)
        _test_recon_mutations(recon_dir, recon_out, recon_receipt)
        time_dir = root / "time"; time_dir.mkdir()
        _, time_receipt = _produce_time(time_dir)
        _test_time_authority_vectors(time_dir, time_receipt)
        _test_time_mutations(time_dir, time_receipt)
        anchor_dir = root / "anchor"; anchor_dir.mkdir()
        anchor_target, anchor_receipt = _anchor_fixture(anchor_dir)
        _test_anchor_mutations(anchor_dir, anchor_target, anchor_receipt)
    print("PASS test_recon_deep_reverify")


if __name__ == "__main__":
    main()
