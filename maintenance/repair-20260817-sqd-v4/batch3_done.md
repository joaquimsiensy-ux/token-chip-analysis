# 批 3 施工交付：消费端两态分立（正式 v4-only＋legacy 显式诊断）

## 1. 结论

批 3 已按 `T1 → T2 → T3 → T4 → T5 → T6 → T6b → T7` 完成并停工，没有启动批 4。

- 正式 Solana 消费链只接受 `sqd-solana-cache/v4`＋严格 7 元组；格式身份来自 v4 meta，
  不再靠逐行长度猜版本。
- legacy 5 元组只在显式 `--legacy-sol5` 下可读，输出强制暴露
  `non_formal=true`、`order_ambiguous=true`；reconcile、evolution、正式异常传导和实体溯源
  均不得借 legacy 入口生成 READY 链产物。
- transaction-net 边的 `instr_index=-1` 被解释为“交易间有序、交易内未决”；只有
  `instr_index>=0` 才是 instruction-exact。多方同交易 fixture 已证明未决量进入
  `UNRESOLVED/order_ambiguous`，不会再伪造交易内因果。
- `audit_closed_accounts.py` 的坏行不再吞掉，任一坏行均带行号整次失败。
- 最终全量 SUITE：119 项中 118 PASS、1 FAIL。唯一失败为工单明确冻结到后续登记批的
  `invariant_scan.py`，共 18 条代码/登记表版本差异；其余 118 项全部通过。

## 2. 开工序与边界

- 开工分支：`fix/sqd-solana-v4`。
- 批 2 交付 HEAD：`2311c7b`，开工时工作树干净。
- 四份前置文件已全文读取：`PLAN.md`、`batch1_done.md`、`batch2_done.md`、
  `batch3_workorder.md`。
- 工单先以独立 commit `28b6317 批3：收编消费端两态分立工单` 收编，之后才改代码。
- 批 3 相对 `2311c7b` 的禁动路径核查为零差异：采集器本体、合并器、
  `producer_history.py`、`scripts/tests/invariant_manifest.json`、VERSION/CHANGELOG、EVM
  生产侧和任何案目录均未修改。

## 3. receipt/schema 版本决策

### 3.1 `solana-reconcile/v3` 保持 v3

reconcile receipt 的字段结构、含义和发布 gate 没有新增字段；本批变化是它绑定的输入从 v3/5
升级为 v4/7。正式入口在写 receipt 前已验证 v4 meta、7 元组、窗口、逻辑摘要、文件
size/sha256 和 holder 快照，因此保持 `solana-reconcile/v3`，避免无结构变化的空升版。

legacy 模式直接拒绝 `reconcile` 和 `evolution`（exit 2），不写 legacy receipt，也不复用正式
`data/reconcile_receipt.json`。这是比另存 `*.legacy.json` 更窄的选择：旧案可诊断，但不能产生
任何容易被后续误收为正式输入的对账/序列件。

### 3.2 `wave-scan/v3` 升为 `wave-scan/v4`

wave receipt 新增并正式定义：

- `edge_order_granularity`；
- `order_ambiguous`；
- `non_formal`。

结构已实质变化，因此升 `wave-scan/v4`。消费面同步为
`adjudication_validator.py`、`handoff_manifest.py`、`audit_release_gate.py` 及其既有回归；READY、
裁决和发布闸均拒绝旧 schema 或 `non_formal/order_ambiguous` 标记不合法的产物。

## 4. 逐文件改动台账

| 任务 | 文件 | 施工结果 |
|---|---|---|
| T1 | `scripts/solana/replay_edges.py` | 正式 v4 meta＋7 元组；全部解包升 7；共享核常量；legacy v3/5 显式装载并归一成内部 7 列；混合宽度拒绝；reconcile/evolution 在 legacy 下 exit 2；正式 reconcile 重算逻辑摘要并锚定边文件。 |
| T2 | `scripts/report/wave_scan.py` | 删除正式路径的长度嗅探；逐行严格类型校验；`instr=-1` 为 transaction/order-ambiguous，`instr>=0` 为 instruction/exact；受控错误 exit 2；receipt 升 v4。 |
| T3 | `scripts/report/flow_anomaly_scan.py` | 显式识别 `--legacy-sol5`，但正式异常传导链直接拒绝，提示旧案 slot+owner 覆盖转 `audit_closed_accounts.py`。 |
| T3 | `scripts/report/entity_source_trace.py` | 正式溯源链直接拒绝 legacy；多方同交易未决量进入独立 `order_ambiguous` 桶并阻断发布。 |
| T4 | `scripts/solana/audit_closed_accounts.py` | 默认严格 7 元组；legacy 5 元组显式入口；坏 JSON/坏行宽/坏类型带行号整次失败；路径复用 `soltx_cache_paths`；legacy 报告带双标记。 |
| T5 | `scripts/solana/curve_cost.py` | 定性为正式内盘成本重建链，只认 v4/7；复用共享路径；逐行 fail-closed；全部解包升 7。 |
| T6 | `scripts/lib/camp_series_provenance.py` | 正式锚定由 v3/`collection_upper_slot` 改为 v4/`finalized_upper_slot`；原 size/sha256/digest 与边数锚定不变。 |
| T6 | `scripts/report/adjudication_validator.py`、`handoff_manifest.py`、`audit_release_gate.py` | wave v4 传导；旧版、non-formal 或标记矛盾均拒绝进入正式裁决/READY/发布。 |
| T6 | `references/scan-schemas.md`、`split-run.md`、`analyze-workflow.md`、`scripts/tests/contract_manifest.json` | 同步 wave v4 契约、正式/legacy 边界及文档路由。未改 `invariant_manifest.json`。 |
| T7 | `scripts/tests/test_sqd_consumer_v4.py` | 新增 v4/legacy 分立、混合宽度、摘要撕裂、curve v4-only 和 camp provenance 回归，并登记进 `run_all.py`。 |
| T7 | 既有消费端测试 | wave/flow/entity/reconcile/audit/release/resume fixtures 升 7 元组与 v4 meta；测试封印改为绑定当前算法实物，不再硬编码旧字节摘要。 |

## 5. legacy 三类合法场景验证

1. **旧案事故复盘**：`replay_edges.py --legacy-sol5` 接受绑定原始 mint、from_slot、
   `collection_upper_slot` 的 v3 meta 和全文件 5 元组；`trace/top/sniper/mints` 在控制台先打印
   `[legacy-sol5] non_formal=true order_ambiguous=true`。混合 5/7 行拒绝。
2. **slot+owner 覆盖审计**：`audit_closed_accounts.py --legacy-sol5` 可读取严格 5 元组做销户
   覆盖核查；报告强制带 `non_formal=true`、`order_ambiguous=true`，因此不能伪装正式审计件。
3. **证明旧数据不能精确溯源**：wave 可在显式 legacy 下生成带双标记的 v4 诊断报告；
   entity provenance 和 flow anomaly 正式链明确 exit 2，handoff/adjudication/release 消费面也拒收
   non-formal 产物。由此保留“为什么不可精确裁决”的证据，但不产正式结论。

## 6. `order_ambiguous` 多方交易证据

`test_entity_source_trace.py` 增加同一 `(slot, tx_index)` 下多方转入、全部
`instr_index=-1` 的 fixture：

- 旧逻辑会按文件行序伪造因果，给出稳定的 DEX 来源结论；
- 新逻辑把该同交易未决资金 100% 记入 `UNRESOLVED/order_ambiguous`，敏感性不稳定并 exit 2；
- 对照 fixture 把 `instr_index` 改为 `0` 后保持 exact，来源回到 `mint=100%`。

wave 对照回归同时证明：transaction-net 输入报告
`edge_order_granularity=transaction`、`order_ambiguous=true`；`instr>=0` 输入报告
`edge_order_granularity=instruction`、`order_ambiguous=false`。

## 7. 红 → 绿证据

每刀均先提交反例，再提交生产修复：

| 任务 | 红态事实 | 绿态证据 |
|---|---|---|
| T1 | 现役 replay 只认 v3/5，v4 meta 与 7 元组无法进入；legacy 可碰正式 reconcile。 | `test_sqd_consumer_v4.py`：v4 正式读取、legacy 显式读取、混合宽度拒绝、legacy reconcile exit 2、摘要撕裂拒绝，全过。红 commit `59e2f54`，绿 commit `a1d686e`。 |
| T2 | wave 把 5/7 行宽当格式探针，且 `instr=-1` 被误当 exact。 | `test_wave_scan.py`：正式拒 5、legacy 双标记、`instr=-1` transaction/ambiguous、`instr=0` instruction/exact、字符串 tx_index 受控 exit 2，全过。红 `24b0989`，绿 `a705020`。 |
| T3 | 传导链缺少明确 legacy 边界，多方同交易可按行序形成伪因果。 | `test_flow_anomaly.py` 与 `test_entity_source_trace.py`：两正式链拒 legacy；多方交易 100% 进入 order_ambiguous 并 exit 2；exact 对照保持 100% mint。红 `3735b7a`，绿 `e2631fb`。 |
| T4 | `load_edge_index` 对坏 JSON/坏行 `except: continue`，审计可在漏行后继续并给出误导结果。 | `test_repair_batch_d.py`：第二行坏 JSON 必须报“第 2 行”并整次失败；legacy 覆盖审计双标记；原 GPT-F-06 状态格全过。红 `1857ca8`，绿 `ac00ad0`。 |
| T5 | curve 成本重建没有 v4 loader，旧 5 元组解包与独立路径无法满足正式链契约。 | 新回归验证 v4 正常读取、第二行混入 5 元组带行号拒绝。红 `91d54fd`，绿 `f30020e`。 |
| T6 | camp provenance 仍期待 v3 meta/旧上界字段，v4 正式件被拒。 | 新回归用 v4 meta＋`finalized_upper_slot` 完成 reconcile→camp provenance 锚定；摘要改写被拒。红 `60722c2`，绿 `c9f1a53`。 |
| T7 | 既有 fixture 仍是 5 元组/v3，算法封印仍硬编码旧 `wave_scan.py` 字节。 | `batch_c` 227 checks、`batch_d` 全过，wave/flow/entity/handoff/adjudication/audit-release/EVM-release/resume 全过。commit `e0fd23b`。 |

## 8. T6b `collection_upper_slot` 读点核查

全库 `rg collection_upper_slot` 后逐点处置：

- `scripts/solana/replay_edges.py`：只在 `legacy_sol5=True` 的 v3 meta 分支读取，正式分支只读
  `finalized_upper_slot`；文案同样明确 legacy 身份。
- `scripts/lib/camp_series_provenance.py`、`scripts/solana/curve_cost.py`：正式路径只读
  `finalized_upper_slot`。
- `references/scan-schemas.md` 的现役 sol-rows 契约已改为 v4/
  `finalized_upper_slot`，窗口包含关系仍由 reconcile 的 `collection_window` 与
  `edge_extrema.slot` 验证。
- `scripts/tests/test_sqd_consumer_v4.py` 中旧字段只用于显式 legacy 正例。
- `scripts/tests/test_r9_batch3_solana_observation.py` 中旧字段是采集侧旧 meta 的负测/历史夹具，
  不属于本批消费端正式读点。
- `maintenance/repair-20260814-batch2/import_pythia_legacy.py` 与历史 review 文档属于冻结的旧案
  迁移/审查记录，不是现役消费路径，未改写历史。

现役正式消费路径不存在 `collection_upper_slot` 读点。

## 9. 最终 SUITE

执行：

```text
python3 scripts/tests/run_all.py
```

因纵切片需要绑定本机 `127.0.0.1` 临时端口，最终 run 经授权在沙箱外执行。结果：

```text
119 total = 118 PASS + 1 FAIL
唯一 FAIL：invariant_scan.py
invariant manifest FAIL: 18 discrepancy(s)
```

两项纵切片、所有业务测试、文档 lint、环境 lint、contract routes、消费链新旧回归均 PASS；
没有 loopback 环境失败。18 条登记差异原文分类如下。

### 9.1 receipt producers（6）

- code 有、manifest 缺：`wave_scan.py wave-scan/v4`、
  `fetch_sqd_transfers_v2.py sqd-solana-cache/v4`、
  `window_fetch.py solana-window-fetch-receipt/v3`。
- manifest 有、code 已无：上述三者分别仍登记 `wave-scan/v3`、`sqd-solana-cache/v3`、
  `solana-window-fetch-receipt/v2`。

### 9.2 receipt consumers（10）

- code 有、manifest 缺：
  `camp_series_provenance.py` 的 `sqd-solana-cache/v4` 组合、
  `adjudication_validator.py` 的 `wave-scan/v4` 组合、
  `handoff_manifest.py` 的含 v4 组合、`curve_cost.py sqd-solana-cache/v4`、
  `fetch_sqd_transfers_v2.py sqd-solana-cache/v4`、
  `replay_edges.py` 的 v3-legacy＋v4 组合，共 6 条。
- manifest 有、code 已无：camp 的 v3 组合、adjudication 的 v3 组合、handoff 的不含 v4 组合、
  replay 的旧 v3-only 组合，共 4 条。

### 9.3 atomic writes（2）

- code 有、manifest 缺：`fetch_sqd_transfers_v2.py persist_meta`。
- manifest 有、code 已无：`fetch_sqd_transfers_v2.py run`。

这些是冻结的 `scripts/tests/invariant_manifest.json` 与批 2/批 3 现役代码之间的登记差异；本批
没有改登记表制造假全绿。

## 10. 六视角①字段来源自审

- **格式身份**：正式来源是 cache meta 的 `schema/version/edge_schema/edge_semantics` 与显式
  CLI 模式，不从单行长度推测 v3/v4。
- **顺序身份**：`tx_index`、`instr_index` 均要求非布尔整数；`instr=-1` 与
  `ORDER_GRANULARITY_TX` 等语义引用 `spl_edge_core`，没有在消费端复制魔法常量。
- **采集上界**：正式来源统一为 v4 meta 的 `finalized_upper_slot`；旧字段只留 legacy 分支。
- **边实物**：reconcile 对真实遍历的 7 元组逐行 JSON 计算逻辑摘要，同时锚边文件
  size/sha256、行数和窗口；camp provenance 再独立核对这些锚。
- **报告正式性**：wave/audit 的 legacy 身份由 CLI 显式产生并落双标记；正式消费面验证标记，
  不信文件名或调用者口头声明。
- **因果边界**：交易内是否可排序只由 `instr_index` 证据决定；未知就进入未决桶，不按输入行序
  补造事实。

## 11. 六视角②失败分支自审

- v3 meta 走正式入口、v4 meta 走 legacy 入口、正式 5 元组、legacy 7 元组、混合行宽、
  非整数 tx/instr、空地址、非正金额：均受控拒绝，不能部分读后继续。
- legacy reconcile/evolution：在任何正式件落盘前 exit 2；flow/entity 正式链同样拒绝 legacy。
- audit 边文件任一坏行：包含文件名与行号的 ValueError，整次失败；不再 `continue`。
- 小写/大小写 mint 路径分叉：消费端统一走共享 `soltx_cache_paths`。
- cache meta 与实际边摘要/行数/size/sha、窗口、mint 或 holder 快照撕裂：reconcile/camp
  provenance fail-closed。
- wave v4 缺正式标记、标记矛盾、旧 v1/v2/v3 或 non-formal：裁决、handoff、release 至少一层
  fail-closed，不能到 READY。
- `git diff --check`、目标 Python 文件 `py_compile`、pre-commit 三检均通过。

## 12. commit 台账（不含本文件交付 commit）

```text
28b6317 批3：收编消费端两态分立工单
59e2f54 批3 T1：固化消费端v4分立红态反例
a1d686e 批3 T1：分立v4正式重放与legacy诊断
24b0989 批3 T2：固化波次顺序语义红态反例
a705020 批3 T2：修正波次扫描交易内顺序语义
3735b7a 批3 T3：固化传导件legacy拒绝红态反例
e2631fb 批3 T3：传导交易内未决并拒绝legacy溯源
1857ca8 批3 T4：固化销户审计吞行红态反例
ac00ad0 批3 T4：销户审计坏行整次失败并分立legacy
91d54fd 批3 T5：固化成本重建v4专用红态反例
f30020e 批3 T5：成本重建只认v4并复用共享路径
60722c2 批3 T6：固化阵营序列v4锚定红态反例
c9f1a53 批3 T6：传导v4锚定与波次正式语义
e0fd23b 批3 T7：同步消费链v4既有回归
```

## 13. 禁动范围证明与遗留事项

相对批 2 HEAD `2311c7b`，以下路径 `git diff --name-only` 为空：

- `scripts/solana/fetch_sqd_transfers_v2.py` 及采集/合并器；
- `producer_history.py`；
- `scripts/tests/invariant_manifest.json`；
- VERSION/CHANGELOG；
- EVM 生产侧；
- 任何案目录。

遗留仅两类：

1. **登记面 18 条冲突**：完整清单见第 9 节，属于冻结的后续登记批范围，本批未处理。
2. **工单前提与采集器实物不一致**：工单写“`edge_logical_sha256` 由批 2 采集器写入”，但对
   `fetch_sqd_transfers_v2.py` 的只读 `rg` 证明采集器实际没有写该字段。采集器属于本批禁动范围，
   因此未越权补写。当前正式消费链的处置是：reconcile 对 7 元组真实遍历计算摘要；meta 已有值
   时必须一致，否则拒绝；字段缺失时由 reconcile 原子回填，并由 receipt 与 camp provenance
   继续互绑。消费者一致性已有测试，但“采集时即落摘要”仍需在获准修改采集器的后续批次闭环。

批 3 到此停止，不启动、不施工批 4。
