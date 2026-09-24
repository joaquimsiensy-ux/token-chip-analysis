# 调度方本机实测（2026-09-24，只作设计依据，非 gate 证据）

## P1 Helius getBlock 压缩（W3 依据）
slot 326000396，`transactionDetails=full, encoding=json, rewards=false, maxSupportedTransactionVersion=1`，同一端点各请求一次（共约 20 credits）：

| 方式 | HTTP | 传输字节 | 解码后字节 | 响应头 |
|---|---|---|---|---|
| 明文 | 200 | 4,516,539 | 4,516,539 | 无 content-encoding |
| `--compressed` | 200 | 737,282 | 4,516,539 | `content-encoding: gzip` |

解码后 JSON 逐字节相等（1,908 笔交易）。压缩比 6.1×。

## P2 SQD 合并查询形态（W4 依据）
端点 `https://portal.sqd.dev/datasets/solana-mainnet/stream`，请求体＝现役 `_census_body` 加 `instructions:[{programId:[System],d4:["0x04000000"]}]` 与 `fields.instruction.transactionIndex`：

| slot | 类型 | 合并响应块键 | transactions | instructions | 单独探针 instructions |
|---|---|---|---|---|---|
| 326000396 | DEFECT_CANDIDATE（PYTHIA census refuted） | header, transactions | 482 | 键缺失（=0） | 0 |
| 426241113 | DEFECT_CANDIDATE（confirmed_nonce_defect） | header, transactions | 358 | 键缺失（=0） | 0 |
| 326000400 | HEALTHY | header, instructions, transactions | 402 | 53（仅 nonce 匹配项，每项只含 transactionIndex） | 53 |

结论：同一请求可同时得到全交易与 nonce 指令；`instructions` 只含匹配指令，零匹配时键缺失；每 slot 一次 SQD 请求即可替代「探针＋census」两次。
