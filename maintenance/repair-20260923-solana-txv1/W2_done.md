# W2 v3 完工记录

已完成 §1–§4：生产者与深验均复核认领候选前缀和来源目录名；两条路径的篡改回归及恢复正向验证通过。§5 登记本未改。7 项定向检查退出码均为 0；registry 按预期退出码 1（4 FAIL）。

## 基线与纪律

- 分支：`fix/solana-txv1`；开工 `git status --short` 输出为空。
- 基线 HEAD：`5ea0686bf90bfc6ff60fe2a87cbf95170b39934b`。编辑前逐一核对工单所列行号、锚文本和正向夹具，全部匹配，无停工项。
- 自报禁读：未读取 `~/.codex`（仅会话启动自动披露）、`~/Documents`、`~/Desktop`；未读取 API 密钥登记文件。
- 全程离线，使用本地 fixture；所有 Python 验证均设 `MPLCONFIGDIR=$HOME/.matplotlib` 与 `PYTHONDONTWRITEBYTECODE=1`。
- `.git` 只读；未执行 git add/commit 或其他 git 写操作。未运行 `run_all.py`；未修改 `scripts/lib/producer_history.py`。
- 工作区改动仅限工单白名单；schema 仅修改第 1007、1008 行的说明列。CHANGELOG 索引行未动。

## 改动文件与当前行号

- `scripts/solana/sqd_gap_repair.py:800`：source 必须等于 `pending-<predecessor_plan_digest>`；`:807`：前 count 行 slot 序列必须等于当前候选前缀，沿用统一异常。
- `scripts/lib/solana_exact_validate.py:1353`：绑定来源目录名；`:1370`、`:1390`：在既有单次遍历中按文件行序收集采纳 slot；`:1525`：与 coverage∪beta 排序后的候选前缀比较。连续性、唯一性拒绝逻辑未改。
- `scripts/tests/test_sqd_gap_repair.py:969`：交换两行并重编 seq、错误来源目录名两个 mutation；`:982`：加入深验篡改循环，同步外层 size/sha256，恢复 ledger/bundle；`:1006`：恢复后深验 PASS；`:1010`：独立 pending 复制两条成功数据及两份 slot 证据；`:1024`：每个 mutation 从复制品原始字节开始，三参数续跑拒绝后恢复；`:1037`：恢复后 completed 恰为原两个 slot。原 after-commit 场景及其断言未改。
- `CHANGELOG.md:103`、`:104`、`:106`、`:107`：删除施工编号、分段叙述与旧代码提交指向，保留版本行为和登记契约，补复验行为与整版已知成本/质量数字。
- `references/scan-schemas.md:1007`、`:1008`：补认领前缀及来源目录名约束和续跑/深验复核说明。
- `maintenance/repair-20260923-solana-txv1/W2_red_evidence.txt:1`：基线、内存复现代码、三组基线接受结果与新增测试红失败日志。
- `maintenance/repair-20260923-solana-txv1/W2_done.md:1`：本交接记录。

## 先红后绿证据

红证据路径：`maintenance/repair-20260923-solana-txv1/W2_red_evidence.txt`。

生产代码未改时，通过内存注入测试钩子运行原 E27(d) fixture；生产函数未打补丁。每次篡改从原始台账开始，更新 bundle 的 size/sha256，之后恢复原件并验证深验通过：

```text
W2 RED reordered-prefix: producer ACCEPTED; deep adopted-invalid ABSENT; deep_ok=True; reasons=[]
W2 RED empty-source: producer ACCEPTED; deep adopted-invalid ABSENT; deep_ok=True; reasons=[]
W2 RED wrong-source: producer ACCEPTED; deep adopted-invalid ABSENT; deep_ok=True; reasons=[]
W2 RED baseline reproduction: 3 vectors confirmed; restored generation PASS
```

随后仅补测试运行 `test_sqd_gap_repair.py`，退出码 1；新乱序深验断言失败，实际为 `ok=True, reasons=[]`，完整输出已追加红证据。再修改生产代码并执行以下检查。

## 定向检查尾行

统一命令前缀：`MPLCONFIGDIR=$HOME/.matplotlib PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/`，后接表内脚本与参数。以下为脚本实际末行（退出码单列）。

| 检查 | 退出码 | 尾行 |
| --- | --- | --- |
| `test_sqd_gap_repair.py` | 0 | `GREEN 29c implemented validate_current_candidates 已实现` |
| `test_batch8_repair_scale.py` | 0 | `PASS batch8: key-neutral identity/pool failover/ordered workers/resume/streaming` |
| `test_batch7_validator_coverage_gaps.py` | 0 | `批7 validator 覆盖缺口加固回归全部 GREEN (缺口1遍历主键 + 缺口3边slot窗口)` |
| `invariant_scan.py` | 0 | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| `changelog_lint.py` | 0 | `PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 83 条 + 归档 139 条` |
| `docs_lint.py --all` | 0 | `PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）` |
| `test_version_consistency.py` | 0 | `PASS: M-03 version metadata consistent at 9.1.0` |
| `test_producer_registry_current.py` | 1（预期） | `producer registry: 4 FAIL` |

`changelog_lint.py` 在写 CHANGELOG 前和改动后均通过。`git diff --check` 通过。

## 与工单差异及调度交接

- §1–§3 实现无偏离；红证据额外覆盖空 source，正式新增回归按工单覆盖乱序与错误目录名。
- §4 成本行仅使用已给出的整版事实：复核 7 轮（5＋2）、一轮盲审 FAIL 分布、链上 3 次约 30 credits、Bash 未统计、交付起点 2026-09-23 05:13Z。二轮盲审结果与交付终点尚未发生，未编造数字或填占位；按工单由调度方 commit 前补入结果、收官时补入终点与时长。
- §5 按授权范围不做；registry 的 4 项失败保留给代码 commit 后的登记任务。

待调度方 commit
