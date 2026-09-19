# 盲审 R8a：1 条发现

审查基线：`c16bf8e63369d8b83097b00ce2d0da765906e25e`；git status 前/后：空/空

分支 `main`，`VERSION=9.0.1`。确认 **1 条 B 类 minor**；未确认 R1–R7 修复引入新的不一致。报告全文已打印到 stdout。

## 覆盖声明

逐文件检查以下 46 份必审文档（合计 6562 行），另检查 CHANGELOG 文件头版本规则及 7.2.0–9.0.1 活跃窗口中的现行行为说明：

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
CHANGELOG.md（限定上述范围）
```

术语表从 SKILL、analyze-workflow、split-run 提取并归一为 **201 条**：21 个 schema/协议标识、33 个脚本名、41 个 CLI 选项、86 个文件名、20 个阶段/门禁标识；另核对相关子命令、阈值、角色及四查/五查口径。

检索采用显式文件白名单、`rg -n` 与 Python 文本/AST 检索，比较命中上下文；对全部文档提及的 147 个脚本文件名检查引用，对 `scripts/**` 的 310 个 Python 文件解析定义与参数，并精读相关生产者、消费者、默认值和测试。非 argparse 入口回查 `sys.argv` 分派。另核对 `agents/openai.yaml`、`pyproject.toml`，与 R1–R7 报告去重并复查修复差异。历史案例、合法别名、formal/exploration/legacy 差异及已裁决的 wave_scan 浮点阈值例外均未计入发现。

全程离线，未修改、新建文件或 commit；验证采用静态对照与内存复现，未复跑落盘测试。**纪律偏差披露**：初始 `wc -l` 误将 `references/attic.md` 纳入行数统计，工具读取了文件但未显示正文；此事已在过程说明，随后显式排除。未读取 `~/.codex/` 或 memories。

## 发现（按严重度排序）

### D1 — minor — B 类 — SPL 扫描默认使用 165 字节过滤的说明已不符合现行请求

- 位置甲：`references/data-pipeline-solana-scan.md:64` 原文「扫描器默认 `--datasizes auto`：Token-2022 强制 all，SPL 用 165」。
- 位置乙：`scripts/solana/scan_token_accounts.py:149` 定义「`ap.add_argument("--datasizes", default="auto",`」；第 150 行说明「`compatibility option; the observation protocol always scans all extension sizes`」。
- 实际请求：`scripts/lib/solana_observation.py:400` 原文「`filters = [{"memcmp": {"offset": 0, "bytes": mint}}]`」；第 401–405 行把该 filters 原样传给 `getProgramAccounts`，没有 `dataSize` 条件。
- 矛盾点：现行 CLI 对 SPL 也不加 165 字节过滤，文档却承诺默认加该过滤；执行者据此复现请求或排查扫描结果时，会采用与生产者不同的筛选条件。
- 反向验证：旧 `choose_datasizes()` 虽仍存在，但 AST 确认 `main()` 对它调用数为 0，对 `observe_snapshot()` 调用数为 1。抽取实际请求构造语句在内存中运行，以本地替身记录请求，SPL 与 Token-2022 的 filters 均只有 mint 的 memcmp；未访问 RPC。普通 SPL 账户仍为 165 字节，不据此推断现有持仓计算错误，故定为 minor。
- 来源核对：`git blame` 将文档句定位到 `eb2f4a60`（2026-08-02），实际请求定位到 `160a8522`（2026-08-08）；**不是 R1–R7 修复引入**。
- 修法建议：优先删除「SPL 用 165」；如需保留默认行为说明，改成「默认不按 dataSize 过滤」。只改文本。
- 复现：在仓库根目录执行：

```bash
rg -n -F 'SPL 用 165' references/data-pipeline-solana-scan.md
rg -n 'choose_datasizes|observe_snapshot|datasizes|compatibility option' scripts/solana/scan_token_accounts.py
rg -n -A5 -F 'filters = [{"memcmp": {"offset": 0, "bytes": mint}}]' scripts/lib/solana_observation.py
git blame -L 64,64 -- references/data-pipeline-solana-scan.md
git blame -L 400,405 -- scripts/lib/solana_observation.py
```

## 待确认（不计入 N）

**A2“唯一认可 accounting-gate/v2”的适用范围。**

`references/analyze-workflow.md:66` 写「正式记账重跑产 `accounting-gate/v2`，是发布消费面唯一认可的记账收据」，但 `references/independent-audit-protocol.md:164` 明确写「Solana 为 `scripts/solana/accounting_gate_sol.py` 的 `accounting-gate/v1`」。

代码与后者一致：`scripts/solana/accounting_gate_sol.py:137` 为「`result = {"schema": "accounting-gate/v1", "chain": "solana", "mint": a.mint,`」；`scripts/report/shared_release_receipt.py:1721` 为「`elif accounting.get("schema") != "accounting-gate/v1":`」，随后拒绝错误版本。

第 66 行所在段以 EVM 命令起笔，该句可能继承 EVM 限定；因此暂不判定为跨链规则矛盾。如其本意覆盖两链族，才需将句首收窄为「EVM 正式记账重跑」。

```bash
rg -n '正式记账重跑' references/analyze-workflow.md
rg -n 'Solana 为' references/independent-audit-protocol.md
rg -n -F '"schema": "accounting-gate/v1"' scripts/solana/accounting_gate_sol.py
rg -n -F 'accounting.get("schema")' scripts/report/shared_release_receipt.py
```

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | B 类 | references/data-pipeline-solana-scan.md:64 | scripts/solana/scan_token_accounts.py:149；scripts/lib/solana_observation.py:400 | 文档称 SPL 默认按 165 字节过滤，实际请求仅按 mint 过滤 |
