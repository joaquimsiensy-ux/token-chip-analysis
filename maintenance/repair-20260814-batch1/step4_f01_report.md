# 批 1 步骤④施工报告：F-01 图 1 白名单＋`select_fig1_series`＋legend receipt

施工范围严格限定为 `maintenance/repair-20260814-batch1/plan.md` “修复 2：F-01 图 1 白名单＋A5 图例集合绑定”的第 1/2/3 点、测试与本步文档。未执行任何 git 命令，未改 `archive/`，未触碰 `a5_report_seal.py`、`audit_release_gate.py`、`fetch_hypersync_v2`，未改版本号、CHANGELOG、`invariant_manifest.json` 或 `contract_manifest.json`。A5 v3、发布闸消费留步骤⑤；`figure1-legend/v1` manifest 登记留步骤⑦。

## ① 不变量

1. fig1 输入中的每个 series 键必须三选一：按权威顺序实绘、按唯一结构化规则豁免，或在出图前硬拒。不存在“wrapper 接受但 plot 静默丢弃”。
2. 实绘集合只由无 IO 的纯函数 `standard_charts.select_fig1_series()` 产生；`plot_camp_evolution` 与 `mode_fig1` 收据各调用同一函数，没有第二份排序/交集实现。
3. 权威绘图白名单由 `CAMP_ORDER` import 得到，不手抄阵营全集。EVM `CHIP_LEGACY_CAMP_DENOM=1` 真实产出的 `销毁` 已进 `CAMP_ORDER_LEGACY` 并有与 `锁仓/销毁` 同系的灰色配色。
4. 唯一豁免键是 `burn_cum_pct`；在场时先验列表长度与每个值的有限性，再以 `[{"key":"burn_cum_pct","reason":"non_stacked_metric"}]` 落收据；不在场时必须是空列表。
5. 白名单外键在 fig1 入口以 exit 2 拒绝，错误串列坏键、可用集合和 `scan-schemas.md` 存量迁移口径。输入/渲染/对账故障仍属 exit 1 语义。
6. 图例收据 schema 为 `figure1-legend/v1`，落在 state 文件同目录，绑定实绘 camps、结构化豁免、overlay 的“标签＋组成 camps”、可选价格 CSV 的 path/size/sha256、输出 PNG 与输入 state 的 path/size/sha256。收据以 tmp＋fsync＋`os.replace` 原子发布。
7. PNG 先渲染到同目录唯一临时 `.png`，确认非空后才原子替换正式路径、再落收据。旧 PNG 在场不能冒充本次渲染产物；本次无 PNG 时零新收据。
8. fig1 与 compile_state 的白名单不等深是有意设计：fig1 承担旧案基线重绘，允许 `CAMP_ORDER_LEGACY`；新报告仍由 `camp_series_provenance.validate_series_payload()` 的 `CAMP_ORDER_MODERN` 白名单拒绝 legacy。额外实跑批 C 115 checks 证明该编译闸未放宽。

## ② 同族 `rg` 清单与查证结论

### 施工命令

```bash
rg -n 'CAMP_ORDER|CAMP_COLORS|LEGACY|plot_camp_evolution' scripts --glob '*.py' --glob '!archive/**'

rg -n 'figures_from_facts|plot_camp_evolution|fig1|CAMP_ORDER' \
  maintenance references scripts/tests --glob '*.md' --glob '*.py' --glob '!archive/**'

rg -n 'fig1_legend_receipt|select_fig1_series|burn_cum_pct|CAMP_ORDER_LEGACY|"\u9500\u6bc1"' \
  scripts/report scripts/tests references --glob '*.py' --glob '*.md' --glob '!archive/**'
```

### 同族实施点

| 同族面 | 文件 | 查证/处置 |
|---|---|---|
| 阵营顺序与配色权威 | `scripts/report/standard_charts.py` | `销毁` 加入 legacy 组并补灰色；新建 `FIG1_EXCLUDED_SERIES` 与纯函数 `select_fig1_series()` |
| fig1 CLI 入口 | `scripts/report/figures_from_facts.py` | 拒绝键在任何绘图 IO 前 exit 2；burn 豁免显式验值；收据原子落 state 同目录 |
| 直接绘图入口 | `standard_charts.plot_camp_evolution` | 取消自建 CAMP_ORDER 交集，改调共享 selector；直接收到拒绝键也硬失败 |
| 新报告编译白名单 | `scripts/lib/camp_series_provenance.py` | 保持 `CAMP_ORDER_MODERN ∪ {burn_cum_pct}` 不动；`销毁` 及其他 legacy 仍不能进新报告 |
| EVM legacy 真实产物 | `scripts/evm/replay_pass2.py` | 只读查证 `CHIP_LEGACY_CAMP_DENOM=1` 产 `销毁`；本步不改 replay |
| 文档消费面 | `analyze-workflow.md`、`report-template.md`、`scan-schemas.md`、`playbook-entity-cluster-tiering.md` | “静默跳过＋人工目检”改为 selector＋receipt 机器闸；存量重绘豁免句补 fig1 白名单硬拒 |
| 后续消费面 | `a5_report_seal.py`、`audit_release_gate.py` | 按任务边界未改；步骤⑤接收 selector 和 legend receipt |

## ③ 三件套测试与先红后绿实跑证据

### a. 原反例：先红后绿

只向 `scripts/tests/test_figures_from_facts.py` 加入“`大庄=[60]`＋`未知阵营=[40]`”反例、尚未改生产代码时执行：

```bash
python3 scripts/tests/test_figures_from_facts.py
```

真实红态命令退出码：`1`。反例内部观察到生产进程 exit `0`，stdout 为：

```text
OK fig1: 1 点 × 2 阵营 → .../unknown.png（无价格轴）
```

这证明 wrapper 把未知键算进“2 阵营”并 exit 0，而旧 `plot_camp_evolution` 实际只画 CAMP_ORDER 交集里的 `大庄`。

修复后再执行同命令，真实命令退出码：`0`。`test_repair_batch1.py` 同时打印生产反例观察：

```text
F01 UNKNOWN observed_rc=2 png=False bad_key=True
PASS v6.41.0 batch1 steps 1-4 RV-07/RV-04/RV-17/F-03/F-01
```

### b. 同族变体

- `销毁` legacy 键实跑出图，断言配色在场且进 `rendered_camps`。
- `burn_cum_pct` 在场时结构化落 `excluded_series`；不在场时为 `[]`，不省略不落 null。
- overlay 有/无两态均实跑；在场时收据同时记 label 与 camps 组成，不在场时为 `[]`。
- 价格 CSV 在场时收据绑 path/size/sha256；无价格时显式记 `null`。
- spy 记录 selector 在 mode receipt 与 plot 两处各调一次，两次三元组结果逐项相等，收据 `rendered_camps` 与 selector 实绘列表相等。
- 额外实跑 `test_repair_batch_c.py` 115 checks，确认 `modern_camp_whitelist() == set(CAMP_ORDER_MODERN)`，新编译路径未被 legacy 绘图键放宽。

### c. 失败分支

- 未知阵营 exit 2，错误串同时含坏键、可用集合和迁移指引；零 PNG、零 legend receipt。
- `burn_cum_pct` 含 NaN 或 Infinity 时在绘图前硬拒，错误串点名键与“非有限”；零 PNG、零 legend receipt。
- overlay 缺等号、引用不存在或非实绘键均非零退出。
- 绘图函数本次不写临时 PNG 时硬失败且零新收据；即使正式路径已有旧 PNG，旧文件也只保留、不能作为本次收据的输出证据。

## ④ 新建代码六视角①②自审

### ① 字段来源审计

- `rendered_camps` 只来自当前 state 的 `camp_share_series.series` 键集与权威 `CAMP_ORDER` 在共享纯函数中的有序选择；mode 不自建第二份交集。
- `excluded_series.reason` 不受调用者自报，只来自代码常量 `FIG1_EXCLUDED_SERIES`；调用者也无添加其他豁免键的 CLI 参数。
- overlay 的 label/camps 来自当次 CLI，但 camps 逐一必须已在 selector 的实绘集合；曲线值再从 state 对应 camps 同点求和，收据冻结原始组成，不仅冻结可随意命名的标签文字。
- state、价格 CSV 与 PNG 的 size/sha256 都从当前磁盘字节重算，不接受 state/CLI 自报哈希。PNG 哈希在临时产物成功替换到正式路径后计算。

结论：本步新增准入与收据字段均能从当前 state/CLI 组成及实物字节离线重验，未把关键实绘集合改成调用者自报。

### ② 失败分支审计

- 拒绝键分类位于日期转换、价格读取、overlay 计算和所有绘图 IO 之前；未知键不可能产生 PNG 或 legend receipt。
- 每个 series 先验列表形态与长度；burn 豁免键再逐值验数字类型与有限性。豁免是“验后不堆叠”，不是“不检查”。
- `plot_camp_evolution` 自身也经 selector 拒绝未知键；即使绕开 wrapper 直接调 plot，也不再静默画交集。
- 渲染使用同目录唯一临时 PNG；图函数抛异常、无产物或空产物都不会替换旧正式 PNG，也不进收据函数。
- 收据在 PNG 成功后以 tmp＋fsync＋replace 发布；写入中断时正式收据不会被半截 JSON 覆盖。
- 不存在 `--allow-unknown-camp`、环境变量或空参数绕过；白名单是 fig1 mode 无条件必经点。

结论：未发现 warning 后继续、旧 PNG 冒充新产物、异常降级成 exit 0、或半截收据进正式路径。

## ⑤ 归因预判确认

维持计划预判：**历史漏检**。

证据：本步只加测试、未改生产代码时，原 fig1 入口已稳定复现“未知键被 wrapper 接受、生产进程 exit 0、图层只画 CAMP_ORDER 交集”，故可排除“本轮 repair diff 新引入”。批 C 的权威工单 `maintenance/repair-20260813-sixlens/batchC_fixround1_workorder.md` 明记“旧案不经 compile_state 的 fig1 重绘路径零触碰”，`r10_ledger.md` 也把该活路径单独留账；批 C F-04 声明的不变量是 producer→compile_state 的 MODERN 白名单与来源绑定，不是 fig1 重绘入口。因此该缺陷早于 2026-08-14 修复基线，且能排除前两类，符合 `maintenance-review-repair.md` 从严规则③。

最强替代解释是“老问题修复不全（半修残留）”：批 C 已经增加 compile_state 白名单，但 fig1 直读路径仍可击穿更宽的“非法阵营不得进正式链”叙事。不采纳理由：批 C 没有宣称修复该路径，反而在工单中明示零触碰，并在 R10 作为独立未完成项保留。将“显式延期、从未宣布闭合”倒算为上轮修复深度失守，与当时的 invariant 边界证据不符。

流程动作：今后修改阵营白名单时，同族清单必须同时列 producer/compile_state、fig1 wrapper、直接 plot、legend receipt 与发布闸五层；其中“旧案可重绘”只豁免 MODERN-only 编译闸，不豁免 fig1 自身的绘图白名单。

## 改动文件清单

- `scripts/report/standard_charts.py`
- `scripts/report/figures_from_facts.py`
- `scripts/tests/test_figures_from_facts.py`
- `scripts/tests/test_repair_batch1.py`
- `scripts/tests/test_repair_batch_c.py`
- `references/analyze-workflow.md`
- `references/report-template.md`
- `references/scan-schemas.md`
- `references/playbook-entity-cluster-tiering.md`
- `maintenance/repair-20260814-batch1/step4_f01_report.md`

## 验证命令与结果

| 命令 | 退出码 | 结果摘要 |
|---|---:|---|
| `python3 scripts/tests/test_repair_batch1.py` | 0 | F-01 三元组、原反例、收据完整性、同源调用、burn/overlay 两态与 PNG 失败分支全绿；步骤①②③回归保持通过 |
| `python3 scripts/tests/test_figures_from_facts.py` | 0 | 未知键 exit 2，legacy `销毁`、legend receipt、burn 豁免、overlay 组成、价格绑定全绿 |
| `python3 scripts/tests/test_repair_batch_c.py` | 0 | 额外保持红验证：115 checks 通过，compile_state 仍仅接受 MODERN 白名单 |
| `python3 scripts/tests/invariant_scan.py` | 1 | **按步骤⑦边界预期保持未登记**：扫描精确报 `figure1-legend/v1` producer 元组更新、`_write_fig1_legend_receipt` 收据原子 writer 和 `mode_fig1` PNG 原子 writer 未进 `invariant_manifest.json`，共 4 个 discrepancy；本步禁止修 manifest，待步骤⑦统一收口 |
| `python3 scripts/tests/docs_lint.py --all` | 0 | 58 个文档引用无断链、粗体配对完整 |
| `python3 -m py_compile scripts/report/standard_charts.py scripts/report/figures_from_facts.py scripts/tests/test_figures_from_facts.py scripts/tests/test_repair_batch1.py scripts/tests/test_repair_batch_c.py` | 0 | 全部改动 Python 文件语法通过 |

`invariant_scan.py` 的 exit 1 是任务书明示延后 manifest 登记所导致的可定位未收口项，不是本步可以通过放宽扫描或越界改 manifest 消除的失败。步骤⑦必须登记 schema producer 元组、收据 atomic writer 与 PNG atomic writer，再在最终合并快照上重跑至 exit 0。
