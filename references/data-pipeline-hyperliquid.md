# Hyperliquid（HyperCore）数据管线

适用：HyperCore 原生现货代币的筹码分析采集。全部免费、无需注册 API key。

> 来源声明：本册规则除特别标注外，均源自 HYPE(Hyperliquid) 分析实测（2026-07），不再逐条标注。

## 0. 开工前三件事

- 地址消歧：HyperCore token ID 是 16 字节（32 位 hex），不是 EVM 的 40 位 hex。拿到"格式不合法"的地址先把字面量丢 WebSearch 精确搜索（如 `"0x0d01dc56..." token`），格式不合法 ≠ 地址错误。
- 认清红利：Hyperliquid 是数据富矿——官方 API 自带实体点名、带对手方的逐地址全量流水、genesis 空投全表；Hypurrscan 有免费历史持仓快照。**不需要**扫块/事件重建，也不需要 Multicall。
- 三条铁律：官方 API 地址级查询 3.0s 间隔；一切基于现货快照的指标必须做质押修正；CEX 净流必须先剔同 CEX 内部对倒（详见第 8、9 节）。

## 1. 数据面总览（四个面各拿什么）

| 数据面 | 能拿到什么 |
|---|---|
| 官方 info API | 供应/价格、genesis 空投全表、非流通实体点名、任意地址全量流水（带对手方）、成交明细、质押、K 线 |
| Hypurrscan | 全量持有人现货快照、TGE 至今 6h 粒度历史快照、463 条实体标签、解质押队列、TWAP 挂单 |
| ASXN 面板 | AF 逐日回购、拍卖、DEX 指标——独立第三方，专用于交叉验证 |
| HyperEVM RPC + Blockscout | 桥入 EVM 侧的 WHYPE 分布——只能部分覆盖，按半盲区处理（第 5 节） |

## 2. 官方 info API

`POST https://api.hyperliquid.xyz/info`，body 为 `{"type": "...", ...}`，例：

```bash
curl -s https://api.hyperliquid.xyz/info -H 'Content-Type: application/json' \
  -d '{"type":"tokenDetails","tokenId":"0x<16字节tokenID>"}'
```

限速（实测，务必照抄）：
- 总配额约 1200 weight/min/IP。地址级查询 1.05s 间隔 429 刷屏（2 分钟只完成 16 个地址），调到 2.2s 仍偶发，**3.0s 后 429 归零**，稳定约 10 地址/分钟。轻量端点（tokenDetails/spotMeta/candleSnapshot 等）0.3s 间隔即可。
- 并行子代理与主采集器打的是**同一个 IP 配额**。派子代理时必须在 prompt 里写死接口纪律：禁止官方 API 地址级查询、Hypurrscan ≤5 次/分钟。

端点表（`type` 取值）：

| type | 用途 | 要点 |
|---|---|---|
| `tokenDetails` | 供应/价格/创世 | `genesis.userBalances` 是空投全表（HYPE 返回 94,023 条）；`nonCirculatingUserBalances` **直接点名团队/基金会/AF 等非流通实体地址**——实体识别第一入口 |
| `userNonFundingLedgerUpdates` | 单地址全量转账+质押流水，带对手方 | 2000 条/页；分页用上一页最后一条的 `time+1` 作新 `startTime` 续拉，不足 2000 条即最后一页 |
| `userFillsByTime` | 单地址成交明细 | 同样 2000 条/页可分页。**坑**：实测单地址只返回近 30 天、约 12000 条封顶，会漏更早的买卖——基于 fills 的结论必须限定时间窗 |
| `delegatorSummary` / `delegatorHistory` | 地址当前质押量 / 质押流水 | 现货快照口径修正的必备件（第 8 节） |
| `spotClearinghouseState` | 单地址现货余额 | 单点核对用 |
| `candleSnapshot` | K 线 | 现货对用 `@index`（HYPE/USDC=`@107`）；其他代币先查 `spotMeta` 取对应 index |
| `validatorSummaries` / `portfolio` | 验证人列表 / 账户组合概览 | 辅助 |

## 3. Hypurrscan API

Base：`https://api.hypurrscan.io`，Swagger UI 在 `/ui/`。

- `GET /holders/{token}`：全量持有人→现货余额快照（HYPE 返回 246,400 个地址）。**不含质押余额**，做任何指标前先看第 8 节。
- `GET /holdersAtTimeWithLimit/{token}/{unix_ts}/{limit}`：历史 top-N 持仓快照，最早时间戳 1732991430（2024-11-30），6 小时粒度——免费历史持仓难题的解法，可重建任意大户/实体的持仓曲线。
  - **重大坑**：部分历史时间戳区间（HYPE 一例为 2025-08~2026-04 共 45 档）在 limit=1000/500/200 时 `holders` 返回空 `{}`，limit=100/50 才有数据。这是服务端行为，不是请求错误，HTTP 照样 200。
  - 操作规程：下载后**立即抽查多档原始 JSON 结构**验证非空；发现空档就做 limit 降级探测（1000→500→200→100），对空档补采 top100 落成单独文件，分析脚本里合并 top1000/top100 两种文件（合并逻辑见原版 `analysis/snapshot_series.py`）。
- `GET /globalAliases`：463 条实体标签（AF/Foundation/Hyper Labs/13 个 CEX/烧毁地址）——关联实体识别的核心免费标签源。注意**没有币安主站和 Coinbase** 的标签。
- `GET /fullUnstakingQueue`：解质押排队 = 准抛压，可用于扩充重点监控地址清单。注意它是**历史全量**记录而非仅当前排队，用前按时间过滤。
- `GET /twap/{token}`：大户程序化买卖单（TWAP）。
- `/transfers/{from}/{to}` 需要 JWT，免费不可用——转账流水一律走官方 `userNonFundingLedgerUpdates` 替代。
- 限速：无官方文档，实测按端点分级节流即稳：默认 0.35s；`/holders`、`/twap` 1.0s；`/holdersAtTimeWithLimit` 1.2s；`/fullUnstakingQueue` 2.0s。

## 4. ASXN 面板 API（独立交叉验证源）

- `GET https://api-data.asxn.xyz/api/data/hl-buybacks`：AF 逐日回购（字段 sz/ntl/average_price，一次拿到 471 天全量）。
- 同族端点：`hl-auctions`、`hl-dex-metrics`、`hype-price`。
- 用法：与链上快照差分互为独立源对表——HYPE 一例两源偏差仅 0.7%。规矩：偏差 <1% 才允许给 HIGH 置信度；这是低成本高置信度的标配动作。

## 5. HyperEVM 侧（半盲区）

- RPC：`POST https://rpc.hyperliquid.xyz/evm`（标准 JSON-RPC，`eth_call` 可用）。
- 浏览器：Blockscout 在 `hyperscan.com`（`hyperliquid.cloud.blockscout.com` 已 404）；Etherscan V2 用 `chainid=999`。
- 定位：EVM 侧只能做到部分覆盖，把它当聚类视野盲区处理——报告里显式量化"视野外占比"，不要假装看得见（第 8 节第 4 条）。

## 6. 已知关键地址（可用 globalAliases + nonCirculatingUserBalances 复核）

| 实体 | 地址 |
|---|---|
| AF（Assistance Fund，官方回购基金） | `0xfefefefefefefefefefefefefefefefefefefefe` |
| AF 二号地址 | `0xccd69f432ce1d8c9cdc31bd535dd11b37cbea4ea` |
| 团队（Hyper Labs vesting） | `0x43e9abea1910387c4292bca4b94de81462f8a251` |
| Hyper Foundation | `0xd57ecca444a9acb7208d286be439de12dd09de5d` |
| 排放池（future emissions） | `0xdddddddddddddddddddddddddddddddddddddddd` |
| HyperCore↔EVM 桥 | `0x2222222222222222222222222222222222222222` |
| WHYPE（EVM 侧 ERC-20） | `0x5555555555555555555555555555555555555555` |

（分析别的 HyperCore 代币时，实体表照此法重建：globalAliases 拉标签 + tokenDetails 的 `nonCirculatingUserBalances` 点名。）

注意：EVM 桥地址是所有跨链转账的中转，流水量过大，**不要拉它的 ledger**，只把它放进聚类/工作清单的排除集。

## 7. 采集器：scripts/hyperliquid/collect.py

单文件采集器，官方 info API + Hypurrscan 双封装。设计要点（照用别改）：
- 纯标准库 + certifi SSL 上下文（macOS python.org 版 Python 的 urllib 默认无 CA 链，裸 urllib 必报 CERTIFICATE_VERIFY_FAILED——此坑曾整跑报废一次后台任务；certifi 缺失时回退 `/etc/ssl/cert.pem`）。
- 429/5xx 指数退避重试（2s→60s 封顶）+ 按端点分级限速 + **断点续传**（已存在的输出文件直接跳过）——长跑中途停/重启不丢进度，调限速参数时也靠它保住已采数据。

六个子命令（按此顺序跑，`addresses` 依赖 `worklist`，`worklist` 依赖 `static`+`entities`）：

| 子命令 | 采什么 | 输出 |
|---|---|---|
| `static` | 一次性底座：tokenDetails、holders 全量快照、globalAliases、validatorSummaries、fullUnstakingQueue、twap、spotMeta、日 K | `data/static/*.json` |
| `entities` | 每个已知实体：ledger 全史（分页）、delegatorSummary/History、spotClearinghouseState、portfolio；另拉 AF 近 30 天 fills 确认回购是否进行中 | `data/entities/{name}/*.json` |
| `snapshots` | 历史快照序列：TGE→90 天前按周、近 90 天按日，每档 top-1000 | `data/snapshots/top1000_{ts}.json` |
| `worklist` | 生成地址级采集清单：现货 top500 ∪ genesis top500 ∪ 团队 spotTransfer/send 接收地址 ∪ 实体流水对手方，再剔除系统地址（实体本身、EVM 桥、0x0、dead、0xffff…） | `data/worklist.json` |
| `addresses` | 地址级长跑：按清单逐地址拉 ledger 全史 + delegatorSummary | `data/addresses/{addr}.json` |
| `vesting` | 团队分发接收地址补拉 fills，判断是否市场卖出（二跳去向） | `data/vesting/{addr}_fills.json` |

注意：`snapshots` 只按 limit=1000 采集，**不内置空档降级**——跑完必须按第 3 节规程抽查空档并另行补采 top100。

config 字段（原 HYPE 版为脚本内常量，换代币时改这四项）：
- `token_id`：HyperCore 16 字节 token ID（tokenDetails 用）。
- `entities`：实体名→地址映射表（按第 6 节方法重建）。
- `tge_ms`：TGE 毫秒时间戳，ledger/fills/K 线的 startTime 与快照序列起点。
- `throttle`：请求间隔秒数。实测常数：官方 API 地址级 3.0、轻量 0.3；Hypurrscan 见第 3 节分级值。

长跑运维：地址级采集 1000+ 地址 × 3s ≈ 2 小时量级（HYPE 一次 1189 地址实跑约 2.1 小时），必须**最先启动**（放任务 DAG 关键路径最前），run_in_background 跑、按输出文件数轮询进度，等待期并行写下游分析脚本和报告骨架（占位符先行）。等待条件用 until-loop，前台裸 `sleep` 会被执行环境 Block。

## 8. 口径坑（每条都能改写结论，逐条核对）

1. **现货快照不含质押**。`/holders` 快照总和可能远小于流通量（HYPE 一例 138M vs 流通 298M，差额≈质押中的量）。大户把币质押会被现货口径误判成"清仓"——初算留存率时 top500 有 477 个地址呈"<创世 10%"的假象，逐地址 `delegatorSummary` 修正后口径变化显著。规矩：留存率/集中度/持仓曲线一律做质押修正，所有基于现货快照的数字必须声明口径。
2. **CEX 充值走用户专属充值地址**，实体 ledger 口径下看不见充值、只看得见提币——不能用实体 ledger 判断"是否充入 CEX"，方向性结论会系统性偏差。
3. **CEX 热钱包内部对倒**（同一 CEX 的热钱包/冷钱包/子钱包互转）会污染充提净流统计——先用 globalAliases 把同一 CEX 的全部地址合并成一个实体集合，集合内部转账全部剔除。
4. **桥入 HyperEVM 的部分（WHYPE）是 HyperCore 侧聚类的视野盲区**——HYPE 一例桥入量占流通盘约 18%。桥出后在 EVM 侧的分布，HyperCore 数据面完全看不见。规矩：报告显式量化"聚类视野外占比"，涉及"没看到 X 行为"的结论一律加"HyperCore 链上可观测范围内"限定。

## 9. 反面教训：CEX 月度净流指标（复用前必读）

- 曾用 top-1000 历史快照差分 + CEX 标签构造"CEX 月度净流"指标并据此给出方向性信号，中途已向用户汇报；对抗复核阶段被**整条推翻**，指标和对应图表从报告删除，并向用户如实披露。
- 两个致命伪影：① 同一 CEX 的内部调仓被误计为用户充提；② top-1000 快照只覆盖当期存活大户，存在幸存者偏差——两者叠加足以造出反向假信号。
- 复用该指标的前置条件（缺一不可）：
  1. 剔除同 CEX 实体集合内部对倒（第 8 节第 3 条）；
  2. 样本改用全量持有人快照或地址级 ledger 做差分，不用 top-N 快照；
  3. 措辞纪律：净充入 CEX ≠ 已卖出，只是"进入可售状态"；结论带"链上可观测范围内"限定。
- 更省事的替代：先跑本地反例自查脚本（快照环比、fills 卖单、直转 CEX、基金会大额出账），再让对抗复核代理拿一手数据文件自己重算——该指标就是这样被抓出来的。
