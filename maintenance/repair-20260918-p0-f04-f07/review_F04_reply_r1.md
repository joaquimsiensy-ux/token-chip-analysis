# 工单F04复核：退回

v1 有 **4 项需要修订**。按现文新增的第 3 个用例会持续失败；重算异常也未完整转成发布闸错误。未发现需要修改 invariant manifest，或扩大生产代码白名单的理由。

复核对象为 [workorder_F04.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F04.md:1)。开工 HEAD 为 `4931098`，收尾核验快照为 `1e5c7e0`；并发提交包含其他工单变更，已确认 F04 工单与 scripts 未变。工作树前后均为空，`scripts/` 与 `311e6c4` 的 diff 为空。

**F04-R1-01：新绿例重复添加 Python 解释器，GREEN→GREEN 不成立。**

工单位置：[§2.2 第 3 例，第 57 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F04.md:57)。

事实：工单指定 `run([sys.executable, str(fff), ...], cwd=td)`，但 [test_repair_batch_c.py:60](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_c.py:60) 的既有包装已经添加解释器：

```python
def run(cmd, cwd, env=None):
    ...
    return subprocess.run([sys.executable] + [str(x) for x in cmd],
```

内存调用该原始包装，得到的参数开头是 `[python3, python3, figures_from_facts.py, "check"]`。实际执行展开命令返回 rc=1：

```text
SyntaxError: Non-UTF-8 code starting with '\xca'
```

此时尚未执行 figures 校验。

修订建议：改为既有调用方式，不修改共享 `run()`：

```python
p = run([fff, "check", "--facts", "facts.json",
         "--series", "ws.json"], td)
```

修正后重新记录第 3 例的基线绿证据，否则 `run_all.py:69` 中的 batch C 成员会因新增用例失败。

**F04-R1-02：except 漏接 AttributeError、OverflowError，会把数据错误变成未捕获异常。**

工单位置：[§2.1，第 43 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F04.md:43)。

事实：`fig2_check_errors` 并非只抛 ValueError。[figures_from_facts.py:298](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py:298) 只将装载阶段的 OSError/ValueError 转为 ValueError，后面仍有：

```python
# :309
eid = (line.get("entity_id") or "").strip()
# :330-331
cur = int(str(ent.get("current_raw", "0")))
want = cur / facts.total_raw * 100 if facts.total_raw else 0.0
```

用原始函数和工单补丁作内存执行，SHA 匹配的输入得到：

- series 为 `[null]`：未捕获 `AttributeError: 'NoneType' object has no attribute 'get'`。
- facts 顶层为 `[]`：未捕获 `AttributeError: 'list' object has no attribute 'get'`。
- current_raw 为 1 后接 400 个零、total 为 1000：未捕获 `OverflowError: integer division result too large for a float`。

`audit_release_gate.run:1756-1759` 只有 try/finally，无法把这些异常转成错误列表。

修订建议：except 补齐这两个已验证类型，并在白名单测试中验证其返回“发布期重算失败”：

```python
except (ValueError, OSError, KeyError, TypeError,
        AttributeError, OverflowError) as exc:
```

同时纠正异常依据：[Facts.__init__:110-116](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:110) 会设置 total_raw；缺 `total_supply_raw` 实际触发已被捕获的 ValueError。AttributeError 的真实来源是 JSON 结构错误，不是正常构造后的 Facts 缺 total_raw。

**F04-R1-03：必跑 batch C 与历史目录禁读冲突。**

工单位置：[§0.2，第 9 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F04.md:9)及 §0.8 第 15 行。

事实：完整 batch C 会加载被 §0.2 禁读的历史文件。[test_repair_batch_c.py:1549](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_c.py:1549) 原文：

```python
importer_path = (ROOT / "maintenance/repair-20260814-batch2/"
                 "import_pythia_legacy.py")
spec = importlib.util.spec_from_file_location("f09_pythia_importer", importer_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
```

第 2025-2030 行还有第二处加载；main 在第 2408、2416 行会进入这些路径。执行测试同样会读取该文件，无法同时满足完整 PASS 与该禁读边界。

修订建议：为这个既有测试依赖规定精确的读取例外，或将完整 batch C 验收交给有对应权限的调度方，并明确施工方的定向验证及交接条件。不能静默跳过相关用例后报全 PASS。本轮未加载该历史文件。

**F04-R1-04：F12 例外挂错测试文件。**

工单位置：[§0.8，第 15 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F04.md:15)。

事实：`test_stage2_closeout.py` 没有 `dry_run_touches_nothing`。实际定位结果：

```text
grep -n -F 'def dry_run_touches_nothing(cases):' scripts/tests/test_stage2_reseal.py
516:def dry_run_touches_nothing(cases):
```

该函数第 518-522 行才有外部 acceptance checkout 调用。工单当前清单并未列 `test_stage2_reseal.py`。

修订建议：删除 closeout 后面的错误例外，要求 closeout 全 PASS；如需验 reseal，另列该文件并把例外准确绑定到指定用例。

**锚点核对**

以下五个明确标为“锚”的文本均实际执行了 `grep -n -F`，每个恰好 1 处，行号一致：

| 文件 | 锚文本 | 行号 |
|---|---|---:|
| audit_release_gate.py | `    _figure2_input_check(case_dir, d.get("series"), "series", errors)` | 1571 |
| audit_release_gate.py | `    _figure2_input_check(case_dir, d.get("facts"), "facts", errors)` | 1572 |
| test_repair_batch_c.py | `def _r08_case_13():` | 1465 |
| test_repair_batch_c.py | `def t_r08_nonfinite():` | 1497 |
| test_repair_batch_c.py | `    _r08_case_13()` | 1510 |

其余所列引用也逐段核过：gate 的 16、1470-1471、1475-1494、1525、1551-1558、1817；figures 的 296-337；batch C 的 1111-1120、1112、1174-1198、1440-1452，均与基线相符。

batch C 第 1111、1112 行属于范例引用，不是唯一定位锚。对相应整行文本使用 `grep -n -F` 分别命中 **13、4 处**，后一项包括 `gate_mod` 的前缀匹配。施工应使用上述明确定位锚。

**修法与发布链核对**

- **basename 一致。** 新代码与 `_figure2_input_check:1479-1483` 使用同一定位规则。缺文件、符号链接或 SHA 不符新增错误后返回，符合 §1.4；已有 mode/tol/verdict 错误不会被清除。
- **局部 import 可解析。** build_html 以 report 目录脚本运行，stage2_closeout 第 26 行显式加入该目录；相关测试也设置了路径。
- **无显示环境已有处理。** figures 第 1-60 行自身没有 `matplotlib.use`，但第 56 行导入的 [standard_charts.py:37](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/standard_charts.py:37) 在 pyplot 前执行 `matplotlib.use("Agg")`；chart_style 第 20 行也设置 Agg。
- **缓存副作用确实存在。** 本机 matplotlib 导入时会初始化缓存；缓存和临时目录均不可用时可抛 OSError，工单 except 已覆盖。有效 new-analysis 发布链现有 `check_figure1_legend_receipt:1586` 已导入 figures；stage2_closeout 第 410 行也早已导入。新增的是直接调用图 2 消费者时的绘图库初始化。§4 宜补明缓存 I/O，不能把“一次性成本”理解成整个 import 过程零写入。本轮未执行冷缓存测试。
- **调用链需准确表述。** `a4_gate.py` 没有调用 `audit_release_gate.run`，只借用链名/正式链检查。stage2_closeout 第 563 行使用 `profile="stage2-dryrun"`，不进入图 2 收据消费者；build_html 第 433 行进入完整发布 run。
- **其余范围自洽。** §0.4 生产白名单足够；§1.3 三个 NC1 拒绝断言仍成立。§4 保留空 series、保持 schema、暂不强制 closeout 与改动相容。合法旧 PASS 收据仍可通过；“旧 PASS 自然失效”应限定为输入不符合当前校验规则的旧收据。

**回归面核查**

下表为源码及输入链核查结论，不代表完整测试已经实跑通过。

| 测试及调用位置 | series / facts 来源与预期影响 |
|---|---|
| [test_a4_gate.py:498](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_a4_gate.py:498)；build 在 530、557 | 三账生成 facts，507-513 对空 series 真跑 check。530 的正式绿例不新增图 2 错误；557 是 workflow_type 负例。 |
| [test_repair_batch_d.py:1205](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_d.py:1205)；run 在 1250、1265、1270、1286、1290、1294、1557、1559、1564 | 共用三账 facts、空 series、真实 check 收据。合法案不新增图 2 错误；篡改/删除 facts 先因 SHA/缺件拒绝。1613-1625 的同案 EVM check 使用 350/950，也同源。 |
| [test_repair_g1_cross_target.py:185](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_g1_cross_target.py:185)；统一入口 250 | 收据是 `{}`，在 schema 检查直接返回。r1-r10（含 r8a/r8b）、g1/g3/g4 只筛选跨分区错误；g2 走 independent-audit。 |
| [test_review_20260804_p105.py:214](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_review_20260804_p105.py:214)；run 在 261 | 三账 facts；222-228 对空 series 真跑 check。绿例不新增图 2 错误。 |
| [test_stage2_closeout.py:76](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_closeout.py:76) | 三账 facts；95-98 生成末点 100% 的 series，已有纯校验器核对。发布预检走 stage2-dryrun；179-180 明确要求图 2 收据不存在。 |
| [test_repair_batch_c.py:1133](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_c.py:1133)；1144、1155、1165、1175、1184、1193 | formal 绿例为 27.8%，对应 278/1000；exploration/FAIL 继续拒；SHA 变化及三个 NC1 负例在输入检查拒。既有断言无需改。 |
| [test_repair_batch_c.py:1452](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_c.py:1452)、1458 | 手写 PASS 绑定 NaN，是确认会反转的既有断言；工单已安排订正。1458 后的“非 PASS”断言仍成立。 |
| batch C 第 584、2361、2372 行 | 584 真跑 check，末点为 300/900；2361、2372 的来源链负例没有图 2 收据，不进入重算。 |

还核查了清单外的调用者：

- `test_repair_batch_b.py:418/436` 复用 p105 的真实空序列收据。
- `test_batch15_three_ledgers_frozen.py:369/395/418/421/428/447`、`test_batch18_shared_bundle_witness.py:147/172/180` 复用 batch D 的收据，后续未改变图 2 输入；包括错误列表逐字比较，不应新增图 2 错误。
- `test_audit_release_gate.py:494/502/509`、`test_repair_g1_audit_report.py:87`、`test_formal_chain_support.py:45`、`test_batch2_robinhood_exploration.py:83` 没有图 2 收据，不进入重算。
- `test_repair_batch1.py:1115` 将 required 过滤为图 1 收据；`test_build_html.py:93` 及两个 exploration 链的 build 负例在前置条件处拒绝。
- `test_figures_from_facts.py` 未直接调用图 2 收据消费者；生产者不改，未发现相应断言变化。

**四个新用例与 R08 断言**

抽取原始函数源码，在内存叠加工单补丁，以字节缓冲模拟文件读取，执行 SHA、JSON 与数值校验；未运行完整 CLI 或绘图库导入。

| 用例 | 基线 | 拟议补丁后 |
|---|---|---|
| 1：90% 对 27.8% | RED，消费者错误为 `[]` | GREEN，报末点差 62.2pp |
| 2：NaN 字面量 | RED，消费者错误为 `[]` | GREEN，报“发布期重算失败” |
| 3：真跑 check 同源 | 按工单命令为 RED | 仍 RED，须修 F04-R1-01；合法收据单独喂消费者，两侧均为 `[]` |
| 4：series 缺席 | GREEN，恰一条“不在案根” | GREEN，同一条错误，无重算消息 |

`_r08_case_12` 定义实际在第 **1430** 行；第 1440 行开始写 NaN series。准确旧断言在 **1453**：

```python
check("R08 同输入手写 PASS 基线消费者接受", errs == [], str(errs))
```

应改为：

```python
check("R08 消费者对 NaN 手写收据直接拒（F04）",
      any("重算失败" in x for x in errs), str(errs))
```

订正断言是 RED→GREEN；1454-1462 的 check 覆盖 FAIL 收据及“非 PASS”断言保持。应将这条订正断言的基线 RED 一并记入证据。

**invariant、字节约束与执行边界**

实际在内存中调用原始 `invariant_scan.main([])`，分别扫描基线及读取层叠加 §2.1 补丁的版本，两次 rc=0：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

修改文件的扫描结果完全相等。扫描器第 1143-1168 行登记 schema 比较及指定网络 import；新增错误文案和普通 figures import 不产生登记项。manifest 第 481 行已有图 2 schema，**无需加入修改白名单**。

仅用 stat 核得：SKILL.md **8021**、references Markdown 合计 **930061**、commands-staging Markdown 合计 **8798**；§0.1 限定 diff 为空。

当前沙箱只读，完整 batch C 需要创建临时目录，且有上述历史文件读取冲突，因此未执行完整 `python3 -B scripts/tests/test_repair_batch_c.py`；也未执行 `run_all.py`。实际执行范围为锚点检查、内存消费者验证、重复解释器命令和两次 invariant 扫描。

对 f) 的结论：照 v1 实施会让 suite 成员 batch C 因新增第 3 例失败；现有第 1453 行断言必须反转，工单已覆盖。除此之外，未发现其他既有断言因重算必然变红，不能据此宣称全套测试通过。

报告全文已打印到 stdout。未主动读取所列禁区，未联网、未修改文件、未 commit。首次系统 Git 的 xcrun 临时缓存创建被沙箱拒绝，后续已使用 CommandLineTools 原生 Git 完成核验。