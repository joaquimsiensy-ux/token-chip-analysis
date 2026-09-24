# 登记单 WR（模板）：`scripts/lib/producer_history.py` 追加 9.2.0 生产者 ACTIVE 条目 —— 分两次派工（WR-a：W4 收官后登记 repair；WR-b：W2 收官后登记 probe）

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
- 0.5 完成报告首行 `# WR-<a|b> 完成：…`，含复算记录、diff 行数、测试尾行。
