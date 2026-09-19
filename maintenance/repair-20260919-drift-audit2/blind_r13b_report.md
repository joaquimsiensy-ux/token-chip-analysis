# 盲审 R13b：0 条发现

审查基线：`f2c9d421f73a0ddbb6d84f663d4a0e2a24dd3b1d`；git status 前/后：空/空。  
分支：`main`；VERSION：`9.0.1`；审查前后 HEAD 一致。

本轮未发现符合收录标准的新 A 类／B 类问题，也未确认 R1–R11 修复引入的新不一致。前十二轮已报并已修条目不重报。

## 覆盖声明

已对下列 **46 份必审文档、6,562 行**逐文件进行全文检索，并审读规则、机器行为承诺及候选上下文。术语表共 **149 个去重检索项**，包含阶段、门禁、协议、脚本／函数、字段、产物、阈值及角色；产生 **829 个“检索项×命中行”记录**。

| 序号 | 文档 | 核对内容 |
|---|---|---|
| 1 | `SKILL.md` | 阶段、冻结门禁、支持档位、禁读身份 |
| 2 | `references/address-book.md` | 身份语义、机制注释、判例引用 |
| 3 | `references/analysis-playbook.md` | 三问一异常、判级与口径 |
| 4 | `references/analyze-workflow.md` | A0–A6、正式记账、四查／五查 |
| 5 | `references/context-discipline.md` | 角色分工、交接与恢复 |
| 6 | `references/data-pipeline-evm-channels.md` | 采集、续采、参数与产物 |
| 7 | `references/data-pipeline-evm-recon.md` | 观测包、供给、峰值与补算 |
| 8 | `references/data-pipeline-evm-sources.md` | 数据源、调用方式、链档位 |
| 9 | `references/data-pipeline-evm.md` | 总册规则与支持边界 |
| 10 | `references/data-pipeline-robinhood-channels.md` | 探索脚本、金额单位与参数 |
| 11 | `references/data-pipeline-robinhood-methods.md` | 资金溯源及修复数字 |
| 12 | `references/data-pipeline-robinhood-traps.md` | 设施、身份、LP 与归因 |
| 13 | `references/data-pipeline-robinhood.md` | 总册规则与支持边界 |
| 14 | `references/data-pipeline-solana-capture.md` | 快照、采集、覆盖、修复与重建 |
| 15 | `references/data-pipeline-solana-scan.md` | GPA、G8、解码与扫描 |
| 16 | `references/data-pipeline-solana.md` | 总册规则与支持边界 |
| 17 | `references/economic-control-accounting.md` | 三账、strict／expanded、确权 |
| 18 | `references/environment.md` | 运行环境、网络内核、CLI |
| 19 | `references/independent-audit-protocol.md` | 复核 profile、三账、收据与发布 |
| 20 | `references/lp-fee-accounting.md` | 费用四分法、单位与产物 |
| 21 | `references/maintenance-review-repair.md` | 维护工序、验收及命令引用 |
| 22 | `references/monitoring-package.md` | 附录 schema、重编译与正式重封 |
| 23 | `references/playbook-entity-cluster-cost.md` | 成本、流量／存量与工具 |
| 24 | `references/playbook-entity-cluster-methods.md` | 构边、身份、冻结及扫描 |
| 25 | `references/playbook-entity-cluster-tiering.md` | 标签门槛、峰值、ET、阵营 |
| 26 | `references/playbook-evidence-wording.md` | 证据等级、事实源与传播 |
| 27 | `references/playbook-state-anomaly.md` | 状态、异常、归因与工具 |
| 28 | `references/playbook-supply-recon.md` | 供应分母、记账及对账 |
| 29 | `references/report-template.md` | facts／state、图表、价格、发布 |
| 30 | `references/research-workflows.md` | 角色、复核产物与装配 |
| 31 | `references/retrospective.md` | 复盘命令、产物与回归引用 |
| 32 | `references/scan-schemas.md` | 字段、协议版本、输入输出与拒收 |
| 33 | `references/split-run.md` | −1／−2／−3、交接、收口与重封 |
| 34 | `references/casebook/README.md` | 判例索引与使用边界 |
| 35 | `references/casebook/cex-custody-methods.md` | 托管证据与方法口径 |
| 36 | `references/casebook/cex-custody.md` | 托管判例与规则指针 |
| 37 | `references/casebook/entity-clustering-methods.md` | 聚类方法与反例边界 |
| 38 | `references/casebook/entity-clustering.md` | 聚类判例、确权与设施 |
| 39 | `references/casebook/supply-accounting-methods.md` | 供应核算方法与指针 |
| 40 | `references/casebook/supply-accounting.md` | 供应、去重、重放与图表 |
| 41 | `references/labels/README.md` | resolver、标签语义与接入 |
| 42 | `references/labels/MAINTENANCE.md` | 维护命令、阈值与链档位 |
| 43 | `commands-staging/token-analyze-1.md` | 机械段入口 |
| 44 | `commands-staging/token-analyze-2.md` | 判断段入口及修复引用 |
| 45 | `commands-staging/token-analyze-3.md` | 装配段入口 |
| 46 | `commands-staging/token-analyze.md` | 总入口与流程选择 |

另审 `CHANGELOG.md` 文件头版本规则、7.2.0–9.0.1 五版索引及详细段；对照 `agents/openai.yaml`、`pyproject.toml`。历史条目中的旧行为按版本语境处理。

检索采用明确的文件白名单：先按变更脚本名、函数名、新字段和产物名寻找全部文档提及点，再反查旧行为表述；CLI 对照 `argparse`、子命令表或手工分派，产物对照实际写入点，数字及拒收条件对照分支与测试断言。另建立了 **310 份 Python 源文件的静态 CLI 索引**，核对文档涉及的 130 个现存脚本名及 89 处调用／参数片段。合法别名、历史行为、链族差异及 formal／exploration／legacy 分档均先排除。

## 代码变更区专审覆盖

已执行：

```sh
git log --oneline 4cbfe48..HEAD -- scripts/
git diff --stat 4cbfe48..HEAD -- scripts/
git diff --name-only 4cbfe48..HEAD -- scripts/
```

范围为 **38 个变更文件，新增 2,806 行、删除 118 行**：16 份生产代码、20 份测试／夹具代码、2 份 manifest。16 份生产代码均逐项反查文档提及点：

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

按五版变更核对了以下机器行为：

| 版本／条目 | 已核对的行为变化 |
|---|---|
| 7.2.0 R08 | 图 2 拒绝 NaN／Infinity、非法及非有限 pct；解析失败时，在两输入可取哈希的前提下尝试写 FAIL 收据；序列输出禁 NaN。 |
| 7.2.0 R03 | 钱包自持只计 strict；expanded 进入上限区间；区间形状、下限和上限关系重算。 |
| 7.2.0 R07 | `facts_gate.py build`／`derive_facts`、三账与 identity／provenance／facts_inputs 输入、`facts-provenance/v1`、峰值证据、发布和收口重算。 |
| 7.2.0 R09 | 峰值产物递归定位、needs 哈希、重复 `--only-addrs` 输入取并集、无门槛补算、首个输入目录输出 `block_precision_followup.json`；跳过全量 pass1／merged／pass2。 |
| 7.2.1 F06 | 消费侧由 `tier=exclude` 重推 `INFRA_IN_ENTITY`；清空 flag 不能解除 resolution 要求。 |
| 7.2.1 F04 | 发布期用实际 facts／series 重跑图 2 校验。 |
| 7.2.1 F07 | summary／needs／followup 任一定位；多目录拒收；补算收据核当前 producer、唯一 channels、value_type 和 count。 |
| 7.2.1 F05 | peak 不超过供应；override 证据对象须与峰值及日期申报相等；日期严格校验并受已声明当前锚点约束；decimals 绑定继续对照 8.0.0 的最终实现。 |
| 8.0.0 G1 | 项目方／大庄／小庄／离场庄必画实体各一条线；缺线、重复线拒收；核对无必画实体时的空序列兼容分支。 |
| 8.0.0 G2 | observation bundle v2；冻结块 decimals 观测、uint8、transcript 9 笔；accounting／bundle／facts／EVM config 精度对账，旧 bundle v1 拒收。 |
| 9.0.0 F04 | RpcPool 缺 result 判失败；合法 result=null 与缺键区分；getcode 只接合法十六进制字节串，非法响应记 error 并退出 1。 |
| 9.0.0 F05 | 价格收据非空 points、verdict 重算、PASS／WARN 准入、`price_file_sha256` 绑定、内联 receipt 引用；旧收据及 FAIL／ALL_SKIP 拒收。 |
| 9.0.0 F02 | 可选 `facts_inputs.circulating_supply {raw,asof,source}`、范围及日期校验、token 两字段输出、扁平键拒收、流通分母触发流转图。 |
| 9.0.1 F04 | EVM 显式“散户”spec 拒收；Solana 分支不套用该限制。 |
| 9.0.1 F01 | 主价格非有限或非正 fatal 退出 1；第二源非有限规范化为 null／SKIP；收据禁 NaN；closeout 按价格重算逐点 status，再核汇总 verdict。 |

同时审读变更测试的相关断言及两份 manifest 差异；没有将“新增能力未写入文档”计为问题。

R1–R11 回查使用 `3942c23..HEAD` 累计文档差异，并对照本工程既有报告、工单及完成记录：累计涉及 **22 份文档**，`scripts/` 无修复差异。已回查修复后的字段、示例参数、收据版本、重封命令、阈值说明和规则引用，未确认新增矛盾。

## 发现

无。

## 待确认（不计入 N）

无保留项。已裁决的 wave_scan 浮点阈值例外未重报；措辞偏好、补写建议和范围外问题未计入。

## 执行边界

报告全文已打印到 stdout。全程离线、只读；未修改或新建文件，未 commit。未读取 `~/.codex/` 或其中的 memories；未读取指定禁读目录及 `references/attic.md` 正文。maintenance 内容读取仅限本工程和获准的上一工程 `code_change_pending.md`。

本轮采用源码、差异、测试断言和文档的静态核对，未执行生产流程或复跑九项机器守卫；报告不以既有守卫通过代替语义审查。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| — | — | — | — | — | 0 条符合收录标准的新发现 |
