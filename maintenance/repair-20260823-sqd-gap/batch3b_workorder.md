# 批 3b 工单（codex 施工）：闭合批 3 自报未闭合项——E25 β 输入与候选留痕／E26 前置一致性"状态一致"／E27 配额停工在途落账＋幂等续跑＋故障注入（分支 fix/sqd-gap-v6520，基线 c237263）

- 权威：`PLAN_errata_batch0.md` **E25/E26/E27**（本批新增，优先级最高）＞ 契约草案（本批允许 errata 驱动小修：`sqd-solana-coverage-resolution_v1.json`、`evidence_tables.json`、`rpc_ledger.json`、INDEX.json 记修订）＞ PLAN 4.1/4.2.4/4.2.5/4.2.10/4.3.2/4.4.6。
- 目标对齐：让批 3 交付的修复生产者在 **live 模式**能 (1) 配额停工后 `--resume` 不重付已完成请求且最终 gid 与一次跑通相同；(2) β 残差驱动兜底可用且离线可验；(3) 前置一致性按 coverage 状态核对。离线施工、不 commit、不联网、完成即停；锚文本与实况不符即停工报告。
- 开工门禁：`git rev-parse --short HEAD` == c237263；`.staging_b2` 21 OK、`.staging_b3` 14 OK（staging 只读参考）。

## 实况锚点（c237263）
- `scripts/solana/sqd_gap_repair.py`：`class QuotaStopped` :46、`_residual_candidates` :299、`_plan` :321、`_census_body` :369、`_is_quota` :393、`_live_payloads` :405、`_cache_payloads` :491、`_routea_slot` :519、`_produce_blocks` :638（主流程：pending 建立/ payloads / census / resolution / merged / bundle / 发布；`rpc_ledger.jsonl` 写于 :760 附近）、`_verify` :852、`build_parser` :896（repair 子命令已有 `--residual-owners/--beta/--beta-rounds/--resume`）。
- `scripts/lib/solana_exact_validate.py`：`validate_repair_bundle_deep` :900；resolution/census 校验在其内部（按实况定位）。
- `scripts/solana/sqd_repair_core.py`：纯函数核（规范化/gid 等）。
- β 参考实现：`.staging_b2/arc_reference/routeA_full/hunt_remaining/hunt_step2_bisect.py`（SQD tokenBalances 探针二分；只读移植语义）。
- β 输入现役文件格式：`data/replay_final_balances.json` ＝ `{owner: int}`；`data/holders_owners.json` ＝ 冻结快照 owner 余额（**结构以 ARC 案实况为准，先读 `scripts/solana/replay_edges.py` 的写出/读入代码确认键名**，不得猜）；`data/reconcile_receipt.json` v3 键：`gate_pass/negative_balance_count/snapshot_mismatch_count/...`。

## 白名单
1. `scripts/solana/sqd_gap_repair.py`：
   - **E27**：`_live_payloads` 逐 slot 完成即落 pending（evidence 对＋`rpc_ledger.jsonl` 追加行；已有的 pending/`rpc_ledger` 写法对齐）；配额首命中 ⇒ 在途完成后停派发、`STOPPED.json{reason,cursor,plan_digest,completed_slots}`、退出 3；`--resume` 跳过已完成 slot（evidence 对齐全 ∧ ledger 成功行 `(plan_digest, params_digest, result_sha256)` 命中），残缺尾行丢弃；续跑后 gid 与一次跑通相同。
   - **E25**：β：`--beta` 时从三份现役产物推导残差 owner 集合（`--residual-owners` 变为可选显式子集过滤）；二分移植；`evidence/beta_trace.json`（`sqd-solana-beta-trace/v1`，字段见 E25）进 evidence_manifest；`plan.candidate_slots = sorted(coverage ∪ beta)`；resolution 增 `plan_candidates{coverage,beta}`；`--beta-rounds` ≤3，某轮无新候选即停；无残差/未开 β ⇒ `beta=[]` 不写 trace。
   - **E26**：live 模式每候选 slot 用探针同一查询体（`sqd_coverage_probe.sqd_query_body(slot, slot)`，只读 import 或复制查询体常量——二选一并在 done 报告写明）免费重查 nonce 计数 → census 行 `sqd_nonce_count_at_repair`、`coverage_state`（由 coverage slot_counts 重算）；状态不一致 ⇒ 中止（退出码非 0、pending 保留、写 STOPPED-like 说明或直接异常——按 PLAN"本次生产中止"）；cache 模式 `sqd_nonce_count_at_repair=null`（仅 exploration 允许）。
2. `scripts/lib/solana_exact_validate.py`：E25（`plan_candidates` 与 beta_trace 一致、全部候选归宿、trace 自洽、三份输入哈希）；E26（`coverage_state` 重算核对；formal 禁 null `sqd_nonce_count_at_repair`；状态语义核对）；E27（bundle/ledger 不变，只需 ledger schema 兼容 `completed_slots` 等）。
3. `scripts/solana/sqd_repair_core.py`：如需纯函数（残差 owner 推导、二分步进、状态映射）放这里。
4. `scripts/tests/test_sqd_gap_repair.py`＋`scripts/tests/fixtures/sqd_repair/`（≤300KB）：E27 三类故障注入 (a)(b)(c) 先红后绿；E25：fixture 案根含三份输入（小 holders/replay_final_balances/receipt v3）＋mock SQD tokenBalances transport → β 推导残差 owner → 二分命中注入的断点 slot → 候选进 plan → census 归宿 → validator 通过；β 未开/无残差 ⇒ `beta=[]`；篡改 beta_trace 一字节 ⇒ 拒；E26：coverage 状态与重查不一致 ⇒ 中止（先红后绿）；`--residual-owners` 子集过滤。
5. 契约草案小修（errata 驱动，INDEX.json 记修订）：`sqd-solana-coverage-resolution_v1.json`（`plan_candidates.coverage[]/beta[]`、census `coverage_state`、`sqd_nonce_count_at_repair`）、`evidence_tables.json`（beta_trace 表）、`rpc_ledger.json`（STOPPED `completed_slots`、resume 跳过规则措辞）。
6. `maintenance/repair-20260823-sqd-gap/batch3b_done.md`＋`batch3b_green_evidence.txt`（红→绿对照；`test_sqd_gap_repair.py`/`test_sqd_coverage_probe.py`/`test_reconcile_v4_receipt.py`/`run_all.py` 结果与允许红说明；scan-schemas §14 与草案的差异只记录留批 6）。
**不动**：其他一切（含 `sqd_coverage_probe.py` 除非只读 import 查询体；`replay_edges.py`；批 4/5 消费端；references；PLAN/errata 正文）。

## 验收口径（Fable）
离线全绿＋三类故障注入红→绿；本机：(1) ARC 全扫发布后 `--blocks-cache` exploration 代 83/83（批 3 遗留）；(2) 用 ARC 残差输入（旧 v3 receipt gate_pass=false＋replay_final_balances＋holders_owners）跑 `plan --beta` 干跑，看残差 owner 集合是否＝26（3 负余额＋23 不匹配）且二分候选命中已知断点（426,869,468／427,406,628 所在邻域）——SQD 免费探针本机联网代跑。
