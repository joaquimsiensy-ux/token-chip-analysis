# 工单 R1：口径漂移与文档-代码不符修复（盲审 R1 消化）v1

基线：main HEAD=4445443（VERSION 7.1.1）。来源：`blind_r1_report.md`（codex 只读盲审 19 条）＋ Fable 亲核补充 F1/D5b、待确认转正 C1/C2。
本工单**只改文本**。D1 涉及改代码，已单列为"暂缓项"等用户审批，本轮不施工。

## §0 施工纪律（约束施工者，不约束被测代码既有行为）
0.1 开工先 `git status --short` 必须为空、`git rev-parse HEAD` 必须为本工单基线（Fable 会把本工单先 commit）；不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`。
0.3 **白名单**（只准改这些文件，超出即违规）：
`SKILL.md`、`commands-staging/token-analyze-2.md`、
`references/analyze-workflow.md`、`references/data-pipeline-evm-recon.md`、`references/data-pipeline-evm-sources.md`、`references/data-pipeline-evm-channels.md`、`references/data-pipeline-solana-capture.md`、`references/data-pipeline-solana-scan.md`、`references/playbook-supply-recon.md`、`references/playbook-entity-cluster-tiering.md`、`references/playbook-entity-cluster-methods.md`、`references/playbook-evidence-wording.md`、`references/independent-audit-protocol.md`、`references/split-run.md`、`references/report-template.md`、`references/labels/README.md`、`references/labels/MAINTENANCE.md`、`references/casebook/entity-clustering.md`，
以及新建报告 `maintenance/repair-20260916-drift-audit/r1_done.md`。
0.4 修法优先级：删除 > 修改 > 新增。**不新增章节、不新增条目、不新增文件**（r1_done.md 除外）。每处改动只动本工单指定的句子；行号与锚文本不一致即停工汇报，不自行猜测。
0.5 不 commit（Fable 验收后代 commit）。不部署 `~/.claude/commands/`（沙箱写不到；`test_commands_deploy_sync.py` 预期红，由 Fable 部署后复验）。
0.6 若某处改动会撞 `scripts/tests/contract_manifest.json` 的 needle（docs_lint 报错），停工汇报，**不得改 manifest**。

## §1 硬约束（验收项）
1.1 字节：`SKILL.md` ≤ 8024；`cat references/*.md references/casebook/*.md references/labels/*.md | wc -c` ≤ 930850（基线，须**净减**）；`commands-staging/*.md` 合计 ≤ 8798。
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

## §2 逐条施工（锚文本＝改前原文片段，须 grep 命中恰 1 处）

### D2 时间抽查示例缺必填 `--input`
文件 `references/data-pipeline-evm-recon.md:152-154`。锚：`python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --rpc <独立archive节点> \`
改为三行：
```
python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --input <生成plan所用的merged转账数据> \
    --rpc <独立archive节点> --chain <eth|bsc|base|arbitrum> --token 0x标的 \
    --out time_spotcheck.json --final-block <数据截止块>
```

### D3 Base 通道册仍推荐已除名的 Alchemy 为主力
文件 `references/data-pipeline-evm-sources.md`
- :60 锚 `### 8.1 全量转账双通道拓扑（与 BSC 经验相反：高峰期 Alchemy 是主力）` → `### 8.1 全量转账通道实测（历史；Alchemy 已除名正式通道，正式 CSV 资格见 data-pipeline-evm-channels §1 末段）`
- :63 锚 `——Base 高峰期 Alchemy 反而是主力通道（PING，07-17）` → `——仅探索采集可用，不产正式收据（PING，07-17）`
- :64 整条删除。锚（行首）：`- **分段接力法（双通道 2:1 提速）**：`（该行以 `（PING，07-17）` 结尾）。
（:65 跨通道去重键陷阱保留不动。）

### D4 锚点法产物被正式编译链拒收
文件 `references/data-pipeline-solana-capture.md:48`。锚：`产出图1/图2 数据。` → `产出 \`sol-anchor-rows\` 序列，仅探索辅助、不进正式编译链（正式序列走 replay_edges/replay_duck）。`

### D5 EVM 对账"余额和=0"与代码/同文件相反
文件 `references/data-pipeline-evm-recon.md:13`。锚：`2. **全网余额和=0**：所有地址重建余额求和应为零（mint/burn 计入），不为零即漏了转账段。（SIREN，07）`
→ `2. **全网余额和=mint_total**：重建余额求和等于铸币总量（sink 收方照加，恒等式见下文 verify_recon 段），不等即漏了转账段。（SIREN，07）`

### D5b 同一旧口径在供应对账册的副本（Fable 补充）
文件 `references/playbook-supply-recon.md:41`。锚：`- 全网余额和 = 0（mint 计负、burn 计正后逐笔累加）（SIREN，07）`
→ `- 全网余额和 = mint_total（sink 收方照加；定义见 data-pipeline-evm-recon §1 第 2 条）（SIREN，07）`

### D6 GMGN"个位精确硬闸"与"比例黄灯"并存
文件 `references/playbook-supply-recon.md:42`。锚：`- 重建余额 vs GMGN top10 逐个对比，要求 **10/10 精确到个位**；`（整行替换，原行以 `（OPN，07）` 结尾）
→ `- 重建余额 vs 冻结块 RPC balanceOf 逐地址精确相等（硬 FAIL）；GMGN top10 只作 0.15pp 黄灯对表，规则见 data-pipeline-evm-recon §1 第 1 条（OPN，07；08-15 黄灯制）`

### D7 "合并口径含全部疑似"与严格/扩展双边界冲突
- `references/playbook-entity-cluster-tiering.md:31` 锚：`**合并口径含全部疑似关联地址（无论证据程度），同一时刻合并计算，` → `**合并口径按 strict／expanded 双边界（见本册"历史静置仓反向扫描后的双边界峰值"条），同一时刻合并计算，`
- `references/analyze-workflow.md:145` 锚：`合并口径含全部疑似关联地址。` → `合并口径按 strict／expanded 双边界。`

### D8 纯行为指纹"可到铁证"突破证据上限
- `references/playbook-entity-cluster-tiering.md:82` 锚：`三者叠加可到链上铁证。` → `三者叠加仍止于"高度疑似"，升铁证须组内资金闭环（methods 行为指纹总纲）。`
- `references/data-pipeline-solana-scan.md:133` 锚：`的关联硬证据（任一即可，叠加为铁案）` → `的关联指纹（任一即入候选；定级上限按 playbook-entity-cluster-tiering 类型③与 methods 行为指纹总纲）`
- `references/data-pipeline-solana-scan.md:135` 锚：`——最强铁证。` → `——最强行为指纹。`

### D9 Streamflow 服务 feePayer 被用作合并依据
文件 `references/data-pipeline-solana-scan.md:85`。锚：`多笔提取共用此 feePayer = 同一批操作，据此把散落的"新钱包"归回原实体。`
→ `多笔提取共用此 feePayer 只证明同用该服务，不作控制边；归属须沿代币流穿透（data-pipeline-solana-capture §7 第 7 条、casebook E-02/E-05）。`

### D10 判例库"先验三测"与正式"四测"冲突
文件 `references/casebook/entity-clustering.md:18`。锚：`**公共基础设施先验三测**（任一命中即出实体表、按设施单列）：①getCode 与已知协议标准字节码比对（PCS V3 池标准 22,962B 一比便知）；②部署时间早于代币创建＝公共设施；③多币服务检验（同时服务大量其他代币）。`
→ `**公共基础设施先验四测**（权威序列见 playbook-entity-cluster-methods 该条：四 selector＋Sourcify→getCode→部署时间只作公共信号→跨币服务面；未过四测不得入成员，按设施单列）。`
（同行其余文字、"必做区分检验"标签与 casebook 六字段结构不动。）

### D11 完整阴性结论沿用已废止的 0.5% 线
文件 `references/playbook-evidence-wording.md:106`。锚：`必须证明当前≥0.5% owner、` → `必须证明当前达到其他大户线（tiering §6a：≥0.1% 总供应或 ≥0.2% 流通）的 owner、`

### D12 独立复核协议的 Solana 对账清单缺第五查
文件 `references/independent-audit-protocol.md:166`。锚：`受控启动四查生产者生成：balance/supply=\`verify_recon.py\`、supply_truth=\`supply_truth_gate.py\`、time=\`time_spotcheck.py\`（Solana 对应 anchor sampler 与 holder snapshot）。`
→ `受控启动对账生产者生成（EVM 四查键集 balance,supply,supply_truth,time；Solana 五查另含 exact_reconcile，键集与生产者见 scan-schemas 对账 wrapper 表）。`

### F1 "四查"泛化提法（Fable 补充，与 D12 同族）
- `SKILL.md:32` 锚：`A2 四查（余额对账/供给闭合/供给真值闸/时间抽查）不过关不进分析。` → `A2 对账关卡（EVM 四查／Solana 五查）不过关不进分析。`
- `SKILL.md:45` 锚 `| 余额/供给闭合/供给真值/时间抽查 |` → `| 余额/供给闭合/供给真值/时间抽查，Solana 加精确重放 |`；同行锚 `| 四查不过不进 A3；` → `| 不过不进 A3；`
- `references/report-template.md:90` 锚：`（四查过关声明：余额对账/供给闭合/供给真值闸/时间抽查）` → `（EVM 四查／Solana 五查逐项过关声明）`
- `references/playbook-supply-recon.md:48` 锚：`Solana 走标准四查` → `Solana 走标准五查`
- `references/analyze-workflow.md:19` 锚：`A2 完成四查对账。` → `A2 完成对账关卡。`
- `references/split-run.md:126` 与 `commands-staging/token-analyze-2.md:13` 锚：`必读件**：anomalies.json、四查结论、` → `必读件**：anomalies.json、对账结论、`（两处须逐字同步）

### D13 `find_snapshot` 默认优先级描述过期
- `references/analyze-workflow.md:117-119` 锚（三行）：`必须显式指定观察快照，因为` / `\`holder_distribution_scan.find_snapshot\` 默认优先 \`data/holders_owners.json\`（冻结件），` / `而发布闸的分布绑定要求 observation bundle 的观察 owners。完整命令：`
  → 合并为：`必须显式指定观察快照（\`--snapshot\`），因为发布闸的分布绑定要求 observation bundle 的观察 owners。完整命令：`（保持原缩进；后一行完整命令不动）
- `references/split-run.md:54` 锚：`必须显式使用观察 owners；\`find_snapshot\` 默认优先 \`data/holders_owners.json\`（冻结件），发布闸分布绑定却要求 observation bundle 的观察件。` → `必须显式使用观察 owners（\`--snapshot\`），因为发布闸分布绑定要求 observation bundle 的观察件。`

### D14 `build_evolution.py` 无 `--no-labels`
文件 `references/labels/README.md:8`。锚：`均已默认接入（\`--no-labels\` 关闭）` → `均已默认接入（\`--no-labels\` 关闭；\`build_evolution.py\` 无此开关）`

### D15 native done 版本号
文件 `references/data-pipeline-evm-channels.md:69`。锚：`native done v3` → `native done v4`

### D16 transfers_lib 整表读描述过期
文件 `references/data-pipeline-evm-channels.md:272`。整行删除。锚（行首）：`| **transfers_lib 整表读大 parquet 必 OOM** |`

### D17 four.meme API"全路径 404"与同库修正并存
文件 `references/data-pipeline-evm-channels.md:259`。锚：`meme-api 全路径已 404，正身改看创世 tx HTML 是否触及` → `正身查 meme-api（可用性以 data-pipeline-evm-sources 表为准）或创世 tx HTML 是否触及`

### D18 标签来源两个"最高"
文件 `references/labels/MAINTENANCE.md:19`。锚：`| 最高，优先级压过一切 |` → `| 次高（SRC_PRIORITY=0，仅低于 curation） |`

### D19 split-run 主序编号过期
文件 `references/split-run.md`：
- :44 锚 `**A3 机械子层**（对照 analyze-workflow A3 主序编号）：` → `**A3 机械子层**：`
- :45 删 `（主序第 1 项前半）`；:46 删 `（主序第 1 项中段的脚本执行侧）`；:47 删 `（主序第 5 项的批量侧）`；:48 删 `（主序第 1 项后半的算法侧）`

### C1 SQD 采集上界描述与生产者不符（待确认 1 转正）
文件 `references/data-pipeline-solana-capture.md:134`。锚：`采集上界取 \`/head\` 没问题（实测到 head 仍正常返回数据）,但别拿两者的差当异常。` → `生产者上界压到 finalized slot（\`fetch_sqd_transfers_v2.py\`），别拿两者的差当异常。`

### C2 方法册 `wave_scan v3` 版本号过期（待确认 2 转正）
文件 `references/playbook-entity-cluster-methods.md:171`。两处：锚 `wave_scan v3 全体历史峰值` → `wave_scan 全体历史峰值`；锚 `**权威脚本**：wave_scan v3、` → `**权威脚本**：wave_scan、`。（`候选全集从三条现役机械通道取齐` 是契约 needle，原样保留。）

## §3 暂缓项（本轮不施工）
- **D1 [需改代码]** `scripts/report/wave_scan.py:735-746` 浮点阈值 vs `analyze-workflow.md:161`"份额阈值一律整数运算"。已复现边界漏判（total=10^24、持仓恰 0.1% 时判 False）。改文本掩盖缺陷不可取；改代码需用户审批，见 Fable 汇报。

## §4 完成报告 `r1_done.md` 必含
①逐条 D/F/C 编号的改前→改后 diff 片段；②§1.1 三个字节数实测；③§1.2 每条命令原始输出；④`git diff --stat`；⑤与工单的任何差异与停工点；⑥是否读过 `~/.codex`（如实）。
