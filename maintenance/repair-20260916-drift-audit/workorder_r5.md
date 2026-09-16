# 工单 R5：口径漂移与文档-代码不符修复（盲审 R5 消化）v1

内容基线：`0e031559f13a4b11608fd94025a447dd645012cc`（VERSION 7.1.1；R1–R4 施工已落地）。来源：`blind_r5_report.md` 2 条（Fable 逐条亲核属实）。只改文本；`scripts/report/standard_charts.py:283` 文档串同错已记入 `code_change_pending.md` 待用户决策，本单不动。

## §0 施工纪律（同工单 R4 §0；白名单与差异如下）
0.1 `git status --short` 为空；`git diff --stat 0e03155 HEAD -- SKILL.md references scripts commands-staging VERSION` 为空；不符停工。
0.2 禁读 `~/.codex/`、`archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`（只约束主动读取；运行 §1.2 守卫脚本属被测代码既有行为，允许并要求原样运行）。
0.3 **白名单**：`references/data-pipeline-robinhood-traps.md`、`references/report-template.md`，以及新建 `maintenance/repair-20260916-drift-audit/r5_done.md`。
0.4 删除 > 修改 > 新增；锚先 `grep -n -F` 核验恰 1 处且行号一致；不符停工；只动指定片段。
0.5 不 commit；不改 `scripts/`、不改 `contract_manifest.json`、不改任何 CSV；撞 needle 停工汇报。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` = 8798 不变；references 三组 glob 合计 ≤ 929888（基线 929969；两处逐字计算净减 −18/−63 = −81 B，实测数写入报告）。
1.2 守卫全绿（`docs_lint.py` 与 `--all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`），输出贴进 r5_done.md。
1.3 `git diff --stat` 只含白名单。

## §2 逐条施工

### D1 坑册硬编码的 RobinHoodSettler 地址与地址簿/标签表/金标/手工源四处不一致
`references/data-pipeline-robinhood-traps.md:62`。锚：``RobinHoodSettler 0xe72688f7d25d73a2a5e2a4e40d1f0b6b2c5c1e05`` → ``RobinHoodSettler`（址见 address-book）`（依据 `references/address-book.md:147`、`references/labels/labels-robinhood.csv:85`、`references/labels/benchmark/goldset.csv:881`、`scripts/labels/sources/manual_labels.csv:118` 四处均为 `0xe72688f7d25d7318b9a81f21edda640ca948c83b`；删除坑册重复硬编码、改指向唯一登记源，不裁定链上真值。同行 DexAggregatorCore、relayer 两址已核与地址簿一致，不动）

### D2 图 2 模板允许"线超 8 条合并"，收口实现硬拒 merge_groups
`references/report-template.md:162`。锚：`，线超 8 条时可将持仓较小的实体合并成一条（合并了谁在图注写明）` → `（本版不支持合并线）`（依据 `scripts/report/stage2_closeout.py:197-198` 声明 merge_groups 即 WORKORDER BLOCK；`figures_from_facts.py:292-300` 逐线按单实体核对末点，无合计语义；merge_groups 属 7.2 遗留清单）

## §3 完成报告 `r5_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测；③§1.2 原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
