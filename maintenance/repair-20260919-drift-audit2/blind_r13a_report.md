# 盲审 R13a：1 条发现

审查基线：`f2c9d421f73a0ddbb6d84f663d4a0e2a24dd3b1d`；git status 前/后：空/空。分支 `main`，`VERSION=9.0.1`。

覆盖声明：逐份审阅以下 46 份必审文档，并审阅 `CHANGELOG.md` 文件头版本规则及活跃窗口 7.2.0–9.0.1 的现行行为描述。

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
CHANGELOG.md（限定范围）
```

术语表共 **246 条**：阶段/门禁 30、schema 25、脚本 33、产物及引用名 88、CLI 选项 41、数值阈值 18、链档位及角色 11。从 SKILL、analyze-workflow、split-run 提取后扩展，在全部必审文档中逐项检索，并回读上下文区分别名、历史案例、正式与探索档。

文档中另提取 145 个 `.py` 名称：131 个定位到仓库脚本，其余为明确标注的外部、案例专属或历史脚本；对 55 组显式 Python 调用及脚本选项片段核对 argparse/分派定义，并追查相关字段、产物路径、默认值和返回分支。对照范围包括 `scripts/`、相关 `scripts/tests/`、`agents/openai.yaml` 与 `pyproject.toml`。重点复核了 7.2.0–9.0.1 的 facts、图 2、价格收据、decimals 观测及序列来源契约。

已检索 R1–R12 两路报告并对照工单、完成记录和修复差异去重；未确认 R1–R11 修复引入的新不一致。全程离线，只读；未访问禁读目录或 attic 正文，未修改、新建文件或 commit。验证采用静态阅读、AST 检查和纯内存复现，未运行会联网或落盘的业务流程。

## 发现（按严重度排序）

### D1 — minor — B 类 — 销户抽样文档将样本无效无条件写成 exit 1，实际漏边优先 exit 2

- 位置甲：[references/data-pipeline-solana-capture.md:96](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:96) 原文「**样本无效机器判据（批 D GPT-F-06 收口，任一命中即 exit 1）**：任一 getMultipleAccounts 批失败／深挖账户全部 fetch_failed／checked=0 且 closed>0／墙钟截断／undetermined 过半。」第 95 行也将 undetermined 过半直接对应 exit 1。
- 位置乙：[scripts/solana/audit_closed_accounts.py:526](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/audit_closed_accounts.py:526)，第 526–529 行原文：

```python
if events["missing"]:
    status, exit_code = "LEAK_FOUND", 2
elif invalid_reasons:
    status, exit_code = "INVALID_SAMPLE", 1
```

同文件 [第 71–74 行](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/audit_closed_accounts.py:71) 在墙钟截断时仅对 `if status not in {"INVALID_SAMPLE", "LEAK_FOUND"}:` 改成 exit 1，明确保留已有 `LEAK_FOUND/2`。

- 矛盾点：同时发现漏边和样本无效时，文档的“任一命中”承诺 exit 1，代码实际返回 `LEAK_FOUND/2`，并保留 `invalid_reasons`。据文档校验或解释该组合结果会错误期待返回码 1；两种结果均不放行，因此定为 minor。
- 修法建议：只改文本，将第 95–96 行的绝对 exit 1 表述收窄为“发现漏边优先 exit 2；否则样本无效 exit 1”，保留现有判据列表；无需改执行逻辑。
- 归因：此前漏报，**非 R1–R11 修复引入**。第 95–97 行及脚本全文与工单内容基线 `3942c23` 相同；前十二轮报告中未检出本条。
- 复现：以下命令只读源码，后者在内存执行现行分支，不启动 RPC 或写文件。

```bash
rg -n -A5 '任一命中即 exit 1|if events\["missing"\]|if status not in' \
  references/data-pipeline-solana-capture.md \
  scripts/solana/audit_closed_accounts.py

python3 -B -c '
import ast
from pathlib import Path
p = Path("scripts/solana/audit_closed_accounts.py")
t = ast.parse(p.read_text())
b = next(n for n in ast.walk(t)
    if isinstance(n, ast.If) and isinstance(n.test, ast.Subscript)
    and isinstance(n.test.value, ast.Name) and n.test.value.id == "events"
    and isinstance(n.test.slice, ast.Constant) and n.test.slice.value == "missing")
for missing in (0, 1):
    ns = {"events": {"missing": missing}, "invalid_reasons": ["墙钟截断"],
          "closed": ["closed-account"]}
    exec(compile(ast.Module(body=[b], type_ignores=[]), str(p), "exec"), ns)
    print(missing, ns["status"], ns["exit_code"])
'
```

实测结果：

```text
0 INVALID_SAMPLE 1
1 LEAK_FOUND 2
```

另在内存调用现行 `_build_report()`，确认第二种情况最终仍为 `LEAK_FOUND/2`，同时保留 `wall_truncated=true` 和墙钟截断原因。

## 待确认（不计入 N）

无新增待确认项。此前已记录的待确认事项与已裁决例外不重复列报。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | B 类 | references/data-pipeline-solana-capture.md:95–96 | scripts/solana/audit_closed_accounts.py:526–529、71–74 | 样本无效的 exit 1 承诺缺少漏边优先 exit 2 的条件 |
