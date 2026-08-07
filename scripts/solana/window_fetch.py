"""SQD 定向窗口拉取:小段(2000 slot)+并发,专攻高密度期(发射窗/事件日)。

用法: python3 window_fetch.py <from_slot> <to_slot> <out.jsonl> --receipt <receipt.json> [--conc 8]
输出: 每行 [ts, slot, from_owner, to_owner, amount_raw](与 fetch_sqd_transfers_v2.py 边格式兼容)
     失败段写入 <out>.gaps.json；gaps 非空只留 <out>.partial 并 exit 2。
"""
import argparse, json, os, sys, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import net
from receipt_kernel import (RawBytes, assert_distinct_paths, build_envelope,
                            finalize_envelope, publish_error_receipt, publish_overwrite,
                            publish_txn)

SQD = "https://portal.sqd.dev/datasets/solana-mainnet/stream"
MINT = json.loads(Path("config.json").read_text())["mint"]
ZERO = "0x" + "0" * 40
CHUNK = 2000
SCHEMA = "solana-window-fetch-receipt/v2"


def pair_tx(delta):
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


def scan_seg(frm, to, endpoint=SQD):
    """扫一段,返回 (edges, ok)。内部按 portal 游标推进,直到覆盖整段。"""
    edges, cur, fails, timestamps = [], frm, 0, []
    while cur <= to:
        body = {"type": "solana", "fromBlock": cur, "toBlock": to,
                "fields": {"block": {"number": True, "timestamp": True},
                           "transaction": {"transactionIndex": True, "err": True},
                           "tokenBalance": {"transactionIndex": True, "preOwner": True,
                                            "postOwner": True, "preAmount": True, "postAmount": True}},
                "tokenBalances": [{"postMint": [MINT], "transaction": True},
                                  {"preMint": [MINT], "transaction": True}]}
        result = net.curl_json(endpoint, post_json=body, timeout=60, attempts=1)
        if not result.ok:
            fails += 1
            if fails > 5:
                return edges, False, timestamps
            time.sleep(2 * fails)
            continue
        blocks = result.value
        if isinstance(blocks, dict):
            blocks = [blocks]
        if not isinstance(blocks, list) or any(not isinstance(block, dict) for block in blocks):
            fails += 1
            if fails > 5:
                return edges, False, timestamps
            time.sleep(2 * fails)
            continue
        last = None
        page_edges = []
        page_valid = True
        for b in blocks:
            hdr = b.get("header", {})
            number = hdr.get("number")
            if not isinstance(number, int) or number < cur or number > to:
                page_valid = False
                break
            last = number
            ts = hdr.get("timestamp")
            if (isinstance(ts, bool) or not isinstance(ts, int)
                    or ts <= 0 or ts > 4102444800):
                page_valid = False
                break
            timestamps.append(ts)
            tbs = b.get("tokenBalances") or []
            if not tbs:
                continue
            errmap = {tx.get("transactionIndex"): tx.get("err") for tx in b.get("transactions") or []}
            by_tx = defaultdict(dict)
            for r in tbs:
                ti = r.get("transactionIndex")
                if errmap.get(ti) is not None:
                    continue
                owner = r.get("postOwner") or r.get("preOwner")
                if not owner:
                    continue
                try:
                    dlt = int(r.get("postAmount") or 0) - int(r.get("preAmount") or 0)
                except (ValueError, TypeError):
                    continue
                if dlt:
                    by_tx[ti][owner] = by_tx[ti].get(owner, 0) + dlt
            for ti, delta in by_tx.items():
                for f, t, amt in pair_tx(delta):
                    page_edges.append((ts, number, f, t, amt))
        if not page_valid or last is None:
            fails += 1
            if fails > 5:
                return edges, False, timestamps
            time.sleep(2 * fails)
            continue
        edges.extend(page_edges)
        fails = 0
        cur = last + 1
    return edges, True, timestamps


def _run_id():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return f"{stamp}.{os.getpid()}"


def _publish_error(receipt_path, envelope, error, run_id):
    try:
        error_path = publish_error_receipt(receipt_path, envelope, error, run_id=run_id)
        print(f"[window_fetch] ERROR → {error_path}", file=sys.stderr)
    except Exception as exc:
        print(f"[window_fetch] ERROR receipt 发布失败: {exc}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("frm", type=int)
    ap.add_argument("to", type=int)
    ap.add_argument("out")
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--endpoint", default=SQD)
    args = ap.parse_args(argv)

    run_id = _run_id()
    out_path = Path(args.out).resolve()
    partial = Path(str(out_path) + ".partial")
    gaps_path = Path(str(out_path) + ".gaps.json")
    try:
        assert_distinct_paths(out_path, args.receipt, partial, gaps_path)
    except Exception as exc:
        print(f"[window_fetch] 发布路径冲突: {exc}", file=sys.stderr)
        return 2
    if args.frm < 0 or args.frm > args.to or args.conc < 1:
        if out_path.exists():
            stale = out_path.with_name(f"{out_path.name}.stale.{run_id}")
            if stale.exists():
                raise RuntimeError(f"stale destination already exists: {stale}")
            os.replace(out_path, stale)
        print("[window_fetch] 正式窗口要求 0 <= from_slot <= to_slot 且 conc >= 1", file=sys.stderr)
        return 2

    segs = []
    s = args.frm
    while s <= args.to:
        segs.append((s, min(s + CHUNK - 1, args.to)))
        s += CHUNK
    if not segs:
        print("[window_fetch] 计划 segment 为空，拒绝正式运行", file=sys.stderr)
        return 2
    print(f"segments: {len(segs)} x {CHUNK} slots, conc={args.conc}", flush=True)

    t0 = time.time()
    done = [0]
    gaps = []
    segment_timestamps = []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    outf = partial.open("w", encoding="utf-8")
    backup = None
    published_current = False
    lock = __import__("threading").Lock()
    target = {"chain": "solana", "token": MINT.lower(), "as_of_block": args.to}
    base_envelope = build_envelope(SCHEMA, target, __file__, "formal")

    def work(seg):
        result = scan_seg(seg[0], seg[1], args.endpoint)
        if len(result) == 2:  # legacy test adapter; production returns bound timestamps.
            e, ok = result
            timestamps = []
        else:
            e, ok, timestamps = result
        with lock:
            for row in e:
                outf.write(json.dumps(list(row), separators=(",", ":")) + "\n")
            if not ok:
                gaps.append(seg)
            segment_timestamps.append({"from_slot": seg[0], "to_slot": seg[1],
                                       "min": min(timestamps) if timestamps else None,
                                       "max": max(timestamps) if timestamps else None})
            done[0] += 1
            if done[0] % 20 == 0:
                print(f"{done[0]}/{len(segs)} segs, {time.time()-t0:.0f}s", flush=True)

    try:
        with ThreadPoolExecutor(args.conc) as ex:
            list(ex.map(work, segs))
        outf.flush(); os.fsync(outf.fileno()); outf.close()
        publish_overwrite(gaps_path, gaps)
        if gaps:
            verdict, exit_code = "FAIL", 2
            if out_path.exists():
                stale = out_path.with_name(f"{out_path.name}.stale.{run_id}")
                if stale.exists():
                    raise RuntimeError(f"stale destination already exists: {stale}")
                os.replace(out_path, stale)
            envelope = build_envelope(
                SCHEMA, target, __file__, "formal", {"output": partial, "gaps": gaps_path})
            published = envelope["inputs"]["output"]
        else:
            verdict, exit_code = "PASS", 0
            envelope = build_envelope(
                SCHEMA, target, __file__, "formal", {"gaps": gaps_path})
            data_bytes = partial.read_bytes()
            published = {"path": str(out_path), "size": len(data_bytes),
                         "sha256": __import__("hashlib").sha256(data_bytes).hexdigest()}
        if gaps:
            published = {**published, "partial": True}
        receipt = finalize_envelope(
            envelope, verdict, exit_code,
            range={"from_slot": args.frm, "to_slot": args.to,
                   "chunk_size": CHUNK, "segments": len(segs)},
            coverage={"completed_segments": len(segs) - len(gaps),
                      "gap_segments": len(gaps), "gaps": gaps},
            output=published,
            timestamps={"segments": sorted(segment_timestamps,
                                            key=lambda item: item["from_slot"])})
        if gaps:
            publish_overwrite(args.receipt, receipt)
        else:
            publish_txn(out_path, RawBytes(data_bytes), args.receipt, receipt)
            if partial.exists():
                partial.unlink()
            if __import__("hashlib").sha256(out_path.read_bytes()).hexdigest() != published["sha256"]:
                raise RuntimeError("联合发布后独立读者哈希不一致")
        if backup and backup.exists():
            backup.unlink()
        print(f"{verdict} {len(segs)} segs ({len(gaps)} gaps) in {time.time()-t0:.0f}s"
              f" -> {out_path if not gaps else partial}", flush=True)
        return exit_code
    except Exception as exc:
        if not outf.closed:
            outf.close()
        # 数据与完成 receipt 是一个发布事务：receipt 落盘失败时撤回本次正式文件。
        if published_current and out_path.exists():
            os.replace(out_path, partial)
        if backup and backup.exists():
            os.replace(backup, out_path)
        _publish_error(args.receipt, base_envelope, exc, run_id)
        print(f"[window_fetch] 检测/提交失败（exit 1）: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
