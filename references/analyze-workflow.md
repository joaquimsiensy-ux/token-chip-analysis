# 完整版分析手册（/token-analyze，A0–A6）

> v6.0.0 承接旧 SKILL.md 全部阶段细节（规则语义零变更）。本手册是各阶段执行细节的唯一权威源；判定类失败模式在 `casebook/`（只指不抄）；上下文与外包纪律在 `context-discipline.md`；链专属操作在各 data-pipeline 文档。

## 通用执行纪律（全阶段生效）

- 优先跑 `scripts/` 固化脚本，禁止现场重写已有能力的脚本；不满足需求先改参数再改脚本，改动记入 A6。
- **关键字符串（地址/哈希）一律从落盘文件取**，从打印输出复制截断补全＝编造。
- 脚本产出判定以代码写入语句＋文件时间戳为准，stdout 叙述不可信（environment.md「stdout 与实际行为不一致」条）。
- 免费层限流当场翻车：限速常数实测收敛；退避＋断点续传标配；卡点超 1–2h 摆路径给用户选，不单通道死等。
- 本机环境坑（SSL/字体/shell/沙箱杀进程等）开工扫一眼 `environment.md`。

## A0 标的画像与链路由

产出计划落盘，**用户决策点前置**：口径选择/新数据源注册/key 索取这类需要用户拍板的事项，在计划阶段用 AskUserQuestion 给选项一次问清，不在分析中途零散打断。

先核定：合约/mint 地址（多源交叉，确认用户持有的到底是哪个）、部署在哪几条链、**总量与流通量多口径分开标注**（链上实查/第三方流通/名义已解锁——口径混淆是历次实战最高频的结论级错误源，见 casebook S 册）、DEX 真实流动性（<$50k 则定价权在 CEX，分析重心＝托管流＋金库＋充提）。

**多链代币硬关卡（不过关不开工）**："部署在哪几条链"不是登记项，是分流关卡。CoinGecko `coins/{id}` platforms 字段＋GMGN/Dexscreener＋官方文档多源核查；凡部署 ≥2 条链，必须先做**链分布盘点**——各链 RPC 实查该链供给（桥接分支按 mint−burn 口径；**镜像关系先做锁仓适配器配平**，见 casebook S-02），产出链分布表（链/合约地址/该链供给及占全局总供应%/主 DEX 流动性/预估转账量级与采集耗时），连成本预估一起用 AskUserQuestion 让用户选定分析范围（推荐项＝供给占比最大的主链；选项：仅主链/主链＋指定分支/全部链）。**禁止拿到地址就按其所在链直接开工**——用户给的地址可能只是小分支链（来源：VIRTUAL 案范围性返工，2026-07-16）。占全局 <5% 的分支默认不单独立项（用户点名除外）；选多链时各链分别过 A2 对账再合并口径。报告 TL;DR 首行必须声明分析范围（覆盖哪几条链、合计占全局总供应%），规范见 report-template.md。

另核定两件事：①**标的是否带解锁表/vesting**（tokenomist/dropstab 有记录，或链上有锁仓合约/多签托管）——有则问 3 必须包含"未来 6–12 个月解锁日程与量级"小节（要求见 report-template.md）；②**开工版本自查**：读 CHANGELOG 首个版本号并在计划里注明，交付前重读一次——版本号变了说明 skill 被并行会话更新过，向用户提示框架可能已迭代。

**链路由表**：

| 标的形态 | 读哪份 pipeline / 跑哪套脚本 |
|---|---|
| 0x 地址，ETH 主网 | `data-pipeline-evm.md`（Etherscan 免费 key 路线）＋ `scripts/evm/` |
| 0x 地址，BSC/Base 等 | 同上（预估转账量 <300 万条走扫块；更大走 HyperSync/Alchemy，先看通道决策树） |
| base58 mint | `data-pipeline-solana.md`（双 RPC 按方法路由见其分册 §0a） |
| HYPE 或 HIP-1 原生代币 | `data-pipeline-hyperliquid.md` ＋ `scripts/hyperliquid/` |
| f0/f1 地址（Filecoin） | `data-pipeline-filecoin.md` ＋ `scripts/filecoin/` |
| 0x 地址，Robinhood Chain（chainid 4663） | `data-pipeline-robinhood.md` ＋ `scripts/robinhood/` |
| 跨链部署（OFT/CCIP 等） | 先过多链硬关卡选定范围 → 各链按其 pipeline 采集＋跨链 mint/burn 配平；桥接分支链范式见 playbook §6a |
| 全新链 | 新链 SOP：先花 ~30 分钟实测免费数据面（浏览器 API/公共 RPC 能力/限速）形成临时管道笔记；分析完按 A6 沉淀为新的 data-pipeline-<chain>.md |

**通道实测探路**：写任何采集脚本前，先用 1–2 分钟小请求逐个实测候选数据源（可用性/返回结构/分页/上限/限速）；拿到任何新 key 先做 1 分钟能力探测再承诺方案；禁止基于文档想象设计方案。

**记账模型准入 gate（链路由定型后、采集开工前必跑）**：fee-on-transfer/rebase/Token-2022 扩展会让"Transfer 流水重建余额"整体算错且供给闭合发现不了（模型错但自洽）。一条命令 1 分钟出裁决，产物 `accounting_mode.json` 落工作目录——EVM `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --out accounting_mode.json`（eth 侧 --rpc 传 Alchemy 检测更强）；Solana `python3 scripts/solana/accounting_gate_sol.py --mint <mint> --out accounting_mode.json`。**exit 0（standard/WARN 级）＝放行**，WARN 逐条抄进报告数据底座节；**exit 2（BLOCK）＝硬停**——向用户报模式与证据，要继续必须人工定制记账模型，禁止套标准管线；**exit 1（检测自身失败）＝修通道重跑，禁止当 standard 放行**。检测原理与判定表见脚本头注。

## A1 并行采集（一次性全部启动）

三路并行：①**全量链上数据**（最耗时最先启动，后台跑；采集脚本标配＝限速可调/退避重试/断点续传/失败段补扫/冒烟小样本先行）②地址标签与安全面（GMGN、浏览器标签页）③价格（CoinGecko/binance.vision）。**vesting 标的加一路解锁情报轻量 agent**（tokenomist/dropstab 多源交叉，见 research-workflows §1 路线 1——下一次大解锁的时间和量是问 3 解锁小节的核心输入）。（v5.0 问 4 删除后背景调研整路退役；research-workflows §1 其余路线按需作分析工具，不再默认启动。）

长任务运维：最长任务最先启动、等待期填满下游脚本编写、零进展要告警、预估偏差超 2 倍主动汇报（抽样外推报保守上限）、废弃通道同步停掉观察哨。

**预采集衔接（/collect-data）**：开工先查工作目录是否已有预采集产物（EVM＝`data/v2/run_*/done.json`，Solana＝`data/soltx-*.jsonl.gz`＋meta）——有则**直接复用并断点续拉增量到最新**（底层采集器天然幂等），禁止无视既有产物从零重采；完整性以 collect_manifest（工作根目录 `collect_plans/`）与 done.json 为准，`done_with_gaps` 项必须先补齐缺口再进对账。批量候选的采集等待尽量前移到 /collect-data 夜间队列（`scripts/collect/collect_queue.py`），分析会话只付增量成本。

## A2 对账关卡（硬性，四查全过才进分析）

1. **余额对账**：重建结果 vs 独立数据源精确对表（形态见各链 pipeline recon 分册）。
2. **供给闭合**：总量恒等式/mint−burn 配平（内部自洽检验）。
3. **供给真值闸（v6 新增，重放收尾必跑）**：`python3 scripts/lib/supply_truth_gate.py --chain <链> --token 0x…|--mint <mint> --replay-stats <replay_stats.json> --out supply_truth.json`——重放净供给对链上实查 totalSupply()，治静默改账盲区（老合约 migrate() 改账不发事件、全部内部自检 PASS 而余额虚高，见 casebook S-01）。**exit 0 PASS／exit 2 FAIL＝该币余额禁用重放结果改 Multicall3/RPC 实时直查（地址全集与转账历史仍可用重放，重放余额仅作 ≥阈值超集筛选）／exit 1 检测自身失败修通道重跑，禁当 PASS**。
4. **时间抽查**：EVM 走分层计划制——先跑 `scripts/lib/anchor_plan.py` 出抽样计划（3 时段×3 余额档矩阵点＋四类强制覆盖点：全史最大单笔/最大单日净变动/数据源交界块/门槛±10% 边缘地址），再照单对照浏览器；纯随机锚点容易全抽在平静期、高风险位置反而漏掉。Solana 案走 anchor_sampler.py。注意本查测的是数据完备性与浏览器一致性，不替代供给闭合对 mint/burn 口径的把关。

对不上＝数据有洞＝回去补，不许"差不多就行"。

## A3 分析

**惯犯层盲化（A2–A3 全程）**：开工即 `export CHIP_BLIND_SERIAL=1`——标签查询的 serial-actor（惯犯）命中不进任何主输出、完整详情自动封存案目录 `sealed_serial_hits.jsonl`（label_lookup/analyze_holdings/replay_edges/build_evolution 四出口已接线；设施类标签照常输出）。动机：提前看到"这是 XX 案惯犯"会造成合并判定的先入之见；实体冻结后在 A4 揭盲作定向复核线索。

方法学全部在 `analysis-playbook.md` 路由索引（先定位节再区间读分册），按序做：

1. **地址身份标注**（官方标签→外部证据→行为特征三级兜底，playbook §3）→ **金库与核心实体逐笔归因**（§4）→ **关联聚类**（多证据边＋服务枢纽剔除，§6；合并只认专属性证据——通用实现/通用服务共用不算，见 casebook E-01）。
2. **判例库过闸（实体表冻结前必做）**：把 `casebook/cex-custody.md` 与 `casebook/entity-clustering.md` 全册触发现象过一遍，命中的逐条做"必做区分检验"。
3. **实体身份硬闸**：实体表冻结前跑 `scripts/report/entity_identity_gate.py --state … --chain … --snapshot …` 产出 `identity_gate.json`——对每个实体地址＋≥1% 大仓做标签双源（CSV 主库＋address-book 手工层，label_lookup 已自动并源）、Solana ed25519 曲线判定、托管假设三查；INFRA_IN_ENTITY／PDA_UNRESOLVED／BIG_UNLABELED 三类 flag 逐条填 resolution（查了什么、结论是什么）——**build_html G8 会校验此闸，flag 未解决报告物理上编不出来**。币安 Alpha 在架的 Solana 标的同时做 Alpha 集齐率判别（casebook C-01；easy 版 E0b 步骤④同款，完整版同责）。
4. **庄级实体识别、标签划分与类型三分类**：门槛与细则的唯一权威源＝playbook-entity-cluster-tiering §6a（v5.0 要点：不分级；项目方无论份额；大庄＝当前 ≥20% 总供应或 ≥20% 流通；小庄＝≥5% 或 ≥10% 流通；离场庄＝峰值 ≥10% 或 ≥15% 流通且当前非庄；刷量地址单独标签；狙击集团标签已废止，发射窗协同实体按普通门槛判级；合并口径含全部疑似关联地址）。
5. **其他大户排查前置双闸**（§6a）：其他大户线＝当前 ≥0.1% 总供应或 ≥0.2% 流通，逐个过批量排查层（标签库/惯犯库/指纹/funder 溯源）才准归阵营，报警才人工深挖；每个已识别实体做不设持仓下限的成员完整性扫描（防分仓漏判）。
6. **全量转账重放出各阵营占比演变序列**（阵营划分见 §6a）：分母＝当期净供应序列，**逐时点 assert Σ阵营＝100%±容差**，改过名册跑反向断言（casebook S-03）；**历史清零层检测**——重放全期 max 仓位而非只看现仓（track set 按现仓筛会漏整个历史波次，casebook S-04）。
7. **庄家当前状态评估**（§7）→ 质押/留存修正（§8）；建仓成本仅按需算（§6b 降为工具）；CEX 净流×价格作为演变解读工具按需用（防内部调仓伪影，§5）。

数据先验结构再分析（榜单唯一性断言、多档抽查），批量脚本先 2 个样本验证编解码再放量、绝不吞异常。**份额阈值一律整数运算**（`TOTAL//100`，浮点比较会把"恰好整数枚"大户判漏——那本身还是橱窗仓指纹，漏它双重损失；来源：meow 案 2026-07-15）。

## A4 对抗复核（必做）

执行序（细则与 prompt 骨架的唯一权威源＝playbook-evidence-wording §10＋research-workflows §2，此处只列主干）：

1. **扰动敏感度前置**（EVM 案，`cluster_sensitivity.py --dir <案目录>`，sensitivity_report.md 作复核输入；FRAGILE/STABLE 字样只进复核材料禁进报告正文）。
2. **惯犯揭盲**（实体冻结后 `label_lookup.py --unseal` 取封存命中，与实体划分互证/互斥）。
3. 本地反例自查脚本前置。
4. **N 路怀疑者 agent**（给数据文件路径让它**自己重算**，不是审阅文字；强制构造备择解释——casebook 三册就是现成的备择解释清单，组 prompt 时按题材摘触发现象）＋1 完整性批评角色查报告缺口（必查全史极值清单）＋1 路**外部异构怀疑者**（codex/GPT 单进程横扫全部结论）。
5. 判定三档 CONFIRMED/WEAKENED/REFUTED（**必须实际核查，"理论上可能"不算推翻**）→ 修订顺序先修数据管线再修文案，图表措辞同步改 → 修正记录印进报告附录。

## A5 报告

报告本体先写 `报告.md`＋`charts/*.png`。**三张标准图必配**（阵营占比演变/庄级实体 vs 价格/价格与关键事件），直接调 `scripts/report/standard_charts.py` 三个函数——规格与配色已固化，不要每次重新设计；**图 1/图 2 放 TL;DR 顶部（问 1 直答上方）**。**每个当前持仓 ≥20% 总供应或 ≥20% 流通的大庄/项目方必配一张全周期流转路径图**（`scripts/report/lifecycle_flow.py`，样图 references/examples/lifecycle-flow-sample.png）。

出图纪律：`standard_charts.plot_camp_evolution` 按 CAMP_ORDER 白名单过滤 series 键，非标准阵营名**静默跳过不报错**——阵营名必须用标准名（项目方/大庄/小庄/离场庄/刷量地址/CEX托管/流动性池/其他大户/散户/桥锁仓/锁仓销毁；"狙击集团"仅旧数据重绘 legacy）；**出图后必须目检图例条数 == 传入阵营数**。

结构与措辞纪律见 `report-template.md`（三问逐条直答＋标签体系＋代币数量带【总量X%】＋正文零地址＋局限性独立成章；CEX 黑箱表述红线——充入≠卖出、"链上可观测范围内"限定、净流剔除同 CEX 内部对倒、给单一实体份额上限——权威源 playbook-evidence-wording §11）。然后 `python3 scripts/report/build_html.py --md 报告.md --out 报告.html` 出自包含 HTML（PDF 仅用户点名，用 md2pdf.py，质检双轨见 environment.md）。质检：build_html 退出码 0（缺图会 WARN 拒绝交付）＋浏览器目检（图全显/表格无错位）。

**附录四件套**（验证步骤/标签↔地址对照/复核修正记录/来源）——附录 B 地址对照任何情况下不可省（正文零地址的可验证性支点）。**监控包默认不做**：观察哨/两档监控建议/appendix.json 在用户确认买入后按 monitoring-package.md「买入后监控包」节补生成（新会话可执行，材料全在落盘产物），报告末尾带固定句"如决定买入，回复一声即可补生成监控包"。**默认交付另落一份 `analysis-state.json`**（appendix 的机器子集：token/whale_groups/vault_addresses/addresses 骨架＋camp_share_series，无监控文案——/token-update 的实体表原料；schema 见 report-template「默认交付的机器状态文件」节）。交付前 checklist 见 report-template.md 末节；**外部代币名自查**（铁律 1）。

## A6 复盘与迭代（固定最后一步，不可省略）

按 `retrospective.md` 执行：五类复盘清单 → AskUserQuestion 确认 → **教训分流决策树**定归宿（gate 代码/casebook/pipeline/workflow/SKILL.md 最后手段）→ 写入对应文件＋CHANGELOG 次版本＋1 → 跑 `scripts/tests/run_all.py` 全 PASS → git commit。质量 4 指标＋成本 3 指标、candidate 分级、逢 0/5 整编——细则全在 retrospective.md。
