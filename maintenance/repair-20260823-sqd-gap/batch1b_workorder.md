# 批 1b 工单（codex 施工）：登记面 ＋ 先红 35 项（分支 fix/sqd-gap-v6520；按 errata E17–E19 修订版）

- 前置：批 1a 契约冻结已验收；codex 复审（`batch1a_review_codex.txt`）判原阻塞全部闭合、另提 4 项工单修正——已按 errata E17–E19 并入本工单。
- 权威：`PLAN.md` §4.5.2／§5 ＋ `PLAN_errata_batch0.md`（E1–E19，冲突以 errata 为准）＋ `contracts_draft/*.json`（batch1-frozen）。
- 目标对齐：①把新协议登记进契约/不变量登记面（文档先行、契约 needle 命中）；②写 31 项先红测试并留红证。**本批不实现任何生产代码、不改任何生产脚本、不改 PLAN/errata/契约草案**。离线、不 commit、完成即停。
- 工作方式：小步；每完成一个测试文件就跑一遍并把输出追加进红证文件；发现工单行号与文件实况不符 → 停工写 done 报告（不要猜）。

## 白名单
1. `scripts/tests/invariant_manifest.json`（只增不删：receipt_producers／receipt_consumers／transport_calls／atomic_writes／formal_entrypoints ＋ `minimum_counts` 同步上调）
2. `scripts/tests/invariant_scan.py`：仅两处——`FORMAL_E2E_REQUIRED_PRODUCERS["sol"]`（现 :81-87，`"sol": frozenset({` 起、`}),` 止）加 `scripts/solana/sqd_coverage_probe.py` 与 `scripts/solana/replay_edges.py`；`FAILURE_ARTIFACT_COVERAGE`（:99 起）按既有条目形态加 `scripts/solana/replay_edges.py` 与 `scripts/solana/sqd_gap_repair.py`。其余一行不动。
3. `scripts/tests/contract_manifest.json` ＋ `scripts/tests/contract_ids_snapshot.json`：新增 **required** needles（ID 前缀 `CT-SQDGAP-01…`，authority_file＝`references/scan-schemas.md`，stages 按 PLAN）：`sqd-solana-coverage/v1`、`sqd-solana-coverage-pointer/v1`、`sqd-solana-coverage-resolution/v1`、`sqd-solana-repair-layer/v1`、`sqd-solana-slot-index-map/v1`、`sqd-solana-repair-bundle/v1`、`sqd-solana-repair-pointer/v1`、`sqd-solana-rpc-ledger/v1`、`solana-reconcile/v4`、`reconciliation-report/v3`、`wave-scan/v5`、`flow-anomaly/v3`、`exact_reconcile`、`sqd_gap_repair.py/v1`、`edge_source_binding`、`有块头但零 AdvanceNonce`、`reference-nonvote-ordinal/v1`、`CURRENT.json`；snapshot 集合同步。**banned needles 本批不加**（与文档修订同批，批 6）——理由：`docs_lint` 在 pre-commit 里跑 `validate_contract_manifest`，banned 句仍在文档会卡提交。
4. `references/scan-schemas.md`：新增章节登记上述全部 schema（每个 schema 一节：字段表＋不变量＋生产者/消费者，内容**以 contracts_draft 为准逐字段**；wave-scan/v5／flow-anomaly/v3 写"与 v4/v2 的差异段"＝新增 `edge_source_binding`（Solana 必填、EVM 省略）；本册路由段更新）。docs_lint 的引用/粗体配对规则必须通过（`python3 scripts/tests/docs_lint.py --all`）。
5. 新测试四件（先红）：`scripts/tests/test_sqd_coverage_probe.py`、`scripts/tests/test_sqd_gap_repair.py`、`scripts/tests/test_reconcile_v4_receipt.py`、`scripts/tests/test_recon_fifth_check.py`
6. `maintenance/repair-20260823-sqd-gap/batch1b_red_evidence.txt`（四件逐项全量输出＋`run_all.py` 结果）＋ `batch1b_done.md`
7. **errata 驱动的草案小修（仅限四份，E14/E17/E18 原话）**：`contracts_draft/solana-reconcile_v4.json`（E14 三 raw 字段入主 fields、type JSON int）、`contracts_draft/reconciliation-report_v3.json`（E18 `checks.exact_reconcile.*` 条件必填）、`contracts_draft/canonicalization.json`＋`contracts_draft/publish_protocol.json`（E17 rpc_ledger 节点与 step_1 句）；`contracts_draft/INDEX.json` notes 记录；其余草案零改动。
**不动**：`scripts/tests/run_all.py`（SUITE 收口才改）、`scripts/lib/producer_history.py`、全部生产脚本、`VERSION/pyproject.toml/CHANGELOG.md/SKILL.md`、references 其他文档、PLAN/errata、上述四份以外的草案。

## 先红 35 项 → 测试文件映射与写法（E13 铁律；E19 扩项）
- **语义红**（必须直接运行现役入口，断言"应拒绝/应存在机制"而现役放行/缺失）：(1)(2)(9)(12)(13)(14)(17)(19)(22)(23)(24)(31)(33-现役字符串即证据)
- **烟雾红＋oracle**（目标模块不存在：try-import 失败 ⇒ 打印 `EXPECTED_RED: <module/symbol> 未实现` 并该项 exit 1；另写纯 fixture/oracle 子测试，用 contracts_draft 的字段表构造正/反例，断言"期望拒绝原因"——批 3/5 实现后直接接入）：其余各项。
- 禁止：skip／xfail／静默通过／用缺模块替代语义反例。每项输出一行机器可读结果 `RED|GREEN <项号> <原因类型> <一句话>`。
- 可复用 fixture：`scripts/tests/sqd_v4_test_fixture.py`（小 v4 缓存/meta/快照）、`test_handoff_manifest.py` 中构造 READY 案根的 helper、`test_batch3_solana_vertical_slice.py` 的纵切片构造。

| 项 | 文件 | 类型 | 现役入口与预期（亲核行号） |
|---|---|---|---|
| (1) gate_pass=false 仍可 generate READY | test_recon_fifth_check | 语义红 | `handoff_manifest.py generate --mode full`：READY 必备齐但 `data/reconcile_receipt.json.gate_pass=false` → 现役 READY（AUTO_GATES :99 不读 gate_pass）→ 断言应 BLOCKED |
| (2) 同 slot 错序修复边改变 curve/entity 结果 | test_sqd_gap_repair | **语义红**（E19） | 直跑现役 `curve_cost`（逐笔储备更新）与 `entity_source_trace` 顺序模拟：同一缺陷 slot 两种边序（参考非投票序号 vs 伪序）得出不同结果（事实断言 GREEN＝顺序敏感成立），随后断言"现役存在把缺陷 slot 统一到参考序号的机制（slot_index_map 双射）"→ 缺 → RED |
| (3) sample 段冒充全覆盖 | test_sqd_coverage_probe | 烟雾＋oracle | oracle：coverage_map fixture `scan_ranges` 不覆盖、`sample_ranges` 覆盖 → 期望"并集不覆盖" |
| (4) coverage 文件被 repair 改写 | test_sqd_gap_repair | 烟雾＋oracle | oracle：guard 规则对 `data/sqd_coverage/` 写入者≠probe 拒 |
| (5) 同签名多边被去重丢边 | test_sqd_gap_repair | 烟雾＋oracle | oracle：一笔交易两条边 → merged 行数恒等式 |
| (6) 第二代覆盖旧代文件 | test_sqd_gap_repair | 烟雾＋oracle | oracle：gen 目录不可变（exclusive 写拒） |
| (7) 无 bundle/无指针 gen 被当有效代 | test_sqd_gap_repair | 烟雾＋oracle | oracle：目录 fixture（pending-*、无 CURRENT 的 gen）→ resolver 期望返回 base |
| (8) local-evidence-cache 代进 formal | test_sqd_gap_repair | 烟雾＋oracle | oracle：bundle.mode=exploration → formal 拒 |
| (9) 显式 base 路径绕 resolver（六入口） | test_reconcile_v4_receipt | 语义红 ×6 | `wave_scan.py`(:104-122 接受任意 `--edges-sol`/`--sol-cache-meta`)、`flow_anomaly_scan.py`、`entity_source_trace.py`、`curve_cost.py`、`camp_series_provenance.py`、`audit_closed_accounts.py`：各用复制到别目录的 v4 base 对显式传入 → 现役放行 → 断言应拒（正式路径集合规则） |
| (10) refuted-only 产代 | test_sqd_gap_repair | 烟雾＋oracle | oracle：census 全 refuted → 期望不产代 |
| (11) `repair_bundle:null` 过 envelope | test_reconcile_v4_receipt | 烟雾＋oracle | oracle：v4 receipt fixture inputs 含 null 键 → 期望拒；顺带对现役 `receipt_validate` 跑同 fixture 记录其行为 |
| (12) cache upper≠快照 slot 仍 PASS | test_reconcile_v4_receipt | 语义红 | `replay_edges.py reconcile`（:343 `snapshot_slot >= to`）：fixture upper<snapshot → 现役 PASS → 断言应 FAIL |
| (13) base meta 被 reconcile 回写 | test_reconcile_v4_receipt | 语义红 | `replay_edges.py reconcile`（:312-314 回写）：跑后 meta 文件 sha256 变化 → 断言不得变 |
| (14) audit_release 只看 status 放行坏 receipt | test_recon_fifth_check | 语义红 | `audit_release_gate.py check_reconciliation`（:467-471 只看 wrapper）：wrapper PASS 但子 receipt 哈希不符 → 现役放行 → 断言应拒 |
| (15) base 重采后旧代仍被消费 | test_sqd_gap_repair | 烟雾＋oracle | oracle：bundle.base.edge_sha256≠当前 base → 期望 resolver 硬错 |
| (16) gid 自引用/exploration 与 formal 同目录/同内容不同 supersedes 同 gid | test_sqd_gap_repair | 烟雾＋oracle | oracle：规范化函数对 fixture 的 gid 差异（三反例） |
| (17) 复制 base 到别目录显式传入绕过 | test_reconcile_v4_receipt | 语义红 | 现役 `validate_cache_meta` 接受任意路径 meta → 断言 v2 应拒（meta_path ∉ 正式路径集合） |
| (18) CAS：supersedes≠当前 CURRENT 仍能切指针 | test_sqd_gap_repair | 烟雾＋oracle | oracle：publish 规则对 supersedes 不等拒；含 E10 同 gid 幂等分支正例 |
| (19) 旧 base 派生 wave/flow 携带进 READY | test_recon_fifth_check | 语义红 | `handoff_manifest.py verify`：wave/flow 产物 binding 与 exact receipt 不等 → 现役放行（:388-440 只查 schema/字段）→ 断言应拒 |
| (20) slot_counts 含 UNSCANNED/长度不符/台账有洞仍 PASS | test_sqd_coverage_probe | 烟雾＋oracle | oracle：三反例各一 |
| (21) getBlocks complete 自报 true 但数组不递增/越界/超 500k | test_sqd_coverage_probe | 烟雾＋oracle | oracle：E2 重裁 8 项合取式逐项反例 |
| (22) wave v4/flow v2 旧产物被 v5/v3 验收接受 | test_recon_fifth_check | 语义红 | `handoff_manifest.py verify`（:400 WAVE_SCHEMA、:426 flow-anomaly/v2）：v4/v2 产物现役接受 → 断言升版后应拒（fail-closed 提示重跑） |
| (23) 无 `--case-root` 或 symlink 案根被正式路径接受 | test_reconcile_v4_receipt | 语义红 | `wave_scan.py` 现役无 `--case-root` 仍跑通；symlink 案根现役接受 → 断言应拒 |
| (24) curve/audit_closed 在场但 binding 不等仍 READY | test_recon_fifth_check | 语义红 | `handoff_manifest.py verify`：案根内 curve/audit_closed 产物 binding 不等 → 现役放行 → 断言应拒 |
| (25) merged meta 含 bundle 哈希/gid 或 bundle.merged.meta_sha256 不等 | test_sqd_gap_repair | 烟雾＋oracle | oracle：两反例 |
| (26) 目录未 fsync 即认发布完成 | test_sqd_gap_repair | 烟雾＋oracle | oracle：monkeypatch `os.fsync` 记录 fd 类型，期望代目录/父目录/指针父目录三次目录 fsync |
| (27) 金额写成字符串仍得同一 gid | test_sqd_gap_repair | 烟雾＋oracle | oracle：规范化对 `"amt":"1"` 拒（禁字符串整数） |
| (28) 位图长度/popcount/范围不符仍 complete | test_sqd_coverage_probe | 烟雾＋oracle | oracle：三反例 |
| (29a) resolution 重算非 DEFECTS_CONFIRMED 仍 PASS | test_sqd_gap_repair | 烟雾＋oracle | oracle |
| (29b) 修复交易/重映射 slot 无 confirmed 支撑仍 PASS | test_sqd_gap_repair | 烟雾＋oracle | oracle |
| (29c) 新候选未被当前代 census 覆盖仍 PASS | test_sqd_gap_repair | 烟雾＋oracle | oracle |
| (30) 探针指针 CAS/同 probe_id 幂等/目录 fsync | test_sqd_coverage_probe | 烟雾＋oracle | oracle 三反例：supersedes≠当前 probe_id 仍切；同 probe_id＋同哈希须幂等成功；monkeypatch `os.fsync` 期望探针目录/父目录/指针父目录三次目录 fsync（E9/E10） |
| (31) coverage CURRENT 更新后旧 reconcile receipt 仍被接受 | test_reconcile_v4_receipt | 语义红 | 用现役 `replay_edges.py reconcile` 产 receipt 后，改写案根 coverage 指针 fixture（新 probe_id）→ 断言 validator 应拒（receipt 无/不等 `inputs.coverage_pointer`）→ 现役无此绑定 → RED（E9） |
| (32) verdict/exit_code/gate_pass 三元不互洽仍被接受 | test_reconcile_v4_receipt | 烟雾＋oracle | oracle：PASS/2、FAIL/0、gate_pass true＋FAIL 三反例；顺带跑现役 `receipt_validate` 记录其对 PASS/2 的行为（E11） |
| (33) v4 receipt raw 字段为字符串仍被接受 | test_reconcile_v4_receipt | 语义红 | 现役 v3 receipt `minted_raw/burned_raw/snapshot_supply_raw` 即字符串（`replay_edges.py:365,369`）＝证据；断言 v4 validator 应拒字符串 → 缺 → RED（E14） |

## 红证与汇报
- `batch1b_red_evidence.txt`：四件逐个 `python3 scripts/tests/<file>.py` 的全量 stdout+stderr、35 项的 `RED|GREEN` 汇总行（应 35 RED；第(2)项的事实断言子步骤 GREEN 单列）、`python3 scripts/tests/run_all.py` 全量输出（预期红项＝`invariant_scan.py`（manifest 登记了尚不存在的脚本）；其余必须绿——任何其他项变红＝本批引入回归，先修再交）。
- `batch1b_done.md`：改动清单（文件/行）、登记面增项表、35 项映射实况、四份草案 errata 小修对照、run_all 红项解释、「发现项」、「未做」、白名单自述。
- **批 6 硬闸登记**：本批不加 banned needles（docs_lint 在 pre-commit 会卡提交），done 报告必须单列"批 6 必做：banned needles 4 组与文档修订同 commit"。
