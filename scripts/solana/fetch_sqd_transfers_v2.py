#!/usr/bin/env python3
"""SQD portal 全量拉取 Solana SPL 代币转账边 v2——压缩传输+自适应区域并发+全局令牌桶。

来源：Solana 采集加速工程 2026-07-21（@CX 交叉复核定案）。v1（fetch_sqd_transfers.py）保留不动。
相对 v1 的三刀（实测依据见 data-pipeline-solana.md §13）：
  1. requests.Session 替代逐请求 curl 子进程：连接复用 + 默认 gzip 协商
     （明文传输是 v1 慢的主因：wSOL 压测明文 4.65 slots/s vs 压缩 98 slots/s ≈ 21 倍）
  2. 自适应区域并发：区域大小按实测耗时自动伸缩（发射窗自动缩小、死亡期自动放大），
     失败区域进 gaps 继续别的——不再像 v1 那样"第一个未完段之后整体丢弃"
  3. 全局令牌桶限速：默认 1.6 请求/秒（公共端点文档限 20 次/10 秒），并发共享一个桶

用法（cd 到工作目录跑，缓存写入 ./data/）：
  python3 fetch_sqd_transfers_v2.py <mint> [--launch-ts <unix秒>] [--wall-min 100]
      [--conc 6] [--rps 1.6] [--url <端点>] [--key-file ~/.config/sqd/api-key]
输出（与 v1 完全同构，下游无感）：
  data/soltx-<小写mint>.jsonl.gz   每行 [ts, slot, from_owner, to_owner, amount_raw]
  data/soltx-<小写mint>.meta.json  断点元数据 v2（自动迁移 v1 格式；重跑自动续拉）
  data/soltx-<小写mint>.parts/     区域分片工作目录（合并成功后自动清空）

要点：
- 转账边=同 tx 内 owner 级净变动贪心配对（与 v1/window_fetch 同一解析核，量级与关系正确够聚类用）
- from/to 为 ZERO 哨兵（"0x"+40个0）即铸造/销毁；双过滤 postMint+preMint；失败交易剔除
- gaps 非空时 stdout 明确声明缺口区间——禁止无声吞洞
- key：公共端点 2026-07 实测不认证（key 无效也无害地带上）；拿到专属端点后 --url 换掉即生效
"""
import argparse, gzip, json, os, sys, threading, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("[fatal] 需要 requests（本机既有环境应自带；没有则 pip3 install requests）")

DEF_URL = "https://portal.sqd.dev/datasets/solana-mainnet"
SQD_SLOT_RATE = 2.51          # slot/秒近似斜率（仅起点估算用，回补环兜底精度）
SQD_LAUNCH_PAD = 150_000      # 发射点前置缓冲（约 16.6 小时）
ZERO = "0x" + "0" * 40
AREA_INIT = 100_000           # 初始区域大小（slot）；按耗时自适应
AREA_MIN, AREA_MAX = 10_000, 1_000_000
AREA_T_FAST, AREA_T_SLOW = 30, 180   # 区域耗时 <30s 翻倍 / >180s 减半


def log(msg):
    print(f"[sqd2] {msg}", file=sys.stderr, flush=True)


class TokenBucket:
    """全局令牌桶：所有 worker 发起 HTTP 请求前取一个令牌。"""
    def __init__(self, rps, burst=8):
        self.rate, self.cap = float(rps), float(burst)
        self.tokens, self.ts = float(burst), time.time()
        self.lock = threading.Lock()

    def take(self):
        while True:
            with self.lock:
                now = time.time()
                self.tokens = min(self.cap, self.tokens + (now - self.ts) * self.rate)
                self.ts = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                need = (1 - self.tokens) / self.rate
            time.sleep(need)


class AdaptiveArea:
    """区域大小全局自适应：完成快→放大，完成慢→缩小（EMA 无需，直接乘除便于推理）。"""
    def __init__(self, init=AREA_INIT):
        self.size = init
        self.lock = threading.Lock()

    def get(self):
        with self.lock:
            return self.size

    def feedback(self, elapsed):
        with self.lock:
            if elapsed < AREA_T_FAST:
                self.size = min(AREA_MAX, self.size * 2)
            elif elapsed > AREA_T_SLOW:
                self.size = max(AREA_MIN, self.size // 2)


def pair_tx(delta):
    """同一 tx 内 owner 级净变动 → 转账边（与 v1 逐字同构）。"""
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


class Fetcher:
    def __init__(self, base_url, mint, key, bucket, conc):
        self.stream_url = base_url.rstrip("/") + "/stream"
        self.head_url = base_url.rstrip("/") + "/head"
        self.mint = mint
        self.bucket = bucket
        # 每 worker 一个 Session（requests.Session 非线程安全）；均默认 gzip 协商+连接复用
        self.local = threading.local()
        self.headers = {"Content-Type": "application/json"}
        if key:
            self.headers["Authorization"] = f"Bearer {key}"

    def _sess(self):
        if not hasattr(self.local, "s"):
            self.local.s = requests.Session()
            self.local.s.headers.update(self.headers)
        return self.local.s

    def head(self):
        try:
            self.bucket.take()
            r = self._sess().get(self.head_url, timeout=20)
            return int(r.json().get("number"))
        except Exception:
            return None

    def scan_area(self, frm, to, deadline):
        """扫 [frm, to]，服务端响应上限自动截断、客户端按最后 slot 续拉。
        → (edges, done_to, finished)。edges=[(ts, slot, from, to, amt)]。"""
        body_fields = {"block": {"number": True, "timestamp": True},
                       "transaction": {"transactionIndex": True, "err": True},
                       "tokenBalance": {"transactionIndex": True, "preOwner": True,
                                        "postOwner": True, "preAmount": True, "postAmount": True}}
        filt = [{"postMint": [self.mint], "transaction": True},
                {"preMint": [self.mint], "transaction": True}]
        edges, cur, fails = [], frm, 0
        while cur <= to:
            if time.time() > deadline:
                return edges, cur - 1, False
            body = {"type": "solana", "fromBlock": cur, "toBlock": to,
                    "fields": body_fields, "tokenBalances": filt}
            last = None
            try:
                self.bucket.take()
                # timeout=(连接, 字节间隔)——流式响应逐行到达，字节间隔 60s 足够
                with self._sess().post(self.stream_url, json=body, stream=True,
                                       timeout=(15, 60)) as r:
                    if r.status_code != 200:
                        raise RuntimeError(f"http {r.status_code}")
                    for ln in r.iter_lines(decode_unicode=True):
                        if not ln:
                            continue
                        try:
                            b = json.loads(ln)
                        except ValueError:
                            break   # 截断行：按已解析部分推进（window_fetch 同款处理）
                        hdr = b.get("header", {})
                        last = hdr.get("number", last)
                        tbs = b.get("tokenBalances") or []
                        if not tbs:
                            continue
                        ts = hdr.get("timestamp") or 0
                        errmap = {tx.get("transactionIndex"): tx.get("err")
                                  for tx in b.get("transactions") or []}
                        by_tx = defaultdict(dict)
                        for rec in tbs:
                            ti = rec.get("transactionIndex")
                            if errmap.get(ti) is not None:
                                continue    # 失败交易：余额无真实变化，纯噪声
                            owner = rec.get("postOwner") or rec.get("preOwner")
                            if not owner:
                                continue
                            try:
                                dlt = int(rec.get("postAmount") or 0) - int(rec.get("preAmount") or 0)
                            except (ValueError, TypeError):
                                continue
                            if dlt:
                                by_tx[ti][owner] = by_tx[ti].get(owner, 0) + dlt
                        for ti, delta in by_tx.items():
                            for f, t, amt in pair_tx(delta):
                                edges.append((ts, hdr["number"], f, t, amt))
            except Exception as e:
                last = None
                err = str(e)[:80]
            if last is None:
                fails += 1
                if fails > 5:
                    return edges, cur - 1, False
                time.sleep(2 * fails)
                continue
            fails = 0
            cur = last + 1
        return edges, to, True


def cache_paths(address):
    d = Path("data")
    key = address.lower()
    return (d / f"soltx-{key}.jsonl.gz", d / f"soltx-{key}.meta.json",
            d / f"soltx-{key}.parts")


def load_meta(meta_fp):
    """读 meta，v1 格式（from_slot/next_slot）自动迁移为 v2 areas。"""
    if not meta_fp.exists():
        return {}
    try:
        m = json.loads(meta_fp.read_text())
    except Exception:
        return {}
    if m.get("version") == 2:
        return m
    # v1 迁移：连续前缀 [from_slot, next_slot) 视为一个已完成区域
    if m.get("next_slot"):
        return {"version": 2, "from_slot": int(m.get("from_slot") or m["next_slot"]),
                "launch_covered": bool(m.get("launch_covered")),
                "areas": [{"s": int(m.get("from_slot") or m["next_slot"]),
                           "e": int(m["next_slot"]) - 1, "done": True, "src": "v1"}]}
    return {}


def plan_areas(meta, span_from, head):
    """已完成区域之外的空洞 → 待扫区间列表 [(s,e)]。"""
    done = sorted(((a["s"], a["e"]) for a in meta.get("areas", []) if a.get("done")),
                  key=lambda x: x[0])
    holes, cur = [], span_from
    for s, e in done:
        if e < cur:
            continue
        if s > cur:
            holes.append((cur, min(s - 1, head)))
        cur = max(cur, e + 1)
        if cur > head:
            break
    if cur <= head:
        holes.append((cur, head))
    return holes


def run(mint, launch_ts, wall_min, conc, rps, base_url, key):
    fx = Fetcher(base_url, mint, key, TokenBucket(rps), conc)
    head = fx.head()
    if not head:
        return None, "SQD portal head 不可达"
    cache_fp, meta_fp, parts_dir = cache_paths(mint)
    parts_dir.mkdir(parents=True, exist_ok=True)
    meta = load_meta(meta_fp)
    old_edges = []
    if cache_fp.exists() and meta:
        try:
            with gzip.open(cache_fp, "rt") as f:
                old_edges = [tuple(json.loads(ln)) for ln in f if ln.strip()]
            log(f"缓存命中：{len(old_edges)} 条边，已完成区域 {len(meta.get('areas', []))} 个")
        except Exception as e:
            log(f"缓存损坏（{e}）——重新全量")
            old_edges, meta = [], {}

    now = int(time.time())
    if meta.get("from_slot"):
        span_from = from_slot = int(meta["from_slot"])
    else:
        back = int((now - (launch_ts or now - 90 * 86400)) * SQD_SLOT_RATE) + SQD_LAUNCH_PAD
        span_from = from_slot = max(1, head - back)
        meta = {"version": 2, "from_slot": from_slot, "launch_covered": False, "areas": []}

    deadline = time.time() + wall_min * 60
    adaptive = AdaptiveArea()
    holes = plan_areas(meta, span_from, head)
    total_span = sum(e - s + 1 for s, e in holes)
    log(f"head={head} 待扫空洞 {len(holes)} 段共 {total_span:,} slots，conc={conc} rps={rps}")

    lock = threading.Lock()
    meta_lock = threading.Lock()
    stats = {"slots": 0, "edges": 0, "areas": 0}
    gaps = []
    t0 = time.time()

    def persist_meta():
        with meta_lock:
            meta_fp.parent.mkdir(parents=True, exist_ok=True)
            meta_fp.write_text(json.dumps(meta))

    # 全局段队列：worker 每次只领"一个自适应区域"，剩余放回队尾——
    # 多 worker 并发消费同一个大空洞（v2.0 冒烟发现按空洞分配时首扫并发恒为 1，已改）
    import queue as _q
    segq = _q.Queue()
    for h in holes:
        segq.put((h[0], h[1], 0))          # (s, e, retry)
    inflight = [0]

    def worker():
        while True:
            if time.time() > deadline:
                return
            try:
                with lock:
                    s, e, retry = segq.get_nowait()
                    inflight[0] += 1
            except _q.Empty:
                with lock:
                    busy = inflight[0]
                if busy == 0:
                    return          # 队列空且无人在飞：真结束
                time.sleep(0.3)     # 有同伴在飞（可能马上切分放回新段）——等待再试
                continue
            size = adaptive.get()
            a_end = min(s + size - 1, e)
            if a_end < e:
                segq.put((a_end + 1, e, 0))    # 剩余放回，供其他 worker 领取
            t_a = time.time()
            edges, done_to, fin = fx.scan_area(s, a_end, deadline)
            adaptive.feedback(time.time() - t_a)
            if edges or fin:
                with open(parts_dir / f"{s}.jsonl", "w") as f:
                    for row in edges:
                        f.write(json.dumps(list(row), separators=(",", ":")) + "\n")
            if fin:
                with meta_lock:
                    meta["areas"].append({"s": s, "e": a_end, "done": True})
                with lock:
                    stats["slots"] += a_end - s + 1
                    stats["edges"] += len(edges)
                    stats["areas"] += 1
                    if stats["areas"] % 10 == 0:
                        el = time.time() - t0
                        rate = stats["slots"] / el if el else 0
                        eta = (total_span - stats["slots"]) / rate / 60 if rate else -1
                        log(f"[prog] areas={stats['areas']} slots={stats['slots']:,}/{total_span:,} "
                            f"edges={stats['edges']:,} {rate:,.0f} slots/s ETA {eta:.0f}min "
                            f"area_size={adaptive.get():,}")
                persist_meta()
            else:
                # 没扫完：吸收连续部分；剩余重新入队最多 2 轮，仍败才记 gap
                if done_to >= s:
                    with meta_lock:
                        meta["areas"].append({"s": s, "e": done_to, "done": True})
                    persist_meta()
                rest = (max(done_to + 1, s), a_end)
                if time.time() > deadline:
                    with lock:
                        gaps.append([rest[0], rest[1], "wall-clock"])
                elif retry < 2:
                    segq.put((rest[0], rest[1], retry + 1))
                else:
                    with lock:
                        gaps.append([rest[0], rest[1], "scan-fail"])
            with lock:
                inflight[0] -= 1

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(conc)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # 墙钟到点后队列里没人领的剩余段 → wall-clock 缺口
    while True:
        try:
            s, e, _ = segq.get_nowait()
            gaps.append([s, e, "wall-clock"])
        except _q.Empty:
            break

    # 合并：旧缓存边 + 全部分区文件 → 排序去重整写
    all_edges = list(old_edges)
    for pf in sorted(parts_dir.glob("*.jsonl")):
        with open(pf) as f:
            all_edges.extend(tuple(json.loads(ln)) for ln in f if ln.strip())
    if not all_edges:
        return None, "SQD 拉取无数据（含缓存为空）"
    all_edges = sorted(set(all_edges), key=lambda x: (x[1], x[0]))

    # 回补验证：起点没盖住发射 → 前移重扫（沿用 v1 语义，最多 2 次）
    if not meta.get("launch_covered"):
        for _ in range(2):
            has_mint = any(f == ZERO for _, _, f, _, _ in all_edges)
            min_ts = min((e[0] for e in all_edges if e[0]), default=None)
            if has_mint or not launch_ts or min_ts is None or min_ts <= launch_ts + 900:
                break
            if time.time() > deadline - 60:
                break
            shift = max(int(((min_ts or now) - launch_ts) * SQD_SLOT_RATE * 1.3), 100_000)
            new_from = max(1, from_slot - shift)
            log(f"回补：起点 {from_slot} 未盖住发射（最早记录 {min_ts} vs 发射 {launch_ts}），前移到 {new_from}")
            b_edges, b_to, b_fin = fx.scan_area(new_from, from_slot - 1, deadline)
            if not b_fin:
                gaps.append([new_from, from_slot - 1, "backfill-fail"])
                break
            all_edges = sorted(set(all_edges) | set(b_edges), key=lambda x: (x[1], x[0]))
            with meta_lock:
                meta["areas"].append({"s": new_from, "e": from_slot - 1, "done": True})
                meta["from_slot"] = from_slot = new_from
            persist_meta()

    # 落盘：整写 jsonl.gz（v1 同构），meta 记 launch_covered 与 gaps，分区文件清空
    try:
        with gzip.open(cache_fp, "wt") as f:
            for e_ in all_edges:
                f.write(json.dumps(list(e_)) + "\n")
        has_mint = any(f_ == ZERO for _, _, f_, _, _ in all_edges)
        covered = sorted(((a["s"], a["e"]) for a in meta["areas"] if a.get("done")),
                         key=lambda x: x[0])
        # 连续覆盖前沿（供增量续拉与 v1 兼容语义）
        front = from_slot - 1
        for s, e in covered:
            if s <= front + 1:
                front = max(front, e)
        meta.update({"launch_covered": bool(meta.get("launch_covered")) or has_mint,
                     "next_slot": front + 1, "gaps": gaps,
                     "updated": time.strftime("%Y-%m-%d %H:%M")})
        persist_meta()
        for pf in parts_dir.glob("*.jsonl"):
            pf.unlink()
    except Exception as e:
        log(f"缓存写入失败（不阻塞）：{e}")

    gap_msg = None
    if gaps:
        seg_s = "; ".join(f"[{g[0]},{g[1]}]({g[2]})" for g in gaps[:6])
        more = f" 等共{len(gaps)}段" if len(gaps) > 6 else ""
        gap_msg = f"存在未覆盖区间：{seg_s}{more}——重跑自动补扫，gaps 清零前不得进重放"
    min_ts = min((e[0] for e in all_edges if e[0]), default=0)
    if launch_ts and min_ts and min_ts > launch_ts + 6 * 3600 and not any(
            f == ZERO for _, _, f, _, _ in all_edges):
        g2 = f"重放起点晚于发射约 {(min_ts - launch_ts) / 3600:.0f} 小时——最早期建仓缺失"
        gap_msg = f"{gap_msg}；{g2}" if gap_msg else g2
    el = time.time() - t0
    log(f"完成：{len(all_edges):,} 条边，{stats['slots']:,} slots / {el:.0f}s "
        f"= {stats['slots'] / el if el else 0:,.0f} slots/s"
        + (f"；缺口：{gap_msg}" if gap_msg else "（无缺口）"))
    return all_edges, gap_msg


def main():
    ap = argparse.ArgumentParser(description="SQD portal Solana 转账边采集 v2（压缩+自适应并发+令牌桶）")
    ap.add_argument("mint")
    ap.add_argument("--launch-ts", type=int, default=0, help="发射 unix 秒，缺省回看 90 天")
    ap.add_argument("--wall-min", type=int, default=100, help="墙钟保险丝（分钟）")
    ap.add_argument("--conc", type=int, default=6, help="并发空洞数（带宽整形下 3 路已近饱和，留冗余）")
    ap.add_argument("--rps", type=float, default=4.0, help="全局请求速率上限/秒（防雪崩护栏；文档标称 2/s 实测对长流不生效、真瓶颈是带宽）")
    ap.add_argument("--url", default=DEF_URL, help="数据集端点（拿到 key 专属端点后换这里）")
    ap.add_argument("--key-file", default=os.path.expanduser("~/.config/sqd/api-key"))
    a = ap.parse_args()
    key = None
    try:
        key = Path(a.key_file).read_text().strip() or None
    except Exception:
        pass
    edges, gap = run(a.mint, a.launch_ts or None, a.wall_min, a.conc, a.rps, a.url, key)
    if edges is None:
        print(f"失败：{gap}", flush=True)
        sys.exit(1)
    print(f"完成：{len(edges)} 条转账边 → data/soltx-{a.mint.lower()}.jsonl.gz"
          + (f"\n缺口声明：{gap}" if gap else "（全量到链头，无缺口）"), flush=True)
    sys.exit(2 if gap else 0)


if __name__ == "__main__":
    main()
