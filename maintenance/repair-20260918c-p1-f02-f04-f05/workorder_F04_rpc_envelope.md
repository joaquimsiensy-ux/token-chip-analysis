# 工单 F04（v1）：RPC 业务响应缺 `result` 键判失败；getCode 只认 `0x` 为空代码 —— repair-20260918c-p1-f02-f04-f05 第一段

> 出处：codex 对 8.0.0（8b041842）六视角 review F04（P1，历史漏审 637df73/3.16.0）：`net.py:298` `RpcPool._one` 在传输正常、无 truthy `error` 时直接 `j.get("result")` 并记 `ok=True`——响应是合法 JSON 但缺 `result` 键（提供商/代理/缓存限流时的空壳包）也算成功；`rpc_batch.py:83` `code = r["result"] or "0x"` 把 None 折成空代码，`is_contract=false`，摘要"失败 0"。同文件 `net.py:314-325` 的链身份握手反而严格拒缺失/非法 result，两套标准。用户 09-18 裁决：修。总原则：skill 上下文不增；能删不增、能改不增；references/SKILL/commands 本段零改动。
> 修法：①网络层统一校验 envelope——`result` 键不在场且无 error → `{"ok": False, "error": "rpc envelope: missing result"}`（合法 `"result": null` 键在场，继续 `ok=True, result=None`，各方法消费者自核类型，见台账 Q6）；②`rpc_batch getcode` 只把字符串 `"0x"` 当空代码，非字符串/不以 `0x` 起头/十六进制长度为奇数一律记 `{"error": …}`（退出码沿用既有 fail-loud：有失败即 1）。
> 内容基线：`8b041842`（v8.0.0）加本工程已入库的裁决/工单 commit；`scripts/` 与 8b041842 逐字节相同。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `F04_done.md`：`git status --short`（须为空）；`git diff --stat 8b041842 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不空即停工写 `F04_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本目录（`maintenance/repair-20260918c-p1-f02-f04-f05/`）以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
- 0.3 **白名单**：生产 `scripts/lib/net.py`、`scripts/lib/rpc_batch.py`；测试 `scripts/tests/test_batch1_rpc_attestation.py`；本目录新建 `F04_done.md`、`F04_red_evidence.txt`，停工时 `F04_done_attempt1_stopped.md`。
- 0.4 **不改**：`net.py` 的 `_attest_endpoint`（`:300-341`）、`_run`（`:349-385`，failover 逻辑不动：全部 `ok=False` 时切下一端点属预期）、`_request_json`、`RETRYABLE_RPC`；`rpc_batch.py` 的 `receipts`/`raw` 分支（`:91-112`）、退出码逻辑（`:123-125`）、docstring `:16-21`（"失败项记 {error}，有失败退出 1"已覆盖新行为）；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`contract_manifest.json`、`invariant_manifest.json`（本段不新增写文件点、不换网络库，manifest 无需登记——开工用 `python3 -B scripts/tests/invariant_scan.py` 证实）；其他消费 `RpcPool` 的脚本一律不改（它们对 `ok=False` 的既有处理见 §1.4）。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.3 新用例在改生产代码前逐例取 RED 写 `F04_red_evidence.txt`（逐例捕获 AssertionError／非零 rc，按真实基线记 RED 或 GREEN→GREEN）。
- 0.8 不跑 `run_all.py`。定向跑（全部须 PASS）：`python3 -B scripts/tests/test_batch1_rpc_attestation.py`、`test_net_result.py`、`test_batch2_capability_matrix.py`、`test_evm_observation.py`、`test_supply_truth_gate.py`、`test_repair_batch_a.py`、`test_repair_batch_d.py`、`test_recon_deep_reverify.py`、`test_r7_findings.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`python3 -B scripts/tests/invariant_scan.py`。

## 1. 硬约束

- 1.1 文档三处字节不变：`SKILL.md` 8021、`references/**/*.md` 合计 930076、`commands-staging/*.md` 合计 8798。只用元数据：`stat -f %z SKILL.md`；`find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'`；`stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'`。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 `_one` 的返回形状不变：仍只有 `{"ok": True, "result": …}` 与 `{"ok": False, "error": str}` 两种；`error` 文案继续经 `redact_endpoint_text` 脱敏（本段新增的固定文案不含端点，无需脱敏，但不得把 `j` 原文拼进 error）。
- 1.4 既有消费者语义不变（开工逐个 `grep -n` 核实并写 done）：`evm_observation.py:62`（`ok is not True` 即拒）、`supply_truth_gate.py:484`、`accounting_gate.py:121`、`verify_recon.py:264`、`time_spotcheck.py:483/501`、`fetch_alchemy.py:153`、`scan_bloxroute_seg.py:73`、`pierce_stake.py:95`、`multicall_balances.py:69`、`lp_positions.py:132`（`parse_receipt` 对 `ok=False` 返回空列表）——它们对 `ok=False` 均已有处理分支，本段只会让"缺 result 键"从假成功变为这些既有失败分支，不新增任何分支。
- 1.5 `test_batch1_rpc_attestation.py:115`/`:133` 的既有断言 `{"ok": True, "result": "0x64"}`/`"0x2a"` 保持 PASS；`:296-298` 的 rpc_batch 错链零业务用例保持 PASS（握手先于业务，本段不触碰握手）。

## 2. 逐条施工

### 2.1 `scripts/lib/net.py` —— `_one` 校验 envelope

`:298`（锚 `            return {"ok": True, "result": j.get("result")}`，唯一）改为：

```python
            if not isinstance(j, dict) or "result" not in j:
                # JSON-RPC envelope 缺 result 且无 error：提供商/代理/缓存的空壳包，不是成功（F04）
                return {"ok": False, "error": "rpc envelope: missing result (no error object)"}
            return {"ok": True, "result": j["result"]}
```

说明：①`:280`/`:289` 的 `err = j.get("error") if isinstance(j, dict) else None` 已处理非 dict 情形（非 dict 时 err=None 落到本处），本段把非 dict 也归入 envelope 失败；②合法 `"result": null` 键在场，`"result" not in j` 为 False，继续 `ok=True, result=None`（Q6）；③`_run:373` 对"全部 ok=False"会切换端点重打，属既有 failover，符合"坏包应成为失败"的修复方向。

### 2.2 `scripts/lib/rpc_batch.py` —— getcode 只认 `0x` 为空代码

`:82-85`（起锚 `            if r["ok"]:`——文件内出现 1 处；止锚 `                             "is_contract": code not in ("0x", "0x0", None)}`，唯一）替换为：

```python
            if r["ok"]:
                code = r["result"]
                if (not isinstance(code, str) or not code.startswith("0x")
                        or len(code) % 2 != 0):
                    # eth_getCode 合法返回只有 "0x" 或偶数长度十六进制串；其余记失败不猜 EOA（F04）
                    out[addr] = {"error": f"eth_getCode 非法返回 {type(code).__name__}"}
                    continue
                out[addr] = {"code_len": (len(code) - 2) // 2,
                             "is_contract": code != "0x"}
```

说明：`:86-87` 的 `else: out[addr] = {"error": r["error"]}` 不动；`:88-90` 摘要按 `is_contract`/`error` 计数，自动把新失败项计入"失败"；`:123-125` 有失败即退出 1，不改。`"0x0"` 原被当 EOA——它不是合法 getCode 返回（奇数 nibble），改后记失败，属目标行为。

### 2.3 `scripts/tests/test_batch1_rpc_attestation.py` —— 两个新用例

在 `:326`（`def test_remaining_formal_entrypoints_wrong_chain_zero_business` 函数结束后的空行）之后、`:327`（锚 `def main():`，唯一）之前新增：

```python
def test_business_envelope_missing_result():
    """F04：握手正常、业务响应缺 result 键 → ok=False；合法 result=null 仍 ok=True。"""
    async def missing(client, bucket, method, url, *, json_body=None, attempts=6):
        if json_body["method"] == "eth_chainId":
            return {"jsonrpc": "2.0", "id": 1, "result": "0x38"}
        return {"jsonrpc": "2.0", "id": json_body["id"]}

    pool = net.RpcPool("http://envelope", expected_chain_id=56)
    got = run_with_backend(pool, missing)
    assert got["ok"] is False and "result" in got["error"], got

    async def null_result(client, bucket, method, url, *, json_body=None, attempts=6):
        if json_body["method"] == "eth_chainId":
            return {"jsonrpc": "2.0", "id": 1, "result": "0x38"}
        return {"jsonrpc": "2.0", "id": json_body["id"], "result": None}

    pool = net.RpcPool("http://envelope", expected_chain_id=56)
    got = run_with_backend(pool, null_result, method="eth_getTransactionReceipt")
    assert got == {"ok": True, "result": None}, got


def test_rpc_batch_getcode_rejects_malformed_code():
    """F04：rpc_batch getcode 对缺 result / 非字符串 / 奇数长度返回记 error 且退出 1；"0x" 为 EOA、偶数长度为合约。"""
    address = "0x" + "b" * 40
    module = load("scripts/lib/rpc_batch.py", "batch1_rpc_batch_f04")
    scenarios = [
        ("missing", None, False),      # 缺 result 键
        ("null", {"result": None}, False),
        ("odd", {"result": "0x0"}, False),
        ("int", {"result": 123}, False),
        ("eoa", {"result": "0x"}, True),
        ("contract", {"result": "0x6080"}, True),
    ]
    with tempfile.TemporaryDirectory(prefix="batch1-rpc-f04-") as td:
        for name, payload, expect_ok in scenarios:
            async def backend(client, bucket, method, url, *, json_body=None, attempts=6, payload=payload):
                if json_body["method"] == "eth_chainId":
                    return {"jsonrpc": "2.0", "id": 1, "result": "0x38"}
                body = {"jsonrpc": "2.0", "id": json_body["id"]}
                if payload is not None:
                    body.update(payload)
                return body
            out = Path(td) / f"{name}.json"
            argv = ["rpc_batch.py", "http://envelope", "getcode", address,
                    "--chain", "bsc", "--out", str(out)]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                    net, "_request_json", side_effect=backend):
                rc = module.main()
            got = json.loads(out.read_text(encoding="utf-8"))[address]
            if expect_ok:
                assert rc == 0 and "error" not in got, (name, rc, got)
                assert got["is_contract"] is (name == "contract"), (name, got)
            else:
                assert rc == 1 and "error" in got and "is_contract" not in got, (name, rc, got)
```

在 `:334`（锚 `    test_remaining_formal_entrypoints_wrong_chain_zero_business()`，唯一）之后紧接两行调用 `    test_business_envelope_missing_result()`、`    test_rpc_batch_getcode_rejects_malformed_code()`。

RED 证据：改生产代码前逐个调用两个新用例，记录 AssertionError 原文（基线预期：`missing` 场景 `got == {"ok": True, "result": None}`；rpc_batch `missing/null/odd/int` 四场景 rc 0 且 `is_contract` 为 False）；`null_result`/`eoa`/`contract` 三段基线 GREEN→GREEN。

## 3. 完成报告 `F04_done.md` 必含

①0.1 两条命令输出；②§2 各处 `git diff` 原文；③RED 摘要；④0.8 各测试结果尾行；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点（含 §1.4 逐消费者核实结果、§0.4 invariant_scan 结果）；⑧禁读披露。stdout 首行 `# 施工 F04：完成` 或 `# 施工 F04：停工`。

## 4. 登记不修（`code_change_pending.md` Q5/Q6，调度方维护）

- 不校验 `id` 回显/`jsonrpc` 版本（Q5）；合法 null 由方法消费者自核（Q6）。
- 存量迁移：无（行为只在坏包时从假成功变失败；已落盘的 getcode 产物若来自坏包，本段不追溯——此类产物在正式路径不作为发布证据，`rpc_batch.py` 是 helper，`test_exemption_guards` 登记边界不变）。
