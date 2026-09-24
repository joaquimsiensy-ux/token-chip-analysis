# 工单 W1 复核提示词（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**（不要只 print 到 stdout）。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（须含 `cc6298b`）。
3. 每条意见须给出可直接替换进工单的原文（含行号/锚），并标注「必改/建议/存疑」；结尾给汇总表（条目/等级/依据文件:行）。你复核的是**工单定形**，不是施工；发现工单事实与源码不符的地方优先级最高。
首行固定 `# 工单W1复核：通过` 或 `# 工单W1复核：退回`。

## 任务
复核 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W1.md`（v1；背景先读同目录 `README.md`）。逐条审：
a) 事实段 ①–⑦ 的每个行号/锚/断言逐一亲核（`grep -n -F -x`），尤其：`_recheck_known_slots` 返回的 `actual` 是否含全部 verified slot 的实测值；`unverified` 的形态；`:781-784` fallback 写法；`classify_four_states` summary 键集；`validate_coverage` 三项全等比较；`validate_shared_map` 对 refuted 的现有处理；export 的 `checked["recomputed"]["candidate_slots"]` 来源；修复侧 `validate_coverage_state_consistency` 对未知状态的行为；`sqd_gap_repair.py:1369` 与 validator `:1574` 对 states 的用法是否会被新状态字符串影响；`sqd_cache_identity.sqd_repair_paths` 签名与返回。
b) 设计正确性：①继承条件（1.2）是否足以保证「继承的 slot 在本案语义下确实无需修复」——给出你认为的漏洞（例如源案 census 判 refuted 的依据是签名差集为空；后案只重查 nonce 计数；SQD 若在同 slot 增删非 nonce 交易但 nonce 仍为 0，重查发现不了——这是否被 canary/历史锚/finalized-head 语义覆盖？如实评估并建议工单是否要加「残余风险」条款或更强的重查（如用 census 形态重查）；②`INHERITED_REFUTED` 不入 `unconfirmed` 时 verdict 可能变 NO_KNOWN…，replay/exact_reconcile 的组合判定（`replay_edges.py:420-448`、validator `:2124-2154`）是否照常成立；③summary 新键「仅非空时存在」的向后兼容策略是否可靠，还是应改为其他方式（如放在 `shared_map` 下而不动 summary）；④校验器 1.4 的独立复核清单是否完整、有无可被 coverage_map 自报绕过的项；⑤2.2 导出对修复代的绑定清单是否够（要不要核 `CURRENT.json` 指针深验、要不要拒绝 exploration 代、census 行 `coverage_state` 与 `state_in_map` 该看哪个）；⑥链式导出（1.6/2.2 步骤 1）会不会让过期地图的驳回无限续命——是否需要在 evidence 里带原始 `generated_at` 或限制链深。
c) 修法最小化与行数上限（1.7）是否现实；有无更简单的等价实现。
d) 测试 2.6 (a)–(f) 是否可在现有 fixture transport 体系下构造（看 `test_sqd_coverage_probe.py:538-765` 与 `:653` export 用例的夹具写法），缺什么补什么。
e) 回归面：`invariant_scan.py`/`test_batch4_invariant_guards.py`/AST 守卫是否会对 classify 签名变化或新状态字符串报警；`scan-schemas.md` §14.1 改动是否触发 `docs_lint`/`test_g3_docs_guards`。
f) 白名单/不改清单是否遗漏必须动的文件。
