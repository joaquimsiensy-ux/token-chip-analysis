#!/usr/bin/env python3
"""增量入库工具（v4）：把一份补录 CSV 合并进 references/labels/ 现库，免全量重建。

用法：
  python3 add_labels.py additions.csv            # 合并 + 自动 validate + 摘要
  python3 add_labels.py additions.csv --dry      # 只看将发生什么

additions.csv 列（缺省列自动补空）：
  address,chain,name,category,tier,source,added_date,evidence,risk_flags[,merge_policy,
  balance_policy,source_snapshot_at,verified_at,status,raw_labels]
规则：
  - 地址按链规范化（EVM 小写）；不合法行拒绝并报错
  - 同址已存在：name/evidence 择优（新条目为 manual/registry 级则覆盖），source 合并，
    risk_flags 并集；tier/category 冲突时【manual/registry 级新条目覆盖，其他保留并警告】
  - 写回后强制 validate_labels.py，FAIL 则还原（写临时文件校验通过才落盘）
"""
import csv, os, shutil, subprocess, sys, tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from labels_resolver import DEFAULT_LABELS_DIR, norm_addr, BASE_FIELDS, V4_OPTIONAL_FIELDS

FIELDS = BASE_FIELDS + V4_OPTIONAL_FIELDS
HIGH_TRUST_PREFIX = ('manual', 'registry', 'serial', 'official')


def load_chain(chain):
    path = os.path.join(DEFAULT_LABELS_DIR, f'labels-{chain}.csv')
    rows, header = [], FIELDS
    if os.path.exists(path):
        with open(path, newline='') as f:
            rd = csv.DictReader(f)
            header = rd.fieldnames
            rows = list(rd)
    return path, header, rows


def main():
    src = sys.argv[1]
    dry = '--dry' in sys.argv
    adds = {}
    with open(src, newline='') as f:
        for r in csv.DictReader(f):
            ch = r['chain'].strip()
            na = norm_addr(r['address'], ch)
            if not na:
                print(f'!! 非法地址（chain={ch}）: {r["address"]}'); sys.exit(1)
            r['address'] = na
            for k in FIELDS:
                r.setdefault(k, '')
            adds.setdefault(ch, {})[na] = r

    for ch, items in sorted(adds.items()):
        path, header, rows = load_chain(ch)
        # 主表可能还是 9 列旧头（新链首建则用全 15 列）
        out_fields = header if header and 'merge_policy' in header else FIELDS
        idx = {r['address']: r for r in rows}
        n_new = n_merge = 0
        for na, add in items.items():
            old = idx.get(na)
            if old is None:
                rows.append({k: add.get(k, '') for k in out_fields})
                idx[na] = rows[-1]
                n_new += 1
                continue
            n_merge += 1
            high = add['source'].split('-')[0] in HIGH_TRUST_PREFIX
            if add['source'] and add['source'] not in old.get('source', ''):
                old['source'] = (old.get('source', '') + '+' + add['source']).strip('+')
            flags = {f for f in (old.get('risk_flags') or '').split('|') if f}
            flags |= {f for f in (add.get('risk_flags') or '').split('|') if f}
            old['risk_flags'] = '|'.join(sorted(flags))
            if high:
                if (old.get('category'), old.get('tier')) != (add['category'], add['tier']):
                    print(f'  ~ {ch} {na[:14]} 分类覆盖: {old.get("category")}/{old.get("tier")}'
                          f' → {add["category"]}/{add["tier"]}（高置信新条目）')
                for k in ('name', 'category', 'tier', 'evidence', 'verified_at', 'added_date'):
                    if add.get(k):
                        old[k] = add[k]
                for k in ('merge_policy', 'balance_policy', 'source_snapshot_at', 'status'):
                    if add.get(k) and k in old:
                        old[k] = add[k]
            else:
                if not old.get('name') and add.get('name'):
                    old['name'] = add['name']
                if not old.get('evidence') and add.get('evidence'):
                    old['evidence'] = add['evidence']
        print(f'[{ch}] 新增 {n_new} | 合并进已有行 {n_merge} | 总 {len(rows)}')
        if dry:
            continue
        tmp = tempfile.NamedTemporaryFile('w', delete=False, newline='',
                                          suffix=f'-labels-{ch}.csv')
        w = csv.DictWriter(tmp, fieldnames=out_fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)
        tmp.close()
        # 落盘前备份原表——validate FAIL 时据此真回滚（2026-07-17 修复:
        # 旧版只打印"从备份恢复"但从未备份,坏行会滞留主库,TRASH 增量入库实测踩中）
        if os.path.exists(path):
            shutil.copy(path, path + '.bak')
        shutil.move(tmp.name, path)

    if not dry:
        rc = subprocess.run([sys.executable, os.path.join(_HERE, 'validate_labels.py')]).returncode
        if rc != 0:
            restored = []
            for ch in adds:
                p = os.path.join(DEFAULT_LABELS_DIR, f'labels-{ch}.csv')
                if os.path.exists(p + '.bak'):
                    shutil.move(p + '.bak', p)
                    restored.append(ch)
            print(f'!! 合并后校验 FAIL——已自动回滚 {restored or "（无备份可回滚!）"}，排查补录数据后重试',
                  file=sys.stderr)
            sys.exit(1)
        for ch in adds:
            p = os.path.join(DEFAULT_LABELS_DIR, f'labels-{ch}.csv') + '.bak'
            if os.path.exists(p):
                os.remove(p)
        # v4.2：入库成功的补录文件自动归档进 sources/additions/——该目录整目录参与全量重建
        # （build_labels.py 6f 段），否则下次重建会静默丢掉本次增量（v4.1 七份文件实测踩坑）。
        add_dir = os.path.join(_HERE, 'sources', 'additions')
        os.makedirs(add_dir, exist_ok=True)
        src_abs = os.path.abspath(src)
        if os.path.dirname(src_abs) != os.path.abspath(add_dir):
            dst = os.path.join(add_dir, os.path.basename(src_abs))
            if os.path.exists(dst) and not os.path.samefile(src_abs, dst):
                stem, ext = os.path.splitext(os.path.basename(src_abs))
                import datetime
                dst = os.path.join(add_dir, f'{stem}_{datetime.date.today().isoformat()}{ext}')
            shutil.copy(src_abs, dst)
            print(f'已归档补录文件 → {dst}（重建流自动回放，请勿删除）')
        print('合并完成，校验通过。别忘了跑 benchmark_labels.py')


if __name__ == '__main__':
    main()
