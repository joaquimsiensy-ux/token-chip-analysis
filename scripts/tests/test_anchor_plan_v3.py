#!/usr/bin/env python3
"""U1 anchor-plan/v3 machine-contract and producer-history regressions."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LIB = ROOT / "scripts" / "lib"
REPORT = ROOT / "scripts" / "report"
sys.path[:0] = [str(LIB), str(REPORT)]

import anchor_plan
import receipt_validate
import shared_release_receipt as shared
import time_spotcheck


TOKEN = "0x" + "a" * 40
ADDR = "0x" + "1" * 40
ADDR2 = "0x" + "2" * 40
EDGE_KIND = "门槛±10% 边缘地址"
FIELDS = {"script", "sha256", "commit", "protocol", "status", "reason"}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _plan(schema="anchor-plan/v3"):
    return {
        "schema": schema,
        "date_range": ["2025-01-01", "2025-01-02"],
        "final_block": 300,
        "matrix_points": [],
        "forced_points": [],
    }


def _balance(*, source="day_end_block", day="2025-01-01"):
    point = {
        "kind": "矩阵[早·大户]",
        "addr": ADDR,
        "day": day,
        "expected_balance_raw": "10",
        "balance_block_source": source,
    }
    if source == "day_end_block":
        point["day_end_block"] = 100
    return point


def _tx():
    return {
        "kind": "全史最大单笔转账",
        "tx": "0xtx",
        "from": ADDR,
        "to": ADDR2,
        "day": "2025-01-01",
        "block": 101,
        "expected_value_raw": "7",
    }


def _expect_reject(fn, needle=""):
    try:
        fn()
    except ValueError as exc:
        if needle and needle not in str(exc):
            raise AssertionError(f"expected rejection containing {needle!r}, got {exc!r}") from exc
        return
    raise AssertionError("malformed anchor point unexpectedly accepted")


def _expect_all_reject(cases):
    accepted = []
    wrong_errors = []
    for label, fn, needle in cases:
        try:
            fn()
        except ValueError as exc:
            if needle and needle not in str(exc):
                wrong_errors.append(f"{label}=>{exc}")
        else:
            accepted.append(label)
    if accepted or wrong_errors:
        raise AssertionError(
            f"accepted={accepted or 'none'} wrong_errors={wrong_errors or 'none'}")


def _produce_plan(root):
    source = root / "transfers.csv"
    rows = ["block,ts,tx,from,to,value"]
    for index in range(1, 25):
        rows.append(
            f"{99 + index},2025-01-{1 + (index % 3):02d}T00:00:00Z,0xt{index},"
            f"0x{'0' * 40},0x{index:040x},100"
        )
    source.write_text("\n".join(rows) + "\n", encoding="utf-8")
    out = root / "plan"
    proc = subprocess.run(
        [
            sys.executable,
            str(LIB / "anchor_plan.py"),
            "--input", str(source),
            "--chain", "bsc",
            "--token", TOKEN,
            "--total-supply", "10000",
            "--decimals", "0",
            "--min-pct", "0",
            "--final-block", "300",
            "--boundary-blocks", "110",
            "--out-dir", str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return source, out / "anchor_plan.json", out / "anchor_plan.receipt.json"


def _refresh_receipt(plan_path, receipt_path):
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["output"]["size"] = plan_path.stat().st_size
    receipt["output"]["sha256"] = _sha(plan_path)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")


def _ref(path, root):
    path = Path(path)
    return {
        "path": path.resolve().relative_to(Path(root).resolve()).as_posix(),
        "size": path.stat().st_size,
        "sha256": _sha(path),
    }


def _shared_authority(root, source, plan_path, receipt_path):
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    time_receipt = {
        "inputs": {
            "plan": _ref(plan_path, root),
            "plan_receipt": _ref(receipt_path, root),
            "input": _ref(source, root),
        }
    }
    return shared._validated_time_plan_authority(root, time_receipt, plan["target"])


def test_01_v3_full_positive():
    with tempfile.TemporaryDirectory(prefix="anchor_v3_positive_") as td:
        source, plan_path, receipt_path = _produce_plan(Path(td))
        plan = time_spotcheck.load_validated_plan(plan_path, receipt_path)
        assert plan["schema"] == "anchor-plan/v3"
        assert _shared_authority(Path(td), source, plan_path, receipt_path) == plan
        anchor_plan._validate_probe_blocks(plan, plan["final_block"])
        time_spotcheck.validate_semantic_replay(plan, source)
        balances, txs, odd = time_spotcheck.classify(plan)
        assert balances and txs and not odd
        for family in ("matrix_points", "forced_points"):
            for point in plan[family]:
                shared._plan_point(point, family, plan)
                if point.get("expected_balance_raw") is not None and point.get("addr"):
                    assert point["balance_block_source"] in {"day_end_block", "final_block"}
                else:
                    assert "balance_block_source" not in point


def test_02_bad_source_enum_rejected():
    plan = _plan()
    plan["matrix_points"] = [_balance(source="foo")]
    plan["matrix_points"][0]["day_end_block"] = 100
    _expect_reject(lambda: anchor_plan._validate_probe_blocks(plan, 300))


def test_03_final_source_in_matrix_rejected():
    plan = _plan()
    plan["matrix_points"] = [_balance(source="final_block")]
    _expect_reject(lambda: time_spotcheck.classify(plan))


def test_04_final_source_forbidden_keys_rejected():
    cases = []
    for key, value in (("day_end_block", 100), ("block", 100), ("tx", "0xtx")):
        plan = _plan()
        point = _balance(source="final_block", day="2025-01-02")
        point[key] = value
        plan["forced_points"] = [point]
        cases.append((key, lambda plan=plan: time_spotcheck.classify(plan), ""))
    _expect_all_reject(cases)


def test_05_day_end_block_shape_rejected():
    cases = []
    for value in (None, "100", True):
        plan = _plan()
        point = _balance()
        if value is None:
            point.pop("day_end_block")
        else:
            point["day_end_block"] = value
        plan["matrix_points"] = [point]
        label = "missing" if value is None else f"type={type(value).__name__}"
        cases.append((label, lambda plan=plan: time_spotcheck.classify(plan), ""))
    _expect_all_reject(cases)


def test_06_tx_with_balance_source_rejected():
    plan = _plan()
    point = _tx()
    point["balance_block_source"] = "day_end_block"
    plan["forced_points"] = [point]
    _expect_reject(lambda: time_spotcheck.classify(plan))


def test_07_balance_without_source_rejected():
    plan = _plan()
    point = _balance()
    point.pop("balance_block_source")
    plan["matrix_points"] = [point]
    _expect_reject(lambda: anchor_plan._validate_probe_blocks(plan, 300))


def test_08_kind_text_is_not_semantic():
    with tempfile.TemporaryDirectory(prefix="anchor_v3_kind_") as td:
        source, plan_path, _ = _produce_plan(Path(td))
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        edge = next(point for point in plan["forced_points"]
                    if point.get("balance_block_source") == "final_block")
        edge["kind"] = "改写后的纯展示文案"
        replayed = {key: copy.deepcopy(plan[key]) for key in (
            "date_range", "time_cuts", "cell_population", "boundary_blocks",
            "matrix_points", "forced_points")}
        original = time_spotcheck.generate_anchor_selection
        time_spotcheck.generate_anchor_selection = lambda **_kwargs: copy.deepcopy(replayed)
        try:
            anchor_plan._validate_probe_blocks(plan, plan["final_block"])
            time_spotcheck.validate_semantic_replay(plan, source)
            balances, _, _ = time_spotcheck.classify(plan)
            assert time_spotcheck.balance_query_block(plan, edge) == plan["final_block"]
            assert edge in balances
            shared._plan_point(edge, "forced_points", plan)
        finally:
            time_spotcheck.generate_anchor_selection = original


def _v2_projection(plan):
    legacy = copy.deepcopy(plan)
    legacy["schema"] = "anchor-plan/v2"
    for family in ("matrix_points", "forced_points"):
        for point in legacy[family]:
            if point.get("expected_balance_raw") is not None and point.get("addr"):
                del point["balance_block_source"]
    return legacy


def test_09_v2_fixture_full_compatibility():
    with tempfile.TemporaryDirectory(prefix="anchor_v2_compat_") as td:
        source, plan_path, receipt_path = _produce_plan(Path(td))
        v3 = json.loads(plan_path.read_text(encoding="utf-8"))
        v2 = _v2_projection(v3)
        plan_path.write_text(json.dumps(v2, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["plan_schema"] = "anchor-plan/v2"
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
        _refresh_receipt(plan_path, receipt_path)
        loaded = time_spotcheck.load_validated_plan(plan_path, receipt_path)
        assert _shared_authority(Path(td), source, plan_path, receipt_path) == loaded
        anchor_plan._validate_probe_blocks(loaded, loaded["final_block"])
        time_spotcheck.validate_semantic_replay(loaded, source)
        for family in ("matrix_points", "forced_points"):
            for point in loaded[family]:
                shared._plan_point(point, family, loaded)

        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["plan_schema"] = "anchor-plan/v3"
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
        _expect_reject(
            lambda: _shared_authority(Path(td), source, plan_path, receipt_path),
            "plan_schema mismatch")


def test_10_v2_projection_asserts_before_stripping():
    with tempfile.TemporaryDirectory(prefix="anchor_v2_projection_") as td:
        source, plan_path, _ = _produce_plan(Path(td))
        v3 = json.loads(plan_path.read_text(encoding="utf-8"))
        v2 = _v2_projection(v3)
        time_spotcheck.validate_semantic_replay(v2, source)

        replayed = {key: copy.deepcopy(v3[key]) for key in (
            "date_range", "time_cuts", "cell_population", "boundary_blocks",
            "matrix_points", "forced_points")}
        victim = next(point for family in ("matrix_points", "forced_points")
                      for point in replayed[family]
                      if point.get("expected_balance_raw") is not None and point.get("addr"))
        victim.pop("balance_block_source")
        original = time_spotcheck.generate_anchor_selection
        time_spotcheck.generate_anchor_selection = lambda **_kwargs: copy.deepcopy(replayed)
        try:
            _expect_reject(lambda: time_spotcheck.validate_semantic_replay(v2, source),
                           "balance_block_source")
        finally:
            time_spotcheck.generate_anchor_selection = original

        attacked = copy.deepcopy(v2)
        attacked["matrix_points"][0]["balance_block_source"] = "day_end_block"
        _expect_reject(lambda: time_spotcheck.validate_semantic_replay(attacked, source),
                       "deterministic replay")


def test_11_strict_xor_rejections():
    attacks = []
    balance_with_tx = _balance()
    balance_with_tx["tx"] = "0xtx"
    attacks.append(("balance-with-tx-key", balance_with_tx))
    tx_with_source = _tx()
    tx_with_source["balance_block_source"] = "day_end_block"
    attacks.append(("tx-with-balance-source", tx_with_source))
    mixed = _balance()
    mixed.update({"tx": "0xtx", "expected_value_raw": "7"})
    attacks.append(("both-balance-and-tx", mixed))
    cases = []
    for label, point in attacks:
        plan = _plan()
        plan["forced_points"] = [point]
        cases.append((label, lambda plan=plan: time_spotcheck.classify(plan), ""))
    _expect_all_reject(cases)


def _receipt(producer_hash):
    return {
        "schema": "anchor-plan-receipt/v2",
        "target": {"chain": "bsc", "token": TOKEN, "as_of_block": 300},
        "producer": {"path": "scripts/lib/anchor_plan.py", "sha256": producer_hash},
        "mode": "formal",
        "inputs": {},
        "verdict": "PASS",
        "exit_code": 0,
    }


def test_12_producer_history_and_default_boundary():
    import producer_history

    assert producer_history.PRODUCER_HISTORY
    for index, entry in enumerate(producer_history.PRODUCER_HISTORY):
        assert set(entry) == FIELDS, f"entry[{index}] field drift"
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
        assert re.fullmatch(r"[0-9a-f]{40}", entry["commit"])
        assert entry["status"] in {"ACTIVE", "REVOKED"}
        assert entry["script"] and entry["protocol"] and entry["reason"].strip()

    allowed = producer_history.historical_producer_hashes(
        "scripts/lib/anchor_plan.py", "anchor-plan/v2")
    old_hash = "e5168a455d53bb5163722ea7f2a67c42b20bd3dd8ef6c3ae5e588014842cc1d9"
    assert old_hash in allowed
    assert receipt_validate.validate_receipt(_receipt("0" * 64),
                                              allowed_producer_hashes=allowed)
    assert not receipt_validate.validate_receipt(_receipt(old_hash),
                                                  allowed_producer_hashes=allowed)
    assert receipt_validate.validate_receipt(_receipt(old_hash)), \
        "default path must still reject a historical non-current hash"
    current_hash = _sha(LIB / "anchor_plan.py")
    assert not receipt_validate.validate_receipt(_receipt(current_hash))
    shared.repo_ref_ok(_receipt(old_hash)["producer"], {"scripts/lib/anchor_plan.py"},
                       "historical anchor", allowed_hashes=allowed)

    original = producer_history.PRODUCER_HISTORY
    producer_history.PRODUCER_HISTORY = original + ({
        "script": "other.py",
        "sha256": old_hash,
        "commit": "0000000",
        "protocol": "other/v1",
        "status": "REVOKED",
        "reason": "test-only hash-wide revocation",
    },)
    try:
        assert old_hash not in producer_history.historical_producer_hashes(
            "scripts/lib/anchor_plan.py", "anchor-plan/v2")
    finally:
        producer_history.PRODUCER_HISTORY = original

    producer_history.PRODUCER_HISTORY = original + ({
        "script": "other.py",
        "sha256": old_hash,
        "commit": "0" * 40,
        "protocol": "other/v1",
        "status": "Revoked",
        "reason": "test-only invalid status",
    },)
    try:
        _expect_reject(lambda: producer_history.historical_producer_hashes(
            "scripts/lib/anchor_plan.py", "anchor-plan/v2"), "status invalid")
    finally:
        producer_history.PRODUCER_HISTORY = original

    doc = receipt_validate.validate_receipt.__doc__ or ""
    assert "receipt.producer.path" in doc and "caller" in doc.lower()

    if (ROOT / ".git").exists():
        for entry in producer_history.PRODUCER_HISTORY:
            proc = subprocess.run(
                ["git", "show", f"{entry['commit']}:{entry['script']}"],
                cwd=ROOT,
                capture_output=True,
            )
            assert proc.returncode == 0, proc.stderr.decode(errors="replace")
            assert hashlib.sha256(proc.stdout).hexdigest() == entry["sha256"]


def test_13_duplicate_keys_rejected_on_both_authority_paths():
    for attacked in ("plan", "receipt"):
        with tempfile.TemporaryDirectory(prefix=f"anchor_dup_{attacked}_") as td:
            source, plan_path, receipt_path = _produce_plan(Path(td))
            if attacked == "plan":
                raw = plan_path.read_text(encoding="utf-8")
                needle = '"balance_block_source": "day_end_block"'
                plan_path.write_text(
                    raw.replace(
                        needle,
                        '"balance_block_source": "final_block",\n      ' + needle,
                        1,
                    ),
                    encoding="utf-8",
                )
                _refresh_receipt(plan_path, receipt_path)
            else:
                raw = receipt_path.read_text(encoding="utf-8")
                needle = '"plan_schema": "anchor-plan/v3"'
                receipt_path.write_text(
                    raw.replace(
                        needle,
                        '"plan_schema": "anchor-plan/v2",\n  ' + needle,
                        1,
                    ),
                    encoding="utf-8",
                )
            _expect_reject(
                lambda: time_spotcheck.load_validated_plan(plan_path, receipt_path),
                "duplicate JSON key",
            )
            _expect_reject(
                lambda: _shared_authority(Path(td), source, plan_path, receipt_path),
                "duplicate JSON key",
            )


def test_14_v3_rejects_v2_historical_producer_hash():
    with tempfile.TemporaryDirectory(prefix="anchor_protocol_history_") as td:
        source, plan_path, receipt_path = _produce_plan(Path(td))
        old_hash = "e5168a455d53bb5163722ea7f2a67c42b20bd3dd8ef6c3ae5e588014842cc1d9"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["producer"]["sha256"] = old_hash
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["producer"]["sha256"] = old_hash
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
        _refresh_receipt(plan_path, receipt_path)
        _expect_reject(
            lambda: time_spotcheck.load_validated_plan(plan_path, receipt_path),
            "producer hash mismatch",
        )
        _expect_reject(
            lambda: _shared_authority(Path(td), source, plan_path, receipt_path),
            "producer hash mismatch",
        )


def test_15_schema_dispatch_v2_field_and_enum_type_fail_closed():
    unsupported = _plan("anchor-plan/v9")
    unsupported["matrix_points"] = [_balance()]
    _expect_all_reject([
        ("classify-v9", lambda: time_spotcheck.classify(unsupported),
         "unsupported plan schema"),
        ("balance-block-v9", lambda: time_spotcheck.balance_query_block(
            unsupported, unsupported["matrix_points"][0]), "unsupported plan schema"),
        ("release-point-v9", lambda: shared._plan_point(
            unsupported["matrix_points"][0], "matrix_points", unsupported),
         "unsupported plan schema"),
    ])

    legacy = _plan("anchor-plan/v2")
    legacy_point = _balance(source="final_block")
    legacy_point["day_end_block"] = 100
    legacy["matrix_points"] = [legacy_point]
    _expect_all_reject([
        ("sign-v2-machine-field", lambda: anchor_plan._validate_probe_blocks(legacy, 300),
         "v2 plan point carries v3 machine field"),
        ("classify-v2-machine-field", lambda: time_spotcheck.classify(legacy),
         "v2 plan point carries v3 machine field"),
        ("balance-block-v2-machine-field", lambda: time_spotcheck.balance_query_block(
            legacy, legacy_point), "v2 plan point carries v3 machine field"),
        ("release-point-v2-machine-field", lambda: shared._plan_point(
            legacy_point, "matrix_points", legacy),
         "v2 plan point carries v3 machine field"),
    ])

    malformed = _plan()
    malformed_point = _balance()
    malformed_point["balance_block_source"] = ["day_end_block"]
    malformed["matrix_points"] = [malformed_point]
    _expect_reject(lambda: time_spotcheck.classify(malformed),
                   "balance_block_source invalid")


def main():
    tests = [
        value for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    print(f"anchor-plan v3: {len(tests) - failed}/{len(tests)} PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
