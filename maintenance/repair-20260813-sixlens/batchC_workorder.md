# 批 C 施工工单：F-05（阵营 spec 四族等深）＋ F-04（阵营序列 producer→consumer 链）

施工方：Fable 5 直接施工（原派 codex 通道因沙箱三连拒 app-server 初始化零施工退出，用户既定计划范围内代工，判断与验收仍归裁判）。基线 main@2582c81（v6.39.5），批内先 F-05 后 F-04。

---

## 施工前两处 rg 定案（计划要求先定案再动工）

### 定案 1：replay_edges 缺 camps 文件的合法性 → **硬拒 exit 2**

调用面全量证据：
- `scripts/solana/replay_edges.py` main：`--camps` 默认 `camps.json`，唯一调用 `cmd_evolution(edges, dec, args.camps, stake_pools)`；
- `scripts/tests/test_review_resume_integrity.py:233`：唯一进程内调用，**camps.json 在场**（`Path("camps.json").write_text(...)` 后才调）；
- 文档面：`replay_edges.py` docstring「evolution 的阵营定义读 --camps camps.json」、`references/data-pipeline-solana-scan.md:100`（evolution --stake-pool 用法）——**全库无一处记载"无 camps 跑 evolution"的用法**；
- 真实案（TROLL/PYTHIA/PUB）evolution 全部带 camps.json。

修前行为＝缺文件静默按空 spec 重放（全部地址落散户/狙击者两桶，序列外观正常实际零阵营——F-05 同族静默失真）。定案：**缺文件 print stderr＋exit 2**；确需无阵营探索跑，显式放一份内容为 `{}` 的 camps 文件表达意图（空对象在场＝合法，文件缺席＝拒）。

### 定案 2：burn schema 豁免键清单（精确键名）

| 产物族 | 轴/元数据键 | burn 键 | burn 是否参与 100% 闭合 |
|---|---|---|---|
| EVM `camp_series.json`（replay_pass2.py:110-114 / replay_duck.py:470-476，dict 形态） | `dates`、`_meta` | `burn_cum_pct`（顶层单列） | **不参与**（分母=当期净供应，可 >100%）；legacy 口径（`CHIP_LEGACY_CAMP_DENOM=1`）`销毁` 桶参与闭合 |
| Solana `camp_share_series.json`（replay_edges.py cmd_evolution，行数组） | `ts`、`_supply_raw` | `锁仓/销毁`（行内） | **不参与**（分母=净供应 minted−burned，有 burn 时全桶合计 >100% 是合法形态——原稿 100% 单式闭合闸会误杀的正是它） |
| Solana `camp_series.json`（build_evolution.py:171-177，行数组） | `ts` | `锁仓/销毁`（行内） | **参与**（分母=config total_supply，散户残差吸收）——与 replay_edges **同名键不同语义**，rg 定案新发现 |

由第三行的新发现，闭合公式定为**双式**：非 burn 桶之和≈100 **或** 全桶之和≈100（容差 0.05pp），二中其一即过；burn 桶单独验非负有限、不设 100 上界；全桶全零点（供应尚未产生）豁免。`销毁`（EVM legacy 堆叠桶）不进豁免清单也不进白名单——legacy 重放不入正式编译，白名单先拒，列进豁免清单就是永远走不到的死分支（变异法自检会抓的那种）。

---

## 末点对账实测前置（计划 ⚠️ 条款：两个真实案纵切片先实测，可行才落地）

**结论：可行**，带三条实测落锤的边界条款（全部已写死进实现）。

实测一（Solana·TROLL 案，`/Users/uravvv/Desktop/老公用/fable筹码分析/TROLL分析`）：camps.json（5 阵营）＋链上终态快照 `holders_owners.json` 重算 vs 案内序列末行——**spec 内静态阵营：小庄 0.0000pp、狙击集团 0.0000pp、项目方 0.0000pp 全中**；流动性池差 0.076pp、CEX托管差 0.18pp、动态桶"其他大户"差 0.44pp。换 `_replay_final.json`（另一版数据段重放）重算：差扩大到 1.70~2.27pp。

实测二（EVM·TAG 案，`/Users/uravvv/Documents/5.6筹码分析/TAG分析`）：whale_groups 地址集＋`data/replay/balances_final.json`＋分母=mint−zero_inflow（replay_stats 机械派生）重算 vs 序列末点——**项目方 73.1451% vs 73.1588%，差 0.0137pp 命中 0.05pp 容差**；动态判定桶"其他大户"差 1.04pp（案内 ≥0.1% 动态阈值判定，spec 外）。

三条边界条款（实测直接证得，非推演）：
1. **快照必须与序列同一次重放同源**——TROLL 异时点链上快照差 0.08~0.44pp、异版重放差 1.7~2.3pp，异源比对必假红。落地＝sidecar 的 final_balances 只登记同一 producer 运行落盘的终态文件（EVM=balances_final.json 同进程 pass1 产物；sol-rows=effective_balances.json 同函数产物）。
2. **动态桶不可机械派生**（其他大户动态阈值/首30分钟狙击者/散户残差不在 camps spec）——末点对账范围＝spec 内阵营逐桶精确比对＋spec 外桶合并残差用恒等式 `100−Σspec` 比对。**这不是单向下界**：spec 桶全部双向精确、残差也是双向等式，只是把不可派生的桶合并到一个恒等量上。未触发降级上报条款。
3. **分母机械派生不信自报**——EVM 当期净供应=Σ(balances_final)−ZERO 哨兵余额（恒等），legacy=Σ(balances_final)=mint_total（供给闭合恒等）；sol-rows 净供应=Σ(effective_balances 全部值)（重放恒等）且必须与 reconcile_receipt.net_supply_raw 交叉相等。TAG 实测验证了 EVM 式（分母=mint−0，项目方命中）。

实测同时抓到一个附带发现：TAG 案内序列桶名"大庄Gate/大庄Bitget"是实体级自造桶名，不在 CAMP_ORDER——这形态在 fig1 直出路径本来就画不出（stackplot 白名单静默跳过），白名单校验把它显式拒掉是正当收紧；测试含该形态反例。

**build_evolution（sol-anchor-rows）不接入正式编译链**：小样本锚点法辅助件（docstring 自 declare「正式重放必须走 replay_edges/DuckDB」）、无对账链锚（无 reconcile/supply_truth 绑定面）。四族等深体现在 spec 校验与 sidecar 记录（四族全挂），正式消费入口只认经过对账链的两族（evm-dict/sol-rows）——consumer 对 sol-anchor-rows 显式 exit 2 并给出改道指引。

---

## ①栏：不变量（本批装的闸到底保什么）

- **F-05**：camps 域是互斥划分——任一规范化地址在全 spec 中至多出现一次；违反时不允许任何静默倾斜（JSON 键序不得决定归属），一律 exit 2。互斥只属 camps 域，entities 的 setdefault-append 多归属是 by design（图 2 实体线允许与阵营重叠），一行未动。
- **F-04（数值面）**：进入 analysis-state 的 camp_share_series 必然满足：桶名 ∈ CAMP_ORDER_MODERN ∪ {burn_cum_pct}、全值有限、非 burn 桶 ∈ [0,100]、同点双式闭合、日期轴 UTC 严格递增。
- **F-04（来源绑定）**：经 `--series-source` 进入正式编译的序列，必然是四族 producer 落盘的字节原样（输出 sha）、其 spec 与输入实物三验在场（存在+sha+size）、锚进案内已对账数据链（supply_truth/reconcile 登记面）、且末点与 spec+同源终态快照的机械重算闭合。**诚实边界**：伪造者仍可保末点改中间点——把伪造成本推到"伪造整案数据链"，与 F-12 已接受边界同款残余；validator 是一致性校验器不是真实性证明器。
- **F-04（钳制）**：figures check 的 `--tol-pp` 在正式模式恒为 0.05（判定翻转参数不留旋钮），覆盖必须显式 `--exploration` 声明（exit 2 政策拒，与 supply_truth `--tolerance-bps` F-02 模式同族同深）。

## ②栏：同族 rg 清单

- 四族 camps 装配点（全部收敛到共享实现）：`replay_pass2.py:28-34`（旧 `set(x.lower())`+dict 覆盖）、`replay_duck.py:374-380`（旧「后配置覆盖先前（复刻 dict 语义）」注释已随修复删除）、`replay_edges.py:238-243`（旧 exists else {} 静默空 spec）、`build_evolution.py:76`（旧 json.load 裸解析，JSON 重复键解析后不可见）——第四族为计划补漏项，已同深接入。
- 序列消费面：`state_from_facts.py compile_state`（本批加双闸）、`figures_from_facts.py mode_fig1`（旧 state 直喂重绘路径，**不动**——R10 台账 F-09 root cause 已由 --series-source 顺带闭合，台账条目按计划保留）、`figures_from_facts.py mode_check`（--tol-pp 本批钳制）。
- 判定翻转参数同族（记录不修，与批 A 台账一致）：accounting `--samples`、verify_recon `--top-n`、anchor_sampler 覆盖窗——证据强度参数非判定翻转参数；`--tol-pp` 与它们不同族（直接决定 PASS/FAIL），故本批钳。
- 白名单唯一权威：`standard_charts.CAMP_ORDER`（analyze-workflow.md:164 印证「唯一权威；现行 14 键」＝拆分后的 MODERN 段，文档说法无需改）；`state_from_facts` 经 `camp_series_provenance.modern_camp_whitelist()` 函数内 import，无第二份手抄清单（测试断言 `modern_camp_whitelist() == set(CAMP_ORDER_MODERN)`）。
- sol-rows 两个 legacy 动态桶名（`其他散户`/`首30分钟狙击者`，replay_edges 现役输出）与 MODERN 白名单的冲突：consumer 转换层固定并桶入 `散户`（`SOL_DYNAMIC_BUCKET_MERGE`，转换语义非阵营名单，狙击窗明细在 sniper_set.json 不丢）——不改 producer 输出契约（golden_baseline 对表与 test_h06 断言零变化）。

## ③栏：三件套测试（scripts/tests/test_repair_batch_c.py，69 checks，已入 run_all SUITE）

- **原反例先红后绿**：F-05 同址跨营（camp_A/camp_B，JSON 后键静默夺走归属）→ 四入口全部 exit 2（修前行为=后项覆盖 exit 0，由变异自检的"删掉即红"等价证明）；F-04 最小反例（source 注入 大庄=-899/散户=999）→ compile_state 拒（修前原样输出）。
- **同族变体**：EVM 大小写变体（0xAbC vs 0xabc）跨营+同营内均拒；Solana base58 大小写敏感不误杀（大小写不同=不同地址，绿例）；JSON 重复键（{addr:camp} 同址写两遍）解析层拒；两 EVM 引擎同 spec 双双 exit 2（test_engine_equivalence 全量绿=同深不破等价）；实体级自造桶名（TAG 实测形态"大庄Gate"）拒；日期轴族（倒序/重复/非法/时区换算倒挂拒；naive-aware 混用 UTC 轴递增、闰日、全零点豁免=绿例）。
- **失败分支**：缺 sidecar、序列篡改（输出 sha）、spec 等长篡改（sha 分支）与增长篡改（size 分支）、无 supply_truth、replay_stats sha 不命中、reconcile gate_pass=false、sol-anchor-rows 拒入、双源分叉（source 手填≠转换结果）、缺 camps 文件、值非列表、空阵营名——各有独立反例，且每个反例断言错误信息特征串（删掉校验→特征串消失→测试红）。
- **合法绿例（防误伤）**：EVM 端到端含 burn（burn_cum_pct 末点 5.2632% 重算命中）、Solana 端到端含 burn（锁仓/销毁 11.11% 口径感知通过、净分母族全桶合计>100 合法放行）、显式空 spec {}、反例注入全部还原后整链复绿（防测试留脏）。
- **真实产物形态用例（批 B 教训条款）**：EVM 链夹具=replay_duck **真跑产出**（camp_series.json 真形态含 `_meta`/`burn_cum_pct` 真键名）；Solana 链夹具=replay_edges reconcile+evolution **真跑产出**（行内 `锁仓/销毁`/`_supply_raw` 真键名）；另有 TROLL/TAG 两真实案的实测（上节）覆盖"真实案行为变化须真实案实测"条款——sidecar 消费与末点对账的口径全部按真实案数据面定型后才写代码。
- 可重放反例脚本：`maintenance/repair-20260813-sixlens/counterexamples/fake_series_dualfeed.py`（伪序列双喂三场景，rc=0）。

## ④栏：新建代码六视角自审（①字段来源 ②失败分支）

- `scripts/lib/camp_spec.py`：字段来源=spec 文件原始列表（set 化之前）；失败分支全部显式 exit 2（非 dict/非 list/空名/非串地址/重复），无静默回退。单点查重（owner 映射）覆盖同营内与跨营两种重复、消息区分——初版曾留 seen_here 并行冗余分支，变异自检抓出后已简化（每道检查独立可命中）。
- `scripts/lib/camp_series_provenance.py`：sidecar 字段全部机械派生（sha256_file 现算，无自报转录）；denominator 仅作口径声明、consumer 分母一律从终态快照重算（字段来源可疑处不信 sidecar 自报数字）；失败分支=SeriesProvenanceError（ValueError 子类，经 compile_state main 的既有捕获统一 BLOCK+exit 2）；_resolve_ref 只按 basename 在序列目录与案根两层内找（sidecar 不携带可逃逸路径），symlink 拒（与批 B F-08 同口径）；写侧 tmp+os.replace 原子替换。已知偏差源预登记：sol-rows 末点重算用合并后 effective_balances 判正，producer 快照是 spot/staked 分开判正——现货负+质押正的边角实体两者有微差，容差 0.05pp 吸收，超差 fail-loud 人工核（不静默）。
- `state_from_facts.py` 增量：--series-source 逻辑全部在 bind_series_source（main 侧），compile_state 签名不变（既有进程内调用面零破坏）；series 由转换器单点生成，source 手填必须逐点相等（消灭双源）。
- 新契约面（**契约登记统一留批 D**，本批只记账）：schema `camp-series-provenance/v1`（权威定义已落 scan-schemas.md §13）；CLI 面 `state_from_facts --series-source`、`figures_from_facts check --exploration`；invariant_manifest.json 本批已同步 +3 条（producer/consumer/atomic 各 1，全收敛在共享库单文件——四 producer 无 schema 字面量不进清单）。

## ⑤栏：归因预判

- F-05 归因=历史漏检（R10 候选 RA-02 存量）：文档声明互斥但四份手抄装配各自演化，replay_duck 甚至把覆盖行为注释成"复刻 dict 语义"当成对旧引擎的忠实——**对错误语义的忠实复刻仍是错误**；该注释已随修复删除。
- F-04 归因=历史漏检（RA-01 存量）+架构位错：series 承载权给了 source（人工装配域）而校验权没跟上；本批把承载权收回 producer 链（--series-source 直出）、source 退化为可省略的一致性副本。
- 施工中自查记录：①变异脚本初版用 `git checkout --` 还原未跟踪新文件→报错未还原（MEMORY「unstaged 施工 git checkout 陷阱」同款），当场改为内存快照备份制并手工还原两处突变残留（camp_spec.py owner 检查、camp_series_provenance.py sha 检查），还原后 grep "if False" 清零+全测复绿；②invariant_manifest 首次登记误用 indent=1 重排全文件（1915 行假 diff），git checkout 恢复后按原 indent=2 与原排序约定重插（净 +17 行）。

## 变异法自检（批 A 纪律 1：每条新校验"删掉即红"，13/13 成立）

方法：逐条把新校验临时失效→跑对应反例→确认反例转"被接受"→内存快照还原。脚本 scratchpad/mutation_check.py（临时件不入库），结果：

| # | 校验 | 突变后反例被接受 |
|---|---|---|
| 1 | F05 跨营查重 | ✅ |
| 2 | F05 查重总闸（同营反例；简化后单点） | ✅（简化前 seen_here 是冗余并行分支，已删） |
| 3 | F05 EVM lower 规范化 | ✅ |
| 4 | F05 JSON 重复键 hook | ✅ |
| 5 | F05 evolution 缺 camps 硬拒 | ✅（须同时中和 sidecar camps_spec 绑定这道新增二线才放行——入口闸独立性成立） |
| 6 | F04 compile_state 数值面挂载 | ✅ |
| 7 | F04 同点闭合 | ✅ |
| 8 | F04 桶名白名单 | ✅ |
| 9 | F04 日期轴严格递增 | ✅ |
| 10 | F04 值域上界 | ✅（反例=闭合容差窗内单值 100.03——"非负+闭合"数学上已覆盖 >100+tol 区间，上界的独立命中区间只有 (100, 100+tol]，如实记录） |
| 11 | F04 输出 sha 绑定＋末点对账 | ✅（双防线各自独立：关 sha 后末点对账仍拦，两道全关才放行） |
| 12 | F04 登记面命中 | ✅ |
| 13 | F04 --tol-pp formal 钳制 | ✅ |

## 改动文件清单与 diff-finding-map

| 文件 | owner |
|---|---|
| `scripts/lib/camp_spec.py`（新建） | F-05 |
| `scripts/evm/replay_pass2.py`（validate 接入＋sidecar） | F-05＋F-04 |
| `scripts/evm/replay_duck.py`（validate 接入＋:380 注释删除＋sidecar） | F-05＋F-04 |
| `scripts/solana/replay_edges.py`（缺 camps 硬拒＋validate＋sidecar） | F-05＋F-04 |
| `scripts/solana/build_evolution.py`（object_pairs_hook 加载＋sidecar） | F-05＋F-04 |
| `scripts/lib/camp_series_provenance.py`（新建） | F-04 |
| `scripts/report/standard_charts.py`（CAMP_ORDER 拆两段，合并保原序） | F-04 |
| `scripts/report/state_from_facts.py`（无条件数值面＋--series-source） | F-04 |
| `scripts/report/figures_from_facts.py`（--tol-pp 钳制＋退出码文档） | F-04 |
| `references/scan-schemas.md`（§13 新节＋路由行） | F-04 文档同批 |
| `references/report-template.md`（唯一生成命令＋两道闸＋--tol-pp 钳制） | F-04 文档同批 |
| `scripts/tests/invariant_manifest.json`（+3 条登记） | F-04 配套 |
| `scripts/tests/test_state_from_facts.py`（fixture 补散户闭合，断言未动） | F-04 配套（不为绿改弱断言：输入合法化非断言弱化） |
| `scripts/tests/test_repair_batch_c.py`（新建）＋`run_all.py`（SUITE +1） | 批 C 测试 |
| `maintenance/repair-20260813-sixlens/counterexamples/fake_series_dualfeed.py`（新建） | F-04 反例 |

## 退出码证据

- `python3 scripts/tests/test_repair_batch_c.py` → **rc=0**（69 checks）
- `python3 scripts/tests/invariant_scan.py` → **rc=0**（producers=53, consumers=58, atomic=44）
- `python3 scripts/tests/docs_lint.py --all` → **rc=0**
- 受影响契约测试逐一：test_state_from_facts / test_figures_from_facts / test_engine_equivalence / test_review_resume_integrity / test_wave_scan / test_entity_source_trace / test_batch3_solana_producers / test_batch3_solana_vertical_slice / test_batch3_evm_vertical_slice / test_build_html → **全部 rc=0**
- `python3 scripts/tests/run_all.py` 全量 → **rc=0**（52 项全绿）
- `counterexamples/fake_series_dualfeed.py` → **rc=0**

## 边界自查（铁律逐条）

- VERSION / SKILL.md 版本行 / pyproject.toml：未动（三处保持 6.39.5）。
- contract_manifest.json / contract_ids_snapshot.json：未动（新契约面记账留批 D）；report-template.md 的 CT-SEMANTIC-14 needle "state_from_facts.py" 保留在场。
- 批 D 生产文件（shared_release_receipt.py / audit_closed_accounts.py）：未动。
- 批 A/B 已收口实现（supply_truth_gate.py / accounting_gate.py / holder_distribution_scan.py / audit_release_gate.py）：未动。
- git commit：未做（工作树留给裁判验收）。
- 既有断言：未改弱（test_state_from_facts 仅 fixture 输入闭合化，断言原样）。

批C施工完成
