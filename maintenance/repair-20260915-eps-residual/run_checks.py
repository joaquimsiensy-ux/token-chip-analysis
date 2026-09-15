"""捕获工单指定检查的原始输出与退出码。"""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
checks=[['changelog_lint.py'],['docs_lint.py','--all'],['test_version_consistency.py'],
        ['invariant_scan.py'],['fixtures_lint.py']]
results=[]
for check in checks:
    args=[sys.executable,str(ROOT/'scripts/tests'/check[0]),*check[1:]]
    start=time.monotonic()
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    name=check[0].removesuffix('.py')
    (OUT/(name+'.log')).write_text(p.stdout+p.stderr)
    result={'command':shlex.join(args),'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-start}
    results.append(result)
    print(json.dumps(result),flush=True)
(OUT/'check_results.json').write_text(json.dumps(results,indent=2))
