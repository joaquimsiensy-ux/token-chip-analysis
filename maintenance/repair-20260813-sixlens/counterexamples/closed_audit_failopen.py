#!/usr/bin/env python3
"""反例（GPT-F-06）：销户账户覆盖审计不再 fail-open。

可重放场景（mock RPC 失败路径，采集工具本体不联网）：
  ① getMultipleAccounts 批失败 → exit 1 INVALID_SAMPLE（旧版 log+continue 假绿）；
  ② checked=0 且 closed>0 → exit 1（旧版 exit 0 冒充零漏）；
  ③ closed=0 → exit 0 status=NO_CLOSED_SAMPLED（边界显式定案：审计对象为空＝弱结论，
     不是查询失败，也不冒充"销户路径零漏"强证明）；
  ④ 发现漏边 → exit 2 LEAK_FOUND（gate 语义保留）；
  ⑤ 墙钟截断 → exit 1（样本不完整不得冒充完整）。

实现复用 scripts/tests/test_repair_batch_d.py。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts/tests")]

import test_repair_batch_d as batch_d  # noqa: E402


def main() -> int:
    batch_d.t_gptf06_closed_audit()
    if batch_d.FAILS:
        print(f"REPLAY FAIL: {batch_d.FAILS}")
        return 1
    print("REPLAY OK: GPT-F-06 五场景退出码与 status 契约全部对齐")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
