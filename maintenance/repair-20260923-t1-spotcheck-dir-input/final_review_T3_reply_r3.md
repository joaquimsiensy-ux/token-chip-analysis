# 收官review r3：通过

FR-02 已在 HEAD 五个入口独立复现闭合；9.0.3 目录链路、9.0.4 旧文件时间收据兼容、9.0.5 覆写拒收三项矩阵成立。按本轮允许的 `SANDBOX-BLOCKED` 处理规则，回归通过，未发现新增 P0/P1。

审查 HEAD：`16482087464ca21a9777401feb88a6f8308aee9f`。范围为指定的 `b52cbed..HEAD` 三版合计差异。全程离线、未 commit、未创建或修改仓库文件；未读取 `~/.codex/`、memories 或禁读材料。仅 `changelog_lint.py` 按授权读取 archive。临时夹具、脚本和日志已清理。

**a）FR-02：五入口闭合**

在已全部通过的目录案上，用 DuckDB 将 `logs.parquet` 覆写为另一份可正常读取的有效 parquet。计划、输入清单、时间收据、四查 wrapper 和共享发布收据均保持原字节。

| 输入状态／消费者 | 对账深验 | READY | verify | validate_bundle | 发布闸 |
|---|---|---|---|---|---|
| 未改目录／HEAD | 通过 | 0 | 0 | `[]` | 0 |
| 有效 parquet 覆写／HEAD | 拒 | 2 | 2 | 错误列表 | 2 |
| 同一覆写／9.0.4 内存对照 | 通过 | 0 | 0 | `[]` | 0 |
| 新增叶子／HEAD | 拒 | 2 | 2 | 错误列表 | 2 |
| 移出叶子／HEAD | 拒 | 2 | 2 | 错误列表 | 2 |
| 目录内 symlink／HEAD | 拒 | 2 | 2 | 错误列表 | 2 |
| 65 MiB 叶子同大小修改中部／HEAD | 拒 | 2 | 2 | 错误列表 | 2 |
| 全部恢复／HEAD | 通过 | 0 | 0 | `[]` | 0 |

表中数字为 CLI 退出码；对账深验拒收为 `ValueError`，`validate_bundle` 返回错误列表。

覆写实验的实际拒收文本：

```text
validate_reconciliation_report:
time plan authority chain broken: time plan input directory content differs from signed identity

READY:
[generate] reconciliation READY 深验失败: time plan authority chain broken: time plan input directory content differs from signed identity

verify:
✗ reconciliation/accounting 公共深验失败: time plan authority chain broken: time plan input directory content differs from signed identity

validate_bundle:
['time plan authority chain broken: time plan input directory content differs from signed identity']

audit_release_gate:
- 共享发布 receipt: time plan authority chain broken: time plan input directory content differs from signed identity
- 受控对账公共深验失败: time plan authority chain broken: time plan input directory content differs from signed identity
```

新增、删除叶子使用相同拒收文本。symlink 五入口均包含：

```text
time plan authority chain broken: input directory contains symlink: …
```

大文件实验使用目录中的 `large.bin`：大小 65 MiB，在 32 MiB 位置修改一个字节。实测 handoff 的头尾分片指纹不变、完整 SHA-256 改变，五入口仍全部拒收：

```text
PASS 65MiB same size sparse unchanged full sha256 changed
```

9.0.4 对照源码来自：

```bash
git show 2197505:scripts/report/shared_release_receipt.py
```

源码仅载入内存；保留当前 `__file__` 身份视图，隔离共享收据 producer 哈希变化，专门比较消费逻辑。旧共享收据的实际升级影响另行验证，见 c）。

**b）三版整体端到端：成立**

目录案实际运行 anchor_plan、目录 time_spotcheck、四查 runner、READY、verify、共享 bundle 和发布闸。runner 顶层 `inputs` 分别省略、登记 `anchor_plan.input.json`，两种均通过。

旧文件案实际执行以下 Git 源码，原样置于临时源码树；仅在生产者自哈希计算期间切换其仓库根，没有手填旧收据哈希：

```bash
git show b52cbed:scripts/lib/time_spotcheck.py
```

实际生成的 producer SHA-256：

```text
87bbad2246f07afa2db4b37a7289fff2fc6ac16387284411e75104e1109f0a39
```

| 同一夹具族中的验收项 | 对账深验 | READY | verify | bundle | 发布闸 |
|---|---|---|---|---|---|
| 9.0.3：目录输入链路，HEAD 消费 | 通过 | 通过 | 通过 | `[]` | 通过 |
| 9.0.4：旧生产者真实自哈希文件收据，HEAD 消费 | 通过 | 通过 | 通过 | `[]` | 通过 |
| 9.0.5：目录通过后覆写，HEAD 消费 | 拒收 | 拒收 | 拒收 | 拒收 | 拒收 |

独立实验命令及尾行如下；临时脚本现已删除：

```bash
PYTHONPATH="$TMP" PYTHONDONTWRITEBYTECODE=1 \
R3_TRANSPORT="$TMP/transport.json" MPLCONFIGDIR="$TMP/mpl" \
python3 -B "$TMP/probe.py"
```

```text
PASS DIRECTORY runner inputs omitted + manifest
PASS OLD SELF HASH 87bbad2246f07afa2db4b37a7289fff2fc6ac16387284411e75104e1109f0a39
PASS R3 INDEPENDENT ALL MATRICES
```

其中 `$TMP` 为本轮 `tempfile` 创建的 `/private/tmp/r3-independent-nmpx7_v0`。

真实 loopback 被沙箱拒绝，因此传输使用原 B3 `FixtureHandler` 的内存响应。实际 CLI 子进程、语义重放、runner、收据生产和消费校验继续执行；没有替换消费校验器。发布闸验证范围为夹具的 `independent-audit` profile，不代表完整 `new-analysis` 流程或真实 socket/HTTP 通信已通过。

**c）回归、存量影响与边界：通过**

文件生产行为对照固定时钟及相同 producer 身份后，`b52cbed` 与 HEAD 的退出码、stdout、stderr、收据和 transcript 字节一致，覆盖成功、缺文件、含 `..` 的输入路径。

消费端在 `b52cbed`、9.0.4、HEAD 三者间比较合法件、错大小、错哈希、缺文件、plan/input 同时损坏，以及重新绑定输入引用但保留旧签名身份：结果与错误文本顺序一致。关键输出：

```text
plan/input 同时损坏：
time plan authority chain broken: time plan sha256 mismatch

输入引用已更新、签名身份未更新：
time plan authority chain broken: time plan input identity sha256 mismatch

PASS FILE BYTE AND ERROR-ORDER REGRESSION
```

命令为同一临时环境中的：

```bash
python3 -B "$TMP/file_regression.py"
```

以下检查 exit 0、无差异：

```bash
git diff --exit-code 2197505 HEAD -- \
  scripts/lib/receipt_kernel.py scripts/lib/receipt_validate.py \
  scripts/lib/anchor_selection.py scripts/lib/time_spotcheck.py \
  scripts/report/handoff_manifest.py scripts/report/audit_release_gate.py \
  scripts/tests/invariant_manifest.json scripts/tests/contract_manifest.json
```

两个 manifest 相对 `b52cbed` 也字节不变；未增加 schema、传输或正式入口，`invariant_scan` 通过，无需新增登记。指定范围的 `git diff --check` 通过。

共享发布收据的存量影响已在 CHANGELOG 9.0.5 如实登记。文件案、目录案分别实测旧 producer 哈希均返回：

```text
['shared receipt producer mismatch']
```

经现有 `create_bundle` 重建后，两案 `validate_bundle` 均返回 `[]`。这与“旧时间收据兼容”是两个不同层次，不能混称所有旧收据均原样兼容。

目录重算次数通过包装真实 `input_identity` 计数，未替换计算结果：

```text
COUNT verify 1
COUNT release 2
```

乘以获准读取的 QUQ 日志实测单次 **3.5 s**，估计分别增加 **3.5 s／7 s**。这是基于日志的乘积估计，本轮未访问 QUQ 实物重测。

witness 边界也做了动态验证：

- 签发后的 witness 未登记 parquet 叶子；随后修改目录，直接消费旧 witness 仍通过。
- 在同次发布 `run()` 第二次完整身份读取结束后修改目录，该次发布仍可通过。
- run 结束缓存清空；下一次发布独立重算并拒收，恢复目录后重新通过。

这些属于工单明确未承诺的持续冻结范围。witness、来源校验和 bundle 相关函数相对 9.0.4 逐字节未变，没有更差退化。

```bash
python3 -B "$TMP/boundaries.py"
```

```text
PASS NEXT RUN independently rejects directory drift; cache cleared
PASS R3 BOUNDARIES AND OLD BUNDLE MIGRATION
```

**d）指定实跑：10 项通过，B3 原样 SANDBOX-BLOCKED、内存补验通过**

统一命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/<脚本>
```

| 脚本 | 退出码／尾行 |
|---|---|
| `test_producer_registry_current.py` | 0；`producer registry: 0 FAIL` |
| `test_anchor_plan_v3.py` | 0；`anchor-plan v3: 17/17 PASS` |
| `test_time_spotcheck.py` | 0；`time_spotcheck 契约测试全部通过（20 项）` |
| `test_recon_deep_reverify.py` | 0；`PASS test_recon_deep_reverify` |
| `test_handoff_manifest.py` | 0；`handoff_manifest 契约测试全部通过（283 项）` |
| `test_audit_release_gate.py` | 0；`PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过` |
| `test_batch3_evm_vertical_slice.py` | **SANDBOX-BLOCKED**，exit 1；`PermissionError: [Errno 1] Operation not permitted` |
| `test_batch4_invariant_guards.py` | 0；`PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `test_exemption_guards.py` | 0；`PASS: exemption guards (EX-01 full-F-03)` |
| `invariant_scan.py` | 0；`PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0` |
| `changelog_lint.py` | 0；`PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 84 条 + 归档 139 条` |

B3 内存补验执行原测试 `main()`，覆盖 ETH/BSC/Base、非零 dead、错链零业务调用断言及交接／发布链；通过临时方法日志保留跨子进程调用列表断言：

```bash
python3 -B "$TMP/b3_memory.py"
```

```text
PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
PASS MEMORY B3 eth/bsc/base + nonzero dead; wrong-chain method assertions retained; sockets excluded
```

**e）判定：通过。** a）五入口及反例闭合，b）三版矩阵成立，c）回归与边界符合工单，d）按沙箱例外规则完成。无未闭合的新 P0/P1。

最终 `git status --short` 全文如下，输出为空：

```text
```
