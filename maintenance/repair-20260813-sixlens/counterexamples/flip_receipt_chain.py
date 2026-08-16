#!/usr/bin/env python3
"""反例（F-06）：翻转裁决收据链——旧口子已死、新收据不可绕。

可重放场景（全部真跑 entity_source_trace 的双来源翻转最小案）：
  ① 真实翻转、无收据 → exit 2（阻断保留）；
  ② 6.39.4 旧串格式 `ENTITY:ANCHOR:十个字符` → exit 2（原审查者的最小反例，翻案后失效）；
  ③ 合法收据（指纹＋披露与明细重算相等）→ exit 0 放行；
  ④ 底层数据改一笔金额、旧收据原样 → 指纹失配 exit 2（收据自动失效必须重裁）；
  ⑤ 收据行指向不存在的翻转锚点 → exit 2（不许预防性豁免）；
  另含 freeze 端 recompute 的同源重验与 A5 报告实文披露核对两段。

实现复用 scripts/tests/test_repair_batch_d.py 的同名函数（先例：waiver_swap_integrity.py）。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts/tests")]

import test_repair_batch_d as batch_d  # noqa: E402


def main() -> int:
    batch_d.t_f06_trace_receipt_chain()
    batch_d.t_f06_receipt_unit_negatives()
    batch_d.t_f06_a5_disclosure()
    if batch_d.FAILS:
        print(f"REPLAY FAIL: {batch_d.FAILS}")
        return 1
    print("REPLAY OK: F-06 全部反例被拒、绿例放行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
