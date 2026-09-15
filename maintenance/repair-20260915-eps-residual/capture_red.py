"""离线保留工单 A3/C-RED 的生产 CLI 输出和 ledger 明细。"""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/tests'))
import test_entity_source_trace as t

OUT = Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

with (OUT / 'red_evidence.txt').open('w') as f:
    for name, edges, total in [('T1', t.eps_residual_edges(), 10 * 2**90),
                               ('T2-small', [(t.day(1), 'X', 'D', 100)], 10**6)]:
        d = ROOT / '.staging_eps' / 'red' / name
        d.mkdir(parents=True, exist_ok=True)
        ep = t.write_edges(str(d), edges)
        p, ledger = t.eps_run_version(str(d), ep, {'D': ['D']}, total, t.SCRIPT)
        f.write(f'## {name}: 7.0.3 baseline\n')
        f.write('COMMAND: ' + shlex.join(p.args) + '\n')
        f.write('ENV: PYTHONPATH=' + str(ROOT / 'scripts/report') + '\n')
        f.write(f'EXIT_CODE: {p.returncode}\n')
        f.write(f'TEST_SHA256: {sha(ROOT / "scripts/tests/test_entity_source_trace.py")}\n')
        f.write(f'DRIVER_SHA256: {sha(__file__)}\nPRODUCTION_SHA256: {sha(t.SCRIPT)}\n')
        f.write('STDOUT_BEGIN\n' + p.stdout + 'STDOUT_END\nSTDERR_BEGIN\n' + p.stderr + 'STDERR_END\n')
        assert p.returncode == 0 and ledger
        e = ledger['entities'][0]
        assert e['simulation']['data_gap_events'] == 1
        for a in ('current', 'peak'):
            assert any(c['subkind'] == 'data_gap' and c['raw'] == ('1' if name == 'T1' else '100')
                       for c in e['anchors'][a]['composition'])
        f.write('LEDGER_BEGIN\n' + json.dumps({'entity': e, 'sensitivity': ledger['bounds_sensitivity']},
                                             indent=2, ensure_ascii=False) + '\nLEDGER_END\n\n')
    command = [sys.executable, '-c', 'import sys; sys.path.insert(0, "scripts/tests"); import test_entity_source_trace as t; t.test_eps_residual(); sys.exit(t.finish())']
    p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    f.write('## Proposed assertions against unchanged 7.0.3\nCOMMAND: ' + shlex.join(command) + '\n')
    f.write(f'EXIT_CODE: {p.returncode}\nTEST_SHA256: {sha(ROOT / "scripts/tests/test_entity_source_trace.py")}\nPRODUCTION_SHA256: {sha(t.SCRIPT)}\n')
    f.write('STDOUT_BEGIN\n' + p.stdout + 'STDOUT_END\nSTDERR_BEGIN\n' + p.stderr + 'STDERR_END\n')
    assert p.returncode == 1
print('RED captured:', OUT / 'red_evidence.txt')
