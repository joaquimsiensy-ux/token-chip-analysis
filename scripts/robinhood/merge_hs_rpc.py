#!/usr/bin/env python3
"""Fail-closed merge of HyperSync gzip and RPC tail; source is read-only."""
import argparse
import bisect
import gzip
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_gzip_complete(path):
    rows = []
    try:
        with gzip.open(path, "rt") as f:
            for n, line in enumerate(f, 1):
                try:
                    rows.append(json.loads(line))
                except Exception as exc:
                    raise SystemExit(f"[fail-closed] {path}:{n} invalid JSON: {exc}")
    except (EOFError, gzip.BadGzipFile, OSError) as exc:
        raise SystemExit(f"[fail-closed] gzip integrity failure; source preserved: {exc}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/transfers.jsonl.gz")
    ap.add_argument("--rpc", default="data/transfers_rpc.jsonl")
    ap.add_argument("--anchors", default="data/ts_anchors.json")
    ap.add_argument("--output", default="data/transfers_merged.jsonl.gz")
    ap.add_argument("--promote", action="store_true",
                    help="after full verification, atomically replace --input with --output")
    a = ap.parse_args()
    if os.path.realpath(a.input) == os.path.realpath(a.output):
        raise SystemExit("[fail-closed] --output must differ from read-only --input")

    source_hash = sha256(a.input)
    rows = load_gzip_complete(a.input)
    seen = set()
    for r in rows:
        key = (r["block"], r["logi"])
        if key in seen:
            raise SystemExit(f"[fail-closed] duplicate key in HyperSync source: {key}")
        seen.add(key)
    hs_max = max((r["block"] for r in rows), default=None)

    anchors = json.load(open(a.anchors))
    blocks = sorted(int(k) for k in anchors)
    if not blocks:
        raise SystemExit("[fail-closed] empty timestamp anchors")

    def interp(block):
        i = bisect.bisect_left(blocks, block)
        if i == 0:
            return anchors[str(blocks[0])]
        if i >= len(blocks):
            return anchors[str(blocks[-1])]
        b0, b1 = blocks[i - 1], blocks[i]
        t0, t1 = anchors[str(b0)], anchors[str(b1)]
        return t0 + (t1 - t0) * (block - b0) / (b1 - b0) if b1 > b0 else t0

    n_rpc = 0
    with open(a.rpc) as f:
        for n, line in enumerate(f, 1):
            try:
                r = json.loads(line)
            except Exception as exc:
                raise SystemExit(f"[fail-closed] {a.rpc}:{n} invalid JSON: {exc}")
            key = (r["block"], r["logi"])
            if key in seen:
                continue
            r["ts"] = datetime.fromtimestamp(interp(r["block"]), timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ")
            seen.add(key)
            rows.append(r)
            n_rpc += 1
    rows.sort(key=lambda r: (r["block"], r["logi"]))
    if any(not r.get("ts") for r in rows):
        raise SystemExit("[fail-closed] merged rows contain missing timestamps")

    tmp = a.output + ".tmp"
    with gzip.open(tmp, "wt") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    verified = load_gzip_complete(tmp)
    if len(verified) != len(rows):
        raise SystemExit("[fail-closed] output row-count verification failed")
    os.replace(tmp, a.output)
    out_hash = sha256(a.output)
    if a.promote:
        os.replace(a.output, a.input)
    print(json.dumps({"source_sha256": source_hash, "output_sha256": out_hash,
                      "hypersync_max_block": hs_max, "rpc_added": n_rpc,
                      "rows": len(rows), "promoted": a.promote}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
