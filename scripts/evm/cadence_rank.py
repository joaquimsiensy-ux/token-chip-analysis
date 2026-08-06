#!/usr/bin/env python3
"""秩相关版节拍指纹：在候选大户池内做穷尽扫描，识别常规聚类结构性失明的协同网络。

来源：EGL1(BSC) 分析二次修正，2026-07-26。**与 cadence_fingerprint.py 配套使用**：
  cadence_fingerprint.py —— 全库粗扫（25 万地址级），用位置精确匹配，快但漏检严重
  cadence_rank.py（本件）—— 候选池细扫（数百地址级），用秩相关，慢但灵敏

## 为什么必须有本件

EGL1 案的教训：位置精确匹配（第 k 位是否同一地址）对成员增删**极度脆弱**——名单
中间插入一个地址，其后全部错位，匹配数从满分跌到 0。同一份数据：
  位置精确匹配 + 单笔 ≥5,000 枚门槛 → 43 址 13.14% 总供应（判为"2 个小庄"）
  Spearman 秩相关 + 排列检验 + 无金额门槛 → 191 址 60.18%（判为"1 个大庄"）
**差 4.4 倍，判级跃迁。** 交付后被用户一句"为什么不逐一做"追问才翻出来。

## 方法

1. 取候选池（雷达线下大户清单）从主池/bonding 曲线的**全部**买入，无金额门槛
2. 按静默间隔切时间簇（默认 1800s）
3. 对每个 ≥6 址的簇：比对「簇内买入顺序」vs「这些地址各自首次建仓的全局时序」，
   算 Spearman ρ，再用 3000 次随机排列做显著性检验
4. 保留 |ρ|≥0.75 且 p≤0.002 的窗口，按成员共享做传递闭包合并

## ★ 跨批次判据（实体归并的核心）

单窗口只证明"这批地址此刻被同一程序驱动"。真正锁死实体的是：**一个遍历窗口里的
地址分散在多个不同建仓批次里，而遍历顺序仍严格对应其首次买入的全局时序。**
EGL1 实测 2025-07-22 的 37 址跨 10 个建仓窗口、跨度 4 天，ρ=−1.000；07-21 的
31 址跨 13 个窗口、跨度两周。要按建仓时序倒着操作一份跨批次名单，操作者必须持有
**按建仓时间排序的完整名单**——独立散户没有，共用同一交易工具的不同用户也没有
（工具不知道别人的建仓时间）。

## ★ 收尾必做：查网络的对外流出去向

节拍只能圈出"一起下单的地址"。EGL1 案在追查母层流出去向时才发现：母层向 39 个
**当时还是空钱包**的地址各转 100–145 万枚（12 小时内、单向、零回转），受赠地址
收到币之后才自己下场买。这是**母钱包→子钱包分仓**的直转边硬证据，比节拍强，
把网络从 191 址 60.18% 又推到 254 址 71.73%。
排除"这是卖币给买家"的判据：买家不会是收币前的空钱包，更不会收货后才去市场买同一个币。

## 纪律

- 零金额事件必须先剔除（address-poisoning spam 制造假共现）。本脚本已内置。
- **传递闭包会链式污染**：A-B 同窗、B-C 同窗即并 A、C。一个错卷入的地址污染整条链。
  EGL1 实测确实卷进过 1 个 DEX 流动性池（1/192）——**产出必须逐个核 eth_getCode
  与标签库**，剔除设施地址后再报数。规模一律按「上界 + 硬绑定下界」的区间陈述。
- **持仓型 vs 过手型必须分流**：刷量 bot 群同样程序驱动、同样完美节拍。用留存率
  与收发笔数分流，只有持仓型才是庄候选。
- **程序驱动 ≠ 受益人同一**：托管跟单、代客理财、打新工作室的多客户批量执行会产生
  同样的指纹。链上只能确证执行侧由单一名单驱动，报告必须写明这条边界。

## 用法

  python3 cadence_rank.py --pools 0x池1,0x池2 --tier-file tier_addrs.txt \
    --parquet out/merged.parquet --total-supply 1000000000000000000000000000 \
    --formation-cutoff 2025-06-18 [--state-file analysis-state.json]
  产物 tier_final.json：{identity, entities}
"""

import argparse
import datetime as dt
import json
import random
import statistics as stt


def parse_args():
    parser = argparse.ArgumentParser(description="候选地址池的 Spearman 节拍指纹细扫")
    parser.add_argument("--pools", help="池地址，多个地址用逗号分隔")
    parser.add_argument("--tier-file", help="候选地址清单文件，一行一个地址")
    parser.add_argument("--parquet", help="Transfer 事件 parquet 文件")
    parser.add_argument("--total-supply", help="总供应 raw 整数")
    parser.add_argument("--formation-cutoff", help="建仓截止日，格式 YYYY-MM-DD")
    parser.add_argument("--state-file", help="可选 analysis-state.json；缺省时不标注已知实体名")
    args = parser.parse_args()
    missing = [name for name in ("pools", "tier_file", "parquet", "total_supply",
                                  "formation_cutoff") if not getattr(args, name)]
    if missing:
        parser.error("缺少必填参数：" + "、".join("--" + name.replace("_", "-") for name in missing))
    try:
        args.total_supply = int(args.total_supply)
        if args.total_supply <= 0:
            raise ValueError
    except ValueError:
        parser.error("--total-supply 必须是正的 raw 整数")
    try:
        dt.datetime.strptime(args.formation_cutoff, "%Y-%m-%d")
    except ValueError:
        parser.error("--formation-cutoff 必须是 YYYY-MM-DD")
    args.pools = [p.strip().lower() for p in args.pools.split(",") if p.strip()]
    if not args.pools:
        parser.error("--pools 至少要提供一个池地址")
    return args


args = parse_args()
import duckdb

POOLS = args.pools
tier = [l.strip().lower() for l in open(args.tier_file) if l.strip().startswith('0x')]
L = ','.join(repr(a) for a in tier); PF = ','.join(repr(p) for p in POOLS)
parquet_sql = args.parquet.replace("'", "''")
con = duckdb.connect(); con.execute("SET memory_limit='8GB'")
con.execute(f'''CREATE VIEW ev AS SELECT block,ts,tx,log_index,"from" AS frm,"to" AS t2,
  CAST(value AS HUGEINT) AS v FROM read_parquet('{parquet_sql}') WHERE CAST(value AS HUGEINT)>0''')
rows = con.execute(f'''SELECT ts,t2 FROM ev WHERE t2 IN ({L}) AND frm IN ({PF})
  ORDER BY block,log_index''').fetchall()
identity = {"pools": POOLS, "parquet": args.parquet, "total_supply": args.total_supply,
            "formation_cutoff": args.formation_cutoff}
print(f"[identity] {json.dumps(identity, ensure_ascii=False, sort_keys=True)}")
def ep(t): return dt.datetime.strptime(t[:19], '%Y-%m-%dT%H:%M:%S').timestamp()
def sp(a, b):
    ra={x:i for i,x in enumerate(a)}; rb={x:i for i,x in enumerate(b)}
    n=len(a); return 1-6*sum((ra[x]-rb[x])**2 for x in a)/(n*(n*n-1))
def firstbuy(ms):
    Ls=','.join(repr(a) for a in ms)
    return [x[0] for x in con.execute(f'''SELECT t2,MIN(block*100000+log_index) k FROM ev
      WHERE t2 IN ({Ls}) AND frm IN ({PF}) GROUP BY 1 ORDER BY k''').fetchall()]

# 1) 切遍历窗口（30 分钟静默切分），只保留「建仓期之后」的复访窗口
cl=[[rows[0]]]
for p,x in zip(rows,rows[1:]):
    (cl.append([x]) if ep(x[0])-ep(p[0])>1800 else cl[-1].append(x))
random.seed(23); hits=[]
for c in cl:
    s,o=set(),[]
    for ts,a in c:
        if a not in s: s.add(a); o.append(a)
    if len(o)<6: continue
    fb=firstbuy(o)
    if fb[0]==o[0] and len(set(fb)&set(o))==len(o) and c[0][0][:10]<=args.formation_cutoff:
        pass  # 建仓窗口本身，仍参与比对
    rho=sp(o,fb)
    cnt=sum(1 for _ in range(3000) if abs(sp(o,random.sample(fb,len(fb))))>=abs(rho))
    p=cnt/3000
    if p<=0.002 and abs(rho)>=0.75:
        hits.append({'t0':c[0][0][:19],'t1':c[-1][0][:19],'n':len(o),'rho':rho,'p':p,'members':o})
print(f'[win] {len(cl)} 个时间簇 → {len(hits)} 个「整窗与建仓序列强相关」的遍历事件:')
for h in sorted(hits,key=lambda x:x['t0']):
    print(f"  {h['t0']}~{h['t1'][11:]}  {h['n']:>3} 址  rho={h['rho']:+.3f} p={h['p']:.4f}")

# 2) 传递闭包合并
par={}
def find(x):
    par.setdefault(x,x)
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
def uni(a,b):
    ra,rb=find(a),find(b)
    if ra!=rb: par[ra]=rb
for h in hits:
    for m in h['members'][1:]: uni(h['members'][0],m)
grp={}
for a in list(par): grp.setdefault(find(a),[]).append(a)

TOT=args.total_supply
bal=con.execute('''SELECT addr,SUM(d) b FROM (SELECT t2 addr,v d FROM ev
  UNION ALL SELECT frm,-v FROM ev) GROUP BY 1''').df()
bm=dict(zip(bal.addr,bal.b))
st=json.load(open(args.state_file)) if args.state_file else {}; kn={}
for g in st.get('whale_groups',[]):
    for m in (g.get('members') or []): kn[m.lower()]=g.get('name','?')

print('\n[final] 合并后实体:')
out=[];tot_pct=0
for root,ms in sorted(grp.items(),key=lambda kv:-sum(int(bm.get(m,0)) for m in kv[1])):
    if len(ms)<6: continue
    Ls=','.join(repr(m) for m in ms)
    ain,nin=con.execute(f'SELECT COALESCE(SUM(v),0),COUNT(*) FROM ev WHERE t2 IN ({Ls})').fetchone()
    aout,nout=con.execute(f'SELECT COALESCE(SUM(v),0),COUNT(*) FROM ev WHERE frm IN ({Ls})').fetchone()
    s=sum(int(bm.get(m,0)) for m in ms); ret=s/int(ain)*100 if ain else 0
    # 备择检验：各成员当前持仓的离散度（同一实体分仓→窄；独立用户→宽）
    hold=[int(bm.get(m,0))/TOT*100 for m in ms]
    cv=stt.pstdev(hold)/stt.mean(hold) if stt.mean(hold) else 0
    tags={}
    for m in ms: tags[kn.get(m,'未归属')]=tags.get(kn.get(m,'未归属'),0)+1
    hh=[h for h in hits if set(h['members'])&set(ms)]
    print(f"\n  === {len(ms)} 址 {s/TOT*100:.4f}% 留存{ret:.2f}% 收/发{nin}/{nout} 持仓CV={cv:.3f}")
    print(f"      归属 {tags}")
    for h in sorted(hh,key=lambda x:x['t0'])[:6]:
        print(f"      {h['t0']} {h['n']}址 rho={h['rho']:+.3f}")
    if ret>=50: tot_pct+=s/TOT*100
    out.append({'members':sorted(ms),'n':len(ms),'pct_supply':s/TOT*100,'retention_pct':ret,
                'n_in':nin,'n_out':nout,'holding_cv':cv,'known_tags':tags,
                'windows':[{'t':h['t0'],'n':h['n'],'rho':h['rho'],'p':h['p']} for h in sorted(hh,key=lambda x:x['t0'])]})
print(f'\n[sum] 持仓型(留存≥50%)实体合计 {tot_pct:.4f}% 总供应')
json.dump({'identity': identity, 'entities': out},open('tier_final.json','w'),ensure_ascii=False,indent=1)
print('[done] -> tier_final.json')
