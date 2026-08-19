# 工单 U1 正式施工报告

## 1. 结论

U1 已按勘误后的工单完成施工，未 commit、未 push。当前基线仍为 `0ec6d1e2365c339d200fc26d17344f962fbdb7a9`。

- 新 producer 只签发 anchor-plan v3；receipt schema 保持 v2。
- v3 余额点使用 `balance_block_source` 正向白名单，balance/tx 采用严格 XOR。
- v2 存量 plan 不重签；重放时只投影重算结果，并在剥离机器字段前执行 v3 形态断言。
- `e5168a...` 与 `1a461169...` 两个历史 producer 哈希已进入 git 可复现登记表。
- 新测试旧态 `0/12 PASS`，实现后 `12/12 PASS`。
- 全量入口共 115 项：113 PASS；仅工单预告的两个 loopback vertical slice 因沙箱 `socket.bind` EPERM 失败，除此之外零失败。
- NES 三份真实 v2 plan/receipt 均已通过历史 producer 深验和完整 dry-run 语义重放。

## 2. 改动摘要（逐文件）

### `scripts/lib/anchor_plan.py`

将 `PLAN_SCHEMA` 升为 v3；签发前按 schema 分派，v3 调用共享机器契约，v2 保留原 legacy kind 路径；块号上界和 tx block 必填约束保持。

### `scripts/lib/anchor_selection.py`

所有日终余额点增加 `balance_block_source=day_end_block`；最终门槛边缘点增加 `balance_block_source=final_block`；tx 点不增加该字段。中文 kind 文案未改。

### `scripts/lib/anchor_point_contract.py`

新增 v3 正向白名单入口 `balance_block_source_of`：严格区分 balance/tx，校验枚举、禁止键、final 源位置和日期约束、day-end 块号类型；保留 v2 的 `is_legacy_final_block_edge_point`。

### `scripts/lib/time_spotcheck.py`

producer 常量升 v3，consumer 接受 v2/v3；加载 plan receipt 时只接纳当前 producer 或登记的 v2 历史哈希。classify 与 balance query 按 schema 分派。语义重放对 v3 精确比较；对 v2 仅投影重算点，先逐点过 v3 XOR 契约，再只删除机器块源字段。

### `scripts/lib/receipt_validate.py`

`validate_receipt` 增加可选参数 `allowed_producer_hashes=None`。默认仍只认当前脚本哈希；显式传集合时，允许集合与当前哈希的并集，未登记哈希仍拒绝。

### `scripts/lib/producer_history.py`（新建）

新增六字段 producer 历史登记表和 `historical_producer_hashes(script, protocol)`；ACTIVE 需同时匹配 script/protocol，任何 REVOKED 同哈希执行跨 protocol 的 hash-wide 否决。

### `scripts/report/shared_release_receipt.py`

深验 plan 点时按 v2/v3 分派；plan schema 接受 v2/v3，receipt 的 `plan_schema` 必须与 plan 精确相等。anchor producer 的 envelope 校验和 repo ref 校验均采用“当前 + 登记历史”策略，其他 producer 默认边界不变。

### `scripts/tests/invariant_manifest.json`

anchor producer 改登 v3；time/shared consumer 同时登记 v2/v3；按 `--dump-actual` 如实登记 `anchor_plan.py`、`anchor_point_contract.py` 的 v3 consumer 面，并将 time_spotcheck producer 面同步为 v3 + time receipt。

### `scripts/tests/test_anchor_plan_v3.py`（新建）

实现工单 12 组矩阵：全链正例、枚举/位置/禁键/类型/缺字段/XOR 负例、kind 文案免疫、v2 全链兼容、投影前断言、producer 历史/REVOKED/默认边界/git 考证。

### `scripts/tests/test_time_spotcheck.py`

- 原 118 行与 136 行保留：两处是手写 v2 攻击 fixture 的 plan/receipt 配对，用于兼容路径回归。
- 原 309 行改为 v3 producer 对账，并同时限定 `script == EXPECTED_PLAN_PRODUCER`，避免 time_spotcheck 自身代码面也含 v3 时产生伪多条。

### `scripts/tests/test_r9_batch1_boundaries.py`

真实 producer 现产 schema 的断言由 v2 改为 v3。

### `scripts/tests/run_all.py`

只新增 `test_anchor_plan_v3.py` 注册行及说明注释。

## 3. 先红后绿实证

### 红态命令

生产代码未改前，先新增测试并运行：

```bash
python3 scripts/tests/test_anchor_plan_v3.py
```

真实结果：`exit=1`，`anchor-plan v3: 0/12 PASS`。关键输出：

```text
FAIL test_02_bad_source_enum_rejected: ... unexpectedly accepted
FAIL test_03_final_source_in_matrix_rejected: ... unexpectedly accepted
FAIL test_04_final_source_forbidden_keys_rejected: accepted=['day_end_block', 'block', 'tx']
FAIL test_05_day_end_block_shape_rejected: accepted=['missing', 'type=str', 'type=bool']
FAIL test_06_tx_with_balance_source_rejected: ... unexpectedly accepted
FAIL test_07_balance_without_source_rejected: ... unexpectedly accepted
FAIL test_11_strict_xor_rejections: accepted=['balance-with-tx-key', 'tx-with-balance-source', 'both-balance-and-tx']
FAIL test_12_producer_history_and_default_boundary: ModuleNotFoundError: No module named 'producer_history'
anchor-plan v3: 0/12 PASS
```

这证明旧实现实际漏过全部新增点形态负例；producer 历史模块也确实尚不存在。正例/兼容/投影测试在旧生成器下同样为红，不是预先写成恒绿。

### 绿态命令与结果

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_anchor_plan_v3.py
```

结果：`exit=0`，12 组逐项 PASS，末行 `anchor-plan v3: 12/12 PASS`。

## 4. producer 历史哈希考证

考证命令：

```bash
for producer_rev in $(git log --format=%H --follow -- scripts/lib/anchor_plan.py); do
  git show "$producer_rev":scripts/lib/anchor_plan.py | shasum -a 256
done
```

结论：

```text
e5168a455d53bb5163722ea7f2a67c42b20bd3dd8ef6c3ae5e588014842cc1d9  3b76db80130987e0faf68d73094b08cddd161c9b
1a461169f0770c7a4b8d74eb185f68ae225906cf1ec49b9ad04154e340ebebb2  a9f4ad14937c7fdc6a7c59649e98be3943d3cced
```

第二条是当前 HEAD 中该文件的内容哈希，按工单登记 commit 为 `0ec6d1e`；再次执行下列命令得到同一哈希：

```bash
git show 0ec6d1e:scripts/lib/anchor_plan.py | shasum -a 256
```

新测试还逐项验证六字段、commit/hash 格式、git show 内容哈希、未登记拒绝、ACTIVE 放行、REVOKED 压过 ACTIVE、跨 protocol hash-wide 否决以及默认参数不放宽。

## 5. NES 三份存量深验

三份真实 receipt 的 producer 均为 `e5168a...`。先用 `load_validated_plan` 逐份深验 envelope、producer、target、input manifest、output 字节、schema 配对，结果：

```text
PASS bsc 115516517 .../NES分析/anchors/anchor_plan.json
PASS bsc 115516517 .../NES分析/bsc/anchors/anchor_plan.json
PASS eth 25739360 .../NES分析/ethereum/anchors/anchor_plan.json
```

随后以真实 plan/receipt/input 执行完整 dry-run 语义重放，精确复跑命令如下。

根 BSC 存量件：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/lib/time_spotcheck.py \
  --plan '/Users/uravvv/Documents/5.6筹码分析/NES分析/anchors/anchor_plan.json' \
  --plan-receipt '/Users/uravvv/Documents/5.6筹码分析/NES分析/anchors/anchor_plan.receipt.json' \
  --input '/Users/uravvv/Documents/5.6筹码分析/NES分析/data/replay/merged.parquet' \
  --dry-run --chain bsc \
  --token 0x3131f6b80c26936ab03f7d9d29eb4ddf36ac3fb5 \
  --final-block 115516517 --out /tmp/nes-root-bsc-u1-dryrun.json
```

实跑：`exit=0`，balance 1、tx 1、total 2。

BSC 正式目录存量件：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/lib/time_spotcheck.py \
  --plan '/Users/uravvv/Documents/5.6筹码分析/NES分析/bsc/anchors/anchor_plan.json' \
  --plan-receipt '/Users/uravvv/Documents/5.6筹码分析/NES分析/bsc/anchors/anchor_plan.receipt.json' \
  --input '/Users/uravvv/Documents/5.6筹码分析/NES分析/bsc/data/replay/merged.parquet' \
  --dry-run --chain bsc \
  --token 0x3131f6b80c26936ab03f7d9d29eb4ddf36ac3fb5 \
  --final-block 115516517 --out /tmp/nes-bsc-u1-dryrun.json
```

实跑：`exit=0`，balance 13、tx 11、total 24。

Ethereum 存量件：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/lib/time_spotcheck.py \
  --plan '/Users/uravvv/Documents/5.6筹码分析/NES分析/ethereum/anchors/anchor_plan.json' \
  --plan-receipt '/Users/uravvv/Documents/5.6筹码分析/NES分析/ethereum/anchors/anchor_plan.receipt.json' \
  --input '/Users/uravvv/Documents/5.6筹码分析/NES分析/ethereum/data/replay/merged.csv' \
  --dry-run --chain eth \
  --token 0x230f1e241c621d5af670dad83ebcdd18971e2995 \
  --final-block 25739360 --out /tmp/nes-eth-u1-dryrun.json
```

实跑：`exit=0`，balance 14、tx 3、total 17，其中 1 点使用签名 plan 的 final block。

三次均为只读 dry-run，未重签、未覆盖案例产物。

## 6. 测试结果

定向结果：

- U1 新测试：12/12 PASS。
- `test_time_spotcheck.py`：20/20 PASS。
- `test_r9_batch1_boundaries.py`：3/3 PASS。
- `test_recon_deep_reverify.py`：PASS。
- `test_audit_release_gate.py`：PASS。
- `test_receipt_kernel.py`：PASS。
- `test_batch1_receipt_paths.py`：PASS。
- `invariant_scan.py --dump-actual`：成功；新面已如实登记。
- `invariant_scan.py`：PASS，producers 63、consumers 91、transport 63、atomic writes 54、formal entrypoints 58、exceptions 0。
- `git diff --check`：PASS。

全量命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
```

最终结果共 115 项：113 PASS，2 FAIL。两项 FAIL 均为工单预告的环境限制：

```text
test_batch3_solana_vertical_slice.py: ThreadingHTTPServer bind 127.0.0.1 -> PermissionError [Errno 1] Operation not permitted
test_batch3_evm_vertical_slice.py:    ThreadingHTTPServer bind 127.0.0.1 -> PermissionError [Errno 1] Operation not permitted
```

其余 113 项全部 PASS；U1 新测试在全量入口末项显示 `anchor-plan v3: 12/12 PASS`。

## 7. 全库旧 schema 字面量残留清单

扫描命令使用 shell 字符串拼接，避免本报告自身新增被扫描字面量：

```bash
rg -n 'anchor-plan/'"v2" . --hidden --glob '!.git/**'
```

共 782 处。下列行号逐一覆盖全部命中；分类只有“兼容路径”“测试 fixture/守卫”“文档/历史日志”，没有现役 v2 producer 漏改。

### 7.1 兼容路径（12 处）

| 文件 | 命中行 | 归属 |
|---|---:|---|
| `scripts/lib/producer_history.py` | 15,17,23 | 兼容路径：历史 protocol 与原因 |
| `scripts/lib/time_spotcheck.py` | 62,83,155 | 兼容路径：支持集合、历史哈希查询、v2 投影分派 |
| `scripts/report/shared_release_receipt.py` | 965,979,980,981 | 兼容路径：历史哈希与 v2/v3 配对矩阵 |
| `scripts/tests/invariant_manifest.json` | 379,490 | 兼容路径：两个 consumer 继续接纳 v2 |

### 7.2 测试 fixture/守卫（12 处）

| 文件 | 命中行 | 归属 |
|---|---:|---|
| `scripts/tests/test_anchor_plan_v3.py` | 259,275,367,392 | 测试 fixture：v2 投影、receipt 配对、历史查询 |
| `scripts/tests/test_apu_legacy_gaps.py` | 309 | 测试 fixture：存量迁移输入 |
| `scripts/tests/test_audit_release_gate.py` | 110,122 | 测试 fixture：v2 plan/receipt 深验兼容 |
| `scripts/tests/test_recon_deep_reverify.py` | 174,194,312 | 测试 fixture/负例：v2 深验与错误文案 |
| `scripts/tests/test_time_spotcheck.py` | 118,136 | 测试 fixture：手写 v2 攻击 plan/receipt |

### 7.3 工单与历史 maintenance 文档/日志（758 处）

以下均为文档、既有评审台账或只读历史执行日志，不参与现役 producer/consumer 运行：

| 文件 | 命中行 |
|---|---|
| `maintenance/closure-20260817-threeunit/workorder_U1.md` | 60,61,90,97,103,106,110,145 |
| `maintenance/repair-20260806/b1_progress.md` | 105,285 |
| `maintenance/repair-20260806/diff-finding-map.md` | 166 |
| `maintenance/repair-20260806/ledger.md` | 84,548 |
| `maintenance/repair-20260806/reviews/r9-batch1-rereview.md` | 238 |
| `maintenance/repair-20260806/reviews/r9-batch1-rereview2.md` | 93 |
| `maintenance/repair-20260806/reviews/r9-batch1-review.md` | 203 |
| `maintenance/repair-20260815-g2/blindreview_g2_round1.md` | 316,403,472 |
| `maintenance/repair-20260815-g2/digest1_codex.log` | 102,189,278,853,888,891,921,1134,1145,1371,1745,1755,1759,1968,1986,2296,2446,2600,2798,2952,3104,3259,3342,3429,3530,3531,3560,3702,3797,3798,3827,3969,4066,4067,4096,4238,4341,4342,4371,4513,4611,4612,4641,4715,4717,4729,4821,4916,4917,4946,5020,5022,5034,5126,5284,5285,5314,5388,5390,5402,5494,5592,5593,5622,5696,5698,5710,5802,6152,6153,6182,6256,6258,6270,6362,6459,6460,6489,6563,6565,6577,6669,6737,6742,7103,7104,7133,7229,7230,7259,7333,7335,7347,7439,7549,7713,7803,7815,7868,7869,7898,7972,7974,7986,8078,8369,8370,8399,8473,8475,8487,8579,8684,8685,8714,8788,8790,8802,8894,8977,8990,8997,9040,9049,9095,9096,9125,9199,9201,9213,9305,9384,9397,9404,9447,9456,9502,9503,9532,9606,9608,9620,9712,9781,9798,9811,9824,9831,9874,9883,9929,9930,9959,10033,10035,10047,10139,10208,10225 |
| `maintenance/repair-20260815-g2/digest1_codex_lastmsg.txt` | 1,18 |
| `maintenance/repair-20260815-g2/digest1_red.log` | 12 |
| `maintenance/repair-20260815-g2/digest1b_codex.log` | 15,104,107,109,116,117,118,119,120,121,137,138,140,141,142,145,147,153,338,359,381,405,434,456,479,502,525,550,573,596,619,641,663,687,709,731,754,777,800,823,848,871,894,916,938,960,1130,1152,1175,1198,1221,1244,1267,1290,1313,1337,1359,1381,1403,1426,1449,1472,1495,1518,1541,1564,1586,1610,1632,1654,1677,2181,2188,2194,2197,2390,2464,2476,2528,2576,2577,2606,2722,2748,2843,2941,3037,3176,3277,3373,3469,3564,3659,3754,3849,3945,4041,4139,4235,4331,4427,4523,4618,4713,4808,4903,4999,5095,5191,5287,5383,5479,5575,5672,5767,5862,5957,6053,6149,6245,6341,6437,6533,6629,6724,6819,6914,7009,7105,7201,7297,7393,7489,7587,7683,7944,7957,8036,8133,8146,8225,8324,8337,8416,8498,8507,8536,8549,8629,8729,8738,8767,8780,8846,8873,8886,8965,9047 |
| `maintenance/repair-20260815-g2/digest1b_codex_lastmsg.txt` | 3 |
| `maintenance/repair-20260815-g2/f07_codex.log` | 547,4787,5834,6269,6710,7147,7597,8043,8492,8964,9364,9382,9698,10150,10625,11104,11988,12875,13813,14753,15781,16757,17146,18087,18865,18876,19228,20006,20017,20372,21150,21161,21531,22309,22320,22672,23450,23461,23816,24594,24605,24976,25754,25765,26117,26895,26906,27261,28039,28050,28421,29199,29210,29563,30341,30352,30708,31486,31497,31712,32124,32902,32913,33298,34116,34127,34506,35324,35335,36074,36892,36903,37303,38121,38132,39104,39922,39933,40643,41461,41472,41854,42563,42772,42783,43162,43871,44080,44091,44473,45182,45438,45449,45828,46537,46793,46804,47185,47894,48150,48161,48577,49286,49547,49558,49937,50646,50907,50918,51300,52009,52270,52281,52664,53373,53634,53645,54028,54737,54998,55009,55432,56141,56402,56413,56839,57548,57809,57820,58288,58997,59326,59337,59760,60469,60798,60809,61235,61944,62273,62284,62712,63422,63751,63762,64185,64895,65224,65235,65661,66371,66700,66711,67135,67845,68174,68185,68837,69547,69876,69887,70314,71024,71411,71422,71845,72555,72942,72953,73379,74089,74476,74487,75013,75723,76110,76121,76548,77258,77657,77668,78091,78801,79200,79211,79637,80347,80746,80757,81202,81912,82311,82322,82774,83484,83883,83894,84349,85098,85497,85508,85960,86709,87108,87119,87578,88327,88726,88737,89341,90090,90489,90500,90952,91701,92100,92111,92809,93558,93957,93968,94545,95294,95693,95704,96159,96908,97307,97318,97811,98560,98959,98970,99465,100214,100613,100624,101118,101867,102266,102277,102773,103522,103921,103932,104426,105175,105574,105585,106293,107042,107441,107452,107946,108695,109094,109105,109601,110350,110749,110760,111254,112003,112402,112413,113013,113762,114161,114172,114665,115414,115813,115824,116317,117066,117465,117476,118077,118826,119225,119236,119735,120484,120883,120894,121553,122302,122701,122712,123326,124075,124474,124485,125069,125818,126217,126228,126725,127509,127908,127919,128412,129196,129595,129606,130102,130886,131285,131296,131801,132585,132984,132995,133489,134273,134672,134683,135184,135968,136367,136378,136871,137655,138054,138065,138558,139342,139741,139752,140245,141029,141428,141439,141939,142723,143122,143133,143627,144411,144810,144821,145315,146099,146498,146509,147003,147787,148186,148197,148691,149475,149874,149885,150379,151163,151562,151573,152067,152851,153250,153261,153756,154540,154939,154950,155443,156227,156626,156637,157130,157914,158313,158324,158817,159601,160000,160011,160504,161288,161687,161698,162766,163550,163949,163960,164628,165412,165811,165822,166497,167281,167680,167691,168385,169169,169568,169579 |
| `maintenance/repair-20260815-g2/f07b_codex.log` | 1727 |
| `maintenance/repair-20260815-g2/f09_codex.log` | 1543,1554,1922,2095,2430,2441,4654,4665 |
| `maintenance/repair-20260815-g2/f09b_codex.log` | 1054 |
| `maintenance/repair-20260815-g2/f10_codex.log` | 1687,1705,2891 |
| `maintenance/repair-20260815-g2/workorder_DIGEST1.md` | 41 |
| `maintenance/repair-20260815-g2/workorder_DIGEST1_done.md` | 7,20,27,70,79,108,121 |

合计核算：兼容路径 12 + 测试 fixture/守卫 12 + 文档/历史日志 758 = 782。

## 8. 白名单与改动面核对

本次施工改动/新建仅涉及工单白名单中的 13 个路径（含本报告）：

```text
scripts/lib/anchor_plan.py
scripts/lib/anchor_selection.py
scripts/lib/anchor_point_contract.py
scripts/lib/time_spotcheck.py
scripts/lib/receipt_validate.py
scripts/lib/producer_history.py
scripts/report/shared_release_receipt.py
scripts/tests/invariant_manifest.json
scripts/tests/test_anchor_plan_v3.py
scripts/tests/test_time_spotcheck.py
scripts/tests/test_r9_batch1_boundaries.py
scripts/tests/run_all.py
maintenance/closure-20260817-threeunit/workorder_U1_done.md
```

`workorder_U1.md` 是调度方预先放入的未跟踪工单，本次只读，未修改。`git diff --check` 通过。`LEGACY_FINAL_BLOCK_EDGE_KIND` 当前值与 HEAD 字节一致，均为 `门槛±10% 边缘地址`。

## 9. 未尽事项

- 业务代码、定向回归、invariant 与除两项 loopback 外的全量 suite 已完成，无业务未尽项。
- 两项 vertical slice 需调度方在允许本机 loopback bind 的环境复跑；当前失败是沙箱能力限制，不是断言失败。
- 版本号、CHANGELOG、commit、push 均按工单留给调度方。
