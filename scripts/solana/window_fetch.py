"""SQD 定向窗口拉取:小段(2000 slot)+并发,专攻高密度期(发射窗/事件日)。

用法: python3 window_fetch.py <from_slot> <to_slot> <out.jsonl> --receipt <receipt.json> [--conc 8]
输出: 每行 [ts, slot, tx_index, -1, from_owner, to_owner, amount_raw]
     失败段写入 <out>.gaps.json；gaps 非空只留 <out>.partial 并 exit 2。
"""
import argparse, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import net
from receipt_kernel import (RawBytes, assert_distinct_paths, build_envelope,
                            finalize_envelope, publish_error_receipt, publish_exclusive,
                            publish_overwrite, publish_supersede, publish_txn)
from spl_edge_core import (EDGE_SCHEMA_FIELDS, EDGE_SEMANTICS,
                           INSTR_INDEX_TX_NET, ORDER_GRANULARITY_TX,
                           ZERO_OWNER as ZERO, owner_deltas_by_tx, pair_tx,
                           transaction_status_by_index, validate_tx_index)

SQD = "https://portal.sqd.dev/datasets/solana-mainnet/stream"
MINT = json.loads(Path("config.json").read_text())["mint"]
CHUNK = 2000
SCHEMA = "solana-window-fetch-receipt/v3"
SCHEMA_FAMILY = "solana-window-fetch-receipt/"


def scan_seg(frm, to, endpoint=SQD):
    """扫一段,返回 (edges, ok)。内部按 portal 游标推进,直到覆盖整段。"""
    edges, cur, fails, timestamps = [], frm, 0, []
    while cur <= to:
        body = {"type": "solana", "fromBlock": cur, "toBlock": to,
                "fields": {"block": {"number": True, "timestamp": True},
                           "transaction": {"transactionIndex": True, "err": True},
                           "tokenBalance": {"transactionIndex": True, "account": True,
                                            "preMint": True, "postMint": True,
                                            "preOwner": True, "postOwner": True,
                                            "preAmount": True, "postAmount": True}},
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
            errmap = transaction_status_by_index(b.get("transactions") or [])
            successful = []
            for r in tbs:
                if not isinstance(r, dict):
                    raise TypeError("tokenBalance record must be an object")
                ti = validate_tx_index(r.get("transactionIndex"))
                if ti not in errmap:
                    raise ValueError(f"tokenBalance tx_index={ti} has no transaction status")
                if errmap[ti] is None:
                    successful.append(r)
            by_tx = owner_deltas_by_tx(successful, MINT)
            for ti, delta in by_tx.items():
                for f, t, amt in pair_tx(delta):
                    page_edges.append((ts, number, ti, INSTR_INDEX_TX_NET, f, t, amt))
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


def _fsync_directory(path: Path):
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _rollback_fail_precommit(data_archive: Path | None, gaps_evidence: Path | None):
    """Undo links/files created before a FAIL receipt becomes canonical."""
    failures = []
    for path in (data_archive, gaps_evidence):
        if path is None:
            continue
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            failures.append((path, exc))
    parents = {path.parent for path in (data_archive, gaps_evidence) if path is not None}
    for parent in parents:
        try:
            _fsync_directory(parent)
        except OSError as exc:
            failures.append((parent, exc))
    if failures:
        detail = "; ".join(f"{path}: {exc}" for path, exc in failures)
        raise RuntimeError(f"FAIL receipt 发布前状态回滚失败: {detail}")


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
    gaps_evidence = Path(f"{gaps_path}.failed-{run_id}")
    try:
        assert_distinct_paths(out_path, args.receipt, partial, gaps_path, gaps_evidence)
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
    lock = __import__("threading").Lock()
    target = {"chain": "solana", "token": MINT, "as_of_block": args.to}
    base_envelope = build_envelope(SCHEMA, target, __file__, "formal")

    def work(seg):
        e, ok, timestamps = scan_seg(seg[0], seg[1], args.endpoint)
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
        if not gaps and (len(segment_timestamps) != len(segs) or any(
                item["min"] is None or item["max"] is None
                for item in segment_timestamps)):
            raise RuntimeError("complete segment 缺少 timestamp min/max 证据")
        if gaps:
            verdict, exit_code = "FAIL", 2
            publish_exclusive(gaps_evidence, gaps)
            _fsync_directory(gaps_evidence.parent)
            envelope = build_envelope(
                SCHEMA, target, __file__, "formal",
                {"output": partial, "gaps": gaps_evidence})
            published = envelope["inputs"]["output"]
        else:
            verdict, exit_code = "PASS", 0
            publish_overwrite(gaps_path, gaps)
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
            edge_contract={"schema": list(EDGE_SCHEMA_FIELDS),
                           "semantics": EDGE_SEMANTICS,
                           "order_granularity": ORDER_GRANULARITY_TX,
                           "order_exact": False,
                           "instr_index": INSTR_INDEX_TX_NET,
                           "supply_delta_source": "tokenBalances-owner-net"},
            timestamps={"segments": sorted(segment_timestamps,
                                            key=lambda item: item["from_slot"])})
        if gaps:
            data_archive = None
            old_data_stat = None
            try:
                if out_path.exists():
                    data_archive = out_path.with_name(f"{out_path.name}.stale.{run_id}")
                    if data_archive.exists():
                        raise RuntimeError(f"stale destination already exists: {data_archive}")
                    old_data_stat = out_path.stat()
                    os.link(out_path, data_archive, follow_symlinks=False)
                    _fsync_directory(out_path.parent)
                publish_supersede(
                    args.receipt, receipt, schema_family=SCHEMA_FAMILY)
            except BaseException as primary:
                try:
                    _rollback_fail_precommit(data_archive, gaps_evidence)
                except BaseException as rollback_exc:
                    raise RuntimeError(
                        f"FAIL receipt 发布失败 ({primary}); 前置状态回滚也失败: "
                        f"{rollback_exc}") from rollback_exc
                raise
            if data_archive is not None:
                current = out_path.stat()
                archived = data_archive.stat()
                identity = lambda item: (item.st_dev, item.st_ino, item.st_size,
                                         item.st_mtime_ns)
                if identity(current) != identity(old_data_stat) or identity(archived) != identity(
                        old_data_stat):
                    raise RuntimeError("旧正式 window 数据在 FAIL 提交期间发生并发变化")
                out_path.unlink()
                _fsync_directory(out_path.parent)
            # Canonical gaps is an operator-facing mirror.  The FAIL receipt
            # binds the immutable run-specific evidence above, so this update
            # cannot invalidate either the old PASS or the new FAIL receipt.
            publish_overwrite(gaps_path, gaps)
        else:
            publish_txn(out_path, RawBytes(data_bytes), args.receipt, receipt)
            try:
                partial.unlink()
            except OSError as cleanup_exc:
                # Formal data+receipt are already atomically committed.  Keep
                # PASS and report only recoverable staging-file cleanup drift.
                print(f"[window_fetch] WARN partial cleanup failed: {cleanup_exc}",
                      file=sys.stderr)
        print(f"{verdict} {len(segs)} segs ({len(gaps)} gaps) in {time.time()-t0:.0f}s"
              f" -> {out_path if not gaps else partial}", flush=True)
        return exit_code
    except Exception as exc:
        if not outf.closed:
            outf.close()
        _publish_error(args.receipt, base_envelope, exc, run_id)
        print(f"[window_fetch] 检测/提交失败（exit 1）: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
