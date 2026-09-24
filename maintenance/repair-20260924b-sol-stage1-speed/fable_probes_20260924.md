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

## P4 无目标块头样本（W4 复核 r2 建议项）——**未取得，且调度方一次误判已订正**
初版记录曾把范围查询 326000000–326000999 中未返回的 127 个 slot 当作「SQD 无块头」，后对其中 326000873/326000874 单 slot 三组查询均 HTTP 200 且返回 1 块（probe 305 B / census 38,705 B / combined 38,924 B）——**它们有块头**。根因：SQD stream 单次响应有大小上限，1000-slot 范围查询被截断成分页尾巴，不是缺块（现役探针按 450-slot 分页正是为此）。结论：本工程未取得 SQD 无目标块头的在线样本，`present=False` 路径由 W4 §2.5 离线 MISSING_BLOCK 正反例覆盖。教训：范围查询判缺块必须按流分页游标续拉，不能以单响应缺失当缺块。

## P5 W3 调度方本机联网验收（施工 commit 6b36dcd 后，2026-09-24）
curl 8.7.1 (x86_64-apple-darwin26.0) libcurl/8.7.1 SecureTransport LibreSSL/3.3.6 zlib/1.2.12。同一 finalized slot 326000396、相同 getBlock 请求体（transactionDetails full、encoding json、rewards false、maxSupportedTransactionVersion 1）、同一 Helius 端点：

| 方式 | HTTP | rc | size_download | time_total | Content-Encoding | result 规范化 sha256（前 16） |
|---|---|---|---|---|---|---|
| identity | 200 | 0 | 4,516,539 | 3.21 s | 无 | 349090c1147eebdb |
| `--compressed` | 200 | 0 | 736,729 | 2.54 s | gzip | 349090c1147eebdb |

解析后 result 规范化摘要相等；实际协商编码 gzip；传输字节 6.1×。不用 ledger.bytes 衡量传输节省。W3 收官：施工 commit 6b36dcd，本机定向 8 项 PASS（含施工方受禁读拦截未跑成的 `test_sqd_gap_repair.py` rc=0），盲审 r1 PASS（`blind_W3_reply_r1.md`），run_all 结果见 `W3_acceptance.md`。
