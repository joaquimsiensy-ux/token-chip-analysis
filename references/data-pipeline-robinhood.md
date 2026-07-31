# Robinhood Chain 数据管道（2026-07-12 GME + RAXOL 两次分析实测合并）

Robinhood Chain = Arbitrum Orbit L2（chainid 4663），原生 gas 币 ETH，Uniswap V2/V4 双栈。已知发射台五类：Virtuals Protocol（agent 币，BONDING_V5，坑 3）、NOXA（无 bonding curve，坑 4/4a/9）、Flap（flap.sh，坑 4b）、Uniswap 官方 Liquidity Launchpad（CCA 拍卖，坑 10）、ReflectionToken 外部资产分红盘（坑 15）。

> 通道结论由 GME/RAXOL 两次独立分析合并（曾互相矛盾的记录见 channels 分册修正记录），此后 CASHCAT/Pointless/TRASH/meow/VEX/HAN/BEGGAR/DUMBMONEY/VIRTUAL/COMPUTE/Index 等案持续增补。

---

## 分册路由（主题三分册，本文件只保索引）

> 读法：开局不整读任何分册；按工序/按问题定位到段，再区间读对应分册。原文无 §N 节号，按"段名＋坑编号"定位（坑 1–17 编号在 traps 分册原样保留）。**新增条目必须回填对应分册并同步本表**。链无关通用条目一律在 playbook 三册（entity-cluster-methods / state-anomaly / evidence-wording），本链分册只存 Robinhood 绑定条目。

| 段 | 主题 | 分册文件 |
|---|---|---|
| 通道决策表（HyperSync/Blockscout/公共 RPC/GT/DS/Etherscan V2/Virtuals API/RPC getLogs 备选/死名单） | 采集通道 | `data-pipeline-robinhood-channels.md` |
| 可复用脚本（scripts/robinhood/ 全 14 件：pull_transfers/gas_trace_bs/cost_engine/build_price/V4 采集/429 备选三件套…） | 采集通道 | `data-pipeline-robinhood-channels.md` |
| 修正记录（否定性通道结论纪律实例，retrospective 红线 4 出处） | 采集通道 | `data-pipeline-robinhood-channels.md` |
| 坑 1–2/7–9/17：平台设施（Relay solver/桥别名/V4 单例/零地址充值/7702 账户/Settler） | 链特有的坑 | `data-pipeline-robinhood-traps.md` |
| 坑 3–4b/10–11/15–16：五类发射台结构（Virtuals/NOXA/Flap/Uniswap CCA/Reflection）＋LP NFT 锁仓判别 | 链特有的坑 | `data-pipeline-robinhood-traps.md` |
| 坑 5–6/12–14：内盘毕业价/税币/V4 采集方案与 liqdelta 符号/UniversalRouter 毛量 | 链特有的坑 | `data-pipeline-robinhood-traps.md` |
| 方法论坑（Robinhood 绑定：swap.to 归因/internal-transactions 溯源/gas funder 三步体检操作版/Virtuals 金库判定/0xb92fe 多身份/RelayDepository…） | 分析方法坑 | `data-pipeline-robinhood-methods.md` |

工序速查：选通道拉数据、跑脚本、排障=分册 1（channels）；识别发射台机制、平台设施剔除、金库/LP 锁仓判别=分册 2（traps）；聚类溯源与监控中的本链特有陷阱=分册 3（methods）。
