#!/usr/bin/env python3
"""2026-08-02 review regressions: B-06/B-07/B-08."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOL = os.path.join(HERE, "..", "solana")
sys.path.insert(0, SOL)

import decode_txs as decode_v1
import decode_txs_v2 as decode_v2
from decode_txs_v2 import SigCache, completed_sigs, decode_result
from scan_token_accounts import T22, cache_identity_matches, choose_datasizes, require_snapshot_closed


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, result):
        self.result = result
        self.proxies = {}

    def post(self, url, json=None, timeout=None):
        items = json if isinstance(json, list) else [json]
        payload = [{"jsonrpc": "2.0", "id": item.get("id"), "result": self.result}
                   for item in items]
        return FakeResponse(payload if isinstance(json, list) else payload[0])


def call_decoder(module, sigs, out, mint, result, extra=None):
    argv = [module.__file__, "--sigs", sigs, "--out", out, "--mint", mint,
            "--rpc", "fixture-rpc", "--interval", "0"] + (extra or [])
    old_argv, old_session, old_sleep = sys.argv, module.requests.Session, module.time.sleep
    sys.argv = argv
    module.requests.Session = lambda: FakeSession(result)
    module.time.sleep = lambda _: None
    try:
        try:
            result_code = module.main()
        except SystemExit as e:
            return int(e.code or 0) if isinstance(e.code, int) else 1
        return int(result_code or 0)
    finally:
        sys.argv = old_argv
        module.requests.Session = old_session
        module.time.sleep = old_sleep


def balance(owner, mint, raw, decimals, ui=None):
    return {"owner": owner, "mint": mint,
            "uiTokenAmount": {"amount": str(raw), "decimals": decimals, "uiAmount": ui}}


def main():
    mint, owner, pool = "MiNtCaseSensitive", "Owner", "Pool"
    pre = 2**53 + 123456789
    res = {"slot": 9, "blockTime": 10, "meta": {
        "preTokenBalances": [balance(owner, mint, pre, 9, None),
                             balance(pool, mint, 10**18 + 7, 9, None)],
        "postTokenBalances": [balance(owner, mint, pre + 1, 9, None),
                              balance(pool, mint, 10**18 + 8, 9, None)]}}
    row = decode_result("sig", res, mint, pool)
    assert row["deltas_raw"][owner] == 1 and row["deltas"][owner] == "0.000000001"
    assert row["pool_balance_raw"] == 10**18 + 8
    assert row["pool_balance"] == "1000000000.000000008"

    with tempfile.TemporaryDirectory() as tmp:
        c1 = SigCache(tmp, "MintA", "Pool", "rpc")
        c1.put({"sig": "sameSig", "mint": "MintA", "deltas_raw": {"a": 1}})
        assert SigCache(tmp, "MintA", "Pool", "rpc").get("sameSig") is not None
        assert SigCache(tmp, "MintB", "Pool", "rpc").get("sameSig") is None
        assert SigCache(tmp, "MintA", "OtherPool", "rpc").get("sameSig") is None

        out = os.path.join(tmp, "decoded.jsonl")
        with open(out, "w") as f:
            f.write(json.dumps({"sig": "retry", "decode_fail": True}) + "\n")
            f.write(json.dumps({"sig": "done", "mint": mint, "deltas_raw": {}}) + "\n")
        assert completed_sigs(out, mint) == {"done"}

        # P1-03：v1 失败行不算 done，下次必须重试并成功收口。
        sigs = os.path.join(tmp, "sigs.txt")
        open(sigs, "w").write("retry\n")
        v1_out = os.path.join(tmp, "v1.jsonl")
        open(v1_out, "w").write(json.dumps({"sig": "retry", "decode_fail": True}) + "\n")
        open(v1_out + ".meta.json", "w").write(json.dumps(
            decode_v2.output_identity(mint, None, "fixture-rpc"), indent=2, sort_keys=True))
        rpc_result = {"slot": 9, "blockTime": 10, "meta": {
            "preTokenBalances": [balance(owner, mint, 1, 0)],
            "postTokenBalances": [balance(owner, mint, 2, 0)]}}
        rc = call_decoder(decode_v1, sigs, v1_out, mint, rpc_result)
        final_rows = [json.loads(x) for x in open(v1_out) if x.strip()]
        receipt = json.load(open(v1_out + ".receipt.json")) if os.path.exists(v1_out + ".receipt.json") else {}
        assert rc == 0 and not final_rows[-1].get("decode_fail") \
            and receipt.get("status") == "PASS"

        # v1 输出身份必须绑定 mint/pool/RPC，跨 mint 复用必须硬退。
        rc = call_decoder(decode_v1, sigs, v1_out, "OtherMint", rpc_result)
        assert rc != 0, "v1 cross-mint output must reject"

        # v1/v2 本次最终仍有 decode_fail 时都必须非零且落 BLOCK receipt。
        for module, extra in ((decode_v1, []),
                              (decode_v2, ["--batch", "1", "--cache-dir", ""])):
            failed_out = os.path.join(tmp, os.path.basename(module.__file__) + ".failed.jsonl")
            rc = call_decoder(module, sigs, failed_out, mint, None, extra)
            receipt_path = failed_out + ".receipt.json"
            rec = json.load(open(receipt_path)) if os.path.exists(receipt_path) else {}
            assert rc != 0 and rec.get("status") == "BLOCK" \
                and rec.get("failure_count") == 1, f"{module.__name__}: rc={rc} {rec}"

    assert choose_datasizes(T22, "auto") == ["all"]
    try:
        choose_datasizes(T22, "165,170")
    except ValueError:
        pass
    else:
        raise AssertionError("Token-2022 partial dataSize scan must reject")
    expected = {"mint": "MintA", "rpc": "rpc", "gpa_response_slot": 123}
    assert cache_identity_matches(dict(expected), expected)
    assert not cache_identity_matches({**expected, "mint": "MintB"}, expected)
    require_snapshot_closed(100, 100)
    for total, supply, malformed in [(99, 100, 0), (100, 100, 1)]:
        try:
            require_snapshot_closed(total, supply, malformed)
        except ValueError:
            pass
        else:
            raise AssertionError("partial/malformed holder snapshot must reject")

    print("PASS: B-06/B-07/B-08 + P1-03 v1/v2 decode retry, identity and failure receipts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
