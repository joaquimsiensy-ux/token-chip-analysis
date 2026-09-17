# 盲审 C 提示词（只读，施工后独立复核）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容；禁读 `/Users/uravvv/Desktop` 下任何文件。
2. 只读、离线、不 commit、不改文件。报告全文打印到 stdout，首行固定 `# 盲审 C：PASS` 或 `# 盲审 C：FAIL`。FAIL 时逐条给：编号、严重度（blocker/minor/nit）、位置 path:line、事实（代码原文或可复现命令）、修法建议。PASS 时列出实际核过的项与未实跑的项。
3. 这是常规盲审，不是攻击式验收：目标是判断本段改动是否正确、完整地实现了工单不变量且无回归；不要求构造边界外攻击向量。

## 范围
- 审查对象：`git diff __BASE__..__HEAD__ -- scripts/ references/`（施工 commit 范围，由调度方填入）；工单 `maintenance/repair-20260917-p0-four/workorder_C.md`（v3）；施工报告 `C_done.md` 与 `C_red_evidence.txt`；工单复核记录 `review_C_reply_r1..r3.md`。
- 不审：`SKILL.md`、`commands-staging/`（本段零改动，只需确认 diff 未触及）；其他段（R03/R08/R09）。

## 任务
a) **不变量**：①`facts.json` 只能由 `facts_gate.py build` 从三账＋identity_gate＋（可选）provenance_ledger＋`state_source.facts_inputs` 生成，产物带 `provenance` 绑定块（schema `facts-provenance/v1`、`facts_binding=ledger-derived`、mode、inputs 逐文件 sha、state_source sha、peak_overrides、producer）；②实体集合＝economic 条目、addresses＝strict 成员、current_raw＝confirmed_economic_control_raw、total_supply_raw＝identity_gate；peak 取 override（evidence path/sha 三验）否则 provenance 锚点，formal 无来源即拒，peak<current 拒；③生成物必须过既有 `gate_check`（G2/G3）；④输入 JSON 严格解析拒 NaN/Infinity/1e999；⑤发布闸 new-analysis 把 `facts.json` 列为必需件并用同一 `derive_facts` 重算逐键/逐实体比对（排除 producer），exploration/缺绑定/不一致/输入变动/符号链接/图 2 收据绑另名 facts 一律报错；⑥stage2 收口新增 `facts_vs_ledgers` record（11→12）。逐条对照 diff 判断是否成立，列出你核到的代码行。
b) **六视角**（`references/maintenance-review-repair.md` §1）：①字段来源（比对用重算值而非自报值；override 证据是否真被复验）②失败分支（缺件/空账/不闭合/证据不符/预置绑定/非有限 是否都 fail-closed 且错误互斥可断言）③存量迁移（无 facts 或手写 facts 的存量案在 new-analysis 闸下必红——这是设计意图；independent-audit/legacy 不受影响是否属实）④同族调用面（其他读 facts.json 的生产路径：`build_html`、`state_from_facts`、`figures_from_facts`、A4/A5 seal——是否有本该也验 provenance 而漏掉的必经路径，列出并判断是否属本段）⑤双向一致性（`report-template.md:212` 新句与代码行为；`facts_gate.py` docstring 的 state_source 块说明与 `derive_facts` 实际校验是否一致）⑥检查点可绕性（`--source` 另名、`--out` 越界、facts.json 为符号链接、provenance_ledger 为 exploration、facts_inputs 预置 provenance）。每视角给结论。
c) **测试真实性**：`C_red_evidence.txt` 的 RED 是否与基线行为一致（用 `git show __BASE__:<path>` 读基线静态推演）；C4-d 十四例、stage2 三变体、batch_d 两反例是否真的区分改前改后；有无为了变绿而弱化的断言；四处夹具改用 `build_facts_from_ledgers` 后是否仍是"要求零错误"的真实绿例（而非跳过检查）；`identity_gate_fixture.augment_gate` 默认分支是否逐字节等价旧行为。
d) **回归**：`git diff --stat` 是否只含白名单；工单 §0.8 各测试在 `C_done.md` 里是否有真实结果尾行；`invariant_manifest.json` 是否只增补不重排；沙箱允许则实跑 `python3 -B scripts/tests/test_report_facts.py`、`test_stage2_closeout.py`、`test_repair_batch_d.py`、`test_a4_gate.py`、`invariant_scan.py`，不允许则注明未实跑。
e) **工单符合度**：diff 是否有工单之外的改动（含注释/docstring/空白），有则列出并判断是否可接受；references 字节是否恰 930065、SKILL.md 8021、commands-staging 8798（只 stat）。
