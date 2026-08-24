#!/usr/bin/env python3
"""Run family reconciliation producers and atomically publish their v3 wrapper."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from shared_release_receipt import (RECON_CHECK_KEYS, RECON_PRODUCERS,
                                    canonical_target, chain_family, repo_ref_ok,
                                    validate_reconciliation_check)


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RUNNER_REL = "scripts/report/reconciliation_report.py"
OUTPUT_NAME = "reconciliation_report.json"
OBSERVED_SLOT_PLACEHOLDER = "{observed_as_of_block}"


class RunnerError(ValueError):
    pass


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repo_ref(rel):
    path = repo_ref_ok({"path": rel, "sha256": sha256_file(REPO / rel)}, {rel},
                       "reconciliation")
    return {"path": rel, "sha256": sha256_file(path)}


def case_path(case_dir, rel, *, must_exist=False):
    if not isinstance(rel, str):
        raise RunnerError("case path must be a string")
    rel_path = Path(rel)
    if rel_path.is_absolute() or not rel_path.parts \
            or any(part in {"", ".", ".."} for part in rel_path.parts):
        raise RunnerError(f"case path is not a safe relative path: {rel!r}")
    lexical = case_dir
    for part in rel_path.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise RunnerError(f"case path contains symlink: {rel}")
    path = lexical.resolve()
    try:
        path.relative_to(case_dir)
    except ValueError as exc:
        raise RunnerError(f"case path escapes case_dir: {rel}") from exc
    if must_exist and not path.is_file():
        raise RunnerError(f"input file missing: {rel}")
    return path


def file_ref(case_dir, rel, *, must_exist=True):
    path = case_path(case_dir, rel, must_exist=must_exist)
    if path.is_symlink() or not path.is_file():
        raise RunnerError(f"evidence is not a regular file: {rel}")
    return {"path": rel, "size": path.stat().st_size, "sha256": sha256_file(path)}


def _input_items(raw):
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [(str(name), value) for name, value in raw.items()]
    if isinstance(raw, list):
        return [(str(index), value) for index, value in enumerate(raw)]
    raise RunnerError("inputs must be an object or array")


def snapshot_inputs(case_dir, raw):
    snapshots = {}
    seen_paths = set()
    for name, item in _input_items(raw):
        declared = {"path": item} if isinstance(item, str) else item
        if not isinstance(declared, dict) or not isinstance(declared.get("path"), str):
            raise RunnerError(f"input {name} lacks path")
        current = file_ref(case_dir, declared["path"])
        if current["path"] in seen_paths:
            raise RunnerError(f"duplicate input path: {current['path']}")
        seen_paths.add(current["path"])
        if "size" in declared and declared["size"] != current["size"]:
            raise RunnerError(f"input size mismatch before execution: {current['path']}")
        if "sha256" in declared and declared["sha256"] != current["sha256"]:
            raise RunnerError(f"input hash mismatch before execution: {current['path']}")
        snapshots[name] = current
    return snapshots


def verify_snapshots(case_dir, snapshots, label):
    for snapshot in snapshots.values():
        if file_ref(case_dir, snapshot["path"]) != snapshot:
            raise RunnerError(f"{label} changed during controlled execution: {snapshot['path']}")


def atomic_write_json(path, value):
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    try:
        with tmp.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise


def _base_wrapper(target, family):
    return {
        "schema": "reconciliation-report/v3",
        "family": family,
        "target": target,
        "producer": repo_ref(RUNNER_REL),
        "verdict": "FAIL",
        "exit_code": 2,
        "checks": {},
    }


def _resolve_case_dir(spec, base_dir):
    if not isinstance(spec, dict):
        raise RunnerError("job spec must be a JSON object")
    raw_case_dir = spec.get("case_dir")
    if not isinstance(raw_case_dir, str) or not raw_case_dir.strip():
        raise RunnerError("case_dir is required")
    case_dir = Path(raw_case_dir).expanduser()
    if not case_dir.is_absolute():
        case_dir = base_dir / case_dir
    case_dir = case_dir.resolve()
    if not case_dir.is_dir():
        raise RunnerError(f"case_dir is not a directory: {case_dir}")
    return case_dir


def _validate_spec(spec, case_dir):
    if "family" in spec:
        raise RunnerError("family 不接受外部声明；必须由 target.chain 推导")
    target = spec.get("target")
    derive_as_of = spec.get("derive_as_of_from")
    try:
        family = chain_family(target.get("chain") if isinstance(target, dict) else None)
    except ValueError as exc:
        raise RunnerError(str(exc)) from exc
    dynamic_solana = family == "solana" and derive_as_of == "supply"
    if derive_as_of is not None and not dynamic_solana:
        raise RunnerError("derive_as_of_from is only supported as solana/supply")
    if not isinstance(target, dict) or set(target) != {"chain", "token", "as_of_block"} \
            or not target.get("chain") or not target.get("token") \
            or (target.get("as_of_block") is None and not dynamic_solana) \
            or (target.get("as_of_block") is not None and (
                isinstance(target.get("as_of_block"), bool)
                or not isinstance(target.get("as_of_block"), int)
                or target["as_of_block"] < 0)):
        raise RunnerError("target must contain exactly chain/token/as_of_block")
    checks = spec.get("checks")
    check_keys = RECON_CHECK_KEYS[family]
    if not isinstance(checks, dict) or tuple(checks) != check_keys:
        raise RunnerError(f"checks must contain exactly, in order, {list(check_keys)}")
    prepared = {}
    receipt_paths = set()
    for key in check_keys:
        item = checks[key]
        if not isinstance(item, dict):
            raise RunnerError(f"check {key} must be an object")
        producer = item.get("producer")
        if not isinstance(producer, str) or producer not in RECON_PRODUCERS[family][key]:
            raise RunnerError(f"check {key} producer is not whitelisted: {producer!r}")
        producer_ref = repo_ref(producer)
        argv = item.get("argv")
        receipt = item.get("receipt")
        if not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv):
            raise RunnerError(f"check {key} argv must be a string array")
        if not isinstance(receipt, str) or receipt not in argv:
            raise RunnerError(f"check {key} receipt path must appear verbatim in argv")
        receipt_path = case_path(case_dir, receipt)
        if receipt_path.exists():
            raise RunnerError(f"check {key} receipt pre-exists: {receipt}")
        if receipt in receipt_paths:
            raise RunnerError(f"duplicate receipt path: {receipt}")
        receipt_paths.add(receipt)
        prepared[key] = {
            "producer": producer, "producer_ref": producer_ref,
            "argv": list(argv), "receipt": receipt,
        }
    if dynamic_solana:
        if OBSERVED_SLOT_PLACEHOLDER in prepared["supply"]["argv"]:
            raise RunnerError("supply producer cannot consume the slot it must observe")
        for key in ("balance", "supply_truth", "time", "exact_reconcile"):
            if OBSERVED_SLOT_PLACEHOLDER not in prepared[key]["argv"]:
                raise RunnerError(
                    f"dynamic solana check {key} must consume {OBSERVED_SLOT_PLACEHOLDER}")
    inputs = snapshot_inputs(case_dir, spec.get("inputs"))
    return family, case_dir, dict(target), prepared, inputs, dynamic_solana


def run_job(spec, *, base_dir=None):
    base_dir = Path(base_dir or Path.cwd()).resolve()
    case_dir = _resolve_case_dir(spec, base_dir)
    wrapper = None
    receipt_snapshots = {}
    try:
        family, case_dir, target, checks, inputs, dynamic_solana = _validate_spec(spec, case_dir)
        wrapper = _base_wrapper(target, family)
        if inputs:
            wrapper["inputs"] = inputs
        order = RECON_CHECK_KEYS[family]
        for key in order:
            item = checks[key]
            argv = list(item["argv"])
            if dynamic_solana and key != "supply":
                observed_slot = target.get("as_of_block")
                if not isinstance(observed_slot, int):
                    raise RunnerError("Solana observed slot was not adopted from supply producer")
                argv = [str(observed_slot) if arg == OBSERVED_SLOT_PLACEHOLDER else arg
                        for arg in argv]
            if OBSERVED_SLOT_PLACEHOLDER in argv:
                raise RunnerError(f"unresolved observed slot placeholder in check {key}")
            proc = subprocess.run(
                [sys.executable, str(REPO / item["producer"]), *argv],
                cwd=case_dir, capture_output=True, text=True,
            )
            result = {
                "status": "FAIL", "exit_code": proc.returncode,
                "process_exit_code": proc.returncode,
                "producer": item["producer_ref"],
            }
            wrapper["checks"][key] = result
            if proc.returncode != 0:
                raise RunnerError(f"check {key} producer exited {proc.returncode}")
            receipt_ref = file_ref(case_dir, item["receipt"])
            try:
                receipt = json.loads(
                    case_path(case_dir, item["receipt"], must_exist=True)
                    .read_text(encoding="utf-8")
                )
            except Exception as exc:
                raise RunnerError(f"check {key} receipt JSON invalid: {exc}") from exc
            result.update({
                "status": receipt.get("verdict"),
                "exit_code": receipt.get("exit_code"),
                "receipt": receipt_ref,
            })
            receipt_snapshots[key] = receipt_ref
            if dynamic_solana and key == "supply":
                observed_target = receipt.get("target")
                if (not isinstance(observed_target, dict)
                        or set(observed_target) != {"chain", "token", "as_of_block"}
                        or canonical_target(observed_target)
                        != canonical_target({**target,
                                             "as_of_block": observed_target.get("as_of_block")})
                        or isinstance(observed_target.get("as_of_block"), bool)
                        or not isinstance(observed_target.get("as_of_block"), int)
                        or observed_target["as_of_block"] < 0):
                    raise RunnerError("supply receipt did not provide a valid observed target")
                target = dict(observed_target)
                wrapper["target"] = dict(target)
            if receipt.get("target") != target:
                raise RunnerError(f"check {key} receipt target mismatch")
            if receipt.get("verdict") != "PASS" or receipt.get("exit_code") != 0:
                raise RunnerError(f"check {key} receipt is not PASS/0")
            verify_snapshots(case_dir, inputs, "input")
        verify_snapshots(case_dir, inputs, "input")
        verify_snapshots(case_dir, receipt_snapshots, "receipt")
        wrapper["verdict"] = "PASS"
        wrapper["exit_code"] = 0
    except Exception as exc:
        if wrapper is None:
            target = spec.get("target") if isinstance(spec, dict) else None
            family = None
            try:
                family = chain_family(target.get("chain")) if isinstance(target, dict) else None
            except ValueError:
                pass
            wrapper = _base_wrapper(target if isinstance(target, dict) else {}, family)
        wrapper["verdict"] = "FAIL"
        wrapper["exit_code"] = 2
        wrapper["error"] = str(exc)

    output = case_dir / OUTPUT_NAME
    try:
        atomic_write_json(output, wrapper)
    except Exception as exc:
        print(f"BLOCK: reconciliation wrapper publish failed: {exc}", file=sys.stderr)
        return 2
    return 0 if wrapper["verdict"] == "PASS" else 2


def reseal_evm(old_wrapper_path):
    """Deeply revalidate an EVM v2 wrapper's four receipt files and reseal v3."""
    old_wrapper_path = Path(old_wrapper_path).resolve()
    case_dir = old_wrapper_path.parent
    old = json.loads(old_wrapper_path.read_text(encoding="utf-8"))
    if old.get("schema") != "reconciliation-report/v2":
        raise RunnerError("--reseal 只接受旧 reconciliation-report/v2 wrapper")
    checks = old.get("checks")
    if not isinstance(checks, dict) or set(checks) != set(RECON_CHECK_KEYS["evm"]):
        raise RunnerError("EVM 旧 wrapper 必须含四份 receipt 引用")
    rebuilt = {}
    observed_target = None
    for key in RECON_CHECK_KEYS["evm"]:
        old_item = checks.get(key)
        ref_value = old_item.get("receipt") if isinstance(old_item, dict) else None
        if not isinstance(ref_value, dict) or not isinstance(ref_value.get("path"), str):
            raise RunnerError(f"旧 wrapper {key} receipt 引用缺失")
        receipt_ref = file_ref(case_dir, ref_value["path"])
        receipt = json.loads(case_path(
            case_dir, receipt_ref["path"], must_exist=True).read_text(encoding="utf-8"))
        target = canonical_target(receipt.get("target"))
        if observed_target is None:
            observed_target = target
        elif target != observed_target:
            raise RunnerError("旧 wrapper 四份 receipt target 不一致")
        if chain_family(target["chain"]) != "evm":
            raise RunnerError("--reseal 仅允许 EVM 家族")
        old_producer = old_item.get("producer") if isinstance(old_item, dict) else {}
        producer = old_producer.get("path") if isinstance(old_producer, dict) else None
        if producer not in RECON_PRODUCERS["evm"][key]:
            raise RunnerError(f"旧 wrapper {key} producer 不在 EVM 白名单")
        item = {"status": receipt.get("verdict"), "exit_code": receipt.get("exit_code"),
                "process_exit_code": 0, "producer": repo_ref(producer),
                "receipt": receipt_ref}
        validate_reconciliation_check(case_dir, key, item, observed_target, "evm")
        rebuilt[key] = item
    wrapper = _base_wrapper(observed_target, "evm")
    wrapper["checks"] = rebuilt
    wrapper["verdict"] = "PASS"
    wrapper["exit_code"] = 0
    atomic_write_json(case_dir / OUTPUT_NAME, wrapper)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("job_spec", nargs="?", type=Path)
    group.add_argument("--reseal", type=Path, metavar="OLD_WRAPPER")
    args = parser.parse_args(argv)
    try:
        if args.reseal is not None:
            return reseal_evm(args.reseal)
        spec_path = args.job_spec.resolve()
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        return run_job(spec, base_dir=spec_path.parent)
    except Exception as exc:
        parser.exit(2, f"BLOCK: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
