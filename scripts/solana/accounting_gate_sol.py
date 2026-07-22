#!/usr/bin/env python3
"""代币记账模型准入 gate（Solana）——开工时自动检测 mint 的记账模型是否适用标准重放。

背景：SPL 标准币的 token account 余额只被转账指令直改，重放模型安全；Token-2022 的
TransferFee / TransferHook / InterestBearing / PermanentDelegate 等扩展会让"按转账流水
重建余额"整体算错（且供给对账闭合也发现不了）。本脚本在采集/对账之前硬拦非标准 mint。

检测项（一次 getAccountInfo jsonParsed 全覆盖，Helius 3.1.9 实测扩展解析完整）：
  1. owner program 判别：SPL Token（Tokenkeg…）/ Token-2022（Tokenz…）/ 其他 → unknown
  2. mint authority / freeze authority 记录（freeze 在手 → WARN：可冻结账户）
  3. Token-2022 扩展逐个分级：
     BLOCK：transferFeeConfig(现役bps>0)、transferHook(hook program 非空)、
            permanentDelegate、interestBearingConfig(rate≠0)、confidentialTransfer 系
     WARN ：transferFeeConfig(bps=0 但 authority 可调起)、transferHook(program 未设)、
            defaultAccountState=frozen、pausableConfig、mintCloseAuthority、
            interestBearingConfig(rate=0)
     INFO ：metadataPointer、tokenMetadata、groupPointer 等纯元数据扩展（不入 warnings）
     未识别扩展 → 保守按 BLOCK（宁可误停不可漏放）

用法:
  python3 accounting_gate_sol.py --mint <mint地址> [--rpc URL] [--out accounting_mode.json]
  --rpc 默认读 ~/.config/helius/api-key 拼 Helius 端点（国内直连）；无 key 时退
        https://api.mainnet-beta.solana.com（须走系统代理）

输出: accounting_mode.json（mode/verdict/exit_code/owner_program/extensions 分级明细）
退出码: 0 = standard 或 WARN 级（可冻结/可调费等——记录放行，报告里提示盯参数切换）
        2 = BLOCK 级（transfer-fee/hook 等转账语义扩展——重放模型不适用，需人工定制）
        1 = 检测自身失败（网络失败/地址不是 mint）——不许把失败伪装成 standard

实测（2026-07-22 通道体检）：Helius getAccountInfo(jsonParsed) 对 BERN(Token-2022)
直接返回 extensions 数组（transferFeeConfig 现役 269bps 全字段），无需手动 TLV 解析。
（来源：v3.19 A-记账模型准入 gate，2026-07-22）"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

SPL_TOKEN = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
PUBLIC_RPC = "https://api.mainnet-beta.solana.com"

# Token-2022 扩展分级表（jsonParsed 的 extension 名，未列出者保守 BLOCK）
EXT_INFO = {"metadataPointer", "tokenMetadata", "groupPointer", "groupMemberPointer",
            "tokenGroup", "tokenGroupMember", "immutableOwner", "memoTransfer",
            "cpiGuard", "scaledUiAmountConfig"}
EXT_WARN = {"mintCloseAuthority", "defaultAccountState", "pausableConfig",
            "nonTransferable"}  # nonTransferable: 转不动≠算错，记 WARN 由人工看
EXT_BLOCK = {"permanentDelegate", "confidentialTransferMint",
             "confidentialTransferFeeConfig", "confidentialMintBurn"}
# transferFeeConfig / transferHook / interestBearingConfig 按内容动态分级，见 classify_ext()


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_ext(ext):
    """返回 (等级, 说明)。等级 ∈ BLOCK / WARN / INFO。"""
    name = ext.get("extension", "?")
    st = ext.get("state") or {}
    if name == "transferFeeConfig":
        newer = st.get("newerTransferFee") or {}
        bps = newer.get("transferFeeBasisPoints", 0)
        mx = newer.get("maximumFee", 0)
        auth = st.get("transferFeeConfigAuthority")
        if bps or mx:
            return "BLOCK", f"转账税现役 {bps}bps maximumFee={mx}（重放的到账额≠事件额）"
        if auth:
            return "WARN", f"转账税当前 0bps 但 authority={auth} 可随时调起"
        return "WARN", "转账税扩展存在（0bps 且 authority 已弃权）——历史期费率需人工核"
    if name == "transferHook":
        prog = st.get("programId") or st.get("hookProgramId")
        if prog:
            return "BLOCK", f"TransferHook 挂载 program={prog}（转账语义由外部程序改写）"
        return "WARN", "TransferHook 扩展存在但 program 未设（authority 可后设）"
    if name == "interestBearingConfig":
        rate = st.get("currentRate", 0)
        if rate:
            return "BLOCK", f"计息代币 currentRate={rate}（UI 余额随时间漂移）"
        return "WARN", "计息扩展存在（rate=0，可被调起）"
    if name in EXT_BLOCK:
        return "BLOCK", f"{name}（转账/余额语义被扩展改写）"
    if name in EXT_WARN:
        detail = ""
        if name == "defaultAccountState":
            detail = f" state={st.get('accountState')}"
            if st.get("accountState") == "initialized":
                return "INFO", f"{name}=initialized（默认不冻结，无害）"
        return "WARN", f"{name}{detail}"
    if name in EXT_INFO:
        return "INFO", name
    return "BLOCK", f"未识别扩展 {name}（保守拦停，人工核对后可加入分级表）"


def main():
    ap = argparse.ArgumentParser(description="Solana 记账模型准入 gate")
    ap.add_argument("--mint", required=True)
    ap.add_argument("--rpc", default=None,
                    help="默认读 ~/.config/helius/api-key 拼 Helius；无则公共 RPC")
    ap.add_argument("--out", default="accounting_mode.json")
    a = ap.parse_args()

    rpc = a.rpc
    if not rpc:
        kf = os.path.expanduser("~/.config/helius/api-key")
        if os.path.exists(kf):
            rpc = "https://mainnet.helius-rpc.com/?api-key=" + open(kf).read().strip()
        else:
            rpc = PUBLIC_RPC

    result = {"schema": "accounting-gate/v1", "chain": "solana", "mint": a.mint,
              "checked_at": now_iso(), "rpc": rpc.split("?")[0],
              "checks": {}, "warnings": [], "reasons": []}

    def finish(mode, verdict, code):
        result.update({"mode": mode, "verdict": verdict, "exit_code": code})
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

    # ---- getAccountInfo（重试 4 次）----
    j = None
    for att in range(4):
        try:
            r = requests.post(rpc, json={"jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
                                         "params": [a.mint, {"encoding": "jsonParsed"}]},
                              timeout=30)
            j = r.json()
            if "error" not in j:
                break
            result["reasons"].append(f"rpc error: {j['error'].get('message', '')[:100]}")
        except Exception as e:  # noqa: BLE001
            result["reasons"].append(f"{type(e).__name__}: {str(e)[:100]}")
        time.sleep(1.5 * (att + 1))
    else:
        result["reasons"] = result["reasons"][-1:] + ["getAccountInfo 重试耗尽"]
        finish("unknown", "FAIL", 1)

    val = (j.get("result") or {}).get("value")
    if val is None:
        result["reasons"].append("账户不存在（mint 地址错/错链）")
        finish("unknown", "FAIL", 1)

    owner = val.get("owner")
    data = val.get("data")
    if not isinstance(data, dict):  # 普通钱包/程序账户: data 为 [base64, "base64"] 列表
        result["checks"]["owner"] = owner
        result["reasons"].append(f"账户不可解析为代币结构（owner={owner}）——不是 mint 地址")
        finish("unknown", "FAIL", 1)
    parsed = data.get("parsed") or {}
    info = parsed.get("info") or {}
    result["checks"]["owner"] = owner
    result["checks"]["account_type"] = parsed.get("type")

    if parsed.get("type") != "mint":
        result["reasons"].append(f"目标不是 mint 账户（type={parsed.get('type')}, owner={owner}）")
        finish("unknown", "FAIL", 1)

    prog = {SPL_TOKEN: "spl-token", TOKEN_2022: "spl-token-2022"}.get(owner, "unknown")
    result["checks"]["owner_program"] = prog
    result["checks"]["mint_authority"] = info.get("mintAuthority")
    result["checks"]["freeze_authority"] = info.get("freezeAuthority")
    result["checks"]["supply"] = info.get("supply")
    result["checks"]["decimals"] = info.get("decimals")

    if info.get("mintAuthority"):
        result["warnings"].append(f"mint authority 未弃权: {info['mintAuthority']}（可增发，供给面盯守）")
    if info.get("freezeAuthority"):
        result["warnings"].append(f"freeze authority 在手: {info['freezeAuthority']}（可冻结持仓账户）")

    if prog == "unknown":
        result["reasons"].append(f"owner 不是 SPL Token/Token-2022（owner={owner}）——非标准代币程序")
        finish("unknown", "BLOCK", 2)

    # ---- Token-2022 扩展枚举 ----
    exts = info.get("extensions") or []
    graded = []
    for e in exts:
        lvl, why = classify_ext(e)
        graded.append({"extension": e.get("extension"), "level": lvl, "why": why,
                       "state": e.get("state")})
    result["checks"]["extensions"] = graded
    blocks = [g for g in graded if g["level"] == "BLOCK"]
    warns = [g for g in graded if g["level"] == "WARN"]
    for g in warns:
        result["warnings"].append(f"扩展 {g['extension']}: {g['why']}")

    if prog == "spl-token-2022":
        if blocks:
            for g in blocks:
                result["reasons"].append(f"扩展 {g['extension']}: {g['why']}")
            finish("token2022-ext", "BLOCK", 2)
        if graded:
            result["warnings"].insert(0, "Token-2022 mint（扩展均非转账语义类，按标准放行）")
        finish("standard", "WARN" if warns else "PASS", 0)
    # 纯 SPL
    finish("standard", "WARN" if result["warnings"] else "PASS", 0)


if __name__ == "__main__":
    main()
