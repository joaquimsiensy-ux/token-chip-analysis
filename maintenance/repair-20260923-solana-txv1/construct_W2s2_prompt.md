# 施工任务：工单 W2 第 2 段（登记本更新；分支 fix/solana-txv1）

纪律（优先级高于工单正文）：
1. **禁读 `~/.codex`**（启动自动披露除外）；禁读 `~/Documents`、`~/Desktop`。
2. **`.git` 对你只读，git add/commit 由调度方代做**——不要尝试 git 写操作，也不以此停工。开工 `git status --short` 应为空，HEAD 应为 `9e6c8ced7db910e8de52c950e988451ca0528591`（仅比代码提交多一个施工提示词文件；登记的 `commit` 用代码提交 `7846184f9f2ba758027cd6c5ddb1b21e87b3c16f`，两个提交下 `sqd_gap_repair.py` 的 sha256 相同，可自行 `git show` 复核）。
3. 离线；所有 Python 验证设 `MPLCONFIGDIR=$HOME/.matplotlib PYTHONDONTWRITEBYTECODE=1`。
4. 白名单：仅 `scripts/lib/producer_history.py` 与本目录 `W2s2_done.md`。

任务（`workorder_W2_v3.md` §5）：
- 先复核：`git show 7846184f9f2ba758027cd6c5ddb1b21e87b3c16f:scripts/solana/sqd_gap_repair.py | shasum -a 256` 必须等于 `3f89aab13054be76711d85d15a3e4f21d6113c35c905f55a8e60edb31ba8446b`；不等即停工写明。
- `scripts/lib/producer_history.py` 中四条 9.1.0 条目（`sqd-solana-cache/v4`、`sqd-solana-repair-bundle/v1`、`sqd-solana-coverage-resolution/v1` 及第四条协议）的 `sha256` 由 `977a4823f819559de070e53be681a66808861deb602fed108aa027c5af88c0c7` **替换**为 `3f89aab13054be76711d85d15a3e4f21d6113c35c905f55a8e60edb31ba8446b`，`commit` 由 `a1f1594a144a9042a529e8c829e4afd2c63e7633` **替换**为 `7846184f9f2ba758027cd6c5ddb1b21e87b3c16f`。是替换不是追加（977a4823… 从未发布）。reason 文案不动。全文件不得再残留旧值（`grep -c 977a4823` 与 `grep -c a1f1594a` 均为 0）。
- 验证并贴尾行：`scripts/tests/test_producer_registry_current.py`（须 PASS）、`scripts/tests/test_sqd_gap_repair.py`、`scripts/tests/invariant_scan.py`。
- 完成写 `maintenance/repair-20260923-solana-txv1/W2s2_done.md`（改动行、尾行、自报禁读），末尾「待调度方 commit」。
