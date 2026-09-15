"""按 t7_ruling.md 对照同输入两次实际运行；不修改 fixture。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
gap = ('UNRESOLVED', 'data_gap', None)
res = ('UNRESOLVED', 'fp_residual', None)


def rawmap(rows):
    result = {}
    for row in rows:
        key = (row['kind'], row['subkind'], row['via'])
        assert key not in result
        result[key] = int(row['raw'])
    return result


def reasons(log):
    return [line for line in log.splitlines()
            if '✗' in line or '敏感性不稳：' in line or '闭合自检失败：' in line]


runs = [json.loads((OUT / f'pythia_run_{v}_result.json').read_text())
        for v in ('703', '704')]
logs = [(OUT / f'pythia_run_{v}.log').read_text() for v in ('703', '704')]
ledgers = [ROOT / f'.staging_eps/pythia/t7_compare/ledger_{v}.json'
           for v in ('703', '704')]
# Same interpreter and all semantic CLI inputs; only algorithm and output differ.
same_args = runs[0]['argv'][0] == runs[1]['argv'][0] and runs[0]['argv'][2:-2] == runs[1]['argv'][2:-2]
report = {
    'same_input_arguments': same_args,
    'exit_codes': [r['exit_code'] for r in runs],
    'exit_codes_equal': runs[0]['exit_code'] == runs[1]['exit_code'],
    'blocking_reasons': [reasons(log) for log in logs],
    'ledger_exists': [p.exists() for p in ledgers],
    'rows': [], 'events': [], 't4_failures': [],
    'historical_q1_data_gap_events_information_only': 2191,
}
report['blocking_reasons_equal'] = report['blocking_reasons'][0] == report['blocking_reasons'][1]
assert same_args and report['exit_codes_equal']
if runs[0]['exit_code'] == 2:
    assert report['blocking_reasons'][0] and report['blocking_reasons_equal']
assert report['ledger_exists'][0] == report['ledger_exists'][1]
if all(report['ledger_exists']):
    old, new = [json.loads(p.read_text()) for p in ledgers]
    a, b = [{e['entity_id']: e for e in x['entities']} for x in (old, new)]
    assert a.keys() == b.keys()
    report['entities'] = len(a)
    report['exploration'] = [x['exploration'] for x in (old, new)]
    report['input_binding_equal'] = {
        key: old['input_binding'][key] == new['input_binding'][key]
        for key in ('source', 'entity_file', 'labels_file', 'handoff_manifest', 'data_map', 'total_supply_raw')
    }
    assert all(report['input_binding_equal'].values())
    for eid, e in a.items():
        before, after = e['simulation'], b[eid]['simulation']
        report['events'].append({'entity_id': eid,
            'data_gap_events': [before['data_gap_events'], after['data_gap_events']],
            'fp_residual_events': [before.get('fp_residual_events', 0), after['fp_residual_events']]})
        for anchor in ('current', 'peak'):
            p, q = e['anchors'][anchor], b[eid]['anchors'][anchor]
            x, y = rawmap(p['composition']), rawmap(q['composition'])
            checks = {
                'stock_equal': p['stock_raw'] == q['stock_raw'],
                'sum_equal': sum(x.values()) == sum(y.values()),
                'nongap_equal': {k: v for k, v in x.items() if k not in (gap, res)} == {k: v for k, v in y.items() if k not in (gap, res)},
                'gap_split_equal': x.get(gap, 0) == y.get(gap, 0) + y.get(res, 0),
            }
            report['rows'].append({'entity_id': eid, 'anchor': anchor,
                'stock_raw': [p['stock_raw'], q['stock_raw']],
                'sum_raw': [str(sum(x.values())), str(sum(y.values()))],
                'data_gap_raw': [str(x.get(gap, 0)), str(y.get(gap, 0))],
                'fp_residual_raw': str(y.get(res, 0)), 'checks': checks,
                'source_rows': [{'terminal': k, 'old_raw': str(x[k]) if k in x else None,
                                 'new_raw': str(y[k]) if k in y else None}
                                for k in sorted(x.keys() | y.keys(), key=str)]})
            report['t4_failures'] += [[eid, anchor, k] for k, ok in checks.items() if not ok]
else:
    report['entities'] = None
    report['quantity_evidence_unavailable'] = True
(OUT / 'pythia_diff.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
lines = ['# PYTHIA 同输入双版本回归', '',
    '- 依据：t7_ruling.md；同一 DuckDB、7 实体 102 址、供应量 998158041739995、edge_budget 5000000；其余默认，allow-no-labels。',
    '- 原清单 33/33 与 PYTHIA 补充清单 2/2 校验通过；fixture 未修改。',
    f'- 退出码：7.0.3 = {runs[0]["exit_code"]}；7.0.4 = {runs[1]["exit_code"]}；阻断原因文本相同：{report["blocking_reasons_equal"]}。',
    f'- 账本落盘：{report["ledger_exists"]}；T4 失败数：{len(report["t4_failures"]) if all(report["ledger_exists"]) else "未能取证"}。',
    '- 历史 fixture q1_peak_anchor.simulation.data_gap_events = 2191，仅信息性并列；与本次实体口径、版本不同，不作相等断言。',
    '- 全量终点 raw 对照与断言见 pythia_diff.json。']
if not all(report['ledger_exists']):
    lines += ['', '**T7 数量不变量未能在 PYTHIA 上取证，由 T6 APU 全量 105 实体承担。**',
              '两版无账本，逐实体 data_gap_events / fp_residual_events 无可读取实测值。']
for v, r in zip(('703', '704'), runs):
    err = (OUT / r['stderr_file']).read_text()
    lines += ['', f'## 7.0.{v[-1]} 实际运行', '', '```sh', r['command'], '```', '',
              f'- cwd：`{r["cwd"]}`；exit {r["exit_code"]}；耗时 {r["elapsed_seconds"]:.3f} 秒。',
              f'- 算法 SHA-256：`{r["production_sha256"]}`。',
              f'- 完整日志：`{r["stdout_and_stderr_log"]}`；stderr 文件：`{r["stderr_file"]}`。',
              '', '### stderr 原文（空则标明）', '', '```text', err if err else '(empty; 0 bytes)', '```',
              '', '### 阻断原因原文（stdout）', '', '```text',
              '\n'.join(report['blocking_reasons'][0 if v == '703' else 1]), '```']
if report['events']:
    lines += ['', '## 逐实体事件数', '', '| 实体 | data_gap_events 旧→新 | fp_residual_events 旧→新 |', '|---|---:|---:|']
    for e in report['events']:
        lines.append(f'| {e["entity_id"]} | {e["data_gap_events"][0]} → {e["data_gap_events"][1]} | {e["fp_residual_events"][0]} → {e["fp_residual_events"][1]} |')
    lines += ['', '## 逐锚点数量', '', '| 实体 | 锚点 | stock_raw 旧/新相同值 | Σraw 旧/新相同值 | data_gap 旧→新 | fp_residual 新 | T4 |', '|---|---|---:|---:|---:|---:|---|']
    for r in report['rows']:
        lines.append(f'| {r["entity_id"]} | {r["anchor"]} | {" / ".join(r["stock_raw"])} | {" / ".join(r["sum_raw"])} | {" → ".join(r["data_gap_raw"])} | {r["fp_residual_raw"]} | {"PASS" if all(r["checks"].values()) else "FAIL"} |')
(OUT / 'pythia_regression.md').write_text('\n'.join(lines) + '\n')
print(json.dumps({k: v for k, v in report.items() if k not in ('rows', 'events')}, ensure_ascii=False, indent=2))
assert not report['t4_failures']
