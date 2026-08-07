# R8 修复闭环：批二能力矩阵施工报告

## 1. 范围与边界

- 开工校验：`git rev-parse HEAD` = `553806b7cda2c954a2d1f55b13182274ada6d57d`，符合工单。
- 施工范围：批一 P3 收尾 `INV-05/INV-15`；批二主轴 `INV-11/INV-12`，以及 Robinhood `INV-20` 防回流。
- 对应 finding：`R8-04`（P3 附注）、`R7-14`、`R8-10`、`R7-07`、`R8-02`、`R8-06`，同族 `R7-08`；`full-F-04` 同步现役文档计数。
- `R8-12` 边界不变：本批只完成 kernel producer-ref P3 加固，`anchor_sampler.py` / `window_fetch.py` 迁入联合事务仍属批三。
- Robinhood 三个采集器 `pull_transfers_rpc.py`、`pull_block_ts_anchors.py`、`merge_hs_rpc.py` 业务逻辑未修；`full-F-02/full-C-01/full-C-05` 由 `RH-EX-01/02` 路径外豁免候选承接。
- 未调用真实 RPC/API。测试只使用本地 fixture/fake；Robinhood 红测补录在 `mktemp -d` 解包只读 `git archive HEAD`，不产生 git 写操作。
- `CHANGELOG.md`、archive 和历史案例段零改写。

## 2. 先红后绿证据

所有候选测试均设 `PYTHONDONTWRITEBYTECODE=1`。

### B2-G0：批一 P3 收尾

红：先写 `test_batch2_p3_hardening.py`，分别在冻结实现上实跑：

```text
AssertionError: parse_risk_flags("\u200btornado-user") != ("tornado-user",)
AssertionError: producer path with intermediate symlink accepted
AssertionError: build_labels.py 仍保留本地 risk_flags 字符串拼接
exit=1
```

绿：

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch2_p3_hardening.py
PASS B2-G0: invisible/type risk flags + producer symlink + OB-2 canonical merge
exit=0
```

| 测试 ID | 覆盖 |
|---|---|
| `B2-P3-RF-01` | `U+200B` 前缀、`U+FEFF` 全空和混合不可见空段按边界空白清理 |
| `B2-P3-RF-02` | list/int/bool 等非 `str`/`None` 结构错误抛 `TypeError`，不再 `str()` 静默吞错 |
| `B2-P3-RF-03` | OB-2：`build_labels.py` 复用 `merge_risk_flags`，本地拼接灭迹 |
| `B2-P3-RK-01` | producer 路径中间目录 symlink 被 `_secure_target` 逐级拒绝 |

`B1-RF-03` 的 470879 行现役表对表与批一 receipt kernel 套件继续全绿。

### B2-G1：INV-11 能力矩阵

红：先写 `test_batch2_capability_matrix.py`，冻结基线首个失败为：

```text
ImportError: cannot import name 'RELEASE_TIERS' from 'chain_registry'
exit=1
```

初版 registry 转绿后，choices 对表又因 `accounting_gate.py` 仍读本地 `DEFAULT_RPC` 转红；十个批一 RPC 调用点全部改为矩阵派生 choices 后最终绿：

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch2_capability_matrix.py
PASS B2-D: immutable release tier + capability closure + derived CLI choices

$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch1_rpc_attestation.py
PASS B1-B RPC session: wrong-chain zero business/fail-closed/correct/failover
```

| 测试 ID | 覆盖 |
|---|---|
| `B2-CAP-01` | 记录中不存在 `formal=True/False`；顶层和嵌套 capability 记录不可原地赋值 |
| `B2-CAP-02` | accounting/balance/supply/time/runner/consumer/identity/labels/handoff/audit/attestation/vertical-slice 每一缺项单独导致 `formal_ready=false`；EVM 还必须有 chain ID |
| `B2-CAP-03` | 当前 formal tier 候选仅 eth/bsc/base/sol，但因 `vertical_slice_verified=false` 全链均不 ready |
| `B2-CAP-04` | registry↔四 mandatory CLI↔handoff↔audit release 及六个其余 attested CLI choices 对表 |

为保留旧契约的正式正例覆盖，`formal_ready_test_harness.py` 在独立子进程或同进程受控 `contextmanager` 作用域内复制矩阵，把 formal-tier 的 `vertical_slice_verified` 临时置真，并在 `finally` 恢复原三层只读矩阵。批内消化修正了此处原“只在独立测试进程”的不实表述；生产代码仍无环境变量、CLI 参数或可写开关绕过。

### B2-G2：INV-12 READY reconciliation

红：先写缺 reconciliation 负例，冻结基线实际接受：

```text
AssertionError: (0, '[generate] READY 14 件产物 3 个 gate ...')
exit=1
```

绿：`REQUIRED_FOR_READY` 无条件纳入 wrapper，verify 端复用 `shared_release_receipt.validate_reconciliation_report`深验 target、当前 runner、四个白名单 producer、四份 receipt 哈希/envelope/语义：

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch2_ready_reconciliation.py
PASS B2-D: READY rejects missing reconciliation wrapper and bound receipts

$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_handoff_manifest.py
handoff_manifest 契约测试全部通过（65 项）
```

| 测试 ID | 覆盖 |
|---|---|
| `B2-REC-01` | READY 缺 `reconciliation_report.json` 在 generate 阶段 exit 2 |
| `B2-REC-02` | wrapper 必须恰好包含 balance/supply/supply_truth/time 四查且全为 PASS/0 |
| `B2-REC-03` | scope 只允许单链；wrapper target chain/token 与 READY scope 双向绑定，BSC wrapper 不得复用到 Solana |
| `B2-REC-04` | 所有 producer/runner 必须是当前仓库脚本及当前哈希；receipt 必须通过独立 envelope 与分类语义校验 |

### B2-G3：Robinhood exploration 防回流

红：用新负例在系统临时目录回放只读 `HEAD=553806b`：

```text
BASELINE_RH_READY_RC 0
[generate] READY 14 件产物 3 个 gate 1 件密封 ...
AssertionError: baseline accepted Robinhood READY
exit=1
```

绿：

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch2_robinhood_exploration.py
PASS B2-E: RH exploration is blocked by READY/A4/A5/build/audit and exemption sentinel
exit=0
```

`B2-RH-01` 包含七个必须面：

1. `release_tier=exploration`、`evm_chain_id=None`、`formal_ready=false`；
2. READY handoff 拒绝 Robinhood；
3. A4/A5/build_html/audit release 两个 formal profile 全拒；
4. 包含四份 schema/哈希自洽回执的 RH exploration 案仍不能生成 formal manifest/data map 可达图；
5. `labels-robinhood.csv` 存在且非空不抬升 tier；
6. 旧 RH A4 seal 不能用于 A5 重签，formal HTML 不落盘；
7. 豁免失效哨兵对 `release_tier=formal` 或任何非空 `evm_chain_id` 立即转红。

## 3. 同族 `rg` 清单与处置

### 3.1 能力声明与 choices

`rg` 复查结果：生产 `formal_chains()` / `formal_ready_chains()` 消费只保留 `handoff_manifest.py` 的 readiness 集合；`audit_release_gate.py` 逐链调 `formal_ready()`。四 mandatory CLI 使用 capability-specific 集合，批一其余六个 RPC CLI 使用 `attested_evm_chains()`。

| 类别 | 调用面 | 处置 |
|---|---|---|
| mandatory formal producers | `accounting_gate.py`、`verify_recon.py`、`supply_truth_gate.py`、`time_spotcheck.py` | 分别从 accounting/balance/supply/time capability 派生 choices |
| 其余 attested EVM 工具 | `fetch_alchemy.py`、`lp_positions.py`、`multicall_balances.py`、`pierce_stake.py`、`scan_bloxroute_seg.py`、`rpc_batch.py` | 从有 chain-id attestation 事实的 EVM 集合派生，保持批一错链零业务调用 |
| 标签维护 | `goplus_check.py` 仍有标签资产链字面列表 | 非 formal release/JSON-RPC 入口；不用于推导 readiness，批四 scanner 补双向监测 |

生产文本中不存在 registry record 的 `formal=True/False` 或与 readiness 同义的第二开关。

### 3.2 EVM RPC 同族面

复查 `eth_call|eth_getLogs|eth_getTransactionReceipt|eth_getBalance|alchemy_getAssetTransfers`：

| 分类 | 调用点 | 处置 |
|---|---|---|
| 正式/现役 | accounting/recon/time/supply/multicall/pierce/lp/bloxroute/rpc-batch/alchemy 十点 | 全部仍走批一唯一 `attested_rpc_pool`；choices 改为矩阵派生 |
| 历史/诊断 | `scripts/evm/scan_transfers.py` | 不迁；不得作 formal producer 回流 |
| exploration | `scripts/robinhood/pull_transfers_rpc.py` 及 RH 同族 | 不迁业务逻辑；RH 无 formal chain attestation，由豁免+防回流承接 |
| 非 JSON-RPC | HyperSync/SQD/Sourcify/GoPlus | 保持各自协议 gate，不套 EVM chain-id session |

### 3.3 Robinhood 文档与资产

- `references/data-pipeline-robinhood.md` 及三分册只在顶部现役入口增加 exploration 边界，历史实测/坑/案例段不改写。
- `analyze-workflow.md` 将 RH 路由改为 exploration only，并把 identity 能力与正式发布资格拆开。
- labels README/MAINTENANCE 将“标签表完整性”与 release tier 拆开；资产和 benchmark 未删。
- `scripts/robinhood/` 实数为 16 个普通文件（15 Python + 1 config），现役文档已从“全14件”改为 16。数字动态守卫与 `INV-17` scanner/manifest 分母同属批四，本批不再造一个文档专用清单副本。
- 影响台账 `RH-EX-01/02` 已填能力矩阵证据、`B2-RH-01` 和失效条件；Fable/盲审栏仍留空待裁决。

## 4. 新建代码六视角自审：①字段来源、②失败分支

| 工单 | ① 字段来源审计 | ② 失败分支审计 | 结论 |
|---|---|---|---|
| P3 / `INV-05` | producer 身份来自调用方词法路径；复用 `_secure_target` 逐级 lstat/dirfd 检查后才 resolve/hash，没有从 resolve 结果反推安全。 | 中间/最终 symlink、越界、非文件均在生成 producer ref 前拒绝；不改批一回滚/PASS 保护。 | P3 路径身份漏口闭合。 |
| P3 / `INV-15` | risk flag 只接受 `str`/`None`；边界空白由 Unicode `isspace` 和 `Cf/Zl/Zp/Zs` 类别判定；五个消费者仍共用 parser/merge。 | 结构类型错误抛出；不可见全空段归一为空集；正常历史字符串宽进语义不变。 | 470879 行现役表不误伤。 |
| D / `INV-11` | release intent 只来自受控 `release_tier`；readiness 只由 12 项 capability facts + EVM chain ID 计算；CLI/handoff/release 不保存第二份链集。 | 未知 tier、缺任一事实、EVM 缺 chain ID、未经纵切片均关闭；错链时批一零业务调用契约不回退。 | 批三前生产 `formal_ready_chains()` 为空是预期。 |
| D / `INV-12` | READY reconciliation 的事实来自实际 wrapper/回执文件、当前仓库 producer 哈希与独立 validator，不信 wrapper 自报。 | 缺件、多/少 check、非 PASS/0、runner/producer 非当前、receipt 哈希/envelope/语义错、target 跨链均拒绝。 | `R8-06` 的“整闸可省”路径已切断。 |
| E / `INV-20` | RH tier/chain ID 只读 registry；labels/docs/旧 seal 都只是资产或历史证据，不是 readiness 来源。 | RH 在 READY 读产物前即拒；A4/A5/build/audit 同一错误源关闭；formal/id 变化让豁免哨兵转红。 | 路径外豁免已有防回流候选证据。 |

自审中发现并处理两个契约不一致：①旧 handoff/A4/A5 正例在生产全链 not-ready 后失去测试覆盖，改为测试进程内复制矩阵的统一 helper，未加生产绕过；②旧 handoff 正例是手写三 gate，改为内容/哈希完整的四回执 fixture，缺 reconciliation 改为明确负例。端到端 fixture 真实性的全面审计仍属批四。

## 5. 归因预判

| finding / 评审项 | 预判 | 批二处置边界 |
|---|---|---|
| `B1R-03` | 批一新建代码 P3 | 本批开头修复并限定复核，不重置盲审计数 |
| `B1R-04` | 批一新建代码 P3 | 同上；不将 producer 迁移边界扩大到批三 |
| `R7-07` | 新引入；后续同族构成半修残留链 | 手工 formal 声明已灭迹，readiness 改为能力闭合派生 |
| `R8-02` | 半修残留 | RH 降 exploration，候选豁免 `RH-EX-01/02` 有防回流证据；待 Fable 批准 |
| `R8-06` | 半修残留 | READY 必含并深验 reconciliation；producer 真实执行 `INV-01` 仍由批三纵切片闭合 |
| `R7-08` | 历史漏检，同族 INV-12 | “整道 reconciliation gate 可省”残留面随 `R8-06` 收口 |
| `full-F-04` | 报告未判定，P3 | 现役计数改为 16；动态守卫留批四 INV-17 统一收口 |

本报告不填 ledger 的“最终结果”或 Fable 结论。

## 6. 逻辑分组（Fable 代 commit）

| 分组 | owner | 文件与目的 |
|---|---|---|
| `B2-G0` | `INV-05/INV-15`; `R8-04`附注、`R7-14`、`R8-10` | `risk_flags.py`、`build_labels.py`、`receipt_kernel.py`、`test_batch2_p3_hardening.py`；两项 P3 + OB-2 收尾。 |
| `B2-G1` | `INV-11`; `R7-07`、`R8-02` | `chain_registry.py`；四 mandatory CLI 与六个其余 RPC CLI choices；`test_batch2_capability_matrix.py`、`test_chain_registry.py`、`test_chain_support_matrix.py`，`test_r7_findings.py` 对应 hunk。 |
| `B2-G2` | `INV-12`; `R8-06`、`R7-08` | `handoff_manifest.py`、`shared_release_receipt.py`、`audit_release_gate.py`；`formal_ready_test_harness.py`；handoff/audit/A4/A5 相关契约 fixture；`test_batch2_ready_reconciliation.py`。 |
| `B2-G3` | `INV-11/INV-20`; `R8-02`、`RH-EX-01/02`; secondary `full-F-04` | `test_batch2_robinhood_exploration.py`、`SKILL.md`、RH 四文档、`analyze-workflow.md`、labels README/MAINTENANCE、`robinhood-impact.md`。 |
| `B2-G4` | 批二共享维护件 | `run_all.py`、`ledger.md`、`diff-finding-map.md`、本报告。Fable 需按 owner hunk 分组暂存。 |

## 7. 门禁结果

- 第一轮全量：67/74 PASS；7 个失败全是旧 formal BSC 正例未提供批三纵切片事实或仍调用删除 API，无生产新失败分支。
- 定向修正后：R7 15/15、audit release、P104/P105/P106、A5、A4 23 项全绿。
- 最终全量：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py` 结束 `exit=0`，**74/74 PASS**，汇总 `全部通过`。
- `invariant_scan.py`：PASS（随全量 suite 实跑）。
- `docs_lint.py --all`：PASS，58 个文档无断链/粗体失配。
- `SKILL.md`：7483 bytes，低于 8192B 硬限。
- `git diff --check`：PASS。
- `transport-injections.json`：`json.load` PASS，本批未新增生产 transport 注入点。
- 结束前已清理 4 个误生的 `.pyc` 及两个空 `__pycache__` 目录；未删除任何受版本控制文件。

## 8. 批内消化（B2R-01～B2R-05）

### 8.1 边界和设计取舍

- 本轮以工单声明 tip `5924cd5` 为起点；按工单未执行任何 git 命令，`reviews/` 只读。
- 对照 `robinhood-impact.md` 后结论是“拒绝 RH legacy READY”与 `RH-EX-01/02` 一致：豁免的核心正是 RH exploration 产物不得进入 formal 交接/对账/发布。未发现需升级给 Fable 的豁免冲突。
- legacy 豁免粒度收紧为“新件缺席可豁免”，而非“旧 schema 全面免验”：旧 v1/v2 案可不含 `reconciliation_report.json`；一旦 artifacts 宣称该 wrapper 在场，必须经当前 validator 深验四回执、producer/runner/hash/envelope，并绑定唯一 scope chain 与 contract。
- legacy 链准入不使用批三前为空的 `READY_CHAINS`；改读 registry 长期 `release_tier`。仅已登记 formal tier 的 eth/bsc/base/sol 可作合法旧案，exploration、unsupported 或伪造链均拒绝。
- OB-A 选择“补真实消费点”：`audit_release_gate.py` 只要在 case 目录发现 `legacy_readonly_receipt.json`（含 symlink）就拒绝编译新正式 analysis。这与 receipt 现有注释承诺一致，比降级注释更少副作用。

### 8.2 逐项先红后绿证据

#### B2R-01 + OB-A（FIX-1）

红：先新增 `test_batch2_legacy_hardening.py`，在未修代码上实跑：

```text
exit=1
test_b2f_lg_01_robinhood_legacy_rejected: B2F-LG-01: Robinhood legacy READY bypassed admission
test_b2f_lg_02_triple_mismatch_rejected: B2F-LG-02: chain/token/wrapper triple mismatch passed
test_oba_legacy_receipt_blocks_formal_audit: []
```

修复：

- `handoff_manifest.py` 对 READY scope 统一验唯一非空 chain 和非空 contract；legacy 改按 registry tier 准入。
- legacy artifacts 内在场 reconciliation 必须有对应 auto gate，并经与严格路径同一个 `validate_reconciliation_report` 深验/绑定；缺席时仍保留旧案豁免。
- `audit_release_gate.py` 消费 legacy receipt 并 fail-closed。

绿：

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch2_legacy_hardening.py
PASS B2F-G1: B2F-LG-01..04 + OB-A legacy formal-release guard
exit=0

$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_handoff_manifest.py
handoff_manifest 契约测试全部通过（65 项）
exit=0
```

`B2F-LG-03` 对 v1/v2 各回放一个 bsc 案：案内自洽、无批二 wrapper，legacy verify 仍 `rc=0`。`B2F-LG-04` 证明同案严格 verify 与 freeze 仍均拒绝。审查表 C0–C10 所在严格契约 65 项全绿，行为未回退。

#### B2R-02（FIX-2）

红：

```text
record_is_formal_ready accepted caller-supplied Mapping
```

修复：删除 `_record_from` Mapping 直通；`formal_ready` / `missing_formal_capabilities` / `record_is_formal_ready` 公开路径统一只接受 registry 链名字符串，非字符串抛 `TypeError`。需构造 record 的逐能力测试改用 `formal_ready_test_harness.fixture_missing_formal_capabilities`显式测试入口；生产 `audit_release_gate.py` 仍传链名。

绿：伪造全 True Mapping 对三个公开 API 均抛 `TypeError`；`test_batch2_capability_matrix.py` 与 `test_chain_registry.py` 均 `exit=0`。

#### B2R-03（FIX-3）

红：

```text
missing reversible fixture context
test_alphabetical_import_does_not_leak_readiness: AssertionError
```

修复：`test_vertical_slices()` 改为 `contextmanager`，用 `finally` 恢复原 `CHAIN_REGISTRY` 对象；patched registry 顶层、record、capabilities 三层全部 `MappingProxyType`。`test_audit_release_gate.py` 改为每次 `gate.run` 短作用域激活，`test_round4_a5_seal.py` 在 `main` 内受控激活，模块 import 不再泄漏 readiness。本报告 §2 原不实“只在独立测试进程”表述已就地修正。

绿：同进程激活时 formal tier 四链 ready；退出后 `formal_ready_chains()==set()` 且恢复原对象；三层赋值均失败；按字母序 import 两测试模块后仍为空集。

#### B2R-04（FIX-4）

红：

```text
test_child_bytecode_guard_is_explicit: AssertionError
```

修复：`run_formal_script` 补 `child_env.setdefault("PYTHONDONTWRITEBYTECODE", "1")`。

绿：`test_batch2_registry_harness_hardening.py` 通过；全量 suite 后 `find` 为空，仓库内无 `.pyc` / `__pycache__`。

#### B2R-05 + OB-D（FIX-5）

- `diff-finding-map.md` 的 `B2-G0` 补了 `build_labels.py` `BUILD_CHAINS` 注释 hunk owner，secondary 为 `INV-11`。
- 批二区间由 `553806b..07fab90` 更正为含 Fable 回填的 `553806b..5924cd5`。
- 新 hunk 全部登记为 `B2F-G1`～`B2F-G3`，未映射候选为 0。

### 8.3 观察项与新代码自审

- `OB-B`：labels 侧硬编码链清单副本仍留给批四 scanner 做 registry↔labels 双向守卫，本批不动。
- `OB-C`：通过 `gc` 刻意穿透 `MappingProxyType` 属当前威胁模型外，不修。
- ① 字段来源：legacy chain/contract 只取 manifest scope，tier 只取 registry，reconciliation 事实只取当前 wrapper/回执 validator；不信 legacy 标签、gate 自报或 caller 传入的 capability Mapping。
- ② 失败分支：scope 空/多链、contract 空、未登记/exploration/unsupported 链、在场 wrapper 缺 gate/深验失败/绑定不符、legacy receipt 回流、非字符串 readiness 输入全部 fail-closed；harness 异常退出仍 finally 恢复。

### 8.4 逻辑分组（Fable 代 commit）

| 分组 | owner | 文件与目的 |
|---|---|---|
| `B2F-G1` | `INV-12`; secondary `INV-20`; `B2R-01/OB-A` | `scripts/report/handoff_manifest.py`、`scripts/report/audit_release_gate.py`、`scripts/tests/test_batch2_legacy_hardening.py`；legacy scope/tier/在场 recon 补闸与 audit receipt 消费。 |
| `B2F-G2` | `INV-11`; secondary `INV-12`; `B2R-02/03/04` | `scripts/lib/chain_registry.py`、`scripts/tests/formal_ready_test_harness.py`、`test_batch2_capability_matrix.py`、`test_chain_registry.py`、`test_audit_release_gate.py`、`test_round4_a5_seal.py`、`test_batch2_registry_harness_hardening.py`；公开 API 收口与可恢复三层只读夹具。 |
| `B2F-G3` | `INV-11/INV-12`; `B2R-05/OB-D` | `scripts/tests/run_all.py`、`maintenance/repair-20260806/diff-finding-map.md`、`batch2-report.md`；挂载、owner/区间回填与批内消化证据。 |

### 8.5 最终门禁与改动文件

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
...
PASS test_batch2_legacy_hardening.py
PASS test_batch2_registry_harness_hardening.py
...
全部通过
76/76 PASS
EXIT=0
```

生产代码：

- `scripts/lib/chain_registry.py`
- `scripts/report/handoff_manifest.py`
- `scripts/report/audit_release_gate.py`

测试：

- `scripts/tests/formal_ready_test_harness.py`
- `scripts/tests/test_batch2_capability_matrix.py`
- `scripts/tests/test_chain_registry.py`
- `scripts/tests/test_audit_release_gate.py`
- `scripts/tests/test_round4_a5_seal.py`
- `scripts/tests/test_batch2_legacy_hardening.py`
- `scripts/tests/test_batch2_registry_harness_hardening.py`
- `scripts/tests/run_all.py`

台账/报告：

- `maintenance/repair-20260806/diff-finding-map.md`
- `maintenance/repair-20260806/batch2-report.md`

`reviews/` 零改动；本轮未改 ledger 的“最终结果”或 Fable 结论栏。
