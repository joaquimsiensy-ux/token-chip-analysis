# 工单 W1 复核提示词 r3（只读 codex）——复核 v3

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260925-replay-only-addrs-scale/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`、`/Volumes`；不得进入 `/Users/uravvv/.claude/skills/token-chip-analysis`（另一工程在用）。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**。首行固定 `# 工单W1复核r3：通过` 或 `# 工单W1复核r3：退回`。工作目录＝`/Users/uravvv/.claude/worktrees/tca-only-addrs`（分支 `fix/replay-only-addrs-scale`，基线 `8457f70`）。

## 背景
`workorder_W1.md` 现为 v3，逐条吸收了 r2（`review_W1_reply_r2.md`）的全部意见：`kept_rows` 改用 `build_events` 逐通道保留行 COUNT 之和（`acc["_kept_rows"]`）；桶内"行数+冲突查重"合并为一条查询；1.6 按实际源查询次数登记；夹具计数定型（2,000,000 含 1,000 复制 / 280+20=300、K=6）；provenance 差异口径；执行路径证据；1.2 K=1 限定；首桶/末桶/空桶/偏斜/v1 NULL 行反例；默认 500 万桶资源证据要求；manifest 位置；`_run` 14 处；`_write_v2_inputs` 改法与 Python 期望值口径；0.6 只读环境说明。r1 的方案性问题（块区间→哈希分桶）已在 v2 解决并经 r2 亲核通过。本轮请**重新完整判定**，不沿用 r1/r2 结论。

## 任务
a) **r2 意见落地核对**：对照 r2 汇总表 10 行与正文各"建议替换"，逐条核 v3 是否落地（给出 v3 对应条款号）；未落地或落地走样的列出原文与建议替换文本。重点：1.5 `kept_rows` 来源与 2.1(a)/(b) 的 `acc["_kept_rows"]` 传递是否自洽；2.1(c) 合并查询是否与 r2 给出的 SQL 语义一致（返回桶行数与冲突键数）；1.6 措辞是否不再出现"K 次读取"。
b) **哈希分桶方案亲核**（用纯内存 DuckDB 1.5.4 构造反例证明或证伪）：①同 `(tag,tx,li)` 两行 b 不同/跨 run/跨通道（tag 不同则键不同，是否与基线口径一致——基线 `GROUP BY tag, tx, li` 也按 tag 分组）是否必落同桶且被桶内查重拒绝；②`hash()` 对 `li` 为 BIGINT、`tx` 为 VARCHAR、`tag` 为 VARCHAR 的组合稳定性（同一连接内同值同哈希；跨桶查询间不变）；③`(a,b)` 跨桶后 `ab_raw → ab GROUP BY a,b` 合并是否恢复与基线 `ab` 逐行相等（含自转同块净零、Z/DEAD 作 a）；④桶内"先过滤后 GROUP BY"在四类冲突反例（工单 0.7-4）下是否都被桶内全行查重先拒绝；⑤`kept_rows` 记账与桶行数之和的等式在有 `n_out_of_segment`/`n_bad_fields` 时是否成立（VIEW 已过滤这些行）。
c) **成本与资源**：正常路径每桶两条源查询的登记是否如实（对照 2.1(c) 全部 SQL，数出每桶实际覆盖源范围的查询条数，含日志/取样若有）；1.6/1.8/2.3 三处措辞是否一致；0.8 对"默认 500 万桶资源证据"的要求是否可执行（给出你认为最省的单桶实测构造法）；r2 否决的"全局 (h,c) 窄表"方案本轮不再评估。
d) **验收设计**：0.7 的 7 项与 0.8 是否足以证明 1.1–1.5（尤其：基线 `--only-addrs` 收据作主对照、低于门槛正峰值地址、四类冲突独立运行、执行路径证据 `duckdb_tables()`）；沙箱可行性（2,000,000 行双格式生成 + 多次运行的时间/磁盘预算是否现实；若不现实给出缩减方案与理由）。
e) **测试**：2.2 `followup_bucketed_case` 是否可构造且最小；"原始行层复制 ≥20 行"在 `_write_v2_inputs` 现有写法下的最小改法；期望峰值由测试内独立 Python 累计计算的写法是否与生产口径一致（块末、严格大于、首达块）；`_run` 扩展是否影响既有 4 处调用。
f) **回归面与守卫**：`followup_peaks` 新增 keyword-only 参数、`build_events` 新增 `materialize` 是否触发 `invariant_scan`/`test_batch4_invariant_guards`/AST 守卫；`os.replace` 留在 `followup_peaks` 是否满足 manifest `:967-969`；`test_audit_release_gate.py:999-1001` 读当前脚本 sha 构造收据的用例是否受影响。
g) **锚与事实**：v2 事实段①-⑨与 2.1/2.3 的锚整行 `grep -n -F -x` 复验；CHANGELOG 索引行字节数（须 ≤200 B，v2 声称 179 B）。
h) **档位**：在"冲突拒绝能力完整保留、数值与收据契约不变、只增 IO 代价"前提下 9.2.2 记"修"是否恰当。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文，含条款号）＋ 汇总表。
