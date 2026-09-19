# 盲审 R3b：0 条发现

审查基线：`c22d102aa4f59ee647def2b63d55e24f96316097`；`git status --short` 前/后：空/空。分支 `main`，`VERSION=9.0.1`。

未发现满足双侧原文实证要求的新 A 类或 B 类问题；未发现 R1/R2 修复引入的新不一致。前两轮已修的 12 条未重复计入。

## 覆盖声明

本轮采用代码变更区反向核对：

- 已检查 `git log --oneline 4cbfe48..HEAD -- scripts/`、`git diff --stat 4cbfe48..HEAD -- scripts/`：共 **38 个变更文件**，其中生产代码 16 个、测试及登记文件 22 个；增删量为 `2806 insertions / 118 deletions`。
- 对变更脚本名、函数名、新增字段和拒收条件，在显式文档白名单内全文检索，再回读命中位置与现行实现。CLI 对照 `add_argument`、`add_parser` 和分派逻辑；产物对照路径常量及写出语句；schema 对照生产者与消费者。
- 术语对照表 **88 项**：协议、schema 及公式版本 61 项，阶段与门禁术语 27 项。另对 **89 处带 CLI 选项的文档引用**做了参数名称静态核对，并人工复核重点命令的子命令、默认值和条件。
- 已核对 R1/R2 工单、完成报告及实际补丁 `07c97d6`、`0a53cbd`；排除历史叙述、合法别名、formal/exploration/legacy 差异，以及“代码新增但文档未承诺”的情况。
- 未复跑题设已通过的机器守卫；本轮结论来自离线静态审查。

逐文件覆盖如下；均作全文检索，重点册另作字段、参数和行为逐项核对：

```text
SKILL.md
CHANGELOG.md（版本规则头、7.2.0—9.0.1 索引及指定五版详细段）

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

另已对照 `agents/openai.yaml`、`pyproject.toml`。重点代码覆盖包括 `scripts/report/*` 分段命令、`scripts/solana/*` 参数及产物、`scripts/labels/*` 查询与维护流程。

## 代码变更区核对清单

以下为从指定版本提取并核过的机器行为，不计作发现。

| 版本 | 核过的新增或改变行为 |
|---|---|
| 7.2.0 | 图 2 拒绝非有限数值，并区分对账失败与前置解析失败的收据写出条件；strict/expanded 分账，expanded 只进入经济控制上限；`facts_gate build` 从三账、identity、provenance 和 `state_source.facts_inputs` 生成 facts，附 `facts-provenance/v1`，发布及 closeout 重算；日级峰值产物递归定位、needs 哈希绑定；可重复 `--only-addrs` 生成 `block-precision-followup/v1`，覆盖并集地址、写首个输入目录、跳过全量产物，非法或空输入 exit 2。 |
| 7.2.1 | G8 消费侧按 `tier=exclude` 重推 `INFRA_IN_ENTITY`；图 2 发布期按实际输入重算；summary/needs/followup 任一可定位峰值目录，followup 核当前 producer、唯一 channels、整数类型与数量；facts 峰值上界、override 证据形状及值相等、严格日期与当前锚点日期约束；decimals 观测绑定。 |
| 8.0.0 | 图 2 必画标签前缀、缺线及重复线拒收，closeout 复用规则；非必画集合为空的既有分支与必画实体缺线分开核对；EVM observation 升 v2，增加 `decimals()`，transcript 为 9 笔，新增 `supply.decimals`，accounting 写 `checks.decimals`，消费侧核 bundle、facts 和 EVM config。 |
| 9.0.0 | RPC 缺 `result` 键判失败；getcode 仅接受 `0x` 或偶数长度十六进制串，异常 exit 1；价格收据读取 points 重算 verdict，仅接受 PASS/WARN，强制 `price_file_sha256` 与工单价格源绑定，内联声明须带 receipt；新增结构化 `facts_inputs.circulating_supply`，拒绝扁平输入，校验数量、日期和来源。 |
| 9.0.1 | EVM camp spec 拒绝显式“散户”，Solana 分档保留；主价格任一点非有限或非正时 fatal exit 1，第二源非有限值转为 SKIP，收据禁 NaN；closeout 逐点重算 deviation/status 并核声明。 |

重点补查结果：

- `scan-schemas.md` 的版本、字段形状与条件必填规则未形成新的确定矛盾。
- `stage2_closeout` 支持省略 `check` 的兼容入口，不能将分段文档中的该写法报成不存在的子命令。
- Solana 参数、质押账本 `≤2 raw` 容差及相关产物名与所读实现一致。
- labels 的冲突过滤发生在生成 `serial_actors.csv` 之前，自动及手动入库消费同一过滤结果；不能据 `add_labels` 内没有重复过滤逻辑报漂移。
- `environment.md` 与 pyproject、复盘草稿及脚本分叉盘点命令未见新的确定冲突。

## 发现

无。

## 待确认（不计入 N）

无保留项。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| — | — | — | — | — | 本轮 0 条新增发现，未发现 R1/R2 修复引入的新不一致。 |

执行纪律披露：全程离线，未修改或新建文件，未 commit，未读取 `~/.codex/` 或其中 memories。发生过一次禁读范围操作失误：`wc` 通配符将 `references/attic.md` 纳入行数统计，返回 42 行，未展示正文；当时已披露，随后改用显式白名单，未再次读取该文件。
