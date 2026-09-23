# 收官 review r3（repair-20260923-t1 整体：9.0.3＋9.0.4＋9.0.5；本轮以可写沙箱运行，仅为允许创建临时夹具与本地测试）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、`maintenance/repair-20260923-t1-spotcheck-dir-input/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；禁读本工程目录内的 `T1_done*`、`T2_done*`、`T3_done*`、`*_red_evidence*`、`blind_*`、`review_*`、`construct_*`、`fable_local_*`、`T2_local_*`、`endpoint_check2.py`、`ep_probe.py`。**可读**：`workorder_T1/T2/T3.md`、`final_review_T1_reply_r1.md`、`final_review_T2_reply_r2.md`（你前两轮的收官 review）、`FR02_decision_page.md`、`T3_cost_quq_v2_identity.log`。`changelog_lint.py` 子进程读 archive 属允许。
2. 离线、不 commit、**禁止修改或新建仓库内任何文件**（临时夹具一律用 `tempfile`，结束前删除）；报告末尾贴 `git status --short` 全文且须为空。loopback 被沙箱拒的步骤记 `SANDBOX-BLOCKED` 并说明内存替身核到哪一步。**报告全文放在最终答复消息里**。首行固定 `# 收官review r3：通过` 或 `# 收官review r3：退回`。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`；审对象＝`git diff b52cbed HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（三版合计）。

## 背景（调度方声明）
你 r1 退回 FR-01/FR-02/FR-03；r2 确认 FR-01/FR-03 闭合、FR-02 单列待裁决。用户 2026-09-23 裁决 FR-02 选 **C 限目录案**，已按工单 T3 施工入库 9.0.5：`_validated_time_plan_authority` 目录分支在案根检查后 `_require(input_identity(directory)[0] == identity, ...)`，文件分支不变。本轮是整个工程（QUQ ANOM-008 引出的三版）的收官。

## 任务
a) **FR-02 是否真正消失**：重跑你 r1 的"目录案通过后覆写 `logs.parquet` 为另一份有效 parquet、不改计划/清单/收据"实验：HEAD 下 `validate_reconciliation_report`、`handoff_manifest generate --status READY`、`verify`、`validate_bundle`、`audit_release_gate` 各入口的结果与拒收文本（预期：全部拒，文本含 `time plan input directory content differs from signed identity`）；对照 9.0.4（`git show 2197505:scripts/report/shared_release_receipt.py` 内存对照）仍放行。再证：增叶子、删叶子、目录内 symlink 三组反例；未改动目录放行；你 r1 提到的"同大小改中间字节躲过 64 MiB 头尾分片指纹"在本修法下是否也被拒（完整 sha256）。
b) **三版整体端到端**：目录输入案在 HEAD 下 anchor_plan → time_spotcheck（目录）→ runner → READY → verify → validate_bundle → 发布闸全通（9.0.3）；旧生产者真实自哈希的文件案时间收据在 HEAD 全通（9.0.4）；覆写后被拒（9.0.5）。三者在同一夹具族上给出通过/拒收矩阵。
c) **回归与边界**：文件分支逐字节行为不变（含错误文本顺序）；`receipt_kernel`/`receipt_validate`/`anchor_selection`/`time_spotcheck`/`handoff_manifest`/`audit_release_gate` 相对 9.0.4 字节不变；`invariant_manifest` 无需登记；共享发布收据 producer 变化的存量影响（旧 `shared_release_receipt.json` 须重建）是否已在 CHANGELOG 如实登记；性能：一次 verify / 一次发布闸的目录重算次数与 QUQ 实测 3.5 s 的乘积估计；witness 边界（签发后改目录、同次 run 内改目录）是否如工单所述属未承诺范围且无更差退化。
d) **实跑**（贴尾行；SANDBOX-BLOCKED 规则同前）：`test_producer_registry_current.py`、`test_anchor_plan_v3.py`（须 17/17）、`test_time_spotcheck.py`、`test_recon_deep_reverify.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_batch3_evm_vertical_slice.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`invariant_scan.py`、`changelog_lint.py`。
e) 结论规则：a) FR-02 在 HEAD 各入口独立复现已消失且反例全拒、b) 三版矩阵成立、c)/d) 通过、无新 P0/P1 → 通过；否则退回并指出哪条未闭合。逐条给证据（命令与尾行）。
