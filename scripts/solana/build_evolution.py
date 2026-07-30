#!/usr/bin/env python3
"""重建各阵营持仓占比演变序列（图1/图2 数据源）。

方法（免全量边的锚点法）：
- 79 个深挖实体：用逐笔流水在时间轴累积重建各自持仓（精确）
- 流动性池：用 550 锚点的 pool_balance 曲线（精确）
- 散户/其他 = 总供应 - 已知实体 - 池子 - 销毁（残差）
- 在 N 个等距时间点采样，每个实体持仓取该时点前最后一笔累积值

输入: data/whale_deep.json, data/decoded_anchors.jsonl, data/entity_camps.json(阵营归属)
输出: data/camp_series.json (camp_share_series 格式), data/whale_series.json (图2 各实体线)
"""
import json, sys
from datetime import datetime, timezone
from pathlib import Path

import json as _json
from pathlib import Path as _Path
# 标的参数从工作目录 config.json 读（铁律5：不写死进 skill）
# config.json 需含：total_supply, decimals, launch_ts, data_cutoff_ts, burn_amount(可选,单列锁仓/销毁)
_cfg = _json.loads(_Path("config.json").read_text()) if _Path("config.json").exists() else {}
TOT = _cfg.get("total_supply", 0)
DECIMALS = 10 ** _cfg.get("decimals", 6)
LAUNCH = _cfg.get("launch_ts", 0)
NOW = _cfg.get("data_cutoff_ts", 0)
BURN_AMOUNT = _cfg.get("burn_amount", 0)  # dev/团队烧毁量(raw)，单列锁仓/销毁阵营

POOLS = {'731zVBbXuXvrom3XNGw8bUAgETBbVvzYzDUqSnqpRspM','HdTXiwhqPTFFriGDndoaFAaPNGSERXSFUDirxj1m8N42',
         '33ENUgyS4SzJDQy3ttPXryXS1zv31QX5odjankhFhdqx','9owQTEx4W6fZY1ZBgDZ5ipAnWjkBS6jhvMoTcRuVZCoe',
         'BLEqaWU9PT7jxosX5JKiEZhRYUs3FhXtDh57y8QmAUZk','Edmun6LKgFbwk4YLwabCr41MSG54b4zBz3APSDaXfmkE',
         'DNhZ4DVr6DEu64MeRj4de92syU3qyJrs63iavrr4fzrx','6xsbqrKH7capCokhVyrMfe1Civdykzizvf7pL69tgwSr',
         'GGDhBnUtfemzcAEBZkBk49bH2C7eoN7Dbs6SQiV56oGS'}

def main():
    deep = json.load(open('data/whale_deep.json'))
    camps = json.load(open('data/entity_camps.json'))  # {addr: camp_name}

    # 阵营定义标签体检（v4 2026-07-17）：人工归属的实体阵营里若混进已知设施
    # （CEX/桥/程序/locker），阵营占比会整体失真——启动即拦截提示，比出图后返工省一轮
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'labels'))
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
    for l in open('data/decoded_anchors.jsonl'):
        d = json.loads(l)
        if d.get('decode_fail') or d.get('pool_balance') is None or not d.get('ts'): continue
        # pool_balance 是主池；其他池子小，近似只用主池
        pool_pts.append((d['ts'], d['pool_balance'] * DECIMALS))
    pool_pts.sort()

    def interp(pts, ts):
        """取 ts 前最后一个点的值（阶梯插值）。"""
        lo, hi = 0, len(pts)
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
    whale_series = {}  # 每个标签实体单独一条线（图2）

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

    json.dump(series, open('data/camp_series.json', 'w'), ensure_ascii=False, indent=1)
    print(f"演变序列 {len(series)} 点，阵营: {all_camps}")
    # 末点各阵营占比
    last = series[-1]
    print("末点各阵营占比:")
    for c in all_camps + ['流动性池', '散户']:
        if c in last and last[c] > 0.01:
            print(f"  {c}: {last[c]:.2f}%")

if __name__ == "__main__":
    main()
