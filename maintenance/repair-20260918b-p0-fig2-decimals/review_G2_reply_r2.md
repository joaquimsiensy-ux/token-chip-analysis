# 工单G2复核r2：退回

仍有 **3 项需修订**。完整报告已打印到 stdout；全程只读、离线，未读取禁区。

**G2-R2-01：8 空格 schema 锚仍不唯一。**

位置：[工单 §2.5](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918b-p0-fig2-decimals/workorder_G2_decimals.md:72)。

实测 `grep -n -F`：

| 锚缩进 | 命中行号 | 数量 |
|---|---|---:|
| 12 空格 | 1356 | 1 |
| 8 空格 | 1356、1761 | 2 |

`grep -F` 匹配子串，8 空格锚也包含在 12 空格那一行中，仍会触发 §0.5 停工规则。

**建议：**这两条完整行锚改用 `grep -n -F -x`，同步明确匹配规则。实测加 `-x` 后各唯一命中。§2.6 的 **1586/1610 起止锚正确，1611 为空行**。

**G2-R2-02：新增 checks 回归按原文执行，改后仍必红。**

位置：[工单 §2.9](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918b-p0-fig2-decimals/workorder_G2_decimals.md:129)，关联 §2.6、§2.11。

断言要求包含 `缺失或非对象`，函数实际返回：

```text
facts.token.decimals 无链上观测来源可核（accounting_mode.checks.decimals 缺失或 checks 非对象）
```

字符串不匹配。内存执行确认：新函数不抛异常，但指定字符串断言为 **False**。

“基线返回拒收、GREEN→GREEN”也须区分链族：

| checks 为列表 | 基线函数 | v2 函数 |
|---|---|---|
| EVM，facts/config decimals 相等且绑定合法 | `[]` | 返回拒收理由 |
| Solana | 捕获 AttributeError，返回拒收理由 | 返回拒收理由 |

**建议：**沿用现成 EVM 夹具时，匹配 `checks 非对象`，记为 **RED→GREEN**。若验证 Solana 行为保持，明确链族，共同断言使用“errors 非空且不抛异常”，新文案另验。同步订正 §2.11 仍写“三处”的清单。

**G2-R2-03：迁移范围正确，但 wrapper 失效原因写错。**

位置：[工单 §4](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918b-p0-fig2-decimals/workorder_G2_decimals.md:150)、[台账 Q7](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918b-p0-fig2-decimals/code_change_pending.md:11)。

`receipt_validate.py:115–120` 确实默认只认当前 producer 哈希，但三者原因不同：

| 产物 | 实际变化 |
|---|---|
| supply_truth | 两链共用的 producer 被修改，旧哈希失效 |
| reconciliation wrapper | 自身 producer 为未修改的 `reconciliation_report.py`；需刷新 supply_truth 子项的 producer/receipt 引用 |
| shared receipt | 自身 producer 被修改，下游输入绑定也须重建 |

代码证据：

```python
# shared_release_receipt.py:75
RECON_RUNNERS = {"scripts/report/reconciliation_report.py"}

# shared_release_receipt.py:2145
raise ValueError("shared receipt producer mismatch")
```

因此不能写成三者“producer 哈希全部失效”或“一律 producer hash mismatch”。

**建议：**分别说明上述失效原因。两链迁移成本、完整旧 checkout/执行环境承接旧案、单填版本字段无效，这些判断成立。

其余实际核查结果：

- **R1-02 通过：**`nonempty_code.py` 全部 5 个用例在内存文件系统执行，基线 **5/5**；漏加字典字段时 **4/5**；补 `"decimals": 0` 后 **5/5**。
- **R1-03 通过：**c 例的 N＝**59,127,382**，human＝**591273.82**，nominal 仍为 N。重绑后两个收据的信封与深验均通过，supply_closure 修改前后全等；F-03 initial/final 快照检查返回 `[]`。
- **R1-04 函数修法成立：**列表及其他非 dict checks 均返回拒收理由，不再抛异常；问题在新增回归要求。
- **R1-05 通过：**读取范围说明与代码对应；四个守卫确为 `test_contract_routes.py`、`test_commands_deploy_sync.py`、`test_repair_batch3_gates.py`、`docs_lint.py`。本轮未运行会读取禁区的守卫。
- **R1-06 通过：**排除式 grep 无缓存命中，现有 18 处文本命中全部在计划替换范围内。
- **v2 变更面：**未发现新增白名单遗漏；确认新增的回归问题为 G2-R2-02。

c 例内存执行 decimals 检查的结果为：

```text
基线：[]

v2：
facts.token.decimals=2 与链上观测 0 不一致——state_source.facts_inputs.decimals 填错
verify_recon config.decimals=2 与链上观测 0 不一致——对账 human 供应量级自报
```

完整 `create_bundle → gate.run` 路径已静态推演：其他相关绑定不变，重建 shared receipt 后能够到达目标分支，支持“基线 `[]` → 改后双错误”。**完整落盘夹具未实跑**，上述完整路径结论与局部内存验证已明确区分。
