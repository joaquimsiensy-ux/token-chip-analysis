# 收官review r2：通过

FR-01 已独立验证修复，9.0.3 目录链路仍贯通，FR-03 文档与源码一致。未发现新增 P0/P1。FR-02 仍存在，但与修复前一致，按本轮约定单列，不据此退回。

审查 HEAD：`3d6a9f8922155043ddbec92d2b242b727afaa844`。全程离线，未读取 `~/.codex/`、memories 或禁读材料；仅 `changelog_lint.py` 按授权读取 archive。未修改、新建仓库文件，未 commit。

**a）FR-01：闭合**

从 Git 提取并实际执行旧生产者：

```bash
git show b52cbedf230218e5da46334cf99b7111235e8367:scripts/lib/time_spotcheck.py
```

源码原样写入临时源码树，仅将生产者哈希计算的仓库根指向该树；没有手改收据哈希，没有替换消费校验器。实得：

```text
87bbad2246f07afa2db4b37a7289fff2fc6ac16387284411e75104e1109f0a39
```

使用真实文件输入、实际语义重放及 HEAD 四查 wrapper，结果如下：

| 关口 | HEAD |
|---|---|
| `validate_reconciliation_report` | 通过 |
| `handoff_manifest generate --status READY` | exit 0 |
| `handoff_manifest verify` | exit 0，18 件产物、4 个 gate |
| `create_bundle` → `validate_bundle` | 返回 `[]` |
| `audit_release_gate --report` | exit 0 |

关键尾行：

```text
PASS GATES OLD FILE REAL SELF-HASH 87bbad2246f07afa2db4b37a7289fff2fc6ac16387284411e75104e1109f0a39 validate_reconciliation_report READY verify validate_bundle=[] release
```

同一收据交给 `git show d2d6641:scripts/report/shared_release_receipt.py` 载入的修复前消费者：

```text
wrapper：reconciliation time producer/runner is not current repository script
envelope：reconciliation time receipt envelope invalid: producer hash mismatch；存量案例须重跑对应生产者获取当前回执
READY：exit 2
[generate] reconciliation READY 深验失败: reconciliation time producer/runner is not current repository script
```

反例均按预期拒绝：

| 反例 | 实测结果 |
|---|---|
| envelope／wrapper 陌生哈希 | 哈希校验拒绝 |
| envelope／wrapper 错 producer path | 哈希或路径白名单拒绝 |
| EVM balance、supply、supply_truth 使用旧时间哈希 | 全拒 |
| Solana 全部五个查项使用旧时间哈希 | 全拒 |
| 收据正文 `[]` | `receipt must be an object`，仍走 `ValueError` |
| 默认 `validate_receipt` | 恰返回 `["producer hash mismatch"]` |
| 旧哈希配 `time-spotcheck/v2` | `unknown schema` |
| owner／producer／path 类型异常 | 历史辅助函数返回 `None` |

旧哈希也没有绕过目录约束：合规目录收据通过；错绑另一文件报：

```text
directory input identity is not bound through the signed input manifest
```

修改清单实物则在 envelope 输入绑定处被拒。

**b）9.0.3 目录链路、FR-03：闭合**

临时构造有效的 `v2/run_1/{logs,blocks}.parquet`，实际执行以下链路；路径和公共参数在此简写：

```bash
python3 -B scripts/lib/anchor_plan.py --input v2 … --out-dir .
python3 -B scripts/report/reconciliation_report.py "$CASE/job.json"
python3 -B scripts/report/handoff_manifest.py generate --case-dir "$CASE" --status READY …
python3 -B scripts/report/handoff_manifest.py verify --case-dir "$CASE"
python3 -B scripts/report/audit_release_gate.py "$CASE" --report "$CASE/report.md"
```

runner 的 time 参数始终为 `--input v2`。分别省略顶层 `inputs`、登记 `anchor_plan.input.json`，两次均四查 PASS：

```text
PASS DIRECTORY runner inputs omitted
PASS DIRECTORY runner inputs manifest
PASS GATES DIRECTORY validate_reconciliation_report READY verify validate_bundle=[] release
```

没有“输入必须是普通文件”拒收。发布闸采用夹具的 `independent-audit` profile。

文档两行符合源码：CLI 使用生成 plan 的同一文件或目录；runner `inputs` 可省略，登记则必须填文件；`data_map.files` 登记叶子，不填目录。两行字节分别为 `111→110`、`326→320`，合计减少 7 B。

**c）FR-02：已知、已升级给用户裁决**

本轮重新将 `logs.parquet` 覆写成另一份有效 parquet，保持计划、清单、时间收据不变：

```text
重跑语义重放：input sha256 mismatch
PASS FR02 pre904 and HEAD both accept unchanged stale receipt
PASS GATES FR02 OVERWRITE unchanged validate_reconciliation_report READY verify validate_bundle=[] release
FR02 witness parquet count 0
```

因此，9.0.4 没有加重该问题。正控制也成立：登记两个 parquet 后再覆写，verify 返回 2：

```text
✗ 哈希/大小漂移: v2/run_1/logs.parquet
```

对裁决页的技术意见：

- **A** 是明确接受现有缺口，不能提供机器防线。
- **B 原文不足以完整关闭 FR-02。** READY 会重新采集当前文件指纹，仅比清单与 `data_map` 声明无法证明当前实物一致；verify 还需独立检查覆盖关系；直接发布入口也须接入。另有既存边界：handoff 对超过 64 MiB 文件使用头尾分片哈希。本轮实测同大小中部修改可保持该指纹不变。
- **若目标是 READY、verify、直接发布均拒绝陈旧目录证据，C 加上重新枚举文件集合，是代码改动最小的完整闭环。** 可复用现有目录身份计算，但须承担完整读取成本。

若优先采用 B，需另行设计增强版：覆盖生成、验证及发布入口，并解决完整哈希和文件集合变化。预计涉及 **2–3 个生产文件及对应测试**，不是“改一处＋沿用 verify”即可；这是实现面估计，未代替用户裁决。

**d）回归面：通过**

执行：

```bash
git diff --exit-code 3b5017d HEAD -- \
  scripts/lib/receipt_kernel.py scripts/lib/receipt_validate.py \
  scripts/lib/time_spotcheck.py scripts/report/handoff_manifest.py
```

exit 0，四文件逐字节不变。

文件输入对照固定时钟和相同 producer 身份后，旧源码与 HEAD 的退出码、stdout、stderr、收据及实际 transcript 字节一致。覆盖成功、缺文件、包含 `..` 的真实文件路径；后者双方均返回 1：

```text
[fatal] receipt envelope 构建失败: input path escape rejected: …
```

消费端合法件、错大小、错哈希、缺文件、plan/input 同时损坏的结果及错误文本一致；同时损坏时仍先报 `time plan sha256 mismatch`。

登记条目 Git 可复现；`test_producer_registry_current.main` AST 不变，仅扩充精确历史协议对及注释。`invariant_manifest`、`contract_manifest` 字节不变，扫描通过，无需新增登记。限定差异的 `git diff --check` 也通过。

**e）指定实跑**

统一命令为：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/<下表脚本>
```

| 脚本 | 退出码与尾行 |
|---|---|
| `test_producer_registry_current.py` | 0；`producer registry: 0 FAIL` |
| `test_anchor_plan_v3.py` | 0；`anchor-plan v3: 16/16 PASS` |
| `test_time_spotcheck.py` | 0；`time_spotcheck 契约测试全部通过（20 项）` |
| `test_recon_deep_reverify.py` | 0；`PASS test_recon_deep_reverify` |
| `test_handoff_manifest.py` | 0；`handoff_manifest 契约测试全部通过（283 项）` |
| `test_audit_release_gate.py` | 0；`PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过` |
| `test_batch3_evm_vertical_slice.py` | **SANDBOX-BLOCKED**，exit 1；`PermissionError: [Errno 1] Operation not permitted` |
| `test_batch4_invariant_guards.py` | 0；`PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `test_exemption_guards.py` | 0；`PASS: exemption guards (EX-01 full-F-03)` |
| `invariant_scan.py` | 0；`PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0` |
| `changelog_lint.py` | 0；`PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 83 条 + 归档 139 条` |

B3 原样执行阻于 loopback `socket.bind`。补充实验将 HTTP 传输接到原 `FixtureHandler` 的内存响应，实际 CLI、runner、收据生成及消费者继续执行；通过临时调用日志保留错链方法列表断言：

```text
PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
PASS MEMORY B3 eth/bsc/base + nonzero dead; wrong-chain method assertions retained; sockets excluded
```

这覆盖 ETH/BSC/Base、非零 dead、错链零业务调用及发布链，**不证明真实 socket/HTTP 通信通过**。

**f）最终判定**

按本轮允许的 `SANDBOX-BLOCKED` 处理规则，a/b/d/e 已闭合，无新增 P0/P1，判定通过。FR-02 保留待用户裁决。

临时脚本、夹具和日志已清理。最终 `git status --short` 全文为空：

```text
```
