# 盲审 A：PASS

r1 唯一 finding **A-01 已消除，本轮未发现新问题**。结论针对工单 v4 与 `f710fad..212ede1`。两个指定测试均被只读沙箱阻止，未完成本轮实跑验收。报告全文已打印到 stdout。

下文 F＝[scripts/report/figures_from_facts.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py)，T＝[scripts/tests/test_repair_batch_c.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_c.py)。行号均指审查终点。

**范围修正**

完整 diff 仅含四个白名单文件：

| 文件 | 新增／删除 |
|---|---:|
| F | 38／5 |
| T | 313／0 |
| [A_done.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/A_done.md) | 584／0 |
| [A_red_evidence.txt](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/A_red_evidence.txt) | 154／0 |

B 段提示词已独立到 `ffe837b`。`references/`、`SKILL.md`、`commands-staging/`、版本文件及两个 manifest 均未触及。当前 HEAD 为 `6a3e0af`，四个审查文件及整个 `scripts/` 均与 `212ede1` 一致；工单在基线、终点和工作树均为同一份 v4。

**不变量**

| 核验项 | 结论与代码行 |
|---|---|
| JSON 非有限字面量 | F:63–65、79–81 默认拒绝 `NaN/Infinity/-Infinity`；check 的 facts、series 均严格解析，见 F:299–302。 |
| pct 全序列合法性 | F:68–76 排除 bool、字符串、null 等非数值、非有限值及整数转 float 溢出；F:324–328 检查全部点，中间坏值不能靠合法末点通过。 |
| FAIL 留痕 | 非法 pct 经 F:364–370 写 FAIL；解析 ValueError 经 F:351–361 写 FAIL。新增输入失败分支若写入失败，明确提示“收据未更新”并 FAIL 退出，不能称为已成功落盘。 |
| 合法有限序列 | 实体匹配、末点计算及容差比较未变，见 F:305–319、329–336；纯内存执行确认合法单点、多点及有限超差例行为不变。 |
| fig1 兼容 | F:125 保留 `strict=False`；F:155–160 字段级检查未改，`burn_cum_pct` 非有限值仍报告字段名和“非有限”。 |
| producer 输出 | F:403–405 增加 `allow_nan=False`，拒绝 NaN/±Inf；合法有限序列的序列化字节保持一致。 |

**六视角**

| 视角 | 结论 |
|---|---|
| ① 字段来源 | 通过。目标末点由 facts 的 `current_raw / total_supply_raw * 100` 重算，见 F:329–331；收据 SHA256 来自实际文件字节，见 F:239–243、282。 |
| ② 失败分支 | 通过工单边界。非法 pct 进入 errs；库函数输入错误继续抛 ValueError；CLI 转 FAIL。普通 PASS/FAIL 写收据 OSError 仍直接传播，属于工单明确保留的边界。 |
| ③ 存量迁移 | 通过。schema、默认容差、收据字段及绑定方式未变；合法旧序列无需迁移，非法旧序列须修复后重跑。升级代码不会自动刷新旧收据。 |
| ④ 同族调用面 | 核齐 `_load` **7 次调用、6 行**：F:125 宽松；217/218、299/300、439 两次调用默认严格。另核 [stage2_closeout.py:458](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:458)：重放复用 producer，对账复用 consumer，异常由 :493–503 转 BLOCK；其宽松读取按工单保留。[standard_charts.py:276](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/standard_charts.py:276) 仍接收调用方绘图数组，本轮不据此认定 PNG 与被检查序列绑定。 |
| ⑤ 双向一致性 | 符合工单。producer 拒非有限输出；consumer 进一步检查全部 pct 类型及 `1e400` 解析所得 inf。`allow_nan=False` 自身不拒 bool/字符串/null，完整类型约束由 check 承担。 |
| ⑥ 检查点可绕性 | 新约束成立。exploration 仍检查数值；[audit_release_gate.py:1352](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:1352) 拒绝 exploration、非默认容差和非 PASS。用例 10/12 检查两种旧 PASS 覆盖。F:362–363 顶层非 list 仍直接 FAIL、不更新收据；空 list 仍可 PASS，均为工单保持的基线行为。 |

**RED 与十三个用例**

已读取基线源码逐条推演。证据中的 **12 FAIL、仅用例 9 PASS** 与源码一致：

| 用例／T 断言行 | 基线行为及断言有效性 |
|---|---|
| 1／1216 | NaN 错误 PASS；断言要求非零、字面量诊断及 FAIL 收据，能区分。 |
| 2／1236 | 忽略中间 `1e400`；断言要求非有限诊断及 FAIL 收据，能区分。 |
| 3／1256 | 接受 `float("27.8")`；新断言拒字符串，能区分。 |
| 4／1276 | TypeError、无收据；断言同时要求 exit 1 和 FAIL 收据，能区分。 |
| 5／1297 | 基线已因末点超差 FAIL；新增解析层诊断与“输入不可用”断言能区分。 |
| 6／1319 | exploration 下 NaN 仍 PASS；断言要求 FAIL 并检查 mode，能区分。 |
| 7／1338 | facts 额外 NaN 被放行；断言要求非零及字面量诊断，能区分。本例未断言收据，与工单一致。 |
| 8／1356、1358 | dumps 输出 NaN；断言必须抛 ValueError，能区分。 |
| 9／1376 | 合法序列改前改后均 PASS，属于保行为回归例。 |
| 10／1395、1403 | 换成 NaN 后基线仍 PASS；断言要求 FAIL 且绑定新输入 SHA，能区分。 |
| 11／1424 | 忽略中间 Inf/401 位整数；断言要求 FAIL 收据且无 OverflowError。列表推导检查全部点，不会在首个 Inf 短路。 |
| 12／1453、1459 | 先证明消费者接受同输入旧 PASS，再要求覆盖为 FAIL 且消费者拒绝，能区分。 |
| 13／1491–1494 | 基线写 PASS 时抛 mock 的 OSError；新断言分别要求 SystemExit、FAIL 原因及“收据未更新”，没有把任意异常算通过。 |

独立重算哈希与记录一致：

- RED 基线生产文件：`0ba4e6607cbb8211a0e03311bdfa9dc61d1623bac7f289b7406e48f448213bd8`。
- RED/GREEN 测试文件：`ffd5a94e277acb2b930a964178cdac19df9c03bfd205e383a796e51952bc0b01`。
- GREEN 生产文件、RED 证据文件及工单哈希也全部匹配。

移除 A5 两处插入后，测试文件与基线逐字节相同；`t_fc5_receipt_chain`、`t_f04_tolpp_clamp` 及其他既有断言均未弱化。

**回归记录与本轮执行**

[A_done.md:506](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/A_done.md:506) 包含五个命令的 exit 0、耗时及以下尾行，与测试源码输出一致：

| 测试 | 记录位置／结果 |
|---|---|
| test_repair_batch_c.py | :513 — `PASS: repair batch C (F-05+F-04+fixround1+fixround2) 244 checks` |
| test_stage2_closeout.py | :519 — `stage2_closeout: 27/27 PASS`；源码确为 27 项。 |
| test_figures_from_facts.py | :525 — `PASS: figures_from_facts fig1白名单/legacy销毁键/legend receipt/burn豁免/overlay组成/价格绑定/flow宏同源/check终值对账全过` |
| test_repair_batch1.py | :531 — `PASS v6.41.0 batch1 steps 1-6 RV-07/RV-04/RV-17/F-03/F-01/A5v3/F-04` |
| test_repair_batch_d.py | :537 — `BATCH D 全部通过` |

这些是施工记录，不能计作本轮独立实跑通过。本轮实际尝试：

- `python3 -B scripts/tests/test_repair_batch_c.py`：exit 1，T:1620 创建临时目录时发生 `PermissionError: [Errno 1] Operation not permitted`。
- `python3 -B scripts/tests/test_figures_from_facts.py`：exit 1，:71 发生 `FileNotFoundError: No usable temporary directory found`。

两者均未进入测试断言。其余三个定向测试、完整十三例端到端执行及 `run_all.py` 本轮未跑。

补充完成原源码函数的纯内存执行：12 类非法 pct、合法序列、有限超差、facts NaN、exploration、写收据 OSError、非 list/空 list 兼容及序列化均符合预期。输入读取和收据写入被替换为内存接口，**不代表真实收据落盘、fsync/replace 或绘图通过**。

**工单符合度与收尾**

生产文件可由基线应用工单 A1–A4 原文逐字重建；测试仅有 A5 两处插入。没有额外注释、docstring、空白或逻辑改动。A_done.md 内嵌 diff 与目标 scripts diff 完全一致；`git diff --check f710fad..212ede1 -- scripts/` 通过。

开工与收尾工作树状态均为空。全程离线，未修改文件、未 commit。


Codex session ID: 01a0af38-b463-7053-a39f-c125a4231b75
Resume in Codex: codex resume 01a0af38-b463-7053-a39f-c125a4231b75
