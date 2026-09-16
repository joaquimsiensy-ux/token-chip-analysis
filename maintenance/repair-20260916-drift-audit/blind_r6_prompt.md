# 盲审 R6 提示词：token-chip-analysis 口径漂移与文档-代码不符审计（只读，第六轮）

本轮是第六轮。前五轮报告在 `maintenance/repair-20260916-drift-audit/blind_r1_report.md`…`blind_r5_report.md`，消化工单 `workorder_r1.md`（v3）、`workorder_r2.md`（v2）、`workorder_r3.md`（v2）、`workorder_r4.md`（v1）、`workorder_r5.md`（v1）均已施工落地于当前 HEAD。**已在 R1–R5 报告或工单中出现并已修复的条目不必重报**；请找前五轮没发现的新问题，以及 R1–R5 修复本身是否引入了新的不一致（若有，明确标"Rn 修复引入"）。若确实找不到，首行写 `# 盲审 R6：0 条发现` 并给出覆盖声明——不要为了凑数把范围外问题（结构/门禁有效性/代码质量/预算等）或措辞偏好写成漂移。`code_change_pending.md` 记录的 D1、D2、D3 属已知待决，不必重报。

## 0. 纪律（逐条约束你这个审查者，不约束被审代码的既有行为）
1. **禁读 `~/.codex/` 下任何文件**（插件启动搜索若已读过 memories，如实披露一次，之后不再读）。禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md` 的内容（attic.md 只允许核对 SKILL.md 对它的"禁读身份"描述是否属实，不读其正文）；`maintenance/` 下只允许读本工程目录 `maintenance/repair-20260916-drift-audit/` 的文件。
2. 本任务**只读**：不修改、不新建任何文件，不 commit。全程离线。
3. 报告全文**打印到 stdout**。首行固定格式：`# 盲审 R6：N 条发现`（N 为整数，0 也要写）。
4. 每条发现都必须有你**亲自 grep/读文件实证**的两侧原文引句与行号，并附可复现命令；禁止凭印象或推断报漂移。拿不准的条目放进末尾"待确认"段，不计入 N。
5. 审查基线：`git rev-parse HEAD` 写进报告；审查前后 `git status --short` 必须为空并写进报告。

## 1. 任务（范围与 R1 完全相同，只有两类）
- **A 类·口径漂移**：同一概念在不同文档之间、或同一文档不同位置，说法不一致（阶段/门禁编号、查数、schema 版本、产物名、命令/子命令名、阈值、链支持档位、角色分工、证据强度上限、章节引用是否真实存在）。
- **B 类·文档与代码不符**：文档描述的脚本名、子命令、CLI 参数、字段、产物名、退出码、阈值、门禁语义，在 `scripts/` 现行代码里不存在、名字不同、语义相反或默认值不同。只收"文档承诺的机器行为代码不成立/相矛盾"；**不收**"代码有而文档没提"。
**不审**：结构与路由设计、门禁有效性、复杂度与可维护性、fail-closed 纪律、Python 代码质量、上下文预算——这些即使看到也不要报。

## 2. 范围
必审文档：`SKILL.md`、`references/*.md`（除 attic.md）、`references/casebook/*.md`、`references/labels/README.md`、`references/labels/MAINTENANCE.md`、`commands-staging/*.md`；`CHANGELOG.md` 只审现行规则型文字。对照代码：`scripts/**`、`agents/openai.yaml`、`pyproject.toml`。
前两轮覆盖较薄的方向（建议重点）：`address-book.md` 地址/程序 ID 与 labels CSV 对照、`environment.md` 依赖/命令与 pyproject/env_check 对照、`retrospective.md` 与 `maintenance-review-repair.md` 流程命令与脚本对照、`playbook-state-anomaly.md`/`playbook-entity-cluster-cost.md`/`economic-control-accounting.md` 与 tiering/methods 的阈值与术语互引、`casebook/*` 判例与正式方法册的规则一致性、CHANGELOG 现行规则段与 retrospective 版本号约定；此前建议方向：`data-pipeline-robinhood-*.md`、`monitoring-package.md`、`lp-fee-accounting.md`、`research-workflows.md`、`maintenance-review-repair.md`、`retrospective.md`、`environment.md`、`address-book.md`、`playbook-state-anomaly.md`、`playbook-entity-cluster-cost.md`、`economic-control-accounting.md`、`labels/README.md` 与 `scripts/labels/*`、`commands-staging/*.md` 与 `scripts/report/*` 的命令/子命令/参数对照、`scan-schemas.md` 各 schema 版本号与生产者 `SCHEMA =` 常量对照。

## 3. 已知基线
9 项机器守卫在 HEAD 已全 PASS，不必复述：`docs_lint.py`（含 --all）、`casebook_lint.py`、`changelog_lint.py`、`test_version_consistency.py`、`test_g3_docs_guards.py`、`test_sixlens_docs.py`、`test_commands_deploy_sync.py`、`test_contract_routes.py`。

## 4. 输出格式（同 R1）
```
# 盲审 R6：N 条发现
审查基线：<HEAD sha>；git status 前/后：空/空
覆盖声明：审过的文档清单；术语表条目数；grep 策略概述；本轮相对 R1–R5 新增的核对方向

## 发现（按严重度排序）
### D1 — <blocker|minor|nit> — <A 类|B 类> — 一句话标题
- 位置甲：<path:line> 原文「…」
- 位置乙：<path:line> 原文「…」
- 矛盾点：…
- 修法建议：删除>修改>新增；只改文本；必须改代码则标 **[需改代码]** 并写原因
- 复现：<命令>

## 待确认（不计入 N）
## 汇总表
| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
```
