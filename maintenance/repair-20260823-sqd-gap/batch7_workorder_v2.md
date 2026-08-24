# 批 7 工单（fresh 会话）：校验器健壮性加固 —— 补齐三处校验覆盖缺口（先红后绿）

【开工门禁】开工第一步 `git rev-parse HEAD` 必须以 `94314de` 开头、`git status --short` 干净、分支 `fix/sqd-gap-v6520`；不符即写停工报告并停。

## 背景
v6.52.0（SQD 覆盖闸 ＋ 修复生产者窄门）六批施工已完成（HEAD 94314de，未合并 main、未发布）。发布前对修复代校验器（validator）做健壮性复查，定位到三处**校验覆盖缺口**——校验逻辑在某些边界输入下不会执行到应有的检查分支。本工单请你**独立核实这三处缺口是否真实存在（基于代码本身判断，不要盲信下面的描述）**，对真实存在的缺口先写复现红测试、再加固到绿，并保证不误伤合法路径。三处缺口的代码位置与触发条件已为你定位好，无需任何外部材料。

## 第一步：独立核实（你自己读代码判断，逐项给"属实 / 不属实 ＋ 理由"）

### 缺口 1（主）—— formal 严格校验的遍历主键绑定在 coverage 候选集上
位置：`scripts/lib/solana_exact_validate.py::validate_repair_bundle_deep`（约 1064–1365 行）。
观察：formal 模式的逐 slot 严格校验写在 `for slot in sorted(all_candidates):`（约 1286 行）循环体内；而 `all_candidates = set(plan_candidates["coverage"]) | set(plan_candidates["beta"])`（约 1256 行）。当 coverage 判定为干净（`candidate_slots=[]`）、或修复层里边所在的 slot 不在候选集内时，这个循环体覆盖不到这些 slot，逐 slot 严格校验被整段跳过。此外 census 约束只有单向 `all_candidates.issubset(census_slots)`（约 1258 行，反向不查），修复边准入判据 `if slot not in confirmed`（约 1360 行）里的 `confirmed` 全部来自 census 自报字段。
待核实：构造一个 coverage 判定为 NO_KNOWN_NONCE_OMISSION_DETECTED（candidate_slots 为空）、但 repair_layer 中含若干额外边（例如某地址多出一笔增发）的修复代夹具，自洽重封（重算 gid、改目录名、重写 CURRENT 指针），核实它能否依次通过：`validate_repair_bundle_deep`（ok=True）→ `sqd_cache_identity.resolve_formal_cache`（接受为 kind=repaired）→ `replay_edges.py reconcile`（gate_pass=true 且余额/供应被抬高）。

### 缺口 2 —— coverage 自扫路径缺真实性复查
本案自扫产出的 `slot_counts` 落盘后，validator 是否只做自洽性重算（长度 / UNSCANNED 残留 / summary 一致），而不做真实性复查；对照：共享地图复用路径有 canary 实时 recheck。核实这个不对称是否可被用来：把一个真实 INCONCLUSIVE 缺陷案的缺陷 slot 计数字节改掉、伪成干净（NO_KNOWN…），从而跳过整个修复义务。（这一项此前两种分析结论不一致，请你实跑独立裁定。）

### 缺口 3 —— 深验是否校验"边 slot ⊆ 声明窗口"
把 `finalized_upper_slot` 收窄（如 19999→19996）并同步三等式（cache upper == 快照 == --as-of-slot）后，深验是否漏检"边文件里边的实际 slot 落在声明窗口 [from, upper] 内"——即边文件存在 slot > 声明 upper 的边仍 PASS。核实属实与否。（此项此前也是两种结论不一致，请独立裁定。）

## 第二步：加固属实项（先红后绿）
对核实**属实**的每项：先写 expected-red 回归测试（在仓库测试内构造对应边界场景，先跑红＝确认缺口真实存在），再加固到绿。加固方向仅供参考，**是否采纳、有无更干净的改法你自己判**：
- 缺口 1：逐 slot 严格校验的遍历主键从"coverage 候选集"改为"实际产生修复边的 slot 集合"（census 中 result 以 `confirmed_` 开头的 slot ∪ repair_layer 各行 slot），逐个跑现有 formal 检查；加反向包含 `confirmed ⊆ all_candidates`；formal 下要求 rpc_ledger 实物（requests ≥ 修复 slot 数、每个修复 slot 有 params_digest 命中的 getBlock 行）；exploration 指纹（`sqd_nonce_count_at_repair is None`）在 mode=formal 下一律拒（不再依赖候选循环触达）；resolver 侧兜底核对 `bundle.coverage.probe_id == 当前 CURRENT coverage 的 probe_id`。语义补强：coverage `verdict == NO_KNOWN_NONCE_OMISSION_DETECTED` 时，confirmed census 行数必须为 0 且 repair_layer.edges 必须为 0（干净 coverage 不该有修复代）。
- 缺口 2 属实 ⇒ 给 coverage 自扫路径补真实性复查或等价的显式声明约束。
- 缺口 3 属实 ⇒ 深验补"边 slot ⊆ 声明窗口"。
- **不误伤合法路径**：加固后必须跑通仓库既有的合法路径回归——`scripts/tests/test_batch3_solana_vertical_slice.py`（合法 repaired 纵切片端到端）、`scripts/tests/test_sqd_gap_repair.py`、`scripts/tests/test_reconcile_v4_receipt.py`——证明合法 base 代与合法 repaired 代照常放行。

## 收尾
- 新增回归测试注册进 `scripts/tests/run_all.py`（SUITE 数相应更新）；`scripts/tests/invariant_manifest.json` 若计数受影响一并核对。
- `CHANGELOG.md` 6.52.0 条目补一句（**版本号保持 6.52.0 不升**——本工程尚未合并 main、未发布）。
- `maintenance/repair-20260823-sqd-gap/batch7_done.md`：逐项核实结论（属实 / 不属实 / 理由）、每项修法与代码位置、先红后绿证据（红测试名 ＋ 红证 ＋ 修后绿）、合法路径不误伤证据、`run_all.py` 结果。
- `batch7_green_evidence.txt` 存 run_all 与关键复现输出。

## 边界
- 白名单：`scripts/lib/solana_exact_validate.py`、`scripts/solana/sqd_gap_repair.py`、`scripts/solana/replay_edges.py`、`scripts/solana/sqd_cache_identity.py`、`scripts/report/shared_release_receipt.py`（仅当 resolver 兜底 / 派生绑定确需）、`scripts/tests/**`（新增 / 改回归测试与 run_all / invariant_manifest）、`CHANGELOG.md`（仅补一句，不改版本号）、`maintenance/repair-20260823-sqd-gap/batch7_*.md`。
- 禁改：契约冻结件（发现契约级不一致只在 done 记录，不擅改）、PLAN.md、VERSION / pyproject / SKILL 版本行、部署副本 ~/.claude/commands、fetch_sqd_transfers_v2.py 与 7 元组协议、既有 base 缓存语义。
- 先红后绿；**不 commit**（Fable 代 commit）；**不联网**（live-canary 相关只用离线夹具验证判定逻辑）；核实为不属实的项不改、在 done 记录理由；工单外的新问题只记录进 done。完成即停。
