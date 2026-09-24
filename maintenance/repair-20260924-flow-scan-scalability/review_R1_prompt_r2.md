# 工单 R1 复核提示词 r2（只读）

## 纪律
同 r1：禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**。首行固定 `# 工单R1复核r2：通过` 或 `# 工单R1复核r2：退回`。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（含 `634c083`）。

## 任务
复核 `maintenance/repair-20260924-flow-scan-scalability/workorder_R1.md`（v2）。它声称全部采纳你 r1 的意见（`review_R1_reply_r1.md`）。逐条核：
a) r1 汇总表 10 项每一项在 v2 中的落地文本是否准确、无遗漏、无引入新矛盾（逐项对照，给出行号）。
b) 新增内容亲核：①1.3 elig 空集插 `''` 的兼容是否与基线 `IN ('')` 在 sink 预筛、sink 候选行两处都等价（`sink_edges` 物化用 `f IN (SELECT addr FROM elig)`，elig 为 `{''}` 时与基线 `f IN ('')` 是否同样只匹配空地址；`attach_duckdb` 路径下若存在空地址行会怎样）；②2.1(b) 的 `presink` CTAS 与 `sink_edges`/`sink_net` 定义是否与 r1 建议一致；`pre_sinks` 遍历顺序改为读临时表后，与基线 `GROUP BY` 结果顺序的关系（两者都无 ORDER BY，均属基线未规定顺序——是否需要在 1.1 明写"候选遍历顺序不在等价承诺内，只影响同排序键并列项"）；③1.5 关于 `preserve_insertion_order` 与 CTAS `ORDER BY` 的说法在 DuckDB 1.5.4 下是否成立（可用内存微实验验证：`SET preserve_insertion_order=false` 后 `CREATE TEMP TABLE x AS SELECT ... ORDER BY c` 的物理顺序是否保留；若不保留，工单给的"CTAS 前后临时切换"是否有效，或应改用什么写法）；④2.2 第 17 例的数值断言与生产公式（`round(x * 100.0 / total, 4)`、`qualified_in` 只含合格来源）是否一致，`TinySrc` 是否确实不会成为合格地址（峰值 <0.02% 且不被 `first_meaningful` 等逻辑纳入 `eligible`），5 来源是否达 `sink_min_sources=5`，20 收方 10^9 是否达 pulse 双线（2% 与 20 fresh）——按 TOTAL 常量核；⑤0.7 EVM 夹具写法引用 `test_lit_regression_f008.py:74` 是否准确可行（列名/编码/timestamp 字段），`--duckdb` 微夹具的零值/负值边在 `attach_duckdb` 下的行为是否如工单预期。
c) 行数预算 ≤110 与 ≤2 helper 在 v2 全部要求（资源日志、阶段释放、保序切换、docstring）下是否仍够；若不够给出建议数字。
d) 是否还有未覆盖的等价性风险或资源风险（一句话列出，无则明说）。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文，含行号）＋ 汇总表。
