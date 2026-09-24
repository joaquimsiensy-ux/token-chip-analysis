# 工单 R1 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260924-flow-scan-scalability/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**（不要只 print 到 stdout）。首行固定 `# 工单R1复核：通过` 或 `# 工单R1复核：退回`。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（须含 `634c083`）。

## 任务
复核 `maintenance/repair-20260924-flow-scan-scalability/workorder_R1.md`（v1）。逐条审：
a) 锚与行号：`flow_anomaly_scan.py:64-65/:70/:113-137/:209-213/:223-231/:235/:237-240/:244-248/:259-262/:288-291/:296-299/:377-380/:385-403`、`CHANGELOG.md:13/:103`、`SKILL.md:23`、`pyproject.toml:15`、`VERSION` 是否与工单事实段①-④一致（整行 `grep -n -F -x` 恰 1 处）。
b) 等价性论证亲核：①`IN (子查询)`/`NOT IN (子查询)` 与字面量列表在本数据（地址非 NULL、全小写）下是否严格等价，含 `sent` 表为空/`elig` 为空的边界（基线 `IN ('')` 会怎样、新写法会怎样——若基线在空集下有特定行为，新写法必须一致或工单须明写）；②`sink_net` 按 1.4 定义与 `:259-262` 是否逐项等价（含 `t = X AND f = X` 自转边、`amt = 0` 边、地址同时在 presink 与 elig 的情形）；③工单事实③"best_window_scan 对同 ts 行序不敏感"的推理是否成立（`:113-137` 逐行核），若不成立指出反例；④`--entity-file` 抵消视图下从 `eflow` 物化是否等价；⑤`retention_bucket(info[f]...)`/`info` 依赖是否被改动波及。
c) 修法定形：物化三张表是否是最小改动，能否再少（如 sink_net 与 sink_edges 合并、是否需要 presink/prespray 表或直接 `CREATE TEMP TABLE ... AS SELECT t FROM ...`）；1.6 的 ≤90 行与 ≤2 helper 是否够；内存风险评估（物化表在亿级边、数千候选下的量级；DuckDB 内存库临时表超 `memory_limit` 时会不会溢出到磁盘还是直接 OOM——给出你的判断依据；若有风险，建议在工单加什么而不引入新 CLI 参数）。
d) 0.7 等价性证据设计是否足以证明 1.1（规模、构造覆盖三口径/抵消/exclude/多窗口累计/`recipients_top` 截断/同址双身份），是否缺 `--duckdb` 输入路径与 `--edges-evm-v2` 路径的对照（沙箱能否用 `test_lit_regression_f008.write_run` 之类现成写法合成 v2 parquet 夹具跑一次 EVM 路径对照——能则建议加入 0.7，给出具体写法）；基线副本通过 `git show` 取得再同目录放 `wave_scan.py` 的 import 方式是否可行。
e) 测试：2.2 第 17 例是否可构造且最小；`net_inflow_pct` 断言写法是否与生产四舍五入一致（`round(x*100.0/total, 4)`）。
f) 回归面：`test_reconcile_v4_receipt.py:362` 引用 `flow_anomaly_scan.load_sol`（转导入）是否受影响；`invariant_scan`/`test_batch4_invariant_guards`/AST 守卫是否会对本脚本的 SQL/结构改动报警；handoff/发布链是否有任何地方绑定 `flow_anomaly_scan.py` 源码哈希（`grep -rn` 证明）。
g) 原则与档位：references/commands 0 B、SKILL 仅版本号；9.1.1 记"修"是否恰当（契约不变、纯性能）。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文，含行号）＋ 汇总表。
