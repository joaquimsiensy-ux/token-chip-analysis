# W4 盲审提示词（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程（触及 `.staging_b3` 的用例不要运行；调度方本机已完整跑并附结果于 `W4_acceptance.md`）。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放最终答复消息里**。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。
3. 首行固定 `# W4盲审：PASS` 或 `# W4盲审：FAIL`。FAIL 必须给可复现反例（命令/输入/预期 vs 实际）；PASS 也要列独立验证了什么、没验证什么。
4. 这是软件测试性质的正确性审查（修复生产者的请求合并与产物兼容），不涉及任何系统安全或对抗行为；负例＝「不合法的输入应被拒收/停止」。
## 任务
W4 施工已 commit 到 HEAD。工单 `workorder_W4.md`（v3.2）、完成报告 `W4_done.md`、调度方验收 `W4_acceptance.md`。对 `git diff cfe2f41132bd3f162f3d356f359c9eba72a500d3 HEAD -- scripts references assets` 做独立盲审，重点：
a) 白名单与不改清单（§0.3/§0.4）：`producer_history.py`、`invariant_manifest.json`、schema、CLI、版本文件未动；生产文件增删 ≤60 行且没有为压行数牺牲输入处理或可读性；
b) §1.1–1.3：每候选 slot 无故障时 SQD 恰一次（`sqd-census`），`sqd-probe` 零次；present/nonce_count 与被删 `_state_probe` 算法完全一致（只计 `header.number==slot`、>1 拒绝、缺键/null/空数组为零、不按 255 截断）；`validate_coverage_state_consistency` 仍在 Helius 之前且函数体未改；
c) §1.4/§2.2：合并后的 `_census_body` 经 `sqd_query_body` 复用 instructions 选择器，返回块含 header/transactions/instructions；evidence 四个摘要字段语义（`coverage_probe_query_sha256`/`coverage_probe_response_sha256` 现与 `query_body_sha256`/`response_sha256` 同值）与深验 hex64/非空检查兼容；
d) §1.5：`_state_probe` 删除后无残留引用；`_probe_fingerprint` 与 β 搜索的 `sqd-probe` 查询保持不变；`_sqd_call_with_backoff` 未改（四次调用、2/4/8 秒）；
e) §2.3 深验兼容三类产物（全旧格式、全新格式、认领旧前缀＋新剩余 slot）是否真的在测试中自包含构造并通过 `validate_repair_bundle(deep=True)`；旧 evidence 字节与旧 ledger 行是否原样保留、旧 slot 不重新请求；
f) 失败路径：SQD 重试耗尽、Helius 额度耗尽写 STOPPED 并保留成功 ledger 前缀、恢复不重采；重复目标块拒绝；拒绝向量 Helius 调用数为 0；
g) 测试是否登记进两份测试的 main；`W4_done.md` 陈述（含 52 行、sha `15822564…`）与 diff 一致；
h) 用不合法输入独立验证：census 响应含两个 `header.number==slot` 块 → 拒绝；α 候选 SQD 有块头 → 拒绝（W1 α 规则）；INHERITED_REFUTED β 候选非零 nonce → 拒绝。
