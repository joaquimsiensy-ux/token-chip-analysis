#!/usr/bin/env python3
"""R1 offline evidence harness. prepare ROOT; run ROOT baseline|new; compare ROOT; probe ROOT.
Inputs and formal_cli_args are generated once; ROOT must be a resolved tempfile directory.
Before prepare, use git show 634c083 to place flow_baseline.py and wave_scan.py in ROOT.
Probe: probe ROOT baseline|new JOB; audit ROOT checks all six diagnostic pairs.
The original, uninstrumented CLI processes supply run timing and per-child RSS.
No production imports are patched in the timed CLI executions. RSS uses each child's wait4.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/tests'))
from sqd_v4_test_fixture import formal_cli_args
TOTAL = 10**12
Z = '0x' + '0'*40
DEAD = '0x' + '0'*36 + 'dead'

def save(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main_edges():
    e = []
    def add(d, f, t, v): e.append((d*86400, f, t, v))
    for i in range(8): add(0, Z, f'Src{i}', 100_000_000_000)
    for k in range(8):
        name = 'MixedHub' if k == 7 else f'Sink{k}'
        for i in range(5): add(50+k*25, f'Src{i}', name, 6_000_000_000+k*500_000_000+i*30_000_000)
        if k == 2:
            for i in range(5): add(400, f'Src{i}', name, 5_000_000_000+i*40_000_000)
    for j in range(2):
        for typ in ['Pulse','Refill']:
            who = typ+str(j)
            add(0, Z, who, 50_000_000_000)
            for i in range(24):
                recv = f'{who}R{i}'
                if typ == 'Refill': add(100, Z, recv, 100_000_000)
                add(300+j*20, who, recv, 1_000_000_000+j*200_000_000+(typ=='Refill')*80_000_000+i*2_000_000)
        who='Slow'+str(j)
        add(0, Z, who, 60_000_000_000)
        for i in range(600): add(110+i, who, f'{who}R{i}', 50_000_000+j*10_000_000+i*10_000)
    for i in range(23): add(701, 'MixedHub', f'MixedR{i}', 1_300_000_000+i*2_000_000)
    add(701,'MixedHub','MixedHub',123_000_000)
    add(700,'TinySrc','MixedHub',100_000_000)
    # Address count and 800-day span; dust cannot enter any candidate.
    for i in range(3500): add(800, Z, f'Noise{i}', 1)
    return e

def expand(edges, target):
    # Split positive semantic edges without changing amounts, dates or recipient totals.
    splittable = sum(v > 1 for _,_,_,v in edges)
    q, r = divmod(target-len(edges), splittable)
    result=[]
    for ts,f,t,v in edges:
        n = 1
        if v > 1:
            n += q+(r>0); r=max(0,r-1)
        a,b=divmod(v,n)
        assert a>0
        result.extend((ts,f,t,a+(i<b)) for i in range(n))
    random.Random(20260924).shuffle(result)
    assert len(result)==target
    return result

def tie_edges():
    e=[(0,Z,f'Src{i}',80_000_000_000) for i in range(5)]
    for hub in ['TieSinkA','TieSinkB']:
        e += [(10*86400,f'Src{i}',hub,6_000_000_000) for i in range(5)]
    e += [(11*86400,'TieSinkA','TieSinkA',999),(11*86400,'Tiny','TieSinkA',100_000_000)]
    for who in ['TieSlowA','TieSlowB']:
        e.append((0,Z,who,80_000_000_000))
        for i in range(540):
            amt=60_000_000+i*1000 if i<490 else (50_000_000 if i<530 else 40_000_000)
            e.append(((100+i)*86400,who,who+'R'+str(i),amt))
    return e

def mixed_edges():
    e=[(0,Z,f'Src{i}',80_000_000_000) for i in range(8)]
    e += [(700*86400,f'Src{i}','MixedHub',6_000_000_000) for i in range(5)]
    e += [(701*86400,'MixedHub',f'MixedR{i}',1_000_000_000) for i in range(20)]
    e += [(701*86400,'MixedHub','MixedHub',1_000_000_000),(701*86400,'TinySrc','MixedHub',100_000_000)]
    return e

def inputs(root, name, rows, kinds):
    import duckdb
    import pyarrow as pa
    d=root/name; d.mkdir()
    save(d/'rows.json',rows)
    addrs=sorted({x for _,f,t,_ in rows for x in [f,t]}-{Z,DEAD})
    mapping={a:'0x'+f'{i+1:040x}' for i,a in enumerate(addrs)}|{Z:Z,DEAD:DEAD}
    save(d/'mapping.json',mapping)
    result={}
    if 'sol' in kinds:
        ep=d/'edges.jsonl'
        with ep.open('w') as fh:
            for i,(ts,f,t,v) in enumerate(rows): fh.write(json.dumps([ts,0,i,-1,f,t,v])+'\n')
        result['sol']=['--edges-sol',str(ep)]+formal_cli_args(ep)
    for kind in sorted(set(kinds)-{'sol'}):
        rr=[(ts,mapping[f],mapping[t],v) for ts,f,t,v in rows] if kind=='evm' else rows
        arr=pa.table({'ts':[x[0] for x in rr], 'f':[x[1] for x in rr], 't':[x[2] for x in rr], 'amt':[x[3] for x in rr]})
        con=duckdb.connect(str(d/'edges.duckdb') if kind=='duck' else ':memory:')
        con.register('input_rows',arr)
        con.execute('CREATE TABLE edges AS SELECT ts::BIGINT ts, f::VARCHAR f,t::VARCHAR t,amt::HUGEINT amt FROM input_rows')
        if kind=='duck': result[kind]=['--duckdb',str(d/'edges.duckdb')]
        else:
            con.execute('CREATE TABLE numbered AS SELECT row_number() OVER () bn,* FROM edges')
            evm=d/'evm'; evm.mkdir()
            n=len(rr)
            for i,(lo,hi) in enumerate([(1,n//2),(n//2+1,n)]):
                rd=evm/f'run_{i}'; rd.mkdir()
                con.execute(f"COPY (SELECT '0x'||lpad(hex(bn),64,'0') transaction_hash,0::BIGINT log_index,bn::BIGINT block_number,'0x'||lpad(substr(f,3),64,'0') topic1,'0x'||lpad(substr(t,3),64,'0') topic2,'0x'||lpad(hex(amt),64,'0') AS data FROM numbered WHERE bn BETWEEN {lo} AND {hi}) TO '{rd/'logs.parquet'}' (FORMAT PARQUET)")
                con.execute(f"COPY (SELECT bn::BIGINT number,ts::VARCHAR AS timestamp FROM numbered WHERE bn BETWEEN {lo} AND {hi}) TO '{rd/'blocks.parquet'}' (FORMAT PARQUET)")
            result[kind]=['--edges-evm-v2',str(evm)]
        con.close()
    return result

def prepare(root):
    assert (root/'flow_baseline.py').exists()
    jobs=[]
    def job(name,kind,args,extra=[]):
        jobs.append({'name':name,'kind':kind,'args':args+['--total-supply',str(TOTAL)]+extra})
    main=expand(main_edges(),300000)
    assert len({a for _,f,t,_ in main for a in [f,t]})>=3000
    assert (max(x[0] for x in main)-min(x[0] for x in main))//86400>=400
    for who in ['Slow0','Slow1']:
        totals=Counter()
        for _,f,t,v in main:
            if f==who: totals[t]+=v
        assert len(set(totals.values()))==len(totals)
    for kind,args in inputs(root,'main',main,['sol','duck','evm']).items():
        job('main_'+kind,kind,args)
        if kind=='sol':
            ent=root/'entity.json'; exc=root/'exclude.json'
            save(ent,{'A':['Sink0']+[f'Src{i}' for i in range(5)],'B':['Sink1']})
            save(exc,['Sink3'])
            job('main_sol_entity',kind,args,['--entity-file',str(ent)])
            job('main_sol_entity_exclude',kind,args,['--entity-file',str(ent),'--exclude-file',str(exc)])
    for name,rows,kinds in [
        ('ties',tie_edges(),['sol','duck','evm']),
        ('empty_candidates',[(0,Z,'Src0',300_000_000),(86400,'Src0','SinkA',100)],['sol','duck','evm']),
        ('empty_elig',[(0,Z,'Src0',100),(86400,'Src0','SinkA',1)],['sol','evm']),
        ('empty_elig_duck',[(0,'','EmptyHub',30_000_000_000)]+[(0,'EmptyHub',f'R{i}',30_000_000) for i in range(1000)],['duck']),
        ('mixed',mixed_edges(),['duck']),
        ('negative',mixed_edges()+[(701*86400,'NegIn','MixedHub',-100_000_000),(701*86400,'MixedHub','NegOut',-300_000_000),(701*86400,'MixedHub','ZeroOnly',0)],['duck']),
    ]:
        for kind,args in inputs(root,name,rows,kinds).items(): job(name+'_'+kind,kind,args)
    for kind,args in inputs(root,'large',expand(main_edges(),3000000),['evm']).items(): job('large_'+kind,kind,args)
    save(root/'jobs.json',jobs)
    files={str(p.relative_to(root)):digest(p) for p in root.rglob('*') if p.is_file() and p.name not in {'frozen.json','anchors.txt'}}
    save(root/'frozen.json',files)
    print('PREPARED',len(jobs),'jobs',root,flush=True)

def verify_frozen(root):
    for name,sha in json.loads((root/'frozen.json').read_text()).items(): assert digest(root/name)==sha,name
    if (root/'baseline_reports_frozen.json').exists():
        for name,sha in json.loads((root/'baseline_reports_frozen.json').read_text()).items(): assert digest(root/name)==sha,name

def run(root,stage):
    verify_frozen(root)
    script=root/'flow_baseline.py' if stage=='baseline' else REPO/'scripts/report/flow_anomaly_scan.py'
    env=os.environ.copy(); env['PYTHONPATH']=':'.join(str(REPO/'scripts'/x) for x in ['lib','solana','report']); env['PYTHONDONTWRITEBYTECODE']='1'
    results=[]
    for job in json.loads((root/'jobs.json').read_text()):
        name=job['name']; d=root/(stage+'_'+name); d.mkdir(exist_ok=True)
        cmd=[sys.executable,'-B',str(script)]+job['args']+['--out',str(d/'report.json')]
        start=time.monotonic(); peak=0; samples=0
        with (d/'stdout.txt').open('w') as out,(d/'stderr.txt').open('w') as err:
            p=subprocess.Popen(cmd,cwd=d,env=env,stdout=out,stderr=err)
            while True:
                disk=sum(x.stat().st_blocks*512 for x in (d/'.tmp').rglob('*') if x.is_file()) if (d/'.tmp').exists() else 0
                peak=max(peak,disk); samples+=1
                pid,status,usage=os.wait4(p.pid,os.WNOHANG)
                if pid:
                    p.returncode=os.waitstatus_to_exitcode(status); break
                time.sleep(.05)
        elapsed=time.monotonic()-start
        item={'name':name,'stage':stage,'seconds':elapsed,'peak_rss_bytes':usage.ru_maxrss,'temp_sampled_peak_allocated_bytes':peak,'sample_count':samples,'temp_sampling':'50ms Python stat st_blocks*512 sum of default cwd/.tmp; sampled lower bound','command':cmd,'exit':p.returncode}
        results.append(item); save(root/(stage+'_timing.json'),results)
        print(stage,name,'exit',p.returncode,'wall',round(elapsed,3),'RSS',usage.ru_maxrss,flush=True)
        assert p.returncode==0,(name,(d/'stdout.txt').read_text(),(d/'stderr.txt').read_text())
        raw=(d/'report.json').read_bytes(); report=json.loads(raw); report.pop('generated_at')
        (d/'canonical.json').write_bytes(re.sub(rb'^ \"generated_at\": \"[^\"]*\",\n',b'',raw,flags=re.M))
        if job['kind']=='evm':
            assert '区间互斥——VIEW 轻路径' in (d/'stdout.txt').read_text()
            assert 'edge_source_binding' not in report
        if name.startswith('main_') or name=='large_evm': check_main(root,job,report)
    print('STAGE PASS',stage,flush=True)

def check_main(root,job,r):
    mapping=json.loads((root/('large' if job['name']=='large_evm' else 'main')/'mapping.json').read_text())
    addr=lambda a:mapping[a] if job['kind']=='evm' else a
    modes=Counter(x['mode'] for x in r['sprays'])
    assert all(modes[x]>=2 for x in ['pulse','pulse_all','slow_spray']),modes
    assert len(r['sinks'])>=5
    sinks={s['addr']:s for s in r['sinks']}; sprays={s['addr']:s for s in r['sprays']}
    for j in range(2):
        assert sprays[addr('Refill'+str(j))]['best_window']['fresh_recipient_count']==0
        assert sprays[addr('Slow'+str(j))]['all_time']['recipient_count']==600
        assert len(sprays[addr('Slow'+str(j))]['recipients_top'])==500
    assert addr('MixedHub') in sinks and addr('MixedHub') in sprays
    assert sinks[addr('Sink2')]['all_time']['qualified_inflow_pct']>sinks[addr('Sink2')]['best_window']['inflow_pct']
    if 'entity' in job['name']:
        assert addr('Sink0') not in sinks and addr('Sink1') in sinks
    if 'exclude' in job['name']: assert addr('Sink3') not in sinks
    # Check the exact production sorting keys, not an arbitrary canonical sort.
    def unique(values): assert len(values)==len(set(values)),values
    unique([x['best_window']['inflow_pct'] for x in r['sinks']])
    unique([x['all_time']['outflow_pct'] for x in r['sprays']])
    for s in r['sinks']: unique([x['pct'] for x in s['sources']])
    expected=3000000 if job['name']=='large_evm' else 300000
    assert r['edges']==expected


def compare(root):
    verify_frozen(root)
    lines=[]
    for job in json.loads((root/'jobs.json').read_text()):
        name=job['name']; a=json.loads((root/('baseline_'+name)/'canonical.json').read_text()); b=json.loads((root/('new_'+name)/'canonical.json').read_text())
        if name.startswith('ties_') or name in ['mixed_duck','negative_duck']:
            compare_ties(root,job,a,b)
            verdict=('PASS tie groups and rank-500 boundary contract' if name.startswith('ties_') else 'PASS equal-key source groups')
        else:
            assert (root/('baseline_'+name)/'canonical.json').read_bytes()==(root/('new_'+name)/'canonical.json').read_bytes(),name
            verdict='PASS bytes after removing generated_at only (no array sorting)'
        if name in ['mixed_duck','negative_duck']:
            for r in [a,b]:
                s=next(s for s in r['sinks'] if s['addr']=='MixedHub'); p=next(s for s in r['sprays'] if s['addr']=='MixedHub')
                assert s['all_time']['net_inflow_pct']==(1.03 if name=='negative_duck' else 1.01)
                assert s['all_time']['qualified_inflow_pct']==3.0 and len(s['sources'])==5
                assert p['all_time']['recipient_count']==20 and 'ZeroOnly' not in p['recipients']
            verdict+='; MixedHub net/qualified/sources/positive recipients PASS'
        lines.append({'name':name,'verdict':verdict,'sinks':len(a['sinks']),'sprays':len(a['sprays']),'mode':dict(Counter(x['mode'] for x in a['sprays'])),'mode_hits':{m:sum(x['mode_hits'][m]['hit'] for x in a['sprays']) for m in ['pulse','pulse_all','slow_spray']}})
    save(root/'equivalence.json',lines); print(json.dumps(lines,ensure_ascii=False,indent=2))

def compare_ties(root,job,a,b):
    import copy
    a=copy.deepcopy(a); b=copy.deepcopy(b)
    rows=json.loads((root/'ties/rows.json').read_text()); mapping=json.loads((root/'ties/mapping.json').read_text())
    if job['kind']=='evm': rows=[(ts,mapping[f],mapping[t],v) for ts,f,t,v in rows]
    for field,key in [('sinks',lambda x:x['best_window']['inflow_pct']),('sprays',lambda x:x['all_time']['outflow_pct'])]:
        # Both orders must honor the production key; compare membership within each equal-key group.
        for r in [a,b]: assert [key(x) for x in r[field]]==sorted([key(x) for x in r[field]],reverse=True)
        assert Counter((key(x),x['id']) for x in a[field])==Counter((key(x),x['id']) for x in b[field])
        b_by={x['id']:x for x in b[field]}
        for x in a[field]:
            y=b_by[x['id']]
            if field=='sinks':
                for z in [x,y]:
                    s=z.pop('sources'); assert [v['pct'] for v in s]==sorted([v['pct'] for v in s],reverse=True)
                    z['_source_groups']={str(k):{v['addr']:v for v in s if v['pct']==k} for k in {v['pct'] for v in s}}
            elif 'recipients_top' in x:
                totals=Counter()
                for _,f,t,v in rows:
                    if f==x['addr'] and f!=t and t not in [Z,DEAD] and v>0: totals[t]+=v
                bound=sorted(totals.values(),reverse=True)[499]
                assert sum(v==bound for v in totals.values())>=30
                for z in [x,y]:
                    top=z.pop('recipients_top'); assert len(top)==len(set(top))==500
                    assert all(totals[t]>=bound for t in top)
                    assert {t for t,v in totals.items() if v>bound}<=set(top)
                    assert [totals[t] for t in top]==sorted([totals[t] for t in top],reverse=True)
            assert x==y,(job['name'],x,y)
        a.pop(field); b.pop(field)
    assert a==b

def probe(root,stage,name):
    """Separate untimed diagnostic execution of the same CLI via a transparent connection proxy."""
    import duckdb
    import runpy
    real_connect=duckdb.connect
    job=next(j for j in json.loads((root/'jobs.json').read_text()) if j['name']==name)
    script=root/'flow_baseline.py' if stage=='baseline' else REPO/'scripts/report/flow_anomaly_scan.py'
    d=root/(stage+'_probe_'+name); d.mkdir(exist_ok=True)
    records=[]; metrics={}; candidate_rows={}; pres={}
    def rows_hash(rows): return hashlib.sha256(json.dumps(sorted(rows),ensure_ascii=False).encode()).hexdigest()
    class Connection:
        def __init__(self,con): self.c=con; self.pending=None
        def execute(self,sql,params=None):
            compact=' '.join(sql.split()); upper=compact.upper(); diagnostic=None
            material=re.match(r'CREATE TEMP TABLE (presink|prespray|sink_edges|sink_net|spray_edges) AS',compact,re.I)
            candidate=(('FROM EFLOW' in upper and ('ORDER BY TS' in upper or 'LIMIT 500' in upper)) or ('FROM SINK_EDGES WHERE' in upper or 'FROM SPRAY_EDGES WHERE' in upper))
            prescreen=(('SELECT T FROM EFLOW' in upper or 'SELECT F FROM EFLOW' in upper) and 'HAVING SUM' in upper) or compact in ['SELECT addr FROM presink','SELECT addr FROM prespray']
            if material or candidate:
                plan=self.c.execute('EXPLAIN (FORMAT JSON) '+sql,params or []).fetchall()[0][1]
                diagnostic={'sql':compact,'params':params,'plan':json.loads(plan)}
                records.append(diagnostic)
            start=time.perf_counter(); self.c.execute(sql,params or []); duration=time.perf_counter()-start
            self.pending=None
            if material:
                table=material[1]; metrics[table]={'rows':self.c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],'seconds':duration}
                if table in ['sink_edges','spray_edges']:
                    col='t' if table=='sink_edges' else 'f'
                    assert self.c.execute("SELECT current_setting('preserve_insertion_order')").fetchone()[0] is True
                    bad=self.c.execute(f'SELECT COUNT(*) FROM (SELECT {col},ts,LAG({col}) OVER (ORDER BY rowid) prev,LAG(ts) OVER (ORDER BY rowid) pts FROM {table}) WHERE {col}<prev OR ({col}=prev AND ts<pts)').fetchone()[0]
                    metrics[table]['rowid_descents']=bad; assert bad==0
                # CTAS has no consumer fetch result in the scanner.
            elif candidate or prescreen:
                self.pending=(compact,params,candidate,prescreen,start,diagnostic)
            if compact.startswith('SET memory_limit='):
                metrics['resources']={'duckdb':duckdb.__version__,**{k:self.c.execute(f"SELECT current_setting('{k}')").fetchone()[0] for k in ['memory_limit','temp_directory','max_temp_directory_size']}}
            return self
        def fetchall(self):
            result=self.c.fetchall(); p=self.pending; self.pending=None
            if p:
                sql,params,cand,pre,start,diag=p
                if pre:
                    key='sink' if ('SELECT t FROM' in sql or 'presink' in sql) else 'spray'
                    pres[key]=sorted(x[0] for x in result)
                if cand:
                    phase='sink' if ('SELECT ts, f, amt' in sql) else ('top' if 'LIMIT 500' in sql else 'spray')
                    addr=params[0] if params else re.search(r"WHERE [tf] = '([^']*)'",sql)[1]
                    candidate_rows[phase+':'+addr]={'rows':len(result),'sha256_sorted':rows_hash(result),'seconds':time.perf_counter()-start}
                    if name=='empty_elig_duck_duck': candidate_rows[phase+':'+addr]['values']=result
                    # The query plan is kept for every query; analyze one per query family.
                    if not any('analyze' in x and x.get('family')==phase for x in records):
                        diag['family']=phase
                        diag['analyze']=json.loads(self.c.execute('EXPLAIN (ANALYZE, FORMAT JSON) '+sql,params or []).fetchall()[0][1])
            return result
        def fetchone(self): return self.c.fetchone()
        def executemany(self,*args): self.c.executemany(*args); return self
        def __getattr__(self,key): return getattr(self.c,key)
    duckdb.connect=lambda *a,**kw:Connection(real_connect(*a,**kw))
    sys.path[:0]=[str(script.parent)]+[str(REPO/'scripts'/x) for x in ['lib','solana','report']]
    sys.argv=[str(script)]+job['args']+['--out',str(d/'report.json')]
    previous=Path.cwd(); os.chdir(d)
    try:
        try: runpy.run_path(str(script),run_name='__main__')
        except SystemExit as e: assert not e.code,e.code
    finally:
        os.chdir(previous); duckdb.connect=real_connect
    save(d/'probe.json',{'metrics':metrics,'prescreen':pres,'candidate_rows':candidate_rows,'queries':records})
    print('PROBE PASS',stage,name,flush=True)


def audit_probes(root):
    def nodes(tree):
        if isinstance(tree,list):
            for v in tree: yield from nodes(v)
        elif isinstance(tree,dict):
            yield tree
            for v in tree.get('children',[]): yield from nodes(v)
    results=[]
    for name in ['main_evm','large_evm','ties_duck','empty_elig_duck_duck','empty_candidates_duck','negative_duck']:
        a=json.loads((root/('baseline_probe_'+name)/'probe.json').read_text())
        b=json.loads((root/('new_probe_'+name)/'probe.json').read_text())
        assert a['prescreen']==b['prescreen'],name
        assert a['candidate_rows'].keys()==b['candidate_rows'].keys(),name
        for k,x in a['candidate_rows'].items():
            y=b['candidate_rows'][k]
            if k.startswith('top:') and name=='ties_duck': continue # verified against boundary universe by compare_ties
            assert (x['rows'],x['sha256_sorted'])==(y['rows'],y['sha256_sorted']),(name,k)
        if name=='empty_elig_duck_duck':
            assert a['prescreen']['sink']==['EmptyHub']
            assert a['candidate_rows']['sink:EmptyHub']['values']==[[0,'',30000000000]]
        if name=='empty_candidates_duck': assert a['prescreen']=={'sink':[],'spray':[]}
        summary={'name':name,'prescreen_count':{k:len(v) for k,v in b['prescreen'].items()},'metrics':b['metrics'],'ctas':[],'points':[]}
        mats=[q for q in b['queries'] if q['sql'].startswith('CREATE TEMP TABLE')]
        assert len(mats)==5
        for q in mats:
            ns=list(nodes(q['plan'])); labels=[n.get('name','') for n in ns]
            assert not any('DELIM' in n for n in labels),(name,q['sql'],labels)
            scans=[n for n in ns if n.get('name','').strip() in ['READ_PARQUET','READ_PARQUET ','PARQUET_SCAN'] or n.get('extra_info',{}).get('Function')=='READ_PARQUET']
            source_tables=[n for n in ns if n.get('extra_info',{}).get('Table','').endswith('.edges') or n.get('extra_info',{}).get('Table')=='edges']
            # EVM eflow expands to exactly one logs reader and one blocks reader.
            if name.endswith('evm'): assert len(scans)==2,(name,q['sql'],scans)
            else: assert len(source_tables)==1,(name,q['sql'],source_tables)
            summary['ctas'].append({'table':q['sql'].split()[3],'parquet_readers':len(scans),'edge_table_scans':len(source_tables),'operators':labels})
        for q in b['queries']:
            if q['sql'].startswith('CREATE TEMP TABLE'): continue
            ns=list(nodes(q['plan']))
            assert all('PARQUET' not in n.get('name','') for n in ns)
            tables=[n.get('extra_info',{}).get('Table') for n in ns if 'Table' in n.get('extra_info',{})]
            assert tables and all(t.split('.')[-1] in ['sink_edges','spray_edges'] for t in tables),tables
            if 'analyze' in q:
                stats=[{k:n.get(k) for k in ['operator_name','operator_rows_scanned','operator_cardinality','extra_info']} for n in nodes(q['analyze']) if n.get('operator_type')=='TABLE_SCAN']
                summary['points'].append({'family':q['family'],'tables':tables,'scan_statistics':stats})
        for stage,probe_data in [('baseline',a),('new',b)]:
            for family in ['sink','spray','top']:
                values=[v['seconds'] for k,v in probe_data['candidate_rows'].items() if k.startswith(family+':')]
                summary[f'{stage}_{family}_mean_seconds']=sum(values)/len(values) if values else None
        results.append(summary)
    save(root/'probe_audit.json',results)
    print('PROBE AUDIT PASS',len(results),'fixtures')

def verify_evm(root):
    import duckdb
    sys.path[:0]=[str(REPO/'scripts'/x) for x in ['report','lib','solana']]
    from wave_scan import load_evm_v2
    rows=json.loads((root/'main/rows.json').read_text()); mapping=json.loads((root/'main/mapping.json').read_text())
    expected=Counter((ts,mapping[f],mapping[t],v) for ts,f,t,v in rows)
    con=duckdb.connect(); load_evm_v2(con,str(root/'main/evm'))
    actual=Counter(con.execute('SELECT ts,f,t,amt FROM edges').fetchall())
    assert actual==expected
    assert len({a for _,f,t,_ in rows for a in [f,t]})>=3000
    assert max(ts for ts,_,_,_ in rows)-min(ts for ts,_,_,_ in rows)>=400*86400
    for who in ['Slow0','Slow1']:
        totals=Counter()
        for _,f,t,v in rows:
            if f==who: totals[t]+=v
        assert len(totals)==len(set(totals.values()))==600
    summary={'rows':len(rows),'addresses':len({a for _,f,t,_ in rows for a in [f,t]}),'span_days':(max(x[0] for x in rows)-min(x[0] for x in rows))//86400,'sum_raw':sum(x[3] for x in rows),'decoded_exact_multiset':'PASS','recipient_cumulative_amounts_unique':'PASS'}
    save(root/'evm_decode.json',summary); print('EVM DECODE PASS',summary)


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['prepare','run','compare','probe','audit','decode']); ap.add_argument('root',type=Path); ap.add_argument('stage',nargs='?'); ap.add_argument('name',nargs='?'); args=ap.parse_args()
    root=args.root.resolve()
    if args.action=='prepare': prepare(root)
    elif args.action=='run': run(root,args.stage)
    elif args.action=='probe': probe(root,args.stage,args.name)
    elif args.action=='audit': audit_probes(root)
    elif args.action=='decode': verify_evm(root)
    else: compare(root)
