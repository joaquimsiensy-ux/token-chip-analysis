# 批 2b 工单（codex 返工）：探针 SQD 分页游标 bug 修复 ＋ 分页/空响应回归（分支 fix/sqd-gap-v6520）

## Fable 本机冒烟发现（2026-08-23，ARC 缺陷区段 426,649,000–426,670,000，21,001 slot，探针 46 秒 published，verdict INCONCLUSIVE）
- 探针 summary：healthy 11,426 / header_zero_nonce 3,496 / **no_header 6,079**；getBlocks 位图 count=20,858（即链上只有 143 个真跳块）→ missing_block_candidate **5,936**。
- 与 ARC 路 A 逐块实测（`.staging_b3/routeA_full/full_slots.jsonl`＋`routeA_pilot/pilot_slots.jsonl`，同区间 4,774 slot）交叉表：
  - 3,378 (ZERO_NONCE, SQD sqd_tx>0) ✔；61 (NO_HEADER, Helius SKIPPED, sqd_tx=0) ✔；3 (ZERO_NONCE, sqd_tx=0, helius_tx>0) ✔（只含投票交易的块，SQD 不存投票）；
  - **1,332 (NO_HEADER, 路 A 实测 SQD sqd_tx>0) ✘**——SQD 明明有块。
- 直查 SQD 复现（curl，`fromBlock 426649370 toBlock 426649385`，同查询体）：返回 16 个块头（370-372 有 nonce 77/57/68，373-385 零 nonce 块头齐全）→ 正确态 HEADER_ZERO_NONCE，探针标成 NO_HEADER。
- 根因（`scripts/solana/sqd_coverage_probe.py:217-255 _scan_request`）：一次请求 [start,end]（固定 450 slot 分片）后把响应中未出现的 slot 全部标 1（NO_HEADER）、`slots_covered=end-start+1`——**未处理 SQD stream 分页**：SQD 单次响应只返回到某块为止（ledger seq=1 该请求 172KB 即截断在 ≈426649372），后续块头未取回却被判"无块头"。"≈450 slot/请求"是 ARC 诊断里单页**返回量**的经验值，不是可一次请求的固定区间。

## 修复要求
1. `_scan_request`（或其调用层）改为**游标分页循环**：对 [cur,end] 请求 → 响应块按 `header.number` 升序；设 L＝本页最后块号；本页可判定覆盖＝[cur, L]（其中未出现的 slot ⇒ NO_HEADER，出现的按 nonce 计数）；`cur=L+1`，直到 `cur>end`。**空响应**（HTTP 200、零块）⇒ [cur,end] 全部 NO_HEADER 并在该 ledger 行记 `empty_response:true`（供 validator/人工审视；getBlocks 确认与批 3 census 是兜底）。本页块号必须 ⊂[cur,end] 且严格递增唯一，否则该页 `ok:false`（不填、保持 UNSCANNED）。响应 `x-sqd-finalized-head-number` 等头部若可得则记入 ledger（非必需）。
2. ledger 逐页一行：`{seq, ts, provider, mode, query_body_sha256, from(=cur), to(=end), returned_from, returned_to, n_blocks, slots_covered(=L-cur+1 或空响应时 end-cur+1), empty_response, http_status, bytes, response_sha256, ok}`；validator 的"成功并集无洞"按 `[from, from+slots_covered-1]` 实际覆盖计算（不再等于请求区间）。`references/scan-schemas.md` §14 对应 ledger 字段如有出入只记录到 done（文档批 6 统一修），但契约草案 `sqd-solana-coverage_v1.json` 的 ledger 字段表**允许本批按本条更新**（errata 驱动小修，INDEX 记录）。
3. `--workers` 分片仍可并行（每片独立游标循环）；`--dry-run` 的预计请求数改为"下界（每页≤N slot 经验值）"并标明不确定。
4. 回归测试（`scripts/tests/test_sqd_coverage_probe.py` ＋ fixture）：新增 (a) 分页截断场景：fixture 对 [s,e] 第一页只回 [s,m] 的块（含零 nonce 块头与缺块），第二页回 [m+1,e] → 断言 counts 逐 slot 正确（零 nonce 块头=2、真缺=1、有 nonce=n+2），ledger 两行、slots_covered 之和==e-s+1；(b) 空响应场景 → 全 NO_HEADER＋`empty_response:true`；(c) 页内块号越界/乱序/重复 → 该页 ok:false、slot 保持 UNSCANNED、最终不发布 exit 2；(d) 旧行为反例：固定区间一次请求把未返回块标 NO_HEADER 的实现必须被 (a) 抓红（先在修复前跑一次 (a) 取红证，再修复转绿）。
5. `validate_coverage` 同步：ledger 成功并集按实际覆盖；`empty_response` 行计入覆盖但在 `recomputed` 中单列计数。
6. 其余不动（白名单：`scripts/solana/sqd_coverage_probe.py`、`scripts/lib/solana_exact_validate.py` coverage 段、`scripts/tests/test_sqd_coverage_probe.py`、`scripts/tests/fixtures/sqd_coverage/`、`contracts_draft/sqd-solana-coverage_v1.json`＋`INDEX.json`（仅 ledger 字段）、`batch2b_done.md`＋`batch2b_green_evidence.txt`）。不 commit、离线、完成即停。

## 验收（Fable 本机）
重跑同一缺陷区段冒烟：预期 no_header ≈ 143（真跳块）＋极少数，与路 A 交叉表不得再出现 (NO_HEADER, sqd_tx>0)；`validate_coverage` ok；再跑健康区段与 NO_HEADER 小区段；三段通过后 commit 并起 ARC 全区间后台扫。
