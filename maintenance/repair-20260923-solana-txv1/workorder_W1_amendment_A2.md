# 工单 W1 勘误 A2（调度方裁决，2026-09-23）— 认领函数登记为原子写入点；§3 的 commit 哈希

**事实**：§2 按 v5 实现的 `adopt_predecessor_pending`（`scripts/solana/sqd_gap_repair.py`）含直接 `os.link`，`invariant_scan.py:1113-1114` 把它登记为原子写入点，`:1302-1303` 报 `atomic_writes: code point missing from manifest: ('scripts/solana/sqd_gap_repair.py', 'adopt_predecessor_pending')`。§0.4 把 `invariant_manifest` 列为不改项过严——该 manifest 正是原子写入点的登记表，新增合法写入点就应登记。

**裁决**：
1. §0.4 放开 `scripts/tests/invariant_manifest.json` **仅限新增一条**：照 `:1186-1190`（锚 `"locator": "main", "script": "scripts/solana/sqd_gap_repair.py", "semantics": "multi_file_txn"`）格式，追加 `{"locator": "adopt_predecessor_pending", "script": "scripts/solana/sqd_gap_repair.py", "semantics": "multi_file_txn"}`（多文件事务：多份证据链接＋一份台账原子发布）。若扫描器对 semantics 另有与实现不符的校验，停工汇报，不要硬凑。放置位置与排序照 manifest 既有约定（若有排序校验以其为准）。
2. `invariant_scan.py` 须 exit 0（零不符）。
3. **§3 登记参数**：代码 commit = `a1f1594a144a9042a529e8c829e4afd2c63e7633`；该 commit 下 `scripts/solana/sqd_gap_repair.py` 的 sha256 = `977a4823f819559de070e53be681a66808861deb602fed108aa027c5af88c0c7`（施工前用 `git show a1f1594a144a9042a529e8c829e4afd2c63e7633:scripts/solana/sqd_gap_repair.py | shasum -a 256` 复核；不一致即停工）。四条条目 reason 照 v5 §3。
4. §5 文档措辞中常量归属写 `endpoint_identity.SOLANA_MAX_SUPPORTED_TX_VERSION`（勘误 A1 第 4 条）。

**A2.1 备注（调度方）**：本文件首版因 shell 展开错误写成空文件、且随后计算出的 sha 为空输入哈希（e3b0c442…），据此派出的两个 codex 任务均已取消，未产生任何改动；本版数值已用 `git show <commit>:<path> | shasum -a 256` 复核。
