#!/usr/bin/env python3
"""CHANGELOG 守护：版本号唯一性 + 排列顺序 + 日期格式。

背景（都实际发生过，2026-07-18 稳定化审计实证）：
- 2.21.0 撞号 ×2：2026-07-17 两个并行会话各自 +1（git 化前无并发防护）
- 2.24.0/2.25.0 物理倒排：同日并行会话插入位置错位
复盘写入 CHANGELOG 前必跑本脚本（retrospective 步骤 4）；FAIL 先修再写。

用法：python3 scripts/tests/changelog_lint.py   （在 skill 根目录或任意位置均可）
退出码：0=PASS；1=FAIL。
"""
import os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ACTIVE = os.path.join(ROOT, 'CHANGELOG.md')
ARCHIVE = os.path.join(ROOT, 'archive', 'CHANGELOG-archive.md')

# 历史事故白名单：已发生且按"不改写历史"原则保留原号的重复（新增撞号不豁免）
KNOWN_DUP_OK = {('2.21.0', '2026-07-17'), ('3.36.0', '2026-07-26')}

VER_RE = re.compile(r'^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})')

def parse(path):
    out = []
    if not os.path.exists(path):
        return out
    for i, line in enumerate(open(path, encoding='utf-8'), 1):
        m = VER_RE.match(line)
        if m:
            out.append((m.group(1), m.group(2), i, os.path.basename(path)))
        elif line.startswith('## [') :
            print(f'FAIL: {os.path.basename(path)}:{i} 版本行格式非法（应为 "## [x.y.z] - YYYY-MM-DD — 标题"）: {line[:60]}')
            return None
    return out

def vtuple(v):
    return tuple(int(x) for x in v.split('.'))

def main():
    active = parse(ACTIVE)
    archive = parse(ARCHIVE)
    if active is None or archive is None:
        return 1
    if not active:
        print(f'FAIL: {ACTIVE} 没有任何版本条目'); return 1
    fails = []

    # 1) 全局唯一性（活跃+归档合并；同版本恰好落在白名单的放行）
    seen = {}
    for v, d, ln, fn in active + archive:
        key = v
        if key in seen and (v, d) not in KNOWN_DUP_OK:
            pv, pd, pln, pfn = seen[key]
            fails.append(f'版本号重复: [{v}] 出现在 {pfn}:{pln}({pd}) 与 {fn}:{ln}({d})——并行会话撞号？后写者请顺延次版本')
        seen.setdefault(key, (v, d, ln, fn))

    # 2) 顺序：活跃文件内新在上（严格降序；白名单重复对允许相等）
    for a, b in zip(active, active[1:]):
        va, vb = vtuple(a[0]), vtuple(b[0])
        if va < vb or (va == vb and (a[0], a[1]) not in KNOWN_DUP_OK):
            fails.append(f'顺序倒排: [{a[0]}]({a[3]}:{a[2]}) 排在 [{b[0]}] 之上但版本更小——新条目应插在文件最上方')
    # 3) 归档文件也查顺序（宽松：只查降序破坏）
    for a, b in zip(archive, archive[1:]):
        if vtuple(a[0]) < vtuple(b[0]):
            fails.append(f'归档顺序倒排: [{a[0]}]({a[3]}:{a[2]}) 在 [{b[0]}] 之上')
    # 4) 活跃窗口最旧版本必须 ≥ 归档最新版本（拆分边界不重叠）
    if archive and vtuple(active[-1][0]) < vtuple(archive[0][0]):
        fails.append(f'活跃/归档边界重叠: 活跃最旧 [{active[-1][0]}] < 归档最新 [{archive[0][0]}]')

    if fails:
        for f in fails:
            print('FAIL:', f)
        return 1
    print(f'PASS: 版本号唯一（豁免 {len(KNOWN_DUP_OK)} 组历史撞号存档）、顺序正确；活跃 {len(active)} 条 + 归档 {len(archive)} 条')
    return 0

if __name__ == '__main__':
    sys.exit(main())
