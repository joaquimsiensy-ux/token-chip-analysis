# 批 1 步骤⑤施工报告：A5 seal v3＋发布闸 legend 消费＋v2 迁移负例

施工范围严格限定为 `maintenance/repair-20260814-batch1/plan.md` “修复 2：F-01 图 1 白名单＋A5 图例集合绑定”的第 4/5 点及本任务书指定同步面。未执行任何 git 命令，未改 `archive/`，未触碰 `fetch_hypersync_v2`、replay/proxy/receipt_kernel，未改版本号或 CHANGELOG。`figure1-legend/v1` 新登记仍留步骤⑦。

## ① 不变量

1. `a5-report-seal/v3` 的 `producer` 固定为 `a5_report_seal.py/v3`；正式 validator 同时要求 schema/status/producer 为 v3 PASS，手工 v2 seal 不得冒充 v3。
2. new-analysis 的 A5 seal 必须把案根 `fig1_legend_receipt.json` 以 `entry()` 的 path/size/sha256 三元组冻结；缺件、符号链接、越出案根或 schema 非 `figure1-legend/v1` 均拒。
3. independent-audit 不强加 legend receipt，seal 内必须留下结构化 `{"status":"NOT_APPLICABLE", ...}`，validate 时按当前 A4 workflow 重算同一标记。
4. A5 new-analysis 四条交叉核对必须同时成立：receipt 绑定 PNG 是报告 images 中唯一同名实物；receipt state hash/size 等于当前标准 `analysis-state.json`；receipt PNG hash/size 等于当前报告 PNG；rendered/excluded/overlay 组成受当前 state 经 `select_fig1_series()` 的结果约束。
5. 步骤④ producer 的 `output_png.path` 是 basename，因此 A5 的 PNG 归属规则是“报告 images 中唯一同 basename 项＋size/sha256 相等”，不能错误地按案根 `fig1.png` 解析。
6. overlay 的选择本身不在 state 中，不能伪称可由 state 推导；机器可证边界是每项只含 `label/camps`、标签非空、组成非空且无重复、每个 camp 都属于当前 selector 实绘集合。
7. 发布闸 new-analysis 必需资产新增 `fig1_legend_receipt.json`，并独立从当前 `analysis-state.json` 调 `select_fig1_series()` 重算 rendered/excluded；排除键只认 `FIG1_EXCLUDED_SERIES`。A5 冻结实物，发布闸重算语义，两层不互相代替。
8. v2→v3 迁移语义已写入 A5 模块 docstring：旧 HTML 不受影响；存量案维持正式身份须重出 legend receipt＋v3 seal；无法重出只能走带水印的 legacy-recompile。

## ② 同族 `rg` 清单与查证结论

### 施工查证命令

```bash
rg -n 'a5-report-seal/v2|a5_report_seal.py/v2' \
  scripts/tests/invariant_manifest.json scripts/tests/contract_manifest.json \
  scripts/tests/test_distribution_gate.py references/analyze-workflow.md \
  references/split-run.md references/report-template.md

rg -n 'fig1_legend_receipt|figure1-legend/v1|select_fig1_series|FIG1_EXCLUDED_SERIES' \
  scripts/report scripts/tests references --glob '!archive/**'

rg -n 'create_seal\(|validate_seal\(|a5_report_seal' scripts/tests --glob '*.py'
```

### 同族实施点

| 同族面 | 文件 | 查证/处置 |
|---|---|---|
| A5 实物冻结与四核对 | `scripts/report/a5_report_seal.py` | schema/producer 升 v3；new-analysis 冻结 receipt entry 并重验 state、PNG、images、selector 语义；audit 写 NOT_APPLICABLE；模块写明迁移语义 |
| 发布闸必需资产与语义信任根 | `scripts/report/audit_release_gate.py` | receipt 加入 `NEW_ANALYSIS_REQUIRED`；发布期从当前 state 独立重算 rendered/excluded，并限制排除白名单及 overlay 组成 |
| schema 唯一字面量 | `scripts/report/figures_from_facts.py` | 把步骤④已有 schema 字面量提升为 `FIG1_LEGEND_RECEIPT_SCHEMA`；A5/发布闸导入消费，避免两份 schema 常量漂移，也避免产生步骤⑦前额外 invariant 差异 |
| A5 schema manifest 既有条目 | `scripts/tests/invariant_manifest.json` | 实际旧串只有 **2 处**（任务书预估 4 处），均只做 `/v2`→`/v3` 字符串替换；未新增条目 |
| 契约与源码字面量守卫 | `scripts/tests/contract_manifest.json`、`scripts/tests/test_distribution_gate.py` | CT-DISTRIBUTION-11 needle 与源码守卫同步 v3；未新增 CT 或测试登记 |
| 权威文档版本串 | `references/analyze-workflow.md`、`references/split-run.md`、`references/report-template.md` | 实际 4 个现役 v2 表述升 v3；未扩写新登记 |
| 回归矩阵 | `scripts/tests/test_repair_batch1.py` | 追加 F-01b/A5v3：缺件双闸、v3 绿例、四交叉反例、audit N/A、v2 迁移、发布闸三拒绝 |

### 步骤⑦待登记/收尾项

- `figures_from_facts.py` producer schema 元组加入 `figure1-legend/v1`（当前扫描以“新元组缺失＋旧元组多余”计 2 项）。
- `_write_fig1_legend_receipt` receipt 原子 writer 登记。
- `mode_fig1` PNG 原子 writer 登记。
- A5 与发布闸已成为 legend receipt 消费者；步骤⑦登记时需同时决定 invariant scanner 如何解析从 producer 导入的 schema 常量，不能靠在两个 consumer 重新手抄 schema 字面量制造第二权威。
- 全量 suite 前升级 `test_a4_gate.py` 的 P1-05 new-analysis 正例夹具：它仍不生成 camp series/legend receipt，现被新契约正确拒绝。该夹具升级不属于本任务书指定测试改动面。

## ③ 三件套测试与先红后绿实跑证据

### 修前红灯（先写测试，生产代码未改）

两条最小入口分别实跑，测试都要求“缺 receipt 必须拒绝”；旧实现实际放行，因此命令以断言失败退出：

| 入口 | 修前真实命令退出码 | 生产行为证据 |
|---|---:|---|
| `test_f01b_a5_missing_receipt_rejected(...)` | 1 | `_expect_error` 报 `expected fail-closed exception`，证明 A5 `create_seal` 无 receipt 仍成功 |
| `test_f01b_release_missing_receipt_rejected(...)` | 1 | 打印 `errors=[]`，证明发布闸 required-assets 面无 receipt 仍 PASS |

这两条红灯互相独立：第一条只走 A5，第二条只走发布闸真实 missing-file 循环并中和无关账本夹具。

### 修后绿灯与反例矩阵

| 场景 | 结果 |
|---|---|
| new-analysis 全材料 create＋validate | v3 schema、v3 producer、receipt entry 三元组均成立，validate `[]` |
| A5 缺 receipt | 最小入口 exit 0，内部确认 create fail-closed |
| 发布闸缺 receipt | 最小入口 exit 0，errors 含 `缺必需资产: fig1_legend_receipt.json` |
| receipt PNG 不在 report images | validate FAIL |
| receipt state sha 不符 | validate FAIL |
| receipt PNG sha 不符 | validate FAIL |
| rendered camps 与 selector 重算不符 | validate FAIL |
| independent-audit 无 receipt | create＋validate PASS，seal 含结构化 NOT_APPLICABLE |
| 手工 v2 seal | 新 validator 以 schema/status/producer 非 v3 PASS 拒绝 |
| 发布闸 receipt/state 不符 | 语义重算拒绝 |
| 发布闸白名单外排除键 | `FIG1_EXCLUDED_SERIES` 限制拒绝 |
| 步骤④未知阵营/burn/overlay/价格绑定 | 既有反例与绿例继续通过 |

## ④ 新建代码六视角①②自审

| 视角 | 自审结论 |
|---|---|
| ① 正确性/不变量 | create 与 validate 共用 `fig1_legend_bundle()`；validate 以当前 A4 workflow 重算，不能靠 seal 自报 profile。发布闸不调用 A5 语义结果，而是自己消费 state＋selector |
| ② 反例/失败分支 | 缺件、v2、四条交叉核对、语义漂移、越权排除、audit N/A 均有可重放测试；非 dict 排除项也 fail-closed，不会因 `.get()` 崩出发布闸 |
| ③ 证据链/信任根 | receipt bytes 由 A5 entry 冻结；state/PNG 当前实物由 A5 对哈希；rendered/excluded 由发布闸按当前 state 重算，封死“收据自报自洽” |
| ④ 兼容/迁移 | independent-audit 保持无 legend receipt 的正式路径；v2 明确拒绝，旧 HTML 保留，无法重出材料的存量案只走带水印 legacy-recompile |
| ⑤ 安全/路径 | receipt 本体经 `safe_file` 拒符号链接与越根；state path 必须恰为标准 basename；PNG basename 必须在报告 images 中唯一，且 size/sha256 同时一致 |
| ⑥ 可维护/单一权威 | camps 顺序与排除白名单只取 `standard_charts.select_fig1_series/FIG1_EXCLUDED_SERIES`；schema 字面量只留 producer，consumer 导入；manifest 不越界新增 |

剩余边界如实保留：state 不能推导“作者应选择哪条 overlay”，当前机器能证明的是已声明 overlay 的组成 camps 均来自实际实绘集合。若未来要强制某类实体搬家必须出现特定 overlay，需要另给 state 增加权威 overlay policy 字段，不能在本步凭空推导。

## ⑤ 归因预判确认

**确认：历史漏检，与 F-01 同案同因。**

- 修前 A5 v2 payload 只冻结报告 images 的 path/size/sha256，不冻结 legend receipt，也不从 state 重算图例语义；发布闸只重验 A5 既有绑定。这不是本批新改动引入。
- 步骤④修的是 fig1 入口白名单、共享 selector 与 receipt producer；A5/发布闸消费明确留到步骤⑤，因此不属于“前一修复声称已闭合却漏一半”的半修残留升格。
- 归因从严排除“修复中新引入”：修前两个独立红灯已实证旧实现同时放行；本步只是把已存在的图例语义缺口接入 A5 与发布信任根。
- 在禁止 git 命令的纪律下，本步不以 git 历史日期作额外证明；归因依据为冻结计划、修前代码与可重放红灯。

## 改动文件清单

- `scripts/report/a5_report_seal.py`
- `scripts/report/audit_release_gate.py`
- `scripts/report/figures_from_facts.py`
- `scripts/tests/test_repair_batch1.py`
- `scripts/tests/test_distribution_gate.py`
- `scripts/tests/invariant_manifest.json`
- `scripts/tests/contract_manifest.json`
- `references/analyze-workflow.md`
- `references/split-run.md`
- `references/report-template.md`
- `maintenance/repair-20260814-batch1/step5_a5v3_report.md`

## 验证命令与结果

| 命令 | 退出码 | 结果摘要 |
|---|---:|---|
| `python3 scripts/tests/test_repair_batch1.py` | 0 | F-01b/A5v3 全矩阵通过；步骤①至④回归继续通过 |
| `python3 scripts/tests/test_distribution_gate.py` | 0 | A5 v3 字面量守卫及既有 distribution 负例全过 |
| `python3 scripts/tests/test_figures_from_facts.py` | 0 | 步骤④未知键、legacy 销毁、receipt、burn、overlay、价格绑定全过 |
| `python3 scripts/tests/invariant_scan.py` | 1 | **按步骤⑦边界预期**，精确 4 discrepancy：producer 元组新缺/旧多 2 项＋receipt/PNG atomic writer 2 项；无 A5/发布闸新增差异 |
| `python3 scripts/tests/docs_lint.py --all` | 0 | 58 个文档引用无断链、粗体配对完整 |
| `python3 -m py_compile scripts/report/a5_report_seal.py scripts/report/audit_release_gate.py scripts/report/figures_from_facts.py scripts/report/standard_charts.py scripts/tests/test_repair_batch1.py scripts/tests/test_distribution_gate.py scripts/tests/test_figures_from_facts.py` | 0 | 全部本步 Python 改动面语法通过 |
| `python3 scripts/tests/test_round4_a5_seal.py`（额外回归） | 0 | 既有 A5 seal 哈希/Markdown/图片/v1 拒绝负例继续通过 |
| `python3 scripts/tests/test_audit_release_gate.py`（额外回归） | 0 | 既有独立发布闸负例套件继续通过 |
| `python3 scripts/tests/test_a4_gate.py`（额外、非指定） | 1 | 仅 P1-05 **正例夹具**未生成新必需 legend receipt，A5 未落盘；其余既有 A5/发布负例标签通过。留步骤⑦全量 suite 前升级夹具，不在本步伪造旁路 |

`invariant_scan.py` 的 exit 1 是任务书明示延后的 manifest 收口，不可通过放宽扫描消除。额外 `test_a4_gate.py` 的 exit 1 是旧正例夹具不满足新正式契约；生产门禁在该点 fail-closed，不能为了让旧夹具变绿而恢复缺 receipt 放行。
