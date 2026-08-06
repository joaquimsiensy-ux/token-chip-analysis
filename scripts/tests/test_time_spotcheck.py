#!/usr/bin/env python3
"""time_spotcheck 契约测试（离线，--dry-run 黑盒；不打网）。

覆盖（A2 时间抽查执行器的 fail-closed 反例集，6.7.0）：
  1. 两型分型正确：balance 型（matrix+净变动+边缘）与 tx 型（最大单笔/交界块）计数分明
  2. 0 锚点 → assert 硬失败（GMX 案"0 点假 PASS"教训的机器化）
  3. 两型都不匹配的锚点（格式漂移）→ exit 非 0
  4. 边缘点缺 day_end_block 且未传 --final-block → exit 非 0（禁静默跳点）
  5. 非 dry-run 缺 --rpc → exit 非 0
用法：python3 scripts/tests/test_time_spotcheck.py   退出码 0=PASS / 1=FAIL
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "lib", "time_spotcheck.py")
FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
    else:
        print(f"ok    {name}")


def run(args):
    return subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True)


def wj(d, name, obj):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    return p


def main():
    d = tempfile.mkdtemp(prefix="spotcheck_test_")
    out = os.path.join(d, "out.json")
    token = "0x594daad7d77592a2b97b725a7ad59d7e188b5bfa"
    base = ["--chain", "bsc", "--token", token, "--out", out]

    # 1. 两型分型（2 matrix balance + 1 净变动 balance + 1 边缘 balance + 2 tx 型）
    plan = wj(d, "plan.json", {
        "chain": "bsc", "token": token,
        "matrix_points": [
            {"kind": "矩阵[早·大户]", "addr": "0xaa", "day": "2025-01-01",
             "day_end_block": 100, "expected_balance_raw": "123"},
            {"kind": "矩阵[晚·小户]", "addr": "0xbb", "day": "2025-06-01",
             "day_end_block": 200, "expected_balance_raw": "456"}],
        "forced_points": [
            {"kind": "最大单日净变动地址-日", "addr": "0xcc", "day": "2025-03-01",
             "day_end_block": 150, "expected_balance_raw": "789"},
            {"kind": "门槛±10% 边缘地址", "addr": "0xdd", "day": "2025-06-30",
             "expected_balance_raw": "999"},
            {"kind": "全史最大单笔转账", "tx": "0xt1", "from": "0xaa", "to": "0xbb",
             "block": 120, "expected_value_raw": "111"},
            {"kind": "交界块 130 前最近转账", "tx": "0xt2", "from": "0xcc", "to": "0xdd",
             "block": 130, "expected_value_raw": "222"}]})
    p = run(["--plan", plan, "--dry-run", "--final-block", "300"] + base)
    ok = p.returncode == 0
    if ok:
        st = json.loads(p.stdout.strip().splitlines()[-1])
        ok = st["balance_points"] == 4 and st["tx_points"] == 2 and st["need_final_block"] == 1
    check("两型分型正确（balance 4 / tx 2 / 边缘缺块 1）", ok)

    # 2. 0 锚点硬失败
    p = run(["--plan", wj(d, "empty.json", {"chain": "bsc", "token": token,
                                              "matrix_points": [], "forced_points": []}),
             "--dry-run"] + base)
    check("0 锚点 assert 硬失败", p.returncode != 0)

    # 3. 格式漂移锚点（两型都不匹配）
    p = run(["--plan", wj(d, "odd.json", {"chain": "bsc", "token": token, "matrix_points": [
        {"kind": "怪点", "addr": "0xee", "day": "2025-01-01"}], "forced_points": []}),
        "--dry-run"] + base)
    check("格式漂移锚点 exit 非 0", p.returncode != 0)

    # 4. 边缘点缺 day_end_block 且未传 --final-block
    p = run(["--plan", plan, "--dry-run"] + base)
    check("边缘点缺块未传 --final-block exit 非 0", p.returncode != 0)

    # 5. 非 dry-run 缺 --rpc
    p = run(["--plan", plan, "--final-block", "300"] + base)
    check("非 dry-run 缺 --rpc exit 非 0", p.returncode != 0)

    print("=" * 40)
    if FAILS:
        print(f"time_spotcheck 契约测试 {len(FAILS)} 项失败")
        return 1
    print("time_spotcheck 契约测试全部通过（5 项）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
