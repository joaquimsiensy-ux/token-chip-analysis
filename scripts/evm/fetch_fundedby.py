#!/usr/bin/env python3
"""bscscan 地址页批量抓 Funded By（首笔注资来源）+ Public Name Tag。
来源：哈基米(BSC) 分析实战产物, 2026-07-18。

用法：python3 fetch_fundedby.py <地址清单文件(一行一个)> <输出json>
  - 单线程 0.8s 间隔（bscscan 并发>1 必限流，见 data-pipeline-evm §7.2）
  - 磁盘缓存 data/bscache/（sha1(addr).html，命中免请求，断点友好）
  - 输出 {addr: {funder, tag}}；正则 fundedby[^>]*>.*?(0x…)（页面文案是
    First Funded By 但 DOM 属性名是 fundedby）
  - 147 址实测约 8 分钟、134 命中（未命中=新钱包无入金或页面结构变化）
"""
import json, re, os, time, subprocess, hashlib, sys

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def main(list_path, out_path):
    targets = [l.strip().lower() for l in open(list_path) if l.strip().startswith("0x")]
    cache = "data/bscache"
    os.makedirs(cache, exist_ok=True)
    out = {}
    if os.path.exists(out_path):
        out = json.load(open(out_path))
    for i, a in enumerate(targets):
        if a in out and out[a].get("funder"):
            continue
        cf = os.path.join(cache, hashlib.sha1(a.encode()).hexdigest() + ".html")
        h = ""
        if os.path.exists(cf) and os.path.getsize(cf) > 50000:
            h = open(cf, encoding="utf-8", errors="replace").read()
        else:
            for att in range(3):
                r = subprocess.run(["curl", "-s", "--max-time", "25", "-A", UA,
                                    f"https://bscscan.com/address/{a}"],
                                   capture_output=True, text=True)
                h = r.stdout
                if len(h) > 50000:
                    open(cf, "w").write(h)
                    break
                time.sleep(2 * (att + 1))
            time.sleep(0.8)
        m = re.search(r"fundedby[^>]*>.*?(0x[0-9a-fA-F]{40})", h, re.S | re.I)
        mt = re.search(r"Public Name Tag[^<]*</span>[^<]*<span[^>]*>([^<]{2,60})<", h, re.S)
        out[a] = {"funder": m.group(1).lower() if m else None,
                  "tag": mt.group(1).strip() if mt else ""}
        if (i + 1) % 20 == 0:
            json.dump(out, open(out_path, "w"))
            print(f"{i+1}/{len(targets)}", flush=True)
    json.dump(out, open(out_path, "w"))
    got = sum(1 for v in out.values() if v.get("funder"))
    print(f"done {got}/{len(targets)} 拿到 funder")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
