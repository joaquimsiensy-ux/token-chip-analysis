#!/usr/bin/env python3
"""拉取 GeckoTerminal 分钟K + 小时K（Robinhood 链，networks/robinhood）。

来源：RAXOL(Robinhood) 分析实战 2026-07-12，v1.3 参数化收编（pool 移入 config.json）。
用法：cd 到工作目录（含 config.json）后
  python3 pull_ohlcv.py [分钟K页数] [小时K页数]   # 默认 3 页 / 2 页，每页≤1000 根
输出：data/ohlcv_minute.json、data/ohlcv_hour.json（rows=[[ts,o,h,l,c,vol],...] 升序）
坑（见 references/data-pipeline-robinhood.md）：
- 必须带浏览器 User-Agent（python-urllib 默认 UA 被 403）；限速≈30req/min，429 退避
- GT 的 pool_created_at 是收录时间不是链上建池时间（Dexscreener pairCreatedAt 才是）
- 分钟K从建池分钟起可得；发射窗口配价用分钟K，勿用小时K
"""
import json, ssl, certifi, urllib.request, time, os, sys

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')


def load_pool():
    with open("config.json") as f:
        pool = (json.load(f).get("pool") or "").lower()
    if not pool.startswith("0x"):
        sys.exit("config.json 的 pool 缺失（主池地址，Dexscreener 可查）")
    return pool


def get(url):
    req = urllib.request.Request(url, headers={'accept': 'application/json', 'User-Agent': UA})
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
                return json.load(r)
        except Exception as e:
            print('  retry', i, e, flush=True)
            time.sleep(8 * (i + 1))
    raise RuntimeError('GT fail')


def pull(pool, tf, pages):
    out = []
    before = ''
    for _ in range(pages):
        u = (f'https://api.geckoterminal.com/api/v2/networks/robinhood/pools/{pool}'
             f'/ohlcv/{tf}?aggregate=1&limit=1000&currency=usd' + before)
        d = get(u)
        rows = (((d.get('data') or {}).get('attributes') or {}).get('ohlcv_list')) or []
        if not rows:
            break
        out.extend(rows)
        before = f'&before_timestamp={min(r[0] for r in rows)}'
        time.sleep(2.5)
        if len(rows) < 1000:
            break
    seen = {}
    for r in out:
        seen[r[0]] = r
    return [seen[k] for k in sorted(seen)]


def main():
    pool = load_pool()
    mp = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    hp = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    os.makedirs("data", exist_ok=True)
    for tf, pages, name in (("minute", mp, "ohlcv_minute.json"), ("hour", hp, "ohlcv_hour.json")):
        rows = pull(pool, tf, pages)
        with open(os.path.join("data", name), "w") as f:
            json.dump({"pool": pool, "timeframe": tf, "rows": rows}, f)
        print(f"{name}: {len(rows)} 根", flush=True)


if __name__ == "__main__":
    main()
