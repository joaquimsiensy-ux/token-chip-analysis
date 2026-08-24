# opus 攻击型盲审 verdict —— v6.52.0 全工程（批 6 后、合并 main 前）

- 仓库：`/Users/uravvv/.claude/skills/token-chip-analysis`，分支 `fix/sqd-gap-v6520`
- HEAD 核验：`94314de99cbc3e54fa9d9ef9f42f55b361a92eda` ✅（开审前 `git rev-parse HEAD` 核对，结审再核一次未变）
- 仓库改动：**零**（`git status --porcelain` 空）。全部攻击在 `/private/tmp/opus_attack_v6520/` 下自建案根完成
- 基线：`python3 scripts/tests/run_all.py` → **全部通过**（含 `test_sqd_coverage_probe 12/12`、`test_sqd_gap_repair`、`test_reconcile_v4_receipt`、`test_recon_fifth_check`）
- 联网：全程离线（transport-fixture）。`--live-canary` 需真实 RPC，**未验**

---

## 总裁定：**BLOCK**

37 个攻击向量实跑，**3 条 BREACH、5 条 WEAK、其余 DEFENDED**。

需要说清楚比例：这套闸的防御强度整体很高——手改 verdict、挖 ledger 洞、改 census 不重算 gid、evidence 少文件、指针指孤儿代、exploration 冒 formal、CAS 漂移、refuted-only 产代、手拼 gate_pass、wrapper 降 v2、缺第五项、binding 不全等、案根 symlink、案外复制 base、CURRENT 有效时回落 base、402 配额路径 key 脱敏……**全部干净拒绝**，且拒绝理由精准。BLOCK 不是对架构的否定，而是下面 3 条具体缺口在按任务书判据（"任一伪造/绕过成功产出正式可消费产物或过闸"＝BREACH）下必须计。

3 条 BREACH 里，**B-10 与 C-3c 是可直接补的检查缺项**；**A-2b 属于"validator 是一致性校验器不是真实性证明器"这一已被工程接受的边界族（scan-schemas.md:594 有原文声明），但该声明只写在 camp-series 链上，coverage 链没有等价声明，且后果远比 camp-series 严重**——这一条需要用户裁决是"补声明接受"还是"补机制"。

---

## 一、BREACH（3 条）

### BREACH-1 ｜ A-2b：coverage `slot_counts` 单字节篡改＋全自洽刷新 → 整个 SQD 缺陷修复机制被跳过

**攻击**：拿一个真实含 nonce 缺陷的案（探针实跑 verdict=`INCONCLUSIVE`），把 `slot_counts.bin.gz` 里那个缺陷 slot 的字节由 `2`（HEADER_ZERO_NONCE）改成 `3`（HEALTHY），然后像伪造者一样把从属证据一路刷新：coverage 自述 size/sha256 → `summary`/`candidate_slots`/`verdict` 按新 counts 重算 → `probe_id` 重算 → 代目录改名 → CURRENT 指针的 `probe_id` 与三个 inputs 的 path/size/sha256 全同步。

**预期**：应被拒（探针产物应有独立于自身的证据锚）。

**实际**：
- `validate_coverage` → `ok=True`，`reasons=[]`，重算 verdict = `NO_KNOWN_NONCE_OMISSION_DETECTED`
- 端到端对照（同一个案，同一份边）：
  - 诚实跑 → `gate_pass=False`，`coverage_effective_verdict=INCONCLUSIVE`，receipt `verdict=FAIL`
  - 伪造后跑 → **`gate_pass=True`，`coverage_effective_verdict=NO_KNOWN_NONCE_OMISSION_DETECTED`，receipt `verdict=PASS`**
  - 独立深验 `validate_reconcile_receipt_deep` → **`ok=True`，`reasons=[]`**

**裁定：BREACH**。一个字节 + 机械刷新，v6.52.0 整条"覆盖闸 → 缺陷确认 → 修复代 → 第五项"的链条被完整旁路，签出一份正式可消费、且能过独立深验的 `solana-reconcile/v4` PASS 收据，全链没有任何产物记录异常。

**性质与反证（必须一并读）**：这属于"控制案目录者可手写一组互相自洽的案内小件"这一族。工程自己在 `references/scan-schemas.md:594` 写过原文——"validator 是一致性校验器不是真实性证明器，F-12 已接受边界同族，此链上不再有可机器闭合的下一层"。而且设计者**在共享地图复用路径上是设了防的**：我把同样的伪造做进共享地图（counts 改 + canary 数组同步自洽），离线 `validate_shared_map` → `ok=True` 放行，但 `_load_known_map` 的**实时 recheck** 立刻抓住 → `fallback_reason="recheck-mismatch:210"`，退回全扫（见 A7c）。

**所以真正的问题不是"能不能防"，而是不对称**：复用别人的地图要实时重查 64+N 个 slot；本案自扫的 counts 一次落盘后再无任何复查。建议二选一（交用户裁决）：
1. 在 §14 coverage 契约段补一条与 §594 等价的诚实声明，把这条列入已接受残余，并在 SKILL/交付话术里写明"coverage verdict 只在案目录未被人为改动的前提下成立"；
2. 把 `--live-canary` 从 repair 段扩到 coverage 段：对 `HEALTHY` 采样若干 slot 实时重查（成本极低，抽 32~64 个即可），把"本案自扫"拉到与"复用地图"同一防护深度。

复现：`/private/tmp/opus_attack_v6520/work/attack_A.py`（向量 A2b）、`evidence/A2b_e2e.json`

---

### BREACH-2 ｜ B-10：`resolve_formal_cache` 浅验放行伪造 merged 边，5 个正式消费者照吃

**攻击**：拿一个真实 formal 修复代（离线 fixture 实跑产出，gid=`d3e8c855…`），直接改 `gen-<gid>/…repaired.jsonl.gz`（凭空注入一条 `CurveOwner → Attacker 1,000,000,000` 的边），然后同步刷新：repaired meta 的 `edge_logical_sha256`/`edge_rows`/`edge_file_sha256`/`edge_file_size` → bundle 的 `merged.edge_sha256`/`edge_logical_sha256`/`edge_rows`/`meta_sha256` → CURRENT 指针的 bundle sha256/size。

**预期**：`resolve_formal_cache` 是批 4 定的"Solana 消费端统一入口"，应当拒。

**实际**：
- `resolve_formal_cache` → **放行**
- `curve_cost.load_edges(MINT, case)` → **放行，且返回的 rows 里带着凭空注入的 10 亿枚**（它自查了 `meta.edge_logical_sha256` 与实际边一致——但那个字段已被同步刷新，自查形同虚设）
- `wave_scan.load_sol` → 同样放行（另一次实测，见 F3b）
- 只有 `validate_repair_bundle(deep=True)` 拒：`merged edges do not equal f(base,layer,map); merged row count identity violated; bundle repair edge count mismatch`

**同族确认**：B-3（签名重现）、B-4a（evidence 改内容）、B-4b（evidence 少文件＋manifest 同步）、B-5（改 census 不重算 gid）四条，**全部浅验放行、仅深验拦**。

**端到端边界**：换成"末态余额不变"的隐蔽注入（把 `ZERO→B 100` 改写成 `ZERO→Middleman 100` + `Middleman→B 100`，供给闭合与快照对账全不变），重跑 `cmd_reconcile` 仍被深验拒；先跑干净 reconcile 再篡改的 TOCTOU 打法，被 D-6 实证的 `edge_source_binding` 全等闸拦死。**所以 READY 不会放行**。

**裁定：BREACH**。按任务书字面（"产出正式可消费产物"）成立：`curve_costs.json`/`wave_scan_report.json` 都是带 binding 的正式产物，是 A3/A4 判断层的直接输入。但性质与 A-2b 不同——**这不是信任边界，是层间校验强度不一致**：深验代码已经写好了、就在同一个仓库里，只是浅验路径没调。

**建议**：`validate_cache_meta_v2` 在 repaired 分支补一条对 merged edge 的逻辑摘要独立重算（读边文件重算 `edge_logical_sha256` 与 meta 比对），或者干脆在 resolver 里对 repaired 代调一次 `deep=True`（代价是每个消费者多一次重建，可加缓存）。至少要让"5 个消费者吃到的边"和"reconcile 深验的边"是同一强度的判定。

复现：`work/attack_B.py`、`work/attack_B10.py`、`evidence/B10_results.json`、`evidence/B_results.json`

---

### BREACH-3 ｜ C-3c：`finalized_upper_slot` 可收窄，签出窗口不实的 PASS 收据

**攻击**：把修复代 merged meta 的 `finalized_upper_slot` 从 `19999` 改成 `19996`，同步 `bundle.merged.meta_sha256` 与 CURRENT 的 bundle 引用；再把 `holders_snapshot_meta.target.as_of_block` 一并改成 `19996`（三等式要求 `as_of_slot == cache upper == 快照 slot`，攻击者当然会一起改）；用 `--as-of-slot 19996` 跑 reconcile。

**预期**：应被拒——边文件里明明有 `slot=19999` 的边，超出声明窗口。

**实际**：
- `resolve_formal_cache` → 放行
- `cmd_reconcile` → **`gate_pass=True`，receipt `verdict=PASS`**，`collection_window={"from_slot":10000,"to_slot":19996}`，而 `max_edge_slot=19999`
- `validate_reconcile_receipt_deep` → **`ok=True`，`reasons=[]`**

**裁定：BREACH**（可修的检查缺项）。深验器逐项重算了边摘要、余额、快照对账、coverage、bundle，唯独**没有校验 `每条边的 slot ∈ [from_slot, finalized_upper_slot]`**。后果是收据的窗口字段可以与实物不符——这个字段是下游叙事（"分析截止到某时点"）和跨产物对锚的依据。

注：该缺口不能用来绕过 coverage 判定（`candidate_slots` 是按 counts 全长重算的，收窄窗口躲不开缺陷 slot——已验证）；`upper` 也只能改小不能改大（改大会触发 `slot_counts interval does not cover case interval`）。

**建议**：`validate_reconcile_receipt_deep` 与 `cmd_reconcile` 各补一行——边集的 `min(slot)/max(slot)` 必须落在 `[from_slot, finalized_upper_slot]` 内。

复现：`evidence/C3c_e2e.json`

---

## 二、WEAK（5 条）

| 编号 | 问题 | 实测 |
|---|---|---|
| W-1 | **symlink 防线不统一**：`resolve_formal_cache` 对"边文件是 symlink 指向案外"放行；`curve_cost`、`replay_edges`、`camp_series_provenance` 各自有 `is_symlink` 自查会拒，而 `wave_scan`、`audit_closed_accounts`、`flow_anomaly_scan`、`entity_source_trace` **没有** | 实跑 `wave_scan.load_sol` 跟随 symlink 读到案外文件、正常产出 `binding.cache_kind=repaired`。危害有限（内容仍受 bundle sha 约束），但破坏"案根自包含"假设，且同一份案不同消费者行为不一致。建议把检查上提到 resolver |
| W-2 | **AUTO_GATES 旧键别名旁路**：`--gate reconciliation_checks:…` 被正确拒（"禁止 declared 覆盖机器读数"），但 legacy 别名 `--gate reconciliation_four_checks:…` **被接受**，manifest 里多出一条 `source=declared` 的 gate，与 auto 机器读数并存 | verify 对 declared gate 只查 `verdict∈{PASS,OK}` 且 `exit_code==0`，**不重读产物**；auto 那条会重读。机器闸不依赖 declared 条目，所以没过闸，但产出了误导性双记录。建议禁止表把 `LEGACY_AUTO_GATE_ALIASES` 的键一并纳入 |
| W-3 | 浅验/深验强度断层（B-3/B-4a/B-4b/B-5 四条同族） | 见 BREACH-2，此处不重复计 |
| W-4 | 拒绝后留 `pending-<plan_digest>/` 半成品目录 | 见 B_e26、B_refuted 案。有 `ERROR-<hash>.json` 记录、不被 resolver 当 formal（只认 `gen-<gid>`），属可追溯的设计中断态；但目录名与错误文件对普通使用者是"脏状态"，建议在 STOPPED/ERROR 里写一句"pending 目录可安全删除" |
| W-5 | coverage 契约段（scan-schemas.md §14.1）缺少 §594 那样的诚实边界声明 | 见 BREACH-1 的性质讨论 |

---

## 三、DEFENDED 全表（逐向量：命令 / 预期 / 实际）

### A. coverage（基座：探针离线实跑的真实 `INCONCLUSIVE` 缺陷案，10000–19999）

| 向量 | 预期 | 实际拒绝理由 | 裁定 |
|---|---|---|---|
| A0 合法绿例 | 应通过 | `ok=True`，verdict=INCONCLUSIVE | ✅ 绿例 |
| A1 手改 verdict 为 NO_KNOWN | 拒 | `probe_id mismatch; coverage verdict mismatch` | DEFENDED |
| A1b 手改 verdict＋重算 probe_id＋改代目录名 | 拒 | `coverage verdict mismatch`（verdict 从 counts 重算，改不动） | DEFENDED |
| A2 slot_counts 改一字节（不刷哈希） | 拒 | `slot_counts size/sha256 mismatch` ＋ summary/candidate/verdict 三重不符 | DEFENDED |
| A2b 同上＋全自洽刷新 | 拒 | **放行** | **BREACH-1** |
| A-UNSCANNED 残留（counts 置 0）＋全自洽刷新 | 拒 | `slot_counts contains UNSCANNED; coverage verdict mismatch`（双防线） | DEFENDED |
| A3 scan_ranges 并集缺口 | 拒 | `scan_ranges union does not cover case interval; ledger successful union differs` | DEFENDED |
| A4 ledger 挖洞（删行＋同步 requests） | 拒 | `ledger successful union differs; ledger success_ranges_sha256 mismatch` | DEFENDED |
| A5 probe_id 直接改（不重算） | 拒 | `probe_id mismatch` | DEFENDED |
| A6 CURRENT 指向不存在的代 | 拒 | `coverage input unreadable: No such file` | DEFENDED |
| A7-green 合法复用共享地图 | 应通过 | `reused=true, fallback_reason=null` | ✅ 绿例 |
| A7a TTL 过期地图冒充 | 拒复用 | `fallback_reason="ttl-expired"` → 退回全扫 | DEFENDED |
| A7b endpoint 指纹不符 | 拒复用 | `fallback_reason="endpoint-fingerprint-changed"` | DEFENDED |
| A7c 地图 counts 伪造＋canary 自洽 | 拒复用 | 离线 `validate_shared_map` ok=True，但**实时 recheck 抓住**：`recheck-mismatch:210` | DEFENDED（关键反证） |

### B. 修复代（基座：离线 fixture 实跑产出的真实 formal 代）

| 向量 | 预期 | 实际 | 裁定 |
|---|---|---|---|
| B0 合法绿例 | 通过 | 浅验＋深验都 ok | ✅ 绿例 |
| B1 换 base 后消费旧代 | 拒 | 浅验 `repaired generation was invalidated by base recapture`；深验 `bundle base edge sha256 differs from current base` | DEFENDED |
| B2 census 外修复边（slot 越界） | 拒 | `bundle edge row identity mismatch` | DEFENDED |
| B3 签名重现（用 SQD 证据里已有的签名） | 拒 | 深验 `repair signature is present in SQD evidence; bundle gid mismatch`（浅验放行 → 见 BREACH-2） | DEFENDED（深）/ WEAK（浅） |
| B4a evidence 改内容不改 manifest | 拒 | 深验 `evidence size/sha256 mismatch` | 同上 |
| B4b evidence 少文件＋manifest 同步 | 拒 | 深验 `coverage state does not recompute for 19999` 等 7 条 | 同上 |
| B5 改 census 不重算 gid | 拒 | 深验 `resolution effective verdict mismatch; lacks confirmed census support; gid mismatch` | 同上 |
| B6 指针指向孤儿 gen | 拒 | 浅验 `CURRENT to merged meta binding invalid`；深验 `gid or generation directory mismatch` | DEFENDED |
| B7 CAS 漂移后再发布 | 拒 | rc=2，`repair bundle is unreadable: gen-beefbeefbeefbeef/bundle.json`，CURRENT 未被工具"顺手修好" | DEFENDED |
| B8 exploration/formal 互冒（两向） | 拒 | `formal bundle requires live reference and vice versa` | DEFENDED |
| B9 refuted-only 产代 | 不产代 | `{"status":"refuted-only"}`，**零 gen 目录、零 CURRENT** | DEFENDED |
| B-E26 前置一致性（SQD nonce 状态漂移） | 中止 | rc=2，`SQD coverage state changed before repair`，零 gen | DEFENDED |
| B10 直改 merged 边＋全同步 | 拒 | 浅验放行、消费者照吃；深验拒 | **BREACH-2** |
| B10-e2e 隐蔽中间人注入后重跑 reconcile | 拒 | 深验拒（末态不变也没用） | DEFENDED |

### C. reconcile v4 / 第五项（基座：真实 repaired 案，绿例 `gate_pass=True` 且深验 ok）

| 向量 | 预期 | 实际拒绝理由 | 裁定 |
|---|---|---|---|
| C0 合法绿例 | 通过 | `gate_pass=True`，深验 ok=True | ✅ 绿例 |
| C1 手拼 gate_pass=true 假 receipt | 拒 | `holders_owners size/sha256 mismatch` ＋ 4 条重算不符 | DEFENDED |
| C1b 手拼＋同步 inputs 哈希 | 拒 | `snapshot_supply_raw / snapshot_mismatch_count / gate_pass does not recompute` | DEFENDED |
| C2 receipt inputs 哈希与实物不符 | 拒 | `reconcile input coverage_map sha256 mismatch` | DEFENDED |
| C3 三等式：`--as-of-slot` 参数错位 | 拒 | `--as-of-slot 必须 == cache finalized_upper_slot` | DEFENDED |
| C3 三等式：快照 slot 错位 | 拒 | `gate_pass=False`（签出的是诚实的 FAIL 收据，深验 ok 表示"如实记录了 FAIL"，非攻击成功） | DEFENDED |
| C3c 三等式：cache upper 收窄＋全同步 | 拒 | **放行并签出 PASS** | **BREACH-3** |
| C4 base 模式带 repair 三键 | 拒 | `conditional input key set mismatch` ＋ verdict/exit_code 三元不符 | DEFENDED |
| C5 coverage 候选未被代 census 覆盖 | 拒 | `plan candidates lack census disposition` ＋ resolution sha 不符 | DEFENDED |

### D. wrapper v3 / READY 硬闸（基座：`build_solana_case` 真实 new-analysis 端到端案，`gate.run` 零 error）

> 方法论纠错：第一轮用 `copytree` 复制案根做攻击，结果多数拒绝的**真实原因**是 `supply_receipt.json` 里的绝对路径复制后逃逸案根，而非我打的那条防线——那是假阳性防御。第二轮改为**就地篡改＋逐字节还原**，并同步 `dormant_warehouse_audit.universe_ref.sha256`、`reconciliation_report.checks.*.receipt.sha256` 等一切从属哈希，确保每次拒绝确实撞在目标防线上；每轮结束还原后复验基线 `errors=[]`。下表是第二轮结果。

| 向量 | 预期 | 实际拒绝理由（首条） | 裁定 |
|---|---|---|---|
| D0 合法绿例 | 通过 | `errors=[]` | ✅ 绿例 |
| D1 wrapper 降 v2 旧壳 | 拒 | `reconciliation-report/v2 已 fail-closed` | DEFENDED |
| D2 Solana 案缺第五项 | 拒 | `checks 必须按顺序恰为 (supply,balance,supply_truth,time,exact_reconcile)` | DEFENDED |
| D2b 第五项降 v3 旧 schema | 拒 | `Solana exact_reconcile 必须重跑 replay_edges.py reconcile 生成 v4 收据` | DEFENDED |
| D2c 第五项事实手改＋报 PASS | 拒 | `独立深验失败: reconcile edge digest/count mismatch` | DEFENDED |
| D3 `--reseal` 用于 Solana | 拒 | `EVM 旧 wrapper 必须含四份 receipt 引用` | DEFENDED |
| D3b `--reseal` 洗成 4 项 EVM 形状 | 拒 | `--reseal 仅允许 EVM 家族` | DEFENDED |
| D4a AUTO_GATES 现役键 declared 覆盖 | 拒 | `--gate reconciliation_checks 已有 AUTO_GATES 适配，禁止 declared 覆盖机器读数` | DEFENDED |
| D4b AUTO_GATES 旧键别名 declared | 拒 | **被接受**（rc=0，注入 declared gate） | **WEAK-2** |
| D5 手改 handoff manifest 报 READY | 拒 | `A5 seal 分布终态不可重验`（seal 绑定链拦） | DEFENDED |
| D5b 手改后跑 `handoff verify` | 拒 | `READY scope.chains 为空；READY scope.contract 为空` | DEFENDED |
| D6 派生产物 binding 不全等（＋同步 universe_ref） | 拒 | `Solana 派生产物 wave_scan_report.json.edge_source_binding 与 exact_reconcile 不全等` | DEFENDED |
| D6b 派生产物删 binding 字段 | 拒 | 同上 ＋ `wave_scan 报告缺 formal scan_universe 逐址全集` | DEFENDED |
| D7 EVM 语义 wave（v4/parquet 参数）混入 Solana | 拒 | 同 D6 ＋ schema 须 wave-scan/v5 | DEFENDED |
| D8 凭空新增 binding 不全等的 `curve_costs.json` 并挂进 data_map | 拒 | `curve_costs.json.edge_source_binding 与 exact_reconcile 不全等` | DEFENDED |

### E. resolver / 路径

| 向量 | 预期 | 实际 | 裁定 |
|---|---|---|---|
| E0 合法绿例 | 通过 | `kind=repaired, gid=055c8715fe301281` | ✅ 绿例 |
| E1 案外复制 base＋meta 后显式传入 | 拒 | `CURRENT exists; formal resolver must not fall back to base` | DEFENDED |
| E2 案根 symlink | 拒 | `case_root itself must not be a symlink` | DEFENDED |
| E2b merged 边文件本身是 symlink | 拒 | resolver **放行**；`curve_cost` 拒（`边文件缺失或为符号链接`）；`wave_scan` **放行** | WEAK-1 |
| E3 meta_path 非正式集合路径（案内另存） | 拒 | `repaired meta is outside CURRENT-selected formal path` | DEFENDED |
| E4 CURRENT 有效时直接消费 base | 拒 | `CURRENT exists; must not fall back to base`；显式传 base meta 给 reconcile → `reconcile cache meta 不是 resolver 当前选择` | DEFENDED |

### F. 脱敏

伪造 402 配额响应夹具，`--reference-rpc` 传入含假 key 的 Helius 风格 URL（`https://mainnet.helius-rpc.com/?api-key=abcd1234-dead-beef-cafe-0123456789ab`）：

| 向量 | 预期 | 实际 | 裁定 |
|---|---|---|---|
| F1 修复段 402 停工 | 无 key 明文 | rc=3；`STOPPED.json` 只含 `{reason:"reference-quota", cursor, plan_digest, completed_slots}`；扫描 pending 目录全部文件 ＋ stdout/stderr → **零命中** `api-key=` 与 key 字面 | DEFENDED |
| F2 探针段 402 停工 | 无 key 明文 | rc=2；产物 `ledger.jsonl` / `resume_state.json` / `slot_counts.bin.gz` → **零命中**；stderr 仅 `{"status":"UNSCANNED","gaps":[[200,263]]}` | DEFENDED |

---

## 四、未验项（如实声明）

1. `--live-canary`（repair verify 段）：需真实 Solana RPC，按任务书不硬试 → **未验**
2. `handoff_manifest generate --status READY` 全链：该夹具缺 READY 必备契约件（PARTIAL 可跑通、READY 报缺件），D4b 的 declared gate 只在 PARTIAL 态验到 → READY 态下 declared gate 的最终影响**未验**
3. EVM 家族的完整 READY 端到端：本次只在 Solana 案上打 wrapper/第五项/binding，EVM 侧仅验了 `--reseal` 家族闸

---

## 五、给用户的三个决策点（大白话）

1. **A-2b 怎么办？** 现状是：任何能改案目录文件的人（包括手滑的自己、或某轮"修一下让它过"的施工方），改 1 个字节 + 跑一段几十行的刷新脚本，就能让"这个币的链上数据有缺口"变成"数据完整"，而所有闸、所有独立验证器都会说 OK。
   - 选项 A（省事）：承认这是已知边界，在文档里写明白，交付时如实说"结论建立在案目录没被人为改过的前提上"。风险：将来谁真这么干了，事后查不出来。
   - 选项 B（加机制）：coverage 也加实时抽查（像共享地图那样抽 64 个 slot 重问一次 SQD）。成本：每次分析多几十个请求、几秒钟。收益：这条路彻底堵死。
   - 我的建议：**选 B**。共享地图那条路已经证明这招管用、代价极小，而本案自扫反而不查，是明显的不对称。

2. **B-10 是不是必须现在修？** 我认为是。深验代码已经写好了，只是消费者走的那条路没调它。后果是报告里的成本曲线、波次、实体流转这些图和数字，可能建立在被改过的边上，而 reconcile 那道闸只在最后才发现。修法很轻：resolver 对 repaired 代补一次边摘要独立重算。

3. **C-3c 与两条 WEAK 属于小补丁**：各加一两行校验（边 slot 落在声明窗口内、别名键纳入禁止表、symlink 检查上提到 resolver）。

---

## 六、复现资产

```
/private/tmp/opus_attack_v6520/
├── VERDICT.md              ← 本报告
├── work/                   ← 攻击脚本（harness.py + attack_A/A7/B/B2/B10/C/D/D2/D3/E/F.py）
├── evidence/               ← 18 份逐向量 JSON 结果
├── green_repair/ A_base/ C_base/ D_base/ …  ← 各类基座与被攻击副本
```

结审复核：`git rev-parse HEAD` = `94314de99cbc…`（未变），`git status --porcelain` 空。
