# 盲审 R7：0 条发现

审查基线：`b1f2c7fd9d985545845ff98782cd2ec362c8e977`；git status 前/后：**空/空**。

## 覆盖声明

对 46 份必审文档全文检索并回读相关上下文，另核对 `CHANGELOG.md` 第 3–9 行现行规则。以下路径相对仓库根目录：

- 根目录：`SKILL.md`、`CHANGELOG.md`。
- `references/`：address-book.md、analysis-playbook.md、analyze-workflow.md、context-discipline.md、data-pipeline-evm.md、data-pipeline-evm-channels.md、data-pipeline-evm-recon.md、data-pipeline-evm-sources.md、data-pipeline-robinhood.md、data-pipeline-robinhood-channels.md、data-pipeline-robinhood-methods.md、data-pipeline-robinhood-traps.md、data-pipeline-solana.md、data-pipeline-solana-capture.md、data-pipeline-solana-scan.md、economic-control-accounting.md、environment.md、independent-audit-protocol.md、lp-fee-accounting.md、maintenance-review-repair.md、monitoring-package.md、playbook-entity-cluster-cost.md、playbook-entity-cluster-methods.md、playbook-entity-cluster-tiering.md、playbook-evidence-wording.md、playbook-state-anomaly.md、playbook-supply-recon.md、report-template.md、research-workflows.md、retrospective.md、scan-schemas.md、split-run.md。
- `references/casebook/`：README.md、cex-custody.md、cex-custody-methods.md、entity-clustering.md、entity-clustering-methods.md、supply-accounting.md、supply-accounting-methods.md。
- `references/labels/`：README.md、MAINTENANCE.md。
- `commands-staging/`：token-analyze.md、token-analyze-1.md、token-analyze-2.md、token-analyze-3.md。

术语表共 **2,110 个去重检索键**，由上述范围的行内代码标识及 A/G/EF/ET 编号提取；这是检索键数量，不是独立规则数量。

**检索策略：**按脚本名、子命令、CLI 参数、schema、字段、产物名、退出码、默认值、阈值、链支持档位和章节引用交叉搜索，再回读上下文及对应实现。对 `scripts/` 下 310 个 Python 文件建立 AST 检索索引，并定向阅读相关生产者、消费者和 labels CSV；另对照 `agents/openai.yaml`、`pyproject.toml`。

**本轮重点补强：**

- 地址册与标签构建源逐字段比较：206 条手工标签一致；发布 CSV 的差异结合覆盖优先级解释，未直接当作漂移。
- environment 的依赖和命令，对照 pyproject、env_check；retrospective 与 CHANGELOG 的版本规则及回灌命令。
- casebook 与 methods/tiering 的证据上限、公共设施排除、供给和阵营口径；分段命令与报告脚本的参数及产物。
- scan-schemas 与生产者常量、Robinhood 数据格式、LP 费用方向、监控包字段，以及 R1–R6 修改处与其他现行条款的关系。

已用 R1–R6 报告及工单排除重复项；`code_change_pending.md` 的 D1、D2、D3 未重报。全程离线，未修改、新建文件或 commit；报告全文已打印到 stdout。

## 发现

未确认新的 A 类或 B 类漂移；未确认 R1–R6 修复引入的新不一致。

## 待确认（不计入 N）

**Q1：图 2 check 的“每次都落收据”，是否包含输入格式错误？**

- **文档：**[report-template.md:222](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:222) 原文：「每次 check（PASS/FAIL、formal/exploration）都落 `figure2_check_receipt.json` 留痕收据」。
- **代码：**[figures_from_facts.py:287](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py:287) 对非 list 的 series 返回「`--series 应为图 2 whale_series JSON（list of lines）`」；第 329–330 行随即执行 `raise SystemExit("FAIL: " + errs[0])`，早于第 334、338 行的收据写入。
- **未计数理由：**如果“check”指合法输入完成的终值对账，两侧可以一致；如果包括输入格式失败，文档承诺则偏宽。当前不足以认定两侧适用范围相同，因此不按已确认漂移或门禁缺陷立项。
- **复现（只读）：**

```sh
sed -n '222p' references/report-template.md
sed -n '280,342p' scripts/report/figures_from_facts.py
```

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| — | — | — | — | — | 已确认新增发现 0 条；待确认 1 项，不计入 N |

---
## 附：调度方裁定（Fable）

Q1 不立项：`figures_from_facts.py:319-342` 对 PASS 与对账 FAIL 均调用 `_write_check_receipt`；不落收据的只有 series 非 list（:329-330）与容差政策拒（:324-327，exit 2）两种"调用方式非法"，不属 check 结果，与 supply_truth_gate 口径一致。R7 确认 0 条，按用户规则"直到 codex 完全找不出问题"循环收官，升版 7.1.2。
