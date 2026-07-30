#!/usr/bin/env python3
# 收编自 PYTHIA(Solana) 双报告交叉核实 2026-07-29（redo/verify_ms_members.py）；
# 成熟度：单案实战（PYTHIA 15 个 multisig 全解析成功）——接口与布局按 Squads v4 现网版本，
# 协议升级后布局可能漂移，解析失败时对照 https://github.com/Squads-Protocol/v4 校 borsh 布局。
"""Squads v4 multisig 配置账户成员解析（borsh 手解，零第三方依赖）。

用途（entity_identity_gate PDA_UNRESOLVED flag 的标准 resolution 工具）：
  大额 off-curve 静置仓若为 Squads v4 vault，解析其 multisig 配置可回答
  "谁控制这些仓"——各仓成员是否共享密钥（同属一方/共同托管）还是互不相干（独立买家）。
  PYTHIA 案裁决示例：15/15 金库全部 2-of-2 且共享同一托管密钥 → escrow 场外交割网。

用法：
  python3 squads_members.py --addrs ms_list.txt [--rpc URL] [--out ms_members.json]
    ms_list.txt: 每行一个 multisig 配置账户地址（不是 vault 地址）
  vault → multisig 的发现路径（本脚本不自动做，见下）：
    vault 是 multisig 的 PDA 派生（seed: "squad", ms, index u8, "vault"）——
    正向验证：已知 ms 候选时按 seed 派生比对 vault；
    反向发现：vault 的创建/首笔 tx 账户列表里 owner=SQDS4ep… 的账户即其 multisig 配置。

输出：stdout 摘要（每 ms 的 threshold/members/create_key + 跨 ms 共享密钥矩阵）+ JSON 落盘。
退出码：0=全部解析成功；1=存在解析失败（协议布局漂移或地址不是 Squads v4 ms）。
"""
import argparse, base64, json, ssl, sys, time, urllib.request
from pathlib import Path

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
SQUADS_V4_PROGRAM = "SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf"


def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = B58[r] + s
    pad = 0
    for x in b:
        if x == 0:
            pad += 1
        else:
            break
    return "1" * pad + s


def default_rpc() -> str:
    key_f = Path.home() / ".config/helius/api-key"
    if key_f.exists():
        return f"https://mainnet.helius-rpc.com/?api-key={key_f.read_text().strip()}"
    return "https://api.mainnet-beta.solana.com"


def rpc(url, method, params, ctx):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for i in range(3):
        try:
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
                out = json.loads(r.read())
                if "error" in out:
                    time.sleep(1.2)
                    continue
                return out.get("result")
        except Exception:
            time.sleep(1.0 + i)
    return None


def parse_multisig(data: bytes) -> dict:
    """Squads v4 Multisig borsh 布局：8 discriminator + create_key(32) + config_authority(32)
    + threshold(u16) + time_lock(u32) + transaction_index(u64) + stale_transaction_index(u64)
    + rent_collector Option<Pubkey> + bump(u8) + members Vec<{key(32), permissions(u8)}>"""
    o = 8
    create_key = b58encode(data[o:o + 32]); o += 32
    config_auth = b58encode(data[o:o + 32]); o += 32
    threshold = int.from_bytes(data[o:o + 2], "little"); o += 2
    o += 4 + 8 + 8  # time_lock, tx_index, stale_tx_index
    has_rc = data[o]; o += 1
    if has_rc:
        o += 32
    o += 1  # bump
    nmem = int.from_bytes(data[o:o + 4], "little"); o += 4
    members = []
    for _ in range(nmem):
        k = b58encode(data[o:o + 32]); o += 32
        perm = data[o]; o += 1
        members.append([k, perm])
    return {"create_key": create_key, "config_authority": config_auth,
            "threshold": threshold, "members": members}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--addrs", required=True, help="multisig 配置账户地址清单文件（每行一个）")
    ap.add_argument("--rpc", default=None, help="RPC 端点（默认 Helius key 文件，缺省 mainnet-beta）")
    ap.add_argument("--out", default="ms_members.json")
    args = ap.parse_args()

    url = args.rpc or default_rpc()
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()

    addrs = [l.strip() for l in Path(args.addrs).read_text().splitlines() if l.strip()]
    print(f"解析 {len(addrs)} 个 multisig 配置账户（rpc={url.split('?')[0]}）")

    parsed, fails = {}, 0
    # getMultipleAccounts 上限 100/批
    for i in range(0, len(addrs), 100):
        chunk = addrs[i:i + 100]
        res = rpc(url, "getMultipleAccounts", [chunk, {"encoding": "base64"}], ctx)
        vals = res.get("value", []) if isinstance(res, dict) else [None] * len(chunk)
        for m, v in zip(chunk, vals):
            if not v:
                parsed[m] = None; fails += 1
                continue
            if v.get("owner") != SQUADS_V4_PROGRAM:
                parsed[m] = {"err": f"owner={v.get('owner')} 非 Squads v4"}; fails += 1
                continue
            raw = base64.b64decode(v["data"][0])
            try:
                parsed[m] = parse_multisig(raw)
            except Exception as e:
                parsed[m] = {"err": str(e), "len": len(raw)}; fails += 1

    member_to_ms = {}
    print("\n=== 各 multisig 成员 ===")
    for m, p in parsed.items():
        if not p or "members" not in p:
            print(f"  {m[:12]}… 解析失败: {p}")
            continue
        mems = [k for k, _ in p["members"]]
        for k in mems:
            member_to_ms.setdefault(k, set()).add(m)
        print(f"  {m[:12]}… thr={p['threshold']}/{len(mems)} members={[x[:8] for x in mems]} create_key={p['create_key'][:8]}")

    shared = {k: v for k, v in member_to_ms.items() if len(v) >= 2}
    print(f"\n=== 跨 multisig 共享的成员密钥（≥2 个 ms；共同托管/同一方指纹）===")
    for k, v in sorted(shared.items(), key=lambda x: -len(x[1])):
        print(f"  {k}  出现在 {len(v)}/{len(addrs)} 个 multisig")
    print(f"\n共 {len(member_to_ms)} 个不同成员密钥，其中 {len(shared)} 个跨多签共享")

    Path(args.out).write_text(json.dumps(
        {m: (dict(p) if isinstance(p, dict) else None) for m, p in parsed.items()},
        indent=1, default=list))
    print(f"落盘 {args.out}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
