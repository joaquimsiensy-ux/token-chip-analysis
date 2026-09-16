# W3 施工工单：`stage2_closeout.py reseal`＋手册净减＋CHANGELOG/VERSION 7.1.0

> 版本 **v3**（2026-09-16，融合 codex 对 v2 的只读复核八条，原文 `scratchpad/cx_reply_w3v2.txt`；待 W2 合入后校一次行号再派工）。W1 落地事实：reopen 回执是案根 `distribution_reopen.json`（schema `distribution-reopen/v1`，`cycles[]` 严格递增），`reopen-cycle` 会把 `a4_seal.json` 与其 registry **复制**进 `data/stage2/dist_cycle<N>/a4_snapshot/`，拒绝 `charts/final` 含终态图以外的文件、拒绝台账引用 `dist_rounds/` 之外的文件、拒绝 `terminal.final_chart_path` 非终态图路径；成功后打印 NORMAL/LOW_SAMPLE 与 ABNORMAL 两条分支提示（`holder_distribution_scan.py:1309`）。W2 契约（v6）：`stage2_closeout.py check|fill-workorder|amend`、`a4_gate.py downstream-check`（exit 3 有过期项）、收据 `stage2_closeout_receipt.json`。依据已批计划 `plan_v2_approved.md` §2.3、§2.8、§4、§5。行号以 W2 合入后的实物为准，本单只给 764b60c 基线锚，施工方开工先 `grep -n` 锚文本重定位。
>
> v3 相对 v2 的改动（codex 复核逐条）：①迁移检测提到 A0 第 0 步（拒绝后全案不变）；②分布裁决改调 `distribution-validate`（freeze 同款 `handoff_manifest.py:1480-1482`）；③补 final-source（ABNORMAL）分支＝先建非终态轮再 finalize，旧 seal 引用已归档路径即停；④轮号一律 `len(rounds)+1`（`:909` 错轮号会把输出写成 data_broken `:1005`）；⑤verdict 停点给出恢复路径；⑥`casebook_note` 为 null 时省略参数；⑦canon 写成固定序列化；⑧解释失败原因从 stdout＋stderr 一并透传，waiver 须 ≥ 第 2 轮（`:1354`）；⑨手册 :136 替换边界收窄、保留 `holder_distribution_current.png`（`CT-DISTRIBUTION-15`）与 `a4-seal/v4`（`CT-DISTRIBUTION-16`）、sealed 读取申报仍人工必填、:117 悬空引用同步、:180 补 `amend`、:94/:154"无 validator"同步；⑩白名单加 `pyproject.toml`；⑪A1 用例改用 `test_handoff_manifest` 可 freeze 夹具，用例 1 不覆盖真实 adversarial_review.json；⑫算法绑定改读 provenance 台账；⑬`--verdicts-file` 须案内持久；⑭APU 备份改案外同级目录、dry-run 验收改路径→sha 映射＋目录清单。**未采纳/存疑**：codex 说"APU initial scan 绑旧扫描器 sha、finalize 会重验并拒"——`validate_scan`（`holder_distribution_scan.py:1016-1080`）不比对 `input_binding.algorithm.sha256`，此说未核实，记入 §E 待实测，不写进 reseal 逻辑。

## §0 开工纪律
同 W1/W2：只改白名单——`scripts/report/stage2_closeout.py`（加 `reseal` 子命令）、`references/split-run.md`、`references/analyze-workflow.md`、`references/report-template.md`（本单**不改**它，列出只为 `wc -c` 验收）、`CHANGELOG.md`、`VERSION`、`pyproject.toml`（仅 `project.version` 行 `7.0.4`→`7.1.0`，`test_version_consistency.py:14` 读它）、`SKILL.md`（仅版本标记行 `<!-- skill-version-source: VERSION; skill-version: 7.0.4 -->` → 7.1.0，`test_version_consistency.py:22`）、`scripts/tests/run_all.py`、`scripts/tests/invariant_manifest.json`（仅登记 reseal 新增的 `os.replace` 写入函数 `overwrite_single`，格式与去重规则同 W2 §0.2；不得删改既有行）、新建 `scripts/tests/test_stage2_reseal.py`。禁改 `handoff_manifest.py`、`a4_gate.py` 既有函数、`holder_distribution_scan.py`、`a5_report_seal.py`、`distribution_explanation_check.py`、`adjudication_validator.py`（只调用）。顺序 A（reseal）→ B（测试）→ C（手册）→ D（CHANGELOG/VERSION/SKILL/pyproject）。先红后绿证据 `w3_red_evidence.txt`，完工 `w3_done.md`，不 commit。开工前工作树须干净（`git status --short` 空），否则停工写 done 请示；全程不读 `~/.codex`。

## §A `reseal` 子命令

用法：`stage2_closeout.py reseal --case-dir <案根> --report 报告.md --from freeze|a4|rounds [--claims-file <json>] [--verdicts-file <案内 json>] [--seal-files a,b,c] [--dry-run]`。退出：0 完成并已跑 `check`；3 停点（列原因与下一步）；2 前置不过；1 脚本错。全程 stdout 打印"层｜动作｜将失效下游件"表（dry-run 只打印不执行）。所有子步骤用 `subprocess.run([sys.executable, <脚本>, ...], capture_output=True, text=True)` 调现有 CLI，**不复制其逻辑**；子命令非 0 时把它的 **stdout＋stderr 一并**原样透传（`holder_distribution_scan.py` 的 BLOCK 原因打在 stdout，`:1006/:1355/:1360`）。

### A0 预检与归档（所有 `--from`；第 0-2 步只读，任一失败全案不变）
0. **案根迁移检测**（最先）：读 `accounting_mode.json` 的 observation bundle 路径（`shared_release_receipt.py:367/:1755` 案根包含检查同款），任一绝对路径不在当前案根内 → exit 2"案根已迁移：observation bundle 绝对路径指向原案，reseal 须在原路径执行；未迁移重绑的复制案无法通过发布闸"。
1. 算法绑定硬约束：读 `provenance_ledger.json.input_binding.algorithm.files`（freeze 同源 `handoff_manifest.py:1178-1189`；`entity_freeze.json` 只存摘要不存路径），对 `entity_source_trace.py`／`wave_scan.py`／`sqd_cache_identity.py` 三项各调 `handoff_manifest.check_algorithm_file(rec, 当前仓库同名文件)`；缺 `input_binding` 或任一不等 → exit 2"须在与 freeze 记录同一 checkout 下运行"。
2. 失效表（按 `--from`）：freeze 层＝final scan（各轮）、rounds 全部行、a4（若 freeze revision 变）、adversarial_review/shared_release_receipt（按 registry sha 判，不按 seal revision，`shared_release_receipt.py:50` 输入不含 seal）、a5 seal、工单 bindings；a4 层＝去掉 final scan 之外同上；rounds 层＝rounds 行、终态图、a5 seal、工单 bindings.rounds/终态图。
3. `charts/final/`：把**除 `holder_distribution_current.png` 外**的文件 `shutil.move` 到 `data/stage2/_history/<UTC 时间戳>/charts_final/`（禁 rm）；分布终态图留给 `reopen-cycle`。
4. 若 `distribution_rounds.json` 有 `terminal`：调 `holder_distribution_scan.py reopen-cycle --case-dir . --reason "reseal --from <层> <UTC>"`（它会核 `charts/final` 只剩终态图，并把 a4_seal＋registry 复制进周期目录）。非 0 → exit 2 透传。台账在场但**非终态**（续跑场景）→ 跳过本步，后续轮号按 A3.1。**此步必须先于 A2 finalize**：`a4_gate finalize` 见台账 terminal 直接拒（`a4_gate.py:285`），顺序反了就是死锁。
5. `distribution_adjudications.json` 在场时：跑 `adjudication_validator.py distribution-validate --case-dir . --entity-file <freeze.entity_file>`（freeze 前置同款，`handoff_manifest.py:1480-1482`；**不是** `validate`，那个校的是 `candidate_adjudications.json`）；通过则不动；不通过且其绑定的 scan 路径已被第 4 步归档 → move 到同一 `_history/<ts>/` 并在 `reseal_log.json`（写在 `_history/<ts>/`，不进案根）记"失效原因＝绑定的分布扫描已随周期归档；终态后由 −2 重新承接裁决"；其它失败 → exit 2。
6. **分支判定**：读当前 `a4_seal.json.distribution_claim_source.stage`（APU 实况 `initial`）。`final` 或 `cluster_claim_ids` 非空 → 标记 **final-source 分支**：A2 之前先执行 A3.1＋A3.3（不带解释，得非终态轮），再进 A2；若该轮直接成为终态（形态已变 NORMAL/LOW_SAMPLE）→ exit 3"分布形态已变，旧 dist-* claims 失去 final 来源，须人工重定 claims；台账已终态，重封前需再 reopen-cycle"。

### A1 freeze（仅 `--from freeze`）
从当前 `entity_freeze.json` 顶层回读 `members_source`、`entity_file`、`pending_items`、`casebook_note`，回传 `handoff_manifest.py freeze --case-dir . --members <members_source> --entity-file <entity_file> [--pending <";".join(pending_items)>] [--casebook-note <casebook_note>]`（参数定义 `:1639-1646`）。**`pending_items` 为空列表时省略 `--pending`；`casebook_note` 为 `null` 时省略 `--casebook-note`**（默认 `None`，`:1646`；APU 当前即 null；不得传字符串 "None" 或空串）；非空时原样传。不传就会被清空并平白新增 revision（`:1582-1583/:1590-1593`）。四道前置任一不过（`:1456-1560`）即 exit 2 透传。成功后打印 revisions 是否增加（"无需新 revision" 也算成功）。

### A2 A4（`--from freeze|a4`）
1. claims：`--claims-file` 未给 → 取当前 `a4_claims.json.claims` 作为待登记；`canon(rows) = json.dumps(a4_gate.validate_claim_rows(case_dir, rows), sort_keys=True, ensure_ascii=False, separators=(",",":"))`（`registered_at_utc` 在数组之外，不需要删键）。**跳过 register 的条件（两者同时）**：①`canon(待登记) == canon(当前 a4_claims.json.claims)`；②`sha256(a4_claims.json 原始字节) == adversarial_review.json["claim_registry"]["sha256"]`（`adversarial_review_runner.py:673`；无 adversarial_review.json 时视为 ② 不成立，须 register）。不满足则 `a4_gate.py register`（`:312-330` 会重写并带时间戳），随后打印并 exit 3：`"registry 已变：按 runner 记录的实际路数重跑受影响复核 → adversarial_review_runner finalize → shared_release_receipt；完成后再跑 reseal --from a4"`（claims 变化即停，用户 §5 拍板 2）。
2. verdicts：`--verdicts-file` 未给 → 从当前 `a4_seal.json` 的 verdicts 文件（`verdicts.path`）复制到案根 `verdicts_rev<新 revision>.json`（**案内、封口后持续保留、禁删**；finalize 会把该路径与 sha 写进 seal，案外路径被 `safe_case_file` 拒，`a4_gate.py:407`）；给了 → 须在案内（否则 exit 2），并与旧 seal 逐 id 比对，任一 verdict 不同 → exit 3"A4 verdict 与上版有差异＝判断变更：请人工按 A4 流程 `a4_gate finalize` 封新 revision、按 `downstream-check` 重跑受影响复核，然后 `reseal --from rounds`"（不自动放行；reseal 不提供"确认"开关）。
3. `--seal-files` 未给 → 取当前 seal `sealed_files[].path`；**任一路径在磁盘不存在（如已随周期归档的 `dist_rounds/…`）→ exit 3 列出并要求显式 `--seal-files`**，不静默剔除。调 `a4_gate.py finalize --case-dir . --verdicts-file <上一步文件> --seal-files <…> --workflow-type new-analysis`；非 0 → exit 2 透传（含其 `distribution_claim_source` 对 initial/最新非终态 final scan 的独立重验 `:273-300`）。
4. 随后调 `a4_gate.py downstream-check`（W2）；仍有过期项 → 打印并 exit 3（例如 shared_release_receipt 需重跑）。

### A3 rounds（所有 `--from`）
1. 轮号 `n = len(rounds)+1`（无台账＝1；`:909` 与 `:1334` 都拒错轮号，且 `:1005` 会把指定输出写成 data_broken 覆盖旧 scan，故不得写死 1）。`holder_distribution_scan.py --case-dir . --stage final --round n`（W1 的 `find_snapshot` 自动从 initial 绑定解析快照；不传 `--snapshot`）。非 0 → exit 2。
2. 读新 scan：`verdict == "ABNORMAL_SHAPE"` 且旧周期最后一轮 `explanation_path` 非空 → 用**当前** scan 与 seal 重新生成解释：`distribution_explanation_check.py --case-dir . --scan dist_rounds/round_n/distribution_scan.json --a4-seal a4_seal.json --out dist_rounds/round_n/explanation.json`（`:183-192`；旧解释绑旧 scan/seal 不能复用）；它 BLOCK → record-round **不带** `--explanation`（带失败解释同样是非终态 UNEXPLAINED，只是台账多记一份解释文件 `:1351`；本单选不带），并在末尾 exit 3 列"解释检查失败：<其 stdout＋stderr>"。旧轮为 WAIVED → 不继承：仍先 record 本轮（不带解释，非终态），再 exit 3"waiver 须 ≥ 第 2 轮（`:1354`）且重新绑定当前 scan/seal/台账（`:1096-1098`）：补证据/复核 → 需要则 finalize → `--stage final --round n+1` → 人工 waiver record"。
3. `holder_distribution_scan.py record-round --case-dir . --scan dist_rounds/round_n/distribution_scan.json [--explanation dist_rounds/round_n/explanation.json]`。输出含 `REQUIRES_A4_REFLOW` 或 scan `new_clusters` 非空 → exit 3"新簇回流 A4"。
4. 终态（NORMAL/LOW_SAMPLE/EXPLAINED）→ 继续 A4 收尾；非终态 UNEXPLAINED → exit 3 并打印 ABNORMAL 分支下一步（"补证据/复核 → finalize → `reseal --from rounds`（轮号自动 n+1，带重生成的解释）"）。final-source 分支（A0.6）在此处不 exit，回到 A2。

### A4 收尾
先调 `stage2_closeout.py fill-workorder --case-dir . --report <报告>`（W2 E4：只更新机械绑定 a4_seal_sha256／entity_freeze_revision／rounds／终态 scan 与图／distribution_terminal／report_image_refs，`bindings.report_md` 原稿锚不动），再调 `stage2_closeout.py check --case-dir . --report <报告>`，透传 check 退出码（0/2）。reseal **不**画图、不写 A5、不改工单选材、不自动重跑对抗复核、不代替首次 A4 封口。

### dry-run
`--dry-run`：执行 A0 第 0-2 步与所有只读判断（分支判定、跳过条件、verdict 差异、失效表、将归档的文件清单、将调用的命令行、seal-files 缺失清单），不写任何文件、不建任何目录、不调任何会写盘的子命令，exit 0（前置不过仍 exit 2）。

## §B 测试 `scripts/tests/test_stage2_reseal.py`（登记 `run_all.py` SUITE）
A2–A4 用例沿 `test_stage2_closeout.py`（W2）的 new-analysis 全案链夹具（`build_release_case`）；**不得**用最小 `adversarial_review.json` 覆盖该夹具的真实 v4 文件（会让 shared receipt 绑定过期污染正例）。A1 用例用 `test_handoff_manifest.py` 的 `make_case`（`:73`）→ `generate` READY → `setup_freezeable`（`:275`）→ `freeze` 链构造真实可 freeze 案（`finish_distribution_normal` 的空 freeze 桩与 `test_batch15` 的三账夹具都没有完整 freeze 前置，不可用）。用例：
1. `skip_register_when_claims_same`：夹具原样（registry sha 与其 adversarial_review.json 一致）→ 不 register（`a4_claims.json` 字节不变）、finalize 后 seal revision +1。
2. `registry_sha_drift_forces_register`：改 `a4_claims.json` 的 `registered_at_utc` → canonical 相同但原始 sha 漂移 → register 被执行且 exit 3。
3. `verdict_change_stops`：`--verdicts-file`（案内）把一条 CONFIRMED 改 WEAKENED → exit 3，seal 未变；案外路径 → exit 2。
4. `terminal_ledger_triggers_reopen`：台账 terminal → reseal 后 `data/stage2/dist_cycle1/` 在场、新台账轮 1 终态、`charts/final` 只剩新终态图。
5. `other_charts_archived_not_deleted`：`charts/final/fig1.png` 被移到 `_history/<ts>/charts_final/`，字节相同。
6. `freeze_readback_no_new_revision`：可 freeze 夹具三变体（pending 非空＋casebook_note 非空；pending 空＋casebook_note null；两者皆非空）`--from freeze` 后 `revisions` 长度均不变、`pending_items`/`casebook_note` 值不变。
7. `dry_run_touches_nothing`：全案 **路径→sha 映射＋`os.walk` 目录清单** 前后完全相同（不是 sha 集合）。
8. `new_clusters_stop`：用 `test_distribution_gate.bump_balances` 类夹具让 final 出新簇 → exit 3 文案含"回流 A4"。
9. `ends_with_closeout_check`：成功路径末尾收据 `stage2_closeout_receipt.json` verdict=PASS，工单 `bindings.a4_seal_sha256` 已更新为新 seal、`bindings.report_md` 不变，新 seal `verdicts.path` 指向案内存在的文件。
10. `migrated_case_root_stops`：夹具 `accounting_mode.json` 写一个指向案外绝对路径的 observation bundle → exit 2 文案含"案根已迁移"，且映射＋清单不变（即使台账已 terminal 也不归档）。
11. `round_number_continues_nonterminal_ledger`：先造非终态轮 1（record-round 不带解释的 UNEXPLAINED 夹具，或 A0.4 跳过场景）→ `--from rounds` 用 round 2，`dist_rounds/round_1/distribution_scan.json` 字节不变。
12. `sealed_file_missing_stops`：夹具变体多封一份 `notes.md`，reseal 前把它 move 走 → 默认 seal-files 缺文件 → exit 3 列出该路径，seal 未变。

## §C 手册净减（施工原则：三册 `wc -c` 合计不增；基线 split-run 28162、analyze-workflow 34301、report-template 42499；每处改完记"删 N 字节／加 M 字节"，最终合计 ≤ 104962；`docs_lint` PASS——特别是 `contract_manifest` 的 CT-WAVE-16/17/18、CT-DISTRIBUTION-15/16 五枚针都在 split-run:136/:150，替换后必须仍在）
| 文件:行 | 现文（锚，只替换引号内这一段） | 改为 |
|---|---|---|
| split-run.md:136 | `→ final 分布扫描写 \`dist_rounds/round_N/\` → 新簇回流 A4；已覆盖异常跑解释五判据，未解释进入成员或机制闭环后回流 A4 → 唯一终态物化`（`a4-seal/v4` 之后、`\`charts/final/holder_distribution_current.png\`` 之前） | `→ final 分布扫描至终态（新簇回流 A4；重封一律 \`stage2_closeout reseal\`）→ 唯一终态物化`；同行 `§3b.3 收口自查` → `§3b.3 收口`。其余（EF-3 各针、`a4-seal/v4`、终态图名、正文亲笔成稿、工单交付即停）一字不动 |
| split-run.md:117 | `改挂 −2 收口自查（§3b.3 第⑤条）` | `改挂工单 \`stage2_selfcheck\` 申报（§3b.2）` |
| split-run.md:150 | 句尾 `…facts 与 state 在场——任一缺失或漂移停下报用户，禁带病开工禁补票。` | 五项改六项：`…facts 与 state 在场／\`stage2_closeout --receipt-only\` PASS——任一缺失或漂移停下报用户，禁带病开工禁补票。` |
| split-run.md:154 | `无 schema 版本、无 validator、不进 handoff manifest` | `无 schema 版本、\`stage2_closeout check\` 校验、不进 handoff manifest` |
| split-run.md:94 | `非正式件、无 validator、不进 handoff manifest` | `非正式件、closeout 校验、不进 handoff manifest` |
| split-run.md:158 | `entity_freeze_revision、` | `entity_freeze_revision（\`stage2_closeout fill-workorder\` 填）、` |
| split-run.md:165 | `\`stage2_selfcheck\`：−2 收口自查申报（§3b.3 五条＋刀 1 公告遵守申报）；` | `\`stage2_selfcheck\`：sealed/ 禁读令遵守申报（全程未读；违规读取写明何时、为何）——人工必填，机器不可验；其余自查由 closeout 收据覆盖；` |
| split-run.md:168-170 | §3b.3 标题＋五条整段 | 标题 `### 3b.3 −2 收口`；正文一句：`跑 \`stage2_closeout --case-dir . --report 报告.md\` 至 PASS（收据 \`stage2_closeout_receipt.json\` 覆盖图片引用一致、固定句式、翻转披露、原稿锚与发布闸干跑）；sealed/ 读取申报仍人工写进 \`stage2_selfcheck\`。` |
| split-run.md:176-177 | 两条（whale_series 落案根／现场 Python 调 plot_*） | 一条：`- 图 2 序列＝案根 \`whale_series.json\`（\`figures_from_facts fig2-series\` 按工单 series_source 装配，旁车 provenance 核 sha；发布闸只认案根）；图 2/3 仍现场调 standard_charts 库的 plot_whale_vs_price／plot_price_events，参数全部从工单声明的源文件读取，禁手抄数字、禁自行改选材。` |
| split-run.md:180 | `最小机械修正＋amendments 哈希链留痕；` | `最小机械修正＋amendments 哈希链留痕＋\`stage2_closeout amend\` 更新收据；` |
| split-run.md:184 | `不覆盖：图表应有基数（少画图仍可能过闸）、fig2 实体线覆盖完整性（figure2_check 只验已提供的线）、渲染输入与 check 输入的同一性、工单字段完备性——这些由工单字段约定＋−3 开工前置自检（3b.1）与交付自查申报承担，属用户已接受的残余风险（不设 validator 系用户 2026-08-18 拍板；首战后评估是否升级）。` | `不覆盖：渲染输入与 check 输入的同一性（PNG 未绑序列）——属用户已接受的残余风险（2026-08-18 拍板）；图表基数、fig2 必画下限、工单字段完备性自 7.1.0 由 \`stage2_closeout\` 承担。` |
| analyze-workflow.md:185 | `删除台账后从非首轮继续、终态后追加或同时存在多个 terminal 都会被拒绝。` | `终态后重开只走 \`holder_distribution_scan.py reopen-cycle\`。` |
| analyze-workflow.md:173 | `＋1 完整性批评角色查 findings/结论清单缺口（必查全史极值清单）` | `＋1 完整性批评角色查 findings/结论清单缺口（局限条目取 \`a4_gate limits-extract\` 输出，禁硬编码；必查全史极值清单）` |
report-template.md 不改。若某处替换后合计超 104962，优先再删 :184 的括注，不得动针所在段。

## §D 版本
- `VERSION` → `7.1.0`；`pyproject.toml` `project.version` → `7.1.0`；`SKILL.md` 版本标记行同步。
- `CHANGELOG.md`：索引段最上一行 `- **7.1.0**（YYYY-MM-DD）…`；详细段 `## [7.1.0] - YYYY-MM-DD — −2 收口与重封命令化` 置于 `## [7.0.4]` 之上（活跃文件严格降序、不得与活跃或归档撞号，`changelog_lint.py:32/:54/:57`）。内容＝stage2_closeout（check/fill-workorder/amend/reseal）、`audit_release_gate --profile stage2-dryrun`、`figures_from_facts fig2-series`、`a4_gate limits-extract/downstream-check/seal_integrity_errors`、`holder_distribution_scan reopen-cycle`＋`find_snapshot` 登记优先、手册净减字节数、SUITE 增量；**标签四址订正另记 `labels vX.Y` 前缀条目**（W1-C 正式入库时由 Fable 补，本单不写）。`changelog_lint`、`test_version_consistency` PASS。
- 压缩钩子改动不属 skill，不进 CHANGELOG。

## §E 验收（Fable）
run_all 全绿（沙箱端口两项本机复跑）；FORGGIE 已发布案 `audit_release_gate --profile new-analysis` 仍 PASS；三册 wc 合计 ≤ 104962 且五枚针仍在；`stage2_closeout --help` 列四子命令；MELANIA/COLLECT/LIT 原案子检查回测不回归。
**APU 0914（W2 挪来）**：副本被 A0.0 拦（accounting 绝对路径，未迁移重绑的复制案不可用），只能在**真案目录**跑。**用户 2026-09-16 裁决：先不真跑。** W3 验收对 APU 只到 `reseal --from a4 --dry-run`（只读）：验收方法＝跑前跑后对案根做 **路径→sha 映射＋目录清单** 比对完全相同（不是 sha 集合），并核 dry-run 输出的失效表（charts/final 三图归档、周期 1 归档、a4 rev2、final round 1、a5 seal/工单 bindings 失效）与分支判定＝initial。完整 closeout PASS 记为待办，待用户另行批准；届时前提另核：①codex 称 initial scan 绑旧扫描器 sha 会被 finalize 重验拒绝——`validate_scan` 不比对 algorithm sha，实测定夺；②APU 案根无 `whale_series.provenance.json`，须先 `fig2-series` 产旁车；③执行前对案根做整目录备份到**案外同级目录** `…/5.6筹码分析/_backup/APU分析_20260914_pre_reseal_<ts>/`（`cp -R`，禁 rm；不得放在案根自身 `_history/` 内，否则递归复制）。
