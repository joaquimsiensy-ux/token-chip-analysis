# 盲审 R9a：1 条发现

审查基线：`bf202667c80cfb59a40404d9d59b50461d91ff30`；分支 `main`；`VERSION=9.0.1`；git status 前/后：空/空。

全程离线、只读；未修改或新建文件，未 commit。未读取 `~/.codex/`、memories 或其他禁读区，未读取 `attic.md` 正文。完整报告已打印到 stdout。

覆盖声明：逐份读取下列 46 份必审文档，共 6,562 行；另审 CHANGELOG 文件头规则及 7.2.0–9.0.1 活跃索引的现行行为描述。核心术语表 **231 项**：阶段 11、门禁 16、schema 21、脚本 33、参数 41、产物 66、子命令 15、数字阈值 16、链/档位/角色 12。

检索策略：从 SKILL、analyze-workflow、split-run 提取并展开术语，用 `rg -n -F` 对必审文件交叉检索；补查脚本、命令、字段、阈值和产物描述。核对文档点名的 130 个现存脚本，解析 `scripts/` 下 310 份 Python 文件的 AST，对候选读取参数定义、实际分派、写出点和消费者；同时核对 `agents/openai.yaml`、`pyproject.toml`。已对照 R1–R8 报告、工单和完成记录去重，排除历史描述、合法别名、明确分档差异及已裁决的 wave_scan 浮点阈值例外。

逐文件清单：

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
CHANGELOG.md（第 1–17 行限定范围）
```

## 发现（按严重度排序）

### D1 — blocker — B 类 — 已交付报告补监控包的正式重封指引，会被分布终态检查拒绝

- 位置甲：[references/monitoring-package.md:117](/Users/uravvv/.claude/skills/token-chip-analysis/references/monitoring-package.md:117) 原文「若要维持正式身份，必须把 `appendix.json` 加入 `a4_gate.py finalize --seal-files ...` 重新封口」。第 110 行明确触发条件为「用户在报告交付后表示"买入了 / 决定买 / 要监控 XX"」。
- 位置乙：[scripts/report/a4_gate.py:285](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/a4_gate.py:285) 原文「`if ledger.get("terminal") is not None:`」；第 286 行紧接「`fails.append("distribution rounds 已到 terminal，禁止再次 A4 finalize")`」。第 387 行在 finalize 中调用此检查，第 434–438 行在存在失败项时返回 `2`。
- 矛盾点：新分析报告交付时已经完成分布终判；文档却指引先直接再次 finalize、随后才继续原工作流，执行到重封就会被拒绝，无法按该顺序补出正式监控版。
- 反向核验：[references/analyze-workflow.md:188](/Users/uravvv/.claude/skills/token-chip-analysis/references/analyze-workflow.md:188) 要求进入 A5 前「分布轮次已到唯一终态，终版分布图已物化」；[references/split-run.md:136](/Users/uravvv/.claude/skills/token-chip-analysis/references/split-run.md:136) 明确「重封一律 `stage2_closeout reseal`」。该入口在 [scripts/report/stage2_closeout.py:1022](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:1022) 先执行 `reopen-cycle`，第 1239 行才调用 A4 finalize。发现限定于已交付的 `new-analysis` 正式路径；代码第 276–277 行排除了 `independent-audit`。
- 验证：从现行源码提取 `distribution_claim_source`，仅在内存模拟已有 terminal，实际返回失败项「distribution rounds 已到 terminal，禁止再次 A4 finalize」。这是函数级复现，未执行会落盘的业务命令。
- 修法建议：**修改文本，无需改代码。** 删除统一的直接 finalize 指引，改为引用原工作流的终态重开及重封流程；分段新分析使用 `stage2_closeout.py reseal --from a4`，在保留原额外封口文件的基础上纳入 `appendix.json`，随后完成原 A5 流程。净室复核保留其自身重封路径。
- 修复归因：**非 R1–R8 修复引入。** R1 审查基线 `d30864944462ae10db38ff7d3b1caaf9a96f9a01` 的同一行已经包含该指引。R7 修的是默认 legacy 重编译缺 `--facts`，与本条正式重封的终态冲突不同；[r7_done.md:74](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260919-drift-audit2/r7_done.md:74) 的改前/改后原文可核实正式分句未变。
- 复现：在仓库根目录执行以下只读命令。

```sh
rg -n -F -e '报告交付后' -e 'a4_gate.py finalize --seal-files' references/monitoring-package.md
rg -n -A 13 'def distribution_claim_source' scripts/report/a4_gate.py
rg -n -A 4 -e 'distribution_source = distribution_claim_source' -e '^    if fails:' scripts/report/a4_gate.py
rg -n -F '分布轮次已到唯一终态' references/analyze-workflow.md
rg -n -F '重封一律' references/split-run.md
rg -n -A 2 -F -e 'reseal_require(case, "holder_distribution_scan.py", "reopen-cycle"' -e 'reseal_require(case, "a4_gate.py", "finalize"' scripts/report/stage2_closeout.py
git show d30864944462ae10db38ff7d3b1caaf9a96f9a01:references/monitoring-package.md | rg -n -F 'a4_gate.py finalize --seal-files'
```

函数级复现：

```sh
python3 -B -c '
import ast, json
from pathlib import Path
p = Path("scripts/report/a4_gate.py")
fn = next(n for n in ast.parse(p.read_text()).body
          if isinstance(n, ast.FunctionDef) and n.name == "distribution_claim_source")
class MemoryPath:
    def __init__(self, *parts): pass
    def __truediv__(self, other): return self
    def is_file(self): return True
    def read_text(self, **kwargs):
        return json.dumps({"rounds": [], "terminal": {"status": "NORMAL", "round_n": 1}})
scope = {"Path": MemoryPath, "json": json}
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(p), "exec"), scope)
errors = []
scope["distribution_claim_source"]("/memory-only", "new-analysis", [], errors)
print(json.dumps(errors, ensure_ascii=False))
'
```

输出：`["distribution rounds 已到 terminal，禁止再次 A4 finalize"]`。

## 待确认（不计入 N）

无。未确认 R1–R8 修复本身引入新的 A/B 类不一致。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | blocker | B 类 | monitoring-package.md:117 | a4_gate.py:285 | 已交付新分析直接再次 finalize，被分布终态检查拒绝 |
