# 工单 R1：口径漂移与文档-代码不符修复（盲审 R1 消化）v2

v2 变更（消化 `review_r1_reply.md` 退回意见）：去掉锚文本中多余的反斜杠；章节号改正（evm-recon 对账 gate＝§5、capture Streamflow 条＝§9）；D2 只列正式链；D5/D5b/D6/D8/D10/D12/D14/D17/C1 采纳复核修订文本；F1 补白名单内 7 处并扩白名单纳入 context-discipline/scan-schemas 5 处；D8 补 4 处同族；D10 补 :19；§0.1 区分内容基线与施工 HEAD。
内容基线：`444544360179d5080657aafd5ad60a78fe89e9b3`（VERSION 7.1.1；§2 所涉文件、`scripts/`、`VERSION` 相对该基线未变）。来源：`blind_r1_report.md`＋Fable 亲核补充 F1/D5b、待确认转正 C1/C2。
本工单**只改文本**。D1 涉及改代码，记入 `code_change_pending.md`，循环结束后统一交用户决策，本轮不施工。

## §0 施工纪律（约束施工者，不约束被测代码既有行为）
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD。工单落档提交允许存在；但 §2 所涉文件、`scripts/`、`VERSION` 相对内容基线必须未变（`git diff --stat 4445443 HEAD -- SKILL.md references scripts commands-staging VERSION` 须为空）。不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`。
0.3 **白名单**（只准改这些文件，超出即违规）：
`SKILL.md`、`commands-staging/token-analyze-2.md`、
`references/analyze-workflow.md`、`references/context-discipline.md`、`references/scan-schemas.md`、`references/data-pipeline-evm-recon.md`、`references/data-pipeline-evm-sources.md`、`references/data-pipeline-evm-channels.md`、`references/data-pipeline-solana-capture.md`、`references/data-pipeline-solana-scan.md`、`references/playbook-supply-recon.md`、`references/playbook-entity-cluster-tiering.md`、`references/playbook-entity-cluster-methods.md`、`references/playbook-evidence-wording.md`、`references/independent-audit-protocol.md`、`references/split-run.md`、`references/report-template.md`、`references/labels/README.md`、`references/labels/MAINTENANCE.md`、`references/casebook/entity-clustering.md`，
以及新建报告 `maintenance/repair-20260916-drift-audit/r1_done.md`。
0.4 修法优先级：删除 > 修改 > 新增。**不新增章节、不新增条目、不新增文件**（r1_done.md 除外）。全部锚文本先在冻结的改前文本上逐项 `grep -n -F` 核验（须恰 1 处且行号一致）；同一文件按改前位置从后向前替换。任一锚不唯一或行号不符即停工汇报，不自行猜测。只动本工单指定的片段，同行其余文字不动。
0.5 不 commit（Fable 验收后代 commit）。不部署 `~/.claude/commands/`（沙箱写不到；`test_commands_deploy_sync.py` 预期红，由 Fable 部署后复验）。
0.6 若某处改动会撞 `scripts/tests/contract_manifest.json` 的 needle（docs_lint 报错），停工汇报，**不得改 manifest**。

## §1 硬约束（验收项）
1.1 字节：`SKILL.md` ≤ 8024；`cat references/*.md references/casebook/*.md references/labels/*.md | wc -c` ≤ 930850（基线，须**净减**；统计时 attic.md 只计字节不读内容）；`commands-staging/*.md` 合计 ≤ 8798。
1.2 守卫全绿（改完必跑，输出贴进 r1_done.md）：
```
python3 scripts/tests/docs_lint.py && python3 scripts/tests/docs_lint.py --all
python3 scripts/tests/casebook_lint.py
python3 scripts/tests/changelog_lint.py
python3 scripts/tests/test_contract_routes.py
python3 scripts/tests/test_sixlens_docs.py
python3 scripts/tests/test_g3_docs_guards.py
python3 scripts/tests/test_version_consistency.py
```
1.3 `git diff --stat` 只含白名单文件。

## §2 逐条施工（锚文本＝改前原文片段，`grep -n -F` 须恰 1 处）

### D2 时间抽查示例缺必填 `--input`
`references/data-pipeline-evm-recon.md:152-154`。锚（152 行）：`python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --rpc <独立archive节点> \`
152-154 三行整体改为：
```
python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --input <生成plan所用的merged转账数据> \
    --rpc <独立archive节点> --chain <eth|bsc|base> --token 0x标的 \
    --out time_spotcheck.json --final-block <数据截止块>
```
（Arbitrum 属探索档须另带 `--exploration`，不并入正式示例，故从示例删除。）

### D3 Base 通道册仍推荐已除名的 Alchemy 为主力
`references/data-pipeline-evm-sources.md`
- :60 锚 `### 8.1 全量转账双通道拓扑（与 BSC 经验相反：高峰期 Alchemy 是主力）` → `### 8.1 全量转账通道实测（历史；Alchemy 已除名正式通道，正式 CSV 资格见 data-pipeline-evm-channels §1 末段）`
- :63 锚 `——Base 高峰期 Alchemy 反而是主力通道（PING，07-17）` → `——仅探索采集可用，不产正式收据（PING，07-17）`
- :64 整行删除。锚（行首）：`- **分段接力法（双通道 2:1 提速）**：`
（:65 跨通道去重键陷阱保留。）

### D4 锚点法产物被正式编译链拒收
`references/data-pipeline-solana-capture.md:48`。锚：`产出图1/图2 数据。` → `产出 `sol-anchor-rows` 序列，仅探索辅助、不进正式编译链（正式序列走 replay_edges/replay_duck）。`

### D5 EVM 对账"余额和=0"与代码/同文件相反
`references/data-pipeline-evm-recon.md:13`。锚：`2. **全网余额和=0**：所有地址重建余额求和应为零（mint/burn 计入），不为零即漏了转账段。（SIREN，07）`
→ `2. **全网余额和=mint_total**：重建余额按 raw integer 求和等于铸币总量（sink 收方照加），不等即对账失败，须排查数据或重放口径。（SIREN，07）`

### D5b 同一旧口径在供应对账册的副本
`references/playbook-supply-recon.md:41`。锚：`- 全网余额和 = 0（mint 计负、burn 计正后逐笔累加）（SIREN，07）`
→ `- 全网余额和 = mint_total（sink 收方照加；定义见 data-pipeline-evm-recon §5 第 2 条）（SIREN，07）`

### D6 GMGN"个位精确硬闸"与"比例黄灯"并存
`references/playbook-supply-recon.md:42` 整行替换。锚（行首）：`- 重建余额 vs GMGN top10 逐个对比，要求 **10/10 精确到个位**；`
→ `- 按 verify_recon 所选 top-N 与冻结块 RPC balanceOf 逐地址精确对账，差异或观测失败均阻断；GMGN top10 差异 ≥0.15pp 时记黄灯，并在发布前绑定合格查证说明（data-pipeline-evm-recon §5 第 1 条；OPN，07；08-15 黄灯制）`

### D7 "合并口径含全部疑似"与严格/扩展双边界冲突
- `references/playbook-entity-cluster-tiering.md:31` 锚：`**合并口径含全部疑似关联地址（无论证据程度），同一时刻合并计算，` → `**合并口径按 strict／expanded 双边界（见本册"历史静置仓反向扫描后的双边界峰值"条），同一时刻合并计算，`
- `references/analyze-workflow.md:145` 锚：`合并口径含全部疑似关联地址。` → `合并口径按 strict／expanded 双边界。`

### D8 纯行为指纹"可到铁证"突破证据上限（总闸＝methods:144"行为指纹三问总闸与强弱两档"）
- `references/playbook-entity-cluster-tiering.md:82` 两处：锚 `三者叠加可到链上铁证。` → `三者叠加仍只作行为证据；定级须过 methods"行为指纹三问总闸与强弱两档"，无独立控制证据时最高为"高度疑似"。`；锚 `gas 不同源时只能写行为级同一实体，不得写资金同源。` → `未补独立控制证据不得确证同一实体；gas 不同源不得写资金同源。`
- `references/data-pipeline-solana-scan.md:133` 锚 `的关联硬证据（任一即可，叠加为铁案）` → `的关联候选指纹（定级须过 playbook-entity-cluster-methods"行为指纹三问总闸与强弱两档"；纯行为最高为"高度疑似"）`
- `references/data-pipeline-solana-scan.md:135` 整行替换。锚（行首）：`1. **同 slot 原子下单**：` → `1. **同 slot 共现**：多钱包同 slot 同买同卖只作候选发现；用 pre/postTokenBalances 按 `(mint,side)` 定位后，须排除公共工具和协议机制；同 slot 本身不证明原子 bundle 或单一控制端。`
- `references/data-pipeline-solana-scan.md:139` 锚 `= 脚本驱动铁证。` → `只作行为候选，须过同期分母与工具/协议对照，不据此确证同一实体。`
- `references/playbook-entity-cluster-methods.md:134` 两处：锚 `①**配对自证**` → `①**配对指纹候选**`；锚 `=批量定制的配对地址，同一实体最硬指纹之一（铁证级；识别看中段不看前缀）` → `只作定制地址候选指纹；须过行为指纹三问总闸，不能仅据共享中段确证同一实体（识别看中段不看前缀）`

### D9 Streamflow 服务 feePayer 被用作合并依据
`references/data-pipeline-solana-scan.md:85`。锚：`多笔提取共用此 feePayer = 同一批操作，据此把散落的"新钱包"归回原实体。`
→ `多笔提取共用此 feePayer 只证明同用该服务，不作控制边；归属须沿代币流穿透（data-pipeline-solana-capture §9 第 7 条、casebook E-02/E-05）。`

### D10 判例库"先验三测"与正式"四测"冲突
`references/casebook/entity-clustering.md`
- :18 锚：`**公共基础设施先验三测**（任一命中即出实体表、按设施单列）：①getCode 与已知协议标准字节码比对（PCS V3 池标准 22,962B 一比便知）；②部署时间早于代币创建＝公共设施；③多币服务检验（同时服务大量其他代币）。`
  → `**公共基础设施先验四测**（按 playbook-entity-cluster-methods"公共基础设施先验四测"执行；未完成核验不得入成员或惯犯库，列为未定性；确认公共设施后按设施单列）。`
- :19 锚：`三测做不全时` → `四测做不全时`
（"必做区分检验"等六字段标签与同行其余文字不动。）

### D11 完整阴性结论沿用已废止的 0.5% 线
`references/playbook-evidence-wording.md:106`。锚：`必须证明当前≥0.5% owner、` → `必须证明当前达到其他大户线（tiering §6a：≥0.1% 总供应或 ≥0.2% 流通）的 owner、`

### D12 独立复核协议的 Solana 对账清单缺第五查
`references/independent-audit-protocol.md:166`。锚：`受控启动四查生产者生成：balance/supply=`verify_recon.py`、supply_truth=`supply_truth_gate.py`、time=`time_spotcheck.py`（Solana 对应 anchor sampler 与 holder snapshot）。`
→ `受控启动各链对账生产者生成（EVM 四查、Solana 五查；键序见 scan-schemas §14.10，逐查生产者见 scripts/report/shared_release_receipt.py 的 RECON_PRODUCERS）。`

### F1 "四查"泛化提法（与 D12 同族；EVM 专属语境与历史条目不改）
- `SKILL.md:32` 锚：`A2 四查（余额对账/供给闭合/供给真值闸/时间抽查）不过关不进分析。` → `A2 对账关卡（EVM 四查／Solana 五查）不过关不进分析。`
- `SKILL.md:45` 锚 `| 余额/供给闭合/供给真值/时间抽查 |` → `| 余额/供给闭合/供给真值/时间抽查，Solana 加精确重放 |`；同行锚 `| 四查不过不进 A3；` → `| 不过不进 A3；`
- `references/report-template.md:90` 锚：`（四查过关声明：余额对账/供给闭合/供给真值闸/时间抽查）` → `（EVM 四查／Solana 五查逐项过关声明）`
- `references/playbook-supply-recon.md:38` 整行替换。锚（行首）：`**总原则：重建/采集结果必须与独立数据源精确对表后才允许进入分析。` → `**总原则：按 analyze-workflow A2 完成全部对账关卡后才进入分析；EVM 四查、Solana 五查（另含 exact_reconcile）。** 下方各链条目为历史校验形态，归入对账关卡执行、不替代正式查项；GMGN 黄灯处理见 data-pipeline-evm-recon §5 第 1 条。`
- `references/playbook-supply-recon.md:48` 锚：`Solana 走标准四查` → `Solana 走标准五查`
- `references/analyze-workflow.md:19` 锚：`A2 完成四查对账。` → `A2 完成对账关卡。`
- `references/analyze-workflow.md:46` 锚：`采集 receipt、四查、标签 resolver` → `采集 receipt、按链定义的对账关卡、标签 resolver`
- `references/analyze-workflow.md:112` 锚：`必须与 A2 四查里 `verify_recon --balances` 吃的是同一个文件` → `必须与 A2 权威输入是同一个文件`
- `references/analyze-workflow.md:114` 锚：`去对四查` → `去对 A2`
- `references/split-run.md:53` 两处：锚 `必须与 A2 四查 `verify_recon --balances` 吃的是同一个文件` → `必须与 A2 权威输入是同一个文件`；锚 `（EVM 对四查 balance 收据的` → `（EVM 对 balance 收据的`
- `references/split-run.md:98` 两处：锚 `四查 producer receipt` → `A2 全部 producer receipt`；锚 `四查 receipt 格式零改动` → `各项 receipt 按现行 schema 提供`
- `references/split-run.md:126` 与 `commands-staging/token-analyze-2.md:13` 锚：`必读件**：anomalies.json、四查结论、` → `必读件**：anomalies.json、对账结论、`（两处逐字同步）
- `references/split-run.md:143` 锚：`verify＋四查兜底` → `verify＋A2 全部对账关卡兜底`
- `references/context-discipline.md:27` 锚：`对账四查执行` → `A2 对账执行`
- `references/context-discipline.md:58` 锚：`对账四查若断前已过` → `A2 对账若断前已过`
- `references/scan-schemas.md:17` 锚：`（four-check 对账）` → `（A2 对账关卡）`
- `references/scan-schemas.md:396` 两处：锚 `必须就是四查真正核过的那一份：EVM 比对四查 `balance` 收据的` → `必须就是 A2 真正核过的那一份：EVM 比对 `balance` 收据的`；锚 `两份都要落在同一个四查 sha 上` → `两份都要落在同一个 A2 快照 sha 上`
- `references/scan-schemas.md:484` 锚：`"快照↔四查绑定"` → `"快照↔A2 绑定"`

### D13 `find_snapshot` 默认优先级描述过期
- `references/analyze-workflow.md:117-119`。锚（118 行）：``holder_distribution_scan.find_snapshot` 默认优先 `data/holders_owners.json`（冻结件），`。117 行自 `必须显式指定观察快照，因为` 起、118 全行、119 行至 `完整命令：` 止，合并为：`必须显式指定观察快照（`--snapshot`），因为发布闸的分布绑定要求 observation bundle 的观察 owners。完整命令：`（保留 117 行前缀"动态 Solana（`exact_reconcile` 早于 wrapper）"与缩进；120 行完整命令不动）
- `references/split-run.md:54` 锚：`必须显式使用观察 owners；`find_snapshot` 默认优先 `data/holders_owners.json`（冻结件），发布闸分布绑定却要求 observation bundle 的观察件。` → `必须显式使用观察 owners（`--snapshot`），因为发布闸分布绑定要求 observation bundle 的观察件。`

### D14 `build_evolution.py`/`label_lookup.py` 无 `--no-labels`
`references/labels/README.md:8`。锚：`均已默认接入（`--no-labels` 关闭）` → `均已默认接入`

### D15 native done 版本号
`references/data-pipeline-evm-channels.md:69`。锚：`native done v3` → `native done v4`

### D16 transfers_lib 整表读描述过期
`references/data-pipeline-evm-channels.md:272` 整行删除。锚（行首）：`| **transfers_lib 整表读大 parquet 必 OOM** |`

### D17 four.meme API"全路径 404"与同库修正并存
`references/data-pipeline-evm-channels.md:259`。锚：`meme-api 全路径已 404，正身改看创世 tx HTML 是否触及` → `正身可试 meme-api（历史实测见 data-pipeline-evm-sources，当前可用性须实测），或查创世 tx HTML 是否触及`

### D18 标签来源两个"最高"
`references/labels/MAINTENANCE.md:19`。锚：`| 最高，优先级压过一切 |` → `| 次高（SRC_PRIORITY=0，仅低于 curation） |`

### D19 split-run 主序编号过期
`references/split-run.md`：
- :44 锚 `**A3 机械子层**（对照 analyze-workflow A3 主序编号）：` → `**A3 机械子层**：`
- :45 删 `（主序第 1 项前半）`；:46 删 `（主序第 1 项中段的脚本执行侧）`；:47 删 `（主序第 5 项的批量侧）`；:48 删 `（主序第 1 项后半的算法侧）`

### C1 SQD 采集上界描述与生产者不符
`references/data-pipeline-solana-capture.md:134`。锚：`采集上界取 `/head` 没问题（实测到 head 仍正常返回数据）,但别拿两者的差当异常。` → `生产者上界不超过 finalized slot，并与 `/head`、可选 `--to-slot` 取较小值（`fetch_sqd_transfers_v2.py`），别拿两者的差当异常。`

### C2 方法册 `wave_scan v3` 版本号过期
`references/playbook-entity-cluster-methods.md:171` 两处：锚 `wave_scan v3 全体历史峰值` → `wave_scan 全体历史峰值`；锚 `**权威脚本**：wave_scan v3、` → `**权威脚本**：wave_scan、`（`候选全集从三条现役机械通道取齐` 是契约 needle，原样保留。）

## §3 暂缓项（本轮不施工）
- **D1 [需改代码]** 见 `code_change_pending.md`。

## §4 完成报告 `r1_done.md` 必含
①逐条 D/F/C 编号的改前→改后 diff 片段；②§1.1 三个字节数实测；③§1.2 每条命令原始输出；④`git diff --stat`；⑤与工单的任何差异与停工点；⑥是否读过 `~/.codex`（如实）。
