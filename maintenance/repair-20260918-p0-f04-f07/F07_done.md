# 施工 F07：完成

按 `workorder_F07.md` 文件头 v3 执行 §0–§3。实际开工及收工 HEAD 均为 `0b0a5f6`；生产变更仅为 §2.1/§2.2 指定替换、插入和 docstring，测试按 §2.3 补齐。7 项指定检查全部 PASS；未运行 `run_all.py`。

## ① §0.1 开工基线命令及原始输出

```text
$ git status --short
```
exit_code=0；stdout 为空。

```text
$ git rev-parse --short HEAD
0b0a5f6
```
exit_code=0。

```text
$ git diff --stat 311e6c4 HEAD -- scripts/tests/test_audit_release_gate.py scripts/tests/invariant_manifest.json scripts/evm references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```
exit_code=0；stdout 为空。

提示词明确允许实际开工 HEAD 比派工基线 `19d01e9` 多恰一个提示词提交。本次已核实父提交、提交文件与提交数：

```text
$ git log -1 --format='%h %p %s' --name-status
0b0a5f6 19d01e9 F07 施工提示词对齐基线 19d01e9

M	maintenance/repair-20260918-p0-f04-f07/construct_F07_prompt.md
$ git rev-list --count 19d01e9..HEAD
1
```

## 开工锚点与事实核验

`grep -n -F` 指定锚点均在施工前命中唯一位置、行号相符；`return hits` 与 `items` 按工单规定区间核验。

```text
$ grep -n -F 'def _find_peaks_summaries(case_dir: Path) -> list[Path]:' scripts/report/audit_release_gate.py
1077:def _find_peaks_summaries(case_dir: Path) -> list[Path]:
$ grep -n -F '    return hits' scripts/report/audit_release_gate.py [核验区间 1077-1094]
1094:    return hits
$ grep -n -F '    hits = _find_peaks_summaries(case_dir)' scripts/report/audit_release_gate.py
1104:    hits = _find_peaks_summaries(case_dir)
$ grep -n -F '    ps_path = hits[0]' scripts/report/audit_release_gate.py
1112:    ps_path = hits[0]
$ grep -n -F '    pd = ps_path.parent' scripts/report/audit_release_gate.py
1113:    pd = ps_path.parent
$ grep -n -F '    if fu.get("engine") != "replay_duck.py":' scripts/report/audit_release_gate.py
1190:    if fu.get("engine") != "replay_duck.py":
$ grep -n -F '    items = fu.get("inputs")' scripts/report/audit_release_gate.py [核验区间 1180-1230]
1192:    items = fu.get("inputs")
$ grep -n -F '    assert not r09_failures, f"R09 失败 {len(r09_failures)}/13: {r09_failures}"' scripts/tests/test_audit_release_gate.py
1154:    assert not r09_failures, f"R09 失败 {len(r09_failures)}/13: {r09_failures}"
ANCHORS PASS: 8/8
$ grep -n '^REPO' scripts/tests/test_audit_release_gate.py
15:REPO = HERE.parent.parent
$ grep -n '多份' scripts/tests/test_audit_release_gate.py
1041:        assert any("多份 peaks_summary.json" in x for x in errors), errors
1135:        ("6 R09 多份 summary 拒", _r09_case_6),
sha256 c35d4a489eb7651e24aa77a872a51fa7c717c103883c74043c177f0613fa3a16 scripts/report/audit_release_gate.py
sha256 4df7bd25160804882f9ffe60bc8e8d3895faca0196b166a0cfba539b32e836a2 scripts/tests/test_audit_release_gate.py
sha256 7fe9588886cf0ef8f9a66a626df1ca4d466a9724a5217a448ac29444979ed11a scripts/tests/invariant_manifest.json
sha256 c3a6123a4b57b22f7dc0ef7b553a5b2322acf9b4a697bc7d2acd1a59cf54a85d scripts/evm/replay_duck.py
sha256 6846f49ab943d2638f181e175f564508a58f5661dfac43cc7020ca71e6613001 scripts/evm/peaks_daily.py
sha256 b301dfcc3ed80e3bd64f11e5b2c5b0d1ec13ace7f9df16a62906cced12cdfa96 scripts/tests/contract_manifest.json
```

其余定位核验原始输出：

```text
995:    def _r09_followup(pd, addresses):
1129:    r09_cases = (
1191:        errors.append("block_precision_followup.json engine 非 replay_duck.py——块级补算须走重放引擎")
```

`REPO` 实际在测试文件第 15 行。用例 6 原断言在第 1041 行命中 `多份 peaks_summary.json`，按工单改为 `多个峰值产物目录`；第 1135 行用例标题保持不变。用例 21/22 均先创建 `data` 父目录。实际 producer 第 405–410 行已写全 `producer/channels/value_type/count`，未修改 producer。

## ② §2.1/§2.2/§2.3 git diff 原文

```text
$ git diff -- scripts/report/audit_release_gate.py scripts/tests/test_audit_release_gate.py scripts/tests/invariant_manifest.json
```
```diff
diff --git a/scripts/report/audit_release_gate.py b/scripts/report/audit_release_gate.py
index 4ecafe8..e3d5708 100644
--- a/scripts/report/audit_release_gate.py
+++ b/scripts/report/audit_release_gate.py
@@ -1074,11 +1074,19 @@ def check_dormant(case_dir: Path, d: dict, errors: list[str]):
 BLOCK_PRECISION_FOLLOWUP_SCHEMA = "block-precision-followup/v1"
 
 
-def _find_peaks_summaries(case_dir: Path) -> list[Path]:
-    """R09（7.2.0）：peaks_daily 产物根不限定案根——递归定位 peaks_summary.json；
-    跳过隐藏目录（.duck_tmp 等）、_history 与符号链接路径。"""
-    hits = []
-    for p in sorted(case_dir.rglob("peaks_summary.json")):
+PEAKS_DAILY_PRODUCTS = ("peaks_summary.json", "needs_block_precision.json",
+                        "block_precision_followup.json")
+
+
+def _find_peaks_dirs(case_dir: Path) -> list[Path]:
+    """R09（7.2.0）：peaks_daily 产物根不限定案根——递归定位；跳过隐藏目录（.duck_tmp 等）、
+    _history 与符号链接路径。F07（7.2.1）：三件**生成产物**任一在场即认定为峰值产物目录，
+    改名 summary 不再使整段检查零命中；trigger_days.json 既是 --trigger-days 原始输入的常见名
+    也是输出名，不作定位依据。单次遍历；返回去重排序后的目录列表。"""
+    dirs = set()
+    for p in case_dir.rglob("*.json"):
+        if p.name not in PEAKS_DAILY_PRODUCTS:
+            continue
         rel = p.relative_to(case_dir)
         if any(part.startswith(".") or part == "_history" for part in rel.parts):
             continue
@@ -1090,8 +1098,8 @@ def _find_peaks_summaries(case_dir: Path) -> list[Path]:
             cur = cur.parent
         if linked or not p.is_file():
             continue
-        hits.append(p)
-    return hits
+        dirs.add(p.parent)
+    return sorted(dirs)
 
 
 def check_daily_peaks(case_dir: Path, errors: list[str]):
@@ -1100,17 +1108,22 @@ def check_daily_peaks(case_dir: Path, errors: list[str]):
     同日等额进出会漏），且四类触发日必须有显式产物（空也要声明）。
     R09（7.2.0）：①产物根按 rglob 定位（原只看案根，data/peaks_daily/ 下的产物整段绕过闸）；
     ②needs_block_precision.json 与 summary 哈希咬合；③needs ∪ 触发日活跃候选非空时，
-    必须有 replay_duck.py --only-addrs 产出的 block_precision_followup.json 覆盖每一址。"""
-    hits = _find_peaks_summaries(case_dir)
-    if not hits:
+    必须有 replay_duck.py --only-addrs 产出的 block_precision_followup.json 覆盖每一址。
+    F07（7.2.1）：④summary/needs/followup 任一在场即检查（trigger_days 不作定位依据）；⑤followup 须绑定当前 replay_duck.py producer 与 channels 实物。"""
+    dirs = _find_peaks_dirs(case_dir)
+    if not dirs:
         return
-    if len(hits) > 1:
-        errors.append("案内出现多份 peaks_summary.json（"
-                      + ", ".join(str(h.relative_to(case_dir)) for h in hits)
+    if len(dirs) > 1:
+        errors.append("案内出现多个峰值产物目录（"
+                      + ", ".join(str(h.relative_to(case_dir)) for h in dirs)
                       + "）——峰值产物根须唯一，清理陈旧目录后重验")
         return
-    ps_path = hits[0]
-    pd = ps_path.parent
+    pd = dirs[0]
+    ps_path = pd / "peaks_summary.json"
+    if ps_path.is_symlink() or not ps_path.is_file():
+        errors.append(f"峰值产物目录 {pd.relative_to(case_dir)} 缺 peaks_summary.json"
+                      "（needs/trigger/followup 在场而 summary 缺席＝改名或残缺产物，拒）")
+        return
     ps = load_json(ps_path, errors)
     if not isinstance(ps, dict):
         errors.append("peaks_summary.json 顶层须为对象")
@@ -1189,6 +1202,28 @@ def check_daily_peaks(case_dir: Path, errors: list[str]):
         errors.append(f"block_precision_followup.json schema 非法（须 {BLOCK_PRECISION_FOLLOWUP_SCHEMA}）")
     if fu.get("engine") != "replay_duck.py":
         errors.append("block_precision_followup.json engine 非 replay_duck.py——块级补算须走重放引擎")
+    # F07（7.2.1）：消费 producer 已写出的绑定字段——自报收据（只有 engine 字符串）拒
+    producer = fu.get("producer")
+    engine_path = Path(__file__).resolve().parent.parent / "evm" / "replay_duck.py"
+    if (not isinstance(producer, dict) or producer.get("path") != "replay_duck.py"
+            or str(producer.get("sha256") or "").lower() != sha256_file(engine_path).lower()):
+        errors.append("block_precision_followup.json producer 未绑定当前 scripts/evm/replay_duck.py"
+                      "（缺 producer 或 sha256 不符）——旧收据/手写收据拒，用当前引擎重跑 --only-addrs")
+    chan = fu.get("channels")
+    chan_name = Path(str((chan or {}).get("path") or "")).name if isinstance(chan, dict) else ""
+    chan_hits = [p for p in case_dir.rglob(chan_name)
+                 if chan_name and p.is_file() and not p.is_symlink()
+                 and not any(part.startswith(".") or part == "_history"
+                             for part in p.relative_to(case_dir).parts)]
+    if not chan_name or len(chan_hits) != 1 \
+            or sha256_file(chan_hits[0]).lower() != str(chan.get("sha256") or "").lower():
+        errors.append("block_precision_followup.json channels 未绑定案内唯一常规文件"
+                      f"（{chan_name or '缺 path'}：命中 {len(chan_hits)} 个或 sha256 不符）——通道清单须随案")
+    if fu.get("value_type") not in ("HUGEINT", "VARINT"):
+        errors.append("block_precision_followup.json value_type 须为 HUGEINT/VARINT（replay_duck 写出）")
+    addrs_obj = fu.get("addresses")
+    if isinstance(addrs_obj, dict) and fu.get("count") != len(addrs_obj):
+        errors.append("block_precision_followup.json count 与 addresses 条数不一致")
     items = fu.get("inputs")
     if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
         errors.append("block_precision_followup.json inputs 须为 [{path, sha256}] 列表")
diff --git a/scripts/tests/test_audit_release_gate.py b/scripts/tests/test_audit_release_gate.py
index ecee9c2..7ff748d 100644
--- a/scripts/tests/test_audit_release_gate.py
+++ b/scripts/tests/test_audit_release_gate.py
@@ -993,10 +993,15 @@ def main():
             write_json(pd, "block_precision_followup.json", followup)
 
     def _r09_followup(pd, addresses):
+        write_json(pd, "channels.json", {"fixture": "channels"})
         return {"schema": "block-precision-followup/v1", "engine": "replay_duck.py",
+                "producer": {"path": "replay_duck.py",
+                             "sha256": sha(REPO / "scripts/evm/replay_duck.py")},
+                "value_type": "HUGEINT",
                 "inputs": [{"path": name, "sha256": sha(pd / name)} for name in
                            ("needs_block_precision.json", "trigger_days.json")],
-                "addresses": addresses}
+                "channels": {"path": "channels.json", "sha256": sha(pd / "channels.json")},
+                "count": len(addresses), "addresses": addresses}
 
     def _r09_case_1(root):
         report = build_case(root, historical=False)
@@ -1038,7 +1043,7 @@ def main():
         _r09_write_peaks(root, needs=[])
         _r09_write_peaks(root / "data/peaks_daily", needs=[])
         errors = gate.run(root, report)
-        assert any("多份 peaks_summary.json" in x for x in errors), errors
+        assert any("多个峰值产物目录" in x for x in errors), errors
 
     def _r09_case_7(root):
         report = build_case(root, historical=False)
@@ -1126,6 +1131,87 @@ def main():
         assert any("block_precision_followup.addresses[0xabc].peak" in x for x in errors), errors
         assert not any("须为 null" in x for x in errors), errors
 
+    def _r09_case_14(root):
+        report = build_case(root, historical=False)
+        pd = root / "data/peaks_daily"
+        _r09_write_peaks(pd, needs=["0xabc"])
+        (pd / "peaks_summary.json").rename(pd / "renamed_summary.json")
+        errors = gate.run(root, report)
+        assert any("缺 peaks_summary.json" in x for x in errors), errors
+
+    def _r09_case_15(root):
+        report = build_case(root, historical=False)
+        _r09_write_peaks(root, needs=["0xabc"])
+        fu = _r09_followup(root, {"0xabc": {"peak": "0", "peak_blk": None}})
+        fu.pop("producer")
+        write_json(root, "block_precision_followup.json", fu)
+        errors = gate.run(root, report)
+        assert any("producer 未绑定" in x for x in errors), errors
+
+    def _r09_case_16(root):
+        report = build_case(root, historical=False)
+        _r09_write_peaks(root, needs=["0xabc"])
+        fu = _r09_followup(root, {"0xabc": {"peak": "0", "peak_blk": None}})
+        fu["producer"]["sha256"] = "0" * 64
+        write_json(root, "block_precision_followup.json", fu)
+        errors = gate.run(root, report)
+        assert any("producer 未绑定" in x for x in errors), errors
+
+    def _r09_case_17(root):
+        report = build_case(root, historical=False)
+        _r09_write_peaks(root, needs=["0xabc"])
+        write_json(root, "block_precision_followup.json", _r09_followup(root, {
+            "0xabc": {"peak": "0", "peak_blk": None}}))
+        (root / "channels.json").unlink()
+        errors = gate.run(root, report)
+        assert any("channels 未绑定" in x for x in errors), errors
+
+    def _r09_case_18(root):
+        report = build_case(root, historical=False)
+        _r09_write_peaks(root, needs=["0xabc"])
+        write_json(root, "block_precision_followup.json", _r09_followup(root, {
+            "0xabc": {"peak": "0", "peak_blk": None}}))
+        write_json(root, "channels.json", {"fixture": "changed channels"})
+        errors = gate.run(root, report)
+        assert any("channels 未绑定" in x for x in errors), errors
+
+    def _r09_case_19(root):
+        report = build_case(root, historical=False)
+        _r09_write_peaks(root, needs=["0xabc"])
+        fu = _r09_followup(root, {"0xabc": {"peak": "0", "peak_blk": None}})
+        fu["count"] = 7
+        write_json(root, "block_precision_followup.json", fu)
+        errors = gate.run(root, report)
+        assert any("count 与 addresses" in x for x in errors), errors
+
+    def _r09_case_20(root):
+        report = build_case(root, historical=False)
+        pd = root / "data/peaks_daily"
+        pd.mkdir(parents=True)
+        write_json(pd, "needs_block_precision.json", {"0.0100": ["0xabc"]})
+        write_json(pd, "trigger_days.json", {
+            "schema": "trigger-days-replay/v1", "days": {}, "empty_reason": "raw input"})
+        errors = gate.run(root, report)
+        assert any("缺 peaks_summary.json" in x for x in errors), errors
+
+    def _r09_case_21(root):
+        report = build_case(root, historical=False)
+        (root / "data").mkdir()
+        _r09_write_peaks(root / "data/peaks_daily", needs=[])
+        write_json(root / "data", "trigger_days.json", {
+            "schema": "trigger-days-replay/v1", "days": {}, "empty_reason": "raw input"})
+        errors = gate.run(root, report)
+        assert not any("多个峰值产物目录" in x or "缺 peaks_summary.json" in x
+                       for x in errors), errors
+
+    def _r09_case_22(root):
+        report = build_case(root, historical=False)
+        (root / "data").mkdir()
+        write_json(root / "data", "trigger_days.json", {
+            "schema": "trigger-days-replay/v1", "days": {}, "empty_reason": "raw input"})
+        errors = gate.run(root, report)
+        assert not any("峰值" in x or "peaks_summary" in x for x in errors), errors
+
     r09_cases = (
         ("1 R09 子目录旧公式拒", _r09_case_1),
         ("2 R09 子目录完整产物放行（GREEN→GREEN）", _r09_case_2),
@@ -1140,6 +1226,15 @@ def main():
         ("11 R09 收据地址项非法拒", _r09_case_11),
         ("12 R09 地址大小写归一放行（GREEN→GREEN）", _r09_case_12),
         ("13 R09 顶层非对象进 errors 不崩", _r09_case_13),
+        ("14 R09/F07 summary 改名仍检查", _r09_case_14),
+        ("15 F07 followup 缺 producer 拒", _r09_case_15),
+        ("16 F07 followup producer sha 过期拒", _r09_case_16),
+        ("17 F07 followup channels 缺席拒", _r09_case_17),
+        ("18 F07 followup channels sha 不符拒", _r09_case_18),
+        ("19 F07 count 不一致拒", _r09_case_19),
+        ("20 F07 只有 needs/trigger 无 summary 拒", _r09_case_20),
+        ("21 F07 兼容：原始触发日清单在 data/ 不被误判（GREEN→GREEN）", _r09_case_21),
+        ("22 F07 兼容：只有原始触发日清单、无峰值产物（GREEN→GREEN）", _r09_case_22),
     )
     r09_failures = []
     for name, case in r09_cases:
@@ -1151,7 +1246,7 @@ def main():
             r09_failures.append(name)
         else:
             print(f"ok    {name}")
-    assert not r09_failures, f"R09 失败 {len(r09_failures)}/13: {r09_failures}"
+    assert not r09_failures, f"R09 失败 {len(r09_failures)}/{len(r09_cases)}: {r09_failures}"
 
     # 6.9.2 修复反例（codex 验收 P1）：挂名≠裁决——空壳候选拒。
     with tempfile.TemporaryDirectory() as td:
```

生产代码额外按施工前原文和工单的三个 Python 代码块重建预期结果，逐字节对比：

```text
PASS: production exactly matches workorder code blocks and prescribed docstring; all other baseline bytes preserved.
UNCHANGED: scripts/evm/replay_duck.py
UNCHANGED: scripts/evm/peaks_daily.py
UNCHANGED: scripts/tests/contract_manifest.json
```

## ③ 先红后绿证据

完整命令、被测文件 SHA256、逐例异常类型及 traceback 已写入 [F07_red_evidence.txt](F07_red_evidence.txt)，并在修改生产代码前检查其落盘及生产文件基线 SHA256。

- 用例 14–20：7 个真实 RED，均为 `AssertionError: []`。
- 用例 21/22：基线已 GREEN，修复后保持 GREEN。
- 取证时生产 SHA256：`c35d4a489eb7651e24aa77a872a51fa7c717c103883c74043c177f0613fa3a16`。
- 取证时测试 SHA256：`2c64f22385b9a9834b32d9fc5af0d99e02929c6b9c41ae3aba242336c6adad34`。
- GREEN 阶段完整 `test_audit_release_gate.py` 通过，R09/F07 用例 1–22 全部通过，含既有用例 2/12。

RED 取证只从测试文件 AST 提取实际 `_r09_*` 函数和 `r09_cases` 执行 14–22；没有修改断言或替换 gate。RED 取证器 exit_code=0 表示观察到预期的 7 RED＋2 GREEN，异常原文保留在证据文件中。

## ④ §0.8 定向测试命令与结果尾行

下列命令均设置 `PYTHONDONTWRITEBYTECODE=1`，使测试子进程继承不生成字节码的环境；均实际执行并以 exit_code=0 结束。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_audit_release_gate.py
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
```
exit_code=0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_engine_equivalence.py
PASS: R09 块级补算峰值等价、零事件地址、非法输入与坏事件不覆盖全量产物
PASS: 三引擎 gate/退出码 10 例 hypothesis 全等；gate PASS 六产物全等；gate FAIL 正式序列零产物；VARINT 双引擎确定性对表通过
```
exit_code=0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_peaks_daily.py
PASS：0 项失败
```
exit_code=0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_batch15_three_ledgers_frozen.py
PASS batch15 frozen consumers: 12/12
```
exit_code=0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_repair_batch_d.py
================================================
BATCH D 全部通过
```
exit_code=0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_stage2_closeout.py
stage2_closeout: 28/28 PASS
```
exit_code=0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```
exit_code=0。

`test_engine_equivalence.py` 实际运行当前 `replay_duck.py --only-addrs` 产出收据，块级峰值等价、零事件地址及非法输入保护测试通过。`test_repair_batch_d.py` 曾输出 Matplotlib 默认缓存目录不可写提示，随后自动使用临时缓存目录，测试正常完成并 PASS；没有失败项或未执行项。未运行工单排除的 `test_stage2_reseal.py::dry_run_touches_nothing` 或全套 `run_all.py`。

R09/F07 GREEN 原始输出：

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
ok    14 R09/F07 summary 改名仍检查
ok    15 F07 followup 缺 producer 拒
ok    16 F07 followup producer sha 过期拒
ok    17 F07 followup channels 缺席拒
ok    18 F07 followup channels sha 不符拒
ok    19 F07 count 不一致拒
ok    20 F07 只有 needs/trigger 无 summary 拒
ok    21 F07 兼容：原始触发日清单在 data/ 不被误判（GREEN→GREEN）
ok    22 F07 兼容：只有原始触发日清单、无峰值产物（GREEN→GREEN）
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
```

## ⑤ §1.1 三处字节数

开工、收工均只按元数据统计，结果一致；没有为统计读取文档内容（含 `references/attic.md`）。

```text
$ stat -f %z SKILL.md
8021
$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930061
$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
```

## ⑥ git diff --stat 与范围

```text
$ git diff --stat
 scripts/report/audit_release_gate.py     |  65 +++++++++++++++-----
 scripts/tests/test_audit_release_gate.py | 101 ++++++++++++++++++++++++++++++-
 2 files changed, 148 insertions(+), 18 deletions(-)
```

`git diff --stat` 只列已跟踪文件；本工单另外新建的 `F07_done.md` 与 `F07_red_evidence.txt` 为未跟踪白名单文件。`git diff --check` exit_code=0，stdout 为空。

受保护文件收工 SHA256 与开工一致：

```text
c3a6123a4b57b22f7dc0ef7b553a5b2322acf9b4a697bc7d2acd1a59cf54a85d scripts/evm/replay_duck.py
6846f49ab943d2638f181e175f564508a58f5661dfac43cc7020ca71e6613001 scripts/evm/peaks_daily.py
b301dfcc3ed80e3bd64f11e5b2c5b0d1ec13ace7f9df16a62906cced12cdfa96 scripts/tests/contract_manifest.json
7fe9588886cf0ef8f9a66a626df1ca4d466a9724a5217a448ac29444979ed11a scripts/tests/invariant_manifest.json
PASS: four protected files byte-identical to baseline
```

## ⑦ 与工单差异、登记与兼容影响

无工单差异、无停工点。`invariant_scan.py` 首次即 PASS、没有报缺项，`invariant_manifest.json` 实际增补项为无，文件未改。`contract_manifest.json`、两份 EVM producer、所有指定保护片段均未改。未 commit、未 push、未 stash/checkout/reset、未部署 `~/.claude/commands/`；未修改其他测试或任何文档上下文。

存量影响按 §1.4：缺 `producer/channels/value_type/count` 的旧 followup 或 producer SHA256 不匹配当前引擎的收据会被拒，须用当前引擎同时传 needs 与 trigger 两件输入重跑；首个 `--only-addrs` 决定收据落点：

```sh
python3 -B scripts/evm/replay_duck.py --channels <通道清单> --out-dir <补算工作目录> --only-addrs <产物目录>/needs_block_precision.json --only-addrs <产物目录>/trigger_days.json
```

该参数仅限制峰值聚合地址范围，仍执行全量通道校验、读取与去重；耗时和临时空间须按案量评估。案内无 summary/needs/followup 三件生成产物时仍按既有契约 return；仅有原始 `trigger_days.json` 不会触发峰值产物定位。工单 §4 残余保持由调度方登记，本次未扩展修复。

## ⑧ 禁读披露

会话启动时平台自动注入了历史记忆摘要；本轮没有主动读取 `~/.codex/` 下任何文件，也未启动插件搜索、读取记忆文件或应用其中历史结论。此项已在首次进度说明披露。

人工命令没有读取 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、禁止访问的历史 maintenance 目录、`/Users/uravvv/Desktop` 或 `/Users/uravvv/Documents` 内容。直接读取的工单均位于当前 `maintenance/repair-20260918-p0-f04-f07/` 目录；读取 F06 工单仅为取得 §1.1 原始字节统计命令。按本次授权运行的测试/守卫可能自行遍历文档；§1.1 统计只读取文件大小元数据。整个施工离线进行。

