# 盲审 W1 r1: FAIL

发现 **1 项 P1、1 项 P2，未确认 P0**。FAIL 原因是认领记录复验缺口，不是测试环境阻断。全程未改文件、未 commit，未读取禁读目录及施工报告。

**P1：续跑和深验未复核认领前缀，可能接受与认领规则矛盾的审计记录。**

位置：[sqd_gap_repair.py:783](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:783)、[solana_exact_validate.py:1387](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:1387)。

首次认领在 `sqd_gap_repair.py:860` 强制检查：

```python
adopted_slots == plan["candidate_slots"][:adopted_count]
```

但 `_verify_adopted_record` 和深验仅检查行数范围、请求摘要及前代计划摘要，没有复查该前缀关系。两处对 `adopted.source` 也只检查字符串类型，没有绑定到 `pending-<predecessor_plan_digest>`。

**已执行的只读内存复现：**

- 候选 `[10,20]`，把台账行排列为 `[20,10]`，声明认领首行；`_verify_adopted_record` 接受。
- 候选 `[10,20,30]`，提供摘要、证据对应的 slot `999`；三参数 `load_resume_slots` 返回完成集合 `{999}`。
- `adopted.source` 分别改为空串、错误摘要目录名、跨 mint 相对路径，均被接受。

**完整产物复现方法：**取 E27(d) 成功产生的两行台账，交换数据行并重编连续 `seq`，保留 `adopted.rows=1`；更新 bundle 中台账的大小及哈希，再深验。静态核对表明，现有深验按 slot 建表，未检查认领前缀顺序；前代摘要重算也不包含该行序和 `source`。完整产物实验受只读沙箱限制，未执行。

影响是**认领审计记录可能错误地宣称某行来自前代**；尚未证明能产生错误修复边。此处要求的是可离线复验的内部一致性，不要求证明外部来源真实性。

E27(d) 的候选集外向量仅覆盖首次认领，未覆盖认领后的续跑/深验：[test_sqd_gap_repair.py:1044](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:1044)。应在两条复验路径补同一前缀约束及来源目录名等式。

**P2：CHANGELOG 混入施工阶段叙述，不利于理解版本整体变化。**

位置：[CHANGELOG.md:103](/Users/uravvv/.claude/tca-fix-txv1/CHANGELOG.md:103)、[CHANGELOG.md:107](/Users/uravvv/.claude/tca-fix-txv1/CHANGELOG.md:107)。

复核方法：对照 `git diff --numstat main...HEAD -- scripts` 与“本段仅登记、文档与版本，新增生产逻辑 0”。后者限定施工阶段，而 9.1.0 实际包含明显生产逻辑增加。建议删去工单编号、施工分段及成本记录，保留版本行为、兼容性和验证边界。

**其余核对结果：**

- 常量化未发现遗漏。生产代码现有 **16 处**请求字典字段；原两份修复请求模板合并为一份。数值字面量仅保留在测试/检测逻辑中。
- 生产者与深验的计划摘要物料一致，包括 coverage、beta 候选并集；内存断言通过。
- 新增指纹检查覆盖 `bundle.reference == ledger.header.reference == ledger.row` 的 endpoint fingerprint 等式。
- 首次认领具备同 parent、登记 producer、拒已认领来源、目标台账存在检查、候选前缀检查及目标证据预检；残尾解析不改来源。复制/链接中断恢复路径静态检查未发现额外问题。
- 无 `adopted` 的两参数续跑及版本 0 请求摘要兼容，已用内存断言验证；batch7/batch8 全流程未能验证。
- E27(d) 的版本 1 请求确有独立字面量断言；候选集外负向向量也先证明证据对齐，再验证候选约束，隔离方式有效。
- 三份中文文档基本对应实现；认领记录的复验能力受上述 P1 限制。`SKILL.md` 仅更新版本，没有增加技能正文。

**指定测试实跑及尾行：**

| 测试 | 结果 / 实际尾行 |
|---|---|
| `test_sqd_gap_repair.py` | 退出 1：`PermissionError: [Errno 1] Operation not permitted: '/private/tmp/sqd-repair-cas-rs9m5ucw'` |
| `test_batch8_repair_scale.py` | 退出 1：`PermissionError: [Errno 1] Operation not permitted: '/private/tmp/batch8-keys-xw7722fr'` |
| `invariant_scan.py` | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| `test_producer_registry_current.py` | `producer registry: 0 FAIL` |

四项均使用指定的 `MPLCONFIGDIR=$HOME/.matplotlib python3 -B` 调用。前两项被沙箱阻止创建临时目录，不能记为回归通过；所有改动的 Python 文件另经不落盘编译检查通过。
