# 工单 W1（v1）：`replay_duck.py --only-addrs` 分段流式补算，消除对全量事件表的物化与全局 GROUP BY——版本 9.2.2

> 出处：QUQ(BSC) 0922 案 −2 收口（案卷由调度方持有，本仓库不含）。发布闸 `audit_release_gate.py:1192-1211` 要求 `data/peaks/block_precision_followup.json` 由 `replay_duck.py --only-addrs` 本体产出并绑定脚本 sha。该路径在 1.097 亿行（v2 parquet，20 个 run 目录，7.1 GB）上六次失败：`--mem-limit` 3/8/12/6/8/12 GB、`--threads` 2/6/4/4/4/1、临时目录本盘（余量 46–61 GB）与外接盘（820 GB）——本盘四次撞 `max_temp_directory_size`（38.1/41.9/43.7/56.8 GiB），外接盘两次在 DuckDB 内存上限内 OOM（"could not allocate block" 7.4/7.4 GiB；"failed to pin block" 11.1/11.1 GiB），六次全部死在 `build_events` 的 `CREATE TABLE events AS … FROM raw_rows GROUP BY tag, tx, li`（`:176-179`）。机器 8 核 16 GB RAM，DuckDB 1.5.4。同一数据在 −1 阶段由 `replay_stream.py`（分段查重、不落表）4 GB/66 s 完成。
> 根因：`--only-addrs` 只需要地址子集的逐块余额增量，但现路径先把 1.1 亿行 `raw_rows` 整表物化（`:160-161`）、再对全表做冲突查重（`:165-168`）与去重物化 `events`（`:175-179`），子集过滤（`:385-387`）在这之后才发生。三份宽表（tx 66 字符、frm/t2 42 字符、v 十进制串）同时在内存/临时盘上，需求超过本机上限且随余量增长而增长（未测出上界）。
> 事实（调度方在本分支基线 `8457f70` 亲核，`grep -n -F` 逐锚复验）：
> ① `build_events(:89)`：逐通道生成 SELECT 片段 `parts`，`:159` `union = " UNION ALL ".join(parts)`，`:160-161` `CREATE TABLE raw_rows AS …`；`:165-168` 冲突查重（`GROUP BY tag, tx, li HAVING COUNT(DISTINCT (b, ts, frm, t2, v)) > 1`）；`:169-174` 命中即 `raise SystemExit("[fail-closed] … 数据损坏，先仲裁再重放")`；`:175-179` `CREATE TABLE events AS SELECT ANY_VALUE(b) b, ANY_VALUE(ts) ts, tx, li, ANY_VALUE(frm) frm, ANY_VALUE(t2) t2, ANY_VALUE(v) v FROM raw_rows GROUP BY tag, tx, li`；`:180` `DROP TABLE raw_rows`；`:181-183` `n_events`/`n_dedup_removed` 记账；`:185` `return acc`。reject 记账（`n_source_rows/n_bad_fields/n_out_of_segment`）在物化之前用 COUNT 扫描完成（v2 路径 `:104-113`，v1csv 路径 `:131-143`），不依赖 `raw_rows` 表。
> ② `_create_deltas_view(:188)`：`CREATE VIEW deltas AS SELECT t2 AS a, b, CAST(v AS {vt}) AS d FROM events UNION ALL SELECT frm, b, -CAST(v AS {vt}) FROM events WHERE frm <> '{Z}'`——mint（frm=Z）不减 Z 余额；burn（t2∈{Z,DEAD}）照加。
> ③ `followup_peaks(:376)`：`:380` `_load_only_addrs`；`:381` `_create_deltas_view(con, vt)`；`:382-383` `only_addrs` 表；`:384-387` `CREATE TABLE ab AS SELECT a, b, SUM(d) dd FROM deltas WHERE a IN (SELECT a FROM only_addrs) GROUP BY a, b`；`:388-398` 峰值窗口 SQL（与 `replay_pass1` 逐字相同）与 VARINT 回退 `_peaks_python(con, 0)`（读 `ab`）；`:399-417` 收据（`schema/engine/producer/value_type/inputs/channels/count/addresses`）写到首个 `--only-addrs` 文件所在目录。
> ④ `main(:635)`：`:646` `--only-addrs` 参数；`:655-664` 临时目录、`_disk_precheck`、`memory_limit/threads/temp_directory/max_temp_directory_size/preserve_insertion_order=false`；`:666` `rej = build_events(con, chans)`；`:667-677` rejected rows 硬退（`:671` only-addrs 分支不写 `replay_stats.json`）；`:681` `maxlen = … FROM events`；`:682` `vt` 选择；`:684-685` `if a.only_addrs: raise SystemExit(followup_peaks(con, a, vt))`。
> ⑤ 发布闸消费面（`scripts/report/audit_release_gate.py:1192-1235`）只核收据字段：`schema == "block-precision-followup/v1"`、`engine == "replay_duck.py"`、`producer.path/sha256` 绑当前脚本、`channels` 绑案内唯一 `channels.json`、`value_type ∈ {HUGEINT, VARINT}`、`count == len(addresses)`、`inputs` 绑 needs/trigger 两文件 sha。**收据字段集与含义零改动**。
> ⑥ 回归用例 `scripts/tests/test_engine_equivalence.py`：`followup_case(:236)` 用 v1csv 夹具（`_write_inputs(:45)`，tx 由计数器生成、无重复行）先跑全量取 `peaks.json`，再跑 `--only-addrs` 比对 `peak/peak_blk`、零事件地址、坏输入/坏事件不覆盖全量产物；`_write_v2_inputs(:83)` 能写 v2 parquet 夹具；`_run(:143)` 子进程运行，`timeout=120`；`main(:318-321)` 顺序调用三案例。该文件已在 `run_all.py:40` 清单内，**不改 `run_all.py`**。
> ⑦ `replay_stream.py:21-23,147-155` 的分段查重口径："把全块空间切 N 段、逐段 GROUP BY 查重"；同一 `(tag, tx, li)` 键只会出现在同一区块（tx 属于唯一区块），故按区块分段的段内查重与全局查重等价；−1 阶段 QUQ 的 `replay_stats.json` 记 `dedup_verified_segments: 8, dedup_duplicate_keys: 0`。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/worktrees/tca-only-addrs`（分支 `fix/replay-only-addrs-scale` 的 git worktree，主仓库 `/Users/uravvv/.claude/skills/token-chip-analysis` 由另一工程占用，**不得进入、不得读写**）。开工先跑并贴进 `W1_done.md`：`git status --short`（须为空）、`git rev-parse --abbrev-ref HEAD`（须为 `fix/replay-only-addrs-scale`）、`git rev-parse --short HEAD`；`git merge-base --is-ancestor 8457f70 HEAD` 须 exit 0。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、本目录以外的全部历史 `maintenance/` 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`、`/Volumes` 下任何内容。
- 0.3 **白名单**（可写）：生产 `scripts/evm/replay_duck.py`；测试 `scripts/tests/test_engine_equivalence.py`；版本登记 `VERSION`、`pyproject.toml:15`、`SKILL.md:23`、`CHANGELOG.md`；完成报告与证据 `maintenance/repair-20260925-replay-only-addrs-scale/{W1_done.md,W1_equivalence.txt,W1_timing.txt,W1_fixture_tools.py}`（`W1_fixture_tools.py` 可选，仅供证据生成，不进 run_all）。
- 0.4 **不改**：`scripts/evm/replay_stream.py`、`replay_pass1.py`、`peaks_daily.py`、`scripts/lib/channels_preflight.py`、`scripts/report/audit_release_gate.py`、`scripts/tests/run_all.py`、`references/**`、`commands-staging/*`。全量路径（无 `--only-addrs`）的 `build_events`/`replay_pass1`/`emit_merged`/`replay_pass2` 行为与产物**逐字节不变**。
- 0.5 首次修改前，以目标块内可唯一识别的非空整行为锚执行 `grep -n -F -x -- '<整行>' <文件>`，须恰命中 1 处且基线行号一致，随后逐行核对完整目标块；行号与描述不一致即停工报告（`W1_done_attempt1_stopped.md`）。修改后行号可自然移动，完成报告记录实际 diff 行号。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset/rebase；不建 worktree、不切分支。基线脚本副本：`git show 8457f70:scripts/evm/replay_duck.py > <tempdir>/replay_duck_base.py`（其 `sys.path.insert` 按自身位置找 `../lib`，故副本须放在 `<tempdir>/evm/` 下并把 `<repo>/scripts/lib` 加入 `PYTHONPATH`，或直接 `cp` 到 `<tempdir>/scripts/evm/` 并同步 `cp -r scripts/lib <tempdir>/scripts/lib`）。临时目录：沙箱若不能写 `/private/tmp`，开工执行 `mkdir -p "$PWD/.staging_w1/tmp" && export TMPDIR="$PWD/.staging_w1/tmp"`（`.staging_*/` 已被 `.gitignore` 忽略；"禁读 `.staging_*`"对你自建的这一个目录豁免）。
- 0.7 **等价性证据（写 `W1_equivalence.txt`）**：
  - 主夹具：由 `W1_fixture_tools.py`（或测试内函数）用固定种子生成 ≥2,000,000 行事件、≥5,000 地址、块跨度 ≥2,000,000（保证 §2.1 分段数 ≥8）、含：同块多事件、mint（from=Z）、burn（to∈{Z,DEAD}）、**完全相同的重复行**（同 tag/tx/li 同内容，v2 与 v1csv 各 ≥1,000 行）、v 位数 ≤37；以 v2 parquet（按 `_write_v2_inputs(:83)` 的列结构，多个 `run_*` 目录）与 v1csv 两种格式各写一份（内容语义相同）。
  - 对照：对同一夹具，**基线副本全量路径** `peaks.json`（`--no-merged`）与 **施工后 `--only-addrs`**（needs 字典 + trigger_days 两文件，并集覆盖 ≥1,000 址，含零事件地址、只作 from 的地址、只作 to 的地址、Z 与 DEAD 本身）逐址比对 `peak`/`peak_blk`：**须逐键逐值相等**；零事件地址须 `{"peak": "0", "peak_blk": None}`。再以**施工后全量路径**跑同夹具，`peaks.json/replay_stats.json/balances_final.json/mint_ledger.json` 与基线副本产物**逐字节相等**（证明全量路径未动）。
  - 冲突夹具：在主夹具上注入 ≥1 组"同 `(tag,tx,li)` 不同 v"的行，分别落在第 1 段与最后一段：施工后 `--only-addrs` 与全量路径都须以 `[fail-closed]` 退出（rc≠0、stderr 含"去重键对应多个不同事件内容"）、不写收据；基线全量路径同样拒绝（三者一致）。
  - 记录每个变体：行数、分段数、并集地址数、比对结论、命令与 rc。任一不符即停工报告。
- 0.8 **资源证据（写 `W1_timing.txt`）**：主夹具（≥2,000,000 行）上施工后 `--only-addrs` 以 `--mem-limit 2GB --threads 2` 跑：墙钟、峰值 RSS（`resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` 或 `/usr/bin/time -l`）、`.duck_tmp` 峰值大小（每秒 `du -s` 采样或运行后 DuckDB `temp_directory` 峰值不可得时注明）、DuckDB 版本、有效 `memory_limit`/`threads`/`temp_directory`/`max_temp_directory_size`（用 `SELECT current_setting(...)` 打印进日志）；同参数基线副本 `--only-addrs` 的同项数据作对照（基线若在 2GB 下失败，记录报错原文即可）。**不要**外推亿级数字，只报实测。
- 0.9 不跑 `run_all.py`（调度方本机跑）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_engine_equivalence.py`、`scripts/tests/test_audit_release_gate.py`、`test_fault_injection.py`、`test_repair_batch_c.py`、`test_repair_batch1.py`、`test_repair_batch_d.py`、`test_review_evm_integrity.py`、`test_review_resume_integrity.py`、`test_apu_legacy_gaps.py`、`fixtures_lint.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`。任一 FAIL 且非环境阻断（沙箱建不了目录/无网络）即停工报告；环境阻断须给最小复现与完整异常并列入"未完成项"。

## 1. 硬约束

- 1.1 **契约不变**：`--only-addrs` 的收据字段集、字段含义、写出位置（首个 `--only-addrs` 文件所在目录）、退出码（成功 0；输入非法 2 并 stderr 含 `[only-addrs]`；rejected rows / 冲突 → `[fail-closed]` 非 0）、`value_type` 决策（`maxlen ≤ 37 → HUGEINT`，`--force-varint` 强制 VARINT）全部不变；峰值窗口 SQL（`:389-394`）与 `_peaks_python` 回退**逐字不动**；全量路径逐字节不变（0.4）。不新增 CLI 参数。
- 1.2 **`--only-addrs` 模式下不得物化全量表**：不得对全体行执行 `CREATE TABLE raw_rows/events`，不得对全体行执行任何单条全局 `GROUP BY tag, tx, li`。允许：①对全体行做 **COUNT/MAX 类流式聚合**（reject 记账、`maxlen`）；②对全体行创建 **VIEW**；③按区块区间**分段**执行 GROUP BY（每段行数由常量控制）。
- 1.3 **分段等价**：按 `(tag, tx, li)` 去重与冲突查重改为**按区块区间分段**执行，段内语义与 `:165-179` 逐字对应（`HAVING COUNT(DISTINCT (b, ts, frm, t2, v)) > 1` 即冲突；`ANY_VALUE` 取内容）。等价前提写进 docstring：同一 `(tag, tx, li)` 只出现在同一区块（与 `replay_stream.py` 同口径，事实⑦）。冲突命中即 `raise SystemExit` 同 `:173-174` 措辞（可加段号）；冲突查重覆盖**该段全部行**（不只是过滤后的行）。
- 1.4 **先过滤后去重的正确性**：过滤条件 `frm IN only_addrs OR t2 IN only_addrs` 只依赖 frm/t2，而同键重复行的 frm/t2 由 1.3 的冲突查重保证相同，故过滤与 `GROUP BY tag, tx, li` 可交换；docstring 写明。段内产出 `(a, b, dd)` 聚合行的口径与 `_create_deltas_view` + `:385-387` 逐条相同（t2 侧 +v，frm 侧 −v 且 `frm <> Z`；Z/DEAD 作 t2 照加）。
- 1.5 **段划分**：区间 `[lo, hi)` 取所有通道 `lo` 最小值与 `hi` 最大值（通道段互斥由 `preflight_channels` 保证）；段数 `K = max(1, ceil(kept_rows / SEG_ROWS))`，`kept_rows = n_source_rows − n_bad_fields − n_out_of_segment`，`SEG_ROWS` 为模块常量 `5_000_000`，允许环境变量 `CHIP_REPLAY_SEG_ROWS`（正整数）覆盖**仅供测试**；段边界按块号均分（最后一段含 `hi`），每段 SQL 用 `b >= s0 AND b < s1` 谓词直接下推到 parquet/CSV 读取。段内行数之和须等于 `kept_rows`（记账断言，不等即 `[fail-closed]` 退出）。
- 1.6 **资源**：每段临时表用完即 `DROP`；`ab` 只累积过滤后的 `(a, b, dd)` 行（并集地址相关行）；不改 `memory_limit/threads/temp_directory/max_temp_directory_size/preserve_insertion_order` 的设置方式与位置（`:659-664`）。日志每段一行：`[only-addrs] 段 i/K [s0,s1) 行 n 过滤后 m 累计 ab 行 t`（数字为实测），结束一行汇总（段数、总行数、`ab` 行数、墙钟）。
- 1.7 生产改动 ≤ 140 行（增删合计），允许 ≤ 3 个模块级私有 helper（`_` 前缀）；不删除、不重命名任何现有公开函数（`build_events`/`followup_peaks`/`_create_deltas_view`/`_load_only_addrs`/`_peaks_python` 签名不变；如需让 `build_events` 在 only-addrs 下只建 VIEW，用**新增的关键字参数并给默认值**，默认行为不变）。模块 docstring 追加 ≤ 6 行"9.2.2 --only-addrs 分段流式"说明。
- 1.8 文档字节：`references/**`、`commands-staging/*` 零改动（`git diff` 验证）；`SKILL.md` 仅 `:23` 版本号；CHANGELOG 索引行 ≤ 200 B。
- 1.9 `git diff --stat 8457f70` 只含 0.3 白名单。

## 2. 逐条施工

### 2.1 `scripts/evm/replay_duck.py`

- (a) `build_events`：锚 `:160-161`（`    con.execute(f"CREATE TABLE raw_rows AS {union}" if len(parts) == 1` 起）。新增关键字参数 `materialize=True`；`materialize=False` 时：把 `raw_rows` 建为 `VIEW`（`CREATE VIEW raw_rows AS …`，同 union 文本），**跳过** `:165-183`（冲突查重、events 物化、DROP、n_events/n_dedup_removed 记账），`acc["n_dedup_removed"]` 不写（或写 `None`），打印一行 `合计源行 {kept_rows}（only-addrs：不物化）` 后 `return acc`。`materialize=True` 路径逐字不动。
- (b) `main`：锚 `:666` 整行 `    rej = build_events(con, chans)`（唯一）→ `rej = build_events(con, chans, materialize=not a.only_addrs)`。锚 `:681` 整行 `    maxlen = con.execute("SELECT COALESCE(MAX(LENGTH(v)), 0) FROM events").fetchone()[0]`（唯一）→ only-addrs 下改从 `raw_rows`（VIEW）取 `MAX(LENGTH(v))`（流式扫描，允许），全量路径仍从 `events` 取；写法如 `src = "raw_rows" if a.only_addrs else "events"`。
- (c) `followup_peaks`：锚 `:381` 整行 `    _create_deltas_view(con, vt)`（在函数内唯一；`:198` 另一处属 `replay_pass1`，不动）与 `:384-387`（`CREATE TABLE ab AS … FROM deltas WHERE a IN (SELECT a FROM only_addrs) GROUP BY a, b`）。改为分段构建：
  1. `only_addrs` 表照旧（`:382-383`）。
  2. 取 `kept_rows`（由 `rej` 传入或函数内从 `raw_rows` COUNT 一次）、`[lo, hi)`（从 `chans` 取，需把 `chans` 或 `(lo, hi, kept_rows)` 作为参数传入 `followup_peaks`——可通过新增带默认值的关键字参数实现，调用点 `:685` 同步传入）；按 1.5 算段边界。
  3. `CREATE TABLE ab (a VARCHAR, b BIGINT, dd {vt})`；逐段执行（伪 SQL，`{s0}/{s1}/{vt}/{Z}` 代入）：
     ```sql
     -- 段内冲突查重（覆盖该段全部行）
     SELECT COUNT(*) FROM (SELECT tag, tx, li FROM raw_rows WHERE b >= {s0} AND b < {s1}
                           GROUP BY tag, tx, li HAVING COUNT(DISTINCT (b, ts, frm, t2, v)) > 1)
     -- 命中>0：取样 LIMIT 3 后 raise SystemExit("[fail-closed] {n} 个去重键对应多个不同事件内容（段 i [s0,s1)，样本 …）——数据损坏，先仲裁再重放")
     -- 段内先过滤后去重，再产 (a,b,dd)
     INSERT INTO ab
     WITH seg AS (
       SELECT ANY_VALUE(b) b, ANY_VALUE(frm) frm, ANY_VALUE(t2) t2, ANY_VALUE(v) v
       FROM raw_rows
       WHERE b >= {s0} AND b < {s1}
         AND (frm IN (SELECT a FROM only_addrs) OR t2 IN (SELECT a FROM only_addrs))
       GROUP BY tag, tx, li),
     d AS (
       SELECT t2 AS a, b, CAST(v AS {vt}) AS d FROM seg
       UNION ALL
       SELECT frm, b, -CAST(v AS {vt}) FROM seg WHERE frm <> '{Z}')
     SELECT a, b, SUM(d) FROM d WHERE a IN (SELECT a FROM only_addrs) GROUP BY a, b
     ```
     段内行数记账：`SELECT COUNT(*) FROM raw_rows WHERE b >= {s0} AND b < {s1}` 累加，结束时与 `kept_rows` 比对（1.5）。
  4. 段循环结束后，`:388-398` 峰值 SQL 与回退**逐字不动**（它们只读 `ab`）；`:399-417` 收据逐字不动。
  5. 不再调用 `_create_deltas_view`（该函数保留给全量路径）。
- (d) 模块 docstring（`:1-39` 内）追加 ≤ 6 行：9.2.2 `--only-addrs` 分段流式（不物化 raw_rows/events；按块区间分段查重+过滤+聚合；等价前提；`CHIP_REPLAY_SEG_ROWS` 仅测试用）。
- (e) 用法段 `:36-38` 不变（无新 CLI 参数）。

### 2.2 `scripts/tests/test_engine_equivalence.py` —— 回归

- 保留 `followup_case(:236)` 全部断言；在其后新增 `followup_segmented_case()`（并在 `main(:318-321)` 的 `followup_case()` 之后调用），用 v2 parquet 夹具（复用 `_write_v2_inputs`，若其只写单 `run_0` 目录可在测试内扩展为 ≥2 个 `run_*` 目录，须保持 `channels.json` 合法且 `preflight_channels` 通过）：
  - 事件 ≥ 300 条、块跨度 ≥ 60、含同块多事件、mint、burn（Z 与 DEAD）、**完全相同重复行 ≥ 20**；`CHIP_REPLAY_SEG_ROWS=50` 使段数 ≥ 4（子进程 env 传入）。
  - 先跑全量（`--no-merged`）取 `peaks.json`；再跑 `--only-addrs`（needs 字典含 ≥3 址 + 一个零事件地址；trigger_days 含 ≥2 址，其中 ≥1 址与 needs 重叠）：断言收据 `addresses` 键集 = 并集、每址 `peak/peak_blk` 与 `peaks.json` 相等、零事件址为 `{"peak":"0","peak_blk":None}`、`inputs` 两项 sha 正确、`count` 正确；断言 stdout 含 `[only-addrs] 段 ` 且段数 ≥ 4；断言全量产物字节未变。
  - 冲突子例：复制夹具，篡改一条重复行的 `data`（同 tx/li 不同 v）→ `--only-addrs` rc≠0、stderr 含 `去重键对应多个不同事件内容`、无收据；全量路径同样 rc≠0。
  - `CHIP_REPLAY_SEG_ROWS=0`/`abc` → rc 2 并 stderr 含 `CHIP_REPLAY_SEG_ROWS`（非法覆盖值 fail-closed）。
- 断言写法遵循本文件既有风格（`assert …, msg`），子进程 `timeout` 可按需提高到 300。

### 2.3 版本登记 9.2.2

- `VERSION` `9.2.1`→`9.2.2`；`pyproject.toml:15` `version = "9.2.1"`→`"9.2.2"`；`SKILL.md:23` `<!-- skill-version-source: VERSION; skill-version: 9.2.1 -->`→`9.2.2`。
- `CHANGELOG.md:13` 整行原文（唯一，以 `- **9.2.1**（2026-09-25）修复标签 CLI 盲化漏封` 开头）之前插入一行（含换行 ≤ 200 B）：

```text
- **9.2.2**（2026-09-25）`replay_duck --only-addrs` 分段流式补算：不再物化全量 raw_rows/events，按块区间分段查重+过滤+聚合；收据契约与全量路径不变，档位 修。
```

- `CHANGELOG.md:106` 整行 `## [9.2.1] - 2026-09-25 — 标签 CLI 惯犯结构化标记盲化补漏`（唯一）之前插入 `## [9.2.2] - 2026-09-25 — replay_duck --only-addrs 分段流式补算` 详细段（同格式四条：出处与根因 / 改法 / 验证（引用 `W1_equivalence.txt`、`W1_timing.txt` 的实测计数与墙钟，不预填结论）/ 成本与边界（等价前提、`CHIP_REPLAY_SEG_ROWS` 仅测试、全量路径未动、亿级实跑由调度方另证）），末尾空一行。

## 3. 完成报告 `W1_done.md`

首行 `# W1 完成：<一句话>` 或 `# W1 停工：<原因>`。含：开工基线四项输出；等价性证据摘要（指向 `W1_equivalence.txt`）；资源证据摘要（指向 `W1_timing.txt`）；每处施工实际 diff 行号与 `git diff --stat 8457f70`；定向测试尾行；与工单差异（若有，逐条说明理由）；末尾披露是否读过禁读路径。不 commit。
