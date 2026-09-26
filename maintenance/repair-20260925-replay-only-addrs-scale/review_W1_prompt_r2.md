# 工单 W1 复核提示词 r2（只读 codex）——复核 v2

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260925-replay-only-addrs-scale/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`、`/Volumes`；不得进入 `/Users/uravvv/.claude/skills/token-chip-analysis`（另一工程在用）。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**。首行固定 `# 工单W1复核r2：通过` 或 `# 工单W1复核r2：退回`。工作目录＝`/Users/uravvv/.claude/worktrees/tca-only-addrs`（分支 `fix/replay-only-addrs-scale`，基线 `8457f70`）。

## 背景
`workorder_W1.md` 现为 v2，逐条吸收了 r1（`review_W1_reply_r1.md`）的意见；最大变化＝分段键从"块区间"改为"去重键哈希分桶 `hash(tag, tx, li) % K`"，以此同时消掉 r1 的 b①（跨块冲突漏检）与 c（段规模偏斜）两项阻断。本轮请**重新完整判定**，不沿用 r1 结论。

## 任务
a) **r1 意见落地核对**：对照 r1 汇总表 13 行，逐行核 v2 是否落地（给出 v2 对应条款号）；未落地或落地走样的列出原文与建议替换文本。
b) **哈希分桶方案亲核**（用纯内存 DuckDB 1.5.4 构造反例证明或证伪）：①同 `(tag,tx,li)` 两行 b 不同/跨 run/跨通道（tag 不同则键不同，是否与基线口径一致——基线 `GROUP BY tag, tx, li` 也按 tag 分组）是否必落同桶且被桶内查重拒绝；②`hash()` 对 `li` 为 BIGINT、`tx` 为 VARCHAR、`tag` 为 VARCHAR 的组合稳定性（同一连接内同值同哈希；跨桶查询间不变）；③`(a,b)` 跨桶后 `ab_raw → ab GROUP BY a,b` 合并是否恢复与基线 `ab` 逐行相等（含自转同块净零、Z/DEAD 作 a）；④桶内"先过滤后 GROUP BY"在四类冲突反例（工单 0.7-4）下是否都被桶内全行查重先拒绝；⑤`kept_rows` 记账与桶行数之和的等式在有 `n_out_of_segment`/`n_bad_fields` 时是否成立（VIEW 已过滤这些行）。
c) **成本与资源**：K 次全量读取（工单 1.6 已如实登记）在 v2 parquet 上每次读取是否真的只解码所需列（`_v2_select` 的投影：block_number/log_index/transaction_hash/topic1/topic2/data + blocks 表 join）；桶谓词 `hash(...) % K = i` 是否会阻止 DuckDB 的投影裁剪；每桶 `GROUP BY tag,tx,li` 在 ≈5,000,000 行、宽字符串下的内存量级估计（给出你的估算依据，不要求精确）；是否存在更省的**且仍精确**的方案（例如一次扫描物化窄列 `(h=hash(tag,tx,li), c=hash(b,ts,frm,t2,v))` 做全局查重再对可疑键精查——请评估其 64 位哈希碰撞导致漏检的风险是否可接受，以及与 K 次全量读取相比的取舍；若你认为更优，给出替换工单 1.3/2.1(c) 的具体文本；若不更优，说明理由）。
d) **验收设计**：0.7 的 7 项与 0.8 是否足以证明 1.1–1.5（尤其：基线 `--only-addrs` 收据作主对照、低于门槛正峰值地址、四类冲突独立运行、执行路径证据 `duckdb_tables()`）；沙箱可行性（2,000,000 行双格式生成 + 多次运行的时间/磁盘预算是否现实；若不现实给出缩减方案与理由）。
e) **测试**：2.2 `followup_bucketed_case` 是否可构造且最小；"原始行层复制 ≥20 行"在 `_write_v2_inputs` 现有写法下的最小改法；期望峰值由测试内独立 Python 累计计算的写法是否与生产口径一致（块末、严格大于、首达块）；`_run` 扩展是否影响既有 4 处调用。
f) **回归面与守卫**：`followup_peaks` 新增 keyword-only 参数、`build_events` 新增 `materialize` 是否触发 `invariant_scan`/`test_batch4_invariant_guards`/AST 守卫；`os.replace` 留在 `followup_peaks` 是否满足 manifest `:967-969`；`test_audit_release_gate.py:999-1001` 读当前脚本 sha 构造收据的用例是否受影响。
g) **锚与事实**：v2 事实段①-⑨与 2.1/2.3 的锚整行 `grep -n -F -x` 复验；CHANGELOG 索引行字节数（须 ≤200 B，v2 声称 179 B）。
h) **档位**：在"冲突拒绝能力完整保留、数值与收据契约不变、只增 IO 代价"前提下 9.2.2 记"修"是否恰当。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文，含条款号）＋ 汇总表。
