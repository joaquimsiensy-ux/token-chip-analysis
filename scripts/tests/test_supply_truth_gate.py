#!/usr/bin/env python3
"""supply_truth_gate 离线契约测试（不打网络）：判定纯函数 + stats 字段解析 + 边界。

覆盖：
  1. 精确相等 → PASS
  2. GNT 式静默迁移（重放 10 亿 vs 链上 2.035 亿）→ FAIL
  3. 容差边界：10bps 内 PASS / 外 FAIL
  4. 链上供给为 0 的两种边界
  5. replay_stats 三种字段命名 + 字符串值解析；字段缺失抛 KeyError（上层转 exit 1）
用法：python3 scripts/tests/test_supply_truth_gate.py   退出码 0=PASS / 1=FAIL
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from supply_truth_gate import decide, parse_replay_stats  # noqa: E402

FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
    else:
        print(f"ok    {name}")


def main():
    E18 = 10 ** 18
    # 1. 精确相等
    v, diff, bps = decide(1_000_000 * E18, 1_000_000 * E18)
    check("exact-equal PASS", v == "PASS" and diff == 0 and bps == 0)

    # 2. GNT 式：重放 10 亿 vs 链上 2.035 亿 → FAIL（差 ~39145bps）
    v, diff, bps = decide(1_000_000_000 * E18, 203_500_000 * E18)
    check("gnt-silent-migration FAIL", v == "FAIL" and diff > 0 and bps > 10000)

    # 3. 容差边界（默认 10bps）：9bps 内 PASS，11bps FAIL
    base = 1_000_000 * E18
    v_in, _, _ = decide(base + base * 9 // 10000, base)
    v_out, _, _ = decide(base + base * 11 // 10000, base)
    check("tolerance 9bps PASS", v_in == "PASS")
    check("tolerance 11bps FAIL", v_out == "FAIL")
    # 反向偏差（重放 < 链上，如漏采 mint）同样要拦
    v_neg, _, _ = decide(base - base * 11 // 10000, base)
    check("negative-diff 11bps FAIL", v_neg == "FAIL")

    # 4. 链上供给 0 边界
    v, _, bps = decide(0, 0)
    check("both-zero PASS", v == "PASS" and bps is None)
    v, _, _ = decide(5 * E18, 0)
    check("replay>0 onchain=0 FAIL", v == "FAIL")

    # 5. stats 字段解析：三种命名 + 字符串值
    m, b = parse_replay_stats({"mint_total_wei": "1000", "burn_total_wei": 200})
    check("parse wei-fields", (m, b) == (1000, 200))
    m, b = parse_replay_stats({"mint_total_raw": 500, "burn_total_raw": "50"})
    check("parse raw-fields", (m, b) == (500, 50))
    m, b = parse_replay_stats({"mint_total": 42})  # burn 缺省=0
    check("parse plain-fields burn-default-0", (m, b) == (42, 0))
    try:
        parse_replay_stats({"foo": 1})
        check("parse missing-fields raises", False)
    except KeyError:
        check("parse missing-fields raises", True)

    print("=" * 40)
    if FAILS:
        print(f"{len(FAILS)} 项失败: {FAILS}")
        return 1
    print("supply_truth_gate 契约测试全部通过（11 项）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
