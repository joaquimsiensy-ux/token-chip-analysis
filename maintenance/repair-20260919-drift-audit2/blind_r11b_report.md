# 盲审 R11b：0 条发现

审查基线：`8f73554a4e14a09c3023962496d43f9f32a01c93`；git status 前/后：空/空。分支 `main`，`VERSION=9.0.1`。

未发现符合本轮收录标准的新 A 类或 B 类问题；未确认 R1–R10 修复引入新的不一致。已排除前十轮去重后的 35 条已修问题，以及已裁决的 `wave_scan` 浮点阈值例外。

**覆盖声明：逐文件审过以下 46 份必审文档。**

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

另核对了 `CHANGELOG.md` 文件头规则、五版索引及详细段，`agents/openai.yaml`、`pyproject.toml`，以及允许读取的前十轮审计、工单、完成记录和上一工程裁决台账。CHANGELOG 中描述当时版本状态的文字，没有当作当前契约重报。

术语检索清单共 **120 项**：阶段 10、门禁 19、协议与版本 15、输入输出字段 32、产物及命令 18、阈值及状态 14、链档位及角色 12。结合全文阅读核对范围写法、别名及上下文；字面未命中不作为发现。

**代码变更区覆盖：**`4cbfe48..HEAD` 涉及 16 个代码提交、38 个文件，合计 `+2806/-118`。核对了以下 16 个生产脚本的变更及相关现行实现，并阅读另外 22 个测试、夹具和 manifest 文件的改动。

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

按版本拆出的机器行为核对清单如下；这些是覆盖记录，不是发现：

| 版本／变更 | 已核对的行为 |
|---|---|
| 7.2.0／R08 | 图 2 输入拒绝非有限值及非法 pct 类型；解析失败的退出与 FAIL 收据写出条件；序列化禁止 NaN。 |
| 7.2.0／R03 | strict 成员计入钱包下限，expanded 成员进入扩展上限；存在 expanded 时区间必填，校验数组形状及上下界。 |
| 7.2.0／R07 | `facts_gate build` 从三账等输入生成 facts；人工字段来自 `state_source.facts_inputs`；`facts-provenance/v1`、峰值来源及 override 证据绑定；正式发布重算比较、规范文件名和 exploration 拒收。 |
| 7.2.0／R09 | 峰值产物递归定位、needs 哈希绑定；可重复 `--only-addrs` 合并候选并补算块级峰值；`block-precision-followup/v1` 写出位置、零事件结果、非法输入 exit 2，以及跳过全量产物写出的行为。 |
| 7.2.1／F06 | 消费侧对实体成员的 `tier=exclude` 重核 `INFRA_IN_ENTITY`；需要 resolution，具备合规 resolution 的情形仍可通过。 |
| 7.2.1／F04 | 发布时读取收据绑定的 facts、series 实物并重算图 2，不能只凭自报 PASS；核对末点容差。 |
| 7.2.1／F07 | 三件峰值产物任一在场即可定位目录；多目录、缺 summary 拒收；followup 绑定当前 producer、唯一 channels 实物及哈希，校验类型、数量与地址覆盖。 |
| 7.2.1／F05 | 峰值供应上界、override 证据 JSON 内容相等、严格日期及当前锚点日期上界；decimals 校验及其后续观测来源变更。 |
| 8.0.0／G1 | 项目方、大庄、小庄、离场庄的图 2 必画集合；缺线、重复线拒收；不存在必画实体时，空 series 仍可合法。 |
| 8.0.0／G2 | observation bundle 升至 v2、拒绝 v1；增加 `decimals()`，观测记录共 9 笔；uint8 范围、`supply.decimals`、`accounting.checks.decimals` 及 facts/config 与观测值的一致性。 |
| 9.0.0／F04 | RPC 非对象或缺 `result` 判失败；键在场的 null 由方法消费者判断；getcode 只接受 `0x` 或偶数长度十六进制字节串，非法结果走失败退出。 |
| 9.0.0／F05 | 价格收据必须绑定 `price_file_sha256`、含非空 points；内联声明须有 receipt 引用；重算 verdict，只接收 PASS/WARN，拒绝旧收据、错绑、FAIL、ALL_SKIP 和纯申报。 |
| 9.0.0／F02 | 可选 `facts_inputs.circulating_supply={raw,asof,source}` 的类型、范围、日期和来源要求；输出 token 流通量字段；拒绝错位扁平键，并影响流转图必画判断。 |
| 9.0.1／F04 | EVM 显式配置“散户”桶 exit 2；Solana 保留既有处理。 |
| 9.0.1／F01 | 主价格非有限或非正时，在写盘及第二源查询前 fatal exit 1；第二源非有限值转为 SKIP；收口按实际价格和 5/15 阈值逐点重算状态。 |

**grep 策略与反向验证：**先用明确文件白名单读取文档，再以改动脚本的文件名、无扩展名名称、变更函数和字段检索提及点；对命中段核对上下文。CLI 对照 argparse，子命令对照分派，产物对照路径和写出实现，阈值与退出条件对照实际分支。候选均检查是否属于历史描述、合法别名或 formal/exploration/legacy 差异；代码新增而文档未承诺的能力没有计入。

变更范围可复核为：

```sh
git rev-parse HEAD
git status --short
git log --oneline 4cbfe48..HEAD -- scripts/
git diff --stat 4cbfe48..HEAD -- scripts/
git diff 4cbfe48..HEAD -- scripts/
```

本轮采用离线静态核对，未运行会写盘的动态测试，也未将已知机器守卫的既有 PASS 当成本轮测试结果。

## 发现（按严重度排序）

无符合本轮证据标准的新发现。

## 待确认（不计入 N）

无保留条目。

执行偏差披露：一次检索使用 shell 展开的 `references/*.md`，排除参数未挡住显式路径，误读并返回了 `attic.md` 的一行；已当场披露，未用作审计证据，后续改用明确文件白名单。未读取 `~/.codex/`，未访问网络，未修改或新建文件，未 commit。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| — | — | — | — | — | 0 条新发现；未确认 R1–R10 修复引入新不一致。 |
