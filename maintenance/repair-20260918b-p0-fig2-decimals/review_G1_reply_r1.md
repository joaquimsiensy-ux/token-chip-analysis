# 工单G1复核：退回

G1 的生产修法能够拦住指定 `empty_figure2` 反例，§2 锚点全部正确。需要修订的是测试取证步骤、缺线回归覆盖，以及 G2 联动反例的基线前提。完整报告已打印到 stdout；以下为复核结论及证据。

**G1-R1-01：消费者 RED 被前面的断言截断**

工单位置：[G1 §2.5，第107、111行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918b-p0-fig2-decimals/workorder_G1_fig2.md:107)。

工单要求先检查 producer，再构造 PASS 收据检查消费者。但既有 `check` 会立即抛错：

```python
# scripts/tests/test_repair_batch_c.py:55–56
if not cond:
    raise AssertionError(f"{name}: {detail}")
```

基线 producer 返回 `rc=0`，第一个断言就会终止 `_g1_case_1`，消费者检查不会执行。内存验证该顺序得到 `visited=['producer']`。

修订建议：将 producer、消费者拆成独立可调用测试，分别捕获 RED；或先执行并记录两项结果，再汇总断言。§0.7 的“§2.3/§2.4 新用例”也应改为“§2.4/§2.5”。

**G1-R1-02：“非空但缺线”没有回归用例**

工单位置：[G1 §2.2，第59行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918b-p0-fig2-decimals/workorder_G1_fig2.md:59)，以及 §2.4、§2.5。

拟议规则是：

```python
missing = sorted(fig2_required_entity_ids(facts.entities) - seen)
```

新增测试却只覆盖一个必画实体的空数组、重复线、非必画实体的空数组，没有覆盖“两个实体都必画，非空 series 只画了一个”。

修订建议：在现有测试白名单内补 `e1=大庄#1、e2=小庄#2`，series 仅含终值正确的 e1；producer、消费者均须指出缺 e2，再补齐两条线验证放行。本次内存执行确认该例可以形成有效 RED→GREEN。

**G1-R1-03：G2 新用例的“基线 errors=[]”不成立**

工单位置：[G2 §2.9，第129行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918b-p0-fig2-decimals/workorder_G2_decimals.md:129)，关联 ruling 的终点要求。这是联动前提核查，不代表完成了 G2 整单复核。

工单保留 `facts.decimals=0`，将 config 改成 2，却声称基线放行。实际基线代码是：

```python
# scripts/report/audit_release_gate.py
1603: observed = cfg.get("decimals")
1609: elif declared != observed:
1610:     errors.append(
              f"facts.token.decimals={declared!r} 与链上观测 {observed} 不一致"
              "——state_source.facts_inputs.decimals 填错")
```

抽取真实函数、将文件读取替换成内存输入后的结果：

| facts.decimals | config.decimals | 真实观测 | 基线专项闸 | G2 拟议专项闸 |
|---:|---:|---:|---|---|
| 0 | 2 | 0 | 已拒：facts 0 与“观测”2 不符 | 拒：config 2 与观测0不符 |
| 2 | 2 | 0 | 放行 | facts、config 均拒 |

原定断言可能因为错误文案不同而 RED，但不能证明原来的放行漏洞被修复。

修订建议：保留第一行作为诊断路径测试；另通过真实 facts producer 生成 `facts.decimals=2`，同步修改 config、human 数量并重建绑定，再验证完整发布路径的放行→拒绝。禁读 Documents 内的原始 review 未读取，不能擅自补全其未给出的 facts 取值。

**a）锚点核查**

所有 §2 锚点均符合工单：

| 文件 | 锚 | 命中数／行号 |
|---|---|---|
| figures_from_facts.py | `FIG1_LEGEND_RECEIPT_SCHEMA` | 1／60 |
| 同上 | `errs, okc = [], 0` | 1／307 |
| 同上 | `pct = line.get("pct") or []` | 1／320 |
| 同上 | `return errs, okc` | 1／337 |
| 同上 | entity_id／label 匹配说明 | 1／29 |
| stage2_closeout.py | `required = set()` | 2／171、211 |
| 同上 | `required.add(entity_id)` | 2／178、216 |
| 同上 | 局部 `import figures_from_facts` | 1／410 |
| test_figures_from_facts.py | 偏0.5pp断言 | 1／182 |
| test_repair_batch_c.py | `_f04_case_4` 定义 | 1／1563 |
| 同上 | `t_r08_nonfinite` 定义 | 1／1584 |
| 同上 | `_f04_case_4()` 调用 | 1／1601 |

“只改第1处”正确：171–178属于图2；211–216属于流转图。

开工核实项也成立：

- `Facts.entities` 写入点是 facts_gate.py:117。
- 图表测试 `FACTS` 确含 `e1.label=大庄#1`，终值27.84%。
- 三个既有空序列夹具的 label 分别为“实体1”、默认“e1”、默认“e1”，不属必画集合。
- §0.2 的 importer 行号过时：实际引用在 test_repair_batch_c.py:1640–1644、2116–2121。未读取 importer 本身。

**b）修法、来源和消费者**

完整上下文核查结果：

- `seen` 在匹配实体后记录，未知实体不进入；坏 pct 仍报原错误，不会放行。
- 按 id、按 label 匹配到同一实体的重复线也会被拒。
- 返回类型、非 list 固定句、装载阶段 OSError/ValueError 转换保持。
- closeout 新旧选材在220组正常 JSON 形态输入上，errors、notes完全一致。
- 单独调用选材函数将新增绘图库加载；正常 closeout 原本就会加载。`reseal --dry-run` 在这些检查前返回，未发现破坏其禁导 matplotlib 测试。
- `build_fig2_series` 仍允许生成选定子集，最终 check／发布闸负责覆盖。
- PNG 是否实际使用被核序列仍不受本工单保证，这是已有明确边界。

来源追踪确认：

| 来源断言 | 实际生产者 |
|---|---|
| facts 实体标签 | facts_gate.py:352–367读取 `facts_inputs.entity_labels`，399–405写实体标签 |
| whale_series | figures_from_facts.py:378–400装配，439–447写序列和旁车 |
| 图2收据 | figures_from_facts.py:279–293 |
| EVM 基线 decimals | **没有链上生产者**；observe_evm_supply只请求totalSupply及两个balanceOf |
| Solana checks.decimals | accounting_gate_sol.py:212–226从mint信息写出 |

因此 Q4 的标签规则限定准确，Q5 的 Solana 生产者描述准确；不能把 EVM verify_recon config 称为链上观测。

函数名全部命中如下，定义、注释及消费者均纳入：

| 函数 | 命中 |
|---|---|
| `fig2_check_errors` | figures_from_facts:296、350；stage2_closeout:464；audit_release_gate:1621、1645；test_stage2_closeout:574、582 |
| `fig2_selection_errors` | stage2_closeout:168、402；test_stage2_closeout:239 |
| `fig2_series_errors` | stage2_closeout:409、573；test_stage2_closeout:469、474 |
| `build_fig2_series` | figures_from_facts:378、439；stage2_closeout:458 |
| `mode_check` | figures_from_facts:340、483；test_repair_batch_c:1488 |
| `check_figure2_receipt` | figures_from_facts:353；audit_release_gate:1613、1905；test_repair_batch_c:1133、1144、1155、1165、1175、1184、1193、1452、1459、1515、1538、1559、1578 |

新增函数与常量在基线均零命中。`lines_checked` 只有283行写点，无消费者；`required_entity_ids`、`mismatches`、`whale_series`、收据名的全部命中及逐组判断已列入 stdout 报告，没有发现遗漏的发布消费者。

**c）既有测试回归面**

静态解析确认 run_all.py 登记151项，其中143个唯一 `test_*.py`。

**没有发现因 G1 修改必然变红的既有测试。** §1.3 的三个空序列正例、§1.4 的正常选材语义、§1.5 的指定返回及异常契约成立。

§0.8 未列、但已追踪的相关测试包括：

- `test_stage2_reseal.py:21、436、646`：复用 closeout；建议纳入定向回归。
- `test_batch15_three_ledgers_frozen.py:33、365–385`：复用非必画空序列夹具。
- `test_batch18_shared_bundle_witness.py:19–22、172、180–181`：同上，精确错误列表不会新增缺线错误。
- `test_repair_batch1.py:40、874、950`：图1路径。
- `test_build_html.py:93–94`、`test_repair_g1_audit_report.py:87–90`：缺资产／缺报告拒绝路径。

这是静态回归判断，不是143份脚本实跑全绿。

**d）实际验证结果**

只读沙箱不允许测试创建临时目录、图片和收据，因此使用真实函数的内存执行验证：

| 用例 | 基线 | 按工单修改后 |
|---|---|---|
| 必画实体＋空序列 | 放行 | 拒 |
| 真哈希旧PASS收据＋空序列 | 放行 | 发布重算拒 |
| 同实体重复线 | 放行，count=2 | 拒，count=1 |
| 非必画实体＋空序列 | 放行 | 放行 |
| 非空序列漏必画实体 | 放行 | 拒 |
| id／label混用重复实体 | 放行 | 拒 |
| 合法完整序列 | 放行 | 放行 |
| 非list及指定装载异常 | 原行为 | 保持 |

基线 `invariant_scan.py` 实跑 PASS。两份拟改生产文件的内存覆盖扫描也得到 `errors=[]`，登记面完全相同。没有运行真实 CLI／HTML 端到端测试。

**e）白名单和守卫**

白名单足够，以上测试修订仍可落在现有两个测试文件内。明确禁止修改的五个函数已在内存逐函数比较，原文不变。

无需新增 invariant、schema或契约ID登记。图2现有契约 needle `figure2-check-receipt/v1` 保留。

完整 `docs_lint.py` 会读取 attic/archive及全库Markdown，违反本次禁读要求，故未运行；仅在内存运行了新增模块docstring的相关检查，通过。契约路由测试需要临时文件，也未整跑。

Q3 所说“由 CHANGELOG 条目承载”尚未落地；本段禁止改 CHANGELOG，应明确由收官段补登。

**f）终点拒绝位置**

G1 的指定输入必然得到 `missing=['e1']`。错误产生于基线 figures_from_facts.py:337的替换块，即工单59–63行：

> 图 2 缺必画实体线 ['e1']（label 以 项目方/大庄/小庄/离场庄 起头的实体必须各有一条线；空 series 不得放行）

随后：

- producer 经基线364–370行写FAIL、返回1。
- 发布闸1645行重算，1649行加入上述错误，前缀为 `figure2 发布期重算:`。
- build_html.py:433–435收集错误，489–493在写文件前退出1。

仅实施G1不会修复decimals链。G2也实施后，真实观测为0、config为2时，工单G2:108的错误为：

> verify_recon config.decimals=2 与链上观测 0 不一致——对账 human 供应量级自报

accounting也被改成2而bundle仍为0，则共享校验器拒：

> EVM accounting checks.decimals is not the bundle observed decimals

旧v1 bundle会在当前校验器335–336行对应的schema检查处先拒：

> EVM observation bundle schema invalid

G2“基线放行”的完整反例仍须按 R1-03补正。

**g）迁移和版本**

G1虽不改格式，旧的缺线／重复线PASS收据会在新发布闸重算时失效；相关案例需要修复序列、重跑check并更新下游封口。宜在工单明示。

G2的Q7、Q8判断准确：旧v1没有decimals调用及transcript，必须重新采集、重跑accounting和supply_truth，并重建下游引用。**旧v1拒收属于不兼容变更**，按CHANGELOG.md:4的规则应采用主版本；钉旧版不能使新版本变成向后兼容。

全程离线、只读，未读指定禁区、未改文件、未提交。结束时工作区干净，生产及文档基线与f1f473f3的指定范围差异为空。
