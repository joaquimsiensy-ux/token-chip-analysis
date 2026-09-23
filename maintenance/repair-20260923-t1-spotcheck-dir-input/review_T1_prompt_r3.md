# 工单 T1 复核提示词 r3（只读，短轮：只核 r2 三条文本意见是否吸收）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260923-t1-spotcheck-dir-input/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/不修改任何文件。报告全文打印到 stdout，首行固定：`# 工单T1复核r3：通过` 或 `# 工单T1复核r3：退回`。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD。

## 任务
`workorder_T1.md` 已升 v3（同目录 `review_T1_reply_r2.md` 为 r2 报告，r2 已判修法/测试/回归面/版本全部通过，仅退回三条工单文本锚纪律）。本轮只核：
a) r2 三条是否逐字吸收：§0.5 非唯一事实行补列（time:422/424、shared:369）；§2.4 文档锚改为代码围栏且工单文件内不再含字面反斜杠（`grep -c '\\\`'` 为 0）、围栏内整行在 `references/data-pipeline-evm-recon.md` 以 `grep -n -F -x` 恰命中 :158、替换后整行 326 B；§2.5 `CHANGELOG.md:13` 完整整行原文在围栏内且恰命中 :13；§2.3 说明④与 §3 措辞按 r2 建议替换。
b) v3 相对 v2 除上述文本外**无其他改动**（用 `git diff HEAD~1 -- maintenance/repair-20260923-t1-spotcheck-dir-input/workorder_T1.md` 核）；修法、白名单、测试、版本档位未变。
c) 施工锚全集最后一次整行核验：time:180/420、shared:1033/1043、tests:99/521、CHANGELOG:99 各恰 1 处且行号一致。
输出：通过/退回 ＋ 逐条结论表。
