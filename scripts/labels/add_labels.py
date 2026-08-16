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
import csv, datetime, os, shutil, subprocess, sys, tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from labels_resolver import DEFAULT_LABELS_DIR, norm_addr, BASE_FIELDS, V4_OPTIONAL_FIELDS
from risk_flags import canonical_risk_flags, merge_risk_flags

FIELDS = BASE_FIELDS + V4_OPTIONAL_FIELDS
# curation 必须在列（3.19.1 修）：它是 build_labels SRC_PRIORITY 的最高层(-1)，此前缺席导致
# curation override 增量入库压不掉已存在的 serial/manual 行（只补空字段）——QUQ 0x238a
# 设施身份恢复实测踩中；增量与全量重建的覆盖语义自此一致。
HIGH_TRUST_PREFIX = ('curation', 'manual', 'registry', 'serial', 'official')
ADDITIONS_DIR = os.path.join(_HERE, 'sources', 'additions')


def archive_stamp():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


def stage_archive(src):
    """Copy source to a private additions staging path and reserve a unique final name."""
    add_dir = os.path.abspath(ADDITIONS_DIR)
    src_abs = os.path.abspath(src)
    os.makedirs(add_dir, exist_ok=True)
    if os.path.dirname(src_abs) == add_dir:
        return None, None
    base = os.path.basename(src_abs)
    target = os.path.join(add_dir, base)
    if os.path.exists(target):
        if os.path.samefile(src_abs, target):
            return None, None
        stem, ext = os.path.splitext(base)
        target = os.path.join(add_dir, f'{stem}_{archive_stamp()}{ext}')
        if os.path.exists(target):
            raise FileExistsError(f'补录归档目标二次重名，拒绝覆盖: {target}')
    fd, staging = tempfile.mkstemp(dir=add_dir, prefix=f'.{os.path.basename(target)}.staging-',
                                   suffix='.tmp')
    os.close(fd)
    try:
        shutil.copy(src_abs, staging)
    except BaseException:
        if os.path.exists(staging):
            os.remove(staging)
        raise
    return staging, target


def rollback(adds, target_was_present, manifest_path, manifest_backup, manifest_was_present):
    restored, removed = [], []
    for ch in adds:
        p = os.path.join(DEFAULT_LABELS_DIR, f'labels-{ch}.csv')
        if target_was_present.get(ch) and os.path.exists(p + '.bak'):
            shutil.move(p + '.bak', p); restored.append(ch)
        elif not target_was_present.get(ch) and os.path.exists(p):
            os.remove(p); removed.append(ch)
    if manifest_was_present and manifest_backup and os.path.exists(manifest_backup):
        shutil.move(manifest_backup, manifest_path)
    elif not manifest_was_present and os.path.exists(manifest_path):
        os.remove(manifest_path)
    if manifest_backup and os.path.exists(manifest_backup):
        os.remove(manifest_backup)
    return restored, removed


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
                print(f'!! 非法地址（chain={ch}）: {r["address"]}'); return 1
            r['address'] = na
            for k in FIELDS:
                r.setdefault(k, '')
            r['risk_flags'] = canonical_risk_flags(r.get('risk_flags'))
            adds.setdefault(ch, {})[na] = r

    archive_staging = archive_target = None
    if not dry:
        try:
            archive_staging, archive_target = stage_archive(src)
        except Exception as exc:
            print(f'!! 补录归档 staging 失败，尚未修改发布库: {exc}', file=sys.stderr)
            return 1

    target_was_present = {
        ch: os.path.exists(os.path.join(DEFAULT_LABELS_DIR, f'labels-{ch}.csv'))
        for ch in adds
    }
    manifest_path = os.path.join(DEFAULT_LABELS_DIR, 'manifest.json')
    manifest_was_present = os.path.exists(manifest_path)
    manifest_backup = None
    try:
        if not dry and manifest_was_present:
            mf = tempfile.NamedTemporaryFile(delete=False, dir=DEFAULT_LABELS_DIR,
                                             prefix='.manifest-add-labels-', suffix='.bak')
            mf.close(); shutil.copyfile(manifest_path, mf.name); manifest_backup = mf.name
    except Exception as exc:
        if archive_staging and os.path.exists(archive_staging):
            os.remove(archive_staging)
        print(f'!! manifest 备份失败，尚未修改发布库: {exc}', file=sys.stderr)
        return 1
    failed = None
    archive_published = False
    try:
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
            old['risk_flags'] = merge_risk_flags(
                old.get('risk_flags'), add.get('risk_flags'))
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
        for row in rows:
            row['risk_flags'] = canonical_risk_flags(row.get('risk_flags'))
        w = csv.DictWriter(tmp, fieldnames=out_fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)
        tmp.close()
        # 落盘前备份原表——validate FAIL 时据此真回滚（2026-07-17 修复:
        # 旧版只打印"从备份恢复"但从未备份,坏行会滞留主库,TRASH 增量入库实测踩中）
        if os.path.exists(path):
            shutil.copy(path, path + '.bak')
        shutil.move(tmp.name, path)

      if not dry:
        gates = [
            ('validate', [sys.executable, os.path.join(_HERE, 'validate_labels.py')]),
            ('benchmark', [sys.executable, os.path.join(_HERE, 'benchmark_labels.py')]),
            ('manifest', [sys.executable, os.path.join(_HERE, '..', 'tests',
                                                        'labels_manifest.py'), '--write']),
        ]
        for name, cmd in gates:
            if subprocess.run(cmd).returncode != 0:
                failed = name
                raise RuntimeError(f'{name} 门禁 FAIL')
        if archive_staging:
            os.link(archive_staging, archive_target)
            archive_published = True
            os.remove(archive_staging)
            archive_staging = None
            print(f'已归档补录文件 → {archive_target}（重建流自动回放，请勿删除）')
    except Exception as exc:
        failed = failed or f'事务异常: {exc}'
        if not dry:
            if archive_published and archive_target and os.path.exists(archive_target):
                os.remove(archive_target)
            if archive_staging and os.path.exists(archive_staging):
                os.remove(archive_staging)
            restored, removed = rollback(adds, target_was_present, manifest_path,
                                         manifest_backup, manifest_was_present)
            print(f'!! 合并后 {failed}——已恢复原表 {restored or "[]"}；'
                  f'已删除新建坏表 {removed or "[]"}；manifest 已恢复；归档 staging 已清理。'
                  '排查后重试', file=sys.stderr)
        return 1

    if not dry:
        if failed:
            return 1
        for ch in adds:
            p = os.path.join(DEFAULT_LABELS_DIR, f'labels-{ch}.csv') + '.bak'
            if os.path.exists(p):
                os.remove(p)
        if manifest_backup and os.path.exists(manifest_backup):
            os.remove(manifest_backup)
        print('合并完成：validate + benchmark + manifest 三闸全部通过。')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except ValueError as exc:
        print(f'BLOCK: risk_flags 脏数据: {exc}', file=sys.stderr)
        raise SystemExit(2)
