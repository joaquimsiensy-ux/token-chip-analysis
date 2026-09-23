# 收官 review r2（repair-20260923-t1 整体：9.0.3＋9.0.4；本轮以可写沙箱运行，仅为允许创建临时夹具与本地测试）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、`maintenance/repair-20260923-t1-spotcheck-dir-input/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；禁读本工程目录内的 `T1_done*`、`T2_done*`、`*_red_evidence*`、`blind_*`、`review_*`、`construct_*`、`fable_local_acceptance.md`、`endpoint_check2.py`、`ep_probe.py`、`T2_local_*`（收官＝只看工单、代码与你自己上一轮的报告）。**可读**：`workorder_T1.md`、`workorder_T2.md`、`final_review_T1_reply_r1.md`（你上一轮的收官 review）、`FR02_decision_page.md`。`changelog_lint.py` 子进程读 archive 属允许。
2. 离线、不 commit、**禁止修改或新建仓库内任何文件**（临时夹具一律用 `tempfile`，结束前删除）；报告末尾贴 `git status --short` 全文且须为空。loopback 被沙箱拒的步骤记 `SANDBOX-BLOCKED` 并说明内存替身核到哪一步。**报告全文放在最终答复消息里**（不要 print 到 stdout）。首行固定 `# 收官review r2：通过` 或 `# 收官review r2：退回`。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`；审对象＝`git diff b52cbed HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（9.0.3 目录输入修复＋9.0.4 历史哈希登记与两层接线）。

## 背景（调度方声明）
你上一轮收官 review 退回三条：FR-01（P1，旧文件案时间收据被 HEAD 拒）→ 已按工单 T2 修复入库 9.0.4；FR-03（P2）→ 按 T2 改 references 两行；FR-02（P1，目录叶子事后覆盖缺必经防线）→ 已写成 `FR02_decision_page.md` 交用户裁决是否另开工单（A 不补 / B 强制清单叶子∈data_map / C 消费期重算），**不在本轮修复范围**。本轮请把 FR-02 作为"已知、已升级给用户裁决"的项单列，不因它退回；但若你发现 9.0.4 使 FR-02 变得更糟或引入新的 P0/P1，照退。

## 任务
a) **FR-01 是否真正消失**：独立复现（不得只依赖新增测试）：从 Git 取旧生产者（`git show b52cbedf230218e5da46334cf99b7111235e8367:scripts/lib/time_spotcheck.py`），用它在临时案生成文件输入的 v3 时间收据（真实自哈希 87bbad22…），配 HEAD 的 EVM 四查 wrapper（`test_handoff_manifest.make_case` 或 `test_recon_deep_reverify` 夹具），走 `validate_reconciliation_report` → `handoff_manifest generate --status READY` → `verify` → `validate_bundle`/发布闸：HEAD 全通；基线 b52cbed 之后、9.0.4 之前（`git show a906cf8~1`或 `d2d6641` 内存对照）被拒于何处。再证：陌生哈希、错 path、其他查项、Solana、`[]` 收据、默认 `validate_receipt` 均不受历史准入影响；旧哈希 + 目录收据仍走 9.0.3 清单信任链。
b) **9.0.3 端到端仍成立**（你上一轮 a) 已证目录案贯通，本轮只需回归确认）：目录输入案在 HEAD 下 anchor_plan → time_spotcheck（目录）→ runner（time 项 `--input <目录>`，runner `inputs` 省略或登记清单）→ READY → verify → validate_bundle 无"输入必须是普通文件"拒收；FR-03 两行文档是否与源码行为一致（runner inputs 可省略、登记则填文件、data_map.files 填叶子）。
c) **FR-02 现状复述**：在 9.0.4 之后重跑你上一轮的"覆写 logs.parquet 后 READY/verify 仍过"实验，确认现状未变差；对 `FR02_decision_page.md` 三个选项给出你的技术意见（哪个最小且足够、B 的实现面估计），不做裁决。
d) **回归面**：文件输入路径逐字节行为不变（错误文本与顺序）；`receipt_kernel`/`receipt_validate`/`time_spotcheck`/`handoff_manifest` 相对 9.0.3（3b5017d）字节不变；`producer_history` 新条目 git 可复现且 `test_producer_registry_current` 逻辑不变；`invariant_manifest` 无需登记。
e) **实跑**（贴尾行；SANDBOX-BLOCKED 规则同前）：`test_producer_registry_current.py`、`test_anchor_plan_v3.py`、`test_time_spotcheck.py`、`test_recon_deep_reverify.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_batch3_evm_vertical_slice.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`invariant_scan.py`、`changelog_lint.py`。
f) 结论规则：a) FR-01 在 HEAD 独立复现已消失且反例全拒、b) 目录案无隐性文件假设拒收、d)/e) 通过、无新 P0/P1（FR-02 单列不计）→ 通过；否则退回并指出哪条未闭合。逐条给证据（命令与尾行）。
