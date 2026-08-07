#!/usr/bin/env python3
"""B2-D regression: READY cannot omit the reconciliation wrapper/receipts."""
from __future__ import annotations

import os
import tempfile

from test_handoff_manifest import GEN, make_case, run


def main():
    with tempfile.TemporaryDirectory(prefix="batch2-ready-recon-") as root:
        case = os.path.join(root, "missing-reconciliation")
        os.makedirs(case)
        make_case(case)
        os.unlink(os.path.join(case, "reconciliation_report.json"))
        response = run(["generate", "--case-dir", case, "--status", "READY"] + GEN)
        output = response.stdout + response.stderr
        assert response.returncode == 2 and "reconciliation" in output.lower(), (
            response.returncode, output)
    print("PASS B2-D: READY rejects missing reconciliation wrapper and bound receipts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
