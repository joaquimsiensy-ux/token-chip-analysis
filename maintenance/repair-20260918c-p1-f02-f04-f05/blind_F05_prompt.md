# 盲审 F05（只读，常规盲审，非攻击式）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；**禁读 `F05_done.md` 与 `F05_red_evidence.txt`**（盲审不看施工方自述，独立判断）。豁免：d) 项测试自身以子进程访问历史 maintenance 目录属测试依赖，允许原样运行，审方本人不主动打开那些历史文件。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 盲审 F05：PASS` 或 `# 盲审 F05：FAIL`。FAIL 时逐条给出：编号（F05-B1-NN）、文件:行、事实、后果、建议。PASS 时列出实际核过的项与实跑的命令/结果尾行。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，以当前 HEAD 为审对象；施工 diff＝`git diff __BASE__ HEAD -- scripts`。`maintenance/` 目录整体不在审查范围。

## 任务
审 F05 施工是否**真正解决**了 review 反例并符合工单 v3（`maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md`）：
a) **终点判据（必做，独立复现）**：`ruling_20260918.md` 的 `price_gate_content` 反例——用真实 `scripts/prices/price_check.py`（第二源离线替身）对主 50/副 100 生成三点 FAIL 收据（退出 2），把它绑进一份其余合法的 −2 工单 `bindings.price_source_checks`，HEAD 下 `stage2_closeout check` 是否 BLOCK（拒在哪一行、哪句文案）。再核：手改收据 `verdict` 为 PASS 但 points 仍 FAIL → 拒；`price_file_sha256` 与 `bindings.price_source.sha256` 不一致 → 拒；旧格式收据（无 `price_file_sha256`）→ 拒；ALL_SKIP 收据 → 拒；内联 `dual_source_check` 纯申报 dict（无 `receipt`）→ 拒；WARN 收据 → 放行且 NOTE 记 WARN 点数。请自行构造夹具（可复用 `test_stage2_closeout.py` 的 `build_closeout_case`），不得只依赖新增测试的断言。
b) 修法与工单一致：`price_check.py` 只多 `price_file_sha256` 一键、stdout/退出码不变；`stage2_closeout.py` 新增 `price_receipt_errors` 的 verdict 重算规则与 `price_check.py` 汇总规则一致（PASS/WARN/FAIL/ALL_SKIP 340 组合法状态组合可抽样核）；closeout 收据仍 12 项 checks；`workorder_errors` 返回类型不变、`WORKORDER BLOCK: ` 前缀不变；`workorder_reference_contracts` 的 19 条既有 mutation 仍 BLOCK 且文案含 field 名。
c) 白名单：**只核 `git diff --stat __BASE__ HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`**，须恰为 `scripts/prices/price_check.py`、`scripts/report/stage2_closeout.py`、`scripts/tests/test_stage2_closeout.py` 三文件；`SKILL.md` 8021 B、`references/**/*.md` 合计 930076 B、`commands-staging/*.md` 合计 8798 B 不变。
d) 实跑（贴尾行）。**沙箱口径**：若某测试因只读沙箱临时目录不可写而报 `No usable temporary directory found`，记为 `SANDBOX-BLOCKED`（贴该错误行）而**不计 FAIL**——由调度方本机补验；能跑的须 PASS。可先 `python3 -c "import tempfile;print(tempfile.gettempdir())"` 自检。命令：`python3 -B scripts/tests/test_stage2_closeout.py`、`test_a4_gate.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`python3 -B scripts/tests/invariant_scan.py`。**不跑 `test_stage2_reseal.py`**（硬依赖预建验收 worktree，调度方本机补验）。
e) 结论规则：a)/b)/c) 全过且 d) 无真实 FAIL（SANDBOX-BLOCKED 不算）即 PASS。另核新增测试 `price_receipt_content_enforced` 的 RED 是否真能在基线上失败（`git stash` 禁用；用 `git show __BASE__:scripts/report/stage2_closeout.py` 等读基线源码做内存对照），以及 `price_check.py` 在基线夹具（单日价格）下会否因"序列过短"退出 1——即施工是否按工单把夹具改成三日。
