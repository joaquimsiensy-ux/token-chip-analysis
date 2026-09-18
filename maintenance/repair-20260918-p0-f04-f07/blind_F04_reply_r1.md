# 盲审 F04：PASS

审查范围为 `git diff b1ccf23..b794325 -- scripts/`。未发现应报缺陷，blocker／minor／nit 均为 0。工单不变量已闭合；本轮完成静态核查、原函数内存重放及 invariant 扫描，八个需要写临时夹具的完整测试未复跑。

开工、收尾 HEAD 均为 `114ef78748e08babef341956757654fadae2a39e`，工作树均为空。当前 `scripts/`、最新版工单、两轮复核意见及施工证据与 `b794325` 一致，以下行号对应该施工提交。

对照[工单 §2](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F04.md:28)，逐条核得：

| 不变量 | 结论及代码位置 |
|---|---|
| 两输入检查无新增错误才重算 | PASS。`scripts/report/audit_release_gate.py:1572` 保存错误数，1573、1574 分别检查 series／facts，1575、1576 在新增错误时返回。缺件、错 SHA、空绑定、符号链接均只报输入错误，重算调用次数为 0。 |
| 按实物、固定容差重算 | PASS。同文件 1579、1580 使用与输入检查一致的 basename 规则；1583 调用原 `fig2_check_errors`，容差固定为 0.05。 |
| 错误与指定异常拒绝发布 | PASS。同文件 1584 捕获指定六类异常，1585、1587 将失败加入错误列表。r1 的 series `[null]`、facts `[]`、401 位 current_raw 三例均返回“发布期重算失败”。 |
| 新用例接入实际测试入口 | PASS。`scripts/tests/test_repair_batch_c.py:1498`、1520、1543、1563 定义四例；1598–1601 调用；原 `main():2510` 仍调用 `t_r08_nonfinite()`。 |
| 指定断言订正，其他断言保持 | PASS。同文件 1453 改为拒绝 NaN 手写收据；原 NC1 1174–1198 及原 R08 后续 1454–1462 均逐字未变。 |

工单头部两组原反例的数值条件已独立重放：

- **90% 对 facts 10%**：基线消费者返回 `[]`；补丁报差 80pp。
- **1% 对 facts 100%**：基线返回 `[]`；补丁报差 99pp。

发布传播链已核到 [build_html.py:433](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/build_html.py:433) 接收错误，489–493 在写 HTML 前退出。原 `repro_formal.py` 的完整 A4/A5 场景本轮未实跑。

六视角结论如下：

| 视角 | 结论与实际核查 |
|---|---|
| ① 字段来源 | PASS。输入字节由 `audit_release_gate.py:1475` 的实物与 SHA 检查约束；百分比由 `figures_from_facts.py:330` 的 current_raw／total_raw 重算。收据自报的 PASS、lines_checked、mismatches 不能替代计算。 |
| ② 失败分支 | PASS。schema／mode／tol／verdict 原有拒绝分支保留；异常、数值不符、非 list series、空 pct 均产生错误。输入失败不重算；已有上游错误也不会使有效输入跳过重算。 |
| ③ 存量迁移 | PASS。schema 保持 v1；合法同源旧 PASS 仍可消费，错误数值或 NaN 的旧 PASS 被重算拒绝。§1.4 的输入检查顺序已满足；§4 明示接受的空 series 残余保留。 |
| ④ 同族调用面 | PASS。已搜索整个 `scripts/`。生产调用点为 `figures_from_facts.py:350`、`stage2_closeout.py:464`、新增 gate 重算；正式发布必经 `audit_release_gate.py:1842`。closeout 的 `stage2-dryrun` 边界保持；`test_a4_gate.py:530` 经 build_html 进入正式闸的回归路径已核。 |
| ⑤ producer／consumer 双向一致 | PASS。生产者 schema、formal、双输入 SHA 与消费者相容；双方使用同一校验函数及 0.05 容差。producer 数值路径、收据生成和 consumer 已在内存串联验证；第 3 例的原始 run 包装只添加一次解释器。 |
| ⑥ 检查点可绕性 | PASS，限工单范围。同 schema 手写 PASS 仍须重算；错误 series 改名仍拒。收据改名会缺必需资产；另名 facts 被 `audit_release_gate.py:1506` 的既有检查拦截。清空绑定、path、SHA、pct 均不能放行。空 series 属明确接受的残余。 |

[RED 证据](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/F04_red_evidence.txt:43)与基线行为一致。已用 `git show b1ccf23:scripts/report/audit_release_gate.py` 确认旧消费者未调用数值校验器。证据中的生产 SHA：

```text
23b6f95bd2a9a7f8a84ac2606886ca3ad503f0b0ce2a6359c3678f0ed81da334
```

与基线 blob 相同；测试、纯校验器及 RED 文件自身的 SHA 也分别与 Git 快照和 done 记录吻合。

以下为抽取两端原函数、保留原断言的**内存执行结果**。文件读写由字节缓冲承接，未启动真实 CLI、绘图库或磁盘收据写入。

| 用例 | 基线 | 补丁后 |
|---|---|---|
| `_f04_case_1`：90% 对 27.8% | RED，错误列表 `[]` | GREEN，拒绝偏差 |
| `_f04_case_2`：NaN 手写 PASS | RED，错误列表 `[]` | GREEN，重算失败 |
| `_f04_case_3`：27.8% 同源 | GREEN | GREEN |
| `_f04_case_4`：series 缺席 | GREEN，恰一条输入错误 | GREEN，相同结果、不重算 |
| 订正后的 `_r08_case_12` | RED，错误列表 `[]` | GREEN，直接拒绝及后续 FAIL 收据检查通过 |

原 `t_fc5_receipt_chain` 的 12 条断言在两种内存环境中也全部通过。未发现为变绿而弱化既有断言；1453 行是工单要求反转的旧缺陷行为。RED runner 的 exit=0 表示“三红两绿”符合预期。

[施工报告验收段](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/F04_done.md:226)列齐九项命令、结果尾行及 exit=0：

| 测试（scripts/tests/） | done 记录 | 本轮 |
|---|---|---|
| test_repair_batch_c.py | PASS，249 checks | 完整测试未实跑 |
| test_figures_from_facts.py | PASS | 未实跑 |
| test_audit_release_gate.py | PASS，十一类契约 | 未实跑 |
| test_a4_gate.py | 全部通过，23 项 | 未实跑 |
| test_repair_batch_d.py | BATCH D 全部通过 | 未实跑 |
| test_repair_g1_cross_target.py | PASS | 未实跑 |
| test_review_20260804_p105.py | PASS | 未实跑 |
| test_stage2_closeout.py | 28/28 PASS | 未实跑 |
| invariant_scan.py | PASS，81／118／65／61／61，exceptions=0 | **实跑 PASS，exit=0，计数一致** |

八个完整测试因只读沙箱无法创建临时夹具而未运行；真实 A4/A5 集成、CLI 落盘及冷字体缓存分支也未复跑。invariant 扫描在只读、离线审计护栏下执行，一次 socket 创建被阻止，扫描仍正常通过。未运行 `run_all.py`。

范围及工单符合度已机械核验：

- 全提交恰含四个白名单文件；脚本差分为 **107 行新增、1 行删除**。
- 生产补丁包含注释、docstring、空白，与 §2.1 逐字一致。测试仅新增四个函数、四行调用并订正指定断言。
- done 内嵌脚本 diff 与 Git 原始输出完全一致。
- `references/`、`SKILL.md`、`commands-staging/` 零改动；其他受保护文件、函数、常量未改。
- 脚本范围 `git diff --check` 通过。全提交另报证据文档空白：内嵌原始 diff 的空上下文行及 RED 末尾空行；属于白名单证据排版，可接受，不计代码缺陷。

全程离线、未改文件、未 commit，未通过工具读取所列禁区。首次系统 Git 创建 xcrun 缓存的尝试被沙箱拒绝，随后使用原生 Git。完整报告已打印到 stdout，未落盘。