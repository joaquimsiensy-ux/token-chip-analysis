# EVM 链数据管道 · 辅助数据面与链专节（data-pipeline-evm 分册 2/3）

> 母文档：`data-pipeline-evm.md`（已拆为薄路由索引页，文档级引言与时效纪律见索引页）。本册覆盖原 **§4 辅助数据面速查表 / §8 Base 链专节 / §9 Arbitrum 链专节 / §10 质押型代币标的范式**；§1/§2/§3/§6/§7 见 `data-pipeline-evm-channels.md`，§5/§11/§12 见 `data-pipeline-evm-recon.md`。正文 §N 交叉引用一律为母文档节号。规则逐条原样迁移、零改写；最后整编 2026-07-22。

## 4. 辅助数据面速查表

| 用途 | 端点/命令 | 要点 | 来源 |
|---|---|---|---|
| 起手定位 | `curl https://api.dexscreener.com/latest/dex/tokens/{token}` | 零注册；返回链/主池/DEX/流动性/创建时间/社媒；多池列表可分主池与尘埃池 | （来源：SIREN(BSC) 分析，2026-07） |
| 合约身份批查（聚类前设施识别第三通道） | `scripts/labels/sourcify_check.py <chain> <地址文件>` | Sourcify v2 免 key 直连；verified 合约名直接暴露身份（PancakeRouter/GnosisSafeProxy/池），代理连实现名一并返回；聚类前对候选地址群跑一遍防设施混入实体集群；404=Sourcify 无源码≠EOA（判 EOA 仍用 getCode）；标的合约用通用模板名（如"Token"）本身即分析信号；⚠v1 批量端点 brownout 弃用（→2027-01），只走 v2 逐地址（0.25s 间隔实测无 429）；支持 eth/bsc/base/arbitrum/polygon，无 robinhood 等小众链 | （来源：B10 Sourcify 接入实测，2026-07-22） |
| 合约安全 | `curl https://api.gopluslabs.io/api/v1/token_security/56?contract_addresses={token}` | 免费无 key；LP 持有人字段可能对应尘埃池而非主池，须与工厂合约 getPair 核对 | （来源：SIREN(BSC) 分析，2026-07） |
| 貔貅模拟 | `curl 'https://api.honeypot.is/v2/IsHoneypot?address={token}&chainID=56'` | 已知误报机制：模拟器对无代码地址发起调用失败被记成 sellTax=100（V3 池代币易中）；必须 GoPlus + 链上真实卖出成交笔数 + 直接 RPC 模拟大户卖出三角验证后才可定性 | （来源：SIREN(BSC) 分析，2026-07） |
| 日 K（近期） | `api.geckoterminal.com/api/v2/networks/bsc/pools/{pool}/ohlcv/day?aggregate=1&limit=1000` | 免费但实际只返回 181 天，老币历史不完整需补源；hour/minute 端点对上线较久的池可能直接返回 0 条（day 正常时 hour 也空，实测），别当采集失败重试；hour 加 before_timestamp 翻页对 >41 天前历史段同样返回 0 条（免费层窗口硬限）——历史行情窗只有日线，小时级须链上池储备重建 | （来源：SIREN(BSC) 2026-07；哈基米(BSC)/ASTEROID(ETH) 2026-07-18） |
| 全量 K 线 | `data.binance.vision/data/futures/um/monthly/klines/{SYM}USDT/1d/{SYM}USDT-1d-YYYY-MM.zip`（另有 daily/） | 若代币上了币安永续则免费无 key 拿全史；月度包+当月每日包拼接去重，几秒完成 | （来源：SIREN(BSC) 分析，2026-07） |
| 地址标签 | WebFetch `https://bscscan.com/address/{addr}` 及 `/txs?a={addr}&ps=100` | 拿 Public Name Tag/合约创建者/首笔注资来源；大户定性必须查浏览器官方标签，不能只看链上行为猜——曾有多个"疑似庄家"地址查标签后证实为 CEX 储备/热钱包 | （来源：SIREN(BSC) 分析，2026-07） |
| top100 持仓/交易者/K线 | scripts/evm/fetch_gmgn.sh（gmgn-cli 批量） | 坑见下方列表 | （来源：OPN/SIREN(BSC) 分析，2026-07） |
| 日线价格全史 | `api.coingecko.com/api/v3/coins/{id}/market_chart?vs_currency=usd&days=365&interval=daily` | 无 key 免费；币页 WebFetch 另可拿合约地址/流通量/FDV，合约地址须双源一致才采用；⚠`days=max` 免费层已死（error 10012 限 365 天，2026-07-18 实测）——**更早历史改用下行 DefiLlama** | （来源：OPN(BSC) 2026-07；ASTEROID(ETH) 2026-07-18） |
| **老币历史价格主兜底** | `scripts/prices/llama_price.py series <chain> <addr> --start <日期> --out p.json` | DefiLlama coins.llama.fi 免 key 直连限速宽；按合约地址直查免找 CG id；chart 端点分段拉全史日线（单段 500 点上限脚本自动分段，CAKE 2020-09 起 2117 点实测无缝）、输出与 CG market_chart 同构下游零改动；spot 子命令批量单时点；聚合价带 confidence——发射窗口精确配价仍用链上主池重建；未收录 exit=3 别拿空当零价；链名用 ethereum 不是 eth（脚本容错）；此前 Poloniex candles 兜底降为其后备 | （来源：B11 DefiLlama 接入实测，2026-07-22） |
| 部署 tx 一步拿模板指纹 | Etherscan V2 `module=contract&action=getcontractcreation` | 返回 creator/txHash/blockNumber/**creationBytecode**——constructor 特征函数名（如 atInversebrah 类乱名）即合约模板指纹，连环发币人识别：同 dev 多次 CREATE 的字节码指纹比对，一次调用免扫块 | （来源：ASTEROID(ETH) 分析，2026-07-18） |
| 是否上过币安 Alpha | `curl https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list` | 官方全量表（600+ 币）**含 fullyDelisted/offline 全历史存档**——可排除"曾上架后移出"；canTransfer 字段实证 Alpha 代币不可提币。**Alpha 2.0 Router Proxy 持仓性质判定的关键一步**：未上架代币的 Router 持仓=外部单方面打入（ERC20 转账无需接收方同意），是营销道具/变相冻结，不是托管买盘。上架时间的链上锚点=Router 首次收该币块（与公告新闻互证）；**Router 托管量月度差分=币安场内净买卖压力曲线（Alpha 在架币标配分析件）**，净流出月归因必查"经场内结算引擎回吐（场内净卖出）vs 直接提现"两分量占比，勿直接猜跨所搬砖 | （来源：bibi(BSC) 2026-07-12；哈基米(BSC) 2026-07-18） |
| four.meme 发射参数 | `curl https://four.meme/meme-api/v1/private/token/get/v2?address={token}` | ✅2026-07-19 SIREN 实测**复活可用**（此前"全路径 404"过时）：返回 totalAmount/saleAmount（曲线售罄量，SIREN=8 亿/80%）/raisedAmount（毕业募集 BNB）/launchTime/userAddress（=creator）/tokenPrice.marketCap；与链上 mint 块时间戳互验；bundle 成本=买入 tx 实付 value + raisedAmount + 毕业注池额三方闭环 | （来源：bibi(BSC) 2026-07-12；SIREN(BSC) API 复活实测 2026-07-19） |
| CEX 封闭盘识别三角 | ①`api.kucoin.com/api/v3/currencies/{SYM}`（免 key，isDepositEnabled/isWithdrawEnabled/chains 含合约地址）②各所现价：Gate `api.gateio.ws/api/v4/spot/tickers?currency_pair={SYM}_USDT`、MEXC `api.mexc.com/api/v3/ticker/price?symbol={SYM}USDT`（均走 clash 代理）③链上池价 GeckoTerminal | rug 后风控关充值→"链上买→充值→场内卖"套利腿被斩断→各所内盘成独立封闭盘、价格脱锚（SIREN 实测 KuCoin/Gate 较链上 +135%）。**多所价差>20% 时 CoinGecko 聚合价被污染成系统性坏数据，估值必须弃用**（SIREN CG $0.055 vs 真实 $0.0288） | （来源：SIREN(BSC) 分析，2026-07-19） |
| 单地址全量流水独立复核 | HyperSync query 按 address 过滤 topics | 对关键黑箱地址（如托管合约）用 HyperSync 独立重扫其全部 Transfer（可跨全部代币），与扫块 CSV 互为独立通道——对账级双验证的低成本方式 | （来源：bibi(BSC) 分析，2026-07-12） |
| 千级地址现时余额 | scripts/evm/multicall_balances.py | 见 §3.5 | （来源：SIREN(BSC) 分析，2026-07） |
| TGE 老币全史日K | `api.gateio.ws/api/v4/spot/candlesticks?currency_pair={SYM}_USDT&interval=1d&limit=1000`（走 clash 代理） | 免 key 单次最多 1000 根，SQD 实测一次拿 796 根全史——上过 Gate 现货的 TGE 老币全史价格正解（GT 181 根墙/CoinGecko 365 天墙的解法）；上过 Gate 的币远多于上币安的，覆盖面广 | （来源：SQD(Arbitrum) 分析，2026-07-20） |
| 第三方富豪榜快照（CoinCarp 类） | — | ⚠只当历史线索、绝不当现状数据：快照可严重过时（SQD 案榜前 8 有 6 个现持已清零，快照疑似两年前）——现状持仓一律链上实查 | （来源：SQD(Arbitrum) 分析，2026-07-20） |
| 官方 subgraph 免 key 白嫖 | 项目 explorer 前端 bundle 里 grep `gateway.thegraph` 附近的压缩变量赋值 | 前端直连 The Graph gateway 的项目会把 API key 以 NEXT_PUBLIC_ 环境变量内联进公开打包 JS（每个访问者浏览器都在用）——提取即得免 key 通道，**对任何"前端直连 subgraph"的项目通用**；LPT 案 10 次查询拿到质押账本快照/全轮次历史，与链上重放双源互验。批量分页快照落盘模板：LPT 工作目录 fetch_subgraph.py（专属存档，非复用件；skip 分页有 5000+1000 上限） | （来源：LPT(ETH+Arbitrum) 分析，2026-07-21） |
| 事件签名 topic0 正算/反查 | 正算：`web3_sha3` RPC（publicnode 支持）；反查：`api.openchain.xyz/signature-database/v1/lookup?event=0x...,0x...&filter=true` | 本机无 keccak 库时 web3_sha3 直接算事件签名 topic0（比装包/在线工具快）；openchain 批量逗号分隔一次全解（LPT 案 BondingManager 12 种 topic0 一次解完）——⚠参数名是 `event` 不是 `topic`，用错返回全空**不报错** | （来源：LPT(ETH+Arbitrum) 分析，2026-07-21） |
| 更老币（2021 前上所）早期价格 | Poloniex candles API（2021-01 起可用，limit 500） | 2018-2021 段老币价格免费源全谱系实测：CoinGecko `/coins/{id}/history` 免费层对老币历史**全 no-price**（月度快照 41 连败）、CryptoCompare histoday 无数据（已入死亡名单）、币安月度包仅覆盖上所后——2021 前只剩 Poloniex candles；更早段报告声明截断 | （来源：LPT(ETH+Arbitrum) 分析，2026-07-21） |
| 币安 Alpha **场内** K 线 | `www.binance.com/bapi/defi/v1/public/alpha-trade/klines?symbol=ALPHA_{alphaId}USDT&interval=1d`（走 clash 代理） | Alpha 在架币**场内盘口**的日级量价（标准币安 12 列 K 线含 trades 笔数字段，bapi 信封 `data` 数组）——Alpha 黑箱唯一的场内价格/量能直查通道，与链上池价对照可检场内外价差、场内成交笔数配合 Router 托管差分解读净压力；alphaId 从 token/list 全量表（上方端点）取。⚠单次实测返回 374 天且首行晚于上架日（窗口/limit 上限，翻页未测）——**非全史**，更早段配 CMC 全史日线补 | （来源：QUQ(BSC) 筛查，2026-07-22） |
| 全史日线（跨链通用兜底） | `api.coinmarketcap.com/data-api/v3/cryptocurrency/detail/chart?id={cmc_id}&range=ALL` | CMC 网页版内部 data-api，一次拿发射日起全史日级量价——破 CoinGecko 365 天墙/GT 181 天墙的正解（与 data-pipeline-solana §4 同条目，USELESS(Solana) 首测 437 点；QUQ(BSC) 二案复用 488 点全覆盖）；cmc_id 从币页 URL/search 端点拿 | （来源：USELESS(Solana) 2026-07-21；QUQ(BSC) 筛查 2026-07-22） |

**价格序列覆盖审计（链无关正式门槛）**：任何日线/小时线进入图表前，先落 `source/start/end/points/max_gap/has_volume/second_source_status`；发射日至首点的空窗、序列内部缺日和末端滞后分别列出。端点“成功返回数组”不等于覆盖完整；有缺口就画断线并降级事件回报措辞，禁止插值补成连续真值。DefiLlama 等聚合源尤其要逐段检查首尾与最大间隔，完整性不能从接口名推定（来源：ASTEROID(ETH) 完整分析复盘，2026-07-24）。

**Blockscout internal-transactions 完备性纪律**：调用地址内部交易端点时必须逐页拉到分页终点，并保存响应里的分页/不完整提示；若服务端明确返回 incomplete、截断或仍有 next page，当前汇总只能写“已返回记录的下限”，不得当作该地址全史 ETH/native 流。关键 P0/P1 的内部价值流须再用交易回执/trace 或另一通道复核（来源：ASTEROID(ETH) 完整分析复盘，2026-07-24）。

gmgn-cli 使用坑（fetch_gmgn.sh 已内置处理）：
- 命令用全路径 `~/.npm-global/bin/gmgn-cli`（不在 PATH；报 command not found 时别去重装）。（来源：SIREN(BSC) 分析，2026-07）
- `--raw` 输出顶层结构不一致：有的是 `{"list":[...]}`，有的是 `{"data":{"list":[...]}}`；解析统一用 `(j.get('data') or {}).get('list') or j.get('list') or []`，否则筛选会假阴性得 0 行。（来源：SIREN(BSC) 分析，2026-07）
- holders top100 稳定且信息量最大（tags、start_holding_at、history_transfer_in/out、native_transfer.from 可做 gas 来源聚类）；traders 按 profit 排序可能只回约 9 行、按 amount_percentage/sell_volume/buy_volume 排序可能 0 行、部分 --tag 组合 0 行；kline 只回 100 条只能兜底。（来源：OPN/SIREN(BSC) 分析，2026-07）
- holders/traders 接口权重 5，有 leaky-bucket 限速，批量采集脚本必须加节流间隔。（来源：OPN(BSC) 分析，2026-07）

### 非 EVM 链的供给对账通道（多链标的用，2026-07-26 IQ(ETH) 补）

多链标的的分支链可能不在 EVM 上（老项目尤其常见：EOS/Tron/Cosmos 系原生发行史）。只查 EVM 侧会漏掉整份独立供应，判定法见 `playbook-supply-recon.md §1b`。已实测可用的免 key 通道：

| 链 | 端点与调用 | 实测 |
|---|---|---|
| EOS | `POST https://eos.greymass.com/v1/chain/get_currency_stats`，body `{"code":"<代币合约账户名>","symbol":"<符号>"}` | ✅ 国内直连免 key；返回 `supply` / `max_supply` / `issuer` 三字段，秒级 |
| EOS（备用节点） | `api.eosn.io` / `eos.eosphere.io` 同路径 | 主节点故障时轮换 |

EOS 侧持有人榜可用 `POST /v1/chain/get_table_by_scope`（`code`=代币合约、`table`=accounts）枚举持币账户名，但**返回的是 scope 名不含余额**，逐账户余额要再打 `get_currency_balance`；账户名是人类可读字符串（非 0x 地址），标签库无法复用，做深度分析需另建管道——**仅做供给对账时不必走到这一步**。

## 8. Base 链专节（PING 全量实测，2026-07-17）

### 8.1 全量转账双通道拓扑（与 BSC 经验相反：高峰期 Alchemy 是主力）

- **HyperSync base 端点（base.hypersync.xyz）高峰期 429 严重**：单进程串行仍连败，退避后有效吞吐 ~250 条/s 且不稳定——BSC"HyperSync 全程稳定"的经验在 Base 高峰时段不成立，§1 决策树不可照搬（来源：PING(Base) 分析，2026-07-17）
- **Alchemy base-mainnet getAssetTransfers 实测 ~230 条/s 稳定零限流**（须走 clash 代理；免费层 30M CU 拉 239 万条余量充足）——Base 高峰期 Alchemy 反而是主力通道（来源：PING(Base) 分析，2026-07-17）
- **分段接力法（双通道 2:1 提速）**：HyperSync 负责发射段（旧块），Alchemy 按 fromBlock/toBlock 切成多个块段并行接力拉近段；fetch_alchemy.py 已支持 `--config/--from-block/--to-block`（v2.26 参数化）（来源：PING(Base) 分析，2026-07-17）
- **★跨通道拼接去重键陷阱（链无关，凡 HyperSync+Alchemy 混拼皆适用）**：HyperSync uniqueId 尾号=链上 log_index，Alchemy uniqueId 尾号=**类别内序号**——语义不同，跨通道按 (tx, 尾号) 去重必然失败，重叠段双计实测造出 5,485 个负余额地址。正解=**按块段给通道划唯一归属**（每通道只收自己块段内的事件，段内用自家键去重），对账以"负余额地址数=0"放行；scripts/evm/replay_pass1.py 已固化该逻辑（来源：PING(Base) 分析，2026-07-17）
- **抽样估算量的 next_block 语义坑**：HyperSync 每次响应的 next_block 推进量由"服务端每响应条数上限"决定，不是固定块跨度——按"首段块跨度"外推全量会严重低估（实测低估 5 倍）；正确外推按事件密度分段抽样（来源：PING(Base) 分析，2026-07-17）
- **HyperSync base 非高峰时段单通道可行**（与上条"高峰期 429"互补，时段依赖）：单进程串行 213 万条 94 分钟拉完全程零 429（≈380 条/s 均速，含发射密集段）；但**主采集运行期间另发探测/复核请求会撞并发限制 429**（第 3 个并发请求即失败）——密度探测要在主采集启动前做完，或探测后再启动主采集（来源：jesse(Base) 分析，2026-07-18）
- **分时段密度探测法（转账量预估标准动作）**：对币龄按月取 4-6 个时点各发一个 HyperSync 单批请求，密度=返回条数/next_block 推进跨度，按分段密度加权外推总量——比"发射首月抽样外推"更准（发射月密度可为稳态 15 倍以上，实测 3.3 vs 0.2 条/块）（来源：jesse(Base) 分析，2026-07-18）
- **亿级标的规模基准（单币 1.263 亿条实测）**：VIRTUAL(Base) 全量 1.263 亿条 = HyperSync 101.1M（高峰段实测单 key 硬顶 ~750-820 条/s，退避后有效吞吐）+ Alchemy getAssetTransfers 24.7M（~470 条/s）；双通道并行墙钟约 30 小时——亿级转账标的的通道速率与 ETA 估算基准（来源：VIRTUAL(Base+ETH) 多链分析，2026-07-18）
- **抽样估总量的"二轮高峰"坑（与上条分时段探测法配套）**：12 段抽样窗踩中 2025 年初 ATH 段初估 1.32 亿（高一倍），按早期密度修正到 5-7 千万（低一半），实际 1.263 亿——祸根是 2025 年末存在此前未预料的第二轮活动高峰（段密度 12.5 笔/块 > ATH 期 7.4，价格却横盘）：生态型代币链上活动密度与价格周期脱钩，分时段密度探测必须覆盖到最近月份、禁止假设"ATH 段=密度峰值段"（来源：VIRTUAL(Base+ETH) 多链分析，2026-07-18）
- **双通道运行中再平衡禁忌**：重放去重是文件内单调逻辑，兜不住跨文件重复——分段计划 plan.json 固化后段边界绝不能改，禁止把同一段切给两个通道（产生跨文件重叠区）；唯一安全的接力=停一边、另一边从该段 .prog 断点续采（两边 CSV 同构且按序写入的前提下）（来源：VIRTUAL(Base+ETH) 多链分析，2026-07-18）
- **亿级多段拼接重放必做"丢弃行审计"（dropped-audit）**：去重丢弃行数应=重复键数，不等即有误杀；段间乱序写入造成的误杀行逐行甄别后补放（实测 607 键去重+607 行乱序误杀全部甄别补放，负余额地址 0 才放行）（来源：VIRTUAL(Base+ETH) 多链分析，2026-07-18）
- **跨天无人值守采集标准件（watchdog 守护+事件观察哨）**：nohup 守护进程每 60s 巡检——备用通道探测到可用即自启采集器、任一采集器死亡自动重启（断点续传保证不重不漏）、备用通道始终未启用则把其段归还主通道兜底、全段落定写 ALL_DONE 退出；会话侧用 Monitor tail -f 守护日志 grep 事件词（ALL_DONE/FALLBACK/HS_DEAD/ALCHEMY_DEAD）实现"完成即叫醒"。脚本：scripts/evm/watchdog_dual.py + fetch_hypersync_par.py（v3.4 参数化收编，含 plan.json 段计划固化/.prog 断点/.aldone 完成标记体系）（来源：VIRTUAL(Base+ETH) 多链分析，2026-07-18）

### 8.2 Base 辅助数据面

- 官方 RPC `mainnet.base.org`：getLogs 限 10,000 块/次、JSON-RPC batch 限 10 calls/请求——角色事件（RoleGranted 等）全史查询改走 HyperSync topic 过滤（一次请求拿全史）（来源：PING(Base) 分析，2026-07-17）
- Blockscout `base.blockscout.com` 免 key 可用：`/api/v2/transactions/{hash}/token-transfers`（单 tx 双币腿核账，定性"领费 vs 买入"，见 playbook §11）、`/api/v2/addresses/{addr}/counters`（公共性体检查 tx 总数）（来源：PING(Base) 分析，2026-07-17）
- **config.json 的 deploy_block 必须记真实部署块**（eth_getCode 二分或浏览器合约页取），不是首笔 Transfer 块——两者可差数千块，记错会漏掉部署时授予的权限角色事件（链无关纪律）（来源：PING(Base) 分析，2026-07-17）
- **Blockscout v1 API 一次拿最早注资 tx**：`base.blockscout.com/api?module=account&action=txlist&address=X&sort=asc&offset=3&page=1` 直接升序返回最早交易——v2 API 只有降序分页（活跃地址翻十几页都到不了底），批量注资溯源一律走 v1 sort=asc（来源：jesse(Base) 分析，2026-07-18）
- **Base App 智能钱包（CoinbaseSmartWallet/ERC-4337）txlist 溯源失效**：此类钱包零外部交易（全部操作经 EntryPoint handleOps、bundler 各不相同），v1/v2 txlist 均查不到注资来源——溯源改走 token 层流水+UserOp 解析；GMGN 大额榜出现"纯转入零买入"新形态也是同因（来源：jesse(Base) 分析，2026-07-18）
- **Coinbase Bundler（`0x8d47ba07ff9ccccf58c7e8810ee42c0dc8b8b123`，Basescan 官方标签）是 Base App 系发射/操作的 tx.from**：经 Base App 内嵌流程发币时合约创建者显示为该 bundler——它是 AA 基础设施不是发行主体；注意 Blockscout 对它标 is_scam=true 属自动风控误标，以 Basescan 为准（标签库已收录为 gas 溯源假金主源）（来源：jesse(Base) 分析，2026-07-18）
- **EIP-7702 委托 EOA 在 Base 大量出现**：eth_getCode 前缀 `0xef0100`+20 字节 delegate 地址即是；GoPlus is_contract=1 误报（BSC 坑表已有）之外，**Blockscout 的 is_contract=true 且 smart-contracts API 无名**也是 7702 特征——大户榜"无名合约"先查 code 前缀再定性；不同 delegate 不构成关联边（来源：jesse(Base) 分析，2026-07-18）

### 8.3 Uniswap V4 标的范式（Base 高发）

- 全部 V4 池共享 **PoolManager 单例**（Base：`0x498581fF718922c3f8e6A244956aF099B2652b2b`）：池子代币余额记在 PoolManager 一个地址名下=**全部 V4 池合计**，单池口径须经池内事件/GeckoTerminal 侧拆分；把 PoolManager 当普通地址会把"池子"误读成超级大户（来源：PING(Base) 分析，2026-07-17）
- pairAddress 是 32 字节 pool id（非合约地址）；GeckoTerminal OHLCV 直接用 pool id 可查（来源：PING(Base) 分析，2026-07-17）
- "LP 锁定"的 V4 实现形态=token 合约自持 LP position + 源码无撤出函数（读源码验证），与 V2 的打死锁/第三方锁仓合约完全不同——按 V2 思路找 locker 会得出"LP 未锁"误判（来源：PING(Base) 分析，2026-07-17）

### 8.4a Zora CreatorCoin 标的范式（Base 高发，与 §8.3 V4 范式配套）

- **识别**：Blockscout 合约 implementations 名=CreatorCoin（clone → Zora 官方实现）；CoinGecko 分类含 Zora Creator（来源：jesse(Base) 分析，2026-07-18）
- **协议结构（合约源码级常量，github ourzora/zora-protocol）**：总量 10 亿；发射 tx 内 10 亿全部 mint 给代币合约自身 → 5 亿（50%）经 ZoraV4CoinHook 注入 V4 池、5 亿（50%）留在**代币合约自身**作创作者 vesting——**合约自持仓=锁仓桶而非项目方现仓**，阵营划分单列；vesting 5 年纯线性（5*365.25 天）无 cliff，claimVesting() 随时可领 → payoutRecipient（**可由创作者变更**，监控要盯变更事件）；creator coin 一律配对 ZORA（不是 ETH！），content coin 配对其创作者的 creator coin（两层金字塔，content 交易给 creator coin 制造经常性兑换）；池费 1%：20% 转单边流动性永久锁池（底部深度缓慢增厚），创作者分成占总费 50% 且**以 ZORA 结算**——创作者费收入不构成本币直接卖压（来源：jesse(Base) 分析，2026-07-18）
- **防狙击税只挡 10 秒**：LAUNCH_FEE_START=99% 起始税 10 秒线性衰减——职业狙击生态靠 Base Flashblocks（200ms 微块）在部署同块抢跑（外部研究员披露约 90% 的 creator coin 发射被同块狙击）；发射同块买家全景是此类标的的标准分析件（来源：jesse(Base) 分析，2026-07-18）
- **同块狙击的标准结构**="买手→卖手"同秒零对价整仓转移+切片出货（私有 sell 合约/等额拆分/BaseSettler 通道各有版本）；多组同型结构≠同一实体——执行栈指纹互斥（自建合约 vs 私有 sell 合约 vs 预部署合约 vs 拆分中转）+组间零资金边可证独立性；狙击者共用同一 CEX 热钱包提币备弹药不作关联边（来源：jesse(Base) 分析，2026-07-18）
- **退出深度专项（ZORA 配对标的必做）**：全部流动性可 90%+ 绑在 ZORA 计价主池，非 ZORA 出口（WETH/USDC 小池）可能只有几万美元——退出承接=主池 ZORA 侧深度，账面市值/承接比+双重贬值链（卖本币得 ZORA、ZORA 再卖一次）是此类标的的核心风险呈现件（来源：jesse(Base) 分析，2026-07-18）

### 8.4 x402/付费 mint 型标的采集特性

- mint 走 facilitator **批量代执行**（一个 tx 打包约 47 笔 mint、付款币全额入池），facilitator=MINTER 角色持有者——mint 账本按 Transfer(from=0x0) 的**接收地址**记，不能按 tx.from（否则全记到 facilitator 名下）（来源：PING(Base) 分析，2026-07-17）
- 转账笔数与市值的异常比可极端（实测 $150 万级市值 239 万笔 Transfer）——数据量预估禁止按市值直觉，先抽样按事件密度外推（呼应 §8.1 抽样坑与 playbook §9 异常比信号）（来源：PING(Base) 分析，2026-07-17）

## 9. Arbitrum 链专节（SQD 全量实测，2026-07-20）

Arbitrum One（chainid 42161）待遇比 BSC/Base 好：Etherscan V2 免费层全开 + 官方公共 RPC 稳定直连，EVM 通用管道原样可用，无需专用脚本。

- **全量转账主通道 = HyperSync `arbitrum.hypersync.xyz`**：fetch_hypersync.py 改 config 端点即用；SQD 实测 83.2 万条 Transfer 56 分钟拉完（sleep 0.25）。（来源：SQD(Arbitrum) 分析，2026-07-20）二战数据点：LPT 案 129.4 万条 Transfer 97 分钟（含与 eth 端点同 key 争抢限流段，见 §3.1 key 级共享限流）；40.9 万条合约全事件（不筛 topic，fetch_hypersync_logs.py）26 分钟。（来源：LPT(ETH+Arbitrum) 分析，2026-07-21）
- **Etherscan V2 免费层对 chainid=42161 全可用**（与 BSC/Base/OP 锁付费层待遇相反，免费三链 ETH/Arb/Polygon 见 api-keys）：tokentx、getLogs（工厂事件枚举 1000 条/页）、proxy 系 eth_getTransactionByHash / eth_getBlockByNumber 全通——对账交叉验证与 vesting 工厂枚举（playbook-supply-recon §1）都走它。（来源：SQD(Arbitrum) 分析，2026-07-20）
- **官方公共 RPC `arb1.arbitrum.io/rpc` 直连免代理**：eth_call balanceOf / getCode 稳定，对账现值核验十几连发无限速。（来源：SQD(Arbitrum) 分析，2026-07-20）
- **Blockscout Arbitrum**：`arbitrum.blockscout.com/api/v2/addresses/{addr}`（免 key 走代理）——标签/is_contract/ens 通道结构可用（SQD 案标签全空但接口正常，标签覆盖别指望它）。（来源：SQD(Arbitrum) 分析，2026-07-20）
- **价格：GeckoTerminal 免费层对老币有一年历史墙**——OHLCV 单次仅回约 181 根，且 before_timestamp 翻页也翻不过 1 年深度——TGE 老币全史价格改走 Gate 现货日K（§4）。（来源：SQD(Arbitrum) 分析，2026-07-20）
- 0 值转账投毒与仿冒地址贴脸在 Arbitrum 同样高发（SQD 案 31,814 笔 0 值占 3.8%；仿冒关键实体地址前缀的假地址实见）——计数剔 0 值、关键地址完整比对，既有纪律 Arbitrum 再验证。（来源：SQD(Arbitrum) 分析，2026-07-20）
- labels 标签库暂无 arbitrum 链表，用 eth 库跨链复用可命中主流 CEX（SQD 案命中 17 个 CEX 地址——Arbitrum 大所热钱包多与 ETH 主网同址）；HTX 例外未命中（见 CHANGELOG v3.9.0 Known Gaps）。（来源：SQD(Arbitrum) 分析，2026-07-20）

## 10. 质押型代币标的范式（方法链无关，LPT(ETH+Arbitrum) 首战实测，2026-07-21）

标的有原生质押体系（BondingManager/Staking 类合约，bond 时代币 Transfer 进协议金库）时，纯 ERC20 Transfer 重放会把全部质押大户记成"转给协议"，筹码结构整体失真。标准动作六件：

1. **权益合并口径**：持仓 = ERC20 余额 + bonded 质押权益，两账本合并（规则见 playbook-supply-recon §1）。金库（Minter 类）行**必须替换为残差**（金库余额 − Σ已归属 bonded），否则与穿透归属双计。（来源：LPT(ETH+Arbitrum) 分析，2026-07-21）
2. **质押账本状态机重放**：用 fetch_hypersync_logs.py（scripts/evm/，全事件版：不筛 topic、保留 topic0-3+data）拉质押合约全事件，先解出 topic0 映射**落盘成 topic_map JSON**，再写状态机重放。**"关键字符串从落盘文件取"纪律覆盖 topic0/事件签名**——LPT 案手敲 TransferBond topic0 错一段，扫出 0 笔 silent fail（无报错，靠"这类事件不可能为零"的直觉才发现）。**校准锚点范式**：事件自带事后绝对值字段的（如 Bond 事件自带 bonded 总额），重放时逐事件比对作内置校准锚点——状态机漂移即刻暴露，比"只在末态对账"早几个量级发现 bug；老版本事件缺金额字段时联表同 tx 的 Transfer 补金额。（来源：LPT(ETH+Arbitrum) 分析，2026-07-21）
3. **记账式通胀的"已铸未领"桶**：奖励 mint 进金库但不分发（用户 claim 才落账）时，"已铸未领"必须单列桶（LPT 案 639 万 = 11.6% 总供给）——它既不是协议自有也不是可动用流通（规则见 playbook-supply-recon §1）；分析时对 top N 委托人可用 pendingStake 类 eth_call 校准到含未领口径。（来源：LPT(ETH+Arbitrum) 分析，2026-07-21）
4. **非 Transfer 换手事件审计（TransferBond 类）**：质押权益可不经 ERC20 Transfer 直接换主（LPT 案 1,774 万枚/1.1 万笔）——实体溯源与"庄不成立"阴性排查必须扫这类场外换手暗道。定性纪律：大额几乎全是跨链迁移中继批量落账（单中继服务 99-478 人=公共通道，按 §6 公共服务规则不作关联边），真定向转让极少但每笔都值得看。（来源：LPT(ETH+Arbitrum) 分析，2026-07-21）
5. **跨链迁移衔接的双计坑**：L1→L2 迁移常走 Migrator 特殊流程**不发 L1 Unbond 事件**——L1 账本"迁移后残留"+ L2 账本新记录在衔接月双计（LPT 案实体峰值虚增近一倍：19.4%→修复后 12.4%）。对策：L1 账本截断在迁移前最后一个完整月，衔接毛刺量化后写进报告局限性。（来源：LPT(ETH+Arbitrum) 分析，2026-07-21）
6. **月度粒度的峰值口径**：月末快照天然 sig 原子化，但月内脉冲被平滑——峰值口径纪律见 playbook-entity-cluster §6a。双链 ERC20+质押账本合并月度权益引擎（跟踪集+retail 聚合+质押前向填充）结构参考：LPT 工作目录 build_evolution.py / rebuild_stake_ledger.py（专属存档，非复用件）。（来源：LPT(ETH+Arbitrum) 分析，2026-07-21）
