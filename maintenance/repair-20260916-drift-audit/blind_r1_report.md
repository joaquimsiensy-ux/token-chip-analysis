<!-- 由 Fable 从 codex 只读盲审任务 task-mu49kw9l-nlxu8m 的 Final output 段原样搬运;codex 沙箱只读无法自行落盘 -->
# 盲审 R1：19 条发现

审查基线：`444544360179d5080657aafd5ad60a78fe89e9b3`；分支 `main`；`VERSION=7.1.1`。  
审查前后 HEAD 一致；`git status --short` 前/后：**空/空**。

共 **12 条 blocker、6 条 minor、1 条 nit**。全程离线，只读；未修改或新建文件，未 commit。

## 覆盖声明

以下 **46 份必审文档**均纳入全文检索及相关规则上下文核对；另审 `CHANGELOG.md` 指定的现行规则部分，共 47 份：

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
CHANGELOG.md
```

`CHANGELOG.md` 仅审文件头版本规则、活跃窗口索引及 7.0.0–7.1.1 对当前行为的描述，未将历史版本状态作为漂移。

检索与核对方法：

- 从 `SKILL.md`、`analyze-workflow.md`、`split-run.md` 提取 **332 个术语条目**，覆盖反引号标识、阶段/门禁编号及数字阈值；在 46 份必审文档中得到 **2,898 个“术语×行”命中**，不是 2,898 个独立行。
- 对 `scripts/**` 的 **310 个 Python 文件**建立 AST 索引，包含测试目录；核对文档中的 **144 个不同脚本名、478 次提及**，追查相关参数定义、分派、输出常量及校验条件。另核对 `agents/openai.yaml`、`pyproject.toml`。
- 命中后读取上下文并反向核对历史说明、探索档位、合法别名。下面带案源日期的发现，均针对仍以执行规则呈现、未明确退出当前路径的文字。
- 验证限于读取、检索、AST 分析及内存算术复算；没有执行会采集数据或写产物的生产流程。没有将 AST 解析成功当成功能测试通过。

以下复现命令均在仓库根目录执行。

## 发现（按严重度排序）

### D1 — blocker — B 类 — “份额阈值一律整数运算”与波次扫描实现相反，并已复现边界漏判

- **位置甲：** [references/analyze-workflow.md:161](/Users/uravvv/.claude/skills/token-chip-analysis/references/analyze-workflow.md:161)  
  原文：「**份额阈值一律整数运算**」「浮点比较会把"恰好整数枚"大户判漏」。
- **位置乙：** [scripts/report/wave_scan.py:735](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/wave_scan.py:735)  
  原文：「`must_raw = total * a.must_dormant_pct / 100.0`」「`line01_raw = total * 0.1 / 100.0`」；742 行使用「`if p >= line01_raw:`」。
- **矛盾点：** 文档禁止的浮点阈值正在用于必裁决判定。离线复算中，总供应 `10**24 raw`、持仓恰为其 0.1% 时，整数持仓为 `1000000000000000000000`，浮点阈值却上浮至 `1000000000000000131072`，比较结果为 `False`。不满足前 200 等其他条件的地址会漏掉这条必裁决理由。
- **修法建议：** 保留文档承诺。**[需改代码]** 百分比转为精确比例后用整数交叉相乘比较；仅修改文字无法消除已复现的漏判。
- **复现：**

```bash
rg -n '份额阈值一律整数运算|must_raw =|line01_raw =|if p >= (line01_raw|must_raw)' references/analyze-workflow.md scripts/report/wave_scan.py
python3 -B -c 'T=10**24; p=T//1000; t=T*0.1/100.0; print(p, int(t), p>=t)'
```

第二条输出：`1000000000000000000000 1000000000000000131072 False`。

### D2 — blocker — B 类 — 时间抽查完整示例缺少必填的 `--input`

- **位置甲：** [references/data-pipeline-evm-recon.md:152](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-recon.md:152)  
  152–154 行原文：

```bash
python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --rpc <独立archive节点> \
    --chain <eth|bsc|base|arbitrum> --token 0x标的 --out time_spotcheck.json \
    --final-block <数据截止块>
```

- **位置乙：** [scripts/lib/time_spotcheck.py:317](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/time_spotcheck.py:317)  
  原文：「`ap.add_argument("--input", required=True,`」，帮助文字为「生成 plan 所用的真实 merged 转账数据；consumer 会全量重放」。
- **矛盾点：** 即使正确替换示例中的占位值，仍会因缺少必填参数在 argparse 阶段退出，无法完成该正式步骤。
- **修法建议：** 修改现有命令，补上 `--input <生成该计划所用的merged数据>`；无须新增说明章节。
- **复现：**

```bash
rg -n -A3 'python3 scripts/lib/time_spotcheck.py --plan|add_argument\("--input"' references/data-pipeline-evm-recon.md scripts/lib/time_spotcheck.py
```

### D3 — blocker — B 类 — Base 全量转账方案仍推荐已失去正式资格的 Alchemy

- **位置甲：** [references/data-pipeline-evm-sources.md:63](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-sources.md:63)  
  原文：「Base 高峰期 Alchemy 反而是主力通道」；64 行继续要求「HyperSync 负责发射段（旧块），Alchemy 按 fromBlock/toBlock 切成多个块段并行接力拉近段」。
- **位置乙：** [scripts/evm/fetch_alchemy.py:27](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/fetch_alchemy.py:27)  
  原文：「`FORMAL_CHANNEL_ELIGIBLE = False`」。  
  [scripts/evm/csv_collector_receipt.py:7](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/csv_collector_receipt.py:7) 仅允许「`SUPPORTED={"fetch_sqd_evm.py"}`」，13–14 行拒绝未登记 adapter。
- **矛盾点：** Base 专节仍将混拼作为可执行的全量方案，未标为探索路径；当前 Alchemy 无法提供这条正式链路要求的采集收据。照做会采完后卡在正式通道验收。
- **修法建议：** 删除旧的 Alchemy 主力及混拼接力建议，引用现有 `data-pipeline-evm-channels.md:154` 正式通道规则。
- **复现：**

```bash
rg -n '高峰期 Alchemy|分段接力法|FORMAL_CHANNEL_ELIGIBLE|SUPPORTED=|approved formal CSV adapter' references/data-pipeline-evm-sources.md scripts/evm/fetch_alchemy.py scripts/evm/csv_collector_receipt.py
```

### D4 — blocker — B 类 — 锚点法仍被推荐生成报告图数据，但产物被正式编译链明确拒绝

- **位置甲：** [references/data-pipeline-solana-capture.md:48](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:48)  
  原文：「锚点法演变重建（免全量 SQD，`scripts/solana/build_evolution.py`）」「产出图1/图2 数据」。该段以 Plan B 操作配方呈现，仅要求披露插值精度，未标正式链路不可用。
- **位置乙：** [scripts/solana/build_evolution.py:213](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/build_evolution.py:213)  
  原文：「`series_format="sol-anchor-rows"`」。  
  [scripts/lib/camp_series_provenance.py:323](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/camp_series_provenance.py:323) 原文：「不接入正式编译链」「sol-anchor-rows=锚点法小样本辅助件、无对账链锚，正式序列走 replay_edges/replay_duck」。
- **矛盾点：** 文档让执行者将该替代方案用于报告图数据，实际生成的格式在正式编译时必拒。
- **修法建议：** 删除正式替代路线的表述，将现段明确改为探索辅助；正式序列指向已有 `replay_edges/replay_duck` 路径。
- **复现：**

```bash
rg -n 'Plan B|锚点法演变重建|series_format="sol-anchor-rows"|不接入正式编译链' references/data-pipeline-solana-capture.md scripts/solana/build_evolution.py scripts/lib/camp_series_provenance.py
```

### D5 — blocker — B 类 — EVM 对账要求余额和为零，代码要求余额和等于铸币总量

- **位置甲：** [references/data-pipeline-evm-recon.md:13](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-recon.md:13)  
  原文：「**全网余额和=0**：所有地址重建余额求和应为零（mint/burn 计入），不为零即漏了转账段」。
- **位置乙：** [scripts/evm/verify_recon.py:339](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/verify_recon.py:339)  
  原文：「`balance_sum = sum(balances.values())`」；343 行为「`supply_closed = mint == nominal and balance_sum == mint and not negatives`」。
- **矛盾点：** 对当前重放余额产物，两个验收目标相反。不是合法的不同账本约定：同一文档 42 行也明确写「`sum_balances == mint_total`」。按第 13 行执行会把正确余额账误判成漏数据。
- **修法建议：** 删除第 13 行旧的零和规则，沿用本文件已有的 `sum_balances == mint_total` 解释。
- **复现：**

```bash
rg -n '全网余额和=0|sum_balances == mint_total|balance_sum =|supply_closed =' references/data-pipeline-evm-recon.md scripts/evm/verify_recon.py
```

### D6 — blocker — A 类 — GMGN 对账同时被规定为“个位精确硬闸”和“比例黄灯”

- **位置甲：** [references/playbook-supply-recon.md:42](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-supply-recon.md:42)  
  原文：「重建余额 vs GMGN top10 逐个对比，要求 **10/10 精确到个位**」。38 行明确要求这些形态「归入四查框架执行」「做哪条链就执行哪套」。
- **位置乙：** [references/data-pipeline-evm-recon.md:12](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-recon.md:12)  
  原文：「GMGN top10 是另一个第三方比例对表：以 0.15pp 为容差，差异不改变收据的 PASS/0」，同时要求黄灯人工查证说明。
- **矛盾点：** 前者把 GMGN 当作 raw 余额硬对账源，后者明确将其与 RPC 精确对账分开；会造成错误回采或错误判 FAIL。黄灯的人工查证义务并不等于“个位精确”要求。
- **修法建议：** 删除供应对账手册中的旧 GMGN 硬闸副本，引用 EVM 对账册现行规则。
- **复现：**

```bash
rg -n '10/10 精确到个位|GMGN 黄灯|0.15pp|归入四查框架执行' references/playbook-supply-recon.md references/data-pipeline-evm-recon.md
```

### D7 — blocker — A 类 — 判级既要求合并全部疑似地址，又禁止扩展关联直接进入实体标签

- **位置甲：** [references/playbook-entity-cluster-tiering.md:31](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-tiering.md:31)  
  原文：「**合并口径含全部疑似关联地址（无论证据程度）**」「按下表打标签」。`analyze-workflow.md:145` 亦重复该口径。
- **位置乙：** [references/playbook-entity-cluster-tiering.md:150](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-tiering.md:150)  
  原文：「标签判级以可证的严格实体为主」「只有 expanded 证据升级为 strict 后才回灌单一实体标签」。
- **矛盾点：** 同一判级规则对疑似地址是否计入实体给出相反答案；前者可能用尚未确权的扩展持仓把实体推过庄级门槛。
- **修法建议：** 删除两处“全部疑似关联地址”承诺，统一引用本文件末尾已有的严格/扩展确权规则。
- **复现：**

```bash
rg -n '合并口径含全部疑似|只有 expanded 证据升级为 strict' references/playbook-entity-cluster-tiering.md references/analyze-workflow.md
```

### D8 — blocker — A 类 — 纯行为指纹仍被允许升级为铁证，与统一证据上限冲突

- **位置甲：** [references/playbook-entity-cluster-tiering.md:82](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-tiering.md:82)  
  镜像余额指纹原文：「同额整数仓 < 秒级同步 < 目标余额驱动；**三者叠加可到链上铁证**」。  
  [references/data-pipeline-solana-scan.md:133](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:133) 又称「关联硬证据（任一即可，叠加为铁案）」，135 行将同 block 同买同卖称为「最强铁证」。
- **位置乙：** [references/playbook-entity-cluster-tiering.md:54](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-tiering.md:54)  
  类型③的措辞上限原文：「**高度疑似（永不实锤）**」。  
  [references/playbook-entity-cluster-methods.md:147](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:147) 进一步规定：「组内资金闭环可升铁证；没有则上限“高度疑似”」。
- **矛盾点：** 局部指纹配方允许仅凭行为同步或余额模式确证同一实体，绕过统一规则要求的独立控制证据。两处属于同一证据上限漂移，合并计一条。
- **修法建议：** 删除纯行为“可到铁证”“任一即可”的升级承诺，沿用现有行为指纹总闸与措辞上限。
- **复现：**

```bash
rg -n '三者叠加可到链上铁证|关联硬证据|同 slot 原子下单|高度疑似（永不实锤）|没有则上限' references/playbook-entity-cluster-tiering.md references/data-pipeline-solana-scan.md references/playbook-entity-cluster-methods.md
```

### D9 — blocker — A 类 — Streamflow 公共服务 feePayer 同时被允许和禁止用作实体合并依据

- **位置甲：** [references/data-pipeline-solana-scan.md:85](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:85)  
  原文：「多笔提取共用此 feePayer = 同一批操作，据此把散落的"新钱包"归回原实体」；同句已明确该地址是 Streamflow 自动提取服务。
- **位置乙：** [references/data-pipeline-solana-capture.md:54](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:54)  
  原文：「服务 feePayer 不作控制边，去向必须靠代币流穿透」。
- **矛盾点：** 前者将公共服务共用关系直接用于合并，后者明确禁止，可能把互不相关的服务使用者归为同一实体。
- **修法建议：** 删除 scan 册中由服务 feePayer 共用推出合并的句子，保留代币流穿透要求。
- **复现：**

```bash
rg -n '共用此 feePayer|服务 feePayer 不作控制边' references/data-pipeline-solana-scan.md references/data-pipeline-solana-capture.md
```

### D10 — blocker — A 类 — “部署早于代币”既是公共设施充分条件，又仅是线索

- **位置甲：** [references/casebook/entity-clustering.md:18](/Users/uravvv/.claude/skills/token-chip-analysis/references/casebook/entity-clustering.md:18)  
  原文：「公共基础设施先验三测（**任一命中即出实体表**、按设施单列）」「②部署时间早于代币创建＝公共设施」。
- **位置乙：** [references/playbook-entity-cluster-methods.md:198](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:198)  
  原文：「公共基础设施先验四测」「③部署早于代币创建**只作公共信号**，晚于不作专属信号」。
- **矛盾点：** 同一个部署时间事实，在判例库中会直接剔除成员，在正式方法中不能独立完成定性。
- **修法建议：** 删除判例库旧三测副本，引用现行四测；至少删除“部署更早即公共设施”的充分条件。
- **复现：**

```bash
rg -n '先验三测|部署早于代币创建只作公共信号' references/casebook/entity-clustering.md references/playbook-entity-cluster-methods.md
```

### D11 — blocker — A 类 — 完整阴性结论仍沿用已明确废止的 0.5% 排查线

- **位置甲：** [references/playbook-evidence-wording.md:106](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-evidence-wording.md:106)  
  原文：「"全盘零庄/无其他实体"必须证明**当前≥0.5% owner**、历史峰值、已归零/回落/静置仓和边界外候选全部裁决」。
- **位置乙：** [references/independent-audit-protocol.md:46](/Users/uravvv/.claude/skills/token-chip-analysis/references/independent-audit-protocol.md:46)  
  原文：「当前所有 **≥0.1% 总供应或 ≥0.2% 流通**的 owner」「**原 0.5% 线废止**」；49 行禁止在达到该线的 owner 尚未裁决时发布完整阴性结论。
- **矛盾点：** 措辞册允许执行者按更窄的当前持仓集合完成阴性证明，漏掉新门槛已要求覆盖的地址。
- **修法建议：** 删除旧数字副本，改为引用“达到 tiering §6a 其他大户线的全部 owner”。
- **复现：**

```bash
rg -n '当前≥0\.5% owner|原 0\.5% 线废止|当前 owner 仍有未裁决' references/playbook-evidence-wording.md references/independent-audit-protocol.md
```

### D12 — blocker — A 类 — 独立复核的 Solana 对账清单仍只有四查

- **位置甲：** [references/independent-audit-protocol.md:166](/Users/uravvv/.claude/skills/token-chip-analysis/references/independent-audit-protocol.md:166)  
  原文：「受控启动**四查生产者**生成：balance/supply=`verify_recon.py`、supply_truth=`supply_truth_gate.py`、time=`time_spotcheck.py`（Solana 对应 anchor sampler 与 holder snapshot）」。
- **位置乙：** [references/split-run.md:41](/Users/uravvv/.claude/skills/token-chip-analysis/references/split-run.md:41)  
  原文：「**EVM 四查；Solana 五查＝四查＋精确重放 `exact_reconcile`**」。  
  [references/scan-schemas.md:1177](/Users/uravvv/.claude/skills/token-chip-analysis/references/scan-schemas.md:1177) 明确 Solana 键集为 `supply,balance,supply_truth,time,exact_reconcile`。
- **矛盾点：** 独立复核协议将四查描述同时用于 Solana，却遗漏必需的第五项。按该清单构造 job spec 会被 runner 的完整键集校验拒绝，见 `reconciliation_report.py:167–168`。
- **修法建议：** 删除重复的四查生产者清单，改为引用按 family 定义的现行完整键集。
- **复现：**

```bash
rg -n '受控启动四查生产者|EVM 四查；Solana 五查|family=solana 时固定顺序' references/independent-audit-protocol.md references/split-run.md references/scan-schemas.md
```

### D13 — minor — B 类 — `find_snapshot` 已没有文档宣称的冻结文件默认优先级

- **位置甲：** [references/analyze-workflow.md:118](/Users/uravvv/.claude/skills/token-chip-analysis/references/analyze-workflow.md:118)  
  原文：「`holder_distribution_scan.find_snapshot` 默认优先 `data/holders_owners.json`（冻结件）」。`split-run.md:54` 重复此说法。
- **位置乙：** [scripts/report/holder_distribution_scan.py:193](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/holder_distribution_scan.py:193)  
  原文：「显式指定 > final 取 initial scan 绑定 > initial 取 data_map 唯一登记候选」；207 行在「`len(registered) != 1`」时拒绝。
- **矛盾点：** 当前行为是绑定解析和唯一登记，不是按冻结文件优先回退。两处完整命令已显式指定快照，因此现有示例仍能避开此错误解释。
- **修法建议：** 删除两处错误的默认优先级解释，保留现有显式指定命令。
- **复现：**

```bash
rg -n 'find_snapshot.*默认优先|显式指定 > final|len\(registered\) != 1' references/analyze-workflow.md references/split-run.md scripts/report/holder_distribution_scan.py
```

### D14 — minor — B 类 — `build_evolution.py` 没有承诺的 `--no-labels` 开关

- **位置甲：** [references/labels/README.md:8](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/README.md:8)  
  原文将 SOL `replay_edges.py`/`build_evolution.py` 纳入「均已默认接入（`--no-labels` 关闭）」。
- **位置乙：** [scripts/solana/build_evolution.py:103](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/build_evolution.py:103)  
  原文：「`_resv = LabelResolver('sol')`」。该文件没有 `--no-labels` 判断或 CLI 参数解析入口；228 行直接调用「`main()`」。
- **矛盾点：** 对 `build_evolution.py`，传入这个字样并不会关闭标签检查。默认接入行为成立，统一关闭开关的承诺不成立。
- **修法建议：** 删除一概适用的括号承诺，或将它限定到实际注册该参数的脚本；无需为了文档而新增开关。
- **复现：**

```bash
rg -n -- '均已默认接入|--no-labels|LabelResolver|sys\.argv|argparse|parse_args|main\(\)' references/labels/README.md scripts/solana/build_evolution.py
```

### D15 — minor — B 类 — 原生 Parquet done 仍被写成 v3，当前生产和校验均为 v4

- **位置甲：** [references/data-pipeline-evm-channels.md:69](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:69)  
  原文：「v2 Parquet 通道则继续由 **native done v3** + `make_channel_receipt.py --format v2` 生成」。
- **位置乙：** [scripts/evm/fetch_hypersync_v2.py:50](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/fetch_hypersync_v2.py:50)  
  原文：「`MANIFEST_SCHEMA = "hypersync-v2-done/v4"`」；51 行将 v3 列入 `LEGACY_MANIFEST_SCHEMAS`，219 行报「legacy done … 未迁移；先运行 --refresh-manifests」。
- **矛盾点：** 文档把需迁移的旧格式称为当前原生格式；当前生产者本身会输出 v4，因此主要误导存量产物识别。
- **修法建议：** 将该处 `native done v3` 改为 `native done v4`，沿用同文件 197 行已有迁移规则。
- **复现：**

```bash
rg -n 'native done v3|MANIFEST_SCHEMA =|LEGACY_MANIFEST_SCHEMAS =|legacy done.*未迁移' references/data-pipeline-evm-channels.md scripts/evm/fetch_hypersync_v2.py
```

### D16 — minor — B 类 — 文档仍称 Parquet reader 整表载入，实际已经分批读取

- **位置甲：** [references/data-pipeline-evm-channels.md:272](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:272)  
  原文：「**transfers_lib 整表读大 parquet 必 OOM**」「`iter_transfers` 内部 `pq.read_table` 整表载入」，并要求亿级扫描另写 reader。
- **位置乙：** [scripts/evm/transfers_lib.py:80](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/transfers_lib.py:80)  
  原文：「`pf = pq.ParquetFile(lp)`」；87 行为「`for batch in pf.iter_batches(batch_size=100_000, columns=available):`」。`iter_transfers` 在 105 行转入该实现。
- **矛盾点：** 文档把已不存在的整表读取方式描述为当前行为，诱导执行者绕开现有统一 reader。这里不据此断言所有内存风险都已消除。
- **修法建议：** 删除旧的 `pq.read_table` 整表载入及“因此必须自写 reader”建议。
- **复现：**

```bash
rg -n 'pq\.read_table|iter_batches|yield from _iter_parquet_dir' references/data-pipeline-evm-channels.md scripts/evm/transfers_lib.py
```

### D17 — minor — A 类 — four.meme API 的“全路径已失效”结论仍与同库修正并存

- **位置甲：** [references/data-pipeline-evm-channels.md:259](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:259)  
  原文：「meme-api 全路径已 404，正身改看创世 tx HTML」。
- **位置乙：** [references/data-pipeline-evm-sources.md:25](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-sources.md:25)  
  原文：「2026-07-19 SIREN 实测**复活可用**（此前"全路径 404"过时）」。
- **矛盾点：** 同库已经明确宣布旧结论过时，当前渠道册仍用该结论指导换路。本条只确认文档冲突，不判定接口今日是否可用。
- **修法建议：** 删除渠道册无时点的“全路径已 404”结论及其强制换路推论，保留有日期的实测记录。
- **复现：**

```bash
rg -n 'meme-api 全路径已 404|复活可用.*全路径 404' references/data-pipeline-evm-channels.md references/data-pipeline-evm-sources.md
```

### D18 — minor — A 类 — 标签来源表同时宣称 curation 和 manual 都“压过一切”

- **位置甲：** [references/labels/MAINTENANCE.md:19](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/MAINTENANCE.md:19)  
  `manual/addressbook` 行原文：「最高，优先级压过一切」。
- **位置乙：** [references/labels/MAINTENANCE.md:8](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/MAINTENANCE.md:8)  
  原文：「curation 层（SRC_PRIORITY = -1，**高于 manual/addressbook**）」；17 行又将 curation 标为「最高（压过一切）」。
- **矛盾点：** 同一手册给出两个互斥的最高优先级，误导维护者判断冲突条目应由哪一层覆盖。
- **修法建议：** 删除 manual 行的“最高，优先级压过一切”，保留现有明确的 curation 优先级规则。
- **复现：**

```bash
rg -n 'SRC_PRIORITY = -1|压过一切' references/labels/MAINTENANCE.md
```

### D19 — nit — A 类 — split-run 引用的 A3 主序编号已过期

- **位置甲：** [references/split-run.md:45](/Users/uravvv/.claude/skills/token-chip-analysis/references/split-run.md:45)  
  地址标注被称为「主序第 1 项前半」；47 行将大户批量排查称为「主序第 5 项的批量侧」。
- **位置乙：** [references/analyze-workflow.md:95](/Users/uravvv/.claude/skills/token-chip-analysis/references/analyze-workflow.md:95)  
  原文：「1. **判例库过闸**」；107 行为「5. **当前持仓分布初判**」；142 行才是「10. **判级（含 ET-1）**」。
- **矛盾点：** 动作名称尚可理解，但按交叉引用编号定位会跳到不同步骤。
- **修法建议：** 删除易漂移的“主序第 N 项”括注，保留步骤名称。
- **复现：**

```bash
rg -n '主序第 [15] 项|^1\. \*\*判例库|^5\. \*\*当前持仓分布|^10\. \*\*判级' references/split-run.md references/analyze-workflow.md
```

## 待确认（不计入 N）

1. **SQD `/head` 描述是否意在承诺正式采集上界。**  
   `references/data-pipeline-solana-capture.md:134` 写「采集上界取 `/head` 没问题」；`scripts/solana/fetch_sqd_transfers_v2.py:981` 获取 finalized slot，985 行执行 `head = min(head, finalized_slot)`。前者也可能仅描述服务端可读范围，尚不足以确定是在承诺生产者最终 cutoff，因此不计 B 类发现。

   ```bash
   rg -n '采集上界取|finalized_slot =|head = min' references/data-pipeline-solana-capture.md scripts/solana/fetch_sqd_transfers_v2.py
   ```

2. **方法册的 `wave_scan v3` 是当前版本要求，还是机制引入版本。**  
   `references/playbook-entity-cluster-methods.md:171` 写「三条现役机械通道」「wave_scan v3」；`references/split-run.md:51` 指定 `wave-scan/v5`，`scripts/report/wave_scan.py:80` 也是 `SCHEMA = "wave-scan/v5"`。前者没有明确写成 `wave-scan/v3` schema，存在指代旧机制版本的解释，暂不独立计数。

   ```bash
   rg -n 'wave_scan v3|wave-scan/v5' references/playbook-entity-cluster-methods.md references/split-run.md scripts/report/wave_scan.py
   ```

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | blocker | B | `references/analyze-workflow.md` | `scripts/report/wave_scan.py` | 整数阈值承诺被浮点实现破坏，已复现漏判 |
| D2 | blocker | B | `references/data-pipeline-evm-recon.md` | `scripts/lib/time_spotcheck.py` | 完整命令缺必填 `--input` |
| D3 | blocker | B | `references/data-pipeline-evm-sources.md` | `scripts/evm/fetch_alchemy.py` | Base 方案仍依赖非正式 Alchemy 通道 |
| D4 | blocker | B | `references/data-pipeline-solana-capture.md` | `scripts/lib/camp_series_provenance.py` | 推荐的锚点产物被正式编译拒绝 |
| D5 | blocker | B | `references/data-pipeline-evm-recon.md` | `scripts/evm/verify_recon.py` | 余额零和要求与铸币总量闭合冲突 |
| D6 | blocker | A | `references/playbook-supply-recon.md` | `references/data-pipeline-evm-recon.md` | GMGN 个位硬闸与比例黄灯并存 |
| D7 | blocker | A | `references/playbook-entity-cluster-tiering.md` | 同文件 | 全部疑似合并与严格实体判级冲突 |
| D8 | blocker | A | `references/playbook-entity-cluster-tiering.md`、`references/data-pipeline-solana-scan.md` | `references/playbook-entity-cluster-methods.md` | 纯行为铁证规则突破统一证据上限 |
| D9 | blocker | A | `references/data-pipeline-solana-scan.md` | `references/data-pipeline-solana-capture.md` | 公共服务 feePayer 被用于实体合并 |
| D10 | blocker | A | `references/casebook/entity-clustering.md` | `references/playbook-entity-cluster-methods.md` | 部署时间被误作公共设施充分条件 |
| D11 | blocker | A | `references/playbook-evidence-wording.md` | `references/independent-audit-protocol.md` | 完整阴性证明仍用已废止的 0.5% 线 |
| D12 | blocker | A | `references/independent-audit-protocol.md` | `references/split-run.md`、`references/scan-schemas.md` | Solana 四查清单遗漏第五项 |
| D13 | minor | B | `references/analyze-workflow.md`、`references/split-run.md` | `scripts/report/holder_distribution_scan.py` | 默认快照优先级描述过期 |
| D14 | minor | B | `references/labels/README.md` | `scripts/solana/build_evolution.py` | 不存在承诺的 `--no-labels` 开关 |
| D15 | minor | B | `references/data-pipeline-evm-channels.md` | `scripts/evm/fetch_hypersync_v2.py` | 原生 done v3 描述落后于 v4 |
| D16 | minor | B | `references/data-pipeline-evm-channels.md` | `scripts/evm/transfers_lib.py` | 整表读取描述与分批实现相反 |
| D17 | minor | A | `references/data-pipeline-evm-channels.md` | `references/data-pipeline-evm-sources.md` | API 全路径失效结论与明确修正并存 |
| D18 | minor | A | `references/labels/MAINTENANCE.md` | 同文件 | 两个来源同时被称为最高优先级 |
| D19 | nit | A | `references/split-run.md` | `references/analyze-workflow.md` | A3 主序交叉引用编号过期 |
