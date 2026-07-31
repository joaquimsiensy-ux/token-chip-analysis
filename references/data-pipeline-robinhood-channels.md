# Robinhood Chain 数据管道 · 采集通道与可复用脚本（data-pipeline-robinhood 分册 1/3）

> 母文档：`data-pipeline-robinhood.md`（已拆为薄路由索引页；链概况与合并来源声明见索引页）。本册覆盖原「通道决策（实测）」＋「可复用脚本」＋「修正记录」三段；「链特有的坑」（坑 1–17）见 `data-pipeline-robinhood-traps.md`，「方法论坑」（Robinhood 绑定条目）见 `data-pipeline-robinhood-methods.md`。规则逐条原样迁移、零改写；拆册整编 2026-07-31（v6.3.0）。

## 通道决策（实测）

| 通道 | 状态 | 说明 |
|---|---|---|
| **envio HyperSync** `https://robinhood.hypersync.xyz/query` | ✅ 主力 | 登记 key 直接可用。logs 查询快（RAXOL：66k 条 Transfer 带 block ts+tx from/to 2.4 分钟；GME：6 万转账+3 万 swap 几分钟）。**transactions 按 from/to 过滤扫全链很慢**（GME 实测 >20 分钟不出；高频地址会扫不完）——按地址查交易改用 Blockscout（下行），HyperSync 只用 logs。**同 key 并发纪律：4 路采集脚本同时打必 429 连败**（meow 实测 transfers 首跑被打死退出、断点续传救回），**≤2 路并发安全**；多脚本按"最长任务先行、其余错峰"排程（meow，07-15）。**收紧（2026-07-17 实测）：高峰时段 2 路并发也会 429→"Remote end closed"连败**（两批 2 路分批仍打挂，改全串行+批间隔 30s 才稳）——服务端限流有时段波动，429 出现即降级串行，勿按"2 路上限"硬扛（DUMBMONEY，07-17） |
| **Blockscout 浏览器 API** `https://robinhoodchain.blockscout.com/api/v2/` | ✅（免费无 key） | GME 实测可用。坑：python urllib 默认 UA 被 403，**必须带浏览器 User-Agent**（curl 默认 UA 反而通）。可用端点：`/addresses/{a}/transactions?filter=to`（gas 溯源）、`/tokens/{a}/holders`、`/smart-contracts/{a}`（合约验证/代码判定）、counters。⚠️ RAXOL 会话曾误记"未找到"（试的是 explorer.robinhood.com 等错误域名），见修正记录。⚠️ `?filter=from` 对个别地址稳定返回 500（HAN 分析实测 0xe4a001…），去掉 filter 改本地过滤即可（HAN，07-16） |
| **公共 RPC** `https://rpc.mainnet.chain.robinhood.com` | ✅ | GME 实测可用。eth_getCode/eth_call 可用 → **金库性质（合约 vs EOA）可直接判定**，无需"是否签过交易"半判据。⚠️ RAXOL 会话曾误记"未找到"（试的 rpc.chain.robinhood.com / robinhood.calderachain.xyz / rpc.robinhood.gelato.digital 三个错误域名），见修正记录。⚠️ **与 Blockscout 同款 WAF：python urllib 默认 UA 会 403（curl 默认 UA 反而通）——批量 eth_call/getCode 必须带浏览器 User-Agent 头**，403 长得像限流实为 UA 拦截（CASHCAT，07-13）。getLogs 实测参数：**40 万块/请求、单次结果上限 1 万条**（5.6 万条约 81 秒）；批量 getCode 会 429，温和退避重试即可（外部 GME/CASHCAT 考古，07） |
| GeckoTerminal | ✅ | 支持 `networks/robinhood`。分钟K从建池分钟起可得，小时K全历史。**必须带浏览器 User-Agent**（python-urllib 默认 UA 被 403）；限速≈30req/min，429 后退避。⚠️ **GT 的 pool_created_at 是 GT 收录时间不是链上创建时间**——新币前期价格要用链上 swap sqrtPriceX96 自己重建；Dexscreener 的 pairCreatedAt **两说并列**：GME 实测=真实链上时间，但 VEX 实测偏差 11.5 小时（DS 显示比链上首笔 Transfer 晚半天）——**用前一律以链上主池首笔 Transfer 定毕业时刻**，DS 时间只作参考（VEX 复核 2026-07-13） |
| Dexscreener | ✅ | `latest/dex/pairs/robinhood/<pair>` 实时池子储备，可做余额对账独立源（RAXOL 对表误差 0.000%）；pairCreatedAt 口径按上行 GT 条的**两说并列**纪律——用前一律以链上主池首笔 Transfer 为准，DS 时间只作参考 |
| **Etherscan V2 chainid=42161（Arbitrum 侧溯源）** | ✅（2026-07-16 实测） | Robinhood 链实体的源链资金常来自 Arbitrum One——登记 key 的免费层支持 Arb，txlist 直查金主注资/LiFi 分批桥出全记录（实测把一个"断头"资金链完整穿透到两个 Arbitrum 金主）。注意两种自桥形态并存：ETH L1 自桥经官方桥有 +0x1111…1111 别名，Arbitrum→Robinhood 经 Across/Relay 聚合则是**同址直查**（Across 的 FilledRelay 事件可解码 originChainId+depositor）（VIRTUAL，07-16） |
| Virtuals 平台 API | ✅ | `api.virtuals.io/api/virtuals?filters[tokenAddress]=<addr>` 可拿 agent 档案（创建者钱包/DAO地址/叙事），走代理。**正式解锁表加 `&populate[0]=tokenomics`**：返回 isLocked/startsAt/linearBips/numOfUnlocksForEachLinear/releases 全字段（RAXOL 实测 Team 25% = TGE+1 年 cliff 后 1666bips 首解 + 8334bips 分 5 次月线性）——问 3 解锁日程小节的权威来源（RAXOL 更新 07-14） |
| **公共 RPC `eth_getLogs`（HyperSync 429 时的全量备选，Index 分析 2026-07-18 实测）** | ✅ 备选主力 | HyperSync logs **高峰时段会整体 429 连败**（断点续传循环也救不回，服务端时段性限流；Index 案拉到 ~10.79M 块后彻底打死）——切公共 RPC `eth_getLogs` 拉尾段速度可观（12.5 万条约 45 秒、~35 万块/20 秒）。坑：①"log query timed out" 需自适应缩窗（40 万块起、超时折半、热点段降到 5 万）②单响应结果上限约 1 万条 ③**无块时间戳**，须另拉锚点（每 2 万块一 `eth_getBlockByNumber`）线性插值（实测误差≤1s）④HyperSync 段 ts=unix int、RPC 段插值也须转 unix int，合并前统一格式（踩坑：插值先写 ISO 字符串致 replay 排序 TypeError）。脚本 `pull_transfers_rpc.py`+`pull_block_ts_anchors.py`+`merge_hs_rpc.py` 已收编。 |
| dRPC | ❌（2026-07-12 实测） | robinhood 网络锁付费层 |
| GMGN | ❌（2026-07-12 实测） | 不支持该链 |

（否定性条目时效纪律见 retrospective.md 红线 4：距实测超 3 个月且确有需要时允许 1 分钟重探。）

## 可复用脚本（scripts/robinhood/，v1.3 已收编进 skill）

- `pull_transfers.py`：HyperSync 全量 Transfer 断点续传（certifi SSL；token/key 从工作目录 config.json 读）
- `gas_trace.py`：候选地址原生币入金批量溯源（HyperSync transactions，50 址/批；基础设施剔除名单从 config.json 读）。⚠️ **COMPUTE 会话实测（链高 789 万时）走 HyperSync transactions 25 分钟无产出并连败退出**——链增高后此路已不可行，改用下面的 gas_trace_bs.py
- `gas_trace_bs.py`：**Blockscout 版 gas 溯源（现主力，v1.4.1 收编进 skill）**（Pointless 2026-07-13 参数化收编，替换原 COMPUTE 项目目录里的样例）——逐地址 `/addresses/{a}/transactions?filter=to` 查最早入金 + funder→目标数汇总；断点续传；须浏览器 UA；候选阈值/extra_targets 从 config.gas_trace 读（34 址约 3-4 分钟；180 址约 20 分钟）。**消费输出时必读 `self_alias` 字段**——脚本已内置 L1 桥别名自检并正确标记，但汇总脚本只打印 funder 会把"本人 L1 自充值"当独立金主展示（NOXA 分析 2026-07-15 实翻：漏读该字段后靠最长公共子串复查才殊途同归，浪费一轮）。**反向坑：SELF_ALIAS ≠ 独立性证据**——alias 自桥的语义是"资金关系断在 L1 侧（本链数据不可见）"，是**不可分辨**而非"已证无外部金主"；把它当独立户论据会漏掉 L1 侧同源的协同群（CASHCAT 增量案：对抗复核据此翻出 7 址同一小时窗 alias 自桥+机器节奏建仓的观察组，主分析曾以 SELF_ALIAS 误判"独立大户"）（CASHCAT 更新，07-15）。**★per_addr_limit=8 采样截断坑：每址只取最早 8 笔入金，高频双向 funder 关系会被系统性漏采**——实测漏掉"creator↔关联人 9 笔双向往来"（截断后只见 3/7 笔）与"埋伏对建仓前 9 小时的 5 ETH 直转"（它是该址第 2 笔入金、恰在 limit 内但按'最早一笔'分组被跳过）两类关键边，复核靠 Blockscout 全量双向拉取才翻案。纪律：①funder 收敛分析不得只按"每址最早一笔"分组，须全笔按 funder 分组；②重点实体地址一律再用 Blockscout `/addresses/{a}/transactions`（双向不带 filter）+ internal-transactions 全量兜底（DUMBMONEY 复核，07-17）
- `pull_weth_pool.py`：**主池报价币侧 Transfer**（Pointless 2026-07-13 收编）——cost_engine 的输入；config.pool + 可选 quote_token（默认 WETH）
- `cost_engine.py`：**tx 级 swap 对价重建**（Pointless 2026-07-13 收编；**2026-07-13 VEX 复核修复 quote_usd 秒/毫秒 bug**——K线 key 为币安原生毫秒时旧版恒取首根汇率、全表 USD 偏差可达 ±17%，现已单位自适应；Pointless 期产物如需复用建议重跑）——本币 vs 报价币逐 tx 配对出每实体成本/已实现盈亏；需 data/weth_pool.jsonl + data/quote_usd_hour.json（报价币/USD 小时K，如 binance.vision ETHUSDT）+ transit_contracts.json；config 可选 fee_distributor（剔除 fee 过账不算买入）。多池/非 WETH 报价标的见 methods 分册"多池标的 cost_engine 要点"
- `pull_swaps.py`：**V3 池全量 Swap 事件**（CASHCAT 2026-07-13 收编）——HyperSync logs 按池过滤，输出 a0/a1/sqrtPriceX96；断点续传；池子写 config.swap_pools 数组（86.8 万条 Transfer 链约 30 分钟含 429 退避、23.2 万条 swap 约 9 分钟，量级参考）
- `pull_swaps_v4.py`：**V4 PoolManager 全量 Swap+ModifyLiquidity 事件**（TRASH 2026-07-14 收编，补 V4 盲区 Known Gap）——HyperSync logs 按 `topic1=poolId` 过滤单例 PoolManager，输出 swap 行(a0/a1/sqrtp/liq/tick/fee)与 modliq 行(tickl/ticku/liqdelta)；断点续传+解码失败计数上报；config 填 `swap_pools_v4`(poolId 数组)+`pool_manager`。实测 4.7 万条约 4 分钟。topic0 常量见 traps 分册坑 12
- `build_price.py`：**全历史 USD 价格重建**（CASHCAT 2026-07-13 收编；**2026-07-15 NOXA 分析双修复**：①价格方向由 config 的 token/quote_token 地址排序自动判定——旧版写死"WETH=token1"，遇 token>quote 地址的标的价格恒为倒数、GT 交叉验证偏差 10^13 倍量级即刻暴露，修复后勿再手动改方向；②ethusd() 自适配毫秒级 K 线 key——旧版对币安原生毫秒 ts 恒取首根）——主池 swap sqrtPriceX96→WETH/枚→×ETHUSD 小时K；自动与 GT 分钟K重叠段交叉验证（实测中位偏差 0.86-0.98%）；解决 GT 只存最近 2 天分钟K/收录晚于建池的前期价格空白。**交叉验证不是装饰**：方向 bug 全靠它当场拦截，无 GT 对照会直接进报告。**输入文件名硬约定（2026-07-17 实测）**：脚本硬读 `data/ethusdt_1h.json`（格式 `[[ts_ms,close]…]` 升序数组，非 {ts:[o,h,l,c]} 字典）与 `data/ohlcv_minute.json`（pull_ohlcv.py 产物）——工作流顺序=先跑 pull_ohlcv.py 再 build_price.py，自拉的币安 K 线须转成该数组格式（DUMBMONEY，07-17）
- `pull_lp_events.py` **用法与输出坑（2026-07-17 实测）**：①与其他脚本不同，**不读 config.json 的池子配置**，必须命令行传参 `--from-block N --pools 0x主池 --out data/lp_events.jsonl`（漏传 --from-block 直接 usage 报错、串行链会被短路）；②输出是**格式化 JSON 数组**（非 JSONL，逐行 json.loads 会炸）；③Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（WETH 枚/本币枚），不是 wei——按 wei 再除 1e18 会把费流水全算成 0（本次 Collect 62 笔 4.33 WETH 首轮统计因此归零，重读字段才修正）（DUMBMONEY，07-17）
  ⚠️ 依赖 `data/ethusdt_1h.json` 为 **list 格式** [[ts_ms,close]...]，而 cost_engine 的 quote_usd_hour.json 是 dict——两文件格式不同需各自生成（一行转换即可），首跑 FileNotFoundError 属预期（BEGGAR，07-17）
- `pull_ohlcv.py`：GT 分钟K+小时K 翻页（带 UA/退避；pool 从 config.json 读）
- **HyperSync 429 备选通道三件套（Index 分析 2026-07-18 收编）**：`pull_transfers_rpc.py`（公共 RPC `eth_getLogs` 全量拉 Transfer，token/rpc 从 config.json 读、块范围走 argv `<起始block> <结束block>`、"log query timed out" 自适应缩窗）→ `pull_block_ts_anchors.py`（每 2 万块拉一 eth_getBlockByNumber 锚点，供 RPC 段无 ts 时线性插值）→ `merge_hs_rpc.py`（HyperSync gzip 段 + RPC jsonl 段按 block+logi 去重合并、锚点插值填 RPC 段 ts、ts 统一 unix int）。HyperSync 高峰 429 连败时的完整补救链，产物与 pull_transfers.py 兼容（下游 replay/prescan/evolution 无缝接）。
- `config.example.json`：复制到工作目录改名 config.json 按标的填写（cost_engine 用可加 fee_distributor/quote_token/deploy_block；gas_trace_bs 可加 extra_targets）

标的专属的分析/图表/报告脚本（analyze.py/build_appendix.py 等）存档于各分析项目目录，非复用件。

## 修正记录（否定性结论纪律的实例，retrospective.md 红线 4 由此而来）

2026-07-12 质量审查发现：RAXOL 会话初版把 Blockscout 与公共 RPC 记为"❌ 未找到"——实际是各试了 3 个猜测域名未中就下了全称否定，而同日早 32 分钟交付的 GME 会话已实测出正确域名（`robinhoodchain.blockscout.com` / `rpc.mainnet.chain.robinhood.com`）。该错误的直接代价：RAXOL 分析全程缺失合约验证与 eth_getCode 能力，金库性质只能用"是否签过交易"半判据。教训：**否定性通道结论入库前必须列出试过的端点清单、标注穷尽程度、与 memory 及既有文档交叉核对**。
