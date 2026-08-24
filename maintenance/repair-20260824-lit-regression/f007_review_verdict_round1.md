# F-007 盲审 verdict（round 1，codex fresh 只读，2026-08-24）

VERDICT: BLOCK

阻断缺陷（唯一）：sol-anchor-rows 豁免映射错误。工单第 29 行把它与 sol-rows 一起列为 burn 豁免格式，但真实生产端 build_evolution.py:177-183 把「锁仓/销毁」写进 camp_raw、计入 known、全桶除以 TOT 输出——即「锁仓/销毁」实际参与 total-supply 堆叠。当前实现 camp_series_provenance.py:76 将它排除，真实形态 40+35+25=100 会按 40+35=75 被误拒。done 报告用 replay_edges.py 的语义证明另一个 producer，anchor 绿例 40+60+25=125 是生产端不会产生的形态（oracle 错误）。

其余六节全部通过：EVM 主体修复正确（豁免仅 burn_cum_pct、endpoint spec_sum 计入、legacy 拒 burn_cum_pct）、sol-rows 正确保持豁免、手填 dual 逐字不变、hunk 全部有归属、红绿证据静态自洽、七个禁改文件 diff 为空。

必须返工的最小清单（原文）：
1. 先为 F007 工单补事实勘误：sol-anchor-rows 不得照搬 sol-rows 豁免语义。
2. stack_exempt_for("sol-anchor-rows") 不应豁免「锁仓/销毁」；最小实现可返回空豁免集，并对 producer 不会输出的 burn_cum_pct 明确决定为拒绝。
3. 将 anchor 测试改为真实形态：例如 40+35+25=100 必须绿；40+60+25=125 必须红。
4. 同步模块 docstring、validate_series_payload() 文档和 f007_done.md，不得再用 replay_edges.py 证明 build_evolution.py 的语义。
5. 重新生成 F007 绿证，并重跑原 12 项及工单指定的五组定向回归；无需触碰任何禁改文件。

调度记录：本缺陷源头=调度方工单第 29 行（计划 §1 不变量把 sol-anchor-rows 与 sol-rows 归并为一族，未核 build_evolution.py），属工单事实错误，非施工方违纪；施工方未独立核实 anchor 生产端亦有责任（工单第一步"不盲信"条款）。返工工单=f007_rework_workorder.md。
