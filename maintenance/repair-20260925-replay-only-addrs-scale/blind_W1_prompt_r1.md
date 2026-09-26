# 盲审 W1 r1（只读 codex，常规盲审，非攻击型）

## 纪律
禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`（自建 `.staging_blind_r1/` 豁免）、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260925-replay-only-addrs-scale/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`、`/Volumes`；不得进入 `/Users/uravvv/.claude/skills/token-chip-analysis`。只读、离线、不 commit。工作目录＝`/Users/uravvv/.claude/worktrees/tca-only-addrs`（分支 `fix/replay-only-addrs-scale`）。**报告全文放在最终答复消息里**，首行固定 `# 盲审 W1 r1：PASS` 或 `# 盲审 W1 r1：FAIL`。
沙箱若写不了 `/private/tmp`：开工执行 `mkdir -p "$PWD/.staging_blind_r1/tmp" && export TMPDIR="$PWD/.staging_blind_r1/tmp"`；若整个工作区只读，测试类项目标注"环境阻断、非代码回归"并列入未完成项，不计 FAIL，但第 2/3 项须改用纯内存 DuckDB 完成。

## 任务
不看施工者的过程记录（`W1_done.md`/`W1_equivalence.txt`/`W1_timing.txt` 只作"声称清单"，每条声称你自己复现）。工单＝`workorder_W1.md`（v3.1），契约以其 §1 为准。逐项：
1. **范围**：`git diff --name-only bb8c871 HEAD -- . ':!maintenance/repair-20260925-replay-only-addrs-scale'` 输出必须是 `scripts/evm/replay_duck.py`、`scripts/tests/test_engine_equivalence.py`、`VERSION`、`pyproject.toml`、`SKILL.md`、`CHANGELOG.md` 的子集；`SKILL.md`/`pyproject.toml` 仅版本行变化；`references/`、`commands-staging/`、`run_all.py`、`invariant_manifest.json` 零改动。
2. **等价性独立复现**（自建固定种子小夹具，纯内存或临时目录均可）：以 `git show 8457f70:scripts/evm/replay_duck.py` 基线副本（放 `<tmp>/scripts/evm/` 保留 basename，`PYTHONPATH` 含工作树 `scripts/evm:scripts/lib`）与 HEAD 脚本同参数对照 `--only-addrs` 收据 `addresses`（含零事件地址、Z/DEAD、低于全量门槛的正峰值地址、同块自转净零、完全重复行），`CHIP_REPLAY_SEG_ROWS` 取小值使 K≥4；HUGEINT 与 `--force-varint` 各一次。四类冲突反例（同键异值 / 同键跨块 / 同键端点不同且仅一行命中 / 两端均不命中）各独立运行：HEAD `--only-addrs` 与全量、基线全量三者都须在冲突检查处拒绝、无新收据、旧收据字节不变。
3. **不物化与分桶**：读 HEAD 源码 + 你自己跑一次带 `EXPLAIN`/日志的 only-addrs：`raw_rows` 为 VIEW、无全量 `events` CTAS、每个去重 GROUP BY 都带桶谓词、桶循环后 `ab` 由 `ab_raw GROUP BY a,b` 合并；正常路径每桶覆盖源范围的查询恰 2 条（列出实际 SQL）；`kept_rows` 来自 `acc["_kept_rows"]`（逐通道保留行 COUNT 之和）且桶行数之和断言存在；`CHIP_REPLAY_SEG_ROWS` 非法值 rc 2 且全量模式不受影响；峰值 SQL、`_peaks_python`、收据构造与 `os.replace` 相对基线逐字不动（`git diff` 证明）。
4. **全量路径未动**：小夹具上基线副本与 HEAD 全量（`--no-merged`）业务 JSON 逐键逐值相等（`replay_stats.producer` 允许不同，其他 provenance 差异须能解释）；带 `--camps` 的 pass2 与 merged 各一次。
5. **测试**：`python3 -B scripts/tests/test_engine_equivalence.py`（含新例 `followup_bucketed_case`）、`test_audit_release_gate.py`、`test_fault_injection.py`、`test_repair_batch_c.py`、`test_repair_batch1.py`、`test_review_evm_integrity.py`、`fixtures_lint.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`changelog_lint.py` 自跑结果。
6. **版本登记**：四处一致为 9.2.2；CHANGELOG 索引行 ≤200 B、详细段四条如实（含默认 500 万桶资源证据状态、按实际源查询次数登记 IO 代价，不写"K 次读取"、不外推亿级）。
判定：任一项不成立即 FAIL 并给出最小复现命令与输出；PASS 须列出你实际复现的命令清单与关键输出。
