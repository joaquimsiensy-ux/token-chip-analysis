# F-007 series_format 堆叠语义修复完成报告

## 结论

- F-007 已完成：EVM `evm-dict` 的「锁仓/销毁」恢复为两种分母口径都参与的普通堆叠桶；`burn_cum_pct` 仍是唯一 EVM 堆叠外披露轨。
- Solana `sol-rows` / `sol-anchor-rows` 继续把 `BURN_EXEMPT_KEYS` 作为堆叠外披露键；无 `series_format` 的手填路径继续使用原 dual/net/total 兼容行为。
- LIT 型 legacy 末点假红与 net 逐点假红先红后绿成立；新测试 12/12 PASS，工单指定的 5 个定向回归全部退出码 0。
- 完成物齐全：`f007_done.md`、`f007_red_evidence.txt`、`f007_green_evidence.txt`；新测试文件为 `scripts/tests/test_lit_regression_f007.py`。
- 归因三选一：**历史漏检**。`git blame` 显示一刀切 `BURN_EXEMPT_KEYS` 和 endpoint 的 `continue` 均由 `20ed20b`（2026-08-13，批 C 主施工）引入；当日后续 `eb6bee2` 只增加 denominator 的 net/total 单式，没有修正按 format 分家的 producer 语义。
- 最强替代解释是“半修残留”：`eb6bee2` 的 F-C4 确实加固过闭合互救，表面上像修了一半。未采纳理由：legacy endpoint 假红在 `20ed20b` 初版已经完整存在，F-C4 既未引入 endpoint 错误，也未尝试建立 series_format 映射；共同根因是一刀切豁免从设计起就与 EVM producer 不一致，不是本轮或近期新引入。

## 基线与施工边界

- 开工仓库：`/Users/uravvv/.claude/skills/token-chip-analysis`。
- 开工分支：`fix/lit-regression-v6522`，符合工单。
- 开工 HEAD：`0d4ceb5f6151dc72d837e71a681bc78e43e3e537`，符合 `0d4ceb5` 前缀门禁。
- 开工 `git status --short` 仅有 `?? maintenance/repair-20260824-lit-regression/`；白名单外干净。
- 执行方式：离线、未 commit、未切分支；没有运行任何真实出网命令。
- 工单目录开工时已有 `f007_workorder.md` 与 `workspace_baseline_20260824.patch`，两者保持不变。

### 第一步独立核实

| # | 裁决 | 独立理由 |
|---:|---|---|
| 1 | 属实 | `scripts/evm/replay_pass2.py:84-86` 的 legacy `stack=list(camps)`；`:101-106` 按全 stack 算 known 与散户；`:142-145` 只在非 legacy 输出 `_meta`/`burn_cum_pct`。 |
| 2 | 属实 | 同文件 `:86` 的 net stack 只排除旧自动桶「销毁」，不会排除 spec 桶「锁仓/销毁」；`:109` 与 `:142-145` 将 0x0 burn 另走 `burn_cum_pct`。 |
| 3 | 属实 | 开工 HEAD 的 `scripts/lib/camp_series_provenance.py:373-385` 用固定 `BURN_EXEMPT_KEYS` 算 `s_non/s_all`，再由 net/total 选择闭合式；豁免集合不分 format。 |
| 4 | 属实 | 开工 HEAD 的 endpoint spec 循环 `:754-779` 对 `BURN_EXEMPT_KEYS` 登记 `burn_recon` 后直接 `continue`，不进 `spec_sum`；散户恒等式因此把 EVM dead-sink 错当残差。 |
| 5 | 属实 | `scripts/solana/replay_edges.py:648-657` 以 `minted_cum-burned` 为 supply，持仓桶由正余额聚合，而「锁仓/销毁」另写 `burned/supply`，属于分母外披露，必须继续豁免。 |
| 6 | 属实 | 全库 `rg` 确认生产调用：`validate_series_payload` 仅 `state_from_facts.py:123` 手填与开工时 `:157` 绑定；`endpoint_reconcile` 仅 `state_from_facts.py:169` 与 `audit_release_gate.py:1363`。全库另有测试调用，工单声称限定“生产调用”，不构成反例。 |
| 7 | 属实 | 开工 HEAD 的 total 分支 `s_all=s_non+Σburn`，所以只替换 net 的豁免参数仍会在 total 分支把豁免键加回；`burn_cum_pct` 永久豁免不能由旧结构保证。 |

七项均属实，没有锚点错位或需停工的事实冲突。

## 改动清单

1. `scripts/lib/camp_series_provenance.py`
   - 新增固定映射 `stack_exempt_for(series_format)`：`evm-dict→("burn_cum_pct",)`；`sol-rows/sol-anchor-rows→BURN_EXEMPT_KEYS`；其他格式显式拒绝。
   - `validate_series_payload()` 新增可选 `series_format=None`。有 format 时只验实际堆叠键单式；无 format 时原 dual/net/total 分支、错误文本和闭合行为保留。
   - 增加 `evm-dict + mint_total_legacy` 携带 `burn_cum_pct` 的一致性拒绝。
   - endpoint 对 EVM 的「锁仓/销毁」同时登记 `burn_recon` 并计入 `spec_sum`；Solana 仍登记后 continue，不加到 `spec_sum`。
   - 同步模块 docstring、`BURN_EXEMPT_KEYS` 邻接注释、`closure_mode_for()` 与 `validate_series_payload()` docstring，并逐处写入 producer 行号依据。
2. `scripts/report/state_from_facts.py`
   - `bind_series_source()` 向共享校验传入 `series_format=sidecar["series_format"]`，同时继续调用 `closure_mode_for()` 校验 denominator 合法性。
   - 同步模块头与 F-C4/F-007 邻接注释，移除“按 denominator 决定 burn 归属”的旧表述。
   - 手填调用 `validate_series_payload(series)` 未改。
3. `scripts/tests/test_lit_regression_f007.py`
   - 新增 12 个独立用例：两条 LIT 型反例、EVM 一排一进、legacy 一致性闸、4 条防伪/非法值、无 format dual、固定映射、EVM 值域与 Solana 绿例/末点回归。
4. 工程档案
   - 新增 `f007_red_evidence.txt`、`f007_green_evidence.txt` 与本报告。

## 前后对照

### 1. 堆叠集合权威

改前（开工 HEAD `scripts/lib/camp_series_provenance.py:56-59`）：

```python
BURN_EXEMPT_KEYS = ("burn_cum_pct", "锁仓/销毁")
```

所有 format 后续都直接用这一集合，无法表达 EVM 与 Solana 同名桶的不同语义。

改后（`scripts/lib/camp_series_provenance.py:53-79`）：

```python
def stack_exempt_for(series_format: str) -> tuple[str, ...]:
    if series_format == "evm-dict":
        return ("burn_cum_pct",)
    if series_format in ("sol-rows", "sol-anchor-rows"):
        return BURN_EXEMPT_KEYS
    raise SeriesProvenanceError(
        f"series_format {series_format!r} 无堆叠语义映射")
```

生产依据写在同文件 `:27-35`、`:53-55`：EVM 对应 `replay_pass2.py:84-86,101-106,139-145`；Solana 对应 `replay_edges.py:648-657`。

### 2. 闭合校验

改前（开工 HEAD `camp_series_provenance.py:373-385`）：

```python
non_burn = [c for c in series if c not in BURN_EXEMPT_KEYS]
burn = [c for c in series if c in BURN_EXEMPT_KEYS]
s_non = sum(series[c][i] for c in non_burn)
s_all = s_non + sum(series[c][i] for c in burn)
if closure_mode == "net":
    closed = abs(s_non - 100.0) <= tol_pp
elif closure_mode == "total":
    closed = abs(s_all - 100.0) <= tol_pp
```

改后（现 `camp_series_provenance.py:333-410`）：

```python
stack_exempt = BURN_EXEMPT_KEYS if series_format is None \
    else stack_exempt_for(series_format)
if series_format == "evm-dict" and closure_mode == "total" \
        and "burn_cum_pct" in series:
    raise SeriesProvenanceError(
        "evm-dict + mint_total_legacy 序列不得含 burn_cum_pct："
        "replay_pass2 legacy producer 从不输出该键")
...
if series_format is not None:
    stack_keys = [c for c in series if c not in stack_exempt]
    s_stack = sum(series[c][i] for c in stack_keys)
    closed = abs(s_stack - 100.0) <= tol_pp
```

`series_format is None` 后仍是原 `s_non/s_all` 与 dual/net/total 分支（现 `:388-414`），用于手填兼容。

### 3. 末点残差

改前（开工 HEAD `camp_series_provenance.py:760-764`）：

```python
if camp in BURN_EXEMPT_KEYS:
    burn_recon[camp] = burn_recon.get(camp, 0.0) + recon
    continue
spec_sum += recon
```

改后（现 `camp_series_provenance.py:784-792`）：

```python
if camp in BURN_EXEMPT_KEYS:
    burn_recon[camp] = burn_recon.get(camp, 0.0) + recon
    if fmt == "evm-dict":
        spec_sum += recon
    continue
spec_sum += recon
```

因此 EVM dead-sink 既保留单桶 `burn_recon` 比对，也进入散户残差的 spec 合计；Solana 分支不加。

### 4. 绑定调用

改前（开工 HEAD `scripts/report/state_from_facts.py:154-158`）：

```python
validate_series_payload(compiled,
                        closure_mode=closure_mode_for(sidecar["denominator"]))
```

改后（现 `state_from_facts.py:155-160`）：

```python
validate_series_payload(compiled,
                        closure_mode=closure_mode_for(sidecar["denominator"]),
                        series_format=sidecar["series_format"])
```

手填路径现 `state_from_facts.py:123` 仍逐字为 `validate_series_payload(series)`。

## 先红后绿原始输出

### RED

生产代码改动前运行：

```text
COMMAND: MPLCONFIGDIR=/tmp/f007-mpl-cache python3 scripts/tests/test_lit_regression_f007.py --red-only
Matplotlib is building the font cache; this may take a moment.
FAIL: LIT legacy dead-sink endpoint: SeriesProvenanceError: 末点对账失败：散户残差末点 5.0000% ≠ 恒等式 100−Σspec=20.0000%（差 15.0000pp）
FAIL: LIT net dead-sink closure: SeriesProvenanceError: 第 0 点（2026-08-24T00:00:00Z）合计不闭合（closure_mode=net）：非burn桶Σ=85.0000、全桶Σ=110.0000，偏离 100 超过 0.05pp
SUMMARY: 0/2 PASS
EXIT_CODE=1
```

完整留档：`maintenance/repair-20260824-lit-regression/f007_red_evidence.txt`。

### GREEN

最终文件状态运行新测试：

```text
PASS: LIT legacy dead-sink endpoint
PASS: LIT net dead-sink closure
PASS: EVM net burn plus dead-sink
PASS: legacy burn_cum_pct consistency gate
PASS: retail endpoint tamper
PASS: dead-sink endpoint tamper
PASS: burn cannot rescue stack gap
PASS: illegal denominator
PASS: no-format dual compatibility
PASS: fixed format mapping
PASS: EVM dead-sink range
PASS: Solana burn disclosure
SUMMARY: 12/12 PASS
EXIT_CODE=0
```

新测试与 5 个定向回归的完整 stdout/stderr、命令和退出码逐字留档于 `maintenance/repair-20260824-lit-regression/f007_green_evidence.txt`（526 行）。

## 残留清点

复扫命令：

```bash
rg -n 'BURN_EXEMPT_KEYS|非 ?burn|s_non|s_all|净分母族|total 分母族|按口径单式|锁仓/销毁.*参与|锁仓/销毁.*不参与|closure_mode_for|validate_series_payload\(' scripts/lib/camp_series_provenance.py scripts/report/state_from_facts.py scripts/report/audit_release_gate.py scripts/tests/test_repair_batch_c.py scripts/tests/test_lit_regression_f007.py
rg -n --glob '*.py' 'validate_series_payload\(|endpoint_reconcile\(' .
```

逐类结论：

1. `BURN_EXEMPT_KEYS` 常量与 `stack_exempt_for(sol-rows/sol-anchor-rows)`：合法。它现在是跨格式披露键全集和 Solana 固定豁免返回值，不再作为所有 format 的唯一堆叠集合。
2. `camp_series_provenance.py:365` 的 `series_format is None` 取 `BURN_EXEMPT_KEYS`，以及 `:388-414` 的 `s_non/s_all`：合法且必须保留，是工单要求逐字兼容的手填 dual/net/total 路径；绑定路径先进入 `:395-410` 的 format 单式。
3. `camp_series_provenance.py:772,784` 的 `BURN_EXEMPT_KEYS`：合法。前者用于识别可披露桶，后者维持 endpoint 单桶 `burn_recon`；EVM 是否进残差合计由紧邻的 `fmt=="evm-dict"` 决定。
4. `closure_mode_for()` 与 state 绑定调用：合法。它继续验证 denominator 值域；不再决定 format 绑定路径的豁免键。
5. `scripts/tests/test_repair_batch_c.py:816-829,1071-1100` 的“净分母族/total 分母族/s_non/s_all”：合法历史兼容测试，全部调用都不传 `series_format`，正好守住无 format 路径；不是生产绑定逻辑残留。
6. `state_from_facts.py` 模块头曾残留“按 sidecar 口径的单式闭合”，收尾复扫时已在白名单内改为“按 sidecar 格式的实际堆叠单式”；最终无未分类旧口径表述。
7. 最终生产调用点仍只有 state 的手填/绑定两处与 state/audit 的 endpoint 两处；绑定处已传 format，手填处保持无 format，audit 只复验 format-aware endpoint。

未发现会让绑定路径回退到一刀切豁免的旧逻辑。

## lint 与测试证据

- `PYTHONPYCACHEPREFIX=/tmp/f007-pycache python3 -m py_compile scripts/lib/camp_series_provenance.py scripts/report/state_from_facts.py scripts/tests/test_lit_regression_f007.py`：退出码 0。
- `python3 scripts/tests/test_lit_regression_f007.py`：12/12 PASS，退出码 0。
- `python3 scripts/tests/test_repair_batch_c.py`：`PASS: repair batch C (F-05+F-04+fixround1+fixround2) 227 checks`，退出码 0。
- `python3 scripts/tests/test_a4_gate.py`：23 项全部通过，退出码 0。
- `python3 scripts/tests/test_sqd_consumer_v4.py`：`PASS: SQD v4 consumer split-mode regressions`，退出码 0。
- `python3 scripts/tests/test_state_from_facts.py`：4 条 PASS，退出码 0。
- `python3 scripts/tests/test_audit_release_gate.py`：十一类契约全过，退出码 0。
- `git diff --check`：无输出，退出码 0。
- 白名单 Python/档案文件行尾空格复扫：零命中；自产文档无 EOF 空行，因此无需新增 `diff_check_exemptions.md`。
- 未运行全量 `run_all.py`：工单明确的验收面是新测试加上述 5 个定向回归，且本批禁改 SUITE 登记；没有把未运行的全量 suite 描述为已通过。

## 发现项（只记录，不修）

1. 未发现工单外代码问题。
2. `test_repair_batch_c.py` 保留 denominator 口径的旧术语，但对应的是无 `series_format` 的兼容测试，并非生产绑定路径漂移，不需要也不允许在本批修改。

## 收工边界

- 只修改 `scripts/lib/camp_series_provenance.py`、`scripts/report/state_from_facts.py`，只新增 `scripts/tests/test_lit_regression_f007.py` 与本工单目录下档案。
- 未改版本三件、CHANGELOG、SUITE、契约、references 文档。
- 禁改文件 `scripts/report/wave_scan.py`、`scripts/report/entity_source_trace.py`、`scripts/solana/sqd_cache_identity.py`、`scripts/evm/replay_pass2.py`、`scripts/evm/replay_duck.py`、`scripts/solana/replay_edges.py`、`scripts/lib/case_paths.py` 均未修改。
- 未删除文件；未联网；未 commit；未 push。
- 完成标准三件齐全且新测试全绿，F-007 到此收工，不进入批 3 收口。

## round2 返工

### 结论与勘误

- round1 盲审唯一 BLOCK 已闭合：`sol-anchor-rows` 的 `stack_exempt_for()` 现返回空集，`锁仓/销毁` 与其余桶一起参与 total-supply 堆叠。
- `sol-anchor-rows` 若含 `burn_cum_pct`，共享校验会显式拒绝，并写明 `build_evolution` 不输出该键。
- round1 把 `sol-anchor-rows` 与 `sol-rows` 合并为同一豁免族的结论错误；本节只做增补澄清，不改写上方 round1 历史原文。

### 开工门禁与独立核实

- 仓库、分支、HEAD 分别为 `/Users/uravvv/.claude/skills/token-chip-analysis`、`fix/lit-regression-v6522`、`0d4ceb5f6151dc72d837e71a681bc78e43e3e537`，符合返工工单。
- 开工 `git status --short` 可见 round1 的 `camp_series_provenance.py`、`state_from_facts.py` 与新测试改动；按返工工单保留并在其上施工，未还原。
- `sol-anchor-rows` 勘误属实：`scripts/solana/build_evolution.py:177-183` 把 `锁仓/销毁` 写入 `camp_raw`，再由 `known=sum(camp_raw.values())` 计入已知桶，散户补 `TOT-known`，最后全桶除以 `TOT` 输出。因此真实行是全桶合计 100%，且该 producer 没有 `burn_cum_pct` 输出路径。
- `SERIES_FORMATS` 四值复核：`evm-dict` 由 `replay_pass2.py:160-165` 与 `replay_duck.py:504-509` 登记，堆叠依据分别同源于两 producer；`sol-rows` 由 `replay_edges.py:648-657,706-710` 登记，烧毁桶在净供应分母外披露；`sol-anchor-rows` 由 `build_evolution.py:177-183,211-215` 登记，烧毁桶参与全桶堆叠；`evm-entity-dict` 由两个 EVM producer 登记实体序列，但 `series_to_state_form()` 在 `camp_series_provenance.py:276-279` 明确把实体序列路由到图 2 check 通道，不进入本闭合路径。未发现第五种格式或其他被错误归并的 producer。

### 改动前后与五条最小清单闭合

1. 映射与非法键：改前 `stack_exempt_for("sol-anchor-rows")` 返回 `BURN_EXEMPT_KEYS`；改后 `camp_series_provenance.py:75-84` 返回 `()`。`camp_series_provenance.py:373-376` 新增 anchor 携带 `burn_cum_pct` 的显式拒绝，错误信息绑定 `build_evolution.py:177-183`。
2. 真实 oracle：`test_lit_regression_f007.py:200-223` 固定三条独立断言：`40+35+25=100` 接受、`40+60+25=125` 拒绝、anchor 出现 `burn_cum_pct` 拒绝；round1 中把 `40+60+25=125` 当绿例的错误 oracle 已删除。
3. 文档同步：模块 docstring `camp_series_provenance.py:27-37`、常量邻接注释与 `stack_exempt_for()` docstring `:55-84`、`closure_mode_for()` docstring `:324-330`、`validate_series_payload()` docstring `:339-353` 均将 anchor 依据改为 `build_evolution.py:177-183`；不再用 `replay_edges.py` 证明 anchor producer 语义。
4. 历史增补：本 `round2 返工` 节记录勘误、前后对照、归因和验收，round1 原文保持不变。
5. 绿证重建：`f007_green_evidence.txt` 已覆盖式重新生成，逐条保留 F-007 与五组定向回归的完整 stdout/stderr、命令和 `EXIT_CODE`；`f007_red_evidence.txt` 未改。

### round2 先红后绿与归因

- 只改新 anchor 测试、生产实现尚未改时：`11/15 PASS`、`EXIT_CODE=1`。四个红点分别是固定映射仍返回旧豁免、真实 100% 形态被按 75% 误拒、125% 错误形态被接受、`burn_cum_pct` 没有 producer-specific 显式拒绝。
- 生产修复后：F-007 `15/15 PASS`、`EXIT_CODE=0`；五组定向回归 `test_repair_batch_c.py`、`test_a4_gate.py`、`test_sqd_consumer_v4.py`、`test_state_from_facts.py`、`test_audit_release_gate.py` 均 `EXIT_CODE=0`。完整原始输出见重建后的 `f007_green_evidence.txt`。
- 归因：源头是原工单事实错误——没有核对 `build_evolution.py` 就把 `sol-anchor-rows` 并入 `sol-rows` 豁免族；施工方同时违反原工单“独立核实”要求，使用 `replay_edges.py` 替另一个 producer 证明语义，未能在 round1 拦住错误 oracle。两者缺一都不足以解释 round1 通过后仍被盲审 BLOCK。
- 最强替代解释是“anchor 不进正式编译链，所以旧映射无实际影响”。不采纳：它仍是 `SERIES_FORMATS` 登记值并由真实 producer 写 sidecar，共享校验函数对该格式公开固定映射；错误映射会直接把 producer 可生成的 100% 形态误拒，不能因其属于辅助件而接受伪语义。

### round2 收工边界

- 本轮只改 `scripts/lib/camp_series_provenance.py`、`scripts/tests/test_lit_regression_f007.py`、`f007_done.md`、`f007_green_evidence.txt`。
- `scripts/report/state_from_facts.py` 保留 round1 已定型改动，本轮未改；`scripts/solana/build_evolution.py` 只读核实，未改。
- 未改任何原工单禁改文件、版本三件、CHANGELOG、SUITE、契约或 references；未联网、未 commit、未 push。
