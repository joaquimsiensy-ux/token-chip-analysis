# 收官 review（repair-20260923-t1 整体：QUQ ANOM-008 是否真正消失；本轮以可写沙箱运行，仅为允许创建临时夹具与本地测试）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260923-t1-spotcheck-dir-input/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；禁读本工程目录内的 `T1_done*.md`、`T1_red_evidence.txt`、`blind_*`、`review_*`、`construct_*`、`fable_local_acceptance.md`、`endpoint_check2.py`、`ep_probe.py`（不看施工/复核/盲审自述，独立判断）。豁免：测试自身以子进程访问历史 maintenance 目录属测试依赖，允许原样运行。
2. 离线、不 commit、**禁止修改或新建仓库内任何文件**（`/Users/uravvv/.claude/skills/token-chip-analysis` 下一字不动；临时夹具一律用 `tempfile`/`/tmp`，结束前删除）；报告末尾必须贴 `git status --short` 全文且须为空。若 loopback 监听被沙箱拒，涉及本地桩 RPC 的步骤记 `SANDBOX-BLOCKED` 并说明改用内存替身能核到哪一步。报告全文打印到 stdout，首行固定为 `# 收官review：通过` 或 `# 收官review：退回`。退回时逐条给出：编号（FR-NN）、文件:行、事实、后果、建议；另列 P0/P1/P2 分级。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`；审对象＝`git diff b52cbed HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`。`maintenance/` 目录整体不在白名单议题内。

## 任务
不以工单为范围边界，逐字段追来源，回答一个问题：**一个 EVM 案用 v2 目录作为 anchor_plan/time_spotcheck 输入，走完 A2 对账 runner（`reconciliation_report.py`）→ `handoff_manifest.py generate --status READY` → `verify` → 发布闸（`audit_release_gate`/`shared_release_receipt.validate_bundle`），在 HEAD 下是否已无任何"输入必须是普通文件"的隐性假设会拒收？** 具体：
a) 端到端独立复现：自行构造 v2 目录夹具（可参考 `test_batch3_evm_vertical_slice.py` 的桩 RPC 与 `test_anchor_plan_v3.py` 目录分支），把 `test_batch3_evm_vertical_slice.execute_real_slice` 同款流程改为目录输入（`anchor_plan --input <目录>`、runner spec 的 time 检查 `--input <目录>`），在 HEAD 下跑到 `handoff_manifest verify` 与 `validate_bundle`；报告每一关的通过/拒收与拒收文本。若某关因桩数据不足而非目录假设被拒，说明原因并给出最小补法（不改生产代码）。
b) 信任链审：目录身份不在发布期重算（工单 §1.2 明示边界）——列出 HEAD 下对目录输入"内容自生产后未改变"这一性质的所有防线（时间生产者语义重放、清单绑定、witness 指纹、data_map/freeze 登记等），指出是否存在比文件输入明显更弱、且能被"自己人误操作"触发的口子（威胁模型＝自己人，不做对抗攻击）；给出是否需要另开工单的判断。
c) 回归面：文件输入路径逐字节行为不变（含错误文本与顺序）；`receipt_kernel` 契约未放宽；`invariant_manifest`/`producer_history` 是否确实无需登记；旧案（文件输入）的既有 `time_spotcheck.json` 在 HEAD 消费侧是否仍放行（用 `test_recon_deep_reverify.py`/`test_handoff_manifest.py` 夹具证明）。
d) 实跑（贴尾行；`SANDBOX-BLOCKED` 规则同前）：`test_anchor_plan_v3.py`、`test_time_spotcheck.py`、`test_recon_deep_reverify.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_batch3_evm_vertical_slice.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`invariant_scan.py`、`changelog_lint.py`。
e) 结论规则：a) 端到端在 HEAD 下无目录假设拒收（或仅剩桩数据原因且给出补法）、b) 无 P0/P1 口子、c)/d) 通过 → 通过；否则退回。
