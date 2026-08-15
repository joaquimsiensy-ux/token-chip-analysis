# 工单 A 完工摘要：EVM 观测件协议库 + CLI producer + 协议负测

> 完工日期：2026-08-14
> 边界：只完成工单 A；未改 `supply_truth_gate.py`、`accounting_gate.py`、`shared_release_receipt.py`、`handoff_manifest.py`、正式 E2E/capability/契约注册表、文档或版本。
> 施工期间未执行任何 git 命令。

## 1. 改动文件清单

| 文件 | 动作 | 本单内容 |
|---|---|---|
| `scripts/lib/evm_observation.py` | 新建 | EVM 冻结块观测协议、bundle builder、公共 validator、transcript 三元组重验 |
| `scripts/evm/observe_supply.py` | 新建 | formal CLI producer；旧件 quarantine、显式链身份观测、staging 自验、双件事务发布、ERROR side receipt 与端点脱敏 |
| `scripts/tests/test_evm_observation.py` | 新建 | transport-only fake 下 10 项协议/失败分支/合法发布回归 |
| `scripts/tests/invariant_scan.py` | 修改 | 新 producer 的 failure-artifact coverage 与 `canonical_artifacts=2` contract |
| `scripts/tests/invariant_manifest.json` | 修改 | 新增 2 producer、1 consumer、1 `net.py` transport、1 dual-file atomic write；对应 minimum floor 分别上调 2/1/1/1 |
| `scripts/tests/run_all.py` | 修改 | 挂载 `test_evm_observation.py` |
| `maintenance/repair-20260814-evmobs/workorder_A_done.md` | 新建 | 本完工证据 |

## 2. 施工首步 rg 同族复核实况

在任何代码/测试写入前执行工单 §2 的四条命令，实况如下：

- `rg -l "solana-observation-bundle" scripts/`：命中 `shared_release_receipt.py`、`scan_token_accounts.py`、`accounting_gate_sol.py`、`supply_truth_gate.py`、`solana_observation.py`、`invariant_manifest.json`、`test_repair_batch_b.py`、`test_batch3_solana_producers.py`、`test_repair_batch_d.py`。
- `rg -n "evm-observation" scripts/ references/`：施工前 0 命中。
- `rg -n "endpoint_fingerprint" scripts/`：施工前仅 `endpoint_identity.py` 定义，以及 `solana_observation.py`、`fetch_sqd_transfers_v2.py`、`decode_txs_v2.py` 三处调用。
- `rg -n "def attest" scripts/lib/net.py`：命中 `net.py:363`；施工前无 EVM 业务方显式调用。

## 3. `evm-observation-bundle/v1` 字段实况

后续工单按以下磁盘实况消费，不应猜测或改名。

```text
schema = "evm-observation-bundle/v1"
target
  chain: str                         # formal: eth | bsc | base
  token: str                         # 小写 0x + 40 hex
  as_of_block: int
producer
  path: str                          # scripts/evm/observe_supply.py
  sha256: str
mode = "formal"
inputs
  transcript
    path: str                        # 相对 bundle 所在案根
    size: int
    sha256: str
attestation
  expected_chain_id: int             # chain_registry
  observed_chain_id: int             # RpcPool.attest() 归一化结果
  endpoint
    public_origin: str
    sha256: str                      # 完整私有 endpoint 的内容指纹
anchor
  number: int
  block_hash: str                    # 0x + 64 hex
  parent_hash: str                   # 0x + 64 hex
  timestamp: int
  recheck_block_hash: str            # 必须等于 block_hash
  tip_block: int
  confirmations: int                 # tip_block - number
supply
  total_supply_raw: str              # 非负十进制字符串
  zero_balance_raw: str              # 非负十进制字符串
  dead_balance_raw: str              # 非负十进制字符串
  block_binding = "eip1898-block-hash"
code
  runtime_code_sha256: str            # eth_getCode 返回字节的 SHA-256
verdict = "PASS"
exit_code = 0
```

Transcript 实物当前是顶层 JSON array，无额外 schema 包装。每行字段严格为：

```text
{seq: int, method: str, params: JSON value, result: JSON value}
```

固定 8 行顺序：

1. `eth_chainId`，`params=[]`，`result` 当前为 `RpcPool.attest()` 归一化后的正整数；
2. `eth_getBlockByNumber(hex(as_of_block), false)`，result 保留节点 block object；
3. `eth_blockNumber`，result 保留节点 hex quantity；
4. `eth_call totalSupply`；
5. `eth_call balanceOf(ZERO)`；
6. `eth_call balanceOf(DEAD)`；
7. `eth_getCode(token, hex(as_of_block))`；
8. 再次 `eth_getBlockByNumber(hex(as_of_block), false)`。

三笔 `eth_call` 的第二参数均严格为
`{"blockHash": anchor.block_hash, "requireCanonical": true}`，无块号降级路径。validator 在 `bundle_path` 在场时同时重验：信封 path/size/hash、bundle 磁盘对象等值、seq/method/完整 params/result、三笔十进制值、两次块头、tip、chainId、runtime code 摘要。

诚实边界：该 bundle 证明的是案内内容绑定与可复算一致性，不证明远端节点真实执行，也不提供案外 blockHash 真实性锚；`runtime_code_sha256` 只绑定该地址该块的 runtime code，不声称防代理升级。

## 4. 测试红 → 绿证据

### 4.1 首轮红态

只创建 `test_evm_observation.py`、尚未创建协议库/CLI 时执行：

```text
python3 scripts/tests/test_evm_observation.py
exit 1
```

输出逐项列出 9 条红态：

- `test_wrong_chain_id_zero_business_calls`: `No module named 'evm_observation'`
- `test_invalid_eth_call_result_rejected`: `No module named 'evm_observation'`
- `test_pre_post_block_hash_mismatch_rejected`: `No module named 'evm_observation'`
- `test_eip1898_unsupported_fails_closed_without_outputs`: `observe_supply.py` 不存在
- `test_declared_as_of_block_mismatch_rejected`: `No module named 'evm_observation'`
- `test_transcript_method_and_params_tamper_rejected`: `No module named 'evm_observation'`
- `test_prepublication_self_validation_failure_leaves_no_canonicals`: `observe_supply.py` 不存在
- `test_error_path_redacts_endpoint_query`: `observe_supply.py` 不存在
- `test_legal_cli_flow_publishes_and_validates_both_files`: `observe_supply.py` 不存在

这证明测试先于实现落盘，基线不能假绿。

### 4.2 六视角①追加反例的独立红态

字段来源自审发现 RpcPool failover 可能让显式 chainId 与最终 endpoint 指纹错配，先加
`test_endpoint_failover_cannot_rebind_attestation`，修复前实跑：

```text
exit 1
test_endpoint_failover_cannot_rebind_attestation:
invalid EVM observation was accepted; expected 'endpoint'
```

加入“显式 attest 后 endpoint 必须在每次业务调用后保持全等”的 fail-closed 守卫后转绿。

### 4.3 最终逐条绿态

最终专项：

```text
python3 scripts/tests/test_evm_observation.py
exit 0
PASS EVM observation bundle protocol: 10/10
```

| 测试 | 最终命中事实 |
|---|---|
| `test_wrong_chain_id_zero_business_calls` | observed chainId 不等即拒，attest 外业务调用数为 0 |
| `test_invalid_eth_call_result_rejected` | 非 `0x` hex 的 eth_call result 拒绝 |
| `test_pre_post_block_hash_mismatch_rejected` | 前后块哈希不等拒绝 |
| `test_eip1898_unsupported_fails_closed_without_outputs` | `-32602` 类错误非零退出；不降级块号；无 canonical bundle/transcript |
| `test_declared_as_of_block_mismatch_rejected` | 返回块号与 `--as-of-block` 声明不等拒绝 |
| `test_endpoint_failover_cannot_rebind_attestation` | 显式 attest 后 endpoint 漂移拒绝 |
| `test_transcript_method_and_params_tamper_rejected` | 保留 result、只改 method 或 params，重建合法 input hash 后仍被业务 validator 拒绝 |
| `test_prepublication_self_validation_failure_leaves_no_canonicals` | 注入同一 validator 异常；双 canonical 均不落，唯一 ERROR side receipt 在场 |
| `test_error_path_redacts_endpoint_query` | stderr 与 ERROR receipt 均不含 `api-key`、secret value、fragment |
| `test_legal_cli_flow_publishes_and_validates_both_files` | transcript + bundle 双件事务发布，磁盘 consumer validator 通过 |

## 5. invariant 与全量回归

### invariant_scan

实现后首次扫描先真实报出 6 个登记缺口（2 producer、1 consumer、1 transport、1 atomic、1 failure coverage），据此补齐；最终：

```text
python3 scripts/tests/invariant_scan.py
exit 0
PASS invariant manifest: receipt_producers=59, receipt_consumers=77,
transport_calls=63, atomic_writes=52, formal_entrypoints=58, exceptions=0
```

双 canonical failure contract 实况：`scripts/evm/observe_supply.py:main` 的
`canonical_artifacts=2`，可达调用包含两次 `quarantine_current`、`publish_txn` 与
`publish_error_receipt`；coverage protection 含 `self_quarantine`。

### run_all

沙箱内首跑只有两个 loopback fixture 在 `socket.bind(127.0.0.1, 0)` 被环境
`PermissionError: [Errno 1] Operation not permitted` 拦截，其余测试通过；未将其记为全绿。
允许 loopback 后，对并发施工稳定后的最终代码快照原样复跑：

```text
python3 scripts/tests/run_all.py
exit 0
全部通过
```

最终输出明确包含：

- `test_batch3_solana_vertical_slice.py` PASS；
- `test_batch3_evm_vertical_slice.py` PASS（ETH/BSC/Base）；
- `test_evm_observation.py` PASS 10/10；
- `invariant_scan.py` PASS；
- 当时全量 SUITE 的其余项全部 PASS。

## 6. 六视角①②自审结论

### ① 字段来源审计：PASS（并在自审中关闭 1 个新引入接受面）

- `target.chain/token/as_of_block` 来自 CLI 声明，但不是观测事实；chain 受 formal choices 与 registry chainId 交叉约束，token 受地址形态/小写约束，as-of 必须与返回块头 number 全等。
- `observed_chain_id` 来自显式 `pool.attest()`；`expected_chain_id` 来自 `chain_registry`；validator 再把 target.chain、expected、observed 三方对齐。
- endpoint 指纹来自显式 attest 的同一 endpoint；每次后续业务调用后检查 endpoint 未漂移。该项是自审新发现，已留下独立红→绿反例。
- anchor 四字段来自第一次块头，tip 来自 `eth_blockNumber`，confirmations 本地相减；第二次块头提供 recheck hash。磁盘 validator 从 transcript result 独立重算并对齐。
- 三个 supply raw 值只来自三笔 EIP-1898 hash-bound eth_call；validator 同时验 method、to、calldata、block selector、result，不能靠自报标量过闸。
- runtime code 摘要从 transcript 中 `eth_getCode` 原始 hex 字节重算；不是调用者自报摘要。
- producer/input path/size/sha256 由 receipt kernel 从真实源码与 staging transcript 实物生成；消费时由独立 `receipt_validate` 重验。
- 未发现剩余案内裸自报字段。案外 RPC/block 真实性明确留作本工程诚实边界，不在本单冒充 CLOSED。

### ② 失败分支审计：PASS

- chainId 错、块头/数量/hex/地址/时间戳非法、tip 落后、声明块不符、EIP-1898 不支持、三调用数量不全、runtime code 非法、块哈希复验不等、endpoint 漂移均直接 raise，CLI exit 1。
- 路径冲突 exit 2；旧件 quarantine 失败 exit 1；不存在 warning 后继续发布 PASS 的路径。
- 成功路径必须先完成对象级同一 validator 自验，再进入 `publish_txn`；validator 注入失败时两份 canonical 均不存在。
- 失败只尝试唯一 ERROR side receipt，写 ERROR receipt 自身失败仍保持 exit 1；ERROR 字符串先做 endpoint/proxy 脱敏。
- `publish_txn` 失败沿 receipt kernel 回滚语义传播，不会被 CLI 吞成 exit 0。
- invariant failure-artifact contract 与 coverage 已登记，后续删除 quarantine/error 路径会使全量门禁转红。

结论：工单 A 范围完工；后续工单可按 §3 的字段实况接入 accounting/supply_truth/shared/handoff，不应把本单 bundle 解释为案外真实性证明。
