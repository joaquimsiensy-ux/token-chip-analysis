#!/usr/bin/env python3
"""SQD portal 全量拉取 Solana SPL 代币转账边（免 key 免代理）。

来源：CLAW(Solana) 分析实战 2026-07-12；v1.3 自
~/Desktop/老公用/meme币叙事总结/scripts/chip_analysis.py 提取为独立脚本（核心逻辑未动）。
配套文档：references/data-pipeline-solana.md §8。

用法（cd 到工作目录跑，缓存写入 ./data/）：
  python3 fetch_sqd_transfers.py <mint> [--launch-ts <unix秒>] [--wall-min 100]
  # launch-ts=发射时间戳（决定起扫 slot，缺省回看 90 天）；wall-min=墙钟保险丝（分钟）

输出：
  data/soltx-<小写mint>.jsonl.gz   每行 [ts, slot, from_owner, to_owner, amount_raw]
  data/soltx-<小写mint>.meta.json  断点元数据（重跑自动续拉）
  stdout 摘要含覆盖区间与缺口声明（墙钟没扫完/起点晚于发射会明说）

要点（详见 pipeline 文档）：
- 转账边=同 tx 内 owner 级净变动贪心配对（swap 聚合路由无法精确还原路径，量级与关系正确即够聚类用）
- from/to 为 ZERO 哨兵（"0x"+40个0）即铸造/销毁
- 双过滤 postMint+preMint（清仓+关户只出现在 pre 侧）；失败交易已剔除
- 按「连续完成前缀」收数防缓存空洞；回补验证确保盖住发射点（最多前移 2 次）
"""
import argparse, gzip, json, subprocess, sys, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SQD_SOL = "https://portal.sqd.dev/datasets/solana-mainnet/stream"
SQD_SOL_HEAD = "https://portal.sqd.dev/datasets/solana-mainnet/head"
SQD_CONC = 16                # 并发段数（实测 32 路也通，留一半余量对公共端礼貌）
SQD_CHUNK = 50_000           # 任务小段大小（slot）；墙钟到期按连续完成前缀收数
SQD_SLOT_RATE = 2.51         # slot/秒近似斜率（仅起点估算用，回补环兜底精度）
SQD_LAUNCH_PAD = 150_000     # 发射点前置缓冲（约 16.6 小时）
ZERO = "0x" + "0" * 40       # 铸造/销毁哨兵


def log(msg):
    print(f"[sqd] {msg}", file=sys.stderr, flush=True)


def curl_json(url, timeout=30):
    try:
        p = subprocess.run(["curl", "-s", "--max-time", str(timeout), url],
                           capture_output=True, text=True, timeout=timeout + 15)
        return json.loads(p.stdout)
    except Exception:
        return None


def sqd_head():
    d = curl_json(SQD_SOL_HEAD, timeout=20)
    try:
        return int((d or {}).get("number"))
    except (TypeError, ValueError):
        return None


def _sqd_pair_tx(delta):
    """同一 tx 内 owner 级净变动 → 转账边 [(from, to, amt)]。
    多对多按量级贪心配对；无来源净增=铸造（from=ZERO）、无去向净减=销毁/关户（to=ZERO）。"""
    pos = sorted(([o, d] for o, d in delta.items() if d > 0), key=lambda x: -x[1])
    neg = sorted(([o, -d] for o, d in delta.items() if d < 0), key=lambda x: -x[1])
    edges, i, j = [], 0, 0
    while i < len(pos) and j < len(neg):
        m = min(pos[i][1], neg[j][1])
        edges.append((neg[j][0], pos[i][0], m))
        pos[i][1] -= m
        neg[j][1] -= m
        if pos[i][1] == 0:
            i += 1
        if neg[j][1] == 0:
            j += 1
    edges.extend((ZERO, o, rem) for o, rem in pos[i:] if rem)
    edges.extend((o, ZERO, rem) for o, rem in neg[j:] if rem)
    return edges


def _sqd_scan_chunk(mint, frm, to, deadline):
    """扫一个小段 [frm, to] → (edges, done_to, finished)。
    edges=[(ts, slot, from, to, amt)]（已滤失败交易、已配对）；
    done_to=段内连续扫到的最后 slot（墙钟/连续失败提前返回时 < to）。"""
    edges, cur, fails = [], frm, 0
    body_fields = {"block": {"number": True, "timestamp": True},
                   "transaction": {"transactionIndex": True, "err": True},
                   "tokenBalance": {"transactionIndex": True, "preOwner": True,
                                    "postOwner": True, "preAmount": True, "postAmount": True}}
    filt = [{"postMint": [mint], "transaction": True},
            {"preMint": [mint], "transaction": True}]   # 双过滤：清仓+关户只在 pre 侧
    while cur <= to:
        if time.time() > deadline:
            return edges, cur - 1, False
        # portal 返回 NDJSON（多行）——不走 curl_json（其 json.loads 只认单个 JSON）
        try:
            p = subprocess.run(["curl", "-s", "-m", "150", "-X", "POST", SQD_SOL,
                                "-H", "Content-Type: application/json",
                                "-d", json.dumps({"type": "solana", "fromBlock": cur,
                                                  "toBlock": to, "fields": body_fields,
                                                  "tokenBalances": filt})],
                               capture_output=True, text=True, timeout=170)
            raw = p.stdout
        except Exception:
            raw = ""
        last = None
        for ln in raw.strip().split("\n"):
            if not ln:
                continue
            try:
                b = json.loads(ln)
                last = b["header"]["number"]
            except (ValueError, KeyError, TypeError):
                continue
            tbs = b.get("tokenBalances") or []
            if not tbs:
                continue
            ts = b["header"].get("timestamp") or 0
            errmap = {tx.get("transactionIndex"): tx.get("err")
                      for tx in b.get("transactions") or []}
            by_tx = defaultdict(dict)   # txIndex -> {owner: delta}
            for r in tbs:
                ti = r.get("transactionIndex")
                if errmap.get(ti) is not None:
                    continue    # 失败交易：余额无真实变化，纯噪声
                owner = r.get("postOwner") or r.get("preOwner")
                if not owner:
                    continue
                try:
                    dlt = int(r.get("postAmount") or 0) - int(r.get("preAmount") or 0)
                except (ValueError, TypeError):
                    continue
                if dlt:
                    by_tx[ti][owner] = by_tx[ti].get(owner, 0) + dlt
            for ti, delta in by_tx.items():
                for f, t, amt in _sqd_pair_tx(delta):
                    edges.append((ts, b["header"]["number"], f, t, amt))
        if last is None:
            fails += 1
            if fails > 6:
                return edges, cur - 1, False
            time.sleep(3 * fails)
            continue
        fails = 0
        cur = last + 1
    return edges, to, True


def _sqd_cache_paths(address):
    d = Path("data")
    key = address.lower()
    return d / f"soltx-{key}.jsonl.gz", d / f"soltx-{key}.meta.json"


def _sqd_scan_span(mint, frm, to, deadline):
    """并发扫 [frm, to]，按「连续完成前缀」收数（防缓存出现空洞）。
    → (edges, covered_to, finished)。"""
    if frm > to:
        return [], to, True
    segs = []
    s = frm
    while s <= to:
        segs.append((s, min(s + SQD_CHUNK - 1, to)))
        s += SQD_CHUNK
    with ThreadPoolExecutor(min(SQD_CONC, len(segs))) as ex:
        results = list(ex.map(lambda sg: _sqd_scan_chunk(mint, sg[0], sg[1], deadline), segs))
    edges, covered_to, finished = [], frm - 1, True
    for (s0, s1), (e, done_to, fin) in zip(segs, results):
        edges.extend(x for x in e if x[1] <= done_to)
        covered_to = done_to
        if not fin:      # 第一个未完段：吸收其连续部分后截断，其后段丢弃
            finished = False
            break
    return edges, covered_to, finished


def sqd_fetch_transfers_sol(address, launch_ts, wall_min=100):
    """SQD 全量拉取（带断点缓存+回补验证+墙钟保险丝）。
    → (transfers[(ts,slot,from,to,amt_raw)], gap|None)；transfers=None 表示通道不可用。"""
    head = sqd_head()
    if not head:
        return None, "SQD portal head 不可达"
    cache_fp, meta_fp = _sqd_cache_paths(address)
    cache_fp.parent.mkdir(parents=True, exist_ok=True)
    edges, meta = [], {}
    if cache_fp.exists() and meta_fp.exists():
        try:
            meta = json.loads(meta_fp.read_text())
            with gzip.open(cache_fp, "rt") as f:
                edges = [tuple(json.loads(ln)) for ln in f if ln.strip()]
            log(f"SQD 缓存命中：{len(edges)} 条边，覆盖 slot [{meta.get('from_slot')}, {meta.get('next_slot')})")
        except Exception as e:
            log(f"SQD 缓存损坏（{e}）——重新全量")
            edges, meta = [], {}

    deadline = time.time() + wall_min * 60
    now = int(time.time())
    if meta.get("next_slot"):
        span_from = int(meta["next_slot"])
        from_slot = int(meta.get("from_slot") or span_from)
    else:
        back = int((now - (launch_ts or now - 90 * 86400)) * SQD_SLOT_RATE) + SQD_LAUNCH_PAD
        span_from = from_slot = max(1, head - back)

    new_edges, covered_to, finished = _sqd_scan_span(address, span_from, head, deadline)
    edges.extend(new_edges)

    # 回补验证：起点没盖住发射（未见铸造边且最早记录晚于发射）→ 前移重扫，最多 2 次
    if not meta.get("launch_covered"):
        for _ in range(2):
            has_mint = any(f == ZERO for _, _, f, _, _ in edges)
            min_ts = min((e[0] for e in edges if e[0]), default=None)
            # min_ts=None（已扫前缀内零边）：起点已够早或墙钟没扫进数据区，回补都无意义
            if has_mint or not launch_ts or min_ts is None or min_ts <= launch_ts + 900:
                break
            if time.time() > deadline - 60:
                break
            shift = max(int(((min_ts or now) - launch_ts) * SQD_SLOT_RATE * 1.3), 100_000)
            new_from = max(1, from_slot - shift)
            log(f"SQD 回补：起点 {from_slot} 未盖住发射（最早记录 {min_ts} vs 发射 {launch_ts}），前移到 {new_from}")
            back_edges, back_to, back_fin = _sqd_scan_span(address, new_from, from_slot - 1, deadline)
            if not back_fin:
                break    # 回补没扫完则不并入（防空洞），维持原 from_slot
            edges.extend(back_edges)
            from_slot = new_from

    if not edges:
        return None, "SQD 拉取无数据（含缓存为空）"

    # 落盘缓存（整写：连续区间 [from_slot, covered_to]；边按 slot 排序）
    edges.sort(key=lambda x: (x[1], x[0]))
    try:
        with gzip.open(cache_fp, "wt") as f:
            for e in edges:
                f.write(json.dumps(list(e)) + "\n")
        has_mint = any(f_ == ZERO for _, _, f_, _, _ in edges)
        meta_fp.write_text(json.dumps({
            "from_slot": from_slot, "next_slot": covered_to + 1,
            "launch_covered": bool(meta.get("launch_covered")) or has_mint,
            "updated": time.strftime("%Y-%m-%d %H:%M")}))
    except Exception as e:
        log(f"SQD 缓存写入失败（不阻塞）：{e}")

    gap = None
    if not finished:
        lag_h = (head - covered_to) / SQD_SLOT_RATE / 3600
        tail_ts = max((e[0] for e in edges if e[0]), default=0)
        tail_s = time.strftime("%m-%d %H:%M", time.localtime(tail_ts)) if tail_ts else "?"
        gap = (f"链上重放因墙钟保险丝（{wall_min} 分钟）只覆盖到 {tail_s}"
               f"（落后链头约 {lag_h:.1f} 小时）——此后的转账/庄家动作未纳入，下次运行自动续拉")
    min_ts = min((e[0] for e in edges if e[0]), default=0)
    if launch_ts and min_ts and min_ts > launch_ts + 6 * 3600 and not any(
            f == ZERO for _, _, f, _, _ in edges):
        miss_h = (min_ts - launch_ts) / 3600
        g2 = f"重放起点晚于发射约 {miss_h:.0f} 小时——最早期建仓（含 dev 初始分配）缺失"
        gap = f"{gap}；{g2}" if gap else g2
    log(f"SQD 全量转账边 {len(edges)} 条，覆盖 slot [{from_slot}, {covered_to}]"
        + (f"；缺口：{gap}" if gap else "（到链头，全量）"))
    return edges, gap


def main():
    ap = argparse.ArgumentParser(description="SQD portal 全量拉取 SPL 代币转账边")
    ap.add_argument("mint", help="SPL 代币 mint 地址")
    ap.add_argument("--launch-ts", type=int, default=0, help="发射 unix 时间戳（秒），缺省回看 90 天")
    ap.add_argument("--wall-min", type=int, default=100, help="墙钟保险丝（分钟），默认 100")
    a = ap.parse_args()
    edges, gap = sqd_fetch_transfers_sol(a.mint, a.launch_ts or None, a.wall_min)
    if edges is None:
        print(f"失败：{gap}", flush=True)
        sys.exit(1)
    print(f"完成：{len(edges)} 条转账边 → data/soltx-{a.mint.lower()}.jsonl.gz"
          + (f"\n缺口声明：{gap}" if gap else "（全量到链头）"), flush=True)


if __name__ == "__main__":
    main()
