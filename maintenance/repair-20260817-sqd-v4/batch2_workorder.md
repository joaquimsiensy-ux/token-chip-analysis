# 批 2 工单：采集器 v4——7 元组落盘＋交易身份去重＋owner 错账修＋meta v4

> 先读同目录 `PLAN.md` 与 `batch1_done.md`。分支 `fix/sqd-solana-v4` 续作，开工验证
> HEAD＝批 1 交付 commit 且树干净。本批只改采集侧；SUITE 全绿收批。

## 批间风险登记（开工必读）

批 1 改变了 pair_tx 等额场景的配对序。若在本批 v3 硬拒落地前对旧 v3 缓存续采，同一交易
新旧配对不同 → 五字段 DISTINCT 不识别 → 双计。当前无活续采场景，但**本批完成前全库禁止
动用 fetch_sqd_transfers_v2 做任何真实增量采集**；本批的 v3 前置硬拒正是永久关闭此窗口的机制。

## 任务

### T1 【修复工单·五栏】DISTINCT 吃边（主缺陷）

```text
bug：合并阶段按五字段 DISTINCT 去重，同 slot 等额的不同真实交易被误删（ARC 案 124,816 条）
1. 不变量：不同交易的边永不因内容相同被合并；同一交易被重复采集时恰保留一份；
   同一交易身份出现内容冲突的两个版本时必须硬失败（禁静默取并集）。
2. 同族清单：rg 全库列 DISTINCT/去重实施点——已知 ExtMerger（fetch_sqd_transfers_v2.py:771
   附近）与 MemMerger（set 语义）两路径；window_fetch.py 若有自身去重面一并列出；
   全部升级为同一交易身份契约。
3. 三件套测试：
   a. 原反例（先红）：同 slot 等额两笔不同 tx_index 的交易 → 现行 5 元组+DISTINCT 合并成
      1 行（红），v4 保留 2 行（绿）——ARC 毒场景最小重现，进 SUITE 作永久回归。
   b. 同族变体：同一交易完整出现在两个 part（模拟重叠采集）→ 恰留一份；
      同一 (slot,tx_index) 两个 part 中内容不同（模拟数据源冲突）→ 硬失败退出非零。
   c. 失败分支：合并器对 5 元组旧行/混合行宽输入必须拒绝（fail-closed），不得静默解析。
4. 新建代码自审：六视角①②过一遍写进 done。
5. 归因预判：历史漏检（v2 采集器设计期即埋入；scan-schemas.md:17 规矩早已有之而实现违反）。
```

实现要点：
- 落盘行升官方 7 元组（import 共享核 `EDGE_SCHEMA_FIELDS/INSTR_INDEX_TX_NET` 常量），
  `instr_index` 恒 −1；`ts,slot` 在前、`from,to,amt` 位置按官方序 `[ts,slot,tx_index,
  instr_index,from,to,amt]`。
- 去重键＝交易身份：finalized 区间内 `(slot, tx_index)`；对每笔交易的完整边集合算排序后
  `tx_digest`，同身份同 digest 留一、异 digest 硬停。digest 算法与存放位置（merge state /
  聚合查询）由你设计，但不变量测试必须逐条覆盖；Mem/Ext 两路径逐字节一致契约保持并升 7 元组。
- `test_sqd_merge_equiv.py` 契约重写：旧契约①"跨格式按五字段去重"已固化缺陷行为，升级为
  交易身份契约（保留其余契约：超 int64 保真、原子落盘、伪 scan-fail、尾段零行）。
- 排序键改 `(slot, tx_index, from, to, amt)` 全序。

### T2 【修复工单·五栏】owner-authority 错账（第二缺陷）

```text
bug：owner = postOwner or preOwner——token account 同一成功交易内换 owner 时 delta 全记
     postOwner，preOwner 的 preAmount 凭空蒸发（ARC 案 codex 正在验证其残余解释力）
1. 不变量：owner 级账本对每条 tokenBalance 记录满足 preOwner 减 preAmount、postOwner 加
   postAmount（同 owner 合并为 post−pre）；任何记录不得因 owner/金额字段异常被静默跳过。
2. 同族清单：parse_owner_delta（spl_edge_core.py，批 1 注明的旧债）唯一实现；rg 确认无他处。
3. 三件套测试：
   a. 原反例（先红）：owner 变更记录（pre_owner=A amount=10 → post_owner=B amount=12）
      现行为只记 B:+2（红）；修后 A:−10 / B:+12（绿）。
   b. 同族变体：owner 变更且金额不变；owner 变更叠加同交易内其他转账；Token-2022
      transfer-fee/withheld 场景独立 fixture。
   c. 失败分支：非零 preAmount 缺 preOwner／非零 postAmount 缺 postOwner→硬失败；
      非法/负数金额→硬失败；同 (tx_index, account) 重复记录→检测并硬失败（防双计）。
4. 新建代码自审：同上。
5. 归因预判：历史漏检。
```

实现要点（七硬规则全落）：请求体新增 `"account": True` 并核验 `account/preMint/postMint`；
只把 mint 等于目标 mint 的一侧计入（close+reinit 换 mint 场景另一 mint 的 postAmount 不得
计入）；ZERO 供给边保留哨兵机制，meta 标注供给增量来源＝tokenBalances 推定（单笔指令级验证
不做，A2 供给闭合闸兜底——此裁量已批准，写进 done 供盲审攻击）。

### T3 输入卫生 fail-closed

`tx_index` 必须非布尔非负整数（None/缺失→该段采集失败重试或整体退出非零，禁聚到 None 键）；
金额解析失败/owner 缺失从静默跳过改为整段失败。批 1 parse_owner_delta 的静默返回 None 旧债
在此关闭。

### T4 meta 升 `sqd-solana-cache/v4`

新增字段：`collector_sha256`（**启动冻结＋finalize 前复验**，不一致拒收尾——Solana 侧归属
防线）、`edge_schema`（7 元组字段序，引共享核常量）、`edge_semantics`、`order_granularity`、
`dedupe_identity`（如 "slot-txindex-digest/v1"）、`finalized_upper_slot`（采集上界 ≤ finalized
slot，接现有 SolanaAttestedSession/dataset adapter 机制）。`collector` 字符串升
`fetch_sqd_transfers_v2.py/v4`。

### T5 前置硬拒与通道收口

- v3 meta / 旧 `.parts`（5 元组内容）在创建或读取 v4 parts **之前**检测并硬拒（exit 2，
  报"格式升级需全量重采，旧缓存请改名归档"）；resume 场景同样拒（防混格式进合并器）。
- **HyperSync 分支硬禁**：v4 下 `--hypersync` 直接 exit 2 并说明通道已禁用（在案纪律），
  连带清理其 docstring 声明，不留第二种隐含五元组出口。
- `window_fetch.py` 生产者同升 7 元组（与采集器同一共享核常量；其 receipt schema 若绑行格式
  一并升版）。

### T6 绑采集器行为的既有测试随刀

`test_sqd_merge_equiv.py`（T1 重写）、`test_r9_batch3_solana_observation.py`（meta collector
断言 v3→v4）、`test_review_resume_integrity.py`（v3 meta 夹具）等——原则：**绑采集器产出行为
的测试本批改；绑消费端读入的测试留批 3；登记面（invariant_manifest/producer_history）留批 4**。
若批 4 前 SUITE 因登记面与新 schema 冲突无法全绿，将冲突项如实列入 done 的遗留事项并给出
最小豁免说明（禁静默改登记面）。

## 禁动范围

消费端七文件（replay_edges/wave_scan/flow_anomaly_scan/entity_source_trace/
camp_series_provenance/audit_closed_accounts/curve_cost，批 3）；`producer_history.py`／
`invariant_manifest.json`（批 4）；VERSION/CHANGELOG（批 5）；EVM 侧；任何案目录。

## 交付物

`batch2_done.md`：五栏台账×2、红→绿证据原文（T1a/T2a 两组）、同族 rg 清单、meta v4 样例、
两路径等价证明、SUITE 结果（全绿或如实列冲突项）、六视角①②自审、遗留事项。完成即停。
