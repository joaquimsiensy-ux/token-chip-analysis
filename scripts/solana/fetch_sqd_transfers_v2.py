#!/usr/bin/env python3
"""SQD portal 全量拉取 Solana SPL 代币转账边 v2——压缩传输+自适应区域并发+全局令牌桶。

来源：Solana 采集加速工程 2026-07-21（@CX 交叉复核定案）。
相对旧采集器的三刀（实测依据见 data-pipeline-solana.md §13）：
  1. requests.Session 替代逐请求 curl 子进程：连接复用 + 默认 gzip 协商
     （明文传输是旧采集器慢的主因：wSOL 压测明文 4.65 slots/s vs 压缩 98 slots/s ≈ 21 倍）
  2. 自适应区域并发：区域大小按实测耗时自动伸缩（发射窗自动缩小、死亡期自动放大），
     失败区域进 gaps 继续别的——不再像旧采集器那样"第一个未完段之后整体丢弃"
  3. 全局令牌桶限速：默认 1.6 请求/秒（公共端点文档限 20 次/10 秒），并发共享一个桶

用法（cd 到工作目录跑，缓存写入 ./data/）：
  python3 fetch_sqd_transfers_v2.py <mint> [--launch-ts <unix秒>] [--wall-min 100]
      [--conc 6] [--rps 1.6] [--url <端点>] [--key-file ~/.config/sqd/api-key]
      [--hypersync  # v4 下硬拒 exit 2]
输出（现役 v4 缓存格式）：
  data/soltx-<sha256(原始mint)>.jsonl.gz
    每行 [ts, slot, tx_index, -1, from_owner, to_owner, amount_raw]
  data/soltx-<sha256>.meta.json  绑定 mint/endpoint/采集器哈希/finalized 上界的 v4 元数据
  data/soltx-<sha256>.parts/     区域分片工作目录（合并成功后自动清空）

要点：
- 转账边=同 tx 内 owner 级净变动贪心配对（与 window_fetch 同一解析核，量级与关系正确够聚类用）
- from/to 为 ZERO 哨兵（"0x"+40个0）即铸造/销毁；双过滤 postMint+preMint；失败交易剔除
- gaps 非空时 stdout 明确声明缺口区间——禁止无声吞洞
- key：公共端点 2026-07 实测不认证（key 无效也无害地带上）；拿到专属端点后 --url 换掉即生效

2026-07-26 两处缺陷修复（BONK 全史采集实测暴露，详见 data-pipeline-solana-capture.md §13b）：
  1. 伪 scan-fail：SQD 对"区间内一个块都没有"（Solana skipped slot 串）正确返回 200+0 字节，
     旧版把零行并进失败重试、6 次后记 gaps['scan-fail'] → 以 gaps==[] 为完成判据的调度器
     永不收敛（BONK 六分片 365 段、watchdog 每 20 分钟重启一次、S00R 被重启 59 次空转约 24h）。
     现按"HTTP 200 + 流完整读完 + 零行"判真空：跨度 ≤ EMPTY_MAX 直接放行，更宽的区间用
     轻量块探针实证无块才放行（探针 = 只要 block.number 不带过滤器，实测封顶 640 字节）。
  2. 收尾 OOM：旧版收尾把旧缓存 + 全部 parts 载入内存做 sorted(set(...))，BONK 单分片
     3900-5900 万行峰值 13-19GB，16GB 机器必炸；且 OOM 落在写 gz 中途会留下损坏缓存、
     下次启动触发"重新全量"。现改为规模超限（MERGE_INMEM_MAX_ROWS）自动降级 DuckDB 磁盘
     外排，且两条路径一律"临时文件写完再原子 rename"——中途死也不会留下半截 gz。

HyperSync 通道已硬禁：历史实测存在持久缺行和静默前移；v4 的 CLI `--hypersync` 与直接
`run(hs_cfg=...)` 均在首个业务请求前 exit 2，不签发缓存或 meta。
"""
import argparse, gzip, hashlib, json, os, shutil, sys, threading, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from endpoint_identity import endpoint_fingerprint
from proxy_config import redact_proxy, resolve_proxy
from solana_attested_session import SolanaAttestedSession
from solana_sqd_dataset import (SOLANA_SQD_DATASET_ID,
                                SolanaSqdDatasetAdapter)
from spl_edge_core import (EDGE_SCHEMA_FIELDS, EDGE_SEMANTICS,
                           INSTR_INDEX_TX_NET, ORDER_GRANULARITY_TX,
                           ZERO_OWNER as ZERO, dedupe_transaction_sources,
                           edge_sort_key, owner_deltas_by_tx, pair_tx,
                           soltx_cache_paths, transaction_status_by_index,
                           validate_edge_row, validate_tx_index)

try:
    import requests
except ImportError:
    sys.exit("[fatal] 需要 requests（本机既有环境应自带；没有则 pip3 install requests）")

try:
    import duckdb            # 仅收尾外排用；缺失时自动退回全内存收尾（小样本无影响）
except ImportError:
    duckdb = None

DEF_URL = "https://portal.sqd.dev/datasets/solana-mainnet"
SQD_SLOT_RATE = 2.51          # slot/秒近似斜率（仅起点估算用，回补环兜底精度）
SQD_LAUNCH_PAD = 150_000      # 发射点前置缓冲（约 16.6 小时）
AREA_INIT = 100_000           # 初始区域大小（slot）；按耗时自适应
AREA_MIN, AREA_MAX = 10_000, 1_000_000
AREA_T_FAST, AREA_T_SLOW = 30, 180   # 区域耗时 <30s 翻倍 / >180s 减半

# ---- 零行响应判真空的闸门（2026-07-26 修伪 scan-fail）----
# BONK 现场 365 段空洞实测跨度 1-13 slot（中位 2）＝典型 skipped slot 串；500 是保守上限。
# 超过闸门的零行区间不直接放行——走块探针实证（probe_blocks），探不出块才判完成。
EMPTY_MAX = 500

# ---- 收尾合并的内存闸门（2026-07-26 修 OOM）----
# 全内存 sorted(set(...)) 每条边实测约 350 字节（5 元组 + 2 个 base58 字符串 + set 哈希表开销），
# 800 万行 ≈ 2.8GB 峰值；超过即降级 DuckDB 磁盘外排（实测 1.55 亿行 / memory_limit 4GB / 约 11 分钟）。
MERGE_INMEM_MAX_ROWS = 8_000_000
MERGE_MEM_LIMIT = "4GB"
MERGE_THREADS = 4

CACHE_SCHEMA = "sqd-solana-cache/v4"
CACHE_VERSION = 4
COLLECTOR_ID = "fetch_sqd_transfers_v2.py/v4"
DEDUPE_IDENTITY = "slot-txindex-digest/v1"
SUPPLY_DELTA_SOURCE = "tokenBalances-owner-net"

# ---- HyperSync 第二引擎常量（schema 实测 2026-07-22，见 data-pipeline-solana.md §13d）----
HS_DEF_URL = "https://solana.hypersync.xyz/query"
HS_DEF_TOKEN = os.path.expanduser("~/.config/hypersync/token")
HS_FALLBACK_PROXY = None       # 由 resolve_proxy() 解析；直连异常后才允许切换并粘住
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


class Fetcher:
    def __init__(self, base_url, mint, key, bucket, conc, empty_max=EMPTY_MAX):
        self.stream_url = base_url.rstrip("/") + "/stream"
        self.head_url = base_url.rstrip("/") + "/head"
        self.mint = mint
        self.bucket = bucket
        self.empty_max = empty_max
        # 判定为"区间内无块"的空区间审计清单（list.append 在 GIL 下原子，多 worker 共享安全）
        self.empty_hits = []
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

    def probe_blocks(self, frm, to):
        """轻量块探针：[frm, to] 内是否存在任何块 → True=有 / False=确无 / None=探针自身失败。

        只要 block.number、不带任何 tokenBalance 过滤器——服务端扫描上限自动截断在 20 行，
        实测封顶 640 字节 / 0.4-0.8 秒（2026-07-26）。用途是把"零行响应"的两种成因分开：
        Solana skipped slot 串（真无块，可判完成）vs 服务端在过滤路径上异常（必须重试）。
        ⚠ 204=区间超出服务端已索引范围，此时判完成会漏数据——归 None 按失败处理。"""
        try:
            self.bucket.take()
            r = self._sess().post(self.stream_url, timeout=(15, 60),
                                  json={"type": "solana", "fromBlock": frm, "toBlock": to,
                                        "fields": {"block": {"number": True}}})
            if r.status_code != 200:
                return None
            return any(ln.strip() for ln in r.text.splitlines())
        except Exception:
            return None

    def _empty_ok(self, cur, to):
        """零行响应能否判定为"区间内真的没有块"（判完成而非失败重试）。

        实证（2026-07-26，BONK 现场四段复验）：这些区间去掉 mint 过滤依然零行，而包围 ±60
        有 103-112 个块——即 Solana skipped slot 串。SQD 对"有块但该 mint 无数据"的区间会
        回稀疏 header 行标记进度（实测 100 万 slot 空区间回 20 行），故零行只对应"无块"。"""
        span = to - cur + 1
        if span <= self.empty_max:
            self.empty_hits.append([cur, to, "span"])
            log(f"空区间 [{cur},{to}]（{span} slot ≤ EMPTY_MAX={self.empty_max}，区间内无块）"
                f"——判完成，不计 scan-fail")
            return True
        got = self.probe_blocks(cur, to)
        if got is False:
            self.empty_hits.append([cur, to, "probe"])
            log(f"空区间 [{cur},{to}]（{span} slot > EMPTY_MAX，块探针实证无块）——判完成")
            return True
        if got is True:
            log(f"⚠ [{cur},{to}] 主查询零行但块探针查到块——服务端过滤路径异常，按失败重试")
        return False

    def scan_area(self, frm, to, deadline):
        """扫 [frm, to]，服务端响应上限自动截断、客户端按最后 slot 续拉。
        → (edges, done_to, finished)。edges 为 v4 交易身份 7 元组。"""
        body_fields = {"block": {"number": True, "timestamp": True},
                       "transaction": {"transactionIndex": True, "err": True},
                       "tokenBalance": {"transactionIndex": True, "account": True,
                                        "preMint": True, "postMint": True,
                                        "preOwner": True, "postOwner": True,
                                        "preAmount": True, "postAmount": True}}
        filt = [{"postMint": [self.mint], "transaction": True},
                {"preMint": [self.mint], "transaction": True}]
        edges, cur, fails = [], frm, 0
        while cur <= to:
            if time.time() > deadline:
                return edges, cur - 1, False
            body = {"type": "solana", "fromBlock": cur, "toBlock": to,
                    "fields": body_fields, "tokenBalances": filt}
            last = None
            complete = False     # HTTP 200 且响应流完整读完（无截断行、无连接层异常）
            truncated = False
            try:
                self.bucket.take()
                # timeout=(连接, 字节间隔)——流式响应逐行到达，字节间隔 60s 足够
                with self._sess().post(self.stream_url, json=body, stream=True,
                                       timeout=(15, 60)) as r:
                    if r.status_code != 200:
                        raise RuntimeError("http 204（区间超出服务端已索引范围）"
                                           if r.status_code == 204 else f"http {r.status_code}")
                    for ln in r.iter_lines(decode_unicode=True):
                        if not ln:
                            continue
                        try:
                            b = json.loads(ln)
                        except ValueError:
                            truncated = True
                            break   # 截断行：按已解析部分推进（window_fetch 同款处理）
                        hdr = b.get("header", {})
                        last = hdr.get("number", last)
                        tbs = b.get("tokenBalances") or []
                        if not tbs:
                            continue
                        ts = hdr.get("timestamp") or 0
                        errmap = transaction_status_by_index(b.get("transactions") or [])
                        successful = []
                        for rec in tbs:
                            if not isinstance(rec, dict):
                                raise TypeError("tokenBalance record must be an object")
                            ti = validate_tx_index(rec.get("transactionIndex"))
                            if ti not in errmap:
                                raise ValueError(
                                    f"tokenBalance tx_index={ti} has no transaction status")
                            if errmap[ti] is None:
                                successful.append(rec)
                        by_tx = owner_deltas_by_tx(successful, self.mint)
                        for ti, delta in by_tx.items():
                            for f, t, amt in pair_tx(delta):
                                edges.append((ts, hdr["number"], ti,
                                              INSTR_INDEX_TX_NET, f, t, amt))
                    complete = not truncated
            except Exception as e:
                last = None
                err = str(e)[:80]
            if last is None:
                # 零行 ≠ 失败：complete 为真说明服务端 200 正常应答且流完整读完，
                # 此时零行的唯一成因是"区间内没有块"（见 _empty_ok 的实证注释）。
                # 旧版无差别并进重试→6 次后记 gaps['scan-fail']→gaps 永不清零。
                if complete and self._empty_ok(cur, to):
                    return edges, to, True
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
    """历史实验实现，仅保留考证；v4 CLI 与 run() 均在实例化前硬拒。

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

    def __init__(self, url, mint, token, bucket,
                 fallback_proxy=HS_FALLBACK_PROXY):
        self.url = url
        self.height_url = url.rsplit("/", 1)[0] + "/height"
        self.mint = mint
        self.bucket = bucket
        self.local = threading.local()
        self.headers = {"Content-Type": "application/json",
                        "Authorization": f"Bearer {token}"}
        self.fallback_proxy = fallback_proxy
        self.proxies = None       # 直连失败一次后切候选代理并粘住（幂等写，无锁风险）

    def _sess(self):
        if not hasattr(self.local, "s"):
            self.local.s = requests.Session()
            self.local.s.headers.update(self.headers)
        return self.local.s

    def _req(self, method, url, **kw):
        """统一请求入口：直连失败后切已解析候选代理重试一次并粘住。"""
        try:
            return self._sess().request(method, url, proxies=self.proxies, **kw)
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
            if self.proxies:
                raise
            if not self.fallback_proxy:
                raise
            alt = {"https": self.fallback_proxy, "http": self.fallback_proxy}
            r = self._sess().request(method, url, proxies=alt, **kw)
            self.proxies = alt
            log(f"HyperSync 直连断——已切解析代理 {redact_proxy(self.fallback_proxy)}")
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
    return soltx_cache_paths(address, Path("data"))


def load_meta(meta_fp):
    """Read one v4 cache meta; malformed or non-v4 files are not resumable."""
    if not meta_fp.exists():
        return {}
    try:
        m = json.loads(meta_fp.read_text())
    except Exception as exc:
        raise ValueError(f"invalid SQD cache meta: {exc}") from exc
    if m.get("schema") == CACHE_SCHEMA and m.get("version") == CACHE_VERSION:
        return m
    return {}


def collector_sha256():
    return hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()


def cache_identity(mint, endpoint, frozen_collector_sha256=None):
    fingerprint = endpoint_fingerprint(endpoint)
    frozen = frozen_collector_sha256 or collector_sha256()
    if (not isinstance(frozen, str) or len(frozen) != 64
            or any(ch not in "0123456789abcdef" for ch in frozen)):
        raise ValueError("collector_sha256 must be 64 lowercase hex characters")
    return {"schema": CACHE_SCHEMA, "mint": mint,
            "endpoint": fingerprint["public_origin"],
            "endpoint_sha256": fingerprint["sha256"],
            "collector": COLLECTOR_ID,
            "collector_sha256": frozen,
            "edge_schema": list(EDGE_SCHEMA_FIELDS),
            "edge_semantics": EDGE_SEMANTICS,
            "order_granularity": ORDER_GRANULARITY_TX,
            "order_exact": False,
            "dedupe_identity": DEDUPE_IDENTITY,
            "supply_delta_source": SUPPLY_DELTA_SOURCE}


def normalize_cache_identity(meta, mint, endpoint, frozen_collector_sha256=None):
    """Validate a v4 cache identity and return its secret-safe canonical copy."""
    if not meta or meta.get("finalized_upper_slot") is None:
        return None
    expected = cache_identity(mint, endpoint, frozen_collector_sha256)
    if any(meta.get(key) != value for key, value in expected.items()):
        return None
    upper = meta.get("finalized_upper_slot")
    if isinstance(upper, bool) or not isinstance(upper, int) or upper < 0:
        return None
    return dict(meta)


def cache_identity_matches(meta, mint, endpoint, frozen_collector_sha256=None):
    return normalize_cache_identity(
        meta, mint, endpoint, frozen_collector_sha256) is not None


def _cache_upgrade_required(detail):
    log("[fail-closed] " + detail
        + "；格式升级需全量重采，旧缓存请改名归档")
    raise SystemExit(2)


def preflight_v4_cache(cache_fp, meta_fp, parts_dir, mint, endpoint,
                       frozen_collector_sha256):
    """Reject every legacy/orphan cache shape before network or parts mutation."""
    part_files = sorted(parts_dir.glob("*.jsonl")) if parts_dir.exists() else []
    if meta_fp.exists():
        try:
            raw_meta = json.loads(meta_fp.read_text())
        except Exception as exc:
            _cache_upgrade_required(f"SQD cache meta 无法解析: {exc}")
        if (raw_meta.get("schema") != CACHE_SCHEMA
                or raw_meta.get("version") != CACHE_VERSION):
            _cache_upgrade_required(
                f"检测到旧 SQD cache meta {raw_meta.get('schema')!r}")
        meta = raw_meta
        if normalize_cache_identity(
                meta, mint, endpoint, frozen_collector_sha256) is None:
            log("[fail-closed] SQD v4 cache meta 与 mint/endpoint/采集器身份不一致；"
                "不得跨标的、跨端点或跨采集器续用")
            raise SystemExit(2)
    else:
        meta = {}
        if cache_fp.exists() or part_files:
            _cache_upgrade_required("检测到缺少 v4 meta 的旧缓存或 .parts")

    for part in part_files:
        line_no = 0
        try:
            with part.open() as handle:
                for line_no, line in enumerate(handle, 1):
                    if line.strip():
                        validate_edge_row(json.loads(line))
        except Exception as exc:
            _cache_upgrade_required(
                f"检测到旧/非法 .parts 行 {part}:{line_no}: {exc}")
    return meta


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


# ============ 收尾合并（2026-07-26 OOM 修复：超限自动降级 DuckDB 磁盘外排）============

def _sort_key(e):
    """Compatibility wrapper around the shared v4 canonical order."""
    return edge_sort_key(e)


def probe_cache(cache_fp):
    """旧缓存流式体检 → (行数, 是否完好)。

    块读计数、不建列表——旧版开局就把整份缓存 load 成 list，本身就是 OOM 点之一
    （BONK 单分片 3900-5900 万行）。读到末尾时 gzip 自动校验 CRC＝完整性检查仍在，
    另抽验前几行 JSON 可解析防"能解压但内容不是边"。"""
    n, head = 0, []
    try:
        with gzip.open(cache_fp, "rb") as f:
            first = f.read(1 << 16)
            head = first.split(b"\n")[:5]
            n += first.count(b"\n")
            for chunk in iter(lambda: f.read(1 << 22), b""):
                n += chunk.count(b"\n")
        for ln in head:
            if ln.strip():
                json.loads(ln)
    except Exception as e:
        log(f"缓存体检失败（{str(e)[:80]}）")
        return 0, False
    return n, True


def _part_rows_estimate(files):
    """parts 行数估算：总字节 / 采样均行长。只用于选收尾路径，不需要精确。"""
    total = sum(p.stat().st_size for p in files)
    if not total:
        return 0
    with open(files[0], "rb") as f:
        sample = f.read(1 << 18)
    lines = sample.count(b"\n")
    return int(total / max((len(sample) / lines) if lines else 165.0, 1.0))


def _atomic_gz(cache_fp, lines):
    """临时文件写完再 os.replace ——中途 OOM/断电也不会留下半截 gz。

    旧版直接 gzip.open(cache_fp) 边算边写，OOM 落在写入中途会留下损坏缓存，
    下次启动触发"缓存损坏——重新全量"，几小时工作作废（BONK 实测风险点）。"""
    tmp = cache_fp.parent / (cache_fp.name + ".tmp")
    try:
        with gzip.open(tmp, "wt") as f:
            for ln in lines:
                f.write(ln + "\n")
        os.replace(tmp, cache_fp)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def logical_edge_evidence(cache_fp):
    """Recompute replay-compatible logical SHA-256 and row count from final gz."""
    digest = hashlib.sha256()
    rows = 0
    with gzip.open(cache_fp, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                edge = validate_edge_row(json.loads(line))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"invalid finalized v4 edge row at line {line_no}: {exc}") from exc
            digest.update(
                (json.dumps(list(edge), ensure_ascii=False) + "\n").encode("utf-8"))
            rows += 1
    if rows == 0:
        raise ValueError("finalized v4 edge cache is empty")
    return digest.hexdigest(), rows


class MemMerger:
    """全内存收尾：按来源比较完整交易 digest，不按边内容 DISTINCT。"""
    mode = "inmem"

    def __init__(self, cache_fp, parts_dir, part_files, old_ok):
        self.cache_fp = cache_fp
        self.sources = []
        if old_ok and cache_fp.exists():
            with gzip.open(cache_fp, "rt") as f:
                self.sources.append((str(cache_fp),
                                     [json.loads(ln) for ln in f if ln.strip()]))
        for pf in part_files:
            with open(pf) as f:
                self.sources.append((str(pf),
                                     [json.loads(ln) for ln in f if ln.strip()]))
        self.edges = dedupe_transaction_sources(self.sources)

    def rows(self):
        return len(self.edges)

    def stats(self):
        return (any(e[4] == ZERO for e in self.edges),
                min((e[0] for e in self.edges if e[0]), default=None))

    def absorb(self, edges):
        self.sources.append((f"backfill-{len(self.sources)}", list(edges)))
        self.edges = dedupe_transaction_sources(self.sources)

    def finalize(self):
        has_mint, min_ts = self.stats()
        rows = sorted(self.edges, key=_sort_key)
        if not rows:
            return {"rows": 0, "has_mint": False, "min_ts": None}   # 零边不动缓存（同旧版语义）
        _atomic_gz(self.cache_fp, (json.dumps(list(e)) for e in rows))
        return {"rows": len(rows), "has_mint": has_mint, "min_ts": min_ts}


class ExtMerger:
    """DuckDB 外排收尾：按 source 计算完整交易 digest 并拒绝身份冲突。"""
    mode = "duckdb-external"
    RC = "columns={'x':'VARCHAR'}, header=false, quote='', delim=e'\\x07'"

    def __init__(self, cache_fp, parts_dir, part_files, old_ok):
        self.cache_fp = cache_fp
        self.parts_dir = parts_dir
        self.parts = list(part_files)
        self.old = cache_fp if (old_ok and cache_fp.exists()) else None
        self.tmpdir = parts_dir.parent / "_merge_tmp"
        self.tmpdir.mkdir(parents=True, exist_ok=True)
        self._cache, self._n_bf = None, 0

    def _con(self):
        con = duckdb.connect()
        con.execute(f"SET memory_limit='{MERGE_MEM_LIMIT}'")
        con.execute(f"SET threads={MERGE_THREADS}")
        con.execute(f"SET temp_directory='{self.tmpdir}'")
        con.execute("SET preserve_insertion_order=false")
        return con

    def _src(self):
        segs = []
        if self.parts:
            segs.append(
                f"SELECT filename AS src_id, x FROM read_csv("
                f"{[str(p) for p in self.parts]!r}, {self.RC}, filename=true)")
        if self.old:
            segs.append(
                f"SELECT {str(self.old)!r} AS src_id, x FROM read_csv("
                f"{[str(self.old)]!r}, {self.RC}, compression='gzip')")
        return " UNION ALL ".join(segs)

    def _ctes(self):
        src = self._src()
        return f"""
            raw AS (
              SELECT src_id, x, try_cast(x AS JSON) AS j FROM ({src})
            ),
            parsed AS (
              SELECT src_id, x, j, json_array_length(j) AS width,
                     json_type(j, '$[4]') AS f_type,
                     json_type(j, '$[5]') AS t_type,
                     json_extract_string(j, '$[0]') AS ts_s,
                     json_extract_string(j, '$[1]') AS slot_s,
                     json_extract_string(j, '$[2]') AS tx_s,
                     json_extract_string(j, '$[3]') AS instr_s,
                     json_extract_string(j, '$[4]') AS f,
                     json_extract_string(j, '$[5]') AS t,
                     json_extract_string(j, '$[6]') AS amt
              FROM raw
            ),
            canonical_source_rows AS (
              SELECT DISTINCT src_id,
                     CAST(ts_s AS BIGINT) AS ts,
                     CAST(slot_s AS BIGINT) AS slot,
                     CAST(tx_s AS BIGINT) AS tx_index,
                     CAST(instr_s AS BIGINT) AS instr_index,
                     f, t, amt
              FROM parsed
            ),
            source_tx AS (
              SELECT src_id, slot, tx_index,
                     sha256(string_agg(
                       '[' || ts || ',' || slot || ',' || tx_index || ',' || instr_index
                       || ',' || to_json(f) || ',' || to_json(t) || ',' || amt || ']',
                       '\\n' ORDER BY f, t, amt, ts, instr_index)) AS tx_digest
              FROM canonical_source_rows
              GROUP BY src_id, slot, tx_index
            ),
            tx_choice AS (
              SELECT slot, tx_index, min(src_id) AS keep_source
              FROM source_tx
              GROUP BY slot, tx_index
            ),
            canonical AS (
              SELECT r.ts, r.slot, r.tx_index, r.instr_index, r.f, r.t, r.amt
              FROM canonical_source_rows r
              JOIN tx_choice c ON r.slot = c.slot AND r.tx_index = c.tx_index
                              AND r.src_id = c.keep_source
            )
        """

    def _validate(self, con):
        invalid = con.execute(f"""
            WITH {self._ctes()}
            SELECT src_id, x FROM parsed
            WHERE j IS NULL OR width <> {len(EDGE_SCHEMA_FIELDS)}
               OR NOT coalesce(regexp_full_match(ts_s, '[0-9]+'), false)
               OR NOT coalesce(regexp_full_match(slot_s, '[0-9]+'), false)
               OR NOT coalesce(regexp_full_match(tx_s, '[0-9]+'), false)
               OR try_cast(ts_s AS BIGINT) IS NULL
               OR try_cast(slot_s AS BIGINT) IS NULL
               OR try_cast(tx_s AS BIGINT) IS NULL
               OR instr_s <> '{INSTR_INDEX_TX_NET}'
               OR f_type <> 'VARCHAR' OR t_type <> 'VARCHAR'
               OR f IS NULL OR f = '' OR t IS NULL OR t = ''
               OR NOT coalesce(regexp_full_match(amt, '[0-9]+'), false)
               OR coalesce(regexp_full_match(amt, '0+'), false)
            LIMIT 1
        """).fetchone()
        if invalid:
            raise ValueError(
                f"invalid v4 edge row in {invalid[0]}; legacy/mixed rows require full recapture")
        conflict = con.execute(f"""
            WITH {self._ctes()}
            SELECT slot, tx_index, count(DISTINCT tx_digest)
            FROM source_tx GROUP BY slot, tx_index
            HAVING count(DISTINCT tx_digest) > 1 LIMIT 1
        """).fetchone()
        if conflict:
            raise RuntimeError(
                "conflicting transaction edge sets for "
                f"slot={conflict[0]} tx_index={conflict[1]}")

    def rows(self):
        return None      # 精确行数要全扫，收尾 COPY 时自然得到

    def stats(self):
        if self._cache is not None:
            return self._cache
        src = self._src()
        if not src:
            self._cache = (False, None)
            return self._cache
        con = self._con()
        try:
            self._validate(con)
            row = con.execute(f"""
                WITH {self._ctes()}
                SELECT max(CASE WHEN f = ? THEN 1 ELSE 0 END),
                       min(CASE WHEN ts <> 0 THEN ts END)
                FROM canonical
            """, [ZERO]).fetchone()
        finally:
            con.close()
        self._cache = (bool(row[0]), row[1])
        return self._cache

    def absorb(self, edges):
        """回补边落成新 part 文件参与最终外排（外排路径不把边留在内存里）。"""
        if not edges:
            return
        self._n_bf += 1
        fp = self.parts_dir / f"backfill_{self._n_bf}.jsonl"
        with open(fp, "w") as f:
            for e in edges:
                f.write(json.dumps(list(e), separators=(",", ":")) + "\n")
        self.parts.append(fp)
        self._cache = None      # 数据变了，回补判据缓存失效

    def finalize(self):
        src = self._src()
        if not src:
            return {"rows": 0, "has_mint": False, "min_ts": None}
        has_mint, min_ts = self.stats()
        tmp = self.cache_fp.parent / (self.cache_fp.name + ".tmp")
        con = self._con()
        try:
            self._validate(con)
            n = con.execute(f"""
                COPY (
                  WITH {self._ctes()}
                  SELECT '[' || ts || ', ' || slot || ', ' || tx_index || ', '
                              || instr_index || ', ' || to_json(f) || ', '
                              || to_json(t) || ', ' || amt || ']' AS line
                  FROM canonical
                  ORDER BY slot, tx_index, f, t, amt
                ) TO '{tmp}' (FORMAT csv, HEADER false, QUOTE '', DELIMITER e'\\x07',
                              COMPRESSION gzip)
            """).fetchone()[0]
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        finally:
            con.close()
            for leftover in self.tmpdir.glob("*"):
                leftover.unlink(missing_ok=True)
        if not n:
            tmp.unlink(missing_ok=True)                             # 零边不动缓存（同旧版语义）
            return {"rows": 0, "has_mint": False, "min_ts": None}
        os.replace(tmp, self.cache_fp)
        return {"rows": int(n), "has_mint": has_mint, "min_ts": min_ts}


class EdgeCount:
    """run() 的返回占位：只承载最终边数。

    外排路径下全量边不在内存里（这正是修复要点），故两条路径统一只回计数——
    调用方（main / collect_queue）本来也只用 len() 与 is None 判断。"""
    __slots__ = ("n",)

    def __init__(self, n):
        self.n = n

    def __len__(self):
        return self.n


def make_merger(cache_fp, parts_dir, part_files, old_ok, old_rows, max_rows):
    """按预估规模选收尾路径：超阈值走 DuckDB 外排，否则全内存（历史行为）。"""
    est = old_rows + _part_rows_estimate(part_files)
    if est <= max_rows:
        return MemMerger(cache_fp, parts_dir, part_files, old_ok), est
    if duckdb is None:
        log(f"⚠ 预估 {est:,} 行超全内存阈值 {max_rows:,}，但本机没有 duckdb——"
            f"只能退回全内存收尾，有 OOM 风险（pip3 install duckdb 后重跑即走外排）")
        return MemMerger(cache_fp, parts_dir, part_files, old_ok), est
    free_gb = shutil.disk_usage(parts_dir.parent).free / 1e9
    need_gb = est * 165 * 2 / 1e9      # 外排 temp + 输出的粗估
    log(f"收尾降级 DuckDB 磁盘外排：预估 {est:,} 行 > 阈值 {max_rows:,}"
        f"（memory_limit={MERGE_MEM_LIMIT} threads={MERGE_THREADS}，"
        f"可用磁盘 {free_gb:.0f}GB / 粗估需 {need_gb:.0f}GB）")
    if free_gb < need_gb:
        log("⚠ 可用磁盘低于粗估需求——外排若失败，parts 与 meta 均保留，清盘后重跑即可续")
    return ExtMerger(cache_fp, parts_dir, part_files, old_ok), est


def run(mint, launch_ts, wall_min, conc, rps, base_url, key,
        hs_cfg=None, from_slot_cli=None, to_slot_cli=None,
        empty_max=EMPTY_MAX, merge_max_rows=MERGE_INMEM_MAX_ROWS,
        dataset_id=SOLANA_SQD_DATASET_ID, state_session=None):
    frozen_collector_sha256 = collector_sha256()
    if hs_cfg is not None:
        log("[fail-closed] --hypersync 通道已禁用；v4 正式采集只允许 SQD")
        raise SystemExit(2)
    cache_fp, meta_fp, parts_dir = cache_paths(mint)
    meta = preflight_v4_cache(
        cache_fp, meta_fp, parts_dir, mint, base_url, frozen_collector_sha256)
    fx = Fetcher(base_url, mint, key, TokenBucket(rps), conc, empty_max=empty_max)
    head = fx.head()
    if not head:
        return None, "SQD portal head 不可达"
    if to_slot_cli:
        head = min(head, int(to_slot_cli))   # 调试/定段采集：上界压到指定 slot
    if state_session is None:
        raise ValueError("formal SQD collection requires an attested Solana state session")
    finalized_slot = state_session.call("getSlot", [{"commitment": "finalized"}])
    if (isinstance(finalized_slot, bool) or not isinstance(finalized_slot, int)
            or finalized_slot < 0):
        raise ValueError(f"invalid finalized Solana slot: {finalized_slot!r}")
    head = min(head, finalized_slot)
    parts_dir.mkdir(parents=True, exist_ok=True)
    identity = cache_identity(mint, base_url, frozen_collector_sha256)
    if meta:
        normalized = normalize_cache_identity(
            meta, mint, base_url, frozen_collector_sha256)
        if normalized is None:
            log("[fail-closed] SQD v4 cache 身份在启动后发生变化")
            raise SystemExit(2)
        meta = normalized

    def fresh_meta(start):
        return {**identity, "version": CACHE_VERSION, "from_slot": start,
                "launch_covered": False, "areas": [],
                "finalized_upper_slot": head}
    # 旧缓存只做流式体检拿行数（不载入内存——收尾阶段才按规模选路径读它）
    old_rows, old_ok = 0, False
    if cache_fp.exists() and meta:
        old_rows, old_ok = probe_cache(cache_fp)
        if old_ok:
            log(f"缓存命中：{old_rows:,} 条边，已完成区域 {len(meta.get('areas', []))} 个")
        else:
            log("缓存损坏——重新全量")
            meta = {}

    now = int(time.time())
    if meta.get("from_slot"):
        span_from = from_slot = int(meta["from_slot"])
        if from_slot_cli and int(from_slot_cli) != from_slot:
            log(f"已有 meta（from_slot={from_slot}）——忽略 --from-slot（增量语义优先）")
    elif from_slot_cli:
        span_from = from_slot = max(1, int(from_slot_cli))
        meta = fresh_meta(from_slot)
    else:
        back = int((now - (launch_ts or now - 90 * 86400)) * SQD_SLOT_RATE) + SQD_LAUNCH_PAD
        span_from = from_slot = max(1, head - back)
        meta = fresh_meta(from_slot)

    dataset_scope = SolanaSqdDatasetAdapter(
        dataset_id=dataset_id, mint=mint, from_slot=span_from, to_slot=head,
        state_session=state_session).attest_state_anchor()
    meta["dataset_scope"] = dataset_scope

    # ---- HyperSync 第二引擎初始化：探窗失败即降级纯 SQD（采集完备性优先）----
    fx_hs, hs_lo, hs_hi = None, None, None
    if hs_cfg:
        log("⚠ HyperSync 完备性验收不通过（历史区缺行 3.6-22%、近端有暂态洞，2026-07-22 "
            "实测）——本开关仅限吞吐实验/对照，正式采集产物必须用纯 SQD 重采或逐段复核")
        cand = HyperSyncFetcher(hs_cfg["url"], mint, hs_cfg["token"],
                                TokenBucket(hs_cfg["rps"]), hs_cfg["proxy"])
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
            tmp = meta_fp.with_name(f".{meta_fp.name}.tmp.{os.getpid()}")
            try:
                with tmp.open("w", encoding="utf-8") as handle:
                    json.dump(meta, handle, separators=(",", ":"), sort_keys=True)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, meta_fp)
            except BaseException:
                tmp.unlink(missing_ok=True)
                raise

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

    # 合并：旧缓存边 + 全部分区文件 → 排序去重整写。
    # 规模超阈值自动降级 DuckDB 磁盘外排——旧版无条件全内存 sorted(set(...))，
    # BONK 单分片 3900-5900 万行峰值 13-19GB，16GB 机器必 OOM。
    part_files = sorted(parts_dir.glob("*.jsonl"))
    merger, est_rows = make_merger(cache_fp, parts_dir, part_files, old_ok,
                                   old_rows, merge_max_rows)
    if merger.rows() == 0 and not part_files and not old_ok:
        return None, "SQD 拉取无数据（含缓存为空）"

    # 回补验证：起点没盖住发射 → 前移重扫（沿用 v1 语义，最多 2 次）
    if not meta.get("launch_covered"):
        for _ in range(2):
            has_mint, min_ts = merger.stats()
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
            merger.absorb(b_edges)
            with meta_lock:
                meta["areas"].append({"s": new_from, "e": from_slot - 1, "done": True})
                meta["from_slot"] = from_slot = new_from
            persist_meta()

    # 落盘：整写 jsonl.gz（临时文件+原子 rename），meta 记 launch_covered 与 gaps
    final = {"rows": 0, "has_mint": False, "min_ts": None}
    try:
        if collector_sha256() != frozen_collector_sha256:
            raise RuntimeError(
                "collector_sha256 changed after startup; refusing cache finalize")
        final = merger.finalize()
        if not final["rows"]:
            return None, "SQD 拉取无数据（含缓存为空）"
        edge_logical_sha256, edge_rows = logical_edge_evidence(cache_fp)
        if edge_rows != final["rows"]:
            raise RuntimeError(
                f"finalized edge row count mismatch: merger={final['rows']} scan={edge_rows}")
        has_mint = final["has_mint"]
        covered = sorted(((a["s"], a["e"]) for a in meta["areas"] if a.get("done")),
                         key=lambda x: x[0])
        # 连续覆盖前沿（供增量续拉）
        front = from_slot - 1
        for s, e in covered:
            if s <= front + 1:
                front = max(front, e)
        # empty_ok = 判定为"区间内无块"的空区间审计清单（伪 scan-fail 修复的留痕，
        # 便于事后复验：任取一段做 ±60 包围请求，应能拿到前后块且不含该段本身）
        meta.update({"launch_covered": bool(meta.get("launch_covered")) or has_mint,
                     "next_slot": front + 1, "gaps": gaps,
                     "finalized_upper_slot": head,
                     "empty_ok": {"n": len(fx.empty_hits), "max": empty_max,
                                  "intervals": fx.empty_hits[:2000]},
                     "edge_logical_sha256": edge_logical_sha256,
                     "edge_rows": edge_rows,
                     "merge_mode": merger.mode,
                     "updated": time.strftime("%Y-%m-%d %H:%M")})
        persist_meta()
        for pf in parts_dir.glob("*.jsonl"):
            pf.unlink()
        shutil.rmtree(parts_dir.parent / "_merge_tmp", ignore_errors=True)
    except Exception as e:
        # 收尾失败＝数据没落盘，必须让退出码非 0（否则"完成 0 条边"会被当成正常空结果）；
        # parts 与 meta 都保留，重跑即从 parts 续合并
        log(f"缓存写入失败：{e}——parts 与 meta 已保留，重跑可续")
        gaps.append([from_slot, head, "merge-fail"])

    gap_msg = None
    if gaps:
        seg_s = "; ".join(f"[{g[0]},{g[1]}]({g[2]})" for g in gaps[:6])
        more = f" 等共{len(gaps)}段" if len(gaps) > 6 else ""
        gap_msg = f"存在未覆盖区间：{seg_s}{more}——重跑自动补扫，gaps 清零前不得进重放"
    min_ts = final["min_ts"] or 0
    if launch_ts and min_ts and min_ts > launch_ts + 6 * 3600 and not final["has_mint"]:
        g2 = f"重放起点晚于发射约 {(min_ts - launch_ts) / 3600:.0f} 小时——最早期建仓缺失"
        gap_msg = f"{gap_msg}；{g2}" if gap_msg else g2
    el = time.time() - t0
    hs_note = ""
    if stats["slots_hs"]:
        hs_note = (f"；其中 HyperSync 采 {stats['slots_hs']:,} slots"
                   f"——⚠该部分存在完备性风险（服务端洞静默），正式使用前需 SQD 复核")
    empty_note = (f"；空区间判完成 {len(fx.empty_hits)} 段（无块，非缺口，见 meta.empty_ok）"
                  if fx.empty_hits else "")
    log(f"完成：{final['rows']:,} 条边（收尾 {merger.mode}），{stats['slots']:,} slots / {el:.0f}s "
        f"= {stats['slots'] / el if el else 0:,.0f} slots/s"
        + (f"；缺口：{gap_msg}" if gap_msg else "（无缺口）") + hs_note + empty_note)
    return EdgeCount(final["rows"]), gap_msg


def _default_state_rpc():
    key_file = Path.home() / ".config/helius/api-key"
    if key_file.is_file():
        key = key_file.read_text(encoding="utf-8").strip()
        if key:
            return f"https://mainnet.helius-rpc.com/?api-key={key}"
    return "https://api.mainnet-beta.solana.com"


def main(argv=None, *, request_json=None):
    ap = argparse.ArgumentParser(description="SQD portal Solana v4 交易级净额边采集器")
    ap.add_argument("mint")
    ap.add_argument("--dataset-id", default=SOLANA_SQD_DATASET_ID)
    ap.add_argument("--state-rpc", action="append", dest="state_rpcs",
                    help="attested Solana mainnet state endpoint; repeat for failover")
    ap.add_argument("--launch-ts", type=int, default=0, help="发射 unix 秒，缺省回看 90 天")
    ap.add_argument("--wall-min", type=int, default=100, help="墙钟保险丝（分钟）")
    ap.add_argument("--conc", type=int, default=6, help="并发空洞数（带宽整形下 3 路已近饱和，留冗余）")
    ap.add_argument("--rps", type=float, default=4.0, help="全局请求速率上限/秒（防雪崩护栏；文档标称 2/s 实测对长流不生效、真瓶颈是带宽）")
    ap.add_argument("--url", default=DEF_URL, help="数据集端点（拿到 key 专属端点后换这里）")
    ap.add_argument("--key-file", default=os.path.expanduser("~/.config/sqd/api-key"))
    ap.add_argument("--hypersync", action="store_true",
                    help="已禁用；v4 正式采集仅允许 SQD，传入即 exit 2")
    ap.add_argument("--hs-url", default=HS_DEF_URL, help="HyperSync Solana 查询端点")
    ap.add_argument("--hs-token-file", default=HS_DEF_TOKEN,
                    help="HyperSync 付费 token 文件（按请求计费，量级忽略不计）")
    ap.add_argument("--hs-conc", type=int, default=2,
                    help="HS 并发段数（POC 实测双通道叠加即近 2 倍，保守默认 2）")
    ap.add_argument("--hs-rps", type=float, default=4.0, help="HS 请求速率护栏/秒")
    ap.add_argument("--proxy", default=HS_FALLBACK_PROXY,
                    help="HyperSync 直连异常后的候选代理；空字符串或 none 禁用切换"
                         "（默认经 CHIP_PROXY/端口探测解析）")
    ap.add_argument("--from-slot", type=int, default=0,
                    help="调试/定段采集：直接指定起点 slot（仅首采无 meta 时生效）")
    ap.add_argument("--to-slot", type=int, default=0,
                    help="调试/定段采集：采集上界 slot（默认链头）")
    ap.add_argument("--empty-max", type=int, default=EMPTY_MAX,
                    help=f"零行响应判「区间内无块」的免探针跨度闸门（默认 {EMPTY_MAX} slot；"
                         "超过闸门的零行区间改用轻量块探针实证，探不出块才判完成）")
    ap.add_argument("--merge-max-rows", type=int, default=MERGE_INMEM_MAX_ROWS,
                    help=f"收尾全内存合并的行数上限（默认 {MERGE_INMEM_MAX_ROWS:,}，"
                         "超过自动降级 DuckDB 磁盘外排防 OOM）")
    a = ap.parse_args(argv)
    if a.from_slot and a.to_slot and a.from_slot > a.to_slot:
        ap.error("--from-slot must not exceed --to-slot")
    if a.hypersync:
        log("[fail-closed] --hypersync 通道已禁用；v4 正式采集只允许 SQD")
        raise SystemExit(2)
    state_session = SolanaAttestedSession(
        a.state_rpcs or [_default_state_rpc()], request_json=request_json, timeout=30)
    # Reject dataset/mint identity before the first SQD business request.  The
    # actual inclusive range is re-bound inside run() after SQD head discovery.
    SolanaSqdDatasetAdapter(
        dataset_id=a.dataset_id, mint=a.mint, from_slot=0, to_slot=0,
        state_session=state_session)
    key = None
    try:
        key = Path(a.key_file).read_text().strip() or None
    except Exception:
        pass
    edges, gap = run(a.mint, a.launch_ts or None, a.wall_min, a.conc, a.rps, a.url, key,
                     hs_cfg=None, from_slot_cli=a.from_slot or None,
                     to_slot_cli=a.to_slot or None, empty_max=a.empty_max,
                     merge_max_rows=a.merge_max_rows, dataset_id=a.dataset_id,
                     state_session=state_session)
    if edges is None:
        print(f"失败：{gap}", flush=True)
        sys.exit(1)
    print(f"完成：{len(edges)} 条转账边 → {cache_paths(a.mint)[0]}"
          + (f"\n缺口声明：{gap}" if gap else "（全量到链头，无缺口）"), flush=True)
    sys.exit(2 if gap else 0)


if __name__ == "__main__":
    main()
