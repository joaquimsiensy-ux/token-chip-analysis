# Robinhood Chain 数据管道 · 方法论坑（Robinhood 绑定条目）（data-pipeline-robinhood 分册 3/3）

> 母文档：`data-pipeline-robinhood.md`（薄路由索引页；链概况与合并来源声明见索引页）。本册只存**与本链通道/平台/脚本绑定**的方法论条目；链无关通用条目一律在 playbook 三册（entity-cluster-methods / state-anomaly / evidence-wording）。通道表与脚本见 `data-pipeline-robinhood-channels.md`，坑 1–17 见 `data-pipeline-robinhood-traps.md`。

## 方法论坑（Robinhood 绑定条目）

- **平台充值通道=溯源断头**：凡入金经平台通道（f70 类）的庄组，组间真实独立性链上不可判定——报告必须声明"N 组是链上可分辨的下限拆分"。
- **分钟K收盘定价低估大单成本**：单笔吃掉 >0.5% 总量的买入，真实滑点成本显著高于分钟K收盘；重仓组成本按"下限"表述。
- **该链 swap 归因必须用 swap.to 而非 txfrom**（COMPUTE 实测）：散户交易大量经 bot relayer 代发（txfrom=relayer、币直达终端），按 txfrom 归因会把几十用户的买入算到一个 relayer 头上，制造假"超级买家"。卖出侧按"给池子币的 transfer.from"归因。
- **Blockscout internal-transactions 端点（ETH 内部转账溯源主力）**（Pointless 实测 2026-07-13）：`/api/v2/addresses/{a}/internal-transactions`（须浏览器 UA）查合约间/充值的 ETH 流转——HyperSync transactions 按地址扫全链极慢时，金主 ETH 入金溯源改用它；直发交易查 `/transactions?filter=to`（value>0 的最早几笔即注资源）、合约转入查 internal-transactions。两者配合能把"谁给这个狙击母钱包打的钱"翻到零地址充值通道或 Relay 桥为止。
- HyperSync **按块范围拉全链 transactions 响应超 16MB 会 IncompleteRead 截断**——内盘期对价重建改用 RPC `eth_getTransactionByHash` batch（20/批 subprocess+curl，466 tx 约 1 分钟）。
- **多池标的 cost_engine 要点**（VEX 实测）：①报价币非 WETH 时（如 VIRTUAL）小时K 用币安 `data-api.binance.vision`（如 VIRTUALUSDT）②内盘 pair 也是 VIRTUAL 计价池——POOLS 集合须含内盘 pair 否则内盘买入全部 unpriced（VEX 案曾漏，修正见工作目录 cost_engine_vex.py 的 POOLS 写法）③V4/稳定币池的对价（USDG 面值 $1）与 VIRTUAL 腿分开算再合并，两种报价币不能混进一个 quote_usd。
- **★gas funder 作聚类证据前必过"公共性三步体检"**（Pointless 增量复核推翻旧报告 G_D 四址聚类的元凶，2026-07-14；通用判据版见 playbook-entity-cluster-methods「gas/资金面溯源纪律」，本条为链上操作版）：①Blockscout counters 总笔数（万笔级即警报）②本体余额量级（千 ETH 级=运营金库）③时窗收款人分散度（HyperSync 拉其任意 1 小时出账，收款人 ≥20 个即公共设施）。App 类链存在**平台托管提款热钱包**（实证 `0x1887fa9e…`：1.1 万笔/1273E/单一金主补货 3666E/时均 ~50 收款人）——给海量用户分发 ETH、形态酷似私人母钱包，"同源供 gas"完全不构成关联。连坐纪律：**据单一 gas 边建的聚类，funder 一旦被证公共即整体作废**（旧报告 G_D 四址聚类唯一依据即此，增量复核瓦解；本次更新还差点据同一 funder 定出"换马甲"新结论）。
- **多项目共用金库的哨兵语义两坑**（VEX 增量更新，2026-07-15）：①Virtuals 金库2 类地址是**平台多项目共用活跃热钱包**（本案窗口内 nonce +113，全是其他新盘的建池/ACF 配置事务）——哨兵结论必须写"零 **<标的>** 动作"而非"零动作/沉睡"，nonce 增长≠标的异动，二者语义与风险含义完全不同；②该链存在 **symbol 相同、合约不同的同名假币**（Blockscout 地址页按 symbol 展示会混入）——一切监控与人工核查必须按代币合约地址过滤，不能按符号。
- **Virtuals Team 金库（金库1）性质判定三步**（RAXOL 实测 2026-07-14，补旧报告"性质未验证"空白）：①getCode——实测为 0age 最小代理（`0x3d3d3d3d363d3d37363d73<impl>5af43d…`，44B），实现未验证 ②`owner()`（selector 0x8da5cb5b）——返回 Virtuals 跨项目 keeper `0x81f7ca…`（即平台托管，非项目方自持私钥）③平台 API tokenomics 拿正式解锁表（见 channels 分册通道表）。标准 vesting selector（start/duration/beneficiary/unlockTime）全不响应，属 Virtuals 自有托管模板；表述纪律："解锁表=平台注册承诺+托管合约形态"，非纯链上可验证铁证。
- **Virtuals 平台侧情报直查**：`api.virtuals.io/api/virtuals?filters[tokenAddress]=<addr>`（走代理）一次拿 creator 钱包/DAO/veToken/TBA/内盘 pair/tokenomics 解锁表/projectMembers（团队推特）；virtualId=该链第 N 个毕业 agent。veVEX 类 sVEX 的质押物是 V2 LP 而非本币（assetToken() 实查）；**LP 锁定验证**：V2 pair 的 LP token holders 若 100% 在 ve 合约=毕业 LP 全锁（撤池风险排除），一次 RPC balanceOf 即可验。

- **★gas_trace_bs 只抓普通 tx，会整体漏掉 internal 转账入金**（VIRTUAL 实测：Safe 部署者军资表面 464E 实际 1,699E 差 8 倍——73% 经 Across SpokePool 以 internal 交付）——大额资金溯源必须补 `/addresses/{a}/internal-transactions`（浏览器 UA）；"资金链断头"结论在补查 internal 前不得下（VIRTUAL 复核，07-16）
- **★纯 LP-token 持有地址是溯源候选集的结构性盲区**：候选集只用代币持仓榜会漏掉 LP 层实体（VIRTUAL 实测：一个五地址集群持主池 LP 5.83%=第 4 大 LP 实体，代币口径峰值仅 0.64% 不入任何榜，靠对抗复核翻出；其中两仓各恰 1,500.0000 LP 的整数指纹早已可见但未深挖）——报价币/主池型标的做 LP 集中度分析时，**LP 持有人榜必须独立生成溯源候选**（VIRTUAL 复核，07-16）
- **Blockscout holders 快照有瞬态伪影**：快照可能恰好拍到某地址"收币后、卖出前"的分钟级窗口（实测一个显示 1.56% 的"大户"实为 2 分钟过手通道）——大户名单以全量重放末态为准，快照只作对账参照（VIRTUAL，07-16）
- **★0xb92fe925（Relay）是多身份设施，"经过它"读不出方向语义**：既是 App 代币交付金库（本币侧双向：入=市场买入、转给它=同 tx 原子落池卖出，GME 增量已验），**又是 RelayRouterV3 公共 swap 路由（原生 ETH 侧：multicall 收 ETH 换出 USDG 等稳定币回到发起人）**——把"9.81E 转给它"读成"App 黑箱提现"是错的，实为 swap；真正的跨链出境是**下一笔** USDG 转入 RelayDepository（`0x4cd00e38…`，Relay 桥存管）。判定资金出境=看稳定币是否进 Depository，不看是否碰过 0xb92fe（Pointless 二次增量对抗复核，07-17）
- **Blockscout 各列表端点第一页 50 条会截断活跃地址的窗口核查**：平台费金库类高频地址的窗口 WETH 流水实为 91 笔、首页只见最近 50 笔（且"首页无外转"≠"窗口无外转"）——哨兵核查涉活跃地址时改 HyperSync 按 topic 过滤全量拉取，浏览器 API 只用于低频地址（Pointless 二次增量，07-17）
- **App 智能账户的"清仓-重建仓"黑箱量化范式**：大额 App 户清仓后，其卖出量与随后 48h 内 App 通道新买家吸入量做覆盖率对比（实测 123%）——"换号重建仓"数学可行性入局限性，既不证实也不证伪；App 通道候选（无 gas、对手方=交付金库）的实体独立性判定天然弱一档，观察哨照设（Pointless 二次增量对抗复核，07-17）
- **RelayDepository `0x4cd00e387622c35bddb9b4c962c136462338bc31` = Relay 桥存款库（已验证合约，17.8 万+笔）**：`depositNative` 调用=资产跨链离开本链，溯源就此断头。项目方/庄家利润撤离的标准通道之一（实测：创建者经 23 个一次性跳板地址向它归集约 13 ETH 离场）；与 Relay solver 热钱包 `0xf70da…` 是同生态两个方向（f70da=入金/代发，4cd00e=出金存款）（TRASH 更新，07-17）
