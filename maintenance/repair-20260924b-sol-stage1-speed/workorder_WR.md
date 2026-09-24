# 登记单 WR（模板 v2）：`scripts/lib/producer_history.py` 追加 9.2.0 生产者 ACTIVE 条目 —— WR-a 在 W4 源码提交后、W4 最终收官前登记 repair；WR-b 在 W2 源码提交后、工程最终收官前登记 probe

> 出处：W4 复核 r1 第 7 条（未登记的新 repair producer 会被正式 resolver `sqd_cache_identity.py:143-147` 拒绝，登记须在 W4 收官前置）；W2 复核 r1 第 2 条（W2 自身改探针文件哈希，登记只能在其 commit 之后）。
> 事实：`producer_history.py:3-6` 登记纪律；元组闭合整行 `)` 在 `:283`（派工时重核）；现役条目 probe `c4980c98…`（commit `cdc4f87f…`）× coverage/v1、coverage-pointer/v1；repair `3f89aab1…`（commit `7846184f…`）× cache/v4、repair-bundle/v1、coverage-resolution/v1、repair-pointer/v1；均 ACTIVE。**无 shared-map 历史条目，本单不新增该协议条目。**

## 派工时由调度方填入
- `<TARGET_SCRIPT>`：`scripts/solana/sqd_gap_repair.py`（WR-a）或 `scripts/solana/sqd_coverage_probe.py`（WR-b）
- `<CODE_COMMIT>`：该脚本最后一次改动的施工 commit（完整 40 位）
- `<SHA256>`：`git show <CODE_COMMIT>:<TARGET_SCRIPT> | shasum -a 256` 结果
- `<REASON>`：WR-a「9.2.0 α 修复状态探针并入 census 请求（W4）」；WR-b「9.2.0 驳回继承导出/继承（W1）＋find-known-map（W2）」

## 纪律
- 0.1 树干净、HEAD＝`<CODE_COMMIT>` 或其后代；禁读同 W1 §0.2；白名单仅 `scripts/lib/producer_history.py` 与 `WR-<a|b>_done.md`；离线、不 commit。
- 0.2 施工者先复算 `<SHA256>`（`git show <CODE_COMMIT>:<TARGET_SCRIPT> | shasum -a 256`）并与工作树文件 `shasum -a 256 <TARGET_SCRIPT>` 比对，两者与工单填值三方一致才写入；不一致停工。
- 0.3 在元组闭合 `)` 前追加：WR-a 四条（cache/v4、repair-bundle/v1、coverage-resolution/v1、repair-pointer/v1）或 WR-b 两条（coverage/v1、coverage-pointer/v1），字段与现有条目同构（script/sha256/commit/protocol/status ACTIVE/reason），保留全部既有条目不改。
- 0.4 定向跑：`test_batch3_solana_producers.py`、`test_sqd_gap_repair.py`（不触及禁读夹具的用例）、`test_sqd_coverage_probe.py`、`test_f03_sharedmap_reuse.py`、`invariant_scan.py`；贴尾行。
- 0.6 调度顺序：W4 源码 commit → WR-a 复算并追加四协议 → 调度方登记 commit → 真实注册表入口验收 → W4 收官；W2 源码 commit → WR-b 复算并追加两协议 → 调度方登记 commit → 工程最终验收。施工者不 commit。
- 0.7 WR-a 正式验收沿用 W4 §3：自包含夹具通过**未替换** `historical_producer_hashes` 的 `validate_repair_bundle(deep=True)` 与 `resolve_formal_cache`（`test_sqd_gap_repair.py:322-330` 既有用例替换了历史注册查询，其通过不能独自证明登记有效）；仅测试尾行或直接调用深验 helper 不替代这项验收。WR-b 核对最终 probe sha 同时进入 coverage/v1 与 coverage-pointer/v1 的真实 ACTIVE 查询结果。完成报告记录源码 commit、登记 commit、sha 与实际验收结果；缺项写待验收。
- 0.8 W1 过渡 probe：调度方在 WR-b 派工前核查 W1 收官版本探针是否产生过需保留、继续重验的正式 coverage/pointer；若无，在 WR-b_done 明记「W1 过渡版本仅作施工测试，无需保留的正式产物」；若有，另列其源码 commit、可复算 sha 与产物范围，补独立登记单追加 coverage/v1、coverage-pointer/v1。WR-b 的两条最终 probe 登记不得表述为已覆盖 W1 过渡哈希。
- 0.5 完成报告首行 `# WR-<a|b> 完成：…`，含复算记录、diff 行数、测试尾行。
