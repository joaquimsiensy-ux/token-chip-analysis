# 工单:main 三缺陷独立修复(7.0.1 → 7.0.2)repair-20260906-main-threefix

基线:`main = f27d3d2`(7.0.1,已 push)。本工单已经 Fable 设计 + codex 只读复核融合 + 用户审批。施工方按本单逐条执行,**先红后绿**,完工**不 commit**(Fable 验收后代 commit)。

## 0. 开工纪律

- 工作目录即本仓库物理路径。开工先 `git status --short`,除本目录 `maintenance/repair-20260906-main-threefix/` 外须为空;`git rev-parse HEAD` 须为 f27d3d2 的后继(工单已 commit)。
- **禁止**读取或参考 `/Users/uravvv/.codex/skills/token-chip-analysis` 下任何文件(codex 分支实现),本单要求独立实现。
- 行号旁附锚文本;若行号与锚文本不一致,**停工**写 `done_attempt1_stopped.md` 汇报,不得自行猜改。
- 离线完成,无网络调用;不 `git fetch`;不改 `build_html.py`、不改 `producer_history.py` 的 REVOKED 规则、不动 `test_repair_batch_d.py`。
- 施工顺序 A → C → B。每段先跑 RED 再改生产代码。
- RED 证据(`red_evidence.txt`)每段必含:准确命令、退出码、输出原文、测试文件 sha256、被测生产文件 sha256。
- 全套 `run_all.py` 本机约 11 分钟,施工方跑用 `nohup python3 scripts/tests/run_all.py > /tmp/run_all.log 2>&1 &` 再等结果;禁止 `| tail`。

## 1. A 段:补登记 + 登记守卫测试

### A1 生产改动(唯一):`scripts/lib/producer_history.py`
在 `:202`(锚 `    },`,sqd_gap_repair 第 12 条结束)之后、`:203`(锚 `    {` 紧接 `:204 "script": "scripts/solana/window_fetch.py"`)之前,追加 4 条字典,四协议各一:
```
script:   scripts/solana/sqd_gap_repair.py
sha256:   25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66
commit:   4c5cd578a5f1a10449d128dcdb91a724c359e7a5
protocol: 依次 sqd-solana-cache/v4 / sqd-solana-repair-bundle/v1 / sqd-solana-coverage-resolution/v1 / sqd-solana-repair-pointer/v1
status:   ACTIVE
reason:   "v7.0.2 registers the v6.52.7 batch-9 producer (verify-CLI local `_base` renamed to `_base_payload` in `_verify`; <协议名> output semantics unchanged)."
```
施工前自行验证:`git show 4c5cd578a5f1a10449d128dcdb91a724c359e7a5:scripts/solana/sqd_gap_repair.py | shasum -a 256` 与 `shasum -a 256 scripts/solana/sqd_gap_repair.py` 均为 25f04ff…。

### A2 新增守卫测试:`scripts/tests/test_producer_registry_current.py`(新文件)
风格沿 `scripts/tests/test_a4_gate.py`(单 `main()` + check 断言器,失败 exit 1)。不 mock 登记表。两组断言:

(1) **当前哈希已登记**。定义:
```python
CURRENT_PRODUCERS = {
    "scripts/solana/sqd_gap_repair.py": {"sqd-solana-cache/v4", "sqd-solana-repair-bundle/v1",
                                         "sqd-solana-coverage-resolution/v1", "sqd-solana-repair-pointer/v1"},
    "scripts/solana/fetch_sqd_transfers_v2.py": {"sqd-solana-cache/v4"},
    "scripts/solana/sqd_coverage_probe.py": {"sqd-solana-coverage/v1", "sqd-solana-coverage-pointer/v1"},
    "scripts/solana/window_fetch.py": {"solana-window-fetch-receipt/v3"},
}
HISTORICAL_ONLY = {("scripts/lib/anchor_plan.py", "anchor-plan/v2")}
```
- 对每个脚本:从 `PRODUCER_HISTORY` 动态收集该脚本出现过的 protocol 集合 `found`;断言 `found` 非空且 `CURRENT_PRODUCERS[script] <= found`(必要协议在场);对 `found` 中每个 protocol 断言工作树 sha256 ∈ `historical_producer_hashes(script, protocol)`。
- `HISTORICAL_ONLY` 豁免并在注释写明理由:`receipt_validate.validate_receipt` 默认路径(`scripts/lib/receipt_validate.py:115-116`,锚 `current_hash = _hash_file(producer_path)`)以当前文件哈希为允许集,登记表两条只是历史 `anchor-plan/v2`;`test_anchor_plan_v3.py:376-377` 断言当前哈希被接受(函数返回错误列表,`assert not` 即无错误)。豁免只限该 (script, protocol) 对。
- 断言登记表里出现的脚本集合 == `CURRENT_PRODUCERS` 键集 ∪ `HISTORICAL_ONLY` 脚本集(新脚本进登记表必须同步本测试)。
- 失败文案点名:"改了生产者文件必须同步登记 scripts/lib/producer_history.py(git show <commit>:<script> 可复现的哈希)"。

(2) **登记纪律 git 可复现**。遍历 `PRODUCER_HISTORY` 每条:
- `subprocess.run(["git", "show", f"{commit}:{script}"], cwd=REPO_ROOT, capture_output=True)`;先检查 `returncode`,再对 `stdout` 字节算 sha256;禁止 `shell=True`/管道。
- 退出码非 0 → FAIL 文案"git 对象不可用(需要完整 git 仓库,浅克隆或源码包不满足): <commit>:<script>";哈希不等 → FAIL 文案"登记与 git 历史不符: <script> <commit> 登记 <sha> 实得 <sha>"。两类都是 FAIL,不得 skip。
- 同一 `(commit, script)` 只调 git 一次(缓存),但逐条验证。
- 测试不得 fetch、不得写文件。

`scripts/tests/run_all.py`:在 `:204`(锚 `SUITE += ['test_batch18_review_digest.py']`)之后追加:
```python
# repair-20260906-main-threefix：生产者当前哈希必登记 + 登记 git 可复现守卫。
SUITE += ['test_producer_registry_current.py']
```
分母 146 → 147。

### A3 不动
`test_sqd_gap_repair.py:314-325`、`test_batch18_review_digest.py:97-105` 的 monkeypatch 本轮不动;done.md 遗留栏登记。

### A4 RED
改 A1 前跑 A2 测试:必红,输出含 `sqd_gap_repair.py`、`25f04ff1` 与四协议名。

## 2. C 段:A4 封口端硬拒重复路径

### C1 生产改动(唯一):`scripts/report/a4_gate.py` `cmd_finalize`(`:333` 锚 `def cmd_finalize(a):`)
在 `:408`(锚 `        verdict_rel = None`)之后、`:410`(锚 `    charts_dir = a.charts_dir`)之前插入:
```python
    reserved = {CLAIMS_NAME, verdict_rel} - {None}
    dup = sorted(reserved & seal_files)
    if dup:
        fails.append(f"封口清单与 registry/verdicts 专用字段路径重复: {dup}"
                     f"——请从 --seal-files 或 claim files 中移除,裁决与登记表由专用字段单独封口")
```
`seal_files` 来自 `:386-393`(锚 `seal_files = {x.strip()` … `seal_files |= claim_files`),已含三来源;走 `:425`(锚 `    if fails:`)既有出口 exit 2。不做路径归一化重构。`build_html.py` G9、`distribution_explanation_check._sealed_paths()` 均不动。

### C2 测试:`scripts/tests/test_a4_gate.py`
在 `:423`(锚 `os.unlink(os.path.join(d, "charts", "final", "premature.png"))`)之后、`:425`(锚 `# 4. finalize 正例`)之前新增。**每个负例用独立临时案目录**(可写一个辅助函数复制当前 `d` 到 `tempfile.mkdtemp()` 子目录;不得在 `d` 上直接跑负例后依赖"失败不写 seal"来保持 `d` 干净——除非该负例确实不产 seal 且不改 `d` 任何文件,claim files 情形需要改 `a4_claims.json`,必须在副本上做)。四种交叉情形,均断言 `returncode == 2`、stderr 含"重复"、`a4_seal.json` 不存在:
1. `--seal-files findings.md,analysis-state.json,v_ok.json` + `--verdicts-file <v_ok.json>`;stderr 还须含 `v_ok.json`;
2. `--seal-files findings.md,analysis-state.json,a4_claims.json`;stderr 还须含 `a4_claims.json`;
3. 副本里改 `a4_claims.json` 某 claim 的 `files` 加 `v_ok.json`,正常参数 → exit 2;
4. 副本里改 `files` 加 `a4_claims.json` → exit 2。
5. 另加一例:在正例(`:425-430`)成功产 seal **之后**,对 `d` 再跑情形 1 参数 → exit 2 且 `a4_seal.json` 字节与正例后完全相同(失败不覆盖也不删旧 seal);跑完立即确认 `d` 状态未变,不影响后续既有 check。
- 既有 check 全部保留、断言不改;脚本末尾"23 项"字样不动(遗留登记)。

### C3 RED
改 C1 前:在 `d` 的副本上跑情形 1 命令 → 记录 exit 0 且 `a4_seal.json` 写出;紧接对该副本跑 `build_html.py --mode analysis-audit`(该夹具由 `run()` 自动补 `--workflow-type independent-audit`,走审计轨;参数照抄 test_a4_gate 既有 G9 正例的 build_html 调用)→ 输出含"封口路径重复"。两段原文入 red_evidence.txt。

## 3. B 段:图一豁免集按生产器格式派生

### B1 生产改动

**`scripts/report/standard_charts.py`**
- `:59`(锚 `FIG1_EXCLUDED_SERIES = {"burn_cum_pct": "non_stacked_metric"}`)保留不改。
- 新增两个函数(放在 `select_fig1_series` 之前):
  - `fig1_excluded_series(series_format=None) -> dict`:`series_format is None` → `dict(FIG1_EXCLUDED_SERIES)`;否则 `{k: "non_stacked_metric" for k in camp_series_provenance.stack_exempt_for(series_format)}`。**只有 `None` 回退**;空串/非法值/非字符串由 `stack_exempt_for` 抛 `SeriesProvenanceError`,本函数不吞。`camp_series_provenance` 的 import 沿用本仓库既有 lib 路径注入写法(参照 `a5_report_seal.py` 或 `audit_release_gate.py` 中 `sys.path` 注入 `scripts/lib` 的现成写法,不新造)。
  - `fig1_series_format(state) -> str | None`:唯一取值点。`prov = state.get("provenance")`;`prov` 非 dict 或无 `camp_series_sidecar` → `None`;`sidecar = prov["camp_series_sidecar"]` 非 dict → 抛 `SeriesProvenanceError("camp_series_sidecar 非对象")`;`fmt = sidecar.get("series_format")`;`fmt is None` → `None`;`fmt` 非 `str` → 抛 `SeriesProvenanceError`;否则返回 `fmt`(合法性由 `stack_exempt_for` 在使用时判定)。
- `:149`(锚 `def select_fig1_series(series):`)改签名 `def select_fig1_series(series, *, series_format=None):`;函数体:
  ```python
  exempt = fig1_excluded_series(series_format)
  keys = list(series)
  rendered = [camp for camp in CAMP_ORDER if camp in series and camp not in exempt]
  excluded = [key for key in exempt if key in series]
  allowed = set(CAMP_ORDER) | set(exempt) | {"ts"}
  rejected = [key for key in keys if key not in allowed]
  return rendered, excluded, rejected
  ```
  docstring 补一句:正式数据的豁免键由 producer `series_format` 经 `stack_exempt_for` 派生;`None` 保留 `FIG1_EXCLUDED_SERIES` 历史行为。
- `:164`(锚 `def plot_camp_evolution(series, out_png, token, note_supply="占总供应量", price_series=None,`)在参数表末尾加**关键字专用** `series_format=None`(用 `*,` 分隔,原有位置参数不动);`:191`(锚 `camps, _excluded, rejected = select_fig1_series(series)`)改为 `select_fig1_series(series, series_format=series_format)`。
- 注释同步:`:18`(锚 `锁仓/销毁在最顶`)与 `:169-170`(锚 `锁仓/销毁如有必须传入。` / `pct 为占总供应量的百分数`)各加半句:"Solana sol-rows 的锁仓/销毁是净供应分母外的真烧毁轨,经 series_format 豁免不堆叠;此时 note_supply 为占净供应量"。

**`scripts/report/figures_from_facts.py`**
- `mode_fig1`(`:107` 锚 `def mode_fig1(a):`):在 `:113`(锚 `rendered_camps, excluded_keys, rejected_keys = charts.select_fig1_series(`)之前加:
  ```python
  try:
      series_format = charts.fig1_series_format(state)
      exemption = charts.fig1_excluded_series(series_format)
  except Exception as exc:  # SeriesProvenanceError 及同族
      raise SystemExit(f"FAIL: state 的 camp_series_sidecar.series_format 非法,无法确定图 1 豁免集: {exc}")
  ```
  `:113` 调用改为 `charts.select_fig1_series(series_by_camp, series_format=series_format)`;`:116`(锚 `available = list(charts.CAMP_ORDER) + list(charts.FIG1_EXCLUDED_SERIES)`)改为 `+ list(exemption)`。
- `:133`(锚 `if camp in excluded_keys:`)有限值校验**不改**。
- `:164`(锚 `charts.plot_camp_evolution(`)调用加两个关键字:`series_format=series_format`、`note_supply=("占净供应量" if series_format == "sol-rows" else "占总供应量")`。
- `:175`(锚 `_write_fig1_legend_receipt(`)调用加 `exemption=exemption`;`:223`(锚 `def _write_fig1_legend_receipt(a, rendered_camps, excluded_keys, overlays):`)签名加 `*, exemption=None`,函数体首行 `exemption = dict(charts.FIG1_EXCLUDED_SERIES) if exemption is None else exemption`;`:229`(锚 `{"key": key, "reason": charts.FIG1_EXCLUDED_SERIES[key]}`)改为 `exemption[key]`。**不在 writer 里重读 state。**

**`scripts/report/a5_report_seal.py`** `_fig1_expected_from_state`(`:49` 锚 `def _fig1_expected_from_state(root):`):`:56`(锚 `rendered,excluded,rejected=standard_charts.select_fig1_series(series)`)之前加 `series_format=standard_charts.fig1_series_format(state_obj)`(state 对象变量名按该函数实际变量名)与 `exemption=standard_charts.fig1_excluded_series(series_format)`;`:56` 传 `series_format=series_format`;`:59`(锚 `standard_charts.FIG1_EXCLUDED_SERIES[key]`)改 `exemption[key]`;`:61`(锚 `set(standard_charts.FIG1_EXCLUDED_SERIES)`)改 `set(exemption)`。`SeriesProvenanceError` 由该函数既有的 `raise ValueError` 路径同族上抛(它已是 ValueError 子类),调用方现有捕获即可归入错误列表——施工时确认调用方捕获的是 `ValueError` 或更宽。

**`scripts/report/audit_release_gate.py`** `check_figure1_legend_receipt`(`:1366`):`:1388`(锚 `rendered, excluded_keys, rejected = standard_charts.select_fig1_series(series)`)所在 `try` 块内先取 `series_format = standard_charts.fig1_series_format(state)`、`whitelist = standard_charts.fig1_excluded_series(series_format)`,再传 `series_format=series_format`;`:1395`(锚 `whitelist = standard_charts.FIG1_EXCLUDED_SERIES`)删除(已在 try 内赋值);其余逻辑(`:1396-1412`)不改。`try` 的 `except Exception` 已能把 `SeriesProvenanceError` 归入 `errors`。

**明确不做**:evm-dict 的 ylabel 不动;sol-anchor-rows 不加特判;`CAMP_ORDER` 不改;被豁免键不画任何轨。

### B2 测试:`scripts/tests/test_figures_from_facts.py`(沿其现有 main() 风格追加)
1. sol-rows 端到端:state 带 `"provenance": {"camp_series_sidecar": {"series_format": "sol-rows"}}`(其余键按该文件既有 fixture 最小集),series 含 `大庄/散户/锁仓/销毁`(锁仓/销毁常值 5.0):exit 0;收据 `rendered_camps == ["大庄","散户"]`,`excluded_series` 含 `{"key":"锁仓/销毁","reason":"non_stacked_metric"}`;PNG 存在非空。
2. evm-dict:同 series,format 改 `evm-dict`:`rendered_camps == ["大庄","散户","锁仓/销毁"]`,`excluded_series == []`。
3. 既有 `:109-138` 无格式用例不改。
4. 纯函数:`select_fig1_series(series, series_format="sol-rows")` 三元组 == `(["大庄","散户"], ["锁仓/销毁"], [])`(series 不含 burn_cum_pct 时);`series_format=""` 与 `"bogus"` 抛 `SeriesProvenanceError`;`fig1_series_format` 对 sidecar 非 dict 抛、对缺 provenance 返回 None。
5. **消费链接入**:用例 1 的案目录,直接调用 `a5_report_seal._fig1_expected_from_state(root)`(断言 rendered/expected_excluded 与收据一致)与 `audit_release_gate.check_figure1_legend_receipt(case_dir, d, state, errors)`(参照 `test_repair_batch1.py:1120-1145` 的 `_f01b_*` 夹具与 stub 写法构造 `d`,断言 `errors == []`);然后四种篡改各自被**两个消费方都拒绝**(A5 侧通过 `_fig1_legend_errors` 或 `validate_seal` 报非空错误;闸侧 `errors` 非空):①收据把「锁仓/销毁」写回 `rendered_camps`;②收据漏掉「锁仓/销毁」豁免项;③overlay 引用被豁免的「锁仓/销毁」;④state 里被豁免桶含 NaN(该情形 fig1 直出应 exit 非 0)。
- `test_repair_batch1.py` F-01 段不改,必须仍绿(`:953` `selector.call_count == 2` 保持恰好两次)。

### B3 文档与注释同步(9 处,只补 Solana 分支,不改总供应判级总原则)
统一口径句(可按上下文缩写):"豁免集按 state 绑定的 producer `series_format` 由 `stack_exempt_for` 派生:`sol-rows` 豁免 `burn_cum_pct` 与「锁仓/销毁」(真烧毁轨,净供应分母外,图一按净供应标注、不堆叠仅在报告披露);`evm-dict` 仅豁免 `burn_cum_pct`(其「锁仓/销毁」仍是在账堆叠桶);无 `series_format` 的历史重绘保持旧规则"。
- `references/analyze-workflow.md:193`(锚 `` `burn_cum_pct` 只能以 `non_stacked_metric` 结构化豁免 ``)
- `references/report-template.md:35`(锚 `占**总供应量**的比例；锁仓/销毁必须单列体现`)加括注"(Solana sol-rows 图一按净供应,真烧毁轨不堆叠仅披露)";`:160`(锚 `y=占总供应量%`)改"y=占总供应量%(sol-rows 为占净供应量%)";`:276`(锚 `图 1 含锁仓/销毁阵营了吗（如有）`)加"(EVM 堆叠;Solana sol-rows 不堆叠仅披露)";`:297`(锚 `仅 `burn_cum_pct` 可以 `non_stacked_metric` 结构化豁免`)改统一口径句。
- `references/playbook-entity-cluster-tiering.md:115`(锚 `必须单列体现在图中`)加"(EVM 堆叠桶;Solana sol-rows 为堆叠外披露)";`:117`(锚 `burn_cum_pct` 豁免句)改统一口径句。
- `references/scan-schemas.md:597-605`:该段已含正确分家口径(`:605` burn 口径定案),仅在 `:599`(锚 `桶名白名单＝`standard_charts.CAMP_ORDER_MODERN`（∪ `burn_cum_pct` 豁免键`)后补半句"图一实绘集合同样按 `series_format` 派生豁免"。
- `SKILL.md:27`(锚 `占比以总供应为分母，锁仓/销毁单列。`)后加半句"(Solana sol-rows 图一按净供应,真烧毁轨不堆叠)";注意 `docs_lint.py` 的 SKILL.md 大小上限,若超限改用更短措辞。
- `runtime_docs_manifest.json`、`contract_manifest.json` 不动;`invariant_manifest.json` 预计不动,若 `invariant_scan.py` 报差异先判断是否无意改了登记面(receipt producer/consumer、formal 入口、原子写),确认确实变化才登记,并在 done.md 说明。

### B4 RED
改 B1 前:构造 sol-rows state(含「锁仓/销毁」=5.0)跑 `figures_from_facts.py fig1` → 收据 `rendered_camps` 含「锁仓/销毁」、`excluded_series == []`;同时用 `camp_series_provenance.validate_series_payload(css, series_format="sol-rows")` 对同一序列(非豁免键之和=100)判通过——两条并列证明画图与校验口径冲突。

## 4. 版本与登记面

- 五处 7.0.2:`VERSION`、`pyproject.toml:15`(锚 `version = "7.0.1"`)、`SKILL.md:23`(锚 `skill-version: 7.0.1`)、`CHANGELOG.md` 索引首行、详情首标题。
- `CHANGELOG.md`:索引一行 + 详情六栏(出处与根因/设计与实现/消费面与防回流/测试/盲审与验收/成本-质量指标),格式照 7.0.1 条目;出处只写"MELANIA/ARC 案触发的工具故障",**禁写任何代币分析结论**;写入前跑 `changelog_lint.py`。
- **白名单**(超出即违规):`scripts/lib/producer_history.py`、`scripts/tests/test_producer_registry_current.py`(新)、`scripts/tests/run_all.py`(仅 SUITE +1)、`scripts/report/a4_gate.py`、`scripts/tests/test_a4_gate.py`、`scripts/report/standard_charts.py`、`scripts/report/figures_from_facts.py`、`scripts/report/a5_report_seal.py`、`scripts/report/audit_release_gate.py`、`scripts/tests/test_figures_from_facts.py`、`references/analyze-workflow.md`、`references/report-template.md`、`references/playbook-entity-cluster-tiering.md`、`references/scan-schemas.md`、`VERSION`、`pyproject.toml`、`SKILL.md`(仅 `:23` 与 `:27`)、`CHANGELOG.md`、`maintenance/repair-20260906-main-threefix/*`;`scripts/tests/invariant_manifest.json` 仅在 invariant_scan 报错且确认登记面确实变化时允许。

## 5. 完工标准与产物

- `red_evidence.txt`:A/C/B 三段 RED。
- `done.md`:格式沿 `maintenance/repair-20260823-sqd-gap/batch18_review4_done.md` 五节;第 4 节命令/结果表逐行列 `changelog_lint.py`、`docs_lint.py --all`、`test_version_consistency.py`、`invariant_scan.py`、`run_all.py`(147/147)实际结果;第 5 节列白名单改动计数、"未 commit";遗留栏登记:A3 两处 monkeypatch、test_a4_gate 末尾"23 项"计数、evm-dict ylabel。
- 全绿后停,**不 commit**。任何一项做不到,写清做不到的原因与已完成部分,不得降低断言凑绿。
