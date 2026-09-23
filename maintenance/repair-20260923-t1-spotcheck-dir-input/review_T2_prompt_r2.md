# 工单 T2 复核提示词 r2（只读）

## 纪律
同 r1（`review_T2_prompt.md` §纪律）：禁读 `~/.codex/`、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、其他 maintenance 目录、Desktop/Documents；只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**（不要 print 到 stdout，调度方只保留最终消息）。首行固定：`# 工单T2复核r2：通过` 或 `# 工单T2复核r2：退回`。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD。

## 任务
复核 `maintenance/repair-20260923-t1-spotcheck-dir-input/workorder_T2.md`（v2；v1 存 `workorder_T2_v1.md`，你的 r1 意见存 `review_T2_reply_r1.md`）。
a) 逐条核 r1 汇总表中"退回/建议"各项是否在 v2 中吸收（HISTORICAL_ONLY 精确对与注释、`_time_producer_history` 私有函数与两层替换文、H14/H15 收紧、类型边界、H16 17 行真实 wrapper 路径、FR-03 两行 −7 B、CHANGELOG :13 整行原文与 200 B 索引行、`:242` 锚改法、开工 HEAD 条件、changelog_lint 交调度方、1.3/1.5 措辞、⑤来源标注）。
b) 新增锚整行 `grep -n -F -x` 恰 1 处且行号一致：`shared_release_receipt.py:1208`、`test_producer_registry_current.py:24` 与 `:21-23` 三行、`test_recon_deep_reverify.py:593/:601`、`references/data-pipeline-evm-recon.md:152/:158`、`CHANGELOG.md:13/:100`。
c) v2 相对 v1 是否引入新问题：§2.3 H16 中 `make_case(str(root), token=..., as_of_block=...)` 与 `test_handoff_manifest.make_case(d, chain="eth", token=TOKEN, as_of_block=999)` 签名是否相容；`make_case` 在同一 root 会写哪些文件、是否与 `_produce_time`/`_plan_fixture` 的文件（`anchor_plan*.json`、`time_spotcheck.json`、transcript）冲突——工单给的兜底（子目录重产）是否可行；`from test_handoff_manifest import make_case` 在 `python3 -B scripts/tests/test_recon_deep_reverify.py` 直跑与 `run_all.py` 两种方式下能否导入（sys.path）；§2.4 `:158` 替换文的语义是否有失真（"exit 0/2/1＝PASS/FAIL/ERROR" 是否等价于原"1 检测自身失败禁当 PASS"；"EVM READY 必备"是否与 `REQUIRED_FOR_READY_EVM` 一致；split-run 限定被删是否引入错误陈述）。
d) 版本 9.0.4 详细段要求是否足够；`docs_lint`（pre-commit）对 `:158` 改写有无粗体/引用断链风险。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文，含行号）＋ 汇总表。
