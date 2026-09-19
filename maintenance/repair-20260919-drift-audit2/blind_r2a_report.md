# 盲审 R2a：2 条发现

审查基线：`652799755085c121498e3787b630f77b536d6e31`；git status 前/后：空/空。两次 `git status --short` 均退出 0、stdout 为空；分支 `main`，`VERSION=9.0.1`。

覆盖声明：从 `SKILL.md`、`analyze-workflow.md`、`split-run.md` 提取核心术语 **206 项**，扩展至全部必审文档后为 **617 项**。逐文件检索阶段、门禁、schema、脚本、子命令、参数和产物名，并核读命中上下文；阈值、角色、链档及章节引用另行比对。对照 `scripts/**` 中 337 个源码／契约文件检索符号与字段，并核读相关实现、测试；另读 `agents/openai.yaml`、`pyproject.toml`。CLI 以参数定义为准，产物以路径和写入语句为准。

审过的文档清单，共 47 份；`CHANGELOG.md` 仅将文件头版本规则及 7.2.0–9.0.1 条目的现行行为陈述纳入判断：

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
CHANGELOG.md
```

已读取本工程 R1 两路报告、工单 v2、完成报告及获准的上一轮裁决台账，排除 R1 九项和已知浮点阈值例外。**本轮两项均早于 R1，未发现 R1 修复引入的新不一致。**

纪律披露：全程离线，未修改、新建文件或 commit，未读取 `~/.codex/`。有一次禁读操作偏差：最初行数统计使用 `references/*.md`，使 `wc -l` 读取了 `attic.md` 的字节计数；没有输出或审阅其正文，当时已披露，随后全部检索显式排除该文件。

## 发现（按严重度排序）

### D1 — blocker — B 类 — Multicall3 跨链调用示例遗漏链参数，ETH／Base 查询会按 BSC 校验而失败

- **位置甲**：[references/data-pipeline-evm-channels.md:219](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:219) 原文「参数化调用：`python3 scripts/evm/multicall_balances.py --token 0x... --input addresses.txt --out balances.json [--rpc URL ...]`。默认 4 个公共节点仅适用于 BSC；跨链必须显式传对应链的 `--rpc`」。
  
  同族说明位于 [references/data-pipeline-evm-sources.md:28](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-sources.md:28)，原文「用 `--token/--input/--out` 注入本案参数，非 BSC 链另显式传 `--rpc`」。

- **位置乙**：[scripts/evm/multicall_balances.py:90](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/multicall_balances.py:90) 原文「`parser.add_argument("--chain", default="bsc",`」；[同文件:107](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/multicall_balances.py:107) 原文「`pool = attested_rpc_pool(nodes, args.chain, formal=True, rps=4, concurrency=1)`」，随后 `pool.attest()`，捕获校验错误后第 112 行「`return 1`」。
  
  [scripts/lib/net.py:339](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/net.py:339) 原文「`if observed != self.expected_chain_id:`」，下一行「`raise RpcChainMismatch(`」。

- **矛盾点**：文档给出的非 BSC 调用步骤只补 RPC，代码不会从 RPC 推导链名，仍按默认 BSC 校验；执行者照示例查询 ETH／Base 会在余额查询前退出 1。

- **反向验证**：链注册表明确登记 ETH=1、BSC=56、Base=8453，均为正式支持链，不涉及别名或探索档。离线提取现行 `parse_args`、`main` 和链校验函数，以内存替身返回链 ID：文档参数在 ETH／Base 下分别得到“1／8453 不匹配预期 56”并返回 1；补上对应 `--chain` 后校验通过。未发生网络请求或文件写入。

- **归因**：R1 前既存。相关文档及实现相对 R1 内容基线 `3942c23` 无差异。

- **修法建议**：删除 `data-pipeline-evm-sources.md:28` 的重复参数说明，保留 §3.5 指针；修改 §3.5 示例，显式加入 `--chain <链>`，并将跨链要求写为对应的 `--chain` 与 `--rpc`。只改文本。

- **复现**：

```sh
rg -n 'multicall_balances|非 BSC 链另显式' \
  references/data-pipeline-evm-channels.md references/data-pipeline-evm-sources.md
nl -ba scripts/evm/multicall_balances.py | sed -n '85,112p'
nl -ba scripts/lib/net.py | sed -n '303,344p'
nl -ba scripts/lib/net.py | sed -n '410,424p'
rg -n 'evm_chain_id=(1|56|8453)' scripts/lib/chain_registry.py
```

### D2 — minor — A 类 — 措辞册将事实源产物写成 `report_facts.json`，与报告模板的 `facts.json` 不一致

- **位置甲**：[references/playbook-evidence-wording.md:18](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-evidence-wording.md:18)，执行契约总表的“权威脚本/产物”栏原文「`report_facts.json`、措辞表、facts gate」。

- **位置乙**：[references/report-template.md:208](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:208) 原文「报告编译化：facts.json 事实源与宏引用（3.18.0 新写作纪律）」；第 212 行明确该产物「由 `facts_gate.py build` 自三账生成，禁手抄」。
  
  实现旁证：[scripts/report/facts_gate.py:531](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:531) 原文「`ap.add_argument("--out", default="facts.json")`」，第 544 行以该输出名构造实际写入路径。

- **矛盾点**：同一报告事实源在两份现行文档中使用不同文件名，措辞册会引导执行者查找未由标准流程生成的 `report_facts.json`；当前主流程仍明确使用 `facts.json`，因此判 minor。

- **反向验证**：`report_facts.json` 在全部必审现行文档中仅此一处，源码没有同名产物约定，也没有将其声明为 `facts.json` 别名。构建器允许自选输出名，并不构成这项权威产物名称的独立定义。

- **归因**：R1 前既存。措辞册相对 `3942c23` 无差异；R1 未改报告模板上述事实源定义。

- **修法建议**：将表格中的 `report_facts.json` 修改为 `facts.json`，不增加解释或新产物。

- **复现**：

```sh
rg -n --glob '*.md' --glob '!attic.md' --glob '!*.bak_*' \
  'report_facts\.json' SKILL.md references commands-staging
nl -ba references/report-template.md | sed -n '208,212p'
nl -ba scripts/report/facts_gate.py | sed -n '526,548p'
rg -n -F 'report_facts.json' scripts
```

最后一条应无匹配、退出 1。

## 待确认（不计入 N）

无保留项。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | blocker | B 类 | `references/data-pipeline-evm-channels.md:219`；`references/data-pipeline-evm-sources.md:28` | `scripts/evm/multicall_balances.py:90`；`scripts/lib/net.py:339` | 跨链示例未传 `--chain`，ETH／Base RPC 被按 BSC 校验并拒绝 |
| D2 | minor | A 类 | `references/playbook-evidence-wording.md:18` | `references/report-template.md:208` | 同一事实源被分别命名为 `report_facts.json` 和 `facts.json` |
