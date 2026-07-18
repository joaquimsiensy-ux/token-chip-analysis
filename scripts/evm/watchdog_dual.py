#!/usr/bin/env python3
"""双通道采集守护（与 Claude 会话解耦的 nohup 常驻，跨天无人值守标准件）：
1) 探测第二通道可用（如 Alchemy 目标网络被启用）-> 自启其采集器
2) 主通道完成而第二通道始终不可用 -> 回收其段（.prog 重置回段首）交还主通道兜底
3) 任一采集进程意外死亡 -> 自动重启（段级断点续传保证不重不漏）
4) 全部段落定 -> 写 <outdir>/ALL_DONE 退出
会话侧配套：Monitor tail -f 本脚本日志 grep "ALL_DONE|FALLBACK|PRIMARY_DEAD|SECONDARY_DEAD|watchdog error"

用法: nohup python3 watchdog_dual.py --config config.json >> <outdir>/watchdog.log 2>&1 &
config.json 的 "watchdog" 节（见 config.example.json）：
  outdir/plan（plan.json 路径，由 fetch_hypersync_par.py 生成）
  primary:   {cmd:[...], pgrep:"进程匹配串", seg_max:N, log:"..."}   # 负责段 0..seg_max
  secondary: {cmd:[...], pgrep:"...", probe_url:"...", probe_proxy:"", log:"..."}  # 负责段 seg_max+1..末段；可整节省略=纯主通道守护
（来源：VIRTUAL(Base+ETH) 多链分析 2026-07-18 收编，v3.4 参数化）"""
import json, os, subprocess, time, sys, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="config.json")
a = ap.parse_args()
W = json.load(open(a.config))["watchdog"]
OUT = W["outdir"]
PLAN = json.load(open(W["plan"]))
PRI = W["primary"]
SEC = W.get("secondary")
SEG_MAX = PRI.get("seg_max", max(i for i, _, _ in PLAN["segments"]))


def log(*x):
    print(time.strftime("%F %T"), *x, flush=True)


def pgrep(pat):
    r = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True)
    return [p for p in r.stdout.split() if p.strip()]


def secondary_enabled():
    if not SEC or not SEC.get("probe_url"):
        return False
    cmd = ["curl", "-s", "--max-time", "20"]
    if SEC.get("probe_proxy"):
        cmd += ["-x", SEC["probe_proxy"]]
    cmd += ["-X", "POST", "-H", "Content-Type: application/json",
            "-d", '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}',
            SEC["probe_url"]]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return '"result"' in r.stdout
    except Exception:
        return False


def csv_has_data(i):
    try:
        with open(os.path.join(OUT, f"part_{i:02d}.csv"), "rb") as fh:
            return len(fh.read(2048).splitlines()) > 1
    except Exception:
        return False


def seg_done(i, s0, s1):
    try:
        prog_ok = int(open(os.path.join(OUT, f"part_{i:02d}.prog")).read().strip()) >= s1
    except Exception:
        prog_ok = False
    if i > SEG_MAX:  # 第二通道段：完成以 .aldone 标记为准
        return os.path.exists(os.path.join(OUT, f"part_{i:02d}.aldone")) or (prog_ok and csv_has_data(i))
    return prog_ok and csv_has_data(i)


def all_covered():
    return all(seg_done(i, s0, s1) for i, s0, s1 in PLAN["segments"])


def reclaim_orphan_segs():
    n = 0
    for i, s0, s1 in PLAN["segments"]:
        if i > SEG_MAX and not os.path.exists(os.path.join(OUT, f"part_{i:02d}.aldone")) and not csv_has_data(i):
            open(os.path.join(OUT, f"part_{i:02d}.prog"), "w").write(str(s0))
            n += 1
            log(f"reclaimed seg{i:02d} back to primary")
    return n


def start(cmd, logfile):
    with open(logfile, "a") as lf:
        subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)


sec_state = ("started" if SEC and os.path.exists(SEC.get("log", "")) else "waiting") if SEC else "absent"
log(f"watchdog up. secondary_state={sec_state}")
while True:
    try:
        if all_covered():
            busy = pgrep(PRI["pgrep"]) or (SEC and pgrep(SEC["pgrep"]))
            if not busy:
                open(os.path.join(OUT, "ALL_DONE"), "w").write(time.strftime("%F %T"))
                log("ALL_DONE all segments covered, exiting")
                sys.exit(0)
        # 第二通道探测与自启
        if sec_state == "waiting" and secondary_enabled():
            log("SECONDARY_ENABLED starting collector")
            start(SEC["cmd"], SEC["log"])
            sec_state = "started"
        # 第二通道死亡重启（有未完段才重启）
        if sec_state == "started" and not pgrep(SEC["pgrep"]):
            pend = [i for i, s0, s1 in PLAN["segments"] if i > SEG_MAX and not seg_done(i, s0, s1)]
            if pend:
                log(f"SECONDARY_DEAD pending={pend} restarting")
                start(SEC["cmd"], SEC["log"])
        # 主通道守护
        if not pgrep(PRI["pgrep"]):
            pri_pend = [i for i, s0, s1 in PLAN["segments"] if i <= SEG_MAX and not seg_done(i, s0, s1)]
            if pri_pend:
                log(f"PRIMARY_DEAD pending={pri_pend} restarting")
                start(PRI["cmd"], PRI["log"])
            elif sec_state == "waiting":
                n = reclaim_orphan_segs()
                if n:
                    log(f"FALLBACK primary takes back {n} segs (secondary never enabled)")
                    start(PRI["cmd"], PRI["log"])
                    sec_state = "fallback"
    except Exception as e:
        log("watchdog error:", str(e)[:200])
    time.sleep(60)
