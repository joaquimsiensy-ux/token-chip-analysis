# 盲审 R4（opus）：PASS

盲审员：Opus 5（只读、全程离线）。对象：工作树 7.0.4 施工产物（仓库 `/Users/uravvv/.claude/skills/token-chip-analysis`，git main，HEAD `2000b6e`，含未提交改动）。
裁决基准：`r3_fix_ruling.md`（含末尾勘误）。未读取 `~/.codex/skills/_archive/`，未读取 tag `codex-frozen-20260915`，未 commit/checkout/stash，除本报告外未创建、修改或删除仓库内任何文件。

**结论：PASS。blocker 0 项；minor 3 项；nit 4 项。**

---

## 1. 生产文件 SHA-256 与改动范围

| 子项 | 判定 | 依据 / 只读复现命令 |
|---|---|---|
| 1.1 生产文件 SHA-256 = `e85acee4…aeda3cd1` | **PASS** | `shasum -a 256 scripts/report/entity_source_trace.py` → `e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1` |
| 1.2 逻辑改动仅限 plan D1–D3（另加 D4 授权的模块 docstring 一行） | **PASS** | `git diff HEAD -- scripts/report/entity_source_trace.py`。全部 hunk 逐一归属：docstring（D4 授权）、`GAP_EPS_REL`+`gap_eps()`（D2）、`algorithm` 加 `gap_eps_rel`（D3）、`simulate()` 签名带默认值 `gap_eps=EPS`（D3）、`residual_events` 计数与 `nonlocal`（D1）、缺口双桶分支（D1）、返回值加 `fp_residual_events`（D1）、`ev_map` 加 `fp_residual`（D1）、`trace_entity` 传 `gap_eps=gap_eps(total)`（D3）、`simulation` 诊断块加 `fp_residual_events`（D1）。**无任何 D1–D4 之外的改动。** |
| 1.3 账户判等/扣减/入账处 EPS 一处未动 | **PASS** | `grep -n "EPS" scripts/report/entity_source_trace.py` 与 `git show HEAD:scripts/report/entity_source_trace.py \| grep -n "EPS"` 对照。HEAD 9 处非缺口 EPS 引用（264/267/296/302/307/554/569/576 及定义行）在工作树对应 276/279/308/314/319/573/588/595 及 90 行，**代码文本逐字相同、仅行号平移**。HEAD:465 的 `elif shortfall > EPS` 一处拆为 477 `> gap_eps` + 481 `> EPS` 双分支，即裁决所指唯一逻辑改动点。`VectorAccount`/`LayeredAccount` 类体零 diff，`__slots__` 未动。 |
| 1.4 `gap_eps` 语义正确 | **PASS** | `gap_eps(total)=max(EPS, float(int(total))*1e-13)`；小供应量退化为 EPS（本报告 §3 N5 实测两版逐字相同，`fp_residual_events=0`）。`simulate` 内形参 `gap_eps` 遮蔽同名模块函数但仅在函数体内做数值比较，`trace_entity` 无同名局部量，无误用。 |

## 2. 测试文件：T4 比较器、四个 mixed 样例、T4-stress

| 子项 | 判定 | 依据 / 只读复现命令 |
|---|---|---|
| 2.1 T4 通用比较器恰好实现最终裁决 | **PASS**（附 minor M3） | `sed -n '198,355p' scripts/tests/test_entity_source_trace.py`。`eps_rounding_bound` 为 `abs(delta)*2**52 <= 4*n*supply + 2*2**52`，即 `\|Δ\| ≤ 4·n·2^-52·S+2`，**常数未放宽**，且用整数/Fraction 交叉相乘，无浮点二次误差。精确断言只剩 `stock_raw`；①非 UNRESOLVED 键逐键判界；②`gap704+residual704 − gap703` 合桶判界；③Σraw 判界；④逐笔短缺以 `float.hex` 原值取 Fraction 后判界；闭合 pct 与展示 pct 均按 `B/stock×100` 判界（`raw_delta = delta*stock/100` 回代同一个 B）。原始 `UNRESOLVED` 标签差走 `bound_checked=False` 的 `T4_LABEL_MIGRATION` 记录路径，不判界。计数/policy_details/指纹无相等断言。 |
| 2.2 既有具体断言保留 | **PASS** | `git diff HEAD -- scripts/tests/test_entity_source_trace.py \| grep "^-" \| grep -v "^---"` → **输出为空，零删除行**（全文件纯追加 568 行）。`check(` 计数 40 → 110。`expect_equal=True` 分支保留两组旧样例的 Σraw 相同、非 gap 键逐条相同、gap 拆分守恒、策略明细差为零等精确断言。 |
| 2.3 四个 mixed 样例断言值与独立内存重放一致 | **PASS**（四例全部重放，非只两例） | 见下表。重放器为本次自建、不复用测试文件任何 helper，仅调用两版真实 `trace_entity()` + 内存 HUGEINT 边表；7.0.3 基线取 `git show HEAD:scripts/report/entity_source_trace.py`（实测与测试所用 `3b29e38` 版本 SHA-256 同为 `ff4b640a…`，基线合法）。 |
| 2.4 T4-stress 真实 300 组固定种子 | **PASS**（附 minor M2） | `sed -n '564,672p' scripts/tests/test_entity_source_trace.py`：`seed=20260915, cases=300`；mint 以 3/4 概率落中间账户 A；转出可超余额；断言 `out_of_bound_count == 0`、`intermediate_mint_cases>0`、`overdraft_cases>0`、`min/max(lengths)==3/8`。日志实证：`grep -o "T4-stress max|Δ|=[^;]*;.*" maintenance/repair-20260915-eps-residual/test_entity_source_trace_r4b.log` → `max|Δ|=1536 raw; occurrences=6; out_of_bound=0`；`intermediate_mint_cases=91`、`overdraft_cases=158`、`external_middle_cases=300`。 |
| 2.5 done.md 表中 max\|Δ\| 与 test 日志一致 | **PASS** | `grep -o "T4-stress [a-z_]* max|Δ|=[^;]*; [a-z_=0-9]*" .../test_entity_source_trace_r4b.log` → 合桶 `unresolved_total=1536`、非 UNRESOLVED `non_unresolved_key=32`、逐笔短缺 `shortfall=1024`、`sum_raw=1536`、`closure_pct=5/22517998136858`、`display_pct=0`、迁移类 `2251799813685574`（仅记录）。与 done.md:382–390 表逐格相同。测试日志自身：`ok=17525 / FAIL=0`、`T4_LABEL_MIGRATION` 行 4632，与 done.md 一致。 |

### 2.3 四个 mixed 样例的独立重放对照（S=10·2^90，全部同日精确顺序）

| 样例 | 边表 | 测试断言值 | 我的独立重放值 | 一致 |
|---|---|---|---|---|
| T4-mixed | `X→A 2^60`,`X→A 1`,`A→D 2^60` | 主构成 Σ 703=2^60、704=2^60+1；策略差 fifo 0、其余 +1 | Σ=[1152921504606846976, 1152921504606846977]；policy Σ fifo 两版同、pro_rata/lifo 704 多 1 | ✅ |
| T4-mixed-b | `X→A 2^60`,`X→A 129`,`A→D 2^60` | 主构成 Σ 703=2^60、704=2^60−128；Δ pro_rata −128 / fifo 0 / lifo +1 | Σ=[…976, …848]；合桶 Δ current+peak 均 pro_rata −128、fifo 0、lifo +1 | ✅ |
| T4-mixed-c（反例 A） | `X→A H`,`Z→A H`,`X→A 257`,`A→D H`（H=2^60） | mint raw 576460752303423488 → 576460752303423360；Σraw H+128 → H−128；末笔 pro_rata 短缺 0→0；Δ pro_rata −128 / fifo 0 / lifo 0 | 全部逐值相同；`stock_raw` 两版均 1152921504606846976 | ✅ |
| T4-mixed-d（反例 B） | 同上前三笔，第四笔 `A→D 2H+512` | mint 两版同 1152921504606846976；Σraw 2305843009213694720 → 2305843009213694209；末笔 pro_rata 短缺 512→0；Δ pro_rata −511 / fifo 0 / lifo +1 | 全部逐值相同；`stock_raw` 两版均 2305843009213694464 | ✅ |

## 3. 新构造的对抗样例（本轮自行设计，两版内存重放）

判界口径：`B = 4·n·2^-52·S + 2`（n=边数，S=total_supply raw），检查 `stock_raw` 精确、①非 UNRESOLVED 逐键、②gap/residual 合桶、③Σraw、④逐笔短缺（`float.hex` 原值）、闭合 pct 与展示 pct 全部 ≤ 界。

### 3.1 定向设计的六例

| # | 名称 / 设计意图 | 边表（ts 用天序，Z=零地址=mint） | n | B | 两版结果 | 违反项 |
|---|---|---|---:|---:|---|---|
| N1 | 多层中间账户 A→B→C→D，每层混 mint 与外部转入＋极小额 | `X→A 2^80`,`Z→A 3`,`A→B 2^80−1`,`Z→B 7`,`B→C 2^79+5`,`X→C 2^40`,`C→D 2^79`,`C→D 2^40+11` | 8 | 8.80e13 | `stock_raw` 两版同 `604462909808414098980875`；事件 gap 3→1、fp_residual 2；max\|Δ\| 合桶 11 / Σraw 11 / 逐笔短缺 2 / 非 UNRESOLVED 0 | **无** |
| N2 | 500 笔 2^36 小额累加后一次性全额转出（裁决所述"累加噪声"场景） | `X→A 2^36` ×500，`A→D 500·2^36` | 501 | 5.51e15 | 500 次假 gap 全数迁为 fp_residual（gap 500→0、residual 500）；所有 Δ 均为 0 | **无** |
| N3 | 极小与极大金额并存＋连续多次超余额转出 | `X→A 2^62`,`Z→A 1`,`Y→A 4095`,`A→D 2^62+10^6`,`A→D 12345`,`A→D 2^55` | 6 | 6.60e13 | `stock_raw` 两版同；gap 5→2、fp_residual 3；max\|Δ\| 合桶 56 / Σraw 56 | **无** |
| N4 | FIFO/LIFO 七层非整除分层，多次按 1/3 扣减 | `X→A 3^20+i`（i=0..6），`A→D (7·3^20+21)/3` ×3 | 10 | 1.10e14 | gap 7→0、fp_residual 7；所有 Δ 均为 0 | **无** |
| N5 | 小供应量（S=10^6，`gap_eps` 退化为 EPS），应逐字不变 | `X→A 1000`,`Z→A 1`,`A→D 1500`,`X→A 7`,`A→D 3` | 5 | 2.000000004 | gap 3→3、`fp_residual_events=0`；所有 Δ 均为 0，行为与 7.0.3 逐字一致 | **无** |
| N6 | mint 与外部转入混于中间账户，三次连续短缺累加 | `Z→A 2^61`,`X→A 2^61`,`Y→A 257`,`A→D 2^61+1` ×3 | 6 | 6.60e13 | `stock_raw` 两版同；gap 3→2、fp_residual 1；max\|Δ\| 合桶 257 / Σraw 257 | **无** |

### 3.2 随机对抗搜索（六例之外的补充，两批共 1200 组）

| 批次 | 参数域 | 组数 | 违反数 | 结论 |
|---|---|---:|---:|---|
| 甲・宽域（含非物理输入） | 5 档 S×金额组合，金额可远超总供应 | 600 | 61 | 仅 `S=2e16、单笔金额 2^62` 一档出现；见 nit N4 |
| 乙・物理域（每笔 ≤ S 且中间账户累计流入 ≤ S） | S∈{10·2^90, 2e16, 2^64}，n≤30 | 600 | **0** | 最紧比值 `max\|Δ\|/B = 0.043`（约 23 倍余量），裁决各项承诺全部成立 |

**结论：在链上可能出现的输入域内（单笔转账不超过总供应），我构造的 6 个定向样例 + 600 组物理域随机样例，`stock_raw` 全部精确相同，①②③④与 pct 的界一条未被违反。无 blocker。**

## 4. 文档措辞与消费面

| 子项 | 判定 | 依据 |
|---|---|---|
| 4.1 CHANGELOG 7.0.4 详细段 | **PASS** | `sed -n '/^## \[7.0.4\]/,/^## \[7.0.3\]/p' CHANGELOG.md`。"设计与实现"栏逐句复述裁决：唯一精确=`stock_raw`、B 定义、①②③④判界、原始标签只记录、pct 界与展示值不承诺、Δ 可正可负、计数/policy_details/指纹不承诺、"两版都是浮点近似无优劣"。**无"四项精确/更接近真值/上界=fp_residual"残留。** |
| 4.2 scan-schemas §4 | **PASS** | `git diff HEAD -- references/scan-schemas.md`。§4 追加段与裁决逐项对应，另补零库存锚点不除零、账户阈值不放大的三反例、极端累加残留声明。枚举、诊断块、`algorithm` 三处结构登记同步。 |
| 4.3 done.md 承诺措辞 | **PASS**（附 nit N2） | 置顶 r4b 范围块（done.md:3）即裁决原文范围；r4 的 684 次"超界"明标为历史标签迁移。 |
| 4.4 CHANGELOG 索引行 | **MINOR M1** | `CHANGELOG.md:13`：「…每笔短缺数量原样保留、账户 EPS 不变…」。本意应是"短缺数量入桶不丢弃"（与"丢弃"方案对比），但字面可读成"逐笔短缺值不变"——**这正是被 T4-mixed-d 反证的说法**（同一提交内实测 512→0）。详细段与 scan-schemas 都写对了，唯独索引行缺后半句。 |
| 4.5 消费面表述准确性 | **PASS** | CHANGELOG:94 称"APU 实测 118/210，全部含旧 data_gap"。我从两份 APU 账本独立复算：210 锚点中 `policy_details` 实际变化 **118** 个，且这 118 个旧版明细**全部**含 `data_gap` 条目，数字与限定语完全准确。"旧账本整体 freeze 重放与 `--check-unseal` 另因算法文件哈希漂移被拒，与收据是否匹配无关"、"'已封存不动'只指不重写文件"表述准确，与 plan D4 [CX] 条一致。 |

## 5. APU / PYTHIA 224 锚点与 `.staging_eps` 四份账本

**PASS。** 我不复用 `ledger_recheck_r4.json`，直接从四份账本独立复算（只读）：

- 账本：`.staging_eps/apu/provenance_ledger.json`（703）、`.staging_eps/apu/provenance_ledger_704.json`、`.staging_eps/pythia/t7_compare/ledger_703.json`、`…/ledger_704.json`。
- 规模复算：APU 105 实体×2 = **210 锚点**，PYTHIA 7 实体×2 = **14 锚点**，合计 **224 锚点 / 666 组策略明细** —— 与 apu_regression.md、pythia_regression.md、CHANGELOG、done.md 的数字一致。
- 全量判定：224 锚点 × （主构成 + 全部策略明细）中，`stock_raw` 全部相同；**非 UNRESOLVED 逐键、gap/residual 合桶量、Σraw 的非零差条目数 = 0**，与两份回归文件"均为 0"的表述一致。

抽查锚点（≥5 个，含指定项）：

| 案 / 实体 / 锚点 | 回归文件所记 | 我的独立复算 | 一致 |
|---|---|---|---|
| APU TE-01 / current | gap 条目 1→0、residual 1、事件 4230→0、residual 事件 4230 | 同；`stock_raw` 两版同 `22465321377829021579209679895`，Σraw 两版同 | ✅ |
| APU TE-01 / peak | 0→0、0、4230→0、4230 | 同；`stock_raw` 两版同 `46779970652625432626847270566` | ✅ |
| APU TE-03 / current | 1→0、1、4015→0、4015 | 同；`stock_raw` 两版同 `12692416205350410074923624134` | ✅ |
| APU TE-03 / peak | 1→0、1、4015→0、4015 | 同 | ✅ |
| PYTHIA e_lp（事件） | `data_gap_events` 11145→3、`fp_residual_events` 0→11139 | 同 | ✅ |
| PYTHIA e_h9 / current | stock 12061341704660、Σraw 12061341704654（两版同值） | 同 | ✅ |
| PYTHIA e_dev / current、peak | 0/0 与 64393693625888（两版同值） | 同 | ✅ |

## 6. 白名单与受保护件

| 子项 | 判定 | 依据 |
|---|---|---|
| 6.1 白名单外无改动 | **PASS** | `git status --porcelain` + `git diff HEAD --stat`：仅 7 个已跟踪文件被改——`CHANGELOG.md`、`SKILL.md`、`VERSION`、`pyproject.toml`、`references/scan-schemas.md`、`scripts/report/entity_source_trace.py`、`scripts/tests/test_entity_source_trace.py`，全部在白名单内。新增未跟踪文件全部落在 `maintenance/repair-20260915-eps-residual/`。`SKILL.md` 只改 1 行版本注释；`VERSION` 7.0.3→7.0.4；`pyproject.toml` 7.0.2→7.0.4（补 7.0.3 遗漏，plan D4 授权）。`.staging_eps/` 由 `.gitignore:24` 的 `.staging_*/` 预先覆盖，非本轮新增忽略规则。 |
| 6.2 受保护文件与 HEAD 相同 | **PASS** | 逐文件 `git show HEAD:<f> \| shasum -a 256` 与 `shasum -a 256 <f>` 对照，六项全部逐字节相同：`scripts/report/handoff_manifest.py`、`scripts/tests/test_sqd_gap_repair.py`、`scripts/tests/test_handoff_manifest.py`、`scripts/tests/fixtures/pythia_anchors.json`、`scripts/tests/invariant_manifest.json`、`scripts/tests/run_all.py`。 |
| 6.3 既有测试断言一条未删 | **PASS** | `git diff HEAD -- scripts/tests/test_entity_source_trace.py \| grep "^-" \| grep -v "^---"` 输出为空。纯追加，无改写、无删除。 |

## 7. `_r4b` 七项日志退出码与 done.md 表

**PASS。** 复现：`python3 -c` 读 `check_results_r4b.json`，对每项重算日志 SHA-256 并与记录比对。

| 命令 | done.md 记录 | 日志实测 | 日志 SHA-256 核验 |
|---|---:|---|---|
| `test_entity_source_trace.py` | 0 | `PASS：0 项失败`（ok 17525 / FAIL 0） | ✅ 一致 |
| `test_version_consistency.py` | 0 | `PASS: M-03 version metadata consistent at 7.0.4` | ✅ |
| `changelog_lint.py` | 0 | `PASS: 版本号唯一…活跃 71 条 + 归档 139 条` | ✅ |
| `docs_lint.py --all` | 0 | `PASS: 59 个文档，引用无断链…` | ✅ |
| `invariant_scan.py` | 0 | `PASS invariant manifest: … exceptions=0` | ✅ |
| `fixtures_lint.py` | 0 | `fixtures_lint PASS：pythia_anchors.json 结构完整` | ✅ |
| `git diff --check` | 0 | 空输出（`e3b0c442…` 空文件哈希） | ✅ |

`check_results_r4b.json` 内登记的四个被测文件 SHA-256（生产文件、测试文件、CHANGELOG、scan-schemas）与当前工作树逐一复算相同 —— 七项确实跑在当前终态代码上。

---

## 问题清单

| 编号 | 级别 | 位置 | 问题 | 只读复现 / 建议 |
|---|---|---|---|---|
| M1 | minor | `CHANGELOG.md:13` | 索引行「每笔短缺数量原样保留」字面等同被 r3 反证的"逐笔短缺不变"；同一提交的 T4-mixed-d 实测 512→0 直接反例。详细段与 scan-schemas 写法正确，仅索引行缺限定。 | `sed -n '13p' CHANGELOG.md`。建议改为「每笔短缺数量入桶不丢弃（两版短缺值本身可在 B 界内变化）」。 |
| M2 | minor | `scripts/tests/test_entity_source_trace.py:564-672` | T4-stress 的 `\|Δ\|≤B` 断言近乎空转：S=10·2^90≈1.24e28，而金额上限仅 2^62≈4.6e18，B≈8.8e13 而实测 max\|Δ\|=1536，**余量约 1e11 倍**。该压力测试有效证明的是 `stock_raw` 精确与标签迁移规模，对"界"本身几乎没有鉴别力。 | 见 §2.4 日志命令。建议补一档 S 与边金额同量级的样本（我的物理域 fuzz 最紧比值降到 0.043 仍全过，说明界确实成立，但应由测试自己证明）。 |
| M3 | minor | `scripts/tests/test_entity_source_trace.py:274-283` | 比较器把**所有** `UNRESOLVED` 键都跳过判界，`order_ambiguous`/`depth_limit`/`budget_truncated`/`facility_candidate` 因此既不入①也不入②，退化为"仅记录"。字面符合裁决勘误（②只定义为 gap+residual 合桶），但留下覆盖洞：这些子类上的回归会被静默记成"标签迁移"。 | `sed -n '274,287p' scripts/tests/test_entity_source_trace.py`。建议把"除 gap/residual 外的 UNRESOLVED 键"并入①逐键判界。 |
| N1 | nit | `entity_source_trace.py:3,92` | 冻结的生产文件 docstring/注释仍写"数量不变""数量原样保留,只改标签"。**已在 `CHANGELOG.md:94` 与 `done.md:123` 明列为已知未修**，原因是裁决冻结 SHA 不许改。属裁决自身的取舍，非施工缺陷。 | `sed -n '3p;92p' scripts/report/entity_source_trace.py` |
| N2 | nit | `done.md:7` | 置顶前言仍写"T6 数量不变量通过"，是 r2 轮措辞残留；紧邻的 done.md:3 已给出 r4b 有效范围，读者不至误解，但建议同步为"有界差分"。 | `sed -n '7p' maintenance/repair-20260915-eps-residual/done.md` |
| N3 | nit | `pythia_regression.md:69` | e_lp 行「11145 → 3 / 0 → 11139」：3+11139=11142≠11145，表面像账不平。实为"事件计数不承诺不变"的正常表现（边界短缺在拆桶后落到 EPS 以下即不再产生事件），但表内无脚注。 | `sed -n '69p' maintenance/repair-20260915-eps-residual/pythia_regression.md`。建议加一行"计数差属不承诺项"。 |
| N4 | nit（信息项） | `r3_fix_ruling.md` / CHANGELOG / scan-schemas | B 被写成无条件式，实际隐含"单笔金额 ≤ 总供应"的域假设。我在甲批宽域搜索里构造出反例：S=2e16，边表 `Y→A 181`、`X→B 2^62`、`Z→B 2^51`、`Z→B 901`、`A→D 4613937818241075551`，n=5 时 B=90.82 而合桶与 Σraw 的 Δ=181 —— **超界**。触发条件是单笔金额约为总供应的 230 倍（阈值约 114 倍），链上不可能出现，故不判 blocker。 | 见 §3.2 甲批。建议在 scan-schemas §4 的 B 段补一句"以边金额不超过 total_supply 为前提"。 |

**开放项（非缺陷，留给验收方）**：全套 `run_all.py` 尚未在 r4b 终态代码上复跑——`run_all_fable_r4b.log` 当前 0 字节。裁决原文已把这一步指派给 Fable 本机（"全套 run_all 由 Fable 本机复跑落盘"），施工侧不算欠账；但 commit 前应补齐，确认 SUITE 仍 147 项且全绿。

---

**总结论：本轮施工与最终裁决一致——生产文件哈希与改动范围、测试比较器与四个具体样例、300 组压力测试、224 锚点回归、白名单与受保护件、七项退出码全部核对通过；自构的 6 个定向对抗样例与 600 组物理域随机样例未发现任何承诺被违反。blocker 0 项，3 项 minor 与 4 项 nit 均为文档措辞与测试鉴别力问题，不阻断合入。盲审 R4（opus）判定 PASS。**
