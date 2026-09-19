# 盲审 R9b：2 条发现

审查基线：`bf202667c80cfb59a40404d9d59b50461d91ff30`；git status 前/后：空/空  
分支：`main`；VERSION：`9.0.1`。

新增 A 类 2 条：minor 1、nit 1。未发现新的 B 类问题；两条均在 `4cbfe48` 基线中已存在，**不是 R1–R8 修复引入**。已与前八轮报告、工单及完成报告去重。报告全文已打印到 stdout。

## 覆盖声明

全程离线、只读，未修改或新建文件，未 commit；未读取 `~/.codex/` 或其他指定禁区。未复跑会读取范围外材料或写入测试产物的守卫。

必审文档 **46 份、6562 行**，已逐文件阅读：

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

另核对 `CHANGELOG.md` 头部版本规则、7.2.0／7.2.1／8.0.0／9.0.0／9.0.1 索引和详细段，以及 `agents/openai.yaml`、`pyproject.toml`。历史条目描述旧版本的行为未作为现行漂移计数；已裁决的 `wave_scan` 浮点阈值例外未重报。

**术语表：312 项。** 计数口径为 `SKILL.md`、`analyze-workflow.md`、`split-run.md` 的行内反引号内容及 EF／ET／G／A 阶段编号去重；另以版本新增字段、函数名、产物名扩展定向检索。

**grep 策略：** 仅对必审文件白名单检索，避免递归进入禁区。先读版本变更，再按改动脚本名、函数名和字段定位文档提及点；反向检查文档中的旧行为承诺。CLI 对照参数定义或分派表，产物对照路径常量和写出语句，阈值、退出码及门禁语义对照实现和相关测试断言。候选再检查历史语境、合法别名、formal／exploration／legacy 差异及前八轮修复。

### 代码变更区覆盖

已执行：

```sh
git log --oneline 4cbfe48..HEAD -- scripts/
git diff --stat 4cbfe48..HEAD -- scripts/
```

结果为 **38 个文件，+2806／−118 行**。其中 16 个生产脚本的变更与文档逐点对照，22 个测试、夹具及登记文件核对变更和相关断言；其余代码按文档承诺反向定位。变更清单：

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
scripts/tests/contract_manifest.json
scripts/tests/identity_gate_fixture.py
scripts/tests/invariant_manifest.json
scripts/tests/test_a4_gate.py
scripts/tests/test_audit_release_gate.py
scripts/tests/test_batch1_rpc_attestation.py
scripts/tests/test_batch3_evm_vertical_slice.py
scripts/tests/test_engine_equivalence.py
scripts/tests/test_entity_identity_gate.py
scripts/tests/test_evm_observation.py
scripts/tests/test_evm_observation_nonempty_code.py
scripts/tests/test_evm_observation_release.py
scripts/tests/test_figures_from_facts.py
scripts/tests/test_handoff_manifest.py
scripts/tests/test_peaks_daily.py
scripts/tests/test_repair_batch_c.py
scripts/tests/test_repair_batch_d.py
scripts/tests/test_report_facts.py
scripts/tests/test_review_20260804_p105.py
scripts/tests/test_stage2_closeout.py
scripts/tests/test_stage2_reseal.py
scripts/tests/test_supply_truth_gate.py
```

### 新增／改变的机器行为核对清单

| 版本 | 核对的行为 |
|---|---|
| 7.2.0 R08 | 图 2 拒非数、bool、NaN／Infinity 等非法 pct；解析失败在两输入实物存在时尝试写 FAIL 收据，非 list 等既有不写收据分支保留；序列序列化拒非有限值。 |
| 7.2.0 R03 | strict 与 expanded 分流；expanded 不进 confirmed 下限，只进 `expanded_economic_control_range_raw` 上限；有 expanded 时区间必填，并核形状、下限及上限最小值。 |
| 7.2.0 R07 | `facts_gate.py build`／`derive_facts` 从三账、identity、provenance 与 `state_source.facts_inputs` 生成 facts；实体、strict 成员、current、total 各有指定来源；formal 峰值无来源或小于 current 拒收，override 须绑定证据。校验人工字段类型及非有限 JSON；写 `facts-provenance/v1`；facts 进入正式必需产物；发布和 stage2 同函数重算，拒探索产物、改名、符号链接及绑定漂移。 |
| 7.2.0 R09 | 递归发现峰值产物并绑定 needs 哈希；`--only-addrs` 可重复，解析 needs／trigger／地址列表并取并集；写 `block-precision-followup/v1` 至首个输入所在目录，覆盖逐址 peak／peak_blk；跳过全量 pass1／merged／pass2；坏形状、坏 JSON、空并集 exit 2。 |
| 7.2.1 F06／F04 | 身份闸对 tier=exclude 的实体成员重新推导 INFRA_IN_ENTITY，清 flag 不解除义务；发布闸读取图 2 两输入实物重算，不能仅凭收据 PASS。 |
| 7.2.1 F07 | summary／needs／followup 任一定位峰值目录；多目录或目录缺 summary 拒；followup 绑定当前 producer 哈希、案内唯一 channels 实物及哈希、value_type、count，并核输入和地址覆盖。 |
| 7.2.1 F05 | peak_raw≤total_raw；override 证据必须为 `{entity_id:{peak_raw,peak_date}}` 且与申报相等；日期严格 ISO，存在当前锚点日期时不得越界；增加 facts decimals 核验，其 EVM 来源在 8.0.0 改为实际观测。 |
| 8.0.0 G1 | 项目方／大庄／小庄／离场庄前缀实体各需一条图 2 线；缺线、重复线拒收；closeout 复用同一规则。无必画实体时的空 series 例外仍保留，未把它误判为新漂移。 |
| 8.0.0 G2 | EVM 增 decimals() 观测，uint8 校验、transcript 9 笔、bundle v2 的 supply.decimals；accounting 写 checks.decimals，shared receipt 核两者相等；facts decimals 两链族统一读 accounting.checks.decimals，EVM 另核 config；旧 v1 拒收及受影响收据重建要求。 |
| 9.0.0 F04 | RpcPool 缺 result 判失败，合法 result:null 仍由消费者判断；getcode 只接受 0x 或偶数长度十六进制代码，其余记 error、exit 1。 |
| 9.0.0 F05 | 价格收据新增必填 price_file_sha256；closeout 读取非空 points 重算 verdict、仅接 PASS／WARN，WARN 记 NOTE；核来源及主文件哈希；内联 dual_source_check 须有 receipt 引用；拒旧收据、纯申报、FAIL、ALL_SKIP 和错绑哈希。 |
| 9.0.0 F02 | 可选 facts_inputs.circulating_supply 的 raw／asof／source，校验正数且不超总量、严格日期和非空来源；生成 token.circulating_supply_raw／circulating_supply_source，供必画下限使用并记 NOTE；拒扁平错位键及重算不一致。 |
| 9.0.1 F04 | EVM camp_spec 显式配置“散户”在共享校验层 exit 2；Solana 不采用这一拒收规则。 |
| 9.0.1 F01 | 主价格任一点非有限或非正即 fatal、exit 1、写盘前结束；第二源非有限归一为 None／SKIP；收据 allow_nan=False；closeout 核主价有限正数，并按两价偏差和 5%／15% 阈值逐点重算 status。 |

上述变更中，未发现前八轮之外的现行文档旧承诺与 HEAD 实现相矛盾。仅代码新增、文档未提及的能力未计为问题。

## 发现（按严重度排序）

### D1 — minor — A 类 — Etherscan V2 免费层被同时写成仅支持 ETH 和支持 Arbitrum

- **位置甲：** [references/data-pipeline-evm-channels.md:214](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:214) 原文「免费 key 仅 chainid=1 可用」。
- **位置乙：** [references/data-pipeline-evm-sources.md:112](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-sources.md:112) 原文「**Etherscan V2 免费层对 chainid=42161 全可用**」「免费三链 ETH/Arb/Polygon 见 api-keys」。
- **矛盾点：** 同一 API 免费层的链范围互斥，会使执行者把 ETH 脚本的限制误当服务限制，放弃文档另一处指定的 Arbitrum 旁证通道。formal／exploration 档位不能解释这两个免费层断言。
- **反向验证：** channels:212 的“仅 ETH 主网”确实适用于所列脚本；[scripts/evm/fetch_etherscan.py:24](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/fetch_etherscan.py:24) 为 `params = dict(params, chainid=1, apikey=KEY)`。本条只判现役文档自相矛盾，不据离线材料裁定服务商当前套餐。相关原句在 `4cbfe48` 已存在，非 Rn 修复引入。
- **修法建议：** 删除 channels:214 的「免费 key 仅 chainid=1 可用；」，保留标题对脚本适用链的限定及后面的 ETH 用途说明。仅改文本。
- **复现：**

```sh
rg -n '免费 key 仅 chainid=1|免费层对 chainid=42161' \
  references/data-pipeline-evm-channels.md \
  references/data-pipeline-evm-sources.md

rg -n 'params = dict\(params, chainid=1' scripts/evm/fetch_etherscan.py
```

### D2 — nit — A 类 — 地址簿仍指向已不存在的 CEX 托管方法条名

- **位置甲：** [references/address-book.md:225](/Users/uravvv/.claude/skills/token-chip-analysis/references/address-book.md:225) 原文「指纹三件套见 playbook-entity-cluster-methods「CEX 提币囤仓反转通道」条」。
- **位置乙：** [references/playbook-entity-cluster-methods.md:59](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:59) 原文「**判例指针**：本组方法级失败模式及案源见 casebook C-07。」
- **实际落点：** [references/casebook/cex-custody-methods.md:23](/Users/uravvv/.claude/skills/token-chip-analysis/references/casebook/cex-custody-methods.md:23) 原文「**【正式·两案】CEX 提币“囤仓大户”的托管/储备层判定指纹组**」，同条明确列出「ETH 侧另查托管商 gas supplier、约 61h 批量激活窗、同 tx 连续 log 等额分发」。
- **矛盾点：** 地址簿承诺的条名在指定 methods 分册中不存在，相关内容实际位于 casebook C-07；按旧文件名和旧条名无法直接定位所需指纹。
- **反向验证：** 对 46 份必审文档检索完整旧条名，仅地址簿自身命中；指定分册无同名条目或别名。此处涉及 address-book／C-07，不是 R8 已修的 C-06／E-12 六处引用；`4cbfe48` 中已有同一句，非 Rn 修复引入。docs_lint 的文件路径检查不校验这种裸写条名。
- **修法建议：** 优先删除失效括注；如需保留指引，将其缩为「判例见 casebook C-07」。仅改文本。
- **复现：**

```sh
rg -n 'CEX 提币囤仓反转通道|本组方法级失败模式及案源见 casebook C-07|CEX 提币“囤仓大户”' \
  references/address-book.md \
  references/playbook-entity-cluster-methods.md \
  references/casebook/cex-custody-methods.md

rg -nF 'CEX 提币囤仓反转通道' references/playbook-entity-cluster-methods.md
```

第二条命令已实跑：无输出、退出码 1，表明旧条名在所指文件中不存在。

## 待确认（不计入 N）

无。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | A 类 | references/data-pipeline-evm-channels.md:214 | references/data-pipeline-evm-sources.md:112 | 同一免费层的 ETH-only 与 Arbitrum 可用断言冲突 |
| D2 | nit | A 类 | references/address-book.md:225 | references/playbook-entity-cluster-methods.md:59；references/casebook/cex-custody-methods.md:23 | 旧方法条名失效，实际内容在 C-07 |
