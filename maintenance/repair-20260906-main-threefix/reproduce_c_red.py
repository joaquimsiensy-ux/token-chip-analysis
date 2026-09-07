"""Use the existing A4 fixture up to its first clean finalize, without editing it."""
from pathlib import Path
import hashlib
import shlex
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/tests'))
import test_a4_gate as t

class Captured(Exception):
    pass


def trace(frame, event, arg):
    if (event == 'line' and frame.f_code is t.main.__code__
            and frame.f_lineno == 426):
        sys.settrace(None)
        original = frame.f_locals['d']
        copied = Path(tempfile.mkdtemp(prefix='threefix_c_red_')) / 'case'
        shutil.copytree(original, copied)
        t.rebind_case_inputs(original, copied)
        seal = copied / 'a4_seal.json'
        results = []
        args = ['finalize', '--case-dir', str(copied), '--seal-files',
                'findings.md,analysis-state.json,v_ok.json',
                '--verdicts-file', str(copied / 'v_ok.json')]
        result = t.run(t.GATE, args)
        results.append(('a4_gate finalize (test_a4_gate.run adds --workflow-type independent-audit)',
                        t.GATE, args + ['--workflow-type', 'independent-audit'], result))
        created = seal.is_file()
        args = ['--mode', 'analysis-audit', '--md', str(copied / 'report.md'),
                '--out', str(copied / 'report.html'), '--facts', str(copied / 'facts.json'),
                '--state', str(copied / 'analysis-state.json'), '--a4-seal', str(seal)]
        built = t.run(t.BUILD, args)
        results.append(('build_html G9 (existing run() A5/formal harness)', t.BUILD, args, built))
        output = '\nC RED\nreproducer: PYTHONDONTWRITEBYTECODE=1 python3 maintenance/repair-20260906-main-threefix/reproduce_c_red.py\n'
        for name in ['maintenance/repair-20260906-main-threefix/reproduce_c_red.py',
                     'scripts/tests/test_a4_gate.py', 'scripts/report/a4_gate.py',
                     'scripts/report/build_html.py']:
            output += f'sha256 {name}: {hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}\n'
        for label, script, argv, p in results:
            output += f'{label}\ncommand: {shlex.join([sys.executable, script, *argv])}\nexit_code: {p.returncode}\n--- stdout ---\n{p.stdout}--- stderr ---\n{p.stderr}\n'
        output += f'finalize a4_seal.json exists: {created}\n'
        with (ROOT / 'maintenance/repair-20260906-main-threefix/red_evidence.txt').open('a') as fh:
            fh.write(output)
        print(output)
        assert result.returncode == 0 and created
        assert '封口路径重复' in built.stdout + built.stderr
        raise Captured
    return trace

sys.settrace(trace)
try:
    t.main()
except Captured:
    pass
finally:
    sys.settrace(None)
