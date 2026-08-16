#!/usr/bin/env python3
"""SQD Portal EVM 薄采集器（免 key 免注册；v3.11.2 定位=HyperSync 故障预案 + 数仓准入期对照源,平时不跑）。

用法: python3 fetch_sqd_evm.py <chain|dataset> <from_block> --token-addr 0x标的 \
        --out data/sqd.csv [--to-block N] [--sleep 0.5]
  - chain 快捷名: bsc/eth/base/arbitrum（其余直接传数据集名,如 optimism-mainnet）
  - 公共端点限流约 20 请求/10 秒 —— sleep 默认 0.5s,别调低
  - 断点续传: --out 已存在时从末行块+1 续拉
输出: 标准 8 列 CSV(block,ts,tx,log_index,from,to,value_raw,block_hash),
  transfers_lib.iter_transfers 直读,可与 HyperSync 产物 merge_sources 对账合并。
（来源：v3.11.2 采集加速工程,2026-07-21;响应结构按当日实测:header{number,timestamp,hash},
  log{logIndex(str),transactionHash,data,topics[]},NDJSON 每行一块,响应按大小截断需续请求）"""
import argparse, csv, json, os, re, sys, time

import requests

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
DATASETS = {"bsc": "binance-mainnet", "eth": "ethereum-mainnet",
            "base": "base-mainnet", "arbitrum": "arbitrum-one"}


def _safe_int(value, field):
    if isinstance(value, bool):
        raise ValueError(f"SQD stream row has invalid {field}")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        return int(value)
    raise ValueError(f"SQD stream row has invalid {field}")


def parse_stream_response(text, req_from, req_to):
    """Parse one SQD NDJSON response and return CSV rows plus provider frontier."""
    import datetime as dt

    if not text or not text.strip():
        return [], None
    rows = []
    provider_last = None
    for line in text.splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if not isinstance(d, dict):
            raise ValueError("SQD stream row must be a JSON object")
        h = d.get("header")
        if not isinstance(h, dict) or "number" not in h:
            raise ValueError("SQD stream row missing valid header.number")
        if isinstance(h["number"], bool) or not isinstance(h["number"], int):
            raise ValueError("SQD stream row has invalid header.number")
        bn = h["number"]
        if bn < req_from or bn > req_to:
            raise ValueError("SQD stream row header.number escapes requested interval")
        provider_last = bn
        if "timestamp" in h:
            timestamp = _safe_int(h["timestamp"], "header.timestamp")
            try:
                iso = dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
            except (OverflowError, OSError, ValueError) as exc:
                raise ValueError("SQD stream row has invalid header.timestamp") from exc
        else:
            iso = ""
        bh = h.get("hash") or ""
        logs = d.get("logs", [])
        if not isinstance(logs, list):
            raise ValueError("SQD stream row logs must be a list")
        for index, lg in enumerate(logs):
            if not isinstance(lg, dict):
                raise ValueError(f"SQD stream log[{index}] must be a JSON object")
            topics = lg.get("topics")
            if not isinstance(topics, list) or len(topics) < 3 \
                    or any(not isinstance(topic, str)
                           or re.fullmatch(r"0x[0-9a-fA-F]{64}", topic) is None
                           for topic in topics):
                raise ValueError(f"SQD stream log[{index}] has invalid topics")
            # data 长度不设限（2026-08-16 用户裁决 G3R2-01，r10_ledger 状态节）：兼容
            # 非标 ERC20 优先；代价=截断后仍为偶数位合法 hex 时此层抓不住、金额量级
            # 静默变小，兜底依赖 A2 供给对账闸。标准 Transfer 应为 0x+64 hex。
            data = lg.get("data")
            if not isinstance(data, str) \
                    or re.fullmatch(r"0x(?:[0-9a-fA-F]*)", data) is None:
                raise ValueError(f"SQD stream log[{index}] has invalid data")
            tx_hash = lg.get("transactionHash")
            if not isinstance(tx_hash, str) \
                    or re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash) is None:
                raise ValueError(f"SQD stream log[{index}] has invalid transactionHash")
            log_index = _safe_int(lg.get("logIndex"), f"log[{index}].logIndex")
            frm = "0x" + topics[1][-40:].lower()
            to = "0x" + topics[2][-40:].lower()
            val = int(data, 16) if data != "0x" else 0
            rows.append([bn, iso, tx_hash, log_index,
                         frm, to, val, bh])
    return rows, provider_last


def _quarantine_new_output(path):
    if not os.path.lexists(path):
        return None
    candidate = path + ".partial"
    suffix = 1
    while os.path.lexists(candidate):
        candidate = f"{path}.{suffix}.partial"
        suffix += 1
    os.rename(path, candidate)
    return candidate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chain")
    ap.add_argument("from_block", type=int)
    ap.add_argument("--token-addr", required=True)
    ap.add_argument("--out", default="data/sqd.csv")
    ap.add_argument("--to-block", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--receipt", help="成功收尾后写正式 evm-collector-run/v2（须显式 --to-block）")
    a = ap.parse_args()
    explicit_to = a.to_block is not None
    if a.receipt:
        if not explicit_to:
            ap.error("正式 SQD receipt 要求显式 --to-block")
        if os.path.lexists(a.out) or os.path.lexists(a.receipt):
            ap.error("正式 SQD receipt 要求输出与 receipt 路径运行前均不存在")
        if os.path.realpath(a.out) == os.path.realpath(a.receipt):
            ap.error("正式 SQD receipt 的输出与 receipt 路径不得相同")
    existed_before = os.path.exists(a.out) and os.path.getsize(a.out) > 0
    ds = DATASETS.get(a.chain, a.chain)
    base = f"https://portal.sqd.dev/datasets/{ds}"
    token = a.token_addr.lower()

    if a.to_block is None:
        r = requests.get(f"{base}/finalized-head", timeout=30)
        a.to_block = int(r.json()["number"])

    resume, mode = a.from_block, "w"
    if os.path.exists(a.out) and os.path.getsize(a.out) > 100:
        with open(a.out, "rb") as fh:
            try:
                fh.seek(-4096, os.SEEK_END)
            except OSError:
                fh.seek(0)
            tail = fh.read().decode(errors="ignore").strip().splitlines()
            last = tail[-1].split(",")
            if last and last[0].isdigit():
                resume, mode = int(last[0]) + 1, "a"
                print(f"[resume] 从块 {resume} 续拉", flush=True)

    f = None
    opened = False
    success = False
    try:
        f = open(a.out, mode, newline="")
        opened = True
        w = csv.writer(f)
        if mode == "w":
            w.writerow(["block", "ts", "tx", "log_index", "from", "to", "value_raw", "block_hash"])

        total, cur, t0, errs = 0, resume, time.time(), 0
        provider_frontier = None
        sess = requests.Session()
        while cur <= a.to_block:
            body = {"type": "evm", "fromBlock": cur, "toBlock": a.to_block,
                    "fields": {"block": {"number": True, "timestamp": True, "hash": True},
                               "log": {"logIndex": True, "transactionHash": True,
                                       "topics": True, "data": True}},
                    "logs": [{"address": [token], "topic0": [TRANSFER]}]}
            try:
                r = sess.post(f"{base}/stream", json=body, timeout=180)
            except Exception as e:
                errs += 1
                print(f"[exc] {str(e)[:100]}", flush=True)
                if errs >= 5:
                    print("[fatal] SQD transport anomalies reached 5 consecutive attempts", flush=True)
                    sys.exit(3)
                time.sleep(min(2 * errs, 60))
                continue
            if r.status_code == 429:
                time.sleep(5)
                continue
            if r.status_code != 200:
                errs += 1
                print(f"[http {r.status_code}] {r.text[:120]}", flush=True)
                if errs >= 5:
                    print("[fatal] SQD HTTP/protocol anomalies reached 5 consecutive attempts", flush=True)
                    sys.exit(3)
                time.sleep(min(2 * errs, 60))
                continue
            try:
                rows, provider_last = parse_stream_response(r.text, cur, a.to_block)
            except ValueError as exc:
                errs += 1
                print(f"[protocol] {str(exc)[:120]}", flush=True)
                if errs >= 5:
                    print("[fatal] SQD HTTP/protocol anomalies reached 5 consecutive attempts", flush=True)
                    sys.exit(3)
                time.sleep(min(2 * errs, 60))
                continue
            if provider_last is None:
                errs += 1
                print(f"[protocol] empty SQD response; retry {errs}/5 without cursor advance", flush=True)
                if errs >= 5:
                    print("[fatal] empty SQD response persisted for 5 consecutive attempts", flush=True)
                    sys.exit(3)
                time.sleep(min(2 * errs, 60))
                continue
            if provider_last < cur:
                errs += 1
                print(f"[protocol] SQD frontier {provider_last} regressed below request {cur}", flush=True)
                if errs >= 5:
                    print("[fatal] SQD frontier regressed for 5 consecutive attempts", flush=True)
                    sys.exit(3)
                time.sleep(min(2 * errs, 60))
                continue
            errs = 0
            for row in rows:
                w.writerow(row)
            n = len(rows)
            total += n
            f.flush()
            provider_frontier = (provider_last if provider_frontier is None
                                 else max(provider_frontier, provider_last))
            if total and total % 20000 < n:
                el = time.time() - t0
                print(f"[prog] +{n} total {total} block {provider_last}/{a.to_block} "
                      f"{total/el:.0f}/s {el:.0f}s", flush=True)
            if provider_last >= a.to_block:
                break
            cur = provider_last + 1
            time.sleep(a.sleep)
        if provider_frontier is None or provider_frontier < a.to_block:
            print("[fatal] SQD provider frontier did not reach requested upper bound", flush=True)
            sys.exit(3)
        f.close()
        if a.receipt:
            from csv_collector_receipt import emit_native_receipt
            emit_native_receipt(a.out, a.receipt, __file__, token, base, a.from_block,
                                a.to_block + 1, provider_frontier + 1,
                                fresh_output=not existed_before)
        print(f"[COMPLETE] {total} rows -> {a.out}, [{resume},{a.to_block}] "
              f"{time.time()-t0:.0f}s", flush=True)
        success = True
    finally:
        if f is not None and not f.closed:
            f.close()
        if opened and not success:
            if mode == "w":
                partial = _quarantine_new_output(a.out)
                if partial:
                    print(f"[warning] incomplete SQD output moved to {partial}", flush=True)
            else:
                print("[warning] incomplete SQD resume left existing output in place", flush=True)


if __name__ == "__main__":
    main()
