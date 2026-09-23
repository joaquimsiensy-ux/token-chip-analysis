# T1 调度方本机验收（Fable）

- 被验工作树：施工 attempt2 落地后、入库前（基线 b52cbed）；施工方停工原因＝沙箱不能监听本地端口跑 `test_batch3_evm_vertical_slice.py`，属调度方本机补验项。
- diff 范围：恰为工单 §0.3 白名单 8 文件（scripts 3 + references 1 + VERSION/pyproject/SKILL/CHANGELOG）；两处生产 diff 与工单 §2.1/§2.2 代码块逐字一致。
- 字节：SKILL.md 8021 不变；references/**/*.md 929092 不变（:158 行 326→326 B，含 `文件/清单`）；commands-staging 8789 不变；版本三处 9.0.3。
- 本机补验（MPLCONFIGDIR=~/.matplotlib）：
  - test_batch3_evm_vertical_slice.py exit=0 — `PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure`
  - test_audit_release_gate.py exit=0 — PASS
  - test_anchor_plan_v3.py exit=0 — `anchor-plan v3: 16/16 PASS`
  - invariant_scan.py PASS（receipt_producers=81, consumers=118, exceptions=0）
  - changelog_lint.py PASS（活跃 82 条）
  - run_all.py：见本文件末尾追加
- 施工方自跑（沙箱内，见 T1_done_attempt2_stopped.md）：anchor_plan_v3 16/16、time_spotcheck 20 项、recon_deep_reverify、handoff_manifest 283 项 均 PASS。
- run_all.py（入库前工作树，MPLCONFIGDIR=~/.matplotlib）：150 PASS，1 FAIL＝`test_stage2_reseal.py` 20/21（`dry_run_touches_nothing`：验收 worktree `/tmp/w3_acceptance` 已被系统清理，环境项，与本工程无关）。
- 入库 `3b5017d`（release 9.0.3）后 `git worktree prune && git worktree add --detach /tmp/w3_acceptance HEAD` 预建，单跑 `test_stage2_reseal.py` exit=0 — `stage2_reseal: 21/21 PASS`。合计 151/151。
- 施工提交 3b5017d 的 `git diff --stat b52cbed` = 8 文件（scripts 3 / references 1 / VERSION / pyproject / SKILL / CHANGELOG），无白名单外文件。

## 盲审 r1 补验：调度方本机独立终点验证（脚本 `endpoint_check2.py`/`ep_probe.py`，存本目录）
盲审 r1 因只读沙箱建不了临时目录，a) 四组终点全部 SANDBOX-BLOCKED（静态核验无缺陷）。调度方本机以临时 worktree `/tmp/t1_base`（b52cbed）与 HEAD 各起子进程探针，同一套夹具（`test_anchor_plan_v3._produce_plan` 目录/CSV 两分支）对比，11/11 PASS：
- G1 生产者：基线 main→build_envelope 的 inputs.input=目录、经真实 receipt_kernel 拒 `not a regular file`；HEAD inputs.input=anchor_plan.input.json、真实封装成功。
- G2 消费者：基线拒 `time plan input identity is not a regular file`；HEAD 目录计划+清单放行且返回 plan；input=计划文件 → 拒 `not bound through the signed input manifest`。
- G3 HEAD 自洽重绑（清单正文改、引用与 plan 输出哈希重签、plan.input 不变）→ 拒 `input manifest identity differs from signed identity`。
- G4 CSV 文件输入：生产者绑定对象、消费者放行、错绑拒收文本（`signed input identity is not the time receipt input object`）基线==HEAD。
首轮尝试把基线模块从临时文件加载出现 3 条假 FAIL（`producer/runner is not current repository script`＝加载位置不在仓库所致），改 worktree 子进程后消失，记录在案。
