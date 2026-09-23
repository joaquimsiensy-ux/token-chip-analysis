# 工单 T3 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**（不要 print 到 stdout）。首行固定 `# 工单T3复核：通过` 或 `# 工单T3复核：退回`。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD。

## 任务
复核 `maintenance/repair-20260923-t1-spotcheck-dir-input/workorder_T3.md`（v1）。它落实用户裁决"FR-02 选 C、限目录案"（背景见 `FR02_decision_page.md` 与你在 `final_review_T2_reply_r2.md` §c 的意见）。逐条审：
a) 锚与行号：`shared_release_receipt.py:39/:1047/:1055-1059`、`test_anchor_plan_v3.py:600`、`CHANGELOG.md:13/:101`、`SKILL.md:23`、`pyproject.toml:15` 整行 `grep -n -F -x` 恰 1 处且行号一致。
b) 来源断言亲核：①READY 生成/verify/发布闸/validate_bundle 是否全部经 `_validated_time_plan_authority`（一处改动是否真覆盖你 r1 实验的全部入口，含 witness 复用路径 `audit_release_gate._validate_reconciliation_report_once` 的缓存语义——缓存会不会让重算只发生一次而后续入口沿用旧结果？若会，是否可接受）；②`input_identity` 返回 dict 与 `plan_receipt.input_identity` 是否恰为同一形态（四键、path 为 resolve 后绝对路径），全等比对在案根未迁移下必真、迁移下已被 `:1056-1059` 先拒；③`anchor_selection` import 无环、`sys.path` 已含 lib；④`_require` 是否抛 `ValueError`，与本函数其他拒收一致。
c) 修法定形：与"C 限目录案"是否严格对应（文件分支逐字不动、其他消费者不动）；是否有更短等价（如直接 `_require(input_identity(directory)[0] == identity, ...)` 不包异常——评估 symlink/无文件时裸 ValueError 文本是否已足够，包与不包哪个更好）；性能（每次 validate_reconciliation_report 都重算，一次 verify/发布闸会调几次？按 QUQ 实测 3.5 s 估总耗时）。
d) 回归面：文件输入路径逐字节行为不变；既有测试对目录分支的断言（test_16、test_recon_deep_reverify、test_handoff_manifest、test_batch3）是否会因新增读盘/全等校验而失败（夹具目录内容在消费前是否被改动、夹具 identity 是否由同一 `input_identity` 产生）；`invariant_manifest` 是否需登记。
e) 测试：§2.2 六步是否足够且最小；步骤 4 的搬移方式与步骤 5 symlink needle 是否可行；是否需补"消费期重算耗时不进收据"之类的非目标断言（不需要请明说）。
f) 原则与档位：references/commands 0 B、SKILL 仅版本号；9.0.5 记"修"是否恰当（消费者收紧、schema 不变；对比 9.0.1 先例）。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文，含行号）＋ 汇总表。
