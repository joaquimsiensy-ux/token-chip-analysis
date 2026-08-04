#!/usr/bin/env python3
"""实体身份硬闸（G8 数据源，v4.1.0 2026-07-30）——实体判级冻结前的强制身份四查。

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
（如"Alpha 集齐率 65/70>90% 判库存仓"或"集齐率低不足以正判托管、另查 gas 溯源独立"
或"Squads 2-of-2 多签，成员 X+Y"，
Squads 解析工具＝scripts/solana/squads_members.py）。

⚠ 误判是双向的（TROLL 2026-07-29 镜像案）：本闸防"托管判成庄家"，但反向
"庄家判成托管"同样发生过——TROLL 案私人四钱包组曾被判"Coinbase 托管体系"，
依据的 0.002246 SOL"所方代建指纹"实为 Solana 建 ATA 物理常数（免租金+fee）。
填 BIG_UNLABELED 的 resolution 判"托管"时必须给正证据（标签库/Vybe 链根/PoR/
gas supplier 体系/批次伪影+集齐率），行为假设与金额常数不算；
"跨所作业"（gas 来自 A 所、筹码来自 B 所）一票排除单所托管解释。
判据细则见 playbook-entity-cluster-methods「托管判定的反向闸」。
"""
import argparse, hashlib, json, os, sys

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
GATE_SCHEMA = 'identity_gate_v2'
FLAGS = {'', 'INFRA_IN_ENTITY', 'PDA_UNRESOLVED', 'BIG_UNLABELED'}
CHAINS = {'eth', 'base', 'bsc', 'sol', 'robinhood', 'hyperliquid', 'filecoin'}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def validate_gate(gate_path, state_path=None, require_resolved=True):
    """Return strict schema/binding/content errors shared by CLI and build_html G8."""
    errors = []
    try:
        gate = json.load(open(gate_path, encoding='utf-8'))
    except Exception as e:
        return [f'identity_gate.json 不可读: {e}']
    if not isinstance(gate, dict):
        return ['identity_gate 顶层必须是对象']
    if gate.get('schema') != GATE_SCHEMA:
        errors.append(f'schema 必须为 {GATE_SCHEMA}')
    chain = gate.get('chain')
    if chain not in CHAINS:
        errors.append(f'chain 非法: {chain!r}')

    state_file = gate.get('state_file')
    if not isinstance(state_file, str) or not state_file or os.path.basename(state_file) != state_file:
        errors.append('state_file 必须是同目录 basename')
    derived_state = os.path.join(os.path.dirname(os.path.abspath(gate_path)), state_file or '')
    bound_state = os.path.abspath(state_path) if state_path else derived_state
    if os.path.abspath(derived_state) != bound_state:
        errors.append('state_file 与当前 analysis-state.json 路径不绑定')
    try:
        state = json.load(open(bound_state, encoding='utf-8'))
        if gate.get('state_sha256') != _sha256(bound_state):
            errors.append('state_sha256 与当前 analysis-state.json 不一致')
    except Exception as e:
        errors.append(f'analysis-state.json 不可读: {e}')
        state = {}
    state_chain = state.get('chain') or (state.get('token') or {}).get('chain')
    if state_chain != chain:
        errors.append(f'chain 与 state 不绑定: gate={chain!r} state={state_chain!r}')

    expected_entities = {}
    for group in state.get('whale_groups') or []:
        entity = group.get('entity_id')
        if not isinstance(entity, str) or not entity.strip():
            errors.append('state.whale_groups 存在空 entity_id')
            continue
        for address in group.get('addresses') or []:
            if address in expected_entities and expected_entities[address] != entity:
                errors.append(f'state 地址跨实体重复: {address}')
            expected_entities[address] = entity

    rows = gate.get('rows')
    if not isinstance(rows, list):
        errors.append('rows 必须是数组')
        rows = []
    seen = set()
    actual_flags = 0
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f'rows[{i}] 必须是对象')
            continue
        address = row.get('address')
        key = address.lower() if isinstance(address, str) and chain != 'sol' else address
        if not isinstance(address, str) or not address.strip():
            errors.append(f'rows[{i}].address 为空')
        elif key in seen:
            errors.append(f'地址重复: {address}')
        seen.add(key)
        entity = row.get('entity')
        if address in expected_entities:
            if entity != expected_entities[address]:
                errors.append(f'{address} entity 与 state 不一致')
        elif entity != '(non-entity big holder)':
            errors.append(f'{address} 不在 state 实体中且未标记 non-entity big holder')
        for required_field in ('share_pct', 'label', 'on_curve', 'flag', 'resolution'):
            if required_field not in row:
                errors.append(f'{address} 缺字段 {required_field}')
        label = row.get('label')
        if label is not None and (not isinstance(label, dict)
                                  or not {'name', 'category', 'tier', 'source'} <= set(label)):
            errors.append(f'{address} label 必须为 null 或完整对象')
        on_curve = row.get('on_curve')
        if chain == 'sol':
            if on_curve not in (True, False, None):
                errors.append(f'{address} on_curve 类型非法')
        elif on_curve is not None:
            errors.append(f'{address} 非 Solana 但 on_curve 非 null')
        flag = row.get('flag')
        if flag not in FLAGS:
            errors.append(f'{address} flag 非法: {flag!r}')
            continue
        actual_flags += bool(flag)
        # 实体成员无标签时必须入闸；share 只用于展示，不是豁免条件。
        if address in expected_entities and label is None:
            required = 'PDA_UNRESOLVED' if chain == 'sol' and on_curve is False \
                else 'BIG_UNLABELED'
            if flag != required:
                errors.append(f'{address} 无标签实体成员必须为 {required}')
        if require_resolved and flag and not str(row.get('resolution', '')).strip():
            errors.append(f'{address} {flag} 无 resolution')
    missing = sorted(set(expected_entities) - {r.get('address') for r in rows if isinstance(r, dict)})
    if missing:
        errors.append(f'{len(missing)} 个 state 实体地址未入闸')
    if gate.get('n_addresses') != len(rows):
        errors.append(f'n_addresses 应为 {len(rows)}，实为 {gate.get("n_addresses")}')
    if gate.get('n_flags') != actual_flags:
        errors.append(f'n_flags 应为 {actual_flags}，实为 {gate.get("n_flags")}')
    return errors


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
                flag = 'BIG_UNLABELED'
        rows.append({'address': a, 'entity': meta['entity'], 'share_pct': meta['share'],
                     'label': label, 'on_curve': oc, 'flag': flag, 'resolution': ''})

    gate = {'schema': GATE_SCHEMA, 'chain': chain,
            'state_file': os.path.basename(state_path),
            'state_sha256': _sha256(state_path),
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
    errors = validate_gate(gate_path)
    if errors:
        print(f"[identity_gate][FAIL] {len(errors)} 项严格校验错误：")
        for error in errors:
            print(f"  - {error}")
        return 1
    gate = json.load(open(gate_path, encoding='utf-8'))
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
