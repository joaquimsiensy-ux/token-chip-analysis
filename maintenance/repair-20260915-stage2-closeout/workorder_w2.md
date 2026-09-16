# W2 施工工单：−2 收口命令 `stage2_closeout.py`（check / fill-workorder / amend）＋四处现有脚本挂点

> 版本 v1（2026-09-15，Fable 起草；待 codex 只读复核后定稿）。依据已批计划 `plan_v2_approved.md` §2.2、§2.4、§4、§6（1a/1b/1c/6/9b/9c）。基线 main=764b60c（7.0.4）之后、W1 施工 commit 之后开工（W2 依赖 W1 的 `find_snapshot(case_dir, requested, stage)` 与 `a4_gate limits-extract`；若 W1 尚未合入，本单 §7 注明的两处调用按 764b60c 签名写，验收时以合入后为准）。

## §0 开工纪律（与 W1 相同，逐条遵守）

1. 工作树 `~/.claude/skills/token-chip-analysis`，main；开工先 `git log -1 --format=%H` 记进 `w2_done.md`；`git status` 须干净。禁读 `~/.codex`；离线（不下载任何源）。
2. **只新建一个脚本** `scripts/report/stage2_closeout.py`（用户施工原则：能修改的不新增）。其余改动全部落在现有文件：`audit_release_gate.py`、`figures_from_facts.py`、`a4_gate.py`、`build_html.py`、`scripts/tests/run_all.py`；新建测试 `scripts/tests/test_stage2_closeout.py`。
3. **禁改**：`a4_gate.py` 的 `cmd_register`/`cmd_finalize`/`distribution_claim_source`（只加新函数与新子命令）；`holder_distribution_scan.py`（W1 在改，本单只调用）；`a5_report_seal.py`（只调用其函数）；`entity_identity_gate.py`；`facts_gate.py`；三册手册（W3 改）；CHANGELOG/VERSION（W3 改）。
4. 顺序 A → B → C → D → E → F（A–D 是挂点，E 是主脚本，F 是测试登记）。每段先跑红证据（`w2_red_evidence.txt`），再改，再绿。
5. 不 commit；完工写 `maintenance/repair-20260915-stage2-closeout/w2_done.md`（改动清单、每条测试的红→绿证据、未做项与原因）。
6. 现有测试 `test_a4_gate.py:608/:638` 断言 build_html 输出含 `封口后被改动`；`test_audit_release_gate.py` 全部用例；`test_distribution_gate.py`；`test_round4_a5_seal.py`——改完全部必须仍 PASS。全套 `python3 scripts/tests/run_all.py` 约 11 分钟，用 nohup 落盘。

## §A `audit_release_gate.py`：新增 profile `stage2-dryrun`

锚点（764b60c）：
- `:44-52 NEW_ANALYSIS_REQUIRED = (...)`，`:54-57 REQUIRED_BY_PROFILE = {...}`
- `:1558 if profile == "independent-audit" and report is None:`
- `:1606 if profile == "new-analysis" and "distribution_scan.json" in data:`
- `:1616 if profile == "new-analysis":`（大块，到 `:1656`），内含 `:1618 if "figure2_check_receipt.json" in data:`、`:1637 if "fig1_legend_receipt.json" in data:`、`:1640 elif "fig1_legend_receipt.json" in data:`、`:1646 seal_path = case_dir / "a5_report_seal.json"`
- `:1671 ap.add_argument("--profile", choices=sorted(REQUIRED_BY_PROFILE), ...)`（自动带上新 profile，不用改）

改法：
1. `:54-57` 加一行 `"stage2-dryrun": SHARED_REQUIRED + ("distribution_scan.json", "distribution_rounds.json"),`。豁免 `a5_report_seal.json`、`fig1_legend_receipt.json`、`figure2_check_receipt.json`（−3 产物）。
2. `:1558` 改为 `if profile in ("independent-audit", "stage2-dryrun") and report is None:`，文案改 `f"{profile} 发布必须带 --report ..."`（fail-closed 不放松）。
3. `:1606` 改 `if profile in ("new-analysis", "stage2-dryrun") and "distribution_scan.json" in data:`。
4. `:1616` 改 `if profile in ("new-analysis", "stage2-dryrun"):`；块内三处各加围栏 `if profile == "new-analysis"`：figure2 收据段（`:1618-1619`）、fig1 legend 段（`:1637-1641` 含 elif 分支）、A5 seal 重验段（`:1642-1656` 整段，含"缺 --report 即 fail-closed"那句——dryrun 下没有 seal 是正常的）。series binding 段（`:1620-1636`）对两种 profile 都跑。
5. 不改 `run()`（`:1543`，保留深验缓存）；closeout 调 `audit_release_gate.run(case_dir, report, profile="stage2-dryrun")`。

红证据：改前 `python3 scripts/report/audit_release_gate.py <APU案> --report 报告.md --profile stage2-dryrun` 报"未知发布 profile"（argparse choices 拒）。绿：返回 PASS 或列出真实错误（APU 0914 案见 §7 注意）。

## §B `figures_from_facts.py`：拆纯校验函数＋新增 `fig2-series` 子命令

锚点：`:256 def _write_check_receipt(a, verdict, okc, errs):`；`:279 def mode_check(a):`（`:288-318` 是校验主体）；`:333 def main():`，`:353 p3 = sub.add_parser("check", ...)`，`:361 p3.set_defaults(fn=mode_check)`。

改法：
1. 从 `mode_check` 抽出 `def fig2_check_errors(facts_path, series_path, tol_pp) -> tuple[list[str], int]`（返回 errs, okc；**不写收据、不打印**）；`mode_check` 改为：容差政策检查（`:284-287` 原样）→ 调 `fig2_check_errors` → 打印与写收据（`:319-330` 原逻辑）。行为逐字不变（`test_a4_gate.py:507-512` 靠它产收据）。
2. 新子命令 `fig2-series`：参数 `--entity-series <案内 entity_series.json>`、`--keys TE-01,TE-02`（逗号）、`--labels-from facts.json`、`--out whale_series.json`。输入格式 `{dates:[YYYY-MM-DD…], <key>:[pct…]}`（APU 0914 实况）；输出裸数组 `[{entity_id, label, ts, pct}]`，`label = facts.entities[key].label`（key 不在 entities 或 series 缺 key → exit 1）；`ts` 直接用 dates；`pct` 原值不改。同时写 `<out 同目录>/whale_series.provenance.json`：`{schema:"fig2-series-provenance/v1", entity_series:{path,sha256}, facts:{path,sha256}, keys:[...], out:{path,sha256}}`（无时间戳，确定性）。写法 tmp+fsync+os.replace（同 `:248-253`）。`plot_whale_vs_price` 只读 label/ts/pct（`standard_charts.py:289-291`），多出的 entity_id 无害；`check` 按 entity_id 优先匹配（`:298`）。
3. 长度约束：`len(pct)==len(dates)` 否则 exit 1。

红证据：改前 `figures_from_facts.py fig2-series ...` 被 argparse 拒。绿：APU 案 `--keys TE-01,TE-02,TE-04` 产出 3 线，`check` 对它 PASS。

## §C `a4_gate.py`：两个只读函数＋一个只读子命令

锚点：`:487 def main():`，`:490 sub = ap.add_subparsers(...)`，`:494 f = sub.add_parser("finalize", ...)`，`:505 return {"register": cmd_register, "finalize": cmd_finalize}[a.subcmd](a)`；W1 会在此同一处加 `limits-extract`，合并时按 W1 结果为准。`safe_case_file` 在 `scripts/lib/case_paths.py:9`；`validate_revision_chain(case, seal)` 已在本文件（build_html.py:346 调用）。

C1 `seal_integrity_errors(case_dir: Path, seal: dict) -> list[str]`：把 `build_html.py:340-391` 的非图片检查逐条搬来（**文案逐字保留**，去掉 `[WARN] ` 前缀由调用方加）：
- schema/verdict/claims 缺失（`:340-343`）；`validate_revision_chain`（`:345-347`）；
- `sealed_files`＋`registry`＋`verdicts` 逐条：路径合法（`checked()` `:354-364` 的规则：非绝对、无 `..`、拒 symlink、resolve 后在案内、是文件）、重复路径拒、实物 sha 与记录一致（`:366-379`，文案"封口后被改动: {rel}"、"封口条目非法: {e}"）；
- 必封资产 required 集合（`:380-389`，含 independent-audit 加 claim_registry、new-analysis 加 `distribution_claim_source.path`）；`claim_files ⊆ sealed`（`:390-391`）。
- **不搬** workflow_type↔mode（`:348-351`，需要 build 模式）与 charts_dir/图片段（`:393-427`，需要 md）。

C2 `build_html.py:340-391` 改为：`for e in a4_gate.seal_integrity_errors(_case, _seal): warns.append("[WARN] G9 " + e)`，保留 `:348-351` 与 `:393-427` 原样；`_sealed_paths` 仍要给后面用（`:325` 定义）——让 `seal_integrity_errors` 顺带返回集合（返回 `(errors, sealed_paths)`）或在 build_html 侧自行从 seal 取；二选一，保证 `test_a4_gate.py:608/:638` 的 `封口后被改动` 断言仍过、"G9 正例"仍 exit 0。

C3 `downstream_stale(case_dir: Path) -> list[dict]`，每项 `{item, expected, actual, fix_order}`，全部只读：
- `adversarial_review.json` 的 `claim_registry.sha256`（runner `:673` 写入 `registry_ref`，结构 `{path,sha256,...}`，以实物为准核字段名）vs `sha256(a4_claims.json)`；
- `shared_release_receipt.json` 的 `inputs["adversarial_review.json"].sha256`（`shared_release_receipt.py:2122`）vs 实物；
- `distribution_rounds.json` terminal 行 `a4_seal_sha`（`holder_distribution_scan.py:1141`）vs `sha256(a4_seal.json)`；
- terminal 行 `final_scan_path` 的 `input_binding.entity_freeze_revision` vs `len(entity_freeze.json["revisions"])+1`；
- `dormant_warehouse_audit.json` 的 `universe_ref{path,sha256}` vs wave_scan 实物（`audit_release_gate.py:989-998` 同款）。
文件不在场的项跳过并标 `absent`（不是过期）。`fix_order` 固定：freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5。

C4 子命令 `downstream-check --case-dir [--json-out]`：打印表；有过期 exit 3，无 exit 0。加进 `:505` 分派字典。

红证据：APU 案手工 `touch`/改 `a4_claims.json` 的 `registered_at_utc` 后 `downstream-check` 报 registry 过期（改完还原文件，用副本目录做，不动原案）。

## §D `build_html.py`：仅 C2 那一处替换，其余不动。

## §E 新脚本 `scripts/report/stage2_closeout.py`

命令行：`stage2_closeout.py [check] --case-dir <案根> --report 报告.md [--workorder a5_assembly_workorder.json] [--receipt-only] [--json-out]`；`fill-workorder --case-dir --report [--workorder]`；`amend --case-dir --report`。exit：0 PASS / 2 BLOCK / 1 脚本错。`reseal` 子命令 W3 加，本单只留 `sub.add_parser` 占位不实现（或不加，W3 加；二选一写进 done）。所有路径经 `case_paths.safe_case_file`（拒 symlink、拒案外）。

### E1 `check` 子检查（顺序固定；每项 `{name,status:PASS|BLOCK|NOTE|ABSENT,detail}`，全部跑完再判，不短路）

| # | name | 做法 | 失败即 BLOCK？ |
|---|---|---|---|
| 1 | release_gate_dryrun | `audit_release_gate.run(case, report, profile="stage2-dryrun")`；errors 非空即 BLOCK，逐条进 detail | 是 |
| 2 | a4_seal_integrity | 读 `a4_seal.json` → `a4_gate.seal_integrity_errors` | 是 |
| 3 | downstream_stale | `a4_gate.downstream_stale`；有过期即 BLOCK 并附 fix_order | 是 |
| 4 | identity_gate | `entity_identity_gate.validate_gate(case/"identity_gate.json", case/"analysis-state.json", require_resolved=True)`（签名 `:162`） | 是 |
| 5 | a5_provenance_flip | `a5_report_seal.provenance_flip_bundle(case, report_text, a4obj)`；抛异常即 BLOCK；返回 `NOT_APPLICABLE` 时：workflow_type 非 new-analysis → BLOCK（closeout 只服务 new-analysis） | 是 |
| 6 | a5_distribution | `a5_report_seal.distribution_bundle(case, report, a4obj)`；异常 BLOCK；`NOT_APPLICABLE` 同上 BLOCK | 是 |
| 7 | caption_same_source | 见 E2 | 是 |
| 8 | dual_basis | facts 顶层 `dual_basis:{lower:<metric id>,upper:<metric id>}` 在场时：两 id 都在 `facts.metrics`，且报告源文本同时含 `{{m:<lower>}}` 与 `{{m:<upper>}}`；不在场 → NOTE"未声明双口径" | 在场时是 |
| 9 | fig2_series | 工单 `fig2.whale_series` 指的案内文件在场 → `figures_from_facts.fig2_check_errors(facts, series, DEFAULT_TOL_PP)` 无错；并核 `whale_series.provenance.json` 在场且 out.sha256 与实物一致 | 是 |
| 10 | workorder | E3 | 是 |
| 11 | facts_gate | `facts_gate.load_and_check(facts, state, md_text)`（`:250`，签名以实物为准）无错 | 是 |

verdict：任一 BLOCK → BLOCK；否则 PASS。成功文案固定："PASS: −2 可进入装配；待 −3 执行项：fig1/fig2/fig3/流转图渲染、fig1_legend_receipt、figure2_check_receipt、a5_report_seal、build_html"（这行就是 `pending_for_stage3`）。

### E2 图注同源（caption_same_source）

- 定位：报告源文本中 `charts/final/holder_distribution_current.png` 的图片引用行（`a5_report_seal.IMG_RE`，须唯一，否则 BLOCK），其后第一段非空文本为图注。
- 数据源：`distribution_rounds.json` terminal 行 `final_scan_path` 的 scan（rounds 已由 #6 重验过）：`bucket_coverage{private_main,private_dust,public_facility,unresolved_contract,burn_sentinel}{raw,net_supply_pct}`、`concentration`（top_k_net_pct 与 hhi；low_sample 时改用 `small_sample_mode.top_k/hhi`；字段名按 `holder_distribution_scan.py:556/:597-598` 实物核）。
- 渲染规则（按 APU 0914 报告.md:49 与 BTW 现行写法归纳）：`raw=="0"` → 串 `"0"`；`round(pct,2) >= 0.01` → `f"{pct:.2f}%"`；否则 `f"{pct:.4f}%"`（APU 私人粉尘箱 `0.0005%`、BTW `0.0001%`）。top-k 用 `.2f%`，HHI 用 `.4f`。
- 判定：五桶串、top1/3/5/10 四串、HHI 串各自在图注段内出现；`raw=="0"` 桶只要求 `"0"` 出现（弱检查，detail 如实标"退化为存在性检查"）。缺任一 → BLOCK，文案 `图注与终态 scan 不同源: <桶名> 期望 <串> 未出现`。
- 只比数字串不比桶名文案（各案桶名措辞不统一）。

### E3 工单校验（workorder）

字段依据 split-run §3b.2（`references/split-run.md:152-166`）与 APU 0914 实况（顶层键 note/meta/bindings/report_image_refs/fig1/fig2/fig3/flow/path_fence/stage2_selfcheck/amendments）：
1. 必备顶层键：note/meta/bindings/report_image_refs/fig1/fig2/fig3/flow/amendments；`stage2_selfcheck` **可选**（W3 手册把五条自查替换为本命令）。
2. 机械字段重算等值：`bindings.report_md.sha256`（工单 amendments 为空时等于报告实物 sha；非空时等于第一条 before_sha256，且最后一条 after_sha256 等于实物）；`bindings.a4_seal_sha256`；`bindings.entity_freeze_revision == len(entity_freeze.revisions)+1`（APU 实况 3+1=4）；`bindings.facts/state/rounds/final_distribution_png/final_distribution_scan` 各 sha；`bindings.distribution_terminal{status,round_n}` 与 rounds terminal 一致；`report_image_refs` 与 `IMG_RE` 重取的有序清单（保留重复）一致。
3. fig2：`lines[].entity_id ∈ facts.entities` 键（写成展示名即 BLOCK，文案 `WORKORDER BLOCK: fig2.lines[i].entity_id: facts 键 != 展示名`）；`required_entity_ids` ⊇ 必画下限；必画下限 = facts.entities 中 `label.strip()` 以 `项目方`/`大庄`/`小庄`/`离场庄` 之一开头的实体（APU：TE-01/TE-02/TE-04；BTW：e_proj）；label 缺失或空串 → BLOCK"实体 <id> 无标签，无法判定必画"；`lines` 的 entity_id 集合 ⊇ required（合并线用 `merge_groups[].member_entity_ids` 覆盖，字段不存在则不算覆盖）；每条 `series_source{path,key,sha256}`：文件在案内、sha 一致、key 在文件里。
4. flow：下限 = facts.entities 中 label 以 `项目方`/`大庄` 开头且 `current_raw/total_raw ≥ 20%` 的实体（report-template.md:176-178 现行门槛；`total_raw` 取 `facts_gate.Facts.total_raw`）；`eligible_entity_ids ⊇ 下限`；逐张清单兼容 `flow.charts`（APU）与 `flow.items`（BTW）——两键任取其一、都无则 BLOCK；每张 `entity_id ∈ eligible`；允许 eligible 多于下限（"承载关键结论"的额外图）。
5. 路径围栏：工单里所有 `path` 值须案内普通文件（拒 symlink、拒绝对路径、拒 `..`）；各 `out` 以 `charts/final/` 开头且 `.png`。
6. 失败文案统一 `WORKORDER BLOCK: <字段路径>: <期望> != <实际>`。

### E4 `fill-workorder`

只填机械字段：`bindings.a4_seal_sha256`、`bindings.entity_freeze_revision`、`bindings.facts/state/rounds/final_distribution_png/final_distribution_scan{path,sha256}`、`bindings.distribution_terminal`、`report_image_refs`、`meta.skill_version`（读 VERSION）、`meta.skill_commit`（`git rev-parse HEAD`，失败写 null）、`meta.produced_at_utc`。**`bindings.report_md` 已存在则绝不覆盖**（原稿锚）；不存在才写当前实物 sha。选材字段（fig1/fig2/fig3/flow 的判断内容）缺失时留 `null` 并在 stdout 列出"待 −2 亲笔"。工单不存在时从最小骨架建（note 固定句、meta 从 facts.token/accounting_mode 取 case_id/token/chain/contract/cutoff、其余 null）。写法 tmp+os.replace。

### E5 收据 `stage2_closeout_receipt.json`

schema `stage2-closeout/v1`：`{schema, verdict, report_md{path,sha256}, workorder{path, effective_sha256}, facts{sha256}, state{sha256}, entity_freeze_revision, a4_seal_sha256, rounds{sha256, terminal_round_n, status}, whale_series{path,sha256}|null, skill_commit, checks[], pending_for_stage3[], amendment_chain[]}`。`workorder.effective_sha256` = 工单剔除 `stage2_selfcheck` 后 `json.dumps(sort_keys=True, ensure_ascii=False, separators=(",",":"))` 的 sha256。无时间戳。BLOCK 也写收据（verdict=BLOCK）。不进 `REQUIRED_BY_PROFILE`（发布闸不认它）。

`--receipt-only`（−3 前置自检用）：只重验收据绑定——report sha（有 amendment_chain 时按最后一条 after_sha256）、workorder effective sha、facts/state/a4_seal/rounds sha、freeze revision、verdict==PASS——不跑子检查。任一不符 exit 2，文案"closeout 收据与现场漂移: <项>，退回 −2 重跑 stage2_closeout"。

### E6 `amend`

−3 每写一条工单 `amendments[]` 后运行：前置：收据在场且 verdict=PASS；工单最后一条 `amendments[-1].after_sha256 == 报告实物 sha`，`before_sha256 == 收据当前记录的报告 sha`（首条对 `report_md.sha256`，后续对 `amendment_chain[-1].after_sha256`）。只重跑 #2 a4_seal_integrity、#5、#6、#7、#8、#11（措辞/图路径类修正能影响的项），全部 PASS 才追加 `amendment_chain[] {before_sha256, after_sha256, checks_rerun:[...], verdict}` 并更新 `workorder.effective_sha256`；否则 exit 2 不写。

## §F 测试 `scripts/tests/test_stage2_closeout.py`（登记进 `run_all.py:206` 之后：`SUITE += ['test_stage2_closeout.py']`）

夹具：复用 `test_a4_gate.py` 的链（`build_case`(test_audit_release_gate) → `shutil.copytree`＋`rebind_case_inputs` → 删净室件 → `add_distribution_initial` → `add_camp_series` → `a4_gate finalize --workflow-type new-analysis` → `finish_distribution_normal`，见 `test_a4_gate.py:489-503`），得到一个**没有** fig1/fig2 收据、没有 A5 seal 的 new-analysis 案；facts.entities 需至少一个 label 以 `大庄` 开头的实体（build_case 的 facts 若不是，测试内改 facts 并同步 state.whale_groups[].label 与 identity_gate.state_sha256，参照 `add_camp_series` `:272-275` 的重绑法）。写一份最小工单（`fill-workorder` 生成骨架后补 fig2/flow 选材）。图注：往 report.md 的终态图引用行后追加按 E2 规则渲染的一段。

用例（名称固定，便于验收对照）：
1. `dryrun_profile_exempts_stage3_artifacts`：无三件 −3 产物，`check` PASS，收据 verdict=PASS，`pending_for_stage3` 含 a5_report_seal。
2. `only_findings_changed_is_rejected`：改 `findings.md` 一字 → `check` BLOCK 且 detail 含 `封口后被改动`。
3. `stale_claims_sha_detected`：改 `a4_claims.json` 的 `registered_at_utc` → BLOCK，downstream_stale 项 `item` 含 `adversarial_review`（夹具若无 adversarial_review.json，则用 rounds terminal `a4_seal_sha` 项：改 a4_seal.json 一字节后 BLOCK）。
4. `old_receipt_new_report_rejected`：PASS 后改报告一字 → `--receipt-only` exit 2。
5. `fig2_entity_id_must_be_facts_key`：`fig2.lines[0].entity_id` 写成展示名 → BLOCK 文案含 `fig2.lines[0].entity_id`。
6. `fig2_required_from_label`：required 由 label 前缀得出且非空；把 lines 清空 → BLOCK。
7. `flow_items_compat_and_extra_allowed`：`flow.items` 形式通过；eligible 多一个未达门槛实体仍 PASS；漏掉 ≥20% 的大庄 → BLOCK。
8. `caption_mismatch_rejected`：图注里把一个桶百分比改掉 → BLOCK。
9. `amend_chain_updates_receipt`：改报告一处措辞并写 `amendments[]` → `amend` exit 0，`amendment_chain` 长 1，`--receipt-only` PASS。
10. `fill_never_overwrites_report_anchor`：工单已有 `bindings.report_md` 旧 sha，`fill-workorder` 后不变。
11. `low_sample_terminal_not_blocked`：夹具本身 owner 少落 low_sample（`finish_distribution_normal` 注释），PASS 用例覆盖即可，单列断言 `a5_distribution` PASS。
12. `fig2_series_subcommand_roundtrip`：`fig2-series` 产 whale_series＋provenance，`check` 子命令 PASS，closeout #9 PASS；篡改 whale_series 一位 → #9 BLOCK。
13. `downstream_check_cli_exit3`：`a4_gate.py downstream-check` 在用例 3 的状态下 exit 3。

## §7 验收（Fable 做，写这里供施工方自检）

- `run_all.py` 全 PASS（含新用例）；`test_a4_gate.py` 单跑 PASS（G9 文案不变）。
- **APU 0914 完整 closeout**：`stage2_closeout.py check --case-dir <APU> --report 报告.md` 须 PASS。⚠ 前提：W1-C 标签四址**尚未入库**——`labels_manifest` 内容哈希进 scan 语义（`holder_distribution_scan.py:656/:715-718`），标签库一变 APU 的 initial/final scan 重验必"语义与独立重算不一致"。因此 W1-C 的执行时点改为 **W2 验收之后**（Fable 在 W1 工单 v2 里改）。
- BTW 纯规则：用 BTW `facts.json`/`analysis-state.json`/工单结构在临时目录跑 E3 的 fig2/flow 判定函数（直接 import 函数，不跑全 check）：required 含 `e_proj`，`flow.items` 兼容。
- 原案回测（改前红改后绿，在案卷副本上做）：MELANIA 图注不同源 → #7 BLOCK；COLLECT fig2 展示名 → #10 BLOCK；LIT identity resolution 空 → #4 BLOCK。
