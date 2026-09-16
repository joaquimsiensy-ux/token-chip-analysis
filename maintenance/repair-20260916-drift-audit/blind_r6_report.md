# 盲审 R6：1 条发现

审查基线：`03e7c65b3963979586a1b2dcd80680c91a0f5672`；`git status --short` 前/后：**空/空**。审查前后 HEAD 相同。

确认 **1 条 minor、A 类**；未确认新的 B 类问题或 R1–R5 修复引入的问题。报告全文已打印到 stdout。全程离线，未修改、新建文件或 commit。

**审查纪律披露：**开始统计行数时，`wc -l references/*.md` 误纳 `references/attic.md`，读取其字节用于计行，未输出正文；随后已排除。这违反了禁读要求，不能宣称访问纪律全部满足。未打开 `~/.codex/` 下文件；会话预载摘要未作为审计证据。

## 覆盖声明

以下 46 份文档纳入全文检索、术语提取及相关规则上下文核对；另核对 `CHANGELOG.md` 开头现行规则，共 47 份：

```text
SKILL.md
references/address-book.md
references/analysis-playbook.md
references/analyze-workflow.md
references/context-discipline.md
references/data-pipeline-evm.md
references/data-pipeline-evm-channels.md
references/data-pipeline-evm-recon.md
references/data-pipeline-evm-sources.md
references/data-pipeline-robinhood.md
references/data-pipeline-robinhood-channels.md
references/data-pipeline-robinhood-methods.md
references/data-pipeline-robinhood-traps.md
references/data-pipeline-solana.md
references/data-pipeline-solana-capture.md
references/data-pipeline-solana-scan.md
references/economic-control-accounting.md
references/environment.md
references/independent-audit-protocol.md
references/lp-fee-accounting.md
references/maintenance-review-repair.md
references/monitoring-package.md
references/playbook-entity-cluster-cost.md
references/playbook-entity-cluster-methods.md
references/playbook-entity-cluster-tiering.md
references/playbook-evidence-wording.md
references/playbook-state-anomaly.md
references/playbook-supply-recon.md
references/report-template.md
references/research-workflows.md
references/retrospective.md
references/scan-schemas.md
references/split-run.md
references/casebook/README.md
references/casebook/cex-custody.md
references/casebook/cex-custody-methods.md
references/casebook/entity-clustering.md
references/casebook/entity-clustering-methods.md
references/casebook/supply-accounting.md
references/casebook/supply-accounting-methods.md
references/labels/README.md
references/labels/MAINTENANCE.md
commands-staging/token-analyze.md
commands-staging/token-analyze-1.md
commands-staging/token-analyze-2.md
commands-staging/token-analyze-3.md
CHANGELOG.md（仅现行规则）
```

- **术语表：2,113 项去重检索键。**从上述 46 份文档的 6,564 行提取非空单行反引号内容及 A/G/EF/ET 编号；该数是检索键数，不是独立规则数。
- **检索策略：**按脚本名、子命令、CLI 参数、schema、字段、默认值、阈值和证据强度交叉检索，再回读上下文；用 AST 解析 `scripts/` 下 310 个 Python 文件的声明，核对文档涉及的 144 个脚本名、463 处行级引用；另对照 `agents/openai.yaml`、`pyproject.toml`。AST 扫描不等于全部实现逐行审计。
- **本轮重点补强：**地址簿与标签数据、依赖与 env_check、复盘/维护命令、casebook 与正式方法册的证据强度、schema 与生产者声明。地址簿 CSV 到 manual_labels 的 206 行、15 字段逐项一致；发布标签差异结合覆盖与合并规则核对，未仅凭差异报错。
- **修复回看：**阅读 R1–R5 报告、五份已施工工单及 `code_change_pending.md`；对照 R1 内容基线 `444544360179d5080657aafd5ad60a78fe89e9b3` 至当前 HEAD 的全部 28 份范围内文档差异。已修复条目及已知 D1/D2/D3 未重报。
- 本轮验证为离线文件核对与内存计算；未重跑已知九项机器守卫，未将静态核对表述为业务运行验收。

## 发现（按严重度排序）

### D1 — minor — A 类 — 公共 CEX 同源边既禁止计入证据，又允许有条件升为中等

- **位置甲：**[references/playbook-entity-cluster-methods.md:117](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:117)  
  原文：「**CEX 热钱包不可作为共同资金来源证据**：从同一热钱包提币的地址不构成关联（热钱包是全用户共用资金池）」。
- **位置乙：**[同文件:155](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:155)  
  原文：「**注资证据分级（gas/资金同源边的强度标尺）**」；「**公用桥 solver / CEX 热钱包同源**默认剔除，仅当"同 48h 窗 + 行为指纹一致"才升中等。」
- **补充约束：**[同文件:247](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:247)  
  原文：「funder 未证为私人钱包（≤15、非合约，或已有独立证据确属该实体）前，共同来源不得作合并边。」
- **矛盾点：**第 155 行升级的是“gas/资金同源边”，其条件不要求证明 funder 私有。因此，对“公共 CEX 热钱包＋同 48h 窗＋行为一致”的同一情形，一处禁止使用共同来源边，另一处允许它进入中等证据等级。影响证据是否参与成边和分级；尚未验证具体案例误并。
- **归因：**上述规则在 R1 内容基线已同时存在，R1–R5 没有修改这些行。属于本轮新发现的既有冲突，**非 Rn 修复引入**。
- **修法建议：删除优先，仅改文本。**删除第 155 行公共来源“才升中等”的例外；行为指纹按现有行为规则独立评价，公共资金来源仍剔除。不需改代码。
- **复现：**在仓库根目录执行：

```bash
nl -ba references/playbook-entity-cluster-methods.md |
  sed -n '105,118p;154,156p;243,247p'

git show 444544360179d5080657aafd5ad60a78fe89e9b3:references/playbook-entity-cluster-methods.md |
  nl -ba | sed -n '117p;155p;247p'

git diff 444544360179d5080657aafd5ad60a78fe89e9b3 HEAD -- references/playbook-entity-cluster-methods.md
```

## 待确认（不计入 N）

无保留的新候选。已知待决 D1/D2/D3 不在本轮重新计数。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | A | playbook-entity-cluster-methods.md:117、247 | 同文件:155 | 公共 CEX 同源边的剔除规则与条件升级规则冲突 |
