# Robinhood 降级影响与豁免台账（准备阶段）

## 一、拟定能力状态

Robinhood 将从当前错误的 formal 声明降为 **exploration/nonformal**：

- `release_tier=exploration`（最终字段名以批二能力矩阵为准）；
- `formal_ready=false` 必须由能力闭合自然导出，不增设同义手工开关；
- `evm_chain_id=None` 保持为显式能力缺口，不能猜填 4663 后绕过适配器/纵切片；
- 现有标签、脚本、历史案例与 casebook/方法文档不删除、不改写历史结论；
- Robinhood 增量更新、A4/A5 重签、audit release 不得走 formal；
- 恢复 formal 时，本文件全部 RH 豁免自动失效，必须先补 A0/A2/runner/consumer/identity/labels/handoff/release/chain-attestation 全闭合与纵切片。

上述是 PLAN 的既定施工方向，不是本阶段已完成事实；当前基线仍为 `chain_registry.py:44-49 formal=True, recon_adapter=evm, evm_chain_id=None`。

## 二、R8-02 当前证据

当前权威 registry 与强制工具矛盾：

| 面 | 当前证据（6e94348） | 结果 |
|---|---|---|
| registry | `scripts/lib/chain_registry.py:44-49` | `formal=True`, `recon_adapter=evm`, `identity_adapter=evm`, `evm_chain_id=None` |
| A0 accounting | `scripts/evm/accounting_gate.py:65-79` | `--chain robinhood` argparse exit 2 |
| A2 balance/recon | `scripts/evm/verify_recon.py:58-65` | `--chain robinhood` argparse exit 2 |
| A2 supply | `scripts/lib/supply_truth_gate.py:103-116` | `--chain robinhood` argparse exit 2 |
| A2 time | `scripts/lib/time_spotcheck.py:71-80` | `--chain robinhood` argparse exit 2 |

准备阶段实际执行四个最小 CLI，四者均在业务逻辑前 exit 2。故当前不是“Robinhood formal 能跑但缺测试”，而是正式纵切片物理不可执行。

## 三、存量 Robinhood 案例清单

`references/data-pipeline-robinhood.md:1,5` 明确列出 13 个历史实战来源。以下仅是影响盘点，不改写其历史结论：

| 存量案例 | 文档定位 | 降级后的处理 |
|---|---|---|
| GME | `data-pipeline-robinhood.md:1,5`；channels/traps/address-book 多处 | 保留为历史方法证据；不得以旧产物直接重签 formal 报告 |
| RAXOL | 同上 | 同上 |
| CASHCAT | `data-pipeline-robinhood.md:5` | 同上 |
| Pointless | `data-pipeline-robinhood.md:5` | 同上 |
| TRASH | `data-pipeline-robinhood.md:5`；labels benchmark 校准来源 | 历史校准/方法证据保留；不等于 formal 能力证明 |
| meow | `data-pipeline-robinhood.md:5` | 保留探索/历史证据 |
| VEX | `data-pipeline-robinhood.md:5` | 保留探索/历史证据 |
| HAN | `data-pipeline-robinhood.md:5` | 保留探索/历史证据 |
| BEGGAR | `data-pipeline-robinhood.md:5` | 保留探索/历史证据 |
| DUMBMONEY | `data-pipeline-robinhood.md:5` | 保留探索/历史证据 |
| VIRTUAL | `data-pipeline-robinhood.md:5` | 保留探索/历史证据 |
| COMPUTE | `data-pipeline-robinhood.md:5` | 保留探索/历史证据 |
| Index | `data-pipeline-robinhood.md:5` | 保留探索/历史证据；其 RPC tail 经验不能替代 receipt/target 闭合 |

## 四、会受降级影响的资产与文档

### 4.1 链专属运行资产

- `scripts/robinhood/` 当前 **16 个普通文件**（15 个 Python + `config.example.json`）：全部保留为 exploration 工具；不得进入 formal producer/data map/handoff/release 可达图。
- 其中 `pull_transfers_rpc.py`、`pull_block_ts_anchors.py`、`merge_hs_rpc.py` 对应 `full-F-02` / `full-C-01` / `full-C-05`：降级只改变可达性，不宣称其业务缺陷已修。
- `references/data-pipeline-robinhood.md` 与三个分册 `data-pipeline-robinhood-{channels,traps,methods}.md`：保留链知识和历史实测；入口/支持措辞需改成 exploration，历史段不重写。

### 4.2 标签与地址资产

准备阶段实数盘点：

| 资产 | 当前量 | 降级影响 |
|---|---:|---|
| `references/labels/labels-robinhood.csv` | 398 数据行 | 保留 exploration 标签资产；不能因为表存在就导出 formal-ready |
| `references/labels/codehash-robinhood.csv` | 3 数据行 | 保留 fingerprint 探索能力 |
| `references/labels/manifest.json` | 登记上述两件；主表 rows=398、codehash rows=3 | manifest 继续保证资产哈希，不授予 release tier |
| `references/address-book.md` Robinhood 机器行 | 71 行 | 历史/现场核验层保留；不改写 |
| `scripts/labels/sources/manual_labels.csv` Robinhood 行 | 71 行 | 与 address-book 同步关系保留 |
| `references/labels/benchmark/goldset.csv` Robinhood 行 | 374 行 | 保留标签质量 benchmark；不能把 benchmark PASS 当 formal chain PASS |
| `references/labels/README.md` / `MAINTENANCE.md` | 多处 Robinhood 主表、指纹、校准与维护路由 | 拆开“标签可用”和“链正式发布可用”两种能力 |

批二能力矩阵必须避免当前 `has_labels_table=True` 推导出 `formal=True`；标签能力只是 formal 闭合的一项事实。

### 4.3 跨链活动文档

以下活动文档含 Robinhood 规则或支持措辞，会受能力降级影响，但只改现役路由/能力表述，不改历史案例内容：

- `references/analyze-workflow.md`
- `references/analysis-playbook.md`
- `references/data-pipeline-evm-channels.md`
- `references/data-pipeline-evm-sources.md`
- `references/monitoring-package.md`
- `references/playbook-entity-cluster-cost.md`
- `references/playbook-entity-cluster-methods.md`
- `references/playbook-entity-cluster-tiering.md`
- `references/playbook-state-anomaly.md`
- `references/report-template.md`
- `references/address-book.md`
- `references/labels/README.md`
- `references/labels/MAINTENANCE.md`

`SKILL.md` frontmatter description 也在批二同步面内，但不属于本节“从 references/ 与 labels 盘点”的统计来源。

## 五、formal 防回流要求

降级后必须有负向证明：

1. chain registry/capability matrix 对 Robinhood 推导 `formal_ready=false`；
2. READY handoff 拒 Robinhood；
3. A4/A5/build_html/audit release 拒 Robinhood formal profile；
4. Robinhood exploration receipt/data 即使 schema/哈希自洽，也不得进入 formal data map 或 reconciliation wrapper；
5. `labels-robinhood.csv`、identity adapter、现有 docs 或旧案例不能单独把链重新抬升 formal；
6. 增量 RH 案不得复用旧 A4/A5 seal 冒充重签；
7. 任何新增 `evm_chain_id`、formal adapter 或调用图变化都触发豁免自动失效测试。

## 六、豁免台账（准备阶段候选）

七要素按 PLAN 合并为七栏；“Fable/盲审”一栏同时记录批准与两轮反查。

| 豁免 ID；finding / INV | 路径外理由与当前调用图 | 影响台账链接 | 能力矩阵 nonformal/exploration 证据 | formal 防回流负向测试 | Fable 批准 + 两轮盲审反查 | 自动失效条件 |
|---|---|---|---|---|---|---|
| `RH-EX-01`; `R8-02` / INV-11（沿革 `R7-07`） | 当前四件强制 CLI 均拒 RH；批二将 registry 降为 exploration，formal reachability 应为零 | 本文件 §2–§4 | 待批二 candidate：`release_tier=exploration`, `formal_ready=false`, `evm_chain_id=None` | 待施工：READY/A4/A5/audit release 四层拒收；labels/identity/旧案不能抬升 | Fable：待批准；Round A：待；Round B：待 | RH 变为 formal、`evm_chain_id` 非空、任一 formal adapter/入口可达或负测失败 |
| `RH-EX-02`; `full-F-02` / INV-02（含 `full-C-01`,`full-C-05`） | RPC tail/anchor/merge 三件只保留 exploration；不修其业务正确性，不允许结果进 formal data map/receipt/handoff | 本文件 §4.1；ledger supplementary 表 | 待批二 candidate：三 producer 不在 formal producer registry | 待施工：即使伪造完整输出/摘要，formal runner/aggregator/handoff/release 全拒 | Fable：待批准；Round A：待；Round B：待 | 三件任一重新进入 formal registry/文档必跑、产物进入 formal data map，或 RH 恢复 formal |

`full-F-04` 不列豁免：它是现役文档计数漂移，应由 INV-18 守卫修正。`full-F-03` 是通用 Multicall 工具，若走第四类豁免，应另建非 Robinhood 影响台账，不混入 RH 台账。
