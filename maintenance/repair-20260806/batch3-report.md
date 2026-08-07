# R8 修复闭环：批三正式链纵切片施工报告

## 1. 范围与门禁

- 开工 HEAD：`62efbf91dbde896d265eb8f12bb41891649da77f`，符合工单 `62efbf9` 门禁。
- 正例链：`eth` / `bsc` / `base` / `sol`（CLI 公开别名 `solana`）。
- 真实执行：accounting producer、四项 reconciliation producer、controlled runner、semantic aggregator、READY handoff 与 audit release gate 全部跑生产入口。
- 唯一 fake 边界：本地 `127.0.0.1:0` HTTP server，仅替换 EVM JSON-RPC / HyperSync / Sourcify 与 Solana JSON-RPC / SQD transport；未 mock producer main、业务函数、receipt builder、runner、aggregator 或 validator。
- 未调用真实 RPC/API；未执行任何 git 写操作；`CHANGELOG.md` 与历史文档零改动。

## 2. 先红后绿

### 2.1 EVM time plan / cutoff（INV-06 / INV-08）

红：在 `test_time_spotcheck.py` 加入 plan `final_block` 与 CLI 不同、查询块越过冻结点两反例，冻结实现首跑：

```text
FAIL plan final_block 与 CLI 不精确一致拒绝
FAIL 查询块越过 final_block 在 RPC 前拒绝
```

绿：`time_spotcheck.py` 在建立 RpcPool 前完成 plan↔CLI `final_block` 精确绑定，且拒绝所有负数、非整数、bool 或 `> final_block` 的 balance/tx 查询块。

```text
ok    plan final_block 与 CLI 不精确一致拒绝
ok    查询块越过 final_block 在 RPC 前拒绝
time_spotcheck 契约测试全部通过（7 项）
```

| 测试 ID | 证明 |
|---|---|
| `B3-TIME-01` | plan `final_block` 必须与 CLI 冻结块精确相等 |
| `B3-TIME-02` | 执行块越过冻结点时在 transport 之前 fail-closed |

### 2.2 Solana producer（INV-05 / INV-08 / INV-09 / INV-10）

红：冻结实现对新反例的实际输出：

```text
accounting_gate_sol.py: error: unrecognized arguments: --as-of-slot 77
FAIL window missing timestamp produced PASS
scan_token_accounts.py: error: unrecognized arguments: --as-of-slot 77 --out ... --receipt ...
runner accepted target.as_of_block=None and entered subprocess.run
```

绿：

```text
PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards
PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release
```

| 测试 ID | 证明 |
|---|---|
| `B3-SOL-PROD-01` | accounting 必填冻结 slot，result 同时绑定 `as_of_slot/as_of_block` |
| `B3-SOL-PROD-02` | window 缺失/非法 timestamp 不发 PASS；回执绑定每 segment timestamp min/max |
| `B3-SOL-PROD-03` | anchor/window 同路径与中间目录 symlink alias 在 transport 前拒绝 |
| `B3-SOL-PROD-04` | supply CLI 生成 `solana-holder-snapshot-receipt/v3` 当前 envelope，data+receipt 联合发布 |
| `B3-SOL-PROD-05` | formal supply truth 的 observed context slot 必须精确等于冻结 slot |
| `B3-SOL-PROD-06` | controlled runner 在 producer 前拒绝 `as_of_block=None` |

### 2.3 四链纵切片与错链

EVM 绿：

```text
PASS B3-EVM-E2E: eth/bsc/base real slices; wrong chain has zero business RPC
```

Solana 绿：

```text
PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release
```

| 测试 ID | 执行链 |
|---|---|
| `B3-EVM-E2E-ETH` | eth chainId=1；real accounting→runner(verify/supply-truth/time)→semantic aggregator→READY→release |
| `B3-EVM-E2E-BSC` | bsc chainId=56；同上 |
| `B3-EVM-E2E-BASE` | base chainId=8453；同上 |
| `B3-EVM-WRONG-ETH/BSC/BASE` | fake 返回 chainId=999，记录的 RPC method 集合仅 `{eth_chainId}` |
| `B3-SOL-E2E` | accounting + supply + supply-truth + anchor(balance/time) + window 真实 CLI，同 target `solana/mint/77` 进 runner/READY/release |

`test_reconciliation_runner.py::test_01_preexisting_receipt_rejected` 作为 `B3-RUNNER-FRESH-01` 复验：预置 receipt 在任一 producer 启动前被拒，因此准备阶段 `CMD-FORGE` 的手写四回执不能通过真实 controlled runner。

## 3. 生产契约收口

1. EVM accounting 回执现在以经 chain-attested 的 `eth_blockNumber` 写入 `as_of_block`；Sourcify endpoint 可仅在 transport 层注入。
2. `time_spotcheck` 先验 plan target/final block/cutoff，再创建 attested session。
3. Solana accounting/supply/supply-truth/anchor/window 统一非空冻结 slot；`sol`/`solana` 在 consumer 比较时 canonicalize，token 小写，slot 必须精确相等。
4. `receipt_kernel.RawBytes` 让同一 `publish_txn` 同时原子发布 JSONL data 和 JSON receipt；producer 在 transport 前使用 `assert_distinct_paths`。
5. `scan_token_accounts.py` 的 formal output/receipt 使用 current envelope；raw GPA cache 与存量 identity 兼容产物限制在可配 `--work-dir`，不与 runner 正式输出混用。
6. `holder_distribution_scan.py` 读取 canonical supply-truth 的 `onchain_total_supply/replay_net`，同时保留旧字段兼容。

## 4. 同族 `rg` 清单与处置

- EVM `eth_*` 字面全库共 47 处；本批纵切片的 accounting / verify_recon / supply_truth / time 全部经批一 attested `RpcPool`，错链时业务调用数为 0。批一已迁的其余正式 callsite 由 `test_batch1_rpc_attestation.py` 继续守卫。
- Solana 直写清单中，`anchor_sampler.py` / `window_fetch.py` 的 PASS data+receipt 已迁 `publish_txn`；`scan_token_accounts.py` formal data+receipt 亦使用同一 primitive。其 GPA cache/存量 identity 兼容文件是不进 shared-release map 的 runner 工作件。
- `accounting_gate_sol.py` 是单 receipt primitive，不存在 data/receipt 多路径原子性。
- `trace_wallet.py`、`stake_decode.py`、`gas_origin.py`、`probe_escrows.py`、`whale_deep.py`、`scan_sharded.py` 等未登记为本批 reconciliation runner 的 formal producer，本批不迁；由批四 scanner/发布路径双向守卫继续判定。
- schema 调用图已将 `scan_token_accounts.py` 新 producer schema 与 `shared_release_receipt.py` consumer schema 同步进 `invariant_manifest.json`；旧 `solana-holder-snapshot-v2` 仅留作 identity 兼容产物。

## 5. 新建代码六视角自审（本工单要求的 ①/②）

### ① 字段来源 / 绑定

- EVM `as_of_block` 来自 attested RPC 的 `eth_blockNumber`；reconciliation target 由 runner spec 单源绑定，四 receipt 必须精确一致。
- time plan 的 chain/token/final-block 同时与 CLI/receipt target 对表，不采信 wrapper 自报。
- Solana slot 来自必填 CLI 冻结值，RPC context slot 必须精确同值；不以“当前 slot”冒充冻结时点。
- supply output hash 按 kernel 实际序列化字节计算，shared consumer 从磁盘独立重算。anchor/window 联合发布后亦由独立 reader 重算。

### ② 失败分支 / fail-closed

- EVM 错链、chainId 无法解析、plan target 不同、查询块越 cutoff 都不会进入业务 RPC。
- runner 拒绝空/None/布尔/负数 target，拒绝预置 receipt，producer 失败则 wrapper=FAIL/2。
- Solana timestamp 缺失/非 int/超范围、空且无法证明覆盖的窗口、gap、旧 resume 身份不一致、超 cutoff、同路径/symlink alias 均不产生 canonical PASS。
- `publish_txn` 任一阶段失败回滚 data/receipt；回滚二次失败继续由批一 fault-on-fault 回归保护备份。
- READY 必须有 runner 产生的 reconciliation wrapper 与四份在场 receipt；shared target、handoff target 与 receipt target 不同即拒。

## 6. 归因预判

- `R8-01/R8-03/R8-11/R8-12`：报告指向的 Solana producer schema/slot/timestamp/transaction 缺口，本批直接修复并以 `B3-SOL-*` 复现和纵切片闭合。
- `R7-03/R7-06/R7-05/R7-13`：跨轮同族残留，分别由 producer alias 反例、runner 可执行 envelope 和 time final-block 精确绑定收口。
- `R8-06/R7-08`：批二已建强制 reconciliation 契约，本批用四链真实 READY 路径证明其必经性。
- `full-F-01/six-F-03/R7-01`：本批不改变“validator 单独不是执行证明”的定性；修复依据是 controlled runner 拒绝预置 receipt 且四链正例确实启动了白名单 producer。
- 施工中暴露的 `holder_distribution_scan.py` 仅读旧 supply 字段是同一纵切片上的 consumer 契约漂移；本批以兼容方式收口，记入 `B3-G1` secondary，不新增 finding 分母。

## 7. 逻辑分组（Fable 代 commit）

| 分组 | 文件 / 目的 |
|---|---|
| `B3-G1` | EVM accounting/time/readiness/distribution consumer + EVM 纵切片；闭合 eth/bsc/base。 |
| `B3-G2` | receipt kernel RawBytes/distinct helper；Solana accounting/supply/anchor/window/supply-truth/shared consumer/runner；闭合 Solana。 |
| `B3-G3` | 新测试、历史 fixture 兼容、run_all 挂载与 invariant manifest。 |
| `B3-G4` | ledger、diff map、transport injections、本报告。 |

## 8. 全量门禁

首次全量回归捕获三个兼容红点：静态 schema manifest 未同步、批一 wrong-chain plan fixture 缺 `final_block`、six-lens anchor fixture 仍假设失败后留 data 且仍 patch 旧单文件 primitive。三项均只更新契约 fixture，复跑点名测试全绿。

最终命令：

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
PASS invariant manifest: receipt_producers=46, receipt_consumers=51, ...
PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release
PASS B3-EVM-E2E: eth/bsc/base real slices; wrong chain has zero business RPC
========================================================
全部通过
EXIT=0（79/79）
```

## 9. 改动文件

### 生产代码

- `scripts/evm/accounting_gate.py`
- `scripts/lib/chain_registry.py`
- `scripts/lib/receipt_kernel.py`
- `scripts/lib/supply_truth_gate.py`
- `scripts/lib/time_spotcheck.py`
- `scripts/report/holder_distribution_scan.py`
- `scripts/report/reconciliation_report.py`
- `scripts/report/shared_release_receipt.py`
- `scripts/solana/accounting_gate_sol.py`
- `scripts/solana/anchor_sampler.py`
- `scripts/solana/scan_token_accounts.py`
- `scripts/solana/window_fetch.py`

### 测试 / 静态契约

- `scripts/tests/test_batch3_evm_vertical_slice.py`
- `scripts/tests/test_batch3_solana_producers.py`
- `scripts/tests/test_batch3_solana_vertical_slice.py`
- `scripts/tests/test_time_spotcheck.py`
- `scripts/tests/test_batch1_rpc_attestation.py`
- `scripts/tests/test_batch2_capability_matrix.py`
- `scripts/tests/test_batch2_registry_harness_hardening.py`
- `scripts/tests/test_chain_registry.py`
- `scripts/tests/test_chain_support_matrix.py`
- `scripts/tests/formal_ready_test_harness.py`
- `scripts/tests/test_handoff_manifest.py`
- `scripts/tests/test_r7_findings.py`
- `scripts/tests/test_round4_identity_emitter.py`
- `scripts/tests/test_sixlens_receipts.py`
- `scripts/tests/invariant_manifest.json`
- `scripts/tests/run_all.py`

### 台账

- `maintenance/repair-20260806/ledger.md`
- `maintenance/repair-20260806/diff-finding-map.md`
- `maintenance/repair-20260806/transport-injections.json`
- `maintenance/repair-20260806/batch3-report.md`

## 10. 批内消化（B3R-01～03）

### 10.1 B3R-01：提交后自检失败真实撤回

红（冻结实现，`B3F-TXN-01/02`）：测试替换的 `publish_txn` 已把与 `data_bytes` 不同的字节及 PASS receipt 写入正式位，然后触发生产独立读者哈希自检。两个 producer 都返回非零并旁写 ERROR receipt，但断言捕获正式 data 仍在：

```text
[window_fetch] 检测/提交失败（exit 1）: 联合发布后独立读者哈希不一致
[anchor_sampler] receipt 生成失败（exit 1）: 联合发布后独立读者哈希不一致
AssertionError: test_window_post_commit_selfcheck_withdraws_formal_artifacts: self-check failure left data in the formal location
test_anchor_post_commit_selfcheck_withdraws_formal_artifacts: self-check failure left data in the formal location
EXIT=1
```

修复：window/anchor 均在 `publish_txn` 成功返回后设置 `committed=True`。后续自检失败时先删除 canonical receipt；window 用 `os.replace` 把正式 data 移到 `.partial`，anchor 复用既有 kernel `publish_overwrite` 安全发布 `.partial` 后删除正式位；最后保留原有时间戳 ERROR receipt。选择删除而不是覆写 FAIL，是为了让 canonical 第一真相立即失效且不引入第二套失败 receipt；诊断仍由既有 ERROR side receipt 承担。receipt 撤回尝试始终先于 data 撤回；任一撤回异常并入 ERROR 信息并保持非零退出。window 原 `published_current`/`backup` 恒假死分支已删除；`receipt_kernel.py` 零改动。

绿：

```text
[window_fetch] 检测/提交失败（exit 1）: 联合发布后独立读者哈希不一致
[anchor_sampler] receipt 生成失败（exit 1）: 联合发布后独立读者哈希不一致
PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards
EXIT=0
```

既有 `test_sixlens_receipts.py` 的 `publish_txn` 自身抛 `disk full` 分支继续绿；该分支发生在 `committed=True` 之前，不触发事后撤回。

### 10.2 B3R-02：生产 3 元组契约与 timestamps 闭环

红（`B3F-TS-01`）：`scan_seg` 返回 complete 但 timestamps 为空时，冻结实现仍发布 PASS，反例以空断言失败并使聚焦脚本 `EXIT=1`。

修复：删除 `window_fetch.py` 的 2 元组兼容分支；五处历史 mock 全部改为 `(edges, ok, timestamps)`。无 gap 的 PASS 分支在发布前要求 segment 摘要数量与计划一致，且每段 `min/max` 均非空，否则旁写 ERROR receipt、不得发布 canonical PASS。

绿：

```text
[window_fetch] 检测/提交失败（exit 1）: complete segment 缺少 timestamp min/max 证据
PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards
PASS: 六视角批①结构化回执与 fail-closed
PASS R7 regression suite: 15/15 observed green; EXPECTED_RED=0
```

### 10.3 B3R-03 与三项观察

- `B3R-03`：diff map 的 `B3-G3` 删除重复归属的 `test_batch3_evm_vertical_slice.py`；新增 `B3F-G1`～`B3F-G3` 三组 owner。
- `OB-H`：anchor resume 从旧逐天落盘退化为整轮联合提交，是 data+PASS receipt 不可分割的直接代价。完整性优先于断点粒度，但长采集中断后整轮重跑的时间/transport 成本真实存在；本轮不粉饰也不另做分段事务重构，留后续在不破坏联合事务前提下设计可验证 checkpoint。
- `OB-I`：`B3-EVM-WRONG-*` 端到端错链反例实际只执行 `time_spotcheck`；逐调用点错链零业务证明来自批一 `test_each_formal_callsite_wrong_chain_zero_business`。`transport-injections.json` 的 allowed_reason 已按此收窄。
- `OB-J`：当前 loopback `/query` 分支不进入 RPC `methods` 计数。未来把错链端到端反例扩展到 `accounting_gate` 前，必须先为 `/query` 增加独立调用计数，不能拿现有 methods 集合宣称 accounting 业务调用为零。
- 批四守卫 `B3R-Q1` 已登记 ledger：凡 `vertical_slice_verified=True`，对应测试文件必须存在且必须进入 `run_all.SUITE`，缺一即红；与 `B1R-01` 裸池守卫、`OB-B` labels 副本双向守卫并列。

### 10.4 逻辑分组

| 分组 | 文件 / 目的 |
|---|---|
| `B3F-G1` | `window_fetch.py`、`anchor_sampler.py`、`test_batch3_solana_producers.py`：B3R-01 提交后自检失败撤回与 `B3F-TXN-01/02`。 |
| `B3F-G2` | `window_fetch.py`、`test_batch3_solana_producers.py`、`test_sixlens_receipts.py`、`test_r7_findings.py`：B3R-02 生产 3 元组契约及 timestamps min/max 闭环。 |
| `B3F-G3` | 四份 maintenance 台账：B3R-03、OB-H/I/J、批四 `B3R-Q1`。 |

### 10.5 全量门禁与本轮改动文件

沙箱内首次全量运行的代码侧唯一红点是 anchor 新增直接 `os.replace` 触发 invariant manifest 未登记；改为复用已登记 kernel primitive 后，`invariant_scan.py` 单跑恢复 PASS。另两项为沙箱禁止绑定 `127.0.0.1` 导致 EVM/Solana loopback 纵切片 `PermissionError`。在允许本机 loopback 的执行环境用同一命令重跑，最终结果：

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
      PASS  invariant_scan.py        PASS invariant manifest: receipt_producers=46, receipt_consumers=51, ... atomic_writes=37
      PASS  test_batch3_solana_producers.py PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards
      PASS  test_batch3_solana_vertical_slice.py PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release
      PASS  test_batch3_evm_vertical_slice.py PASS B3-EVM-E2E: eth/bsc/base real slices; wrong chain has zero business RPC
========================================================
全部通过
EXIT=0（79/79）
```

收尾检查：`transport-injections.json` 可被 `json.tool` 解析；仓库内 `.pyc` / `__pycache__` 查询结果为空。

生产代码：

- `scripts/solana/window_fetch.py`
- `scripts/solana/anchor_sampler.py`

测试：

- `scripts/tests/test_batch3_solana_producers.py`
- `scripts/tests/test_sixlens_receipts.py`
- `scripts/tests/test_r7_findings.py`

台账：

- `maintenance/repair-20260806/diff-finding-map.md`
- `maintenance/repair-20260806/batch3-report.md`
- `maintenance/repair-20260806/transport-injections.json`
- `maintenance/repair-20260806/ledger.md`

未超出工单预期清单；未修改 `receipt_kernel.py`，未执行 git 操作。
