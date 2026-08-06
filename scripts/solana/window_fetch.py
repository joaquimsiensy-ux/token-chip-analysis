"""SQD 定向窗口拉取:小段(2000 slot)+并发,专攻高密度期(发射窗/事件日)。

用法: python3 window_fetch.py <from_slot> <to_slot> <out.jsonl> --receipt <receipt.json> [--conc 8]
输出: 每行 [ts, slot, from_owner, to_owner, amount_raw](与 fetch_sqd_transfers_v2.py 边格式兼容)
     失败段写入 <out>.gaps.json；gaps 非空只留 <out>.partial 并 exit 2。
"""
import argparse, hashlib, json, os, subprocess, sys, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SQD = "https://portal.sqd.dev/datasets/solana-mainnet/stream"
MINT = json.loads(Path("config.json").read_text())["mint"]
ZERO = "0x" + "0" * 40
CHUNK = 2000


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


def scan_seg(frm, to):
    """扫一段,返回 (edges, ok)。内部按 portal 游标推进,直到覆盖整段。"""
    edges, cur, fails = [], frm, 0
    while cur <= to:
        body = {"type": "solana", "fromBlock": cur, "toBlock": to,
                "fields": {"block": {"number": True, "timestamp": True},
                           "transaction": {"transactionIndex": True, "err": True},
                           "tokenBalance": {"transactionIndex": True, "preOwner": True,
                                            "postOwner": True, "preAmount": True, "postAmount": True}},
                "tokenBalances": [{"postMint": [MINT], "transaction": True},
                                  {"preMint": [MINT], "transaction": True}]}
        try:
            p = subprocess.run(["curl", "-s", "-m", "60", "-X", "POST", SQD,
                                "-H", "Content-Type: application/json", "-d", json.dumps(body)],
                               capture_output=True, text=True, timeout=75)
            raw = p.stdout
        except Exception:
            raw = ""
        last = None
        for ln in raw.strip().split("\n"):
            if not ln:
                continue
            try:
                b = json.loads(ln)
            except ValueError:
                break  # 截断行:按已解析部分推进
            hdr = b.get("header", {})
            last = hdr.get("number", last)
            tbs = b.get("tokenBalances") or []
            if not tbs:
                continue
            ts = hdr.get("timestamp") or 0
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
                    edges.append((ts, hdr["number"], f, t, amt))
        if last is None:
            fails += 1
            if fails > 5:
                return edges, False
            time.sleep(2 * fails)
            continue
        fails = 0
        cur = last + 1
    return edges, True


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
    ap.add_argument("frm", type=int)
    ap.add_argument("to", type=int)
    ap.add_argument("out")
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--receipt", required=True)
    args = ap.parse_args(argv)

    segs = []
    s = args.frm
    while s <= args.to:
        segs.append((s, min(s + CHUNK - 1, args.to)))
        s += CHUNK
    print(f"segments: {len(segs)} x {CHUNK} slots, conc={args.conc}", flush=True)

    t0 = time.time()
    done = [0]
    gaps = []
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partial = Path(str(out_path) + ".partial")
    outf = partial.open("w", encoding="utf-8")
    backup = None
    lock = __import__("threading").Lock()

    def work(seg):
        e, ok = scan_seg(seg[0], seg[1])
        with lock:
            for row in e:
                outf.write(json.dumps(list(row), separators=(",", ":")) + "\n")
            if not ok:
                gaps.append(seg)
            done[0] += 1
            if done[0] % 20 == 0:
                print(f"{done[0]}/{len(segs)} segs, {time.time()-t0:.0f}s", flush=True)

    try:
        with ThreadPoolExecutor(args.conc) as ex:
            list(ex.map(work, segs))
        outf.flush(); os.fsync(outf.fileno()); outf.close()
        gaps_path = Path(str(out_path) + ".gaps.json")
        gaps_path.write_text(json.dumps(gaps), encoding="utf-8")
        if gaps:
            verdict, exit_code = "FAIL", 2
            published = None
        else:
            if out_path.exists():
                backup = out_path.with_name(f".{out_path.name}.previous.{os.getpid()}")
                os.replace(out_path, backup)
            os.replace(partial, out_path)
            verdict, exit_code = "PASS", 0
            published = {"path": str(out_path), "size": out_path.stat().st_size,
                         "sha256": _sha256(out_path)}
        receipt = {
            "schema": "solana-window-fetch-receipt/v2",
            "target": {"chain": "solana", "token": MINT, "as_of_block": args.to},
            "range": {"from_slot": args.frm, "to_slot": args.to,
                      "chunk_size": CHUNK, "segments": len(segs)},
            "coverage": {"completed_segments": len(segs) - len(gaps),
                         "gap_segments": len(gaps), "gaps": gaps},
            "output": published or {"path": str(partial), "size": partial.stat().st_size,
                                     "sha256": _sha256(partial), "partial": True},
            "verdict": verdict, "exit_code": exit_code,
        }
        _atomic_json(args.receipt, receipt)
        if backup and backup.exists():
            backup.unlink()
        print(f"{verdict} {len(segs)} segs ({len(gaps)} gaps) in {time.time()-t0:.0f}s"
              f" -> {out_path if not gaps else partial}", flush=True)
        return exit_code
    except Exception as exc:
        if not outf.closed:
            outf.close()
        # 数据与完成 receipt 是一个发布事务：receipt 落盘失败时撤回本次正式文件。
        if not gaps and out_path.exists():
            os.replace(out_path, partial)
        if backup and backup.exists():
            os.replace(backup, out_path)
        print(f"[window_fetch] 检测/提交失败（exit 1）: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
