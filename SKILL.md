---
name: token-chip-analysis
description: 对任意链上代币（EVM/Solana/Hyperliquid/Filecoin 及新链）做机构级庄家链上行为分析与既有报告独立复核——全量数据采集重放、庄级实体识别与 P0/P1 标签分级（项目方/大庄/小庄/离场庄/狙击集团/刷量地址）、各阵营持仓演变、P0 流转路径图、项目方背景调查、V3/V4 流动性与庄家 LP 手续费归因、对抗复核、自包含 HTML 报告（用户确认买入后可补生成观察哨与监控 JSON 附录）。当用户问"某代币的筹码分析/筹码结构/庄家行为分析"、"复核/审计已有筹码报告或Fable报告"、"有几个庄/庄家什么类型"、"庄家/项目方/做市商在吸筹还是砸盘"、"有没有关联地址/老鼠仓/单一实体控盘"、"庄家是不是跑了/弃盘了"、"该不该买/该不该卖/解锁抛压大不大"、"看看某代币的链上持仓/大户动向"、"庄家做 LP 赚了多少/V3 还是 V4/LP 手续费怎么计算"，或提到 holder analysis、鲸鱼追踪、代币尽调时使用。与 gmgn-token 的区别：gmgn-token 是快速单项查询；本 skill 是数小时深度分析工程。只查价格/K线/热榜/新币列表不要用本 skill。
---

# 代币筹码分析（Token Chip Analysis）

## Codex 运行适配

- Skill 根目录固定为 `${CODEX_HOME:-$HOME/.codex}/skills/token-chip-analysis`；执行脚本时优先从该目录解析相对路径。
- API key 继续以 `~/.claude/api-keys.md` 为唯一登记源，并复用其中指向的 `~/.config/*` 凭据文件。不要复制密钥登记文件，不要把 key 写进 skill 目录、日志、报告或命令行参数；案目录临时配置须设为 `600`。
- 文中旧工具名按 Codex 能力映射：`AskUserQuestion` 表示在确有关键决策点时直接向用户提一个简短问题；`WebSearch` / `WebFetch` 表示使用当前可用的联网检索、浏览器或 fetch 工具；`Agent` / `Workflow` 表示把具体、独立、可并行的任务交给 Codex 子代理；`Monitor` 表示使用当前环境提供的 wait/monitor 机制。不要调用不存在的 Claude 专用工具名。
- Claude 的 `sonnet` / `opus` 是历史模型别名，不是 Codex 模型名。机械任务优先使用当前可用的均衡/低成本代理，P0 实体素材装配使用当前可用的高推理代理；没有模型覆盖能力时继承当前模型，不得臆造别名。
- 本副本自 2026-07-26 起是 Claude Code 版 skill 仓库的 **git worktree**（`codex` 分支，与 `~/.claude/skills/token-chip-analysis` 共用同一个 `.git`）。阶段 6 复盘照常落盘、跑测试并 commit，规则见下方「codex 侧迭代本 skill 的规则」。旧说明"此安装副本默认不含 .git、不要伪造提交"已作废。

### 第 0 步（硬性前置）：跑任何分析前，先同步 Claude Code 侧的迭代

本副本的方法论与引擎修复由 Claude Code 侧持续迭代（每 1–2 天数个版本）。**接到任何筹码分析任务，动手前第一件事**：

```bash
bash "${CODEX_HOME:-$HOME/.codex}/skills/token-chip-analysis/sync-from-cc.sh"
```

按退出码处置：

| 退出码 | 含义 | 怎么做 |
|---|---|---|
| 0 | 已是最新，或同步成功且测试全过 | 正常开工 |
| 1 | 前置检查没过（不在 codex 分支，或有未提交改动）| 按脚本给的提示处理——通常是先提交，再重跑同步 |
| 2 | 合并有冲突 | **停下来先解冲突再开工**——冲突意味着两边对同一处规则有分歧，带着分歧跑几小时的分析，风险远大于花几分钟解冲突。解法规矩见 `SYNC.md` |
| 3 | 合并后测试没过 | 必须停。`git reset --hard HEAD~1` 回退后向用户报告 |

**为什么是硬性**：CC 侧的迭代里有引擎级缺陷修复——例如 3.34.0 修 Solana 采集器两处缺陷、3.35.0 揭露锚点法"三查全过但中段数值全错"的静默失真。用未同步的旧版本跑出来的结论**可能整篇是错的**，而同步通常只要几十秒。

### codex 侧迭代本 skill 的规则

**版本号**：一律用 `c` 前缀，从 **`c1.0.0`** 起（`c1.1.0`、`c1.0.1`…）。三维含义与 CC 侧一致：主=架构级重构 / 次=每次分析复盘迭代 +1 / 修=文档小修。
**禁止再用 `3.x.x`** —— 那是 CC 侧的号轴。分叉期两边各自续号，已造成 3.26.0 / 3.27.0 / 3.28.0 / 3.29.0 / 3.29.1 / 3.30.0 **六个号在两边含义完全不同**（原委见 `CHANGELOG-codex.md` 顶部说明）。

**写哪个 CHANGELOG**：codex 侧的条目**只写 `CHANGELOG-codex.md`**（格式照抄该文件已有条目：版本索引一行 + 详细章节一节）。
**`CHANGELOG.md` 一个字都不要改** —— 它由 CC 侧单向下发，改了下次同步必冲突。

**怎么提交**（改完立刻提交，别攒着——未提交的改动会挡住下次同步）：

```bash
cd "${CODEX_HOME:-$HOME/.codex}/skills/token-chip-analysis"
python3 scripts/tests/run_all.py                    # 全过才提交
git add -A && git commit -m "c1.1.0 一句话说明改了什么"
```

pre-commit 钩子会自动跑 `changelog_lint` / `docs_lint` / `env_check` 三检，不过关会拦下提交。
⚠️ 这两个 lint **都不覆盖 `CHANGELOG-codex.md`**（只扫 `CHANGELOG.md`），该文件的格式、粗体配对、引用断链需自查。

**这些文件不要改**（CC 侧单向下发，改了每次同步都冲突）：`CHANGELOG.md`、`references/labels/**`、`scripts/labels/sources/**`。
codex 侧分析新发现的惯犯地址、未命中标签地址，**回灌到 CC 侧那份**（`~/.claude/skills/token-chip-analysis` 对应位置），下次同步自然下来。

对一个代币的项目方/庄家/做市商回答四个固定命题（v2.0 四问框架，2026-07-14 取代五问）：**①有几个庄？（按 P0/P1 标签体系分级：项目方 / 大庄 / 小庄 / 离场庄 / 狙击集团 / 刷量地址，见 playbook §6a）②每个庄什么类型（单地址明牌/多地址互转·gas同源/伪装分散·指纹一致）？③各阵营全历史持仓占比如何演变（占总供应量，锁仓/销毁单列；建仓后动没动、拉升期有没有出货）？④项目方背景调查（创始人/项目历史含黑历史、社媒运营、大V关注、互动与热度、水军嫌疑；无项目方看 dev）？** 交付一份每条结论可独立验证的**自包含 HTML 报告**（图 1/图 2 前置于 TL;DR 顶部 + 每个 P0 实体一张全周期流转路径图）。建仓成本不再是固定命题（§6b 降为按需工具）。**监控包（观察哨+两档监控建议+JSON 附录）v3.2 起默认不随报告生成——用户看完报告确认买入后按需补生成**（monitoring-package.md「买入后监控包」节；用户实测约 3/4 标的不买入，监控产物只为持仓服务）。

**四问是下限不是上限（开放条款）**：链上任何不属于四问的显著结构性异常——暴跌/暴涨归因、假量对倒矩阵、流动性池异动、治理/权限异动、跨链桥异常等——必须单列章节报告，并在 TL;DR 增设"本次特有发现"条目（确无发现时明写"无"，这也是结论）。禁止因"框架未覆盖"而略去；报告骨架是最小集，允许按标的插入特有章节（见 report-template.md）。

方法论来自多次独立实战的滚动综合（IO/OPN/FIL/SIREN/HYPE 五次平权奠基 + bibi 定型五问与交付格式；此后每次分析经阶段 6 复盘持续迭代，已覆盖 Solana/BSC/Filecoin/Hyperliquid/Robinhood Chain 等链生态，累计来源见 CHANGELOG）。核心信条：**不对账的分析是猜测，未经反驳的结论是自嗨。**

## 铁律（任何阶段不可越过）

1. **结论独立性**：本 skill 只沉淀工具性知识。可复用白名单=数据源端点与限速实测、脚本与参数、坑与对策、workflow 模板、措辞纪律、基础设施地址标签（用前抽查核验）。禁止黑名单=任何历史分析对具体代币的结论/数字/判定，以及"上次 XX 也是这样"式类比推理。报告红线：除标的及其生态 gas 币外不得出现其他代币名（用户点名对比除外），交付前对报告做一次外部代币名自查。同一会话已完成另一代币分析时，主动建议用户新开会话。
2. **对账关卡**：阶段 2 三查不过关不允许进入分析（形态见各链 pipeline 文档）。
3. **证据强度纪律**：行内置信度/证据 tag 已全部取消（v2.0，2026-07-14 用户定）；证据强度用自然语言分级用词（链上铁证/高度疑似/疑似/未能确证）融入行文，意图判定（出货 vs 做市备货）链上不可区分时并列写。呈现规范见 report-template.md「证据强度呈现」节。
4. **对抗复核必做**：历次实战中凡执行复核，每次都实质改写了结论（修正 6/10、推翻 2/5、删除整条指标、翻出漏检集群各有发生）——这是投入产出比最高的环节，不可跳过。
5. **免费数据源优先**；API key 从 `~/.claude/api-keys.md` 登记文件直接取用（全局自动加载；缺了才向用户索取或走 auto-register-api），运行时只写工作目录 config.json，永不写死进 skill 目录。
6. **成本纪律**（见下节）：成本目标永远让位于准确性——为省 token 砍复核路数/数据源属于违反铁律。
7. **交付边界**：**筹码分析输出结构事实与风险判定，买卖裁决由用户做出。** 报告给的是"筹码结构是什么样、风险在哪、触发条件是什么"，不是"买/卖/持"的指令。用户问"该不该买"时，答法是把筹码结构、风险点、需要盯的触发条件讲透，并明确裁决权在用户（实战先例：SPX6900 CEX 黑箱 22.19% 超 20% 红线，由用户裁决是否继续）。这不影响措辞的直接性——风险该说死就说死，不加免责声明式的模糊话。
8. **控盘看最终经济控制，不看币停在哪个地址**：回答“庄控制多少”时，主口径必须是实体的**可证经济控制量**，即钱包自持加上其在 LP、CEX 子账户、桥、质押/锁仓、vault、托管等设施中仍拥有可证明赎回权或受益权的代币等价权益。公共设施不得并入实体成员表，但其可归属份额必须穿透回实体；“设施不是成员”绝不等于“设施内权益不算控盘”。直接钱包余额只能作为位置拆分项，禁止在存在重大可归属设施仓位时把它写成实体控盘结论。完整门槛、证据等级和防双计规则见 `references/economic-control-accounting.md`。
9. **既有报告复核必须净室重建并经过发布硬闸**：原报告是被审对象，不是证据；只把其文字拆成待审命题，禁止把原实体桶、阵营分类、图或衍生 JSON 当作事实输入。必须冻结输入清单、重建全量大额地址分类、分开成员/位置/经济控制三账、登记逐条命题与备择解释，并运行 `scripts/report/audit_release_gate.py`。硬闸不通过时，统一输出“本轮无法裁决”，禁止为了交付完整叙事另造 P0/P1、历史峰值、历史图或“全盘零庄”。完整协议见 `references/independent-audit-protocol.md`。

## 工作流总览

```
阶段0 标的画像与链路由（~10分钟）
  → 计划落盘 + 用户决策点前置（口径/注册/key 用 AskUserQuestion 给选项）
阶段1 并行采集：全量链上数据(后台) + 标签 + 价格 + 背景调研 workflow
阶段2 对账关卡（硬性，不过不进分析）
阶段3 分析：地址标注 / 金库归因 / 初步聚类 / 历史静置仓反向扫描硬闸 / 实体冻结与 P0/P1 标签分级 / 演变重放 / 项目方背景调查
阶段4 对抗复核（必做）
阶段5 HTML 报告（三张标准图 + 附录四件套 + analysis-state.json）+ 质检
  （监控包默认不做，买入后补——v3.2）
阶段6 复盘沉淀（固定最后一步，见 references/retrospective.md）
```

## 既有报告独立复核模式

凡用户要求“复核、审计、重新检查、为什么另一模型推翻旧结论”，在阶段0先切换净室复核模式：

1. 原报告只进入 `claim_registry.json`，不得导入原 `entity_camps`、阵营桶或实体判级作为计算起点；
2. 立即生成 `audit_input_manifest.json`，冻结开工时文件哈希与数据截止时间，后补数据单列；
3. 从原始 Transfer 与独立快照重建当前所有≥0.5% owner、历史峰值/归零/静置候选，重新做地址类型和实体聚类；
4. 落盘 `membership_ledger.json`、`position_ledger.json`、`economic_control_ledger.json`，禁止用算术闭合替代身份和受益权证明；
5. 证据只够推翻旧结论时停在 `unverified`，不得把“运营控制”“流向CEX”“零DEX”自动升级为“庄家”或“必然非庄”；
6. 报告发布前运行 `python3 scripts/report/audit_release_gate.py <案目录> --report <报告.md>`；退出码非0即停止肯定性判级和历史图交付。

逐项 schema、阴性结论门槛、CEX通道纪律和必需资产清单见 `references/independent-audit-protocol.md`。

## 阶段 0：标的画像与链路由

先核定：合约/mint 地址（多源交叉，确认用户持有的到底是哪个）、部署在哪几条链、**总量与流通量多口径分开标注**（链上实查 / 第三方流通 / 名义已解锁——口径混淆是历次实战最高频的结论级错误源）、DEX 真实流动性（<$50k 则定价权在 CEX，分析重心=托管流+金库+充提）。

**多链代币硬关卡（v2.16，不过关不开工）**：“部署在哪几条链”不是登记项，是分流关卡。CoinGecko `coins/{id}` 的 platforms 字段 + GMGN/Dexscreener + 官方文档多源核查；凡部署 ≥2 条链，必须先做**链分布盘点**——各链 RPC 实查该链供给（桥接分支按 mint−burn 口径），产出链分布表（链 / 合约地址 / 该链供给及占全局总供应% / 主 DEX 流动性 / 预估转账量级与采集耗时），连成本预估一起用 AskUserQuestion 让用户选定分析范围（推荐项=供给占比最大的主链；选项：仅主链 / 主链+指定分支 / 全部链）。**禁止拿到地址就按其所在链直接开工**——用户给的地址可能只是小分支链（实战教训：按给定地址所在链做完全量分析，交付后才发现该链仅占全局供给 ~1%、主战场在别的链，整份报告范围性返工；来源：VIRTUAL，2026-07-16）。占全局 <5% 的分支默认不单独立项（用户点名除外）；选多链时各链分别过阶段 2 对账再合并口径。报告 TL;DR 首行必须声明分析范围（覆盖哪几条链、合计占全局总供应 %），规范见 report-template.md。

另核定两件事（v1.3）：①**标的是否带解锁表/vesting**（tokenomist/dropstab 有记录，或链上有锁仓合约/多签托管）——有则问 4 必须包含"未来 6–12 个月解锁日程与量级"小节（要求见 report-template.md）；②**开工版本自查**：读 CHANGELOG 首个版本号并在计划里注明，交付前重读一次——版本号变了说明 skill 被并行会话更新过，向用户提示框架可能已迭代（多会话并行的版本竞态防护）。

| 标的形态 | 读哪份 pipeline / 跑哪套脚本 |
|---|---|
| 0x 地址，ETH 主网 | `references/data-pipeline-evm.md`（Etherscan 免费 key 路线）+ `scripts/evm/` |
| 0x 地址，BSC/Base 等 | 同上（预估转账量 <300 万条走扫块；更大走 HyperSync/Alchemy，先看通道决策树） |
| base58 mint | `references/data-pipeline-solana.md`（2026-07-12 经 IO 原始会话实录核验，双 RPC 按方法路由见其 §0a） |
| HYPE 或 HIP-1 原生代币 | `references/data-pipeline-hyperliquid.md` + `scripts/hyperliquid/` |
| f0/f1 地址（Filecoin） | `references/data-pipeline-filecoin.md` + `scripts/filecoin/` |
| 0x 地址，Robinhood Chain（chainid 4663，Arbitrum Orbit L2） | `references/data-pipeline-robinhood.md` + `scripts/robinhood/` |
| 跨链部署（OFT/CCIP 等） | 先过上方多链硬关卡选定范围 → 各链按其 pipeline 采集 + 跨链 mint/burn 配平；桥接分支链范式见 playbook §6a |
| 全新链 | 新链 SOP：先花 ~30 分钟实测免费数据面（浏览器 API/公共 RPC 能力/限速），形成临时管道笔记；分析完按阶段 6 沉淀为新的 data-pipeline-<chain>.md |

**通道实测探路**：写任何采集脚本前，先用 1-2 分钟小请求逐个实测候选数据源（可用性/返回结构/分页/上限/限速）；拿到任何新 key 先做 1 分钟能力探测再承诺方案；禁止基于文档想象设计方案。

**记账模型准入 gate（3.19 硬闸，链路由定型后、采集开工前必跑）**：fee-on-transfer（转账税）/rebase/Token-2022 转账语义扩展会让"Transfer 流水重建余额"**整体算错，且供给对账闭合也发现不了**（模型错但自洽）。一条命令 1 分钟内出裁决，产物 `accounting_mode.json` 落工作目录：EVM `python3 scripts/evm/accounting_gate.py --token 0x... --chain <链> --out accounting_mode.json`（eth 侧 --rpc 传 Alchemy 检测更强）；Solana `python3 scripts/solana/accounting_gate_sol.py --mint <mint> --out accounting_mode.json`。**exit 0（standard/WARN 级如可升级代理）=放行**，WARN 逐条抄进报告数据底座节（升级切点是观察哨素材）；**exit 2（BLOCK：fee-on-transfer/rebase/token2022-ext/unknown）=硬停**——向用户报模式与证据，要继续必须人工定制记账模型，禁止套标准管线；**exit 1（检测自身失败）=修通道重跑，禁止当 standard 放行**。检测原理与判定表见 accounting_gate.py 头注；验收样本：QUQ(BSC) standard 8/8 精确、HOGE(ETH) 2% 税双路 BLOCK、BERN(Solana) Token-2022 现役 269bps BLOCK。

## 阶段 1：并行采集（一次性全部启动）

四路并行：①**全量链上数据**（最耗时，最先启动，后台跑；采集脚本标配=限速可调/退避重试/断点续传/失败段补扫/冒烟小样本先行）②地址标签与安全面（GMGN、浏览器标签页）③价格（CoinGecko / binance.vision）④**背景调研 workflow**（3-5 路并行 agent，模板见 `references/research-workflows.md`；下一次大解锁的时间和量是最重要的单一情报）。

纪律：优先跑 `scripts/` 固化脚本，禁止现场重写已有能力的脚本；不满足需求先改参数再改脚本，改动记入阶段 6。长任务运维：最长任务最先启动、等待期填满下游脚本编写、零进展要告警、预估偏差超 2 倍主动汇报、废弃通道同步停掉观察哨。

**预采集衔接**（/collect-data，v3.16.0）：开工先查工作目录是否已有预采集产物（EVM=`data/v2/run_*/done.json`，Solana=`data/soltx-*.jsonl.gz`+meta）——有则**直接复用并断点续拉增量到最新**（底层采集器天然幂等），禁止无视既有产物从零重采；产物完整性以其 collect_manifest（工作根目录 `collect_plans/`）与 done.json 为准，`done_with_gaps` 项必须先补齐缺口再进对账。批量候选的采集等待应尽量前移到 /collect-data 夜间队列（`scripts/collect/collect_queue.py`），分析会话只付增量成本。

## 阶段 2：对账关卡（硬性）

三查全过才进分析：**余额对账**（重建结果 vs 独立数据源精确对表）、**供给闭合**（总量恒等式 / mint−burn 配平）、**时间抽查**（3.19 起 EVM 改分层计划制：先跑 `scripts/lib/anchor_plan.py` 出抽样计划——3 时段×3 余额档矩阵点+四类强制覆盖点（全史最大单笔/最大单日净变动/数据源交界块/门槛±10% 边缘地址，QUQ 1.03 亿行实测 5.5 分钟出计划），再照单对照浏览器；纯随机锚点容易全抽在平静期、高风险位置反而漏掉。Solana 案继续走 anchor_sampler.py。注意本查测的是数据完备性与浏览器一致性，不替代供给闭合对 mint/burn 口径的把关）。各链具体形态见对应 pipeline 文档。对不上=数据有洞=回去补，不许"差不多就行"。

## 阶段 3：分析

**惯犯层盲化（3.19，阶段 2-3 全程）**：开工即 `export CHIP_BLIND_SERIAL=1`——标签查询的 serial-actor（惯犯）命中不进任何主输出、完整详情自动封存案目录 `sealed_serial_hits.jsonl`（label_lookup/analyze_holdings/replay_edges/build_evolution 四出口均已接线；设施类标签照常输出，聚类拦截不受影响）。动机：提前看到"这是 XX 案惯犯"会造成合并判定的先入之见；实体冻结后在阶段 4 揭盲作定向复核线索，更贴合结论独立性铁律。

方法学全部在 `references/analysis-playbook.md`，按序做：地址身份标注（官方标签→外部证据→行为特征三级兜底）→ 金库与核心实体逐笔归因 → 关联聚类（多证据边+服务枢纽剔除）→ **庄级实体识别、P0/P1 标签分级与类型三分类**（§6a：项目方无论份额皆 P0；大庄=当前 ≥20% 总供应或 ≥20% 流通（P0）；小庄=当前 ≥5% 总供应或 ≥10% 流通（P1）；离场庄=峰值 ≥10% 总供应或 ≥15% 流通且当前非庄（P1）；狙击集团单独标签；刷量地址单独标签）→ **建立经济控制账本并据此判级**（`economic_control_ledger.json`：钱包自持 + 可证 LP/CEX/桥/质押/锁仓/vault/托管权益，见 `references/economic-control-accounting.md`）→ 全量转账重放出各阵营占比演变序列 → 庄家当前状态评估（§7）→ 质押/留存修正；建仓成本仅按需算（§6b 降为工具）；CEX 净流×价格作为演变解读工具按需用。**强制三账分离：成员表回答“哪些地址由该实体控制”，位置账回答“币在链上哪里”，经济控制账回答“最终受益权属于谁”。公共设施不进永久成员表；但能以 LP 头寸所有权、份额凭证、受益人账本、CEX 子账户证明或闭合赎回链证明的份额，必须在经济控制账继续计入原实体。设施总余额不得整池归庄；归属不清部分单列未决，不得猜。** 项目方背景调查与背景调研并行走（research-workflows §1 路线5）。数据先验结构再分析（榜单唯一性断言、多档抽查），批量脚本先 2 个样本验证编解码再放量、绝不吞异常。

**历史静置仓反向扫描硬闸（3.29.2，任何代币都必须做）**：初步聚类完成后、实体名单冻结和峰值判级之前，必须从全量逐事件重放得到的历史峰值榜、当前已归零/大幅回落地址、长期静置地址及关键退出日前突然激活地址反向追查，寻找不在主链正向 BFS 可达域内的平行库存仓、尾仓和前代仓；同时从核心实体的关键执行/归集网络向上游币源与边界外一圈自签名地址回扫。结果必须落盘为 `dormant_warehouse_audit.json`，逐候选记录币源路径、静置区间、关键日动作、公共设施排除、证据等级及 strict/expanded/excluded 裁决。**没有该文件，或仍有未裁决候选，就不允许冻结实体、不允许发布历史峰值、不允许画图 1/图 2。** 严格实体与强关联扩展体系分别计算“严格下限/扩展上限”；公共路由、CEX 热钱包、协议设施和单纯同日动作不能把地址确权为同一主体。完整候选集、证据门槛与同一交易末快照重放规则见 `references/playbook-entity-cluster-methods.md` 与 `references/playbook-entity-cluster-tiering.md`。

## 阶段 4：对抗复核（必做）

流程：**扰动敏感度前置（3.19，EVM 案）**——`python3 scripts/evm/cluster_sensitivity.py --dir <案目录>` 对每个 P0/P1 重建机械证据图做四类扰动（单源边移除/stale 标签放开/门槛±10%/割边移除），sensitivity_report.md 直接作复核输入：FRAGILE 项逐条问"该边若不成立叙事还立得住吗"，机械孤立成员=完全靠人工证据绑定的复核最优先对象（**只进复核材料，禁止把 STABLE/FRAGILE 字样带进报告正文**——行内置信度已取消；机械证据≠全部证据，分裂≠结论错误）→ **惯犯揭盲（3.19）**——实体冻结后 `label_lookup.py --unseal` 取封存命中，逐条与实体划分互证/互斥 → 本地反例自查脚本前置 → N 路怀疑者 agent（给数据文件路径让它**自己重算**，不是审阅文字；强制构造备择解释）+ 1 个完整性批评角色查报告缺口；完整性角色必须独立检查 `dormant_warehouse_audit.json`，从历史峰值榜和关键退出窗重新抽样，专门挑战“是否漏掉静置旁支仓、前代仓或已归零仓” + 1 路**外部异构怀疑者**（codex/GPT-5.6-sol 单进程横扫全部结论，3.40.0 制度化；调用与裁决纪律见 research-workflows §2）→ 判定三档 CONFIRMED/WEAKENED/REFUTED（**必须实际核查，"理论上可能"不算推翻**）→ 修订顺序先修数据管线再修文案，图表措辞同步改 → 修正记录印进报告附录。**复核拥有发布否决权**：运营控制≠受益权、公共设施/CEX误并、候选集不完整、图表不闭合、样本外依赖或未排除合理备择解释，任一命中就写入 `adversarial_review.json.blocking_findings`；未关闭前主模型不得保留 CONFIRMED 结论。prompt 骨架见 `references/research-workflows.md` §2。

## 阶段 5：报告

报告本体先写 `报告.md` + `charts/*.png`。**三张标准图必配**（阵营占比演变/庄级实体vs价格/价格与关键事件），直接调 `scripts/report/standard_charts.py` 的三个函数——规格与配色已固化，不要每次重新设计；**图 1/图 2 放 TL;DR 顶部（问 1 直答上方）**。**每个 P0 级实体必配一张全周期流转路径图**（`scripts/report/lifecycle_flow.py`，样图 references/examples/lifecycle-flow-sample.png）；生产图必须经 `figures_from_facts.py flow --strict-text-numbers`，让 subtitle/卡片/边标签/footnote 的案情数字也走 facts 宏。`economic_control_ledger.json` 是报告必需件：TL;DR 的控盘比例、P0/P1 判级、图 2 与实体表必须从该账本同源生成；图 1保留链上位置账。凡存在设施权益，正文必须给“钱包自持 / 可证设施权益 / 强关联扩展 / 未决”拆分，不能用钱包自持冒充控盘总量。图 2 若存在已闭合的设施归属区间，`whale_series.json` 必填 `temporary_custody_checks`，并由 `figures_from_facts.py check` 拒绝区间内错误归零。历史静置仓反向扫描若产出 expanded 成员，正文、图注与附录必须并列披露严格实体下限和强关联体系上限，不能把 expanded 上限写成单一主体确权。结构与措辞纪律见 `references/report-template.md`（四问逐条直答 + 标签体系 + 代币数量带【总量X%】 + 正文零地址 + 局限性独立成章）。然后 `python3 scripts/report/build_html.py --md 报告.md --out 报告.html` 出自包含 HTML（PDF 仅当用户点名，用 md2pdf.py）。质检：build_html 退出码 0（缺图会打 WARN 拒绝交付）+ 浏览器目检（图全显/表格无错位）+ 每张图放大核对图内实体名/成员数/日期/金额/份额与 facts/state。**独立复核另加总门禁**：`python3 scripts/report/audit_release_gate.py <案目录> --report <报告.md>`，退出码2时禁止交付肯定性判级、完整阴性结论和历史图。**附录四件套**（验证步骤/标签↔地址对照/复核修正记录/来源）——附录 B 地址对照任何情况下不可省（正文零地址的可验证性支点）。**监控包默认不做（v3.2）**：观察哨/两档监控建议/appendix.json 在用户确认买入后按 monitoring-package.md「买入后监控包」节补生成（新会话可执行，材料全在落盘产物；report-extract 四键/sentinel 纪律等格式标准原样不变），报告末尾带固定句"如决定买入，回复一声即可补生成监控包"。**默认交付另落一份 `analysis-state.json`**（appendix 的机器子集：token/whale_groups/vault_addresses/addresses 骨架+camp_share_series，无监控文案——/token-update 的实体表原料，防日后从报告文字反抄地址；schema 见 report-template「默认交付的机器状态文件」节）。交付前 checklist 见 report-template.md 末节。

## 阶段 6：复盘与迭代（固定最后一步，不可省略）

按 `references/retrospective.md` 执行：生成五类复盘清单（新数据源/新坑/方法修正/脚本变更/遗留 TODO）→ AskUserQuestion 确认 → 写入对应 references + CHANGELOG 次版本 +1。v3.0 起同步执行：成本 3 指标 + **质量 4 指标**（初稿结论数/复核判定分布/漏检数/数字错误数）、分析方法类新规则按 **candidate 分级**入库、逢 0/5 版本做**整编**（减法）、写入后跑 `scripts/tests/` 守护三件套 + git commit——细则全在 retrospective.md。

## 断点恢复（会话中断/上下文爆掉后续跑，3.19 固化）

主分析会话断在任何阶段（VIRTUAL 案断在交付瞬间由收尾会话救回的先例），新会话按固定序恢复，不临场发挥：
1. **盘点断点资产**：案目录 `findings.md`（阶段交接包：结论+数字+tx哈希+口径+已排除假设）→ `analysis-state.json` / `facts.json`（实体表与事实源，有 entity_id 可直接续）→ `data/` 采集产物（done.json/collect_manifest 判完整性）→ `charts/` 与报告残稿；
2. **判定断点位置**：对照工作流总览六阶段，findings.md 末段+最新产物 mtime 定位断在哪个阶段边界内；
3. **数据不重采**：采集产物幂等续拉增量即可（阶段 1 预采集衔接同款纪律）；对账三查若断前已过、数据未增量则不重跑，增量后必重跑；
4. **结论不重derive**：findings.md 里已有的判定直接继承（含"已排除假设"——防止新会话把排除过的假设重新走一遍）；只补断点之后的活；
5. 恢复后第一件事重读 CHANGELOG 首行版本号（开工版本自查同款——断点期间 skill 可能被并行会话迭代）。

## 更新模式（/token-update，增量刷新已有研报）

对本 skill 产出过的研报做增量更新：复用旧研报的实体表与本地原始数据，只拉上次 data_cutoff 之后的增量数据，回答"有无新庄（含从其他大户升级者）/ 旧庄增减持 / 观察哨触发情况 / 旧结论修正"，交付**轻量更新简报**而非重做全量报告。全流程与纪律见 `references/update-workflow.md`（U0–U6）；**EVM 标的的采集/重放/对表/分析/序列五环节先用现成通用件 `scripts/update/`**（v2.10 六战抽象收编，README 有步骤映射），别再手写。两条核心纪律：①**一切判定标准与呈现规范以当前 skill 版本为准**（阈值/标签/命名/措辞/schema），旧研报只提供数据资产与对比基线，判级变化须区分"持仓变动 vs 标准迁移"；②新庄扫描在"旧余额快照+增量重放"的最新全量持仓榜上做，禁止只扫增量流水。

## 简化筛查模式（/token-easy-analysis，批量候选找高控盘标的）

对新标的做**筛查级**筹码分析（v3.12 新增，场景=币安 Alpha/现货初筛候选批量过一遍找类庄家盘）：分析引擎与完整版同强度——全量采集、对账三查、深度关联全套（金库归因/gas 溯源/行为指纹/女巫深挖/P0P1 判级）、对抗复核路数**一分不减**；砍掉的只有背景调研（问 4 整路）与完整报告，交付缩为**两件套单页 HTML**（图 1 含价格右轴 + 按实体结构细分的阵营快照表 + 3–5 行判定块）+ analysis-state.json。判定块只给"是否值得跑完整版"的参考意见，**绝不自动升级**——用户人工决策后新会话跑 /token-analyze 同目录衔接（数据/聚类/判级直接继承，只补背调+完整报告+扩面复核）。全流程见 `references/easy-workflow.md`（E0–E7）。一币一会话铁律不变，跨币汇总不进分析会话。

## 成本纪律（v3.1 三刀版，2026-07-18 全量账单解剖后重订）

**实证结论（65 会话账单拆解，2026-07-18）**：63% 的钱是缓存读——每轮工具调用都要重读全部会话历史；输出只占 18%（HTML 由脚本拼装几乎免费）。恒等式：**成本 ≈ 轮次 × 平均上下文 × 单价**，三个因子三把刀（历史基线数字在 CHANGELOG v3.1.0 条目可考古）。参考预算：轮次 <150、缓存读 <4000 万、**上下文峰值 <30 万**（新链首战可放宽；超了如实报告原因即可，不许为达标偷工减料）。

**刀 1——机械活外包子代理（卸上下文；两档模型制，3.39.2 勘误版）**：
1. 机械阶段一律派 Codex 子代理执行。**模型两档制**：**机械型 → 当前可用的高推理执行代理**（Claude 文档里的 `opus+high` 在 Codex 中按「Codex 运行适配」映射，禁止臆造历史模型别名，也不以换便宜模型为理由）；**判断型 → 保持主模型，model/effort 都不传并继承主会话**。**外包的收益是子代理不背主线几十万上下文**。**外包清单·机械档**：标准脚本跑批与重试循环（采集/余额扫描/CSV 加工）、对账三查的执行侧、标签库批量 lookup、图表脚本执行、数据完整性验证、逐地址溯源 fan-out（按 schema 批量抓地址页）、**P0 实体素材装配**（每 P0 一路并行，模板见 research-workflows.md §二b；完整版与 easy 版同办）。**外包清单·判断档（继承主模型）**：背景调研 fan-out（综合评估）、对抗复核的怀疑者与完整性批评（复核另有 1 路**外部异构怀疑者走 codex/GPT-5.6-sol**，见 research-workflows §2）。**禁止外包**：聚类判定、实体定性、对抗复核裁决（汇总仲裁）、报告撰写——一切需要"判断"的环节留在主线亲做（质量底线，铁律 6）。
2. 外包 prompt 四要素：目标 + 脚本路径与参数 + 期望产物落盘路径 + 回报格式（≤30 行摘要：行数/区间/异常计数/文件路径，禁止贴原始数据）。prompt 必须自包含（链名/合约地址/输出目录写死），子代理看不到主线对话。

**刀 2——控上下文（缓存读占成本 63%）**：
3. 大结果一律落盘：脚本 stdout 只回显 ≤20 行摘要；调用存量脚本输出不可控时加 `| head -30` 兜底——**仅限跑完才输出的一次性命令；流式/长跑任务禁用管道截断**（head 关闭管道后上游进程收 SIGPIPE 会被提前杀死、还被误当成"只是省显示"），此类输出先落文件再 head 文件；异常检测内置进脚本主动报告
4. 读大文件必带 limit/offset；**playbook 分册/中间稿/旧报告禁止整读**——先看 analysis-playbook.md 路由索引定位节，再区间读对应分册（v3.5 四分册：供给对账/实体聚类/状态异常/复核措辞）；分析开局只全读 SKILL.md + 当链 pipeline，其余文档按阶段按需读
5. 阶段边界写**交接包**：阶段 3 结束把关键结论写入 `findings.md`（结论+数字+tx哈希+图表路径+数据口径+已排除假设）——这是断点资产不只是好习惯；**上下文超 30 万后**，在下个阶段边界主动建议用户 /compact 或新开会话续跑（交接包在盘，断点无损）
6. 复盘（阶段 6）与 /token-update 在轻上下文里做：报告刚交付且上下文已超 30 万时，建议用户新开会话跑复盘（只读 CHANGELOG 头部+复盘清单，成本约 1/5）
7. 后台长任务运行期主会话不做零散小交互（缓存 >5min 空窗会整体重写；2026-07-22 注：会话为 1 小时缓存 TTL 时该前提放宽、本条降为软约束——但账号超量降级 5 分钟 TTL 时恢复硬执行，以当期账单实测为准）

**刀 3——省轮次（既有纪律，继续执行）**：
8. 跑固化脚本替代现场试错（历史 Bash 试错 56-103 次/会话，多为重新发现已知坑）；独立工具调用同一轮并行发出；进度管理类调用合并
9. 报告初稿 3-5 个大 Write 一次成文；**修正性 Edit 不设限**（修正是质量来源）
10. 机械环节（跑脚本/转 PDF）照做即可；**分析与复核环节思考深度不设限**——成本目标永远让位于准确性（铁律 6）

## 踩坑速查（跨链通用；链专属坑在各 pipeline 文档）

| 坑 | 对策 |
|---|---|
| macOS Python urllib 裸连 HTTPS 必报 SSL 错（踩过 4 次） | requests 或 certifi context，或 subprocess+curl；绝不裸 urllib |
| reportlab 中文字体全家坑 | STHeiti Light/Medium subfontIndex=0；表格单元格包 CJK Paragraph；先跑一页字体探针；Hiragino 在 matplotlib 可用但 reportlab 报错，正好相反 |
| PDF 质检假通过 | 双轨：pypdf 抽文本 + qlmanage 渲染目检；纯文本查不出表格裁切 |
| 免费层限流当场翻车/整夜零进展 | 限速常数实测收敛；退避+断点续传标配；卡点超 1-2h 摆路径给用户选，不单通道死等 |
| Etherscan 免费 key 只覆盖 ETH 主网（踩过 2 次） | 非 ETH 主网直接走链专属通道 |
| 口径混淆（名义解锁 vs 流通、快照 vs 质押、总供应 vs CMC 流通） | 先核对字段原始定义；两套口径分开标注来源；快照指标声明含不含质押 |
| CEX 黑箱越界表述 | 充入≠卖出、"链上可观测范围内"限定、净流剔除同 CEX 内部对倒、给单一实体份额上限 |
| 聚类被服务地址污染 | 高出度节点剔除；CEX 热钱包不可作共同来源；比对完整地址防投毒 |
| 长跑预估跳票被用户催问（3 次） | 抽样外推报保守上限；零进展告警；最长任务最先启动 |
| 关键字符串从打印输出复制 | 地址/哈希一律从落盘文件取，截断补全=编造 |
| **EIP-7702 委托 EOA 被 `eth_getCode` 误判为合约**（2026-07-26 IQ(ETH)） | code 以 `0xef0100`+20 字节地址开头＝**委托 EOA 不是合约**（判"庄组是否纯 EOA"、"部署者是合约还是人"时会翻车）；且 MetaMask 的 `EIP7702StatelessDeleGator` 等是**通用钱包实现，多址共同委托同一实现不构成关联证据**（等同"都用 MetaMask"），禁止据此合并实体 |
| **"残留极少/收多少转多少"通道指纹用结果当筛选条件**（2026-07-26 IQ(ETH)） | 若中转集合是按"已清空并转入 CEX"筛出来的，再拿它算残留必然接近 0＝循环论证（实测子集 5,485 枚 vs 全下游真值 520 万枚，**948 倍**）；枚举下游必须用**完整下游集合**，再看残留分布 |
| 份额阈值过滤用浮点比较漏"恰好整数枚"地址 | `int(v) >= TOTAL*0.01` 的 float 1e25 不精确（实测把恰持 1000 万枚整=1.000000% 的大户判为 False 漏出阵营与监控网）——阈值一律整数运算 `TOTAL//100`；"恰好整数枚"本身还是橱窗仓指纹，漏它双重损失（来源：meow(Robinhood) 分析，2026-07-15） |
| 前台 sleep 被环境禁止 | until 循环 / Codex wait/monitor 机制 / 后台任务；**until 前台等待同样受 Bash 超时上限（最长 10 分钟）约束**——实测 10 分钟被杀（exit 143），预计等待超 10 分钟必须转后台或使用 wait/monitor（外部 CLAW 考古，2026-07） |
| zsh 通配符无匹配报错中断 | `rm -f xx_* 2>/dev/null \|\| true` |
| **★图表脚本静默跳过非标准阵营名**（自定义名如"项目方·官方系"→ 图只画出命中标准名的少数阵营，无任何报错） | `standard_charts.plot_camp_evolution` 按 `CAMP_ORDER` 白名单过滤 series 键；阵营名**必须**用标准名（项目方/大庄/小庄/离场庄/狙击集团/刷量地址/CEX托管/流动性池/其他大户/散户/桥锁仓/锁仓销毁）。**出图后必须目检图例条数 == 你传入的阵营数**（GMX 实测传 8 个只画出 2 个） |
| **★DuckDB `read_csv` 的 AUTO_DETECT 把 wei 值推断成 DOUBLE 丢精度**（文本比较全一致、`CAST` 后却有几十万条不等，极易误判为"双源不一致"） | 读 wei 列一律显式 `columns={'value_raw':'VARCHAR',...}`；GMX 实测 83 万行里 51.4 万行假差异，改显式类型后归零 |
| **★校验脚本读到 0 个抽查点仍报 PASS**（假通过；`anchor_plan.json` 的键名是 `matrix_points`/`forced_points`，写成 `matrix`/`forced` 会静默取空） | 任何校验脚本在计数为 0 时必须 `assert` 硬失败（fail-closed），禁止"没有不一致"等价于"通过" |

## 深入阅读（references/）

- `data-pipeline-evm.md` — BSC/Base/Arbitrum 数据管道**路由索引**（节→分册对照表；2026-07-22 拆三分册）
- `data-pipeline-evm-channels.md` — evm 分册1 采集通道（§1 决策树含通道表/§2 死亡名单/§3 通道操作细节/§6 BSC 专属坑表/§7 免注册通道）
- `data-pipeline-evm-sources.md` — evm 分册2 数据面与链专节（§4 辅助数据面速查表/§8 Base 专节含 V4 与 Zora 范式/§9 Arbitrum 专节/§10 质押型标的范式）
- `data-pipeline-evm-recon.md` — evm 分册3 对账与重放（§5 对账 gate 四件套/§11 公共数仓准入与分工/§12 DuckDB 亿级重放缩图引擎）
- `lp-fee-accounting.md` — EVM V3/V4 LP 手续费专项口径：池子产生/仓位应得/当前未结算/历史已结算四分法、V4 逐 Swap×逐 tick 重放、`feeGrowthInside` 快照与可说/不可说边界；凡回答“庄家做 LP 赚了多少”或比较 V3/V4 收入时必读
- `data-pipeline-solana.md` — Solana 数据管线**路由索引**（IO 实录核验版；节→分册对照表；2026-07-22 拆两分册）
- `data-pipeline-solana-scan.md` — solana 分册1 扫描与判别（§0a 双 RPC 互补矩阵/§0b 死亡名单/§1 全量扫描/§2a 托管判别五步法/§3a 签名投毒坑/§4 辅助数据面/§5 观测边界）
- `data-pipeline-solana-capture.md` — solana 分册2 采集与重建（§8 SQD 通道/§9 锚点法/§10 快照对比增量/§11 长币龄混合重建/§12 销户覆盖审计/§13 采集加速工程）
- `data-pipeline-hyperliquid.md` — 官方 API/Hypurrscan 端点与口径坑
- `data-pipeline-filecoin.md` — Filfox 管道、创世 ID 段标签、multisig 直读
- `data-pipeline-robinhood.md` — Blockscout/RPC 双通道（都要浏览器 UA）、gas 溯源、发射台指纹、方法论坑
- `analysis-playbook.md` — 链无关方法学**路由索引**（四问总纲+节→分册对照表；v3.5 拆四分册）
- `economic-control-accounting.md` — 控盘比例主口径：成员表/链上位置账/经济控制账三分离，LP/CEX/桥/质押/vault/托管权益穿透、P0/P1 判级、防双计与报告硬闸；凡回答“庄控制多少”必读
- `independent-audit-protocol.md` — 既有/Fable筹码报告独立复核净室协议：输入冻结、全量地址重标、三账、命题表、CEX边界、历史图门禁、对抗否决权与 `audit_release_gate.py` 必需资产；凡做“复核/审计/重新检查”必读
- `playbook-supply-recon.md` — 分册1 供给与对账（§1 分母口径/§2 对账 gate/§8 cohort 留存质押）
- `playbook-entity-cluster.md` — 分册2 实体识别与聚类**路由索引**（节→分册对照表；2026-07-22 二次拆三分册）
- `playbook-entity-cluster-methods.md` — 实体分册1 标注/归因/聚类（§3 标注三级兜底/§4 逐笔归因/§6 聚类硬规则含半枢纽与代买枢纽裁决）
- `playbook-entity-cluster-tiering.md` — 实体分册2 标签体系与判级（§6a P0/P1 门槛与类型三分类/峰值与分母口径/合并指纹库/场景范式/世代阵营法）
- `playbook-entity-cluster-cost.md` — 实体分册3 成本工具（§6b 配价方法优先级/流量存量双口径/染色分摊/退出深度比/出货美元核算优先级）
- `playbook-state-anomaly.md` — 分册3 状态评估与市场异常（§5 CEX 净流/§7 状态评估/§9 刷量克制/§9a 死币复活盘两亚型）
- `playbook-evidence-wording.md` — 分册4 证据复核与措辞（§10 对抗复核/§11 措辞纪律）
- `research-workflows.md` — 调研 fan-out（含项目方背景调查标配路线）与对抗复核的 prompt 模板、任务编排纪律
- `report-template.md` — 四问报告结构与 P0/P1 标签体系、三张标准图+全周期流转路径图规范、analysis-state.json（默认交付的机器状态文件）、措辞对照表、HTML 排版约定、交付 checklist
- `monitoring-package.md` — 监控包分册（v3.3 拆分）：appendix.json schema 与 report-extract 四键硬标准、sentinel/监控建议两档字段纪律、「买入后监控包」三件产出流程——默认分析不读，买入后/滚动 JSON 时读
- `update-workflow.md` — /token-update 增量更新六阶段（旧研报资产盘点与兜底、增量起点与重叠窗去重、新庄扫描口径、滚动 JSON、何时该回全量）
- `easy-workflow.md` — /token-easy-analysis 简化筛查（E0–E7：引擎全保留砍背调与报告、两件套交付规范、判定块要素、转正式衔接与继承清单）
- `address-book.md` — 跨分析累积的基础设施地址标签库（手工实战核验层）
- `labels/README.md` — 批量地址标签库**使用篇**（七链 ~47.1 万条 CSV + labels_resolver.py 共享内核，v4.2+ 2026-07-18）：**聚类前把全部候选地址先过一遍 label_lookup.py**（七段输出，`--json` 出 JSONL）；EVM/SOL/HL/FIL 主力脚本已内置 resolver 自动兜底（`--no-labels` 关闭，缺表显式报 degraded_mode）；决策三维、惯犯 serial-actor 层（提示不定罪纪律）、codehash 指纹、行为守门员、miss 队列——用法/纪律/盲区全在该 README
- `labels/MAINTENANCE.md` — 标签库**维护篇**（重建/发布流程含 roundtrip+manifest 门禁、curation 层语义、数据源清单、注入清洗纪律、benchmark、扩容路线）——只在维护标签库时读，分析会话不用碰
- `environment.md` — 本机环境坑速查
- `retrospective.md` — 阶段 6 复盘迭代操作手册
