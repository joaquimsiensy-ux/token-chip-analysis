# 批 7 完成记录：curve_cost 归属闭环与 provenance 威胁模型收敛

日期：2026-08-18  
分支：`fix/sqd-solana-v4`  
开工基线：`2fb1924`（批 6 F-08 完成态）  
工单：`batch7_workorder.md`，收编提交 `45be11138bfa8d9ba5c7a7bd6136a576e80246f0`

## 1. 收批结论

- F2-01：**CONFIRMED，已修**。`curve_cost.py` 原先只做八项内联格式检查，未校验 ACTIVE
  producer、逻辑摘要和行数；独立夹具证明伪造 meta 可产出 `curve_costs.json`。现已复用
  `sqd_cache_identity.validate_cache_meta`，并对实际边文件重算摘要和行数。
- F2-02：**CONFIRMED（WEAK，接受项）**。文档对 slot+owner 弱覆盖与 signature 未映射的说明真实
  存在，RPC 抽样兜底路径也真实存在；按验收方定性不改逻辑。
- F2-03：**CONFIRMED（非 bug）**。`collector_sha256` 是 git 可复现的公开完整性哈希，当前校验只
  证明本地件内部自洽，不抗能写 `data/` 的主动伪造者。只做文档定性和宣称收敛，没有新增防御代码、
  签名或链上重验机制。
- F2-04：**CONFIRMED，选择低成本修复**。reconcile 原先对内存逻辑边与磁盘物理哈希两次独立读取；
  现改为一次冻结压缩字节，同一字节像同时产生 size/SHA-256 和解压重放输入，receipt 协议未改。
- F2-05：正常 PATH 与不含 `rg` 的 PATH 各完整执行一次 SUITE，均为 **121/121 PASS、exit 0**。
- `fetch_sqd_transfers_v2.py`、VERSION、CHANGELOG 零改动；版本保持 `6.49.0`。未 merge、未 push。

## 2. 开工与边界

- 开工前全文读取 `PLAN.md`、六份 `batch*_done.md`（含 F-08）及 `batch7_workorder.md`。
- 开工时分支正确，无已跟踪脏改；未跟踪件只有工单和外部提供的 `opus_review_round1.md`。
- 工单先以独立 commit `45be111` 收编；`opus_review_round1.md` 全程未读、未改、未暂存。
- 本批没有读取或改写 ARC 外部案目录。
- 工单所述 `sync-from-cc.sh`/`SYNC.md` 在本仓库不存在；本次又是指定冻结分支维护，不伪造同步成功，
  也不引入同步产生的工单外变更。

## 3. F2-01：curve_cost 正式归属覆盖缺口

### 3.1 独立复核 — CONFIRMED

用 `inspect.getsource` 读取开工态真实函数，`curve_cost.load_edges` 源码 SHA-256 为：

```text
608ed994c43ab8641d8bf29d3d4f29603d1025ef6e75b503aa548182f40c7dd2
```

真实代码只内联比较 schema/version/mint/edge schema/semantics/order/finalized upper slot，未 import
或调用 `validate_cache_meta`，也不比较 meta 的摘要/行数与实际 gzip。

隔离夹具不复用二审产物：从红态 commit 的 git object 载入旧 `curve_cost.py`，构造字段对齐但
`collector_sha256=ffff…`、`edge_logical_sha256=0000…`、`edge_rows=999` 的 meta 和一条真实 7 元组边，
真跑 `main()` 得到：

```text
F2-01_INDEPENDENT_RED rc=0 output_exists=True owner_present=True
forged_collector=ffffffff forged_rows=999
```

这证明缺口不止停在 loader：旧代码实际签出了 `data/curve_costs.json` 成本结论。同一未登记 producer
输入由 `replay_edges.load_edges` 精确拒绝“producer 登记”。

### 3.2 红 → 绿

红态提交：

```text
5a9d9b8124918c236d20116d6916768ee2236b6b
批7 F2-01：固化成本重建归属缺口红态反例
```

生产修复前定向测试真实 exit 1：

```text
AssertionError: expected rejection containing 'producer 登记'
```

绿态提交：

```text
abccb8e35f3ea4342a850cd9596c117c7ca0a3a2
批7 F2-01：补齐成本重建归属与边实物校验
```

修法严格最小化：

1. 删除 curve_cost 的八项私有内联校验，改调共享 `validate_cache_meta(..., legacy_sol5=False)`；
2. 保留严格 7 元组逐行校验，同时按 producer 规范化算法流式计算逻辑 SHA-256 和行数；
3. meta 的 `edge_logical_sha256/edge_rows` 与实际 gzip 任一不符即拒绝；
4. 未登记 collector 与摘要错两类输入，分别与 replay load/reconcile 正式链等价拒绝。

定向绿态：

```text
PASS: SQD v4 consumer split-mode regressions
PASS invariant manifest: receipt_producers=63, receipt_consumers=93,
transport_calls=63, atomic_writes=54, formal_entrypoints=58, exceptions=0
```

### 3.3 不误伤合法 v4 产物确认

批 4 起正式 collector finalize 必写 `collector_sha256`、`edge_logical_sha256`、`edge_rows`；批 6 现役
ACTIVE producer 的两个 git object 哈希也独立复算一致：

```text
75aa622a... -> 2589f6a396c262d0747343ef21dee2bc7ba814eaa59eebdfa782fe9253c32212 MATCH
47b3620f... -> a94b193b94ba8872e4d6aa4915ff7d89ef6cc438d7f2c6c0744ebc33212d9bae MATCH
```

合法 `_v4_meta(rows)`＋实际边夹具仍通过 curve_cost；`test_sqd_collector_meta_v4.py` 与完整 SUITE
也通过。因此新增校验只拒绝不具备正式 v4 证据的输入，不改变合法产物协议。

## 4. F2-02：audit_closed_accounts 弱覆盖

### 4.1 两条理由的真字节复核

理由一属实。当前文件真字节明确写明：

- `grep_legacy_whitelist.md`：该入口“仅保留 slot+owner 旧案覆盖审计”；
- `batch5_done.md` §6.2/§11：覆盖谓词仍为 slot+owner，签名尚未映射到 `(slot,tx_index)`；
- 现役 `data-pipeline-solana-capture.md` §12：同 slot、同 owner 多笔仍可能误判覆盖，需
  signature→`(slot,tx_index)` 才能 transaction-exact。

只读复核时三份关键文件 SHA-256：

```text
grep_legacy_whitelist.md  5be39bf8ebafb30a13b1057161d4d358fa8666f58121af09754f0a4e160363e1
batch5_done.md            e8a3eb1136cf595332345c7fe75dc13aab464b9d5ff64817ec40f680cde8e96f
audit_closed_accounts.py  b3205860e7b5f76abe3185cbd0621c75c4c6ec60fd7cee83da8bc4ebe45c563c
```

理由二属实。`audit_closed_accounts.py` 真实执行 `getSignaturesForAddress`、`getBlock`、
`getTransaction`、`getMultipleAccounts`：独立发现账户和签名、判存活/销户、decode token account
delta，再以 slot+owner 对照 SQD 边；RPC 失败、墙钟截断、checked=0 等均进入 `INVALID_SAMPLE`，不是
无条件放行。

### 4.2 最终定性

F2-02 定为**已知、已文档化的接受项**，本批不改逻辑：六个正式入口做完整 v4 归属校验；
`audit_closed_accounts` 是第七个、明确声明的弱覆盖例外，强度为 slot+owner＋RPC 抽样兜底，不能称为
transaction-exact。

## 5. F2-03：provenance 威胁模型边界

### 5.1 独立复核 — CONFIRMED，非 bug

`producer_history.py` docstring 明确登记值必须能由：

```text
git show <commit>:<script> | shasum -a 256
```

复现；本批也对两个 ACTIVE SQD producer 真跑复算并命中。因此 `collector_sha256` 是公开完整性哈希，
不是秘密、签名或链上证明。`validate_cache_meta` 只核 meta 字段、ACTIVE hash、摘要/行数格式；各消费端
再核 meta↔本地边/receipt 的一致性，整个路径没有证明“这些边确实由链上采集”的步骤。

### 5.2 处置

- `references/data-pipeline-solana-capture.md` 新增“v4 provenance 的保护范围与信任前提”；
- `PLAN.md` 文末新增“provenance 威胁模型与根治宣告边界”，并诚实注明当前 PLAN 原文没有工单所称的
  独立“根治宣告条件”段，再显式登记 A2 0/0 或 47 残差归因条件下仍适用的边界；
- `batch6_done.md` 文末追加 §11 勘误。真字节复核表明工单所称“建立归属根基/打断自证环”两个原句并不
  存在，故没有伪称改写原句，而是收窄 §3 F-02/F-03 与 §7 的 formal 身份含义。

定稿边界：防版本漂移、旧采集器产物误用、改装采集器冒名；假设 `data/` 可信；不防能同时伪造
边＋meta＋快照的本地写盘对手。抗主动伪造需签名或独立链上重验，是独立后续工程，本批没有实现。

文档提交：

```text
ae57331ad2bc61ac8e5611295f187d48fa9af210
批7 F2-03：收敛SQD归属防线威胁模型宣称
```

## 6. F2-04：reconcile TOCTOU

### 6.1 独立复核 — CONFIRMED

开工态 `cmd_reconcile` 源码 SHA-256：

```text
d114297e263d774f80909301cf31d1adbe412ed28c106160dd1763b6a9c95725
```

代码先对调用者传入的内存边执行 `_replay_with_evidence`，之后才对路径调用 `stat()` 和
`sha256_file()`；这是两次独立读取。注入在 replay 返回后替换 gzip，旧实现仍 `gate_pass=True`，红态
精确失败：

```text
AssertionError: reconcile 的逻辑摘要与物理哈希来自两次独立读盘
```

红态提交：

```text
6d62b237d1a36039ff6fa92934a5717d96d3bb69
批7 F2-04：固化重放双读盘TOCTOU红态反例
```

### 6.2 二选一结论：低成本修复

没有改 receipt schema，也没有改采集器。新增 `_read_frozen_formal_edges`：

1. 拒绝 symlink、缺失、空文件及非法 gzip/UTF-8/JSON/7 元组；
2. 一次 `read_bytes()` 冻结压缩字节；
3. 对同一字节像计算 size/SHA-256，并经内存 `BytesIO` 解压、规范化和排序；
4. 调用者传入的内存边必须与冻结边逐行一致；
5. 逻辑摘要、行数、余额重放和物理身份全部从该冻结像派生。

绿态提交：

```text
072717061655af18e4b6ed2da9929391b03a2352
批7 F2-04：绑定重放逻辑与物理身份到单次冻结读取
```

注入修复后，receipt/meta 里的逻辑与物理证据都指向替换前同一冻结字节；替换后的磁盘件与所记物理
hash 不同，下游物理锚核验会拒绝。定向 consumer、resume、collector meta、invariant 均通过。

## 7. 七个 Solana 边消费入口覆盖终表

| 入口 | 归属与边实物状态 | 最终定性 |
|---|---|---|
| `replay_edges.py` | `validate_cache_meta`＋实际摘要/行数；reconcile 物理/逻辑同次冻结读 | 完整正式校验 |
| `wave_scan.py` | `validate_cache_meta`＋实际摘要/行数 | 完整正式校验 |
| `flow_anomaly_scan.py` | 正式 Solana 分支复用 `wave_scan.load_sol` | 完整正式校验 |
| `entity_source_trace.py` | 正式 Solana 分支复用 `wave_scan.load_sol` | 完整正式校验 |
| `camp_series_provenance.py` | meta ACTIVE 归属＋receipt/meta 摘要/行数＋物理文件锚 | 完整正式校验 |
| `curve_cost.py` | 本批接入共享 meta 校验＋实际摘要/行数 | 完整正式校验 |
| `audit_closed_accounts.py` | 不读 meta；严格 7 元组，但只做 slot+owner＋RPC 抽样 | 文档化弱覆盖例外 |

因此最终口径为 **6/7 完整归属校验，1/7 文档化弱覆盖例外**，不得把 audit 一项包装成
transaction-exact。

## 8. F2-05：双 PATH 完整 SUITE

正常 PATH：

```text
python3 scripts/tests/run_all.py
121/121 PASS
全部通过
exit 0
```

不含 `rg` 的 PATH：

```text
env PATH=/usr/bin:/bin /usr/local/bin/python3 scripts/tests/run_all.py
121/121 PASS
全部通过
exit 0
```

两次都是原命令完整运行，Solana/EVM loopback 纵切片均 PASS；没有 skip、补回 `rg`、抽样运行或用
单测补跑冒充整套。F2-01 与 F2-04 新回归均由已登记 SUITE 项 `test_sqd_consumer_v4.py` 承载，因此
SUITE 文件数仍为 121，而不是另增一个脚本计数。

## 9. 六视角①②自审

### ① 字段来源审计

- curve 的正式身份统一来自共享 meta validator；collector 允许集合来自 git 可复现 producer history，
  不接受调用者自报“现役”；
- curve 摘要与行数来自逐行读取的实际 gzip，不信 meta 自报值；
- reconcile 物理 size/hash 与逻辑边、行数、余额全部来自同一压缩字节像；
- provenance 文档明确把“内部自洽”与“链上真实性”分开，没有把公开 hash 升格成签名；
- audit 的覆盖强度以实际索引键和 RPC 路径为准，不因输入是 7 元组就虚构 transaction-exact。

### ② 失败分支审计

- curve 对 meta 缺字段、未登记/revoked producer、摘要或行数错误、symlink、坏 gzip/JSON/行宽/类型、
  空边均拒绝，不产生成本结论；
- reconcile 对 symlink、缺失/空/坏 gzip、坏 UTF-8/JSON/7 元组、传入内存边与冻结磁盘边不一致均拒绝；
- reconcile 的新冻结读不改 receipt 字段，现有 camp provenance 物理锚继续校验落盘后漂移；
- F2-02 仍有 slot+owner 假覆盖可能，但已明确降级且 RPC 失败/无有效样本 fail-closed；
- F2-03 的主动伪造风险没有被“修复完成”措辞掩盖，也没有用未批准的新安全机制扩大范围。

## 10. 改动与提交台账

生产/测试改动：

- `scripts/solana/curve_cost.py`；
- `scripts/solana/replay_edges.py`；
- `scripts/tests/test_sqd_consumer_v4.py`。

文档改动：

- `references/data-pipeline-solana-capture.md`；
- `maintenance/repair-20260817-sqd-v4/PLAN.md`；
- `maintenance/repair-20260817-sqd-v4/batch6_done.md`；
- `batch7_workorder.md` 与本文件。

提交序列（不含本文件最后交付提交）：

```text
45be111 批7：收编opus二次盲审消化工单
5a9d9b8 批7 F2-01：固化成本重建归属缺口红态反例
abccb8e 批7 F2-01：补齐成本重建归属与边实物校验
ae57331 批7 F2-03：收敛SQD归属防线威胁模型宣称
6d62b23 批7 F2-04：固化重放双读盘TOCTOU红态反例
0727170 批7 F2-04：绑定重放逻辑与物理身份到单次冻结读取
```

## 11. 遗留、冻结范围与停止点

保留两项已定性边界，不冒充本批未完成的代码修复：

1. `audit_closed_accounts` 仍是 slot+owner＋RPC 抽样的弱覆盖例外；升级到 transaction-exact 需新增
   signature→`(slot,tx_index)` 映射，属独立工作。
2. 当前 provenance 假设 `data/` 可信，不抗可同时伪造边/meta/快照的本地写盘对手；签名或独立链上
   重验属根治宣告后的独立工程。

F2-04 不再列遗留；本批已用单次冻结读取闭合。相对 `2fb1924`：

- `scripts/solana/fetch_sqd_transfers_v2.py`：零 diff；
- VERSION、CHANGELOG：零 diff，版本仍为 `6.49.0`；
- 未跟踪 `opus_review_round1.md`：未读、未改、未暂存；
- 未 merge、未 push。

本文件提交后批 7 停止，等待验收方复核。
