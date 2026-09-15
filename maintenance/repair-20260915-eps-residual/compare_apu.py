"""全实体、双锚点整数对齐；输出数量差分及指纹变化，不输出分析结论。"""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/report'),str(ROOT/'scripts/lib')]
from handoff_manifest import flip_fingerprint, ledger_real_flips
D=ROOT/'.staging_eps/apu'
old=json.loads((D/'provenance_ledger.json').read_text())
tag='704' if (D/'provenance_ledger_704.json').exists() else '704_diagnostic'
new=json.loads((D/f'provenance_ledger_{tag}.json').read_text())
input_checks={k:old['input_binding'][k]==new['input_binding'][k]
              for k in ('source','entity_file','labels_file','handoff_manifest','data_map','total_supply_raw')}
input_checks['production_sha256']=new['input_binding']['algorithm']['script_sha256']==hashlib.sha256((ROOT/'scripts/report/entity_source_trace.py').read_bytes()).hexdigest()
assert all(input_checks.values()), input_checks
a={e['entity_id']:e for e in old['entities']}
b={e['entity_id']:e for e in new['entities']}
assert len(a)==len(b)==105 and a.keys()==b.keys()
gap=('UNRESOLVED','data_gap',None)
res=('UNRESOLVED','fp_residual',None)

def rawmap(rows,policy=False):
    result={}
    for c in rows:
        k=tuple(c['terminal']) if policy else (c['kind'],c['subkind'],c['via'])
        assert k not in result
        result[k]=int(c['raw'])
    return result

def compare(x,y):
    return {'sum_equal':sum(x.values())==sum(y.values()),
            'nongap_equal':{k:v for k,v in x.items() if k not in (gap,res)}=={k:v for k,v in y.items() if k not in (gap,res)},
            'gap_split_equal':x.get(gap,0)==y.get(gap,0)+y.get(res,0)}

rows=[]
changes=[]
fails=[]
policy_fails=[]
for eid,e in a.items():
    for anchor in ('current','peak'):
        p,q=e['anchors'][anchor],b[eid]['anchors'][anchor]
        x,y=rawmap(p['composition']),rawmap(q['composition'])
        checks={'stock_equal':p['stock_raw']==q['stock_raw'],**compare(x,y)}
        for k,v in checks.items():
            if not v:fails.append([eid,anchor,k])
        pd0=old['bounds_sensitivity']['per_entity'][eid]['anchors'][anchor]['policy_details']
        pd1=new['bounds_sensitivity']['per_entity'][eid]['anchors'][anchor]['policy_details']
        pcs={}
        for policy in pd0:
            u,v=rawmap(pd0[policy],True),rawmap(pd1[policy],True)
            pcs[policy]=compare(u,v)
            for check_name, ok in pcs[policy].items():
                if not ok: policy_fails.append([eid,anchor,policy,check_name])
            for k in sorted(u.keys()|v.keys(),key=str):
                if u.get(k)!=v.get(k):
                    changes.append({'entity_id':eid,'anchor':anchor,'policy':policy,'terminal':k,'old_raw':u.get(k),'new_raw':v.get(k)})
        row={'entity_id':eid,'anchor':anchor,'checks':checks,
             'old_gap_entries':sum(c['subkind']=='data_gap' for c in p['composition']),
             'new_gap_entries':sum(c['subkind']=='data_gap' for c in q['composition']),
             'residual_entries':sum(c['subkind']=='fp_residual' for c in q['composition']),
             'old_gap_raw':str(x.get(gap,0)),'new_gap_raw':str(y.get(gap,0)),'residual_raw':str(y.get(res,0)),
             'policy_checks':pcs,'old_fingerprint':flip_fingerprint(pd0),'new_fingerprint':flip_fingerprint(pd1)}
        rows.append(row)
receipt=json.loads((D/'flip_adjudications.json').read_text())
real_flips=ledger_real_flips(new)
receipt_fingerprints=[]
for row in receipt['adjudications']:
    key=(row['entity_id'],row['anchor'])
    current=real_flips.get(key,{}).get('fingerprint')
    receipt_fingerprints.append({'entity_id':key[0],'anchor':key[1],
                                 'old_fingerprint':row['flip_fingerprint'],'new_fingerprint':current,
                                 'equal':row['flip_fingerprint']==current})
report={'receipt_fingerprints':receipt_fingerprints,
        'receipt_fingerprint_mismatches':sum(not x['equal'] for x in receipt_fingerprints),
        'input_checks':input_checks,'entities':105,'anchors':len(rows),'t4_failures':fails,'policy_failures':policy_fails,
        'old_gap_entries':sum(x['old_gap_entries'] for x in rows),
        'new_gap_entries':sum(x['new_gap_entries'] for x in rows),
        'residual_entries':sum(x['residual_entries'] for x in rows),
        'policy_changed_keys':len(changes),
        'policy_nongap_changed_keys':sum(x['terminal'] not in (gap,res) for x in changes),
        'fingerprints_changed':sum(x['old_fingerprint']!=x['new_fingerprint'] for x in rows),
        'rows':rows,'policy_changes':changes}
out=Path(__file__).resolve().parent
(out/'apu_diff.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
run=json.loads((D/f'trace_{tag}_run.json').read_text())
lines=['# APU 离线回归', '',f'- 模式：{tag}；退出码 {run["exit_code"]}。',
       '- 原参数正式运行因缺 data/stage2/flip_evidence.md 在收据校验处 exit 2；诊断模式只省略 --acknowledge-flip，保留其余参数。T6 正式运行仍未通过。' if tag.endswith('diagnostic') else '- 按原账本参数还原 CLI。',
       f'- 原始输入绑定逐项相同、生产算法 SHA-256 校验：{all(input_checks.values())}。',
       f'- 实体 {len(a)}；锚点 {len(rows)}；T4 失败 {len(fails)}。',
       f'- data_gap 条目 {report["old_gap_entries"]} → {report["new_gap_entries"]}；fp_residual 条目 {report["residual_entries"]}。',
       f'- 三策略数量检查失败 {len(policy_fails)}。',
       f'- 三策略来源 raw 变化键 {len(changes)}，非 gap/residual 变化键 {report["policy_nongap_changed_keys"]}；指纹变化 {report["fingerprints_changed"]}/{len(rows)}。',
       f'- 旧裁决收据指纹不匹配 {report["receipt_fingerprint_mismatches"]}/{len(receipt_fingerprints)}；补齐 evidence 文件后仍需处理这些旧收据失配，本次未修改裁决收据。',
       '- 全量来源 raw 差分、两版指纹及各项断言见 apu_diff.json。', '', '## 命令', '', '```sh', 'cd '+str(D), run['command'],'```','', '## 尘埃字段','', '| 实体 | current_negligible_skipped 旧→新 | composition_usable 旧→新 |','|---|---|---|']
for eid in ('TE-02','TE-04'):
    lines.append(f'| {eid} | {a[eid]["closure_check"].get("current_negligible_skipped")} → {b[eid]["closure_check"].get("current_negligible_skipped")} | {a[eid]["anchors"]["current"].get("composition_usable")} → {b[eid]["anchors"]["current"].get("composition_usable")} |')
lines+=['','## 逐实体、逐锚点', '', '| 实体 | 锚点 | gap 条目旧→新 | residual 条目 | gap 事件旧→新 | residual 事件 | T4 | 指纹变化 |','|---|---|---:|---:|---:|---:|---|---|']
for r in rows:
    eid=r['entity_id'];s0=a[eid]['simulation'];s1=b[eid]['simulation']
    lines.append(f'| {eid} | {r["anchor"]} | {r["old_gap_entries"]} → {r["new_gap_entries"]} | {r["residual_entries"]} | {s0["data_gap_events"]} → {s1["data_gap_events"]} | {s1["fp_residual_events"]} | {"PASS" if all(r["checks"].values()) else "FAIL"} | {r["old_fingerprint"]!=r["new_fingerprint"]} |')
(out/'apu_regression.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('rows','policy_changes','receipt_fingerprints')},indent=2))
sys.exit(1 if fails or policy_fails or report['policy_nongap_changed_keys'] else 0)
