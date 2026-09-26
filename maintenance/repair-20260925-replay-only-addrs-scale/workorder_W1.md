# 工单 W1（v2，融合 codex 复核 r1 全部意见）：`replay_duck.py --only-addrs` 按去重键哈希分桶流式补算，消除全量事件表物化与全局 GROUP BY——版本 9.2.2

> v2 变更（`review_W1_reply_r1.md`）：**分段键由"块区间"改为"去重键哈希分桶"**（r1 阻断项 b①：块区间分段会漏掉同 `(tag,tx,li)` 跨块的冲突；哈希分桶保证同键必同桶，与全局查重严格等价，且桶大小由哈希均匀性保证、无块号偏斜——同时消掉 r1 的 c"段规模"阻断）；锚点/事实订正（L48 唯一锚、docstring `:2-35`、用法 `:31-34`、`channels_preflight` 路径、事实⑤⑦、"三份宽表"措辞）；峰值对照改以基线 `--only-addrs` 收据为主对照（全量 `peaks.json` 带 `mint_total // 1000` 门槛）；provenance 差异按真实文件验证、不再要求跨版本"逐字节相等"；冲突反例拆四类独立运行；夹具/超时/资源测量方法按 r1 建议重写；`_run` 加 `env/timeout`；`CHIP_REPLAY_SEG_ROWS` 校验位置定在参数解析后、预检前；收据构造与 `os.replace` 保留在 `followup_peaks`（invariant manifest locator）；白名单补 `W1_done_attempt1_stopped.md` 并区分两种 diff 口径；CHANGELOG 索引行改为 179 B；合并后案卷必须用最终版脚本重跑写成交接动作。
> 出处：QUQ(BSC) 0922 案 −2 收口（案卷由调度方持有，本仓库不含）。发布闸 `audit_release_gate.py:1192-1264` 要求 `data/peaks/block_precision_followup.json` 由 `replay_duck.py --only-addrs` 本体产出并绑定脚本 sha。该路径在 1.097 亿行（v2 parquet，20 个 run 目录，7.1 GB）上六次失败（调度方提供的运行信息，本仓库不含原始证据）：`--mem-limit` 3/8/12/6/8/12 GB、`--threads` 2/6/4/4/4/1，临时目录本盘（余量 46–61 GB）与外接盘（820 GB）——本盘四次撞 `max_temp_directory_size`（38.1/41.9/43.7/56.8 GiB），外接盘两次在 DuckDB 内存上限内 OOM（"could not allocate block" 7.4/7.4 GiB；"failed to pin block" 11.1/11.1 GiB），六次全部死在 `build_events` 的 `CREATE TABLE events AS … FROM raw_rows GROUP BY tag, tx, li`（`:176-179`）。机器 8 核 16 GB RAM，DuckDB 1.5.4。
> 根因：`--only-addrs` 只需要地址子集的逐块余额增量，但现路径先把 1.1 亿行 `raw_rows` 整表物化（`:160-161`）、再对全表做冲突查重（`:165-168`）与去重物化 `events`（`:175-179`），子集过滤（`:385-387`）在这之后才发生。`raw_rows` 与正在生成的 `events`，连同冲突查重、去重聚合的中间状态，共同占用内存或临时盘；峰值随余量增长而增长，未测出上界。
> 事实（调度方在本分支基线 `8457f70` 亲核；复核 r1 已对 152 条非空整行 `grep -n -F -x` 复验一致）：
> ① `build_events(:89)`：逐通道生成 SELECT 片段 `parts`，`:159` `union = " UNION ALL ".join(parts)`，`:160-161` `CREATE TABLE raw_rows AS …`；`:165-168` 冲突查重（`GROUP BY tag, tx, li HAVING COUNT(DISTINCT (b, ts, frm, t2, v)) > 1`）；`:169-174` 命中即 `raise SystemExit("[fail-closed] … 数据损坏，先仲裁再重放")`；`:175-179` `CREATE TABLE events AS SELECT ANY_VALUE(b) b, ANY_VALUE(ts) ts, tx, li, ANY_VALUE(frm) frm, ANY_VALUE(t2) t2, ANY_VALUE(v) v FROM raw_rows GROUP BY tag, tx, li`；`:180` `DROP TABLE raw_rows`；`:181-183` `n_events`/`n_dedup_removed` 记账；`:185` `return acc`。reject 记账（`n_source_rows/n_bad_fields/n_out_of_segment`）在物化之前用 COUNT 扫描完成（v2 路径 `:104-113`，v1csv 路径 `:131-143`），不依赖 `raw_rows` 表。v2 读取 `_v2_select(:58-72)` 与 v1csv 读取（`:144-154`）都**不验证** `(tag,tx,li)→b` 的函数关系；`channels_preflight` 只验文件、收据、区间。
> ② `_create_deltas_view(:188-193)`：`CREATE VIEW deltas AS SELECT t2 AS a, b, CAST(v AS {vt}) AS d FROM events UNION ALL SELECT frm, b, -CAST(v AS {vt}) FROM events WHERE frm <> '{Z}'`（`:193` 为出方排 Z 的整行）——mint（frm=Z）不减 Z 余额；burn（t2∈{Z,DEAD}）照加。
> ③ `followup_peaks(:376)`（整行 `def followup_peaks(con, a, vt):` 全文件唯一，作本函数锚；`_create_deltas_view(con, vt)` 整行在 `:198`（属 `replay_pass1`，不动）与 `:381` 各出现一次，**不作唯一锚**）：`:380` `_load_only_addrs`；`:381` `_create_deltas_view(con, vt)`；`:382-383` `only_addrs` 表；`:384-387` `CREATE TABLE ab AS SELECT a, b, SUM(d) dd FROM deltas WHERE a IN (SELECT a FROM only_addrs) GROUP BY a, b`；`:388-398` 峰值窗口 SQL（与 `replay_pass1` 逐字相同）与 VARINT 回退 `_peaks_python(con, 0)`（读 `ab`，逐行更新峰值——**同 `(a,b)` 多行时会产生块内伪峰值，故 `ab` 必须每 `(a,b)` 至多一行**）；`:399-417` 收据（`schema/engine/producer/value_type/inputs/channels/count/addresses`）与 `os.replace` 原子写到首个 `--only-addrs` 文件所在目录（`scripts/tests/invariant_manifest.json:967-969` 登记 locator `followup_peaks`/schema `block-precision-followup/v1`/`overwrite_single`，**收据构造与原子写点不得移出本函数**）。
> ④ `main(:635)`：`:646` `--only-addrs` 参数；`:652` `a = ap.parse_args()`；`:653` `chans = preflight_channels(a.channels, a.out_dir)`；`:655-664` 临时目录、`_disk_precheck`、`memory_limit/threads/temp_directory/max_temp_directory_size/preserve_insertion_order=false`；`:666` `rej = build_events(con, chans)`；`:667-677` rejected rows 硬退（`:671` only-addrs 分支不写 `replay_stats.json`）；`:681` `maxlen = … FROM events`；`:682` `vt` 选择；`:684-685` `if a.only_addrs: raise SystemExit(followup_peaks(con, a, vt))`；`:688` 全量路径 `replay_provenance(a.out_dir, __file__)` 把实际引擎文件名与 sha 写进 `replay_stats.json`（`scripts/evm/channels_preflight.py:383`）。
> ⑤ 发布闸消费面 `scripts/report/audit_release_gate.py:1192-1264`：核 schema、engine、当前脚本 `producer.path/sha256`、`channels` 所声明 basename 对应的案内唯一常规文件及其 sha256、`value_type`、`count`、needs/trigger 输入绑定，以及 `addresses` 的覆盖范围、大小写重复和 `peak/peak_blk` 合法性。**收据字段集与含义零改动。**
> ⑥ 回归用例 `scripts/tests/test_engine_equivalence.py`：`followup_case(:236)` 用 v1csv 夹具（`_write_inputs(:45)`，tx 由计数器生成、无重复行，通道区间 `[0,99999999999)`）先跑全量取 `peaks.json`，再跑 `--only-addrs` 比对；`_write_v2_inputs(:83-140)` 只写单 `run_0`（done `from_block 0/to_block 99999999999`）并签 v2 收据；`_run(:143-146)` 子进程运行，无 `env` 参数、`timeout=120`；`main(:318-321)` 顺序调用三案例。该文件已在 `run_all.py:40` 清单内，**不改 `run_all.py`**。`channels_preflight.py:319-325` 要求多 run 的 done 区间连续无洞无重叠。
> ⑦ `replay_stream.py:152-154` 按 `(block_number, transaction_hash, log_index)` 分块区间查重复，键含区块号、检查的是重复而非同键异内容，**不能作为本工单等价性证明**；案内 `dedup_verified_segments/dedup_duplicate_keys` 只是既有运行记录。
> ⑧ DuckDB 1.5.4 `hash(a, b, c)` 可变参，返回 `UBIGINT`，`hash(...) % K` 合法（调度方本机实测）。同一 `(tag,tx,li)` 的 `hash(tag,tx,li)` 必相同 → 同桶。
> ⑨ 全量 `peaks.json` 带门槛 `peak_min = mint_total // 1000`（`:220`，`:296/:299`）；`followup_peaks` 无门槛（`_peaks_python(con, 0)`）。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/worktrees/tca-only-addrs`（分支 `fix/replay-only-addrs-scale` 的 git worktree；主仓库 `/Users/uravvv/.claude/skills/token-chip-analysis` 由另一工程占用，**不得进入、不得读写**）。开工先跑并贴进 `W1_done.md`：`git status --short`（须为空）、`git rev-parse --abbrev-ref HEAD`（须为 `fix/replay-only-addrs-scale`）、`git rev-parse --short HEAD`（记为 `START`）；`git merge-base --is-ancestor 8457f70 HEAD` 须 exit 0。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`（自建的 `.staging_w1/` 豁免）、`.hypothesis/`、`references/attic.md`、本目录以外的全部历史 `maintenance/` 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`、`/Volumes` 下任何内容。
- 0.3 **白名单**（可写）：生产 `scripts/evm/replay_duck.py`；测试 `scripts/tests/test_engine_equivalence.py`；版本登记 `VERSION`、`pyproject.toml:15`、`SKILL.md:23`、`CHANGELOG.md`；完成报告与证据 `maintenance/repair-20260925-replay-only-addrs-scale/{W1_done.md,W1_done_attempt1_stopped.md,W1_equivalence.txt,W1_timing.txt,W1_fixture_tools.py}`（`W1_fixture_tools.py` 可选，仅供证据生成，不进 run_all）。
- 0.4 **不改**：`scripts/evm/replay_stream.py`、`replay_pass1.py`、`peaks_daily.py`、`scripts/evm/channels_preflight.py`、`scripts/report/audit_release_gate.py`、`scripts/tests/run_all.py`、`scripts/tests/invariant_manifest.json`、`references/**`、`commands-staging/*`。全量路径（无 `--only-addrs`）的 `build_events`/`replay_pass1`/`emit_merged`/`replay_pass2` 计算逻辑与数值契约不变（验收口径见 0.7 第 3 条）。
- 0.5 首次修改前，以目标块内可唯一识别的非空整行为锚执行 `grep -n -F -x -- '<整行>' <文件>`，须恰命中 1 处且基线行号一致，随后逐行核对完整目标块；行号与描述不一致即停工报告（`W1_done_attempt1_stopped.md`）。修改后行号可自然移动，完成报告记录实际 diff 行号。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset/rebase；不建 worktree、不切分支。基线脚本副本：`git show 8457f70:scripts/evm/replay_duck.py > <tempdir>/scripts/evm/replay_duck.py`（保留 basename），子进程 `PYTHONPATH` 含本工作树的 `scripts/evm` 与 `scripts/lib`；分别验证基线与新脚本各自真实的 producer sha，不得为让比较通过而改写 provenance。临时目录：沙箱若不能写 `/private/tmp`，开工执行 `mkdir -p "$PWD/.staging_w1/tmp" && export TMPDIR="$PWD/.staging_w1/tmp"`（`.staging_*/` 已被 `.gitignore` 忽略）。磁盘预留 ≥20 GiB；生成、输入、输出、临时盘峰值逐项记录。
- 0.7 **等价性证据（写 `W1_equivalence.txt`）**：
  1. **主夹具**（`W1_fixture_tools.py`，固定种子，DuckDB 向量化/Arrow 批量写，不用逐行 INSERT）：规范化事件 2,000,000 行、≥5,000 地址、块范围与通道声明一致（如 `[100, 2_000_100)`）、含同块多事件、mint（from=Z）、burn（to∈{Z,DEAD}）、**在原始行层复制 ≥1,000 条完全相同行（保留 tx/li）**、v 位数 ≤37；从同一规范化事件集生成 **v2 parquet**（两个互斥连续区间 `[lo,cut)`、`[cut,hi)` 的 `run_*` 目录，各自写 logs/blocks/done——done 的 from_block/to_block/next_block 与本目录区间一致，共享正确的 capture_from 与 identity，重算 size/rows/min/max/sha256；全部目录完成后只对采集根目录签发一次 channel receipt；不得复制 `run_0` 沿用旧 done）与 **v1csv** 两种格式，保持 tx/li/区块/端点/值/时间语义一致，并确认 `preflight_channels` 通过。
  2. **补算对照**：needs 字典 + trigger_days 两文件并集 ≥1,000 址（含零事件地址、只作 from 的地址、只作 to 的地址、Z 与 DEAD 本身、**≥1 个正峰值低于全量门槛 `mint_total // 1000` 的地址**）。以**基线副本 `--only-addrs` 收据的 `addresses`** 为主对照，与施工后 `--only-addrs` 收据逐键逐值比较（`peak/peak_blk`），双格式各一次；全量 `peaks.json` 仅用于比较其中实际存在的地址（缺项不解释为零）；零事件地址与纯出方无正峰值地址断言 `{"peak":"0","peak_blk":null}`。分桶运行显式 `CHIP_REPLAY_SEG_ROWS=250000`（预期 K=8，断言每桶行数 >0 且总和＝kept_rows），另跑默认配置一次并记录实际 K。
  3. **全量路径未动**：基线副本与施工后脚本各跑一次全量（`--no-merged`）：`peaks.json/balances_final.json/mint_ledger.json` 业务键逐键逐值相等；`replay_stats.json` 除 `producer`（允许随实际脚本变化）外逐键逐值相等，差异逐项列明；另在 only-addrs 运行前后对既有全量四产物做原始字节比较（补算不覆盖）。全量 merged 与带 `--camps` 的 pass2 路径以小夹具（可复用 `followup_case` 事件）基线/施工后逐键逐值对照一次。
  4. **冲突反例（每类独立运行、独立输出目录、双格式）**：①仅某一桶内同键异值（同 tx/li 不同 v）；②同键两行 b 不同（跨块）；③同键 frm/t2 不同且仅一行命中目标地址；④同键异值且两端都**不命中**目标地址。变体在生成 done/channel receipt 之前注入（改 parquet 后必须同步重建元数据与收据，防止只命中预检 sha 拒绝），先确认预检通过；再要求基线全量、施工后全量、施工后 `--only-addrs` 三者都在冲突检查处拒绝（rc≠0、stderr 含 `去重键对应多个不同事件内容`），未生成新收据，旧收据原字节不变。
  5. **小夹具边界**：HUGEINT/VARINT 决策边界（37/38 位）、`--force-varint`、相同最高峰多次出现取首次区块、全部零增量、空并集拒绝、`CHIP_REPLAY_SEG_ROWS` 非法值（`0`/负数/`abc`/空串→rc 2、stderr 含 `CHIP_REPLAY_SEG_ROWS`、无收据；全量模式不受影响）。
  6. **执行路径证据**：施工后 `--only-addrs` 运行日志须出现 `[only-addrs] 桶 i/K` 行且 `duckdb_tables()` 在桶循环期间不含 `raw_rows`/`events`（可在日志打印一次 `SELECT list(table_name) FROM duckdb_tables()`），证明未进入全量物化；低 RSS 不单独作证明。
  7. 每个变体记录：行数、K、并集地址数、比对结论、命令、rc、超时设定；SKIP 与 PASS 分开记录。任一不符即停工报告。
- 0.8 **资源证据（写 `W1_timing.txt`）**：主夹具双格式上，施工后 `--only-addrs`（默认 `SEG_ROWS` 与 `250000` 各一次）以 `--mem-limit 2GB --threads 2` 跑：每次命令单独用 `/usr/bin/time -l` 测墙钟与峰值 RSS（注明 macOS 单位为字节）；每秒采样 `.duck_tmp` 用量（注明可能漏短暂峰值）；日志打印实际执行连接的 `current_setting('memory_limit'/'threads'/'temp_directory'/'max_temp_directory_size')` 与 DuckDB 版本；每桶扫描墙钟与行数；同参数基线副本 `--only-addrs` 的同项数据作对照（失败则记报错原文）。超时预算：夹具生成 600 s、单次大夹具重放 900 s、整组证据 3,600 s；超时记为失败证据。**不外推亿级数字**。
- 0.9 不跑 `run_all.py`（调度方本机跑）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_engine_equivalence.py`、`test_audit_release_gate.py`、`test_fault_injection.py`、`test_repair_batch_c.py`、`test_repair_batch1.py`、`test_repair_batch_d.py`、`test_review_evm_integrity.py`、`test_review_resume_integrity.py`、`test_apu_legacy_gaps.py`、`fixtures_lint.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`changelog_lint.py`。任一 FAIL 且非环境阻断即停工报告；环境阻断须给最小复现与完整异常并列入"未完成项"。

## 1. 硬约束

- 1.1 **契约不变**：`--only-addrs` 的收据字段集、字段含义、写出位置、退出码（成功 0；输入非法 2 并 stderr 含 `[only-addrs]`；rejected rows / 冲突 → `[fail-closed]` 非 0）、`value_type` 决策（`maxlen ≤ 37 → HUGEINT`，`--force-varint` 强制 VARINT）全部不变；峰值窗口 SQL（`:389-394`）、`_peaks_python` 回退、收据构造与 `os.replace` **逐字不动且留在 `followup_peaks` 内**；全量路径计算逻辑与数值契约不变（0.4/0.7-3）。不新增 CLI 参数。
- 1.2 **`--only-addrs` 模式下不得物化全量表**：不得对全体行执行 `CREATE TABLE raw_rows/events`，不得对全体行执行任何单条全局 `GROUP BY tag, tx, li`。允许：①对全体行做 COUNT/MAX 类流式聚合（reject 记账、`maxlen`）；②对全体行创建 VIEW；③按**去重键哈希分桶**逐桶执行 GROUP BY。
- 1.3 **保留完整冲突拒绝能力（与全局严格等价）**：分桶键 `hash(tag, tx, li) % K = i`（`i ∈ [0, K)`），同一 `(tag,tx,li)` 必落同一桶，因此逐桶 `GROUP BY tag, tx, li HAVING COUNT(DISTINCT (b, ts, frm, t2, v)) > 1` 的并集与 `:165-168` 的全局查重**集合相等**（含同键跨块、跨 run、跨通道的情形）。冲突查重覆盖**该桶全部保留行**（不只是地址过滤后的行）；命中即 `raise SystemExit` 同 `:173-174` 措辞（可加桶号），不写收据。docstring 写明"哈希分桶 ⇒ 同键同桶 ⇒ 与全局 GROUP BY 等价"。
- 1.4 **先过滤后去重**：桶内过滤条件 `frm IN only_addrs OR t2 IN only_addrs` 只依赖 frm/t2，而同键重复行的 frm/t2 由 1.3（覆盖全部保留行、含跨桶不可能）保证相同，故过滤与 `GROUP BY tag, tx, li` 可交换。桶内产出 `(a, b, dd)` 的口径与 `_create_deltas_view` + `:385-387` 逐条相同（t2 侧 +v 含 Z/DEAD；frm 侧 −v 且 `frm <> Z`；最后再按目标地址过滤；按 `(a,b)` 聚合）。**桶循环结束后必须 `CREATE TABLE ab AS SELECT a, b, SUM(dd) dd FROM ab_raw GROUP BY a, b`**（同一地址同块的不同事件可分属不同桶），保证 `ab` 每 `(a,b)` 至多一行（事实③ `_peaks_python` 要求）。
- 1.5 **桶数**：`kept_rows = n_source_rows − n_bad_fields − n_out_of_segment`（来自 `rej`，不得为取同一计数再扫一遍）；`K = max(1, (kept_rows + SEG_ROWS − 1) // SEG_ROWS)`，`SEG_ROWS` 为模块常量 `5_000_000`；环境变量 `CHIP_REPLAY_SEG_ROWS`（正整数）**仅供测试**覆盖，在 only-addrs 分支中于 `:652` 参数解析后、`:653` 通道预检前校验，非法值 `_fail("[only-addrs] CHIP_REPLAY_SEG_ROWS …")` 返回 2；全量模式不读该变量。哈希均匀性使每桶期望行数 ≈ `SEG_ROWS`；逐桶统计实际行数写日志，桶行数之和须等于 `kept_rows`（不等即 `[fail-closed]` 退出）；任一桶行数 > 4×`SEG_ROWS` 打印 `[only-addrs][警告] 桶偏斜` 但不中止。
- 1.6 **扫描成本如实登记**：`raw_rows` 为 VIEW，桶谓词 `hash(...) % K = i` 不可下推，每桶都会完整读取输入（v2 parquet 解码/v1csv 解析）；K 桶 ⇒ K 次全量读取（外加 reject 记账与 `maxlen` 各一次流式扫描）。这是本方案以 IO 换内存的代价，须在 docstring 与 CHANGELOG 写明，并在 0.8 记录每桶扫描墙钟；**不得**为省 IO 引入对全量行的物化（1.2）。
- 1.7 **资源**：每桶临时表用完即 `DROP`；`ab_raw` 只累积过滤后的 `(a, b, dd)` 行；不改 `memory_limit/threads/temp_directory/max_temp_directory_size/preserve_insertion_order` 的设置方式与位置（`:659-664`）。日志每桶一行：`[only-addrs] 桶 i/K 行 n 过滤后 m 累计 ab_raw 行 t 耗时 s`（实测数字），结束一行汇总（K、总行数、`ab` 行数、墙钟）。
- 1.8 生产改动以增删合计 ≤160 行、≤3 个模块级私有 helper（`_` 前缀）为目标；不得为满足行数目标省略冲突检查、记账断言或必要回退；若完整实现超限，先在 `W1_done_attempt1_stopped.md` 提交逐项行数预算与原因，由修订工单确认。不删除、不重命名现有函数；允许 `build_events` 新增 keyword-only 参数 `materialize=True`，允许 `followup_peaks` 新增 keyword-only 参数 `kept_rows=None`（`None` 保留原 `events` 路径，兼容既有三参数调用）；其余函数签名不变。模块 docstring（`:2-35`，在结束引号 `:35` 之前）追加 ≤ 8 行"9.2.2 --only-addrs 哈希分桶流式"说明（不物化；同键同桶等价；K 次读取代价；`CHIP_REPLAY_SEG_ROWS` 仅测试）。用法段 `:31-34` 不变。
- 1.9 文档字节：`references/**`、`commands-staging/*` 零改动（`git diff` 验证）；`SKILL.md` 仅 `:23` 版本号；CHANGELOG 索引行 ≤ 200 B（2.3 给定文本 179 B）。
- 1.10 diff 口径：`git diff --stat 8457f70`（允许含开工前已存在的本工程工单/复核文件）与 `git diff --stat START`（只允许 0.3 白名单）分别记录。

## 2. 逐条施工

### 2.1 `scripts/evm/replay_duck.py`

- (a) `build_events`：锚 `:160` 整行 `    con.execute(f"CREATE TABLE raw_rows AS {union}" if len(parts) == 1`（唯一）。新增 keyword-only 参数 `materialize=True`；`materialize=False` 时：把 `raw_rows` 建为 VIEW（`CREATE VIEW raw_rows AS …`，同 union 文本，单/多 parts 两种写法对应），**跳过** `:165-183`（冲突查重、events 物化、DROP、n_events/n_dedup_removed 记账），`acc["n_dedup_removed"]` 不写，打印 `合计保留源行 {kept_rows}（only-addrs：不物化，冲突查重在分桶阶段执行）` 后 `return acc`。`materialize=True` 路径逐字不动。
- (b) `main`：在 `:652` `a = ap.parse_args()` 之后、`:653` 预检之前插入 only-addrs 分支的 `CHIP_REPLAY_SEG_ROWS` 校验（1.5）。锚 `:666` 整行 `    rej = build_events(con, chans)`（唯一）→ `rej = build_events(con, chans, materialize=not a.only_addrs)`。锚 `:681` 整行 `    maxlen = con.execute("SELECT COALESCE(MAX(LENGTH(v)), 0) FROM events").fetchone()[0]`（唯一）→ `src = "raw_rows" if a.only_addrs else "events"` 后从 `{src}` 取（only-addrs 下为流式扫描）。锚 `:685` 整行 `        raise SystemExit(followup_peaks(con, a, vt))`（唯一）→ 传入 `kept_rows=rej["n_source_rows"] - rej["n_bad_fields"] - rej["n_out_of_segment"]`。
- (c) `followup_peaks`（锚 `def followup_peaks(con, a, vt):` 唯一；核对完整函数 `:376-417` 后只改本函数内的 `:381` 与 `:384-387`）：签名改 `def followup_peaks(con, a, vt, *, kept_rows=None):`。`kept_rows is None` → 原路径逐字不动。否则：
  1. `only_addrs` 表照旧（`:382-383`）。
  2. `K` 按 1.5；`CREATE TABLE ab_raw (a VARCHAR, b BIGINT, dd {vt})`。
  3. 逐桶 `i in range(K)` 执行（`{K}/{i}/{vt}/{Z}` 代入；伪 SQL，施工可等价改写但语义逐条对应）：
     ```sql
     -- 桶内冲突查重（覆盖该桶全部保留行）
     SELECT COUNT(*) FROM (SELECT tag, tx, li FROM raw_rows WHERE hash(tag, tx, li) % {K} = {i}
                           GROUP BY tag, tx, li HAVING COUNT(DISTINCT (b, ts, frm, t2, v)) > 1)
     -- 命中>0：取样 LIMIT 3 后 raise SystemExit("[fail-closed] {n} 个去重键对应多个不同事件内容（桶 i/K，样本 …）——数据损坏，先仲裁再重放")
     -- 桶内行数记账
     SELECT COUNT(*) FROM raw_rows WHERE hash(tag, tx, li) % {K} = {i}
     -- 桶内先过滤后去重，再产 (a,b,dd)
     INSERT INTO ab_raw
     WITH seg AS (
       SELECT ANY_VALUE(b) b, ANY_VALUE(frm) frm, ANY_VALUE(t2) t2, ANY_VALUE(v) v
       FROM raw_rows
       WHERE hash(tag, tx, li) % {K} = {i}
         AND (frm IN (SELECT a FROM only_addrs) OR t2 IN (SELECT a FROM only_addrs))
       GROUP BY tag, tx, li),
     d AS (
       SELECT t2 AS a, b, CAST(v AS {vt}) AS d FROM seg
       UNION ALL
       SELECT frm, b, -CAST(v AS {vt}) FROM seg WHERE frm <> '{Z}')
     SELECT a, b, SUM(d) FROM d WHERE a IN (SELECT a FROM only_addrs) GROUP BY a, b
     ```
     每桶日志按 1.7；桶循环结束核对行数总和＝`kept_rows`（1.5）。
  4. `CREATE TABLE ab AS SELECT a, b, SUM(dd) dd FROM ab_raw GROUP BY a, b`；`DROP TABLE ab_raw`。
  5. `:388-398` 峰值 SQL 与回退、`:399-417` 收据与 `os.replace` **逐字不动**（只读 `ab`）。
  6. 新路径不调用 `_create_deltas_view`（保留给全量路径）。
- (d) 模块 docstring 追加（1.8）；用法段不变；不新增 CLI 参数。

### 2.2 `scripts/tests/test_engine_equivalence.py` —— 回归

- `_run(:143)` 扩展为 `def _run(tmp, cmd, *, env=None, timeout=120):`，把 `env=env, timeout=timeout` 传给 `subprocess.run`（既有调用行为不变）。
- 保留 `followup_case(:236)` 全部断言；在其后新增 `followup_bucketed_case()`（并在 `main(:318-321)` 的 `followup_case()` 之后调用）。使用**单 run** v2 parquet 夹具（复用 `_write_v2_inputs`；允许在测试内以最小改动支持"原始行层复制"与"块范围声明"，若改 `_write_v2_inputs` 签名须给默认值保持既有调用不变）：
  - 规范化事件 300 行、块范围声明与实际一致（如 `[100,160)`），含同块多事件、mint、burn（Z 与 DEAD）；**在 tx/li 已生成后的原始行层复制 ≥20 行**（保留 tx/li，形成相同去重键）。
  - 子进程 env `{**os.environ, "CHIP_REPLAY_SEG_ROWS": "50"}`（预期 K=6），`timeout=300`。
  - 先跑基线路径对照物：本用例内以**同一脚本**先跑全量（`--no-merged`）取 `peaks.json`；再跑 `--only-addrs`（needs 字典含 ≥3 址 + Z + DEAD + 一个零事件地址；trigger_days 含 ≥2 址，其中 ≥1 址与 needs 重叠）：断言收据 `addresses` 键集＝并集、`peaks.json` 中存在的地址 `peak/peak_blk` 相等、含 ≥1 个低于门槛的正峰值地址由测试内独立 Python 累计（按事件逐块累加、块末口径、严格大于更新）算出的期望值相等、零事件地址为 `{"peak":"0","peak_blk":None}`、`inputs` 两项 sha 正确、`count` 正确；断言 stdout 含 `[only-addrs] 桶 ` 且 K=6、桶行数之和＝300+复制行数；断言全量产物字节未变。
  - 冲突子例（各独立目录）：①同 tx/li 不同 `data`；②同 tx/li 不同 `block_number`（跨块）。均在生成 done/收据前注入 → `--only-addrs` rc≠0、stderr 含 `去重键对应多个不同事件内容`、无收据；全量路径同样 rc≠0。
  - `CHIP_REPLAY_SEG_ROWS` 非法值 `0`/`-1`/`abc`/空串 → rc 2、stderr 含 `CHIP_REPLAY_SEG_ROWS`、无收据；同一非法 env 下全量模式 rc 0。
- 断言写法遵循本文件既有风格（`assert …, msg`）。

### 2.3 版本登记 9.2.2

- `VERSION` `9.2.1`→`9.2.2`；`pyproject.toml:15` `version = "9.2.1"`→`"9.2.2"`；`SKILL.md:23` `<!-- skill-version-source: VERSION; skill-version: 9.2.1 -->`→`9.2.2`。
- `CHANGELOG.md:13` 整行原文（唯一，以 `- **9.2.1**（2026-09-25）修复标签 CLI 盲化漏封` 开头）之前插入一行（含换行 179 B）：

```text
- **9.2.2**（2026-09-25）`replay_duck --only-addrs` 按去重键哈希分桶流式补算，免全量事件表物化；冲突拒绝、收据与全量路径不变，档位 修。
```

- `CHANGELOG.md:106` 整行 `## [9.2.1] - 2026-09-25 — 标签 CLI 惯犯结构化标记盲化补漏`（唯一）之前插入 `## [9.2.2] - 2026-09-25 — replay_duck --only-addrs 哈希分桶流式补算` 详细段（同格式四条：出处与根因 / 改法（哈希分桶⇒同键同桶⇒与全局查重等价；K 次读取换内存）/ 验证（引用 `W1_equivalence.txt`、`W1_timing.txt` 的实测计数与墙钟，不预填结论）/ 成本与边界（K 次全量读取代价、`CHIP_REPLAY_SEG_ROWS` 仅测试、全量路径未动、**合并后案卷须用最终合并版脚本重跑 `--only-addrs` 再过发布闸，旧收据不得沿用或手改 sha**）），末尾空一行。

## 3. 完成报告 `W1_done.md`

首行 `# W1 完成：<一句话>` 或 `# W1 停工：<原因>`。含：开工基线四项输出；等价性证据摘要（指向 `W1_equivalence.txt`，逐项列 0.7 的 1–7）；资源证据摘要（指向 `W1_timing.txt`）；每处施工实际 diff 行号与两种 `git diff --stat`（1.10）；定向测试尾行；与工单差异（若有，逐条说明理由）；末尾披露是否读过禁读路径。不 commit。

## 4. 交接（调度方执行，施工方不做）
合并到 main 后，QUQ 案卷必须用最终合并版 `scripts/evm/replay_duck.py --only-addrs` 重新生成 `block_precision_followup.json`（producer.sha256 随脚本变），再跑 `stage2_closeout check` 与发布闸；施工夹具通过不替代案卷重跑。
