# CHANGELOG 归档 — token-chip-analysis（2.19.0 及更早）

活跃窗口在 `CHANGELOG.md`（最近 ~10 版，整编时滚动追加到本文件）。本文件保存完整早期迭代史——考古某条规则的来源与完整案例上下文时先 grep 这里。头部版本规则以活跃文件为准。

## [2.27.0] - 2026-07-18 — Index(Robinhood) 全量分析复盘：HyperSync 429→RPC getLogs 备选通道 + 第5类发射结构(外部资产分红盘) + EIP-7702 做市钱包费流陷阱 + 染色闭合口径

> 用户 2026-07-18 确认"全部写入 skill"——pipeline/playbook 正文条目已全部落地（下列各条已写入对应 references 文件）。

- **★HyperSync logs 高峰期整体 429 连败 → 公共 RPC getLogs 备选通道（pipeline-robinhood 待写）**：本次 HyperSync 拉到 ~10.79M 块后 429 连败退出（断点续传循环也救不回=服务端时段性限流），切公共 RPC `eth_getLogs` 拉尾段 12.5 万条速度可观（~20s/35万块）。RPC getLogs 坑：①"log query timed out" 需自适应缩窗（40万块起、超时折半、热点段降 5万）②单响应上限约 1 万条 ③**无块时间戳**，须另拉锚点（每 2 万块一 eth_getBlockByNumber）线性插值（实测误差≤1s）④HyperSync 段 ts=unix int、RPC 段插值也须转 unix int，合并前统一格式（踩坑：插值先写 ISO 字符串致 replay 排序 TypeError）。
- **★第 5 类 Robinhood 发射结构：ReflectionToken 外部资产分红盘（pipeline-robinhood 待写）**：普通 ERC20 + V4 hook 收原生 ETH 税(FEE_BPS constant/treasury immutable) → StockTreasury 买"代币化股票" → Distributor 按链上 holder registry(minShareBalance 门槛，holderCount/holderAt 直读) pro-rata 分发。分析要点：分红是外部资产不污染本币筹码，税=项目方现金流用 StocksBought 事件 ethSpent 求和量化；LpLock 永久锁池(无 removeLiquidity/withdraw、非代理不可升级、seed onlyOwner 一次性、collect 零 delta 只领费)是新 rug-proof 结构。
- **★"费收合约"可能是 EIP-7702 Ambire 做市钱包（playbook §7 待写）**：LpLock.collect(address to) 的 to 由 owner 任意指定；getCode=0xef0100 前缀=7702 委托 EOA。费流去向必须实际追踪（本案 collect Index 只销毁 65% 非"全烧"），"项目方零留仓/纯公益"叙事必查 collect(to) 去向+rewardsExcluded 标志+getCode——做市钱包持币+领分红会被漏归散户。
- **★染色(taint)比例分摊闭合口径（playbook §6b 待写）**：开盘扫货型集团出货量化用"注入%=净退出%+现存%"闭合，比名单口径现仓严谨；区分 gross 卖出(含往返)vs 净退出，避免"已卖77%+现存17%=94%>注入88%"口径不自洽(本案初稿踩坑、复核抓出)。
- **脚本收编（scripts/robinhood/）**：pull_transfers_rpc.py（HyperSync 429 时 RPC getLogs 全量备选，token/rpc 从 config 读、块范围 argv、自适应缩窗）、pull_block_ts_anchors.py（块时间戳锚点插值）、merge_hs_rpc.py（HyperSync gzip+RPC jsonl 合并去重填 ts）——三脚本 py_compile 通过。
- 成本指标：243,420 条 Transfer（HyperSync 到 10.79M + RPC 续 12.5万）+13,546 V4 ModLiq；5 路子代理（2 调研+3 复核，全 CONFIRMED，纠 1 子结论+3 口径+1 新实体）；约 95 轮/75 Bash；定时任务延时 4h 启动 + 3 次会话中断重启。

## [2.26.0] - 2026-07-18 — PING(Base) 全量分析复盘：Base 双通道拓扑反转 + 跨通道去重键陷阱 + AccessControl 口径盲区 + V4 单例池范式

- **★Base 双通道拓扑与 BSC 相反（pipeline-evm 新增 §8）**：HyperSync base 高峰期 429 连败（~250条/s 且不稳定），Alchemy base-mainnet 反而 ~230条/s 稳定零限流（走 clash 代理，免费层 30M CU 充裕）——分段接力法（HyperSync 拉发射段 + Alchemy 按 fromBlock/toBlock 多轮并行拉近段）2:1 提速拉完 239.3 万条。Base 官方 RPC getLogs 限 1 万块/batch 限 10 calls（角色事件全史改走 HyperSync topic 过滤）；Blockscout base 的 token-transfers（双币腿核账）/counters（公共性体检）免 key 可用。
- **★跨通道拼接去重键陷阱（本次最大坑，链无关）**：HyperSync uniqueId 尾号=链上 log_index、Alchemy 尾号=类别内序号——语义不同，跨通道按 (tx,尾号) 去重必然失败，重叠段双计实测造出 5,485 个负余额地址。正解=按块段给通道划唯一归属+段内自家键去重+"负余额=0"放行（replay_pass1.py 固化并内置段重叠校验）。
- **★AccessControl renounce 口径盲区（playbook §1）**：GMGN/GoPlus 的 renounced=true 只读 Ownable owner()——AccessControl 角色须 hasRole eth_call 逐个亲验（selector 0x91d14854）+ RoleGranted 事件从**部署块**起拉全史；"角色在手"与"能否增发"分开验证（mint 计数器 immutable 打满=角色在手也增发不了）。配套：config.json 的 deploy_block 必须记真实部署块而非首笔 transfer 块（pipeline-evm §8.2）。
- **★V4 单例池范式 + x402 mint 型标的（pipeline-evm §8.3/8.4）**：全部 V4 池共享 PoolManager 单例（池子余额=全 V4 池合计，当普通地址会误读成超级大户）、pairAddress 是 32 字节 pool id（GT OHLCV 直接可查）；"LP 锁定"的 V4 形态=token 合约自持 position+源码无撤出函数。x402 币 mint 走 facilitator 批量代执行（一 tx ~47 笔），mint 账本按 from=0x0 接收方记不按 tx.from；此类标的转账笔数与市值异常比极端，数据量预估按事件密度抽样（HyperSync 抽样外推按"服务端每响应条数上限"理解 next_block 推进，首段块跨度外推实测低估 5 倍）。
- **playbook 方法条目 7 条（§6/§7/§11）**：大户入方溯源独立于峰值普查表（低余额高吞吐"隐形管道"盲区，执行合约峰值从不上榜）；DCA 定投服务假分发器（入方 99%+ 是池子即拆穿，用户间无关联）；同模板 bot 路由粘连假实体（设施剔除名单须含"同模板高对手方合约"getCode 哈希分组排查）；registry 标签命中优先级高于行为学（deBridge 履约管道禁并入实体，三源裁决实证）；灰产资金池可为实体 gas 上游（背景画像不作合并边）；挂单式慢出货（收币→加 CL 位→质押 gauge→撤位收对价=限价出货新形态，误读成"分钟级卖出"会错写节奏）；collectLpFees"从池收币"≠买入（method 名+双币腿定性，定向动词第④查）；"名单现持全≈0"群体断言逐址复核（43 址名单混入 1.02% 在场残仓实测）。
- **脚本收编（scripts/evm/）**：fetch_alchemy.py 参数化升级（--config/--from-block/--to-block/--out-dir，key 走 config 不落 skill，支持块段接力+代理字段）；新增 replay_pass1.py（多通道块段互斥拼接去重→merged.csv+终态余额+峰值普查+mint 账本+供给闭合 gate）、replay_pass2.py（merged.csv+camps.json→每日阵营/实体占比序列，分母自动读 replay_stats 的 mint_total）。三脚本 py_compile+真实数据冒烟通过（段重叠校验实测报错、截断样本负余额被 gate 正确拦截）。
- **复核实效**：五路数据级重算（聚类/项目方/大户溯源/量能/完整性）——13 CONFIRMED / 4 WEAKENED / 2 REFUTED；REFUTED 两条全在项目方章节（"从池买入"实为 collectLpFees 领费、"11 分钟内卖出"实为加 CL 流动性+质押挖矿），实体变现口径实质改写。
- Known Gaps（PING 案遗留）：lpGuardHook 现状未闭环（selector 定位失败，不影响增发结论的纯尾巴）；两个策略合约（合计 3.93%）部署者/受益人未穿透；CEX 提币潮 ~1,800 万枚未溯源提币者；小庄#1 的 deBridge 下单源链身份（跨链盲区）。
- 成本：全量首战约 4.5 小时（含 3 路调研 + 5 路对抗复核 agent），Bash 约 80 次，主上下文一次未断；双通道 4 轮采集合计约 55 分钟（HyperSync 高峰限流拖累，Alchemy 三轮接力救场）。

## [2.25.0] - 2026-07-17 — 标签库 v4.2：round-trip 闭环 + 行为守门员 + P0 覆盖面（codex 第四轮交叉复核；"为什么四轮审计还有漏洞"的流程性回答）

**总路线（用户四轮同题复核后拍板）**：审计循环不收敛的根因=①审计是 LLM 注意力采样不是清单穷举②发现没固化成机器断言③修复引入新面积只验正向路径④零实战反馈。对策=封闭问题一次性系统化（不变量+门禁的门禁）+"全"的职责移交行为判别+扩容改实战 miss 驱动。

- **★round-trip 三断环（本轮最重发现，全部实测证伪"重建幂等"）**：①`upsert()` 无 policy 参数——全量重建丢全部手工 merge_policy/balance_policy 覆盖（v4 加列时引入，无 round-trip 测试）；②**v4.1 七份增量文件不在重建源里——全量重建静默丢约 250 条 registry 级设施标签**（modus：add_labels 只写现库不进真源）；③SOL spellbook 21 条"格式合法但链上从无签名"垃圾的删除只做在现库——重建即复活（v4.2 干跑当场抓获 bc1q/DdzFF 地址回魂）。修复=upsert 透传+`sources/additions/` 目录整目录进重建流（add_labels 入库成功自动归档）+清洗审计档 never 名单进构建器；historical 120 条/未归档增量 22 条导出固化文件。**教训：一切"只改现库不改真源"的手术都是定时炸弹；验收必须含全量重建 diff**。
- **★带毒标签比缺标签更危险（codex 第四轮核心发现）**：ETH 17 条 Alchemy/Candide/Stackup bundler+paymaster 因 dawsbot 项目名长尾类目默认 identity——每天代付十万笔 gas 的公共设施在库里"合法"参与聚类与 gas 溯源（建库首日进来，四轮抽查全漏，因为没人 grep 过 bundler）。修复=构建器 AA/Seaport 名字归一+设施类目（cex/bridge/router/mixer/bot-service）identity 矛盾行强制 exclude（规则化后实抓 27+2+7 行，比单点修多 19 行）。
- **★"疑似"条目禁边不剔仓纪律 + suspected-cex 类目**："疑似 OKX/Bitget（未免费确证）"直接 cex+exclude=真大户持仓可被静默藏掉。新类目=identity+no_merge+count；validate 不变量 14 强制"name 含疑似/未确证 ⇒ 不得 exclude"。launchpad 入 NO_MERGE_CATEGORIES（平台地址与用户的边全是公共通道边）。
- **★validate 不变量 11-14 + benchmark 门禁的门禁**：status 枚举白名单（DxLock 源文件半角逗号切爆字段错位值 2026-07-17 实锤放行过）/设施类目≠identity/AA 必须 exclude/疑似不得 exclude；benchmark 七链强制出现（此前只遍历 goldset 已有链——HL/FIL 零金标静默 PASS，"PASS 才发布"对两链是空承诺）+`--labels-dir` 发布前预检+HL 赌池 no_merge 覆盖进金标=policy round-trip 活体断言；goldset 支持 dict/list 形态 appendix。
- **★行为守门员 gatekeeper.py（防线重心从"查全"移向"兜底"）**：漏斗指纹（fan_in≥30 且 fan_out≥30 且净留存≤5% 且笔数≥80 ⇒ FUNNEL 禁边）纯本地零 RPC；bibi(BSC 20.5万转账)+TRASH(RH 9.9万) 双案校准 **47 实体误伤 0**、净增益 8 个库外真漏斗（含 BSC 侧未标的跨链同址服务合约——行为层抓住了静态库的漏）。evm/cluster.py 默认接入（R1+R2 双拦截、serial/team 豁免、gatekeeper_blocked 对账、FUNNEL∧未命中库 ⇒ miss 队列最高优先级回填候选）。miss 队列首次吃到实战数据（bibi 案 13 条）。
- **P0 覆盖面 208 条（全部官方源+链上亲验双纪律）**：Safe 官方部署家族 72（safe-deployments registry+三链 getCode 批量亲验，Robinhood 4663 在官方 registry 有登记；MultiSend=批量分发通道高危）；Relay 22 solver EOA 按链精确收录（api.relay.link 官方 API 亲验，RH 第 5 个 solver 为新发现）+Relay/Across/deBridge/LiFi/Socket 合约层 95 条（LiFi Executor/Receiver **各链不同址**；Across MulticallHandler 三链同址）；**Base bundler 24+paymaster 12**（HyperSync 7 日 33 万 UserOp 聚合，tx.from=bundler、topic3=paymaster——此前 Base AA 层=0 是 gas 溯源假金主最大盲区）；EntryPoint v0.6 四链（getCode 亲验 code 全长一致）。
- **韩所 SOL 调研定论（诚实盲区）**：四所无官方披露、主流标签库全空；唯一链上实证=Upbit 2025-11-27 被黑事件——疑似热钱包 2 条（signer 反查 B 级：6000+ 高频、事发后活跃至今、余额归零画像；主线程 getSignatures 独立复核）入 suspected-cex，攻击者 3 条（Blockmedia 逐字+RPC 时间戳吻合官方通报）入 heist。韩流币的韩所归集靠守门员兜底。**spellbook "Korbit" 5 条=BTC bech32 错标**（never 黑名单已拦）。
- **Filecoin cluster.py 接 resolver**（README 宣称"全链路接入"与事实不符的欠账）；add_labels 自动归档；benchmark --labels-dir。
- **坑（实测）**：python urllib 直连 publicnode 被拦而 curl 通（改 curl batch JSON-RPC，72 地址一链一请求）；safe-deployments 新版 registry 格式 networkAddresses 值是部署类型名（canonical/eip155），真地址在 deployments 段；UserOperationEvent 的 paymaster 在 **topic3**（topic2 是 sender——错读会聚合出 9.3 万"paymaster"=智能钱包全集）；HyperSync 空响应重试勿推进 next_block。
- 成本：单会话三步全交付（机制修复+重建发布 ×3 轮迭代+守门员两案校准+调研员 2 路+链上聚合 2 轮），Bash 约 60 次。

## [2.24.0] - 2026-07-17 — DUMBMONEY(Robinhood) 全量分析复盘：满贯池判级分母 + gas 溯源采样截断坑 + LP/价格脚本 IO 约定

- **★满贯池标的判级分母（playbook §6a）**：铸币 100% 入池标的的历史峰值判级必须并行"池外流通"口径（分母=总量−主池−销毁，逐时点重放），实测同一实体两口径差 2.6 倍（8.33% 总量 vs 21.9% 池外流通，判级结论相反）；发射后极早期（池外 <15% 总量）流通分母病态放大，该窗口瞬时峰值不适用流通口径（防发射 bot 全体误判庄）。
- **★gas_trace_bs per_addr_limit=8 采样截断坑（pipeline-robinhood）**：每址只取最早 8 笔入金会系统性漏采高频双向 funder 关系（实测漏"creator↔关联人 9 笔双向往来"与"埋伏对建仓前 5 ETH 直转"两类关键边，全部靠复核的 Blockscout 全量双向拉取翻案）；纪律=funder 收敛分析须全笔分组（禁"每址最早一笔"）、P0/重点地址一律 Blockscout 双向+internal 全量兜底。
- **HyperSync 并发纪律收紧（pipeline-robinhood 通道表）**：高峰时段 2 路并发也 429 连败（meow 案"≤2 路安全"不恒成立），429 即降级全串行+批间隔 30s。
- **脚本 IO 约定三坑（pipeline-robinhood 脚本节）**：build_price 硬读 `data/ethusdt_1h.json`（[[ts,close]] 升序数组）+`ohlcv_minute.json`；pull_lp_events 不读 config、须命令行 `--from-block/--pools/--out`；其输出是 JSON 数组（非 JSONL）且 amount0/1 为已解码浮点（非 wei，按 wei 解析费流水全归零）。
- 本次实战验证（未新增条目）：serial-actor 惯犯层首次在全量分析中直接命中 3 个历史案集团（身份引用+本案独立判定的边界把握顺畅）；"截断地址禁止补全"纪律 4 次拦截编造地址（两次是自己犯、两次是消费复核转述时拦截）；四路对抗复核 2 REFUTED + 多项 WEAKENED，全部实质改写实体表。
- 成本：全量首战约 5.5 小时（含四路复核与三路调研 agent），Bash 调用约 70 次，主上下文一次未断；HyperSync 全量 Transfer 仅 39 秒（13,711 条，26 天链史新盘的量级参考）。

## [2.23.0] - 2026-07-17 — Pointless(Robinhood) 二次增量更新复盘：协同检验 ETH 资金面纪律 + 定向动词三查（与 v2.22.0 TRASH 案同日互补——两会话独立踩中"分仓贴线漏检"同类坑，对策合并生效）

- **★协同检验双面纪律（playbook §6 + update-workflow U3a）**：token 面四维全阴性≠独立，合并铁证可 100% 在 ETH 资金面（wei 级等额批量注资/同秒多址注资闭环/gas 双向互供；disperse 类分发合约"单批次归属单一操作者"可作合并边）——实锤：九址协同工作室现仓 4.71%、峰值曾破小庄线，初判"双址簇 2.98%"靠对抗复核以 ETH 面证据扩成整族；两个 0.8-0.9% 马甲恰逃 1% 深挖线（与 TRASH 案"低档同秒共现扫描"对策互补）。配套：gas 溯源 first_in **逐笔消化**（只看第一笔漏"三马甲同秒供 gas"）；"旧期零交织"要查**行为交集**（三胞胎旧期 150 条同块协同、持仓端点为零，持仓交集检验完全漏检）；同实体观察哨按合并口径设（单址阈值被分单绕过）。
- **★定向动词三查（playbook §11）**：①"资金经过某合约"≠"进入黑箱"（多身份设施把 swap 误读成提现）②"在场+清仓"≠"收割"（须算完两腿对价——被判"潜伏收割"的惯犯双址实为净亏 78% 割肉）③平台函数动作定性前扫同期全平台调用分布（"主动抢费"实为单日 911 笔的平台级登记浪潮跟随）。宁可只写事实不写动词。
- **Robinhood 新坑 4 条（pipeline）**：0xb92fe925 多身份（App 交付金库兼 RelayRouterV3 swap 路由——出境判定看 RelayDepository 入账不看是否碰过它）；NOXA feeRouter 的 collect/setConfig 均无许可（3/6 轮 collect 系第三方代触发，烧速退化为 collect 频率指标；setConfig 有平台级浪潮）；Blockscout 列表首页 50 条截断活跃地址窗口核查（改 HyperSync 全量）；App 黑箱"清仓-重建仓"覆盖率量化范式（123% 实测入局限性）。
- **update-workflow 哨兵复判补丁**：mode-aware 自动核查漏复合触发条件的"或清仓"腿——人工复判逐条对照 trigger 原文每个"或"分支。
- **标签库/地址簿**：0x243a 热钱包新增入库（add_labels 增量+benchmark PASS）；0xb92fe 双身份、0xd29c=Across SpokePool、0x3f43 批次穿透用法三条补注对齐。SERIAL 惯犯层增量首战命中（另案集团 2 址潜伏仓 3.54%）——回报确凿。
- **实战成果**：无新 P0/P1（4.71% 贴线实体最高显著度披露+合并哨）；旧观察哨 9 条触发 5 条；两路怀疑者复核实质改写 6 处定性（A 路把双址簇扩成九址工作室、B 路推翻"抢费/黑箱提现/惯犯收割"三个动词）；对账三查全过。
- Known Gaps：工作室A 金主层 L1 侧身份未穿透（Relay 桥断头）；场外发币网络与 dev 集团深页历史边未穷尽（597 笔仅扫首页）；分发合约 0x3f43 的其他批次接收方（潜在其他标的马甲网）未扫。
- 成本：约 58 轮、Bash 约 50 次、活跃约 3h（含两路复核 agent 各 35-40 分钟）；U2 曾因旧快照仅存 264 大户地址触发双路径 FAIL，rebuild_wei_balances 标准兜底 10 秒修复。

## [2.22.0] - 2026-07-17 — TRASH(Robinhood) 二次增量更新复盘：新庄扫描两大检测盲区修补 + add_labels 回滚 bug 实测修复

- **★分仓贴线漏检对策=低档同秒共现扫描（playbook §6 新硬步骤 + update-workflow U3a 指针）**：份额候选线（如 ≥0.8%）可被"多址分仓、单址全部压线下"精确钻空（实锤：9 址协同族单址全部 <0.55%，全量+增量两轮分析漏检，合并 3.69%、对抗复核才翻出）。对策：0.1%–候选线档全体地址按"从池买入时间戳"聚集，同秒 ≥5 址即翻整族（等差递减面额=程序化附加指纹）；零额外采集成本。
- **★gas 档案双向用（playbook §6 新硬步骤）**：只正查"候选的金主"漏掉"候选是别人的金主"——实锤：某"独立新面孔"实为已知庄家集团最大成员的 ETH 金主（6 笔 8.7 ETH 发射前），反查即命中。gas_in 档案建 funder→下游反向索引为聚类标准步骤。
- **★暴涨暴跌归因逐笔价格对齐纪律（playbook §7）**："拉升时段内卖出"≠"顶部出货"（实锤：初判"顶部精准出货"的协同组实际卖在主升浪前 12 分钟、约开盘价一半——恐慌卖飞，定性反转）；"顶部出货"只授予均价 ≥顶部 70% 的卖方；崩跌归因看首卖距顶时长与价位（"回砸砸盘"实为距顶 5.7h、-75% 处亏 40% 割肉）。
- **★出金监控盯本尊转出（playbook §7）**：出金模式代际升级（冷藏→冷藏→一次性跳板 nonce=1 即收即 depositNative 跨链），盯历史收款地址的哨兵天然失效——threshold 哨直接盯本尊 value>0 转出。
- **★怀疑者地址转录不可信（research-workflows §2 裁决纪律）**：怀疑者结构性发现可全对（前缀/尾缀/份额/事件秒精确）而 40-hex 中段整批幻觉（实锤 9/9 错）——采纳前必须用其描述的行为特征从本地数据重新检索真实地址。
- **watch_return 条款纳入哨核查循环（update-workflow U3c）**：addresses 级"重新持币=回场"条款不在主哨 monitoring_advice 里,漏查即漏报（实锤：庄#1 集团 8 址回场 1.9 千万枚系该条款触发）。
- **中位价格序列抹极值坑（data-pipeline-robinhood 坑表,链无关）**：小时中位把高点抹低 33%/低点抹高 18-22%+漏二次探底——极值叙事必须 GT high/low 或逐笔,中位序列只画形态。
- **address-book Robinhood +4**：RelayDepository 0x4cd00e（Relay 桥存款库=跨链离场断头,与 0xf70da 同生态反方向）+3 原子中转设施（0xa687/0x2e9b/0x8f10）;gen_manual 同步、check_manual_sync 一致、benchmark PASS。
- **add_labels.py 回滚 bug 实测修复**：旧版先落盘后校验,FAIL 时只打印"从备份恢复"但从未备份——坏行滞留主库（本次增量入库实测踩中,21 条含半角逗号的行污染主库,手术剔除恢复）。修复=写盘前 .bak、FAIL 真回滚、成功后清理;破坏性实测通过（坏行触发 FAIL→自动回滚→主库零残留）。另:additions CSV 的 name/evidence 字段禁半角逗号,生成一律 csv.writer QUOTE_ALL。
- **标签库 serial 层 +21**（TRASH 案协同组:vanity 九胞胎族 10 含 dust 工具、d5ff 网 4、996 网 6、庄#1 第 19 址）;协同观察组用 name="协同建仓组（XX案·组名）"区别于已判级"惯犯庄家"。
- Known Gaps：①矩阵族↔vanity 族并体待定案（跨族直接边监控中,7.16% 若实锤即新庄）②dust 工具 0x5fff 上游未挖 ③TRASH 已连续 2 次增量更新,下次到 3 次触发全量重置基线规则 ④分仓更细（<0.2%/址）的协同结构仍是理论盲区。
- 成本：主会话轮次 ~85、Bash ~55、活跃 ~3h（超更新任务参考预算：HyperSync 并发冲突串行重试 + 对抗复核翻出 vanity 族/庄#1 第 19 址触发简报/appendix/图表全面第二轮修订——修正即质量,符合成本让位准确性铁律）;子代理 4 路（社媒/审计/怀疑者×2）合计 ~53 万 tokens,怀疑者两路合计翻案/加固 12 项。

## [2.21.0] - 2026-07-17 — 标签库 v4.1：覆盖面专项（codex 第三轮交叉复核，P0/P1/P2 全批全落地）

**总判断（双方共识）**：v4 是"高价值种子库"但四主战场设施层偏薄——46.9 万行里 61.9% 是 Tornado 隐私层，SOL 88% 是 validator、HL 82% 是 deployer。本轮火力全部投向"公共通道底座"。

- **spellbook CEX 三链投影分流（codex 硬发现+我方裁决修正）**：cex_evms 4,957 址是同一集合三链展开且无 EOA/合约分流——与 v4 OFAC 分流同构的逻辑洞。裁决"EOA 留+合约分流"否决 codex 激进版"全量重验砍到数百"（EOA 同私钥跨链同控，丢几千条正确标签换不来精度）。三链 getCode 后删合约空投影 531（eth 24/bsc 93/base 414），多源行保留；build_labels spellbook 段防回退。
- **SOL spellbook CEX 垃圾清洗（本轮最大意外战果，双方复核都没预见）**：166 条里 55 条是跨链垃圾——hildobby 表把 BTC bech32/Cardano 切片/Elrond/hex 错录成"Solana 地址"，且**全部恰好通过字符集+长度校验**。双层证据定罪：base58 解码≠32 字节（34 条格式假）+ getSignaturesForAddress 从无签名（21 条从未上链）；14 条有历史签名的真地址标 historical。norm_addr 改 base58 解码必须 32B（validate/add_labels/upsert 全链路生效）。教训：**"人工维护的上游"≠格式可信；地址真伪的最后防线是链上存在性，不是正则**。
- **HL 三连修**：CEX_WORDS 漏 robinhood/bitvavo/coinspot 致 8 条交易所钱包错归 entity 参与聚类（codex 发现，词典+manual 覆盖修正）；HyperCore↔HyperEVM 系统转移地址族 472 条确定性生成入库（官方规则 0x20+token index，PURR 系统地址持 5.1 万亿 wei 实锤"漏标即假大户"；spotMeta 快照进 _EXTRA_SOURCES 防回退）；entity 层词典二审 19 条（Unit 五大资产托管金库→bridge/exclude、HyBridge→bridge、两 MM 归位、3 空投钱包→airdrop-distributor、4 赌池显式 no_merge）。
- **BSC 设施底座**：现役桥 30 条官方亲验（Stargate V1/V2、LZ V1/V2+ULN、Celer 6、deBridge 5、Axelar 4、Wormhole 2）+106 条 Multichain 死桥标 historical（占原 bridge 类 51%）；router 家族 18 条（Pancake 九类角色——**V2 Router 0x10ED 此前竟不在库**、THENA 4、Biswap 3）；locker 17 条还清 README 欠账（FlokiFi 三代厂/DxLock 7/GemPad 2/Mudra 2/DeepLock/CryptEx/UNCX V2）；four.meme 全家族 11 条（官方 gitbook 附件 md 亲验 V1/V2/Helper2/Helper3/AgentIdentifier+fee 推断+部署者锚点+3 impl；**旧登记"0x757e 主合约"证伪**——仅 18 笔 tx 辅助合约，主力是 V2 0x5c95 2846 万笔）。
- **SOL 出货所层**：四所热钱包 23 条全链上亲验（MEXC 主力 40.2 万 SOL/Gate 主力 21.9 万 SOL 实锤；Bitget 12 条 DefiLlama 自报 C 级；OKX 2 条 GMGN/Solscan 增补）；Jupiter Lock+Bonfida vesting（locker 3→5）+Boop 主程序三重验证+Believe 架构结论（无自有程序，平台钱包直调 Meteora DBC——Token Authority 单源 C 级入库）。
- **GoPlus 运行时风险通道（P2）**：goplus_check.py——address_security 是查询式 API 不能拉黑名单，做成候选大户批量体检（30/min 限速+断点缓存）；EVM 实测可用（OFAC 攻击地址命中 stealing_attack/SlowMist），**SOL 覆盖未证实**（制裁地址返回全 0，如实标注）；candidate 纪律挂 README+playbook。
- **Robinhood verified-contracts 增量通道（P1）**：pull_verified_contracts.py 分页拉候选池（增量模式拉到全页已知即停；同名家族统计=克隆工厂线索）；只产候选不自动入库。
- **方法论沉淀**：①GMGN holders API name 字段是 SOL CEX 标签最高效通道（十币 top100 扫一遍覆盖主流所归集地址）；②四调研员并行抓官方源+主线程逐条链上复核（getCode/executable/余额）的分工模式全程零返工；③WebFetch 小模型转述会失真（Wormhole"同地址"误报、BscScan UI 按钮当标签）——**地址类调研必须 curl 原文逐字复核**。
- **坑（实测）**：BscScan curl 需代理+浏览器 UA+间隔≥2s（连发 HTTP 000 冷却 20s）；four.meme 官方地址藏 gitbook 附件 md（渲染页/llms.txt 均无）；deBridge 文档两跳迁移到 docs.debridge.com（靠 sitemap.xml 定位）；LayerZero docs 是 React SPA（用 metadata API+npm 包双源）；dx.app 多链同址部署（跨链复用标签注意链别）；getMultipleAccounts 一批里混非法地址会整批报错（先本地 base58 解码过滤）。
- 成本：单会话全量交付（P0×5+P1×5+P2×1+收尾），4 并行调研员+主线程复核。

## [2.21.0] - 2026-07-17 — BEGGAR(Robinhood) 分析复盘：gas 边"发本金"检查 + 分钟级行情归因两大方法修正

- **★方法修正（playbook）**：①§6 聚类新增 gas 边"发本金"性质检查——「转账 ETH ÷ 下游买入成本」≥1 即母子边（实测漏检致某集团 7→12 址、峰值低估 53%、一个 1.14% 潜伏仓藏身"其他大户"）；②§7 新增"行情归因最小单元=分钟级价格路径时点"（日级净额把'卖飞在日内低点'误判'借涨出货'，三处细节被复核推翻；出货窗口叙事须并列当日净买盘）+"喊单类利好对齐推文精确时刻"（'利好日回补'实为'公告前 4.5h 进场'时序反转）；③§4 新增"平台出纳机器人 ETH 分发名单=官方关联仓发现通道"（借此发现官方系隐性仓 0.15%）。
- **pipeline（robinhood）**：坑 4a 新增——LaunchToken 参数是发射配置项（maxTxBps=10000 即不限单笔）、发射块 deployer 特权**可不行使**（"平台有自买前例"≠"本案必有自买腿"，发射块 transfer 实证）、狙击顶格整数枚=专业指纹、ENS 双向解析（ensdata/ensideas 免费 API）作官方身份链上自认级证据；build_price 依赖 ethusdt_1h.json 为 list 格式（与 cost_engine 的 dict 并存两口径）。
- **address-book/labels**：Robinhood 段 +7 条（NOXA 官方族 treasury.noxa.eth/出纳机器人/LaunchLocker + 4 个公共卖币执行合约）+dev.noxa.eth 补注 ENS；labels-robinhood 增量入库 6 条（新 4 合并 2），check_manual_sync 一致、benchmark PASS（infra 召回 manual 45/45）。
- **复核实效**：4 路（A 聚类/B 项目方/C 归因/D 完整性）——A 两处 WEAKENED 均为方向强化型上修，B 四条全 CONFIRMED＋翻出官方关联仓，C 推翻 3 处细节（含一条 REFUTED："持有至今"实为双程波段客），D 因会话重启中断、独有项由主线程补做（V4 参与者/极端K归因/沉默大户）。修正记录 10 条印进报告附录 C。
- **坑（实测）**：会话重启后 subagent 被判"用户停止不可恢复"——复核路中断优先 SendMessage 续命，彻底丢失则主线程按其 prompt 补做独有项并在局限性声明。
- Known Gaps：BEGGAR 案 8859 集团 4 个弱边波段址未并入（峰值时点仓位 0）；7 个合计 5.33% 大户 gas 经平台内部通道不可观测；0xcdfc08a1…ca90 的"头部 meme 创建者"身份 tx 直验一次失败待补。
- 成本：主会话约 60 轮、Bash 约 55 次、交付约 2.5h（含 1 次会话重启续跑）；subagent 6 个（2 调研+4 复核）。

## [2.20.0] - 2026-07-17 — 标签库 v4：决策语义三维拆分 + 全链路接入 + 惯犯层（codex 第二轮交叉复核全量落地）

**总路线（codex 力主并被采纳）**：先修"语义/接入/基准"三断环，再谈扩地址——SOL 流程此前根本没接 resolver、Base entity 金标为 0 却承担门禁、批量分发工具可合法作合并边，任何"再补十万条"都是给断路电网发电。

- **决策语义**：tier 单字段拆为 merge_policy（no_merge 扩 locker→locker/airdrop-distributor/token-sale/charity 四类公共通道）+ balance_policy（count/bucket/exclude）+ 风险四档白名单（definitive 白名单制修复"未知旗标一律定性"休眠炸弹，unknown 档人工核验；validate_labels 白名单外旗标禁止入库）。
- **全链路接入**：SOL replay_edges（top/sniper/trace 标签标注+miss 队列）与 build_evolution（阵营体检：设施混入实体阵营即拦截）、HL main_metrics（AMAP 兜底+聚类 no_merge）首次接 resolver；全部入口 degraded_mode 显式告警（"没命中"≠"没加载"）；分析产物落 labels_meta。
- **惯犯 serial-actor 层（本方差异化提案）**：accumulate_offenders.py 从 15 份 appendix 聚合实锤收割集团 196 址（自动规则+人工白名单，宁缺毋滥），lookup 七段之首 SERIAL 高亮；首建即抓出 CASHCAT 工作室 2 址现身 NOXA 案的跨案惯犯。
- **金标扩衡**：random-eoa 负样本 120 条（低频交易者 sha256 确定性抽样）摘掉 BSC 弱门禁；余弱门禁链（base/eth）显式 ⚠️ 声明不再假装有防线。
- **Base 定向补录 54 条**（全部官方源亲验带 URL）：Aerodrome 全家+Slipstream 三代、Clanker v3.1/v4 全家、Zora Coins 官方 npm 包全量、Uniswap V4 Base（双源吻合）、Virtuals Base（docs+CoinGecko 双源）。
- **风险层跨链纠偏**：probe_codetype.py 批量 getCode 分流（OFAC 90 EOA/6 合约、ScamSniffer 2389/141）——EOA 才三链注入，BSC/Base 各清理 147 条历史合约误注入（上一轮 codex 建议被这一轮 codex 推翻，裁决取两者交集）。
- **新链**：labels-hyperliquid.csv 首建 464 条（Hypurrscan aliases+WHYPE RPC 亲验）、labels-filecoin.csv 首建 25 条（filfox 官方 tag，f 地址规范化进 resolver）。
- **Robinhood codehash 组合指纹**（fingerprint_check.py：sha256+长度+selector 签名，candidate 语义）：三模板入库，实测揪出"0x68be51 是模板升级版而非同款"的旧记录偏差。
- **B8 审计**：BSC 12.4 万 tornado-user 实锤为真（spellbook 事件级模型 SQL 审计+链上抽验 9/10 命中；0/5 首验失败系 proxy 调用语义——用户 tx.to 是 proxy 不是面额合约）；顺带入库 Tornado BSC 合约本体 5 条（此前 12 万用户在库、合约本体反而不在）。
- **体积治理**：纯 tornado-user 29 万行拆 labels-{eth,bsc}-privacy.csv 子表（resolver 自动合并，主表 ETH 30.7万→14万/BSC 13.9万→1.5万）；v4 六扩展列（policy 覆盖+source_snapshot_at/verified_at/status/raw_labels 时态与溯源）。
- **工程机制**：add_labels.py 增量入库（免重建+自动校验）、check_manual_sync.py 双真源一致性（不过构建失败，首跑抓出 HL 两条漏同步+自身正则 bug）、official_registry.csv 官方注册表源、实战 miss 队列（cluster/analyze/replay-top 自动落盘未命中高权重地址）。
- **坑（实测）**：publicnode/filfox 与 Robinhood 同款 python-UA WAF（403 像限流实为 UA 拦截）；codex-crosscheck.sh 在非交互 shell 须 `< /dev/null` 否则 codex 等 stdin 挂死；HyperSync logs+transactions 联合查询步长骤减（改两段式：纯 logs 大步扫+RPC 批取详情）；dRPC 对 batch JSON-RPC 回 403。
- **重建链路空壳干跑（发布前最后验证）抓出两枚重建时才会引爆的 bug 并修复**：①HL/FIL 表源不在主构建器——月度重建 cp out/ 会把 464 条 HL 表覆盖成 2 条（修复：_EXTRA_SOURCES 机制+缺失告警）；②旧 upsert 地址校验只认 SOL/EVM，FIL f 地址被静默丢弃且 merged 计数照常（修复：统一走 labels_resolver.norm_addr）。教训：**新链入库必须干跑完整重建链路，"增量入库成功"不等于"重建也对"**。
- 成本：单会话全量交付（P0×5+P1×7+P2×5 共 17 项），Bash 调用约 80 次。


## [2.19.0] - 2026-07-16 — 标签库 v3：风险层纠偏 + resolver 进主流程 + 回归基准（codex 交叉复核落地）

### Fixed（正确性修复，优先于一切扩容）
- **风险旗标分级剥离**：burn 地址（0x0000/0xdead）曾被打上 tornado-user/blocked 旗标——任何代币的销毁统计都会在 RISK 段弹出荒谬告警；修复=burn 类剥全部旗标、exclude 设施剥"行为型"旗标（tornado-user），"定性型"（ofac-sdn/heist）保留双重属性。共剥 26 行。
- **NUL 字节污染**：Dune balancer_lbp 模型名字段带 \x00（12 处）致 CSV 被文本工具当二进制拒读；构建器 name 字段统一剥控制字符。
- **956 条 risk 行补 evidence**（dawsbot/brianleect 的 blocked/exploit 行证据=官方标签本身）。
- **做市商/locker 分类碎裂确认**（Wintermute 碎在 5 个类别）——本期先建 locker 专类，MM 归一列入后续。

### Added
- **labels_resolver.py 共享内核**：label_lookup / cluster.py / analyze_holdings.py 三处共用。核心纪律：自动决策只认目标链直接命中（BSC/Base 与 eth 表 5,100 同址存在分类冲突，跨链同址只作提示）；exclude≠删除（禁作合并边/不计实体持仓，资金路径叙事保留）；风险三级分区 definitive/candidate/privacy。
- **cluster.py / analyze_holdings.py 原生集成（默认启用，--no-labels 关闭）**：R1/R2 合并边与 gas 同源种子过 no_merge 拦截（Relay solver/提款热钱包类历史假聚类源头堵死）；被拦地址写 clusters.json 的 label_excluded_nodes 供对账；analyze 侧 cex_lib 并入 CEX 净流、exclude/locker 不进大额边与吸筹普查、新增 top200 定性风险扫描段（命中必写报告）。
- **label_lookup 五段输出 + --json**：RISK / RISK-CANDIDATE（ScamSniffer 单源候选，不作定性）/ EXCLUDE / IDENTITY / PRIVACY（Tornado 使用记录，陈述不定性）；JSONL 供脚本管道。
- **OFAC 分资产导入**：0xB10C 仓库 lists 分支按 ETH(96)/BSC(1)/SOL(3) 资产精确导入——SOL 风险层从零补起。坑：文件在 **lists 分支**不在 main，`data/` 路径 404。
- **ScamSniffer 候选层**：scam-database 2,530 条 EVM drainer/钓鱼地址入 eth/bsc/base，risk_flags=scam-candidate（开源版延迟 7 天，降权提示不作定性）。
- **locker 专类（快速档）**：name 正则归一 147 行（Unicrypt/Team Finance/vesting 系）+ 亲验补录 PinkLock V2（BSC，bscscan 官方标签）、Team Finance Lock（ETH 官方标签 + BSC 同址合约名 LockToken）。语义=identity 不剔除（锁仓量是有经济含义的供应）但禁作聚类合并边（resolver NO_MERGE_CATEGORIES）。坑：关键词会误归代币（MUDRA Token/MyTeamFinance），须排除 "Name (SYMBOL)" 命名格式。
- **validate_labels.py 构建后强制校验**（NUL/UTF-8/地址格式/重复键/tier 枚举/burn 无旗标/exclude 无行为旗标/risk 行必带 evidence），不过即拒绝发布——首跑即抓出 96 项存量问题。
- **回归基准**（build_goldset.py + benchmark_labels.py）：从 15 份历史 appendix.json + manual 层抽 447 条金标（entity 281/infrastructure 166）；硬断言=实战庄家地址错误 exclude 必须为 0，manual 设施召回 100%（防重建退化）；扩容/重建后必跑。**首跑即发现一例历史报告误判**：某"L1 金主"经 etherscan 亲验实为 ChangeNOW 16 兑换热钱包（287 万笔公共服务，不构成关联证据）——已入 goldset 仲裁名单，报告侧修正另行处理。
- **per-token 实例不入静态库的边界再确认**：基准未命中的 12 条实战设施（做市组钱包/桥托管 PDA/费路由实例）均为 per-token 地址，归动态判别——作参考指标不设断言。

### 成本指标
- 全程零 Dune credits（用 sources/ 存档重建）；外部源下载 5 项（dawsbot 19M/brianleect 3.7M/OFAC 3 表/ScamSniffer）；两轮构建+校验+基准 PASS 一次完成。

## [2.18.0] - 2026-07-16 — 标签库 Dune 扩容至 ~46 万条 + 两个 API 资产（浏览器自动化注册实战）

### Added（工具性知识，无代币结论）
- **Dune labels.addresses 接入**（api-keys.md 第 13 节，query 7999252 为月度刷新资产）：精选 27 个 model 6.2 万行（CEX 7555 完整版/dao_multisig 命名多签 483/桥/OFAC/**SOL validator 7255（SOL 覆盖 882→8137）**/夹子 bot/Balancer 池/Base OP-stack 系统合约）+ **tornado_cash 用户 29 万行**（risk_flags='tornado-user'，Depositor/Recipient 角色区分；措辞纪律入 README 第 9 条）。终库：ETH 30.4 万/BSC 13.4 万/Base 1.2 万/SOL 8137/Robinhood 81。
- **三个数仓坑**：①labels.addresses 语义键是 **model_name** 不是 category（category='social'=ENS 噪音 12.8 万、'institution' 才是 CEX）；②Solana 地址存 varbinary hex 须转 base58（build_labels.py 内置）；③免费层 API POST /execute 403，**网页执行后 GET /results 拉取**是省 credits 正解。成本实录 ≈1100+/2500 credits。
- **Vybe 反面结论**：labeled-accounts（SOL 万级标签）实测免费层锁端点（宣传与实际不符）——SOL 标签扩容此路不通；key 留档作数据备用（api-keys.md 第 12 节）。
- **浏览器自动化注册流程实战**（auto-register-api + Claude in Chrome）：Google OAuth/Cloudflare 人机验证由用户手点、其余全自动；**key 不落 transcript 纪律**：网页复制 → pbpaste 直接落盘 ~/.config/<svc>/api-key（chmod 600）→ 登记文件只记存放位置。

### 成本指标
- 浏览器自动化注册两平台 + 四轮 SQL 迭代（探索/探查/精选/tornado）+ 构建落位一次完成；Dune onboarding 问卷 6 步全自动过。

## [2.17.0] - 2026-07-16 — 批量地址标签库建成（五链 ~11.8 万条 + 查询器 + KOL 层）

### Added（工具性知识，无代币结论）
- **references/labels/**：labels-{eth,bsc,base,sol,robinhood}.csv（100,928/10,682/5,802/882/81 条）+ README（口径/纪律/局限/扩容路线）。源：dawsbot eth-labels（Etherscan 系官方标签快照）、brianleect 快照、Dune spellbook（CEX 统一表/桥/基金，hildobby）、Jupiter 官方 program-id-to-label 97 程序、SOL 程序 29 条逐个 RPC executable 核验（1 条不存在剔除、1 条纠名 Jupiter Perpetuals）、OFAC SDN 制裁 96 址、Jito tip 8 账户、Robinhood 官方 docs 合约全套（L1+L2+预编译）、GMGN kol/smartmoney 流聚合 122 钱包、kolscan 558 KOL、中文车头 4 条（0xSun 本人自证 A 级 + 3 条单源 C 级）。
- **scripts/labels/**：label_lookup.py（三段输出：RISK/EXCLUDE/IDENTITY；EVM 同址联查带语义标注）、build_labels.py（多源合并构建器）、gen_manual_from_addressbook.py、accumulate_gmgn.py（KOL 滚动积累）、verify_sol_programs.py；sources/ 存小体积中间产物可重建。
- **schema 设计（codex 交叉复核融合）**：risk_flags 独立列与功能分类并存（被制裁 CEX 不丢 exclude 行为）；exclude 语义精确化=禁止作聚类合并依据+不计入实体持仓，资金路径叙事保留；CREATE2 联查措辞修正（同部署流程≠同私钥）；Arbitrum Orbit L1→L2 aliasing 公式记入局限。
- **挂钩**：SKILL.md references +1 行；address-book.md 顶部"先跑批量层"导语；update-workflow 深挖前置步骤改为 label_lookup 先行。

### 未竟（记入 README 扩容路线）
Vybe known-accounts（SOL 万级标签，P0 待注册接入）、Dune labels.addresses 完整表（P0）、Blockscout 增量通道、神鱼/大宇待补录（公开源仅截断地址，宁缺毋滥）。

### 成本指标
- 专项建设会话（非分析复盘）：数据下载+清洗+核验+CX 复核+落位一次完成；X full-archive 搜索在现有 key 上不可用（连续空结果）记入经验。

## [2.16.0] - 2026-07-16 — 用户反馈修正：多链代币先盘点链分布再开工（阶段 0 新增硬关卡）

### Added（工具性知识，无代币结论）
- **★SKILL.md 阶段 0 新增"多链代币硬关卡"**：凡标的部署 ≥2 条链（CoinGecko platforms / GMGN / Dexscreener / 官方文档多源核查），必须先各链 RPC 实查供给、产出链分布表（链/合约/供给占比/流动性/预估采集成本），AskUserQuestion 让用户选定分析范围（推荐主链；仅主链 / 主链+指定分支 / 全部链）后才准开工；**禁止拿到地址就按其所在链直接开工**。占全局 <5% 的分支默认不单独立项（用户点名除外）。路由表"跨链部署"行同步改写。
- **report-template.md**：多链代币 TL;DR 首行强制"分析范围声明"（红框：覆盖链 + 合计占全局总供应% + 其余链一句话列名带占比）；元信息行列全各链合约；checklist +1b。

### 教训来源
用户反馈：VIRTUAL 首次分析拿到 Robinhood 链合约地址即按该链全量开工，交付后被指出该链供给仅占全局 ~1%、主战场在别的链——阶段 0 原有"核定部署在哪几条链"只是登记动作没有形成分流决策，属流程级漏洞。范围错误比任何单条结论错误代价都大：整份报告范围性返工。

### 成本指标
- 用户反馈驱动的即时修正，非完整分析复盘；重做 VIRTUAL 的成本记入下一条目。

## [2.15.0] - 2026-07-16 — VIRTUAL(Robinhood) 全量分析复盘：桥接代币分析范式 + LP 层溯源盲区 + internal 转账漏查坑 + CCIP 基建档案

### Added（工具性知识，无代币结论）
- **★analysis-playbook §6a +2 条**：桥接代币（CCIP/OFT 跨链版）分析范式（时变供给分母/桥流双向同等归因——"只讲桥入不讲桥出"是系统性盲区，复核实锤"资金流守恒记账"视角/庄家命题转向流动性控制权/先池子识别再划阵营）；V2 LP 控制权分析标准件（LP token 全量重放→集中度+整数 LP 仓指纹+穿透口径，LP 持有人榜喂溯源候选）。
- **★data-pipeline-robinhood 坑表 +5**：gas_trace_bs 漏 internal 转账（军资估算差 8 倍实锤，"断头"结论前必查 internal-transactions；Across FilledRelay 可解码 depositor 同址续溯）；纯 LP-token 持有地址是溯源候选结构性盲区（复核翻出五址 LP 集群 5.83% 实锤）；Blockscout holders 快照瞬态伪影（1.56% "大户"实为 2 分钟过手）；Safe 多签双时点解读（SafeToL2Setup 勿当 owner、threshold 创建后可扩）；口径变更后正文数字全文重核（36.8%→42.7% 残留教训）。
- **data-pipeline-robinhood 通道表 +1**：Etherscan V2 chainid=42161 对 Robinhood 实体的 Arbitrum 侧溯源实测可用；两种自桥形态（ETH 官方桥别名 vs Arbitrum 聚合桥同址）。
- **address-book Robinhood 段 +3 档案 +1 补充**：CCIP OffRamp `0xcdca5d…`、CCIP 桥出收集通道 `0x786803…`（"转给它"=桥出勿判卖出）、TokenFactory 直连分发代理 `0x43e4c1…`（曾误判短命设施）；AgentTaxV2 补"对报价币=机械税变现通道"语义（税流断流才是异常信号）。
- 复盘期与并行 HAN 会话（v2.14.0）互证：`0x324872…` 平台回购机器与 `0xe4a001…` 平台部署管理员两档案由两个互不知情的会话独立收敛——跨会话互证为地址簿最强核验形态。

### 成本指标
- 轮次约 78 / Bash 约 58 / 活跃约 3.5 小时（含 45 分钟采集等待；176 万条 Transfer 45 分钟采完）。对抗复核 4 路（3 怀疑者+1 完整性批评）：CONFIRMED 1 / WEAKENED 4 / 分项 REFUTED 2 / 完整性缺口 6 项，每一路都实质改写报告（第十次实战再证铁律 4）；亲验纪律两次拦下编造地址（复核报告截断前缀补全被自查抓获——Arbitrum 金主完整地址实查后与臆测版后半段完全不同）。

### Known Gaps（VIRTUAL 下次更新重点，非结论仅口径）
- Safe 吸筹体 Arbitrum 侧两金主（0x25681ab5…74db / 0x3931dab9…c857）上游身份未穿透
- 隐匿 LP 集群 L1 金主 0x0b53aff8… 身份未穿透
- V4 池内部 LP 份额未逐仓重建（V4 PM 峰值 71 万→31 万腰斩仅归因到做市组调仓）
- Safe 执行合约完整地址待核验（复核报告仅给前缀 0x1e8ee74b）
- 税变现 70/30 分发收款地址#1 完整地址待取证（收款#2 与 Base 官方 Affiliates 同址）

## [2.14.0] - 2026-07-16 — HAN(Robinhood) 全量分析复盘：BONDING_V5 全账本实测 + 平台回购机器档案 + 瞬时峰值口径纪律 + 流通分母双口径

### Added（工具性知识，无代币结论）
- **★address-book Robinhood 段 +2 档案**：`0x324872…` Virtuals 平台回购机器（TWAP buyback bot，150+ 币单向积累、gas 来自平台、处置=keeper 编排整仓转入新合约封存非卖出——买家榜前排出现它勿判外部庄；监控白名单规则随附）；`0xe4a001…` 平台部署管理员（掌握核心合约 ownership/role，作为 funder 出现=收款方为平台组件的强证据）。
- **data-pipeline-robinhood 坑 3 HAN 实测补充（7 点）**：分配比是发射配置项（"X% Liquidity Pool"字段=内盘真实发售盘，名义 50% 内盘发射后十几秒即回收超发）；全部 vesting 进同一锁仓合约+多段 bips 解析法；ACF 毕业前 54 分钟即可启动（内盘挂单对价 VIRTUAL 与 V3 段 USDG 两币种）；ACF 成交量口径坑（毛流出≠净成交，拆两段两对价）；RelayRouterV3 转入="桥出/换出"与卖出不可区分；sHAN 类凭证=V2 主池 100% LP 十年锁（matureAt/founder 直查，撤池 rug 锁死是 BONDING_V5 标准安全垫，必查必报）；平台回购机器为生态系统性组件。
- **★analysis-playbook §6a +2 条**：阴性断言（"无实体曾持超 X%"）必须用瞬时峰值口径——期末净买口径会漏快进快出者（实测单址瞬时 1.12% 在净买榜只显示 0.46%）；贴线集群流通分母双口径检验（名义流通 vs 真实浮筹可差 2.6 倍，官方持仓极高的发射台新币用名义分母会把门槛虚高到永不触发）。
- data-pipeline-robinhood 通道表：Blockscout `?filter=from` 对个别地址稳定 500（去 filter 本地过滤）。
- environment.md：matplotlib 文本含 $ 触发 mathtext 解析崩溃（图表金额写"万U"或转义）。

### 成本指标
- 轮次约 50 / Bash 约 40 / 活跃约 1.5 小时（交付：全量报告 HTML+JSON 附录）。币龄仅 1 天数据量小（3.6 万条 Transfer 86 秒采完），首次实现"当天发射当天全账本 wei 级闭合"。对抗复核 4 路（3 怀疑者+1 完整性）CONFIRMED 6/WEAKENED 3/REFUTED 0，翻出暴跌归因缺失、sHAN 底层、观察组扩员、瞬时峰值漏检等 7 项漏报——完整性批评角色单路产出最高，再次验证铁律 4。
- 教训重演：附录 tx 哈希从截断输出"补全"被自查抓获（后 52 位全错）——"地址/哈希一律从落盘文件取"第三次实证，凭记忆补全=编造。

### Known Gaps（HAN 下次更新重点，非结论仅口径）
- `0x185f8d…`（ACF 执行器过手 54,933 枚收款方）身份未明
- 复核 agent 报告的 3 个同批平台系统地址（0x02118e…/0xc1c37b…/0x8e5017…）与 BRAMBL 接收合约 creator `0x07cd7d…` 未独立二次核验（翻页 400 中断），下次 Robinhood 分析时核验后补入 address-book
- HAN 合约税参数可调性未从代码层验证（Approval/权限事件不在采集面）
- V4 事件级数据未拉（净持仓 >0.5% 或 V4 量 >V2 的 20% 时补）

## [2.13.0] - 2026-07-15 — GME(Robinhood) 增量更新复盘：观察组全历史回放检验 + 单一成员集合对账 + 外包产物旧研报接管路径 + 聚合器三角流量档案

### Added（工具性知识，无代币结论）
- **★update-workflow U3a：观察组独立性检验必须回放全历史**——增量窗口内三件套（互转/funder/同窗）全阴性≠独立；实锤马甲边、与旧实体建仓期秒级穿插、程序化拆单指纹可能全部在窗口前的旧数据里，窗口切分本身是盲区。标准动作=每个观察组候选 grep 旧全量出完整历史（对抗复核据此把"独立买家"翻成"高度疑似同圈"，观察组拆独立/疑似两档+敏感性双口径入报）。
- **★report-template checklist 4b：单一成员集合对账**——图 1/图 2 曲线、verdict 汇总、附录逐址表、JSON whale_groups 必须由同一份名单驱动并交叉对账；"逐址表 vs 汇总曲线"两套手工产出会互相打架（实锤：曲线漏编 1.2% 成员致 verdict 低估在场庄 1.21pct，逐址表反而对——旧账抽验独有的收获，增量监控永远抓不到）。
- **update-workflow U0：外包会话产物旧研报接管路径**——自定义附录 id（grep `<script.*json` 找块）、monitoring_advice 裸地址数组喂 verify_balances 前适配 `[{"watch": addr}]`、CSV 格式旧全量转 jsonl.gz 约定（txfrom 置 null，失去旧段代发者穿透维度但重放/对账不受影响）。
- **address-book Robinhood 段 +5 档案 +2 补充**：DexAggregatorCore/DexAggregator/Diamond 聚合器三角（"池买→内部转→卖回池"三角流量=全市场聚合非对倒洗币环，COMPUTE 教训第二次验证）、公共合约出金通道 0xD29C85（大额出金曾被误当"私人金主注资"）、0x68be51 第三个同模板卖币 bot（曾被旧报告误判"归集器"）；b92fe925 补双向语义（转给它=同 tx 原子落池卖出，勿写"经 Relay 撤离"）。
- 复核期实锤重演两条既有纪律的价值（未新增文字，记录以证有效）：缩写地址继承禁令两次拦下编造地址（主分析自己踩、实查纠正）；"经同一合约"不构成关联（怀疑者C 曾用 b92fe925 共用上游补强归属，被主分析按纪律驳回该条证据）。

### 成本指标
- 轮次约 70 / Bash 约 38 / 活跃约 3 小时（更新任务预算：轮次 <60 ❌、活跃 <40min ❌——超因：三路对抗复核全部实质改写结论[A 修两处出货账、B 翻出实锤马甲+同窗穿插触发观察组拆分重写、C 翻出旧报告两套账]，且旧研报为外包产物无标准 appendix/wei 快照/jsonl 需全套兜底路径，另做了社媒/L1/LP 托管/主脑领费四路旁证核查。铁律 6 准确性优先；第九次实战再次验证对抗复核为投入产出比最高环节）

### Known Gaps（GME 下次更新/全量重点，非结论仅口径）
- 观察组B 与在场庄的并组信号（互转/同源注资/同步卖出）已布进监控表，触发即需简报级重判
- V4 池事件级数据未拉（Transfer 净额口径已覆盖归因；V4 活动放大时补 pull_swaps_v4）
- L1 金主以太坊侧全量溯源未做（本次仅 Etherscan 首页级检查）；6-17 系旧期完整 gas 网络未回溯

## [2.12.0] - 2026-07-15 — CASHCAT(Robinhood) 增量更新复盘：float 快照坑 + 币本位储备哨 + SELF_ALIAS 方法论纠错 + 留存率二分鉴别器 + 尘埃 gas 出纳档案 + 两脚本收编

### Added（工具性知识，无代币结论）
- **★update-workflow U0 / scripts/update：旧研报快照 float"枚"格式坑**——直接喂 replay_inc 错 10^18 倍且 float64 精度不足 wei 级；收编 `rebuild_wei_balances.py`（旧全量从零重放 wei 快照+互验，顺带独立复验旧账本：供给闭合+逐址偏差清单）。
- **★data-pipeline-robinhood（链无关）：池子"储备骤降"观察哨必须币本位**——Dexscreener USD 流动性口径被币价变动吞信号（实测 USD -28% vs WETH 枚数 -48.8%）；定性"LP 撤出 vs swap 卖压"用池 Mint/Burn/Collect 三 topic 分解（收编 `scripts/robinhood/pull_lp_events.py`），账配平判据=swap 净流隐含均价≈窗口均价。
- **★data-pipeline-robinhood：SELF_ALIAS ≠ 独立性证据**——alias 自桥语义是"资金关系断在 L1（不可分辨）"，当"已证独立"用会漏 L1 侧同源协同群（对抗复核据此翻出同窗建仓观察组，主分析曾误判"独立大户"）。
- **★analysis-playbook §6a：同窗建仓"留存率二分"统计鉴别器**——热点日同窗指纹被背景噪声稀释时，对同窗全体大买家 vs 长期留存者做模式比例超几何检验（实测 42 买家/7 留存/7 全同模式 P≈2.4×10⁻⁴），显著才升观察组；产出是"行为指纹显著"非实体合并。
- **update-workflow U3c：旧版 appendix 无 mode 字段时 analyze_inc 观察哨自动核查按 any_out 兜底会误报 threshold 语义旧哨**——必须逐条人工按旧哨 trigger 原文复判。
- **address-book：`0x91604f…c499` 尘埃 gas 出纳服务**（Robinhood 第三种 gas 断头形态，8,787 笔/111+ 收款人/"注 gas→秒级交易"服务模式）——据它建的 gas 边降级辅助证据；同文件 0x1887 双条目合并（三次核验定性收敛公共提款热钱包）。

### 成本指标
- 轮次约 60 / Bash 约 40 次 / 活跃约 2 小时（更新任务预算：轮次 <60 贴线、活跃 <40min ❌——超因：三路对抗复核 1 WEAKENED+1 证据降级+新识别毕业日观察组，触发简报核心章节/观察哨/JSON 大幅扩写，铁律 6 准确性优先。复核第八次实战再次实质改写结论：阴性结论"静止大仓=独立户"被删除、SELF_ALIAS 方法论被纠错）

### Known Gaps（CASHCAT 下次更新/全量重点）
- 毕业日观察组 7 个 alias 地址的 L1 侧（以太坊主网）资金关系未溯源——合并判定的决定性证据在 L1，需 Etherscan 通道
- 0xf1aa 0 枚转账合约工具（对 64 址发过 270 笔非零+对重点仓发 0 枚）性质未明
- OFT 跨链桥部署者身份（上游一跳断头）与对端链流转未跟踪；V4 swap 增量未拉（Transfer 净额口径覆盖归因）
- pull_lp_events.py 的 amount0/amount1 报价币腿自动判据未实做（脚本内注释占位，消费前须实 tx 校准）

## [2.11.0] - 2026-07-15 — meow(Robinhood) 全量分析复盘：同秒面额指纹的输入/输出侧方向性纠错 + 金主收敛双口径 + NOXA"自购砸价+马甲低吸"组合拳 + 浮点阈值坑 + HyperSync 并发纪律

### Added（工具性知识，无代币结论）
- **★analysis-playbook §6a：同秒面额指纹必须比对"报价币输入面额"（WETH 侧），禁止比对 token 输出面额**——输出受池价状态影响同秒必然不同，输入侧才是操作者指纹（可 wei 级全同）；初稿据输出面额否定关联被复核 REFUTED 并翻出一个伪装分散集团。输入面额同样要过"分母/独占性"检验（0.5×99% 通道费率系为通道指纹非实体指纹）。
- **★analysis-playbook §6a：金主收敛分析"现仓+同时刻合并峰值"双口径过滤**——只按现仓筛会系统性漏掉已出货协同集团（漏检根因：共享金主记录就在自有溯源文件里、被现仓过滤线筛掉）；私人 funder 服务 ≥2 址的簇一律再算 sig 原子化合并峰值；"每址最早一笔 funder"人工比对不能替代全笔按 funder 分组。
- **analysis-playbook §6a：发射窗口买家全景从第 1 秒扫起**——"期末仍持仓"口径漏快闪客（实测头 60 秒有三组协同扫货又秒卖，全部不在期末名单）；狙击识别按"窗口累计买入"取全景。
- **analysis-playbook §6a：出货回款归集排查表述边界**——池侧数据只证"直接收款人无归集"，经公共路由后不可证，措辞必须限定否则复核按"超出可证范围"降级。
- **data-pipeline-robinhood 坑 4 NOXA 补充**：新版 LaunchToken 反狙击限购参数语义（launchBlock 是 L1 块号）、LaunchLocker protocolFeeShare=100 的费流水真实路径（看 feeRouter→creator 而非 Locker→creator 的 0 wei 转账）、**"特权自购砸价+同注资网络马甲低吸卖 FOMO"组合拳模式**（凡满贯池标的必查发射后 60 秒买家与 deployer 注资网络的资金边；马甲注资在发射前 1-3 天 0.5-0.6E 级批量）。
- **data-pipeline-robinhood 通道表**：HyperSync 同 key 4 路采集脚本并发必 429 连败（断点续传救回），≤2 路并发安全。
- **SKILL.md 踩坑速查**：份额阈值过滤禁用浮点比较——`int(v)>=TOTAL*0.01` 的 float 不精确会把"恰好整数枚"地址（本身即橱窗仓指纹）漏出阵营与监控网，一律 `TOTAL//100` 整数运算。

### Known Gaps（meow 下次更新/全量重点）
- deployer 钱包 nonce 382 vs 本地 380 笔的 2 笔缺口未定位（0.5%，复核 A 标记）
- 工作室源头钱包 0x74b0 的 07-08 之前历史未穷尽；其注资网络在其他标的上的行为未扫
- HyperSync 安全并发数未系统实测（本次仅 4 路必挂/2 路存活两个数据点）

### 成本指标
- 轮次约 100 / Bash 约 85 次 / 活跃约 110 分钟（预算：轮次 <150 ✅、活跃 <1h ❌——超因：三路对抗复核 1 REFUTED+连锁新发现（马甲抢筹）触发问 1/2/3/5、第三章、图 2/流转图、JSON 的大面积修订，按铁律 6 成本让位准确性。复核第七次实战再次实质改写核心结论：REFUTED 1 条+新增两个 P1 实体+项目方叙事升级）

## [2.10.0] - 2026-07-15 — /token-update 脚本抽象收编（用户定：六次实战样本足够，防单样本归因错误的等待期结束）：scripts/update/ EVM 增量七件套 + VEX 数据全量回归验证

### Added（工具性知识，无代币结论）
- **scripts/update/（新目录，EVM 增量更新通用件 7 脚本 + README）**——抽象依据=六次 /token-update 实战（EVM 四战 RAXOL/Pointless/TRASH/VEX 全部出现的模块才收编为逻辑；Solana 两战 PUB/CLUDE 已由 v2.9.0 在 scripts/solana/ 收编，本目录不重复）。历史决策链：首战定"等第二次"、二战定"再等一次"、四战 VEX 复盘挂账 TODO，本次兑现：
  - `pull_inc.py`（U1）：起点自动=旧数据末行块（含重叠窗），断点续传，**拉完自动做重叠窗一致性校验**（键 tx,logi,from,to,amount；FAIL 退出码 1 不许带伤进 U2）
  - `replay_inc.py`（U2）：旧快照+增量→最新余额表；**全局 (tx,logi) 去重**（Pointless 版，优于单边界）；供给闭合+负余额检查；**每地址窗口统计**（buy/sell/t_in/t_out/burn，pools 驱动，下游复用）；`--full` 双路径互验（全量从零 vs 快照+增量逐址比对）；输出带 last_block/last_ts 元信息
  - `verify_balances.py`（U2）：对表名单自动构建（whale_groups∪观察哨∪addresses[watch]∪top20∪随机5 固定种子）；**归档块探测**（按数据末块对账，失败退 latest）；wei 级精确口径；**非 42 位地址值过滤+U0 4b 缩写禁令警告**（回归时实测抓到 watch 字段双地址串导致 RPC 炸）
  - `analyze_inc.py`（U3）：四态表（组级合并，--state-eps 默认 0.01pp，历史三战用过 0.005/0.01/0.02）；**新庄候选双口径**（现仓≥线 ∪ 窗口净增≥线，默认 0.3%）；观察哨 mode-aware 逐条核查（any_out 查窗口转出 / threshold 对 alert_threshold_pct）；**窗口买卖榜用全窗净变化口径**（v2.7.0 NOXA"同 tx 净额仍是毛口径"教训固化进脚本），毛买卖作辅助列
  - `getcode_recheck.py`（U0 硬步骤）：appendix 全地址（实体表∪金库∪addresses）getCode 一键复检，EIP7702 委托目标识别，非 EOA 高亮+全落点同步提醒
  - `camp_series_inc.py`（U5 图1）：阵营序列增量追加+等距重采样 ≤500 点（首末必留），输出 report-template 格式直接嵌 appendix；**每次都变的部分外置**——camps.json（地址→阵营）与 remap.json（旧键名→新键名，标准迁移用）人工产出，未映射旧键 WARN 防图1断层
  - `v3_positions.py`（按需）：V3 池 tick 级头寸重建（挂单墙监控正解坑的脚本化）。⚠ 单次实战成熟度（VEX）；token0/token1 方向由地址排序自动判定（v2.7.0 build_price 方向写死翻车教训），用前仍须现价交叉验证；头注含 owner=PositionManager、名义投放≠剩余挂单两坑
- **config.example.json +2 字段**：`rpc`（verify_balances/getcode_recheck 用；Robinhood 链默认浏览器 UA，可选 rpc_ua）、`pools`（{地址:标签}，窗口买卖归因；pool/pool_manager/v2_pairs 自动并入）
- **刻意不收编清单（防单样本/伪通用归因错误，两路独立调研 agent 结论一致）**：build_appendix（主体 80–90% 为人工研判文案——改为 update-workflow U5 骨架四则：rebuild 勿 mutate/存档幂等/skill_version 单点定义防 CLUDE 案 2.9.0-2.5.0 两处不一致/序列用 camp_series_inc 输出）；更新图表薄壳（standard_charts 三函数已是通用渲染层，薄壳里的实体选择每次都变）；深挖/怀疑者脚本（每次问题不同）；报价币侧哨兵核查（TRASH 走 Blockscout ETH 侧、VEX 走 HyperSync USDG 侧，实现链/标的特异）
- **文档同步**：update-workflow.md U0/U1/U2/U3/U5 加脚本指针+U1 开头总指针；SKILL.md 更新模式段落加"先用现成的别手写"；data-pipeline-robinhood.md V3 挂单坑条目补 v3_positions 指针

### 回归验证（全部用 VEX 实战落盘数据，输出进 scratch 不污染原目录）
- replay_inc：供给闭合精确 PASS + 双路径互验 211,480 条 0 不匹配 + **逐地址对照 VEX 实战产物 3,762 址 0 不一致**
- analyze_inc：庄#1 四态"增持+0.159%"与实战"净增持约 159 万枚"一致；新面孔候选集合与实战发现吻合；观察哨 0/8 触发同简报。argparse help 含 `%` 需转义为 `%%` 的坑当场修复
- camp_series_inc：末点 12 阵营占比与实战 camp_series_new **逐位一致**（另多补真实截止时刻尾点，属改进）
- verify_balances：归档块探测成功（按块 9937570），40/40 精确一致（优于实战当时 latest 口径的 33/36）
- pull_inc：真实拉取 5,171 条增量，重叠窗校验 PASS（两侧 4 行一致），SSL 瞬断退避重试实证
- getcode_recheck：22 址复检，5 合约全部为已知机制合约（ACF/DAO/TBA/锁仓/ve），无意外混入
- v3_positions：**窄带挂单 52 档 $0.01736-$0.02372 与 VEX 对抗复核实证逐位一致**，方向自动判定正确
- 全部脚本 py_compile 通过；密钥纪律：HyperSync key 一律 config/env（RAXOL 期 pull_incremental 曾明文硬编码，收编版清除）

### 成本指标
- 本条为脚本工程任务（非分析复盘）：主会话轮次约 35、Bash 约 20 次；外包 2 路调研 agent（四项目 20 脚本横向对比，合计约 16 万 subagent tokens）；交付 7 脚本+README+4 处文档同步+7 项回归全过

## [2.9.0] - 2026-07-15 — CLUDE(Solana) 增量更新复盘（/token-update 第六次实战）：ATA trace 资金侧盲区重坑 + 快照对比法定型 + 归集代卖指纹 + 旧账本抽验纪律

### Added（工具性知识，无代币结论）
- **★data-pipeline-solana §3a.8 重坑：ATA 级 trace 的 sol_delta 恒 0 →"费领取"系统性误判**——对 token account 跑 trace 时 lamports 恒不动，"零 SOL 流入"被顺势标为费领取；CLUDE 增量复核抽验 3/3 推翻（实为整数 SOL 市场买入），整个费收入账本作废重算。纪律：流入定性必须验资金侧（owner 主钱包 SOL Δ）；旧版 trace 产出的"费领取"标签一律视为未定性。§3a.9：CEX 提币型定投钱包识别（固定热钱包精确注资→秒买；资金源 CEX 硬止，排除性结论封顶"无罪推定"）。
- **data-pipeline-solana §10（新节）：快照对比法增量更新**——旧研报为锚点法时不补拉全量流水：新快照→snapshot_diff→窗口流转定性→轻量对账三查→观察哨签名级加固;大额变动地址 100% 覆盖定性（抽样会漏换仓对，实战被复核抓漏 1 对后补扫闭合）；cutoff 一律 datetime 验算禁手算（手算错 2 天首跑作废）；meta.updated 是写入时间不是覆盖范围。
- **analysis-playbook §6a +2**：①"归集代卖"指纹（零对价直转→1 分钟内合并卖池=同实体链上铁证，可把同窗清仓群措辞抬升为"内部分层关联集群"）+"同窗批次转入"单指纹不成边的反例实证（独立交易者/CEX 定投者在产品期先后归集,曾被误列疑似外围）；②增量复核必须含"旧报告账本抽验"一路（旧基线错误不在增量数据里）。
- **update-workflow U4/U1 补强**：怀疑者任务含旧账本抽验（对象优先级：核心定性账本>实体表>观察哨基线）；U1 加 Solana 快照对比法路由指针。
- **scripts/solana/ 收编 2 脚本**（py_compile 通过）：`snapshot_diff.py`（新旧快照 diff+实体标注+新面孔/清零榜）、`probe_window_moves.py`（窗口流转批量定性+直转对汇总，金额取对手方口径防虚高）——README 第 17/18 条。

### Changed
- **scripts/solana/trace_wallet.py 修复**（py_compile 通过）：新增 `owner_sol_delta` 字段（w 为 ATA 时自动补算 owner 主钱包 lamports Δ）+ 头部坑注释——上条重坑的脚本级修复。

### Known Gaps（CLUDE 下次更新/全量重点）
- dev 全史 72 条流水逐笔重算（每笔区分市场买入 vs 真实费领取）：旧"费累计 56.13M/成本 $547"口径全部待重核，devPDA 存入来源同查——下轮全量必做
- 双跳过路地址终点未追一跳（G4u1 案）；4ZgL 约 578 万窗口前存货来源未溯
- probe_window_moves 首版"直转对金额用本址净额"的虚高 bug 已在收编版修正,研报目录旧版留档勿复用

### 成本指标
- 轮次约 70 / Bash 约 45 次 / 活跃约 120 分钟（预算：轮次 <60 ❌、活跃 <40min ❌——超因：两路复核 REFUTED 级修正触发 38 址补扫与简报/appendix 全面修订,墙钟大头为复核 agent 各 ~19 分钟;按铁律 6 成本让位准确性。复核第六次实战再次实质改写核心结论：REFUTED 1 条+WEAKENED 3 条+抓漏 1 处）

## [2.8.0] - 2026-07-15 — PUB(Solana) 增量更新复盘（/token-update 第五次实战）：内置市场"做局出货"识别范式 + Token-2022 全扫缓存双坑 + 贴线观察组披露

### Added（工具性知识，无代币结论）
- **★analysis-playbook §6a 新范式：内置对赌/预测市场平台的"做局出货"识别与定性**——识别指纹六件（creator 大额走平台程序通道带固定费率费边/市场规模远超平台中位/赢家预知备币/赢家全平台高胜率分布/领彩即卖/资金链一次性中转隔断）+ 定性三事实收敛法（出资方+裁判资金归属+结算时点收敛同一利益方即定性"定向转移"，**不需要证明赢家钱包归属**、其身份最高"高度疑似"并标注不可区分）+ 取证要点（escrow owner→创建 tx 指令与签名者→注入 tx 指令语义（BuyShares≠注入奖池）→结算 tx 签发者与时距）+ 营销备择反证三件套。两路对抗复核 CONFIRMED，其中"自家裁判 53 秒结算"与"预知备币"两环为复核新增取证——复核再次实质升级结论
- **"creator 零卖出"核查清单补充**（并入上条）：必须单独扫"转出+同 tx 平台费边"指纹——平台通道转移不出现在 DEX 卖出扫描里
- **data-pipeline-solana.md §8.8：scan_token_accounts.py 双坑**——Token-2022 全扫忘传 --rpc 时默认 publicnode 恒 504；504 错误体被当有效缓存落盘+合法旧缓存无告警静默复用（增量同目录二跑必踩，假性对账炸 24.6%）；仲裁纪律：对账炸掉先用第三通道单查 2-3 关键地址定"谁是旧数据"再修
- **data-pipeline-solana.md §8.1 补充**：fetch_sqd_transfers.py 断点续拉增量场景首次实战验证（next_slot 无缝续拉，34 链上小时增量约 10 分钟，重放 vs 全扫零差异）
- **update-workflow.md U3a 贴线观察组披露范式**：无合并实锤的贴线集群→阴性结论照写但必须披露合计与同时刻合并峰值+声明"成立依赖判断而非数字余量"+全组并哨；有效否定证据主次（零互转+funder 不收敛硬、出生时间分散弱）
- **environment.md 操作纪律坑**：脚本 print 硬编码文件名与实际写入目标不一致→凭 stdout 误判覆盖事故并错误"恢复"；判定产出以 grep 代码+ls 时间戳为准，危机处置前先验证事故真伪

### Changed
- **scripts/solana/scan_token_accounts.py 加固**（py_compile 通过+原标的回归验证）：①rpc_call 校验返回体为含 result 的合法 JSON 才落缓存，错误体删除重试（curl 对 504 同样 returncode=0）②缓存命中打 mtime 告警提示非实时

### Known Gaps（PUB 下次更新重点）
- 做局出货 SOL 侧终点未溯：大赢家卖池回收的 SOL 是否回流 creator（变现受益人闭环最后一环）
- 疑似平台结算 cranker 地址（与大赢家前缀孪生）角色未确认
- 受托代卖系（收直转 94 秒代卖模式）是否服务更多母仓未展开
- gas_origin.py 的 max_pages 回填仍未做（v2.5.0 遗留；gas_fast.py 已带）

### 成本指标
- 约 50 轮 API 调用 / Bash 约 37 次 / 交付用时约 75 分钟（预算：轮次 <60 ✅、活跃 <40min ❌超——墙钟大头为两路复核 agent 各 15-19 分钟与 SQD 采集 10 分钟，属必要投入非流程浪费；主会话在等待期并行完成了图表与 JSON 构建）

## [2.7.0] - 2026-07-15 — NOXA(Robinhood) 全量分析复盘：价格方向自动判定 + 面额指纹环境依赖性 + 窗口净额归因 + 量能虚胖四件套

### Added（工具性知识，无代币结论）
- **scripts/robinhood/build_price.py 双修复**（py_compile 通过、原标的回归验证 GT 中位偏差 0.86% 达标）：①价格方向由 config 的 token/quote_token 地址排序自动判定——旧版写死"quote=token1"，遇 token>quote 地址的标的价格恒为倒数（GT 交叉验证偏差 10^13 倍量级当场暴露，交叉验证环节价值实证）；②ethusd() 自适配毫秒级 K 线 key（旧版对币安原生毫秒 ts 恒取首根）。
- **analysis-playbook.md §6 +5 条**：①★面额指纹的环境依赖性（分母细化）——同一面额在死盘窗（全场 9 笔中 3 笔 0.1E 整全是目标组）有独占性、在 bot 潮窗（同面额 672+ 用户）是通道指纹（整数×99%=1% 抽费通道特征）；引用必须报告"同时段全场同面额买家数"，同次分析同一指纹可一组成立另一组被击穿；②★净盈亏≈0 群体归因边界（量能虚胖四件套：多阈值稳健性/构成分解/原子性检验/群体盈亏）+"客观点火效果"与"主观点火意图"分开表述；③★窗口归因必须用全窗净变化——"同 tx 净额"仍是毛口径，会把窗口内买回的往返客计成大卖家（初稿两个数字被复核撤换的实例）；④★"其他大户互不关联"阴性三查（互转/gas funder 分层含 self_alias/同窗同秒共同下游）+"待证关联对"呈现范式（同分钟建仓差秒级、合并将破线的弱信号：列观察哨不并入不无视）；⑤消费对抗复核报告时地址纪律不豁免——复核文字里的截断前缀落地前必须回落盘数据反查（本次凭前缀补全出后 32 位全错的地址、险些进监控名单）。
- **analysis-playbook.md §9a 补满贯池变体**：mint 100% 进池标的的"创建者借势出货"环天然缺失——按四阶段判定，缺环写成"变现闭环未完成"的并列解释；死盘阈值按链龄折算。
- **data-pipeline-robinhood.md 2 处**：build_price 修复说明（含"交叉验证不是装饰"教训）；gas_trace_bs 输出消费必读 self_alias 字段（漏读会把 L1 桥别名自充值当独立金主，本次浪费一轮靠公共子串复查殊途同归）。
- **address-book.md Robinhood 段**：`0xd29c85f1…` 升级为 Across 桥 Universal_SpokePool 确证身份（与 VEX 会话同日独立核验合并）；新增 `0xb0999731…` 公共 bot 服务费收集地址（23,998 笔，"共同下游"边作废元凶）；NOXA 工厂条目补第 4 个费拆分数据点（烧 86.26%/treasury 13.74%、创作者领费同 tx 的平台机制分成——treasury"持仓"是被动费留成勿当建仓）。

### 影响面
- 修改文件：scripts/robinhood/build_price.py / analysis-playbook.md（§6 +5、§9a +1）/ data-pipeline-robinhood.md（2 处）/ address-book.md（2 条目+1 合并去重）。全量分析流程与看板抽取零变化。
- **遗留 TODO**：V4 池成交额并入图 3 的通用化（本次 V4 占 1.35% 已在局限性声明）；崩盘后量能结构待 /token-update 补测。
- 成本指标：单会话交付约 65 分钟（含 5 路对抗复核）；Bash 约 65 次；Workflow 2 个（背景调研 4 agent + 复核 5 agent，subagent tokens 合计约 105 万）；数据量 Transfer 11.2 万+V3 swap 6.5 万+V4 0.7 万，对账 49/50 逐 wei+RPC 终裁。对抗复核战果：CONFIRMED 10/WEAKENED 10/REFUTED 2，实质改写报告 12 处（点火组实体降格、暴跌数字撤换、发射人隐匿出货翻出、疑似知情者漏报补录），投入产出比第 N 次验证。**版本竞态实例**：开工时 v2.5.0、交付时发现并行会话已写 v2.6.0（同日 VEX 增量更新），本条目顺延 v2.7.0，报告 JSON 的 skill_version 如实记录开工版本 2.5.0；两会话同日独立核验出同一 Across SpokePool 地址（互证），address-book 已合并去重。

## [2.6.0] - 2026-07-15 — VEX(Robinhood) 增量更新复盘（/token-update 第四次实战；旧报告 v1.10 → 现行标准全量重判的首个标准迁移案例）

### Added（工具性知识，无代币结论）
- **update-workflow.md +4 条**：U0 新增 4b"缩写地址继承禁令"硬步骤（旧研报哨兵/正文缩写地址必须从旧数据文件 grep 解析，手工补全=编造——本案税 swapper 补错地址产生假发现+假阴性哨兵，两路复核独立抓到）；U1 新增"报价币侧定向流水"（观察哨含稳定币余额/挂单条目时必须补拉，否则哨兵不可核查）；U3a 新增"深挖前先 grep address-book"（本案 3 个待查大户库里全有，重复深挖两轮）；U4 新增"阴性结论证明强度声明范式"三件套（依据类型/数学上界/跨链盲区量化——复核抓出"逐个溯源均为散户"过度断言）。
- **data-pipeline-robinhood.md 方法论坑 +2 条**：★V3 挂单监控禁用"池子余额净变化"法（V3 栈通用）——集中流动性被穿越后回落自动复原、净额小推不出未成交，正解 tick 级头寸重建（单池全事件四 topic 一次拉齐，产出挂单墙价位）；多项目共用金库哨兵语义两坑（零交易≠零标的动作、nonce 增长≠标的异动；同名假币 symbol 撞名——监控一律按合约地址过滤）。
- **address-book.md Robinhood 段 +2 地址**：公共卖出执行合约第二部署 `0xb01ca24b…`（与 0x9be3 同模板，设施剔除两个都要含）、公共入金/跨链交付服务 `0xd29c85f1…`（ERC1967 代理、≥100 收款址——"同经它入金"为 Relay 桥同级弱信号）。

### 影响面
- 修改文件：update-workflow.md / data-pipeline-robinhood.md / address-book.md；全量分析流程与看板抽取零变化。
- **遗留 TODO（Known Gaps）**：①VEX 下次更新重扫名单——41 个 ≥0.05% 窗口新建仓的 gas 同源全量覆盖、0xd571 母钱包实体（783 ETH 级资金 vs 现仓 0.43%）、两个共用入金服务的弱信号对；②V3 tick 级头寸重建从项目 scratch 脚本抽象为通用脚本（本次产物存 VEX分析/data/skeptic2_v3ev.json 可复用）；③增量三件套（pull_inc/replay_inc/verify_balances）参数化收编 scripts/update/ 待做。
- 成本指标：主会话轮次约 65、Bash 约 45 次、活跃约 80 分钟；外包 3 agent（社媒脉搏 1 + 对抗复核 2，合计约 43 万 subagent tokens、69 次工具调用）。超 update 预算（<60 轮/<40min）原因：对抗复核修正量大（8 处修订全部落盘）+首个标准迁移案例需全量重判级+正文零地址纪律返工替换。复核投入产出比再次验证：两路怀疑者贡献了挂单墙实证（$0.0174-$0.0237）、金库2 热钱包语义、5 万枚隐藏卖出腿、3 处表述失真，全部实质改写了简报。

## [2.5.0] - 2026-07-15 — LAYOFF(Solana) 复盘：锚点法演变重建 + gas 溯源加固 + 喂料对/原子化峰值方法

### Added（工具性知识，无代币结论）
- **scripts/solana/ 收编 4 新脚本**（py_compile 通过）：`fetch_pool_sigs.py`（池全史签名落盘，断点续传）、`decode_txs.py`（fast 版 requests.Session 逐笔 decode + 池余额锚点，`--proxy` 必带绕 429）、`build_evolution.py`（锚点法阵营演变重建，标的参数从工作目录 config.json 读）、`gas_fast.py`（翻页上限版 gas 溯源，避免高频地址卡死）。见 scripts/solana/README.md 第 13-16 条。
- **data-pipeline-solana.md §9（新节）**：锚点法演变重建 Plan B 替代（免全量 SQD）；decode 直连恒 429 必走代理 + dRPC 免费层 Solana 需付费；gas 翻页上限加固；**高频服务热钱包识别**（持巨额 SOL+近千签名<10 分钟跨度=服务，gas 聚类取"最早入金 funder"防误合并）；发射窗 decode 的 AMM 路由噪声（bundle 用 GMGN 标签兜底）；**pump.fun creator 履历 + set_creator 洗白识别** + RugCheck creator 前科 danger 标签；Streamflow feePayer 洗筹指纹实战命中。
- **analysis-playbook.md §6a 新增 5 条方法**：①同时刻合并峰值必须 sig 原子化（否则喂料转账虚增约一倍，对抗复核 REFUTED 伪小庄最常见来源）；②"喂料对"指纹（买手零 SOL 对价转大额币=同一实体链上铁证，强度等同 gas 同源）；③"无控盘庄"分散盘判定范式（gas funder 收敛判定 + 转账相连≠同一实体 + 超 5% 转账簇必须披露为边界案例不得静默剔除）；④媒体驱动型 meme 的问 4 权重调整。

### 影响面
- 修改文件：scripts/solana/（4 新脚本 + README）/ data-pipeline-solana.md（§9 新节）/ analysis-playbook.md（§6a +5 条）；全量分析流程与看板抽取零变化。
- **遗留 TODO**：把 gas_fast.py 的 max_pages 上限回填进 skill 的 gas_origin.py；Streamflow 洗筹链穿透（feePayer 反查全部提取）方法固化。
- 成本指标：本次跨一次会话恢复（断点续，桌面版 stopped 后继续）；轮次数偏高（138 万签名池全史采集 + 550 锚点 + 65 实体 ATA 深挖 + 3 轮 gas 溯源 + 4 路对抗复核 + 复核修正重画）；Bash 调用约 200+；交付含 4 图（含 P0 流转图 + 图2 疑似簇线）+ JSON 附录。对抗复核 V1 实质改写问 1 结论（"无小庄"→披露 6.26% 边界案例），投入产出比再次验证。

## [2.4.1] - 2026-07-15 — 图2 价格轴改线性刻度（用户指定）

### Changed
- **standard_charts.py 图2（plot_whale_vs_price）价格右轴：对数 → 线性（均匀）刻度**。用户 2026-07-15 定：对数刻度与 K 线软件直觉差异大、涨跌幅不直观。新增 `_linear_price_axis()`（FuncFormatter 直标数值，规避 ScalarFormatter 的 ×10^n offset 上标中文乱码坑）；`_log_price_axis()` 保留仅供图3。图3 价格/成交额维持对数（全历史跨 2~3 个数量级，线性会把早期行情压成贴零平线）。report-template.md 图2 规格行同步，图注不要再写"右轴对数"。

## [2.4.0] - 2026-07-14 — TRASH(Robinhood) 增量更新复盘（/token-update 第三次实战；与 2.3.0 为同日并行会话，内容正交）

### Added
- **analysis-playbook §6 聚类规则 +2 方法**：①"同秒等额买入"矩阵指纹三要素法（同秒本身非指纹——对照组检验法：同工具全体用户中同秒率=误报率；有效指纹=wei 级面额一致（整数 ETH×99%=bot 抽费净额）+重复共现富集（>1000 倍级）+资金/币流边闭环；单次共现只作外延）②贴线实体双口径呈现范式（硬边/含弱边并列、按证据下限判级、观察哨最高优先级+下次重扫指令；跨组无资金边时表述封顶"高度疑似同一工作室"）。
- **update-workflow U0 +1 硬步骤**：旧实体表"漏斗/中转/马甲"角色地址继承前逐个 getCode 复检——复核修正可能只改账本漏改实体表（TRASH 案 0x53bf 随 appendix 传代）；"一处结论多处落点（账本/实体表/图/JSON/文案），修正必须全落点同步"。
- **address-book.md Robinhood 段 +3 地址**：UniversalRouter 第二部署 `0x53bf6b06…`（与 0x8876 并存，设施剔除两个都要含；"单币早期用户少≠私有"）、买入代理合约 `0xe492912f…`（IN 全来自 PoolManager、分发 300+，以它为共同上游的聚类作废）、batchTransferNative 公共工具 `0x3f43479c…`（判关联看单笔调用 payload 不看工具）。
- **data-pipeline-robinhood.md 坑 2 反向警告**：L1→L2 桥别名会伪装"独立金主"（funder=目标+0x1111…1111 ⇒ 本人自充值；本次 3 例误判）；坑 14 地址修正（实测数字对应 0x53bf 非 0x8876，两部署并存）。
- **scripts/robinhood/gas_trace_bs.py**：内置 alias 自检（self_alias 字段+金主聚合自动剔除），py_compile 通过。

### 实战记录（流程验证）
- /token-update 第三次实战（TRASH，超短窗 11.9h）：重叠窗校验/续传/滚动 JSON/缩放复核全流程顺畅；对抗复核两路因模型额度中断，重发一路合并版完成（47 tool calls），复核实质产出：矩阵指纹证据结构纠正+外延扩大（15→21 硬边址）+两跳扫描新发现一组+alias 缺陷捕获——**复核再次改写结论（历次 100% 命中率延续）**。
- 成本指标：主会话轮次 ~65、Bash ~50、活跃 ~3h（超 update 预算 40min，原因：①Fable 额度中断等待 ~40min ②bot 矩阵族为计划外重大发现，深挖+复核+简报重写占 ~1h——准确性优先于成本纪律）。

### Known Gaps（TRASH 下次更新重点）
- TRASH bot 矩阵族：G 组 5 址资金溯源未做（单次行为边）；矩阵族硬边 4.99% 贴线，下次更新重扫（过 5% 则正式判 P1 小庄）；B 组三胞胎窗口后收网的 ETH 小号网（5 址）动向待跟踪。

## [2.3.0] - 2026-07-14 — Pointless(Robinhood) 增量更新复盘（/token-update 第二次实战）

### Added
- **address-book.md Robinhood 段 +5 地址**：公共提款热钱包 `0x1887fa9e…`（1.1 万笔/1273E/单一金主补货 3666E/时均 ~50 收款人，曾被误当私人母钱包）、Relay/App 代币交付金库 `0xb92fe925…`（大额"转入"=市场买入）、RobinHoodSettler `0xe72688f7…`（App 结算器 518 万转账）、公共 relayer `0xabb2acd3…`、LiFiDiamond(Robinhood) `0xb477751b…`
- **data-pipeline-robinhood.md 方法论坑 +1**：★gas funder 公共性三步体检（counters 总笔数→余额量级→时窗收款人分散度）——App 托管提款热钱包伪装母钱包；据单一 gas 边建的聚类在 funder 被证公共后整体作废
- **analysis-playbook.md §6 补强**：gas 同源边未过公共性体检不得计为"强证据"（成边条件补注）

### 实战记录（流程验证）
- /token-update 第二次实战全流程通过：38,179 旧+12,793 增量（重叠窗校验一致）；U2 三查全过（供给闭合精确/双路径重放互验 0 不匹配/54 址归档 RPC 对表零误差）；观察哨 6 条 3 触发（dev 撤资/大户卖出/烧速失速）；新庄扫描阴性（26 候选四维排查+碎矩阵/时间指纹/wei 级面额/App 通道四项补充检验全过）
- 复核实效（"省采集不省判断"再验证）：B 路怀疑者**推翻本次初判"G_D 换马甲"**（元凶=公共提款热钱包伪装母钱包）并**连带瓦解旧报告 G_D 四址聚类**（唯一依据 gas 同源失效）、把"卖出或跨链两可"升级为"本地卖出实锤"（逐笔同 tx 进池）、补"dev 清空后队友补 gas 领 fee"集团协同铁证；A 路（攻阴性结论）经用户停止后由主会话本地补齐四项检验并如实入册
- "截断补全=编造"红线亲测再犯：给复核 prompt 时把截断地址 0x4c1b… 凭空补全，被怀疑者用链上数据抓获更正——教训条目已在 §6 硬规则，本次是执行层再犯，引以为戒
- 脚本抽象决策（用户定）：增量重放/归档对表/JSON 滚动通用件**再等一次**，第三次增量实战后抽象；本次标的专属脚本留存项目目录（replay_update/verify_balances/watchpost_check/build_update_charts/build_appendix_update）
- 成本指标：主会话约 50 轮、Bash 约 35 次、活跃约 2.5h（含复核 agent 一次限额中断+一次断连重续+跨夜等待）——轮次达标（<60），活跃超预算（agent 中断为主因，属外部环境非流程问题）

## [2.2.0] - 2026-07-14 — RAXOL(Robinhood) 增量更新复盘（/token-update 首次实战）

### Added
- **data-pipeline-robinhood.md 方法论坑 +2**：①★"归集出货 hub"定性前必查出账签名结构（出账 txfrom 全≠本体=被调用的合约工具非钱包枢纽；三步拆穿=txfrom 结构→getCode→Blockscout 全链计数；"经同一合约出货"永不构成协同证据；**单币用户数少≠私有**，判公共性看全链总 tx/币种数/调用者分散度）——RAXOL 旧报告把公共 bot 卖币执行合约误判为"39 上游协同出货网络"，增量复核推翻，误判根因=当时 RPC 盲区跳过体检 ②Virtuals Team 金库性质判定三步（getCode→owner()→平台 API tokenomics）：实测为 0age 最小代理+owner=平台 keeper，标准 vesting selector 全不响应
- **data-pipeline-robinhood.md 通道表**：Virtuals API 加 `populate[0]=tokenomics` 参数拿正式解锁表（isLocked/startsAt/linearBips/releases 全字段，问 4 解锁日程权威来源）
- **address-book.md Robinhood 段 +9 地址**：公共 bot 卖币执行合约 0x9be3cc59…（61.7 万 tx，曾被误判协同实体）、旧"漏斗"实为工具合约 ×2、原子中转小合约 0x3da661…、"共同上游"假集群元凶路由组 ×5（怀疑者复核揪出，增量新庄扫描前先剔）
- **update-workflow.md U0 资产表 +1 行**：gas 溯源数据覆盖期检查（增量窗口 gas 维度盲区要么 U1 补拉要么局限性声明）

### 实战记录（流程验证）
- /token-update 全流程首战通过：66,333 旧转账+9,440 增量（重叠窗按 (tx,logi) 去重无 off-by-one）；U2 三查全过（供给闭合精确/27 址对表含活跃设施同块高复查零误差/旧 25 实体基线复现 0 不匹配）；"新庄扫描在最新全量榜上做"与"沿用≠盲信"均产出实效——**增量复核翻出旧报告 2 个实体级误判**（协同网络+漏斗框架），证明"省采集不省判断"设计的价值；标准迁移标注全程执行（旧庄#N→大户组#N）
- 缩放版复核配置：2 路怀疑者 agent（攻"公共工具反转"判 CONFIRMED 附 4 马甲小簇局部保留；攻"无新庄"判 CONFIRMED 附 TOP5 压力注记）+ 本地反例自查（txfrom 结构检查即翻案元凶）
- 暂不收编通用增量重放器（用户定）：等第二次增量实战再抽象，避免过早固化
- 成本指标：主会话约 60 轮、Bash 约 35 次、活跃约 2h（等 2 路怀疑者约 25min）、简报 HTML 532KB WARN=0——轮次达标（<60 压线）、活跃超预算（复核深挖为主因，属不可省项）

### Known Gaps
- RAXOL 旧报告"12 个即收即卖漏斗地址经手 9.37%"框架需整体重审（本次抽检 6 个翻出 4 个非 EOA），留待该标的下次全量分析
- RAXOL 增量窗口 gas 溯源未跑（已在简报局限性声明），下次更新补

## [2.1.0] - 2026-07-14 — 新增增量更新模式（/token-update，用户定形态 A：轻量增量简报）

### Added
- **references/update-workflow.md（新文档）+ ~/.claude/commands/token-update.md（新入口命令，skill 外部）**：对已有研报做增量刷新的工作流 U0–U6——U0 旧研报定位与资产盘点（兜底分级：缺 JSON 从 HTML report-extract 抽 / 缺期末余额快照改链上实查重建、实查不可行降级建议全量 / 缺原始转账仅损失溯源回查并声明）→ U1 增量采集（**起点一律从旧原始数据末行取区块/slot/签名**，data_cutoff 仅人读参考；重叠窗去重防 off-by-one）→ U2 轻量对账（旧余额快照+增量重放、抽样对表=全部旧 P0+top20+随机 5、供给闭合复验）→ U3 增量分析（**新庄扫描在最新全量榜上做、禁止只扫增量流水**，新面孔与"其他大户"升级实体都算；旧实体四态对比；观察哨逐条核查；旧结论修正清单=沿用≠盲信；开放条款轻量版）→ U4 缩放版对抗复核（有新发现 ≥2 路怀疑者重算；无新发现本地反例自查=阈值边缘名单+窗口完整性；阴性结论同样复核）→ U5 轻量更新简报（五条直答骨架、目标体量 ≤ 全量 1/3、图 1 必配图 3 可选）+ appendix.json 滚动更新（旧版按 data_cutoff 日期存档，report-extract 四键与看板衔接零影响）→ U6 复盘照旧（预算参考：轮次 <60、活跃 <40min）
- **版本对齐铁律（用户 2026-07-14 指定）**：更新时一切判定标准与呈现规范以当前 skill 版本为准（阈值/标签/命名/措辞/schema），旧研报只提供数据资产与对比基线；实体判级与旧报告不一致必须标注"持仓变动 vs 标准迁移"，防读者把标准变化误读成庄家行为
- **report-template.md JSON schema：token 块新增 skill_version 字段（本版起新报告必填）**——增量更新靠它识别旧报告框架版本；旧 JSON 缺失视为未知旧版，全部实体按现行标准重判
- 实测确认 build_html.py 质检与标准图数量无关（只查引用图存在性+四键+地址完整），轻量简报（2 图）走同一管道零改动
- 何时不该增量（写入 update-workflow 末节）：缺余额快照且实查不可行 / 距上次 >2 个月或主战场迁移 / 新 P0 行为贯穿旧数据期（旧报告或整体漏判）/ 连续 3 次增量未做全量

### 影响面与兼容
- 修改文件：SKILL.md（新增"更新模式"节+深入阅读+1）/ report-template.md（token schema +skill_version 及字段说明）/ update-workflow.md（新）/ commands/token-update.md（新）
- 全量分析流程零变化；看板抽取零影响（四键/id 不动，appendix.json 滚动更新保持惯例位置最新）；本条目来自用户需求会话（非分析复盘），无成本指标

## [2.0.0] - 2026-07-14 — 框架级重构（用户审阅最新几篇报告后指定九条修改，主版本 +1）

### Changed（框架命题与标签体系）
- **五问改四问**：旧问③"每个庄建仓成本"从固定命题删除（§6b 降级为按需工具——出货获利/浮盈结论需要成本参照时就地算，JSON whale_groups 成本三字段改可选）；旧问⑤"官推什么情况"升级为**问④项目方背景调查**（创始人/项目历史含黑历史、推特/Discord/Telegram 运营、大V关注量、互动数与浏览量、热度综合评估与水军嫌疑；无项目方查 dev——research-workflows §1 路线 5 五块结构扩容，原官推侦查手段全保留为其 (b) 块）
- **庄级实体改 P0/P1 标签体系**（playbook §6a 重写，取代旧"庄#N + 峰值 ≥5% 总供应或 ≥10% 流通"单门槛）：项目方（P0，无论份额）/ 大庄（P0，当前 ≥20% 总供应或 ≥20% 流通）/ 小庄（P1，当前 ≥5% 或 ≥10% 流通）/ 离场庄（P1，峰值 ≥10% 或 ≥15% 流通且当前非庄）/ 狙击集团（单独标签永不与"庄"混排，当前 ≥20%/≥20% 为 P0 否则 P1）/ 刷量地址（单独标签，可关联时打复合标签"大庄#N·刷量地址"）。合并口径含全部疑似关联地址（无论证据程度）、同一时刻合并计算；其他大户（当前 ≥1% 总供应或 ≥2% 流通）与散户只出现在图 1、正文不分析。阵营划分表与 standard_charts.py CAMP_ORDER/CAMP_COLORS 同步重写（旧键保留兼容）；旧"首30分钟狙击者"cohort 降为解读工具（流量/存量双口径纪律保留）
- **图 1/图 2 前置**：两张标准图移到报告一、TL;DR 顶部（问 1 直答上方），原第五章改为演变解读章（不重复贴图）；图 2 更名"庄级实体持仓变动 vs 价格"，线色按标签前缀取语义色（_entity_line_color，同前缀多实体亮度递变）
- **正文呈现三硬性**：①所有代币数量后带【总量X%】换算②钱包一律标签制（项目方钱包#1/大庄#1钱包#2），正文（含表格）零地址，完整地址只在附录 B 对照表与 JSON 附录③行内置信度/证据 tag 全部取消（[HIGH/MED/LOW]/[单源]/[INFERRED]/[UNPROVABLE]），纪律本身保留改自然语言（SKILL 铁律 3 重写；playbook §11 更名"措辞纪律与证据强度"）
- **监控建议两档制**（第七章收尾必做+JSON monitoring_advice 加 mode/label/alert_threshold_pct/reason 字段）：a) 转出即预警（理应沉睡地址，逐条写为什么理应沉睡）b) 减持阈值预警（会正常活动的地址，默认累计减持 ≥1% 总供应触发，逐条写为什么不能转出即报+为什么这个阈值）

### Added
- **scripts/report/lifecycle_flow.py（新脚本）+ references/examples/lifecycle-flow-sample.png（新样图）**：全周期流转路径图——每个 P0 级实体必配（币从哪来→中转/拆分→终点，账目行配平，意图不可区分并列写）。数据驱动自动布局取代旧 chart_style.flow_box 手摆坐标，解决文字拥挤：框高按行数自适应（行距 1.55×）、箭头标签白底垫片+同源出边自动错开、账目行独立灰条、超长文字 WARN；防拥挤排版纪律（标题 ≤14 字/行 ≤16 字/边 label ≤2 行/每列 ≤5 节点/列 ≤5，超限拆图）写入 report-template
- report-template.md 新增「标签体系与重要度分级」「全周期流转路径图」两节；章节骨架重排（三、庄级实体识别按 P0→P1 排序呈现；六、项目方背景调查；七、状态+观察哨+监控建议合章）；checklist 重写为 13 条

### 影响面与兼容
- 修改文件：SKILL.md / report-template.md / analysis-playbook.md（§6a §6b §11+框架头）/ research-workflows.md（路线5）/ data-pipeline-solana.md（编号引用）/ standard_charts.py / lifecycle_flow.py（新）/ 样图（新）
- **看板抽取零影响**：JSON 顶层四键、id="report-extract"、id="chart-camps" 约定不动；addresses 字段集不变（role 改为标签开头）；whale_groups 加 tier 字段、label 换新标签格式
- 待定项（下次分析实战校验）：狙击集团 P0/P1 判级采用"当前持仓"口径（用户原文主句"重要程度取决于当前持有量"与括号"峰值"表述存在歧义，已按主句执行——若用户要峰值口径改一行 §6a 表格即可）

## [1.14.0] - 2026-07-14 — TRASH(Robinhood·Uniswap CCA拍卖台) 分析复盘：V4采集脚本补盲区 + 第4类发射台全解 + LP锁仓判别法 + 拍卖协同集团识别

### Added
- **scripts/robinhood/pull_swaps_v4.py（新脚本，补 CASHCAT 遗留的 V4 采集盲区 Known Gap）**：Uniswap V4 单例 PoolManager 的 Swap+ModifyLiquidity 全量采集，按 `topic1=poolId` 过滤（不是按池子地址）、断点续传、解码失败计数上报；config 填 `swap_pools_v4`(poolId 数组)+`pool_manager`。实测 4.7 万条约 4 分钟。config.example.json 同步加 V4 字段。**topic0 实测常量**：Swap=`0x40e9cecb…d7112f`（data 6 字：a0,a1(带符号 int128),sqrtPriceX96,liquidity,tick,fee）、ModifyLiquidity=`0xf208f491…711d5ec`（data 4 字：tickLower,tickUpper,liquidityDelta(带符号),salt）
- **data-pipeline-robinhood.md 坑 10：Uniswap 官方 Liquidity Launchpad 发射结构（第 4 类发射台，前三为 Virtuals/NOXA/Flap）**：2026-07-13 上线该链，permissionless（app.uniswap.org no-code 发射）。全套 canonical 基建地址（UERC20Factory/LiquidityLauncher/CCA 工厂/LBPStrategy 单例/V4 PositionManager keeper，全部对上 Uniswap GitHub 部署表）+ CCA 连续清算拍卖机制（逐块统一清算价、供应分时释放、防狙击靠跨块时间分布）+ 创建者收益三通道（LP 1% 池费/组池余数/自配 Distribution）；协议费当前=0
- **data-pipeline-robinhood.md 坑 11：LP position NFT 归属与锁仓判别法**：LP NFT 铸给创建者 EOA **≠ 无锁**——必查 `PositionManager.ownerOf(tokenId)`（selector `0x6352211e`）；owner=合约则读源码判真锁（UniV4PositionLocker 的 `LOCK_DURATION`/`unlockTime`/`beneficiary`/`StillLocked`；实读 `unlockTime()=0x251c1aa3`、`beneficiary()=0x38af3eed`）。协议原生亦提供 TimelockedPositionRecipient/BuybackAndBurn 选件
- **data-pipeline-robinhood.md 坑 13：V4 ModifyLiquidity 的 liquidityDelta 符号=撤池 vs 领费判据**：`<0`=撤本金（真撤池）、`=0`=纯 collect 领费（本金分毫不动）、`>0`=加池——不查符号会把"领费"误判成"撤池出货"；领费的 token 腿卖出=永续机械卖压，单列勿混"庄家出货"或"撤池"
- **data-pipeline-robinhood.md 坑 14：V4 swap 归因用同 tx Transfer 净额**，UniversalRouter `0x8876…` 替散户透传会虚高毛卖量（净额归因终端买卖家，或先把路由从集团名单剔除）
- **analysis-playbook.md §6a +3 条**：①CCA 拍卖型发射台协同集团识别（"前 N 分钟零出价→末分钟同窗口挤兑"是机制诱导非协同实锤，协同定性须靠资金硬边=拍卖中互转弹药/wei 级同额桥入/私有出纳预注资/组内 gas 互供）②多硬边簇无直接币流边、仅靠公共 gas 分发台连接时按"N 簇+疑似成员"分层报，"单一实体"作合并主张单独陈述③拍卖内盘成本=出价净额非毛额（退款从毕业 tx internal-tx 反查）
- **address-book.md Robinhood 段 +6**：Uniswap Launchpad 全套基建（UERC20Factory/LiquidityLauncher/CCA 工厂/LBPStrategy 单例/V4 PositionManager keeper）+ Robinhood 7702 标准实现 `0xe6cae83b…`

### 复盘备注（方法教训）
- **对抗复核再次实质改写**（延续历史 100% 命中率）：7 路（6 怀疑者+1 完整性批评）→ CONFIRMED×3 + WEAKENED×3 + REFUTED=0。三处 WEAKENED 均实质改写：①**"LP 无锁可随时撤池"结论整条被 ownerOf 查询推翻**（NFT 已锁进创建者自建 locker，真锁 365 天）——教训固化为坑 11"LP 铸给创建者≠无锁，必查 NFT 当前 owner"②聚类名单剔除一个公共路由（原误判为"私有出货漏斗"，实为 Uniswap UniversalRouter 替散户透传，只数集团内入边未数全量来源所致）③毛卖量口径含路由透传需改净额。完整性批评抓出**阴性排查漏检达标狙击簇**（只按当前余额口径扫簇、未按峰值口径扫——修法：达标簇即使已离场也要列为"离场狙击庄"）
- **★版本竞态 + 并发写者双教训**：开工读 CHANGELOG 首版号=1.13.0，交付时头部已是 1.13.1（并发会话文档小修）——V4 采集本是空白无重复造轮，但再次印证阶段 0 版本自查必要；另**实测发现并发会话会编辑同名工作文件**（本次报告.md 与 build_appendix.py 中途被外部改动，出现半截字符串语法错误、CHANGELOG 被写入垃圾行与重复标题）——新纪律：交付前对报告 md 与 build 脚本做一次语法/残留自查（`py_compile` + grep 旧数字），别假设自己是唯一写者；skill 文件写入后立刻重读核验（本条目即因并发污染重写一次）
- **成本指标**：约 140 轮、Bash 约 60 次、活跃约 2.5h；调研 4 agents 41.9 万 tokens + 复核 7 agents 84.5 万 tokens；交付 563KB 自包含 HTML 零 WARN、对账三查全过（供给闭合误差 0、余额 20/20、时间 3/3）、复核 REFUTED=0

### Known Gaps（TRASH 分析遗留，投后监控期可续溯）
- 庄#1 内部 3 个资金硬边簇是否单一实体链上无法定案（gas 分发台 `0x3807771d` 中等强度连接）——OTC/工作室悬置
- gas 溯源 84/412 候选 funder 为空（7702 paymaster 代付/桥直入），App 内部撮合不上链——聚类系统性盲区
- V4 采集脚本目前只拉 Swap+ModifyLiquidity；Donate 等其他 V4 事件未纳入（本次标的无关，遇到需补对应 topic0）

## [1.13.1] - 2026-07-14 — 文档小修：TAG/置信度纪律收归 skill 自身（清除对全局 CLAUDE.md 的悬空引用）

- SKILL.md 铁律 3 与 report-template.md「TAG 与置信度呈现」节原标注出处为"用户全局 CLAUDE.md 纪律"，该全局条款已被用户删除、引用悬空（静态抄录无同步机制所致）。经用户确认（2026-07-14）：**纪律本身保留不变**，仅改出处表述——今后此纪律以 SKILL.md 铁律 3 为唯一事实源，不再依赖任何外部文件。

## [1.13.0] - 2026-07-14 — OPAL(Solana·pump.fun) 分析复盘：Base-Solana 官方桥地址库 + 两条控盘新指纹 + owner级边表漏边补扫 + 版本竞态教训

### Added
- **address-book.md Solana 基础设施 +3**：Base-Solana 官方桥 Bridge 程序 `HNCne2FkVaNghhjKXapxJzPaBvAKDG1Ge3gqhZyfVWLM` + Base Relayer `g1et5VenhfJHJwsdJsDbxWZuotD5H4iELNG61kS4fb9`（Solana→Base 跨链，出现在"代币转股权/ACE 轮"项目——币桥到 Base 侧锁仓/股权化）；桥托管仓判别（散户几天内桥出汇入的整数配额托管仓＝跨链募集非市场买盘，判别=入账 tx 涉及桥程序）（OPAL 实测）
- **data-pipeline-solana §3b 控盘指纹 +2**：⑥**母钱包代付创建落仓户 ATA**（落仓户收币前无链上生命、其 token account 由付款方母钱包同 tx 代付创建＝凭空生成空壳收款方，比 gas 同源更强、换钱包换不掉）；⑦**跨地址凑整回补**（N 笔碎额从一址精确凑整数目标补入另一址、使多落仓户终局配比成整数＝单一记账者全局配平铁证，独立主体不会为凑别人仓位分 15 笔转账）
- **data-pipeline-solana §3a 坑 +1（坑7）**：owner 级签名史对"纯接收巨仓"漏入账边（转入 tx 只提及收款 ATA 未把 owner 放进 accountKeys）→ 边表节点"流出>流入"负净额；正解=对不配平节点走 ATA 级补扫（现有 probe_token_account_history.py / whale_deep.py），全节点净流配平后边表才可信

### 复盘备注（方法教训）
- **★版本竞态实付代价**：开工读的是 1.11.x 的 data-pipeline-solana.md，**漏看 1.12.0 新增的 `replay_edges.py`（SQD 边重放引擎，含 evolution 阵营序列+reconcile 对账+mints 铸造边清单）与 `whale_deep.py`（ATA 级深挖含销户反查）**——导致本次手写了 build_camp_series（≈replay_edges evolution）+ 手写 ATA 补扫（≈whale_deep），重复造轮约 2 个脚本。**新纪律：阶段 0 自查除读 CHANGELOG 首个版本号外，必须读首条 Added 全文 + `scripts/<chain>/` 目录 ls 一遍**，确认没有现成脚本再动手（SKILL 阶段 0"版本号变了提示框架已迭代"应升级为"版本号变了必须读新条目的脚本清单"）
- **对抗复核再次实质改写**（延续历史 100% 命中率）：6 路 CONFIRMED×4 + WEAKENED×1（06-28"独立交易者"被推翻为"关联投资集团/候选庄#3"——上游 2 户有 2024-12 直接转账+同 KuCoin）+ 完整性批评抓出发射狙击 3 巨鲸漏报（按门槛应走排查=离场庄）；还抓出**数据文件缺笔硬伤**（trace_creator_ata.py `if not tx: continue` 对 getTransaction 失败静默跳过，漏第一期锁仓流出笔，配平靠 ±1 亿抵消"碰巧对"）——脚本纪律：解码失败必须计数上报，收尾核对"log 成功数 vs 文件行数"
- **RPC 三方挤兑**：主会话 + 多个后台采集脚本同打 api.mainnet-beta 互相 429/超时（trace_upstream 前台 7 分钟被杀、network_full 走代理龟速）；缓解=①脚本改**直连**（本机 clash 环境对 api.mainnet-beta 直连比走代理快且稳，与旧 pipeline"走 clash 代理"表述相反，存疑待多机验证）②后台任务**串行链**（用 `until grep -q DONE 前一个.log` 排队，不并发抢配额）③断点续传逐地址落盘（超时重启不丢进度）
- **发射狙击盘净持仓峰值失明**：内盘 bonding curve 反复买卖，launch_buys 只录买入边，单地址"累计买入 7.7%"≠净持仓峰值——已清仓离场庄的净持仓曲线是快照封口架构固有盲区，措辞用"累计买入达门槛、列离场狙击盘"+局限性声明，不硬报净持仓峰值
- **成本指标**：约 130 轮 API 调用、Bash 约 75 次、活跃约 4.5h（超时主因=RPC 三方挤乎 trace 脚本被杀 2 次+走代理龟速重跑，非流程低效；但重复造轮 2 脚本是版本竞态净损）；调研 5 agents 56.6 万 + 复核 6 agents 64.6 万 tokens；交付 656KB 自包含 HTML 零 WARN、对账三查全过、复核 REFUTED=0

### Known Gaps（OPAL 分析遗留，投后监控期可续溯）
- 拆仓网络（庄#2）身份三选一悬置（独立操盘方/项目方影子/OTC desk 代持）——币源系市场买入+creator 零外转已排除"项目方影子"，但顶端 gas 源 `DGHii8nL`/`9AWQ5Lm1Jp3oLWpE1UFffg8mngwehAAchfbcFqAvSzw` 的 SOL 来源未溯（网络真实规模可能>22 地址）
- `3Cw4F7a…` 07-01~03 补给拆仓网络的 1,000 万枚上游未深挖，成本未知（净投入区间 $18k~$37.6k 的不确定来源）
- 候选庄#3 第三户 `4CNJAV` 与另两户的关联仅"行为同构"无直接转账实锤（2/3 户实锤）
- creator fee vault SOL 手续费收入总量未量化（"项目方零卖出"的隐性获利对冲项，仅定性）

## [1.12.0] - 2026-07-14 — PUB(Solana·pump.fun) 分析复盘：铸造边全清单必查 + 质押合约判别五步法 + 目标余额驱动镜像指纹 + Solana 脚本 5 连收编

### Added
- **data-pipeline-solana §2a 自建质押/托管合约判别五步法**：owner 程序两跳 → executable+loader → ProgramData(data[4:36]) 部署时间对表 → **upgrade_authority(data[13:45]) 是否放弃必查**（未放弃=项目方可单方面升级转走托管资产，必须进报告风险章）→ 部署者 gas 溯源闭环；配套账本验证（净额 vs 池链上余额对表、"取回>存入"排除归集仓伪装）。**触发纪律：transfer_in 型大户两跳判别先于庄家定性**（本次 13.57% 供应"疑似 dev 分仓"经此反转为官方质押池）；质押池确认后全部持仓分析做质押修正（有效持仓=现货+池内份额）。playbook §3 兜底边界同步加链无关版
- **data-pipeline-solana §8 第 5 条：★铸造边全清单必查（pump.fun 币第一优先检查项）**——创建 tx 铸造边可有 2 条，dev-buy 直分收币地址可不是 creator 本人；本次创世直分 4.24% 供应主分析漏掉靠复核抓回（恰是"项目方系已套现一轮"最强证据）。固化动作：边加载后第一步 `replay_edges.py mints`，creator 系从"创建 tx 全部受益地址"起步
- **data-pipeline-solana §8 第 6 条：curve 成本重建参数校准法**——标准参数(30/1073M)枚数逐位精确但 SOL 成本系统性低估约 10%；关键笔用 getTransaction pre/postBalances 实付真值校准，批量笔 +10% 区间；毕业迁移笔混入买家列表必须剔除（SOL 疑 wSOL 双计），迁移真实 SOL 用 GT 开盘价锚定
- **data-pipeline-solana §4**：pump.fun v3 creator 履历三端点（/coins?creator= 发币前科 / /users x_username=null 证明官推无平台绑定 / /balances 站内口径）；RugCheck insiderNetworks 免费层 size 有值但成员列表空（只当计数用）；GMGN 正规 key 通道 holders --tag / traders --order-by profit
- **analysis-playbook §6a**：★"目标余额驱动"镜像指纹（卖出量互不相同、卖后余额双双精确修剪到同一整数 raw 级零误差——直接排除跟单 bot：跟单会"卖出量同、余额不同"与观测相反；强度排序 同额整数仓<秒级同步<目标余额驱动）；CA 公开前窗口量化标准件（净买清单+占比+现持仓归零率；措辞"信息不对称窗口"非"内幕"）；离场庄亚型分层呈现（闪电 bot/小时级/数日波段，防"N 个庄"印象失真）
- **analysis-playbook §9**：外盘 wash 毛流量口径三件套（主池毛流出/供应比 + 单址双向毛流量 top + 净≈0 判往返 bot）；暴跌归因毛卖压/净卖压分开列（本次 ATH 后毛卖 top5 有 4 个净≈0 bot）
- **environment.md**：★Bash 工具沙箱杀多进程并发脚本（16 并发 curl 两次被杀 exit 144 零日志、串行无恙；正解 nohup+disown+dangerouslyDisableSandbox 脱管；连带发现进程组级清理会波及其他会话进程）
- **research-workflows §四 坑表 +2**：坑 9 后台长任务输出禁接 `| tail`（缓冲吞进度，失败死无对证；日志直写文件，存活看 ps CPU 时间）；坑 10 TaskStop/pkill 进程组误伤（kill 精确到 PID、链式任务合并单条、关键长跑脱管）
- **research-workflows §一官推路线**：X API full-archive 可分页拉官推全量原创推文（本次 631 条，停更/复活时点精确到分钟）；twitterscore Renamed 记录再确认
- **scripts/solana/ 5 连收编（全部参数化+py_compile 通过+零标的残留）**：`replay_edges.py`（SQD 边重放引擎：reconcile 对账关卡/trace/top/sniper/mints 铸造边清单/evolution 阵营序列含质押修正——原 replay+camp_evolution 合并，全量重放路线下游标准件）、`stake_decode.py`（托管池账本解码+自动闭合验证）、`gas_origin.py`（批量 gas 溯源，mint 无关）、`whale_deep.py`（大户 ATA 级全量流水深挖，三级 ATA 发现含销户反查+--known-sig）、`curve_cost.py`（bonding curve 成本重建，--grad-price 自校准/--exclude 剔迁移）；另 `fast_probe_tops.py` 的 SKIP/EXTRA 硬编码改 PROBE_SKIP/PROBE_EXTRA 环境变量

### 复盘备注（方法教训）
- **初判"dev 系分仓 19.4%"被两跳判别整体反转为官方质押池**——transfer_in 大户前置判别纪律就此固化；升级权限未放弃风险由复核 agent 用 RPC 抓出（复核再次实质改写：6 路两轮 11 处修正含 1 项完整性 HIGH 缺口=创世直分仓）
- 地址截断补全**再犯未遂**（凭记忆补全 16 字符截断地址的后半段，实际完全不同，自查拦下重取落盘文件）——探针类脚本 stdout 已改打完整地址；"关键地址一律从落盘文件取"仍是最高频失误点
- critic 首跑 API 中断失败，resumeFromRunId 二次跑通（5 怀疑者缓存命中零重跑）——resume 机制两战两胜
- trace_wallet.py 查 owner 不查 ATA 的老坑让链式任务空跑一轮——ATA 级正解已由 whale_deep.py 固化
- 成本指标：约 105 轮 API 调用（历史 66~150 中位）、Bash 约 60 次、活跃约 3.5h（超时主因=沙箱杀 SQD 两次净损约 50 分钟，非流程低效——skill 固化脚本 6 个直接跑、仅 1 个需小改）；调研 workflow 4 agents 32.8 万 + 复核 6 agents 63 万 tokens；交付 748KB 自包含 HTML 零 WARN

### Known Gaps（PUB 分析遗留，投后监控期可续溯）
- 庄#3（CrNJGDXz…）SOL 资金上游只溯到一跳（CNBcM2X3D6…无标签）——"外部鲸鱼 vs 操盘方执行器"二选一悬置
- 庄#1（6UxyrqEvsX…）首笔非 SOL 入金的上游未深挖；8GnV91zz…（53.4 SOL 金主）身份未明
- 9 个离场庄 gas 同源未全量排查（币面零互转已验证）
- 外盘 ≥10 个 wash bot 是否受雇项目方链上不可证（官方自述 "Dex paid" 的关联），留作背景疑点
- 多组 1%+ 钱包间原额往返/倒仓（各 1-1.8% 未过庄家门槛）未逐组深挖，监控期异动再查

## [1.11.1] - 2026-07-13 — 监控抽取块硬性标准落地（用户看板方指定格式；文档 + build_html.py 同步改）

### Changed
- **report-template.md「JSON 附录 schema」章节重写**：新增「监控抽取块硬性标准」节——HTML 末尾 JSON 必须嵌为 `<script type="application/json" id="report-extract">`（**看板只认此 id**，曾因自定义 id 抽取失败）；顶层四键必备 chip_summary（zhuang_count/total_share_pct/total_tokens/last_action）/ addresses / unlock_events / source_line；addresses 字段纪律：完整地址不缩写、chain 小写枚举、group 同集群同名（组内互转不算流出）、**sentinel=true 只给理应长期沉睡的地址**（空投池/税池/做市/奖励池等周期性会动的必须 false，防天天误报红卡）、watch=false 也要列出便于审计、可选 round_target（整数橱窗仓破整红卡）与 watch_return（离场庄回场红卡）；阵营演变图须可被 `id="chart-camps"` 或 alt 含「阵营」定位（看板自动抽独立 png）。原详细键（token/whale_groups/vault_addresses/camp_share_series/key_events/monitoring_advice）与四键并存于同一 JSON，键名不变
- **build_html.py**：嵌入 id `chip-json`→`report-extract`（含 docstring 提取示例）；--json 顶层缺四键、addresses 现省略号/星号缩写地址时打 [WARN]（沿用有 WARN 不许交付纪律）；自动给 alt/题注含「阵营」的第一张图加 `id="chart-camps"`
- **SKILL.md 阶段 5 + reference 清单**：补监控抽取硬标准提示（四键 + report-extract）
- 交付前 checklist 第 8 条扩充：四键齐 / sentinel 纪律复查 / round_target·watch_return 该填的填了 / 两个 id 目检

### 复盘备注
- 本条由用户监控看板方反馈驱动：历史报告 JSON 附录 id 与结构不统一（如 chip-json）导致看板自动抽取失败——交付格式从此以看板抽取端为准；旧报告（GME/CASHCAT/VEX/CLUDE 等）如需接入看板，须按新 schema 补四键重出 HTML

## [1.11.0] - 2026-07-13 — CLUDE(Solana·Token-2022) 分析复盘：Token-2022 大扫描分支实战 + Solana 脚本库 6 连收编

### Added
- **data-pipeline-solana §0a**：双 RPC 矩阵新增 Token-2022 大扫描行——**与 SPL 行为相反**：publicnode 504（疑无 Token-2022 mint 二级索引）、api.mainnet-beta 放行无 dataSize 全扫（16,186 账户 4.6MB 45s）；§1 Token-2022 坑预警升级为实战版（165/170 双形态外还有零星其他 dataSize，165/170 双扫漏 0.036% 供应不闭合，正解=无 dataSize 全扫）
- **data-pipeline-solana §0b 死亡名单**：GMGN 全路径被 Cloudflare 拦（07-13 实测 UA+Referer 伪装失效，§4 原绕过法同步标注失效待重探）；web.archive.org CDX 对 x.com 个人页零快照（官推旧名回溯此路不通）
- **data-pipeline-solana §3a 流水坑 +3**：④高频钱包 owner 级签名史稀释→ATA 级签名史正解（销户后从已知 tx 的 tokenBalances 反查 account）；⑤镜像 vanity dust 投毒（仿真实大额对手首尾、操作后 16-19s 跟发）——密集同窗签名不可当关联证据、反向可佐证真实资金关系；⑥中转钱包时间窗解码必须校验 NET≥0（漏流入边致物理矛盾）
- **data-pipeline-solana §2 Streamflow**：data_len=1104 布局固定偏移速查（9 创建/33 到期/409 start/417 净存/441 cliff 三处互验）+ **cancelable/transferable/automatic_withdrawal 标志位必读**（一次性 cliff 判定法；transferable=0 直接反证"受益权可转让"通用话术）
- **data-pipeline-solana §8 SQD**：吞吐量化预期（发射高密度段 90min/2.3 链上小时 ≈1.5x 实时、常规 ≈4x）→ 4-5 个月币龄全程重放不现实，Plan B 架构（发射窗 SQD 精确+核心实体 RPC 全流水+池子 CPMM 重建+散户残差+快照封口）为标准替代；CPMM 中段实测端点偏差 35~49%（小时K 取样的 10% 是侥幸值），必须声明"仅供形状参考"
- **analysis-playbook §6a**：峰值声明必须有数据点（单调增实体峰值=现值，"≥X%"无点支撑会被复核推翻）；同秒/同块狙击全景纪律（防"最大狙击者"印象失真）
- **analysis-playbook §6b**：配价合理性下界自检（不得低于成交所在 K 线 low）；流量 vs 存量口径自问（"累计"必须是加总不是快照——存量误作流量可差一倍）；出货量毛/净双口径；退出深度比三层递进（双边 TVL→对手币侧承接→恒定乘积滑点实际可提取比）
- **analysis-playbook §7**：滚动锁仓观察哨三规则（标志位必查后才写风险提示/续锁基率量化不写"每次都续"/到期过渡窗取历史最长空窗防误报）
- **scripts/solana/ 6 连收编**（原 IO 待重建清单 1+2 项就此勾销）：scan_token_accounts.py（Token-2022/SPL 双分支全量扫描器）、trace_wallet.py（单钱包全流水解码）、fast_probe_tops.py（大户快速画像）、probe_escrows.py（escrow+Streamflow raw 解码）、probe_wallet_batch.py（批量钱包画像+SOL 流向）、probe_token_account_history.py（ATA 级签名史）——全部 py_compile 通过，MINT 读环境变量/工作目录 config.json

### 复盘备注（方法教训）
- **流量/存量混淆是本次最实质的数字错误**（创作者费存量 33M 被写成"累计"，实际流量 56M，复核用逐笔加总+三处去向闭环抓出）——已固化为 §6b 自问纪律
- 手敲时间戳三连错（05-18/05-15/05-13 全错，图 3 重绘两次）+ 地址截断补全再踩 2 次——"程序化提取时间戳、地址从落盘文件取"两条纪律仍是最高频失误点
- 对抗复核 5 路（两轮跑完，第一轮 evolution 先行+第二轮 4 路基于修正后数据）再次实质改写：2 REFUTED（阵营加总/散户残差誊写）+ 4 WEAKENED（峰值无点/费口径/配价低于 low/近似声明）+ 2 项完整性 HIGH 缺口（3 月周期漏报/隐鲸群未筛查）当日补查完成——投入产出比继续最高
- session limit 与 Fable 5 用量限额先后两次打断复核 Workflow，靠 resumeFromRunId 断点续跑恢复（缓存命中机制有效）
- 成本指标：约 150 轮 API 调用（超 150 参考预算的原因：复核触发的两项 HIGH 缺口补查+第二轮全量修订均在同会话完成）、Bash 约 85 次、活跃约 6h（全程跨 12h 含限额等待）、交付 HTML 948KB（复核 workflow 两轮 98 万 tokens、调研 workflow 约 45 万 tokens）

### Known Gaps（CLUDE 分析遗留，下次同链分析或投后监控期可补）
- 隐鲸 3y5VNvpV 出货窗口未解（ATA 已销户且 owner 级 4000 签名抽样无 CLUDE 笔——可试 SQD 窗口内买入边定位 slot 后 getBlock 反查）
- 庄#3 更上层金主 DQ5JWbJyWdJe（03-08 注资 59.3 SOL）未再上溯
- defAh9DW 程序身份与其 PDA authority（2476 字节 data 布局）未解
- 同型整数仓 6+1 个（2.35%+1.9%）未做庄#3 同源排查；shill 账号名单未落盘
- 3 月周期买卖主力未归因（SQD 覆盖限制，隐鲸假说已排除）；sebbsssss 03-26 前推文不可检视（X API timeline 返回受限）

## [1.10.0] - 2026-07-13 — VEX(Robinhood) 分析复盘：Virtuals BONDING_V5 全解 + cost_engine 汇率 bug 修复

### Fixed
- **scripts/robinhood/cost_engine.py**：quote_usd() 秒/毫秒不匹配 bug——K线 key 为币安原生毫秒时旧版 bisect 恒取首根收盘价当全程汇率（USD 数字最大偏差 ±17%），改为单位自适应（key>1e12 判毫秒）。对抗复核抓出，Pointless 期产物如需复用建议重跑

### Added
- **data-pipeline-robinhood.md**：Virtuals 发射结构条目升级为 BONDING_V5 全解（Team 25% 合约锁仓 vault+ACF 25% 价格触发阶梯变现直付创始人、拨付仓=疑似内盘反狙击税回收、创始人收入=ACF 本金+税分成 70%、其 USDG 再分发是挖关联网主线索、挂单≠卖出的图2 会计注记纪律）；DS pairCreatedAt 改两说并列（GME=准 vs VEX 偏差 11.5h，一律以链上首笔定毕业时刻）；transit 名单二次分层法（txfrom 用户数+上游集中度分公共/私有漏斗，防庄家出货通道被当基础设施剔除）；多池标的 cost_engine 三要点（非 WETH 报价用币安K、POOLS 须含内盘 pair、双报价币分开算）；Virtuals API 档案直查+LP 锁定一次验证法
- **address-book.md Robinhood 段**：+8 个 Virtuals 平台设施（跨项目 keeper 0x81f7ca、批量执行合约 0x3eb3(Multicall3 变体)、内盘 router 0x8a19、TokenFactory 0xd4cc、部署 funder 0xe4a0、AgentTaxV2 0x6d80、税 swapper 0xf36f）——核心提醒：金库2 类 EOA 与平台 funder gas 同源=平台设施证据非项目方私钱包证据

### 复盘备注（方法教训）
- 复核文本里的地址截断补全再踩 2 次（0x993e/0x99a8 尾部抄错、交付前从落盘数据核验揪回）——"地址一律从落盘文件取"纪律仍是高频失误点，建议交付前把附录B 全部地址跑一遍落盘文件 grep 核验
- 对抗复核 5 路全部返回且再次实质改写结论（0 REFUTED 但 15 处修正：汇率 bug/时间线错误/叙事补全"关联网双向操作"/口径统一），投入产出比继续最高
- 成本指标：约 100 轮 API 调用、Bash 约 65 次、活跃约 3h、交付 HTML 959KB（对抗复核 5 agent 54.6 万 tokens、背景调研 5 agent 45.4 万 tokens）

## [1.9.0] - 2026-07-13 — 他机 8 币会话考古合并完成（第二批净增量约 20 条 + 补记第一批）

### 背景
用户自 Windows 虚拟机导出 8 份投研会话记录（CZ/ASTEROID/TCC/人生K线/bibi/CLAW/CASHCAT/GME），经验提取汇总文档见 `~/Desktop/老公用/fable筹码分析/他机会话记录_经验提取汇总_8币.md`（该文档第 10 节含用户已拍板的全部落位决策）。**第一批合并**（2026-07-13 凌晨会话，04:01–04:14 写入）已进 evm §7 零门槛免注册通道全节 / §6 four.meme·V3 topic·48club 死亡名单修正、playbook §9a 死币复活盘 / §6 跨代币共现聚类·逆向找历代马甲 / §7 派发前兆 / §9 克隆镜像空投·wash bot 指纹、solana §0a publicnode 3-4 天签名坑 / §2 Streamflow / §3b 控盘团伙指纹 / §4 GMGN vas·RugCheck·Bags、research-workflows 官推回收账号侦测·Workflow 编排增强、address-book 二级热钱包·聚合器桥·Giggle·7702 delegate·Solana 平台段等——**但未记 CHANGELOG，本条目补记**。本次为**第二批**：全量对照 10 份文档逐条去重后写入剩余净增量，原则=只新增不重复（用户拍板）。

### Added（第二批）
- **analysis-playbook §6**：vanity 定制地址两用法（中段配对自证同源=铁证 / 前缀仿冒基建伪装分发，识别互为镜像）；注资证据分级标尺（私人 gas 钱包 <20 笔供多母钱包=强 / 同窗批次 ~90 分钟集中入金=中 / 公用桥·CEX 同源默认剔除、仅同 48h 窗+行为一致才升中等）；共现聚类补两判据（同区块共买 ≥85–90% 且中位时差 0 秒=同一实体铁证；区块内位置恒差=同一引擎）；证据边新增"小额测试转账紧跟大额"同人验证指纹
- **analysis-playbook §6a**：整数配额橱窗指纹（精准 1% 配额 / 整数枚仓 / 整数比锁仓，ETH/BSC/Solana 三链均见；与售罄参数整数、§7 破整信号互相区分/联动）
- **analysis-playbook §7**：派发前兆族谱（藏仓归位 / 蚂蚁搬家等额切片喂 bot / 沉睡收币大户通电 / 换仓双钱包 / wash 掩护阴跌出货）；评估维度新增发射台币创作者费现金流（"靠费吃饭"型动机结构）
- **analysis-playbook §3**：标签冲突裁决——浏览器官方标签 > 工具/tracer 转述
- **analysis-playbook §6b**：退出深度比呈现维度（持仓账面 $ ÷ 池子退出深度 $）
- **data-pipeline-evm §7.3 增强**：mevblocker archive eth_call（历史块 balanceOf 重建余额曲线）+ 缓存台账截断坑；老币 top~200 定向台账免 key 拓扑；大窗口二分细分片纪律；publicnode 块限 2 万/5 万两说并列；eth.blockscout.com/api/v2 与 Robinhood Blockscout 同栈说明
- **data-pipeline-evm 新增 §7.5**：BSC 老币免 key 三段拼接采集拓扑（48club 近 6 天 + BscScan 深历史 + GT 日线；输出形态=结构快照+6 天净变动+fresh/old 大户分层；创世期空白可视化证法）
- **data-pipeline-evm §6**：four.meme 连环盘指纹（同创建者连发多币+同一收币钱包）与致敬币变体（KOL 收币钱包+捐赠/自转印证）+ 毕业价曲线参数反解；§7.1 保留窗口二分探测通用法；§7.2 磁盘缓存抓取层模式（sha1(url)+单线程限速）；§2 死亡名单补 Routescan（不支持 BSC）与 api-legacy.bubblemaps.io（400 两场验证）
- **data-pipeline-solana §2**：Streamflow 补 recipient 激活状态检测（fresh keypair 不存在=休眠+受益人时序画像）与"锁仓流可由受益人转让"措辞纪律；§4 补 pump.fun API v1 死/v3 可用；§0b 死亡名单补 solana.drpc.org（400）/extrnode（SSL）
- **data-pipeline-robinhood**：公共 RPC getLogs 实测参数（40 万块/请求、单次上限 1 万条、5.6 万条 ~81s；批量 getCode 429 退避）
- **report-template**：死币复活盘特有章节现成模板指引（用户拍板：模板在此、信号清单留 playbook §9a）；JSON 附录→投后监控衔接句（用户批准；监控系统本身不属本 skill）；净流向/留存图幸存者偏差图题声明纪律
- **SKILL.md 踩坑速查**：until 前台等待受 Bash 10 分钟超时上限约束（exit 143），超时等待必须 run_in_background/Monitor

### 决策与去重记录
- 8 币汇总文档第 10 节 6 个待拍板点均已由用户在前序会话决策，本次照办：48club+BscScan 直抓入 evm 决策树（第一批已完成）；BSC 块间隔 0.45s 与本机 evm §6 锚点条目已一致（无需改）；bibi/GME/CASHCAT 重合内容只取净增量；投后监控只加衔接句；死币复活盘=report-template 模板+playbook 信号清单；8 币间无方法论硬冲突
- 未吸收项（对照后判定已覆盖或价值过低）：Blockscout counters 画像（robinhood 表已提及）、空投接收方口径/gross-net 双口径/分级计数呈现（playbook 已有）、ETH/BSC 双端点 getCode 判链与合约元数据四选择器直读（常识级操作）、honeypot.is 单场景 404（§4 已有其误报机制条目，偶发不入死亡名单）
- 与既有内容的两处数字差异按"并列两说+用前实测"处理：publicnode ETH 块限（2 万 vs 5 万）；48club 吞吐（§7.1 已录区间涵盖两次实测）

### 成本指标
- 考古式吸收（非分析实战）：通读 skill 全部 10 文档 + 8 币汇总逐条对照去重 + 23 处精准追加，约 20 轮、Edit 23 次、零脚本变更

## [1.8.0] - 2026-07-13 — CASHCAT(Robinhood/NOXA) 复盘：尘埃投毒伪出纳网 REFUTED 教训 + 两跳体检 + 假桥双层呈现 + swap/价格重建脚本收编

### Added
- **playbook §6 聚类硬规则 2 条**：①gas 边可被外部尘埃投毒伪造——"出纳判定三查"（拉出纳本体全量 tx 看收款人全集/查收款人构成含无持仓地址即非庄名单/与其他空投名单查同额重叠）；尘埃级（≤0.001 ETH）gas 边默认不作聚类证据，真出纳特征=低频专职+发射前注资+建仓级金额（本次初版"庄#2 出纳网 19 址"被 6 路对抗复核 REFUTED 的教训，实为第三方对 63 址的营销 dust）②两跳下游追踪每跳节点先 eth_getCode 合约体检——132 址体检出 14 个公共 swap 执行合约，剔除后马甲口径 21.9%→12.7%、96 址大集群拆为三个独立星座
- **playbook §6a 假桥双层呈现范式**：清洗后大集群拆成多星座时按"N 个实锤庄（各自过门槛）+ 高度疑似同一实体合并主张（注明下限拆分）"两层报告
- **playbook §9 LP 做市口径**：从 V3 NPM 收大额=LP 提取非买入，其"池卖"含流动性撤出须单独声明
- **playbook §11 时间锚点纪律**：关键 epoch 必须程序换算双向核对禁止心算（本次手算错 +1 天致时序窗口整段错位被复核整改）
- **data-pipeline-robinhood.md**：方法论坑 3 条（尘埃投毒三查/两跳体检与 v1.7 原子中转法互补/假桥拆分）；HyperSync 体量参考（86.8 万 Transfer ~30min 含 429 退避、23.2 万 swap ~9min）
- **scripts/robinhood/ 收编 2 脚本**（py_compile 通过）：`pull_swaps.py`（V3 池全量 Swap 事件，config.swap_pools 数组）、`build_price.py`（sqrtPriceX96 全历史 USD 价格重建+GT 交叉验证，实测中位偏差 0.98%，解决 GT 分钟K只存 2 天/收录晚于建池的前期空白）
- **address-book.md Robinhood 段**：仲裁 0x7b226b0b 地址冲突（实测为 DEX 聚合器执行合约，非 V4 PoolManager，外部标注系误标）；新增 UniversalRouter 0x8876789976（曾混入聚类虚增账本 $28M 的教训）与 V3 NPM 0x73991a25；0xe72688f7 补实名 RobinHoodSettler；工厂费率补 CASHCAT 侧第三数据点（与 Pointless 读数一致，且创建者本币份额中途被置零——确认 per-launch 动态可变）；0x1887fa9e 补两解相容观察

### 成本指标
- 约 85 轮 API 调用、Bash ~60 次、活跃约 4.5h（跨一次会话中断续跑；两轮 Workflow：4 路调研 + 6 路对抗复核共约 118 万 subagent tokens）
- 对抗复核战绩：REFUTED 1 条整实体判定（庄#2/0x3009 出纳网→第三方 dust）+ WEAKENED 2 条（马甲口径 21.9%→12.7%、Tenev 时序数字全部重列）+ CONFIRMED 2 条（庄#1 聚类 wei 级复现、成本账本）+ 完整性批评 7 项 HIGH（96 址混入公共合约/LP 行为/V4 盲区/平台烧币机制/毕业日未归因/散户桶纯度/发射者跨币画像）——铁律 4「凡执行必实质改写」第 N 次验证
- 版本竞态：开工 v1.4.0，交付时已被 COMPUTE(v1.6.0)/Pointless(v1.7.0) 两个并行 Robinhood 会话推进；另检测到一个同标的并行会话的零散写入（RPC WAF 条目先至，内容一致跳过重写；其 0x7b22 误标已仲裁修正）。多会话对同一 pipeline 高频并发下追加式写入+交付前重读版本号的防护全程生效

### Known Gaps（遗留 TODO）
- V4 PoolManager 侧 Swap 事件采集方案未建（本次 V4 日均 0.8-1.65 亿枚吞吐按盲区声明处理）——下次 Robinhood 标的若 V4 活跃须补：PoolManager Swap topic + poolId 过滤

## [1.7.0] - 2026-07-13 — Pointless(Robinhood/NOXA类工厂) 复盘：原子中转识别法 + 平台充值/7702 两类新断头 + Blockscout gas 脚本收编 + tx 级成本引擎

### Added
- **data-pipeline-robinhood.md 方法论坑新增 3 条通用性强的**：①**原子中转设施识别法**（重放前先算"同 tx 进出金额占比>90%"批量揪聚合器/路由/收集器/工厂，一次抓 23 个，并入市场腿防顶榜；比逐个 getCode 快且不漏，判据独立于是否合约）；②**relayer/公共代理判据统一为 txfrom 用户数**（上千即公共设施，复核曾据"两组共用 0x6505"误推同一实体被 REFUTED——"共用某执行合约"永不能作私有关联证据）；③**Blockscout internal-transactions 端点**（ETH 内部转账/充值溯源主力，HyperSync transactions 慢时用）
- **data-pipeline-robinhood.md 链特有坑新增 2 类溯源断头**：①**零地址直铸 ETH = App 内充值/托管通道**（gas_in from=0x0 的 value，继 Relay 桥后第二种断头）；②**EIP-7702 智能账户识别**（getCode 返回 23 字节 `0xef0100`+地址=委托 EOA 非合约金库，委托实现相同≠同一实体，与 4337 并存）
- **scripts/robinhood/ 收编 3 个可复用脚本并参数化**（红线 5：替换原 COMPUTE 项目目录里断链的 gas_trace_bs 样例）：`gas_trace_bs.py`（Blockscout 版 gas 溯源现主力，断点续传+funder 汇总）、`pull_weth_pool.py`（主池报价币侧 Transfer）、`cost_engine.py`（tx 级 swap 对价重建出每实体成本/已实现盈亏，config 可选 fee_distributor/quote_token）——均 py_compile 通过
- address-book.md Robinhood 段：新增 `0x65050a9b…`（公共狙击 bot 执行代理，1500+ 用户，勿作关联证据）

### Fixed
- address-book.md 工厂 `0xd9ec…` 手续费分成标注：GME 侧记 57%销毁/33%平台/10%创建者，Pointless 侧实测本币侧 80%烧/20%平台、WETH 侧 65%平台/35%创建者——**两次不一致，工厂疑 per-launch 可配置，标注"遇到时现场实测勿套历史比例"**（否定性/矛盾结论如实并列，未覆盖任一方）

### 成本指标
- 约 40 轮 API 调用、Bash ~40 次、活跃约 2.2h（跨一次会话中断续跑；两轮 Workflow：3 路调研 + 6 路对抗复核共约 92 万 subagent tokens）
- 对抗复核战绩：REFUTED 1 条子断言（0x6505 同实体推断）+ WEAKENED 4 条（46%→34.6% 同时刻口径、交易税→池 fee、WETH 分成 dev 大头→平台大头 65/35、散户口径闭合）+ 完整性批评补 2 章漏报（现役吸筹中户/G_D 顶点接盘聚类）——再次验证铁律 4「凡执行必实质改写」
- 版本竞态实例：开工见 v1.4.0，交付时已被并行 COMPUTE 会话推进至 v1.6.0（纯数据管道增补，五问框架与门槛未变，本次分析有效）；本条为 v1.7.0

## [1.6.0] - 2026-07-12 — COMPUTE(Robinhood/Flap) 复盘：Flap 发射台结构 + 聚合器误判 REFUTED 教训 + gas 溯源换 Blockscout 通道

### Added
- data-pipeline-robinhood.md：Flap（flap.sh）发射台结构条目（第三家：Portal 工厂即内盘 bonding、newTokenV6 同 tx 自购、毕业注 V2+LP 烧毁、FlapTaxTokenV3 永久税模板、0x…7777 平台 vanity、税先落代币合约再归集 TaxProcessor 机械卖出、beneficiary=项目方收入通道）
- data-pipeline-robinhood.md 方法论坑 5 条：①swap 归因必须用 swap.to（bot relayer 代发普遍，txfrom 归因制造假超级买家）②"漏斗/对倒环"定性前必须 getCode+合约验证身份（DEX 聚合器形态与洗量环完全同构——本次对抗复核 REFUTED 实例，聚合器 USD 占比与枚数吞吐两个量纲分开报）③发射前预注资是"预谋建仓"最硬时序证据（链上-链下时间对齐表打法）④HyperSync 按块拉全链 transactions >16MB 截断，改 RPC batch ⑤面额指纹先做全体参与者独占性检验（初稿两处张冠李戴被复核抓出；常见整数面额无区分力，wei 级奇葩面额才是硬指纹）
- address-book.md Robinhood 段补全 9 地址：Flap Portal、LiFiDiamond、DexAggregatorCore/DexAggregator（完整地址核验，解决 1.5.0 遗留的前缀截断待补全项）、bot relayer×2、清算枢纽 0xe726、疑似 CEX 热钱包 0x1887（性质待定防误聚类）、ERC-4337 EntryPoint v0.7
- gas_trace.py 加坑注：链高 789 万时 HyperSync transactions 路 25 分钟无产出，改walk Blockscout filter=to 逐址（34 址 3-4 分钟，样例 gas_trace_bs.py 存 COMPUTE分析/scripts/）

### 成本指标
- 约 58 轮 API 调用、Bash ~40 次、活跃约 2.2h（含两轮 Workflow：4 路调研 + 6 路对抗复核共 90 万 subagent tokens）；对抗复核 REFUTED 1 条核心叙事（刷量环→公共聚合器）+ WEAKENED 多条 + 补 5 项漏报，再次验证铁律 4
- 版本竞态防护首次实战生效：开工记录 1.4.0，交付前复查发现 1.5.0（并行会话 Solana 升级），本条目基于 1.5.0 追加为 1.6.0

## [1.5.0] - 2026-07-12 — IO 原始会话记录考古：Solana 管线 [INFERRED]→[VERIFIED] 批量升级 + 双 RPC 互补矩阵（来源：用户找回 Windows 电脑 IO 分析会话 jsonl，逐条比对实录）

### Added
- **data-pipeline-solana §0a 双公共 RPC 互补矩阵（关键工程事实）**：publicnode 放行 getProgramAccounts 大扫描（117MB 响应实录 OK、~45s）与 getTokenLargestAccounts，但方法级屏蔽 getMultipleAccounts/getTokenAccountsByOwner（`-32602 Request blocked`）；api.mainnet-beta 恰好相反（getTokenLargestAccounts 恒 429、其余可用）——必须按方法路由，单节点走不通全程
- **data-pipeline-solana §0b 死亡名单**：Solscan API（Cloudflare/401）与 WebFetch 抓 solscan.io（同拦）、rpc.ankr.com（403 需 key）、solana.fm（502）、Birdeye public（401）、Arkham（403）——标签主通道只剩 WebSearch 裸搜地址字符串（可命中 PoR PDF/侦探推文/媒体标注）
- **data-pipeline-solana §3a 流水追踪三个 Solana 特有坑**：①签名史挂 token account 不挂 owner 钱包（休眠大户 owner 查签名 9/13 NO TXS）②签名列表投毒——pump AMM 垃圾交易制造大钱包"日活十几笔"假象，活跃度判定必须 decode pre/postTokenBalances 看本尊变动，不能数签名条数③decode 必须按 mint 过滤（他币活动与 decimals 差异污染）
- **data-pipeline-solana §3 新增行为指纹**：CEX 冷钱包动态指纹（向已知热钱包调拨多币种=冷→热补库）、getTokenAccountsByOwner 钱包全持仓画像（多币种大额圆整+SOL≈0=托管/金库）、轮换出货通道指纹（每期换下游地址=刻意规避追踪）；后者同步进 playbook §4（链无关）
- **衍生品结构化通道 fapi.binance.com**（fundingRate + openInterestHist，响应自带 CMCCirculatingSupply）：IO 实录 Windows 直连成功 + 2026-07-12 本机直连复测通（451 只拦现货域名）——同步登记 api-keys.md 免注册通道；CoinGecko coin id≠slug 坑（io.net→`io`）一并记入 §4
- address-book 程序 ID 回填完整值：Squads `SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf`、Magna `magnaSHyv8zzKJJmr8NSz5JXmtdGDTTFPEADmvNAwbj`；新增 SPL Token 程序与 PumpSwap AMM（投毒识别用）

### Changed
- **data-pipeline-solana 全文来源声明重写**：原"自报告反推、会话记录已丢失"作废——记录已找回并逐条比对，原 [INFERRED] 凡实录确认改标 [VERIFIED·IO实录]（§1 全量扫描含 dataSlice 一次切 {32,40} 的实录教训与 99–117MB/45s 容量参数、§2 两跳判别含 dataSlice{0,0} 省流量、§3 全部指纹、§4 辅助数据面、§5 架构约束）；§7 首战清单大幅勾销，遗留项仅 Token-2022 分支/is_on_curve/屏蔽面漂移/本机大扫描表现
- playbook 来源代号表注释更新：IO 条目实证强度升至与其余会话等同；SKILL.md 阶段 0 路由表与深入阅读处的"自报告反推"提示同步移除
- §5 三段式架构降级为 SQD 不可用时的备用（交叉引用 §8，避免把 IO 时代限制当现状）

### 成本指标
- 本次为考古式吸收（非分析实战）：解析 5 场会话 jsonl（2.4MB）+ 2 子代理转录，约 20 轮；来源材料=IO 主会话 447 行实录（82 思考块/43 Bash/2 子代理）

## [1.4.0] - 2026-07-12 — 庄家认定门槛：历史峰值双门槛规则（5% 总供应或 10% 流通）（来源：用户直接定义）

### Added
- **playbook §6a 庄家认定门槛（硬性，双门槛）**：认定为"庄"的必要条件 = 实体合并口径（单地址自身，或集群含全部疑似关联地址合并）在任意历史时刻的**同一时刻合并持仓**峰值 ≥ 总供应量 5% **或** ≥ 流通供应量 10%，满足其一即可（流通门槛为用户定的低流通盘防漏判条款，流通占比 <50% 时才实际起作用；触发口径与分母取值须声明，vesting 标的用峰值时刻已流通量近似）。峰值从全量重放序列取，禁止只看当前快照、禁止跨时刻峰值相加
- **离场庄条款**：已清仓但历史峰值曾 ≥5% 的实体仍纳入庄家组展示与计数，标注「已离场」，历史持仓照常计入庄家阵营演变曲线；命名按历史峰值续排在现役庄之后（`庄#N·…·已离场`）
- **资源纪律**：合并口径峰值从未达 5% 的候选不认定为庄、不投入深挖，阴性排查一句话带过
- 三处同步：SKILL.md 阶段 3 短语、report-template 第三章入选门槛、JSON 附录 whale_groups 增加 `status: active|exited` 字段

## [1.3.0] - 2026-07-12 — 质量审查修订：开放条款 + Robinhood 管道合并修正 + 否定性结论纪律（来源：质量审查会话，用户逐项批准）

### Added
- **五问开放条款（三处同步：SKILL.md / analysis-playbook §框架段 / report-template）**：五问是下限不是上限——不属于五问的显著结构性异常（暴跌归因/假量矩阵/流动性事件/治理异动等）必须单列章节 + TL;DR 第 6 条"本次特有发现"（无则明写"无"）；报告骨架声明为最小集，允许插入标的特有章节。动因：框架收紧前的报告（CLAW"第一性原理视角"、RAXOL"暴跌归因"章）证明自主发现有真实价值，固定骨架曾无处安放
- report-template 问 4 vesting 附加要求：带解锁表的标的必含"未来 6–12 个月解锁日程与量级"小节（补五问框架自 meme 币实战定型带来的偏科）；SKILL.md 阶段 0 增加解锁表判定
- research-workflows §2 完整性批评角色必含一问："原始数据中是否存在显著异常未被五问覆盖而漏报？"
- retrospective 红线 4：**否定性通道结论入库前必须核查**（列端点清单/标穷尽度/与 memory 及既有文档交叉核对；"不可用"必须带实测日期，超 3 个月允许 1 分钟重探）——实例教训见 data-pipeline-robinhood.md 修正记录
- retrospective 红线 5：可复用脚本必须收编进 scripts/<chain>/ 并参数化，禁止只留桌面项目目录路径
- SKILL.md 阶段 0 版本竞态防护：开工记录 CHANGELOG 版本号、交付前复核（同日多会话交错曾致一次会话用旧框架交付）
- scripts/robinhood/ 新建：pull_transfers.py / gas_trace.py / pull_ohlcv.py（自 RAXOL分析/scripts/ 收编并参数化，key/标的移入工作目录 config.json）+ config.example.json
- scripts/solana/fetch_sqd_transfers.py：SQD portal 全量转账边拉取（自 meme 项目 chip_analysis.py 提取为独立脚本，逻辑未动），solana/README 同步更新
- address-book 新增 Robinhood Chain 段 3 地址（Relay solver f70da / 聚合器执行器 / V4 PoolManager）；补齐 Filecoin 段（f0121 基金会 / f0117–f0120 PL / f090 挖矿储备 / 低位段扫描法）

### Fixed
- **data-pipeline-robinhood.md 两处假阴性修正并全文重写**（合并 GME+RAXOL 两会话经验）：Blockscout 实为可用（robinhoodchain.blockscout.com，须浏览器 UA）、公共 RPC 实为可用（rpc.mainnet.chain.robinhood.com）——RAXOL 会话各试 3 个错误域名即下全称否定，同日 GME 会话已实测出正确域名但经验只进了 memory 未进 skill；合入 GME 独有经验：Arbitrum 桥地址别名溯源 L1（−0x1111…1111 常数）、GT pool_created_at 是收录时间非链上建池时间（Dexscreener pairCreatedAt 才是）、NOXA 发射平台结构、HyperSync transactions 慢的替代方案（按地址查交易改 Blockscout）
- SKILL.md 铁律 4 与 playbook §10 复核战绩计数矛盾统一（"五次实战每次都"→"凡执行必实质改写"，并入 bibi 翻出漏检集群实例）；"六次独立实战"等写死总数改为滚动表述（不随次数过时）
- playbook 来源会话代号表补入 bibi/CLAW/GME/RAXOL；retrospective"交付 PDF 后"→"交付报告（HTML）后"（v1.1 漏改）
- data-pipeline-evm 死亡名单加时效纪律（实测于 2026-07；超 3 个月允许 1 分钟重探）
- 成本纪律基线更新：补入 bibi 66 轮实测，参考预算轮次 <200 → <150（新链首战可放宽）

### 背景（为什么有这次修订）
GME(18:37)/RAXOL(19:09) 两次分析的复盘未走阶段 6（GME 经验只进 memory、RAXOL 直接写文件未经确认且无 CHANGELOG 条目），且两者对同一条链的通道结论互相矛盾——本次修订合并修正，并把暴露的三个制度缺口（否定性结论无核查、脚本外置、版本竞态）补进纪律。经验教训：错误的"不可用"会被死亡名单纪律锁死，比错误的"可用"危害更持久。

## [1.2.0] - 2026-07-12 — 五问框架首次完整实战复盘（来源：bibi(BSC) 分析，同日二次会话）

### Added
- data-pipeline-evm §4 新增 3 数据源：币安 Alpha 官方全量表（判"是否上过 Alpha"，Router 持仓性质判定关键，含全历史存档字段）、four.meme API 发射参数（成本三方闭环之一）、HyperSync 作单地址流水独立复核通道
- data-pipeline-evm §6 新增 5 坑：scan_transfers 毒段死循环（段停+行停=卡死，杀进程跑 fill）、锚点插值发射窗口 +108s 级恒定偏差（分钟K配价须精确锚定块外推）、GoPlus 对 EIP-7702 账户误报 is_contract、GMGN 卖出榜 EOA 口径新形态（操作者可完全不在 Transfer 事件中）、WebFetch 读代理合约页可能误报合约名（须 implementation slot+字节码选择器取证）
- analysis-playbook §6 新增 EIP-7702 delegate 指纹正确用法（"参考实现"恰是小众指纹，判据=产品分发面；复核曾据此翻出漏检 PLAUSIBLE 集群）
- analysis-playbook §6a 新增 bundle 型庄家账本级三件套（同块分发+CEX 广播前预注资 nonce=0 烧钱包+回款归集金库）、售罄参数整数不作关联证据（曲线残量买家可能是独立扫尾 bot）
- analysis-playbook §6a 狙击者统计流量/存量双口径纪律（累计净拿≠时点峰值持仓；留存分直接/经济体两档）
- analysis-playbook §9 新增拉升日集中度 gross/per-tx 净额双口径（环路自动清零）、疑似原子环路须验 tx 重叠+卖出时间分布再定性
- address-book 新增 BSC 段 7 地址：Alpha 2.0 Router Proxy（含权限取证结论）、RelayRouterV3、Binance DEX Router、Rainbow Router、Prediction bot、four.meme 主合约/TokenManager

### Known Gaps（本次遗留）
- 同 dev 多盘的资金层交叉溯源（老盘收益是否滚入新盘发射资金）未做——下次同类标的可补
- 币安热钱包 10/23 完整地址未取全（复核转录中为截断值），入库前须 bscscan 再核
- scan_transfers.py 毒段自动踢出改造（同段失败 N 次移出主队列）待实施，当前靠文档坑表

### 成本指标
- 主会话约 66 轮 / Bash 约 40 次 / 活跃约 3.2h（19:10 起，21:05 交付 HTML，含复核等待）
- 子代理：调研 fan-out 5 agent 47.6 万 tokens / 对抗复核 5 agent 70.6 万 tokens（44 分钟，221 次工具调用）
- 对比基线（266-480 轮）：轮次降约 75%——固化脚本+两次 Workflow 外包是主因

## [1.1.0] - 2026-07-12 — 五问框架 + HTML 交付 + 三张标准图固化（来源：bibi 分析实战 + 用户迭代指令）

### Changed
- **分析框架：三问版 → 五问版**（用户定稿）：①有几个庄 ②每个庄什么类型（单地址明牌/多地址·互转·gas同源/伪装分散·指纹一致三分类）③建仓成本 ④各阵营全历史持仓占比演变（占总供应量，锁仓/销毁单列）⑤官推侦查。旧三问的分析内涵（吸筹派发/关联集群/弃盘）全部并入五问，方法学章节保留 → SKILL.md、report-template.md、analysis-playbook.md 框架段
- **交付格式：中文 PDF → 自包含单文件 HTML**（图 base64 内嵌 + 末尾机器可读 JSON 附录，双轨嵌入：可见 details 折叠块 + `<script id="chip-json">` 供监控脚本提取）；md2pdf.py 保留仅点名时用
- 阵营命名与配色标准化：庄家TOP1(红)/庄家其他组(橙)/流动性池(蓝)/首30分钟狙击者(紫)/其他散户(绿)/锁仓销毁(灰)

### Added
- `scripts/report/standard_charts.py`——三张标准图生成器（阵营占比演变堆叠图/庄家组vs价格双轴图/价格+事件+成交额双panel图），规格配色固化，自带合成数据 demo；以后每次分析直接调函数，用户不再需要贴样图
- `scripts/report/build_html.py`——报告.md → 自包含 HTML（零第三方依赖；`> i`/`> !` 蓝红框语法与 md2pdf 一致；缺图/JSON 坏打 WARN 退出码 1 拒绝交付）；冒烟测试通过（浏览器目检：图内嵌/表格/蓝红框/JSON 可提取全过）
- analysis-playbook §6a 庄家类型三分类与阵营划分（含分级计数规则：实锤组与高度疑似组分开报、类型③措辞上限"高度疑似"、洗仓双跳归回原实体）
- analysis-playbook §6b 建仓成本估算（四件套输出；配价方法优先级 swap逐笔>分钟K>影子成本；CEX 场内不可见边界）
- research-workflows §1 官推侦查升为标配路线（memory.lol 前科/X API 画像/发帖 vs 链上动作对齐表）
- report-template.md JSON 附录 schema（token/whale_groups/vault_addresses/camp_share_series/key_events/monitoring_advice 六块，键名稳定供监控脚本消费）
- 经验条目：资金净流向全景图信息量低，改按需生成（仅适合单集群内部资金分析场景），不画时报告用红框注明（来源：bibi 实战）

## [1.0.1] - 2026-07-12 — 装后即时修正与 Solana 通道补强

- 修正：API key 取用方式由"每次向用户索取"改为"从 ~/.claude/api-keys.md 登记文件直接取用"（用户 2026-07-06 已废除不落盘规则并建立集中登记制；skill 目录内仍禁止写死 key）→ SKILL.md 铁律5、scripts/evm/ 相关注释
- 修正：清除 fetch_alchemy.py 中会话恢复时残留的明文 key 与旧路径（置为占位符）
- 新增：data-pipeline-solana.md §8 实测通道补充（SQD portal 全量转账/GT 分钟K/gas 溯源/洗仓识别，来源：CLAW(Solana) 分析 2026-07-12）——部分弥补 Known Gaps 中 Solana 反推内容未经实测的缺口

## [1.0.0] - 2026-07-05 — 从 0 新建（五次实战平权综合）

来源分析：IO(Solana, 07-02)、OPN(BSC, 07-03)、FIL(Filecoin, 07-03)、SIREN(BSC, 07-03~04)、HYPE(Hyperliquid, 07-04)。
构建方式：四个会话记录全量浓缩提炼（经独立事实核查，109/111 条 verified）+ IO 自最终报告反推 + 平权归纳（不以任何单次为基准）。曾参考 OPN 会后的旧版 skill（存档于 `~/Desktop/token-chip-analysis/`，仅基于单次经验）做遗漏对照，未作为底稿。

### Added
- 三问框架（吸筹派发/关联集群/**弃盘评估**）与链路由（EVM/Solana/Hyperliquid/Filecoin/新链 SOP）
- 铁律 1 结论独立性（工具知识可复用、代币结论禁复用、报告不跨币对比）——来自用户的去偏见实验结论
- 阶段 6 复盘迭代机制（references/retrospective.md）
- 成本纪律章（基于四会话消耗解剖：轮次×上下文是大头、thinking 占输出 85-89%）
- references 十件套；scripts 按链分目录（evm 9 个 / hyperliquid 3 个 / filecoin 4 个 / report 2 个）
- 报告管道定为 报告.md + md2pdf.py（HYPE 实战版通用化：argparse + 蓝/红提示框 + 图注不跨页，已用 HYPE 真实报告冒烟回归）

### Deprecated
- reportlab story 直写路线（OPN/FIL 用过）：md 直写试错更少、可先审后渲；旧 build_pdf.py 存档于桌面 v1 目录，且确认为表格修复前旧版

### Known Gaps
- `scripts/solana/` 为空：IO 会话记录丢失无法恢复脚本；方法要点存于 data-pipeline-solana.md（自报告反推，全文 [INFERRED]），首次 Solana 实战时逐条验证并补脚本
- data-pipeline-filecoin.md 与 filecoin 脚本恢复自会话存档，未在新标的上回归——首次 FIL 复用时留意
- 五次分析均未覆盖：DEX 流动性充足型代币的池内行为分析（LP 增减/大额 swap），遇到时按新链 SOP 精神现场补方法并沉淀
