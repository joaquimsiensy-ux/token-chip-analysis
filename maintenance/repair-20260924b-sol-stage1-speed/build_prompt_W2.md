# W2 施工提示词（codex --write）
## 纪律（优先级高于工单）
1. 你是施工者。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**只按下方工单 W2（v3.2；v3.1 已通过 codex 复核 r3，v3.2 仅由调度方填实基线、§0.1 形式与事实⑥）施工**，不扩展范围；停工条件触发即停工写报告。派工基线 `W2_BASE=97e888df0a5cfeb88a0b94285475c8845d7aac40`；整行锚按 §0.5 用 `grep -n -F -x -e "<整行>"` 重核（两行以 `-` 开头必须 `-e`）。
2. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程与测试（§0.7 清单之外不跑；`docs_lint.py`/`changelog_lint.py` 由调度方本机跑）。
3. 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree；只写工单 §0.3 白名单文件与完成报告；临时目录只用系统 tempfile；禁止批量删除。
4. 完成报告写到 `maintenance/repair-20260924b-sol-stage1-speed/W2_done.md`，**并把报告全文放在最终答复消息里**。
5. 文档字节预算（§1.2）与 §2.4 三段原文逐字照抄；CHANGELOG 日期 2026-09-24；版本四处等长替换；`SKILL.md` ≤8,192 B。每个施工点改完即跑对应定向测试。

---

# 以下为工单 W2 v3.2 全文

