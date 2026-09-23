# 工单 W1 勘误 A1（调度方裁决，2026-09-23）— 常量落点改为 `scripts/lib/endpoint_identity.py`

**事实**：§1 按 v5 施工后，`scripts/tests/invariant_scan.py:1190/1220`（锚 `has_solana_session |= node.module == "solana_attested_session"` → `transports.add("solana-attested-session")`）把任何 `from solana_attested_session import …` 都判为接入 RPC 传输通道，12 个只导入常量的文件被报 `transport_calls: code point missing from manifest`。manifest 属 §0.4 不改项，且这些文件并未使用 session 传输——是工单定形错误。

**裁决（最小改动）**：
1. `SOLANA_MAX_SUPPORTED_TX_VERSION = 1`（连同 v5 §1.1 那三行中文注释）改放 `scripts/lib/endpoint_identity.py`（纯标准库叶子模块，`:3-7` 只 import hashlib/re/urllib.parse；已被 session `:10`、net `:40` 引用；扫描器不把它归为传输）。`solana_attested_session.py` 不再放该常量，且**撤销**其 `:10` 的 try/except 导入回退（恢复原行）。
2. 所有导入改为 `from endpoint_identity import SOLANA_MAX_SUPPORTED_TX_VERSION`：`solana_exact_validate.py` 用其既有 try/except 相对导入写法；`solana_observation.py:16` 已 `from endpoint_identity import endpoint_fingerprint` → 加名字，撤销对 session 导入行的改动；`sqd_gap_repair.py:24` 已 `from endpoint_identity import (endpoint_fingerprint, public_endpoint,` → 加名字，撤销新增的 session 导入行；其余 10 个 `scripts/solana/*.py`（audit_closed_accounts、decode_txs、decode_txs_v2、fast_probe_tops、gas_origin、probe_escrows、probe_window_moves、stake_decode、trace_wallet、whale_deep；数量按 `rg -n "from solana_attested_session import SOLANA_MAX_SUPPORTED_TX_VERSION" scripts/solana` 实况为准）把导入模块名改为 `endpoint_identity`（`decode_txs.py` 新增的 `sys.path` 行保留）。
3. 验收标准改为：`python3 -B scripts/tests/invariant_scan.py` 退出 0（transport_calls 零不符）；隔离导入检查改为 `python3 -c "import scripts.lib.endpoint_identity, scripts.lib.solana_exact_validate"`。红证据④（session 包导入失败）作废，改记「常量在 session 时 invariant_scan 报 12 条 transport_calls 不符」作为本勘误依据。
4. 文档措辞（§1.1 注释、§5 capture.md 句子、CHANGELOG）中的常量归属一律写 `endpoint_identity.SOLANA_MAX_SUPPORTED_TX_VERSION`。

**A1.1 勘误（调度方，第 2 段停工后）**：第 2 条原写「其余 11 个」，实为 10 个（`sqd_gap_repair.py` 已单列），已订正。
