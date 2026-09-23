# 施工任务：工单 W2 v3（盲审 r1 消化；分支 fix/solana-txv1）

纪律（优先级高于工单正文）：
1. **禁读 `~/.codex`**（启动自动披露除外）；禁读 `~/Documents`、`~/Desktop`。
2. **`.git` 对你只读，git add/commit 由调度方代做**——不要尝试 git 写操作，也不以此停工。开工 `git status --short` 应为空。
3. 按 `maintenance/repair-20260923-solana-txv1/workorder_W2_v3.md` 施工 §1–§4（§5 登记本段不做）；§0 纪律全部适用（白名单、行号不符停工、先红后绿、离线、`MPLCONFIGDIR`）。
4. 定向测试按 W2 §0.5 全部跑并贴尾行（registry 预期 FAIL 记录即可）。
5. 完成写 `W2_done.md`（改动文件:行、与工单差异、尾行、红证据路径、自报禁读），末尾「待调度方 commit」。工单里任何行号/断言与实况不符：停工写明，不猜。
