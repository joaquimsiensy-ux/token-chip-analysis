# WR-b 施工提示词（codex --write）
## 纪律（优先级高于工单）
1. 你是施工者。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**只按下方登记单 WR-b v2（v1 通过 codex 复核 r1，v2 仅吸收其四条模板残留清理）施工**：白名单仅 `scripts/lib/producer_history.py`（在元组闭合 `)` 前同构追加两条 ACTIVE 条目（coverage/v1、coverage-pointer/v1），保留全部既有条目不改）与完成报告 `maintenance/repair-20260924b-sol-stage1-speed/WR-b_done.md`。停工条件触发即停工写报告。
2. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程与测试（`test_sqd_coverage_probe.py` 触及 `.staging_b3` 的用例不要运行，可用 `unittest.mock.patch.object` 临时跳过，报告列为「未运行，调度方本机补验」）。
3. 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree；临时目录只用系统 tempfile；禁止批量删除。
4. 写入前按 0.2 三方比对 sha（`git show "<CODE_COMMIT>:scripts/solana/sqd_coverage_probe.py" | shasum -a 256`、工作树 `shasum`、工单填值）；不一致停工。
5. 0.7 正式入口验收由调度方在登记 commit 后执行，**你不做**；0.4 的 `test_producer_registry_current.py` 你必跑并逐项判读（预期 **0 FAIL、退出码 0**，任何 FAIL 即停工）。
6. 完成报告首行 `# WR-b 完成：…`，含复算记录、diff 行数、各测试尾行与剩余失败明细，**并把报告全文放在最终答复消息里**。

---

# 以下为登记单 WR-b v2 全文

# 登记单 WR-b v2（v1 填实＋吸收复核 r1 四条模板残留清理，2026-09-24）：`scripts/lib/producer_history.py` 追加 9.2.0 probe 生产者两协议 ACTIVE 条目

> 填实值：`<TARGET_SCRIPT>`＝`scripts/solana/sqd_coverage_probe.py`；`<CODE_COMMIT>`＝`f78b5c4575ebe1db36f2cf3a96e75b79731f3fc6`（W2 施工 commit，该脚本最后一次改动）；`<SHA256>`＝`d4adc0c88f87bc03b3d847db7df9c9f7e588cb503734dfd977b818b581d998d8`（调度方按 `git show "<CODE_COMMIT>:<TARGET_SCRIPT>" | shasum -a 256` 复算，与工作树 `shasum` 及 W2_done.md 自报值三方一致）；`<REASON>`＝「9.2.0 驳回继承导出/继承（W1）＋find-known-map（W2）」；完成报告文件名 `WR-b_done.md`；元组闭合 `)` 现为 `producer_history.py:315`（WR-a 追加 32 行后，派工时已重核）。本单只做 WR-b：追加 **两条**（`sqd-solana-coverage/v1`、`sqd-solana-coverage-pointer/v1`），不动 WR-a 已登记的四条 repair 条目与其余既有条目。

> §0.8 前置核查结论（调度方已做，见 `W2_acceptance.md`）：W1 过渡版本探针（哈希 `ab2371f5…`）在全部案卷与仓库 assets 零命中，**仅作施工测试，无需保留的正式产物**；本单两条登记不表述为覆盖过渡哈希。

> 0.4 判据改为 WR-b 版：追加后 `test_producer_registry_current.py` 须 **0 FAIL、退出码 0**（repair 四协议已由 WR-a 登记）；出现任何 FAIL 即停工。0.7 改为 WR-b 版：核对最终 probe sha 同时进入 coverage/v1 与 coverage-pointer/v1 的真实 ACTIVE 查询结果（`historical_producer_hashes` 未替换），并用 `test_sqd_coverage_probe.py` 自包含发布用例产物跑一次真实 `solana_exact_validate.validate_coverage`（现役 sha 判据 `:712-716`）确认 producer 判据通过——由调度方或写模式验收任务执行。

以下为模板 v2 全文（已按 v2 变更就地修订），占位符按上述填实值理解。

---

# 登记单 WR（模板 v2）：`scripts/lib/producer_history.py` 追加 9.2.0 生产者 ACTIVE 条目 —— WR-a 在 W4 源码提交后、W4 最终收官前登记 repair；WR-b 在 W2 源码提交后、工程最终收官前登记 probe

> 出处：W4 复核 r1 第 7 条（未登记的新 repair producer 会被正式 resolver `sqd_cache_identity.py:143-147` 拒绝，登记须在 W4 收官前置）；W2 复核 r1 第 2 条（W2 自身改探针文件哈希，登记只能在其 commit 之后）。
> 事实：`producer_history.py:3-6` 登记纪律；元组闭合整行 `)` 在 `:315`（WR-b 派工时重核）；现役条目 probe `c4980c98…`（commit `cdc4f87f…`）× coverage/v1、coverage-pointer/v1；repair 最新登记 `15822564…`（WR-a，commit `59f88b8…`）四协议，历史 `3f89aab1…`（commit `7846184f…`）四协议保持 ACTIVE；均 ACTIVE。**无 shared-map 历史条目，本单不新增该协议条目。**

## 派工时由调度方填入
- `<TARGET_SCRIPT>`：`scripts/solana/sqd_gap_repair.py`（WR-a）或 `scripts/solana/sqd_coverage_probe.py`（WR-b）
- `<CODE_COMMIT>`：该脚本最后一次改动的施工 commit（完整 40 位）
- `<SHA256>`：`git show <CODE_COMMIT>:<TARGET_SCRIPT> | shasum -a 256` 结果
- `<REASON>`：WR-a「9.2.0 α/β 候选修复状态探针并入 census 请求（W4）」（本单不用）；WR-b「9.2.0 驳回继承导出/继承（W1）＋find-known-map（W2）」

## 纪律
- 0.1 树干净、HEAD＝`<CODE_COMMIT>` 或其后代；禁读同 W1 §0.2；白名单仅 `scripts/lib/producer_history.py` 与 `WR-<a|b>_done.md`；离线、不 commit。
- 0.2 施工者先复算 `<SHA256>`（`git show <CODE_COMMIT>:<TARGET_SCRIPT> | shasum -a 256`）并与工作树文件 `shasum -a 256 <TARGET_SCRIPT>` 比对，两者与工单填值三方一致才写入；不一致停工。
- 0.3 在元组闭合 `)` 前追加：WR-a 四条（cache/v4、repair-bundle/v1、coverage-resolution/v1、repair-pointer/v1）或 WR-b 两条（coverage/v1、coverage-pointer/v1），字段与现有条目同构（script/sha256/commit/protocol/status ACTIVE/reason），保留全部既有条目不改。
- 0.4 定向跑：`test_batch3_solana_producers.py`、`test_sqd_gap_repair.py`（不触及禁读夹具的用例）、`test_sqd_coverage_probe.py`、`test_f03_sharedmap_reuse.py`、`invariant_scan.py`；贴尾行。**另必跑 `python3 -B scripts/tests/test_producer_registry_current.py`（直接检验本单登记结果）并逐项判读**：追加后 probe 两协议（coverage/v1、coverage-pointer/v1）的当前哈希检查须 `ok`，两条新增登记的 Git 复现检查须通过；repair 四协议已由 WR-a 登记，故整体须 **0 FAIL、退出码 0**（预期尾行 `producer registry: 0 FAIL`）；报告贴逐项明细；出现任何 FAIL 即停工。
- 0.6 调度顺序：W4 源码 commit → WR-a 复算并追加四协议 → 调度方登记 commit → 真实注册表入口验收 → W4 收官；W2 源码 commit → WR-b 复算并追加两协议 → 调度方登记 commit → 工程最终验收。施工者不 commit。
- 0.7 WR-b 正式验收（**由调度方在登记 commit 后以写模式验收任务执行**，施工者不做）：① 用真实 `historical_producer_hashes`（未替换）分别查询 `sqd-solana-coverage/v1` 与 `sqd-solana-coverage-pointer/v1`，断言最终 probe sha `d4adc0c8…` 同时在两个协议的 ACTIVE 结果中；② 复用 `test_sqd_coverage_probe.py` 自包含发布用例（`:205` 附近或 `_w1_run`/`_w1_check` 动态夹具）在 tempfile 存续期间跑一次真实 `solana_exact_validate.validate_coverage`，断言 ok=True——注意校验器 `:712-722` 允许当前源码 sha 直接通过，故 ② 只证兼容、① 才证登记有效，两者缺一不可；③ 对照：仅内存移除本次两条登记后 ① 须查不到该 sha。WR-a 的 `validate_repair_bundle(deep=True)`/`resolve_formal_cache` 入口属 repair 验收，已在 `WR-a_formal_entry.md` 完成，本单不重复。完成报告
- 0.8 W1 过渡 probe：调度方在 WR-b 派工前核查 W1 收官版本探针是否产生过需保留、继续重验的正式 coverage/pointer；若无，在 WR-b_done 明记「W1 过渡版本仅作施工测试，无需保留的正式产物」；若有，另列其源码 commit、可复算 sha 与产物范围，补独立登记单追加 coverage/v1、coverage-pointer/v1。WR-b 的两条最终 probe 登记不得表述为已覆盖 W1 过渡哈希。
- 0.5 完成报告首行 `# WR-<a|b> 完成：…`，含复算记录、diff 行数、测试尾行。
