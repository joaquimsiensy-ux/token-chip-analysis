"""子进程探针：从给定仓库根导入生产者/消费者，对给定夹具执行四类操作，打印 JSON。"""
import json, sys, hashlib
from pathlib import Path
ROOT=Path(sys.argv[1]); fx=json.loads(Path(sys.argv[2]).read_text())
sys.path[:0]=[str(ROOT/'scripts/lib'),str(ROOT/'scripts/report')]
import time_spotcheck as TS, shared_release_receipt as SH
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p,root): p=Path(p); return {'path':p.resolve().relative_to(Path(root).resolve()).as_posix(),'size':p.stat().st_size,'sha256':sha(p)}
def authority(root,input_file,plan_path,receipt_path):
    plan=json.loads(Path(plan_path).read_text()); rec={'inputs':{'plan':ref(plan_path,root),'plan_receipt':ref(receipt_path,root),'input':ref(input_file,root)}}
    try: r=SH._validated_time_plan_authority(Path(root),rec,plan['target']); return ['OK', r==plan]
    except Exception as e: return ['REJ', f'{type(e).__name__}: {e}']
def run_main(root,source,plan_path,token):
    captured={}
    def fake(*a,**k): captured.update(k.get('inputs') or {}); raise RuntimeError('stop-before-rpc')
    out=Path(root)/'ts.json'; sys.argv=['time_spotcheck.py','--plan',str(plan_path),'--input',str(source),'--chain','bsc','--token',token,'--final-block','300','--rpc','http://127.0.0.1:9','--out',str(out)]
    TS.build_envelope=fake; rc=TS.main(); return [rc, captured.get('input')]
out={}
for name,c in fx.items():
    root,source,plan,rec=c['root'],c['source'],c['plan'],c['receipt']
    out[name]={'main':run_main(root,source,plan,c['token']),
               'auth_input':authority(root,c['auth_input'],plan,rec),
               'auth_planfile':authority(root,plan,plan,rec)}
print(json.dumps(out))
