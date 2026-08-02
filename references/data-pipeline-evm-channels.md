# EVM 链数据管道 · 采集通道与决策树（data-pipeline-evm 分册 1/3）

> 母文档：`data-pipeline-evm.md`（薄路由索引页，文档级引言与时效纪律见索引页）。本册覆盖 **§1 全量转账通道决策树 / §2 死亡名单 / §3 各通道操作细节 / §6 BSC 专属坑表 / §7 零门槛免注册通道**；§4/§8/§9/§10 见 `data-pipeline-evm-sources.md`，§5/§11/§12 见 `data-pipeline-evm-recon.md`。正文 §N 交叉引用一律为母文档节号（本册未含的按索引页对照表跳册）。

## 1. 全量转账通道决策树（BSC）

先估数据量（预估纪律见 §6），再选通道：

```
预估 Transfer 总条数？（先抽样发射首月外推，报保守上限）
├─ 任何量级【v3.11.2 起默认,Starter 付费 key 在役】
│     → ① HyperSync 官方客户端 v2【首选】（scripts/evm/fetch_hypersync_v2.py，
│          Rust 自动并发+Parquet 直写，实测 ~1 万条/s = 手写轮询 18 倍）
│       ② v1 手写轮询【兜底】（fetch_hypersync.py，无 pip 环境/逐字段调试用）
├─ < 300 万条且 ≤60 天新盘（手头无任何 key 的冷启动）→ bloXroute getLogs 扫块（scan_transfers.py）
├─ HyperSync 平台级故障 / 数仓切源准入对照 → SQD Portal 薄采集器（fetch_sqd_evm.py，免 key，~280 条/s）
├─ HyperSync 结果可疑 / 对账 gate 挂了后的独立复核【仅 ETH 主网】→ BigQuery goog 官方公共数据集
│     （fetch_bigquery.py,定向日期查询 ~12GiB/次,免费 1TiB/月;定位=备用+复核,不用于常态采集,详见 §11）
├─ 跨链代币的 ETH 主网侧补充 → Etherscan V2 免费 key（仅 chainid=1，fetch_etherscan.py）
└─ 任何情况下都别碰 ──→ §2 死亡名单端点（禁止重探）

落盘与合并纪律（v3.11.2 起）：多源产物一律经 transfers_lib.py merge 合并——重叠块区
集合级对账，不等即 exit(3) fail-closed（PING 案 uniqueId 双计 5485 负余额的制度化防线）；
标准 8 列含 block_hash，去重键 (block_hash,tx,log_index) 防链重组。
channels.json 的 path 字段语义（2026-07-25 SPX6900 实测坑）：hypersync_v2 通道的 path
指向 **v2 采集根目录**（如 data/v2，内含分段 parquet 全集），**不是单次 run 子目录**——
分段采集/断点续拉的币该目录下有多段产物，把某段 run 目录填进 path 会静默漏段；
续拉与重放引用 channels.json 时按根目录读全段。
```

批量预采集（v3.16.0，/collect-data 命令）：多币串行队列 `scripts/collect/collect_queue.py`
——EVM 五链(bsc/eth/base/arbitrum/robinhood)走 fetch_hypersync_v2（部署块自动探测进全局缓存）、
solana 走 fetch_sqd_transfers_v2；manifest 原子记账、残缺 run 改名 partial_ 隔离不删除、
单项失败不阻塞；HyperSync key 读 `~/.config/hypersync/token`。夜间队列先行，分析会话只付增量。

分叉依据：bloXroute 8 并发扫 249.6 万行约 80 分钟，量级再大耗时不可控且免注册通道无 SLA；HyperSync 免费层拉 1568 万条约 5.2 小时（OPN/SIREN，07）；**Starter 付费档（$70/月,100rpm+overage 5x=500rpm）+官方客户端后，同类量级压至半小时内**（v3.11.2 POC，2026-07-21，详见下表）。

配套缓存（transfers_lib.py，存 `~/.cache/chip-analysis/`，跨币跨会话复用）：
- **部署块缓存** `get_deploy_block(chain, token, fetch_fn)`——每币首次定位后永存，免每次从 0 扫空段；
- **时间戳锚点库** `add_anchors(chain, pairs)` / `estimate_ts`——按链累积复用，v2 产物的 blocks.parquet (number,timestamp) 直接喂入，新币插值免重复采锚点（⚠发射窗口精确配价仍禁用插值，恒定偏差坑见 §6）。

**增量拉取（研报更新/补尾场景）**：v2 对增量天然友好——同一 run 根目录下新起 run（from_block=上次 done.json 的 next_block）即可，付费档实测 7 万块 2.3 万条仅 4s；**补丁段重叠核验法**：对怀疑有洞的区间补拉一段落盘独立 patch 目录，按 (tx,log_index) 键与主数据对比，零差即证该段完整、有差即用 patch 覆盖（QUQ 完整版增量，07-22）。

| 通道 | 注册要求 | 限速实测 | 吞吐实测 | 断点续传 | 脚本 | 来源 |
|---|---|---|---|---|---|---|
| **HyperSync 官方客户端 v2（Starter 付费档,现役首选）** | Starter $70/月 | 官方客户端并发 | **10,080 条/s**（CAKE 实测） | done manifest v2 绑定 token/url/capture bounds/query/client；不一致或 start>=to 非零退出 | fetch_hypersync_v2.py | （2026-08-02 加固） |
| envio HyperSync v1 手写轮询（兜底） | 同上 key 通用 | 免费层:0.5s 间隔基本无 429（2026-07-18 收紧后实测）;**Starter 付费档:0.12s 间隔 429=0**,但单进程吞吐仅 552-792 条/s（RTT 主导,ETH RTT~0.2s/BSC~0.6s）——付费买到的是高峰稳定性,大标的提速必须换 v2 | 免费层 ~1000-1300 logs/2s,1568 万条约 5.2h;付费单进程 ETH 792 条/s、BSC 552 条/s | from_block 起点 + 增量写 CSV（v3.11.2 起新文件 8 列含 block_hash,老 7 列续拉自动兼容） | fetch_hypersync.py | （SIREN 07；哈基米 429 实测 07-18；v3.11.2 付费实测 07-21） |
| SQD Portal 薄采集器（故障预案+对照源） | 免 key 免注册（portal.sqd.dev 公共端点;注册 gateway key 免费可选更稳） | 公共限流 20 请求/10s,sleep 0.5 保守;无自助付费档（官网 pricing coming soon,2026-07-21 核实） | ~280 条/s（CAKE 21,857 行/79s）——平时不跑,HyperSync 平台级故障或数仓切源准入对照时才上;**对账关卡（余额对账/时间抽查）的代表日双源对照亦用它**（独立索引商,BANANAS31(BSC) 四代表日 67,731 行 (block,tx,li,from,to,value) 六元组与 HyperSync 零差集全等,2026-07-22） | CSV 末行块+1 | fetch_sqd_evm.py | （v3.11.2,2026-07-21） |
| BigQuery goog 官方公共数据集（备用+复核,**仅 ETH**） | Google 账号 OAuth 一次(凭据缓存后免弹窗)+GCP sandbox 项目(免绑卡,见 api-keys.md 第 17 节「Google Cloud / BigQuery」) | 免费 1 TiB/月查询量;熔断线 config max_scan_gib(默认 200GiB) | 服务端过滤只回传命中行,13 万行 ~1 分钟;定向日期查询 ~12GiB/次≈月额度可复核 85 次 | 无需(按日期范围幂等重查) | fetch_bigquery.py | （v3.12.1 准入实证,2026-07-21） |
| Alchemy getAssetTransfers | 免费 key（dashboard.alchemy.com 国内直连） | 平台级 429 全局限流，高峰期可整夜不可用 | ~46 万条/10 分钟，1000 条/页 | 读 CSV 末行区块置 fromBlock（勿依赖 pageKey） | fetch_alchemy.py | （SIREN，07） |
| bloXroute getLogs | 免注册 | ⚠**并发承受力已变**（2026-07-19 SIREN 实测）：8 并发 curl 线程池整体挂死零产出、requests 3 线程 0.5s 间隔稳定；历史窗口比 07-18 更宽（下界块 100.1M~101.5M ≈55-60 天，二分探测）——**窗口是动态的，用前必二分**。降级为"近期段快扫" | requests 3 线程 万块段 ~50 段/4 分钟（SIREN 396 万条约 30 分钟）；旧 8 并发数字已不可复现 | done-segments 清单 + 失败段补扫 | scan_transfers.py（curl 线程池版本机挂死，改用 requests.Session） | （OPN 07；哈基米 窗口实测 07-18；SIREN 并发/窗口实测 07-19） |
| Etherscan V2（仅 ETH 主网） | 用户免费 key | 免费层限速未成瓶颈 | tokentx 每页 10000 条，7 万余行顺利拉完 | 按返回末行 block 续页 | fetch_etherscan.py | （OPN，07） |
| envio HyperSync **ETH 主网**（eth.hypersync.xyz） | 同上免费 token | 0.25s 间隔全程仅 11 次 429、全部退避成功 | 139.9 万条 33 分钟单进程拉完（~700 条/s 均速） | 同 BSC 版（fetch_hypersync 断点续传版） | fetch_hypersync.py | （ASTEROID，07-18） |

## 2. 死亡名单（实测不可用，3 个月内禁止重探）

免费匿名的 BSC 历史 getLogs 通道整体已死，唯一例外是 bloXroute。（OPN/SIREN，07）

> 时效纪律（v1.3）：本表实测于 2026-07。免费层政策季度级变化——任何条目距实测超过 3 个月后若确有需要，允许花 1 分钟小请求重探一次，复活/仍死都把本表日期更新；3 个月内维持禁令（重探是历史上最大的轮次浪费源之一）。否定性结论的入库纪律见 retrospective.md 红线 4。

| 端点/通道 | 实测症状 | 来源 |
|---|---|---|
| bsc-dataseed 系（bnbchain 官方） | getLogs 连 span=100 都报 -32005 limit exceeded；仅可做轻查询（见 §6） | （OPN/SIREN，07） |
| publicnode | 老区块要求 archive token | （OPN/SIREN，07） |
| dRPC 匿名（bsc.drpc.org） | 限 10000 块/次且 "Too many request" 频发，全链扫必卡死在重试 | （OPN/SIREN，07） |
| dRPC 注册免费 key（lb.drpc.org） | 持续 429；>10000 块不支持；network=bsc-archive / bsc-full 是非法名——注册了也没用 | （SIREN，07） |
| Alchemy eth_getLogs 免费层 | 限 10 个区块范围；但同一 key 换 alchemy_getAssetTransfers 方法即可用，别因此弃掉 key | （SIREN，07） |
| Etherscan 免费 key + chainid=56 | "Free API access is not supported for this chain"，两次会话都把它当过首选然后报废 | （OPN/SIREN，07） |
| api.bscscan.com v1 | 已 deprecated | （OPN，07） |
| 1rpc.io | getLogs 限 50 块 | （OPN/SIREN，07） |
| blastapi | getLogs 限 10 块 | （OPN/SIREN，07） |
| meowrpc | 不支持 getLogs | （OPN，07） |
| llamarpc / blockpi | 返回异常 | （OPN，07） |
| zan.top | 要注册 | （OPN，07） |
| 48.club | 限 5000 块且 "header not found" 不稳定 ⚠️**并非全废，见 §7.1**：外部会话实测它是**唯一可用的免费历史 getLogs 端点**，"不稳定"真相=只保留最近 ~6 天块，用于 6 天内新盘可用 | （OPN，07；外部 CZ/TCC 考古修正，07） |
| nodies / ankr / merkle / omniatech | 限范围/限量/限流，均无法扫全史 | （OPN/SIREN，07） |
| Routescan | 不支持 BSC（`chain not supported`） | （外部 CZ 考古，07） |
| `api-legacy.bubblemaps.io` | 返回 400——Bubblemaps legacy API 已死（BSC/ETH 两场会话独立验证） | （外部 CZ/ASTEROID 考古，07） |
| CryptoCompare min-api histoday | 已并入 CoinDesk、强制要求 API key——免 key 历史日K时代结束；TGE 老币全史价格改走 Gate 现货日K（§4） | （SQD，07-20） |

## 3. 各通道操作细节

### 3.1 envio HyperSync（scripts/evm/fetch_hypersync.py）
- POST `https://bsc.hypersync.xyz/query`；header `Authorization: Bearer {TOKEN}`；body 含 `from_block`、`logs: [{address, topics}]`、`field_selection`。（SIREN，07）
- 匿名（无 token）已不可用；token 让用户到 app.envio.dev 注册——控制台在用户（中国）网络打不开需 VPN，但 API 端点直连可用，"控制台打不开 ≠ API 不可用"。（SIREN，07）
- archive_height 到最新块，全史无缺口；换 token 地址与链子域名即可用于其他 HyperSync 支持链。（SIREN，07）
- token 从 `~/.config/hypersync/token` 自动读取（fetch_hypersync 与 /collect-data 内置）；换 key 时该文件与 `~/.claude/api-keys.md` §1 两处同步。
- **transactions 端点做 BNB 注资溯源**：body `{"transactions":[{"to":[addr]}],"field_selection":{"transaction":["block_number","from","to","value"]}}`（value 为 hex）——单址全链入金一次查询 ~2.3s 到 tip，比逐块扫快几个量级；⚠25 址×全链批量会 10 分钟超时，可用姿势=关键地址单址逐查 / 发射窗小块段批量（from/to_block 圈定）。（哈基米，07-18）
- 分段多进程姿势：复制脚本改 OUT 与 to_block 边界（`if nxt >= BOUND: break`）、sleep 提至 0.5s，各进程独立 CSV 事后按 (tx,log_index) 去重合并；改 config 后重启前删本地缓存的段清单文件。（哈基米，07-18）
- **多会话共享 key 限速冲突**：并行分析会话同打一个 HyperSync key/端点会互相触发 429（SQD 案与另一标的采集会话撞车实测）——开工前 `ps aux | grep fetch_hypersync` 查有无在跑进程；撞车时不必停工，调低单会话吞吐预期、靠 429 退避共存（SQD 案 83.2 万条 56 分钟、429×20 次全部自愈）。（SQD，07-20）**限流是 key 级共享、不是端点独立**——同 key 打不同链子域（eth+arbitrum）并发同样互抢限额：LPT 案 eth+arbitrum 三进程并发时 arbitrum 端点 429 密集，串行后恢复；多链标的的分链采集按链串行或错峰，别指望换端点绕开限额。（LPT，07-21）
- **分段采集**：`staged_capture.sh` 只在 done manifest 的 token/url/from/to/query 全字段一致时跳段；残段移入 `outdir/quarantine/` 保留诊断现场，不再递归删除。失败 retry-once 后仍失败即停。

- **★稀疏事件（单池单 topic）别用 HyperSync 全链扫，改「已有 Transfer 反查 tx → 打回执」**：HyperSync 按"扫过的块量"分批返回，对稀疏匹配（如某一个池的 `Mint` 事件）实测每次只推进 **~5,400 块 / 12 秒**——扫 1.1 亿块要几十小时，且中途看不出异常（进程活着、只是慢）。**正解**：从已落盘的全量 Transfer 里筛出"该合约 ↔ 任意地址、金额 ≥ 门槛"的交易去重得 tx 列表，再并发 `eth_getTransactionReceipt` 逐个解析（KOGE 案 82 个交易几十秒拿到全部 81 次 LP 操作，对比 HyperSync 全链扫的几十小时）。**反过来**：块区间已知的小范围精确查询（如追某个 tokenId 的 ERC721 Transfer）用 HyperSync **一次返回**，比公共 RPC 的 `eth_getLogs` 省事——后者在 BSC 公共节点超 5,000 块即 `-32005 limit exceeded`。选型口诀：**大范围稀疏→反查回执；小范围精确→HyperSync**。（KOGE 第二轮追加取证，07-25）
- **v2 响应里的 log 字段是 `topic0/topic1/topic2/topic3` 分列，不是 `topics` 数组**：按 `l['topics'][0]` 取会直接 `KeyError`（与 `eth_getLogs` 的 RPC 返回结构不同，混用两套代码时高发）；`field_selection.log` 里也要逐个列名申请。同理 `transaction`/`block` 的字段名各自独立申请。（KOGE 第二轮追加取证，07-25）

- **v2 resume 语义**：只消费同 `capture_from` 且身份完全一致的 manifests；边界必须满足 `capture_from<=from<to=next<=本次to`。跨标的、跨端点、坏边界、`start>=to` 全部 fail-closed，禁止“空完成”。

### 3.2 Alchemy getAssetTransfers（scripts/evm/fetch_alchemy.py）
- POST `https://bnb-mainnet.g.alchemy.com/v2/{KEY}`，method=`alchemy_getAssetTransfers`，params 含 `contractAddresses`、`category:["erc20"]`、`maxCount:"0x3e8"`、`pageKey` 分页；返回自带时间戳。（SIREN，07）
- pageKey 有有效期，长任务中断后必过期：断点续拉一律读 CSV 末行区块号置 fromBlock 重开游标，容忍少量重复、下游按 tx hash 去重。（SIREN，07）
- 会遇平台级 429（"global traffic"，与自身配额无关、恢复时间不可控），曾整夜零进展：脚本内置指数退避（最长 20 分钟）+ 外层 while 冷却重启；卡点超 1-2 小时必须并行准备第二通道并用 AskUserQuestion 摆路径，绝不单通道死等。（SIREN，07）

### 3.3 bloXroute getLogs 扫块（scripts/evm/scan_transfers.py）
- POST `https://bsc.rpc.blxrbdn.com`，eth_getLogs 按 Transfer topic 分段扫：10000 块/段、8 并发 worker、~2s/请求。（OPN，07）
- 断点续传：done-segments 清单跳过已完成段；多线程必留失败段（某次 3392 段中 92 段失败），扫完自动列 remaining 并补扫，remaining=0 才算采集完成。（OPN，07）
- 起始块定位：勿用 eth_getCode 二分找部署块（免费节点历史状态请求被拒，会找错块导致空扫秒退）；改按"块时间戳 >= 已知安全起始日期"二分，起始日期用 GMGN start_holding_at 或跨链铸造日锚定，多扫无害。（OPN/SIREN，07）
- 同脚本顺带采时间戳锚点：每隔固定块距 eth_getBlockByNumber 取块头时间戳（数百个锚点几分钟采完），分析期 bisect 线性插值，省数千次逐块 RPC。（OPN，07）
- **起点缓存坑**：`<chain>_scan_meta.json` 缓存 start_block/head，改 config 的 start_time_utc 后必须删除该文件才会重新二分，否则沿用旧起点空跑。（哈基米，07-18）
- HTTP 客户端用 subprocess 调系统 curl（或 requests），绝不裸 urllib——macOS 证书链坑两次会话都踩过。（OPN/SIREN，07）

### 3.4 Etherscan V2（scripts/evm/fetch_etherscan.py，仅 ETH 主网）
- `https://api.etherscan.io/v2/api?chainid=1&module=account&action=tokentx|txlist|txlistinternal&apikey=KEY`；tokentx 每页 10000 条，按末行 block 续页拉全。（OPN，07）
- 免费 key 仅 chainid=1 可用；跨链代币的 ETH 侧全量转账、金库地址 txlist/txlistinternal（vesting 释放追踪）都走它。（OPN，07）

### 3.5 Multicall3 批量余额（scripts/evm/multicall_balances.py）
- eth_call 到 Multicall3（`0xca11bde05977b3631167028862be2a173976ca11`，各 EVM 链同地址）的 aggregate3，手工 ABI 编解码，≤200 地址/批；近千地址几十秒查完。（SIREN，07）
- 反例：逐地址 eth_call 串行查 990 地址 10 分钟命令超时（exit 143），别走。（SIREN，07）
- 纪律：先用 2 个地址小样本打印原始 RPC 响应验证编解码再放量；异常必须落日志绝不吞（曾因"地址文件混入余额尾巴 + 返回值动态偏移解码错 + 吞异常"三连 bug 三轮 990/990 全失败）。（SIREN，07）
- 地址清单文件须纯地址一行一个，任何附加字段都会污染 calldata。（SIREN，07）

### 3.6 记账模型 gate 的通道实测（accounting_gate.py，3.19）

- **BSC dataseed**：eth_call 历史 state 窗口 **~128 块且节点池深浅抖动**（150 块探测过、边缘偶发 missing trie node——gate 的 rebase 两时点已收缩到 64 块保命中）；支持 **eth_simulateV1**（模拟转账读实收的兜底路）；getLogs 拒(-32005)。bsc/eth publicnode 全 archive 墙（128 块内也拒）；dRPC 免费层限速凶只配兜底。
- **Alchemy ETH 免费层：eth_call 全历史 archive**（100 万块前实测通）→ ETH 侧 gate 事件窗口自动放大到 1 万块、rebase 窗口 7200 块，检测强度远超 BSC；但 getLogs 限 10 块——事件一律走 HyperSync。`.g.alchemy.com` 走 clash 代理（脚本内置）。
- **fee-on-transfer 双路互补是实测教训**：BabyDoge 型"只对 DEX pair 收税"钱包互转免税——**模拟法测不出，只有真实事件差值（覆盖过池路径）能抓**；反之低活跃币近程无事件时靠 eth_simulateV1 兜底。事件差值用"单侧干净样本"制（地址在该块仅现身一次），给 bot 刷量币（一笔多跳、双侧同块多现身）留活路。
- **PAXG 链上转账费现役为 0**（曾经 0.02% 是老黄历）——勿再当税币验收样本；**HOGE 2% 税硬编码在合约里，是稳定的 BLOCK 回归样本**。
- Helius getAccountInfo(jsonParsed) 对 Token-2022 扩展解析完整（BERN transferFeeConfig 全字段直出），无需手动解 TLV。
- BSC 非 archive 下 rebase 属弱检测（64 块≈3 分钟窗口抓不到 24h 周期 rebase，脚本 warnings 自我声明）——BSC 币强怀疑 rebase 时用 HyperSync 拉单地址全史微重放核对。

## 6. BSC 专属坑表

| 坑 | 识别/处理 | 来源 |
|---|---|---|
| Binance Alpha 2.0 Router 托管黑箱 | BSC meme 生态特有：单一 Alpha 托管合约可能就是 top1 holder 且份额巨大，绝不能当成"庄家地址"分析。识别=WebFetch bscscan 官方标签 + 工厂合约 getPair 分清主池/尘埃池；处理=与 CEX 热钱包一并归入"不可穿透黑箱"，报告显式给黑箱占比与单一实体份额上限，措辞一律带"链上可证范围内"限定 | （SIREN，07） |
| **Alpha 转正币安现货后 Router 黑箱消失** | bapi 全量表 `listingCex=True`（Alpha 转正现货）的币：Alpha 端 offline=True/canTransfer=False，**Alpha 2.0 Router 托管随转正清空迁移**（BANANAS31 实测 Router 余额仅剩 ≈101 枚）——转正币无 Alpha Router 黑箱，币安黑箱=常规充提托管热钱包体系，E0b/黑箱盘点按普通 CEX 口径做即可，勿再找 Router 大仓 | （BANANAS31，07-22） |
| **BSC 历史段块时长折算坑** | BSC 块时长随硬分叉多次变更（2024-11 实测 3s/块，≠现值亚秒级）——"发射后 N 分钟"类时间叙述**必须用区块时间戳差**，禁止块数×固定块时长折算（BANANAS31 案复核抓出 27→81 分钟传播级错误，狙击峰值时点差 3 倍） | （BANANAS31 复核，07-22） |
| **four.meme TokenManager 毛口径虚高** | bonding curve 买卖双向都过 TokenManager，其**毛流出可远超总供应**（BANANAS31 案毛流出 153.5 亿 > 总量 100 亿）——发射窗 bundle/狙击/份额判定禁止用 TokenManager 毛流出，必须重放净口径+毕业时点存量（流量存量双口径纪律的 four.meme 场景） | （BANANAS31，07-22） |
| 新 key 不探测就承诺方案 | 任何新 key 到手先做 1 分钟能力探测：eth_blockNumber + 一次真实 getLogs（或一页 transfers），确认块范围上限/限速/链覆盖后再写进计划。反例：dRPC 免费 key 探测前就让用户注册，实测基本不可用，白费一次注册 | （SIREN，07） |
| 用户网络可达性 | 让用户注册任何站点前，先在用户机器上 `curl -s -o /dev/null -w '%{http_code}' {url}` 预检。实测（用户中国网络）：drpc/alchemy/getblock/bitquery 返回 200，app.envio.dev/nodereal 返回 000，dune 403；且"控制台打不开 ≠ API 端点不可用"（bsc.hypersync.xyz 直连通） | （SIREN，07） |
| 数据量按市值臆测 | 曾按市值预估几十万条、实际 2150 万条（代币被高频机器人生态盘踞），耗时预估连环跳票：先拉发射首月抽样外推总量，向用户报保守上限；"转账笔数/市值异常比"本身可写进报告当信号 | （SIREN，07） |
| dataseed 只能做轻查询 | eth_blockNumber / eth_getBlockByNumber / eth_call / eth_getCode（latest 状态）正常，可做时间戳锚点与工厂 getPair；getLogs 与历史状态一律被拒 | （OPN/SIREN，07） |
| 部署块 getCode 二分失效 | 免费节点拒历史 eth_getCode（archive 请求），二分会找错块 → 改用块头时间戳二分定起始块（非 archive 请求） | （OPN/SIREN，07） |
| 通道切换不清观察哨 | 废弃一条数据通道时，同步 TaskStop 与之绑定的 until-grep 观察哨/循环任务，否则空挂十几小时、用户来质问"任务还活着吗" | （SIREN，07） |
| zsh 裸 glob 杀命令链 | 后台命令 `rm -f part_*.csv && python3 ...` 在 glob 无匹配时报 "no matches found" 并中断整条链，扫块脚本被连带杀掉 → 用 `rm -f ... 2>/dev/null \|\| true` 或拆成两条命令 | （OPN，07） |
| scan_transfers 毒段死循环 | 主扫 worker 对失败段无限放回重试：**段数长期不动 + CSV 行数停涨 = 毒段卡死**（发射高峰段数据量超节点上限）。处置：杀掉 scan 进程直接跑 fill 模式（1000 块子段减半递归）；已完成数据在磁盘不丢，fill 后按 done.json 续 | （bibi，07-12） |
| 锚点插值发射窗口系统偏差 | 每 10 万块锚点线性插值在发射窗口可有 +100s 级恒定偏差（BSC 出块速率变化）。分钟 K 配价前必须 RPC 实查 2-3 个关键块定量偏差，发射窗口改用"精确锚定块 + 实测出块间隔外推"（如 ts=mint_ts+(blk-mint_blk)*0.45）；小时/日级分析不受影响 | （bibi，07-12） |
| GoPlus is_contract 误报 EIP-7702 | 委托型 EOA（7702）被 GoPlus 标 is_contract=1（曾致 top10 中 4 个被误当合约）。甄别：bscscan 地址页看"委托对象"字段，或 eth_getCode 前缀 0xef0100 | （bibi，07-12） |
| GMGN 卖出榜 EOA 口径新形态 | 卖出榜"纯转入零买入、卖出数十万美元"地址可能在 Transfer 事件里**完全不出现**（智能钱包/路由的操作者 EOA），不能当"内部钱包变现"指认；需 tx 层核实 msg.sender 与事件主体的关系 | （bibi，07-12） |
| WebFetch 读代理合约页误报合约名 | bscscan 代理合约页经 WebFetch 提取可能拿到错误合约名（曾把某实现合约误读成别的标签名）。代理合约身份认定必须：EIP-1967 implementation slot 读实现地址 + 字节码 PUSH4 选择器提取（openchain 签名库解析）——WebFetch 文本不作为代理合约功能的最终证据 | （bibi，07-12） |
| 币安 Web3 钱包 DEX Router 串假实体 | `0xb300000b72deaeb607a12d5f54773d1c19c7028d`（vanity 前缀）是币安 Web3 钱包 app 的 DEX 交易入口：数十个用户的"首笔代币来源"都是它、与用户双向大额往来——作"共同首币来源/直转"边会把互不相识的币安钱包用户串成数百址假实体（实测 421 址大簇根因）。**E3 类共源边的源地址必须先过标签库**；它与 LI.FI Diamond、高频对倒 bot 代理同为漏网"半枢纽"（度数几十、不到出度>200 剔除线） | （哈基米，07-18） |
| Uniswap V4 PoolManager 漏出池子清单 | V4 是单例合约（bsc: `0x28e2ea090877bf75740558f6bfb36a5ffee9e9df`），不在常规 pair 发现流程（factory getPair/Dexscreener pairs）内——漏掉会错过其上的 bot 刷量：实测四个脉冲日占全网转账笔数 49-88%、毛量 40-76%（单日毛量 4.7 亿枚 vs 池深仅 24.7 万枚），且与拉升起点精准同步，"放量上涨"表观数据严重失真。**量能真实性检查加"V4 毛量占比"维度**；四日脉冲定量法=占笔数/占毛量/池深对照/与拉升同步性 | （哈基米，07-18） |
| **ETH V4 PoolManager 被公共标签库错标** | ETH 主网 V4 单例=`0x000000000004444c5dc75cb358380d2e3de08a90`（vanity 全零前缀），dawsbot 源把它标成 "Sandwich Attacker"——差点把 V4 池仓当 MEV bot 个人仓写进报告。**vanity 全零前缀地址命中"bot/攻击者"类标签时必先 getCode+行为核验**；本库已 curation 修正。各链 V4 单例地址不同（Base=`0x498581fF718922c3f8e6A244956aF099B2652b2b`），新链先查官方部署表 | （ASTEROID，07-18） |
| **V4/Infinity 单例合约余额禁止直接归池、归庄** | PoolManager/Vault 类单例是**所有池共用的中央金库**：`balanceOf(单例)` = 该币在全部 V4 池＋未结清余额的总和，既不等于某一个池、更不等于某一个庄的头寸。把单例总余额直接写成"庄的 V4 池仓"是方法越界——哪怕该币恰好只有一个 V4 主池、数量级碰巧对上（QUQ 案 V4 17.6% 即此错法，外部复核判 WEAKENED：口径方向对、精确值未闭合）。**归属唯一正解=逐头寸闭合**：按 `poolId＋position(tickLower,tickUpper,salt)＋owner` 重放 ModifyLiquidity 全史，算出各 owner 头寸在目标区块可赎回的本币数量，再穿透回实体（经济控制账，见 report-template 三账本分离）；单例总余额只可用作池级监控哨与上界锚。 | （GPT5.6 外部复核采纳，07-24） |
| "高入度低出度"在 ETH 不能直接判 CEX 归集 | 入度数千/出度个位的地址在 ETH 大多是 swap 执行中转/路由内腿（下游=池子/路由，如 V4 适配器、聚合器执行合约），不是 CEX 充值归集。判 CEX 库必须看**下游对象身份**（热钱包/冷钱包标签）而非只看入出度形态 | （ASTEROID，07-18） |
| DexScreener dexId "uniswap" 无版本标注可能是 V3 池 | Swap topic：V3=`0xc42079f9…`、V2=`0xd78ad95f…`；dexId 只写 "uniswap" 不标版本时，先按 log topic 判池版本再解析，按错版本解析买卖归因全错 | （外部 bibi 考古，07） |
| four.meme 内盘量化 / 克隆快判 | 内盘额度恰 8 亿/80%，dev-buy 同 tx 按 bonding curve 买断内盘凑满即秒毕业、创世后约 8 块（~4s）TokenManager2 注 20% 入 Pancake V2；"创世同秒单钱包拿走 ~80%"=dev buy。`7777` 后缀=另一发射台 CREATE2（与 4444 并列，平台特征非指纹）。meme-api 全路径已 404，正身改看创世 tx HTML 是否触及 TokenManager2/部署器（创建者从合约页 Contract Creator 取，href 单引号，正则 `["']?`） | （外部 TCC/bibi 考古，07） |
| **PancakeSwap V3 Swap topic ≠ Uniswap V3** | Pancake V3 Swap=`0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83`（data 布局 7×32B：amount0,amount1,sqrtPriceX96,liquidity,tick,protocolFeesToken0,protocolFeesToken1），Uniswap V3=`0xc42079f9...`（5 字段）。**按 Uniswap topic 采 Pancake 池 Swap 会静默返回 0 行**（无报错）；反解价格 price=(sqrtPriceX96/2^96)^2 为 token1/token0，SIREN(token0)<WBNB(token1) 时该值=WBNB/SIREN，×BNB 价得 USD。发射期无 CEX K 线时用池 Swap 重建日中位价（SIREN 23.8 万条 Swap 重建 2025-02~03 吸筹成本） | （SIREN，07-19） |
| **scan_transfers.py 本机 curl 线程池挂死** | 8 worker × subprocess(curl) 组合在本机零产出、无报错、进程活着但不写 CSV；同端点单请求 curl 通、requests 3 线程 0.4-0.5s 间隔稳定 → HTTP 客户端改 `requests.Session`（自写 scan_seg11.py 范式，已入 scripts_local 待收编）；bloXroute 并发降到 3、间隔 ≥0.4s | （SIREN，07-19） |
| four.meme 连环盘 / 致敬币指纹 | **连环盘**：同一创建者短时（十几小时）连发 ≥5 个币、每次创世秒买断 ~80% 并在 1 分钟内把大部分转给**同一收币钱包**——TOP1 大户的 tokentxns 里混着大量其他 4444 币即此线索。**致敬币变体**：收币钱包可能是被致敬 KOL 本人（印证行为=向官方慈善多签捐 1% + 向代币合约自转等效销毁），其约束只有公开声誉（软约束），报告按"收币实体"陈述、身份措辞按证据分级。另：GT 日线只留 ~180 天导致老币毕业价缺失时，可由 four.meme 曲线参数（saleAmount/raisedAmount）反解毕业价 | （外部 TCC/人生K线 考古，07） |
| **币安 Alpha"场内↔链上结算引擎桥"识别** | Alpha 在架 BSC 标的会出现一个超大吞吐地址（AKE 案 0x6aba…1b90，累计吞吐 1218 亿枚=1.2 倍总供应、净持≈0）：对手方全是 Alpha Router / 币安 Web3 入口(0xb300000b72deaeb607a12d5f54773d1c19c7028d，vanity 前缀) / 公共聚合路由 / 各池子——它是**币安场内买卖↔链上 DEX 的双向对冲执行器**（把场内压力实时传导到链上池价），归 CEX 基础设施桶（no_merge/exclude），**绝不能当大户或庄**。识别=高吞吐+净持≈0+对手方全为交易所/路由/池子。Alpha 标的标配排查件 | （AKE，07-19） |
| **CEX 归集批次节奏≠行为指纹（对抗复核 REFUTED 源）** | "两地址同分钟末笔充值 Gate=同一操作者"被硬证据推翻：交易所归集是**批次节奏**，同一分钟窗常有数十个互不相关用户地址同批入账（AKE 案 7-18 17:40-49 共 71 个不同地址同批充 Gate1）。凡"充值时间对齐"类指纹，**必须先拉同窗口全量充值做对照组**——同窗地址数 >10 即该"同分钟"零区分力。与 §6 同秒买入矩阵三要素法同理（先造对照组测误报率） | （AKE 复核，07-19） |
| **投毒者 dust 伪装 gas 种子 + 幽灵地址反污染** | 职业投毒团伙给"即将活跃的新地址"发 0.001 BNB 级 dust，gas 溯源会误当"同源强边"（AKE 案双雄的"同额 gas 种子"实为投毒者所发）。判据：该 funder 流水含大量 $0 vanity 仿冒转账+盯梢真实转账=职业投毒者，其一切转账不作聚类边。**衍生坑**：从 trace/BFS 截断打印转述地址时会手补出"幽灵地址"（全史 0 笔的仿冒体）混入实体表——凡进 camps/实体表的地址必须回 merged.csv 验证存在性+走量匹配（AKE 案完整性复核抓出 2 个幽灵，替换为同前缀真实节点） | （AKE，07-19） |
| **币安 Alpha Box 空投标的三件套时序指纹** | 项目方系统=空投币源提供方时：①公告前数天向 Alpha Router 集中充值（AKE 案 7-04~07 充 76 亿）②同期向粉尘分发器注资（随后数万笔粉尘化发放=空投投放通道）③公告后砸底卖压主力的**更优备择=领取人即领即抛**（非项目方场内出货，后者是黑箱不可证）。**Router 充值构成必拆"托管系新币 vs 场内库存回充"**——AKE 案 76 亿中 58 亿是 4 月已提出库存的原额回充（44 址静默 3 个月+dust 试提指纹），不拆会把注入规模高估 4 倍 | （AKE 复核，07-19） |
| **key_edges 提取排除设施边 → 来源拆解选择偏差** | 亿级转账为控量提取"关键边"流水时，若把池/枢纽/路由的设施边排除在外，事后拿 key_edges 做某仓"币从哪来/去哪"的来源拆解会**系统性漏掉经设施走的流量**（选择偏差——刷量盘的大头恰恰经池/枢纽走）。兜底=**daily_delta 缺口法**：该仓按日全量净变动（daily_delta）与 key_edges 汇总的差值=未入选边的缺口量，缺口显著就回全量数据补拉该仓该窗口的完整边再下结论 | （QUQ，07-22） |
| **亿级 edges 提取禁止攒内存** | 1 亿条级转账逐行提边时 list 攒内存会 OOM/假死——一律边读边流式 append 落盘（QUQ 案 key_edges.csv 7.3GB 逐行流式写出），聚合统计另做二遍 pass；产物文件在交接包标注"勿整读" | （QUQ，07-22） |
| **币安 Alpha 积分倍数 mulPoint 直查** | `www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list`（免 key 国内直连，~656 币）每币带 **`mulPoint`=当前积分倍数**及 listingTime/volume24h/count24h/holders/score。2026-07-22 实测分布：645 币=1x、11 币=4x（全是 30 天内新 TGE=Points Plus 加成）。Alpha 在架标的量能判读**第一步先查此字段**；⚠只有当前值无历史接口，历史轨迹靠政策线锚点+快讯/推特回溯 | （QUQ 投后，07-22） |
| **Alpha 积分政策时间线锚点 + 量能断崖三因鉴别** | 政策线：2025 年中 BSC 币全板块 2x → **2025-09-04 取消**（BSC 双倍与 Alpha 2.0 限价单双倍一并废止，改新 TGE 30 天 4x）→ **2026-07-22 Alpha CEX 限价单买 BSC 币 4x**（挽回板块流量新政）。Alpha 币量能台阶/断崖先对政策线，再三因鉴别：①个币处分（mulPoint 降档）②板块政策变化 ③**竞价性分流**（更高倍数/更低磨损的新载体抢走刷分大军——刷分量是"倍数×磨损成本"性价比的函数）。鉴别三件套=mulPoint 直查+**对照币实验**（同板块 2-3 币 GT 日 K 同窗看是否同跌，同跌=板块性非个币）+xapi `search_posts_all` 断崖窗口±3 天搜刷分社区实时讨论（⚠中文**带引号词组零命中**，拆开词搜）。QUQ 案：07-14 单日腰斩且随后 8 天窄带平稳（窄带新平台=新配额指纹），判③——美股代币 4x+磨损低 15 倍分流，对照币同窗 -93% 更狠、QUQ 仍全表量第一=分流非处分 | （QUQ 投后，07-22） |
| **Alpha 场内↔链上量能迁移互斥 + 监控防误读** | 场内（Alpha CEX 限价单）有倍数/磨损优势时，**链上 DEX 量可整段归零而需求未死**：QUQ 案 2025-08 下旬~09-10 链上池成交连续 $0，恰为场内托管峰期；09-04 场内双倍取消后量才迁回链上。推论三条：①链上量崩先查同期币安页 24h 总量与政策线，勿直判需求死亡；②监控组"向 Alpha 托管/寄存仓大额转移"落在场内政策利好窗口（如 2026-07-22 限价单 4x 生效日）时，优先解读为"搬场内复业"而非出货——辅证=结算引擎桥（6aba 类）双向对冲仍活跃+托管后无 CEX 出金链；③上架头几个月成交可能全在场内，**全史链上口径系统性低估早期量，报告必须声明** | （QUQ 投后，07-22） |
| **全史 DEX 成交量硬算（池腿法）** | 每笔 swap 必有一条代币进/出池的 Transfer 腿：POOLS={各直连池+V4 PoolManager 单例}，from/to 恰一侧在集合=计一腿（**单边口径**），池↔池转账（V3↔V4 摆深度）自动排除；**LP 加撤剔除**=lp_events 的 mint（进池）+collect（出池）amount 按日减（burn 只记账无 Transfer 勿剔，QUQ 案剔 2%）。价格三源拼接：CG（365d 窗）+DefiLlama historical 逐日（2025 起 BSC 小币覆盖好，发射数日内即有价）+GT day 线只留 ~181 天。**费反推独立交叉验证器**：V3 全史 collect−burn 双边费 ÷ 池费率 = 名义成交额，与池腿实算互验（QUQ 案吻合 103%=强自洽）；CG 聚合口径预期偏高（链上/CG≈83% 属正常带） | （QUQ 投后，07-22） |
| **transfers_lib 整表读大 parquet 必 OOM** | `iter_transfers` 内部 `pq.read_table` 整表载入，logs.parquet 数 GB 级（QUQ 案 6.6GB/1.03 亿行）直接 SIGKILL（exit 137、输出全空）。亿级全史扫描自写 pyarrow `ParquetFile.iter_batches(batch_size=20万, columns=['block_number','topic1','topic2','data'])` 流式，峰值内存 <1GB、约 2 分钟/亿行；日期用 blocks.parquet number→timestamp 映射 + `ts//86400` 整数日聚合（避免逐行 strftime）；跨 run 去重用块边界法 `[from_block,next_block)`（亿级 (tx,log_index) set 去重内存不可行） | （QUQ 投后，07-22） |
| **V3/V4 LP 费口径鸿沟 + swap 回执速查** | V3 费与本金分开记账：`collect−burn`=纯费，**但只有在同仓位、同边界且处理了期初 `tokensOwed`/跨窗结转之后才成立**；且**双边各收**（买单付 U 侧费、卖单付币侧费，平衡盘两侧近似对称——只算 U 侧会漏报一半）。V4 费并入头寸结算（`callerDelta=principalDelta+feesAccrued`），普通 `ModifyLiquidity` 事件不公开本金与费的拆分，但**核心调用分别返回 `principalDelta`/`feesAccrued`** ⇒ **单笔提现转账拆不出费 ≠ 费不可算**（旧结论"只有净现金流无硬数"被 GPT5.6 外部复核推翻，2026-07-24）：①全池费=Σ逐笔 Swap 实际输入×费率；②仓位应得=重放全部 ModifyLiquidity 史，按价格路径/tick 区间/活跃流动性占比分摊（每笔 Swap 事件的 liquidity 字段可对账重放正确性——QUQ 复核 24h 重放 20,610 笔 swap 0 次不匹配、核心加权份额 99.99998%）；③当前未结算=`feeGrowthInside` 公式 `liquidity×(feeGrowthInside−feeGrowthInsideLast)/2^128`；已结算部分只能称"晶化估算"、历史已提净利润还需处理本金混合与迁仓——分层措辞，参考实现 calc_v4_lp_fees_24h.py（QUQ 复核资产，Documents/5.6筹码分析/QUQ分析/scripts/）。**四层口径（池子产生/仓位应得/当前未结算/历史已结算）与公式、8 项对账 gate 统一见 `lp-fee-accounting.md`。**swap 回执速查三招：①V4 腿特征=代币对手方必是 PoolManager 单例，直连池合约收付=V3 系（Uni/PCS 再按 Swap topic 分家）；②池费率必须从池状态/Swap 事件读取（`fee()` selector `0xddca3f43` 直查，返回 pips/1e6，V3 最低档 0.01%=100），**动态费禁用静态假设**；③路由抽成验证=各拆腿输入之和 vs 用户付出额（b300 实测零抽成、拆单两腿成交价一致）；路由按笔实时比价，同一标的先后两笔可走完全不同的池组合 | （QUQ 投后，07-22；LP 复核修正 07-24） |
| **GT 逐池 TVL 伪影 + V4 幽灵仓 + LP 归属定池属** | GT 的 V4 逐池 TVL 多处鬼影（近空池显示数十万美元 TVL）；V4 头寸可转移 ⇒ 按 `(pool,tx_from)` 聚合会出"幽灵仓"。**归属判定优先级**：官方 PositionManager 头寸优先按 `ownerOf(tokenId)` + NFT Transfer 历史 + `(owner,tickLower,tickUpper,salt)` 状态链确定归属；自定义 manager/复合金库再用 receipt 净现金流、内部 trace 与份额账本穿透。**receipt 净现金流只证明投入/提取，不等于手续费账本**（旧口径"V4 外部 LP 硬口径只有 receipt 净现金流"已收窄为兜底路径，2026-07-24）。**池子算不算体系自有，以目标时点可证 LP 归属为准**（V3 看 NFT tokenId 持有人份额）；"体系曾在此做过市"不算：体系 LP 连本带费撤离后的池=外部池，须从当前控制口径摘出（QUQ 案 Pancake 池摘出，67.4%→64.6%） | （QUQ LP 补查，07-22；归属口径修正 07-24） |
| **枢纽性质裁决：同 tx 等额配对法** | 拟判"仓库/归集器 vs 撮合过账设施"的高吞吐地址：统计其每笔转入是否在**同一 tx** 内有等额转出（配对率）。配对率≈100%=原子过账/router 内部撮合腿（资金零滞留，是管道不是仓库），归公共设施桶；配对率低+余额滞留=仓库性质，才有"归集/囤仓"嫌疑。QUQ 案 b300（币安 Web3 钱包官方 DEX Router，vanity 前缀 0xb300000b72…）4,181 笔 100% 同笔等额 ⇒"专用性未决"结案为公共设施 | （QUQ 投后，07-22） |
| **GMGN 池子流动性数字是 V2 式等值估算，V3 池禁直采** | GMGN 面板的 pool liquidity 疑按"稳定币侧×2"的 V2 恒等假设估算——集中流动性（V3/V4）下两侧储备价值不对称，该估算系统性失真（EGL1 案面板 $76.5 万 vs 两侧储备实算 $64.6 万，高估 18%；GoPlus 口径另为 $37.7 万，三源三值）。V3 池 TVL 一律 `slot0`+两侧 `balanceOf(pool)` 储备实算（reserve0×价+reserve1×价），报告写明口径；外部聚合器前端流动性数字同 GT TVL 伪影条待遇——属"别人的分析结论"，入报前必须第一方复算 | （EGL1 redo2 复核 C5，07-28） |

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
- 地址概览：`bscscan.com/address/<addr>` 拿 Public Name Tag / Contract Creator / "Funded By"（href 用单引号，正则要 `["']?` 容单双引号）。⚠ WebFetch 抓此类页面返回的地址常是省略号截断形态（`0xe096774F...BD5E2f603`），截断地址禁止进任何产物——一律回本地落盘数据前缀反查完整地址（evidence-wording 落盘取值纪律）（QUQ 07-22）
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
- **`eth.blockscout.com/api/v2` 与 Robinhood 链 Blockscout 同栈同端点**（holders 分页 / token counters / smart-contracts 合约名与 implementation（识别 proxy/EIP-7702 delegate）/ internal-transactions 全套可用，端点细节见 data-pipeline-robinhood-channels.md）——ETH 侧持有人榜、地址画像、合约识别的免 key 主通道（外部 ASTEROID 考古，2026-07）。
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

- **输出形态随之改变**（全史演变曲线在此拓扑下不可得，报告口径必须声明）：**结构快照**（当前各阵营占比）+ **6 天净变动表** + **大户建仓时间线**。⚠️ **边界：此路线不满足 /token-analyze 与 /token-easy-analysis 的交付合同**（两者都要求全史演变），只能作预检/受限快照用；正式分析必须补全史（拿 key 走 HyperSync 等全量通道）或明确告知用户后中止。
- **fresh/old 大户分层**：用 6 天窗口把前排大户分为"本窗口进场新大户 vs 更早老持仓"两层，直答"这波爆量谁在买"。
- 图表叙事技巧：大户建仓时间线图上"创世期区域完全空白"= 没有任何创世钱包还留在前排的可视化证明（老庄已清仓的直观证法）。

（本节来源：外部电脑 BSC/ETH 分析考古，2026-07；原始会话见 `windows虚拟机cc会话记录/`）


### 7.6 Blockscout v2 持有人榜与地址画像（ETH / Base / Arbitrum，免 key）
端点 `https://<eth|base|arbitrum>.blockscout.com/api/v2/...`，普通 Chrome UA 直连，无需 key。三件套：
- 持有人榜 `/tokens/{addr}/holders`——**不支持 `limit` 参数**（传了返 422 `Unexpected field: limit`），只能用响应里的 `next_page_params` 逐页翻，50 条/页；items 带 `address.name` 公共标签（RewardTracker / UniswapV2Pair / GnosisSafeProxy / 交易所名等），是免费认所的第一道。
- 代币元信息 `/tokens/{addr}`——`total_supply`（raw）/`decimals`/`holders_count`。
- 地址画像 `/addresses/{a}`（`coin_balance` 原生币余额、`is_contract`）+ `/addresses/{a}/tokens?type=ERC-20`（持币种类）+ `/addresses/{a}/counters`（`transactions_count` = 主动发起交易数）+ `/addresses/{a}/token-transfers?type=ERC-20&token=<币>`（按币种过滤的单地址流水，分页同上）。
- **⚠ 持有人榜有滞后与遗漏，禁止作为余额权威源**（TOSHI(Base) 实测，2026-07-26）：与全量 Transfer 重放 + 链上 `balanceOf` 三方对账发现——`0x8752a799…` 榜单报 16.17 亿而实际 121.37 亿（**少报 105 亿**）；`0x5d657592…`（180.47 亿枚，占流通 4.29%）与 `0xe810e8b2…`（64.22 亿枚）**在 top500 榜里完全不出现**。重放与链上实查逐笔相等，榜单错。**纪律：Blockscout 榜只用于"快速找候选 + 拿公共标签"，任何进入结论的余额数字必须经全量重放或 `balanceOf` 复核**；E0b 快照若只靠榜单，覆盖率与占比都会系统性偏低（该案初值 36.62% → 重放后 43.96%）。
- 同源提示：`transactions_count` 与 `eth_getTransactionCount`（nonce）不是一回事但同向；判"从未主动签发交易"以 **nonce 为准**（见 playbook-entity-cluster-methods §6 nonce 基准率法）。

### 7.7 Avalanche：Routescan API（免 key，snowtrace 已 403）
`https://api.routescan.io/v2/network/mainnet/evm/43114/erc20/{token}/holders?limit=100`，免 key 直连、`link.nextToken` 翻页，返回 `address`/`balance`(raw)/`percentage`（**小数形态，0.300574 即 30.06%**）。
- 死路记录（2026-07-26 实测）：`snowtrace.io/api/v2/...` 返 **403**；`avalanche.blockscout.com` **不存在**（404 default backend）；`bsc.blockscout.com` 同样 404——**BSC 无 Blockscout 实例，持有人榜只能走 §7.2 BscScan 网页**。
- 用途：多链标的的分支链快照（GMX 的 Avalanche 侧占其全局链上量 5.46%，看板口径未覆盖，实查该侧另有 22.73% 在 CEX）。
