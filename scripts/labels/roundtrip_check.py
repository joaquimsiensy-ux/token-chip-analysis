#!/usr/bin/env python3
"""round-trip 收敛验证：新构建 staging（sources/out/）必须完整覆盖当前发布版（references/labels/）的增量。

背景：add_labels.py 直改发布库、build_labels.py 写 staging，两条写入路径曾造成 5/9 组 md5 不一致
（2026-07-18 稳定化审计实测，发布版均比 staging 新）。v4.2 的 round-trip 机制主张 additions/ 是重建真源；
本脚本证明这一主张：若发布版存在 staging 没有的地址行，说明有增量绕过了 additions/（断环），须先救回再发布。

用法（在 scripts/labels/ 下）：
  python3 roundtrip_check.py            # 全链比对，输出差异摘要
  python3 roundtrip_check.py --dump     # 差异行落盘 roundtrip_diff_<chain>.csv 供救回
退出码：0=收敛（发布版被新构建完整覆盖，可安全发布）；1=断环或行内退化；
        2=任一正式链的发布表或 staging 表缺失。
比对键：(address, chain)；除检查发布版地址是否仍在 staging，也逐行比较全部行为字段。
纯 provenance 字段允许差异但逐项输出 WARN，禁止静默吞掉。
staging 比发布版多行是正常扩容。
"""
import argparse, csv, datetime, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from risk_flags import canonical_risk_flags

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'sources', 'out')
PUB = os.path.normpath(os.path.join(HERE, '..', '..', 'references', 'labels'))
CHAINS = ['eth', 'bsc', 'base', 'sol', 'robinhood']
DECISION_FIELDS = ['category', 'tier', 'merge_policy', 'balance_policy', 'status', 'name',
                   'risk_flags']
PROVENANCE_FIELDS = ['source', 'evidence', 'added_date', 'verified_at',
                     'source_snapshot_at', 'raw_labels']
DIRECTIONAL_DATE_FIELDS = {'added_date', 'verified_at', 'source_snapshot_at'}

def load_keys(path):
    keys = {}
    if not os.path.exists(path):
        return None
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            addr = (row.get('address') or '').strip()
            if addr:
                keys[(addr, (row.get('chain') or '').strip())] = row
    return keys

def parse_args():
    ap = argparse.ArgumentParser(description='检查发布标签与 staging 是否逐行收敛')
    ap.add_argument('--dump', action='store_true', help='把差异行写成 CSV')
    ap.add_argument('--pub-dir', default=PUB, help='发布标签目录（默认 references/labels）')
    ap.add_argument('--out-dir', default=OUT, help='staging 标签目录（默认 sources/out）')
    ap.add_argument('--dump-dir', default=HERE, help='差异 CSV 目录（默认脚本目录）')
    return ap.parse_args()


def _decision(row):
    # risk_flags 是 | 拼接的集合语义：历史存量存在未排序串（2026-08-06 实测
    # privacy 表 59 行），比较前规范化为排序集合，防止"序不同语义同"误伤发布。
    out = {}
    for field in DECISION_FIELDS:
        value = (row.get(field) or '').strip()
        if field == 'risk_flags':
            value = canonical_risk_flags(value)
        out[field] = value
    return out


def _timestamp(value):
    try:
        parsed = datetime.datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed.astimezone(datetime.timezone.utc)
    except (TypeError, ValueError):
        return None


def _write_dump(path, missing, degraded, pub):
    rows = []
    for key in missing:
        item = dict(pub[key])
        item['diff_type'] = 'missing_in_staging'
        rows.append(item)
    for key, old, new, changed in degraded:
        item = dict(old)
        item['diff_type'] = 'row_degraded'
        item['changed_fields'] = '|'.join(changed)
        for field in DECISION_FIELDS:
            item[f'staging_{field}'] = (new.get(field) or '').strip()
        rows.append(item)
    if not rows:
        return
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    broken = False
    missing_table = False
    for ch in CHAINS:
        fn = f'labels-{ch}.csv'
        pub = load_keys(os.path.join(args.pub_dir, fn))
        new = load_keys(os.path.join(args.out_dir, fn))
        if pub is None or new is None:
            missing_table = True
            print(f'[FAIL] {fn}: 缺正式链主表（发布版={pub is not None} staging={new is not None}）')
            continue
        # privacy 子表并入比对（resolver 视角是合并加载的）
        for side, store in (('pub', pub), ('new', new)):
            pv = load_keys(os.path.join(args.pub_dir if side == 'pub' else args.out_dir,
                                        f'labels-{ch}-privacy.csv'))
            if pv:
                store.update(pv)
        missing = [k for k in pub if k not in new]
        degraded = []
        provenance_diffs = []
        date_regressions = []
        for key in pub.keys() & new.keys():
            old_decision = _decision(pub[key])
            new_decision = _decision(new[key])
            changed = [field for field in DECISION_FIELDS
                       if old_decision[field] != new_decision[field]]
            if changed:
                degraded.append((key, pub[key], new[key], changed))
            prov_changed = [field for field in PROVENANCE_FIELDS
                            if (pub[key].get(field) or '').strip()
                            != (new[key].get(field) or '').strip()]
            if prov_changed:
                provenance_diffs.append((key, prov_changed))
            for field in DIRECTIONAL_DATE_FIELDS:
                old_value = (pub[key].get(field) or '').strip()
                new_value = (new[key].get(field) or '').strip()
                if old_value == new_value:
                    continue
                old_ts, new_ts = _timestamp(old_value), _timestamp(new_value)
                if old_ts is not None and new_ts is not None and new_ts < old_ts:
                    date_regressions.append((key, field, old_value, new_value))
        extra = sum(1 for k in new if k not in pub)
        if missing or degraded or date_regressions:
            broken = True
            print(f'[FAIL] {ch}: 丢失增量 {len(missing)} 行；行内退化 {len(degraded)} 行；'
                  f'日期倒退 {len(date_regressions)} 项；新构建净增 {extra} 行')
            for key in missing[:5]:
                print(f'       丢失例: {key[0][:20]}… ({pub[key].get("name", "")} / '
                      f'{pub[key].get("source", "")})')
            for key, old, new_row, changed in degraded[:5]:
                detail = ', '.join(
                    f'{field}={_decision(old)[field]!r}→{_decision(new_row)[field]!r}'
                    for field in changed)
                print(f'       行内退化例: {key[0][:20]}… {detail}')
            if degraded:
                print(f'       行内退化总数: {len(degraded)}')
            for key, field, old_value, new_value in date_regressions[:5]:
                print(f'       日期倒退例: {key[0][:20]}… {field}={old_value!r}→{new_value!r}')
            if args.dump:
                dp = os.path.join(args.dump_dir, f'roundtrip_diff_{ch}.csv')
                _write_dump(dp, missing, degraded, pub)
                print(f'       差异已落盘 {dp}')
        else:
            print(f'[PASS] {ch}: 发布版 {len(pub)} 行全部被新构建覆盖（新构建净增 {extra} 行）')
        if provenance_diffs:
            fields = sorted({field for _, changed in provenance_diffs for field in changed})
            print(f'[WARN] {ch}: {len(provenance_diffs)} 行 provenance 差异；字段={"|".join(fields)}'
                  '（允许差异，需人工确认来源迁移）')
    if missing_table:
        print('\n结论：正式链标签表不完整——缺表属于发布前置条件失败，禁止发布。')
        return 2
    if broken:
        print('\n结论：round-trip 未收敛——先把丢失或退化行救回 additions/ 再重建，勿直接 cp 发布。')
        return 1
    print('\n结论：round-trip 收敛，可安全发布（cp out/labels-*.csv → references/labels/）。')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except ValueError as exc:
        print(f'BLOCK: risk_flags 脏数据: {exc}', file=sys.stderr)
        raise SystemExit(2)
