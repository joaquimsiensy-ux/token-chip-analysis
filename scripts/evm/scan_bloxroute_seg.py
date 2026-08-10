#!/usr/bin/env python3
"""bloXroute 免注册 getLogs 段扫描器（共享 attested session，替代旧 curl 线程池）。

为什么单独一件：scan_transfers.py 的 subprocess(curl)×8 线程池在本机实测挂死零产出；
本件用共享 net.py session + 低并发（默认 3 线程 0.4s 间隔）。适用场景=近期段快扫
（bloXroute 历史窗口动态、约 55-60 天，用前先二分探测边界；旧段用 HyperSync）。
输出 7 列与 replay_pass1 直用（ts 留空，后用锚点插值补）。

用法：python3 scan_bloxroute_seg.py --chain bsc --token 0x.. --lo <块> --hi <块> --out data/seg.csv \
        [--workers 3] [--sleep 0.4] [--step 10000]
断点续传：--out 存在且 <out>.done.json 有已完成段清单时自动跳过。
（来源：SIREN(BSC) 分析实战产物，2026-07-19；bloXroute 并发/窗口实测见 data-pipeline-evm.md §1）"""
import json, csv, time, threading, queue, os, argparse, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from chain_registry import attested_evm_chains
from net import RpcAttestationError, attested_rpc_pool

TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
URL = "https://bsc.rpc.blxrbdn.com"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True)
    ap.add_argument("--lo", type=int, required=True)
    ap.add_argument("--hi", type=int, required=True, help="不含上界 [lo,hi)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default=URL)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--step", type=int, default=10000)
    ap.add_argument("--chain", default="bsc",
                    choices=sorted(attested_evm_chains()),
                    help="目标链（默认 bsc；chain id 只读 chain_registry）")
    a = ap.parse_args()
    pool = attested_rpc_pool(a.url, a.chain, formal=True, rps=max(1, a.workers),
                             concurrency=max(1, a.workers))
    try:
        pool.attest()
    except RpcAttestationError as exc:
        print(f"[fatal] RPC chain attestation failed: {exc}", file=sys.stderr)
        return 1
    token = a.token.lower()
    done_f = a.out + ".done.json"
    done = set(json.load(open(done_f))) if os.path.exists(done_f) else set()
    segs = [b for b in range(a.lo, a.hi, a.step) if b not in done]
    q = queue.Queue()
    for s in segs:
        q.put(s)
    lock = threading.Lock()
    mode = "a" if os.path.exists(a.out) and os.path.getsize(a.out) > 10 else "w"
    f = open(a.out, mode, newline="")
    w = csv.writer(f)
    if mode == "w":
        w.writerow(["block", "ts", "tx", "from", "to", "value", "uniqueId"])
    fails = []

    def worker():
        while True:
            try:
                seg = q.get_nowait()
            except queue.Empty:
                return
            hi = min(seg + a.step - 1, a.hi - 1)
            ok = False
            for att in range(5):
                try:
                    result = pool.call("eth_getLogs", [{"fromBlock": hex(seg),
                                                        "toBlock": hex(hi),
                                                        "address": token,
                                                        "topics": [[TOPIC]]}])
                    logs = result.get("result") if result.get("ok") else None
                    if isinstance(logs, list):
                        rows = []
                        for lg in logs:
                            tx = lg["transactionHash"]
                            li = int(lg["logIndex"], 16)
                            data = lg.get("data") or "0x0"
                            val = int(data, 16) if data not in ("0x", "") else 0
                            rows.append([int(lg["blockNumber"], 16), "", tx,
                                         "0x" + lg["topics"][1][-40:], "0x" + lg["topics"][2][-40:],
                                         val, f"{tx}:log:{li}"])
                        with lock:
                            w.writerows(rows)
                            f.flush()
                            done.add(seg)
                            if len(done) % 50 == 0:
                                json.dump(sorted(done), open(done_f, "w"))
                                print(f"[prog] {len(done)}/{len(segs)} segs", flush=True)
                        ok = True
                        break
                    time.sleep(2 * (att + 1))
                except Exception:
                    time.sleep(2 * (att + 1))
            if not ok:
                with lock:
                    fails.append(seg)
            time.sleep(a.sleep)

    ths = [threading.Thread(target=worker) for _ in range(a.workers)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    json.dump(sorted(done), open(done_f, "w"))
    f.close()
    print(f"DONE segs={len(done)} fails={fails[:20]}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
