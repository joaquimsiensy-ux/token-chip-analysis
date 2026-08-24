#!/usr/bin/env python3
"""标签库回归基准（P2，codex 复核融合 2026-07-16）——以效果指标评估库，而非行数。

指标：
  错误 exclude 率   entity 金标（实战确认的庄家/项目方地址）被库标成 exclude 的数量。
                    【必须为 0】——>0 意味着聚类阶段会直接漏庄，exit 1。
  infra 召回率      infrastructure 金标命中 no_merge 的比例。manual-layer 来源应 100%
                    （防重建退化）；appendix 来源反映批量层对实战设施的覆盖。
  identity 标注率   entity 金标里被库标注为身份（kol/fund 等）的比例（信息项，不设阈值）。

用法：
  python3 benchmark_labels.py                 # 用默认 goldset.csv，只打印
  python3 benchmark_labels.py --save          # 另存结果 JSON 到 benchmark/（对比历史）
扩容/重建后必跑：错误 exclude 没上升、manual 召回 100%、infra 召回不降，才允许发布。
"""
import csv, json, os, sys, datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from labels_resolver import LabelResolver

BENCH_DIR = os.path.normpath(os.path.join(_HERE, '..', '..', 'references', 'labels', 'benchmark'))
DEFAULT_LABELS_DIR = os.path.normpath(os.path.join(_HERE, '..', '..', 'references', 'labels'))
EXPECTED_CHAINS = ('eth', 'bsc', 'base', 'arbitrum', 'sol', 'robinhood')


def require_complete_labels(labels_dir):
    """注册为 labels_table 的六张主表必须存在且至少有一条数据行。"""
    bad = []
    for chain in EXPECTED_CHAINS:
        path = os.path.join(labels_dir, f'labels-{chain}.csv')
        if not os.path.isfile(path):
            bad.append(f'{chain}:缺失')
            continue
        try:
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                has_row = next(reader, None) is not None
        except (OSError, UnicodeError, csv.Error):
            has_row = False
        if not has_row:
            bad.append(f'{chain}:空表')
    if bad:
        print(f'FAIL: 六条 labels_table 链标签主表必须齐全且非空：{"; ".join(bad)}')
        return False
    return True


def main():
    gs_path = os.path.join(BENCH_DIR, 'goldset.csv')
    labels_dir = None      # 【v4.2】--labels-dir=out 支持对重建产物预检（发布前过门禁）
    for a in sys.argv[1:]:
        if a.startswith('--labels-dir='):
            labels_dir = a.split('=', 1)[1]
        elif not a.startswith('--'):
            gs_path = a
    if not os.path.exists(gs_path):
        print(f'FAIL: 金标集不存在 {gs_path}（先跑 build_goldset.py）'); sys.exit(1)
    effective_labels_dir = labels_dir if labels_dir is not None else DEFAULT_LABELS_DIR
    if not require_complete_labels(effective_labels_dir):
        sys.exit(2)

    rows = list(csv.DictReader(open(gs_path)))
    by_chain = {}
    for r in rows:
        by_chain.setdefault(r['chain'], []).append(r)

    # 发布标签表覆盖的六链必须全部有金标；缺链不得静默 PASS。
    missing = set(EXPECTED_CHAINS) - set(by_chain)
    if missing:
        print(f'FAIL: goldset 缺链 {sorted(missing)}——该链零金标=零门禁，先重跑 build_goldset.py')
        sys.exit(1)

    result = {'date': datetime.date.today().isoformat(), 'goldset': os.path.basename(gs_path),
              'total': len(rows), 'chains': {}, 'violations': [], 'weak_gate_chains': []}
    total_violation = 0
    WEAK_GATE_MIN = 10        # entity+random-eoa 合计低于此数 → 该链门禁弱，显式声明
    for chain, items in sorted(by_chain.items()):
        resv = LabelResolver(chain, labels_dir=labels_dir)
        ent = [r for r in items if r['expected'] == 'entity']
        rnd = [r for r in items if r['expected'] == 'random-eoa']
        inf = [r for r in items if r['expected'] == 'infrastructure']
        inf_manual = [r for r in inf if r['source_analysis'] == 'manual-layer']
        inf_field = [r for r in inf if r['source_analysis'] != 'manual-layer']

        viol, viol_rnd = [], []
        ident = 0
        for r in ent:
            if resv.is_exclude(r['address']):
                viol.append(r)
            else:
                row = resv.get(r['address'])
                if row and not row['cross_chain'] and row['tier'] == 'identity':
                    ident += 1
        for r in rnd:
            if resv.is_exclude(r['address']):
                viol_rnd.append(r)
        hit_manual = [r for r in inf_manual if resv.no_merge(r['address'])]
        hit_field = [r for r in inf_field if resv.no_merge(r['address'])]

        manual_miss = [r for r in inf_manual if r not in hit_manual]
        total_violation += len(viol) + len(viol_rnd) + len(manual_miss)
        result['violations'] += [{'chain': chain, **r} for r in viol + viol_rnd]
        result['violations'] += [{'chain': chain, 'violation': 'manual-infra-miss', **r}
                                 for r in manual_miss]
        weak = (len(ent) + len(rnd)) < WEAK_GATE_MIN
        if weak:
            result['weak_gate_chains'].append(chain)
        result['chains'][chain] = {
            'entity': len(ent), 'entity_wrong_exclude': len(viol), 'entity_identity_tagged': ident,
            'random_eoa': len(rnd), 'random_eoa_wrong_exclude': len(viol_rnd),
            'infra_manual': len(inf_manual), 'infra_manual_hit': len(hit_manual),
            'infra_field': len(inf_field), 'infra_field_hit': len(hit_field),
            'weak_gate': weak,
        }
        mm = f'{len(hit_manual)}/{len(inf_manual)}' if inf_manual else '-'
        ff = f'{len(hit_field)}/{len(inf_field)}' if inf_field else '-'
        wtag = '  ⚠️弱门禁（负样本不足，此链 PASS 不代表有防线）' if weak else ''
        print(f'[{chain}] entity {len(ent)} + random-eoa {len(rnd)}: 错误exclude {len(viol)}+{len(viol_rnd)}'
              f' | 身份标注 {ident} || infra 召回 manual {mm} / 实战 {ff}{wtag}')
        for r in viol + viol_rnd:
            row = resv.get(r['address'])
            print(f'    !! 错误exclude: {r["address"]} 金标={r["note"][:40]}({r["source_analysis"]})'
                  f' 库标={row["name"][:40]}<{row["category"]}>')
        for r in manual_miss:
            print(f'    !! manual 设施未命中(重建退化?): {r["address"]}')

    if '--save' in sys.argv:
        os.makedirs(BENCH_DIR, exist_ok=True)
        out = os.path.join(BENCH_DIR, f'result-{result["date"]}.json')
        json.dump(result, open(out, 'w'), ensure_ascii=False, indent=1)
        print(f'\n结果已存 {out}')

    if total_violation:
        print(f'\nFAIL: {total_violation} 条硬断言违例（错误 exclude 或 manual 设施未命中）——'
              '发布前必须修复')
        sys.exit(1)
    weak = result['weak_gate_chains']
    print('\nPASS: 错误 exclude = 0'
          + (f'（注意：{"/".join(weak)} 为弱门禁链——金标不足，PASS 不代表该链有防线）' if weak else ''))


if __name__ == '__main__':
    main()
