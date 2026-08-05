# EVM 链数据管道实测手册（BSC/Base/Arbitrum，2026-07 实测版）

> 通道结论由多次 BSC 实战合并（OPN/SIREN，07 起）。
> 所有限速/吞吐数字为当时实测，节点政策随时会变；复用任何通道前先按 §6 做 1 分钟能力探测。

---

## 分册路由（主题三分册，本文件只保索引）

> 读法：开局不整读任何分册；按工序/按问题定位到节，再区间读对应分册（正文 §N 节号沿用本表，跨分册引用按本表定位）。**新增章节必须同步回填本表**。

| 节 | 主题 | 分册文件 |
|---|---|---|
| §1 全量转账通道决策树（含通道表/断点续拉） | 采集通道 | `data-pipeline-evm-channels.md` |
| §2 死亡名单（实测不可用，3 个月内禁止重探） | 采集通道 | `data-pipeline-evm-channels.md` |
| §3 各通道操作细节（HyperSync/Alchemy/bloXroute/Etherscan/Multicall3） | 采集通道 | `data-pipeline-evm-channels.md` |
| §6 BSC 专属坑表 | 采集通道 | `data-pipeline-evm-channels.md` |
| §7 零门槛免注册通道（48club/BscScan 直抓/mevblocker/省请求取证/三段拼接/CEX 黑箱通道） | 采集通道 | `data-pipeline-evm-channels.md` |
| §4 辅助数据面速查表（价格/K线/标签/安全审计/gmgn-cli 坑） | 数据面与链专节 | `data-pipeline-evm-sources.md` |
| §8 Base 链专节（8.1 双通道拓扑/8.2 辅助面/8.3 V4/8.4a Zora/8.4 x402） | 数据面与链专节 | `data-pipeline-evm-sources.md` |
| §9 Arbitrum 链专节 | 数据面与链专节 | `data-pipeline-evm-sources.md` |
| §10 质押型代币标的范式（方法链无关） | 数据面与链专节 | `data-pipeline-evm-sources.md` |
| §5 对账 gate（四件套+重放前置完整性+差额排查 Burn/Mint） | 对账与重放 | `data-pipeline-evm-recon.md` |
| §11 公共数仓准入实证与分工定稿（BigQuery/AWS/新源准入纪律） | 对账与重放 | `data-pipeline-evm-recon.md` |
| §12 DuckDB 重放/缩图引擎（亿级样本主路径） | 对账与重放 | `data-pipeline-evm-recon.md` |
| §13 时间抽查第二源分层选型（默认 time_spotcheck.py 锚点直查；全史重拉仅例外且先 pilot 报 ETA；勿用区块浏览器 API） | 对账与重放 | `data-pipeline-evm-recon.md` |

工序速查：选通道拉数据、踩坑排障=分册 1（channels）；分析期查辅助数据源、Base/Arbitrum/质押型标的=分册 2（sources）；采集完对账、出错复核切源、亿级重放缩图=分册 3（recon）。
