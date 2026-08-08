# R9 批一施工进度：公共原语和真实边界

- 冻结基线：`main@63cf715cb6d11f6669f4370c77574930da655891`
- 施工分支：`fix/r9-closure-20260807`
- 批一边界：只执行 PLAN「批一：公共原语和真实边界」与 T1 台账追加；不处理 R9-01 实现，不接入 Solana 正式 callsite，不改能力矩阵，不改 `VERSION`，不做 git 写操作。

## 开工工单（按 `references/maintenance-review-repair.md` 五栏）

### R9-02：真实 anchor producer 与 time consumer 断契约

1. 不变量：正式 EVM plan 必须由登记 producer 针对同一 chain/token/final block 和真实输入生成，所有探测块不得越过 final block，consumer 只接收可独立校验的真实 producer receipt。
2. 同族清单：`rg -n "anchor_plan|final_block|day_end_block|forced_points|matrix_points" scripts/lib scripts/tests`；正式 producer=`scripts/lib/anchor_plan.py`，正式 consumer=`scripts/lib/time_spotcheck.py`，正向纵切片=`scripts/tests/test_batch3_evm_vertical_slice.py`，单元契约=`scripts/tests/test_time_spotcheck.py`。
3. 三件套测试：a. `B1-R9-02-PRODUCER-CONSUMER` 真实运行 producer 后喂 consumer；b. final block 缺失/不一致/探测块越界；c. plan/receipt 缺失、篡改或 producer 发布失败必须非零且不得被 consumer 接收。
4. 新建代码自审：字段来源必须绑定真实输入哈希、producer 代码身份和 final block；读/解析/receipt/发布任一失败均不得产生可消费 PASS。
5. 归因预判：修复中新引入；旧 cutoff+1 假 PASS 已被 consumer 堵住，本缺陷是修复 diff 新造成 producer/consumer 不兼容。

### R9-03：pool swaps 失败退出与 stale canonical

1. 不变量：网络、解析、cursor 或发布失败时最终进程必须非零，本轮启动前旧 canonical 必须退出当前正式位置，失败不得留下本轮可消费结果。
2. 同族清单：`rg -n "stale|partial|tmp|next_block|return [12]|__main__" scripts/evm scripts/solana`；点名 producer=`scripts/evm/fetch_pool_swaps.py`；既有同语义实现=`scripts/evm/fetch_gmgn.sh`、`scripts/solana/window_fetch.py`。
3. 三件套测试：a. success→missing cursor；b. network/invalid JSON/missing cursor/stalled cursor/非法区间；c. stale 隔离或临时文件处理失败必须非零且旧 canonical 不得继续 current。
4. 新建代码自审：旧件只从磁盘实态判断，不信调用方声明；stale 隔离失败必须在 transport 前 fail-closed。
5. 归因预判：老问题修复不全；`six-F-06/six-F-07` 同入口的退出与旧件不变量仍可复现。

### R9-04：Solana supply producer 失败返回与 marker

1. 不变量：snapshot、receipt/commit marker 必须分阶段生成且合法 marker 最后发布；任一参数、网络、解析、slot 或事务失败都必须进程非零，旧 canonical data/marker 不得代表本轮成功。
2. 同族清单：`rg -n "return [12]|sys.exit|publish_txn|--receipt|__main__" scripts/solana/scan_token_accounts.py scripts/report/reconciliation_report.py scripts/report/shared_release_receipt.py`；四个显式 return 分支为路径冲突、supply slot、GPA slot、事务发布失败。
3. 三件套测试：a. 四个 return 分支均走真实 subprocess；b. network/invalid JSON/会计不闭合；c. 预置旧 snapshot+PASS marker 后注入失败，二者必须退出 current 位置。
4. 新建代码自审：marker 只能来自最终发布事务，输入 slot 与会计字段来自 RPC 持久响应；旧件隔离/事务撤回失败均 fail-closed。
5. 归因预判：老问题修复不全；这是 `R7-05/R8-01` 正式 producer 执行真实性同族的浅修残留。

### R9-05 批一部分：SolanaAttestedSession 公共原语

1. 不变量：每个正式 JSON-RPC endpoint 首次业务请求前必须验证 genesis，错 genesis 时业务调用次数为 0，failover 后新 endpoint 必须重新验证。
2. 同族清单：`rg -n "getGenesisHash|jsonrpc|rpc_call|curl_json|requests.post" scripts/solana scripts/lib`；本批只建 `scripts/lib/` 公共原语及独立测试，正式 callsite 接入留批二/三。
3. 三件套测试：a. 正确 genesis 后业务请求；b. 错 genesis→业务调用 0、failover 重验；c. genesis 网络/解析失败与所有 endpoint 耗尽均 fail-closed。
4. 新建代码自审：observed genesis 必须来自 endpoint 响应，不接受调用者自报；身份失败、切换失败、业务失败均保留明确错误且不越过身份门。
5. 归因预判：修复中新引入；本轮 capability 晋升使原本不存在的能力声明进入 formal-ready 发布面。

## B1-G1｜纯反例测试组

- 目标 finding：`R9-02`、`R9-03`、`R9-04`。
- 改动文件：
  - `scripts/tests/test_r9_batch1_boundaries.py`（新增；真实 subprocess，只有 transport 被替换）；
  - `scripts/tests/run_all.py`（挂载新测试）；
  - `maintenance/repair-20260806/b1_progress.md`（本组即时施工记录）。
- 新增测试：
  - `B1-R9-02-PRODUCER-CONSUMER`：真实 `anchor_plan.py` 产物交给 `time_spotcheck.py`；
  - `B1-R9-03-PROCESS/STALE`：pool 参数、网络、解析、缺 cursor、停滞 cursor、success→failure；
  - `B1-R9-04-PROCESS/MARKER`：路径冲突、supply slot、GPA slot、事务发布、network、解析、会计失败、旧件在场。
- 红色命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch1_boundaries.py`
- 红色结果：`exit=1`，`3/3` 目标族失败且原因准确命中：
  - R9-02：新契约参数 `--final-block 300` 被 producer 拒；为复现报告原断裂，测试以旧 CLI 真实生成 plan 成功，再交 consumer，consumer `rc=2`，stderr=`[fatal] anchor_plan final_block 必须与 CLI --final-block 精确一致`；
  - R9-03：fake backend 缺 `next_block`，脚本打印 fatal，但真实 subprocess `rc=0`；
  - R9-04：`--out/--receipt` 路径冲突，脚本打印 fatal，但真实 subprocess `rc=0`。
- 绿色证据：待后续实现组分别转绿；B1-G1 按纪律不改生产实现。

## B1-G2｜CLI 进程契约与 pool stale 语义

- 目标 finding：`R9-03`；同族任务：T2 裁定的 6 个正式 producer/gate 入口。
- 改动文件：
  - `scripts/evm/fetch_pool_swaps.py`；
  - `scripts/solana/scan_token_accounts.py`；
  - `scripts/evm/accounting_gate.py`；
  - `scripts/report/entity_identity_gate.py`；
  - `scripts/evm/cadence_fingerprint.py`；
  - `scripts/bench/golden_baseline.py`；
  - `maintenance/repair-20260806/b1_progress.md`。
- 实现：6 个入口统一为 `raise SystemExit(main())`；pool 使用词法绝对路径，transport 前把旧 canonical 原子移至唯一 `.stale.<time_ns>.<pid>`，隔离失败直接非零；本轮仍只写临时 CSV，完整成功后 `os.replace` 发布新 canonical。
- 新增测试：复用 B1-G1 的 `B1-R9-03-PROCESS/STALE`，覆盖参数、网络、解析、缺 cursor、停滞 cursor、success→failure。
- 红色证据：见 B1-G1，缺 `next_block` 时 fatal 但 subprocess `rc=0`，旧 canonical 保持 current。
- 绿色命令与结果：
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch1_boundaries.py --only pool` → `PASS ... 1/1`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_fetch_failclosed.py` → `PASS: HyperSync 采集器失败与游标异常均 fail-closed`；
  - `rg -n -U 'if __name__ == ...:\n +main\(\)' <6 个裁定文件>` → 0 命中。
- 六视角①②自审：stale 资格取自启动时磁盘实态，不由调用者自报；stale 隔离、网络耗尽、JSON 解析、cursor 缺失/停滞均在进程层非零，临时文件删除，不产生本轮 PASS receipt（该 producer 无 receipt 输出口）。

## B1-G3｜Solana supply producer 分阶段 marker

- 目标 finding：`R9-04`。
- 改动文件：
  - `scripts/solana/scan_token_accounts.py`；
  - `maintenance/repair-20260806/b1_progress.md`。
- 实现：参数和路径冲突检查后、任何业务 RPC 前生成唯一 run id；按“receipt/commit marker 先、snapshot data 后”将旧 canonical 移至 `.stale.<time_ns>.<pid>`；隔离失败非零退出。新 snapshot/receipt 仍由 `publish_txn` 分别 staging，先 data、最后 receipt marker 发布；发布失败不能恢复已隔离的旧 marker 到 current。
- 新增测试：复用 B1-G1 的 `B1-R9-04-PROCESS/MARKER`；四个点名 return 分支（路径冲突、supply slot、GPA slot、事务发布）及 network/invalid JSON/会计不闭合；预置旧 snapshot+PASS marker 后失败。
- 红色证据：B1-G1 路径冲突 subprocess `rc=0`；入口转为 `SystemExit` 后再跑，本组剩余红点为 `failed scan left prior canonical data/marker current`，证明测试独立抓住旧件语义。
- 绿色命令与结果：
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch1_boundaries.py --only scan` → `PASS ... 1/1`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch3_solana_producers.py` → `PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards`。
- 六视角①②自审：supply/GPA slot 均取持久 RPC 响应，不取本地推测；任何旧 marker 先退出 current 名称，四个 return、网络、解析、对账与事务失败均由真实进程码非零表达，合法 marker 只在 data 发布后出现。

## B1-G4｜EVM anchor v2 producer/receipt/consumer

- 目标 finding：`R9-02`。
- 改动文件：
  - `scripts/lib/anchor_plan.py`；
  - `scripts/lib/time_spotcheck.py`；
  - `scripts/tests/test_r9_batch1_boundaries.py`；
  - `scripts/tests/test_time_spotcheck.py`；
  - `scripts/tests/test_batch3_evm_vertical_slice.py`；
  - `maintenance/repair-20260806/b1_progress.md`。
- 实现：
  - producer 强制 `--token`、`--final-block>=0`，先验拒绝所有 `day_end_block/block` 非整数、负数或高于 final block；
  - 输出 `anchor-plan/v2`，同时保留兼容 chain/token/final_block，并新增 canonical target、输入文件/目录哈希身份、producer 路径+代码哈希、生成时间和探测点；
  - 生成 `anchor-plan-input/v1` 清单，以既有 `build_envelope/finalize_envelope/publish_txn` 联合发布 plan 与 `anchor-plan-receipt/v2`，receipt 绑定 input manifest、target、producer、plan 路径/大小/哈希；
  - consumer 默认读取同目录 `anchor_plan.receipt.json`，先用独立 `receipt_validate` 校验，再交叉核对 schema/target/兼容字段/producer/input manifest/output hash/generated_at/probe_count，之后才允许分型或 RPC；
  - EVM 纵切片现场写真实 transfer CSV 并运行 `anchor_plan.py`，不再手写正例 plan；loopback transport 补真实 tx receipt 响应。
- 既有测试适配补记：`test_r7_findings.py` 的 R7-13 正例及 `test_batch1_rpc_attestation.py` 的 time 错链用例也改为现场运行 producer；否则缺 receipt 会在错链 RPC 前提前失败，构成假绿。
- 新增/更新测试：`B1-R9-02-PRODUCER-CONSUMER`；producer 探测块越界无正式产物；真实 plan 两型正例；0 点/格式漂移/final mismatch/越界/缺 RPC/plan 篡改；三链真实 producer 纵切片。
- 红色证据：见 B1-G1，旧 producer 成功但 plan 无 final block，真实 consumer `rc=2`。
- 绿色命令与结果：
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch1_boundaries.py --only anchor` → `PASS ... 1/1`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_time_spotcheck.py` → `time_spotcheck 契约测试全部通过（8 项）`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch1_boundaries.py` → anchor/pool/scan `3/3 PASS`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch3_evm_vertical_slice.py`：沙箱内首次仅因 `bind(127.0.0.1)` 权限失败；获批在沙箱外运行同一命令 → `PASS B3-EVM-E2E: eth/bsc/base real slices; wrong chain has zero business RPC`。
- 六视角①②自审：final block/探测点/输入/producer 均来自 producer 计算并双文件绑定；输入、DuckDB、边界校验、receipt 构造、MD 发布或 plan+receipt 联合发布失败均非零，consumer 对缺失/篡改 receipt 在任何业务 RPC 前拒绝。

## B1-G5｜SolanaAttestedSession 公共原语

- 目标 finding：`R9-05` 的批一部分；本组不宣告 finding 销账，正式 callsite/矩阵/纵切片接入按计划留批二/三。
- 改动文件：
  - `scripts/lib/solana_attested_session.py`（新增）；
  - `scripts/tests/test_r9_solana_attested_session.py`（新增）；
  - `scripts/tests/run_all.py`（挂载）；
  - `maintenance/repair-20260806/b1_progress.md`。
- 实现：固定可信 mainnet genesis `5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d`；每个 active endpoint 首次业务 RPC 前内部调用 `getGenesisHash`；错误/缺失/错 genesis 均拒绝该 endpoint；业务失败切换 endpoint 时清空 attestation 状态，新 endpoint 必须重新验证。唯一测试注入边界为 decoded JSON transport，默认 transport 使用 stdlib HTTPS JSON POST。
- 新增测试：
  - 错 genesis 单 endpoint → 方法序列只有 `getGenesisHash`，业务调用 0；
  - 正 genesis → attestation 严格先于业务；
  - 错 genesis endpoint → failover 正 endpoint 重新 attestation，错 endpoint 业务 0；
  - 已验证 endpoint 业务失败 → 新 endpoint 重新 attestation 后才执行业务；
  - genesis 网络失败/响应缺 result → 全部 fail-closed，业务 0。
- 绿色命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_solana_attested_session.py`。
- 绿色结果：`PASS R9 SolanaAttestedSession: 5/5`。
- 六视角①②自审：observed genesis 只来自当前 endpoint 的 RPC 响应；调用者不能通过业务 API 自报/直接调用 `getGenesisHash`；transport、JSON shape、RPC error、错 genesis、业务 failure 和 endpoint 耗尽均抛明确异常，不会绕过身份门。

## B1-G6｜49 项主账、归因规则与 diff owner

- 目标 finding/配套任务：`T1`；登记 `R9-01`～`R9-05`，不把批一未完成的 R9-01/R9-05 callsite 闭合写成已修。
- 改动文件：
  - `maintenance/repair-20260806/ledger.md`；
  - `maintenance/repair-20260806/invariant-merge.md`；
  - `maintenance/repair-20260806/diff-finding-map.md`；
  - `references/maintenance-review-repair.md`；
  - `maintenance/repair-20260806/b1_progress.md`。
- 主分类与覆盖：`R9-01→INV-08/②`；`R9-02→INV-10/②`；`R9-03→INV-03/①`；`R9-04→INV-03/①`；`R9-05→INV-11/②`。每项唯一 primary、唯一主覆盖类别；secondary 不计分母。
- 规则：把“老问题修复不全/修复中新引入/历史漏检”的严格定义、最强替代解释和从严优先级写回维护方法论唯一事实源；不能排除旧 invariant 同族残留时归修复不全，旧绕过已关但 repair diff 造新断契约时归新引入，只有同时排除两者才可归历史漏检。
- diff owner：R9 批一新表逐 hunk 覆盖 G1～G6；同文件多 owner（`test_r9_batch1_boundaries.py`、`run_all.py`、`scan_token_accounts.py`）显式分物理/语义 hunk，没有“顺手整理”。
- 验证命令与结果：
  - ledger Python 对表 → `rows 49 unique 49`，R9 五 ID 各出现 1 次；
  - invariant primary 数求和 → `[3,3,5,3,2,3,3,4,2,3,3,1,2,2,4,1,1,3,1,0] 49`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py --all` → `PASS: 58 个文档`；
  - `git diff --check` → 通过。

## B1-G7｜既有 invariant census 同步

- 目标 finding/配套任务：`T2/T5/T6` 的现役静态登记；secondary `R9-02`～`R9-05`。不新增批四 AST 守卫，不抢跑批四。
- 改动文件：
  - `scripts/tests/invariant_manifest.json`；
  - `maintenance/repair-20260806/diff-finding-map.md`；
  - `maintenance/repair-20260806/b1_progress.md`。
- 红色命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py`。
- 红色结果：5 discrepancy，精确点名 `anchor_plan.py` producer、`time_spotcheck.py` consumer、`solana_attested_session.py:urllib`、pool/scan 两个 `quarantine_current` atomic locator。
- 实现：机械追加上述实际 code point；minimum counts 从 `46/51/57/37/58` 同步为 `49/53/58/39/58`（producer/consumer/transport/atomic/formal entrypoint）。
- 绿色命令与结果：
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py` → `PASS invariant manifest: receipt_producers=49, receipt_consumers=53, transport_calls=58, atomic_writes=39, formal_entrypoints=58, exceptions=0`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py --self-test` → delete/add 两类破坏注入均 `RED (rc=1)`，self-test exit 0。

## 批一自检汇总

### 红→绿闭环

- `R9-02`：红色基线为真实旧 producer 成功生成无 final-block 的 plan，真实 consumer `rc=2`；绿色为真实 `anchor_plan.py` v2 plan+receipt 经 `time_spotcheck.py` 消费，契约测试 `8/8 PASS`、三条正式 EVM 纵切片通过。producer 探测块高于 `--final-block` 时非零且不发布 plan/receipt。
- `R9-03`：红色基线为缺 `next_block` 已打印 fatal 但 subprocess `rc=0`，旧 canonical 仍 current；绿色为参数/网络/解析/缺 cursor/停滞 cursor/success→failure 全部分支进程码非零，旧件启动即隔离，`test_fetch_failclosed.py` 通过。
- `R9-04`：红色基线为路径冲突 fatal 但 subprocess `rc=0`；入口修正后测试继续抓到旧 data/marker 未失效，最终绿色覆盖路径冲突、supply slot、GPA slot、事务发布、网络、解析、会计失败及旧件在场，合法 marker 最后发布。
- `R9-05`：批一只完成公共 `SolanaAttestedSession` 原语与 `5/5` 反例；错 genesis 时业务调用严格为 0，故障切换重新验证。正式 callsite、能力矩阵和纵切片仍按计划留批二/三，本批不宣告该 finding 销账。
- `R9-01`：本批只进入 49 项主账和不变量归并；其实现属于批三，未抢跑、未宣告修复。

### 受影响测试与全量门禁

- 受影响集合全部通过：R9 边界 `3/3`、Solana session `5/5`、time contract `8/8`、R7 `15/15`，以及 fetch failclosed、Solana producer、EVM vertical slice、RPC attestation、receipt kernel、batch4 invariant guards、docs lint。
- 全量命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py`。
- 全量结果：`82/82 PASS`，末行 `全部通过`。其中既有 loopback 纵切片因沙箱禁止 `bind(127.0.0.1)`，获批后在沙箱外运行同一命令；只使用本机回环 fake，不访问外网。
- invariant census：`receipt_producers=49, receipt_consumers=53, transport_calls=58, atomic_writes=39, formal_entrypoints=58, exceptions=0`；破坏注入 delete/add 均稳定红。

### 台账、边界与 diff owner 自查

- ledger：`49` 行、`49` 个唯一 finding；`R9-01`～`R9-05` 各 1 行；primary INV 计数求和 `49`。
- diff→finding：当前 22 个改动/新增文件全部映射到 `R9-B1-G1`～`R9-B1-G7` 或配套任务 `T1`～`T6`，未映射 hunk=`0`；`test_r9_batch1_boundaries.py`、`run_all.py`、`scan_token_accounts.py` 的多 owner hunk 已显式拆分。
- 范围：未改 `VERSION`，仍为 `6.36.0`；未改 `scripts/lib/chain_registry.py`、`scripts/solana/accounting_gate_sol.py`，`getGenesisHash` 只存在于新公共原语及其测试，未接正式 callsite。
- CLI 同族：裁定的 6 个文件均为 `raise SystemExit(main())`，裸 `main()` 入口扫描 0 命中。
- 仓库纪律：施工期间未执行 `git add/commit/push/branch` 等 git 写操作；`git diff --check` 通过；`git status --short` 未列出 `.pyc`/`__pycache__` 施工变更。工作树内存在被 git 忽略的既有 cache 目录，本批未擅自删除。

## B1F-G1｜消化 B1R-01：consumer 绑定真实 producer 身份

- 修改文件：`scripts/tests/test_time_spotcheck.py`、`scripts/lib/time_spotcheck.py`、本进度文件。通用 `receipt_validate.py` 未改，anchor 特例只绑在 consumer 侧。
- 红测场景：先用真实 `anchor_plan.py` 生成 plan+receipt，再把两份 `producer` 同步伪造为仓库内 `references/maintenance-review-repair.md`，填入其真实 SHA256 并重签 plan output size/hash。
- 红色命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_time_spotcheck.py`。
- 红色结果：`exit=1`，新增两条均红：`FAIL  伪造 Markdown producer 的 dry-run 在业务前拒绝`、`FAIL  伪造 Markdown producer 的正式路径在 RPC 前拒绝`。
- 实现：`load_validated_plan` 在通用 receipt 验证后将 `receipt.producer.path` 词法归一化，必须精确等于仓库根相对固定值 `scripts/lib/anchor_plan.py`；既有 `plan.producer == receipt.producer` 交叉绑定保留。
- 绿色命令与结果：
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_time_spotcheck.py` → `time_spotcheck 契约测试全部通过（10 项）`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch3_evm_vertical_slice.py` → 沙箱内仅因 `bind(127.0.0.1)` 权限失败；获批在沙箱外运行同一命令后 `PASS B3-EVM-E2E: eth/bsc/base real slices; wrong chain has zero business RPC`。

## B1F-G2｜消化 B1R-02：anchor 启动隔离与公共原语

- 修改文件：新增 `scripts/lib/artifact_quarantine.py`；修改 `scripts/lib/anchor_plan.py`、`scripts/evm/fetch_pool_swaps.py`、`scripts/solana/scan_token_accounts.py`、`scripts/tests/test_r9_batch1_boundaries.py`、`scripts/tests/invariant_manifest.json`、本进度文件。
- 红测场景：同一 `--out-dir` 先用合法 CSV 成功产出 plan+receipt，再用含 `block=301 > final_block=300` 的 CSV 注入生产失败；断言旧 plan/receipt 已离开正式位置、两份 stale 存在、consumer 非零。
- 红色命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch1_boundaries.py --only anchor`。
- 红色结果：`exit=1`，`FAIL R9 batch1 anchor: failed anchor rerun left prior plan/receipt current`。
- 实现：把原 pool/scan 两份 `quarantine_current` 合并为唯一公共原语，共享 `quarantine_run_id=<time_ns>.<pid>`；pool/scan/anchor 三处共用。anchor 在读取/解析输入之前先隔离 receipt（commit marker）、再隔离 plan；任一隔离失败返回非零，部分隔离也不会留下可消费的 plan+receipt 对。
- invariant 同步：首跑 `invariant_scan.py` 稳定红 3 discrepancy（新公共 locator 未登记，pool/scan 旧 locator 已消失）；manifest 改登记 `scripts/lib/artifact_quarantine.py:quarantine_current`，`atomic_writes` 由 39 按实际唯一实现更新为 38。
- 绿色命令与结果：
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch1_boundaries.py --only anchor` → `PASS ... 1/1`；
  - 同一测试的 `--only pool`、`--only scan` 均 `PASS ... 1/1`，整组→ `PASS ... 3/3`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_fetch_failclosed.py` → `PASS: HyperSync 采集器失败与游标异常均 fail-closed`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch3_solana_producers.py` → `PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py` → `PASS ... atomic_writes=38 ... exceptions=0`；`--self-test` 的 delete/add 破坏注入均 `RED (rc=1)`。
- 同族深度检查：`rg -n '^def quarantine_current' scripts/lib scripts/evm scripts/solana` 仅命中 `scripts/lib/artifact_quarantine.py`，无三重复制。

## B1F-G3｜消化 B1R-03：收紧 SolanaAttestedSession 信任根

- 修改文件：`scripts/tests/test_r9_solana_attested_session.py`、`scripts/lib/solana_attested_session.py`、本进度文件。
- 红测场景：构造 `SolanaAttestedSession(..., expected_genesis="caller-controlled-genesis", request_json=<transport>)`，要求构造器没有该信任根注入口并抛 `TypeError`。
- 红色命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_solana_attested_session.py`。
- 红色结果：`exit=1`，精确失败为 `AssertionError: caller can override the Solana genesis trust root`，证明旧构造器接受该覆盖。
- 实现：删除 `expected_genesis` 构造参数和 `_expected_genesis` 实例状态；`_attest` 只与库常量 `SOLANA_MAINNET_GENESIS_HASH` 比较。docstring 明确为 Solana mainnet attestation，`request_json` 现为唯一测试注入边界。
- 绿色命令与结果：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_solana_attested_session.py` → `PASS R9 SolanaAttestedSession: 6/6`；原 5 条 transport 注入反例全保留，新增第 6 条构造口不存在反例。
- 静态核对：`rg -n "expected_genesis|_expected_genesis" scripts/lib scripts/tests` 只剩正式测试中的攻击调用，生产实现零命中。

## B1F-G4｜消化 B1R-04：恢复治理条文并补 owner/区间

- 修改文件：`maintenance/repair-20260806/invariant-merge.md`、`maintenance/repair-20260806/diff-finding-map.md`、本进度文件。
- 红色命令：`PYTHONDONTWRITEBYTECODE=1 python3 -c '<精确 needle 断言>'`，needle 为「此后拆分/合并不变量必须经 Fable 批准并同步 ledger 双台账，不得在验收阶段为销账临时改组。」
- 红色结果：`exit=1`，`AssertionError: governance clause missing`。
- 实现：在 `invariant-merge.md` 页首状态/计数口径之间恢复完整治理纪律；`diff-finding-map.md` 的 R9 批一节补 `B1F-G1`～`B1F-G4` 四条 hunk owner，SHA 对照表补四行空值待裁判回填，未映射 hunk 节补 `144c652..candidate tip` 批一消化区间行，当前计数 `0`。
- 绿色命令与结果：
  - 同一精确 needle 断言 → `PASS governance clause restored`；
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py --all` → `PASS: 58 个文档，引用无断链、粗体配对完整`；
  - `rg` 核对→ `B1F-G1`～`B1F-G4` 四行 SHA 为空，且批一消化 `144c652..` 区间行存在。

## B1F 批一消化汇总

### 四项红→绿

- `B1R-01`：伪造 Markdown producer 的 dry-run/正式路径两条在旧实现均未命中「registered anchor producer」前置拒绝而红；consumer 固定绑定后转绿，`time_spotcheck` `10/10`，eth/bsc/base 纵切片通过。
- `B1R-02`：同 out-dir 成功→失败后旧 plan/receipt 仍 current 的反例红；公共 quarantine 原语和 anchor 启动隔离后转绿，pool/scan/anchor 边界 `3/3`，atomic 登记对表通过。
- `B1R-03`：调用方可传 `expected_genesis` 的构造反例红；删除入口后 TypeError 反例与原 5 条 transport 反例共 `6/6` 绿。
- `B1R-04`：治理条文精确 needle 缺失红；恢复条文、四组 owner、空 SHA 和 `144c652..candidate tip` 消化区间后转绿，未映射 hunk=`0`。

### 受影响集合与全量门禁

- 受影响命令全部通过：`test_time_spotcheck.py` `10/10`；`test_r9_batch1_boundaries.py` `3/3`；`test_r9_solana_attested_session.py` `6/6`；`test_fetch_failclosed.py`；`test_batch3_solana_producers.py`；`invariant_scan.py` 及 `--self-test`；`docs_lint.py --all`；`test_batch3_evm_vertical_slice.py` eth/bsc/base。
- EVM 纵切片因沙箱禁止 `bind(127.0.0.1)` 在沙箱外运行同一命令，仅使用本机回环 fake，不访问外网；结果 `PASS B3-EVM-E2E: eth/bsc/base real slices; wrong chain has zero business RPC`。
- 全量命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py`。
- 全量结果：`82/82 PASS`，`exit=0`，末行 `全部通过`。
- invariant census：`receipt_producers=49, receipt_consumers=53, transport_calls=58, atomic_writes=38, formal_entrypoints=58, exceptions=0`；delete/add 两类自测破坏注入均稳定红。
- 边界核对：`git diff --check` 通过；`VERSION` 零 diff，仍为 `6.36.0`；未执行任何 git 写操作。
