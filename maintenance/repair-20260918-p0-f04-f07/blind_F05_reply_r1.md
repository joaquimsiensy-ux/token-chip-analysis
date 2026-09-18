# 盲审 F05：PASS

未发现需要退回的 blocker、minor 或 nit。审查范围为 `d7baf54..332a582 -- scripts/`，依据工单 v3 及两轮复核意见。

本轮实跑登记守卫通过；8 项需要写盘的定向测试受只读沙箱限制，未实跑。报告全文已打印到 stdout，未写入文件。

**a）不变量与原始反例**

| 不变量 | 结论与代码位置 |
|---|---|
| 峰值供给上界 | 闭合。[facts_gate.py:201](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:201) 检查每个实体峰值；第 492–494 行在 derive 返回前执行 gate，覆盖 override、provenance、exploration 来源。正式 derive 在第 340–342 行要求总供应为正。 |
| override 证据内容一致 | 闭合。[facts_gate.py:411](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:411) 先验路径和 SHA，第 423–429 行按 entity_id 核对 peak_raw、peak_date。旧哈希、缺实体、数组及内容不匹配均拒绝。 |
| 严格日期及条件上界 | 闭合。[facts_gate.py:443](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:443) 同时覆盖 override、provenance；解析后回写比较，拒绝 `20260102`。存在 current.date 时检查日期上界。 |
| decimals 绑定指定来源 | 闭合。[audit_release_gate.py:1586](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:1586) 归一链族后取值；第 1604–1610 行拒绝获取失败、非整数观测及数值不一致。调用仅位于第 1907–1910 行的 new-analysis 分支。 |

原反例的 `{"note":"fixture"}`、peak=1000000、date=1900-01-01 组合，会在 derive 阶段因证据内容失败；观测值仍为 0 时，单独将 facts_inputs.decimals 改为 2，会被发布闸拒绝。

正式 HTML 路径调用发布闸，并在有错误时于写出前退出，见 [build_html.py:431](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/build_html.py:431)、第 487–493 行。本轮完成静态追踪和局部演算，未重跑完整 facts→A4→A5→HTML 链。

**b）六视角**

| 视角 | 结论 |
|---|---|
| ① 字段来源 | 符合工单。EVM 读取深验 witness 的 balance 收据绑定的 config.decimals；Solana 读取 accounting_mode.checks.decimals，生产者从 mint info 写入。核过 `shared_release_receipt.py:559–567、593–607、1445、2031–2045`、`accounting_gate_sol.py:213–226`。 |
| ② 失败分支 | 闭合。证据、日期、供给违规抛 ValueError；decimals 获取异常和缺值进入 errors；消费者重算失败阻断发布。未见新增失败分支放行。 |
| ③ 存量迁移 | 说明闭合，未执行案库迁移。[工单:24](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F05.md:24) 已明确更新所有证据引用的 SHA/path，再依次重建 facts、图 2 收据、A4、stage2、A5；符合先验哈希及 stage2 绑定 A4 的代码顺序。 |
| ④ 同族调用面 | 已核 build、HTML、stage2，以及 a4、batch D、P105 共享夹具调用。decimals 未进入 stage2；峰值和证据约束按设计经过共享 derive/gate 生效。`check_facts_vs_ledgers` 逐字未变。 |
| ⑤ producer/consumer 一致 | 已核共享夹具新证据格式、既有合法 override 迁移、Solana 夹具补 decimals=0。schema 未升级；宏、渲染及受保护函数未改。 |
| ⑥ 检查点可绕性 | 在工单边界内闭合。facts.json 为 new-analysis 必需件；局部演算确认：同 schema 手改峰值、清空 entities/decimals/provenance、将图 2 绑定改为 facts_alt.json，均被重算或绑定检查拒绝。 |

工单 §4 明示边界保持一致：证据只核值一致；日期没有下界，缺 current.date 时没有该日期上界；真实历史峰值超过当前供应会被保守阻断。未将这些已登记边界计为缺陷。

**c）测试真实性**

已通过 `git show d7baf54:<path>` 核对基线：

- 基线不读取 override 证据内容，也没有峰值供给上界、日期格式及日期上界检查。RED 中 16、18、19 两例、20、21 共六个拒绝断言失败，与基线行为一致。
- 基线发布分支没有 decimals 比较，a/b 记录的 `errors=[]` 与代码路径一致。收集器捕获 a 的预期 AssertionError 后继续 b，未将其 `exit=0` 冒充为 a 通过。
- RED 两份生产文件 SHA 与基线 blob 一致；新增 facts、P105 测试文件 SHA 与最终提交一致。
- 既有断言无删除、无改弱；合法 override、坏哈希、缺证据三类断言保留。

补充内存隔离演算确认：原始 note 反例及上述六个负例均由接受变为拒绝；合法证据保持放行。EVM/Solana decimals 0 放行、2 拒绝；缺失、布尔、字符串观测被拒，witness 异常进入 errors，缓存重复调用只深验一次。

这些演算对文件 I/O、既有三账检查和 witness 输入使用了替身，未计作端到端测试通过。

**d）回归与实际执行**

[F05_done.md:303](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/F05_done.md:303) 包含全部 9 项命令、结果尾行和 `exit=0`；报告内 diff 与实际提交 diff 完全一致。

| §0.8 项目 | done 记录 | 本轮 |
|---|---|---|
| test_report_facts.py | 21 类、41 个用例及宏/gate PASS | 未实跑 |
| test_audit_release_gate.py | 十一类契约 PASS | 未实跑 |
| test_state_from_facts.py | D-05 PASS | 未实跑 |
| test_a4_gate.py | 23 项通过 | 未实跑 |
| test_repair_batch_d.py | BATCH D 全部通过 | 未实跑 |
| test_review_20260804_p105.py | decimals 两例及 P1-05 PASS | 未实跑 |
| test_stage2_closeout.py | 28/28 PASS | 未实跑 |
| test_figures_from_facts.py | 图表契约 PASS | 未实跑 |
| invariant_scan.py | 登记守卫 PASS | **实跑 PASS，exit=0** |

本轮守卫尾行：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

前 8 项需创建临时目录或文件，其结果仅按施工记录核验。本轮另完成 6 个改动脚本的内存编译、受保护源码逐字比较及 `git diff --check`，均通过。未运行工单排除的 run_all.py、reseal 全套。

**e）工单符合度与只读收尾**

- scripts 差异为 **6 个文件，111 行新增、7 行删除**，全部在白名单；完整提交另有获准的 done、RED 两个交付文件。
- 注释、docstring、空白在内的全部变化均落在授权区间；无工单外改动。
- `references/`、`SKILL.md`、`commands-staging/` 的指定提交 diff 为空。
- 审查前后 HEAD 均为 `e727addb4c6131987386a4e72cd19c53607feb98`，工作树干净；受审脚本与 332a582 一致，5 份审查输入文件哈希未变。
- 全程离线，未修改文件、未 commit。首次系统 git 包装器的 xcrun 缓存写入尝试被沙箱拒绝，随后使用实际 CommandLineTools git 完成核验；该环境限制不计缺陷。