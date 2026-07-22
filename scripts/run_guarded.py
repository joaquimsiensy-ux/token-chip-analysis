#!/usr/bin/env python3
"""长跑任务监督器（B9，2026-07-22 DuckDB 引擎改造工程配套）——脱管启动+内存水位+状态落盘。

解决两类实战事故（references/environment.md 记档）：
  ①Claude Code 沙箱/会话清理连带杀采集进程（exit 144、进程组消失）——子进程以新
   会话（start_new_session）脱管，监督器本身可 --detach 自守护；
  ②亿级任务内存失控逼近 16GB 物理线 → 系统假死/OOM——psutil 双水位（任务树 RSS
   上限 + 系统可用内存下限），越线先 SIGTERM 宽限再 SIGKILL，事故写进状态文件。

状态文件 <name>.status.json 原子写（.tmp+rename），字段：
  pid/cmd/started/ended/exit_code/peak_rss_gb/killed_by_guard/reason
进程存活检测用 psutil（macOS 无 /proc——不可用 [ -d /proc/pid ]，environment.md 坑）。

用法：
  python3 run_guarded.py --name quq_prep --mem-ceiling-gb 12 --min-free-gb 2 \
      [--detach] -- python3 heavy_script.py args...
  查状态：cat <name>.status.json；看日志：tail -f <name>.log
  （多任务串行队列场景用 pueue：`pueued -d` 起守护进程后 `pueue add -- <命令>`）
"""
import argparse, datetime, json, os, signal, subprocess, sys, time

import psutil


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_status(path, obj):
    tmp = path + ".tmp"
    json.dump(obj, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, path)          # 原子改名——防"文件存在但只写了一半"


def tree_rss(proc):
    try:
        procs = [proc] + proc.children(recursive=True)
        return sum(p.memory_info().rss for p in procs
                   if p.is_running()), len(procs)
    except psutil.Error:
        return 0, 0


def kill_tree(proc, sig):
    try:
        for p in [proc] + proc.children(recursive=True):
            try:
                p.send_signal(sig)
            except psutil.Error:
                pass
    except psutil.Error:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="任务名（日志/状态文件前缀）")
    ap.add_argument("--mem-ceiling-gb", type=float, default=12.0,
                    help="任务进程树 RSS 上限（默认 12GB；16GB 机器留 4GB 余量）")
    ap.add_argument("--min-free-gb", type=float, default=1.5,
                    help="系统可用内存下限（默认 1.5GB，谁超谁触发）")
    ap.add_argument("--interval", type=float, default=5.0, help="巡检间隔秒")
    ap.add_argument("--out-dir", default=".", help="日志与状态文件目录")
    ap.add_argument("--detach", action="store_true", help="监督器自守护（立刻返回，后台巡检）")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="-- 后接被守护命令")
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        raise SystemExit("用法：run_guarded.py --name X [选项] -- <命令...>")

    os.makedirs(a.out_dir, exist_ok=True)
    log_path = os.path.join(a.out_dir, f"{a.name}.log")
    st_path = os.path.join(a.out_dir, f"{a.name}.status.json")

    if a.detach:
        # 自守护：fork 出独立会话的监督器副本，父进程立刻返回
        args = [sys.executable, os.path.abspath(__file__),
                "--name", a.name, "--mem-ceiling-gb", str(a.mem_ceiling_gb),
                "--min-free-gb", str(a.min_free_gb), "--interval", str(a.interval),
                "--out-dir", os.path.abspath(a.out_dir), "--"] + cmd
        sup = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, start_new_session=True)
        print(f"[run_guarded] 监督器已脱管 pid={sup.pid}；状态 {st_path}；日志 {log_path}")
        return 0

    log_f = open(log_path, "a")
    child = subprocess.Popen(cmd, stdout=log_f, stderr=log_f,
                             start_new_session=True)
    st = {"name": a.name, "pid": child.pid, "cmd": cmd, "started": now(),
          "ended": None, "exit_code": None, "peak_rss_gb": 0.0,
          "killed_by_guard": False, "reason": None,
          "mem_ceiling_gb": a.mem_ceiling_gb, "min_free_gb": a.min_free_gb}
    write_status(st_path, st)
    try:
        proc = psutil.Process(child.pid)
    except psutil.NoSuchProcess:
        proc = None
    ceiling = a.mem_ceiling_gb * 2**30
    min_free = a.min_free_gb * 2**30

    while child.poll() is None:
        if proc is not None:
            rss, nprocs = tree_rss(proc)
            st["peak_rss_gb"] = max(st["peak_rss_gb"], round(rss / 2**30, 2))
            avail = psutil.virtual_memory().available
            breach = ("任务树 RSS %.1fGB 超上限 %.1fGB" % (rss / 2**30, a.mem_ceiling_gb)
                      if rss > ceiling else
                      "系统可用内存 %.1fGB 低于下限 %.1fGB" % (avail / 2**30, a.min_free_gb)
                      if avail < min_free else None)
            if breach:
                st["killed_by_guard"] = True
                st["reason"] = breach
                write_status(st_path, st)
                kill_tree(proc, signal.SIGTERM)
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    kill_tree(proc, signal.SIGKILL)
                break
            write_status(st_path, st)
        time.sleep(a.interval)

    child.wait()
    st["ended"] = now()
    st["exit_code"] = child.returncode
    write_status(st_path, st)
    log_f.close()
    tag = "被水位守护终止" if st["killed_by_guard"] else "完成"
    print(f"[run_guarded] {a.name} {tag}：exit={child.returncode} "
          f"峰值 {st['peak_rss_gb']}GB（{st_path}）")
    return 0 if child.returncode == 0 and not st["killed_by_guard"] else 1


if __name__ == "__main__":
    sys.exit(main())
