#!/usr/bin/env python3
"""Run the fixed case-local reproduce_audit.py entry and emit a bound receipt.

This is the only supported receipt generator.  It does not accept a shell command or an
alternate executable: claims may retain reproduce_command as prose, but the release gate
trusts only this receipt and re-hashes every bound file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def atomic_json(path, obj):
    tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def inside(case_dir, rel, label):
    raw = case_dir / rel
    if Path(rel).is_absolute() or ".." in Path(rel).parts or raw.is_symlink():
        raise ValueError(f"{label} 路径非法: {rel}")
    path = raw.resolve()
    path.relative_to(case_dir)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case_dir", type=Path)
    ap.add_argument("--output", default="reproduce_output.json")
    ap.add_argument("--receipt", default="reproduce_receipt.json")
    ap.add_argument("script_args", nargs=argparse.REMAINDER,
                    help="传给固定 reproduce_audit.py 的参数（可在 -- 之后填）")
    a = ap.parse_args(argv)
    case_dir = a.case_dir.resolve()
    if not case_dir.is_dir():
        print(f"ERROR: 案目录不存在: {case_dir}", file=sys.stderr)
        return 1
    try:
        entry = inside(case_dir, "reproduce_audit.py", "固定入口")
        manifest = inside(case_dir, "audit_input_manifest.json", "输入 manifest")
        output = inside(case_dir, a.output, "输出")
        receipt_path = inside(case_dir, a.receipt, "receipt")
        if not entry.is_file() or not manifest.is_file():
            raise ValueError("缺 reproduce_audit.py 或 audit_input_manifest.json")
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    script_args = list(a.script_args)
    if script_args[:1] == ["--"]:
        script_args = script_args[1:]
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    proc = subprocess.run([sys.executable, str(entry)] + script_args, cwd=case_dir,
                          capture_output=True)
    output_meta = None
    summary_hash = None
    output_error = None
    if output.is_file():
        try:
            parsed = json.loads(output.read_text(encoding="utf-8"))
            summary = parsed.get("summary") if isinstance(parsed, dict) and "summary" in parsed \
                else parsed
            summary_hash = canonical_json_sha(summary)
            output_meta = {"path": str(output.relative_to(case_dir)),
                           "size": output.stat().st_size, "sha256": sha256_file(output)}
        except Exception as exc:
            output_error = f"输出不是可摘要 JSON: {exc}"
    else:
        output_error = f"输出不存在: {output.relative_to(case_dir)}"
    passed = proc.returncode == 0 and output_meta is not None and output_error is None
    receipt = {"schema": "reproduce-receipt/v1",
               "status": "PASS" if passed else "BLOCK", "exit_code": proc.returncode,
               "run_at_utc": started,
               "entrypoint": {"path": "reproduce_audit.py", "sha256": sha256_file(entry)},
               "input_manifest": {"path": "audit_input_manifest.json",
                                  "sha256": sha256_file(manifest)},
               "args": script_args, "output": output_meta, "summary_sha256": summary_hash,
               "stdout_sha256": hashlib.sha256(proc.stdout).hexdigest(),
               "stderr_sha256": hashlib.sha256(proc.stderr).hexdigest(),
               "error": output_error}
    atomic_json(receipt_path, receipt)
    print(f"[{receipt['status']}] reproduce receipt -> {receipt_path}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
