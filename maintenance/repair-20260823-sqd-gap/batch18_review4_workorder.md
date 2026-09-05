# 批 18 第四轮盲审消化工单 b18r4:signature_discovery 早退透传 sig 史 complete

基线:main=ad44909(v7.0.0,已 push)。第四轮盲审(base=50d7767)仅 1 条 P2,已亲核属实。
版本:7.0.0 → **7.0.1**(既定契约内修复,修订位,符合 4A 版本规则)。

## 发现(P2,亲核锚点)
`scripts/solana/audit_closed_accounts.py:397-404`:mode=sigs 时 `fetch_mint_sigs` 返回 `(sigs, complete, wall_hit)`——`complete=True` 表示签名史查询完整跑完且成功签名结果为空(**措辞精度,复核定**:函数过滤失败笔,不得表述为"链上绝对没有任何历史";RED/done/CHANGELOG 同此口径),`False` 表示因翻页上限/墙钟截断(可能是拉取失败)。空 `sigs` 早退分支(:401-404)在 `state.update` 时塞的是**初始** `sig_stat`(`{"total":0,"complete":None,"in_range":0}`,:406 才写真值),早退报告 `mint_sig_history.complete` 恒 `null`,丢失"真空历史 vs 拉取失败"的诊断区分。

## 修法(唯一生产改动点)
:401 早退分支的 `state.update` 中 `"sig_stat"` 改为 `{"total": 0, "complete": complete, "in_range": 0}`(把 :397 拿到的 `complete` 如实透传;其余键保持 0 语义不变)。不改 fetch_mint_sigs、不改 builder、不改其他 bail 点。

## 测试(先红后绿)
`scripts/tests/test_batch18_review_digest.py` 既有 signature_discovery bail 契约测试(或紧邻新增一个断言组)覆盖两态:
- R1 红:mock `fetch_mint_sigs` 返回 `([], True, False)`(完整查询、真空历史)→ 基线报告 `mint_sig_history.complete` 为 `null`(红证据原文);修后为 `true`。
- N1:mock 返回 `([], False, False)`(截断/失败)→ 修后 `complete` 为 `false`;`sampling_phase="signature_discovery"`、`counts_complete=false`、直接原因"mint 签名史为空/拉取失败"等既有断言不变。
- 断言写法(复核建议,采纳):两态各取完整报告后一次性断言 `report["mint_sig_history"] == {"total": 0, "complete": expected, "in_range": 0}`,两态结果成对 `[True, False]`,RED 原文同时证明两态。
- 既有 146 全绿(run_all.py 不改,分母 146);test_repair_batch_d.py 禁改;blocks/auto 及其他早退分支的 `complete=null` 是正确的"不适用",禁止扩大改动面。

## 纪律
- 白名单:`scripts/solana/audit_closed_accounts.py`(仅 :401-404 一处)、`scripts/tests/test_batch18_review_digest.py`、`VERSION`、`pyproject.toml`、`SKILL.md`(:23)、`CHANGELOG.md`(7.0.1 六栏)、本目录 batch18_review4_red_evidence.txt / batch18_review4_done.md。
- 红证据先于生产改动;完工不 commit;其余禁改同前批。
