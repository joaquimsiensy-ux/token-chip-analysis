# 施工 F04：完成

已按工单 v3 完成 §2.1–§2.3。RPC 业务响应缺少 `result` 键或不是对象时，返回固定 envelope 错误；合法 `result=null` 在网络层仍成功。`rpc_batch getcode` 只接受 `0x` 或偶数长度十六进制串，非法值记 error、计入失败并退出 1。

先仅加入测试，独立取证 9 个场景（6 RED、3 GREEN），再修改生产代码。§0.8 的 14 项定向命令全部通过。代码与工单规定的替换结果逐字节一致，没有方案差异或本次停工点。

## 1. 开工基线与行号锚（§0.1、§0.5）

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。开工分支为 `main`；HEAD 仅作记录，基线判定采用工单指定的两项空输出检查。

```console
$ git rev-parse HEAD
2a8ee25d3a8bfc9de4af7ee51b9ece55319d2c71
$ git branch --show-current
main
$ git status --short
$ git diff --stat 8b041842 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

上述 `git status --short` 与指定的 `git diff --stat` 均无输出，满足开工条件。所有文本锚均实际执行 `grep -n -F`，命中恰 1 处且行号一致：

```text
scripts/lib/net.py | grep -n -F '            return {"ok": True, "result": j.get("result")}'
298:            return {"ok": True, "result": j.get("result")}
scripts/lib/rpc_batch.py | grep -n -F 'import re'
26:import re
scripts/lib/rpc_batch.py | grep -n -F '            if r["ok"]:'
82:            if r["ok"]:
scripts/lib/rpc_batch.py | grep -n -F '                             "is_contract": code not in ("0x", "0x0", None)}'
85:                             "is_contract": code not in ("0x", "0x0", None)}
scripts/tests/test_batch1_rpc_attestation.py | grep -n -F 'import asyncio'
5:import asyncio
scripts/tests/test_batch1_rpc_attestation.py | grep -n -F 'import importlib.util'
7:import importlib.util
scripts/tests/test_batch1_rpc_attestation.py | grep -n -F 'def main():'
327:def main():
scripts/tests/test_batch1_rpc_attestation.py | grep -n -F '    test_remaining_formal_entrypoints_wrong_chain_zero_business()'
334:    test_remaining_formal_entrypoints_wrong_chain_zero_business()
```

同时核实测试文件基线 `:5-14` 已有 json/sys/tempfile/Path/mock；`:326` 为插入空行；`:115` / `:133` 的 `0x64` / `0x2a` 断言和 `:296-298` 的 rpc_batch 错链用例均吻合。`rpc_batch.py:26 import re` 已存在，无需新增生产 import。

## 2. §2 各处 git diff 原文

```diff
diff --git a/scripts/lib/net.py b/scripts/lib/net.py
index 8862da1..6820280 100644
--- a/scripts/lib/net.py
+++ b/scripts/lib/net.py
@@ -295,7 +295,10 @@ class RpcPool:
                     detail = redact_endpoint_text(err.get("message"), [endpoint])
                     return {"ok": False,
                             "error": f"rpc {err.get('code')}: {detail[:120]}"}
-            return {"ok": True, "result": j.get("result")}
+            if not isinstance(j, dict) or "result" not in j:
+                # JSON-RPC envelope 缺 result 且无 error：提供商/代理/缓存的空壳包，不是成功（F04）
+                return {"ok": False, "error": "rpc envelope: missing result (no error object)"}
+            return {"ok": True, "result": j["result"]}
 
     async def _attest_endpoint(self, client, bucket, endpoint):
         if self.expected_chain_id is None:
diff --git a/scripts/lib/rpc_batch.py b/scripts/lib/rpc_batch.py
index a9f0538..1fd0012 100644
--- a/scripts/lib/rpc_batch.py
+++ b/scripts/lib/rpc_batch.py
@@ -80,9 +80,13 @@ def main():
         out = {}
         for addr, r in zip(addrs, res):
             if r["ok"]:
-                code = r["result"] or "0x"
-                out[addr] = {"code_len": max(0, (len(code) - 2) // 2),
-                             "is_contract": code not in ("0x", "0x0", None)}
+                code = r["result"]
+                if not isinstance(code, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", code):
+                    # eth_getCode 合法返回只有 "0x" 或偶数长度十六进制串；其余记失败不猜 EOA（F04）
+                    out[addr] = {"error": f"eth_getCode 非法返回 {type(code).__name__}"}
+                    continue
+                out[addr] = {"code_len": (len(code) - 2) // 2,
+                             "is_contract": code != "0x"}
             else:
                 out[addr] = {"error": r["error"]}
         n_c = sum(1 for v in out.values() if v.get("is_contract"))
diff --git a/scripts/tests/test_batch1_rpc_attestation.py b/scripts/tests/test_batch1_rpc_attestation.py
index 64c36f4..e8e4e08 100644
--- a/scripts/tests/test_batch1_rpc_attestation.py
+++ b/scripts/tests/test_batch1_rpc_attestation.py
@@ -3,8 +3,10 @@
 from __future__ import annotations
 
 import asyncio
+import contextlib
 import csv
 import importlib.util
+import io
 import json
 import os
 import subprocess
@@ -324,6 +326,73 @@ def test_remaining_formal_entrypoints_wrong_chain_zero_business():
             assert rc != 0 and methods == ["eth_chainId"], (name, rc, methods)
 
 
+def test_business_envelope_missing_result():
+    """F04：握手正常、业务响应缺 result 键 → ok=False；合法 result=null 仍 ok=True。"""
+    async def missing(client, bucket, method, url, *, json_body=None, attempts=6):
+        if json_body["method"] == "eth_chainId":
+            return {"jsonrpc": "2.0", "id": 1, "result": "0x38"}
+        return {"jsonrpc": "2.0", "id": json_body["id"]}
+
+    pool = net.RpcPool("http://envelope", expected_chain_id=56)
+    got = run_with_backend(pool, missing)
+    assert got["ok"] is False and "result" in got["error"], got
+
+    async def null_result(client, bucket, method, url, *, json_body=None, attempts=6):
+        if json_body["method"] == "eth_chainId":
+            return {"jsonrpc": "2.0", "id": 1, "result": "0x38"}
+        return {"jsonrpc": "2.0", "id": json_body["id"], "result": None}
+
+    pool = net.RpcPool("http://envelope", expected_chain_id=56)
+    got = run_with_backend(pool, null_result, method="eth_getTransactionReceipt")
+    assert got == {"ok": True, "result": None}, got
+
+
+def _getcode_scenario(module, td, name, payload):
+    """跑一次真实 rpc_batch.main()（握手 0x38 正常，业务返回按 payload 构造），返回 (rc, 该地址结果, stdout)。"""
+    address = "0x" + "b" * 40
+
+    async def backend(client, bucket, method, url, *, json_body=None, attempts=6):
+        if json_body["method"] == "eth_chainId":
+            return {"jsonrpc": "2.0", "id": 1, "result": "0x38"}
+        body = {"jsonrpc": "2.0", "id": json_body["id"]}
+        if payload is not None:
+            body.update(payload)
+        return body
+
+    out = Path(td) / f"{name}.json"
+    argv = ["rpc_batch.py", "http://envelope", "getcode", address,
+            "--chain", "bsc", "--out", str(out)]
+    buf = io.StringIO()
+    with mock.patch.object(sys, "argv", argv), mock.patch.object(
+            net, "_request_json", side_effect=backend), contextlib.redirect_stdout(buf):
+        rc = module.main()
+    return rc, json.loads(out.read_text(encoding="utf-8"))[address], buf.getvalue()
+
+
+def test_rpc_batch_getcode_rejects_malformed_code():
+    """F04：rpc_batch getcode 对缺 result / null / 奇数长度 / 非十六进制 / 非字符串记 error 且退出 1，
+    摘要"失败 1 / EOA 0"；"0x" 为 EOA、偶数长度十六进制为合约。"""
+    module = load("scripts/lib/rpc_batch.py", "batch1_rpc_batch_f04")
+    scenarios = [
+        ("missing", None, False),          # 缺 result 键
+        ("null", {"result": None}, False),
+        ("odd", {"result": "0x0"}, False),
+        ("badhex", {"result": "0xgg"}, False),
+        ("int", {"result": 123}, False),
+        ("eoa", {"result": "0x"}, True),
+        ("contract", {"result": "0x6080"}, True),
+    ]
+    with tempfile.TemporaryDirectory(prefix="batch1-rpc-f04-") as td:
+        for name, payload, expect_ok in scenarios:
+            rc, got, stdout = _getcode_scenario(module, td, name, payload)
+            if expect_ok:
+                assert rc == 0 and "error" not in got, (name, rc, got)
+                assert got["is_contract"] is (name == "contract"), (name, got)
+            else:
+                assert rc == 1 and "error" in got and "is_contract" not in got, (name, rc, got)
+                assert "失败 1" in stdout and "EOA 0" in stdout, (name, stdout)
+
+
 def main():
     test_wrong_chain_zero_business()
     test_attestation_failures()
@@ -332,6 +401,8 @@ def main():
     test_registry_factory_rejects_missing_identity()
     test_each_formal_callsite_wrong_chain_zero_business()
     test_remaining_formal_entrypoints_wrong_chain_zero_business()
+    test_business_envelope_missing_result()
+    test_rpc_batch_getcode_rejects_malformed_code()
     print("PASS B1-B RPC session: wrong-chain zero business/fail-closed/correct/failover")
     return 0
 
```

## 3. 先 RED 后 GREEN（§0.7、§2.3）

RED 取证前，已比对两个生产文件与 `8b041842` 无差异，并校验下列 SHA-256。测试文件先加入两个用例、辅助函数、import 与 main 调用，生产文件随后才修改。

```text
85fed436a2d1d6a1c676d9f6660c9bee6403a1d6392e0ea755ad43897ddb3f1a  scripts/lib/net.py
f993c16ea846945e24c8d403d5962d3d2deae7c6358663b3ac84eb36f817a5a8  scripts/lib/rpc_batch.py
80af01730c0068e5b6f66883eb1add19b7ff4daddfbe1ba6f18c595dd68ea616  scripts/tests/test_batch1_rpc_attestation.py（取 RED 时）
```

使用 `python3 -B -` 临时驱动逐场景调用 `run_with_backend` / `_getcode_scenario`，每条独立 try/except；四个错误返回场景的返回值断言与摘要断言也分别捕获。没有用整个测试函数的首个失败代替后续场景。每条记录均保留场景名、异常类型与原文、被测文件 SHA-256；GREEN 条目的异常列表为空。

| 场景 | 基线状态 | 基线实际结果 | 修改后（定向测试验证） |
| --- | --- | --- | --- |
| envelope/missing | RED，`AssertionError` | `{'ok': True, 'result': None}` | GREEN：`ok=False`，错误含 `result` |
| envelope/null_result | GREEN，无异常 | `{'ok': True, 'result': None}` | GREEN：合法 null 仍成功 |
| getcode/missing | RED，`AssertionError` | rc=0，`is_contract=False`；EOA 1 / 失败 0 | GREEN：rc=1，仅 error；EOA 0 / 失败 1 |
| getcode/null | RED，`AssertionError` | rc=0，`is_contract=False`；EOA 1 / 失败 0 | GREEN：rc=1，仅 error；EOA 0 / 失败 1 |
| getcode/odd | RED，`AssertionError` | rc=0，`is_contract=False`；EOA 1 / 失败 0 | GREEN：rc=1，仅 error；EOA 0 / 失败 1 |
| getcode/badhex | RED，`AssertionError` | rc=0，`is_contract=True`；EOA 0 / 失败 0 | GREEN：rc=1，仅 error；EOA 0 / 失败 1 |
| getcode/int | RED，`TypeError` | `object of type 'int' has no len()`；无 rc、无 JSON 或临时产物 | GREEN：rc=1，仅 error；EOA 0 / 失败 1 |
| getcode/eoa | GREEN，无异常 | rc=0，`code_len=0`，`is_contract=False` | GREEN：EOA |
| getcode/contract | GREEN，无异常 | rc=0，`code_len=2`，`is_contract=True` | GREEN：合约 |

完整原始证据：[F04_red_evidence.txt](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/F04_red_evidence.txt)。证据文件 SHA-256：`58807534e39968912f8fdf08071abb82bd0e2ef86b25a4f77af30b9b747478df`。

## 4. §0.8 定向测试结果尾行

所有命令均以 `python3 -B` 原样运行，并设置 `PYTHONDONTWRITEBYTECODE=1` 供测试子进程继承；未运行 `run_all.py`。每项退出码均为 0。下表保留 stdout 最后一个非空行原文。

| 命令 | 退出码 | stdout 尾行 |
| --- | --- | --- |
| `python3 -B scripts/tests/test_batch1_rpc_attestation.py` | 0 | `PASS B1-B RPC session: wrong-chain zero business/fail-closed/correct/failover` |
| `python3 -B scripts/tests/test_net_result.py` | 0 | `PASS: net Result 显式状态与 curl_json 失败分类` |
| `python3 -B scripts/tests/test_batch2_capability_matrix.py` | 0 | `PASS B2-D: immutable release tier + capability closure + derived CLI choices` |
| `python3 -B scripts/tests/test_evm_observation.py` | 0 | `PASS EVM observation bundle protocol: 11/11` |
| `python3 -B scripts/tests/test_evm_observation_nonempty_code.py` | 0 | `PASS F-04 EVM nonempty code and ABI word checks: 5/5` |
| `python3 -B scripts/tests/test_supply_truth_gate.py` | 0 | `supply_truth_gate 形态①/②离线契约测试全部通过` |
| `python3 -B scripts/tests/test_repair_batch_a.py` | 0 | `PASS batch A F-01/F-02 regressions 45/45` |
| `python3 -B scripts/tests/test_repair_batch_d.py` | 0 | `BATCH D 全部通过` |
| `python3 -B scripts/tests/test_recon_deep_reverify.py` | 0 | `PASS test_recon_deep_reverify` |
| `python3 -B scripts/tests/test_r7_findings.py` | 0 | `PASS R7 regression suite: 15/15 observed green; EXPECTED_RED=0` |
| `python3 -B scripts/tests/test_batch4_invariant_guards.py` | 0 | `PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `python3 -B scripts/tests/test_exemption_guards.py` | 0 | `PASS: exemption guards (EX-01 full-F-03)` |
| `python3 -B scripts/tests/test_g3_alt_collectors.py` | 0 | `SUMMARY: 13 passed, 0 failed, 0 skip-red` |
| `python3 -B scripts/tests/invariant_scan.py` | 0 | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0` |

新增两个测试已经由 main 调用并通过。既有 `0x64` / `0x2a` 成功断言和 rpc_batch 错链零业务用例保持通过；握手仍先于业务调用。

## 5. 文档字节数（§1.1）

开工与完工均仅使用文件元数据执行以下命令，结果完全一致。

```console
$ stat -f %z SKILL.md
8021
$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930076
$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
```

## 6. git diff --stat 与白名单（§0.3、§1.2）

```console
$ git diff --stat
 scripts/lib/net.py                           |  5 +-
 scripts/lib/rpc_batch.py                     | 10 ++--
 scripts/tests/test_batch1_rpc_attestation.py | 71 ++++++++++++++++++++++++++++
 3 files changed, 82 insertions(+), 4 deletions(-)
```

`git diff --check` 无输出，退出码 0。已跟踪文件的 diff 仅含工单白名单中的三个 Python 文件；另新建本目录的 `F04_red_evidence.txt` 与本报告 `F04_done.md`。新文件未暂存，因此不出现在上述 `git diff --stat` 中。没有修改现有停工报告。

完工代码 SHA-256：

```text
de4d94ebd51acee296f851d7f0532c403737dc94038ca6b260e6f7a177cc9823  scripts/lib/net.py
9fb209487cdcfbb28701c6a57745db10f4d54dc26c067259fbae0c4734eeb61b  scripts/lib/rpc_batch.py
80af01730c0068e5b6f66883eb1add19b7ff4daddfbe1ba6f18c595dd68ea616  scripts/tests/test_batch1_rpc_attestation.py
```

## 7. 工单一致性、消费者复核及保留边界（§0.4、§1.3、§1.4）

与工单差异：无。本次停工点：无。以 HEAD 中的三个原始文件为输入，应用工单三个 Python 代码块及指定 import/main 插入后，与落地文件逐字节相等：

```text
PASS exact workorder transformation: scripts/lib/net.py
PASS exact workorder transformation: scripts/lib/rpc_batch.py
PASS exact workorder transformation: scripts/tests/test_batch1_rpc_attestation.py
PASS unchanged code outside specified replacements, including all protected functions/branches/assertions
```

因此 `net.py` 的 `_attest_endpoint`、`_run`、`_request_json`、`RETRYABLE_RPC` 及 `rpc_batch.py` 的 receipts/raw、退出码、docstring、摘要和原有失败分支均保持不变。没有新增生产写文件点或更换网络库；未改两份 manifest、其他生产脚本、references、SKILL、commands-staging、VERSION、pyproject.toml 或 CHANGELOG。

`_one` 新分支沿用 `{ok: False, error: str}`，成功分支沿用 `{ok: True, result: ...}`。新增错误固定为 `rpc envelope: missing result (no error object)`，不含端点或响应原文。合法 `result=null` 仍返回 `{ok: True, result: None}`；getcode 的方法级类型与格式校验按工单单独拒绝 null。

开工逐个打开工单指定的消费者代码位置，核实 11 处既有处理如下（行号为施工前基线；这些文件未改）：

| 消费者位置 | `ok=False` 的既有处理与保留语义 |
| --- | --- |
| `scripts/lib/evm_observation.py:62-64` | `ok` 非真即抛 `EvmObservationError`。 |
| `scripts/lib/supply_truth_gate.py:484-486` | `ok=False` 即抛 `ValueError`。 |
| `scripts/evm/accounting_gate.py:121-126` | 按既有错误分类抛 `RpcSemanticError` / `RpcNetError`。 |
| `scripts/evm/verify_recon.py:264-265` | `ok=False` 触发“eth_call 无有效 result”的 `ValueError`。 |
| `scripts/lib/time_spotcheck.py:483-485` | 余额项记 `RPC_ERR`；`:528-546` 生成错误回执并返回 1。`:487` 合法 null 余额按 0 的语义保留。 |
| `scripts/lib/time_spotcheck.py:501-503` | 收据项 `ok=False` 或 null 记 `RPC_ERR`；按既有分支返回 1。 |
| `scripts/evm/fetch_alchemy.py:153-176` | 进入错误处理及重试；耗尽后 `sys.exit(2)`。 |
| `scripts/evm/scan_bloxroute_seg.py:73-98` | 失败结果转为 `logs=None`，重试耗尽后将区间记入 `fails`。 |
| `scripts/evm/pierce_stake.py:95-103` | 重试耗尽后警告并返回 `[None] * len(addrs)`。 |
| `scripts/evm/multicall_balances.py:69-81` | 重试耗尽后该批地址余额置 `None`。 |
| `scripts/evm/lp_positions.py:132-134` | `parse_receipt` 对失败或 null 收据返回空列表；该语义保留。 |

本段让缺 `result` 键进入这些既有失败分支，不改变各消费者的返回或退出策略。部分消费者返回 `None` 或空列表；`time_spotcheck` 余额 null 当 0、`lp_positions` 跳过 null 收据均保留，没有一并修复消费者对 null 的处理。

开工 `python3 -B scripts/tests/invariant_scan.py` 与完工同一命令均退出 0、PASS，投影与 manifest 无差异；两次输出相同：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

Q5 / Q6 / Q13 按工单登记不修，未修改调度方维护的台账：不新增 id/jsonrpc 校验；合法 null 由方法消费者自核；`_run` 的端点轮转原样保留。Q13 的 A→B→A 漏访 C 反例限定为三端点；更多端点可能重复访问或漏访，顺序取决于端点数与各次结果，不泛化为必然失败。已落盘 getcode 产物不追溯。

## 8. 禁读与执行纪律披露

全程离线；未 commit、push 或部署；未执行 stash、checkout、reset；未调用子代理。人工操作仅写入 §0.3 白名单文件，测试临时产物由既有测试流程管理。

未读取 `~/.codex/` 或 memories，未主动读取 archive/、blind-reviews/、.staging_*、references/attic.md、本工单目录以外的历史 maintenance 内容、`/Users/uravvv/Desktop` 或 `/Users/uravvv/Documents`。SKILL / references / commands-staging 的字节数检查仅使用元数据。历史 maintenance 依赖仅由测试子进程按既有代码访问，适用 §0.2 明示豁免；本人未打开、阅读、复制或修改这些历史文件。
