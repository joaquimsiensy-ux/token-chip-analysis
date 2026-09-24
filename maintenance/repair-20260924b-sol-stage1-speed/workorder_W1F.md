# 返修单 W1F（v1.1，行号订正）：校验器继承 recheck 见证——完整响应中未返回块头的 slot 须按值 1 参与继承条件与跨记录冲突检查 —— 归属 W1（盲审 r2 FAIL 反例修复）

> 出处：`blind_W1_reply_r2.md`（codex 盲审 r2 FAIL 唯一阻断项）：同一继承 slot 两条自报 `verified` 的完整 recheck，一条含该 slot 零 nonce 块（值 2）、一条为空响应（探针语义值 1），校验器仍 `ok=True`、`states=['INHERITED_REFUTED']`；非空完整响应缺继承 slot 同样被接受。
> 事实（调度方本机亲核，基线 `W1F_BASE=65132abda8253cf34562f92f726d311d9a32b4f8`，行号以此为准）：
> ① `scripts/lib/solana_exact_validate.py:532` `_inherited_recheck_values(row, template_sha)`：核请求摘要/模板/响应见证/摘要/size/`slots_covered==end-start+1` 后，空响应分支核 `empty_response/returned_*/n_blocks` 事实并 **`return {}`（`:567`；注意 `:536` 另有一处 `return {}` 是「非 recheck 行直接跳过」分支，语义不同，不得改）**；非空分支 `values = {}`（`:568`）只对响应中出现的块写 `values[slot] = min(255, 2 + len(instructions))`（`:578`），完整性靠 `previous == end` 等事实核（`:580-586`）——**请求区间内未返回块头的 slot 不出现在返回映射中**。
> ② `_validated_inherited(:595)` 在 `:646-653` 合并各 recheck 行的 measured（调用 `:648`）：`if slot in actual and actual[slot] != value: raise "recheck results conflict"`；`:660` 附近要求 `actual.get(slot) == 2`（施工前整行核）。由于①不返回隐含的 1，「空响应」或「非空但缺该 slot」的完整 recheck 既不触发冲突、也不使 `actual.get(slot)` 变为非 2。
> ③ 探针 `_scan_request`（`sqd_coverage_probe.py:332`）语义：空正文/空数组 → 整个请求区间 `bytes([1]) * (end-start+1)`（`:353-356`、`:365-367`）；非空 → `counts = bytearray([1]) * (covered_to-start+1)` 再覆盖块值（`:378-388`），即**完整区间内未返回块头 = 1（NO_HEADER）**。校验器必须与此一致。
> ④ 相关测试：`scripts/tests/test_sqd_coverage_probe.py` 的 `test_w1_inherited_tamper_rejection`（26 类负例，均同步重绑外层引用）与 `test_w1_inheritance_and_partial_retry_fallback`；main 显式列表。

## 0. 开工纪律
- 0.1 工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`；固定 `W1F_BASE=65132abda8253cf34562f92f726d311d9a32b4f8`；开工贴 `git status --short`（空）、`git rev-parse HEAD`、`git merge-base --is-ancestor "$W1F_BASE" HEAD`（exit 0）、`git diff --quiet "$W1F_BASE" HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets`（exit 0）。不符停工。
- 0.2 禁读同 W1 §0.2（含子进程；触及 `.staging_b3` 的用例不跑）。本目录可读：`README.md`、`workorder_W1.md`、`workorder_W1F.md`、`blind_W1_reply_r2.md`、`W1_done.md`、`review_W1F_reply_*.md`。
- 0.3 **白名单**：生产 `scripts/lib/solana_exact_validate.py`（仅 `_inherited_recheck_values`，必要时 `_validated_inherited` 的合并段）；测试 `scripts/tests/test_sqd_coverage_probe.py`；完成报告 `W1F_done.md`。
- 0.4 **不改**其他任何文件（探针不改：其语义是基准）。
- 0.5 锚整行 `grep -n -F -x` 恰 1 处；0.6 离线不 commit、禁 stash/checkout/reset、tempfile、禁批量删除。
- 0.7 定向跑：`test_sqd_coverage_probe.py`、`test_f03_sharedmap_reuse.py`、`test_batch3_solana_producers.py`、`test_reconcile_v4_receipt.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`；`test_sqd_gap_repair.py` 只跑不触及禁读夹具的用例。

## 1. 硬约束
- 1.1 `_inherited_recheck_values` 对**完整请求区间 `[start, end]` 内每个 slot** 都给出值：未返回块头的 slot＝1；返回块头的＝`min(255, 2+len(instructions))`；空响应同样返回全 1 映射（`{slot: 1 for slot in range(start, end+1)}`）。现有全部绑定/事实检查（请求摘要、模板、见证、摘要/size、`slots_covered`、空响应事实、块顺序/范围、完整响应事实）**一项不放宽**。
- 1.2 `_validated_inherited` 的冲突检查与 `actual.get(slot) == 2` 判据不变——修 ① 后，反例 A（零 nonce 块 vs 空响应）在合并段触发 `recheck results conflict`；反例 B（非空完整响应缺该 slot）同样冲突或使 `actual[slot]==1` 被 `actual.get(slot) != 2` 拒。
- 1.3 生产改动 ≤ 8 行（增删合计）；不改探针、不改 schema、不改 summary/verdict 语义；无继承路径不受影响（`_validated_inherited` 早退分支不变）。
- 1.4 recheck 区间是连续已知点小区间（canary/candidate/refuted），全区间映射规模可接受；不得为此改探针分段。

## 2. 逐条施工
- 2.1 `solana_exact_validate.py`：`        return {}` 整行在文件内多处命中（`:536/:567/:2245/:2248`），**不能作唯一锚**；以 `    values = {}`（`:568`，唯一）为锚定位函数，把其上方空响应分支的 `return {}`（`:567`）改为返回全 1 映射（如 `return {slot: 1 for slot in range(start, end + 1)}`），并把 `:568` 改为 `values = {slot: 1 for slot in range(start, end + 1)}`；`:578` 覆盖逻辑不变。`:536` 的 `return {}` 不动。
- 2.2 测试（`test_sqd_coverage_probe.py`，在 `test_w1_inherited_tamper_rejection` 内追加或新增用例并登记 main）：负例 A：同一继承 slot 两条 `recheck_outcome="verified"` 的完整 recheck 行——一条含该 slot 零 nonce 块，一条为空响应（`empty_response=True`、`returned_*=None`、`n_blocks=0`、摘要/size 与 `[]` 一致）→ `validate_coverage` 拒且 reasons 含 `inherited refuted`；负例 B：非空完整响应只含区间内更后的 slot、缺继承 slot（`returned_from` 为该后 slot、`returned_to==end`、`previous==end` 成立）→ 拒；正例：单条正确完整 recheck 仍 PASS；另一正例：两条完整 recheck 对同一 slot 值均为 2 → PASS。所有夹具同步重算 ledger 引用、coverage 摘要、probe_id、CURRENT 引用（可参考 `blind_W1_reply_r2.md` 的内存构造法，但测试须落 tempfile 并走现有夹具体系）。

## 3. 完成报告 `W1F_done.md`
首行 `# W1F 完成：…`；§0.1 输出；diff 行号与 `--numstat "$W1F_BASE"`；§0.7 尾行；披露禁读。
