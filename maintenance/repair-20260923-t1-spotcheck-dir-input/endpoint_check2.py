import json, subprocess, sys, tempfile, hashlib
from pathlib import Path
HEAD=Path('/Users/uravvv/.claude/skills/token-chip-analysis'); BASE=Path('/tmp/t1_base'); L=Path(__file__).parent
sys.path[:0]=[str(HEAD/'scripts/tests'),str(HEAD/'scripts/lib'),str(HEAD/'scripts/report')]
import test_anchor_plan_v3 as T
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def probe(root, fx):
    f=Path(tempfile.mkstemp(suffix='.json')[1]); f.write_text(json.dumps(fx))
    p=subprocess.run([sys.executable,'-B',str(L/'ep_probe.py'),str(root),str(f)],capture_output=True,text=True)
    if p.returncode!=0: print(p.stderr[-800:]); raise SystemExit('probe failed')
    return json.loads(p.stdout.strip().splitlines()[-1])
R=[]
with tempfile.TemporaryDirectory(prefix='ep_dir_') as td, tempfile.TemporaryDirectory(prefix='ep_csv_') as tc:
    rd=Path(td).resolve(); src_d,plan_d,rec_d=T._produce_plan(rd,directory=True); plan=json.loads(plan_d.read_text()); manifest=Path(plan['input_manifest']['path'])
    rc=Path(tc).resolve(); src_c,plan_c,rec_c=T._produce_plan(rc); plan_csv=json.loads(plan_c.read_text())
    fx={'dir':{'root':str(rd),'source':str(src_d),'plan':str(plan_d),'receipt':str(rec_d),'auth_input':str(manifest),'token':T.TOKEN},
        'csv':{'root':str(rc),'source':str(src_c),'plan':str(plan_c),'receipt':str(rec_c),'auth_input':str(src_c),'token':T.TOKEN}}
    b=probe(BASE,fx); h=probe(HEAD,fx)
    R.append(('G1 基线 main→build_envelope inputs.input=目录', Path(b['dir']['main'][1] or '')==src_d and b['dir']['main'][0]==1))
    R.append(('G1 HEAD  main→build_envelope inputs.input=清单', Path(h['dir']['main'][1] or '')==manifest and h['dir']['main'][0]==1))
    import receipt_kernel as RK
    def env(inp):
        try: RK.build_envelope('time-spotcheck/v3',plan['target'],str(HEAD/'scripts/lib/time_spotcheck.py'),'formal',inputs={'plan':str(plan_d),'plan_receipt':str(rec_d),'input':inp},input_base=rd); return 'OK'
        except Exception as e: return str(e)
    R.append(('G1 基线绑定对象经真实 receipt_kernel → 拒 not a regular file', 'not a regular file' in env(b['dir']['main'][1])))
    R.append(('G1 HEAD 绑定对象经真实 receipt_kernel → 封装成功', env(h['dir']['main'][1])=='OK'))
    R.append(('G2 基线消费者 目录计划+清单 → 拒 identity not a regular file', b['dir']['auth_input'][0]=='REJ' and 'time plan input identity is not a regular file' in b['dir']['auth_input'][1]))
    R.append(('G2 HEAD 消费者 目录计划+清单 → 放行且==plan', h['dir']['auth_input']==['OK',True]))
    R.append(('G2 HEAD 消费者 目录计划+计划文件 → 拒 not bound through manifest', h['dir']['auth_planfile'][0]=='REJ' and 'not bound through the signed input manifest' in h['dir']['auth_planfile'][1]))
    R.append(('G4 CSV 生产者 基线==HEAD 且绑文件本身', b['csv']['main']==h['csv']['main'] and Path(h['csv']['main'][1])==src_c))
    R.append(('G4 CSV 消费者 放行 基线==HEAD==plan', b['csv']['auth_input']==h['csv']['auth_input']==['OK',True]))
    R.append(('G4 CSV 消费者 错绑(input=计划文件) 拒收文本 基线==HEAD', b['csv']['auth_planfile']==h['csv']['auth_planfile'] and b['csv']['auth_planfile'][0]=='REJ'))
    print('   G4 错绑文本:', h['csv']['auth_planfile'][1][:110])
    # G3 自洽重绑（HEAD）
    orig=manifest.read_bytes(); doc=json.loads(orig); doc['input']['sha256']='0'*64; manifest.write_text(json.dumps(doc,ensure_ascii=False,indent=2))
    new_ref={'path':str(manifest),'size':manifest.stat().st_size,'sha256':sha(manifest)}
    pd=json.loads(plan_d.read_text()); rr=json.loads(rec_d.read_text()); pd['input_manifest']=new_ref; rr['inputs']['input_manifest']=new_ref
    plan_d.write_text(json.dumps(pd,ensure_ascii=False,indent=2)+'\n'); rec_d.write_text(json.dumps(rr,ensure_ascii=False,indent=2)+'\n'); T._refresh_receipt(plan_d,rec_d)
    h3=probe(HEAD,{'dir':fx['dir']})
    R.append(('G3 HEAD 自洽重绑(plan.input 不变) → 拒 manifest identity differs', h3['dir']['auth_input'][0]=='REJ' and 'input manifest identity differs from signed identity' in h3['dir']['auth_input'][1]))
for n,v in R: print(('PASS ' if v else 'FAIL ')+n)
print('ENDPOINT', 'ALL PASS' if all(v for _,v in R) else 'HAS FAIL', f'{sum(v for _,v in R)}/{len(R)}')
