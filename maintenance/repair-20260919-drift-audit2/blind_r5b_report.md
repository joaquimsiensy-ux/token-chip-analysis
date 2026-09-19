# 盲审 R5b：1 条发现

审查基线：`c6e01f3dd696d534fc7e9380825effb2f0edb588`；`main`，`VERSION=9.0.1`；git status 前/后：空/空。

发现为 A 类 minor；未确认新的 B 类问题或 R1–R4 修复引入的不一致。全程离线、只读，未读禁区或 `~/.codex/`，未修改、新建文件或 commit。报告全文已打印到 stdout。

覆盖声明：以下 46 份必审文档均逐文件通读；另审 CHANGELOG 文件头规则、7.2.0—9.0.1 五版索引及详细段，对照 `agents/openai.yaml`、`pyproject.toml` 和相关脚本实现。前四轮 19 条已修发现及 wave_scan 已裁决例外均排除。

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

术语表 **544 项**：阶段 11、展开后的门禁编号 16、协议串 59、脚本名 144、CLI 参数 149、产物名 165。显式白名单上的 `rg -n -F` 检索命中 875 行、43 份文件；其余 3 份仍完整阅读。数值阈值、角色、链档、章节引用及新增字段另作检索与上下文核对。

grep 策略：先按变更脚本名追文档提及，再按函数名、字段名、产物名及对应中文表述反查旧行为；对候选展开上下文，以 argparse／实际分派、写入路径和返回分支核验，并排除历史描述、合法别名及 formal/exploration/legacy 差异。命令示例另做参数扫描；例如 `benchmark_labels.py --labels-dir=…` 虽未用 argparse，但由 `sys.argv` 分派支持，已排除误报。没有把“新增能力未写文档”计为缺陷。

**代码变更区专审覆盖**

已执行：

```bash
git log --oneline 4cbfe48..HEAD -- scripts/
git diff --stat 4cbfe48..HEAD -- scripts/
git diff --name-only 4cbfe48..HEAD -- scripts/
```

共 38 个变更文件：16 个生产脚本、22 个测试／契约清单文件。生产脚本差异逐一核读；测试侧核对新增拒收断言及关联夹具。38 个文件均按文件名追查文档引用，并对生产函数与字段补充检索。生产脚本清单：

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

从五版 CHANGELOG 提取并与 HEAD 对照的机器行为如下；较早版本描述被后续版本替代时，按最终实现核对现行文档。

- **7.2.0**：图 2 拒 NaN/Infinity、非法类型及非有限 pct，解析失败时在两输入在场的条件下尝试写 FAIL 收据；序列序列化禁非有限值。三账中 strict 进入可证下限、expanded 只进入扩展上限；存在 expanded 时必须给两元素区间，下限等于重算 confirmed，上限至少覆盖下限加 expanded。新增 `facts_gate build`，从三账、identity、provenance 和 `state_source.facts_inputs` 生成带 `facts-provenance/v1` 的 facts；formal 缺峰值来源、峰值低于当前值或非法输入均拒，发布与 stage2 同源重算，exploration 产物不能正式消费。日级峰值产物递归定位并绑定 needs 哈希；`--only-addrs` 可重复接 needs／trigger／地址列表，合并后无门槛补算，输出 `block-precision-followup/v1`，正峰值配区块、零峰值配 null；写首个输入目录，跳过全量产物，坏输入或空并集 exit 2。
- **7.2.1**：身份闸按实体成员的 `tier=exclude` 重推 `INFRA_IN_ENTITY`。图 2 发布闸对绑定的 facts／series 实物重算。峰值目录以 summary／needs／followup 任一定位，多目录或缺 summary 拒；followup 加验当前 producer SHA、案内唯一 channels 实物、value_type 和 count。facts 加验每实体峰值不超过总供应；override 证据必须为 `{entity_id:{peak_raw,peak_date}}` 且与申报一致；日期须严格 ISO，并受显式 current 锚点日期限制。发布闸增加 decimals 对账；EVM 来源在 8.0.0 再改为实际观测。
- **8.0.0**：图 2 必画集合由项目方／大庄／小庄／离场庄标签前缀产生，缺线和重复线拒；存在必画实体时空 series 拒，必画集合为空的旧绿例保留。EVM 冻结块补读 `decimals()`，限定 uint8；transcript 从 8 笔变 9 笔，bundle 升 v2 并新增 `supply.decimals`，旧 v1 拒收。accounting 写观测 decimals，shared 核 accounting 与 bundle 相等，发布闸两链族读 `accounting.checks.decimals`，EVM 另核 config 与观测相等；旧观测及受 producer 哈希影响的收据须重建。
- **9.0.0**：RpcPool 对非对象或缺 result 的业务响应判失败；显式 `result:null` 在通用层仍可成功，由消费者校验。getcode 仅接受 `0x` 或偶数长度十六进制串，坏值记 error 并 exit 1。价格收据新增 `price_file_sha256`；stage2 要求真实收据引用、非空 points、合法状态及一致汇总、非空源名、主文件哈希一致，只放行 PASS/WARN；旧收据、纯申报和 FAIL/ALL_SKIP 拒，价格生产者 PASS/WARN=0、FAIL=2、ALL_SKIP=3。新增可选 `facts_inputs.circulating_supply {raw,asof,source}`，raw 须为正且不超总供应，日期严格 ISO、来源非空；拒扁平错位键，写入 facts 流通量及来源供流转图下限使用。迁移更新价格绑定后须完整 check；冻结 bindings 不能走 amend。
- **9.0.1**：EVM camp spec 显式配置“散户”走既有 `_fail`、exit 2；Solana 保留原分档行为。主价格任一点非有限或非正，在联网／写盘前 fatal exit 1；第二源非有限规范化为 null／SKIP，收据禁 NaN。stage2 对每点主价验有限正数，按第二源有效性及对称偏差重算状态，偏差先保留两位再按 >5／>15 判 WARN／FAIL；声明状态不符即拒。

上述变更未形成前四轮之外的新 B 类实证。本轮采用静态读取和无写入检索，没有复述既有九项守卫的 PASS 输出。

## 发现（按严重度排序）

### D1 — minor — A 类 — −1 会话示例漏掉同册与命令契约要求的 `full` 参数

- 位置甲：[references/split-run.md:15](/Users/uravvv/.claude/skills/token-chip-analysis/references/split-run.md:15) 原文「或 CC 开 Opus 会话（备轨）跑 /token-analyze-1 <币> [链]」。
- 位置乙：[commands-staging/token-analyze-1.md:3](/Users/uravvv/.claude/skills/token-chip-analysis/commands-staging/token-analyze-1.md:3) 原文「argument-hint: <代币名或合约地址> full [链名等补充信息]」；[第 16 行](/Users/uravvv/.claude/skills/token-chip-analysis/commands-staging/token-analyze-1.md:16) 原文「第二个参数必须是 `full`，缺失或不符时开工前先问我」。
- 同册实证：[references/split-run.md:104](/Users/uravvv/.claude/skills/token-chip-analysis/references/split-run.md:104) 原文「用户未给档位时 −1 开工前先问、禁猜」。
- 矛盾点：会话流给出的调用形状缺少必填第二参数；照抄时该位置为空或变成链名，触发开工前补问。命令有明确纠正流程，因此定为 minor。
- 修法建议：**修改**第 15 行为 `/token-analyze-1 <币> full [链]`；无需新增段落或改代码。
- 来源判定：两文件自 `4cbfe48` 至 HEAD 的 diff 为空，属于此前未报的存量问题，**非 R1–R4 修复引入**。
- 复现：

```bash
rg -n -F -e '/token-analyze-1 <币>' -e '用户未给档位' references/split-run.md
rg -n -F -e 'argument-hint:' -e '第二个参数必须是' commands-staging/token-analyze-1.md
git diff 4cbfe48..HEAD -- references/split-run.md commands-staging/token-analyze-1.md
```

## 待确认（不计入 N）

**Solana 的 NOT_EXIST 判定是否已经隐含 off-curve 前提。**

- [references/data-pipeline-solana-scan.md:78](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:78) 写「返回 null（NOT_EXIST）= 从未注资的 PDA（多签 vault 常见形态）」。
- [同文件第 86 行](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:86) 又写「账户不存在（fresh keypair 从未注资）= 收款人从未动过，锁仓休眠中」。
- 反证：[第 79 行](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:79) 紧邻要求「PDA 必 off-curve，先做 `is_on_curve` 检查」；[entity_identity_gate.py:274](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/entity_identity_gate.py:274) 的 PDA 分支也以 `chain == 'sol' and on_curve is False` 为条件。因此第 78 行可能只描述预筛后的分支，尚不能排除适用范围不同的解释，不计为已证实漂移。

```bash
rg -n -F -e '返回 null' -e 'PDA 必 off-curve' -e 'fresh keypair' references/data-pipeline-solana-scan.md
rg -n -F -e "on_curve is False" -e 'oc = is_on_curve' scripts/report/entity_identity_gate.py
```

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
| --- | --- | --- | --- | --- | --- |
| D1 | minor | A 类 | references/split-run.md:15 | commands-staging/token-analyze-1.md:3、16 | −1 调用示例漏写必填 `full`，照抄触发补问 |
