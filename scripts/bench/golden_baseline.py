#!/usr/bin/env python3
"""黄金基线工具（A1 回归门禁）：对重放链路产物算规范化指纹，跨引擎逐字段对表。

来源：2026-07-22 DuckDB 引擎改造工程（@CX 交叉复核方案 A1——先建"可证明等价"
的基线，再做任何性能优化，防"快了但数字错了"）。

用法：
  python3 golden_baseline.py snapshot <data_dir> --out <baseline.json> [--tag 说明]
  python3 golden_baseline.py compare <a.json> <b.json>

snapshot 收集（存在哪个算哪个，缺文件记 null）：
  replay_stats.json   -> 原样嵌入（供给闭合/负余额数/gate 等硬指标）
  balances_final.json -> 条数 + 规范化 sha256
  peaks.json / mint_ledger.json / camp_series.json / entity_series.json -> 同上
  merged.csv          -> 数据行数 + 全行流式 sha256（跳表头）

规范化：json 解析后 sort_keys + 紧凑分隔符重序列化再哈希——与产出引擎的
键序/缩进/浮点尾随格式无关，只比语义内容。

compare 退出码：0=全等 1=有差异 2=输入错误（fail-closed：缺文件不算等）。
"""
import argparse, hashlib, json, os, sys

PRODUCTS = ["balances_final.json", "peaks.json", "mint_ledger.json",
            "camp_series.json", "entity_series.json"]


def canon_hash(obj):
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode()).hexdigest()


def file_lines_hash(path):
    """merged.csv：数据行数 + 流式 sha256（跳首行表头）。"""
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as f:
        first = True
        for line in f:
            if first:
                first = False
                continue
            h.update(line)
            n += 1
    return n, h.hexdigest()


def snapshot(data_dir, tag=""):
    out = {"tag": tag, "data_dir": os.path.abspath(data_dir)}
    sp = os.path.join(data_dir, "replay_stats.json")
    out["replay_stats"] = json.load(open(sp)) if os.path.exists(sp) else None
    for name in PRODUCTS:
        p = os.path.join(data_dir, name)
        key = name.replace(".json", "")
        if not os.path.exists(p):
            out[key] = None
            continue
        obj = json.load(open(p))
        n = len(obj.get("dates", [])) if "series" in name else len(obj)
        out[key] = {"n": n, "sha256": canon_hash(obj)}
    mp = os.path.join(data_dir, "merged.csv")
    if os.path.exists(mp):
        n, h = file_lines_hash(mp)
        out["merged_csv"] = {"rows": n, "sha256": h}
    else:
        out["merged_csv"] = None
    return out


# replay_stats 的对表契约键（两引擎必须逐字段相等）；此外的键视为引擎自有扩展
# （如 DuckDB 引擎的 reject 记账 n_source_rows 等），只展示不判等。
STATS_CONTRACT = ["events", "mint_total_wei", "burn_total_wei", "sum_balances_wei",
                  "zero_event_inflow_wei", "dead_event_inflow_wei",
                  "dead_event_outflow_wei", "dead_sink_net_wei",
                  "supply_check_ok", "neg_balance_addrs", "unique_addrs", "gate_pass"]


def compare(pa, pb):
    a, b = json.load(open(pa)), json.load(open(pb))
    keys = ["replay_stats", "merged_csv"] + [n.replace(".json", "") for n in PRODUCTS]
    fails = []
    for k in keys:
        va, vb = a.get(k), b.get(k)
        if k == "replay_stats" and va is not None and vb is not None:
            diff = {x: (va.get(x), vb.get(x)) for x in STATS_CONTRACT
                    if va.get(x) != vb.get(x)}
            extra = sorted((set(va) | set(vb)) - set(STATS_CONTRACT))
            if diff:
                fails.append(k)
                print(f"  FAIL  {k}: 契约字段差异 {diff}")
            else:
                print(f"  PASS  {k}（契约 {len(STATS_CONTRACT)} 键全等"
                      f"{'；扩展字段忽略: ' + ','.join(extra) if extra else ''}）")
            continue
        if va == vb and va is not None:
            print(f"  PASS  {k}")
        elif va is None or vb is None:
            fails.append(k)
            print(f"  FAIL  {k}: {'A缺' if va is None else 'B缺'}产物（fail-closed：缺=不等）")
        else:
            fails.append(k)
            print(f"  FAIL  {k}: A(n={va.get('n', va.get('rows'))}, {str(va.get('sha256'))[:12]}…) "
                  f"vs B(n={vb.get('n', vb.get('rows'))}, {str(vb.get('sha256'))[:12]}…)")
    if fails:
        print(f"[基线对表] FAIL：{len(fails)} 项不等 -> {fails}")
        return 1
    print(f"[基线对表] PASS：{len(keys)} 项全等（A={a.get('tag')} B={b.get('tag')}）")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("snapshot")
    s1.add_argument("data_dir")
    s1.add_argument("--out", required=True)
    s1.add_argument("--tag", default="")
    s2 = sub.add_parser("compare")
    s2.add_argument("a")
    s2.add_argument("b")
    args = ap.parse_args()
    if args.cmd == "snapshot":
        snap = snapshot(args.data_dir, args.tag)
        json.dump(snap, open(args.out, "w"), indent=1, ensure_ascii=False)
        present = [k for k, v in snap.items() if v is not None and k not in ("tag", "data_dir")]
        print(f"[基线快照] {args.data_dir} -> {args.out}（收 {len(present)} 项: {present}）")
    else:
        sys.exit(compare(args.a, args.b))


if __name__ == "__main__":
    raise SystemExit(main())
