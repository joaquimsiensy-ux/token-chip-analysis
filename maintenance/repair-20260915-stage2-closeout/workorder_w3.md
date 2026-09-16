# W3 施工工单：`stage2_closeout.py reseal`＋手册净减＋CHANGELOG/VERSION 7.1.0

> 版本 **v2**（2026-09-16，Fable 按 W1 已合入实物（main 4cd65f6）与 W2 工单 v6 契约修订；待 W2 合入后校一次行号再派工）。W1 落地事实：reopen 回执是案根 `distribution_reopen.json`（schema `distribution-reopen/v1`，`cycles[]` 严格递增），`reopen-cycle` 会把 `a4_seal.json` 与其 registry **复制**进 `data/stage2/dist_cycle<N>/a4_snapshot/`，拒绝 `charts/final` 含终态图以外的文件、拒绝台账引用 `dist_rounds/` 之外的文件、拒绝 `terminal.final_chart_path` 非终态图路径；成功后打印 NORMAL/LOW_SAMPLE 与 ABNORMAL 两条分支提示。W2 契约（v6）：`stage2_closeout.py check|fill-workorder|amend`、`a4_gate.py downstream-check`（exit 3 有过期项）、收据 `stage2_closeout_receipt.json`。依据已批计划 `plan_v2_approved.md` §2.3、§2.8、§4、§5 及 W1 v2 对计划的两处修订：①`charts/final` 归档职责＝reseal 只搬**非**终态分布图的其它图，终态分布图由 `reopen-cycle` 搬（codex W1 复核第 5 条）；②重开后的条件分支＝NORMAL/LOW_SAMPLE 形态只有"claims 与 initial 闭合 → 先 finalize → 轮 1 终态"一条路，ABNORMAL 才有"轮 1 UNEXPLAINED → finalize → 轮 2"（codex W1 复核第 8 条，`a4_gate.py:282-284`、`holder_distribution_scan.py:1113-1119`）。行号以 W2 合入后的实物为准，本单只给 764b60c 基线锚，施工方开工先 `grep -n` 锚文本重定位。

## §0 开工纪律
同 W1/W2：只改白名单——`scripts/report/stage2_closeout.py`（加 `reseal` 子命令）、`references/split-run.md`、`references/analyze-workflow.md`、`references/report-template.md`（本单**不改**它，列出只为 `wc -c` 验收）、`CHANGELOG.md`、`VERSION`、`SKILL.md`（仅版本标记行 `<!-- skill-version-source: VERSION; skill-version: 7.0.4 -->` → 7.1.0，`test_version_consistency.py:22` 要求）、`scripts/tests/run_all.py`、`scripts/tests/invariant_manifest.json`（仅登记 reseal 新增的 `os.replace` 写入函数 `overwrite_single`，格式与去重规则同 W2 §0.2；不得删改既有行）、新建 `scripts/tests/test_stage2_reseal.py`。禁改 `handoff_manifest.py`、`a4_gate.py` 既有函数、`holder_distribution_scan.py`、`a5_report_seal.py`、`distribution_explanation_check.py`（只调用）。顺序 A（reseal）→ B（测试）→ C（手册）→ D（CHANGELOG/VERSION/SKILL 标记）。先红后绿证据 `w3_red_evidence.txt`，完工 `w3_done.md`，不 commit。

## §A `reseal` 子命令

用法：`stage2_closeout.py reseal --case-dir <案根> --report 报告.md --from freeze|a4|rounds [--claims-file <json>] [--verdicts-file <json>] [--seal-files a,b,c] [--dry-run]`。退出：0 完成并已跑 `check`；3 停点（列原因）；2 前置不过；1 脚本错。全程 stdout 打印"层｜动作｜将失效下游件"表（dry-run 只打印不执行）。所有子步骤用 `subprocess.run([sys.executable, <脚本>, ...])` 调现有 CLI，**不复制其逻辑**。

### A0 预检与归档（所有 `--from`）
1. 硬约束：`entity_freeze.json` 若记录了算法文件绑定，其 `path` 的 realpath 须等于当前仓库同名文件（`handoff_manifest.py:806-829 check_algorithm_file` 同规则）；不等 → exit 2"须在与 freeze 记录同一 checkout 下运行"。
2. 失效表（按 `--from`）：freeze 层＝final scan（各轮）、rounds 全部行、a4（若 freeze revision 变）、adversarial_review/shared_release_receipt（按 registry sha 判，不按 seal revision，`shared_release_receipt.py:50` 输入不含 seal）、a5 seal、工单 bindings；a4 层＝去掉 final scan 之外同上；rounds 层＝rounds 行、终态图、a5 seal、工单 bindings.rounds/终态图。
3. `charts/final/`：把**除 `holder_distribution_current.png` 外**的文件 `shutil.move` 到 `data/stage2/_history/<UTC 时间戳>/charts_final/`（禁 rm）；分布终态图留给 `reopen-cycle`。
4. 若 `distribution_rounds.json` 有 `terminal`：调 `holder_distribution_scan.py reopen-cycle --case-dir . --reason "reseal --from <层> <UTC>"`（W1 产物；它会核 `charts/final` 只剩终态图，并把 a4_seal＋registry 复制进周期目录）。非 0 → exit 2 透传其输出。**此步必须先于 A2 finalize**：`a4_gate finalize` 见台账 terminal 直接拒（`a4_gate.py:285`），顺序反了就是死锁。
6. **案根迁移检测**：读 `accounting_mode.json` 的 observation bundle 路径（`shared_release_receipt.py:367/:1755` 案根包含检查同款），任一绝对路径不在当前案根内 → exit 2"案根已迁移：observation bundle 绝对路径指向原案，reseal 须在原路径执行（复制案无法通过发布闸）"。APU 0914 实况如此，见 §E。
5. `distribution_adjudications.json` 在场时：先跑 `adjudication_validator.py validate --case-dir . --entity-file <freeze.entity_file>`（freeze 前置 1 同款，`handoff_manifest.py:1468-1475`）；通过则不动；不通过且其绑定的 scan 路径已被第 4 步归档 → move 到同一 `_history/<ts>/` 并在 `reseal_log.json`（写在 `_history/<ts>/`，不进案根）记"失效原因＝绑定的分布扫描已随周期归档；终态后由 −2 重新承接裁决"；其它失败 → exit 2。

### A1 freeze（仅 `--from freeze`）
从当前 `entity_freeze.json` 顶层回读 `members_source`、`entity_file`、`pending_items`（`";".join`）、`casebook_note`，原样回传 `handoff_manifest.py freeze --case-dir . --members <members_source> --entity-file <entity_file> --pending <…> --casebook-note <…>`（参数定义 `:1639-1646`；不传 `--pending/--casebook-note` 会被清空并平白新增 revision，`:1582-1583/:1590-1593`）。四道前置任一不过（`:1456-1560`）即 exit 2 透传。成功后打印 revisions 是否增加（`:1591-1593` "无需新 revision" 也算成功）。

### A2 A4（`--from freeze|a4`）
1. claims：`--claims-file` 未给 → 取当前 `a4_claims.json.claims` 作为待登记；规范化函数 `canon(claims)` = 经 `a4_gate.validate_claim_rows(case_dir, rows)` 后 `json.dumps(sort_keys)`（剔除 `registered_at_utc` 这一顶层键）。**跳过 register 的条件（两者同时）**：①`canon(待登记) == canon(当前 a4_claims.json.claims)`；②`sha256(a4_claims.json 原始字节) == adversarial_review.json["claim_registry"]["sha256"]`（`adversarial_review_runner.py:673`；无 adversarial_review.json 时视为 ② 不成立，须 register）。不满足则 `a4_gate.py register`（`:312-330` 会重写并带时间戳），随后打印停点提示但**不 exit**：`"registry 已变：按 runner 记录的实际路数重跑受影响复核 → adversarial_review_runner finalize → shared_release_receipt；完成后再跑 reseal --from a4"`，然后 exit 3（claims 变化即停，用户 §5 拍板 2）。
2. verdicts：`--verdicts-file` 未给 → 从当前 `a4_seal.json.claims[]` 取 `{id, verdict, revision_note}`；给了 → 与旧 seal 逐 id 比对，任一 verdict 不同 → exit 3"A4 verdict 与上版有差异，请人工确认后带 --verdicts-file 重跑并附 revision_note"（不自动放行）。
3. `--seal-files` 未给 → 取当前 seal `sealed_files[].path` 列表。调 `a4_gate.py finalize --case-dir . --verdicts-file <tmp> --seal-files <…> --workflow-type new-analysis`；`charts/final` 此时应为空（A0 已处理）；非 0 → exit 2 透传。
4. 随后调 `a4_gate.py downstream-check`（W2）；仍有过期项 → 打印并 exit 3（例如 shared_release_receipt 需重跑）。

### A3 rounds（所有 `--from`）
1. `holder_distribution_scan.py --case-dir . --stage final --round 1`（W1 的 `find_snapshot` 自动从 initial 绑定解析快照；不传 `--snapshot`）。非 0 → exit 2。
2. 读新 scan：`verdict == "ABNORMAL_SHAPE"` 且旧周期最后一轮 `explanation_path` 非空 → 用**当前** scan 与 seal 重新生成解释：`distribution_explanation_check.py --case-dir . --scan dist_rounds/round_1/distribution_scan.json --a4-seal a4_seal.json --out dist_rounds/round_1/explanation.json`（`:183-192`；旧解释绑旧 scan/seal 不能复用）；它 BLOCK（UNEXPLAINED）→ 仍继续到 record-round 但不带 `--explanation`（得非终态 UNEXPLAINED），并在末尾 exit 3 列"解释检查失败：<其 stderr>"。旧轮为 WAIVED → 不继承，exit 3 提示"waiver 须重新绑定当前 scan/seal/台账后人工 record"。
3. `holder_distribution_scan.py record-round --case-dir . --scan dist_rounds/round_1/distribution_scan.json [--explanation dist_rounds/round_1/explanation.json]`。输出含 `REQUIRES_A4_REFLOW` 或 scan `new_clusters` 非空 → exit 3"新簇回流 A4"。
4. 终态（NORMAL/LOW_SAMPLE/EXPLAINED）→ 继续；非终态 UNEXPLAINED（未带解释）→ exit 3 并打印 ABNORMAL 分支下一步（"补证据/复核 → finalize → --stage final --round 2 带 --explanation"）。

### A4 收尾
先调 `stage2_closeout.py fill-workorder --case-dir . --report <报告>`（W2 E4：只更新机械绑定 a4_seal_sha256／entity_freeze_revision／rounds／终态 scan 与图／distribution_terminal／report_image_refs，`bindings.report_md` 原稿锚不动），再调 `stage2_closeout.py check --case-dir . --report <报告>`，透传 check 退出码（0/2）。reseal **不**画图、不写 A5、不改工单选材、不自动重跑对抗复核。

### dry-run
`--dry-run`：执行 A0 第 1 步与所有只读判断（跳过条件、verdict 差异、失效表、将归档的文件清单、将调用的命令行），不写任何文件、不调任何会写盘的子命令，exit 0。

## §B 测试 `scripts/tests/test_stage2_reseal.py`（登记 `run_all.py` SUITE）
夹具沿 `test_stage2_closeout.py`（W2）的 new-analysis 全案链，并需要 `entity_freeze.json` 真实可 freeze（若 W2 夹具用的是 `finish_distribution_normal` 的空 freeze 桩 `{"schema":"entity-freeze/v1","revisions":[]}`，A1 用例改用 `test_batch15_three_ledgers_frozen.build_unit_case` 类可 freeze 夹具，或标注 A1 只做 dry-run 级用例并在 done 说明）。用例：
1. `skip_register_when_claims_same`：canonical 相同且 registry sha 与 adversarial_review 一致（夹具写一份最小 `adversarial_review.json` 含 `claim_registry.sha256`）→ 不 register（`a4_claims.json` 字节不变）、finalize 后 seal revision +1。
2. `registry_sha_drift_forces_register`：改 `registered_at_utc` → canonical 相同但 sha 漂移 → register 被执行且 exit 3。
3. `verdict_change_stops`：`--verdicts-file` 把一条 CONFIRMED 改 WEAKENED → exit 3，seal 未变。
4. `terminal_ledger_triggers_reopen`：台账 terminal → reseal 后 `data/stage2/dist_cycle1/` 在场、新台账轮 1 终态、`charts/final` 只剩新终态图。
5. `other_charts_archived_not_deleted`：`charts/final/fig1.png` 被移到 `_history/<ts>/charts_final/`，字节相同。
6. `freeze_readback_no_new_revision`（若可 freeze 夹具可得）：`--from freeze` 后 `revisions` 长度不变。
7. `dry_run_touches_nothing`：全案文件 sha 集合前后相同。
8. `new_clusters_stop`：用 `test_distribution_gate.bump_balances` 类夹具让 final 出新簇 → exit 3 文案含"回流 A4"。
9. `ends_with_closeout_check`：成功路径末尾收据 `stage2_closeout_receipt.json` verdict=PASS，且工单 `bindings.a4_seal_sha256` 已更新为新 seal、`bindings.report_md` 不变。
10. `migrated_case_root_stops`：夹具 `accounting_mode.json` 写一个指向案外绝对路径的 observation bundle → exit 2 文案含"案根已迁移"，全案文件 sha 不变。

## §C 手册净减（施工原则：三册 `wc -c` 合计不增；基线 split-run 28162、analyze-workflow 34301、report-template 42499）
| 文件:行 | 现文（锚） | 改为 |
|---|---|---|
| split-run.md:136 | `→ A4 register/finalize 产 \`a4-seal/v4\` → final 分布扫描写 \`dist_rounds/round_N/\` → 新簇回流 A4；已覆盖异常跑解释五判据，未解释进入成员或机制闭…`（整段从"→ A4 register"起到句末） | `→ A4 封口与分布终态一律 \`stage2_closeout reseal\`（重封）／\`stage2_closeout\`（收口）` |
| split-run.md:150 | 句尾 `…facts 与 state 在场——任一缺失或漂移停下报用户，禁带病开工禁补票。` | 五项改六项：`…facts 与 state 在场／\`stage2_closeout --receipt-only\` PASS——任一缺失或漂移停下报用户，禁带病开工禁补票。` |
| split-run.md:158 | `entity_freeze_revision、` | `entity_freeze_revision（\`stage2_closeout fill-workorder\` 填）、` |
| split-run.md:165 | `\`stage2_selfcheck\`：−2 收口自查申报（§3b.3 五条＋刀 1 公告遵守申报）；` | `\`stage2_selfcheck\`（可选）：sealed/ 读取申报（冻结前未读；冻结后何时、为何读取）；` |
| split-run.md:168-170 | §3b.3 标题＋五条整段 | 标题改 `### 3b.3 −2 收口`，正文一句：`跑 \`stage2_closeout --case-dir . --report 报告.md\` 至 PASS（收据 \`stage2_closeout_receipt.json\`；它覆盖原五条自查与发布闸干跑）。` |
| split-run.md:176-177 | 两条（whale_series 落案根／现场 Python 调 plot_*） | 一条：`- 图 2 序列消费 −2 产的 whale_series.json（\`figures_from_facts fig2-series\`，核 provenance sha）；图 2/3 仍现场调 standard_charts 的 plot_whale_vs_price／plot_price_events，参数全部来自工单声明的源文件。` |
| split-run.md:184 | `、工单字段完备性——这些由工单字段约定＋−3 开工前置自检（3b.1）与交付自查申报承担，属用户已接受的残余风险（不设 validator 系用户 2026-08-18 拍板；首战后评估是否升级）。` | `——这些属用户已接受的残余风险（2026-08-18 拍板）。` |
| analyze-workflow.md:185 | `删除台账后从非首轮继续、终态后追加或同时存在多个 terminal 都会被拒绝。` | `终态后重开只走 \`holder_distribution_scan.py reopen-cycle\`。` |
| analyze-workflow.md:173 | `＋1 完整性批评角色查 findings/结论清单缺口（必查全史极值清单）` | `＋1 完整性批评角色查 findings/结论清单缺口（局限条目取 \`a4_gate limits-extract\` 输出，禁硬编码；必查全史极值清单）` |
每处改完记"删 N 字节／加 M 字节"，最终 `wc -c` 三册合计 ≤ 104962；`docs_lint` PASS（引用无断链）。report-template.md 不改。

## §D 版本
- `VERSION` → `7.1.0`；`SKILL.md` 版本标记行同步；`CHANGELOG.md` 索引一行＋详细段 `## [7.1.0] - <日期> — −2 收口与重封命令化`：内容＝stage2_closeout（check/fill-workorder/amend/reseal）、`audit_release_gate --profile stage2-dryrun`、`figures_from_facts fig2-series`、`a4_gate limits-extract/downstream-check/seal_integrity_errors`、`holder_distribution_scan reopen-cycle`＋`find_snapshot` 登记优先、手册净减字节数、SUITE 增量；**标签四址订正另记 `labels vX.Y` 前缀条目**（在 W1-C 正式入库那次由 Fable 补，本单不写）。`changelog_lint`、`test_version_consistency` PASS。
- 压缩钩子改动不属 skill，不进 CHANGELOG。

## §E 验收（Fable）
run_all 全绿；FORGGIE 已发布案 `audit_release_gate --profile new-analysis` 仍 PASS；三册 wc 合计 ≤ 104962；`stage2_closeout --help` 列四子命令。
**APU 0914 完整 closeout 验收（W2 挪来）**：副本被 A0.6 拦（accounting 绝对路径），只能在**真案目录**跑——先 `reseal --from a4 --dry-run`（只读，输出失效表：charts/final 三图归档、周期 1 归档、a4 rev2、final round 1、a5 seal/工单 bindings 失效）；真跑会归档 −3 三图与周期 1、封 a4 rev2、重跑 final scan——**属 ③ 档改真实案卷，须用户拍板后执行**，执行前对案根做 `_history/pre_reseal_<ts>/` 整目录备份（`cp -R`，禁 rm）。用户不批则 W3 验收只到 dry-run，完整 PASS 记为待办。
