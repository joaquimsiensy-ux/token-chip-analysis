# 施工 R9：完成

按 `maintenance/repair-20260919-drift-audit2/workorder_r9.md` v2 的 §0–§3 完成三处整行替换。施工 HEAD：`e615763a73028a9fd88c8d8fb938a7bcf9122377`；内容基线：`bf20266`。九项守卫全部通过，references 净变动 -23 B。

## §0.1 开工基线校验

以下命令在任何修改前实际运行，保留其原始输出。开工工作区干净，指定内容路径与 `bf20266` 无差异。

`git status --short`；退出码：0。

原始输出为空。

`git rev-parse HEAD`；退出码：0。

```text
e615763a73028a9fd88c8d8fb938a7bcf9122377
```

`git diff --stat bf20266 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md`；退出码：0。

原始输出为空。

## 锚与行号核验

三处均实际使用 `grep -n -F -x` 核验，整行各命中一次，行号分别为 117、214、225。以下为核验原始输出；字节统计仅调用文件大小接口，`references/attic.md` 未读取内容。

```text
$ grep -n -F -x -- '3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`（含宏加 `--facts facts.json`）——这是合法重编译但带显式水印。若要维持正式身份，必须把 `appendix.json` 加入 `a4_gate.py finalize --seal-files ...` 重新封口，再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。' references/monitoring-package.md
117:3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`（含宏加 `--facts facts.json`）——这是合法重编译但带显式水印。若要维持正式身份，必须把 `appendix.json` 加入 `a4_gate.py finalize --seal-files ...` 重新封口，再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
D1: exactly one anchor, line 117; UTF-8 delta +81 B
$ grep -n -F -x -- '- 免费 key 仅 chainid=1 可用；跨链代币的 ETH 侧全量转账、金库地址 txlist/txlistinternal（vesting 释放追踪）都走它。（OPN，07）' references/data-pipeline-evm-channels.md
214:- 免费 key 仅 chainid=1 可用；跨链代币的 ETH 侧全量转账、金库地址 txlist/txlistinternal（vesting 释放追踪）都走它。（OPN，07）
D2: exactly one anchor, line 214; UTF-8 delta -34 B
$ grep -n -F -x -- '0xa86309988947559b6e72ef716c5058f479386c0f,eth,Coinbase Prime Custody Gas Supplier 1,cex,exclude,addressbook,2026-07-25,标签库多源 + 创世资金来自 Coinbase 4；Prime 托管分仓 gas 滴灌锚,,,,,,,,E-CEX,Coinbase Prime Custody Gas Supplier 1 (ETH)；标签库多源＋创世资金来自 Coinbase 4；**机构托管分仓群识别锚**——分仓群 gas 全由它精确滴灌＝Prime 托管实锤（指纹三件套见 playbook-entity-cluster-methods「CEX 提币囤仓反转通道」条）；⚠托管≠自营，Prime 托管是客户/机构资产，风险语义与所自营仓不同（SPX6900 分析核验 2026-07-25）' references/address-book.md
225:0xa86309988947559b6e72ef716c5058f479386c0f,eth,Coinbase Prime Custody Gas Supplier 1,cex,exclude,addressbook,2026-07-25,标签库多源 + 创世资金来自 Coinbase 4；Prime 托管分仓 gas 滴灌锚,,,,,,,,E-CEX,Coinbase Prime Custody Gas Supplier 1 (ETH)；标签库多源＋创世资金来自 Coinbase 4；**机构托管分仓群识别锚**——分仓群 gas 全由它精确滴灌＝Prime 托管实锤（指纹三件套见 playbook-entity-cluster-methods「CEX 提币囤仓反转通道」条）；⚠托管≠自营，Prime 托管是客户/机构资产，风险语义与所自营仓不同（SPX6900 分析核验 2026-07-25）
D3: exactly one anchor, line 225; UTF-8 delta -70 B
SKILL.md = 8021 B
commands-staging/*.md = 8789 B
references/*.md references/casebook/*.md references/labels/*.md = 929154 B
PASS: all three anchors and baseline byte counts match; planned total delta -23 B.
```

## ① 逐条改前 → 改后 diff

### D1

`git diff --unified=0 -- references/monitoring-package.md`；退出码：0。

```diff
diff --git a/references/monitoring-package.md b/references/monitoring-package.md
index cf0b255..ec80845 100644
--- a/references/monitoring-package.md
+++ b/references/monitoring-package.md
@@ -117 +117 @@ HTML 内嵌后监控脚本提取方式已写在 build_html.py docstring。**JSON
-3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`（含宏加 `--facts facts.json`）——这是合法重编译但带显式水印。若要维持正式身份，必须把 `appendix.json` 加入 `a4_gate.py finalize --seal-files ...` 重新封口，再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
+3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`（含宏加 `--facts facts.json`）——这是合法重编译但带显式水印。若要维持正式身份，按原流程重封 A4（新分析用 `stage2_closeout.py reseal --from a4 ...`），`--seal-files` 含原 extras 及 `appendix.json`，重走 A5（含 report seal），再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
```

### D2

`git diff --unified=0 -- references/data-pipeline-evm-channels.md`；退出码：0。

```diff
diff --git a/references/data-pipeline-evm-channels.md b/references/data-pipeline-evm-channels.md
index 7f8f04e..7621627 100644
--- a/references/data-pipeline-evm-channels.md
+++ b/references/data-pipeline-evm-channels.md
@@ -214 +214 @@ size 与 SHA-256；全部通过后才原子将 v2/v3/pre-schema done 升为
-- 免费 key 仅 chainid=1 可用；跨链代币的 ETH 侧全量转账、金库地址 txlist/txlistinternal（vesting 释放追踪）都走它。（OPN，07）
+- 跨链代币的 ETH 侧全量转账、金库地址 txlist/txlistinternal（vesting 释放追踪）都走它。（OPN，07）
```

### D3

`git diff --unified=0 -- references/address-book.md`；退出码：0。

```diff
diff --git a/references/address-book.md b/references/address-book.md
index ef181ad..1a1fb3e 100644
--- a/references/address-book.md
+++ b/references/address-book.md
@@ -225 +225 @@ Ay9wnuZCRTceZJuRpGZnuwYZuWdsviM4cMiCwFoSQiPH,sol,冷静哥（中文车头/打新
-0xa86309988947559b6e72ef716c5058f479386c0f,eth,Coinbase Prime Custody Gas Supplier 1,cex,exclude,addressbook,2026-07-25,标签库多源 + 创世资金来自 Coinbase 4；Prime 托管分仓 gas 滴灌锚,,,,,,,,E-CEX,Coinbase Prime Custody Gas Supplier 1 (ETH)；标签库多源＋创世资金来自 Coinbase 4；**机构托管分仓群识别锚**——分仓群 gas 全由它精确滴灌＝Prime 托管实锤（指纹三件套见 playbook-entity-cluster-methods「CEX 提币囤仓反转通道」条）；⚠托管≠自营，Prime 托管是客户/机构资产，风险语义与所自营仓不同（SPX6900 分析核验 2026-07-25）
+0xa86309988947559b6e72ef716c5058f479386c0f,eth,Coinbase Prime Custody Gas Supplier 1,cex,exclude,addressbook,2026-07-25,标签库多源 + 创世资金来自 Coinbase 4；Prime 托管分仓 gas 滴灌锚,,,,,,,,E-CEX,Coinbase Prime Custody Gas Supplier 1 (ETH)；标签库多源＋创世资金来自 Coinbase 4；**机构托管分仓群识别锚**——分仓群 gas 全由它精确滴灌＝Prime 托管实锤（见 casebook C-07）；⚠托管≠自营，Prime 托管是客户/机构资产，风险语义与所自营仓不同（SPX6900 分析核验 2026-07-25）
```

## ② §1.1 字节实测

| 范围 | 修改前（B） | 修改后（B） | 要求（B） |
| --- | ---: | ---: | ---: |
| `SKILL.md` | 8021 | 8021 | 8021 |
| `commands-staging/*.md` 合计 | 8789 | 8789 | 8789 |
| `references/*.md references/casebook/*.md references/labels/*.md` 合计 | 929154 | 929131 | 929131 |

D1 +81 B、D2 -34 B、D3 -70 B，合计 -23 B。以 UTF-8 字节逐文件比对当前文件与施工 HEAD：每个文件均严格等于仅替换工单指定整行后的结果，其他字节不变。

校验原始输出：

```text
D1: PASS; only line 117 replaced exactly as specified; +81 B
D2: PASS; only line 214 replaced exactly as specified; -34 B
D3: PASS; only line 225 replaced exactly as specified; -70 B
SKILL.md = 8021 B
commands-staging/*.md = 8789 B
references/*.md references/casebook/*.md references/labels/*.md = 929131 B
PASS: exact replacements, byte totals, git diff --check, and changed-path whitelist.
```

## ③ §1.2 守卫原始输出

九项命令均离线执行，退出码全部为 0。运行环境设置 `PYTHONDONTWRITEBYTECODE=1`，避免生成字节码；守卫脚本及参数未修改。以下逐项保留原始输出。

`python3 scripts/tests/docs_lint.py`；退出码：0。

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

`python3 scripts/tests/docs_lint.py --all`；退出码：0。

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

`python3 scripts/tests/casebook_lint.py`；退出码：0。

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

`python3 scripts/tests/changelog_lint.py`；退出码：0。

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

`python3 scripts/tests/test_contract_routes.py`；退出码：0。

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

`python3 scripts/tests/test_sixlens_docs.py`；退出码：0。

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

`python3 scripts/tests/test_g3_docs_guards.py`；退出码：0。

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

`python3 scripts/tests/test_version_consistency.py`；退出码：0。

```text
PASS: M-03 version metadata consistent at 9.0.1
```

`python3 scripts/tests/test_commands_deploy_sync.py`；退出码：0。

```text
PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
```

## ④ git diff --stat

`git diff --stat`；退出码：0。

```text
 references/address-book.md               | 2 +-
 references/data-pipeline-evm-channels.md | 2 +-
 references/monitoring-package.md         | 2 +-
 3 files changed, 3 insertions(+), 3 deletions(-)
```

新建完成报告 `maintenance/repair-20260919-drift-audit2/r9_done.md` 保持未跟踪状态，故不计入 `git diff --stat`；未执行暂存操作。三份修改文档及本报告均属于 §0.3 白名单。

## ⑤ 差异 / 停工点

无工单差异，无停工点。三处锚均唯一且行号吻合，替换后的文本与工单逐字一致；D1 后半句“再按原工作流用 `build_html.py …`”保持原文。全部硬约束已满足，`git diff --check` 通过。

未 commit、push 或部署；未修改 `scripts/`、`commands-staging/`、`CHANGELOG.md` 或两份 manifest。除白名单三份文档与本报告外，无其他工作区变更。

## ⑥ 禁读披露

本轮未读取 `~/.codex/` 下任何文件，包括 memories；未启动插件文件搜索。未主动读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/` 或 `references/attic.md` 的内容；`attic.md` 仅以文件大小计入 §1.1 统计。`maintenance/` 下仅读取本工程目录 `maintenance/repair-20260919-drift-audit2/`。

按工单授权，九项守卫保持既有行为运行；守卫自身的文档遍历属于被测代码行为。全部施工离线完成，未使用外部网络或 API。

