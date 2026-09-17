# 工单 A 复核提示词（只读，r3：对 v3 全量复核；r2 两条见 `review_A_reply_r2.md`，重点核 A-R2-01/02 的处置：`_pct_value_ok` 是否覆盖超大整数与 `float()` 溢出、A3 的 OSError 收敛、新增用例 11/12/13 的 RED 与断言是否成立）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容（统计大小只用 stat）。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单A复核：通过` 或 `# 工单A复核：退回`。退回时逐条给出：编号、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。

## 任务
复核 `maintenance/repair-20260917-p0-four/workorder_A.md`（v3；r1 七条见 `review_A_reply_r1.md`，r2 两条见 `review_A_reply_r2.md`）。工作目录＝本仓库根。逐项核：
a) §2 每个锚文本 `grep -n -F` 在指定文件恰 1 处且行号一致（`figures_from_facts.py` :60/:63-65/:109/:139-144/:201-202/:257/:282-286/:306-308/:328-330/:370-372/:406；`test_repair_batch_c.py` :37-40/:45/:54/:60/:1109/:1111-1120/:1201/:2106）。
b) v2 对 r1 七条的处置是否各自闭合：A-01（fig1 `:109` strict=False 后 `test_figures_from_facts.py:150-151`、`test_repair_batch1.py:993-994` 是否仍绿；其余 6 处 strict 是否有任何现有测试从通过变失败——请检查 `test_figures_from_facts.py`、`test_stage2_closeout.py`、`test_repair_batch_d.py`、`test_a4_gate.py`、`test_repair_g1_cross_target.py`、`test_review_20260804_p105.py` 中喂给 flow/check/fig2-series 的 JSON 夹具有无 NaN/Infinity 字面量）；A-02（A3 的 except 分支写 FAIL 收据是否可行：`_write_check_receipt`/`_file_ref` 对未解析的文件取 sha 是否无副作用；`os.path.isfile` 守卫是否够；用例 10 是否能证明覆盖）；A-03（锚唯一性）；A-04（子函数拆分与 RED 取证方式）；A-05（stat 命令是否正确且不读内容）；A-06/A-07。
c) A5 十个用例的 RED/GREEN 断言在基线与改后是否成立（沙箱允许则在临时目录实跑 `python3 scripts/report/figures_from_facts.py check …` 取证，否则静态推演并注明"未实跑"）；用例 5 与 6 新增的收据字段断言（`mismatches[0]` 含"输入不可用"、`mode == "exploration"`）是否与 `_write_check_receipt` 写出的字段一致。
d) §0.4 不改清单、§0.8 定向测试清单、§1.1 字节约束、§4 登记项是否与改动范围自洽；是否还有遗漏的同族点（列出并注明是否属本段）。
e) 有无任何一处会让 `scripts/tests/run_all.py` 现有用例变红。
