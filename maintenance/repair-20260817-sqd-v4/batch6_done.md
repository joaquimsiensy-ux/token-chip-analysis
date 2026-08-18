# 批 6 完成记录：SQD Solana v4 opus 盲审消化

日期：2026-08-18

分支：`fix/sqd-solana-v4`

开工基线：`801f7cca8cbf24e0b2e2f0cd6d751d28971f7148`

工单：`batch6_workorder.md`，SHA256 `a52effca903677240bd7c1f2338a0e6a76aade01cc1c4f9050dc228bb5afdfeb`

## 1. 收批结论

- F-01 至 F-07 均经独立可运行反例复核，结论全部为 **CONFIRMED**；没有把工单原判直接当证据。
- 每项均先提交红态，再提交绿态；F-05 采集器变更另走 producer 两步登记。
- NOTE-02 低成本顺修并完成红绿；NOTE-01、NOTE-04 有可运行证据，但不在本批做跨层重构，列入遗留。
- 完整 `scripts/tests/run_all.py` 在允许 loopback 的验收环境中 **121/121 全绿，exit 0**。
- ARC 外部案目录全程只读；收批哈希、大小、mtime 与开工冻结值逐项相同。
- 未 merge、未 push。

## 2. 开工与提交纪律

工单先于任何生产改动收编：

```text
e78ade0 批6：收编opus盲审消化工单
```

红绿提交序列：

```text
f07b695 批6 F-01：固化跨链formal闸红态反例
794f7b9 批6 F-01：统一全链formal顺序语义
039310c 批6 F-02：固化元数据洗白红态反例
369fa47 批6 F-02：前置校验采集逻辑证据
5cb1f25 批6 F-03：固化补零洗白红态反例
9e66f28 批6 F-03：绑定Solana正式边采集身份
d7fcd2d 批6 F-04：固化静置仓死字段红态反例
d044f4d 批6 F-04：封死静置仓非正式产物发布
86552e2 批6 F-05：固化外排解析差异红态反例
47b3620 批6 F-05：收严外排边行类型校验
a9d45af 批6 F-05：登记收严后的SQD采集器
433d8b0 批6 F-06：固化五元组构造漏扫红态反例
41290aa 批6 F-06：补齐五元组构造扫描白名单
b4e8532 批6 F-07：固化旧损失口径红态反例
5705432 批6 F-07：补记旧损失口径勘误
04f116f 批6 NOTE-02：固化指令级边放行红态反例
431abf6 批6 NOTE-02：统一重放交易净额指令哨兵
```

## 3. Finding 逐条复核与修复

### F-01 — CONFIRMED

真实 DuckDB `edges` 表经 `wave_scan.py --duckdb` 产出：

```text
edge_order_granularity=source-defined
non_formal=false
```

修复前，同一报告被 adjudication 与 handoff formal 闸拒绝；这证明 producer 与三个 consumer 的
formal 顺序白名单不一致。红态用例真跑 DuckDB producer，再进入 adjudication template、handoff
generate/verify，不以手写报告替代 producer。

修复：新增 `scripts/lib/wave_contract.py` 作为唯一机器契约，formal 粒度统一为
`transaction/instruction/log/source-defined`，三个 consumer 复用 `has_formal_wave_semantics`。

### F-02 — CONFIRMED

从合法 v4 meta 删除 `edge_logical_sha256/edge_rows`，保留真实登记 collector 哈希；修复前
`cmd_reconcile` 会用消费期内存边回填缺失字段并签出 `gate_pass=true`。这使“不带采集证据的 meta”
可以被下游洗白。

修复：新增共享 `sqd_cache_identity.py`，v4 meta 在任何消费前必须已有 collector 签出的逻辑摘要与
行数；reconcile 只做纯比较，不再首次建立证据。破坏注入新增第 4 项 `missing_logical_evidence`，
命中精确错误：

```text
SQD v4 meta.edge_logical_sha256/edge_rows 为 collector 必填证据
```

### F-03 — CONFIRMED

将旧 5 元组机械补成 `[ts,slot,0,-1,from,to,amt]`，不提供 meta 且不传 `--legacy-sol5`；修复前
`wave_scan.py` exit 0，并签出 formal transaction 报告。`non_formal` 只由 CLI 开关自报，无法证明
边的采集身份。

修复：Solana wave/flow/entity 三入口统一要求 `--sol-cache-meta + --mint`；消费前校验登记 producer、
逻辑摘要、行数及实际边内容。`non_formal` 改由加载器验证出的身份派生；handoff 同时冻结 meta、mint
与共享校验算法。

### F-04 — CONFIRMED

在一份 release-gate 零错误夹具的 `dormant_warehouse_audit.json` 中加入
`non_formal=true/order_ambiguous=true`，修复前仍为零错误；对照把绑定 wave 的 `non_formal` 改真，
发布闸会拒绝。故缺陷是 dormant 两字段死掉，不是闸整体失活。

修复：`check_dormant` 对两个字段均要求显式 `false`；缺字段、legacy 或顺序歧义一律阻断。

### F-05 — CONFIRMED

同一非法 part 分别喂 MemMerger 与 ExtMerger，六类输入均出现 `Mem=REJECT / Ext=ACCEPT`：

```text
ts="0"; slot="200"; tx_index="7"; instr_index="-1"; amt="5"; amt="007"
```

其中 `amt="007"` 被外排路径拼成未加引号的 `007`，产出语法非法 JSON。修复后外排路径校验五个
整数位置的 JSON 类型与规范十进制文本；合法超 int64/uint64 整数字面量仍逐字节保真。

### F-06 — CONFIRMED（验收面缺口，不是可达生产缺陷）

原登记正则对 `fetch_sqd_transfers_v2.py:448`：

```text
edges.append((ts, slot, f, t, amt))
```

返回 rc=1；修正为同时覆盖赋值与 tuple constructor 后 rc=0。该构造位于
`HyperSyncFetcher.scan_area`，但 `run(hs_cfg=...)` 与 CLI `--hypersync` 都在首个业务请求前 exit 2，
因此判为不可达死代码。

处置采用工单 a：不再改采集器；修正 `grep_legacy_whitelist.md` 的机器正则，并登记 1 处死代码豁免
及两条前置硬拒证据。排除 3 个 legacy 解析白名单与该死代码豁免后，正式可达面仍为零命中。

### F-07 — CONFIRMED

`batch2_workorder.md` 原行仍把“ARC 案 124,816 条”写在纯 DISTINCT 缺陷后，未指向后续反证；
`PLAN.md` 尾部勘误与 `batch4_done.md §6.3` 已证明该数字是两版全史边表的混合差值。

遵守历史件不改写边界：只在原行追加勘误指向与当前口径——域内机械可证为
**11,502 行 / 8,487 组**；其余历史文本不动。

## 4. F-04 marker 全仓审计

生产代码 `rg` 清点结果：

| marker | producer | consumer | 结论 |
|---|---|---|---|
| wave `non_formal` | `wave_scan.py` | `wave_contract.py`；再由 adjudication、handoff、release gate 调用 | 活字段 |
| wave `order_ambiguous` | `wave_scan.py` | `wave_contract.py`；同上 | 活字段；只要求布尔，formal 可声明顺序层级内歧义 |
| dormant `non_formal` | `audit_closed_accounts.py` 正常与早退两路径 | `audit_release_gate.check_dormant` | 本批接通，必须显式 false |
| dormant `order_ambiguous` | `audit_closed_accounts.py` 正常与早退两路径 | `audit_release_gate.check_dormant` | 本批接通，必须显式 false |
| entity trace `order_ambiguous` | `entity_source_trace.py` terminal reason | `handoff_manifest.py` 对 terminal 三元组计数 | 活枚举，不是 dormant 顶层 marker |

上述两类 marker 当前没有“写出但无人消费”的剩余字段。

## 5. Producer 两步登记

采集器只在 `47b3620fb2f739b9a609b543572e0b69559038b0` 修改；登记提交没有再改采集器。

复算命令与结果：

```text
git show 47b3620:scripts/solana/fetch_sqd_transfers_v2.py | shasum -a 256
a94b193b94ba8872e4d6aa4915ff7d89ef6cc438d7f2c6c0744ebc33212d9bae  -
```

`a9d45af` 将该哈希以 `sqd-solana-cache/v4 / ACTIVE` 登记。前一 ACTIVE 哈希
`2589f6a3…` 仍对应合法历史 v4 缓存，没有撤销；测试夹具改为允许同协议多个 ACTIVE producer，
而不是错误断言集合长度恒为 1。

F-06 采用文档白名单方案，之后没有再次改动采集器，因此无第二次登记义务。

## 6. NOTE 评估

### NOTE-02 — 已顺修

修复前 `replay_edges._validate_formal_edge` 接受 `instr_index >= -1`，共享
`spl_edge_core.validate_edge_row` 只接受 transaction-net 哨兵 `-1`；当前又没有 instruction 级
登记 producer。红态证明 `instr_index=0` 可进入 replay，绿态统一为严格 `== -1`。

### NOTE-01 — 遗留，已证实

可运行注入在 `_replay_with_evidence(edges)` 返回后替换磁盘 gzip；`cmd_reconcile` 仍返回 true 并签出
`gate_pass=true`，同时 meta 的逻辑摘要属于旧内存边、物理文件哈希属于新磁盘边：

```text
cmd_return True; gate_pass True
meta_logical_is_old True
disk_logical_is_new True
logical_mismatch_survived True
```

根因是内存 replay 与随后磁盘 `sha256_file` 不是同一次冻结读。可靠修复需要把 load、replay、物理
身份绑定到同一文件描述符/冻结快照，并调整调用链与收据协议；不属于低风险顺修，交二次盲审。

### NOTE-04 — 遗留，已证实假设边界

当前共享 `pair_tx({'S': -12, 'R': 10})` 的确定性输出为：

```text
[('S', 'R', 10), ('S', ZERO, 2)]
```

若 Token-2022 withheld 变化没有作为独立 owner delta 出现在摄取响应里，差额会被表达成销毁边。
现有完整 fixture `{S:-12,R:+10,FEE:+2}` 可正确配成 `S→R 10 + S→FEE 2`，但不能证明真实通道总会
提供 withheld 状态。修复需要新增 Token-2022 fee/withheld 原始字段来源与协议语义，不能仅改贪心配对。

## 7. 六视角①②自审

### ① 字段来源审计

- formal wave 粒度由 producer 报告字段进入共享机器白名单，不再由各 consumer 私有枚举裁决；
- Solana formal 身份由登记 producer、meta 逻辑摘要/行数与实际边复算共同证明，CLI 不再自报 formal；
- dormant 的两个标记由审计 producer 正常/早退路径写出，release gate 强制消费，不以 coverage 自报替代；
- F-05 外排路径在原 JSON token 层校验类型与十进制文本，不以 DuckDB cast 后的值替代输入类型；
- producer 新哈希只从已提交对象 `git show` 复算，未登记 dirty worktree 哈希。

### ② 失败分支审计

- 缺 meta、缺逻辑摘要/行数、未登记 producer、摘要/行数不符均在正式消费前拒绝；
- legacy/补零 Solana 边不能通过 wave/flow/entity 的 formal 身份闸；
- dormant 缺 marker、non-formal 或顺序歧义都阻断发布；
- ExtMerger 对非法标量与 MemMerger 等价抛错，异常时临时 gzip 仍清理，不发布半件；
- 四项破坏注入都验证目标分支与精确错误，不把任意非零退出笼统算命中；
- 首轮 SUITE 的两项 loopback `EPERM` 如实保留为环境失败，随后原命令在允许绑定的环境全量重跑，
  没有跳过或单独补跑后冒充整套全绿。

## 8. 验收证据

### 8.1 完整 SUITE

```text
python3 scripts/tests/run_all.py
121/121 PASS
全部通过
exit 0
```

首轮受限沙箱为 119 PASS + 2 FAIL；仅两条本地纵切片在
`ThreadingHTTPServer(('127.0.0.1', 0))` 处 `PermissionError: [Errno 1]`。允许 loopback 后原命令完整
重跑，Solana 与 EVM vertical slice 均 PASS，最终 121/121。

本套包含：批 6 新增回归、真实 EVM/DuckDB wave→formal gates、SQD merge 八组契约、Batch C 227
checks、handoff 68 项、Batch D、R9 双链纵切片、docs/manifest/invariant/contract/version 全部守卫。

### 8.2 破坏注入

```text
python3 maintenance/repair-20260817-sqd-v4/tools/destructive_injection_verify.py
status=PASS
source_unchanged_after=true
```

四项均命中目标分支：单逻辑字节、legacy v3 meta、未登记 collector 哈希、缺 collector 逻辑证据。

### 8.3 ARC 只读证明

| 文件 | SHA256 | size | mtime(epoch) |
|---|---|---:|---:|
| `collector_part_manifest.json` | `bc72747223aa732f030c9badc982785745d8daba3c605b07abccbf2ac43c30b2` | 568819 | 1786935692 |
| `holders_owners.json` | `6dd0bb4c8061871586e0433eba1a9eb3e6dacc49f778a118a18ef5ca944d4abe` | 2694062 | 1787012665 |
| `owner_authority_repairs.json` | `c40bfe79bb7beb241410e7d85d24473fcac0f2963d26c56562ae2c8bdde585fa` | 455 | 1786935936 |

三项与开工冻结值完全一致；没有向 `/Users/uravvv/Documents/5.6筹码分析/ARC分析` 写入文件。

## 9. 环境与停止点

- 本仓库源树没有 skill 指令所述 `sync-from-cc.sh` 或 `SYNC.md`，因此没有可执行的同步步骤；未伪造同步成功。
- `batch6_done.md` 为本批最后交付物；其提交完成后停止，等待 opus 二次攻击型盲审。
- 不 merge，不 push。
