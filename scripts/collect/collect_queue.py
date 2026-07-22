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
  - 串行执行（HyperSync 限流 key 级共享 + SQD 单 IP 带宽整形，并行只会互抢）
  - 单项失败不阻塞后续；结束码 0=全部完成 2=有缺口(Solana gaps) 1=有失败
  - manifest（collect_manifest.json，plan 同目录）逐项原子更新；--resume 跳过 done 项
    （不带 --resume 重跑也安全：底层采集器自动续拉，幂等）
  - EVM 残缺 run（无 done.json）开跑前自动改名 partial_run_*_<ts> 隔离——只改名不删除，
    防 partial parquet 污染下游 run_*/ glob
  - 只做采集侧完整性校验（done.json/行数/块范围）；对账三查是分析会话 E2 的事
夜间脱管跑法（推荐）:
  python3 <skill>/scripts/run_guarded.py --detach --mem-gb 6 --name collect \
      -- python3 <skill>/scripts/collect/collect_queue.py plan.json
（来源：B12 批量预采集，2026-07-22）"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import time

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "evm"))
from transfers_lib import get_deploy_block  # noqa: E402

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


def collect_evm(it, workdir, token, logf):
    chain, addr = it["chain"], it["address"].lower()
    v2dir = os.path.join(workdir, "data", "v2")
    os.makedirs(v2dir, exist_ok=True)
    quarantine_partial_runs(v2dir)
    url = f"https://{chain}.hypersync.xyz"

    fb = get_deploy_block(chain, addr, lambda: probe_deploy_block(chain, addr, token))
    if fb is None:
        return {"status": "failed",
                "error": f"{chain} 链上未发现该合约的任何 Transfer——检查链路由/地址是否匹配"}
    cmd = [sys.executable, FETCH_V2, token, str(fb), "--url", url,
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

def main():
    ap = argparse.ArgumentParser(description="批量预采集队列（只采集不分析）")
    ap.add_argument("plan")
    ap.add_argument("--resume", action="store_true", help="跳过 manifest 里已 done 的项")
    ap.add_argument("--dry-run", action="store_true", help="只打印路由计划不执行")
    ap.add_argument("--token-file", default=os.path.expanduser("~/.config/hypersync/token"))
    a = ap.parse_args()

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

    t_all = time.time()
    for i, it in enumerate(plan["items"], 1):
        key = item_key(it)
        prev = m["items"].get(key, {})
        if a.resume and prev.get("status") == "done":
            log(f"({i}/{len(plan['items'])}) {it['name']} 已完成，跳过")
            continue
        workdir = os.path.join(base, f"{it['name']}分析")
        os.makedirs(os.path.join(workdir, "data"), exist_ok=True)
        log(f"({i}/{len(plan['items'])}) {it['name']} [{it['chain']}] 开始 -> {workdir}")
        m["items"][key] = {**it, "status": "running", "started": now_iso()}
        save_manifest(mpath, m)
        logpath = os.path.join(workdir, "data", "collect.log")
        with open(logpath, "a") as logf:
            logf.write(f"\n===== collect_queue {now_iso()} {it['name']} {it['chain']} =====\n")
            logf.flush()
            try:
                if it["chain"] in EVM_CHAINS:
                    res = collect_evm(it, workdir, token, logf)
                else:
                    res = collect_solana(it, workdir, logf)
            except Exception as e:  # 单项异常不塌整个队列
                res = {"status": "failed", "error": f"{type(e).__name__}: {e}"}
        m["items"][key] = {**it, **res, "finished": now_iso()}
        save_manifest(mpath, m)
        log(f"  -> {res['status']}"
            + (f" rows={res.get('rows'):,}" if res.get("rows") else "")
            + (f" 用时 {res.get('elapsed_s')}s" if res.get("elapsed_s") else "")
            + (f" | {res.get('error')}" if res.get("error") else ""))

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
            has_fail = True
    log(f"manifest: {mpath}")
    sys.exit(1 if has_fail else (2 if has_gap else 0))


if __name__ == "__main__":
    main()
