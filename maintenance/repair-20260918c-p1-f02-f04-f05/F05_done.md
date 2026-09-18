# 施工 F05：完成

按工单 F05 v3 完成白名单内施工。价格双源收据新增主价格文件哈希；closeout 从 points 重算 verdict，拒绝 FAIL、ALL_SKIP、旧收据、哈希错绑和无收据引用的纯申报对象，WARN 放行并写 NOTE。先取 RED，再改生产代码；六项定向测试全部首次 PASS。

工单目录：`maintenance/repair-20260918c-p1-f02-f04-f05`。
开工及完成时 HEAD：`87f962b653104faa1facbd1aca4540a1f95d9871`；分支：`main`。未 commit、push、部署，未执行 stash、checkout、reset。

**① §0.1 开工基线（修改前的原始输出）**

```console
$ git rev-parse HEAD
87f962b653104faa1facbd1aca4540a1f95d9871
```

```console
$ git branch --show-current
main
```

```console
$ git status --short
```

上条 stdout 为空，工作区干净。

按派工提示词对 §0.1 第二项的修正口径，广范围差异恰好仅含已入库 F04 三文件：

```console
$ git diff --stat 8b041842 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
 scripts/lib/net.py                           |  5 +-
 scripts/lib/rpc_batch.py                     | 10 ++--
 scripts/tests/test_batch1_rpc_attestation.py | 71 ++++++++++++++++++++++++++++
 3 files changed, 82 insertions(+), 4 deletions(-)
```

F05 白名单三文件相对内容基线无差异：

```console
$ git diff --stat 8b041842 HEAD -- scripts/prices/price_check.py scripts/report/stage2_closeout.py scripts/tests/test_stage2_closeout.py
```

工单正文中的原范围也无差异：

```console
$ git diff --stat 8b041842 HEAD -- scripts/prices scripts/report/stage2_closeout.py scripts/tests/test_stage2_closeout.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

后两条 stdout 均为空、退出码均为 0。14 个锚均以 `grep -n -F` 逐项核查，唯一匹配且基线行号完全一致：

```text
PASS scripts/prices/price_check.py:27: ['27:（来源：A9 小工程件，2026-07-22；QUQ CG vs DefiLlama 实测通过）"""']
PASS scripts/prices/price_check.py:30: ['30:import datetime']
PASS scripts/prices/price_check.py:46: ['46:def _load_series(path):']
PASS scripts/prices/price_check.py:185: ['185:           "points": results, "verdict": verdict}']
PASS scripts/report/stage2_closeout.py:238: ['238:def amendment_errors(row, field):']
PASS scripts/report/stage2_closeout.py:350: ['350:    if "price_source_checks" in bindings:']
PASS scripts/report/stage2_closeout.py:354: ['354:        need("bindings.price_source_checks|price_source.dual_source_check", "双源检查对象在场", dual, isinstance(dual, dict))']
PASS scripts/tests/test_stage2_closeout.py:15: ['15:sys.path[:0] = [str(HERE), str(REPO / "scripts/report"), str(REPO / "scripts/lib")]']
PASS scripts/tests/test_stage2_closeout.py:93: ['93:def build_closeout_case(root) -> Path:']
PASS scripts/tests/test_stage2_closeout.py:100: ['100:    write(case / "price_series.json", [[1767225600, 1.0]])']
PASS scripts/tests/test_stage2_closeout.py:102: ['102:    write(case / "price_checks.json", {"status": "PASS"})']
PASS scripts/tests/test_stage2_closeout.py:534: ['534:    obj["bindings"]["price_source"]["dual_source_check"] = {"status": "PASS"}']
PASS scripts/tests/test_stage2_closeout.py:605: ['605:def facts_vs_ledgers_rejects_hand_edit(cases):']
PASS scripts/tests/test_stage2_closeout.py:631: ['631:         facts_vs_ledgers_rejects_hand_edit]']
ANCHORS: 14/14 PASS
```

开工 invariant 扫描：

```console
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

**② §2 各处 git diff 原文**

包含 §2.1 生产者、§2.2 消费者、§2.3 真实生产者夹具及 §2.5 新用例。§2.4 所述 mutation 未改。

```diff
diff --git a/scripts/prices/price_check.py b/scripts/prices/price_check.py
index fb7c364..44c12a5 100644
--- a/scripts/prices/price_check.py
+++ b/scripts/prices/price_check.py
@@ -24,10 +24,12 @@
   python3 price_check.py --price-file data/cg_price_365d.json --source coingecko \
       --chain bsc --addr 0x4fa7... [--second defillama|binance] \
       [--binance-symbol CAKEUSDT] [--points 3] [--proxy URL] [--out check.json]
+收据（--out）含 price_file_sha256——stage2_closeout 用它把收据绑定到工单 bindings.price_source，并重算 verdict（F05）。
 （来源：A9 小工程件，2026-07-22；QUQ CG vs DefiLlama 实测通过）"""
 import argparse
 import csv
 import datetime
+import hashlib
 import json
 import os
 import sys
@@ -43,6 +45,14 @@ BINANCE_KLINES = "https://data-api.binance.vision/api/v3/klines"
 LLAMA_HIST = "https://coins.llama.fi/prices/historical"
 
 
+def _sha256_file(path):
+    h = hashlib.sha256()
+    with open(path, "rb") as f:
+        for chunk in iter(lambda: f.read(1 << 20), b""):
+            h.update(chunk)
+    return h.hexdigest()
+
+
 def _load_series(path):
     """价格文件 → [(ts_sec, price)] 升序。格式自适应，认不出硬退。"""
     if path.endswith(".csv"):
@@ -182,6 +192,7 @@ def main():
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "price_file": os.path.abspath(a.price_file), "main_source": a.source,
            "second_source": second, "thresholds": {"warn_pct": WARN_PCT, "fail_pct": FAIL_PCT},
+           "price_file_sha256": _sha256_file(a.price_file),
            "points": results, "verdict": verdict}
     if a.out:
         with open(a.out, "w") as f:
diff --git a/scripts/report/stage2_closeout.py b/scripts/report/stage2_closeout.py
index f48b7ce..9330f06 100644
--- a/scripts/report/stage2_closeout.py
+++ b/scripts/report/stage2_closeout.py
@@ -235,6 +235,59 @@ def flow_selection_errors(facts, flow):
     return errors, notes
 
 
+PRICE_POINT_STATUSES = ("PASS", "WARN", "SKIP", "FAIL")
+
+
+def price_receipt_errors(case, bindings):
+    """F05：价格双源收据必须是 price_check.py 产物且结论可放行——从 points 按 price_check 同规则
+    重算 verdict 并要求一致；只放行 PASS/WARN（WARN 记 NOTE）；price_file_sha256 须等于
+    bindings.price_source.sha256；引用取 bindings.price_source_checks，否则取内联
+    price_source.dual_source_check.receipt；两者皆无＝纯申报对象，拒。返回 (errors, notes, ref)。"""
+    errors, notes = [], []
+    price_source = bindings.get("price_source") if isinstance(bindings.get("price_source"), dict) else {}
+    ref = bindings.get("price_source_checks")
+    if ref is None:
+        inline = price_source.get("dual_source_check")
+        ref = inline.get("receipt") if isinstance(inline, dict) else None
+    if not (isinstance(ref, dict) and isinstance(ref.get("path"), str)
+            and isinstance(ref.get("sha256"), str) and ref["sha256"]):
+        errors.append(workorder_error("bindings.price_source_checks|price_source.dual_source_check.receipt",
+                                      "price_check.py 收据引用 {path,sha256}（纯申报对象不放行）", ref))
+        return errors, notes, None
+    try:
+        receipt = load(case, ref["path"])
+    except (OSError, ValueError) as exc:
+        errors.append(workorder_error("bindings.price_source_checks.path", "可读取的收据 JSON", str(exc)))
+        return errors, notes, ref
+    points = receipt.get("points") if isinstance(receipt, dict) else None
+    if not isinstance(points, list) or not points:
+        errors.append(workorder_error("bindings.price_source_checks.points", "非空 list", points))
+        return errors, notes, ref
+    statuses = [(p.get("status") if isinstance(p, dict) else None) for p in points]
+    expected = ("FAIL" if any(s not in PRICE_POINT_STATUSES or s == "FAIL" for s in statuses)
+                else "ALL_SKIP" if all(s == "SKIP" for s in statuses)
+                else "WARN" if "WARN" in statuses else "PASS")
+    if receipt.get("verdict") != expected:
+        errors.append(workorder_error("bindings.price_source_checks.verdict",
+                                      f"与 points 重算一致（{expected}）", receipt.get("verdict")))
+    if expected not in ("PASS", "WARN"):
+        errors.append(workorder_error("bindings.price_source_checks.verdict",
+                                      "PASS|WARN（FAIL/ALL_SKIP 禁入装配：换源或人工裁决后重跑 price_check）", expected))
+    for key in ("main_source", "second_source"):
+        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
+            errors.append(workorder_error(f"bindings.price_source_checks.{key}", "非空字符串", receipt.get(key)))
+    bound = receipt.get("price_file_sha256")
+    if not isinstance(bound, str) or not bound:
+        errors.append(workorder_error("bindings.price_source_checks.price_file_sha256",
+                                      "在场（旧收据无此字段：用当前 price_check.py 重跑）", bound))
+    elif bound != price_source.get("sha256"):
+        errors.append(workorder_error("bindings.price_source_checks.price_file_sha256",
+                                      f"= bindings.price_source.sha256 {price_source.get('sha256')}", bound))
+    if not errors and expected == "WARN":
+        notes.append(f"NOTE: 价格双源 WARN 点 {statuses.count('WARN')} 个（>5% 过目口径，见 report-template 2b）")
+    return errors, notes, ref
+
+
 def amendment_errors(row, field):
     errors = []
     if not isinstance(row, dict):
@@ -347,11 +400,11 @@ def workorder_errors(case, report_rel, workorder_rel=WORKORDER, *, obj=None, fac
     price2_path = price2.get("path") if isinstance(price2, dict) else price2
     need("fig2.price_source|price", f"与 bindings.price_source.path={price_path} 同路径",
          price2_path, isinstance(price_path, str) and price2_path == price_path)
-    if "price_source_checks" in bindings:
-        required_refs.append(("bindings.price_source_checks", bindings["price_source_checks"]))
-    else:
-        dual = price_source.get("dual_source_check") if isinstance(price_source, dict) else None
-        need("bindings.price_source_checks|price_source.dual_source_check", "双源检查对象在场", dual, isinstance(dual, dict))
+    price_errors, price_notes, price_ref = price_receipt_errors(case, bindings)
+    errors.extend(price_errors)
+    notes.extend(price_notes)
+    if price_ref is not None:
+        required_refs.append(("bindings.price_source_checks", price_ref))
 
     def self_reference(field, ref):
         return (field == "fig3.events_input" and isinstance(ref, dict)
diff --git a/scripts/tests/test_stage2_closeout.py b/scripts/tests/test_stage2_closeout.py
index fed31f2..d212b0d 100644
--- a/scripts/tests/test_stage2_closeout.py
+++ b/scripts/tests/test_stage2_closeout.py
@@ -12,7 +12,7 @@ import tempfile
 
 HERE = Path(__file__).resolve().parent
 REPO = HERE.parent.parent
-sys.path[:0] = [str(HERE), str(REPO / "scripts/report"), str(REPO / "scripts/lib")]
+sys.path[:0] = [str(HERE), str(REPO / "scripts/report"), str(REPO / "scripts/lib"), str(REPO / "scripts/prices")]
 os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
 os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="w2-mpl-"))
 import test_a4_gate as fixture
@@ -90,6 +90,21 @@ def cli(case, command="check", *args):
     return run_formal_script(CLOSEOUT, [command, "--case-dir", str(case), "--report", "report.md", *args])
 
 
+def write_price_receipt(case, second_price, out="price_checks.json", prices="price_series.json"):
+    """F05：收据由真实 price_check.py 生成（第二源离线 stub），不手写 PASS。返回退出码（PASS/WARN 0、FAIL 2、ALL_SKIP 3、fatal 1）。"""
+    import price_check
+    from unittest import mock
+    argv = ["price_check.py", "--price-file", str(case / prices), "--source", "coingecko",
+            "--chain", "bsc", "--addr", "0x" + "1" * 40, "--out", str(case / out)]
+    with mock.patch.object(sys, "argv", argv), mock.patch.object(
+            price_check, "second_llama", return_value=(second_price, "offline")):
+        try:
+            price_check.main()
+            return 0
+        except SystemExit as exc:
+            return int(exc.code) if isinstance(exc.code, int) else 1
+
+
 def build_closeout_case(root) -> Path:
     case = build_release_case(root)
     write(case / "entity_series.json", {"dates": ["2026-01-01"], "e1": [100.0]})
@@ -97,9 +112,9 @@ def build_closeout_case(root) -> Path:
         "--keys", "e1", "--labels-from", str(case / "facts.json"), "--out", str(case / "whale_series.json")])
     assert proc.returncode == 0, proc.stdout + proc.stderr
     write(case / "flow_e1.json", {"title": "{{e1.label}}", "nodes": [], "edges": []})
-    write(case / "price_series.json", [[1767225600, 1.0]])
+    write(case / "price_series.json", [[1767225600, 1.0], [1767312000, 1.0], [1767398400, 1.0]])
     write(case / "volume_series.json", [[1767225600, 10]])
-    write(case / "price_checks.json", {"status": "PASS"})
+    assert write_price_receipt(case, second_price=1.0) == 0
     report = case / "report.md"
     report.write_text(report.read_text(encoding="utf-8") +
         "\n私人主桶 100.00%，私人尘埃 0.00%，公共设施 0.00%，未识别合约 0.00%，销毁哨兵 0.00%；"
@@ -531,7 +546,8 @@ def workorder_reference_contracts(cases):
     for old, new in (("final_distribution_scan", "final_scan"), ("final_distribution_png", "terminal_distribution_chart")):
         obj["bindings"][new] = obj["bindings"].pop(old)
     obj["bindings"].pop("price_source_checks")
-    obj["bindings"]["price_source"]["dual_source_check"] = {"status": "PASS"}
+    obj["bindings"]["price_source"]["dual_source_check"] = {
+        "receipt": {"path": "price_checks.json", "sha256": sha(case / "price_checks.json")}, "verdict": "PASS"}
     obj["fig2"]["price"] = {"path": obj["fig2"].pop("price_source")}
     obj["fig3"]["price_input"] = obj["fig3"].pop("price")
     obj["fig3"]["volume_input"] = obj["fig3"].pop("volume")
@@ -602,6 +618,60 @@ def amend_rechecks_all_and_is_atomic(cases):
     assert len(checks) == 12 and checks["facts_gate"]["status"] == "BLOCK"
 
 
+def price_receipt_content_enforced(cases):
+    """F05：真实 price_check 收据的结论/绑定被 closeout 语义消费；纯申报对象不放行。"""
+    import stage2_closeout as closeout
+    case = cases.fresh()
+
+    def rebind():
+        obj = read(case / "a5_assembly_workorder.json")
+        obj["bindings"]["price_source_checks"]["sha256"] = sha(case / "price_checks.json")
+        write(case / "a5_assembly_workorder.json", obj)
+        return closeout.workorder_errors(case, "report.md")
+
+    # 1 真实 FAIL 收据（主 1.0/副 2.0 → 66.67%）退出 2；绑定后 workorder 与完整 check 均 BLOCK
+    assert write_price_receipt(case, second_price=2.0) == 2
+    errors, _ = rebind()
+    assert any("price_source_checks.verdict" in e for e in errors), errors
+    row = check_result(case, 2)["workorder"]
+    assert "price_source_checks.verdict" in detail(row), row
+    # 2 手改 verdict=PASS 但 points 含 FAIL → 重算不一致
+    update(case, "price_checks.json", lambda r: r.update(verdict="PASS"))
+    errors, _ = rebind()
+    assert any("重算一致" in e for e in errors), errors
+    # 3 WARN 收据（主 1.0/副 1.08 → 7.69%）放行并记 NOTE
+    assert write_price_receipt(case, second_price=1.08) == 0
+    errors, notes = rebind()
+    assert not errors, errors
+    assert any("WARN 点 3" in n for n in notes), notes
+    # 4 price_file_sha256 与工单主源不一致
+    update(case, "price_checks.json", lambda r: r.update(price_file_sha256="0" * 64))
+    errors, _ = rebind()
+    assert any("price_file_sha256" in e and "= bindings.price_source.sha256" in e for e in errors), errors
+    # 5 旧收据（无 price_file_sha256）
+    update(case, "price_checks.json", lambda r: r.pop("price_file_sha256"))
+    errors, _ = rebind()
+    assert any("price_file_sha256" in e and "在场" in e for e in errors), errors
+    # 6 全 SKIP → ALL_SKIP 退出 3；绑定后 BLOCK
+    assert write_price_receipt(case, second_price=None) == 3
+    errors, _ = rebind()
+    assert any("ALL_SKIP" in e for e in errors), errors
+    # 7 内联纯申报对象拒；内联带 receipt（ARC 形态）放行
+    assert write_price_receipt(case, second_price=1.0) == 0
+    obj = read(case / "a5_assembly_workorder.json")
+    obj["bindings"].pop("price_source_checks")
+    obj["bindings"]["price_source"]["dual_source_check"] = {"status": "PASS"}
+    write(case / "a5_assembly_workorder.json", obj)
+    errors, _ = closeout.workorder_errors(case, "report.md")
+    assert any("dual_source_check.receipt" in e for e in errors), errors
+    obj["bindings"]["price_source"]["dual_source_check"] = {
+        "receipt": {"path": "price_checks.json", "sha256": sha(case / "price_checks.json")}, "verdict": "PASS"}
+    write(case / "a5_assembly_workorder.json", obj)
+    errors, _ = closeout.workorder_errors(case, "report.md")
+    assert not errors, errors
+    check_result(case)
+
+
 def facts_vs_ledgers_rejects_hand_edit(cases):
     case = cases.fresh()
     update(case, "facts.json", lambda obj: obj["entities"]["e1"].update(current_raw="90"))
@@ -628,7 +698,7 @@ TESTS = [dryrun_profile_exempts_stage3_artifacts, only_findings_changed_is_rejec
          downstream_check_cli_exit3, amendments_chain_gap_rejected,
          workorder_reference_contracts, receipt_shape_and_fill_nulls,
          caption_raw_rounding_and_pure_series_errors, amend_rechecks_all_and_is_atomic,
-         facts_vs_ledgers_rejects_hand_edit]
+         facts_vs_ledgers_rejects_hand_edit, price_receipt_content_enforced]
 
 
 def main():
```

**③ RED 摘要（逐段独立执行）**

完整证据：[F05_red_evidence.txt](F05_red_evidence.txt)。执行前已完成 §2.3 全部变更，包括三日价格夹具，并加入 §2.5 新用例；两个生产文件仍与 HEAD / 8b041842 逐字节一致。每段先确认真实生产者退出码、三点收据，再执行独立消费端断言；每段各自 try/except，7a 与 7b 分开执行。第二源为离线 stub。

| 段 | 生产者预置与退出码 | 基线消费结果 | 修改后 |
| --- | --- | --- | --- |
| 1 | 主 1.0 / 副 2.0，FAIL，exit 2，三点 66.67% | workorder 未报错；完整 check 错放 PASS / exit 0；两项断言 RED | workorder 与完整 check BLOCK |
| 2 | 独立 PASS / exit 0 初始化；再生成真实 FAIL / exit 2 并手改 verdict=PASS | 未核 points 与 verdict 一致性，RED | 拒绝重算不一致 |
| 3 | 主 1.0 / 副 1.08，WARN，exit 0，三点 7.69% | 放行但缺 WARN 点 3 NOTE，RED | 放行且记 NOTE |
| 4 | PASS，exit 0；收据主源哈希设为 64 个 0 | 未拒错绑，RED | 拒绝主源哈希不一致 |
| 5 | PASS，exit 0；基线生产者本就不含 price_file_sha256 | 未拒旧收据，RED | 拒绝缺字段 |
| 6 | 副源 None，ALL_SKIP，exit 3 | 未拒 ALL_SKIP，RED | 拒绝 ALL_SKIP |
| 7a | PASS，exit 0；删顶层引用，仅留内联纯申报 dict | 未拒纯申报，RED | 拒绝缺 receipt |
| 7b | PASS，exit 0；内联带真实收据引用 | GREEN；完整 check PASS、12 项 | GREEN；完整 check PASS |

RED 取证进程 exit 0、结尾 `RED_EVIDENCE PASS`，生产代码在取证结束时仍未修改。修改后 `price_receipt_content_enforced` 完整用例 PASS。

**④ §0.8 定向测试结果尾行**

```console
$ python3 -B scripts/tests/test_stage2_closeout.py
stage2_closeout: 29/29 PASS
```
退出码：0；首次执行 PASS。

```console
$ python3 -B scripts/tests/test_a4_gate.py
a4_gate 契约测试全部通过（23 项）
```
退出码：0；首次执行 PASS。

```console
$ python3 -B scripts/tests/test_audit_release_gate.py
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
```
退出码：0；首次执行 PASS。

```console
$ python3 -B scripts/tests/test_batch4_invariant_guards.py
PASS B4-G1: bare pool / labels / vertical slice / denominator injections
```
退出码：0；首次执行 PASS。

```console
$ python3 -B scripts/tests/test_exemption_guards.py
PASS: exemption guards (EX-01 full-F-03)
```
退出码：0；首次执行 PASS。

```console
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```
退出码：0；首次执行 PASS。

`test_stage2_closeout.py` 输出同时确认 `ok    workorder_reference_contracts` 与 `ok    price_receipt_content_enforced`。原有 19 条 mutation 全部保持 BLOCK 且错误文案含对应 field；内联 receipt 正例通过。closeout 收据仍为 12 项 checks。

未出现 `data_broken: '_items'`，无需冷字体缓存重跑；没有失败首轮输出需要保留。
未跑 `run_all.py`。**reseal 未实跑、交调度方本机补验**：按 R1-03，在本段提交后，主仓库干净且 `/tmp/w3_acceptance` 同 HEAD 时由调度方执行 `test_stage2_reseal.py`。该测试文件未修改。

**⑤ §1.1 文档字节数**

开工与收尾均仅用文件大小元数据求和：

| 路径 | 开工字节 | 完成字节 |
| --- | ---: | ---: |
| SKILL.md | 8021 | 8021 |
| references/**/*.md | 930076 | 930076 |
| commands-staging/*.md | 8798 | 8798 |

`git diff --exit-code HEAD -- references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md scripts/tests/test_stage2_reseal.py scripts/report/audit_release_gate.py scripts/report/build_html.py contract_manifest.json invariant_manifest.json` 退出 0、stdout 为空。跟踪文件差异集合也仅有白名单三个 Python 文件，其他路径未改。

**⑥ git diff --stat**

```console
$ git diff --stat
 scripts/prices/price_check.py         | 11 +++++
 scripts/report/stage2_closeout.py     | 63 ++++++++++++++++++++++++---
 scripts/tests/test_stage2_closeout.py | 80 ++++++++++++++++++++++++++++++++---
 3 files changed, 144 insertions(+), 10 deletions(-)
```

`git diff --stat` 不包含未跟踪文件；新增交付文件仅为本工单目录内 `F05_done.md` 和 `F05_red_evidence.txt`。未生成停工报告。

`git diff --check` 退出 0、stdout 为空。

**⑦ 与工单差异、作用域核实及边界**

无施工方案差异，无停工点。§2 指定代码逐处落地，没有额外修法。

§2.2 说明①已核实：基线 `workorder_errors:270` 初始化 `errors, notes`，`:299` 初始化 `required_refs`，替换位置 `:350-354` 位于同一函数作用域内且在引用校验之前；新增校验的 errors/notes 合并到既有 workorder 项，未新增 check。原 `:361-366` 结构检查及 `:368-381` 文件/哈希/路径围栏遍历逐字节保留。

`price_receipt_errors` 只读取所引收据文件，主源哈希比较使用绑定字段，未打开主源文件。主源绝对路径/符号链接诊断仍由既有遍历承担；收据引用路径失败时允许 helper 与通用遍历各报一条，按工单限定。

静态逐函数核对通过：生产者原有函数除 main 指定插入外未变；main 原 stdout、阈值、退出码与第二源逻辑未变，收据仅新增 price_file_sha256。消费者既有函数除 workorder_errors 指定替换外未变，fig2/flow、receipt_document、receipt_only_errors、fill_workorder、amend、reseal 及 need/workorder_error 前缀保留。19 条 mutation 原始列表逐字节不变。

核对输出：

```text
PASS protected functions/classes byte-identical: scripts/prices/price_check.py; existing=6; allowed=['main']
PASS producer only specified edits: docstring/import/helper/one receipt field; stdout/thresholds/exits unchanged
PASS protected functions/classes byte-identical: scripts/report/stage2_closeout.py; existing=49; allowed=['workorder_errors']
PASS generic reference checks (baseline 361-381) byte-identical; errors/notes at 270 and required_refs at 299 precede replacement at 350
PASS protected functions/classes byte-identical: scripts/tests/test_stage2_closeout.py; existing=41; allowed=['build_closeout_case', 'workorder_reference_contracts']
PASS all 19 existing reference mutations byte-identical
PASS DOCUMENT_BYTES {'SKILL.md': 8021, 'references/**/*.md': 930076, 'commands-staging/*.md': 8798}
PASS tracked whitelist ['scripts/prices/price_check.py', 'scripts/report/stage2_closeout.py', 'scripts/tests/test_stage2_closeout.py']
```

Q7/Q8/Q9/Q14 仍按工单登记不修：未重跑 APU 0914、未修改历史收据或台账、未用 amend 做存量迁移；保持 ALL_SKIP 严格拒收，未新增人工旁证字段或放行路径。文档与 manifest 未改。

**⑧ 禁读披露**

未读取 `~/.codex/`（包括 memories），未读取 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容，未读取 Desktop、Documents；施工方未主动打开、阅读、复制或修改本工单目录之外的历史 maintenance 文件。references 字节统计只访问文件大小元数据，未打开禁读文档内容。历史 maintenance 依赖仅由指定测试进程及其子进程按既有代码访问，适用 §0.2 明示豁免。全程离线，未调用外部数据/API，未读取 API 密钥登记文件。

