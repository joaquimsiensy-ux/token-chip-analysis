# 工单E复核：退回

v1 不能原样派施工：两处事实表述错误，一项补验完成状态缺少核对依据。复核 HEAD：`1575ab5e1f4cb05d73a132306ffb9e2c6f7b584d`。

1. **E-R1-01：F01 行号沿用了施工前基线。**

   工单位置：[§2.4 详细段 F01，第 30 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/workorder_E_version.md:30)。

   事实：“`:175` 判点前”不符合当前源码。当前 `price_check.py:175` 是第二源选择分支；非有限值规范化位于第 **179** 行，SKIP 判点位于第 **180** 行。第 175 行作为判点位置仅适用于 `868d3f61`，工单 E 未注明这一限定。

   修订建议：改为“`price_check.py:179` 在判点前将非有限第二源价规范化为 None”，或明确注明施工前基线。

2. **E-R1-02：收官摘要把正常放行的 WARN 对照也写成了拒收。**

   工单位置：[§2.4「工艺」，第 31 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/workorder_E_version.md:31)。

   事实：[收官报告第 34 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/final_review_reply_r1.md:34) 明确记录：真实 `1.0/1.052` 收据在基线和 HEAD **均放行 WARN**。五组收据中只有四组异常场景由放行变为拒收，不能统称“均为基线复现原缺陷／HEAD 拒”。五组输入中的第二源 NaN 场景则生成完整收据、`ALL_SKIP` 退出 3。

   修订建议：分别写明“四组坏主价 fatal 1；第二源 NaN 生成 ALL_SKIP 收据、退出 3；四组异常收据 HEAD 拒，一组真实 WARN 两版本均放行；retail 两引擎基线复现缺陷、HEAD 拒”。

3. **E-R1-03：本机补验完成断言缺少可核对记录。**

   工单位置：[§2.4「字节与测试」，第 32 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/workorder_E_version.md:32)，关联第 31 行的 run_all 补验声明。

   事实：允许目录中的其他记录及本批提交说明，未提供 `run_all 151/151`、reseal `21/21`、九项守卫全 PASS，以及验收 worktree 同步 `84e70e5` 的完成记录。[F01 完成报告第 251 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/F01_done.md:251) 记载未运行 run_all，随后注明 reseal 待补验；[收官报告第 113 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/final_review_reply_r1.md:113) 仍记本机 run_all 待执行。源码登记数量确为 151 和 21，但不能据此证明全过。本项是未能核实，不认定调度方没有执行。

   修订建议：在允许目录补入已有的本机验收记录，注明命令、被验提交、退出码、结果尾行和 worktree 提交；尚未完成的保留待补验措辞。

其余实际核过的项：

- **锚点与改法**：`VERSION` 为 `b'9.0.0\n'`，6 字节、单个 LF；`pyproject.toml:15`、`SKILL.md:23`、CHANGELOG `:13`／`:97` 均正确且唯一。内存应用四文件改法后，版本一致性检查通过，SKILL 保持 8021 字节，活跃详细条目 79→80。
- **代码与字节**：F04 两文件 `+19/−1`，F01 三文件 `+59/−4`，合计五文件 `+78/−5`，文件集合无交集。函数、拒收文案、退出码、Solana 桶语义、逐点重算、阈值、6b–6g、12 项 checks、收据键及 manifest 均已对照。三处字节 **930076／8021／8798** 与基线一致；九项守卫均有对应文件。
- **过程记录**：F04 复核 4→通过、F01 5→1→通过，两段盲审 r1 PASS，均相符。七项／六项定向测试及 closeout 30/30 有完成记录；两次停工原因有停工报告及 `838f918` 提交说明支持。存量 28 文件零命中、零份 price_check 收据、LAYOFF 27 处与 Q4/Q5 一致，本轮未进入禁读案卷复测。
- **档位与纪律**：9.0.1 符合版本规则、限定后的兼容范围及用户明确裁决。§0 两项检查当前均为空；四文件白名单和 §3 报告要件可执行。两项 lint 确会读取 archive，交调度方执行的理由成立。

全程离线，未修改文件、未 commit，始末工作区干净。未读取 `~/.codex/`、memories 或其他禁读内容；references 字节统计仅使用元数据。报告全文已打印到 stdout，未落盘。
