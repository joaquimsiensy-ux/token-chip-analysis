# 工单 W1（v2）：共享覆盖地图「驳回继承」——refuted_slots 由已发布修复 census 填充；探针复用地图时经一次 SQD 重查即继承为 `INHERITED_REFUTED`；校验器 fail-closed 独立复核 —— 归属版本 9.2.0（版本登记在 W2；producer 登记另单）

> 出处：用户 2026-09-24 裁决第 1 条「驳回过的 slot 记进共享地图,后案只做一次便宜的 SQD 状态确认就继承」；2026-08-23 已裁决 E22「全普查＋驳回继承」但至今未落地（导出恒写 `"refuted_slots": []`）。
> v2 变更：吸收 codex 复核 r1（`review_W1_reply_r1.md`）13 条——必改 1–12 全采纳、建议 13 采纳。设计决定：①**残余风险明示**（重查只证「块头在、零 AdvanceNonce」，不证交易集合未变；用户裁决即接受此风险）；②**成员见证＝资产副本随 coverage 发布件落盘**，校验器跨机可核成员关系；③**时效随证据项走**（origin_generated_at 不因链式导出刷新）；④**slot→证据绑定**用与 `refuted_slots` 等长的索引数组 `refuted_origin`；⑤新状态 β 路径兼容（白名单加 `sqd_gap_repair.py` 一函数）；⑥修复来源绑定 helper 放校验器、探针只编排（避免探针新增 schema 消费面）；⑦生产行数上限改为报告指标。
> 调度方陈述（案卷不在本仓库，施工方不核）：PYTHIA 0919 案 α 修复 157,700 候选中 155,642 与 TROLL 0905 地图 `candidate_slots` 相同；census refuted 150,133 / confirmed_nonce_defect 7,566 / confirmed_other_defect 1；Helius 下载 366.7 GB。
> 事实（调度方本机亲核，基线 `cc6298b` 9.1.1；行号以该基线为准；锚整行 `grep -n -F -x` 恰 1 处）：
> ① `scripts/solana/sqd_coverage_probe.py:670` `_load_known_map`：校验三件套/TTL/身份/历史锚后，`:743` 重查集合＝`canary.slots ∪ candidate_slots ∪ refuted_slots`；`_recheck_known_slots(:573)` 按 `_contiguous_ranges(:557)` 切区间逐段 `recheck` 请求，`:625-628`、`:635-638` 把首轮与重试中**全部 verified 区间**的逐 slot 实测值收进 `actual`（不只 canary），`:644-647` 返回 `actual, mismatch|None, unverified[(start,end)…], stats`；任一 mismatch → 整图作废；非 canary 段 request-failed 重试仍失败 → `unverified`（`:747-748` 转为 `{from_slot,to_slot}` 对象数组）局部剔除；canary 所在段最终失败 → 整图回退。`:774-777` 把跨本案边界的成功 recheck 行 `counts_coverage=False`。`:778` 返回 `info, bytes(reused), overlap_from, overlap_to`；异常分支 `:780-784`：本轮 recheck 行 `counts_coverage=False`、`:783` 写 `fallback_reason`、`:784` 返回 `info, None, None, None`。`actual` 目前不出 `_load_known_map`。
> ② `run_probe`：`:1228` `if reused is not None:` 写复用 counts 并追加 `map-reuse` ledger 行；`:1313` `classified = classify_four_states(counts, args.from_slot, confirmation=…, blocks_bitmap=…)`；`:1333` 把 `_load_known_map` 的 `info` 原样落盘 `shared_map`。coverage_map 落盘 summary/candidate_slots/verdict，**不落盘 states**；`compute_probe_id(:84)` 哈希整份 coverage_map（含 producer.sha256），改 producer 后新产物 probe_id 自然变化。
> ③ `scripts/lib/solana_exact_validate.py:223` `classify_four_states(counts, from_slot, *, confirmation=None, blocks_bitmap=None)`；`:241-246` summary 固定 11 键；`:268` `elif code == 2:` 分支：时代校准通过 → `DEFECT_CANDIDATE` 入候选，否则 `ERA_UNCERTAIN` 入 unconfirmed。`:458` `validate_coverage` 用同函数重算，`:684-689` 要求 `summary`/`candidate_slots`/`verdict` 三者与 coverage_map 全等。`:711` `validate_shared_map`：`:863` `refuted_slots` 只做形态检查；`:877-880` 要求 `candidate_slots` 等于资产二进制重算候选。`_success_ranges(:413)` 是校验器自己的 ledger 成功区间实现（探针的 `_successful_coverage_range(:418)` 不得反向导入）。
> ④ `sqd_coverage_probe.py:805` `export_shared_map`：从源案 `data/sqd_coverage/CURRENT.json` 所指发布代导出三件套，`:858` `candidate_slots` 取 `validate_coverage()["recomputed"]["candidate_slots"]`（**有效候选**），`:859` 恒写 `"refuted_slots": [],`；无读取修复代的逻辑。
> ⑤ 修复侧 `scripts/solana/sqd_gap_repair.py:576` `validate_coverage_state_consistency(state, *, header_present, nonce_count, beta_candidate=False)`：非 β 且 state ∉ {DEFECT_CANDIDATE, MISSING_BLOCK} → raise「non-candidate coverage state entered alpha」；未知状态在 α/β 均 raise「SQD coverage state changed before repair」。`_plan(:607-608)` 候选＝`coverage.candidate_slots ∪ beta_slots`。census 行（`:1336-1338`）`state_in_map` **硬编码** `"DEFECT_CANDIDATE"`，真实分类在 `coverage_state`。修复代目录＝`sqd_repair_paths(case_root, mint)`（定义 `scripts/solana/spl_edge_core.py:240`，返回 parent/CURRENT.json/.lock），指针校验 `validate_repair_pointer(:1039)` 只核 envelope/mint/gid/bundle sha。**refuted-only 不产代不发指针**（`:1493`；`scan-schemas.md:953` 不变量）。
> ⑥ `classify_four_states` 生产直接调用 3 处：probe:1313、validator:676、validator:877；修复 `sqd_gap_repair.py:1369` 与深验 `validator:1574` 消费重算 `states` 并做状态语义检查（`_repair_state_matches(:1202)` 对未知状态返回 False）——新状态必须同时适配 α 拒绝、β 允许两条路径。
> ⑦ 仓库资产 `assets/sqd-solana-coverage-map/20260827.json`：`generated_at` 2026-08-25T03:17:11.217739+00:00，candidate_slots 153,667，refuted_slots 空。
> ⑧ `invariant_scan.py:1165-1172` 按脚本内 schema 字符串比较识别消费者；manifest（`invariant_manifest.json:627-631`）给探针只登记 shared-map schema，校验器已登记 repair-bundle/coverage-resolution/repair-pointer 等全部修复 schema。
> ⑨ `test_sqd_coverage_probe.py:743-760` 用显式 tests 列表，新增函数必须登记才会执行。夹具实测：同一 ERA 窗口内 62 个 code=3＋2 个 code=2 → 候选空、ERA_UNCERTAIN=2；9998 个 code=3＋2 个 code=2 → 两 slot 为候选。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `W1_done.md`：`git status --short`（须为空）、`git rev-parse --short HEAD`；`git merge-base --is-ancestor cc6298b HEAD` 须 exit 0；`git diff --quiet cc6298b HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets` 须 exit 0。任一不符**停工**。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、本工程目录以外的全部历史 `maintenance/` 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。本目录可读：`README.md`、`workorder_W*.md`、`review_W1_reply_*.md`、`fable_probes_20260924.md`。禁读纪律**同样适用于子进程与测试脚本**：`test_sqd_gap_repair.py`/`test_batch8_repair_scale.py` 依赖禁读 `.staging_b3`，施工者不得执行触及这些数据的用例（新增 β 用例须自包含数据）。
- 0.3 **白名单**（可写）：生产 `scripts/solana/sqd_coverage_probe.py`、`scripts/lib/solana_exact_validate.py`、`scripts/solana/sqd_gap_repair.py`（**仅** `validate_coverage_state_consistency` 一函数）；测试 `scripts/tests/test_sqd_coverage_probe.py`、`scripts/tests/test_f03_sharedmap_reuse.py`（可选，放继承相关回归）、`scripts/tests/test_sqd_gap_repair.py`（仅新增自包含的 β 状态用例）；文档 `references/scan-schemas.md`（仅 §14.1 表内相关行与其后不变量段）、`assets/sqd-solana-coverage-map/README.md`；完成报告 `W1_done.md`（本目录）。
- 0.4 **不改**：`scripts/solana/sqd_repair_core.py`、`scripts/solana/replay_edges.py`、`scripts/solana/spl_edge_core.py`、`scripts/lib/producer_history.py`、`scripts/tests/invariant_manifest.json`、`VERSION`/`pyproject.toml`/`SKILL.md`/`CHANGELOG.md`、`references/` 其他文件、`commands-staging/*`、任何资产二进制。**探针不得新增任何 schema 字符串比较**（修复来源绑定放校验器 helper，§2.2）；若 `invariant_scan.py` 报探针新增消费者 → 停工汇报，不得改 manifest、不得拼接字符串规避。
- 0.5 首次修改前，以目标块内可唯一识别的**完整非空语义行**为锚 `grep -n -F -x -- '<整行>' <文件>`，须恰命中 1 处且行号与本单一致；不选重复赋值或闭合括号行（如 probe `:782`、validator `:246` 均多处命中，只作范围不作锚）。不符**停工**。修改后行号可自然移动，完成报告记实际 diff 行号。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree。临时目录只用系统 `tempfile`（`Path(td).resolve()`）；沙箱若建不了 → 停止对应测试并在报告写明环境限制，**不得**改用 `.staging_*`；**禁止 `rm -rf` 等批量删除**。
- 0.7 不跑 `run_all.py`、`docs_lint.py`、`changelog_lint.py`（它们读禁区，由调度方本机跑并附入验收；报告写「待调度方验收」不得写 PASS）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_sqd_coverage_probe.py`、`test_f03_sharedmap_reuse.py`、`test_batch3_solana_producers.py`、`test_reconcile_v4_receipt.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`；`test_sqd_gap_repair.py`/`test_batch8_repair_scale.py` 只运行不触及禁读夹具的用例（报告逐条列 PASS/未运行及原因）。

## 1. 硬约束

- 1.1 **无继承时不变**：不带 `--known-map`、或资产 `refuted_slots` 为空、或复用回退时，`classify_four_states` 对同输入的 `summary`/`candidate_slots`/`verdict`/`states` 与基线完全一致；summary 与 `shared_map` **均不新增** `inherited_refuted` 键；本单不新增 `coverage_map.states` 字段（states 只在分类器与 `validate_coverage()["recomputed"]` 返回值中）。现役已发布 coverage_map（无继承键）与现役共享资产（无 `refuted_evidence`）在新校验器下**必须继续 PASS**。改 producer 后新产物 probe_id 允许变化，不要求前后相同；测试分别验证「分类兼容」「旧产物兼容」「同版本确定性」。
- 1.2 **继承的唯一路径与残余风险**：地图复用成功（无 `fallback_reason`）∧ slot ∈ 资产 `refuted_slots` ∧ 本次 recheck 对该 slot 实测值＝资产值＝2 ∧ slot 在实际 `reused_ranges` 内且不在 `unverified_ranges` 内 ∧ 该 slot 对应证据项**未过原始时效**（1.7）。任一不满足即不继承（照旧当候选）。**明示残余风险**：驳回继承复用源案的整块签名比对结论，本次只重新验证块头存在且 AdvanceNonce 计数仍为零；该条件不能识别 SQD 在同 slot 增删非 nonce 交易且计数保持零的变化，canary/历史锚/finalized-head 检查也不能消除此风险。本方案依赖来源可信及 SQD 已驳回 slot 的交易集合未发生不可见退化；**不得把 `INHERITED_REFUTED` 表述为本案重新证明了完整性**（文档如实写）。不引入抽样、不放宽 canary/mismatch 整图回退语义、不改 ERA_PARAMS 与候选判据、不改 `sqd_query_body`/查询模板。
- 1.3 状态命名 `INHERITED_REFUTED`（进 `states`；不入 `candidate_slots`/`unconfirmed_slots`；`summary["header_zero_nonce"]` 照常计）；summary 新键 `inherited_refuted` **仅在继承集非空时存在**，计数＝实际分类为该状态的数量。`VERDICTS` 集合与 replay/exact_reconcile 组合判定规则**不变**（无候选无 unconfirmed 时 base 路径仍接受 `NO_KNOWN_NONCE_OMISSION_DETECTED`；repaired 路径仍要求有效修复＋census 覆盖当前候选）；新增测试覆盖「继承后 base 干净路径」与「β 修复后 repaired 路径」。
- 1.4 **β 兼容**：`INHERITED_REFUTED` 不进 α 候选，但不得阻断独立 β 候选。`sqd_gap_repair.py::validate_coverage_state_consistency` 最小修改：保留 α 准入拒绝（非 β 仍 raise「non-candidate coverage state entered alpha」）；仅在 `beta_candidate=True` 时把 `INHERITED_REFUTED` 按「有块头且 nonce_count==0」验证。`solana_exact_validate.py::_repair_state_matches(:1202)` 同步加该状态同判据。census/evidence 的 `coverage_state` 与重算状态全等的检查保留。不得把新状态伪装成 `DEFECT_CANDIDATE`。
- 1.5 **校验器 fail-closed 且跨机可核**：coverage_map 自报的继承集必须由校验器独立复核（§2.4）；来源成员关系凭**资产副本**（§2.3）核，缺副本或副本 sha ≠ `shared_map.sha256` → 拒非空继承。校验失败 → `reasons` 追加且按继承集为空重算（拒绝依据是 reasons 非空，不依赖候选比较必失败——继承可能把本案 `ERA_UNCERTAIN` 改为继承状态，清空后候选未必变化）。
- 1.6 共享资产协议名保持 `sqd-solana-shared-coverage-map/v1`；只**新增可选字段** `refuted_evidence`、`refuted_origin`（§2.1）；旧资产（缺两键、refuted 空）继续 PASS。
- 1.7 **时效**：每条证据项带 `origin_generated_at`（首次直接 census 证明所属 coverage 的发布时刻，ISO-8601 UTC）与 `origin_asset_sha256`（该证据首次进入的资产 sha；首次导出时为 null）。链式导出**原样带出**，不得用后案发布时间重置。继承时要求「本次探针验证时点 ≤ origin_generated_at + 30 天」（按 slot 对应的证据项逐一判，`refuted_origin` 映射）；重查不延长有效期；无 origin 信息的非空 refuted 不可继承（校验器同样按 coverage_map 记录的验证时点核，不因日后重验时间推移否定历史合法发布）。
- 1.8 导出来源只认：(a) 源案**当前已发布** formal 修复代（`--repair-gid` 显式指定＋修复 `CURRENT.json` 必须存在且指向该代，§2.2）；(b) 源案 coverage_map 的 `shared_map.inherited_refuted`（链式）。refuted-only 案无代，自有驳回**不可导出**，只能链式带出继承部分。导出核 §2.2 列出的绑定，不重放整个修复证据目录（来源可信是输入前提，同 9.1.0 认领语义，文档如实写）。
- 1.9 CLI：`build_export_parser` 新增**互斥**参数 `--repair-gid <gid>` 与 `--no-repair`；不新增其他 CLI 参数。mint 取已验证 `coverage["mint"]`；修复 parent/current_path 在分支前统一计算。
- 1.10 生产改动量列入报告（`git diff --numstat cc6298b -- <文件>` 逐文件）；原 ≤140/≤120 上限改为**审查指标**：超过须逐项说明新增职责与复用情况；不得为压行数省略校验或压缩可读性。优先复用现有 helper（`_check_file_ref`、`_success_ranges`、`checked_slots`、`validate_repair_pointer`、`_repair_state_matches` 等）。
- 1.11 `git diff --stat cc6298b -- . ':!maintenance'` 只含 0.3 白名单。

## 2. 逐条施工

### 2.1 共享资产字段（导出侧 `sqd_coverage_probe.py` ＋ 校验 `solana_exact_validate.py::validate_shared_map`）

- `refuted_slots`：整型升序去重，⊆ 资产 raw 候选（用资产二进制、空继承集重算），且资产 counts 该位＝2。
- `refuted_origin`（可选；`refuted_slots` 非空时必填）：整数数组，与 `refuted_slots` 等长，第 i 项＝第 i 个 slot 所属的 `refuted_evidence` 索引（0-based，须 < len(evidence)）。
- `refuted_evidence`（可选；`refuted_slots` 非空时必填非空数组）：每项 `{"kind": "repair-census"|"inherited", "source_mint": str, "probe_id": hex16, "repair_gid": hex16|null, "plan_digest": hex16|null, "resolution_sha256": hex64|null, "bundle_sha256": hex64|null, "producer": {"path": str, "sha256": hex64}, "refuted_count": int>0, "origin_generated_at": ISO-8601 UTC, "origin_asset_sha256": hex64|null, "asset_sha256": hex64|null}`。`kind=="repair-census"`：四个修复字段必填非空、`asset_sha256`=null、`origin_asset_sha256`=null、`origin_generated_at`＝源 coverage pointer.published_at、`producer`＝bundle.producer。`kind=="inherited"`：四个修复字段 null、`asset_sha256`＝直接来源资产 sha、`origin_*` 原样来自来源资产对应证据项、`producer`＝源 coverage_map.producer。`refuted_count` 必须等于 `refuted_origin` 中指向该项的个数（允许为 0 的项不得存在——导出时剔除无 slot 的证据项）。
- `validate_shared_map`（锚 `    refuted = checked_slots(asset.get("refuted_slots"), "refuted_slots")` :863）之后追加：⊆ raw 候选、counts==2、非空时 `refuted_origin`/`refuted_evidence` 形态与计数一致、每项字段合法（含 origin_generated_at 可解析带时区）；空时允许缺键或 `[]`。
- README（`assets/sqd-solana-coverage-map/README.md:43` `  "refuted_slots": [],` 之后）补 `refuted_origin`/`refuted_evidence` 示例；正文「复用是 fail-closed 的」段后加「驳回继承」段（大白话，含 1.2 残余风险原文、1.7 时效、1.8 来源限制、副本文件说明）。

### 2.2 `export-shared-map --repair-gid <gid> | --no-repair`（探针编排＋校验器 helper）

- `build_export_parser`（锚 `def build_export_parser():` :1419）新增互斥组 `--repair-gid`/`--no-repair`。
- 校验器新增 helper（放 `solana_exact_validate.py`，命名如 `validate_repair_export_source(case_root, mint, gid, *, expected_probe_id, coverage_map_sha256, effective_candidates)` → `{"ok", "reasons", "own_refuted": [slot…], "confirmed_slots": [slot…], "bundle_sha256", "resolution_sha256", "plan_digest", "producer"}`），逻辑：
  1. `parent, current_path, _ = sqd_repair_paths(case_root, mint)`；**CURRENT.json 必须存在**（未发布代不接受）；gid 为 16 位小写 hex；`validate_repair_pointer(pointer, expected_mint, expected_gid=gid, expected_bundle_sha256=sha256_file(gen/bundle.json))` 通过；额外核 CURRENT 的 bundle 引用路径 resolve 后恰指向 `parent/gen-<gid>/bundle.json`、size/sha256 与实物一致、路径不逃逸修复目录（复用 `_repair_path/_repair_ref`）。
  2. bundle：schema `sqd-solana-repair-bundle/v1`、kind `repair`、mint、gid、`mode=="formal"`、`reference.source=="live"`、`coverage.probe_id==expected_probe_id`、`coverage.map_sha256==coverage_map_sha256`（字段名按 bundle 实际，施工前 grep 确认）、`coverage_resolution{path,size,sha256}` 绑定所读文件；resolution：schema `sqd-solana-coverage-resolution/v1`、mint、`plan_digest==bundle.plan_digest` 且合法、`coverage.probe_id` 同、producer.path==`scripts/solana/sqd_gap_repair.py` 且 sha ∈ `historical_producer_hashes(path,"sqd-solana-repair-bundle/v1") ∪ {现役文件 sha}`（现役文件 sha 判据同 `:499-506`）。
  3. census：slot 严格整数、排序唯一的对象数组；`result` ∈ 已知枚举；`plan_candidates.coverage`（字段名按实际）与 `effective_candidates` 相同；census 处置覆盖计划候选；`effective_verdict` 与处置重算一致。**不得要求全部 census slot ⊆ coverage.candidate_slots**（β 行合法）。
  4. `own_refuted`＝`result=="refuted"` ∧ `coverage_state=="DEFECT_CANDIDATE"` ∧ 与源 coverage 重算状态相符 ∧ 源 counts==2 ∧ `sqd_nonce_count_at_repair==0` ∧ missing 计数为 0 ∧ 块哈希自洽（字段按实际）的行；`state_in_map` 不作依据。`confirmed_slots`＝`result` 以 `confirmed_` 开头的行（用于剔除冲突继承）。exploration 代（mode≠formal）拒绝。
- `export_shared_map`（锚 `def export_shared_map(args):` :805）在现有 `validate_coverage` 通过后：
  1. `raw_candidates`＝用源 counts/confirmation/bitmap 调 `classify_four_states(..., inherited_refuted=frozenset())` 所得候选（**不再用** `checked["recomputed"]["candidate_slots"]` 作资产 candidate_slots，锚 `:858` 行改为 raw_candidates）。
  2. `inherited`＝源 coverage `shared_map.inherited_refuted`（键缺失即空）：其 `slots` 与逐 slot 证据索引、证据项原样（`kind` 转为 `inherited`、`asset_sha256`＝源 shared_map.sha256、origin 不变）。
  3. 分支：给 `--repair-gid` → 调 helper，失败 `ValueError` 明示 reasons；未给任何选项且 `current_path` 存在 → `ValueError("repair CURRENT exists; pass --repair-gid <gid> or --no-repair")`；`--no-repair` 或无 CURRENT → own 为空、confirmed_slots 为空（无 CURRENT 时）。
  4. `refuted_slots`＝(own ∪ inherited) ∩ raw_candidates，再剔除 ∈ `confirmed_slots` 的继承项（当前 census 处置优先，不静默续传）与已过 1.7 时效的继承项；三类剔除各打印计数到 stderr（非法 own/来源绑定失败不得靠求交掩盖，须报错）。`refuted_origin`/`refuted_evidence` 与实际导出集同步生成（无 slot 的证据项删除）。
  5. 其余导出逻辑不变；导出后 `validate_shared_map` 必过。

### 2.3 探针复用侧（`sqd_coverage_probe.py`）

- `_recheck_known_slots` 返回值已含 `actual`（`:644-647`），`_load_known_map` 内在 `:778` 返回前计算：`inherited`＝资产 `refuted_slots` 中满足 1.2 全部条件（含 1.7 时效按 `refuted_origin` 找证据项）的 slot；非空时 `info["inherited_refuted"] = {"slots": [...], "count": n, "asset_sha256": info["sha256"], "verified_at": <本次验证时点 ISO UTC>, "origin": [<每 slot 对应证据索引>], "refuted_evidence": <资产 evidence 原样>, "source_ref": {path,size,sha256}}`；**空则不写键**。回退分支不写。
- **资产副本**：继承非空时，把资产 JSON **原始字节**作为 coverage 发布件之一写入本案 coverage 目录（文件名如 `shared_map_source.json`），按现有发布协议（与 counts/ledger 同级、三目录 fsync、`_sha_ref` 形态）登记为 `source_ref`；其 sha256 必须＝`shared_map.sha256`。若现有发布协议对发布件清单有硬编码校验（施工前 grep `publish_exclusive`/清单相关代码确认），把副本纳入清单；不能纳入 → 停工汇报。
- `run_probe`（锚 `    classified = classify_four_states(` :1313）传 `inherited_refuted=frozenset(...)`（无继承传空）。`:1333` info 原样落盘。
- `--resume`：resume 时 `shared_map` 为 None（`:1222-1224`），**继承随之丢失**属现状限制；本单不改 resume，完成报告与文档写明。

### 2.4 分类与校验（`solana_exact_validate.py`）

- `classify_four_states`（锚 `def classify_four_states(counts, from_slot, *, confirmation=None,` :223）签名加 `inherited_refuted=frozenset()`；summary 初始化（`:241`）后 `if inherited_refuted: summary["inherited_refuted"] = 0`；`:268` `elif code == 2:` 分支开头：`if slot in inherited_refuted: state="INHERITED_REFUTED"; summary["inherited_refuted"] += 1`（不入候选/unconfirmed），否则原逻辑。
- `validate_coverage`（锚 `def validate_coverage(case_root, coverage_path, pointer_path,` :458）：重算前从 `coverage["shared_map"]` 提取继承集并逐项核（独立实现，不导入探针）：
  1. shared_map 为成功复用（无 `fallback_reason`）；`slots/count/origin/verified_at/source_ref` 严格类型合法（排除 bool），slot 在本案范围内后才索引 counts；
  2. `source_ref` 实物存在（`_check_file_ref`）、sha256＝`shared_map.sha256`；解析副本 → `inherited ⊆ 副本.refuted_slots`、副本 `refuted_origin` 与 coverage_map 记录的 origin 一致、副本 counts 声明值＝2（读副本 JSON 即可，不必解压二进制；若需要核值则读二进制该位）；
  3. 本案 `counts[slot-from_slot]==2`；slot ∈ 实际 `reused_ranges` 且 ∉ `unverified_ranges`；
  4. recheck 成功证明：ledger 中 `mode=="recheck"` 且成功（用 `_success_ranges` 或同等：完整返回、请求范围、查询身份、结果绑定；拒绝失败/短返回/mismatch/整图回退记录）的区间覆盖该 slot——**跨案边界、`counts_coverage=false` 的完整成功 recheck 行可证明其与本案交集内的 slot**，但不得因此把案外区间加入 counts 覆盖；
  5. 每 slot 对应证据项时效：`verified_at ≤ origin_generated_at + 30d`；证据形态同 2.1；
  6. 不符 → `reasons.append("inherited refuted <原因>")` 且继承集置空后再重算。
- `validate_shared_map`（锚 `:863`）按 2.1。
- `_repair_state_matches`（锚 `def _repair_state_matches(state, header_present, nonce_count):` :1202）加 `INHERITED_REFUTED` → `header_present and nonce_count == 0`。
- `sqd_gap_repair.py::validate_coverage_state_consistency`（锚 `def validate_coverage_state_consistency(state, *, header_present,` :576）按 1.4。

### 2.5 文档（本单只改两处）

- `references/scan-schemas.md:667`（`shared_map` 行）说明末尾追加 `,inherited_refuted{slots,count,asset_sha256,verified_at,origin,refuted_evidence,source_ref}`；`:669` `summary` 说明改为 `饱和计数；含 inherited_refuted 键当且仅当继承集非空`；`:697` 后新增 `shared_map.inherited_refuted.*` 字段行；§14.1 不变量段补：「状态 `INHERITED_REFUTED` 只由复用地图的 refuted_slots 经 recheck 值相同（＝2）且证据未过原始时效产生；不入候选；只证块头在、零 AdvanceNonce，不证交易集合未变（残余风险）；resume 不保留继承」。共享资产 README 按 2.1。字节数列入报告（原 ≤1,200 B 改为指标）。

### 2.6 测试

夹具在 `tempfile` 内动态生成，不新增大型静态 fixture。用同一 ERA 窗口内 ≥10,000 个块头（如 9,998 个 code=3、2 个 code=2，两目标 slot 为原始候选）；按实际连续 recheck 区间及 full 扫描 450-slot 分页生成 request_digest 响应；retry 用 FixtureTransport 已支持的响应序列。**新增测试函数必须加入所在文件 `main()` 的显式 tests 列表**。

- (a) 资产 `refuted_slots=[R1,R2]`＋合法 `refuted_origin/refuted_evidence`（origin 在时效内），fixture 重查值＝2 → 发布后：`validate_coverage()["recomputed"]["states"]` 按 `slot-from_slot` 取值为 `INHERITED_REFUTED`；`candidate_slots` 不含；`summary.inherited_refuted==2`；`shared_map.inherited_refuted.slots==[R1,R2]`；副本文件在场且 sha 相符；无候选时 verdict `NO_KNOWN_NONCE_OMISSION_DETECTED`（base 组合判定路径）。
- (b) 同资产 R1 重查值变 3 → 整图回退成功发布、无继承键、summary 无新键；另加：非 canary 失败段（继承与 unverified 并存，落在 unverified 的 R 不继承）、失败后重试成功、canary 最终失败。
- (c) 篡改已发布 coverage_map（同步更新 ledger seq/size/sha/requests/成功区间摘要/probe_id/CURRENT 引用，使检查真正到达继承验证）：非资产 refuted 的候选塞进 `slots`；改 `asset_sha256`；删覆盖 R1 的 recheck 行；副本缺失；副本 sha 不符；越界/负数/bool/重复 slot；unverified 重叠；短返回；证据与 slot 不匹配；origin 过期 → `validate_coverage` 均拒且 reasons 含 `inherited refuted`。正例：跨案边界成功 recheck 行（counts_coverage=false）仍可证明交集内 slot。
- (d) `export-shared-map --repair-gid`：夹具含符合绑定的 CURRENT/bundle/resolution，census 混合 confirmed/refuted → `refuted_slots`＝own∩raw、`refuted_evidence[0].kind=="repair-census"`、`refuted_origin` 正确、`validate_shared_map` PASS。负例：无 CURRENT；错 pointer 路径/size/hash/mint/gid；错 map_sha；错 schema；exploration；重复 census；错 `coverage_state`；无效 producer；状态/计数矛盾；篡改 `refuted_count`；非候选 slot 塞进 refuted；counts 改 3（语义负例同步更新二进制与引用）；有 CURRENT 而无选项 → 报错；`--repair-gid` 与 `--no-repair` 同给 → argparse 拒。
- (e) 链式：(a) 发布的案再导出（带 getBlocks 证据，**不沿用** roundtrip 的 `--no-getblocks`；`--no-repair`）→ 资产 `candidate_slots`＝raw_candidates（含 R1/R2）、`refuted_slots` 含 R1/R2、evidence `kind=="inherited"` 且 origin 未刷新。负例：origin 过期 → 剔除；当前 census 对 R1 confirmed → 剔除。
- (f) 兼容：全部旧用例不变通过；无继承时不写新键；旧 producer 产物继续通过；同版本确定性；β 命中继承 slot（`validate_coverage_state_consistency(..., beta_candidate=True)` 通过、`beta_candidate=False` 拒）与 `_repair_state_matches` 新状态；repaired 组合判定路径；resume 丢失继承后的保守分类。

## 3. 完成报告 `W1_done.md`

首行 `# W1 完成：<一句话>` 或 `# W1 停工：<原因>`。含：§0.1 四项输出；每处施工实际 diff 行号与 `git diff --numstat cc6298b` 逐文件行数（超出原 140/120 指标的逐项说明）；§0.7 测试尾行与未运行清单；1.1 兼容证据（具体用例名）；2.3 resume 限制与副本发布协议处理说明；`invariant_scan.py` 结果（探针无新增消费者）；文档字节数；`git diff --stat cc6298b -- . ':!maintenance'` 只含白名单；末尾披露是否读过禁读路径。
