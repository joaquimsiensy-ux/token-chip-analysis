#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hyperliquid 原生代币筹码分析统一采集器。
来源：HYPE(Hyperliquid) 分析会话实战产物, 2026-07（标的常量已外置到 config，HYPE 原值见 config.example.json）。
只用标准库；两套免费 API（Hyperliquid 官方 info + Hypurrscan），带限速与重试。
用法: python3 collect.py [--config <path>] <子命令>
  配置读取顺序：--config 指定路径 > 脚本同目录 config.json；缺失则报错退出。
子命令:
  static     下载静态底座数据（holders/tokenDetails/aliases/validators/unstaking/candles/twap/spotMeta）
  entities   核心实体全量时间线（ledger 分页 / 质押史 / portfolio / 现货余额 / 近期 fills）
  snapshots  历史持仓快照（周度全史 + 近90天日度, top-1000）
  worklist   由静态数据生成 T4 地址工作清单
  addresses  T4 长跑：按工作清单逐地址拉 ledger + delegatorSummary
  vesting    T3：团队分发接收地址的二级追踪
"""
import json, os, ssl, sys, time, urllib.request, urllib.error

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")

def _load_config():
    """--config <path> 优先，否则脚本同目录 config.json；缺失即退出（不设默认标的）。"""
    if "--config" in sys.argv:
        i = sys.argv.index("--config")
        if i + 1 >= len(sys.argv):
            sys.exit("--config 后须跟配置文件路径")
        path = sys.argv[i + 1]
        del sys.argv[i:i + 2]   # 摘除，避免干扰子命令解析
    else:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if not os.path.exists(path):
        sys.exit(f"缺配置 {path}：复制 config.example.json 为 config.json 按标的填写，或用 --config 指定")
    with open(path) as f:
        return json.load(f)

CFG = _load_config()
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = CFG.get("data_dir") or os.path.join(BASE, "data")
INFO_URL = "https://api.hyperliquid.xyz/info"
HPS_URL = "https://api.hypurrscan.io"
SYMBOL = CFG["token_symbol"]                 # Hypurrscan 路径用
TOKEN_ID = CFG["token_id"]                   # 官方 tokenDetails 用
CANDLE_COIN = CFG["candle_coin"]             # candleSnapshot 的 coin（现货对 @<index>）
TGE_MS = int(CFG["tge_ms"])                  # ledger/fills 分页起点
SNAPSHOT_START_S = int(CFG["snapshot_start_s"])  # Hypurrscan 最早可用快照（秒）

ENTITIES = {k: v.lower() for k, v in CFG["entities"].items()}
TEAM_ENTITY = CFG.get("team_entity") or ""           # worklist/vesting 用的团队实体键名
FILLS_ENTITY = CFG.get("fills_recent_entity") or ""  # 补拉近30天 fills 的实体键名，空则跳过
# EVM 桥流水量过大（所有跨链转账中转），不拉 ledger，只在排除集中使用
EVM_BRIDGE = CFG["evm_bridge"].lower()

_last_call = {"info": 0.0, "hps": 0.0}

def _throttle(kind, min_gap):
    now = time.time()
    wait = _last_call[kind] + min_gap - now
    if wait > 0:
        time.sleep(wait)
    _last_call[kind] = time.time()

def _request(req, kind, min_gap, tries=6):
    for i in range(tries):
        _throttle(kind, min_gap)
        try:
            with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                sleep_s = min(60, 2 ** (i + 1))
                print(f"  HTTP {e.code}, 退避 {sleep_s}s", flush=True)
                time.sleep(sleep_s)
                continue
            raise
        except Exception as e:
            sleep_s = min(60, 2 ** (i + 1))
            print(f"  网络错误 {type(e).__name__}: {e}, 退避 {sleep_s}s", flush=True)
            time.sleep(sleep_s)
    raise RuntimeError("重试耗尽")

def info(body, address_level=True):
    """官方 API。地址级查询 weight 20 → 保守 1.05s 间隔；轻查询 0.3s。"""
    req = urllib.request.Request(INFO_URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return _request(req, "info", 3.0 if address_level else 0.3)

def hps(path, min_gap=0.35):
    req = urllib.request.Request(HPS_URL + path, headers={"User-Agent": "research/1.0"})
    return _request(req, "hps", min_gap)

def save(relpath, obj):
    p = os.path.join(DATA, relpath)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    size = os.path.getsize(p)
    print(f"  已存 {relpath} ({size/1024:.0f} KB)", flush=True)

def exists(relpath):
    return os.path.exists(os.path.join(DATA, relpath))

def now_ms():
    return int(time.time() * 1000)

# ---------- ledger / fills / staking 分页 ----------

def fetch_ledger_full(addr, start=TGE_MS, end=None):
    """userNonFundingLedgerUpdates 全史，2000条/页分页。"""
    end = end or now_ms()
    out, cursor = [], start
    while True:
        page = info({"type": "userNonFundingLedgerUpdates", "user": addr,
                     "startTime": cursor, "endTime": end})
        if not isinstance(page, list):
            break
        out.extend(page)
        if len(page) < 2000:
            break
        cursor = page[-1]["time"] + 1
    return out

def fetch_fills(addr, start=TGE_MS, end=None, max_pages=6):
    end = end or now_ms()
    out, cursor = [], start
    for _ in range(max_pages):
        page = info({"type": "userFillsByTime", "user": addr,
                     "startTime": cursor, "endTime": end, "aggregateByTime": False})
        if not isinstance(page, list) or not page:
            break
        out.extend(page)
        if len(page) < 2000:
            break
        cursor = page[-1]["time"] + 1
    return out

# ---------- 子命令 ----------

def cmd_static():
    print("== static ==", flush=True)
    if not exists("static/token_details.json"):
        save("static/token_details.json",
             info({"type": "tokenDetails", "tokenId": TOKEN_ID}, address_level=False))
    if not exists("static/holders.json"):
        save("static/holders.json", hps(f"/holders/{SYMBOL}", min_gap=1.0))
    if not exists("static/global_aliases.json"):
        save("static/global_aliases.json", hps("/globalAliases"))
    if not exists("static/validator_summaries.json"):
        save("static/validator_summaries.json",
             info({"type": "validatorSummaries"}, address_level=False))
    if not exists("static/unstaking_queue.json"):
        save("static/unstaking_queue.json", hps("/fullUnstakingQueue", min_gap=2.0))
    if not exists("static/twap.json"):
        save("static/twap.json", hps(f"/twap/{SYMBOL}", min_gap=1.0))
    if not exists("static/spot_meta.json"):
        save("static/spot_meta.json", info({"type": "spotMeta"}, address_level=False))
    if not exists("static/candles_1d.json"):
        save("static/candles_1d.json",
             info({"type": "candleSnapshot",
                   "req": {"coin": CANDLE_COIN, "interval": "1d",
                           "startTime": TGE_MS, "endTime": now_ms()}}, address_level=False))
    print("static 完成", flush=True)

def cmd_entities():
    print("== entities ==", flush=True)
    for name, addr in ENTITIES.items():
        d = f"entities/{name}"
        if not exists(f"{d}/ledger.json"):
            ledger = fetch_ledger_full(addr)
            save(f"{d}/ledger.json", ledger)
            print(f"  {name} ledger {len(ledger)} 条", flush=True)
        if not exists(f"{d}/delegator_summary.json"):
            save(f"{d}/delegator_summary.json",
                 info({"type": "delegatorSummary", "user": addr}))
        if not exists(f"{d}/delegator_history.json"):
            save(f"{d}/delegator_history.json",
                 info({"type": "delegatorHistory", "user": addr}))
        if not exists(f"{d}/spot_state.json"):
            save(f"{d}/spot_state.json",
                 info({"type": "spotClearinghouseState", "user": addr}))
        if not exists(f"{d}/portfolio.json"):
            save(f"{d}/portfolio.json", info({"type": "portfolio", "user": addr}))
    # 关键实体近期成交（HYPE 场景=援助基金，判断回购是否仍在进行）
    if FILLS_ENTITY and not exists(f"entities/{FILLS_ENTITY}/fills_recent.json"):
        fills = fetch_fills(ENTITIES[FILLS_ENTITY],
                            start=now_ms() - 30 * 86400_000)
        save(f"entities/{FILLS_ENTITY}/fills_recent.json", fills)
        print(f"  {FILLS_ENTITY} 近30天 fills {len(fills)} 条", flush=True)
    print("entities 完成", flush=True)

def cmd_snapshots():
    print("== snapshots ==", flush=True)
    start_s = SNAPSHOT_START_S    # hypurrscan 最早快照（config.snapshot_start_s）
    now_s = int(time.time())
    week = 7 * 86400
    targets = list(range(start_s, now_s - 90 * 86400, week))          # 周度全史
    targets += list(range(now_s - 90 * 86400, now_s, 86400))          # 近90天日度
    print(f"共 {len(targets)} 档快照", flush=True)
    for i, ts in enumerate(targets):
        rel = f"snapshots/top1000_{ts}.json"
        if exists(rel):
            continue
        snap = hps(f"/holdersAtTimeWithLimit/{SYMBOL}/{ts}/1000", min_gap=1.2)
        save(rel, snap)
        if i % 20 == 0:
            print(f"  进度 {i+1}/{len(targets)}", flush=True)
    print("snapshots 完成", flush=True)

def cmd_worklist():
    """生成 T4 地址清单：现货 top-500 ∪ genesis top-500 ∪ 团队 spotTransfer 接收地址 ∪ 实体对手方"""
    print("== worklist ==", flush=True)
    holders = json.load(open(os.path.join(DATA, "static/holders.json")))["holders"]
    top_spot = sorted(holders.items(), key=lambda kv: -kv[1])[:500]
    td = json.load(open(os.path.join(DATA, "static/token_details.json")))
    gen = [(a, float(b)) for a, b in td["genesis"]["userBalances"]]
    top_gen = sorted(gen, key=lambda kv: -kv[1])[:500]
    team_ledger = json.load(open(os.path.join(DATA, f"entities/{TEAM_ENTITY}/ledger.json")))
    team_recv, counterparties = set(), set()
    for ev in team_ledger:
        d = ev.get("delta", {})
        if d.get("type") in ("spotTransfer", "send") and d.get("destination"):
            team_recv.add(d["destination"].lower())
    for name in ENTITIES:
        led = json.load(open(os.path.join(DATA, f"entities/{name}/ledger.json")))
        for ev in led:
            d = ev.get("delta", {})
            for k in ("destination", "user"):
                v = d.get(k)
                if isinstance(v, str) and v.startswith("0x") and len(v) == 42:
                    counterparties.add(v.lower())
    allset = set(a.lower() for a, _ in top_spot) | set(a.lower() for a, _ in top_gen) \
             | team_recv | counterparties
    system = set(ENTITIES.values()) | {EVM_BRIDGE,
                                       "0x0000000000000000000000000000000000000000",
                                       "0x000000000000000000000000000000000000dead",
                                       "0xffffffffffffffffffffffffffffffffffffffff"}
    allset -= system
    wl = sorted(allset)
    save("worklist.json", {"count": len(wl),
                           "team_recv": sorted(team_recv),
                           "addresses": wl})
    print(f"工作清单 {len(wl)} 地址（其中团队接收地址 {len(team_recv)} 个）", flush=True)

def cmd_addresses():
    print("== addresses (T4 长跑) ==", flush=True)
    wl = json.load(open(os.path.join(DATA, "worklist.json")))["addresses"]
    done = fail = 0
    for i, addr in enumerate(wl):
        rel = f"addresses/{addr}.json"
        if exists(rel):
            done += 1
            continue
        try:
            ledger = fetch_ledger_full(addr)
            deleg = info({"type": "delegatorSummary", "user": addr})
            save_quiet(rel, {"addr": addr, "ledger": ledger, "delegation": deleg})
            done += 1
        except Exception as e:
            fail += 1
            print(f"  {addr} 失败: {e}", flush=True)
        if (i + 1) % 50 == 0:
            print(f"T4进度 {i+1}/{len(wl)} 完成={done} 失败={fail}", flush=True)
    print(f"T4完成 total={len(wl)} 完成={done} 失败={fail}", flush=True)

def save_quiet(relpath, obj):
    p = os.path.join(DATA, relpath)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f, ensure_ascii=False)

def cmd_vesting():
    """T3：团队接收地址的去向二级追踪（这些地址多数已含在 T4 清单里，此处补拉近期 fills 判断是否市场卖出）"""
    print("== vesting trace ==", flush=True)
    wl = json.load(open(os.path.join(DATA, "worklist.json")))
    for addr in wl["team_recv"]:
        rel = f"vesting/{addr}_fills.json"
        if exists(rel):
            continue
        fills = fetch_fills(addr)
        save_quiet(rel, fills)
    print("vesting trace 完成", flush=True)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"static": cmd_static, "entities": cmd_entities, "snapshots": cmd_snapshots,
     "worklist": cmd_worklist, "addresses": cmd_addresses, "vesting": cmd_vesting,
     }.get(cmd, lambda: print(__doc__))()
