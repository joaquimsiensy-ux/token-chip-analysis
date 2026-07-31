---
name: token-chip-analysis
description: 对任意链上代币（EVM/Solana/Hyperliquid/Filecoin 及新链）做机构级庄家链上行为分析与既有报告独立复核——全量数据采集重放、庄级实体识别与标签划分（项目方/大庄/小庄/离场庄/刷量地址）、各阵营持仓演变、重点实体流转路径图、V3/V4 流动性与庄家 LP 手续费归因、对抗复核、自包含 HTML 报告（用户确认买入后可补生成观察哨与监控 JSON 附录）。当用户问"某代币的筹码分析/筹码结构/庄家行为分析"、"复核/审计已有筹码报告"、"有几个庄/庄家什么类型"、"庄家/项目方/做市商在吸筹还是砸盘"、"有没有关联地址/老鼠仓/单一实体控盘"、"庄家是不是跑了/弃盘了"、"该不该买/该不该卖/解锁抛压大不大"、"看看某代币的链上持仓/大户动向"、"庄家做 LP 赚了多少/LP 手续费怎么计算"，或提到 holder analysis、鲸鱼追踪、代币尽调时使用。与 gmgn-token 的区别：gmgn-token 是快速单项查询；本 skill 是数小时深度分析工程。只查价格/K线/热榜/新币列表不要用本 skill。
---

# 代币筹码分析（Token Chip Analysis）

对标的回答三个固定命题（v5.0 三问框架）：**①有几个庄**（按标签体系计数：项目方/大庄/小庄/离场庄/刷量地址）**②每个庄什么类型**（单地址明牌/多地址互转·gas同源/伪装分散·指纹一致）**③各阵营全历史持仓占比如何演变**（占总供应，锁仓/销毁单列；建仓后动没动、拉升期有没有出货）。**开放条款：三问是下限不是上限**——任何显著结构性异常必须单列章节，TL;DR 设"本次特有发现"（确无发现明写"无"）。交付自包含 HTML 报告；**监控包默认不生成，用户确认买入后补**。核心信条：**不对账的分析是猜测，未经反驳的结论是自嗨。**

## Codex 运行适配（本副本独有节；解同步冲突时整节保留）

- **第 0 步（硬性前置）**：接到任何筹码分析任务，动手前先跑 `bash "${CODEX_HOME:-$HOME/.codex}/skills/token-chip-analysis/sync-from-cc.sh"`——退出码 0 正常开工；1＝先提交本地改动再重跑；2＝**停下解冲突再开工**（规矩见 `SYNC.md`）；3＝合并后测试没过，必须停，`git reset --hard HEAD~1` 回退后报告用户。CC 侧迭代含引擎级缺陷修复，用旧版跑出的结论可能整篇是错的，而同步只要几十秒。
- **worktree 与分享包**：维护者本机副本是 CC 版 skill 仓库的 git worktree（`codex` 分支，共用同一 `.git`）；独立分享 ZIP 不携带 `.git`，同步脚本识别为固定快照并返回 0，不把缺维护仓库误报为故障；分享包不自动获得后续更新，需重新分发。
- **G1 路径/工具/模型映射（通则）**：文中 `~/.claude/skills/token-chip-analysis` 一律读作 `${CODEX_HOME:-$HOME/.codex}/skills/token-chip-analysis`；`AskUserQuestion`＝确有关键决策点时向用户提一个简短问题；`WebSearch`/`WebFetch`＝当前可用的联网检索/浏览器/fetch；`Agent`/`Workflow`＝Codex 子代理（只交具体、独立、可并行的任务）；`Monitor`＝当前 wait/monitor 机制；Claude 的 `sonnet`/`opus` 是历史别名不得原样使用——机械任务用当前可用的均衡/低成本代理，判断任务继承当前模型，无模型覆盖能力时不臆造别名。`~/.claude/workflows/*.js` 不是 Codex 可执行入口，复用其中 prompt/schema 时读取内容改写为 Codex 子任务。
- **G2 禁自审（c1.1.0 条款，通则）**：下发文档中一切"外部异构怀疑者/codex 外审/GPT-5.6 复核"步骤在本副本一律**不适用**——禁止执行 `codex exec`、另开 Codex CLI 或调用同一 Codex 模型充当"外部独立复核"；同体系多代理只能称"内部对抗性自检"，用于降低遗漏，不能宣称外部独立性。真正外审须由用户把冻结输入交给不同模型或人工审计方。
- **G3 独有资产（永不随同步删除）**：`agents/openai.yaml`、`SYNC.md`、`CHANGELOG-codex.md`。原独有的方法学资产（economic-control-accounting / lp-fee-accounting / independent-audit-protocol 三分册＋audit_release_gate.py 及其测试、tiering 判级确权边界节）已于 6.5.0 经用户裁决回灌 main 转正，此后为两边共有、main 权威、同步单向下发——本副本不再单独维护这些文件。完整版交付前经济控制账与发布门禁照常执行（report-template 交付 checklist 4c/4d，main 正文）。
- **G4 硬闸（6.5.0 起与 main"实体冻结前双硬闸"节同文，本副本载体）·控盘看最终经济控制，不看币停在哪个地址**：回答"庄控制多少"时主口径必须是实体的**可证经济控制量**（钱包自持＋在 LP/CEX 子账户/桥/质押锁仓/vault/托管等设施中可证明赎回权或受益权的等价权益），账本落盘 `economic_control_ledger.json` 并同源驱动 TL;DR/判级/实体表/图 2。三账分离：成员表答"哪些地址受控"、位置账答"币在哪"、经济控制账答"受益权归谁"；**公共设施不进永久成员表**，但可归属份额必须穿透回实体；设施总余额不得整池归庄，归属不清单列未决不得猜。细则唯一权威源＝`economic-control-accounting.md`。
- **G5 硬闸（6.5.0 起与 main 同文，本副本载体）·历史静置仓反向扫描硬闸**：初步聚类后、实体名单冻结与峰值判级前，必须从历史峰值榜/已归零回落仓/长期静置仓/关键日激活仓反向追查平行库存与尾仓，并从核心网络向上游币源与边界外一圈回扫；结果落盘 `dormant_warehouse_audit.json`（逐候选记币源路径/静置区间/关键日动作/设施排除/证据等级/strict·expanded·excluded 裁决）。**没有该文件或仍有未裁决候选，就不允许冻结实体、不允许发布历史峰值、不允许画图 1/图 2。**严格下限与扩展上限分别按同一交易末快照重放，禁止个人峰值相加（tiering 判级确权边界节）。
- **G6 split-run −1 执行条款（c2.1.0；本副本＝−1 主轨执行者）**：用户说"对 <币> 跑 −1 / 机械段 / token-analyze-1"即触发，唯一权威源＝`references/split-run.md` §1（范围）＋§2（交接契约），逐条照做：①开工探针（split-run §1.1）不过不启动全量采集，先抢案级 `.stage1.lock`（§1.2），抢不到即退出报告在跑者；②范围＝A0–A2 全部＋A3 机械子层（§1.3），E0b 黑箱关卡维持点名制；③**停止线（§1.4，越线＝流程事故）**：聚类合并裁决/实体冻结/判级/casebook 过闸/大户报警深挖/正式 entity_identity_gate/状态评估定性/A4/A5 一律禁做——G4/G5 硬闸属实体冻结环节，在 −1 模式下**不执行、由 −2 承担**（G6 停止线优先于 G4/G5 的"必须做"，二者不矛盾：G4/G5 管"冻结前必须做完"，−1 根本不冻结）；初步定性只准写 `sealed/stage1_hypotheses.sealed.md`；④未档异常→停下写 blocker 进 anomalies.json，禁自创解法；⑤全程 `export CHIP_BLIND_SERIAL=1`，每步跑 `handoff_manifest.py receipt` 记收据；⑥收工跑 `handoff_manifest.py generate`（状态如实报 READY/PARTIAL/BLOCKED/BLOCKED_E0B），打印交接摘要并提示用户去 CC 开 Fable 会话跑 /token-analyze-2，**完成即停不多做一步**；⑦`audit_input_manifest` 等三账审计件仍是独立审计协议（G3）内部件，与 handoff 契约互不替代；⑧本条款与 G2 兼容：−1 模式产物之后由 CC 侧 −2 消费，A4 外部异构复核按 split-run §3.3 收紧条款在 CC 侧进行，本副本不自调任何复核。
- **API key**：以 `~/.claude/api-keys.md` 为唯一登记源（复用其指向的 `~/.config/*` 凭据文件）；不复制登记文件，不把 key 写进 skill 目录/日志/报告/命令行参数；案目录临时配置权限 600。
- **迭代规则**：codex 侧版本号一律 `c` 前缀（三维含义同 CC：主=架构级/次=复盘迭代/修=文档小修）；条目只写 `CHANGELOG-codex.md`；`CHANGELOG.md` 由 CC 单向下发一字不改；改完立刻 commit（run_all 全过才提交，别攒着挡同步）。

## 铁律（7 条封顶：新进＝旧出或代码化。任何阶段不可越过）

1. **结论独立性**：只沉淀方法，禁止复用任何历史标的的结论/数字/判定与"上次也是这样"式类比；同会话不连做两币。判例库是方法级失败模式，不是结论先验（casebook/README.md）。
2. **对账关卡**：阶段 2 四查（余额对账/供给闭合/供给真值闸/时间抽查）不过关不进分析。
3. **证据强度纪律**：证据强度用自然语言分级（链上铁证/高度疑似/疑似/未能确证）；意图不可区分时并列写（report-template「证据强度呈现」）。
4. **对抗复核必做**：历次执行每次都实质改写结论，投入产出比最高的环节，不可跳过（本副本按 G2 通则执行内部对抗性自检）。
5. **数据源取用**：key 从 `~/.claude/api-keys.md` 登记文件直接取用；运行时只写工作目录 config.json，永不写死进 skill 目录。
6. **成本纪律**：成本目标永远让位于准确性——为省 token 砍复核路数/数据源属于违反铁律；上下文纪律见 context-discipline.md。
7. **交付边界**：输出结构事实与风险判定，买卖裁决由用户做出。

## 全流程路由（完整版；每阶段细节的唯一权威源＝`analyze-workflow.md` A0–A6）

| 阶段 | 干什么 | 必读 | 硬闸（exit 语义） | 落盘产物 |
|---|---|---|---|---|
| A0 画像与路由 | 合约核定/多链硬关卡/分母口径/链路由 | A0＋当链 pipeline；多链读 casebook S 册 | accounting_gate：0 放行/2 硬停人工定制/1 修通道重跑禁当放行 | 计划、accounting_mode.json |
| A1 并行采集 | 全量数据＋标签＋价格（后台先行） | A1＋当链 pipeline | — | data/、collect_manifest |
| A2 对账关卡 | 四查：余额/供给闭合/**供给真值闸**/时间抽查 | A2＋当链 recon 分册 | 四查不过不进分析；supply_truth_gate：0 PASS/2 FAIL 余额改实时直查/1 修通道重跑 | supply_truth.json、anchor_plan.json |
| A3 分析 | 标注→归因→聚类→判级→大户双闸→演变重放 | A3＋**casebook C/E 册全过一遍**＋playbook 按需 | entity_identity_gate→build_html G8：flag 未解决报告物理编不出 | findings.md、identity_gate.json |
| A4 对抗复核 | 扰动前置→揭盲→N 路怀疑者→三档裁决 | A4＋evidence-wording §10；casebook 三册作备择弹药 | 三档必须实际核查，"理论上可能"不算推翻 | 复核修正记录 |
| A5 报告 | 三标准图＋流转图＋HTML＋质检 | A5＋report-template | build_html 退出码 0（缺图/G8 拒交付） | 报告.html、analysis-state.json |
| A6 复盘 | **仅用户明确要求时执行，不自动触发**：教训分流入库（分流决策树） | retrospective.md | run_all 全 PASS＋git commit | CHANGELOG-codex |

## 六入口（一行路由）

- **/token-analyze**＝完整版：上表 A0–A5 全程；A6 复盘不自动执行，仅用户要求时跑（候选教训随手记案目录 retro_notes.md）；本副本另执行经济控制账与发布门禁（见 G3）。
- **/token-easy-analysis**＝批量筛查档：`easy-workflow.md` E0–E7——引擎与复核同强度，砍完整报告，交付两件套；**绝不自动转正式**，用户人工决策后同目录衔接。
- **/token-analyze-1**＝分段·机械段（−1）：A0–A2 全部＋A3 机械子层，产交接契约后**完成即停**；**本副本＝−1 主轨执行者**（执行者 GPT-5.6 codex 主轨 / Opus CC 备轨）——唯一权威源 `split-run.md`。
- **/token-analyze-2**＝分段·判断段（−2）：`handoff_manifest.py verify` fail-closed 通过后接 A3 判断层＋A4–A5（A6 仅用户要求时），档位（easy|full）必选——同上 `split-run.md`；主力判断模型在 CC 侧执行，不属本副本职责，−1 收工时提示用户去 CC 开 −2 会话。
- **/token-update**＝增量更新：`update-workflow.md` U0–U5（U6 复盘仅用户要求时）——复用旧实体表只拉增量；**判定标准一律以当前 skill 版本为准**，判级变化须区分"持仓变动 vs 标准迁移"。
- **/collect-data**＝预采集队列：`collect-workflow.md`——只采集零结论；产物以 collect_manifest 与 done.json 为准，分析会话直接复用续增量，禁止从零重采。

## 上下文预算（细则与断点恢复＝context-discipline.md）

- 峰值 <30 万 tokens（新链首战可放宽，超了如实报告）；开局只读本文件＋当链 pipeline，其余按阶段按需读。
- 大结果落盘、stdout ≤20 行摘要；大文件带 limit/offset；playbook 分册/旧报告禁整读——先路由索引再区间读。
- 机械活外包子代理卸上下文（两档模型制按 G1 映射执行）；判断环节永远留主线。
- 阶段边界写 findings.md 交接包；超 30 万在下个阶段边界建议压缩上下文或新会话续跑。

## 深入阅读（references/）

- `analyze-workflow.md` — 完整版 A0–A6 阶段手册（本 skill 的执行主文档）
- `context-discipline.md` — 上下文纪律与断点恢复（外包两档制唯一权威源）
- `casebook/README.md` — 判例库总纲（六字段结构与使用纪律；C 托管/E 聚类/S 供给三册）
- `analysis-playbook.md` — 链无关方法学路由索引
- `playbook-supply-recon.md` — 供给与对账（§1 分母口径/§1b 多链判据/§2 对账 gate/§8 留存质押）
- `playbook-entity-cluster-methods.md` — 标注/归因/聚类（§3 三级兜底/§4 逐笔归因/§6 聚类硬规则）
- `playbook-entity-cluster-tiering.md` — 标签体系与判级（§6a 门槛与三分类/大户排查双闸/合并指纹库；尾部 Codex 复盘判据节）
- `playbook-entity-cluster-cost.md` — 成本工具（§6b 配价方法/双口径/退出深度比）
- `playbook-state-anomaly.md` — 状态评估与市场异常（§5 CEX 净流/§7 状态评估/§9 刷量/§12-14 形态库）
- `playbook-evidence-wording.md` — 复核与措辞（§10 对抗复核/§10b 第一性五问/§11 措辞纪律）
- `report-template.md` — 报告结构/标签体系/三图与流转图规范/analysis-state.json/交付 checklist（尾部 Codex 版补充义务节）
- `easy-workflow.md` — 简化筛查 E0–E7
- `update-workflow.md` — 增量更新 U0–U6
- `collect-workflow.md` — 批量预采集（队列/锁/夜间模式/key 巡检）
- `split-run.md` — 分段执行手册（−1/−2 边界、交接契约、两段开工序唯一权威源）
- `monitoring-package.md` — 监控包分册（买入后才读）
- `research-workflows.md` — 解锁情报路线与复核 prompt 模板（按 G1/G2 通则映射后使用）
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
- `economic-control-accounting.md` — 经济控制账（Codex 独有：三账口径/防双计/economic_control_ledger.json）
- `lp-fee-accounting.md` — LP 手续费归因（Codex 独有：V3/V4 本金与费拆分）
- `independent-audit-protocol.md` — 独立审计协议（Codex 独有：三账 schema/输入哈希冻结/发布门禁）
