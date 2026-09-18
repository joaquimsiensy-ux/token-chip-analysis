# 工单F04复核：退回

核心反例按拟议修改可以达标；5 个施工锚点全部正确，未发现因此新增变红的既有测试。仍需修订以下 3 项。

本轮只读、离线，未读取禁读路径，未改文件、未 commit。HEAD 为 `467ff4c`，工作树干净，指定范围相对 `8b041842` 的差异为空。下文“拟改后”均指内存替换，不是已经施工。

**F04-R1-01：getCode 校验没有验证十六进制字符。**

工单位置：[§2.2，第 43–54 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F04_rpc_envelope.md:43)。

事实：拟议代码只检查类型、前缀和长度：

```python
if (not isinstance(code, str) or not code.startswith("0x")
        or len(code) % 2 != 0):
```

工单第 50 行却说明“合法返回只有 `"0x"` 或偶数长度十六进制串”。内存执行确认，`"0xgg"` 仍被接受：

```text
rc=0
[SUMMARY] 1 址 | 合约 1 | EOA 0 | 失败 0
{"code_len": 1, "is_contract": true}
```

修订建议：利用文件已有的 `re`，将条件改为：

```python
if not isinstance(code, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", code):
```

并在现有测试文件增加非十六进制场景，要求记 `error`、返回 1。

**F04-R1-02：RED 预期与基线不符，当前测试结构无法取得所宣称的逐场景证据。**

工单位置：[§2.3，第 64–122 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F04_rpc_envelope.md:64)。

事实：`grep -n -F 'RED 证据'` 命中的第 122 行称：

```text
rpc_batch missing/null/odd/int 四场景 rc 0 且 is_contract 为 False
```

但基线 `rpc_batch.py:83-84` 为：

```python
code = r["result"] or "0x"
out[addr] = {"code_len": max(0, (len(code) - 2) // 2),
```

`123` 是真值，随后 `len(123)` 抛出：

```text
TypeError: object of type 'int' has no len()
```

因此该场景没有正常返回的 `rc`、地址结果或摘要。

此外，基线执行第一个新函数时，第 73 行断言失败，后面的 `null_result` 不执行；第二个新函数在 `missing` 场景断言失败，后五个场景也不执行。“逐个调用两个新用例”不足以证明第 122 行所称的全部 RED／GREEN→GREEN。

修订建议：逐场景独立执行并记录结果；把 `int` 的基线预期改为上述异常。合法 null、EOA、合约三个对照必须独立取得基线证据。缺字段场景还应断言摘要包含“失败 1”和“EOA 0”。

**F04-R1-03：需明确保留的三端点 failover 缺陷及新增触发条件。**

工单位置：[§0.4，第 12 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F04_rpc_envelope.md:12)、§2.1 第 39 行。

事实：基线 `net.py` 原文：

```python
354: for offset in range(len(self.endpoints)):
355:     index = (self._active_index + offset) % len(self.endpoints)
...
372:     self._active_index = index
```

循环过程中修改了下一轮计算使用的 `_active_index`。三端点 A、B、C 中，A/B 返回缺字段、C 正常时，拟改后的实际请求顺序为：

```text
A: eth_chainId → eth_getCode
B: eth_chainId → eth_getCode
A: eth_chainId → eth_getCode
```

C 未被访问，最终返回失败。基线以 A/B 超时替代缺字段时也出现同样顺序，证明这是既有缺陷；本段会让缺字段响应开始触发它。

修订建议：若继续保持 `_run` 不改，应在工单及台账明确该继承限制。若本段要求保证遍历全部备用端点，则需同步修订 §0.4，并纳入三端点回归。单端点不存在此问题。

其余逐项核对结果如下。

**a）锚点**

实际执行了 `grep -n -F`：

| 文件 | 锚文本 | 命中数 | 基线行号 |
|---|---|---:|---:|
| `net.py` | `return {"ok": True, "result": j.get("result")}` | 1 | 298 |
| `rpc_batch.py` | `            if r["ok"]:` | 1 | 82 |
| `rpc_batch.py` | `"is_contract": code not in ("0x", "0x0", None)}` | 1 | 85 |
| `test_batch1_rpc_attestation.py` | `def main():` | 1 | 327 |
| 同上 | `    test_remaining_formal_entrypoints_wrong_chain_zero_business()` | 1 | 334 |

第 326 行确为空行，测试插入位置正确。

**b）插入位置、循环和摘要**

- 已完整核对 `net.py:271-298`、`:349-385`。新增校验位于错误处理之后，覆盖 `:287-289` 重试重新赋值的 `j`；内存执行“可重试错误→缺字段”得到预期 envelope 错误。
- 单端点因 `offset + 1 < len(self.endpoints)` 为假，不会切换或重复请求；双端点已验证会重新握手后访问第二端点。三端点限制见 F04-R1-03。
- 拟议 `continue` 位于 `for addr, r in zip(...)` 内，编译通过。
- `rpc_batch.py:88-90` 分别统计合约与错误，再相减得到 EOA。新增错误项不会计入 EOA；`load_list()` 已去重，计数基础一致。

**§1.4：10 个消费者、11 处判断均已打开核实**

| 消费者及基线位置 | `ok=False` 的实际行为 |
|---|---|
| `lib/evm_observation.py:62-64` | 抛 `EvmObservationError`。 |
| `lib/supply_truth_gate.py:484-486` | 抛 `ValueError`。 |
| `evm/accounting_gate.py:121-126` | 分类抛异常；新增 envelope 文案走 `RpcNetError`。 |
| `evm/verify_recon.py:264-265` | 抛“eth_call 无有效 result”。 |
| `lib/time_spotcheck.py:483-485` | 余额项记 `RPC_ERR`；`:528-546` 返回 1。 |
| 同上 `:501-503` | 收据项记 `RPC_ERR`；null 收据亦进入此分支。 |
| `evm/fetch_alchemy.py:153-176` | 错误分支重试，耗尽后 `sys.exit(2)`。 |
| `evm/scan_bloxroute_seg.py:73-98` | 转为 `None`，重试后记录失败段；`:109` 仍返回 0。 |
| `evm/pierce_stake.py:95-103` | 重试后打印警告，返回 `[None] * len(addrs)`。 |
| `evm/multicall_balances.py:69-81` | 重试耗尽后将该批地址结果置为 `None`。 |
| `evm/lp_positions.py:132-134` | `parse_receipt()` 返回空列表；混合结果中的失败记录被跳过。 |

“均已有处理分支”这一字面断言成立；它不能解释为“所有消费者都会显式失败退出”。

**c）既有测试回归面**

已解析 `run_all.py`，确认登记 **143 个不同的 `test_*.py`**，并扫描其源码及相关辅助代码。预期因本段新增变红的既有测试集合为 **空**；这是静态审计结论，并非 143 文件实跑结果。

具体证据：

- `_request_json` 的 mock 仅出现在 `test_batch1_rpc_attestation.py:30/202/231/243/255/268/317` 和 `test_r7_findings.py:368`。正常业务响应均带 `result`。
- `test_batch1_rpc_attestation.py:75-76` 确有无 `result` 的 error 响应，但用于握手失败测试，在 `_attest_endpoint` 内被拒，不经过拟改出口。
- 未发现断言 `rpc_batch` 将 `None`／`"0x0"` 判为 EOA 的既有测试；登记测试中没有 `is_contract` 断言。
- §0.8 未列的 `test_evm_observation_nonempty_code.py:48/53` 使用自己的 `FakePool`；其中 `"0x0"` 是 `eth_call` 短返回测试，不经过本次修改。`test_g3_alt_collectors.py:50/104` 同样替换整个 pool。
- §1.5 成立：`:115/133` 两个成功断言在基线与内存拟改版均通过；`:296-298` 的 rpc_batch 错链测试在握手阶段终止，静态确认不受影响。

**d）新用例及加载路径**

完整 `test_batch1_rpc_attestation.py` 会创建临时目录、写文件；本沙箱只读，因此未运行完整文件。已执行其中 5 个无落盘既有测试函数，基线与拟改版均通过；第一个新测试取得基线 RED、拟改后 GREEN。

第二个新测试按场景执行真实 `main()` 的无落盘分支，结果为：

| 场景 | 基线 | 拟改后 |
|---|---|---|
| 缺 `result` | 返回 0，EOA | 返回 1，`error` |
| `result=null` | 返回 0，EOA | 返回 1，`error` |
| `"0x0"` | 返回 0，EOA | 返回 1，`error` |
| `123` | `TypeError` | 返回 1，`error` |
| `"0x"` | 返回 0，EOA | 同左 |
| `"0x6080"` | 返回 0，合约 | 同左 |

`load()` 二次加载没有导入障碍：测试文件 `:17` 已插入 `scripts/lib`，`rpc_batch.py:29` 也自行插入所在目录；`:30-31` 的两个导入可解析。实际二次加载确认使用同一个 `net.attested_rpc_pool`，mock 能生效。

**e）白名单、不改项与守卫**

当前两处生产修改及测试修订可容纳于 §0.3 白名单；除 F04-R1-03 所需的边界说明外，§0.4 保持握手、传输重试、receipts/raw 和退出码逻辑不改是自洽的。

已执行 `invariant_scan` 的实际扫描与校验函数：基线和内存拟改版均为 `errors=[]`，扫描清单完全相同，无须修改 manifest。

`test_batch4_invariant_guards.py` 已静态核对，没有本段导致的新登记要求；其临时文件注入测试未运行。`test_exemption_guards.py` 的三个只读检查已通过，但其 `EXEMPT_MODULE` 是 **`multicall_balances`**，并非 rpc_batch 的专用发布边界守卫。

另已运行 `test_net_result.py`、`test_batch2_capability_matrix.py` 的基线 `main()`，均通过。文档大小仅通过 `stat` 核对，分别为 **8021／930076／8798**，与工单一致。旧 getcode 产物不会自动重算，工单第 131 行已明确不追溯。

**f）终点判据**

指定单端点反例按工单修改后满足终点：

1. 握手返回 `"0x38"`，通过。
2. 基线 `net.py:298` 的替换块拒绝缺字段响应；按原样落地后为第 300 行，文案为：
   ```text
   rpc envelope: missing result (no error object)
   ```
3. 进入既有 `rpc_batch.py:86-87`，该地址仅记 `{"error": ...}`。
4. 既有 `:88-90` 输出：
   ```text
   [SUMMARY] 1 址 | 合约 0 | EOA 0 | 失败 1
   ```
5. 既有 `:123-125` 返回 1。

以上业务路径已在内存拟改版执行确认；`--out` 落盘分支仅静态核对，未实际写文件。

**g）Q5／Q6 边界**

Q5 不校验 `id/jsonrpc`，不会取消本次对缺字段的拒绝。

Q6 在网络层确实区分两者：缺键返回 `ok=False`，键在场且为 null 返回 `ok=True, result=None`。getCode 消费者随后拒绝 null，符合方法自身要求。

但 Q6 不代表所有消费者已严格验证类型。例如 `time_spotcheck.py:487` 仍把余额调用的 null 当作 0；`lp_positions.py:132-134` 会跳过 null 收据。这些是保留的消费者语义，不能在完成报告中声称本段一并修复。
