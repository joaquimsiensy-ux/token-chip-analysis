# 盲审 R1（只读 codex，常规盲审，非攻击型）

## 纪律
禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260924-flow-scan-scalability/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。只读、离线、不 commit、不新建/修改仓库文件（临时目录可用）。**报告全文放在最终答复消息里**，首行固定 `# 盲审R1 r2：PASS` 或 `# 盲审R1 r2：FAIL`。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，被审对象＝HEAD 相对 `634c083` 的差异。

## 任务
不看施工者的过程记录（`R1_done.md` 只作"声称清单"，每条声称你自己复现）。逐项：
1. 范围：`git diff --stat 634c083 HEAD` 是否只含工单 §0.3 白名单；references/commands-staging 零改动。
2. 等价性独立复现：用你自己生成的固定种子夹具（覆盖工单 §0.7 列出的主夹具要素与并列微夹具、三入口），以 `git show 634c083:...` 基线副本（按工单 §0.6 的 PYTHONPATH 写法）与 HEAD 脚本同参数对照，按工单 1.1 契约判定；重点：elig 空集 `IN ('')` 兼容、`sink_net` 单侧净流入、entity 抵消、exclude、`recipients_top` 边界。
3. 源扫描次数：`EXPLAIN` 逐候选查询只读物化表；`eflow` 被扫描的语句数 ≤ 工单 1.2 上限。
4. 保序与过滤效果：物化表是否按候选列组织生效（工单 1.5）。
5. 测试：`test_flow_anomaly.py` 17 例、`test_wave_scan.py`、`test_reconcile_v4_receipt.py`、`fixtures_lint.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py` 自跑结果。
6. 版本登记四处与 CHANGELOG 索引行 ≤200 B、详细段四条。
判定：任一项不成立即 FAIL 并给出最小复现命令与输出；PASS 须列出你实际复现的命令清单。

## r2 相对 r1 的两处澄清（r1 报告 `blind_R1_reply_r1.md` 的 FAIL 两项均为审查条件问题，不是生产代码问题；本轮请重新完整判定，不沿用 r1 结论）
1. **范围判定口径**：`maintenance/repair-20260924-flow-scan-scalability/` 目录下的工单、复核提示词/报告、探针等是调度方在施工前后自行提交的工程文档，**不在范围判定之内**。范围判定命令固定为：
   ```bash
   git diff --name-only 634c083 HEAD -- . ':!maintenance/repair-20260924-flow-scan-scalability'
   ```
   其输出必须是以下六个文件的子集，否则 FAIL：`scripts/report/flow_anomaly_scan.py`、`scripts/tests/test_flow_anomaly.py`、`VERSION`、`pyproject.toml`、`SKILL.md`、`CHANGELOG.md`。另核 `SKILL.md` 与 `pyproject.toml` 仅版本行变化，`references/`、`commands-staging/`、`scripts/lib/`、`scripts/solana/`、`scripts/report/wave_scan.py` 零改动。
2. **临时目录**：沙箱写不了 `/private/tmp`。请在开工时执行 `mkdir -p "$PWD/.staging_blind_r2/tmp" && export TMPDIR="$PWD/.staging_blind_r2/tmp"`（该路径已被 `.gitignore` 的 `.staging_*/` 忽略，允许你读写自己建的这一个目录，"禁读 `.staging_*`"对它豁免），在此前提下**必须**真实完成：工单 §0.6 的基线副本子进程运行、三入口（`--edges-sol`/`--edges-evm-v2`/`--duckdb`）正式对照、真实 EVM parquet 入口的 `EXPLAIN`、以及第 5 项全部 7 个测试文件。结束前 `rm -rf "$PWD/.staging_blind_r2"`，并在报告末尾确认 `git status --short` 为空。
   若设置 TMPDIR 后仍有测试因环境无法运行，给出最小复现命令与完整异常，并明确写明"环境阻断、非代码回归"，该项不计 FAIL 但须列入"未完成项"。

## 补充
- 工单为 `maintenance/repair-20260924-flow-scan-scalability/workorder_R1.md`（v3.1），等价契约以其 §1.1 为准（含"候选遍历顺序不在承诺内"与 `recipients_top` 第 500 名并列规则）。
- 本机探针 `R1_fable_ctas_probe.md` 只是观测，不是结论；第 4 项请你自己用 `EXPLAIN`/点查耗时核，不要引用它替代复现。
- 施工者的证据文件 `R1_equivalence.txt`/`R1_timing.txt`/`R1_done.md` 同样只作声称清单。
