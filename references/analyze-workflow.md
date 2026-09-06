# 完整版分析手册（/token-analyze，A0–A6）

> v6.0.0 承接旧 SKILL.md 全部阶段细节（规则语义零变更）。本手册是各阶段执行细节的唯一权威源；判定类失败模式在 `casebook/`（只指不抄）；上下文与外包纪律在 `context-discipline.md`；按需研究与异构复核在 `research-workflows.md`；链专属操作在各 data-pipeline 文档。

## 通用执行纪律（全阶段生效）

- 优先跑 `scripts/` 固化脚本，禁止现场重写已有能力的脚本；不满足需求先改参数再改脚本，改动记入 A6。
- **关键字符串（地址/哈希）一律从落盘文件取**，从打印输出复制截断补全＝编造。
- 脚本产出判定以代码写入语句＋文件时间戳为准，stdout 叙述不可信（environment.md「stdout 与实际行为不一致」条）。
- 免费层限流当场翻车：限速常数实测收敛；退避＋断点续传标配；卡点超 1–2h 摆路径给用户选，不单通道死等。
- 本机环境坑（SSL/字体/shell/沙箱杀进程等）开工 preflight 只扫 `environment.md` 坑速查（扫≠整读）；运行异常或涉及 OS/Python/字体/SSL/shell 时再深读对应节。

## 入口分流（唯一权威）

- 用户以自然语言要求**复核、审计或核验既有筹码报告/第三方报告/旧版分析**时，进入
  `independent-audit-protocol.md` 净室复核轨；不新增 slash command。旧报告只拆成
  `claim_registry.json` 待审命题，正文、实体表、标签、衍生 JSON 与图表均不作证据输入。
- 净室轨与新分析共用 A0–A2 骨架：A0 核定标的、链范围、分母和记账模型，A1 独立采集原始数据
  并冻结 `audit_input_manifest.json`，A2 完成四查对账。A3 起以净室协议重建实体、三账、历史序列和
  命题裁决；A4 使用 `--workflow-type independent-audit`，A5 仅以
  `build_html.py --mode analysis-audit` 编译并强制 `audit_release_gate --profile independent-audit`。
- 不满足上述触发条件的新币/新分析走标准 A0–A5、`--workflow-type new-analysis` 与
  `build_html.py --mode analysis-new`。两轨不得互相猜 profile 或共用被审报告的衍生结论。

## A0 标的画像与链路由

产出计划落盘，**用户决策点前置**：口径选择/新数据源注册/key 索取这类需要用户拍板的事项，在计划阶段用 AskUserQuestion 给选项一次问清，不在分析中途零散打断。

先核定：合约/mint 地址（多源交叉，确认用户持有的到底是哪个）、部署在哪几条链、**总量与流通量多口径分开标注**（链上实查/第三方流通/名义已解锁——口径混淆是历次实战最高频的结论级错误源，见 casebook S 册）、DEX 真实流动性（<$50k 则定价权在 CEX，分析重心＝托管流＋金库＋充提）。

**多链代币硬关卡（不过关不开工）**："部署在哪几条链"不是登记项，是分流关卡。CoinGecko `coins/{id}` platforms 字段＋GMGN/Dexscreener＋官方文档多源核查；凡部署 ≥2 条链，必须先做**链分布盘点**——各链 RPC 实查该链供给（桥接分支按 mint−burn 口径；
  **镜像关系先做锁仓适配器配平**，见 casebook S-02），产出链分布表（链/合约地址/该链供给及占全局总供应%/主 DEX 流动性/预估转账量级与采集耗时），连成本预估一起用 AskUserQuestion 让用户选定分析范围（推荐项＝供给占比最大的主链；选项：仅主链/主链＋指定分支/全部链）。
  **禁止拿到地址就按其所在链直接开工**——用户给的地址可能只是小分支链（VIRTUAL 案范围性返工，07-16）。占全局 <5% 的分支默认不单独立项（用户点名除外）；选多链时各链分别过 A2 对账再合并口径。报告 TL;DR 首行必须声明分析范围（覆盖哪几条链、合计占全局总供应%），规范见 report-template.md。

另核定两件事：①**标的是否带解锁表/vesting**（tokenomist/dropstab 有记录，或链上有锁仓合约/多签托管）——有则问 3 必须包含"未来 6–12 个月解锁日程与量级"小节（要求见 report-template.md）；②**开工版本自查**：读 `VERSION` 文件并在计划里注明，交付前重读一次——版本号变了说明 skill 被并行会话更新过，向用户提示框架可能已迭代。

**链路由表**：

| 标的形态 | 读哪份 pipeline / 跑哪套脚本 |
|---|---|
| 0x 地址，Ethereum/BSC/Base（正式） | 进入 `data-pipeline-evm.md` 通道决策树＋ `scripts/evm/` |
| 0x 地址，Arbitrum（探索） | 可跑 EVM 采集、对账与身份快照；已有 CEX-only 初版标签表但覆盖不完整，仍为 exploration，禁止 A4/A5 seal 与 formal compile |
| base58 mint | `data-pipeline-solana.md`（双 RPC 按方法路由见其分册 §0a） |
| 0x 地址，Robinhood Chain（exploration only） | 可路由至 `data-pipeline-robinhood.md` ＋ `scripts/robinhood/`；禁止 A4/A5 seal 与正式 analysis 编译 |
| 跨链部署（OFT/CCIP 等） | 先过多链硬关卡选定范围 → 各链按其 pipeline 采集＋跨链 mint/burn 配平；桥接分支链范式见 playbook §6a |
| 全新链 | 新链 SOP：先实测数据面并实现采集 receipt、四查、标签 resolver 与 G8 chain 适配；这些正式门禁未齐前只能交付明确降级的探索结果，不得编译正式 analysis |

**通道实测探路**：写任何采集脚本前，先用 1–2 分钟小请求逐个实测候选数据源（可用性/返回结构/分页/上限/限速）；拿到任何新 key 先做 1 分钟能力探测再承诺方案；禁止基于文档想象设计方案。

**记账模型准入 gate（链路由定型后、采集开工前必跑）**：fee-on-transfer/rebase/Token-2022 扩展会让"Transfer 流水重建余额"整体算错且供给闭合发现不了（模型错但自洽）。一条命令 1 分钟出裁决——EVM `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --exploration --out accounting_mode.exploration.json`（eth 侧 --rpc 传 Alchemy 检测更强）；Solana `python3 scripts/solana/accounting_gate_sol.py --mint <mint> --out accounting_mode.json`。A0 是模型预检：EVM 使用探索档并产 `accounting-gate/v1`，文件名固定为 `accounting_mode.exploration.json`，不得占用正式名；正式 `accounting_mode.json` 在 A2 生成 observation bundle 后重跑产出（见 A2 第 3 查）。**exit 0（standard/WARN 级）＝放行**，WARN 逐条抄进报告数据底座节；**exit 2（BLOCK）＝硬停**——向用户报模式与证据，要继续必须人工定制记账模型，禁止套标准管线；**exit 1（检测自身失败）＝修通道重跑，禁止当 standard 放行**。检测原理与判定表见脚本头注。EVM 正式发布产物须带**双时点诚实记录**（批 A F-01/F-B）：`tip_block`（探测时链头）必填且 `as_of_block <= tip_block`，探测块另记 `model_probe_block` 且必须等于 `tip_block`——消费侧两个字段都验，想抬时点必须同时改两处且保持自洽。

## A1 并行采集（一次性全部启动）

三路并行：①**全量链上数据**（最耗时最先启动，后台跑；采集脚本标配＝限速可调/退避重试/断点续传/失败段补扫/冒烟小样本先行）②地址标签与安全面（GMGN、浏览器标签页）③价格（CoinGecko/binance.vision）。**vesting 标的加一路解锁情报轻量 agent**（tokenomist/dropstab 多源交叉，见 research-workflows §1 路线 1——下一次大解锁的时间和量是问 3 解锁小节的核心输入）。（v5.0 问 4 删除后背景调研整路退役；research-workflows §1 其余路线按需作分析工具，不再默认启动。）

长任务运维：最长任务最先启动、等待期填满下游脚本编写、零进展要告警、预估偏差超 2 倍主动汇报（抽样外推报保守上限）、废弃通道同步停掉观察哨。

**既有采集产物复用**：开工先查工作目录是否已有采集产物（EVM＝`data/v2/run_*/done.json`，Solana＝`data/soltx-*.jsonl.gz`＋meta）——有则**直接复用并断点续拉增量到最新**（底层采集器天然幂等），禁止无视既有产物从零重采；完整性以当链 `done.json`、`collection_manifest.json`/receipt 为准，链内 manifest/receipt 证明单链数据范围。`done_with_gaps` 必须先补齐缺口再进对账。

## A2 对账关卡（硬性，EVM 四查／Solana 五查全过才进分析）

1. **余额对账**：重建结果 vs 独立数据源精确对表（形态见各链 pipeline recon 分册）。
2. **供给闭合**：总量恒等式/mint−burn 配平（内部自洽检验）。
   分母定夺与重放收尾先过 `casebook/supply-accounting.md` 和
   `casebook/supply-accounting-methods.md` 的触发现象与区分检验。
3. **供给真值闸（v6 新增，重放收尾必跑）**：EVM 先运行 `python3 scripts/evm/observe_supply.py --chain <eth|bsc|base> --token 0x… --as-of-block <冻结块> --out evm_observation_bundle.json --transcript-out evm_observation_transcript.json`，再运行 `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --bundle evm_observation_bundle.json --as-of-block <冻结块> --out accounting_mode.json`，最后运行 `python3 scripts/lib/supply_truth_gate.py --chain <链> --token 0x… --as-of-block <冻结块> --replay-stats <replay_stats.json> --observation-bundle evm_observation_bundle.json --out supply_truth.json`，产 `supply-truth-receipt/v4`；Solana 仍产 `supply-truth-receipt/v3`。正式记账重跑产 `accounting-gate/v2`，是发布消费面唯一认可的记账收据；A2 formal 结果为唯一 canonical，与 A0 预检结论不同时以 formal 为准并停止后续阶段等待人工裁决。两者均绑定 target。主规则按形态①对比 `mint−burn` 与链上 `totalSupply()`；EVM 主 FAIL 且拆分统计齐全时，形态②自动要求 `mint==totalSupply`、ZERO/dead 各自与冻结块 `balanceOf` 逐地址相等、两 sink 合计与 burn 闭合。这里只证明终态标量与 sink 逐地址归因闭合；混合形态、旧 stats 或任一观测失败均维持 fail-closed（见 casebook S-01/S-11）。

   容差政策按以下三段执行；`approved_tolerance_bps`、`observed_diff_bps`、本次申请 `tolerance_bps` 与消费侧独立重算的实际偏差四值取最大值定区，所有 waiver/approval 数值必须有限（含超出 float 范围的巨整数一律拒绝），JSON 中 `NaN`、`Infinity`、`-Infinity` 一律拒绝。

   | 最大值 | 放行凭据 |
   |---|---|
   | ≤10bps | 自动容差区，不需要 waiver |
   | >10bps 且 ≤100bps | 必须有合法 `tolerance-waiver/v1` 普通人工豁免单 |
   | >100bps | waiver 之外，必须再绑定独立 `over-cap-approval/v1` 用户特批收据；缺件或验不过即政策拒绝 |

   `tolerance-waiver/v1` 必须写明批准容差、裁决人、UTC 决定时间、本次实际偏差 `observed_diff_bps`、与本次全等的 target、绑定本次 `--replay-stats` 的 path/size/sha256，以及至少一份独立于 replay_stats 和 over-cap approval 的人工核对证据与理由；所有人工文本字段须含实义字符（不可见字符不算）。`over-cap-approval/v1` 必须以安全相对 path/size/sha256 绑定在 waiver 同目录，并同时进入 supply truth 收据 `inputs`；request 逐项绑定 target、记录偏差、申请容差、replay_stats 实物与理由；生产侧和消费侧都独立重算 request 规范 JSON 的 `request_sha256`，并校验 nonce、有效期不超过 30 天、用户批复原文、已向用户报告的偏差原因、批准主体与决定时间。非超顶区若主动挂了 approval 引用，也必须完整验真。

   **流程要求**：Fable 必须在当前会话内向用户如实报告偏差原因并取得明确批复后，才可写 `over-cap-approval/v1`；不得把普通 waiver 自行升级成用户特批。用户批复必须含文字（中英文等白名单语种），纯表情符号不构成有效批复文本。此设计防工作流走捷径/误操作，不防持同用户权限的恶意进程。

   **退出语义**：exit 0＝PASS。exit 2 有两种情况，看有没有落收据来分：落了收据＝FAIL；若同 target、同 schema 家族的旧 PASS 在场，kernel 会先以同目录 hard-link 将它归档为 `.superseded-<UTC微秒>.<PID>`，再原子替换 canonical，FAIL 仍返回 exit 2，不得误报通道故障 exit 1。该币余额禁用重放结果并改 Multicall3/RPC 实时直查（地址全集与转账历史仍可用重放，重放余额仅作 ≥阈值超集筛选）；没落收据＝容差政策拒绝（缺 waiver/approval、凭据不合法或未覆盖本次实际偏差），不是 FAIL。政策拒绝会把上一轮旧收据自动作废归档为 `supply_truth.json.superseded-<UTC>`，案内不再有现役收据，下游缺件即停；归档失败升格 exit 1；凭据内容导致的解析异常归 exit 2，同样履行旧收据自动作废归档。exit 1＝检测自身失败（含凭据文件读不动等通道故障），修通道重跑，禁当 PASS。
4. **时间抽查**：EVM 走分层计划制——先跑 `scripts/lib/anchor_plan.py` 出抽样计划，再跑 `scripts/lib/time_spotcheck.py --chain <链> --final-block <冻结块>` 对独立第二源逐锚点核对，产绑定 target、计划链与逐笔调用 transcript 的 `time-spotcheck/v3`；纯随机锚点容易漏高风险位置。Solana 走 `anchor_sampler.py --as-of-slot <冻结slot> --receipt <回执>`，任一失败日 exit 2。第二源分层选型与全史重拉例外见 evm-recon §13。注意本查不替代供给闭合。
5. **Solana 精确重放（第五查）**：仅 Solana 必跑 `exact_reconcile`，消费当前 coverage 指针、正式 base 或修复代、owner 快照并产 `solana-reconcile/v4`；wrapper 一律为 `reconciliation-report/v3`。动态 Solana job spec 中，balance／supply_truth／time 三查消费 `{observed_as_of_block}`，第五查的 argv 则禁止该占位符，必须把 `--as-of-slot` 写成账本缓存 `finalized_upper_slot` 的非负整数字面量。supply 活观测的 `--work-dir` 必须使用独立子目录（例如 `data/observe_live`），不得覆盖第五查固定读取的 `data/holders_owners.json`、`data/holders_accounts.json`、`data/holders_snapshot_meta.json`；封账点观测 bundle 必须以正式名称 `data/solana_observation_bundle_frozen.json` 密封留案。大白话：前三查问“链上现在是什么”，第五查问“冻结的这本账在冻结点能否逐 owner 全等”；两者可以是不同 slot，但第五查 receipt 的 chain/token 必须与 wrapper 全等，冻结 slot 不得晚于观测 slot，并由深验继续强制它等于所绑定 cache meta 的 `finalized_upper_slot`。FAIL 先用 `sqd_coverage_probe.py` 归因，再按 α/β 止损线运行 `sqd_gap_repair.py`，禁止逐账户 BFS 补账。EVM 无此第五项且 wrapper 中必须省略。

对不上＝数据有洞＝回去补，不许"差不多就行"。

## A3 分析

**惯犯层盲化（A2–A3 全程）**：开工即 `export CHIP_BLIND_SERIAL=1`——标签查询的 serial-actor（惯犯）命中不进任何主输出、完整详情自动封存案目录 `sealed_serial_hits.jsonl`（label_lookup/analyze_holdings/replay_edges/build_evolution 四出口已接线；设施类标签照常输出）。动机：提前看到"这是 XX 案惯犯"会造成合并判定的先入之见；实体冻结后在 A4 揭盲作定向复核线索。

方法学全部在 `analysis-playbook.md` 路由索引（先定位节再区间读分册）。先完成机械准备：
**地址身份标注**（官方标签→外部证据→行为特征三级兜底，playbook §3）→
**金库与核心实体逐笔归因**（§4）；分段模式直接验收 −1 的同源产物。其后判断主序与
`split-run.md` §3.2 一致，按下列顺序执行：

1. **判例库过闸（实体表冻结前必做）**：按 `casebook/README.md` 的使用纪律，把
   `casebook/cex-custody.md`、`casebook/cex-custody-methods.md`、
   `casebook/entity-clustering.md`、`casebook/entity-clustering-methods.md`
   全册触发现象过一遍，命中的逐条做"必做区分检验"。
2. **聚类合并裁决→临时实体**：多证据边＋中间节点三段式检验（§6）；合并只认专属性证据，
   通用实现/通用服务共用不算（见 casebook E-01）。本步只落临时实体，不得提前冻结。
3. **ET-2 无下限成员完整性扫描**：对每个临时实体做不设持仓下限的成员完整性扫描。
   ET 是判级筛查层，不与 EF-1～EF-3 顶层冻结门禁混称。
4. **EF-3A 全体持仓波次扫描／EF-3B 资金流异常扫描**：名册定稿前分别运行
   `wave_scan.py` 与 `flow_anomaly_scan.py`，产 `wave_scan_report.json`（wave-scan/v5）和
   `flow_anomaly_report.json`（flow-anomaly/v3）。Solana 两件必须带与 exact receipt 全等的
   `edge_source_binding`，EVM 必须省略。分段执行时 EF-3A/B 跑批归 −1。
5. **当前持仓分布初判**：仅在 EF-3A 和 EF-3B 之后运行
   `holder_distribution_scan.py --stage initial`。产物是 `distribution_scan.json` 和
   `charts/distribution_stage1.png`。JSON 进入 READY `handoff/v3`，verify 会重新派生五桶并重算；
   工作图不进 seal，也不进报告。initial 只绑定快照、来源收据、排除派生链、算法和阈值，
   不绑定 handoff manifest。
   **喂它的 owner 快照必须与 A2 四查里 `verify_recon --balances` 吃的是同一个文件**
   （EVM 通常是 `balances_final.json`，Solana 是 scanner 自己产的
   `data/holders_owners.json`）：发布闸 new-analysis 会拿分布快照的 sha256 去对四查
   `balance` 收据的 `inputs.balances`（Solana 对 observation bundle 的
   `holder_outputs.owners`），喂两份不同的文件即便总和相同也会被判"同值换仓"而拒。
   动态 Solana（`exact_reconcile` 早于 wrapper）必须显式指定观察快照，因为
   `holder_distribution_scan.find_snapshot` 默认优先 `data/holders_owners.json`（冻结件），
   而发布闸的分布绑定要求 observation bundle 的观察 owners。完整命令：
   `python3 scripts/report/holder_distribution_scan.py --case-dir . --stage initial --snapshot data/observe_live/holders_owners.json`。
   `supply_truth` 为 PASS/exit 0 且冻结点 `replay_net` 因冻结后链上微量销毁略高于观测时点
   `onchain_total_supply` 时，扫描器只在收据 `diff` 逐 raw 相等且整数复算不超过其
   `tolerance_bps` 时放行并记录 `supply_drift_raw`；分布百分比仍以冻结点 `replay_net`
   为分母，Solana owner 快照对 `onchain` 的精确闭合不变。
6. **EF-3C 候选裁决与实体溯源**：两扫描器全部候选经 `adjudication_validator.py`
   成员级裁决，再对临时实体表跑 `entity_source_trace.py`；新支路回裁决环，EF-3C 归 −2。
7. **EF-1／EF-2 门禁**：临时实体成形后、freeze 前落
   `economic_control_ledger.json` 与 `dormant_warehouse_audit.json`；EF-1 核清最终经济控制，
   EF-2 完成历史静置仓反向扫描。任一未闭合不得 freeze。
8. **实体冻结**：`handoff_manifest.py freeze` 固定校验 EF-3C-P1 严格 verify、P2 裁决名册绑定、
   P3 溯源内容重查、P4 原始边/标签/分母/cutoff/block/manifest/data_map/算法绑定后真实重放；
   存在 `distribution_adjudications.json` 时同时绑定当前分布裁决。
9. **实体身份硬闸（G8）**：从冻结实体表生成 state 输入，再由生产 emitter 生成
   `identity-holder-snapshot/v2`。EVM 五链（eth/base/bsc/arbitrum/robinhood）均可生成
   身份快照 receipt；其中 arbitrum 与 robinhood 仅供探索档与存量数据重放，身份能力不构成正式发布资格。EVM 用
   `identity_snapshot_receipt.py --chain ... --snapshot balances_final.json --source-receipt channels_preflight.json --replay-stats replay_stats.json`，
   Solana 用同工具 `--chain sol --snapshot holders_owners.json --source-receipt holders_snapshot_meta.json`。
   EVM 的 `channels_preflight.json` 必须由当前 `channels_preflight.py` 生成并绑定已验 collector receipt/segment chain 与确切 CSV/Parquet `inputs`，`replay_stats.json` 必须由所选当前 replay 引擎生成并绑定同一 inputs、preflight 与 `balances_final.json`；Solana meta 必须由当前 `scan_token_accounts.py` 生成并绑定 supply receipt、每个 GPA raw/meta 与 account/owner 输出；emitter 和 G8 check 会用 scanner 的同一套 base64→
   owner/amount＋跨 scan pubkey 去重函数离线重解析全部 raw GPA，逐条比对 `holders_accounts.json`/`holders_owners.json`，并重读 supply receipt 的 amount 后闭合总量。emitter 和 G8 check 都重验上述实物链，孤立手写或只抄 producer 哈希一律拒绝。再跑 `entity_identity_gate.py --state ... --snapshot-receipt ... --total-supply-raw ...`，产 `identity_gate_v3`。
   存量没有 `producer/inputs/outputs` 的 EVM preflight/stats 必须重跑对应 replay 引擎（其会重跑 preflight 与完整重放），Solana 旧 meta 必须重跑 `scan_token_accounts.py` 重新扫描，然后再跑 emitter；不得手工补字段或用测试 fixture 迁移。闸覆盖每个实体地址＋≥1% 总供应单址；所有无标签实体成员一律 `BIG_UNLABELED`（Solana off-curve 则 `PDA_UNRESOLVED`）。
   CLI `--check` 与 build_html G8 共用 validator，重验全部来源绑定。
10. **判级（含 ET-1）**：庄级实体识别、标签划分与类型三分类的门槛数值与细则唯一权威源＝
    playbook-entity-cluster-tiering §6a（本处不设数值副本防漂移）。ET-1 对其他大户线逐个过
    标签库/惯犯库/指纹/funder 批量排查，报警才人工深挖；项目方、大庄/小庄、离场庄、
    刷量地址与发射窗协同实体均按该节判级，合并口径含全部疑似关联地址。
    分段执行时报警地址证据采集归 −1（只记观察事实，split-run §1.3），人工深挖定性归 −2（§1.4）。
11. **阵营演变重放**：按已冻结且过 G8/判级的名册，重放已声明范围内各阵营占比演变序列；
    分母＝当期净供应序列，**逐时点 assert Σ阵营＝100%±容差**，改过名册跑反向断言
    （casebook S-03）。不得在 EF-3 候选闭环前先跑本步。
12. **A3 落盘**：生成 `findings.md`、`facts.json`、`analysis-state.json`、`identity_gate.json`；
    完成庄家当前状态评估（§7）与质押/留存修正（§8）。建仓成本仅按需算（§6b 降为工具）；
    CEX 净流×价格作为演变解读工具按需用（防内部调仓伪影，§5）。

**覆盖真空声明（用户 2026-08-01 确认接受）**：

- **当前事实**：系统没有从最终阵营序列反向发现并归因全部未解释大变化的硬闸。
- **仍可能漏检**：标签重分类、分母变化、慢速迁移；收方 20～99 且任一 14 日窗不达双线、少于 20 收方拆分、全史流出低于 2%、一实体轮换多址各低于 2%（entity-file 只抵消内部边、不聚合外发）及多跳二级分发。
- **现有轻量信号**：阵营重放标记单日阵营变动 ≥10pp 的日期，作为峰值逐笔触发日之一，但不承担归因义务。
- **报告义务**：无法归因的骤变和上述覆盖边界必须写入报告局限性，不得把未报警表述为不存在异常。

数据先验结构再分析（榜单唯一性断言、多档抽查），批量脚本先 2 个样本验证编解码再放量、绝不吞异常。**份额阈值一律整数运算**（`TOTAL//100`，浮点比较会把"恰好整数枚"大户判漏——那本身还是橱窗仓指纹，漏它双重损失；来源：meow 案 2026-07-15）。

## A4 对抗复核（必做）

**A4→A5 顺序硬闸（6.7.0，2026-08-01 定）：本阶段全部裁决落定并 `a4_gate.py finalize` 封口前，禁止进入 A5——不画报告图、不写 `报告.md`、不编 HTML。复核对象＝findings.md/结论清单＋落盘数据文件，不是排版后的报告。**（历史核查：16 个时间戳可判定案 12 案图表/报告先于复核落盘，7 案因翻案实际返工，另 5 案结论翻了图没跟着改成错误残留。翻案率极高是本环节的固有属性，提前做 A5＝无用功＋上下文污染。）

执行序（细则与 prompt 骨架的唯一权威源＝playbook-evidence-wording §10＋research-workflows §2，此处只列主干）：

1. **claim 注册表登记**：`python3 scripts/report/a4_gate.py register --case-dir . --claims-file <claims.json>`——把 A3 全部核心结论写成稳定 id 的 claims 清单（与 adversarial-review skill 的 args.claims 及 split-run §3.3 外部异构路输入同构），产 `a4_claims.json`。claim_id 不得含空格；仓库现役 fixtures 也必须遵守。存量案重跑时若遇 `A4 01` 这类含空格 id，须先改两套 registry 及其引用，不能把旧 id 直接送入 runner。initial scan 中每个异常簇必须登记对应 `dist-<cluster_id>` claim；漏登或多登时 finalize 双向对账拒绝。
2. **扰动敏感度前置**（EVM 案，`cluster_sensitivity.py --dir <案目录>`，sensitivity_report.md 作复核输入；FRAGILE/STABLE 字样只进复核材料禁进报告正文）。
3. **惯犯揭盲**（实体冻结后 `label_lookup.py --unseal` 取封存命中，与实体划分互证/互斥）。
4. 本地反例自查脚本前置。
5. **N 路怀疑者 agent**＋1 完整性批评角色查 findings/结论清单缺口（必查全史极值清单）＋1 路**外部异构怀疑者**（codex/GPT 单进程横扫全部结论）——重算义务、备择解释与分组细则按 §10＋research-workflows §二执行，不在此复述。所有落盘件必须使用 `adversarial-review-artifact/v2` 绑定当前 `a4_claims.json` sha；claim-review 的 claim_id 并集全覆盖，且每条 evidence 至少 10 个实义白名单字符。白名单覆盖 ASCII 可打印、拉丁补充与扩展、通用标点、CJK、假名、韩文音节和全角段；不在覆盖面的语种（如俄文、阿拉伯文）与纯 emoji 文本会被拒。外语原文证据应附一行中文说明，或保留 URL/数字等覆盖面内字符；中英文工作流不受影响。每条 findings、non_covered 与 REFUTED verdict 必须以机械定位符对应唯一 blocker，少记、多记或未处置均阻断。每路成功 execution receipt 同时追加到案根 `adversarial_review_ledger.jsonl`（`review-ledger/v1` 哈希链）；finalize 要求 ledger 当前有效 receipt SHA 集与传入清单精确相等，并把 `entries/active/tip_sha` 写入 `adversarial-review/v4.review_ledger`。之后只可由 runner `finalize` 原子产出 `adversarial-review/v4`。

   **机器化边界**：机器已强制两类角色在场（≥1 claim 怀疑者＋≥1 完整性批评）、claim_id 并集精确覆盖注册表、entrypoint 内容去重、execution ledger 哈希链精确对账、每条 evidence ≥10 实义白名单字符、findings/non_covered/REFUTED 与 blocker 双向联动。机器未强制（依执行纪律与独立盲审落实）：怀疑者路数 N、每条结论的分档路数、外部路是否真为异构模型、外部异构路成功与否（该路失败不阻塞交付，见本册既有条款）。机器闸 PASS 不等于 N 路已落实——路数与异构性的核验责任在执行纪律与盲审，不在发布闸。
6. 判定三档 CONFIRMED/WEAKENED/REFUTED（**必须实际核查，"理论上可能"不算推翻**）→ 修订顺序先修数据管线再修文案 → 修正记录印进报告附录。
7. **封口收尾**：A3 已先落 `findings.md`、`facts.json`、`analysis-state.json`、`identity_gate.json`。运行 `a4_gate.py finalize ... --workflow-type new-analysis|independent-audit --seal-files findings.md,analysis-state.json,facts.json,identity_gate.json`，产 `a4-seal/v4`。新分析会重验当前分布 claim source，并要求 `dist-*` claims 与异常簇严格相等。每次重封都追加 revision 和 previous seal 哈希。净室复核继续机器对账两套 claim registry，但 v1 分布闸不挂 analysis-audit。路径经 containment 校验，`charts/final/` 为空且 exit 0 才准进入终判环。

## A4.5 当前持仓分布终判环

A4 finalize 后，用同一 cutoff 快照运行 `holder_distribution_scan.py --stage final --round N`。final 绑定 READY handoff manifest、身份快照收据、当前 A4 seal、当前 entity freeze revision、三账、initial scan 和上一轮 final scan。每轮 JSON 和工作图写入 `dist_rounds/round_N/`，不得写入 `charts/final/`。

如果 final 出现当前 A4 seal 未覆盖的新异常簇，立即回流 A4 登记和复核。已经覆盖的异常簇运行 `distribution_explanation_check.py`。位置、成员、数量、证据和传播五项全部通过才记 `EXPLAINED`。未通过时，默认逐成员生成 `distribution_adjudications.json`；只有书面排除成员路径后才能使用 `pattern_resolutions.json`。两条路径的结论都必须回流 A4 重封，再开始新一轮 final。

`distribution_rounds.json` 按轮追加并绑定上一条记录哈希。两轮仍未终态时让用户选择第三轮或标准 waiver。只有 `NORMAL`、完整 `LOW_SAMPLE`、`EXPLAINED` 或带完整收据的 `WAIVED` 能成为终态。终态才物化 `charts/final/holder_distribution_current.png`。删除台账后从非首轮继续、终态后追加或同时存在多个 terminal 都会被拒绝。

## A5 报告

分段执行时本阶段的装配执行归 −3（split-run §3b）；−2 收口于报告正文＋装配工单。

**进入本阶段的前置＝`a4_seal.json` 已由 A4 第 7 步产出，分布轮次已到唯一终态，终版分布图已物化。** 报告本体先写 `报告.md`＋`charts/final/*.png`，再运行 `a5_report_seal.py --case-dir . --report 报告.md --a4-seal a4_seal.json --out a5_report_seal.json`，产 `a5-report-seal/v3`。A5 seal 会绑定 rounds 台账、terminal final scan、解释或 waiver 收据和唯一分布图。build_html 的 G11 会重新计算这些绑定。**报告图一律输出到 `charts/final/`**。复核过程草稿图放 charts/ 根或 `dist_rounds/`，不进报告。**三张标准图必配**（阵营占比演变/庄级实体 vs 价格/价格与关键事件），直接调 `scripts/report/standard_charts.py` 三个函数。持仓分布终版图另放第二章，不作为第二张分布图重复绘制。**每个当前持仓 ≥20% 总供应或 ≥20% 流通的大庄/项目方必配一张全周期流转路径图**。

出图纪律：`figures_from_facts.py fig1` 与 `standard_charts.plot_camp_evolution` 共用 `select_fig1_series()` 机器闸。阵营名必须逐字取自 `standard_charts.py` 的 `CAMP_ORDER`（唯一权威；现行 14 键：项目方、大庄、小庄、离场庄、刷量地址、CEX资金通道、CEX托管、疑似CEX托管、流动性池、其他大户、历史大户、散户、桥锁仓、锁仓/销毁；"狙击集团"与 EVM legacy `销毁`等仅旧数据重绘 legacy）。白名单外键 exit 2 硬拒；豁免集按 state 绑定的 producer `series_format` 由 `stack_exempt_for` 派生：`sol-rows` 豁免 `burn_cum_pct` 与「锁仓/销毁」（真烧毁轨，净供应分母外，图一按净供应标注、不堆叠仅在报告披露）；`evm-dict` 仅豁免 `burn_cum_pct`（其「锁仓/销毁」仍是在账堆叠桶）；无 `series_format` 的历史重绘保持旧规则，豁免原因记 `non_stacked_metric`；出图后必须落 `fig1_legend_receipt.json`，绑定实绘集合、豁免键、overlay 组成及输入/输出哈希，不再以人工目检替代闸口。

结构与措辞纪律见 `report-template.md`。正式报告只有两个入口：全新分析用 `build_html.py --mode analysis-new ... --a5-seal a5_report_seal.json`，净室复核用 `--mode analysis-audit ...`；二者都会核对 seal.workflow_type，并分别强制 `audit_release_gate --profile new-analysis|independent-audit`。**new-analysis 发布闸必须带 `--report <最终 Markdown>`**——A5 seal 自批 D 消化轮 1 起在发布闸内重验（分布终态链与翻转披露都要对报告实物核），缺 `--report` 时 A5 seal 在场即 fail-closed 拒。不存在 generic analysis 或 skip gate。历史重编译必须显式用 `--mode legacy-recompile --degrade-reason "<理由>"`，产物带可见非正式水印。PDF 仅用户点名。

**附录四件套**（验证步骤/标签↔地址对照/复核修正记录/来源）——附录 B 地址对照任何情况下不可省（正文零地址的可验证性支点）。**监控包默认不做**：观察哨/两档监控建议/appendix.json 在用户确认买入后按 monitoring-package.md「买入后监控包」节补生成（新会话可执行，材料全在落盘产物），报告末尾带固定句"如决定买入，回复一声即可补生成监控包"。**默认交付另落一份 `analysis-state.json`**（appendix 的机器子集：token/whale_groups/vault_addresses/addresses 骨架＋camp_share_series，无监控文案；schema 见 report-template「默认交付的机器状态文件」节）。交付前 checklist 见 report-template.md 末节。

## A6 复盘与迭代（仅用户明确要求时执行，不自动触发）

**默认交付 A5 报告即收工，不进入本阶段**——结论未经用户复核就自动沉淀教训，会把可能错误的经验固化进 skill（2026-07-31 用户定）。会话中发现的候选教训随手记案目录 `retro_notes.md`（只动案目录，不动 skill 文件）。用户复核确认结论没问题、明确下令复盘后，按 `retrospective.md` 执行：五类复盘清单 → AskUserQuestion 确认 → **教训分流决策树**定归宿（gate 代码/casebook/pipeline/workflow/SKILL.md 最后手段）→ 写入对应文件＋CHANGELOG 次版本＋1 → 跑 `scripts/tests/run_all.py` 全 PASS → git commit。质量 4 指标＋成本 3 指标、candidate 分级、逢 0/5 整编——细则全在 retrospective.md。
