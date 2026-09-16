# 盲审 R5：2 条发现

审查基线：`0e031559f13a4b11608fd94025a447dd645012cc`；git status 前/后：空/空；结束时 HEAD 未变。两条均为 minor，均早于 R1，并非 R1–R4 修复引入。报告全文已打印到 stdout。

纪律披露：全程离线，无文件写入、无提交；未调用工具读取 `~/.codex/`。但一次 `wc -l` 的 `references/*.md` 展开误含 `references/attic.md`，读取其字节统计了 42 行。未显示或引用正文，仍违反了禁读约束；已当场披露并停止使用该通配读取。这是审查者的纪律偏离，不计入仓库发现数。

## 覆盖声明

对以下 46 份必审文档、共 6,564 行进行了全文检索与术语提取，对候选矛盾展开上下文并定向读代码；另审 `CHANGELOG.md` 顶部的现行规则。

| 目录 | 文档清单 |
|---|---|
| 根目录 | `SKILL.md` |
| `references/` 流程与环境 | `analysis-playbook.md`、`analyze-workflow.md`、`context-discipline.md`、`environment.md`、`independent-audit-protocol.md`、`maintenance-review-repair.md`、`monitoring-package.md`、`report-template.md`、`research-workflows.md`、`retrospective.md`、`scan-schemas.md`、`split-run.md` |
| `references/` EVM | `data-pipeline-evm.md`、`data-pipeline-evm-channels.md`、`data-pipeline-evm-recon.md`、`data-pipeline-evm-sources.md` |
| `references/` Robinhood | `data-pipeline-robinhood.md`、`data-pipeline-robinhood-channels.md`、`data-pipeline-robinhood-methods.md`、`data-pipeline-robinhood-traps.md` |
| `references/` Solana | `data-pipeline-solana.md`、`data-pipeline-solana-capture.md`、`data-pipeline-solana-scan.md` |
| `references/` 方法与地址 | `address-book.md`、`economic-control-accounting.md`、`lp-fee-accounting.md`、`playbook-entity-cluster-cost.md`、`playbook-entity-cluster-methods.md`、`playbook-entity-cluster-tiering.md`、`playbook-evidence-wording.md`、`playbook-state-anomaly.md`、`playbook-supply-recon.md` |
| `references/casebook/` | `README.md`、`cex-custody.md`、`cex-custody-methods.md`、`entity-clustering.md`、`entity-clustering-methods.md`、`supply-accounting.md`、`supply-accounting-methods.md` |
| `references/labels/` | `README.md`、`MAINTENANCE.md` |
| `commands-staging/` | `token-analyze.md`、`token-analyze-1.md`、`token-analyze-2.md`、`token-analyze-3.md` |

术语表：**2,114 条**，按非空单行反引号内容与 A0–A6/G/EF/ET 标识去重。脚本索引覆盖 310 个 Python 文件；从文档提取 147 个不同脚本名、471 处行级引用，对照脚本存在性、CLI 定义、schema、字段、默认值及退出语义。另核对了 `agents/openai.yaml`、`pyproject.toml` 和相关 labels CSV。

检索策略：先读 R1–R4 报告、对应工单及 `code_change_pending.md` 排重；再按脚本名、参数、schema、阈值、阶段编号、完整地址交叉检索，用 `nl -ba` 展开两侧原文；最后对照 R1 基线 `444544360179d5080657aafd5ad60a78fe89e9b3` 的限定路径 diff，核查修复归因。未执行生产入口。

相对前四轮，本轮重点补查：地址簿与发布标签表的完整地址；环境说明与依赖/探针；复盘、维修和版本规则；判例与成本/经济控制/判级方法；监控和报告示例与实际收口接口；schema 字段与生产者。

## 发现（按严重度排序）

### D1 — minor — A 类 — RobinHoodSettler 的完整地址在坑册与地址簿中不一致

- 位置甲：[references/data-pipeline-robinhood-traps.md:62](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-traps.md:62)，原文：「平台核心设施地址（Index 分析核验 2026-07-18，已入 address-book）」及「`RobinHoodSettler 0xe72688f7d25d73a2a5e2a4e40d1f0b6b2c5c1e05`=App 交易结算器」。
- 位置乙：[references/address-book.md:147](/Users/uravvv/.claude/skills/token-chip-analysis/references/address-book.md:147)，原文：「`0xe72688f7d25d7318b9a81f21edda640ca948c83b,robinhood,RobinHoodSettler（App 交易结算器，原子过手末余额 0）,infra,exclude,addressbook`」。
- 旁证：[references/labels/labels-robinhood.csv:85](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/labels-robinhood.csv:85) 同样登记地址簿中的 `0xe72688f7d25d7318b9a81f21edda640ca948c83b`。
- 矛盾点：坑册声称该完整地址已登记，实际同名登记项和发布标签表却是另一地址。照坑册构造排除名单会与标签库不一致。本轮确证的是仓内登记冲突，未裁定链上地址真值。
- 修法建议：按“删除 > 修改 > 新增”，优先删除坑册重复硬编码地址，改指向地址簿同名条目；仅改文本，不新增地址记录、不需改代码。
- 归因：相关三个文件相对 R1 基线无变化；不是 R1–R4 修复引入。
- 复现（仓库根目录执行）：

```bash
rg -n 'RobinHoodSettler|e72688f7' references/data-pipeline-robinhood-traps.md references/address-book.md references/labels/labels-robinhood.csv
```

### D2 — minor — B 类 — 图 2 文档允许合并实体线，现行收口实现明确拒绝

- 位置甲：[references/report-template.md:162](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:162)，原文：「标签实体各画一线，线超 8 条时可将持仓较小的实体合并成一条（合并了谁在图注写明）」。
- 位置乙：[scripts/report/stage2_closeout.py:197](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:197)，原文：

```python
if "merge_groups" in fig2:
    errors.append(workorder_error("fig2.merge_groups", "本版不支持合并线（范围调整，见 §0 第 6 条）", fig2["merge_groups"]))
```

- 矛盾点：正式分段收口要求必画实体逐一被覆盖，而模板仍允许用合并线替代。按模板声明合并会返回 `WORKORDER BLOCK`。只读内存复现：9 个小庄各画一线时错误列表为空；加入第 8、9 个实体的合并声明后，出现“本版不支持合并线”。此外，[figures_from_facts.py:295](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py:295) 所示函数按单一实体核对每条线的末点，没有合计实体对账语义。
- 修法建议：按“删除 > 修改 > 新增”，删除模板中“线超 8 条时可合并”的许可，保留每实体一线，与当前实现一致。仅改文本，不需改代码。
- 归因：模板该句及收口实现均已存在于 R1 基线；不是 R1–R4 修复引入。
- 复现：以下仅从源文件抽取并执行两个无 I/O 的函数，输入全在内存，不导入生产模块、不写文件。

```bash
python3 -B -c '
import ast
from pathlib import Path
p = Path("scripts/report/stage2_closeout.py")
t = ast.parse(p.read_text())
names = {"workorder_error", "fig2_selection_errors"}
ns = {}
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), str(p), "exec"), ns)
facts = {"entities": {f"e{i}": {"label": f"小庄#{i}"} for i in range(1, 10)}}
fig2 = {"required_entity_ids": list(facts["entities"]), "lines": [{"entity_id": e} for e in facts["entities"]]}
print("9 distinct lines:", ns["fig2_selection_errors"](facts, fig2)[0])
fig2["merge_groups"] = [{"entity_ids": ["e8", "e9"], "label": "小庄#8+#9合计"}]
print("merge requested:", ns["fig2_selection_errors"](facts, fig2)[0])
'
```

实测第二行返回：`WORKORDER BLOCK: fig2.merge_groups: 本版不支持合并线（范围调整，见 §0 第 6 条）`。

## 待确认（不计入 N）

无另列条目。已知待决 D1、D2 及 R1–R4 已报问题未重复计数。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | A | `references/data-pipeline-robinhood-traps.md:62` | `references/address-book.md:147` | 同名结算器的完整地址与登记表不一致 |
| D2 | minor | B | `references/report-template.md:162` | `scripts/report/stage2_closeout.py:197` | 模板允许合并线，收口实现明确拒绝 |
