# 盲审 R7a：2 条发现

审查基线：`fc704dee8cd6cbec60bc4cabf4caffc5674ddd81`；分支：`main`；VERSION：`9.0.1`；git status 前/后：空/空。

两条均为 minor，分别属于 B 类和 A 类；未证实 R1–R6 修复引入新的不一致。两条对应的文档和代码在 `198abf6..HEAD` 无改动。报告全文已打印到 stdout。

## 覆盖声明

逐文件审阅以下 46 份必审文档；另审 CHANGELOG 的指定现行规则：

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
CHANGELOG.md（文件头现行版本规则及 7.2.0–9.0.1 当前行为描述）
```

术语表 **220 项**：阶段/门禁 27、schema/协议 22、脚本 33、CLI 参数 41、产物 63、阈值 18、子命令 10、角色/支持档位 6。以 SKILL、analyze-workflow、split-run 为种子，展开编号缩写并去重；使用显式文件清单进行 `rg -n -F` 交叉检索。

另外提取全部必审文档中的脚本名和 CLI 参数，对 `scripts/**` 中 310 个 Python 文件进行引用、定义与参数检索，精读相关 argparse、分派、默认值、输出及判断分支，并对照有关测试；检查了 `agents/openai.yaml` 和 `pyproject.toml`。对候选逐项排除历史描述、合法别名、formal/exploration/legacy 差异及已裁决例外；与前六轮报告去重，并复查 R1–R6 涉及的 16 份现行文档差异。

全程离线，未修改、新建、删除文件或 commit。**禁读边界披露**：早期一次 `wc -l` 通配符误包含 `references/attic.md`，读取了该文件以统计行数，输出为 42 行；未展示正文，此后未再读取。这违反了本轮禁读要求，已在过程中披露。未读取 `~/.codex/`。

## 发现（按严重度排序）

### D1 — minor — B 类 — 监控包默认重编译命令遗漏 facts，导致当前报告宏原样输出

- 位置甲：[references/monitoring-package.md:117](/Users/uravvv/.claude/skills/token-chip-analysis/references/monitoring-package.md:117) 原文「默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`——这是合法重编译但带显式水印。」
- 位置乙：[scripts/report/build_html.py:267](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/build_html.py:267) 定义可选参数 `--facts`，第 268 行原文「见 facts_gate.py docstring；不给则旧行为不变」；第 419 行原文「`if a.facts:`」，其内第 422 行调用「`rendered, gate_errs, gate_notes = facts_gate.load_and_check(`」，第 424 行才执行「`md_text = rendered`」。
- 关联口径：[references/report-template.md:214](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:214) 原文「报告 md 中实体的持仓枚数/占比/峰值/成员数一律写宏」，以及「附录 B 整块写 `{{appendix_b}}` 自动生成」；第 224 行原文「**新报告必用**」。
- 矛盾点：买入后流程会编辑原 `报告.md` 并覆盖 `报告.html`，但给出的完整默认命令未传 `--facts`，代码因此跳过宏展开。对当前按模板生成的报告，实体数字及附录 B 会变成字面宏，不能完成所述补嵌后交付。纯内存替换输入输出、实际执行现行 `main()` 的结果为：退出码 **0**、**零 WARN**、两种宏均残留；因此第 119 行规定的质检也不会识别此结果。此处问题是宏未展开，与显式降级水印无关。
- 修法建议：**修改现有命令**，补入 `--facts facts.json`，复用原报告事实源；不需改代码。严重度为 minor，因为发生于可选监控包的默认降级重编译路径。
- 来源核对：不是 R1–R6 修复引入；相关命令、宏要求与代码条件此前已存在。
- 复现（仓库根目录运行，均只读）：

```sh
rg -n '默认重跑|退出码 0 且零 WARN' references/monitoring-package.md
rg -n '实体的持仓枚数|新报告必用' references/report-template.md
rg -n -A 6 'if a\.facts:' scripts/report/build_html.py
rg -n -A 1 'ap.add_argument\("--facts"' scripts/report/build_html.py
```

### D2 — minor — A 类 — SQD 专属端点已被明确否定，却仍列为未完成待办

- 位置甲：[references/data-pipeline-solana-capture.md:110](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:110) 原文「**直接匿名调用即可,不需要配 key**」，以及「**不存在"专属端点 URL",无需再等用户抄回**（2026-07-21 定论,2026-07-25 复核确认）」。
- 位置乙：[references/data-pipeline-solana-capture.md:178](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:178) 原文「**遗留后续项**：①~~v2 整合 HyperSync 第二引擎~~ ②~~完备性验收~~（均 3.18.0 完成，验收不通过→禁用待 GA 重验）③Helius key 运行时检测（见 §13c）④SQD key 专属端点补录 ⑤实时 mint 档案（方案 4,用户暂缓）。」
- 矛盾点：同一执行页已经要求停止等待该端点，却仍把补录端点列为未撤销的后续任务，可能引导执行者再次向用户索取它。①②用删除线表示完成，④没有同类撤销标记，也没有“未来推出后再办”的条件；HyperSync 的禁用分档不构成这项 SQD 待办的例外。
- 修法建议：优先**删除**第 178 行的「④SQD key 专属端点补录」，不新增说明，不需改代码。
- 来源核对：不是 R1–R6 修复引入；该文件在上述修复区间未改动。
- 复现：

```sh
rg -n 'SQD gateway key|遗留后续项|专属端点' references/data-pipeline-solana-capture.md
```

## 待确认（不计入 N）

无保留条目。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | B 类 | monitoring-package.md:117 | build_html.py:419 | 默认补嵌命令未传 facts，报告宏不展开且零 WARN |
| D2 | minor | A 类 | data-pipeline-solana-capture.md:110 | 同文件:178 | 无需等待的 SQD 专属端点仍列为补录待办 |
