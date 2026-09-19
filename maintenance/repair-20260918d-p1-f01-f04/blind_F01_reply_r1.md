# 盲审 F01：PASS

审查 HEAD：`84e70e51059c136aef1fcd840c2eaea1bd24f400`；基线：`7a0b083`。

**a／b／c 全过；d 中 1 项 PASS、5 项 SANDBOX-BLOCKED，无真实 FAIL，符合指定结论规则。** 全文已打印到 stdout，未写报告文件。

全程只读、离线，无文件改动、无 commit；始末工作区均干净。未主动读取禁区或施工自述。指定工单当前标题为 v3，相对 v2 澄清了合法输入范围；本次按你列出的条件核验。

独立复现使用 `git show` 加载原始源码，通过内存文件替身与第二源替身执行真实业务函数。对照工单先经 `workorder_errors` 验证为 `errors=[]`。

实际核验结果：

- **主价格拒收**：三天 `date,close` 全 NaN，以及首日分别为 inf、0、−1，HEAD 均退出 1，无收据、无输出文件打开、无第二源调用。拒绝位置：[price_check.py:88](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/prices/price_check.py:88)。NaN 原文如下，其余三例计数为 1：

  `[fatal] 价格文件含非有限或非正价格 3 点（首个 ts=1767225600）：主价格文件先清洗再抽查`

- **第二源非有限值**：NaN／inf 带 `--out` 均退出 3，生成完整三点收据；全部 `second_price=null`、`deviation_pct=null`、`status=SKIP`，汇总 `ALL_SKIP`，无 ValueError。
- **消费者拒收**：[stage2_closeout.py:278](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:278) 对 NaN／0.0 主价返回含 `points[0].main_price`、`有限正数` 的错误。第二价改为 2.0、仍报 PASS 时，:286 返回 `points[1].status: 与 main/second_price 重算一致（FAIL） != PASS`。
- **WARN 边界**：1.0／1.052 的真实收据偏差 5.07%，放行并记 WARN NOTE；全部 status 和 verdict 改成 PASS 后，三个点均因重算为 WARN 被拒。
- **基线 RED**：三天 NaN CSV 在基线退出 0、verdict=PASS，收据含 `NaN` 字面量；`price_receipt_errors=[]`、`workorder_errors=[]`。

新增段按 HEAD 原始代码逐段独立执行：

| 段 | 基线实际表现 | HEAD |
|---|---|---|
| 6b | NaN、0 分别退出 0 并写收据，RED | GREEN |
| 6c | 第二源 NaN 判 PASS、退出 0，RED | GREEN |
| 6d | 主价 NaN，errors=[]，RED | GREEN |
| 6e | 主价 0.0，errors=[]，RED | GREEN |
| 6f | 66.67% 偏差伪报 PASS，errors=[]，RED | GREEN |
| 6g | 常量缺失触发 AttributeError；另独立验证真实 WARN 放行、伪造 PASS 后 errors=[]，RED | GREEN |

修法及兼容性核验：

- 在内存中移除许可改动后，与基线逐字相同：生产者仅指定五处；消费者仅 import、阈值常量、docstring、逐点重算四处。
- 测试仅新增 31 行 6b–6g；原段 1–7、19 条 mutation 未变。
- 15 组合法输入及 3 种补充格式对照，退出码、stdout、stderr、完整收据字节相同；比较时固定时钟。顶层仍 8 键，每点仍 6 键。
- 两端偏差表达式 AST 相同；阈值两侧共 8 例通过，含 4.99／5.01、14.99／15.01，以及舍入邻界 5.004／5.006、15.004／15.006。
- 19 条既有 mutation 在 HEAD／基线均 BLOCK，错误含对应 field 和 `WORKORDER BLOCK: ` 前缀；别名放行、符号链接拒绝。
- 汇总规则、哈希绑定、12 项 checks、返回类型、错误前缀未变；哈希缺失／不匹配及 FAIL／ALL_SKIP 收据仍拒绝。

白名单实跑：

```text
git diff --stat 7a0b083 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md

 scripts/prices/price_check.py         |  9 +++++++--
 scripts/report/stage2_closeout.py     | 23 +++++++++++++++++++++--
 scripts/tests/test_stage2_closeout.py | 31 +++++++++++++++++++++++++++++++
 3 files changed, 59 insertions(+), 4 deletions(-)
```

元数据核验全部吻合：`SKILL.md=8021 B`；`references/**/*.md=930076 B`；`commands-staging/*.md=8798 B`。

指定测试实跑结果：

| 命令 | 结果 |
|---|---|
| `python3 -B scripts/tests/test_stage2_closeout.py` | SANDBOX-BLOCKED，退出 1，尾行 E1 |
| `python3 -B scripts/tests/test_a4_gate.py` | SANDBOX-BLOCKED，退出 1，尾行 E1 |
| `python3 -B scripts/tests/test_audit_release_gate.py` | SANDBOX-BLOCKED，退出 1，尾行 E1 |
| `python3 -B scripts/tests/test_batch4_invariant_guards.py` | SANDBOX-BLOCKED，退出 1，尾行 E1 |
| `python3 -B scripts/tests/test_exemption_guards.py` | 前三条 EX-01 PASS，随后 SANDBOX-BLOCKED，退出 1，尾行 E1 |
| `python3 -B scripts/tests/invariant_scan.py` | PASS，退出 0，尾行 E2 |

E1，五项相同的实际错误尾行：

```text
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']
```

E2：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

另实跑四段 `python3 -B -c '…'` 内存审计，均退出 0，各段尾行：

```text
F01 producer endpoints and baseline RED: PASS
F01 exact 6b-6g: HEAD 6/6 GREEN; baseline 6/6 RED; 6g behavior RED confirmed
F01 structural contract audit: PASS
F01 format compatibility 3/3; existing binding/verdict contract 4/4: PASS
```

五项 SANDBOX-BLOCKED 留给调度方本机补验；按指令未跑 `test_stage2_reseal.py`，亦由调度方补验。
