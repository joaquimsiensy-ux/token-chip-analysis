# 施工 F06：完成

按 `workorder_F06.md` **v2** 完成 §0–§3。consumer 现在根据实体成员的 `tier=exclude` 标签强制要求 `INFRA_IN_ENTITY`，清空 flag 并同步 `n_flags` 已无法绕过身份闸。原有 resolution 校验继续生效。八项定向检查全部 PASS。

## 1. 开工基线与核实结果

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。

§0.1 两条命令已在任何写入前实际运行；原始终端输出如下，两条命令均无 stdout，退出码均为 0：

```text
$ git status --short
$ git diff --stat 311e6c4 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```
提示词派工基线为 `ad93d95a6fb6cd0a0e3102edd394463cce2d5ede`，实际开工 HEAD 为 `1e5c7e0c9b734a74ffc5c8e3043a8dcb03cd81b1`。已核实多出的唯一提交只给施工提示词填写派工 HEAD；工单及 §0.1 指定内容均无变化。依据工单说明的“工单与提示词单独 commit、HEAD 晚于内容基线”及两项基线检查通过继续施工，没有放宽代码基线。

```text
$ git rev-parse HEAD
1e5c7e0c9b734a74ffc5c8e3043a8dcb03cd81b1
$ git log --format='%H %s' ad93d95..HEAD
1e5c7e0c9b734a74ffc5c8e3043a8dcb03cd81b1 repair-20260918-p0-f04-f07: 施工 F06 提示词填派工 HEAD ad93d95
$ git show --format=fuller --stat --oneline HEAD
1e5c7e0 repair-20260918-p0-f04-f07: 施工 F06 提示词填派工 HEAD ad93d95
 maintenance/repair-20260918-p0-f04-f07/construct_F06_prompt.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
$ git diff --stat ad93d95 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md maintenance/repair-20260918-p0-f04-f07/workorder_F06.md
```
五个定位锚在改动前均实际执行 `grep -n -F`，每个恰好命中一处，行号完全一致：

```text
$ grep -n -F '        if address in expected_entities and label is None:' 'scripts/report/entity_identity_gate.py'
273:        if address in expected_entities and label is None:
$ grep -n -F '                errors.append(f'\''{address} 无标签实体成员必须为 {required}'\'')' 'scripts/report/entity_identity_gate.py'
277:                errors.append(f'{address} 无标签实体成员必须为 {required}')
$ grep -n -F '        if require_resolved and flag and not str(row.get('\''resolution'\'', '\'''\'')).strip():' 'scripts/report/entity_identity_gate.py'
278:        if require_resolved and flag and not str(row.get('resolution', '')).strip():
$ grep -n -F '        assert gate.check(str(mismatch_path)) != 0, "逐行实体必须与 state 一致"' 'scripts/tests/test_entity_identity_gate.py'
65:        assert gate.check(str(mismatch_path)) != 0, "逐行实体必须与 state 一致"
$ grep -n -F '    print("PASS: P1-01 无标签实体成员 + 严格 identity gate schema/计数/唯一性/实体绑定")' 'scripts/tests/test_entity_identity_gate.py'
67:    print("PASS: P1-01 无标签实体成员 + 严格 identity gate schema/计数/唯一性/实体绑定")
```
已逐行核实 producer 原 :327–345（含 :336–337）、label 形状检查 :257–260、flag 枚举检查 :267–270、resolution 检查 :278–279，以及测试夹具 :25–34。工单无其他独立标注“开工核实”的条目。

## 2. §2.1 / §2.2 git diff 原文

```diff
diff --git a/scripts/report/entity_identity_gate.py b/scripts/report/entity_identity_gate.py
index a694cd1..a1d1b36 100644
--- a/scripts/report/entity_identity_gate.py
+++ b/scripts/report/entity_identity_gate.py
@@ -275,6 +275,11 @@ def validate_gate(gate_path, state_path=None, require_resolved=True):
                 else 'BIG_UNLABELED'
             if flag != required:
                 errors.append(f'{address} 无标签实体成员必须为 {required}')
+        # 与 producer（build，tier=exclude 的实体成员必出 INFRA_IN_ENTITY）对称：consumer 按
+        # 绑定标签重推必需 flag，不让 flag 字段自行清空来解除 resolution 义务。
+        if address in expected_entities and isinstance(label, dict) \
+                and label.get('tier') == 'exclude' and flag != 'INFRA_IN_ENTITY':
+            errors.append(f'{address} 公共设施标签（tier=exclude）实体成员必须为 INFRA_IN_ENTITY')
         if require_resolved and flag and not str(row.get('resolution', '')).strip():
             errors.append(f'{address} {flag} 无 resolution')
     missing = sorted(set(expected_entities) - {r.get('address') for r in rows if isinstance(r, dict)})
diff --git a/scripts/tests/test_entity_identity_gate.py b/scripts/tests/test_entity_identity_gate.py
index 204b0a8..7d1f0f2 100644
--- a/scripts/tests/test_entity_identity_gate.py
+++ b/scripts/tests/test_entity_identity_gate.py
@@ -64,7 +64,34 @@ def main():
         dump(mismatch_path, mismatch)
         assert gate.check(str(mismatch_path)) != 0, "逐行实体必须与 state 一致"
 
-    print("PASS: P1-01 无标签实体成员 + 严格 identity gate schema/计数/唯一性/实体绑定")
+        f06_a = json.loads(json.dumps(built))
+        f06_a["rows"][0]["label"] = {"name": "public-infra", "category": "dex", "tier": "exclude", "source": "test"}
+        f06_a["rows"][0]["flag"] = ""
+        f06_a["rows"][0]["resolution"] = ""
+        f06_a["n_flags"] = 0
+        f06_a_path = Path(tmp) / "f06_a.json"
+        dump(f06_a_path, f06_a)
+        assert gate.check(str(f06_a_path)) != 0, "F06 清空 flag 不得解除 INFRA 义务"
+
+        f06_b = json.loads(json.dumps(built))
+        f06_b["rows"][0]["label"] = {"name": "public-infra", "category": "dex", "tier": "exclude", "source": "test"}
+        f06_b["rows"][0]["flag"] = "INFRA_IN_ENTITY"
+        f06_b["rows"][0]["resolution"] = ""
+        f06_b["n_flags"] = 1
+        f06_b_path = Path(tmp) / "f06_b.json"
+        dump(f06_b_path, f06_b)
+        assert gate.check(str(f06_b_path)) != 0, "F06 INFRA 无 resolution 仍拒（既有行为回归）"
+
+        f06_c = json.loads(json.dumps(built))
+        f06_c["rows"][0]["label"] = {"name": "public-infra", "category": "dex", "tier": "exclude", "source": "test"}
+        f06_c["rows"][0]["flag"] = "INFRA_IN_ENTITY"
+        f06_c["rows"][0]["resolution"] = "已核：DEX 池地址，已从实体成员剔除"
+        f06_c["n_flags"] = 1
+        f06_c_path = Path(tmp) / "f06_c.json"
+        dump(f06_c_path, f06_c)
+        assert gate.check(str(f06_c_path)) == 0, "F06 INFRA 带 resolution 放行"
+
+    print("PASS: P1-01 无标签实体成员 + 严格 identity gate schema/计数/唯一性/实体绑定/F06 exclude 标签重推 INFRA")
     return 0
 
 
```
## 3. RED → GREEN

RED 文件：`maintenance/repair-20260918-p0-f04-f07/F06_red_evidence.txt`。先用内联 Python 复制既有 build 夹具，并通过真实绑定 receipt 重放三种情形；在生产文件未改时写入证据。随后只加入新测试，实际运行定向测试，在新断言处失败；把命令、原始输出和退出码追加到同一证据文件之后，才修改生产代码。

被测生产文件修改前 SHA-256：`62eecf07ccb6ebffc096e493bbc33bdc6e596940e85d83b229ab184530dc1232`。

| 用例 | 修改前实际结果 | 修改后实际结果 |
| --- | --- | --- |
| F06 清空 flag 不得解除 INFRA 义务 | `validate_gate=[]`，`check=0`，RED | `check=1`，拒绝，GREEN |
| F06 INFRA 无 resolution 仍拒 | `check=1`，GREEN | `check=1`，GREEN |
| F06 INFRA 带 resolution 放行 | `validate_gate=[]`，`check=0`，GREEN | `check=0`，GREEN |

内联 RED harness 退出码为 1；加入新用例后的测试也退出 1，最后一行为 `AssertionError: F06 清空 flag 不得解除 INFRA 义务`。生产修改后同一测试退出 0；既有五段断言保持不变且全部通过。

## 4. §0.8 各测试结果尾行

下列八条命令全部实际运行，退出码均为 0；各代码块保留相应输出的最后一行。负例打印的 `[FAIL]` 为断言所要求的拒绝行为。

```text
$ python3 -B scripts/tests/test_entity_identity_gate.py
PASS: P1-01 无标签实体成员 + 严格 identity gate schema/计数/唯一性/实体绑定/F06 exclude 标签重推 INFRA
exit_code=0
```
```text
$ python3 -B scripts/tests/test_batch17_identity_chain_alias.py
PASS batch17 identity chain alias: 4/4
exit_code=0
```
```text
$ python3 -B scripts/tests/test_round4_identity_emitter.py
PASS: real EVM collector+preflight+replay and Solana scan chains; copied-hash self-reports blocked
exit_code=0
```
```text
$ python3 -B scripts/tests/test_v2_identity_history.py
PASS: R-3 v2 historical identity maintenance/consumer parity
exit_code=0
```
```text
$ python3 -B scripts/tests/test_audit_release_gate.py
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
exit_code=0
```
```text
$ python3 -B scripts/tests/test_a4_gate.py
a4_gate 契约测试全部通过（23 项）
exit_code=0
```
```text
$ python3 -B scripts/tests/test_stage2_closeout.py
stage2_closeout: 28/28 PASS
exit_code=0
```
```text
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
exit_code=0
```
未运行 `run_all.py` 或 `test_stage2_reseal.py`，不对全套验收作结论。`invariant_scan.py` PASS，无需且未修改任何 manifest。

## 5. §1.1 文档字节数

开工及改后三个数字一致；只运行元数据统计，未为统计读取文档内容：

| 范围 | 字节数 |
| --- | ---: |
| `SKILL.md` | 8021 |
| `references/**/*.md` 合计 | 930061 |
| `commands-staging/*.md` 合计 | 8798 |

```text
$ stat -f %z SKILL.md
find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8021
930061
8798
```
## 6. 范围核验与 git diff --stat

```text
$ git diff --stat
 scripts/report/entity_identity_gate.py     |  5 +++++
 scripts/tests/test_entity_identity_gate.py | 29 ++++++++++++++++++++++++++++-
 2 files changed, 33 insertions(+), 1 deletion(-)
```
`git diff --check` 退出 0、无输出。另用内联 Python 将生产文件精确移除工单五行后与 HEAD 原文比较，并从测试移除三个新增用例、还原 print 后与 HEAD 比较，结果：

```text
PASS: production differs only by the five specified insertion lines
PASS: existing test lines 1-65 unchanged; remaining changes confined to three cases and print suffix
PASS: build, FLAGS, GATE_SCHEMA, load_snapshot_binding and other validate_gate branches unchanged
```
本轮只修改两处代码白名单，并新建本报告及 RED 证据。`git diff --stat` 不包含未跟踪报告文件。两份 manifest、producer、schema、FLAGS、snapshot binding、其他消费分支及既有测试断言均未改变。未 commit、push、stash、checkout、reset 或部署 commands；全部离线完成。

收尾文件 SHA-256：

```text
bac32a17873a96184925e0bb43b720a07771baa5019c5039c81698a57bf912ce  scripts/report/entity_identity_gate.py
29088617efa7e086a18e17474f3b3ae2f2420214d17415bc500464284536b534  scripts/tests/test_entity_identity_gate.py
c3675adb1cc6ace5ef8591a7ef7445a1cb04713e62874cd0155e45671109ca68  maintenance/repair-20260918-p0-f04-f07/workorder_F06.md
9b854643179fc44a3ce40ef535dd529796558f195c07ecf6270f6e90851b7086  maintenance/repair-20260918-p0-f04-f07/F06_red_evidence.txt
```
## 7. 与工单差异 / 停工点

实现及验收无偏离，无停工点。HEAD 相对派工值的提示词提交已在第 1 节核实并披露。

施工期间先观察到未跟踪的 `maintenance/repair-20260918-p0-f04-f07/review_F04_reply_r1.md`。收尾核验快照中 HEAD 已推进到 `e4cc5da49e63d507f8faeae27d3faf4cdd8fc756`，新增两次 F04 提交；另观察到未跟踪的 `review_F05_reply_r1.md`。本轮未生成、读取或修改这两份复核文件，未执行任何 commit。重新运行 §0.1 内容基线检查仍无输出，F06 两个代码文件的 diff 与测试时完全一致，三项文档字节数不变。

```text
$ git log --format='%H %s' ad93d95..HEAD
e4cc5da49e63d507f8faeae27d3faf4cdd8fc756 repair-20260918-p0-f04-f07: 工单 F04 v2 正文(复核 r1 四条)
43f6c6bbbee8c8657b8b7712a0d6d75785aa2737 repair-20260918-p0-f04-f07: 工单 F04 v2(复核 r1 四条)+复核回复落盘
1e5c7e0c9b734a74ffc5c8e3043a8dcb03cd81b1 repair-20260918-p0-f04-f07: 施工 F06 提示词填派工 HEAD ad93d95
$ git diff --stat 311e6c4 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

收尾 `git status --porcelain=v1 --untracked-files=all` 原始快照（并发复核文件不归入本轮施工产物）：

```text
 M scripts/report/entity_identity_gate.py
 M scripts/tests/test_entity_identity_gate.py
?? maintenance/repair-20260918-p0-f04-f07/F06_done.md
?? maintenance/repair-20260918-p0-f04-f07/F06_red_evidence.txt
?? maintenance/repair-20260918-p0-f04-f07/review_F05_reply_r1.md
```

## 8. 禁读披露

会话启动时系统已自动提供记忆摘要；本轮未通过工具打开或读取 `~/.codex/` 下任何文件，也未进行插件启动搜索。未主动读取禁读的 archive、blind-reviews、.staging_*、references/attic.md、其他历史 maintenance、Desktop 或 Documents 内容；守卫/测试脚本自身的文档遍历按工单例外运行。§1.1 仅统计元数据。
