#!/usr/bin/env python3
"""2026-08-02 review regressions: B-06/B-07/B-08."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOL = os.path.join(HERE, "..", "solana")
sys.path.insert(0, SOL)

from decode_txs_v2 import SigCache, completed_sigs, decode_result
from scan_token_accounts import T22, cache_identity_matches, choose_datasizes, require_snapshot_closed


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

    print("PASS: B-06 raw precision, B-07 cache/retry identity, B-08 Token-2022 closure")
    return 0


if __name__ == "__main__":
    sys.exit(main())
