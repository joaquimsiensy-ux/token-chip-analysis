# Solana 筹码分析脚本

## 已有脚本

1. **fetch_sqd_transfers.py** — SQD portal 全量转账边拉取（免 key 免代理，断点缓存+回补验证+墙钟保险丝）。来源：CLAW(Solana) 分析 2026-07-12，v1.3 收编。这是"免费 RPC 无 archive 历史回放"缺口的正解，全量重放路线首选；吞吐量化预期见 pipeline §8（发射高密度段 ≈1.5x 实时、常规 ≈4x）。
2. **scan_token_accounts.py** — getProgramAccounts 全量扫描器（SPL 与 Token-2022 双分支；Token-2022 走 api.mainnet-beta 无 dataSize 全扫 `--datasizes all`，SPL 走 publicnode dataSize:165，见 pipeline §0a/§1）；owner 聚合双口径输出。来源：CLUDE(Solana) 2026-07-13 实战重建（原 IO 待重建清单第 1+2 项）。
3. **trace_wallet.py** — 单钱包全签名流水解码（`--mint` 必填按 mint 过滤 pre/postTokenBalances，0.13s 限速+重试，counterparties 记录）。来源：CLUDE(Solana) 2026-07-13。
4. **fast_probe_tops.py** — top 大户快速画像（首笔时间+来源+签名分布，每 owner 4-8 个 RPC 调用，比全量 decode 快一个数量级）。来源：CLUDE(Solana) 2026-07-13。
5. **probe_escrows.py** — escrow 最老交易探查 + Streamflow stream 元数据 raw 解码（sender/recipient/到期三处互验/cancelable/transferable 标志位，data_len=1104 布局速查见 pipeline §2 Streamflow 条）。来源：CLUDE(Solana) 2026-07-13。
6. **probe_wallet_batch.py** — 批量钱包全流水画像（目标 mint 变动+SOL 流向+最大对手方；隐鲸群/中转网排查用）。目标地址列表按标的替换。来源：CLUDE(Solana) 2026-07-13。
7. **probe_token_account_history.py** — **ATA 级签名史解码**（高频钱包 owner 级签名被稀释时的正解；ATA 已销户时从已知 tx 的 tokenBalances 反查 account 地址，见 pipeline §3a 坑 4）。来源：CLUDE(Solana) 2026-07-13。
8. **replay_edges.py** — **SQD 边重放引擎（全量重放路线的下游标准件）**：reconcile（供给闭合+快照 top50 对账，阶段 2 关卡）/ trace / top / sniper（狙击窗）/ **mints（铸造边全清单——pump.fun 币第一优先检查项，见 pipeline §8）** / evolution（小时级阵营占比序列，`--stake-pool` 质押修正：有效持仓=现货+质押）。阵营定义读 camps.json。来源：PUB(Solana) 2026-07-14 收编。
9. **stake_decode.py** — 质押/托管池账本解码器：池 ATA 签名史 → 逐用户存/取账本 → **净额合计 vs 池链上余额自动闭合验证**；"取回>存入"用户单列（排除归集仓伪装的证据）。配套 pipeline §2 自建质押合约判别五步法。来源：PUB(Solana) 2026-07-14 收编。
10. **gas_origin.py** — 批量地址 gas/资金溯源（最早 3 笔签名 → SOL 入金 funder，累积落盘）。与 mint 无关纯 SOL 层。来源：PUB(Solana) 2026-07-14 收编。
11. **whale_deep.py** — 大户 ATA 级**全量 decode 深挖**（逐笔对手方/程序/SOL 变动，累积落盘；ATA 发现三级含销户反查+`--known-sig` 手动入口）。与 probe_token_account_history 分工：那个是轻量探查，这个是全量流水落盘供下游脚本消费。来源：PUB(Solana) 2026-07-14 收编。
12. **curve_cost.py** — pump.fun 内盘 bonding curve 成本数学重建（恒定乘积虚拟储备；`--grad-price` 毕业价自校准告警、`--exclude` 剔迁移笔）。**精度注记：枚数逐位精确、SOL 成本标准参数低估约 10%，关键笔须 getTransaction 实付真值校准**（pipeline §8）。来源：PUB(Solana) 2026-07-14 收编。

MINT 来源约定：脚本读 `MINT` 环境变量或工作目录 `config.json` 的 `mint` 字段（铁律 5：标的参数不写死进 skill）。

## 待重建清单（剩余）

1. **解锁款穿透追踪器 `trace_token_flow.py`**（通用）— 给定地址集拉时间窗 SPL 转账建图谱、共用中转检测、终点二分（CEX/囤币）。trace_wallet.py 已覆盖单钱包场景，多址图谱化未做。
2. `market_snapshot.py` — CoinGecko 日线 + Coinglass OI/费率一键快照。
3. `cex_label_book.json` — Solana CEX 钱包标签库（手工累积）。

## 验收标准

首次触及对应场景时按 `references/data-pipeline-solana.md` 逐条验证方法并把脚本沉淀于此（阶段 6 流程）。

## 新增脚本（LAYOFF(Solana) 2026-07-15 收编）

13. **fetch_pool_sigs.py** — 池子/地址签名全史落盘（只拉签名列表不 decode，断点续传按末行 signature 续）。用于评估全史交易量级 + 供 decode_txs 消费；大币龄盘先跑它拿全量签名再抽样/全量 decode。
14. **decode_txs.py**（fast 版）— requests.Session 连接复用逐笔 decode（getTransaction jsonParsed），按 mint 过滤提取 owner 级净变动 + 池子余额锚点（`--pool` 给池 owner 则每笔落 pool_balance）。**直连 api.mainnet-beta 恒 429，必带 `--proxy http://127.0.0.1:7897`**；比 curl 版快约 3 倍。断点续传。
15. **build_evolution.py** — 锚点法阵营演变重建（免全量 SQD）：核心实体逐笔流水累积 + 池子余额锚点插值 + 散户残差 → 图1/图2 数据源。标的参数（total_supply/decimals/launch_ts/data_cutoff_ts/burn_amount）从工作目录 config.json 读。需先备好 entity_camps.json（阵营归属）。
16. **gas_fast.py** — 翻页上限版 gas 溯源（gas_origin.py 的加固版）：`oldest_sigs` 加 max_pages=2 上限，超深高频地址标 approx，避免卡死；落仓户签名少秒完成。**取最早入金 funder 作聚类依据**（非任意交互，规避高频服务热钱包误合并）。
17. **snapshot_diff.py** — /token-update 快照对比法第一步:新旧 holders_owners.json 全量 diff,输出实体逐址变动/大额变动榜(新面孔·清零标注)/新 top30 粗筛。`--entities` 传旧研报实体表 {addr:label}。（来源:CLUDE(Solana) 增量更新,2026-07-15）
18. **probe_window_moves.py** — /token-update 快照对比法第二步:对大额变动地址批量拉窗口内 ATA 签名史,逐笔解析并按对手方分类(pool_buy/pool_sell/direct_transfer),汇总"直转对"识别换仓/洗仓/归集。`--cutoff` 只收 ISO 时间字符串(内部 datetime 解析,禁手算 unix——实战手算错 2 天首跑作废);直转对金额取对手方 |Δ| 口径(本址净额会虚高)。净额一律以快照 diff 为权威。（来源:CLUDE(Solana) 增量更新,2026-07-15）
