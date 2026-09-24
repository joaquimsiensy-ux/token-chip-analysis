# 工单 W4 复核提示词（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**（不要只 print 到 stdout）。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（须含 `cc6298b`）。
3. 每条意见须给出可直接替换进工单的原文（含行号/锚），并标注「必改/建议/存疑」；结尾给汇总表（条目/等级/依据文件:行）。你复核的是**工单定形**，不是施工；发现工单事实与源码不符的地方优先级最高。
首行固定 `# 工单W4复核：通过` 或 `# 工单W4复核：退回`。

## 任务
复核 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W4.md`（v1；背景先读同目录 `README.md`）。逐条审：
a) 事实段 ①–⑥ 每个行号/锚/断言亲核；特别核：validator 是否真的不重算任何 SQD 请求体摘要（`grep -n` 证明）；`_verify_adopted_record(:783)` 是否触及 `coverage_probe_*` 字段；`_state_probe` 引用处；`test_batch8_repair_scale.py:57/:317` 的具体用法；`sqd_repair_core.py` 是否有别的地方复算 census 请求体或依赖 `instructions` 缺席。
b) SQD 查询语义：同一请求同时带 `transactions:[{}]` 与 `instructions:[{programId,d4}]` 并 `includeAllBlocks`，按 `sqd_coverage_probe.py:128` 与 `_census_body` 两模板及 `data-pipeline-solana-capture.md` §13 实录，判断响应块是否会同时含 `transactions` 与 `instructions` 数组、`instructions` 是否只含匹配指令（而不是全部指令）。若文档证据不足，明确写「需调度方本机实测」并给出最小实测命令（curl 到 `https://portal.sqd.dev/datasets/solana-mainnet/stream`）。
c) 合并后 `present`/`nonce_count` 语义是否与探针完全一致（含缺 `instructions` 键、饱和 255 等）；`validate_coverage_state_consistency` 调用顺序调整是否改变任何错误路径的可观测行为（ledger 行何时写、QuotaStopped 何时抛）。
d) 深验兼容：新代 evidence 的 `coverage_probe_query_sha256==query_body_sha256` 是否会撞任何唯一性/差异断言；旧代夹具是否仍 PASS；`--adopt-pending` 认领前代（探针分离的）pending 是否仍可行。
e) 测试 2.5 设计是否够（计数断言、三个故障向量）；行数上限 1.6 是否现实。
f) 白名单/不改清单遗漏；producer 换代登记归 W2 的安排是否会让 W4 收官 commit 处于「现役 sha 未登记」的中间态而影响本机验收（现役文件 sha 是否总被接受——核 validator `producer_sha == current_sha or ...`）。
