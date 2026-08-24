# F-007 盲审 verdict（round 2，codex fresh 只读，2026-08-24）

VERDICT: PASS

1. 盲审 round1 最小清单五条逐条闭合：stack_exempt_for("sol-anchor-rows") 返回空集（camp_series_provenance.py:75-84）；anchor 含 burn_cum_pct 显式拒（:371-381）；anchor oracle 改真实形态（100 绿 test_lit_regression_f007.py:200-203 / 125 红 :206-211 / burn_cum_pct 拒 :214-223）；文档依据分家（模块说明 :27-37、映射 :55-84、闭合说明 :324-353 均以 build_evolution.py:177-183 证 anchor，不再用 replay_edges.py 代证）；绿证重建 15/15 PASS＋五组定向回归 EXIT_CODE=0（f007_green_evidence.txt:3-536）。
2. round1 已通过六项无回退：EVM 主修复、sol-rows 豁免、手填 dual 逐字不变、hunk 归属、红证不动（f007_red_evidence.txt 修改时间早于 round1 verdict）、七个禁改文件＋build_evolution.py diff 均为空；state_from_facts.py 本轮未再动（文件时间戳佐证）。
3. f007_done.md round2 增补节与 diff 一致，round1 原文未改写（追加式纠正结构成立）。

限制声明（盲审原文）：档案未入 git 无 round1 哈希，无法密码学证明历史正文未动，但正文结构/交叉引用/文件元数据均支持追加式返工，无实质矛盾。本轮未执行测试，结论基于只读审查。
