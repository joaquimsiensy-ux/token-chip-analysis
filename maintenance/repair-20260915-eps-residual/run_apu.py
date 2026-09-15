"""从已校验的 staging 账本还原 CLI，仅写入 staging。"""
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[2]
d = ROOT / '.staging_eps/apu'
r = json.loads((d / 'provenance_ledger.json').read_text())
diagnostic = '--diagnostic-without-receipt' in sys.argv
args = [sys.executable, str(ROOT / 'scripts/report/entity_source_trace.py')]
for k, v in r['params'].items():
    if v is None or v is False or (diagnostic and k == 'acknowledge_flip'):
        continue
    args.append('--' + k.replace('_', '-'))
    if v is not True:
        args.append(str(v))
tag = '704_diagnostic' if diagnostic else '704'
args += ['--out', f'provenance_ledger_{tag}.json']
t0 = time.monotonic()
with (d / f'trace_{tag}.log').open('w') as log:
    p = subprocess.run(args, cwd=d, stdout=log, stderr=subprocess.STDOUT)
receipt = {'command': shlex.join(args), 'cwd': str(d), 'exit_code': p.returncode,
           'elapsed_seconds': time.monotonic() - t0}
(d / f'trace_{tag}_run.json').write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt, indent=2))
sys.exit(p.returncode)
