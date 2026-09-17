# 施工 D：完成

依据 maintenance/repair-20260917-p0-four/workorder_D.md v4；开工与交付 HEAD 均为 f9b3800。D1–D6 已完成，六项指定测试及 invariant_scan 全部 PASS；无 SKIP。

## ① 开工基线与锚点

以下为实际开工命令及原始 stdout；git status --short 输出为空（0 字节），两条命令退出码均为 0。

```text
$ git status --short
$ git rev-parse --short HEAD
f9b3800
```

工单指定 19 个锚点均经 grep -n -F 实跑确认：恰 1 处且施工前行号一致。

```text
$ grep -n -F '    json.dump(need, open(f"{a.out_dir}/needs_block_precision.json", "w"), indent=1)' scripts/evm/peaks_daily.py
171:    json.dump(need, open(f"{a.out_dir}/needs_block_precision.json", "w"), indent=1)
$ grep -n -F '               "trigger_days_sha256": trig_sha,' scripts/evm/peaks_daily.py
213:               "trigger_days_sha256": trig_sha,
$ grep -n -F 'def check_daily_peaks(case_dir: Path, errors: list[str]):' scripts/report/audit_release_gate.py
1074:def check_daily_peaks(case_dir: Path, errors: list[str]):
$ grep -n -F '        errors.append("trigger_days.json 触发日为空且无 empty_reason 显式声明")' scripts/report/audit_release_gate.py
1103:        errors.append("trigger_days.json 触发日为空且无 empty_reason 显式声明")
$ grep -n -F '    check_daily_peaks(case_dir, errors)' scripts/report/audit_release_gate.py
1676:    check_daily_peaks(case_dir, errors)
$ grep -n -F '        CREATE VIEW deltas AS' scripts/evm/replay_duck.py
191:        CREATE VIEW deltas AS
$ grep -n -F '        SELECT frm, b, -CAST(v AS {vt}) FROM events WHERE frm <> \'{Z}\'""")' scripts/evm/replay_duck.py
194:        SELECT frm, b, -CAST(v AS {vt}) FROM events WHERE frm <> '{Z}'""")
$ grep -n -F 'def _peaks_python(con, peak_min):' scripts/evm/replay_duck.py
330:def _peaks_python(con, peak_min):
$ grep -n -F '    ap.add_argument("--force-varint", action="store_true",' scripts/evm/replay_duck.py
556:    ap.add_argument("--force-varint", action="store_true",
$ grep -n -F '        json.dump(receipt, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)' scripts/evm/replay_duck.py
577:        json.dump(receipt, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)
$ grep -n -F '    stats, mint_total = replay_pass1(con, a.out_dir, vt)' scripts/evm/replay_duck.py
587:    stats, mint_total = replay_pass1(con, a.out_dir, vt)
$ grep -n -F 'import argparse, csv, glob, json, os, sys, time' scripts/evm/replay_duck.py
36:import argparse, csv, glob, json, os, sys, time
$ grep -n -F '        # h) 显式空声明＋哈希咬合 → 峰值/触发日检查放行' scripts/tests/test_audit_release_gate.py
960:        # h) 显式空声明＋哈希咬合 → 峰值/触发日检查放行
$ grep -n -F '        assert not any(("trigger" in x or "上界" in x) for x in errors), errors' scripts/tests/test_audit_release_gate.py
970:        assert not any(("trigger" in x or "上界" in x) for x in errors), errors
$ grep -n -F '    # 6.9.2 修复反例（codex 验收 P1）：挂名≠裁决——空壳候选拒。' scripts/tests/test_audit_release_gate.py
972:    # 6.9.2 修复反例（codex 验收 P1）：挂名≠裁决——空壳候选拒。
$ grep -n -F 'def main():' scripts/tests/test_engine_equivalence.py
236:def main():
$ grep -n -F '          and summary.get("trigger_days_sha256") == real_sha)' scripts/tests/test_peaks_daily.py
113:          and summary.get("trigger_days_sha256") == real_sha)
$ grep -n -F '对这批再补块级精确值——**只多查不漏查**。' references/data-pipeline-evm-recon.md
132:凡 L1 未达门槛但 L2 达标者落 `needs_block_precision.json`，对这批再补块级精确值——**只多查不漏查**。
$ grep -n -F '过线地址补块级精查。' references/playbook-entity-cluster-tiering.md
149:- **峰值判级：日终 L1 + L2 上界 + 四类触发日逐笔** — **触发条件**：庄级判级或发射窗协同全景。**必做动作**：L1 用日终；L2＝昨日日终余额 + 当日毛流入，peaks_summary.json 必含 ub_formula=prev_close_plus_gross_in/v2，过线地址补块级精查。无论 L2 是否报警，发射日、毕业日、价格单日 ±50%、单日阵营变动 ≥10pp 都逐笔；以 peaks_daily.py --trigger-days 生成 trigger_days.json，零触发也写 empty_reason。新阵营触发日出现后必须回跑并重验判级。图用日终或更粗粒度时补盘中事件点并注明。**阻断语义**：旧 Σmax(单日净变动,0) 公式产物拒绝；缺 trigger_days、漏回跑或用平滑曲线替判级证据均拒绝。阴性断言仍须逐事件峰值。**权威脚本**：peaks_daily.py、peaks_summary.json、audit_release_gate。2026-08-02 定。
ANCHORS: PASS
```

## ② D1/D2/D3 diff 原文与 D4/D5/D6 摘要

### D1 scripts/evm/peaks_daily.py

```diff
diff --git a/scripts/evm/peaks_daily.py b/scripts/evm/peaks_daily.py
index e6f2703..06f5665 100644
--- a/scripts/evm/peaks_daily.py
+++ b/scripts/evm/peaks_daily.py
@@ -61,6 +61,7 @@ trigger_days.json（逐触发日列出当日活跃候选地址名单，供块级
     <out>/trigger_days.json          触发日→当日活跃候选名单（仅 --trigger-days 时产出）
     <out>/peaks_summary.json         含 ub_formula 口径标记＋trigger_days_file/
                                      trigger_days_sha256（发布闸靠哈希咬合拒目录残留的陈旧触发日产物）
+                                     needs_block_precision_sha256（发布闸靠它咬合补算收据）
 
 （来源：KOGE(BSC) 3.595 亿行分析，2026-07-25；上界公式修正 2026-08-02）
 """
@@ -169,6 +170,8 @@ def main():
         print(f"  门槛 {lvl*100:>6.2f}%: 日末达标 {ok:>5} 址；"
               f"日末未达但上界达标（需块级精确）{len(hit):>5} 址", flush=True)
     json.dump(need, open(f"{a.out_dir}/needs_block_precision.json", "w"), indent=1)
+    need_sha = hashlib.sha256(
+        open(f"{a.out_dir}/needs_block_precision.json", "rb").read()).hexdigest()
 
     UB_FORMULA = "prev_close_plus_gross_in/v2"
     if a.trigger_days:
@@ -211,6 +214,8 @@ def main():
                "levels_checked": a.levels,
                "trigger_days_file": bool(a.trigger_days),
                "trigger_days_sha256": trig_sha,
+               "needs_block_precision_file": "needs_block_precision.json",
+               "needs_block_precision_sha256": need_sha,
                "elapsed_s": round(time.time() - t0, 1)}
     json.dump(summary, open(f"{a.out_dir}/peaks_summary.json", "w"), indent=1)
     print(json.dumps(summary, indent=1))
```

### D2 scripts/report/audit_release_gate.py

```diff
diff --git a/scripts/report/audit_release_gate.py b/scripts/report/audit_release_gate.py
index ced419f..b0171fd 100644
--- a/scripts/report/audit_release_gate.py
+++ b/scripts/report/audit_release_gate.py
@@ -1071,14 +1071,50 @@ def check_dormant(case_dir: Path, d: dict, errors: list[str]):
                       f"＋decision_reason 非空；示例 {bad[:3]}）——仅把地址挂进名单不算裁决")
 
 
+BLOCK_PRECISION_FOLLOWUP_SCHEMA = "block-precision-followup/v1"
+
+
+def _find_peaks_summaries(case_dir: Path) -> list[Path]:
+    """R09（7.2.0）：peaks_daily 产物根不限定案根——递归定位 peaks_summary.json；
+    跳过隐藏目录（.duck_tmp 等）、_history 与符号链接路径。"""
+    hits = []
+    for p in sorted(case_dir.rglob("peaks_summary.json")):
+        rel = p.relative_to(case_dir)
+        if any(part.startswith(".") or part == "_history" for part in rel.parts):
+            continue
+        cur, linked = p, False
+        while cur != case_dir:
+            if cur.is_symlink():
+                linked = True
+                break
+            cur = cur.parent
+        if linked or not p.is_file():
+            continue
+        hits.append(p)
+    return hits
+
+
 def check_daily_peaks(case_dir: Path, errors: list[str]):
-    """日级峰值口径闭环（v6.9.1）：案目录出现 peaks_summary.json 即视为用了
+    """日级峰值口径闭环（v6.9.1）：案内出现 peaks_summary.json 即视为用了
     peaks_daily 替代件——旧上界公式产物拒收（Σmax(day_delta,0) 非恒等上界，
-    同日等额进出会漏），且四类触发日必须有显式产物（空也要声明）。"""
-    ps_path = case_dir / "peaks_summary.json"
-    if not ps_path.is_file():
+    同日等额进出会漏），且四类触发日必须有显式产物（空也要声明）。
+    R09（7.2.0）：①产物根按 rglob 定位（原只看案根，data/peaks_daily/ 下的产物整段绕过闸）；
+    ②needs_block_precision.json 与 summary 哈希咬合；③needs ∪ 触发日活跃候选非空时，
+    必须有 replay_duck.py --only-addrs 产出的 block_precision_followup.json 覆盖每一址。"""
+    hits = _find_peaks_summaries(case_dir)
+    if not hits:
+        return
+    if len(hits) > 1:
+        errors.append("案内出现多份 peaks_summary.json（"
+                      + ", ".join(str(h.relative_to(case_dir)) for h in hits)
+                      + "）——峰值产物根须唯一，清理陈旧目录后重验")
         return
+    ps_path = hits[0]
+    pd = ps_path.parent
     ps = load_json(ps_path, errors)
+    if not isinstance(ps, dict):
+        errors.append("peaks_summary.json 顶层须为对象")
+        return
     if str(ps.get("ub_formula")) != "prev_close_plus_gross_in/v2":
         errors.append("peaks_daily 产物是旧上界公式（缺 ub_formula=prev_close_plus_gross_in/v2）"
                       "——同日等额进出会被对冲漏检，升级脚本重跑")
@@ -1088,19 +1124,109 @@ def check_daily_peaks(case_dir: Path, errors: list[str]):
         errors.append("peaks_daily 本次运行未带 --trigger-days（四类触发日义务未履行）"
                       "——目录里残留的旧 trigger_days.json 不作数，带触发日清单重跑")
         return
-    tp = case_dir / "trigger_days.json"
+    tp = pd / "trigger_days.json"
     if not tp.is_file() or tp.is_symlink():
         errors.append("peaks_summary 声称产出触发日但 trigger_days.json 缺失")
         return
-    expected = str(ps.get("trigger_days_sha256", "")).lower()
-    if not expected or sha256_file(tp).lower() != expected:
+    trig_sha = str(ps.get("trigger_days_sha256", "")).lower()
+    if not trig_sha or sha256_file(tp).lower() != trig_sha:
         errors.append("trigger_days.json 与本次 peaks_daily 运行不咬合"
                       "（sha256 不匹配或 summary 未登记）——陈旧/换包产物拒收")
     td = load_json(tp, errors)
+    if not isinstance(td, dict):
+        errors.append("trigger_days.json 顶层须为对象")
+        return
     if str(td.get("schema")) != "trigger-days-replay/v1":
         errors.append("trigger_days.json schema 非法（须 trigger-days-replay/v1）")
     elif not td.get("days") and not td.get("empty_reason"):
         errors.append("trigger_days.json 触发日为空且无 empty_reason 显式声明")
+    # R09 ②：needs 文件必须在场且与 summary 登记哈希咬合（旧版 peaks_daily 未登记＝升级重跑）
+    needs_path = pd / "needs_block_precision.json"
+    needs_sha = str(ps.get("needs_block_precision_sha256", "")).lower()
+    if needs_path.is_symlink() or not needs_path.is_file() or not needs_sha \
+            or sha256_file(needs_path).lower() != needs_sha:
+        errors.append("needs_block_precision.json 缺失或与 peaks_summary 登记的 sha256 不咬合"
+                      "（旧版 peaks_daily 未登记该哈希＝升级脚本重跑）")
+        return
+    need = load_json(needs_path, errors)
+    if not isinstance(need, dict) or any(not isinstance(v, list) for v in need.values()):
+        errors.append("needs_block_precision.json 形状非法（须 {门槛: [地址]} 字典）")
+        return
+    union = set()
+    for bucket in need.values():
+        if any(not isinstance(x, str) or not x.strip() for x in bucket):
+            errors.append("needs_block_precision.json 地址项须为非空字符串")
+            return
+        union.update(x.strip().lower() for x in bucket)
+    days = td.get("days")
+    if days is not None and not isinstance(days, dict):
+        errors.append("trigger_days.json days 须为对象（日→{reason,count,active_candidates}）")
+        return
+    td_union = set()
+    for key, day in (days or {}).items():
+        if not isinstance(day, dict):
+            errors.append(f"trigger_days.json days[{key}] 须为对象")
+            return
+        cands = day.get("active_candidates")
+        if not isinstance(cands, list) or any(not isinstance(x, str) or not x.strip() for x in cands):
+            errors.append(f"trigger_days.json days[{key}].active_candidates 须为地址字符串列表（缺项/null 不作零候选）")
+            return
+        td_union.update(x.strip().lower() for x in cands)
+    union |= td_union
+    if not union:
+        return
+    # R09 ③：补算覆盖收据——每个待补地址都必须有块级精确峰值，且收据绑定当前 needs/触发日
+    fu_path = pd / "block_precision_followup.json"
+    if fu_path.is_symlink() or not fu_path.is_file():
+        errors.append(f"日级峰值有 {len(union)} 址需块级精确补算，但缺 block_precision_followup.json "
+                      "收据（replay_duck.py --only-addrs 产出）——L2 过线地址未补算不得判级")
+        return
+    fu = load_json(fu_path, errors)
+    if not isinstance(fu, dict):
+        errors.append("block_precision_followup.json 顶层须为对象")
+        return
+    if fu.get("schema") != BLOCK_PRECISION_FOLLOWUP_SCHEMA:
+        errors.append(f"block_precision_followup.json schema 非法（须 {BLOCK_PRECISION_FOLLOWUP_SCHEMA}）")
+    if fu.get("engine") != "replay_duck.py":
+        errors.append("block_precision_followup.json engine 非 replay_duck.py——块级补算须走重放引擎")
+    items = fu.get("inputs")
+    if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
+        errors.append("block_precision_followup.json inputs 须为 [{path, sha256}] 列表")
+        return
+    bound = {Path(str(i.get("path") or "")).name: str(i.get("sha256") or "").lower() for i in items}
+    if bound.get("needs_block_precision.json") != needs_sha:
+        errors.append("block_precision_followup.json 未绑定当前 needs_block_precision.json（inputs sha 不咬合）——needs 变了要重跑补算")
+    if td_union and bound.get("trigger_days.json") != trig_sha:
+        errors.append("block_precision_followup.json 未绑定当前 trigger_days.json（inputs sha 不咬合）——触发日活跃候选也须补算")
+    addrs = fu.get("addresses")
+    if not isinstance(addrs, dict):
+        errors.append("block_precision_followup.json 缺 addresses 映射")
+        return
+    norm = {}
+    for key, entry in addrs.items():
+        k = str(key).strip().lower()
+        if k in norm:
+            errors.append(f"block_precision_followup.json addresses 含大小写重复地址 {k}")
+            return
+        norm[k] = entry
+    missing = sorted(a for a in union if a not in norm)
+    if missing:
+        errors.append(f"块级补算收据未覆盖 {len(missing)} 址（样例 {missing[:3]}）——只多查不漏查")
+    for addr in sorted(union - set(missing)):
+        entry = norm[addr]
+        if not isinstance(entry, dict) or "peak" not in entry or "peak_blk" not in entry:
+            errors.append(f"块级补算收据 {addr} 须含 peak 与 peak_blk 两字段")
+            continue
+        before = len(errors)
+        peak = raw_int(entry.get("peak"), f"block_precision_followup.addresses[{addr}].peak", errors)
+        if len(errors) > before:
+            continue   # peak 本身非法只报根因，不再用替代值 0 判 peak_blk
+        blk = entry.get("peak_blk")
+        if peak > 0:
+            if isinstance(blk, bool) or not isinstance(blk, int) or blk < 0:
+                errors.append(f"块级补算收据 {addr}.peak_blk 须为非负整数区块（peak>0）")
+        elif blk is not None:
+            errors.append(f"块级补算收据 {addr}.peak_blk 在 peak==0 时须为 null")
 
 
 def check_reproduce_receipt(case_dir: Path, rel, cid, errors: list[str]):
```

### D3 scripts/evm/replay_duck.py

```diff
diff --git a/scripts/evm/replay_duck.py b/scripts/evm/replay_duck.py
index c096cf0..e22b30f 100644
--- a/scripts/evm/replay_duck.py
+++ b/scripts/evm/replay_duck.py
@@ -33,7 +33,7 @@ uint256 策略（防浮点退化——UHUGEINT 的 SUM 会静默退化 DOUBLE，
       [--camps camps.json] [--emit-csv] [--merged-parquet] [--no-merged] \
       [--mem-limit 8GB] [--threads 6]
 """
-import argparse, csv, glob, json, os, sys, time
+import argparse, csv, glob, hashlib, json, os, sys, time
 from pathlib import Path
 
 import duckdb
@@ -185,13 +185,17 @@ def build_events(con, chans):
     return acc
 
 
-def replay_pass1(con, out_dir, vt):
-    """聚合出 bal/peak/mint/burn/first/last + stats，写 pass1 四件产物。返回 (stats, mint_total)。"""
+def _create_deltas_view(con, vt):
     con.execute(f"""
         CREATE VIEW deltas AS
         SELECT t2 AS a, b, CAST(v AS {vt}) AS d FROM events
         UNION ALL
         SELECT frm, b, -CAST(v AS {vt}) FROM events WHERE frm <> '{Z}'""")
+
+
+def replay_pass1(con, out_dir, vt):
+    """聚合出 bal/peak/mint/burn/first/last + stats，写 pass1 四件产物。返回 (stats, mint_total)。"""
+    _create_deltas_view(con, vt)
     con.execute("CREATE TABLE bal AS SELECT a, SUM(d) s FROM deltas GROUP BY a")
     mint_total = con.execute(
         f"SELECT COALESCE(SUM(CAST(v AS {vt})), 0) FROM events WHERE frm = '{Z}'").fetchone()[0]
@@ -327,6 +331,92 @@ def replay_pass1(con, out_dir, vt):
     return stats, mint_total
 
 
+def _load_only_addrs(paths):
+    """--only-addrs 输入三态：needs_block_precision.json（{门槛:[地址]}）、trigger_days.json
+    （{"days":{日:{"active_candidates":[...]}}}）、纯地址列表。返回 (并集(小写), [(basename, sha256)])。"""
+    union, inputs = set(), []
+    for p in paths:
+        try:
+            raw = json.load(open(p, encoding="utf-8"))
+        except (OSError, ValueError) as exc:
+            _fail(f"[only-addrs] 读不了 {p}: {exc}")
+        if isinstance(raw, list):
+            found = raw
+        elif isinstance(raw, dict) and "days" in raw:
+            days = raw["days"]
+            if not isinstance(days, dict) or any(not isinstance(d, dict) for d in days.values()):
+                _fail(f"[only-addrs] {p} trigger_days 形状非法（days 须为 日→对象）")
+            found = []
+            for key, d in days.items():
+                cands = d.get("active_candidates")
+                if not isinstance(cands, list):
+                    _fail(f"[only-addrs] {p} days[{key}].active_candidates 须为列表（缺项/null 不作零候选）")
+                found.extend(cands)
+        elif isinstance(raw, dict):
+            if any(not isinstance(v, list) for v in raw.values()):
+                _fail(f"[only-addrs] {p} needs 形状非法（须 {{门槛: [地址]}}）")
+            found = [x for v in raw.values() for x in v]
+        else:
+            _fail(f"[only-addrs] {p} 格式非法（需 needs 字典 / trigger_days / 地址列表）")
+        if any(not isinstance(x, str) or not x.strip() for x in found):
+            _fail(f"[only-addrs] {p} 地址项须为非空字符串")
+        union.update(x.strip().lower() for x in found)
+        with open(p, "rb") as fh:
+            inputs.append((os.path.basename(p), hashlib.sha256(fh.read()).hexdigest()))
+    if not union:
+        _fail("[only-addrs] 地址并集为空——无需补算（needs 与触发日活跃候选均空）")
+    return union, inputs
+
+
+def _fail(msg):
+    print(msg, file=sys.stderr, flush=True)
+    raise SystemExit(2)
+
+
+def followup_peaks(con, a, vt):
+    """R09（7.2.0）：只对 --only-addrs 并集算块级精确峰值（无门槛、无预筛），写
+    block_precision_followup.json 到第一个 --only-addrs 文件所在目录。整段跳过 pass1/merged/
+    pass2，不碰 replay_stats/peaks.json 等全量产物。窗口 SQL 与 replay_pass1 逐字相同。"""
+    union, inputs = _load_only_addrs(a.only_addrs)
+    _create_deltas_view(con, vt)
+    con.execute("CREATE TABLE only_addrs (a VARCHAR)")
+    con.executemany("INSERT INTO only_addrs VALUES (?)", [(x,) for x in sorted(union)])
+    con.execute("""
+        CREATE TABLE ab AS
+        SELECT a, b, SUM(d) dd FROM deltas
+        WHERE a IN (SELECT a FROM only_addrs) GROUP BY a, b""")
+    try:
+        con.execute("""
+            CREATE TABLE peaks AS
+            WITH cum AS (SELECT a, b, SUM(dd) OVER (PARTITION BY a ORDER BY b) c FROM ab),
+                 mx AS (SELECT a, MAX(c) mc FROM cum GROUP BY a HAVING MAX(c) > 0)
+            SELECT m.a, m.mc, MIN(cum.b) pb FROM mx m
+            JOIN cum ON cum.a = m.a AND cum.c = m.mc GROUP BY m.a, m.mc""")
+        peak_rows = con.execute("SELECT a, mc, pb FROM peaks").fetchall()
+    except duckdb.Error as e:
+        print(f"[only-addrs] SQL 窗口不可用（{str(e)[:80]}），回退 Python 流式", flush=True)
+        peak_rows = _peaks_python(con, 0)
+    found = {str(x): {"peak": str(int(mc)), "peak_blk": int(pb)} for x, mc, pb in peak_rows}
+    addresses = {x: found.get(x, {"peak": "0", "peak_blk": None}) for x in sorted(union)}
+    with open(a.channels, "rb") as fh:
+        chan_sha = hashlib.sha256(fh.read()).hexdigest()
+    with open(__file__, "rb") as fh:
+        self_sha = hashlib.sha256(fh.read()).hexdigest()
+    receipt = {"schema": "block-precision-followup/v1", "engine": "replay_duck.py",
+               "producer": {"path": os.path.basename(__file__), "sha256": self_sha},
+               "value_type": vt,
+               "inputs": [{"path": n, "sha256": s} for n, s in inputs],
+               "channels": {"path": os.path.basename(a.channels), "sha256": chan_sha},
+               "count": len(addresses), "addresses": addresses}
+    out = os.path.join(os.path.dirname(os.path.abspath(a.only_addrs[0])), "block_precision_followup.json")
+    tmp = out + ".tmp"
+    with open(tmp, "w", encoding="utf-8") as fh:
+        json.dump(receipt, fh, ensure_ascii=False, indent=1)
+    os.replace(tmp, out)
+    print(f"[only-addrs] 块级精确峰值 {len(addresses)} 址（有事件 {len(found)}）→ {out}", flush=True)
+    return 0
+
+
 def _peaks_python(con, peak_min):
     """VARINT 慢路径兜底：从聚合行 (addr,block,delta) 流式算块末峰值（精确 int）。"""
     cur = con.execute("SELECT a, b, dd FROM ab ORDER BY a, b")
@@ -553,6 +643,10 @@ def main():
                     help="不写任何 merged 产物（亿级基准/对表跑省盘省时；默认关=行为不变）")
     ap.add_argument("--mem-limit", default="8GB")
     ap.add_argument("--threads", type=int, default=6)
+    ap.add_argument("--only-addrs", action="append", metavar="JSON",
+                    help="只对这些地址算块级精确峰值（needs_block_precision.json / trigger_days.json / "
+                         "地址列表，可重复）；写 block_precision_followup.json 到首个文件所在目录，"
+                         "跳过 pass1/merged/pass2，不覆盖全量产物")
     ap.add_argument("--force-varint", action="store_true",
                     help="强制任意精度 VARINT 路径（HUGEINT 聚合溢出报错时的显式出路；慢 ~5x 仍精确）")
     a = ap.parse_args()
@@ -574,7 +668,10 @@ def main():
         receipt = {**rej, "gate_pass": False,
                    "failure": "rejected_input_rows",
                    "policy": "n_bad_fields == 0 and n_out_of_segment == 0"}
-        json.dump(receipt, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)
+        if a.only_addrs:
+            print("[only-addrs] 输入含 rejected rows，不写 replay_stats.json（不覆盖全量产物）", file=sys.stderr, flush=True)
+        else:
+            json.dump(receipt, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)
         raise SystemExit(
             f"[fail-closed] 输入含 rejected rows: bad_fields={rej['n_bad_fields']} "
             f"out_of_segment={rej['n_out_of_segment']}——修复或重新采集后再重放")
@@ -584,6 +681,8 @@ def main():
     maxlen = con.execute("SELECT COALESCE(MAX(LENGTH(v)), 0) FROM events").fetchone()[0]
     vt = "VARINT" if a.force_varint else ("HUGEINT" if maxlen <= 37 else "VARINT")
     print(f"value 最大位数={maxlen} -> {vt} 路径", flush=True)
+    if a.only_addrs:
+        raise SystemExit(followup_peaks(con, a, vt))
     stats, mint_total = replay_pass1(con, a.out_dir, vt)
     stats.update(rej)
     stats.update(replay_provenance(a.out_dir, __file__))
```

### D4 测试摘要

- D4-a：只修订指定 h 夹具并在指定位置加入 _r09_case_1..13、夹具助手与捕获 Exception 的逐例循环；各例独立临时目录。覆盖子目录旧公式、多份 summary、needs/trigger 形状与哈希、补算覆盖、收据结构、地址归一、非法 peak 的根因。
- D4-b：只新增 followup_case() 及 main 调用。采用 v4 最后一笔 5*10**18；全量先成功后补算，峰值/首达块对表；无事件地址为 peak=0/peak_blk=null。坏 JSON、空列表、非法 needs 及四种 active_candidates 坏形状均校验 exit 2；坏事件通过 _write_inputs 在生成两层收据前加入 value=BAD，确认命中 bad_fields=1 且不覆盖旧 peaks/replay_stats，也不产新补算收据。在指定新增函数内同时比较 balances_final/mint_ledger 字节，核对 merged/pass2 产物未新增。
- D4-c：仅在指定位置新增 needs 文件名与实际 SHA-256 的 check。三个测试文件其余既有测试原文未改。

### D5 按 scanner 缺项逐条补登

第一次扫描退出码为 1，原文如下（消费者同一条目 schema 集合变化产生两条差异）：

```text
FAIL receipt_producers: code point missing from manifest: ('scripts/evm/replay_duck.py', ('block-precision-followup/v1',))
FAIL receipt_consumers: code point missing from manifest: ('scripts/report/audit_release_gate.py', ('address-balance-snapshot/v1', 'adversarial-review/v2', 'adversarial-review/v3', 'adversarial-review/v4', 'block-precision-followup/v1', 'facts-provenance/v1', 'figure2-check-receipt/v1', 'identity-holder-snapshot/v2', 'reproduce-receipt/v2'))
FAIL receipt_consumers: manifest point missing from code: ('scripts/report/audit_release_gate.py', ('address-balance-snapshot/v1', 'adversarial-review/v2', 'adversarial-review/v3', 'adversarial-review/v4', 'facts-provenance/v1', 'figure2-check-receipt/v1', 'identity-holder-snapshot/v2', 'reproduce-receipt/v2'))
FAIL atomic_writes: code point missing from manifest: ('scripts/evm/replay_duck.py', 'followup_peaks')
invariant manifest FAIL: 4 discrepancy(s)
```

只新增 replay_duck.py 的 block-precision-followup/v1 producer、audit_release_gate.py 同 schema consumer、followup_peaks overwrite_single atomic write。minimum_counts 按实际为 81 / 118 / 65 / 61 / 61（producer / consumer / transport / atomic / formal）；保留旧条目及排列，未整体回填。登记下限更新后再次实跑 scanner，退出码 0。

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

### D6 文档

- references/data-pipeline-evm-recon.md：只改施工前第 132 行的指定子串，61 B → 48 B，−13 B。
- references/playbook-entity-cluster-tiering.md：只改第 149 行的指定子串，30 B → 39 B，+9 B；末尾 2026-08-02 定。保留。
- references 合计净减 4 B：930065 → 930061。

## ③ RED → GREEN 逐例证据

D_red_evidence.txt 在任何生产修改前生成，记录三个未修改生产文件的 SHA-256、三个测试命令完整 stdout/stderr 与退出码。下表异常文字直接取自该证据；改后对应测试全部通过。

| 用例 | 改前实际结果及原文 | 改后 |
|---|---|---|
| D4-a 1 | RED：R09 子目录旧公式拒: AssertionError: [] | GREEN |
| D4-a 2 | GREEN→GREEN：R09 子目录完整产物放行（GREEN→GREEN） | GREEN |
| D4-a 3 | RED：R09 needs 非空缺收据拒: AssertionError: [] | GREEN |
| D4-a 4 | RED：R09 收据少一址拒: AssertionError: [] | GREEN |
| D4-a 5 | RED：R09 needs sha 不咬合拒: AssertionError: [] | GREEN |
| D4-a 6 | RED：R09 多份 summary 拒: AssertionError: [] | GREEN |
| D4-a 7 | RED：R09 触发日活跃候选进并集: AssertionError: [] | GREEN |
| D4-a 8 | RED：R09 needs 形状非法拒: AssertionError: (['0xabc'], []) | GREEN |
| D4-a 9 | RED：R09 触发日形状非法拒: AssertionError: ('x', []) | GREEN |
| D4-a 10 | RED：R09 收据结构非法进 errors 不崩: AssertionError: [] | GREEN |
| D4-a 11 | RED：R09 收据地址项非法拒: AssertionError: ({'peak': '1'}, []) | GREEN |
| D4-a 12 | GREEN→GREEN：R09 地址大小写归一放行（GREEN→GREEN） | GREEN |
| D4-a 13 | RED：R09 顶层非对象进 errors 不崩: AttributeError: 'list' object has no attribute 'get' | GREEN |
| D4-b | RED：AssertionError: block_precision_followup.json 不存在（rc=2）；argparse 不认识 --only-addrs | GREEN |
| D4-c | RED：FAIL  summary 登记 needs_block_precision 哈希（发布闸补算覆盖咬合依据）；FAIL：1 项失败 | GREEN |

D4-a 第 13 例按实际记录 AttributeError，未误记为 GREEN。D4-b 改前在第一处收据断言失败，后续坏输入/坏事件断言当时未执行；没有把 argparse 的 rc=2 当作它们通过。D4-c 沿用 check/finish，未伪造 AssertionError。

证据 SHA-256：a890d7ced0ebb343bbb3a1b4f2238f37a15008692e584c80ed03ba0615ba24c7

## ④ §0.8 各测试结果尾行

全部使用 python3 -B；设置 PYTHONDONTWRITEBYTECODE=1 使子进程不写 pycache，Matplotlib/Hypothesis 缓存放在系统临时目录。只运行下列工单允许的测试。

### test_audit_release_gate.py

```text
$ python3 -B scripts/tests/test_audit_release_gate.py
exit_code=0
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
```

### test_engine_equivalence.py

```text
$ python3 -B scripts/tests/test_engine_equivalence.py
exit_code=0
PASS: R09 块级补算峰值等价、零事件地址、非法输入与坏事件不覆盖全量产物
PASS: 三引擎 gate/退出码 10 例 hypothesis 全等；gate PASS 六产物全等；gate FAIL 正式序列零产物；VARINT 双引擎确定性对表通过
```

### test_peaks_daily.py

```text
$ python3 -B scripts/tests/test_peaks_daily.py
exit_code=0
PASS：0 项失败
```

### test_batch15_three_ledgers_frozen.py

```text
$ python3 -B scripts/tests/test_batch15_three_ledgers_frozen.py
exit_code=0
PASS batch15 frozen consumers: 12/12
```

### test_repair_batch_d.py

```text
$ python3 -B scripts/tests/test_repair_batch_d.py
exit_code=0
BATCH D 全部通过
```

### test_stage2_closeout.py

```text
$ python3 -B scripts/tests/test_stage2_closeout.py
exit_code=0
stage2_closeout: 28/28 PASS
```

### invariant_scan.py

```text
$ python3 -B scripts/tests/invariant_scan.py
exit_code=0（minimum_counts 更新后的复跑）
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

D4-a 改后逐例输出：

```text
ok    1 R09 子目录旧公式拒
ok    2 R09 子目录完整产物放行（GREEN→GREEN）
ok    3 R09 needs 非空缺收据拒
ok    4 R09 收据少一址拒
ok    5 R09 needs sha 不咬合拒
ok    6 R09 多份 summary 拒
ok    7 R09 触发日活跃候选进并集
ok    8 R09 needs 形状非法拒
ok    9 R09 触发日形状非法拒
ok    10 R09 收据结构非法进 errors 不崩
ok    11 R09 收据地址项非法拒
ok    12 R09 地址大小写归一放行（GREEN→GREEN）
ok    13 R09 顶层非对象进 errors 不崩
```

## ⑤ §1.1 三个字节数

只按 stat 元数据计数，references/attic.md 仅计文件大小。

```text
$ stat -f %z SKILL.md
8021
```

```text
$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930061
```

```text
$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
```

## ⑥ git diff --stat 与白名单

```text
$ git diff --stat
 references/data-pipeline-evm-recon.md         |   2 +-
 references/playbook-entity-cluster-tiering.md |   2 +-
 scripts/evm/peaks_daily.py                    |   5 +
 scripts/evm/replay_duck.py                    | 107 ++++++++++++++-
 scripts/report/audit_release_gate.py          | 140 ++++++++++++++++++-
 scripts/tests/invariant_manifest.json         |  18 ++-
 scripts/tests/test_audit_release_gate.py      | 186 +++++++++++++++++++++++++-
 scripts/tests/test_engine_equivalence.py      |  83 ++++++++++++
 scripts/tests/test_peaks_daily.py             |   5 +
 9 files changed, 531 insertions(+), 17 deletions(-)
```

git diff --stat 包含 9 个已跟踪白名单文件；另新增白名单 D_done.md、D_red_evidence.txt，未跟踪文件不计入上述 diff --stat。

```text
$ git status --porcelain=v1 --untracked-files=all
 M references/data-pipeline-evm-recon.md
 M references/playbook-entity-cluster-tiering.md
 M scripts/evm/peaks_daily.py
 M scripts/evm/replay_duck.py
 M scripts/report/audit_release_gate.py
 M scripts/tests/invariant_manifest.json
 M scripts/tests/test_audit_release_gate.py
 M scripts/tests/test_engine_equivalence.py
 M scripts/tests/test_peaks_daily.py
?? maintenance/repair-20260917-p0-four/D_done.md
?? maintenance/repair-20260917-p0-four/D_red_evidence.txt
```

## ⑦ 差异、保护范围与停工点

无施工范围差异，无停工点。D1/D2/D3 的工单代码块直接用于施工；D4-a 第 2/12 例维持真实 GREEN→GREEN，其余取证不制造 RED。D5 的 minimum_counts 从旧下限更新到实际扫描计数；既有登记内容与排列保持不变。

```text
build_events: 原文未变
emit_merged: 原文未变
replay_pass2: 原文未变
_peaks_python: 原文未变
replay_pass1: 仅抽取 deltas；SQL 文本逐字不变
audit_release_gate.py: check_daily_peaks 及新增辅助之外原文未变
references/data-pipeline-evm-recon.md: 仅第 132 行，字节变化 -13
references/playbook-entity-cluster-tiering.md: 仅第 149 行，字节变化 +9
日期戳保留
```

```text
D5: 移除三项精确增补并还原 minimum_counts 后，与开工 manifest 逐项一致（保留原排列）
minimum_counts 按实际：{"receipt_producers": 81, "receipt_consumers": 118, "transport_calls": 65, "atomic_writes": 61, "formal_entrypoints": 61}
白名单：11/11 文件；HEAD 仍为 f9b3800
```

机械核对确认 D4-a 仅 h 夹具及指定新块、D4-b 仅 followup_case/main 调用、D4-c 仅 needs 哈希检查。git diff --check 退出码 0，无输出。未 commit、push、stash、checkout、reset 或部署；contract_manifest.json、SKILL.md、commands-staging、VERSION、pyproject、CHANGELOG 及其他测试文件均未改。未跑 run_all.py、docs_lint、test_stage2_reseal.py；§4 的 APU 本机对照与 code_change_pending 登记由调度方验收，本段未执行。P2/P3/P13 仍为工单注明的另单项。

## ⑧ 禁读披露

启动时会话已预载 ~/.codex/memories/memory_summary.md 的摘要；实际还执行过一次对 /Users/uravvv/.codex/memories/MEMORY.md 的关键词检索（rg -n '施工 D|workorder_D|repair-20260917-p0-four'，退出码 1、无匹配输出）。已在过程中如实披露，之后未再访问 ~/.codex/；未将记忆作为施工依据。

未读取本仓库 archive/、blind-reviews/、.staging_*、references/attic.md 的内容，也未读取 /Users/uravvv/Desktop 下任何文件。references/attic.md 只在 §1.1 统计中通过 stat 读取大小。施工与全部验收均离线。
