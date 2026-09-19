# 盲审 R11a：2 条发现

审查基线：`8f73554a4e14a09c3023962496d43f9f32a01c93`；分支 `main`；VERSION=`9.0.1`；git status 前/后：空/空。

覆盖声明：逐文件审阅下列 46 份必审文档，并审阅 `CHANGELOG.md` 文件头版本规则及 7.2.0–9.0.1 活跃窗口中的现行规则描述，共 47 份。

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
CHANGELOG.md（仅指定规则范围）
```

术语表共 **231 项**：阶段/门禁/契约 27、schema 20、文件与产物名 123、参数 41、阈值 12、角色/支持档位/对账称谓 8。从 `SKILL.md`、`analyze-workflow.md`、`split-run.md` 抽取后，在文档白名单上执行 `rg -n -F` 交叉检索，共 756 个命中行；同时逐文件阅读非命中段落。

对照范围为 `scripts/**`（含 tests）、`agents/openai.yaml`、`pyproject.toml`；解析 310 个 Python 文件的 AST，结合源码核对脚本、argparse 参数与子命令、字段、产物及阈值。候选逐项排除合法别名、历史描述和支持档位差异，并与 R1–R10 报告、工单及完成记录去重；复查 R1 基线以来 20 份必审文档的修订。以下两条在 R1 基线 `d30864944462ae10db38ff7d3b1caaf9a96f9a01` 已存在，均为此前未报的存量问题；未确认新的“Rn 修复引入”问题。

执行记录：全程未联网，未新建、修改、删除文件或提交；未读取 `~/.codex/`。有一次已披露的纪律偏差：初始 `wc -l` 通配符误纳入 `references/attic.md`，命令扫描该文件并仅返回 42 行计数，未展示正文；随后改用排除它的白名单，该文件未作为审查证据。

## 发现（按严重度排序）

### D1 — minor — B 类 — 快照更新示例将 RPC 简称写成不可执行的参数值

- 位置甲：[references/data-pipeline-solana-capture.md:61](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:61)，原文「Token-2022 记得 `--rpc api.mainnet-beta`」。这是 §10“快照对比法”第一步“新全量快照”的操作指令。
- 位置乙：[scripts/solana/scan_token_accounts.py:147](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/scan_token_accounts.py:147)，原文「`ap.add_argument("--rpc", action="append", dest="rpcs",`」；同文件第 191 行原文「`endpoints = args.rpcs or [_default_rpc()]`」。[scripts/lib/solana_attested_session.py:42](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_attested_session.py:42) 原文「`request = urllib.request.Request(`」，第 43 行将「`endpoint, data=json.dumps(payload).encode("utf-8"),`」直接传入。
- 矛盾点：代码只对端点字符串去除首尾空白，没有把 `api.mainnet-beta` 展开成 URL。照抄该参数会在构造请求时得到 `ValueError: unknown url type: 'api.mainnet-beta'`，无法取得新快照。它位于既有锚点研报的更新示例，按 minor 计；同名通道在一般叙述中可作简称，但这里是具体 CLI 参数值。
- 修法建议：**修改**这一参数为 `--rpc https://api.mainnet-beta.solana.com`。该完整地址也见 `references/data-pipeline-solana-scan.md:14` 及扫描器第 132 行；仅改文本。
- 复现：以下最后一条仅构造请求对象，不发送网络请求；已实测得到上述异常。

```sh
rg -n -- '--rpc api\.mainnet-beta' references/data-pipeline-solana-capture.md
rg -n 'args\.rpcs|SolanaAttestedSession|add_argument\("--rpc"' scripts/solana/scan_token_accounts.py
rg -n 'urllib\.request\.Request|endpoint = endpoint\.strip|self\._endpoints|self\._request_json' scripts/lib/solana_attested_session.py
python3 -B -c 'from urllib.request import Request; Request("api.mainnet-beta", data=b"{}")'
```

### D2 — minor — A 类 — 同一资金溯源案例的金额与“差 8 倍”不一致

- 位置甲：[references/data-pipeline-robinhood-methods.md:20](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-methods.md:20)，原文「Safe 部署者军资表面 464E 实际 1,699E」。
- 位置乙：同文件同一行，原文「差 8 倍——73% 经 Across SpokePool 以 internal 交付」。
- 矛盾点：`1699 / 464 ≈ 3.6616`；即使将“差”解释为增量倍率，`(1699 − 464) / 464 ≈ 2.6616`，也不是 8。漏计占总额的比例约 `72.6898%`，与句中的 73% 相符。这是现行方法册内部的定量矛盾，会让执行者误引该案例的漏计幅度。
- 修法建议：优先**删除**「差 8 倍」；已有两个金额和 73% 足够表达案例，只改文本。
- 复现：

```sh
rg -n '表面 464E|差 8 倍|73%' references/data-pipeline-robinhood-methods.md
python3 -B -c 'from decimal import Decimal as D; a=D(464); b=D(1699); print("total_ratio", b/a); print("increment_ratio", (b-a)/a); print("missing_pct", (b-a)/b*100)'
```

两条存量归因可复现为：

```sh
git show d30864944462ae10db38ff7d3b1caaf9a96f9a01:references/data-pipeline-solana-capture.md | rg -n -- '--rpc api\.mainnet-beta'
git show d30864944462ae10db38ff7d3b1caaf9a96f9a01:references/data-pipeline-robinhood-methods.md | rg -n '表面 464E'
```

## 待确认（不计入 N）

无新增待确认项。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | B 类 | references/data-pipeline-solana-capture.md:61 | scripts/solana/scan_token_accounts.py:191；scripts/lib/solana_attested_session.py:42 | RPC 简称被直接用作 URL，示例参数无法执行 |
| D2 | minor | A 类 | references/data-pipeline-robinhood-methods.md:20 | 同文件同一行 | 464E 与 1,699E 不支持“差 8 倍” |
