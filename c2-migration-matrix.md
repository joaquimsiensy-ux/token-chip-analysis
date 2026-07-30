# c2.0 迁移矩阵（codex 侧 v4.1.0+c1.1.0 → main v6.1.1 大同步）

> 2026-07-30 定稿后执行 merge。宗旨：main 是方法学真源，codex 独有资产（三账/审计 gate/复盘判据）不丢失；"逐文件改字"式平台适配升级为 SKILL.md 适配节**通则映射**，压缩未来同步冲突面。被替换的 codex 原文不复制存档——git ref `codex@639bfd0` 即档案，下表注明文件与内容键即可考古。

## 一、v5/v6 概念变更 × codex 独有资产

| v5/v6 变更 | codex 独有资产影响点 | 处置 |
|---|---|---|
| P0/P1 分级废止（v5.0 起判级=大庄/小庄双门槛，不分级） | economic-control-accounting.md 4 处（"P0/P1 判级/候选"措辞） | 措辞迁移："P0/P1 判级"→"庄级判定（大庄/小庄门槛，tiering §6a）"；账本结构零变更 |
| 同上 | audit_release_gate.py L33 审计维度名 `whale_tier` | **保留维度名**（协议内部枚举，非判级 schema）；语义=按现行门槛体系核判级，零代码改动 |
| 同上 | independent-audit-protocol.md / lp-fee-accounting.md / agents/openai.yaml / test_audit_release_gate.py | grep 零命中，不动 |
| 四问→三问（问 4 删除） | codex 独有文件零命中（命中的全是下发文档，merge 随 main） | 无动作 |
| 狙击集团标签废止 | codex 独有文件零命中 | 无动作 |
| SKILL.md v6 薄骨架（37KB→8.6KB） | codex SKILL.md 的「Codex 运行适配」大节＋description 复核能力宣称 | 重构：main v6 为体＋适配节重挂（§六）；description 取 v6 版＋补"既有报告独立复核"能力句，去 P0/P1/狙击/四问旧词 |

## 二、16 个双改文件逐项解法

| # | 文件 | codex 侧改动性质 | 解法 |
|---|---|---|---|
| 1 | SKILL.md | 「Codex 运行适配」大节＋老骨架 | **手工重构**：main v6 体＋薄适配节（§六） |
| 2 | analysis-playbook.md | 三账分册登记行＋工序句 | 取 main＋加回一行三账分册指针（v5 口径） |
| 3 | easy-workflow.md | 禁自审改字（E4 外审路→内部自检） | **取 main**，差异升级为适配节通则 G2 |
| 4 | labels/README.md | 路径 `~/.claude`→`~/.codex` | **取 main**，通则 G1 覆盖 |
| 5 | monitoring-package.md | camp_share_series schema 修正 | 已回灌 main 6.1.1，**取 main**（冲突自动消解） |
| 6 | playbook-entity-cluster-methods.md | 路径改字＋dormant_warehouse_audit 段（纯增量）＋枢纽三段→两段（替换性分歧） | 取 main＋加回 dormant_warehouse_audit 段；**枢纽改写不收**（分歧存档：codex@639bfd0 该文件"枢纽两段处理法"段，主张删③事后卫生检查步——与 main 正式条冲突，留用户/复盘裁决是否回灌） |
| 7 | playbook-entity-cluster-tiering.md | ＋6 条复盘判据（FROGGIE/ASTEROID 案：串联边不自动确权/行为 cohort 分离/自报角色≠共同控制/日终≠事件峰值/双边界峰值/经济控制量释义） | 取 main＋判据以"codex 侧复盘判据"小节加回（P0/P1 措辞按 v5 迁移；"行为 cohort 分离"与 v5 废狙击集团同源，兼容） |
| 8 | playbook-evidence-wording.md | 措辞对照表＋7 行（三账/LP 费配套） | 取 main＋加回（纯增量，无旧词） |
| 9 | playbook-state-anomaly.md | 9c 正式条弱化重写（"调度商定性"→"强 CEX 连接通道四命题拆开"） | **取 main**（9c 是两案转正的正式条，弱化属方法学立场分歧；分歧存档：codex@639bfd0 该文件 §9c，留裁决） |
| 10 | report-template.md | 三问改写＋economic_control_ledger 强制段（带 P0/P1 旧词） | 取 main＋加回最小指针句（"Codex 版另按 economic-control-accounting.md 建经济控制账"，v5 口径） |
| 11 | research-workflows.md | Codex 适配头＋禁自审段 | **取 main**，通则 G1/G2 覆盖 |
| 12 | update-workflow.md | U 阶段外审路一行改禁自审 | **取 main**，通则 G2 覆盖 |
| 13 | accumulate_offenders.py | 单案目录模式＋fail-closed＋行为 cohort 排除（功能增强） | **codex 为体**＋main 的一行注释叠加；⚠ 本脚本属标签库工具（CC 真源），c2.0 后建议回灌 main（TODO 记 CHANGELOG-codex） |
| 14 | run_all.py | SUITE 加 test_audit_release_gate | main SUITE（16 项）＋test_audit_release_gate＝**17 项** |
| 15 | test_cluster_quality.py | ＋T3/T4/T5（单案/fail-closed/敏感度） | 两边并存（功能不相交）；T3 测试数据清 `"tier":"P1"` 残留字段 |
| 16 | test_figures_from_facts.py | ＋metrics 宏/schema 契约测试 | 两边并存（main 只删 tier 字段） |

## 三、gate 输入 schema 变化

- **audit_release_gate.py**：输入＝三账 JSON＋audit_input_manifest（codex 审计协议自有 schema），main v5/v6 未触及三账概念 → **零变化**。
- economic-control-accounting.md 措辞迁移后，whale_tier 维度的判定口径＝playbook-entity-cluster-tiering §6a 现行双门槛（大庄/小庄），报告不再出现 P0/P1 字样。
- main 新增 gate（supply_truth_gate、handoff_manifest verify/freeze）平台无关，codex 侧直接可用。

## 四、每个测试的新预期

| 测试 | merge 后预期 |
|---|---|
| run_all.py | **17/17 PASS**（main 16＋audit_release_gate） |
| test_cluster_quality.py | T1–T5 全过；T5 判级断言已随 main 改"小庄"（codex T5 与 main T5 同名不同体——以实际 merge 后并集为准，冲突段手工融合） |
| test_figures_from_facts.py | main 删 tier＋codex 契约测试并存全过 |
| test_handoff_manifest.py（main 新增） | 19 项照过（脚本平台无关） |
| test_audit_release_gate.py（codex 独有） | 照过（输入 schema 零变化） |
| casebook_lint / test_report_facts / test_supply_truth_gate 等 main 新增 | 照过（首次进 codex SUITE） |

## 五、未收编分歧存档（不丢内容，留裁决）

1. **state-anomaly §9c**：codex 弱化版（强 CEX 连接通道，四命题拆开审）vs main 正式条（调度商定性，两案转正）——`git show 639bfd0:references/playbook-state-anomaly.md` 可考古。
2. **entity-cluster-methods 枢纽处理法**：codex 两段版（删除③事后公共合约卫生检查作为独立步）vs main 三段版——同上考古。
3. 裁决路径：后续复盘或用户点名时对比两版，若 codex 立场胜出则走"回灌 CC"流程改 main。

## 六、SKILL.md 适配节通则（c2.0 重构后的差异承载方式）

- **G1 路径/工具/模型映射**：文中 `~/.claude/skills/token-chip-analysis` 一律读作 `${CODEX_HOME:-$HOME/.codex}/skills/token-chip-analysis`；`AskUserQuestion`/`WebSearch`/`Agent`/`Workflow`/`Monitor` 等 Claude 工具名按 Codex 现有能力映射；`sonnet`/`opus` 别名不得原样使用。
- **G2 禁自审（c1.1.0 条款，通则化）**：下发文档中一切"外部异构怀疑者/codex 外审/GPT-5.6 复核"步骤，Codex 版一律读作**不适用**——不得 `codex exec`、另开 Codex CLI 或同模型充当外审；相应角色只能称内部对抗性自检。
- **G3 独有分册**：economic-control-accounting.md / lp-fee-accounting.md / independent-audit-protocol.md / audit_release_gate.py 为 codex 独有资产，永不随同步删除；economic-control 账本与审计协议在完整版交付前照常执行。
- 效果：以后 CC 下发文档更新时，codex 侧不再需要逐文件改字承载平台差异——双改文件冲突面预期从 16 个大幅收缩到"真方法学增量"少数几个。
