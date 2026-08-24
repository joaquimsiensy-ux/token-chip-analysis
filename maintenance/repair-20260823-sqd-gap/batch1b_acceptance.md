# 批 1b 验收记录（Fable，2026-08-23）

- 工单 `batch1b_workorder.md`（首派因 Fable 行号数错 :85-91→实 :81-87 被 codex 开工门禁拦停，报告存 `batch1b_done_attempt1_stopped.md`；更正后 resume 同线程 45 分钟完成）；汇报件 `batch1b_done.md`（codex 按 fail-closed 标 STOPPED，阻塞项见 E20）。
- 改动范围（`git status`）：登记面 4 件（invariant_manifest/invariant_scan/contract_manifest/contract_ids_snapshot）＋`references/scan-schemas.md`（§14 契约族 600+ 行）＋四份草案 errata 小修＋INDEX＋四个新测试＋红证；无白名单外写入。
- 红证 `batch1b_red_evidence.txt`：**35 RED ＋ 1 GREEN（第(2)项顺序敏感事实）**；语义红 13 项（1/2-fact/9/12/13/14/17/19/22/23/24/31/33）、其余 missing-mechanism 烟雾红＋oracle；无 skip/xfail。
- 本机 `run_all.py`（126 项）：**2 失败＝预期先红**——`invariant_scan.py`（20 项登记缺口，全部指向批 2–5 要交付的 probe/repair/validator/wave v5/flow v3/reconcile v4）＋`test_batch4_invariant_guards.py:198`（E20）；沙箱内另两项回环 EPERM 本机全绿；其余 124 项绿＝本批零回归。
- 裁定：E20 选项 2（闭合批次批 2/批 5 写死）。
- 结论：**批 1b 验收通过**，commit 到分支；下一步派批 2（探针）。
