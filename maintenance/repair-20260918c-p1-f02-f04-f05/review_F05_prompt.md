# 工单 F05 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`（统计大小只用 stat）。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F05复核：通过` 或 `# 工单F05复核：退回`。退回时逐条给出：编号（F05-R1-NN）、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。
3. 这是对**修复计划**的复核，不是攻击式验收：目标是拦住工单里"想得不周"的地方——锚点错、修法有副作用、既有测试会变红、同族入口漏了、迁移代价没说清、**工单前提与代码事实不符**（专门核"来源"断言：`price_check.py` 是否真的在 `:181-185` 一处写出收据、`points[].status` 取值集合是否恰为 PASS/WARN/SKIP/FAIL、verdict 规则是否恰为 `:178-180`）。

## 任务
复核 `maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md`（v1）与同目录 `ruling_20260918.md`、`code_change_pending.md`。工作目录＝本仓库根（HEAD 含本工程工单 commit；`scripts/`、`references/` 与 8b041842 逐字节相同，行号按 8b041842 核；F04 尚未施工）。逐项核：
a) §2 每个锚文本 `grep -n -F` 的命中数与行号是否与工单一致。
b) 修法正确性与副作用：读 `stage2_closeout.workorder_errors:265-405` 完整上下文，判断 §2.2 替换后 `errors`/`notes`/`required_refs` 的作用域与顺序是否正确；`price_receipt_errors` 的 verdict 重算与 `price_check.py:165-180` 是否逐条等价（含 SKIP 判定与 WARN/FAIL 阈值不重算的边界）；`load()`（`:62`）对越界/符号链接/坏 JSON 的异常类型是否都落在 `except (OSError, ValueError)`；内联 `dual_source_check.receipt` 引用进入 `required_refs` 后 `:358-379` 遍历是否会重复报错或误报 `self_reference`。
c) 回归面：列出所有会因本段变红的既有测试（含 run_all.py 登记的 143 个 test_*.py 里工单 §0.8 未列的）——重点：任何构造 `price_checks.json`/`price_source_checks`/`dual_source_check` 的夹具（`grep -rn` 全 tests），`test_stage2_reseal.py` 是否复用 `build_closeout_case`，`price_series.json` 改为 3 点是否影响其他断言；`workorder_reference_contracts:503-544` 每条 mutation 在新逻辑下是否仍 BLOCK 且文案含 field 名。
d) 新用例 RED/GREEN 在基线与改后是否成立（沙箱允许则实跑 `test_stage2_closeout.py`，否则静态推演注明）；`write_price_receipt` 对 `price_check.main()` 的 `sys.exit` 捕获是否覆盖 `sys.exit("[fatal] …")` 字符串码的情形；偏差数值（66.67% / 7.69% / SKIP）是否算对。
e) §0.3 白名单是否足够、§0.4 不改项是否自洽；`invariant_scan.py`（price_check 登记为 `requests` 类、写文件点 `--out`）是否会因新增 `_sha256_file` 或收据新键要求登记或报错；`test_batch4_invariant_guards.py`/`test_exemption_guards.py` 同。
f) 终点判据：`ruling_20260918.md` 的 `price_gate_content` 反例（真实 price_check 主 50/副 100 → FAIL 收据退出 2 → 绑定进工单）按工单改后是否**必然**使 `stage2_closeout check` 退出 2——给出拒在哪一行、哪句文案。
g) 存量代价（台账 Q8/Q9）表述是否准确、是否有遗漏的正式路径消费者（`grep -rn price_source_checks|dual_source_check` 全 scripts/references/commands-staging）；文档 `split-run.md:158`"价格源 path＋sha256 及双源检查结果"在零改动前提下是否与新契约冲突。
