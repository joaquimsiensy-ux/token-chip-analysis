# 工单F05复核：退回

拟议修法能拦住裁决中的真实 FAIL 收据；未发现 verdict 汇总、变量作用域或既有引用 mutation 的阻断性问题。但 v1 的迁移操作、存量兼容断言、reseal 补验安排和 RED 预期需要修订。

本次只读、离线，无文件修改、commit 或联网；未读取 `~/.codex/`、memories 或其他禁读内容。完整 CLI 测试需要创建夹具，本沙箱不允许，以下明确区分静态核对、不落盘函数演练和实际扫描结果。

**F05-R1-01：存量迁移不能使用 `stage2_closeout amend`。**

工单位置：[工单导语第 5 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md:5)、[台账 Q8](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/code_change_pending.md:12)。

事实：重跑收据后必须更新工单中的收据 SHA；`bindings` 属于冻结字段，`amend` 明确拒绝这种修改。代码原文：

```python
# stage2_closeout.py:82-84
def frozen_workorder(obj):
    return {key: value for key, value in obj.items()
            if key not in {"stage2_selfcheck", "amendments", "report_image_refs"}}

# stage2_closeout.py:727-728
if hashes["frozen_sha256"] != bound.get("frozen_sha256"):
    return ["工单冻结字段已改（frozen_sha256 漂移）：退回 −2 重跑 stage2_closeout"], None
```

`grep -n -F '工单冻结字段已改' scripts/report/stage2_closeout.py` 命中 **728**。没有旧 PASS closeout 收据时，`amend` 还会先在 **719–720** 拒绝。

修订建议：迁移步骤改为“用新生产者重跑价格收据 → 更新工单收据引用及 SHA → 完整运行 `stage2_closeout check` 至 PASS → `--receipt-only` 核验”。不要使用 `amend` 更新价格绑定。

**F05-R1-02：Q8 对 ARC 的免迁移断言过强，新增拒收范围没有完整交代。**

工单位置：[§2.5 段 7](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md:205)、[台账 Q8/Q9](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/code_change_pending.md:12)。

事实：内联 `dual_source_check.receipt` 只解决引用位置问题；收据仍必须满足新内容契约。工单代码原文：

```python
# 工单:101-104
bound = receipt.get("price_file_sha256")
if not isinstance(bound, str) or not bound:
    errors.append(workorder_error("bindings.price_source_checks.price_file_sha256",
                                  "在场（旧收据无此字段：用当前 price_check.py 重跑）", bound))
```

基线生产者 **181–185** 没有这个字段。段 7b 使用的是段 7 开头重新生成的收据，不能证明 ARC 的既有收据无需迁移。本次遵守禁读限制，没有读取实名存量案原件。

此外：

- 新逻辑也拒绝原先可放行的内联纯申报 dict，以及已绑定的 FAIL／ALL_SKIP 收据。
- `report-template.md:278` 的“exit 3 回退人工对 Dexscreener 图”，不能满足此次只接受 PASS/WARN 收据的 closeout 契约。
- Q9“字符串早已 BLOCK”只在没有顶层 `price_source_checks`、实际走内联分支时成立。基线 **350–354** 有顶层引用时不会检查该字符串。

修订建议：将 ARC 改为“内联引用结构可保留；所指旧收据仍须核验并按新契约迁移”，补充纯申报和 ALL_SKIP 人工回退路径的新增代价；给 Q9 加上分支条件。不要把未读取的存量原件描述为已经核实。

**F05-R1-03：reseal 本机补验还会被旧 overlay 白名单阻断。**

工单位置：[§0.3、§0.8](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md:12)。

事实：`test_stage2_reseal.py:518–519` 在主仓库运行时调用 `overlay_acceptance()`。其代码原文：

```python
# test_stage2_reseal.py:610-611
overlay = changed | untracked
assert overlay <= allowed, "白名单外变更，停止验收：" + str(sorted(overlay - allowed))
```

**604–609** 的 `allowed` 没有以下 F05 文件：

```text
scripts/prices/price_check.py
scripts/tests/test_stage2_closeout.py
maintenance/repair-20260918c-p1-f02-f04-f05/F05_done.md
maintenance/repair-20260918c-p1-f02-f04-f05/F05_red_evidence.txt
```

因此，在工单规定的不提交施工状态下，即使 `/tmp/w3_acceptance` 已存在，完整 reseal 测试中的 `dry_run_touches_nothing` 仍会失败。这不是单纯的沙箱或 worktree 缺失。

修订建议：明确补验是在调度方收录改动、主仓库干净且验收 worktree 同 HEAD 后执行；或者另行授权调整测试 overlay 白名单。当前 §0.3 足够完成生产修法和夹具迁移，但不足以支持未提交状态下修改该测试守卫。

**F05-R1-04：段 3 的基线预期应为 RED。**

工单位置：[§2.5 第 223 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md:223)。

事实：工单 **192** 要求：

```python
assert any("WARN 点 3" in n for n in notes), notes
```

基线不读取价格收据，也不会生成这条 NOTE。不落盘演练得到：

| 段 | 基线 | 按工单修改后 |
|---|---|---|
| 1：真实 FAIL | RED | GREEN |
| 2：篡改 verdict | RED | GREEN |
| 3：WARN 放行且有 NOTE | **RED** | GREEN |
| 4：主源哈希不一致 | RED | GREEN |
| 5：缺少主源哈希 | RED | GREEN |
| 6：ALL_SKIP | RED | GREEN |
| 7a：内联纯申报 | RED | GREEN |
| 7b：内联合格收据 | GREEN | GREEN |

修订建议：将段 3 改为 RED→GREEN；若要保留 GREEN→GREEN 描述，只能单独指“WARN 无错误放行”，不能包括新增 NOTE 断言。逐段取证还须保留后续段的执行，不能让段 1 的预期失败提前终止整函数。

**F05-R1-05：修正行号和“本函数不重复”的说明。**

工单位置：[§2.2 第 57、125 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md:57)，以及 §0.4、§1.4 的通用遍历范围。

事实：

```text
grep -n -F '    return errors, notes' scripts/report/stage2_closeout.py
```

其中 `flow_selection_errors` 的返回实际在 **235**；**236、237** 是空行。该文本全文件有 8 个子串命中，不能单独作为唯一锚；真正的 `def amendment_errors(row, field):` 锚在 **238**，唯一。

通用引用检查实际分两段：

```text
361:    for field, ref in required_refs:
368:    for field, ref in walk_objects(obj):
380:            except (OSError, ValueError) as exc:
381:                errors.append(workorder_error(field + ".path", "案内普通文件", str(exc)))
```

`required_refs` 遍历负责引用结构；文件读取、路径围栏和 SHA 重验在 `walk_objects` 遍历。新增 helper 的 `load()` 也会调用路径围栏，因此越界／绝对路径／符号链接收据会同时得到 helper 和通用遍历两条路径错误。演练已复现，§2.2“本函数不重复”不准确。

修订建议：将返回行改为 **235**，分别注明结构检查 **361–366**、输入路径与哈希检查 **368–381**；说明路径失败可能出现两条诊断，不必为消除重复而修改既有通用遍历。

另应准确表述来源：`price_check.py:181–185` 是唯一收据对象构造处，实际唯一落盘点是 **187–188**：

```text
188:            json.dump(out, f, ensure_ascii=False, indent=1)
```

以下是其余实际核过的项。

**a）§2 锚点。** 对工单完整锚文本实际执行了 `grep -n -F`。13 个明示锚全部唯一、行号一致：

| 文件 | 锚文本识别 | 命中数／行号 |
|---|---|---|
| `price_check.py` | `import datetime` | 1／30 |
| 同上 | `"points": results, "verdict": verdict}` 整行 | 1／185 |
| 同上 | 来源 docstring 末行 | 1／27 |
| `stage2_closeout.py` | `def amendment_errors(row, field):` | 1／238 |
| 同上 | `if "price_source_checks" in bindings:` | 1／350 |
| 同上 | “双源检查对象在场”完整 `need(...)` 止锚 | 1／354 |
| `test_stage2_closeout.py` | `sys.path[:0] = ...` 整行 | 1／15 |
| 同上 | `def build_closeout_case(root) -> Path:` | 1／93 |
| 同上 | 单点 `price_series.json` 写入整行 | 1／100 |
| 同上 | 手写 PASS 收据整行 | 1／102 |
| 同上 | 内联 `{"status": "PASS"}` 整行 | 1／534 |
| 同上 | `def facts_vs_ledgers_rejects_hand_edit(cases):` | 1／605 |
| 同上 | TESTS 列表末行 | 1／631 |

另核实 `_load_series` 定义唯一，在 **46**，**45** 为空行。三份拟议源码仅在内存中拼接，均可编译。

**b）作用域、状态规则与异常。**

- 完整读取了 `workorder_errors:265–405`。`errors/notes` 在 **270** 初始化，`required_refs` 在 **299** 初始化；替换 **350–354** 后的 `extend/append` 均在正确作用域，且发生在引用校验之前。
- 生产者状态集合确为 **PASS/WARN/SKIP/FAIL**，赋值位置是 **166、170**；verdict 规则确在 **178–180**。
- 对非空、合法生产者状态序列，汇总规则逐条等价：FAIL 优先；全 SKIP 为 ALL_SKIP；其余有 WARN 为 WARN；否则 PASS。枚举长度 1–4 的 **340** 组状态全部一致。
- 生产者的 SKIP 条件是 **165** 的 `p2 is None or p2 <= 0 or p1 <= 0`。新 helper 消费已有 status，不重新计算该条件、价格偏差或阈值；生产者仍先把百分比四舍五入到两位，再按严格 `>5`／`>15` 分类。未知状态和空 points 的拒绝属于新增结构约束。
- `safe_case_file` 对越界、绝对路径、符号链接等抛 `ValueError`；读取失败为 `OSError`；普通坏 JSON 的 `JSONDecodeError`、编码失败的 `UnicodeDecodeError` 均属于 `ValueError`。拟议捕获覆盖这些情形。
- 合格内联引用不会因加入 `required_refs` 而重复进行通用哈希检查；`walk_objects` 遍历的是工单对象。`self_reference` 要求字段严格等于 `fig3.events_input`，不会误豁免价格收据。异常路径的重复诊断见 R1-05。

**c）既有回归面。**

解析 `run_all.py` 得到 **151 项入口，其中 143 个 `test_*.py`**，与测试目录的 143 个文件一致。全 tests 的递归检索发现：价格收据夹具集中在 `test_stage2_closeout.py`；`test_stage2_reseal.py:21、436、646` 导入并复用它的 `build_closeout_case`，会自动获得新夹具。`test_reopen_cycle.py` 的简化工单用于重开流程，不消费价格契约。

按整个工单实施后，没有发现额外遗漏的价格夹具需要修改。确定会在未提交补验阶段变红的是 R1-03 所述 reseal 用例；不能把这一结论写成“143 个测试已实跑通过”。

三点价格序列只改变价格输入及其随文件计算的哈希；没有找到依赖它必须为单点的断言。`entity_series`、`whale_series` 的单点断言消费不同文件。

对 **503–544** 的原测试函数做了不落盘演练。19 条 mutation 均保持 BLOCK、统一错误前缀及预期字段名：

| 基线行 | mutation | 结果 |
|---|---|---|
| 504 | 删除主价格源 | BLOCK，含 `bindings.price_source` |
| 505、506 | 缺失／错配图 2 价格源 | BLOCK，含 `fig2.price_source\|price` |
| 507 | 删除价格检查引用 | BLOCK，含 `price_source_checks` |
| 508 | 删除主源 SHA | BLOCK，含 `bindings.price_source` |
| 509 | 删除实体序列 SHA | BLOCK，含 `fig2.lines[0].series_source` |
| 510 | 流转 spec SHA 为 null | BLOCK，含 `flow.charts[0].spec` |
| 511 | 缺失成交量引用 | BLOCK，含 `fig3.volume` |
| 512 | 自引用 key 错误 | BLOCK，含 `fig3.events_input` |
| 513 | 非豁免自引用 | BLOCK，含 `bindings.bad_self` |
| 514、515、516 | 缺 overlay／错 state／未验证 price_csv | 分别 BLOCK，含对应字段 |
| 517、518 | 缺图 2 输出／空事件 | 分别 BLOCK，含对应字段 |
| 519、520 | 错报告路径／图片清单重复 | 分别 BLOCK，含对应字段 |
| 521、522 | 越界输出／绝对主源路径 | 分别 BLOCK，含对应字段 |

同时，修改后的 **529–540** 别名、内联引用和 CSV 正例通过；**541–544** 符号链接负例继续拒绝。

**d）新用例与退出码。**

上述 RED/GREEN 是原函数和拟议代码在内存文件系统上的演练结果，未冒充完整 CLI 测试。完整 `test_stage2_closeout.py` 在导入时 **17** 就创建临时目录，故本次未运行。

真实生产者函数演练确认：

- `1/2`、`50/100`：三点 **66.67%／FAIL**，退出 **2**。
- `1/1.08`：三点 **7.69%／WARN**，退出 **0**。
- 第二源 `None`、第二源非正或主源非正：对应点 SKIP；全 SKIP 退出 **3**。
- 用单日输入触发真实 `sys.exit("[fatal] …")`，拟议 `write_price_receipt` 捕获后返回 **1**，没有尝试把字符串转换成整数。

**e）白名单与守卫。**

除 R1-03 的补验安排外，生产代码及夹具白名单够用；没有必要修改契约或 invariant 清单。基线扫描实际通过：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118,
transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

将三份修改仅投影到内存后，完整 scanner 校验仍为 **0 discrepancies**。两份生产文件的扫描清单前后完全一致：

- `price_check.py` 仍为 `requests` 类；没有 schema 登记或原子写点新增。
- `_sha256_file` 只读文件；`--out` 仍使用原有 `json.dump`。
- closeout 的 schema、网络类别和原子写位置均未改变。

`test_exemption_guards.py` 的三项只读正向检查在投影后实际通过。它的注入测试和 `test_batch4_invariant_guards.py` 完整测试需要写临时文件，未实跑；静态核对及投影扫描未发现此次修改触发其守卫的原因。

**f）终点判据成立。**

在有效反例案根中，主 **50**／副 **100** 产生三点 FAIL，生产者退出 **2**。按工单代码原样投影，closeout 在新增 helper 的 **273–275** 拒绝，原样文案为：

```text
WORKORDER BLOCK: bindings.price_source_checks.verdict: PASS|WARN（FAIL/ALL_SKIP 禁入装配：换源或人工裁决后重跑 price_check） != FAIL
```

随后 `workorder` 检查成为 BLOCK，整体 verdict 为 BLOCK，正常 CLI 流程返回 **2**。对应基线调用链是 **573 → 495 → 586 → 1348**；投影后的对应行为位置是 **626 → 548 → 639 → 1401**。函数演练已验证 verdict 错误，完整 CLI 退出链为静态核实。

**g）正式消费者和文档。**

在允许范围内递归检索 `price_source_checks|dual_source_check`，命中生产代码仅 `stage2_closeout.py`，另有测试夹具；references 和 commands-staging 没有这些字段的字面消费者。间接入口包括完整 `check`、`amend` 的重检及 reseal 的最终收口，没有找到遗漏的第二个价格收据内容消费者。

`--receipt-only` 保持已有冻结哈希及版本漂移检查，不重新消费价格收据；迁移应按 R1-01 重新执行完整 check。

`split-run.md:158` 的“价格源 path＋sha256 及双源检查结果”是概括性要求，与新收据引用契约没有直接冲突，可以保持零改动。需要修正的是 Q8/Q9 的兼容性与迁移表述，并明确 `report-template.md:278` 人工回退路径在此次收紧后的边界。
