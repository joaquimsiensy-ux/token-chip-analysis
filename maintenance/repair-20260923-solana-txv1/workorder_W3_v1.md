# 工单 W3 v1 — 盲审 r2 唯一 P2 消化：前代 digest 负向向量须真正进入摘要重算

> 来源：`blind_review_W1_r2_report.md`（PASS，P0/P1 0，P2 1）。E27(d) 深验篡改循环里「改 `predecessor_plan_digest` 为 `"0"*16`」的向量（`scripts/tests/test_sqd_gap_repair.py:987`，锚 `rows[0]["adopted"].update(predecessor_plan_digest="0" * 16)`）保留原 `source`，因此先被 `solana_exact_validate.py:1353` 的「source == pending-<digest>」等式拒绝，从未到达 `_plan_digest_from_generation` 重算；该向量名义上测"前代 digest 重算拒绝伪值"，实际测的是目录名绑定，与 `change_source` 向量重复。

## 0. 纪律
- 分支 `fix/solana-txv1`；开工 `git status --short` 为空，HEAD 为 `e44551a` 的后代且 `git diff --stat e44551a HEAD` 只含 `maintenance/`；`.git` 只读、commit 由调度方代做（不以此停工）；禁读 `~/.codex`（启动披露除外）、`~/Documents`、`~/Desktop`；离线；`MPLCONFIGDIR=$HOME/.matplotlib PYTHONDONTWRITEBYTECODE=1`。
- 白名单：仅 `scripts/tests/test_sqd_gap_repair.py` 与本目录 `W3_done.md`。生产代码零改动。

## 1. 改动（一处）
`:987` 的 lambda 改为同时改两个字段，使 source 等式成立、只剩摘要重算能拒绝：
`lambda rows: rows[0]["adopted"].update(predecessor_plan_digest="0" * 16, source="pending-" + "0" * 16)`
（`"0"*16` 与真实前代 digest 相等的概率可忽略，但为与 `:974` 的 `wrong_digest` 一致，允许改用 `wrong_digest` 变量：`update(predecessor_plan_digest=wrong_digest, source="pending-" + wrong_digest)`；二选一，勿两处都写。）期望 reason 仍为 `"adopted record invalid"` 子串。

## 2. 证据
- 先红后绿的"红"在此不适用（该向量当前也 FAIL 预期通过）；改为**隔离证据**：在改动前后各跑一次该测试并临时（仅内存 monkeypatch，不改仓库文件）计数 `solana_exact_validate._plan_digest_from_generation` 被调用次数——改前该向量 0 次，改后 ≥1 次；把两次计数写进 `W3_done.md`。
- `test_sqd_gap_repair.py` 尾行 GREEN；`git diff --stat` 只含一个文件一处改动。

## 3. 完成
写 `W3_done.md`（改动行、隔离计数、尾行、自报禁读），末尾「待调度方 commit」。
