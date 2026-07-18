#!/usr/bin/env python3
"""发布标签库校验和 manifest：发布时落印，分析/维护时验印。

目的：references/labels/ 是唯一发布真相（双真相事故 2026-07-18 已收敛）——manifest 把"发布时刻
的文件指纹"固化下来，此后任何绕过发布流程的直改（手编 CSV、误 cp、半成品覆盖）在下次校验时现形。
- 发布流程末尾：python3 scripts/tests/labels_manifest.py --write   （MAINTENANCE.md 重建步骤已挂）
- 分析开工/复盘收尾：python3 scripts/tests/labels_manifest.py      （校验模式）
- add_labels.py 增量入库后也应 --write（发布库合法变更的落印）
退出码：0=一致；1=有文件与 manifest 不符（先查谁改的、按 MAINTENANCE 流程重放，再决定重写印）。
"""
import glob, hashlib, json, os, sys, time

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
PUB = os.path.join(ROOT, 'references', 'labels')
MANIFEST = os.path.join(PUB, 'manifest.json')

def fingerprint():
    out = {}
    for p in sorted(glob.glob(os.path.join(PUB, 'labels-*.csv')) + glob.glob(os.path.join(PUB, 'codehash-*.csv'))):
        h = hashlib.sha256()
        rows = -1  # 表头不计
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        with open(p, encoding='utf-8', errors='replace') as f:
            for rows, _ in enumerate(f):
                pass
        out[os.path.basename(p)] = {'sha256': h.hexdigest(), 'rows': rows, 'bytes': os.path.getsize(p)}
    return out

def main():
    cur = fingerprint()
    if not cur:
        print(f'FAIL: {PUB} 下没有任何标签表'); return 1
    if '--write' in sys.argv:
        doc = {'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'files': cur}
        json.dump(doc, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'manifest 已落印: {len(cur)} 个文件 @ {doc["generated_at"]}')
        return 0
    if not os.path.exists(MANIFEST):
        print('FAIL: manifest.json 不存在——先在一次可信发布后 --write 落印'); return 1
    doc = json.load(open(MANIFEST, encoding='utf-8'))
    old = doc.get('files', {})
    fails = []
    for name, meta in cur.items():
        if name not in old:
            fails.append(f'新文件未落印: {name}（{meta["rows"]} 行）')
        elif meta['sha256'] != old[name]['sha256']:
            fails.append(f'指纹不符: {name}（manifest {old[name]["rows"]} 行 → 现 {meta["rows"]} 行）——发布库被 manifest 之外的路径改动')
    for name in old:
        if name not in cur:
            fails.append(f'文件消失: {name}')
    if fails:
        for f in fails:
            print('FAIL:', f)
        print(f'（manifest 落印于 {doc.get("generated_at","?")}；合法变更请走 MAINTENANCE 发布流程后 --write）')
        return 1
    print(f'PASS: {len(cur)} 个发布表与 manifest（{doc.get("generated_at","?")}）指纹一致')
    return 0

if __name__ == '__main__':
    sys.exit(main())
