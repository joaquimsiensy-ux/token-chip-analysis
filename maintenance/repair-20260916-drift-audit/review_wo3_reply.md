<!-- 由 Fable 从 codex 只读复核任务 task-mu4g89eg-6h1nrl 的 Final output 段原样搬运 -->
# 工单R3复核：退回

锚点与三项替换的代码事实均通过；**退回原因是字节预算与指定替换冲突。**

[工单第 13 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260916-drift-audit/workorder_r3.md:13)允许净增 **49 B**，实际逐字替换的 UTF-8 增量为：

| 项目 | 锚点核验 | 字节增量 |
|---|---|---:|
| D1 | `references/environment.md:18`，恰 1 处 | +119 B |
| D2 | `references/scan-schemas.md:873`，恰 1 处 | +7 B |
| F3 | `references/data-pipeline-solana-scan.md:100`，恰 1 处 | +15 B |

合计 **+141 B**。按工单声明基线计算，`929831 + 141 = 929972 B`，超过上限 **92 B**。结合“只动指定片段”，原样施工无法满足验收条件，需修订替换文本或预算。

代码事实核验结果：

- **D1 通过**：[密钥选择逻辑](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:122)默认先读 `KEYS_FILE`，无条目才回退 `KEY_FILE`；显式 RPC 优先，显式 keys 文件覆盖默认池文件。8 个内存场景通过。
- **D2 通过**：[生产者](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1094)按 `index` 排序；[消费者](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:1558)要求各列唯一、首列有序。第二、三列递减的样例通过相关检查。
- **F3 通过**：[闭合条件](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/stake_decode.py:212)为 `abs(onchain - tot) <= 2`；差额 −2 至 2 均 PASS，±3 均 FAIL。

D2 依据中的“只查”需收紧：消费者还会按证据重算 `ordinal` 并核对完整映射；替换句本身正确。

报告已打印到 stdout。仅执行隔离函数及 AST 内存核验，未运行施工守卫；离线、未改文件、未 commit。8 个审查文件哈希前后相同，HEAD 保持 `078d9be`，工作树前后均干净。
