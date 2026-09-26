# 工单 W1 复核提示词（只读 codex）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260925-replay-only-addrs-scale/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`、`/Volumes`；不得进入 `/Users/uravvv/.claude/skills/token-chip-analysis`（另一工程在用）。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**（不要只 print 到 stdout）。首行固定 `# 工单W1复核：通过` 或 `# 工单W1复核：退回`。工作目录＝`/Users/uravvv/.claude/worktrees/tca-only-addrs`（分支 `fix/replay-only-addrs-scale`，基线 `8457f70`）。

## 任务
复核 `maintenance/repair-20260925-replay-only-addrs-scale/workorder_W1.md`（v1）。逐条审：
a) 锚与行号：`replay_duck.py:89/:159-161/:165-185/:188-192/:334/:376-417/:635/:646/:655-664/:666/:671/:681-685`、`audit_release_gate.py:1192-1235`、`test_engine_equivalence.py:45/:83/:143/:236/:318-321`、`CHANGELOG.md:13/:106`、`SKILL.md:23`、`pyproject.toml:15`、`VERSION` 是否与工单事实段①-⑦一致（整行 `grep -n -F -x` 复验，报出不符处的实际行号与原文）。
b) 等价性论证亲核：①"按块区间分段的段内 `(tag,tx,li)` 冲突查重与去重 ≡ 全局"是否成立，前提（同键只在同一区块）在 v2 parquet（`_v2_select`）与 v1csv 两种读取下是否都有保证；若同一 tx 因数据损坏出现在两个区块，基线全局查重会怎样、分段版会怎样——工单是否如实写明了该差异并给出可接受理由；②"先过滤（frm/t2 ∈ 并集）后 `GROUP BY tag,tx,li`"与"先去重后过滤"是否严格等价（含重复行 frm/t2 不同但被冲突查重拦下的情形）；③段内 `(a,b,dd)` 聚合与 `_create_deltas_view`+`:385-387` 的口径（mint 不减 Z、burn 照加、`frm <> Z`）是否逐条相同；④`ab` 表在分段版里 `(a,b)` 是否可能跨段重复（若可能，峰值 SQL `:391` 的 `SUM(dd) OVER (PARTITION BY a ORDER BY b)` 在同 `(a,b)` 多行时是否仍正确、是否需要最终 `GROUP BY a,b` 合并）；⑤`maxlen` 从 `raw_rows` VIEW 取 与 从 `events` 取 是否同值（重复行不影响 MAX）。
c) 修法定形：把 `raw_rows` 改 VIEW 后，每段的 `WHERE b >= s0 AND b < s1` 能否下推到 `read_parquet`/`read_csv`（DuckDB 1.5.4 对 UNION ALL VIEW 上的谓词下推行为），还是每段都会全量扫一遍 parquet（若是，K 段=K 次全扫，7 GB parquet × 22 段的 IO 代价是否可接受、有无更省的分段法，如按 `run_*` 目录分段或先把过滤后的窄行物化一次）；`ANY_VALUE` 段内 GROUP BY 的内存量级评估；1.5 的 `SEG_ROWS=5_000_000` 与 `K` 公式是否合理；1.7 的 ≤140 行/≤3 helper 是否够；`followup_peaks` 新增参数的传法（工单 2.1(c)2 允许的两种写法）哪种更小。
d) 0.7/0.8 证据设计是否足以证明 1.1-1.4（重复行、冲突行落在首尾段、零事件地址、Z/DEAD 作地址、v2 与 v1csv 双格式、全量路径字节不变）；沙箱可行性（≥2,000,000 行夹具的生成时间与磁盘、`timeout=120` 是否够，建议具体规模与超时值）。
e) 测试：2.2 新例是否可构造且最小；`_write_v2_inputs` 是否支持多 `run_*` 目录与 receipt（若不支持，给出最小扩展写法或改用单目录的理由）；`CHIP_REPLAY_SEG_ROWS` 非法值的 fail-closed 判定位置。
f) 回归面：`grep -rn` 证明哪些测试/脚本调用 `followup_peaks`/`build_events`/`_create_deltas_view`（签名变化影响）；`invariant_scan`/`test_batch4_invariant_guards`/AST 守卫是否对 `replay_duck.py` 结构改动报警；发布闸 `producer.sha256` 绑定意味着合并后案卷必须用新脚本重跑（工单是否写明）。
g) 原则与档位：references/commands 0 B、SKILL 仅版本号；9.2.2 记"修"是否恰当（契约不变、纯性能）。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文，含行号）＋ 汇总表。
