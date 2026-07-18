# EVM 链数据管道实测手册（BSC/Base，2026-07 实测版）

> 本文合并两次 BSC 实战的通道结论。两份结论不矛盾：SIREN 会话因"从零分析"未复测 bloXroute，其免费端点死亡名单不含 blxrbdn；OPN 实测 blxrbdn 可用。两表合并即为下方决策树。（来源：OPN/SIREN(BSC) 分析，2026-07）
> 所有限速/吞吐数字为当时实测，节点政策随时会变；复用任何通道前先按 §6 做 1 分钟能力探测。

## 1. 全量转账通道决策树（BSC）

先估数据量（预估纪律见 §6），再选通道：

```
预估 Transfer 总条数？（先抽样发射首月外推，报保守上限）
├─ < 300 万条 ────→ bloXroute getLogs 扫块（免注册，scripts/evm/scan_transfers.py）
├─ ≥ 300 万条 ────→ ① envio HyperSync【首选】（需免费 token，scripts/evm/fetch_hypersync.py）
│                    ② Alchemy getAssetTransfers【备选】（需免费 key，scripts/evm/fetch_alchemy.py）
├─ 跨链代币的 ETH 主网侧 → Etherscan V2 免费 key（仅 chainid=1，scripts/evm/fetch_etherscan.py）
└─ 任何情况下都别碰 ──→ §2 死亡名单端点（禁止重探）
```

分叉依据：bloXroute 8 并发扫 249.6 万行约 80 分钟，量级再大耗时不可控且免注册通道无 SLA；HyperSync 拉 1568 万条约 5.2 小时且全程稳定。（来源：OPN/SIREN(BSC) 分析，2026-07）

| 通道 | 注册要求 | 限速实测 | 吞吐实测 | 断点续传 | 脚本 | 来源 |
|---|---|---|---|---|---|---|
| envio HyperSync | 免费 token（app.envio.dev 注册需 VPN；API 端点国内直连） | ⚠2026-07-18 起免费层限流收紧：0.15s 间隔高峰期 429 频发（实测 173 次/时级、吞吐腰斩），**0.5s 间隔基本消失**；同 key 2-3 进程按块段分兵并行可行（互扰有限），大标的提速正解=分段多进程+断点续拉（436 万条实战） | ~1000-1300 logs/2s；1568 万条约 5.2h | from_block 起点 + 增量写 CSV | fetch_hypersync.py | （来源：SIREN(BSC) 2026-07；哈基米(BSC) 429 实测 2026-07-18） |
| Alchemy getAssetTransfers | 免费 key（dashboard.alchemy.com 国内直连） | 平台级 429 全局限流，高峰期可整夜不可用 | ~46 万条/10 分钟，1000 条/页 | 读 CSV 末行区块置 fromBlock（勿依赖 pageKey） | fetch_alchemy.py | （来源：SIREN(BSC) 分析，2026-07） |
| bloXroute getLogs | 免注册 | 连发 5 请求全 200，~2s/请求，8 并发可承受。⚠2026-07-18 实测**历史保留窗口收缩至约 1 个月**（当前块−5.5M 块可用、−10.5M 块 header not found，二分 100M✗/105M✓）——已非全史通道，降级为"近期段快扫"（550 万块 555 段 7 分钟实测）；同端点两参数复测，未穷尽全端点池 | 10k 块/段 ×8 并发，249.6 万行约 80 分钟 | done-segments 清单 + 失败段补扫 | scan_transfers.py | （来源：OPN(BSC) 2026-07；哈基米(BSC) 窗口实测 2026-07-18） |
| Etherscan V2（仅 ETH 主网） | 用户免费 key | 免费层限速未成瓶颈 | tokentx 每页 10000 条，7 万余行顺利拉完 | 按返回末行 block 续页 | fetch_etherscan.py | （来源：OPN(BSC) 分析，2026-07） |

## 2. 死亡名单（实测不可用，3 个月内禁止重探）

免费匿名的 BSC 历史 getLogs 通道整体已死，唯一例外是 bloXroute。（来源：OPN/SIREN(BSC) 分析，2026-07）

> 时效纪律（v1.3）：本表实测于 2026-07。免费层政策季度级变化——任何条目距实测超过 3 个月后若确有需要，允许花 1 分钟小请求重探一次，复活/仍死都把本表日期更新；3 个月内维持禁令（重探是历史上最大的轮次浪费源之一）。否定性结论的入库纪律见 retrospective.md 红线 4。

| 端点/通道 | 实测症状 | 来源 |
|---|---|---|
| bsc-dataseed 系（bnbchain 官方） | getLogs 连 span=100 都报 -32005 limit exceeded；仅可做轻查询（见 §6） | （来源：OPN/SIREN(BSC) 分析，2026-07） |
| publicnode | 老区块要求 archive token | （来源：OPN/SIREN(BSC) 分析，2026-07） |
| dRPC 匿名（bsc.drpc.org） | 限 10000 块/次且 "Too many request" 频发，全链扫必卡死在重试 | （来源：OPN/SIREN(BSC) 分析，2026-07） |
| dRPC 注册免费 key（lb.drpc.org） | 持续 429；>10000 块不支持；network=bsc-archive / bsc-full 是非法名——注册了也没用 | （来源：SIREN(BSC) 分析，2026-07） |
| Alchemy eth_getLogs 免费层 | 限 10 个区块范围；但同一 key 换 alchemy_getAssetTransfers 方法即可用，别因此弃掉 key | （来源：SIREN(BSC) 分析，2026-07） |
| Etherscan 免费 key + chainid=56 | "Free API access is not supported for this chain"，两次会话都把它当过首选然后报废 | （来源：OPN/SIREN(BSC) 分析，2026-07） |
| api.bscscan.com v1 | 已 deprecated | （来源：OPN(BSC) 分析，2026-07） |
| 1rpc.io | getLogs 限 50 块 | （来源：OPN/SIREN(BSC) 分析，2026-07） |
| blastapi | getLogs 限 10 块 | （来源：OPN/SIREN(BSC) 分析，2026-07） |
| meowrpc | 不支持 getLogs | （来源：OPN(BSC) 分析，2026-07） |
| llamarpc / blockpi | 返回异常 | （来源：OPN(BSC) 分析，2026-07） |
| zan.top | 要注册 | （来源：OPN(BSC) 分析，2026-07） |
| 48.club | 限 5000 块且 "header not found" 不稳定 ⚠️**并非全废，见 §7.1**：外部会话实测它是**唯一可用的免费历史 getLogs 端点**，"不稳定"真相=只保留最近 ~6 天块，用于 6 天内新盘可用 | （来源：OPN(BSC) 分析，2026-07；外部 CZ/TCC(BSC) 考古修正，2026-07） |
| nodies / ankr / merkle / omniatech | 限范围/限量/限流，均无法扫全史 | （来源：OPN/SIREN(BSC) 分析，2026-07） |
| Routescan | 不支持 BSC（`chain not supported`） | （来源：外部 CZ(BSC) 考古，2026-07） |
| `api-legacy.bubblemaps.io` | 返回 400——Bubblemaps legacy API 已死（BSC/ETH 两场会话独立验证） | （来源：外部 CZ/ASTEROID 考古，2026-07） |

## 3. 各通道操作细节

### 3.1 envio HyperSync（scripts/evm/fetch_hypersync.py）
- POST `https://bsc.hypersync.xyz/query`；header `Authorization: Bearer {TOKEN}`；body 含 `from_block`、`logs: [{address, topics}]`、`field_selection`。（来源：SIREN(BSC) 分析，2026-07）
- 匿名（无 token）已不可用；token 让用户到 app.envio.dev 注册——控制台在用户（中国）网络打不开需 VPN，但 API 端点直连可用，"控制台打不开 ≠ API 不可用"。（来源：SIREN(BSC) 分析，2026-07）
- archive_height 到最新块，全史无缺口；换 token 地址与链子域名即可用于其他 HyperSync 支持链。（来源：SIREN(BSC) 分析，2026-07）
- key 不落盘：用户账号见 memory `onchain-data-accounts.md`，token 每次让用户现提供。
- **transactions 端点做 BNB 注资溯源**：body `{"transactions":[{"to":[addr]}],"field_selection":{"transaction":["block_number","from","to","value"]}}`（value 为 hex）——单址全链入金一次查询 ~2.3s 到 tip，比逐块扫快几个量级；⚠25 址×全链批量会 10 分钟超时，可用姿势=关键地址单址逐查 / 发射窗小块段批量（from/to_block 圈定）。（来源：哈基米(BSC) 分析，2026-07-18）
- 分段多进程姿势：复制脚本改 OUT 与 to_block 边界（`if nxt >= BOUND: break`）、sleep 提至 0.5s，各进程独立 CSV 事后按 (tx,log_index) 去重合并；改 config 后重启前删本地缓存的段清单文件。（来源：哈基米(BSC) 分析，2026-07-18）

### 3.2 Alchemy getAssetTransfers（scripts/evm/fetch_alchemy.py）
- POST `https://bnb-mainnet.g.alchemy.com/v2/{KEY}`，method=`alchemy_getAssetTransfers`，params 含 `contractAddresses`、`category:["erc20"]`、`maxCount:"0x3e8"`、`pageKey` 分页；返回自带时间戳。（来源：SIREN(BSC) 分析，2026-07）
- pageKey 有有效期，长任务中断后必过期：断点续拉一律读 CSV 末行区块号置 fromBlock 重开游标，容忍少量重复、下游按 tx hash 去重。（来源：SIREN(BSC) 分析，2026-07）
- 会遇平台级 429（"global traffic"，与自身配额无关、恢复时间不可控），曾整夜零进展：脚本内置指数退避（最长 20 分钟）+ 外层 while 冷却重启；卡点超 1-2 小时必须并行准备第二通道并用 AskUserQuestion 摆路径，绝不单通道死等。（来源：SIREN(BSC) 分析，2026-07）

### 3.3 bloXroute getLogs 扫块（scripts/evm/scan_transfers.py）
- POST `https://bsc.rpc.blxrbdn.com`，eth_getLogs 按 Transfer topic 分段扫：10000 块/段、8 并发 worker、~2s/请求。（来源：OPN(BSC) 分析，2026-07）
- 断点续传：done-segments 清单跳过已完成段；多线程必留失败段（某次 3392 段中 92 段失败），扫完自动列 remaining 并补扫，remaining=0 才算采集完成。（来源：OPN(BSC) 分析，2026-07）
- 起始块定位：勿用 eth_getCode 二分找部署块（免费节点历史状态请求被拒，会找错块导致空扫秒退）；改按"块时间戳 >= 已知安全起始日期"二分，起始日期用 GMGN start_holding_at 或跨链铸造日锚定，多扫无害。（来源：OPN/SIREN(BSC) 分析，2026-07）
- 同脚本顺带采时间戳锚点：每隔固定块距 eth_getBlockByNumber 取块头时间戳（数百个锚点几分钟采完），分析期 bisect 线性插值，省数千次逐块 RPC。（来源：OPN(BSC) 分析，2026-07）
- **起点缓存坑**：`<chain>_scan_meta.json` 缓存 start_block/head，改 config 的 start_time_utc 后必须删除该文件才会重新二分，否则沿用旧起点空跑。（来源：哈基米(BSC) 分析，2026-07-18）
- HTTP 客户端用 subprocess 调系统 curl（或 requests），绝不裸 urllib——macOS 证书链坑两次会话都踩过。（来源：OPN/SIREN(BSC) 分析，2026-07）

### 3.4 Etherscan V2（scripts/evm/fetch_etherscan.py，仅 ETH 主网）
- `https://api.etherscan.io/v2/api?chainid=1&module=account&action=tokentx|txlist|txlistinternal&apikey=KEY`；tokentx 每页 10000 条，按末行 block 续页拉全。（来源：OPN(BSC) 分析，2026-07）
- 免费 key 仅 chainid=1 可用；跨链代币的 ETH 侧全量转账、金库地址 txlist/txlistinternal（vesting 释放追踪）都走它。（来源：OPN(BSC) 分析，2026-07）

### 3.5 Multicall3 批量余额（scripts/evm/multicall_balances.py）
- eth_call 到 Multicall3（`0xca11bde05977b3631167028862be2a173976ca11`，各 EVM 链同地址）的 aggregate3，手工 ABI 编解码，≤200 地址/批；近千地址几十秒查完。（来源：SIREN(BSC) 分析，2026-07）
- 反例：逐地址 eth_call 串行查 990 地址 10 分钟命令超时（exit 143），别走。（来源：SIREN(BSC) 分析，2026-07）
- 纪律：先用 2 个地址小样本打印原始 RPC 响应验证编解码再放量；异常必须落日志绝不吞（曾因"地址文件混入余额尾巴 + 返回值动态偏移解码错 + 吞异常"三连 bug 三轮 990/990 全失败）。（来源：SIREN(BSC) 分析，2026-07）
- 地址清单文件须纯地址一行一个，任何附加字段都会污染 calldata。（来源：SIREN(BSC) 分析，2026-07）

## 4. 辅助数据面速查表

| 用途 | 端点/命令 | 要点 | 来源 |
|---|---|---|---|
| 起手定位 | `curl https://api.dexscreener.com/latest/dex/tokens/{token}` | 零注册；返回链/主池/DEX/流动性/创建时间/社媒；多池列表可分主池与尘埃池 | （来源：SIREN(BSC) 分析，2026-07） |
| 合约安全 | `curl https://api.gopluslabs.io/api/v1/token_security/56?contract_addresses={token}` | 免费无 key；LP 持有人字段可能对应尘埃池而非主池，须与工厂合约 getPair 核对 | （来源：SIREN(BSC) 分析，2026-07） |
| 貔貅模拟 | `curl 'https://api.honeypot.is/v2/IsHoneypot?address={token}&chainID=56'` | 已知误报机制：模拟器对无代码地址发起调用失败被记成 sellTax=100（V3 池代币易中）；必须 GoPlus + 链上真实卖出成交笔数 + 直接 RPC 模拟大户卖出三角验证后才可定性 | （来源：SIREN(BSC) 分析，2026-07） |
| 日 K（近期） | `api.geckoterminal.com/api/v2/networks/bsc/pools/{pool}/ohlcv/day?aggregate=1&limit=1000` | 免费但实际只返回 181 天，老币历史不完整需补源；hour/minute 端点对上线较久的池可能直接返回 0 条（day 正常时 hour 也空，实测），别当采集失败重试 | （来源：SIREN(BSC) 2026-07；哈基米(BSC) 2026-07-18） |
| 全量 K 线 | `data.binance.vision/data/futures/um/monthly/klines/{SYM}USDT/1d/{SYM}USDT-1d-YYYY-MM.zip`（另有 daily/） | 若代币上了币安永续则免费无 key 拿全史；月度包+当月每日包拼接去重，几秒完成 | （来源：SIREN(BSC) 分析，2026-07） |
| 地址标签 | WebFetch `https://bscscan.com/address/{addr}` 及 `/txs?a={addr}&ps=100` | 拿 Public Name Tag/合约创建者/首笔注资来源；大户定性必须查浏览器官方标签，不能只看链上行为猜——曾有多个"疑似庄家"地址查标签后证实为 CEX 储备/热钱包 | （来源：SIREN(BSC) 分析，2026-07） |
| top100 持仓/交易者/K线 | scripts/evm/fetch_gmgn.sh（gmgn-cli 批量） | 坑见下方列表 | （来源：OPN/SIREN(BSC) 分析，2026-07） |
| 日线价格全史 | `api.coingecko.com/api/v3/coins/{id}/market_chart?vs_currency=usd&days=365&interval=daily` | 无 key 免费；币页 WebFetch 另可拿合约地址/流通量/FDV，合约地址须双源一致才采用 | （来源：OPN(BSC) 分析，2026-07） |
| 是否上过币安 Alpha | `curl https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list` | 官方全量表（600+ 币）**含 fullyDelisted/offline 全历史存档**——可排除"曾上架后移出"；canTransfer 字段实证 Alpha 代币不可提币。**Alpha 2.0 Router Proxy 持仓性质判定的关键一步**：未上架代币的 Router 持仓=外部单方面打入（ERC20 转账无需接收方同意），是营销道具/变相冻结，不是托管买盘。上架时间的链上锚点=Router 首次收该币块（与公告新闻互证）；**Router 托管量月度差分=币安场内净买卖压力曲线（Alpha 在架币标配分析件）**，净流出月归因必查"经场内结算引擎回吐（场内净卖出）vs 直接提现"两分量占比，勿直接猜跨所搬砖 | （来源：bibi(BSC) 2026-07-12；哈基米(BSC) 2026-07-18） |
| four.meme 发射参数 | `curl https://four.meme/meme-api/v1/private/token/get/v2?address={token}` | 拿 launchTime/saleAmount（曲线售罄量）/raisedAmount（毕业募集 BNB）/创建者，与链上 mint 块时间戳互验；bundle 成本=买入 tx 实付 value + raisedAmount + 毕业注池额三方闭环 | （来源：bibi(BSC) 分析，2026-07-12） |
| 单地址全量流水独立复核 | HyperSync query 按 address 过滤 topics | 对关键黑箱地址（如托管合约）用 HyperSync 独立重扫其全部 Transfer（可跨全部代币），与扫块 CSV 互为独立通道——对账级双验证的低成本方式 | （来源：bibi(BSC) 分析，2026-07-12） |
| 千级地址现时余额 | scripts/evm/multicall_balances.py | 见 §3.5 | （来源：SIREN(BSC) 分析，2026-07） |

gmgn-cli 使用坑（fetch_gmgn.sh 已内置处理）：
- 命令用全路径 `~/.npm-global/bin/gmgn-cli`（不在 PATH；报 command not found 时别去重装）。（来源：SIREN(BSC) 分析，2026-07）
- `--raw` 输出顶层结构不一致：有的是 `{"list":[...]}`，有的是 `{"data":{"list":[...]}}`；解析统一用 `(j.get('data') or {}).get('list') or j.get('list') or []`，否则筛选会假阴性得 0 行。（来源：SIREN(BSC) 分析，2026-07）
- holders top100 稳定且信息量最大（tags、start_holding_at、history_transfer_in/out、native_transfer.from 可做 gas 来源聚类）；traders 按 profit 排序可能只回约 9 行、按 amount_percentage/sell_volume/buy_volume 排序可能 0 行、部分 --tag 组合 0 行；kline 只回 100 条只能兜底。（来源：OPN/SIREN(BSC) 分析，2026-07）
- holders/traders 接口权重 5，有 leaky-bucket 限速，批量采集脚本必须加节流间隔。（来源：OPN(BSC) 分析，2026-07）

## 5. 对账 gate（数据不闭合不进分析）

标准四件套，全过才允许跑下游分析：
1. **重建余额 vs GMGN top10 精确对表**：全量转账逐笔累加重建每地址余额，与 GMGN top10 逐个对到个位数。曾在扫块进度 97% 时 4/10 MISMATCH、补扫 remaining=0 后 10/10 全 OK——证明该 gate 能兜住数据缺口；预跑一次有提前暴露口径问题的价值，但通过判定只认补扫完成之后。（来源：OPN(BSC) 分析，2026-07）
2. **全网余额和=0**：所有地址重建余额求和应为零（mint/burn 计入），不为零即漏了转账段。（来源：SIREN(BSC) 分析，2026-07）
3. **总量恒等式 wei 级闭合**：跨链代币各链余量之和 ≈ 总供应，精确到 wei。（来源：OPN(BSC) 分析，2026-07）
4. **时间戳锚点插值抽查**：锚点表（每隔固定块距，或每 100 万块一个）bisect 线性插值出的日期，抽几笔与浏览器页面核对。（来源：OPN/SIREN(BSC) 分析，2026-07）

加分项：重建结果与第三方链上分析师独立披露的同口径数字对表，独立吻合是结论可信度的最强背书（具体数字属于当次报告，不进本手册）。（来源：SIREN(BSC) 分析，2026-07）

## 6. BSC 专属坑表

| 坑 | 识别/处理 | 来源 |
|---|---|---|
| Binance Alpha 2.0 Router 托管黑箱 | BSC meme 生态特有：单一 Alpha 托管合约可能就是 top1 holder 且份额巨大，绝不能当成"庄家地址"分析。识别=WebFetch bscscan 官方标签 + 工厂合约 getPair 分清主池/尘埃池；处理=与 CEX 热钱包一并归入"不可穿透黑箱"，报告显式给黑箱占比与单一实体份额上限，措辞一律带"链上可证范围内"限定 | （来源：SIREN(BSC) 分析，2026-07） |
| 新 key 不探测就承诺方案 | 任何新 key 到手先做 1 分钟能力探测：eth_blockNumber + 一次真实 getLogs（或一页 transfers），确认块范围上限/限速/链覆盖后再写进计划。反例：dRPC 免费 key 探测前就让用户注册，实测基本不可用，白费一次注册 | （来源：SIREN(BSC) 分析，2026-07） |
| 用户网络可达性 | 让用户注册任何站点前，先在用户机器上 `curl -s -o /dev/null -w '%{http_code}' {url}` 预检。实测（用户中国网络）：drpc/alchemy/getblock/bitquery 返回 200，app.envio.dev/nodereal 返回 000，dune 403；且"控制台打不开 ≠ API 端点不可用"（bsc.hypersync.xyz 直连通） | （来源：SIREN(BSC) 分析，2026-07） |
| 数据量按市值臆测 | 曾按市值预估几十万条、实际 2150 万条（代币被高频机器人生态盘踞），耗时预估连环跳票：先拉发射首月抽样外推总量，向用户报保守上限；"转账笔数/市值异常比"本身可写进报告当信号 | （来源：SIREN(BSC) 分析，2026-07） |
| dataseed 只能做轻查询 | eth_blockNumber / eth_getBlockByNumber / eth_call / eth_getCode（latest 状态）正常，可做时间戳锚点与工厂 getPair；getLogs 与历史状态一律被拒 | （来源：OPN/SIREN(BSC) 分析，2026-07） |
| 部署块 getCode 二分失效 | 免费节点拒历史 eth_getCode（archive 请求），二分会找错块 → 改用块头时间戳二分定起始块（非 archive 请求） | （来源：OPN/SIREN(BSC) 分析，2026-07） |
| 通道切换不清观察哨 | 废弃一条数据通道时，同步 TaskStop 与之绑定的 until-grep 观察哨/循环任务，否则空挂十几小时、用户来质问"任务还活着吗" | （来源：SIREN(BSC) 分析，2026-07） |
| zsh 裸 glob 杀命令链 | 后台命令 `rm -f part_*.csv && python3 ...` 在 glob 无匹配时报 "no matches found" 并中断整条链，扫块脚本被连带杀掉 → 用 `rm -f ... 2>/dev/null \|\| true` 或拆成两条命令 | （来源：OPN(BSC) 分析，2026-07） |
| scan_transfers 毒段死循环 | 主扫 worker 对失败段无限放回重试：**段数长期不动 + CSV 行数停涨 = 毒段卡死**（发射高峰段数据量超节点上限）。处置：杀掉 scan 进程直接跑 fill 模式（1000 块子段减半递归）；已完成数据在磁盘不丢，fill 后按 done.json 续 | （来源：bibi(BSC) 分析，2026-07-12） |
| 锚点插值发射窗口系统偏差 | 每 10 万块锚点线性插值在发射窗口可有 +100s 级恒定偏差（BSC 出块速率变化）。分钟 K 配价前必须 RPC 实查 2-3 个关键块定量偏差，发射窗口改用"精确锚定块 + 实测出块间隔外推"（如 ts=mint_ts+(blk-mint_blk)*0.45）；小时/日级分析不受影响 | （来源：bibi(BSC) 分析，2026-07-12） |
| GoPlus is_contract 误报 EIP-7702 | 委托型 EOA（7702）被 GoPlus 标 is_contract=1（曾致 top10 中 4 个被误当合约）。甄别：bscscan 地址页看"委托对象"字段，或 eth_getCode 前缀 0xef0100 | （来源：bibi(BSC) 分析，2026-07-12） |
| GMGN 卖出榜 EOA 口径新形态 | 卖出榜"纯转入零买入、卖出数十万美元"地址可能在 Transfer 事件里**完全不出现**（智能钱包/路由的操作者 EOA），不能当"内部钱包变现"指认；需 tx 层核实 msg.sender 与事件主体的关系 | （来源：bibi(BSC) 分析，2026-07-12） |
| WebFetch 读代理合约页误报合约名 | bscscan 代理合约页经 WebFetch 提取可能拿到错误合约名（曾把某实现合约误读成别的标签名）。代理合约身份认定必须：EIP-1967 implementation slot 读实现地址 + 字节码 PUSH4 选择器提取（openchain 签名库解析）——WebFetch 文本不作为代理合约功能的最终证据 | （来源：bibi(BSC) 分析，2026-07-12） |
| 币安 Web3 钱包 DEX Router 串假实体 | `0xb300000b72deaeb607a12d5f54773d1c19c7028d`（vanity 前缀）是币安 Web3 钱包 app 的 DEX 交易入口：数十个用户的"首笔代币来源"都是它、与用户双向大额往来——作"共同首币来源/直转"边会把互不相识的币安钱包用户串成数百址假实体（实测 421 址大簇根因）。**E3 类共源边的源地址必须先过标签库**；它与 LI.FI Diamond、高频对倒 bot 代理同为漏网"半枢纽"（度数几十、不到出度>200 剔除线） | （来源：哈基米(BSC) 分析，2026-07-18） |
| Uniswap V4 PoolManager 漏出池子清单 | V4 是单例合约（bsc: `0x28e2ea090877bf75740558f6bfb36a5ffee9e9df`），不在常规 pair 发现流程（factory getPair/Dexscreener pairs）内——漏掉会错过其上的 bot 刷量：实测四个脉冲日占全网转账笔数 49-88%、毛量 40-76%（单日毛量 4.7 亿枚 vs 池深仅 24.7 万枚），且与拉升起点精准同步，"放量上涨"表观数据严重失真。**量能真实性检查加"V4 毛量占比"维度**；四日脉冲定量法=占笔数/占毛量/池深对照/与拉升同步性 | （来源：哈基米(BSC) 分析，2026-07-18） |
| DexScreener dexId "uniswap" 无版本标注可能是 V3 池 | Swap topic：V3=`0xc42079f9…`、V2=`0xd78ad95f…`；dexId 只写 "uniswap" 不标版本时，先按 log topic 判池版本再解析，按错版本解析买卖归因全错 | （来源：外部 bibi(BSC) 考古，2026-07） |
| four.meme 内盘量化 / 克隆快判 | 内盘额度恰 8 亿/80%，dev-buy 同 tx 按 bonding curve 买断内盘凑满即秒毕业、创世后约 8 块（~4s）TokenManager2 注 20% 入 Pancake V2；"创世同秒单钱包拿走 ~80%"=dev buy。`7777` 后缀=另一发射台 CREATE2（与 4444 并列，平台特征非指纹）。meme-api 全路径已 404，正身改看创世 tx HTML 是否触及 TokenManager2/部署器（创建者从合约页 Contract Creator 取，href 单引号，正则 `["']?`） | （来源：外部 TCC/bibi(BSC) 考古，2026-07） |
| four.meme 连环盘 / 致敬币指纹 | **连环盘**：同一创建者短时（十几小时）连发 ≥5 个币、每次创世秒买断 ~80% 并在 1 分钟内把大部分转给**同一收币钱包**——TOP1 大户的 tokentxns 里混着大量其他 4444 币即此线索。**致敬币变体**：收币钱包可能是被致敬 KOL 本人（印证行为=向官方慈善多签捐 1% + 向代币合约自转等效销毁），其约束只有公开声誉（软约束），报告按"收币实体"陈述、身份措辞按证据分级。另：GT 日线只留 ~180 天导致老币毕业价缺失时，可由 four.meme 曲线参数（saleAmount/raisedAmount）反解毕业价 | （来源：外部 TCC/人生K线(BSC) 考古，2026-07） |

## 7. 零门槛免注册通道（外部会话考古 2026-07 补充）

> 本节来自另一台电脑对 CZ/TCC/人生K线/bibi(BSC)、ASTEROID/OPN(ETH) 的独立分析实战。与 §1–§3 的本机通道（bloXroute/HyperSync/Alchemy）**互补**：这套通道**完全免注册免 key**，适合"手头无任何 key、临时快速起手分析新盘"的冷启动；代价是历史保留窗口短或需网页抓取。用前仍按 §6 做 1 分钟能力探测（政策季度级变化）。

### 7.1 BSC：`0.48.club` 是唯一可用的免费历史 getLogs 端点
- 免 key 免注册，**实测唯一能服务历史 eth_getLogs 的免费端点**，5000 块/请求（~1000–2500 logs/s），支持宽 topic-OR（40 个 padded 地址塞一个 topic 数组 OK）；也支持 eth_call / eth_getCode / eth_getTransactionReceipt。**不支持 JSON-RPC batch**（发单请求，并发 ~8 可），Python requests 偶发 SSL EOF 重试即可。
- **致命保留限制**：只保留最近 **~1.14M 块 ≈ 6 天**（二分实测边界，更早 getBlockByNumber 返 null、getLogs 报错）——**只够 6 天内新盘，几个月前历史无用**。且 eth_call/eth_getCode 只在 `"latest"` 有效，任何历史块参数返 `-32000 not supported`（state 不归档，连 30 分钟前都查不到）。保留窗口探测通用法（适用任何新免费端点）：probe 当前块 −10万/−100万/−500万 的 getBlockByNumber/getLogs，二分收敛，几分钟测清历史窗口边界。
- 推论：0.48.club 上 getCode/eth_call **不能**二分定位老合约创建块（state 非归档）→ 改用 BscScan 合约页 "Contract Creator … at txn" 直接拿创建 tx→回执→blockNumber。

### 7.2 BSC：BscScan 网页直抓（免 key 深度历史，反爬已摸透）
服务端渲染、**普通 Chrome UA 的 fetch 即可过 Cloudflare**（无需 firecrawl/浏览器），是"无 key 时逐个大户深度溯源"的主通道：
- 单地址转账史：`bscscan.com/tokentxns?a=<addr>&p=<N>&ps=100`（硬上限 ~10 页×100 行/地址；超活跃 bot 会被截断——**别据截断数据推"钱包年龄/建仓时间"**，翻不完必须在报告标注"建仓可能更早"）
- 持有人榜：`bscscan.com/token/generic-tokenholders2?m=normal&a=<token>&p=<N>&ps=100`（ps 被强制 50、最多 20 页=前 1000 名，meme 币通常覆盖 99%+ 供应；行内自带公共标签如 MEXC/Null）
- 地址概览：`bscscan.com/address/<addr>` 拿 Public Name Tag / Contract Creator / "Funded By"（href 用单引号，正则要 `["']?` 容单双引号）
- **并发 >1 必触发限流返回空页**（3 线程实测 16/43 失败）→ **必须单线程 0.6–1s 间隔**；失败地址单线程重试即 100% 成功。
- 行级解析坑（血泪）：①时间戳在 `class='showLocalDate'` 的 span **文本**里（不是 data-timestamp 属性）；②方向靠 `>IN</span>`/`>OUT</span>` badge（tokentxns 行不把自身地址渲染成链接，只有对手方在 `data-highlight-target`——只存对手方会丢方向）；③数量在 `td_showAmount` 的 `data-bs-title`（全精度｜$价）；④**持有人榜百分比列常年显示 0.0000%（BscScan 自身坏的），持仓数量要取百分比单元格的前一格**——"取行内第一个大数"的偷懒解析会把排名数字（第 101 名起 >100）当持仓。
- 已死端点：`token/generic-tokentxns2`（按币种过滤单地址史）返回 "unexpected error"；`advanced-filter` 页被 Cloudflare 403。替代=全局 tokentxns 抓回后按行内 `/token/<ca>` 链接过滤目标币。
- **工程模式——磁盘缓存抓取层**：批量直抓统一封装为"单线程限速 + 磁盘缓存（`sha1(url)` 作缓存文件名，命中即免请求）"——反复抓同址零成本、中断重跑断点友好，是 BscScan 串行慢速纪律下的效率补偿（外部 bibi 会话 fetchlib.py 模式，2026-07）。

### 7.3 ETH 主网：`rpc.mevblocker.io` 全史 getLogs（免 key）
- **支持全区块段 eth_getLogs**（不像 BSC 各免费端点限几十块），按 Transfer topic 的 from/to 过滤，每地址 2 次调用即拿全史台账；偶发 429 退避。这是 ETH 侧**无 key 全史通道**（§1 的 ETH 侧只有 Etherscan V2 免费 key 路线，此为零门槛补充）。
- **坑：负载均衡后端偶发静默返回不完整结果**——必须"重建台账余额 vs 链上 balanceOf(latest) 逐钱包对账"校验，缺口用 `ethereum-rpc.publicnode.com` 50k 块分块补抓。
- **archive eth_call 可用（mevblocker 第二关键能力）**：支持对历史块直查 `balanceOf`——任意时点余额曲线可直接重建，不必靠日志累加。**缓存台账截断坑**：台账文件的单腿（如 out 腿）可能被静默截断（外部 ASTEROID 实测 8000/13846 行），余额曲线必须用 archive balanceOf 按时间点独立重建交叉验证，不能只信台账累加。
- **老币/百万级转账的免 key 采集拓扑**：全量拉取不现实时，改对 top ~200 持有人 + 关键地址**逐地址定向拉台账**（from/to 各一次 getLogs），全部台账逐一 balanceOf 对账（unreconciled=0 才放行）；代价=非 top 持有人行为不可见，报告声明口径（外部 ASTEROID：134 万笔转账标的，201 个台账全对平）。
- 大窗口 getLogs 分片纪律：块范围自适应二分细分片，<250 块仍失败才放弃该段。
- 首笔注资溯源：`eth.blockscout.com/api?module=account&action=txlist|txlistinternal&sort=asc&offset=1` 一次调用拿钱包首笔注资交易（免 key，资金溯源关键）。
- **`eth.blockscout.com/api/v2` 与 Robinhood 链 Blockscout 同栈同端点**（holders 分页 / token counters / smart-contracts 合约名与 implementation（识别 proxy/EIP-7702 delegate）/ internal-transactions 全套可用，端点细节见 data-pipeline-robinhood.md）——ETH 侧持有人榜、地址画像、合约识别的免 key 主通道（外部 ASTEROID 考古，2026-07）。
- 其他 ETH 免费端点：`ethereum-rpc.publicnode.com` 近期块 getLogs 可 2 万块/请求（老块要 key）——⚠️ 块限两说：外部 ASTEROID 实测为 5 万块/次需分片，政策会变，用前 1 分钟实测取当前值；`eth.drpc.org` archive+10000 块 free 但 CU 频控紧。

### 7.4 省请求取证技巧（外部 OPN/ASTEROID 实战）
- **mint 常在合约创建那笔 tx（constructor 铸造）**：`eth_getCode` 二分定位创建块 → `eth_getBlockReceipts` 一次拿整块回执 → 本地过滤 Transfer(from=0x0)，绕开 getLogs 范围限制。⚠️ **与 §3.3/§6 冲突**：本机 bloXroute/免费节点实测"拒历史 eth_getCode（archive 请求）、二分会找错块"；外部实测"bsc-dataseed 的 eth_getCode 是 archive、可查任意历史状态"。**两说并存**——用前对目标节点实测一次历史 getCode 是否被拒：被拒→按块头时间戳二分（§3.3）；不被拒→getCode 二分更省请求。
- **锁仓盘往往集中在另一条链**（外部 OPN：BSC 只放流通盘，8 亿 vesting 全在 ETH、转账极稀疏一次 getLogs 拿完）——全量扫描前先判"要不要扫这条链"，别对着流通链扫全量却漏了锁仓链（呼应 analysis-playbook §1 多口径）。
- `topics:[Transfer,[from1,from2,…]]`（topic1 传数组=OR）一次查多个金库桶流出；查"金库动没动"最省的是 `balanceOf(latest)` 对比初始分配额，有变动再回头扫 log 找 tx 证据。

### 7.5 BSC 老币（超出 48club 6 天窗口）免 key 三段拼接采集拓扑

适用：老币 + 手头无任何 key 的冷启动（外部 人生K线(BSC) 实战 47 分钟交付验证）。三段互补拼接：

1. **近 6 天全量 getLogs**（48club，§7.1）→ 当前筹码结构与本轮爆量归因；
2. **BscScan 网页直抓深历史**（§7.2）→ 创世取证（token 页 Contract Creator 段）+ 前排大户 `tokentxns?a=` 建仓史（≤10页×100 上限，翻不完标注"建仓可能更早"）+ generic-tokenholders2 持有人榜；
3. **GT 日线价格轴**（只留 ~180 天，§4）+ 关键放量日与链下事件（上所/Alpha 公告等）对齐。

- **输出形态随之改变**（全史演变曲线在此拓扑下不可得，报告口径必须声明）：**结构快照**（当前各阵营占比）+ **6 天净变动表** + **大户建仓时间线**。
- **fresh/old 大户分层**：用 6 天窗口把前排大户分为"本窗口进场新大户 vs 更早老持仓"两层，直答"这波爆量谁在买"。
- 图表叙事技巧：大户建仓时间线图上"创世期区域完全空白"= 没有任何创世钱包还留在前排的可视化证明（老庄已清仓的直观证法）。

（本节来源：外部电脑 BSC/ETH 分析考古，2026-07；原始会话见 `windows虚拟机cc会话记录/`）

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

通用环境坑（macOS SSL 证书、reportlab 中文字体、前台 sleep 被 Block 等）不在本文重复，见 skill 其他参考文档与 memory（mac-python-pdf-environment.md、onchain-data-accounts.md）。
