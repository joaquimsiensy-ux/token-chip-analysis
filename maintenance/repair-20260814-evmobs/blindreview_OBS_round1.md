# 盲审攻击报告 · EVM 链上观测锚工程（OBS round1）

- **审计对象**：commit 范围 `411bf18..56aa3eb`（工单 A/B/C/D），worktree `/Users/uravvv/.claude/worktrees/tca-evmobs`，分支 `fix/evm-observation-20260814-w`，HEAD=56aa3eb。
- **审计者立场**：独立盲审攻击者，与施工者无关。只读+只跑只读脚本/测试，未改任何生产/测试/文档件；本报告是唯一写入的仓库文件。

## 总结论：**PASS**

| 严重级 | 数量 |
|---|---|
| P0 阻断 | 0 |
| P1 高 | 0 |
| P2 中 | 0 |
| P3 建议/观察 | 2 |

四条工程宣称（F-02 CLOSED / F-03 MITIGATED / 消费无旁路 / 登记齐全 + run_all 99/99）经对抗验证**全部成立**。观测件校验闸 `validate_evm_observation_bundle` 对我构造的 **31 个伪造/篡改向量全部 fail-closed**；三方消费者都必经同一对公共 validator；exploration→formal、legacy 逃逸门、夹具直拼绕闸三条路均已封死；能力探针/E2E/失败产物/invariant 登记都真实接入门禁而非"装了等于没装"。关账文档诚实、未把案内自洽写成案外真实。两个 P3 均为可辩护的设计取舍或措辞提示，**不影响发布门禁强度**。

> 复现环境：本机 `python3`，全程离线。探针脚本见文末附录，临时产物落 `/private/tmp`，未留仓库根。`python3 scripts/tests/run_all.py` 独立复跑：exit 0，"全部通过"，SUITE 99/99（AST 静态计数 Assign+AugAssign = 99，与宣称一致）。

---

## 攻击面 A — bundle 伪造面（`scripts/lib/evm_observation.py`）

**结论：无 finding。** 校验闸对内容篡改与 transcript 逐位不一致做了完整交叉绑定。

我把 `validate_evm_observation_bundle`（`evm_observation.py:329`）拆成三道独立防线，逐一实测：

1. **信封哈希绑定**（`validate_receipt`，`receipt_validate.py:81`）：`inputs.transcript` 绑 size+sha256、`producer` 绑仓库件 path+sha256。任何只改 transcript 文件不改绑定的篡改在这里就被"input transcript size/hash mismatch"拦下（probe1 M4/M5/M8/M15/M16/M17）。
2. **bundle 字段自洽**（`evm_observation.py:338-395`）：verdict/exit/mode、producer==`scripts/evm/observe_supply.py`、chainId 三值全等（expected==observed==`evm_chain_id_for(chain)`）、endpoint 指纹结构、`block_hash==recheck_block_hash`（**前后两次块头全等校验确实作用在第二次块头**，见 `:377` 主闸 + `:323-326` transcript 侧双重）、`tip>=as_of` 且 `confirmations==tip-as_of`、supply 三值非负十进制、`block_binding`、runtime code sha 结构。
3. **transcript 语义逐位**（`_validate_transcript`，`evm_observation.py:260-326`）：`len==8`、方法序列、每行 `set(row)=={seq,method,params,result}`、`seq==index` 连续、params 全等（含 eth_call 的 `{"blockHash":anchor.block_hash,"requireCanonical":True}` 选择器、getCode 的 `[token,hex(as_of)]`）、**result 十六进制解析后必须等于 bundle 十进制值**（`:311-316`）、code sha 由 transcript result 重算比对。

**实测（现实伪造者视角：篡改 transcript 后重建信封哈希绑定，强制走到 `_validate_transcript`）**：14 个语义向量 13 个被拒（T1 额外字段/T2 缺 result/T3 seq 重复/T4 requireCanonical False/T5 blockHash 换块号 tag/T6 totalSupply 十六进制≠十进制/T7 tip/T8 chainId/T9 锚块 hash/T10 recheck hash/T11 方法重排/T12 eth_call to 换址/T14 行数 9），仅 T13（大写十六进制 `0xF4240`==1000000 等值，**本就应通过**）被接受——是我特意放的正确性对照，非漏洞。

**"result 十六进制与十进制不一致能否过？"**：不能。probe2 T6 直接反证。**"block selector 混淆？"**：不能，T4/T5 反证。**"attestation 双值/endpoint 能否绕？"**：不能，probe1 M2/M11 反证。

> 端点指纹 `sha256(完整endpoint)` 是不可逆哈希、`public_origin` 已脱敏（`endpoint_identity.py:52-57`），不构成密钥泄露；且 endpoint 本身不与外部真值对锚——这属 F-03 明示的诚实边界，非缺陷。

---

## 攻击面 B — 消费旁路第三条路

**结论：无 finding。** 三方消费者都必经 `validate_accounting_receipt`（`shared_release_receipt.py:795`）与 `validate_evm_observation_source_chain`（`:891`），无第二套手抄断言。

- **shared**：`validate_sources`（`:915-923`）直接两调。
- **handoff READY 深验**：`_verify_light_schema`（`handoff_manifest.py:352-356`）非 legacy 分支两调。
- **audit**：`check_accounting`（`audit_release_gate.py:239-245`）直调 `validate_accounting_receipt`；`validate_evm_observation_source_chain` 经 `shared_release_receipt.validate_bundle(case_dir)`（`audit_release_gate.py:1188` → `shared_release_receipt.py:951` → `validate_sources`）**传递性必达**。故宣称 3"三方同一对公共函数"成立（audit 侧 source-chain 是经 validate_bundle 达成，非独立手抄）。

**全库 grep 其余读者逐一排除**（`grep -rn accounting_mode|supply_truth.json|onchain_total_supply|observation_bundle scripts --include=*.py`）：
- `build_html.py`/A5 seal：**不读** accounting_mode.json（grep 无命中）。
- `adversarial_review_runner.py:337 _target_from_accounting`：仅抽 chain/token/block 当复核 target，不对未验字段做发布决策；且 audit gate `check_adversarial`（`audit_release_gate.py:1208-1216`）用**已验 accounting 派生的 expected_target** 反向校验复核 target 一致，无旁路。
- `camp_series_provenance.py` / `holder_distribution_scan.py`：见 P3-2，非发布决策路径、且被发布闸 v4 硬闸覆盖。

**legacy 分支不是 EVM 新案逃逸门**：进入 legacy 需同时满足①`consumer_min_schema ∈ LEGACY_SCHEMAS`（旧 schema，新案 −1 生产者写的是现役 schema）②显式 `--legacy-read-only`（`handoff_manifest.py:424`）。legacy 案落 `legacy_readonly_receipt.json`，而 `audit_release_gate.run`（`:1171-1173`）见此件即 append error"只读降级 legacy 案不得编译新正式 analysis"。即使强行手改 manifest 冒充 legacy，也过不了正式发布闸。legacy 跳过 source-chain 深验（`:352 if not legacy`）是"旧案无观测件"的正当设计，非新案可用的绕过。

---

## 攻击面 C — 生产侧逃逸

**结论：无 finding。**

- **exploration 冒充 formal**：`accounting_gate` exploration 出 `accounting-gate/v1`+`execution_mode=exploration`、**不落 observation_bundle/observed_anchor**；`validate_accounting_receipt`（EVM 分支 `:814-875`）硬要 `schema==accounting-gate/v2`、`execution_mode==formal`、`observation_bundle` 为 dict 并过 `validate_evm_observation_bundle`、`observed_anchor.block/block_hash==bundle.anchor`。手改 schema/execution_mode 两字段无法补出合法 bundle 绑定链，不构成升级。
- **supply_truth v3 冒充 EVM formal**：`validate_reconciliation_check`（`shared_release_receipt.py:530-533`）对 EVM **硬要 `supply-truth-receipt/v4`**，并在 `:638` 做 N-2：`receipt.onchain_total_supply == bundle.supply.total_supply_raw`。exploration 走 live RPC 自报的 v3 收据在 EVM 上直接被 schema 闸拒——**这正是 F-02 裸标量缺口在消费侧的真实闭合点**。
- **`observe_supply --as-of-block` 声明≠实际观测块**：`observe_evm_supply`（`evm_observation.py:158`）`assert_declared_slot(as_of_block, first["number"], ...)` fail-closed；`test_evm_observation.py::test_declared_as_of_block_mismatch_rejected` 实证（"assertion mismatch"）。producer 自验失败不落 canonical、落 ERROR 侧件（`test_prepublication_self_validation_failure_leaves_no_canonicals`、`test_eip1898_unsupported_fails_closed_without_outputs` 实证）。

---

## 攻击面 D — 夹具配合度

**结论：无 finding。** 夹具走真 `build_evm_observation_bundle`，validator 在测试路径上真正生效。

- `test_evm_observation.py`：`FakePool` 仅做 transport，`observe_evm_supply`/`build_evm_observation_bundle`/`validate_evm_observation_bundle` 全是真件；transcript 篡改测试是**先建真 bundle 再篡改 transcript 重验**（`:178-192`）。
- `test_supply_truth_gate.py::write_evm_bundle`（`:87-146`）手拼 `core`+transcript 但**交给真 `build_evm_observation_bundle`**，产物由 supply_truth_gate 里真 `validate_evm_observation_bundle` 消费——夹具是"正确复刻 producer 输出形态"，非"直拼绕过 validator"。
- `test_evm_observation_release.py::build_case` / `test_batch3_evm_vertical_slice.py`：后者**真跑 `observe_supply.py`** 对着 fixture 节点（fixture 断言 eth_call dict 选择器恰为 `{"blockHash":BLOCK_HASH,"requireCanonical":True}`，`:76-78`），再真跑 accounting v2 `--bundle`、supply_truth v4 `--observation-bundle`、shared_release_receipt，端到端经真 runner。我用夹具同法构造的 31 向量已证 validator 在此路径有牙。

**"亲手构造最小改动使伪造 bundle 通过全部闸"**：未能成功——任一改动要么破坏信封哈希绑定、要么破坏 bundle 自洽、要么破坏 transcript 逐位交叉。唯一"能过"的是等值不同表示（大写十六进制），不改变任何被消费的数值语义。

---

## 攻击面 E — 登记完整性（无"装了等于没装"）

**结论：无 finding。** 四类登记都真实接入运行时门禁：

- **能力探针**：`chain_registry.REQUIRED_FORMAL_CAPABILITIES` 含 `accounting_supply_adapter`（`:29-32`）→ `_missing_formal_capabilities_from_record` 调 `missing_executable_capabilities`（`:221`）→ `resolve_formal_capability` 对 `evm-accounting-supply-v2` 逐个 `importlib.import_module` 并断言 callable（`formal_capability_probes.py:181-205`），其目标元组新增 `scripts.evm.observe_supply:main`（`:29-33`）。observe_supply 缺失即令 eth/bsc/base 掉出 `formal_ready`。非可选参数。
- **FORMAL_E2E**：`FORMAL_E2E_REQUIRED_PRODUCERS`（`invariant_scan.py:62-88`）eth/bsc/base 均含 `scripts/evm/observe_supply.py`；`formal_e2e_provenance_errors`（`:751-781`）要求纵切片测试经真 runner 且执行证据覆盖全部登记 producer，主扫描 `:1325` 调用，`invariant_scan.py` 挂载于 `run_all.SUITE`（`run_all.py:11`）。
- **失败产物**：`FAILURE_ARTIFACT_CONTRACTS`（`:89-93`，canonical_artifacts=2）与 `FAILURE_ARTIFACT_COVERAGE`（`:125-128`）均含 observe_supply，被 `failure_artifact_contract_errors()`/`failure_artifact_coverage_errors()`（主扫描 `:1326-1327`）消费。
- **invariant_manifest**：登记 `observe_supply.py`/`evm_observation.py` 的 `evm-observation-bundle/v1` schema、net.py 与 dual_file_txn 语义（diff 实见）。
- **契约注册表**：`test_r9_batch2_executable_capabilities.py` 新增 `test_evm_accounting_supply_v2_resolves_observation_producer` 断言键与三链绑定；SUITE 全绿。

`run_all.py` SUITE 挂载无法被绕过：能力探针要求 test 必须出现在 `mounted_suite_tests()`（AST 解析 SUITE）中（`formal_capability_probes.py:201-204`），删测即掉能力。

---

## 攻击面 F — 关账诚实性

**结论：无夸大。文档措辞审慎，未把案内自洽写成案外真实。**

- **R10-9 标 MITIGATED**（`r10_ledger.md`）：明写"案内件仍可同步伪造，独立 RPC 复验/案外签署/git 上位登记未落"——与实际强度一致，**未夸大**。
- **`independent-audit-protocol.md` 改写**：明示"**bundle 是内容绑定，不是块真实性或 producer 真执行证明**：蓄意手拼者仍可同步伪造案内块头、响应和哈希链……不能把案内自洽写成案外真实。故 F-02 的裸标量缺口已闭合，外部真实性锚仍是开放边界。"——这是我见过对该类边界最准确的表述之一。
- **`data-pipeline-evm-recon.md` 改写**：同样明写"它证明案内内容闭合，不证明块头案外真实或 producer 确实执行"。

---

## P3 观察（不影响门禁强度，供施工者斟酌）

### P3-1 · r10_ledger 中 R10-13(A-4) 标"CLOSED"与 R10-9 标"MITIGATED"并列，措辞可能被粗读误解
- 位置：`maintenance/repair-20260813-sixlens/r10_ledger.md`（三、R10-13 行 与 R10-9 行）。
- 事实：R10-13 是"造 EVM 观测件锚定 onchain_total_supply"的**建设工单**，其 CLOSED 描述限于"producer 落块头+三笔调用+transcript+双路线 N-2 重验"，**本身未声称外部真实性**；R10-9 是同一底层问题的"真实对锚"残留，正确标 MITIGATED。二者同表相邻，且 audit-protocol 已显式兜底。
- 判断：**可辩护，倾向非 finding**。若求零歧义，可在 R10-13 CLOSED 后缀一句"仅指案内锚定建设完成，外部真实性锚见 R10-9(MITIGATED)"。
- 为何现闸拦得住误解：真正的发布门禁读的是代码闸（本报告 A–E 已证其强度），文档措辞不改变门禁行为。

### P3-2 · `camp_series_provenance.py` 对 EVM 案接受 `supply-truth-receipt/{v3,v4}`（非仅 v4）
- 位置：`scripts/lib/camp_series_provenance.py:401-403`（`SUPPLY_TRUTH_SCHEMAS={v3,v4}`）、`:442-461`。
- 事实：`registry_anchor_check` evm-dict 分支接受 v3 或 v4（注释明写"Solana/legacy EVM v3、EVM formal v4"）。这是**序列编译前置校验**，非发布决策；且它另验 PASS/exit0/target 三键/replay_stats sha 位绑定。
- 为何不是绕过 F-02：正式发布必经 `audit_release_gate`→`validate_reconciliation_check`，EVM **硬要 v4**（`shared_release_receipt.py:531`）。一份 v3 EVM 收据即便能编译 camp series，该案也无法正式发布。v3 仅对"legacy EVM 冻结案"开放，而 legacy 案被 `legacy_readonly_receipt.json` 挡在正式发布外（见攻击面 B）。
- 判断：**与 legacy 设计一致，非 finding**；仅记录该处 schema 接受面是链无关的、其 EVM-formal 收紧依赖下游发布闸，若日后有人把 camp series 产物直接当正式交付需复核此假设。

---

## 附录 · 复现命令与探针结果

```
# 基线：exit 0，全部通过，SUITE 99/99
python3 scripts/tests/run_all.py

# 探针1（17 向量，含 bundle 字段篡改 + 未重建哈希的 transcript 篡改）→ GAPS: NONE
python3 <scratch>/probe_validator.py
# 探针2（14 向量，现实伪造者重建 inputs.transcript 哈希后强制走 _validate_transcript）
#   → 仅 T13 等值大写十六进制被接受（预期正确对照），其余 13 篡改全拒 → GAPS 实质: NONE
python3 <scratch>/probe_transcript.py
```

两个探针均复用真 `build_evm_observation_bundle` + `test_supply_truth_gate.write_evm_bundle` 造合法 bundle，再施加篡改后调真 `validate_evm_observation_bundle(bundle_path=...)`。任一"ACCEPTED"即防线缺口；除刻意放行的等值对照外无一命中。

**审计边界声明**：本审计验证的是**案内一致性闸的不可绕过性**（F-02 裸标量缺口已闭合、消费无旁路、登记有牙），未、也无法验证 bundle 所载数值的**案外真实性**——那是 F-03 明示 OPEN 的诚实边界，需独立公共节点用 bundle 的 blockHash+transcript 外部复验或案外签署/git 上位登记才能进一步收敛，不在本工程宣称范围内。
