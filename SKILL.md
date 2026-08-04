---
name: token-chip-analysis
description: 对任意链上代币做机构级庄家链上行为分析与既有报告独立复核——全量数据采集重放、庄级实体识别与标签划分（项目方/大庄/小庄/离场庄/刷量地址）、各阵营持仓演变、重点实体流转路径图、V3/V4 流动性与庄家 LP 手续费归因、对抗复核、自包含 HTML 报告（用户确认买入后可补生成观察哨与监控 JSON 附录）。当用户问"某代币的筹码分析/筹码结构/庄家行为分析"、"复核/审计已有筹码报告"、"有几个庄/庄家什么类型"、"庄家/项目方/做市商在吸筹还是砸盘"、"有没有关联地址/老鼠仓/单一实体控盘"、"庄家是不是跑了/弃盘了"、"看看某代币的链上持仓/大户动向"、"庄家做 LP 赚了多少/LP 手续费怎么计算"，或提到 holder analysis、鲸鱼追踪、代币尽调时使用。与 gmgn-token 的区别：gmgn-token 是快速单项查询；本 skill 是数小时深度分析工程。只查价格/K线/热榜/新币列表不要用本 skill。
---

<!-- skill-version-source: VERSION; skill-version: 6.13.0 -->

# 代币筹码分析（Token Chip Analysis）

对标的回答三个固定命题（v5.0 三问框架）：**①有几个庄**（按标签体系计数：项目方/大庄/小庄/离场庄/刷量地址）**②每个庄什么类型**（单地址明牌/多地址互转·gas同源/伪装分散·指纹一致）**③各阵营全历史持仓占比如何演变**（占总供应，锁仓/销毁单列；建仓后动没动、拉升期有没有出货）。**开放条款：三问是下限不是上限**——任何显著结构性异常必须单列章节，TL;DR 设"本次特有发现"（确无发现明写"无"）。交付自包含 HTML 报告；**监控包默认不生成，用户确认买入后补**。核心信条：**不对账的分析是猜测，未经反驳的结论是自嗨。**

## 铁律（7 条封顶：新进＝旧出或代码化。任何阶段不可越过）

1. **结论独立性**：只沉淀方法，禁止复用任何历史标的的结论/数字/判定与"上次也是这样"式类比；同会话不连做两币。判例库是方法级失败模式，不是结论先验（casebook/README.md）。
2. **对账关卡**：阶段 2 四查（余额对账/供给闭合/供给真值闸/时间抽查）不过关不进分析。
3. **证据强度纪律**：证据强度用自然语言分级（链上铁证/高度疑似/疑似/未能确证）；意图不可区分时并列写（report-template「证据强度呈现」）。
4. **对抗复核必做**：历次执行每次都实质改写结论，投入产出比最高的环节，不可跳过。
5. **数据源取用**：key 从 `~/.claude/api-keys.md` 登记文件直接取用；运行时只写工作目录 config.json，永不写死进 skill 目录。
6. **成本纪律**：成本目标永远让位于准确性——为省 token 砍复核路数/数据源属于违反铁律；上下文纪律见 context-discipline.md。
7. **交付边界**：输出结构事实与风险判定，买卖裁决由用户做出。

## 全流程路由（完整版；每阶段细节的唯一权威源＝`analyze-workflow.md` A0–A6）

| 阶段 | 干什么 | 必读 | 硬闸（exit 语义） | 落盘产物 |
|---|---|---|---|---|
| A0 画像与路由 | 合约核定/多链硬关卡/分母口径/链路由 | A0＋当链 pipeline；多链读 casebook S 册 | accounting_gate：0 放行/2 硬停人工定制/1 修通道重跑禁当放行 | 计划、accounting_mode.json |
| A1 并行采集 | 全量数据＋标签＋价格（后台先行） | A1＋当链 pipeline | — | data/、collect_manifest |
| A2 对账关卡 | 四查：余额/供给闭合/**供给真值闸**/时间抽查 | A2＋当链 recon 分册 | 四查不过不进分析；supply_truth_gate：0 PASS/2 FAIL 余额改实时直查/1 修通道重跑；time_spotcheck 同语义（默认锚点直查，全史重拉仅例外） | supply_truth.json、anchor_plan.json、time_spotcheck.json |
| A3 分析 | 标注→归因→聚类→判级→大户双闸→演变重放 | A3＋**casebook C/E 册全过一遍**＋playbook 按需 | entity_identity_gate→build_html G8：flag 未解决报告物理编不出 | findings.md、identity_gate.json |
| A4 对抗复核 | claims 登记→扰动前置→揭盲→N 路怀疑者→三档裁决→**finalize 封口** | A4＋evidence-wording §10；casebook 三册作备择弹药 | 三档必须实际核查，"理论上可能"不算推翻；**a4_gate finalize 封口前禁进 A5（0 封口/2 未决拒封）** | a4_claims.json、a4_seal.json、复核修正记录 |
| A5 报告 | 三标准图＋流转图＋HTML＋质检（图一律 charts/final/） | A5＋report-template | build_html 退出码 0（缺图/G8/**G9 封口哈希**拒交付；--a4-seal 必传；有 WARN 不写出文件） | 报告.html、analysis-state.json |
| A6 复盘 | **仅用户明确要求时执行，不自动触发**：教训分流入库（分流决策树） | retrospective.md | run_all 全 PASS＋git commit | CHANGELOG |

## 实体冻结前三硬闸（A3 判级环节强制；前两闸 6.5.0 回灌转正，第三闸 6.6.0 W1 复盘）

- **控盘看最终经济控制，不看币停在哪个地址**：回答"庄控制多少"时主口径必须是实体的**可证经济控制量**（钱包自持＋在 LP/CEX 子账户/桥/质押锁仓/vault/托管等设施中可证明赎回权或受益权的等价权益），账本落盘 `economic_control_ledger.json` 并同源驱动 TL;DR/判级/实体表/图 2。三账分离：成员表答"哪些地址受控"、位置账答"币在哪"、经济控制账答"受益权归谁"；**公共设施不进永久成员表**，但可归属份额必须穿透回实体；设施总余额不得整池归庄，归属不清单列未决不得猜。细则唯一权威源＝`economic-control-accounting.md`。
- **历史静置仓反向扫描硬闸**：初步聚类后、实体名单冻结与峰值判级前，必须从历史峰值榜/已归零回落仓/长期静置仓/关键日激活仓反向追查平行库存与尾仓，并从核心网络向上游币源与边界外一圈回扫；结果落盘 `dormant_warehouse_audit.json`（逐候选记币源路径/静置区间/关键日动作/设施排除/证据等级/strict·expanded·excluded 裁决）。**没有该文件或仍有未裁决候选，就不允许冻结实体、不允许发布历史峰值、不允许画图 1/图 2。**严格下限与扩展上限分别按同一交易末快照重放，禁止个人峰值相加（tiering 判级确权边界节）。
- **三道互补防线硬闸（v6.8.0）**：①全体持仓波次扫描 `scripts/report/wave_scan.py`（对象＝全体历史峰值 ≥0.02% 不限清零层，四指纹合并口径与单址线脱钩）＋②资金流异常扫描 `scripts/report/flow_anomaly_scan.py`（汇集点＋分发点三口径多命中 v2——pulse 灌新仓/pulse_all 不限新老收方堵补货盲区/slow_spray 全史 ≥100 兜底；sink 判级影响取历史峰值/现仓/全史净流入/最佳合格窗的最大值）——两报告全部候选经 `adjudication_validator.py` **成员级裁决闭环**，裁决完毕前历史大户兜底桶不准关闸；③已知实体溯源闸 `entity_source_trace.py`（祖先子图正向模拟，两锚点币源构成＋direct_upstream 进货单＋FIFO/LIFO 与事件顺序双维敏感性，溯到可证来源/边界终点为止、未决显式记账），新支路补候选回裁决环。`freeze` 机器强制四重前置：严格 verify＋裁决名册绑定＋溯源内容级重查＋原始边/标签/分母/cutoff/block/manifest/data_map/算法完整绑定并以当前代码真实重放；敏感性从三策略明细机器重算，全部绑定哈希进入 revision，`check-unseal` 逐项复核——自报值一概不作数。与静置仓反扫互补：反扫从已知实体向外摸藤，波次闸对全体无藤自摸，溯源闸顺已知的藤彻查到底——单址全在雷达线下的批量协同（PYTHIA W1 波次 341 址合并峰 63.44% 两度漏检）与进货单上的裸露支路（Q1 的 20 上家 9 藤无人看）分别由①③堵死（2026-08-01 复盘）。
- 分段执行（split-run）时：前两闸由 −2 判断段承担（−1 停止线覆盖）；两扫描器跑批归 −1（wave_scan_report.json＋flow_anomaly_report.json 为 READY 必产件，缺件 generate 即拒）、候选裁决与溯源闸归 −2。

## 六入口（一行路由）

- **/token-analyze**＝完整版：上表 A0–A5 全程；A6 复盘不自动执行，仅用户要求时跑（候选教训随手记案目录 retro_notes.md）。
- **/token-easy-analysis**＝批量筛查档：`easy-workflow.md` E0–E7——引擎与复核同强度，砍完整报告，交付两件套；**绝不自动转正式**，用户人工决策后同目录衔接。
- **/token-analyze-1**＝分段·机械段（−1）：A0–A2 全部＋A3 机械子层，产交接契约后**完成即停**；执行者 GPT-5.6（codex 主轨）或 Opus（CC 备轨）——唯一权威源 `split-run.md`。
- **/token-analyze-2**＝分段·判断段（−2）：`handoff_manifest.py verify` fail-closed 通过后接 A3 判断层＋A4–A5（A6 仅用户要求时）；档位（easy|full）必选——同上 `split-run.md`。
- **/token-update**＝增量更新：`update-workflow.md` U0–U5（U6 复盘仅用户要求时）——复用旧实体表只拉增量；**判定标准一律以当前 skill 版本为准**，判级变化须区分"持仓变动 vs 标准迁移"。
- **/collect-data**＝预采集队列：`collect-workflow.md`——只采集零结论；产物以 collect_manifest 与 done.json 为准，分析会话直接复用续增量，禁止从零重采。

## 上下文预算（细则与断点恢复＝context-discipline.md）

- 峰值 <30 万 tokens（新链首战可放宽，超了如实报告）；开局只读本文件＋当链 pipeline，其余按阶段按需读。
- 大结果落盘、stdout ≤20 行摘要；大文件带 limit/offset；playbook 分册/旧报告禁整读——先路由索引再区间读。
- 机械活外包子代理卸上下文（两档模型制，唯一权威源在 context-discipline.md）；判断环节永远留主线。
- 阶段边界写 findings.md 交接包；超 30 万在下个阶段边界建议 /compact 或新会话续跑。

## 深入阅读（references/）

- `analyze-workflow.md` — 完整版 A0–A6 阶段手册（本 skill 的执行主文档）
- `context-discipline.md` — 上下文纪律与断点恢复（外包两档制唯一权威源）
- `casebook/README.md` — 判例库总纲（六字段结构与使用纪律；C 托管/E 聚类/S 供给三册）
- `analysis-playbook.md` — 链无关方法学路由索引
- `playbook-supply-recon.md` — 供给与对账（§1 分母口径/§1b 多链判据/§2 对账 gate/§8 留存质押）
- `playbook-entity-cluster-methods.md` — 标注/归因/聚类（§3 三级兜底/§4 逐笔归因/§6 聚类硬规则）
- `playbook-entity-cluster-tiering.md` — 标签体系与判级（§6a 门槛与三分类/大户排查双闸/合并指纹库）
- `playbook-entity-cluster-cost.md` — 成本工具（§6b 配价方法/双口径/退出深度比）
- `economic-control-accounting.md` — 经济控制账（三账口径/8 类设施纳入门槛/防双计/economic_control_ledger.json；6.5.0 回灌转正）
- `lp-fee-accounting.md` — LP 手续费归因（V3/V4 四层口径/逐 tick 分摊/8 项对账 gate；6.5.0 回灌转正）
- `independent-audit-protocol.md` — 既有报告净室复核协议（输入哈希冻结/claim 注册表/发布门禁 audit_release_gate.py；仅复核任务适用）
- `playbook-state-anomaly.md` — 状态评估与市场异常（§5 CEX 净流/§7 状态评估/§9 刷量/§12-14 形态库）
- `playbook-evidence-wording.md` — 复核与措辞（§10 对抗复核/§10b 第一性五问/§11 措辞纪律）
- `report-template.md` — 报告结构/标签体系/三图与流转图规范/analysis-state.json/交付 checklist
- `easy-workflow.md` — 简化筛查 E0–E7
- `update-workflow.md` — 增量更新 U0–U6
- `collect-workflow.md` — 批量预采集（队列/锁/夜间模式/key 巡检）
- `split-run.md` — 分段执行手册（−1/−2 边界、交接契约、两段开工序唯一权威源）
- `scan-schemas.md` — 机械扫描产物 schema 冻结（wave-scan/v3、flow-anomaly/v2、candidate-adjudications/v1、provenance-ledger/v2 四 schema 唯一权威字段定义＋稳定 ID/零截断/完整字段登记纪律）
- `monitoring-package.md` — 监控包分册（买入后才读）
- `research-workflows.md` — 解锁情报路线与复核 prompt 模板
- `data-pipeline-evm.md` — EVM 路由索引；分册：`data-pipeline-evm-channels.md`（通道决策树/死亡名单）、`data-pipeline-evm-sources.md`（数据面/Base/Arbitrum 专节）、`data-pipeline-evm-recon.md`（对账/DuckDB 重放引擎）
- `data-pipeline-solana.md` — Solana 路由索引；分册：`data-pipeline-solana-scan.md`（双 RPC/托管判别五步法）、`data-pipeline-solana-capture.md`（SQD/锚点法/采集加速）
- `data-pipeline-robinhood.md` — Robinhood 路由索引；分册：`data-pipeline-robinhood-channels.md`（通道决策表/脚本/修正记录）、`data-pipeline-robinhood-traps.md`（五类发射台/平台设施坑 1–17）、`data-pipeline-robinhood-methods.md`（本链绑定方法论坑）
- `data-pipeline-hyperliquid.md` / `data-pipeline-filecoin.md` — 各链管道
- `address-book.md` — 基础设施地址标签库（手工核验层；label_lookup 已自动并源）
- `labels/README.md` — 批量标签库使用篇（七链 CSV＋resolver；聚类前全量候选先过 label_lookup）
- `labels/MAINTENANCE.md` — 标签库维护篇（维护会话才读）
- `environment.md` — 本机环境坑速查
- `retrospective.md` — 复盘与教训分流决策树（**仅用户明确要求复盘时执行**；阶段 6 唯一权威源）
- `attic.md` — 三判据未过条目存档（**分析会话禁读**——对工作流程等于不存在；仅存留审计/整编会话可动）
