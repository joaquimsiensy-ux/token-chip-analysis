#!/usr/bin/env python3
"""round-trip 收敛验证：新构建 staging（sources/out/）必须完整覆盖当前发布版（references/labels/）的增量。

背景：add_labels.py 直改发布库、build_labels.py 写 staging，两条写入路径曾造成 5/9 组 md5 不一致
（2026-07-18 稳定化审计实测，发布版均比 staging 新）。v4.2 的 round-trip 机制主张 additions/ 是重建真源；
本脚本证明这一主张：若发布版存在 staging 没有的地址行，说明有增量绕过了 additions/（断环），须先救回再发布。

用法（在 scripts/labels/ 下）：
  python3 roundtrip_check.py            # 全链比对，输出差异摘要
  python3 roundtrip_check.py --dump     # 差异行落盘 roundtrip_diff_<chain>.csv 供救回
退出码：0=收敛（发布版 ⊆ 新构建，可安全发布）；1=断环（有丢失增量）。
比对键：(address, chain)；只比"发布版有而新构建没有"的方向——staging 比发布版多行是正常扩容。
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'sources', 'out')
PUB = os.path.normpath(os.path.join(HERE, '..', '..', 'references', 'labels'))
CHAINS = ['eth', 'bsc', 'base', 'sol', 'robinhood']

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

def main():
    dump = '--dump' in sys.argv
    broken = False
    for ch in CHAINS:
        fn = f'labels-{ch}.csv'
        pub = load_keys(os.path.join(PUB, fn))
        new = load_keys(os.path.join(OUT, fn))
        if pub is None or new is None:
            print(f'[WARN] {fn}: 缺文件（发布版={pub is not None} staging={new is not None}），跳过')
            continue
        # privacy 子表并入比对（resolver 视角是合并加载的）
        for side, store in (('pub', pub), ('new', new)):
            pv = load_keys(os.path.join(PUB if side == 'pub' else OUT, f'labels-{ch}-privacy.csv'))
            if pv:
                store.update(pv)
        missing = [k for k in pub if k not in new]
        extra = sum(1 for k in new if k not in pub)
        if missing:
            broken = True
            print(f'[FAIL] {ch}: 发布版有 {len(missing)} 行不在新构建中（丢失增量）；新构建净增 {extra} 行')
            if dump:
                dp = os.path.join(HERE, f'roundtrip_diff_{ch}.csv')
                with open(dp, 'w', newline='', encoding='utf-8') as f:
                    w = None
                    for k in missing:
                        row = pub[k]
                        if w is None:
                            w = csv.DictWriter(f, fieldnames=list(row.keys()))
                            w.writeheader()
                        w.writerow(row)
                print(f'       差异已落盘 {dp}')
            else:
                for k in missing[:5]:
                    print(f'       例: {k[0][:20]}… ({pub[k].get("name","")} / {pub[k].get("source","")})')
        else:
            print(f'[PASS] {ch}: 发布版 {len(pub)} 行全部被新构建覆盖（新构建净增 {extra} 行）')
    if broken:
        print('\n结论：round-trip 断环——先把差异行救回 additions/（add_labels 的 canonical 路径）再重建，勿直接 cp 发布。')
        return 1
    print('\n结论：round-trip 收敛，可安全发布（cp out/labels-*.csv → references/labels/）。')
    return 0

if __name__ == '__main__':
    sys.exit(main())
