#!/usr/bin/env python3
"""envio HyperSync 全量/补拉 ERC20 转账事件，输出 CSV 与 fetch_alchemy.py 的 transfers_full.csv 同构。
来源：SIREN(BSC) 2026-07 实战产物；v3.5 参数化+断点续传（ASTEROID(ETH) 2026-07-18 收编）。

用法：python3 fetch_hypersync.py <from_block> --token-file ~/.config/hypersync/token \
        --url https://eth.hypersync.xyz/query --token-addr 0x标的 --out data/transfers_full.csv
  - token：显式 --token-file > HYPERSYNC_TOKEN > ~/.config/hypersync/token；禁止位置参数明文传入
  - from_block：起始块（部署块起；断点续传时自动改用已有 CSV 末行块）
  - --url 换链改子域（bsc/eth/base…）；--sleep 请求间隔，按账号档位选：
      免费层 0.5s（2026-07-18 起限流收紧后的实测稳值；ETH 低峰可试 0.25s）
      Starter 付费档 0.12s（≈500rpm 爆发上限；单进程即吃满，勿再多进程同 key 并发）
      （Starter=100rpm 基础+overage 爆发，超量按请求计费，token 设置里需开 overage ceiling 5x）
断点续传：--out 已存在且非空时自动从末行块续拉（重叠由下游按 uniqueId 去重）；
  老 7 列 CSV 续拉时自动维持 7 列，新文件起手为 8 列（尾列 block_hash，供防重组去重键）。
"""
import requests, json, csv, os, sys, time, datetime, argparse, shutil
from pathlib import Path

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
DEFAULT_TOKEN_FILE = "~/.config/hypersync/token"


class SafeParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed, extras = self.parse_known_args(args, namespace)
        if extras:
            self.error("存在未识别参数（输入值已隐去）")
        return parsed


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("须为整数（输入值已隐去）") from None

def _load_token(ap, token_file):
    if token_file is not None:
        path = os.path.expanduser(token_file)
    else:
        env_token = os.environ.get("HYPERSYNC_TOKEN", "").strip()
        if env_token:
            return env_token
        path = os.path.expanduser(DEFAULT_TOKEN_FILE)
    try:
        token = Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        token = ""
    if not token:
        ap.error("HyperSync token 文件缺失或为空（路径已隐去）；"
                 "默认路径 ~/.config/hypersync/token，或设 HYPERSYNC_TOKEN")
    return token


def parse_args(argv=None):
    ap = SafeParser()
    ap.add_argument("from_block", type=_safe_int)
    ap.add_argument("--token-file", default=None,
                    help="token 文件；显式给出时优先于 HYPERSYNC_TOKEN")
    ap.add_argument("--url", default="https://bsc.hypersync.xyz/query")
    ap.add_argument("--token-addr", required=True)
    ap.add_argument("--out", default="data/transfers_full.csv")
    ap.add_argument("--to-block", type=int,
                    help="可选排他上界；需生成正式 collector receipt 时建议显式给出")
    ap.add_argument("--receipt",
                    help="采集完成后原子写 evm-collector-run/v2；正式采集必须显式给 --to-block")
    ap.add_argument("--resume-receipt",
                    help="正式续段必填：上一张 v2 receipt；先重验现有 CSV 全前缀再延伸")
    ap.add_argument("--sleep", type=float, default=0.25)
    a = ap.parse_args(argv)
    a.token = _load_token(ap, a.token_file)
    a._parser = ap
    if a.receipt and a.to_block is None:
        ap.error("正式 collector receipt 必须显式给 --to-block；动态 archive tip 不可作为冻结上界")
    if a.from_block < 0 or (a.to_block is not None
                            and (a.to_block < 0 or a.from_block >= a.to_block)):
        ap.error("块区间必须满足 0 <= from_block < to_block")
    return a


def main():
    a = parse_args()
    ap = a._parser
    headers = {"Authorization": f"Bearer {a.token}", "Content-Type": "application/json"}
    resume, mode, with_bh, prior_segments = a.from_block, "w", True, []
    out_path = Path(a.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp.{os.getpid()}")
    exists_nonempty = out_path.exists() and out_path.stat().st_size > 0
    if a.receipt and exists_nonempty:
        if not a.resume_receipt:
            ap.error("正式输出已有前缀但缺 --resume-receipt；存量 legacy CSV 必须另名归档后从冻结下界重采")
        try:
            from channels_preflight import _csv_collector_provenance
            prev = json.loads(Path(a.resume_receipt).read_text(encoding="utf-8"))
            pq = prev.get("query") or {}
            if pq.get("requested_from") != a.from_block or pq.get("requested_to") >= a.to_block:
                raise ValueError("前驱 receipt 起点不同或新上界未前移")
            _csv_collector_provenance(a.resume_receipt, out_path, a.token_addr,
                                      a.from_block, pq["requested_to"])
            resume, mode = pq["requested_to"], "a"
            prior_segments = list(prev["segments"])
            with open(out_path, encoding="utf-8") as fh:
                with_bh = "block_hash" in fh.readline()
        except Exception as exc:
            ap.error(f"正式续段前驱重验失败: {exc}")
    elif a.receipt and a.resume_receipt:
        ap.error("--resume-receipt 只能与现有非空正式 CSV 一起使用")
    elif not a.receipt and exists_nonempty:
        with open(out_path) as fh:
            with_bh = "block_hash" in fh.readline()
        with open(out_path, "rb") as fh:
            try: fh.seek(-4096, os.SEEK_END)
            except OSError: fh.seek(0)
            tail = fh.read().decode(errors="ignore").strip().splitlines()
            last = tail[-1].split(",")
            if last and last[0].isdigit():
                resume, mode = int(last[0]), "a"
                print(f"[legacy resume] 从已有 CSV 末行块 {resume} 续拉；该文件不能取得正式 receipt", flush=True)
    if mode == "a":
        shutil.copyfile(out_path, tmp_path)
    f = open(tmp_path, "a" if mode == "a" else "x", newline="")
    w = csv.writer(f)
    if mode == "w":
        w.writerow(["block", "ts", "tx", "from", "to", "value_raw", "uniqueId", "block_hash"])
        f.flush(); os.fsync(f.fileno())
    segment_from = resume
    total, cur, t0, e429 = 0, resume, time.time(), 0
    while True:
        q = {"from_block": cur,
             "logs": [{"address": [a.token_addr], "topics": [[TRANSFER]]}],
             "field_selection": {
                 "log": ["block_number", "block_hash", "log_index", "transaction_hash", "topic1", "topic2", "data"],
                 "block": ["number", "timestamp"]}}
        if a.to_block is not None:
            q["to_block"] = a.to_block
        ok = False
        for attempt in range(12):
            try:
                r = requests.post(a.url, json=q, headers=headers, timeout=90)
                if r.status_code == 200:
                    j = r.json(); ok = True; break
                if r.status_code == 429:
                    e429 += 1
                print(f"[http {r.status_code}] {r.text[:120]}", flush=True)
                time.sleep(min(3 * (attempt + 1), 30))
            except Exception as e:
                print(f"[exc] {str(e)[:100]}", flush=True)
                time.sleep(min(3 * (attempt + 1), 30))
        if not ok:
            print("[fatal] giving up", flush=True)
            f.close(); tmp_path.unlink(missing_ok=True); return 2
        bts, n = {}, 0
        for batch in j.get("data", []):
            for b in batch.get("blocks", []):
                ts = b.get("timestamp")
                bts[int(b["number"])] = int(ts, 16) if isinstance(ts, str) else int(ts)
            for lg in batch.get("logs", []):
                bn = int(lg["block_number"])
                ts = bts.get(bn)
                iso = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z") if ts else ""
                frm = "0x" + lg["topic1"][-40:]
                to = "0x" + lg["topic2"][-40:]
                data = lg.get("data") or "0x0"
                val = int(data, 16) if data not in ("0x", "") else 0
                li = int(lg["log_index"])
                row = [bn, iso, lg["transaction_hash"], frm, to, val,
                       f"{lg['transaction_hash']}:log:{li}"]
                if with_bh:
                    row.append(lg.get("block_hash") or "")
                w.writerow(row)
                n += 1
        total += n
        nxt, ah = j.get("next_block"), j.get("archive_height")
        if total % 50000 < n or n == 0:
            print(f"[prog] +{n} total {total} next {nxt} height {ah} 429s {e429} {time.time()-t0:.0f}s", flush=True)
        target = a.to_block if a.to_block is not None else ah
        if isinstance(nxt, bool) or not isinstance(nxt, int):
            f.close(); tmp_path.unlink(missing_ok=True)
            print("[fatal] provider 缺整数 next_block，部分响应不得签完成", flush=True)
            return 2
        if nxt <= cur:
            f.close(); tmp_path.unlink(missing_ok=True)
            print(f"[fatal] provider cursor 未前进: current={cur} next={nxt}", flush=True)
            return 2
        if target is None:
            f.close(); tmp_path.unlink(missing_ok=True)
            print("[fatal] provider 未返回 archive_height，无法冻结采集上界", flush=True)
            return 2
        if nxt >= target:
            break
        cur = nxt
        time.sleep(a.sleep)
    f.flush(); os.fsync(f.fileno()); f.close()
    receipt_stage = None
    if a.receipt:
        from channels_preflight import _csv_stats, _sha256_file
        out = os.path.realpath(os.path.abspath(a.out))
        rows, min_block, max_block = _csv_stats(tmp_path)
        collector = os.path.realpath(os.path.abspath(__file__))
        segment = {"requested_from": int(segment_from), "requested_to": int(a.to_block),
                   "provider_next_block": int(nxt),
                   "output_prefix": {"size": tmp_path.stat().st_size,
                                     "sha256": _sha256_file(tmp_path)}}
        payload = {"schema": "evm-collector-run/v2", "status": "PASS",
                   "producer": "fetch_hypersync.py/v3",
                   "collector": {"path": "fetch_hypersync.py",
                                 "sha256": _sha256_file(Path(collector))},
                   "query": {"token": a.token_addr.lower(),
                             "query_schema": "erc20-transfer-fields/v2",
                             "provider_url": a.url, "requested_from": a.from_block,
                             "requested_to": int(a.to_block)},
                   "completion": {"reason": "requested_bound_reached",
                                  "next_block": int(nxt)},
                   "segments": prior_segments + [segment],
                   "output": {"path": out, "size": tmp_path.stat().st_size,
                              "sha256": _sha256_file(tmp_path), "rows": rows,
                              "min_block": min_block, "max_block": max_block}}
        rp = Path(a.receipt).resolve()
        rp.parent.mkdir(parents=True, exist_ok=True)
        tmp = rp.with_name(f".{rp.name}.tmp.{os.getpid()}")
        with tmp.open("x", encoding="utf-8") as rf:
            json.dump(payload, rf, ensure_ascii=False, indent=2)
            rf.flush(); os.fsync(rf.fileno())
        receipt_stage = (tmp, rp)
    backup = None
    try:
        if out_path.exists():
            backup = out_path.with_name(f".{out_path.name}.previous.{os.getpid()}")
            os.replace(out_path, backup)
        os.replace(tmp_path, out_path)
        if receipt_stage:
            os.replace(receipt_stage[0], receipt_stage[1])
        if backup and backup.exists():
            backup.unlink()
    except Exception as exc:
        # CSV 与 receipt 是同一发布事务；任一提交失败都恢复旧正式前缀。
        if out_path.exists():
            if backup and backup.exists():
                out_path.unlink()
            else:
                os.replace(out_path, tmp_path)
        if backup and backup.exists():
            os.replace(backup, out_path)
        if receipt_stage and receipt_stage[0].exists():
            receipt_stage[0].unlink()
        tmp_path.unlink(missing_ok=True)
        print(f"[fatal] collector 原子提交失败: {exc}", flush=True)
        return 1
    print(f"[COMPLETE] {total} transfers this run, tip {ah}, 429s {e429}, {time.time()-t0:.0f}s", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
