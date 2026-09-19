# 盲审 R10a：1 条发现

审查基线：`435345448c31b02d9798fcc89e9216754cde5df8`；main，VERSION=9.0.1；git status 前/后：空/空。

全程离线、只读；未新建或修改文件，未 commit，未读取 `~/.codex/`、memories 或其他禁读内容。报告全文已打印到 stdout。

## 覆盖声明

逐文件审查了以下 46 份必审文档：

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

另审 `CHANGELOG.md` 文件头现行规则及活跃窗口 7.2.0–9.0.1 的当前行为描述；对照 `agents/openai.yaml`、`pyproject.toml`。

术语表去重后 **275 项**，从 SKILL、analyze-workflow、split-run 提取阶段、门禁、schema、文件名、参数、子命令、字段、角色及数字口径，再对全部必审文档执行固定字符串检索，共命中 955 行。结合逐文件阅读，用 `rg -n` 和带行号正文复核候选；对 `scripts/**` 中 310 个 Python 文件作 AST 静态解析，并沿相关 argparse、子命令分派、产物写入及消费校验核对机器行为。

已对照 R1–R9 报告、工单与完成记录去重，并检查修复差异；未确认九轮修复新引入的不一致。已排除历史描述、明确的 exploration/legacy 档位、合法别名，以及已裁决的 wave_scan 浮点阈值例外。

## 发现（按严重度排序）

### D1 — blocker — B 类 — 旧 Solana 快照“完整即可重新 emit”的迁移承诺无法通过当前扫描器哈希校验

- **位置甲**：[references/data-pipeline-solana-scan.md:67](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:67) 原文：「round4b 格式存量若 raw/supply 实物完整可直接重新 emit；缺失或重放不一致则必须重跑 `scan_token_accounts.py`，禁止手补 meta/hash。」
- **位置乙**：[scripts/report/identity_snapshot_receipt.py:83](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/identity_snapshot_receipt.py:83) 原文：

  ```python
  if m.get("producer")!={"path":"scan_token_accounts.py","sha256":sha(collector)}:
   raise ValueError("Solana holder meta producer is not current scan_token_accounts.py")
  ```

- **生产与调用证据**：[scripts/solana/scan_token_accounts.py:265](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/scan_token_accounts.py:265) 写入原文 `"producer": {"path": "scan_token_accounts.py", "sha256": sha256_file(__file__)}`；identity emitter 第 143 行先调用上述校验，第 188 行将该异常转为 exit 2。
- **矛盾点**：旧扫描器生成的 meta 绑定旧代码哈希，raw/supply 完整不能满足“当前扫描器哈希”条件。按文档直接重新 emit 会在原始数据重放前被阻断，正式身份收据无法生成。
- **离线实证**：早期提交 `3bc6224` 的扫描器 SHA-256 为 `de9efb18d93e853900e2aaca9c6764df98ab9aa6ef49dce3ace75efef8530767`，HEAD 为 `d7d18b68abf795754bd7276054e9fa2fbb6a487016c8e7b93a7882d3e2e58df3`。隔离执行当前校验函数，传入绑定前者的 meta，得到上述 ValueError；尚未进入 raw/supply 实物校验。
- **修法建议**：删除“round4b 格式存量若 raw/supply 实物完整可直接重新 emit”这一承诺。若保留迁移指引，将条件改为“producer 哈希必须匹配当前扫描器；旧哈希产物须重跑扫描器”，保留禁止手补 meta/hash。只改文本，不需改代码。
- **来源判定**：非 R1–R9 修复引入。文档该句的 blame 为 `4aa98834`，代码校验为 `3bc6224b`，均早于本工程九轮修复。
- **复现**：在仓库根目录执行：

  ```sh
  rg -n 'round4b' references/data-pipeline-solana-scan.md
  rg -n 'm.get\("producer"\)|producer is not current scan_token_accounts|def emit_solana|m,collector=validate_solana_source|ap.exit\(2' scripts/report/identity_snapshot_receipt.py
  rg -n '"producer".*sha256_file' scripts/solana/scan_token_accounts.py
  git blame -L 67,67 -- references/data-pipeline-solana-scan.md
  git blame -L 83,84 -- scripts/report/identity_snapshot_receipt.py
  python3 -B -c '
  from hashlib import sha256
  from pathlib import Path
  from subprocess import check_output
  p = "scripts/solana/scan_token_accounts.py"
  print("early:", sha256(check_output(["git", "show", "3bc6224:" + p])).hexdigest())
  print("HEAD: ", sha256(Path(p).read_bytes()).hexdigest())
  '
  ```

## 待确认（不计入 N）

- [references/data-pipeline-solana-scan.md:147](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:147) 写「固定归集口/核心中枢新流出的零历史地址 = 新马甲」；同文件第 133 行限定「关联候选指纹（定级须过 playbook-entity-cluster-methods"行为指纹三问总闸与强弱两档"；纯行为最高为"高度疑似"）」。第 147 行是否隐含已完成控制证据核验，单句不明确；但前文总闸可能已约束该简写，不能据此认定为独立规则冲突，本轮不计数。复现：`rg -n '关联候选指纹|换钱包后第一时间识别的三死穴' references/data-pipeline-solana-scan.md`。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | blocker | B 类 | references/data-pipeline-solana-scan.md:67 | scripts/report/identity_snapshot_receipt.py:83 | 旧快照即使 raw/supply 完整，仍会因旧 producer 哈希被拒，不能按说明直接重新 emit。 |
