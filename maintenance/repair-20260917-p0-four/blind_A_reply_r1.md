# 盲审 A：FAIL

发现 **1 项 minor：完整提交范围超出白名单**。A 段代码符合提交内 v4 工单，未发现本段功能缺陷或静态回归。两个指定测试均被只读沙箱阻止，未完成验收；这不作为代码缺陷。

报告全文已打印到 stdout。

**A-01｜minor｜提交范围包含白名单外文件**

- **位置**：[maintenance/repair-20260917-p0-four/review_B_prompt.md:1](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/review_B_prompt.md:1)。
- **事实**：`git diff --numstat f710fad..c6a306f` 包含该文件的 **16 行新增**，但工单 §0.3、§1.2 未将其列入白名单。
- **判断**：commit 标题明确注明合并了 B 段复核提示词，可以解释来源，且没有运行影响；但完整范围仍不满足白名单约束。此项属于提交打包偏差，不据此认定 A 施工者越权。
- **修法建议**：调度方拆分 B 提示词并重新给出 A 范围；或明确登记该调度文件为范围例外。无需因此修改 A 段代码。

**审查基准**

`f710fad`、`c6a306f` 内的工单均为 **v4**，字节相同；提示词中的“v2”已过时。十三个用例与 v4 对应。

已确认当前检查的 scripts、工单、施工报告及 RED 证据与目标提交相同。下文简称：

- F＝[scripts/report/figures_from_facts.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py)
- T＝[scripts/tests/test_repair_batch_c.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_c.py)

**不变量**

| 项目 | 核验结论及代码行 |
|---|---|
| JSON 非有限字面量 | F:63–65、79–81 默认拒绝 NaN/Infinity/-Infinity；check 的 facts、series 均严格解析，见 F:299–302。 |
| pct 全序列合法性 | F:68–76 排除 bool、非数值、非有限数及超大整数转换溢出；F:324–328 检查全部点，中间坏值不能靠合法末点通过。 |
| FAIL 收据 | 数值错误经 F:364–370 写 FAIL；解析 ValueError 经 F:351–361 写 FAIL、覆盖旧收据。新增分支写入失败时明确提示“收据未更新”并 FAIL 退出，不能称为已成功留收据。 |
| 合法有限序列 | 实体匹配、末点换算和容差比较保持原样，见 F:305–319、329–336；内存执行确认合法单点、多点和有限超差例行为不变。 |
| fig1 兼容 | F:125 保留 `strict=False`；F:155–160 保留字段级检查，`burn_cum_pct` 的 NaN/Inf 仍报字段名和“非有限”。 |
| producer | F:403–405 的 `allow_nan=False` 拒绝 NaN/±Inf 输出，其余编码参数不变。 |

**六视角**

| 视角 | 结论 |
|---|---|
| ① 字段来源 | 通过。目标末点由实际 facts 的 `current_raw / total_supply_raw * 100` 重算；收据 SHA 来自文件字节，见 F:239–243、282、329–331。 |
| ② 失败分支 | 通过工单边界。非法 pct、解析失败均不返回成功；新增收据写入错误明确报告。普通 PASS/FAIL 写收据 OSError 的既有传播行为按工单保留。 |
| ③ 存量迁移 | 通过。schema、容差、绑定格式未变，合法旧序列无需迁移；非法旧序列须修复后重跑。升级本身不会刷新已有收据。 |
| ④ 同族调用面 | 核齐 **7 次调用、6 行**：F:125 宽松；217/218、299/300 严格；439 两次严格。另核 `stage2_closeout.py:458–468`，重放和对账复用相同函数，异常经 `:493–503` 转 BLOCK。 |
| ⑤ 双向一致性 | 符合工单。producer 拒非有限输出，consumer 另检查全部 pct 类型和 `1e400`。`allow_nan=False` 本身不拒 bool/字符串/null，完整类型检查由 check 承担。 |
| ⑥ 检查点可绕性 | 新约束成立。exploration 仍检查数值，发布消费者拒 exploration/非默认容差/非 PASS。用例 10/12 覆盖两种旧 PASS，用例 13 覆盖更新失败。顶层非 list 仍直接 FAIL、不更新收据；空 list 仍可 PASS，均为工单要求保持的基线边界。 |

**十三个用例与 RED**

| 用例／T 断言行 | 基线行为及断言区分能力 |
|---|---|
| 1／1216 | NaN 错误 PASS；新断言要求非零、字面量诊断、FAIL 收据，能区分。 |
| 2／1236 | 基线忽略中间 `1e400`；新断言要求非有限诊断及 FAIL 收据，能区分。 |
| 3／1256 | 基线接受 `float("27.8")`；新断言拒绝字符串，能区分。 |
| 4／1276 | 基线 TypeError、无收据；新断言同时要求 exit 1 和 FAIL 收据，能区分。 |
| 5／1297 | 基线已因末点超差 FAIL；新断言要求解析层诊断和“输入不可用”，能区分。 |
| 6／1319 | exploration 下 NaN 基线仍 PASS；新断言检查 FAIL 和 mode，能区分。 |
| 7／1338 | facts 额外 NaN 基线放行；新断言要求非零及字面量诊断，能区分。本例未断言收据，与工单一致。 |
| 8／1356、1358 | 基线 dumps 输出 NaN；新断言必须抛 ValueError，能区分。 |
| 9／1376 | 合法序列在改前改后均 PASS，属于保行为回归例。 |
| 10／1395、1403 | 验证先 PASS、换 NaN 后 FAIL，并绑定新 SHA，能区分。 |
| 11／1424 | 基线忽略中间 Inf/401 位整数；新断言要求 FAIL 收据且无 OverflowError，能区分。列表推导不会被首个 Inf 短路。 |
| 12／1453、1459 | 先证明消费者接受旧 PASS，再要求覆盖为 FAIL、消费者拒绝，能区分。 |
| 13／1491–1494 | 基线抛 OSError；新断言分别要求 SystemExit、FAIL 原因及“收据未更新”，没有把任意异常算通过。 |

RED 的 **12 FAIL、仅用例 9 PASS** 与基线一致。

已机械确认：

- RED 基线生产文件哈希与 `f710fad` 一致。
- RED/GREEN 测试哈希均为 `ffd5a94e277acb2b930a964178cdac19df9c03bfd205e383a796e51952bc0b01`。
- 移除 A5 两处插入后，测试文件与基线**逐字节相同**，既有断言未弱化。
- 额外完成原函数的只读内存执行，相关分支符合预期；输入读取和收据写入接口被替换，**不代表真实收据落盘、fsync/replace 或绘图通过**。

**回归记录与本轮实跑**

[A_done.md:506](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/A_done.md:506) 包含全部五项的结果尾行、exit 0 和耗时，输出与测试源码相符：

| 测试 | 施工记录位置及结果 |
|---|---|
| test_repair_batch_c.py | :513，244 checks PASS |
| test_stage2_closeout.py | :519，27/27 PASS |
| test_figures_from_facts.py | :525，图表相关契约全过 |
| test_repair_batch1.py | :531，batch1 PASS |
| test_repair_batch_d.py | :537，BATCH D 全部通过 |

这些是施工记录，不能计作本轮独立实跑通过。本轮实际尝试结果：

- `test_repair_batch_c.py`：exit 1，`:1620` 创建 `/private/tmp/c-blind-fix1-…` 时遇 `PermissionError: [Errno 1] Operation not permitted`。
- `test_figures_from_facts.py`：exit 1，`:71` 遇 `FileNotFoundError: No usable temporary directory found`。
- 两者均未进入测试断言；其余三项及全套 `run_all.py` 未跑。

**工单符合度与只读收尾**

- scripts diff 仅两个白名单文件，**351 行新增、5 行删除**。
- 生产文件可由基线应用 A1–A4 原文逐字重建，无额外注释、docstring、空白或逻辑改动；测试仅 A5 两处插入。
- `A_done.md` 内嵌 diff 与目标 scripts diff 完全一致。
- `references/`、`SKILL.md`、`commands-staging/`、版本文件和两个 manifest 未触及；元数据字节数为 **8021 / 930070 / 8798**。
- `git diff --check` 通过；开工、收尾工作树状态均为空。全程离线、未改文件、未 commit，未主动读取禁读路径内容。

Codex session ID: 01a0af2f-fe0b-7d31-8713-77a4721cb1b9
Resume in Codex: codex resume 01a0af2f-fe0b-7d31-8713-77a4721cb1b9
