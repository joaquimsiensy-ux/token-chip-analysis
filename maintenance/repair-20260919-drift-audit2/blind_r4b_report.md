# 盲审 R4b：2 条发现

审查基线：`8d92dae2943d2018291516ec38b0db0dfaacd4ad`；`main`；`VERSION=9.0.1`；git status 前/后：空/空。

两条均为 **minor、B 类**，位于 Robinhood exploration 文档及对应脚本。相关文件自 `4cbfe48` 起未改，均非 R1–R3 修复引入。代码增量反查未发现其他确定漂移。

全程离线、只读，未新建或修改文件；未读取 `~/.codex/`、其他禁读目录或 `attic.md` 正文。

覆盖声明：

- 对以下 **46 份现行文档**全文检索，并回读命中段及对应代码；另审 `CHANGELOG.md` 头部规则、五版索引和详细段。
- 术语索引 **84 项**：55 个协议/格式标识、26 个阶段/门禁名称、3 个分段编号（−1/−2/−3）。另逐项追踪新增字段、CLI、产物名及阈值。
- 已用指定 `git log`、`git diff --stat` 核实增量：**38 个文件，16 个生产脚本、22 个测试/夹具/清单文件，+2806/−118**。逐文件检索文档提及点，再以函数、字段及中文旧行为描述反查。
- 重点核对非 SQD schema 的字段、必填/可空条件、生产者常量；聚类、判级、状态与经济控制规则；判例互引；monitoring、LP、research、labels 与 Robinhood 脚本。并读取 `agents/openai.yaml`、`pyproject.toml`。
- 已对照前三轮报告、工单、完成报告及修复段，排除已修 15 项和已裁决 wave 浮点阈值例外。验证采用静态对照及源码表达式的内存复现，未运行会落盘的测试。

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
```

代码变更区核对账如下；这些是已核对的变化，不计为发现：

| 版本 | 新增或改变的机器行为 |
|---|---|
| 7.2.0 | 图 2 拒非有限值，输入解析失败分支尝试写 FAIL 收据；strict/expanded 分账及扩展区间约束；facts 自三账生成、`facts-provenance/v1`、发布重算及 stage2 第 12 项检查；递归定位日峰产物、needs 哈希绑定；`--only-addrs` 并集补算、`block-precision-followup/v1`、首输入目录落盘、无事件 0/null、异常输入 exit 2。 |
| 7.2.1 | `tier=exclude` 消费侧重推 `INFRA_IN_ENTITY`；图 2 发布期实物重算；summary/needs/followup 三定位、缺 summary/多根拒收，followup 核 producer、channels、value_type、count；峰值上界、override JSON 形状和值、严格日期与当前日期约束；decimals 核验。 |
| 8.0.0 | 图 2 四种标签前缀的必画集合、缺线/重复线拒收；无必画实体的空集合分支另核；EVM observation v2、冻结块 `decimals()`、uint8、9 笔 transcript、旧 v1 拒收；`supply.decimals`、`accounting.checks.decimals`、facts/config 交叉核验。 |
| 9.0.0 | RPC 缺 `result` 判失败，显式 null 留给方法消费者处理；getcode 仅认合法偶数十六进制，坏结果 exit 1；价格收据非空 points、verdict 重算、PASS/WARN 限制、`price_file_sha256` 及 receipt 引用；`facts_inputs.circulating_supply {raw,asof,source}` 派生输出，扁平错位键拒收。 |
| 9.0.1 | EVM 显式「散户」配置 exit 2，Solana 分档不误套；主价格非有限/非正 fatal exit 1；第二源非有限转 null/SKIP，禁止序列化 NaN；closeout 按价格逐点重算 status，再核汇总 verdict。 |

## 发现（按严重度排序）

### D1 — minor — B 类 — 成本脚本未按配置保留 `decimals=0`

- **位置甲**：[references/data-pipeline-robinhood-channels.md:30](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-channels.md:30) 原文：「本币和报价币分别使用 config 的 `decimals` / `quote_decimals`，不得再写死 18」。
- **位置乙**：[scripts/robinhood/cost_engine.py:17](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/robinhood/cost_engine.py:17) 原文：「`dec = int(cfg.get('decimals') or 18)`」。第 71 行再用「`"tok": float(raw_to_units(tb, dec))`」生成数量。
- **矛盾点**：配置中的数值 `0` 会被 `or 18` 覆盖。直接执行当前源码表达式，`decimals=0` 得到有效精度 18，`1000 raw` 被换算为 `1e-15`，不是 1000 枚；同一精度还用于第 19、84 行的供应量筛选门槛。按文档直接消费会得到错误数量。
- **反向验证**：同脚本第 18 行对 `quote_decimals` 使用显式 `is not None`，能保留 0；本币路径没有后续恢复。分册第 5 行明确限定 exploration，因此这是同档内部的不符，定为 minor。
- **修法建议**：**修改**现有说明，限定本币 `decimals=0` 当前不适用，删除无条件“分别使用 config”承诺；无需新增章节。
- **复现**：以下只读源码并在内存求值：

```bash
rg -n 'config 的' references/data-pipeline-robinhood-channels.md
rg -n 'dec =|TOTAL =|raw_to_units\(tb|TOTAL \* MIN_SHARE' scripts/robinhood/cost_engine.py
python3 -B -c '
import ast
from pathlib import Path
p = Path("scripts/robinhood/cost_engine.py")
n = next(n for n in ast.parse(p.read_text()).body
         if isinstance(n, ast.Assign)
         and any(isinstance(t, ast.Name) and t.id == "dec" for t in n.targets))
d = eval(compile(ast.Expression(n.value), str(p), "eval"), {"cfg": {"decimals": 0}})
print("effective_decimals =", d, "1000_raw_units =", 1000 / 10**d)
'
```

实测输出：`effective_decimals = 18 1000_raw_units = 1e-15`。

### D2 — minor — B 类 — LP 事件字段被描述为“枚”，实际固定按 `raw/1e18` 输出

- **位置甲**：[references/data-pipeline-robinhood-channels.md:33](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-channels.md:33) 原文：「Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（WETH 枚/本币枚），不是 wei」。
- **位置乙**：[scripts/robinhood/pull_lp_events.py:92](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/robinhood/pull_lp_events.py:92) 原文：「`"amount0": a0 / 1e18, "amount1": a1 / 1e18,`」。第 112 行将这个 `out` 直接 `json.dump` 到输出文件。
- **矛盾点**：浮点类型属实，但“本币枚”的单位承诺仅在对应币精度为 18 时成立。若本币精度为 6，一枚对应的 `1000000 raw` 被输出为 `1e-12`；按文档直接当枚汇总，会少算 12 个数量级。
- **反向验证**：第 79–84 行从事件读取整数原始量，第 37–40 行配置读取没有 decimals，第 92 行两腿固定缩放，写出前没有精度校正。该条位于当前“可复用脚本”用法说明；其中历史 WETH 实测不能证明其他精度也已换算为枚。
- **修法建议**：**修改**现有单位括注为“固定按 raw/1e18 输出；仅 18 位币可直接按枚使用”，替换原来的无条件单位描述。
- **复现**：

```bash
rg -n 'amount0/amount1' references/data-pipeline-robinhood-channels.md
nl -ba scripts/robinhood/pull_lp_events.py | sed -n '79,112p'
python3 -B -c '
import ast
from pathlib import Path
p = Path("scripts/robinhood/pull_lp_events.py")
tree = ast.parse(p.read_text())
expr = next(v for n in ast.walk(tree) if isinstance(n, ast.Dict)
            for k, v in zip(n.keys, n.values)
            if isinstance(k, ast.Constant) and k.value == "amount0")
print(eval(compile(ast.Expression(expr), str(p), "eval"), {"a0": 10**6}))
'
```

实测输出：`1e-12`；6 位精度下对应的实际数量为 1 枚。

## 待确认（不计入 N）

无保留项。未将新能力缺少文档、历史版本状态、合法分档差异或措辞偏好计入发现。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | B 类 | references/data-pipeline-robinhood-channels.md:30 | scripts/robinhood/cost_engine.py:17 | 配置精度 0 被回退为 18，与按配置换算的承诺不符 |
| D2 | minor | B 类 | references/data-pipeline-robinhood-channels.md:33 | scripts/robinhood/pull_lp_events.py:92 | 固定 raw/1e18 的字段被无条件描述为代币“枚” |
