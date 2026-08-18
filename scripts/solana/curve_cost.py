#!/usr/bin/env python3
"""pump.fun 内盘 bonding curve 成本数学重建（恒定乘积虚拟储备）。

用法：python3 curve_cost.py <curve_owner> --grad-price <外盘首根开盘价USD>
        [--mint <mint>] [--exclude <迁移收币地址,可逗号分隔>] [--list-buyers n]
        [--vs0 30] [--vt0 1073000191] [--decimals 6]
mint 来源：--mint / MINT 环境变量 / 工作目录 config.json 的 mint 字段。
输入：共享 sha256(mint) 路径的 SQD v4 7 元组边＋meta + data/solusdt_1h.json（币安 SOLUSDT 小时K，
      data-api.binance.vision/api/v3/klines 免 key 直连）
输出：data/curve_costs.json {buyer: {tokens, sol_paid, n_buys, first_ts, last_ts}}

精度注记（pipeline §8 curve 重建条，PUB 实测）：
- 买入枚数逐位精确（token 守恒不受 wash 影响）；SOL 成本用标准参数(30/1073M)系统性低估约 10%
  （实际虚拟储备参数偏移）。关键笔（creator 买入等）必须用 getTransaction 的
  preBalances/postBalances 拿链上实付真值校准；批量笔按"重建值 +10% 修正区间"报告
- 毕业迁移笔会混进买家列表（外盘池地址一笔巨量"买入"，SOL 数疑似 wSOL 双计）——
  用 --exclude 剔除迁移收币地址；迁移的真实 SOL 用 GT 外盘开盘价锚定
- 脚本自校准：重建毕业边际价 vs --grad-price 偏差 >20% 告警（参数不匹配）
来源：PUB(Solana) 分析 2026-07-14 收编（参数化）。
"""
import argparse, gzip, json, os, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from spl_edge_core import (EDGE_SCHEMA_FIELDS, EDGE_SEMANTICS,
                           ORDER_GRANULARITY_TX, soltx_cache_paths,
                           validate_edge_row)


def resolve_mint(cli):
    if cli:
        return cli
    if os.environ.get("MINT"):
        return os.environ["MINT"]
    p = Path("config.json")
    if p.exists():
        m = json.loads(p.read_text()).get("mint")
        if m:
            return m
    sys.exit("mint 未指定：--mint / MINT 环境变量 / config.json:mint")


def sol_price_at(ts, sol_klines):
    # sol_klines: [[openTime(ms), o,h,l,c,...], ...]
    for k in sol_klines:
        if k[0] / 1000 <= ts < k[0] / 1000 + 3600:
            return float(k[4])
    return float(sol_klines[-1][4])


def load_edges(mint, data_dir=Path("data")):
    """Load the formal v4 transaction-net cache; legacy rows are not cost evidence."""
    edge_path, meta_path, _parts_path = soltx_cache_paths(mint, data_dir)
    if not meta_path.is_file():
        raise ValueError(f"SQD v4 meta 不存在: {meta_path}")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"SQD v4 meta 非法: {exc}") from exc
    upper = meta.get("finalized_upper_slot")
    if (meta.get("schema") != "sqd-solana-cache/v4"
            or meta.get("version") != 4 or meta.get("mint") != mint
            or meta.get("edge_schema") != list(EDGE_SCHEMA_FIELDS)
            or meta.get("edge_semantics") != EDGE_SEMANTICS
            or meta.get("order_granularity") != ORDER_GRANULARITY_TX
            or meta.get("order_exact") is not False
            or not isinstance(upper, int) or isinstance(upper, bool) or upper < 0):
        raise ValueError("curve_cost 正式链只接受绑定 mint 与 v4 边契约的 SQD meta")
    if not edge_path.is_file() or edge_path.is_symlink():
        raise ValueError(f"SQD v4 边文件缺失或为符号链接: {edge_path}")
    rows = []
    with gzip.open(edge_path, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                rows.append(list(validate_edge_row(row)))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError(f"SQD v4 边文件第 {line_no} 行非法: {exc}") from exc
    if not rows:
        raise ValueError("SQD v4 边文件为空")
    rows.sort(key=lambda edge: (edge[1], edge[2], edge[4], edge[5], str(edge[6])))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("curve_owner", help="内盘 bonding curve 的 owner 地址")
    ap.add_argument("--grad-price", type=float, required=True,
                    help="外盘首根开盘价 USD（GT 分钟/小时K首根，校准锚）")
    ap.add_argument("--mint")
    ap.add_argument("--exclude", default="", help="剔除地址（迁移收币的外盘池等），逗号分隔")
    ap.add_argument("--list-buyers", type=int, default=15)
    ap.add_argument("--vs0", type=float, default=30.0, help="初始虚拟 SOL 储备")
    ap.add_argument("--vt0", type=float, default=1_073_000_191, help="初始虚拟 token 储备（ui 枚）")
    ap.add_argument("--decimals", type=int, default=6)
    args = ap.parse_args()
    mint = resolve_mint(args.mint)
    dec = 10 ** args.decimals
    vt0 = args.vt0 * dec
    k_const = args.vs0 * vt0
    exclude = set(filter(None, args.exclude.split(",")))
    ZERO = "0x" + "0" * 40

    try:
        edges = load_edges(mint)
    except (OSError, ValueError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    sol_k = json.load(open("data/solusdt_1h.json"))

    sold = 0.0  # curve 已净卖出（raw）
    buyers = defaultdict(lambda: {"tokens": 0.0, "sol_paid": 0.0, "n_buys": 0,
                                  "first_ts": None, "last_ts": None})
    total_out = total_in = skipped = 0.0
    for ts, slot, _tx_index, _instr_index, src, dst, amt in edges:
        if src == args.curve_owner and dst != ZERO:
            if dst in exclude:
                skipped += amt
                continue
            vt_before = vt0 - sold
            vt_after = vt_before - amt
            if vt_after <= 0:
                print(f"[WARN] curve 储备耗尽异常 ts={ts}（迁移笔未剔除？用 --exclude）", file=sys.stderr)
                continue
            cost_sol = k_const / vt_after - k_const / vt_before
            b = buyers[dst]
            b["tokens"] += amt
            b["sol_paid"] += cost_sol
            b["n_buys"] += 1
            b["first_ts"] = b["first_ts"] or ts
            b["last_ts"] = ts
            sold += amt
            total_out += amt
        elif dst == args.curve_owner and src != ZERO:
            # 卖回：进度回退（卖家收 SOL，不影响买家成本记账）
            sold -= amt
            total_in += amt

    # 毕业校准
    vt_end = vt0 - sold
    vs_end = k_const / vt_end
    marg_price_sol = vs_end / vt_end * dec  # SOL per token(ui)
    last_ts = max((b["last_ts"] or 0) for b in buyers.values()) if buyers else 0
    solp = sol_price_at(last_ts, sol_k)
    marg_usd = marg_price_sol * solp
    dev = abs(marg_usd - args.grad_price) / args.grad_price
    print(f"curve 净流出 {sold/dec:,.0f} 枚（毛出 {total_out/dec:,.0f} / 回流 {total_in/dec:,.0f}"
          + (f" / 剔除迁移 {skipped/dec:,.0f}" if skipped else "") + "）")
    print(f"重建毕业边际价 ${marg_usd:.4g}（SOL@${solp}） vs 外盘开盘 ${args.grad_price:.4g}"
          f"  偏差 {dev*100:.1f}%"
          + ("  [WARN>20% 参数可能不匹配]" if dev > 0.2 else "  [校准通过；SOL成本仍按+10%区间报告]"))

    out = {a: {**b, "tokens": b["tokens"] / dec} for a, b in
           sorted(buyers.items(), key=lambda kv: -kv[1]["tokens"])}
    json.dump(out, open("data/curve_costs.json", "w"))
    n = args.list_buyers
    print(f"\n内盘买家 {len(out)} 个，top{n}（按买入量）：")
    for a, b in list(out.items())[:n]:
        ft = datetime.fromtimestamp(b["first_ts"], tz=timezone.utc).strftime("%m-%d %H:%M")
        print(f"{a}  买 {b['tokens']:>14,.0f} 枚  付 {b['sol_paid']:>8.3f} SOL  {b['n_buys']:>3}笔  首笔 {ft}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
