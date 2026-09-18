# 盲审 F04：PASS

审对象：`7235c834bf6817525569f8b292be67e76e838305`。审查期间 HEAD 从 `49db004` 前进；已确认两者在指定审查范围内的 Git 对象完全一致。

a)、b)、c)、e) 均通过；d) 为 **3 项 PASS、5 项 SANDBOX-BLOCKED，无真实 FAIL**。

a) 终点判据已独立复现。通过 `git show` 读取生产源码，在内存中运行真实 `RpcPool` 和 `rpc_batch`，仅替换网络响应及文件 I/O，未依赖新增测试断言。单端点握手返回 `0x38`，业务响应严格为 `{"jsonrpc":"2.0","id":1}`。

```text
RpcPool: {"ok": false, "error": "rpc envelope: missing result (no error object)"}
rpc_batch __main__: 进程 rc=1
地址结果: {"error": "rpc envelope: missing result (no error object)"}
[SUMMARY] 1 址 | 合约 0 | EOA 0 | 失败 1
```

地址结果只有 `error`，不含 `is_contract`。另行执行生产 `__main__`，确认实际触发 `SystemExit(1)`。

b) 修法符合工单 v3，实际核过：

- [net.py:298](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/net.py:298)：缺字段及非对象响应返回固定错误，不拼接端点或响应原文。`_one` 仍只有 `{ok,result}`、`{ok,error}` 两种返回形状。
- 合法 `"result": null` 实测仍为 `{"ok": true, "result": null}`。
- [rpc_batch.py:82](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/rpc_batch.py:82)：`"0x"` 为 EOA；`"0x6080"`、`"0x00"`、`"0xaBcD"` 为合约，字节长度正确。缺失、null、奇数长度、非十六进制、int/bool/list/dict 均返回 rc 1、仅记 error、摘要失败 1。
- 源码对照确认 `_run`、`_attest_endpoint`、`_request_json`、`RETRYABLE_RPC`、receipts/raw 分支、输出及退出码逻辑、docstring 未改；`re` 原已导入。
- 原有 `0x64`、`0x2a` 断言实跑通过；rpc_batch 错链实测 rc 1，仅调用 `eth_chainId`，业务调用为 0。

c) 白名单及字节数通过。实跑结果：

```text
$ git diff --stat 2a8ee25d3a8b HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md

 scripts/lib/net.py                           |  5 +-
 scripts/lib/rpc_batch.py                     | 10 ++--
 scripts/tests/test_batch1_rpc_attestation.py | 71 ++++++++++++++++++++++++++++
 3 files changed, 82 insertions(+), 4 deletions(-)
```

仅上述三文件；maintenance 未纳入白名单判定。元数据核算：

```text
SKILL.md                 8021 B
references/**/*.md     930076 B
commands-staging/*.md    8798 B
```

`git diff --quiet HEAD -- scripts` 返回 0，被测工作区脚本与 HEAD 一致。

d) 指定测试均已执行。以下三项 **PASS，rc 0**，命令及尾行：

```text
$ python3 -B scripts/tests/test_net_result.py
PASS: net Result 显式状态与 curl_json 失败分类

$ python3 -B scripts/tests/test_batch2_capability_matrix.py
PASS B2-D: immutable release tier + capability closure + derived CLI choices

$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

以下五项均 rc 1，原因均为临时目录不可写，按约定记 **SANDBOX-BLOCKED**。命令及尾行：

```text
$ python3 -B scripts/tests/test_batch1_rpc_attestation.py
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']

$ python3 -B scripts/tests/test_evm_observation.py
test_legal_cli_flow_publishes_and_validates_both_files: FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']

$ python3 -B scripts/tests/test_evm_observation_nonempty_code.py
test_zero_supply_deployed_contract_passes_full_chain: FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']

$ python3 -B scripts/tests/test_g3_alt_collectors.py
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']

$ python3 -B scripts/tests/test_exemption_guards.py
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']
```

预检 `python3 -B -c 'import tempfile;print(tempfile.gettempdir())'` 同样报上述错误。这五项完整测试由调度方本机补验；内存验证作为单独补充证据。

e) 消费者语义及基线 RED 通过。工单 §1.4 的 10 个文件与基线逐字节一致，全部 11 个消费点已逐处检查：

| 文件及行号 | 既有失败处理 |
|---|---|
| `scripts/lib/evm_observation.py:62` | 抛 EvmObservationError |
| `scripts/lib/supply_truth_gate.py:484` | 抛 ValueError |
| `scripts/evm/accounting_gate.py:121` | 分类抛 RpcSemanticError / RpcNetError |
| `scripts/evm/verify_recon.py:264` | 抛“无有效 result” |
| `scripts/lib/time_spotcheck.py:483、501` | 两处记 RPC_ERR，最终返回 1 |
| `scripts/evm/fetch_alchemy.py:153` | 重试耗尽退出 2 |
| `scripts/evm/scan_bloxroute_seg.py:73` | 重试后记录失败段 |
| `scripts/evm/pierce_stake.py:95` | 警告后返回 None 列表 |
| `scripts/evm/multicall_balances.py:69` | 该批置 None |
| `scripts/evm/lp_positions.py:132` | parse_receipt 返回空列表 |

保留 `time_spotcheck` 的余额 null→0、`lp_positions` 的 null 收据→空列表语义。

基线通过 `git show 2a8ee25d3a8b:scripts/lib/net.py` 及对应 `rpc_batch.py` 读取并在内存加载。新增测试原函数及 getcode 循环内原断言分别执行，每个场景独立捕获结果：

| 场景 | 基线 | HEAD |
|---|---|---|
| RpcPool 缺 result | RED：AssertionError；实际 ok=True/result=None | GREEN |
| getcode missing | RED：AssertionError；rc 0、误判 EOA | GREEN |
| getcode null | RED：AssertionError；rc 0、误判 EOA | GREEN |
| getcode odd | RED：AssertionError；rc 0、误判 EOA | GREEN |
| getcode badhex | RED：AssertionError；rc 0、误判合约 | GREEN |
| getcode int | RED：TypeError；无返回码、无产物 | GREEN |
| getcode eoa / contract | GREEN | GREEN |
| RpcPool 合法 null | GREEN | GREEN |

int 场景异常原文：`TypeError: object of type 'int' has no len()`。

额外内存驱动均以 `python3 -B -c` 执行，结果尾行：

```text
PASS independent memory comparison: missing-result endpoint rejected by HEAD; baseline reproduced; null preserved; getcode matrix checked
PASS structural review: protected branches unchanged; 10 consumer files/11 sites unchanged; audited files match HEAD
PASS original added tests: baseline RED individually reproduced; HEAD GREEN; existing success/attestation assertions preserved
```

纪律披露：全程离线、只读，未改文件、未 commit，未使用 stash/checkout/reset；未读取 `~/.codex/`、memories、`F04_done.md`、`F04_red_evidence.txt` 或其他指定禁读材料。未主动打开历史 maintenance 文件；指定测试按原命令执行。报告全文已打印到 stdout，未落盘。
