#!/usr/bin/env python3
"""对地址清单在 ETH 主网批量 eth_getCode，产出 {addr: 'eoa'|'contract'} 分流文件。
用途（v4，codex 第二轮复核）：OFAC/ScamSniffer 风险地址只有 EOA 才允许跨 EVM 链注入
（同私钥跨链同控成立）；合约地址跨链不成立（Tornado 等在他链是不同部署地址）。

用法（在 sources/ 目录下）：
  python3 ../probe_codetype.py ofac_eth.txt ofac_eth_codetype.json
  python3 ../probe_codetype.py scamsniffer_address.json scamsniffer_codetype.json
RPC：必须通过环境变量 ETH_RPC 提供端点（如 dRPC：去 ~/.claude/api-keys.md 第 3 节取 key，
     拼 https://lb.drpc.org/ogrpc?network=ethereum&dkey=<key>）。铁律 5：key 永不写死进本目录。
     批量 JSON-RPC（每批 40），429 退避重试。
注意：EIP-7702 委托 EOA 的 getCode 返回 0xef0100…（非空）——按'合约'保守处理即可，
     不跨链注入一个可能换 delegate 的地址是安全方向。
"""
import json, os, ssl, sys, time, urllib.request

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:                     # 本机 python 系统证书链不全（环境已知坑），certifi 兜底
    _SSL_CTX = ssl.create_default_context()


def _rpc_url():
    u = os.environ.get('ETH_RPC')
    if u:
        return u
    sys.exit('缺 ETH_RPC 环境变量。去 ~/.claude/api-keys.md 第 3 节取 dRPC key，'
             '运行前 export ETH_RPC="https://lb.drpc.org/ogrpc?network=ethereum&dkey=<key>"'
             '（铁律 5：key 不写死进 skill 目录）')


def load_addrs(path):
    if path.endswith('.json'):
        data = json.load(open(path))
        return [a.lower() for a in data]
    return [l.strip().lower() for l in open(path) if l.strip()]


def batch_getcode(addrs, url):
    payload = [{'jsonrpc': '2.0', 'id': i, 'method': 'eth_getCode', 'params': [a, 'latest']}
               for i, a in enumerate(addrs)]
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json',
                                          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                                          'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'})
    with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as r:
        res = json.loads(r.read())
    out = {}
    for item in res:
        if 'result' in item:
            out[addrs[item['id']]] = 'eoa' if item['result'] in ('0x', '0X', '') else 'contract'
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    addrs = load_addrs(src)
    url = _rpc_url()
    result = {}
    if os.path.exists(dst):           # 断点续跑
        result = json.load(open(dst))
    todo = [a for a in addrs if a not in result]
    print(f'{src}: {len(addrs)} 址，待查 {len(todo)}')
    B = 40
    i = 0
    while i < len(todo):
        chunk = todo[i:i + B]
        try:
            result.update(batch_getcode(chunk, url))
            i += B
            if i % 400 < B:
                json.dump(result, open(dst, 'w'), indent=0)
                print(f'  {min(i, len(todo))}/{len(todo)}')
            time.sleep(0.6)
        except Exception as e:
            print(f'  batch 失败（{e}），退避 20s 重试', file=sys.stderr)
            time.sleep(20)
    json.dump(result, open(dst, 'w'), indent=0)
    n_eoa = sum(1 for v in result.values() if v == 'eoa')
    print(f'完成: {len(result)} 址 → EOA {n_eoa} / contract {len(result) - n_eoa}，已存 {dst}')


if __name__ == '__main__':
    main()
