#!/usr/bin/env python3
"""实体身份硬闸（G8 数据源，v4.2 2026-07-30）——实体判级冻结前的强制身份四查。

血案背景（本闸的存在理由，三案同族复发）：
  IQ 2026-07-26   Upbit 交易所托管 58.5% → 误判"大庄#1"（还污染了惯犯库）
  LPT 2026-07-21  Bitvavo 质押产品 6.96% → 初判"最大神秘巨鲸"（复核才翻案）
  PYTHIA 2026-07-29 币安 Alpha 库存仓 16.72% → 误判"小庄#1"（地址簿里明明有现成答案）
共性：大额持仓的"身份排除项"（交易所托管/质押产品/PDA 设施）没有被强制先查。
文字教训写过三轮全部衰减——本脚本把它变成机械闸：**无 gate 记录/有未解决 flag，
build_html G8 直接 WARN（有 WARN 不许交付），报告物理上编不出来。**

用法：
  生成：python3 entity_identity_gate.py --state analysis-state.json --chain sol \
            [--snapshot holders_owners.json] [--out identity_gate.json]
  校验：python3 entity_identity_gate.py --check identity_gate.json   # exit 1=有未解决 flag

对每个实体地址（+快照现仓 ≥1% 的所有单址）产出四查记录：
  label     : LabelResolver 双源查询（CSV 主库 + address-book.md 手工层）
  on_curve  : Solana 链 ed25519 曲线判定（EVM 为 null）
  flag      : 需要显式回答的身份疑点——
              INFRA_IN_ENTITY  标签命中设施/CEX 却被列入实体成员（红线级）
              PDA_UNRESOLVED   off-curve 无标签（谁的程序/多签？必须解释）
              BIG_UNLABELED    ≥1% 大仓无标签（托管假设过了吗？）
  resolution: 分析者对 flag 的显式回答（生成时为空；分析流程逐条填写后才可过闸）

resolution 填写纪律：不是走过场——每条必须写"查了什么、结论是什么"
（如"Alpha 集齐率 3/70 不是托管仓；gas 溯源独立"或"Squads 2-of-2 多签，成员 X+Y"）。
"""
import argparse, json, os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, '..', 'labels')))

P = 2**255 - 19
D = (-121665 * pow(121666, P - 2, P)) % P
_B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
_B58IDX = {c: i for i, c in enumerate(_B58)}


def _b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + _B58IDX[c]
    raw = n.to_bytes((n.bit_length() + 7) // 8, 'big')
    pad = len(s) - len(s.lstrip('1'))
    return b'\x00' * pad + raw


def is_on_curve(addr):
    """ed25519 解压判定（curve25519-dalek decompress 等价）。非法 base58 返回 None。"""
    try:
        b = _b58decode(addr)
    except KeyError:
        return None
    if len(b) != 32:
        return None
    y = int.from_bytes(b, 'little') & ((1 << 255) - 1)
    if y >= P:
        return False
    yy = y * y % P
    u, v = (yy - 1) % P, (D * yy + 1) % P
    xx = u * pow(v, P - 2, P) % P
    x = pow(xx, (P + 3) // 8, P)
    if x * x % P != xx:
        x = x * pow(2, (P - 1) // 4, P) % P
        if x * x % P != xx:
            return False
    if x == 0 and (b[31] >> 7) == 1:
        return False
    return True


BIG_SHARE = 0.01   # 快照单址 ≥1% 总供应即入闸


def build(state_path, chain, snapshot_path=None, out_path=None):
    from labels_resolver import LabelResolver
    state = json.load(open(state_path))
    resolver = LabelResolver(chain)
    resolver.warn_if_degraded()

    targets = {}   # addr -> {entity, share}
    for g in state.get('whale_groups', []):
        for a in g.get('addresses', []):
            targets[a] = {'entity': g.get('entity_id', '?'), 'share': None}
    if snapshot_path:
        snap = json.load(open(snapshot_path))
        total = sum(snap.values())
        if total > 0:
            for a, v in snap.items():
                if v / total >= BIG_SHARE and a not in targets:
                    targets[a] = {'entity': '(non-entity big holder)',
                                  'share': round(v / total * 100, 3)}

    rows = []
    for a, meta in sorted(targets.items()):
        row = resolver.get(a)
        oc = is_on_curve(a) if chain == 'sol' else None
        label = None
        flag = ''
        if row:
            label = {'name': row.get('name'), 'category': row.get('category'),
                     'tier': row.get('tier'), 'source': row.get('source')}
            if row.get('tier') == 'exclude' and meta['entity'] != '(non-entity big holder)':
                flag = 'INFRA_IN_ENTITY'
        else:
            if oc is False:
                flag = 'PDA_UNRESOLVED'
            elif meta['share'] is not None or meta['entity'] != '(non-entity big holder)':
                # 实体成员或 ≥1% 大仓且无标签：必须显式过一遍托管/设施假设
                flag = 'BIG_UNLABELED' if (meta['share'] or 0) >= 1 else ''
        rows.append({'address': a, 'entity': meta['entity'], 'share_pct': meta['share'],
                     'label': label, 'on_curve': oc, 'flag': flag, 'resolution': ''})

    gate = {'schema': 'identity_gate_v1', 'chain': chain,
            'state_file': os.path.basename(state_path),
            'n_addresses': len(rows),
            'n_flags': sum(1 for r in rows if r['flag']),
            'rows': rows}
    out = out_path or os.path.join(os.path.dirname(os.path.abspath(state_path)),
                                   'identity_gate.json')
    json.dump(gate, open(out, 'w'), ensure_ascii=False, indent=1)
    print(f"[identity_gate] {len(rows)} 址入闸，{gate['n_flags']} 个 flag 待解决 → {out}")
    for r in rows:
        if r['flag']:
            print(f"  [{r['flag']}] {r['address']}  entity={r['entity']}"
                  + (f" share={r['share_pct']}%" if r['share_pct'] else ''))
    return gate


def check(gate_path):
    gate = json.load(open(gate_path))
    unresolved = [r for r in gate.get('rows', []) if r.get('flag') and not str(r.get('resolution', '')).strip()]
    if unresolved:
        print(f"[identity_gate][FAIL] {len(unresolved)} 个身份疑点未解决：")
        for r in unresolved:
            print(f"  [{r['flag']}] {r['address']} entity={r['entity']}")
        return 1
    print(f"[identity_gate][PASS] {gate.get('n_addresses', 0)} 址全部过闸")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state')
    ap.add_argument('--chain')
    ap.add_argument('--snapshot')
    ap.add_argument('--out')
    ap.add_argument('--check', help='校验模式：identity_gate.json 路径')
    a = ap.parse_args()
    if a.check:
        sys.exit(check(a.check))
    if not (a.state and a.chain):
        ap.error('生成模式需要 --state 与 --chain')
    build(a.state, a.chain, a.snapshot, a.out)


if __name__ == '__main__':
    main()
