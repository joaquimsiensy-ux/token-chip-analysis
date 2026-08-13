# 批 C 批内对抗审查（盲审）

- **审查对象**：`20ed20b`（基线 `2582c81`）——F-05 阵营 spec 四族共享校验（新库 `scripts/lib/camp_spec.py`）＋F-04 producer sidecar 链（新库 `scripts/lib/camp_series_provenance.py`）、CAMP_ORDER 拆段白名单、数值面/UTC 日期轴、末点对账、`--tol-pp` formal 钳制
- **审查方式**：只读仓库生产文件（本审查全程零改动）。所有变异实验在仓库副本 `/private/tmp/batchC_probe/repo/` 上做，逐条内存快照还原并逐字节核对（三轮全部 `还原 ✓`）。工作树接手时干净，`git rev-parse HEAD = 20ed20b`，无漂移
- **基线核对（独立复跑，不引用施工方自报）**：
  - `python3 scripts/tests/run_all.py` → **EXIT=0，"全部通过"**
  - `python3 scripts/tests/test_repair_batch_c.py` → **rc=0，69 checks**（计数机制真实：`check()` 内 `PASSED.append`，静态调用点 72 处、运行时命中 69）
  - `python3 scripts/tests/invariant_scan.py` → **rc=0**（producers=53／consumers=58／atomic=44）
  - 施工方自报的红绿状态**属实**
- **结论**：**6 条 finding，最高 P0**。数值面这一半是实打实的增量（无条件挂载、反例齐、误伤面小）；**来源绑定那一半整条挂在一个可选 CLI 参数上，不加参数即完全绕过，且落盘产物里没有任何下游闸认这条链**——F-04 原始 finding 写明的影响路径（伪造序列一路走到 A5）原样敞着

| 编号 | 严重度 | 一句话 |
|---|---|---|
| F-C1 | **P0** | `--series-source` 是可选参数，不加就没有任何来源绑定；`camp_series_sidecar` 全库只有写入处和自家测试，下游零校验——纯手编的"项目方 5%→88.8% 吸筹"序列 rc=0 直接进 analysis-state |
| F-C2 | P1 | 存量迁移未普查：13 个真实案的 analysis-state 有 **7 个**被新的无条件数值面闸拒（含 TAG/MOG/B2 三个近一周主力案），而 plan 与工单的"无追溯卡死"声明只覆盖 sidecar 链、没覆盖无条件数值面 |
| F-C3 | P1 | 登记面锚退化成自证：`supply_truth.json` 只验"文件在场＋含某个 sha 字符串"，schema/gate/target 一概不验——全套伪造数据链实测成本 **1663 字节、6 个小 JSON**，与工单声称的"把伪造成本推到伪造整案数据链"不是一个量级 |
| F-C4 | P2 | 双式闭合互救：净分母族少算 5pp 被 `burn_cum_pct=5` 蹭过 `s_all` 式；total 分母族总量 107% 被 `s_non` 式蹭过。sidecar 里已有 `denominator` 字段可做单式严判，未用 |
| F-C5 | P2 | `--tol-pp` 钳制与 F-02 **不等深**：`--exploration` 是零成本 flag，配 `--tol-pp 99` 让 45pp 的不同源实测 PASS，且 figures check **不产任何收据、零落盘留痕**，发布闸无从判别 |
| F-C6 | P3 | producer 侧静默降级＋原子写弱于仓内最强先例：`balances_final.json` 不在场时 sidecar 静默少绑 `final_balances`（producer 不报警，拖到编译期才炸）；`write_series_sidecar` 只有 `os.replace` 无 `fsync` |

---

## 施工方自报属实性核对（逐条）

| 自报项 | 核对结论 |
|---|---|
| `run_all.py` 全量绿 rc=0（52 项） | **属实**，独立复跑 EXIT=0 |
| `test_repair_batch_c.py` rc=0、69 checks | **属实**，计数非硬编码 |
| `invariant_scan.py` rc=0（53/58/44） | **属实** |
| 变异法 13/13"删掉即红" | **属实且偏保守**。我独立扩面到 **32 条**（覆盖新库两个文件的每条校验＋四族接线＋consumer 全链），**30 条成立**；2 条不成立但有正当理由（见下表），未发现"装了等于没装"的空闸 |
| 自查事故①：变异脚本误用 `git checkout` 致两处突变短暂残留，已手工还原＋grep 清零 | **独立确认零残留**。生产树 `grep "if False\|and False\|# neutralized"` 除 `scripts/robinhood/pull_lp_events.py:89` 一处既有占位（`git log -S` 定位到 `0fe2d60`，与批 C 无关）外无命中；自报还原的两处（`camp_spec.py:68` owner 查重、`camp_series_provenance.py:156` sha 三验）在场且原样 |
| 自查事故②：invariant_manifest 曾全文件 indent 误排后恢复重插（净 +17 行） | **独立确认结构完好**。`git diff --numstat` = `17 0`（纯增无重排），indent=2，顶层 8 段齐全；**双向一致性用破坏性反证坐实**：三条新登记（producers/consumers/atomic）逐条删掉 → `invariant_scan` 各自 `FAIL: 1 discrepancy` |
| 末点对账"不是单向下界，spec 桶双向精确" | **独立证实**。构造"同值换仓"（项目方↔大庄互换 20pp，Σspec／残差／闭合／burn 四项全不变）→ 基线逐桶比对抓获；中和该检查后 rc=0 PASS，说明这道闸有独立命中区间且确为双向 |
| 变异表第 10 条"上界独立命中区间只有 (100, 100+tol]" | **属实**（我用 100.03 复现） |
| 变异表第 11 条"关 sha 后末点对账仍拦，两道全关才放行" | **可更正为更强**：篡改若只改序列中间点（末点/桶名/闭合全不变），sha 闸**单独就能命中**（中和后 rc=0）。施工方原反例改动了桶结构才被二线抢先 |
| 工单末行"git commit：未做（工作树留给裁判验收）" | **与落盘不符**：`20ed20b` 已由施工方自行 commit（message 含批 C 全文）。不影响技术结论，记录以免后续引用工单文字时误判节拍 |

### 变异法独立重放明细（32 条，`/private/tmp/batchC_probe/mutate.py` + `mutate2.py`）

**成立（中和即转绿）30 条**：C1 EVM lower 规范化／C2 跨营查重／C3 同营查重／C4 JSON 重复键 hook／C5 值须列表／C6 阵营名非空／C7 地址非串空／C8 顶层须 dict；V1 桶名白名单／V2 有限数／V3 非负／V4 上界 100／V5 双式闭合／V6 日期轴严格递增／V7 长度对齐；P2 sidecar schema／P3 series_file 名绑定／P4 序列输出 sha／P5 输入 size 三验／P6 输入 sha 三验／P7 符号链接拒收／P8 supply_truth 在场／P9 replay_stats sha 命中／P10 spec 桶末点／P11 散户残差恒等式／P12 stray 桶拒收／P13 final_balances 必需／P14 camps_spec 必需／P16 双源分叉／P17 数值面挂载 compile_state。

**不成立但有正当理由 2 条**（如实记录，非缺陷）：

- **P1 sidecar 必需**：中和 `if not sc_path.is_file()` 后被 `FileNotFoundError` 天然兜底（main 的 `except OSError` → BLOCK exit 2）。显式分支的价值是错误信息，不是拦截力。
- **P15 sol-anchor-rows 拒入**：中和 `series_to_state_form` 的拒收后，被 `registry_anchor_check` 的"无登记面锚"二线拦下。**双防线，是好事**。

**方法学提醒（给后续维护）**：`if stray:` → `if False:` 这类**等长**替换会让文件 size 不变，若与上次写入落在同一秒，CPython 会复用 `__pycache__` 里的旧 pyc，变异法出**假阴性**（我第一轮 P12 就中招，清 `__pycache__` 后复验立即转绿）。做变异自检必须每次清 pycache 或改变文件长度。

---

## 视角① 字段来源

**被校验字段的生产者是谁、能否被同一伪造方顺手改掉？**

- **序列自身的 sha**：`load_series_with_sidecar` 现算实物 sha 与 sidecar 登记比对，有实物锚 ✓。
- **camps_spec / final_balances / inputs 三验**：`_resolve_ref` 只按 **basename** 在序列目录与案根两层内找，现算 size+sha，符号链接拒 ✓。**路径逃逸实测无效**：把 sidecar 的 `camps_spec.path` 改成 `../../../../etc/hosts`，报"在序列目录与案根两层内都找不到"（basename 化把逃逸面焊死了，这一设计成立）。
- **登记面锚（本视角的问题所在）**：`registry_anchor_check` 的 evm 分支只做两件事——案内有个叫 `supply_truth.json` 的文件，且 sidecar 登记的 replay_stats sha 出现在该文件**任意位置的 sha256 值集合**里。它不验 supply_truth 的 `schema`、不验 `gate` 判定、不验 `target` 三键、不验 producer。sol 分支同理，只读 `gate_pass` 这一个布尔。**这就是"自己报自己验"**：伪造方连造带签一条龙，见 **F-C3**。
- **末点对账的分母**：确实不信 sidecar 自报数字，一律从终态快照机械派生（`Σbalances − ZERO`／`Σeffective_balances` 并与 `reconcile_receipt.net_supply_raw` 交叉）✓。**但快照本身也归伪造方所有**，机械派生只保证"自洽"不保证"真实"——这一点工单说清楚了，本视角不重复记 finding。

## 视角② 失败分支

逐条实跑（EVM 全链 + Solana 全链两套夹具），**没有发现静默放过**：

| 破坏点 | 实测 |
|---|---|
| 删 sidecar | exit 2 |
| sidecar schema 改 `x/v9` | exit 2 |
| series_file 名对不上 | exit 2 |
| 序列改一字节（仅中间点） | exit 2 |
| camps_spec size / sha 篡改 | exit 2（两条各自独立命中） |
| camps.json 换成符号链接 | exit 2 |
| 删 supply_truth.json | exit 2 |
| replay_stats sha 不命中 | exit 2 |
| sol：`gate_pass=false` | exit 2 |
| sol：缺 reconcile 绑定 | exit 2 |
| sol：`net_supply_raw` 不符 | exit 2 |
| 末点被改（EVM/Solana 各一） | exit 2 |
| source 手填 series ≠ 转换结果（双喂） | exit 2 |
| sidecar format 冒充 `sol-anchor-rows` | exit 2（两道） |
| 数值面六项（白名单/有限数/负值/上界/闭合/日期轴） | 全 exit 2 |

**唯一的静默降级在 producer 侧**：`replay_duck.py:492` 与 `replay_pass2.py:133` 写 `final_balances_path=_fb if os.path.exists(_fb) else None`——快照文件不在场时 sidecar 静默少绑一项，producer 打印正常收工，要拖到 `compile_state` 才报"sidecar 未绑定 final_balances"。见 **F-C6**。

## 视角③ 存量迁移

**这是本轮误伤面最大的地方。** 我把两个案库（`~/Desktop/老公用/fable筹码分析`、`~/Documents/5.6筹码分析`）里所有含 `camp_share_series` 的 `analysis-state.json` 全量喂进新的 `validate_series_payload`：

```
存量案 13 个；数值面通过 6；被拒 7
  QUQ      ['狙击集团']
  ASTEROID ['狙击集团']
  APU      ['项目方(初始分发地址)','狙击集团','跨链桥','销毁(dEaD)']
  TAG      ['大庄Bitget','大庄Gate']
  MOG      ['W系做市体系','W系做市体系(扩展)','独立大户实体','池与设施','散户与未标注']
  KOGE     ['质押设施']
  B2       结构非 {dates, series}（形态整体不合）
```

白名单收紧本身有依据（legacy 名新报告禁用是既定政策，工单也点名了 TAG 的"大庄Gate"形态）。**问题在于施工方只从 TAG 一个案发现了这个形态，没做全库普查，也没把迁移影响写进任何文档**，而 plan.md:52 与工单反复写的"旧案无 sidecar → 不经 compile_state 的重绘路径不受影响，无追溯卡死"**只对 sidecar 链成立**——数值面是**无条件**挂在 `compile_state` 上的，任何存量案只要需要重编译 state（A5 终态重验、复核翻案后重出名册、freeze 重放、发布闸返工），当场被拒。MEMORY 里 TAG 案正卡在"HTML 卡 skill 算法升版重验兼容"、MOG 案记着"freeze 绑定环死结与全家桶复跑坑"、B2 案记着"发布闸连锁重封 6 次"——**这三个案都是高概率要重跑 compile_state 的**。见 **F-C2**。

## 视角④ 同族调用面（四族等深）

**结构层面等深成立**：四个入口各自只有一处读 camps，且都在装配 `addr2camp` 之前调共享实现，没有第二条旁路。

| 入口 | 接线点 | 实跑验证 |
|---|---|---|
| `evm/replay_pass2.py:34` | `validate_camp_spec(chain_family="evm")` | 跨营重复／同营重复／大小写变体 **三种全 rc=2** |
| `evm/replay_duck.py:377` | 同上（`:385` 用规范化后的键装配，旧"复刻 dict 语义"注释已删） | 共享实现同一份，`test_engine_equivalence` 全绿 |
| `solana/replay_edges.py:251` | `validate_camp_spec(chain_family="solana")`，前置缺文件硬拒 exit 2 | 缺 camps 硬拒在 `cmd_evolution` 首行（代码核）；坏 spec 走同一共享实现 |
| `solana/build_evolution.py:82` | `load_addr_camp_json` → `object_pairs_hook` → 反转过 `validate_camp_spec` | JSON 重复键实跑 **rc=2** |

`set()` 化确实在查重**之后**（`replay_pass2:36` 的 `set(v)` 吃的是已校验列表）✓；EVM lower 规范化在查重**之前** ✓；Solana base58 保持大小写敏感、大小写不同视为不同地址（绿例，不误杀）✓。

**两处等深上的小裂缝（不构成 finding，记录备查）**：

1. `load_addr_camp_json` 返回的是**未规范化的原始 obj**，`build_evolution` 后续用原始键匹配。Solana 原样保留所以无实害；将来若把 `chain_family` 改成 evm，"查重用小写、匹配用原样"会裂开。
2. EVM 规范化只做 `lower()`，不归一 `0x` 前缀：`"0xabc…"` 与 `"abc…"` 不判重。无实害（无 `0x` 的地址在余额表里根本匹配不到，夺不走归属）。

**consumer 侧的等深则是另一回事**：四族都写 sidecar，但只有 `evm-dict`/`sol-rows` 两族能进正式链，`sol-anchor-rows` 显式拒、`evm-entity-dict` 走不到转换器。这是有意设计，成立。

## 视角⑤ 双向一致性（文档宣称 vs 代码实际）

三处宣称与实际强度对不上，构成 F-C1／F-C3／F-C5 的定性依据：

| 出处 | 宣称 | 实际 |
|---|---|---|
| `report-template.md:201` | "正式编译 `--series-source` **必给**" | 纯文档约束，代码零强制、产物零标记、下游零校验（F-C1） |
| 工单①栏 | sidecar 把"伪造成本推到**伪造整案数据链**" | 实测 6 个小 JSON、1663 字节即可全链自洽（F-C3） |
| 工单①栏 | `--tol-pp` 钳制"与 supply_truth `--tolerance-bps` F-02 模式**同族同深**" | F-02 超容差要 waiver 收据（裁决人＋UTC＋sha 绑定）且 supply_truth 收据留痕、发布闸复验；这里 `--exploration` 是零成本 flag、零落盘、发布闸不可验（F-C5） |

`scan-schemas.md:529` 那句"数值面 compile_state 无条件校验，与 `--series-source` 无关"倒是**准确的**——它恰好也是 F-C1 的反证：文档自己承认了两道闸强度不同，只是没人把第二道焊成必经之路。`state_from_facts.py` 的 `--series-source` help 文本更是直白写着"不给时 series 只过数值面、无来源绑定"——代码自己承认了绕过路径。

## 视角⑥ 闸可绕性（站到施工方反例边界外一步）

施工方的反例边界是"**带** `--series-source` 时能不能骗过验证链"。往外走一步的三个攻击，两个得手：

1. **不带 `--series-source`**（F-C1，得手）：整条链不执行。
2. **带 `--series-source` 但全套自造**（F-C3，得手）：链执行且全过。
3. **带 `--series-source` 且只改一处**（未得手）：sha/size/末点/闭合/日期轴/白名单逐条拦，包括同值换仓——这部分做得扎实。

---

## F-C1 —— P0 —— 来源绑定整条链挂在可选参数上，下游没有任何闸认它

**要害**：`state_from_facts.py` 的 `--series-source` 是可选参数。不加，`bind_series_source` 整个函数不执行，`camp_share_series` 依旧是 source 里的自报字段，只多过一道数值面体检；产物 `provenance` 里也就没有 `camp_series_sidecar` 这个键——而**全库 grep 只有两处引用该键**：`state_from_facts.py:152`（写入）和 `test_repair_batch_c.py:230`（自家测试断言）。`a4_gate.py`／`build_html.py`／`facts_gate.py`／`entity_identity_gate.py`／`audit_release_gate.py`／`a5_report_seal.py` 没有一处检查它。

**实测复现**（`/private/tmp/batchC_probe/`，CLI 级）：

```python
source["camp_share_series"] = {"dates": ["2026-08-01","2026-08-02","2026-08-03"],
    "series": {"项目方":[5.0,40.0,88.8], "散户":[95.0,60.0,11.2]}}   # 纯手编，无 producer
# python3 state_from_facts.py --facts facts.json --source src.json --out analysis-state.json
```
→ `rc=0`，`PASS: compiled analysis-state.json`，伪造的"项目方 5%→88.8% 吸筹"原样进 state，`provenance` 无 sidecar 键。

**为什么是 P0**：F-04 原始 finding 的问题陈述是"camp_share_series 是调用者自报字段，伪造序列可以一路走到 A5 封章"。修完之后这条路径**原样存在**，代价只是把伪造数字凑成闭合形态（本 finding 的复现数据就是闭合的）。这与批 B 的 F-B1 同构：闸装了，但装在了非必经之路上。MEMORY 的 v6.11.0 教训（"B-03 揭 G8 所在 build_html 闸体系挂可选参数＝装了等于没装"）与元规则第八层（"闸须为必经之路，不可挂可选参数"）在本批被原样复发，且是本批**自己新引入**的结构。

**注意公允之处**：数值面这一半确实是无条件的、确实有效（`-899/999` 那类粗糙伪造在 `compile_state` 当场被拒，我独立复现过）。P0 针对的是来源绑定这一半。

## F-C2 —— P1 —— 存量迁移未普查，13 案拒 7，"无追溯卡死"声明不成立

**要害**：见视角③的全量扫描结果。核心不是"该不该收紧白名单"（该收），而是三点：

1. 施工方**没做存量普查**——工单只从 TAG 一个案发现了实体级自造桶名，把它当孤例写成"正当收紧"，实际是 7/13 的面。
2. plan.md 与工单反复出现的"旧案不受影响、无追溯卡死"**只覆盖 sidecar 链**（那半确实是可选路径所以确实不影响），但数值面是**无条件**的，覆盖不到。两句话被混在同一个"不受影响"的结论里。
3. **没有迁移指引**：被拒的 7 个案里，`狙击集团`(QUQ/ASTEROID/APU) 有 `CAMP_ORDER_LEGACY` 明确对应关系可以指路；`大庄Gate`/`W系做市体系`/`质押设施` 这类实体级自造桶名要归到哪个现代桶、归并后份额怎么重算，无人给过口径；B2 案则是整个 `camp_share_series` 结构就不是 `{dates, series}`（连数值面的第一道形态检查都过不去），属于另一类问题。

**复现**：`/private/tmp/batchC_probe/` 内一段十行扫描脚本（报告视角③已贴结果），只读用户案库，零写入。

## F-C3 —— P1 —— 登记面锚退化成自证，全链伪造实测 1663 字节

**要害**：`registry_anchor_check` 对 `supply_truth.json` 的全部要求是"文件在场"＋"sidecar 登记的 replay_stats sha 出现在该文件递归收集的 `sha256` 值集合里"（`_sha_values` 把任意深度的 `sha256` 键都收进来）。schema、gate 判定、target 三键、producer 全不验。sol 分支只读 `gate_pass` 一个布尔。

**实测复现**（`/private/tmp/batchC_probe/`）：造 6 个文件——`camps.json`、`data/balances_final.json`、`data/replay_stats.json`、`data/supply_truth.json`（**内容就是 `{"sha256": "<自造 replay_stats 的 sha>"}` 这一行**）、`data/camp_series.json`、sidecar（直接调公开函数 `write_series_sidecar` 生成）——总计 **1663 字节**，没有一个字节来自链上。跑 `--series-source` → **rc=0**，产出的 state 里 `provenance.camp_series_sidecar.producer` 写着 `scripts/evm/replay_pass2.py`。

**为什么算 finding 而不是"已接受边界"**：工单把这条定性为"与 F-12 已接受边界同款残余"，理由是"伪造成本被推到伪造整案数据链"。实测表明成本远低于该措辞暗示的量级——`supply_truth.json` 在案内本来是批 A 强验证链上的收据，这里却退化成一个"含某个字符串的任意 JSON"。**只要加验 schema／gate verdict／target 三键，成本就从"46 字节任意 JSON"提到"结构完整的伪造收据"，还能顺带挡住误用**（比如把无关 JSON 错当 supply_truth）。低成本、高收益、不改架构。

## F-C4 —— P2 —— 双式闭合让两族的正确式互相救活

**要害**：`validate_series_payload` 的闭合式是 `非burn桶Σ≈100 或 全桶Σ≈100`，二中其一即过。两个族各自只有一式是对的，双式等于每族都多了一条本不该适用的逃生通道。

**实测**：

| 构造 | 应判 | 实判 |
|---|---|---|
| 净分母族（`burn_cum_pct`），非 burn 桶只有 95、burn 恰为 5 | 拒（少算 5pp） | **ACCEPT**（`s_all=100` 蹭过） |
| total 分母族（`锁仓/销毁` 参与闭合），`s_non=100` 且 burn=7（总量 107%） | 拒 | **ACCEPT**（`s_non=100` 蹭过） |
| 对照：净分母族缺 5pp、burn=1（两式都不中） | 拒 | REJECT ✓ |

**可行收口**：sidecar 里已经有 `denominator` 字段（四取一），`bind_series_source` 路径上完全可以按它选**单式**严判；无 sidecar 的手填路径没有口径信息，保留双式。这样不牺牲 burn 案的合法通过，又把互救通道关掉。

**实害评估**：需要 burn 值恰好等于缺口，自然发生概率低；主要是故意伪造场景——而伪造场景下 F-C1 已经能整条绕过，所以定 P2 而非更高。

## F-C5 —— P2 —— `--tol-pp` 钳制与 F-02 不等深：exploration 零成本、零留痕

**要害**：钳制本身有效（实测 `--tol-pp 99` 不加 `--exploration` → exit 2 政策拒 ✓）。但 `--exploration` 是 `store_true`，任何调用方随手加，加上之后容差任意：

```
formal 默认              → rc=1  FAIL: 图 2 装配数据与 facts 终值 1 处不同源
formal 改 tol            → rc=2  FAIL: 正式模式 --tol-pp 写死 0.05pp
--tol-pp 99 --exploration → rc=0  [exploration] PASS: …（容差 99.0pp）   ← 真实差 45pp
exploration 运行产生的落盘文件：无（零留痕）
```

对照 F-02：`supply_truth_gate` 超容差必须给 `tolerance-waiver/v1` 收据（裁决主体＋`user_decided_at_utc`＋evidence sha/size 绑定），且 `supply_truth.json` 收据本身记录 mode 与容差、由 `shared_release_receipt` 独立复算复验。`figures_from_facts check` **不写任何产物**，`[exploration]` 前缀只落在 stdout，发布闸只看得到 rc=0。所以工单"同族同深"这个断言不成立，**差在留痕与可验证性上，不在钳制逻辑上**。

**可行收口（择一）**：①`check` 落一份小收据（含 mode／tol_pp／facts+series 的 sha），发布闸验 mode==formal；②`--exploration` 与 F-02 同样要收据；③最低限度：把该判定移出正式发布路径并在 R10 台账明账"不作为发布闸"。

## F-C6 —— P3 —— producer 侧静默降级 ＋ 原子写弱于仓内最强先例

两个小项，合并记录：

1. **静默降级**：`replay_pass2.py:133`／`replay_duck.py:492` 的 `final_balances_path=_fb if os.path.exists(_fb) else None`。`balances_final.json` 不在场时 sidecar 少绑一项，producer 正常收工无任何提示，要到 `compile_state` 才炸"sidecar 未绑定 final_balances"。fail-closed 最终成立（不会放行），但把问题从重放期推迟到编译期，与本批"缺 camps 文件当场硬拒 exit 2"的口径不一致（同一批里两处缺件、两种态度）。
2. **原子写**：`write_series_sidecar` 是 `tmp.write_text` + `os.replace`，无 `fsync`。仓内最强先例 `receipt_kernel.py:316` 是 `fsync` + `os.replace`。manifest 已按 `overwrite_single` 登记、`invariant_scan` 通过，所以不违规，只是"不是最强"——sidecar 是整条来源链的锚点件，值得对齐最强先例。

---

## 复现件清单

全部在 `/private/tmp/batchC_probe/`（仓库副本 + 脚本，零污染生产树）：

| 文件 | 用途 |
|---|---|
| `repo/` | `20ed20b` 的完整副本，变异实验专用；三轮实验后与 `git show 20ed20b` 逐字节相同 |
| `mutate.py` | 变异法驱动器（32 条中的 32 条定义 + EVM 全链绿例夹具工厂 `build_evm_case`）；内存快照备份制，末尾自动做还原核对 |
| `mutate2.py` | 第二轮精化（C5/C6/V3/P4 换独立命中区间的反例；P1/P10/P11/P12/P15 辨析二线） |
| 会话内一次性脚本 | F-C1 绕过复现、F-C3 全链伪造（1663B）、F-C2 存量 13 案扫描、F-C4 双式闭合构造、F-C5 exploration 逃逸、sol-rows 六场景、四入口实跑、manifest 三条破坏性反证——均为十余行、报告正文已贴关键输入与输出，可照抄重放 |

**未做的两项**（如实声明，供复审接手）：①`replay_edges evolution` 的坏 spec 未端到端实跑（需 soltx 缓存 meta，夹具成本高），该入口结论基于代码审查＋施工方真跑测试在 run_all 中全绿；②`replay_duck` 的坏 spec 未单独实跑，理由同为共享实现单点＋`test_engine_equivalence` 全绿。

---

## 收口建议

**必须修（P0/P1，建议进消化轮）**：

1. **F-C1**：把来源绑定焊成必经之路。最小改法——`compile_state` 在 formal 路径要求 `provenance.camp_series_sidecar` 在场，`--series-source` 缺席时要么 exit 2、要么必须显式 `--exploration`（与本批 `--tol-pp` 同一模式，本批内即可自洽）；并让至少一个下游闸（`a4_gate` 的 seal 面或 `audit_release_gate` 的 new-analysis profile）验该键在场且 `series_sha256` 与案内序列实物相符。**不做这一条，F-04 就等于没修。**
2. **F-C3**：`registry_anchor_check` 加验 `supply_truth.json` 的 `schema` 与 gate 判定（sol 侧同理加验 reconcile 收据的 schema/target），把"含某个 sha 字符串的任意 JSON"提到"结构完整的收据"。
3. **F-C2**：补一次全库存量普查（脚本十行，本报告已给结果），把 7 个被拒案的迁移口径写进 `scan-schemas.md` 或 CHANGELOG；把 plan/工单里"无追溯卡死"改口为"sidecar 链无追溯卡死，数值面白名单对存量案是硬迁移"。

**建议修（P2/P3）**：

4. **F-C4**：`bind_series_source` 路径按 sidecar 的 `denominator` 选单式闭合，手填路径保留双式。
5. **F-C5**：给 `figures_from_facts check` 落收据或明账降级，别再称"与 F-02 同族同深"。
6. **F-C6**：`final_balances` 缺席改为 producer 侧 fail-loud；`write_series_sidecar` 补 `fsync` 对齐 `receipt_kernel`。

**做得扎实、建议保留不动的部分**（防止消化轮误伤）：四族共享校验的收敛与规范化时序、`_resolve_ref` 的 basename 化＋符号链接拒收、末点对账的双向逐桶精确（同值换仓能抓）、日期轴 UTC 族（时区换算/naive-aware/闰日/重复全部咬得住）、sol-rows 的三条登记面校验、双源分叉消灭。

**原样收口的终判**：**不建议**。F-C1 一条就使本批 F-04 的核心不变量（"进入 analysis-state 的序列必然锚在 producer 链上"）在落盘产物上不成立，属于必须进消化轮的 P0；F-C2/F-C3 两条 P1 一个是存量面未评估、一个是强度宣称与实际不符，都可低成本收口。数值面与 F-05 那两半可以原样保留。

对抗审查完成

---

# 消化轮 1 复核

- **复核对象**：`eb6bee2`（基线 `20ed20b`）——批 C 消化轮 1，工单 `batchC_fixround1_workorder.md`，施工方声称 F-C1~F-C6 全关
- **复核方式**：只读＋副本变异，副本 `/private/tmp/batchC_probe/repo2/`（`eb6bee2` 钉死态）。生产树零改动
- **基线核对（独立复跑）**：`run_all.py` **EXIT=0**；`test_repair_batch_c.py` **rc=0，103 checks**（69→103 属实）；`invariant_scan.py` **rc=0**（producers=54／consumers=61／atomic=45，与工单自报一致）
- **结论**：**5 关 1 开**。F-C2/C3/C4/C5/C6 关闭；**F-C1 REOPEN（P0→P1）**——编译期必经化做得干净彻底，但轮 1 新写的下游发布闸 `check_series_binding` 是**自证式**的，"伪造序列进正式发布"这条路径换个操作方式仍然通畅。另有 **3 条新 finding（全 P2）**

| 编号 | 判定 | 一句话 |
|---|---|---|
| F-C1 | **REOPEN（P1）** | 编译期三道全关（原攻击 exit 2／exploration 如实标记／source 预置拒），但发布闸 `check_series_binding` 只验"state 自报的 sidecar 块与案内同名文件 sha 自洽"，**从不比对 state 里的 `camp_share_series` 与那个序列文件的内容**——手改两个字段即放行 |
| F-C2 | CLOSED | 34 state 扩面属实、A/B/C 分类框架站得住（A/B 类独立抽查全成立）；C 类两处数字失真另记 N-C2 |
| F-C3 | CLOSED | 三种粗糙伪造（46B 冒充／sha 塞顶层／verdict=FAIL）全部转拒 ✓；完整伪造收据仍过、成本仅 +129B，另记 N-C3 |
| F-C4 | CLOSED | 两个互救构造全部转拒（`closure_mode=net`／`total` 各自报错）；burn 两族合法绿例与 dual 宽式零误伤 |
| F-C5 | CLOSED | `--tol-pp 99 --exploration` 现在落收据（mode=exploration）且被发布闸拦下——原诉求"零留痕、发布闸不可验"已消除；收据本身可手写另记 N-C1 |
| F-C6 | CLOSED | `replay_pass2` 缺 `balances_final.json` → **rc=2 硬拒**（实跑）；有则正常绑定；`write_series_sidecar` 已 flush+fsync+replace |

| 新编号 | 严重度 | 轮 1 新引入？ | 一句话 |
|---|---|---|---|
| N-C1 | P2 | **是** | `figure2_check_receipt.json` 可纯手写伪造：series sha 验证是**条件式**（收据里的 path 不在案根就整段跳过）、facts sha **完全不验**——不跑 check 直接手写一份 formal/PASS 收据即过发布闸 |
| N-C2 | P2 | **是** | F-C2 上报裁判的 MOG 闭合偏差取的**不是最差点**：工单写"第 93 点 99.9440，差 0.056pp 超容差一线"，实测最差在 idx 177 = **99.7433（偏离 0.2567pp）**，低估 4.6 倍；KOGE 日期轴重复实为 **2 处**（idx 8、idx 12），工单只报 1 处 |
| N-C3 | P2 | 否（盲审建议未完全落实） | 登记面三验加了 schema/verdict/exit_code＋位绑定，**但没加 target 三键**（真实收据带 `chain/token/as_of_block`）——完整伪造链实测从 1663B 涨到 **1792B**，成本几乎未变，登记面仍无案身份锚 |

---

## 1. F-C1~F-C6 逐条重放

### F-C1 —— REOPEN（P0→P1）

**已关的部分（编译期，做得干净）**——三条实测全部转拒：

```
手编序列直通（无 --series-source）  rc=2  BLOCK: formal 编译必须 --series-source（闸不挂可选参数）
加 --exploration 豁免              rc=0  产物 provenance.series_binding = "exploration-unbound"   ← 标记如实
source 预置 producer-sidecar 标记   rc=2  BLOCK: source.provenance 不得预置 series_binding/camp_series_sidecar
```

**未关的部分（下游发布闸自证）**——`check_series_binding` 只做三件事：读 state 自报的 `series_binding`、按 `camp_series_sidecar.series_file` 的 basename 在案根/`data/` 找实物、比对该实物 sha 与 state 自报的 `series_sha256`。**三样东西全部由 state 自己携带，序列文件的内容与 state 里的 `camp_share_series` 之间没有任何一行代码建立联系。**

单元级实测（`check_series_binding(case_dir, state, errors)` 直调）：

| 场景 | 结果 |
|---|---|
| **A) exploration 产物手改标记**：伪造 `camp_share_series`＋手写 `series_binding="producer-sidecar"`＋自补 sidecar 块指向案内一份内容任意的 `data/camp_series.json`（sha 自己算） | **★ 放行（零 error）** |
| **B) formal 合法产物编译后篡改 `camp_share_series`**（provenance 原样不动） | **★ 放行（零 error）** |
| A0) 诚实的 `exploration-unbound` 产物 | 拦下 ✓ |
| C) 序列实物被改（sha 与登记不符） | 拦下 ✓ |
| D) 序列实物不在案根/`data/` 两层 | 拦下 ✓ |

攻击 A 的完整成本：手写两个 JSON（改后的 state ＋ 一份随便什么内容的 `camp_series.json`），**不需要跑任何 producer、不需要任何真实数据**。

**兜底面已查，无有效兜底**：`entity_identity_gate.py:187` 与 `a5_report_seal.py` 确实绑 analysis-state 的 sha256，但它们封的是"当前磁盘状态"——攻击者手改 state 之后再跑这两步，封的就是改后的 state。它们防的是"封章后被改"，不防"封章前被改"。

**归属说明（对我自己轮 0 建议的更正）**：我轮 0 的收口建议原文是"让至少一个下游闸验该键在场且 `series_sha256` 与案内序列实物相符"——施工方**逐字照做了**。是我的建议本身不完备：验 sha 相符只证明"序列文件没被改"，不证明"state 里的序列是这个文件转换来的"。**正确的闸条件是：发布闸自己用 `series_to_state_form` 把案内序列文件重新转换一遍，与 state 里的 `camp_share_series` 逐点比对**（转换器是纯函数、无外部依赖，发布闸可直接 import；这样 A 和 B 两个攻击同时死）。

### F-C2 —— CLOSED（分类站得住，数字失真另记 N-C2）

**A 类（仅白名单拒）独立抽查 2 案**——把白名单这一道临时豁免、其余数值面全跑：

| 案 | 点数 | 日期轴重复 | 最差闭合偏离 | 负值 | 超 100 | 豁免白名单后 |
|---|---|---|---|---|---|---|
| QUQ | 489 | 0 | 0.0002pp | 无 | 无 | **PASS ✓** |
| TAG | 500 | 0 | 0.0002pp | 无 | 无 | **PASS ✓** |

A 类定义（"数值面全过、仅桶名不合"）**成立**。

**B 类（非本批引入）定性抽查 2 案**——用旧编译器（`2582c81` 版 `state_from_facts.py`，无 `validate_series_payload`）跑：

```
B2    camp_share_series 键 = [schema, denominator, camps, series, final_pct]
      旧编译器 REJECT: source.camp_share_series 结构非法   ← 非本批引入 ✓
TROLL camp_share_series 键 = [dates, camps]
      旧编译器 REJECT: source.camp_share_series 结构非法   ← 非本批引入 ✓
```

B 类定性**成立**，"本批新增拒绝面实为 A 类 4 案＋C 类 2 案"这一修正对我轮 0 报告的细化**属实**（我轮 0 把 B2 列进"7 拒"里确实是口径问题）。

**C 类抽查**：分类归属成立（两案确实是白名单＋数值面双拒），但两处数字失真，见 N-C2。

### F-C3 —— CLOSED（原诉求已关，成本几乎未变另记 N-C3）

四个梯度实测：

```
原 1663B {"sha256": "..."} 冒充        rc=2  不是合法供给真值收据（schema 必须是 supply-truth-receipt/v3）
真 schema 但 sha 塞顶层任意位置          rc=2  缺 inputs.replay_stats.sha256 绑定
真 schema + 位对但 verdict=FAIL        rc=2  非 PASS/exit 0
真 schema + PASS + exit_code=0 + 位对   rc=0  ★ 仍过（完整伪造链 1792 字节）
```

schema 名矫正独立核实**属实**：TAG 案实物 `supply_truth.json` 的 `schema` 确为 `supply-truth-receipt/v3`、`verdict=PASS`、`exit_code=0`、`inputs.replay_stats.sha256` 在场——修主批时夹具用的 `supply-truth/v1` 确是影子形态，本轮矫正方向正确。

原 finding 的论点①（"schema/gate/target 一概不验"）已关；论点②（"成本 1663 字节，与'伪造整案数据链'不是一个量级"）**未关**，见 N-C3。判 CLOSED 是因为①是要害、②本就是程度问题且工单未再声称已解决。

### F-C4 —— CLOSED，零误伤

```
净族 非burn=95 + burn_cum_pct=5 蹭 s_all   rc=2  不闭合（closure_mode=net）：非burn桶Σ=95.0000
total族 s_non=100 + 锁仓/销毁=7（总量107）  rc=2  不闭合（closure_mode=total）：全桶Σ=107.0000
```

**防误伤抽查（裁判要求 4）全过**：净族 EVM（非 burn=100、`burn_cum_pct`=5.2632）PASS ✓；净族 sol-rows（非 burn=100、`锁仓/销毁`=11.11）PASS ✓；total 族（全桶含 `锁仓/销毁`=100）PASS ✓；手填路径 `dual` 宽式保留 ✓。`closure_mode_for` 四口径映射正确（`current_net_supply`/`net_supply`→net，`mint_total_legacy`/`config_total_supply`→total），未知口径拒 ✓。

TROLL/TAG 的末点对账实测不受本轮影响：`endpoint_reconcile` 本轮零改动，且这两案的序列桶名本就不在 MODERN 白名单（轮 0 报告已指出那两次"实测"是在 `endpoint_reconcile` 层单跑的，不是全链）。

### F-C5 —— CLOSED（原诉求已关，收据可手写另记 N-C1）

```
--tol-pp 99 --exploration   rc=0，收据在场，mode=exploration / tol_pp=99.0 / verdict=PASS
发布闸 check_figure2_receipt → 拦下："mode='exploration'——exploration 运行的产物不得进正式发布"
```

轮 0 的原诉求是"exploration 放宽零成本、零留痕、发布闸不可验"——**三点全部消除**：现在有收据、mode 如实、发布闸复验。判 CLOSED。

### F-C6 —— CLOSED

```
replay_pass2 缺 data/balances_final.json  rc=2  [camp-series] 缺 …/balances_final.json
replay_pass2 有 balances_final            rc=0  sidecar final_balances 绑定 = balances_final.json
```

`write_series_sidecar` 已改为 `open→write→flush→os.fsync→os.replace`，与 `receipt_kernel` 先例对齐 ✓。

---

## 2. 轮 1 新代码检查（固定动作）

### 2a. formal 必经化后，exploration 产物能不能伪装 formal

**编译期不能**（`source.provenance` 预置标记直接拒，实测 exit 2）；**产物落盘后能**——把 `analysis-state.json` 里的 `series_binding` 手改成 `producer-sidecar` 并补一个 sidecar 块，发布闸放行（见 F-C1 攻击 A）。标记的防伪只做到了"编译器不接受外部预置"，没做到"发布闸能识别标记是不是这次编译真产的"。**结论：伪装 formal 的 exploration 产物能混过发布闸。**

### 2b. `audit_release_gate.py` 改动是否"仅新增独立函数与 REQUIRED 项，批 B 第二层 hunk 零触碰"

**核对属实**。三个 hunk 分别是 `NEW_ANALYSIS_REQUIRED` 加一项、在 `check_distribution_snapshot_binding` **之后**纯插入 74 行新函数（删除 0 行）、`run()` 里加 7 行 new-analysis 分支。逐字节验证：`20ed20b` 版 `check_distribution_snapshot_binding` 函数体（3149 字符）**原样出现在 `eb6bee2` 中**。批 A/B 其余已收口实现（`holder_distribution_scan.py`／`supply_truth_gate.py`／`accounting_gate.py`／`shared_release_receipt.py`）`git diff --numstat` 全部**零改动**。

（方法学提醒：`git diff` 的 `@@ … @@ def check_distribution_snapshot_binding` 里那个函数名只是 hunk 所在位置的最近函数标记，**不代表该函数被改**；按"下一个顶层 def"截取函数体做比对也会因新函数插入而假阳性——必须用"旧函数体文本是否原样出现在新文件中"来判。）

### 2c. `closure_mode_for` / `supply_truth` 三验 / `check_figure2_receipt` 自身有没有绕路

- `closure_mode_for`：四口径全覆盖、未知即拒、`validate_series_payload` 三态校验（`dual/net/total` 之外拒）——**无绕路**。
- `supply_truth` 三验：schema/verdict/exit_code 三道 ＋ 位绑定（`inputs.replay_stats.sha256`），`_sha_values` 递归收集式已整段删除（无死代码）——**无绕路**，但无案身份锚（N-C3）。
- `check_figure2_receipt`：mode/tol_pp/verdict 三验硬命中；**series sha 是条件式**（`if cand.is_file()`，收据里 path 的 basename 在案根找不到就整段跳过），**facts sha 完全不验**——见 N-C1。

---

## 3. 新 finding 详表

### N-C1 —— P2（轮 1 新引入）—— figure2 收据可纯手写伪造

`check_figure2_receipt` 的四道校验里，三道读的是收据自报字段（mode/tol_pp/verdict），第四道（series sha）是条件式。实测：

| 攻击 | 结果 |
|---|---|
| a) 手写 formal 收据、series 在案根但 sha 填假 | 拦下 ✓ |
| **b) 手写 formal 收据、`series.path` 写成 `charts/other_series.json`**（案根无同名文件→sha 整段跳过） | **★ 放行** |
| **c) 手写 formal 收据、series sha 填真值、facts sha 乱填** | **★ 放行** |

也就是说：根本不跑 `figures_from_facts check`，直接手写一份 JSON 就能满足发布闸的"图 2 已对账"这项必经资产。攻击 c 的成本 = 一个 JSON ＋ 对案内序列文件算一次 sha。

**收口建议**：①series 找不到实物时**报错而不是跳过**（收据宣称对账过就必须能验）；②facts sha 同样加验（案根 `facts.json` 是必经资产，一定在场）；③进一步可要求收据的 facts/series sha 与 `analysis-state`／案内实物三方一致。

### N-C2 —— P2（轮 1 新引入）—— 上报裁判的 C 类数字失真

工单 F-C2 上报段第 3 条写 MOG"第 93 点闭合差 **0.0560pp** 超容差 0.05 **一线**（数据微洞或舍入累积）——是'修数据'还是'容差边界裁决'归裁判定"。

独立核数（MOG 案 5 份 state 全部同值）：

- 第 93 点 `s_non=99.9440` — **数字本身属实**
- **但最差点是 idx 177：`s_non=s_all=99.7433`，偏离 0.2567pp** — 是上报值的 **4.6 倍**

这个差别直接影响裁决：按"差 0.056pp 一线"，裁判可能倾向"容差边界裁决"（放宽到 0.06 即可）；按实际 0.2567pp，要放宽到 5 倍现容差才盖得住，"舍入累积"的解释也站不住（0.26pp 不是 `round(4)` 能攒出来的），只能是数据问题。**上报材料必须取最差点，不能取任意一点。**

同段 KOGE 只报了 `dates[8]='2025-06-15'` 一处日期轴重复，实测有 **2 处**（idx 8 与 idx 12='2025-07-18'）。

### N-C3 —— P2（非轮 1 新引入；盲审收口建议未完全落实）—— 登记面仍无案身份锚

我轮 0 的收口建议 2 原文是"加验 `schema` 与 gate 判定（sol 侧同理加验 reconcile 收据的 schema/target）"。落实了 schema／verdict／exit_code／位绑定，**没落实 target**。真实 `supply_truth.json` 带 `target = {chain, token, as_of_block}`（TAG 案实物核对），这是唯一能把收据钉到"哪个案、哪个币、哪个块"的字段——不验它，一份从别的案复制来的合法收据、或凭空造的收据都能用。

实测量化：完整伪造链从轮 0 的 **1663 字节**变成轮 1 的 **1792 字节**（+129B，多写 4 个字段）。工单写"登记面命中结构化"给人的印象是伪造门槛显著提高，实测**几乎没变**。

**收口建议**：加验 `truth["target"]` 的 chain/token 与案内身份件（`identity_gate.json`／`facts.token`）一致；sol 侧同理。这一项能真正把成本推到"整案身份自洽"。

---

## 4. 复现件清单（轮 1 新增）

全部在 `/private/tmp/batchC_probe/`：

| 件 | 用途 |
|---|---|
| `repo2/` | `eb6bee2` 完整副本（复核期间零改动，无需还原） |
| 会话内一次性脚本 | `check_series_binding` 五场景单元攻击（A/A0/B/C/D）；F-C1 编译期三攻击；F-C3 四梯度伪造；F-C4 两互救＋四绿例；F-C5 exploration 逃逸＋三手写收据攻击；F-C6 producer 两态；F-C2 的 A/B/C 三类抽查（含旧编译器 `2582c81` 动态加载对照）；`audit_release_gate` 批 B 函数体逐字节比对 |

轮 0 的 `mutate.py`／`mutate2.py` 本轮未重跑（轮 1 未触碰 `camp_spec.py`，`camp_series_provenance.py` 的改动已被本节针对性重放覆盖）。

---

## 5. 终判

**需消化轮 2。** 单一原因：**F-C1 未闭合**——批 C 的核心不变量"进入正式发布的 analysis-state，其 `camp_share_series` 必然是 producer 链产出的"在落盘产物上**仍然不成立**，只是操作成本从"少给一个 CLI 参数"变成"手改 state 里两个字段"，威胁模型上是同一档（都不需要任何真实数据）。修法明确且工作量小：发布闸用 `series_to_state_form` 重新转换案内序列文件，与 state 的 `camp_share_series` 逐点比对（一次同时关掉 F-C1 的 A、B 两个攻击）。

其余五条实质关闭，轮 1 的工程质量总体高于主施工轮（编译期必经化、closure_mode 分派、fsync、producer fail-loud 都是干净的单点修复，零误伤，103 checks 与 invariant 登记同步到位）。三条新 finding 均为 P2，其中 N-C1 与 F-C1 同族（两个新发布闸函数都是"验产物自洽"而非"验产物来自真实运行"），**建议与 F-C1 同批修**；N-C2 是上报材料的数字问题，需要在裁判裁决 MOG 之前更正。

消化轮 1 复核完成

---

# 消化轮 2 复核（收口判定轮）

- **复核对象**：`70096b4`（基线 `e26dac6`）——F-C1 终关＋N-C1/N-C2/N-C3，工单 `batchC_fixround2_workorder.md`
- **复核方式**：只读＋副本变异，副本 `/private/tmp/batchC_probe/repo3/`（`70096b4` 钉死态）。生产树零改动
- **基线核对（独立复跑）**：`run_all.py` **EXIT=0**；`test_repair_batch_c.py` **rc=0，112 checks**（103→112 属实）；`invariant_scan.py` **rc=0**（54/61/45，本轮零新 schema 字面量与工单说法一致）
- **结论**：**4 条全部 CLOSED，零误伤**。轮 2 是三轮里质量最高的一轮——修法逐字落在盲审给的位置上，且每处都没留条件式跳过。**但站到边界外一步仍抓到 2 条新 finding（P2/P3，均非轮 2 新引入，是同根因的更深一层）**：发布闸把"验 state 自洽"扩大成了"验 state 与案内序列文件互洽"，仍然不是"验产物来自真实 producer 运行"

| 编号 | 判定 | 一句话 |
|---|---|---|
| F-C1 | **CLOSED** | 轮 1 点名的两攻击（A 手改标记＋自补块指真文件／B 编译后篡改 series）双双转拒，重转换逐点比对生效；format 异族值、缺 format、exploration 标记全拒；formal 绿例与旧简报型 state 零误伤 |
| N-C1 | **CLOSED** | 三攻击（series.path 写不存在名字／facts sha 乱填／缺 facts 段）全转拒，条件式跳过整段消除，绿例放行 |
| N-C2 | **CLOSED** | 数字已更正入台账 `e26dac6`；A 类 5 文件独立核数与自报**逐案一致**（最差闭合全 0.0002pp、日期重复 0、负值 0、超 100 零、非有限 0），分类零翻案；失真归因（fail-fast 取首个违例当最差点）成立 |
| N-C3 | **CLOSED** | target 三键结构验＋chain 两处同源＋token 对案内 `channels_preflight.json` 锚，四个反例全转拒；全库 18 份 preflight **全部**含非空 token 键，零误伤 |

| 新编号 | 严重度 | 轮 2 新引入？ | 一句话 |
|---|---|---|---|
| N-C4 | P2 | 否（F-C1 同根因更深一层） | 发布闸从不要求 producer sidecar 实物在场、不复算 registry/末点链——**"同步一致造假"实测放行**：自造一份原生格式序列文件＋state 用它的转换结果＋绑定块自填，案内**不需要** `.provenance.json`、**不需要** `supply_truth.json` |
| N-C5 | P3 | 否 | 两处结构检查无真实对锚：①`target.as_of_block` 只验"正整数"，改成任意别的正整数照过（实测）；②sol 侧 `solana-reconcile/v2` 收据 schema 确无身份键（`replay_edges.py:166` 实物核实，施工方诚实边界**如实**），跨案复制收据可用 |

---

## 1. F-C1 终判：两攻击转拒 ＋ 边界外一步

**轮 1 两攻击已死**（单元级直调 `check_series_binding`）：

| 场景 | 轮 1 | 轮 2 |
|---|---|---|
| A) 伪 series＋手改标记＋绑定块指向案内真序列（sha/format 全真） | ★放行 | **拦下**："camp_share_series 与案内序列实物的重转换结果不一致" |
| B) formal 合法产物编译后篡改 `camp_share_series` 一个值 | ★放行 | **拦下**（同上） |
| 绿例：formal 正常产物 | 放行 | 放行 ✓ |
| 旧简报型 state（无 `camp_share_series`） | 不强加 | 不强加 ✓ |

**边界外一步的三题（裁判点题）逐条查证**：

1. **`series_format` 分派键喂异族值**——不可绕。喂 `sol-rows` 给 evm-dict 文件、喂 `sol-anchor-rows`，均在重转换处抛错被捕获成 exit 拒；缺 `series_format` 直接拒。分派键虽由 state 携带（攻击者可控），但两族形态互斥（dict 带 dates ↔ 非空行数组），换键必然转换失败或结果不等。
2. **重转换函数与编译器转换器漂移**——不存在。发布闸 `from camp_series_provenance import series_to_state_form` 与 `bind_series_source` 是**同一个纯函数**，无第二份实现。
3. **篡改序列文件与 state 同步一致造假**——**可绕，实测放行**。见 N-C4。

### N-C4 —— P2（非轮 2 新引入）—— "同步一致造假"仍通

发布闸 `check_series_binding` 读三样东西：state 自报的 `series_binding`、state 自报的 `camp_series_sidecar` 块（series_file／series_sha256／series_format）、案内同名序列文件。**磁盘上的 `<series>.provenance.json` sidecar 实物它从不读**，`registry_anchor_check`（supply_truth/target/preflight 锚）与 `endpoint_reconcile`（末点对账）也只在 `compile_state` 里跑过一次，发布期不复算——而发布闸无从确认这个 state 是不是 `compile_state` 产的。

实测（攻击 C'）：

```
案内写一份自造的 data/camp_series_v2.json（evm-dict 原生格式，内容=想要的伪造序列）
state.camp_share_series = series_to_state_form(该文件, "evm-dict")
state.provenance = {series_binding: "producer-sidecar",
                    camp_series_sidecar: {series_file: "camp_series_v2.json",
                                          series_sha256: <自己算>, series_format: "evm-dict"}}
→ check_series_binding: ★ 放行（零 error）
   案内是否需要 .provenance.json sidecar 实物: False
   案内是否需要 supply_truth.json:            False
```

**成本评估（关键）**：攻击者不必手写整个 state——拿一份**真实的 formal 编译产物**（whale_groups／token／address_balances 全真，过 G1 成员对账与其余所有闸），只改 `camp_share_series` ＋ 三个 provenance 字段 ＋ 案内加一个原生格式 JSON 即可。而 evm-dict 原生格式（`{dates: [...], 桶名: [...]}`）与 state 形态只差一层嵌套，把伪造序列写成原生格式**近乎零额外成本**。**边际成本与轮 1 攻击 A 基本相同。**

**轮 2 确实提高了什么**：关掉了"改 state 不改文件"和"改文件不改 state"两类**不一致**篡改。这是实质进步，但对"双向一致地造假"无效。

**修法（明确、量小、有终点）**：发布闸在重转换比对之外，再复用现成的三件套——`load_series_with_sidecar(案内序列文件)`（强制 `.provenance.json` 实物在场＋输出 sha＋输入三验）→ `registry_anchor_check`（supply_truth/target/preflight 锚）→ `endpoint_reconcile`（camps spec＋终态快照末点对账）。约 15 行，全部是已有纯函数。修完之后，剩余残余就落到"伪造整案原始数据后真跑一遍 producer"——那是仓内已接受的 F-12 同族边界（一致性校验器不能证伪自洽的伪造输入）。**也就是说 N-C4 是这条链上最后一层可机器闭合的边界，值得关掉；关掉之后不会再有第四层。**

## 2. N-C1 / N-C2 / N-C3 逐条

### N-C1 —— CLOSED

```
绿例（两输入 sha 全真）                  放行 ✓
攻击 b) series.path 写案根不存在的名字     拦下："不在案根——收据宣称对账过的输入必须随案可验"
攻击 c) series sha 真 + facts sha 乱填   拦下："facts sha256 与案内实物不一致"
攻击 d) 收据缺 facts 绑定段              拦下："缺 facts 绑定（path/sha256）"
对照）series sha 假                    拦下 ✓
```

轮 1 的两个穿透点（series 条件式 `if cand.is_file()`、facts 完全不验）**整段消除**，`_figure2_input_check` 对两个输入做同一套无条件三段验（找不到＝拒／符号链接＝拒／sha 不符＝拒）。

### N-C2 —— CLOSED

台账 `e26dac6` 已按我轮 1 的核数更正（MOG 最差 idx 177 = 99.7433／偏离 0.2567pp，裁决不变、不放宽容差）。

**裁判要求的 A 类独立复核（抽全 5 文件）**：

| 文件 | 最差闭合偏离 | 日期重复 | 负值 | 超 100 | 非有限 |
|---|---|---|---|---|---|
| APU分析/analysis-state.json | 0.0002pp (idx 473) | 0 | 0 | 0 | 0 |
| QUQ分析/analysis-state.json | 0.0002pp (idx 34) | 0 | 0 | 0 | 0 |
| ASTEROID分析/analysis-state.json | 0.0002pp (idx 248) | 0 | 0 | 0 | 0 |
| TAG分析/analysis-state.json | 0.0002pp (idx 479) | 0 | 0 | 0 | 0 |
| TAG replay/analysis-state.json | 0.0002pp (idx 479) | 0 | 0 | 0 | 0 |

与工单自报**逐案一致**，A 类定义（数值面全过、仅桶名不合）成立，分类零翻案。失真归因（诊断脚本复用 fail-fast 的 `validate_series_payload`，抛首个违例即停，把首违例点当最差点抄进上报表）**成立**——分类判据是二值"过/不过"，与取哪个违例点无关，所以只影响上报数字不影响分类。归因诚实。

### N-C3 —— CLOSED

```
无 target（盲审 1792B 伪造链）              rc=2  缺合法 target 三键
target.chain 与顶层撕裂                     rc=2  两处同源，撕裂即伪造/拼接
target.token 不对案内 preflight             rc=2  收据不是本案的
案内缺 channels_preflight.json             rc=2  采集链身份件缺席（无条件式跳过 ✓）
as_of_block=0 / bool                      rc=2  结构检查命中
绿例：target 三键全对＋token 命中 preflight     rc=0  ✓
```

**误伤面已查**：TAG 案实物 `channels_preflight.json` 有 `token` 键且与 `supply_truth.target.token` 一致；全库 **18 份 preflight 全部含非空 token**，键名对得上，无误伤。

**诚实评估（记入 N-C4 的语境）**：target.token 锚提高的是"跨案复制收据"和"凭空造收据"的门槛。对**本案内伪造序列**这个最现实的威胁（分析师想让自己报告好看）它**不起作用**——本案内 preflight/token/chain 全是真的。伪造链成本 1792B → **2010B**。

## 3. 轮 2 新代码固定检查

- **内容重转换逐点比对的误伤面**：formal 正常产物放行 ✓（编译器注入的 series 本就是同一转换器输出，逐点必等）；旧简报型 state 不强加 ✓；`sol-rows` 族的转换含 `round(acc, 4)` 与并桶，发布闸与编译器走同一函数故必等 ✓。
- **无条件三段验的误伤面**：`facts.json` 与 `whale_series.json` 都是 new-analysis 的必经资产、恒在案根，无条件验不会误杀；p105／a4_gate 两处夹具已改为真跑 `check` 产收据（run_all 全绿佐证）。
- **burn 两族＋dual 绿例复查**（轮 1 已关项防误伤）：净族 EVM（`burn_cum_pct`=5.2632）PASS ✓／净族 sol（`锁仓/销毁`=11.11）PASS ✓／total 族（全桶=100）PASS ✓／`dual` 手填宽式 PASS ✓——F-C4 实现零触碰、零回归。
- **sol 侧诚实边界核实**：`replay_edges.py:166` 的收据实物形态 = `{schema: "solana-reconcile/v2", edge_count, net_supply_raw, snapshot_mismatch_count, gate_pass, …}`，**确无 mint/token/chain 任一身份键**——施工方"target 锚加不上去、属 producer schema 扩面、留 R10"的说法**如实**。
  **当前可利用性评级：P3。** 缺身份锚使一份来自别的 Solana 案的 reconcile 收据可直接复用（`net_supply_raw` 与终态快照合计的交叉等式由攻击者控制的快照凑得上）。但在 N-C4 未关的前提下，sol 侧这个缺口**不是边际决定项**（发布期整条链本就不复算）；若将来按 N-C4 修法复算发布期链条，则此项升为边际项，需同批补 producer 侧身份键。

## 4. 复现件清单（轮 2 新增）

`/private/tmp/batchC_probe/repo3/`（`70096b4` 完整副本，复核期零改动）＋会话内一次性脚本：`check_series_binding` 九场景（轮 1 攻击 A/B、绿例、★攻击 C'、format 异族两种、缺 format、exploration 标记、旧简报型）；`check_figure2_receipt` 五场景；`registry_anchor_check` 八梯度（含 as_of_block 三变体）；burn 两族＋dual 绿例；A 类 5 文件独立核数；preflight 全库 18 份键在场率扫描。

## 5. 终判

**技术判定：批 C 的四条待关项全部 CLOSED，轮 2 零误伤、零回归、测试与登记同步到位。** 但**核心不变量在发布期仍未闭合**——N-C4 实测证明"同步一致造假"以与轮 1 攻击 A 相当的边际成本仍可进正式发布。

**给裁判的两个选项（我不替裁判拍板，但给出倾向）**：

- **选项 1（倾向）：开消化轮 3，只修 N-C4 一条。** 修法明确、量小（约 15 行，复用 `load_series_with_sidecar`＋`registry_anchor_check`＋`endpoint_reconcile` 三个现成纯函数），且**这是这条链上最后一层可机器闭合的边界**——关掉之后剩余残余落到仓内已接受的 F-12 同族边界，不会再有第四层。第 3 轮触线需上报用户裁决，但代价是一次小改而不是一轮拉锯。N-C5 两项随轮入 R10 台账。
- **选项 2：本批就此收口。** 则 N-C4／N-C5 必须入 R10 台账，且 CHANGELOG 与 `scan-schemas.md` §13 要**明账**："批 C 的序列来源绑定在**编译期**闭合，**发布期**只做 state↔序列文件一致性复验、不复算 producer 链——控制案目录的伪造方仍可让伪造序列进正式发布。" 不能让"F-C1 全关"这个说法留在文档里被将来引用成"发布期已闭合"。

**明确反对的第三种处理**：把 N-C4 记成"已接受边界"而不修也不明账。它与 F-12 有本质区别——F-12 的残余是"伪造原始数据后真跑一遍"（无法用一致性校验器证伪），N-C4 的残余是"根本不跑 producer"（现成函数就能证伪）。两者不是一回事，不能借 F-12 的口径豁免。

消化轮 2 复核完成
