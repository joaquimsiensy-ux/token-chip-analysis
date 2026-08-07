# 批四施工报告：守卫、fixture 与方法论写回

基线：`f2a6e419c7161f38e21be7e183109453da32a554`。本批只做 scanner/测试、方法论和维护台账；生产业务代码零改动，未执行任何 git 写操作。

## 1. 先红后绿

### 1.1 冻结实现红例

先加入包含四组违规注入的 `test_batch4_invariant_guards.py`，未改 scanner 时实跑：

```text
AttributeError: module 'batch4_invariant_scan' has no attribute 'bare_rpc_pool_errors'
EXIT=1
```

守卫实现后、manifest 尚未登记新增 census 时，scanner 转为 23 项显式红：18 个此前漏检的 urllib/httpx/变量 curl transport、4 个能力/producer registry 正式入口、1 个 minimum-counts 缺口。关键摘录：

```text
FAIL transport_calls: code point missing from manifest: ('scripts/robinhood/pull_transfers.py', 'urllib')
FAIL transport_calls: code point missing from manifest: ('scripts/solana/probe_window_moves.py', 'curl')
FAIL formal_entrypoints: capability/producer registry point missing: scripts/evm/verify_recon.py
FAIL formal_entrypoints: capability/producer registry point missing: scripts/solana/scan_token_accounts.py
FAIL minimum_counts must contain the five scanner denominators
invariant manifest FAIL: 23 discrepancy(s)
EXIT=1
```

### 1.2 违规注入与绿例

| 测试 ID | 临时违规注入 | 守卫结果 |
|---|---|---|
| `B4-RPC-01` | 临时生产文件直接 `RpcPool('http://wrong')` | `bare RpcPool construction`，RED；现状仅 `net.py:attested_rpc_pool` 允许 |
| `B4-LABEL-01` | resolver known 集多 `ghost` | `unregistered chains ['ghost']`，RED |
| `B4-LABEL-02` | build labels 资产面摘 `robinhood` | `missing labels_table chains ['robinhood']`，RED |
| `B4-VS-01` | 临时摘 `run_all.SUITE` 的 EVM 纵切片项 | `not mounted in run_all.SUITE`，RED |
| `B4-VS-02` | `sol` 映射改指不存在测试 | `test file missing`，RED |
| `B4-INV17-01` | urllib backend、变量 `cmd=['curl', ...]` | 两类 transport 均被 AST census 识别 |
| `B4-INV17-02` | manifest 摘一个 formal entrypoint | 分母低于 floor，RED；producer registry 必经项另做 subset 守卫 |
| `B4-RH-COUNT-01` | 文档从磁盘实数 16/15 改成 15/14 | `Robinhood inventory mismatch`，RED |

聚焦绿输出：

```text
INJECT B4-RPC-01 bare RpcPool -> RED
INJECT B4-LABEL-01/02 extra ghost + missing robinhood -> RED
INJECT B4-VS-01/02 missing SUITE + missing file -> RED
INJECT B4-INV17-01/02 urllib + variable curl + denominator shrink -> RED
INJECT B4-RH-COUNT-01 documented 15/14 vs disk 16/15 -> RED
PASS B4-G1: bare pool / labels / vertical slice / denominator injections
PASS invariant manifest: receipt_producers=46, receipt_consumers=51, transport_calls=57, atomic_writes=37, formal_entrypoints=58, exceptions=0
```

## 2. scanner 分母与三条守卫

1. transport census 现在覆盖 `requests`、`urllib.urlopen`、`httpx`、`aiohttp`、内部 `net`、字面量 curl 和变量命令 curl。为什么：网络入口不再依赖某一种 import/调用写法。
2. formal 必经最小集从 `CHAIN_REGISTRY` 的真实 readiness/capability facts 与 `shared_release_receipt.py` 的 accounting/reconciliation producer registry 推导；manifest 可保留更广维护入口，但不得漏掉推导集。为什么：删文档中的脚本名字不再能静默缩分母。
3. manifest 新增五类 `minimum_counts`：`46/51/57/37/58`。任何列表/ schema 分母低于冻结 floor 即红；`--self-test` 删除和伪加 transport 也都保持 RED。
4. labels 分两类对表：resolver/manual known 面=`eth,bsc,base,arbitrum,robinhood,sol`；表资产面=`labels_table=True` 的 `eth,bsc,base,robinhood,sol`。Robinhood exploration 保留资产能力，未被 release-tier 口径误删。
5. 纵切片显式映射：eth/bsc/base→EVM test，sol→Solana test；每条链同时验测试文件在场和 SUITE 挂载。
6. Robinhood 活跃文档的“16 个普通文件/15 个 Python”由 scanner 与磁盘逐次对表，闭合 `full-F-04` 的数字漂移。

## 3. fixture 全库审计

审计范围：`scripts/tests/` 共 88 个文件；使用 schema/legacy/API 全文 `rg`，并聚焦执行 handoff 65 项和 B2 legacy hardening。

| 面 | 检查结果 |
|---|---|
| handoff v1/v2 | 只出现在 `test_handoff_manifest.py` 和 `test_batch2_legacy_hardening.py`；默认 strict/freeze 均拒，合法旧案仅显式 `--legacy-read-only` 可读，磁盘在场 wrapper 仍深验 |
| current reconciliation/envelope | handoff 正 fixture 含 current reconciliation wrapper 与四份 current receipt；six-lens/B3 producer 正例走生产 builder/CLI |
| 旧 Solana schema | `solana-gpa-cache-v2`、`solana-holder-snapshot-v2` 只在 round4c 伪造/旧源负例，预期被 offline replay 绑定拒绝，不是 formal 正例 |
| 手写 PASS | 保留在 validator/gate 单元 fixture；端到端 B3 正例先删旧产物、由真实 producer 重造。`test_fault_injection` 的空壳 receipt 只用于缺文件负例 |
| 删除 API | `activate_test_vertical_slices`、旧 `_record_from` dict 注入、Mapping 自报 readiness 调用均为零命中 |

聚焦执行：`test_batch2_legacy_hardening.py` PASS；`test_handoff_manifest.py` 65/65 PASS。

**审计结论：零过时 fixture。** 本批没有为了“审计动作”修改任何既有 fixture。

## 4. 六个批三遗留脚本的发布可达性

| 脚本 | rg 消费链 | 判定 |
|---|---|---|
| `trace_wallet.py` | 只写 `data/trace_<addr>.json`；生产代码零 consumer | 探索工具，发布路径外 |
| `gas_origin.py` | 只写 `data/gas_origins.json`；方法文档人工取证，生产代码零 consumer | 探索取证工具，发布路径外 |
| `probe_escrows.py` | 只写 `data/escrow_probe.json`；生产代码零 consumer | 探索取证工具，发布路径外 |
| `stake_decode.py` | `stake_ledger.json` 仅被 `whale_deep.py` 作为可选销户反查输入 | 手工预处理，未进 runner/required artifacts |
| `whale_deep.py` | 输出被 `build_evolution.py` 消费；后者 `camp_series.json` 无 release consumer | 纵向分析辅助链止于发布闸外，当前非 formal producer |
| `scan_sharded.py` | 产兼容 `holders_accounts/owners`；正式 registry 的 supply producer 仍是 `scan_token_accounts.py` | fallback/探索采集，未进 formal producer registry |

六者本批不迁。若未来进入 formal runner、handoff required artifact 或 release consumer，必须先迁 current envelope/attested transport，再更新 producer registry；新增入口将由 INV-17 守卫转红提醒。

## 5. 方法论写回

`references/maintenance-review-repair.md` 只追加第七章，未改写既有内容。新增：

- 新引入/半修残留全严重度修复重审，历史 P2/P3 记录＋限定复核，代码问题连续三循环则冻结；
- 施工→独立复核/代 commit→对抗审查→消化→重审→裁决；
- 未映射 hunk=0、map 三条通例原文和物理/语义 owner 互注；
- 边界外一步、同族等深、声明与磁盘实态、先删后真造；
- transport-only fake 五字段和 fixture 使用边界。

## 6. 新建代码自审（六视角①②）

### ① 字段来源

- labels 期望集合直接从 immutable `CHAIN_REGISTRY` 的 release/capability facts 计算，不采信测试或某个 labels 文件自报。
- formal 必经 producer 路径从生产 registry AST 字面量读取，并受实际 formal-ready family 约束。
- vertical slice 事实同时读 registry、磁盘文件和 SUITE，任何单份声明都不足以通过。
- Robinhood 数量从磁盘逐次计数，再与活跃文档拆分总数/Python 数核对。

### ② 失败分支

- 任一 AST/locator 数量不符、额外链、漏链、裸池、缺测试、脱 SUITE、正式 registry 漏登记、分母下降或 RH 数字漂移都会追加 scanner error 并使进程 exit 1。
- scanner 无跳过参数；测试注入全部在系统临时目录，不改生产/labels/references 资产。

## 7. 归因预判

- `R8-05`：scanner v6.35 新建时语法与 formal 分母模型不足，维持“新引入”；本批直接修复 INV-17。
- `B1R-01`、`B3R-Q1`：历批新代码缺第二道自动绑定，按批内观察收口。
- `OB-B`：历史 labels 多份手写清单缺双向守卫，按“历史漏检”记录，不新增 44 分母。
- `full-F-04`：文档计数漂移已在批二改正，本批补动态守卫完成 secondary INV-17。
- fixture 审计零过时、六脚本未进入 formal release，不产生新 finding。

## 8. 逻辑分组

| 分组 | 文件 / 目的 |
|---|---|
| `B4-G1` | `invariant_scan.py`、`invariant_manifest.json`、`test_batch4_invariant_guards.py`、`run_all.py`：scanner 分母与三条自动守卫。 |
| `B4-G2` | `references/maintenance-review-repair.md`：只追加闭环方法论。 |
| `B4-G3` | `ledger.md`、`diff-finding-map.md`、`batch4-report.md`：证据补齐、fixture 审计和六脚本判定。 |

## 9. 全量门禁与改动文件

执行：

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
PASS invariant manifest: receipt_producers=46, receipt_consumers=51,
transport_calls=57, atomic_writes=37, formal_entrypoints=58, exceptions=0
PASS test_batch3_solana_vertical_slice.py
PASS test_batch3_evm_vertical_slice.py
PASS test_batch4_invariant_guards.py
全部通过
EXIT=0（80/80）
```

补充机器检查：`docs_lint.py --all` 58 份文档全绿；两份 JSON 均可由
`python3 -m json.tool` 解析；仓库内无 `.pyc`/`__pycache__` 残留。
`git status --porcelain` 仅列出下方八个允许文件；`git diff --check` 为零错误。

### 测试/守卫

- `scripts/tests/invariant_scan.py`
- `scripts/tests/invariant_manifest.json`
- `scripts/tests/test_batch4_invariant_guards.py`
- `scripts/tests/run_all.py`

### 方法论

- `references/maintenance-review-repair.md`

### 台账

- `maintenance/repair-20260806/ledger.md`
- `maintenance/repair-20260806/diff-finding-map.md`
- `maintenance/repair-20260806/batch4-report.md`

既有 fixture、生产业务代码、CHANGELOG 均零改动。
