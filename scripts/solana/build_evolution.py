#!/usr/bin/env python3
"""重建各阵营持仓占比演变序列（图1/图2 数据源）。

方法（免全量边的锚点法）：
- 79 个深挖实体：用逐笔流水在时间轴累积重建各自持仓（精确）
- 流动性池：用 550 锚点的 pool_balance 曲线（精确）
- 散户/其他 = 总供应 - 已知实体 - 池子 - 销毁（残差）
- 在 N 个等距时间点采样，每个实体持仓取该时点前最后一笔累积值

输入: data/whale_deep.json, data/decoded_anchors.jsonl, data/entity_camps.json(阵营归属)
输出: data/camp_series.json (camp_share_series 格式)
      + data/camp_series.input_manifest.json（配置与全部输入身份）

本脚本是锚点小样本辅助入口，默认最多 5,000 个实体、200,000 条锚点；亿级正式
Transfer 重放必须走 replay_edges.py/DuckDB，不得在这里全量装内存。
"""
import hashlib, json, os, sys
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path

# 标的参数从工作目录 config.json 读（铁律5：不写死进 skill）
# config.json 需含：total_supply, decimals, launch_ts, data_cutoff_ts, burn_amount(可选,单列锁仓/销毁)
CONFIG_PATH = Path("config.json")
if not CONFIG_PATH.is_file():
    sys.exit("缺 config.json：total_supply/decimals/launch_ts/data_cutoff_ts 均为必填")
_cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def required_int(name, *, minimum=0, maximum=None):
    value = _cfg.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        sys.exit(f"config.{name} 必须是 >= {minimum} 的整数")
    if maximum is not None and value > maximum:
        sys.exit(f"config.{name} 必须 <= {maximum}")
    return value


TOT = required_int("total_supply", minimum=1)
DECIMAL_PLACES = required_int("decimals", minimum=0, maximum=30)
DECIMALS = 10 ** DECIMAL_PLACES
LAUNCH = required_int("launch_ts", minimum=1)
NOW = required_int("data_cutoff_ts", minimum=1)
if NOW <= LAUNCH:
    sys.exit("config.data_cutoff_ts 必须晚于 launch_ts")
BURN_AMOUNT = _cfg.get("burn_amount", 0)
if isinstance(BURN_AMOUNT, bool) or not isinstance(BURN_AMOUNT, int) or not 0 <= BURN_AMOUNT <= TOT:
    sys.exit("config.burn_amount 必须是 0..total_supply 的整数 raw amount")
MAX_ENTITIES = _cfg.get("max_entities", 5_000)
MAX_ANCHORS = _cfg.get("max_anchor_rows", 200_000)
MAX_DEEP_ROWS = _cfg.get("max_deep_rows", 2_000_000)
MAX_INPUT_BYTES = _cfg.get("max_input_bytes", 512 * 1024 * 1024)
for _name, _value in (("max_entities", MAX_ENTITIES), ("max_anchor_rows", MAX_ANCHORS),
                      ("max_deep_rows", MAX_DEEP_ROWS), ("max_input_bytes", MAX_INPUT_BYTES)):
    if isinstance(_value, bool) or not isinstance(_value, int) or _value <= 0:
        sys.exit(f"config.{_name} 必须是正整数")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    input_paths = [Path('data/whale_deep.json'), Path('data/decoded_anchors.jsonl'),
                   Path('data/entity_camps.json')]
    missing = [str(p) for p in input_paths if not p.is_file()]
    if missing:
        sys.exit(f"缺输入文件: {missing}")
    oversized = [str(p) for p in input_paths if p.stat().st_size > MAX_INPUT_BYTES]
    if oversized:
        sys.exit(f"小样本输入文件超过 {MAX_INPUT_BYTES} bytes: {oversized}")
    deep = json.load(open(input_paths[0]))
    camps = json.load(open(input_paths[2]))  # {addr: camp_name}
    if not isinstance(deep, dict) or not deep:
        sys.exit("data/whale_deep.json 必须是非空对象")
    if not isinstance(camps, dict) or not camps:
        sys.exit("data/entity_camps.json 必须是非空对象")
    if len(deep) > MAX_ENTITIES:
        sys.exit(f"小样本上限：实体 {len(deep)} > {MAX_ENTITIES}；正式重放请用 replay_edges.py/DuckDB")
    deep_rows = 0
    for addr, value in deep.items():
        if not isinstance(value, dict) or not isinstance(value.get('rows'), list):
            sys.exit(f"whale_deep 条目缺 rows 列表: {addr}")
        deep_rows += len(value['rows'])
        if deep_rows > MAX_DEEP_ROWS:
            sys.exit(f"小样本上限：实体流水 > {MAX_DEEP_ROWS}；正式重放请用 replay_edges.py/DuckDB")

    # 阵营定义标签体检（v4 2026-07-17）：人工归属的实体阵营里若混进已知设施
    # （CEX/桥/程序/locker），阵营占比会整体失真——启动即拦截提示，比出图后返工省一轮
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'labels'))
    try:
        from labels_resolver import LabelResolver, blind_serial_env, seal_serial_hits, blind_notice
        _resv = LabelResolver('sol')
        if not _resv.warn_if_degraded():
            _bad, _sealed = [], []
            for _a, _camp in camps.items():
                _r = _resv.get(_a)
                if _r and _r['tier'] == 'exclude' and _camp not in ('流动性池', '散户'):
                    _bad.append((_a, _camp, _r['name'], _r['category']))
                elif _r and _r.get('serial'):
                    if blind_serial_env():   # A5 盲化：惯犯命中封存不打印（复核期 --unseal 揭盲）
                        _sealed.append({'chain': 'sol', 'address': _a, 'camp': _camp,
                                        **{k: v for k, v in _r.items()}})
                    else:
                        print(f"🚨 阵营体检: {_a[:16]}…({_camp}) 命中惯犯层 {_r['name'][:40]}——立即调案源比对")
            if blind_serial_env():
                blind_notice(seal_serial_hits(_sealed, '.', 'sol build_evolution 阵营体检'))
            if _bad:
                print('⚠️ 阵营体检: 以下地址是已知公共设施，混在实体阵营会让占比失真（核实后剔除或改归池子桶）:')
                for _a, _camp, _n, _c in _bad:
                    print(f'   {_a} [{_camp}] = {_n[:44]} <{_c}>')
    except ImportError:
        print('[labels][degraded_mode] labels_resolver 导入失败——阵营体检跳过', file=_sys.stderr)

    # 每个实体的累积持仓序列 [(ts, cum_raw)]
    ent_series = {}
    for addr, v in deep.items():
        rows = sorted(v.get('rows', []), key=lambda r: r['blockTime'])
        cum = 0; pts = [(LAUNCH, 0)]
        for r in rows:
            cum += r['delta_raw']
            pts.append((r['blockTime'], cum))
        ent_series[addr] = pts

    # 池子余额锚点序列
    pool_pts = []
    anchor_rows = 0
    for l in open(input_paths[1]):
        anchor_rows += 1
        if anchor_rows > MAX_ANCHORS:
            sys.exit(f"小样本上限：锚点 > {MAX_ANCHORS}；请改用 streaming/DuckDB 正式入口")
        d = json.loads(l)
        if d.get('decode_fail') or d.get('pool_balance') is None or not d.get('ts'): continue
        # pool_balance 是主池；其他池子小，近似只用主池
        raw = d.get('pool_balance_raw')
        if raw is None:  # legacy decoder output
            raw = int(Decimal(str(d['pool_balance'])) * DECIMALS)
        pool_pts.append((d['ts'], int(raw)))
    pool_pts.sort()
    if not pool_pts:
        sys.exit("decoded_anchors 没有可用的非 decode_fail 池余额锚点")

    def interp(pts, ts):
        """取 ts 前最后一个点的值（阶梯插值）。"""
        val = pts[0][1]
        for t, v in pts:
            if t <= ts: val = v
            else: break
        return val

    # 采样时间点（等距 400 点）
    N = 400
    times = [LAUNCH + int((NOW - LAUNCH) * i / (N-1)) for i in range(N)]

    # 阵营列表
    all_camps = sorted(set(camps.values()))
    series = []
    for ts in times:
        row = {"ts": datetime.fromtimestamp(ts, timezone.utc).isoformat()}
        camp_raw = {c: 0 for c in all_camps}
        for addr, pts in ent_series.items():
            bal = max(0, interp(pts, ts))
            camp = camps.get(addr, '散户')
            camp_raw[camp] = camp_raw.get(camp, 0) + bal
        pool_bal = interp(pool_pts, ts) if pool_pts else 0
        camp_raw['流动性池'] = pool_bal
        # dev 烧毁 34,199,203 枚 LAYOFF，发射后即恒定（锁仓/销毁单列）
        if BURN_AMOUNT:
            camp_raw['锁仓/销毁'] = BURN_AMOUNT  # config.burn_amount (raw)
        known = sum(camp_raw.values())
        camp_raw['散户'] = camp_raw.get('散户', 0) + max(0, TOT - known)
        for c, raw in camp_raw.items():
            row[c] = round(raw / TOT * 100, 4)
        series.append(row)

    result_path = Path('data/camp_series.json')
    with result_path.open('w', encoding='utf-8') as f:
        json.dump(series, f, ensure_ascii=False, indent=1)
        f.write('\n')
    manifest = {
        "schema": "solana-camp-series-inputs/v1",
        "small_sample_only": True,
        "limits": {"max_entities": MAX_ENTITIES, "max_anchor_rows": MAX_ANCHORS,
                   "max_deep_rows": MAX_DEEP_ROWS, "max_input_bytes": MAX_INPUT_BYTES},
        "config": {"path": str(CONFIG_PATH.resolve()), "sha256": sha256_file(CONFIG_PATH),
                   "total_supply": TOT, "decimals": DECIMAL_PLACES,
                   "launch_ts": LAUNCH, "data_cutoff_ts": NOW},
        "inputs": [{"path": str(p.resolve()), "sha256": sha256_file(p)} for p in input_paths],
        "counts": {"entities": len(deep), "deep_rows": deep_rows, "camps": len(camps),
                   "anchor_rows": anchor_rows, "usable_pool_anchors": len(pool_pts)},
        "output": {"path": str(result_path.resolve()), "sha256": sha256_file(result_path),
                   "rows": len(series)},
    }
    with open('data/camp_series.input_manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')
    print(f"演变序列 {len(series)} 点，阵营: {all_camps}")
    # 末点各阵营占比
    last = series[-1]
    print("末点各阵营占比:")
    for c in all_camps + ['流动性池', '散户']:
        if c in last and last[c] > 0.01:
            print(f"  {c}: {last[c]:.2f}%")

if __name__ == "__main__":
    main()
