# 施工 C7：完成

仅施工 `maintenance/repair-20260917-p0-four/workorder_C.md` v5 的 C7。六项指定检查均 exit 0；用例 15 六变体改后全部通过。源码逐字节等于在开工基线上仅应用 C7 指定替换后的结果，C1–C6 其他片段未改。

## 0.1 开工输出

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。下列为写入任何交付文件前的实际输出，`git status --short` 无输出。HEAD 校验以用户派工副本的 `72430e9` 为准。

```text
$ git status --short
$ git rev-parse --short HEAD
72430e9
```

## 锚点与范围检查

改前逐锚执行 `grep -n -F`，10 个锚均恰好一处且行号一致：

| 文件 | 工单基线锚行 | 结果 |
| --- | --- | --- |
| scripts/report/facts_gate.py | 69、357、360、368、446、447、448 | PASS，7/7 |
| scripts/tests/test_report_facts.py | 257、283、285 | PASS，3/3 |

对 `scripts/tests` 的 Python 测试执行下列旧文案复核，无输出、exit 1（无匹配）：

```sh
grep -rn -F --include='*.py' --exclude-dir='archive' --exclude-dir='blind-reviews' --exclude-dir='.staging_*' -- '缺失或非法' scripts/tests
```

改后将两份开工源码仅按 C7 指定文本替换并与落盘字节比较，两份均匹配；`git diff --check` 无输出、exit 0。

## 先红后绿证据

RED 实物：`maintenance/repair-20260917-p0-four/C7_red_evidence.txt`。生产和测试源码均未修改时，使用现有 `_r07_case` 建六份独立临时夹具，各自修改一个输入并执行与 `reject` 相同的断言，逐例捕获 AssertionError。基线源码 SHA-256 已记入证据，RED 前后两份源码哈希一致；证据先落盘，随后才修改生产和测试源码。RED harness 实际 exit 1。

| 用例 15 变体 | 基线结果 | 基线证据 | 改后 |
| --- | --- | --- | --- |
| symbol = 123 | RED | AssertionError: derive_facts 应拒绝该输入: symbol | GREEN |
| decimals = "18" | 基线即 GREEN，回归例 | ValueError: facts_inputs.symbol/decimals 缺失或非法 | GREEN |
| metrics = [{"value": "7"}] | RED | AssertionError: derive_facts 应拒绝该输入: metrics | GREEN |
| metrics = {"m1": "7"} | RED | AssertionError: derive_facts 应拒绝该输入: metrics | GREEN |
| dual_basis = "x" | RED | AssertionError: derive_facts 应拒绝该输入: dual_basis | GREEN |
| dual_basis = null（Python None） | RED | AssertionError: derive_facts 应拒绝该输入: dual_basis | GREEN |

基线合计：5 RED / 1 基线 GREEN / 6 个独立变体。改后 `test_report_facts.py` 包含 15 类、34 个独立 R07 用例，全过。

## 六项指定检查尾行

仅执行 C7 指定的六个入口；统一设置 `PYTHONDONTWRITEBYTECODE=1`，避免子进程写入字节码缓存。以下为实际退出码与输出尾行。

### test_report_facts.py

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_report_facts.py
PASS: R07 build/derive/发布闸 15 类、34 个独立用例
PASS: facts 宏渲染/附录B同源/G1集合gate(含entity_id主键)/G4宏名gate/G5手写检出/G2上界/G6归并时点/G7血缘提示，七契约全过
exit_code=0
```

### test_stage2_closeout.py

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_stage2_closeout.py
stage2_closeout: 28/28 PASS
exit_code=0
```

### test_repair_batch_d.py

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_repair_batch_d.py
BATCH D 全部通过
exit_code=0
```

### test_review_20260804_p105.py

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_review_20260804_p105.py
PASS: P1-05 mandatory new-analysis vs independent-audit release profiles
exit_code=0
```

### test_a4_gate.py

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_a4_gate.py
a4_gate 契约测试全部通过（23 项）
exit_code=0
```

### invariant_scan.py

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=80, receipt_consumers=117, transport_calls=65, atomic_writes=60, formal_entrypoints=61, exceptions=0
exit_code=0
```

运行记录：`test_repair_batch_d.py`、`test_review_20260804_p105.py` 提示默认 Matplotlib 缓存目录不可写，自动使用系统临时目录；两项实际均 exit 0，无失败或跳过项。

## 文档字节数

仅统计路径元数据，不读取文档内容。

| 范围 | 开工 | 完工 |
| --- | ---: | ---: |
| SKILL.md | 8021 | 8021 |
| references/**/*.md | 930065 | 930065 |
| commands-staging/*.md | 8798 | 8798 |

开工、改后两次执行下列命令，三行输出均为 `8021 / 930065 / 8798`：

```sh
stat -f %z SKILL.md
find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
```

## C7 diff 原文

```diff
diff --git a/scripts/report/facts_gate.py b/scripts/report/facts_gate.py
index bf8d4a9..adb86b8 100644
--- a/scripts/report/facts_gate.py
+++ b/scripts/report/facts_gate.py
@@ -66,7 +66,7 @@ state_source.facts_inputs schema：
       （可选，优先于 provenance 锚点，证据须为案根常规文件）
   merge_evidence: {eid: {earliest, note}}（可选）
   role_notes: {eid: {addr: note}}（可选）
-  metrics: {}（可选透传）；dual_basis: {}（可选透传）
+  metrics: {mid: {...}}（可选；对象且每项为对象）；dual_basis: {}（可选；对象）
   禁止 provenance/facts_binding 键；绑定块只能由 build 生成。
 """
 import argparse
@@ -354,10 +354,13 @@ def derive_facts(case_dir, *, exploration=False):
         raise ValueError(f"state_source 缺 {FACTS_INPUTS_KEY} 对象")
     if "provenance" in fi or "facts_binding" in fi:
         raise ValueError("state_source.facts_inputs 不得预置 provenance/facts_binding——绑定块只能由 build 生成")
-    symbol = str(fi.get("symbol") or "").strip()
+    symbol = fi.get("symbol")
     decimals = fi.get("decimals")
-    if not symbol or isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
-        raise ValueError("facts_inputs.symbol/decimals 缺失或非法")
+    if not isinstance(symbol, str) or not symbol.strip():
+        raise ValueError("facts_inputs.symbol 必须是非空字符串")
+    symbol = symbol.strip()
+    if isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
+        raise ValueError("facts_inputs.decimals 必须是 ≥0 的整数")
     labels = fi.get("entity_labels")
     if not isinstance(labels, dict) or not labels:
         raise ValueError("facts_inputs.entity_labels 缺失或为空")
@@ -366,6 +369,12 @@ def derive_facts(case_dir, *, exploration=False):
     roles = fi.get("role_notes") or {}
     if not all(isinstance(x, dict) for x in (overrides, merges, roles)):
         raise ValueError("facts_inputs.peak_overrides/merge_evidence/role_notes 须为对象")
+    metrics = fi.get("metrics", {})
+    if not isinstance(metrics, dict) or any(not isinstance(v, dict) for v in metrics.values()):
+        raise ValueError("facts_inputs.metrics 须为对象且每项为对象")
+    dual_basis = fi.get("dual_basis")
+    if "dual_basis" in fi and not isinstance(dual_basis, dict):
+        raise ValueError("facts_inputs.dual_basis 须为对象")
 
     members = data["membership_ledger.json"]
     members = members.get("entries", members.get("entities", []))
@@ -443,9 +452,9 @@ def derive_facts(case_dir, *, exploration=False):
     if ledger is not None:
         inputs["provenance_ledger.json"] = {"sha256": _sha256_path(ledger_path)}
     facts = {"token": {"symbol": symbol, "decimals": decimals, "total_supply_raw": total_raw},
-             "entities": entities, "metrics": fi.get("metrics") or {}}
-    if isinstance(fi.get("dual_basis"), dict):
-        facts["dual_basis"] = fi["dual_basis"]
+             "entities": entities, "metrics": metrics}
+    if dual_basis is not None:
+        facts["dual_basis"] = dual_basis
     facts["provenance"] = {
         "schema": FACTS_PROVENANCE_SCHEMA, "facts_binding": "ledger-derived",
         "mode": "exploration" if exploration else "formal",
diff --git a/scripts/tests/test_report_facts.py b/scripts/tests/test_report_facts.py
index b27629a..3cdfd4b 100644
--- a/scripts/tests/test_report_facts.py
+++ b/scripts/tests/test_report_facts.py
@@ -254,6 +254,10 @@ def _r07_build_cases():
         gate.check_facts_vs_ledgers(root, facts, errors)
         assert any("metrics" in error for error in errors), errors
 
+    def bad_type(root, field, value, text):
+        edit(root, "state_source.json", lambda obj: obj["facts_inputs"].update({field: value}))
+        reject(root, text)
+
     def existing_gate(root):
         for name in ("identity_gate.json", "provenance_ledger.json"):
             edit(root, name, lambda obj: obj.update(total_supply_raw="50"))
@@ -281,8 +285,12 @@ def _r07_build_cases():
         run("13 非有限输入 " + literal, lambda root, v=literal: nonfinite(root, v))
     run("13 facts 溢出值拒", nonfinite_facts)
     run("14 产物过既有 G2 gate", existing_gate)
+    for field, value, text in (("symbol", 123, "symbol"), ("decimals", "18", "decimals"),
+                               ("metrics", [{"value": "7"}], "metrics"), ("metrics", {"m1": "7"}, "metrics"),
+                               ("dual_basis", "x", "dual_basis"), ("dual_basis", None, "dual_basis")):
+        run(f"15 类型非法拒 {field}", lambda root, f=field, v=value, t=text: bad_type(root, f, v, t))
     assert not failures, f"R07 失败 {len(failures)}/{len(results)}: {failures}"
-    print(f"PASS: R07 build/derive/发布闸 14 类、{len(results)} 个独立用例", flush=True)
+    print(f"PASS: R07 build/derive/发布闸 15 类、{len(results)} 个独立用例", flush=True)
 
 
 def main():
```

## git diff --stat

```text
 scripts/report/facts_gate.py       | 23 ++++++++++++++++-------
 scripts/tests/test_report_facts.py | 10 +++++++++-
 2 files changed, 25 insertions(+), 8 deletions(-)
```

`git diff --stat` 不包含下列两份未跟踪交付文件；最终工作区状态另列。

## 差异、停工点与边界

无工单偏离、无停工点。仅两份指定源码与两份交付文件有工作区增量。HEAD 仍为 `72430e9`。离线施工；未 commit、push，未执行 stash、checkout、reset，未运行 run_all、reseal 或 docs_lint。

禁读披露：会话启动时平台已预载历史记忆摘要；本次工具未主动打开 `~/.codex/` 下的文件，后续未读取该目录。未读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容，也未读取 `/Users/uravvv/Desktop` 下文件。`references` 字节统计只访问元数据。

## 完工文件 SHA-256

```text
b9bc055919af6d9264e0323d5fd2f70fb63a05826aeacb20812490aa254994b2  scripts/report/facts_gate.py
658c4c299a808e2a460f55eb6b3ef9c879685b9b659662f1708f8802bd24a651  scripts/tests/test_report_facts.py
7fdc5eb23e726a3c4bd2a8e37ff8d240d83dc33506ebe825b034eb7f0888ac2b  maintenance/repair-20260917-p0-four/C7_red_evidence.txt
```

## 完工工作区状态

```text
$ git status --porcelain=v1 --untracked-files=all
 M scripts/report/facts_gate.py
 M scripts/tests/test_report_facts.py
?? maintenance/repair-20260917-p0-four/C7_done.md
?? maintenance/repair-20260917-p0-four/C7_red_evidence.txt
```
