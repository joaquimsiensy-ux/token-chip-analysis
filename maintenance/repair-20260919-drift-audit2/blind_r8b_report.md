# 盲审 R8b：2 条发现

审查基线：`c16bf8e63369d8b83097b00ce2d0da765906e25e`；`git status` 前/后：空/空。分支 `main`，`VERSION=9.0.1`，审查前后 HEAD 一致。

两条均为 **nit 级 A 类引用错位**，在 `4cbfe48` 基线中已经存在，**非 R1–R7 修复引入**。未确认新的 B 类文档与代码行为矛盾。

全程离线、只读；未读取指定禁区，未创建或修改文件、未提交。报告直接输出，不落盘。状态检查前后 stdout 均为空、退出码均为 0；Git 启动器另有临时缓存创建被沙箱拒绝的 stderr 提示。

## 覆盖声明

逐文件审查以下 **46 份必审文档**。地址簿审查规则、机器接口及机制说明，未在线核验地址标签真实性。

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

另审：

- `CHANGELOG.md` 文件头版本规则、7.2.0–9.0.1 五版索引及详细段；历史状态未当作现行承诺报错。
- `agents/openai.yaml`、`pyproject.toml`。
- 本工程 R1–R7 双路报告、工单及完成报告，用于去重和修复归因。
- 获准读取的上一轮 `code_change_pending.md`；未重报已裁决的 `wave_scan` 浮点阈值例外。

**术语表：117 项**，包括阶段与角色 14 项、门禁与查数 26 项、协议/schema 20 项、字段及语义 22 项、产物名 25 项、阈值 10 项。

**检索策略：**先按脚本 basename、函数名、字段名检索全部允许文档，再从文档中的命令、参数、产物、阈值反查 argparse、分派表、路径常量和实际写出位置；随后核对链族、formal/exploration、legacy、合法别名及历史语境。章节与判例引用另核“指定文件内是否实际存在该内容”，不只检查文件是否存在。

### 代码变更区覆盖

执行了指定的：

```sh
git log --oneline 4cbfe48..HEAD -- scripts/
git diff --stat 4cbfe48..HEAD -- scripts/
git diff --name-only 4cbfe48..HEAD -- scripts/
```

范围为 **38 个文件，+2806/-118**：16 个运行脚本及 22 个测试、夹具或 manifest 文件。运行脚本逐一核对：

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

测试侧核对新增断言、夹具和契约变化；本轮采用静态审查，未将既有测试记录当作本轮运行结果。

### 新增或改变的机器行为核对清单

| 版本 | 已逐项反查文档的行为 |
|---|---|
| 7.2.0 | 图 2 JSON 拒 NaN/Infinity，pct 全序列检查类型及有限值，解析失败尝试写 FAIL 收据；expanded 不进严格钱包汇总，区间必填及上下界检查；`facts_gate build` 从三账、identity、provenance、`facts_inputs` 生成 facts，增加 `facts-provenance/v1`、override 证据绑定、formal 峰值来源要求及发布/收口重算，收口检查数 11→12；日级峰值 summary 绑定 needs 哈希，候选非空要求 `block-precision-followup/v1`；`--only-addrs` 接受可重复输入、计算地址并集、无预筛门槛、无事件输出 0/null、收据落首个输入目录、跳过全量产物，坏输入退出 2。 |
| 7.2.1 | 身份闸按 `tier=exclude` 重推 `INFRA_IN_ENTITY`；图 2 发布期读取绑定实物重算；summary/needs/followup 任一可定位峰值目录，多目录或缺 summary 拒收，followup 核当前 producer、唯一 channels 实物、`value_type` 和 `count`；实体峰值不超过总供应，override 证据强制 `{entity_id:{peak_raw,peak_date}}` 并逐值相等，日期严格 ISO 且受显式当前锚点日期约束；新增 decimals 来源核验。 |
| 8.0.0 | 项目方/大庄/小庄/离场庄实体必须各有图 2 线，缺线及重复线拒收，收口复用同一规则；无必画实体时的空 series 不混同处理；EVM 冻结块新增 `decimals()` 观测，uint8 范围、transcript 8→9、observation bundle v2、旧 v1 拒收；`accounting.checks.decimals` 来自 `bundle.supply.decimals`，shared receipt 核相等，发布闸两链族读 accounting，并对 EVM 另核 verify_recon config。 |
| 9.0.0 | RpcPool 缺 `result` 键判失败，键在场的 null 交消费者判断；getcode 只认 `0x` 或偶数长度十六进制，其余记错误并退出 1；价格收据增加 `price_file_sha256`，收口真读顶层或内联 receipt 引用、重算汇总、只接收 PASS/WARN、核主价格哈希，旧收据/纯申报/FAIL/ALL_SKIP 拒收，迁移不能使用 `amend` 改冻结 bindings；`facts_inputs.circulating_supply {raw,asof,source}` 可选通道、范围和日期约束、扁平键拒收、生成 token 字段并参与流转图必画判断。 |
| 9.0.1 | EVM camp spec 显式「散户」退出 2，Solana 不套用该禁令；主价格任一点非有限或非正，在写盘前 fatal 退出 1；第二源非有限规范化为 null/SKIP，JSON 禁非有限值；收口逐点按同一偏差公式、舍入及 5%/15% 阈值重算 status，核主价有限且为正。 |

上述核对未发现前七轮之外可确认的 B 类问题。代码新增但文档没有作出相应承诺的字段或能力，未列为发现。

## 发现（按严重度排序）

### D1 — nit — A 类 — Solana §15 引用的“§8 CLUDE Plan B 混合架构”在现行 §8 中不存在

- **位置甲：**[references/data-pipeline-solana-capture.md:237](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:237)，原文：「与 §8 CLUDE"Plan B 混合架构"的分工：那是**高密度短币龄**的取舍方案」。
- **位置乙：**[同文件:35](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:35)，现行 §8 原文：「2-6 个月币龄全程重放数小时级；§11 混合重建（发射窗精确+核心实体流水+CPMM 重建+快照封口）降级为超长币龄（1 年+）专用。」该节结束处 [第 42 行](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:42) 标明：「（CLAW，07-12，经 onchain-data-accounts 记忆转录；第 5/6 条为 PUB 07-14 补充）」。
- **矛盾点：**§15 用于说明当前适用场景的比较，要求读者参照 §8 的 CLUDE Plan B；亲读现行 §8 全段后，既没有该方案名称，也没有其说明。读者无法沿指定章节核验这项方法分工。本条只认定章节指称失效，不据此裁判采集方案设计。
- **修法建议：**优先删除第 237 行「与 §8 CLUDE…取舍方案；」这一失效比较，保留本节自身的稀疏长内盘期方法说明；不新增方法规则。
- **归因：**该引句在 `4cbfe48` 中已存在，非 R1–R7 修复引入。
- **复现：**

```sh
nl -ba references/data-pipeline-solana-capture.md |
  sed -n '30,43p;69,73p;112,115p;235,237p'

sed -n '30,43p' references/data-pipeline-solana-capture.md |
  rg -n 'CLUDE|Plan B'

git show 4cbfe48:references/data-pipeline-solana-capture.md |
  rg -n '与 §8 CLUDE'
```

第二条命令预期无命中，退出码为 1。

### D2 — nit — A 类 — C-06、E-12 已在 methods 续册，六处引用仍指定主册

- **位置甲：**六处原文如下，合并为一条发现。

| 位置 | 原文引句 |
|---|---|
| [references/playbook-entity-cluster-tiering.md:136](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-tiering.md:136) | 「翻案见 casebook/cex-custody.md C-06」 |
| [references/data-pipeline-evm-channels.md:255](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:255) | 「（判例：casebook/cex-custody.md C-06）」 |
| [references/data-pipeline-evm-channels.md:259](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:259) | 「（判例：casebook/entity-clustering.md E-12）」 |
| [references/data-pipeline-solana-capture.md:39](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:39) | 「（判例：casebook/entity-clustering.md E-12）」 |
| [references/data-pipeline-solana-capture.md:53](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:53) | 「（判例：casebook/entity-clustering.md E-12）」 |
| [references/data-pipeline-solana-capture.md:83](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:83) | 「（判例：casebook/entity-clustering.md E-12）」 |

- **位置乙：**
  - [references/casebook/cex-custody-methods.md:5](/Users/uravvv/.claude/skills/token-chip-analysis/references/casebook/cex-custody-methods.md:5)，原文：「## C-06 零 DEX 交互被误当 CEX 资金通道 【单案候选】」。
  - [references/casebook/entity-clustering-methods.md:5](/Users/uravvv/.claude/skills/token-chip-analysis/references/casebook/entity-clustering-methods.md:5)，原文：「## E-12 平台派彩藏住 creator 经济流出 【单案候选】」。
- **矛盾点：**六处均明确指定了文件与判例编号，但对应主册不存在该编号；实际条目在 `-methods.md` 续册。执行者按引用打开文件后找不到证据条目。文件路径本身存在，因此不能只靠文件存在性检查识别此错位。
- **修法建议：**修改六处路径：C-06 改指 `casebook/cex-custody-methods.md`，E-12 改指 `casebook/entity-clustering-methods.md`。保留编号，不复制或新增判例正文。
- **归因：**六处旧路径均可在 `4cbfe48` 中复现，非 R1–R7 修复引入。
- **复现：**

```sh
rg -n \
  'casebook/(cex-custody\.md C-06|entity-clustering\.md E-12)|^## (C-06|E-12) ' \
  references/data-pipeline-evm-channels.md \
  references/data-pipeline-solana-capture.md \
  references/playbook-entity-cluster-tiering.md \
  references/casebook/*.md

rg -n '^## [CE]-' \
  references/casebook/cex-custody.md \
  references/casebook/entity-clustering.md

git show 4cbfe48:references/data-pipeline-evm-channels.md |
  rg -n 'casebook/(cex-custody\.md C-06|entity-clustering\.md E-12)'

git show 4cbfe48:references/data-pipeline-solana-capture.md |
  rg -n 'casebook/entity-clustering\.md E-12'

git show 4cbfe48:references/playbook-entity-cluster-tiering.md |
  rg -n 'casebook/cex-custody\.md C-06'
```

## 待确认（不计入 N）

**混合方案的币龄适用范围是否另有冲突：**`data-pipeline-solana-capture.md:237` 写「高密度短币龄」，第 35、115 行则把 §11 混合重建限定为「超长币龄（1 年+）专用」。但现行文件已缺失被指称的 CLUDE Plan B 完整定义，无法仅凭这些句子证明它与 §11 是同一方案，也不能排除密度条件造成适用差异。因此未将“适用范围互斥”计为发现；D1 仅保留可直接验证的章节指称错误。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | nit | A 类 | `data-pipeline-solana-capture.md:237` | 同文件 §8，第 30–42 行 | §15 指向现行 §8 中不存在的 CLUDE Plan B 说明 |
| D2 | nit | A 类 | `playbook-entity-cluster-tiering.md`、`data-pipeline-evm-channels.md`、`data-pipeline-solana-capture.md` | `casebook/cex-custody-methods.md`、`casebook/entity-clustering-methods.md` | 六处 C-06/E-12 引用指定了错误分册 |
