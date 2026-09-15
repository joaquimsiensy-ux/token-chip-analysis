#!/usr/bin/env python3
"""Offline unit migration fixtures; producer headers model old native versions."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lib'))
sys.path.insert(0, str(Path(__file__).parent))
from test_r9_batch3_solana_observation import SolanaTransportFake, MINT, _load


def main():
    scan = _load(ROOT / 'scripts/solana/scan_token_accounts.py', 'history_reuse_scan')
    ident = _load(ROOT / 'scripts/report/identity_snapshot_receipt.py', 'history_reuse_identity')
    old_scanner = next(r['sha256'] for r in __import__('producer_history').PRODUCER_HISTORY
                       if r['script'] == 'scripts/solana/scan_token_accounts.py'
                       and r['commit'] == '2fcbaa788eba2e551f739786dee2b15b113133d7')
    old_identity = next(r['sha256'] for r in __import__('producer_history').PRODUCER_HISTORY
                        if r['script'] == 'scripts/report/identity_snapshot_receipt.py'
                        and r['commit'] == '2fcbaa788eba2e551f739786dee2b15b113133d7')
    prior = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                assert scan.main([MINT, '--program', 'spl', '--rpc', 'https://fixture.invalid',
                                  '--out', 'snapshot.json', '--bundle', 'bundle.json'],
                                 request_json=SolanaTransportFake()) == 0
            meta = Path('data/holders_snapshot_meta.json')
            value = json.loads(meta.read_text())
            value['producer']['sha256'] = old_scanner
            meta.write_text(json.dumps(value))
            actual_sha = ident.sha
            # Model a scanner upgrade without replacing raw parser or validator.
            def upgraded_sha(path):
                if Path(path).resolve() == (ROOT / 'scripts/solana/scan_token_accounts.py').resolve():
                    return 'f' * 64
                return actual_sha(path)
            with mock.patch.object(ident, 'sha', side_effect=upgraded_sha):
                emitted = ident.emit_solana(MINT, 104, 'data/holders_owners.json', str(meta), 100,
                                             'data/identity.json')
                assert emitted['source']['collector']['sha256'] == old_scanner
                assert not ident.validate_receipt('data/identity.json', 'data/holders_owners.json', 100, 'sol')
                emitted['producer']['sha256'] = old_identity
                Path('data/identity.json').write_text(json.dumps(emitted))
                assert not ident.validate_receipt('data/identity.json', 'data/holders_owners.json', 100, 'sol')
                emitted['source']['collector']['sha256'] = '0' * 64
                Path('data/identity.json').write_text(json.dumps(emitted))
                assert ident.validate_receipt('data/identity.json', 'data/holders_owners.json', 100, 'sol')
                value['producer']['sha256'] = '0' * 64
                meta.write_text(json.dumps(value))
                try:
                    ident.validate_solana_source(MINT, 'data/holders_owners.json', str(meta), 100)
                except ValueError:
                    pass
                else:
                    raise AssertionError('unknown historical scanner was accepted')
        finally:
            os.chdir(prior)
    print('PASS: verified historical source, preserved provenance, unknown hashes and mismatched collector rejected')


if __name__ == '__main__':
    main()
