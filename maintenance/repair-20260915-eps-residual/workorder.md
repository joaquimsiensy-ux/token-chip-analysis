# 工单:溯源假 data_gap 改判为浮点残差(7.0.3 → 7.0.4)repair-20260915-eps-residual

基线:`main = 3b29e38`(7.0.3 逻辑 + agents/openai.yaml)。本工单已经 Fable 设计 + codex 只读复核融合(v1→v2 四反例复算)+ 用户审批(2026-09-15)。施工方按本单逐条执行,**先红后绿**,完工**不 commit**(Fable 验收后代 commit)。

## 0. 开工纪律

- 工作目录即本仓库物理路径 `/Users/uravvv/.claude/skills/token-chip-analysis`。开工先 `git status --short`,除本目录 `maintenance/repair-20260915-eps-residual/` 外须为空;`git rev-parse HEAD` 须为 3b29e38 的后继(工单已 commit)。
- 行号旁附锚文本;若行号与锚文本不一致,**停工**写 `done_attempt1_stopped.md` 汇报,不得自行猜改。
- **禁止**读取 `/Users/uravvv/.codex/skills/_archive/` 与 git tag `codex-frozen-20260915` 下任何实现;禁止参考 `maintenance/repair-20260915-provenance-exact-arith/`(那是另一条根治路线,本单不采用)。
- 离线完成,无网络调用;不 `git fetch`;**不改** `scripts/report/handoff_manifest.py`、`scripts/tests/test_sqd_gap_repair.py`、`scripts/tests/test_handoff_manifest.py` 的既有断言。
- **唯一逻辑改动点是 §1 A1**;其余全部是登记/文档/测试。账户类 `VectorAccount`/`LayeredAccount`、`EPS` 常量及其其余 9 处引用(第 264/267/296/302/307/554/569/576 行)**一字不改**。
- 全套 `run_all.py` 本机约 11 分钟,用 `nohup python3 scripts/tests/run_all.py > /tmp/run_all_eps.log 2>&1 &` 再等结果;禁止 `| tail`。
- RED 证据(`red_evidence.txt`)每段必含:准确命令、退出码、输出原文、测试文件 sha256、被测生产文件 sha256。

## 1. A 段:生产改动 `scripts/report/entity_source_trace.py`

### A1 缺口判定改判(唯一逻辑改动)
- `:89`(锚 `EPS = 1e-6`)之后新增:
  ```python
  # 缺口判定专用相对阈值:float64 在 1e29 量级 raw 上单步噪声约 1e13,绝对 EPS=1e-6 会把纯噪声
  # 记成"数据缺失"。低于 gap_eps 的账户短缺改记 UNRESOLVED/fp_residual(数量原样保留,只改标签);
  # 账户判等/扣减/入账仍用 EPS,不放大(放大会清空小额真实转账并新增 peak 拒收,2026-09-15 复算)。
  GAP_EPS_REL = 1e-13


  def gap_eps(total_supply):
      """max(EPS, total*1e-13):小供应量退化为 EPS,行为与 7.0.3 逐字一致。"""
      return max(EPS, float(int(total_supply)) * GAP_EPS_REL)
  ```
- `:406`(锚 `def simulate(edges_iter, Mset, ancestors, term_key, term_plen, policy, T_peak):`)签名改为 `..., T_peak, gap_eps=EPS):`(**带默认值**,`test_sqd_gap_repair.py:159/160/344/346` 直接调用 `entity.simulate()`,默认值保证其行为不变)。docstring 返回值说明补 `"fp_residual_events": int`。
- `:427`(锚 `gap_events = ambiguous_groups = ambiguous_events = n_edges = 0`)改为 `gap_events = residual_events = ambiguous_groups = ambiguous_events = n_edges = 0`;`flush_group` 内 `nonlocal` 行同步加 `residual_events`。
- `:465–468`(锚 `elif shortfall > EPS:` … `gap_events += 1`)改为:
  ```python
              elif shortfall > gap_eps:
                  gap_key = ("UNRESOLVED", "data_gap", None)
                  comp[gap_key] = comp.get(gap_key, 0.0) + shortfall
                  gap_events += 1
              elif shortfall > EPS:
                  # 浮点残差:噪声量级的短缺,数量保留、不代表链上数据缺失
                  res_key = ("UNRESOLVED", "fp_residual", None)
                  comp[res_key] = comp.get(res_key, 0.0) + shortfall
                  residual_events += 1
  ```
  注意 `gap_eps >= EPS` 恒成立,两分支互斥且 `shortfall <= EPS` 时与 7.0.3 一样不记账。
- `:487–488`(锚 `return {"peak": peak_snap, "current": snap(),` / `"gap_events": gap_events,`)返回字典加 `"fp_residual_events": residual_events`。
- `:549–550`(锚 `ev_map = {"mint": "onchain_pattern",` / `"data_gap": "onchain_pattern",`)加 `"fp_residual": "onchain_pattern"`。
- `:603`(锚 `runs[policy] = simulate(edges, Mset, ancestors, term_key, term_plen, policy, T_peak)`)改为 `..., T_peak, gap_eps=gap_eps(total))`(`total` 是 `trace_entity` 第 579 行签名参数)。
- `:665`(锚 `"data_gap_events": main["gap_events"]},`)改为 `"data_gap_events": main["gap_events"],` 换行 `"fp_residual_events": main["fp_residual_events"]},`。
- `:163`(锚 `"policies": list(POLICIES), "order_material_pct": ORDER_MATERIAL_PCT},`)改为 `..., "order_material_pct": ORDER_MATERIAL_PCT, "gap_eps_rel": GAP_EPS_REL},`。
- `:2` 模块 docstring 追加一句:"v7.0.4:低于 gap_eps(max(EPS, total·1e-13))的账户短缺记 UNRESOLVED/fp_residual,不再冒充 data_gap;数量不变。"

### A2 明确不做
不改 `EPS` 值与其余引用;不改 `unresolved_total`(第 826–828 行,fp_residual 属 UNRESOLVED 如实计入);不改闭合检查(第 ~806 行 0.5%);不改 7.0.3 尘埃降级;不改 schema(仍 `provenance-ledger/v2`);不处理 `int(float)` 截断为 `"raw":"0"` 的既有现象(记 CHANGELOG"已知未修")。

### A3 RED(改 A1 前先跑,证据入 red_evidence.txt)
T1 三笔边表(见 §3)在 7.0.3 代码下跑正式 trace:`simulation.data_gap_events == 1`、构成含 `subkind == "data_gap"` raw "1";记录三策略 `policy_details`。这是 RED。

## 2. B 段:登记面与文档

- `VERSION`:`7.0.4`。
- `pyproject.toml:15`(锚 `version = "7.0.2"`,**7.0.3 漏改**)→ `"7.0.4"`。
- `SKILL.md:23`(锚 `skill-version: 7.0.3`)→ `7.0.4`。
- `CHANGELOG.md`:
  - `:13`(锚 `- **7.0.3**（2026-09-15）`)之前插入 7.0.4 索引行(一行,格式同列)。
  - `:88`(锚 `## [7.0.2] - 2026-09-06`)之前插入 **两段**详细段,顺序 `## [7.0.4]` 在上、`## [7.0.3]` 在下(7.0.3 详细段此前缺失,`test_version_consistency.py:20` 要求首个详细段标题 == VERSION)。六栏格式照 7.0.2:出处与根因/设计与实现/消费面与防回流/测试/盲审与验收/成本-质量指标。出处只写"APU 案触发的工具故障",**禁写任何代币分析结论**。7.0.3 段按其提交 f0036f8 内容如实补写(尘埃 current 降级、freeze 同步豁免、四组回归),并注明"pyproject/详细段漏改由 7.0.4 补齐"。7.0.4 消费面须写:算法文件哈希变化 → 旧账本 freeze 重放与 `--check-unseal` 会拒;"已封存不动"只指不重写文件;极端累加序列的假缺口仍可能超过 gap_eps 记成 data_gap(浮点根因未除的残留)。
- `references/scan-schemas.md`:
  - `:251`(锚 `"policies": [str…], "order_material_pct": float},`)→ 加 `"gap_eps_rel": float`。
  - `:285`(锚 `"data_gap_events": int}   # 诊断块`)→ 加 `"fp_residual_events": int`。
  - `:307`(锚 `# UNRESOLVED: data_gap|depth_limit|budget_truncated|facility_candidate|order_ambiguous`)→ 枚举加 `fp_residual`。
  - §4 末尾追加一段(≤10 行):gap_eps 定义与量级依据(APU 实测最大假 gap 1.1e-18 倍供应、理论 7e-17、阈值 1e-13)、fp_residual 语义("浮点噪声量级的账户短缺,数量保留、不代表链上数据缺失")、账户阈值为何不放大(三反例一句话)、残留声明。
- `scripts/tests/invariant_manifest.json` 预计不动;若 `invariant_scan.py` 报差异,先判断是否误改登记面,确认确实变化才登记并在 done.md 说明。

## 3. C 段:测试 `scripts/tests/test_entity_source_trace.py`(沿现有 `check()` 风格在 `main()` 前追加函数并在 `main()` 首部调用;不改任何既有断言)

fixture 约定沿该文件既有 `write_edges`/`run_trace`/`day()`/`Z`;T1/T2 边表须**同天且带精确顺序位置**(参照 `dust_precision_edges` 的写法,若既有 helper 不支持精确序号则按 `fetch_sim_edges` 的排序列自行构造)。

- **T1 假 gap 改判(主证据)**:总供应 `10 * 2**90`;三笔:`Z→X 2**90`、`X→D 2**90-1`、`X→D 1`;实体 `{"D": ["D"]}`。断言:`exit 0`;`simulation.data_gap_events == 0`;`simulation.fp_residual_events == 1`;current 与 peak 构成各含一条 `kind=="UNRESOLVED", subkind=="fp_residual", raw=="1"`;无 `subkind=="data_gap"` 条目;两锚点 `stock_raw == str(2**90)`;mint 条目 raw 与 RED 记录相同;`closure_check` 两 Σ 与 RED 相同。
- **T2 真缺口仍报**:①总供应 `10**6`:`X→D 100`(X 无入账)→ `data_gap` raw "100"、`data_gap_events == 1`、`fp_residual_events == 0`;②总供应 `10 * 2**90`:`X→D 2**60` → `data_gap` raw `str(2**60)`、`data_gap_events == 1`。
- **T3 小供应逐字不变**:`import entity_source_trace as m`(该文件已有的 import 方式,若无则按 `test_reconcile_v4_receipt.py:27` 方式)断言 `m.gap_eps(10**4) == m.gap_eps(10**6) == m.EPS`;`m.gap_eps(10 * 2**90) == 10 * 2**90 * 1e-13`(允许浮点相等比较用 `math.isclose`)。另:对既有 `dust_precision_edges(nonempty=True)` 案例,用 7.0.3 代码(`git show 3b29e38:scripts/report/entity_source_trace.py > /tmp/trace_703.py`,以相同参数跑)与 7.0.4 各跑一次,断言三策略 `sensitivity.anchors.*.policy_details` 逐条相同、`data_gap_events` 相同。
- **T4 数量不变性**:对 T1 边表与一个多来源反复扣减边表(`Z→A 2**90`、`Z→B 2**90`、`A→D 2**89`、`B→D 2**89`、`D→OUT 2**88` ×4、`A→D 1`、`B→D 1`),7.0.3(`/tmp/trace_703.py`)与 7.0.4 各跑,断言每实体每锚点:`stock_raw` 相同;`Σraw` 相同;除 `data_gap`/`fp_residual` 两键外每条构成 raw 相同;`data_gap_raw(7.0.3) == data_gap_raw(7.0.4) + fp_residual_raw(7.0.4)`。
- **T5 登记**:账本 `input_binding.algorithm.gap_eps_rel == 1e-13`;`simulation` 含 `fp_residual_events` 键。
- **T6 APU 真实回归**(离线;不进测试文件,结果落 `apu_regression.md`):把 `/Users/uravvv/Documents/5.6筹码分析/APU分析_20260914` 的 `handoff_manifest.json`、`data_map.json`(如有)、`data/v2/`、实体文件、标签文件、`provenance_ledger.json` 所引用的收据,**复制**到本仓库 `.staging_eps/apu/`(保持相对布局;`git status` 已忽略 `.staging_*`,若未忽略则加入 `.git/info/exclude`,不改 `.gitignore`);用 `provenance_ledger.json` 的 `input_binding.algorithm_params`/`params` 还原命令行参数,在副本上跑 7.0.4 trace 输出到副本;与案卷 `provenance_ledger.json`(7.0.3)对比:按实体×锚点×`(kind,subkind,via)` 对齐,T4 不变量对 105 实体全部成立;记录 `data_gap` 条目 105 → x、`fp_residual` 条目 y、逐实体两计数;TE-02/TE-04 的 `current_negligible_skipped`/`composition_usable` 如实记录是否仍在;`policy_details` 逐来源 raw 差分(预期仅 gap 相关键变化);翻转指纹(`handoff_manifest.flip_fingerprint`)逐锚点是否变化。**不写回案卷,不改案卷任何文件。**若 APU 案根有 macOS TCC 读取限制(Operation not permitted),停工汇报,由 Fable 搬入 staging。
- **T7 PYTHIA 对表**(`scripts/tests/fixtures/pythia_anchors.json` 约定):库 `/Users/uravvv/Documents/5.6筹码分析/PYTHIA分析/s2_work.duckdb`(444MB,只读 ATTACH),`total_supply_raw` 见该文件;按 `provenance_v2.run_params` 重跑 trace 到 `.staging_eps/pythia/`;与 `q1_peak_anchor`/`3ymk_peak_anchor`/`closure`/`sensitivity_stable` 逐项比对,数量类锚点须相等;`_note_v2` 已声明该基线是历史诊断(5 元组缺精确序),故 `data_gap_events` 若因本单改判而变化,按 T4 不变量(`data_gap + fp_residual == 旧 data_gap`)比对并**人工更新**该 json(每项旧值/新值/原因写入 done.md),`fixtures_lint.py` 绿。结果落 `pythia_regression.md`。同样 TCC 限制则停工汇报。
- **T8 freeze 重放**:复用 `scripts/tests/test_handoff_manifest.py:293` 附近的完整案根搭建流程(manifest、data_map、成员、裁决材料)——**在 `test_entity_source_trace.py` 内以 subprocess 调 `handoff_manifest.py freeze`**,不改 `test_handoff_manifest.py`;对 T1 边表:新代码 trace → freeze `exit 0`;用 7.0.3 代码生成的账本放入同一案根 → freeze 拒(stderr 含"算法哈希已变化")。若搭建流程无法在不改 `test_handoff_manifest.py` 的前提下复用,把 T8 写成独立新文件 `scripts/tests/test_eps_residual_freeze.py` 并登记 `run_all.py` SUITE(+1)。
- **T9**:`test_version_consistency.py` 绿;`run_all.py` 全绿。

### C-RED
A1 前用 T1 边表跑 7.0.3:`data_gap_events == 1`;T2①同样在 7.0.3 下也是 `data_gap` raw 100(证明 T2 不是本单引入的行为)。

## 4. 完工标准与产物

- `red_evidence.txt`:A3/C-RED。
- `apu_regression.md`、`pythia_regression.md`:只记数字与差分,不记任何代币结论。
- `done.md`:五节(改动清单含每文件 diff 行数/与工单差异/RED→GREEN/命令与结果表逐行列 `changelog_lint.py`、`docs_lint.py --all`、`test_version_consistency.py`、`invariant_scan.py`、`fixtures_lint.py`、`test_entity_source_trace.py`、`run_all.py` 实际结果/已知未修)。
- 白名单(超出即违规):`scripts/report/entity_source_trace.py`、`scripts/tests/test_entity_source_trace.py`、`scripts/tests/test_eps_residual_freeze.py`(仅 T8 备选)、`scripts/tests/run_all.py`(仅 T8 备选 SUITE +1)、`scripts/tests/fixtures/pythia_anchors.json`(仅 T7 人工更新)、`scripts/tests/invariant_manifest.json`(仅当扫描要求)、`references/scan-schemas.md`、`CHANGELOG.md`、`VERSION`、`pyproject.toml`、`SKILL.md`(仅 :23)、本目录、`.staging_eps/`(不入 commit)。
- 全绿后停,**不 commit**。任何一项做不到,写清做不到的原因与已完成部分,不得降低断言凑绿。
