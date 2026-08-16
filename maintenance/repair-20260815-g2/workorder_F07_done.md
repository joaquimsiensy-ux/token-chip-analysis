# 工单 F-07 施工报告（停在名单外测试决策点）

## 状态

**BLOCKED — 工单主体与红名单已完成，但全量验收命中名单外失败，已按工单停止扩面。**

没有运行任何 git 命令。没有修改 VERSION、CHANGELOG、SKILL.md、r10_ledger.md、pyproject、run_all.py、audit_release_gate.py、handoff_manifest.py、anchor_sampler.py、contract_ids_snapshot.json，也没有触碰 shared 的 A4/adversarial 函数区。

## A. producer 最小补齐

### `scripts/evm/verify_recon.py`

- schema 升为 `evm-reconciliation-receipt/v3`；family 不变。
- top-N 排序改为 `(-balance, address)`；收据新增正整数 `requested_top_n` 与固定语义 `top_n_then_skip_sinks`。
- GMGN 前 10 行改用 Decimal；拒非有限值、非法数值和重复地址；行内百分比/差值写 Decimal 规范字符串，阈值使用 `Decimal("0.15")`。
- 每次成功的 `balanceOf` 调用落 `{seq,method,params,result}` transcript；默认 `verify_recon_transcript.json`，支持 `--transcript-out`。
- transcript 被 `inputs.transcript` 的 path/size/sha256 绑定；receipt 与 transcript 通过 `publish_txn` 双件发布。

### `scripts/lib/time_spotcheck.py`

- schema 升为 `time-spotcheck/v3`。
- `inputs` 同时绑定 plan、plan_receipt、merged input 与 transcript。
- balance/tx 两类 RPC 调用均落连续 transcript；默认 `time_spotcheck_transcript.json`，支持 `--transcript-out`。
- receipt 与 transcript 通过 `publish_txn` 双件发布。

## B. consumer 深重验

仅在 `shared_release_receipt.py` 对账区新增私有 helper，并接入 `validate_reconciliation_check`：

- EVM supply：从 config、replay_stats、balances 重算 nominal、mint、burn、balance sum、负值全列与 closed；校验 config token 与 replay cutoff。
- EVM balance：按绑定余额重算 top-N 有序地址全集；逐行核 replay_raw、chain_raw、diff_raw、status 与四计数；PASS 禁 MISMATCH/RPC_ERROR。
- EVM balance transcript：校验连续 seq、eth_call、holder calldata、冻结块与原始 hex result。
- GMGN：从绑定 CSV 与 balances/nominal 用 Decimal 重算全部 rows、状态与 diff_count。
- EVM time：plan 点与 rows 做 multiset 一一对应；核 plan receipt 的 input identity；重算六计数；balance 与 tx 均对 transcript 重放。
- Solana anchor：顶层 output 做 path/size/sha256 三验；逐行核日期范围、日期唯一、target 身份、失败行；重算 coverage/failures。
- v2 正式拒收并给出 `verify_recon v3` / `time_spotcheck v3` 重跑迁移文案。

## C. schema 级联收口

| 命中位置 | 处置 |
|---|---|
| `verify_recon.py` producer | v2 -> v3 |
| `time_spotcheck.py` producer | v2 -> v3 |
| `shared_release_receipt.py` consumer | 只接受 v3；v2 留给负测 |
| `invariant_manifest.json` producer/consumer schema | v3 |
| `invariant_manifest.json` atomic writes | 新增两个 dual_file_txn，minimum 52 -> 54 |
| `references/data-pipeline-evm-recon.md` | 当前产物说明改 v3，并写明新增绑定 |
| `references/analyze-workflow.md` | 当前时间抽查路由改 v3 |
| `contract_manifest.json` | 无旧 schema needle，无需修改 |
| 维修计划、历史 review、archive/CHANGELOG | 历史事实，保留 v2 原文 |
| `test_repair_batch1.py` 的 v2 | schema-family 失效测试的历史输入，保留 |
| `test_recon_deep_reverify.py` 的 v2 | 明确迁移拒收负测，保留 |

扫描结果：`invariant_scan.py` PASS，计数为 producers=62、consumers=83、transport=63、atomic=54、formal=58、exceptions=0；self-test 两个注入均按预期转红。

## D. 存量适配及理由

| 文件 | 适配理由 |
|---|---|
| `test_audit_release_gate.py` | 公共 EVM 案夹具升级为真实 v3 config/balances/stats/gmgn/transcript 与 v3 time plan 链；被多个红名单 suite 复用 |
| `test_sixlens_receipts.py` | 浅 v2 正例升级为公共深语义夹具；producer schema 断言改 v3 |
| `test_handoff_manifest.py` | READY 案四查夹具升级 v3；直接 time artifact schema 改 v3 |
| `test_evm_observation_release.py` | EVM release 案升级 v3；旧“只改 target”攻击现在更早死于 replay cutoff 深验，断言改认新的首个拒绝层 |
| `test_repair_batch_d.py` | A-5 异源账本补合法 cutoff，使反例继续抵达同源断言；Solana anchor 夹具补真实 output/date/identity |
| `test_repair_batch1.py` | verify/time 已改双件事务，source-wiring guard 从 supersede 改验 publish_txn |
| `test_arbitrum_exploration_cli.py` | C 节 schema 级联：formal 正例改为完整 v3；exploration/formal-tier 拒收语义不变 |

红名单结果：除 `test_batch3_evm_vertical_slice.py` 在沙箱内因 loopback bind EPERM 外，其余全部通过；该纵切片在沙箱外复跑通过。详见 `f07_green.log`。

## E. 新测试与红绿证据

`scripts/tests/test_recon_deep_reverify.py` 使用离线 fake transport 跑真实 verify_recon/time producer，另构造最小 Solana output。覆盖：

- supply 实物和与自报 closed 冲突；
- balance 少行、replay_raw 错、matched 虚报、缺 requested_top_n、地址乱序；
- transcript result 错、缺 transcript；
- GMGN diff_count 虚报；
- time plan 不对应、tx from 改动、计数虚报、缺 plan_receipt；
- anchor output 少行、日期重复；
- recon/time v2 迁移拒收；
- 三类真实绿例。

施工前 `f07_red.log`：旧 consumer 放行 `balances sum=80` 但自报 `balance_sum=100, closed=true` 的收据，新测试因此红。

施工后新测试 PASS；证据见 `f07_green.log`。

## 全量验收阻断（需调度方裁决）

`python3 scripts/tests/run_all.py` 尚未完成全绿。运行中出现以下名单外失败后，已立即中断，未修改名单外文件：

1. `test_repair_batch_b.py`：`test_f03_gate_evm_same_total_swap` 的旧夹具在 `bind_balance_receipt_to_snapshot` 换绑余额实物后，仅刷新输入引用，没有同步 v3 收据自报的 `supply_closure.balance_sum_raw`；新 consumer 在 `_validate_recon_supply` 正确拒绝。该文件不在 D 节红名单。
2. `test_repair_batch_a.py`：全量汇总显示 `BATCH A FAIL 1/45`，但当前截获尾段没有该 case 名。按“名单外打红即停”没有再单跑定位。
3. Solana/EVM 两个纵切片在沙箱内均为 `socket.bind EPERM`；EVM 已沙箱外单测通过。它们是环境能力限制，不定性为业务红灯。

### 请求裁决

请明确是否授权扩展 D 节名单，至少纳入：

- `scripts/tests/test_review_20260804_p105.py`（实际换绑 helper 所在）；
- `scripts/tests/test_repair_batch_b.py`（触发方）；
- `scripts/tests/test_repair_batch_a.py`（先只读定位其 1/45，再按同族夹具规则最小适配）；
- 若上述测试复用其他旧浅夹具，仅允许沿调用链追加必要的测试文件白名单，不改生产语义。

未获授权前，本工单保持 BLOCKED，不声称全量 suite 全绿。

## 如实定性

本刀已把 F-07 关闭到“案内实物哈希绑定 + transcript 调用记录绑定 + 消费侧独立重算”的深度，原最小反例及同族单点变异均被拒绝。transcript 仍是调用记录，不是远端节点真执行证明；完整 job spec、远端执行身份与抗伪造外部锚定仍属于 R10-9/14 台账范围，本刀没有声称关闭这些剩余面。

## 补充轮（调度方裁决后）

### 状态

**DONE — 所有业务测试通过；全量仅余两个工单已声明由调度方本机复跑的 loopback `EPERM`。**

本轮没有运行任何 git 命令，没有修改生产文件。`references/analyze-workflow.md` 的 v3 串级联越界披露按补充裁决保留，本轮未回退、未改写。

### batch_a 1/45 只读定位结论

先单跑 `python3 scripts/tests/test_repair_batch_a.py`，唯一失败为：

- case：`test_f01_shared_evm_timing_and_legal_dual_time`；
- 首个错误：`verify_recon replay_stats cutoff does not match target.as_of_block`；
- 红因：`_retarget_evm_case` 把案子从块 123 改到 1/101 时，只改了 envelope target 与部分 bundle 字段，没有同步 v3 深夹具的 `fixture_replay_stats.max_block`，也没有同步 balance transcript、time plan/receipt/transcript；
- 定性：同族旧浅夹具，不是生产语义问题。按补充裁决做最小测试适配后，`test_repair_batch_a.py` 为 `45/45 PASS`。

### 适配文件、红因与最小改动

| 文件 | 红因 | 最小改动 |
|---|---|---|
| `scripts/tests/test_repair_batch_a.py` | retarget helper 只改自报 target，未重建冻结块相关深实物；首次适配后又暴露 supply_truth 仍绑定旧 replay_stats size/sha | 调用既有 `write_deep_recon_fixtures` 重建 balance/supply/time 深夹具，并同步 supply_truth 的 replay_stats 引用；不改任何生产断言 |
| `scripts/tests/test_review_20260804_p105.py` | `bind_balance_receipt_to_snapshot` 只换 balances 引用；新 consumer 先在 supply_closure、三查 replay_stats 同源和 rows/transcript 层拒绝 | 换绑 owner 世界时机械重建 balance/supply/supply_truth 的同源 stats、rows、transcript、GMGN 空比较及 observation bundle，并刷新 accounting/reconciliation 哈希；测试意图仍是同一快照跨层绑定 |
| `scripts/tests/test_repair_batch_b.py` | 触发 P105 helper 的旧浅夹具问题 | 无需改文件；P105 helper 修复后原测试 `41/41 PASS` |
| `scripts/tests/test_a4_gate.py`（调用链追加） | 全量首轮命中本地同名浅 helper，`balance_reconciliation address sequence differs from bound balances` | 本地 helper 改为复用 P105 的 v3 深夹具适配；原 P1-05/F-03 断言层不变，定向 `23 项 PASS` |

### 最终测试输出

- `python3 scripts/tests/test_repair_batch_a.py`：`PASS batch A F-01/F-02 regressions 45/45`；
- `python3 scripts/tests/test_repair_batch_b.py`：`PASS batch B F-03/F-08 regressions 41/41`；
- `python3 scripts/tests/test_a4_gate.py`：`a4_gate 契约测试全部通过（23 项）`；
- `python3 scripts/tests/test_recon_deep_reverify.py`：`PASS test_recon_deep_reverify`；
- `python3 scripts/tests/test_audit_release_gate.py`：PASS；
- `python3 scripts/tests/test_sixlens_receipts.py`：`PASS: 六视角批①结构化回执与 fail-closed`；
- 最终 `python3 scripts/tests/run_all.py`：101 项中 99 项 PASS；唯一两项失败为：
  - `test_batch3_solana_vertical_slice.py`：`ThreadingHTTPServer(("127.0.0.1", 0), ...)` 在 `socket.bind` 报 `PermissionError: [Errno 1] Operation not permitted`；
  - `test_batch3_evm_vertical_slice.py`：同一 loopback `socket.bind EPERM`；
- 除上述两项沙箱能力限制外无业务失败；调用链追加的 `test_a4_gate.py` 已在最终全量中 PASS。
