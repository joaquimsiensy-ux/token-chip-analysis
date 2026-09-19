# 施工 R1：完成

按 `maintenance/repair-20260919-drift-audit2/workorder_r1.md` v2 的 §0–§3 完成 D1–D9。5 个白名单正文文件仅发生 9 处指定替换，另新建本报告。8 项必过守卫全部通过；部署同步守卫按工单预期 FAIL，仅 `token-analyze-2.md` 与已部署版不一致。

- 开工时间（UTC）：2026-09-19 06:05:22 UTC。
- 施工 HEAD：`198abf60bf65b10202066628b9bdad7701267536`。
- 内容基线：`3942c23`；开工工作区干净，指定内容基线差异为空。
- 全程离线；未 commit、push 或部署，未修改 `scripts/`、`contract_manifest.json`、`invariant_manifest.json`。

## 1. §0.1 开工检查原始输出

以下命令均实际运行，空输出以空代码块保留。

```sh
git status --short
```

退出码：0；原始输出为空。

```text
```

```sh
git rev-parse HEAD
```

退出码：0；原始输出如下。

```text
198abf60bf65b10202066628b9bdad7701267536
```

```sh
git diff --stat 3942c23 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md
```

退出码：0；原始输出为空。

```text
```

## 2. D1–D9 逐条改前 → 改后 diff

施工前每处均实际运行 `grep -n -F -- <锚> <文件>`：匹配恰 1 处且行号与工单一致。以下 diff 展示指定替换片段；整文件字节比对确认没有锚外改动。

### D1 — `references/independent-audit-protocol.md:162`

锚核验：唯一 1 处，行号 162。

```diff
-wallet_self_held_raw == Σ position.amount_raw
+wallet_self_held_raw == Σ strict 成员的 position.amount_raw
```

### D2 — `references/report-template.md:203`

锚核验：唯一 1 处，行号 203。

```diff
-`facts.json` 唯一拥有 entity_id/label/成员/current_raw/peak_raw；`state_source.json` 只承载它没有的分析时点、实体 type/status、逐址快照余额、vault 与 provenance。
+`facts.json` 由 `facts_gate.py build` 生成（人工声明取自 `state_source.facts_inputs`）；`state_source.json` 另承载分析时点、实体 type/status、逐址快照余额、vault 与 provenance。
```

### D3 — `references/report-template.md:278`

锚核验：唯一 1 处，行号 278。

```diff
-双源都无该币（Robinhood 链类）exit 3 回退人工对 Dexscreener 图
+exit 3（ALL_SKIP）须换源重跑，−2 收口只接 PASS/WARN
```

### D4 — `references/report-template.md:215`

锚核验：唯一 1 处，行号 215。

```diff
-`{{e.peak_share}}` 只代表日末序列峰值；日内事件占比禁用宏，
+`{{e.peak_share}}` 代表 facts 绑定的峰值，粒度按来源标明；未绑定该峰值的日内事件占比，
```

### D5 — `CHANGELOG.md:117`

锚核验：唯一 1 处，行号 117。

```diff
-2，均可选）
+2）
```

### D6 — `references/report-template.md:222`

锚核验：唯一 1 处，行号 222。

```diff
-**每次 check（PASS/FAIL、formal/exploration）都落 `figure2_check_receipt.json` 留痕收据**
+**终值对账结果（PASS/FAIL、formal/exploration）均写 `figure2_check_receipt.json` 收据**
```

### D7 — `references/data-pipeline-evm-recon.md:136`

锚核验：唯一 1 处，行号 136。

```diff
-**今按 1% 预筛会把 0.1%–1% 区间候选不可逆滤掉**
+**须显式传 `--pct`＝上述最低枚数/总供应量，勿沿用默认 0.01（1%）**
```

### D8 — `references/report-template.md:200`

锚核验：唯一 1 处，行号 200。

```diff
-（≤500 点，重绘图 1 基线）
+（重绘图 1 基线）
```

### D9 — `commands-staging/token-analyze-2.md:16`

锚核验：唯一 1 处，行号 16。

```diff
-按 §3b.3 第⑤条自查申报
+按 §3b.3 自查申报
```

## 3. §1.1 字节实测

| 范围 | 开工实测（B） | 完工实测（B） | 净变化（B） | 工单约束 | 结果 |
| --- | ---: | ---: | ---: | --- | --- |
| `SKILL.md` | 8021 | 8021 | 0 | = 8021 | PASS |
| references 三组 glob | 930076 | 930145 | +69 | ≤ 930160 | PASS，余 15 B |
| `commands-staging/*.md` | 8798 | 8789 | −9 | = 8789 | PASS |

references 按 `references/*.md references/casebook/*.md references/labels/*.md` 取文件并去重，共 42 个；同时核查这三个目录的 `*.bak_*`，本次无匹配，含备份口径与三组 glob 合计一致。`commands-staging/*.md` 共 4 个。每个文件均实际调用 `stat -f %z` 取大小后求和；`references/attic.md` 只取大小，未读取内容。

完工字节统计原始输出：

```text
{
  "size_method": "stat -f %z, one file per invocation; no file contents read",
  "SKILL.md": 8021,
  "references_three_globs": 930145,
  "references_including_bak_files": 930145,
  "reference_file_count": 42,
  "bak_files": [],
  "bak_files_outside_three_globs": [],
  "commands-staging/*.md": 8789,
  "command_file_count": 4
}
```

## 4. §1.2 守卫原始输出

脚本及参数原样执行；统一设置 `PYTHONDONTWRITEBYTECODE=1`，避免测试生成 `__pycache__`。下列输出为各实际进程返回的完整原始输出，未删节。

### 1. `python3 scripts/tests/docs_lint.py`

```sh
python3 scripts/tests/docs_lint.py
```

退出码：0；原始输出如下。

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

### 2. `python3 scripts/tests/docs_lint.py --all`

```sh
python3 scripts/tests/docs_lint.py --all
```

退出码：0；原始输出如下。

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

### 3. `python3 scripts/tests/casebook_lint.py`

```sh
python3 scripts/tests/casebook_lint.py
```

退出码：0；原始输出如下。

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

### 4. `python3 scripts/tests/changelog_lint.py`

```sh
python3 scripts/tests/changelog_lint.py
```

退出码：0；原始输出如下。

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

### 5. `python3 scripts/tests/test_contract_routes.py`

```sh
python3 scripts/tests/test_contract_routes.py
```

退出码：0；原始输出如下。

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

### 6. `python3 scripts/tests/test_sixlens_docs.py`

```sh
python3 scripts/tests/test_sixlens_docs.py
```

退出码：0；原始输出如下。

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

### 7. `python3 scripts/tests/test_g3_docs_guards.py`

```sh
python3 scripts/tests/test_g3_docs_guards.py
```

退出码：0；原始输出如下。

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

### 8. `python3 scripts/tests/test_version_consistency.py`

```sh
python3 scripts/tests/test_version_consistency.py
```

退出码：0；原始输出如下。

```text
PASS: M-03 version metadata consistent at 9.0.1
```

### 9. `python3 scripts/tests/test_commands_deploy_sync.py`（预期 FAIL）

```sh
python3 scripts/tests/test_commands_deploy_sync.py
```

退出码：1；原始输出如下。

```text
- SHA-256 不一致：token-analyze-2.md staging=2943d2a1d35386d217a0bf2bf7cb01366c0fee45209fbdeab79a12b69b3ffe97 deployed=a3ba9220d5a3a25730b8dd0d0796423c83cb253f17a9f72ce14d8d56131f4584
FAIL: commands-staging 与已部署命令不一致
```

部署同步检查失败仅涉及工单 D9 修改的 `token-analyze-2.md`，符合 §1.2 预期，不是停工条件；部署由 Fable 完成后复验，本次未部署。

## 5. 差异范围与完整性核验

实际运行 `git diff --stat` 的原始输出：

```text
 CHANGELOG.md                             |  2 +-
 commands-staging/token-analyze-2.md      |  2 +-
 references/data-pipeline-evm-recon.md    |  2 +-
 references/independent-audit-protocol.md |  2 +-
 references/report-template.md            | 10 +++++-----
 5 files changed, 9 insertions(+), 9 deletions(-)
```

该命令只统计 tracked 差异；新建的本报告保持 untracked，未暂存。全部写入路径均属于 §0.3 白名单。

```sh
git diff --check
```

退出码：0；原始输出为空。

```text
```

逐文件读取施工 HEAD 中的原文，只应用工单替换并与当前文件逐字节比较，同时核对差异文件集合及暂存区。核验原始输出：

```text
PASS: CHANGELOG.md — only D5
PASS: commands-staging/token-analyze-2.md — only D9
PASS: references/data-pipeline-evm-recon.md — only D7
PASS: references/independent-audit-protocol.md — only D1
PASS: references/report-template.md — only D2, D3, D4, D6, D8
PASS: exactly 9 specified replacements in 5 whitelisted files; all bytes outside replacements unchanged
PASS: scripts, SKILL.md, VERSION and both manifests unchanged; no staged changes
```

## 6. 差异／停工点

- 无停工点，无工单外修改；9 处锚均唯一且行号正确。
- references 实测净增 +69 B，与 v2 模拟一致；三项字节约束全部满足。
- 唯一非零退出是工单明确预期的部署同步 FAIL，原始输出已完整保留。
- 未修改版本、脚本或两份 manifest；未 commit、push、部署或删除文件。

## 7. 禁读披露

- 本会话未读取 `~/.codex/` 下任何文件，也未读取其中 memories；未进行插件启动搜索。
- 未直接读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/` 的内容。
- `references/attic.md` 仅通过 `stat -f %z` 统计大小，未读取内容。
- `maintenance/` 下仅读取本工程目录中的工单并新建本报告，未读取其他工程目录。
- 守卫脚本自行遍历文档属于 §0.2 与用户明确允许的既有行为；脚本未改动，按要求执行。

