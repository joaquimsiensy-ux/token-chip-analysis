#!/usr/bin/env python3
"""反例（F-07）：多 manifest 迁移必须全有或全无——字节回滚原样，不是"报错干净"。

可重放场景（真 Parquet 太古 run ×2，注入点按 os.replace 调用序精确定位）：
  ① 绿例：双 run 正常迁移全升 v3；
  ② 第二个 done 提交时注入 OSError → 断言**两个 done.json 字节与注入前逐字节相同**
     ＋无 .refresh-tmp/.refresh-bak/.recover 残留＋CLI exit 2（原反例：旧版留下
     run_1=v3、run_2=legacy 的混合状态）；
  ③ 提交失败且回滚也失败 → 保留 .recover 恢复件＋exit 1；
  ④ 只读目录令 ensure_outdir_identity 抛 OSError → CLI exit 2 不裸 traceback。

实现复用 scripts/tests/test_repair_batch_d.py。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts/tests")]

import test_repair_batch_d as batch_d  # noqa: E402


def main() -> int:
    batch_d.t_f07_refresh_transaction()
    if batch_d.FAILS:
        print(f"REPLAY FAIL: {batch_d.FAILS}")
        return 1
    print("REPLAY OK: F-07 注入后字节回滚原样，回滚失败保留恢复件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
