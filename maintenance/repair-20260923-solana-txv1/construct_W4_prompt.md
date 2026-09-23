# 施工任务：工单 W4（纯文档措辞订正；分支 fix/solana-txv1）

纪律（优先级高于工单正文）：
1. **禁读 `~/.codex`**（启动自动披露除外）；禁读 `~/Documents`、`~/Desktop`。
2. **`.git` 对你只读，git add/commit 由调度方代做**——不要尝试 git 写操作，也不以此停工。开工 `git status --short` 应为空。
3. 按 `maintenance/repair-20260923-solana-txv1/` 下**版本号最高**的 `workorder_W4_v*.md` 施工 §1–§3；§0 纪律全部适用。
4. 锚文本用 `grep -nF -e "<锚>"` 核对唯一命中后再改；任何锚不唯一或行为核对不符：停工写明，不猜。
5. 完成写 `W4_done.md`，末尾「待调度方 commit」。
