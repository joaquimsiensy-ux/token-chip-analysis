# v6.52.0 攻击型盲审 verdict（SQD 覆盖闸＋修复生产者窄门）

- 被审对象：`/Users/uravvv/.claude/skills/token-chip-analysis`，分支 `fix/sqd-gap-v6520`，HEAD `94314de`
- 审查角色：攻击型验收员（红队），只读攻击＋ /private/tmp 夹具
- 审查日期：2026-08-23
- 仓库改动情况：**零改动**（审后 `git status --short` 为空，HEAD 仍为 94314de；未 commit、未联网）

---

## 一、总判

# BLOCK

判据：任一 BREACH ⇒ BLOCK。本轮实跑 **3 个 BREACH**（B-09 / B-10 / B-11，同一根因），
其余 50 个攻击向量全部 DEFENDED，9 个合法绿例全部未被误杀，1 项（联网 live-canary）未验。

---

## 二、分向量统计

| 类 | 攻击面 | DEFENDED | WEAK | BREACH | 未验 | 绿例 | 最严重一条 |
|---|---|---:|---:|---:|---:|---:|---|
| A | coverage 闸 | 13 | 0 | 0 | 0 | 3 | 全自洽 reseal 也被 verdict/summary/candidate_slots 重算逐项打回 |
| B | 修复代窄门 | 11 | 0 | **3** | 1 | 2 | **coverage 候选集之外的伪造 formal 代可注入任意假边并全程过闸** |
| C | reconcile v4／第五项 | 5 | 0 | 0 | 0 | 1 | 手拼 PASS receipt 被独立重放逐字段打回 |
| D | wrapper v3／READY | 14 | 0 | 0 | 0 | 2 | v2 wrapper、缺第五项、预置 receipt、非白名单生产者一律 fail-closed |
| E | resolver／路径 | 5 | 0 | 0 | 0 | 1 | 删修复指针退回 base 只能落 FAIL receipt（gate false/exit 2） |
| F | 脱敏 | 2 | 0 | 0 | 0 | — | 402 停工路径 stdout/stderr/全部产物零 key 明文 |
| 合计 | | **50** | 0 | **3** | 1 | 9 | |

---

## 三、BREACH 详述（P0）

### 3.1 一句话

**修复代的 formal 严格校验只覆盖 coverage 候选集内的 slot；候选集之外的 slot 完全无闸。**
攻击者可以在任意 Solana 案（含 coverage 判定为“完全干净”的案）里，构造一个自称 formal、
零 live 请求记录的修复代，往任意 slot 注入凭空捏造的边，
并顺利通过 **独立 validator → 正式 resolver → 受控对账第五项 → 派生绑定闸 → wave 正式语义闸** 全链。

### 3.2 实证（三次独立复现）

| 编号 | 场景 | 结果 |
|---|---|---|
| B-09 | `--blocks-cache` 产的 **exploration 代**（本地证据缓存，非 live），手工改 `mode=formal`＋`reference.source=live`，重算 gid、改目录名、手写 CURRENT 指针 | `validate_repair_bundle_deep` **ok=True（零 reasons）**；`resolve_formal_cache` **ACCEPTED kind=repaired** |
| B-10 | coverage 干净（`verdict=NO_KNOWN_NONCE_OMISSION_DETECTED`、`candidate_slots=[]`）的案，手工伪造 formal 代，注入 `ZERO → EVILWALLET 1,000,000` 铸造边 | validator ok=True；resolver ACCEPTED；`replay_edges reconcile` **exit 0**，产出 `solana-reconcile/v4`：`gate_pass=true / verdict=PASS / minted_raw=1,002,000`（真实供应 2,000） |
| B-11 | 已被正常修复的案（coverage 候选＝{19999}），在**候选集之外**的 slot 15000 追加伪造边并自洽重封 | 同上：validator ok、resolver ACCEPTED、reconcile PASS、`minted_raw=1,002,000` |
| B-13 | 上述伪造代的 `edge_source_binding` 进入下游 | `validate_solana_derived_bindings` **ACCEPTED**；`wave_contract.has_formal_wave_semantics` **True** ⇒ 可直达 READY 链，下游无补救闸 |

复现脚本（可直接重跑）：
- `/private/tmp/opus_review_v6520/attack_B2.py`（B-09）
- `/private/tmp/opus_review_v6520/attack_B10.py`（B-10）
- `/private/tmp/opus_review_v6520/attack_B11.py`（B-11）
- `/private/tmp/opus_review_v6520/attack_B12.py`（B-13 下游穿透）

伪造代的“体检报告”（B-10 实测值，全部被放行）：
- `mode=formal`、`reference.source=live`，但 `rpc_ledger.requests=0`（**一条 live 请求都没有**）
- `census[0].coverage_state="HEALTHY"` 却 `result="confirmed_nonce_defect"`（**自相矛盾**）
- `census[0].sqd_nonce_count_at_repair=null`（这正是契约里 exploration 代的指纹，formal 下本应拒）
- `coverage_map.verdict="NO_KNOWN_NONCE_OMISSION_DETECTED"` 与 `resolution.effective_verdict="DEFECTS_CONFIRMED"` **直接冲突**
- 以上五处矛盾，validator 一处都没报

### 3.3 根因（代码定位）

`scripts/lib/solana_exact_validate.py::validate_repair_bundle_deep`：

1. formal 的全部严格校验写在 `for slot in sorted(all_candidates):` 循环体内——
   包括 `_repair_state_matches`（coverage 状态语义）、四个证据 sha 字段校验、
   `repair ledger/evidence resume identity`（ledger 与证据绑定）、
   以及 `exploration cache repair must use null nonce recheck` 这条 exploration 指纹拦截。
2. `all_candidates = set(plan_candidates["coverage"]) | set(plan_candidates["beta"])`，
   而 `plan_candidates["coverage"]` 被强制等于 `coverage_map.candidate_slots`。
   **coverage 干净 ⇒ all_candidates 为空 ⇒ 整个循环一次都不执行。**
3. census 只被要求 `all_candidates ⊆ census_slots`（`plan candidates lack census disposition`），
   **反向不检查**：census 里可以塞任意 slot 并自称 `confirmed_*`。
4. 修复边的唯一准入条件是 `slot in confirmed`，而 `confirmed` 完全来自 census 自报。
5. `rpc_ledger` 逐行契约校验写在 `if ledger_rows:` 里，只有 header 行时 `ledger_rows[1:]` 为空，
   `requests==len(ledger_rows)-1==0` 自洽通过——**零 live 请求可以自称 live**。
6. `mode=formal ⇔ reference.source=live` 只是两个自报字段的等价性检查，没有任何实物锚。

对照佐证：同样的伪造边**落在 coverage 候选内**（B-02）会被干净拒（`repair transaction lacks confirmed census support`），
说明设计意图确实要拦这类伪造，只是闸被挂在了“候选集”这把钥匙上，候选集外是敞开的。

### 3.4 威胁模型说明（为什么算 BREACH 而不是“威胁模型外”）

整套 v6.52.0 机制（内容寻址 gid、pending→gen 原子改名、锁内 CAS、生产者白名单、
独立 validator、live canary、binding 全等）存在的前提就是**假设案根内容可被伪造**——
否则这些闸没有意义。A 类 13 个向量、C/D/E 全部向量都是在“攻击者可写案根”前提下被成功拦住的。
同一前提下 B 类出现放行，是闸本身的缺口，不是前提失效。

### 3.5 修复建议（按优先级）

1. **把 formal 严格校验的遍历主键从“coverage 候选集”换成“实际产生修复边的 slot 集合”**：
   `repair_slots = {census 中 result.startswith("confirmed_") 的 slot} ∪ {repair_layer 各行的 slot}`，
   对 `repair_slots` 逐个执行现有 formal 检查（状态语义、四证据 sha、ledger/evidence 身份绑定）。
2. **加反向包含约束**：`confirmed_slots ⊆ all_candidates`；
   并规定 `coverage_map.verdict == NO_KNOWN_NONCE_OMISSION_DETECTED` 时
   `confirmed census 行数必须为 0 且 repair_layer.edges 必须为 0`（干净 coverage 不该有修复代）。
3. **formal 要求 ledger 实物**：`mode=formal` 时 `rpc_ledger.requests ≥ len(repair_slots) > 0`，
   每个修复 slot 必须有 `params_digest == _repair_getblock_params_digest(slot)` 的 getBlock 行。
4. **exploration 指纹前移**：`census[*].sqd_nonce_count_at_repair is None` 在 `mode=formal` 下一律拒，
   不再依赖候选循环触达（这条能单独封死 B-09 的提升路径）。
5. **resolver 侧兜底**：`resolve_formal_cache` 采纳 repaired 代前，
   复核 `bundle.coverage.probe_id == 当前 CURRENT coverage 的 probe_id`
   且该 coverage 的 `candidate_slots` 非空。
6. 回归测试补三条先红：B-09/B-10/B-11 的夹具可直接移植为 expected-red 用例。

### 3.6 现有测试为何没抓到

审后实跑仓库自带 `scripts/tests/test_sqd_gap_repair.py`：**EXIT=0 全绿**。
测试里已存在 `validate_census_support` / `validate_current_candidates` 符号，
即设计者意识到需要“census 支持”和“当前候选”校验，但用例只覆盖了**候选集内**的越界场景
（对应我这边被防住的 B-02），没有构造“候选集外/干净 coverage”的反例。属于典型的等价类盲区。

---

## 四、逐向量记录

说明：`rc` 为 `replay_edges.py reconcile` 子进程退出码；`receipt_written=False` 表示未留脏产物。

### A. coverage 闸（13 向量，全 DEFENDED）

| 编号 | 攻击 | 预期 | 实际 | 裁定 |
|---|---|---|---|---|
| A-01 | coverage `verdict` 手改为 NO_KNOWN…（不重算 probe_id） | 拒 | rc=2 `coverage_map size mismatch; sha256 mismatch`，无脏 receipt | DEFENDED |
| A-02 | 真实候选存在但 verdict/summary 伪报干净（**全自洽 reseal**：重算 probe_id、改目录名、重建 CURRENT） | 拒 | rc=2 `coverage summary mismatch; candidate_slots mismatch; coverage verdict mismatch` | DEFENDED |
| A-03 | `slot_counts.bin.gz` 篡改一字节（sha 不同步） | 拒 | rc=2 `slot_counts size/sha256 mismatch` ＋三项重算不符 | DEFENDED |
| A-04 | repaired 案伪造“干净”coverage 绕过修复义务（缺陷字节 2→3，全自洽 reseal） | 拒 | rc=2 `coverage state does not recompute for 19999; repair coverage state semantics mismatch` | DEFENDED |
| A-05 | UNSCANNED(0) 残留＋自洽 reseal | 拒 | rc=2 `slot_counts contains UNSCANNED` | DEFENDED |
| A-06 | ledger 挖洞（删一段成功记录）＋自洽 reseal | 拒 | rc=2 `ledger seq has hole; ledger successful union differs from scan_ranges union` | DEFENDED |
| A-07 | scan_ranges 并集留缺口＋自洽 reseal | 拒 | rc=2 `scan_ranges union does not cover case interval` | DEFENDED |
| A-08 | probe_id 不重算直接改（pointer 同步） | 拒 | rc=2 `probe_id mismatch` | DEFENDED |
| A-09 | CURRENT 指向不存在的 probe 目录 | 拒 | rc=2 `coverage_map 文件缺失或逃逸案根` | DEFENDED |
| A-10a | TTL 过期共享地图冒充复用 | 不得复用 | rc=0 但 `modes=["full"]`、`reused_ranges=[]`（回退全扫） | DEFENDED |
| A-10b | endpoint 指纹不符共享地图 | 不得复用 | 同上，回退全扫 | DEFENDED |
| A-10c | 共享地图 counts 实物被篡改（sha 不符） | 不得复用 | 同上，`shared_map.version=null` | DEFENDED |
| A-10d | 共享地图声称健康但真实 SQD 全零 nonce（canary 说谎） | 抓出 | 未复用，`verdict=INCONCLUSIVE` | DEFENDED |
| A-GREEN / A-GREEN2 / A-10-GREEN | 未篡改 base 案、未篡改 repaired 案、合法新鲜共享地图 | 通过 | rc=0 / rc=0 / 复用成功且 `map-reuse` 出现 | 绿例通过 |

### B. 修复代窄门（11 DEFENDED / 3 BREACH / 1 未验）

| 编号 | 攻击 | 预期 | 实际 | 裁定 |
|---|---|---|---|---|
| B-01 | 换 base（追加边并同步 base meta）后仍消费旧代 | 拒 | rc=2 `repaired generation was invalidated by base recapture`；validator `bundle base edge sha256 differs from current base` | DEFENDED |
| B-02 | 修复边落在 census 外 slot（自洽重封 gid/指针） | 拒 | rc=2 `repair transaction lacks confirmed census support` | DEFENDED |
| B-03 | census 内容改但 gid 不重算（各 sha 全同步） | 拒 | rc=2 `bundle gid or generation directory mismatch` | DEFENDED |
| B-04a | bundle 证据少一个文件 | 拒 | rc=2 `evidence file missing` ＋六项连锁不符 | DEFENDED |
| B-04b | `repair_layer.jsonl` 实物改动（bundle sha 不同步） | 拒 | rc=2 `bundle repair_layer reference mismatch` | DEFENDED |
| B-05 | CURRENT 指向孤儿 gen（目录改名 `pending-`） | 拒 | rc=2 `repair bundle is unreadable` | DEFENDED |
| B-06 | CURRENT.gid 指向不存在的代 | 拒 | rc=2 `repair bundle is unreadable` | DEFENDED |
| B-07 | 并发双代：`supersedes≠CURRENT.gid` 仍试切 CAS | 抛错且 CURRENT 不变 | `RuntimeError: repair pointer CAS failed`，`CURRENT_unchanged=True` | DEFENDED |
| B-08a | 前置一致性：repair 时 SQD nonce 计数与 coverage 状态不一致 | 中止 | `sqd gap repair failed: SQD coverage state changed before repair`，rc=2，零代零指针 | DEFENDED |
| B-08b | 签名重现：待修复签名其实已在 SQD census 中 | refuted-only | rc=0，`status=refuted-only`，**不产代、不发指针** | DEFENDED |
| B-12 | live-canary 离线夹具：参考源与证据不符 | 抓出 | 一致→ok；不符→`live canary differs at slot 19999` | DEFENDED（联网 canary＝未验） |
| **B-09** | exploration 代改 `mode=formal`＋`source=live`，重算 gid 后手工发指针 | 拒 | **validator ok=True；resolver ACCEPTED kind=repaired** | **BREACH** |
| **B-10** | 干净 coverage 案上手工伪造 formal 代，注入 ZERO→EVILWALLET 1,000,000 | 拒 | **validator ok；resolver ACCEPTED；reconcile exit 0；gate_pass=true；minted_raw=1,002,000** | **BREACH** |
| **B-11** | 已修复案的候选集**之外**追加伪造边并自洽重封 | 拒 | **同上全过；minted_raw=1,002,000** | **BREACH** |
| B-13 | 伪造代 binding 进入下游派生绑定闸与 wave 语义闸 | 应被拦 | `validate_solana_derived_bindings` ACCEPTED；`has_formal_wave_semantics` True | BREACH 佐证（下游无补救） |
| B-GREEN / B-GREEN2 | 未篡改 formal 代 / exploration 代原生行为 | 通过 | rc=0 且 validator ok / 产代但不发 CURRENT 指针 | 绿例通过 |

### C. reconcile v4／第五项（5 向量，全 DEFENDED）

| 编号 | 攻击 | 预期 | 实际 | 裁定 |
|---|---|---|---|---|
| C-01 | 手拼 `gate_pass=true` 假 receipt（快照与重放不符但声称 0 mismatch，inputs 哈希已同步） | 拒 | 深验拒：`snapshot_supply_raw / snapshot_mismatch_count does not recompute; gate_pass does not recompute` | DEFENDED |
| C-02 | receipt inputs 哈希与实物不符 | 拒 | `reconcile input holders_owners sha256 mismatch` ＋六项连锁 | DEFENDED |
| C-03 | `--as-of-slot` 三等式破坏（参数≠快照；快照＝参数但≠cache upper） | 拒 | 两种均 rc=2 `--as-of-slot 必须 == cache finalized_upper_slot`，不落 receipt | DEFENDED |
| C-04 | base 模式带 repair 三键（双向：repaired 谎报 base／base 加三键） | 拒 | 均 `reconcile conditional input key set mismatch` | DEFENDED |
| C-05 | coverage 候选未被代 census 覆盖仍试图 PASS | 拒 | rc=2 `plan candidates lack census disposition` | DEFENDED |
| C-GREEN | 未篡改 repaired/base receipt 深验 | 通过 | 均 ok，零 reasons | 绿例通过 |

### D. wrapper v3／READY（14 向量，全 DEFENDED）

| 编号 | 攻击 | 预期 | 实际 | 裁定 |
|---|---|---|---|---|
| D-01 | v2 旧 wrapper 冒充过闸 | 拒 | `reconciliation-report/v2 已 fail-closed` | DEFENDED |
| D-02 | Solana wrapper 缺第五项（手拼 4 键） | 拒 | `checks 必须按顺序恰为 (…, exact_reconcile)` | DEFENDED |
| D-02b | runner 用 4 键 spec 跑 Solana | 拒 | rc=2，wrapper 落 `verdict=FAIL`，消费端拒 | DEFENDED |
| D-03 | `--reseal` 用于 Solana wrapper | 拒 | rc=2 `EVM 旧 wrapper 必须含四份 receipt 引用` | DEFENDED |
| D-04 | 旧键 `reconciliation_four_checks` 声明绕过 AUTO_GATES | 拒 | rc=2，READY 深验直接失败，未生成 manifest | DEFENDED |
| D-04b | 现行键 `reconciliation_checks` 声明覆盖机器读数 | 拒 | rc=2 | DEFENDED |
| D-05 | 改动已登记产物后 verify | 拒 | rc=2 `哈希/大小漂移: wave_scan_report.json` | DEFENDED |
| D-05（续） | 再把 manifest 内所有哈希重算成新值后 verify | 拒 | rc=2（自封哈希不足以过闸，密封独立） | DEFENDED |
| D-05b | EVM 案用 v2 wrapper 走 READY | 拒 | rc=2，未生成 manifest | DEFENDED |
| D-05c | BLOCKED manifest 手改 `status=READY` 后 verify | 拒 | rc=2 `READY scope.chains 为空／scope.contract 为空` | DEFENDED |
| D-06 | wave 报告 binding 与 exact receipt 不全等 | 拒 | `edge_source_binding 与 exact_reconcile 不全等` | DEFENDED |
| D-06b | closed_audit 派生产物 binding 不全等 | 拒 | 同上（data_map 登记的派生件同样深验） | DEFENDED |
| D-07 | EVM 语义 wave 携带 binding／Solana wave 缺 binding | 均判非正式 | `False / False`，合法 Solana wave＝True | DEFENDED |
| D-08 | 预置手拼 exact receipt 让 runner 采信 | 拒 | `check exact_reconcile receipt pre-exists` | DEFENDED |
| D-08b | 非白名单脚本冒充 exact 生产者 | 拒 | `producer is not whitelisted: 'scripts/solana/curve_cost.py'` | DEFENDED |
| D-GREEN / D-GREEN2 | 合法 binding 全等＋wave 正式语义 / EVM 合法 READY generate＋verify | 通过 | True / generate rc=0、verify rc=0 | 绿例通过 |

### E. resolver／路径（5 向量，全 DEFENDED）

| 编号 | 攻击 | 预期 | 实际 | 裁定 |
|---|---|---|---|---|
| E-01 | base 边＋meta 复制到案内别目录后显式传入 wave/flow/entity | 拒 | 三入口均 `SystemExit 2`（`--edges-sol glob 结果必须恰为 resolver 解析出的唯一边文件`） | DEFENDED |
| E-02 | 案根本身是 symlink | 拒 | rc=2 `case_root itself must not be a symlink`，不落 receipt | DEFENDED |
| E-03 | meta_path 指向正式路径集合外（案外副本） | 拒 | `CURRENT exists; formal resolver must not fall back to base` | DEFENDED |
| E-04 | 删除 repair CURRENT 指针，退回未修复 base 边过闸 | 拒 | resolver 回落 base，但 reconcile `coverage_effective_verdict=INCONCLUSIVE`、`gate_pass=false`、`verdict=FAIL`、exit 2；落的是 FAIL receipt（符合三元互洽契约，wrapper 不采信） | DEFENDED |
| E-05 | 案内 symlink 指向案外 / `../` 逃逸 | 拒 | `artifact path contains symlink` / `escapes case root` | DEFENDED |
| E-GREEN | 合法案 resolver 解析并被消费端使用 | 通过 | `kind=repaired gid=b61ec3533d950584`，curve 消费 4 行，binding kind=repaired | 绿例通过 |

### F. 脱敏（2 向量，全 DEFENDED）

| 编号 | 攻击 | 预期 | 实际 | 裁定 |
|---|---|---|---|---|
| F-01 | 修复生产者遇 Helius 402 配额停工，`--reference-rpc` 内嵌 key | 无明文 | rc=3（配额停工专用码），STOPPED.json 落于 `pending-<plan_digest>/`，stdout/stderr/全案文件**零 key 明文**；停工报文只含 `completed_slots/cursor/plan_digest/reason=reference-quota` | DEFENDED |
| F-02 | 覆盖探针 `--reference-rpc` 内嵌 key | 无明文 | rc=0，stdout/stderr/全案文件零 key 明文 | DEFENDED |

---

## 五、未验项

| 项 | 原因 |
|---|---|
| `--live-canary` 真实联网核对 | 任务书禁止联网。已用离线夹具替代验证 canary 判定逻辑本身有效（B-12）：证据被改即报 `live canary differs at slot`。**但需注意：canary 仅在显式传入时启用，reconcile/resolver 默认路径不触发，且只覆盖 census 前 N 个 slot——不能作为 3.5 节修复项的替代。** |

---

## 六、复现材料

| 内容 | 路径 |
|---|---|
| 夹具库（造案／造代／自洽重封） | `/private/tmp/opus_review_v6520/fixtures/harness.py`、`/private/tmp/opus_review_v6520/fixtures/reseal.py` |
| A 类攻击 | `/private/tmp/opus_review_v6520/attack_A.py`、`attack_A10.py` |
| B 类攻击 | `attack_B.py`、`attack_B2.py`、`attack_B10.py`、`attack_B11.py`、`attack_B12.py` |
| C 类攻击 | `attack_C.py` |
| D 类攻击 | `attack_D.py`、`attack_D2.py`、`attack_D3.py`、`attack_D4.py` |
| E／F 类攻击 | `attack_EF.py` |
| 结果 JSON | `/private/tmp/opus_review_v6520/logs/*_results.json` |
| 合法绿例案根 | `/private/tmp/opus_review_v6520/green_base/case`（base 模式）、`green_repaired/case`（repaired 模式） |
| BREACH 案根 | `work_B10/case`、`work_B11/case`、`work_B2/b09/case` |
| 仓库自带测试结果 | `/private/tmp/opus_review_v6520/logs/repo_test_gap_repair.log`（EXIT=0 全绿）、`baseline_reconcile_v4.log`（EXIT=0） |

---

## 七、结论

覆盖闸（A）、对账 v4 与第五项（C）、wrapper／READY 硬闸（D）、resolver 与路径围栏（E）、脱敏（F）
这五面在 50 个攻击向量下**一处未破**，且 9 个合法绿例无一被误杀——工程质量很高。

问题集中在修复代窄门（B）的一处等价类盲区：**严格校验的遍历主键选错了**。
把主键从“coverage 候选集”换成“实际产生修复边的 slot 集合”，再补上反向包含与 ledger 实物要求，
即可关闭这三个 BREACH。修复前不建议合并 main。

/private/tmp/opus_review_v6520/verdict.md
