"""Archived A4 repair: real producer loop and negative input-preservation cases."""
import argparse
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'scripts/report')]
import a4_gate as a4
import a4_binding_repair as repair
import holder_distribution_scan as dist
import distribution_explanation_check as explain
import entity_identity_gate as identity
from identity_gate_fixture import write_binding
from test_distribution_gate import make_case,add_final_inputs,write_json,sha


def scan(c,n):
    args=argparse.Namespace(case_dir=str(c),stage='final',snapshot='data/holders_owners.json',output=None,chart=None,round=n)
    assert dist.cmd_scan(args)==0
    return f'dist_rounds/round_{n}/distribution_scan.json'


def finish(c,n,explained):
    rel=scan(c,n); ep=f'dist_rounds/round_{n}/distribution_explanation_check.json'
    if explained:
        obj=explain.evaluate(c,rel,'a4_seal.json');assert obj['verdict']=='EXPLAINED',obj
        write_json(c/ep,obj)
    assert dist.cmd_record_round(argparse.Namespace(case_dir=str(c),scan=rel,explanation=ep if explained else None,waiver=None))==0


def fixture(c):
    balances={f'0x12345678900000000000000000000000{i:08x}':75000 for i in range(200)}
    head='0xabcdef7890000000000000000000000000000001';balances[head]=5000000
    make_case(c,balances)
    initial=dist.build_scan(c,'initial','data/holders_owners.json');write_json(c/'distribution_scan.json',initial)
    claims=[]
    for x in initial['abnormal_clusters']:
        claims.append({'id':'dist-'+x['cluster_id'],'text':'fixture observed concentrated holdings',
                       'files':['evidence.json'],'report_locations':['report:1'],
                       'distribution_explanation':{'cluster_ids':[x['cluster_id']],
                           'members':[m['owner'] for m in x['members']],
                           'explained_raw':x['raw_balance'],'evidence_refs':['evidence.json'],'propagation':{}}})
    assert claims
    add_final_inputs(c,claims)
    state={'chain':'bsc','whale_groups':[{'entity_id':'e1','addresses':[head]}]}
    write_json(c/'analysis-state.json',state);write_json(c/'history/state.json',state)
    total,_=write_binding(c,balances)
    def make_identity():
        gate=identity.build(str(c/'analysis-state.json'),'bsc',str(c/'balances_final.json'),str(c/'identity_gate.json'),total_supply_raw=total,snapshot_receipt_path=str(c/'identity_holders_receipt.json'))
        for row in gate['rows']:
            if row['flag']:row['resolution']='Fixture reviewed identity based on the synthetic source.'
        write_json(c/'identity_gate.json',gate);assert not identity.validate_gate(str(c/'identity_gate.json'))
        return gate
    old=make_identity();write_json(c/'history/identity.json',old)
    state['distribution_observation']={'scope':'additional observation metadata'};write_json(c/'analysis-state.json',state)
    for claim in claims:
        claim['distribution_explanation']['propagation']={'facts_sha256':sha(c/'facts.json'),'analysis_state_sha256':sha(c/'analysis-state.json')}
    write_json(c/'claims-input.json',claims)
    assert a4.cmd_register(argparse.Namespace(case_dir=str(c),claims_file=str(c/'claims-input.json')))==0
    write_json(c/'verdicts.json',[{'id':x['id'],'verdict':'CONFIRMED'} for x in claims])
    (c/'findings.md').write_text('Synthetic fixture findings.\n')
    # Remove the seed fixture seal; it has not entered a revision chain.
    os.replace(c/'a4_seal.json',c/'history/seed-seal.json')
    args=argparse.Namespace(case_dir=str(c),verdicts_file=str(c/'verdicts.json'),seal_files='evidence.json,verdicts.json,a4_claims.json',charts_dir='charts/final',workflow_type='new-analysis')
    assert a4.cmd_finalize(args)==2, 'duplicate dedicated paths must fail closed'
    assert not (c/'a4_seal.json').exists(), 'rejected finalize must not create a seal'
    args.seal_files='evidence.json'
    assert a4.cmd_finalize(args)==0
    sealed=repair.load(c/'a4_seal.json');paths=[x['path'] for x in sealed['sealed_files']]+[sealed['registry']['path'],sealed['verdicts']['path']]
    assert len(paths)==len(set(paths)),'native finalize still produces duplicate dedicated paths'
    # Recreate the former producer's identical cross-role duplicate.
    sealed['sealed_files'].append(copy.deepcopy(sealed['verdicts']));write_json(c/'a4_seal.json',sealed)
    make_identity()
    finish(c,1,False);shutil.copy2(c/'distribution_rounds.json',c/'history/checkpoint.json')
    finish(c,2,True)
    return argparse.Namespace(case_dir=str(c),previous_identity='history/identity.json',previous_state='history/state.json',rounds_checkpoint='history/checkpoint.json',archive_dir='recovery/native',apply=False)


def snapshot(c):
    return {str(p.relative_to(c)):sha(p) for p in c.rglob('*') if p.is_file()}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        c=Path(tmp)
        with contextlib.redirect_stdout(io.StringIO()):args=fixture(c)
        before=snapshot(c);plan=repair.preflight(args);assert snapshot(c)==before
        print('ok read-only preflight with real native terminal replay')
        def reject(rel,change,expected):
            path=c/rel;raw=path.read_bytes();value=repair.load(path)
            try:
                change(value);write_json(path,value)
                frozen=snapshot(c)
                try:repair.preflight(args)
                except ValueError as e:assert expected in str(e),(expected,str(e))
                else:raise AssertionError('accepted invalid '+rel)
                assert snapshot(c)==frozen,'rejected preflight mutated case'
            finally:path.write_bytes(raw)
            print('ok reject '+expected)
        reject('facts.json',lambda x:x.update(extra=1),'A4-sealed input changed')
        reject('identity_gate.json',lambda x:x['rows'][0].update(resolution='Changed substantive judgment'),'identity rows')
        reject('history/state.json',lambda x:x.update(extra=1),'previous state')
        reject('analysis-state.json',lambda x:x.update(new_judgment=True),'state_sha256')
        reject('history/checkpoint.json',lambda x:x.update(rounds=[]),'exact recorded preterminal')
        reject('a4_seal.json',lambda x:x['sealed_files'].append({'path':'facts.json','sha256':sha(c/'facts.json')}),'duplicate path')
        reject('a4_seal.json',lambda x:x['sealed_files'][-1].update(sha256='0'*64),'A4-sealed input changed')
        reject('dist_rounds/round_2/distribution_scan.json',lambda x:x.update(owner_count_private_main=1),'terminal scan hash changed')
        reject('dist_rounds/round_2/distribution_explanation_check.json',lambda x:x.update(verdict='UNEXPLAINED'),'terminal explanation hash changed')
        reject('distribution_rounds.json',lambda x:x['terminal'].update(status='WAIVED'),'valid terminal')
        (c/'outside-link').symlink_to(c/'history',target_is_directory=True)
        bad=copy.copy(args);bad.archive_dir='outside-link/new'
        try:repair.preflight(bad)
        except ValueError as e:assert 'symlink' in str(e)
        else:raise AssertionError('archive symlink accepted')
        (c/'outside-link').unlink()
        # Revalidate every planned input immediately before applying.
        p=repair.preflight(args);raw=(c/'facts.json').read_bytes();(c/'facts.json').write_text('{}')
        try:repair.apply(p)
        except ValueError as e:assert 'changed after preflight' in str(e)
        else:raise AssertionError('TOCTOU admitted')
        (c/'facts.json').write_bytes(raw)
        old=repair.load(c/'a4_seal.json');old_scan=repair.load(c/'dist_rounds/round_2/distribution_scan.json')
        p=repair.preflight(args);out=repair.apply(p);assert out['revision']==old['revision']+1
        new=repair.load(c/'a4_seal.json');assert new['claims']==old['claims'] and new['verdicts']==old['verdicts']
        assert not a4.validate_revision_chain(c,new)
        assert not repair.load(c/'distribution_rounds.json')['terminal']
        assert not (c/'dist_rounds/round_2/distribution_scan.json').exists()
        assert not list((c/'charts/final').iterdir())
        for rel,digest in before.items():
            archived=c/'recovery/native/before'/rel
            if archived.exists():assert sha(archived)==digest
        print('ok native repair archives complete old terminal and advances A4 revision')
        with contextlib.redirect_stdout(io.StringIO()):finish(c,2,True)
        fresh=repair.load(c/'dist_rounds/round_2/distribution_scan.json')
        for key in ['partition','partition_check','abnormal_clusters','denominators','bucket_coverage','base_bins','shifted_bins','verdict']:
            assert fresh[key]==old_scan[key],key
        assert repair.load(c/'distribution_rounds.json')['terminal']['status']=='EXPLAINED'
        assert not dist.validate_scan(c,'dist_rounds/round_2/distribution_scan.json','final')
        print('ok real native scan/explanation/record reproduces identical analytical result')
    print('PASS: bounded A4 binding repair, 12 negative checks and full native terminal replay')
    return 0

if __name__=='__main__':raise SystemExit(main())
