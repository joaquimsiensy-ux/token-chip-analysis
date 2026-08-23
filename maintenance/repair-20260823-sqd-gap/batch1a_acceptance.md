# 批 1a 验收记录（Fable，2026-08-23）

- 工单：`batch1a_workorder.md`；施工方 codex（task-mt5tww9p-d6v2g3，8 分钟，哨兵终态 completed）；汇报件 `batch1a_done.md`。
- 机器检查：`git status` 仅 contracts_draft/*.json（17 份）＋ done；17 份 JSON 可解析、无浮点、`draft_status=batch1-frozen`；INDEX 的 errata/final_review sha256 与实物一致、plan_sha256 不变。
- 抽核：`fetch_sqd_transfers_v2.py:521-537` 字段抄录逐项对得上；`replay_edges.py:363-370` 三个 raw 字段字符串属实；coverage-pointer 按 E9 全字段、reconcile v4 含 `inputs.coverage_pointer` 与 verdict/exit_code 明确映射（E11）、wrapper 单层 checks＋family（E12）。
- 发现项处置：#2 → 新增 E14（v4 三 raw 字段 JSON int）；#1/#3 → E15/E16 记录（已被既有条款覆盖）。INDEX 的 errata sha256 随之更新。
- 结论：**批 1a 验收通过**；下一步 codex 只读复审（准入闸第二次），判"可进批 1"后派批 1b。
