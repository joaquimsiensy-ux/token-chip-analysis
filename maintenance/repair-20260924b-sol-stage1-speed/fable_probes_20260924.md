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

## P3 SQD 三组查询内容对照（W4 复核 r2 必改项，2026-09-24 补测）
同一 slot 分别发 probe-only（仅 instructions 选择器）、census-only（仅 transactions 选择器）、combined（两者），`--compressed`，529 时退避重试（服务端过载，census-only 单独请求也出现过 529，与合并无关）。比较：三组 `header` 全等；combined 与 census-only 的 `transactions` 规范化 JSON 全等；combined 与 probe-only 的 `instructions` 规范化 JSON 全等（含重复项保留）。

| slot | 类型 | HTTP(probe/census/combined) | 块头三方全等 | tx 全等 | instr 全等 | tx 数 | instr 数 | combined 有 `instructions` 键 |
|---|---|---|---|---|---|---|---|---|
| 326000400 | 有匹配 nonce 指令的健康块 | 200/200/200 | 是 | 是 | 是 | 402 | 53 | 是 |
| 326000396 | 有块头零匹配（PYTHIA census refuted） | 200/200/200 | 是 | 是 | 是 | 482 | 0 | 否（键缺失） |
| 326000391 | 有匹配 | 200/200/200 | 是 | 是 | 是 | 268 | 1 | 是 |
| 326000393 | 有匹配 | 200/200/200 | 是 | 是 | 是 | 207 | 4 | 是 |
| 326000395 | 有匹配 | 200/200/200 | 是 | 是 | 是 | 301 | 12 | 是 |

说明：probe-only 与 combined 的 `instructions` 都只含匹配 AdvanceNonce 的指令（每项仅 `transactionIndex`），非匹配指令不可由该查询观察；「健康块同时含其他指令」由交易数（402）远大于匹配指令数（53）间接支持。范围查询 326000380–326000440 全部 61 个 slot 均有块头，本段未含无块头样本（见 P4）。
原始结果：调度方 scratchpad `sqd3_results.json`/`sqd3b_results.json`（不入仓库）。
