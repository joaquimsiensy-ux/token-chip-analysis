#!/usr/bin/env python3
"""行为守门员（gatekeeper，v4.2 2026-07-17）——用资金流形状识别"漏斗型"公共设施，
不依赖任何标签。与静态标签库互补的第二道防线：

  静态库（labels-*.csv）  = 已知设施秒识别（省时间）——但设施是开放集合，永远追不全
  行为守门员（本模块）    = 未知设施兜底（防误判）——漏斗的行为学特征是封闭知识：
                            多进多出、过手不留存、对手方分散。交易所热钱包/桥/路由/
                            分发器不管叫什么名字，资金流形状都是漏斗；庄家是水库
                            （进得多出得少、对手方集中）。

设计纪律：
1. 判定只用分析时已采集的转账数据（cluster.py 的 rows），零额外 RPC 成本。
2. FUNNEL 命中 ≠ 从数据删除：只禁作聚类合并边 + 建议持仓单列，与标签库 exclude 同语义；
   全部命中落 gatekeeper_blocked 对账清单，防误伤不可审计。
3. 保守优先：阈值宁可漏拦（漏网还有标签库+人工复核两道），不可误杀真庄家的分发钱包——
   庄家分发钱包的特征是"出得多但对手方少且集中/留存高/入度极小"，与漏斗可区分。
4. FUNNEL 且未命中静态库 → 自动入 miss 队列（append_misses），人工确认后回填标签库。
   行为发现 → 人工审 → 静态库成长，是库最健康的扩容闭环。

用法（模块）：
    from gatekeeper import funnel_scan
    verdicts = funnel_scan(rows)          # rows = [(from, to, value_int), ...]
    verdicts[addr] -> {'verdict': 'FUNNEL'|'FUNNEL_CANDIDATE'|None, ...指纹字段}

用法（CLI，人工核查单个数据目录）：
    python3 gatekeeper.py <chain> [数据目录]   # 读 <chain>_part_*.csv，打印 FUNNEL 榜
"""
import glob
import os
import sys
from collections import defaultdict

# ---- 阈值（2026-07-17 用 bibi(BSC)+TRASH(Robinhood) 历史数据校准；改动须重跑校准） ----
TH = {
    'FI_MIN': 30,        # FUNNEL: 最小唯一上游数
    'FO_MIN': 30,        # FUNNEL: 最小唯一下游数
    'RET_MAX': 0.05,     # FUNNEL: 净留存率上限（流入的 ≤5% 留在手里）
    'MIN_FLOW_TX': 80,   # FUNNEL: 最小总笔数（低频地址不判，样本不足）
    'CAND_DEG': 120,     # 候选: 唯一对手方总数下限
    'CAND_RET': 0.15,    # 候选: 净留存率上限
}


def funnel_profile(rows, addr_filter=None):
    """从转账三元组算每地址行为指纹。
    rows: iterable of (from_addr, to_addr, value_int)，地址须已小写规范化。
    addr_filter: 可选 set——只对这些地址产出指纹（省内存；None=全量）。
    返回 {addr: profile dict}。"""
    inflow = defaultdict(int)
    outflow = defaultdict(int)
    tx_in = defaultdict(int)
    tx_out = defaultdict(int)
    peers_in = defaultdict(set)
    peers_out = defaultdict(set)
    peer_flow = defaultdict(lambda: defaultdict(int))   # addr -> peer -> 双向流量

    for f, t, v in rows:
        if addr_filter is None or t in addr_filter:
            inflow[t] += v
            tx_in[t] += 1
            peers_in[t].add(f)
            peer_flow[t][f] += v
        if addr_filter is None or f in addr_filter:
            outflow[f] += v
            tx_out[f] += 1
            peers_out[f].add(t)
            peer_flow[f][t] += v

    out = {}
    for a in set(list(inflow) + list(outflow)):
        inf, ouf = inflow[a], outflow[a]
        total_flow = inf + ouf
        if not total_flow:
            continue
        retention = max(0, inf - ouf) / inf if inf else 1.0
        pf = peer_flow[a]
        top_peer_share = max(pf.values()) / total_flow if pf else 0.0
        out[a] = {
            'fan_in': len(peers_in[a]), 'fan_out': len(peers_out[a]),
            'tx_in': tx_in[a], 'tx_out': tx_out[a],
            'inflow': inf, 'outflow': ouf,
            'retention': round(retention, 4),
            'top_peer_share': round(top_peer_share, 4),
        }
    return out


def classify(p):
    """指纹 → 判定。返回 'FUNNEL' | 'FUNNEL_CANDIDATE' | None。
    FUNNEL          多进多出 + 过手不留存 + 笔数足够 → 自动禁边（与标签 exclude 同语义）
    FUNNEL_CANDIDATE 形状可疑但证据不足 → 只提示，不自动决策"""
    txs = p['tx_in'] + p['tx_out']
    if (p['fan_in'] >= TH['FI_MIN'] and p['fan_out'] >= TH['FO_MIN']
            and p['retention'] <= TH['RET_MAX'] and txs >= TH['MIN_FLOW_TX']):
        return 'FUNNEL'
    if (p['fan_in'] + p['fan_out'] >= TH['CAND_DEG']
            and p['retention'] <= TH['CAND_RET']):
        return 'FUNNEL_CANDIDATE'
    return None


def funnel_scan(rows, addr_filter=None, exempt=None):
    """一步到位：指纹 + 判定。exempt: 已知实体地址集合（惯犯/团队等，永不判 FUNNEL——
    它们的形状由案源证据定性，不由本模块）。返回只含命中地址的 dict。"""
    exempt = exempt or set()
    verdicts = {}
    for a, p in funnel_profile(rows, addr_filter).items():
        if a in exempt:
            continue
        v = classify(p)
        if v:
            p['verdict'] = v
            verdicts[a] = p
    return verdicts


def _cli():
    chain = sys.argv[1] if len(sys.argv) > 1 else 'bsc'
    d = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    rows = []
    seen = set()
    for p in glob.glob(os.path.join(d, f'{chain}_part_*.csv')):
        for line in open(p):
            parts = line.strip().split(',')
            if len(parts) == 6 and parts[0] != 'block':
                k = (parts[1], parts[2])
                if k in seen:
                    continue
                seen.add(k)
                rows.append((parts[3].lower(), parts[4].lower(), int(parts[5])))
    print(f'{len(rows)} 条转账（去重后）')
    verdicts = funnel_scan(rows)
    strong = {a: p for a, p in verdicts.items() if p['verdict'] == 'FUNNEL'}
    cand = {a: p for a, p in verdicts.items() if p['verdict'] == 'FUNNEL_CANDIDATE'}
    print(f'FUNNEL {len(strong)} | CANDIDATE {len(cand)}')
    for a, p in sorted(strong.items(), key=lambda x: -(x[1]['tx_in'] + x[1]['tx_out']))[:25]:
        print(f"  {a} in{p['fan_in']}/out{p['fan_out']} tx{p['tx_in']+p['tx_out']} "
              f"ret={p['retention']:.3f} top_peer={p['top_peer_share']:.2f}")


if __name__ == '__main__':
    _cli()
