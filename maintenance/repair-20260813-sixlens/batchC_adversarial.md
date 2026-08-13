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
