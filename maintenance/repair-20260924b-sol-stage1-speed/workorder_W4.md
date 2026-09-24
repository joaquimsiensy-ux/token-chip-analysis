# 工单 W4（v3.1）：修复生产者每候选 slot 的 SQD 请求由两次（状态探针＋census）合并为一次 —— 归属版本 9.2.0（producer 换代；登记走 `workorder_WR.md` 登记单 WR-a）

> 出处：用户 2026-09-24 裁决第 4 条「同一个候选 slot 被 SQD 探两次，看看怎么修复」。
> v3.1 变更：codex 复核 r3 通过（`review_W4_reply_r3.md`），采纳两条建议（事实⑥结论限定为已记录样本；§2.4 注释写明 α/β 共用流程）。
> v3 变更：吸收 codex 复核 r2（`review_W4_reply_r2.md`）——必改 1（事实⑥收窄为已记录证据，调度方已补三组内容对照实测 P3）；建议 2（无块头样本：范围查询截断误判，未取得 SQD 无块头在线样本，改由离线夹具覆盖 MISSING_BLOCK）、3（深验兼容自包含构造路线）、4（W1 保护边界与继承状态合并路径回归）采纳。
> v2 变更：吸收 codex 复核 r1（`review_W4_reply_r1.md`）9 条——必改 1–8 全采纳（事实⑤/⑥/② 改写、d4 经 `sqd_query_body` 复用、请求次数与 β 范围与错误时序明示、新采/认领证据区分、测试计数与故障向量、producer 登记前移为独立登记单 WR-a、禁读夹具与临时目录纪律）；建议 9 采纳（≤60 行保留、锚精确）。
> 事实（调度方本机亲核，基线 `cc6298b`；**派工基线＝W1 收官 commit `<W4_BASE>`，届时行号重核**，W1 只改本脚本 `validate_coverage_state_consistency` 一函数）：
> ① `scripts/solana/sqd_gap_repair.py:1022` `_fetch_live_slot`：`:1024` 先 `_state_probe(sqd_transport, slot, retry=True)`（`:917`，请求体 `sqd_query_body(slot, slot)`＝`includeAllBlocks`＋`fields.block.number`＋`fields.instruction.transactionIndex`＋System Program `d4=0x04000000` 的 AdvanceNonce 指令过滤；`:933` `nonce_count=len(block.instructions or [])`，返回 present/nonce_count/请求 sha/响应 sha）→ `:1026` `validate_coverage_state_consistency` → `:1030` Helius `getBlock` → `:1044` `census_body=_census_body(slot)`（`:643-653`：`includeAllBlocks`＋`fields.block.number/hash`＋`fields.transaction.transactionIndex/signatures/err`＋`transactions:[{}]`）再请求 SQD → `:1052-1054` 校验 census 块头与探针一致。即**无重试时每候选 slot 两次 SQD 调用**；`_sqd_call_with_backoff(:900-913)` 最多调 transport 四次，Helius pool（`:181-190`）可切 key 重试。`_plan(:607-608)` 候选＝α ∪ β，共用 `_fetch_live_slot`。
> ② evidence 构造在 `:1284-1298`（`_routea_slot` 写 `.sqd.json`）：`coverage_probe_query_sha256`、`coverage_probe_response_sha256`、`query_body_sha256`（census 请求）、`response_sha256`（census 响应）、`sqd_nonce_count_at_repair`。深验 `solana_exact_validate.py:1594-1606` 对 nonce 状态及四个摘要字段做 hex64/非空检查，**不重建 SQD 查询体、不要求 probe/census 摘要互异**（validator 无 `_census_body`/`sqd_query_body` 引用；`:1225` 重建的是 Helius getBlock 请求摘要）。`_verify_adopted_record(:783-815)` 校验前代登记、plan digest、候选前缀及 getBlock 参数摘要，不触及 `coverage_probe_*`；`_verify_ledger_rows(:745-779)` 不复算 SQD 摘要；`_payload_from_evidence(:978-985)` 原样恢复旧摘要。
> ③ transport：`:108` `RepairLiveTransport.call` 对 `{"sqd-census","sqd-probe","sqd-beta"}` 同走 `net.curl_json(f"{DEFAULT_SQD}/stream")`；`RepairFixtureTransport(:78)` 按 `request_digest(kind, body)` 查表。β 搜索 `_probe_fingerprint(:483)` 用 `sqd-probe` 区间查询——**保留**。
> ④ 测试夹具：`test_sqd_gap_repair.py:255-266` 每 slot 三条响应（`sqd-probe` 块含 `instructions`×nonce_count、`reference-getBlock`、`sqd-census` 块含 header/transactions 无 instructions）；`test_batch8_repair_scale.py:57-59` fake transport `sqd-probe` 分支、`:61-68` **已有** `sqd-census` 分支、`:316-322` 测 `_sqd_call_with_backoff` 重试（四次调用、2/4/8 秒），未调 `_state_probe`；`adoption_regressions(:842-880)` 用当前生产者生成 pending 再换 producer 标识。`main` 入口：`test_sqd_gap_repair.py:1210`、`test_batch8_repair_scale.py:325`。
> ⑤ `compute_plan_digest`（`sqd_repair_core.py:59-82`）绑定 producer sha；`_plan(:619-620)` 取当前脚本文件 sha，本单改脚本即换代。`:46-49` 注释针对 `SOLANA_MAX_SUPPORTED_TX_VERSION` 与 `repair_getblock_body`，未提 `_census_body`。跨代认领须满足前代 sha 已登记、除 producer 外 plan 身份可重现、成功记录构成候选前缀等条件。正式消费入口 `sqd_cache_identity.py:143-147` 要求 bundle.producer.sha256 ∈ `historical_producer_hashes(REPAIR_COLLECTOR_SCRIPT, "sqd-solana-cache/v4")`——**未登记的新代会被正式 resolver 拒绝**（深验 `:1611` 可过、指针可发，但消费被拒），故登记为收官前置（§3）。
> ⑥ **组合选择器实测（调度方本机 2026-09-24，`fable_probes_20260924.md` §P2/§P3）**：对同一 finalized slot 分别发 probe-only、census-only、combined 三组查询并比较：三组 `header` 全等；combined 与 census-only 的 `transactions` 规范化 JSON 全等；combined 与 probe-only 的 `instructions` 规范化 JSON 全等（重复项保留）。样本：有匹配 AdvanceNonce 指令的有头块 326000400（tx 402、匹配指令 53；交易数远大于匹配指令数，间接支持「同时含其他指令」）及 326000391/393/395；有块头零匹配块 326000396（tx 482、combined 无 `instructions` 键）。全部 HTTP 200、三方一致。529 为 SQD 服务端过载（census-only 单独请求亦出现），退避重试即恢复。**无块头样本**：范围查询 1000 slot 时 SQD 流被截断（分页尾巴），误判为缺块，单 slot 查询证实有块头；本工程未取得 SQD 无目标块头的在线样本，`present=False` 路径由 §2.5 离线 MISSING_BLOCK 正反例覆盖。结论：P3 已记录样本中的交易内容与匹配指令内容支持采用合并查询替代「探针＋census」；有头零匹配样本的 `instructions` 键缺失，符合 `or []` 语义。P4 未取得无目标块头在线样本；该路径及其他边界仍按 §2.5 离线验证。本段为设计依据，不替代施工验收。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工贴 `git status --short`（须为空）、`git rev-parse HEAD`（须＝`<W4_BASE>`）、`git merge-base --is-ancestor cc6298b HEAD` exit 0。不符停工。
- 0.2 禁读同 W1 §0.2（含子进程/测试脚本）。本目录可读：`README.md`、`workorder_W*.md`、`review_W4_reply_*.md`、`fable_probes_20260924.md`、`W1_done.md`。
- 0.3 **白名单**：生产 `scripts/solana/sqd_gap_repair.py`；测试 `scripts/tests/test_sqd_gap_repair.py`、`scripts/tests/test_batch8_repair_scale.py`；完成报告 `W4_done.md`（本目录）。
- 0.4 **不改**：`scripts/lib/solana_exact_validate.py`、`scripts/solana/sqd_repair_core.py`、`scripts/solana/sqd_coverage_probe.py`、`scripts/solana/sqd_cache_identity.py`、`scripts/lib/producer_history.py`、`scripts/tests/invariant_manifest.json`、`scripts/tests/test_batch3c_census_fields.py`、`references/**`、版本四处、其他任何文件。不给 `sqd_cache_identity.py` 加「现役 sha 自动接受」豁免。
- 0.5 锚核同 W1 §0.5（行号以 `<W4_BASE>` 重核）。
- 0.6 离线、不 commit/push、禁 stash/checkout/reset；临时数据只用系统 `tempfile`，不使用 `.staging_*`，**禁止批量删除命令**；环境禁止写入时只做源码复核并如实列未运行项。
- 0.7 定向跑（贴尾行；区分 PASS/FAIL/未运行及原因）：`test_sqd_gap_repair.py`、`test_batch8_repair_scale.py`（两者依赖禁读 `.staging_b3` 的用例**不得执行**，新增 W4 用例须自包含）、`test_batch3c_census_fields.py`、`test_sqd_coverage_probe.py`、`test_batch3_solana_producers.py`、`test_repair_batch1.py`、`test_reconcile_v4_receipt.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`。受限旧套件由调度方在有权访问夹具的验收环境运行并附结果。

## 1. 硬约束

- 1.1 对本轮尚未恢复的 live 修复候选，每 slot 只执行**一次合并 SQD 查询流程**；无故障、无重试时为一次 `sqd-census` transport 调用，状态校验通过后一次 `reference_pool.get_block`。保留 SQD 重试与 Helius 多 key 故障转移（实际请求数可大于一）；已恢复 slot 不再请求。β 搜索阶段的 `_beta_body`、`_probe_fingerprint` 及其请求模板不变；β 候选进入共用修复流程后同样使用合并查询。
- 1.2 evidence/ledger/resolution/bundle schema 与字段名不变。**本单新采集**的 evidence：`coverage_probe_query_sha256==query_body_sha256`、`coverage_probe_response_sha256==response_sha256`；**从前代恢复或认领**的 evidence 保留原摘要，不要求相等，不得改写以制造相等；允许同一新代同时含前代分离摘要与本代合并摘要。formal `sqd_nonce_count_at_repair` 仍为非负整数。
- 1.3 与被替换的 `_state_probe` 保持相同 present/nonce_count 计算：只统计 `header.number==slot` 的块，匹配块 >1 → 拒绝；无匹配块 present=False、nonce_count=0；有匹配块 `nonce_count=len(block.get("instructions") or [])`（缺键/null/空数组均为零；保存原始长度，**不按 255 截断**——coverage 普查的 `min(255, 2+len)` 是另一编码层）。`validate_coverage_state_consistency` 保持在 Helius 调用之前，函数判定与异常文案以 `<W4_BASE>` 的 W1 收官实现为准：**W4 不修改该函数体**，保留 W1 对 `INHERITED_REFUTED` 的 β 兼容与 α 拒绝规则。
- 1.4 `_census_body` 保持现有 block/transaction fields、`transactions` 选择器及原有键相对顺序，只追加探针所需 instruction fields 与 instructions 选择器——**通过本文件已导入的 `sqd_query_body(slot, slot)` 取得**，不新增或复制 SYSTEM_PROGRAM/d4 常量，不修改探针模板，无需新增 import。
- 1.5 `_state_probe`：删除前确认允许读取范围内只有定义 `:917` 与调用 `:1024` 两处命中（「仅一处」指调用）；删除后无剩余引用；保留 `_probe_fingerprint:483` 及 `sqd-probe` transport 支持；`_sqd_call_with_backoff` 不变。
- 1.6 生产文件增删合计 ≤60 行（`git diff --numstat <W4_BASE> -- scripts/solana/sqd_gap_repair.py`；测试与报告不计）；不得为压行数省略输入处理、改变既有重试或压缩可读性；不新增 CLI 参数。
- 1.7 `git diff --stat <W4_BASE>` 只含 0.3 白名单。

## 2. 逐条施工

- 2.1 `_census_body`（锚 `def _census_body(slot):`）：取 `probe_body = sqd_query_body(slot, slot)`；在 fields 中追加 `"instruction": probe_body["fields"]["instruction"]`，顶层追加 `"instructions": probe_body["instructions"]`；其余保持原值。
- 2.2 `_fetch_live_slot`（锚 `def _fetch_live_slot(slot, state, beta_slots, reference_pool, sqd_transport,`）：删除 `_state_probe` 调用；先 `census_body=_census_body(slot)`、`census_value=_sqd_call_with_backoff(sqd_transport, "sqd-census", census_body, slot, "SQD census failed")`；从 blocks 取 `matching`（`header.number==slot`），`len(matching)>1 → ValueError(f"SQD census duplicated slot {slot}")`；`present=bool(matching)`；`nonce_count` 按 1.3；`census_raw=canonical_json(blocks)`；`probe_query_sha=sha256_bytes(canonical_json(census_body))`、`probe_response_sha=sha256_bytes(census_raw)`；然后 `validate_coverage_state_consistency(...)`；再 Helius；后续 `normalized_sqd` 等不变（原 `:1052-1054` 「探针与 census 块头不一致」检查删除，已同源）。payload 字段赋值不变。
  **可观测变化（允许且须测试）**：SQD 传输失败及重复块错误现在先于 Helius 发生；原两请求块头不一致错误取消，重复块错误改为 census 文案；SQD 合法响应且状态匹配时 Helius pool 耗尽仍抛 QuotaStopped；SQD 自身先失败则可能先返回普通错误而不进额度停工路径。不得宣称全部异常顺序与文案不变。ledger 时序：`_fetch_live_slot` 只构造 ledger_row，成功行在 `_persist_live_slot` 写出两份 evidence 后追加；失败 slot 不追加成功行；QuotaStopped 由上层写 STOPPED 返回 3；并发保留按候选顺序落盘、已完成前缀与取消未开始任务的既有规则。
- 2.3 删除 `_state_probe`（锚 `def _state_probe(transport, slot, *, retry=False):`）按 1.5。
- 2.4 模块 `:46-49` 注释旁追加 ≤4 行：「9.2.0：α/β 候选共用修复流程的状态探针并入 census 请求（`_census_body` 经 `sqd_query_body` 复用探针选择器）；β 搜索查询保持不变；新采 evidence 的 `coverage_probe_*` 与 `query_body_sha256/response_sha256` 同值；改 `_census_body` 语义须换代并登记 producer_history」。
- 2.5 测试：
  - 计数在测试侧包装 transport（不给生产 `RepairFixtureTransport` 加计数）。对无重试、无额度切换、无 resume、无 β 搜索的正式运行，**逐 slot** 断言 sqd-census=1、sqd-probe=0、reference-getBlock=1，总数同时等于候选数；至少覆盖 workers=1 与现有并发路径。
  - 三个基础向量：① DEFECT_CANDIDATE＋有头＋非空 instructions → 拒绝，异常含「SQD coverage state changed before repair」，Helius 调用 0、无该 slot 成功 ledger 行；② 两个匹配目标 slot 的块 → 拒绝含 `duplicated`，Helius 0；③ DEFECT_CANDIDATE＋有头缺 `instructions` 键 → 按零通过，核 evidence 的 nonce_count 与两组摘要相等。
  - 补 null/空数组；MISSING_BLOCK 无头正例与有头反例；`beta_candidate=True` 的 HEALTHY 用例检查 253/255/256 条指令仍保存原始长度。
  - SQD 重试耗尽与 Helius quota 组合故障：断言先后顺序、返回码、STOPPED 与成功 ledger 前缀符合 2.2；保留现有额度切换、resume、并发有序落盘与 β 搜索回归。
  - `test_sqd_gap_repair.py:255-266` 夹具 census 块加 `"instructions": [{"transactionIndex": i} ...]×nonce_count`；`sqd-probe` 条目按是否仍有用途保留或删除。`test_batch8_repair_scale.py:61-68` 已有 census 分支在此追加 instructions；`:57-59` probe 分支按用途保留/删除，不得改名遮蔽；`:316-322` 保留四次调用/2/4/8 秒断言，可增 `sqd-census` 参数覆盖。
  - **深验兼容**：保留独立的旧格式证据构造（显式用旧 probe-only 与 census-only 请求及分离响应计算摘要，不随 `_census_body` 改动自动变新格式）；分别验证旧格式、新格式、「认领旧格式前缀＋新格式剩余 slot」混合代：断言旧 evidence 字节不变、旧 slot 无重新请求、新 slot 两组摘要相等、深验通过。
  - **深验兼容构造路线**：复用 `build_batch3b_case`（`test_sqd_gap_repair.py:170-222` 自包含 10,000-slot coverage/base 构造器），missing transaction 使用测试代码内构造的 nonce 交易及 token balance 变化（`:277-302`），不调用 `staged_missing_transactions`；旧格式 helper 显式固定旧 probe-only/census-only 模板及各自响应，独立计算四个摘要并形成 evidence/ledger；选择已登记前代 sha，保持 base、coverage、候选及 reference 身份不变，重算前代 plan_digest（参考 `:820-954` 现有组织方式）；分别构造全旧格式、全新格式、旧前缀＋新剩余 slot 三类用例；用于发布及深验的用例至少含一个 confirmed 缺失交易（避免 refuted-only 提前返回不到 bundle 深验入口）。登记前的直接深验不替代 §3 登记后的正式入口验收。
  - **继承状态合并路径回归**（自包含）：`INHERITED_REFUTED`＋β＋有头＋零 nonce 通过；同状态非 β 拒绝；β 下无头或非零 nonce 拒绝，且拒绝发生在 Helius 调用前。保留 W1 已加入测试文件及 main 的用例，不得覆盖。
  - 新增测试接入各文件实际 `main` 入口。

## 3. 完成报告 `W4_done.md` 与收官前置

首行 `# W4 完成：…`/`# W4 停工：…`；§0.1 输出；`_state_probe` grep 结果；实际 diff 行号/`--numstat`；§0.7 尾行与未运行清单；新 `sqd_gap_repair.py` 文件 sha256（`shasum -a 256`）；披露禁读路径。
**收官前置（调度方）**：W4 代码 commit 后，立即按登记单 `workorder_WR.md`（WR-a）以该 commit 的脚本 sha 追加 ACTIVE 登记 commit（四协议）；登记后以**未替换历史登记查询的真实入口**验证 `validate_repair_bundle(deep=True)` 与 `resolve_formal_cache`（自包含夹具），仅直接调 `validate_repair_bundle_deep` 或测试侧登记替身不构成正式验收；收官报告记代码 commit、登记 commit 与 sha。
