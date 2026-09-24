# W1F 施工提示词（codex --write）
## 纪律（优先级高于工单）
1. 你是施工者。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**只按下方返修单 W1F（v2，已通过两轮复核）施工**，不扩展范围；工单内「停工」条件触发即停工写报告。
2. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读纪律同样适用于你运行的子进程与测试（触及 `.staging_b3` 的用例不要运行，报告列为「未运行，调度方本机补验」）。
3. 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree；只写工单白名单文件与完成报告；临时目录只用系统 tempfile；禁止批量删除。
4. 完成报告写到 `maintenance/repair-20260924b-sol-stage1-speed/W1F_done.md`，**并把报告全文放在最终答复消息里**。停工同样写报告并说明原因。
5. 先通读工单与目标函数再动手；修法严格按工单两处整行锚（改前 `grep -n -F -x` 确认各恰命中 1 处）；改完即跑工单 §0.7 定向测试。

---

# 以下为返修单 W1F v2 全文

# 返修单 W1F（v2）：校验器继承 recheck 见证——完整响应中未返回块头的 slot 须按值 1 参与继承条件与跨记录冲突检查（**全部事实检查通过后再补齐映射**）—— 归属 W1（盲审 r2 FAIL 反例修复）

> v2 变更：吸收 codex 复核 r1（`review_W1F_reply_r1.md`）5 条——必改 1（修法改为事实检查后补值，不预填，保住 `returned_from` 首块绑定）、2（负例 B 保留正确证明；断言完整冲突理由；补首块事实回归与 helper 解码正例）、3（事实②③行号订正）、4（§0.5/0.6 纪律表述）与建议 5（§1.4 去掉「小区间」断言）全采纳。
> 出处：`blind_W1_reply_r2.md`（codex 盲审 r2 FAIL 唯一阻断项）：同一继承 slot 两条自报 `verified` 的完整 recheck，一条含该 slot 零 nonce 块（值 2）、一条为空响应（探针语义值 1），校验器仍 `ok=True`、`states=['INHERITED_REFUTED']`；非空完整响应缺继承 slot 同样被接受。
> 事实（调度方本机亲核，基线 `W1F_BASE=65132abda8253cf34562f92f726d311d9a32b4f8`，行号以此为准）：
> ① `scripts/lib/solana_exact_validate.py:532` `_inherited_recheck_values(row, template_sha)`：核请求摘要/模板/响应见证/摘要/size/`slots_covered==end-start+1` 后，空响应分支核 `empty_response/returned_*/n_blocks` 事实并 **`return {}`（`:567`；注意 `:536` 另有一处 `return {}` 是「非 recheck 行直接跳过」分支，语义不同，不得改）**；非空分支 `values = {}`（`:568`）只对响应中出现的块写 `values[slot] = min(255, 2 + len(instructions))`（`:578`），完整性靠 `previous == end` 等事实核（`:580-586`）——**请求区间内未返回块头的 slot 不出现在返回映射中**。
> ② `_validated_inherited` 定义于 `solana_exact_validate.py:589`；`:644` 初始化 actual，`:648` 获取 measured，`:649-652` 合并并拒绝冲突（冲突判据与抛错 `:650-651`）；`:656-657` 要求本案 counts 与 actual 中该 slot 的值均为 2。当前 helper 不返回缺失块头对应的隐含值 1，故另一条记录留下的值 2 可以逃过冲突检查。
> ③ 探针 `_scan_request` 定义于 `sqd_coverage_probe.py:332`：特定 HTTP 200 空正文解码错误分支在 `:343-357` 处理并于 `:357` 返回全 1；空数组分支于 `:366-368` 返回全 1；非空响应以末块确定 `covered_to`（`:383`），`:384` 初始化全 1，再于 `:385-389` 覆盖实际返回块的值。**仅当响应覆盖至请求 end 时**，才能把整个请求区间的缺失块头解释为 1；短返回不能据此推定未覆盖尾部。校验器必须与此一致。
> ④ 相关测试：`scripts/tests/test_sqd_coverage_probe.py` 的 `test_w1_inherited_tamper_rejection`（26 类负例，均同步重绑外层引用）与 `test_w1_inheritance_and_partial_retry_fallback`；main 显式列表。

## 0. 开工纪律
- 0.1 工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`；固定 `W1F_BASE=65132abda8253cf34562f92f726d311d9a32b4f8`；开工贴 `git status --short`（空）、`git rev-parse HEAD`、`git merge-base --is-ancestor "$W1F_BASE" HEAD`（exit 0）、`git diff --quiet "$W1F_BASE" HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets`（exit 0）。不符停工。
- 0.2 禁读同 W1 §0.2（含子进程；触及 `.staging_b3` 的用例不跑）。本目录可读：`README.md`、`workorder_W1.md`、`workorder_W1F.md`、`blind_W1_reply_r2.md`、`W1_done.md`、`review_W1F_reply_*.md`。
- 0.3 **白名单**：生产 `scripts/lib/solana_exact_validate.py`（仅 `_inherited_recheck_values`，必要时 `_validated_inherited` 的合并段）；测试 `scripts/tests/test_sqd_coverage_probe.py`；完成报告 `W1F_done.md`。
- 0.4 **不改**其他任何文件（探针不改：其语义是基准）。
- 0.5 修改前使用唯一完整语义行执行 `grep -n -F -x`，须恰命中 1 处；不得使用重复的 `return {}` 作为唯一锚。
- 0.6 离线、不 commit，禁 stash/checkout/reset；测试临时夹具仅使用系统 `tempfile`，不得使用禁读目录；环境不允许创建临时目录时，停止对应测试并如实报告；禁止批量删除。
- 0.7 定向跑：`test_sqd_coverage_probe.py`、`test_f03_sharedmap_reuse.py`、`test_batch3_solana_producers.py`、`test_reconcile_v4_receipt.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`；`test_sqd_gap_repair.py` 只跑不触及禁读夹具的用例。

## 1. 硬约束
- 1.1 `_inherited_recheck_values` 对**完整请求区间 `[start, end]` 内每个 slot** 都给出值：未返回块头的 slot＝1；返回块头的＝`min(255, 2+len(instructions))`；空响应同样返回全 1 映射。**补值必须发生在全部事实检查之后**（请求摘要、模板、见证、摘要/size、`slots_covered`、空响应事实、块顺序/范围、完整响应事实含 `returned_from == 首个实际返回块`），一项不放宽、不预填。
- 1.2 `_validated_inherited` 的冲突检查与 `actual.get(slot) == 2` 判据不变——修 ① 后，反例 A（零 nonce 块 vs 空响应）在合并段触发 `recheck results conflict`；反例 B（非空完整响应缺该 slot）同样冲突或使 `actual[slot]==1` 被 `actual.get(slot) != 2` 拒。
- 1.3 生产改动 ≤ 8 行（增删合计）；不改探针、不改 schema、不改 summary/verdict 语义；无继承路径不受影响（`_validated_inherited` 早退分支不变）。
- 1.4 recheck 请求按 canary/candidate/refuted 并集的连续区间生成（`_recheck_known_slots:582`），当前没有固定区间宽度上限；映射规模与所处理区间长度相关，不得宣称恒为小区间。本单不改探针分段，不为压缩映射而忽略缺失 slot 或案外重叠冲突。

## 2. 逐条施工
- 2.1 `solana_exact_validate.py`：保持 `values = {}`（`:568`）、逐块赋值（`:578`）及全部事实检查（`:580-585`）不变。以唯一整行 `            raise ValueError("empty recheck response facts invalid")`（`:566`）定位，将紧随其后的空响应 `return {}`（`:567`）改为 `return {slot: 1 for slot in range(start, end + 1)}`。以唯一整行 `    return values`（`:586`）定位，改为 `return {slot: values.get(slot, 1) for slot in range(start, end + 1)}`。非目标行早退（`:536`）不动；不改 `_validated_inherited`。增删合计 4 行。
- 2.2 在现有 tempfile 夹具体系内构造下列用例（`test_sqd_coverage_probe.py`；复用 `_w1_reseal` 同步更新 ledger、成功区间摘要、probe_id、CURRENT 引用及代目录）；新增函数登记 main：
  - 负例 A：保留继承 slot（如 500）的正确完整 recheck，追加请求 `[500,500]`、响应 `[]` 的完整行（空响应事实及摘要/size 全部正确）。
  - 负例 B：保留上述正确行，追加请求 `[500,501]`、仅返回 slot 501 的完整非空行，正确设置 `returned_from=returned_to=501`、`slots_covered=2`、`n_blocks=1`、`empty_response=False`，重算查询摘要及响应摘要/size。
  - A/B 均自报 `verified`；基线（W1F_BASE）应接受、修复后必须拒收，且 reasons 包含**完整理由 `inherited refuted recheck results conflict`**，不得因响应事实错误提前拒收。
  - 正例：单条正确完整证明；两条对同一继承 slot 均证明值 2 的完整记录。断言不存在引用、摘要、seq 或 probe_id 错误。
  - 首块事实负例：请求起点早于首个返回块，却将 `returned_from` 伪报为请求起点 → 必须拒收（防止预填式修法）。
  - helper 解码正例：完整非空响应存在前缀空洞时，正确的 `returned_from` 通过事实检查，缺失 slot 返回 1（该正例只测 helper 解码，不冒充正常探针生成的 `verified` 发布产物——正常生产者不会把缺 canary/candidate/refuted 块头的响应标成 verified）。
  - 保留既有跨案边界、canary、部分继承、失败后重试和 unverified 排除回归。

## 3. 完成报告 `W1F_done.md`
首行 `# W1F 完成：…`；§0.1 输出；diff 行号与 `--numstat "$W1F_BASE"`；§0.7 尾行；披露禁读。
