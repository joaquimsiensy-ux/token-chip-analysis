#!/usr/bin/env python3
"""peaks_daily 上界公式与触发日闭环契约测试（离线合成 parquet，不依赖真库）。

覆盖（2026-08-02 codex 复核修复的回归防线）：
  1. 同日等额进出反例：地址同日 +100/-100、次日 +50 —— 真实盘中峰值 100。
     旧公式 Σmax(day_delta,0) 给 50（同日对冲被吞、漏检）；新公式
     "昨日日终余额+当日毛流入" 必须给 100 且该址落入 needs_block_precision。
  2. ub_formula 口径标记：peaks_summary.json 必须带 prev_close_plus_gross_in/v2
     （发布闸按它拒旧公式产物）。
  3. 触发日闭环：--trigger-days 产出 trigger_days.json，逐触发日列当日活跃候选；
     空清单无 empty_reason → exit 2（fail-closed）；显式空声明 → 正常产出。
用法：python3 scripts/tests/test_peaks_daily.py   退出码 0=PASS / 1=FAIL
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "evm", "peaks_daily.py")
FAILS = []

TOT = 10000                      # 合成总供应（wei 级小数字，1% = 100）
X = "0x" + "11" * 20             # 同日对冲反例地址
Y = "0x" + "22" * 20             # 对照地址（同日买入不卖）
ZT = "0x" + "0" * 64             # mint 侧 topic（全零）


def topic(addr):
    return "0x" + "0" * 24 + addr[2:]


def amt(v):
    return f"0x{v:064x}"


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
    else:
        print(f"ok    {name}")


def build_fixture(d):
    import duckdb
    logs_dir = os.path.join(d, "logs")
    os.makedirs(os.path.join(logs_dir, "run_0"))
    con = duckdb.connect()
    con.execute("""CREATE TABLE t (block_number BIGINT, log_index BIGINT,
                   topic1 VARCHAR, topic2 VARCHAR, data VARCHAR)""")
    rows = [
        # day 1970-01-02：mint→X 100（block 1），X→Y 100（block 2）——X 同日等额进出
        (1, 0, ZT, topic(X), amt(100)),
        (2, 0, topic(X), topic(Y), amt(100)),
        # day 1970-01-03：mint→X 50（block 3）
        (3, 0, ZT, topic(X), amt(50)),
    ]
    con.executemany("INSERT INTO t VALUES (?,?,?,?,?)", rows)
    con.execute(f"COPY t TO '{logs_dir}/run_0/logs.parquet' (FORMAT parquet)")
    con.execute("CREATE TABLE b (block_number BIGINT, ts_i BIGINT)")
    con.executemany("INSERT INTO b VALUES (?,?)",
                    [(1, 86400), (2, 90000), (3, 172800)])
    bp = os.path.join(d, "blockts.parquet")
    con.execute(f"COPY b TO '{bp}' (FORMAT parquet)")
    con.close()
    return logs_dir, bp


def run(logs_dir, bp, out, extra=None):
    args = [sys.executable, SCRIPT, "--logs", logs_dir, "--blockts", bp,
            "--total-supply-wei", str(TOT), "--out-dir", out,
            "--pct", "0.01", "--levels", "0.01"] + (extra or [])
    return subprocess.run(args, capture_output=True, text=True)


def main():
    d = tempfile.mkdtemp(prefix="peaks_daily_test_")
    logs_dir, bp = build_fixture(d)

    # ---- 1+2+3 正常路径（带触发日）----
    out1 = os.path.join(d, "out1")
    trig = os.path.join(d, "trig.json")
    json.dump(["1970-01-03"], open(trig, "w"))
    p = run(logs_dir, bp, out1, ["--trigger-days", trig])
    check("正常路径 exit 0", p.returncode == 0)
    if p.returncode != 0:
        print(p.stdout, p.stderr)
        return finish()

    peaks = json.load(open(os.path.join(out1, "peaks_daily.json")))
    px, py = peaks[X], peaks[Y]
    check("X 日末峰值=50（同日对冲后日终只剩次日仓）", px["peak_daily"] == "50")
    check("X 上界=100（昨收0+当日毛流入100；旧公式 Σmax(day_delta,0) 只给 50=漏检反例）",
          px["upper_bound"] == "100")
    check("X 上界日=对冲当日", px["ub_day"] == "1970-01-02")
    check("Y 对照：峰值=上界=100", py["peak_daily"] == "100" and py["upper_bound"] == "100")

    need = json.load(open(os.path.join(out1, "needs_block_precision.json")))
    hit = need.get("0.0100", [])
    check("X 落入 needs_block_precision（L1 50<100≤L2 100）", X in hit)
    check("Y 不误入名单（L1 已达标）", Y not in hit)

    summary = json.load(open(os.path.join(out1, "peaks_summary.json")))
    check("summary 带新公式标记 ub_formula=prev_close_plus_gross_in/v2",
          summary.get("ub_formula") == "prev_close_plus_gross_in/v2")

    tdj = json.load(open(os.path.join(out1, "trigger_days.json")))
    check("trigger_days schema", tdj.get("schema") == "trigger-days-replay/v1")
    day2 = tdj.get("days", {}).get("1970-01-03", {})
    check("触发日活跃候选=仅 X（Y 当日无动作）", day2.get("active_candidates") == [X])

    # ---- 3b. 空触发日无声明 → exit 2 ----
    trig_empty = os.path.join(d, "trig_empty.json")
    json.dump([], open(trig_empty, "w"))
    out2 = os.path.join(d, "out2")
    p2 = run(logs_dir, bp, out2, ["--trigger-days", trig_empty])
    check("空触发日且无 empty_reason → exit 2", p2.returncode == 2)

    # ---- 3c. 显式空声明 → 正常产出 ----
    trig_decl = os.path.join(d, "trig_decl.json")
    json.dump({"days": {}, "empty_reason": "合成案：窗内无发射/毕业/±50%/±10pp 日"},
              open(trig_decl, "w"))
    out3 = os.path.join(d, "out3")
    p3 = run(logs_dir, bp, out3, ["--trigger-days", trig_decl])
    t3 = json.load(open(os.path.join(out3, "trigger_days.json")))
    check("显式空声明 → exit 0 且 empty_reason 落盘",
          p3.returncode == 0 and t3.get("empty_reason", "").startswith("合成案"))

    return finish()


def finish():
    print(f"\n{'PASS' if not FAILS else 'FAIL'}：{len(FAILS)} 项失败")
    for f in FAILS:
        print(f"  - {f}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
