# 施工 F04：完成

按 `workorder_F04_retail_bucket.md` v2 完成。EVM spec 精确配置「散户」时在共享校验层走既有 `_fail`，stderr 前缀为 `[camp-spec] `、exit 2；Solana 语义保持不变。生产与测试修改严格对应工单 §2。

## 1. 开工基线与锚点

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`；分支：`main`。

开工命令及实际输出（两项基线检查均 exit 0，输出为空）：

```console
$ git rev-parse HEAD
a4a0f2ccb5cb4beae1c20949fe2f5bae1f68afa9
$ git status --short
$ git diff --stat 868d3f61 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

六个锚点逐一执行 `grep -n -F`，均只有一处，且与基线行号一致：

```text
scripts/lib/camp_spec.py expected=22 count=1 PASS=True
22:  - "销毁"阵营由引擎自动补列（烧入 0x0 的量），spec 里可不配置。
scripts/lib/camp_spec.py expected=61 count=1 PASS=True
61:            _fail(f"{source_label} 含非法阵营名: {camp!r}")
scripts/tests/test_repair_batch_c.py expected=159 count=1 PASS=True
159:    check("F05 空阵营名硬拒", rejected({"": [A]}, "evm"))
scripts/tests/test_repair_batch_c.py expected=251 count=1 PASS=True
251:    dup_spec = {"camps": {"camp_A": [A], "camp_B": [A]}, "entities": {}}
scripts/tests/test_repair_batch_c.py expected=256 count=1 PASS=True
256:        check("F05 replay_duck 跨营重复 exit2", "camp-spec" in p.stderr, p.stderr[-300:])
scripts/tests/test_repair_batch_c.py expected=272 count=1 PASS=True
272:        check("F05 replay_pass2 合法 spec 绿例", p.returncode == 0, p.stderr[-300:])
```

开工执行 `python3 -B scripts/tests/invariant_scan.py`（rc=0）：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

## 2. 工单 §2 各处 git diff 原文

```diff
diff --git a/scripts/lib/camp_spec.py b/scripts/lib/camp_spec.py
index ad93c8d..e300808 100644
--- a/scripts/lib/camp_spec.py
+++ b/scripts/lib/camp_spec.py
@@ -19,7 +19,7 @@ solana/build_evolution.py）此前各自手写 `addr2camp[addr] = camp` 式装
 边界（by design，不在本模块管辖）：
   - 互斥只属 camps 域；entities 域一个地址可属多个实体（图 2 实体线与阵营
     本来就允许重叠），不查重。
-  - "销毁"阵营由引擎自动补列（烧入 0x0 的量），spec 里可不配置。
+  - "销毁"阵营由引擎自动补列（烧入 0x0 的量），spec 里可不配置；EVM 的"散户"是引擎残差桶（100−已知阵营），spec 里配置即拒（F04，2026-09-18）。
 """
 from __future__ import annotations
 
@@ -59,6 +59,9 @@ def validate_camp_spec(camps, *, chain_family: str, source_label: str = "camps")
     for camp, addrs in camps.items():
         if not isinstance(camp, str) or not camp.strip():
             _fail(f"{source_label} 含非法阵营名: {camp!r}")
+        if chain_family == "evm" and camp == "散户":
+            _fail(f"{source_label} 阵营「散户」是 EVM 引擎的残差桶（100−已知阵营），不得在 spec 里配置"
+                  f"——显式配置会让 replay_pass2/replay_duck 同日写两个元素；把这些地址归入其他阵营或删掉")
         if not isinstance(addrs, list):
             _fail(f"{source_label} 阵营「{camp}」的值必须是地址列表，"
                   f"收到 {type(addrs).__name__}")
diff --git a/scripts/tests/test_repair_batch_c.py b/scripts/tests/test_repair_batch_c.py
index 48eebc4..4a8f120 100644
--- a/scripts/tests/test_repair_batch_c.py
+++ b/scripts/tests/test_repair_batch_c.py
@@ -157,6 +157,10 @@ def t_f05_unit():
     # 失败分支：值非列表 / 非法阵营名
     check("F05 值非列表硬拒", rejected({"camp_A": "not-a-list"}, "evm"))
     check("F05 空阵营名硬拒", rejected({"": [A]}, "evm"))
+    # F04（review 9.0.0）：EVM 残差桶不得显式配置；Solana 分格式语义不变（build_evolution 默认桶）
+    check("F04 EVM 显式散户桶硬拒", rejected({"大庄": [A], "散户": [B]}, "evm"))
+    check("F04 solana 显式散户不误杀",
+          validate_camp_spec({"散户": [SA]}, chain_family="solana") == {"散户": [SA]})
     # 绿例：规范化返回（EVM lower、保序）
     out = validate_camp_spec({"甲": ["0xAbC0000000000000000000000000000000000001", B]},
                              chain_family="evm")
@@ -249,11 +253,17 @@ def compile_state_cli(td: Path, *extra):
 def t_f05_evm_engines():
     """两 EVM 引擎同批同深度：重复 spec 双双 exit 2；合法 spec 双双照常出货。"""
     dup_spec = {"camps": {"camp_A": [A], "camp_B": [A]}, "entities": {}}
+    retail_spec = {"camps": {"大庄": [A], "散户": [B]}, "entities": {}}
     ok_spec = {"camps": {"项目方": [A], "大庄": [B]}, "entities": {"实体X": [B]}}
     with tempfile.TemporaryDirectory() as s:
         td = Path(s)
         p = build_evm_case(td, dup_spec, expect_rc=2)
         check("F05 replay_duck 跨营重复 exit2", "camp-spec" in p.stderr, p.stderr[-300:])
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        p = build_evm_case(td, retail_spec, expect_rc=2)
+        check("F04 replay_duck 显式散户桶 exit2 且不产序列",
+              "残差桶" in p.stderr and not (td / "data/camp_series.json").exists(), p.stderr[-300:])
     with tempfile.TemporaryDirectory() as s:
         td = Path(s)
         build_evm_case(td, ok_spec)
@@ -270,6 +280,11 @@ def t_f05_evm_engines():
         p = run([ROOT / "scripts/evm/replay_pass2.py", "camps.json",
                  "--data-dir", "data"], td)
         check("F05 replay_pass2 合法 spec 绿例", p.returncode == 0, p.stderr[-300:])
+        (td / "camps_retail.json").write_text(json.dumps(retail_spec, ensure_ascii=False))
+        p = run([ROOT / "scripts/evm/replay_pass2.py", "camps_retail.json",
+                 "--data-dir", "data"], td)
+        check("F04 replay_pass2 显式散户桶 exit2",
+              p.returncode == 2 and "残差桶" in p.stderr, f"rc={p.returncode} {p.stderr[-300:]}")
         check("F04 replay_pass2 sidecar 落盘",
               (td / "data/camp_series.provenance.json").is_file()
               and (td / "data/entity_series.provenance.json").is_file())
```

## 3. 修改前 RED 摘要

完整逐项记录见 [F04_red_evidence.txt](F04_red_evidence.txt)。四项由仓库外临时脚本分别启动独立 Python 进程求值，证据文件先于生产修改落盘；未靠运行整个测试或 `check()` 提取 RED。

| 项目 | 条件表达式结果 | 被测 rc | stderr 尾行 | 序列证据 |
| --- | --- | --- | --- | --- |
| 1. EVM 显式散户拒收 | False（RED） | 0 | 空 | 单元级，无序列 |
| 2. Solana 显式散户接受 | True（GREEN 对照） | 0 | 空 | 单元级，无序列 |
| 3. replay_duck 残差桶报错且不产序列 | False（RED） | 0 | 空 | 序列存在；dates=4，散户=8 |
| 4. replay_pass2 exit2 且残差桶报错 | False（RED） | 0 | 空 | 序列存在；dates=4，散户=8 |

第 3 项基线工厂使用 `expect_rc=0`；第 4 项在相同临时目录先执行 `--emit-csv`（rc=0）再重放。
两引擎的基线「散户」值均为 `[0.0, 0, 40.0, 0, 40.0, 10.0, 36.8421, 10.5263]`，即 `len(散户) == 2*len(dates) == 8`。

## 4. 工单 §0.8 定向测试

七项全部首轮 PASS，均 rc=0。命令按工单执行，环境仅补充 `PYTHONDONTWRITEBYTECODE=1`，避免测试子进程写字节码。未遇到 `data_broken: '_items'`，未启用字体缓存重跑。未运行 `run_all.py` 或 `test_stage2_reseal.py`。

各测试实际结果尾行：

```console
$ python3 -B scripts/tests/test_repair_batch_c.py
PASS: repair batch C (F-05+F-04+fixround1+fixround2) 263 checks
```
首轮 rc=0；耗时 358.837 秒。

```console
$ python3 -B scripts/tests/test_repair_batch_d.py
BATCH D 全部通过
```
首轮 rc=0；耗时 88.439 秒。

```console
$ python3 -B scripts/tests/test_engine_equivalence.py
PASS: 三引擎 gate/退出码 10 例 hypothesis 全等；gate PASS 六产物全等；gate FAIL 正式序列零产物；VARINT 双引擎确定性对表通过
```
首轮 rc=0；耗时 13.643 秒。

```console
$ python3 -B scripts/tests/test_fault_injection.py
PASS: 故障注入 F0–F5 + P0-02 四类通道完整性×三引擎 + R1 receipt 生成/漂移
```
首轮 rc=0；耗时 1.557 秒。

```console
$ python3 -B scripts/tests/test_batch4_invariant_guards.py
PASS B4-G1: bare pool / labels / vertical slice / denominator injections
```
首轮 rc=0；耗时 10.666 秒。

```console
$ python3 -B scripts/tests/test_exemption_guards.py
PASS: exemption guards (EX-01 full-F-03)
```
首轮 rc=0；耗时 0.428 秒。

```console
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```
首轮 rc=0；耗时 3.438 秒。

完整首轮日志保留在仓库外临时目录 `/private/tmp/f04-construction-u3tf2_ws/`，对应文件名为 `<测试文件名>.attempt1.log`。

## 5. 硬约束与兼容性

文档仅查元数据，开工与收工均为以下值：

```console
$ stat -f %z SKILL.md
8021
$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930076
$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
```

使用既有 `ok_spec` 及同一工厂在修改前后分别运行两个 EVM 引擎，逐字节比较阵营、实体序列，四份输出全部一致；规范化 dict 的序列化内容也一致：

| 产物（两引擎相同） | 字节数 | 修改前后 SHA-256 |
| --- | ---: | --- |
| `camp_series.json` | 435 | `4de17c06f330bc386136115febe2ce8f23206a3ef4cd4ec75d3c3c51d781cc6e` |
| `entity_series.json` | 112 | `e0e67ec1077640da7fe894fa9594145d07e7f3f1e9ba574735d93fcb29b488ed` |

`validate_camp_spec({"散户": [SA]}, chain_family="solana") == {"散户": [SA]}` 的 GREEN 对照由新增回归检查覆盖；仓库外兼容性核验同时确认 `load_addr_camp_json` 修改前后均接受 `{SA: "散户"}`。

静态核对确认 `_normalize`、`load_addr_camp_json` 源码与 HEAD 完全相同，`validate_camp_spec` 参数签名不变；原互斥查重代码未修改。四入口、`camp_series_provenance.py`、文档、版本文件及两类 manifest 均无 diff。

## 6. git diff --stat 与白名单

```console
$ git diff --stat
 scripts/lib/camp_spec.py             |  5 ++++-
 scripts/tests/test_repair_batch_c.py | 15 +++++++++++++++
 2 files changed, 19 insertions(+), 1 deletion(-)
```

`git diff --stat` 只统计已追踪文件。另新建以下两个未追踪白名单文件：

- `maintenance/repair-20260918d-p1-f01-f04/F04_done.md`
- `maintenance/repair-20260918d-p1-f01-f04/F04_red_evidence.txt`

`git diff --check` 通过；暂存区为空，HEAD 保持 `a4a0f2ccb5cb4beae1c20949fe2f5bae1f68afa9`。

## 7. 与工单差异 / 停工点

无方案差异，无停工点。工单 §2 的六处修改逐条落地；Q5/Q6/Q7 按登记不修处理，未修改台账。所有临时取证脚本、兼容性样本和完整测试日志均在仓库外 `/private/tmp/f04-construction-u3tf2_ws/`，没有新增仓库 helper。

全程离线；未 commit、push、部署，未执行 stash/checkout/reset，未主动删除文件或目录。辅助进程元数据查询 `ps` 被沙箱拒绝，未提权或绕过；此查询不属于测试，不影响七项实测结果。

## 8. 禁读披露

施工方未读取 `~/.codex/`（包括 memories）、`archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、Desktop 或 Documents。启动时 `git ls-files` 从 Git 索引返回过历史 maintenance 文件名，未打开、读取正文、复制或修改这些历史文件。`SKILL.md`、references 和 commands-staging 仅按工单统计文件大小。历史 maintenance 文件仅由测试子进程访问，属于工单 §0.2 明确豁免。
