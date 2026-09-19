# 施工 F01：完成

已按工单 v3 完成 §2 的全部指定修改。主价格文件含非有限或非正值时退出 1；第二源非有限值规范化为 None 并走 SKIP；收据序列化禁止 NaN；closeout 逐点重算价格状态。6b–6g 先取得独立 RED，生产修改后 §0.8 六项定向测试全部首次 PASS。无工单偏离、无停工点。

① 开工基线、锚点与 invariant

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。开工 HEAD 已记录，收工再次核验未变。

```text
$ git rev-parse HEAD
838f9184b4c79ae35be5b3fa66ad2a9b01ed74f7

$ git branch --show-current
main

$ git status --short
```

上述 `git status --short` 无输出，退出码 0。§0.1 窄范围命令原始输出如下（命令后无输出，退出码 0）：

```text
$ git diff --stat 868d3f61 HEAD -- scripts/prices scripts/report scripts/tests/test_stage2_closeout.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

派工附加的宽范围检查原始输出（仅 F04 两个预期文件，退出码 0）：

```text
$ git diff --stat 868d3f61 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
 scripts/lib/camp_spec.py             |  5 ++++-
 scripts/tests/test_repair_batch_c.py | 15 +++++++++++++++
 2 files changed, 19 insertions(+), 1 deletion(-)
```

11 个指定锚均使用 `grep -n -F` 验证为恰 1 处，行号与施工前基线一致。输出行如下（前三组依次属于 price_check.py、stage2_closeout.py、test_stage2_closeout.py）：

```text
34:import os
18:  时间戳 >1e12 自动判毫秒。
84:    out = [(t // 1000 if t > 10 ** 12 else t, p) for t, p in out]
175:        if p2 is None or p2 <= 0 or p1 <= 0:
199:            json.dump(out, f, ensure_ascii=False, indent=1)
15:import os
240:PRICE_POINT_STATUSES = ("PASS", "WARN", "SKIP", "FAIL")
244:    """F05：价格双源收据必须是 price_check.py 产物且结论可放行——从 points 按 price_check 同规则
245:    重算 verdict 并要求一致；只放行 PASS/WARN（WARN 记 NOTE）；price_file_sha256 须等于
268:    statuses = [(p.get("status") if isinstance(p, dict) else None) for p in points]
659:    # 7 内联纯申报对象拒；内联带 receipt（ARC 形态）放行
```

开工 invariant scan 原始尾行：

```text
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

② §2 全部 git diff 原文

```diff
diff --git a/scripts/prices/price_check.py b/scripts/prices/price_check.py
index 44c12a5..1bb6525 100644
--- a/scripts/prices/price_check.py
+++ b/scripts/prices/price_check.py
@@ -15,7 +15,7 @@
   - price_series.json：[[ts_sec, price], ...]
   - CG market_chart / llama series：{"prices": [[ts_ms, price], ...]}
   - CSV：表头嗅探时间列（ts/timestamp/time/date）+ 价格列（price/close）
-  时间戳 >1e12 自动判毫秒。
+  时间戳 >1e12 自动判毫秒；任一点非有限（NaN/inf）或非正即 [fatal] 退出 1，先清洗主价格文件再抽查（F01）。
 
 网络：DefiLlama 与 data-api.binance.vision 均实测直连通（api-keys.md 免注册通道节）；
 个别网络环境不通时加 --proxy <proxy-url>，代理地址推荐统一放在 CHIP_PROXY。
@@ -31,6 +31,7 @@ import csv
 import datetime
 import hashlib
 import json
+import math
 import os
 import sys
 import time
@@ -82,6 +83,9 @@ def _load_series(path):
         else:
             sys.exit(f"[fatal] 价格 JSON 认不出结构（既非 [[ts,p]] 也非 {{'prices':...}}）")
     out = [(t // 1000 if t > 10 ** 12 else t, p) for t, p in out]
+    bad = [t for t, p in out if not (math.isfinite(p) and p > 0)]
+    if bad:
+        sys.exit(f"[fatal] 价格文件含非有限或非正价格 {len(bad)} 点（首个 ts={bad[0]}）：主价格文件先清洗再抽查")
     return sorted(out)
 
 
@@ -172,6 +176,7 @@ def main():
             p2, src2 = second_llama(day, a.chain, a.addr, a.proxy)
         else:
             p2, src2 = second_binance(day, a.binance_symbol, a.proxy)
+        p2 = p2 if p2 is None or math.isfinite(p2) else None  # 第二源非有限→按无数据 SKIP（收据可序列化）
         if p2 is None or p2 <= 0 or p1 <= 0:
             status, dev = "SKIP", None
             n_skip += 1
@@ -196,7 +201,7 @@ def main():
            "points": results, "verdict": verdict}
     if a.out:
         with open(a.out, "w") as f:
-            json.dump(out, f, ensure_ascii=False, indent=1)
+            json.dump(out, f, ensure_ascii=False, indent=1, allow_nan=False)
     print(f"[{verdict}] {len(picks)} 点：FAIL={n_fail} WARN={n_warn} SKIP={n_skip}"
           + (f" -> {a.out}" if a.out else ""))
     if verdict == "FAIL":
diff --git a/scripts/report/stage2_closeout.py b/scripts/report/stage2_closeout.py
index 3f74ea0..e6cb98b 100644
--- a/scripts/report/stage2_closeout.py
+++ b/scripts/report/stage2_closeout.py
@@ -12,6 +12,7 @@ import argparse
 from datetime import date, datetime, timezone
 import hashlib
 import json
+import math
 import os
 from pathlib import Path
 import re
@@ -238,11 +239,12 @@ def flow_selection_errors(facts, flow):
 
 
 PRICE_POINT_STATUSES = ("PASS", "WARN", "SKIP", "FAIL")
+PRICE_WARN_PCT, PRICE_FAIL_PCT = 5.0, 15.0  # 与 scripts/prices/price_check.py:43 同值；report 层离线不 import 该 requests 类脚本
 
 
 def price_receipt_errors(case, bindings):
-    """F05：价格双源收据必须是 price_check.py 产物且结论可放行——从 points 按 price_check 同规则
-    重算 verdict 并要求一致；只放行 PASS/WARN（WARN 记 NOTE）；price_file_sha256 须等于
+    """F05/F01：价格双源收据必须是 price_check.py 产物且结论可放行——逐点用 main/second_price 按 price_check
+    同规则重算 status（主价非有限正数即拒）再汇总 verdict，均须与声明一致；只放行 PASS/WARN（WARN 记 NOTE）；price_file_sha256 须等于
     bindings.price_source.sha256；引用取 bindings.price_source_checks，否则取内联
     price_source.dual_source_check.receipt；两者皆无＝纯申报对象，拒。返回 (errors, notes, ref)。"""
     errors, notes = [], []
@@ -266,6 +268,23 @@ def price_receipt_errors(case, bindings):
         errors.append(workorder_error("bindings.price_source_checks.points", "非空 list", points))
         return errors, notes, ref
     statuses = [(p.get("status") if isinstance(p, dict) else None) for p in points]
+    for i, p in enumerate(points):
+        if not isinstance(p, dict):
+            continue
+        p1, p2 = p.get("main_price"), p.get("second_price")
+        ok1 = isinstance(p1, (int, float)) and not isinstance(p1, bool) and math.isfinite(p1) and p1 > 0
+        ok2 = isinstance(p2, (int, float)) and not isinstance(p2, bool) and math.isfinite(p2) and p2 > 0
+        if not ok1:
+            errors.append(workorder_error(f"bindings.price_source_checks.points[{i}].main_price", "有限正数", p1))
+            continue
+        if not ok2:
+            status = "SKIP"
+        else:
+            dev = round(abs(p1 - p2) / ((p1 + p2) / 2) * 100, 2)
+            status = "FAIL" if dev > PRICE_FAIL_PCT else ("WARN" if dev > PRICE_WARN_PCT else "PASS")
+        if p.get("status") != status:
+            errors.append(workorder_error(f"bindings.price_source_checks.points[{i}].status",
+                                          f"与 main/second_price 重算一致（{status}）", p.get("status")))
     expected = ("FAIL" if any(s not in PRICE_POINT_STATUSES or s == "FAIL" for s in statuses)
                 else "ALL_SKIP" if all(s == "SKIP" for s in statuses)
                 else "WARN" if "WARN" in statuses else "PASS")
diff --git a/scripts/tests/test_stage2_closeout.py b/scripts/tests/test_stage2_closeout.py
index 9f6111f..0353d33 100644
--- a/scripts/tests/test_stage2_closeout.py
+++ b/scripts/tests/test_stage2_closeout.py
@@ -656,6 +656,37 @@ def price_receipt_content_enforced(cases):
     assert write_price_receipt(case, second_price=None) == 3
     errors, _ = rebind()
     assert any("ALL_SKIP" in e for e in errors), errors
+    # 6b F01：主价格文件含 NaN 或 0 → 生产者 [fatal] 退出 1、不写收据
+    for name, first in (("price_nan.json", float("nan")), ("price_zero.json", 0.0)):
+        write(case / name, [[1767225600, first], [1767312000, 1.0], [1767398400, 1.0]])
+        assert write_price_receipt(case, second_price=1.0, prices=name, out="price_bad_checks.json") == 1, name
+        assert not (case / "price_bad_checks.json").exists(), name
+    # 6c F01：第二源返回 NaN → 按无数据 SKIP，ALL_SKIP 退出 3，收据可序列化且 second_price 为 null
+    assert write_price_receipt(case, second_price=float("nan")) == 3
+    assert all(q["second_price"] is None and q["status"] == "SKIP" for q in read(case / "price_checks.json")["points"])
+    # 6d F01：收据主价被改成 NaN（status 仍 PASS）→ 消费者拒"有限正数"
+    assert write_price_receipt(case, second_price=1.0) == 0
+    update(case, "price_checks.json", lambda r: r["points"][0].update(main_price=float("nan")))
+    errors, _ = rebind()
+    assert any("points[0].main_price" in e for e in errors), errors
+    # 6e F01：收据主价被改成 0.0（status 仍 PASS）→ 同样拒（消费者与改后生产者同口径：有限正数）
+    update(case, "price_checks.json", lambda r: r["points"][0].update(main_price=0.0))
+    errors, _ = rebind()
+    assert any("points[0].main_price" in e for e in errors), errors
+    # 6f F01：收据第二价被改成 2.0（偏差 66.67%）但 status 仍 PASS → 逐点重算不一致
+    assert write_price_receipt(case, second_price=1.0) == 0
+    update(case, "price_checks.json", lambda r: r["points"][1].update(second_price=2.0))
+    errors, _ = rebind()
+    assert any("points[1].status" in e and "FAIL" in e for e in errors), errors
+    # 6g F01：两端阈值相等；WARN 边界（1.0/1.052 → 5.07% WARN）真实收据放行，手改 status=PASS 后拒
+    import price_check
+    assert (closeout.PRICE_WARN_PCT, closeout.PRICE_FAIL_PCT) == (price_check.WARN_PCT, price_check.FAIL_PCT) == (5.0, 15.0)
+    assert write_price_receipt(case, second_price=1.052) == 0
+    errors, _ = rebind()
+    assert not errors, errors
+    update(case, "price_checks.json", lambda r: ([q.update(status="PASS") for q in r["points"]], r.update(verdict="PASS")))
+    errors, _ = rebind()
+    assert any("points[0].status" in e and "WARN" in e for e in errors), errors
     # 7 内联纯申报对象拒；内联带 receipt（ARC 形态）放行
     assert write_price_receipt(case, second_price=1.0) == 0
     obj = read(case / "a5_assembly_workorder.json")
```

已从开工 HEAD 原文按工单的替换／插入规则重建预期文件，与三份实际文件逐字比较全部一致。工单未指定的位置均保持原文；包括 `_daily_close`、CSV 日期截断、原 SKIP 条件、选源、阈值、退出码、汇总 verdict、价格文件哈希绑定、`load()`、`workorder_errors` 其他逻辑。测试既有 19 条 mutation、价格段 1–7 与 12 项 checks 断言均原样保留并通过。

③ RED 摘要（生产代码修改前）

证据文件：[F01_red_evidence.txt](F01_red_evidence.txt)。取证开始和结束的两份生产文件 `git diff --exit-code` 均为 0，文件 SHA256 也已记录。使用既有真实生产者与离线第二源 stub；从已插入的用例代码提取各段独立执行，每段各自 try/except，前段失败不截断后段。6b 两个输入分别执行；6g 阈值、真实 WARN、手改 PASS 分开取证。

| 用例 | 基线实际结果 | 结论 |
| --- | --- | --- |
| 6b NaN 主价 | `rc=0`，`receipt_exists=True`，`verdict='PASS'`，NaN 点也为 PASS | RED |
| 6b 零主价 | `rc=0`，`receipt_exists=True`，`verdict='PASS'`，零价点 SKIP、其余 PASS | RED |
| 6c 第二源 NaN | `rc=0`，三点均 PASS，收据含 NaN | RED |
| 6d 主价篡改 NaN | `errors = []` | RED |
| 6e 主价篡改 0.0 | `errors = []` | RED |
| 6f 第二价篡改 2.0、仍声明 PASS | `errors = []` | RED |
| 6g 阈值相等断言 | `AttributeError: module 'stage2_closeout' has no attribute 'PRICE_WARN_PCT'` | RED |
| 6g 真实 1.0/1.052 收据 | `rc=0`，三点 5.07% WARN，`errors = []`，NOTE 记录 3 个 WARN 点 | GREEN 正控 |
| 6g 全部点及 verdict 手改 PASS | `errors = []` | RED |

每段返回码／errors、生产者 stdout 和断言异常原文均保存在证据文件。生产修改后，以上六段随 `price_receipt_content_enforced` 全部通过。

④ §0.8 定向测试结果尾行

```text
$ python3 -B scripts/tests/test_stage2_closeout.py
stage2_closeout: 30/30 PASS
exit_code=0

$ python3 -B scripts/tests/test_a4_gate.py
a4_gate 契约测试全部通过（23 项）
exit_code=0

$ python3 -B scripts/tests/test_audit_release_gate.py
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
exit_code=0

$ python3 -B scripts/tests/test_batch4_invariant_guards.py
PASS B4-G1: bare pool / labels / vertical slice / denominator injections
exit_code=0

$ python3 -B scripts/tests/test_exemption_guards.py
PASS: exemption guards (EX-01 full-F-03)
exit_code=0

$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
exit_code=0
```

六项均首次运行退出 0。`test_stage2_closeout.py` 与 `test_a4_gate.py` 均未出现 `data_broken: '_items'`，无需使用 `MPLCONFIGDIR="$HOME/.matplotlib"` 重跑。没有运行 `run_all.py`。

reseal 未实跑、交调度方本机补验：按工单要求，在本段由调度方 commit 后，主仓库干净且 `/tmp/w3_acceptance` 同步 HEAD 时执行 `test_stage2_reseal.py`。

⑤ 文档字节数（开工及收工一致）

```text
$ stat -f %z SKILL.md
8021

$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930076

$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
```

以上只读文件元数据。文档与 VERSION、pyproject.toml、CHANGELOG.md、manifest 和 reseal 测试均未修改。

⑥ 改动范围

```text
$ git diff --stat
 scripts/prices/price_check.py         |  9 +++++++--
 scripts/report/stage2_closeout.py     | 23 +++++++++++++++++++++--
 scripts/tests/test_stage2_closeout.py | 31 +++++++++++++++++++++++++++++++
 3 files changed, 59 insertions(+), 4 deletions(-)
```

`git diff --stat` 不显示未跟踪文件；本工单目录另新增 `F01_done.md` 与 `F01_red_evidence.txt`，两者均在白名单。全部实际改动均在 §0.3 白名单内，`git diff --check` 通过；HEAD 与分支未变化。

⑦ 与工单差异／停工点及兼容范围

无差异，无停工点。没有新增函数、收据键或 closeout check 项；逐点错误归入既有 workorder 检查，仍为 12 项 checks。`price_receipt_errors` 返回 `(errors, notes, ref)`，`WORKORDER BLOCK: ` 前缀保持不变。

合法输入范围为：主价格文件各点均为有限正数，第二源为 None 或有限数；此范围内原有 stdout 格式、收据键集合及 PASS/WARN 0、FAIL 2、ALL_SKIP 3 退出码保持不变。主价格文件的 0／负价原可 SKIP 并汇总 PASS，现 `[fatal]` 退出 1，属于本轮预期变化。消费者也要求逐点主价为有限正数，且声明 status 与重算一致。

存量无实际迁移对象的依据采用工单 §1.7／Q4 已给出的调度方核验结论：存量没有任何 `price_check.py` 生成、含 `points` 的收据。本次未另行扫描历史案卷。Q1–Q4 台账由调度方维护，本轮未改；F05 同源选源问题按工单不修。

全程离线施工，未 commit、push 或部署，未使用 stash／checkout／reset，未主动删除文件或目录。

⑧ 禁读披露

未读取 `~/.codex/`（含 memories），未主动读取 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本工单目录以外的历史 maintenance 内容，未读取 `/Users/uravvv/Desktop` 或 `/Users/uravvv/Documents`。文档字节统计只使用元数据。历史 maintenance 依赖仅由原样运行的指定测试子进程访问，适用 §0.2 豁免；施工方未主动打开、复制或修改这些历史文件。

