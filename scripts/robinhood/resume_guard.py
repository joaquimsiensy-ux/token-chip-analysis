"""Identity-bound, overlap-safe resume helpers for Robinhood collectors."""
import gzip
import hashlib
import json
import os


def bind_output(path, identity):
    meta_path = path + ".meta.json"
    expected = {"schema": "robinhood-collector-cache/v2", **identity}
    if os.path.exists(path) and os.path.getsize(path):
        if not os.path.exists(meta_path) or json.load(open(meta_path)) != expected:
            raise SystemExit(f"[fail-closed] {path} 缓存未绑定当前 token/query/config")
    else:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(meta_path, "w") as f:
            json.dump(expected, f, sort_keys=True, indent=2)


def overlap_state(path, key_fields):
    if not os.path.exists(path) or not os.path.getsize(path):
        return 0, set(), 0
    last_block, count, rows = None, 0, []
    with gzip.open(path, "rt") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            count += 1
            block = int(row["block"])
            if last_block is None or block > last_block:
                last_block, rows = block, [row]
            elif block == last_block:
                rows.append(row)
    keys = {tuple(r.get(k) for k in key_fields) for r in rows}
    return (last_block or 0), keys, count


def require_progress(current, next_block, archive_height):
    if next_block is None or int(next_block) <= int(current):
        raise RuntimeError(f"next_block missing/stalled: current={current} next={next_block}")
    return bool(archive_height and int(next_block) >= int(archive_height))


def require_fetch_success(ok, data):
    if not ok:
        raise RuntimeError("network/API failure is not an empty result")
    return data


def write_receipt(path, identity, archive_height, next_block, rows):
    out_hash = hashlib.sha256(open(path, "rb").read()).hexdigest()
    with open(path + ".done.json", "w") as f:
        json.dump({"schema": "robinhood-collector-done/v2", **identity,
                   "archive_height": archive_height, "next_block": next_block,
                   "rows": rows, "output_sha256": out_hash, "complete": True},
                  f, sort_keys=True, indent=2)
