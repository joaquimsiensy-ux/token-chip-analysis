# 存量 evm_v2 台账盘点（codex 只读，2026-08-24，发版前）

扫描根：/Users/uravvv/Documents/5.6筹码分析/ ＋ /Users/uravvv/Desktop/老公用/fable筹码分析/（provenance_ledger.json，maxdepth 4）
共 12 份 ledger：4 份 evm_v2＋8 份 duckdb（duckdb 不受 F-008 集合闸影响，未深查）。

evm_v2 四案逐一核对（按新集合闸命中规则：argument 目录下 run_ 前缀真实子目录内 logs.parquet/blocks.parquet，不跟随 symlink）：
- TAG分析：一致（磁盘 2=ledger 2，双向差集空）
- LIT分析：一致（同上）
- AKE分析：一致（同上）
- APU分析0801：一致（同上）
无 argument 目录缺失案、无 symlink/非普通文件异常。

结论：**当前零存量案需要仅因 stale-ledger 集合闸而重跑 provenance**。
盘点方保留意见（原文）：本结果仅审计 evm_v2 输入文件集合闸，不代表其他哈希/schema/发布门禁也通过——"集合一致"≠"一定能重 freeze"。
