# 工单F02复核：退回

发现两项需要先修订工单的问题：§2.6 的贯通测试使用了错误的供给量前提，改完生产代码仍会失败；§1.3 的“derive 产物逐字节不变”无法兑现。生产修法本身能满足裁决指定的三个 `flow_migration` 分支。

复核基于 HEAD `467ff4c0`、`8b041842` 行号。相关工作区源码与基线的 git diff 为空。完整测试结论均为静态推演；实际执行了内存编译和纯函数探针，没有实跑会创建临时夹具的测试脚本。报告全文已打印到 stdout。

**F02-R1-01｜阻断：贯通测试的 seed 实际为 current=100、total=100**

工单位置：[§2.6](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F02_circulating.md:137)，特别是第 137、144、155、157 行。

事实：`cases.fresh()` 复制的是 `test_stage2_closeout.build_closeout_case` 创建的 seed。该路径调用 `augment_gate` 时只有一个地址，未传 `balances`；实际供应量由下列代码产生：

```python
# scripts/tests/identity_gate_fixture.py
56:        balances = {row["address"]: 100 for row in rows}
38:    total = sum(balances.values())
65:                 "share_basis": "total_supply", "total_supply_raw": total,

# scripts/tests/test_audit_release_gate.py
391:                     "confirmed_economic_control_raw": "100",

# scripts/tests/test_stage2_closeout.py
39:        "schema": "provenance-ledger/v2", "total_supply_raw": "100", "entities": []}
76:    build_facts_from_ledgers(case, labels={"e1": "大庄#1"})
```

`test_a4_gate.py:192–206` 的夹具说明及执行代码也确认全案供应量为 100，并把三账同步到该 owner 快照。该文件其他用例手写的 `total=1000` 不属于此 seed。F05 工单的夹具修改只涉及价格数据，不改变上述数值。

因此 `current×5=500`，已经满足总量门槛 `500≥100`。工单第 144 行“没有包含下限错误”的断言在基线和改后都会失败；即使越过它，`raw="400"` 也会被新范围校验拒绝：

```text
facts_inputs.circulating_supply.raw 400 须在 (0, total_supply_raw=100] 内
```

第 155 行“只调整声明值”的补救不能改变总量分支已经命中的事实。另外，`build_release_case` 实际定义在 `test_stage2_closeout.py:50`；在 `test_audit_release_gate.py` 中 grep 命中为 0。

修订建议：此用例另建裁决指定的 `_r07_case` 独立夹具，固定 `total=1000、current=100、circulating=400`，调用真实 `derive_facts` 和 `flow_selection_errors`；保留公共 closeout seed。同步改正夹具定位和 RED/GREEN 描述。

**F02-R1-02｜要求不自洽：“未声明时 derive 产物逐字节不变”**

工单位置：[§1.3](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F02_circulating.md:22)，并关联 §4 的迁移说明。

事实：`derive_facts` 会把生产者文件自身的哈希写进产物。`grep -n -F` 命中：

```python
# scripts/report/facts_gate.py
489:                     "sha256": _sha256_path(Path(__file__).resolve())},

# scripts/report/audit_release_gate.py
1567:    got_prov.pop("producer", None)
1568:    want_prov.pop("producer", None)
```

修改 `facts_gate.py` 后，即使输入没有流通量字段，重新 derive 的 `provenance.producer.sha256` 仍会变化，完整 JSON 不可能跨版本逐字节相同。`test_report_facts.py:121` 只比较 token；`:140–148` 的幂等测试只比较同一版本连续 build，两者均不能证明这个跨版本承诺。

修订建议：改为“同输入、未声明时，除 `provenance.producer.sha256` 外产物不变；token 保持原三键；同版本重复 build 字节一致”。保留生产者哈希。补充区分：保留旧 facts 时，重算比较明确忽略 producer，可继续通过；主动重 build 后，文件哈希变化，需要刷新相关绑定，即使没有新增流通量。

**a）§2 锚点核验**

下列锚均实际用 `grep -n -F` 核验，命中数均为 **1**，行号符合工单：

| 工单位置 | 文件与实际行号 | 锚文本识别 |
|---|---|---|
| §2.1 | facts_gate.py:10 | token 示例整行 |
| §2.1 | facts_gate.py:66 | “可选，优先于 provenance 锚点…”整行 |
| §2.2 | facts_gate.py:380 | dual_basis 须为对象的 raise |
| §2.3 | facts_gate.py:477 | facts/token 初始化整行 |
| §2.3 续行 | facts_gate.py:478 | entities、metrics 续行 |
| §2.4 | stage2_closeout.py:209 | `circulating = int(circulating)` |
| §2.5 | test_report_facts.py:326 | 最后一个 F05 证据非对象用例续行 |
| §2.5 | test_report_facts.py:328 | “21 类”打印整行 |
| §2.6 | test_stage2_closeout.py:605 | `def facts_vs_ledgers_rejects_hand_edit(cases):` |

`price_receipt_content_enforced]` 当前命中 **0**。F05 尚未施工，其工单 §2.5 明确安排把列表末行改成包含该文本；这是依赖落地后的待核锚，不能现在记为已通过，也不单独作为本轮退回原因。

**b）插入点、类型和副作用**

已读 `derive_facts:324–495` 完整上下文。插入点之前，`total_raw` 在 `:340`、`fi` 在 `:355` 已赋值；`_raw_str` 定义于 `:317`，`_dt` 在 `:73` 导入。formal 与 exploration 都经过新增解析及 token 写出路径。

内存应用 §2.2/§2.3/§2.4 后，两个生产文件均编译通过；§2.3 保留 `:478` 续行的语法成立。新增 `test_report_facts` 代码也编译通过。`Facts`、`gate_check`、`build_main` 的 AST 保持不变。

`_raw_str` 实际调用 `:89` 的 `int(str(s))`：

| 输入 | 实际结果 |
|---|---|
| `True、False、400.0、400.5` | ValueError |
| `"abc"、"400.0"、"4e2"` | ValueError |
| `"-1"` | `_raw_str` 拒绝负数 |
| `"0"` | `_raw_str` 接受，新范围检查拒绝 |
| `"400"`、整数 `400`、`"+400"`、`"4_00"`、`" 400 "` | 归一化为 `"400"` |

所以 bool/float/非数字串不会被静默转成流通量；但这是沿用 Python 整数解析，并非“只接受纯数字 str”的类型白名单。

实际 `gate_check(Facts(facts))` 调用在 `:492`，`:491` 是注释。内存对照显示新增 token 字段前后 gate 结果相同，share 宏仍为 `10.00%`。不进入 G2 或宏分母的前提成立。

**c）同族消费者及“来源”断言**

已执行指定的 token 全库 grep，并补查 facts、Facts 和 facts.json 的间接入口：

| 消费点 | 核验结果 |
|---|---|
| `facts_gate.Facts :108–119` | 只提取 decimals、total_supply_raw；不限制 token 键集合 |
| `state_from_facts.compile_state :65–74、130–142` | 只从 facts.token 读取 total、decimals、symbol；新增键不进入 state 输出 |
| `stage2_closeout.flow_selection_errors :205–214` | 确实按 circulating_supply_raw 取值；原整数阈值不变 |
| `audit_release_gate.check_facts_vs_ledgers :1569–1573` | 对顶层字段用 `!=` 比较；轮到 token 时比较整个字典，自动覆盖两个新键及来源内容 |
| `audit_release_gate.check_facts_decimals :1592–1611` | 单独核 decimals，新增键不影响 |
| `build_html.py:422` | 经 load_and_check → Facts/gate_check，无 token 白名单 |
| `figures_from_facts.py:227、309、345、407` | 流转宏及图 2 对账仍按 total；fig2-series 取实体标签；无 token 白名单 |
| `a5_report_seal.py:331–392` | 不直接读取 facts.token；绑定 A4、正文和图片，影响体现为重封后的哈希变化 |
| a4_gate、distribution_explanation_check、closeout 绑定检查 | 消费 facts 文件身份/哈希；重建后须刷新绑定 |

grep 中其余 token 集合断言属于链身份 target、收据或 analysis-state，不是 facts.token 白名单。

**d）既有回归面**

`run_all.py` 的 SUITE 经 AST 汇总为 **151 项，151 个唯一入口**，不是 143 项。

指定测试 grep 找到的 token 精确相等断言是 `test_report_facts.py:121`；其夹具未声明流通量，改后仍是原三键。其他 `"token": {` 命中是夹具构造，没有因此自动变成键白名单。现有 `test_stage2_closeout.py:270` 手补 `raw="50"` 的直接消费者测试缺 source，新 NOTE 使用空字典回退，原错误断言仍成立。

静态检查未发现会被本段生产修改新增打红的既有断言。按原工单新增 §2.6 后，`test_stage2_closeout.py` 整个入口会因该新用例失败。

§0.8 未列但已追查的相关入口包括 `test_repair_batch_d.py:1205`、其夹具消费者 `test_batch15_three_ledgers_frozen.py`，以及 `test_stage2_reseal.py:21、436、646`。它们使用未声明流通量的生产夹具；reseal 有自己的 TESTS，不会自动执行新加的 closeout 测试。生产者登记守卫的清单也不包含本次修改的两个文件。

“21 类”改为“24 类”没有其他字符串消费者：`test_sixlens_docs` 扫旧大小口径等文本，`docs_lint` 的 Python docstring 扫描排除 scripts/tests，`casebook_lint` 只查判例文档；contract_manifest 无该文案针脚。写盘函数及 schema 未变，invariant manifest 的函数定位不因行号移动失效。以上为静态核验，不声称这些守卫已经实跑 PASS。

**e）新用例 RED/GREEN**

| 新用例 | 基线推演 | 改后推演 |
|---|---|---|
| 22 合法声明及发布重算 | RED：取新键时 KeyError | GREEN |
| 23 六种非法声明 | 六例各 RED：基线忽略未知键 | 六例各 GREEN：指定 ValueError 文案命中 |
| 24 无声明手补 token | GREEN：已有整 token 比较拒绝 | GREEN |
| §2.6 当前写法 | 前半已 RED，原因是总量门槛 | 仍 RED；400 还超过实际总量 |

22 的 KeyError 不在旧 `run()` 的捕获列表内（`test_report_facts.py:92`）。因此逐例 RED 取证须按工单末尾要求独立捕获，不能把整脚本第一次提前退出当成六个变体的证据。

`cases.fresh()` 的 seed 具备三账、identity_gate、provenance_ledger、state_source；`build_facts_from_ledgers` 还提供 peak_overrides 及匹配证据，默认生成 formal。因此 baseline derive 的问题不是缺件或 exploration，而是供给量与测试设想不符。

**f）裁决的三个 flow_migration 分支**

对 ruling 指定的 `_r07_case`（total=1000、current=100、label=大庄#1），按生产修改静态推演，三个分支均成立：

1. 声明合法的 `circulating_supply {raw:"400", asof, source}`：生成两个 token 新键，发布重算一致；`500<1000` 且 `500≥400`，空 flow 报 `WORKORDER BLOCK: flow.eligible_entity_ids: 包含下限 ['e1'] != []`。
2. 写扁平键 `facts_inputs.circulating_supply_raw="400"`：明确抛出 `facts_inputs.circulating_supply_raw 键名错位——流通量须写成 circulating_supply: {raw, asof, source}`。
3. 无声明而手补 facts.token：发布闸报 `facts.token 与三账重算值不一致`。

解析、选材及完整 token 比较均做了内存探针；比较探针注入了重算输入和文件在场条件，不能替代完整 derive/发布 CLI 实跑。§2.6 应换成上述正确夹具来固化终点。

**g）文档、迁移和版本**

`report-template.md:179` 已允许“≥20% 总供应或 ≥20% 流通”。`playbook-supply-recon.md:13` 要求第三方口径只作可比引用并注明口径。限定为附带 source/asof 的额外选材分母、保持链上供给/G2/宏不变，两者可以兼容；Q11 不应被解释成第三方数字已获得链上真值认证。

允许读取的 references 文档中，`facts_inputs` 命中为 0；字段 schema 集中在 facts_gate.py 的模块 docstring。`references/attic.md` 未读，不能把这个结论扩大为包含禁读文件的全量内容断言。仅用 stat 核得三项大小为 **8021、930076、8798 字节**，与 §1.1 一致。

未声明且保留原 facts 的旧案无需因 F02 强制迁移。主动加声明并重 build 后，还须处理 A4 封口、图 2 旁车/对账收据、工单、closeout，以及已有 A5/HTML 的相关绑定；仅重跑 check 不会修复它们。证据包括 `a4_gate.py:52` 强制封入 facts，以及 `stage2_closeout.py:422–426` 校验旁车 facts 哈希；现有 reseal 末段并不重建 fig2-series。若新命中选材下限，还要补流转图及报告引用。

版本意见：**F02 单段可定 8.1.0；三段合并倾向 9.0.0。** `CHANGELOG.md:4` 以兼容性划档；F05 已声明旧有效收据因缺新增必需字段而被拒，需要迁移，这符合不兼容持久化契约变更。Q12 保留用户最终裁决。

全程离线，未读取 `~/.codex/`、memories 或禁读目录内容，未修改文件、未 commit。初始 Git 启动缓存及 shell here-document 的临时文件尝试被沙箱拒绝；后续使用直接 Git 二进制及 `Python -B -c` 内存检查。
