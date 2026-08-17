#!/usr/bin/env python3
"""U3: HyperSync CSV resume must retain one collector hash per receipt chain."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
EVM = HERE.parent / "evm"
LIB = HERE.parent / "lib"
FETCH = EVM / "fetch_hypersync.py"
TOKEN = "0x" + "a" * 40
PROTOCOL = "evm-collector-run/v2"
GUIDANCE = (
    "采集脚本已升级，禁止跨版本续采同一 CSV；请以前驱 receipt 覆盖终点为新起点另开 "
    "CSV/receipt，作为新 channel 段接入 channels.json"
)

sys.path[:0] = [str(EVM), str(LIB), str(HERE)]


class Response:
    status_code = 200
    text = ""

    def __init__(self, next_block):
        self.next_block = next_block

    def json(self):
        return {"data": [], "next_block": self.next_block,
                "archive_height": self.next_block}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path):
    Path(path).write_text(
        "block,ts,tx,from,to,value_raw,uniqueId,block_hash\n",
        encoding="utf-8",
    )


def native_payload(data, collector_hash, *, schema=PROTOCOL, collector_marker=True):
    path = Path(data).resolve()
    size = path.stat().st_size
    digest = sha256(path)
    payload = {
        "schema": schema,
        "status": "PASS",
        "producer": "fetch_hypersync.py/v3",
        "query": {
            "token": TOKEN,
            "query_schema": "erc20-transfer-fields/v2",
            "provider_url": "https://fixture.hypersync.xyz/query",
            "requested_from": 0,
            "requested_to": 10,
        },
        "completion": {"reason": "requested_bound_reached", "next_block": 10},
        "segments": [{
            "requested_from": 0,
            "requested_to": 10,
            "provider_next_block": 10,
            "output_prefix": {"size": size, "sha256": digest},
        }],
        "output": {
            "path": str(path),
            "size": size,
            "sha256": digest,
            "rows": 0,
            "min_block": None,
            "max_block": None,
        },
    }
    if collector_marker is not False:
        payload["collector"] = collector_marker if collector_marker is not True else {
            "path": "fetch_hypersync.py", "sha256": collector_hash,
        }
    return payload


def argv(root, out, receipt, *, resume_receipt=None, frm=0, to=20):
    token_file = Path(root) / "hypersync.token"
    token_file.write_text("fixture-token\n", encoding="utf-8")
    args = [
        "fetch_hypersync.py", str(frm), "--token-file", str(token_file),
        "--url", "https://fixture.hypersync.xyz/query",
        "--token-addr", TOKEN, "--to-block", str(to),
        "--out", str(out), "--receipt", str(receipt), "--sleep", "0",
    ]
    if resume_receipt is not None:
        args += ["--resume-receipt", str(resume_receipt)]
    return args


def invoke(module, args, *, response_to, provenance_stub=False, post=None):
    import channels_preflight

    stdout, stderr = io.StringIO(), io.StringIO()
    request = post or (lambda *a, **k: Response(response_to))
    code = 0
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(sys, "argv", args))
        stack.enter_context(mock.patch.object(module.requests, "post", request))
        stack.enter_context(mock.patch.object(module.time, "sleep", lambda _seconds: None))
        if provenance_stub:
            stack.enter_context(mock.patch.object(
                channels_preflight, "_csv_collector_provenance", lambda *a, **k: {}
            ))
        stack.enter_context(contextlib.redirect_stdout(stdout))
        stack.enter_context(contextlib.redirect_stderr(stderr))
        try:
            result = module.main()
            if isinstance(result, int):
                code = result
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, stdout.getvalue() + stderr.getvalue()


def historical_hash():
    import collector_history

    current = sha256(FETCH)
    return next(
        entry["sha256"]
        for entry in collector_history.COLLECTOR_HISTORY
        if entry["script"] == "fetch_hypersync.py"
        and entry["protocol"] == PROTOCOL
        and entry["status"] == "ACTIVE"
        and entry["sha256"] != current
    )


def resume_fixture(root, collector_hash, *, schema=PROTOCOL, collector_marker=True,
                   raw_receipt=None):
    out = Path(root) / "full.csv"
    prior = Path(root) / "prior.collector.json"
    next_receipt = Path(root) / "next.collector.json"
    write_csv(out)
    payload = native_payload(
        out, collector_hash, schema=schema, collector_marker=collector_marker
    )
    prior.write_text(raw_receipt or json.dumps(payload), encoding="utf-8")
    return out, prior, next_receipt, payload


def test_same_hash_resume_passes():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out, prior, receipt, _ = resume_fixture(root, sha256(FETCH))
        module = load(FETCH, "u3_same_hash")
        code, transcript = invoke(
            module, argv(root, out, receipt, resume_receipt=prior), response_to=20
        )
        assert code == 0, transcript
        result = json.loads(receipt.read_text(encoding="utf-8"))
        assert len(result["segments"]) == 2
        assert result["collector"]["sha256"] == sha256(FETCH)


def test_cross_hash_resume_rejected_with_guidance():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out, prior, receipt, _ = resume_fixture(root, historical_hash())
        before = out.read_bytes()
        module = load(FETCH, "u3_cross_hash")
        code, transcript = invoke(
            module, argv(root, out, receipt, resume_receipt=prior), response_to=20
        )
        assert code == 2 and GUIDANCE in transcript, transcript
        assert out.read_bytes() == before and not receipt.exists()


def test_missing_and_malformed_collector_rejected_by_resume_layer():
    cases = ((False, "missing"), ([], "list"), ({"sha256": 7}, "non-string-hash"))
    for marker, label in cases:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out, prior, receipt, _ = resume_fixture(
                root, sha256(FETCH), collector_marker=marker
            )
            module = load(FETCH, f"u3_bad_collector_{label}")
            code, transcript = invoke(
                module, argv(root, out, receipt, resume_receipt=prior),
                response_to=20, provenance_stub=True,
            )
            assert code == 2 and "collector" in transcript, (label, transcript)
            assert not receipt.exists()


def test_duplicate_collector_key_rejected_by_resume_reader():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out, prior, receipt, payload = resume_fixture(root, sha256(FETCH))
        payload.pop("collector")
        raw = (
            '{"collector":{"path":"fetch_hypersync.py","sha256":"'
            + historical_hash()
            + '"},"collector":{"path":"fetch_hypersync.py","sha256":"'
            + sha256(FETCH)
            + '"},'
            + json.dumps(payload)[1:]
        )
        prior.write_text(raw, encoding="utf-8")
        module = load(FETCH, "u3_duplicate_collector")
        code, transcript = invoke(
            module, argv(root, out, receipt, resume_receipt=prior),
            response_to=20, provenance_stub=True,
        )
        assert code == 2 and "duplicate JSON key" in transcript, transcript
        assert not receipt.exists()


def test_unknown_schema_rejected_before_dispatch():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out, prior, receipt, _ = resume_fixture(
            root, sha256(FETCH), schema="evm-collector-run/future"
        )
        module = load(FETCH, "u3_unknown_schema")
        code, transcript = invoke(
            module, argv(root, out, receipt, resume_receipt=prior),
            response_to=20, provenance_stub=True,
        )
        assert code == 2 and "schema" in transcript, transcript
        assert not receipt.exists()


def test_sqd_emitter_is_single_segment_and_fresh_only():
    from csv_collector_receipt import emit_native_receipt

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        data = root / "sqd.csv"
        write_csv(data)
        payload = emit_native_receipt(
            data, root / "sqd.collector.json", EVM / "fetch_sqd_evm.py",
            TOKEN, "https://portal.sqd.dev/datasets/fixture/stream",
            10, 20, 20, fresh_output=True,
        )
        assert len(payload["segments"]) == 1
        assert payload["segments"][0]["requested_from"] == 10
        assert payload["segments"][0]["requested_to"] == 20
        try:
            emit_native_receipt(
                data, root / "sqd-existing.collector.json", EVM / "fetch_sqd_evm.py",
                TOKEN, "https://portal.sqd.dev/datasets/fixture/stream",
                10, 20, 20, fresh_output=False,
            )
        except ValueError as exc:
            assert "existing unreceipted prefix" in str(exc)
        else:
            raise AssertionError("SQD emitter signed an existing output")


def test_upgrade_continues_as_a_new_channel():
    import channels_preflight
    from make_channel_receipt import make_receipt

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        old_csv = root / "old.csv"
        old_native = root / "old.collector.json"
        write_csv(old_csv)
        old_native.write_text(
            json.dumps(native_payload(old_csv, historical_hash())), encoding="utf-8"
        )

        new_csv = root / "new.csv"
        new_native = root / "new.collector.json"
        module = load(FETCH, "u3_new_channel")
        code, transcript = invoke(
            module, argv(root, new_csv, new_native, frm=10, to=20), response_to=20
        )
        assert code == 0, transcript

        old_channel = root / "old.receipt.json"
        new_channel = root / "new.receipt.json"
        old_channel.write_text(json.dumps(make_receipt(
            old_csv, "v1csv", TOKEN, 0, 10, "old", collector_receipt=old_native
        )), encoding="utf-8")
        new_channel.write_text(json.dumps(make_receipt(
            new_csv, "v1csv", TOKEN, 10, 20, "new", collector_receipt=new_native
        )), encoding="utf-8")
        manifest = root / "channels.json"
        manifest.write_text(json.dumps({
            "schema": "evm-channels/v2", "token": TOKEN,
            "expected_from": 0, "expected_to": 20,
            "channels": [
                {"path": str(old_csv), "format": "v1csv", "lo": 0, "hi": 10,
                 "tag": "old", "receipt": str(old_channel)},
                {"path": str(new_csv), "format": "v1csv", "lo": 10, "hi": 20,
                 "tag": "new", "receipt": str(new_channel)},
            ],
        }), encoding="utf-8")
        ordered = channels_preflight.preflight_channels(manifest, root / "preflight")
        result = json.loads(
            (root / "preflight" / "channels_preflight.json").read_text(encoding="utf-8")
        )
        assert result["status"] == "PASS"
        assert [item["tag"] for item in ordered] == ["old", "new"]


def test_toctou_drift_rejected_before_receipt_signing():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        copied = root / "fetch_hypersync.py"
        shutil.copyfile(FETCH, copied)
        module = load(copied, "u3_toctou_copy")
        out = root / "fresh.csv"
        receipt = root / "fresh.collector.json"

        def mutate_then_reply(*_args, **_kwargs):
            copied.write_bytes(copied.read_bytes() + b"\n# fixture drift\n")
            return Response(10)

        code, transcript = invoke(
            module, argv(root, out, receipt, frm=0, to=10),
            response_to=10, post=mutate_then_reply,
        )
        assert code != 0 and "漂移" in transcript, transcript
        assert not out.exists() and not receipt.exists()


def test_revoked_current_hash_rejected_at_startup():
    import collector_history

    current = sha256(FETCH)
    revoked = {
        "script": "fetch_hypersync.py", "sha256": current,
        "commit": "test-fixture", "protocol": PROTOCOL, "status": "REVOKED",
        "reason": "Test-only startup revocation fixture.",
    }
    original = collector_history.COLLECTOR_HISTORY
    collector_history.COLLECTOR_HISTORY = original + (revoked,)
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "revoked.csv"
            receipt = root / "revoked.collector.json"
            module = load(FETCH, "u3_revoked_startup")
            code, transcript = invoke(
                module, argv(root, out, receipt, frm=0, to=10), response_to=10
            )
            assert code != 0 and "当前脚本版本已被吊销" in transcript, transcript
            assert not out.exists() and not receipt.exists()
    finally:
        collector_history.COLLECTOR_HISTORY = original


def main():
    checks = [
        ("same-hash resume passes", test_same_hash_resume_passes),
        ("cross-hash resume rejects with split-channel guidance",
         test_cross_hash_resume_rejected_with_guidance),
        ("missing/malformed collector rejects in resume layer",
         test_missing_and_malformed_collector_rejected_by_resume_layer),
        ("duplicate collector key rejects in resume reader",
         test_duplicate_collector_key_rejected_by_resume_reader),
        ("unknown prior schema rejects before dispatch",
         test_unknown_schema_rejected_before_dispatch),
        ("SQD receipt remains one segment and fresh-only",
         test_sqd_emitter_is_single_segment_and_fresh_only),
        ("collector upgrade continues through a new channel",
         test_upgrade_continues_as_a_new_channel),
        ("TOCTOU drift rejects before receipt signing",
         test_toctou_drift_rejected_before_receipt_signing),
        ("hash-wide REVOKED rejects current collector at startup",
         test_revoked_current_hash_rejected_at_startup),
    ]
    results = []
    for name, check in checks:
        try:
            check()
        except Exception as exc:
            results.append((name, False, f"{type(exc).__name__}: {exc}"))
        else:
            results.append((name, True, ""))
    failures = 0
    for name, passed, detail in results:
        failures += not passed
        print(f"{'PASS' if passed else 'FAIL'}: {name}" + (f" -- {detail}" if detail else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
