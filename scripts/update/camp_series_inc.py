#!/usr/bin/env python3
"""U5 阵营占比序列增量追加（EVM 输入格式；核心逻辑链无关）：
旧 appendix 的 camp_share_series + 增量重放逐小时采样 → 新 camp_share_series
（report-template 格式 [{ts, 阵营: pct, ...}]，可直接嵌入滚动 appendix 与画图1）。

来源：RAXOL(make_inc_charts 拼接段) / Pointless(build_update_charts) / TRASH(make_charts_inc)
/ VEX(extend_series) 四次 /token-update 实战合并参数化收编（v2.10.0）——四战各写了一版
序列延长逻辑，稳定部分（逐小时重放采样+残差阵营+重采样）在此固化；每次都变的部分
（地址→阵营归属、旧键名→新键名映射）外置为两个人工产出的 JSON 文件。

用法（工作目录含 config.json）：
  python3 camp_series_inc.py --camps camps.json --old-balances data/balances_now.json
                             [--appendix appendix.json] [--inc data/transfers_inc.jsonl.gz]
                             [--remap remap.json] [--residual 散户] [--max-points 500]
                             [--out data/camp_share_series_new.json]
camps.json：{阵营名: [完整地址,...]}——本次更新后的阵营映射，键名用 standard_charts
  CAMP_ORDER 标准名（项目方/大庄/小庄/离场庄/狙击集团/CEX托管/疑似CEX托管/其他大户/
  历史大户/流动性池/桥锁仓/锁仓销毁等；2026-07-25 扩三键，互斥优先级见 standard_charts 注释）。
remap.json（可选）：{旧序列键名: 新阵营键名}，多对一相加——旧研报阵营命名与当前标准
  不一致（标准迁移）时必给，否则旧段与新段键不齐、图1 会断层（脚本会 WARN）。
残差阵营（--residual，默认"散户"）＝100−已映射阵营合计，自动计算不进 camps.json。
"""
import argparse, gzip, json, sys
from datetime import datetime, timezone


def load_cfg():
    with open("config.json") as f:
        cfg = json.load(f)
    return int(cfg["total_supply_tokens"]) * 10 ** int(cfg.get("decimals", 18))


def load_balances(path):
    with open(path) as f:
        d = json.load(f)
    if isinstance(d.get("balances"), dict):
        d = d["balances"]
    return {k.lower(): int(v) for k, v in d.items()}


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camps", required=True, help="{阵营名:[addr,...]} 本次阵营映射")
    ap.add_argument("--old-balances", required=True)
    ap.add_argument("--appendix", default="appendix.json", help="旧研报 appendix（取旧序列）")
    ap.add_argument("--inc", default="data/transfers_inc.jsonl.gz")
    ap.add_argument("--cutoff-block", type=int, default=None)
    ap.add_argument("--remap", default=None, help="{旧键:新键} 旧序列键名映射（标准迁移时必给）")
    ap.add_argument("--residual", default="散户")
    ap.add_argument("--max-points", type=int, default=500)
    ap.add_argument("--out", default="data/camp_share_series_new.json")
    args = ap.parse_args()

    total = load_cfg()
    with open(args.camps) as f:
        camps = json.load(f)
    camp_of = {}
    for c, addrs in camps.items():
        for a in addrs:
            camp_of[a.lower()] = c
    camp_names = list(camps.keys())
    if args.residual in camp_names:
        sys.exit(f"残差阵营名 {args.residual} 不应出现在 camps.json（它由 100−Σ 自动算）")

    # ── 旧序列（remap 后） ──
    with open(args.appendix) as f:
        app = json.load(f)
    old_series = app.get("camp_share_series") or []
    remap = {}
    if args.remap:
        with open(args.remap) as f:
            remap = json.load(f)
    new_keys = set(camp_names) | {args.residual}
    series = []
    unmapped = set()
    for p in old_series:
        q = {}
        for k, v in p.items():
            if k == "ts":
                continue
            nk = remap.get(k, k)
            if nk not in new_keys:
                unmapped.add(k)
            q[nk] = round(q.get(nk, 0.0) + (v or 0.0), 3)
        for nk in new_keys:
            q.setdefault(nk, 0.0)
        series.append({"ts": p["ts"], **q})
    if unmapped:
        print(f"WARN: 旧序列键未映射到新阵营键（图1 将断层）: {sorted(unmapped)}；"
              f"用 --remap 提供旧键→新键映射", flush=True)
    last_ts = parse_ts(series[-1]["ts"]) if series else 0

    # ── 增量重放逐小时追加 ──
    bal = load_balances(args.old_balances)
    rows = []
    with gzip.open(args.inc, "rt") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    rows.sort(key=lambda r: (r["block"], r["logi"]))
    cutoff = args.cutoff_block if args.cutoff_block is not None else (rows[0]["block"] if rows else 0)
    rows = [r for r in rows if r["block"] > cutoff]
    if not rows:
        sys.exit("增量窗口内无有效行（cutoff 之后为空）")

    zero = "0x" + "0" * 40

    def snapshot(ts):
        agg = {c: 0 for c in camp_names}
        others = 0
        for a, v in bal.items():
            if v <= 0 or a == zero:
                continue
            c = camp_of.get(a)
            if c:
                agg[c] += v
            else:
                others += v
        out = {c: round(agg[c] / total * 100, 3) for c in camp_names}
        out[args.residual] = round(others / total * 100, 3)
        return {"ts": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(), **out}

    i, appended = 0, 0
    hour = (rows[0]["ts"] // 3600) * 3600
    end_ts = rows[-1]["ts"]
    while hour <= end_ts:
        hh = hour + 3600
        while i < len(rows) and rows[i]["ts"] < hh:
            r = rows[i]
            amt = int(r["amount"])
            bal[r["from"].lower()] = bal.get(r["from"].lower(), 0) - amt
            bal[r["to"].lower()] = bal.get(r["to"].lower(), 0) + amt
            i += 1
        if hour > last_ts:
            series.append(snapshot(hour))
            appended += 1
        hour += 3600
    # 末点补真实截止时刻（不足整点的尾巴）
    if end_ts > last_ts and (not series or parse_ts(series[-1]["ts"]) < end_ts):
        series.append(snapshot(end_ts))
        appended += 1

    # ── 等距重采样（首末必留） ──
    n = len(series)
    if n > args.max_points:
        keep = sorted({round(i * (n - 1) / (args.max_points - 1)) for i in range(args.max_points)})
        series = [series[j] for j in keep]
        print(f"重采样 {n} → {len(series)} 点")

    with open(args.out, "w") as f:
        json.dump(series, f, ensure_ascii=False)
    print(f"追加 {appended} 点，总 {len(series)} 点 → {args.out}")
    print("末点:", {k: v for k, v in series[-1].items() if k != 'ts'})


if __name__ == "__main__":
    main()
