"""Git-verifiable historical hashes for formal anchor-plan producers.

Admission discipline: every entry must be reproducible with
`git show <commit>:scripts/lib/anchor_plan.py | shasum -a 256`.  This module has
no runtime extension channel.  A hash produced from a dirty worktree cannot be
proven from git history and must not be admitted.
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
