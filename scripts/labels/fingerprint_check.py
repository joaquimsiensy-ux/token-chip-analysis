#!/usr/bin/env python3
"""字节码模板指纹检查器（v4 2026-07-17，codex 第二轮复核方案：组合指纹而非裸 hash）

背景：Robinhood 链公共 bot 卖币合约是【同模板多部署】（已知 3 个 23.4KB 未验证部署，
每次新部署都得现场 getCode 判别）。本工具把"判别"变成查表：
  指纹 = sha256(runtime_code) + code 长度 + selector 集合签名（PUSH4 启发式提取）
  - 完整 hash 相同 → 同字节码（immutable 参数都相同）
  - hash 不同但 len 相近（±2%）且 selector 签名相同 → 同模板不同 immutable/构造参数
命中输出 **candidate 级提示**（"疑似已知公共设施模板，行为复核后才升 exclude"）——
代理壳同 hash ≠ 同服务、同模板 ≠ 同运营者，指纹只缩小排查范围不下定论（codex 纪律）。

用法：
  python3 fingerprint_check.py --chain robinhood ADDR1 ADDR2 ...      # 查表
  python3 fingerprint_check.py --chain robinhood --add ADDR --name "公共bot卖币合约" \
      --verdict infra-candidate --evidence "RAXOL/GME 案实测同模板"    # 取样入库
指纹库：references/labels/codehash-robinhood.csv（按链分文件）
"""
import argparse, csv, hashlib, json, os, re, ssl, sys, urllib.request

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()

_HERE = os.path.dirname(os.path.abspath(__file__))
LABELS_DIR = os.path.normpath(os.path.join(_HERE, '..', '..', 'references', 'labels'))
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')     # Robinhood RPC WAF 拦 python 默认 UA

RPC = {
    'robinhood': 'https://rpc.mainnet.chain.robinhood.com',
    'eth': 'https://ethereum-rpc.publicnode.com',
    'bsc': 'https://bsc-rpc.publicnode.com',
    'base': 'https://base-rpc.publicnode.com',
}
FIELDS = ['fingerprint_sha256', 'code_len', 'selector_sig', 'name', 'verdict',
          'evidence', 'sample_address', 'added_date']


def get_code(chain, addr):
    req = urllib.request.Request(
        RPC[chain], data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'eth_getCode',
                                     'params': [addr, 'latest']}).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return json.loads(r.read())['result']


def selectors(code_hex):
    """PUSH4 启发式提取 dispatcher selector 集合（0x63 + 4 字节，去 ffffffff 等噪声）。"""
    body = code_hex[2:] if code_hex.startswith('0x') else code_hex
    sels = set(re.findall(r'63([0-9a-f]{8})(?=1[46])', body))   # PUSH4 后跟 EQ/DUP 的典型 dispatch
    sels |= set(re.findall(r'7c010000000000000000000000000000000000000000000000000000000000009004', body) and [])
    return {s for s in sels if s not in ('ffffffff', '00000000')}


def fingerprint(code_hex):
    body = bytes.fromhex(code_hex[2:] if code_hex.startswith('0x') else code_hex)
    sels = sorted(selectors(code_hex))
    sel_sig = hashlib.sha256('|'.join(sels).encode()).hexdigest()[:16] if sels else ''
    return hashlib.sha256(body).hexdigest(), len(body), sel_sig


def load_db(chain):
    path = os.path.join(LABELS_DIR, f'codehash-{chain}.csv')
    rows = list(csv.DictReader(open(path))) if os.path.exists(path) else []
    return path, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--chain', required=True, choices=list(RPC))
    ap.add_argument('--add', help='取样入库：拉该地址 code 存指纹')
    ap.add_argument('--name', default='')
    ap.add_argument('--verdict', default='infra-candidate')
    ap.add_argument('--evidence', default='')
    ap.add_argument('addrs', nargs='*')
    args = ap.parse_args()
    path, db = load_db(args.chain)

    if args.add:
        code = get_code(args.chain, args.add.lower())
        if code in ('0x', ''):
            print(f'{args.add}: EOA（无 code），不入指纹库'); return
        fp, ln, sig = fingerprint(code)
        if any(r['fingerprint_sha256'] == fp for r in db):
            print(f'{args.add}: 指纹已在库（{fp[:16]}…）'); return
        db.append({'fingerprint_sha256': fp, 'code_len': str(ln), 'selector_sig': sig,
                   'name': args.name or '未命名模板', 'verdict': args.verdict,
                   'evidence': args.evidence, 'sample_address': args.add.lower(),
                   'added_date': '2026-07-17'})
        with open(path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader(); w.writerows(db)
        print(f'已入库: {args.add} → {fp[:16]}… len={ln} sel_sig={sig} 「{args.name}」')
        return

    if not args.addrs:
        ap.error('给地址列表查表，或 --add 取样入库')
    for a in args.addrs:
        code = get_code(args.chain, a.lower())
        if code in ('0x', ''):
            print(f'{a}: EOA')
            continue
        fp, ln, sig = fingerprint(code)
        exact = [r for r in db if r['fingerprint_sha256'] == fp]
        tmpl = [r for r in db if not exact and r['selector_sig'] == sig and sig
                and abs(int(r['code_len']) - ln) <= max(64, int(ln * 0.02))]
        if exact:
            r = exact[0]
            print(f'{a}: 【字节码完全一致】{r["name"]}（样本 {r["sample_address"][:14]}…）'
                  f' → candidate 级：{r["verdict"]}；行为复核后才可按设施处理 | {r["evidence"]}')
        elif tmpl:
            r = tmpl[0]
            print(f'{a}: 【同模板疑似】selector 签名与 {r["name"]} 相同、长度相近'
                  f'（{ln} vs {r["code_len"]}）→ candidate 级提示，须行为复核 | {r["evidence"]}')
        else:
            print(f'{a}: 未命中指纹库（len={ln} fp={fp[:16]}… sel_sig={sig}）')


if __name__ == '__main__':
    main()
