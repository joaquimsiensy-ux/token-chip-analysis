# 盲审 R6b：0 条发现

审查基线：`8e54242c5c4e0fd02c5c1a1e1dae4d509b349236`；`main`；`VERSION=9.0.1`；git status 前/后：空/空。

本轮未确认符合纳入标准的新 A 类或 B 类问题，也未确认 R1–R5 修复引入新的不一致。前五轮已修的 22 条去重问题未重复计入。

## 覆盖声明

完成以下 **46 份必审文档、共 6,562 行**的逐文件全文检索及相关规则、契约、示例上下文核读：

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

另审 `CHANGELOG.md` 文件头现行规则、7.2.0—9.0.1 索引及对应详细段；对照 `agents/openai.yaml`、`pyproject.toml`。已读取允许范围内的前五轮报告、工单、完成记录和上一工程裁决台账，用于去重及排除已知例外。

核对词表 **154 项**：阶段、角色与链档位 15 项；门禁与查项 28 项；协议标识 60 项；变更字段 28 项；阈值 7 项；变更生产脚本名 16 项。

检索采用两个方向：

- 从变更脚本名、函数名、字段名反查全部必审文档，核对命中位置的完整语境。
- 从文档中的命令、参数、输入输出、协议、阈值和退出条件回查实现。CLI 对照 `argparse` 和子命令分派；产物对照写入位置；拒收条件对照实际分支。对候选另行排除别名、历史描述、迁移方式及 formal／exploration／legacy 差异。

代码变更范围由以下命令确认：

```sh
git log --oneline 4cbfe48..HEAD -- scripts/
git diff --stat 4cbfe48..HEAD -- scripts/
```

结果为 **38 个变更文件，新增 2,806 行、删除 118 行**。其中 16 个生产脚本均完成变更与文档提及点对照：

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

其余 22 个文件为测试、夹具与清单，已纳入变更检索和相关契约核对。此次为静态审查，未复跑测试套件。

## 代码变更行为核对清单

以下是本路核对的机器行为清单，均未据此确认尚存的文档矛盾。

| 版本 | 已核对的新增或改变行为 |
|---|---|
| **7.2.0** | 图表输入严格处理非有限数值、非数字及布尔值；解析失败、FAIL 收据和退出码分支。严格持仓计入钱包下界，expanded 部分进入 `expanded_economic_control_range_raw` 上界，并校验区间形状及上下界关系。`facts_gate build` 从台账、身份和来源材料派生 facts，生成 `facts-provenance/v1`；正式路径要求 facts，发布与收口重新派生比较。`peak_overrides` 要求证据及绑定，峰值不得低于当前值。峰值摘要绑定补查文件及哈希；合并 needs 与 trigger 对应候选。`replay_duck --only-addrs` 可重复输入、合并地址，只运行区块精度峰值补查，并在首个输入所在目录生成 `block_precision_followup.json`；错误形状或空并集退出 2。 |
| **7.2.1** | G8 消费端重新检查 `tier=exclude` 成员对应的 `INFRA_IN_ENTITY`，不能只靠清除标记通过。发布端重新执行真实 series／facts 的图 2 校验。峰值材料不得分散于多个目录；补查核对当前生产者、通道哈希、数值类型及数量。峰值不得超过总供应；override 证据对象须匹配实体、峰值与日期，日期执行格式及适用的时间上界检查。decimals 增加绑定检查，其后由 8.0.0 改为观测与 accounting 来源。 |
| **8.0.0** | 图 2 对必需实体检查缺线、重复线及标签；空 series 的拒收与是否存在必需实体相关，无必需实体的情形保留允许分支。EVM observation bundle 升至 v2，新增 decimals 调用及 0—255 校验，转录由 8 项增至 9 项。观测值写入 `supply.decimals`，进入 `accounting.checks.decimals`；共享收据和 facts 消费 accounting 值，EVM 对账另核配置一致性；旧 v1 不再接受。 |
| **9.0.0** | `RpcPool` 拒绝非对象及没有有效错误信息却缺少 `result` 的响应；显式 `result: null` 仍交由调用方解释。getcode 只接受带 `0x` 前缀的偶数长度十六进制，非法输入失败；合法空字节码与非空字节码分别分类。价格收据新增 `price_file_sha256`；stage2 核对实际收据、非空点集、状态汇总、来源和文件绑定，接受规定的两种收据引用位置；旧收据及纯声明不能替代，迁移须重新检查后再生成收据。`facts_inputs.circulating_supply` 使用结构化对象并校验数量、日期及来源，派生流通量字段，支持流转图 20% 门槛；旧平铺输入不接受。 |
| **9.0.1** | EVM camp spec 显式配置散户退出 2；Solana 保留不同处理。主价格非有限或非正数在写入和网络查询前退出 1；副价格无有效值进入 SKIP，JSON 禁止输出非有限值。stage2 重新计算各点价格状态及 5%／15% 偏差档位，拒绝状态不一致。价格检查 PASS／WARN、FAIL、ALL_SKIP 的退出码分别保持 0、2、3。 |

## 发现

无。

未将新增字段未写入文档、合法分档差异、历史版本描述或措辞偏好计为漂移。

## 待确认（不计入 N）

无。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| — | — | — | — | — | 本轮 0 条新增发现 |

纪律记录：全程离线，未修改或新建文件，未 commit，未读取 `~/.codex/`。初始一次 `wc -l` 通配操作误将 `references/attic.md` 纳入计数，仅返回其 42 行行数、未展示正文；该偏差已披露，随后显式排除。其余禁读内容未读取。
