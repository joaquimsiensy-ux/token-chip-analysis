# 盲审 F04：FAIL

**终点反例已解决。** 本次未通过的原因是白名单不符，以及 5 项必跑测试受环境阻断；未发现两处生产修法偏离工单。

基线为 `2a8ee25d3a8b`。审查开始 HEAD 为 `6de26a47ff8d`，结束为 `4926916999836ac2af4fb43438a8ee8fbb338d20`；期间外部仅新增 F05 提示词，`scripts` 内容未变。工作区前后干净。完整报告已打印到 stdout。

1. **F04-B1-01：验收区间包含白名单外文件。**

   文件：[blind_F04_prompt.md:6](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/blind_F04_prompt.md:6)、[construct_F05_prompt.md:1](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/construct_F05_prompt.md:1)。

   **事实：** 除允许的三个 scripts 文件及 done/evidence 外，还修改了盲审提示词的三处基线占位符，并新增 247 行 F05 提示词。前者审查开始时已存在，后者在审查期间由外部新增。

   **后果：** 不满足任务 c 和工单 §0.3 的严格白名单；属于文档范围问题。

   **建议：** 将提示词维护从 F04 验收区间分离，或由派工方明确调整白名单后重审。

2. **F04-B1-02：必跑回归未全部通过，原因是临时目录不可写。**

   文件：[test_batch1_rpc_attestation.py:188](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch1_rpc_attestation.py:188)、[test_evm_observation.py:149](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_evm_observation.py:149)、[test_evm_observation_nonempty_code.py:103](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_evm_observation_nonempty_code.py:103)、[test_g3_alt_collectors.py:197](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_g3_alt_collectors.py:197)、[test_exemption_guards.py:92](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_exemption_guards.py:92)。

   **事实：** 这五条原始测试命令均退出 1，报 `No usable temporary directory found`；其余三条退出 0。

   **后果：** 任务 d 的“全部须 PASS”未满足。这些失败不能归因为 F04 代码回归，也不能记为通过。

   **建议：** 在仓库保持只读、离线，但测试临时目录可写的环境原样补跑五项测试；无需因此修改生产逻辑。

**独立复现结果**

自行构造单端点内存后端，握手返回 `0x38`，业务严格返回 `{"jsonrpc":"2.0","id":1}`，未依赖新增测试断言。

HEAD 的 `RpcPool` 返回：

```json
{"ok": false, "error": "rpc envelope: missing result (no error object)"}
```

通过真实 `__main__` 入口执行 `rpc_batch getcode`，**进程实际退出 1**，输出：

```text
[SUMMARY] 1 址 | 合约 0 | EOA 0 | 失败 1
{"0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb": {"error": "rpc envelope: missing result (no error object)"}}
```

同一输入在基线返回 `ok=True,result=None`；getcode 返回 0、`is_contract:false`、摘要“EOA 1 | 失败 0”。

其他核验结果：

- `"0x"` 判 EOA；合法偶数十六进制判合约。奇数、非十六进制、非字符串、缺失和 null 均返回 1，地址结果仅含 `error`。
- `_one` 仍只有 ok/result、ok/error 两种返回形状；合法 `result:null` 在网络层仍为成功。
- `_run`、`_attest_endpoint`、`_request_json`、`RETRYABLE_RPC`、receipts/raw、退出码逻辑及既有测试断言未改。
- 文档字节数实测：`SKILL.md` **8021 B**、`references/**/*.md` **930076 B**、`commands-staging/*.md` **8798 B**；对应基线 diff 为空。

**消费者语义核验**

10 个消费者文件与基线逐字节相同，11 处处理均沿用既有分支：

| 消费者 | 缺 result 经网络层失败后的处理 |
|---|---|
| `evm_observation.py:62` | 抛 EvmObservationError |
| `supply_truth_gate.py:484` | 抛 ValueError |
| `accounting_gate.py:121` | 进入异常分类，本错误抛 RpcNetError |
| `verify_recon.py:264` | 抛“无有效 result” |
| `time_spotcheck.py:483、501` | 两处均记 RPC_ERR，最终返回 1 |
| `fetch_alchemy.py:153` | 重试耗尽后退出 2 |
| `scan_bloxroute_seg.py:73` | 重试后记失败段 |
| `pierce_stake.py:95` | 警告后返回 None 列表 |
| `multicall_balances.py:69` | 该批地址置 None |
| `lp_positions.py:132` | 返回空列表 |

合法 null 余额按 0 处理、跳过 null 收据等保留语义仍在，不能宣称所有消费者都会失败退出。

**新增测试的基线 RED 核验**

通过 `git show 2a8ee25d3a8b:...` 将基线源码装入内存，逐场景运行新增断言，输出用内存流承接：

| 场景 | 基线 | HEAD |
|---|---|---|
| RpcPool 缺 result | AssertionError | GREEN |
| RpcPool 合法 null | GREEN | GREEN |
| getcode missing/null/odd/badhex | 每项分别 AssertionError；原 rc 0、失败 0 | 全部 GREEN |
| getcode int | `TypeError: object of type 'int' has no len()`；无 rc、无产物 | GREEN |
| getcode eoa/contract | GREEN | GREEN |

**指定命令实跑尾行**

全部设置了 `PYTHONDONTWRITEBYTECODE=1`，保留要求的 `-B`：

```text
$ python3 -B scripts/tests/test_batch1_rpc_attestation.py
rc=1
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']

$ python3 -B scripts/tests/test_net_result.py
rc=0
PASS: net Result 显式状态与 curl_json 失败分类

$ python3 -B scripts/tests/test_batch2_capability_matrix.py
rc=0
PASS B2-D: immutable release tier + capability closure + derived CLI choices

$ python3 -B scripts/tests/test_evm_observation.py
rc=1
test_legal_cli_flow_publishes_and_validates_both_files: FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']

$ python3 -B scripts/tests/test_evm_observation_nonempty_code.py
rc=1
test_zero_supply_deployed_contract_passes_full_chain: FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']

$ python3 -B scripts/tests/test_g3_alt_collectors.py
rc=1
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']

$ python3 -B scripts/tests/test_exemption_guards.py
rc=1
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']

$ python3 -B scripts/tests/invariant_scan.py
rc=0
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

全程只读、离线，未改文件、未 commit，未使用 stash/checkout/reset。未读取 `~/.codex/`、memories 或其他禁读内容；done/evidence 仅出现在 git diff 元数据中。未主动打开历史 maintenance 文件，指定测试原样运行。
