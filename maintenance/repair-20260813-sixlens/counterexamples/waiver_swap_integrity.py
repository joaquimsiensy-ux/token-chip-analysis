#!/usr/bin/env python3
"""反例：supply truth 生成后，原地掉包它已经绑定的 tolerance waiver。

收据自身一个字节都不动，只把案根里那份 waiver.json 换成另一份结构自洽、
内容不同的 waiver，看发布校验器还认不认。两个场景：

  A 变长替换：批准容差放大到 20000bps、理由改文 —— 文件长度跟着变了，
    三验里 size 一项先命中。
  B 等长替换：只把理由里一个汉字换成同宽度的另一个汉字 —— 字节数分毫不差，
    size 一项完全看不出破绽，只能靠 sha256 拦下。

B 是 A 的边界外一步：没有它，这道防线看起来成立，其实可能只是"长度恰好变了"
的侥幸。两条都拒绝，才说明绑定校验真的落在内容上。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts/tests")]

import test_repair_batch_a as fixture  # noqa: E402


SIZE_BRANCH = "input tolerance_waiver size mismatch"
HASH_BRANCH = "input tolerance_waiver hash mismatch"


def longer_reason(body):
    """把批准容差放大、理由改写——文件必然变长。"""
    body["reason"] = "特殊迁移币经第二轮人工核对，现批准更大的供给真值容差。"


def equal_length_reason(body):
    """只换一个同宽度的汉字：内容变了，字节数没变。"""
    original = body["reason"]
    swapped = original.replace("已", "经", 1)
    if swapped == original:
        swapped = original[:-1] + "！"
    assert swapped != original, original
    assert len(swapped.encode("utf-8")) == len(original.encode("utf-8")), swapped
    body["reason"] = swapped


def swap_and_validate(root: Path, mutate, *, approved=10000):
    """跑通合法 producer，再原地掉包 waiver，返回 (掉包后大小, 收据登记大小, 拒绝原文)。"""
    (root / "replay_stats.json").write_text(
        json.dumps({"mint_total_raw": "1", "burn_total_raw": "0"}),
        encoding="utf-8",
    )
    waiver = fixture.write_waiver(root)
    rc, receipt, stderr = fixture.run_supply(root, waiver=waiver)
    assert rc == 0 and receipt["verdict"] == "PASS", (rc, receipt, stderr)

    supply_path = root / "supply_truth.json"
    original_supply = supply_path.read_bytes()
    bound = dict(receipt["inputs"]["tolerance_waiver"])

    # 掉包：新 waiver 内部的 replay_stats/evidence 引用仍指向磁盘实物，自身结构自洽。
    fixture.write_waiver(root, approved=approved, mutate=mutate)
    assert supply_path.read_bytes() == original_supply, "收据本身必须保持原样"
    assert fixture.sha256(waiver) != bound["sha256"], "掉包后的 waiver 内容必须确实不同"

    # wrapper 按当前实物重建 supply_truth.json 的 size/sha，堵死"外层哈希先炸"的捷径。
    item = {
        "status": "PASS",
        "exit_code": 0,
        "receipt": {
            "path": "supply_truth.json",
            "size": supply_path.stat().st_size,
            "sha256": fixture.sha256(supply_path),
        },
    }
    try:
        fixture.shared.validate_reconciliation_check(
            root, "supply_truth", item, fixture.TARGET, "evm")
    except ValueError as exc:
        return waiver.stat().st_size, bound["size"], str(exc)
    raise AssertionError("共享发布校验器放行了生成后被替换的 tolerance waiver")


def main() -> int:
    with tempfile.TemporaryDirectory(
            prefix="batch-a-waiver-swap-a-", dir="/private/tmp") as raw:
        size, bound_size, error = swap_and_validate(
            Path(raw), longer_reason, approved=20000)
        assert size != bound_size, (size, bound_size)
        assert SIZE_BRANCH in error, error
        print(f"[A 变长替换 {bound_size}→{size} 字节] {error}")

    with tempfile.TemporaryDirectory(
            prefix="batch-a-waiver-swap-b-", dir="/private/tmp") as raw:
        size, bound_size, error = swap_and_validate(Path(raw), equal_length_reason)
        assert size == bound_size, ("等长场景没构造成等长", size, bound_size)
        assert HASH_BRANCH in error, error
        print(f"[B 等长替换 {bound_size}={size} 字节] {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
