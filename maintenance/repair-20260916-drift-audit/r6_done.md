# 施工 R6：完成

按 `maintenance/repair-20260916-drift-audit/workorder_r6.md` v1 的 §0–§3 完成。D1 仅在第 155 行将指定例外替换为 `一律剔除。`；净减 55 B，8 项指定守卫全部通过。

## 0. §0.1 内容基线与锚点

施工前 HEAD：`f39b2809569e4704c4ee6b7bb970b52a0d6d84ea`。工单内容基线：`03e7c65b3963979586a1b2dcd80680c91a0f5672`。以下两条命令均已实际运行，退出码均为 0，原始 stdout 均为空（代码块中命令之后无输出）：

```console
$ git status --short
```

```console
$ git diff --stat 03e7c65 HEAD -- SKILL.md references scripts commands-staging VERSION
```

施工前按工单先运行 `grep -n -F`；仅返回 1 处，行号为 155：

```console
$ grep -n -F '默认剔除，仅当"同 48h 窗 + 行为指纹一致"才升中等。' references/playbook-entity-cluster-methods.md
155:- **注资证据分级（gas/资金同源边的强度标尺）**：**私人 gas 钱包**（本体 <20 笔交易）供养多个母钱包＝强证据；**同窗批次注资**（多地址在同一 ~90 分钟窗集中入金、多波重复）＝中等证据；**公用桥 solver / CEX 热钱包同源**默认剔除，仅当"同 48h 窗 + 行为指纹一致"才升中等。报告按分级分开计数/画图，强证据簇与同窗批次簇不混在一个数里（外部 GME 考古，07）
```

锚点唯一性、行号、原文和逐字替换均通过程序断言；修改后整文件与 HEAD 版本仅相差该一次替换。

## 1. D1 改前 → 改后 diff

```console
$ git diff --unified=0 -- references/playbook-entity-cluster-methods.md
diff --git a/references/playbook-entity-cluster-methods.md b/references/playbook-entity-cluster-methods.md
index 29a1d1b..bac01e0 100644
--- a/references/playbook-entity-cluster-methods.md
+++ b/references/playbook-entity-cluster-methods.md
@@ -155 +155 @@ tier=exclude 设施与 locker 禁作合并边，被拦地址写入 clusters.json
-- **注资证据分级（gas/资金同源边的强度标尺）**：**私人 gas 钱包**（本体 <20 笔交易）供养多个母钱包＝强证据；**同窗批次注资**（多地址在同一 ~90 分钟窗集中入金、多波重复）＝中等证据；**公用桥 solver / CEX 热钱包同源**默认剔除，仅当"同 48h 窗 + 行为指纹一致"才升中等。报告按分级分开计数/画图，强证据簇与同窗批次簇不混在一个数里（外部 GME 考古，07）
+- **注资证据分级（gas/资金同源边的强度标尺）**：**私人 gas 钱包**（本体 <20 笔交易）供养多个母钱包＝强证据；**同窗批次注资**（多地址在同一 ~90 分钟窗集中入金、多波重复）＝中等证据；**公用桥 solver / CEX 热钱包同源**一律剔除。报告按分级分开计数/画图，强证据簇与同窗批次簇不混在一个数里（外部 GME 考古，07）
```

公共来源改为一律剔除，与同文第 117 行、第 247 行一致；同窗批次注资及该行其他文字保持原样。

## 2. §1.1 字节实测

| 范围 | 改前 B | 改后 B | 差值 B | 要求 |
| --- | ---: | ---: | ---: | --- |
| `SKILL.md` | 8021 | 8021 | 0 | = 8021 |
| `commands-staging/*.md` | 8798 | 8798 | 0 | = 8798 |
| references 三组 glob 合计 | 929888 | 929833 | -55 | ≤ 929833 |

三组 glob 为 `references/*.md`、`references/labels/*.md`、`references/casebook/*.md`，按匹配文件的 `stat().st_size` 求和。`references/attic.md` 只计大小，未主动读取内容。旧片段 UTF-8 为 70 B，新片段为 15 B；目标文件从 48061 B 变为 48006 B。

改前测量及断言原始 stdout（退出码 0）：

```text
references globs: references/*.md, references/labels/*.md, references/casebook/*.md
SKILL.md: 8021 B
commands-staging/*.md: 8798 B
references_three_globs: 929888 B
target before: 48061 B
old anchor: 70 B
new anchor: 15 B
replacement delta: -55 B
pre-edit byte/anchor/new-report checks: PASS
```

改后精确替换核验及测量原始 stdout（退出码 0）：

```text
D1 exact replacement at line 155: PASS
target before: 48061 B
target after: 48006 B
target delta: -55 B
SKILL.md: 8021 B
commands-staging/*.md: 8798 B
references_three_globs: 929833 B
section 1.1 bytes: PASS
```

## 3. §1.2 守卫原始输出

以下命令均在仓库根目录离线运行，使用原有脚本；`PYTHONDONTWRITEBYTECODE=1` 用于避免生成字节码缓存。各项退出码均为 0。

### 1. `docs_lint.py`

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py
PASS: 45 个文档，引用无断链、粗体配对完整
```

退出码：`0`。

### 2. `docs_lint.py --all`

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py --all
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

退出码：`0`。

### 3. `casebook_lint.py`

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/casebook_lint.py
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

退出码：`0`。

### 4. `changelog_lint.py`

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/changelog_lint.py
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 73 条 + 归档 139 条
```

退出码：`0`。

### 5. `test_contract_routes.py`

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_contract_routes.py
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

退出码：`0`。

### 6. `test_sixlens_docs.py`

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_sixlens_docs.py
PASS: 六视角批⑤大小口径与 archive 路由
```

退出码：`0`。

### 7. `test_g3_docs_guards.py`

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_g3_docs_guards.py
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

退出码：`0`。

### 8. `test_version_consistency.py`

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_version_consistency.py
PASS: M-03 version metadata consistent at 7.1.1
```

退出码：`0`。

## 4. git diff --stat 与范围

```console
$ git diff --stat
 references/playbook-entity-cluster-methods.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

`git diff --stat` 默认不显示未跟踪文件；新建的 `maintenance/repair-20260916-drift-audit/r6_done.md` 属另一项白名单文件，保持未暂存。施工改动仅限上述两项白名单。

`git diff --check` 已实际运行，退出码 0、stdout 为空。

报告落盘后的 `git status --short` 原始输出（退出码 0）：

```console
$ git status --short
 M references/playbook-entity-cluster-methods.md
?? maintenance/repair-20260916-drift-audit/r6_done.md
```

报告落盘后再次核对 `git diff --stat`，与上列一致；`git diff --check` 仍退出 0、stdout 为空，HEAD 与施工前相同。

## 5. 差异与停工点

施工差异：无。停工点：无。净减 -55 B 与工单逐字计算一致，没有 needle 碰撞；所有指定守卫通过。

只修改 D1 指定片段并新建本报告；未修改脚本、`scripts/tests/contract_manifest.json` 或其他文件，未 commit、push，未部署 `~/.claude/commands/`。

## 6. 禁读披露

会话初始化时系统已自动提供 memory 摘要，首次施工说明已如实披露。施工期间未主动读取 `~/.codex/` 下任何文件，也未主动读取本仓库 `archive/`、`blind-reviews/`、`.staging_*` 或 `references/attic.md` 的内容；attic 仅按 §1.1 统计大小。守卫脚本原样运行时的文档遍历属于工单明确允许的被测代码既有行为。

---
## 附：调度方验收（Fable）

新文本命中 1、旧文本"才升中等"全库 0；亲跑九项守卫全 PASS；`git diff --stat` 仅一个白名单文件；references 实测 929833 B = 基线 929888 − 55，与工单 §1.1 一致。
