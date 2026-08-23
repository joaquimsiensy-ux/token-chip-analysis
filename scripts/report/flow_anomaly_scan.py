#!/usr/bin/env python3
"""flow_anomaly_scan.py — 资金流异常扫描器：汇集点＋分发点（v3 schema）。

背景：W1 波次二次漏检复盘（2026-08-01）的第三道防线——wave_scan 抓"同窗建仓的群"，
本脚本抓"资金拓扑上的枢纽"：①汇集点（sink）＝滚动窗内从多个合格来源收币的地址
（Q1/3yMk 型进货枢纽——19 根 W1 藤裸露在它们的进货单上却无人看）；②分发点（spray）＝
向大批地址批量派发的地址（H9 三派发器型出货器）。
两类候选只报警不定性，按 candidate-adjudications/v1 成员级裁决归 −2 判断层。

上一版（2026-08-02 用户拍板补缝＋codex 交叉复核重构）：
  两条覆盖缝——缝1：慢速批发线 500 过宽（PYTHIA H9 单案 6,503 收方校准），收方 20~499
  且控节奏避开脉冲窗的慢速分发双模式全漏 → 慢速线降 100（用户设定的高召回初值）；
  缝2：脉冲只数"首建当日来自此源"的 fresh 新收方，向已建仓老地址补货的分发完全隐形
  （先占位建仓再灌大货，脉冲计数为零）→ 新增 pulse_all 广义脉冲口径。
  三口径判据（金额线全部整数运算，meow 案纪律）：
    pulse＝14 日滑窗内 fresh 边流出 ≥2% 且窗内 fresh 新收方 ≥20（escrow 灌新仓型）；
    pulse_all＝14 日滑窗内全部出边流出 ≥2% 且窗内 distinct 收方（不限新老）≥20；
    slow_spray＝全史 distinct 收方 ≥100 且全史流出 ≥2%（匀速出货滑窗不突出的兜底）。
  pulse ⊂ pulse_all（fresh 达标窗必然全体达标）——故产物为多命中结构：一址一条 entry
  （ID 规则 spray-<addr> 不变，validator 拒重复 ID），mode_hits 记三口径各自命中与窗口，
  顶层 mode＝主定性标签（取序 pulse > pulse_all > slow_spray，fresh 灌新仓语义最尖），
  不得以顶层 mode 当作"未命中其他口径"的证据。
  同步修复：出边零值转账过滤（amt>0，零值可凑收方数）；窗口浓度字段
  top1_recipient_share_pct＋meaningful_recipient_count（窗内收 ≥0.001% 供应的收方数，
  线与 wave_scan D 指纹一致）——"1 笔大额＋19 粉尘收方"可伪命中双线，浓度只报不拒，
  供裁决识别伪分发；pulse_all 命中时 launch_window 用其窗口起点（旧逻辑回退首出账日）。
  残余缝（诚实声明，写入 analyze-workflow 覆盖真空段）：收方 20~99 且窗口不达标的慢速
  分发／<20 收方拆分／全史 <2%／一实体轮换多址各 <2%／多跳二级分发，本闸均不可见。

⚠ 参数出身：PYTHIA 单案回测＋用户设定初值（2026-08-02），非多案校准；
首个新案实战时如实标注此局限。

口径纪律（与 wave_scan 完全一致）：分母＝--total-supply 冻结值；边表同源；mint/burn
哨兵排除；f==t 自转排除；--entity-file 抵消只对**同一实体**内部流转生效（按 entity_id
分组，跨实体转账保留——v6.8.1 codex 复核修复：拍平成单一集合会把实体间真实转账当
内部边删掉；−1 阶段无实体表时不传）；"新地址/首次有意义建仓"复用 wave_scan 的
first_meaningful_day 抗 dust 定义（首日末余额 ≥自身峰值×first-meaningful-ratio）。

输入三选一（同 wave_scan）：--edges-sol / --edges-evm-v2 / --duckdb；正式
--edges-sol 强制 --case-root 与 --mint，经 resolver 取唯一 cache；--sol-cache-meta 若给出
必须等于 resolver 结果。输出：--out flow_anomaly_report.json（schema flow-anomaly/v3，
Solana 含 edge_source_binding、EVM 省略；来源/收方数组全量零截断；
sink 另含历史峰值、当前余额、全史净流入，供 validator 防多窗口累计低估；权威定义
references/scan-schemas.md）。

退出码：0=扫描完成；2=数据探测失败/参数错误（fail-closed）；1=脚本自身错误。

回测基线（装闸必附原案回测；改阈值/算法后必须重跑 PYTHIA 并比对 fixtures/pythia_anchors.json，
数值锚点唯一权威＝该 fixture 文件）：
  - 汇集点义务：Q1Ac6Y…（进货 83.27% 的调度枢纽）与 3yMkB8oc…（Alpha 场内 8.77% 过手）
    以稳定 ID 过阈值（排名仅参考）；sink 判据 v2 未变，稳定 ID 集合零扰动。
  - 分发点义务：H9 三派发器 DWVGbsn7/8WwVTK51/5GpctXbe 全部命中；mode 按实测记录——
    旧备注"匀速出货任何 14 日窗 <0.2%"仅对 fresh 口径成立（v2 订正），全收方口径下
    其中派发器存在双达标窗者归 pulse_all 属预期迁移，不是回归。
  - Q1Ac6Y 的 spray 候选保持 mode=pulse（2025-08-13 窗灌新仓）。
"""
import argparse
import json
import sys
from datetime import datetime, timezone

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wave_scan import (Z, DEAD, load_sol, load_evm_v2, attach_duckdb,  # noqa: E402
                       build_addr_summary, retention_bucket, day_str)

SCHEMA = "flow-anomaly/v3"


def log(msg):
    print(f"[flow_anomaly] {msg}", flush=True)


def pct_to_raw(total, pct):
    """百分比阈值 → raw 整数线（份额阈值一律整数运算——浮点比较会漏"恰好整数枚"边界，
    meow 案 2026-07-15 纪律）。精度 0.0001 个百分点，覆盖本脚本全部参数粒度。"""
    return total * int(round(pct * 10000)) // 1000000


def load_entity_groups(path):
    """--entity-file：json（{entity_id:[addr…]} 或 [[addr…]…] 或 addr 数组）→ {addr: entity_id}。
    v6.8.1（codex 复核修复）：保留分组而非拍平成一个大集合——抵消只对**同一实体**内部
    流转生效，实体 A → 实体 B 的真实跨实体转账必须保留（拍平会把它当内部边删掉，
    可能漏掉 sink/spray）。同址跨实体即拒（名册冲突先并册）。"""
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    mapping = {}

    def put(addr, eid):
        if not isinstance(addr, str) or not addr:
            log(f"参数错误：--entity-file 成员必须是非空字符串: {addr!r}")
            sys.exit(2)
        if addr in mapping and mapping[addr] != eid:
            log(f"参数错误：地址 {addr} 同时属于实体 {mapping[addr]} 与 {eid}——先并册再扫描")
            sys.exit(2)
        mapping[addr] = eid

    if isinstance(obj, dict):
        for eid, v in obj.items():
            if isinstance(v, list):
                for x in v:
                    put(x, str(eid))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, list):
                for x in v:
                    put(x, f"e{i}")
            elif isinstance(v, str):
                put(v, "e0")
    return mapping


def best_window_scan(rows, win_sec, min_val, min_keys):
    """rows=[(ts, key, val)] 按 ts 升序。在 ≤win_sec 滑窗中找**同时满足**
    合计 ≥min_val 且 distinct key ≥min_keys 的窗，返回其中合计最大者
    (best_sum, best_keys, w_start, w_end)；无达标窗返回 (0, None, None, None)。
    ⚠ 不能先取金额最大窗再验 key 数——PYTHIA 回测实证 Q1 金额最大窗（22.2%）
    恰好来源仅 4 个被拒，而另存在 14 来源/18.8% 的双达标窗（实现 bug 教训）。"""
    from collections import Counter
    best = (0, None, None, None)
    cnt = Counter()
    ssum = 0
    j = 0
    for i in range(len(rows)):
        cnt[rows[i][1]] += 1
        ssum += rows[i][2]
        while rows[i][0] - rows[j][0] > win_sec:
            cnt[rows[j][1]] -= 1
            if not cnt[rows[j][1]]:
                del cnt[rows[j][1]]
            ssum -= rows[j][2]
            j += 1
        if ssum >= min_val and len(cnt) >= min_keys and ssum > best[0]:
            best = (ssum, set(cnt), rows[j][0], rows[i][0])
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--edges-sol")
    src.add_argument("--edges-evm-v2")
    src.add_argument("--duckdb")
    ap.add_argument("--edges-table", default="edges")
    ap.add_argument("--legacy-sol5", action="store_true",
                    help="保留显式诊断开关；本 READY anomaly 链一律拒绝")
    ap.add_argument("--sol-cache-meta")
    ap.add_argument("--mint")
    ap.add_argument("--case-root", help="正式 Solana 案根；经 cache resolver 且拒符号链接")
    ap.add_argument("--total-supply", required=True)
    ap.add_argument("--out", default="flow_anomaly_report.json")
    ap.add_argument("--exclude-file", help="已知设施地址清单（不参与扫描）")
    ap.add_argument("--entity-file", help="已知实体成员表——实体内部流转抵消（可选）")
    ap.add_argument("--mem-limit", default="8GB")
    ap.add_argument("--min-peak-pct", type=float, default=0.02, help="合格来源线（与 wave_scan 一致）")
    ap.add_argument("--first-meaningful-ratio", type=float, default=0.05)
    # 汇集点（初值）
    ap.add_argument("--sink-window-days", type=int, default=14)
    ap.add_argument("--sink-min-inflow-pct", type=float, default=2.0)
    ap.add_argument("--sink-min-sources", type=int, default=5)
    # 分发点（v2 三口径——pulse：escrow 灌新仓型脉冲；pulse_all：不限新老收方的广义脉冲
    # （堵"向已建仓老地址补货"口径盲区，2026-08-02）；slow_spray：匀速出货滑窗不突出的
    # 全史兜底（H9 型；慢速线 500→100，500 系 PYTHIA 单案 6,503 收方校准的过宽初值））
    ap.add_argument("--spray-window-days", type=int, default=14)
    ap.add_argument("--spray-min-outflow-pct", type=float, default=2.0,
                    help="pulse/pulse_all：窗内流出 ≥此%%；slow_spray：全史流出 ≥此%%")
    ap.add_argument("--spray-min-recipients", type=int, default=20,
                    help="pulse：窗内 fresh 新收方 ≥此数；pulse_all：窗内收方（不限新老）≥此数")
    ap.add_argument("--spray-slow-min-recipients", type=int, default=100,
                    help="慢速批发模式：全史 distinct 收方 ≥此数（高召回初值，用户 2026-08-02 定）")
    a = ap.parse_args()

    if a.legacy_sol5:
        log("正式 anomaly 链拒绝 legacy-sol5；旧案 slot+owner 覆盖请用 audit_closed_accounts")
        return 2

    import duckdb
    total = int(a.total_supply)
    if total <= 0:
        log("参数错误：--total-supply 必须为正")
        sys.exit(2)
    exclude = set()
    if a.exclude_file:
        with open(a.exclude_file, encoding="utf-8") as fh:
            txt = fh.read().strip()
            try:
                exclude = set(json.loads(txt))
            except json.JSONDecodeError:
                exclude = {x.strip() for x in txt.splitlines() if x.strip()}
    entity_groups = load_entity_groups(a.entity_file) if a.entity_file else {}

    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.mem_limit}'")
    con.execute("SET preserve_insertion_order=false")
    t0 = datetime.now(timezone.utc)
    edge_source_binding = None
    if a.edges_sol:
        n_edges, edge_source_binding = load_sol(
            con, a.edges_sol, cache_meta_path=a.sol_cache_meta,
            expected_mint=a.mint, case_root=a.case_root)
    elif a.edges_evm_v2:
        n_edges = load_evm_v2(con, a.edges_evm_v2)
    else:
        n_edges = attach_duckdb(con, a.duckdb, a.edges_table)
    log(f"边表就绪 {n_edges:,} 条")

    build_addr_summary(con, exclude, a.first_meaningful_ratio)
    min_peak_raw = pct_to_raw(total, a.min_peak_pct)
    eligible = {r[0] for r in con.execute(
        f"SELECT owner FROM addr WHERE peak >= {min_peak_raw}").fetchall()}
    log(f"合格地址（峰值≥{a.min_peak_pct}%）{len(eligible):,} 个")
    info = {r[0]: (int(r[1]), int(r[2]), int(r[3])) for r in con.execute(
        f"SELECT owner, peak, final_bal, first_meaningful_day FROM addr").fetchall()}

    sentinels = {Z, DEAD} | exclude
    # 实体内部流转抵消视图：仅两端属于**同一实体**的边被剔除（跨实体转账保留）；
    # 无实体表时 eflow 直通 edges。sink/spray 一切扫描查询走 eflow；
    # 地址概要（addr）仍按全量 edges——持仓史不做抵消。
    if entity_groups:
        con.execute("CREATE TEMP TABLE entmap(addr VARCHAR, eid VARCHAR)")
        con.executemany("INSERT INTO entmap VALUES (?, ?)", sorted(entity_groups.items()))
        con.execute("""
            CREATE VIEW eflow AS
            SELECT e.ts, e.f, e.t, e.amt FROM edges e
            LEFT JOIN entmap mf ON mf.addr = e.f
            LEFT JOIN entmap mt ON mt.addr = e.t
            WHERE mf.eid IS NULL OR mt.eid IS NULL OR mf.eid <> mt.eid""")
    else:
        con.execute("CREATE VIEW eflow AS SELECT ts, f, t, amt FROM edges")
    sent_ph = "', '".join(sorted(sentinels))
    data_first_day = con.execute("SELECT MIN(ts) // 86400 FROM edges").fetchone()[0] or 0

    # ---------------- ① 汇集点 ----------------
    sink_min_raw = pct_to_raw(total, a.sink_min_inflow_pct)
    elig_ph = "', '".join(sorted(eligible - sentinels))
    # amt > 0：零值转账既凑不了金额也不许凑来源/收方数（v2，spray 同款）
    pre_sinks = [r[0] for r in con.execute(f"""
        SELECT t FROM eflow
        WHERE f IN ('{elig_ph}') AND t NOT IN ('{sent_ph}') AND f <> t AND amt > 0
        GROUP BY t HAVING SUM(amt) >= {sink_min_raw}""").fetchall()]
    log(f"汇集点预筛 {len(pre_sinks)} 个（合格来源总流入 ≥{a.sink_min_inflow_pct}%）")
    win_sec = a.sink_window_days * 86400
    sinks = []
    for t in pre_sinks:
        rows = con.execute(f"""
            SELECT ts, f, amt FROM eflow
            WHERE t = '{t}' AND f IN ('{elig_ph}') AND f <> t AND amt > 0
            ORDER BY ts""").fetchall()
        best_sum, best_srcs, w0, w1 = best_window_scan(
            [(int(ts), f, int(v)) for ts, f, v in rows], win_sec,
            sink_min_raw, a.sink_min_sources)
        if best_srcs is None:
            continue
        src_pct = {}
        for ts, f, v in rows:
            if w0 <= int(ts) <= w1 and f in best_srcs:
                src_pct[f] = src_pct.get(f, 0) + int(v)
        qualified_in = sum(int(v) for _, _, v in rows)
        net_in = con.execute(f"""
            SELECT COALESCE(SUM(CASE WHEN t = '{t}' AND f <> t THEN amt
                                     WHEN f = '{t}' AND t <> f THEN -amt ELSE 0 END), 0)
            FROM eflow WHERE t = '{t}' OR f = '{t}'""").fetchone()[0]
        hist_peak, current_bal = info.get(t, (0, 0, 0))[:2]
        sinks.append({
            "id": f"sink-{t}",
            "addr": t,
            "best_window": {"start": day_str(w0 // 86400), "end": day_str(w1 // 86400),
                            "inflow_pct": round(best_sum * 100.0 / total, 4),
                            "source_count": len(best_srcs)},
            # 判级影响不能只看单个最佳窗：多段不重叠的 4% 流入可累计成 12% 历史库存。
            # validator 以历史峰值/当前余额/全史净流入/合格最佳窗的最大值重算影响。
            "balance": {"historical_peak_pct": round(int(hist_peak) * 100.0 / total, 4),
                        "current_balance_pct": round(int(current_bal) * 100.0 / total, 4)},
            "all_time": {"net_inflow_pct": round(int(net_in) * 100.0 / total, 4),
                         "qualified_inflow_pct": round(qualified_in * 100.0 / total, 4)},
            "sources": sorted(({"addr": f, "pct": round(v * 100.0 / total, 4),
                                "retention_bucket": retention_bucket(info[f][1], info[f][0])
                                if f in info else None}
                               for f, v in src_pct.items()), key=lambda s: -s["pct"]),
            "launch_window": (w0 // 86400) <= data_first_day + 3,
        })
    sinks.sort(key=lambda s: -s["best_window"]["inflow_pct"])

    # ---------------- ② 分发点（v2 三口径多命中） ----------------
    spray_min_raw = pct_to_raw(total, a.spray_min_outflow_pct)
    # 浓度线：窗内"有意义收方"＝单收方窗内累计 ≥0.001% 总供应（与 wave_scan D 指纹同线）
    meaningful_recv_raw = pct_to_raw(total, 0.001)
    pre_sprays = [r[0] for r in con.execute(f"""
        SELECT f FROM eflow
        WHERE t NOT IN ('{sent_ph}') AND f NOT IN ('{sent_ph}') AND f <> t AND amt > 0
        GROUP BY f HAVING SUM(amt) >= {spray_min_raw}""").fetchall()]
    log(f"分发点预筛 {len(pre_sprays)} 个（总流出 ≥{a.spray_min_outflow_pct}%）")
    win_sec2 = a.spray_window_days * 86400
    sprays = []
    for f in pre_sprays:
        rows = [(int(ts), t, int(v)) for ts, t, v in con.execute(f"""
            SELECT ts, t, amt FROM eflow
            WHERE f = '{f}' AND t NOT IN ('{sent_ph}') AND f <> t AND amt > 0
            ORDER BY ts""").fetchall()]
        all_recv = {t for _, t, _ in rows}
        all_out = sum(v for _, _, v in rows)
        # "喂新地址"的边：该笔发生日 == 收方 first_meaningful_day（首建即来自此来源）
        fresh = [(ts, t, v) for ts, t, v in rows
                 if t in info and ts // 86400 == info[t][2]]
        fresh_recv = {t for _, t, _ in fresh}

        def window_summary(w0, w1, wsum):
            """选定窗的统一摘要（v2 统一键：不按 mode 换键名，消费者无须分支）。
            recipient_count＝窗内全体 distinct 收方；fresh_recipient_count＝窗内首建
            当日收方；浓度两键识别"1 笔大额＋N 粉尘"伪分发（只报不拒，供裁决）。"""
            recv_tot = {}
            fresh_in_win = set()
            for ts, t, v in rows:
                if w0 <= ts <= w1:
                    recv_tot[t] = recv_tot.get(t, 0) + v
                    if t in info and ts // 86400 == info[t][2]:
                        fresh_in_win.add(t)
            top1 = max(recv_tot.values()) if recv_tot else 0
            return {"start": day_str(w0 // 86400), "end": day_str(w1 // 86400),
                    "outflow_pct": round(wsum * 100.0 / total, 4),
                    "recipient_count": len(recv_tot),
                    "fresh_recipient_count": len(fresh_in_win),
                    "top1_recipient_share_pct": round(top1 * 100.0 / total, 4),
                    "meaningful_recipient_count": sum(
                        1 for v in recv_tot.values() if v >= meaningful_recv_raw)}

        # pulse：fresh 边滑窗双达标（escrow 灌新仓型）
        p_sum, p_recv, p_w0, p_w1 = best_window_scan(
            fresh, win_sec2, spray_min_raw, a.spray_min_recipients)
        pulse_hit = p_recv is not None
        # pulse_all：全部出边滑窗双达标（不限新老——堵"向已建仓老地址补货"盲区）。
        # pulse ⊂ pulse_all：fresh 达标窗必然全体达标，故 pulse 命中者此处必命中。
        a_sum, a_recv, a_w0, a_w1 = best_window_scan(
            rows, win_sec2, spray_min_raw, a.spray_min_recipients)
        pulse_all_hit = a_recv is not None
        # slow_spray：全史 distinct 收方 ≥N 且全史流出 ≥X%（匀速出货任何滑窗都不突出，
        # 只有全史口径能抓——H9 三派发器型）
        slow_hit = len(all_recv) >= a.spray_slow_min_recipients and all_out >= spray_min_raw
        if not (pulse_hit or pulse_all_hit or slow_hit):
            continue
        # 一址一条 entry（validator 拒重复 ID）；顶层 mode＝主定性标签，
        # mode_hits 保全三口径命中事实——顶层 mode 不是"未命中其他口径"的证据。
        mode = "pulse" if pulse_hit else ("pulse_all" if pulse_all_hit else "slow_spray")
        mode_hits = {
            "pulse": {"hit": pulse_hit},
            "pulse_all": {"hit": pulse_all_hit},
            "slow_spray": {"hit": slow_hit},
        }
        if pulse_hit:
            mode_hits["pulse"]["best_window"] = window_summary(p_w0, p_w1, p_sum)
        if pulse_all_hit:
            mode_hits["pulse_all"]["best_window"] = window_summary(a_w0, a_w1, a_sum)
        first_day = rows[0][0] // 86400
        # launch_window：主模式窗起点（pulse_all 也用其 w0——旧逻辑对非 pulse 一律回退
        # 首出账日，v2 修正）；slow_spray 无窗仍用首出账日
        launch_day = (p_w0 // 86400 if pulse_hit
                      else a_w0 // 86400 if pulse_all_hit else first_day)
        entry = {
            "id": f"spray-{f}",
            "addr": f,
            "mode": mode,
            "mode_hits": mode_hits,
            "all_time": {"outflow_pct": round(all_out * 100.0 / total, 4),
                         "recipient_count": len(all_recv),
                         "fresh_recipient_count": len(fresh_recv)},
            "best_window": mode_hits.get(mode, {}).get("best_window"),
            "launch_window": launch_day <= data_first_day + 3,
        }
        if mode == "pulse":
            # 判据收方全量：pulse＝主窗 fresh 收方，len == best_window.fresh_recipient_count
            entry["recipients"] = sorted(p_recv)
        elif mode == "pulse_all":
            # pulse_all＝主窗全体收方，len == best_window.recipient_count
            entry["recipients"] = sorted(a_recv)
        else:
            # 慢速模式收方列 top（按累计收量）——显式摘要非静默截断，全量数在 all_time.recipient_count
            top = con.execute(f"""
                SELECT t, SUM(amt) AS v FROM eflow
                WHERE f = '{f}' AND t NOT IN ('{sent_ph}') AND f <> t AND amt > 0
                GROUP BY t ORDER BY v DESC LIMIT 500""").fetchall()
            entry["recipients_top"] = [r[0] for r in top]
        sprays.append(entry)
    sprays.sort(key=lambda s: -s["all_time"]["outflow_pct"])

    report = {
        "schema": SCHEMA,
        "generated_at": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {k: v for k, v in vars(a).items() if k not in ("out",)},
        "total_supply_raw": str(total),
        "edges": n_edges,
        "eligible_universe_count": len(eligible),
        "sinks": sinks,
        "sprays": sprays,
        "requires_adjudication": bool(sinks or sprays),
        "note": "候选≠结论：汇集点可能是 CEX 充值地址/DEX 路由、分发点可能是空投器/设施——"
                "按 candidate-adjudications/v1 成员级逐条裁决归 −2/A3 判断层；launch_window "
                "打标不过滤。spray 为多命中结构：顶层 mode 是主定性标签（pulse>pulse_all>"
                "slow_spray），mode_hits 保全三口径命中事实；浓度字段识别伪分发只报不拒。"
                "参数出身＝PYTHIA 单案回测＋用户设定初值（2026-08-02），非多案校准。",
    }
    if a.edges_sol:
        report["edge_source_binding"] = edge_source_binding
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    log(f"汇集点 {len(sinks)} 个 / 分发点 {len(sprays)} 个 → {a.out}")
    for s in sinks[:10]:
        log(f"  sink {s['addr'][:14]}… 窗{s['best_window']['start']}起 "
            f"流入{s['best_window']['inflow_pct']}% 来源{s['best_window']['source_count']} | "
            f"历史峰值{s['balance']['historical_peak_pct']}% 净流入{s['all_time']['net_inflow_pct']}%")
    for s in sprays[:10]:
        bw = s.get("best_window") or {}
        if s["mode"] == "pulse":
            log(f"  spray[脉冲] {s['addr'][:14]}… 窗{bw['start']}起 流出{bw['outflow_pct']}% "
                f"新收方{bw['fresh_recipient_count']}（全收方{bw['recipient_count']}，"
                f"有效{bw['meaningful_recipient_count']}）")
        elif s["mode"] == "pulse_all":
            log(f"  spray[广脉冲] {s['addr'][:14]}… 窗{bw['start']}起 流出{bw['outflow_pct']}% "
                f"收方{bw['recipient_count']}（fresh {bw['fresh_recipient_count']}，"
                f"有效{bw['meaningful_recipient_count']}）")
        else:
            log(f"  spray[慢速] {s['addr'][:14]}… 全史流出{s['all_time']['outflow_pct']}% "
                f"收方{s['all_time']['recipient_count']}（fresh {s['all_time']['fresh_recipient_count']}）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[flow_anomaly] 脚本自身错误（exit 1，修完重跑）: {e}", file=sys.stderr)
        raise SystemExit(1)
