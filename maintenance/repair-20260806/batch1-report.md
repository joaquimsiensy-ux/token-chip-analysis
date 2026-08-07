# R8 修复闭环：批一公共原语施工报告

## 1. 范围与边界

- 冻结基线：`66d7ba7760215bde00755559e1bd3c8780ab7594`。
- 施工范围：`INV-05`、`INV-07`、`INV-15`；对应 `R8-04`、`R8-12`（仅 kernel 能力）、`R7-12`、`R8-07`、`R8-09`、`R7-14`、`R8-10`。
- 未调用任何真实外部 RPC/API；所有 RPC 反例只在 `scripts/lib/net.py:_request_json` transport 边界注入 fake，逐项登记于 `transport-injections.json`。
- `R8-12` 的边界没有扩大：本批只闭合 `receipt_kernel.py` primitive。`anchor_sampler.py`、`window_fetch.py` 改用 data+receipt 联合事务仍是批三工作，本批未改这两个 producer。
- `references/` 与 `CHANGELOG.md` 未修改；现役 labels 只读验证，不改写 59 条历史非 canonical `risk_flags`。

## 2. 先红后绿证据

所有命令均在仓库根目录执行，并设置 `PYTHONDONTWRITEBYTECODE=1`。

### 工单 A：INV-05 receipt kernel

红：先新增 `scripts/tests/test_batch1_receipt_paths.py`，在冻结实现上执行：

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch1_receipt_paths.py
Traceback (most recent call last):
  ...
AssertionError: exclusive final symlink: unsafe path was accepted
exit=1
```

绿：实现逐级无跟随打开、dirfd 发布、路径判重和回滚保护后：

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch1_receipt_paths.py
PASS B1-A receipt paths: symlink/alias/rollback/fail-closed/PASS protection
exit=0

$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_receipt_kernel.py
PASS receipt kernel: 24 fixtures (envelope/identity/publication/faults)
exit=0
```

测试 ID：

| ID | 反例/正例 |
|---|---|
| `B1-RK-01` | 四种发布/恢复 primitive 加 ERROR-side wrapper 的最终组件 symlink 均拒绝，外部目标不产生 |
| `B1-RK-02` | 四种发布/恢复 primitive 加 ERROR-side wrapper 的中间目录 symlink 均拒绝，外部目录不产生半成品 |
| `B1-RK-03` | data/receipt 不同词法名但为同一 hardlink inode 时拒绝，原字节不变 |
| `B1-RK-04` | staging 写失败向上传播且无目标/临时半成品 |
| `B1-RK-05` | 第二次发布失败且回滚再失败时，仍保留备份，异常列出备份路径，无 tmp 半成品 |
| `B1-RK-06` | 已存在 canonical PASS 不得被 FAIL/ERROR 或无 PASS verdict 的写入降级覆盖 |

### 工单 B：INV-07 chain-attested RPC session

第一次红：共享层尚无 attestation 契约。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch1_rpc_attestation.py
TypeError: RpcPool.__init__() got an unexpected keyword argument 'expected_chain_id'
exit=1
```

对已知四入口转绿后，扩大同族扫描又发现六个正式/现役 EVM 调用点。补充反例先因缺 `--chain` 转红：

```text
multicall_balances.py: error: unrecognized arguments: --chain bsc
methods=[]
exit=1
```

最后发现 Alchemy 的专有 EVM JSON-RPC 方法也属于业务 RPC，同样先转红：

```text
fetch_alchemy.py: error: unrecognized arguments: --chain bsc
methods=[]
exit=1
```

十个正式调用点全部迁入唯一 session 后转绿：

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch1_rpc_attestation.py
PASS B1-B RPC session: wrong-chain zero business/fail-closed/correct/failover
exit=0
```

测试 ID：

| ID | 反例/正例 |
|---|---|
| `B1-RPC-01` | 错链只允许 `eth_chainId`，随后抛 `RpcChainMismatch`，业务调用数为 0 |
| `B1-RPC-02` | `eth_chainId` 超时、异常、空值、非 hex、非字符串、非正数全部 fail-closed |
| `B1-RPC-03` | 正确链先 attest，再正常执行一个业务调用 |
| `B1-RPC-04` | endpoint 切换后必须对新 endpoint 重新 attest，才可重试业务调用 |
| `B1-RPC-05` | registry 中 `evm_chain_id=None` 的 `robinhood`、`opbnb` 在 formal 工厂入口拒绝 |
| `B1-RPC-06` | 十个正式生产 CLI/调用点逐个错链运行，记录均严格等于 `['eth_chainId']` |

`B1-RPC-06` 的调用点子 ID：`accounting`、`recon`、`time`、`supply`、`multicall`、`pierce`、`lp`、`bloxroute`、`rpc-batch`、`alchemy`；完整注入边界见 `transport-injections.json`。

### 工单 C：INV-15 canonical risk_flags parser

红：四层尚无可共同 import 的唯一 parser。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch1_risk_flags.py
ModuleNotFoundError: No module named 'risk_flags'
exit=1
```

首轮转绿后的严出复核又先补 staging 反例；当时 validator 尚无 strict 契约：

```text
TypeError: validate_file() got an unexpected keyword argument 'strict_canonical'
exit=1
```

绿：共享 parser 和全部消费者迁移后：

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch1_risk_flags.py
PASS B1-C risk_flags: canonical parser + four-consumer/live-table agreement
exit=0
```

测试 ID：

| ID | 反例/正例 |
|---|---|
| `B1-RF-01` | 原反例 `" tornado-user"` 经 parser 后 validator 与 resolver 均解释为 `tornado-user`，exclude 行不再绕过 policy |
| `B1-RF-02` | 重复、乱序、空段、全空白、`None` 均得到去重排序的同一集合；merge 也输出 canonical 串 |
| `B1-RF-03` | 全部现役 `labels-*.csv` 共 470879 行逐表 validate，并逐行对比 resolver 与 canonical parser；59 条历史非 canonical 行宽进告警，新 staging 同值严格拒绝 |

共享函数放在 `scripts/labels/risk_flags.py`，因为五个消费者本来就是同目录脚本式 import；放入 `scripts/lib` 会引入新的 `sys.path` 层和第二种导入约定。除工单指定的 add/validate/roundtrip/resolver 外，`build_labels.py` 也有 policy split 和写出职责，因此一并迁入，否则“唯一 parser”仍不成立。读取侧规范化后解释；现役目录的历史非 canonical 存储仅告警，其他 staging 默认严格拒绝。add/build 写出前规范化整张表，不只规范本次触碰行。

## 3. 同族调用面清单与处置

### 3.1 直接写入面

执行命令：

```text
rg -l 'json\.dump|write_text|rename|os\.replace' scripts --type py
```

结果为 154 个文件：103 个生产/工具文件，51 个测试文件。人工筛分如下；这里登记迁移责任，不在批一越界改 producer。

| 处置 | 文件/范围 |
|---|---|
| 本批已闭合公共 primitive | `scripts/lib/receipt_kernel.py`；已使用 kernel 的 `verify_recon.py`、`time_spotcheck.py`、`supply_truth_gate.py` 继续通过原测试 |
| 批三必须迁入联合发布/当前 envelope | `scripts/solana/accounting_gate_sol.py`、`anchor_sampler.py`、`window_fetch.py`、`scan_token_accounts.py`、`replay_edges.py`；EVM 纵切片中的 `accounting_gate.py`、`channels_preflight.py`、`csv_collector_receipt.py`、`fetch_hypersync.py`、`fetch_hypersync_logs.py`、`fetch_hypersync_v2.py`、`fetch_pool_swaps.py`、`make_channel_receipt.py`；聚合/交接的 `reconciliation_report.py`、`handoff_manifest.py`、`shared_release_receipt.py` |
| 批四由发布守卫/fixture 收口 | `a4_gate.py`、`a5_report_seal.py`、`adjudication_validator.py`、`adversarial_review_runner.py`、`audit_release_gate.py`、`build_html.py`、`distribution_explanation_check.py`、`entity_identity_gate.py`、`entity_source_trace.py`、`holder_distribution_scan.py`、`identity_snapshot_receipt.py`、`reproduce_receipt.py`、`state_from_facts.py`；51 个 `scripts/tests/*.py` 写入点按 fixture/测试输出管理 |
| 正式发布路径外，本批不迁 | `scripts/robinhood/` 下命中的 14 个文件全部保持 exploration；`scan_transfers.py` 为历史/诊断 RPC 工具；`scripts/labels/{fingerprint_check.py,probe_codetype.py}` 为标签维护/探针；这些路径不得产出 formal PASS，能力恢复时豁免自动失效 |
| 普通业务数据、缓存或分析派生物，不是 receipt 发布 primitive | `scripts/evm/` 余下 replay/cluster/peaks/holdings/cadence/LP 查询输出；`scripts/solana/` 余下 decode/probe/trace/build/cache 输出；`scripts/labels/` 余下维护输出；`scripts/prices/`、`scripts/bench/`、`scripts/hooks/`、`proclock.py`、`run_guarded.py`；本批不把普通数据写入误归为 receipt |

以上“批三必须迁”是责任清单，不表示这些 producer 已被本批修复。尤其 `anchor_sampler.py`、`window_fetch.py` 仍是 `R8-12` 未施工面。

### 3.2 EVM RPC 调用面

检索 `eth_call|eth_getLogs|eth_getTransactionReceipt|eth_getBalance|alchemy_getAssetTransfers` 并人工检查 adapter 后：

| 分类 | 调用点 | 处置 |
|---|---|---|
| 正式/现役 | `accounting_gate.py`、`verify_recon.py`、`time_spotcheck.py`、`supply_truth_gate.py`、`multicall_balances.py`、`pierce_stake.py`、`lp_positions.py`、`scan_bloxroute_seg.py`、`rpc_batch.py`、`fetch_alchemy.py` | 全部迁到 `attested_rpc_pool`；每项错链业务调用=0 |
| 历史/诊断 | `scan_transfers.py` | 不迁；不得作为 formal producer 回流 |
| exploration | `scripts/robinhood/pull_transfers_rpc.py` 及 Robinhood 同族 | 不迁；`evm_chain_id=None`，formal 工厂显式拒绝 |
| 标签维护/探针 | `labels/fingerprint_check.py`、`labels/probe_codetype.py` | 不迁；不是 formal 发布状态来源 |
| 非 JSON-RPC 协议 | Sourcify HTTP、HyperSync、SQD | 不套 EVM attestation；各自协议守卫仍由原 adapter 负责 |

### 3.3 risk_flags 解释面

```text
rg -n "risk_flags.*split|split\(['\"]\|['\"]\).*risk_flags" scripts/labels --type py
```

结果为空；`split('|')` 只保留在 `risk_flags.py:10` 的 canonical parser 内。add、validate、roundtrip、resolver、build 五个消费者均 import 同一实现。

## 4. 新建代码六视角自审：①字段来源、②失败分支

| 工单 | ① 字段来源审计 | ② 失败分支审计 | 结论 |
|---|---|---|---|
| A / `INV-05` | 路径身份来自调用方词法路径；逐级 `lstat` 后用 dirfd 固定父目录对象，最终组件用 nofollow stat；多路径再以规范化词法名和现存 inode 双重判重。没有把 `resolve()` 后结果当唯一身份。 | staging、link/replace、校验、发布及 rollback 均传播失败；rollback 再失败时不清理其备份，异常给出保留路径；canonical PASS 降级在 staging 前拒绝。 | 本批反例覆盖四种 primitive 及 ERROR-side wrapper；producer 是否选对 primitive 留给批三。 |
| B / `INV-07` | expected chain ID 只由 `chain_registry.get_chain_config(chain).evm_chain_id` 进入 formal 工厂；endpoint 自报值只作 observed 值，不能覆盖 expected 值；`verify_recon` 私有实现已删除。 | chainId 请求失败、RPC error、不可解析、错链均在业务调用前关闭；failover 新 endpoint 重新验证；错链不尝试“猜链”或继续业务调用。 | 十个正式调用点动态证明错链方法序列只有 `eth_chainId`。 |
| C / `INV-15` | 原始 `risk_flags` 只由 `parse_risk_flags` 解释成 trim/去空/dedup/排序 tuple；policy 层不再读取另一套 split 结果。 | 现役非 canonical 历史存储读取为同一集合并告警；新 staging 严格拒绝；add/build 整表写出 canonical；空值/空段安全归一为空集合。 | 470879 行现役表 validate 与 resolver 对表一致，59 条历史行不被误伤且不能回流进新 staging。 |

自审中发现并当场处理三项遗漏：初次 B 迁移只覆盖工单点名的四入口，扩大同族 rg 后补入五个标准 eth_* 调用点和 Alchemy 专有业务 RPC；初次 kernel 重构把 `os.replace` 藏在私有 helper，静态 invariant scanner 无法定位公共 primitive，随后把 dirfd 原子操作保留在各 public primitive 内；初次 C 实现对所有非 canonical 输入只告警，随后拆成“现役历史宽进、其他 staging 严出”，并让写入器规范化整表。三项均在最终全量门禁前补反例并转绿。

## 5. 归因预判

| finding | 预判 | 批一处置边界 |
|---|---|---|
| `R8-04` | 新引入 | kernel path identity/TOCTOU/fault-on-fault/PASS 保护已覆盖，待批内审查和 Fable 裁决 |
| `R8-12` | 半修残留 | 仅 kernel 能力闭合；anchor/window producer 迁移未完成，不在本批申请整项销账 |
| `R7-12` | 新引入；后续同族构成半修残留链 | 私有 attestation 合并进唯一 session，正式调用面收口 |
| `R8-07` | 半修残留 | time spotcheck 已迁入共享 session |
| `R8-09` | 历史漏检 | supply 及扫描出的正式 sibling 已迁入共享 session |
| `R7-14` | 新引入；后续同族构成半修残留链 | 唯一 parser 进入所有解释/写入层 |
| `R8-10` | 半修残留 | 原前导空格与同族变体均由共享 parser 收口 |

最终结果栏继续留空；本报告不替代批内审查与 Fable 终裁。

## 6. 逻辑分组（Fable 代 commit）

| 分组 | owner | 文件与目的 |
|---|---|---|
| `B1-G1` | `INV-05`; `R8-04`, `R8-12` kernel-only | `scripts/lib/receipt_kernel.py`；`scripts/tests/test_batch1_receipt_paths.py`、`test_receipt_kernel.py`、R7/six-lens 既有 fixture 的临时根解析 hunk、`run_all.py` 对应 hunk；ledger/diff-map/report 对应段。闭合四类 primitive 与回滚。 |
| `B1-G2` | `INV-07`; `R7-12`, `R8-07`, `R8-09` | `scripts/lib/net.py`、四个 lib/已知调用点、七个 EVM 调用脚本、R7/six-lens 的 RPC/session fixture hunk、`invariant_manifest.json`、`transport-injections.json`、`run_all.py` 对应 hunk及台账段。建立唯一 attested session 并迁移正式面。 |
| `B1-G3` | `INV-15`; `R7-14`, `R8-10` | `scripts/labels/risk_flags.py` 及五个消费者、`test_batch1_risk_flags.py`、`run_all.py` 对应 hunk及台账段。建立唯一 parser 并保持存量读取兼容。 |

共享维护文件需按表中相应 hunk 分组暂存；禁止把三个 owner 合并成无法反查的笼统 commit。

## 7. 门禁结果

- 定向三件套：全绿。
- `scripts/tests/invariant_scan.py`：全绿，输出 `PASS invariant manifest: receipt_producers=44, receipt_consumers=51, transport_calls=39, atomic_writes=37, formal_entrypoints=54, exceptions=0`。
- 全量 `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py`：`exit=0`，汇总输出 `全部通过`；清单中的 70 项门禁均为 PASS。
- `git diff --check`：通过。
- `transport-injections.json`：`json.loads` 通过，10 条 entry。
