#!/usr/bin/env python3
"""代币记账模型准入 gate（EVM）——开工时自动检测"Transfer 流水重建余额"模型是否适用。

背景：fee-on-transfer（转账税）、rebase/reflection 这类币会让全历史重放整体算错，
且供给对账闭合也发现不了（模型错但自洽）。本脚本在采集/对账之前硬拦非标准币。

检测项：
  1. proxy      EIP-1967 implementation/admin/beacon slot（eth_getStorageAt）→ WARN
  2. fee-on-transfer 双路：
     a) 真实事件差值法（主路）：HyperSync 拉近程 Transfer，选"干净样本"（from/to 在该块
        仅出现一次），事件前后块 eth_call balanceOf 差值 vs 事件 value——能覆盖
        "只对 DEX pair 收税"的形态（BabyDoge 实测钱包互转免税、只有走池路径才收）
     b) eth_simulateV1 模拟转账（兜底/加强）：真实 holder → 探针地址转账后读探针余额，
        实收 < 发送即收税（HOGE 实测 0.98 实收率）；只能测"全局税"，测不出仅池收税
  3. rebase     a) totalSupply 对账：TS(tip-W) + 窗口内 mint-burn 净额 == TS(tip)
                b) 静默地址漂移：窗口内无事件的持币地址，两时点 balanceOf 是否漂移
  4. 权限面     Sourcify v2 ABI 扫 mint/pause/blacklist/setFee 类函数名——只记录不定级

用法:
  python3 accounting_gate.py --token 0x... --chain bsc [--rpc URL] [--out accounting_mode.json]
  python3 accounting_gate.py --token 0x... --chain eth --rpc https://eth-mainnet.g.alchemy.com/v2/<key> \
      --proxy http://127.0.0.1:7897
  --rpc      不给时用链默认免 key 端点（见 DEFAULT_RPC；eth/base 建议传 Alchemy=archive）
  --hypersync / --hypersync-token-file  事件通道（默认从 ~/.config/hypersync/token 读取）
  --proxy    只作用于 RPC（Alchemy *.g.alchemy.com 国内必须走 clash）；HyperSync/Sourcify 国内直连
  --samples  事件差值法样本数上限（默认 8）

输出: accounting_mode.json（mode/verdict/exit_code/checks 逐项证据+抽样明细）
退出码: 0 = standard 或 WARN 级（upgradeable-proxy、可暂停等——记录放行，报告里提示盯升级切点）
        2 = BLOCK 级（fee-on-transfer / rebase / 未知记账——重放模型不适用，需人工定制）
        1 = 检测自身失败（网络/数据不足）——不许把失败伪装成 standard

实测坑（2026-07-22 通道体检）：
  - BSC dataseed：eth_call 历史 state 窗口 ~128 块（120 OK / 240 missing trie node），
    支持 eth_simulateV1；eth_getLogs 拒（-32005）→ 事件一律走 HyperSync
  - bsc publicnode 全 archive 墙（128 块内也拒）；dRPC 免费层限速凶+上游不稳只配当兜底
  - Alchemy ETH 免费层：eth_call 全历史 archive ✅，但 getLogs 限 10 块 → 事件仍走 HyperSync
  - state 窗口自动探测：tip-150 试探成功按 archive 用大窗口，失败按 100 块保守窗口
  - PAXG 链上转账费现役为 0（勿当税币样本）；HOGE(ETH) 2% 硬编码税是稳定 BLOCK 样本
（来源：v3.19 A-记账模型准入 gate，2026-07-22）"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from chain_registry import evm_chain_id_for, formal_evm_chains
from net import RpcAttestationError, attested_rpc_pool

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO32 = "0x" + "0" * 64
ZERO_ADDR = "0x" + "0" * 40
# EIP-1967 标准槽位
SLOT_IMPL = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
SLOT_ADMIN = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
SLOT_BEACON = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
SEL_BALANCE = "0x70a08231"   # balanceOf(address)
SEL_TOTSUP = "0x18160ddd"    # totalSupply()
SEL_TRANSFER = "0xa9059cbb"  # transfer(address,uint256)
SEL_DECIMALS = "0x313ce567"  # decimals()
PROBE_ADDR = "0x0000000000000000000000000000000000012345"  # 模拟转账收款探针（无私钥地址）

DEFAULT_RPC = {
    "bsc": "https://bsc-dataseed.bnbchain.org",
    "eth": "https://ethereum-rpc.publicnode.com",   # 建议 --rpc 传 Alchemy（archive）
    "base": "https://mainnet.base.org",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "polygon": "https://polygon-rpc.com",
}
DEFAULT_HS = {
    "bsc": "https://bsc.hypersync.xyz",
    "eth": "https://eth.hypersync.xyz",
    "base": "https://base.hypersync.xyz",
    "arbitrum": "https://arbitrum.hypersync.xyz",
    "polygon": "https://polygon.hypersync.xyz",
}
# 权限面扫描（Sourcify ABI 函数名，小写含匹配；只记录不定级）
PERM_PATTERNS = ["mint", "pause", "blacklist", "blocklist", "freeze", "setfee", "settax",
                 "setmax", "excludefrom", "upgradeto", "burnfrom", "rescue", "setrate",
                 "rebase", "setrouter", "setswap"]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Rpc:
    """Accounting adapter over the sole chain-attested shared RPC session."""

    def __init__(self, url, chain, proxy=None, interval=0.12):
        self.url, self.interval = url, interval
        self.pool = attested_rpc_pool(
            url, chain, formal=True, proxy=proxy, rps=max(1.0, 1.0 / interval),
            concurrency=1, attempts=5)
        self.n_calls = 0

    def call(self, method, params, attempts=5, quiet_errors=()):
        try:
            result = self.pool.call(method, params)
        except RpcAttestationError as exc:
            raise RpcNetError(str(exc)) from exc
        self.n_calls += 1
        if not result.get("ok"):
            message = str(result.get("error") or "RPC call failed")
            if any(item in message for item in quiet_errors) \
                    or "rpc -32601:" in message or "rpc -32602:" in message:
                raise RpcSemanticError(message)
            raise RpcNetError(message)
        time.sleep(self.interval)
        return result.get("result")


class RpcNetError(Exception):
    pass


class RpcSemanticError(Exception):
    pass


STATE_GONE = ("missing trie node", "block not found", "Archive requests", "header not found",
              "state not available", "required historical state unavailable")


def call_balance(rpc, token, addr, block):
    tag = block if isinstance(block, str) else hex(block)
    data = SEL_BALANCE + addr[2:].lower().rjust(64, "0")
    res = rpc.call("eth_call", [{"to": token, "data": data}, tag], quiet_errors=STATE_GONE)
    return int(res, 16) if res and res != "0x" else 0


def call_totsup(rpc, token, block="latest"):
    tag = block if isinstance(block, str) else hex(block)
    res = rpc.call("eth_call", [{"to": token, "data": SEL_TOTSUP}, tag], quiet_errors=STATE_GONE)
    return int(res, 16) if res and res != "0x" else 0


def hs_logs(hs_url, bearer, token, from_block, to_block, max_logs=4000):
    """HyperSync 拉 [from_block, to_block) 的 Transfer 事件（自动接续 next_block）。"""
    out, cur = [], from_block
    hdrs = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    for _ in range(60):
        if cur >= to_block or len(out) >= max_logs:
            break
        body = {"from_block": cur, "to_block": to_block,
                "logs": [{"address": [token.lower()], "topics": [[TRANSFER]]}],
                "field_selection": {"log": ["block_number", "log_index",
                                            "transaction_hash", "topic1", "topic2", "data"]}}
        r = requests.post(hs_url + "/query", json=body, headers=hdrs, timeout=60)
        r.raise_for_status()
        j = r.json()
        for b in j.get("data", []):
            for l in b.get("logs", []):
                out.append({"block": l["block_number"], "log_index": l["log_index"],
                            "tx": l.get("transaction_hash"),
                            "from": "0x" + l["topic1"][-40:], "to": "0x" + l["topic2"][-40:],
                            "value": int(l["data"], 16) if l.get("data") and l["data"] != "0x" else 0})
        nb = j.get("next_block")
        if not nb or nb <= cur:
            break
        cur = nb
    return out


def detect_state_window(rpc, token, tip):
    """探测 RPC 的历史 state 深度：archive 返回 None（不限），否则保守 100 块。"""
    try:
        call_totsup(rpc, token, tip - 150)
    except RpcSemanticError:
        return 100
    except RpcNetError:
        return 100
    try:
        call_totsup(rpc, token, max(1, tip - 200000))
        return None  # archive
    except (RpcSemanticError, RpcNetError):
        return 5000  # 半深窗口（少见，如实用）


def check_proxy(rpc, token):
    out = {"is_proxy": False, "impl": None, "admin": None, "beacon": None}
    for key, slot in (("impl", SLOT_IMPL), ("admin", SLOT_ADMIN), ("beacon", SLOT_BEACON)):
        v = rpc.call("eth_getStorageAt", [token, slot, "latest"])
        if v and v != ZERO32 and int(v, 16) != 0:
            out[key] = "0x" + v[-40:]
            out["is_proxy"] = True
    return out


def pick_clean_samples(logs, lo_block, n):
    """单侧干净样本：某地址在该块内只出现在这一个事件里，即可单侧验证其余额差
    （bot 刷量币一笔交易多跳、双侧同时干净的事件几乎不存在——QUQ 实测 20 条 0 双侧样本）。
    返回 [{block, addr, side, value, tx}]；零地址与自转跳过。"""
    seen = {}
    for l in logs:
        for side in ("from", "to"):
            seen.setdefault((l["block"], l[side]), 0)
            seen[(l["block"], l[side])] += 1
    picked, used = [], set()
    for l in sorted(logs, key=lambda x: -x["block"]):  # 越新越好（离 state 窗口越远越险）
        if l["block"] < lo_block or l["value"] == 0 or l["from"] == l["to"]:
            continue
        for side in ("to", "from"):  # to 侧优先（收税币扣的是到账侧）
            ad = l[side]
            if ad == ZERO_ADDR or seen[(l["block"], ad)] != 1 or (l["block"], ad) in used:
                continue
            used.add((l["block"], ad))
            picked.append({"block": l["block"], "addr": ad, "side": side,
                           "value": l["value"], "tx": l.get("tx")})
        if len(picked) >= n:
            break
    return picked[:n]


def check_fot_events(rpc, token, samples):
    """事件差值法（单侧）：地址在事件前后块的 balanceOf 之差 vs 事件 value
    （from 侧应减 value、to 侧应增 value；容差 max(2 wei, value*1e-6)）。"""
    detail, mismatch, ok = [], 0, 0
    for s in samples:
        blk = s["block"]
        try:
            b0 = call_balance(rpc, token, s["addr"], blk - 1)
            b1 = call_balance(rpc, token, s["addr"], blk)
        except RpcSemanticError as e:
            detail.append({**s, "result": "state-gone", "err": str(e)[:60]})
            continue
        except RpcNetError as e:
            detail.append({**s, "result": "net-fail", "err": str(e)[:60]})
            continue
        tol = max(2, s["value"] // 10**6)
        delta = (b0 - b1) if s["side"] == "from" else (b1 - b0)
        d = {**s, "delta": delta, "deviation": delta - s["value"]}
        if abs(delta - s["value"]) > tol:
            d["result"] = "MISMATCH"
            mismatch += 1
        else:
            d["result"] = "exact"
            ok += 1
        detail.append(d)
    return {"samples_ok": ok, "samples_mismatch": mismatch, "detail": detail}


def check_fot_sim(rpc, token, holders, max_tries=4):
    """eth_simulateV1 模拟 holder→探针转账，读探针实收。返回 (状态, 明细列表)。"""
    detail = []
    tried = 0
    for h in holders:
        if tried >= max_tries:
            break
        try:
            bal = call_balance(rpc, token, h, "latest")
        except (RpcSemanticError, RpcNetError):
            continue
        if bal < 10**4:
            continue
        amt = bal // 2
        tried += 1
        pad = lambda a: a[2:].lower().rjust(64, "0")  # noqa: E731
        calls = [{"from": h, "to": token, "data": SEL_TRANSFER + pad(PROBE_ADDR) + "%064x" % amt},
                 {"to": token, "data": SEL_BALANCE + pad(PROBE_ADDR)}]
        try:
            res = rpc.call("eth_simulateV1",
                           [{"blockStateCalls": [{"calls": calls}]}, "latest"])
        except RpcSemanticError as e:
            return "unsupported", [{"err": str(e)[:80]}]
        except RpcNetError as e:
            detail.append({"holder": h, "result": "net-fail", "err": str(e)[:60]})
            continue
        cs = res[0]["calls"]
        if cs[0].get("status") != "0x1":
            detail.append({"holder": h, "sent": amt, "result": "revert"})
            continue
        got = int(cs[1]["returnData"], 16)
        detail.append({"holder": h, "sent": amt, "probe_received": got,
                       "result": "exact" if got == amt else "SHORTFALL",
                       "received_ratio": round(got / amt, 8) if amt else None})
    if not detail:
        return "no-holder", detail
    if any(d["result"] == "SHORTFALL" for d in detail):
        return "shortfall", detail
    if any(d["result"] == "exact" for d in detail):
        return "clean", detail
    return "all-revert", detail


def check_rebase(rpc, hs_url, bearer, token, tip, window, logs_in_window):
    """rebase 双检：totalSupply 对账 + 静默地址两时点漂移。window 为 None（archive）时取 7200。"""
    # 非 archive 时收缩到 64 块：dataseed 类节点池后端 state 深度抖动（实测同请求
    # 150 块能过、100 块偶发 missing trie node），离边缘远一点保命中率
    w = window if window is not None else 7200
    w = min(w if window is None else min(w, 64), tip - 1)
    lo = tip - w
    out = {"window_blocks": w, "window": [lo, tip]}
    if window is not None and window <= 120:
        out["note"] = ("非 archive RPC，rebase 两时点窗口仅 %d 块（分钟级）——24h 周期 rebase "
                       "抓不到，属弱检测；有 archive RPC 时建议复测" % w)
    # 窗口事件（archive 大窗口时 logs_in_window 只覆盖近程，需补拉）
    logs_w = [l for l in logs_in_window if l["block"] > lo]
    if window is None:
        logs_w = hs_logs(hs_url, bearer, token, lo + 1, tip + 1, max_logs=200000)
    # a) totalSupply 对账
    try:
        ts0, ts1 = call_totsup(rpc, token, lo), call_totsup(rpc, token, tip)
        minted = sum(l["value"] for l in logs_w if l["from"] == ZERO_ADDR)
        burned = sum(l["value"] for l in logs_w if l["to"] == ZERO_ADDR)
        drift = (ts1 - ts0) - (minted - burned)
        tol = max(2, ts1 // 10**9)
        out["total_supply"] = {"ts_lo": ts0, "ts_tip": ts1, "minted": minted,
                               "burned": burned, "drift": drift,
                               "result": "MISMATCH" if abs(drift) > tol else "exact"}
    except (RpcSemanticError, RpcNetError) as e:
        out["total_supply"] = {"result": "unavailable", "err": str(e)[:80]}
    # b) 静默地址漂移：窗口前一段的参与者中，选窗口内零事件者
    active = {l["from"] for l in logs_w} | {l["to"] for l in logs_w}
    pre = hs_logs(hs_url, bearer, token, max(0, lo - max(w, 2000) * 5), lo, max_logs=3000)
    cands, seen = [], set()
    for l in reversed(pre):
        for a in (l["to"], l["from"]):
            if a not in active and a != ZERO_ADDR and a not in seen:
                seen.add(a)
                cands.append(a)
    out["quiet_candidates"] = len(cands)
    quiet, drifted = [], 0
    for a in cands:
        if len(quiet) >= 3:
            break
        try:
            b0 = call_balance(rpc, token, a, lo)
            if b0 == 0:
                continue
            b1 = call_balance(rpc, token, a, tip)
        except (RpcSemanticError, RpcNetError):
            continue
        tol = max(2, b0 // 10**6)
        rec = {"addr": a, "bal_lo": b0, "bal_tip": b1,
               "result": "DRIFT" if abs(b1 - b0) > tol else "stable"}
        if rec["result"] == "DRIFT":
            drifted += 1
        quiet.append(rec)
    out["quiet_addrs"] = quiet
    out["quiet_drifted"] = drifted
    ts_bad = out.get("total_supply", {}).get("result") == "MISMATCH"
    out["conclusion"] = ("REBASE" if (drifted > 0 or ts_bad)
                         else ("clean" if (quiet or out.get("total_supply", {}).get("result") == "exact")
                               else "inconclusive"))
    return out


def check_permissions(chain, token):
    """Sourcify v2 ABI 权限面扫描——只记录不定级；404=未验证不算失败。"""
    cid = evm_chain_id_for(chain)
    if not cid:
        return {"available": False, "note": "Sourcify 不支持该链"}
    try:
        r = requests.get(f"https://sourcify.dev/server/v2/contract/{cid}/{token}",
                         params={"fields": "abi,compilation"}, timeout=25)
        if r.status_code == 404:
            return {"available": True, "verified": False}
        r.raise_for_status()
        j = r.json()
        fns = [x.get("name", "") for x in (j.get("abi") or []) if x.get("type") == "function"]
        flags = sorted({p for f in fns for p in PERM_PATTERNS if p in f.lower()})
        hit_fns = sorted({f for f in fns if any(p in f.lower() for p in PERM_PATTERNS)})
        return {"available": True, "verified": True,
                "contract_name": (j.get("compilation") or {}).get("name"),
                "flags": flags, "functions": hit_fns[:30]}
    except Exception as e:  # noqa: BLE001
        return {"available": False, "err": f"{type(e).__name__}: {str(e)[:80]}"}


def main():
    ap = argparse.ArgumentParser(description="EVM 记账模型准入 gate")
    ap.add_argument("--token", required=True)
    ap.add_argument("--chain", required=True,
                    choices=sorted(formal_evm_chains("accounting_adapter")))
    ap.add_argument("--rpc", default=None, help="JSON-RPC 端点（默认见 DEFAULT_RPC）")
    ap.add_argument("--hypersync", default=None, help="HyperSync 裸域名（默认按链）")
    ap.add_argument("--hypersync-token-file",
                    default=os.path.expanduser("~/.config/hypersync/token"))
    ap.add_argument("--proxy", default=None, help="RPC 代理（Alchemy 国内必须 clash）")
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--out", default="accounting_mode.json")
    a = ap.parse_args()

    token = a.token.lower()
    rpc_url = a.rpc or DEFAULT_RPC[a.chain]
    proxy = a.proxy
    if proxy is None and ".g.alchemy.com" in rpc_url:
        proxy = "http://127.0.0.1:7897"  # 登记文件既定坑：Alchemy 国内直连被墙
    hs_url = a.hypersync or DEFAULT_HS[a.chain]
    bearer = None
    if os.path.exists(a.hypersync_token_file):
        bearer = open(a.hypersync_token_file).read().strip()
    rpc = Rpc(rpc_url, a.chain, proxy=proxy)

    result = {"schema": "accounting-gate/v1", "chain": a.chain, "token": token,
              "producer": {"path": "scripts/evm/accounting_gate.py",
                           "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
              "checked_at": now_iso(), "rpc": rpc_url.split("/v2/")[0],
              "hypersync": hs_url, "checks": {}, "warnings": [], "reasons": []}

    def finish(mode, verdict, code):
        result.update({"mode": mode, "verdict": verdict, "exit_code": code,
                       "rpc_calls": rpc.n_calls})
        tmp = a.out + ".tmp"
        with open(tmp, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
        os.replace(tmp, a.out)
        print(f"[GATE] mode={mode} verdict={verdict} exit={code} -> {a.out}")
        for r_ in result["reasons"]:
            print(f"  reason: {r_}")
        for w_ in result["warnings"]:
            print(f"  warn:   {w_}")
        sys.exit(code)

    # ---- 基础与代理 ----
    try:
        tip = int(rpc.call("eth_blockNumber", []), 16)
        code_ = rpc.call("eth_getCode", [token, "latest"])
        if not code_ or code_ == "0x":
            result["reasons"].append("目标地址无合约代码（EOA/错链）")
            finish("unknown", "FAIL", 1)
        result["tip_block"] = tip
        result["checks"]["proxy"] = check_proxy(rpc, token)
    except (RpcNetError, RpcSemanticError) as e:
        result["reasons"].append(f"RPC 基础调用失败: {e}")
        finish("unknown", "FAIL", 1)
    if result["checks"]["proxy"]["is_proxy"]:
        result["warnings"].append("EIP-1967 可升级代理：记账逻辑可被升级切换，报告需盯升级切点")

    # ---- state 窗口探测 ----
    window = detect_state_window(rpc, token, tip)
    result["state_window_blocks"] = window if window is not None else "archive"

    # ---- 事件采集（近程；archive RPC 可用大窗口——历史 balanceOf 不受限）----
    ev_lo = tip - (window if window is not None else 10000) + 2
    try:
        logs = hs_logs(hs_url, bearer, token, ev_lo, tip + 1)
        wide_logs = logs
        for span in (20000, 400000):  # 仅用于模拟法找 holder / rebase 候选
            if wide_logs:
                break
            wide_logs = hs_logs(hs_url, bearer, token, max(0, tip - span), tip + 1, max_logs=1000)
    except Exception as e:  # noqa: BLE001
        result["reasons"].append(f"HyperSync 事件采集失败: {type(e).__name__}: {str(e)[:100]}")
        finish("unknown", "FAIL", 1)
    result["recent_logs_in_state_window"] = len(logs)

    # ---- fee-on-transfer 双路 ----
    samples = pick_clean_samples(logs, ev_lo, a.samples)
    fot = {"event_diff": None, "sim": None}
    if samples:
        fot["event_diff"] = check_fot_events(rpc, token, samples)
    holders = []
    for l in sorted(wide_logs, key=lambda x: -x["block"]):
        for side in ("to", "from"):
            ad = l[side]
            if ad != ZERO_ADDR and ad not in holders:
                holders.append(ad)
    sim_status, sim_detail = check_fot_sim(rpc, token, holders[:12])
    fot["sim"] = {"status": sim_status, "detail": sim_detail}
    result["checks"]["fee_on_transfer"] = fot

    ev = fot["event_diff"] or {}
    ev_bad, ev_ok = ev.get("samples_mismatch", 0), ev.get("samples_ok", 0)
    sim_bad = sim_status == "shortfall"
    sim_ok = sim_status == "clean"
    if sim_status == "all-revert":
        result["warnings"].append("模拟转账全部 revert（黑名单/暂停/受限转账嫌疑）——事件差值法结果为准")

    # ---- rebase ----
    reb = check_rebase(rpc, hs_url, bearer, token, tip, window, logs)
    result["checks"]["rebase"] = reb
    if "note" in reb:
        result["warnings"].append(reb["note"])
    if reb["conclusion"] == "inconclusive":
        result["warnings"].append("rebase 子检测无有效样本（TS 读取失败且静默地址全无余额）——本项未证伪")

    # ---- 权限面（只记录）----
    perms = check_permissions(a.chain, token)
    result["checks"]["permissions"] = perms
    if perms.get("flags"):
        result["warnings"].append("权限面（Sourcify ABI，只记录不定级）: " + ",".join(perms["flags"]))

    # ---- 裁决 ----
    if ev_bad > 0 or sim_bad:
        if ev_bad:
            result["reasons"].append(
                f"事件差值法 {ev_bad}/{ev_bad + ev_ok} 样本余额变动≠事件value（fee-on-transfer/非标准记账）")
        if sim_bad:
            worst = min((d.get("received_ratio") for d in sim_detail
                         if d.get("received_ratio") is not None), default=None)
            result["reasons"].append(f"模拟转账实收率 {worst}（<1 即链上收税）")
        finish("fee-on-transfer", "BLOCK", 2)
    if reb["conclusion"] == "REBASE":
        if reb.get("quiet_drifted"):
            result["reasons"].append(f"静默地址 {reb['quiet_drifted']} 个余额无事件漂移（rebase/reflection）")
        if reb.get("total_supply", {}).get("result") == "MISMATCH":
            result["reasons"].append(f"totalSupply 与 mint-burn 净额不闭合 drift={reb['total_supply']['drift']}")
        finish("rebase", "BLOCK", 2)
    if ev_ok == 0 and not sim_ok:
        result["reasons"].append(
            f"核心检测无有效样本（state 窗口内事件 {len(logs)} 条、干净样本 {len(samples)}、模拟 {sim_status}）——"
            "无法证明记账标准，不伪装成 standard")
        finish("unknown", "FAIL", 1)
    if result["checks"]["proxy"]["is_proxy"]:
        finish("upgradeable-proxy", "WARN", 0)
    finish("standard", "PASS", 0)


if __name__ == "__main__":
    main()
