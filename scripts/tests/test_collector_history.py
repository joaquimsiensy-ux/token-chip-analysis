#!/usr/bin/env python3
"""R-2 collector history registry, provenance, and git-evidence guards."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
EVM = HERE.parent / "evm"
sys.path.insert(0, str(EVM))


FIELDS = {"script", "sha256", "commit", "protocol", "status", "reason"}


def _active_hash(script):
    import collector_history

    return next(
        entry["sha256"]
        for entry in collector_history.COLLECTOR_HISTORY
        if entry["script"] == script and entry["status"] == "ACTIVE"
    )


def _make_receipt(root, collector_path, collector_hash, label):
    import channels_preflight

    data = root / f"{label}.csv"
    data.write_text(
        "block,ts,tx,log_index,from,to,value_raw,block_hash\n"
        "10,2026-01-01T00:00:00,0xt,0,0xa,0xb,1,0xh\n",
        encoding="utf-8",
    )
    digest = channels_preflight._sha256_file(data)
    size = data.stat().st_size
    token = "0x" + "c" * 40
    payload = {
        "schema": "evm-collector-run/v2",
        "status": "PASS",
        "collector": {"path": collector_path, "sha256": collector_hash},
        "query": {
            "token": token,
            "query_schema": "erc20-transfer-fields/v2",
            "provider_url": "https://provider.example",
            "requested_from": 10,
            "requested_to": 13,
        },
        "completion": {"reason": "requested_bound_reached", "next_block": 13},
        "segments": [{
            "requested_from": 10,
            "requested_to": 13,
            "provider_next_block": 13,
            "output_prefix": {"size": size, "sha256": digest},
        }],
        "output": {
            "path": str(data.resolve()),
            "size": size,
            "sha256": digest,
            "rows": 1,
            "min_block": 10,
            "max_block": 10,
        },
    }
    receipt = root / f"{label}.receipt.json"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    return data, receipt, token


def _expect_reject(root, collector_path, collector_hash, label):
    import channels_preflight

    data, receipt, token = _make_receipt(root, collector_path, collector_hash, label)
    try:
        channels_preflight._csv_collector_provenance(receipt, data, token, 10, 13)
    except channels_preflight.ChannelsPreflightError:
        return
    raise AssertionError(f"collector provenance unexpectedly accepted: {label}")


def test_structure():
    import collector_history

    assert collector_history.COLLECTOR_HISTORY, "collector history registry is empty"
    for index, entry in enumerate(collector_history.COLLECTOR_HISTORY):
        assert isinstance(entry, dict), f"entry[{index}] is not a dict"
        assert set(entry) == FIELDS, f"entry[{index}] fields drift: {sorted(entry)}"
        assert isinstance(entry["script"], str) and entry["script"], f"entry[{index}] script empty"
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), \
            f"entry[{index}] invalid sha256"
        assert isinstance(entry["commit"], str) and entry["commit"].strip(), \
            f"entry[{index}] commit empty"
        assert isinstance(entry["protocol"], str) and entry["protocol"], \
            f"entry[{index}] protocol empty"
        assert entry["status"] in {"ACTIVE", "REVOKED"}, f"entry[{index}] invalid status"
        assert isinstance(entry["reason"], str) and entry["reason"].strip(), \
            f"entry[{index}] reason empty"


def test_active_historical_hash_passes(root):
    import channels_preflight

    historical_hash = _active_hash("fetch_hypersync.py")
    data, receipt, token = _make_receipt(
        root, "fetch_hypersync.py", historical_hash, "active-history"
    )
    result = channels_preflight._csv_collector_provenance(receipt, data, token, 10, 13)
    assert result["kind"] == "collector-native-csv-chain"


def test_unregistered_hash_rejected(root):
    _expect_reject(root, "fetch_hypersync.py", "0" * 64, "unregistered")


def test_wrong_script_name_rejected(root):
    _expect_reject(
        root,
        "historical_fetch_hypersync.py",
        _active_hash("fetch_hypersync.py"),
        "wrong-script",
    )


def test_non_string_hash_rejected(root):
    for index, value in enumerate((["f" * 64], 7)):
        _expect_reject(root, "fetch_hypersync.py", value, f"non-string-{index}")


def test_revoked_hash_rejected(root):
    import collector_history

    revoked_hash = "f" * 64
    original = collector_history.COLLECTOR_HISTORY
    collector_history.COLLECTOR_HISTORY = original + ({
        "script": "fetch_hypersync.py",
        "sha256": revoked_hash,
        "commit": "test-fixture",
        "protocol": "evm-collector-run/v2",
        "status": "REVOKED",
        "reason": "Test-only revoked entry proving status filtering.",
    },)
    try:
        _expect_reject(root, "fetch_hypersync.py", revoked_hash, "revoked")
    finally:
        collector_history.COLLECTOR_HISTORY = original


def test_revocation_overrides_active(root):
    import collector_history

    active_hash = _active_hash("fetch_hypersync.py")
    original = collector_history.COLLECTOR_HISTORY
    collector_history.COLLECTOR_HISTORY = original + ({
        "script": "fetch_hypersync.py",
        "sha256": active_hash,
        "commit": "test-fixture",
        "protocol": "evm-collector-run/v2",
        "status": "REVOKED",
        "reason": "Test-only twin proving revocation overrides ACTIVE registration.",
    },)
    try:
        assert active_hash not in collector_history.historical_script_hashes(
            "fetch_hypersync.py"
        ), "ACTIVE+REVOKED twin hash must be removed from the allowed set"
        _expect_reject(root, "fetch_hypersync.py", active_hash, "active-revoked-twin")
    finally:
        collector_history.COLLECTOR_HISTORY = original


def test_git_evidence():
    import collector_history

    git_marker = ROOT / ".git"
    if not git_marker.exists():
        print("SKIP: git evidence guard (.git not present in packaged skill)")
        return
    for entry in collector_history.COLLECTOR_HISTORY:
        script_path = f"scripts/evm/{entry['script']}"
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", entry["commit"], "HEAD"],
            cwd=ROOT,
            capture_output=True,
        )
        assert ancestor.returncode == 0, (
            f"collector history commit is not a HEAD ancestor: {entry['commit']}: "
            f"{ancestor.stderr.decode('utf-8', errors='replace').strip()}"
        )
        proc = subprocess.run(
            ["git", "show", f"{entry['commit']}:{script_path}"],
            cwd=ROOT,
            capture_output=True,
        )
        assert proc.returncode == 0, (
            f"git evidence missing for {entry['commit']}:{script_path}: "
            f"{proc.stderr.decode('utf-8', errors='replace').strip()}"
        )
        actual = hashlib.sha256(proc.stdout).hexdigest()
        assert actual == entry["sha256"], (
            f"git evidence hash mismatch for {entry['commit']}:{script_path}: "
            f"{actual} != {entry['sha256']}"
        )


def main():
    checks = []

    def check(name, fn):
        try:
            fn()
        except Exception as exc:
            checks.append((name, False, f"{type(exc).__name__}: {exc}"))
        else:
            checks.append((name, True, ""))

    check("registry entries have all six fields", test_structure)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        check("ACTIVE historical hash passes CSV provenance", lambda: test_active_historical_hash_passes(root))
        check("unregistered hash is rejected", lambda: test_unregistered_hash_rejected(root))
        check("wrong script name is rejected", lambda: test_wrong_script_name_rejected(root))
        check("non-string collector hashes are controlled rejects",
              lambda: test_non_string_hash_rejected(root))
        check("REVOKED historical hash is rejected", lambda: test_revoked_hash_rejected(root))
        check("REVOKED overrides an ACTIVE twin hash",
              lambda: test_revocation_overrides_active(root))
    check("every registry entry is git-verifiable", test_git_evidence)

    failed = 0
    for name, passed, detail in checks:
        failed += not passed
        print(f"{'PASS' if passed else 'FAIL'}: {name}" + (f" -- {detail}" if detail else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
