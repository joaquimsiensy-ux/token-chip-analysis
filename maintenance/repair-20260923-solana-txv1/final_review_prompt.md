# 收官 review：分支 fix/solana-txv1 是否真正解决原问题（vs main）

纪律：**只读**，不改文件、不 commit；禁读 `~/.codex`（启动自动披露除外）、`~/Documents`、`~/Desktop`；离线（不得调用任何 RPC）。报告**作为最终回复文本直接输出**，首行 `# 收官 review: PASS / FAIL`。

原问题（PYTHIA-SKILL-001）：Solana 主网出现交易版本 1；本 skill 13 个 Solana 脚本 17 处把 `maxSupportedTransactionVersion` 写死 0，`scripts/solana/sqd_gap_repair.py repair` 遇含版本 1 交易的区块报 RPC -32015 后退出，且 plan_digest 绑 producer sha，改码后旧 pending（已成功拉取的十几万 slot 证据）无法续用。用户批准的修复目标：①常量化且不再写死；②新增「经审计的前代 pending 认领」机制（`--resume --adopt-pending`）；③中文文档同步；④能删不加、能改不加。

本轮不是再找新缺陷的盲审，而是**终局确认**。请独立做以下四件事并逐项给证据（文件:行 / 命令尾行）：
1. **原问题已解**：在 `git diff main...HEAD` 中确认修复 producer 的 getBlock 请求体使用 `endpoint_identity.SOLANA_MAX_SUPPORTED_TX_VERSION`（=1），`grep -rn "maxSupportedTransactionVersion" scripts` 无写死数字；写一段不联网的复现：用 monkeypatch/夹具让 `_rpc_body`/`repair_getblock_body` 输出的 JSON 里 `maxSupportedTransactionVersion == 1`；并确认 `invariant_scan.py` 的 `hardcoded_tx_version_errors` 守卫对注入写死 0 的临时副本会报错（只在内存/临时目录验证，不改仓库文件）。
2. **认领机制可用且不弱化防伪**：跑 `MPLCONFIGDIR=$HOME/.matplotlib python3 -B scripts/tests/test_sqd_gap_repair.py` 贴尾行；读 E27(d) 断言，确认它覆盖：正向认领后剩余 slot 只拉未完成部分、认领记录在续跑/发布/深验三处被重算与校验（前代 digest、候选前缀、来源目录名、参考源指纹）、篡改向量被拒且恢复后正向通过。指出任何"自证"（断言与被测代码共用同一函数计算期望值）的地方。
3. **回归与登记**：`test_batch8_repair_scale.py`、`test_batch7_validator_coverage_gaps.py`、`invariant_scan.py`、`test_producer_registry_current.py`、`changelog_lint.py`、`docs_lint.py --all`、`test_version_consistency.py` 尾行；确认 `producer_history.py` 9.1.0 四条条目的 sha256 等于 `git show <其 commit>:scripts/solana/sqd_gap_repair.py | shasum -a 256`，且等于当前 HEAD 该文件的 sha256。
4. **文档一致**：`CHANGELOG.md` 9.1.0、`references/scan-schemas.md` §14.8、`references/data-pipeline-solana-capture.md` 中对认领机制的中文描述与代码行为逐条对照，列出任何夸大、缺失或相互矛盾之处；确认没有施工过程叙述混入用户文档。

输出：总判定；逐项证据；仍存在的 P0/P1（导致原问题未解或防伪弱化/回归）→ FAIL；仅 P2（措辞）→ PASS 并列出建议。
