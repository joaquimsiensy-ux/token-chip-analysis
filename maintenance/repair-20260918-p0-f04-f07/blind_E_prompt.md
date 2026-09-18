# 盲审 E（r1）提示词（只读，版本登记施工后独立复核）
# 审查范围 commit＝git diff 5e335b2..66d02ef（E 施工 commit 66d02ef：CHANGELOG.md / SKILL.md / VERSION / pyproject.toml ＋ E_done.md）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改文件。报告全文打印到 stdout，首行固定 `# 盲审 E：PASS` 或 `# 盲审 E：FAIL`。FAIL 时逐条给：编号（E-B1-NN）、严重度（blocker/minor/nit）、位置 path:line、事实、修法建议。PASS 时列出实际核过的项与未实跑的项。
3. 这是常规盲审，不是攻击式验收。

## 任务
- 对照 `maintenance/repair-20260918-p0-f04-f07/workorder_E_version.md`（v2）§2：四处版本号是否全为 7.2.1、CHANGELOG 两处插入是否逐字与工单代码块一致、插入位置是否正确（索引行在 7.2.0 行之前、详细段在 `## [7.2.0]` 之前且段后空一行）、其他行零改动、`references/`、`scripts/` 零改动。
- 条目文案与仓库事实：抽核 CHANGELOG 新条目中引用的函数/常量/测试名与计数是否与源码一致（可复用 `review_E_reply_r1.md`/`_r2.md` 已核项，只需确认施工未走样）；有无代币分析结论（红线）。
- `E_done.md` 报告是否如实（diff 行数、test_version_consistency 输出、SKILL 字节）。
- 调度方本机已跑：changelog_lint 活跃 77 条 PASS、docs_lint 与 --all PASS、casebook_lint、test_version_consistency、test_g3_docs_guards、test_sixlens_docs、test_commands_deploy_sync、test_contract_routes 全 PASS；沙箱能跑的自行复跑，不能跑的列为未实跑。
