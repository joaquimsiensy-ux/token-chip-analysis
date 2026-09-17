# 工单 R7：待决代码台账三项裁决落地 v1

内容基线：`33548fc5e257014a6f30533094a911a50fe25972`（VERSION 7.1.2）。来源：`code_change_pending.md` D1/D2/D3，用户 2026-09-16 裁决："①选 B（改文档不改码），②③都改（注释），能不改代码就先不改"。本单：一处文档文本、两处 Python **仅 docstring/注释** 文字，零逻辑改动。

## §0 施工纪律（同工单 R6 §0；白名单与差异如下）
0.1 `git status --short` 为空；`git diff --stat 33548fc HEAD -- SKILL.md references scripts commands-staging VERSION` 为空；不符停工。
0.2 禁读 `~/.codex/`、`archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`（只约束主动读取；运行 §1.2 守卫脚本属被测代码既有行为，允许并要求原样运行）。
0.3 **白名单**：`references/analyze-workflow.md`、`scripts/solana/decode_txs_v2.py`（仅第 8 行注释）、`scripts/report/standard_charts.py`（仅第 283 行 docstring），以及新建 `maintenance/repair-20260916-drift-audit/r7_done.md`。
0.4 删除 > 修改 > 新增；锚先 `grep -n -F` 核验恰 1 处且行号一致；不符停工；只动指定片段。**两处 .py 改动必须 `python3 -c "import ast; ast.parse(open(p).read())"` 各验一次语法，且 `git diff` 里除注释/docstring 行外零变化。**
0.5 不 commit；不改 `contract_manifest.json`/`invariant_manifest.json`；撞 needle 停工汇报。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` = 8798 不变；references 三组 glob 合计 ≤ 930070（基线 929833；D1 按用户裁决登记已知例外，逐字净增 237 B）；`decode_txs_v2.py` 16947、`standard_charts.py` 23009（基线 16952/23051，净 -5/-42 B）。
1.2 守卫全绿（`docs_lint.py` 与 `--all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`），另跑 `scripts/tests/test_figures_from_facts.py` 与 `test_review_solana_integrity.py`（引用两脚本的既有测试），输出贴进 r7_done.md。
1.3 `git diff --stat` 只含白名单。

## §2 逐条施工

### D1（裁决 B）文档承诺"一律整数运算"，wave_scan 必裁决线用浮点——登记为已知例外
`references/analyze-workflow.md:158`。锚：`来源：meow 案 2026-07-15）。` → `来源：meow 案 2026-07-15）。已知例外：`wave_scan.py` 必裁决四标记的 0.1%/0.05% 线仍用浮点，恰好等于阈值的地址可能丢标记（用户 2026-09-16 裁决暂不改码，见 maintenance/repair-20260916-drift-audit/code_change_pending.md）。`（依据 `scripts/report/wave_scan.py:735-746`；APU 案实测 1 址峰值恰 0.1% 丢 peak_ge_0.1pct 标记）

### D2 decode_txs_v2 文头注释"256 片"
`scripts/solana/decode_txs_v2.py:8`。锚：`按 sig 前 2 字符分 256 片` → `按 sig 前 2 字符分片`（依据同文 `:75` 文件名取 sig 前 2 字符，Base58 下分片数非 256；文档侧已于 R4 改正）

### D3 standard_charts 文档串"线超 8 条可合并"
`scripts/report/standard_charts.py:283`。锚：`标签实体各画一线；线超 8 条时可将持仓较小的实体合并成一条避免花屏。` → `标签实体各画一线（本版不支持合并线）。`（依据 `stage2_closeout.py:197-198` 硬拒 merge_groups；文档侧已于 R5 改正）

## §3 完成报告 `r7_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测；③§1.2 原始输出＋两处 ast.parse 结果；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
