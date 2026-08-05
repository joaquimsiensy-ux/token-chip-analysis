# Solana 数据管线（SPL 代币筹码分析）

> **来源声明：本文档以 IO 分析会话实录逐条核验为底（含实录才有、反推不可能推出的坑：双 RPC 互补矩阵、方法级屏蔽、签名列表投毒等）。scan 分册规则默认＝实录已确认，仅例外才标注：**
> - `[INFERRED]` = 仍未经实录/复现验证的遗留条目，用前核实
> - `[实测·他场景]` = 本机其他项目实测过的工具性事实（见 api-keys.md / memory），可信度高
> - `[知识补充]` = SPL 通用常量与标准手法，用前顺手核实
> - `[VERIFIED·XX实战]` / `[07-12 本机直连实测]` = 后续案例或本机补充确认

---

## 分册路由（主题两分册，本文件只保索引）

> 读法：按工序定位到节，再区间读对应分册（正文 §N 节号沿用本表，跨分册引用按本表定位；标注图例见上方约定）。**新增章节必须同步回填本表**。

| 节 | 主题 | 分册文件 |
|---|---|---|
| §0 通道速查 / §0a 双公共 RPC 互补矩阵 / §0b 免费通道死亡名单 | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §1 全量持仓扫描（getProgramAccounts + owner 去重） | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §2 托管类型判别 / §2a 自建质押托管合约判别五步法 | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §3 行为特征识别库 / §3a 流水追踪坑（签名投毒/ATA 级 trace 等） / §3b 控盘团伙识别指纹 | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §4 辅助数据面（GMGN/RugCheck/Vybe/CMC/解锁表等） | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §5 架构约束与观测边界（报告局限性声明必写） | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §6 脚本资产（原待重建清单，已建成收拢） / §7 验证清单 | 采集与重建 | `data-pipeline-solana-capture.md` |
| §8 后续实测补充（SQD 全量转账首选/铸造边全清单/curve 成本重建） | 采集与重建 | `data-pipeline-solana-capture.md` |
| §9 锚点法演变重建 + gas 溯源加固 | 采集与重建 | `data-pipeline-solana-capture.md` |
| §10 快照对比法（已有快照之间的窗口流转复核） | 采集与重建 | `data-pipeline-solana-capture.md` |
| §11 长币龄混合重建 + 高密度期定向采集 | 采集与重建 | `data-pipeline-solana-capture.md` |
| §12 销户账户覆盖审计 | 采集与重建 | `data-pipeline-solana-capture.md` |
| §13 采集加速工程（13a 传输层/13b 采集器 v2/13c 解码 v2/13d Solana HyperSync 通道·已禁用） | 采集与重建 | `data-pipeline-solana-capture.md` |
| §14 日级余额快照重建法（取代锚点法做长币龄演变） | 采集与重建 | `data-pipeline-solana-capture.md` |
| §15 pump.fun 长内盘期全量重建（签名史双索引法） | 采集与重建 | `data-pipeline-solana-capture.md` |

工序速查：当前快照/托管判别/行为定性/辅助数据源/局限性声明=分册 1（scan）；全量转账采集、演变重建、增量更新、销户对账加固、加速工程=分册 2（capture）。
