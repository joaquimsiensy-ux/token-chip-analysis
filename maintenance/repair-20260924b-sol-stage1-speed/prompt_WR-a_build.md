# WR-a 施工提示词（codex --write）
## 纪律（优先级高于工单）
1. 你是施工者。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**只按下方登记单 WR-a v2（已通过两轮 codex 复核）施工**：白名单仅 `scripts/lib/producer_history.py`（在元组闭合 `)` 前同构追加四条 ACTIVE 条目，保留全部既有条目不改）与完成报告 `maintenance/repair-20260924b-sol-stage1-speed/WR-a_done.md`。停工条件触发即停工写报告。
2. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程与测试（`test_sqd_gap_repair.py` 触及 `.staging_b3` 的用例不要运行，可用 `unittest.mock.patch.object` 临时跳过，报告列为「未运行，调度方本机补验」）。
3. 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree；临时目录只用系统 tempfile；禁止批量删除。
4. 写入前按 0.2 三方比对 sha（`git show "<CODE_COMMIT>:scripts/solana/sqd_gap_repair.py" | shasum -a 256`、工作树 `shasum`、工单填值）；不一致停工。
5. 0.7 正式入口验收由调度方在登记 commit 后执行，**你不做**；0.4 的 `test_producer_registry_current.py` 你必跑并逐项判读（预期尾行 `producer registry: 2 FAIL`，仅 probe 两协议）。
6. 完成报告首行 `# WR-a 完成：…`，含复算记录、diff 行数、各测试尾行与剩余失败明细，**并把报告全文放在最终答复消息里**。

---

# 以下为登记单 WR-a v2 全文

# 登记单 WR-a v2（由模板 v2 填实并吸收复核 r1，2026-09-24）：`scripts/lib/producer_history.py` 追加 9.2.0 repair 生产者四协议 ACTIVE 条目

> 填实值：`<TARGET_SCRIPT>`＝`scripts/solana/sqd_gap_repair.py`；`<CODE_COMMIT>`＝`59f88b84c9ab9eeb95c92a15e342d8cbe09925db`（W4 施工 commit）；`<SHA256>`＝`15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33`（调度方按 `git show <CODE_COMMIT>:<TARGET_SCRIPT> | shasum -a 256` 复算，与工作树 `shasum` 及 W4_done.md 自报值三方一致）；`<REASON>`＝「9.2.0 α/β 候选修复状态探针并入 census 请求（W4）」（复核 r1 建议：W4 覆盖 α/β 共用修复流程）；完成报告文件名 `WR-a_done.md`；元组闭合 `)` 现为 `producer_history.py:283`（派工时已重核）。本单只做 WR-a，不含 WR-b。

> v2 变更（吸收 `review_WR-a_reply_r1.md`）：必改 1——0.4 加入 `test_producer_registry_current.py` 及逐项判据与 WR-a 阶段预期失败范围；建议——`<REASON>` 改为 α/β；0.7 补明正式入口调用、参数与断言（调度方一次性验收运行器执行，不改生产文件与既有测试）；纪律编号 0.5 位置不动。

以下为模板 v2 全文（已按 v2 变更就地修订），占位符按上述填实值理解。

---

# 登记单 WR（模板 v2）：`scripts/lib/producer_history.py` 追加 9.2.0 生产者 ACTIVE 条目 —— WR-a 在 W4 源码提交后、W4 最终收官前登记 repair；WR-b 在 W2 源码提交后、工程最终收官前登记 probe

> 出处：W4 复核 r1 第 7 条（未登记的新 repair producer 会被正式 resolver `sqd_cache_identity.py:143-147` 拒绝，登记须在 W4 收官前置）；W2 复核 r1 第 2 条（W2 自身改探针文件哈希，登记只能在其 commit 之后）。
> 事实：`producer_history.py:3-6` 登记纪律；元组闭合整行 `)` 在 `:283`（派工时重核）；现役条目 probe `c4980c98…`（commit `cdc4f87f…`）× coverage/v1、coverage-pointer/v1；repair `3f89aab1…`（commit `7846184f…`）× cache/v4、repair-bundle/v1、coverage-resolution/v1、repair-pointer/v1；均 ACTIVE。**无 shared-map 历史条目，本单不新增该协议条目。**

## 派工时由调度方填入
- `<TARGET_SCRIPT>`：`scripts/solana/sqd_gap_repair.py`（WR-a）或 `scripts/solana/sqd_coverage_probe.py`（WR-b）
- `<CODE_COMMIT>`：该脚本最后一次改动的施工 commit（完整 40 位）
- `<SHA256>`：`git show <CODE_COMMIT>:<TARGET_SCRIPT> | shasum -a 256` 结果
- `<REASON>`：WR-a「9.2.0 α/β 候选修复状态探针并入 census 请求（W4）」；WR-b「9.2.0 驳回继承导出/继承（W1）＋find-known-map（W2）」

## 纪律
- 0.1 树干净、HEAD＝`<CODE_COMMIT>` 或其后代；禁读同 W1 §0.2；白名单仅 `scripts/lib/producer_history.py` 与 `WR-<a|b>_done.md`；离线、不 commit。
- 0.2 施工者先复算 `<SHA256>`（`git show <CODE_COMMIT>:<TARGET_SCRIPT> | shasum -a 256`）并与工作树文件 `shasum -a 256 <TARGET_SCRIPT>` 比对，两者与工单填值三方一致才写入；不一致停工。
- 0.3 在元组闭合 `)` 前追加：WR-a 四条（cache/v4、repair-bundle/v1、coverage-resolution/v1、repair-pointer/v1）或 WR-b 两条（coverage/v1、coverage-pointer/v1），字段与现有条目同构（script/sha256/commit/protocol/status ACTIVE/reason），保留全部既有条目不改。
- 0.4 定向跑：`test_batch3_solana_producers.py`、`test_sqd_gap_repair.py`（不触及禁读夹具的用例）、`test_sqd_coverage_probe.py`、`test_f03_sharedmap_reuse.py`、`invariant_scan.py`；贴尾行。**另必跑 `python3 -B scripts/tests/test_producer_registry_current.py`（直接检验本单登记结果）并逐项判读**：追加后 repair 四协议（cache/v4、repair-bundle/v1、coverage-resolution/v1、repair-pointer/v1）的当前哈希检查须全部 `ok`，四条新增登记的 Git 复现检查须全部通过；WR-b 尚未执行时**只允许** probe 的 coverage/v1、coverage-pointer/v1 两项 FAIL，预期尾行 `producer registry: 2 FAIL`、退出码 1；报告须列出剩余失败项明细，不得只贴尾行或把整个守卫记作 PASS；出现任何其他失败即停工。
- 0.6 调度顺序：W4 源码 commit → WR-a 复算并追加四协议 → 调度方登记 commit → 真实注册表入口验收 → W4 收官；W2 源码 commit → WR-b 复算并追加两协议 → 调度方登记 commit → 工程最终验收。施工者不 commit。
- 0.7 WR-a 正式验收沿用 W4 §3（**由调度方在登记 commit 后以一次性验收运行器执行**，复用 `test_sqd_gap_repair.py` W4 三类证据用例的自包含构造器，在夹具临时目录仍存在时用真实模块调用：`identity.validate_repair_bundle(gen/"bundle.json", deep=True, case_root=case, current_base={"edge_sha256": repair.sha256_file(base_edge)})`（`base_edge` 为本案规范 base 文件）与 `edge, meta, kind, gid, binding = identity.resolve_formal_cache(MINT, case)`，断言 `kind=="repaired"`、`gid==bundle["gid"]`、`binding["cache_kind"]=="repaired"`，并核 edge/meta 指向 CURRENT 所选代；三类产物（全旧/全新/混合）各做一次；不修改生产文件与既有测试）：自包含夹具通过**未替换** `historical_producer_hashes` 的 `validate_repair_bundle(deep=True)` 与 `resolve_formal_cache`（`test_sqd_gap_repair.py:322-330` 既有用例替换了历史注册查询，其通过不能独自证明登记有效）；仅测试尾行或直接调用深验 helper 不替代这项验收。WR-b 核对最终 probe sha 同时进入 coverage/v1 与 coverage-pointer/v1 的真实 ACTIVE 查询结果。完成报告记录源码 commit、登记 commit、sha 与实际验收结果；缺项写待验收。
- 0.8 W1 过渡 probe：调度方在 WR-b 派工前核查 W1 收官版本探针是否产生过需保留、继续重验的正式 coverage/pointer；若无，在 WR-b_done 明记「W1 过渡版本仅作施工测试，无需保留的正式产物」；若有，另列其源码 commit、可复算 sha 与产物范围，补独立登记单追加 coverage/v1、coverage-pointer/v1。WR-b 的两条最终 probe 登记不得表述为已覆盖 W1 过渡哈希。
- 0.5 完成报告首行 `# WR-<a|b> 完成：…`，含复算记录、diff 行数、测试尾行。
