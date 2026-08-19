# 批 1 施工交付：语义冻结＋共享核＋pair_tx 确定性

## 1. 结论

批 1 已按 `PLAN.md` 与 `batch1_workorder.md` 完成，停在批 1 边界：

- T1：`pair_tx` 等额输入顺序非确定性已按 `(-amount, owner)` 双键修复；
- T2：`pair_tx`、legacy owner delta 解析、sha256(mint) 缓存路径已抽到单一纯函数模块；
- T3：7 元组 transaction-net 语义已由文档与机器常量同 commit 冻结；
- T4：新回归已登记 `run_all.py`，收批 118 项 SUITE 全部通过；
- 禁动文件零 diff，VERSION 保持 `6.48.1`，未开批 2。

## 2. 开工序证据

- 开工分支：`main`；基线 HEAD：`e1be99ab25c0a6f60091d7a7b635ab6097e532c8`；VERSION：`6.48.1`。
- 开工脏树只有 `maintenance/repair-20260817-sqd-v4/` 下两份调度件，符合修订工单豁免。
- 新分支：`fix/sqd-solana-v4`。
- 首个 commit：`82372b1 批1：收编SQD v4工程调度件`，只收编 `PLAN.md` 与
  `batch1_workorder.md`。

基线 SUITE 首次在受限沙箱内执行，只有两个 loopback fixture 因环境拒绝绑定失败，原始失败核心为：

```text
PermissionError: [Errno 1] Operation not permitted
FAIL(rc=1)  test_batch3_solana_vertical_slice.py (无输出)
FAIL(rc=1)  test_batch3_evm_vertical_slice.py (无输出)
2 项失败——修完再收工
```

未把该次称为全绿；按同一命令解除沙箱端口限制后原样重跑，基线结果为：

```text
PASS  test_batch3_solana_vertical_slice.py PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release
PASS  test_batch3_evm_vertical_slice.py PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
========================================================
全部通过
```

## 3. T1 修复工单五栏

### 3.1 bug

`pair_tx` 等额时继承输入映射插入序，同一 tokenBalance 记录集合换序后可配出不同边，破坏
v4 后续按交易身份计算稳定 digest 的前提。

### 3.2 不变量

同一笔交易的 owner delta 记录集合，无论输入顺序如何，`pair_tx` 必须产出逐字节相同的边集合。

### 3.3 同族清单

执行：

```text
rg -n -C 4 'def pair_tx|pair_tx\(' scripts references --glob '!archive/**'
```

结果与处置：

1. `scripts/solana/fetch_sqd_transfers_v2.py`：删除复制实现，SQD 与 HyperSync 两个调用面均 import
   `spl_edge_core.pair_tx`；
2. `scripts/solana/window_fetch.py`：删除复制实现并 import 共享核；
3. `scripts/solana/spl_edge_core.py`：唯一生产实现；
4. `scripts/tests/test_spl_edge_core.py::_legacy_pair_tx`：仅为非等额迁移等价 oracle，不是生产入口。

未发现第三个生产实现。收批 `rg` 只剩共享核定义、三个生产调用面与测试调用。

### 3.4 三件套测试

- 原反例：A、B 各 −10；C、D 各 +10。只交换 C/D 输入顺序，旧实现从
  `A→C/B→D` 翻为 `A→D/B→C`；修复后固定为 `A→C/B→D`。
- 同族变体：固定随机种子生成 80 组 delta，每组 shuffle 20 轮；覆盖等额、零值、
  `10**30` 超 int64、供给不平时 ZERO mint/burn 哨兵，逐次断言输出恒等。
- 失败分支：非整数金额、bool 金额、`owner=None`、非 mapping 输入均必须抛 `TypeError`。

### 3.5 新建代码六视角①②自审

①字段来源审计：

- `pair_tx` 的 owner/amount 全部来自调用者传入的聚合 delta，并在入口验证类型；边金额只由整数
  delta 贪心扣减派生，不接收调用者自报的结果字段；
- `soltx_cache_paths` 的 key 只由原始 mint UTF-8 字节做 sha256 派生，不接收自报 hash；
- 7 元组字段序、edge semantics、顺序粒度和 `instr_index=-1` 是共享核机器常量，文档与测试引用
  同一冻结值；
- `parse_owner_delta` 仍按工单要求保留 `postOwner or preOwner`，没有把这一旧口径包装成精确
  owner-authority 结论。

②失败分支审计：

- `pair_tx` 对非法 mapping、owner、amount fail-closed；`soltx_cache_paths` 对非字符串 mint
  fail-closed；
- `parse_owner_delta` 对 owner 缺失/金额解析失败仍返回 `None`，调用侧仍静默跳过。这是工单明确
  要求本批原样迁移的已知旧债，不宣称已通过输入卫生；批 2 必须与 owner 七硬规则、整段失败语义
  一起关闭。本批未新增成功 receipt/meta，因此没有把该旧失败支路升级成新的正式成功面。

### 3.6 归因预判

归因：**历史漏检**。证据是单键排序从 v2 采集器既有实现起即存在，且 window_fetch 同期复制；
本轮 repair diff 之前即可由红态 fixture 稳定复现。最强替代解释是“既有去重/OOM 修复的半修残留”，
但此前 finding 的不变量是合并内存、原子写与字段去重，不含 owner 净额配对的输入序确定性，因此
不归半修残留。流程补强落在本批随机 shuffle 性质测试与同族 rg 守卫。

## 4. 红 → 绿证据原文

生产代码修改前红态（exit 1）：

```text
AssertionError: 同一 delta 集合因输入顺序漂移: [('A', 'C', 10), ('B', 'D', 10)] != [('A', 'D', 10), ('B', 'C', 10)]
```

修复后绿态（exit 0）：

```text
PASS: spl_edge_core T1 三件套 + T2 迁移等价 + T3 语义常量
```

迁移相关既有守卫同时通过：

```text
PASS: fetch_sqd_transfers_v2 六条契约全过
PASS: H-02/H-03 + U2b staged first capture + R2 legacy manifest refresh + H-04/H-05/H-06
```

## 5. T2/T3/T4 落地说明

- T2 共享核：`scripts/solana/spl_edge_core.py` 无网络、无文件读写；`parse_owner_delta` 原样保持
  legacy owner 选择与静默跳过；`cache_paths(address)` 保留兼容 wrapper，实际路径解析下沉到
  `soltx_cache_paths(mint, data_dir)`。
- T3 语义：正式 7 元组冻结为 `[ts,slot,tx_index,instr_index,from,to,amt]`；SQD
  transaction-net 边使用 `instr_index=-1`、`edge_semantics="owner-net-greedy"`、
  `order_granularity="transaction"`、`order_exact=false`，明确推定配对不等于链上精确 from→to。
- T3 提交：`79d846f` 同时包含两份文档和 `spl_edge_core.py` 机器常量，满足同 commit 约束。
- CT-SEMANTIC-29：`references/analyze-workflow.md` 中 `data/soltx-*.jsonl.gz` needle 保持命中；
  `docs_lint.py --all`、`invariant_scan.py`、`test_contract_routes.py` 全通过。
- T4：`test_spl_edge_core.py` 已登记 `run_all.py`，位于既有 `test_sqd_merge_equiv.py` 后。

## 6. 收批 SUITE

执行：`python3 scripts/tests/run_all.py`（非沙箱运行，仅为允许两个本机 loopback fixture 绑定
临时端口）。结果：118 项全部通过，exit 0。摘要原文：

```text
PASS  test_sqd_merge_equiv.py  PASS: fetch_sqd_transfers_v2 六条契约全过
PASS  test_spl_edge_core.py    PASS: spl_edge_core T1 三件套 + T2 迁移等价 + T3 语义常量
PASS  test_batch3_solana_vertical_slice.py PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release
PASS  test_batch3_evm_vertical_slice.py PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
========================================================
全部通过
```

## 7. 改动文件清单

以下为收批时 `wc -l`：

| 文件 | 行数 | 归属 |
|---|---:|---|
| `maintenance/repair-20260817-sqd-v4/PLAN.md` | 82 | 首提收编调度件 |
| `maintenance/repair-20260817-sqd-v4/batch1_workorder.md` | 85 | 首提收编调度件 |
| `maintenance/repair-20260817-sqd-v4/batch1_done.md` | 197 | 本交付物 |
| `references/data-pipeline-solana-capture.md` | 211 | T3 采集语义冻结 |
| `references/scan-schemas.md` | 583 | T3 边格式/顺序语义冻结 |
| `scripts/solana/fetch_sqd_transfers_v2.py` | 1182 | T1/T2 改用共享核，落盘仍为 5 元组 |
| `scripts/solana/spl_edge_core.py` | 82 | T1/T2/T3 新共享纯函数核与机器常量 |
| `scripts/solana/window_fetch.py` | 298 | T1/T2 改用共享核，落盘仍为 5 元组 |
| `scripts/tests/run_all.py` | 172 | T4 SUITE 登记 |
| `scripts/tests/test_spl_edge_core.py` | 125 | T1 三件套、T2 等价、T3 常量测试 |

## 8. commit 台账（不含本文件的交付 commit）

```text
82372b1 批1：收编SQD v4工程调度件
4c82fe4 批1 T1：固化pair_tx等额乱序红态反例
68b0514 批1 T1-T2：确定性配对并抽取SPL边共享核
79d846f 批1 T3：冻结Solana交易净额边语义
172d657 批1 T4：登记SPL边共享核回归套件
```

## 9. 禁动范围与遗留事项

基于 `e1be99a..HEAD` 的路径审计结果：

- `replay_edges.py`、`wave_scan.py`、`flow_anomaly_scan.py`、`entity_source_trace.py`、
  `camp_series_provenance.py`、`audit_closed_accounts.py`、`curve_cost.py`：零 diff；
- meta schema、落盘行格式、合并器：未改；本批 producer 仍输出 5 元组；
- `producer_history.py`、`scripts/tests/invariant_manifest.json`：零 diff；
- VERSION 与 CHANGELOG：零 diff，VERSION 仍为 `6.48.1`；
- EVM 侧脚本与任何案目录：零触碰。

遗留事项全部属于后续已批准批次，本批不施工：

1. 批 2：v4 meta、7 元组落盘、tx_digest 冲突硬失败、输入卫生、owner 七硬规则、前置旧缓存硬拒、
   HyperSync v4 禁用；
2. 批 3：正式/legacy 消费端两态分立及 `instr_index=-1 => order_exact=false` 的真实消费落地；
3. 批 4：producer history / invariant manifest 登记守卫与后续回归；
4. 批 5：VERSION/CHANGELOG、真实双 window 验收与最终收口。

批 1 到此停止，不开批 2。
