# T2 调度方本机验收记录（9.0.4，release=a906cf8；验收树 HEAD=3d6a9f8）

| 项 | 命令 | 结果 |
|---|---|---|
| 施工 diff 亲核 | `git diff d2d6641 a906cf8 -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` | 九文件，与工单 v3.1 §2 逐字一致（私有 `_time_producer_history`＋:1221/:1459 两处接线；登记条目六键；HISTORICAL_ONLY 扩一对；文档 :152 111→110 B、:158 326→320 B；版本四处 9.0.4；CHANGELOG 索引 200 B＋详细段） |
| 字节 | `wc -c SKILL.md` / `cat commands-staging/*.md \| wc -c` | 8021 / 8789，均不变 |
| 登记守卫 | `python3 -B scripts/tests/test_producer_registry_current.py` | `producer registry: 0 FAIL`（新条目 git show b52cbed 复现一致） |
| changelog_lint | `python3 -B scripts/tests/changelog_lint.py` | PASS（活跃 83 条＋归档 139 条） |
| **FR-01 真实案复验** | `handoff_manifest.py verify --case-dir <OPN 案>` | 修前 exit 2 `reconciliation time producer/runner is not current repository script`（T2_red_evidence_opn_verify.log）→ 修后 **exit 0 PASS**（176 件产物、8 gate，READY；T2_local_opn_verify_after.log） |
| FR-01 真实案复验 ② | 同上 `<BITCOIN 案>` | **exit 0 PASS**（121 件产物、4 gate，READY） |
| 纵切片（沙箱 SANDBOX-BLOCKED 项） | `python3 -B scripts/tests/test_batch3_evm_vertical_slice.py` | `PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure` |
| 全套 | `python3 -B scripts/tests/run_all.py`（后台，日志 run_all_t2.log） | 150 PASS / 1 FAIL：唯一 FAIL＝`test_stage2_reseal.py dry_run_touches_nothing`"验收 HEAD 与派工 HEAD 不一致"（run_all 启动后 HEAD 因入库提交前移、预建 worktree 失配，属环境时序项，同 T1） |
| reseal 单跑补验 | 按当前 HEAD 重建 `/tmp/w3_acceptance` 后 `python3 -B scripts/tests/test_stage2_reseal.py` | **21/21 PASS** |
| codex 盲审 r1 | blind_T2_reply_r1.md | PASS：独立复现文件组（基线拒/HEAD 通、反例全拒）与目录组（旧哈希仍走清单信任链）；10 项测试 exit 0 |

工艺记录：codex 只读任务把报告 print 到 stdout 会被 companion 截断丢失，须要求"报告放最终答复消息"（r1 复核因此补发一轮）；`codex-companion.mjs task --help` 会把 `--help` 当提示词发出（误触一次，无副作用）。
