# 工单 A 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单A复核：通过` 或 `# 工单A复核：退回`。退回时逐条给出：编号、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。

## 任务
复核 `maintenance/repair-20260917-p0-four/workorder_A.md`（v1）。工作目录＝本仓库根。逐项核：
a) §2 每个锚文本 `grep -n -F` 在指定文件恰 1 处且行号一致（`figures_from_facts.py` :60/:63-65/:139-144/:282-286/:304-308/:328/:370-372；`test_repair_batch_c.py` :1109/:1111-1120/:1201/:2106）。
b) A1：`_reject_constant` 抛 ValueError 是否与 `fig2_check_errors` :282-286 的透传及 `scripts/tests/test_stage2_closeout.py:569-574` 契约一致；`_load` 五路调用方（fig1 state、flow spec、check 双输入、fig2-series）加 `parse_constant` 是否有任何路径会因此从"通过"变"拒"而破坏现有测试（列出你查到的调用点行号与结论）。
c) A2：插入位置是否正确（在"线无 pct 数据" continue 之后、`last = float(pct[-1])` 之前）；`math` 是否已 import；断言 `1e400` 走 A2 而非 `parse_constant` 是否属实（Python json 对 `1e400` 的行为）。
d) A3：`mode_check` 加 try/except 后，`:329-330` 的 `--series 应为 …` 特判与后续收据写入逻辑是否不受影响；NaN 字面量路径确认"不写收据、exit 1"。
e) A5：九个用例的 RED 断言是否成立——基线代码上用例 1/2/3/6 是否真的 PASS（返回码 0）、用例 4 是否 traceback 无收据、用例 5/7/8 的基线行为是否如工单所述；若沙箱允许在临时目录运行 `python3 scripts/report/figures_from_facts.py check …` 请实跑取证，不允许则静态推演并注明"未实跑"。`run`/`check`/`A`/`fff` 辅助与 `sys.path` 设置是否如工单所述可直接复用；用例 8 的模块导入方式是否可行。
f) §0.4 不改清单与 §1.1 字节约束是否与改动范围自洽；是否遗漏了本段应改而未列的同族点（例如其他读 series 的路径仍裸 `json.load`），若有请列出但注明"是否属本段范围"。
g) 有无任何一处会让 `scripts/tests/run_all.py` 现有用例变红（重点：`test_repair_batch_c.py`、`test_stage2_closeout.py`、`test_repair_batch_d.py` 端到端夹具的空 series `[]`、`test_figures_from_facts.py`）。
