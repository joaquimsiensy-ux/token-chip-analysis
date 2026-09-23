# 工单 W2 v3 — 盲审 r1 消化：认领记录复验补「候选前缀＋来源目录名」约束；CHANGELOG 去施工叙述

> v2→v3（吸收 codex 复核 `review_W2_r2_report.md` 1 条）：§3 续跑路径明确每个 mutation 从复制品原始台账字节开始、断言拒绝后恢复原始字节、恢复后调 `load_resume_slots(pending, repair._ledger_header(plan), plan)` 断言不抛且 completed 等于原两个 slot 集合，再做下一向量。
> v1→v2（吸收 codex 复核 `review_W2_r1_report.md` 5 条）：①候选构造行号改 `:607-608`/`:626-629`，深验列表初始化与收集位置写明；②§3 明确"两条成功数据行、认领一行"的独立 pending 构造、篡改隔离、原件恢复与恢复后正向断言；③schema 白名单扩为 `rows`、`source` 两行（`:1007-1008`）；④成本/质量指标改为整版有据数字，去掉施工分段。
> 来源：`blind_review_W1_r1_report.md`。P1＝首次认领（`sqd_gap_repair.py:861`，锚 `adopt: adopted slots are not a candidate prefix`）强制「采纳行 slot 序列 == `plan["candidate_slots"]` 前缀」，但认领后的两条复验路径——生产者 `_verify_adopted_record`（`:783-814`）与深验（`solana_exact_validate.py:1341-1353`、`:1387-1392`、`:1520-1527`）——都没复查该前缀关系，`adopted.source` 也只查是 str，未绑定到 `pending-<predecessor_plan_digest>`；盲审内存复现：候选 `[10,20]` 台账行排成 `[20,10]` 声明 rows=1 被接受、source 改空串/错误目录名被接受。P2＝CHANGELOG 9.1.0 正文混入「按 W1 v5、A1、A2 施工」「本段仅登记…新增生产逻辑 0」等施工分段叙述。

## 0. 纪律
- 0.1 分支 `fix/solana-txv1`；开工 `git status --short` 为空；`.git` 只读、commit 由调度方代做（不以此停工）；禁读 `~/.codex`（启动披露除外）、`~/Documents`、`~/Desktop`；离线；`MPLCONFIGDIR=$HOME/.matplotlib`。
- 0.2 白名单：`scripts/solana/sqd_gap_repair.py`、`scripts/lib/solana_exact_validate.py`、`scripts/tests/test_sqd_gap_repair.py`、`CHANGELOG.md`、`references/scan-schemas.md`（仅 §14.8 `:1007-1008` 两行：`header.adopted.rows` 与 `header.adopted.source` 的说明列）、本目录 `W2_done.md`/`W2_red_evidence.txt`。**本段不改** `scripts/lib/producer_history.py`（登记需代码 commit 哈希，调度方 commit 后另派 W2 第 2 段）。
- 0.3 行号为基线 `6782e9c`+2 提交（HEAD 含盲审提示词），旁附锚文本；不符即停工写明。
- 0.4 先红后绿：`W2_red_evidence.txt` 记盲审两条内存复现在基线上成立（前缀乱序被 `_verify_adopted_record` 接受；深验对乱序台账不报 adopted invalid；source 错值被两处接受）。
- 0.5 定向测试全 PASS 贴尾行：`test_sqd_gap_repair.py`、`test_batch8_repair_scale.py`、`test_batch7_validator_coverage_gaps.py`、`invariant_scan.py`、`changelog_lint.py`、`docs_lint.py --all`、`test_version_consistency.py`；`test_producer_registry_current.py` 本段**预期 FAIL**（sha 变、待第 2 段登记），记录即可。
- 0.6 完成写 `W2_done.md`（改动文件:行、差异、尾行、自报禁读），末尾「待调度方 commit」。

## 1. 生产者复验 `scripts/solana/sqd_gap_repair.py`
`_verify_adopted_record(header, data_rows, plan)`（`:783`）在现有检查之上追加两条（任一不满足同样 `raise ValueError`，最终统一转 `ValueError("RPC ledger adopted record invalid")`）：
- `[row["slot"] for row in data_rows[:count]] == plan["candidate_slots"][:count]`（`:807` 锚 `for row in data_rows[:count]:` 的循环前后均可）。
- `adopted["source"] == f"pending-{digest}"`（`:800` 锚 `or not isinstance(adopted["source"], str)` 处从「是 str」收紧为等式）。
首次认领处（`:861` 附近）写入的 `source` 本就是 `old.name`，且 `old.name` 已被校验等于 `pending-<rows[0]["plan_digest"]>`，故等式对合法认领恒成立，无需改写入逻辑。

## 2. 深验 `scripts/lib/solana_exact_validate.py`
- `:1353`（锚 `and isinstance(adopted.get("source"), str) and _integer(adopted.get("ts")))`）：source 改为 `adopted.get("source") == f"pending-{adopted['predecessor_plan_digest']}"`（digest 格式已在前面校验）。
- 前缀关系：在 `:1518-1519`（锚 `all_candidates = set(plan_candidates["coverage"]) | set(`）之后、`:1520`（锚 `if adopted_valid:`）的摘要重算块内增加：按台账数据行 seq 顺序取前 `rows` 行的 slot 列表，必须 `== sorted(all_candidates)[:rows]`（与生产者严格同构：`sqd_gap_repair.py:607-608` 锚 `candidates = sorted(set(coverage.get("candidate_slots") or [])` / `| set(beta_slots))`，`:626` 锚 `"candidate_slots": sorted(set(candidates)),`，`:627-629` 两类候选写入 `plan_candidates`）；不满足 `reasons.append("RPC ledger adopted record invalid")`。收集方式：在 `:1369`（锚 `for expected_seq, row in enumerate(_jsonl_data(refs["rpc_ledger"])):`）循环之前初始化局部列表 `adopted_prefix_slots = []`，在 `:1387`（锚 `if adopted_valid and expected_seq < adopted["rows"]:`）分支内追加 `row.get("slot")`，不新增遍历；**按台账文件行序比较，不得先按 slot 排序台账**（否则掩盖乱序）；`:1404-1407` 的连续性/唯一性拒绝逻辑保持不动。

## 3. 测试 `scripts/tests/test_sqd_gap_repair.py`
在 E27(d)（入口 `:775`，函数正文 `:820` 起，`:1161` 锚 `GREEN E27(d):` 之前）补两组向量：
- **深验路径**：复用正向 gen（`:935-937` 锚 `gen = generation(case)` / `adopted_rows = read_rows(gen)`，两条数据行、`adopted.rows=1`），加入 `:972-993` 现有篡改循环（每个 mutation 从原始字节出发、同步 `bundle.rpc_ledger` 的 size/sha256、断言 reasons 含 `"RPC ledger adopted record invalid"`、然后恢复 ledger 与 bundle 原件）：①交换两条数据行并重编连续 seq（rows 仍 1）；②`adopted.source` 改为 `"pending-" + 另一 16hex`。循环结束后再次断言未篡改 gen 深验 PASS（若该循环已有此断言则沿用）。
- **续跑路径**：现有 pending 都不满足"两条成功数据行且只认领一行"（发布已把 pending 改名为 gen，`sqd_gap_repair.py:337`；after-commit 场景 `:1089-1094` 只有一条数据行）。构造独立 pending：从正向 gen **复制**台账与两份 slot 的证据到一个新 `pending-<gen 的 plan_digest>` 目录（复制品，不动 gen），对其做同样两种篡改（①交换两数据行并重编连续 seq；②`adopted.source` 改错目录名），**每个 mutation 都从复制品的原始台账字节独立开始**，调三参数 `load_resume_slots(pending, repair._ledger_header(plan), plan)` → 抛 `RPC ledger adopted record invalid`；**断言拒绝后恢复原始字节，恢复后再次调用，断言不抛且 completed 等于原两个 slot 的集合**，再进行下一向量。篡改与断言不得影响 `:1100`（锚 `assert (snapshot(old), snapshot(pending)) == before`）与 `:1110`（锚 `assert resumed[:len(committed)] == committed`）所依赖的原件。

## 4. 文档
- `CHANGELOG.md:101-107`（锚 `## [9.1.0] - 2026-09-23`）：删去工单编号、施工分段、A1/A2、「本段」等施工过程叙述；保留版本行为（常量化、认领接口与契约、信任与硬链接边界、登记与验证）；成本-质量指标一行按 CHANGELOG 头部规则（`CHANGELOG.md:7`：轮次数/Bash 调用数/交付用时 ＋ 质量指标）**保留但改为整版有据数字**，由调度方提供如下（不保留占位、不写施工分段）：工单复核 codex 5 轮（W1 r1–r5）＋ W2 复核 2 轮；盲审 codex 第 1 轮 FAIL（P0 0/P1 1/P2 1）→ 本工单消化后第 2 轮结果由调度方在 commit 前补入；外部链上调用 3 次（Helius getBlock 复现，约 30 credits）；交付用时自 2026-09-23 05:13Z 工单 v1 入库起算，收官时由调度方补终点；Bash 调用数未统计（写"未统计"）。索引行不动。
- `references/scan-schemas.md:1007-1008`（锚 `| \`header.adopted.rows\` |`、`| \`header.adopted.source\` |`）：`source` 行说明改为「旧 pending 目录名，必须等于 `pending-<predecessor_plan_digest>`；续跑/深验复核」；同表 `rows` 行说明补「前 rows 行的 slot 序列须等于候选集（coverage∪beta 排序）的前缀，续跑/深验复核」。

## 5. 第 2 段（调度方 commit 后另派）
`producer_history.py:235-262` 四条 9.1.0 条目的 `sha256`/`commit` 改为新代码 commit 的值（977a4823… 从未发布，直接替换而非追加）；`test_producer_registry_current.py` PASS。
