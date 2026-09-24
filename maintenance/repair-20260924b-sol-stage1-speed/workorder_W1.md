# 工单 W1（v1）：共享覆盖地图「驳回继承」——refuted_slots 由修复 census 填充；探针复用地图时经一次 SQD 重查即继承，不再进候选；校验器同步重算 —— 归属版本 9.2.0（版本登记在 W2）

> 出处：用户 2026-09-24 裁决第 1 条「驳回过的 slot 记进共享地图,后案只做一次便宜的 SQD 状态确认就继承」；2026-08-23 已裁决 E22「全普查＋驳回继承」但至今未落地（导出恒写 `"refuted_slots": []`）。
> 调度方实证（案卷不在本仓库）：PYTHIA 0919 案 α 修复 157,700 候选中 155,642（98.7%）与 TROLL 0905 共享地图 `candidate_slots` 完全相同（缺陷是 SQD 数据集层面的，与 mint 无关）；修复 census refuted 150,133 / confirmed_nonce_defect 7,566 / confirmed_other_defect 1；补边 0；Helius 下载 366.7 GB、约 157 万 credits。
> 事实（调度方本机亲核，基线 `cc6298b` 9.1.1；行号以该基线为准，锚整行 `grep -n -F -x` 恰 1 处）：
> ① `scripts/solana/sqd_coverage_probe.py:670` `_load_known_map`：校验三件套/TTL 30 天/身份/历史锚后，`:743` 重查集合＝`canary.slots ∪ candidate_slots ∪ refuted_slots`；`_recheck_known_slots(:573)` 把重查集合按 `_contiguous_ranges(:557)` 切成连续区间逐段请求（`_scan_request` mode=`recheck`），逐 slot 比对资产 counts：任一 `mismatch` → 整图作废（返回 `recheck-mismatch:<slot>` 由 `:781-784` 记 `fallback_reason` 回退全扫）；`request-failed` 重试一轮仍失败 → 记 `unverified_ranges` 只剔除该段。`:778` 返回 `info, bytes(reused), overlap_from, overlap_to`；`actual` 字典（重查得到的逐 slot 值）目前只在函数内用于 canary 比对，不外传。
> ② `run_probe`：`:1228` `if reused is not None:` 把复用 counts 写进本案 counts 并追加 `map-reuse` ledger 行；`:1313` `classified = classify_four_states(counts, args.from_slot, confirmation=confirmation, blocks_bitmap=bitmap)`；`:1333` `"skipped_confirmation": confirmation, "shared_map": shared_map,` 把 `_load_known_map` 的 `info` 原样写进 coverage_map。
> ③ `scripts/lib/solana_exact_validate.py:223` `classify_four_states(counts, from_slot, *, confirmation=None, blocks_bitmap=None)`；`:268` `elif code == 2:` 分支：时代校准通过 → `DEFECT_CANDIDATE` 入 `candidates`，否则 `ERA_UNCERTAIN` 入 `unconfirmed`；summary 键集固定（`:242-246`）。`:676` `validate_coverage` 用同函数重算，`:684-689` 要求 `summary`/`candidate_slots`/`verdict` 三者与 coverage_map 全等。`:711` `validate_shared_map`：`:863` `refuted_slots` 只做「整型/排序去重/区间内」形态检查，无其他语义；`:877-880` 要求 `candidate_slots` 等于用资产二进制重算的候选。
> ④ `sqd_coverage_probe.py:805` `export_shared_map`：从源案 `data/sqd_coverage/CURRENT.json` 所指发布代导出三件套，`:859` 恒写 `"refuted_slots": [],`；无任何读取修复代的逻辑。
> ⑤ 修复侧：`scripts/solana/sqd_gap_repair.py:576` `validate_coverage_state_consistency` 对非 `DEFECT_CANDIDATE/MISSING_BLOCK` 状态直接 `raise`（新状态天然不进 α）；`_plan(:596)` 候选＝`coverage.candidate_slots`；修复代 `gen-<gid>/coverage_resolution.json`（`sqd-solana-coverage-resolution/v1`）的 `census[]` 每行含 `slot/state_in_map/result/coverage_state/...`，`result ∈ {confirmed_nonce_defect, confirmed_other_defect, confirmed_missing_block, refuted}`；`bundle.json` 含 `coverage.probe_id`、`coverage_resolution{path,size,sha256}`、`producer{path,sha256}`、`mode`、`plan_digest`、`gid`。修复代目录＝`sqd_cache_identity.sqd_repair_paths(root, mint)` 返回的 `parent / f"gen-{gid}"`，指针 `parent / "CURRENT.json"`。**refuted-only 不产代不发指针**（`:1493` 只打印 status，`scan-schemas.md:953` 不变量）。
> ⑥ 消费 `classify_four_states` 的地方共 4 处：`sqd_coverage_probe.py:1313`、`solana_exact_validate.py:676`（validate_coverage）、`:877`（validate_shared_map 重算资产候选）、修复深验 `:1574` 取 `recomputed["states"]` 只用于修复触及 slot 的状态对表；`sqd_gap_repair.py:1369` 同样只做 states 映射。`handoff_manifest.py`/`audit_release_gate.py` 不读 summary 各键（调度方 grep 无命中）。
> ⑦ 现役共享地图资产：仓库 `assets/sqd-solana-coverage-map/20260827.json`（ARC 导出，`generated_at` 决定 TTL）；案侧 TROLL `data/shared_sqd_coverage/20260905.json`（candidate_slots 155,642、refuted_slots 0）。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `W1_done.md`：`git status --short`（须为空）、`git rev-parse --short HEAD`；`git merge-base --is-ancestor cc6298b HEAD` 须 exit 0；`git diff --quiet cc6298b HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets` 须 exit 0。任一不符**停工**。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、本工程目录以外的全部历史 `maintenance/` 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。本目录可读：`README.md`、`workorder_W*.md`、`review_W1_reply_*.md`。
- 0.3 **白名单**（可写）：生产 `scripts/solana/sqd_coverage_probe.py`、`scripts/lib/solana_exact_validate.py`；测试 `scripts/tests/test_sqd_coverage_probe.py`；文档 `references/scan-schemas.md`（仅 §14.1 表内相关行与其后不变量段）、`assets/sqd-solana-coverage-map/README.md`；完成报告 `W1_done.md`（本目录）。
- 0.4 **不改**：`scripts/solana/sqd_gap_repair.py`、`scripts/solana/sqd_repair_core.py`、`scripts/solana/replay_edges.py`、`scripts/lib/producer_history.py`、`scripts/tests/invariant_manifest.json`、`VERSION`/`pyproject.toml`/`SKILL.md`/`CHANGELOG.md`（版本登记归 W2）、`references/` 其他文件、`commands-staging/*`、任何资产二进制。
- 0.5 首次修改前，以目标块内可唯一识别的非空整行为锚 `grep -n -F -x -- '<整行>' <文件>`，须恰命中 1 处且行号与本单一致；不符**停工**。修改后行号可自然移动，完成报告记实际 diff 行号。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree。临时目录用 `tempfile` 并 `Path(td).resolve()`；沙箱若建不了系统临时目录，`mkdir -p "$PWD/.staging_w1/tmp" && export TMPDIR="$PWD/.staging_w1/tmp"`，结束 `rm -rf`。
- 0.7 不跑 `run_all.py`（调度方本机跑）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_sqd_coverage_probe.py`、`test_sqd_gap_repair.py`、`test_batch8_repair_scale.py`、`test_reconcile_v4_receipt.py`、`test_batch3_solana_producers.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`docs_lint.py`。

## 1. 硬约束

- 1.1 **无继承时字节不变**：不带 `--known-map`、或带地图但资产 `refuted_slots` 为空、或复用回退时，coverage_map 的 `summary`/`candidate_slots`/`verdict`/`states` 与基线逐字节相同（`summary` **不得**出现新键；现有全部夹具的 `probe_id` 不变，以现有测试通过为证）。现役已发布 coverage_map（无 `inherited_refuted`）与现役共享资产（无 `refuted_evidence`）在新校验器下**必须继续 PASS**。
- 1.2 **继承的唯一路径**＝地图复用成功 ∧ 该 slot 在资产 `refuted_slots` 内 ∧ 本次 recheck 对该 slot 实测值＝资产值＝2（有块头、零 AdvanceNonce）∧ 该 slot 落在 `reused_ranges` 内且不在 `unverified_ranges` 内。任一不满足即不继承（照旧当候选）。**不引入抽样、不放宽 canary/mismatch 整图回退语义、不改 ERA_PARAMS 与候选判据。**
- 1.3 继承状态命名 `INHERITED_REFUTED`（ASCII，进 `states`；不入 `candidate_slots`，不入 `unconfirmed_slots`）；summary 新键 `inherited_refuted` **仅在继承集非空时存在**。`VERDICTS` 集合不变。
- 1.4 校验器 fail-closed：coverage_map 自报的继承集必须能从「资产哈希绑定＋recheck ledger 成功区间＋counts 值＋reused/unverified 区间」独立复核；任一不符 → `reasons` 追加且**按继承集为空重算**（从而 summary/candidate_slots 对比必失败）。校验器**不要求**共享资产文件在场（跨机验证）；资产在场时（`shared_map.asset_path` 可读且 sha 相同）额外核 `inherited ⊆ asset.refuted_slots`。
- 1.5 共享资产协议名保持 `sqd-solana-shared-coverage-map/v1`；只**新增可选字段** `refuted_evidence`。`validate_shared_map` 新增语义：`refuted_slots ⊆ 重算候选`、`counts[refuted]==2`、`refuted_slots` 非空时 `refuted_evidence` 为非空数组且形态合法、各项 `refuted_count` 之和 ≥ `len(refuted_slots)`；空时允许缺键或 `[]`。
- 1.6 导出的驳回来源只认两种：(a) 源案**已发布**修复代 `gen-<gid>` 的 `coverage_resolution.json`（经 `--repair-gid` 显式指定，见 2.2）；(b) 源案 coverage_map 自身的 `shared_map.inherited_refuted.slots`（链式继承）。refuted-only 案（无代）自有驳回**不可导出**，只能链式带出继承部分——文档如实写明。导出不深验修复代全量证据（来源可信是输入前提，同 9.1.0 认领语义），但必须核 2.2 列出的绑定。
- 1.7 生产改动量：`sqd_coverage_probe.py` ≤ 140 行、`solana_exact_validate.py` ≤ 120 行（增删合计）；不新增 CLI 参数（`--repair-gid` 除外）；不改 `sqd_query_body`/查询模板（否则所有现役地图身份失效）。
- 1.8 `git diff --stat` 只含 0.3 白名单；`docs_lint.py` PASS。

## 2. 逐条施工

### 2.1 共享资产字段（`sqd_coverage_probe.py` export ＋ `solana_exact_validate.py` validate_shared_map）

- `refuted_slots`：整型升序去重，⊆ 资产重算候选，且资产 counts 该位＝2。
- `refuted_evidence`（可选，数组）：每项 `{"kind": "repair-census" | "inherited", "source_mint": str, "probe_id": str(16 hex), "repair_gid": str(16 hex)|null, "plan_digest": str(16 hex)|null, "resolution_sha256": hex64|null, "bundle_sha256": hex64|null, "producer": {"path": str, "sha256": hex64}, "refuted_count": int>0, "asset_sha256": hex64|null}`。`kind=="repair-census"` 时 `repair_gid/plan_digest/resolution_sha256/bundle_sha256` 必填非空、`asset_sha256` 为 null；`kind=="inherited"` 时反之（`asset_sha256`＝继承来源资产 sha，四个修复字段 null）。`producer` 为写出该证据的脚本（repair-census → `scripts/solana/sqd_gap_repair.py` 与 bundle.producer.sha256；inherited → 源案 coverage_map.producer）。
- `validate_shared_map`（锚 `:863` `    refuted = checked_slots(asset.get("refuted_slots"), "refuted_slots")`）之后追加上述语义检查；README `:43` `  "refuted_slots": [],` 之后补 `"refuted_evidence": [...]` 示例，并在正文「复用是 fail-closed 的」段落后加一段「驳回继承」语义（大白话：驳回＝源案用 Helius 整块比对证明 SQD 该 slot 没漏非投票交易；后案只重查 SQD 该 slot 仍是“有块头零 nonce”即继承，不再拉 Helius；SQD 一变即回退全扫；来源可信是前提）。

### 2.2 `export-shared-map --repair-gid <gid>`（`sqd_coverage_probe.py`）

- `build_export_parser`（锚 `:1419` `def build_export_parser():`）新增可选 `--repair-gid`。
- `export_shared_map`（锚 `:805`）在现有 `validate_coverage` 通过后：
  1. 读源案 coverage_map；`inherited = coverage.get("shared_map", {}).get("inherited_refuted", {}).get("slots", [])`（键不存在即 []），来源证据项 `kind="inherited"`（`asset_sha256`＝源 coverage_map.shared_map.sha256，`probe_id`＝源 probe_id，`producer`＝源 coverage.producer）。
  2. 若给了 `--repair-gid`：`parent, current_path, _ = sqd_cache_identity.sqd_repair_paths(case_root, mint)`；`gen = parent / f"gen-{gid}"`；读 `gen/bundle.json` 与 `gen/coverage_resolution.json`；硬核：`bundle.schema=="sqd-solana-repair-bundle/v1"`、`bundle.gid==gid`、`bundle.mode=="formal"`、`bundle.coverage.probe_id==args.probe_id`、`bundle.coverage_resolution.sha256==sha256_file(resolution)` 且 size 一致、`resolution.plan_digest==bundle.plan_digest`、`resolution.coverage.probe_id==args.probe_id`、`resolution.effective_verdict ∈ {DEFECTS_CONFIRMED, NO_KNOWN_NONCE_OMISSION_DETECTED}`、`bundle.producer.path=="scripts/solana/sqd_gap_repair.py"` 且 `bundle.producer.sha256 ∈ historical_producer_hashes(path, "sqd-solana-repair-bundle/v1") ∪ {现役文件 sha}`、`{row.slot} ⊆ coverage.candidate_slots`、`CURRENT.json` 若存在则其 `gid==gid`（指针形态按 `validate_repair_pointer` 现有函数）；任一不符 `ValueError` 明示原因。`own = sorted(row.slot for row in census if row.result=="refuted" and row.state_in_map=="DEFECT_CANDIDATE")`；证据项 `kind="repair-census"`。
  3. 未给 `--repair-gid` 而 `current_path` 存在 → `ValueError("repair CURRENT exists; pass --repair-gid to export refuted census or omit intentionally")`（防漏导；用户要明示才跳过 → 提供 `--no-repair` 开关显式跳过）。
  4. `refuted_slots = sorted(set(own) ∪ set(inherited)) ∩ 重算候选`（差集若非空打印计数到 stderr，不报错）；写 `refuted_evidence`。
  5. 其余导出逻辑不变；导出后 `validate_shared_map` 必过。

### 2.3 探针复用侧（`sqd_coverage_probe.py`）

- `_load_known_map`：在 `_recheck_known_slots` 返回后、`:778` 返回前，计算 `inherited = sorted(s for s in asset.get("refuted_slots", []) if overlap_from <= s <= overlap_to and s in actual and actual[s] == 2 and asset_counts[s - afrom] == 2 and not any(a <= s <= b for a, b in unverified))`；`info["inherited_refuted"] = {"slots": inherited, "count": len(inherited), "asset_sha256": info["sha256"], "refuted_evidence": list(asset.get("refuted_evidence") or [])}`。回退（except 分支）不写该键。`actual` 已由 `_recheck_known_slots` 返回（`:641-645`），无需改其签名。
- `run_probe`：锚 `:1313` `    classified = classify_four_states(`——改为传 `inherited_refuted=frozenset(shared_map["inherited_refuted"]["slots"]) if shared_map and shared_map.get("inherited_refuted") else frozenset()`。`:1333` 不变（info 原样落盘）。
- `--resume` 路径：resume 加载同 identity checkpoint 时 `shared_map` 为 None（现状 `:1222-1224` 只在非 resume 加载地图）——**继承随之丢失**属现状限制（PYTHIA-RAW-002 已记录 resume 不支持 overlay）；本单不改 resume，但完成报告必须写明。

### 2.4 分类与校验（`solana_exact_validate.py`）

- `classify_four_states`（锚 `:223`）签名加 `inherited_refuted=frozenset()`；summary 初始化后 `if inherited_refuted: summary["inherited_refuted"] = 0`；`:268` `elif code == 2:` 分支开头：`if slot in inherited_refuted: state = "INHERITED_REFUTED"; summary["inherited_refuted"] += 1`（不入 candidates/unconfirmed，`summary["header_zero_nonce"]` 照常 +1），否则原逻辑。
- `validate_coverage`（锚 `:676`）：在调用前从 `coverage.get("shared_map")` 提取继承集并逐项核 1.4：`slots` 升序去重整型；`count==len(slots)`；`asset_sha256==shared_map.sha256`；每 slot ∈ 某 `reused_ranges` 段且 ∉ 任一 `unverified_ranges` 段；`counts[slot-from_slot]==2`；ledger 中 `mode=="recheck"` 且 `_successful_coverage_range` 非 None 的区间并集覆盖该 slot；`refuted_evidence` 形态同 2.1；资产在场则 `⊆ asset.refuted_slots`。不符 → `reasons.append("inherited refuted <原因>")` 且继承集置空后再重算。
- `validate_shared_map`（锚 `:863`）按 2.1 追加。

### 2.5 文档（本单只改两处）

- `references/scan-schemas.md:667`（`| \`shared_map\` | object\|null | 是 | ...`）说明末尾追加 `,inherited_refuted{slots,count,asset_sha256,refuted_evidence}`；`:669` `| \`summary\` | object | 是 | 饱和计数 |` 说明改为 `饱和计数；含 inherited_refuted 键当且仅当继承集非空`；`:697` 后新增四行 `shared_map.inherited_refuted.*` 字段行；§14.1 不变量段补一句「状态 `INHERITED_REFUTED` 只由复用地图的 refuted_slots 经 recheck 值相同产生；不入候选」。共享资产 README 按 2.1。合计 ≤ 1,200 B。

### 2.6 测试（`scripts/tests/test_sqd_coverage_probe.py`）

扩展 `:538` `test_shared_map_lifecycle_rechecks_all_known_and_canary` 或新增用例，覆盖：
- (a) 资产 `refuted_slots=[R1,R2]`＋合法 `refuted_evidence`，fixture 重查值＝2 → 发布后 coverage_map：`states[R]=="INHERITED_REFUTED"`、`candidate_slots` 不含、`summary.inherited_refuted==2`、`shared_map.inherited_refuted.slots==[R1,R2]`；`validate_coverage` PASS；无候选时 verdict `NO_KNOWN_NONCE_OMISSION_DETECTED`。
- (b) 同资产，R1 重查值变为 3 → `recheck-mismatch` 整图回退、无 `inherited_refuted` 键、summary 无新键。
- (c) 篡改已发布 coverage_map：①把一个非资产 refuted 的候选加进 `inherited_refuted.slots`；②改 `asset_sha256`；③删掉覆盖 R1 的 recheck ledger 行（需同步重算 ledger sha 后放行到该检查）——`validate_coverage` 均拒且 reasons 含 `inherited refuted`。
- (d) `export-shared-map --repair-gid`：夹具 gen（最小 bundle.json＋coverage_resolution.json，producer.sha256 用现役 `sqd_gap_repair.py` 文件 sha）导出 → `refuted_slots` 含 census refuted ∩ candidates、`refuted_evidence[0].kind=="repair-census"`；`validate_shared_map` PASS；篡改 `refuted_count=0`、把非候选 slot 塞进 `refuted_slots`、把 counts 值改 3 → 各拒；有 CURRENT 而未给 `--repair-gid/--no-repair` → 报错。
- (e) 链式：把 (a) 发布的案作为源案再导出（无 `--repair-gid`，`--no-repair`）→ `refuted_slots==[R1,R2]`、evidence `kind=="inherited"`。
- (f) 旧资产（无 `refuted_evidence` 键、refuted 空）与既有全部用例不变通过。

## 3. 完成报告 `W1_done.md`

首行 `# W1 完成：<一句话>` 或 `# W1 停工：<原因>`。含：§0.1 四项输出；每处施工实际 diff 行号与行数（两生产文件各自证 ≤ 上限）；§0.7 全部测试尾行；1.1 字节不变证据（现有夹具 probe_id 前后相同的具体用例名）；2.3 resume 限制说明；`git diff --stat cc6298b -- . ':!maintenance'` 只含白名单；末尾披露是否读过禁读路径。
