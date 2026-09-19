# 盲审 R5a 提示词：token-chip-analysis v9.0.1 口径漂移与文档-代码不符审计（只读，全范围路）

本轮是第五轮。前四轮报告 `maintenance/repair-20260919-drift-audit2/blind_r{1,2,3,4}{a,b}_report.md`（去重后 9＋3＋3＋4 条）已由工单 `workorder_r1.md`（v2）、`workorder_r2.md`（v2）、`workorder_r3.md`（v2）、`workorder_r4.md` 施工落地于当前 HEAD（完成报告 `r1_done.md`…`r4_done.md`）。**前四轮已报并已修的条目不必重报**；请找前四轮没发现的新问题，以及 R1–R4 修复本身是否引入了新的不一致（若有，明确标"Rn 修复引入"）。若确实找不到，首行写 `# 盲审 R5a：0 条发现` 并给出覆盖声明——不要为了凑数把范围外问题或措辞偏好写成漂移。前四轮已覆盖的重点：report-template、independent-audit-protocol、evm-recon/channels/sources、evidence-wording、analyze-workflow、scan-schemas 的 SQD 段、research-workflows 外部路、labels/README、robinhood-channels。本轮请做**全量兜底扫**：对每份必审文档逐一过一遍（不限方向），特别是前四轮尚未点名的 `context-discipline.md`、`analysis-playbook.md`、`data-pipeline-evm.md`/`data-pipeline-solana.md` 总册、`data-pipeline-solana-scan.md`、`playbook-supply-recon.md`、`lp-fee-accounting.md`、`monitoring-package.md`、`retrospective.md`、`maintenance-review-repair.md`、`environment.md`、`casebook/*`、`token-analyze*.md`（commands-staging）、SKILL.md 本身。

## 0. 纪律（逐条约束你这个审查者，不约束被审代码的既有行为）
1. **禁读 `~/.codex/` 下任何文件**（插件启动搜索若已读过 memories，如实披露一次，之后不再读）。禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md` 的内容（attic.md 只允许核对 SKILL.md 对它的"禁读身份"描述是否属实，不读其正文）；`maintenance/` 下只允许读本工程目录 `maintenance/repair-20260919-drift-audit2/`（含 R1 报告、工单、r1_done），以及上一轮工程 `maintenance/repair-20260916-drift-audit/code_change_pending.md`（已裁决台账，其 D1 wave_scan 浮点阈值已由用户裁决登记为文档已知例外，不必重报）。
2. 本任务**只读**：不修改、不新建任何文件，不 commit。全程离线，不访问网络。
3. 报告全文**打印到 stdout**（只读沙箱写不了文件）。首行固定格式：`# 盲审 R5a：N 条发现`（N 为整数，0 也要写）。
4. 每条发现都必须有你**亲自 grep/读文件实证**的两侧原文引句与行号，并附可复现命令；禁止凭印象或推断报漂移。拿不准的条目放进末尾"待确认"段，不计入 N。
5. 审查基线：`git rev-parse HEAD` 的输出写进报告；审查前后 `git status --short` 必须为空并写进报告。

## 1. 任务
被审对象：本仓库（main，VERSION=9.0.1）的**现行文档**与**现行代码**。目标是找出两类问题：

- **A 类·口径漂移**：同一概念在不同文档之间、或同一文档不同位置，说法不一致。典型维度：阶段名与阶段编号（A0–A6、−1/−2/−3）、门禁编号与含义（EF-1/2/3、EF-3A/B/C、EF-3C-P1..P4、ET-1/2、G8–G11、accounting_gate 0/1/2）、"四查/五查"的查数与名称、schema/协议版本号（如 reconcile v4、wave v5、flow v3、wrapper v3、a5-report-seal/v3、anchor-plan v3、done v4、facts-provenance/v1、block-precision-followup/v1、observation bundle v2）、产物文件名（*.json/*.md/*.html）、命令名与子命令名、阈值与数字（如 10bps、<30 万 tokens、峰值 <0.01% 供应）、链支持档位（formal/exploration）、角色分工（Fable/Opus/codex 各段谁跑）、章节引用是否真实存在。
- **B 类·文档与代码不符**：文档描述的脚本名、子命令、CLI 参数、输入/输出字段、产物文件名、退出码、阈值、门禁语义，在 `scripts/` 的现行代码里**不存在**、**名字不同**、**语义相反**或**默认值不同**。只收"文档承诺的机器行为代码不成立/相矛盾"；**不收**"代码有而文档没提"的补写建议（本工程原则是不增加 skill 上下文）。

**不审**（即使看到也不要报）：结构与路由设计、门禁有效性、复杂度与可维护性、fail-closed 纪律、Python 代码质量、上下文预算。

## 2. 范围
必审文档：`SKILL.md`、`references/*.md`（除 attic.md 与 *.bak_* 备份件）、`references/casebook/*.md`、`references/labels/README.md`、`references/labels/MAINTENANCE.md`、`commands-staging/*.md`。
`CHANGELOG.md` 只审"现行规则型"文字（文件头版本规则段、活跃窗口索引里 7.2.0–9.0.1 条目对当前行为的描述）；历史条目描述当时版本状态，不算漂移。
对照代码：`scripts/**`（含 `scripts/tests/`），`agents/openai.yaml`，`pyproject.toml`。

## 3. 已知基线（请找这些守卫抓不到的东西）
以下 9 项机器守卫在 HEAD 已全 PASS，不必重复报它们能抓的断链/粗体/版本号/部署同步类问题：
`docs_lint.py`（含 --all）、`casebook_lint.py`、`changelog_lint.py`、`test_version_consistency.py`、`test_g3_docs_guards.py`、`test_sixlens_docs.py`、`test_commands_deploy_sync.py`、`test_contract_routes.py`。
你可以自行复跑它们确认，但报告里不要复述它们的 PASS 输出。

## 4. 建议方法（可自行调整，但覆盖声明必须写）
1. 先从 SKILL.md 与 `analyze-workflow.md`、`split-run.md` 抽出术语表：阶段/门禁/契约编号/schema 版本/脚本名/子命令名/产物文件名/阈值。
2. 对术语表每一项在全部必审文档里 `grep -n`，比对说法是否一致（A 类）。
3. 对每个被文档点名的脚本/子命令/参数/字段/产物名，在 `scripts/` 里 `grep -n` 核对存在性与语义（B 类）；CLI 参数以 argparse 定义为准，子命令以 `add_parser`/分派表为准，产物名以 `open(`/`write_text`/路径常量为准。
4. 对每条候选都要做"反向验证"：确认不是同一概念的合法别名（如链名 `sol`/`solana` 已有注册表归一）、不是历史条目、不是被明确标注"exploration/legacy"的分档差异。
5. 特别提示：上一轮同类审计（2026-09-16，v7.1.3 收官）之后，仓库经 7.2.0→9.0.1 六个修复工程，代码大量变更而 references/SKILL/commands 几乎零改动。本路仍按全范围术语表法审，但对 7.2.0 之后出现的字段/闸/schema 与文档旧描述的冲突要格外留心。

## 5. 输出格式
```
# 盲审 R5a：N 条发现
审查基线：<HEAD sha>；git status 前/后：空/空
覆盖声明：审过的文档清单（逐文件）；术语表条目数；grep 策略概述

## 发现（按严重度排序）
### D1 — <blocker|minor|nit> — <A 类|B 类> — 一句话标题
- 位置甲：<path:line> 原文「…」
- 位置乙：<path:line> 原文「…」（B 类时乙侧为代码）
- 矛盾点：一句话说清为什么不一致，以及执行者会被误导做什么
- 修法建议：优先级 删除>修改>新增；只改文本；若你认为必须改代码，单独标 **[需改代码]** 并写原因
- 复现：<grep/python 命令>

## 待确认（不计入 N）
…

## 汇总表
| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
```
严重度定义：blocker＝会让执行者在正式路径上做错事或跑不通；minor＝不一致但当前不致错；nit＝措辞/编号不整齐。
