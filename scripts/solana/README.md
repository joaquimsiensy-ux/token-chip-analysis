# Solana 脚本资产索引

| path | role | stage | status | fallback |
|---|---|---|---|---|
| `accounting_gate_sol.py` | Solana 记账模型准入 | A0 | 现役硬闸 | BLOCK 后停下补适配器 |
| `scan_token_accounts.py` | 全量账户与 owner 快照 | A1/A2 | 现役主线 | 大响应失败时换 Helius；分片仅验证用 |
| `scan_sharded.py` | amount 字节分片扫描 | A1 | 待更多标的验证 | `scan_token_accounts.py` + Helius |
| `fetch_sqd_transfers_v2.py` | SQD 全量转账边采集 | A1 | 现役主线 | v1 对照或 `window_fetch.py` 补窗口 |
| `fetch_sqd_transfers.py` | SQD v1 同构采集 | A1 | 兼容兜底 | `fetch_sqd_transfers_v2.py` |
| `window_fetch.py` | 高密度窗口定向采集 | A1 | 现役专项 | v2 区域重拉 |
| `fetch_pool_sigs.py` | 地址签名全史落盘 | A1/A3 | 现役 | RPC 换源后续拉 |
| `decode_txs_v2.py` | 批量交易解码与 receipt | A1/A3 | 现役主线 | `decode_txs.py` 逐笔兼容入口 |
| `decode_txs.py` | 逐笔交易解码 | A1/A3 | 兼容入口 | `decode_txs_v2.py` |
| `replay_edges.py` | SQD 边重放、对账与演变 | A2/A3 | 现役标准件 | 修复采集缺口后重放 |
| `audit_closed_accounts.py` | 销户账户覆盖审计 | A2 | 现役审计件 | 切换 sigs/blocks 发现模式 |
| `trace_wallet.py` | 单钱包 owner 级流水 | A3 | 现役探查 | ATA 级脚本 |
| `fast_probe_tops.py` | Top owner 快速画像 | A3 | 现役预筛 | `whale_deep.py` |
| `probe_escrows.py` | escrow/PDA 与 Streamflow 探查 | A3 | 现役专项 | RPC 原始账户解码 |
| `probe_wallet_batch.py` | 批量钱包流水画像 | A3 | 旧案模板 | `whale_deep.py` |
| `probe_token_account_history.py` | ATA 级轻量签名史 | A3 | 旧案模板 | `whale_deep.py` |
| `stake_decode.py` | 质押池逐用户账本闭合 | A3 | 现役专项 | 原始签名史人工复核 |
| `gas_origin.py` | SOL 注资来源批量溯源 | A3 | 现役 | `--full` 深翻 |
| `whale_deep.py` | 大户 ATA 全量流水 | A3 | 现役深挖 | `--known-sig` 补销户 ATA |
| `curve_cost.py` | pump.fun 内盘成本重建 | A3 | 现役专项 | 关键笔取链上实付真值 |
| `build_evolution.py` | 锚点法阵营演变 | A3 | 小样本辅助 | 正式大数据走 `replay_edges.py` |
| `snapshot_diff.py` | 新旧 owner 快照差分 | A3 | 现役更新件 | 全量重放复核 |
| `probe_window_moves.py` | 快照窗口流转分类 | A3 | 现役更新件 | ATA 全量解码 |
| `anchor_sampler.py` | SQD 日级锚点采样 | A3 | 辅助信号 | 快照或全流水兜底阴性结论 |
| `squads_members.py` | Squads v4 控制成员解析 | A3 | 现役身份件 | 对照官方布局手工复核 |
| `hypersync_recon.py` | HyperSync GA 后重验收 | A1/A2 | 禁用通道验收专用 | 正式采集继续用 SQD |

MINT 来源约定：支持 mint 参数的脚本读取 `MINT` 环境变量或工作目录 `config.json` 的 `mint` 字段；若脚本提供 `--mint`，显式参数优先。标的参数不得写死进 skill。

方法、边界与验收细节按阶段查 `references/data-pipeline-solana.md` 的对应分册；本文件只登记资产状态，不承载案例、版本史或 backlog。
