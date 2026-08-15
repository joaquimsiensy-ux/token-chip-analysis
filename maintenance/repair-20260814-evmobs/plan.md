# F-02/F-03 修复计划：EVM 链上观测锚（evm-observation-bundle/v1）【经 @CX 融合】

> 仓库：`/Users/uravvv/.claude/skills/token-chip-analysis`（main=83394ab, v6.42.0）
> 状态：三路代码探索 + codex @CX 只读复核已融合，待用户批准开工。
> codex 意见采纳情况在文中以【CX】标注；其结论"方案主体可保留，但五项必改"已全部吸收。

## Context（为什么修）

codex 六视角审查（2026-08-14，BLOCK）的 3 个 P1 里有两个共享同一根因，均已验证属实：

- **F-02**：EVM `supply_truth` 收据的 `onchain_total_supply` 是现场 RPC 观测后的自报标量（supply_truth_gate.py:502-513 现场 eth_call → :718 直写整数），案内无冻结块观测实物；消费侧只有 Solana 分支做 bundle N-2 数值对账（shared_release_receipt.py:575-603），EVM 无对称分支。
- **F-03**：EVM 冻结时点 `as_of_block`/`tip_block`/`model_probe_block` 三字段同源写进 accounting_mode.json（accounting_gate.py:436-441），消费侧只做同件内大小关系比较（shared:762-778），无外部锚。

台账对应：R10-13（设计要点已留档）+ R10-9/C-R1。本会话专职此件，其他 finding 由其他 fork 分支修。

**关账口径【CX 必改项 A，采纳】**：一份案内 bundle 仍是案内可伪造件（R10-9 原文自己写明"锚到案内件只是多一个可伪造件"）。因此本工程：
- **R10-13/F-02 → CLOSED**：从"裸标量"升为"案内可复算观测实物"，达到 Solana N-2 等深；
- **R10-9/F-03 → MITIGATED（仍 OPEN）**：伪造成本从"改三个数字"抬到"编造整套块头+调用 transcript+哈希链"，但外部真实性锚（独立 RPC 复验/案外签署/git 上位登记）仍是开放项，台账如实标注，不得标 CLOSED。

## 设计总览

**定位**：Solana bundle 身兼三角色；EVM 四查 supply 槽被 verify_recon.py 占死且 runner 硬性恰好四键（reconciliation_report.py:160-162），故 EVM 观测件走"runner 之前独立 producer + 双收据绑定 + spec inputs 快照"，零改 runner：

```
observe_supply.py（新，runner 之前独立跑）
   → evm_observation_bundle.json + RPC transcript 文件（publish_txn 双件原子）
        ├─→ accounting_gate.py --bundle        （as_of_block 锚定，升 accounting-gate/v2·EVM）
        ├─→ supply_truth_gate.py --observation-bundle（onchain 供给来源，升 supply-truth-receipt/v4·EVM）
        ├─→ runner spec["inputs"] 快照（零改 runner）
        ├─→ shared_release_receipt.py：EVM 三处绑定（镜像 Solana）
        └─→ handoff_manifest.py READY：同一公共 validator【CX 必改项 B】
```

**诚实边界**（文档如实写）：bundle 是内容绑定，不是块真实性或 producer 真执行证明——离线消费侧无法证明 blockHash/RPC 响应为真；增量价值是案内落了 blockHash 与调用 transcript，第三方可拿去任何公共节点独立验真。与 audit-protocol.md:165 现有口径一致。

## Bundle 规格（`evm-observation-bundle/v1`）

走 receipt_kernel 信封（build_envelope/finalize_envelope，target 三键），业务块：

| 块 | 内容 | 备注 |
|---|---|---|
| `attestation` | `expected_chain_id`（chain_registry）/`observed_chain_id`（`pool.attest()`）/`endpoint`（endpoint_fingerprint，EVM 首用） | 【CX 措辞修正】错链保护本就在每次业务调用前自动执行（net.py:317 _attest_endpoint）；显式 attest() 的价值是把 observed chain id **落件**，非首次获得保护 |
| `anchor` | `eth_getBlockByNumber(as_of_block)` 的 `{number, block_hash, parent_hash, timestamp}` + `eth_blockNumber` tip 观测；number==target.as_of_block、as_of≤tip；**业务调用前后各取一次块头，两次 hash 必须全等**；记录 `tip−as_of` 确认深度 | F-03 锚。【CX 必改项 E】前后夹验防重组/节点漂移 |
| `supply` | 同一冻结块 eth_call 三笔：totalSupply/balanceOf(ZERO)/balanceOf(DEAD)。**块参数优先 EIP-1898 `{"blockHash":…,"requireCanonical":true}` 按哈希执行**，节点不支持时明确报错换端点（fail-closed，不静默降级），binding 形态落 bundle | 【CX 必改项 E】把状态读取钉在 hash 上而非块号 |
| `code` | `eth_getCode(token, as_of_block)` → `runtime_code_sha256` | 【CX 必改项 G】**只声称防合约地址/部署状态混淆，不承诺防代理升级**（Transparent/UUPS 升级改的是 EIP-1967 storage 非 runtime bytecode）；不用 keccak（标准库无，不为此加依赖），sha256 做案内完整性指纹并如实命名 |
| `inputs` | **canonical RPC request/result transcript** 落盘文件并绑定（input_base=案根） | 【CX 必改项 D】RpcPool.call_many 返回的是归一化 `{"ok","result"}`（已剥 jsonrpc/id），不是原始响应——命名改准；transcript 每条必须记 method/完整 params/result/顺序唯一键/block selector/解析后十进制值——只存响应值无法证明"这份 0x 是哪个方法哪个 token 哪个块返回的" |

**validator `validate_evm_observation_bundle`**（producer 落盘前对内存对象先跑同一函数——maintenance-review-repair.md:172 铁条）：信封走独立 receipt_validate（case_root）；expected_token/expected_chain_id 绑定；attestation 双值与注册表三方相等；anchor.number==target.as_of_block、as_of≤tip、前后块头 hash 全等；三笔数值与 transcript 实物重读对账（method+params+result 三元组校验，非只对 result）；bundle_path 在场时 canonical sha 字节等值。

## Schema 升版【CX 必改项 C，翻我原 D1】

- **EVM supply_truth 升 `supply-truth-receipt/v4`；Solana 暂留 v3**。理由（codex，采纳）：本次把 EVM formal 从"无需 bundle"改成"缺 bundle 必拒"并改变 onchain_total_supply 权威来源，是实质破坏性变更；waiver 留 v3 的先例不适用（waiver 是条件性输入）；v2→v3 升版先例正是"新增强制语义"场景（CHANGELOG:134）。shared 对 EVM formal 只接受 v4；v3 EVM 存量只允许 legacy-read-only，禁新 READY/发布。
- **EVM accounting 升 `accounting-gate/v2`；Solana 留 v1**（新增强制 bundle/execution_mode/锚字段，同理）。
- 升版连锁（施工首步 rg 全库，第八层纪律）：camp_series_provenance.py:401 SUPPLY_TRUTH_SCHEMA 写死 v3 → 按链分版或改双接受；shared:525 schema 断言分 family；契约注册表新增 v4/v2 needle（v3/v1 不 banned——Solana 现役）；文档三处串分链写清；全部测试夹具。

## 逐文件施工清单

### A. 新建
- `scripts/lib/evm_observation.py`：观测协议 + build/validate（对标 solana_observation.py；无 activity/窗口/三方闭合——EVM archive 冻结块直查即终态）
- `scripts/evm/observe_supply.py`：CLI producer（对标 scan_token_accounts.py 骨架：quarantine_current → error envelope 先建后重建 → 发布前自验 → publish_txn 双件原子 → publish_error_receipt + 端点脱敏）；`--as-of-block` 必给 + assert_declared_slot 断言

### B. `scripts/lib/supply_truth_gate.py`
- `--observation-bundle` 链无关，EVM formal 必给；EVM formal：onchain 与 sink 三值全部从 bundle 读，**业务阶段断言零 RPC**【CX 收缩版第 3 条】；envelope_inputs 绑 bundle；schema EVM 分支产 v4；exploration 保留现场 RPC（v3 行为不变）

### C. `scripts/evm/accounting_gate.py`
- 加 `--bundle`（formal 必给）/`--exploration` 互斥 + `execution_mode`；formal 下 **`as_of_block` 从 bundle 派生，CLI `--as-of-block` 降为可选一致性断言，不再是第二权威源**【CX 收缩版第 4 条】；result 加 observation_bundle ref + observed_anchor{block, block_hash}；EVM 产 accounting-gate/v2；本轮不迁 receipt_kernel（D2 维持，codex 有条件同意——os.replace 非本轮阻断项）

### D. 消费侧：抽公共 validator，shared 与 handoff 双消费【CX 必改项 B——真实旁路】
- 现状旁路：handoff_manifest.py READY 只对 reconciliation wrapper 深验（:333），accounting 的 AUTO_GATE 只重读 verdict/exit_code（:477）——accounting→bundle 绑定若只加在 shared，split-run 的 stage-1 READY 仍可绕过
- 修法：从 shared_release_receipt.py 抽出 `validate_accounting_receipt(root, expected_target=None)` 与 `validate_evm_observation_source_chain(root, accounting, recon_receipts)`（含：bundle 案内三验 → validate_evm_observation_bundle → as_of==anchor.number → **accounting 与 supply_truth 绑同一 bundle sha**），由 `shared_release_receipt.validate_sources` 与 `handoff_manifest._verify_light_schema` 同时调用，不在 handoff 手抄第二套
- supply_truth EVM 分支：N-2 数值对账 onchain==bundle.supply.totalSupply + anchor.number==target.as_of_block（对称抄 Solana :575-603）
- bundle 与 transcript 进 handoff artifact 必备/传递面（搬案不漏被间接引用的实物）
- ACCOUNTING_PRODUCERS/RECON_PRODUCERS/runner 不改

### E. 测试三件套
- **原反例先红后绿**：codex 报告 F-02/F-03 两个最小反例修后被拒；**F-03 回归须同步改 accounting+reconciliation target+四份 receipt target，确认最终被"bundle anchor mismatch"拒绝而非被旧 target mismatch 提前拦截**【CX 补充反例 1】
- 生产者协议负测（新 test_evm_observation.py）：chainId 错→零业务、eth_call 响应非法、anchor 前后块头 hash 不等、declared as_of 与观测不符、发布前自验被拒→两件不落盘、error receipt 脱敏
- 消费侧负测：accounting 缺 bundle/锚块不符/supply_truth 缺 bundle/onchain 与 bundle 不符/两收据绑不同 bundle；**handoff verify 对前三种同样分别拒绝**【CX 补充反例 2】；**transcript 只换 method/params 保留 result 必须拒绝**【CX 补充反例 3】
- 夹具：FixtureHandler 补 eth_getBlockByNumber 分支 + eth_call 的 EIP-1898 dict 块参数分流；execute_real_slice 插观测件真跑；test_audit_release_gate.build_case 补 bundle+两收据升版；test_repair_batch_a._retarget_evm_case 同步；test_supply_truth_gate FakePool 加 bundle 场景
- 绿例：eth/bsc/base 三链纵切片端到端

### F. 登记面（含【CX 必改项 F】五补）
| 登记点 | 动作 |
|---|---|
| invariant_manifest.json | receipt_producers/consumers 按 AST 实际枚举登记（lib+CLI+accounting+supply_truth+shared+handoff，不只手列三个）；transport_calls；atomic_writes；minimum_counts 抬地板 |
| invariant_scan.py 源码 | FAILURE_ARTIFACT_COVERAGE 加条目（protections 含 self_quarantine）；**FAILURE_ARTIFACT_CONTRACTS 加新 producer canonical_artifacts=2**（双件事务两旧件都须 quarantine 检查，不只 coverage）；FORMAL_E2E_REQUIRED_PRODUCERS 三链各加 |
| formal 能力 | **formal_capability_probes.ACCOUNTING_SUPPLY_ADAPTER_TARGETS 加新 producer；chain_registry 的 accounting_supply_adapter 升 evm-accounting-supply-v2**；test_batch1_rpc_attestation 错链零业务 callsite 集合加新 producer |
| 契约注册表 | CT-SEMANTIC-57：needle `evm-observation-bundle/v1`（authority=data-pipeline-evm-recon.md）+ v4/v2 相关 needle 更新 + ids_snapshot 排序插入 |
| run_all.py SUITE | 手动挂新测试（唯一无守卫点，同 commit 自查） |
| 版本五处 | VERSION/pyproject/CHANGELOG 索引+详情（全角—，存量影响段+suite 分母段）/SKILL.md 注释 → 暂定 6.43.0，多 fork 合并时让号 |
| 文档 | audit-protocol.md:166 改写（EVM 供给一半闭合+"bundle 是内容绑定非块真实性证明"边界+分链版本）、:182 补迁移口径；data-pipeline-evm-recon.md；scan-schemas.md:341-345 核对；避免孤立 E0/U1~U6 |
| R10 台账 | **R10-13 标 CLOSED 6.43.0；R10-9 标 MITIGATED 仍 OPEN**（外部真实性锚开放，可选修法留档：独立 RPC 复验/另一主体签署 bundle sha/git 上位登记）；最小行编辑防与 F-07 线冲突 |

## 决策点终稿（经 @CX）

| # | 定论 | 来源 |
|---|---|---|
| D1 | **升 EVM v4**（Solana 留 v3；v3 EVM 只 legacy-read-only） | codex 反对我原稿保持 v3，论证成立，采纳 |
| D2 | accounting 本轮不迁 receipt_kernel，但**升 accounting-gate/v2 + 抽共享 validator 给 handoff** | codex 有条件同意，条件已并入 |
| D3 | 进 FORMAL_E2E_REQUIRED_PRODUCERS，**且补 capability probe/failure contract/wrong-chain callsite** | codex "同意但不充分"，五补全采 |
| D4 | exploration 不强制 bundle——**理由改写**：仅指 ETH/BSC/Base 的显式非发布探索；两 CLI 的 choices 本就不含 Robinhood/Arbitrum | codex 纠正理由，采纳 |
| D5 | 保留 `runtime_code_sha256`，**删除"防代理升级"声称**（只防地址/部署状态混淆） | codex 反对原表述，采纳 |

## 存量影响（CHANGELOG 必写段）

已交付 EVM 案（QUQ/AKE/B2/TAG/MOG/APU/EGL1 等）accounting/supply_truth 均为 v1/v3 无 bundle：已交付不重跑发布闸不受影响；未来重发布必须先跑 observe_supply.py 并按 v2/v4 重做 accounting+supply_truth；禁手工补字段迁移。QUQ 监控走 posthold 独立体系不受影响。

## 施工组织

- 分支 `fix/evm-observation-20260814`；开工 commit `观测锚开工：plan落盘+基线冻结<N>绿@<sha>`
- 工单目录 `maintenance/repair-20260814-evmobs/`：plan.md（本计划）+ baseline_run_all.log + workorder_OBS_f0203.md（五栏模板）+ done + blindreview_OBS[_roundN].md + final_closure
- 节拍：基线冻结 → lib+CLI（先红）→ supply_truth v4 → accounting v2 → shared 抽公共 validator + handoff 接入 → 测试三件套 → 登记面 → 文档 → run_all 全绿 → 盲审 → 消化轮 → 收口
- 同族清单 rg 首步复核（v3/v1 schema 串全库、handoff/A5 消费点全数）

## Verification

1. run_all.py 全绿（含新增项）；git diff --check 干净；docs_lint/changelog_lint/invariant_scan/契约双向闭合
2. 原 F-02/F-03 反例被拒（先红后绿证据入 done 报告，F-03 须验"死在新闸而非旧闸"）
3. 生产者/消费侧/handoff 三层负测全红转绿；transcript 换 method/params 拒绝
4. 三链纵切片绿例 + wrong-chain 零业务含观测件
5. 盲审边界外一步攻击；"同步伪造整案"预期仍可过——文档如实声明该边界（R10-9 MITIGATED 的依据）

## codex @CX 复核记录

- 已送审（只读，read-only sandbox），codex 结论：**反对原稿直接开工，方案主体保留+五项必改**——①R10-9 不能关账（→MITIGATED）②handoff READY 旁路（→抽公共 validator 双消费）③升 v4/v2 ④transcript 命名与内容规格（归一化非原始响应）+EIP-1898 块哈希绑定 ⑤正式能力/失败产物登记五补；另纠正 attest() 价值定位、D4 理由、D5 代理升级表述。**全部采纳并已并入上文**。
- codex 亦确认：我对现状代码的读码结论属实；F-02 方案基本成立；runner inputs 路线合理。
