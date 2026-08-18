# 批 3 工单：消费端两态分立（正式 v4-only ＋ legacy 显式诊断入口）

> 先读同目录 `PLAN.md`、`batch1_done.md`、`batch2_done.md`。分支 `fix/sqd-solana-v4` 续作，
> 开工验证 HEAD＝批 2 交付 commit 且树干净。本批只改消费端；SUITE 全绿（或如实列批 4 依赖冲突）收批。

## 总原则（每个文件都要过）

- **正式路径**（新采/reconcile/READY/发布链）只认 v4 meta＋7 元组；**禁止按行长度静默嗅探格式**
  ——schema 判定来自 meta 或显式 CLI 标志；混合行宽（同文件 5/7 混杂）必须拒绝。
- **诊断路径**：显式 `--legacy-sol5` 标志才接受 5 元组；输出/receipt 强制标记
  `order_ambiguous`＋`non_formal`；legacy 模式**不得生成** v4 meta、v4 reconcile receipt 或
  任何 READY 链产物。三类合法场景：旧案事故复盘、slot+owner 级覆盖审计、对旧数据证明
  "为何不能精确溯源"。
- 7 元组读入语义：`instr_index >= 0` ⇒ `order_exact=True`（真指令级，未来 decode 线）；
  `instr_index == -1` ⇒ `order_exact=False`＋`order_granularity="transaction"`（交易间全序、
  交易内未决——多方交易必须能触发 order_ambiguous，禁止伪因果过账）。引用共享核常量，
  禁止在消费端复制字面值。

## 任务（逐文件）

### T1 `scripts/solana/replay_edges.py`（A2 硬闸链路，最高优先）

- 8 处元组解包升 7 元组；`:192` `len(edge) != 5` 改 `!= 7`（报错文案同步）；
  `:141/:231` meta schema 校验 v3→v4；`:200` 逻辑摘要随 7 元组行自然升级（meta 侧
  `edge_logical_sha256` 由批 2 采集器写入，两侧必须同算法——加一条两侧一致性测试）。
- 注意：**collector_sha256 对表 producer_history 的校验不在本批**（登记面属批 4，登记与
  消费校验同批闭环，防"表空拒一切"的批间死锁）。本批只保证 meta v4 结构校验。
- reconcile receipt（solana-reconcile/v3）是否升 v4：若 receipt 内容新增字段（如
  order_granularity 透传），schema 升 `solana-reconcile/v4` 并在 done 列出消费面清单
  （camp_series_provenance 等）；若仅输入格式变、receipt 结构不变，保持 v3 并在 done 说明
  理由。二选一，禁含糊。
- `--legacy-sol5` 诊断模式：接受 v3 meta＋5 元组，receipt 强制 `non_formal=true`＋
  `order_ambiguous=true`，且 cmd_reconcile 在该模式下**拒绝写正式 reconcile receipt 路径**
  （另存 `*.legacy.json` 或直接拒绝 reconcile 子命令——你选定并写明理由）。

### T2 `scripts/report/wave_scan.py`

- `load_sol`：删按行长度分支嗅探；正式路径仅 7 元组（校验逐行 len==7＋字段类型，
  `int(r[2])` 前显式类型校验——现状靠未捕获 ValueError 偶然拦截，改为设计好的 exit 2）；
  `instr_index` 语义按总原则；5 元组仅 `--legacy-sol5` 显式进入，DuckDB 表 `order_exact`
  全 False＋receipt 标记 non_formal。
- 它的 `wave-scan/v3` receipt：透传 `edge_order_granularity` 与 legacy 标记（升 v4 与否
  同 T1 的二选一纪律）。

### T3 传导件 `flow_anomaly_scan.py` / `entity_source_trace.py`

- 继承 wave_scan 的装载语义，验证传导（各自 CLI 补 `--legacy-sol5` 透传或显式拒绝——
  entity_source_trace 属溯源正式链，**建议直接拒 legacy**，写明）。
- `entity_source_trace.simulate`（`:419` 附近）：确认 `order_exact=False` 的同桶边正确落
  order_ambiguous 分支（这是 @CX ③伪因果修正的落地点，必须有一条多方交易 fixture 证明）。

### T4 `scripts/solana/audit_closed_accounts.py`

- `:99-104` 逐行吞异常改为报行号整次失败（全库唯一静默错读点）；
- 路径改用共享核 `soltx_cache_paths`（修旧小写 mint 路径脱节）；
- 它是 slot+owner 覆盖审计（legacy 合法场景②）：支持 `--legacy-sol5`，默认 v4。

### T5 `scripts/solana/curve_cost.py`

- 解包升 7 元组＋共享核路径；确定它属正式链还是诊断链并写明（内盘成本重建——若正式链
  则 v4-only）。

### T6 `scripts/lib/camp_series_provenance.py`

- `:592` schema 校验 v3→v4（与 T1 的 receipt 版本决策联动）；边文件 size/sha256/digest
  锚定逻辑本身格式无关，确认零行为回归。

### T6b meta 字段更名的消费端读点核查（批 2 验收新增）

批 2 的 v4 meta 用 `finalized_upper_slot` **替代**了 v3 的 `collection_upper_slot`。
rg 全库列出 `collection_upper_slot` 的全部读点（含 replay_edges、camp_series_provenance、
scan-schemas.md:565 的 sol-rows consumer 契约"edge_extrema.slot ⊆ collection_window"等），
逐一适配 v4 字段名或写明该读点仅服务 legacy；漏一处＝新数据在消费端撞 KeyError 或静默
读 None。处置清单进 done。

### T7 绑消费端的既有测试随刀

`test_wave_scan.py`／`test_flow_anomaly.py`（5 元组 fixture 升 7）、`test_repair_batch_c.py`
（reconcile 链真产物 fixture 重生成）、`test_repair_batch_d.py:1028+`、
`test_review_resume_integrity.py`（消费面）、`test_entity_source_trace.py`（exact 双形态
语义核对：instr=0 fixture 保持 exact=True 合法）。原则同批 2：登记面冲突留批 4，如实列出。

## 禁动范围

采集器本体与合并器（批 2 已定型，本批发现采集侧问题记 done 遗留、禁顺手改）；
`producer_history.py`／`invariant_manifest.json`（批 4）；VERSION/CHANGELOG（批 5）；
EVM 侧；任何案目录。

## 交付物

`batch3_done.md`：逐文件改动台账、receipt 版本二选一决策及理由、legacy 入口三场景验证
记录、order_ambiguous 多方交易 fixture 证据、红→绿证据（吞异常改 fail-closed 等）、
SUITE 结果、六视角①②自审、遗留事项（批 4 依赖冲突清单）。完成即停，不开批 4。
