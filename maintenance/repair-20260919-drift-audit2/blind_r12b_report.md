# 盲审 R12b：0 条发现

审查基线：`16f9c44c917d5f5f9d27d948c7d15f35715fbece`；`main`；`VERSION=9.0.1`；git status 前/后：空/空。审查前后 HEAD 未变化。

未发现满足双侧实证标准、且未被 R1–R11 覆盖的新增 A/B 类问题；未确认 R1–R11 修复引入新的不一致。

## 覆盖声明

逐文件审阅以下 **46 份必审文档，共 6,562 行**：

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
references/casebook/cex-custody.md
references/casebook/cex-custody-methods.md
references/casebook/entity-clustering.md
references/casebook/entity-clustering-methods.md
references/casebook/supply-accounting.md
references/casebook/supply-accounting-methods.md
references/labels/README.md
references/labels/MAINTENANCE.md
commands-staging/token-analyze.md
commands-staging/token-analyze-1.md
commands-staging/token-analyze-2.md
commands-staging/token-analyze-3.md
```

另审 `CHANGELOG.md` 文件头规则、活跃索引及指定五版详细段；读取 `agents/openai.yaml`、`pyproject.toml`，并对照允许读取的既往报告、施工记录及已裁决台账去重。

**术语核对表：116 项**，其中阶段与门禁 29 项、协议版本 21 项、字段与分支 37 项、参数／产物／阈值 29 项。未命中的新增字段不作为补写建议或发现。

### 代码变更区覆盖

亲查：

```sh
git log --oneline 4cbfe48..HEAD -- scripts/
git diff --stat 4cbfe48..HEAD -- scripts/
git diff --name-only 4cbfe48..HEAD -- scripts/
```

变更范围为 **38 个文件，新增 2,806 行、删除 118 行**：16 个生产脚本及 22 个测试／清单文件。

生产脚本逐项对照：

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

检索采用显式文档白名单，按脚本名、函数名、字段名、协议及参数双向搜索；命中处展开上下文。CLI 对照 `argparse`，产物对照实际写出路径，拒收条件对照分支及测试断言。候选再排查历史描述、合法别名、探索档／旧版边界和既有修复记录。本轮未执行测试，未将源码中的测试断言当作运行结果。

### 五版机器行为核对清单

| 版本 | 已核对的新增或改变行为 |
|---|---|
| **7.2.0** | 图 2 拒绝非有限值及非法数值类型；解析失败时的 FAIL 收据尝试与早期拒绝分支。经济控制下限排除 expanded 位置，扩展区间检查形状及上下界。新增 `facts_gate build`、`facts-provenance/v1`、三账／溯源派生及输入类型检查；正式路径要求 facts，并在发布与收口时重推。日峰产物递归定位、补算输入哈希绑定；`--only-addrs` 可重复并取并集，无门槛补算，输出 `block-precision-followup/v1` 至首个输入目录；无事件地址为零峰值／空块号，非法输入或空并集 exit 2，跳过全量重放产物。 |
| **7.2.1** | `tier=exclude` 不能靠清空 `INFRA_IN_ENTITY` 解除义务。图 2 发布期读取绑定实物重算。峰值三件产物任一存在即定位目录，多目录或缺 summary 拒收；followup 校验当前 producer、唯一 channels 实物、哈希、`value_type` 和计数。峰值不得超过总供应；override 证据必须为指定 JSON 形状且数值一致；日期严格校验，存在当前锚点日期时限制峰日上界；新增 decimals 一致性检查及迁移要求。 |
| **8.0.0** | 图 2 对项目方／大庄／小庄／离场庄强制必画，拒缺线和重复线；无必画实体时保留空集合例外。EVM 冻结块新增 `decimals()` 观测，uint8 范围、九笔 transcript、`supply.decimals`、bundle v2；accounting、shared receipt、facts 与 config 对观测值核验，旧 v1 bundle 拒收及相关收据迁移。 |
| **9.0.0** | RpcPool 缺 `result` 键判失败，合法 null 交消费者处理；getCode 仅接受 `0x` 或偶数字节十六进制，非法响应记失败。价格收据强制主价格哈希、非空 points 与结论重算；仅 PASS／WARN 放行，拒 FAIL／ALL_SKIP／旧收据／纯申报，支持内联 receipt 引用。新增结构化流通量输入及派生字段，校验金额、日期、来源；流转图消费流通量门槛并记录口径。 |
| **9.0.1** | EVM 显式散户桶拒收，Solana 保留原行为。主价格任一点非有限或非正时 exit 1，并在写收据前终止；第二源非有限值归空值／SKIP，禁止序列化 NaN。收口逐点按相同 5%／15% 阈值重算状态，并要求主价为有限正数。 |

## 发现

无新增可计数发现。上述变更未查到尚存且符合本轮收录条件的旧行为承诺。

## 待确认（不计入 N）

无保留候选。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| — | — | — | — | — | 0 条新增发现 |

纪律记录：全程离线，无文件修改、新建或提交，未读取 `~/.codex/`。初始 `wc -l` 行数统计误将 `references/attic.md` 纳入，属于一次禁读边界失误；该调用未展示正文，已即时披露，后续读取与检索均显式排除禁读路径。
