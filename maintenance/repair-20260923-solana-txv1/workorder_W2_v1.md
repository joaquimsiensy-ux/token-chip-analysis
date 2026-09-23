# 工单 W2 v1 — 盲审 r1 消化：认领记录复验补「候选前缀＋来源目录名」约束；CHANGELOG 去施工叙述

> 来源：`blind_review_W1_r1_report.md`。P1＝首次认领（`sqd_gap_repair.py:861`，锚 `adopt: adopted slots are not a candidate prefix`）强制「采纳行 slot 序列 == `plan["candidate_slots"]` 前缀」，但认领后的两条复验路径——生产者 `_verify_adopted_record`（`:783-814`）与深验（`solana_exact_validate.py:1341-1353`、`:1387-1392`、`:1520-1527`）——都没复查该前缀关系，`adopted.source` 也只查是 str，未绑定到 `pending-<predecessor_plan_digest>`；盲审内存复现：候选 `[10,20]` 台账行排成 `[20,10]` 声明 rows=1 被接受、source 改空串/错误目录名被接受。P2＝CHANGELOG 9.1.0 正文混入「按 W1 v5、A1、A2 施工」「本段仅登记…新增生产逻辑 0」等施工分段叙述。

## 0. 纪律
- 0.1 分支 `fix/solana-txv1`；开工 `git status --short` 为空；`.git` 只读、commit 由调度方代做（不以此停工）；禁读 `~/.codex`（启动披露除外）、`~/Documents`、`~/Desktop`；离线；`MPLCONFIGDIR=$HOME/.matplotlib`。
- 0.2 白名单：`scripts/solana/sqd_gap_repair.py`、`scripts/lib/solana_exact_validate.py`、`scripts/tests/test_sqd_gap_repair.py`、`CHANGELOG.md`、`references/scan-schemas.md`（仅 §14.8 `header.adopted.source` 一行说明）、本目录 `W2_done.md`/`W2_red_evidence.txt`。**本段不改** `scripts/lib/producer_history.py`（登记需代码 commit 哈希，调度方 commit 后另派 W2 第 2 段）。
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
- 前缀关系：在 `:1518-1519`（锚 `all_candidates = set(plan_candidates["coverage"]) | set(`）之后、`:1520`（锚 `if adopted_valid:`）的摘要重算块内增加：按台账数据行 seq 顺序取前 `rows` 行的 slot 列表，必须 `== sorted(all_candidates)[:rows]`（与生产者 `plan["candidate_slots"] = sorted(set(coverage)|set(beta))` 同构，`sqd_gap_repair.py:595-596`）；不满足 `reasons.append("RPC ledger adopted record invalid")`。台账行按 seq 顺序的列表在 `:1370-1392` 的行循环里已逐行可得——若该循环只按 slot 建表（`ledger_by_slot`）而无有序列表，就在循环内顺带收集前 `rows` 行的 slot 到一个局部列表（不新增遍历）。

## 3. 测试 `scripts/tests/test_sqd_gap_repair.py`
在 E27(d)（`:775` 起，`:1161` 锚 `GREEN E27(d):` 之前）补两组向量，复用现有 E27(d) 的正向产物：
- 续跑路径：对认领后的 pending（提交后、发布前）把台账两数据行交换并重编连续 seq（保持 rows=1）→ 三参数 `load_resume_slots(pending, header, plan)` 抛 `RPC ledger adopted record invalid`；把 header `adopted.source` 改成 `"pending-" + 另一 16hex` → 同样抛。
- 深验路径：对发布 gen 做同样两种篡改（同步更新 `bundle.rpc_ledger` 的 size/sha256）→ `validate_repair_bundle_deep` reasons 含 `"RPC ledger adopted record invalid"`；并断言未篡改的 gen 仍 PASS。

## 4. 文档
- `CHANGELOG.md:101-107`（锚 `## [9.1.0] - 2026-09-23`）：删去工单编号、施工分段、A1/A2、「本段」等施工过程叙述；保留版本行为（常量化、认领接口与契约、信任与硬链接边界、登记与验证）；成本-质量指标一行按 CHANGELOG 头部规则**保留但改为整版口径**（例如：codex 复核 5 轮/盲审 n 轮/施工 3 段/外部网络调用 0）。索引行不动。
- `references/scan-schemas.md` §14.8 `header.adopted.source` 行说明改为「旧 pending 目录名，必须等于 `pending-<predecessor_plan_digest>`；续跑/深验复核」；同表 `rows` 行说明补「前 rows 行的 slot 序列须等于候选集（coverage∪beta 排序）的前缀，续跑/深验复核」。

## 5. 第 2 段（调度方 commit 后另派）
`producer_history.py:235-262` 四条 9.1.0 条目的 `sha256`/`commit` 改为新代码 commit 的值（977a4823… 从未发布，直接替换而非追加）；`test_producer_registry_current.py` PASS。
