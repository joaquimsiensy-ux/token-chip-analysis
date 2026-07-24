# CHANGELOG — token-chip-analysis（活跃窗口）

版本规则（v3.0 起两维制，详见 references/retrospective.md「版本号约定」）：
- **skill 版本**：主=架构级重构；次=每次**分析复盘**迭代 +1；修=文档小修
- **labels 数据版本**：标签库扩容/重建记 `labels vX.Y` 前缀条目，不再占用 skill 次版本号
红线：条目只记工具性知识（数据源/坑/方法/脚本），禁止记录任何代币的分析结论。
每条迭代条目附成本指标（轮次数/Bash 调用数/交付用时）+ 质量指标（初稿关键结论数/复核判定分布/漏检实体数/传播级数字错误数，v3.0 起，见 retrospective 步骤 1）。
**写入前必跑 `python3 scripts/tests/changelog_lint.py`**（防撞号/倒排——两者都实际发生过）。
本文件只保留最近 ~10 版（整编时滚动）；更早的完整迭代史在 `CHANGELOG-archive.md`，考古规则来源先 grep 该文件。

已知版本事故存档（保留原貌，不改写历史）：
- **2.21.0 重复 ×2**（2026-07-17 两个并行会话撞号：「标签库 v4.1」与「BEGGAR 复盘」各自 +1 —— git 化前无并发防护的实证；两条均保留原号，引用时注意区分）
- **2.24.0/2.25.0 曾物理倒排**（同日并行会话插入位置错位）——2026-07-18 稳定化时仅调整排列顺序，两条内容一字未动

## 版本索引（活跃窗口，新在上）
- **3.28.0 2026-07-24 GOAT(Solana) GPT5.6 外部复核裁决采纳：Jupiter DCA keeper 代付边假小庄病灶+复核翻案落盘义务+正文↔state 一致性硬闸**：methods **注资边先决字段闸**（gas 溯源产物 `my_sol_delta≈0`=funder 仅 fee payer 非注资方一律禁作边；Jupiter DCA/Router keeper 指纹三件套=目标 SOL 零变化+自动执行程序+同 keeper 服务互不相关多址；approx=true 单独不成边——5.24% 假小庄实锤：三址合并唯一依据共同 funder 86KSd 全为代付、同文件里它还服务被单列的独立定投户、复核撤销拆回全不达标）+三步体检两补强（**体检必须在 funder 活跃窗内做**——"已弃用清空"≠非服务型，退役 keeper 酷似私人母钱包；**排他反例检查**——判私人前先查同 funder 还服务谁）；address-book Solana +2（Jupiter DCA keeper 86KSd/CTaDZW，禁作合并边）；evidence-wording §10 +2 条（**翻案证据落盘义务**——风险降级型翻案〔庄→调度商/做市〕证据标准不得低于原结论、临时 RPC 查完即弃只配"高度疑似"，GOAT P0 调度商改写三中转→三所路径未落盘被外部复核降级"CEX 终点未确证"；**修正传播机器件清单义务**——state/entity_camps/生成脚本硬编码/下游脚本全入必改清单，数据修 bug 出新版后**旧文件当场改名失效**防静默读脏〔compose_evolution 读去重前发射窗致 LP 桶高估 0.83pp〕）+对照表 3 行（截断样本禁外推"全体系"/残余非零禁写"全部换手"/抽样数据禁"共 N 个"全量普查用词）；easy-workflow **交付前正文↔机器件一致性硬闸**（实体数/成员数/tier/status/峰值五项 diff，正文口径禁领先机器件——GOAT 正文三处复核修正〔狙击作废/P0 改写/离场庄扩 5 址〕全没回写 state，外部复核判"state 带毒 update 会复引已推翻实体"）+判定块④理由纪律（禁引未确证定性；P0 身份未确证禁写"不推荐完整版"——用数据缺口反证无价值是循环论证）+阴性结论覆盖披露（锚点峰值 ≥1% 清点"已深挖 N/M"）；state-anomaly §9c 取证落盘义务注记（指纹保留=BANANAS31 独立复现全链路落盘；GOAT 案侧未落盘被降级）；report-template 混合重建图注两条（末日封口跳变 ≥2pp **逐桶**注明口径切换——GOAT -12/+13pp 只解释了 P0 的 2.8pp；作图输入必终版文件）。外部复核判定分布（对本方 easy 报告）：REFUTED 9/WEAKENED 5/CONFIRMED 5（供给闭合、末日阵营算术、P0 三址关系与 24.31%、离场庄严格两址、发射窗 571/500%/9.42% 限定口径保留）。**不采纳 4 项（矫枉过正）**：①"历史图谎称全量重放"系稻草人（图注/局限早声明混合口径）②"缺 entity_id/provenance"时代错位（3.19 引入晚于 GOAT）③"静置仓反扫规则/dormant_warehouse_audit"系 GPT 引申发明（skill 无此规则；实质缺口按覆盖披露轻量吸收）④"币安 0.66%→Alpha 黑箱可忽略 REFUTED"部分矫枉（9ZPsRW 行为学托管仓在 0.66% 内、"其份额≈Alpha 黑箱"有集齐率方法论支撑——吸收的只是论证链须写出+单源标注注明）。GOAT 案侧：state 按裁决重建（原版备份 .pre-review），记忆存档同步改写
- **3.27.0 2026-07-24 SIREN(BSC) GPT5.6 外部复核裁决采纳：Hedgey 公共锁仓协议误判"庄家自有设施"翻案+等额原路返还指纹双解**：methods 四测④首实锤（**币种内视角选择偏差**——"生命周期仅两日/只服务这批地址"以本币种史为分母的假专属，跨币种反查一步即碎；SIREN"归集主仓"实为 Hedgey TokenLockup、"专用原子中转"实为 BatchNFTMinter，Sourcify 名"Hedgeys"一查现形）+pool-probe 硬闸扩类（**锁仓/vesting 协议＝第二类必查设施**，池 selector 探测无效、抓手=Sourcify 名+④测+「多址存入→长持→到期等额赎回」形态；对历史报告追溯核查同样适用）+归属证据学原例证修正（**"N/N wei 级等额原路返还"零协同证明力**——锁仓到期赎回的机械必然，SIREN 曾用它"排除托管备择"而托管恰是真相；**行为指纹准入前置=先对动作中枢跑四测排除协议机械行为**）；report-template 三账本第三案（锁仓协议版两复核方各犯一半：本方吸入协议位置账凑巧对/对方剔除不穿透曲线二月错误归零，夹出正解=剔除+受益权穿透）；evidence-wording 口径三件套（分解构成值≠子口径峰值·48.41 冒充核心峰值真值 48.53@2025-08-07/衍生分母必须命名·"流通盘 94.9%"实为非销毁供给/复合实体控盘**双端点交付**·可证下限~风险上限禁单冠"单一庄家"）+对照表 2 行；病例回填成员数三套互斥（正文 1,036+93/附录 1,086/局限 50，state 真值 1,129）+残仓 1.44 vs 精确 1.41414——编译化前手写病 facts G1/G5 已覆盖。外部复核判定分布（对本方）：REFUTED 2/WEAKENED 4/CONFIRMED 4（重放闭合、68.69% 峰值与时点、903 址协同行为层、图 2 六月离场方向——对方自认其原图二月归零错误）；行为群与投资结论不塌，中层机制叙事"归集→洗仓换代"改写为"批量锁仓→到期赎回+赎回后真实换仓"
- **3.26.0 2026-07-24 QUQ(BSC) GPT5.6 外部复核裁决采纳：公共池误判 bot 病灶修复+三账本分离口径宪法+V4 费可算改判**：methods 先验三测升级**四测**（DEX 池四 selector 探测为决定性首测；部署时间测试对池类单向有效——池必晚于代币，"晚于"零信号；**同模板 code size 语义修正=第一解释是同 factory 标准实例非同一服务商**，22962B=Pancake V3 池标准长度/22142B=Uniswap V3）+**成员表 pool-probe 准入硬闸**（定稿前+复核时对表内全部合约无差别重探，复核者禁沿用主分析标签——R2 翻了 449e 却漏同性质两池的正交性病根）；state-anomaly §9b 二次修正（"bot 合约对"证伪为 Pancake V3 QUQ/USDT 0.01%/1% 两公共池，盘型=strict EOA 接力核心+自有 LP+经池轮转；"与主仓百万笔互转"非专属证据——池与其最大 LP 天然如此）；channels +2（**V4/Infinity 单例余额禁直接归池归庄**，归属唯一正解=poolId+position+owner 逐头寸重放，QUQ V4 17.6% 拿单例总余额判 WEAKENED 实锤；**V4 费可算改判**推翻 3.22.0"无硬数"——全池费=Σswap 输入×费率/仓位=ModifyLiquidity 重放按活跃流动性分摊（复核 24h 重放 20,610 笔 swap 与 liquidity 字段 0 不匹配）/未结算=feeGrowthInside 公式，calc_v4_lp_fees_24h.py 留档）；tiering **行为 cohort≠确权实体**（P1 授予最低门槛=硬边覆盖全员；793 址"狙击集团 P1"被推翻——附录自注"含路由独立用户"却仍标集团，标签与认知不一致即禁）；evidence-wording +2（**ATH 全史通道纪律**：窗口自算只能写区间高点、采集产物 error 响应落盘必列警——CG max 挂了没兜底、本地 CMC 全史真 ATH $0.008875@2025-03-22 没交叉、$0.004798 假 ATH 被抓；**账号数≠自然人数**：1,800 账号独立性 WEAKENED）+对照表 2 行；report-template **三账本分离口径宪法**（成员表/位置账/经济控制账互不冒充，"庄控制多少"主答案必用经济控制账=钱包+可证 LP 赎回权穿透；Codex 拿位置账 26.73% 当主答案与 Fable 拿单例余额归庄为同一制度的两个反向病例；economic_control_ledger 候选交付件）；病例回填：正文 215 vs state 214 成员数不一致系编译化前手写报告，facts G1/G5 已架构性覆盖。外部复核判定分布（对本方报告）：REFUTED 5/WEAKENED 2/CONFIRMED 3（经济控制口径 64.6% 方向、strict 四址核心、07-22 订单流拆壳保留）；QUQ 案侧同日执行监控地址表重梳（纯 EOA 庄组+设施独立哨）
- **3.25.0 2026-07-23 BANANAS31(BSC) easy 三战复盘+逢5轻整编**：channels +5（**v2 官方客户端本机三态与分段采集解法**——直连必挂大响应被掐/clash 代理长连接偶发劣化 stall/解法=staged_capture.sh 段级短跑收编+v1 轮询兜底最稳+混通道 v1→v2 归一 roundtrip 后段界互斥合并；SQD 对账双源 BSC 数据点四代表日 67,731 行六元组零差集；**Alpha 转正币 Router 黑箱消失**（listingCex=True→Router 清空迁移）；**BSC 历史块时长折算坑**（2024-11=3s/块，时间叙述必用块时间戳差，复核抓 27→81 分钟）；four.meme TokenManager 毛口径虚高禁用）；state-anomaly **§9c CEX 间调度商转正**（GOAT+BANANAS31 跨链两案复现；BSC 亚型=归集在途仓，配套 CEX 托管曲线系统性低估注记义务）+§7 **离场时点必以处置流水（DEX 卖出/充所）定位**（余额消失可能只是迁移；迁移窗零卖出反是最硬协同证据）；methods 测试转账指纹机制二见（10 枚测试一对二跨簇合并+秒级交替时序）+【候选】**同尾数批量提币=同批次非同人指纹**（体系外反例实证）+**zero-value transferFrom 投毒串簇**（cluster.py+cluster_prep_duck 双路 value>0 过滤补丁）；tiering【候选】狙击 bundle 阴性≠非协同（建仓形态两型：捆绑原子/程序化连续扫货）；easy-workflow E0b BSC 版首战入册（~30min：标签盲化认所+HyperSync 三层溯源+方向判别补强**提出方向≠非所方**须跨币种画像）+E4 前 state 骨架先落盘+成本基准三战行（2-3h 档守住）；evidence-wording 截断地址第七犯（反查时点前移到首次誊写前）；report-template state 供给字段 human 单位注；轻整编：CHANGELOG 滚动归档 3.10.0–3.11.3 五条+docs lint
- **3.24.0 2026-07-23 SIREN(BSC) 全案元复盘：口径质疑回应纪律（禁报告自证）+归属证明证据学+封闭盘定价结构+叙事开关+五问回填第一案**：supply-recon 质疑条升级为正式（拆数必回原始数据现算、禁转抄报告口径自证——报告是被审对象不是证据；报告内部"多处一致"对同源漏改零证明力；用户复述求证=高信号输入，复述与报告的冲突按读者错/报告错双向可疑逐处回数据裁决——SIREN 案分析者引用报告口径把用户的正确理解"纠正"成错、20 分钟后被 65.9−49.3−1.44 加法推翻的完整反例）；entity-cluster-methods 新增归属证明证据学（层数封顶原理：图全连通、层数越深可达含金量越低，穷举更多代数是稀释不是加固；归属证明本质=只有同一控制者做得出的动作组合非"钱能流到"；双向合龙 BFS+反向池穿透两条独立链中间重叠≫单向穷举）；state-anomaly 新增 §5a 封闭盘定价结构（割裂≠孤岛：双边库存无搬运套利软连接成封闭联合体/小所镜像盘先验库存再计数/残留价差 1% 双向印证断裂与软连接/价差梯度=通道断裂梯度；报告写封闭盘必须预答"价格为何仍一致"）+§9d 可人为触发的叙事开关【候选】（送币给公开人物赌例行处置="互动即背书"谁都能按的开关；时间锁扣单独陈列、策划者=庄家须独立举证；联动 §11 死料引爆日期陷阱）；§10b 五问守恒问/口径问回填 SIREN 第一案实证（跨案两实证：SIREN 07-20 配平与口径事故先于 QUQ 同型发生——教训入库后同类追问在 QUQ 案消失〔时区/术语/图零追问〕、新面孔口径错误照样出现，类型化交付前自检的必要性双案实证）；全景过程档《复盘_SIREN追问翻案链_2026-07-23.md》落案目录
- **3.23.0 2026-07-23 QUQ(BSC) 全案元复盘：交付前第一性五问+庄组纯 EOA 原则+报警归因分解+复盘完备性两道硬检**：evidence-wording 新增 §10b 交付前第一性五问（与对抗复核正交的第二道闸——复核与主分析共享数据集与图视角，视角缺的维度重算百遍看不见；五问=不依赖视角的不变量检验：守恒加总·外部聚合器存量必过第一方账本/数量级闭合·N×单体 vs 宏观缺口>30%必拆/动机自洽·讲不出动机=归因红旗【候选】/口径三要素·范围性质时效/真值探针·自有真单当 ground truth【候选】；附则=用户假说是正式输入【候选】+前提翻案的传播义务·数字配平管数字这条管逻辑）；monitoring 投后运行纪律 +2（庄组第一性原则=只放会自己走路的 EOA、合约含自有池/执行器/托管 Vault 一律不进组改独立哨；"庄在动"报警先按发出方身份×接收方期末留存归因分解再定性，口诀"池子或合约=营业流水划走，库存 EOA 动了才是庄的手"）；retrospective 复盘完备性两道硬检（修正对照表逐行核销防"只沉淀最后一段"偏科/candidate 清账扫描防复盘班车滞后，含 git status 补提交检查）；全景过程档《复盘_QUQ追问翻案链_2026-07-23.md》落案目录（12 轮追问-翻案对照+错误根源六类+复核为何不抓的正交性分析）
- **3.22.0 2026-07-22 QUQ(BSC) 投后专项复盘：币安 Alpha 制度侧特征三件+全史量能考古三件**：channels 分册 +6 条——Alpha mulPoint 积分倍数直查接口（bapi token/list，645/656=1x、新 TGE 30 天=4x，只有当前值无历史）/Alpha 积分政策时间线锚点（2025 中 BSC 全板 2x→09-04 取消→2026-07-22 CEX 限价单 BSC 4x）+量能断崖三因鉴别法（个币处分/板块政策/竞价分流；mulPoint+对照币 GT 同窗+xapi 断崖窗口社区讨论三件套）/场内↔链上量能迁移互斥+监控防误读（链上量可归零而需求未死；政策利好窗"向托管大额转移"优先判搬场内非出货；早期链上口径系统性低估须声明）/全史 DEX 成交量池腿法（单边口径+LP mint/collect 剔除+价格三源拼接+费反推独立交叉验证 103%）/transfers_lib 整表读大 parquet OOM（亿级自写 iter_batches 流式+块边界去重）/V3-V4 LP 费口径鸿沟（V3 collect−burn 双边各收、V4 费并头寸无硬数）+swap 回执速查三招（V4 腿=PoolManager 对手方/fee() 0xddca3f43/拆腿和验路由抽成）；**同日补录 v2 修订翻案方法群**：订单流成色拆解四步（"对倒/自转"定性前必拆 tx.from+4337 UserOp+档位分桶——90% 自转→95% 外部订单流大翻案的方法化）/独立量化工作室三重判据（资金隔离+起源早于标的+多币面=第三类桶，金库撤墙哨）/GT V4 TVL 伪影+LP 归属定池属/同 tx 等额配对裁决法（b300 结案件）/监控分册新增投后运行纪律五条（口径翻案三处同步+通道集过标签库+制度哨升头号+承接哨单列+毛净判读口诀）
- **3.21.0 2026-07-22 PENGUIN(Solana) easy 四战 E0b 关卡中止复盘：币安 Alpha 链上托管体系首次实锤+Alpha 集齐率判别法**：E0b 固化当天首次复用即中止案（严格口径 35.69%/宽口径 46.36% 超线，用户两轮问询制——初判报数→令深挖"高度疑似"档→升格后终裁中止）；最大沉淀=币安 Alpha 的 Solana 链上托管三层体系接近确证（库存仓 9ZPsR 集齐 66/70 Alpha 币+执行仓 6ZaWyb 直连三 DEX 池对倒+BN111 vanity 批量程序 fee payer 4 址轮换），address-book +4 址+1 程序；"Alpha 集齐率判别法"入 pipeline-solana-scan §3（全持仓×Alpha bapi 表交集一次调用分四档 94%/3-8%/≤2%）；E0b 三通道认所补④Alpha 对撞步（Alpha 托管仓常为第一大持仓，漏认即把最大黑箱当神秘巨鲸）
- **3.20.0 2026-07-22 Fartcoin(Solana) easy 三战黑箱关卡中止复盘：前置 CEX 黑箱关卡固化 E0b+Solana CEX 地址资产 3 条**：连续三案用户手写要求后固化——easy-workflow 新增 E0b（top榜快照→三通道认所(本地库/Vybe top-holders/历史cex_map)→行为画像分层补认(热钱包=百余币种+万级SOL+大流水；冷储分仓群 trace 调度枢纽)→确证/疑似两档分层报数→超线 AskUserQuestion 停等，中止則存档不交付）；address-book Solana CEX 节 +3 高复用热钱包（Hyperunit 桥/Coinbase 热3 含冷储分仓调度指纹/Kraken 双源）；执行侧教训两条重申（开工未读当链 pipeline §4 重复试错已固化端点、截断地址手工补全再犯致 7 址查空返工）
- **3.19.1 2026-07-22 serial 回灌设施冲突硬闸+curation 增量覆盖修复（0x238a 裁决执行，文档小修级）**：A7 首战冲突（QUQ 大庄#1 误吸 PancakeSwap Infinity Vault）用户裁决三条组合拳落地——curation override 恢复主库设施身份/QUQ 案侧摘出成员表 215→214（曲线注记下次更新重算）/accumulate_offenders 设施级冲突硬闸（primary+goldset-infra 拦在 CSV 外，绕闸须人工显式动作无 --force）；顺修 add_labels HIGH_TRUST_PREFIX 缺 curation 真缺陷（此前 curation 增量入库压不掉现行、与 build_labels SRC_PRIORITY=-1 语义不一致）；T2 契约翻转（拦截+不误伤）；全家桶 12/12
- **3.19.0 2026-07-22 质量/速度/稳定性专项第三批（非复盘专项，@CX 三轮 18 项）**：记账模型准入 gate 双链硬闸（HOGE/BERN 税币实测 BLOCK）/entity_id 稳定主键+provenance 薄版血缘+时间因果轻量口径（merged_since 宏+合并时点措辞纪律）/图层同源 figures_from_facts 三模式/惯犯层延迟揭盲四出口+跨案身份冲突检测（首战抓 QUQ 误吸 PancakeSwap Vault 实锤待裁决）/聚类扰动敏感度进复核材料/采集跨进程锁+run_id+token 出 argv/probe_keys 12 项周巡检 launchd/峰值窗口两级预筛 657→330s/时间抽查分层计划制/价格双源抽查/P0 素材外包模板点名 opus/复盘草稿生成器/脚本分叉盘点首轮 439 份/时间封存测试两件/断点恢复节；全家桶 12 项
- **3.18.1 2026-07-22 HyperSync Solana 混合分段提议评估否决存档+验收对账器收编（文档小修）**：recon2.py 从会话 scratchpad 收编为 scripts/solana/hypersync_recon.py（GA 重验收资产防清理丢失）；§13d 增"近期段 HS+历史段 SQD"否决硬结论（@CX 复核：196 天=覆盖范围非准确范围、干净区仅前沿 ~20h 单次抽样、静默洞→证完整=SQD 重拉、供给对账兜不住成对缺行、双引擎不缩短认证关键路径）
- **3.18.0 2026-07-22 质量/速度/稳定性专项第二批（非复盘专项，@CX 方案 18 项）**：报告编译化 facts 事实源+宏+语义 gate（手抄数字架构级消灭）/故障注入盲测六用例（QUQ 快照缺块盲区固定化）/D3 三大文档拆 8 分册兑现/惯犯库双源回灌 217→1741 址/标签时效语义切分/Solana 双引擎整合+完备性验收**不通过禁用**（历史区缺行 3.6-22% 链上终审实锤）/collect_queue 泳道化/磁盘水位三件/launchd 夜间自动采集/监控两段制 schema 三字段/外部代币名自查自动化/HyperSync overage 831rpm 实测已生效/pre-commit 三检/git 历史 key 清洗
- **3.17.0 2026-07-22 GOAT(Solana) easy 二战复盘：长币龄混合重建工程加固+CEX 间调度商指纹**：Helius 大扫描 300s+gzip 通道（24.7 万账户 67MB 一次拉全，分片器降末位）/window_fetch gap 合并重复坑+负余额指纹/whale_deep cap 截断语义+10RPS 并发纪律/pump.fun 毕业迁移钱包入 address-book（发射窗峰值榜必剔）/编造地址 base58 侧五六犯；candidate 2 组（CEX 间库存调度商指纹 state-anomaly §9c+锚点复用两扫描 §11.3）；whale_deep 三参数悬账收编+scan_token_accounts --compressed/--timeout；easy 成本基准 GOAT 行（2-3h 档初步稳定）
- **3.16.0 2026-07-22 B 档五项收官：/collect-data 批量预采集+网络层异步化+复核 workflow 固化+Sourcify/DefiLlama 双通道+文件守卫 hook（非复盘专项）**：@CX 方案 B 档全部落地——新命令 /collect-data（collect_queue.py 多币串行队列，EVM 五链+Solana，manifest 记账/残缺 run 隔离/断点幂等，CAKE 296 万行+wSOL 缺口态+错址 fail-closed 三路实测）；net.py+rpc_batch.py 进程内异步替代 curl 子进程树（httpx+tenacity+msgspec，40 址与 curl 逐项等价）；adversarial-review 固化 workflow（schema 强制裁决 JSON+同批并行 fan-out，冒烟 2 路 100s）；Sourcify 合约身份批查（sourcify_check.py，v2 直连免 key，代理实现名一次拿到）；DefiLlama 老币历史价格主兜底（llama_price.py，CAKE 2020 起 2117 点全史实测）；guard_file_ops hook（Read 巨文件拦截+原始采集产物写保护，热加载实证）+PostCompact 提醒；HyperSync key 固化 ~/.config/hypersync/token
- **3.15.0 2026-07-22 QUQ(BSC) 完整版复盘+逢5轻整编**：公共基础设施先验三测（部署早于代币=强公共信号+同模板 code size 指纹——449e 大翻案教训）/寄存仓移仓指纹（监管点名对齐+3天原路等额往返）/净成本病态敏感双口径（正式：净额<毛额1%禁点估计,+剔自控镜像流第三口径）/bot 营运峰≠EOA 囤仓峰入 §9b 排代际/R2 备择解释路对结构性定性必设；快照缺块坑（供给闭合对缺整行免疫,done.json 前置第5查+负余额指纹）/手写地址第四犯工具化 real_addr/bscscan WebFetch 截断地址禁入产物/HyperSync v2 增量 4s+补丁段核验；整编：高扇出三判据两案转正、CEX 事件驱动做市纪律降档存档、5 条标疑、归档滚动 12+1 条（3.6.0 缺失正文补档）；D3 三大文档拆分推迟单独会话
- **3.14.0 2026-07-22 DuckDB 重放/缩图引擎三阶段落地（非复盘专项，@CX 交叉复核方案执行）**：亿级样本主路径换列式引擎——新件 7（replay_duck 合一引擎 v1CSV+v2parquet 双输入/cluster_prep_duck 缩图件+cluster --prep/golden_baseline 回归门禁/test_engine_equivalence hypothesis 性质测试/env_check 版本锁/run_guarded 长跑监督器/pyproject+requirements.lock 依赖锁）；等价实证=ASTEROID+SIREN 七项全等（含 merged.csv 逐字节）+QUQ 1.03 亿行三件逐键全等+聚类四类判定全等；性能=QUQ 核心重放 31s（原数十分钟）/缩图 19.5s 出 76 万聚合边/SIREN 7.1GB 守限（旧外推 19GB）；DuckDB 数字安全坑 6 条实测入 data-pipeline-evm §12（UHUGEINT SUM 退化 DOUBLE/VARINT 乘法退化/hex cast 位宽/temp 磁盘 GB-GiB/块界感知去重/窗口成本）；三缺口修复（pass1 坏行记账/cluster 阈值整数化/dedup 重组冲突检测）+排序确定化；changelog_lint 自动 hook 进 settings.json
- **3.13.0 2026-07-22 QUQ(BSC) easy 模式首战复盘**：币安 Alpha 场内 K 线端点（bapi alpha-trade/klines，374 天窗口**非全史**）+CMC 全史日线 EVM 侧二案复用；「接力库存仓」盘型入 state-anomaly §9b（主仓多代交棒直转·数十倍总量/净持≈0 执行枢纽网/「自持↔池↔CEX 场内」三态日轮转 30-50% 锯齿/量能市值数十倍倒挂——体系判定靠直转边不靠 gas，「独立做市商」备择每案独立走）；单 tick V3 NFT 头寸=零滑点自转刷量设施指纹；枢纽三段处理法（度>200 不作扩散桥/种子枢纽保留成员资格/NPM·EntryPoint·1inch 事后卫生检查强制收尾）；key_edges 设施边排除→来源拆解选择偏差（daily_delta 缺口法兜底）+亿级 edges 流式写；easy 首战成本基准单币 ~2.5h（采集 67min）
- **3.12.1 2026-07-21 公共数仓准入验证+BigQuery 复核通道正式化（非复盘专项）**：ASTEROID(ETH) 5 代表日 132,471 行三源对账——AWS v1.0/eth 与 BigQuery goog 官方版均与 HyperSync **逐行字节级等价**（键零差集/值零不一致）,"数仓质量≤HyperSync"疑虑在 ETH 段实证解除；分工定稿（用户拍板）：主力=HyperSync 不变、BigQuery=备用+出错复核源（新件 fetch_bigquery.py,仅 ETH,定向日期查询实测 12GiB/次推翻旧估 200-500GiB,免费 1TiB/月≈85 次复核）、AWS=等价但 pass（S3 无服务端过滤整分区下载 60 分钟,手工方法留档 §11 应急可复活,新鲜度实测 T+1~T+2 优于 sonarx T+7）；GCP 资产一次性开通（sandbox 项目+OAuth 缓存,api-keys.md 第 16 节;新账号 ToS 403 坑实测）；新源准入通用纪律定型（四型代表日+键值集合对账,禁品牌信任替代逐行对账）；data-pipeline-evm 新增 §11
- **3.12.0 2026-07-21 简化筛查模式 /token-easy-analysis + 图 1 价格右轴（非复盘专项）**：新命令+新分册 easy-workflow.md（E0–E7）——引擎与完整版同强度（采集/对账三查/深度关联全套/复核路数一分不减），砍背调（问 4 整路）与完整报告，交付两件套单页 HTML（图 1+按实体结构细分的阵营快照表+判定块含 Alpha 黑箱占比）+analysis-state.json 必落盘；绝不自动转正式，人工决策后 /token-analyze 同目录衔接（E7 继承清单+隔日增量拼接）；E6 复盘按需触发（有工具性增量才走全套）；场景=币安 Alpha/现货初筛 60+ 候选批量找高控盘标的，档 A 预估单币省 30-40%。standard_charts.plot_camp_evolution 新增 price_series 参数（右轴黑线白描边/量程>30x 自动对数/图例并轴单位/裁剪到阵营时间范围，demo+AKE 真数据双验证），完整版图 1 同步升级为必传，旧调用兼容
- 3.11.3 Solana采集加速 | 3.11.2 HyperSync付费档+客户端v2 | 3.11.1 销户覆盖审计 | 3.11.0 USELESS(Solana) | 3.10.0 LPT(ETH+Arbitrum)质押型首战
- 3.9.0 SQD(Arbitrum) | 3.8.x SIREN报告可读性+时区 | 3.7.0 AKE(BSC) | 3.6.0 SIREN(BSC) | 3.5.0 ASTEROID(ETH)+逢5整编
- 3.4.0 VIRTUAL(Base+ETH) 多链 | 3.3.0 体检修复 | 3.2.0 监控包按需化 | 3.1.0 成本三刀 | 3.0.0 稳定化
- 2.29.0 jesse(Base) | 2.28.0 哈基米(BSC)
- （3.11.3 及更早正文 → CHANGELOG-archive.md：3.10.0–3.11.3 五条系 2026-07-23 v3.25.0 逢5整编滚动归档，3.9.0 及更早 61 条含 3.6.0 补档）

## [3.28.0] - 2026-07-24 — GOAT(Solana) GPT5.6 外部复核裁决采纳（外部复核采纳专项，非分析复盘）

> 用户送来 GPT5.6 对《GOAT筹码筛查_2026-07-22》（easy 模式）的独立复核。所有关键指控在采纳前均按"禁报告自证"原则回原始落盘数据独立复验，**量化指控全部坐实**：①小庄三址 gas_origins 记录 `my_sol_delta` 全为 0（目标没收到 SOL，86KSd 仅为 Jupiter DCA 执行 tx 的 fee payer），且同文件里 86KSd 还服务被单列为"独立定投户"的第四址——反例就躺在自己的数据里；②analysis-state.json 三处保留被正文复核撤销的旧叙事（狙击集团 P1 20.69%/make_state.py SNIPER 硬编码/P0"低位归集运营"status/离场庄 2 址 vs 正文 5 址）；③compose_evolution.py 读去重前发射窗（dedup 版就在旁边）；④whale_htv 恰触 2,000 笔上限仅覆盖 48 天，"60,000 枚定额轮发"在落盘流水中出现 0 次（最常见 200,000×315 次；该证据来自复核时对 Am8MAE 三中转的临时追查，全部未落盘）。
>
> **病灶三层**：一层=注资边根本性质误判（fee payer 当 funder，规则缺失——methods §117/§118 已有的三步体检与反向索引也都没执行）；二层=复核翻案环节自身产出的新定性（调度商）不受落盘约束（制度盲区——§10 只约束怀疑者"自己重算"，没约束翻案证据的可复现性）；三层=复核修正传播链只覆盖"图表/表格/正文"三处，机器交付件（state/生成脚本/下游作图脚本）系统性漏改。
>
> **判定分布**（对本方报告）：REFUTED 9 / WEAKENED 5 / CONFIRMED 5（供给闭合、末日阵营算术、P0 三址同控与 24.31%、离场庄严格两址、发射窗限定口径全保留）。**不采纳 4 项矫枉过正**：稻草人（"谎称全量重放"——图注早已声明混合口径）、时代错位（entity_id 系 3.19 引入晚于 GOAT）、规则发明（"静置仓反扫规则/dormant_warehouse_audit.json"skill 中不存在）、Alpha 黑箱推论（9ZPsRW 行为学托管仓已计入 0.66%，集齐率方法论支撑"该仓份额≈黑箱"，仅吸收论证链书写义务）。
>
> **写入（6 处）**：methods 注资边先决字段闸+三步体检两补强；address-book +2 Jupiter DCA keeper；evidence-wording §10 第 11/12 条+对照表 3 行；easy-workflow 交付前一致性硬闸+判定块④理由纪律+阴性覆盖披露；state-anomaly §9c 取证落盘义务；report-template 混合重建图注两条。**GOAT 案侧**：analysis-state.json 按裁决重建（狙击集团删除、小庄三址拆回独立、P0 status 降级"高频转账/结算体系·调度商高度疑似"、离场庄 2 址+扩展口径注记），原版备份 `analysis-state.pre-review-20260724.json`；记忆存档同步改写防旧结论复引。

## [3.27.0] - 2026-07-24 — SIREN(BSC) GPT5.6 外部复核裁决采纳（外部复核采纳专项，非分析复盘）

> 用户送来 GPT5.6 对《Fable5 SIREN 2026-07-19》的独立复核（其以本地全量 parquet 独立逐笔重放）。对本方报告判定：**REFUTED 2 / WEAKENED 4 / CONFIRMED 4**（背调/水军/CEX 充提/获利/LP 不在其复核范围）。所有指控按"禁报告自证"在采纳前独立复验：Sourcify 实锤 `0x2aa5…a351`＝**Hedgeys**(exact_match)、`0xb1c5…6699`＝**BatchNFTMinter**；state 复数确认离场庄并集 **1,129**（1,036 核心+93 扩展）且两 Hedgey 合约在核心成员表内；balances_final×成员表复算残仓 **1.41414%** 与其完全一致；自有日线序列 2025-08-07 恰为 2025-07~09 窗口局部最高日，与其复算的核心链真峰值日精确同日互证。
>
> **最重翻案（REFUTED）**：报告的"归集主仓＝庄家的单一大钱包"“专用原子转发合约……私人通道反成归属铁证"实为 Hedgey 公共锁仓协议+BatchNFTMinter——中层机制叙事"归集→903/903 wei 级等额原路返还洗仓换代"实为"批量锁仓 905 份→到期机械赎回＋赎回后真实换仓（47 个 gas 同源三代钱包）"；报告用等额返还"排除 OTC/托管重组备择解释"，被排除的托管类恰是真相，论证方向整体反转。**保留（CONFIRMED）**：21,689,815 条重放供给闭合、体系峰值 68.69053%@2026-02-06 数值与时点、903 受益地址高度协同（行为层）、图 2 六月离场方向（复核方自认其原图二月归零系位置账当经济账的制图错误——歪打正着机制：本方错误吸入协议地址反而使位置账≈经济账）。**WEAKENED 采纳**：单一所有人确权降级为"核心可证下限 48.41~50.18% + 强关联体系上限 68.69%"双端点；"核心链单口径峰值 48.4%"实为扩展峰值日构成值（核心真峰值 48.53%@2025-08-07）；"≈流通盘 94.9%"分母实为非销毁供给；残仓 1.44% 与 state 1.41414% 不同源。
>
> **未采纳（假错误/过苛）**：①复核方"必须已核验流通盘（再扣池/托管）才可称流通盘"——meme 币"总量−销毁"是通行流通口径，采纳一半＝分母命名义务；②"1.44% 精确性"单独批评——真病是编译化前手写不同源（facts G1/G5 已架构性覆盖），不另立条；③其原图二月归零与其 50.18% 漏历史静置仓反扫系复核方自认错误，与本方无关，仅取其"三账分开"病例价值。
>
> **写入（4 分册 6 处）**：methods 四测④币种内视角选择偏差首实锤+pool-probe 硬闸扩"锁仓/vesting 协议"必查类+归属证据学"等额原路返还"例证修正（指纹准入前置=排除协议机械行为）；report-template 三账本第三案（锁仓协议版）；evidence-wording 口径三件套+对照表 2 行。SIREN 案侧：analysis-state 成员表含两 Hedgey 合约不回改（离场废墟无监控、不再 update），记忆存档写明翻案防旧结论传播。
>
> **标签库污染清理（0x238a/QUQ 同型第三次事故，照 3.19.1 章程）**：SIREN 1,129 址成员表 07-22 整表回灌惯犯层，两个 Hedgey 合约随批被标"惯犯庄家"入主库——**任何用 Hedgey 锁仓的 BSC 项目都会被误提示庄家介入，污染面最大的一次**；讽刺对照：miss-queue 07-19 已排入这两址且备注"deg=905 疑似路由/分发设施"（正确直觉无人跟进，反被惯犯流水线覆写）。处置：`curation_overrides_20260724_siren.csv` 两条（0x2aa5=**locker**/exclude Hedgey TokenLockup、0xb1c5=infra/exclude BatchNFTMinter）入库压制+自动归档 additions/；serial_actors.csv 与 miss-queue/bsc.csv 各显式删 2 行；**INFRA_CATS 硬闸补 `locker` 类**（原集合漏锁仓类=本案暴露的硬闸缺口，FlokiFi 等 29 条 locker 行自此同受保护）；benchmark PASS（错误 exclude=0）+manifest 落印。**遗留 TODO**：serial_actors 内 SIREN 其余 1,127 行中扩展 93 址系"强关联未确权"（GPT 复核 WEAKENED），语义偏强但均已离场清零、误伤面小，不清理；additions 历史批次两文件保留原貌（重放被 curation 压制）。

## [3.26.0] - 2026-07-24 — QUQ(BSC) GPT5.6 外部复核裁决采纳（外部复核采纳专项，非分析复盘）

> 用户送来 GPT5.6 对《Fable5 QUQ 完整版 2026-07-22》与《Codex QUQ 2026-07-23》的独立复核。对本方报告判定：**REFUTED 5 / WEAKENED 2 / CONFIRMED 3**。所有 REFUTED 项均按"禁报告自证"原则在采纳前做了链上/本地数据独立复验——四 selector RPC 证实两"bot 合约"为 Pancake V3 QUQ/USDT 池（fee 100/10000，factory=Pancake V3 Factory，code 22962B；顺带发现 e1ac"V3 主池"factory=Uniswap V3 0xdb1d1001…，即 QUQ/USDT 系 Uni V3+双 Pancake V3 三池并存）；本地 cmc_chart_all.json 证实全史 ATH $0.008875@2025-03-22（所写 $0.004798 仅 2026 段区间高点，且 cg_price_max.json 落盘的是 error 响应无人拦）。

**被推翻的五条与病灶**：①两公共池判 bot（同模板 22962B 被读成"同一服务商指纹"，而它首先是同 factory 标准实例——三测无池探测+部署时间测试对池类失效的组合盲区）②215 址同控层（公共池/路由/EntryPoint 混入成员表）③793 址 P1 狙击集团（行为 cohort 实体化，附录自注"含路由独立用户"却仍标集团）④V4 手续费不可算（混淆"单笔提现不可拆"与"账本不可重建"）⑤假 ATH（窗口高点越界+错误响应文件未拦）。**保留的三条**：经济控制口径 64.6% 方向（钱包 27.81+V3 19.22+V4 17.60，V4 精确值待逐头寸闭合）、strict 四址 EOA 核心（2,718 条内部 Transfer+V3 NFT 所有权）、07-22 币安钱包入口 95.6% 订单流拆解。

**写入（7 处）**：methods 三测→四测+同模板语义修正+pool-probe 准入硬闸（复核者对成员表合约独立重探——本案 R2 翻 449e 却漏两池的正交性病根）；state-anomaly §9b 二次修正；channels V4 单例禁归庄+V4 费可算改判（修 3.22.0 旧条）；tiering cohort≠实体；evidence-wording ATH 通道纪律+账号≠真人+对照表 2 行；report-template 三账本分离口径宪法（economic_control_ledger 候选交付件）。QUQ 案侧同日：监控地址表按纯 EOA 庄组+设施独立哨重梳，appendix.json 与报告附录 E 同步重写。

**标签库污染清理（0x238a 同型二次事故，处置照 3.19.1 章程）**：QUQ 214 址成员表 07-22 曾整表回灌惯犯层——两池与 **ERC-4337 EntryPoint v0.7** 均被标"惯犯庄家"入主库（EntryPoint 系 3.19.1 硬闸漏网：其时主库无该址设施身份可比对）。处置：`curation_overrides_20260724_quq.csv` 三条（两池=dex/exclude、EntryPoint=infra/exclude，均落 INFRA_CATS 受硬闸保护）入库压制；appendix 改四址后重跑 accumulate_offenders，QUQ 批次 214→strict 四址（含 1a29 补录）再入库；benchmark PASS+manifest 落印。**遗留 TODO**：主库仍残留 ~210 条 QUQ 未确权成员的"惯犯庄家"行（upsert 删不掉、additions 历史批次重建会回放），待下次 /token-update 成员表重建出确权名单后做批次撤回；miss-queue 候选 2 址（0x00000000ae2193c4…/0x00000688768803bb…，vanity 疑公共设施未确证，暂不 curation）。

## [3.25.0] - 2026-07-23 — BANANAS31(BSC) easy 三战复盘 + 逢5轻整编

> easy 模式三战（QUQ/GOAT 后首个 BSC four.meme 毕业币标的，609 天币龄、1037 万事件/24 万地址）；E0b 前置 CEX 黑箱关卡 BSC 版首战（17.2% 过关继续）。本次采集通道被本机网络连环卡（v2 直连挂→代理 stall），分段采集解法与混通道归一是最大工程沉淀；方法侧最大收获=§9c 调度商跨链第二案转正 + 三个复核翻案模式（块时长折算/迁移窗误判出清/同尾数降格）。

**新数据源/通道（channels 分册，直接正式）**：
- §3.1 v2 官方客户端本机网络三态：直连必挂（大响应被网络层掐，curl 小请求过——探测通≠采集通）/clash 代理可用但长连接偶发劣化 stall（168MB 卡 16 分钟）/解法=分段采集 `staged_capture.sh`（段级独立 run/done.json 幂等+retry-once；无 done.json 的 parquet 无 footer 不可读须整目录清）；v1 轮询+代理最稳兜底（91.2 万行 34 分钟零 429）；混通道归一=v1 CSV 转标准 v2 parquet run 段、roundtrip 零差集验证后 replay_duck 段界互斥合并
- SQD Portal 对账关卡查3 双源对照 BSC 数据点：四代表日 67,731 行 (block,tx,li,from,to,value) 六元组与 HyperSync 零差集全等
- §6 坑表 +3：Alpha 转正币（listingCex=True）Router 托管清空迁移、无 Alpha 黑箱按普通 CEX 口径；BSC 历史段块时长≠现值（2024-11=3s/块），时间叙述必用块时间戳差（复核抓出 27→81 分钟传播级错误）；four.meme TokenManager bonding curve 双向回流、毛流出可超总供应（153.5 亿>100 亿），发射窗判定禁毛口径

**方法修正（playbook 分册）**：
- state-anomaly §9c **CEX 间库存调度商【候选→正式】**：GOAT(Solana)+BANANAS31(BSC) 跨链两案独立复现；BSC 亚型=归集在途仓（等额散址归集→在途仓→直充所，峰值可达链上前三大仓、终态清零）；新增衍生口径义务：调度商在途仓默认落散户桶→CEX 托管曲线系统性低估，识别出调度体系须注记受影响时段
- state-anomaly §7 离场/出货时点必以真实处置流水（DEX 卖出/充所）定位：余额从名单消失≠离场（等额转移=迁移/重组）；实锤=70 分钟"出清窗"复核发现窗内 DEX 卖出为零、实为协同迁移窗，真实出货在前两周切片卖出——迁移同步性反是最硬协同证据（"标准迁移"判据从更新场景扩展到初判场景）
- methods 小额测试指纹补强（机制二见）：10 枚测试→3-4 分钟全额跟进，一对二 SOP 可合并两簇；跨簇秒级交替时序=待证关联强信号
- methods 【候选·单案】同尾数批量提币=「同批次」指纹非「同人」指纹（CEX 固定手续费机制；体系外同尾数反例同日独立清仓实证）——同人判定必须行为协同独立支撑
- methods zero-value transferFrom 投毒串簇：0 额伪造 Transfer+仿冒前缀把投毒对手方带进 BFS 簇并虚增 profile 度数；一切聚类构边 value>0 过滤
- tiering 【候选·单案】狙击集团 bundle 阴性≠非协同：建仓形态两型（捆绑原子型/程序化连续扫货型——逐块鱼贯进场无同块原子性），"捆绑发射"措辞仅授予第①型
- evidence-wording 截断地址第七犯追加：复核材料截断输出补全 2 址后 32 位全错、落盘反查抓回——反查时点前移到"首次誊写进任何产物（含 findings/实体表）"之前

**easy-workflow**：E0b BSC/EVM 版首战入册（~30 分钟：GMGN top100+标签库盲化认所+HyperSync 三层溯源，方向判定"提出出所→链上囤仓"不算黑箱；先例行补 BANANAS31 17.2% 过关）+方向判别补强（提出方向≠非所方，须叠加跨币种画像：单币种纯收零 gas=私人仓/多币种大额高频=疑似所方运营仓）；E4 前先落 analysis-state 骨架（cluster_sensitivity 依赖）；成本基准三战行（~2.5-3h 含通道折腾，2-3h 档守住）

**脚本**：staged_capture.sh 参数化收编（scripts/evm/）；cluster.py+cluster_prep_duck.py 双路 0 额边过滤（同口径补丁，投毒免疫）；report-template state 供给字段 human 单位注（曾 wei 再除 decimals 双重计）

**轻整编（逢5）**：CHANGELOG 滚动归档 3.10.0–3.11.3 五条正文→archive（原样未改写）；candidate 存量清点=本次 §9c 转正 1 条、其余入库未超 8 版无降档；docs lint 全过

**成本指标**：交付用时 ~2.5-3h（21:0x 开工→23:47 交付；主会话轮次/Bash 数未记录——easy 会话未带指标落盘，下次案随 findings 记录）。**质量指标**：初稿关键结论 6；复核判定 CONFIRMED 3 / WEAKENED 2 / REFUTED 0；复核翻出漏检实体 3（F1 MEXC 调度体系=历史第三大链上实体、小庄 S 同模式外延 ~4.8%、狙击续持漏网 1 址）；传播级数字错误 4（发射后 27→81 分钟块时长折算、CEX 峰值 34.19%→37.89% 单日值误读、项目方"加流动性"实为先卖 1 亿枚变现路径改写、state supply 单位双重计）

## [3.24.0] - 2026-07-23 — SIREN(BSC) 全案元复盘：当分析者成为错误的辩护人

> 复盘对象=07-19 主分析+07-20 交付后全天追问链（主分析方法已入 v3.6.0，可读性/时区验收已入 3.8.0/3.8.1，配平自检与日期陷阱已入 §10.7/§11——本条收 07-20 讨论中此前未入册的四件+跨案回填）。SIREN 与 QUQ 的追问链完全同构且 SIREN 在前：守恒加法（15.2pp 去哪儿了）、口径追问（49.3 含不含四仓）、常识质疑（割裂的所价格为何一致）、时间线对齐（K 线 9-10 点才崩）——v3.23.0 第一性五问的史前第一案。双案对照的两个硬观察：**教训入库后同类追问在下一案确实消失**（时区/术语/图在 QUQ 零追问=闸门有效）；**新面孔的口径/守恒错误照样出现**（SIREN 修配平、QUQ 出 TVL 伪影）——具体错误修补堵不住错误类型，只有类型化交付前自检能前置拦截。全景过程档《复盘_SIREN追问翻案链_2026-07-23.md》在案目录（9 轮追问对照表+"错误纠正的 20 分钟"专章）。

**supply-recon 口径质疑回应纪律升级（正式）**：拆数必须**回原始数据现算**，禁止转抄报告口径自证——报告是被审对象不是证据；错误若源于同一次漏改，图/正文/表格是同源复制、"三处一致"零证明力。配套：用户复述求证是高信号输入，复述与报告的每一处冲突按"读者错/报告错"双向可疑逐处回数据裁决，不允许默认报告对。完整反例：SIREN 复述求证环节用户"49.3 不含四仓"的理解本来正确，分析者引用报告修正表把它"纠正"成错误方向，20 分钟后被用户 65.9−49.3−1.44=15.16 的加法推翻——rug 净出实为 64.5pp，报告与"纠正"双双认账。

**entity-cluster-methods 新增「归属证明的证据学」（正式）**：BFS 扩散类聚类的答辩标准件——①层数封顶原理：转账图全连通，层数越深"可达"含金量越低（碰公共设施再一步即通向数十万无关户），**穷举更多代数是稀释证据不是加固**，4 层封顶+公共设施截断；②归属证明的本质=只有同一控制者才做得出的动作组合（N/N wei 级等额、分钟级多所同步、同凌晨注入同一执行网），不是"钱能流到"；③**双向合龙**：自上而下 BFS 与自下而上池子反向穿透两条独立证据链中间重叠，≫ 单向穷举（单向可被质疑"挑路走"，合龙不能）；交集外成员由行为指纹补焊。

**state-anomaly 新增两节**：§5a 封闭盘定价结构（正式）——割裂≠孤岛：币的通道断但人和钱（USDT）通，双边库存玩家无搬运套利把各所软连接成一个封闭联合体（断的是联合体↔链上的桥）；小所行情先用链上托管库存过滤（镜像盘复读机，CMC 星号/双星号剔除标记旁证）；残留价差 ~1% 双向印证（压不到 0.1%=硬搬砖断、收敛不发散=软连接活）；价差梯度=通道断裂梯度；封闭盘冻结价=市场死了非价格稳。§9d 可人为触发的叙事开关【候选·单案】——给公开人物送币赌其例行处置（销毁），处置动作链上可见被截图传播="互动即背书"，谁都能按的开关；备货完成与引爆日的时间锁扣单独陈列、"策划者=庄家"须独立举证；联动 §11：引爆日可以是死料翻出日。

**§10b 回填**：守恒加总问、口径三要素问补 SIREN 第一案来源注记（跨案两实证成立）。

**质量指标**：本条为元复盘无新初稿；07-20 讨论 9 轮追问全部入册核销（2 翻案+1 深化+2 验收硬性+1 时区+3 衍生），未入册遗留=0。**成本指标**：会话考古 10 个 jsonl 重建时间线约 40 条独特消息；零采集零付费。

## [3.23.0] - 2026-07-23 — QUQ(BSC) 全案元复盘：把"用户追问"内化为流程

> 复盘对象=07-22 全天的 12 轮"追问→翻案"链（v3.22.0 沉淀了其中的具体方法，本条沉淀过程层教训）。核心发现：**12 轮交付后翻案中，五路对抗复核提前抓住约 1.5 条，用户的五类朴素追问命中 5/5**——原因是复核者与主分析共享同一落盘数据集与同一 Transfer 图视角，翻案所需维度（tx 发起人/外部源对账/制度情报/费率真值）不在数据集里，重算百遍也看不见；用户追问全是不依赖数据视角的**不变量检验**（守恒/数量级/动机/口径/真值），与复核维度正交。全景过程档《复盘_QUQ追问翻案链_2026-07-23.md》在案目录（12 轮对照表+错误根源六类：聚合器盲信/视角盲区/口径缺陷/动机脑补/前提未传播/复盘班车滞后）。

**evidence-wording 新增 §10b「交付前第一性五问」（常识审计，发布前最后一道闸）**：
- 守恒加总问（正式）：互斥口径份额加总 ≤100% 自检；**外部聚合器前端存量数字=别人的分析结论，入报必过第一方账本复算**（GT 逐池 TVL 幽灵仓被"加起来超总量"一问引爆的教训）
- 数量级闭合问（正式）：N 主体×单体行为 vs 宏观总量，缺口 >30% 必拆（拆解常顺带产出更干净口径——"全天 0 笔 ≥$10 万"金额铁证即副产品）
- 动机自洽问【候选·单案】：行为归因讲不出"它图什么"=归因红旗，禁叙事填空；与"行为可证意图只能推断"互补（那条管别乱写动机，这条管动机写不出）
- 口径三要素问（正式）：TL;DR 级数字逐个过范围/性质/时效（双边费单边算、已撤设施旧归属、想当然参数三类实锤）
- 真值探针问【候选·单案】：分析者/用户自有真单当 ground truth 校准路径与费率
- 附则一【候选·单案】：**用户假说是正式输入**——产品侧/交易侧怀疑当 hypothesis 跑数据，链上数据里没有产品知识；裁决两头不迁就（证实/证伪/第三答案均有实例）
- 附则二（正式）：**前提翻案的传播义务**——前提倒掉后点名重查依赖它的下游结论（"量是庄刷的"倒了，"费大头自付"必须跟着倒）；与账目配平自检并行：数字传播 vs 逻辑传播

**monitoring-package 投后运行纪律 +2（正式）**：
- **庄组成员第一性原则：只放会自己走路的地址**——合约无私钥不自主转账，其转出永远是调用者订单流；自有池/执行器/路由/托管 Vault 产权再明确也不进庄组（入组=把全市场客户流量算到庄头上，"疑似倒仓"滚成 361% 且无法消音；改纯 EOA 后真信号语义反而变纯）；设施用独立哨，修法走 manual-watch 源文件由 monitor 自动重建
- **"庄在动"类报警先归因分解再定性**——发出方身份（EOA/合约）×接收方期末留存两维拆解；"合约发出+期末归零"=客户订单流足迹（18,290 笔报警 100% 合约发出、庄 EOA 仅 1 笔尘埃，"摆深度"定性当面收回，连委托人本人买单都被计成庄倒仓）；速读口诀：看到推送先看发出方——池子或合约=营业流水划走，库存 EOA 动了才是庄的手

**retrospective 复盘完备性两道硬检**：修正对照表逐行核销（复盘结构性偏科只沉淀最后一段工作——最大翻案群曾滞留 retro_notes 靠用户贴表追问才入册）；candidate 清账扫描（复盘 commit 后新增 candidate 滞留 retro_notes，下次开工先 grep 清账+git status 查漏提交——v3.22.0 变更隔夜未 commit 由本会话补班车实证）

**质量指标**：本条为元复盘无新初稿；对 07-22 案的复盘覆盖率自查=12 轮翻案全部入册核销（v3.22.0 覆盖 8 轮方法+本条补 4 件过程层）。**成本指标**：纯会话考古与写入，零采集零付费通道；跨 9 个会话 jsonl 重建用户追问时间线约 26 条。

## [3.22.0] - 2026-07-22 — QUQ(BSC) 投后专项复盘：币安 Alpha 制度侧特征 + 全史量能考古

> 非完整分析复盘——买入后投后阶段由用户连环追问驱动的两条战线沉淀：①币安 Alpha **制度侧**（积分倍数/政策线/量能断崖归因），与 3.20.0/3.21.0 的托管体系（链上侧）互补成完整 Alpha 排查面；②发射以来全史成交量硬算工程。全部入 data-pipeline-evm-channels.md §6 表（+6 条目）。

**币安 Alpha 制度侧三件（直接正式）**：
- **mulPoint 积分倍数直查**：Alpha 全量表 bapi 每币带 `mulPoint` 当前积分倍数（2026-07 实测 645/656=1x、11 币=4x 全是 30 天内新 TGE）——Alpha 标的量能判读第一步；⚠只有当前值，历史轨迹靠政策线+快讯/推特回溯
- **积分政策时间线锚点+量能断崖三因鉴别**：2025 年中 BSC 全板块 2x → 2025-09-04 取消（改新币 30 天 Points Plus 4x）→ 2026-07-22 Alpha CEX 限价单买 BSC 币 4x。断崖归因三分：个币处分/板块政策/**竞价性分流**（刷分量=「倍数×磨损成本」性价比函数，新载体出现即迁移）；鉴别三件套=mulPoint+对照币同窗 GT 日量（同跌=板块性）+xapi 断崖窗口±3 天刷分社区实时讨论（中文带引号词组零命中坑）。案例：QUQ 07-14 单日腰斩后 8 天窄带平稳（窄带新平台=新配额指纹），判分流非处分（对照币同窗 -93% 更狠）
- **场内↔链上量能迁移互斥+监控防误读**：场内有倍数/磨损优势时链上 DEX 量可整段归零而需求未死（QUQ 案 2025-08 下旬链上 $0 恰为场内托管峰期，09-04 政策反转量才迁回链上）；监控三推论=①链上量崩先对政策线勿直判需求死亡 ②政策利好窗"向 Alpha 托管/寄存仓大额转移"优先判搬场内复业非出货（辅证=结算桥双向仍活跃+无 CEX 出金链）③上架早期量可能全在场内、全史链上口径系统性低估须报告声明

**量能考古工程三件（直接正式）**：
- **全史 DEX 成交量池腿法**：POOLS 含 V4 PoolManager 单例，单边口径、池↔池自动排除、LP 剔除=lp_events mint+collect（burn 无 Transfer 勿剔）；价格三源拼接（CG 365d+DefiLlama 逐日早期+GT day 仅 181 天）；**费反推独立交叉验证器**（V3 全史 collect−burn 双边费÷费率=名义成交额 vs 池腿实算，QUQ 案 103% 吻合；CG 聚合口径偏高 ~1.2x 属正常）
- **transfers_lib 整表读大 parquet 必 OOM**：`pq.read_table` 载 6.6GB/亿行级直接 SIGKILL——自写 `iter_batches(20 万, 4 列)` 流式 <1GB 内存 ~2 分钟/亿行；日期整数日聚合、跨 run 块边界去重（亿级 set 去重内存不可行）
- **V3/V4 LP 费口径鸿沟+swap 回执速查**：V3 费=collect−burn 硬数**且双边各收**（只算 U 侧漏报一半）；V4 费并入头寸无硬数只有净现金流（应计估算须声明）；回执速查=V4 腿对手方必是 PoolManager/`fee()` 0xddca3f43 直查/拆腿输入和 vs 付出额验路由抽成（b300 实测零抽成）

**同日补录：v2 修订翻案方法群（昨夜平行会话产出，用户对照表点名后补全入册）**：
- entity-cluster-methods +2 候选：**订单流成色拆解四步**（"庄对倒/自转/左右手"定性前强制前置——tx.from 发起人构成/4337 EntryPoint UserOp sender 拆壳/2^n 美元档位分桶（路由拆单后整档统计=下限）/高峰时段体系库存对照；QUQ 案"日成交 90%+ 庄自转"→"约 95% 外部刷分订单流"结构性大翻案，连带作废"一次性合约=马仔"与"调度服务器操作手册"叙事——数百个单笔生命周期合约实为币安/LI.FI 路由 per-tx 执行中间件）；**独立量化/MEV 工作室三重判据**（资金隔离+起源早于标的+多币服务面→第三类桶"独立承接方"，不并庄口径但必须单独陈述，金库撤墙=承接方撤出领先哨）
- channels +2：**GT 逐池 TVL 伪影+V4 幽灵仓+LP 归属定池属**（V4 头寸可转移致 (pool,tx_from) 聚合出幽灵仓，硬口径=receipt 净现金流；池属以当前 LP 归属为准，体系撤离后的池从控制口径摘出）；**同 tx 等额配对裁决法**（配对率≈100%=原子过账管道非仓库，"专用性未决"枢纽结案件）
- monitoring-package 新增**投后运行纪律**节 5 条：口径翻案三处同步（appendix/看板组名单/哨位）/通道集喂监控组前逐址过 label_lookup（公共设施吸入教训+假阴性坑）/制度哨可升头号哨/第三方承接哨单列/毛量净量判读口诀（"疑似倒仓"推送核查标配）

**质量指标**：交付前修正 2（口径天数 450→489 顺嘴粗算被复算纠正；断崖归因从"疑似积分下调"假设修正为"竞价分流"——对照币+社区实录+挽回新政三证闭环）；交叉验证 3 路全咬合（费反推 103%/CG 83%/GT 当前量一致）。
**成本指标**：投后连环问答约 6 轮；全史扫描 1.03 亿行约 2 分钟（流式重写后）；外部调查全走零付费通道（bapi/WebSearch/WebFetch/xapi/GT/DefiLlama），Firecrawl 未动用。

## [3.21.0] - 2026-07-22 — PENGUIN(Solana) easy 四战 E0b 关卡中止复盘：币安 Alpha 链上托管体系首次实锤 + Alpha 集齐率判别法

> easy 模式第四战、E0b 固化（3.20.0）当天的首次实战复用，第三例关卡中止案（先例序列：QUQ 过关/GOAT 过关/Fartcoin ~48% 中止/CLANKER 37.6% 中止/本案严格 35.69%）。全程 ~55 分钟、~35 轮次、零付费 credits（Helius+Vybe+GMGN+GoPlus+bapi+WebSearch 全免费通道）。用户创新**两轮问询制**：初判报数（确证 15.03%+高度疑似 32.06%）→ 用户不直接裁决、令先深挖"高度疑似"档 → 升格核查（1 升格接近确证/1 改判剔除/2 维持）→ 终裁中止。质量指标：关卡实体判定 10、深挖修正 2、漏检 0 已知、传播级数字错误 0。

**币安 Alpha 的 Solana 链上托管体系（本案最大发现，接近确证，address-book +4 址+1 程序）**：三层结构=库存仓（`9ZPsR…`，PENGUIN 20.66% 第一大持仓，381 种持仓集齐 66/70 个币安 Alpha Solana 币=94%，另为 HAT/PYTHIA 等多 Alpha 币第一大持仓，SOL≈0 gas 全代付）↔ 执行仓（`6ZaWyb…`，124 币种余额常态≈0，与库存仓单进单出高频对倒）↔ DEX 池（执行仓直连 PumpSwap/Orca/Meteora 双向买卖）＝币安 Alpha「App 内下单、链上 DEX 执行」机制的链上形态；专用结算走 `BN111…` vanity 可升级批量程序（2025-03 部署持续维护，fee payer 4 址轮换代付）；旁证=币安主热钱包/双冷钱包 PENGUIN 持仓全零（敞口全走 Alpha 体系，与 listingCex=false 一致）。**含义**：Alpha 在架 Solana 币的"最大神秘巨鲸"优先怀疑此体系——它不是庄，是场内黑箱（真实持有人在币安 Alpha 账本内不可穿透）。

**Alpha 集齐率判别法（pipeline-solana-scan §3 新条目）**：对多币种高频大仓，getTokenAccountsByOwner 全持仓 × 币安 Alpha bapi 全量表取交集一次分档——~94%=Alpha 专属托管；3-8%=通用热钱包；≤2%（仅标的自身）=做市/bot。本案四仓实测 94%/3%/8%/2% 四档分野清晰无重叠，比"多热门币最大持仓者"老判据多一层归属定性能力。

**E0b 条文迭代（easy-workflow）**：三通道认所补第④步——币安 Alpha 在架的 Solana 标的先对撞 address-book 已知 Alpha 托管体系地址，未命中再对未认大仓跑集齐率判别；冷储分仓 trace 调度枢纽打法二连验证（本案 Bybit 冷储分仓 0.90% 由已认 Bybit 热钱包 authority 供币实锤，与 Fartcoin 案 Coinbase 热3 调度同构）。

**执行侧记录**：gmgn-cli 实际装于 `~/.npm-global/bin/gmgn-cli`（登记文件写 gmgn 系笔误）且 holders 参数为 `--chain sol --address <mint>`（位置参数不认）；Vybe top-holders 正确路径 `/v4/tokens/<mint>/top-holders`（`/token/...` 404）；solscan 页 WebFetch 403+内置浏览器 preview 超时双失效，公开标注检索改走 WebSearch 地址串反查（本案借此发现 9ZPsR 是 HAT/PYTHIA 第一大持仓）。

## [3.20.0] - 2026-07-22 — Fartcoin(Solana) easy 三战黑箱关卡中止复盘：前置 CEX 黑箱关卡固化 E0b + Solana CEX 地址资产

> easy 模式第三战，首例在前置关卡即中止的案子（先例 CLANKER 为 E0 后中止）：用户附加「CEX 托管黑箱 >20% 流通须问询」，实测确证 36.97%+高度疑似 11.15%≈48%，用户裁决中止，未进入采集。全程 ~40 分钟、零付费 credits，落盘数据资产八件备重启。

**流程固化（easy-workflow 新增 E0b「前置 CEX 黑箱关卡」）**：连续三案（GOAT 两轮问询过关/CLANKER 37.6% 中止/本案 48% 中止）用户在命令里手写同一要求→固化为用户点名时的标准步。五动作：①GMGN top100 --raw（native_balance/流水字段即行为画像原料）+RPC top20 owner 映射互验 ②三通道认所=本地标签库(盲化)+Vybe v4 top-holders ownerName+历史案 cex_map/address-book 合并表 ③行为画像分层补认——热钱包画像（百余币种+万级 SOL+大额双向流水）与冷储分仓形态（SOL=0+个位数币种+纯转入+金额相近），后者 trace 对手方找统一调度枢纽，命中已知热钱包即实锤归属（本案 11 分仓×Coinbase 热3 调度=13.02% 一锅端）④确证/高度疑似两档分层报数+桥型托管单列（Hyperunit 可跨 HL 穿透）+Solana CEX 标签缺口纪律注记 ⑤超线 AskUserQuestion 引先例停等；中止则 findings.md 存档+数据留 data/，不交付两件套。

**地址资产（address-book Solana CEX 节 +3，均 2026-07-22 行为核验）**：`9SLPTL41…`=Hyperunit 热钱包（HL 现货桥托管，凡 HL 上架 Solana 币必遇；200 币种/28 万 SOL）；`D89hHJT5…`=Coinbase 热钱包 3（404 币种/4.7 万 SOL/分钟级高频；**冷储分仓调度指纹**入备注）；`6LY1JzAF…`=Kraken 热钱包（Vybe+GOAT cex_map 双源；274 币种/38.7 万 SOL）。

**执行侧教训（均为已在库规则的再犯，不新增规则）**：①前置关卡开工未先读当链 pipeline §4 辅助数据面→Vybe top-holders 端点（3.11.0 已固化含虚高坑）重复试错重新发现，白烧 2 轮；②「关键字符串从打印输出复制」坑第 N 犯——GMGN 输出截断地址手工补全致 7 地址查空，返工一轮后改从落盘 JSON 取全（E0b 文本已带此警句）。

成本：~25 轮 / ~20 Bash / ~40 分钟 / 付费 credits 0（Vybe 1 调用免费层）。质量：中止案无分析结论；关卡产出=确证 11 所 36.97%+疑似 8 仓 11.15%，Coinbase 分仓网实锤为本案唯一深挖发现。

## [3.19.1] - 2026-07-22 — serial 回灌设施冲突硬闸+curation 增量覆盖修复（0x238a 裁决执行）

> 3.19.0 A7 冲突检测首战抓到的 QUQ 误吸 PancakeSwap Infinity Vault（`0x238a…bad5e6c4` bsc）覆盖事故，用户裁决三条组合拳，当日执行完毕。

**裁决执行（三条）**：①主库恢复设施身份——`sources/additions/curation_overrides_20260722.csv` 入库（protocol/exclude/no_merge/exclude，与 Uniswap V4 PoolManager 同构语义固化），发布行 serial-actor→protocol，benchmark bsc manual 召回恢复 168/168；②QUQ 案侧 state+appendix 双档摘出成员表 215→214、组 note 追加裁决注记（该址终态余额 1.5 万枚占总供给 <0.00001=纯流经关联误吸指纹，份额口径影响可忽略；camp_share_series 与份额数字注记"下次 /token-update 重放校正"）、findings.md 落裁决记录、additions 归档同步净版；③`accumulate_offenders.py` 设施级硬闸——detect 前移至写 CSV 前，primary/goldset-infra 级冲突地址拦在 serial_actors.csv 外（--apply 与手动 add_labels 两条入库路径一并挡住），secondary/cross_chain 仅提示；裁决三路径固化 docstring/README/冲突报告 note（①修案源重跑 ②curation override ③确属庄家自建设施→手工编辑 CSV 单独入库，绕闸必须人工显式动作，无 --force 参数）。

**顺修真缺陷（curation 增量覆盖失效）**：`add_labels.py` HIGH_TRUST_PREFIX 原为 (manual, registry, serial, official)——**缺 curation**，导致最高层（build_labels SRC_PRIORITY=-1）的 curation override 走增量入库时只补空字段、压不掉已存在的 serial/manual 行，增量与全量重建覆盖语义不一致（0x238a 恢复实测踩中）。已加入并注明成因；今后 curation 精修一律可增量生效，无需全量重建。

**测试契约翻转**：test_cluster_quality T2 由"冲突不得阻塞候选产出"改为硬闸语义三断言——primary/goldset-infra 必须不在 CSV、干净地址必须在（不误伤）、stdout 必须明示拦截。全家桶 12/12。

## [3.19.0] - 2026-07-22 — 质量/速度/稳定性专项第三批（非复盘专项，@CX 三轮 18 项）

> 用户三问"筹码分析还有什么优化"。@CX 交叉复核（codex 读库判定：短板已转到"结论是否被时间检验/记账模型是否选对/数据资产与自动化任务是否生产级"），融合清单 26 项用户逐条批复：**批 18 项**（A1 只做轻量版、C6 只取薄版、B2 外包模型点名 opus4.8）；**否决/自留 8 项**（A3 判定后验回测、B1 黑箱关卡批量化=用户自留、B4 资源感知调度、C1 备份、C4 夜间摘要推送、C8 标签库刷新提醒、C9 BSC 兜底演练、D1 研报索引看板——勿再主动重提）。主线+5 子代理并行交付。

**记账模型准入 gate（A2，开工硬闸）**：新件 `scripts/evm/accounting_gate.py`+`scripts/solana/accounting_gate_sol.py`——fee-on-transfer/rebase/Token-2022 转账语义扩展会让 Transfer 流水重建**整体算错且供给对账闭合发现不了**（模型错但自洽）；链路由定型后必跑，exit 0=standard/WARN（可升级代理等）放行、2=BLOCK 硬停人工定制、1=检测失败禁当 standard。EVM 双路 fee 检测互补是实测教训（BabyDoge 型"只对 pair 收税"钱包互转免税、模拟法测不出，只有真实事件差值能抓；单侧干净样本制给 bot 刷量币留活路）；验收：QUQ standard 8/8 精确、HOGE 2% 合约税双路 BLOCK（稳定回归样本；**PAXG 现役 0 费勿再当税币样本**）、GOAT/USELESS standard、BERN Token-2022 现役 269bps BLOCK。通道坑入 channels §3.6（BSC dataseed state 窗口 ~128 块支持 eth_simulateV1/Alchemy ETH 免费层全历史 archive 但 getLogs 限 10 块）。

**entity_id 稳定主键 + 薄版血缘 + 时间因果轻量口径（C5/C6/A1，schema 组）**：analysis-state whale_groups 必带 entity_id（=facts entities 字典键，终身不改；label 只是展示，改措辞不断 gate/update 链路）+顶层 provenance{schema_version/skill_commit/data_sources}；facts 实体加 merge_evidence_earliest（多地址实体的归并证据最早时间）+宏 `{{e.merged_since}}`；facts_gate G1 改 id 优先 label 回退，新增 G6（缺归并时点提示）/G7（缺血缘提示），七契约测试。**合并时点措辞纪律**（evidence-wording §11 新★条+对照表行）：全历史证据聚类会把后期归集/gas 同源倒灌回早期——禁写"当时已可确认同一实体"，叙述归并证据之前的共同行为必须"以最终归并口径回看"限定或标注 merged_since；回看口径 vs 当时可见口径两种曲线回答不同问题不许混写（codex 本轮最有分量的结构性洞察，完整版时间切片重聚类未立项）。

**图层同源（A8）**：新件 `scripts/report/figures_from_facts.py` 三模式——fig1 从 state camp_share_series 直出（QUQ 489 点×8 阵营实测与交付版形态一致，禁止再现场手写装配）；flow 流转图 spec JSON 里数字一律写 facts 宏渲染出图（残留宏必炸同 G4）；check 图 2 装配数据与 facts 终值对账（末点 vs current 超 0.05pp 拒绝）——手抄数字在图层的通道就此关闭；四契约测试进全家桶；report-template 编译化节+checklist 4b 同步。

**惯犯层延迟揭盲 + 跨案身份冲突检测（A5/A7）**：聚类期 `CHIP_BLIND_SERIAL=1` 全程盲化（serial 命中不进主输出、封存案目录 sealed_serial_hits.jsonl；label_lookup/analyze_holdings/replay_edges/build_evolution 四出口接线，"有无命中"这个事实本身也盲化；设施标签照常不影响拦截），实体冻结后 `--unseal` 揭盲作定向复核线索——防确认偏差更贴合结论独立性；cluster.py 的 is_serial 仅 gatekeeper 豁免不改。accumulate_offenders 每次运行自动查四档冲突（primary 设施身份/goldset-infra 金标/secondary/cross_chain），**存量首扫 1741 址抓 1 条实锤**：PancakeSwap Infinity Vault（bsc）被 QUQ 大庄#1 成员表误吸并经 --apply 高置信覆盖成 serial-actor→聚类禁边失效、benchmark"manual 167/168"告警根因——**待用户裁决**（三选一路径入 labels/README；裁决前勿再 --apply 该地址）。检出经金标独立真相源，"覆盖已发生"的历史冲突也能抓。

**聚类扰动敏感度（A4）**：新件 `scripts/evm/cluster_sensitivity.py`——对 P0/P1 重建机械证据图施四类扰动（单源边逐删/stale 标签放开/门槛±10%/割边逐删），输出脆弱性清单**只进阶段 4 复核材料**（行内置信度已取消，STABLE/FRAGILE 字样禁入正文）；QUQ 实测 36.7M 边 17s：大庄#1 机械证据仅覆盖主分量 155/215、其余靠人工证据=复核最优先对象，门槛扰动判级稳定。诚实边界：机械证据≠全部证据，分裂≠结论错误；余额源必用 balances 快照（key_edges 抽取集重放净额虚高 409 倍实测坑）。Solana 边产物形态暂不适配。

**采集跨进程锁 + 密钥治理 + 周巡检（C2/C3）**：新件 proclock.py（flock 内核级：持有者死亡自动放锁=天然接管；心跳超 600s 挂死保守拒绝附 kill 建议不强抢；心跳原地刷新**禁 rename**——换 inode 甩锁）；collect_queue 队列单实例锁（exit 3）+每币 data/.collect.lock（抢不到 skipped_locked 跳过不崩队列）；run_id 贯通 nightly→run_guarded（日志/状态文件名带 run_id 不互覆盖+退出码透传修正）→队列 manifest；HyperSync token 全链路出 argv（--token-file/env，ps 与全部产物 grep 零泄露实测）。新件 probe_keys.py：12 项 key 免额度探测五分类（实跑 10 ok+sqd/vybe skipped），全输出 sanitize 脱敏，--feishu 仅异常推送；launchd `com.chip-analysis.weekly-probe` 每周一 10:00 在役——key 失效从"用时才发现"变提前一周暴露。test_collect_lanes 扩七用例（真两进程对抢）。

**峰值窗口两级预筛（B3，3.14.0 遗留 432s 收官）**：replay_duck 峰值段先做数学恒等上界预筛（一级=累计流入≥门槛才候选：峰值≤Σ入账；二级=正块净增更紧上界：前缀和≤正项和），只缩精确窗口输入集合、精确 SQL 逐字未动，只可能多收不漏收；QUQ 1.03 亿行 peaks/balances/stats **逐键全等**+ASTEROID golden_baseline 7 项全等；耗时 657s→~330s（2.0x；刷量盘为最不利盘型——真达标 21,826 址刚性占 ab 45%，常规盘型 ASTEROID 筛除 92.8%）。⚠终态余额预筛不完备（清仓者漏），只有流量口径可用；HUGEINT 溢出自动回退 VARINT。新参数 --no-merged（亿级基准跑省盘）。**顺带发现（待修）**：build_events 亿级全局宽键去重 temp >114.5GiB 三跑三败且 QUQ v2 五 run 零重叠=纯开销——修复方向块界感知去重（recon §12 已记）。

**E 组五小件**：①anchor_plan.py 时间抽查分层计划制（3 时段×3 余额档+四类强制点：最大单笔/最大日净变动/交界块/门槛±10% 边缘；QUQ 1.03 亿行 5.5 分钟出计划；测完备性与浏览器一致性、不替代供给闭合；Solana 仍走 anchor_sampler）入 SKILL 阶段 2；②price_check.py 价格双源 3 点抽查（DefiLlama/币安现货互补，>5% WARN >15% FAIL 禁入报告；QUQ 尾点 9.49% WARN=日线时点差正常形态；双源均无覆盖 exit 3 回退人工）入 checklist 2b；③retro_draft.py 复盘草稿生成器（五类关键词启发式+文件:行号出处，GOAT 71 行→35 候选；**不许原样当复盘交差**）入 retrospective 首步；④scan_script_forks.py 分叉盘点：首轮 439 份 py/358 组/多份组 32——make_charts.py ×21 份 21 种指纹居首、"已有通用件仍存私版"6 组；收编节奏仍守"≥3 次重现"用户纪律，盘点只供发现排序；⑤truncate_dataset.py+holdout_diff.py 时间封存测试（截 75% 历史重跑聚类判级、封存尾段验证协同延续=后见拟合体检；衍生 json 必须从副本重生成防穿帮）——④⑤组成 retrospective 新"季度质检节拍"节。

**主线三件**：P0 实体素材装配外包模板（research-workflows §二b，**模型点名 opus**=用户定例外档，判定禁外包不变）；断点恢复五步固定序（SKILL 新节：盘点资产→定位断点→数据不重采→结论不重derive→重读版本号）；消费方文档同步（update-workflow 实体跟踪按 entity_id 对齐+旧 state 顺手补 id、easy E0/E5、collect-data 7b/9）。

**遗留**：①0x238a PancakeSwap Vault 冲突待用户裁决 ②盲化开关靠会话纪律（已写 SKILL 阶段 3，未做强制 hook）③cluster_sensitivity 的 Solana 适配 ④build_events 块界感知去重 ⑤holdout_diff 只比 whale_groups 层（曲线对比待日期对齐方案）⑥巨分区窗口串行是峰值段剩余大头 ⑦分析会话尚未接入 .collect.lock（协议已定）⑧A6 交界块依赖 run 目录名（v1 产物无此信息时少一类强制点）
**成本指标**：主线 ~45 轮 / 5 子代理并行（91 万 tokens、348 工具调用、最长单路 80 分钟）/ 全程约 3h；全家桶 12/12 全绿（新增 test_figures_from_facts、test_cluster_quality）

## [3.18.1] - 2026-07-22 — HyperSync Solana 混合分段提议评估否决存档 + 验收对账器收编（文档小修）

用户提议"HyperSync 有近半年数据,近期段用 HS+历史段用 SQD"，@CX 交叉复核后**否决并存档**（防日后重议）：

- **前提辨析**：滚动窗口 196 天是**数据覆盖范围不是准确范围**——实测干净区仅摄取前沿约 20h（head-18 万 slot,且属单次抽样非服务承诺）,head-13 万 slot（≈14h）外即见静默暂态洞,21 天前缺 3.6%、67 天前缺 22%,渐变无干净分界线。
- **结构性否决理由**：洞静默（空响应+next_slot 照常推进,单跑 HS 无法自知缺数据）→证明某段完整的唯一办法=SQD 重拉该段对账,HS 白跑；增量更新窗口（数天-数周）恰好落在暂态洞区。
- **codex 独立补充两条硬论点**（标注来源:codex 第二意见）：①**供给对账兜不住成对缺行**——一笔转账借贷双侧同缺时供给仍守恒,完备性验收必须落到边集合一致,不能只看供给/余额/行数闭合；②**认证完成时间账**:T_hybrid≥max(S_SQD,H)+差集修复,SQD 全量扫描恒为关键路径,双引擎不缩短"经完备性认证的数据"产出时间,只可能提前"未认证预览"（对夜间自动采集无决策价值,不立项）。唯一理论净收益架构（SQD 只出键清单+HS 出载荷）依赖 SQD 服务端摘要能力,现实不存在。
- **工件**：验收对账器收编 `scripts/solana/hypersync_recon.py`（原 scratchpad recon2.py,逻辑未动,docstring 补 GA 重验收用法:改 MINT/FRM/TO 三区各跑一轮+Helius 终审定责）——修复 3.18.0 把 GA 重验收资产留在会清理的临时目录的隐患；§13d 路径引用同步+否决结论入档。

成本：单轮对话内完成（含 codex 交叉复核一次）。

## [3.18.0] - 2026-07-22 — 质量/速度/稳定性专项第二批（非复盘专项，@CX 方案 18 项）

> 用户二问"筹码分析还有什么优化"。@CX 交叉复核（codex 读库后判定：**引擎已不是瓶颈**，短板=①"计算结果→报告"最后一公里手工作坊 ②质量只有复核补救指标、没有漏检率分母），融合清单用户批 18 项（**easy 三级级联筛查被否决**——与"复核一分不减"需求冲突，shadow mode 亦不启动）。主线+2 子代理并行交付；两条与用户已批方向冲突的实现细节按保守侧裁定（见惯犯库/标签时效两段）。

**大件① 报告编译化（facts 事实源+宏引用+语义 gate）**：新件 `scripts/report/facts_gate.py`——facts.json 每案唯一事实源（实体/指标数值一律原始整数字符串）+宏渲染（`{{e.amount_share}}`→"2.78亿枚【总量27.84%】"等 9 种；`{{appendix_b}}` 附录 B 整块自动生成=**手打地址架构级消灭**）+语义 gate 五条（G1 实体成员集合与 analysis-state 逐组相等=checklist 4b 自动化/G2 供给上界/G3 current≤peak/G4 宏名打错必炸无静默漏渲染/G5 手写百分比差集清单）；build_html 加 `--facts/--state`（不给则旧行为不变）；report-template 新节+新写作纪律（结论数字一律宏引用，新报告必用）；test_report_facts 五契约进全家桶。手抄数字第四犯的架构级回应；claims 结论账本+覆盖证书为后续第 3 步。

**大件② 故障注入盲测烟雾集**：新件 `scripts/tests/test_fault_injection.py` 六用例——F0 合法账本基准全绿/F1 中段缺块必须被负余额暴露/F2 同键异值必须硬退/F3 无 mint 必须 gate 失败/**F4 尾部截断=盲区固定化**（断言供给闭合对 QUQ 快照缺块形态"抓不到"且 gate 照过——把已知盲区钉进测试防未来误信，真防线=done.json 前置查）/F5 通道段重叠启动即拒；进全家桶。纪律：新故障形态实战出现一次加一个 F 用例。golden_baseline 证"新旧一致"、本集证"行为本身对"——留一外测/召回率账本需产物指纹积累，下批。

**D3 文档拆分兑现（3.15.0 遗留，子代理执行+主线抽查）**：三大文档→8 分册+3 薄路由页（evm→channels/sources/recon；entity-cluster→methods/tiering/cost；solana→scan/capture，全部 <45KB）；inventory 逐条核对 268/205/242 全命中+verify_bytes 母文档 740 非空行零缺失双保险；docs_lint 33 文档 PASS；SKILL.md 深入阅读清单同步；§N 引用沿母文档节号经路由页对照表定位（analysis-playbook v3.5 先例模式）。

**惯犯库双源回灌闭环**：accumulate_offenders 扫描源加 analysis-state.json（**修真缺口：v3.2 后 state-only 案子的实锤庄全漏**——AKE/ASTEROID/GOAT/LPT/SIREN/SQD/USELESS 等 8 案此前未入库）+`--apply` 一键入库+labels_manifest 自动落印+日期动态化（added=当天/snapshot=案 data_cutoff）+addresses 元素 dict 形态兼容（Pointless 形态）；217→**1741 址/52 实锤组/跨案命中 11**；交付后固定动作挂 report-template checklist 15 与 easy E5。⚠组级收纳语义沿旧（实锤组全组进库）——QUQ 215 址 bot 体系/SIREN 散仓网含一次性执行地址，README 加"命中远端成员提示不定罪"注记，收窄规则待用户定夺。

**标签时效（提示不定罪+语义切分）**：resolver get() 附 stale_days/stale_hint（cex/suspected-cex/infra/bridge/bundler/paymaster/mev 超 90 天提示复核）；status∈{deprecated,rotated,historical,stale} 人工失效标记按**语义切分**生效——余额侧回退（is_exclude=False/balance=count，退役设施当前持仓不再自动剔）、**聚类禁边保留**（全历史重放里退役桥/轮换热钱包活跃期的边仍是公共边，放开=聚类污染回归——codex 原方案"过期即失效"被此裁定否决）；自动决策不因库龄变老而失效；benchmark 金标门禁 PASS；README 纪律 4 条（含单源标签禁独自驱动合并/剔除）。

**Solana 双引擎整合+完备性验收（子代理，结论=验收不通过→禁用）**：fetch_sqd_transfers_v2 新增 HyperSyncFetcher（schema 五轮实测定案）+SegPool 双引擎段池（SQD 偷段带礼让）+`--hypersync` 系列参数（默认关）；BONK 三区对账+Helius getTransaction 链上终审：摄取前沿附近零差集且**关户行语义与 SQD 逐字一致**（§13d 旧"pre/post 未验收"翻篇）、近端 head-13~33 万乱序回填暂态洞（静默吞 81 条边）、**历史区持久缺行越老越糟（head-450 万缺 3.6%/head-1450 万缺 22%）——禁止正式采集**（脚本四处硬警示），仅吞吐实验（双引擎实测 1,175 slots/s=纯 SQD 2.2-2.8 倍）与前沿对照/fee_payer 指纹查询，GA 后重验收（对账件 recon2.py 留 scratchpad）；默认路径 500 slot 回归**逐字节一致**；§13d 已更新（洞与窗外均静默快进 next_slot=响应判断完备性不可行/tb 索引前沿滞后 /height 13-27 万且乱序回填/tx_index 含投票 tx 跨源对账须去键）。

**collect_queue 泳道化**：EVM 泳道与 Solana 泳道**并行**、各泳道内串行（HyperSync key 级限流与 SQD 单 IP 带宽互不相干，跨泳道纯赚墙钟）+`--serial` 回退+manifest 读改写锁；test_collect_lanes 三用例（并行实证 1s vs 串行 2s/失败传播/回退）进全家桶；顺修 collect-data.md 与脚本头 `--mem-gb`→`--mem-ceiling-gb` 参数名 bug（照抄会当场报错）。

**磁盘水位三件（QUQ temp 两次爆仓回应）**：run_guarded 第三水位 `--min-free-disk-gb`（默认 5GB；触发实测正确）+min_disk_free_gb 状态记账+`--disk-path` 指定卷；replay_duck `_disk_precheck`（<10GB 硬拒+输入体积×4 粗估警告+max_temp_directory_size=盘余-5GB 动态化）；cluster_prep_duck 同款预检+护栏 min(40GB,盘余-5)。

**夜间自动采集（launchd）**：`com.chip-analysis.nightly-collect`（每天 02:30，合盖睡过点唤醒补跑）+`scripts/collect/nightly_collect.sh`——`collect_plans/pending_plan.json` 存在即 run_guarded 守护开采，按退出码归档 done/gaps/failed_plan_*；用法与卸载命令入 collect-data.md 第 8 步。

**监控报警两段制 schema**：monitoring_advice 新增必填三字段——confirm（数值型阈值类默认 `next_round`：首轮候选、下轮**同源同口径**复现才红卡；仅沉睡地址转出类强信号 `immediate`）/denominator（分母口径声明）/source_pin（数据源钉死+LP ×2÷2 口径跳变指纹注记）——投后三起误报事故（SOL 池子吸入/Bitget 热钱包/GMGN LP 口径互跳）的设计层预防；**posthold 执行器侧未动**（2859 行生产脚本架构改动，单列建议另会话做）。

**外部代币名自查自动化（铁律 1/checklist 10 自动化）**：build_html `token_name_scan`——$cashtag 非白名单即 WARN 拒交付、孤立全大写词 NOTE 供人工扫一眼；`--token-whitelist` 传标的+用户点名对比项；内置通用缩写/工具名/链 gas/稳定币/CEX 名白名单；QUQ 真报告实测零误 WARN。

**小件与实测**：HyperSync overage **实测已生效**（100 请求 7.2s 全 200≈831rpm 短爆发，api-keys 第 1 节更新、旧注"建议设 5x"作废兑现）；gas_origin.py max_pages=2+approx 回填（清 solana §8.3 挂账，gas_fast 同款语义）；skill 仓库 pre-commit hook（changelog_lint+docs_lint+env_check 三秒级检，`--no-verify` 应急）；SKILL.md 成本纪律刀 2 第 7 条加 1h 缓存 TTL 注记（降软约束，超量降级 5min TTL 时恢复）；**Workflow 按名调用结论落定**：认 ~/.claude/workflows/ 用户全局目录，但注册表**会话启动时快照一次**——会话中途新建的 workflow 认不到须用 scriptPath（3.16.0 遗留①翻篇，research-workflows §2 注记）；git 历史旧 key 清洗（全历史扫描确认仅 dRPC 一 key 一文件，Exa 命中为地址子串巧合；备份后 filter-repo 替换）。

**遗留**：①claims 结论账本+覆盖证书（编译化第 3 步）②留一外测与召回率/误报率账本（需历史案例产物指纹积累）③posthold 执行侧通用两段制（单独会话）④HyperSync Solana GA 后重验收 ⑤惯犯库大组收纳是否收窄待用户定夺 ⑥easy 级联筛查含 shadow mode 整体不启动（用户否决存档，异日需求变再议）
**成本指标**：主线 ~80 轮 / 子代理 2 路（26.6 万+20.7 万 tokens，共 106 工具调用）/ 全程约 3.5h；全家桶 10/10 全绿（新增 3 测试）

## [3.17.0] - 2026-07-22 — GOAT(Solana) easy 二战复盘：长币龄混合重建工程加固 + CEX 间调度商指纹

> retro 原料=GOAT分析/findings.md E6 素材清单（easy 交付后新会话执行）；用户批"全部写入"。Solana 侧 easy 首例：651 天 pump.fun 毕业币、7.6 万独立 owner、§11 混合重建全程实战。

**数据工程 5 条（正式）**：
- **Helius 大扫描通道打通**：24.7 万 token account / 67MB 响应，publicnode 恒 504、Helius 默认 120s 超时同样断——Helius + curl `--compressed`(gzip) + 300s 长超时一次拉全（§1 实测升级行 + §11.4 死角地图更新，scan_sharded 分片器降末位备选）；`scan_token_accounts.py` 加 `--timeout` 参数并内置 `--compressed`
- **window_fetch gap 段补拉合并纪律**（§11.2）：标 gap 的段仍写出部分数据，补拉后 cat 追加合并=9,212 行重复边；快查指纹=**重放负余额账户数暴增**（534→dedup 后 1）；正解=gap 段整段替换或全字段 dedup，两位数以上负余额先查重复再查通道
- **whale_deep cap 截断样本用途边界 + Helius 并发纪律**（§11.5）：签名史翻到 cap（2000 笔）即截断样本——起点非零禁从零累积持仓线，只作行为定性样本、时间线锚点/快照兜底；Helius 免费档 10 RPS 为账号级配额，多进程互抢反拖慢（5 进程实测单笔 decode 0.6-1.2s），正解=`--out` 分组并行+总并发贴限速
- **pump.fun→Raydium 官方毕业迁移钱包入 address-book**（`39azUYFW…jUJjg`）：毕业储备 2.069 亿枚 ≈20.7% 供应协议常数、Withdraw 指令数十秒过手——**发射窗重放峰值榜必剔**（GOAT 初稿误判"狙击集团 20.69%"被复核 REFUTED 的直接教训；§8.6 成本侧"迁移笔剔除"的实体识别侧补全）
- **编造地址第五六犯（base58 侧首发）**：funder 截断补全+基础设施地址拼写——evidence-wording 第 10 条适用范围明确为"一切链的完整地址字面量"，real_addr 反查纪律对 Solana 同样强制

**方法 candidate 2 组**：
- **【候选·单案】CEX 间库存调度商指纹**（state-anomaly 新 §9c）：零 DEX 交互（数百笔抽样解码）/精确定额轮发一所一线/凌晨日结节奏/多币种枢纽+闲置质押理财/双向大流量只报净向——P0 大仓的备择定性五判据，破"吸筹—拉盘—出货"框架硬套；配套"同类前例结局对照法"（锚点峰值普查出历史大仓名单→按画像匹配已离场同类作情景参照）
- **【候选·单案】锚点复用两扫描**（§11.3 + easy-workflow E3）：全 owner 峰值普查（≥1.5% 档，含已离场者）+ 全史前三涨跌日×锚点对照，零边际成本——GOAT 案完整性复核 4 条 must_add 有 3 条半源于缺这步

**脚本**：`whale_deep.py` --rpc/--proxy/--out 三参数收编（3.14.0 注记的他会话悬账，本条入库）；`scan_token_accounts.py` --compressed/--timeout；GOAT 案 `compose_evolution.py`（混合重建合成器）按红线 5 判标的专属件留工作目录存档，§11.1 注明"非复用件"

**easy 成本基准**：GOAT 行追加——Solana 长币龄混合重建与 BSC 亿级刷量盘同落 2-3h 档，单币基准初步稳定

**遗留**：①window_fetch gap 补拉替换/dedup 逻辑脚本化（本次仅入文档纪律）②Helius 300s 大扫描通道单案实证，下个大盘子 Solana 币复验③compose_evolution 通用化抽象④标的专属 TODO 4 条留 GOAT findings.md（E7 转正式时继承，不占 skill 条目）
**成本指标**：192 回合 / 139 Bash / 报告交付 2h06m（09:08→11:14，全程含 E6 素材沉淀 ~3h）
**质量指标**：初稿关键结论 ~16（判定块 4 直答+硬结论 12）；复核 4 路=1 CONFIRMED 加强 / 1 WEAKENED 定性改写 / 1 REFUTED 实体作废 + 审计 5 PASS·2 FAIL·3 WARN + 完整性 4 must_add 全采；漏检实体 3（离场庄三仓扩容、峰值 8.80% 历史大仓、4.73% 波段仓）；传播级数字错误 6（含发射窗统计重复合并 bug 修正）

## [3.16.0] - 2026-07-22 — B 档五项收官（非复盘专项，@CX 方案第二批）

> 3.14.0 三阶段（A 档+B6/B7/B9）交付后用户批"B 档也全部做"，其中 B12 附加三条需求：一个会话采集多币、专门命令 /collect-data、只采集不自动分析。本条为 B5/B8/B10/B11/B12 全部落地 + B7 补遗。

**B12 /collect-data 批量预采集（重头戏，用户三需求全兑现）**：
- 新件 `scripts/collect/collect_queue.py`：多币串行队列（HyperSync 限流 key 级共享+SQD 单 IP 带宽整形，串行是正解）——EVM 五链（bsc/eth/base/arbitrum/robinhood 走 fetch_hypersync_v2，部署块自动探测进全局缓存 deploy_blocks.json）+ Solana（fetch_sqd_transfers_v2，launch_ts 建议必给否则仅回看 90 天）；产物直接落 `<币名>分析/data/` 标准布局，分析会话零搬迁复用+断点续拉增量
- 行为契约：manifest（collect_manifest.json）逐项原子记账；残缺 run（无 done.json）改名 partial_run_* 隔离不删除（防污染下游 glob，遵守删除纪律）；单项失败不阻塞后续；退出码 0/2/1=全成/有缺口/有失败（按严重度 failed>gaps）；--resume 跳 done 项，不带也幂等
- 实测三路全过：CAKE(BSC) 早期 130 万块段 296 万行 220s（部署块 694452 自动探测）+ 幂等重跑 1.6s；wSOL 保险丝断开走 done_with_gaps 缺口注记；错误地址探测扫全链零命中 fail-closed 报"检查链路由"
- 新命令 `~/.claude/commands/collect-data.md`：解析多币清单→Solana 顺手查发射时间→生成 plan→run_guarded 脱管跑→只报采集事实不给结论；SKILL.md 阶段 1 + easy-workflow E1 加"预采集衔接"段（开工先查既有产物，禁从零重采）
- HyperSync Starter key 固化 `~/.config/hypersync/token`（chmod 600，长跑不挂进程列表；api-keys.md 第 1 节登记）

**B5 网络层进程内异步（买稳定性不是速度）**：新件 `scripts/lib/net.py`（httpx AsyncClient+异步令牌桶贴配额+tenacity 统一重试+msgspec 解析回退 stdlib；RpcPool 逐笔并发兼容 Helius 禁 batch）+首个消费者 `scripts/lib/rpc_batch.py`（批量 getCode 判 EOA/收据/任意方法 CLI，--browser-ua 治 robinhood WAF）；BSC publicnode 40 址实测与 curl 单发逐项等价、零失败（对照期 curl 裸发正好被瞬时抖动打中一次=重试价值的反证）；边界=CF/指纹敏感站点仍走 curl、在役老脚本不强改；三库进 pyproject+requirements.lock+env_check（14 关键依赖）；environment.md 沙箱节追加根治通道

**B8 对抗复核并行 fan-out 固化**：新件 `~/.claude/workflows/adversarial-review.js`（怀疑者×N+完整性批评同批并行、prompt 骨架内置、VERDICT schema 强制 JSON 输出根治坑表 #2、args 字符串化兼容层治坑表 #3——冒烟首跑就撞上该坑，兼容层实证必要）；冒烟 2 agent 100s：CONFIRMED 重算零偏差+完整性批评自发识破合成数据指纹；research-workflows §2 新增执行规范（同批并行=独立性正确形态/missing 非空必补跑/分歧以硬重算证据为准不投票）

**B10 Sourcify 合约身份批查（聚类前设施识别第三通道）**：新件 `scripts/labels/sourcify_check.py`——v2 API 国内直连免 key（0.2s 间隔 10 连发无 429），verified 合约名+代理实现名一次拿到（FiatTokenProxy→FiatTokenV2_2）；404=无源码≠EOA（判 EOA 仍用 getCode）；标的合约通用模板名（如 QUQ="Token"）本身即分析信号；⚠v1 批量端点 brownout 弃用至 2027-01 只走 v2 逐址；evm §4 入表+api-keys 免注册通道登记

**B11 DefiLlama 老币历史价格主兜底**：新件 `scripts/prices/llama_price.py`（series 分段拉 chart 端点全史日线单段 500 点上限自动分段/spot 批量单时点；输出与 CG market_chart 同构下游零改动；未收录 exit=3 别拿空当零价）；CAKE 2020-09 起 2117 点全史+2021-04 峰值 $42.46 抽查实测；CG 免费层 365 天墙的正解，Poloniex candles 降为其后备；evm §4 入表

**B7 补遗（守卫 hooks）**：新件 `scripts/hooks/guard_file_ops.py` 挂 settings.json PreToolUse——①Read 整读巨型数据文件拦截（二进制>1MB/文本>5MB，导向 duckdb 定向抽取）②Write/Edit 覆盖原始采集产物拦截（run_*/logs.parquet、soltx-* 只许采集器写）；pipe-test 四用例+本会话热加载实证（258MB parquet 当场被拦，顺带证明 settings watcher 对既有文件生效=3.14.0 遗留⑦翻篇）；PostCompact hook 注入"压缩后先重读落盘状态"提醒

**遗留**：①workflow 按名调用（Workflow({name})）不认 ~/.claude/workflows/ 用户全局目录（实测只列内置），须用 scriptPath 绝对路径——但 Skill 列表已识别其 meta，是否为加载时序问题下次会话验证 ②collect_queue 未覆盖 Hyperliquid/Filecoin（管道特殊用得少，遇到走原管道）③Solana 发射时间探测未自动化（命令层由 Claude 查填）④rpc_batch 尚无 nonce/traces 模式（按需加）
**成本指标**：~35 轮 / ~30 Bash / 约 1.5h；冒烟 workflow 2 agent 110k tokens；HyperSync 测试消耗 ~300 万行请求（Starter 档 <$0.5）

## [3.15.0] - 2026-07-22 — QUQ(BSC) 完整版复盘 + 逢5轻整编

> retro 原料=QUQ 分析目录 retro_notes.md（阶段 6 断点新会话执行）；用户批"全部写入 + 轻整编"（D1 归档滚动+D2 候选清点本次做，D3 文档拆分单独会话）。v3.13.0 已入 easy 首战复盘，本条为完整版增量。

**数据工程 4 条（正式）**：
- HyperSync v2 增量拉取实测（付费档 7 万块 2.3 万条 4s）+ 补丁段重叠核验法（补拉段落盘 patch 目录按 (tx,log_index) 键对比）→ evm §1；v2 parquet 资产做增量不走 pull_inc.py（面向 v1 CSV），直接 v2 新起 run → update-workflow U1
- **快照缺块坑**：重放跑在尾部采集完成前 → 快照缺尾部 ~980 块/682 条；**供给闭合恒等式对"缺整行"免疫**（借贷两边同缺、sum 恒=TOTAL 照过），只有 RPC 抽查负余额能暴露；对策=重放前 done.json 前置完整性检查（evm §5 新增第 5 查）；"期初 0 地址转出变负"=上游有洞指纹
- bscscan WebFetch 返回地址是省略号截断形态（`0xe096774F...BD5E2f603`），禁入任何产物 → evm §7.2
- 手写补全地址**第四犯**：纪律已有仍在脚本层再犯（camp 脚本首版 6 址 40-hex 中段凭记忆写入、equal 匹配全 miss 静默零输出）——工具化对策=脚本内 `real_addr(prefix)` 从落盘数据反查+断言唯一，代码禁手打 40 位字面量 → evidence-wording 第 10 条追加

**方法 5 条（1 正式 + 3 候选 + 1 注记）**：
- 【候选·单案】**公共基础设施先验三测**（getCode / 部署时间 vs 代币创建时间——早于代币=强公共信号（机制性子判据）/ 是否服务其他代币）+ 同模板合约对 code size 指纹 → entity-cluster §6。本次最大翻案来源：R2 复核据此 REFUTED"专属归集器"初判（1/9 项），主叙事"五代接力"整体改写为"bot 合约对+EOA 接力"两段式
- 【候选·单案】**寄存仓移仓指纹**（监管事件时点对齐 + 经枢纽收付 + ~3 天原路等额往返 = 移仓躲避非撤离；名单口径与实体维度分开表述）→ state-anomaly §7
- **净成本双口径与病态敏感声明（正式，机制=差分放大相对误差）**：净额<毛额 1% 禁报点估计浮盈；报"净成本≈0+现持市值"+近 90 天稳健口径；另算剔除体系自控镜像流后的"对外部实体真实交换"第三口径（QUQ 案镜像流占 91%）→ entity-cluster §6b
- 【候选·单案】**bot 合约瞬时峰≠EOA 囤仓峰**（合约 peak 是营运过手峰，排代际叙事时执行层/库存层分开）→ state-anomaly §9b 排代际纪律 + 枢纽定性引三测
- R2 型（备择解释）怀疑者对"归集器/枢纽/主仓"类结构性定性必设一路：REFUTED 计数低≠收益低，单条可重写主叙事 → evidence-wording 强度配置注记

**逢5轻整编（D1+D2；D3 推迟）**：
- **候选清点（21 条）**：转正 1——"高扇出≠公共服务商"三判据（LPT+QUQ 两案，§146 预告的合并兑现，标记改【正式·两案】）；降档 1——"CEX 上线事件驱动做市商身份判定纪律"（VIRTUAL 2026-07-18 入库超 8 版无第二案，正文删除、全文存档见下）；标疑 5——公共代买枢纽四特征 / 非关联组双口径 / 锁仓池动态性复核 / 世代阵营划分法 / 死币复活亚型分流（各附保留理由行内注记，下次整编复审）；其余 14 条未超版保留
- **归档滚动**：3.9.0~2.28.0 共 12 条正文移入 CHANGELOG-archive.md；**3.6.0 正文条目历史缺失**（并行会话时期只写了索引行）以索引行内容补档入 archive，版本序恢复完整；活跃索引区同步压缩
- **降档存档【CEX 上线事件驱动做市商的身份判定纪律】原文**：多地址在某 CEX 上线公告后、开盘前窗口集体激活并高频作业，只构成事件驱动型做市实体；"受该 CEX 委托做市"必须另查其全部流水与该 CEX 全部已标注钱包（热/冷/托管）的直接往来笔数——零直接往来时委托关系"不能确认也不能排除"，降级表述并把独立高频商作同等备择并列；上线时间强相关是行为证据不是身份证据（来源：VIRTUAL(Base+ETH) 多链分析，2026-07-18；3.15.0 整编降档，异案复现即复活）
- **D3 遗留（单独会话执行）**：data-pipeline-evm ~76KB / playbook-entity-cluster ~78KB / data-pipeline-solana ~65KB 三份超 60KB 整编线待主题拆分（拆分纪律=先冻结规则清单再逐条迁移核对，禁凭印象重写）

**质量 4 指标**：初稿关键结论 ~20（TL;DR 四问+特有 6）；复核判定 CONFIRMED 多数 / WEAKENED 1（净成本表述）/ REFUTED 1（449e 定性，连带改写体系叙事）；漏检 4 处全吸收（R5 完整性路抓出：寄存仓层/Alpha 搬运腿/V4 刷量环/沉睡大户）；传播级数字错误 0（R3 审计 7+13 项零误差；口径修正 3：215 址/毛净混淆/48.81% 口径）；另记数据洞 1（快照缺块，修复后全量重跑）
**成本 3 指标**：上下文峰值 ~33 万（超 30 万参考线，原因如实=重放修复+R2 大翻案连续作业、断点不划算）；子代理背调 4 + 复核 5 全后台并行；轮次/Bash 数未记录
**遗留**：QUQ 标的专属深挖 TODO 6 条留分析目录 retro_notes.md §五（下次 /token-update 取用）；本次脚本全为工作目录私有薄壳，无收编项

## [3.14.0] - 2026-07-22 — DuckDB 重放/缩图引擎三阶段落地（非复盘专项）

> 起因：用户问"筹码分析有什么优化建议"，@CX 交叉复核（codex 读代码后指出真瓶颈=亿级数据反复装进 Python 对象层，非采集/网络），融合方案获批后按"基线→改造→对表→亿级实测→监督器/依赖锁/hooks"三阶段执行。全程纪律：先建可证明等价的基线，再做任何优化——"快了但数字错了"是本工作流最贵的事故。

**新工程件 7**：
- **replay_duck.py**（scripts/evm）：pass1+pass2 合一列式引擎，v1 7列 CSV 与 v2 parquet 目录双输入自适应；`--emit-csv` 逐字节复刻旧 merged.csv；uint256 策略=≤37 位 HUGEINT 快路径/超界 VARINT 慢路径全程无浮点；reject 记账+同键异值硬退+空 ts 硬退（比旧引擎严）。
- **cluster_prep_duck.py**（scripts/evm）：亿级明细→edges_agg/bal/profile 三件全整数聚合 parquet；v2 输入块界感知去重（per-run 元数据定重叠区间，仅重叠段 shuffle）；派生表全部从 edges_agg 算（(f,t) 聚合保和）。
- **cluster.py --prep 模式**：四容器内存装载改读缩图件，判定语义零变化（ASTEROID 沙盘四类判定产物全等）；gatekeeper 新增 scan_profiles 聚合底数入口（浮点派生表达式与 funnel_profile 逐条同构）。
- **golden_baseline.py**（scripts/bench 新目录）：产物规范化指纹 snapshot/compare，stats 按 8 契约键判等（引擎扩展字段忽略）。
- **test_engine_equivalence.py**：hypothesis 随机边角数据（mint/burn/自转/同块多事件/零值/38+ 位大值/负余额盘）双引擎对表，进 run_all 全家桶。
- **env_check.py + pyproject.toml + requirements.lock**（A4 依赖锁）：关键 11 依赖版本冻结+全家桶内校验；刻意不用 venv（保住"系统 python3 直接跑"的全部既有入口），升级流程=先全家桶+基线对表再更新 lock。
- **run_guarded.py**（scripts/）：长跑监督器——脱管+任务树 RSS 上限+系统可用内存下限双水位+状态 JSON 原子写；替代裸 nohup。

**等价实证与性能**（细节与验收口径=data-pipeline-evm 新 §12）：ASTEROID 140 万行/SIREN 2169 万行三通道与旧引擎七项全等（含 merged.csv 逐字节哈希）；QUQ 1.03 亿行与 replay_pass1_quq 原产物 stats 11 键+balances 51,871 址+daily_delta 196 万键逐键逐值全等，peaks 两口径不变量零违例；性能=QUQ 核心重放 31s、缩图 19.5s/1.35GB 出 76.2 万聚合边（rustworkx 连通分量 0.35s——"先缩图再换库"实证：缩图后图算法不再是瓶颈，纯 UF 亦亚秒）、SIREN 峰值 7.1GB 守 8GB 限（旧引擎外推 ~19GB 不可行）。

**旧引擎三缺口修复（fail-closed）**：①replay_pass1 解析异常静默 continue→坏行计数+样本+默认即退（--allow-bad-rows 显式放行）；②cluster R1 边阈值/集群准入浮点累计→整数交叉乘法（0.005%=1/20000、0.01%=1/10000 精确等价）；③transfers_lib dedup 主键统一 (block,tx,log_index)+重组冲突（同键双 hash）硬退——曾双计。另修 cluster 输出排序非确定性（并列余额+set 迭代序→加 addr tiebreaker）。修复后 ASTEROID 重跑与基线 7 项全等（合法输入行为不变实证）。

**DuckDB 1.5.4 数字安全坑 6 条（全部实测踩出,§12 详表）**：UHUGEINT SUM 静默退化 DOUBLE / VARINT 乘法退化 DOUBLE（仅加法/SUM 精确）/ hex cast 位宽限制（32 字节 value 两段 HUGEINT 法）/ make_timestamp 不吃 UBIGINT+day 保留字 / temp 磁盘为亿级真瓶颈（max_temp_directory_size 十进制解析,全局 (tx,li) 去重 1 亿行需 >37GB→块界感知去重）/ 亿级窗口峰值 432s 为最重一环（easy 场景可跳）。

**自动化**：~/.claude/settings.json 新增 PostToolUse hook——Edit/Write 命中本仓库 CHANGELOG.md 后自动跑 changelog_lint，FAIL 时 exit 2 阻断反馈（撞号/倒排两次实际事故的制度化防线；若配置当次会话未热加载,重启后生效）。

**遗留（下次验收/优化点）**：①块末峰值窗口 432s 待优化（先按终态/流量粗筛候选再窗口）；②v2 输入超 127bit value 的 UDF 十进制慢路径未实现（触发即硬退提示,常规币不会触发）；③data-pipeline-evm 69.8KB→本条后更超 60KB 整编线（下次整编拆分）；④equivalence 测试未覆盖多通道段拼接（SIREN 实数据已覆盖）；⑤pueue 队列工具未装（夜间批量采集队列场景按需 brew install pueue,run_guarded 已覆盖单任务守护）。

成本指标：轮次 ~70 / Bash 调用 ~55 / 交付约 3.5h（含 QUQ 亿级三跑与两次 temp 爆仓排障）。质量指标：对表 FAIL 后翻案 0（全部一次通过或定位为口径/展示差异）；hypothesis 10 例边角全过；性能回归门禁（run_all 6/6 + env_check）全绿。

## [3.13.0] - 2026-07-22 — QUQ(BSC) easy 模式首战复盘

> easy 模式（/token-easy-analysis，v3.12.0 新增）首个实战标的：four.meme 发射、币安 Alpha 在架的亿级转账刷量盘（1.03 亿条 Transfer，HyperSync v2 付费档 67 分钟采完，对账三查全过）。E0–E6 全流程走通，两件套交付。复盘在轻上下文新会话执行（成本纪律刀 2 第 6 条）。

**新数据源 2（数据工程，直接正式）→ data-pipeline-evm §4**：
- **币安 Alpha 场内 K 线**：`www.binance.com/bapi/defi/v1/public/alpha-trade/klines?symbol=ALPHA_{alphaId}USDT&interval=1d`——Alpha 黑箱唯一的场内量价直查通道（标准币安 12 列 K 线含 trades 笔数，bapi 信封）；⚠实测单次返回 374 天且首行晚于上架日（窗口/limit 上限，翻页未测）——**非全史**，更早段配 CMC 全史日线补。
- **CMC data-api 全史日线 EVM 侧二案复用**：USELESS(Solana) 首测（437 点）后 QUQ(BSC) 复用 488 点全覆盖——跨链通用兜底地位确认，EVM §4 补行与 solana §4 互引。

**新盘型 1（候选·单案）→ state-anomaly 新 §9b「接力库存仓（Alpha 刷量盘）」**：库存=做量原料非待派发筹码，按吸筹/派发框架解读会错判。四指纹：①主仓多代接力+交棒直转（换代互转达总量数十倍、单笔数十% 整仓移交）②净持≈0 执行枢纽网（与主仓百万笔级互转）③「自持↔DEX 池↔CEX 场内托管」三态日轮转 30-50% 总量（日度曲线同步锯齿=真实倒仓非毛刺）④量能/市值数十倍倒挂。纪律：体系判定靠交棒直转边**不靠 gas**（各代 funder 独立=钱包卫生干净不构成反证）；「独立第三方做市商」备择每案必须独立走；CEX 托管曲线大幅波动属此盘型常规操作，单独看会误报"进所出货"。

**新指纹 1（候选·单案）→ state-anomaly §9**：**单 tick V3 NFT 头寸=零滑点自转刷量设施**——最窄 tick 区间（tickLower/tickUpper 差一个 tickSpacing）的集中流动性=自转特制场地；NonfungiblePositionManager positions() 查区间宽度；GoPlus lp_holders 报单址 99.9%+ 时先辨池版本（V3/V4 LP 是 NFT 非 ERC20）。

**聚类方法 1（候选·单案）→ entity-cluster §6**：**枢纽三段处理法**——①度>200 不作扩散桥（既有剔除规则的 BFS 执行形态）②种子枢纽保留成员资格（剔边不剔身份；为 LPT"高扇出≠公共服务商"三判据的第二案方向印证，整编时合并裁决）③事后公共合约卫生检查强制收尾（NPM/EntryPoint/1inch 等；QUQ 案复核剥离 34 址执行通道、现仓影响仅 0.04%）。

**工程坑 2 → data-pipeline-evm §6**：①key_edges 提取排除设施边→来源拆解**选择偏差**（刷量盘大头恰经池/枢纽走），daily_delta 缺口法兜底；②亿级 edges 提取禁攒内存，流式 append 落盘（7.3GB 实证）。

**easy 首战成本基准 → easy-workflow.md 新节**：单币全程 ~2.5h（采集 67min 占大头），亿级刷量盘属重型样本、普通量级预期显著更短。

成本指标：交付 ~2.5h（采集 67min）；轮次/Bash 计数未导出（分析会话与复盘会话分离，原会话未记录）。质量指标：初稿关键结论 9；对抗复核 4 路=3 CONFIRMED + 1 备择解释 REFUTED（主结论存活），实质修正 5（1 归属翻案：首日大买家独立大户→项目方关联分配仓 / 1 证据降档 / 1 成员剥离 34 址 / 2 措辞补证）；复核翻出漏检 P0/P1 实体 0；传播级数字错误 0。

另：本次 git 收口 3.12.0/3.12.1 两会话的未提交悬账（先补 commit 纯 3.12.x 文件，共享文件随本条 commit 进库——见 git log）。

## [3.12.1] - 2026-07-21 — 公共数仓准入验证 + BigQuery 复核通道正式化（非复盘专项）

> 起因：v3.11.2 数仓 D/E 评估后用户挂起待验证（"找已分析币看数据是否完全一致,检验过后再决定"）。本次用 ASTEROID(ETH,22 个月史,140 万条) 抽 5 代表日执行分区级准入,验证全过后用户拍板分工。全程未动采集主力选型。

**准入实证（当日实测）**：
- **抽样设计**：部署日 2024-09-10(创世+发射窗 14,447)/低活日 2025-01-03(47)/极稀日 2025-03-01(全天 1 条,阴性边界)/峰值日 2026-04-19(Musk 事件 114,010,压力面)/近期日 2026-07-17(3,966,新鲜度面),合计 132,471 行。
- **双仓皆 PASS**：AWS v1.0/eth raw logs 自解码与 BigQuery goog 官方版 raw logs 自解码,均与本地 HyperSync 基准**逐行字节级等价**——键 (block,tx,log_index) 零差集、值 (from,to,value) 零不一致。传递性下 AWS=BigQuery 亦等价。
- **成本实测**：BigQuery 定向查询(按币活跃日限日期分区)仅扫 12.0 GiB——**推翻 v3.11.2 存档的"老币单查 200-500GiB"悲观估算**(那是无日期限定的全表扫口径),免费 1TiB/月≈85 次复核;AWS 侧 4.9GB/60 分钟(瓶颈=用户宽带 1.7MB/s;S3 无服务端过滤,单币复核也须整分区下载,99%+ 流量为无关合约数据)。
- **AWS 新鲜度实测 T+1~T+2**(07-21 已见 07-19 分区),优于 sonarx base/arbitrum 的 T+7——修正 v3.11.2"官方宣称日更不成立"仅适用 sonarx 表的边界。

**分工定稿（用户 2026-07-21 拍板）**：采集主力=HyperSync Starter+v2 不变;**BigQuery=备用+出错复核源**;**AWS=已验证等价但 pass**(太慢),不做采集器、手工方法留档应急。BSC 对照源仍只有 SQD(两仓均不覆盖 BSC,格局未变);Base sonarx 未做准入。

**新件与文档**：
- **fetch_bigquery.py**(scripts/evm 第 12 件)：goog 官方数据集薄采集器——参数化(config bigquery 节+--dates/--from-date)、强制日期条件(防全史扫爆额度)、dry run 熔断(max_scan_gib 默认 200GiB)、输出与 fetch_sqd_evm 同款标准 8 列、对账走 transfers_lib merge;冒烟=2 日 48 行与基准六字段全等、凭据缓存零弹窗。
- **data-pipeline-evm §11 新节**：准入实证数字/分工定稿/BigQuery 操作要点(raw logs 自解码禁 token_transfers 表-跨仓通用/ToS 403 坑:新 Google 账号必须网页接受条款否则 API 建项目 403 `Callers must accept Terms of Service`)/AWS 手工方法留档(匿名桶列目录+逐 row-group 选列过滤)/**新源准入通用纪律**(四型代表日+键值集合对账全等才准入,禁止品牌信任替代逐行对账);§1 决策树+通道表各加 BigQuery 行。
- **GCP 资产开通并登记 api-keys.md 第 16 节**：sandbox 项目 chip-recon-77201(免绑卡)+OAuth 凭据缓存 ~/.cache/pydata_google_auth/(scope=cloud-platform,复用免弹窗)。

成本指标：轮次 ~12 / Bash 调用 ~20 / 交付约 2h(含 60 分钟 AWS 下载挂机与用户 OAuth/ToS 两次搭手)。质量指标：非复盘条目按修号+1(3.12.0→3.12.1,并行会话已占 3.11.3/3.12.0,写前重读索引防撞号);冒烟发现 0 缺陷;本次验证脚本自身的负面路径(ToS 403/项目创建假成功)均实测记档。

## [3.12.0] - 2026-07-21 — 简化筛查模式 /token-easy-analysis + 图 1 价格右轴（非复盘专项）

> 起因：用户从 SIREN 受启发做"币安系高流通候选"初筛（60+ 币），逐个完整分析成本不可行，需要筛查档位。方案讨论三轮定档 A：深度关联与对抗复核用户点名不可省（怕漏伪装分散庄），砍背调与完整报告（省 30-40%）；HyperSync Starter 付费后采集退出瓶颈位。开工时 skill v3.11.3。

**新增**：
- **命令 `/token-easy-analysis`** + 分册 `references/easy-workflow.md`（E0–E7）：E0=完整版阶段 0 原样（初筛清单地址可采信但多链硬关卡不可跳）；E1 三路采集砍背调路（不碰 Firecrawl/推特，问 4 以局限声明代之）；E2 三查原样；E3 引擎同强度（阵营表按实体结构细分粒度不降；Alpha 在架必算黑箱占比进判定块）；E4 复核路数不减、复核面自然缩；E5 两件套单页 HTML（图 1 必传价格+阵营快照表+判定块 3–5 行+局限声明）+ analysis-state.json 必落盘 + 工作目录沿用 `<代币>分析/` 转正式零搬迁；E6 复盘按需（有工具性增量走全套，无增量一行收）；E7 转正式衔接（同次产物直接继承免"沿用须检验"，隔日以上先按 U1 增量拼接；已 CONFIRMED 项不重跑复核）
- **standard_charts.plot_camp_evolution 新增 `price_series` 可选参数**（2026-07-21 用户定"价格+筹码对照"）：右轴价格黑线（白描边，堆叠色块上唯一不撞色组合）；默认线性对齐图 2 直觉，量程 max/min > PRICE_LOG_SWITCH_RATIO(30) 自动切对数；单位并入图例条目（右轴 ylabel 与外置图例同位会重叠，实测踩过）；图例 x 锚 1.01→1.075 给右轴刻度让位（线性轴多位小数刻度会被压住，实测踩过）；价格序列自动裁剪到阵营时间范围防 x 轴撑出堆叠区。demo 合成数据 + AKE 真实数据（13.6x 线性档）双验证通过。**完整版图 1 同步升级为必传**（report-template 三张标准图表格已改），不传保持纯占比图（旧报告基线重绘兼容）
- SKILL.md 新增「简化筛查模式」节 + 分册清单行；build_html.py 零改动（质检本就是"md 引用什么检什么"，单图天然兼容）

**纪律边界**：一币一会话铁律不变，跨币汇总矩阵不进分析会话（用户在独立轻会话用各币 analysis-state.json 纯机械拼表）；判定块只给参考意见绝不自动转正式。
