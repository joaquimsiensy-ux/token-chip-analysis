"""Offline reproduction of sol-rows chart/validator disagreement before B1."""
from pathlib import Path
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lib'))
from camp_series_provenance import validate_series_payload

case = Path(tempfile.mkdtemp(prefix='threefix_b_red_'))
os.environ.setdefault('MPLCONFIGDIR', str(case / 'mpl'))
css = {'dates': ['2026-01-01', '2026-01-02'],
       'series': {'大庄': [60.0, 60.0], '散户': [40.0, 40.0], '锁仓/销毁': [5.0, 5.0]}}
state = {'token': {'symbol': 'TT'}, 'camp_share_series': css,
         'provenance': {'camp_series_sidecar': {'series_format': 'sol-rows'}}}
sp = case / 'analysis-state.json'
sp.write_text(json.dumps(state, ensure_ascii=False))
cmd = [sys.executable, 'scripts/report/figures_from_facts.py', 'fig1',
       '--state', str(sp), '--out', str(case / 'fig1.png')]
p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
output = '\nB RED\nreproducer: PYTHONDONTWRITEBYTECODE=1 python3 maintenance/repair-20260906-main-threefix/reproduce_b_red.py\n'
for name in ['maintenance/repair-20260906-main-threefix/reproduce_b_red.py',
             'scripts/tests/test_figures_from_facts.py', 'scripts/report/figures_from_facts.py',
             'scripts/report/standard_charts.py', 'scripts/report/a5_report_seal.py',
             'scripts/report/audit_release_gate.py', 'scripts/lib/camp_series_provenance.py']:
    output += f'sha256 {name}: {hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}\n'
output += f'fixture: {json.dumps(state, ensure_ascii=False)}\ncommand: {shlex.join(cmd)}\nexit_code: {p.returncode}\n--- stdout ---\n{p.stdout}--- stderr ---\n{p.stderr}\n'
assert p.returncode == 0, output
receipt = (case / 'fig1_legend_receipt.json').read_text()
output += '--- receipt original ---\n' + receipt + '\n'
valid = validate_series_payload(css, series_format='sol-rows')
output += f'call: camp_series_provenance.validate_series_payload(css, series_format="sol-rows")\nresult: PASS (no exception), returned {valid!r}; non-exempt sum=100\n'
with (ROOT / 'maintenance/repair-20260906-main-threefix/red_evidence.txt').open('a') as f:
    f.write(output)
print(output)
obj = json.loads(receipt)
assert '锁仓/销毁' in obj['rendered_camps'] and obj['excluded_series'] == []
