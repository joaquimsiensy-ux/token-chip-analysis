"""执行调度裁决的 T6 正式运行与 T7 同输入双版本对照；不修改输入。"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PROD=ROOT/'scripts/report/entity_source_trace.py'

def run(tag,args,cwd):
    log=OUT/(tag+'.log')
    err=OUT/(tag+'.stderr.txt')
    env=os.environ.copy()
    env['PYTHONPATH']=str(ROOT/'scripts/report')+os.pathsep+env.get('PYTHONPATH','')
    start=time.monotonic()
    with log.open('w') as stdout,err.open('w') as stderr:
        p=subprocess.run(args,cwd=cwd,env=env,stdout=stdout,stderr=stderr)
    stderr=err.read_text()
    with log.open('a') as f:
        f.write('\n--- STDERR (verbatim) ---\n'+stderr)
    receipt={'command':shlex.join(args),'argv':args,'cwd':str(cwd),
             'PYTHONPATH':env['PYTHONPATH'],'exit_code':p.returncode,
             'elapsed_seconds':time.monotonic()-start,
             'production_sha256':hashlib.sha256(Path(args[1]).read_bytes()).hexdigest(),
             'stdout_and_stderr_log':log.name,'stderr_file':err.name}
    (OUT/(tag+'_result.json')).write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2),flush=True)
    return receipt

if sys.argv[1]=='apu':
    d=ROOT/'.staging_eps/apu'
    old=json.loads((d/'provenance_ledger.json').read_text())
    args=[sys.executable,str(PROD)]
    for k,v in old['params'].items():
        if v is None or v is False:continue
        args.append('--'+k.replace('_','-'))
        if v is not True:args.append(str(v))
    args+=['--out','provenance_ledger_704.json']
    run('apu_formal_followup',args,d)
else:
    base=subprocess.run(['git','show','HEAD:scripts/report/entity_source_trace.py'],cwd=ROOT,capture_output=True,check=True).stdout
    assert hashlib.sha256(base).hexdigest()=='ff4b640a1adbcecf8f3651efbda04493d3085754f939da1ef23b8d9f2efe0fc3'
    layout=Path(tempfile.mkdtemp(prefix='eps_703_followup_'))
    report=layout/'scripts/report'
    report.mkdir(parents=True)
    oldscript=report/'trace_703.py'
    oldscript.write_bytes(base)
    (report/'wave_scan.py').symlink_to(ROOT/'scripts/report/wave_scan.py')
    for sub in ['lib','solana']:(layout/'scripts'/sub).symlink_to(ROOT/'scripts'/sub,target_is_directory=True)
    d=ROOT/'.staging_eps/pythia'
    dest=d/'t7_compare'
    dest.mkdir(exist_ok=True)
    common=['--duckdb',str(d/'s2_work.duckdb'),'--edges-table','edges',
            '--entity-file',str(d/'entity_file_flat.json'),'--allow-no-labels',
            '--total-supply','998158041739995','--edge-budget','5000000']
    for version,script in [('703',oldscript),('704',PROD)]:
        args=[sys.executable,str(script),*common,'--out',str(dest/f'ledger_{version}.json')]
        run('pythia_run_'+version,args,ROOT)
