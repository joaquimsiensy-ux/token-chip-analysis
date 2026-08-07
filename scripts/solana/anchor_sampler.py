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
import argparse, json, os, sys, time, datetime, bisect
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import net
from receipt_kernel import (RawBytes, assert_distinct_paths, build_envelope,
                            finalize_envelope, publish_error_receipt, publish_overwrite,
                            publish_txn)

SQD = "https://portal.sqd.dev/datasets/solana-mainnet/stream"
CFG = json.loads(Path("config.json").read_text())
MINT = CFG["mint"]
WIN = 9000  # ~1h
SCHEMA = "solana-anchor-sampler-receipt/v2"
ROW_IDENTITY = {"chain": "solana", "mint": MINT, "endpoint": SQD}


def fetch_window(frm, to, endpoint=SQD):
    body = {"type": "solana", "fromBlock": frm, "toBlock": to,
            "fields": {"block": {"number": True, "timestamp": True},
                       "transaction": {"transactionIndex": True, "err": True},
                       "tokenBalance": {"transactionIndex": True, "account": True,
                                        "postOwner": True, "postAmount": True}},
            "tokenBalances": [{"postMint": [MINT], "transaction": True}]}
    result = net.curl_json(endpoint, post_json=body, timeout=150, attempts=4)
    if not result.ok:
        return None
    blocks = result.value
    if isinstance(blocks, dict):
        blocks = [blocks]
    if not isinstance(blocks, list) or any(not isinstance(block, dict) for block in blocks):
        return None
    for block in blocks:
        number = (block.get("header") or {}).get("number")
        if not isinstance(number, int) or number < frm or number > to:
            return None
    return blocks


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


def _identity_error(row, cutoff, seen_dates, endpoint=SQD):
    missing = [key for key in (*ROW_IDENTITY, "as_of_slot") if key not in row]
    if missing:
        return f"旧格式缺身份列 {missing}，拒绝复用；请重采"
    expected = {**ROW_IDENTITY, "endpoint": endpoint, "as_of_slot": cutoff}
    mismatched = [key for key, value in expected.items() if row.get(key) != value]
    if mismatched:
        return f"resume 身份不匹配 {mismatched}，拒绝复用；请重采"
    date = row.get("date")
    if not isinstance(date, str) or date in seen_dates:
        return f"resume 日期缺失或重复: {date!r}"
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        return f"resume 日期不可解析: {date!r}"
    if row.get("error"):
        return f"resume 含失败行 {date}: {row.get('error')}；请重采"
    for key in ("from_slot", "to_slot"):
        value = row.get(key)
        if not isinstance(value, int) or value < 0 or value > cutoff:
            return f"resume {key}={value!r} 越过 cutoff={cutoff} 或不是非负整数"
    return None


def _with_identity(row, cutoff, endpoint=SQD):
    return {**row, **ROW_IDENTITY, "endpoint": endpoint, "as_of_slot": cutoff}


def _error_receipt(receipt_path, envelope, message):
    try:
        error_path = publish_error_receipt(receipt_path, envelope, message)
        print(f"[anchor_sampler] ERROR → {error_path}", file=sys.stderr)
    except Exception as exc:
        print(f"[anchor_sampler] ERROR receipt 发布失败: {exc}", file=sys.stderr)


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
    ap.add_argument("--endpoint", default=SQD)
    args = ap.parse_args(argv)

    target = {"chain": "solana", "token": MINT.lower(), "as_of_block": args.as_of_slot}
    base_envelope = build_envelope(SCHEMA, target, __file__, "formal")

    if not args.ref_slot or not args.ref_ts:
        sys.exit("缺参考锚定点:config.json 加 ref_slot/ref_ts,或传 --ref-slot/--ref-ts"
                 "(取法:getSlot + getBlockTime 一对近期映射)")

    out = Path(args.out)
    partial = Path(str(out) + ".partial")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        assert_distinct_paths(out, args.receipt, partial)
    except Exception as exc:
        print(f"[anchor_sampler] 发布路径冲突: {exc}", file=sys.stderr)
        return 2
    calib = Calib(args.ref_ts, args.ref_slot)
    done = set()
    rows = []
    if out.exists():
        resume_error = None
        for line_no, ln in enumerate(out.read_text(encoding="utf-8").splitlines(), 1):
            try:
                r = json.loads(ln)
            except Exception as exc:
                resume_error = f"resume 第 {line_no} 行不可解析: {exc}；请重采"
                break
            resume_error = _identity_error(r, args.as_of_slot, done, args.endpoint)
            if resume_error:
                resume_error = f"resume 第 {line_no} 行: {resume_error}"
                break
            done.add(r["date"])
            rows.append(r)
            if r.get("ts_seen") and r.get("from_slot") is not None:
                calib.add(r["ts_seen"], r["from_slot"])
        if resume_error:
            envelope = build_envelope(SCHEMA, target, __file__, "formal", {"output": out})
            _error_receipt(args.receipt, envelope, resume_error)
            print(f"[anchor_sampler] {resume_error}", file=sys.stderr)
            return 2

    end = args.end or datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    d0 = datetime.date.fromisoformat(args.start)
    d1 = datetime.date.fromisoformat(end)
    if d0 > d1:
        print("[anchor_sampler] start 晚于 end，拒绝空计划", file=sys.stderr)
        return 2
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
            to = min(frm + WIN, args.as_of_slot)
            if frm < 0 or frm > to:
                res = _with_identity({"date": ds, "error": "range_beyond_cutoff",
                                      "from_slot": frm, "to_slot": to}, args.as_of_slot,
                                     args.endpoint)
                break
            blocks = fetch_window(frm, to, args.endpoint)
            if blocks is None:
                res = _with_identity({"date": ds, "error": "fetch_fail",
                                      "from_slot": frm, "to_slot": to}, args.as_of_slot,
                                     args.endpoint)
                break
            accounts, ts_seen, n_rows, first_slot = parse_blocks(blocks)
            if ts_seen is None:
                if blocks:
                    res = _with_identity({"date": ds, "error": "unproven_empty",
                                          "from_slot": frm, "to_slot": to}, args.as_of_slot,
                                         args.endpoint)
                    break
                # 仅成功 RPC 的结构化空列表可证明该查询窗无该 mint 活动。
                res = _with_identity({"date": ds, "from_slot": frm, "to_slot": to,
                                      "ts_seen": None, "n_rows": 0, "accounts": {}},
                                     args.as_of_slot, args.endpoint)
                break
            drift = ts_seen - want
            if abs(drift) <= 4 * 3600:
                actual_from = first_slot if first_slot is not None else frm
                if not isinstance(actual_from, int) or actual_from < 0 or actual_from > args.as_of_slot:
                    res = _with_identity({"date": ds, "error": "observed_slot_beyond_cutoff",
                                          "from_slot": actual_from, "to_slot": to}, args.as_of_slot,
                                         args.endpoint)
                    break
                res = _with_identity({"date": ds, "from_slot": actual_from, "to_slot": to,
                                      "ts_seen": ts_seen, "n_rows": n_rows,
                                      "accounts": accounts}, args.as_of_slot, args.endpoint)
                calib.add(ts_seen, first_slot or frm)
                break
            # 偏了:把这次观测加进校准表再重估
            calib.add(ts_seen, first_slot or frm)
            frm = calib.slot_for(want)
        else:
            to = min(frm + WIN, args.as_of_slot)
            res = _with_identity({"date": ds, "error": "no_converge",
                                  "from_slot": frm, "to_slot": to}, args.as_of_slot,
                                 args.endpoint)
        if res.get("error"):
            fails += 1
        rows.append(res)
        if (idx + 1) % 25 == 0:
            print(f"{idx+1}/{len(days)} days ({ds}), fails={fails}, elapsed={time.time()-t0:.0f}s", flush=True)
    print(f"DONE {len(days)} days, fails={fails}, {time.time()-t0:.0f}s", flush=True)
    failures = []
    covered = 0
    committed = False
    try:
        for row in rows:
            if args.start <= str(row.get("date", "")) <= end:
                if row.get("error"):
                    failures.append({"date": row.get("date"), "error": row.get("error"),
                                     "from_slot": row.get("from_slot"),
                                     "to_slot": row.get("to_slot")})
                else:
                    covered += 1
        envelope = build_envelope(SCHEMA, target, __file__, "formal", {"config": "config.json"})
        coverage = {"requested_days": (d1 - d0).days + 1,
                    "covered_days": covered, "failed_days": len(failures)}
        if failures:
            _error_receipt(args.receipt, envelope, json.dumps(
                {"coverage": coverage, "failures": failures}, ensure_ascii=False,
                separators=(",", ":")))
            return 2
        data_bytes = b"".join((json.dumps(row, separators=(",", ":")) + "\n").encode()
                              for row in rows)
        output_ref = {"path": str(out), "size": len(data_bytes),
                      "sha256": __import__("hashlib").sha256(data_bytes).hexdigest()}
        receipt = finalize_envelope(
            envelope, "PASS", 0, date_range={"start": args.start, "end": end},
            output=output_ref, coverage=coverage, failures=[])
        publish_txn(out, RawBytes(data_bytes), args.receipt, receipt)
        committed = True
        if __import__("hashlib").sha256(out.read_bytes()).hexdigest() != output_ref["sha256"]:
            raise RuntimeError("联合发布后独立读者哈希不一致")
        return 0
    except Exception as exc:
        withdrawal_errors = []
        if committed:
            try:
                Path(args.receipt).unlink(missing_ok=True)
            except Exception as cleanup_exc:
                withdrawal_errors.append(f"receipt: {cleanup_exc}")
            try:
                if out.exists():
                    publish_overwrite(partial, RawBytes(out.read_bytes()))
                    out.unlink()
            except Exception as cleanup_exc:
                withdrawal_errors.append(f"data: {cleanup_exc}")
        if withdrawal_errors:
            exc = RuntimeError(f"{exc}; 撤回失败: {'; '.join(withdrawal_errors)}")
        _error_receipt(args.receipt, base_envelope, exc)
        print(f"[anchor_sampler] receipt 生成失败（exit 1）: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
