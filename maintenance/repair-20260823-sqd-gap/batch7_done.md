# 批7 完成报告：修复代深验三处校验覆盖缺口的核实与加固

- 分支 `fix/sqd-gap-v6520`，开工 HEAD `94314de`，工作树干净（门禁通过，见 batch7_green_evidence.txt §0）。
- 版本号保持 **6.52.0 不升**（工程未合并 main、未发布）。
- 全程离线、未 commit（改动留工作树等主控验收）。
- 原始输出全部落在 `batch7_green_evidence.txt`。

---

## 一、逐项核实结论（独立读代码 + 实跑夹具裁定）

### 缺口1（主）——**属实**
`validate_repair_bundle_deep`（`scripts/lib/solana_exact_validate.py`）的 formal 逐 slot 严格校验写在
`for slot in sorted(all_candidates)` 循环体内，而修复边准入判据是 `if slot not in confirmed`
（`confirmed` = census 中 `result` 以 `confirmed_` 开头的 slot，纯自报）。二者主键不一致：
当某个 confirmed 的 slot **不在候选集**里时，逐 slot 严格校验（coverage_state 重算、
state 语义、四个 evidence 哈希、ledger/evidence resume 身份）对它整段跳过，而修复边准入只查
`slot in confirmed` 即放行。census 约束又只有单向 `all_candidates.issubset(census_slots)`
（反向不查），于是攻击者凭一条自报 confirmed census 行，即可让一条**凭空的转账边**通过深验。

**实证（先红）**：在合法 formal 代基础上注入 `census` 一行 `{slot:15000, result:"confirmed_injected"}`
＋ `repair_layer` 一行凭空边 `[EVILATTACKER→VICTIMTREASURY 999999] @slot 15000`（15000 不在 candidate=[19999]），
自洽重封（重算 gid、改 gen 目录名、更新各 ref sha256、merged edge/meta）。加固前深验返回
`ok=True, reasons=[], edge_rows 2→3`——凭空边被无声合并、抬高供应。
→ 端到端链路成立：深验 ok=True 后，`validate_reconcile_v4`（solana_exact_validate.py:1676）与
`replay_edges.cmd_reconcile`（replay_edges.py:373）的 repaired 分支 `combination_ok` 仅依赖
`bundle_result.ok is True and effective=='DEFECTS_CONFIRMED' and current_candidates⊆census and gid对`，
全部满足（effective=DEFECTS_CONFIRMED、current_candidates=候选集⊆census、gid 自洽），
配合自报 snapshot 即 `gate_pass=True`。

### 缺口2——**属实（不对称客观存在、可实证放行），但裁定为离线 validator 固有信任边界，不加 validator 假闸**
`validate_coverage`（自扫路径，solana_exact_validate.py:442）对 `slot_counts` 字节流只做
**自洽性重算**：`classify_four_states(counts,...)` 从 counts 重算 candidate_slots/verdict/summary，
再与 coverage_map 声明比对；`validate_slot_counts` 查长度/无 UNSCANNED/scan==ledger union。
**没有**任何对照真实链上的复查。对照：复用路径的 producer `sqd_coverage_probe.py:436-454`
在 map-reuse 时对 canary+candidate 做 `mode="recheck"` 的**实时联网**复查，validator 侧
`validate_shared_map`（solana_exact_validate.py:685）另有 64-slot canary 静态校验。

**实证**：把 `slot_counts` 里真实缺陷 slot 19999 的字节 `2`(HEADER_ZERO_NONCE→DEFECT_CANDIDATE)
改成 `3`(HEALTHY)，重算并自洽重封 coverage_map（candidate_slots=[]、verdict=NO_KNOWN、summary、
probe_id）＋ 目录改名 ＋ CURRENT 指针 sha/probe_id。`validate_coverage` 返回 `ok=True`、
recomputed.verdict=`NO_KNOWN_NONCE_OMISSION_DETECTED`——真实缺陷被伪成干净，reconcile 走
`combination_ok = verdict==NO_KNOWN` 直接放行，整个修复义务被跳过。

**独立裁定（为何不加固）**：
1. 这套系统的深验哲学是"独立重建、不信任 producer 自报"，但 coverage 自扫的 counts 是
   producer 亲手扫链的**唯一权威产出、无任何离线可验证的外部锚点**（ledger 只记扫描请求范围、
   不记逐 slot 结果哈希；sqd.query_body_sha256/finalized_head 只锚查询指纹不锚计数结果）。
   离线 validator 无法重新扫链核对 counts 真值。
2. 复用路径能防的是"复用一张他处/历史的被篡改地图"，靠的是 producer 的**联网** recheck；
   其 validator 侧 canary 静态校验本身也防不住**协同篡改**（canary_counts 与 counts 同在
   一份 asset 里自报，一起改即绕）。要给自扫路径补"真实性复查"＝要么联网重扫（工单禁联网、
   且 validator 离线），要么改 producer `sqd_coverage_probe.py` 让自扫也产 canary 承诺
   （该文件**不在白名单**，且既有合法自扫 coverage 无 canary 字段、强加会全量误伤）。
3. 因此在"白名单 + 离线 + 不误伤"约束下，任何 validator 侧加固要么无实效（防不住协同篡改＝
   装了等于没装的假闸）、要么误伤合法路径。按"内部自洽≠真实性""假闸不如不装""不误伤合法
   路径"的既定纪律，**如实记录边界、不加假闸**，而非把缺口固化成"放行"测试。
   建议（超本工单范围，供后续立项）：若要真堵，需在 producer 侧对自扫也生成 canary 采样承诺，
   并在消费时对 canary 采样点做联网 recheck——本质是把复用路径的联网复查对称地引入自扫路径。

### 缺口3——**属实**
深验 `validate_repair_bundle_deep` 完全不读 `finalized_upper_slot`、不校验任何边的 slot 上界；
`replay_edges.cmd_reconcile`（replay_edges.py:373）只校验 `as_of_slot==finalized_upper_slot`，
`_replay_with_evidence` 用**全部**冻结边算 minted/burned/余额、不查 `slot ≤ to`。于是边文件里
存在 `slot > 声明 upper` 的边（谎报采集时点/夹带超窗口数据）时，深验与 reconcile 都放行。

**实证（先红）**：合法 formal 代 base 边追加一条 `slot=25000` 的边（声明窗口 upper=19999），
自洽重封 base/merged/meta（base 不进 gid_material，gid 不变）。加固前深验 `ok=True, edge_rows 2→3`。

---

## 二、加固修法与代码位置（仅改白名单内 `scripts/lib/solana_exact_validate.py` 深验）

### 缺口1（五处，全部限定 `mode=="formal"`；exploration 探索代不进正式发布路径、豁免）
- **反向包含** `solana_exact_validate.py:1265-1270`：`if mode=="formal" and not confirmed.issubset(all_candidates): reasons.append("confirmed census slots escape candidate set")`。
- **干净 verdict 零修复边** `:1271-1274`：`effective==NO_KNOWN` 时 `confirmed` 与 `repair_layer.edges` 必须为 0。
- **formal 拒 exploration 指纹** `:1275-1280`：formal 下任一 census 行 `sqd_nonce_count_at_repair is None` 即拒（不依赖候选循环触达）。
- **遍历主键改** `:1302-1311`：formal 逐 slot 严格校验遍历 `all_candidates ∪ confirmed ∪ {repair_layer 各 slot}`（`repair_touched`）；exploration 保持仅 `all_candidates` 遍历。
- **ledger 实物下限** `:1340-1346`：formal 下 `len(ledger_rows)-1 ≥ 修复层 slot 数`。

### 缺口3（一处）
- **边 slot ⊆ 声明窗口** `solana_exact_validate.py:1415-1424`：所有 merged 边的 slot 必须落在
  coverage 窗口 `[slot_meta.from_slot, slot_meta.to_slot]` 内，且 `base.finalized_upper_slot == window_upper`。

### 缺口2
- 不改代码（裁定见 §一）。

**为何这套改法能拦死缺口1而不误伤 exploration**：缺口1 攻击面在 formal（能被 resolver 接受、
进 reconcile gate）；exploration 代用本地区块缓存可**合法地**确认 SQD 自扫（指纹）漏标的缺陷，
故 exploration 的 confirmed 合法地超出 candidate、且它不产 CURRENT 指针、不进正式发布路径。
首轮加固未区分模式，误伤了 `--blocks-cache` exploration 代（`confirmed census slots escape
candidate set`，见 green_evidence §3）；改为 formal-only 后误伤消除、formal 攻击仍被拦。

---

## 三、先红后绿证据（详见 batch7_green_evidence.txt）

| 缺口 | 红测试（正式回归函数） | 先红（加固前） | 后绿（加固后） |
|---|---|---|---|
| 缺口1 | `test_batch7_validator_coverage_gaps.py::gap1_regression` | 深验 `TAMPERED_OK True`、凭空边合并 edge_rows 2→3（green_evidence §1） | `TAMPERED_OK False`，reasons0=`confirmed census slots escape candidate set`（§2/§4） |
| 缺口3 | `test_batch7_validator_coverage_gaps.py::gap3_regression` | 深验 `GAP3_TAMPERED_OK True`（§1） | `TAMPERED_OK False`，reason=`merged edge slot escapes declared coverage window`（§2/§4） |
| 缺口2 | 不固化（裁定离线信任边界） | `GAP2_TAMPERED_OK True`（§1，作为实证留档） | 保持放行（不加假闸；§一裁定） |

正式回归 `test_batch7_validator_coverage_gaps.py` 每项**同时**断言"合法 formal 代放行(不误伤)"＋
"篡改代被拒(加固生效，且命中预期理由)"。加固后跑：两项全 GREEN（green_evidence §4）。

---

## 四、不误伤合法路径 + run_all 结果

- 工单点名三项合法回归全绿（green_evidence §5）：
  `test_batch3_solana_vertical_slice.py`（真 producer→runner→aggregator→READY→release）、
  `test_reconcile_v4_receipt.py`、`test_sqd_gap_repair.py`（含 `--blocks-cache` exploration 端到端）。
- `invariant_scan.py` PASS，minimum_counts 下限不破（producers=75/consumers=112/transport=65/
  atomic=56/formal=61/exceptions=0），未改 `invariant_manifest.json`（我只加校验分支、未减任何
  producer/consumer/transport/atomic_write/formal_entrypoint，也未动 vertical-slice 挂载）。
- **完整 `run_all.py`：129 项全 PASS（"全部通过"）**，含新增 `test_batch7_validator_coverage_gaps.py`。

## 五、收尾登记
- 新测试注册进 `run_all.py`（SQD 组后，SUITE 128→129）。
- `CHANGELOG.md` 6.52.0 条目「producer 与回归」下补一条批7加固记录（版本号未升）。
- 契约冻结件/PLAN.md/VERSION/SKILL 版本行/部署副本/fetch_sqd_transfers_v2.py 与 7 元组协议：未改。
- 未发现工单外的新契约级不一致。
