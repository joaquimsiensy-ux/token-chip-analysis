#!/usr/bin/env python3
"""W1 offline evidence generator; all generated data stays in resolved tempfile paths.
Reproduce: python3 -B W1_fixture_tools.py baseline|candidate|edges|wide ROOT
ROOT contains scripts/evm/replay_duck.py copied with git show 8457f70:...
"""
import collections, hashlib, importlib.util, json, os, re, runpy, shlex
import shutil, subprocess, sys, time
from pathlib import Path
import duckdb

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EVM = REPO / 'scripts/evm'
sys.path[:0] = [str(EVM), str(REPO / 'scripts/lib'), str(REPO / 'scripts/tests')]
Z = '0x' + '0' * 40
DEAD = '0x' + '0' * 36 + 'dead'
A = lambda i: f'0x{i:040x}'
TOKEN = A(161)
FILES = ('peaks.json', 'balances_final.json', 'mint_ledger.json', 'replay_stats.json')
SEED = 20260925


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def write(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=1))


def read(p):
    return json.loads(Path(p).read_text())


def size(p):
    return sum(f.stat().st_size for f in Path(p).rglob('*') if f.is_file()) if Path(p).exists() else 0


def record(name, text):
    with (HERE / name).open('a') as f:
        f.write(text + '\n')
    print(text, flush=True)


def eq(text):
    record('W1_equivalence.txt', text)


def timing(text):
    record('W1_timing.txt', text)


def connect():
    con = duckdb.connect()
    con.execute("SET memory_limit='2GB'")
    con.execute('SET threads=2')
    return con


def metadata(con, p, col):
    n, lo, hi = con.execute(f'SELECT count(*), min({col}), max({col}) FROM read_parquet(?)', [str(p)]).fetchone()
    return dict(size=p.stat().st_size, rows=n, min_block=lo, max_block=hi, sha256=sha(p))


def emit(con, root, bounds, formats=('v1csv', 'v2'), split=None):
    """raw columns: b, ts, tx, li, frm, t2, v; receipts issued after all mutations."""
    from evm_channel_fixture import write_csv_channel_receipt
    from make_channel_receipt import make_receipt
    from channels_preflight import preflight_channels
    root.mkdir(parents=True, exist_ok=True)
    lo, hi = bounds
    manifests = {}
    for fmt in formats:
        if fmt == 'v1csv':
            data = root / 'transfers.csv'
            con.execute(f'''COPY (SELECT b AS block, ts, tx, frm AS "from", t2 AS "to", v AS value,
                tx || ':log:' || li AS uniqueId FROM raw) TO '{data}' (HEADER, FORMAT CSV)''')
            receipt = Path(write_csv_channel_receipt(root, 't', data, TOKEN, lo, hi))
        else:
            from fetch_hypersync_v2 import MANIFEST_SCHEMA, QUERY_SCHEMA, SCRIPT_PATH, ensure_outdir_identity
            data = root / 'v2'
            url = 'https://fixture.hypersync.xyz'
            ensure_outdir_identity(data, TOKEN, url)
            cuts = [lo, split, hi] if split is not None else [lo, hi]
            for i, (start, end) in enumerate(zip(cuts, cuts[1:])):
                d = data / f'run_{i}'
                d.mkdir()
                con.execute(f'''COPY (SELECT b AS block_number, '0x'||lpad(hex(b),64,'0') AS block_hash,
                    li AS log_index, tx AS transaction_hash, '0x'||repeat('0',24)||substr(frm,3) AS topic1,
                    '0x'||repeat('0',24)||substr(t2,3) AS topic2,
                    '0x'||lpad(hex(v::HUGEINT),64,'0') AS data FROM raw WHERE b >= {start} AND b < {end})
                    TO '{d / 'logs.parquet'}' (FORMAT parquet)''')
                con.execute(f'''COPY (SELECT b AS number, epoch(ANY_VALUE(ts)::TIMESTAMP)::BIGINT AS timestamp
                    FROM raw WHERE b >= {start} AND b < {end} GROUP BY b)
                    TO '{d / 'blocks.parquet'}' (FORMAT parquet)''')
                write(d / 'done.json', dict(schema=MANIFEST_SCHEMA, query_schema=QUERY_SCHEMA,
                    capture_from=lo, from_block=start, to_block=end, next_block=end, token=TOKEN, url=url,
                    files={'logs.parquet': metadata(con, d/'logs.parquet', 'block_number'),
                           'blocks.parquet': metadata(con, d/'blocks.parquet', 'number')},
                    collector={'path': SCRIPT_PATH, 'sha256': sha(EVM/'fetch_hypersync_v2.py')}))
            receipt = root / 'v2.receipt.json'
            write(receipt, make_receipt(data, fmt, TOKEN, lo, hi, 't'))
        manifest = root / f'channels_{fmt}.json'
        write(manifest, dict(schema='evm-channels/v2', token=TOKEN, expected_from=lo, expected_to=hi,
            channels=[dict(path=str(data), lo=lo, hi=hi, tag='t', format=fmt, receipt=str(receipt))]))
        preflight_channels(manifest, root/f'preflight_{fmt}')
        manifests[fmt] = manifest
    return manifests


def needs(root, wanted=None):
    wanted = wanted or ([A(i) for i in range(1000, 2050)] + [A(90000), A(90001), A(90002), Z, DEAD])
    n, t = root/'needs.json', root/'trigger_days.json'
    write(n, {'0.0100': wanted[:800]})
    write(t, {'days': {'2026-01-01': {'active_candidates': wanted[700:]}}})
    return [n, t], set(wanted)


def generate(root):
    started = time.monotonic()
    assert shutil.disk_usage(root).free >= 20 * 1024**3
    con = connect()
    con.execute(f"SET temp_directory='{root / 'generation_tmp'}'")
    # Fixed deterministic integer arithmetic, with seed used for address rotation.
    con.execute(f'''CREATE TABLE canonical AS
        SELECT (100 + (i//4)*4)::BIGINT b, '2026-01-01T12:00:00'::VARCHAR ts,
          '0x'||lpad(hex(i),64,'0') tx, i::BIGINT li,
          CASE WHEN i=0 OR i%101=0 THEN '{Z}' WHEN i=2 THEN '{A(90001)}'
               ELSE '0x'||lpad(hex(1000+(i+{SEED})%6000),40,'0') END frm,
          CASE WHEN i=1 THEN '{A(90002)}' WHEN i%107=0 THEN '{Z}' WHEN i%109=0 THEN '{DEAD}'
               ELSE '0x'||lpad(hex(1000+(i+{SEED}+1)%6000),40,'0') END t2,
          CASE WHEN i=0 THEN '1000000000000000000000000000000' WHEN i=1 THEN '1'
               ELSE ((i%97)+1)::VARCHAR END v
        FROM range(1999000) x(i)''')
    con.execute('CREATE TABLE raw AS SELECT * FROM canonical UNION ALL SELECT * FROM canonical WHERE li<1000')
    counts = con.execute('SELECT count(*), count(DISTINCT (tx,li)), max(length(v)) FROM raw').fetchone()
    assert counts == (2000000, 1999000, 31), counts
    manifests = emit(con, root/'main', (100, 2000100), split=1000100)
    paths, wanted = needs(root/'main')
    addresses = con.execute('SELECT count(*) FROM (SELECT frm FROM raw UNION SELECT t2 FROM raw)').fetchone()[0]
    assert addresses >= 5000 and len(wanted) >= 1000
    write(root/'fixture.json', dict(seed=SEED, raw_rows=counts[0], unique_rows=counts[1],
        addresses=addresses, union=len(wanted), manifests={k:str(v) for k,v in manifests.items()}))
    con.close()
    timing(f'GENERATE seed={SEED} rows={counts} addresses={addresses} union={len(wanted)} wall={time.monotonic()-started:.3f}s '
           f'input_bytes={size(root/"main")} generation_scratch_peak=NOT_SAMPLED (not claimed zero) '
           f'free_bytes={shutil.disk_usage(root).free}; timeout budget=600s')
    assert time.monotonic()-started < 600
    eq('PASS main fixture: 2,000,000 retained raw rows / 1,999,000 normalized keys / 1,000 copies; '
       'v1csv and two-run v2 derived from same canonical set; both preflight PASS; '+str(read(root/'fixture.json')))


def wrapped(script, args):
    """Same instrumentation on baseline/candidate; no source result caching or rewriting."""
    orig = duckdb.connect
    trace = Path(os.environ['W1_TRACE'])
    class Connection:
        def __init__(self, c):
            self.c, self.active = c, False
        def __getattr__(self, k):
            return getattr(self.c, k)
        def execute(self, sql, *a, **kw):
            s = str(sql).strip()
            if self.active:
                with trace.open('a') as f:
                    f.write('SQL '+s+'\n')
                    if 'hash(tag, tx, li)' in s and ('WITH g AS' in s or 'INSERT INTO ab_raw' in s):
                        # EXPLAIN is planning only; no source execution.
                        if not hasattr(self, 'explained_'+('g' if 'WITH g AS' in s else 'd')):
                            f.write('EXPLAIN\n'+self.c.execute('EXPLAIN '+s).fetchone()[1]+'\n')
                            setattr(self, 'explained_'+('g' if 'WITH g AS' in s else 'd'), True)
            if os.environ.get('W1_FORCE_WINDOW_ERROR') == '1' and s.startswith('CREATE TABLE peaks AS'):
                raise duckdb.NotImplementedException('W1 injected VARINT window failure')
            result = self.c.execute(sql, *a, **kw)
            if 'SET preserve_insertion_order=false' == s:
                self.active = True
                settings = self.c.execute("SELECT current_setting('memory_limit'), current_setting('threads'), "
                    "current_setting('temp_directory'), current_setting('max_temp_directory_size')").fetchone()
                print('[W1 settings]',duckdb.__version__,settings,flush=True)
            if self.active and ('CREATE VIEW raw_rows' in s or 'INSERT INTO ab_raw' in s or 'DROP TABLE ab_raw' in s):
                tables = self.c.execute('SELECT table_name FROM duckdb_tables() WHERE NOT internal ORDER BY 1').fetchall()
                views = self.c.execute('SELECT view_name FROM duckdb_views() WHERE NOT internal ORDER BY 1').fetchall()
                with trace.open('a') as f:
                    f.write('CATALOG '+json.dumps(dict(tables=tables, views=views))+'\n')
                assert ('events',) not in tables and ('raw_rows',) not in tables, tables
                assert ('raw_rows',) in views, views
            return result
    duckdb.connect = lambda *a, **kw: Connection(orig(*a, **kw))
    sys.argv = [str(script)] + args
    try:
        runpy.run_path(str(script), run_name='__main__')
    except SystemExit as e:
        print('[W1 engine rc]', e.code if isinstance(e.code, int) else 1, flush=True)
        raise
    finally:
        import resource
        print('[W1 getrusage RSS bytes]', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, flush=True)


def run(root, label, script, manifest, out, only=None, seg=None, extra=(), timeout=900):
    assert shutil.disk_usage(root).free >= 20*1024**3
    logs = root/'logs'; logs.mkdir(exist_ok=True)
    trace, stdout, stderr = [logs/(label+s) for s in ('.sql', '.stdout', '.stderr')]
    trace.write_text('')
    args = ['--channels',str(manifest),'--out-dir',str(out),'--mem-limit','2GB','--threads','2']
    if not extra:
        args += ['--no-merged']
    args += list(extra)
    for p in only or []:
        args += ['--only-addrs', str(p)]
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONPATH':os.pathsep.join([str(EVM),str(REPO/'scripts/lib')]),
           'W1_TRACE':str(trace)}
    env.pop('CHIP_REPLAY_SEG_ROWS', None)
    if seg is not None:
        env['CHIP_REPLAY_SEG_ROWS']=str(seg)
    cmd = ['/usr/bin/time','-l',sys.executable,'-B',str(Path(__file__).resolve()),'wrapped',str(script),*args]
    start = time.monotonic(); peak = 0; samples = 0
    with stdout.open('w') as so, stderr.open('w') as se:
        p = subprocess.Popen(cmd, stdout=so, stderr=se, env=env, cwd=root)
        while p.poll() is None:
            peak = max(peak, size(out/'.duck_tmp')); samples += 1
            if time.monotonic()-start > timeout:
                p.kill(); p.wait(); raise TimeoutError(label)
            time.sleep(1)
    wall = time.monotonic()-start
    so, se = stdout.read_text(), stderr.read_text()
    rss = re.search(r'(\d+)\s+maximum resident set size',se)
    fallback = re.search(r'\[W1 getrusage RSS bytes\] (\d+)',so)
    engine_rc = re.search(r'\[W1 engine rc\] (\d+)',so)
    actual_rc = int(engine_rc[1]) if engine_rc else p.returncode
    result = dict(label=label,rc=actual_rc,launcher_rc=p.returncode,wall=wall,rss_bytes=int(rss[1]) if rss else None,
                  getrusage_rss_bytes=int(fallback[1]) if fallback else None,
                  tmp_sample_peak_bytes=peak,samples=samples,output_bytes=size(out),timeout=timeout,
                  cmd=shlex.join(cmd),seg=seg)
    write(logs/(label+'.json'),result)
    timing(json.dumps(result,ensure_ascii=False)+'\n'+so+'\n'+se)
    eq(f'RUN {label}: command={result["cmd"]}; CHIP_REPLAY_SEG_ROWS={seg!r}; engine_rc={actual_rc}; launcher_rc={p.returncode}; timeout={timeout}s')
    return result, so, se


def verify_receipt(p, script, manifest, paths):
    r=read(p)
    assert r['producer']==dict(path='replay_duck.py',sha256=sha(script)),r
    assert r['channels']==dict(path=manifest.name,sha256=sha(manifest)),r
    assert r['inputs']==[dict(path=x.name,sha256=sha(x)) for x in paths],r
    assert r['count']==len(r['addresses']),r
    return r


def baseline(root):
    if not (root/'fixture.json').exists():
        generate(root)
    script=root/'scripts/evm/replay_duck.py'
    paths,wanted=needs(root/'main')
    for fmt, manifest in read(root/'fixture.json')['manifests'].items():
        manifest=Path(manifest); out=root/f'baseline_full_{fmt}'
        r,so,se=run(root,'baseline_full_'+fmt,script,manifest,out)
        assert r['rc'] in (0,4),so+se
        frozen={n:(out/n).read_bytes() for n in FILES}
        r,so,se=run(root,'baseline_only_'+fmt,script,manifest,out,paths)
        assert r['rc']==0,so+se
        receipt=root/'main/block_precision_followup.json'
        fu=verify_receipt(receipt,script,manifest,paths)
        assert set(fu['addresses'])==wanted
        assert fu['addresses'][A(90000)]==fu['addresses'][A(90001)]==dict(peak='0',peak_blk=None)
        assert fu['addresses'][A(90002)]==dict(peak='1',peak_blk=100)
        peaks=read(out/'peaks.json'); assert A(90002) not in peaks
        for a in wanted & peaks.keys():
            assert fu['addresses'][a]=={k:peaks[a][k] for k in ('peak','peak_blk')}
        (root/f'baseline_only_{fmt}.json').write_bytes(receipt.read_bytes())
        assert all((out/n).read_bytes()==v for n,v in frozen.items())
        eq(f'PASS baseline frozen {fmt}: rows=2000000 K=global union={len(wanted)} sha={sha(script)} '
           'receipt binding, no-event/from-only zero, low peak=1, full overlapping peaks and untouched full files')


def verify_stats(out,script):
    from channels_preflight import replay_provenance
    s=read(out/'replay_stats.json'); p=replay_provenance(out,script)
    assert all(s[k]==v for k,v in p.items()),(s,p)
    return s


def candidate(root):
    script=EVM/'replay_duck.py'; paths,wanted=needs(root/'main')
    for fmt,manifest in read(root/'fixture.json')['manifests'].items():
        manifest=Path(manifest); out=root/f'candidate_full_{fmt}'; old=root/f'baseline_full_{fmt}'
        r,so,se=run(root,'candidate_full_'+fmt,script,manifest,out)
        assert r['rc'] in (0,4),so+se
        for n in FILES[:3]:
            assert read(out/n)==read(old/n),n
        a=verify_stats(old,root/'scripts/evm/replay_duck.py'); b=verify_stats(out,script)
        for k in a.keys()|b.keys():
            if a.get(k)==b.get(k): continue
            assert k in ('producer','outputs'),(k,a.get(k),b.get(k))
            eq(f'ALLOWED {fmt} stats.{k}: {a[k]} -> {b[k]}; '+
               ('true script SHA change' if k=='producer' else 'balances_final parsed business keys equal; JSON key order only'))
        frozen={n:(out/n).read_bytes() for n in FILES}
        for seg in (250000,None):
            label=f'candidate_only_{fmt}_{seg or "default"}'
            r,so,se=run(root,label,script,manifest,out,paths,seg)
            assert r['rc']==0,so+se
            fu=verify_receipt(root/'main/block_precision_followup.json',script,manifest,paths)
            assert fu['addresses']==read(root/f'baseline_only_{fmt}.json')['addresses']
            k=8 if seg else 1
            buckets=re.findall(r'\[only-addrs\] 桶 (\d+)/(\d+) 行 (\d+)',so)
            assert len(buckets)==k and {int(x[1]) for x in buckets}=={k},so
            counts=[int(x[2]) for x in buckets]; assert sum(counts)==2000000
            assert all((out/n).read_bytes()==v for n,v in frozen.items())
            trace=(root/'logs'/f'{label}.sql').read_text()
            assert 'CREATE TABLE raw_rows' not in trace and 'CREATE TABLE events' not in trace
            assert trace.count('SQL ')>2*k and trace.count('SQL INSERT INTO ab_raw')==k
            assert ('READ_PARQUET' if fmt=='v2' else 'READ_CSV') in trace
            eq(f'PASS {label}: rows=2000000 K={k} union={len(wanted)} buckets={counts} max={max(counts)}; '
               'all baseline address keys/values equal, full four files unchanged, real producer/input binding verified')
            timing(f'PATH {label}: {2*k} bucket source queries ({k} combined counts/conflict + {k} filtered aggregation); '
                   'plus retained COUNT=1 reject=1 maxlen=1, v2 probe=1 for v2 only; preflight summary/digests additional; '
                   'EXPLAIN does not execute sources. Query count is not file byte-read multiplier.\n'+trace)
        eq(f'PASS full {fmt}: three JSON business maps equal; all stats fields compared; '
           'producer/preflight/inputs/outputs independently revalidated against real files')


def small_raw(rows):
    con=connect()
    con.execute('CREATE TABLE raw(b BIGINT, ts VARCHAR, tx VARCHAR, li BIGINT, frm VARCHAR, t2 VARCHAR, v VARCHAR)')
    if rows:
        con.executemany('INSERT INTO raw VALUES (?,?,?,?,?,?,?)',rows)
    return con


def row(i, b=100, frm=Z, to=None, v='10'):
    return (b,'2026-01-01T12:00:00',f'0x{i:064x}',i,frm,to or A(1000),v)


def expected(rows, wanted):
    unique={}
    for b,ts,tx,li,frm,to,v in rows:
        if v is None: continue
        unique[tx.lower(),li]=(b,frm.lower(),to.lower(),int(v))
    d=collections.defaultdict(int)
    for b,frm,to,v in unique.values():
        d[to,b]+=v
        if frm!=Z: d[frm,b]-=v
    answer={}
    for a in wanted:
        bal=peak=0; pb=None
        for b in sorted(b for aa,b in d if aa==a):
            bal+=d[a,b]
            if bal>peak: peak,pb=bal,b
        answer[a]=dict(peak=str(peak),peak_blk=pb)
    return answer


def edges(root):
    old=root/'scripts/evm/replay_duck.py'; new=EVM/'replay_duck.py'
    wanted=[A(1000),A(1001),A(90000),Z,DEAD]
    cases={
        '37digits':([row(0,v=str(10**36))], 'HUGEINT', (), 1),
        '38digits':([row(0,v=str(10**37))], 'VARINT', (), 1),
        'force_varint':([row(0),row(1,b=101,frm=A(1000),to=A(1001),v='3')], 'VARINT', ('--force-varint',), 1),
        'first_peak':([row(0),row(1,b=101,frm=A(1000),to=A(1001),v='5'),row(2,b=102,v='5')], 'HUGEINT', (), 1),
        'zero_delta':([row(0,frm=A(1000),v='0'),row(1,frm=A(1000),v='10')], 'HUGEINT', (), 1),
        'zero_retained':([], 'HUGEINT', (), 1),
        'null_value':([row(0,v=None),row(1)], 'HUGEINT', (), 1),
        'skew_empty':([row(0)]*9, 'HUGEINT', (), 1),
    }
    for name,(rows,vt,extra,seg) in cases.items():
        case=root/('edge_'+name); case.mkdir()
        con=small_raw(rows)
        manifests=emit(con,case,(100,110),formats=('v1csv',) if name=='null_value' else ('v1csv','v2'))
        con.close(); paths,ws=needs(case,wanted)
        for fmt,m in manifests.items():
            baseline_fu=None
            for version,script in [('old',old),('new',new)]:
                label=f'{name}_{fmt}_{version}'
                r,so,se=run(root,label,script,m,case/(fmt+version),paths,seg,extra,timeout=120)
                assert r['rc']==0,so+se
                fu=verify_receipt(case/'block_precision_followup.json',script,m,paths)
                assert fu['value_type']==vt,(name,fu)
                assert fu['addresses']==expected(rows,ws),(name,fu,expected(rows,ws))
                if version=='old': baseline_fu=fu
                else:
                    assert fu['addresses']==baseline_fu['addresses']
                    buckets=re.findall(r'\[only-addrs\] 桶 (\d+)/(\d+) 行 (\d+)',so)
                    kept=sum(x[-1] is not None for x in rows)
                    assert sum(int(x[2]) for x in buckets)==kept
                    if name=='skew_empty':
                        assert '[only-addrs][警告] 桶偏斜' in so and any(x[2]=='0' for x in buckets),so
                    eq(f'PASS edge {label}: retained={kept} K={max(1,kept)} union={len(ws)} value_type={vt} '
                       'baseline and independent Python block-end peaks equal; first-peak/zero/skew assertions as applicable')
            if name=='null_value':
                for version,script in [('old',old),('new',new)]:
                    r,so,se=run(root,f'null_full_{version}',script,m,case/('full_'+version),timeout=120)
                    assert r['rc']==0,so+se
                a=read(case/'full_old/replay_stats.json'); b=read(case/'full_new/replay_stats.json')
                for k in ('n_source_rows','n_bad_fields','n_out_of_segment','n_dedup_removed'):
                    assert a[k]==b[k],(k,a,b)
                eq('PASS NULL source value: baseline full/new full reject counts '+str({k:a[k] for k in a if k.startswith('n_')})+
                   '; new only kept=1, no additional rejection, address peaks equal baseline full present keys')
    conflicts(root,old,new,wanted)
    merged(root,old,new)


def conflicts(root,old,new,wanted):
    # Six independent variants; complete-key collisions remain within one hash bucket.
    h=connect()
    for variant in ('value','cross_block','endpoints','unselected','first_bucket','last_bucket'):
        key=10
        if variant in ('first_bucket','last_bucket'):
            target=0 if variant=='first_bucket' else 3
            key=h.execute("SELECT i FROM range(10000) r(i) WHERE hash('t', '0x'||lpad(lower(hex(i)),64,'0'), i::BIGINT)%4=? LIMIT 1",[target]).fetchone()[0]
        original=row(key,frm=A(2000) if variant=='unselected' else Z,to=A(2001) if variant=='unselected' else A(1000))
        mutated=list(original)
        if variant=='cross_block': mutated[0]=101
        elif variant=='endpoints': mutated[4:6]=[A(2000),A(2001)]
        else: mutated[-1]='11'
        rows=[original,tuple(mutated)]
        rows.extend(row(key+100+j,frm=A(1000),to=DEAD,v='0') for j in range(2))
        case=root/('conflict_'+variant); case.mkdir(); c=small_raw(rows)
        manifests=emit(c,case,(100,110),split=101 if variant=='cross_block' else None); c.close()
        paths,ws=needs(case,wanted)
        bucket=h.execute("SELECT hash('t',?,?::BIGINT)%4",[original[2],original[3]]).fetchone()[0]
        for fmt,m in manifests.items():
            receipt=case/'block_precision_followup.json'
            # First run proves no new receipt. Sentinel proves old receipt byte preservation.
            for version,script,only in [('old_full',old,None),('new_full',new,None),('new_only',new,paths)]:
                r,so,se=run(root,f'conflict_{variant}_{fmt}_{version}',script,m,case/(fmt+version),only,1,timeout=120)
                assert r['rc']!=0 and '去重键对应多个不同事件内容' in se,so+se
                assert not receipt.exists(),receipt
            sentinel=b'W1 previous receipt: exact bytes\n'; receipt.write_bytes(sentinel)
            r,so,se=run(root,f'conflict_{variant}_{fmt}_old_receipt',new,m,case/(fmt+'preserve'),paths,1,timeout=120)
            assert r['rc']!=0 and '去重键对应多个不同事件内容' in se,so+se
            assert receipt.read_bytes()==sentinel
            # Single exact file deletion, permitted; never directory/batch deletion.
            receipt.unlink()
            eq(f'PASS conflict {variant}/{fmt}: retained=4 K=4 key_bucket={bucket} union={len(ws)}; '
               'preflight passed, old full/new full/new only reject at conflict check; no new receipt; old bytes preserved')
    h.close()
    # Empty union and all invalid environment values, both formats, independent output dirs.
    for fmt in ('v1csv','v2'):
        case=root/('edge_inputs_'+fmt); case.mkdir(); c=small_raw([row(0)])
        m=emit(c,case,(100,110),formats=(fmt,))[fmt]; c.close()
        paths,ws=needs(case,wanted)
        for value in ('0','-1','abc',''):
            r,so,se=run(root,f'invalid_{fmt}_{value or "empty"}',new,m,case/('bad_'+(value or 'empty')),paths,value,timeout=120)
            assert r['rc']==2 and 'CHIP_REPLAY_SEG_ROWS' in se,so+se
            assert not (case/'block_precision_followup.json').exists()
            r,so,se=run(root,f'invalid_full_{fmt}_{value or "empty"}',new,m,case/('full_'+(value or 'empty')),seg=value,timeout=120)
            assert r['rc']==0,so+se
        empty=case/'empty.json'; write(empty,[])
        r,so,se=run(root,f'empty_union_{fmt}',new,m,case/'empty_out',[empty],1,timeout=120)
        assert r['rc']==2 and '[only-addrs]' in se
        assert not (case/'block_precision_followup.json').exists()
        eq(f'PASS {fmt}: retained=1 K=1 union=0 rejects; env 0/-1/abc/empty rejected rc2 before preflight, full unaffected rc0')


def merged(root,old,new):
    case=root/'merged'; case.mkdir()
    rows=[row(0,v='100000'),row(1,frm=A(1000),to=A(1001),v='10'),row(2,b=101,frm=A(1001),to=DEAD,v='5')]
    c=small_raw(rows); m=emit(c,case,(100,110),formats=('v1csv',))['v1csv']; c.close()
    camps=case/'camps.json'; write(camps,dict(camps={'A':[A(1000)],'B':[A(1001)],'销毁':[DEAD]},entities={'X':[A(1000)]}))
    for version,script in [('old',old),('new',new)]:
        r,so,se=run(root,'merged_'+version,script,m,case/version,extra=['--emit-csv','--merged-parquet','--camps',str(camps)],timeout=120)
        assert r['rc']==0,so+se
        verify_stats(case/version,script)
    for n in (*FILES[:3],'camp_series.json','entity_series.json'):
        assert read(case/'old'/n)==read(case/'new'/n),n
    assert (case/'old/merged.csv').read_bytes()==(case/'new/merged.csv').read_bytes()
    c=connect()
    oldrows=c.execute('SELECT * FROM read_parquet(?) ORDER BY ALL',[str(case/'old/merged.parquet')]).fetchall()
    newrows=c.execute('SELECT * FROM read_parquet(?) ORDER BY ALL',[str(case/'new/merged.parquet')]).fetchall()
    assert oldrows==newrows; c.close()
    a=read(case/'old/replay_stats.json'); b=read(case/'new/replay_stats.json')
    assert {k:v for k,v in a.items() if k not in ('producer','outputs')}=={k:v for k,v in b.items() if k not in ('producer','outputs')}
    eq('PASS merged/pass2: rows=3 K=full union=N/A CSV byte equal, parquet rows equal, five business JSON equal; '
       'stats fields equal except independently verified producer/output digests')


def wide(root):
    """Default target-scale evidence, isolated source-only bounded group-by workload."""
    # This mode is executed under /usr/bin/time -l by the caller; RUSAGE fallback below.
    import resource
    p=root/'wide'; p.mkdir(exist_ok=True)
    con=connect(); con.execute(f"SET temp_directory='{p/'duck_tmp'}'")
    con.execute("SET max_temp_directory_size='20GB'"); con.execute('SET preserve_insertion_order=false')
    t=time.monotonic()
    con.execute(f'''COPY (SELECT 't' tag, '0x'||lpad(hex(i),64,'0') tx, i::BIGINT li,
       (100+i//4)::BIGINT b, '2026-01-01T12:00:00'::VARCHAR ts,
       '0x'||lpad(hex(i%6000),40,'0') frm, '0x'||lpad(hex((i+1)%6000),40,'0') t2,
       lpad((i+1)::VARCHAR,37,'0') v FROM range(4999000) r(i))
       TO '{p/'wide.parquet'}' (FORMAT parquet)''')
    con.execute(f"CREATE VIEW raw_rows AS SELECT * FROM read_parquet('{p/'wide.parquet'}')")
    query='''WITH g AS (SELECT tag,tx,li,count(*) n,count(DISTINCT (b,ts,frm,t2,v)) variants
      FROM raw_rows WHERE hash(tag,tx,li)%1=0 GROUP BY tag,tx,li)
      SELECT sum(n),count(*) FILTER(WHERE variants>1) FROM g'''
    print('SETTINGS',con.execute("SELECT current_setting('memory_limit'),current_setting('threads'),current_setting('temp_directory'),current_setting('max_temp_directory_size')").fetchone(),flush=True)
    print('EXPLAIN',con.execute('EXPLAIN '+query).fetchone()[1],flush=True)
    result=con.execute(query).fetchone(); assert result==(4999000,0),result
    print('PASS wide',result,'wall',time.monotonic()-t,'RSS_bytes',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'input_bytes',size(p),flush=True)
    con.close()


def supplement(root):
    for mode, subroot, limit in [('generate', root/'generation_measured', 600), ('wide', root, 900)]:
        subroot.mkdir(exist_ok=True)
        cmd=['/usr/bin/time','-l',sys.executable,'-B',str(Path(__file__).resolve()),mode,str(subroot)]
        log=root/'logs'/f'{mode}_supplement.log'
        watch=subroot/'generation_tmp' if mode=='generate' else root/'wide/duck_tmp'
        start=time.monotonic(); peak=generated_peak=0; samples=0
        with log.open('w') as f:
            p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},cwd=root)
            while p.poll() is None:
                peak=max(peak,size(watch)); samples+=1
                generated_peak=max(generated_peak,size(subroot if mode=='generate' else root/'wide'))
                if time.monotonic()-start>limit:
                    p.kill(); p.wait(); break
                time.sleep(1)
        text=log.read_text()
        timing(f'SUPPLEMENT {mode}: cmd={shlex.join(cmd)} launcher_rc={p.returncode} '
               f'wall={time.monotonic()-start:.3f}s timeout={limit}s temp_sample_peak_bytes={peak} '
               f'generated_total_sample_peak_bytes={generated_peak} samples={samples}; 1s sampling may miss brief peaks\n'+text)
        if mode=='wide':
            if 'PASS wide' in text:
                eq('PASS default-scale workload: 4,999,000 unique keys, tx66/address42/ts19/value37; '
                   'single bucket full-key GROUP BY + COUNT DISTINCT; settings/EXPLAIN/resource in W1_timing.txt; '
                   'not a claim about 100M rows or arbitrary skew')
            else:
                eq('INCOMPLETE default 5M bucket feasibility: '+text[-2500:])
        else:
            assert 'PASS main fixture' in text,text
            eq('PASS generation disk supplement: fixed seed regenerated identical design/counts under 600s; '
               'generation, inputs and scratch separately sampled; original frozen baseline fixture unchanged')


def varint_merge(root):
    case=root/'varint_merge'; case.mkdir()
    c=connect()
    keys=c.execute("SELECT min(i) FROM range(100) r(i) GROUP BY hash('t','0x'||lpad(lower(hex(i)),64,'0'),i::BIGINT)%3 ORDER BY 1").fetchall()
    assert len(keys)==3
    ids=[x[0] for x in keys]
    rows=[row(ids[0]),row(ids[1],frm=A(1000),to=A(1001)),row(ids[2],b=101,v='5')]
    c.close();c=small_raw(rows); manifests=emit(c,case,(100,110));c.close()
    paths,wanted=needs(case,[A(1000),A(1001),Z,DEAD,A(90000)])
    for fmt,m in manifests.items():
        for forced in (False,True):
            if forced: os.environ['W1_FORCE_WINDOW_ERROR']='1'
            else: os.environ.pop('W1_FORCE_WINDOW_ERROR',None)
            for version,script in [('old',root/'scripts/evm/replay_duck.py'),('new',EVM/'replay_duck.py')]:
                label=f'varint_merge_{fmt}_{forced}_{version}'
                r,so,se=run(root,label,script,m,case/label,paths,1,['--force-varint'],timeout=120)
                assert r['rc']==0,so+se
                fu=verify_receipt(case/'block_precision_followup.json',script,m,paths)
                assert fu['addresses']==expected(rows,wanted),(fu,expected(rows,wanted))
                assert fu['addresses'][A(1000)]==dict(peak='5',peak_blk=101),fu
                if forced: assert '回退 Python 流式' in so,so
            eq(f'PASS VARINT cross-bucket block merge {fmt} forced_window_error={forced}: '
               'rows=3 K=3 union=5; three keys in distinct buckets; mint 10 / outflow 10 same block net zero, next block peak5; '
               'old/new receipts and independent Python equal; fallback exercised when forced')
    os.environ.pop('W1_FORCE_WINDOW_ERROR',None)


if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='wrapped':
        wrapped(Path(sys.argv[2]),sys.argv[3:])
    else:
        root=Path(sys.argv[2]).resolve()
        globals()[mode](root)
