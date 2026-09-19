# 盲审 R2b：0 条发现

审查基线：`652799755085c121498e3787b630f77b536d6e31`；git status 前/后：空/空。  
分支 `main`；`VERSION=9.0.1`。中断后续审再次确认 HEAD 相同、工作区为空。

覆盖声明：46 份必审文档，共 6,564 行，已逐文件检索并读取代码变更相关命中及上下文；另审 `CHANGELOG.md` 文件头版本规则、指定五版的索引与详细段。术语表按字面量去重共 **138 项**，涵盖脚本名、函数、字段、协议、阈值及中文行为词。

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
commands-staging/token-analyze.md
commands-staging/token-analyze-1.md
commands-staging/token-analyze-2.md
commands-staging/token-analyze-3.md
CHANGELOG.md（上述限定范围）
```

检索策略：先以指定 Git 区间取得变更清单，再按脚本全名／无后缀名、变更函数、字段和中文旧口径交叉 `rg`；对相关命中读取上下文，并回查 argparse、分派、常量、写出点与消费者。逐项排除历史叙述、合法简写、formal／exploration／legacy 差异，以及没有旧承诺的新增能力。

指定区间实际核对命令：

```sh
git log --oneline 4cbfe48..HEAD -- scripts/
git diff --stat 4cbfe48..HEAD -- scripts/
git diff --name-only 4cbfe48..HEAD -- scripts/
rg -n '^## \[' CHANGELOG.md
```

区间共 **38 个变更文件，+2806／−118**。16 个生产脚本均已核对变更及文档提及点：

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

另核对 `scripts/tests/` 下 22 个变更文件的登记、夹具及相关新增断言，以及 `agents/openai.yaml`、`pyproject.toml`。

增量机器行为覆盖：

| 版本 | 核对内容 |
|---|---|
| 7.2.0 | 图 2 拒非有限／非法 pct，解析失败按条件写 FAIL 收据，序列序列化禁 NaN；strict／expanded 位置金额分流，扩展区间形状与上下界核验；facts build 从三账、identity、provenance、facts_inputs 派生，输入类型／非有限值／峰值来源校验，生成 facts-provenance/v1，new-analysis 发布与收口重算，checks 11→12；日峰产物递归定位、needs 哈希绑定、候选并集补算，--only-addrs 生成 block-precision-followup/v1，写首个输入目录、跳过全量产物、零事件为 0/null、非法输入退出 2。 |
| 7.2.1 | tier=exclude 实体成员重推 INFRA_IN_ENTITY；图 2 发布期按输入实物重算；summary／needs／followup 任一定位峰值目录，多目录或缺 summary 拒收，followup 核 producer、channels、value_type、count；facts 峰值不超总供应、override 证据内容相等、严格 ISO 日期及当前锚点日期约束、decimals 核验。 |
| 8.0.0 | 图 2 四类标签前缀的必画下限、缺线／重复线拒收、选材共用规则；无必画实体的空 series 仍允许；EVM bundle v2 新增冻结块 decimals() 与 uint8 校验，transcript 总数 8→9 笔，旧 v1 拒收；accounting.checks.decimals 对回 bundle.supply.decimals，发布侧核 facts／config decimals。 |
| 9.0.0 | RPC 缺 result 判失败，显式 result:null 留给方法消费者；getcode 只接受 0x 或偶数长度十六进制，非法结果记 error、退出 1；价格收据要求引用、非空 points、来源和 price_file_sha256，重算 verdict，仅接 PASS/WARN，拒旧收据／纯申报／FAIL／ALL_SKIP；circulating_supply 的 raw／asof／source 校验、拒扁平错位键、派生 token 字段并参与流转图选材。 |
| 9.0.1 | EVM 显式配置“散户”退出 2，Solana 保留原分档；主价格任一点非有限或非正即 fatal 退出 1，第二源非有限转 null／SKIP，收据禁 NaN；收口按 main_price／second_price 逐点重算 status，核对 5%／15% 阈值及声明。 |

验证采用静态对照与六组纯内存点验，覆盖阵营链族差异、facts 峰值上界、图 2 必画与数值检查、主价格解析、价格收据重算、流通量选材。未重跑已知九项守卫，未执行真实采集或发布流程。

已复核 R1 两路报告、v2 工单、完成报告及当前九处修订；已排除上一工程台账中的 wave_scan 浮点阈值已知例外。全程离线、只读，未新建或修改文件、未 commit；未读取 `~/.codex/`、其他禁读目录或 `attic.md` 正文，未进行插件启动搜索。

## 发现（按严重度排序）

无。本轮未确认新的 A 类／B 类漂移，也未确认“R1 修复引入”的新不一致。R1 已修条目不重复计入。

## 待确认（不计入 N）

无保留候选。历史版本行为、明确分档差异及仅需补写新增能力的建议均未计入发现。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| — | — | — | — | — | 本轮 0 条新发现；未确认 R1 修复引入新不一致。 |
