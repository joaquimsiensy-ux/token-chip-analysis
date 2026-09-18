# 工单F04复核：退回

v2 已闭合 r1 四条退回的核心问题；仍需修订 **2 处验收说明**。按 v2 的生产与测试改动一并实施后，未发现其他必然变红的既有断言，无须扩大生产代码或 manifest 白名单。

复核 HEAD 为 `92ff4fe144158a5f80025dba634f64835b25d1b2`，前后未变，工作树均为空。F04 的 gate、figures、batch C 三个脚本与 `311e6c4` 无差异。整个 `scripts/` 已包含 F06 的两个文件改动；工单 §0.1 的限定文件检查仍为空，不构成 F04 停工理由。

**F04-R2-01：§0.8 缺少已知冷字体缓存故障的验收处理。**

工单位置：[workorder_F04.md:16](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F04.md:16)，关联第 79 行。

事实：§0.8 要求清单全部 PASS，但未说明提示词已指出的 `data_broken: '_items'` 本机环境项。实际执行 `grep -n -F` 核得：

```text
scripts/tests/test_a4_gate.py:307:
    os.environ.setdefault("MPLCONFIGDIR", os.path.join(root, "matplotlib-cache"))
scripts/tests/test_stage2_closeout.py:17:
os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="w2-mpl-"))
```

两者默认选用新缓存目录。当前安装的 matplotlib `font_manager.py:275` 直接读取 `d["_items"]`；冷缓存初始化会调用该字体扫描路径，而第 1833–1846 行允许有效同版本缓存直接返回。[holder_distribution_scan.py:1004](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/holder_distribution_scan.py:1004) 将绘图异常转换为 `data_broken`。本机 `~/.matplotlib/fontlist-v3.11.0.json` 存在，内部版本与当前 FontManager 一致。

这能解释提示词给出的失败及重跑办法；**本轮没有重新实跑冷缓存测试，也未验证重跑后完整 PASS**。

修订建议：§0.8 补明，施工方在沙箱外遇上述特定错误时，保留首次失败输出，并使用既有缓存重跑：

```sh
MPLCONFIGDIR="$HOME/.matplotlib" python3 -B scripts/tests/test_a4_gate.py
MPLCONFIGDIR="$HOME/.matplotlib" python3 -B scripts/tests/test_stage2_closeout.py
```

重跑仍须实际 PASS，不得作为跳过项或 F12 豁免。§4 的 Agg 引用顺带订正为 `standard_charts.py:38`；第 37 行实际是 `import matplotlib`。

**F04-R2-02：§0.8 把生产 a4_gate 与 test_a4_gate 的调用范围混淆。**

工单位置：[workorder_F04.md:16](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F04.md:16)，原文：“`test_a4_gate.py` 不调用 `audit_release_gate.run`，只作回归对照。”

事实：测试经 build_html 间接进入完整发布闸。源码调用链如下：

```text
test_a4_gate.py:530:
    p_build = run(BUILD, ["--mode", "analysis-new", ...
build_html.py:254:
    formal_modes = {"analysis-new": "new-analysis",
build_html.py:433-434:
        audit_errors = audit_release_gate.run(
            Path(mddir), Path(a.md).resolve(), profile=formal_modes[a.mode])
audit_release_gate.py:1827-1828:
        if profile == "new-analysis" and "figure2_check_receipt.json" in data:
            check_figure2_receipt(case_dir, data["figure2_check_receipt.json"], errors)
```

修订建议：改成“生产 `a4_gate.py` 本身不调用发布闸 run；`test_a4_gate.py` 包含经 build_html 进入 new-analysis 发布闸的集成绿例，是本段直接回归面。”

r1 四项处置已核实：

| r1 项 | v2 处置与结论 |
|---|---|
| R1-01 重复解释器 | 已闭合。原始 `run():60-66` 只添加一次解释器；内存捕获参数确认 fff 是绝对路径、cwd 为 td，两个 JSON 相对路径均在 td 解析。 |
| R1-02 异常漏接 | 已闭合。原始校验器对 series `[null]`、facts `[]`、401 位 current_raw 分别抛 AttributeError、AttributeError、OverflowError；v2 均返回“发布期重算失败”。 |
| R1-03 历史依赖禁读冲突 | 已闭合。§0.2 精确允许测试进程加载指定 importer，覆盖 batch C 的 1549–1553、2025–2030 两处，并禁止施工方主动阅读、引用或改动。施工方无需读其源码即可执行完整 batch C。本轮未加载该文件。 |
| R1-04 F12 例外归属 | 已闭合。`dry_run_touches_nothing` 实际在 `test_stage2_reseal.py:516`，不在 closeout；v2 已移除错误豁免。 |

定位锚已实际执行 `grep -n -F`，均恰好一处：

| 文件 | 锚文本 | 行号 |
|---|---|---:|
| audit_release_gate.py | `    _figure2_input_check(case_dir, d.get("series"), "series", errors)` | 1571 |
| audit_release_gate.py | `    _figure2_input_check(case_dir, d.get("facts"), "facts", errors)` | 1572 |
| test_repair_batch_c.py | `def _r08_case_12():` | 1430 |
| test_repair_batch_c.py | `        check("R08 同输入手写 PASS 基线消费者接受", errs == [], str(errs))` | 1453 |
| test_repair_batch_c.py | `def _r08_case_13():` | 1465 |
| test_repair_batch_c.py | `def t_r08_nonfinite():` | 1497 |
| test_repair_batch_c.py | `    _r08_case_13()` | 1510 |

辅助引用也逐段核过：gate 的 16、1470–1471、1475–1494、1525、1551–1558、1817；figures 的 296–337；batch C 的 1111–1120、1174–1198、1440–1452。与基线相符。

batch C 第 1111、1112 行是范例引用，整行固定字符串分别命中 **13、4 处**，不能当唯一定位锚；v2 没有将其指定为施工定位锚。

修法与边界核查结论：

- basename 与原 `_figure2_input_check` 一致。两次输入检查增加错误即返回；NC1 三种缺件/错 SHA 拒绝结果保持原样，既有 mode/tol/verdict 错误不会被清除。
- 同目录 import 可解析：build_html 按 report 目录脚本运行，stage2_closeout 第 26 行显式加入目录，相关测试亦配置 sys.path。
- figures 第 1–60 行自身没有 `matplotlib.use`；第 56 行导入的 standard_charts 在第 38 行、pyplot 之前设置 Agg。没有新增显示器要求，但直接调用图 2 消费者会新增绘图库初始化与缓存依赖，§4 已登记。
- `audit_release_gate.py:1586` 的图 1 消费者原已导入 figures；stage2_closeout 第 410 行也早已导入。closeout 第 563 行使用 `stage2-dryrun`，不会进入图 2 收据消费者。
- 六类 except 覆盖本轮指定异常。`Facts.__init__:110-116` 会设置 total_raw；缺 total_supply_raw 实际报 ValueError。结构错误才是本轮 AttributeError 的来源。
- §0.4、§1、§4 的生产边界自洽：纯校验函数不写收据；模块 import 的缓存 I/O 已另行登记；空 series 仍放行；合法同源旧 PASS 仍可过；无需 schema 升版或将 closeout 改成必经。

回归面已按输入来源与断言核查；下表是源码与内存验证结论，**不是完整测试 PASS 声明**：

| 测试及调用行号 | facts / series 来源及预期 |
|---|---|
| [test_a4_gate.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_a4_gate.py:498)：build 530、557 | 498 三账生成 facts，507–513 对空 series 真跑 check。530 的集成绿例不新增图 2 错误；557 的 workflow_type 负例保持。冷缓存另按 R2-01 处理。 |
| [test_repair_batch_d.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_d.py:1205)：run 1250、1265、1270、1286、1290、1294、1557、1559、1564 | 1205–1211 使用三账 facts、空 series、真实 check 收据；手改/删除 facts 先由 SHA/缺件检查拒绝。1613–1625 的同案 EVM check 为 350/950，同源。 |
| [test_repair_g1_cross_target.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_g1_cross_target.py:185)：入口 250 | 图 2 收据为 `{}`，schema 检查直接返回，不重算；跨分区断言不受影响。 |
| [test_review_20260804_p105.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_review_20260804_p105.py:214)：run 261 | 214 三账 facts；222–228 空 series 真跑 check，仍无新增图 2 错误。 |
| [test_stage2_closeout.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_closeout.py:76) | 76 三账 facts，95–98 生成末点 100% 的 series，已有纯校验器核对；发布预检为 stage2-dryrun，179–180 要求图 2 收据不存在。冷缓存另按 R2-01 处理。 |
| [test_repair_batch_c.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_c.py:1133)：1133、1144、1155、1165、1175、1184、1193 | formal 绿例 27.8%=278/1000；exploration、FAIL、SHA 漂移与三个 NC1 负例继续拒。 |
| 同文件：1452、1458 | 唯一确认须反转的既有断言在 1453：NaN 手写 PASS 的“基线消费者接受”。v2 已安排订正；1454–1462 的 FAIL 收据及“非 PASS”断言保持。 |
| 同文件：584、2361、2372 | 584 真跑 check，末点 300/900；2361、2372 的来源链负例没有图 2 收据，不进入重算。 |

清单外的同族入口也已确认：

- `test_repair_batch_b.py:418/436` 复用 p105 的真实空 series 收据。
- `test_batch15_three_ledgers_frozen.py:369/395/418/421/428/447`、`test_batch18_shared_bundle_witness.py:147/172/180` 复用 batch D 的收据，后续未改变图 2 输入；错误列表逐字比较不会因此新增图 2 错误。
- `test_audit_release_gate.py:494/502/509`、`test_repair_g1_audit_report.py:87`、`test_formal_chain_support.py:45`、`test_batch2_robinhood_exploration.py:83` 没有图 2 收据，不重算。
- `test_repair_batch1.py:1115` 将 required 过滤为图 1 收据；`test_build_html.py:93` 及 formal_chain_support、robinhood_exploration 的 analysis-new 构建负例在前置条件拒绝。
- `test_figures_from_facts.py` 不直接调用此消费者，生产者保持不变。

四个新用例及订正断言已抽取原始源码、叠加 v2 补丁在内存执行，文件读取用字节缓冲承接：

| 用例 | 基线 | v2 补丁后 |
|---|---|---|
| 1：90% 对 27.8% | RED：错误列表为空 | GREEN：报末点差 62.2pp |
| 2：NaN 字面量 | RED：错误列表为空 | GREEN：报重算失败 |
| 3：27.8% 同源 | GREEN | GREEN |
| 4：series 缺席 | GREEN：恰一条“不在案根” | GREEN：同一条错误，无重算文案 |
| 订正后的 R08 case 12 | RED | GREEN |

第 3 例执行了原始 `mode_check` 数值路径，收据写入被内存捕获，消费者两侧均返回 `[]`；另捕获原始 `run()` 的 argv/cwd 验证命令构造。**没有实跑 CLI 或收据落盘**，施工方仍须取真实 GREEN 证据。

1453 行旧断言定位唯一，工单给出的订正正确：

```python
check("R08 消费者对 NaN 手写收据直接拒（F04）",
      any("重算失败" in x for x in errs), str(errs))
```

随后原始 `mode_check` 的 NaN 路径仍进入 FAIL；补丁后消费者同时保留“非 PASS”和重算失败，因此 1454–1462 的既有断言不受影响。

原始 `invariant_scan.main([])` 在基线与内存补丁上均返回 0，gate 单文件扫描集合完全一致：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

扫描器 1143–1168 登记 schema 比较及指定网络 import；新错误文案与普通 figures import 不新增登记项。manifest 第 481 行已有图 2 schema，**无须加入白名单**。扫描由只读离线护栏约束，urllib3 的本机 IPv6 探测在创建 socket 前被阻止；未联网。

仅用 stat 核得 §1.1：SKILL.md **8021**、references Markdown **930061**、commands-staging Markdown **8798**。工单及三个目标脚本的收尾 SHA 与复核中快照一致。

报告全文已打印到 stdout。本轮未运行完整 batch C、其他需写临时夹具的测试或 run_all。对 f) 的结论是：1453 的既有断言反转已被工单覆盖，未发现其余用例因 F04 修法必然变红；冷缓存失败属于提示词已指出的本机环境项，不能据静态核查承诺沙箱外全套 PASS。全程未主动读取禁区、未修改文件、未 commit。