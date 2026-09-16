# W2 施工工单：−2 收口命令 `stage2_closeout.py`（check / fill-workorder / amend）＋四处现有脚本挂点

> 版本 **v3**（2026-09-16，Fable 按 codex 第二轮只读复核 `scratchpad/cx_reply_w2v2.txt` 八条修订；v2 被退回。v1 复核见 `cx_reply_w2.txt`）。依据已批计划 `plan_v2_approved.md` §2.2、§2.4、§4、§6。**开工前提：W1 已合入 main**（本单调用 W1 的 `find_snapshot(case_dir, requested, stage)`、`a4_gate limits-extract` 与 `holder_distribution_scan` 的 `reopened_from_cycle` 字段）。行号一律以**开工时 HEAD 的实物**为准，下文行号是 764b60c 基线锚点，W1 已使 `a4_gate.py` 位移（`main` 已到 `:574` 附近、分派字典在 `:600` 附近），**按锚文本定位，不按旧行号施工**。
>
> v2 相对 v1 的改动摘要（复核时对照）：§A 明确 dryrun 下 `report` 只剩非 None 检查；§B 纯函数契约不抛 SystemExit、`fig2-series` 旁车三项绑定＋重放核验、日期消费说明；§C G9 抽取统一返回 `(errors, sealed_paths)`、前缀契约、`:431-442` 消费点；§E1 facts_gate 三元组、A5 bundle 按 `status` 判、dual_basis 缺失 NOTE、#9 历史输入迁移；§E2 原始 `pct >= 0.01` 分界、零值兼容、top-k/HHI 缺失 NOTE；§E3 flow 流通分母、图中实体＝eligible、amendments 逐条链＋必备字段、合并线本版不支持；§E5/E6 收据补 whale_series/skill_commit 复验、amend 校验未获准字段并全量重跑；§F 夹具从 `test_a4_gate.main` 复制 facts/state/identity 并构造 ≥20% 大庄、用例 3 用真实 registry 漂移、补 WAIVED 与 BTW 图注兼容用例；§7 APU 完整 closeout 挪到 W3（reseal 迁移副本）。
>
> **v3 相对 v2 的改动摘要**：§B/E1-9 图 2 交叉绑定写死（旁车 out 必须是案根 whale_series.json、旁车输入与工单每条 `series_source` 逐条等值、重放**字节**等于实物、拒重复 entity_id、display_label 与 facts 同源、time_range 本版不消费记 NOTE、PNG 消费边界如实写）；E5/E6 冻结完整 amendments 内容（`amendments_sha256`）、追加时验旧前缀未变、从现稿反向重放 `exact_change` 证明"实际改动＝获准改动"、放行语义统一为"verdict PASS（无 BLOCK，NOTE 不拦）"、工单字段一律不可 amend；E3 补 `{path,sha256}` 通用实物重验与各图最小结构（按路径值不按键名，兼容 APU/BTW 两套键名）；§F 夹具三处硬错误改正（总量/现值/峰值统一 100、裁决只给 C1、不覆盖真实 adversarial_review.json、先写完正文再首次 fill）；§7 APU 改为纯规则验收（同 BTW），组合 closeout 完整 PASS 整体留 W3；§0 白名单补 `scripts/tests/invariant_manifest.json`（仅新增 schema 登记）；合并线不支持明确记为**对已批计划的范围调整**。

## §0 开工纪律（逐条遵守）

1. 工作树 `~/.claude/skills/token-chip-analysis`，main；开工先 `git log -1 --format=%H` 记进 `w2_done.md`；`git status` 须干净。**禁读 `~/.codex`**（含其 memories）；离线（不下载任何源）。
2. **只新建一个脚本** `scripts/report/stage2_closeout.py`。其余改动全部落在现有文件：`audit_release_gate.py`、`figures_from_facts.py`、`a4_gate.py`、`build_html.py`、`scripts/tests/run_all.py`、`scripts/tests/invariant_manifest.json`（**只允许新增 schema 登记行**：`stage2_closeout.py` producer/consumer 登记 `stage2-closeout/v1`，`figures_from_facts.py` producer 登记 `fig2-series-provenance/v1`，`stage2_closeout.py` consumer 登记 `fig2-series-provenance/v1`；W1 已登记的 3 行保留；若 `invariant_scan.py` 还报其他未登记项，停工写进 `w2_done.md` 请示，不得自行扩）；新建测试 `scripts/tests/test_stage2_closeout.py`。
3. **禁改**：`a4_gate.py` 的 `cmd_register`/`cmd_finalize`/`distribution_claim_source`/`validate_revision_chain`（只加新函数与新子命令）；`holder_distribution_scan.py`（只调用）；`a5_report_seal.py`（只调用）；`entity_identity_gate.py`；`facts_gate.py`；`standard_charts.py`；三册手册与 CHANGELOG/VERSION（W3 改）。
4. 顺序 A → B → C → D → E → F。每段先跑红证据（`w2_red_evidence.txt`），再改，再绿。
5. 不 commit；完工写 `maintenance/repair-20260915-stage2-closeout/w2_done.md`（改动清单、每条测试的红→绿证据、run_all 结果行、未做项与原因）。
6. **对已批计划的范围调整（施工方知悉即可，裁决在调度方）**：已批计划 §2.4 写"合并线用 `merge_groups[].member_entity_ids` 表示覆盖"，本单改为**本版不支持合并线**（工单 `fig2.merge_groups` 在场即 BLOCK）。理由：APU/BTW 两案无实例，`figures_from_facts check` 末点对账只认单实体，支持合并线要同时改 check 与 fig2-series，超出本批。留 7.2。
7. 现有测试 `test_a4_gate.py:608/:638` 断言 build_html 输出含 `封口后被改动`；`test_audit_release_gate.py`、`test_distribution_gate.py`、`test_round4_a5_seal.py`、W1 新增的 `test_reopen_cycle.py`/`test_a4_limits_extract.py`——改完全部必须仍 PASS。全套 `python3 scripts/tests/run_all.py` 约 11 分钟，`nohup … > /tmp/run_all_w2.log 2>&1 &` 落盘后读回真实结果，不得凭部分输出宣称 PASS。

## §A `audit_release_gate.py`：新增 profile `stage2-dryrun`

锚点（764b60c）：`:44-52 NEW_ANALYSIS_REQUIRED`、`:54-57 REQUIRED_BY_PROFILE`、`:1558 if profile == "independent-audit" and report is None:`、`:1606 if profile == "new-analysis" and "distribution_scan.json" in data:`、`:1616 if profile == "new-analysis":`（大块到 `:1656`：`:1618` figure2 收据段、`:1620-1636` series binding 段、`:1637-1641` fig1 legend 段含 elif、`:1642-1656` A5 seal 重验段）、`:1671 --profile choices=sorted(REQUIRED_BY_PROFILE)`（自动带新 profile）。

改法：
1. `REQUIRED_BY_PROFILE` 加 `"stage2-dryrun": SHARED_REQUIRED + ("distribution_scan.json", "distribution_rounds.json"),`。豁免 `a5_report_seal.json`、`fig1_legend_receipt.json`、`figure2_check_receipt.json`。
2. `:1558` 改 `if profile in ("independent-audit", "stage2-dryrun") and report is None:`，文案 `f"{profile} 发布必须带 --report ..."`。
3. `:1606` 改 `profile in ("new-analysis", "stage2-dryrun")`。
4. `:1616` 改 `profile in ("new-analysis", "stage2-dryrun")`；块内三段各加 `if profile == "new-analysis":` 围栏：figure2 收据段、fig1 legend 段（含 elif 分支整体）、A5 seal 重验段（整段，含"缺 --report 即 fail-closed"那句）。series binding 段对两种 profile 都跑。
5. 不改 `run()`（`:1543`，保留深验缓存）；closeout 调 `audit_release_gate.run(case_dir, report, profile="stage2-dryrun")`。

**行为边界（写进 closeout 的 detail 文案，勿夸大）**：①`check_formal_case_chain`（`:132-147/:251-284`）对**在场**的 A5 仍会读并核 chain，缺席才跳过——dryrun 是"允许 A5 缺席"不是"忽略 A5"；②`_run` 只装载 profile required 文件进 `data`（`:1563-1571`），新 profile 不含 `claim_registry.json`，故 `check_claims` 不执行、`claim_types` 为空、historical-chart 检查跳过，即使磁盘有该文件；③围住 A5 段后，dryrun 下 `report` 参数**只剩非 None 检查**，报告内容与 sha 校验由 closeout 的 #2/#5/#6/#7/#10/#11 承担。

红证据：改前 `audit_release_gate.py <案> --report 报告.md --profile stage2-dryrun` 被 argparse choices 拒。绿：夹具案返回 PASS。

## §B `figures_from_facts.py`：拆纯校验函数＋新增 `fig2-series` 子命令

锚点：`:256 _write_check_receipt`；`:279 mode_check`（`:284-287` 容差政策 exit 2；`:288-291` 载入与非 list 抛 `SystemExit`；`:292-318` 校验主体；`:319-330` 打印与写收据）；`:333 main`；`:353 p3 = sub.add_parser("check")`；`:361 set_defaults(fn=mode_check)`。现有子命令只有 fig1/flow/check（`:336/:348/:353`），**没有** fig2 绘图子命令，图 2 由 −3 现场调 `standard_charts.plot_whale_vs_price`（`:276`，只读 label/ts/pct，`ts` 直接喂 matplotlib，不做日期转换；APU `stage3/assemble.py:100` 自行转 `datetime`）。

改法：
1. 抽纯函数 `fig2_check_errors(facts_path: Path, series_path: Path, tol_pp: float) -> tuple[list[str], int]`：返回 `(errs, okc)`；**不写收据、不打印、不抛 SystemExit**——series 非 list 时返回 `(["--series 应为图 2 whale_series JSON（list of lines）"], 0)`；文件不存在/JSON 非法抛 `ValueError`（调用方捕获）。`mode_check` 改为：容差政策（`:284-287` 原样）→ 调纯函数 → 若 errs 且首条是"应为 list"文案则保持原 `raise SystemExit("FAIL: ...")` 行为（CLI 退出码逐字不变）→ 其余打印/写收据（`:319-330` 原逻辑）。`test_a4_gate.py:507-512` 靠它产收据，行为不变。
2. 新子命令 `fig2-series`：`--entity-series <案内 entity_series.json> --keys TE-01,TE-02 --labels-from facts.json --out whale_series.json`。输入格式 `{dates:[YYYY-MM-DD…], <key>:[pct…]}`（APU 0914 与 BTW `data/replay/entity_series.json` 同款）。输出裸数组 `[{entity_id, label, ts, pct}]`：`label = facts.entities[key].label`（key 不在 entities、series 缺 key、`len(pct)!=len(dates)` → exit 1）；`ts` 保留 `YYYY-MM-DD` 字符串；`pct` 原值。实现为纯函数 `build_fig2_series(entity_series_obj, facts_obj, keys) -> list` ＋ `dumps_fig2_series(lines) -> bytes`（`json.dumps(ensure_ascii=False, sort_keys=True, separators=(",",":"))`，确定性），closeout 用它重放。
   - 同时写 `<out 同目录>/whale_series.provenance.json`：`{schema:"fig2-series-provenance/v1", entity_series:{path,sha256}, facts:{path,sha256}, keys:[…], out:{path,sha256}}`，path 为案根相对路径，无时间戳。写法 tmp+fsync+os.replace（同 `:248-253`）。`--keys` 有重复 → exit 1。`--out` 不是案根 `whale_series.json` 时照常生成，但 closeout #9 只认案根那份（见 E1-9），`--help` 写明。
   - **日期消费**：输出 `ts` 是字符串；`plot_whale_vs_price` 不转日期，−3 消费前须转 `datetime`（APU `assemble.py:100` 现状）。本单不改 `standard_charts.py`；在 `fig2-series` 的 `--help` 文案写一句"ts 为 ISO 日期串，绘图前转 datetime"。W3 手册 §3b.4 那一行据此写。
3. **合并线本版不支持**（§0 第 6 条范围调整）：`fig2-series` 不提供 merge 参数；工单 `fig2.merge_groups` 在场即 BLOCK（见 E3）。

红证据：改前 `fig2-series` 被 argparse 拒。绿：APU 副本 `--keys TE-01,TE-02,TE-04` 产 3 线＋旁车，`check` 对它 PASS。

## §C `a4_gate.py`：两个只读函数＋一个只读子命令

锚点：`main`/分派字典按锚文本 `sub.add_parser("finalize"` 与 `}[a.subcmd](a)` 定位（W1 已加 `limits-extract`，在同一字典加 `downstream-check`）。`safe_case_file` 在 `scripts/lib/case_paths.py:9`；`validate_revision_chain` 在本文件 `:87`。

C1 `seal_integrity_errors(case_dir: Path, seal: dict) -> tuple[list[str], set[str]]`：把 `build_html.py:340-391` 的非图片检查逐条搬来，**同一次遍历**产出 `errors` 与 `sealed_paths`（后者＝`sealed_files`＋`registry`＋`verdicts` 的相对路径集合，即原 `_sealed_paths` 语义，`:325` 定义）。**文案逐字保留**，但去掉完整前缀 `"[WARN] G9 "`，由调用方统一加：
- schema/verdict/claims 缺失（`:340-343`）；`validate_revision_chain`（`:345-347`）；
- `sealed_files`＋`registry`＋`verdicts` 逐条：路径合法（`checked()` `:354-364`：非绝对、无 `..`、拒 symlink、resolve 后在案内、是文件）、重复路径拒、实物 sha 一致（`:366-379`，"封口后被改动: {rel}"、"封口条目非法: {e}"）；
- 必封资产 required 集合（`:380-389`，independent-audit 加 claim_registry、new-analysis 加 `distribution_claim_source.path`）；`claim_files ⊆ sealed`（`:390-391`）。
- **不搬** workflow_type↔mode（`:348-351`）与 charts_dir/图片段（`:393-427`）。

C2 `build_html.py:340-391` 改为 `_g9_errs, _sealed_paths = a4_gate.seal_integrity_errors(_case, _seal); warns.extend("[WARN] G9 " + e for e in _g9_errs)`；`:348-351`、`:393-427` 原样保留，且 `_sealed_paths` 继续供 `:393-427` 图片段与 `:431-442` 监控 JSON 封口判断使用。保持"schema 无效时后续段不跑"的控制关系（若原代码用 `elif`/提前 return 组织，改后等价）。验收：`test_a4_gate.py:608/:638` 断言仍过、G9 正例仍 exit 0、监控 JSON 正例（若有）仍过。

C3 `downstream_stale(case_dir: Path) -> list[dict]`，每项 `{item, expected, actual, status: stale|ok|absent, fix_order}`，只读：
- `adversarial_review.json` 顶层 `claim_registry{path,sha256}`（runner `:673` 写入）vs `sha256(a4_claims.json)`；
- `shared_release_receipt.json` 的 `inputs["adversarial_review.json"].sha256`（`shared_release_receipt.py:2122`）vs 实物；
- `distribution_rounds.json` terminal 行 `a4_seal_sha` vs `sha256(a4_seal.json)`；
- terminal 行 `final_scan_path` 的 `input_binding.entity_freeze_revision` vs `len(entity_freeze.json["revisions"])+1`；
- `dormant_warehouse_audit.json` 的 `universe_ref{path,sha256}` vs wave_scan 实物（`audit_release_gate.py:989-998` 同款）。
文件不在场标 `absent`。`fix_order` 固定串：freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5。

C4 子命令 `downstream-check --case-dir [--json-out]`：打印表；有 stale exit 3，无 exit 0。

红证据：夹具案（§F）构造 `adversarial_review.json` 后改 `a4_claims.json` 的 `registered_at_utc` → `downstream-check` exit 3 且 item 含 `adversarial_review`。

## §D `build_html.py`：仅 C2 那一处替换，其余不动。

## §E 新脚本 `scripts/report/stage2_closeout.py`

命令行：`stage2_closeout.py [check] --case-dir <案根> --report 报告.md [--workorder a5_assembly_workorder.json] [--receipt-only] [--json-out]`；`fill-workorder --case-dir --report [--workorder]`；`amend --case-dir --report`。exit：0 PASS / 2 BLOCK / 1 脚本错。`reseal` 由 W3 加，本单不留占位。所有路径经 `case_paths.safe_case_file`。closeout **只服务 new-analysis**（a4_seal `workflow_type` 非 new-analysis → 整体 BLOCK 一条后仍跑完其余项）。

### E1 `check` 子检查（顺序固定；每项 `{name,status:PASS|BLOCK|NOTE|ABSENT,detail}`，全部跑完再判，任何子项抛异常都记 BLOCK 不中断）

**放行语义（全文统一）**：`verdict = BLOCK`（任一子项 BLOCK）否则 `PASS`；`NOTE` 与 `ABSENT` **永不拦**，只进 detail。下文凡写"PASS"指 verdict，不要求十一项字面全 PASS。

| # | name | 做法 | BLOCK 条件 |
|---|---|---|---|
| 1 | release_gate_dryrun | `audit_release_gate.run(case, report, profile="stage2-dryrun")`，errors 逐条进 detail | errors 非空 |
| 2 | a4_seal_integrity | `a4_gate.seal_integrity_errors(case, seal)[0]` | 非空 |
| 3 | downstream_stale | `a4_gate.downstream_stale(case)`；detail 附 fix_order | 任一 `stale` |
| 4 | identity_gate | `entity_identity_gate.validate_gate(case/"identity_gate.json", case/"analysis-state.json", require_resolved=True)`（`:162`，第二位置参数即 state_path） | 返回错误非空 |
| 5 | a5_provenance_flip | `a5_report_seal.provenance_flip_bundle(case, report_text, a4obj)` 返回字典；`status ∈ {DISCLOSED, NO_LEDGER, NO_FLIPS}` → PASS（detail 记 status）；`NOT_APPLICABLE` → BLOCK；抛 `ValueError`/文件或 JSON 异常 → BLOCK 带异常文案 | 如左 |
| 6 | a5_distribution | `a5_report_seal.distribution_bundle(case, report_path, a4obj)`；`status ∈ {NORMAL, LOW_SAMPLE, EXPLAINED, WAIVED}` → PASS；`NOT_APPLICABLE` → BLOCK；异常 → BLOCK | 如左 |
| 7 | caption_same_source | E2 | 如 E2 |
| 8 | dual_basis | facts 顶层 `dual_basis:{lower:<metric id>,upper:<metric id>}` 在场：两 id 都在 `facts.metrics` 且报告源文本同时含 `{{m:<lower>}}` 与 `{{m:<upper>}}`；**不在场 → NOTE"未声明双口径"**（APU/BTW 均无该键，不得 BLOCK） | 仅在场且不满足 |
| 9 | fig2_series | 见 E1-9 | 如下 |
| 10 | workorder | E3 | 如 E3 |
| 11 | facts_gate | `rendered, errors, notes = facts_gate.load_and_check(facts_path, state_path, md_text)`（`:250-256`，传**文件路径**）；**只用 `errors`**，`notes` 进 detail 不判 | errors 非空 |

**E1-9 fig2_series 细则**：固定读案根 `whale_series.json` 与 `whale_series.provenance.json`（不解析工单 `fig2.whale_series`/`whale_series_out` 字段的文字，APU 实况该字段是带说明的串）。逐项，任一不符 BLOCK：
①两文件都不在场 → BLOCK"未生成 whale_series：运行 `figures_from_facts.py fig2-series` 生成（历史案迁移办法同此）"。
②旁车 schema 须 `fig2-series-provenance/v1`；**`out.path` 必须逐字等于 `whale_series.json`**（案根；绑定别的输出即 BLOCK"旁车 out 非案根 whale_series.json"）；`entity_series/facts/out` 三项 path 案内、sha 与实物一致；`facts.path` 必须等于工单 `bindings.facts.path`（防旁车绑另一份 facts）。
③**与工单逐条等值**：工单 `fig2.lines[]` 的 `series_source.path` 全部相同且 == 旁车 `entity_series.path`，`series_source.sha256` == 旁车 `entity_series.sha256`；`lines[].series_source.key` 列表（无重复）与旁车 `keys`（无重复）集合相等；`lines[].entity_id` 无重复。任一不等 → BLOCK 文案指明是 path/sha/keys/重复。
④**重放核验（字节级）**：用旁车 `entity_series`、`facts`、`keys` 调 `build_fig2_series`＋`dumps_fig2_series`，得到的**字节**须与案根 `whale_series.json` 实物字节完全相等（不只比 sha，且 `out.sha256` 也须等于实物 sha）。
⑤`figures_from_facts.fig2_check_errors(facts, whale_series, DEFAULT_TOL_PP)` 无错。
⑥whale_series 的 `entity_id` 集合 == 工单 `lines[].entity_id` 集合（工单 lines 非空而序列空即 BLOCK）；每条 `lines[i].display_label` == `facts.entities[entity_id].label` == whale_series 同 entity_id 行的 `label`（三者逐字相等，否则 BLOCK 文案 `fig2.lines[i].display_label`）。
⑦`time_range` **本版不消费**（两案写法不一，APU 只有起点）：detail 记 NOTE"time_range 未核"。
**边界（写进 detail 与 `--help`，勿夸大）**：以上只闭合"案根 whale_series.json ↔ 工单选材 ↔ entity_series 实物"，**不能证明 −3 渲染的 PNG 用的是这份序列**——`plot_whale_vs_price` 接受调用方任意数组（`standard_charts.py:289`），该边界既有，由 −3 的 `figure2_check_receipt`（对 whale_series 实物 sha）承担，本单不改绘图库。

verdict：任一 BLOCK → BLOCK；否则 PASS。成功文案固定："PASS: −2 可进入装配；待 −3 执行项：fig1/fig2/fig3/流转图渲染、fig1_legend_receipt、figure2_check_receipt、a5_report_seal、build_html"（即 `pending_for_stage3`）。

### E2 图注同源（caption_same_source）

- 定位：报告源文本中引用 `charts/final/holder_distribution_current.png` 的图片行（`a5_report_seal.IMG_RE`，须唯一，否则 BLOCK）；其后第一段非空文本为图注。
- 数据源：`distribution_rounds.json` terminal 行 `final_scan_path` 的 scan：`bucket_coverage{private_main,private_dust,public_facility,unresolved_contract,burn_sentinel}{raw,net_supply_pct}`；正常样本 `concentration.top_k_net_pct{"1","3","5","10"}` 与 `concentration.hhi`（`:556`）；low_sample 时 `small_sample_mode.top_k/hhi`（`:594-604`，该分支无 `concentration`）。
- 渲染规则（按 APU 0914 报告.md:49 与 BTW 报告.md:54 归纳，**比较原始 pct，不用 round 后比较**）：每桶生成"可接受串集合"：`raw=="0"` → `{"0", "0.0%", "0.00%"}`；`pct >= 0.01` → `{f"{pct:.2f}%"}`；`0.00005 <= pct < 0.01` → `{f"{pct:.4f}%"}`（APU 私人尘埃 `0.0005%`、BTW 未识别合约 `0.0056%`、BTW 私人尘埃 `0.0001%`）；`0 < pct < 0.00005` → `{f"{pct:.4f}%", "0.0%", "0.00%", "0"}`（BTW 销毁哨兵 `0.0%`）。
- 判定：五桶各自至少一个可接受串出现在图注段 → 否则 BLOCK，文案 `图注与终态 scan 不同源: <桶名> 期望 <串集合> 未出现`。`raw=="0"`/极小值桶退化为存在性检查，detail 如实标注。
- top-k（`.2f%`×4）与 HHI（`.4f`）：图注段内**若出现** `HHI` 或 `top` 字样则逐串核对，不符 BLOCK；**未出现 → NOTE**"图注未披露集中度数字"（存量 BTW 图注兼容；本轮不加必填项）。
- 只比数字串不比桶名文案。**如实边界**：本检查是"格式兼容＋存在性"，不是严格同源证明——`0`/`0.0%` 可命中日期等无关数字，某桶的串也可能出现在别桶旁边；detail 固定加一句"存在性检查，非逐桶配对"。收紧留后续。

### E3 工单校验（workorder）

字段依据 split-run §3b.2（`:152-166`）与 APU 0914 实况（顶层键 note/meta/bindings/report_image_refs/fig1/fig2/fig3/flow/path_fence/stage2_selfcheck/amendments）：
1. 必备顶层键：note/meta/bindings/report_image_refs/fig1/fig2/fig3/flow/amendments；`stage2_selfcheck` 可选。
2. 机械字段重算等值（**按路径值找，不按键名**，APU 与 BTW 的 bindings 键名不同：APU `final_distribution_scan/final_distribution_png`，BTW `final_scan/terminal_distribution_chart`）：`bindings.report_md.sha256`（amendments 为空时＝报告实物 sha；非空时＝首条 `before_sha256`）；`bindings.a4_seal_sha256 == sha256(a4_seal.json)`；`bindings.entity_freeze_revision == len(entity_freeze.revisions)+1`（APU 3+1=4）；`bindings.facts.path/state.path/rounds.path` 必须分别是 `facts.json`/`analysis-state.json`/`distribution_rounds.json`；`bindings` 下**必须存在**一个 `{path,sha256}` 对象其 `path` == rounds terminal 行 `final_scan_path`，另一个其 `path` == terminal 行 `final_chart_path`（键名不限）；`bindings.distribution_terminal{status,round_n}` 与 rounds terminal 一致；`report_image_refs` 与 `IMG_RE` 重取的有序清单（保留重复）一致。
2b. **通用实物重验**：递归遍历工单全文（`stage2_selfcheck` 除外），凡对象同时含 `path`（str）与 `sha256` 键 → path 过围栏（第 6 条）且 `sha256(实物) == sha256`；`sha256` 为 null → BLOCK，**唯一例外**：`path` 指向工单自身（APU `fig3.events_input` 自引用）→ NOTE 不核。这一条覆盖 `flow.*.spec.sha256`、`fig2.lines[].series_source.sha256`、`fig3.price/volume/price_input/volume_input`、`bindings.price_source` 等，**不逐键枚举**。
2c. **各图最小结构**（缺一 BLOCK）：`fig1`/`fig2`/`fig3` 均为对象且含 `out`（str）；`fig2.lines` 非空 list、`fig2.required_entity_ids` list；`fig3.events` 非空 list 且每项含 `date`（`YYYY-MM-DD`）与 `label`；`flow` 含 `eligible_entity_ids` list 且 `charts` 或 `items` 至少一键（第 5 条）。不核更细的类型（两案写法差异大，本轮不定死）。
3. **amendments 链完整性**：每条必备字段 `before_sha256/after_sha256/trigger/exact_change{before,after}/approved_by`（APU 实况字段）；首条 `before == bindings.report_md.sha256`；逐条 `amendments[i].after_sha256 == amendments[i+1].before_sha256`；末条 `after == 报告实物 sha`。任一断链 BLOCK。内容冻结与"实际改动＝获准改动"由 E5/E6 承担。
4. fig2：`lines[].entity_id ∈ facts.entities` 键（写展示名 → `WORKORDER BLOCK: fig2.lines[i].entity_id: facts 键 != 展示名`）；必画下限＝facts.entities 中 `label.strip()` 以 `项目方`/`大庄`/`小庄`/`离场庄` 开头的实体（APU {TE-01,TE-02,TE-04}；BTW {e_proj}）；label 缺失/空串 → BLOCK"实体 <id> 无标签，无法判定必画"；`required_entity_ids ⊇ 下限`，`lines` 的 entity_id 集合 ⊇ `required_entity_ids`（允许额外线，BTW 另两条合法）；每条 `series_source{path,key,sha256}`：案内、sha 一致、key 在文件里；`merge_groups` 在场 → BLOCK"本版不支持合并线（范围调整，见 §0 第 6 条）"。
5. flow：分母两种：总供应 `facts_gate.Facts.total_raw`；流通 `facts.token.circulating_supply_raw`（可选键，缺失则 detail 记 NOTE"未声明流通量，门槛仅按总供应判"，不 BLOCK）。下限＝label 以 `项目方`/`大庄` 开头且 `current_raw/总供应 ≥ 20%` **或** `current_raw/流通 ≥ 20%`（report-template.md:176-178）；`eligible_entity_ids ⊇ 下限`；逐张清单兼容 `flow.charts`（APU）与 `flow.items`（BTW），两键都无 → BLOCK；**图中实体集合 == eligible 集合**（split-run.md:163 双向相等；`eligible=[e_proj], items=[]` 即 BLOCK）；eligible 允许多于下限（承载关键结论的额外图）。APU 实况：下限空、eligible 空、charts 空 → PASS（NOTE 未声明流通量）；BTW 实况：下限 {e_proj}（总供应 20.81%）、eligible {e_proj}、items {e_proj} → PASS（同 NOTE）。
6. 路径围栏：所有 `path` 值须案内普通文件（拒 symlink/绝对/`..`）；各 `out` 以 `charts/final/` 开头且 `.png`。
7. 失败文案统一 `WORKORDER BLOCK: <字段路径>: <期望> != <实际>`。

### E4 `fill-workorder`

只填机械字段：`bindings.a4_seal_sha256`、`bindings.entity_freeze_revision`、`bindings.facts/state/rounds/final_distribution_png/final_distribution_scan{path,sha256}`、`bindings.distribution_terminal`、`report_image_refs`、`meta.skill_version`（读 VERSION）、`meta.skill_commit`（`git rev-parse HEAD`，失败 null）、`meta.produced_at_utc`。**`bindings.report_md` 已存在则绝不覆盖**；不存在才写当前实物 sha。选材字段缺失留 `null` 并 stdout 列"待 −2 亲笔"。工单不存在时从最小骨架建。写法 tmp+os.replace。

### E5 收据 `stage2_closeout_receipt.json`

schema `stage2-closeout/v1`：`{schema, verdict, report_md{path,sha256}, workorder{path, frozen_sha256, report_image_refs_sha256, amendments_sha256, amendments_count}, facts{sha256}, state{sha256}, entity_freeze_revision, a4_seal_sha256, rounds{sha256, terminal_round_n, status}, whale_series{path,sha256}|null, skill_commit, checks[], pending_for_stage3[], amendment_chain[]}`。
- 记 `canon(x) = json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",",":")).encode()` 的 sha256。`workorder.frozen_sha256` ＝ 工单剔除 `stage2_selfcheck`、`amendments`、`report_image_refs` 三键后的 canon sha（−3 唯一获准改动的三处不入冻结哈希）；`report_image_refs_sha256` ＝ canon(`report_image_refs`)；**`amendments_sha256` ＝ canon(`amendments` 完整数组)**（冻结旧条目全部内容，不只计数）；`amendments_count` 单独记。无时间戳。BLOCK 也写收据。不进 `REQUIRED_BY_PROFILE`。
- `--receipt-only`（−3 前置自检）：只复验——report sha（有 amendment_chain 按最后一条 after_sha256）、workorder frozen_sha256＋report_image_refs_sha256＋**amendments_sha256**＋amendments_count、facts/state/a4_seal/rounds sha、freeze revision、**whale_series sha、skill_commit**（当前 `git rev-parse HEAD` 须等于收据值，否则文案"skill 已换版，重跑 stage2_closeout"）、verdict==PASS。任一不符 exit 2，文案"closeout 收据与现场漂移: <项>，退回 −2 重跑 stage2_closeout"。

### E6 `amend`

−3 每写一条 `amendments[]` 后运行：`amend --case-dir --report [--previous <修正前报告副本>]`。

**范围**：amend 只承接 split-run §3b.4 修错分类 ②（报告.md 逐字模板句/图路径字符串的最小机械修正）。**工单任何字段都不可经 amend 修改**（含路径/落位）：`frozen_sha256` 变即 BLOCK 文案"工单字段已改（frozen_sha256 漂移）：工单不可在 −3 修改，退回 −2 重跑 stage2_closeout"；分类 ① 的缺件/落位红灯属产物侧，不改报告也不改工单，无需 amend；分类 ③ 一律退回 −2。

**前置（任一不过 exit 2 不写）**：
1. 收据在场且 verdict=PASS；当前 `frozen_sha256` == 收据值；`report_image_refs_sha256` 允许变（图路径修正）。
2. **旧条目未被改写**：`canon(amendments[:-1])` 的 sha == 收据 `amendments_sha256`；`len(amendments) == 收据 amendments_count + 1`。
3. 新条 `amendments[-1]` 必备字段齐（E3.3）；`before_sha256` == 收据当前报告 sha（首次对 `report_md.sha256`，之后对 `amendment_chain[-1].after_sha256`）；`after_sha256` == 报告实物 sha。
4. **实际改动＝获准改动（重放）**：取 `exact_change{before,after}`。默认**反向重放**：当前报告文本中 `after` 必须恰出现 1 次，替换为 `before` 得到"前稿"，其 sha 须 == `before_sha256`；`after` 为空串或出现次数≠1 时必须传 `--previous`（其 sha 须 == `before_sha256`），改为**正向重放**：前稿中 `before` 恰出现 1 次，替换为 `after` 后 sha 须 == 报告实物 sha。两向都不成立 → BLOCK"实际改动与 exact_change 不符：正文混入未获准改动"。`approved_by`/`approval_text` 只要求非空，不作证明。
通过后**全量重跑 E1 十一项**（不做子集选择），**verdict PASS（无 BLOCK，NOTE 不拦）** 才追加 `amendment_chain[] {before_sha256, after_sha256, verdict}`，更新收据 `report_md.sha256`（工单 `bindings.report_md` 原稿锚不动）、`report_image_refs_sha256`、`amendments_sha256`（含新条）、`amendments_count`；否则 exit 2 不写。

## §F 测试 `scripts/tests/test_stage2_closeout.py`（登记进 `run_all.py` SUITE 末尾）

**夹具**（`build_closeout_case(root) -> Path`）：
1. `test_audit_release_gate.build_case` 得基础案 → `shutil.copytree`＋`test_a4_gate.rebind_case_inputs` → 删净室件（`test_a4_gate.py:493-495` 六件）。
2. **补 facts/state/identity 准备**（`build_case` 不产这些，原在 `test_a4_gate.main:370-389`）：从该处复制写法，但实体 label 改为 `"大庄#1"`，**facts `token.total_supply_raw`、实体 `current_raw`、`peak_raw` 三者统一为 `"100"`**（`augment_gate` 只生成一行余额 100，`add_distribution_initial` 从 balances 取总量也是 100——codex 内存实跑核实；facts_gate 不对账 balances 数额，所以 300/1000 不会被拒但与扫描分母失真，故不用）；持仓 100% ≥ 20% 供 flow 正例；state `whale_groups[0].label` 同步；identity `state_sha256` 按 `add_camp_series` `:272-275` 的重绑法算。**裁决文件只给 `[{"id":"C1","verdict":"CONFIRMED"}]`**——`build_case` 只登记 C1，照抄 `test_a4_gate` 的 `v_ok.json`（含 C2）finalize 必拒（`a4_gate.py:369`）。若 facts_gate 报错，按报错调整夹具数值，**不改闸**。
3. `add_distribution_initial` → `add_camp_series` → `a4_gate finalize --workflow-type new-analysis --seal-files findings.md,analysis-state.json --verdicts-file v_ok.json` → `finish_distribution_normal`。
4. 写 `entity_series.json {dates:[…], "e1":[…最后一点=100.0]}` → `fig2-series --keys e1 --out whale_series.json` 产案根 whale_series＋旁车；写最小 `flow_e1.json` spec（可复用 `test_a4_gate` 现有 flow 夹具写法，若无则最小合法 spec）；**先写完报告正文**（第 5 步）再首次 `fill-workorder`（fill 不覆盖已存在的 `bindings.report_md`，先 fill 后改正文会锁错锚）；fill 生成骨架后补 fig2（lines=[{entity_id:e1, display_label:"大庄#1", series_source{path:"entity_series.json", key:"e1", sha256}}]，required=[e1]）、flow（eligible=[e1]，charts=[{entity_id:e1, spec{path,sha256}, out:"charts/final/flow_e1.png"}]）、fig1/fig3 最小合法值（E3.2c）。
5. 报告：在终态图引用行后追加按 E2 规则渲染的图注段（含 HHI）。**不构造、不覆盖 `adversarial_review.json`**：基础夹具已产真实文件（v4 schema，且 `shared_release_receipt` 已绑其 sha，`audit_release_gate.py:1212`），用例 3/13 直接改 `a4_claims.json` 的 `registered_at_utc` 即得真实 registry 漂移。
环境说明：导入 `test_a4_gate` 会改 `sys.path` 并包装 `gate.run`；`MPLCONFIGDIR` 在其 `main()` 内设置，导入不执行——本测试自行 `os.environ.setdefault("MPLCONFIGDIR", tmp)`。

**用例**（名称固定；每个变异用例在独立副本上做，不互相污染；负例先证正例可用再断言业务错误文案）：
1. `dryrun_profile_exempts_stage3_artifacts`：无三件 −3 产物，`check` PASS，收据 verdict=PASS，`pending_for_stage3` 含 a5_report_seal。
2. `only_findings_changed_is_rejected`：改 `findings.md` 一字 → BLOCK 且 #2 detail 含 `封口后被改动`。
3. `stale_registry_sha_detected`：改 `a4_claims.json` 的 `registered_at_utc` → #3 BLOCK，item 含 `adversarial_review`（真实 registry 漂移，不用改 seal 替代）。
3b. `stale_a4_seal_sha_detected`：改 `a4_seal.json` 一字节 → #3 item 含 `rounds`（单独用例）。
4. `old_receipt_new_report_rejected`：PASS 后改报告一字 → `--receipt-only` exit 2。
4b. `receipt_only_checks_whale_series_and_commit`：改 whale_series 一位 → `--receipt-only` exit 2 文案含 `whale_series`。
5. `fig2_entity_id_must_be_facts_key`：`fig2.lines[0].entity_id` 写展示名 → BLOCK 文案含 `fig2.lines[0].entity_id`。
6. `fig2_required_from_label`：required 由 label 前缀得出且非空；清空 lines → BLOCK；`merge_groups` 在场 → BLOCK。
7. `flow_items_compat_and_extra_allowed`：`flow.items` 形式通过；eligible 与图各多一个未达门槛实体仍 PASS；eligible 含 e1 但图清单为空 → BLOCK；facts 无 `circulating_supply_raw` → detail 含 NOTE。
8. `caption_mismatch_rejected`：改一个桶百分比 → BLOCK。
8b. `caption_btw_style_tiny_values_accepted`：构造 scan 副本（或 facts 侧夹具）使某桶 pct=0.0056、某桶 2e-6，图注写 `0.0056%` 与 `0.0%` → #7 PASS；图注去掉 HHI 与 top 字样 → #7 NOTE 不 BLOCK。
9. `amend_chain_updates_receipt`：改报告一处措辞并追加合法 amendment（`exact_change` 与实际改动一致）→ `amend` exit 0，`amendment_chain` 长 1，`--receipt-only` PASS；再改工单 `fig2.required_entity_ids` 后 `amend` → exit 2 文案含 `frozen_sha256`。
9b. `amend_replay_mismatch_rejected`：amendment 的 `exact_change` 写 A→B，实际正文除 A→B 外另改一处 → `amend` exit 2 文案含 `未获准改动`；`after` 为空串且未传 `--previous` → exit 2；传正确 `--previous` 的删除型修正 → exit 0。
9c. `old_amendment_rewritten_rejected`：用例 9 通过后改 `amendments[0].approved_by` → `--receipt-only` exit 2 文案含 `amendments_sha256`；再追加合法第二条后 `amend` → exit 2（旧前缀已变）。
9d. `amend_passes_with_note`：夹具 facts 无 `dual_basis`（#8 NOTE）时 `amend` 仍 exit 0（NOTE 不拦）。
10. `fill_never_overwrites_report_anchor`：工单已有旧 `bindings.report_md` → `fill-workorder` 后不变。
11. `low_sample_terminal_not_blocked`：夹具 owner 少走 low_sample 时 #6 PASS、#7 用 `small_sample_mode`。
11b. `waived_terminal_not_blocked`：按 `holder_distribution_scan` waiver 路径（`:1125-1134`，`validate_waiver` 必备字段）构造合法 WAIVED 终态＋报告含"未解释" → #6 PASS。若夹具无法构造 ABNORMAL，允许用 `test_distribution_gate.py` 现有 WAIVED 夹具（若有）；两者都不可行则在 done 写明并留待 W3。
12. `fig2_series_replay_binds_workorder`：`fig2-series` 产物 → #9 PASS；手改 whale_series 一位 → #9 BLOCK（重放字节不符）；工单 lines 加一个序列里没有的实体 → #9 BLOCK。
12b. `fig2_sidecar_substitution_rejected`：另生成 `--out whale_series_alt.json`，把旁车整体换成指向 alt 的那份（自身一致）→ #9 BLOCK 文案含 `旁车 out`；旁车 `entity_series.path` 改指向另一份内容相同但路径不同的副本 → #9 BLOCK（与工单 `series_source.path` 不等）。
12c. `fig2_duplicate_and_label_rejected`：工单 lines 重复 entity_id → BLOCK；`display_label` 与 facts label 不等 → BLOCK 文案含 `display_label`。
13. `downstream_check_cli_exit3`：用例 3 状态下 `a4_gate.py downstream-check` exit 3。
14. `amendments_chain_gap_rejected`：工单两条 amendments，第一条 after ≠ 第二条 before → #10 BLOCK。

## §7 验收（Fable 做，写这里供施工方自检）

- `run_all.py` 全 PASS（含新用例与 `invariant_scan.py`）；`test_a4_gate.py` 单跑 PASS（G9 文案不变）。
- **APU 0914 完整 closeout 挪到 W3 验收**：W1 改扫描器后 APU 两份 scan 绑定的扫描器整文件 SHA（`holder_distribution_scan.py:663/:1073`，`semantic_payload` 保留）必失配，且 APU `a4_seal.sealed_files` 封了 `distribution_scan.json`——重跑 initial scan 会改封口件 sha，须先 `reopen-cycle` 解除旧 terminal、再 finalize、再重跑 final scan，这正是 W3 `reseal --from a4` 的全链（`a4_gate.py:285` 见 terminal 即拒，顺序不可反）。另外 APU `accounting_mode.json` 的 observation bundle 用原案绝对路径，普通复制到新案根会被案根包含检查拒（`shared_release_receipt.py:367/:1755`），副本迁移办法也归 W3 定义。**因此 W2 阶段对 APU 只做纯规则验收（与 BTW 同法，不跑组合 `check`）**：在临时目录 import E2/E3 判定函数，喂 APU 的 `facts.json`/`analysis-state.json`/工单/报告.md/终态 scan：fig2 required 得 {TE-01,TE-02,TE-04} 且 lines ⊇ required、display_label 与 facts 同源；flow 下限空/eligible 空/charts 空 → PASS 带 NOTE；图注五桶＋top-k＋HHI 全部命中（codex 逐桶重算：76.69%/0.0005%/23.31%/0/24.51%，top-k 3.76/8.89/12.17/17.09，HHI 0.0049）。不宣称 "#2–#11 PASS"。
- BTW 纯规则：同法。required == {e_proj}，`flow.items` 兼容，图中实体==eligible；图注五桶命中（24.02%/0.0001%/75.97%/0.0056%/0.0%），无 HHI/top → NOTE 不 BLOCK；无流通量 → NOTE。
- 原案回测（案卷副本上、只跑对应子检查函数）：MELANIA 图注不同源 → #7 BLOCK；COLLECT fig2 展示名 → #10 BLOCK；LIT identity resolution 空 → #4 BLOCK。
