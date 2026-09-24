# W1 收官验收（调度方，2026-09-24）

- 施工：codex `--write` 线程 01a0d254…（首段 task-muf7s5sb，中途提问；续接 task-muf89gnm）。中途提问裁定：允许修正旧 `test_f03_sharedmap_reuse.py` 非法 refuted 夹具（counts=3 的 slot 当 refuted）、保留回归语义（`W1_done.md` §2.6(f) 例外段）。工单 v4，基线 `W1_BASE=6b36dcd`。
- diff（`git diff --numstat 6b36dcd -- . ':!maintenance'`）：validator +352/−5、probe +130/−7、repair +1/−1（仅 `validate_coverage_state_consistency` 零 nonce 分支加 `INHERITED_REFUTED`）、test_sqd_coverage_probe +505/−1、test_f03 +25/−10、test_sqd_gap_repair +114、scan-schemas +12/−2、README +35。全部白名单内；校验器超原 120 行指标与文档超 1,200 B 指标均已在完成报告逐项说明（新增职责：证据映射、专用 recheck、副本交叉校验、修复来源绑定；残余风险原文）。
- 调度方本机定向（工单 §0.7 全清单＋施工方未跑项）：`test_sqd_coverage_probe` 18/18、`test_f03_sharedmap_reuse` 15/15、`test_batch3_solana_producers`、`test_reconcile_v4_receipt`、`invariant_scan`（探针消费者集合不变）、`test_batch4_invariant_guards`、`test_exemption_guards`、**`test_sqd_gap_repair` 整套 rc=0**、**`test_batch8_repair_scale` 整套 rc=0**、`docs_lint`、`changelog_lint`——**11/11 PASS**。
- `run_all.py`：见下方补记。
- codex 盲审：见 `blind_W1_reply_r*.md`。
