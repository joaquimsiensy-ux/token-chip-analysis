# 基础设施地址标签库（跨分析累积）

> **先跑批量层**：本文件是手工实战核验层（含机制注释）；另有批量标签库 `labels/`（v4 2026-07-17 七链 ~46.9 万条：CEX/桥/路由/协议/OFAC 制裁/Tornado 用户与合约/KOL/惯犯庄家 serial-actor/Hyperliquid/Filecoin，来源与纪律见 `labels/README.md`）。**聚类前先用 `scripts/labels/label_lookup.py --chain <链> <地址...>` 把全部候选过一遍**（七段输出，SERIAL 惯犯命中=最高优先级），命中 EXCLUDE 的按纪律剔除、命中 risk_flags 的按四档分区处置；Robinhood 疑似公共 bot 合约加跑 `fingerprint_check.py`；批量层查不到再走本文件 grep 与现场判别。两层结论冲突时以现场核验为准（热钱包会轮换）。**改本文件地址条目后必须同步 `gen_manual_from_addressbook.py` 并重跑构建**——`check_manual_sync.py` 双向校验不过，构建直接失败（v4 起强制）。

**性质**：CEX 热/冷钱包、做市商、系统程序等基础设施地址属于工具性知识，可跨代币复用。
**纪律**：①用前抽查核验（热钱包会轮换、标签会过期）——链上浏览器点开看最近行为是否仍符合标签；②**项目方实例地址（金库/vesting/团队钱包）不入此库**，它们属于单次分析的标的信息；③每条附来源与核验日期，新增条目走阶段 6 复盘流程。
**已知坑**：CEX 热钱包是全体用户共享的——**不可作为地址关联依据**（聚类纪律，见 analysis-playbook）。

## EVM（BSC / ETH，OPN·SIREN 分析核验 2026-07）

### CEX

| 地址 | 标签 | 备注 |
|---|---|---|
| `0xf977814e90da44bfa03b6295a0616a897441acec` | Binance HotWallet20 | BSC/ETH 双链同址 |
| `0x8894e0a0c962cb723c1976a4421c95949be2d4e3` | Binance 51 | |
| `0xe2fc31f816a9b94326492132018c3aecc4a93ae1` | Binance Withdrawals7 | 提币出口 |
| `0x631fc1ea2270e98fbd9d92658ece0f5a269aa161` | Binance BSC hot | |
| `0x5a52e96bacdabb82fd05763e25335261b270efcb` | Binance 28 | |
| `0x28c6c06298d514db089934071355e5743bf21d60` | Binance 14 (ETH) | |
| `0xdfd5293d8e347dfe59e90efd55b2956a1343963d` | Binance 16 (ETH) | |
| `0xf89d7b9c864f589bbf53a82105107622b35eaa40` | Bybit HotWallet | BSC/ETH/Arbitrum 多链同址；Bybit PoR 审计 2026-04-22 清单命中（SQD 分析核验 2026-07-20） |
| `0x9d271a4e9523d74572b618ec10419a0a330e1bf0` | Bybit Hot Wallet 10 (Arbitrum) | Arbiscan 官方标签 + Bybit PoR 审计 2026-04-22 双证（SQD 分析核验 2026-07-20） |
| `0x7da0b9211020d3775b18116fe751c555b9a7058c` | Bybit (Arbitrum) | Bybit PoR 审计 2026-04-22 清单 arbitrum 段命中（SQD 分析核验 2026-07-20）；⚠SQD 案实见仿冒前缀假地址 `0x7da05d2dc6…` 贴脸投毒——引用必完整比对 |
| `0xb9de92603d5e2a568bf67ad3f03a04f3a83cf3b2` | Bybit 储备/归集仓 (Arbitrum·行为学判定) | 本期 PoR 清单未列；判定依据=资金源 99.9% 来自上列 PoR 实锤钱包（f89d+9d27）+先 990/90 枚 dust 测试后大额的所内调度指纹、nonce=3（SQD 复核 2026-07-20）——引用时注明行为学置信 |
| `0x4982085c9e2f89f2ecb8131eca71afad896e89cb` | MEXC 13 | |
| `0x4e3ae00e8323558fa5cac04b152238924aa31b60` | MEXC 15 (Base) | Basescan 官方标签 2026-07-18 亲验；Base 链主力 CEX 通道，充值/提现/gas 提款服务共用；曾被三路复核分别误读为大户/工作室操作台/服务热钱包——热钱包持币榜形态酷似大户，定性必看官方标签 |
| `0x75e89d5979e4f6fba9f97c104c2f0afb3f1dcb88` | MEXC 1 (ETH) | |
| `0x0d0707963952f2fba59dd06f2b425ace40b492fe` | Gate.io 1 | |
| `0x1ab4973a48dc892cd9971ece8e01dcc7688f8f23` | Bitget 6 | |
| `0x2b5634c42055806a59e9107ed44d43c426e58258` | KuCoin 1 (ETH) | |
| `0xdc76cd25977e0a5ae17155770273ad58648900d3` | HTX 56 (ETH) | |
| `0x6cc5f688a315f3dc28a7781717a9a798a59fda7b` | OKX (ETH) | |

### 币安 BSC 二级提币热钱包（外部 BSC 分析考古 2026-07：TCC/人生K线/bibi；funded-by 聚类头号假阳性源）

由 `0x8894e0a0…`（上表 Binance 51）注资的下一层提币热钱包，**多个"独立"大户若共享其中之一作出资方 = 都从币安提币，零关联价值**。判定法：`eth_getTransactionCount` 看 nonce 百万级 + 常驻余额 2500–4500 BNB 即热钱包。

| 地址 | 标签 |
|---|---|
| `0xdccf3b77da55107280bd850ea519df3705d1a75a` | Binance BSC 二级提币热钱包 |
| `0x1fbe2acee135d991592f167ac371f3dd893a508b` | Binance BSC 二级提币热钱包 |
| `0x73f5ebe90f27b46ea12e5795d16c4b408b19cc6f` | Binance BSC 二级提币热钱包 |
| `0xbd612a3f30dca67bf60a39fd0d35e39b7ab80774` | Binance BSC 二级提币热钱包 |
| `0xeb2d2f1b8c558a40207669291fda468e50c8a0bb` | Binance BSC 二级提币热钱包 |

> 另有一批 ETH 主网 CEX 热钱包（MEXC 16、Binance 14–20、Union Chain 代付、deBridge DlnDestination 等）在外部 ETH 分析（ASTEROID/OPN）中被识破为"共同注资方"假阳性，但 memory 仅存地址前缀截断值——**用前必须 etherscan 补全并核验完整地址，禁止凭前缀补全**（末段是校验和）。

### 聚合器 / 跨链桥基建（EVM 通用，聚类时整体剔除；外部 BSC/ETH 分析考古 2026-07）

经这些合约买入 = 跨链/聚合买家，**源链身份断链，不作关联证据**。高出度节点，也命中服务枢纽剔除规则（analysis-playbook §6）。

| 地址 | 标签 | 备注 |
|---|---|---|
| `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | Relay 桥 solver 热钱包 | **BSC 与 Robinhood Chain 同址**；供 gas/代发交易/替空投池发币，38 万+笔公共设施 |
| `0x9008d19f58aabd9ed0d60971565aa8510560ab41` | CoW Protocol Settlement | 批量撮合结算，放币像撒钱包 |
| `0x1111111254eeb25477b68fb85ed929f73a960582` | 1inch v5 Router | |
| `0x111111125421ca6dc452d289314280a0f8842a65` | 1inch v6 Router | |
| `0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae` | LI.FI Diamond | 跨链聚合 |
| `0x663dc15d3c1ac63ff12e45ab68fea3f0a883c251` | deBridge（BSC） | 跨链桥结算 |

### 做市商

| 地址 | 标签 |
|---|---|
| `0xf584f8728b874a6a5c7a8d4d387c9aae9172d621` | Jump Trading |
| `0xdbf5e9c5206d0db70a90108bf936da60221dc080` | Wintermute |
| `0xd8d6ffe342210057bf4dcc31da28d006f253cef0` | GSR |
| `0xddacad3b1edee8e2f5b2e84f658202534fcb0374` | DWF Labs |

### 通用合约

| 地址 | 标签 | 用途 |
|---|---|---|
| `0xca11bde05977b3631167028862be2a173976ca11` | Multicall3 | 批量查余额（每批 ≤200 地址），全 EVM 链同址 |

### BSC 路由/托管/平台（bibi 分析核验 2026-07-12，bscscan 标签+行为画像）

| 地址 | 标签 | 备注 |
|---|---|---|
| `0x73d8bd54f7cf5fab43fe4ef40a62d390644946db` | Binance: Alpha 2.0 Router Proxy | 币安 Alpha 场内买盘的链上托管（omnibus）。**对未上 Alpha 的代币**：其持仓=外部单方面打入（判定法见 data-pipeline-evm §4 Alpha 全量表条目）。实现合约（EIP-1967）有 emergencyWithdraw+UUPS，权限 100% 在币安系管理员；误转资产先例=归集进币安热钱包而非退回原主 |
| `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` | RelayRouterV3（Relay.link） | 跨链聚合路由，高度数节点；经它买入=跨链买家，源链身份断链；不作关联证据 |
| `0xb300000b72deaeb607a12d5f54773d1c19c7028d` | Binance: DEX Router（官方标签） | 币安 Web3 钱包/App DEX 功能的链上路由；经它买入=币安系入口散户；不作关联证据 |
| `0x00000000009726632680fb29d3f7a9734e3010e2` | Rainbow: Router | Rainbow 钱包路由 |
| `0x0d4eca97c066961e0caa10608a0736f858dd13e6` | "Prediction" 高频 bot 代理 | EIP-1967 代理，292 万笔+、上百币种通用高频对倒 bot（逐小时买卖平衡、净仓恒零）；非任何单一代币的专属操盘手，从庄家候选剔除 |
| `0x757eba15a64468e6535532fcf093cef90e226f85` | four.meme 主合约 | mint 接收者；createToken 入口 |
| `0x5c952063c7fc8610ffdb798152d69f0b9550762b` | four.meme TokenManager | bonding curve 分发者：mint 块内它→各买家的转账即内盘买家名单；毕业时它→DEX 池 |
| `0x238a358808379702088667322f80ac48bad5e6c4` | PancakeSwap Infinity Vault | LP 基础设施，归 LP 桶不当大户（外部人生K线分析，2026-07） |
| `0x28e2ea090877bf75740558f6bfb36a5ffee9e9df` | Uniswap V4 PoolManager（BSC 单例） | BSC 第 4 交易场所，内嵌池；quote 侧资金全池混同无法按币种拆，别当大户（外部 bibi 分析，2026-07） |
| `0xc7f501d25ea088aefca8b4b3ebd936aae12bf4a4` | Giggle Academy 捐赠地址（Safe 2/4 多签，CZ 慈善） | BSC meme 流行"捐 1–2% 供应求背书"营销手法的收款方；大额转入此地址≈营销性捐赠、已脱离庄家控制，独立实体无锁仓（外部 CZ/bibi 分析，2026-07） |

### BSC/EVM EIP-7702 已知 delegate 实现（委托 EOA 识别；外部 bibi 分析 2026-07）

大户地址 `getCode` 返回 `0xef0100‖<delegate>` = 委托型 EOA（个人钱包），GoPlus/Blockscout 会误标 is_contract=1。**同 delegate ≠ 同实体**——主流钱包各用自家统一实现、海量用户共用（用法辨析见 analysis-playbook §6 的 delegate 指纹条）。

| delegate 地址 | 实现 | 关联面 |
|---|---|---|
| `0xcc0c946eecf01a4bc76bc333ea74ceb04756f17b` | 某钱包 App 统一 7702 实现 | 海量用户，同 delegate 无关联价值 |
| `0x63c0c19a282a1b52b07dd5a65b58948a07dae32b` | MetaMask StatelessDeleGator | 海量用户，同 delegate 无关联价值 |

## Solana（IO 分析核验 2026-07）

### CEX

| 地址 | 标签 | 来源 |
|---|---|---|
| `9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM` | Binance 冷钱包 | 公开标签；整数余额=冷储特征 |
| `3gd3dqgtJ4jWfBfLYTX67DALFetjc5iS72sCgRhCkW2u` | Binance 冷钱包2 | DA Labs/BlockTempo 标注 |
| `5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9` | Binance 热钱包 | Onchain Lens 标注 |
| `5LZkATrLwHYCQj2YuVbjjgsDZzBk6YfL4pFQRJmtboT2` | Bybit | Bybit PoR 审计报告收录 |
| `u6PJ8DtQuPFnfmwHbGFULQ4u4EgjDiyYKjVEsynXq2w` | Gate.io | 公开标签 |
| `ASTyfSima4LLAdDgoFGkgqoKowG1LZFDr9fAQrg7iaJZ` | MEXC | 公开标签 |
| `BmFdpraQhkiDQE6SnfG5omcA1VwzqfXrwtNYBwWTymy6` | KuCoin | 公开标签 |
| `H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS` | Coinbase（含 Prime 托管） | 公开标签；Prime=机构托管通道，提币含义与散户不同 |
| `AobVSwdW9BbpMdJvTqeCN4hPAmh4rHm7vwLnQ5ATSyrS` | Crypto.com | 公开标签 |
| `8Mm46CsqxiyAputDUp2cXHg41HE3BfynTeMBDwzrMZQH` | 疑似 OKX/Bitget 归集 | 未免费确证；特征=同时是多个热门币最大持仓者。**v4.2 起标 suspected-cex/identity+no_merge（禁边不剔仓）**——未确证设施不得 exclude，防真大户持仓被静默剔除；确证后升 cex/exclude |

### 识别用程序 ID（跨代币通用；完整 ID 2026-07-12 自找回的 IO 会话实录回填）

| 程序 ID | 名称 | 用途 |
|---|---|---|
| `magnaSHyv8zzKJJmr8NSz5JXmtdGDTTFPEADmvNAwbj` | Magna vesting 程序 | token account 的 owner 是它 → 该账户是官方线性解锁托管 PDA |
| `SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf` | Squads 多签程序 | 金库转出交易 instructions 含它 → 官方多签金库的强佐证（CEX 不用 Squads） |
| `TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA` | SPL Token 程序 | getProgramAccounts 大扫描的目标程序 |
| `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` | PumpSwap AMM | 大钱包签名列表里高频出现它 = 投毒/垃圾交易污染（见 data-pipeline-solana §3a），非本尊活动 |
| `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` | pump.fun bonding curve 程序 | 债券曲线账户 owner；毕业后仍可持 20%+ 被 GT 收录为"池"，勿当个人鲸鱼（用前核验完整 ID） |

### Solana 平台 / 路由 / 锁仓基础设施（外部 CLAW/FyedK/SGL 分析考古 2026-07）

| 地址 | 标签 | 备注 |
|---|---|---|
| `BAGSB9TpGrZxQbEsrEznv5jXXdwyP6AXerN8aVRiAmcv` | Bags 平台署名 creator | Bags 发射盘链上 creator 统一是它（平台特征非项目方，类比 four.meme 的 4444） |
| `FhVo3mqL8PW5pH5U2CN4XE33DokiyZnUwuGpH2hmHLuM` | Bags 平台金库 | **恰持每币 17% 整数配额**、单日 3000+ 签名高频机器钱包；算集中度前必剔除 |
| `FLASHX8DrLbgeR8FcfNV1F5krxYcYMUdBkrP1EPBtxB9` | Axiom Trade 路由（Solscan 标签） | pump.fun 狙击盘常 100% 经它路由；同一操盘方可按优先费固定档位（cu_price 预设档）指纹识别 |
| `jitodontfrontB1111111TradeWithAxiomDotTrade` | Axiom 防抢跑标记账户 | 与 FLASHX 路由伴随出现 |
| `strmRqUCoQUgGUan5YhzUZa6KqdzwX5L6FpUxfmKg5m` | Streamflow 锁仓程序 | escrow token 账户 authority=账户自身；stream 元数据账户 owner=它，可 raw 解码锁仓参数（见 data-pipeline-solana §2） |
| `wdrwhnCv4pzW8beKsbPa4S2UDZrXenjg16KJdKSpb5u` | Streamflow 自动提取服务 feePayer | 多笔提取共用它作 feePayer = 同批操作；"即建即提" stream 洗筹一跳中转的识别锚点 |
| `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ` | pump.fun fee 程序 | **RugCheck 的 creator 字段可能标成此程序派生的费金库 PDA**（与 pump.fun API 的真 creator 不冲突）——两源分歧先查所标地址的 owner 是否为它再下结论（CLUDE(Solana) 实测 2026-07-13） |
| `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` | PumpSwap AMM 程序 | 毕业池程序；其 creator-vault-authority PDA 是 dev 币本位创作者费的领取来源——dev"从池子收币"多半是**领费不是交易**，勿误判为买入（CLUDE(Solana) 实测 2026-07-13） |
| `39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg` | pump.fun→Raydium 官方毕业迁移钱包（Raydium Migrator） | 毕业时以 Withdraw 指令自 bonding curve 提出毕业储备注入 Raydium 池，过手约 2.069 亿枚 ≈20.7% 供应（**协议常数，pump.fun 毕业币同级**）、数十秒内完成过手。**发射窗重放的瞬时峰值榜必剔此址**——GOAT 案初稿曾把它误判"狙击集团 20.69% 瞬时峰"（复核 REFUTED 实体作废）；§8.6 成本重建的"迁移笔剔除"同源坑。走 PumpSwap 毕业的新币无此址过手（见上 pAMMBay 行）（GOAT(Solana) 实测 2026-07-22） |
| `HNCne2FkVaNghhjKXapxJzPaBvAKDG1Ge3gqhZyfVWLM` | Base-Solana 官方桥 Bridge 程序（Coinbase/docs.base.org 确认） | Solana→Base 跨链桥主程序；某钱包大额代币转入它=跨链桥出。出现在做"代币转股权/ACE 轮"的项目（币桥到 Base 侧锁仓/股权化）（OPAL(Solana) 实测 2026-07-14） |
| `g1et5VenhfJHJwsdJsDbxWZuotD5H4iELNG61kS4fb9` | Base-Solana 官方桥 Base Relayer 程序 | 上条桥的可选 relayer（Solana→Base 方向代付 Base gas），与 Bridge 程序伴随出现（OPAL(Solana) 实测 2026-07-14） |
| （某项目专属桥托管仓，用 owner 程序判别） | 桥托管 token account（例 OPAL 的 `F8446Bh5…` 恰持 2.5% 整数=ACE 轮满额） | 由多个散户地址在几天内桥出汇入的整数配额托管仓＝股权轮/跨链募集，非市场买盘；判别=其入账 tx 涉及上面两个桥程序 |

## Hyperliquid（HYPE 分析核验 2026-07）

### 系统地址（链级基础设施）

| 地址 | 标签 | 备注 |
|---|---|---|
| `0xfefe...fefe` | AF（Assistance Fund，回购基金） | 逐日回购数据见 ASXN 面板 |
| `0xdddd...dddd` | 排放池 | |
| `0x5555...5555` | WHYPE 合约 | HyperEVM 上的包装 HYPE |
| `0x43e9abea1910387c4292bca4b94de81462f8a251` | Hyperliquid 团队地址 | 仅分析 HYPE 本身时相关 |
| `0xd57ecca444a9acb7208d286be439de12dd09de5d` | Hyper Foundation | 同上 |

（Hypurrscan `globalAliases` 端点有 463 个实体标签，可在线查询，无需在此穷举）

## Robinhood Chain（chainid 4663；GME/RAXOL 分析核验 2026-07-12）

| 地址 | 标签 | 备注 |
|---|---|---|
| `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | Relay 桥 solver 热钱包 | 38 万+笔公共基础设施：供 gas/代发交易/替空投池发币。**gas 同源聚类必须整体剔除**——"同用它供 gas"只说明都经 Relay 桥入金，不是关联证据 |
| `0x00000000aa59b37306e34cef3e021e07156cfa3a` | 聚合器执行器 | 代发交易的高度数节点，聚类剔除 |
| `0x8366a39cc670b4001a1121b8f6a443a643e40951` | Uniswap V4 PoolManager（单例）⚠️见下 | 其"持仓"=全链所有 V4 池流动性合计，不是大户 |
| `0x7b226b0b2347aa522b97eba6c6da59c2edf908b2` | DEX 聚合器执行合约（**冲突已仲裁：不是 V4 PoolManager**） | CASHCAT 会话 2026-07-13 实测仲裁：22.7KB 未验证合约、单币吞吐可达供应量 44%/1.2 万笔、即收即卖回池（峰值持仓≈0）——聚合器执行形态；当前 V4 PoolManager 确认为 `0x8366a39c…`（GT V4 池数据与其持仓吻合）。外部分析的"V4 PoolManager"标注系误标。聚类整体剔除 |
| `0x0bd7d308f8e1639fab988df18a8011f41eacad73` | WETH（Robinhood Chain） | 原生 gas 币包装合约 |
| `0x1887fa9edadeab7562b01cc3f4fa246ace2c3cdd` | **公共提款热钱包**（App 托管出金通道形态）（Pointless 增量复核实证 2026-07-14；CASHCAT 增量三次核验 2026-07-15） | 11,339→12,524 笔持续增长、余额千 ETH 级、单一金主 `0x469CB5dA5f46D9C16d9825e41D831377E167478f` 累计补货 3666E、时均给 ~50 个不同地址分发 ETH；出账画像实查=50 笔/39 收款人/零整数金额（法币换算碎值）——**"同用它供 gas"≠关联**；据它建的聚类一律作废（实战两例：Pointless 换马甲误判、CASHCAT 旧报告"22 址分仓集群 3.91%"整体作废）。COMPUTE 案曾为矩阵成员资金链上游、早期条目标"性质待定"，三次核验后定性收敛为公共设施 |
| `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` | Relay/App 代币交付金库 **兼 RelayRouterV3 swap 路由（多身份设施）**（Pointless 实证 2026-07-14；双向语义 GME 增量验证 2026-07-15；swap 语义 Pointless 二次增量 tx 级穿透 2026-07-17） | **本币侧双向通道**：大额"转入"来自它=市场买入非私下转账；反向"转给它"=同 tx 原子落池卖出（**不是跨链离场/静置**，勿写"经 Relay 撤离"——16 笔实测全部同交易落入主池）；txfrom 为各公共 relayer；单币吞吐可达供应 62%、进出精确相等存量零。**原生 ETH 侧另有 swap 身份**：EOA 对它 multicall 送 ETH=换出 USDG 等稳定币**回到发起人自己**（勿读作"提现进 App 黑箱"）；真正跨链出境=下一笔稳定币转入 RelayDepository（`0x4cd00e38…`）——出境判定看 Depository 入账，不看是否碰过本设施 |
| `0xe72688f7d25d7318b9a81f21edda640ca948c83b` | RobinHoodSettler（已验证合约） | App 交易结算器（518 万 token 转账），原子过手末余额 0；买卖归因用同 tx 终端 |
| `0xabb2acd3be814a80e502575d6c1dc5f789e9cd10` | 公共 relayer（Pointless 实测 2026-07-14） | 797 条转账/273 地址代发交易，与 0x56c2…/0xa67d… 同类 |
| `0xb477751b76cf82d00a686a1232f5fcd772414af3` | LiFiDiamond（Robinhood 链部署，已验证） | 跨链聚合路由，原子过手；币进它=卖出或跨链撤离（同 tx logi 链可判：进池=卖出） |
| `0xcaf681a66d020601342297493863e78c959e5cb2` | Uniswap SwapRouter02 | 聚类先 getCode 甄别，别把 router 串成假簇 |
| `0xd9ec2db5f3d1b236843925949fe5bd8a3836fccb` | 主流 meme 发射台工厂（NOXA 类） | mint 10 亿→全额建 V3 池 1%，同 tx 创建者可自狙。**手续费分成两次分析不一致，工厂疑似 per-launch 可配置**：GME 侧记 57%销毁/33%平台/10%创建者；Pointless 侧实测=本币侧 fee 80%烧/20%平台、WETH 侧 fee 65%平台金库/35%创建者（来源：Pointless 分析 2026-07-13）；CASHCAT 侧独立实测与 Pointless 读数一致（本币 fee 经 feeRouter `0x9efdc1a8…` 烧 80%/20% 卖回池变现；feeRouter protocolShare=65 链上实读）——**遇到时按标的现场实测 fee 流向，勿套用任一历史比例**（第三点：该标的 7/1 起创建者本币侧份额被置零，份额参数确认 per-launch 动态可变，来源：CASHCAT 分析 2026-07-13）。NOXA 案又一数据点：本币侧 feeRouter 吞吐拆分实测=烧 86.26%/平台 treasury 13.74%、创建者本币份额≈0；且 LaunchLocker 在创作者领费的同 tx 会给平台 treasury 一笔机制分成——treasury 的"持仓"是纯被动费留成，勿当建仓（来源：NOXA 分析 2026-07-15） |
| `0x7e035fb048a31e0481b88074557415b1c187242b` | 发射台基建部署者·**dev.noxa.eth**（BEGGAR 核验 2026-07-17） | 上述工厂的部署者 EOA；ENS=dev.noxa.eth（创始人推文自认官方地址）；代发平台金库的领费交易（零仓操作手形态） |
| `0x71f2f1c2dc94cdabfe29cb355119f8683ae0969b` | **NOXA 平台金库 treasury.noxa.eth**（BEGGAR 核验 2026-07-17） | ENS 双向解析+创始人推文自认；全平台数十币的协议费归集金库（千 WETH 级）+亲手发射平台自营币；其从 feeRouter 收的 WETH 是**多币混合口径**，单币归因须按该币主池 Collect 拆分上限；作为 deployer 出现=平台自营盘 |
| `0x69957a4b1b97adb44742bb2f0f736f196960a83a` | **NOXA 平台出纳机器人**（BEGGAR 核验 2026-07-17） | 万笔级 EOA，约每 5 分钟自动 collect feeRouter+withdraw；**其 ETH 自动分发名单=官方关联仓发现通道**（名单极短，非金库收款人是运营侧隐性关联仓候选，见 playbook §4）；作为 funder 的 gas 边不可作私有聚类 |
| `0x7f03effbd7ceb22a3f80dd468f67ef27826acd85` | **NOXA LaunchLocker**（LP NFT 托管，已验证；BEGGAR 核验 2026-07-17） | 发射 tx 同交易把 UNI-V3-POS NFT 锁入；费分成给 creator（token 腿经 feeRouter）；**其 ERC-721 转出=撤池信号**（监控标配哨兵）；给 creator 的 0 枚心跳转账与费转账同 tx 出现属机制常态 |
| `0xd7aaa32920ebca1ef9b9bc684f519da56b37503d` | 公共卖币执行合约（BEGGAR 核验 2026-07-17） | 66 独立 txfrom/百笔级同 tx 等额进出且币同 tx 落池——"转给它"=真实卖出（经代卖通道），勿判私有漏斗/协同出货 |
| `0xa58bdd0ab5ebbb8dc425090fea8fd0ba969c1668` | 公共卖币执行合约（BEGGAR 核验 2026-07-17） | 63 独立 txfrom，同上语义 |
| `0x243a17063102c29fb60aa930db199d4b73ab8a37` | 公共卖币执行合约（BEGGAR 核验 2026-07-17） | 66 独立 txfrom，同上语义 |
| `0x2a7f3d7486641c77600b9b9256132755c8aebb4f` | 公共卖币执行合约/原子代卖路由（BEGGAR 核验 2026-07-17） | 238 独立 txfrom、过手可达供应 39%、唯一出方=池；同上语义 |
| `0x26605f322f7ff986f381bb9a6e3f5dab0beaeb09` | **Flap（flap.sh）Portal v5.14+**（COMPUTE 核验 2026-07-12） | 第三家发射台，日发币约千个。机制见 data-pipeline-robinhood.md Flap 段 |
| `0xb477751b76cf82d00a686a1232f5fcd772414af3` | LiFiDiamond（LI.FI 跨链聚合协议） | 已验证合约。经手枚数可达供应量级但为公共通道，**勿判为对倒枢纽**（COMPUTE 复核 REFUTED 实例） |
| `0x09ad820aac5779683b481c4674208a4e1b024afa` | DexAggregatorCore（已验证，部署者 0x9f2eFccb…） | 与下行同栈。买入归集+卖出形态酷似漏斗出货，实为聚合器路由——**先 getCode+验证合约名再定性** |
| `0x20f6ee51340adeed01a59b0e65cb3703f3dc860c` | DexAggregator（同上同栈） | 单进单出中转形态是其正常设计，非对倒证据 |
| `0x56c262027e0de4aea31d2489529cb25d23e58a8b` | bot relayer（全链 14 万+笔） | 代发 swap：txfrom=它、币直达终端。**按 swap.to 归因**，txfrom 归因会把散户买入算到它头上 |
| `0x4cd00e387622c35bddb9b4c962c136462338bc31` | **RelayDepository（Relay 桥存款库，已验证；TRASH 增量核验 2026-07-17）** | 17.8 万+笔;`depositNative`=资产跨链**离开**本链、溯源断头。项目方利润撤离标准通道（与 0xf70da 同生态反方向：f70da=入金/代发、4cd00e=出金存款）|
| `0xa687b664662b96b180346d699a6d5b42e9b05d31` | 聚合卖出路由/原子中转（TRASH 核验 2026-07-17） | 549 上游→唯一下游 PoolManager、同分钟入出、余额恒 0;"转给它"=同 tx 落池卖出,勿判私有漏斗 |
| `0x2e9b3fc5e73221e8ac0da2a1d836bda0273eab7f` | App 交易路径中转（TRASH 核验 2026-07-17） | 1,550 条流水、同秒入出、上游主要为 RobinHoodSettler(0xe726);经它"转入"的仓位=App 内市场买入交付,**共同上游≠关联** |
| `0x8f10b468b06c6fd214b65f87778827f7d113f996` | 套利/路由 bot 原子中转（TRASH 核验 2026-07-17） | 319 条,同秒对倒于 PoolManager 与 0xb92fe925 之间,零驻留;勿当仓位地址 |
| `0xa67d7eb4dc68fa6ce8e34ef8cadaf075b9893fbb` | bot relayer（同上，354 笔/币对级） | 同上 |
| `0xe72688f7d25d7318b9a81f21edda640ca948c83b` | RobinHoodSettler（交易产品清算枢纽，Blockscout 实名） | 34 进/94 出，用户托管提币模式。CASHCAT 会话教训：其过账曾以"大额转账边"混进庄家聚类当假桥——**与它的转账是产品过账，勿作关联边**（来源：CASHCAT 分析 2026-07-13） |
| `0x91604f590d66ace8975eed6bd16cf55647d1c499` | **尘埃 gas 出纳服务**（Robinhood 第三种 gas 断头/伪关联形态，与 Relay 桥、0x1887 提款热钱包并列）（CASHCAT 增量更新实证 2026-07-15） | 8,787 笔、抽样 111+ 个不同收款地址、模式="发尘埃级 gas → 收款者 1-3 秒内交易"（对照组接收者含与标的零关联的做市 bot）——**"共享此 funder"与"注 gas 后秒级交易"均为服务普遍机制，不构成同实体证据**；据它建的 gas 边一律降级为辅助证据，同实体认定须币流闭环独立支撑 |
| `0x32487287c65f11d53bbca89c2472171eb09bf337` | **Virtuals 平台回购机器（TWAP buyback bot）**（HAN 分析实证+对抗复核 2026-07-16） | EOA；对 Virtuals 系 agent 币做 TWAP 机械买入（中位 13 秒/笔、单向零卖出），跨 **150+ 种** agent 币系统性积累，弹药 VIRTUAL；gas 来自平台部署管理员 0xe4a001…与 keeper 0x81f7ca…。**出现在任何 Virtuals 币的买家榜=平台系统组件，勿判外部庄家/吸筹方**；其处置模式=keeper 对新合约三连初始化后数秒内整仓 transfer 转入封存（非卖出）——监控其转出时先核对接收方 creator 是否平台合约+有无 keeper 初始化前奏，命中=平台拨付勿报"庄家出货" |
| `0xe4a0015b4c12f84bf9b8b9db56b7ef0bc539d88f` | **Virtuals 平台部署管理员**（HAN 分析实证+对抗复核 2026-07-16） | EOA；掌握工厂/ACF 执行器/USDG 分发合约的 ownership 与 role 管理权（grantRole/transferOwnership 实测），权限高于 keeper；曾同秒向 6 个系统地址批量注资 0.01E 初始化（受益者含 keeper/金库2/回购机器）。**作为 funder 出现=收款方为平台系统组件的强证据**；坑：Blockscout `/transactions?filter=from` 对它稳定 500，去掉 filter 正常 |
| `0x0000000071727de22e5e9d8baf0edac6f37da032` | ERC-4337 EntryPoint v0.7（跨链同址） | AA 钱包交易的 txto 都是它，由多家 bundler 代发（txfrom 常见 0x4337 前缀），勿作关联证据 |
| `0x5ff137d4b0fdcd49dca30c7cf57e578a026d2789` | ERC-4337 EntryPoint v0.6（跨链同址） | 存量流量仍大；四链 getCode 亲验 2026-07-17（v4.2 补录，此前只有 v0.7 是覆盖漏洞） |
| `0xd29c85f15df544ba632c9e25829fd29d767d7978` | Across 桥 Universal_SpokePool（跨链入金通道之三；标签库已有，Pointless 二次增量行为面补注 2026-07-17） | 12.2 万+笔 ERC1967Proxy；跨链 fill 以 internal 转账给用户地址交付——**经它 internal 入金=跨链断头**，不构成私人金主边（实测一个 1.6% 大户的注资来自它，据此排除私人关联） |
| `0x3f43479c8536f7ee8180d0f67a050980dc5bc8c8` | batchTransferNative 批量转账工具（disperse 类半公共，125 用户；标签库已有，Pointless 二次增量穿透用法补注 2026-07-17） | **穿透用法：每一笔调用批次归属单一操作者**——同批次接收方=同一操作者的马甲组（wei 级等额分发是附加指纹，实测据此并出九址协同工作室）；但跨批次用户互不相干，"都用过它"不构成关联 |
| `0x243a17063102c29fb60aa930db199d4b73ab8a37` | 公共热钱包/托管结算设施（Pointless 二次增量核验 2026-07-17） | 8 万+笔高频；大户"分仓转给它"实为经它卖出/托管过手，勿判私人分仓地址 |
| `0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc` | 公共狙击 bot 执行代理（已验证 Proxy，1500+ 独立 txfrom 用户）（来源：Pointless 分析 2026-07-13） | 多个狙击组同用它下单——**"共用此合约"不能当私有关联/同一实体证据**（复核 REFUTED 一次"两组同实体"推断的元凶）。判据同 relayer：txfrom 用户数上千即公共设施 |
| `0x8876789976decbfcbbbe364623c63652db8c0904` | Uniswap UniversalRouter（CREATE2 公共路由） | 92 万+笔。CASHCAT 案曾以转账边混进 96 址庄家聚类当假桥并把全市场用户买卖算进庄家账本（虚增 $28M 买入额）——聚类与账本一律剔除（来源：CASHCAT 分析 2026-07-13） |
| `0x73991a25c818bf1f1128deaab1492d45638de0d3` | Uniswap V3 NonfungiblePositionManager | LP 头寸 mint/collect/burn 通道。**从它收到大额代币 = LP 提取，不是买入**；LP 做市行为者的"池卖"含流动性撤出，买卖口径须单独声明（来源：CASHCAT 分析 2026-07-13） |
| `0x81f7ca6af86d1ca6335e44a2c28bc88807491415` | Virtuals 跨项目 keeper EOA（VEX(Robinhood) 分析实测 2026-07-13） | 每个 agent 币发射时充当"50% 锁仓分配器"（拆两金库 25%+25%），并为多项目执行 ACF 分账（实测至少 5 个项目）。**平台运营 EOA 非项目方私钱包**，勿据它建关联边 |
| `0x3eb3394f5d89465a77f73a83d3675b0ed051f852` | Virtuals 平台批量执行合约（Blockscout 验证名 Multicall3 变体，7665B）（来源：VEX 分析 2026-07-13） | ACF 阶梯挂单执行器：收各项目金库2 的币→V3 USDG 池挂纯单边卖单→collect 本金直付各创始人（多项目共用，早于单个项目存在）。其吞吐是机制变现，单列勿混"庄家手动出货" |
| `0x8a19963649b2fc3d50c951953f89bcbfbd5f0b51` | Virtuals 内盘 bonding router（Robinhood）（来源：VEX 分析 2026-07-13） | 内盘期与毕业后平台前端交易均经它（过手可超总量 100%、中转率 100%）。真实买卖家=同 tx 的下游/上游终端 |
| `0xd4ccbfa37e2f35611b3042e4096ad7a3459bd007` | Virtuals TokenFactory/铸币分发（VEX 案实测；是否全平台同址待多标的验证） | 铸 1B→50% 内盘+50% 分配器；毕业 tx 内回收内盘库存→注 V2 主池+拨"拨付仓"EOA（疑似内盘反狙击税回收，白皮书条款 3 个月 cliff+9 个月线性归创始人） |
| `0xe4a0015b4c12f84bf9b8b9db56b7ef0bc539d88f` | Virtuals 平台部署 funder（来源：VEX 分析 2026-07-13） | 批量预生成金库2/keeper 等设施钱包并同秒注 gas。金库2 类 EOA 与它 gas 同源=平台设施证据，**不是**项目方私钱包证据 |
| `0x6d80b81d9fc56a7a839b1af9006eb49151961ce7` | Virtuals AgentTaxV2 税合约（TransparentUpgradeableProxy 已验证） | 1% 买卖税 projectTaxRecipient 指向它；分成 70% creator/30% 平台 treasury——创始人真实收入通道之一 |
| `0xf36f0dd7b6b1730d0a59d1f3fd0e494c4d5c66e8` | Virtuals 税 swapper（来源：VEX 分析 2026-07-13） | 税池代币→池子机械卖回执行腿（中转率 100%）。机械卖压单列，勿算庄家出货 |
| `0x000000e200088d55c39a11f609e5f667729ad49b` | Uniswap 官方 UERC20Factory（跨链 canonical，Blockscout 已验证；来源：TRASH 分析 2026-07-14） | 第 4 类发射台=Uniswap Liquidity Launchpad。代币模板名 UERC20。机制见 data-pipeline-robinhood 坑 10 |
| `0x00004c4ccc709ef590f7c81102c0689f0263d4e9` | Uniswap 官方 LiquidityLauncher（跨链 canonical，来源：TRASH 分析 2026-07-14） | 发射入口合约；铸 10 亿→拆 CCA 拍卖+LP 储备 |
| `0x000000001f26a0044baa66024e7b6599c61963f8` | Uniswap 官方 CCA 工厂 v2.1.0（来源：TRASH 分析 2026-07-14） | 每次发射 CREATE2 部署一个 auction 实例（=内盘 bonding 合约）；实例是 per-launch 地址非固定 |
| `0x05d552391067389ee44fec3924157ed33f976000` | Uniswap 官方 LBPStrategy v3.1.0 单例（来源：TRASH 分析 2026-07-14） | 毕业时初始化 V4 池+迁移流动性；亦是合法 V4 hook。**过手全部发射盘的币，勿当大户/庄** |
| `0x9be3cc594a47d90148b9f65466c57600018d237c` | 公共 bot 卖币执行合约（未验证，23.4KB；全链 61.7 万 tx/204 万代币转账/15+ 币种；创建于 2026-07-11）（来源：RAXOL 增量更新复核 2026-07-14） | 用户调用它同 tx 内把币卖进池子（100% 原子、出账全部由调用者签名）。**曾被整体误判为"39 上游归集出货协同网络"**——"经同一合约出货"永不构成协同证据；其入账流量只是"有人用工具卖币"的信号，勿作实体监控 |
| `0x2a7f3d7486641c77600b9b9256132755c8aebb4f` | 公共 bot 卖币执行合约（同 0x9be3cc59 形态；Pointless 单币即见 246 独立 txfrom、655 笔原子入→卖、过手 4.87 亿枚、余额恒 0）（来源：Pointless D14 告警甄别 2026-07-15） | 入→同 tx 卖进池，全程不留仓。单窗口"净卖 1.16 亿枚"实为数百用户流水总和——按 txfrom 穿透到真实卖家，勿当单一砸盘大户 |
| `0x68be5163fdd75ecad02aee1c9242e8afc8e95c8d` | 公共 bot 卖币执行合约第三部署（同 0x9be3cc59 模板，23.6KB 未验证）（来源：GME(Robinhood) 增量更新 2026-07-15） | 与 0x9be3cc/0xb01ca2 同款；曾被旧报告误判"归集器（隐藏库存枢纽）"——该模板设施剔除名单三个部署都要含 |
| `0x09ad820aac5779683b481c4674208a4e1b024afa` | DexAggregatorCore（已验证；全链 117 万 token 转账、直接 tx 仅 1 笔=全部被内部调用）（来源：GME 增量更新 2026-07-15） | 聚合器执行核心：从池买入→分发用户/转 DexAggregator，同窗吞吐可达供应 10%+ 而存量零。与 20f6ee51/b477751b 构成的"池买→内部转→卖回池"三角流量是**全市场用户聚合，不是对倒洗币环**（本次"洗币环"假设被 getCode+counters 证伪，COMPUTE 案同款教训第二次验证） |
| `0x20f6ee51340adeed01a59b0e65cb3703f3dc860c` | DexAggregator（已验证；全链 36 万 token 转账）（来源：GME 增量更新 2026-07-15） | 同上，聚合器外层；与 Core 互转是内部结构不是实体关联边 |
| `0xb300000b72deaeb607a12d5f54773d1c19c7028d` | Diamond 聚合器入口（已验证，180B proxy；vanity 地址 b300000b）（来源：GME 增量更新 2026-07-15） | 多小上游汇入→转 LiFiDiamond 的公共汇聚腿，勿当"归集器" |
| `0xd29c85f15df544ba632c9e25829fd29d767d7978` | 公共合约出金通道（11.5 万 tx/25.5 万 token 转账、余额恒 0）（来源：GME 增量更新 2026-07-15） | 大额 ETH 内部转账出金方（实测单址收 47.5E 后 1 分钟买币）——**曾被误当"私人金主注资"**；从它收 ETH=经某公共服务出金，不构成金主关联边，性质同 Relay 断头 |
| `0xb01ca24bd01be40ee950a8746cf7546134442049` | 公共 swap bot 合约（双向：买入币直达用户、卖出经它原子入→卖；2026-07-13 部署，两天即 92 独立 txfrom）（来源：Pointless D14 告警甄别 2026-07-15） | 有默认参数指纹：多个用户单笔买入恰为 0.99 ETH——"同金额+同合约"可能只是工具默认值，不足以单独判同一运营者 |
| `0x2ca37ff95caf25366ef16fc2e655b78a165d125f`、`0x5d6395cde0e26aa97fcf3a8004439f29a9124d5c` | 公共工具合约（12.5KB / 21.6KB，未验证）（来源：RAXOL 增量更新复核 2026-07-14） | 旧报告曾误归"即收即卖漏斗地址"；实为工具合约。"漏斗"定性前先 getCode |
| `0x3da66157309794822c1506702a9c966fd9612773` | 原子中转小合约（1.5KB，进出同 tx 同额转发）（来源：RAXOL 增量更新复核 2026-07-14） | 曾以"共同上游"形态把多个独立买家虚接成假集群——聚类剔除 |
| `0xa58bdd0ab5ebbb8dc425090fea8fd0ba969c1668`、`0x7b021ceb65edaf40ed73c51e78cf44ad4edf99a4`、`0x48a097df16c7844a33b1c3d11ab353457846e13f`、`0x50ad1c820290c9cc694dd47b0a61323f4d163e7e`、`0x4e5ffb3bd801d9db9a98daee7d4293afd46da677` | 路由/中转合约组（100% 同 tx 进出、txfrom 高度分散、余额归零）（来源：RAXOL 增量更新对抗复核 2026-07-14） | 怀疑者以"共同上游"聚类曾拼出 63 址假大集群（2.26% 总量），穿透后全系此类设施——增量新庄扫描前先把它们剔干净 |
| `0x58daec3116aae6d93017baaea7749052e8a04fa7` | Uniswap V4 PositionManager（Robinhood；来源：TRASH 分析 2026-07-14） | 96,061 笔平台 keeper EOA 形态，替所有 launchpad 币建池、铸 LP NFT。gas/币流勿据它聚类 |
| `0xe6cae83bde06e4c305530e199d7217f42808555b` | Robinhood 钱包 EIP-7702 标准实现之一（来源：TRASH 分析 2026-07-14） | 海量 App 散户 7702 户共用（TRASH top30 大户 12/14 指向它）。**同实现≠同实体**，勿聚类 |
| `0x53bf6b0684ec7ef91e1387da3d1a1769bc5a6f77` | Uniswap UniversalRouter **第二部署**（已验证，全链 24.7 万 tx）（来源：TRASH 增量更新 2026-07-14） | 与 `0x8876…0904` 并存的另一 UniversalRouter——设施剔除两个都要含。曾被误判"庄#1 私有漏斗"纳入实体表（早期单币用户少造成"只服务 2 上游"假象，后期 68 个流入方）；**单币早期用户数少≠私有** |
| `0xe492912f37c2a4eca45d42dc67548f4c6cd7ce2b` | 买入代理合约（2,265 笔 IN 全部来自 PoolManager、OUT 分发 300+ 地址）（来源：TRASH 增量更新对抗复核 2026-07-14） | 公共买入执行设施：多个独立买家经它从池收币——以它为"共同上游"的聚类一律作废（曾拼出 3.33% 假组） |
| `0x3f43479c8536F7eE8180d0f67a050980dC5Bc8C8` | batchTransferNative 批量转账工具（5,012 tx 公共 multisend）（来源：TRASH 增量更新对抗复核 2026-07-14） | 批量平分 ETH 的公共工具。**"同用它分钱"不构成关联**；但其单笔调用内的收款人列表（一次把 X ETH 平分给 N 址）是**该次调用者自己的钱包组**——判关联看单笔调用的 payload，不看工具本身 |
| `0xd29c85f15df544ba632c9e25829fd29d767d7978` | Across 桥 Universal_SpokePool（ERC1967Proxy 已验证，11 万+笔；internal 交付 ETH、≥100 收款址）（来源：NOXA+VEX 两会话同日独立核验 2026-07-15） | 跨链入金通道之三（与 Relay 桥/App 零地址充值并列）：以 internal 转账给用户发 ETH。**"共同上游是它"="同用 Relay 桥"同级弱信号，不构成关联**（NOXA 案一条实体关联假设、VEX 案一个弱信号对均据此作废） |
| `0xb0999731f7c2581844658a9d2ced1be0077b7397` | 公共 bot 服务费收集地址（23,998 笔、发送者高度分散）（来源：NOXA 分析对抗复核 2026-07-15） | 用户经该 bot 交易时向它付小额 ETH 费。**"共同下游是它"不构成关联**（复核剔除了一条据它建的实体边）；两地址同秒向它付费只说明用同一公共 bot 服务 |
| `0xb01ca24bd01be40ee950a8746cf7546134442049` | 公共 bot 卖币执行合约第二部署（未验证 23.4KB，与 `0x9be3cc…237c` 同模板；140 txfrom 用户、期初期末零库存）（来源：VEX 增量更新 2026-07-15） | 与 0x9be3 同款"用户调用同 tx 代卖进池"设施——**设施剔除名单两个部署都要含**（同 UniversalRouter 双部署之理）；表观大额卖出=散户合计透传 |

| `0xcdca5d374e46a6dddab50bd2d9acb8c796ec35c3` | Chainlink CCIP OffRamp（已验证）（来源：VIRTUAL 分析 2026-07-16） | CCIP 跨链 mint 的统一 txto——桥入代币（如 VIRTUAL）的入口执行合约；"txto=它"的 mint 即官方 CCIP 桥入 |
| `0x78680385fcb8187ac1b28e0d6b1e0acf5e0d0992` | CCIP 桥出收集通道（来源：VIRTUAL 分析 2026-07-16） | 全部 burn 的前置收款方（收币→同链 burn，净 0 设施）——**"转给它"=桥出回主链**，勿判卖出/私下转移 |
| `0x43e4c17b15365596caae8e7d00e42bc8e988c2d4` | Virtuals TokenFactory 直连分发代理（TransparentUpgradeableProxy 已验证）（来源：VIRTUAL 分析 2026-07-16） | 96% 入金来自 TokenFactory，持续过手报价币净 0——平台常设分发枢纽；曾被误判"短命高频设施"，定性前先看首笔时间与入金构成 |

> `0x6d80b81d…`（上表 Virtuals AgentTaxV2）补充语义（VIRTUAL 分析 2026-07-16）：对报价币 VIRTUAL 本体而言它是**机械税变现通道**——归集生态税收（VIRTUAL 计价）经 USDG 池 swap 换稳定币并 70/30 分账；其持续"卖出"是机制流水（规模跟随生态交易量），勿当实体出货，监控应反向盯"税流断流"。

> RelayRouterV3 完整地址见上方 EVM 聚合器基建段 `0xb92fe925…`（跨链同址；Robinhood 链上表现为 392 进/599 出的清算金库形态）。UniV3Factory、NonfungiblePositionManager、LP 费用合约等如遇到仍需 Blockscout 现场核验。

## Filecoin（FIL 分析核验 2026-07；actor ID 由协议分配，不轮换）

| 地址/段 | 标签 |
|---|---|
| `f0121` | Filecoin Foundation |
| `f0117`–`f0120` | Protocol Labs 系列 |
| `f090` | 挖矿储备（Mining Reserve） |
| `f00`–`f0126` 低位段 | 创世实体集中区（另含 Faucet、Burn 等系统地址）：逐个 `GET /address/f0<N>` 批量取全部官方标签，方法见 data-pipeline-filecoin.md §2 |
