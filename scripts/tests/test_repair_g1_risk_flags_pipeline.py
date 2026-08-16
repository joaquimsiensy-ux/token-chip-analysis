#!/usr/bin/env python3
"""AI-1 F-12：risk_flags 脏字符在 lint、消费与产物层 fail-closed。"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LABELS_DIR = ROOT / "scripts/labels"
sys.path.insert(0, str(LABELS_DIR))

from labels_resolver import BASE_FIELDS, V4_OPTIONAL_FIELDS, LabelResolver  # noqa: E402
from validate_labels import validate_file  # noqa: E402


FIELDS = BASE_FIELDS + V4_OPTIONAL_FIELDS
DIRTY_FLAG = "torna\u200bdo-user"
FAILURES: list[str] = []


def check(name: str, condition: bool, detail="") -> None:
    if condition:
        print(f"ok    {name}")
    else:
        print(f"FAIL  {name}  {detail}")
        FAILURES.append(name)


def label_row(address: str, risk_flags: str) -> dict[str, str]:
    row = dict.fromkeys(FIELDS, "")
    row.update({
        "address": address,
        "chain": "eth",
        "name": "fixture",
        "category": "wallet",
        "tier": "risk" if risk_flags else "identity",
        "source": "fixture",
        "added_date": "2026-08-15",
        "evidence": "fixture evidence",
        "risk_flags": risk_flags,
    })
    return row


def write_labels(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_lint_and_eager_consumer(root: Path) -> None:
    labels = root / "labels-eth.csv"
    write_labels(labels, [
        label_row("0x" + "1" * 40, DIRTY_FLAG),
        label_row("0x" + "2" * 40, "exploit"),
    ])

    try:
        errors, _, count = validate_file(labels)
    except Exception as exc:
        check("F-12 lint 脏行转行级错误且继续扫描", False, repr(exc))
    else:
        dirty_error = any(
            "行2" in item and "risk_flags" in item
            and ("非法字符" in item or "脏字符" in item)
            for item in errors
        )
        check(
            "F-12 lint 脏行转 risk_flags 字符类错误且继续扫描",
            count == 2 and dirty_error,
            (count, errors),
        )

    try:
        LabelResolver("eth", labels_dir=str(root), evm_fallback=False)
    except ValueError:
        eager_rejected = True
    else:
        eager_rejected = False
    check("F-12 LabelResolver 载入脏库即抛 ValueError", eager_rejected)


def test_analyze_holdings_no_partial_artifacts(root: Path) -> None:
    """复制生产脚本字节到临时 app，使默认 labels 根可注入而不写 references。"""
    app = root / "app"
    evm = app / "scripts/evm"
    labels_code = app / "scripts/labels"
    case = root / "case"
    labels_data = app / "references/labels"
    evm.mkdir(parents=True)
    labels_code.mkdir(parents=True)
    case.mkdir()

    for source, destination in (
        (ROOT / "scripts/evm/analyze_holdings.py", evm / "analyze_holdings.py"),
        (ROOT / "scripts/labels/labels_resolver.py", labels_code / "labels_resolver.py"),
        (ROOT / "scripts/labels/risk_flags.py", labels_code / "risk_flags.py"),
    ):
        shutil.copy2(source, destination)

    dirty_address = "0x" + "1" * 40
    write_labels(labels_data / "labels-eth.csv", [label_row(dirty_address, DIRTY_FLAG)])
    (case / "config.json").write_text(
        json.dumps({"decimals": 18, "total_supply_m": 1}), encoding="utf-8")
    (case / "eth_transfers.csv").write_text(
        "block,tx,from,to,value_raw,ts\n"
        f"1,0xtx,{'0x' + '0' * 40},{dirty_address},1000000000000000000,1700000000\n",
        encoding="utf-8",
    )
    product_names = {
        "eth_cex_daily.json",
        "eth_edges.json",
        "eth_key_balances.json",
        "eth_labels_meta.json",
    }
    before = {path.name for path in case.iterdir()}
    proc = subprocess.run(
        [sys.executable, str(evm / "analyze_holdings.py"), "eth", "--eth-csv"],
        cwd=case,
        capture_output=True,
        text=True,
        check=False,
    )
    created_products = sorted(
        path.name for path in case.iterdir()
        if path.name not in before and path.name in product_names
    )
    check(
        "F-12 analyze_holdings 脏库非零退出且不落新产物",
        proc.returncode != 0 and not created_products,
        (proc.returncode, created_products, proc.stdout, proc.stderr),
    )


def test_writer_cli_stable_block(root: Path) -> None:
    additions = root / "dirty-additions.csv"
    write_labels(additions, [label_row("0x" + "3" * 40, DIRTY_FLAG)])
    proc = subprocess.run(
        [sys.executable, str(LABELS_DIR / "add_labels.py"), str(additions), "--dry"],
        cwd=LABELS_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    stderr = proc.stderr or ""
    check(
        "D4 写入侧脏 risk_flags 稳定 BLOCK 且无裸 traceback",
        proc.returncode != 0
        and "BLOCK" in stderr
        and "risk_flags 脏数据" in stderr
        and "Traceback" not in stderr,
        (proc.returncode, proc.stdout, proc.stderr),
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="repair-g1-f12-") as td:
        root = Path(td)
        test_lint_and_eager_consumer(root / "labels")
        test_analyze_holdings_no_partial_artifacts(root / "artifact")
        test_writer_cli_stable_block(root / "writer")
    if FAILURES:
        print(f"FAIL: F-12 pipeline 共 {len(FAILURES)} 项未满足")
        return 1
    print("PASS: F-12 risk_flags lint/consumer/artifact fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
