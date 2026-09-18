# 工单F05复核：退回

核心修法能满足 `price_gate_content` 终点判据；仍需修订 Q14 的影响范围、RED 取证准备步骤和双诊断的适用范围。

本次离线只读，未修改文件、未 commit，未读取 `~/.codex/`、memories 或其他禁读路径。`scripts/` 相对 `8b041842` 的 diff 为空。以下函数演练均在内存中进行，没有运行会创建夹具的完整 CLI 测试。

**F05-R2-01：Q14 将 ALL_SKIP 的影响范围写窄了。**

- **工单位置：**[§4，第233行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md:233)、[台账 Q14，第18行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/code_change_pending.md:18)。
- **事实：**正式候选链受到支持，不等于其全部代币、全部历史日期都有第二源价格。当前 `price_check.py`：
  - `:140` 每次只选一个第二源；不会在 DefiLlama 失败后自动再试币安。因此，`ALL_SKIP` 不证明“两种第二源都没有该币”。
  - DefiLlama 在 `:108-110` 对未收录或抽样时点无数据返回 `None`；币安在 `:117-122` 对没有相应日 K 返回 `None`。这些情况不限于新币早期。
  - `_get:87-100` 请求重试耗尽同样返回 `None`。全部抽样点如此时，`:165-180` 汇总为 `ALL_SKIP`，`:193-194` 退出 3。
  - 四条正式候选链 × 两种第二源 × 空数据／重试耗尽，共 **16 组离线演练**均得到 `ALL_SKIP`、退出 3，并被拟议 helper 拒绝。这里验证的是代码分支，没有查询线上覆盖率。
- **修订建议：**改为按实际条件描述：“所选第二源在全部抽样日期无法提供有效对照时，ALL_SKIP 的新增拒收也可能影响 ETH/BSC/Base/Solana 正式候选链，且不限币龄；人工比图不能满足当前 PASS/WARN 收据契约。”保留严格门槛及人工旁证另行裁决的安排。Robinhood 原已不能正式发布，应与本轮新增影响分开说明。

范围也不应扩大成“出现任何 SKIP 就拒收”：部分 SKIP 仍可能汇总为 PASS/WARN。另外，缺少 `--binance-symbol` 在 `:143-145` 是退出 1、无收据，不属于 ALL_SKIP。

**F05-R2-02：RED 准备步骤遗漏了必须先完成的三日价格夹具变更。**

- **工单位置：**[§2.5 RED 段，第224行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md:224)，关联 §2.3 第151行。
- **事实：**该段只列出先落 `write_price_receipt` 与 `sys.path` 改动。若按这两项准备，基线 `test_stage2_closeout.py:100` 仍只有一天价格。真实生产者在 `price_check.py:149-150` 提前退出，内存演练结果为：

  ```text
  [fatal] 价格序列过短（1 天），抽不成首/中/尾
  exit 1；未生成收据
  ```

  此时段1、3、6等会因输入过短而红，不能作为价格收据内容未被消费的 RED 证据，段7b的预期也无法按原步骤完成。
- **修订建议：**明确“先完成 §2.3 的测试侧变更，包括 `:100` 三日价格夹具，保持生产代码未改”。取证时先确认生产者达到各段预期退出码，再记录消费端断言的 RED；继续逐段捕获失败，7a不得遮断7b。

**F05-R2-03：双诊断说明误覆盖了主价格文件路径负例。**

- **工单位置：**[§1.4，第25行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md:25)，关联 §2.2 第126行。
- **事实：**`test_stage2_closeout.py:522` 和 `:541-544` 修改的是 `bindings.price_source.path`。新增 helper 读取的是**收据路径**，不会再次读取主价格文件路径。内存演练得到：

  | 失败对象 | 路径诊断数 | 来源 |
  |---|---:|---|
  | 主价格文件绝对路径／符号链接 | 1 | 通用遍历 |
  | 收据绝对路径／符号链接 | 2 | helper＋通用遍历 |

  表中只计路径诊断；主源路径变化还可能触发图2同路径约束。
- **修订建议：**将“双诊断可接受”限定为**收据引用路径失败**，不要将其套用于 `:522`、`:541-544` 的主源路径负例。既有遍历无需修改。

其余逐项核验结果如下。

| 项目 | 结果 |
|---|---|
| **a／R1-01** | 已落实。导语第5行和 Q8 均为“重跑价格收据→直接更新工单引用→完整 check 至 PASS→receipt-only”，明确禁用 amend；冻结字段和旧 PASS 收据前置条件的引用准确。 |
| **b／R1-02** | Q8 已列明四类新增拒收面，并区分 ARC 引用结构与旧收据迁移；Q9 已补“无顶层引用”的分支条件。Q14 尚需按 R2-01 修订。本次未读取实名存量案原件。 |
| **c／R1-03** | 已落实。§0.4 将 reseal 测试列入不改，§0.8 明确施工方不跑，§4 明确调度方 commit 后、主仓库干净且验收 worktree 同 HEAD 时补验；与 overlay 白名单逻辑吻合。 |
| **d／R1-04** | 段3已改为 RED，并明确逐段独立取证、段1不得截断后续。准备步骤仍需补齐，见 R2-02。 |
| **e／R1-05** | `:235` 返回、`:236-237` 空行、`:238` 锚、`:270/:299` 作用域、`:361-366` 结构检查与 `:368-381` 文件／哈希检查均准确。构造 `:181-185` 与落盘 `:187-188` 的区分准确。双诊断适用范围见 R2-03。 |

**f）§2 全部14个明示锚均唯一，行号全部一致。** 实际按完整锚文本匹配，表中长文本简写：

| 文件 | 锚识别 | 命中数／行号 |
|---|---|---:|
| `price_check.py` | `import datetime` | 1／30 |
| 同上 | `def _load_series(path):` | 1／46 |
| 同上 | `"points": results, "verdict": verdict}` 完整行 | 1／185 |
| 同上 | 来源 docstring 末行 | 1／27 |
| `stage2_closeout.py` | `def amendment_errors(row, field):` | 1／238 |
| 同上 | `if "price_source_checks" in bindings:` 完整行 | 1／350 |
| 同上 | “双源检查对象在场”完整 `need(...)` 止锚 | 1／354 |
| `test_stage2_closeout.py` | `sys.path[:0] = ...` 完整行 | 1／15 |
| 同上 | `def build_closeout_case(root) -> Path:` | 1／93 |
| 同上 | 单点价格写入完整行 | 1／100 |
| 同上 | 手写 PASS 收据完整行 | 1／102 |
| 同上 | 内联 `{"status": "PASS"}` 完整行 | 1／534 |
| 同上 | `def facts_vs_ledgers_rejects_hand_edit(cases):` | 1／605 |
| 同上 | TESTS 列表末行 | 1／631 |

`:44-45` 确为两空行。三份拟议源码在内存中拼接后均编译通过；340组合法状态组合的 verdict 汇总规则一致。19条既有引用 mutation 在内存演练中均保持 BLOCK 和预期字段名；该演练替代了无关选材校验，不等同完整回归通过。

**g）终点判据仍成立。**

对其余输入有效的反例案，真实生产者以主 **50**／副 **100** 生成三点 **66.67%／FAIL**，退出 **2**。拟议 helper 在工单 **第96—98行**拒绝；按工单原样插入后的 `stage2_closeout.py` 对应 **第273—275行**，文案为：

```text
WORKORDER BLOCK: bindings.price_source_checks.verdict: PASS|WARN（FAIL/ALL_SKIP 禁入装配：换源或人工裁决后重跑 price_check） != FAIL
```

该错误使 `workorder` 检查为 BLOCK、整体 verdict 为 BLOCK，完整 `check` 的正常退出链返回 **2**。投影后的关键位置是 `:626` 调用、`:548` 记录 BLOCK、`:639` 汇总、`:1401` 返回2。生产者和 helper 已做内存函数演练；完整 CLI 退出链为源码核对。
