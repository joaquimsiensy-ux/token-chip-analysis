#!/usr/bin/env python3
"""bscscan 地址页批量抓 Funded By（首笔注资来源）+ Public Name Tag。
来源：哈基米(BSC) 分析实战产物, 2026-07-18。

用法：python3 fetch_fundedby.py <地址清单文件(一行一个)> <输出json>
  - 单线程 0.8s 间隔（bscscan 并发>1 必限流，见 data-pipeline-evm §7.2）
  - 磁盘缓存 data/bscache/（sha1(addr).html，命中免请求，断点友好）
  - 输出 {addr: {funder, tx, tag}}；页面文案是 First Funded By，DOM 锚点是
    id="linkIcon_fundedby_address"
  - 147 址实测约 8 分钟、134 命中（未命中=新钱包无入金或页面结构变化）

⚠ 2026-07-26 修复的静默错误（EGL1(BSC) 案实测）：旧正则
  `fundedby[^>]*>.*?(0x[0-9a-fA-F]{40})` 从锚点**向后**贪找 40-hex，而 bscscan
  改版后锚点后紧跟的是 `<a href="/tx/0x{64}">` —— **64 位交易哈希的前 40 位被当成了
  地址**，于是 121/121 全部"命中"却全是不存在的假地址（实测这批假地址 nonce 全为 0、
  余额 0、无代码）。危害是静默的：下游"gas 注资方各不相同 → 判定非同一实体"的结论
  会被完全带偏，且假地址看起来完全合法。
  修复要点（三条缺一不可）：
    ① 真 funder 在锚点**之前**的 `/address/0x{40}` 链接里，取锚点前窗口的最后一个；
    ② 40-hex 匹配必须加负向先行断言 `(?![0-9a-fA-F])`，否则仍会咬住 64-hex 前缀；
    ③ 自检 funder != 目标地址本身（页面顶部就有自己的地址，窗口取大了会误抓）。
  另附带产出首笔注资的 tx 哈希，便于人工复验。
"""
import json, re, os, time, subprocess, hashlib, sys

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# 40-hex 且右侧不再接 hex —— 防咬住 64 位 tx 哈希的前 40 位（见模块头注 ⚠）
_ADDR_RE = re.compile(r"/address/(0x[0-9a-fA-F]{40})(?![0-9a-fA-F])")
_ANCHORS = ("linkicon_fundedby_address", "fundedby")
_WINDOW = 2500          # 锚点前回看窗口（字符）


def _parse_funder(html, self_addr):
    """从地址页 HTML 提取 (funder, first_funding_tx)；解析不出返回 (None, None)。

    真 funder 在 fundedby 锚点**之前**的 /address/ 链接里；锚点之后是 /tx/ 链接。
    """
    low = html.lower()
    i = -1
    for anc in _ANCHORS:
        i = low.find(anc)
        if i >= 0:
            break
    if i < 0:
        return None, None
    cands = _ADDR_RE.findall(html[max(0, i - _WINDOW):i + 50])
    funder = None
    for c in reversed(cands):                       # 取离锚点最近的一个
        if c.lower() != self_addr.lower():          # 页面顶部有自己的地址，排除
            funder = c.lower()
            break
    mtx = re.search(r"/tx/(0x[0-9a-fA-F]{64})", html[i:i + 800])
    return funder, (mtx.group(1).lower() if mtx else None)


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
        funder, ftx = _parse_funder(h, a)
        mt = re.search(r"Public Name Tag[^<]*</span>[^<]*<span[^>]*>([^<]{2,60})<", h, re.S)
        out[a] = {"funder": funder, "tx": ftx,
                  "tag": mt.group(1).strip() if mt else ""}
        if (i + 1) % 20 == 0:
            json.dump(out, open(out_path, "w"))
            print(f"{i+1}/{len(targets)}", flush=True)
    json.dump(out, open(out_path, "w"))
    got = sum(1 for v in out.values() if v.get("funder"))
    print(f"done {got}/{len(targets)} 拿到 funder")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
