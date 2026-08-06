# Solana SQD v1 采集器（已退役）

2026-08-06 第四轮瘦身退役；新案禁止启用。

正式主线见 `scripts/solana/fetch_sqd_transfers_v2.py`（sha256 缓存路径＋`sqd-solana-cache/v3` meta）。
本目录的 v1 采集器写小写 mint 路径与旧 meta 格式，v2 与 `replay_edges.py` 均不消费；
若需恢复旧 v1 缓存，须先写一次性 importer 转换为 v3 identity 并过对账验收。
