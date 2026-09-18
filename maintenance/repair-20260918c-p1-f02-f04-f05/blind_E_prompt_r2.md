# 盲审 E（只读，版本登记 9.0.0 事实核对，非攻击式）—— r2（r1 唯一 FAIL 项为提示词范围口径，本轮修正）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；禁读本目录 `E_done.md`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 盲审 E：PASS` 或 `# 盲审 E：FAIL`。FAIL 时逐条给出：编号（E-B2-NN）、文件:行、事实、后果、建议。
3. 工作目录＝本仓库根；审对象＝`git diff 0f6f4e47a65f HEAD -- VERSION pyproject.toml SKILL.md CHANGELOG.md references scripts commands-staging`（版本登记 commit）。`maintenance/` 目录整体不在审查范围（工单允许的 `E_done.md` 与调度方的提示词/回复文件随时入库，不属四文件议题）。

## 任务
a) 四处版本一致：`VERSION`、`pyproject.toml:15`、`SKILL.md:23`、CHANGELOG 最新索引行与最新详细段标题均为 `9.0.0`；上述限定路径的 diff 只含这四个文件；`SKILL.md` 8021 B 不变；`references/`、`scripts/`、`commands-staging/` 零差异。
b) CHANGELOG 新增索引行与详细段与 `maintenance/repair-20260918c-p1-f02-f04-f05/workorder_E_version.md` §2.4 逐字一致（含插入位置：索引在原 8.0.0 行之前、详细段在原 `## [8.0.0]` 之前且段后空一行）；其他行零改动。
c) 详细段事实抽核（不重评施工）：至少核 6 处可机器验证的断言——三段 diff 行数（`git diff --stat 8b041842 <F04>`/`<F05>`/`<F02>` 各 commit）、`price_receipt_errors`/`PRICE_POINT_STATUSES`/`price_file_sha256`/`circulating_supply_source` 等标识符在 scripts 中存在、索引行提到的拒绝文案在源码中逐字存在、台账 Q15 存在。
d) 实跑：`python3 -B scripts/tests/test_version_consistency.py`（须 PASS 9.0.0）；`python3 -B scripts/tests/changelog_lint.py` 与 `docs_lint.py --all` 若因读 `archive/` 被禁读约束或沙箱阻断，记 `SKIPPED-BY-RULE` 不计 FAIL（调度方本机已跑）。
e) 结论规则：a)/b) 全过、c) 无事实错误、d) 无真实 FAIL → PASS。
