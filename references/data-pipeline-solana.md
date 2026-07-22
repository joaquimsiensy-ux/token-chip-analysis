# Solana 数据管线（SPL 代币筹码分析）

> **来源声明（2026-07-12 修订）：本文档原自 IO 分析最终报告反推。IO 原始会话记录（Windows 电脑 jsonl，含全部思考过程与命令实录）已于 2026-07-12 由用户找回，全文经逐条比对核验：原 `[INFERRED]` 条目凡实录确认的已改标 `[VERIFIED·IO实录]`，并据实录补入反推不可能推出的坑（双 RPC 互补矩阵、方法级屏蔽、签名列表投毒等）。**
>
> 标注约定：
> - `[VERIFIED·IO实录]` = IO 会话命令与返回实录直接确认，可信度最高
> - `[INFERRED]` = 仍未经实录/复现验证的遗留条目，用前核实
> - `[实测·他场景]` = 本机其他项目实测过的工具性事实（见 api-keys.md / memory），可信度高
> - `[知识补充]` = SPL 通用常量与标准手法，用前顺手核实

---

## 分册路由（2026-07-22 D3 整编：主题两分册，本文件只保索引）

> 读法：按工序定位到节，再区间读对应分册。分册内规则逐条原样迁移自单文件版（2026-07-22 拆分，零改写；正文 §N 节号沿用本表，跨分册引用按本表定位；标注图例见上方约定）。

| 节 | 主题 | 分册文件 |
|---|---|---|
| §0 通道速查 / §0a 双公共 RPC 互补矩阵 / §0b 免费通道死亡名单 | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §1 全量持仓扫描（getProgramAccounts + owner 去重） | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §2 托管类型判别 / §2a 自建质押托管合约判别五步法 | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §3 行为特征识别库 / §3a 流水追踪坑（签名投毒/ATA 级 trace 等） / §3b 控盘团伙识别指纹 | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §4 辅助数据面（GMGN/RugCheck/Vybe/CMC/解锁表等） | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §5 架构约束与观测边界（报告局限性声明必写） | 扫描与判别 | `data-pipeline-solana-scan.md` |
| §6 待重建脚本清单 / §7 验证清单 | 采集与重建 | `data-pipeline-solana-capture.md` |
| §8 后续实测补充（SQD 全量转账首选/铸造边全清单/curve 成本重建） | 采集与重建 | `data-pipeline-solana-capture.md` |
| §9 锚点法演变重建 + gas 溯源加固 | 采集与重建 | `data-pipeline-solana-capture.md` |
| §10 快照对比法增量更新（/token-update 的 Solana 特化） | 采集与重建 | `data-pipeline-solana-capture.md` |
| §11 长币龄混合重建 + 高密度期定向采集 | 采集与重建 | `data-pipeline-solana-capture.md` |
| §12 销户账户覆盖审计 | 采集与重建 | `data-pipeline-solana-capture.md` |
| §13 采集加速工程（13a 传输层/13b 采集器 v2/13c 解码 v2/13d Solana HyperSync 通道） | 采集与重建 | `data-pipeline-solana-capture.md` |

工序速查：当前快照/托管判别/行为定性/辅助数据源/局限性声明=分册 1（scan）；全量转账采集、演变重建、增量更新、销户对账加固、加速工程=分册 2（capture）。
