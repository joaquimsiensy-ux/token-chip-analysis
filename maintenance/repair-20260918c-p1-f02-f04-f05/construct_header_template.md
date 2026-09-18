# 施工任务 __FID__（codex --write，按下方工单 v__VER__ 逐条执行）

## 派工基线
- 派工基线：main 分支、HEAD 为包含本提示词文件的最新提交（本提示词入库后 HEAD 才定，故**不以具体 SHA 判定**）；基线判定只看工单 §0.1 两项检查：`git status --short` 为空，且 `git diff --stat 8b041842 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` __SCRIPTS_STATE__。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先 `git rev-parse HEAD` 记入完成报告即可。
- 本任务是**施工**，不是复核：按工单 §2 逐条落地、按 §0.7 先取 RED、按 §0.8 跑定向测试、按 §3 写完成报告 `__FID___done.md` 到工单所在目录。
- 纪律以工单 §0 为准（禁读 `~/.codex/`、白名单、不 commit/push、禁 stash/checkout/reset、锚不符即停工）。工单已由 codex 只读复核通过（`review___FID___reply_r__RVER__.md`），施工中若发现工单与代码不符，**停工写 `__FID___done_attempt1_stopped.md`**，不得自行改方案。
- stdout 首行固定 `# 施工 __FID__：完成` 或 `# 施工 __FID__：停工`；末尾披露是否读过禁读路径。

---

