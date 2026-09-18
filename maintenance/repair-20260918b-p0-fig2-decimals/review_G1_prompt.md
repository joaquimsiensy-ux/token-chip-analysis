# 工单 G1 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918-p0-f04-f07/` 与 `maintenance/repair-20260918b-p0-fig2-decimals/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`（统计大小只用 stat）。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单G1复核：通过` 或 `# 工单G1复核：退回`。退回时逐条给出：编号（G1-R1-NN）、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。
3. 这是对**修复计划**的复核，不是攻击式验收：目标是拦住工单里"想得不周"的地方——锚点错、修法有副作用、既有测试会变红、同族入口漏了、迁移代价没说清、**工单前提与代码事实不符**（上一轮 F05 工单把 verify_recon config 当"链上观测"，两轮复核都没拆穿——本轮请专门核每个"来源"断言是否真有生产者写出该字段）。

## 任务
复核 `maintenance/repair-20260918b-p0-fig2-decimals/workorder_G1_fig2.md`（v1）与同目录 `ruling_20260918.md`、`code_change_pending.md`。工作目录＝本仓库根（HEAD 含本工程工单 commit；`scripts/`、`references/` 与 f1f473f3 逐字节相同，行号按 f1f473f3 核）。逐项核：
a) §2 每个锚文本 `grep -n -F` 的命中数与行号是否与工单一致；工单自己标注"开工核实"或"第 N 处"的项给出实况。
b) 修法正确性与副作用：逐条读被改函数的完整上下文，判断替换/插入后语义是否如工单声明；异常面、返回类型、调用方是否有未列出的消费者（`grep -rn` 函数名与字段名，列出全部命中并逐个判定影响）。
c) 回归面：列出所有会因本段变红的既有测试（含 run_all.py 登记的 143 个 test_*.py 里工单 §0.8 未列的），给出行号与原因；判断工单 §1 "不得变红"的断言是否成立。
d) 新用例 RED/GREEN 在基线与改后是否成立（沙箱允许则实跑相关测试，否则静态推演注明）。
e) §0.3 白名单是否足够、§0.4 不改项是否自洽；`invariant_scan.py`/`docs_lint.py`/契约路由守卫是否会要求登记或报错。
f) 终点判据：codex review 附录 C 的反例（G1＝`empty_figure2`：非空 facts.entities 含"大庄#1"＋whale_series=[]；G2＝`decimals_selfreport`：config decimals 0→2、human 100→1、重签哈希）按工单改后是否**必然**变为拒——给出拒在哪一行、哪句错误文案。
g) 迁移代价与版本档位表述是否准确（G2：v1 bundle 拒收＝不兼容？）。
