# 工单 C 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容（统计大小只用 stat）。禁读 `/Users/uravvv/Desktop` 下任何文件。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单C复核：通过` 或 `# 工单C复核：退回`。退回时逐条给出：编号、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。

## 任务
复核 `maintenance/repair-20260917-p0-four/workorder_C.md`（v1）。工作目录＝本仓库根，HEAD 应为 `8ead156`。逐项核：
a) §2 每个锚文本 `grep -n -F` 在指定文件恰 1 处且行号一致（facts_gate.py :8/:59/:61/:64/:250/:259-260；audit_release_gate.py :44-52/:406/:482/:1343/:1368/:1644-1645/:1673-1680；stage2_closeout.py :31/:62/:575；test_stage2_closeout.py :48-49/:52-55/:58/:74/:123/:352/:590/:593；test_repair_batch_d.py :1056/:1167-1168/:1207/:1246-1252；test_report_facts.py :115；a4_gate.py:52；report-template.md:212 子串唯一且字节 58→53）。
b) **设计要点①**（闸"在场即验"而非加进 `NEW_ANALYSIS_REQUIRED`）：请实际核对全仓 `profile="new-analysis"` 的测试夹具哪些带 facts.json、哪些不带（工单断言：batch15/batch18/test_audit_release_gate 不带，batch_d Solana 带）；若把 facts.json 加进 REQUIRED，是否确实会让不带的夹具变红；"在场即验"下 A4 `MANDATORY_SEAL_FILES` + 闸 A5 seal 重验是否真的能保证正式案 facts.json 在场（请读 `a4_gate.py:52,:390` 与 `audit_release_gate.py:1673-1680`、`a5_report_seal.validate_seal`），给出结论；该口子登记为 P11 是否可接受。
c) **设计要点②**（stage2 夹具地址改 `0xabc`）：`build_release_case` 把 state/identity rows 改 `0xabc`、facts 改 build 生成后，`augment_gate`→`write_binding`（`identity_gate_fixture.py:18-40`，CSV `to=0xabc` 走 `replay_pass1.py`）、`entity_identity_gate.validate_gate`、`add_distribution_initial`/`add_camp_series`（用 `balances_final.json`）、A4 finalize `--seal-files`、`finish_distribution_normal`、`Cases.fresh` 的 `check_result(case)` 是否仍全绿；`fixture.ENTITY_ADDR` 在该文件其余用例有无依赖；沙箱允许则实跑改造后的 `build_release_case`。
d) **C1 `derive_facts`**：与 `check_three_ledgers(chain=None)` 的互相延迟 import 是否成立（`stage2_closeout.py:31-33` 已同时 import）；`_case_file` 的 basename 约束对 `evidence.path` 是否够；`peak_date` 为 None 时 `Facts._entity_value("peak_date")`（`facts_gate.py:124-125`）与 `state_from_facts`（读 facts peak）是否兼容（exploration 产物不进正式，但 `figures_from_facts`/`stage2` 若读到 None 会否异常——列出即可）；entity 集合＝economic ledger 条目、addresses＝strict 成员，与 `economic-control-accounting.md`、`facts_gate.py` docstring（entities 键=entity_id）是否一致；`facts["provenance"]` 新顶层键是否会被任何现有消费者拒绝（`Facts`、`state_from_facts.compile_state`、`figures_from_facts`、`stage2_closeout` 的 `dual`/`fig2_selection_errors`/`workorder_errors`、`a4_gate`/`a5_report_seal`、`build_html`）——逐个 grep 判断。
e) **C2 闸比对**：排除 `producer` 后整体相等的比对是否 fail-closed 于原缺陷（手改 current_raw/peak_raw/addresses/total_supply/新增实体）；`load_json`（:406，严格非有限策略）对 facts 的适用；exploration 拒绝；`regular_case_path` 对符号链接的处理。
f) **C3/C4-a**：stage2 `record` 新增后 11→12 的三处计数是否齐全（另 grep `== 11`/`11 项`/receipt schema 文档有无计数）；`facts_vs_ledgers_rejects_hand_edit` 三个变体在改后是否 BLOCK 且 `detail` 含指定子串；`update(case,"facts.json",...)` 的 :447 用例（加 e2 观察实体后直调 `fig2_series_errors`）与 :246-259（直调）是否不受新 record 影响；`Cases.fresh` 每次 `check_result(case)` 要求 PASS——新 record 对 seed 案是否 PASS（peak_evidence/state_source 写入位置与 A4 finalize `--seal-files` 的先后是否会让 seal 漂移）。
g) **C4-b**：`build_solana_case` 内 `owners_path` 变量在 :1207 处是否在作用域；align 后三账 e1 的 amount 与 `owner_amount` 是否一致；identity_gate `total_supply_raw "100"` 与 owner amount 关系（peak≥current）；build 后写出的 facts 是否影响后续 figures check（空 series）、a4_seal/a5 seal（在 build 之后计算 sha 即可）；`t_b2` :1246-1252 与 :1540-1548 两处 `gate.run == []` 在新闸下是否仍绿；反例放置方式。
h) **C4-c**：11 例在基线与改后的 RED/GREEN 是否成立（沙箱允许则实跑）；夹具三账是否满足 `check_three_ledgers(chain=None)`（balance_source sha 绑定、as_of_block）。
i) **C5**：`invariant_scan.py` 对新 schema 字面量/`os.replace`/consumer 的识别方式与登记形态是否如工单预期；`minimum_counts` 是否会变。
j) **C6/§1.1**：报表模板行替换后 references 字节是否恰 930065；docs_lint 对该行有无粗体配对/引用断链影响。
k) 回归：§0.8 列出的测试在新逻辑下有无必红点；有无遗漏同族点（其他读 facts.json 的生产路径是否也该验 provenance，列出并注明是否属本段）；有无任何一处会让 `run_all.py` 现有用例变红。
