"""SQD 日级锚点采样器 v2:串行滚动校准(从新到旧,逐日外推,自建 slot<->ts 校准表)。

用法: python3 anchor_sampler.py --start YYYY-MM-DD [--end YYYY-MM-DD] --as-of-slot N \
      --out data/anchors_daily.jsonl --receipt anchor_sampler_receipt.json
参考锚定点(冷启动必需): 工作目录 config.json 的 ref_slot/ref_ts 字段,或 CLI --ref-slot/--ref-ts。
  取法:对当前时刻做一次 getSlot + getBlockTime 即得(任意近期 slot 与其时间戳的一对映射)。
输出: anchors JSONL + solana-anchor-sampler-receipt/v2；任一失败日完整落明细后 exit 2。
断点续传:已有日期跳过,且其 (slot,ts) 进校准表。

⚠观测边界(pipeline §11.3):名义 1h 窗在高活跃期因响应截断实际可能仅数分钟,且只记发生
变动的账户——静止大户系统性漏观测,锚点单独不可作阴性依据,须快照/全流水兜底。
"""
import argparse, hashlib, json, os, subprocess, sys, time, datetime, bisect
from pathlib import Path

SQD = "https://portal.sqd.dev/datasets/solana-mainnet/stream"
CFG = json.loads(Path("config.json").read_text())
MINT = CFG["mint"]
WIN = 9000  # ~1h


def fetch_window(frm, to):
    body = {"type": "solana", "fromBlock": frm, "toBlock": to,
            "fields": {"block": {"number": True, "timestamp": True},
                       "transaction": {"transactionIndex": True, "err": True},
                       "tokenBalance": {"transactionIndex": True, "account": True,
                                        "postOwner": True, "postAmount": True}},
            "tokenBalances": [{"postMint": [MINT], "transaction": True}]}
    for attempt in range(4):
        try:
            p = subprocess.run(["curl", "-s", "-m", "150", "-X", "POST", SQD,
                                "-H", "Content-Type: application/json", "-d", json.dumps(body)],
                               capture_output=True, text=True, timeout=170)
            lines = [ln for ln in p.stdout.strip().split("\n") if ln]
            blocks = []
            ok = True
            for ln in lines:
                try:
                    blocks.append(json.loads(ln))
                except ValueError:
                    ok = False
                    break
            if ok:
                return blocks
        except Exception:
            pass
        time.sleep(2 * (attempt + 1))
    return None


class Calib:
    """slot<->ts 校准表:分段线性。"""
    def __init__(self, ref_ts, ref_slot):
        self.pts = [(ref_ts, ref_slot)]

    def add(self, ts, slot):
        self.pts.append((ts, slot))
        self.pts.sort()

    def slot_for(self, ts):
        pts = self.pts
        if len(pts) == 1:
            t0, s0 = pts[0]
            return int(s0 - (t0 - ts) * 2.5)
        i = bisect.bisect_left(pts, (ts, 0))
        if i == 0:
            (t1, s1), (t2, s2) = pts[0], pts[1]
        elif i >= len(pts):
            (t1, s1), (t2, s2) = pts[-2], pts[-1]
        else:
            (t1, s1), (t2, s2) = pts[i - 1], pts[i]
        if t2 == t1:
            return s1
        rate = (s2 - s1) / (t2 - t1)
        return int(s1 + (ts - t1) * rate)


def parse_blocks(blocks):
    accounts = {}
    ts_seen = None
    n_rows = 0
    first_slot = None
    for b in blocks:
        hdr = b.get("header", {})
        if hdr.get("timestamp"):
            if ts_seen is None:
                ts_seen = hdr["timestamp"]
                first_slot = hdr.get("number")
        errmap = {tx.get("transactionIndex"): tx.get("err") for tx in b.get("transactions") or []}
        for r in b.get("tokenBalances") or []:
            if errmap.get(r.get("transactionIndex")) is not None:
                continue
            acct = r.get("account")
            if not acct:
                continue
            n_rows += 1
            accounts[acct] = {"owner": r.get("postOwner"), "post": r.get("postAmount")}
    return accounts, ts_seen, n_rows, first_slot


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_json(path, payload):
    out = Path(path).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.name}.tmp.{os.getpid()}")
    try:
        with tmp.open("x", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, out)
    finally:
        if tmp.exists(): tmp.unlink()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="采样起始日 YYYY-MM-DD(通常=发射日)")
    ap.add_argument("--end", default=None)
    ap.add_argument("--ref-slot", type=int, default=CFG.get("ref_slot"))
    ap.add_argument("--ref-ts", type=int, default=CFG.get("ref_ts"))
    ap.add_argument("--as-of-slot", type=int, required=True,
                    help="与 accounting target 对齐的冻结 slot")
    ap.add_argument("--out", default="data/anchors_daily.jsonl")
    ap.add_argument("--receipt", required=True)
    args = ap.parse_args(argv)

    if not args.ref_slot or not args.ref_ts:
        sys.exit("缺参考锚定点:config.json 加 ref_slot/ref_ts,或传 --ref-slot/--ref-ts"
                 "(取法:getSlot + getBlockTime 一对近期映射)")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    calib = Calib(args.ref_ts, args.ref_slot)
    done = set()
    if out.exists():
        for ln in out.read_text().splitlines():
            try:
                r = json.loads(ln)
                done.add(r["date"])
                if r.get("ts_seen") and r.get("from_slot"):
                    calib.add(r["ts_seen"], r["from_slot"] + 0)
            except Exception:
                pass

    end = args.end or datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    d0 = datetime.date.fromisoformat(args.start)
    d1 = datetime.date.fromisoformat(end)
    days = []
    d = d1  # 从新到旧
    while d >= d0:
        s = d.isoformat()
        if s not in done:
            days.append(s)
        d -= datetime.timedelta(days=1)
    print(f"target days: {len(days)} (skip {len(done)}), order new->old", flush=True)

    t0 = time.time()
    fails = 0
    for idx, ds in enumerate(days):
        want = int(datetime.datetime.fromisoformat(ds + "T00:00:00+00:00").timestamp())
        res = None
        frm = calib.slot_for(want)
        for attempt in range(3):
            blocks = fetch_window(frm, frm + WIN)
            if blocks is None:
                res = {"date": ds, "error": "fetch_fail", "from_slot": frm, "to_slot": frm + WIN}
                break
            accounts, ts_seen, n_rows, first_slot = parse_blocks(blocks)
            if ts_seen is None:
                # 窗内无该 mint 活动:接受(低活跃日),但没有 ts 反馈
                res = {"date": ds, "from_slot": frm, "to_slot": frm + WIN, "ts_seen": None,
                       "n_rows": 0, "accounts": {}}
                break
            drift = ts_seen - want
            if abs(drift) <= 4 * 3600:
                res = {"date": ds, "from_slot": first_slot or frm, "to_slot": frm + WIN,
                       "ts_seen": ts_seen, "n_rows": n_rows, "accounts": accounts}
                calib.add(ts_seen, first_slot or frm)
                break
            # 偏了:把这次观测加进校准表再重估
            calib.add(ts_seen, first_slot or frm)
            frm = calib.slot_for(want)
        else:
            res = {"date": ds, "error": "no_converge", "from_slot": frm}
        if res.get("error"):
            fails += 1
        with open(out, "a") as f:
            f.write(json.dumps(res, separators=(",", ":")) + "\n")
        if (idx + 1) % 25 == 0:
            print(f"{idx+1}/{len(days)} days ({ds}), fails={fails}, elapsed={time.time()-t0:.0f}s", flush=True)
    print(f"DONE {len(days)} days, fails={fails}, {time.time()-t0:.0f}s", flush=True)
    failures = []
    covered = 0
    try:
        for line in out.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if args.start <= str(row.get("date", "")) <= end:
                if row.get("error"):
                    failures.append({"date": row.get("date"), "error": row.get("error"),
                                     "from_slot": row.get("from_slot"),
                                     "to_slot": row.get("to_slot")})
                else:
                    covered += 1
        verdict = "FAIL" if failures else "PASS"
        exit_code = 2 if failures else 0
        receipt = {
            "schema": "solana-anchor-sampler-receipt/v2",
            "target": {"chain": "solana", "token": MINT,
                       "as_of_block": args.as_of_slot},
            "date_range": {"start": args.start, "end": end},
            "output": {"path": str(out.resolve()), "size": out.stat().st_size,
                       "sha256": _sha256(out)},
            "coverage": {"requested_days": (d1 - d0).days + 1,
                         "covered_days": covered, "failed_days": len(failures)},
            "failures": failures, "verdict": verdict, "exit_code": exit_code,
        }
        _atomic_json(args.receipt, receipt)
        return exit_code
    except Exception as exc:
        print(f"[anchor_sampler] receipt 生成失败（exit 1）: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
