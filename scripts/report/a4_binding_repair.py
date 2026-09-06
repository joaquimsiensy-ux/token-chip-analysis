"""Narrow, archived recovery of stale G8 bindings after a terminal distribution.

No claim, amount, membership, snapshot or classification may change here. The
only permitted identity delta is a state hash following addition of the already
A4-sealed distribution_observation field. The existing terminal is independently
recomputed before a new A4 revision is issued. Its real preterminal checkpoint is
restored, so normal scan/explain/record producers must produce a new terminal.
"""
from __future__ import annotations
import copy
import fcntl
import hashlib
import json
import os
import shutil
from collections import Counter
from pathlib import Path

import a4_gate
import entity_identity_gate
import holder_distribution_scan as distribution
import distribution_explanation_check as explanation


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def regular(root, rel):
    path = a4_gate.safe_case_file(root, rel)
    raw = root / Path(rel)
    for item in (raw, *raw.parents):
        if item == root:
            break
        if item.is_symlink():
            raise ValueError(f'symlink rejected: {rel}')
    return path


def entry(root, path):
    path = Path(path)
    return {'path': path.relative_to(root).as_posix(), 'sha256': sha(path),
            'size': path.stat().st_size}


def output_dir(root, rel):
    raw = Path(rel)
    if raw.is_absolute() or '..' in raw.parts or not raw.parts:
        raise ValueError('repair archive must be a new relative case directory')
    path = root / raw
    if path.exists() or path.is_symlink():
        raise ValueError('repair archive already exists; preserve the prior repair')
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError('repair archive parent is a symlink')
    path.resolve().relative_to(root)
    return path


def preflight(args):
    root = Path(args.case_dir).resolve()
    archive = output_dir(root, args.archive_dir)
    seal_path = regular(root, 'a4_seal.json')
    seal = load(seal_path)
    if seal.get('schema') != 'a4-seal/v4' or seal.get('verdict') != 'PASS' \
            or seal.get('workflow_type') != 'new-analysis':
        raise ValueError('repair requires a new-analysis PASS a4-seal/v4')
    errors = a4_gate.validate_revision_chain(root, seal)
    errors += entity_identity_gate.validate_gate(str(regular(root, 'identity_gate.json')))
    if errors:
        raise ValueError('; '.join(errors))
    old_gate_path = regular(root, args.previous_identity)
    old_state_path = regular(root, args.previous_state)
    old_gate, new_gate = load(old_gate_path), load(root/'identity_gate.json')
    old_state, new_state = load(old_state_path), load(root/'analysis-state.json')
    if old_gate.get('state_sha256') != sha(old_state_path):
        raise ValueError('previous state is not the state bound by the old identity receipt')
    if {k:v for k,v in old_gate.items() if k != 'state_sha256'} != \
            {k:v for k,v in new_gate.items() if k != 'state_sha256'}:
        raise ValueError('identity rows, resolutions or snapshot changed')
    if old_state == new_state or 'distribution_observation' in old_state \
            or {k:v for k,v in new_state.items() if k != 'distribution_observation'} != old_state:
        raise ValueError('only an added distribution_observation field may explain the old state hash')
    entries = seal.get('sealed_files', []) + [seal.get('registry', {}), seal.get('verdicts', {})]
    if any(not isinstance(x,dict) or not x.get('path') for x in entries):
        raise ValueError('invalid A4 file entry')
    counts = Counter(x['path'] for x in entries)
    dedicated = {seal['registry']['path'], seal['verdicts']['path']}
    if any(n > 1 and (rel not in dedicated or n != 2) for rel,n in counts.items()):
        raise ValueError('duplicate path is not a redundant registry/verdict role')
    expected = {}
    for item in entries:
        rel = item['path']; path = regular(root, rel)
        if rel in expected and expected[rel] != item['sha256']:
            raise ValueError('duplicate A4 entries disagree')
        expected[rel] = item['sha256']
        digest = sha(old_gate_path) if rel == 'identity_gate.json' else sha(path)
        if digest != item['sha256']:
            raise ValueError('A4-sealed input changed: ' + rel)
    required = a4_gate.MANDATORY_SEAL_FILES | {'a4_claims.json'}
    if not required <= set(expected):
        raise ValueError('A4 required inputs missing')
    if 'identity_gate.json' not in expected or sha(root/'identity_gate.json') == expected['identity_gate.json']:
        raise ValueError('no stale identity binding to repair')
    registry = load(root / seal['registry']['path'])
    claims = a4_gate.validate_claim_rows(root, registry.get('claims'))
    claim_ids = {x['id'] for x in claims}
    verdicts = load(root / seal['verdicts']['path'])
    if {str(v.get('id')) for v in verdicts} != claim_ids \
            or {x.get('id') for x in seal.get('claims',[])} != claim_ids:
        raise ValueError('claim/verdict coverage differs')
    for verdict in verdicts:
        if verdict.get('verdict') not in a4_gate.VERDICTS:
            raise ValueError('invalid verdict')
    ledger_path = regular(root, 'distribution_rounds.json')
    ledger = load(ledger_path)
    errors = distribution.validate_rounds_ledger(ledger)
    terminal = ledger.get('terminal') or {}
    if errors or terminal.get('status') not in {'EXPLAINED','NORMAL','LOW_SAMPLE'}:
        raise ValueError('repair requires an existing non-waived valid terminal')
    rounds = ledger['rounds']; last = rounds[-1]
    if terminal.get('round_n') != len(rounds) or last['a4_seal_sha'] != sha(seal_path):
        raise ValueError('terminal is not the current A4-bound last round')
    scan_rel = last['final_scan_path']; scan_path = regular(root, scan_rel)
    if sha(scan_path) != last['final_scan_sha']:
        raise ValueError('terminal scan hash changed')
    errors = distribution.validate_scan(root, scan_rel, 'final')
    if errors:
        raise ValueError('terminal independent replay: ' + '; '.join(errors))
    if terminal['status'] == 'EXPLAINED':
        ep = regular(root, last['explanation_path'])
        if sha(ep) != last['explanation_sha']:
            raise ValueError('terminal explanation hash changed')
        errors = explanation.validate_explanation(root, last['explanation_path'])
        if errors:
            raise ValueError('terminal explanation replay: ' + '; '.join(errors))
    checkpoint_path = regular(root, args.rounds_checkpoint)
    checkpoint = load(checkpoint_path)
    prefix = {**ledger, 'rounds':rounds[:-1], 'terminal':None}
    if checkpoint != prefix:
        raise ValueError('checkpoint is not the exact recorded preterminal ledger')
    rb = load(scan_path)['input_binding']['round_binding']['rounds_before_append']
    if not rb or rb.get('canonical_sha256') != distribution.canonical_sha(checkpoint):
        raise ValueError('checkpoint is not bound by the terminal scan')
    source = seal.get('distribution_claim_source') or {}
    if source.get('path') not in expected:
        raise ValueError('A4 distribution claim source not sealed')
    observed = {'dist-'+x['cluster_id'] for x in load(scan_path).get('abnormal_clusters',[])}
    if observed != {x for x in claim_ids if x.startswith('dist-')}:
        raise ValueError('terminal clusters differ from existing A4 claims')
    archives = {'a4_seal.json','distribution_rounds.json',scan_rel,
                str(Path(scan_rel).parent/'holder_distribution_round.png')}
    if last.get('explanation_path'):
        archives.add(last['explanation_path'])
    charts = root / str(seal.get('charts_dir','charts/final'))
    charts.resolve().relative_to(root)
    if charts.is_symlink():
        raise ValueError('chart directory is a symlink')
    for path in charts.iterdir() if charts.exists() else []:
        rel = path.relative_to(root).as_posix()
        regular(root, rel)
        if path.suffix != '.png':
            raise ValueError('unexpected non-PNG final output')
        archives.add(rel)
    if (root/'a5_report_seal.json').exists():
        archives.add('a5_report_seal.json')
    if (root/'报告.html').exists():
        raise ValueError('existing published HTML requires a separate report revision workflow')
    inputs = {rel:entry(root,regular(root,rel)) for rel in set(expected)|archives|
              {args.previous_identity,args.previous_state,args.rounds_checkpoint}}
    revision_archive = root / f'a4_seals/revision_{seal["revision"]}.json'
    if revision_archive.is_symlink() or revision_archive.parent.is_symlink():
        raise ValueError('A4 revision archive is a symlink')
    if revision_archive.exists() and sha(revision_archive) != sha(seal_path):
        raise ValueError('A4 revision archive conflicts')
    return {'root':root,'archive':archive,'seal':seal,'ledger':ledger,'inputs':inputs,
            'archives':sorted(archives),'checkpoint_path':checkpoint_path,
            'revision_archive':revision_archive,'round_n':len(rounds)}


def apply(plan):
    root, archive = plan['root'], plan['archive']
    for rel, expected in plan['inputs'].items():
        if entry(root,regular(root,rel)) != expected:
            raise ValueError('input changed after preflight: ' + rel)
    archive.mkdir(parents=True, exist_ok=False)
    for rel in plan['archives']:
        target = archive/'before'/rel; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/rel,target)
        if sha(target) != plan['inputs'][rel]['sha256']:
            raise ValueError('archive copy mismatch')
    for rel, expected in plan['inputs'].items():
        if entry(root,regular(root,rel)) != expected:
            raise ValueError('input changed while archiving: ' + rel)
    record = {'schema':'a4-binding-repair/v1','created_at_utc':a4_gate.utcnow(),
              'scope':'Only refresh the stale G8 state hash and remove identical cross-role duplicates; no claim or numeric change.',
              'inputs':plan['inputs'],'archived_files':plan['archives'],
              'old_revision':plan['seal']['revision'],'new_revision':plan['seal']['revision']+1,
              'round_to_replay':plan['round_n'],'terminal_replayed_before_repair':True,
              'required_next':'Native final scan, explanation and record of the same round must run again; no terminal is asserted by this receipt.'}
    record_path = archive/'repair_plan.json'
    distribution.atomic_json(record_path,record)
    # Every old artifact is preserved before canonical outputs are invalidated.
    # Each move targets one known file. A failure leaves a nonterminal case.
    for rel in plan['archives']:
        if rel in {'a4_seal.json','distribution_rounds.json'}:
            continue
        dest=archive/'superseded'/rel; dest.parent.mkdir(parents=True,exist_ok=True)
        os.replace(root/rel,dest)
    checkpoint_pending=root/'.distribution_rounds.binding-repair.tmp'
    if checkpoint_pending.exists():
        raise ValueError('pending checkpoint already exists')
    shutil.copy2(plan['checkpoint_path'],checkpoint_pending)
    os.replace(checkpoint_pending,root/'distribution_rounds.json')
    previous = plan['revision_archive']; previous.parent.mkdir(exist_ok=True)
    if not previous.exists():
        shutil.copy2(root/'a4_seal.json',previous)
    new = copy.deepcopy(plan['seal'])
    new.update(revision=new['revision']+1, sealed_at_utc=a4_gate.utcnow(),
               previous_seal={'path':previous.relative_to(root).as_posix(),
                              'sha256':sha(previous),'revision':plan['seal']['revision']})
    dedicated={new['registry']['path'],new['verdicts']['path']}
    refs={x['path']:x for x in new['sealed_files'] if x['path'] not in dedicated}
    refs['identity_gate.json']={'path':'identity_gate.json','sha256':sha(root/'identity_gate.json')}
    refs[record_path.relative_to(root).as_posix()]={'path':record_path.relative_to(root).as_posix(),'sha256':sha(record_path)}
    new['sealed_files']=[refs[key] for key in sorted(refs)]
    new['binding_repair']={'schema':'a4-binding-repair/v1','plan':entry(root,record_path)}
    distribution.atomic_json(root/'a4_seal.json',new)
    errors=a4_gate.validate_revision_chain(root,new)
    if errors:
        raise ValueError('; '.join(errors))
    return {'status':'A4_REPAIRED_REQUIRES_NATIVE_TERMINAL_REPLAY','revision':new['revision'],
            'a4_sha256':sha(root/'a4_seal.json'),'round_to_replay':plan['round_n'],
            'archive':archive.relative_to(root).as_posix()}


def run(args):
    try:
        if not args.apply:
            p=preflight(args)
            result={'status':'REPAIR_PREFLIGHT_PASS','old_revision':p['seal']['revision'],
                    'new_revision':p['seal']['revision']+1,'round_to_replay':p['round_n']}
        else:
            root=Path(args.case_dir).resolve(); lock=root/'.a4_binding_repair.lock'
            descriptor=os.open(lock,os.O_RDWR|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
            with os.fdopen(descriptor,'w') as stream:
                fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
                result=apply(preflight(args))
        print(json.dumps(result,ensure_ascii=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('BLOCK: '+str(exc))
        return 2
