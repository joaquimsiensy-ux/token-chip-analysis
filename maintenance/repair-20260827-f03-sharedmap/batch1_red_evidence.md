# F-03 batch 1 RED evidence

Baseline gate checked before production edits:

- branch: `main`
- HEAD: `5156f6e9a51ac0235a6855033ed3f2b53fe35686`
- probe SHA-256: `bccf1802b6a5c9d9bbbdb12e19354ad761416c631e3cdfde2449f7fe1794f176`
- no network requests were made; both cases use `FixtureTransport`.

## RED 1 — a forward-moving finalized head is treated as identity drift

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_f03_sharedmap_reuse.py
```

Exit code: `1`

Raw output:

```text
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_f03_sharedmap_reuse.py", line 421, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_f03_sharedmap_reuse.py", line 415, in main
    test()
    ~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_f03_sharedmap_reuse.py", line 165, in test_head_forward_anchor_and_gap_exact_rechecks
    assert reused == counts and (lower, upper) == (LOWER, UPPER), info
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: {'asset_path': '/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/f03-head-forward-3n4eo5b3/map.json', 'version': '20260827', 'sha256': '9ee868d2943bdd2ebe38c8e81881413bf1e63ea494fad413734abe09c88586a7', 'supersedes': None, 'generated_at': '2026-08-27T12:38:38.485606+00:00', 'reused_ranges': [], 'canary': {'slots': [], 'counts_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'verified_at': '2026-08-27T12:38:38.486958+00:00'}, 'fallback_reason': 'metadata-changed'}
```

Interpretation: stable identity fields and endpoint are unchanged, but the baseline compares the entire normalized metadata dictionary. The expected dynamic changes (`finalized_head`, `number`, and current-head `hash`) therefore reject reuse before any recheck.

## RED 2 — an anchor mismatch is inexpressible and ignored by the baseline gate

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts/tests').resolve()))
import test_f03_sharedmap_reuse as t
t.test_anchor_mismatch_is_not_ignored()
PY
```

Exit code: `1`

Raw output:

```text
Traceback (most recent call last):
  File "<stdin>", line 5, in <module>
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_f03_sharedmap_reuse.py", line 184, in test_anchor_mismatch_is_not_ignored
    assert reused is None
           ^^^^^^^^^^^^^^
AssertionError
```

Interpretation: the fixture returns a different hash for historical slot 1000, but the baseline implementation has no identity-anchor request at all. With current metadata equal to the asset metadata, it ignores the contradictory historical hash and reuses the counts. This is the workorder's “baseline cannot express the anchor mismatch” case made executable.

## RED scope

The test file and its `run_all.py` registration were written before any production-code edit. The remaining F-03 matrix intentionally was not forced past the first failure; it will be exercised after construction and recorded as GREEN in `batch1_done.md`.
