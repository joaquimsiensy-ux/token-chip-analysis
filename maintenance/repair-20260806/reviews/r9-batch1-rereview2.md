# R9 批一 · 二次消化增量重审报告（B1R-01 语义重放终局核验）

- **审查对象**：`/Users/uravvv/Documents/5.6筹码分析/r9-closure-worktree`，分支 `fix/r9-closure-20260807`，HEAD `120c9ef`
- **增量审查区间**：`0bb94ba..120c9ef`（3 commit：`1a7e685` 终修主体 / `658f78e` 台账 / `120c9ef` SHA 回填）；11 文件、56 hunk
- **审查角色**：批一二次消化增量重审员，只读沙箱，与前两轮审查者无关。全程未对 worktree 做任何 git 写操作或文件增删改（`git status --short` 空、HEAD 未动、仅读+跑测试；临时产物一律落 `/private/tmp/r9b1r3/`）
- **审查模型身份（如实登记）**：**Claude Opus 4.8**（模型 ID `claude-opus-4-8`），以 Claude Code / Claude Agent SDK 子代理身份运行。PLAN-R9 第二节角色表规定批内对抗审查由「Opus 4.8 子代理」执行；本轮实际调度即 Opus 4.8，与角色表相符，无静默替代问题。
- **审查日期**：2026-08-08
- **前序报告**：`report.md`（BLOCK，B1R-01 P1 首次成立）；`report-recheck.md`（BLOCK，B1R-01 第二次 REOPEN + 新增 B1R2-01/B1R2-02 两 P3）

---

## 1. 裁决

### **ALL-CLEAR**

一句话理由：**B1R-01 第三轮语义重放方案是结构性修复而非又一层声明式补丁——真正闭合了**。前两轮之所以被穿，是因为闸校验的是「一个可照抄的声明」（producer 字段自洽 / producer 路径+公开 sha）；本轮 consumer 不再读任何声明，而是用 plan 携带的全部生成参数、对 `--input` 绑定的真实数据、经 producer/consumer **共用**的 `anchor_selection.py` **重算**整套选点与分格统计，再逐字段/多重集合比对。我用适配新接口（真传 `--input`）的攻击直击 `validate_semantic_replay`：手写任意锚点、篡改任一字段（余额/删点/seed/cell_population/threshold/min_pct/date_range/time_cuts/额外 boundary 共 9 类）、多重集去重、类型混淆、输入/plan 错配——**全部被拒且非零**。要造出能通过的 plan，手写方只能真跑确定性核心，伪造已失去意义。两项 P3（B1R2-01 末尾空行、B1R2-02 EXPECTED_PLAN_PRODUCER 单源）均已 CLOSED。本轮 56 hunk 全部有主、未映射=0、无夹带式削弱。

**上轮 3 项结论**：CLOSED × 3（B1R-01 终修、B1R2-01、B1R2-02）。
**新 finding 计数**：1 项 P3 —— `B1R3-01`（覆盖面下限缝：consumer 接受退化参数的**真实** producer plan，把抽查缩到 2 个强制点；**历史漏检**，非 B1R-01 未闭合）。另有 1 条观察（输入替换＝上游职责的 scope 边界，非缺陷）。
**严格三分类**：老问题修复不全 0；修复中新引入 0；历史漏检 1（B1R3-01）。
**零新 ≥P2。** 故满足 ALL-CLEAR 三条件（B1R-01 CLOSED 且两 P3 CLOSED 且零新 ≥P2）。

> 关于 B1R3-01 为何不推翻 ALL-CLEAR：它是 P3 历史漏检，方法论 §7.1「历史 P2/P3 记账后做限定复核，不无限重置整轮」；且它**不满足** BLOCK 触发条件（无 REOPEN、无半修残留、无本轮新引入）。它是给下一轮的一条可选加固线索，不是止损点。

---

## 2. B1R-01 终局攻击清单与逐项证据 → **CLOSED**

### 2.0 修复方案与「为什么这次不一样」

- **共享核心**：新建 `scripts/lib/anchor_selection.py`，承载 `input_identity`（输入文件/目录内容身份哈希）、`_detect_input`（输入嗅探 SQL）、`generate_anchor_selection`（日频净变动/余额/分格/每格 `hash()` 选点 + 四类强制点）。producer（`anchor_plan.py:36`）与 consumer（`time_spotcheck.py:44`）**都 `from anchor_selection import`**——同一份实现，非两份副本（攻击 d 关闭，见 2.4）。
- **consumer 语义门**（`time_spotcheck.py:139-185` `validate_semantic_replay`）：`--input` 必填 → 先核 `input_identity(--input).sha256 == plan.input.sha256`（把真实数据字节绑进 plan）→ 再用 plan 声明的 11 个重放参数（`REPLAY_PARAMETER_FIELDS`）跑 `generate_anchor_selection` → 逐字段比对 `date_range/time_cuts/cell_population/boundary_blocks`、多重集合比对 `matrix_points/forced_points`。任一缺参或差异 `return 2`。该门在 dry-run 与正式路径共用，且早于分型、receipt 构建、任何 RPC。
- **和前两轮的本质区别**：round1 校验 `plan.producer==receipt.producer`（两个自洽声明）、round2 校验 `producer.path=="anchor_plan.py"`+公开 sha（两个公开常量）——都是「照抄可满足的声明」。round3 校验的是「**这套点集合是不是这份真实输入 + 这套参数的确定性函数值**」，没有任何可照抄的常量：点集合依赖输入**内容**，而输入被 sha256 绑定。手写方要通过，必须真跑核心算出点集合——那就等价于真跑了 producer。

### 2.1 绿例基线（真实产物，作对照）

真实转账 CSV（85 行、7 活跃日、多余额档 + 1 笔巨鲸）→ 真 `anchor_plan.py` 默认参数产 **8 点**（6 矩阵 + 2 强制），真 consumer dry-run `rc=0`（`balance_points=7, tx_points=1, total=8`）。选点数 > 1，缩水才有意义。脚本 `/private/tmp/r9b1r3/build_baseline.py`。

### 2.2 攻击逐项（全部真传 `--input`，直击 `validate_semantic_replay`）

脚本 `/private/tmp/r9b1r3/attack_battery.py`（除注明外均 dry-run；每次篡改后**自洽重签 receipt** 的 output size/sha256/probe_count，排除「只是 receipt 层拦下」的假象）：

| 攻击 | 手法 | 结果 | 拦截点 |
|---|---|---|---|
| **a 手写任意锚点** | 手写 1 个 `addr=0xaaa…` 的点、清空 forced，重签 receipt | **REJECT rc≠0** | `matrix_points differs from deterministic replay (missing=6, extra=1)` |
| b1 改 expected_balance_raw | 把某点余额改 999999 | **REJECT** | `matrix_points differs …(missing=1, extra=1)` |
| b2 删一个锚点 | pop 一个 matrix 点 | **REJECT** | `matrix_points …(missing=1, extra=0)` |
| b3 改 cell_population 一格 | 某格改 999999 | **REJECT** | `cell_population differs …` |
| b4 换 seed（合法 int） | seed+7 | **REJECT** | `matrix_points …(missing=5, extra=5)`（换 seed→换选点） |
| b5 声明多一个 boundary | `boundary_blocks=[150]` | **REJECT** | `forced_points …(missing=2, extra=0)`（重放据此多算交界点） |
| b6 改 threshold_pct | 改 0.001 | **REJECT** | `cell_population differs …`（改档→改分格） |
| b7 改 min_pct | 改 50.0 | **REJECT** | `cell_population differs …` |
| b8 改 date_range | 改 `[…,2025-01-31]` | **REJECT** | `date_range differs …` |
| b9 改 time_cuts | 改 `[…]` | **REJECT** | `time_cuts differs …` |
| **c3a 多重集去重** | 复制一个点使其出现两次 | **REJECT** | `matrix_points …(extra=1)`（`Counter` 抓重复） |
| c3b 重排点序 | 反转 matrix_points 顺序 | **ACCEPT rc=0**（正确/无害） | 多重集比对本就无序敏感，语义等价 |
| **c3c 类型混淆** | `day_end_block` int→str | **REJECT** | `matrix_points …(missing=1, extra=1)`（canonical json 串不同） |
| c1' 输入错配 | 真 plan + 错 `--input`（内容不同） | **REJECT rc=2** | `input sha256 mismatch: actual … != plan …` |

**结论**：语义重放对「伪造/篡改覆盖面」的正向拦截面完整。手写方无法在不真跑确定性核心的前提下产出任何能过闸的 plan。原 C2/C3（round2 穿透反例：真路径真 sha + 手写 1 点）在本轮语义门下等价于攻击 a，**已被拒**（仓库自带 test 9 亦覆盖，我独立复现一致）。

### 2.3 攻击 c（找重放的缝）逐条结论

- **被 consumer 忽略的选点参数？无。** `REPLAY_PARAMETER_FIELDS`（chain/token/final_block/total_supply/decimals/threshold_pct/min_pct/per_cell/edge_max/seed/boundary_blocks）覆盖了 `generate_anchor_selection` 全部影响选点的入参；只有 `mem_limit/threads` 不在其列，而二者**不影响选点输出**（HUGEINT SUM 与全序 tie-breaker 使结果与线程数无关——实测 `--threads 1` 重放仍 `rc=0` 匹配）。故「借未校验参数制造 plan↔replay 分歧」这条**不成立**。
- **多重集能否用重复/顺序/类型变体骗过？不能。** 去重 REJECT、类型混淆 REJECT、重排正确 ACCEPT（无害）。canonical `json.dumps(sort_keys=True)` 使 100 与 100.0、int 与 str 都判不等。
- **`--input` 与 `plan.input.sha256` 的绑定能否用「换一份能重算出目标选点的输入」绕过？** 见 2.5 观察——能构造「假输入 + 与之自洽的真 plan」使**重放**通过，但这不属 time_spotcheck 的绑定职责，且正式路径有 RPC 兜底。非 B1R-01 缝。

### 2.4 攻击 d：producer/consumer 是否真共用一份 anchor_selection

`rg "from anchor_selection import"`：`anchor_plan.py:36`、`time_spotcheck.py:44` 均 import 自同一模块，仓库内 `generate_anchor_selection`/`input_identity` 各只有一处 `def`（在 `anchor_selection.py`）。**无两份副本**，无法「针对 consumer 那份单独构造」。绿例基线（producer 产物被 consumer 重放逐字匹配）实证二者行为一致。

### 2.5 归因裁定：B1R-01 = CLOSED

判据「手写方能否在不真跑确定性核心的前提下产出过闸 plan」= **否**（2.2 全表实证）。上轮工单不变量「正式 EVM plan 必须由登记 producer 针对同一 chain/token/final block 和真实输入生成……consumer 只接收可独立校验的真实 producer receipt」——现由「consumer 亲自重算并逐项比对」在实现层闭合，plan 变成自证对象。给出 CLOSED。

---

## 3. 两项 P3 结论

### B1R2-01（末尾空行无主夹带）→ **CLOSED**

- 上轮：`658f78e` 前 `solana_attested_session.py` 末尾空行被无主删除。
- 本轮：`git diff 0bb94ba..120c9ef -- solana_attested_session.py` 仅 1 hunk（EOF +1 空行），`tail -c 6 | od -c` = `s ) ) \n \n`——空行已恢复。文件是批一新建，此字节属批一创建态，本轮只是回退上轮的无主删除，未夹带其他改动。→ CLOSED。
- **如实登记的张力（不构成 finding）**：`git diff --check 63cf715..120c9ef` 会报 `solana_attested_session.py:119: new blank line at EOF`。根因＝该文件相对冻结基线 `63cf715` 是整份新增，其批一创建态本身就带一个 EOF 空行（一处轻微空白瑕疵）。修复方 `b1_progress.md:311` 已显式登记此告警且声明「不擅自再删」——恢复满足 B1R2-01、再删又变成新的无主夹带，两难下选择回到被授权态并上报，处理正确。该 EOF 空白瑕疵应作为**有主**改动在后续批次清理，不在本轮止损范围。

### B1R2-02（EXPECTED_PLAN_PRODUCER 第三事实源）→ **CLOSED**

- 上轮：`time_spotcheck.py` 本地硬编码 `EXPECTED_PLAN_PRODUCER`，与 manifest 登记、文件实际位置三处零对账。
- 本轮单源化实证（`rg -n EXPECTED_PLAN_PRODUCER scripts/`）：
  - **赋值仅一处**：`anchor_selection.py:13`；
  - consumer `time_spotcheck.py:44` 为 `import`、`:84/:86` 为使用；
  - `test_time_spotcheck.py:26` `import`、`:301-303` 为对账守卫。
- **与 invariant_manifest 真对账**：`test_time_spotcheck.py` 第 12 项（`:296-303`）读 `invariant_manifest.json`，断言含 `anchor-plan/v2` 的 `receipt_producers` 条目**恰好 1 条**且其 `script == anchor_selection.EXPECTED_PLAN_PRODUCER`。改常量或改 manifest 任一处而漏同步即红——双向咬合。实跑该契约 `PASS`；`invariant_scan.py` 亦 `PASS`（`receipt_producers=49 … exceptions=0`）。
- 修复方未采「生产件 import 测试件 manifest」的倒置依赖，而是「常量入共享生产模块 + 契约测试对账」，正合上轮 B1R2-02「最低成本是加一条守卫而非倒置依赖」的建议方向。→ CLOSED。

---

## 4. 新 finding

### B1R3-01｜P3｜历史漏检｜consumer 接受退化选点参数的**真实** producer plan，抽查覆盖面可被压到 2 个强制点

**证据（全真实产物，无任何手写；脚本 `/private/tmp/r9b1r3/attack_paramshrink.py`、`final_probe.py`）**：

同一真实输入，真 `anchor_plan.py`：
- 默认参数 → 8 点（6 矩阵 + 2 强制），consumer `rc=0`；
- `--per-cell 0 --edge-max 0`（不传 `--boundary-blocks`）→ 产出**合法** 2 点 plan（0 矩阵 + 2 强制：全史最大单笔 + 最大单日净变动），consumer dry-run `rc=0`（`balance_points=1, tx_points=1, total=2`）；
- 同一 2 点 plan 走**正式路径**（死 RPC）→ 通过 `validate_semantic_replay`（`semantic replay` **未**出现在 stderr），抵达 RPC 阶段并写 error receipt——即活 RPC 下会产出 `verdict=PASS`。

即：`per_cell`/`edge_max` 在 `time_spotcheck._strict_int` 只校验「是整数」、不校验下界，producer 端 `--per-cell/--edge-max` 亦无下界；调用方可用退化参数把分层矩阵与门槛边缘点清零，只剩 2 个算法强制的极值点，而重放逐项一致、receipt 照打 PASS。下限是 2（两个强制点是无条件的、不受参数控制，故压不到 1）。

**为什么判「历史漏检」而非「B1R-01 未闭合」（最强替代解释及不采纳/采纳理由）**：

- 替代解释①「这是 B1R-01 的自选覆盖面在复活，应判 REOPEN」。**不采纳**：B1R-01 不变量的三个分句——「由登记 producer 生成」「针对真实输入」「consumer 只接收**可独立校验**的真实 producer receipt」——被这份 2 点 plan **逐句满足**（它确由真 producer 产出、对真实输入、且被 consumer 亲自重放验证通过）。不变量对最小覆盖面/参数下限**只字未提**。方法论 §二规则 1 要求「无法排除旧不变量被击穿」才归修复不全；此处旧不变量可**明确排除**被击穿（每句都成立）。更关键：B1R-01 的危害原文是「缩水成**任意 1 个易过的**锚点」，而语义重放恰恰杀死了「任意」（算法强制）与「易过」（强制点是最大单笔/最大单日净变动＝最难伪造、最该查的极值，且被 RPC 实核）——2 点缩水既非任意、亦非易过，与 B1R-01 危害不同型。
- 替代解释②「修复中新引入」。**不采纳**：producer 的 `--per-cell`（默认 1）/`--edge-max`（默认 5）**无下界**早于冻结基线 `63cf715`（本轮 diff 未触碰这两个 argparse 定义）；且修复前的 consumer 根本不重放、完全信任 plan，缩水更容易。本轮 repair diff 既未引入、也无义务引入覆盖面下限。规则 2 的「repair diff 新造成新接受面」不成立。
- 采纳「历史漏检」：缺陷早于基线，且同时排除前两类（规则 3 满足）。

**最强「这根本不是缺陷」的反方（有相当分量，如实登记）**：`per_cell`/`edge_max` 是正当的操作者调参旋钮；持有人极少、天然选点就少的代币，强制下限反而会误伤合法小样本分析；把 `--per-cell 0` 设下去等于操作者在破坏自己的分析（何况输入也在其掌控）；两个强制极值点无论如何都被 RPC 实核；receipt 里 `points/balance_points/tx_points` 如实记录了点数，可审计。**仍记 P3 的理由**：缩水后的 receipt 与全量 8 点的 receipt 携带**同样的 `verdict=PASS`/schema**，下游 `AUTO_GATES` 只读 verdict 时无法区分「2 点」与「全量」，而中段典型地址的数据洞恰恰只有矩阵点抽得到、强制极值点抽不到。方向是「覆盖变少」而非「fail-open 放假货」，故封顶 P3、不 ≥P2、不 block。

**给下一轮的可选加固（不代替设计，非本轮止损项）**：consumer 侧对 `per_cell>=1`、或对 `matrix_points`/`cell_population` 的非空做最低覆盖断言；或把 `per_cell/edge_max` 写进 time_spotcheck receipt 供审计；或由 skill 流程固定这两参数为 canonical 值。任一即可，且需权衡小样本代币的合法性。

### 观察（非 finding）：输入替换是上游职责的 scope 边界

consumer 强绑 `--input` 与 `plan.input.sha256`（错配即 REJECT，2.2 表 c1' 实证），但**不**绑定 `--input` 是否为本案 canonical merged 数据集。故可构造「精心设计的极小假输入 + 与之自洽的真 plan」使**重放**通过（实测 `attack_battery.py` c1：假输入 4 点 plan 被 consumer 接受）。这**不是 time_spotcheck 的缺陷**：核验 `--input` 是不是 canonical 数据集，是上游采集管线（handoff_manifest / merged 数据自身 receipt 链）的职责；且正式路径的 RPC 实核会兜住假输入里捏造的余额/tx（除非攻击者引用真链状态，那已等价于换了一份更小的真数据）。属职责分层，登记备查。

---

## 5. 本轮 diff 夹带扫描（56 hunk 逐块归属）

`git diff --unified=0 0bb94ba..120c9ef` 逐文件统计 `@@`，共 **56 hunk / 11 文件**；不看 map 独立判归属，再与 `diff-finding-map.md` 的 B1F2 三行对账。

| 文件 | hunk | 独立归属 | map 声明 | 对账 |
|---|---:|---|---|---|
| `maintenance/repair-20260806/b1_progress.md` | 1 | B1F2-G1/G2/G3 消化节 | 三行均列 | ✓ |
| `maintenance/repair-20260806/diff-finding-map.md` | 3 | B1F2-G3（owner 三行 / SHA 对照三行 / 未映射 hunk 复算：上轮自报 0→1 修正 + 本轮 0） | B1F2-G3 | ✓ |
| `scripts/lib/anchor_plan.py` | 11 | B1F2-G1 纯抽取（删 `urls/_sha256/_input_identity/_detect_input/EXPLORER/Z/DEAD`，换 `from anchor_selection import`） | B1F2-G1 | ✓ |
| `scripts/lib/anchor_selection.py` | 1 | B1F2-G1（新共享核心）+ G2（`EXPECTED_PLAN_PRODUCER` 单源赋值） | B1F2-G1/G2 | ✓ |
| `scripts/lib/solana_attested_session.py` | 1 | **B1F2-G3**（B1R2-01 末尾空行恢复，纯空白） | B1F2-G3 | ✓ |
| `scripts/lib/time_spotcheck.py` | 12 | B1F2-G1（`validate_semantic_replay`+`_strict_*`+`_point_multiset`+import 共享）+ G2（import 常量、删本地副本） | B1F2-G1/G2 | ✓ |
| `scripts/tests/test_batch1_rpc_attestation.py` | 1 | B1F2-G1（补 `--input`） | B1F2-G1 | ✓ |
| `scripts/tests/test_batch3_evm_vertical_slice.py` | 2 | B1F2-G1（补 `--input`，2 处 argv） | B1F2-G1 | ✓ |
| `scripts/tests/test_r7_findings.py` | 1 | B1F2-G1（补 `--input`） | B1F2-G1 | ✓ |
| `scripts/tests/test_r9_batch1_boundaries.py` | 3 | B1F2-G1（3 处 argv 补 `--input`） | B1F2-G1 | ✓ |
| `scripts/tests/test_time_spotcheck.py` | 20 | B1F2-G1（test 9 手写 1 点 / test 10 五变形 / test 11 `--input` 必填 / test 13 输入 sha 错配 + `produce_plan` 换 20 行真实 fixture）+ G2（test 12 manifest 对账） | B1F2-G1/G2 | ✓ |
| **合计** | **56** | | | **全部有主** |

**逐项验伪（不信自报，读 diff 正文）**：

- **anchor_plan.py（-291 行）确为纯抽取**：删除的都是被移入 `anchor_selection.py` 的辅助函数与常量，替换为一行 import；选点/发布逻辑主体（`_validate_probe_blocks`、plan 组装、`publish_txn`、启动隔离）未动。绿例基线 + `run_all 82/82` + 三链 EVM 纵切片实证抽取忠实（producer 产物被 consumer 逐字重放匹配）。
- **time_spotcheck.py 无删除式夹带**：删除的仅 docstring、`import hashlib`、本地 `EXPECTED_PLAN_PRODUCER`、本地 `_sha256`，以及 output size/hash 校验行的**旧写法**（`_sha256(plan_file)` → 换成共享 `sha256_file(plan_file)`，校验本身仍在 `:106-108`）。无任何验证被删。
- **既有测试适配无削弱**：`test_r7_findings/test_batch1_rpc_attestation/test_batch3_evm_vertical_slice/test_r9_batch1_boundaries` 的改动全部是给 consumer 调用补 `--input <source>`，无断言删除或放宽。
- **test_time_spotcheck.py 只增强不削弱**：10→20 项，老 8 项（含 test 8 Markdown 伪造 producer 的路径白名单反例）全保留，`produce_plan` 由 1 行升为 20 行更真实 fixture。round2 的路径白名单（`:84`）作为纵深防线**保留**在语义重放之上（分层）。
- **范围抽验**：`VERSION` 零 diff（`6.36.0`）；`git status --short` 空、HEAD=`120c9ef`；无 `.pyc`/`__pycache__` 入版本控制。
- **唯一空白告警**：`git diff --check` 仅报 `solana_attested_session.py:119 new blank line at EOF`——即 B1R2-01 恢复的那个字节，已在 §3 定性（属批一创建态、后续有主清理）。

**结论**：未映射 hunk = **0**（与自报一致）；无「有 owner 的 hunk 内夹带目的外语义内容」（上轮 B1R-04 那种形态本轮未复现）；无格式化夹带。

---

## 6. 实际运行的关键命令清单

工作目录为 worktree 或 `/private/tmp/r9b1r3/`；**对仓库严格只读**，未执行任何 git 写、未增删改 worktree 任何文件，临时产物一律落系统 tempdir。

**仓库状态与 diff**
```bash
git log --oneline -8 ; git status --short ; git rev-parse HEAD        # HEAD=120c9ef，status 空
git diff --unified=0 0bb94ba..120c9ef | grep -c "^@@"                 # → 56
for f in $(git diff --name-only 0bb94ba..120c9ef); do \
    git diff --unified=0 0bb94ba..120c9ef -- "$f" | grep -c "^@@"; done
git diff 0bb94ba..120c9ef -- scripts/lib/anchor_plan.py scripts/lib/time_spotcheck.py \
    maintenance/repair-20260806/diff-finding-map.md scripts/tests/*.py
git diff --check 63cf715..120c9ef                                     # 仅 solana EOF 空白告警
tail -c 6 scripts/lib/solana_attested_session.py | od -c              # 末尾 \n\n 已恢复
rg -n "EXPECTED_PLAN_PRODUCER" scripts/ ; rg -n "from anchor_selection import" scripts/lib/
```

**自报声明重验（不信自报，逐条重跑）**
```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py            # 全部通过 / exit 0
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_time_spotcheck.py # 20/20
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py      # 49/53/58/38/58 exceptions=0
cat VERSION                                                            # 6.36.0
```

**攻击脚本（全部本轮新写，适配新 `--input` 接口，直击 validate_semantic_replay）**
```bash
python3 /private/tmp/r9b1r3/build_baseline.py     # 绿例：真 producer 8 点 → consumer rc=0
python3 /private/tmp/r9b1r3/attack_battery.py     # a 手写1点 / b1-b9 九类篡改 / c3 多重集 / c1 输入替换与错配 → 除重排外全 REJECT
python3 /private/tmp/r9b1r3/attack_paramshrink.py # B1R3-01：真 producer --per-cell 0 --edge-max 0 → 2 点 plan 被 consumer 接受
python3 /private/tmp/r9b1r3/final_probe.py        # B1R3-01 正式路径过闸 + threads=1 重放确定性
python3 /private/tmp/r9b1r3/perf.py               # 1,000,000 行 129.7MB：producer 0.97s / consumer 重放 0.96s
```

**攻击脚本留存**：`/private/tmp/r9b1r3/`（`build_baseline.py`、`attack_battery.py`、`attack_paramshrink.py`、`final_probe.py`、`perf.py`），供裁判独立复现。上轮脚本 `/private/tmp/r9b1r2/`、`/private/tmp/r9b1/` 保持原状未改。

---

## 附：自报验证表（逐条重跑）

| # | `b1_progress.md` B1F2 节声明 | 我的结果 | 属实 |
|---:|---|---|:--:|
| 1 | `test_time_spotcheck.py` 20/20 | 实跑 20/20 | ✅ |
| 2 | 全量 `82/82 PASS`、末行「全部通过」、exit 0 | 实跑「全部通过」exit 0 | ✅ |
| 3 | `invariant_scan` `49/53/58/38/58`、exceptions=0 | 逐字一致 | ✅ |
| 4 | 百万行 producer 0.96s / consumer 0.91s、无采样降级 | 1,000,000 行：0.97s / 0.96s | ✅ |
| 5 | `EXPECTED_PLAN_PRODUCER` 唯一赋值在 `anchor_selection.py`，consumer/test 只 import | `rg` 证实 | ✅ |
| 6 | 末尾空行恢复、文件以 `\n\n` 结尾 | `od -c` 证实 | ✅ |
| 7 | 未映射 hunk = 0（本轮区间） | 独立复算 56 hunk 全有主 → 0 | ✅ |
| 8 | 未改 `VERSION`、未做 git 写 | `6.36.0`、status 空、HEAD 未动 | ✅ |
| 9 | 「B1R-01 终修」四路红→绿 | 手写 1 点/五变形/输入错配/缺 `--input` 独立复现均 REJECT；真 producer 正例通过 | ✅ |
| 10 | threads 无关确定性（`hash/value/block`+`addr/day/tx/from/to` 全序 tie-breaker） | `--threads 1` 重放仍 rc=0 匹配 | ✅ |

18 条自报口径无一失准；失衡处仅在「覆盖面下限未设」——但那不在其宣称范围内，属本报告 B1R3-01 历史漏检。
