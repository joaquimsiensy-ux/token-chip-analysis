# T3 调度方本机验收记录（9.0.5，release=0c58cd2）

| 项 | 命令 | 结果 |
|---|---|---|
| 施工 diff 亲核 | `git diff 2197505 0c58cd2 -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` | 六文件，与工单 T3 v2 §2 逐字一致（import 1 行＋注释 1 行＋两行全等校验；test_17 六步；版本四处 9.0.5；索引 176 B＋详细段） |
| 目录回归 | `python3 -B scripts/tests/test_anchor_plan_v3.py` | `anchor-plan v3: 17/17 PASS` |
| changelog_lint | `python3 -B scripts/tests/changelog_lint.py` | PASS（活跃 84 条） |
| **QUQ 真实目录案（含目录重算）** | `shared.validate_reconciliation_report(<QUQ 案根>)` | PASS，3.7 s（v2 7.62 GB / 61 文件） |
| OPN 文件案 | `handoff_manifest.py verify --case-dir <OPN>` | PASS（176 件、8 gate，READY） |
| 纵切片（沙箱阻塞项） | `python3 -B scripts/tests/test_batch3_evm_vertical_slice.py` | `PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure` |
| 全套 | `python3 -B scripts/tests/run_all.py`（HEAD 0c58cd2，预建 worktree 同步，期间未提交） | 全部通过；exit 0 |
| codex 盲审 r1 | blind_T3_reply_r1.md | PASS（基线复现/HEAD 四反例拒/READY+verify 入口拒/文件分支七组错误文本逐字一致） |
