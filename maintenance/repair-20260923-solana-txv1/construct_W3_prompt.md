# 施工任务：工单 W3 v2（盲审 r2 P2 消化；分支 fix/solana-txv1）

纪律（优先级高于工单正文）：
1. **禁读 `~/.codex`**（启动自动披露除外）；禁读 `~/Documents`、`~/Desktop`。
2. **`.git` 对你只读，git add/commit 由调度方代做**——不要尝试 git 写操作，也不以此停工。开工 `git status --short` 应为空；HEAD 是 `e44551a` 的后代且 `git diff --stat e44551a HEAD` 只含 `maintenance/`（不核对具体 HEAD 哈希）。
3. 按 `maintenance/repair-20260923-solana-txv1/workorder_W3_v2.md` 施工 §1–§3；§0 纪律全部适用（白名单、离线、`MPLCONFIGDIR`）。
4. 隔离核验脚本只放内存或本目录外的临时位置，不入仓库；若沙箱禁止写 `/private/tmp`，用 `tempfile` 指向仓库内 `.staging_b3/`（已被 gitignore）或改为纯内存路径，不以此停工。
5. 完成写 `W3_done.md`（改动行、隔离计数与参数、尾行、自报禁读），末尾「待调度方 commit」。工单里任何行号/断言与实况不符：停工写明，不猜。
