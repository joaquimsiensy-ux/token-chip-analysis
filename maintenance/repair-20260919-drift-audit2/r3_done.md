# 施工 R3：完成

工单：`maintenance/repair-20260919-drift-audit2/workorder_r3.md`（v2）。

内容基线：`0a53cbd`；施工 HEAD：`4c1706a9339ec1dd9ce6ffc20653f365ac30ad84`。

D1、D2、D3 共七处整行替换已按 §2 字面完成；`references/scan-schemas.md` 净减 6 B，锚外字节保持不变。九项守卫全部通过。仅修改该文档，并新建本报告；未 commit、push 或部署。

## 1. §0.1 开工基线校验

命令：```sh
git status --short
```
原始输出（为空）：

```text
```

退出码：`0`。

命令：```sh
git rev-parse HEAD
```
原始输出：

```text
4c1706a9339ec1dd9ce6ffc20653f365ac30ad84
```

退出码：`0`。

命令：```sh
git diff --stat 0a53cbd HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md
```
原始输出（为空）：

```text
```

退出码：`0`。

结论：开工工作区干净，指定内容范围相对 `0a53cbd` 的差异为空。

## 2. 锚点核验与逐条改前 → 改后 diff

修改前逐项运行 `grep -n -F`；七项均退出码 0，输出均恰一行，整行内容及行号一致。以下保留实际命令和原始输出。

命令：```sh
grep -n -F -- '- array_monotonic_unique 与 array_in_range 是生产时对原始响应数组的断言结果；任一为 false 则该段 unconfirmed，其 NO_HEADER 保持未确认，有效 verdict 为 INCONCLUSIVE；--live-canary 重拉若干段与位图切片对表。' references/scan-schemas.md
```
原始输出：

```text
714:- array_monotonic_unique 与 array_in_range 是生产时对原始响应数组的断言结果；任一为 false 则该段 unconfirmed，其 NO_HEADER 保持未确认，有效 verdict 为 INCONCLUSIVE；--live-canary 重拉若干段与位图切片对表。
```

退出码：`0`。

命令：```sh
grep -n -F -- '| `census[].sqd_blockhash` | string | 是 |  |' references/scan-schemas.md
```
原始输出：

```text
795:| `census[].sqd_blockhash` | string | 是 |  |
```

退出码：`0`。

命令：```sh
grep -n -F -- '| `shared_map` | object\|null | 是 | asset_path,version,sha256,supersedes,generated_at,reused_ranges,unverified_ranges,recheck_stats,canary{slots[64],counts_sha256,verified_at} |' references/scan-schemas.md
```
原始输出：

```text
667:| `shared_map` | object\|null | 是 | asset_path,version,sha256,supersedes,generated_at,reused_ranges,unverified_ranges,recheck_stats,canary{slots[64],counts_sha256,verified_at} |
```

退出码：`0`。

命令：```sh
grep -n -F -- '| `shared_map.version` | string | 是 |  |' references/scan-schemas.md
```
原始输出：

```text
688:| `shared_map.version` | string | 是 |  |
```

退出码：`0`。

命令：```sh
grep -n -F -- '| `shared_map.sha256` | string (sha256 hex) | 是 |  |' references/scan-schemas.md
```
原始输出：

```text
689:| `shared_map.sha256` | string (sha256 hex) | 是 |  |
```

退出码：`0`。

命令：```sh
grep -n -F -- '| `shared_map.generated_at` | string | 是 |  |' references/scan-schemas.md
```
原始输出：

```text
691:| `shared_map.generated_at` | string | 是 |  |
```

退出码：`0`。

命令：```sh
grep -n -F -- '| `shared_map.canary.slots` | array[integer] | 是 | 长度64 |' references/scan-schemas.md
```
原始输出：

```text
695:| `shared_map.canary.slots` | array[integer] | 是 | 长度64 |
```

退出码：`0`。

### D1：删除 `--live-canary` 与位图切片对表的错误承诺（第 714 行）

```diff
--- a/references/scan-schemas.md
+++ b/references/scan-schemas.md
@@ -714 +714 @@
-- array_monotonic_unique 与 array_in_range 是生产时对原始响应数组的断言结果；任一为 false 则该段 unconfirmed，其 NO_HEADER 保持未确认，有效 verdict 为 INCONCLUSIVE；--live-canary 重拉若干段与位图切片对表。
+- array_monotonic_unique 与 array_in_range 是生产时对原始响应数组的断言结果；任一为 false 则该段 unconfirmed，其 NO_HEADER 保持未确认，有效 verdict 为 INCONCLUSIVE。
```

### D2：`census[].sqd_blockhash` 补充 `null` 类型（第 795 行）

```diff
--- a/references/scan-schemas.md
+++ b/references/scan-schemas.md
@@ -795 +795 @@
-| `census[].sqd_blockhash` | string | 是 |  |
+| `census[].sqd_blockhash` | string\|null | 是 |  |
```

### D3：共享地图回退对象放宽元数据类型及 canary 长度（第 667、688、689、691、695 行）

```diff
--- a/references/scan-schemas.md
+++ b/references/scan-schemas.md
@@ -667 +667 @@
-| `shared_map` | object\|null | 是 | asset_path,version,sha256,supersedes,generated_at,reused_ranges,unverified_ranges,recheck_stats,canary{slots[64],counts_sha256,verified_at} |
+| `shared_map` | object\|null | 是 | asset_path,version,sha256,supersedes,generated_at,reused_ranges,unverified_ranges,recheck_stats,canary{slots,counts_sha256,verified_at} |
@@ -688 +688 @@
-| `shared_map.version` | string | 是 |  |
+| `shared_map.version` | string\|null | 是 |  |
@@ -689 +689 @@
-| `shared_map.sha256` | string (sha256 hex) | 是 |  |
+| `shared_map.sha256` | string (sha256 hex)\|null | 是 |  |
@@ -691 +691 @@
-| `shared_map.generated_at` | string | 是 |  |
+| `shared_map.generated_at` | string\|null | 是 |  |
@@ -695 +695 @@
-| `shared_map.canary.slots` | array[integer] | 是 | 长度64 |
+| `shared_map.canary.slots` | array[integer] | 是 | 长度0或64；复用成功时为64 |
```

施工后重新从工单 §2 提取十四个整行代码块，按七对替换重建施工 HEAD 中的原文件，并与工作区结果逐字节比较；原始核验输出：

```text
PASS: exactly seven literal full-line replacements from workorder §2; all other bytes unchanged.
references/scan-schemas.md byte delta: -6
{"SKILL.md": 8021, "commands-staging/*.md": 8789, "references_three_globs": 930073}
```

## 3. §1.1 字节实测

| 统计范围 | 施工前（B） | 施工后（B） | 工单要求 |
| --- | ---: | ---: | --- |
| `SKILL.md` | 8021 | 8021 | 固定为 8021 |
| `commands-staging/*.md` 合计 | 8789 | 8789 | 固定为 8789 |
| `references/*.md references/casebook/*.md references/labels/*.md` 合计 | 930079 | 930073 | ≤ 930260 |

按各 glob 匹配文件的 `stat().st_size` 求和；未读取 `references/attic.md` 内容。references 合计净减 6 B，与工单模拟值一致。

## 4. §1.2 各守卫原始输出

全部离线运行；各命令仅设置 `PYTHONDONTWRITEBYTECODE=1`，避免生成 Python 字节码。脚本及参数未改动。

### `python3 scripts/tests/docs_lint.py`

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

退出码：`0`。

### `python3 scripts/tests/docs_lint.py --all`

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

退出码：`0`。

### `python3 scripts/tests/casebook_lint.py`

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

退出码：`0`。

### `python3 scripts/tests/changelog_lint.py`

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

退出码：`0`。

### `python3 scripts/tests/test_contract_routes.py`

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

退出码：`0`。

### `python3 scripts/tests/test_sixlens_docs.py`

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

退出码：`0`。

### `python3 scripts/tests/test_g3_docs_guards.py`

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

退出码：`0`。

### `python3 scripts/tests/test_version_consistency.py`

```text
PASS: M-03 version metadata consistent at 9.0.1
```

退出码：`0`。

### `python3 scripts/tests/test_commands_deploy_sync.py`

```text
PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
```

退出码：`0`。

## 5. git diff --stat 与空白检查

命令：```sh
git diff --stat
```
原始输出：

```text
 references/scan-schemas.md | 14 +++++++-------
 1 file changed, 7 insertions(+), 7 deletions(-)
```

退出码：`0`。

命令：```sh
git diff --check
```
原始输出（为空）：

```text
```

退出码：`0`。

上述 `git diff --stat` 仅含白名单文件 `references/scan-schemas.md`。本报告为新建、未暂存文件，不计入普通 `git diff --stat`。

## 6. 差异与停工点

无偏离、无停工点。基线、七处锚点、字面替换、字节约束和九项守卫均通过。未修改 `scripts/`、`commands-staging/`、`CHANGELOG.md` 或两份 manifest；未改变版本。

## 7. 禁读披露

本次未读取 `~/.codex/` 下任何文件，未读取 memories；未直接读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/` 或 `references/attic.md` 的内容。`references/attic.md` 仅计文件大小。`maintenance/` 下的读取限定在 `maintenance/repair-20260919-drift-audit2/`。

守卫脚本按工单要求原样运行；其内部既有文档遍历属于工单明确允许的被测代码行为。未使用外部网络、未启动插件搜索。

