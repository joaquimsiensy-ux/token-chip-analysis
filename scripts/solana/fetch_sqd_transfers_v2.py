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
      [--hypersync] [--hs-conc 2] [--hs-rps 4] [--hs-token-file ~/.config/hypersync/token]
输出（与 v1 完全同构，下游无感）：
  data/soltx-<小写mint>.jsonl.gz   每行 [ts, slot, from_owner, to_owner, amount_raw]
  data/soltx-<小写mint>.meta.json  断点元数据 v2（自动迁移 v1 格式；重跑自动续拉）
  data/soltx-<小写mint>.parts/     区域分片工作目录（合并成功后自动清空）

要点：
- 转账边=同 tx 内 owner 级净变动贪心配对（与 v1/window_fetch 同一解析核，量级与关系正确够聚类用）
- from/to 为 ZERO 哨兵（"0x"+40个0）即铸造/销毁；双过滤 postMint+preMint；失败交易剔除
- gaps 非空时 stdout 明确声明缺口区间——禁止无声吞洞
- key：公共端点 2026-07 实测不认证（key 无效也无害地带上）；拿到专属端点后 --url 换掉即生效

HyperSync 第二引擎（--hypersync，默认关）：
⚠⚠ 完备性验收不通过（2026-07-22 BONK 三区实测）——**禁止用于正式采集，仅限吞吐实验/对照**：
  - 历史区持久缺行且越老越糟：head-450万 段缺 3.6%、head-1450万 段缺 22%（成功交易的
    真实转账行，Helius getTransaction 链上终审证实为 HS 缺失而非 SQD 幽灵行）
  - 近端 head-13~33万 带存在乱序回填暂态洞（静默返回空+next_slot 照常推进，客户端无法
    从响应区分洞与真空窗；实测吞掉 81 条边后大部回填、洞头 18 slot 残留）
  - 仅摄取前沿附近（观测点 head-18万）逐行等于 SQD（含失败 tx/关户行/owner 语义全对齐），
    但"甜蜜区"边界不可探测且随回填漂移
机制说明（整合已完成，等 HyperSync GA 后重验收即可启用）：
- 端点 solana.hypersync.xyz（付费 key 按请求计费，量级忽略不计）；开跑前先探可用窗口：
  ① floor：from_slot=1 的 mint 过滤查询，首批行最小 slot（无行取 next_slot，保证 ≥ 真实窗起点）
  ② ceiling：token_balances 索引前沿滞后 /height 十几万 slot——空过滤器探针从 HS 链头
    几何回退找前沿，再减安全边距；探不出则退 head-60万 保守值
- ⚠ 窗外查询服务端**静默快进 next_slot 不报错**——绝不能靠"失败回落"兜底窗口边界，
  必须先探窗、窗外段全部派给 SQD
- 分段：窗内空洞按条带在两引擎交替分配（各采各段），HS 段失败自动回落 SQD 补采；
  SQD worker 在 HS 全忙时可接管 HS 未领段（带礼让条件防抢跑饿死；反向不行——HS 有窗口限制）
- 两引擎输出行格式/落盘/gaps 语义完全一致；失败交易两边同样剔除（HS 按 success 字段）
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

# ---- HyperSync 第二引擎常量（schema 实测 2026-07-22，见 data-pipeline-solana.md §13d）----
HS_DEF_URL = "https://solana.hypersync.xyz/query"
HS_DEF_TOKEN = os.path.expanduser("~/.config/hypersync/token")
HS_CLASH_PROXY = "http://127.0.0.1:7897"   # 直连间歇 SSL 断时自动切 clash
HS_HEAD_SAFETY = 50_000       # tb 索引前沿探测命中点再回退的安全边距（防前沿附近索引洞）
HS_HEAD_LAG_FALLBACK = 600_000  # 前沿探测失败时的保守上界回退（实测滞后 ~13 万，×4.6 余量）
HS_STRIPE_MAX = 100_000       # 双引擎交替条带宽上限（下限按窗内总量/8 自适应，保证两边都有活）
HS_AREA_INIT = 20_000         # HS 区域初值（单响应 ~千行级截断，起小步快反馈）


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


def _hs_flat(v):
    """HyperSync 响应数组是嵌套批次（外层批、内层行）——平铺成行列表。"""
    out = []
    for x in v or []:
        out.extend(x if isinstance(x, list) else [x])
    return out


class HyperSyncFetcher:
    """HyperSync Solana 第二引擎——与 Fetcher(SQD) 同构接口：scan_area(frm, to, deadline)
    → (edges, done_to, finished)，edges 行格式与 SQD 路径逐字段一致 [ts, slot, from, to, amt]。

    schema 实测事实（2026-07-22 探测定案）：
    - 查询体 from_slot / to_slot(exclusive)，token_balances 过滤器 mint 键（文档未载、实测有效）
    - 响应顶层直接放 token_balances/blocks/transactions 嵌套批次数组（无 data 包裹），游标 next_slot
    - blocks 自动 join 回带匹配块（block_time=unix 秒）；transactions 回带 success/err
    - 失败交易的 token_balances 行也会出现（pre==post）——按 success=False 显式剔除与 SQD 对齐
    - 金额是字符串；单响应行数截断按 next_slot 续拉
    - ⚠ 窗外查询静默快进 next_slot 不报错——窗口边界只能靠 probe_window 前置探测
    """
    FS = {"token_balance": ["slot", "mint", "owner", "account", "pre_amount",
                            "post_amount", "transaction_index"],
          "block": ["slot", "block_time"],
          "transaction": ["slot", "transaction_index", "success"]}

    def __init__(self, url, mint, token, bucket):
        self.url = url
        self.height_url = url.rsplit("/", 1)[0] + "/height"
        self.mint = mint
        self.bucket = bucket
        self.local = threading.local()
        self.headers = {"Content-Type": "application/json",
                        "Authorization": f"Bearer {token}"}
        self.proxies = None       # 直连失败一次后自动切 clash 并粘住（幂等写，无锁风险）

    def _sess(self):
        if not hasattr(self.local, "s"):
            self.local.s = requests.Session()
            self.local.s.headers.update(self.headers)
        return self.local.s

    def _req(self, method, url, **kw):
        """统一请求入口：直连失败（SSL/连接层）自动切 clash 代理重试一次并粘住。"""
        try:
            return self._sess().request(method, url, proxies=self.proxies, **kw)
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
            if self.proxies:
                raise
            alt = {"https": HS_CLASH_PROXY, "http": HS_CLASH_PROXY}
            r = self._sess().request(method, url, proxies=alt, **kw)
            self.proxies = alt
            log("HyperSync 直连断——已切 clash 代理")
            return r

    def height(self):
        try:
            self.bucket.take()
            r = self._req("GET", self.height_url, timeout=20)
            return int(r.text)
        except Exception:
            return None

    def _query(self, body, timeout=(15, 90)):
        self.bucket.take()
        r = self._req("POST", self.url, json=body, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"hs http {r.status_code}")
        return r.json()

    def probe_window(self, hs_head):
        """探可用窗口 → (floor, ceiling)；任一探不出返回 None 项（调用方决定降级）。
        floor：from_slot=1 的 mint 过滤查询——有行取最小行 slot；无行取 next_slot
              （服务端已扫过 [窗起点, next_slot) 且无该 mint 数据，两种取值都 ≥ 真实窗起点，
               派给 HS 的段必在窗内——floor 偏大只损失一点加速量，无完备性风险）。
        ceiling：空过滤器全网 tb 探针从 hs_head 几何回退找索引前沿（实测滞后 /height 十几万
              slot），命中点再减 HS_HEAD_SAFETY；探测异常退 hs_head - HS_HEAD_LAG_FALLBACK。"""
        floor = None
        try:
            j = self._query({"from_slot": 1,
                             "token_balances": [{"mint": [self.mint]}],
                             "field_selection": {"token_balance": ["slot"]}})
            rows = [x["slot"] for x in _hs_flat(j.get("token_balances")) if "slot" in x]
            floor = min(rows) if rows else j.get("next_slot")
            if not isinstance(floor, int) or floor <= 1:
                floor = None
        except Exception as e:
            log(f"HyperSync floor 探测失败：{str(e)[:80]}")
        ceiling = None
        try:
            lag = 32_000
            while lag <= 4_096_000:
                x = hs_head - lag
                if floor and x <= floor:
                    break
                j = self._query({"from_slot": x, "to_slot": x + 30,
                                 "token_balances": [{}],
                                 "field_selection": {"token_balance": ["slot"]}})
                if _hs_flat(j.get("token_balances")):
                    ceiling = x - HS_HEAD_SAFETY
                    break
                lag *= 2
        except Exception as e:
            log(f"HyperSync ceiling 探测异常：{str(e)[:80]}——退保守回退值")
        if ceiling is None:
            ceiling = hs_head - HS_HEAD_LAG_FALLBACK
        return floor, ceiling

    def scan_area(self, frm, to, deadline):
        """扫 [frm, to]（含界，与 SQD 版同约定），next_slot 续拉。→ (edges, done_to, finished)。"""
        edges, cur, fails = [], frm, 0
        while cur <= to:
            if time.time() > deadline:
                return edges, cur - 1, False
            body = {"from_slot": cur, "to_slot": to + 1,
                    "token_balances": [{"mint": [self.mint]}],
                    "field_selection": self.FS}
            try:
                j = self._query(body)
                nxt = j.get("next_slot")
                if not isinstance(nxt, int) or nxt <= cur:
                    raise RuntimeError(f"next_slot 异常 {nxt}")
            except Exception:
                fails += 1
                if fails > 5:
                    return edges, cur - 1, False
                time.sleep(1.5 * fails)
                continue
            fails = 0
            ts_map = {b["slot"]: b.get("block_time") or 0
                      for b in _hs_flat(j.get("blocks")) if "slot" in b}
            failed_tx = {(t.get("slot"), t.get("transaction_index"))
                         for t in _hs_flat(j.get("transactions"))
                         if t.get("success") is False}
            by_tx = defaultdict(dict)
            for rec in _hs_flat(j.get("token_balances")):
                key = (rec.get("slot"), rec.get("transaction_index"))
                if key[0] is None or key[1] is None or key in failed_tx:
                    continue
                owner = rec.get("owner")
                if not owner:
                    continue
                try:
                    dlt = int(rec.get("post_amount") or 0) - int(rec.get("pre_amount") or 0)
                except (ValueError, TypeError):
                    continue
                if dlt:
                    d = by_tx[key]
                    d[owner] = d.get(owner, 0) + dlt
            for (slot, _ti), delta in by_tx.items():
                ts = ts_map.get(slot, 0)
                for f, t, amt in pair_tx(delta):
                    edges.append((ts, slot, f, t, amt))
            cur = nxt
        return edges, to, True


class SegPool:
    """双引擎段池（纯数据结构，调用方持外层锁）。段=[s, e, retry, engine]。
    take：优先本引擎段；can_steal=True 时 SQD 可接管 HS 段（全能兜底），HS 永不偷
    （窗口限制）。⚠ 偷段必须带礼让条件（HS worker 全在飞才偷）——v2.1 首测 6 个 SQD
    线程启动瞬间把 HS 段全部抢走、HS 引擎空转，实测教训。"""
    def __init__(self):
        self.items = []

    def put(self, seg):
        self.items.append(seg)

    def take(self, engine, can_steal=False):
        for i, sg in enumerate(self.items):
            if sg[3] == engine:
                return self.items.pop(i)
        if can_steal and self.items:
            return self.items.pop(0)
        return None

    def drain(self):
        out, self.items = self.items, []
        return out


def split_engine_plan(holes, hs_lo, hs_hi):
    """空洞 → 引擎标注段列表。[hs_lo, hs_hi] 窗内部分按条带在两引擎交替，窗外全 SQD。
    条带宽 = clamp(窗内总量/8, 2000, HS_STRIPE_MAX)——保证小任务两引擎也都分到活。"""
    segs = []
    zone = sum(max(0, min(e, hs_hi) - max(s, hs_lo) + 1) for s, e in holes)
    if zone <= 0:
        return [[s, e, 0, "sqd"] for s, e in holes]
    stripe = max(2_000, min(HS_STRIPE_MAX, zone // 8 or 1))
    for s, e in holes:
        if s < hs_lo:
            segs.append([s, min(e, hs_lo - 1), 0, "sqd"])
        lo, hi = max(s, hs_lo), min(e, hs_hi)
        k, cur = 0, lo
        while cur <= hi:
            end = min(cur + stripe - 1, hi)
            segs.append([cur, end, 0, "hs" if k % 2 else "sqd"])
            k += 1
            cur = end + 1
        if e > hs_hi:
            segs.append([max(s, hs_hi + 1), e, 0, "sqd"])
    return segs


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


def run(mint, launch_ts, wall_min, conc, rps, base_url, key,
        hs_cfg=None, from_slot_cli=None, to_slot_cli=None):
    fx = Fetcher(base_url, mint, key, TokenBucket(rps), conc)
    head = fx.head()
    if not head:
        return None, "SQD portal head 不可达"
    if to_slot_cli:
        head = min(head, int(to_slot_cli))   # 调试/定段采集：上界压到指定 slot
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
        if from_slot_cli and int(from_slot_cli) != from_slot:
            log(f"已有 meta（from_slot={from_slot}）——忽略 --from-slot（增量语义优先）")
    elif from_slot_cli:
        span_from = from_slot = max(1, int(from_slot_cli))
        meta = {"version": 2, "from_slot": from_slot, "launch_covered": False, "areas": []}
    else:
        back = int((now - (launch_ts or now - 90 * 86400)) * SQD_SLOT_RATE) + SQD_LAUNCH_PAD
        span_from = from_slot = max(1, head - back)
        meta = {"version": 2, "from_slot": from_slot, "launch_covered": False, "areas": []}

    # ---- HyperSync 第二引擎初始化：探窗失败即降级纯 SQD（采集完备性优先）----
    fx_hs, hs_lo, hs_hi = None, None, None
    if hs_cfg:
        log("⚠ HyperSync 完备性验收不通过（历史区缺行 3.6-22%、近端有暂态洞，2026-07-22 "
            "实测）——本开关仅限吞吐实验/对照，正式采集产物必须用纯 SQD 重采或逐段复核")
        cand = HyperSyncFetcher(hs_cfg["url"], mint, hs_cfg["token"],
                                TokenBucket(hs_cfg["rps"]))
        hs_head = cand.height()
        if hs_head:
            # ceiling 探测必须基于 HS 自己的链头（tb 索引前沿是 HS 服务端属性），
            # 不能用被 --to-slot 压小的 head——否则探针在采集上界附近必然命中，
            # ceiling 被错误拉低、窗内段被挤给 SQD（2026-07-22 实测踩坑）
            hs_lo, hs_hi = cand.probe_window(hs_head)
            if hs_lo and hs_hi and hs_hi >= hs_lo:
                fx_hs = cand
                log(f"HyperSync 窗口 [{hs_lo:,}, {hs_hi:,}]（floor 探测 + tb 前沿-安全边距）")
            else:
                log(f"HyperSync 窗口无效（floor={hs_lo} ceiling={hs_hi}）——本次降级纯 SQD")
        else:
            log("HyperSync /height 不可达——本次降级纯 SQD")

    deadline = time.time() + wall_min * 60
    adaptive = AdaptiveArea()
    adaptive_hs = AdaptiveArea(HS_AREA_INIT)
    holes = plan_areas(meta, span_from, head)
    total_span = sum(e - s + 1 for s, e in holes)
    if fx_hs:
        segs = split_engine_plan(holes, hs_lo, hs_hi)
        hs_span = sum(sg[1] - sg[0] + 1 for sg in segs if sg[3] == "hs")
        log(f"head={head} 待扫空洞 {len(holes)} 段共 {total_span:,} slots，双引擎分段："
            f"SQD {sum(1 for sg in segs if sg[3] == 'sqd')} 段 / "
            f"HS {sum(1 for sg in segs if sg[3] == 'hs')} 段（{hs_span:,} slots），"
            f"conc={conc}+{hs_cfg['conc']} rps={rps}+{hs_cfg['rps']}")
    else:
        segs = [[s, e, 0, "sqd"] for s, e in holes]
        log(f"head={head} 待扫空洞 {len(holes)} 段共 {total_span:,} slots，conc={conc} rps={rps}")

    lock = threading.Lock()
    meta_lock = threading.Lock()
    stats = {"slots": 0, "edges": 0, "areas": 0, "slots_hs": 0}
    gaps = []
    t0 = time.time()

    def persist_meta():
        with meta_lock:
            meta_fp.parent.mkdir(parents=True, exist_ok=True)
            meta_fp.write_text(json.dumps(meta))

    # 全局段池：worker 每次只领"一个自适应区域"，剩余放回——多 worker 并发消费同一个大
    # 空洞（v2.0 冒烟发现按空洞分配时首扫并发恒为 1，已改）。双引擎时段带 engine 标注：
    # HS worker 只领 hs 段；SQD worker 优先 sqd 段、闲时接管 hs 段（全能兜底，反向不行）。
    pool = SegPool()
    for sg in segs:
        pool.put(sg)
    inflight = {"sqd": 0, "hs": 0}

    def worker(engine):
        fxl = fx_hs if engine == "hs" else fx
        ad = adaptive_hs if engine == "hs" else adaptive
        while True:
            if time.time() > deadline:
                return
            with lock:
                # SQD 接管 HS 段的礼让条件：HS worker 全在飞（忙不过来/失败重试中）
                # 才偷——否则那个段马上会被空闲 HS worker 领走，抢跑反而饿死第二引擎
                can_steal = engine == "sqd" and (
                    not fx_hs or inflight["hs"] >= hs_cfg["conc"])
                seg = pool.take(engine, can_steal)
                if seg:
                    inflight[engine] += 1
            if seg is None:
                with lock:
                    # HS 只等自家在飞段（可能切分放回 hs 段）；SQD 要等所有在飞
                    # （HS 失败段会回落成 sqd 段）——各自归零才真结束
                    busy = inflight["hs"] if engine == "hs" \
                        else inflight["sqd"] + inflight["hs"]
                if busy == 0:
                    return
                time.sleep(0.3)
                continue
            s, e, retry, _seng = seg
            size = ad.get()
            a_end = min(s + size - 1, e)
            if a_end < e:
                with lock:
                    pool.put([a_end + 1, e, 0, _seng])   # 剩余放回，保持原引擎标注
            t_a = time.time()
            edges, done_to, fin = fxl.scan_area(s, a_end, deadline)
            ad.feedback(time.time() - t_a)
            if edges or fin:
                with open(parts_dir / f"{s}.jsonl", "w") as f:
                    for row in edges:
                        f.write(json.dumps(list(row), separators=(",", ":")) + "\n")
            if fin:
                with meta_lock:
                    meta["areas"].append({"s": s, "e": a_end, "done": True, "eng": engine})
                with lock:
                    stats["slots"] += a_end - s + 1
                    stats["edges"] += len(edges)
                    stats["areas"] += 1
                    if engine == "hs":
                        stats["slots_hs"] += a_end - s + 1
                    if stats["areas"] % 10 == 0:
                        el = time.time() - t0
                        rate = stats["slots"] / el if el else 0
                        eta = (total_span - stats["slots"]) / rate / 60 if rate else -1
                        hs_part = f" hs={stats['slots_hs']:,}" if fx_hs else ""
                        log(f"[prog] areas={stats['areas']} slots={stats['slots']:,}/{total_span:,}"
                            f"{hs_part} edges={stats['edges']:,} {rate:,.0f} slots/s "
                            f"ETA {eta:.0f}min area_size={adaptive.get():,}")
                persist_meta()
            else:
                # 没扫完：吸收连续部分；HS 剩余立即回落 SQD 补采；SQD 剩余重试 2 轮仍败记 gap
                if done_to >= s:
                    with meta_lock:
                        meta["areas"].append({"s": s, "e": done_to, "done": True, "eng": engine})
                    with lock:
                        stats["slots"] += done_to - s + 1
                        if engine == "hs":
                            stats["slots_hs"] += done_to - s + 1
                    persist_meta()
                rest = (max(done_to + 1, s), a_end)
                if time.time() > deadline:
                    with lock:
                        gaps.append([rest[0], rest[1], "wall-clock"])
                elif engine == "hs":
                    log(f"HS 段 [{rest[0]},{rest[1]}] 失败——回落 SQD 补采")
                    with lock:
                        pool.put([rest[0], rest[1], 0, "sqd"])
                elif retry < 2:
                    with lock:
                        pool.put([rest[0], rest[1], retry + 1, "sqd"])
                else:
                    with lock:
                        gaps.append([rest[0], rest[1], "scan-fail"])
            with lock:
                inflight[engine] -= 1

    threads = [threading.Thread(target=worker, args=("sqd",), daemon=True)
               for _ in range(conc)]
    if fx_hs:
        threads += [threading.Thread(target=worker, args=("hs",), daemon=True)
                    for _ in range(hs_cfg["conc"])]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # 墙钟到点后池里没人领的剩余段 → wall-clock 缺口
    for sg in pool.drain():
        gaps.append([sg[0], sg[1], "wall-clock"])

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
    hs_note = ""
    if stats["slots_hs"]:
        hs_note = (f"；其中 HyperSync 采 {stats['slots_hs']:,} slots"
                   f"——⚠该部分存在完备性风险（服务端洞静默），正式使用前需 SQD 复核")
    log(f"完成：{len(all_edges):,} 条边，{stats['slots']:,} slots / {el:.0f}s "
        f"= {stats['slots'] / el if el else 0:,.0f} slots/s"
        + (f"；缺口：{gap_msg}" if gap_msg else "（无缺口）") + hs_note)
    return all_edges, gap_msg


def main():
    ap = argparse.ArgumentParser(description="SQD portal Solana 转账边采集 v2（压缩+自适应并发+令牌桶+HyperSync 第二引擎）")
    ap.add_argument("mint")
    ap.add_argument("--launch-ts", type=int, default=0, help="发射 unix 秒，缺省回看 90 天")
    ap.add_argument("--wall-min", type=int, default=100, help="墙钟保险丝（分钟）")
    ap.add_argument("--conc", type=int, default=6, help="并发空洞数（带宽整形下 3 路已近饱和，留冗余）")
    ap.add_argument("--rps", type=float, default=4.0, help="全局请求速率上限/秒（防雪崩护栏；文档标称 2/s 实测对长流不生效、真瓶颈是带宽）")
    ap.add_argument("--url", default=DEF_URL, help="数据集端点（拿到 key 专属端点后换这里）")
    ap.add_argument("--key-file", default=os.path.expanduser("~/.config/sqd/api-key"))
    ap.add_argument("--hypersync", action="store_true",
                    help="启用 HyperSync 第二引擎双引擎分段并行（默认关。⚠完备性验收不通过："
                         "历史区缺行 3.6-22%%、近端有暂态洞——仅限吞吐实验/对照，禁止正式采集；"
                         "滚动窗外区间自动全给 SQD，HS 段失败自动回落 SQD）")
    ap.add_argument("--hs-url", default=HS_DEF_URL, help="HyperSync Solana 查询端点")
    ap.add_argument("--hs-token-file", default=HS_DEF_TOKEN,
                    help="HyperSync 付费 token 文件（按请求计费，量级忽略不计）")
    ap.add_argument("--hs-conc", type=int, default=2,
                    help="HS 并发段数（POC 实测双通道叠加即近 2 倍，保守默认 2）")
    ap.add_argument("--hs-rps", type=float, default=4.0, help="HS 请求速率护栏/秒")
    ap.add_argument("--from-slot", type=int, default=0,
                    help="调试/定段采集：直接指定起点 slot（仅首采无 meta 时生效）")
    ap.add_argument("--to-slot", type=int, default=0,
                    help="调试/定段采集：采集上界 slot（默认链头）")
    a = ap.parse_args()
    key = None
    try:
        key = Path(a.key_file).read_text().strip() or None
    except Exception:
        pass
    hs_cfg = None
    if a.hypersync:
        try:
            hs_token = Path(a.hs_token_file).read_text().strip()
            if not hs_token:
                raise ValueError("token 文件为空")
        except Exception as e:
            sys.exit(f"[fatal] --hypersync 需要有效 token（{a.hs_token_file}）：{e}")
        hs_cfg = {"url": a.hs_url, "token": hs_token, "conc": a.hs_conc, "rps": a.hs_rps}
    edges, gap = run(a.mint, a.launch_ts or None, a.wall_min, a.conc, a.rps, a.url, key,
                     hs_cfg=hs_cfg, from_slot_cli=a.from_slot or None,
                     to_slot_cli=a.to_slot or None)
    if edges is None:
        print(f"失败：{gap}", flush=True)
        sys.exit(1)
    print(f"完成：{len(edges)} 条转账边 → data/soltx-{a.mint.lower()}.jsonl.gz"
          + (f"\n缺口声明：{gap}" if gap else "（全量到链头，无缺口）"), flush=True)
    sys.exit(2 if gap else 0)


if __name__ == "__main__":
    main()
