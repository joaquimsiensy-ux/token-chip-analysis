# 施工 B：完成

执行工单：`maintenance/repair-20260917-p0-four/workorder_B.md`，文件头版本 **v2**。
开工 HEAD：`0877f714114839d6cfb5e3517e2039136f9d68f5`；指定内容基线：`4cbfe48`。
结果：B1/B2/B3 完成；先 RED 后 GREEN；三个指定测试均 exit_code=0。

## ① §0.1 两条开工基线命令及实际输出

以下两条命令均实际执行，exit_code=0；各自输出均为 0 字节。
代码块内命令下一行没有输出，未省略非空内容。

```console
$ git status --short
```

```console
$ git diff --stat 4cbfe48 HEAD -- scripts/report/audit_release_gate.py scripts/tests/test_audit_release_gate.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

六处指定锚均在修改前用 `grep -n -F` 实际核验；唯一且行号一致：

```text
scripts/report/audit_release_gate.py expected_line=895
895:    pos_seen, wallet_by_entity, position_by_address = set(), {}, {}
scripts/report/audit_release_gate.py expected_line=915
915:        wallet_by_entity[entity] = wallet_by_entity.get(entity, 0) + amt
scripts/report/audit_release_gate.py expected_line=962
962:            errors.append(f"实体 {entity} 经济控制算术不闭合: {confirmed} != {wallet}+{facility_sum}")
scripts/report/audit_release_gate.py expected_line=964
964:    active_entities = {entity for entity, status, _ in member_map.values()
scripts/tests/test_audit_release_gate.py expected_line=554
554:        assert any("balance_source sha256" in x for x in errors), errors
scripts/tests/test_audit_release_gate.py expected_line=556
556:    # P2-01：零余额成员可用显式 zero_balance_proof，位置账缺行按 0 闭合。
ALL 6 ANCHORS PASS
```

## ② B1/B2 生产 diff 原文

实际命令：`git diff -- scripts/report/audit_release_gate.py`。

```diff
diff --git a/scripts/report/audit_release_gate.py b/scripts/report/audit_release_gate.py
index 4f5833f..340e742 100644
--- a/scripts/report/audit_release_gate.py
+++ b/scripts/report/audit_release_gate.py
@@ -892,7 +892,7 @@ def check_three_ledgers(case_dir: Path, data: dict, errors: list[str], chain=Non
                     errors.append(f"membership[{i}] as_of_balance_raw 与绑定快照不一致")
         member_map[key] = (entity, status, balance)
 
-    pos_seen, wallet_by_entity, position_by_address = set(), {}, {}
+    pos_seen, wallet_by_entity, expanded_by_entity, position_by_address = set(), {}, {}, {}
     for i, row in enumerate(positions):
         if not isinstance(row, dict):
             errors.append(f"position[{i}] 不是对象")
@@ -912,7 +912,11 @@ def check_three_ledgers(case_dir: Path, data: dict, errors: list[str], chain=Non
             errors.append(f"位置账重复 location/address: {key}")
         pos_seen.add(key)
         amt = raw_int(row.get("amount_raw"), f"position[{i}].amount_raw", errors)
-        wallet_by_entity[entity] = wallet_by_entity.get(entity, 0) + amt
+        wallet_by_entity.setdefault(entity, 0)   # 实体集合语义不变（:966 用 set(wallet_by_entity)）
+        if member_map.get(addr_key, ("", "", None))[1] == "expanded":
+            expanded_by_entity[entity] = expanded_by_entity.get(entity, 0) + amt
+        else:
+            wallet_by_entity[entity] += amt
         position_by_address[addr_key] = position_by_address.get(addr_key, 0) + amt
 
     for address, (entity, status, balance) in member_map.items():
@@ -960,6 +964,27 @@ def check_three_ledgers(case_dir: Path, data: dict, errors: list[str], chain=Non
                             f"economic[{i}].confirmed_economic_control_raw", errors)
         if confirmed != wallet + facility_sum:
             errors.append(f"实体 {entity} 经济控制算术不闭合: {confirmed} != {wallet}+{facility_sum}")
+        # R03（2026-09-17）：expanded 成员只进上限区间，不进可证下限。区间用重算值校验
+        # （不信自报 confirmed）：下限＝严格自持＋已闭合设施；上限 ≥ 下限＋expanded 成员位置之和
+        # （文档 economic-control-accounting §3 允许上限再含"疑似但未确权的设施受益权增量"，
+        # 三账无该增量的来源字段，故上限只验下界——超出部分属登记的残余风险 P10）。
+        want_lo = wallet + facility_sum
+        min_hi = want_lo + expanded_by_entity.get(entity, 0)
+        has_expanded = any(e == entity and s == "expanded" for e, s, _ in member_map.values())
+        if "expanded_economic_control_range_raw" not in row:
+            if has_expanded:
+                errors.append(f"实体 {entity} 有 expanded 成员但缺 expanded_economic_control_range_raw"
+                              f"（须为 [{want_lo}, ≥{min_hi}]）")
+        else:
+            rng = row.get("expanded_economic_control_range_raw")
+            if not isinstance(rng, list) or len(rng) != 2:
+                errors.append(f"economic[{i}].expanded_economic_control_range_raw 须为 [下限, 上限] 两元素数组")
+            else:
+                lo = raw_int(rng[0], f"economic[{i}].expanded_economic_control_range_raw[0]", errors)
+                hi = raw_int(rng[1], f"economic[{i}].expanded_economic_control_range_raw[1]", errors)
+                if lo != want_lo or hi < min_hi:
+                    errors.append(f"实体 {entity} expanded 区间不闭合: [{lo}, {hi}] 须满足下限 == {want_lo}"
+                                  f"（严格自持＋设施）且上限 >= {min_hi}（下限＋expanded 成员位置之和）")
 
     active_entities = {entity for entity, status, _ in member_map.values()
                        if status != "excluded"}
```

## ③ RED 逐例摘要与 GREEN

原始证据：[B_red_evidence.txt](B_red_evidence.txt)。
先插入 B3，再用内联 Python 的 AST 提取执行新增循环；每例有独立临时目录，逐例捕获 AssertionError，全部执行后汇总。
直调 `check_three_ledgers(chain=None)`，不走 `gate.run`。
生产文件在 RED 前后均与 `4cbfe48` 相同；SHA256 前后均为
`f865d53ab2c73eaf15c63226836d385c65c1bc12eec2ab4cfd8af35b0fb4a4d2`。
RED runner exit_code=1，共 9/10 个用例失败，符合工单预期。

| 用例 | 修改前实际结果 / AssertionError 原文 | 修改后 |
| --- | --- | --- |
| 1 R03 绿例 | RED：`['实体 e1 钱包自持与位置账不闭合: 100 != 300']` | PASS |
| 2 原反例必拒 | RED：`[]`（基线错误放行） | PASS |
| 3 上限低于下界拒 | RED：`['实体 e1 钱包自持与位置账不闭合: 100 != 300']` | PASS |
| 4 下限不等拒 | RED：`['实体 e1 钱包自持与位置账不闭合: 100 != 300']` | PASS |
| 5 上限含疑似设施增量放行 | RED：`['实体 e1 钱包自持与位置账不闭合: 100 != 300']` | PASS |
| 6 形状错拒 | RED：`['实体 e1 钱包自持与位置账不闭合: 100 != 300']` | PASS |
| 7 显式 null 拒 | RED：`['实体 e1 钱包自持与位置账不闭合: 100 != 300']` | PASS |
| 8 有 expanded 缺字段拒 | RED：`['实体 e1 钱包自持与位置账不闭合: 100 != 300']` | PASS |
| 9 无 expanded 缺字段放行 / 在场须合法 | 缺字段 PASS；[100,150] PASS；[100,99] RED：`[]` | 全部 PASS |
| 10 expanded 仍须逐地址闭合 | PASS（原有回归） | PASS |

GREEN 时仍使用 RED 时的同一测试文件，SHA256 为
`b761f94235bbc7b5b9dac62452743fa76e769120f8a79ef39bb614055cdb03ff`。
用例 9 先收集两个区间的结果，再断言 [100,99]，使两条兼容性分支也在 RED 日志中留证。

B3 修改后实际输出：

```text
ok    1 R03 绿例
ok    2 R03 原反例必拒
ok    3 R03 上限低于下界拒
ok    4 R03 下限不等拒
ok    5 R03 上限含疑似设施增量放行
ok    6 R03 形状错拒
ok    7 R03 显式 null 拒
ok    8 R03 有 expanded 缺字段拒
ok    R03 case 9 无 expanded 缺字段放行
ok    R03 case 9 无 expanded 上限含疑似设施增量放行
ok    9 R03 无 expanded 缺字段放行 / 在场须合法
ok    10 R03 逐地址闭合对 expanded 仍生效
```

## ④ §0.8 三个测试结果尾行

环境：`PYTHONDONTWRITEBYTECODE=1`，防止子进程留下 pyc；
`MPLCONFIGDIR=/private/tmp/repair-20260917-p0-four-b-mpl`。
仅运行这三个指定测试文件，另有上述 B3 独立 RED 循环；未运行 `run_all.py`。

命令：`python3 -B scripts/tests/test_audit_release_gate.py`；exit_code=0。

```text
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
```

命令：`python3 -B scripts/tests/test_batch15_three_ledgers_frozen.py`；exit_code=0。

```text
PASS batch15 frozen consumers: 12/12
```

命令：`python3 -B scripts/tests/test_repair_batch_d.py`；exit_code=0。

```text
BATCH D 全部通过
```

## ⑤ §1.1 三个字节数

开工与完工结果相同；以下命令只统计元数据，未读取文档内容。

```console
$ stat -f %z SKILL.md
8021
$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930070
$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
```

## ⑥ 最终 git diff --stat 与工作树

```text
 scripts/report/audit_release_gate.py     |  29 +++++-
 scripts/tests/test_audit_release_gate.py | 156 +++++++++++++++++++++++++++++++
 2 files changed, 183 insertions(+), 2 deletions(-)
```

`git diff --stat` 只展示两个已跟踪代码文件；新增报告和 RED 证据由以下
`git status --short` 输出覆盖。最终修改/新增路径全部属于 §0.3 白名单。

```text
 M scripts/report/audit_release_gate.py
 M scripts/tests/test_audit_release_gate.py
?? maintenance/repair-20260917-p0-four/B_done.md
?? maintenance/repair-20260917-p0-four/B_red_evidence.txt
```

## ⑦ 差异、停工点与边界核验

无停工点，无超出工单的功能改动。

- 生产文件由 `4cbfe48` 原文仅套用 B1 两处替换和 B2 插入后，与当前文件逐字一致；§0.4 所列受保护片段未变。
- 测试只在原 :554 后、:556 前插入 B3；移除该新增块后与 `4cbfe48` 原文件逐字一致，全部既有断言不变，原 :516–554 块保留且整文件通过。
- `git diff --check` 实际运行，exit_code=0，输出为空。
- 文档、VERSION、pyproject、CHANGELOG、contract_manifest、invariant_manifest 和其他测试文件均未修改。
- 离线完成；未 commit、push、部署，未执行 stash/checkout/reset。
- §4 存量 APU 案验证由调度方本机执行，本次未执行；本报告不声称全套或存量验收完成。
- P10 保留：上限超出“下限＋Σexpanded”的疑似设施增量来源和数额不在本段校验；未修改调度方维护的 `code_change_pending.md`。

静态边界核验输出：

```text
PASS: 生产差异与 B1/B2 指定片段逐字一致；所有受保护生产片段原样
PASS: 测试仅在原 :554 后、:556 前新增；全部既有文本和断言逐字不变
PASS: RED 后测试文件 SHA256 未变 b761f94235bbc7b5b9dac62452743fa76e769120f8a79ef39bb614055cdb03ff
SHA256 scripts/report/audit_release_gate.py 940eedd582a036d0059e5a740eb0e52ac52a1ff045e36698d4db512d06c159c5
SHA256 scripts/tests/test_audit_release_gate.py b761f94235bbc7b5b9dac62452743fa76e769120f8a79ef39bb614055cdb03ff
```

## ⑧ 禁读披露

本次未通过工具读取 `~/.codex/` 下任何文件。会话启动时自动载入了记忆摘要，
已在首次进度消息披露；本次未查询 memory 文件，也未以历史结论替代当前工单和校验。

未读取 `archive/`、`blind-reviews/`、`.staging_*`、
`references/attic.md` 或 `/Users/uravvv/Desktop` 下文件的内容。
`references/attic.md` 仅随 §1.1 命令统计文件大小。
