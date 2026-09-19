# 施工 R7：完成

按 `maintenance/repair-20260919-drift-audit2/workorder_r7.md`（v2）执行。三处指定整行替换完成，9 项守卫全部通过，references 净变动 `0 B`，无停工点。

## 1. §0.1 内容基线校验

内容基线：`fc704de`。施工 HEAD：`d6b84f018cc4c9b44c0fa60895ba52b37c5a5a4b`；施工后 HEAD 未变。以下命令均实际运行；`git status --short` 与指定内容基线差异命令均无输出。

```console
$ git status --short
```

退出码：`0`。

```console
$ git rev-parse HEAD
d6b84f018cc4c9b44c0fa60895ba52b37c5a5a4b
```

退出码：`0`。

```console
$ git diff --stat fc704de HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md
```

退出码：`0`。

## 2. 锚点核验与逐条改前→改后 diff

修改前使用 `grep -n -F -x` 对工单代码块中的整行字面锚逐条核验，均恰好 1 处，行号分别为 117、178、119。以下为核验原始输出；命令展示中的方括号表示传给 grep 的工单完整整行锚，实际调用没有使用占位符。

```text
$ grep -n -F -x -- [workorder D1 exact whole-line anchor] references/monitoring-package.md
117:3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`——这是合法重编译但带显式水印。若要维持正式身份，必须把 `appendix.json` 加入 `a4_gate.py finalize --seal-files ...` 重新封口，再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
D1: exact anchor count=1; line=117; UTF-8 delta=+36 B
$ grep -n -F -x -- [workorder D2 exact whole-line anchor] references/data-pipeline-solana-capture.md
178:**遗留后续项**：①~~v2 整合 HyperSync 第二引擎~~ ②~~完备性验收~~（均 3.18.0 完成，验收不通过→禁用待 GA 重验）③Helius key 运行时检测（见 §13c）④SQD key 专属端点补录 ⑤实时 mint 档案（方案 4,用户暂缓）。
D2: exact anchor count=1; line=178; UTF-8 delta=-30 B
$ grep -n -F -x -- [workorder D3 exact whole-line anchor] references/data-pipeline-solana-scan.md
119:### 3a. 流水追踪的三个 Solana 特有坑
D3: exact anchor count=1; line=119; UTF-8 delta=-6 B
SKILL.md = 8021 B (expected 8021 B)
commands-staging/*.md = 8789 B (expected 8789 B)
references/*.md references/casebook/*.md references/labels/*.md = 929528 B (expected 929528 B)
Pre-edit checks: PASS
```

- D1：`references/monitoring-package.md:117`，插入 `（含宏加 --facts facts.json）`，其中参数保留工单要求的行内代码格式；实际增加 `36 B`。含宏报告加 `--facts facts.json`；未传时宏不展开且不因此 WARN；无宏老报告不强制补 facts.json。本轮仅修改指定括注。
- D2：`references/data-pipeline-solana-capture.md:178`，删除 SQD 专属端点待办，后续项由 ⑤ 改为 ④；实际减少 `30 B`。
- D3：`references/data-pipeline-solana-scan.md:119`，删除标题中的“三个”，保留中英文之间的空格；实际减少 `6 B`。

以下为实际 `git diff --unified=0` 输出：

```diff
diff --git a/references/data-pipeline-solana-capture.md b/references/data-pipeline-solana-capture.md
index 905f484..950844a 100644
--- a/references/data-pipeline-solana-capture.md
+++ b/references/data-pipeline-solana-capture.md
@@ -178 +178 @@ JSON-RPC batch + 跨地址共享 sig 缓存（`--cache-dir`,按 sig 前 2 字符
-**遗留后续项**：①~~v2 整合 HyperSync 第二引擎~~ ②~~完备性验收~~（均 3.18.0 完成，验收不通过→禁用待 GA 重验）③Helius key 运行时检测（见 §13c）④SQD key 专属端点补录 ⑤实时 mint 档案（方案 4,用户暂缓）。
+**遗留后续项**：①~~v2 整合 HyperSync 第二引擎~~ ②~~完备性验收~~（均 3.18.0 完成，验收不通过→禁用待 GA 重验）③Helius key 运行时检测（见 §13c）④实时 mint 档案（方案 4,用户暂缓）。
diff --git a/references/data-pipeline-solana-scan.md b/references/data-pipeline-solana-scan.md
index c11ff4d..28533c7 100644
--- a/references/data-pipeline-solana-scan.md
+++ b/references/data-pipeline-solana-scan.md
@@ -119 +119 @@ Solana 特有优势：program-owned PDA 让托管类型可以直接从账户归
-### 3a. 流水追踪的三个 Solana 特有坑
+### 3a. 流水追踪的 Solana 特有坑
diff --git a/references/monitoring-package.md b/references/monitoring-package.md
index e6d5244..cf0b255 100644
--- a/references/monitoring-package.md
+++ b/references/monitoring-package.md
@@ -117 +117 @@ HTML 内嵌后监控脚本提取方式已写在 build_html.py docstring。**JSON
-3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`——这是合法重编译但带显式水印。若要维持正式身份，必须把 `appendix.json` 加入 `a4_gate.py finalize --seal-files ...` 重新封口，再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
+3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`（含宏加 `--facts facts.json`）——这是合法重编译但带显式水印。若要维持正式身份，必须把 `appendix.json` 加入 `a4_gate.py finalize --seal-files ...` 重新封口，再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
```

## 3. §1.1 字节实测与整文件核对

| 统计口径 | 修改前 | 修改后 | 净变动 |
| --- | ---: | ---: | ---: |
| `SKILL.md` | 8021 B | 8021 B | 0 B |
| `commands-staging/*.md` 合计 | 8789 B | 8789 B | 0 B |
| `references/*.md references/casebook/*.md references/labels/*.md` 合计 | 929528 B | 929528 B | 0 B |

统计使用 `Path.stat().st_size`；`references/attic.md` 只计文件大小，未读取内容。三处修改合计 `+36 −30 −6 = 0 B`。

将三个当前文件分别与施工 HEAD 中对应文件按工单进行单次整行替换所得结果比较，确认其他每个字节均未变。原始核验输出：

```text
D1: PASS; exact whole-line replacement at references/monitoring-package.md:117; all other bytes unchanged; delta=+36 B
D2: PASS; exact whole-line replacement at references/data-pipeline-solana-capture.md:178; all other bytes unchanged; delta=-30 B
D3: PASS; exact whole-line replacement at references/data-pipeline-solana-scan.md:119; all other bytes unchanged; delta=-6 B
SKILL.md = 8021 B
commands-staging/*.md = 8789 B
references/*.md references/casebook/*.md references/labels/*.md = 929528 B
Net references delta: 0 B
HEAD unchanged; tracked diff exactly matches the three whitelisted documents; no staged or untracked changes before report.
```

## 4. §1.2 守卫原始输出

以下 9 项命令全部退出码为 `0`。设置 `PYTHONDONTWRITEBYTECODE=1` 仅用于避免生成字节码缓存；脚本及其参数未改动。

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py
PASS: 45 个文档，引用无断链、粗体配对完整
```

退出码：`0`。

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py --all
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

退出码：`0`。

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/casebook_lint.py
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

退出码：`0`。

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/changelog_lint.py
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

退出码：`0`。

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_contract_routes.py
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

退出码：`0`。

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_sixlens_docs.py
PASS: 六视角批⑤大小口径与 archive 路由
```

退出码：`0`。

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_g3_docs_guards.py
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

退出码：`0`。

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_version_consistency.py
PASS: M-03 version metadata consistent at 9.0.1
```

退出码：`0`。

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_commands_deploy_sync.py
PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
```

退出码：`0`。

## 5. git diff --stat 与范围核验

```console
$ git diff --stat
 references/data-pipeline-solana-capture.md | 2 +-
 references/data-pipeline-solana-scan.md    | 2 +-
 references/monitoring-package.md           | 2 +-
 3 files changed, 3 insertions(+), 3 deletions(-)
```

退出码：`0`。

```console
$ git diff --check
```

退出码：`0`。

三个已跟踪文件各仅替换 1 行。另新建本报告 `maintenance/repair-20260919-drift-audit2/r7_done.md`；新文件未暂存，因此不计入默认 `git diff --stat`。所有变更均在 §0.3 白名单内。

## 6. 差异、停工点与范围外残留

无工单偏离，无锚点或行号不符，无停工点。未修改 `scripts/`、`commands-staging/`、`CHANGELOG.md` 或两份 manifest；未 commit、push 或部署，全程离线。

按工单 §2b 登记、不修：`scripts/solana/fetch_sqd_transfers_v2.py:26`、`:1301` 的专属端点帮助文字残留留待日后升版处理；本轮未另读或修改该脚本。

## 7. 禁读披露

本轮未主动读取 `~/.codex/` 下任何文件，未进行插件启动搜索，未读取 memories。未主动读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/` 或 `references/attic.md` 的内容；attic.md 仅参与文件大小统计。`maintenance/` 下仅读取本工程目录 `maintenance/repair-20260919-drift-audit2/` 中的文件。

工单要求的守卫按原样运行，其既有文档遍历按 §0.2 的明确例外执行；未为查看禁读内容另行运行读取命令。
