#!/usr/bin/env python3
"""F-09 GMGN divergence yellow-light and investigation-note regressions."""
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

import shared_release_receipt as shared


TARGET = {
    "chain": "eth",
    "token": "0x1111111111111111111111111111111111111111",
    "as_of_block": 123,
}
HOLDERS = [f"0x{value:040x}" for value in (2, 3, 4)]
BALANCES = {HOLDERS[0]: 60, HOLDERS[1]: 30, HOLDERS[2]: 10}
NOTE_SCHEMA = "gmgn-divergence-note/v1"


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


def _canonical_sha(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _expect_error(fn, needle: str = "") -> None:
    try:
        fn()
    except ValueError as exc:
        if needle and needle not in str(exc):
            raise AssertionError(f"expected {needle!r}, got {exc!r}") from exc
        return
    raise AssertionError("invalid GMGN divergence state unexpectedly passed")


class _ReconPool:
    def attest(self):
        return 1

    def call(self, method, params):
        assert method == "eth_call"
        address = "0x" + params[0]["data"][-40:]
        return {"ok": True, "result": hex(BALANCES[address])}


def _fixture(root: Path, *, divergent: bool):
    producer = _load(ROOT / "scripts" / "evm" / "verify_recon.py",
                     f"f09_verify_{root.name}")
    config = _write_json(root / "config.json", {
        "token": TARGET["token"], "decimals": 0, "total_supply_human": "100",
        "alchemy": {"url": "http://offline/", "key": "fixture"},
    })
    balances = _write_json(root / "balances.json", {k: str(v) for k, v in BALANCES.items()})
    stats = _write_json(root / "replay_stats.json", {
        "max_block": 123, "mint_total_raw": "100", "burn_total_raw": "0",
    })
    gmgn = root / "gmgn.csv"
    first_pct = "0.5" if divergent else "0.6"
    gmgn.write_text(
        "address,pct\n" + "\n".join(
            f"{address},{pct}" for address, pct in
            ((HOLDERS[0], first_pct), (HOLDERS[1], "0.3"), (HOLDERS[2], "0.1"))) + "\n",
        encoding="utf-8")
    out = root / "verify_recon.json"
    args = ["--config", str(config), "--balances", str(balances),
            "--replay-stats", str(stats), "--gmgn", str(gmgn), "--chain", "eth",
            "--token", TARGET["token"], "--end-block", "123", "--top-n", "3",
            "--rpc", "http://offline/", "--out", str(out)]
    return producer, out, args


def _run(producer, args, note: Path | None = None) -> int:
    argv = list(args)
    if note is not None:
        argv += ["--divergence-note", str(note)]
    with mock.patch.object(producer, "attested_rpc_pool", return_value=_ReconPool()):
        return producer.main(argv)


def _divergences(receipt: dict) -> list[dict]:
    return [
        {key: row[key] for key in ("address", "gmgn_pct", "replay_pct", "diff_pp")}
        for row in receipt["observations"]["gmgn_comparison"]["rows"]
        if row["status"] == "DIFF"
    ]


def _note_payload(receipt: dict) -> dict:
    request = {
        "target": copy.deepcopy(receipt["target"]),
        "inputs_sha256": {
            key: receipt["inputs"][key]["sha256"]
            for key in ("config", "balances", "replay_stats", "gmgn")
        },
        "divergences": _divergences(receipt),
    }
    findings = [
        {"address": row["address"], "cause": "gmgn_data_lag",
         "explanation": "GMGN公开快照存在更新延迟，已逐项核对冻结块重放账本与输入哈希保持一致。"}
        for row in request["divergences"]
    ]
    return {
        "schema": NOTE_SCHEMA,
        "request": request,
        "request_sha256": _canonical_sha(request),
        "findings": findings,
        "conclusion": "重放数据经查证无误，当前差异仅来自已记录的第三方口径或时效原因。",
        "investigator": "fixture-reviewer",
        "investigated_at_utc": "2026-08-15T00:00:00Z",
    }


def _refresh_request_sha(note: dict) -> None:
    note["request_sha256"] = _canonical_sha(note["request"])


def _validate_consumer(root: Path, out: Path) -> dict:
    return shared.validate_reconciliation_check(
        root, "balance", _item(out, root), TARGET, "evm")


def _test_divergent_four_states(root: Path):
    producer, out, args = _fixture(root, divergent=True)

    # State 1: producer emits PASS/yellow, but release consumer blocks without a note.
    assert _run(producer, args) == 0
    yellow = json.loads(out.read_text(encoding="utf-8"))
    assert yellow["verdict"] == "PASS" and yellow["exit_code"] == 0
    assert yellow["warnings"] == ["gmgn_divergence"]
    _expect_error(lambda: _validate_consumer(root, out), "divergence_note")

    # State 2: a complete note is bound by a producer rerun and passes consumption.
    valid_note = _write_json(root / "gmgn_divergence_note.json", _note_payload(yellow))
    assert _run(producer, args, valid_note) == 0
    bound = json.loads(out.read_text(encoding="utf-8"))
    assert bound["warnings"] == ["gmgn_divergence"]
    assert bound["inputs"]["divergence_note"] == _ref(valid_note, root)
    _validate_consumer(root, out)

    # State 3: producer rejects every single-field invalid note and preserves yellow output.
    base = _note_payload(yellow)
    mutations = []

    def missing_divergence(value):
        value["request"]["divergences"] = []
        value["findings"] = []
        _refresh_request_sha(value)
    mutations.append(("missing", missing_divergence))

    def wrong_number(value):
        value["request"]["divergences"][0]["diff_pp"] = "9"
        _refresh_request_sha(value)
    mutations.append(("number", wrong_number))

    def wrong_input(value):
        value["request"]["inputs_sha256"]["gmgn"] = "0" * 64
        _refresh_request_sha(value)
    mutations.append(("input", wrong_input))
    mutations.extend([
        ("cause", lambda value: value["findings"][0].__setitem__("cause", "self_error")),
        ("short", lambda value: value["findings"][0].__setitem__("explanation", "x" * 26)),
        ("time", lambda value: value.__setitem__("investigated_at_utc", "2026-08-15")),
        ("request_sha", lambda value: value.__setitem__("request_sha256", "f" * 64)),
    ])
    for name, mutate in mutations:
        invalid = copy.deepcopy(base)
        mutate(invalid)
        note_path = _write_json(root / f"invalid_{name}.json", invalid)
        before = out.read_bytes()
        assert _run(producer, args, note_path) == 1, name
        assert out.read_bytes() == before, f"producer overwrote yellow receipt for {name}"

    # Consumer-side independent mutations after a valid bound note.
    bound = json.loads(out.read_text(encoding="utf-8"))
    no_warning = copy.deepcopy(bound)
    no_warning["warnings"] = []
    no_warning_path = _write_json(root / "consumer_no_warning.json", no_warning)
    _expect_error(lambda: shared.validate_reconciliation_check(
        root, "balance", _item(no_warning_path, root), TARGET, "evm"), "warnings")

    outside = copy.deepcopy(bound)
    outside["inputs"]["divergence_note"] = {
        "path": "../outside.json", "size": 1, "sha256": "0" * 64,
    }
    outside_path = _write_json(root / "consumer_outside.json", outside)
    _expect_error(lambda: shared.validate_reconciliation_check(
        root, "balance", _item(outside_path, root), TARGET, "evm"))
    return producer, yellow, base


def _test_zero_diff_state(root: Path) -> None:
    producer, out, args = _fixture(root, divergent=False)
    assert _run(producer, args) == 0
    clean = json.loads(out.read_text(encoding="utf-8"))
    assert clean["warnings"] == []
    _validate_consumer(root, out)

    false_warning = copy.deepcopy(clean)
    false_warning["warnings"] = ["gmgn_divergence"]
    false_warning_path = _write_json(root / "consumer_false_warning.json", false_warning)
    _expect_error(lambda: shared.validate_reconciliation_check(
        root, "balance", _item(false_warning_path, root), TARGET, "evm"), "warnings")

    note_path = _write_json(root / "prefilled_note.json", _note_payload(clean))
    before = out.read_bytes()
    assert _run(producer, args, note_path) == 1
    assert out.read_bytes() == before


def _test_two_side_vectors(root: Path, producer, yellow: dict, valid: dict) -> None:
    vectors = [("valid", copy.deepcopy(valid), True)]
    cases = []

    def add(name, mutate):
        value = copy.deepcopy(valid)
        mutate(value)
        cases.append((name, value, False))

    add("schema", lambda value: value.__setitem__("schema", "gmgn-divergence-note/v0"))
    add("target", lambda value: value["request"]["target"].__setitem__("as_of_block", 124))
    add("input", lambda value: value["request"]["inputs_sha256"].__setitem__("gmgn", "0" * 64))
    add("divergence", lambda value: value["request"]["divergences"][0].__setitem__("diff_pp", "1"))
    add("request_sha", lambda value: value.__setitem__("request_sha256", "0" * 64))
    add("cause", lambda value: value["findings"][0].__setitem__("cause", "self_error"))
    add("explanation", lambda value: value["findings"][0].__setitem__("explanation", "x" * 26))
    add("conclusion", lambda value: value.__setitem__("conclusion", "checked"))
    add("investigator", lambda value: value.__setitem__("investigator", "\u200b"))
    add("time", lambda value: value.__setitem__("investigated_at_utc", "not-utc"))
    vectors.extend(cases)

    input_refs = {key: yellow["inputs"][key] for key in
                  ("config", "balances", "replay_stats", "gmgn")}
    divergences = _divergences(yellow)
    for name, payload, expected in vectors:
        if name in {"target", "input", "divergence"}:
            _refresh_request_sha(payload)
        path = _write_json(root / f"vector_{name}.json", payload)
        verdicts = []
        for validator in (producer._validate_gmgn_divergence_note,
                          shared._validate_gmgn_divergence_note):
            try:
                validator(root, path, TARGET, input_refs, divergences)
                verdicts.append(True)
            except ValueError:
                verdicts.append(False)
        assert verdicts == [expected, expected], (name, verdicts)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="f09-gmgn-note-") as raw:
        root = Path(raw).resolve()
        divergent = root / "divergent"; divergent.mkdir()
        producer, yellow, valid = _test_divergent_four_states(divergent)
        clean = root / "clean"; clean.mkdir()
        _test_zero_diff_state(clean)
        vectors = root / "vectors"; vectors.mkdir()
        _test_two_side_vectors(vectors, producer, yellow, valid)
    print("PASS test_gmgn_divergence_note")


if __name__ == "__main__":
    main()
