import sys, os, json, hashlib, tempfile, traceback
from pathlib import Path
from copy import deepcopy
from collections import Counter
from unittest.mock import patch

ROOT = Path('/Users/uravvv/.claude/skills/token-chip-analysis')
OUT = Path(__file__).resolve().parent
os.chdir(OUT)
tempfile.tempdir = str(OUT)
sys.dont_write_bytecode = True
blocked = []

def audit(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system', 'os.posix_spawn'}:
        blocked.append((event, str(args[:1])))
        raise RuntimeError('offline runner blocked ' + event)
    paths = args[:1] if event in {'open', 'os.listdir', 'os.scandir'} else ()
    for path in paths:
        if not isinstance(path, (str, bytes, os.PathLike)):
            continue
        path = Path(os.path.abspath(os.fsdecode(path)))
        parts = path.parts
        forbidden = any(p in {'.codex', 'archive', 'blind-reviews', '.hypothesis'} or p.startswith('.staging_') for p in parts)
        forbidden |= path == ROOT / 'references/attic.md'
        forbidden |= any(path == p or p in path.parents for p in (Path('/Users/uravvv/Desktop'), Path('/Users/uravvv/Documents')))
        if ROOT / 'maintenance' in path.parents:
            allowed = ROOT / 'maintenance/repair-20260924b-sol-stage1-speed'
            forbidden |= path != allowed and allowed not in path.parents
        if forbidden:
            blocked.append((event, str(path)))
            raise RuntimeError('forbidden path: ' + str(path))
        if event == 'open':
            mode, flags = args[1:3]
            writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            if writing and OUT != path and OUT not in path.parents:
                blocked.append((event, str(path)))
                raise RuntimeError('write outside tempfile: ' + str(path))

sys.addaudithook(audit)
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts/tests'), str(ROOT / 'scripts/solana'), str(ROOT / 'scripts/lib')]
import test_sqd_gap_repair as t
from scripts.solana import sqd_gap_repair as repair
import sqd_cache_identity as identity
import producer_history as registry

SHA = '15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33'
SCRIPT = 'scripts/solana/sqd_gap_repair.py'
PROTOCOLS = {'sqd-solana-cache/v4', 'sqd-solana-repair-bundle/v1', 'sqd-solana-coverage-resolution/v1', 'sqd-solana-repair-pointer/v1'}
MINT = t.MINT
original_registry = registry.PRODUCER_HISTORY
original_query = identity.historical_producer_hashes
assert original_query is registry.historical_producer_hashes
assert repair.historical_producer_hashes is original_query
assert repair.sha256_file(ROOT / SCRIPT) == SHA
removed = tuple(e for e in original_registry if e['script'] == SCRIPT and e['sha256'] == SHA and e['protocol'] in PROTOCOLS)
assert len(removed) == 4 and {e['protocol'] for e in removed} == PROTOCOLS
assert all(e['status'] == 'ACTIVE' and e['commit'] == '59f88b84c9ab9eeb95c92a15e342d8cbe09925db' for e in removed)
filtered = tuple(e for e in original_registry if e not in removed)
results = {'python': sys.version, 'executable': sys.executable, 'tempfile': str(OUT), 'removed': removed, 'cases': []}
slots = [19998, 19999]
old_sha = '25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66'
assert old_sha in repair.historical_producer_hashes(SCRIPT, 'sqd-solana-repair-bundle/v1')
fp = repair.reference_endpoint_identity('fixture://helius')['sha256']
original_call = repair.RepairFixtureTransport.call

for label, old_count in (('old', 2), ('new', 0), ('mixed', 1)):
    row = {'label': label, 'old_count': old_count}
    results['cases'].append(row)
    try:
        root = Path(tempfile.mkdtemp(prefix=f'w4-{label}-', dir=OUT))
        case = t.build_batch3b_case(root, set(slots), [
            [i + 1, slot, 0, -1, t.ZERO, f'Base{i}', 1]
            for i, slot in enumerate(slots)])
        plan, _, _ = repair._plan(case, MINT, reference_fingerprint=fp)
        parent, pointer, _ = repair.sqd_repair_paths(case, MINT)
        old_bytes = {}
        args = ['repair', '--mint', MINT, '--case-root', str(case)]
        if old_count:
            previous = deepcopy(plan)
            previous['producer']['sha256'] = old_sha
            previous['plan_digest'] = repair.compute_plan_digest(previous)
            old = parent / f"pending-{previous['plan_digest']}"
            old.mkdir(parents=True)
            repair.load_resume_slots(old, repair._ledger_header(previous))
            for seq, slot in enumerate(slots[:old_count]):
                payload, ledger = t.w4_old_payload_and_ledger(repair, slot, fp, seq)
                repair._persist_live_slot(old, payload, MINT, ledger)
            old_bytes = {str(p.relative_to(old)): p.read_bytes() for p in old.rglob('*') if p.is_file()}
            args += ['--resume', '--adopt-pending', str(old)]
        responses = {}
        for slot in slots[old_count:]:
            responses.update(t.repair_slot_responses(repair, slot, t.w4_missing_transaction(slot)))
        fixture = t.write_repair_fixture(root / 'fixture', responses)
        calls = []
        def observe(self, kind, body):
            calls.append((kind, body['params'][0] if kind == 'reference-getBlock' else body['fromBlock']))
            return original_call(self, kind, body)
        with patch.object(repair.RepairFixtureTransport, 'call', observe):
            assert repair.main(args + ['--transport-fixture', str(fixture)]) == 0
        assert Counter(calls) == Counter((kind, slot) for slot in slots[old_count:] for kind in ('sqd-census', 'reference-getBlock'))
        current = json.loads(pointer.read_text())
        gen = parent / f"gen-{current['gid']}"
        bundle = json.loads((gen / 'bundle.json').read_text())
        for name, content in old_bytes.items():
            assert (old / name).read_bytes() == content
            if name.startswith('evidence/'):
                assert (gen / name).read_bytes() == content
        rows = repair._parse_ledger_prefix((gen / 'rpc_ledger.jsonl').read_bytes())
        if old_count:
            assert rows[0]['adopted']['rows'] == old_count
            assert rows[1:old_count + 1] == repair._parse_ledger_prefix(old_bytes['rpc_ledger.jsonl'])[1:]
        for i, slot in enumerate(slots):
            ev = json.loads((gen / f'evidence/{slot}.sqd.json').read_text())
            assert (ev['coverage_probe_query_sha256'] == ev['query_body_sha256']) == (i >= old_count)
            assert (ev['coverage_probe_response_sha256'] == ev['response_sha256']) == (i >= old_count)
        resolution = json.loads((gen / 'coverage_resolution.json').read_text())
        confirmed = [r['slot'] for r in resolution['census'] if r['result'] == 'confirmed_nonce_defect']
        assert confirmed == slots
        assert bundle['producer']['sha256'] == SHA and bundle['mode'] == 'formal'
        base_edge, _, _ = repair.soltx_cache_paths(MINT, case / 'data')
        assert base_edge.resolve() == (case / bundle['base']['edge_file']).resolve()
        assert repair.sha256_file(base_edge) == plan['base']['edge_sha256']
        kwargs = dict(deep=True, case_root=case, current_base={'edge_sha256': repair.sha256_file(base_edge)})
        row.update(case=str(case), gen=str(gen), base_edge=str(base_edge), confirmed=confirmed, gid=bundle['gid'], calls=calls)
        # B: real registry and query function, without patches.
        assert registry.PRODUCER_HISTORY is original_registry
        assert identity.historical_producer_hashes is original_query
        checked = identity.validate_repair_bundle(gen / 'bundle.json', **kwargs)
        assert checked == bundle
        row['B_validate'] = f"PASS: returned bundle gid={checked['gid']}, mode={checked['mode']}"
        edge, meta, kind, gid, binding = identity.resolve_formal_cache(MINT, case)
        assert kind == 'repaired' and gid == bundle['gid'] == current['gid']
        assert binding['cache_kind'] == 'repaired' and binding['gid'] == gid
        assert edge.resolve() == (gen / bundle['merged']['edge_file']).resolve()
        assert meta.resolve() == (gen / bundle['merged']['meta_file']).resolve()
        assert edge.parent.resolve() == meta.parent.resolve() == gen.resolve()
        assert (case / current['inputs']['bundle']['path']).resolve() == (gen / 'bundle.json').resolve()
        assert binding['soltx_edges_sha256'] == repair.sha256_file(edge)
        assert binding['soltx_meta_sha256'] == repair.sha256_file(meta)
        row['B_resolve'] = f"PASS: kind={kind}, gid={gid}, binding.cache_kind={binding['cache_kind']}; edge/meta=CURRENT-selected generation"
        row.update(edge=str(edge), meta=str(meta), binding=binding)
        # C: remove exactly the four entries, in memory only; same artifacts and calls.
        row['C'] = {}
        with patch.object(registry, 'PRODUCER_HISTORY', filtered):
            assert identity.historical_producer_hashes is original_query
            for protocol in PROTOCOLS:
                assert SHA not in original_query(SCRIPT, protocol)
            for name, call in (
                ('validate_repair_bundle', lambda: identity.validate_repair_bundle(gen / 'bundle.json', **kwargs)),
                ('resolve_formal_cache', lambda: identity.resolve_formal_cache(MINT, case)),
            ):
                try:
                    call()
                except ValueError as exc:
                    row['C'][name] = f'{type(exc).__name__}: {exc}'
                    assert str(exc) == 'formal repair producer is not registered'
                else:
                    raise AssertionError(name + ' unexpectedly accepted unregistered producer')
        assert registry.PRODUCER_HISTORY is original_registry
        row['PASS'] = True
    except Exception:
        row['error'] = traceback.format_exc()
        row['PASS'] = False
    print('CASE_RESULT ' + json.dumps(row, ensure_ascii=False), flush=True)
results['blocked_events'] = blocked
results['PASS'] = all(r['PASS'] for r in results['cases']) and not blocked
(OUT / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
print('FINAL ' + ('PASS' if results['PASS'] else 'FAIL'), flush=True)
sys.exit(0 if results['PASS'] else 1)
