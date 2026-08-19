#!/usr/bin/env python3
"""销户账户覆盖审计：抽查 SQD 边集是否漏掉"已 closeAccount 销户"的 token account 的转账。

原理（data-pipeline-solana.md §12）：普通 Transfer 指令不引用 mint，但一切 token account
的初始化指令（initializeAccount/2/3、ATA create）必引用 mint——所以 mint 自身签名史是
"历史账户全集"（含已销户）的独立发现源；而 getProgramAccounts 快照只见存活账户，
销户账户的中间路径是"重放 vs 快照"对账的天然盲区。本脚本从 mint 签名史抽样初始化事件
→ 判定账户存活/销户 → 对销户账户拉其自身签名史 decode 实际转账 → 逐事件对照 SQD 边集
（slot+owner 粒度）→ 覆盖率报告。来源：Helius vs SQD 通道交叉复核（codex 第二意见提议
反向审计法），2026-07-21。

用法（cd 到工作目录跑；audit 旧分析目录时用 --edges/--out 指路径）：
  python3 audit_closed_accounts.py <MINT> [--edges data/soltx-<mint小写>.jsonl.gz]
      [--mode auto|sigs|blocks] [--block-samples 15]
      [--sample-inits 60] [--deep-accounts 25] [--deep-sigs 120]
      [--max-sig-pages 600] [--interval 0.15] [--wall-min 25] [--seed 42]
      [--rpc URL] [--proxy URL|''] [--out data/closed_audit-<mint小写>.json]

样本发现两模式：sigs=mint 签名史抽样（全程边集适用；签名史从新往老翻，若边集是历史定向段
会翻不到区间）；blocks=在边集 slot 区间内均匀抽 getBlock 整块提取初始化事件（定向段正解，
免翻页）。auto=先试 sigs，3 页内未进区间自动切 blocks。

判定与退出码：事件覆盖=边集中存在 slot 相同且 from/to 含该 owner 的边（SQD 边是 owner 级
同 tx 净变动聚合，无 sig 字段，slot+owner 是可用最细粒度）；边集覆盖区间外的事件计
out_of_range 不算漏。深挖账户按结果分类（events_found / all_zero_delta=undetermined /
fetch_failed），undetermined 不算"无漏"——占比过高即样本无效（exit 1，不再只告警）。
退出码 0=抽样零漏边；2=发现漏边（对账 gate 语义）；1=运行失败/样本无效。
样本无效的机器判据（GPT-F-06 收口，任一命中→exit 1，报告 status=INVALID_SAMPLE）：
任一 getMultipleAccounts 批失败／深挖账户全部 fetch_failed／checked=0 且 closed>0／
墙钟截断／undetermined（all_zero_delta+fetch_failed）过半。
边界显式定案：closed=0（抽样内无销户账户，审计对象为空）不是查询失败——
如实报弱结论 status=NO_CLOSED_SAMPLED、exit 0，但它只证明"这批样本里没有销户账户"，
不构成"销户路径零漏"的强证明，引用时按弱结论对待。
报告 JSON 的 status 字段：CLEAN（checked>0 零漏）/ NO_CLOSED_SAMPLED（弱结论）/
LEAK_FOUND（exit 2）/ INVALID_SAMPLE（exit 1）。
"""
import argparse, gzip, json, random, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from proxy_config import resolve_proxy
from spl_edge_core import soltx_cache_paths, validate_edge_row

DEF_RPC = "https://api.mainnet-beta.solana.com"
DEF_PROXY = None
INIT_TYPES = {"initializeAccount", "initializeAccount2", "initializeAccount3"}
ATA_TYPES = {"create", "createIdempotent"}
T0 = time.time()


def log(msg):
    print(f"[audit] {msg}", file=sys.stderr, flush=True)


def bail_invalid(out_path, mint, edges_path, reason, *, legacy_sol5=False):
    """F-D8：早退路径也必须落带 status 的报告——"无报告"会让 status 契约的四态无从分辨。
    精简报告只含身份与失败原因（样本统计彼时尚不存在，不编造）。"""
    report = {"mint": mint, "edges_file": str(edges_path),
              "status": "INVALID_SAMPLE", "exit_code": 1,
              "non_formal": bool(legacy_sol5),
              "order_ambiguous": bool(legacy_sol5),
              "invalid_reasons": [reason],
              "generated": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=1))
        log(f"INVALID_SAMPLE 报告 → {out_path}")
    except OSError as exc:
        log(f"早退报告写入失败（不改变 exit 1 语义）: {exc}")
    log(reason)
    sys.exit(1)


class Rpc:
    def __init__(self, url, proxy, interval):
        self.url, self.proxy, self.interval = url, proxy, interval
        self.calls = 0

    def call(self, method, params, retries=4):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        cmd = ["curl", "-s", "-m", "30"]
        if self.proxy:
            cmd += ["-x", self.proxy]
        cmd += [self.url, "-X", "POST", "-H", "Content-Type: application/json", "-d", body]
        for i in range(retries):
            time.sleep(self.interval)
            self.calls += 1
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                d = json.loads(p.stdout)
                if "result" in d:
                    return d["result"]
            except Exception:
                pass
            time.sleep(1.5 * (i + 1))
        return None


def load_edge_index(path, *, legacy_sol5=False):
    """边集 → (owner→slot集合 索引, slot 区间)。from/to 都记（ZERO 哨兵除外）。"""
    idx, lo, hi, n = {}, None, None, 0
    with gzip.open(path, "rt") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if legacy_sol5:
                    if not isinstance(row, list) or len(row) != 5:
                        raise ValueError("legacy-sol5 必须为 5 元组，混合行宽拒绝")
                    ts, slot, frm, to, amt = row
                    if (not isinstance(ts, int) or isinstance(ts, bool) or ts < 0
                            or not isinstance(slot, int) or isinstance(slot, bool) or slot < 0
                            or not isinstance(frm, str) or not frm
                            or not isinstance(to, str) or not to
                            or not isinstance(amt, int) or isinstance(amt, bool) or amt <= 0):
                        raise ValueError("legacy-sol5 字段类型非法")
                else:
                    ts, slot, _tx_index, _instr_index, frm, to, amt = validate_edge_row(row)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError(f"边文件 {path} 第 {line_no} 行非法: {exc}") from exc
            n += 1
            lo = slot if lo is None or slot < lo else lo
            hi = slot if hi is None or slot > hi else hi
            for o in (frm, to):
                if not o.startswith("0x"):
                    idx.setdefault(o, set()).add(slot)
    return idx, lo, hi, n


def fetch_mint_sigs(rpc, mint, max_pages, wall_dl, stop_below=None):
    """mint 签名史 [(sig, slot)]（滤失败笔），新→老翻页。stop_below：翻过该 slot 即停。
    返回 (rows, complete, wall_hit)——wall_hit=True 表示因墙钟截断（样本无效判据之一）。"""
    out, before = [], None
    for page in range(max_pages):
        if time.time() > wall_dl:
            log(f"签名史拉取触墙钟保险丝，截断于 {len(out)} 条")
            return out, False, True
        params = [mint, {"limit": 1000}]
        if before:
            params[1]["before"] = before
        rows = rpc.call("getSignaturesForAddress", params)
        if rows is None:
            log(f"签名史第 {page} 页失败，截断")
            break
        out += [(r["signature"], r["slot"]) for r in rows if r.get("err") is None]
        if len(rows) < 1000:
            return out, True, False
        before = rows[-1]["signature"]
        if stop_below is not None and rows[-1]["slot"] < stop_below:
            return out, True, False
    return out, False, False


def sample_inits_from_blocks(rpc, mint, lo, hi, n_blocks, target, wall_dl, wall_flag):
    """blocks 模式：区间内均匀抽 slot，getBlock 整块提取目标 mint 初始化事件。
    因墙钟提前收数时置位 wall_flag["hit"]（样本无效判据）。"""
    inits, blocks_read = {}, 0
    step = max(1, (hi - lo) // max(1, n_blocks))
    slots = list(range(lo, hi + 1, step))[:n_blocks]
    for s in slots:
        if len(inits) >= target:
            break
        if time.time() > wall_dl:
            wall_flag["hit"] = True
            log("blocks 抽样触墙钟保险丝，提前收数（样本无效）")
            break
        blk = None
        for try_slot in range(s, min(s + 4, hi + 1)):  # 空块（skipped slot）顺移重试
            blk = rpc.call("getBlock", [try_slot, {
                "encoding": "jsonParsed", "transactionDetails": "full",
                "rewards": False, "maxSupportedTransactionVersion": 0}])
            if blk:
                break
        if not blk:
            continue
        blocks_read += 1
        slot_real = blk.get("parentSlot", s) + 1
        for tx in blk.get("transactions", []):
            if (tx.get("meta") or {}).get("err") is not None:
                continue
            for acc, owner in extract_inits(tx, mint).items():
                inits.setdefault(acc, {"owner": owner, "init_slot": slot_real})
    log(f"blocks 模式读块 {blocks_read} 个 → 初始化事件 {len(inits)} 个")
    return inits


def iter_parsed_instructions(tx):
    """外层 + innerInstructions 全部 jsonParsed 指令。"""
    msg = tx.get("transaction", {}).get("message", {})
    for ins in msg.get("instructions", []):
        yield ins
    for grp in (tx.get("meta") or {}).get("innerInstructions", []) or []:
        for ins in grp.get("instructions", []):
            yield ins


def extract_inits(tx, mint):
    """一笔 tx 里目标 mint 的历史账户发现 → {token_account: owner}。
    双通道并集：①初始化指令（外/内层合扫）②pre/postTokenBalances 里 mint 匹配的条目
    （每笔转账双方都在列，产率远高于仅初始化笔；owner 字段自带）。"""
    found = {}
    for ins in iter_parsed_instructions(tx):
        p = ins.get("parsed")
        if not isinstance(p, dict):
            continue
        typ, info = p.get("type"), p.get("info", {})
        if info.get("mint") != mint:
            continue
        if typ in INIT_TYPES:
            found.setdefault(info.get("account"), info.get("owner"))
        elif typ in ATA_TYPES:
            found.setdefault(info.get("account"), info.get("wallet"))
    meta = tx.get("meta") or {}
    keys = [k["pubkey"] if isinstance(k, dict) else k
            for k in tx.get("transaction", {}).get("message", {}).get("accountKeys", [])]
    for side in ("preTokenBalances", "postTokenBalances"):
        for tb in meta.get(side, []) or []:
            if tb.get("mint") == mint and tb.get("owner") and tb["accountIndex"] < len(keys):
                found.setdefault(keys[tb["accountIndex"]], tb["owner"])
    return {a: o for a, o in found.items() if a and o}


def account_deltas(tx, token_account, mint):
    """该 token account 在这笔 tx 的净变动（raw 整数；0 变动/非目标 mint 返回 None）。"""
    meta = tx.get("meta") or {}
    keys = [k["pubkey"] if isinstance(k, dict) else k
            for k in tx.get("transaction", {}).get("message", {}).get("accountKeys", [])]
    pre = post = None
    owner = None
    for tb in meta.get("preTokenBalances", []) or []:
        if tb.get("mint") == mint and keys[tb["accountIndex"]] == token_account:
            pre = int(tb["uiTokenAmount"]["amount"]); owner = tb.get("owner")
    for tb in meta.get("postTokenBalances", []) or []:
        if tb.get("mint") == mint and keys[tb["accountIndex"]] == token_account:
            post = int(tb["uiTokenAmount"]["amount"]); owner = owner or tb.get("owner")
    if pre is None and post is None:
        return None
    delta = (post or 0) - (pre or 0)
    return (delta, owner) if delta else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mint")
    ap.add_argument("--edges", default=None, help="SQD 边集 jsonl.gz（默认共享 sha256(mint) 路径）")
    ap.add_argument("--legacy-sol5", action="store_true",
                    help="显式审计旧 5 元组；报告强制 non-formal/order-ambiguous")
    ap.add_argument("--out", default=None, help="审计报告 JSON 输出路径")
    ap.add_argument("--mode", choices=["auto", "sigs", "blocks"], default="auto")
    ap.add_argument("--block-samples", type=int, default=15, help="blocks 模式抽块数")
    ap.add_argument("--sample-inits", type=int, default=60, help="目标初始化事件样本数（边集区间内）")
    ap.add_argument("--deep-accounts", type=int, default=25, help="深挖销户账户数上限")
    ap.add_argument("--deep-sigs", type=int, default=120, help="每销户账户签名史上限")
    ap.add_argument("--max-sig-pages", type=int, default=600)
    ap.add_argument("--interval", type=float, default=0.15)
    ap.add_argument("--wall-min", type=float, default=25.0, help="总墙钟保险丝（分钟）")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--rpc", default=DEF_RPC)
    ap.add_argument("--proxy", default=None,
                    help="代理 URL；空字符串或 none 显式直连（默认经 CHIP_PROXY/端口探测解析）")
    args = ap.parse_args()
    try:
        args.proxy = resolve_proxy(args.proxy)
    except ValueError as exc:
        ap.error(str(exc))
    random.seed(args.seed)
    wall_dl = T0 + args.wall_min * 60
    mint = args.mint
    default_edges, _default_meta, _default_parts = soltx_cache_paths(mint, Path("data"))
    edges_path = Path(args.edges) if args.edges else default_edges
    out_path = Path(args.out or f"data/closed_audit-{mint.lower()}.json")
    if not edges_path.exists():
        bail_invalid(out_path, mint, edges_path, f"边集不存在：{edges_path}",
                     legacy_sol5=args.legacy_sol5)

    rpc = Rpc(args.rpc, args.proxy, args.interval)
    try:
        idx, lo, hi, n_edges = load_edge_index(
            edges_path, legacy_sol5=args.legacy_sol5)
    except (OSError, ValueError) as exc:
        bail_invalid(out_path, mint, edges_path, str(exc),
                     legacy_sol5=args.legacy_sol5)
    if not n_edges or lo is None or hi is None:
        bail_invalid(out_path, mint, edges_path, "边文件为空，无法抽样审计",
                     legacy_sol5=args.legacy_sol5)
    log(f"边集 {n_edges} 条，slot 区间 [{lo}, {hi}]，owner {len(idx)} 个")

    # 样本发现：sigs / blocks / auto（3 页探路未进区间即切 blocks）
    mode, decoded, sig_stat = args.mode, 0, {"total": 0, "complete": None, "in_range": 0}
    inits = {}  # account -> {owner, init_slot}
    wall_flag = {"hit": False}  # GPT-F-06：任何一处因墙钟截断＝样本无效
    if mode == "auto":
        probe, _, _ = fetch_mint_sigs(rpc, mint, 3, wall_dl, stop_below=lo)
        if probe and any(lo <= s <= hi for _, s in probe):
            mode = "sigs"
        else:
            log("auto：3 页签名史未进入边集区间（历史定向段），切 blocks 模式")
            mode = "blocks"
    if mode == "sigs":
        sigs, complete, wall_hit = fetch_mint_sigs(rpc, mint, args.max_sig_pages, wall_dl,
                                                   stop_below=lo)
        wall_flag["hit"] = wall_flag["hit"] or wall_hit
        if not sigs:
            bail_invalid(out_path, mint, edges_path, "mint 签名史为空/拉取失败",
                         legacy_sol5=args.legacy_sol5)
        in_range = [s for s in sigs if lo <= s[1] <= hi]
        sig_stat = {"total": len(sigs), "complete": complete, "in_range": len(in_range)}
        log(f"mint 签名史 {len(sigs)} 条（complete={complete}），边集区间内 {len(in_range)} 条")
        pool = in_range if in_range else sigs
        random.shuffle(pool)
        for sig, slot in pool:
            if len(inits) >= args.sample_inits:
                break
            if time.time() > wall_dl:
                wall_flag["hit"] = True
                log("初始化事件抽样触墙钟保险丝（样本无效）")
                break
            tx = rpc.call("getTransaction", [sig, {"encoding": "jsonParsed",
                                                   "maxSupportedTransactionVersion": 0}])
            decoded += 1
            if not tx:
                continue
            for acc, owner in extract_inits(tx, mint).items():
                inits.setdefault(acc, {"owner": owner, "init_slot": slot})
        log(f"decode {decoded} 笔 → 初始化事件 {len(inits)} 个")
    else:
        inits = sample_inits_from_blocks(rpc, mint, lo, hi, args.block_samples,
                                         args.sample_inits, wall_dl, wall_flag)
    if not inits:
        bail_invalid(out_path, mint, edges_path,
                     "抽样未命中任何初始化事件（样本过小或池全为非初始化笔）",
                     legacy_sol5=args.legacy_sol5)

    # 存活/销户判定（getMultipleAccounts 批 100；publicnode 屏蔽此法，须 mainnet-beta）
    accs = list(inits.keys())
    alive, closed = set(), set()
    gma_batch_failed = 0
    for i in range(0, len(accs), 100):
        batch = accs[i:i + 100]
        res = rpc.call("getMultipleAccounts", [batch, {"encoding": "base64"}])
        if res is None:
            # GPT-F-06：批失败＝存活/销户判定对这批账户是盲的，样本无效（后面统一 exit 1），
            # 不再静默 continue 冒充"这批没有销户账户"。
            log("getMultipleAccounts 失败（样本无效，将按 INVALID_SAMPLE exit 1）")
            gma_batch_failed += 1
            continue
        for a, v in zip(batch, res.get("value", [])):
            (alive if v else closed).add(a)
    log(f"存活 {len(alive)} / 销户 {len(closed)}（批失败 {gma_batch_failed}）")

    # 深挖销户账户：自身签名史（翻页）decode 实际转账 → 对照边集；结果按账户分类
    events = {"checked": 0, "covered": 0, "missing": 0, "out_of_range": 0}
    acct_cls = {"events_found": 0, "all_zero_delta": 0, "fetch_failed": 0}
    missing_detail, deep_done = [], 0
    for acc in list(closed)[: args.deep_accounts]:
        if time.time() > wall_dl:
            wall_flag["hit"] = True
            log("深挖触墙钟保险丝，提前收数（样本无效）"); break
        owner = inits[acc]["owner"]
        rows, before = [], None
        while len(rows) < args.deep_sigs:
            params = [acc, {"limit": min(1000, args.deep_sigs - len(rows))}]
            if before:
                params[1]["before"] = before
            page = rpc.call("getSignaturesForAddress", params)
            if page is None:
                rows = None; break
            rows += page
            if len(page) < params[1]["limit"]:
                break
            before = page[-1]["signature"]
        deep_done += 1
        if rows is None:
            acct_cls["fetch_failed"] += 1; continue
        found_any = False
        for r in rows:
            if r.get("err") is not None:
                continue
            tx = rpc.call("getTransaction", [r["signature"], {"encoding": "jsonParsed",
                                                              "maxSupportedTransactionVersion": 0}])
            if not tx:
                continue
            d = account_deltas(tx, acc, mint)
            if not d:
                continue
            found_any = True
            delta, ob = d
            own = ob or owner
            slot = r["slot"]
            if not (lo <= slot <= hi):
                events["out_of_range"] += 1
                continue
            events["checked"] += 1
            if slot in idx.get(own, ()):
                events["covered"] += 1
            else:
                events["missing"] += 1
                missing_detail.append({"token_account": acc, "owner": own, "slot": slot,
                                       "sig": r["signature"], "delta_raw": str(delta)})
        acct_cls["events_found" if found_any else "all_zero_delta"] += 1
    undetermined_over_half = bool(
        deep_done and acct_cls["all_zero_delta"] + acct_cls["fetch_failed"] > deep_done // 2)
    if undetermined_over_half:
        log(f"⚠ 深挖账户过半无有效事件（{acct_cls}）——签名窗口可能没盖住 delta 笔，"
            f"建议加大 --deep-sigs 或检查代理/限速；undetermined 过半＝样本无效（exit 1）")

    # ── GPT-F-06 收口：退出码对齐脚本自身契约（0=零漏；2=发现漏边；1=运行失败/样本无效）。
    # 样本无效判据（任一命中即 exit 1，不再 fail-open 冒充零漏）：
    invalid_reasons = []
    if gma_batch_failed:
        invalid_reasons.append(f"getMultipleAccounts 批失败 {gma_batch_failed} 批"
                               "（存活/销户判定对这些账户是盲的）")
    if deep_done and acct_cls["fetch_failed"] == deep_done:
        invalid_reasons.append("深挖账户全部 fetch_failed（一个转账都没核到）")
    if closed and not events["checked"]:
        invalid_reasons.append(f"抽到 {len(closed)} 个销户账户但核到的区间内事件为 0"
                               "（checked=0 且 closed>0，覆盖率无从谈起）")
    if wall_flag["hit"]:
        invalid_reasons.append("墙钟截断（样本被保险丝提前收数，不完整）")
    if undetermined_over_half:
        invalid_reasons.append("undetermined（all_zero_delta+fetch_failed）过半")
    # 边界显式定案：closed=0＝抽样内无销户账户（审计对象为空）——是弱结论不是查询失败，
    # 如实报 NO_CLOSED_SAMPLED / exit 0，不冒充"销户路径零漏"的强证明。
    if events["missing"]:
        status, exit_code = "LEAK_FOUND", 2
    elif invalid_reasons:
        status, exit_code = "INVALID_SAMPLE", 1
    elif not closed:
        status, exit_code = "NO_CLOSED_SAMPLED", 0
    else:
        status, exit_code = "CLEAN", 0

    cov = events["covered"] / events["checked"] if events["checked"] else None
    report = {
        "mint": mint, "edges_file": str(edges_path), "edges": n_edges,
        "edge_slot_range": [lo, hi], "mode": mode,
        "status": status, "exit_code": exit_code,
        "non_formal": bool(args.legacy_sol5),
        "order_ambiguous": bool(args.legacy_sol5),
        "invalid_reasons": invalid_reasons,
        "mint_sig_history": sig_stat,
        "sampled": {"decoded_txs": decoded, "init_events": len(inits),
                    "alive": len(alive), "closed": len(closed), "deep_checked": deep_done,
                    "deep_account_classes": acct_cls,
                    "gma_batch_failed": gma_batch_failed,
                    "wall_truncated": wall_flag["hit"]},
        "events": events, "coverage_rate": cov, "missing_detail": missing_detail[:200],
        "params": {k: getattr(args, k.replace("-", "_")) for k in
                   ["sample-inits", "deep-accounts", "deep-sigs", "block-samples",
                    "seed", "interval", "mode"]},
        "rpc_calls": rpc.calls, "elapsed_sec": round(time.time() - T0, 1),
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    log(f"报告 → {out_path}")
    print(json.dumps({"mode": mode, "status": status,
                      "closed_sampled": len(closed), "deep_checked": deep_done,
                      "deep_account_classes": acct_cls,
                      "events_checked": events["checked"], "covered": events["covered"],
                      "missing": events["missing"], "out_of_range": events["out_of_range"],
                      "coverage_rate": cov,
                      "invalid_reasons": invalid_reasons}, ensure_ascii=False))
    if invalid_reasons and status == "INVALID_SAMPLE":
        for reason in invalid_reasons:
            log(f"样本无效: {reason}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
