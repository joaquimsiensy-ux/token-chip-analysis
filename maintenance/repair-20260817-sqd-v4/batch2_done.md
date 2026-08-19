# 批 2 施工交付：采集器 v4＋交易身份去重＋owner 双侧记账

## 1. 结论

批 2 已按 `PLAN.md` 与 `batch2_workorder.md` 完成，停在批 2 边界：

- T1：主 SQD 采集器落盘升为 7 元组；Mem/DuckDB 两条合并路径均按
  `(slot, tx_index)` 的完整交易边集 `tx_digest` 去重，同身份异 digest 硬失败；
- T2：owner authority 改为 pre/post 两侧独立记账，七条硬规则全部落在共享核与主采集入口；
- T3：非法/缺失交易身份、金额、owner、mint、account 与重复记录均 fail-closed；
- T4：meta 升 `sqd-solana-cache/v4`，collector SHA-256 启动从磁盘实算并在 finalize 前复验，
  上界被 finalized slot 截断，meta 改为原子发布；
- T5：v3 meta、孤儿缓存、旧/非法 `.parts` 在任何业务请求和 v4 parts 创建前 exit 2；CLI
  `--hypersync` 与直接 `run(hs_cfg=...)` 双入口硬禁；`window_fetch.py` 同升 7 元组与 receipt v3；
- T6：所有绑定本批生产者行为的既有测试随刀升级；消费端七文件、登记面、VERSION/CHANGELOG
  均未改；
- 最终 SUITE：118 项中 117 PASS、1 FAIL。唯一失败是工单明确冻结到批 4 的
  `invariant_manifest.json` 登记差异，共 7 条；业务测试、两条真实纵切片与全部其他 117 项通过；
- 未运行任何真实增量采集，未读取或启动批 3。

## 2. 开工序与基线

- 分支：`fix/sqd-solana-v4`；
- 批 2 开工 HEAD：`6fe6b3f52f5dddaf9267bdfeb16aaa60a209ba90`；
- 唯一开工脏项：用户提供、未跟踪的 `batch2_workorder.md`；按批 1 惯例先单独收编为
  `0af52e6`；
- 基线 `python3 scripts/tests/run_all.py`：118/118 PASS（两个 loopback fixture 在受限沙箱先报
  `PermissionError: [Errno 1] Operation not permitted`，同一命令获准绑定本机临时端口后全绿）；
- 批间风险纪律：批 2 完成前没有调用主采集器做任何真实增量采集，也没有出网采集。

施工期间另一个进程新建了未跟踪的 `batch3_workorder.md`。本批未读取、未修改、未暂存该文件；
它不属于本批 diff，收批状态中仍原样保留。

## 3. T1 修复工单五栏：DISTINCT 吃边

### 3.1 bug

旧生产者丢弃 `transactionIndex`，输出 5 元组；MemMerger 用边元组 `set`、ExtMerger 用五字段
`SELECT DISTINCT`。同 slot、同额、同 owner 的不同真实交易因此合并成一条。

### 3.2 不变量

不同交易的边永不因内容相同被合并；同一交易完整边集重复采集时恰保留一份；同一
`(slot, tx_index)` 出现不同完整边集时必须硬失败，禁止选一份或取并集。

### 3.3 同族清单

执行：

```text
rg -n -C 2 "SELECT DISTINCT|self\.edges = set\(|dedupe_transaction_sources|tx_digest|DISTINCT" \
  scripts/solana scripts/tests references --glob '!archive/**'
```

结果与处置：

1. `MemMerger`：旧边级 `set` 已删除，改用共享 `dedupe_transaction_sources`，按来源计算完整
   transaction digest；
2. `ExtMerger`：仍使用 `SELECT DISTINCT` 的位置只负责**同一 source 内相同 v4 行规范化**，
   不再跨交易按边去重；跨 source 先按 `(slot,tx_index)` 计算 `tx_digest`，同身份多 digest
   由独立冲突查询硬退；
3. `window_fetch.py`：没有自建去重实施点；本批只同步交易身份 7 元组与共享输入核；
4. `spl_edge_core.py`：`validate_edge_row`、`transaction_digest`、
   `dedupe_transaction_sources` 是内存路径唯一共享契约；
5. `test_sqd_merge_equiv.py`：旧“跨格式五字段去重”契约已删除，改为交易身份契约。

### 3.4 三件套测试

- 原反例：同 slot、同 from/to/amount 的两笔 `tx_index=1/2`，旧产物只剩 1 行；v4 保留 2 行；
- 同族变体：同一完整交易分别出现在两个 part，digest 相同只留一份；同身份两个 part 内容不同
  必须抛错；
- 失败分支：5 元组、混合 5/7 行宽、非法字段、同身份异 digest 均受控拒绝；超 int64 金额保持
  文本无损；Mem/DuckDB 输出逐字节一致。

### 3.5 新建代码自审与归因

- 字段来源：`slot/tx_index/ts` 来自 SQD 响应，`instr_index=-1` 来自冻结语义常量，from/to/amt
  来自经校验的 owner delta 与 `pair_tx` 重算；digest 只对规范化完整边集计算，不接受上游自报；
- 失败分支：行宽/类型/交易身份/金额/owner 任一非法即抛错；DuckDB 外排先做全量 shape 校验与
  digest 冲突查询，再 COPY 正式 gz；失败不替换旧缓存；
- 归因：**历史漏检**。五字段去重从 v2 设计期即存在，且早于本工程的
  `scan-schemas.md:17` 已明确“同五元组合法重复真实存在”；不是批 1 新引入。

## 4. T2 修复工单五栏：owner-authority 错账

### 4.1 bug

旧 `postOwner or preOwner` 把 token account 同交易内换 authority 的全部差额记到 postOwner；
`A:10 → B:12` 被记成 `B:+2`，A 的 10 凭空消失。

### 4.2 不变量

每条成功 tokenBalance 记录必须独立执行 `preOwner -= preAmount` 与
`postOwner += postAmount`；同 owner 自然合并为 post-pre；只计目标 mint 侧；任何异常记录不得
静默跳过。

### 4.3 同族清单

执行：

```text
rg -n -C 2 "def parse_owner_delta|owner_deltas_by_tx|postOwner or preOwner|parse_owner_delta\(" \
  scripts references --glob '!archive/**'
```

结果与处置：

1. `spl_edge_core.py::parse_owner_delta`：唯一单记录生产实现，已改为双侧 owner 记账；
2. `spl_edge_core.py::owner_deltas_by_tx`：唯一跨记录聚合实现，负责
   `(tx_index,account)` 重复检测与 owner delta 合并；
3. `fetch_sqd_transfers_v2.py` 与 `window_fetch.py`：均只调用共享核，无复制解析器；
4. 旧 `postOwner or preOwner` 生产代码命中为 0；仅批 1 交付文档保留历史事实叙述。

### 4.4 三件套测试与七硬规则

- 原反例：`preOwner=A, preAmount=10, postOwner=B, postAmount=12` →
  `A:-10 / B:+12`；
- 同族变体：同额换 owner；authority 变更叠加同交易其他 token account；close+reinit 换 mint
  只计目标 mint 一侧；
- Token-2022 transfer-fee/withheld 独立 fixture：`S:-12 / R:+10 / FEE:+2`，配边为
  `S→R:10 / S→FEE:2`，不制造 ZERO 供给边；
- 失败分支：非零 pre/post amount 缺对应 owner、非法/负金额、缺 account/preMint/postMint、
  非布尔非负整数 tx_index、重复 `(tx_index,account)` 全部拒绝；
- 请求体显式请求并核验 `account/preMint/postMint`；只计目标 mint 侧；close+reinit 不串账；
  供给增量来源在 v4 meta 标记为 `tokenBalances-owner-net`，指令级真值仍由 A2 供给闭合兜底。

### 4.5 新建代码自审与归因

- 字段来源：account/mint/owner/raw amount 全部来自 SQD tokenBalance 原始记录；目标 mint 来自冻结
  CLI 标的；没有接受“净额”“owner 结论”或供给增量的上游自报；
- 失败分支：成功交易状态必须在 transaction 表有唯一对应记录；缺状态不能再由
  `dict.get(...) is None` 冒充成功；解析异常使整页失败并走整段重试，超过重试上限返回未完成；
- 归因：**历史漏检**。`postOwner or preOwner` 在批 1 前已存在；批 1 明确只迁移不修，并把它登记
  为批 2 旧债，因此不是批 1 半修残留或本批新引入。

## 5. 红 → 绿证据原文

### 5.1 T1a/T1b/T1c 红态（生产代码修改前，exit 1）

```text
FAIL: T1a DISTINCT 吃边仍存在：同 slot 等额不同 tx_index 未保留 2 笔
（finished=True done_to=101 rows=1 body=['[1700000000, 101, "AAA", "BBB", 5]']）
FAIL: 同交易身份异 digest 未 fail-closed
FAIL: 旧 5 元组 未 fail-closed
```

混合 5/7 行宽在旧实现中因 Python 排序比较 int/string 偶然抛错；该异常不是显式格式门禁，不计作
旧实现正确。绿态实现改为 `validate_edge_row` 的稳定、可解释硬拒。

### 5.2 T1 绿态（exit 0）

```text
PASS: T1a 同 slot 等额不同 tx_index 保留 2 笔
PASS: T1b/c 同身份异 digest 与旧/混合行宽均硬失败
PASS: 契约1+2 两路径逐字节一致（7 行，大数保真，slot 单调）
PASS: 契约3 路径选择正确（阈值内=inmem / 超阈值=duckdb-external）
PASS: 契约4 原子落盘（中途 OOM 既不毁旧缓存也不留残件）
PASS: fetch_sqd_transfers_v2 v4 七组契约全过
```

### 5.3 T2a 红态（生产代码修改前，exit 1）

```text
TypeError: parse_owner_delta() takes 1 positional argument but 2 were given
```

红例已把目标 mint 与双 owner 期望写入测试；旧单 owner API 无法表达该不变量，测试在原反例首断言
处真实失败。

### 5.4 T2 绿态（exit 0）

```text
PASS: spl_edge_core T1 三件套 + T2 迁移等价 + T3 语义常量
```

该脚本内部已逐项断言 owner 变更、同额变更、close+reinit、Token-2022 fee/withheld、缺 owner、
非法/负金额、重复 account 与非法 tx_index。

### 5.5 T3 额外红 → 绿

红态：

```text
FAIL: T3 缺 transaction 状态的 tokenBalance 被默认成成功交易
（finished=True done_to=301 edges=[(1700000000, 301, 3, -1, 'AAA', 'BBB', 5)]）
```

绿态：

```text
PASS: T3 缺 transaction 状态触发整段失败
```

## 6. v4 meta 样例与 collector 冻结

最终采集器磁盘 SHA-256（写本交付物前）：

```text
a0302c40529ba385b359873901c3883cd3c64bfd22877c6448882aaeab9354bb
```

样例（mint/slot 为说明值，字段集合与生产者一致）：

```json
{
  "schema": "sqd-solana-cache/v4",
  "version": 4,
  "mint": "MintExample",
  "endpoint": "https://portal.sqd.dev/datasets/solana-mainnet",
  "endpoint_sha256": "3f96c669332c0d68461e2acf61e9a9a945a3ef583797756659ec96dccdb9ab7a",
  "collector": "fetch_sqd_transfers_v2.py/v4",
  "collector_sha256": "a0302c40529ba385b359873901c3883cd3c64bfd22877c6448882aaeab9354bb",
  "edge_schema": ["ts", "slot", "tx_index", "instr_index", "from", "to", "amt"],
  "edge_semantics": "owner-net-greedy",
  "order_granularity": "transaction",
  "order_exact": false,
  "dedupe_identity": "slot-txindex-digest/v1",
  "supply_delta_source": "tokenBalances-owner-net",
  "from_slot": 100,
  "finalized_upper_slot": 200
}
```

冻结/复验顺序：

1. `run()` 第一行从 `Path(__file__).resolve().read_bytes()` 实算 SHA-256；调用者无注入参数；
2. 该哈希写入 v4 identity；旧 v4 meta 的 hash 与当前启动 hash 不同即在网络前拒绝续跑；
3. `merger.finalize()` 前再次从磁盘实算；不一致则 finalize 调用次数为 0，只保留 parts/meta 供人工
   判断，返回非零 gap；
4. meta 使用同目录临时文件、flush/fsync、`os.replace` 原子发布；失败删除临时件。

TOCTOU 注入证据：启动 hash=`aaaa…`、写前 hash=`bbbb…` 时，测试用
`MemMerger.finalize(side_effect=AssertionError("finalize reached"))` 证明调用次数为 0；定向测试 exit 0。

## 7. 两路径等价证明

同一 fixture 同时覆盖：跨 source 重叠整笔交易、同 source 重复行、同 slot 不同 tx_index、
`10**19` 与 30 位大数、ts=0 mint、burn、默认/紧凑 JSON 分隔符。结果：

```text
PASS: 契约1+2 两路径逐字节一致（7 行，大数保真，slot 单调）
```

实现口径：

- Mem：每个 cache/part/backfill 是一个 source；source 内规范化完整交易边集并计算 digest；
- DuckDB：每个文件保留 `src_id`；先校验 7 栏与类型，再按 source/slot/tx_index 聚合排序边集
  `sha256(string_agg(...))`；`count(DISTINCT tx_digest)>1` 即硬失败；同 digest 选确定 source；
- 两边最终排序均为 `(slot, tx_index, from, to, amt-text)`；amount 不做 int64 cast。

## 8. 前置拒绝、HyperSync 与 window_fetch

- v3 meta、坏 JSON meta、无 v4 meta 的 cache/parts、任一非法/5 元组 part：在 `Fetcher.head()`、
  RPC、parts mkdir/read-for-merge 前 exit 2；统一提示：

```text
格式升级需全量重采，旧缓存请改名归档
```

- `--hypersync` CLI 与直接 `run(hs_cfg=...)` 均在首个业务请求前 exit 2；测试给
  `Fetcher.head(side_effect=AssertionError("network reached"))`，断言未触达；
- `window_fetch.py` 输出同一 7 元组，共用 transaction status、owner 双侧记账与 tx_index 校验；
  receipt 升 `solana-window-fetch-receipt/v3`，写入 edge contract；
- `test_batch3_solana_vertical_slice.py` 在本机 loopback 真 producer→runner→aggregator→READY→release
  路径通过，证明本批 producer 改动未破坏该纵切片。

## 9. 最终 SUITE

最终候选 tip：`3da3ad9935d00fb1ce1af49f0c3a7adc2044a691`。

执行：

```text
python3 scripts/tests/run_all.py
```

环境：获准在受限沙箱外运行，只为两个本机 loopback fixture 绑定 `127.0.0.1` 临时端口；没有真实
外网采集。

结果：**117 PASS / 1 FAIL / 0 SKIP，共 118 项，exit 1**。唯一失败：

```text
FAIL receipt_producers: code point missing from manifest:
  ('scripts/solana/fetch_sqd_transfers_v2.py', ('sqd-solana-cache/v4',))
FAIL receipt_producers: code point missing from manifest:
  ('scripts/solana/window_fetch.py', ('solana-window-fetch-receipt/v3',))
FAIL receipt_producers: manifest point missing from code:
  ('scripts/solana/fetch_sqd_transfers_v2.py', ('sqd-solana-cache/v3',))
FAIL receipt_producers: manifest point missing from code:
  ('scripts/solana/window_fetch.py', ('solana-window-fetch-receipt/v2',))
FAIL receipt_consumers: code point missing from manifest:
  ('scripts/solana/fetch_sqd_transfers_v2.py', ('sqd-solana-cache/v4',))
FAIL atomic_writes: code point missing from manifest:
  ('scripts/solana/fetch_sqd_transfers_v2.py', 'persist_meta')
FAIL atomic_writes: manifest point missing from code:
  ('scripts/solana/fetch_sqd_transfers_v2.py', 'run')
invariant manifest FAIL: 7 discrepancy(s)
```

这是 `scripts/tests/invariant_manifest.json` 冻结到批 4造成的预期冲突：两个 schema 版本替换、
fetch v4 meta 的 producer/consumer 登记，以及原子 meta 写 owner 从 `run` 精确迁到
`persist_meta`。工单明确禁止本批修改登记面，故没有以越权改 manifest 换取假全绿。

除 `invariant_scan.py` 外其余 117 项全部 PASS，包括：

```text
PASS test_sqd_merge_equiv.py  fetch_sqd_transfers_v2 v4 七组契约全过
PASS test_spl_edge_core.py    owner/输入/语义共享核回归
PASS test_r9_batch3_solana_observation.py  v4 identity/旧缓存/TOCTOU/HS 负测
PASS test_batch3_solana_vertical_slice.py  real producer->runner->aggregator->READY->release
PASS test_batch3_evm_vertical_slice.py     eth/bsc/base vertical closure
PASS test_review_resume_integrity.py       H-02..H-06
PASS test_sixlens_receipts.py              receipt fail-closed
PASS test_repair_batch1.py                 历史回归族
```

## 10. 六视角①②自审

### ① 字段来源审计

- `tx_index`：SQD `transaction.transactionIndex` 与 tokenBalance 同字段交叉绑定，不接受缺失状态；
- `account/preMint/postMint/preOwner/postOwner/preAmount/postAmount`：来自原始 tokenBalance；所有
  owner delta 在本地重算；
- `from/to/amt`：只由共享 `pair_tx` 对 owner delta 派生；
- `collector_sha256`：仅从当前脚本磁盘字节实算；六视角自审已删除调用者注入参数；
- `finalized_upper_slot`：来自 attested Solana mainnet session 的
  `getSlot(commitment=finalized)`，SQD head/CLI 上界只能向下截断；
- `endpoint_sha256`：由 endpoint 原文在本地指纹化，meta 只落脱敏 public origin 与 hash；
- `edge_schema/semantics/order`：从 `spl_edge_core.py` 单一机器常量导入；
- `tx_digest`：对每个 source 内规范化、排序后的完整交易边集本地计算。

未发现关键字段依赖调用者自报结论。

### ② 失败分支审计

- 旧/孤儿缓存、v3 meta、5/7 混宽：网络前 exit 2；
- tx 状态缺失/重复、tx_index 非法、金额/owner/mint/account 非法：整页失败，整段重试，最终未完成；
- 同身份异 digest：Mem/Ext 都抛错；
- collector 运行中变更：写前拒 finalize；
- meta 原子写失败：不替换正式 meta，临时文件清理；
- gz COPY/写入失败：不替换旧 cache，parts/meta 保留；
- HyperSync：CLI/直接 API 两条入口均首请求前 exit 2；
- window receipt/data 发布失败：沿用 receipt kernel 原子/错误回执路径，定向故障注入全绿。

未发现 warning 后继续签发正式成功产物的新分支。

## 11. diff → finding 与改动清单

| finding/任务 | 主要文件 | 测试 owner |
|---|---|---|
| T1 交易身份去重 | `spl_edge_core.py`、`fetch_sqd_transfers_v2.py` | `test_sqd_merge_equiv.py` |
| T2 owner 双侧记账 | `spl_edge_core.py`、两个 producer | `test_spl_edge_core.py` |
| T3 输入卫生 | `spl_edge_core.py`、两个 producer | 两个上述测试 |
| T4 meta/collector/finalized | `fetch_sqd_transfers_v2.py` | `test_r9_batch3_solana_observation.py` |
| T5 旧缓存/HS/window | 两个 producer、采集文档 | R9、vertical、receipt 历史测试 |
| T6 既有行为测试 | 5 个既有测试文件 | 各文件自身 |

自批 2 基线至最终候选，代码/测试/文档共 12 个文件，856 insertions / 221 deletions（不含本交付物）。

## 12. commit 台账（不含本文件交付 commit）

```text
0af52e6 批2：收编SQD采集器v4工单
ca75523 批2 T1：固化交易身份去重红态反例
29c196b 批2 T1：按交易身份去重并拒绝冲突版本
441eef9 批2 T2：固化owner-authority错账红态反例
94c836a 批2 T2：按owner双侧记账并落实七硬规则
55c1fbd 批2 T3：固化缺交易状态的输入红态反例
cc145bd 批2 T3：缺失或非法交易身份整段失败
41c8959 批2 T4：冻结采集器哈希并发布v4元数据
22c611b 批2 T5-T6：硬拒旧缓存并同步窗口采集器
fe3e695 批2 T6：同步SQD缓存身份既有回归
3da3ad9 批2 T4自审：采集器哈希只允许磁盘实算
```

## 13. 禁动范围与遗留事项

基于 `6fe6b3f..3da3ad9` 的路径审计：

- 消费端七文件 `replay_edges.py`、`wave_scan.py`、`flow_anomaly_scan.py`、
  `entity_source_trace.py`、`camp_series_provenance.py`、`audit_closed_accounts.py`、
  `curve_cost.py`：零 diff；
- `scripts/lib/producer_history.py`、`scripts/tests/invariant_manifest.json`：零 diff；
- VERSION、CHANGELOG：零 diff，版本仍 `6.48.1`；
- EVM 侧：零 diff；
- 任何案目录：零触碰；
- 外部未跟踪 `batch3_workorder.md`：未读、未动、未暂存。

遗留事项仅为后续已批准批次：

1. 批 3：消费端正式 v4/legacy 两态分立；
2. 批 4：把本批 7 条 invariant 差异登记进 `invariant_manifest.json`，并处理 producer history；
3. 批 5：VERSION/CHANGELOG、真实双 window 采集验收及最终收口。

批 2 到此停止，不开批 3。
