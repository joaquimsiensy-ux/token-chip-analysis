#!/usr/bin/env python3
"""B2-G0 regressions for the two Batch-1 review P3 hardenings."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/labels"))
sys.path.insert(0, str(ROOT / "scripts/lib"))

import receipt_kernel
from risk_flags import parse_risk_flags
from test_repair_batch_a import BLINDREVIEW_RESIDUAL_INVISIBLES


def test_risk_flags_invisible_and_type_fail_closed():
    assert parse_risk_flags("\u200btornado-user") == ("tornado-user",)
    assert parse_risk_flags("\ufeff") == ()
    assert parse_risk_flags(" a |\u200b| b ") == ("a", "b")
    invalid = {
        "U+200B 中段": "torna\u200bdo-user",
        "U+3164 末尾": "tornado-user\u3164",
        "大写字母": "Tornado-user",
        "非 ASCII 字母": "tornadó-user",
    }
    invalid.update({
        f"残余不可见 U+{ord(char):04X}": f"torna{char}do-user"
        for char in BLINDREVIEW_RESIDUAL_INVISIBLES
    })
    accepted = []
    for label, raw in invalid.items():
        try:
            parse_risk_flags(raw)
        except ValueError:
            pass
        else:
            accepted.append((label, raw))
    assert not accepted, f"非法 risk_flags 未 fail-closed: {accepted!r}"
    for malformed in ([], ["a"], 0, 1, False, True):
        try:
            parse_risk_flags(malformed)
        except TypeError:
            pass
        else:
            raise AssertionError(f"non-string risk_flags accepted: {malformed!r}")


def test_producer_parent_symlink_rejected():
    with tempfile.TemporaryDirectory(prefix="batch2-producer-") as td:
        repo = Path(td).resolve()
        real = repo / "real" / "nested"
        real.mkdir(parents=True)
        producer = real / "producer.py"
        producer.write_text("# fixture\n", encoding="utf-8")
        (repo / "linked").symlink_to(repo / "real", target_is_directory=True)
        shown = repo / "linked" / "nested" / "producer.py"
        with mock.patch.object(receipt_kernel, "REPO", repo):
            try:
                receipt_kernel._producer_ref(shown)
            except receipt_kernel.ReceiptKernelError:
                pass
            else:
                raise AssertionError("producer path with intermediate symlink accepted")


def test_build_labels_uses_canonical_merge():
    source = (ROOT / "scripts/labels/build_labels.py").read_text(encoding="utf-8")
    assert "from risk_flags import canonical_risk_flags, merge_risk_flags, parse_risk_flags" in source
    assert "old['risk_flags'] + '|' + risk_flag" not in source
    assert "merge_risk_flags(old['risk_flags'], risk_flag)" in source


def main():
    test_risk_flags_invisible_and_type_fail_closed()
    test_producer_parent_symlink_rejected()
    test_build_labels_uses_canonical_merge()
    print("PASS B2-G0: invisible/type risk flags + producer symlink + OB-2 canonical merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
