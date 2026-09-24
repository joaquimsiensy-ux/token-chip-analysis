# Solana SQD 共享覆盖地图

本目录存放由 `scripts/solana/sqd_coverage_probe.py --full` 在可联网主机完成全史扫描后发布的、可复算的 SQD 覆盖资产。批 2 只交付生产程序与协议说明，不放首版数据；首版由 Fable 本机完成 ARC 全扫并验收后入库。

每版由三件组成：

- `<YYYYMMDD>.json`：资产描述与覆盖结论；
- `<YYYYMMDD>.counts.bin.gz`：逐 slot u8 计数，编码与 `sqd-solana-coverage/v1` 相同；
- `<YYYYMMDD>.blocks.bin.gz`：逐 slot u1 getBlocks 位图。

JSON 是 `sqd-solana-coverage/v1` 去掉案级 `mint` 后的超集，并至少包含：

```json
{
  "schema": "sqd-solana-shared-coverage-map/v1",
  "version": "YYYYMMDD",
  "generated_at": "UTC ISO-8601",
  "ttl_days": 30,
  "supersedes": null,
  "sqd": {
    "endpoint_fingerprint": "sha256",
    "metadata_normalized": {},
    "finalized_head_at_scan": 0,
    "query_body_sha256": "sha256"
  },
  "slot_counts": {
    "path": "YYYYMMDD.counts.bin.gz",
    "size": 0,
    "sha256": "sha256",
    "from_slot": 0,
    "to_slot": 0,
    "encoding": "u8:0=UNSCANNED,1=NO_HEADER,2=HEADER_ZERO_NONCE,n>=3→nonce_count=n-2，255饱和"
  },
  "blocks_bitmap": {
    "path": "YYYYMMDD.blocks.bin.gz",
    "size": 0,
    "sha256": "sha256",
    "from_slot": 0,
    "to_slot": 0,
    "encoding": "u1 per slot,1=getBlocks列出该slot"
  },
  "candidate_slots": [],
  "refuted_slots": [],
  "refuted_origin": [],
  "refuted_evidence": [],
  "canary": {
    "slots": ["恰好 64 个确定性 slot"],
    "counts": ["与 slots 等长的 u8 值"]
  }
}
```

复用是 fail-closed 的（不确定就拒绝复用）：TTL 必须未过期，端点指纹和稳定身份字段（数据集、起始块、实时标志）必须全等；还要在本次 SQD 请求中实测旧 `finalized_head_at_scan` 的块哈希（历史锚）相同、当前 finalized head（最终确认高度）不倒退、查询模板哈希一致，并逐 slot 重验全部 canary/candidate/refuted 已知点。动态的 head、高度别名和当前 head 哈希允许向前变化，不再参与整份字典全等；任何未知 metadata 字段仍会 fail-closed 回退全扫。64 个 canary 的计数也必须逐值相同。重验时值对不上＝整张地图作废全扫；个别请求被限流失败＝只有那几段不复用、单独重扫补上，其余照常复用。案级探针以 `shared_map.fallback_reason` 记录整体回退原因，以 `unverified_ranges` 和 `recheck_stats` 记录局部剔除及重试结果。`sample_ranges` 只是附加证据，永远不能补正式覆盖并集的洞。

驳回继承：`refuted_slots` 只能包含用源二进制重算出的原始候选，且 counts 必须为 2。后案成功复用时，逐点 recheck 仍为 2、落在实际复用区间且不在未验证段、原始证据尚在 30 天内，才分类为 `INHERITED_REFUTED`。该状态不进入候选或未确认集合，header_zero_nonce 仍计数；只有实际继承非空才增加 summary.inherited_refuted。`--resume` 不保留继承，恢复后按普通分类保守处理。

驳回继承复用源案的整块签名比对结论，本次只重新验证块头存在且 AdvanceNonce 计数仍为零；该条件不能识别 SQD 在同 slot 增删非 nonce 交易且计数保持零的变化，canary/历史锚/finalized-head 检查也不能消除此风险。本方案依赖来源可信及 SQD 已驳回 slot 的交易集合未发生不可见退化；不得把 `INHERITED_REFUTED` 表述为本案重新证明了完整性。

非空驳回集合的字段示例（摘要用占位说明，实际必须为对应长度的小写十六进制）：

```json
{
  "refuted_slots": [123456],
  "refuted_origin": [0],
  "refuted_evidence": [{
    "kind": "repair-census",
    "source_mint": "源案 mint",
    "probe_id": "hex16",
    "repair_gid": "hex16",
    "plan_digest": "hex16",
    "resolution_sha256": "hex64",
    "bundle_sha256": "hex64",
    "producer": {"path": "scripts/solana/sqd_gap_repair.py", "sha256": "hex64"},
    "refuted_count": 1,
    "origin_generated_at": "2026-09-24T00:00:00+00:00",
    "origin_asset_sha256": null,
    "asset_sha256": null
  }]
}
```

每个 refuted_origin 索引指向对应 slot 的证据项；refuted_count 必须等于该项的成员数，不能保留零成员项。首次 census 导出的 origin_generated_at 是源 coverage CURRENT 的 published_at。链式导出改为 kind=inherited，四个修复字段置 null，source_mint/probe_id/producer 归当前源 coverage，asset_sha256 指向直接来源资产；origin_generated_at 原样保留，重查和再导出均不续期。origin_asset_sha256 首次直接导出为 null，第一次链式导出填直接来源资产摘要，以后保留；它只用于溯源，不决定时效。

导出来源只认当前已发布 formal/live 修复代，或已验证 coverage 中的继承记录。存在修复 CURRENT 时必须明确选择互斥参数 `--repair-gid <gid>` 或 `--no-repair`；前者核验指定代与 CURRENT 一致，后者跳过自有驳回输出但仍核验当前修复来源并剔除 confirmed 冲突。refuted-only 不发布修复代，自有驳回不能导出，只能续传已继承部分。导出会报告非原始候选、confirmed 冲突、原始时效过期三类剔除计数。来源核验绑定 pointer/bundle/resolution、coverage、producer 与 census；不重放完整修复证据目录，来源可信是输入前提。

非空继承会随案级 coverage 发布原资产 JSON 的原始字节副本 `shared_map_source.json`。source_ref 以该发布代为基准绑定文件大小及摘要，副本先于 probe_id 落盘，经 coverage_map 和 CURRENT 形成绑定，不增加 pointer.inputs。副本参与幂等重发和冲突检查，沿用文件及目录 fsync 发布协议。跨机校验无需读取原资产绝对路径；副本只证明来源声明的成员关系及证据对应，不包含源二进制逐 slot 计数。源 counts=2 在探针加载原三件套时核验；离线校验独立核本案 counts、实际复用区间和完整 recheck 响应。部分继承仍携带来源完整 evidence，不能把其中 refuted_count 改为本案子集数；新导出资产才按最终成员重新编号和计数。

地图只按单 slot 的“有块头但零 AdvanceNonce”判定候选；禁止用连续游程长度或阈值代替。共享资产不得直接手改，重扫产生新版本并以 `supersedes` 串联。
