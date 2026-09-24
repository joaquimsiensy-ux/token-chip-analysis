# 工单 R1（v2，融合 codex 复核 r1 全部意见）：flow_anomaly_scan 候选边物化，消除逐候选底层全量重扫——版本 9.1.1

> 出处：QUQ(BSC) 0922 案 ANOM-009（案卷由调度方持有，本仓库不含）。`flow_anomaly_scan.py` 在 EVM v2 目录直读（`load_evm_v2` 互斥段 VIEW 轻路径，边表 1.097 亿行）下：汇集点预筛 7,093 个后**逐候选**对 `eflow` 全量重扫；调度方本机实测单候选一次查询 117.9 s（与在跑进程争 CPU；`EXPLAIN` 显示 5,086 址字面量 IN 列表被下推为 parquet 扫描过滤、每次查询重新聚合 blocks 表并 HASH_JOIN），7,093 × ≥60 s ≈ 5 天；try1 7h14m、try3 18h35m 均未走出汇集点阶段。前案 OPN(BSC，255 万边)同脚本数分钟完成。用户 2026-09-24 裁决：走 skill 修复（选 A），流程＝工单→codex 复核→codex 施工→codex 盲审→codex 收官 review。
> v2 变更（`review_R1_reply_r1.md`，全部采纳）：事实②/③/④更正（sentinels `:215`、`log()` 走 stdout、`params`＝`vars(a)` 去 `out`、同 ts 结论只覆盖函数返回值）；1.1 改为"并列项等价边界"契约（基线 OPN 案两次运行 `recipients_top` 已不一致——调度方本机实测：第 500 名处 13,650 个收方并列同额，其余字段逐字节相等）；1.3 候选表改 CTAS、elig 空集兼容 `IN ('')`、不 lower；1.4 净流入两侧分别补零并定形 SQL；1.5 资源边界与阶段释放；0.7 三入口＋变体＋并列微夹具＋基线 PYTHONPATH；2.2 第 17 例重写；索引行 158 B；标题与完成报告去掉"亿级必可完成/报告字节不变"类未证承诺。
> 事实（调度方本机亲核，基线 HEAD `634c083`，9.1.0；复核 r1 已逐锚 `grep -n -F -x` 复验）：
> ① 逐候选查询共 4 处，全部只读 `eflow`（`:229` 或 `:223-227` 定义的 VIEW）：sink 候选行 `:245-248`（`WHERE t = '{t}' AND f IN ('{elig_ph}') AND f <> t AND amt > 0 ORDER BY ts`）、sink 全史净流入 `:259-262`（`t = X OR f = X`，无 `amt > 0` 过滤）、spray 候选行 `:296-299`（`WHERE f = '{f}' AND t NOT IN ('{sent_ph}') AND f <> t AND amt > 0 ORDER BY ts`）、慢速收方 top `:377-380`（同过滤 `GROUP BY t ORDER BY v DESC LIMIT 500`）。预筛两处 `:237-240`（sink）、`:288-291`（spray）各一次全扫，同样带字面量 IN 列表。
> ② `eligible` 位于 `:209-210`，`info` 位于 `:212-213`，`sentinels = {Z, DEAD} | exclude` 位于 `:215`；字面量列表 `elig_ph`/`sent_ph` 位于 `:235`/`:230`。地址集必须保留原字符串（正式 Solana 地址区分大小写，测试夹具用 `Src0`/`SinkA` 等），不做 lower。非空集合使用成员相同且不含 NULL 的临时表时，`IN`/`NOT IN` 判断与字面量列表等价。`sentinels` 固定含 Z、DEAD 不会为空；`eligible - sentinels` 为空时基线实际执行 `IN ('')`（DuckDB 1.5.4 实测 `'' IN ('')` 为 true、`'x' IN ('')` 为 false），新 `elig` 表在该情形须保留一行空字符串以兼容。`con.executemany(sql, [])` 抛 `InvalidInputException`，任何空参数列表不得直接传入。
> ③ `best_window_scan(:113-135)` 在按 ts 升序、金额为正整数的输入下对同 ts 行序不敏感（窗口边界只依赖 ts 值；同组前缀和被组末支配；`:133` 严格 `>`）；此结论只覆盖函数返回的金额、key 集合与窗口端点，**不覆盖整个报告的数组顺序**：`sources(:254-279)` 同 pct 项（`src_pct` 保留首次出现顺序、仅按四舍五入 pct 排序）、`sinks(:282)` 同窗口 pct 项、`sprays(:383)` 同全史 pct 项、`recipients_top(:377-381)` 同累计金额项均存在基线未规定的并列顺序，第 500 名并列还可能改变所选地址集合。
> ④ 报告字段（`:385-403`）不含运行时长与 SQL 文本；`params`（`:388`）记录 `vars(a)` 中除 `out` 外全部键值，不新增 CLI 参数即不变。`log()`（`:70-71`）用 `print(..., flush=True)` 写 **stdout**。`test_flow_anomaly.py` 16 例走 `--edges-sol` 路径，与 EVM/`--duckdb` 路径共用 `:207` 以后全部逻辑；正式 Solana 装载器 `wave_scan.py:172-181` 拒绝 `amount <= 0`。`fixtures/pythia_anchors.json` 由 `fixtures_lint.py` 校验形态。`invariant_manifest.json:200-202/:1259` 只登记 schema 与脚本路径，`invariant_scan.scan_python()` 对本脚本返回 `producers={'flow-anomaly/v3'}`，不解析 SQL；`producer_history.py` 无 flow 条目；`shared_release_receipt.py:1564-1613` 只对 Solana 派生报告核 `edge_source_binding`；`adjudication_validator.py:425/:480` 与 handoff 绑定的是**报告文件**哈希（源码兼容不代表重写报告后下游哈希自动兼容——本单不重写任何存量案报告）。`test_reconcile_v4_receipt.py:362` 依赖 `flow_anomaly_scan.load_sol` 转导入（`:64-65`），须保持。
> ⑤ `wave_scan.py` 不在本单范围（`load_evm_v2/load_sol/attach_duckdb/build_addr_summary` 为 wave/flow 共用；F008 AST 守卫保护 `load_evm_v2`；ANOM-009 的 wave 临时盘问题另单）。
> ⑥ 基线副本 import：`wave_scan.py:68-76` 按自身位置插入 `../lib` 与 `../solana`，仅把两份基线文件放同一临时目录会 `ModuleNotFoundError: wave_contract`；须显式 `PYTHONPATH=<repo>/scripts/lib:<repo>/scripts/solana:<repo>/scripts/report`（开工门禁保证这些共享依赖与 `634c083` 一致）。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `R1_done.md`：`git status --short`（须为空）与 `git rev-parse --short HEAD`（记录实际 HEAD）；`git merge-base --is-ancestor 634c083 HEAD` 须 exit 0；`git diff --quiet 634c083 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 须 exit 0。行号以 `634c083` 为准；任一不符**停工**。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents` 下任何内容。本目录内可读：`workorder_R1.md`、`workorder_R1_v1.md`、`review_R1_reply_*.md`。
- 0.3 **白名单**（可写）：生产 `scripts/report/flow_anomaly_scan.py`；测试 `scripts/tests/test_flow_anomaly.py`；版本登记 `VERSION`、`pyproject.toml:15`、`SKILL.md:23`、`CHANGELOG.md`；完成报告 `R1_done.md`、`R1_equivalence.txt`、`R1_timing.txt`（本目录）；等价性/耗时夹具脚本 `R1_fixture_tools.py`（本目录，仅供本工程复现，不接入测试套件）。
- 0.4 **不改**：`scripts/report/wave_scan.py`、`scripts/tests/fixtures/pythia_anchors.json`、`scripts/tests/invariant_manifest.json`、`scripts/tests/test_lit_regression_f008.py`（可**复用其 `write_run` 的列结构与编码写法**于 `R1_fixture_tools.py`，不修改原文件）、`references/**`、`commands-staging/*`、其他任何文件。
- 0.5 首次修改前，以目标块内可唯一识别的非空整行为锚，执行 `grep -n -F -x -- '<整行>' <文件>`，须恰命中 1 处且基线行号一致；随后逐行核对完整目标块。空行、重复的 `else:`（`:228`）和 `if a.edges_sol:`（`:401`）不作独立唯一锚。修改后行号可自然移动，完成报告记录实际 diff 行号。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree。基线脚本副本：`git show 634c083:scripts/report/flow_anomaly_scan.py > <tempdir>/flow_baseline.py`、`git show 634c083:scripts/report/wave_scan.py > <tempdir>/wave_scan.py`，基线子进程显式设置 `PYTHONPATH=<repo>/scripts/lib:<repo>/scripts/solana:<repo>/scripts/report` 并用 `python3 -B <tempdir>/flow_baseline.py ...`（同目录 `wave_scan.py` 由基线副本优先导入）。基线与施工后运行复用**同一份**已生成的输入与 `formal_cli_args` 产物，不分别重建带不同路径的夹具。
- 0.7 **等价性证据（先冻结夹具与基线报告，施工后同夹具、同入口、同参数重跑；写 `R1_equivalence.txt`）**：
  - 主夹具（`--edges-sol` 格式，复用 `test_flow_anomaly.py` 的 `run()`/`formal_cli_args` 写法，固定随机种子，由 `R1_fixture_tools.py` 生成）：≥3,000 地址、≥300,000 边、跨度 ≥400 天；断言顶层 `mode` 为 pulse / pulse_all / slow_spray 的地址各 ≥2 并另列 `mode_hits` 分布（须含"老收方补货"型 pulse_all：收方先建仓再受灌，fresh 计数为 0）；sink ≥5，其中含多窗口累计高于最佳单窗者、同址 sink/spray；至少一个纯 slow_spray 有 >500 收方；**构造上避免输出排序键并列**（收方累计金额、来源 pct、窗口 pct、全史 pct 两两不等），使去 `generated_at` 后可逐字节比较。分别运行无 entity、有 entity、有 entity＋exclude 三个变体，断言同实体边被抵消、跨实体边保留、exclude 确实改变相关候选或金额。
  - 并列微夹具（各入口内新旧对照按 1.1 专项判定，不得以"排序所有数组"掩盖差异）：空 elig（无地址达 0.02%）、空候选（预筛为 0）、自转边、非合格来源入边、同 ts 同额多来源（sources 并列）、`recipients_top` 第 500 名并列（≥520 收方中 ≥30 个同额落在边界）；零值/负值边只放 `--duckdb` 微夹具（该入口装载器不校验金额），断言 `amt = 0` 出边不改变净流入且不计入收方数。
  - 入口覆盖：主夹具另以 `--edges-evm-v2`（用 `R1_fixture_tools.py` 按 `test_lit_regression_f008.py:74` 的列结构批量写两个互斥 block 区间的 `run_*/logs.parquet`＋`blocks.parquet`，地址为固定映射的小写 40-hex，保留 Z/DEAD；确认日志出现"区间互斥——VIEW 轻路径"、解码边数/金额/地址与夹具一致、报告无 `edge_source_binding`）与 `--duckdb`（同一边集写入 `edges(ts BIGINT, f VARCHAR, t VARCHAR, amt HUGEINT)` 的 DuckDB 文件）各跑一遍；严格比较只在**同一入口的基线与施工后脚本之间**进行（跨入口 `params`/binding 天然不同）。
  - 每个变体记录：覆盖断言与结果、sink/spray 计数、三口径分布、比较结论。任一不符即停工报告。
- 0.8 **耗时证据（写 `R1_timing.txt`）**：主夹具上基线与施工后的总墙钟；再将主夹具同构放大到 ≥3,000,000 边各跑一次（三入口至少 `--edges-evm-v2` 一次），记录墙钟、峰值 RSS（`resource.getrusage(RUSAGE_CHILDREN)` 或 `/usr/bin/time -l`）、DuckDB 版本、有效 `memory_limit`/`temp_directory`/`max_temp_directory_size`、候选数、三张物化表行数、逐候选查询的 `EXPLAIN` 摘要（证明只读物化表、不再扫 parquet）与每候选平均耗时。只记录，不设阈值；测不到的项明确标注。
- 0.9 不跑 `run_all.py`（调度方本机跑）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_flow_anomaly.py`、`test_wave_scan.py`、`test_reconcile_v4_receipt.py`、`fixtures_lint.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`。测试带 `MPLCONFIGDIR=$HOME/.matplotlib`（若可写）；临时目录 `Path(td).resolve()`。

## 1. 硬约束

- 1.1 **等价契约**：保持判据、阈值、字段、排序键、ID 规则、`params` 键集及确定性计算结果不变，不新增 CLI 参数。无输出排序键并列的固定夹具上，报告除 `generated_at` 外须逐字节相等。已有并列项单独核验：仅允许相同生产排序键组内重排；`recipients_top` 第 500 名并列时允许从相同累计金额的边界组中选择不同成员，但须满足数量、唯一性、全部严格高于边界者均入选且低于边界者均不入选。其他差异一律失败。日志沿用现有 `log()` 的 stdout 行为，允许新增 `log()` 行。
- 1.2 **只重组 sink/spray 阶段查询**：两次预筛与三次数据物化各至多读取 `eflow` 一次（装载、`build_addr_summary`、`data_first_day` 不计入该上限）；CTAS 语句数不等于实际源扫描次数，须用 `EXPLAIN` 核验。四处逐候选查询只读物化表，不再触碰 `eflow`/`edges`。`sink_net` 不得通过候选数规模的 OR/非等值连接恢复 O(候选数×全边数) 工作量。
- 1.3 地址集：`elig(addr)`、`sent(addr)` 两张单列临时表，保留地址原字符串；插入前判空——`sent` 恒非空，`elig` 为空时插入单行 `''`（兼容基线 `IN ('')`，见事实②）。`presink(addr)`、`prespray(addr)` 直接以 `CREATE TEMP TABLE ... AS SELECT t/f AS addr FROM eflow ... GROUP BY ... HAVING ...` 物化预筛结果，候选遍历读 `SELECT addr FROM presink/prespray`（Python 侧不再往返插入）。查询中用 `f IN (SELECT addr FROM elig)` / `t NOT IN (SELECT addr FROM sent)`。删除失去引用的 `elig_ph`/`sent_ph` 定义。
- 1.4 净流入：`sink_net` 对每个 presink 地址 X 等于 `COALESCE(SUM(amt) FILTER (WHERE t=X AND f<>t),0) - COALESCE(SUM(amt) FILTER (WHERE f=X AND t<>f),0)`，来源 `eflow`，**不施加 elig/sent 或 `amt > 0` 过滤**；无对应聚合行取 0（Python `.get(addr, 0)`）；自转贡献 0；两个 presink 地址互转时两端分别计入。定形 SQL（单次 `eflow` 扫描，半连接，无 DELIM_JOIN——施工时以 `EXPLAIN` 复验）：

```sql
CREATE TEMP TABLE sink_net AS
SELECT CASE WHEN k = 0 THEN t ELSE f END AS addr,
       SUM(CASE WHEN k = 0 THEN amt ELSE -amt END) AS net
FROM eflow CROSS JOIN (VALUES (0), (1)) sides(k)
WHERE f <> t
  AND CASE WHEN k = 0 THEN t ELSE f END IN (SELECT addr FROM presink)
GROUP BY 1
```

- 1.5 资源：物化容量按实际相关边数评估（最坏各接近全量），不以候选数代替；保持 `--mem-limit` 语义与默认 `temp_directory`（DuckDB 内存库临时数据可溢写磁盘，不因超 `memory_limit` 必然 OOM；`fetchall()` 的 Python 对象不受 `memory_limit` 约束）。`log()` 记录 DuckDB 版本、有效 `memory_limit`/`temp_directory`/`max_temp_directory_size`（`SELECT current_setting(...)`）与三张数据表行数。**阶段释放**：sink 阶段结束后 `DROP` `sink_edges`、`sink_net`，再建 `spray_edges`。**边表按候选列物理组织**（`sink_edges` 按 `t, ts`、`spray_edges` 按 `f, ts` 排序写入——`:193` 已 `SET preserve_insertion_order=false`，CTAS 的 `ORDER BY` 可能不被保留，须在 CTAS 前后临时 `SET preserve_insertion_order=true/false` 并用 `EXPLAIN ANALYZE` 或逐候选平均耗时验证过滤效果），逐候选查询保留 `ORDER BY ts`。未获亿级实跑证据前，只声明"消除了逐候选底层全量重扫"，不声明"亿级必可完成"。
- 1.6 生产改动 ≤ 110 行（增删合计），允许 ≤ 2 个模块级私有 helper（`_` 前缀）；不删除、不重命名任何现有公开模块属性（含 `:64-65` 转导入）。模块 docstring 追加 ≤ 6 行"9.1.1 查询重组"说明（三重浪费与常数次源扫描结论；不写案卷结论）。
- 1.7 文档字节：`references/**`、`commands-staging/*` **零改动**（用 `git diff` 验证，不为统计字节而读 `references/attic.md`）；`SKILL.md` 仅 `:23` 版本号；CHANGELOG 索引行 ≤ 200 B。
- 1.8 `git diff --stat` 只含 0.3 白名单。

## 2. 逐条施工

### 2.1 `scripts/report/flow_anomaly_scan.py`

- (a) 地址集临时表。锚：`:235` 整行 `    elig_ph = "', '".join(sorted(eligible - sentinels))`（唯一）。在其位置建立 `elig`/`sent`（按 1.3：保留原字符串、判空、elig 空集插 `''`），删除 `:230` `sent_ph` 与 `:235` `elig_ph`（若无剩余引用）。
- (b) 汇集点。锚：`:237-240` 预筛查询改为 `CREATE TEMP TABLE presink AS SELECT t AS addr FROM eflow WHERE f IN (SELECT addr FROM elig) AND t NOT IN (SELECT addr FROM sent) AND f <> t AND amt > 0 GROUP BY t HAVING SUM(amt) >= {sink_min_raw}`，随后 `pre_sinks = [r[0] for r in con.execute("SELECT addr FROM presink").fetchall()]`（`:241` 日志与 `:244` 遍历不变）。紧接着物化：
  `CREATE TEMP TABLE sink_edges AS SELECT ts, f, t, amt FROM eflow WHERE t IN (SELECT addr FROM presink) AND f IN (SELECT addr FROM elig) AND f <> t AND amt > 0 ORDER BY t, ts`（按 1.5 保序处理）；`sink_net` 按 1.4 定形 SQL；`net_map = dict(con.execute("SELECT addr, net FROM sink_net").fetchall())`。锚 `:245-248` 改为 `con.execute("SELECT ts, f, amt FROM sink_edges WHERE t = ? ORDER BY ts", [t])`；锚 `:259-262` 改为 `net_in = net_map.get(t, 0)`（后续 `int(net_in)` 用法不变）。sink 阶段结束（`:282` 排序之后）`DROP TABLE sink_edges; DROP TABLE sink_net`。
- (c) 分发点。锚：`:288-291` 预筛查询改为 `CREATE TEMP TABLE prespray AS SELECT f AS addr FROM eflow WHERE t NOT IN (SELECT addr FROM sent) AND f NOT IN (SELECT addr FROM sent) AND f <> t AND amt > 0 GROUP BY f HAVING SUM(amt) >= {spray_min_raw}`，随后 `pre_sprays = [...]`（`:292` 日志与 `:295` 遍历不变）。紧接着物化 `CREATE TEMP TABLE spray_edges AS SELECT ts, f, t, amt FROM eflow WHERE f IN (SELECT addr FROM prespray) AND t NOT IN (SELECT addr FROM sent) AND f <> t AND amt > 0 ORDER BY f, ts`。锚 `:296-299` 改为 `con.execute("SELECT ts, t, amt FROM spray_edges WHERE f = ? ORDER BY ts", [f])`；锚 `:377-380` 改为 `con.execute("SELECT t, SUM(amt) AS v FROM spray_edges WHERE f = ? GROUP BY t ORDER BY v DESC LIMIT 500", [f])`。
- (d) 日志：装载后一行资源设置（1.5）；三张数据表各一行行数。
- (e) 说明：`eflow` 在 `--entity-file` 下是抵消视图（`:223-227`），物化一律从 `eflow` 取，抵消语义继承；`info`/`eligible`/`build_addr_summary`/`data_first_day` 继续来自 `edges`/`addr`，不得由物化表重建；`retention_bucket(info[f]...)` 与 fresh 首建日判断不动。

### 2.2 `scripts/tests/test_flow_anomaly.py` —— 回归

- 新增第 17 例 `MixedHub`：复用既有 SRC，5 个来源于 `day(700)` 各向 `MixedHub` 转入 6×10^9；`MixedHub` 于 `day(701)` 向 20 个新收方各转出 10^9；另加一条 `day(701)` 正值自转 `MixedHub→MixedHub`（预期净额不变）；另加一条来自非合格来源 `TinySrc`（峰值 <0.02%）的入边 10^8（预期计入净流入、不计入 `sources`/`qualified_inflow_pct`）。断言：`MixedHub` 同时出现在 sinks 与 sprays；`sink.all_time.net_inflow_pct == round((5*6*10**9 + 10**8 - 20*10**9) * 100.0 / TOTAL, 4)`；`sink.all_time.qualified_inflow_pct == round(5*6*10**9 * 100.0 / TOTAL, 4)`；`sources` 长度 5。复用既有 `SlowSpray`（`:101-109`，600 收方），断言其 `len(recipients_top) == 500` 且 `all_time.recipient_count == 600`。零值/负值边不进本夹具（正式 Solana 装载器拒绝）。文件头列表追加第 17 条一行说明；保留尾行"失败项数"计数逻辑。

### 2.3 版本登记 9.1.1

- `VERSION` `9.1.0`→`9.1.1`；`pyproject.toml:15` `version = "9.1.0"`→`"9.1.1"`；`SKILL.md:23` `<!-- skill-version-source: VERSION; skill-version: 9.1.0 -->`→`9.1.1`。
- `CHANGELOG.md:13` 整行原文（唯一，以 `- **9.1.0**（2026-09-23）Solana 交易版本上限统一为` 开头）之前插入一行（含换行 158 B）：

```text
- **9.1.1**（2026-09-24）flow 扫描候选边物化，消除逐候选底层全量重扫（QUQ ANOM-009）；参数、schema 与判据不变，档位 修。
```

- `CHANGELOG.md:103` 整行 `## [9.1.0] - 2026-09-23 — Solana 交易版本 1 与可信前代 pending 认领`（唯一）之前插入 `## [9.1.1] - 2026-09-24 — flow 扫描候选边物化` 详细段（同格式四条：出处与裁决 / 改法 / 字节与测试（引用 `R1_equivalence.txt`、`R1_timing.txt` 的计数与墙钟）/ 成本-质量指标），末尾空一行。`changelog_lint.py` 由调度方执行。

## 3. 完成报告 `R1_done.md`

首行 `# R1 完成：<一句话>` 或 `# R1 停工：<原因>`。含：开工基线四项输出；等价性证据摘要（逐项列明三种输入入口、entity/exclude 变体、无并列夹具字节比较及并列微夹具专项结果，指向 `R1_equivalence.txt`）；耗时证据摘要（DuckDB 版本、有效资源设置、候选数、物化行数、查询计划、墙钟与峰值 RSS，测不到的项标注，指向 `R1_timing.txt`）；每处施工实际 diff 行号与行数（生产 ≤ 110 行自证）；§0.9 尾行；`git diff --stat 634c083 -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（references/commands-staging 零改动以此为准）；未做/存疑逐条；末尾披露是否读过禁读路径。
