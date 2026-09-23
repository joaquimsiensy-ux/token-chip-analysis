# 工单 W3 v2 — 盲审 r2 唯一 P2 消化：前代 digest 负向向量须真正进入摘要重算

> v2 吸收 codex 复核 r1（`review_W3_r1_report.md`，通过）：改法定为 `wrong_digest` 版；隔离证据按单次 deep_check 计数并记参数；"一处改动"限定为测试 diff；开工树干净由调度方先归档复核件保证。
> 来源：`blind_review_W1_r2_report.md`（PASS，P0/P1 0，P2 1）。E27(d) 深验篡改循环里「改 `predecessor_plan_digest` 为 `"0"*16`」的向量（`scripts/tests/test_sqd_gap_repair.py:987`，锚 `rows[0]["adopted"].update(predecessor_plan_digest="0" * 16)`）保留原 `source`，因此先被 `solana_exact_validate.py:1353` 的「source == pending-<digest>」等式拒绝，从未到达 `_plan_digest_from_generation` 重算；该向量名义上测"前代 digest 重算拒绝伪值"，实际测的是目录名绑定，与 `change_source` 向量重复。

## 0. 纪律
- 分支 `fix/solana-txv1`；开工 `git status --short` 为空，HEAD 为 `e44551a` 的后代且 `git diff --stat e44551a HEAD` 只含 `maintenance/`；`.git` 只读、commit 由调度方代做（不以此停工）；禁读 `~/.codex`（启动披露除外）、`~/Documents`、`~/Desktop`；离线；`MPLCONFIGDIR=$HOME/.matplotlib PYTHONDONTWRITEBYTECODE=1`。
- 白名单：仅 `scripts/tests/test_sqd_gap_repair.py` 与本目录 `W3_done.md`。生产代码零改动。

## 1. 改动（一处）
`:987` 的 lambda 改为同时改两个字段，使 source 等式成立、只剩摘要重算能拒绝：
`lambda rows: rows[0]["adopted"].update(predecessor_plan_digest=wrong_digest, source="pending-" + wrong_digest)`（复用 `:974` 的 `wrong_digest`）。期望 reason 仍为 `"adopted record invalid"` 子串（生产端 `solana_exact_validate.py:1534`，前代摘要比较在 `:1529`）。

## 2. 证据
- 先红后绿的"红"在此不适用（该向量改前改后都 FAIL 预期通过）；改为**隔离证据**：用一段临时内存核验脚本（`unittest.mock.patch(..., wraps=真实函数)` 包住 `solana_exact_validate._plan_digest_from_generation`，不改仓库文件），从同一有效 gen 复制两份输入，分别施加旧向量与新向量并照原循环更新台账外层 size/sha256，各自独立重置 spy 后只跑**那一次** `validate_repair_bundle_deep`：旧向量调用 0 次；新向量调用 2 次，参数依次为当前代 sha 与前代 sha；两者 reasons 均含原子串。把两组计数与参数写进 `W3_done.md`。同时断言 `wrong_digest` 既不等于当前代 digest 也不等于真实前代 digest。
- `test_sqd_gap_repair.py` 尾行 GREEN；测试代码 `git diff --stat` 只含 `scripts/tests/test_sqd_gap_repair.py` 一处改动（`W3_done.md` 为新增交付件，不计）。

## 3. 完成
写 `W3_done.md`（改动行、隔离计数、尾行、自报禁读），末尾「待调度方 commit」。
