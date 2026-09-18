# 工单F04复核：退回

核心修法正确，`rpc_missing_result` 终点成立；仍有两处施工说明需要修订。

**F04-R2-01：新增 import 的插入位置与字母序要求冲突。**

工单位置：[§2.3，第 61 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F04_rpc_envelope.md:61)。

事实：基线第 5–8 行依次为 `asyncio`、`csv`、`importlib.util`、`json`。将 `contextlib`、`io` 都紧接第 5 行插入，会得到：

```python
import asyncio
import contextlib
import io
import csv
import importlib.util
import json
```

代码可以编译，但不符合工单要求的字母序。

修订建议：`import contextlib` 插在基线 `:5 import asyncio` 后；`import io` 插在基线 `:7 import importlib.util` 后。这两个锚均唯一。

**F04-R2-02：Q13 将三端点反例推广成了多端点的必然行为。**

工单位置：[§4，第 147 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F04_rpc_envelope.md:147)；同步涉及[台账 Q13，第 17 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/code_change_pending.md:17)。

事实：`_run:355` 根据当前 `_active_index` 加 offset 计算端点，`:372` 又更新 `_active_index`。新建 pool、握手均正常时，内存执行结果如下：

| 条件 | 实际访问顺序 | 结果 |
|---|---|---|
| 三端点，A/B 业务失败，C 正常 | A→B→A | 失败 |
| 四端点，A/B 业务失败，C/D 正常 | A→B→D | 成功 |
| 八端点，仅 C 业务正常 | A→B→D→G→C | 成功 |

因此，“三端点及以上……第三个端点不会被访问（A→B→A），最终返回失败”不准确。上述轮转在基线用超时、拟改版用缺 `result` 响应均复现，属于既有行为。

修订建议：工单和 Q13 将确定性反例限定为“三端点”；更多端点表述为“也可能重复访问或漏访，实际顺序取决于端点数和各次结果”。保留 §0.4／§4 已明确的“本段不改 `_run`”。

**其余实际核验结果**

**a）R1-01 已解决。**

完整校验条件恰好接受 `"0x"` 和其后由十六进制字符对组成的字符串，拒绝 `"0x0"`、`"0xgg"`；`isinstance` 短路拒绝非字符串，不会将其交给 `re.fullmatch`。`re` 已在基线第 26 行导入，§2.3 已加入 `badhex`。

**b）R1-02 的取证逻辑已解决。**

helper 每次独立创建 backend、输出路径和 stdout 缓冲区，mock 在退出时恢复。测试函数本身仍会在首个失败断言处停止，但 §0.7／§2.3 明确要求 RED 驱动逐场景调用 helper、分别捕获异常，可以取得独立证据。

`rpc_batch.py:90` 是普通 `print(...)`，没有 `file=sys.stderr`；实际执行确认 `redirect_stdout` 能捕获 `[SUMMARY]`。

| 场景 | 基线实际结果 | 按 v2 拟改后的结果 |
|---|---|---|
| missing | rc 0，`is_contract=False` | rc 1，仅记 `error` |
| null | rc 0，`is_contract=False` | rc 1，仅记 `error` |
| odd：`0x0` | rc 0，`is_contract=False` | rc 1，仅记 `error` |
| badhex：`0xgg` | rc 0，`is_contract=True` | rc 1，仅记 `error` |
| int：123 | `TypeError: object of type 'int' has no len()`；无 rc、产物或摘要 | rc 1，仅记 `error` |
| eoa：`0x` | rc 0，`is_contract=False` | 保持一致 |
| contract：`0x6080` | rc 0，`is_contract=True`，`code_len=2` | 保持一致 |

拟改后的五个异常场景均输出“合约 0 / EOA 0 / 失败 1”。`int` 和 `badhex` 的 RED 预期正确。网络层合法 `result=null` 已独立验证：基线与拟改版均保持 `ok=True, result=None`。

**c）R1-03 的三端点事实及保留边界已登记。**

§0.4、§4 与 Q13 均明确保留 `_run`。单端点不重打、双端点切换后重新握手的行为已执行确认；需修订的是上述端点数量概括。

**d）§2 七处锚文本的命中数和行号均正确。**

| 文件 | 锚文本 | 命中数 | 基线行号 |
|---|---|---:|---:|
| `scripts/lib/net.py` | `return {"ok": True, "result": j.get("result")}` | 1 | 298 |
| `scripts/lib/rpc_batch.py` | `if r["ok"]:`，含指定缩进 | 1 | 82 |
| 同上 | `"is_contract": code not in ("0x", "0x0", None)}` | 1 | 85 |
| 同上 | `import re` | 1 | 26 |
| `scripts/tests/test_batch1_rpc_attestation.py` | `import asyncio` | 1 | 5 |
| 同上 | `def main():` | 1 | 327 |
| 同上 | `test_remaining_formal_entrypoints_wrong_chain_zero_business()`，含指定缩进 | 1 | 334 |

测试文件第 326 行确为空行；已有 `json/sys/tempfile/Path/mock` 分别位于第 8/11/12/13/14 行。§2 引用的错误处理、摘要及退出码代码位置也与基线一致。

§0.8 新增的两个测试文件均存在：

- `test_evm_observation_nonempty_code.py` 检查消费者对运行时代码及 ABI 返回值的处理；第 48 行的 `"0x0"` 属于 `eth_call`。
- `test_g3_alt_collectors.py` 覆盖包括 `fetch_alchemy` 在内的采集器错误处理。

两者作为消费者补充回归有相关性，但均使用 FakePool，绕过真实网络层，不能替代新增的 envelope/getcode 测试。

**e）终点判据成立。**

按[裁决第 22 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/ruling_20260918.md:22)的单端点反例，握手 `0x38` 通过；缺 `result` 在 `_one` 被判失败，进入 getcode 既有错误分支。内存执行结果为：

```text
rc=1
该地址结果：{"error": "rpc envelope: missing result (no error object)"}
[SUMMARY] 1 址 | 合约 0 | EOA 0 | 失败 1
```

结果不含 `is_contract`。

本轮 HEAD 为 `a1541898d953`；`scripts/` 状态为空，与 `8b041842` 的差异为空。使用工单原文代码块、真实业务函数和内存文件替身验证：两个新增测试函数通过，五个无需落盘的既有测试在基线／拟改版均通过。未运行需真实临时文件的完整 §0.8 测试清单。

本轮离线、未修改文件、未 commit；未读取 `~/.codex/`、memories 或其他禁读路径。完整报告已打印到 stdout，未保存报告文件。
