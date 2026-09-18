# 工单 F02 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`（统计大小只用 stat）。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F02复核：通过` 或 `# 工单F02复核：退回`。退回时逐条给出：编号（F02-R1-NN）、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。
3. 这是对**修复计划**的复核，不是攻击式验收：目标是拦住工单里"想得不周"的地方——锚点错、修法有副作用、既有测试会变红、同族入口漏了、迁移代价没说清、**工单前提与代码事实不符**（专门核"来源"断言：`check_facts_vs_ledgers:1569-1573` 是否真的对整个 `token` 字典做相等比对从而自动覆盖新键；`flow_selection_errors:205-216` 是否真的按 `circulating_supply_raw` 键消费；`state_from_facts.compile_state:65-74` 与 `Facts.__init__:108-119` 对 token 新键是否零影响）。

## 任务
复核 `maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F02_circulating.md`（v1）与同目录 `ruling_20260918.md`、`code_change_pending.md`。工作目录＝本仓库根（HEAD 含本工程工单 commit；`scripts/`、`references/` 与 8b041842 逐字节相同，行号按 8b041842 核；F04/F05 尚未施工，工单已声明 `test_stage2_closeout.py` 的锚只按锚文本核）。逐项核：
a) §2 每个锚文本 `grep -n -F` 的命中数与行号是否与工单一致。
b) 修法正确性与副作用：读 `derive_facts:324-495` 完整上下文，判断 §2.2 插入点上 `total_raw`、`fi`、`_raw_str`、`_dt` 均已定义；`_raw_str` 对 bool/float/非数字串的实际行为（`_int:88`）是否与工单"非整数串拒"一致；§2.3 替换后 `:478` 续行语法是否成立；`gate_check(Facts(facts))`（`:491`）对 token 多键是否零影响；exploration 模式同路径。
c) 全库同族消费者：`grep -rn "\"token\"\|\.token\b" scripts/report scripts/lib` 列出所有读 facts.token 的地方，逐个判定新键影响（含 `build_html.py`、`a5_report_seal.py`、`audit_release_gate.py` 的 facts 相关检查、`figures_from_facts.py`）；是否有对 token 键集合做白名单/相等断言的既有测试会变红（`grep -rn 'facts\["token"\] ==\|"token": {' scripts/tests`）。
d) 回归面：列出所有会因本段变红的既有测试（含 run_all.py 登记的 143 个里工单 §0.8 未列的）；`test_report_facts.py:328` 文案改动是否被别的测试/守卫（`test_sixlens_docs`/`docs_lint`/`casebook_lint`）字符串匹配。
e) 新用例 RED/GREEN 在基线与改后是否成立（沙箱允许则实跑 `test_report_facts.py`，否则静态推演注明）；§2.6 seed 案数值（`test_audit_release_gate.build_release_case` 与 `test_a4_gate` 夹具的 total/current）是否满足"current×5 < total 且 ≥ 400"；`cases.fresh()` 后 `derive_facts(case)` 能否在 seed 案上成功（三账/identity_gate/provenance_ledger/state_source 是否齐全且 formal）。
f) 终点判据：`ruling_20260918.md` 的 `flow_migration` 三个分支按工单改后是否**必然**成立：①声明 `circulating_supply {raw 400}` → derive token 含 `circulating_supply_raw`、发布重算一致、`flow_selection_errors` 报 `包含下限 ['e1']`；②反例写法 `facts_inputs.circulating_supply_raw="400"` → derive 明确拒（给出文案）；③手补 facts.token 无声明 → `check_facts_vs_ledgers` 报 `facts.token 与三账重算值不一致`。
g) 迁移代价与文档零改动前提：`report-template.md:179`"≥20% 总供应或 ≥20% 流通"与 `playbook-supply-recon.md:13`"第三方流通口径只作可比口径引用"是否与本段契约一致；`facts_inputs` 契约只在 py docstring（`:63-69`）承载、references 无 `facts_inputs` 字样（工单声明）是否属实；版本档位（台账 Q12：8.1.0 vs 9.0.0）你的意见。
