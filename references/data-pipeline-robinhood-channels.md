# Robinhood Chain 数据管道 · 采集通道与可复用脚本（data-pipeline-robinhood 分册 1/3）

> 母文档：`data-pipeline-robinhood.md`（薄路由索引页；链概况与合并来源声明见索引页）。本册覆盖「通道决策（实测）」＋「可复用脚本」＋「修正记录」三段；「链特有的坑」（坑 1–17）见 `data-pipeline-robinhood-traps.md`，「方法论坑」（Robinhood 绑定条目）见 `data-pipeline-robinhood-methods.md`。

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

- `pull_transfers.py`：HyperSync Transfer；缓存 meta 绑定 token/url/query，断点从末块本身重叠回拉并按 `(block,tx,log_index)` 去重，避免 mid-block crash 漏尾；next_block 缺失/停滞非零退出，完成写链高与输出哈希 receipt。
- `gas_trace.py`：候选地址原生币入金批量溯源（HyperSync transactions，50 址/批；基础设施剔除名单从 config.json 读）。⚠️ **COMPUTE 会话实测（链高 789 万时）走 HyperSync transactions 25 分钟无产出并连败退出**——链增高后此路已不可行，改用下面的 gas_trace_bs.py
- `gas_trace_bs.py`：Blockscout gas 溯源。成功空结果写 `status=EMPTY/no_native_in`；四次网络失败进入 retry queue、exit 2 且不进入 done，二者不再混成同一记录。消费时仍须处理 `self_alias`，重点实体补 internal-transactions。
- `pull_weth_pool.py`：**主池报价币侧 Transfer**（Pointless 2026-07-13 收编）——cost_engine 的输入；config.pool + 可选 quote_token（默认 WETH）
- `cost_engine.py`：**tx 级 swap 对价重建**——本币和报价币分别使用 config 的 `decimals` / `quote_decimals`，不得再写死 18；逐 tx 配对出每实体成本/已实现盈亏。需 data/weth_pool.jsonl + data/quote_usd_hour.json + transit_contracts.json；config 可选 fee_distributor。
- `pull_swaps.py` / `pull_swaps_v4.py`：与 Transfer 同样采用身份绑定、末块重叠续拉和事件键去重；V4 有任何解码失败不写完成 receipt。
- `build_price.py`：**全历史 USD 价格重建**——方向由 token/quote 地址排序判定，V3 raw ratio 再乘 `10^(token_decimals-quote_decimals)` 校正单位；GT 分钟 K 没有任何重叠样本时 fail-closed，不得发布无交叉验证的价格序列。输入仍为 `data/ethusdt_1h.json` 与 `data/ohlcv_minute.json`。
- `pull_lp_events.py` **用法与输出坑（2026-07-17 实测）**：①与其他脚本不同，**不读 config.json 的池子配置**，必须命令行传参 `--from-block N --pools 0x主池 --out data/lp_events.jsonl`（漏传 --from-block 直接 usage 报错、串行链会被短路）；②输出是**格式化 JSON 数组**（非 JSONL，逐行 json.loads 会炸）；③Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（WETH 枚/本币枚），不是 wei——按 wei 再除 1e18 会把费流水全算成 0（本次 Collect 62 笔 4.33 WETH 首轮统计因此归零，重读字段才修正）（DUMBMONEY，07-17）
  ⚠️ 依赖 `data/ethusdt_1h.json` 为 **list 格式** [[ts_ms,close]...]，而 cost_engine 的 quote_usd_hour.json 是 dict——两文件格式不同需各自生成（一行转换即可），首跑 FileNotFoundError 属预期（BEGGAR，07-17）
- `pull_ohlcv.py`：GT 分钟K+小时K 翻页（带 UA/退避；pool 从 config.json 读）
- **HyperSync 429 备选通道三件套**：`pull_transfers_rpc.py` → `pull_block_ts_anchors.py` → `merge_hs_rpc.py`。合并器遇 gzip EOF/坏 JSON/重复键立即失败，原输入只读；默认写 `transfers_merged.jsonl.gz`，完整复读、行数和哈希 receipt 通过后，只有显式 `--promote` 才替换输入。
- `config.example.json`：复制到工作目录改名 config.json 按标的填写（cost_engine 用可加 fee_distributor/quote_token/deploy_block；gas_trace_bs 可加 extra_targets）

标的专属的分析/图表/报告脚本（analyze.py/build_appendix.py 等）存档于各分析项目目录，非复用件。

## 修正记录（否定性结论纪律的实例，retrospective.md 红线 4 由此而来）

2026-07-12 质量审查发现：RAXOL 会话初版把 Blockscout 与公共 RPC 记为"❌ 未找到"——实际是各试了 3 个猜测域名未中就下了全称否定，而同日早 32 分钟交付的 GME 会话已实测出正确域名（`robinhoodchain.blockscout.com` / `rpc.mainnet.chain.robinhood.com`）。该错误的直接代价：RAXOL 分析全程缺失合约验证与 eth_getCode 能力，金库性质只能用"是否签过交易"半判据。教训：**否定性通道结论入库前必须列出试过的端点清单、标注穷尽程度、与 memory 及既有文档交叉核对**。
