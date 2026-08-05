---
name: token-chip-analysis
description: 对已具备受支持数据管线的链上代币做机构级庄家行为分析与既有报告独立复核——在声明的数据范围内采集重放、识别庄级实体并划分标签（项目方/大庄/小庄/离场庄/刷量地址）、重建阵营持仓演变、绘制重点实体流转路径、核算 V3/V4 流动性与可证 LP 权益，并交付经对抗复核的自包含 HTML。正式深度管线覆盖 Ethereum/BSC/Base/Arbitrum/Robinhood EVM、Solana；全新链须先补齐采集、对账与身份门禁适配器才可正式发布。当用户问"某代币的筹码分析/筹码结构/庄家行为分析"、"复核/审计已有筹码报告"、"有几个庄/庄家什么类型"、"庄家/项目方/做市商在吸筹还是砸盘"、"有没有关联地址/老鼠仓/单一实体控盘"、"庄家是不是跑了/弃盘了"、"看看某代币的链上持仓/大户动向"、"庄家做 LP 赚了多少/LP 手续费怎么计算"，或提到 holder analysis、鲸鱼追踪、代币尽调时使用。与 gmgn-token 的区别：gmgn-token 是快速单项查询；本 skill 是数小时深度分析工程。只查价格/K线/热榜/新币列表不要用本 skill。
---

<!-- skill-version-source: VERSION; skill-version: 6.15.0 -->

# 代币筹码分析（Token Chip Analysis）

固定交付“三问一异常”：①有几个庄；②每个庄什么类型；③各阵营在已声明且过闸的历史范围内持仓占比如何演变；④本次特有发现（确无发现写“无”）。占比以总供应为分母，锁仓/销毁单列。交付自包含 HTML；监控包只在用户确认买入后补。核心信条：**不对账的分析是猜测，未经反驳的结论是自嗨。**

## 铁律（7 条封顶，任何阶段不可越过）

1. **结论独立性**：只沉淀方法，禁止复用历史标的结论/数字/判定或作“上次也是这样”类比；同会话不连做两币。casebook 只提供方法级失败模式。
2. **对账关卡**：A2 四查（余额对账/供给闭合/供给真值闸/时间抽查）不过关不进分析。
3. **证据强度纪律**：用链上铁证/高度疑似/疑似/未能确证分级；意图不可区分时并列写（`report-template.md`）。
4. **对抗复核必做**：历史执行高频实质改写结论，必须给出实际重算证据；允许复核零推翻（REFUTED=0 如实记录），不可跳过。
5. **数据源取用**：key 以 `~/.claude/api-keys.md` 登记为唯一真源，运行时按其登记的原始存放位置（如 `~/.config/*`）读取；只写工作目录 config.json，永不写死进 skill 目录。
6. **成本纪律**：准确性优先；不得为省 token 砍复核路数或数据源，细则见 `context-discipline.md`。
7. **交付边界**：输出结构事实与风险判定，买卖裁决由用户做出。

## 全流程路由（细节唯一权威源＝`analyze-workflow.md` A0–A6）

| 阶段 | 核心动作 | 必读/产物 | 阻断语义 |
|---|---|---|---|
| A0 画像与路由 | 合约、多链、分母、链路由 | A0＋当链 pipeline；accounting_mode.json | accounting_gate：0 放行/2 硬停/1 修通道重跑 |
| A1 并行采集 | 完整数据＋标签＋价格 | A1＋当链 pipeline；data/、队列层 collect_manifest、链内 collection_manifest/receipt | — |
| A2 对账关卡 | 余额/供给闭合/供给真值/时间抽查 | A2＋recon；supply_truth.json、anchor_plan.json、time_spotcheck.json | 四查不过不进 A3；gate 0 PASS/2 FAIL/1 修通道重跑 |
| A3 分析 | 标注→归因→聚类→判级→ET→演变→facts/state | A3＋casebook C/E＋playbook；findings.md、facts.json、analysis-state.json、identity_gate.json | EF-1～EF-3 或 G8 未闭合即拒编译 |
| A4 对抗复核 | claims→扰动→揭盲→N 路复核→裁决→finalize | A4＋evidence-wording；a4_claims.json、a4_seal.json | 实际核查三档；a4_gate 未封口（2）禁进 A5 |
| A5 报告 | 三图＋流转图＋MD/HTML＋质检 | A5＋report-template；报告.md、a5_report_seal.json、报告.html | build_html 必须 0；G8/G9 A4 哈希/G10 A5 seal 任缺拒交付 |
| A6 复盘 | 仅用户明确要求时分流教训 | `retrospective.md`；CHANGELOG | run_all 全 PASS 后才 commit |

## A3 实体冻结门禁编号

- 编号：**EF-1 经济控制账闸**、**EF-2 历史静置仓反扫闸**、**EF-3 覆盖发现闸**；EF-3 含 **EF-3A 波次扫描**、**EF-3B 资金流异常扫描**、**EF-3C 候选裁决与实体溯源**，freeze 前置为 **EF-3C-P1** 严格 verify、P2 名册绑定、P3 溯源重查、**P4 原始输入及算法绑定重放**；ET-1/ET-2 是判级筛查，不混入 EF 计数。
- 阻断：控盘看最终经济控制，EF-1 必须落 `economic_control_ledger.json` 且公共设施不进永久成员表；EF-2 必须落 `dormant_warehouse_audit.json`；任一门禁或候选未闭合，就不允许冻结实体、发布峰值或出图。
- 权威定义：EF-1 见 `economic-control-accounting.md`；EF-2 与判级边界见 `playbook-entity-cluster-tiering.md`；EF-3、分段分工与 schema 见 `analyze-workflow.md`、`split-run.md`、`scan-schemas.md`。

## 六入口

- **/token-analyze**：A0–A5 完整版；A6 仅用户要求。
- **/token-easy-analysis**：`easy-workflow.md` E0–E7 轻量筛查档；同强度引擎/复核，砍完整报告，绝不自动转正式。
- **/token-analyze-1**：A0–A2＋A3 机械子层；按 `split-run.md` 交接后完成即停。
- **/token-analyze-2**：handoff verify 后接 A3 判断层＋A4–A5；easy/full 必选，A6 仍须用户要求。
- **/token-update**：`update-workflow.md` U0–U5（U6 仅用户要求）；复用旧实体表、只拉增量，按当前版本重判并区分持仓变动/标准迁移。
- **/collect-data**：`collect-workflow.md` 只采集零结论；以 collect_manifest/done.json 续增量，禁止从零重采。

## 上下文预算

- 峰值 <30 万 tokens（新链首战可放宽）；开局只读本文件＋当链 pipeline，其他按阶段读。大结果落盘，stdout ≤20 行，大文件分页，旧报告禁整读。
- 机械任务可外包，判断留主线；阶段边界写 findings.md，超预算在阶段边界压缩或新会话续跑。完整纪律见 `context-discipline.md`。

## 深入阅读（references/）

- 流程：`analyze-workflow.md`、`easy-workflow.md`、`update-workflow.md`、`collect-workflow.md`、`split-run.md`、`retrospective.md`、`context-discipline.md`。
- 方法：`analysis-playbook.md`、`playbook-supply-recon.md`、`playbook-entity-cluster-methods.md`、`playbook-entity-cluster-tiering.md`、`playbook-entity-cluster-cost.md`、`playbook-state-anomaly.md`、`playbook-evidence-wording.md`。
- 门禁/交付：`report-template.md`、`scan-schemas.md`、`economic-control-accounting.md`、`lp-fee-accounting.md`、`independent-audit-protocol.md`、`casebook/README.md`。
- EVM：`data-pipeline-evm.md`、`data-pipeline-evm-channels.md`、`data-pipeline-evm-sources.md`、`data-pipeline-evm-recon.md`。
- Solana：`data-pipeline-solana.md`、`data-pipeline-solana-scan.md`、`data-pipeline-solana-capture.md`。
- Robinhood：`data-pipeline-robinhood.md`、`data-pipeline-robinhood-channels.md`、`data-pipeline-robinhood-traps.md`、`data-pipeline-robinhood-methods.md`。
- 标签/环境：`address-book.md`、`labels/README.md`、`labels/MAINTENANCE.md`、`environment.md`。
- 按需：`monitoring-package.md`、`research-workflows.md`；`attic.md` 仅存留审计/整编会话可读，分析会话禁读。
