"""Git-verifiable historical hashes for formal artifact producers.

Admission discipline: every entry must be reproducible with
`git show <commit>:<script> | shasum -a 256`.  This module has no runtime
extension channel.  A hash produced from a dirty worktree cannot be proven
from git history and must not be admitted.
"""


PRODUCER_HISTORY = (
    {
        "script": "scripts/lib/anchor_plan.py",
        "sha256": "e5168a455d53bb5163722ea7f2a67c42b20bd3dd8ef6c3ae5e588014842cc1d9",
        "commit": "3b76db80130987e0faf68d73094b08cddd161c9b",
        "protocol": "anchor-plan/v2",
        "status": "ACTIVE",
        "reason": "v6.39.5 NES case receipts were signed by this anchor-plan/v2 producer.",
    },
    {
        "script": "scripts/lib/anchor_plan.py",
        "sha256": "1a461169f0770c7a4b8d74eb185f68ae225906cf1ec49b9ad04154e340ebebb2",
        "commit": "0ec6d1e2365c339d200fc26d17344f962fbdb7a9",
        "protocol": "anchor-plan/v2",
        "status": "ACTIVE",
        "reason": "v6.45.1 pre-v3 producer replaced by the U1 anchor-plan/v3 upgrade.",
    },
    {
        "script": "scripts/solana/fetch_sqd_transfers_v2.py",
        "sha256": "2589f6a396c262d0747343ef21dee2bc7ba814eaa59eebdfa782fe9253c32212",
        "commit": "75aa622a546755a7848d211739a75f7b31f9e59b",
        "protocol": "sqd-solana-cache/v4",
        "status": "ACTIVE",
        "reason": "Batch 4 T1 producer issues replay-compatible logical edge evidence in v4 cache meta.",
    },
    {
        "script": "scripts/solana/fetch_sqd_transfers_v2.py",
        "sha256": "a94b193b94ba8872e4d6aa4915ff7d89ef6cc438d7f2c6c0744ebc33212d9bae",
        "commit": "47b3620fb2f739b9a609b543572e0b69559038b0",
        "protocol": "sqd-solana-cache/v4",
        "status": "ACTIVE",
        "reason": "Batch 6 F-05 keeps v4 output semantics and rejects scalar-type drift equally in both merge paths.",
    },
    {
        "script": "scripts/solana/sqd_coverage_probe.py",
        "sha256": "e41370b185aef9bd16fea8ce1abc519a138ee4ce8923bdbc8058d64cdd0619bf",
        "commit": "c2372635cf567c451892f828dcb229cdd4dc277d",
        "protocol": "sqd-solana-coverage/v1",
        "status": "ACTIVE",
        "reason": "v6.52.0 registers the finalized coverage map producer used by the Solana A2 coverage gate.",
    },
    {
        "script": "scripts/solana/sqd_coverage_probe.py",
        "sha256": "e41370b185aef9bd16fea8ce1abc519a138ee4ce8923bdbc8058d64cdd0619bf",
        "commit": "c2372635cf567c451892f828dcb229cdd4dc277d",
        "protocol": "sqd-solana-coverage-pointer/v1",
        "status": "ACTIVE",
        "reason": "v6.52.0 registers the atomic CURRENT coverage pointer producer from the same frozen probe implementation.",
    },
    {
        "script": "scripts/solana/sqd_coverage_probe.py",
        "sha256": "bccf1802b6a5c9d9bbbdb12e19354ad761416c631e3cdfde2449f7fe1794f176",
        "commit": "55d4efede78f6afb6c1d3c8aa3bbec95b6faa33f",
        "protocol": "sqd-solana-coverage/v1",
        "status": "ACTIVE",
        "reason": "v6.52.3 recognizes the exact HTTP-200 empty-body SQD stream tail as covered skipped slots.",
    },
    {
        "script": "scripts/solana/sqd_coverage_probe.py",
        "sha256": "bccf1802b6a5c9d9bbbdb12e19354ad761416c631e3cdfde2449f7fe1794f176",
        "commit": "55d4efede78f6afb6c1d3c8aa3bbec95b6faa33f",
        "protocol": "sqd-solana-coverage-pointer/v1",
        "status": "ACTIVE",
        "reason": "v6.52.3 registers the atomic CURRENT pointer from the stream-tail-aware frozen probe.",
    },
    {
        "script": "scripts/solana/sqd_coverage_probe.py",
        "sha256": "be415db3552588532ff195126ddd53aefe9d3c14785da64c2be4cf23804f7bea",
        "commit": "f0469a376c0101759f260dafb1678c00ff785d65",
        "protocol": "sqd-solana-coverage/v1",
        "status": "ACTIVE",
        "reason": "v6.52.14 registers the shared-map probe with three-way identity checks, a historical anchor, and concurrent rechecks.",
    },
    {
        "script": "scripts/solana/sqd_coverage_probe.py",
        "sha256": "be415db3552588532ff195126ddd53aefe9d3c14785da64c2be4cf23804f7bea",
        "commit": "f0469a376c0101759f260dafb1678c00ff785d65",
        "protocol": "sqd-solana-coverage-pointer/v1",
        "status": "ACTIVE",
        "reason": "v6.52.14 registers the atomic CURRENT pointer producer from the same frozen F-03 probe.",
    },
    {
        "script": "scripts/solana/sqd_coverage_probe.py",
        "sha256": "c4980c984b08d27f5a7e46db50f97c9c16e47ea491f37a459b3773f939218769",
        "commit": "cdc4f87f8e3ee4d181760cb8455d688f23049f20",
        "protocol": "sqd-solana-coverage/v1",
        "status": "ACTIVE",
        "reason": "v6.52.15 registers the F-03b failure-classifying probe that drops request-failed recheck segments to full after retries while preserving whole-map fallback for mismatches.",
    },
    {
        "script": "scripts/solana/sqd_coverage_probe.py",
        "sha256": "c4980c984b08d27f5a7e46db50f97c9c16e47ea491f37a459b3773f939218769",
        "commit": "cdc4f87f8e3ee4d181760cb8455d688f23049f20",
        "protocol": "sqd-solana-coverage-pointer/v1",
        "status": "ACTIVE",
        "reason": "v6.52.15 registers the atomic CURRENT pointer producer from the same frozen F-03b probe.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "c8beb16e998c5019f6d3cfee0cb14ca163b4dcc3b7d3eb9bdd43fdfd6e44d137",
        "commit": "5782f76773fae0f3b9b036222ad85298992ec840",
        "protocol": "sqd-solana-cache/v4",
        "status": "ACTIVE",
        "reason": "v6.52.0 registers the repaired v4 cache producer with base, resolution, bundle, and pointer binding.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "c8beb16e998c5019f6d3cfee0cb14ca163b4dcc3b7d3eb9bdd43fdfd6e44d137",
        "commit": "5782f76773fae0f3b9b036222ad85298992ec840",
        "protocol": "sqd-solana-repair-bundle/v1",
        "status": "ACTIVE",
        "reason": "v6.52.0 registers the repair evidence bundle producer consumed by formal resolver and exact validation.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "c8beb16e998c5019f6d3cfee0cb14ca163b4dcc3b7d3eb9bdd43fdfd6e44d137",
        "commit": "5782f76773fae0f3b9b036222ad85298992ec840",
        "protocol": "sqd-solana-coverage-resolution/v1",
        "status": "ACTIVE",
        "reason": "v6.52.0 registers the confirmed coverage-resolution producer that authorizes repaired slots.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "c8beb16e998c5019f6d3cfee0cb14ca163b4dcc3b7d3eb9bdd43fdfd6e44d137",
        "commit": "5782f76773fae0f3b9b036222ad85298992ec840",
        "protocol": "sqd-solana-repair-pointer/v1",
        "status": "ACTIVE",
        "reason": "v6.52.0 registers the atomic CURRENT repair pointer producer for the published generation.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "da6eb283ab08ed714268a6c1b19bbc39f091b18bbb3a64ce1e1056e01571dda0",
        "commit": "80ab2a380952bf63eb01bb896c9d7e260bc8055f",
        "protocol": "sqd-solana-cache/v4",
        "status": "ACTIVE",
        "reason": "v6.52.4 keeps v4 cache output semantics while omitting the unsupported, unconsumed parentSlot SQD census field.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "da6eb283ab08ed714268a6c1b19bbc39f091b18bbb3a64ce1e1056e01571dda0",
        "commit": "80ab2a380952bf63eb01bb896c9d7e260bc8055f",
        "protocol": "sqd-solana-repair-bundle/v1",
        "status": "ACTIVE",
        "reason": "v6.52.4 registers repair bundles produced after removing the invalid SQD census block field.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "da6eb283ab08ed714268a6c1b19bbc39f091b18bbb3a64ce1e1056e01571dda0",
        "commit": "80ab2a380952bf63eb01bb896c9d7e260bc8055f",
        "protocol": "sqd-solana-coverage-resolution/v1",
        "status": "ACTIVE",
        "reason": "v6.52.4 registers coverage resolutions from the SQD-contract-compatible census producer.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "da6eb283ab08ed714268a6c1b19bbc39f091b18bbb3a64ce1e1056e01571dda0",
        "commit": "80ab2a380952bf63eb01bb896c9d7e260bc8055f",
        "protocol": "sqd-solana-repair-pointer/v1",
        "status": "ACTIVE",
        "reason": "v6.52.4 registers the atomic CURRENT repair pointer from the SQD-contract-compatible producer.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "60b48f86154d8793c8b1229121641f3f2d6517e924188aa47452855cc8636f7b",
        "commit": "ddfeec1b307f33e4ca9c22d129ad554d33ef426d",
        "protocol": "sqd-solana-cache/v4",
        "status": "ACTIVE",
        "reason": "v6.52.6 registers the key-neutral, pooled, ordered-streaming v4 cache producer frozen by Batch 8 stage 1.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "60b48f86154d8793c8b1229121641f3f2d6517e924188aa47452855cc8636f7b",
        "commit": "ddfeec1b307f33e4ca9c22d129ad554d33ef426d",
        "protocol": "sqd-solana-repair-bundle/v1",
        "status": "ACTIVE",
        "reason": "v6.52.6 registers repair bundles emitted by the Batch 8 key-pool and bounded ordered-worker producer.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "60b48f86154d8793c8b1229121641f3f2d6517e924188aa47452855cc8636f7b",
        "commit": "ddfeec1b307f33e4ca9c22d129ad554d33ef426d",
        "protocol": "sqd-solana-coverage-resolution/v1",
        "status": "ACTIVE",
        "reason": "v6.52.6 registers coverage resolutions assembled from the Batch 8 streaming live-repair producer.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "60b48f86154d8793c8b1229121641f3f2d6517e924188aa47452855cc8636f7b",
        "commit": "ddfeec1b307f33e4ca9c22d129ad554d33ef426d",
        "protocol": "sqd-solana-repair-pointer/v1",
        "status": "ACTIVE",
        "reason": "v6.52.6 registers the atomic CURRENT repair pointer from the Batch 8 stage-1 frozen producer.",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66",
        "commit": "4c5cd578a5f1a10449d128dcdb91a724c359e7a5",
        "protocol": "sqd-solana-cache/v4",
        "status": "ACTIVE",
        "reason": "v7.0.2 registers the v6.52.7 batch-9 producer (verify-CLI local `_base` renamed to `_base_payload` in `_verify`; sqd-solana-cache/v4 output semantics unchanged).",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66",
        "commit": "4c5cd578a5f1a10449d128dcdb91a724c359e7a5",
        "protocol": "sqd-solana-repair-bundle/v1",
        "status": "ACTIVE",
        "reason": "v7.0.2 registers the v6.52.7 batch-9 producer (verify-CLI local `_base` renamed to `_base_payload` in `_verify`; sqd-solana-repair-bundle/v1 output semantics unchanged).",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66",
        "commit": "4c5cd578a5f1a10449d128dcdb91a724c359e7a5",
        "protocol": "sqd-solana-coverage-resolution/v1",
        "status": "ACTIVE",
        "reason": "v7.0.2 registers the v6.52.7 batch-9 producer (verify-CLI local `_base` renamed to `_base_payload` in `_verify`; sqd-solana-coverage-resolution/v1 output semantics unchanged).",
    },
    {
        "script": "scripts/solana/sqd_gap_repair.py",
        "sha256": "25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66",
        "commit": "4c5cd578a5f1a10449d128dcdb91a724c359e7a5",
        "protocol": "sqd-solana-repair-pointer/v1",
        "status": "ACTIVE",
        "reason": "v7.0.2 registers the v6.52.7 batch-9 producer (verify-CLI local `_base` renamed to `_base_payload` in `_verify`; sqd-solana-repair-pointer/v1 output semantics unchanged).",
    },
    {
        "script": "scripts/solana/window_fetch.py",
        "sha256": "56d94cbecf476b632c814a57b245c58397087dd105406e2538cac47c2fa6661c",
        "commit": "75aa622a546755a7848d211739a75f7b31f9e59b",
        "protocol": "solana-window-fetch-receipt/v3",
        "status": "ACTIVE",
        "reason": "Batch 4 registers the v3 formal Solana window producer frozen at the T1 tip.",
    },
)


def historical_producer_hashes(script, protocol):
    """Return matching ACTIVE hashes after hash-wide REVOKED precedence."""
    for index, entry in enumerate(PRODUCER_HISTORY):
        status = entry.get("status")
        if status not in {"ACTIVE", "REVOKED"}:
            raise ValueError(
                f"producer history entry[{index}] status invalid: {status!r}")
    revoked = {
        entry["sha256"]
        for entry in PRODUCER_HISTORY
        if entry["status"] == "REVOKED"
    }
    return {
        entry["sha256"]
        for entry in PRODUCER_HISTORY
        if entry["status"] == "ACTIVE"
        and entry["script"] == script
        and entry["protocol"] == protocol
        and entry["sha256"] not in revoked
    }
