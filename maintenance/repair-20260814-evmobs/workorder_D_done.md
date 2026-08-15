# 工单 D 完工摘要：夹具升级、正式能力登记、文档与 6.43.0 收账

> 完工日期：2026-08-15（America/New_York）
> 边界：工单 D 最终施工单；未执行任何 git 命令，commit 由 Fable 完成。测试中生产脚本内部允许的只读 `git rev-parse` 不属于人工 git 操作。

## 1. 终态结论

- `python3 scripts/tests/run_all.py`：99/99 PASS，rc=0；EVM/Solana 纵切片在沙箱外获准使用 loopback 后实跑，不以环境项豁免。
- ETH/BSC/Base 三条正式纵切片均在 reconciliation 前真跑 `scripts/evm/observe_supply.py`，产 bundle＋transcript，再由 accounting v2、supply_truth v4、runner、shared/handoff/audit 消费。
- 原 F-02 标量改写反例被 N-2 bundle 数值对账拒绝；原 F-03 同步改 target/receipts 的反例最终死在 `EVM accounting bundle anchor mismatch: as_of_block != bundle anchor.number`，不是旧 target mismatch。
- `VERSION`、`pyproject.toml`、`SKILL.md`、CHANGELOG 一致为 6.43.0；R10-13 CLOSED，R10-9 MITIGATED 且仍 OPEN。

## 2. 改动清单

### 2.1 公共夹具与纵切片

- `scripts/tests/test_audit_release_gate.py`：唯一公共 `build_case` 改产真实 `evm-observation-bundle/v1`＋transcript；accounting 升 v2，supply_truth 升 v4，两者绑定同一 bundle。由此带动 audit、R7、batch2、reconciliation、formal support、P104/P202、round4b 等复用族转绿。
- `scripts/tests/test_supply_truth_gate.py`：`write_evm_bundle` 支持 eth/bsc/base 分链 chainId，供全仓夹具复用。
- `scripts/tests/test_batch3_evm_vertical_slice.py`：FixtureHandler 增加稳定 `eth_getBlockByNumber`；`eth_call` 同时支持块号与 EIP-1898 dict selector；`execute_real_slice` 真跑 observe_supply，accounting/supply_truth 传 bundle，runner inputs 登记 bundle/transcript；三链与 nonzero-dead 绿例均过。
- `scripts/tests/test_repair_batch_a.py`：所有 EVM formal supply/waiver 夹具产并传 bundle；`_retarget_evm_case` 同步重建 bundle、两收据和 wrapper 绑定；新增“改 target/tip/probe 不改 bundle”第五场景。
- `scripts/tests/test_repair_batch_d.py`、`scripts/tests/test_repair_batch1.py`：旧 formal supply CLI 夹具补 bundle。
- `scripts/tests/test_a4_gate.py`：copytree 新案同步搬迁 accounting/supply_truth 的 bundle 绝对引用并重建 shared receipt。
- `scripts/tests/test_handoff_manifest.py`、`scripts/tests/test_batch2_legacy_hardening.py`：EVM make_case 按目标链生成 bundle；重复 bsc chain 规范化绿例的 case target 与生成参数一致。

### 2.2 正式能力、失败产物与 invariant

- `scripts/tests/invariant_scan.py`：eth/bsc/base 的 `FORMAL_E2E_REQUIRED_PRODUCERS` 均加入 `scripts/evm/observe_supply.py`。
- `scripts/lib/formal_capability_probes.py`：新增 `evm-accounting-supply-v2`，解析顺序为 observe_supply、accounting_gate、supply_truth_gate。
- `scripts/lib/chain_registry.py`：三条正式 EVM 链的 `accounting_supply_adapter` 升 v2。
- `scripts/tests/test_r9_batch2_executable_capabilities.py`：新增精确 capability/三链 registry 回归，防只改声明或漏 producer。
- `scripts/tests/test_batch1_rpc_attestation.py`：错链零业务 callsite 加 observe_supply；supply/accounting 的非发布探索路径继续证明只调用 `eth_chainId`。
- `scripts/tests/invariant_manifest.json`：minimum floors 抬到扫描实况 61/78/63/52/58；receipt producer/consumer 与 formal entrypoints 已在 A/C 工单后和 AST 实况一致，无伪造额外入口。
- `FAILURE_ARTIFACT_COVERAGE` 与 `FAILURE_ARTIFACT_CONTRACTS` 的 observe_supply 条目已由工单 A 在场，复核确认 protections 含 `self_quarantine` 且 `canonical_artifacts=2`，本单未重复改写。

### 2.3 契约、文档、版本与台账

- `scripts/tests/contract_manifest.json`、`contract_ids_snapshot.json`：新增排序 ID CT-SEMANTIC-57～59，分别锚定 `evm-observation-bundle/v1`、`supply-truth-receipt/v4`、`accounting-gate/v2`。
- `references/independent-audit-protocol.md`：改写 EVM 供给闭合与诚实边界；写明 bundle 是内容绑定，不是块真实性或 producer 真执行证明；补 EVM v4/v2、Solana v3/v1、shared/handoff 双路线与存量重发布迁移。
- `references/data-pipeline-evm-recon.md`、`references/analyze-workflow.md`、`references/scan-schemas.md`：补 observe_supply 命令、EIP-1898、bundle 供给来源、零现场 RPC和分链 schema 口径。
- `VERSION`、`pyproject.toml`、`SKILL.md`：一致升 6.43.0。
- `CHANGELOG.md`：新增全角破折号详情块、工程目录、分链升版、存量影响、99/99 suite 分母与 R10 关账。
- `maintenance/repair-20260813-sixlens/r10_ledger.md`：仅编辑 R10-9/R10-13 两行；总数行未动。

## 3. 红 → 绿证据

### 3.1 公共根与纵切片

- `test_audit_release_gate.py` 施工前：rc=1，首错 `EVM accounting schema 'accounting-gate/v1' is not accounting-gate/v2`；升级 `build_case` 后 rc=0。
- `test_batch3_evm_vertical_slice.py`：沙箱内 `socket.bind EPERM` 后按批准在沙箱外实跑；修后 `PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure`。同轮 Solana vertical slice 也在完整 suite 通过，证实它的旧红属于 build_case 族而非豁免环境项。
- `test_repair_batch_a.py`：施工前 30/45 红，均为 formal 缺 observation bundle；修后 45/45 PASS。
- `test_repair_batch_d.py`、`test_repair_batch1.py`、`test_a4_gate.py`：分别从旧 formal/bundle 搬案红转为专项全绿。

### 3.2 正式能力登记先红后绿

先只加入精确回归并运行：

```text
test_r9_batch2_executable_capabilities.py rc=1
KeyError: 'evm-accounting-supply-v2'
```

补 capability target 与三链 registry 后：

```text
PASS R9 B3-G3/G4: six probes ready; deleting one slice drops its chain
```

错链专项随后通过，observe_supply 的方法集合严格为 `['eth_chainId']`；`invariant_scan.py` 终态为 `receipt_producers=61, receipt_consumers=78, transport_calls=63, atomic_writes=52, formal_entrypoints=58, exceptions=0`。

### 3.3 原 F-02/F-03 反例

`test_evm_observation_release.py` 11/11 PASS：

- F-02：只同步修改 supply_truth 标量、不改 bundle，消费侧以 bundle 的 `total_supply_raw` 重算后拒绝。
- F-03：同步修改 accounting、reconciliation target 与四份 receipt target，避开旧 target mismatch，仍以 `F03_LAYER=EVM accounting bundle anchor mismatch: as_of_block != bundle anchor.number` 被新锚闸拒绝。

### 3.4 lint/manifest

- docs lint：58 文档全绿。
- contract routes：注册表、ID 快照、五组锚与 SKILL 阶段双向闭合。
- changelog lint：版本唯一且顺序正确。
- version consistency：6.43.0 四锚一致。
- 用户禁止任何 git 命令，故未运行工单旧条目中的 `git diff --check`；以 `rg '[ \t]+$'` 对全部本单文件检查尾随空白，零命中，并由 JSON/文档/版本/完整 suite 守卫覆盖语法与 EOF。

## 4. 两个“预期红没红”的核实

### 4.1 `test_distribution_gate.py`：PASS 合理，不是漏洞

其 `supply-truth-receipt/v3` 是 `holder_distribution_scan.py` 的分布算法最小标量输入：无 formal target、accounting、reconciliation wrapper、shared/handoff/audit 调用。它不声称是可发布 EVM formal receipt，也不经过本次 v4 公共 validator，故不属于 EVM formal 迁移面；专项与完整 suite 均 PASS。

### 4.2 `test_repair_batch_c.py`：PASS 合理，不是漏洞

该文件的 EVM v3 夹具进入 camp-series/state compiler 的 provenance/schema/target/replay_stats 绑定测试；Solana 段的 v3 是现役合法版本。文件不调用 EVM shared/handoff/audit formal 发布链。独立实跑最终 `PASS: repair batch C ... 227 checks`，因此 B/C done 的“含 EVM v3 即应红”是按字符串清单作出的过度预期，不是 validator 放行漏洞。

## 5. 六视角①②自审

### ① 字段来源审计：PASS

- chainId 来自注册表与显式 attestation；anchor.number/hash/parent/timestamp 来自前后两次同块头；三笔供给值来自同一 EIP-1898 blockHash selector；transcript 将 method、完整 params、result、顺序与解析值绑定。
- accounting 的 as_of/observed_anchor 来自已验证 bundle，tip/model_probe 仍来自本次模型探测；两类时点未混源。
- supply_truth 的 totalSupply/ZERO/dead 只读 bundle，formal 业务阶段零 RPC；replay_net/mint/burn 回到 receipt 绑定的 replay_stats 实物。
- accounting、supply_truth、runner inputs、shared/handoff artifact 面绑定同一 bundle/transcript；copytree 夹具重绑当前案根，不允许绝对路径逃逸。
- 文档未扩大证明强度：bundle 只证明案内内容闭合；blockHash/transcript 仅提供第三方外验材料。

### ② 失败分支审计：PASS

- producer 对错链、坏块头、EIP-1898 失败、前后 hash 漂移、坏 transcript、自验失败均 fail-closed；双 canonical 旧件先 quarantine，失败落唯一 ERROR side receipt。
- accounting/supply_truth 对缺 bundle、错 token/chain/as-of、ref size/hash、bundle schema/producer/transcript、锚块和 N-2 数值不一致均拒；formal 不回退现场 RPC。
- shared、handoff、audit 共用公共 validator；READY artifact 缺 bundle/transcript 或两收据不同源均拒，无 split 旁路。
- wrong-chain observe_supply 只发生 `eth_chainId`；三链纵切片与 Solana 控制组均真跑，不拿 loopback 环境项抵代码红。
- 原 F-02/F-03 反例死在新闸；R10-9 未被误标 CLOSED。

## 6. 遗留移交

- R10-9/F-03 仍 OPEN：案内 bundle 可被蓄意同步伪造。后续若要 CLOSED，至少需要独立 RPC 复验、另一主体签署 bundle sha 或案外/git 上位登记之一，并给消费侧可验证身份链。
- `test_distribution_gate.py`、`test_repair_batch_c.py`、`test_review_20260804_p105.py` 等仍可见 v3 字符串，均为非 EVM formal 发布夹具或 Solana 现役控制组；不得为“清字符串”误升成 v4。
