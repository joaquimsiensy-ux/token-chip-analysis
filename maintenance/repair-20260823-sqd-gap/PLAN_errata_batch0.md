# PLAN.md 勘误与补全注记（批 0，2026-08-23；PLAN.md 正文原文保留、逐字不改）

> 来源：codex 批 0 落盘报告 `batch0_done.md` §6「发现项」7 条（第 8 条为自指哈希，见 `batch0_acceptance.md`）。
> 行号：左＝PLAN.md 行号（含 11 行 frontmatter），括号内＝原计划文件行号。Fable 逐条核对原文属实后裁定如下；**本注记与 PLAN.md 冲突处以本注记为准**，批 1 起的工单一律引用本注记。

| # | 发现（codex） | Fable 裁定（对施工有约束力） |
|---|---|---|
| E1 | L153(142) 4.2.0 规定 evidence/*、evidence_manifest、merged 边文件**不含** `plan_digest`；L173(162) 发布协议步骤①却概括写"各文件含 plan_digest" | **以 4.2.0 清单为准**。步骤①应读作："按依赖图依次写 evidence/evidence_manifest/resolution/layer/map/merged 边/merged meta——其中 resolution、layer header、map header、merged meta 含 `plan_digest`；所有文件一律不含 gid/bundle 哈希"。`canonicalization.json` 已按清单记录，`publish_protocol.json` 的 notes 引用本条。 |
| E2 | L114(103) r5→r6 摘要把"数组严格递增唯一且 ⊂[from,to]"列为 getBlocks `complete` 机械条件；L160(149) 4.2.1 的离线合取式不含这两项，改为"生产时断言并记录、`--live-canary` 可复核" | **以 4.2.1 为准**（r7 定稿口径）。离线 validator 的 `complete` 合取式＝response_ok ∧ (to−from+1) ≤ 500,000 ∧ reference_head_at_check ≥ to ∧ 位图该段长度 == to−from+1 ∧ popcount == count ∧ count ≤ 区间长度；`array_monotonic_unique` 为生产时断言字段（必须为 true，否则该段 `response_ok` 置 false），validator 只检查其为 true 且可被 `--live-canary` 抽检。L114 为历史变更摘要，不再作为规范引用。 |
| E3 | L163(152) 只说探针 `CURRENT.json` 为 kernel 收据（`sqd-solana-coverage-pointer/v1`，PASS），未逐字段 | **补全**：与 repair pointer 同构——`{schema:"sqd-solana-coverage-pointer/v1", target{chain:"solana", token:<mint>, as_of_block:<coverage_map.slot_counts.to_slot>}, mode:"formal", verdict:"PASS", exit_code:0, producer{path,sha256}, inputs{coverage_map{path,size,sha256}, slot_counts{path,size,sha256}, ledger{path,size,sha256}, blocks_bitmap{path,size,sha256}|省略}, probe_id, published_at}`；`inputs` 路径案根相对（`data/sqd_coverage/<probe_id>/…`）；`blocks_bitmap` 仅在 `skipped_confirmation` 非 null 时出现（省略而非 null）。锁内 `publish_overwrite`（PASS→PASS）发布；resolver 校验 `inputs.coverage_map.sha256 == sha256(文件)` 且 `probe_id` 重算一致。`sqd-solana-coverage-pointer_v1.json` 草案按本条在批 1 冻结时补齐。 |
| E4 | L186(175) 合并缓存 meta"与 base v4 meta 同契约"，本计划未列 base v4 meta 完整字段表 | **以现役实现为准**：继承字段集＝`fetch_sqd_transfers_v2.py` 当前写出的 v4 meta 全部字段（以 main=f06078e 的实现为冻结基线）∪ `sqd_cache_identity.validate_cache_meta` 必检字段；差异字段按 4.2.6。批 3 工单必须附"base v4 meta 字段表（从实现抄录）＋ repaired meta 差异表"，契约草案在批 1 冻结时补一条 note 指向本条。 |
| E5 | L192(181) `solana-reconcile/v4`"在 v3 字段全保留基础上"，本计划未列 v3 完整字段表 | **以现役实现为准**：v3 字段集＝`replay_edges.py cmd_reconcile`（main=f06078e）当前写出的全部键；v4＝v3 全部键 ＋ 4.2.8 新增键；唯一删除项＝不再回写 base meta（非 receipt 字段）。批 5 工单必须附"v3 字段表（从实现抄录）＋ v4 增量表"。 |
| E6 | L198(187) `rpc_ledger.jsonl` 逐行字段不含 `plan_digest`，同一行却规定 `--resume` 以 `(plan_digest, params_digest, result_sha256)` 判已完成 | **补全**：`rpc_ledger.jsonl` 首行为 header `{"schema":"sqd-solana-rpc-ledger/v1","plan_digest":<…>,"reference":{kind,endpoint_fingerprint}}`，其后逐行按 4.2.10 字段（逐行不重复 plan_digest）；`--resume` 判据中的 `plan_digest` 取自 header，且必须 == 所在 `pending-<plan_digest>/` 目录名 == bundle.plan_digest。4.2.0"必须含 plan_digest 的文件清单"**增补** `rpc_ledger header`（与 layer/map header 同级）；`canonicalization.json`/`rpc_ledger.json` 草案在批 1 冻结时按本条补齐。探针的 `ledger.jsonl`（4.2.1）不受影响（探针无 plan_digest，靠 probe_id 绑定）。 |
| E7 | L239-241(228-230) 4.4.4 只给家族键集/一律 v3/`--reseal`/exact 分支检查，未给 `reconciliation-report/v3` 完整外壳字段表 | **以现役实现为准**：v3 外壳＝`reconciliation_report.py`（main=f06078e）当前写出的 v2 外壳全部键 ＋ `schema` 升 v3 ＋ 新增 `family`（"evm"/"solana"，由 target 推导，不接受外部声明）＋ `checks` 键集按家族（EVM 四项/Solana 五项，顺序固定）；批 5 工单必须附"v2 外壳字段表（从实现抄录）＋ v3 增量表"。 |

## 对批 1 的直接后果
- 批 1"契约冻结"时，契约草案 JSON 按 E1/E2/E3/E6 修订（canonicalization / publish_protocol / sqd-solana-coverage-pointer_v1 / rpc_ledger 四份），E4/E5/E7 各加一条 note 指向本注记；`INDEX.json` 的 `plan_sha256` 不变（PLAN.md 正文未改），增加 `errata: "PLAN_errata_batch0.md"` 与其 sha256。
- 先红清单不变（31 项）；E2 归入第 (21)/(28) 项的断言口径；E6 归入第 (13)/(26) 项相关的 resume 幂等测试（`test_sqd_gap_repair.py`）。

---

# 终审增补（2026-08-23 codex 只读终审后；Fable 逐条核实现役代码属实，全部采纳；PLAN 正文仍不改）

> 终审原文存档：`batch0_final_review_codex.txt`。裁定口径同上：冲突处以本注记为准；E8–E13 与 E2/E3 重裁对批 1 起全部工单有约束力。

| # | 终审意见（codex） | 核实 | Fable 裁定 |
|---|---|---|---|
| **E8** | 规范化全工程禁浮点（L152-154），coverage `era_params.min_ratio:0.99`（L161）却是浮点，且 probe_id 由 coverage_map 规范化内容计算 | 属实 | `era_params` 改为 `{window:1000000, min_headers:10000, min_ratio_num:99, min_ratio_den:100}`；判定用整数交叉相乘 `nonce_blocks*min_ratio_den >= header_blocks*min_ratio_num`；**全工程所有落盘 JSON（不只哈希输入）禁止浮点**，比率一律分子/分母整数。 |
| **E9（E3 重裁）** | 探针 `CURRENT.json` 只说"kernel 收据锁内发布"：`publish_overwrite` 单文件原子、不 fsync 目录（`receipt_kernel.py:590-601`）、无 CAS，旧探针可并发覆盖新探针；且 reconcile v4 `inputs` 未绑 `coverage_pointer`（L192-193），CURRENT 更新后旧 receipt 仍可能通过 | 属实 | 探针发布协议与 repair 同构：施工目录 `data/sqd_coverage/pending-<scan_id>/`（scan_id＝sha256(mint, scan_ranges, sqd 指纹, 启动时刻)[:16]，仅作临时名）→ 写齐 `coverage_map.json`（probe_id 在写前由规范化内容算出并写入）/`slot_counts.bin.gz`/`blocks.bin.gz`/`ledger.jsonl` 并逐文件 fsync → fsync 目录 → `os.rename(pending-<scan_id>, <probe_id>)` → fsync 父目录 → `.lock` 独占 → CAS：`pointer.supersedes == 当前 CURRENT.probe_id`（无 CURRENT 时 null）→ `publish_overwrite` 写 CURRENT → 锁内 fsync 指针父目录。`sqd-solana-coverage-pointer/v1` 字段（取代 E3 表）：`{schema, target{chain:"solana", token:<mint>, as_of_block:<slot_counts.to_slot>}, mode:"formal", verdict:"PASS", exit_code:0, producer{path,sha256}, inputs{coverage_map{path,size,sha256}, slot_counts{path,size,sha256}, ledger{path,size,sha256}, blocks_bitmap{path,size,sha256}|省略}, probe_id, supersedes:<probe_id>|null, published_at}`。**reconcile v4 `inputs` 新增必填 `coverage_pointer{path,size,sha256}`**（案根 `data/sqd_coverage/CURRENT.json`），validator 深验：该文件当前内容哈希 == receipt 记录值（即 CURRENT 未被更新）∧ 指针 `inputs.coverage_map.path` == receipt `inputs.coverage_map.path` ∧ probe_id 重算一致；CURRENT 更新后旧 receipt 一律 FAIL（须重跑 reconcile）。`camp_series`/handoff/audit 深验同样检查 coverage 当前性。 |
| **E10** | 崩溃恢复"⑧前崩溃 ⇒ 幂等补发 ⑧⑨"（L175）与 CAS `bundle.supersedes == CURRENT.gid`（L173）冲突：若 ⑧ 已写 CURRENT、⑨ fsync 前崩溃，重跑时 CURRENT.gid == 本 gid，CAS 必失败 | 属实 | 锁内增加幂等分支：若 `CURRENT.gid == bundle.gid` ∧ `CURRENT.inputs.bundle.sha256 == sha256(gen-<gid>/bundle.json)` ⇒ 不改 CURRENT，只补 fsync 指针父目录并成功返回（退出码 0，日志标 `idempotent-republish`）；否则按原 CAS 规则（`supersedes == CURRENT.gid` 且 base 哈希一致）；两者都不满足 ⇒ 孤儿代、报错退出。探针指针同构（按 probe_id）。 |
| **E11** | `solana-reconcile/v4` 的 `verdict/exit_code（与 gate_pass 同值）`（L193）与现役 `VERDICT_EXITS` PASS/0、FAIL/2 契约（`receipt_kernel.py:159-163`）语义不明 | 属实（措辞） | 明确映射：`gate_pass is True ⇒ verdict "PASS", exit_code 0`；`gate_pass is False ⇒ verdict "FAIL", exit_code 2`；经 `receipt_kernel.finalize_envelope` 强制一致；`gate_pass` 字段保留为布尔（展示/兼容），validator 校验三者互洽。 |
| **E2 重裁** | 合取式未显式含 `array_monotonic_unique==true`，也无"数组 ⊂[from,to]"断言，只靠 `response_ok` 间接承载 | 采纳 | `skipped_confirmation.ranges[]` 每段字段：`{from, to, response_sha256, count, response_ok:bool, array_monotonic_unique:bool, array_in_range:bool}`（后两者为生产时对原始响应数组的断言结果，逐段落盘）。离线 `complete` 合取式＝`response_ok ∧ array_monotonic_unique ∧ array_in_range ∧ (to−from+1) ≤ 500,000 ∧ reference_head_at_check ≥ to ∧ 位图该段长度 == to−from+1 ∧ popcount == count ∧ count ≤ 区间长度`；任一 false/不符 ⇒ 该段 unconfirmed ⇒ 其 NO_HEADER 保持未确认 ⇒ 有效 verdict INCONCLUSIVE。位图是原始数组在两断言为真时的无损表示；`--live-canary` 重拉若干段与位图切片对表。 |
| **E4/E5/E7 前移** | 把继承字段表延至批 3/5 与"批 1 契约冻结"冲突 | 采纳 | 批 1 首动作（批 1a）从 main=f06078e 现役实现抄录三张表写入契约草案：①`fetch_sqd_transfers_v2.py` 写出的 v4 meta 全字段（→`sqd-solana-cache_v4_repaired-meta.json` 的 `inherited_fields`）；②`replay_edges.py cmd_reconcile` 写出的 v3 全键（→`solana-reconcile_v4.json` 的 `inherited_fields`）；③`reconciliation_report.py` `_base_wrapper`/写出的 v2 外壳全键（→`reconciliation-report_v3.json`）。抄录须附源码行号，不得臆造。 |
| **E12（wrapper 形状）** | 草案把 checks 写成 `checks.evm/checks.solana`，现役外壳是单层 `checks{balance,…}`（`reconciliation_report.py:117-125`） | 属实 | `reconciliation-report/v3` 保持**单层** `checks{<key>: …}`；键集由新增顶层字段 `family`（"evm"/"solana"，由 target 推导）决定：EVM `(balance, supply, supply_truth, time)`、Solana `(supply, balance, supply_truth, time, exact_reconcile)`；不得嵌套分家族。 |
| **E13（先红写法）** | 依赖尚不存在模块的 (3)–(8)/(10)–(11)/(15)–(18)/(20)–(21)/(25)–(29c) 会 ImportError 装死 | 采纳 | 这些项：try-import 失败 ⇒ 打印 `EXPECTED_RED: <module/symbol> 未实现` 并以 exit 1 结束**该项**（烟雾红），同时**另写纯 fixture/oracle 子测试**校验"期望拒绝原因"的判定逻辑（不依赖未实现模块，用草案契约 JSON 构造正/反例，断言 validator 规则函数的预期行为——批 3/5 实现后直接接入）；(1)/(2)/(9)/(12)–(14)/(19)/(22)–(24) 必须直接运行现役入口，断言现役确实"闸不存在/坏产物被放行"（语义红），禁止用缺模块替代。 |

## 批 1 拆分（准入闸要求）
- **批 1a（准入补丁，先行）**：九份契约草案修订（`canonicalization`/`publish_protocol`/`sqd-solana-coverage-pointer_v1`/`sqd-solana-coverage_v1`/`rpc_ledger`/`solana-reconcile_v4`/`sqd-solana-cache_v4_repaired-meta`/`reconciliation-report_v3`/`INDEX`）＋ E4/E5/E7 三张继承表抄录 ＋ `draft_status: batch1-frozen`。完成后 codex 只读复审一次，判"可进批 1"后才派批 1b。
- **批 1b**：登记面（invariant/contract/scan-schemas）＋ 先红 31 项（按 E13 写法）。

---

# 批 1a 增补（2026-08-23，源自 codex 批 1a 抄录时的「发现项」，Fable 核实属实）

| # | 发现 | 裁定 |
|---|---|---|
| **E14** | 现役 v3 receipt 把 `minted_raw`、`burned_raw`、`snapshot_supply_raw` 写成**字符串**（`replay_edges.py:365,369`），而 `net_supply_raw` 是 JSON int（:366） | `solana-reconcile/v4` 三个 raw 字段**一律 JSON int**（Python 任意精度；与 E8"全工程落盘 JSON 禁字符串整数/禁浮点"一致）；`solana_exact_validate` 对字符串值拒收；v3 归 LEGACY 时按旧类型校验不回溯。`solana-reconcile_v4.json` 草案的 `inherited_fields` 对应三项 `type` 标"v3: string → v4: JSON int（E14）"——批 1b 顺手改（草案仍属 batch1-frozen 档，允许 errata 驱动的小修）。 |
| E15 | 现役 `fetch_sqd_transfers_v2.py` 写出的 v4 meta 不含 `edge_file_size/edge_file_sha256`，二者由 `replay_edges.py:312-314` 回写 | 已在 PLAN 4.2.6/4.2.8 与 E4 表中处理（repaired 生产者写出、消费端不回写；base meta 保持采集器原样不再被回写）——无新裁定，记录在案。 |
| E16 | 现役 wrapper 从 job spec 接受外部 `family`（`reconciliation_report.py:143-146`）且 `CHECK_KEYS` 固定四项 | 已由 E12 覆盖（`family` 由 target 推导、不接受外部声明；键集按家族）——批 5 实施。 |

---

# 批 1a 复审增补（2026-08-23，codex 准入闸第二次 `batch1a_review_codex.txt`；原 4 项阻塞全部【已闭合】；以下为新抓 3 矛盾＋批 1b 工单 4 项，Fable 核实属实全部采纳）

| # | 发现 | 裁定 |
|---|---|---|
| **E17** | `canonicalization.json` 必含表含 `rpc_ledger header`，但依赖图节点与 `publish_protocol.json` step_1 均漏 `rpc_ledger` | 依赖图增节点 `rpc_ledger`（append-only 台账，施工期持续追加；**step ③ 写 bundle 之前 fsync 定稿**，其 `{path,size,sha256,requests,credits_estimate}` 进 bundle；**不进 gid**——含时间戳/尝试次数等非确定内容；header 含 plan_digest）。step_1 增一句"rpc_ledger 自 step ① 起 append-only 写入，step ③ 前 fsync 定稿"。 |
| **E18** | `reconciliation-report_v3.json` 的 `exact_reconcile.*` 五字段无条件 `required:true`，与"EVM 仅四 checks"矛盾；路径未写成 `checks.exact_reconcile` | 字段名改 `checks.exact_reconcile.*`；`required` 条件化："family==solana 必填；family==evm 必须省略（出现即拒）"；语义＝对 `solana-reconcile/v4` exact receipt 的引用（path/size/sha256）＋摘要字段，与其他四项同构。 |
| **E14 落地** | E14 只在 `inherited_fields` 列名无类型、主 `fields` 缺项；INDEX 说批 1b 补但批 1b 工单禁改草案 | 批 1b 白名单**允许且仅允许 errata 驱动的四份草案小修**：`solana-reconcile_v4.json`（E14：`minted_raw/burned_raw/snapshot_supply_raw` 入主 fields，type "JSON int"，inherited 标 v3 string→v4 int）、`reconciliation-report_v3.json`（E18）、`canonicalization.json`＋`publish_protocol.json`（E17）；其余草案不动；INDEX 记修订。 |
| **E19（先红清单扩 31→35 项＋写法修正）** | 第(2)项被降为烟雾红；E9/E10/E11/E14 缺反例 | (2) 改**语义红**：直跑现役 `curve_cost`（逐笔储备更新）与 `entity_source_trace` 顺序模拟，同一缺陷 slot 两种边序得出不同结果（事实断言 GREEN，证明顺序敏感），随后断言"现役存在把缺陷 slot 统一到参考非投票序号的机制（slot_index_map）"→ 缺 → RED；新增 **(30)** 探针指针 CAS（supersedes≠当前 probe_id 仍切）/同 probe_id 幂等分支/目录 fsync 三反例（oracle＋烟雾）；**(31)** coverage `CURRENT.json` 更新后旧 reconcile receipt 仍被接受（现役无 coverage_pointer → 语义红：用现役 `reconcile` 产 receipt 后改写 coverage 指针 fixture，断言 validator 应拒）；**(32)** `verdict/exit_code/gate_pass` 三元不互洽（PASS/2、FAIL/0、gate_pass true＋FAIL）仍被接受（oracle；顺带跑现役 `receipt_validate` 记录行为）；**(33)** v4 receipt raw 字段为字符串仍被接受（oracle；现役 v3 即字符串＝语义红证据）。**banned needles 调批 6 ＝ 批 6 硬闸**（不加不得收口）；invariant_scan 先红不替代逐项红证。 |

---

# 批 1b 增补（2026-08-23；codex 批 1b fail-closed 停工报告 `batch1b_done.md` 阻塞项，Fable 裁定）

| # | 发现 | 裁定 |
|---|---|---|
| **E20** | 给 `invariant_scan.FORMAL_E2E_REQUIRED_PRODUCERS["sol"]` 登记 `sqd_coverage_probe.py`/`replay_edges.py` 后，现役守卫 `test_batch4_invariant_guards.py:198`（断言默认 `formal_e2e_provenance_errors()==[]`）必然红——Solana 纵切片 `test_batch3_solana_vertical_slice.py` 尚无二者的执行证据 | 选项 2：**预期先红清单＝`invariant_scan.py`（20 项登记缺口）＋`test_batch4_invariant_guards.py`（仅 :198 一条）**；不得条件化常量/伪造 producer/削弱守卫。闭合批次写死：**批 2** 把 probe 接入 Solana 纵切片（离线 mock transport 下真实执行 `sqd_coverage_probe.py` 产 coverage 产物＋指针），**批 5** 把 `replay_edges.py reconcile`（v4）接入纵切片并产 exact receipt → 两条执行证据齐后 :198 自然转绿。沙箱两项回环 `EPERM` 失败为 companion 沙箱限制（本机复跑全绿），不计。 |

---

# 批 2/2b 验收增补（2026-08-23；Fable 本机联网冒烟与路 A 真值交叉表的发现，详见 `batch2b_fable_acceptance.md`）

| # | 发现 | 裁定 |
|---|---|---|
| **E21（待用户裁决，不改冻结参数）** | 时代校准按 100 万 slot 桶算"有 nonce 块/有块头块 ≥0.99"，统计只来自本案 slot_counts。阈值把"时代是否普遍用 nonce"与"桶内缺陷密度"耦合：缺陷段冒烟窗比率 0.77 → 4,863 个真缺陷全部 ERA_UNCERTAIN；若 ARC 全扫某桶缺陷密度 >1%（已知 38 段＋新发现微段集中在 06-13/15/16 三天），该桶全部缺陷 ERA_UNCERTAIN → 按计划文本 INCONCLUSIVE ⇒ FAIL，且 α 只普查 DEFECT_CANDIDATE ⇒ **越缺越修不了**。健康基线≈100%、老时代比率 0.1–0.5，阈值 0.90 同样能分清时代 | **批 3 按计划文本施工（ERA_UNCERTAIN 归 unconfirmed ⇒ INCONCLUSIVE）**；ARC 全扫结束后用逐桶真实统计报用户，候选改法：①允许 α 对 ERA_UNCERTAIN slot 普查并给归宿（census 行 confirmed/refuted 即为归宿，有效 verdict 规则相应扩到 candidate ∪ era_uncertain）；②冻结参数 `min_ratio` 0.99→0.90。用户拍板后若采纳，立批 3b 小修 validator/resolution（范围：`classify_four_states` 归宿规则＋`coverage_resolution` 有效 verdict 重算＋对应测试）。 |
| **E22（待用户裁决，成本结构）** | 健康期 5 万 slot 样本有 0.05% 单块零 nonce 候选（薄块/纯投票块），Helius 对照 3/3 全良性、普查必 refuted；外推全史 ≈6.7 万良性候选 ×10 credits ≈ **67 万 credits 只为驳回**，计划 §4.6 的 ≈68k 未含此项。且按计划文本每案 resolution 须自行给候选归宿，共享地图 `refuted_slots` 只用于"逐 slot 复核"不替代普查 ⇒ 每个新 Solana 案都要重付 | 选项：(A) 全普查（裁决④无上限；一次性，需补"驳回继承"规则：地图 `refuted_slots` 带 census 证据哈希，后案在 SQD 侧状态（该 slot 签名集哈希）未变时可继承驳回——链上侧是已 finalized 历史事实；需 errata 写进 4.2.4/4.3.1 与 validator）；(B) 允许公共 RPC 作"仅驳回用"第二参考（便宜但引入第二来源类，违背裁决④精神）；(C) 薄块启发式免普查（不可靠，Fable 反对）。**Fable 推荐 (A)＋驳回继承**。ARC 全扫给出精确候选数后再报。 |
| **E23（批 2c，已派）** | 探针只在整趟结束/配额停工时写 `resume_state.json`，22 小时全扫中途被杀全丢 | 批 2c：`_scan_ranges` 主线程每完成 N 页（`--checkpoint-every`，默认 2,000）写一次 `resume_state.json`（沿用现有 `_write_resume`，同一 pending 目录、identity 不变）；`--resume` 从检查点续扫只补 UNSCANNED；测试用 fixture transport 注入"第 k 页后中断"再 `--resume`，断言续扫请求数＝剩余页数且产物 probe_id 与一次跑通一致。不改 coverage 契约。 |
| **E24（批 3 工单补第 10 条）** | 探针能消费共享地图（`--known-map`）但不能把一次全扫**导出**成地图资产；README 已写"首版由 Fable 全扫验收后入库" | 批 3 新增：`sqd_coverage_probe.py export-shared-map --case-root --probe-id <id> --out assets/sqd-solana-coverage-map/`：从已发布 probe 产 `<YYYYMMDD>.{json,counts.bin.gz,blocks.bin.gz}`（schema `sqd-solana-shared-coverage-map/v1`、`ttl_days:30`、`supersedes`＝目录内上一版 version 或 null、`candidate_slots`＝重算 DEFECT_CANDIDATE、`refuted_slots`＝[]（待 E22 规则）、canary 64 slot＝由 sha256(probe_id) 驱动在有块头 slot 中确定性等距取样＋其 counts）；导出确定性（同 probe 两次导出字节一致）；validator 校验资产自洽并能被 `--known-map` 回读（round-trip 测试）。不新增 producer 登记（资产由 probe 的 coverage_map 哈希锚定）。 |

---

# 批 3 施工增补（2026-08-23；codex `batch3_done.md` 自报未闭合项 #6/#7/#8/#9，Fable 核实属实——均为冻结契约/计划文本的承载缺口，非施工偷懒；裁定后由批 3b 闭合）

| # | 发现 | 裁定 |
|---|---|---|
| **E25（β 输入与候选留痕；闭合 #6/#9）** | PLAN 4.1/4.3.2 规定 β"对残差 owner 做余额连续性二分"，但没冻结"残差 owner 从哪来"的产物，resolution 也不持久化 plan 的完整候选集（含 β 候选），离线 validator 无法独立验 β 候选完整性 | ①β 输入＝三份**现役产物**（不新造 schema）：`data/reconcile_receipt.json`（v3 现役／v4 批 5 后）、`data/replay_final_balances.json`（`{owner: replay_balance(int)}`，`replay_edges.py reconcile` 写出）、`data/holders_owners.json`（冻结快照 owner 余额；结构以现役文件为准核对）；**残差 owner 集合＝replay≠snapshot 的 owner（含只在一侧出现者），按 owner 排序**；`--residual-owners` 改为可选的显式子集过滤，不再是唯一来源。②二分算法按 `.staging_b2/arc_reference/routeA_full/hunt_remaining/hunt_step2_bisect.py` 移植（SQD 免费 `tokenBalances` 探针比较 `postAmount` 与 base 边重放余额；每 owner ≤40 次；断点邻域 ±64 slot 跑探针指纹；`--beta-rounds` ≤3；某轮无新候选即停）。③留痕：新证据文件 `evidence/beta_trace.json`（`sqd-solana-beta-trace/v1`：`inputs{receipt,replay_final_balances,holders_owners:{path,size,sha256}}`、`residual_owners[{owner,replay,snapshot}]`、`rounds[{round,owner,probes[{slot,sqd_post_amount|null,replay_balance,match,query_body_sha256,response_sha256}],breakpoint_slot|null,window[from,to],fingerprint[{slot,count}],candidate_slots[]}]`、`candidate_slots[]`），进 evidence_manifest（故进 gid）；`coverage_resolution` 增 **`plan_candidates{coverage:[…],beta:[…]}`**（草案 errata 小修），`plan.candidate_slots == sorted(coverage ∪ beta)`。④validator：`plan_candidates.beta == beta_trace.candidate_slots`；全部候选（coverage ∪ beta）有 census 归宿；trace 内部自洽（候选＝各轮并集、断点∈window、probes 按 slot 升序）；三份输入哈希与案根文件一致。⑤无残差（receipt gate_pass true）或未开 `--beta` ⇒ `plan_candidates.beta=[]`、不写 beta_trace。 |
| **E26（前置一致性改"状态一致"；闭合 #7）** | PLAN 4.1 写"coverage 阶段与 repair 阶段 SQD 签名集哈希一致"，但探针从未取签名集（只取逐 slot nonce 计数），该哈希不存在 | 前置一致性（每候选 slot，生产时）改为：(a) live 模式对该 slot **用探针同一查询体**免费重查 SQD nonce 计数，得 `sqd_nonce_count_at_repair`，须与 coverage `slot_counts` 状态一致（NO_HEADER ⇒ 仍无块头；ZERO_NONCE ⇒ 仍为 0；HEALTHY/SKIPPED_CONFIRMED slot 不得成为 α 候选——β 候选例外，记 `coverage_state`）；(b) census 的 SQD 普查自带 `response_sha256`；拟修复签名 ∉ 该普查签名集；(c) 参考块 blockhash 与 SQD 块头 hash 一致；任一不符 ⇒ 本次生产中止（SQD 状态已变），已发布旧代不受影响。census 行增 **`coverage_state`**（validator 用 slot_counts 重算核对）与 **`sqd_nonce_count_at_repair`**（cache 模式 null，仅 exploration 允许 null）——草案 errata 小修。 |
| **E27（配额停工在途落账＋幂等续跑＋故障注入；闭合 #8）** | 现实现 `QuotaStopped` 抛出时已完成请求的 payload/ledger 不落 pending，`--resume` 重请求全部候选 | 按 PLAN 4.2.10/4.4.6 闭合：①`_live_payloads` 逐 slot 完成即把 evidence 对（`<slot>.sqd.json`/`<slot>.ref.json`）与 `rpc_ledger.jsonl` 行**落 pending**（append-only，行级 fsync 可按批）；配额首命中 ⇒ 在途请求完成后停派发、写 `STOPPED.json{reason,cursor,plan_digest,completed_slots}`、退出 3；②`--resume`：同 plan_digest 的 pending 内，凡 evidence 对齐全且 rpc_ledger 有对应 `(plan_digest, params_digest, result_sha256)` 成功行的 slot 跳过不重请求，残缺尾行丢弃；续跑后最终 gid 与一次不中断跑通**相同**（rpc_ledger 不进 gid，E17）；③故障注入测试（先红后绿）：(a) mock transport 第 k 个候选后返回 402 ⇒ STOPPED＋k 对证据＋ledger 行在盘，resume 只请求余下候选、最终 gid 相同；(b) 在步骤 ⑤–⑧ 之间注入异常（monkeypatch `_fsync_dir`/rename/CAS）⇒ resume 幂等补发或孤儿代被忽略；(c) CAS 漂移（resume 前 CURRENT 被他代抢先）⇒ 硬错不覆盖。 |
