# 独立复核协议：报告是被审对象，不是证据

本协议用于复核任何既有筹码报告、第三方报告或旧版分析。目标不是”评价报告是否合理”，而是从原始链上数据重新建立可复算事实，再逐条裁决原报告命题。

> **作用域与入口**：本协议仅适用于“复核既有报告”任务。`audit_release_gate.py` 的底层 validator 由两条流程共用，但入口强制分开：全新分析=`--profile new-analysis`（共享三账、对账、分类、静置仓与对抗复核资产），净室复核=`--profile independent-audit`（共享资产＋`audit_input_manifest.json`、`claim_registry.json`、`reproduce_audit.py`）。`build_html --mode analysis-new|analysis-audit` 与 `a4_seal.workflow_type` 机器匹配；不得拿净室专用资产要求卡死全新分析，也不得把净室复核降成共享 profile。

## 本册路由

- §1–§3 净室、冻结与正确性；§4–§6 三账/CEX/历史图；§7–§8 命题与否决；§9 交付资产。

## 1. 净室原则

1. 开工时只把原报告拆成 `claim_registry.json` 的待审命题，不得把其实体表、阵营桶、标签、峰值或结论当作计算输入。
2. 实体、地址类型和历史序列必须从原始 Transfer、owner余额、交易调用、原生币对价、mint/burn、LP/质押/桥/托管权益及独立标签源重建。
3. 原报告附带的衍生 JSON、图表和分类表只可列入“被审资产”，不得与原始数据混为一层证据。
4. 若必须复用原报告的脚本，先记录其输入血缘，并用独立脚本或独立数据源交叉验证；不得以“正文、图、JSON三处一致”证明正确，因为三者可能同源一致地错。

`claim_registry.json` 是净室命题主表，A4 register 会生成执行态 `a4_claims.json`；两者不是可各自维护的两套结论。`a4_gate finalize --workflow-type independent-audit` 必须逐项对账 claim id、规范化文本、最终 verdict、证据文件集合和报告位置，任一缺失或分歧均 exit 2，seal 同时绑定两份表。

## 2. 输入冻结与时间线

开工第一步生成 `audit_input_manifest.json`，逐文件记录：

- 相对路径、字节数、SHA-256、修改时间；
- `evidence_layer`：`raw` / `independent_label` / `derived_subject`；
- `available_at_audit_start`；
- 冻结时间和数据截止时间。

发布前重新验哈希。冻结后新增文件单列 `late_additions`，不得悄悄并入旧审计口径。结论必须注明是由开工时材料、补采材料还是交付后新增材料支持。

## 3. 三类正确性不得互相替代

- **算术正确**：地址余额加总、供给闭合、时间锚点一致。
- **分类正确**：每个大额地址是私人钱包、CEX、协议设施、LP、桥、锁仓还是未知。
- **经济归属正确**：最终受益权属于谁，能否证明赎回权或持续控制。

供给闭合只证明没有丢币，不能证明地址类型和经济控制。地址互转、共同gas、账户创建和同步操作最多证明运营控制；没有最终受益权证据，不得升级为庄家经济控制。

## 4. 强制三账与全覆盖候选集

独立复核必须生成：

- `membership_ledger.json`：严格成员、扩展关联、排除地址、逐边证据及目标块逐地址余额绑定；
- `position_ledger.json`：目标时点币停留的链上位置；
- `economic_control_ledger.json`：钱包自持和可证设施权益，含防双计键与未决暴露；
- `address_classification.json`：当前所有 ≥0.1% 总供应或 ≥0.2% 流通的 owner（与 tiering §6a 其他大户线同源，2026-07-30 用户定；6.5.0 修订，原 0.5% 线废止）、历史越过判级线的地址、已归零/大幅回落/长期静置地址的完整分类；
- `dormant_warehouse_audit.json`：历史峰值、归零仓、静置仓、关键窗口上游和边界外一圈的裁决。

当前榜单不是全史候选集。只要历史候选、静置仓候选或达到其他大户线（≥0.1% 总供应或 ≥0.2% 流通）的当前 owner 仍有未裁决项，就不得发布”无其他庄””全盘零庄”等完整阴性结论。

## 5. CEX与资金通道裁决

1. 进入交易所只证明币进入托管或可售状态，不证明已经卖出。
2. 主仓经中转流向CEX，能证明“强CEX连接的运营/资金通道”，不能单独证明运营者是交易所、做市商或非庄家。
3. 核心仓零DEX交互不是“非庄一票否决”：筹码可能来自CEX、OTC、上游钱包、项目分配或链下交割。
4. CEX标签余额只能称“公开标签地址余额下限”；不得写成完整客户托管、交易所自营库存或单一经济控制量。
5. CEX身份、资金通道功能、最终受益人和操盘意图是四个不同命题，必须分别列证据和裁决。

## 6. 历史图发布门槛

历史阵营图只能来自全量逐事件重放，或同一粒度、同一覆盖口径的日终采样。禁止：

- 稀疏锚点前向填充后用末日全量快照封口；
- 将截断鲸鱼流水、发射窗和全量快照拼成同一条“全史”曲线；
- 对负累计值静默钳制为零；
- 把未跟踪的大额地址塞入散户残差后仍称“完整阵营演变”。

发布前生成 `chart_reconciliation.json`，至少通过：

- 末日逐地址对同截止快照；
- 各阵营同日合计与供给闭合；
- 倒数第二日到末日异常跳变检查；
- 大额地址覆盖检查；
- 缺口和插值检查；
- 图表成员集合与三账同源检查。

任一项不通过，禁止画图1/图2；只能展示当前快照或带明确缺口的观测点。

## 7. 命题注册表与阴性结论

`claim_registry.json` 每条命题必须包含：

- `claim_id`、原命题、命题类型和报告位置；
- `verdict`：`confirmed` / `weakened` / `refuted` / `unverified`；
- 原始证据文件、受控复算 receipt、反例和备择解释；命令文本只作说明，不作放行证据；
- 未解决事项及其是否阻断发布；
- 对下游结论的依赖关系。

`confirmed` 命题必须有原始证据和 `reproduce_receipt`。用
`scripts/report/reproduce_receipt.py <案目录>` 运行案内固定入口 `reproduce_audit.py`；
receipt 绑定入口脚本哈希、`audit_input_manifest.json` 哈希、参数、exit code 0、
输出文件大小/哈希与关键摘要哈希。发布闸只重验 receipt 与当前文件，绝不执行
claim 里的 `reproduce_command`。完整阴性命题还必须证明候选集完整、未决候选为零、黑箱边界已量化。证据只够否定旧结论时，必须停在 `unverified`，不得为了交付完整叙事另造一个肯定结论。

### 存量 reproduce-receipt/v1 迁移

`reproduce-receipt/v1` **不得原地升级**或补字段冒充 v2；旧 receipt 与旧输出先改名归档为
`reproduce_receipt.v1.archived.json` / `reproduce_output.v1.archived.json`（保留审计链，不覆盖），
再由唯一生产生成器 `scripts/report/reproduce_receipt.py` 重跑：

```bash
python3 scripts/report/reproduce_receipt.py <案目录> \
  --output reproduce_output.json --receipt reproduce_receipt.json
```

controller 会先确认正式输出不存在，再独占创建 staging 文件、设置
`CHIP_REPRODUCE_OUTPUT=<staging绝对路径>` 后执行案内固定入口。`reproduce_audit.py` 必须直接打开该
环境变量指向的文件写入并保留 inode；禁止继续硬编码 `reproduce_output.json`，也禁止临时文件
`os.replace`/rename 覆盖 staging。exit code 非零、未写 staging、inode 被替换、输出不是 JSON 或摘要
无法计算均不产 PASS receipt。迁移成功后更新 claim registry 引用新 v2 receipt；旧 v1 只归档，
不能进入发布闸。这样“存量怎么迁”由完整重跑回答，“谁生产新格式”由上述 controller 回答。

## 8. 对抗复核否决权

至少设置实体归因怀疑者和完整性批评者两类独立复核。复核者直接读取原始数据，不审阅主报告叙事。任何以下发现均为发布否决项：

- 运营控制被升级为最终受益权；
- CEX、公共设施、路由器或协议仓被确权为庄家；
- 候选集、历史流或静置仓审计不完整；
- 图表与同截止快照不闭合；
- 结论依赖抽样范围外事实；
- 阴性结论存在尚未排除的合理备择解释。

`adversarial_review.json` 的 `blocking_findings` 非空或未逐项关闭时，不得发布肯定性实体判级、完整阴性结论和历史图。

## 9. 强制交付资产与发布命令

独立复核至少交付：

```text
audit_input_manifest.json
accounting_mode.json
reconciliation_report.json
address_classification.json
membership_ledger.json
position_ledger.json
economic_control_ledger.json
dormant_warehouse_audit.json
claim_registry.json
adversarial_review.json
shared_release_receipt.json
reproduce_audit.py
reproduce_receipt.json
reproduce_output.json
```

三账正式 schema（空数组不构成审计证据，正式发布一律拒绝空壳）：

- `membership_ledger.json.entries[]`：`entity_id,address,membership,as_of_balance_raw,balance_source`，其中 membership 只能是 `strict|expanded|excluded`；地址规范化后全局唯一。每个有效成员必须绑定 `address-balance-snapshot/v1` 的 `path,sha256,as_of_block`，快照 `entries[]` 的地址与 `balance_raw` 必须与成员账逐行一致。零余额必须显式写 `as_of_balance_raw: 0`，或写非空 `zero_balance_proof`并由同一绑定快照证明为 0。
- `position_ledger.json.entries[]`：`entity_id,address,location_id,amount_raw`；每条地址必须映射到同一实体的有效成员，`(location_id,address)` 唯一，金额为非负 raw integer。发布闸会按地址汇总所有位置，并要求每个有效成员的 `Σ amount_raw == as_of_balance_raw`；无位置行只能与经证明的零余额闭合。
- `economic_control_ledger.json.entries[]`：按 `economic-control-accounting.md` §5；发布闸从明细重算 `wallet_self_held_raw == Σ position.amount_raw`、`confirmed_economic_control_raw == wallet_self_held_raw + Σ claim.token_raw`，并校验 `double_count_key` 全局唯一及所有权/数量算法/目标块证据齐全。任何 `unresolved_count` 都必须与实际 unresolved 明细一致，汇总布尔和自报 count 不作为放行证据。

`accounting_mode.json` 必须是当前 `scripts/evm/accounting_gate.py`（Solana 为 `scripts/solana/accounting_gate_sol.py`）的 `accounting-gate/v1` exit 0 产物，并带脚本自身的 `producer.path/sha256`。
  `reconciliation_report.json` 使用 v2 target，并给四查逐项绑定 exit-0 receipt 与仓库当前白名单生产脚本：balance/supply=`scripts/evm/verify_recon.py`、supply_truth=`scripts/lib/supply_truth_gate.py`、time=`scripts/lib/time_spotcheck.py`（Solana 对应 balance/time=`scripts/solana/anchor_sampler.py`、supply=`scripts/solana/scan_token_accounts.py`）。案目录里的同名/复制脚本即使抄到正确 SHA-256 也不是生产者。
  `adversarial_review.json` 使用 v2 target；实体归因怀疑者与完整性批评者都必须通过当前 `scripts/report/adversarial_review_runner.py` 启动独立 entrypoint，绑定新鲜非空 artifact 与 `adversarial-review-execution/v1` execution receipt，聚合器同时重验 runner、entrypoint、artifact。
  示例：`python3 scripts/report/adversarial_review_runner.py <案目录> --role entity_attribution_skeptic --entrypoint review_entity.py --artifact review_entity.md --receipt review_entity_execution.json`（另一角色用 `completeness_critic`）。三者完成后由唯一生产聚合器运行 `python3 scripts/report/shared_release_receipt.py <案目录>`，生成并哈希绑定三者的 `shared-release-receipt/v1`。
  存量裸布尔、无 producer 的 accounting、任意 producer/runner 或无 execution receipt 的旧文件都不得手工补字段迁移：必须重跑当前 accounting/四查生产工具和两个固定 runner，再运行聚合器；任何 receipt 后替换都会阻断。

涉及历史图时另需 `chart_reconciliation.json`。发布前运行：

```bash
python3 scripts/report/audit_release_gate.py <案目录> --report <报告.md>
```

退出码0才可交付。退出码2表示硬闸失败：保留已复算事实，但把实体判级、历史峰值、历史图和完整阴性结论统一降为“本轮无法裁决”。
