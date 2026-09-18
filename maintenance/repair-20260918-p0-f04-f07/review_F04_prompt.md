# 工单 F04 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`（统计大小只用 stat）。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F04复核：通过` 或 `# 工单F04复核：退回`。退回时逐条给出：编号（F04-R1-NN）、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。
3. 这是对**修复计划**的复核，不是攻击式验收：目标是拦住工单里"想得不周"的地方——锚点错、修法有副作用、既有测试会变红、同族入口漏了、迁移代价没说清。

## 任务
复核 `maintenance/repair-20260918-p0-f04-f07/workorder_F04.md`（v1）。工作目录＝本仓库根（HEAD 含本工程工单 commit；`scripts/` 与 311e6c4 逐字节相同，行号按 311e6c4 核）。逐项核：
a) §2.1/§2.2 每个锚文本 `grep -n -F` 恰 1 处且行号一致（`audit_release_gate.py` :16/:1470-1471/:1475-1494/:1525/:1551-1558/:1571/:1572/:1817；`figures_from_facts.py` :296-337；`test_repair_batch_c.py` :1111-1120/:1112/:1174-1198/:1440-1452/:1465/:1497/:1510）。
b) 修法正确性与副作用：①`import figures_from_facts` 在 `audit_release_gate` 内局部 import 是否可行（sys.path 同目录；连带 `standard_charts`→matplotlib 在 `build_html` 发布链、`stage2_closeout`、`a4_gate` 调用 `audit_release_gate.run` 时是否引入新失败模式，例如无显示环境/字体缓存；`figures_from_facts.py:1-60` 有无 `matplotlib.use` 设置）；②basename 定位与 `_figure2_input_check` 是否一致；③`fig2_check_errors` 抛出的异常类型是否只有 ValueError（`:298-302` 把 OSError 转 ValueError；其他分支如 `int(str(ent.get("current_raw")))` 可能抛 ValueError；`facts.total_raw` 属性缺失可能抛 KeyError/AttributeError——工单 except 元组是否够，不够建议加 AttributeError）。
c) 回归面：列出所有喂 `check_figure2_receipt` 或走 `profile="new-analysis"` 完整 `gate.run`/`build_html --mode analysis-new` 的测试（`test_a4_gate.py`、`test_repair_batch_d.py`、`test_repair_g1_cross_target.py`、`test_review_20260804_p105.py`、`test_stage2_closeout.py`、`test_repair_batch_c.py`），逐个判断其 series 与 facts 是否同源（真跑 check 产收据者应仍绿；手写 PASS 收据且不同源者会变红——列出行号）。特别核 `_r08_case_12`（`:1440` 起）"基线消费者接受"断言的准确行号与文案，给出应改成的断言。
d) §2.2 四个新用例的 RED/GREEN 在基线与改后是否成立（沙箱允许则实跑 `python3 -B scripts/tests/test_repair_batch_c.py`，否则静态推演注明）。
e) §0.4/§0.8/§1/§4 是否自洽；`invariant_scan.py`/`invariant_manifest.json` 是否会因 consumer 新增文案或新 import 而要求登记（若会，工单需把 manifest 加进白名单）。
f) 有无任何一处会让 `run_all.py` 现有用例变红。
