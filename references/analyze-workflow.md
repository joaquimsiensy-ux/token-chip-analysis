# 完整版分析手册（/token-analyze，A0–A6）

> v6.0.0 承接旧 SKILL.md 全部阶段细节（规则语义零变更）。本手册是各阶段执行细节的唯一权威源；判定类失败模式在 `casebook/`（只指不抄）；上下文与外包纪律在 `context-discipline.md`；按需研究与异构复核在 `research-workflows.md`；链专属操作在各 data-pipeline 文档。

## 通用执行纪律（全阶段生效）

- 优先跑 `scripts/` 固化脚本，禁止现场重写已有能力的脚本；不满足需求先改参数再改脚本，改动记入 A6。
- **关键字符串（地址/哈希）一律从落盘文件取**，从打印输出复制截断补全＝编造。
- 脚本产出判定以代码写入语句＋文件时间戳为准，stdout 叙述不可信（environment.md「stdout 与实际行为不一致」条）。
- 免费层限流当场翻车：限速常数实测收敛；退避＋断点续传标配；卡点超 1–2h 摆路径给用户选，不单通道死等。
- 本机环境坑（SSL/字体/shell/沙箱杀进程等）开工 preflight 只扫 `environment.md` 坑速查（扫≠整读）；运行异常或涉及 OS/Python/字体/SSL/shell 时再深读对应节。

## 入口分流（唯一权威）

- 用户以自然语言要求**复核、审计或核验既有筹码报告/第三方报告/旧版分析**时，进入
  `independent-audit-protocol.md` 净室复核轨；不新增 slash command。旧报告只拆成
  `claim_registry.json` 待审命题，正文、实体表、标签、衍生 JSON 与图表均不作证据输入。
- 净室轨与新分析共用 A0–A2 骨架：A0 核定标的、链范围、分母和记账模型，A1 独立采集原始数据
  并冻结 `audit_input_manifest.json`，A2 完成四查对账。A3 起以净室协议重建实体、三账、历史序列和
  命题裁决；A4 使用 `--workflow-type independent-audit`，A5 仅以
  `build_html.py --mode analysis-audit` 编译并强制 `audit_release_gate --profile independent-audit`。
- 不满足上述触发条件的新币/新分析走标准 A0–A5、`--workflow-type new-analysis` 与
  `build_html.py --mode analysis-new`。两轨不得互相猜 profile 或共用被审报告的衍生结论。

## A0 标的画像与链路由

产出计划落盘，**用户决策点前置**：口径选择/新数据源注册/key 索取这类需要用户拍板的事项，在计划阶段用 AskUserQuestion 给选项一次问清，不在分析中途零散打断。

先核定：合约/mint 地址（多源交叉，确认用户持有的到底是哪个）、部署在哪几条链、**总量与流通量多口径分开标注**（链上实查/第三方流通/名义已解锁——口径混淆是历次实战最高频的结论级错误源，见 casebook S 册）、DEX 真实流动性（<$50k 则定价权在 CEX，分析重心＝托管流＋金库＋充提）。

**多链代币硬关卡（不过关不开工）**："部署在哪几条链"不是登记项，是分流关卡。CoinGecko `coins/{id}` platforms 字段＋GMGN/Dexscreener＋官方文档多源核查；凡部署 ≥2 条链，必须先做**链分布盘点**——各链 RPC 实查该链供给（桥接分支按 mint−burn 口径；
  **镜像关系先做锁仓适配器配平**，见 casebook S-02），产出链分布表（链/合约地址/该链供给及占全局总供应%/主 DEX 流动性/预估转账量级与采集耗时），连成本预估一起用 AskUserQuestion 让用户选定分析范围（推荐项＝供给占比最大的主链；选项：仅主链/主链＋指定分支/全部链）。
  **禁止拿到地址就按其所在链直接开工**——用户给的地址可能只是小分支链（VIRTUAL 案范围性返工，07-16）。占全局 <5% 的分支默认不单独立项（用户点名除外）；选多链时各链分别过 A2 对账再合并口径。报告 TL;DR 首行必须声明分析范围（覆盖哪几条链、合计占全局总供应%），规范见 report-template.md。

另核定两件事：①**标的是否带解锁表/vesting**（tokenomist/dropstab 有记录，或链上有锁仓合约/多签托管）——有则问 3 必须包含"未来 6–12 个月解锁日程与量级"小节（要求见 report-template.md）；②**开工版本自查**：读 `VERSION` 文件并在计划里注明，交付前重读一次——版本号变了说明 skill 被并行会话更新过，向用户提示框架可能已迭代。

**链路由表**：

| 标的形态 | 读哪份 pipeline / 跑哪套脚本 |
|---|---|
| 0x 地址，Ethereum/BSC/Base（正式） | 进入 `data-pipeline-evm.md` 通道决策树＋ `scripts/evm/` |
| 0x 地址，Arbitrum（探索） | 可跑 EVM 采集、对账与身份快照；标签主表缺失，禁止 A4/A5 seal 与正式 analysis 编译 |
| base58 mint | `data-pipeline-solana.md`（双 RPC 按方法路由见其分册 §0a） |
| 0x 地址，Robinhood Chain（chainid 4663） | `data-pipeline-robinhood.md` ＋ `scripts/robinhood/` |
| 跨链部署（OFT/CCIP 等） | 先过多链硬关卡选定范围 → 各链按其 pipeline 采集＋跨链 mint/burn 配平；桥接分支链范式见 playbook §6a |
| 全新链 | 新链 SOP：先实测数据面并实现采集 receipt、四查、标签 resolver 与 G8 chain 适配；这些正式门禁未齐前只能交付明确降级的探索结果，不得编译正式 analysis |

**通道实测探路**：写任何采集脚本前，先用 1–2 分钟小请求逐个实测候选数据源（可用性/返回结构/分页/上限/限速）；拿到任何新 key 先做 1 分钟能力探测再承诺方案；禁止基于文档想象设计方案。

**记账模型准入 gate（链路由定型后、采集开工前必跑）**：fee-on-transfer/rebase/Token-2022 扩展会让"Transfer 流水重建余额"整体算错且供给闭合发现不了（模型错但自洽）。一条命令 1 分钟出裁决，产物 `accounting_mode.json` 落工作目录——EVM `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --out accounting_mode.json`（eth 侧 --rpc 传 Alchemy 检测更强）；Solana `python3 scripts/solana/accounting_gate_sol.py --mint <mint> --out accounting_mode.json`。**exit 0（standard/WARN 级）＝放行**，WARN 逐条抄进报告数据底座节；**exit 2（BLOCK）＝硬停**——向用户报模式与证据，要继续必须人工定制记账模型，禁止套标准管线；**exit 1（检测自身失败）＝修通道重跑，禁止当 standard 放行**。检测原理与判定表见脚本头注。

## A1 并行采集（一次性全部启动）

三路并行：①**全量链上数据**（最耗时最先启动，后台跑；采集脚本标配＝限速可调/退避重试/断点续传/失败段补扫/冒烟小样本先行）②地址标签与安全面（GMGN、浏览器标签页）③价格（CoinGecko/binance.vision）。**vesting 标的加一路解锁情报轻量 agent**（tokenomist/dropstab 多源交叉，见 research-workflows §1 路线 1——下一次大解锁的时间和量是问 3 解锁小节的核心输入）。（v5.0 问 4 删除后背景调研整路退役；research-workflows §1 其余路线按需作分析工具，不再默认启动。）

长任务运维：最长任务最先启动、等待期填满下游脚本编写、零进展要告警、预估偏差超 2 倍主动汇报（抽样外推报保守上限）、废弃通道同步停掉观察哨。

**既有采集产物复用**：开工先查工作目录是否已有采集产物（EVM＝`data/v2/run_*/done.json`，Solana＝`data/soltx-*.jsonl.gz`＋meta）——有则**直接复用并断点续拉增量到最新**（底层采集器天然幂等），禁止无视既有产物从零重采；完整性以当链 `done.json`、`collection_manifest.json`/receipt 为准，链内 manifest/receipt 证明单链数据范围。`done_with_gaps` 必须先补齐缺口再进对账。

## A2 对账关卡（硬性，四查全过才进分析）

1. **余额对账**：重建结果 vs 独立数据源精确对表（形态见各链 pipeline recon 分册）。
2. **供给闭合**：总量恒等式/mint−burn 配平（内部自洽检验）。
3. **供给真值闸（v6 新增，重放收尾必跑）**：`python3 scripts/lib/supply_truth_gate.py --chain <链> --token 0x…|--mint <mint> --replay-stats <replay_stats.json> --out supply_truth.json`——重放净供给对链上实查 totalSupply()，治静默改账盲区（老合约 migrate() 改账不发事件、全部内部自检 PASS 而余额虚高，见 casebook S-01）。**exit 0 PASS／exit 2 FAIL＝该币余额禁用重放结果改 Multicall3/RPC 实时直查（地址全集与转账历史仍可用重放，重放余额仅作 ≥阈值超集筛选）／exit 1 检测自身失败修通道重跑，禁当 PASS**。
4. **时间抽查**：EVM 走分层计划制——先跑 `scripts/lib/anchor_plan.py` 出抽样计划（3 时段×3 余额档矩阵点＋四类强制覆盖点：全史最大单笔/最大单日净变动/数据源交界块/门槛±10% 边缘地址），再跑 `scripts/lib/time_spotcheck.py` 对独立第二源逐锚点核对（balance 型 archive balanceOf 直查＋tx 型收据五元组，产 `time_spotcheck.json`，verdict=PASS 才过；第二源分层选型与"全史双源重拉仅例外、做前 pilot 报 ETA"条款见 evm-recon §13——**默认锚点级即闭环，禁止把全史第二源重拉当标准动作**，APU 案 103 分钟冗余教训）；纯随机锚点容易全抽在平静期、高风险位置反而漏掉。Solana 案走 anchor_sampler.py。注意本查测的是数据完备性与第二源一致性，不替代供给闭合对 mint/burn 口径的把关。

对不上＝数据有洞＝回去补，不许"差不多就行"。

## A3 分析

**惯犯层盲化（A2–A3 全程）**：开工即 `export CHIP_BLIND_SERIAL=1`——标签查询的 serial-actor（惯犯）命中不进任何主输出、完整详情自动封存案目录 `sealed_serial_hits.jsonl`（label_lookup/analyze_holdings/replay_edges/build_evolution 四出口已接线；设施类标签照常输出）。动机：提前看到"这是 XX 案惯犯"会造成合并判定的先入之见；实体冻结后在 A4 揭盲作定向复核线索。

方法学全部在 `analysis-playbook.md` 路由索引（先定位节再区间读分册）。先完成机械准备：
**地址身份标注**（官方标签→外部证据→行为特征三级兜底，playbook §3）→
**金库与核心实体逐笔归因**（§4）；分段模式直接验收 −1 的同源产物。其后判断主序与
`split-run.md` §3.2 一致，按下列顺序执行：

1. **判例库过闸（实体表冻结前必做）**：把 `casebook/cex-custody.md` 与
   `casebook/entity-clustering.md` 全册触发现象过一遍，命中的逐条做"必做区分检验"。
2. **聚类合并裁决→临时实体**：多证据边＋中间节点三段式检验（§6）；合并只认专属性证据，
   通用实现/通用服务共用不算（见 casebook E-01）。本步只落临时实体，不得提前冻结。
3. **ET-2 无下限成员完整性扫描**：对每个临时实体做不设持仓下限的成员完整性扫描。
   ET 是判级筛查层，不与 EF-1～EF-3 顶层冻结门禁混称。
4. **EF-3A 全体持仓波次扫描／EF-3B 资金流异常扫描**：名册定稿前分别运行
   `wave_scan.py` 与 `flow_anomaly_scan.py`，产 `wave_scan_report.json`（wave-scan/v3）和
   `flow_anomaly_report.json`（flow-anomaly/v2）。分段执行时 EF-3A/B 跑批归 −1。
5. **当前持仓分布初判**：仅在 EF-3A 和 EF-3B 之后运行
   `holder_distribution_scan.py --stage initial`。产物是 `distribution_scan.json` 和
   `charts/distribution_stage1.png`。JSON 进入 READY `handoff/v3`，verify 会重新派生五桶并重算；
   工作图不进 seal，也不进报告。initial 只绑定快照、来源收据、排除派生链、算法和阈值，
   不绑定 handoff manifest。
6. **EF-3C 候选裁决与实体溯源**：两扫描器全部候选经 `adjudication_validator.py`
   成员级裁决，再对临时实体表跑 `entity_source_trace.py`；新支路回裁决环，EF-3C 归 −2。
7. **EF-1／EF-2 门禁**：临时实体成形后、freeze 前落
   `economic_control_ledger.json` 与 `dormant_warehouse_audit.json`；EF-1 核清最终经济控制，
   EF-2 完成历史静置仓反向扫描。任一未闭合不得 freeze。
8. **实体冻结**：`handoff_manifest.py freeze` 固定校验 EF-3C-P1 严格 verify、P2 裁决名册绑定、
   P3 溯源内容重查、P4 原始边/标签/分母/cutoff/block/manifest/data_map/算法绑定后真实重放；
   存在 `distribution_adjudications.json` 时同时绑定当前分布裁决。
9. **实体身份硬闸（G8）**：从冻结实体表生成 state 输入，再由生产 emitter 生成
   `identity-holder-snapshot/v2`。EVM 五链（eth/base/bsc/arbitrum/robinhood）均可生成
   身份快照 receipt；其中 arbitrum 仅供探索档与存量数据重放，不构成正式发布资格。EVM 用
   `identity_snapshot_receipt.py --chain ... --snapshot balances_final.json --source-receipt channels_preflight.json --replay-stats replay_stats.json`，
   Solana 用同工具 `--chain sol --snapshot holders_owners.json --source-receipt holders_snapshot_meta.json`。
   EVM 的 `channels_preflight.json` 必须由当前 `channels_preflight.py` 生成并绑定已验 collector receipt/segment chain 与确切 CSV/Parquet `inputs`，`replay_stats.json` 必须由所选当前 replay 引擎生成并绑定同一 inputs、preflight 与 `balances_final.json`；Solana meta 必须由当前 `scan_token_accounts.py` 生成并绑定 supply receipt、每个 GPA raw/meta 与 account/owner 输出；emitter 和 G8 check 会用 scanner 的同一套 base64→
   owner/amount＋跨 scan pubkey 去重函数离线重解析全部 raw GPA，逐条比对 `holders_accounts.json`/`holders_owners.json`，并重读 supply receipt 的 amount 后闭合总量。emitter 和 G8 check 都重验上述实物链，孤立手写或只抄 producer 哈希一律拒绝。再跑 `entity_identity_gate.py --state ... --snapshot-receipt ... --total-supply-raw ...`，产 `identity_gate_v3`。
   存量没有 `producer/inputs/outputs` 的 EVM preflight/stats 必须重跑对应 replay 引擎（其会重跑 preflight 与完整重放），Solana 旧 meta 必须重跑 `scan_token_accounts.py` 重新扫描，然后再跑 emitter；不得手工补字段或用测试 fixture 迁移。闸覆盖每个实体地址＋≥1% 总供应单址；所有无标签实体成员一律 `BIG_UNLABELED`（Solana off-curve 则 `PDA_UNRESOLVED`）。
   CLI `--check` 与 build_html G8 共用 validator，重验全部来源绑定。
10. **判级（含 ET-1）**：庄级实体识别、标签划分与类型三分类的门槛数值与细则唯一权威源＝
    playbook-entity-cluster-tiering §6a（本处不设数值副本防漂移）。ET-1 对其他大户线逐个过
    标签库/惯犯库/指纹/funder 批量排查，报警才人工深挖；项目方、大庄/小庄、离场庄、
    刷量地址与发射窗协同实体均按该节判级，合并口径含全部疑似关联地址。
11. **阵营演变重放**：按已冻结且过 G8/判级的名册，重放已声明范围内各阵营占比演变序列；
    分母＝当期净供应序列，**逐时点 assert Σ阵营＝100%±容差**，改过名册跑反向断言
    （casebook S-03）。不得在 EF-3 候选闭环前先跑本步。
12. **A3 落盘**：生成 `findings.md`、`facts.json`、`analysis-state.json`、`identity_gate.json`；
    完成庄家当前状态评估（§7）与质押/留存修正（§8）。建仓成本仅按需算（§6b 降为工具）；
    CEX 净流×价格作为演变解读工具按需用（防内部调仓伪影，§5）。

**覆盖真空声明（用户 2026-08-01 确认接受；2026-08-02 flow v2 补缝后边界更新）**：v6.8.0 删除 camp_jump_audit.py（阵营序列骤变归因闸）后，系统不再有"从最终阵营序列反向发现未解释大变化"的输出侧报警器——wave/flow 覆盖不了标签重分类、分母变化、慢速迁移类异常；无法归因的骤变按判断层义务写进报告"局限性"，本轮不做替代闸（不承诺永久）。flow 分发点侧 v2 补缝后仍不可见（真空收窄未消除）：收方 20~99 且任何 14 日窗不达双线的慢速分发／<20 收方拆分／全史流出 <2%／一实体轮换多址各 <2%（entity-file 只抵消内部边不聚合外发）／多跳二级分发。仅存的输出侧轻量信号＝阵营重放产出时标记"单日阵营变动 ≥10pp"的日子，作为峰值逐笔触发日之一（无归因义务，见 tiering"峰值判级口径"条，2026-08-02）。

数据先验结构再分析（榜单唯一性断言、多档抽查），批量脚本先 2 个样本验证编解码再放量、绝不吞异常。**份额阈值一律整数运算**（`TOTAL//100`，浮点比较会把"恰好整数枚"大户判漏——那本身还是橱窗仓指纹，漏它双重损失；来源：meow 案 2026-07-15）。

## A4 对抗复核（必做）

**A4→A5 顺序硬闸（6.7.0，2026-08-01 定）：本阶段全部裁决落定并 `a4_gate.py finalize` 封口前，禁止进入 A5——不画报告图、不写 `报告.md`、不编 HTML。复核对象＝findings.md/结论清单＋落盘数据文件，不是排版后的报告。**（历史核查：16 个时间戳可判定案 12 案图表/报告先于复核落盘，7 案因翻案实际返工，另 5 案结论翻了图没跟着改成错误残留。翻案率极高是本环节的固有属性，提前做 A5＝无用功＋上下文污染。）

执行序（细则与 prompt 骨架的唯一权威源＝playbook-evidence-wording §10＋research-workflows §2，此处只列主干）：

1. **claim 注册表登记**：`python3 scripts/report/a4_gate.py register --case-dir . --claims-file <claims.json>`——把 A3 全部核心结论写成稳定 id 的 claims 清单（与 adversarial-review skill 的 args.claims 及 split-run §3.3 外部异构路输入同构），产 `a4_claims.json`。initial scan 中每个异常簇必须登记对应 `dist-<cluster_id>` claim；漏登或多登时 finalize 双向对账拒绝。
2. **扰动敏感度前置**（EVM 案，`cluster_sensitivity.py --dir <案目录>`，sensitivity_report.md 作复核输入；FRAGILE/STABLE 字样只进复核材料禁进报告正文）。
3. **惯犯揭盲**（实体冻结后 `label_lookup.py --unseal` 取封存命中，与实体划分互证/互斥）。
4. 本地反例自查脚本前置。
5. **N 路怀疑者 agent**＋1 完整性批评角色查 findings/结论清单缺口（必查全史极值清单）＋1 路**外部异构怀疑者**（codex/GPT 单进程横扫全部结论）——重算义务、备择解释与分组细则按 §10＋research-workflows §二执行，不在此复述。
6. 判定三档 CONFIRMED/WEAKENED/REFUTED（**必须实际核查，"理论上可能"不算推翻**）→ 修订顺序先修数据管线再修文案 → 修正记录印进报告附录。
7. **封口收尾**：A3 已先落 `findings.md`、`facts.json`、`analysis-state.json`、`identity_gate.json`。运行 `a4_gate.py finalize ... --workflow-type new-analysis|independent-audit --seal-files findings.md,analysis-state.json,facts.json,identity_gate.json`，产 `a4-seal/v4`。新分析会重验当前分布 claim source，并要求 `dist-*` claims 与异常簇严格相等。每次重封都追加 revision 和 previous seal 哈希。净室复核继续机器对账两套 claim registry，但 v1 分布闸不挂 analysis-audit。路径经 containment 校验，`charts/final/` 为空且 exit 0 才准进入终判环。

## A4.5 当前持仓分布终判环

A4 finalize 后，用同一 cutoff 快照运行 `holder_distribution_scan.py --stage final --round N`。final 绑定 READY handoff manifest、身份快照收据、当前 A4 seal、当前 entity freeze revision、三账、initial scan 和上一轮 final scan。每轮 JSON 和工作图写入 `dist_rounds/round_N/`，不得写入 `charts/final/`。

如果 final 出现当前 A4 seal 未覆盖的新异常簇，立即回流 A4 登记和复核。已经覆盖的异常簇运行 `distribution_explanation_check.py`。位置、成员、数量、证据和传播五项全部通过才记 `EXPLAINED`。未通过时，默认逐成员生成 `distribution_adjudications.json`；只有书面排除成员路径后才能使用 `pattern_resolutions.json`。两条路径的结论都必须回流 A4 重封，再开始新一轮 final。

`distribution_rounds.json` 按轮追加并绑定上一条记录哈希。两轮仍未终态时让用户选择第三轮或标准 waiver。只有 `NORMAL`、完整 `LOW_SAMPLE`、`EXPLAINED` 或带完整收据的 `WAIVED` 能成为终态。终态才物化 `charts/final/holder_distribution_current.png`。删除台账后从非首轮继续、终态后追加或同时存在多个 terminal 都会被拒绝。

## A5 报告

**进入本阶段的前置＝`a4_seal.json` 已由 A4 第 7 步产出，分布轮次已到唯一终态，终版分布图已物化。** 报告本体先写 `报告.md`＋`charts/final/*.png`，再运行 `a5_report_seal.py --case-dir . --report 报告.md --a4-seal a4_seal.json --out a5_report_seal.json`，产 `a5-report-seal/v2`。A5 seal 会绑定 rounds 台账、terminal final scan、解释或 waiver 收据和唯一分布图。build_html 的 G11 会重新计算这些绑定。**报告图一律输出到 `charts/final/`**。复核过程草稿图放 charts/ 根或 `dist_rounds/`，不进报告。**三张标准图必配**（阵营占比演变/庄级实体 vs 价格/价格与关键事件），直接调 `scripts/report/standard_charts.py` 三个函数。持仓分布终版图另放第二章，不作为第二张分布图重复绘制。**每个当前持仓 ≥20% 总供应或 ≥20% 流通的大庄/项目方必配一张全周期流转路径图**。

出图纪律：`standard_charts.plot_camp_evolution` 按 CAMP_ORDER 白名单过滤 series 键，非标准阵营名**静默跳过不报错**——阵营名必须逐字取自 `standard_charts.py` 的 `CAMP_ORDER`（唯一权威；现行 14 键：项目方、大庄、小庄、离场庄、刷量地址、CEX资金通道、CEX托管、疑似CEX托管、流动性池、其他大户、历史大户、散户、桥锁仓、锁仓/销毁；"狙击集团"等仅旧数据重绘 legacy）；**出图后必须目检图例条数 == 传入阵营数**。

结构与措辞纪律见 `report-template.md`。正式报告只有两个入口：全新分析用 `build_html.py --mode analysis-new ... --a5-seal a5_report_seal.json`，净室复核用 `--mode analysis-audit ...`；二者都会核对 seal.workflow_type，并分别强制 `audit_release_gate --profile new-analysis|independent-audit`。不存在 generic analysis 或 skip gate。历史重编译必须显式用 `--mode legacy-recompile --degrade-reason "<理由>"`，产物带可见非正式水印。PDF 仅用户点名。

**附录四件套**（验证步骤/标签↔地址对照/复核修正记录/来源）——附录 B 地址对照任何情况下不可省（正文零地址的可验证性支点）。**监控包默认不做**：观察哨/两档监控建议/appendix.json 在用户确认买入后按 monitoring-package.md「买入后监控包」节补生成（新会话可执行，材料全在落盘产物），报告末尾带固定句"如决定买入，回复一声即可补生成监控包"。**默认交付另落一份 `analysis-state.json`**（appendix 的机器子集：token/whale_groups/vault_addresses/addresses 骨架＋camp_share_series，无监控文案；schema 见 report-template「默认交付的机器状态文件」节）。交付前 checklist 见 report-template.md 末节。

## A6 复盘与迭代（仅用户明确要求时执行，不自动触发）

**默认交付 A5 报告即收工，不进入本阶段**——结论未经用户复核就自动沉淀教训，会把可能错误的经验固化进 skill（2026-07-31 用户定）。会话中发现的候选教训随手记案目录 `retro_notes.md`（只动案目录，不动 skill 文件）。用户复核确认结论没问题、明确下令复盘后，按 `retrospective.md` 执行：五类复盘清单 → AskUserQuestion 确认 → **教训分流决策树**定归宿（gate 代码/casebook/pipeline/workflow/SKILL.md 最后手段）→ 写入对应文件＋CHANGELOG 次版本＋1 → 跑 `scripts/tests/run_all.py` 全 PASS → git commit。质量 4 指标＋成本 3 指标、candidate 分级、逢 0/5 整编——细则全在 retrospective.md。
