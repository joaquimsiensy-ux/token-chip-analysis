#!/usr/bin/env python3
"""批量预采集队列——多币串行采集全量转账事件，只采集不分析。

场景：/collect-data 命令的执行器。候选滚动排查时把"采集 67 分钟/币"的等待挪到
夜间：睡前排队 N 个候选，白天 easy/完整分析会话在同一工作目录直接复用产物
（fetch_hypersync_v2 / fetch_sqd_transfers_v2 都自带断点续拉，开工时自动补增量）。

用法:
  python3 collect_queue.py <plan.json> [--resume] [--dry-run] [--token-file PATH]

plan.json 格式:
{
  "base_dir": "/Users/uravvv/Desktop/老公用/fable筹码分析",
  "items": [
    {"name": "QUQ", "chain": "bsc", "address": "0x4fa7..."},
    {"name": "XX", "chain": "solana", "address": "<mint>", "launch_ts": 1710000000}
  ]
}
  - chain ∈ {bsc, eth, base, arbitrum, robinhood} → HyperSync 官方客户端 v2
    产物 <base_dir>/<name>分析/data/v2/run_*/（logs+blocks parquet）
    from_block 自动探测部署块（全局缓存 ~/.cache/chip-analysis/deploy_blocks.json）
  - chain = solana → SQD Portal v2
    产物 <base_dir>/<name>分析/data/soltx-<mint小写>.jsonl.gz
    launch_ts 强烈建议给——缺省只回看 90 天，老币会缺早期数据（manifest 会标注）
  - 可选字段: to_block(EVM,默认链头) / wall_min(Solana 保险丝,默认 300 分钟) /
    concurrency(EVM,默认 10)

行为契约:
  - 泳道调度（3.18.0）：EVM 泳道与 Solana 泳道**并行**，各泳道内部串行——
    HyperSync 限流是 key 级共享（EVM 币间互抢），SQD 是单 IP 带宽整形（Solana 币间
    互抢），但两者资源池互不相干，跨泳道并行纯赚墙钟；--serial 回退全串行
  - 单项失败不阻塞后续；结束码 0=全部完成 2=有缺口(Solana gaps) 1=有失败/有 skipped_locked
    3=队列单实例锁被占（本次什么都没跑，plan 保留）
  - manifest（collect_manifest.json，plan 同目录）逐项原子更新；--resume 跳过 done 项
    （不带 --resume 重跑也安全：底层采集器自动续拉，幂等）
  - EVM 残缺 run（无 done.json）开跑前自动改名 partial_run_*_<ts> 隔离——只改名不删除，
    防 partial parquet 污染下游 run_*/ glob
  - 只做采集侧完整性校验（done.json/行数/块范围）；对账三查是分析会话 E2 的事
跨进程锁（C2，3.19——launchd 夜采与白天手动会话并发防护，语义见 proclock.py）:
  - 队列单实例锁 <base_dir>/collect_plans/queue.lock：抢不到立即退出码 3 并报持有者；
    持有进程死亡（含 SIGKILL）flock 自动释放，残留元数据下次接管并记日志
  - 每币写锁 <币目录>/data/.collect.lock：抢不到**跳过该币**记 manifest
    skipped_locked（不崩队列，退出码归入 1，--resume 重跑会重试）
  - 锁文件带 pid/run_id/心跳（60s 刷新）；心跳超时判挂死只报不强抢
  - --run-id 标识本次运行（默认取环境变量 CHIP_RUN_ID，再默认 时间戳p<pid>）
密钥治理（C3）: HyperSync token 不再进子进程 argv——只把 --token-file 路径传给
  fetch_hypersync_v2，token 由子进程自己读文件（ps 视角无明文）
夜间脱管跑法（推荐）:
  python3 <skill>/scripts/run_guarded.py --detach --mem-ceiling-gb 6 --name collect \
      -- python3 <skill>/scripts/collect/collect_queue.py plan.json
（来源：B12 批量预采集，2026-07-22；C2/C3 加固同日）"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import threading
import time

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "evm"))
sys.path.insert(0, SCRIPT_DIR)
from transfers_lib import get_deploy_block  # noqa: E402

from proclock import ProcLock  # noqa: E402

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
EVM_CHAINS = {"bsc", "eth", "base", "arbitrum", "robinhood"}
FETCH_V2 = os.path.join(SCRIPT_DIR, "..", "evm", "fetch_hypersync_v2.py")
FETCH_SOL = os.path.join(SCRIPT_DIR, "..", "solana", "fetch_sqd_transfers_v2.py")


def log(msg):
    print(f"[queue] {msg}", flush=True)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------- plan / manifest ----------------

def load_plan(path):
    plan = json.load(open(path))
    base = plan.get("base_dir")
    items = plan.get("items")
    if not base or not os.path.isdir(base):
        sys.exit(f"[fatal] plan 的 base_dir 缺失或不是目录: {base}")
    if not items:
        sys.exit("[fatal] plan 的 items 为空")
    seen = set()
    for it in items:
        name, chain, addr = it.get("name"), it.get("chain"), it.get("address")
        if not name or not chain or not addr:
            sys.exit(f"[fatal] 项缺 name/chain/address: {it}")
        if chain not in EVM_CHAINS and chain != "solana":
            sys.exit(f"[fatal] 不认识的链 {chain}（支持 {sorted(EVM_CHAINS)} + solana）: {name}")
        if chain in EVM_CHAINS and not re.fullmatch(r"0x[0-9a-fA-F]{40}", addr):
            sys.exit(f"[fatal] {name}: EVM 地址格式不对: {addr}")
        if re.search(r"[/\s]", name):
            sys.exit(f"[fatal] 币名含斜杠或空白（会破坏目录名）: {name!r}")
        k = (name, chain, addr.lower())
        if k in seen:
            sys.exit(f"[fatal] plan 重复项: {k}")
        seen.add(k)
    return plan


def manifest_path(plan_path):
    return os.path.join(os.path.dirname(os.path.abspath(plan_path)), "collect_manifest.json")


def load_manifest(mpath):
    if os.path.exists(mpath):
        return json.load(open(mpath))
    return {"updated": None, "items": {}}


def save_manifest(mpath, m):
    m["updated"] = now_iso()
    tmp = mpath + ".tmp"
    with open(tmp, "w") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    os.replace(tmp, mpath)


def item_key(it):
    return f"{it['name']}|{it['chain']}|{it['address'].lower()}"


# ---------------- EVM ----------------

def probe_deploy_block(chain, addr, token):
    """HyperSync JSON 轻查询：从 0 起找第一条 Transfer 的块号。空段推进极快。"""
    url = f"https://{chain}.hypersync.xyz/query"
    headers = {"Authorization": f"Bearer {token}"}
    cur = 0
    for _ in range(200):
        q = {"from_block": cur,
             "logs": [{"address": [addr.lower()], "topics": [[TRANSFER]]}],
             "field_selection": {"log": ["block_number"]}}
        r = requests.post(url, json=q, headers=headers, timeout=60)
        if r.status_code == 429:
            time.sleep(3)
            continue
        r.raise_for_status()
        j = r.json()
        for batch in j.get("data", []):
            logs = batch.get("logs", [])
            if logs:
                return int(logs[0]["block_number"])
        nxt, ah = j.get("next_block"), j.get("archive_height")
        if not nxt or (ah and nxt >= ah):
            return None  # 扫到链头都没有该合约的 Transfer
        cur = nxt
        time.sleep(0.3)
    return None


def quarantine_partial_runs(v2dir):
    """无 done.json 的 run_* 改名 partial_run_*_<ts> 隔离（不删除）。"""
    n = 0
    for d in sorted(glob.glob(os.path.join(v2dir, "run_*"))):
        if os.path.isdir(d) and not os.path.exists(os.path.join(d, "done.json")):
            dst = os.path.join(v2dir, "partial_" + os.path.basename(d) + f"_{int(time.time())}")
            os.rename(d, dst)
            log(f"隔离残缺 run: {os.path.basename(d)} -> {os.path.basename(dst)}")
            n += 1
    return n


def evm_stats(v2dir):
    """duckdb 数行+块范围（只扫 run_*/logs.parquet，partial_ 不入）。"""
    import duckdb
    pat = os.path.join(v2dir, "run_*", "logs.parquet")
    if not glob.glob(pat):
        return None
    con = duckdb.connect()
    r = con.execute(
        "SELECT COUNT(*), MIN(block_number), MAX(block_number) FROM read_parquet(?)",
        [pat]).fetchone()
    con.close()
    return {"rows": int(r[0]), "min_block": int(r[1]) if r[1] is not None else None,
            "max_block": int(r[2]) if r[2] is not None else None}


def collect_evm(it, workdir, token, token_file, logf):
    chain, addr = it["chain"], it["address"].lower()
    v2dir = os.path.join(workdir, "data", "v2")
    os.makedirs(v2dir, exist_ok=True)
    quarantine_partial_runs(v2dir)
    url = f"https://{chain}.hypersync.xyz"

    fb = get_deploy_block(chain, addr, lambda: probe_deploy_block(chain, addr, token))
    if fb is None:
        return {"status": "failed",
                "error": f"{chain} 链上未发现该合约的任何 Transfer——检查链路由/地址是否匹配"}
    # C3：token 不进 argv（ps 可见）——传 --token-file 路径，子进程自己读
    cmd = [sys.executable, FETCH_V2, str(fb), "--url", url,
           "--token-file", token_file,
           "--token-addr", addr, "--outdir", v2dir,
           "--concurrency", str(it.get("concurrency", 10))]
    if it.get("to_block"):
        cmd += ["--to-block", str(it["to_block"])]
    t0 = time.time()
    rc = subprocess.call(cmd, stdout=logf, stderr=subprocess.STDOUT)
    el = round(time.time() - t0, 1)
    if rc != 0:
        return {"status": "failed", "elapsed_s": el,
                "error": f"fetch_hypersync_v2 退出码 {rc}（详见 data/collect.log）"}
    st = evm_stats(v2dir)
    if not st or st["rows"] == 0:
        return {"status": "failed", "elapsed_s": el,
                "error": "采集完成但 0 行——地址/链路由可疑"}
    return {"status": "done", "elapsed_s": el, "from_block": fb, "outdir": v2dir, **st}


# ---------------- Solana ----------------

def collect_solana(it, workdir, logf):
    mint = it["address"]
    os.makedirs(os.path.join(workdir, "data"), exist_ok=True)
    cmd = [sys.executable, FETCH_SOL, mint,
           "--wall-min", str(it.get("wall_min", 300))]
    lt = it.get("launch_ts")
    if lt:
        cmd += ["--launch-ts", str(int(lt))]
    t0 = time.time()
    rc = subprocess.call(cmd, cwd=workdir, stdout=logf, stderr=subprocess.STDOUT)
    el = round(time.time() - t0, 1)
    out = os.path.join(workdir, "data", f"soltx-{mint.lower()}.jsonl.gz")
    if rc not in (0, 2) or not os.path.exists(out):
        return {"status": "failed", "elapsed_s": el,
                "error": f"fetch_sqd_transfers_v2 退出码 {rc}（详见 data/collect.log）"}
    import gzip
    with gzip.open(out, "rt") as f:
        rows = sum(1 for _ in f)
    if rows == 0:
        return {"status": "failed", "elapsed_s": el, "error": "采集完成但 0 行"}
    res = {"status": "done" if rc == 0 else "done_with_gaps",
           "elapsed_s": el, "rows": rows, "outfile": out}
    if rc == 2:
        res["note"] = "SQD 报有缺口（详见 data/collect.log 的缺口声明）——分析会话开工时须补齐"
    if not lt:
        res["note"] = (res.get("note", "") +
                       " 未给 launch_ts，仅回看 90 天——老币早期数据可能缺失").strip()
    return res


# ---------------- main ----------------

def default_run_id():
    return os.environ.get("CHIP_RUN_ID") or \
        f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}p{os.getpid()}"


def main():
    ap = argparse.ArgumentParser(description="批量预采集队列（只采集不分析）")
    ap.add_argument("plan")
    ap.add_argument("--resume", action="store_true", help="跳过 manifest 里已 done 的项")
    ap.add_argument("--serial", action="store_true", help="关闭泳道并行，回退全串行")
    ap.add_argument("--dry-run", action="store_true", help="只打印路由计划不执行")
    ap.add_argument("--token-file", default=os.path.expanduser("~/.config/hypersync/token"))
    ap.add_argument("--run-id", default=None,
                    help="本次运行标识（默认 $CHIP_RUN_ID，再默认 时间戳p<pid>）")
    a = ap.parse_args()
    run_id = a.run_id or default_run_id()

    plan = load_plan(a.plan)
    base = plan["base_dir"]
    need_evm = any(it["chain"] in EVM_CHAINS for it in plan["items"])
    token = None
    if need_evm:
        try:
            token = open(a.token_file).read().strip()
        except OSError:
            sys.exit(f"[fatal] 读不到 HyperSync token: {a.token_file}")
        if not token:
            sys.exit(f"[fatal] token 文件为空: {a.token_file}")

    mpath = manifest_path(a.plan)
    m = load_manifest(mpath)

    if a.dry_run:
        for it in plan["items"]:
            wd = os.path.join(base, f"{it['name']}分析")
            prev = m["items"].get(item_key(it), {}).get("status")
            log(f"{it['name']:12s} {it['chain']:9s} {it['address']}  -> {wd}"
                + (f"  [manifest: {prev}]" if prev else ""))
        return

    # ---- C2 队列单实例锁：同一工作根只允许一个队列在跑 ----
    qlock = ProcLock(os.path.join(base, "collect_plans", "queue.lock"),
                     run_id=run_id, role="queue")
    ok, note = qlock.acquire()
    if not ok:
        log(f"[fatal] 队列单实例锁被占（{note}）——本次不跑，plan 保留原样")
        sys.exit(3)
    if note:
        log(f"[lock] {note}")
    log(f"[lock] 队列锁已持有 run_id={run_id}")

    # 心跳线程：60s 刷新队列锁 + 当前活跃的币锁（daemon，随主进程退出）
    active_locks = [qlock]
    alock = threading.Lock()

    def _beat():
        while True:
            time.sleep(60)
            with alock:
                for lk in active_locks:
                    lk.heartbeat()

    threading.Thread(target=_beat, daemon=True).start()

    t_all = time.time()
    mlock = threading.Lock()   # manifest 读改写竞态保护（save 本身已原子改名）

    def run_one(it, tag, i, n):
        key = item_key(it)
        with mlock:
            prev = dict(m["items"].get(key, {}))
        if a.resume and prev.get("status") == "done":
            log(f"[{tag}]({i}/{n}) {it['name']} 已完成，跳过")
            return
        workdir = os.path.join(base, f"{it['name']}分析")
        os.makedirs(os.path.join(workdir, "data"), exist_ok=True)
        # ---- C2 每币目录写锁：别的进程（或本进程另一泳道）在写就跳过 ----
        clock = ProcLock(os.path.join(workdir, "data", ".collect.lock"),
                         run_id=run_id, role=f"collect:{it['name']}")
        got, cnote = clock.acquire()
        if not got:
            log(f"[{tag}]({i}/{n}) {it['name']} 目录被占，跳过（{cnote}）")
            with mlock:
                m["items"][key] = {**it, "status": "skipped_locked",
                                   "error": f"币目录写锁被占：{cnote}",
                                   "finished": now_iso()}
                save_manifest(mpath, m)
            return
        if cnote:
            log(f"[{tag}] {it['name']} {cnote}")
        with alock:
            active_locks.append(clock)
        log(f"[{tag}]({i}/{n}) {it['name']} [{it['chain']}] 开始 -> {workdir}")
        with mlock:
            m["items"][key] = {**it, "status": "running", "started": now_iso(),
                               "run_id": run_id}
            save_manifest(mpath, m)
        logpath = os.path.join(workdir, "data", "collect.log")
        try:
            with open(logpath, "a") as logf:
                logf.write(f"\n===== collect_queue {now_iso()} {it['name']} "
                           f"{it['chain']} run_id={run_id} =====\n")
                logf.flush()
                try:
                    if it["chain"] in EVM_CHAINS:
                        res = collect_evm(it, workdir, token, a.token_file, logf)
                    else:
                        res = collect_solana(it, workdir, logf)
                except Exception as e:  # 单项异常不塌整个队列
                    res = {"status": "failed", "error": f"{type(e).__name__}: {e}"}
        finally:
            with alock:
                active_locks.remove(clock)
            clock.release()
        with mlock:
            m["items"][key] = {**it, **res, "finished": now_iso(), "run_id": run_id}
            save_manifest(mpath, m)
        log(f"[{tag}] {it['name']} -> {res['status']}"
            + (f" rows={res.get('rows'):,}" if res.get("rows") else "")
            + (f" 用时 {res.get('elapsed_s')}s" if res.get("elapsed_s") else "")
            + (f" | {res.get('error')}" if res.get("error") else ""))

    def run_lane(tag, lane_items):
        for i, it in enumerate(lane_items, 1):
            run_one(it, tag, i, len(lane_items))

    evm_items = [it for it in plan["items"] if it["chain"] in EVM_CHAINS]
    sol_items = [it for it in plan["items"] if it["chain"] == "solana"]
    if a.serial or not (evm_items and sol_items):
        run_lane("all", plan["items"])          # 单泳道场景/显式回退：原串行行为
    else:
        lanes = [threading.Thread(target=run_lane, args=("evm", evm_items), daemon=True),
                 threading.Thread(target=run_lane, args=("sol", sol_items), daemon=True)]
        for t in lanes:
            t.start()
        for t in lanes:
            t.join()

    # 汇总（严重度：failed > gaps > done；退出码 1=有失败 2=仅有缺口 0=全完成）
    log(f"全部结束，总用时 {time.time() - t_all:.0f}s。汇总：")
    has_fail, has_gap = False, False
    for it in plan["items"]:
        r = m["items"].get(item_key(it), {})
        s = r.get("status", "?")
        line = (f"  {it['name']:12s} {it['chain']:9s} {s:15s}"
                + (f" rows={r.get('rows'):,}" if r.get("rows") else "")
                + (f" [{r.get('min_block')},{r.get('max_block')}]" if r.get("min_block") is not None else ""))
        if r.get("error"):
            line += f"  错误: {r['error']}"
        if r.get("note"):
            line += f"  注: {r['note']}"
        log(line)
        if s == "done_with_gaps":
            has_gap = True
        elif s != "done":
            has_fail = True   # failed / skipped_locked / 意外状态都算未完成
    log(f"manifest: {mpath}")
    qlock.release()
    sys.exit(1 if has_fail else (2 if has_gap else 0))


if __name__ == "__main__":
    main()
