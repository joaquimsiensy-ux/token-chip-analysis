# 工单 W4（v1）：修复生产者每候选 slot 的 SQD 请求由两次（状态探针＋census）合并为一次 —— 归属版本 9.2.0（producer 换代；登记在 W2）

> 出处：用户 2026-09-24 裁决第 4 条「同一个候选 slot 被 SQD 探两次，看看怎么修复」。
> 事实（调度方本机亲核，基线 `cc6298b`；行号按派工时基线重核）：
> ① `scripts/solana/sqd_gap_repair.py:1022` `_fetch_live_slot`：`:1024` 先 `_state_probe(sqd_transport, slot, retry=True)`（`:917`，请求体＝`sqd_query_body(slot, slot)`：`includeAllBlocks`＋`fields.block.number`＋`fields.instruction.transactionIndex`＋System Program `d4=0x04000000` 的 AdvanceNonce 指令过滤；返回 `present, nonce_count=len(block.instructions or []), 请求 sha, 响应 sha`）→ `validate_coverage_state_consistency(:576)` → Helius `getBlock` → `:1044` `census_body = _census_body(slot)`（`:643`：`includeAllBlocks`＋`fields.block.number/hash`＋`fields.transaction.transactionIndex/signatures/err`＋`transactions:[{}]` 全交易）再请求 SQD 一次；`:1052-1054` 校验 census 块头存在性与探针一致。即**每候选 slot 两次 SQD 请求**（PYTHIA 157,700 候选＝31.5 万次）。
> ② payload/evidence 字段（`:1086-1097`、`_routea_slot :1226` 写 `.sqd.json`）：`coverage_probe_query_sha256`、`coverage_probe_response_sha256`、`census_query_body_sha256`→`query_body_sha256`、`census_response_sha256`→`response_sha256`、`sqd_nonce_count_at_repair`。深验 `solana_exact_validate.py:1594-1605`：formal 下四个 sha 字段须为 hex64、`sqd_nonce_count_at_repair` 非 null、`_repair_state_matches`；**不重算任何 SQD 请求体摘要**（调度方 grep：validator 无 `_census_body`/`sqd_query_body` 引用）。`_verify_adopted_record(:783)` 只核 ledger 行与 getBlock 参数摘要，不涉这两字段（施工前须自核，若涉及则停工汇报）。
> ③ transport：`:108` `RepairLiveTransport.call` 对 `{"sqd-census","sqd-probe","sqd-beta"}` 同走 `net.curl_json(f"{DEFAULT_SQD}/stream")`；`RepairFixtureTransport(:78)` 按 `request_digest(kind, body)` 查表。beta 路径 `_probe_fingerprint(:483)` 用 `sqd-probe` 区间查询——**保留**。
> ④ 测试夹具：`scripts/tests/test_sqd_gap_repair.py:255-266` 为每 slot 造三条响应（`sqd-probe` 状态块含 `instructions`×nonce_count、`reference-getBlock`、`sqd-census` 块含 header/transactions **无 instructions**）；`scripts/tests/test_batch8_repair_scale.py:57`（fake transport 按 kind 分支）、`:317`（直接调 `_sqd_call_with_backoff(..., "sqd-probe", ...)`）也引用 `sqd-probe`。
> ⑤ `compute_plan_digest`（`sqd_repair_core.py:59`）绑 producer sha → 本单改脚本即换代；存量案钉版运行时不受影响；跨代续跑走 9.1.0 `--resume --adopt-pending`。`:47` 注释已写明「改 `_census_body`/请求模板语义须换代并登记 producer_history」——登记归 W2。
> ⑥ SQD portal 查询语义（`data-pipeline-solana-capture.md` §13 实录）：一个请求可同时带多个选择器（`transactions`、`instructions`）并 `includeAllBlocks`，响应按块给出各选择器命中的数组；`sqd_coverage_probe.py:128` 探针即以 `instructions` 选择器单独工作，`_census_body` 以 `transactions` 选择器单独工作。合并＝同一请求同时带两个选择器与两组 fields。（沙箱无网，语义以文档与现有两请求体为据；调度方本机在派工后用真实 slot 对照验证一次，结果附于完成报告之后的验收记录。）

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工贴 `git status --short`（须为空）、`git rev-parse --short HEAD`；`git merge-base --is-ancestor <本单基线> HEAD` exit 0；`git diff --quiet <本单基线> HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets` exit 0（基线由调度方派工时填入）。不符停工。
- 0.2 禁读同 W1 §0.2。本目录可读：`README.md`、`workorder_W*.md`、`review_W4_reply_*.md`。
- 0.3 **白名单**：生产 `scripts/solana/sqd_gap_repair.py`；测试 `scripts/tests/test_sqd_gap_repair.py`、`scripts/tests/test_batch8_repair_scale.py`；完成报告 `W4_done.md`。
- 0.4 **不改**：`scripts/lib/solana_exact_validate.py`、`scripts/solana/sqd_repair_core.py`、`scripts/solana/sqd_coverage_probe.py`、`scripts/lib/producer_history.py`、`scripts/tests/invariant_manifest.json`、`references/**`、版本四处、其他任何文件。
- 0.5 锚核同 W1 §0.5（行号以本单基线为准）。
- 0.6 离线、不 commit/push、禁 stash/checkout/reset；临时目录同 W1 §0.6。
- 0.7 定向跑（全部 PASS 贴尾行）：`test_sqd_gap_repair.py`、`test_batch8_repair_scale.py`、`test_sqd_coverage_probe.py`、`test_batch3_solana_producers.py`、`test_repair_batch1.py`、`test_reconcile_v4_receipt.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`。

## 1. 硬约束

- 1.1 每候选 slot（α 路径）**恰一次** SQD 请求 ＋ 恰一次 Helius `getBlock`；beta 路径请求形态不变。
- 1.2 evidence/ledger/resolution/bundle 全部 schema 与字段名**不变**；`coverage_probe_query_sha256`/`coverage_probe_response_sha256` 保留（值＝合并后同一请求的请求/响应 sha，与 `query_body_sha256`/`response_sha256` 相同），`sqd_nonce_count_at_repair` 仍为非 null 整数；深验 `validate_repair_bundle_deep` 对新代 PASS，且对 W1 之前的旧代夹具（现有测试）仍 PASS。
- 1.3 状态一致性判定语义不变：`present`＝合并响应中存在 `header.number==slot` 的块（多块 → `ValueError`），`nonce_count`＝该块 `instructions` 数组长度（缺键视为 0，与探针 `:934` 一致）；`validate_coverage_state_consistency` 调用点与异常文案不变。
- 1.4 `_census_body` 只**新增** `instructions` 选择器与 `fields.instruction.transactionIndex`，其余键与顺序不变；`SYSTEM_PROGRAM` 与 `d4` 字面量从 `sqd_coverage_probe` 导入（该模块已被本脚本 import），禁止再抄一份常量。
- 1.5 `_state_probe` 若无其他引用则删除（beta 用 `_probe_fingerprint`），`RepairLiveTransport` 的 kind 集合保持含 `sqd-probe`；`_sqd_call_with_backoff` 不变。
- 1.6 生产改动 ≤ 60 行（增删合计）；不新增 CLI 参数；不改 stdout/stderr 文案除必要。
- 1.7 `git diff --stat` 只含 0.3 白名单。

## 2. 逐条施工

- 2.1 `_census_body`（锚 `def _census_body(slot):`）：在 `"transactions": [{}],` 前后加入 `"instructions": [{"programId": [SYSTEM_PROGRAM], "d4": ["0x04000000"]}]`，`fields` 增 `"instruction": {"transactionIndex": True}`。同文件顶部 `from sqd_coverage_probe import sqd_query_body` 改为同时导入 `SYSTEM_PROGRAM`（探针 `:42`）。
- 2.2 `_fetch_live_slot`（锚 `def _fetch_live_slot(slot, state, beta_slots, reference_pool, sqd_transport,`）：删除 `_state_probe` 调用；改为先 `census_body = _census_body(slot)`；`census_value = _sqd_call_with_backoff(sqd_transport, "sqd-census", census_body, slot, "SQD census failed")`；从 `blocks` 取 `matching`（`header.number==slot`），`len(matching)>1 → ValueError(f"SQD census duplicated slot {slot}")`；`present=bool(matching)`；`nonce_count=len((matching[0].get("instructions") or [])) if present else 0`；`census_raw=canonical_json(blocks)`；`probe_query_sha=sha256_bytes(canonical_json(census_body))`、`probe_response_sha=sha256_bytes(census_raw)`；然后 `validate_coverage_state_consistency(...)`；再 Helius；后续 `normalized_sqd` 等逻辑不变（原 `:1052-1054` 的「探针与 census 块头不一致」检查删除，因已同源）。payload 字段赋值不变。
- 2.3 删除 `_state_probe`（锚 `def _state_probe(transport, slot, *, retry=False):`）——先 `grep -n "_state_probe"` 确认仅 `:1024` 一处引用。
- 2.4 模块 docstring 或 `:47` 注释旁追加 ≤ 4 行：「9.2.0：α 路径探针并入 census 请求；`coverage_probe_*` 两字段与 `query_body_sha256/response_sha256` 同值；producer 换代」。
- 2.5 测试：
  - `test_sqd_gap_repair.py:255-266` 夹具：census 块加 `"instructions": [{"transactionIndex": 0}] * nonce_count`；删除 `sqd-probe` 条目（若某用例依赖其存在则改为不依赖）。新增断言：fixture transport 加计数器，正式修复一次运行中 kind==`sqd-census` 的调用次数 == 候选数、kind==`sqd-probe` == 0（beta 用例除外）。新增故障向量：①census 响应 `instructions` 非空 → `ValueError` 含 "SQD coverage state changed before repair"；②同 slot 两块 → `ValueError` 含 "duplicated"；③缺 `instructions` 键 → 视为 0 正常通过。
  - `test_batch8_repair_scale.py:57/:317`：按实况改（fake transport 的 `sqd-probe` 分支改为 `sqd-census` 分支返回带 `instructions` 的块；`:317` 直接调用若针对 `_state_probe` 则改为对 `_sqd_call_with_backoff` 同等断言）。
  - 深验用例（现有 `validate_repair_bundle_deep` 相关）在新夹具下通过。

## 3. 完成报告 `W4_done.md`

首行 `# W4 完成：…`/`# W4 停工：…`；§0.1 输出；`_state_probe` 引用 grep 结果；`_verify_adopted_record` 自核结论；实际 diff 行号/行数；§0.7 尾行；新 `sqd_gap_repair.py` 文件 sha256（`shasum -a 256`，供 W2 登记）；披露禁读路径。
