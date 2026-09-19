# 盲审 R10b：0 条发现

审查基线：`435345448c31b02d9798fcc89e9216754cde5df8`；git status 前/后：空/空  
分支：main；VERSION：9.0.1。

本轮未确认前九轮之外的新 A 类或 B 类问题，也未确认由 R1–R9 修复引入的新不一致。报告全文已打印到 stdout。

## 覆盖声明

完成下列 **46 份必审文档、6,562 行**的全文静态扫描，并对现行规则、命令和机器契约命中点作交叉核对：

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
references/casebook/cex-custody-methods.md
references/casebook/cex-custody.md
references/casebook/entity-clustering-methods.md
references/casebook/entity-clustering.md
references/casebook/supply-accounting-methods.md
references/casebook/supply-accounting.md
references/labels/README.md
references/labels/MAINTENANCE.md
commands-staging/token-analyze.md
commands-staging/token-analyze-1.md
commands-staging/token-analyze-2.md
commands-staging/token-analyze-3.md
```

另核对了 `CHANGELOG.md` 文件头规则、指定五版索引及详细段，以及 `agents/openai.yaml`、`pyproject.toml`。读取允许范围内的 R1–R9 报告、工单与完成记录作去重；上一工程已裁决的 wave_scan 浮点阈值例外未重报。

术语表共 **118 条**：阶段 11 条、门禁及退出语义 19 条、schema／协议版本 60 条、口径／字段／阈值 28 条；另提取 **415 个不同 JSON 字段名**作代码检索。

### 代码变更区覆盖

已执行：

```bash
git log --oneline 4cbfe48..HEAD -- scripts/
git diff --stat 4cbfe48..HEAD -- scripts/
git diff --name-only 4cbfe48..HEAD -- scripts/
```

变更清单共 **38 个文件**：16 个运行时代码文件、22 个测试／fixture／manifest 文件。运行时代码核对范围：

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

检索策略：以变更脚本名、函数名及字段名反查全部必审文档，再从文档中的 CLI、schema、产物名、默认值和退出条件反查代码。参数核对 argparse 及手工 `sys.argv` 分派，产物核对写出路径；候选均复查历史语境、合法别名与 formal／exploration／legacy 分档。

五版机器行为核对摘要：

| 版本 | 已核对的行为 |
|---|---|
| 7.2.0 | 图 2 非有限值及非法数值类型拒收、失败收据适用边界；expanded 下限／上限分离；facts 自三账构建及 `facts-provenance/v1` 绑定、发布与收口重推；日级峰值补查覆盖、证据绑定及 `block-precision-followup/v1` 产出。 |
| 7.2.1 | `tier=exclude` 重推 `INFRA_IN_ENTITY`；发布期读取实物重算图 2；峰值产物定位、目录唯一性、followup 生产者与输入哈希绑定；峰值供应上限、override 内容、日期及 decimals 约束。 |
| 8.0.0 | 图 2 必画实体覆盖、重复线／漏线拒收；存在必画实体时空 series 拒收；冻结块 `decimals()` 观测、observation bundle v2、旧 v1 拒收，以及 bundle／accounting／facts／config 的 decimals 对账。 |
| 9.0.0 | RpcPool 缺 `result` 判失败；getcode 严格十六进制形状；价格收据实物、来源及 `price_file_sha256` 绑定，FAIL／ALL_SKIP／旧式自报拒收；`facts_inputs.circulating_supply{raw,asof,source}` 输入校验、产出及流转图门槛消费。 |
| 9.0.1 | EVM 显式“散户”桶退出 2；主价格非有限或非正值退出 1，第二源非有限值转 SKIP；收据禁 NaN；`price_receipt_errors` 逐点重算并核对状态和汇总 verdict。 |

另覆盖阶段与角色分工、四查／五查、EF／ET／G8–G11、链支持档位、章节与案例编号、供给与经济控制口径、图表分母、监控重封及维护命令。

本轮全程离线、只读；未新建或修改文件，未 commit，未读取 `~/.codex/`、memories、禁读目录或 `attic.md` 正文。代码及测试作静态对照，未复跑所列机器守卫。

## 发现

无。未将新增能力缺少文档、人工模板字段未由脚本生成、合法分档差异或已修条目计为发现。

## 待确认（不计入 N）

无。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| — | — | — | — | — | 0 条新发现，未确认 R1–R9 修复引入新的不一致。 |
