# 盲审 R6a：2 条发现

审查基线：`8e54242c5c4e0fd02c5c1a1e1dae4d509b349236`；分支：`main`；VERSION：`9.0.1`；git status 前/后：空/空。

两条均为此前未报的残留不一致。对照 R1 施工前基线 `3942c23`，相关原句当时已经存在；**未确认 R1–R5 修复新引入的问题**。

## 覆盖声明

逐文件审阅以下 **46 份文档，共 6,562 行**：

```text
SKILL.md
references/address-book.md
references/analysis-playbook.md
references/analyze-workflow.md
references/context-discipline.md
references/data-pipeline-evm-channels.md
references/data-pipeline-evm-recon.md
references/data-pipeline-evm-sources.md
references/data-pipeline-evm.md
references/data-pipeline-robinhood-channels.md
references/data-pipeline-robinhood-methods.md
references/data-pipeline-robinhood-traps.md
references/data-pipeline-robinhood.md
references/data-pipeline-solana-capture.md
references/data-pipeline-solana-scan.md
references/data-pipeline-solana.md
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
references/casebook/cex-custody-methods.md
references/casebook/cex-custody.md
references/casebook/entity-clustering-methods.md
references/casebook/entity-clustering.md
references/casebook/supply-accounting-methods.md
references/casebook/supply-accounting.md
references/labels/README.md
references/labels/MAINTENANCE.md
commands-staging/token-analyze-1.md
commands-staging/token-analyze-2.md
commands-staging/token-analyze-3.md
commands-staging/token-analyze.md
```

另外审阅 `CHANGELOG.md` 文件头版本规则及 7.2.0–9.0.1 活跃索引，核对 `agents/openai.yaml`、`pyproject.toml`。

术语表规范化后 **227 项**，覆盖阶段、门禁、schema、文件名、参数与阈值；在必审文档中检得 **1,577 个“术语—行”命中**。以 `rg -n` 和带行号区间阅读交叉核对，辅以 **310 个 Python 文件的 AST 静态解析**核查参数、必填项及分派；对候选继续追读去重键、字段构造和消费逻辑，排除别名、历史说明、探索档差异及前五轮已报项。

全程离线、只读，未新建或修改文件；未读取 `~/.codex/` 或其他禁止路径内容，未读取 `attic.md` 正文。

## 发现（按严重度排序）

### D1 — minor — B 类 — Alchemy 续采文档写按交易哈希去重，现行重放按交易内事件键去重

- **位置甲**：[references/data-pipeline-evm-channels.md:201](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:201) 原文「容忍少量重复、下游按 tx hash 去重」。
- **位置乙**：[scripts/evm/replay_pass1.py:79](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/replay_pass1.py:79) 原文：
  ```python
  rows[(c["tag"], tx.lower(), li)] = (b, ts, frm.lower(), (to or Z).lower(), v)
  ```
  同文件第 72 行：
  ```python
  li = int(row["log_index"]) if standard8 else int(uid.rsplit(':', 1)[-1])
  ```
- **矛盾点**：实际键包含通道、交易哈希和事件序号，单独使用交易哈希会合并同笔交易里的不同转账。以内存执行现行 AST 键表达式验证：同一交易、两个不同 `li` 保留 **2 条**，按交易哈希只剩 **1 条**。
- **反向验证**：`references/data-pipeline-evm-sources.md:64` 明确写「Alchemy uniqueId 尾号=**类别内序号**」及「段内用自家键去重」，与代码一致。这不是别名差异。通道已明确限制为 exploration，因此定为 minor。
- **修法建议**：删除「、下游按 tx hash 去重」，去重规则沿用已有 §8.1；只改文本，无需改代码。
- **复现**：
  ```bash
  rg -n -F '下游按 tx hash 去重' references/data-pipeline-evm-channels.md
  rg -n 'uniqueId 尾号|自家键' references/data-pipeline-evm-sources.md
  rg -n 'uid\.rsplit|rows\[\(c\["tag"\]' scripts/evm/replay_pass1.py
  ```

### D2 — minor — A 类 — 聚类总括句统一封顶“高度疑似”，判级权威表却允许类型②达到“链上铁证”

- **位置甲**：[references/playbook-entity-cluster-methods.md:184](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:184) 原文「**措辞锁定：** 聚类结论一律"高度疑似同一实体"，不写确权」。
- **位置乙**：[references/playbook-entity-cluster-tiering.md:53](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-tiering.md:53) 类型②定义原文「链上可实锤合并」，措辞上限原文「链上铁证 / 高度疑似」。同文件第 60 行进一步要求「实锤（类型①②）与高度疑似（类型③）分开报」。
- **矛盾点**：甲将所有聚类结论统一降至疑似，乙允许有充分证据的多地址关联实体进入实锤档；执行者据甲处理，会与乙要求的分档呈现发生冲突。
- **反向验证**：甲位于现行聚类规则正文，未标历史或 exploration；其“一律”也未限定为共用出纳这一种证据。乙明确是标签与类型的权威规则，故属于残留总括句冲突，定为 minor。
- **修法建议**：删除甲侧统一限定措辞上限的句子，沿用现有类型分级及经济确权证据规则；无需新增规则或改代码。
- **复现**：
  ```bash
  rg -n '措辞锁定|聚类结论一律' references/playbook-entity-cluster-methods.md
  rg -n '② 多地址关联|实锤（类型①②）' references/playbook-entity-cluster-tiering.md
  ```

## 待确认（不计入 N）

无新增待确认项。前五轮已报问题及已裁决的 `wave_scan` 浮点阈值例外未重复计入。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | B 类 | `references/data-pipeline-evm-channels.md:201` | `scripts/evm/replay_pass1.py:79` | 文档按交易哈希去重，代码保留交易内事件序号 |
| D2 | minor | A 类 | `references/playbook-entity-cluster-methods.md:184` | `references/playbook-entity-cluster-tiering.md:53` | 聚类统一疑似上限与类型②允许实锤冲突 |
