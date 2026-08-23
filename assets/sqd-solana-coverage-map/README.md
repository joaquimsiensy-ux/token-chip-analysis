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
    "metadata_normalized": {}
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
  "canary": {
    "slots": ["恰好 64 个确定性 slot"],
    "counts": ["与 slots 等长的 u8 值"]
  }
}
```

复用是 fail-closed 的：TTL 必须未过期，SQD `metadata_normalized` 与端点指纹必须一致，全部已知 candidate/refuted slot 必须逐 slot 复核，64 个 canary 的计数必须逐值相同。任一条件不成立，案级探针记录 `shared_map.fallback_reason` 并升级为全扫。`sample_ranges` 只是附加证据，永远不能补正式覆盖并集的洞。

地图只按单 slot 的“有块头但零 AdvanceNonce”判定候选；禁止用连续游程长度或阈值代替。共享资产不得直接手改，重扫产生新版本并以 `supersedes` 串联。
