# 收官 review R1（只读 codex）：确认 QUQ ANOM-009 问题真正解决

## 纪律
禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260924-flow-scan-scalability/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。只读、离线、不 commit、不新建/修改仓库文件；临时目录用 `mkdir -p "$PWD/.staging_review_r1/tmp" && export TMPDIR="$PWD/.staging_review_r1/tmp"`（对该目录豁免 `.staging_*` 禁读），结束 `rm -rf` 并确认 `git status --short` 为空。**报告全文放在最终答复消息里**，首行固定 `# 收官review R1：PASS` 或 `# 收官review R1：FAIL`。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。

## 背景（调度方提供，数字以引用文件为准）
- 问题：`flow_anomaly_scan.py` 在 EVM v2 直读、1.097 亿边、7,093 个汇集点预筛候选下逐候选全量重扫 parquet，单候选 ~118 s，整案 ≈5 天不可完成（工单 §出处）。
- 修复：HEAD 相对 `634c083` 的差异（生产仅 `scripts/report/flow_anomaly_scan.py`，测试 `scripts/tests/test_flow_anomaly.py`，版本 9.1.1）。已过工单三轮复核、施工、盲审（`blind_R1_reply_*.md`）。
- 调度方本机验收结果（只作声称）：OPN 真实案（BSC 255 万边）HEAD 输出与 9.1.0 基线去 `generated_at` 后核心逐字节相等、`recipients_top` 第 500 名并列合法；QUQ 亿级实跑结果见本提示词末尾"调度方补充"。

## 任务（每条给出你实际运行的命令与关键输出）
1. **问题是否真正解决（机制层）**：读 HEAD 源码，说明逐候选查询现在读什么、底层 `eflow`/parquet 被扫描的语句次数是多少（用 `EXPLAIN` 在你自建的 `--edges-evm-v2` 两 run parquet 夹具上证明），与基线对比。指出任何仍随候选数线性放大的全量扫描路径（含 spray 阶段 `spray_edges` 点查是否仍为全表扫、其代价上界如何随边数增长）。
2. **等价性是否守住**：抽 3 个你自己设计的对抗场景（例如：候选同时是 sink 与 spray、实体抵消后候选消失、exclude 名单含候选、空 elig、`amt` 极大 HUGEINT 边界）在基线副本（`git show 634c083:scripts/report/flow_anomaly_scan.py`，`PYTHONPATH=<repo>/scripts/lib:<repo>/scripts/solana:<repo>/scripts/report`）与 HEAD 上对照，按工单 §1.1 契约判定。
3. **资源风险**：物化表容量与 `--mem-limit`/临时盘的关系，亿级下最坏情形（相关边≈全量）是否会 OOM 或写满临时盘；`preserve_insertion_order` 是否在异常路径恢复；阶段释放是否生效。给出结论与依据，不要外推没有证据的数字。
4. **回归面**：`test_flow_anomaly.py` 全部用例、`test_wave_scan.py`、`fixtures_lint.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py` 自跑；`wave_scan.py`/`scripts/lib`/`scripts/solana`/`references`/`commands-staging` 相对 `634c083` 零改动。
5. **版本与文档**：`VERSION`/`pyproject.toml`/`SKILL.md`/`CHANGELOG.md` 四处一致为 9.1.1；CHANGELOG 详细段是否如实（不夸大为"亿级必可完成"）。
6. **残余问题清单**：按 P0/P1/P2 分级列出未解决或新引入的问题；P0/P1 为空才可 PASS。

## 调度方补充（QUQ 亿级实跑，只作声称）
- QUQ(BSC) 真实案，HEAD 脚本 9.1.1，命令 `flow_anomaly_scan.py --edges-evm-v2 data/v2 --total-supply 1000000000000000000000000000 --case-root . --mem-limit 8GB`（机器 8 核 16 GiB，DuckDB 1.5.4，有效 memory_limit 7.4 GiB，默认 temp_directory=.tmp）：
  - 边表 109,681,418 条；合格地址 5,088；汇集点预筛 7,093 → 物化 sink_edges 26,094,518 行、sink_net 7,093 行；分发点预筛 42,064 → 物化 spray_edges 106,359,203 行。
  - 结果：汇集点 1,779 个 / 分发点 69 个；rc=0；总墙钟 4,947.8 s（≈82 min）；该进程峰值 RSS 6,302.8 MiB（os.wait4 rusage）；运行中 `.tmp` 溢写观测到约 10 GB（单次 du 采样，非峰值保证），结束后自动清空。
  - 阶段观察：sink 阶段（7,093 候选点查）约 2 分钟完成；spray 阶段耗时 ≈70 min，进程采样显示 DuckDB 工作线程全部空闲、主线程在纯 Python（逐候选 fetchall + `best_window_scan` 滑窗），即 DB 层重扫已消除、剩余成本在基线原有的 Python 侧逻辑（R1 范围外，请在残余清单里如实分级，不要求本轮修）。
  - 对照：修复前同案 try1 7h14m、try3 18h35m 均未走出汇集点阶段（估算 ≈5 天）。
- 本机 run_all：150/151 + reseal 预建 worktree 补验 21/21（唯一红项为环境项）。盲审 r2 沙箱无法建临时目录，其未完成的 5 个测试已由本机 run_all 覆盖（只作声称）。
- 你的沙箱可能同样无法创建任何目录（含仓库内）；若如此，第 1/2 项请改用内存方式（`git show` 基线源码载入内存、`--duckdb` 内存库或 `:memory:`）完成，并如实写明；第 4 项测试若因此跑不了，标注"环境阻断"并不计 FAIL。
