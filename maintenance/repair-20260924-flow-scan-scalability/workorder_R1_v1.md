# 工单 R1（v1）：flow_anomaly_scan 逐候选全量重扫 → 一次性物化候选相关边子集（亿级可完成）—— 版本 9.1.1

> 出处：QUQ(BSC) 0922 案 ANOM-009（`anomalies.json`，调度方持有；本仓库不含案卷）。`flow_anomaly_scan.py` 在 EVM v2 目录直读（`load_evm_v2` 互斥段 VIEW 轻路径，边表 1.097 亿行）下：汇集点预筛 7,093 个后**逐候选**对 `eflow` 全量重扫；调度方本机实测单个候选一次查询 117.9 s（与在跑进程争 CPU；`EXPLAIN` 显示 `f IN (5,086 址字面量列表)` 被下推为 parquet 扫描过滤、每次查询重新聚合 blocks 表并 HASH_JOIN），7,093 × ≥60 s ≈ 5 天；try1 7h14m、try3 18h35m 均未走出汇集点阶段。前案 OPN(BSC，255 万边)同脚本数分钟完成，故属亿级可扩展性缺陷，非口径问题。用户 2026-09-24 裁决：走 skill 修复（选 A），流程＝工单→codex 复核→codex 施工→codex 盲审→codex 收官 review。
> 事实（调度方本机亲核，基线 HEAD `634c083`，9.1.0）：
> ① 逐候选查询共 4 处，全部只读 `eflow`（`:229` 或 `:223-227` 定义的 VIEW）：sink 候选行 `:245-248`（`WHERE t = '{t}' AND f IN ('{elig_ph}') AND f <> t AND amt > 0 ORDER BY ts`）、sink 全史净流入 `:259-262`（`t = X OR f = X`，无 `amt > 0` 过滤）、spray 候选行 `:296-299`（`WHERE f = '{f}' AND t NOT IN ('{sent_ph}') AND f <> t AND amt > 0 ORDER BY ts`）、慢速收方 top `:377-380`（同过滤 `GROUP BY t ORDER BY v DESC LIMIT 500`）。预筛两处 `:237-240`（sink）、`:288-291`（spray）各一次全扫，本已可接受但同样带字面量 IN 列表。
> ② 候选集 `eligible`（`:209-210`，`addr.peak >= min_peak_raw`）与 `sentinels`（`:213`）在 `:235/:230` 拼成字面量 `elig_ph`/`sent_ph`；地址串全小写、无 NULL，`IN (子查询)` 与字面量 IN 语义相同。
> ③ `best_window_scan`（`:113-137`）对同 `ts` 行的相对顺序不敏感：窗口边界只依赖 `ts` 值；同组内中间位置的前缀和被组末位置支配（全部 `amt > 0`），`best` 取严格 `>`，故 `best_sum/w0/w1/best_keys` 与同 ts 行序无关。基线的候选遍历顺序（`GROUP BY` 结果顺序）与 `LIMIT 500` 边界并列项本就非确定。
> ④ 报告字段（`:385-403`）不含运行时长、不含 SQL 文本；`params` 记 `vars(a)`（不新增 CLI 参数即不变）。`test_flow_anomaly.py` 16 例走 `--edges-sol` 路径，与 EVM 路径共用 `:230` 以后全部逻辑；`fixtures/pythia_anchors.json` 由 `fixtures_lint.py` 校验形态。`invariant_manifest.json:1259` 只登记脚本路径与 schema（`:200-202`），不钉源码哈希；无 producer_history 条目；`shared_release_receipt.py:1564-` 只对 Solana 深验 `edge_source_binding`，与本改动无关。
> ⑤ `wave_scan.py` 不在本单范围（其 QUQ 实跑已完成；ANOM-009 的 wave 临时盘问题另单）。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `R1_done.md`：`git status --short`（须为空）与 `git rev-parse --short HEAD`（记录实际 HEAD）；`git merge-base --is-ancestor 634c083 HEAD` 须 exit 0；`git diff --quiet 634c083 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 须 exit 0。行号以 `634c083` 为准；任一不符**停工**。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents` 下任何内容。本目录内可读：`workorder_R1.md`、`review_R1_reply_*.md`。
- 0.3 **白名单**（可写）：生产 `scripts/report/flow_anomaly_scan.py`；测试 `scripts/tests/test_flow_anomaly.py`；版本登记 `VERSION`、`pyproject.toml:15`、`SKILL.md:23`、`CHANGELOG.md`；完成报告 `R1_done.md`、`R1_equivalence.txt`、`R1_timing.txt`（本目录）。
- 0.4 **不改**：`scripts/report/wave_scan.py`（`load_evm_v2/load_sol/attach_duckdb/build_addr_summary` 为 wave/flow 共用装载与概要，不动）、`scripts/tests/fixtures/pythia_anchors.json`、`scripts/tests/invariant_manifest.json`、`references/**`、`commands-staging/*`、其他任何文件。
- 0.5 所有施工锚在首次修改前统一核验：目标文件整行原文以 `grep -n -F -x -- '<整行>' <文件>` 命中恰 1 处且基线行号一致，不符**停工**。修改后的行号允许自然移动，完成报告记录实际 diff 行号。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree。基线脚本副本用 `git show 634c083:scripts/report/flow_anomaly_scan.py > <tempdir>/flow_baseline.py` 取得（同目录再放 `git show 634c083:scripts/report/wave_scan.py > <tempdir>/wave_scan.py` 供其 import），只作对照运行，不入库。
- 0.7 **等价性证据（先做，写 `R1_equivalence.txt`）**：用固定随机种子在临时目录合成一套 `--edges-sol` 格式边集（复用 `test_flow_anomaly.py` 的 `run()`/`formal_cli_args` 写法）：≥3,000 地址、≥300,000 条边、跨 ≥400 天，构造上必须让基线报告同时含 sink ≥5、spray 三口径各 ≥2（pulse / pulse_all / slow_spray，其中 slow_spray 至少 1 个收方 >500 以触发 `recipients_top` 截断）、`--entity-file` 一组内部抵消、且 ≥1 个地址同时出现在 sinks 与 sprays。分别用基线副本与施工后脚本以**相同参数**跑，两份 JSON 去掉 `generated_at` 后 `json.dumps(sort_keys=True)` 逐字节相等；再以 `--exclude-file` 变体重跑一次同样相等。记录两份报告的 sink/spray 计数与三口径分布。不相等即停工报告。
- 0.8 **耗时证据（写 `R1_timing.txt`）**：在 0.7 同一边集上记录基线与施工后的总墙钟；另以 0.7 数据放大到 ≥3,000,000 条边（同构造）再各跑一次记录墙钟与峰值 RSS（`/usr/bin/time -l` 或 `resource.getrusage`）。只记录，不设阈值。
- 0.9 不跑 `run_all.py`（调度方本机跑）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_flow_anomaly.py`、`test_wave_scan.py`、`test_reconcile_v4_receipt.py`、`fixtures_lint.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`。测试带 `MPLCONFIGDIR=$HOME/.matplotlib`（若可写）；临时目录 `Path(td).resolve()`。

## 1. 硬约束

- 1.1 **产物字节等价**：报告 JSON（除 `generated_at`）在任意输入与参数下与基线相同——不改任何判据、阈值、字段、排序键、ID 规则、`params` 键集；不新增 CLI 参数；不改 stdout/stderr 以外的任何输出。允许新增 `log()` 行（stderr）。
- 1.2 **只改查询组织方式**：全量扫描次数由"2 + 逐候选 O(N)"降为**常数次**（预筛 2 次＋物化 ≤3 次），逐候选查询一律改查物化的 DuckDB 临时表（`CREATE TEMP TABLE`），不再触碰 `eflow`/`edges`。物化表列只取 `ts, f, t, amt`（净流入表只取 `addr, net`）。
- 1.3 字面量 IN 列表改为临时表半连接：`elig(addr)`、`sent(addr)`、`presink(addr)`、`prespray(addr)` 四张单列临时表（`executemany` 插入，地址保持原样小写），查询中用 `f IN (SELECT addr FROM elig)` / `t NOT IN (SELECT addr FROM sent)`。`elig_ph`/`sent_ph` 字符串若不再被引用则删除其定义。
- 1.4 净流入等价：`sink_net` 表定义须与 `:259-262` 逐项对应——对每个 presink 地址 X：`SUM(amt) FILTER (t = X AND f <> t) − SUM(amt) FILTER (f = X AND t <> f)`，来源 `eflow`，**不加 `amt > 0`**，缺行取 0。
- 1.5 内存：物化表大小随候选数变化；不改 `--mem-limit` 语义；不设置 `temp_directory`（沿用 DuckDB 默认）。在 `log()` 中打印每张物化表行数。
- 1.6 生产改动 ≤ 90 行（增删合计），不新增模块级函数/常量以外的公开接口；允许 ≤ 2 个模块级私有 helper（`_` 前缀）。模块 docstring 追加 ≤ 6 行"9.1.1 性能重组"说明（引用 QUQ 实测的三重浪费与常数次全扫结论，不写案卷数字以外的结论）。
- 1.7 文档字节：`references/**`、`commands-staging/*` **零改动**；`SKILL.md` 仅 `:23` 版本号；CHANGELOG 索引行 ≤ 200 B。
- 1.8 `git diff --stat` 只含 0.3 白名单。

## 2. 逐条施工

### 2.1 `scripts/report/flow_anomaly_scan.py`

- (a) 地址集临时表。锚：`:235` 整行 `    elig_ph = "', '".join(sorted(eligible - sentinels))`（唯一）。在其位置建立 `elig`/`sent` 两张临时表（`sent` 内容＝`sentinels`，`elig` 内容＝`eligible - sentinels`），`sent_ph`（`:230`）与 `elig_ph` 若无引用则删除。
- (b) 汇集点。锚：`:237-240` 预筛查询——改用 `elig`/`sent` 半连接，结果顺序与语义不变；紧接着建 `presink(addr)` 临时表并物化：
  `CREATE TEMP TABLE sink_edges AS SELECT ts, f, t, amt FROM eflow WHERE t IN (SELECT addr FROM presink) AND f IN (SELECT addr FROM elig) AND f <> t AND amt > 0`；
  `CREATE TEMP TABLE sink_net AS ...`（按 1.4）。锚 `:245-248` 候选行查询改为 `SELECT ts, f, amt FROM sink_edges WHERE t = ? ORDER BY ts`（参数化）；锚 `:259-262` 改为从 `sink_net` 取值（缺行 0）。`for t in pre_sinks:`（`:244`）遍历顺序不变。
- (c) 分发点。锚：`:288-291` 预筛查询——改用 `sent` 半连接；紧接着建 `prespray(addr)` 并物化：
  `CREATE TEMP TABLE spray_edges AS SELECT ts, f, t, amt FROM eflow WHERE f IN (SELECT addr FROM prespray) AND t NOT IN (SELECT addr FROM sent) AND f <> t AND amt > 0`。锚 `:296-299` 候选行查询改为 `SELECT ts, t, amt FROM spray_edges WHERE f = ? ORDER BY ts`；锚 `:377-380` 慢速 top 改为 `SELECT t, SUM(amt) AS v FROM spray_edges WHERE f = ? GROUP BY t ORDER BY v DESC LIMIT 500`。
- (d) 日志：物化后各打一行 `log(f"物化 sink_edges {n:,} 行 / sink_net {m:,} 行")`、`log(f"物化 spray_edges {k:,} 行")`。
- (e) 说明：`eflow` 在 `--entity-file` 下是抵消视图（`:223-227`），物化一律从 `eflow` 取，抵消语义自然继承；`data_first_day`（`:231`）与 `build_addr_summary` 仍查 `edges`，不动。参数化查询用 `con.execute(sql, [addr])`，避免地址拼接。

### 2.2 `scripts/tests/test_flow_anomaly.py` —— 回归

- 新增第 17 例 `MixedHub`：同一地址既是 sink（14 日窗内 ≥5 合格来源合计 ≥2%）又是 spray（同一批币在其后 14 日内派给 ≥20 新收方 ≥2%），且另有一个 slow_spray 地址收方 ≥600（触发 `recipients_top` 恰 500）。断言：sinks 与 sprays 各含该地址；`recipients_top` 长度 500 且 `all_time.recipient_count ≥ 600`；`sink.all_time.net_inflow_pct` 等于该地址（全部入边 − 全部出边）/总量的四舍五入四位值（含一条 `amt=0` 的出边以证 1.4 的"不加 amt>0"）。文件头列表追加第 17 条一行说明；尾行计数随之 +1。

### 2.3 版本登记 9.1.1

- `VERSION` `9.1.0`→`9.1.1`；`pyproject.toml:15` `version = "9.1.0"`→`"9.1.1"`；`SKILL.md:23` `<!-- skill-version-source: VERSION; skill-version: 9.1.0 -->`→`9.1.1`。
- `CHANGELOG.md:13` 整行原文（唯一，以 `- **9.1.0**（2026-09-23）Solana 交易版本上限统一为` 开头）之前插入一行（≤ 200 B）：

```text
- **9.1.1**（2026-09-24）flow_anomaly_scan 亿级可完成：候选相关边一次物化为临时表，逐候选不再全量重扫（QUQ ANOM-009）；报告字节、参数、schema 不变，档位 修。
```

- `CHANGELOG.md:103` 整行 `## [9.1.0] - 2026-09-23 — Solana 交易版本 1 与可信前代 pending 认领`（唯一）之前插入 `## [9.1.1] - 2026-09-24 — flow 扫描常数次全扫重组` 详细段（同格式四条：出处与裁决 / 改法 / 字节与测试（引用 `R1_equivalence.txt`、`R1_timing.txt` 的计数与墙钟）/ 成本-质量指标），末尾空一行。`changelog_lint.py` 由调度方执行。

## 3. 完成报告 `R1_done.md`

首行 `# R1 完成：<一句话>` 或 `# R1 停工：<原因>`。含：开工基线四项输出；等价性证据摘要（指向 `R1_equivalence.txt`，两变体均逐字节相等）；耗时证据摘要（指向 `R1_timing.txt`）；每处施工实际 diff 行号与行数（生产 ≤ 90 行自证）；§0.9 尾行；字节三处（`SKILL.md` 仅版本号、`commands-staging` 不变、`references` 不变，各贴 `wc -c` 合计）；`git diff --stat 634c083 -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`；未做/存疑逐条；末尾披露是否读过禁读路径。
