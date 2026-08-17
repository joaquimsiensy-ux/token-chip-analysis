"""Git-verifiable historical hashes for formal EVM collector scripts.

Admission discipline: every entry must be reproducible with
`git show <rev>:scripts/evm/<name> | shasum -a 256`.  This module has no
runtime extension channel.  A hash produced from a dirty worktree cannot be
proven from git history and must not be admitted.
"""


COLLECTOR_HISTORY = (
    {
        "script": "fetch_hypersync.py",
        "sha256": "0521ec08f6f6d4eba7bda916f85559aa1ae182bb6d5152fb62d193726d25b420",
        "commit": "6da91f8ad837621aa3dad9e3d93a69d67a7503db",
        "protocol": "evm-collector-run/v2",
        "status": "ACTIVE",
        "reason": "2026-08-04 CSV 链式 receipt 制度起始版本，用于正式 HyperSync v1 CSV 采集。",
    },
    {
        "script": "fetch_hypersync.py",
        "sha256": "bdcd716c71c79c32c4458d3c415fc10b6184982e2cf723f57c6ea71dd6475295",
        "commit": "b0b774486862f2fb3d547dcbb10e56e08400fc8a",
        "protocol": "evm-collector-run/v2",
        "status": "ACTIVE",
        "reason": "v6.32.0 fail-closed 与 token-file 加固期用于正式 HyperSync v1 CSV 采集。",
    },
    {
        "script": "fetch_hypersync.py",
        "sha256": "d8113c590fe78e497364b15089215e82d0b061c413f80bb4600913f334f36b6d",
        "commit": "2ebd885d1a1364779338e02f8f30e991eec2302d",
        "protocol": "evm-collector-run/v2",
        "status": "ACTIVE",
        "reason": "v6.39.5 NES 案 −1 段用于 BSC/ETH 全量 CSV 通道采集。",
    },
    {
        "script": "fetch_hypersync.py",
        "sha256": "450f47bbbd51d2e6284f065e5894cfa0b77edcb1959f851321a51a10af02c128",
        "commit": "253ac798d262002684b22770a7fe955f6add5cb6",
        "protocol": "evm-collector-run/v2",
        "status": "ACTIVE",
        "reason": "2026-08-14 移除位置 token 后用于正式 HyperSync v1 CSV 采集。",
    },
    {
        "script": "fetch_hypersync_v2.py",
        "sha256": "7fecfd30f358afb6f39cc137683948a587c29f25ec9e5512c66bb16cbb995fe8",
        "commit": "8a7c6709252f4593c6e5bb05f046047c5171ad31",
        "protocol": "hypersync-capture-identity/v1",
        "status": "ACTIVE",
        "reason": "2026-08-04 outdir identity 制度起始版本，用于正式 HyperSync v2 Parquet 采集。",
    },
    {
        "script": "fetch_hypersync_v2.py",
        "sha256": "d229a1c200554708560f8eab4bed1ccaf378b65cd9fe852d57bcf75b7569fe16",
        "commit": "2ebd885d1a1364779338e02f8f30e991eec2302d",
        "protocol": "hypersync-capture-identity/v1",
        "status": "ACTIVE",
        "reason": "v6.39.5 NES 案 −1 段用于 BSC v2 capture identity 采集。",
    },
    {
        "script": "fetch_hypersync_v2.py",
        "sha256": "9634a035ba9776441416ca881806151194671856c5e950a195f77d027bf60fd7",
        "commit": "b3ee35221dd059499ab63b8f8acade86669c9c30",
        "protocol": "hypersync-capture-identity/v1",
        "status": "ACTIVE",
        "reason": "v6.40.0 批 D receipt 与闭合加固期用于正式 HyperSync v2 采集。",
    },
    {
        "script": "fetch_hypersync_v2.py",
        "sha256": "26b113a458f4be9284e3a5d0eca15a9c28e373b0e3f14bc91d3a4827f73b0363",
        "commit": "da8da7175f0c0c377fc64c4e5db44fd1e3a03d1e",
        "protocol": "hypersync-capture-identity/v1",
        "status": "ACTIVE",
        "reason": "2026-08-13 批 D 消化加固后用于正式 HyperSync v2 采集。",
    },
    {
        "script": "fetch_hypersync_v2.py",
        "sha256": "194cd25e16d47c3f459c8b6686158b0b736281899024a8a74a4cdc716e08962e",
        "commit": "253ac798d262002684b22770a7fe955f6add5cb6",
        "protocol": "hypersync-capture-identity/v1",
        "status": "ACTIVE",
        "reason": "2026-08-14 移除位置 token 后用于正式 HyperSync v2 采集。",
    },
    {
        "script": "fetch_hypersync_v2.py",
        "sha256": "887c0f58ad938ed17d562b9c0abe05645d8bccac9e43cd3d676cd63a22875b82",
        "commit": "2d69373a2a2e0fdc08615e41c8a3dc9676cff22c",
        "protocol": "hypersync-capture-identity/v1",
        "status": "ACTIVE",
        "reason": "2026-08-14 批1锁修复版本；批C 升级该脚本时按维护纪律同步登记的被替换版本。",
    },
    {
        "script": "fetch_hypersync_v2.py",
        "sha256": "f544a1968dfa86e1705b2c028b33ad591e869b4194e257313b58519bb12c6d11",
        "commit": "0ec6d1e2365c339d200fc26d17344f962fbdb7a9",
        "protocol": "hypersync-capture-identity/v1",
        "status": "ACTIVE",
        "reason": "6.46.1 U2 升级 done/v4 前的现役 identity/v1 签发版本。",
    },
    {
        "script": "fetch_sqd_evm.py",
        "sha256": "042fe44eb1f8aea703f195707d91a9ad89e239ba94414b1dc03c0b837ff55a4b",
        "commit": "a620fd91f9e82fa8b52a960acb6ae2d4bcfc8db8",
        "protocol": "evm-collector-run/v2",
        "status": "ACTIVE",
        "reason": "2026-08-04 SQD 正式 receipt 制度起始版本，用于备用 CSV 正式采集。",
    },
    {
        "script": "fetch_sqd_evm.py",
        "sha256": "6c8306d05ab3fadd186c99daac732b88a3523e7d6d8d7821dde1da3a6b11acb3",
        "commit": "2d8ad6382d72e1acb85e875d4b8cd8ca58758bea",
        "protocol": "evm-collector-run/v2",
        "status": "ACTIVE",
        "reason": "2026-08-15 备用采集器完整性加固后用于 SQD 正式 CSV 采集。",
    },
)


def historical_script_hashes(name, protocol=None):
    """Return matching ACTIVE hashes, with any REVOKED twin taking precedence.

    Revocation is hash-wide: one REVOKED registry entry removes that sha256 from every
    script/protocol allowed set even when another entry still marks the same hash ACTIVE.
    ``protocol=None`` retains the registry-inspection API; production callers must bind an
    exact protocol.
    """
    revoked = {
        entry["sha256"]
        for entry in COLLECTOR_HISTORY
        if entry["status"] == "REVOKED"
    }
    return {
        entry["sha256"]
        for entry in COLLECTOR_HISTORY
        if entry["script"] == name and entry["status"] == "ACTIVE"
        and (protocol is None or entry["protocol"] == protocol)
        and entry["sha256"] not in revoked
    }
