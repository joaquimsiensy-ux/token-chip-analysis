# 盲审 R7b：1 条发现

审查基线：`fc704dee8cd6cbec60bc4cabf4caffc5674ddd81`；git status 前/后：空/空。

分支 `main`，`VERSION=9.0.1`。本轮确认 **1 条 A 类 nit**；blocker、minor、B 类均为 0。未确认 R1–R6 修复引入的新不一致。

覆盖声明：46 份必审文档，共 6,562 行，逐文件全文检索并回读规则、示例和关联上下文；另审 CHANGELOG 的版本规则及指定五版索引、详细段，对照 `agents/openai.yaml`、`pyproject.toml`。术语／字段索引 129 项：阶段 10 项、门禁及退出码 19 项、协议及版本标识 64 项、字段／产物／角色／阈值等 36 项。

全程离线、只读；报告全文已打印到 stdout，未新建或修改文件、未 commit。未读取 `~/.codex/` 或 memories，未读取所列禁读目录及 attic 正文。maintenance 仅使用本工程目录和获准的上一轮裁决台账。

## 发现（按严重度排序）

### D1 — nit — A 类 — Solana 流水追踪小节标题宣称三个坑，正文实际列出九个

- 位置甲：[references/data-pipeline-solana-scan.md:119](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:119) 原文「### 3a. 流水追踪的三个 Solana 特有坑」。
- 位置乙：[references/data-pipeline-solana-scan.md:129](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:129) 原文「9. **CEX 精确注资型定投**：可写交易所提币后定投画像；资金源在 CEX 截断时不得确证独立或项目方归属。判例见 casebook C-07。」
- 矛盾点：同一小节在第 121–129 行连续列出 1–9 九项，第 131 行才进入下一小节；标题数量与正文不一致，使读者误判检查项数量，但不影响命令执行。
- 修法建议：只删除标题中的「三个」，改为「### 3a. 流水追踪的 Solana 特有坑」。无需改代码。
- 来源判定：该文件与 `4cbfe48` 版本逐字相同，因此不是 R1–R6 修复引入；前六轮报告、工单及完成报告未检出该计数问题。
- 复现：在仓库根目录运行以下只读命令。

```sh
nl -ba references/data-pipeline-solana-scan.md | sed -n '119,131p'
python3 -B -c 'from pathlib import Path; import re; s=Path("references/data-pipeline-solana-scan.md").read_text().split("### 3a.",1)[1].split("### 3b.",1)[0]; a=re.findall(r"(?m)^([0-9]+)\. ",s); print(a); print("count =",len(a))'
git diff --exit-code 4cbfe48 HEAD -- references/data-pipeline-solana-scan.md
```

实测编号为 `['1','2','3','4','5','6','7','8','9']`，数量为 `9`；该文件历史差异为空。

## 覆盖明细

以下文件均已逐份审查：

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

grep 策略：先用 `rg -n` 检索阶段、门禁、版本、阈值、产物名和命令；再按变更脚本 basename、函数名及字段名双向检索上述明确文件清单，回读命中段。CLI 对照 argparse／分派表，产物对照写入点，字段和退出条件对照当前实现及相关测试断言。每个候选再检查历史语境、别名和 formal／exploration／legacy 条件，并与前六轮条目及已裁决例外去重。

### 代码变更区专审

已执行：

```sh
git log --oneline 4cbfe48..HEAD -- scripts/
git diff --stat 4cbfe48..HEAD -- scripts/
```

差异共 **38 个文件，新增 2,806 行、删除 118 行**。其中以下 16 个生产脚本均已检查变更及文档提及点；其余 22 个测试、fixture、manifest 文件已检查相应断言或登记变化：

```text
scripts/evm/accounting_gate.py
scripts/evm/observe_supply.py
scripts/evm/peaks_daily.py
scripts/evm/replay_duck.py
scripts/lib/camp_spec.py
scripts/lib/evm_observation.py
scripts/lib/net.py
scripts/lib/rpc_batch.py
scripts/lib/supply_truth_gate.py
scripts/prices/price_check.py
scripts/report/audit_release_gate.py
scripts/report/entity_identity_gate.py
scripts/report/facts_gate.py
scripts/report/figures_from_facts.py
scripts/report/shared_release_receipt.py
scripts/report/stage2_closeout.py
```

同时复查 `bc19e2b..HEAD` 在上述文档和 CHANGELOG 中的 R1–R6 修复差异，未发现新增矛盾。本轮采用静态对照和无写入的文本复算，未复跑机器守卫或案卷发布流程。

### 五版机器行为核对清单

以下为核对项，不计入发现；较早版本已被后续版本替代的行为按历史描述处理。

**7.2.0**

- 图 2：拒绝非法类型及非有限数；解析失败时，仅在两输入文件在场的条件下尝试写 FAIL 收据；保留原有不产收据的结构错误分支；序列序列化禁止 NaN。
- 三账：严格成员计入自持，扩展成员计入上限；有扩展成员时要求 `expanded_economic_control_range_raw`，下限等于重算 confirmed，上限至少覆盖 expanded。
- facts：新增 `facts_gate.py build`，从三账、identity、provenance、`state_source.facts_inputs` 生成；formal 缺峰值来源或 peak 小于 current 拒绝；override 要求证据绑定；输出 `facts-provenance/v1`、`facts_binding=ledger-derived`。new-analysis 必须有 facts，并与 stage2 共用派生逻辑重算；同时核对非有限 JSON、人工字段类型及输入绑定。
- 日级峰值：递归定位产物，校验 needs 哈希与候选覆盖；`--only-addrs` 支持重复传入 needs、trigger 或地址列表并取并集，在首个输入目录写 `block-precision-followup/v1`；正峰值须有非负整数区块，零峰值对应 null；补算不覆写全量 pass1／merged／pass2，坏形状或空并集退出 2。

**7.2.1**

- 身份闸：实体成员带 `tier=exclude` 时重推 `INFRA_IN_ENTITY` 义务，清空 flag 不能消除义务。
- 图 2：发布时按已绑定的 facts、series 实物重新校验，收据自报 PASS 不替代计算。
- 峰值：summary／needs／followup 任一文件用于定位目录；多目录或缺 summary 拒绝。followup 绑定当前引擎 SHA、案内唯一 channels 实物及哈希，校验 `value_type` 和 `count`。
- facts：`peak_raw≤total_raw`；override 证据要求 `{entity_id:{peak_raw,peak_date}}` 且值相等；日期严格 ISO，并受显式当前锚点日期约束。该版 decimals 来源随后由 8.0.0 改为真实观测值。

**8.0.0**

- 图 2：项目方／大庄／小庄／离场庄前缀的实体必须各有一条线，缺线和重复线拒绝；没有必画实体的空 series 仍有明确例外，未误报为漂移。
- EVM 观测：bundle 升为 v2，旧 v1 拒收；补 `decimals()`，transcript 为 9 笔，值按 uint8 校验；写入 `supply.decimals`，accounting 写 `checks.decimals`，shared receipt 核两者一致。发布闸两链族统一读取 accounting decimals，并额外核 EVM config 一致。
- 迁移：观测、供给真值及 shared receipt 生产者变化影响旧绑定；按当前生产者重建相关收据与下游封口，单改版本字段不能替代迁移。

**9.0.0**

- RPC：缺 `result` 键判失败；显式 `result:null` 仍通过 envelope 层，由方法消费者判断类型。getcode 仅接受 `0x` 或偶数长度十六进制字节串；坏值记录 error，退出 1。
- 价格收据：要求非空 points，重算汇总 verdict，只放行 PASS／WARN，WARN 留 NOTE；要求 `price_file_sha256` 与主源绑定一致；内联 `dual_source_check` 必须有 receipt 引用。旧收据、纯申报、FAIL、ALL_SKIP 不能进入收口。
- 流通量：可选 `facts_inputs.circulating_supply {raw,asof,source}`，要求 `0<raw≤total`、严格日期及非空来源；拒绝错位的扁平键。输出 token 的两项流通量字段，使既有流通量分母下的必画判断可触发，并进入重算比对和 NOTE。

**9.0.1**

- camp spec：EVM 显式「散户」桶退出 2；Solana 保留不同处理条件，未据此报跨链矛盾。
- 价格：主源任一点非有限或非正，在写收据前 fatal 退出 1；第二源非有限规范化为 null／SKIP；收据禁止 NaN。stage2 按两价格逐点重算状态，以四舍五入后的对称偏差对照 5%／15% 阈值，再核申报状态及汇总 verdict。

## 待确认（不计入 N）

无保留的待确认候选。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | nit | A 类 | data-pipeline-solana-scan.md:119 | 同文件:121–129 | 标题写三个，正文列九个；删除标题数量即可。 |
