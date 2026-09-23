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
