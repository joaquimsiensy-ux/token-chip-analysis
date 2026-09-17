# 施工 A：完成

按 `workorder_A.md` 文件头 **v4** 完成 §0–§3。A1–A5 已落实，先 RED 后 GREEN；五个指定测试全部 PASS。没有停工点。

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`  
开工 HEAD：`f710fada900df16caecb82725264155116e98528`  
工单 SHA256：`399f5bcf6663db1f58c03384612797ba3f853a0ff3ab7f3c854985add28295d1`

## ① §0.1 两条基线命令原始输出

以下记录来自任何文件改动之前的实际执行；两条命令均 exit 0，stdout/stderr 均为空。

```console
$ git status --short
```

```console
$ git diff --stat 4cbfe48 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

### 施工前指定锚点核验

全部 13 个 `grep -n -F` 命中恰一处且行号一致，原始输出如下：

```text
$ grep -n -F 'FIG1_LEGEND_RECEIPT_SCHEMA = "figure1-legend/v1"' scripts/report/figures_from_facts.py
60:FIG1_LEGEND_RECEIPT_SCHEMA = "figure1-legend/v1"
$ grep -n -F 'def _load(p):' scripts/report/figures_from_facts.py
63:def _load(p):
$ grep -n -F '    with open(p, encoding="utf-8") as f:' scripts/report/figures_from_facts.py
64:    with open(p, encoding="utf-8") as f:
$ grep -n -F '        return json.load(f)' scripts/report/figures_from_facts.py
65:        return json.load(f)
$ grep -n -F '    state = _load(a.state)' scripts/report/figures_from_facts.py
109:    state = _load(a.state)
$ grep -n -F '            errs.append(f"{key} 线无 pct 数据")' scripts/report/figures_from_facts.py
306:            errs.append(f"{key} 线无 pct 数据")
$ grep -n -F '        last = float(pct[-1])' scripts/report/figures_from_facts.py
308:        last = float(pct[-1])
$ grep -n -F '    errs, okc = fig2_check_errors(Path(a.facts), Path(a.series), a.tol_pp)' scripts/report/figures_from_facts.py
328:    errs, okc = fig2_check_errors(Path(a.facts), Path(a.series), a.tol_pp)
$ grep -n -F 'def dumps_fig2_series(lines) -> bytes:' scripts/report/figures_from_facts.py
370:def dumps_fig2_series(lines) -> bytes:
$ grep -n -F '    return json.dumps(lines, ensure_ascii=False, sort_keys=True,' scripts/report/figures_from_facts.py
371:    return json.dumps(lines, ensure_ascii=False, sort_keys=True,
$ grep -n -F '                      separators=(",", ":")).encode("utf-8")' scripts/report/figures_from_facts.py
372:                      separators=(",", ":")).encode("utf-8")
$ grep -n -F 'def t_f04_tolpp_clamp():' scripts/tests/test_repair_batch_c.py
1201:def t_f04_tolpp_clamp():
$ grep -n -F '    t_fc5_receipt_chain()' scripts/tests/test_repair_batch_c.py
2106:    t_fc5_receipt_chain()
ANCHOR_CHECK: PASS (13 anchors)
```

## ② A1–A5 改前 → 改后及 git diff 原文

| 工项 | 改前 → 改后 | 下方原始 diff 对应位置 |
| --- | --- | --- |
| A1 | `_load` 宽松解析 → 默认严格拒绝 NaN/Infinity/-Infinity；新增 `_pct_value_ok`，bool/非数/非有限/超大整数返回 False；fig1 state 显式 `strict=False` | 生产文件前两个 hunk，基线 :60、:106 |
| A2 | 仅转换 pct 末点 → 检查 pct 全序列，非法值进入 errs/FAIL 收据；末点转换原样保留 | 生产文件第三个 hunk，基线 :305 |
| A3 | 输入 ValueError 直接传播 → 覆盖陈旧 PASS 为 FAIL；该新增分支写收据 OSError 提示“收据未更新”并 FAIL 退出 | 生产文件第四个 hunk，基线 :325 |
| A4 | 序列化可产生 NaN → `allow_nan=False`，拒绝非有限输出 | 生产文件第五个 hunk，基线 :369 |
| A5 | 没有 R08 用例 → 新增 13 个独立子函数、汇总函数与 main 调用；原测试保持原样 | 测试文件两个 hunk |

实际命令：`git diff -- scripts/report/figures_from_facts.py scripts/tests/test_repair_batch_c.py`。以下为完整原文，依次覆盖 A1–A5：

```diff
diff --git a/scripts/report/figures_from_facts.py b/scripts/report/figures_from_facts.py
index d9690b8..d4b8351 100644
--- a/scripts/report/figures_from_facts.py
+++ b/scripts/report/figures_from_facts.py
@@ -60,9 +60,25 @@ FIG1_LEGEND_RECEIPT_NAME = "fig1_legend_receipt.json"
 FIG1_LEGEND_RECEIPT_SCHEMA = "figure1-legend/v1"
 
 
-def _load(p):
+def _reject_constant(token):
+    """JSON 的 NaN/Infinity/-Infinity 字面量一律拒（标准 JSON 不允许；Python json 默认放行）。"""
+    raise ValueError(f"JSON 非有限数值字面量 {token} 拒收（NaN/Infinity）")
+
+
+def _pct_value_ok(v):
+    """pct 单点合法：非 bool 的 int/float，且可转为有限 float（超大整数转 float 的
+    OverflowError 也算非法——不能让它在检查阶段抛异常绕过 FAIL 收据分支）。"""
+    if isinstance(v, bool) or not isinstance(v, (int, float)):
+        return False
+    try:
+        return math.isfinite(float(v))
+    except OverflowError:
+        return False
+
+
+def _load(p, strict=True):
     with open(p, encoding="utf-8") as f:
-        return json.load(f)
+        return json.load(f, parse_constant=_reject_constant if strict else None)
 
 
 def _parse_date(s):
@@ -106,7 +122,7 @@ def _read_price_csv(path, cols=None):
 
 
 def mode_fig1(a):
-    state = _load(a.state)
+    state = _load(a.state, strict=False)
     css = state.get("camp_share_series") or {}
     dates, series_by_camp = css.get("dates"), css.get("series")
     if not dates or not series_by_camp:
@@ -305,6 +321,11 @@ def fig2_check_errors(facts_path: Path, series_path: Path, tol_pp: float) -> tup
         if not pct:
             errs.append(f"{key} 线无 pct 数据")
             continue
+        bad = [i for i, v in enumerate(pct) if not _pct_value_ok(v)]
+        if bad:
+            errs.append(f"{key} 线 pct[{bad[0]}] 非有限/非法数值 {pct[bad[0]]!r}"
+                        "（NaN/±Inf/bool/非数/超大整数一律拒，容差不豁免）")
+            continue
         last = float(pct[-1])
         cur = int(str(ent.get("current_raw", "0")))
         want = cur / facts.total_raw * 100 if facts.total_raw else 0.0
@@ -325,7 +346,19 @@ def mode_check(a):
         print(f"FAIL: 正式模式 --tol-pp 写死 {DEFAULT_TOL_PP}pp（收到 {a.tol_pp}）"
               f"——探索性放宽必须显式加 --exploration", file=sys.stderr)
         raise SystemExit(2)
-    errs, okc = fig2_check_errors(Path(a.facts), Path(a.series), a.tol_pp)
+    try:
+        errs, okc = fig2_check_errors(Path(a.facts), Path(a.series), a.tol_pp)
+    except ValueError as exc:
+        # 输入不可用也要留痕：覆盖同目录里可能残留的陈旧 PASS 收据（其输入 sha 仍匹配，
+        # 否则发布闸 check_figure2_receipt 会继续接受它）。两输入任一缺失/非常规文件时
+        # 无法取 sha，只报错不写收据；收据写入过程本身的 OSError（输入不可读、目录不可写、
+        # fsync/replace 失败）也不得吞掉 FAIL 退出——如实提示"收据未更新"。
+        if os.path.isfile(a.facts) and os.path.isfile(a.series):
+            try:
+                _write_check_receipt(a, "FAIL", 0, [f"输入不可用：{exc}"])
+            except OSError as io_exc:
+                print(f"[CHECK-FAIL] 收据未更新（写入失败：{io_exc}）", file=sys.stderr)
+        raise SystemExit(f"FAIL: 图 2 对账输入不可用——{exc}")
     if errs and errs[0] == "--series 应为图 2 whale_series JSON（list of lines）":
         raise SystemExit("FAIL: " + errs[0])
     if errs:
@@ -369,7 +402,7 @@ def build_fig2_series(entity_series_obj, facts_obj, keys) -> list:
 
 def dumps_fig2_series(lines) -> bytes:
     return json.dumps(lines, ensure_ascii=False, sort_keys=True,
-                      separators=(",", ":")).encode("utf-8")
+                      separators=(",", ":"), allow_nan=False).encode("utf-8")
 
 
 def _write_fig2_outputs(out, data, provenance):
diff --git a/scripts/tests/test_repair_batch_c.py b/scripts/tests/test_repair_batch_c.py
index 051354c..9f8a027 100644
--- a/scripts/tests/test_repair_batch_c.py
+++ b/scripts/tests/test_repair_batch_c.py
@@ -1198,6 +1198,318 @@ def t_fc5_receipt_chain():
               any("缺 facts 绑定" in x for x in errs), str(errs))
 
 
+def _r08_case_1():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        (td / "ws.json").write_text(
+            '[{"entity_id":"e1","ts":["2026-01-01"],"pct":[NaN]}]',
+            encoding="utf-8")
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        out = p.stdout + p.stderr
+        rcpt_path = td / "figure2_check_receipt.json"
+        rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
+        check("R08 NaN 末点必 FAIL",
+              p.returncode != 0 and "字面量" in out and rcpt.get("verdict") == "FAIL",
+              f"rc={p.returncode}; receipt={rcpt!r}\n{out}")
+
+
+def _r08_case_2():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        (td / "ws.json").write_text(
+            '[{"entity_id":"e1","ts":["2026-01-01","2026-01-02"],'
+            '"pct":[1e400,27.8]}]', encoding="utf-8")
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        out = p.stdout + p.stderr
+        rcpt_path = td / "figure2_check_receipt.json"
+        rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
+        check("R08 中间点 Inf 全序列拒",
+              p.returncode == 1 and "非有限" in out and rcpt.get("verdict") == "FAIL",
+              f"rc={p.returncode}; receipt={rcpt!r}\n{out}")
+
+
+def _r08_case_3():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        (td / "ws.json").write_text(
+            '[{"entity_id":"e1","ts":["2026-01-01"],"pct":["27.8"]}]',
+            encoding="utf-8")
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        out = p.stdout + p.stderr
+        rcpt_path = td / "figure2_check_receipt.json"
+        rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
+        check("R08 字符串 pct 拒",
+              p.returncode == 1 and "非有限" in out and rcpt.get("verdict") == "FAIL",
+              f"rc={p.returncode}; receipt={rcpt!r}\n{out}")
+
+
+def _r08_case_4():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        (td / "ws.json").write_text(
+            '[{"entity_id":"e1","ts":["2026-01-01"],"pct":[null]}]',
+            encoding="utf-8")
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        out = p.stdout + p.stderr
+        rcpt_path = td / "figure2_check_receipt.json"
+        rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
+        check("R08 null pct 拒且留痕",
+              p.returncode == 1 and rcpt.get("verdict") == "FAIL",
+              f"rc={p.returncode}; receipt={rcpt!r}\n{out}")
+
+
+def _r08_case_5():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        (td / "ws.json").write_text(
+            '[{"entity_id":"e1","ts":["2026-01-01"],"pct":[Infinity]}]',
+            encoding="utf-8")
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        out = p.stdout + p.stderr
+        rcpt_path = td / "figure2_check_receipt.json"
+        rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
+        mismatches = rcpt.get("mismatches") or []
+        check("R08 Infinity 字面量解析层拒",
+              p.returncode != 0 and "字面量" in out and rcpt.get("verdict") == "FAIL"
+              and bool(mismatches) and "输入不可用" in mismatches[0],
+              f"rc={p.returncode}; receipt={rcpt!r}\n{out}")
+
+
+def _r08_case_6():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        (td / "ws.json").write_text(
+            '[{"entity_id":"e1","ts":["2026-01-01"],"pct":[NaN]}]',
+            encoding="utf-8")
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json",
+                 "--exploration", "--tol-pp", "99"], td)
+        out = p.stdout + p.stderr
+        rcpt_path = td / "figure2_check_receipt.json"
+        rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
+        check("R08 exploration 放宽容差不豁免",
+              p.returncode != 0 and rcpt.get("verdict") == "FAIL"
+              and rcpt.get("mode") == "exploration",
+              f"rc={p.returncode}; receipt={rcpt!r}\n{out}")
+
+
+def _r08_case_7():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300", "x": NaN}}}', encoding="utf-8")
+        (td / "ws.json").write_text(
+            '[{"entity_id":"e1","ts":["2026-01-01"],"pct":[27.8]}]',
+            encoding="utf-8")
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        out = p.stdout + p.stderr
+        check("R08 facts 含 NaN 字面量同拒",
+              p.returncode != 0 and "字面量" in out, f"rc={p.returncode}\n{out}")
+
+
+def _r08_case_8():
+    import figures_from_facts as ffm
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        (td / "ws.json").write_text(
+            '[{"entity_id":"e1","ts":["d"],"pct":[NaN]}]', encoding="utf-8")
+        try:
+            blob = ffm.dumps_fig2_series(
+                [{"entity_id": "e1", "ts": ["d"], "pct": [float("nan")]}])
+        except ValueError:
+            check("R08 dumps_fig2_series 拒 NaN", True)
+        else:
+            check("R08 dumps_fig2_series 拒 NaN", False, f"未抛 ValueError: {blob!r}")
+
+
+def _r08_case_9():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        (td / "ws.json").write_text(
+            '[{"entity_id":"e1","ts":["2026-01-01"],"pct":[27.8]}]',
+            encoding="utf-8")
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        out = p.stdout + p.stderr
+        rcpt_path = td / "figure2_check_receipt.json"
+        rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
+        check("R08 合法序列仍 PASS",
+              p.returncode == 0 and rcpt.get("verdict") == "PASS",
+              f"rc={p.returncode}; receipt={rcpt!r}\n{out}")
+
+
+def _r08_case_10():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        ws = td / "ws.json"
+        ws.write_text('[{"entity_id":"e1","ts":["2026-01-01"],"pct":[27.8]}]',
+                      encoding="utf-8")
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        rcpt_path = td / "figure2_check_receipt.json"
+        rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
+        check("R08 换输入前 PASS 收据在场",
+              p.returncode == 0 and rcpt.get("verdict") == "PASS",
+              f"rc={p.returncode}; receipt={rcpt!r}\n{p.stdout}{p.stderr}")
+        ws.write_text('[{"entity_id":"e1","ts":["2026-01-01"],"pct":[NaN]}]',
+                      encoding="utf-8")
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        out = p.stdout + p.stderr
+        rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
+        check("R08 陈旧 PASS 收据被 FAIL 覆盖（换输入）",
+              p.returncode != 0 and rcpt.get("verdict") == "FAIL"
+              and rcpt.get("series", {}).get("sha256") == hashlib.sha256(ws.read_bytes()).hexdigest(),
+              f"rc={p.returncode}; receipt={rcpt!r}\n{out}")
+
+
+def _r08_case_11():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        (td / "ws.json").write_text(
+            '[{"entity_id":"e1","ts":["2026-01-01","2026-01-02","2026-01-03"],'
+            '"pct":[1e400,1' + '0' * 400 + ',27.8]}]', encoding="utf-8")
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        out = p.stdout + p.stderr
+        rcpt_path = td / "figure2_check_receipt.json"
+        rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
+        check("R08 超大整数不抛异常、走 FAIL 收据",
+              p.returncode == 1 and ("非法数值" in out or "非有限" in out)
+              and "OverflowError" not in out and rcpt.get("verdict") == "FAIL",
+              f"rc={p.returncode}; receipt={rcpt!r}\n{out}")
+
+
+def _r08_case_12():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    import audit_release_gate as gate
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        facts = td / "facts.json"
+        facts.write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        ws = td / "ws.json"
+        ws.write_text('[{"entity_id":"e1","ts":["2026-01-01"],"pct":[NaN]}]',
+                      encoding="utf-8")
+        rcpt_path = td / "figure2_check_receipt.json"
+        handwritten = {
+            "schema": "figure2-check-receipt/v1", "mode": "formal",
+            "tol_pp": 0.05, "verdict": "PASS",
+            "facts": {"path": "facts.json", "sha256": hashlib.sha256(facts.read_bytes()).hexdigest()},
+            "series": {"path": "ws.json", "sha256": hashlib.sha256(ws.read_bytes()).hexdigest()},
+        }
+        rcpt_path.write_text(json.dumps(handwritten), encoding="utf-8")
+        errs = []
+        gate.check_figure2_receipt(td, handwritten, errs)
+        check("R08 同输入手写 PASS 基线消费者接受", errs == [], str(errs))
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        out = p.stdout + p.stderr
+        rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
+        errs2 = []
+        gate.check_figure2_receipt(td, rcpt, errs2)
+        check("R08 同输入陈旧 PASS 收据被覆盖且消费者拒",
+              p.returncode != 0 and rcpt.get("verdict") == "FAIL"
+              and any("非 PASS" in x for x in errs2),
+              f"rc={p.returncode}; receipt={rcpt!r}; consumer={errs2!r}\n{out}")
+
+
+def _r08_case_13():
+    import argparse
+    import contextlib
+    import io
+    from unittest import mock
+    import figures_from_facts as ffm
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        (td / "facts.json").write_text(
+            '{"token":{"symbol":"TT","decimals":0,"total_supply_raw":"1000"},'
+            '"entities":{"e1":{"label":"大庄#1","addresses":["' + A + '"],'
+            '"current_raw":"278","peak_raw":"300"}}}', encoding="utf-8")
+        (td / "ws.json").write_text(
+            '[{"entity_id":"e1","ts":["2026-01-01"],"pct":[NaN]}]',
+            encoding="utf-8")
+        ns = argparse.Namespace(facts=str(td / "facts.json"), series=str(td / "ws.json"),
+                                tol_pp=0.05, exploration=False)
+        buf = io.StringIO()
+        caught = None
+        with mock.patch.object(ffm, "_write_check_receipt", side_effect=OSError("disk full")), \
+                contextlib.redirect_stderr(buf):
+            try:
+                ffm.mode_check(ns)
+            except (SystemExit, OSError) as e:
+                caught = e
+        detail = f"exception={caught!r}; stderr={buf.getvalue()!r}"
+        check("R08 收据写入失败仍 FAIL 退出", isinstance(caught, SystemExit), detail)
+        check("R08 收据写入失败保留 FAIL 原因",
+              isinstance(caught.code, str) and caught.code.startswith("FAIL:"), detail)
+        check("R08 收据写入失败提示未更新", "收据未更新" in buf.getvalue(), detail)
+
+
+def t_r08_nonfinite():
+    _r08_case_1()
+    _r08_case_2()
+    _r08_case_3()
+    _r08_case_4()
+    _r08_case_5()
+    _r08_case_6()
+    _r08_case_7()
+    _r08_case_8()
+    _r08_case_9()
+    _r08_case_10()
+    _r08_case_11()
+    _r08_case_12()
+    _r08_case_13()
+
+
 def t_f04_tolpp_clamp():
     """--tol-pp 同族钳制（同 F-02 模式）：formal 写死默认值，仅 --exploration 可覆盖。"""
     fff = ROOT / "scripts/report/figures_from_facts.py"
@@ -2104,6 +2416,7 @@ def main():
     t_f09_importer_fail_closed()
     t_fixround1()
     t_fc5_receipt_chain()
+    t_r08_nonfinite()
     t_fixround2()
     print(f"PASS: repair batch C (F-05+F-04+fixround1+fixround2) "
           f"{len(PASSED)} checks")
```

## ③ RED 证据与 GREEN 对应

路径：`maintenance/repair-20260917-p0-four/A_red_evidence.txt`。

改生产代码前，内联 Python 逐个调用 `_r08_case_1()` … `_r08_case_13()`，分别捕获 `AssertionError` 后继续。证据文件含可复现命令、被测生产文件与测试文件 SHA256、各用例失败异常原文及汇总。

```text
SUMMARY: FAIL=12 [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13]; PASS=1 [9]
```

- 工单要求的 1/2/3/4/6/10/11/12/13 均取得真实 RED；5/7/8 也按预期 RED，9 是合法输入回归绿例。
- 用例 1/2/3/6/7/10/11/12 基线错误放行；4 为 TypeError 且无收据；5 已 FAIL 但没有解析层“输入不可用”留痕；8 输出含 NaN；13 捕获 `OSError('disk full')`，不是 `SystemExit`，由第一条 check 记录失败。
- RED 阶段实际核验 `git diff --exit-code HEAD -- scripts/report/figures_from_facts.py` 为 exit 0、输出为空，生产文件仍是基线。
- GREEN 阶段测试文件 SHA256 与 RED 完全相同。完整批 C 的 `main()` 调用全部 13 个用例，244 checks 全通过；没有改断言或改 RED 夹具获取 GREEN。

| 文件 | SHA256 |
| --- | --- |
| 生产文件（RED 基线） | `0ba4e6607cbb8211a0e03311bdfa9dc61d1623bac7f289b7406e48f448213bd8` |
| 生产文件（GREEN） | `557c7099ccec38615771da8fd64facd83deab93928dda0aa2e6c9e6b6a28a9e0` |
| 测试文件（RED/GREEN 相同） | `ffd5a94e277acb2b930a964178cdac19df9c03bfd205e383a796e51952bc0b01` |
| RED 证据文件 | `a45a5a80d56d9e092895299549db30ef4d4f5356a2b23a9058c67a0029a1f30a` |

## ④ §0.8 五个定向测试结果尾行

五个命令顺序实际执行，无跳过、无重试，退出码全部为 0：

命令：`python3 -B scripts/tests/test_repair_batch_c.py`；退出码 0；耗时 30.49 秒。

```text
PASS: repair batch C (F-05+F-04+fixround1+fixround2) 244 checks
```

命令：`python3 -B scripts/tests/test_stage2_closeout.py`；退出码 0；耗时 34.87 秒。

```text
stage2_closeout: 27/27 PASS
```

命令：`python3 -B scripts/tests/test_figures_from_facts.py`；退出码 0；耗时 5.57 秒。

```text
PASS: figures_from_facts fig1白名单/legacy销毁键/legend receipt/burn豁免/overlay组成/价格绑定/flow宏同源/check终值对账全过
```

命令：`python3 -B scripts/tests/test_repair_batch1.py`；退出码 0；耗时 2.45 秒。

```text
PASS v6.41.0 batch1 steps 1-6 RV-07/RV-04/RV-17/F-03/F-01/A5v3/F-04
```

命令：`python3 -B scripts/tests/test_repair_batch_d.py`；退出码 0；耗时 15.86 秒。

```text
BATCH D 全部通过
```

运行时设置 `PYTHONDONTWRITEBYTECODE=1`，避免子进程生成仓库 pycache；GREEN 的 `MPLCONFIGDIR` 指向系统临时目录，仅供 Matplotlib 缓存。RED 中默认 Matplotlib 目录不可写而自动改用临时目录的提示保留在原始证据中；GREEN 的字体 fallback 提示、批 C/批 1 的故障注入诊断均未导致测试失败。未运行 `run_all.py`，全套验收仍由调度方执行。

## ⑤ §1.1 文档三处字节数

施工前与施工后均实际运行工单给定的元数据命令，三个输出完全一致：

```console
$ stat -f %z SKILL.md
8021
$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930070
$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
```

## ⑥ git diff --stat 与改动边界

```text
 scripts/report/figures_from_facts.py |  43 ++++-
 scripts/tests/test_repair_batch_c.py | 313 +++++++++++++++++++++++++++++++++++
 2 files changed, 351 insertions(+), 5 deletions(-)
```

`git diff --stat` 中只有两个白名单内的跟踪文件。另新建白名单内 `A_red_evidence.txt` 与本报告 `A_done.md`，未跟踪文件不会出现在该命令输出中。

额外机械核验：生产文件逐字节等于 HEAD 加上工单 A1/A2/A3 原文与 A4 的 `allow_nan=False`；测试文件移除 A5 的两个插入点后逐字节等于 HEAD。因此既有 `t_fc5_receipt_chain`、`t_f04_tolpp_clamp` 的全部断言以及其他既有测试均未改变。生产受保护常量、收据 schema/写法、线与实体匹配逻辑、fig1 豁免键检查均原样保留。`git diff --check` 实际执行通过，工作树路径检查仅含白名单文件。

## ⑦ 与工单差异、停工点及范围外登记

与工单施工内容无差异；无停工点。离线完成；未 commit、push、部署 commands，未使用 stash/checkout/reset，未改两个 manifest。

按工单 §0.4/§4 仅登记、未修复下列边界；未写调度方维护的 `code_change_pending.md`：

- 收据消费者不验 `lines_checked>0` 与实体线覆盖完整性；批 D 的空 series 端到端用例仍通过。工单注明这是已接受残余，本轮未另读 split-run 文档。
- `stage2_closeout.py` 的裸 `json.loads`（工单基线 :63、调用 :459/:468）。
- fig1 state 非豁免键 NaN 维持基线行为。
- 非 pct 字段中的 `1e400` 不受 `parse_constant` 覆盖；本段只对 pct 数值与输出序列封口。
- fig1 豁免键超大整数的 `math.isfinite` 溢出边界。
- 普通 PASS/FAIL 分支写收据的 OSError 仍直接传播；A3 仅收敛新增输入失败分支。

## ⑧ 禁读披露

启动上下文已自动提供 memory 摘要，开工时已向用户披露一次；本轮没有通过工具读取 `~/.codex/` 下任何文件，也未使用历史记忆结论替代现场核验。

未主动读取仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容；文档字节数仅以 `stat` 元数据累计。五个获准测试按工单运行，其内部文档遍历属于用户明确允许的范围。
