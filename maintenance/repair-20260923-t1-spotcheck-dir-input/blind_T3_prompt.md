# 盲审 T3 r1（常规盲审，非攻击式；以可写沙箱运行，仅为允许创建临时夹具）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、`maintenance/repair-20260923-t1-spotcheck-dir-input/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；**禁读本工程目录内的 `T3_done*`、`T3_red_evidence*`、`review_T3_*`、`construct_*`、`T1_*`、`T2_*`、`blind_T1_*`、`blind_T2_*`、`final_review_*`、`fable_local_*`**（盲审＝只看工单与代码）。可读：`workorder_T3.md`、`FR02_decision_page.md`、`T3_cost_quq_v2_identity.log`。
2. 离线、不 commit、**禁止修改或新建仓库内任何文件**（临时夹具一律用 `tempfile`，结束前删除）；报告末尾贴 `git status --short` 全文且须为空。**报告全文放在最终答复消息里**。首行固定 `# 盲审T3：PASS` 或 `# 盲审T3：FAIL`。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，以当前 HEAD 为审对象；施工 diff＝`git diff 2197505 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`。工单＝`maintenance/repair-20260923-t1-spotcheck-dir-input/workorder_T3.md`（v2）。`changelog_lint.py` 子进程读 archive 属允许。

## 任务
审 T3 施工是否**真正解决**缺陷（目录输入案通过后叶子被覆写/增删，READY/verify/发布闸仍放行）并符合工单：
a) **终点判据（必做，独立复现，不得只依赖新增测试断言）**：自行构造 v2 目录夹具（可参考 `test_anchor_plan_v3._produce_plan(directory=True)` 的列形态），跑真实 `anchor_plan.py --input <目录>` 出计划/清单/收据，构造合法目录时间收据（`inputs.input`=清单，见 9.0.3 目录信任链），调 `shared_release_receipt._validated_time_plan_authority`：HEAD 放行；然后①同长度覆写 `run_1/logs.parquet` 末字节、②新增叶子、③搬走 `blocks.parquet`、④目录内 symlink → HEAD 各自被拒（贴完整错误文本）；恢复后放行。**基线 2197505**（`git show 2197505:scripts/report/shared_release_receipt.py` 内存对照，勿从临时文件路径加载被审模块）下 ①②③ 仍放行（原缺陷复现）。再走一遍完整入口：用 `test_handoff_manifest.make_case`/`test_batch3_evm_vertical_slice` 同款流程改目录输入（或内存替身接 RPC），覆写叶子后 `handoff_manifest generate --status READY`/`verify`/`audit_release_gate` 至少一条入口在 HEAD 被拒并贴文本（loopback 被拒记 SANDBOX-BLOCKED 并说明内存替身核到哪一步）。
b) **文件分支不变**：文件输入（CSV）在 HEAD 与基线的放行/拒收与错误文本顺序逐字一致（含同长度覆写 → `time plan input identity sha256 mismatch`）。
c) **修法与工单一致**：`shared_release_receipt.py` 仅 +1 行 import（`anchor_selection.input_identity`）、注释 `:1047` 订正、目录分支末尾两行 `_require(input_identity(directory)[0] == identity, ...)`；不包异常；`anchor_selection.py`/`receipt_kernel.py`/`receipt_validate.py`/`time_spotcheck.py`/`handoff_manifest.py`/`audit_release_gate.py` 字节不变。
d) **白名单与字节**：`git diff --stat 2197505 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 只含 `scripts/report/shared_release_receipt.py`、`scripts/tests/test_anchor_plan_v3.py`、`VERSION`、`pyproject.toml`、`SKILL.md`、`CHANGELOG.md`；references/commands-staging 零改动（929085 / 8789）；SKILL 8021 仅版本号；版本四处 9.0.5；CHANGELOG 索引行 176 B＋详细段。
e) **实跑**（贴尾行；SANDBOX-BLOCKED 不计 FAIL）：`python3 -B scripts/tests/test_anchor_plan_v3.py`（须 17/17）、`test_time_spotcheck.py`、`test_recon_deep_reverify.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`invariant_scan.py`、`changelog_lint.py`。
f) 结论规则：a) 基线复现缺陷、HEAD 四组反例全拒且恢复放行、至少一条完整入口在 HEAD 拒收，b)/c)/d) 全过、e) 无真实 FAIL → PASS；否则 FAIL 并指出哪条未闭合。逐条给证据。
