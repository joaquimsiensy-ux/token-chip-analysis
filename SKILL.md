---
name: token-chip-analysis
description: 对任意链上代币（BSC/ETH 等 EVM、Solana、Hyperliquid、Filecoin 及新链）做机构级庄家链上行为分析——全量链上数据采集与重放、庄级实体识别与 P0/P1 标签分级（项目方/大庄/小庄/离场庄/狙击集团/刷量地址）、各阵营持仓占比演变、P0 实体全周期流转路径图、项目方背景调查、对抗复核、自包含 HTML 报告（含机器可读 JSON 附录与监控建议供投后监控）。当用户问"某代币的筹码分析/筹码结构/庄家行为分析"、"有几个庄/庄家什么类型"、"庄家/项目方/做市商在吸筹还是砸盘"、"有没有关联地址/老鼠仓/单一实体控盘"、"庄家是不是跑了/弃盘了"、"这个币该不该买/该不该卖/解锁抛压大不大"、"帮我看看某代币的链上持仓/大户动向"，或提到 holder analysis、鲸鱼追踪、代币尽调时使用。与 gmgn-token 的区别：gmgn-token 是快速查询单项数据；本 skill 是数小时的深度分析工程（全量数据+交叉验证+HTML 交付）。只查价格/K线/热榜/新币列表不要用本 skill。
---

# 代币筹码分析（Token Chip Analysis）

对一个代币的项目方/庄家/做市商回答四个固定命题（v2.0 四问框架，2026-07-14 取代五问）：**①有几个庄？（按 P0/P1 标签体系分级：项目方 / 大庄 / 小庄 / 离场庄 / 狙击集团 / 刷量地址，见 playbook §6a）②每个庄什么类型（单地址明牌/多地址互转·gas同源/伪装分散·指纹一致）？③各阵营全历史持仓占比如何演变（占总供应量，锁仓/销毁单列；建仓后动没动、拉升期有没有出货）？④项目方背景调查（创始人/项目历史含黑历史、社媒运营、大V关注、互动与热度、水军嫌疑；无项目方看 dev）？** 交付一份每条结论可独立验证的**自包含 HTML 报告**（图 1/图 2 前置于 TL;DR 顶部 + 每个 P0 实体一张全周期流转路径图 + 末尾机器可读 JSON 附录与两档监控建议供后续监控）。建仓成本不再是固定命题（§6b 降为按需工具）。

**四问是下限不是上限（开放条款）**：链上任何不属于四问的显著结构性异常——暴跌/暴涨归因、假量对倒矩阵、流动性池异动、治理/权限异动、跨链桥异常等——必须单列章节报告，并在 TL;DR 增设"本次特有发现"条目（确无发现时明写"无"，这也是结论）。禁止因"框架未覆盖"而略去；报告骨架是最小集，允许按标的插入特有章节（见 report-template.md）。

方法论来自多次独立实战的滚动综合（IO/OPN/FIL/SIREN/HYPE 五次平权奠基 + bibi 定型五问与交付格式；此后每次分析经阶段 6 复盘持续迭代，已覆盖 Solana/BSC/Filecoin/Hyperliquid/Robinhood Chain 等链生态，累计来源见 CHANGELOG）。核心信条：**不对账的分析是猜测，未经反驳的结论是自嗨。**

## 铁律（任何阶段不可越过）

1. **结论独立性**：本 skill 只沉淀工具性知识。可复用白名单=数据源端点与限速实测、脚本与参数、坑与对策、workflow 模板、措辞纪律、基础设施地址标签（用前抽查核验）。禁止黑名单=任何历史分析对具体代币的结论/数字/判定，以及"上次 XX 也是这样"式类比推理。报告红线：除标的及其生态 gas 币外不得出现其他代币名（用户点名对比除外），交付前对报告做一次外部代币名自查。同一会话已完成另一代币分析时，主动建议用户新开会话。
2. **对账关卡**：阶段 2 三查不过关不允许进入分析（形态见各链 pipeline 文档）。
3. **证据强度纪律**：行内置信度/证据 tag 已全部取消（v2.0，2026-07-14 用户定）；证据强度用自然语言分级用词（链上铁证/高度疑似/疑似/未能确证）融入行文，意图判定（出货 vs 做市备货）链上不可区分时并列写。呈现规范见 report-template.md「证据强度呈现」节。
4. **对抗复核必做**：历次实战中凡执行复核，每次都实质改写了结论（修正 6/10、推翻 2/5、删除整条指标、翻出漏检集群各有发生）——这是投入产出比最高的环节，不可跳过。
5. **免费数据源优先**；API key 从 `~/.claude/api-keys.md` 登记文件直接取用（全局自动加载；缺了才向用户索取或走 auto-register-api），运行时只写工作目录 config.json，永不写死进 skill 目录。
6. **成本纪律**（见下节）：成本目标永远让位于准确性——为省 token 砍复核路数/数据源属于违反铁律。

## 工作流总览

```
阶段0 标的画像与链路由（~10分钟）
  → 计划落盘 + 用户决策点前置（口径/注册/key 用 AskUserQuestion 给选项）
阶段1 并行采集：全量链上数据(后台) + 标签 + 价格 + 背景调研 workflow
阶段2 对账关卡（硬性，不过不进分析）
阶段3 分析：地址标注 / 金库归因 / 庄级实体识别与 P0/P1 标签分级 / 演变重放 / 项目方背景调查
阶段4 对抗复核（必做）
阶段5 HTML 报告（三张标准图 + JSON 附录）+ 质检
阶段6 复盘沉淀（固定最后一步，见 references/retrospective.md）
```

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

## 阶段 1：并行采集（一次性全部启动）

四路并行：①**全量链上数据**（最耗时，最先启动，后台跑；采集脚本标配=限速可调/退避重试/断点续传/失败段补扫/冒烟小样本先行）②地址标签与安全面（GMGN、浏览器标签页）③价格（CoinGecko / binance.vision）④**背景调研 workflow**（3-5 路并行 agent，模板见 `references/research-workflows.md`；下一次大解锁的时间和量是最重要的单一情报）。

纪律：优先跑 `scripts/` 固化脚本，禁止现场重写已有能力的脚本；不满足需求先改参数再改脚本，改动记入阶段 6。长任务运维：最长任务最先启动、等待期填满下游脚本编写、零进展要告警、预估偏差超 2 倍主动汇报、废弃通道同步停掉观察哨。

## 阶段 2：对账关卡（硬性）

三查全过才进分析：**余额对账**（重建结果 vs 独立数据源精确对表）、**供给闭合**（总量恒等式 / mint−burn 配平）、**时间抽查**（锚点插值随机对照浏览器）。各链具体形态见对应 pipeline 文档。对不上=数据有洞=回去补，不许"差不多就行"。

## 阶段 3：分析

方法学全部在 `references/analysis-playbook.md`，按序做：地址身份标注（官方标签→外部证据→行为特征三级兜底）→ 金库与核心实体逐笔归因 → 关联聚类（多证据边+服务枢纽剔除）→ **庄级实体识别、P0/P1 标签分级与类型三分类**（§6a：项目方无论份额皆 P0；大庄=当前 ≥20% 总供应或 ≥20% 流通（P0）；小庄=当前 ≥5% 总供应或 ≥10% 流通（P1）；离场庄=峰值 ≥10% 总供应或 ≥15% 流通且当前非庄（P1）；狙击集团单独标签（当前 ≥20%/≥20% 为 P0 否则 P1）；刷量地址单独标签；合并口径含全部疑似关联地址；未达标者不深挖，其他大户与散户只进图 1）→ 全量转账重放出各阵营占比演变序列（阵营划分标准见 §6a）→ 庄家当前状态评估（§7）→ 质押/留存修正；建仓成本仅按需算（§6b 降为工具）；CEX 净流×价格作为演变解读工具按需用（防内部调仓伪影）。项目方背景调查与背景调研并行走（research-workflows §1 路线5）。数据先验结构再分析（榜单唯一性断言、多档抽查），批量脚本先 2 个样本验证编解码再放量、绝不吞异常。

## 阶段 4：对抗复核（必做）

流程：本地反例自查脚本前置 → N 路怀疑者 agent（给数据文件路径让它**自己重算**，不是审阅文字；强制构造备择解释）+ 1 个完整性批评角色查报告缺口 → 判定三档 CONFIRMED/WEAKENED/REFUTED（**必须实际核查，"理论上可能"不算推翻**）→ 修订顺序先修数据管线再修文案，图表措辞同步改 → 修正记录印进报告附录。prompt 骨架见 `references/research-workflows.md` §2。

## 阶段 5：报告

报告本体先写 `报告.md` + `charts/*.png` + `appendix.json`。**三张标准图必配**（阵营占比演变/庄级实体vs价格/价格与关键事件），直接调 `scripts/report/standard_charts.py` 的三个函数——规格与配色已固化，不要每次重新设计；**图 1/图 2 放 TL;DR 顶部（问 1 直答上方）**。**每个 P0 级实体必配一张全周期流转路径图**（`scripts/report/lifecycle_flow.py`，样图 references/examples/lifecycle-flow-sample.png）。结构与措辞纪律见 `references/report-template.md`（四问逐条直答 + 标签体系 + 代币数量带【总量X%】 + 正文零地址 + 观察哨与两档监控建议 + 局限性独立成章 + JSON 附录 schema）。然后 `python3 scripts/report/build_html.py --md 报告.md --out 报告.html --json appendix.json` 出自包含 HTML（PDF 仅当用户点名，用 md2pdf.py）。**appendix.json 须满足监控抽取硬标准**：顶层四键 chip_summary/addresses/unlock_events/source_line、地址完整不缩写、sentinel 只给理应沉睡的地址——字段纪律见 report-template.md「监控抽取块硬性标准」节；build_html 会嵌为 `id="report-extract"`（用户看板只认此 id）并在缺键/缩写地址时 WARN。质检：build_html 退出码 0（缺图/JSON 坏/缺四键会打 WARN 拒绝交付）+ 浏览器目检（图全显/表格无错位/JSON 折叠块可展开）。交付前 checklist 见 report-template.md 末节（四问直答 / 图 1+2 前置且三图齐 / P0 流转图全覆盖 / 数量带【总量X%】/ 正文零地址 / 监控建议两档 / 外部代币名自查 / 附录五件套含 JSON）。

## 阶段 6：复盘与迭代（固定最后一步，不可省略）

按 `references/retrospective.md` 执行：生成五类复盘清单（新数据源/新坑/方法修正/脚本变更/遗留 TODO）→ AskUserQuestion 确认 → 写入对应 references + CHANGELOG 次版本 +1，并记录本次轮次数/Bash 调用数等成本指标。

## 更新模式（/token-update，增量刷新已有研报）

对本 skill 产出过的研报做增量更新：复用旧研报的实体表与本地原始数据，只拉上次 data_cutoff 之后的增量数据，回答"有无新庄（含从其他大户升级者）/ 旧庄增减持 / 观察哨触发情况 / 旧结论修正"，交付**轻量更新简报**而非重做全量报告。全流程与纪律见 `references/update-workflow.md`（U0–U6）；**EVM 标的的采集/重放/对表/分析/序列五环节先用现成通用件 `scripts/update/`**（v2.10 六战抽象收编，README 有步骤映射），别再手写。两条核心纪律：①**一切判定标准与呈现规范以当前 skill 版本为准**（阈值/标签/命名/措辞/schema），旧研报只提供数据资产与对比基线，判级变化须区分"持仓变动 vs 标准迁移"；②新庄扫描在"旧余额快照+增量重放"的最新全量持仓榜上做，禁止只扫增量流水。

## 成本纪律（来自历次实战的消耗解剖）

历史基线：v1.0 前五次分析 266-480 轮 API 调用、缓存读 4200 万~1.24 亿 tokens；v1.1 后 bibi 实测约 66 轮（固化脚本+Workflow 外包生效，降约 75%）。大头=轮次×上下文的乘积；thinking 占输出的 85-89%，每省一轮省一整份。参考预算：轮次 <150、活跃 <1h、缓存读 <4000 万（新链首战可放宽；超了如实报告原因即可，不许为达标偷工减料）。

1. 跑固化脚本替代现场试错（历史上 Bash 试错 56-103 次/会话，多为重新发现已知坑）
2. 独立工具调用同一轮并行发出；进度管理类调用合并
3. 报告初稿 3-5 个大 Write 一次成文；**修正性 Edit 不设限**（修正是质量来源）
4. 机械环节（跑脚本/转 PDF）照做即可；**分析与复核环节思考深度不设限**
5. 大结果一律落盘：脚本 stdout 只回显 ≤20 行摘要；异常检测内置进脚本主动报告
6. 重活外包子代理/Workflow（调研、复核、长清洗），主会话只收结构化结论
7. 阶段 3 结束把关键结论写入 `findings.md`（结论+数字+tx哈希+图表路径）——这是好习惯；仅当上下文逼近 200k 时才建议用户断点续会话
8. 读大文件必带 limit/offset；后台长任务运行期主会话不做零散小交互（缓存 >5min 空窗会整体重写）

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
| 份额阈值过滤用浮点比较漏"恰好整数枚"地址 | `int(v) >= TOTAL*0.01` 的 float 1e25 不精确（实测把恰持 1000 万枚整=1.000000% 的大户判为 False 漏出阵营与监控网）——阈值一律整数运算 `TOTAL//100`；"恰好整数枚"本身还是橱窗仓指纹，漏它双重损失（来源：meow(Robinhood) 分析，2026-07-15） |
| 前台 sleep 被环境禁止 | until 循环 / Monitor / run_in_background；**until 前台等待同样受 Bash 超时上限（最长 10 分钟）约束**——实测 10 分钟被杀（exit 143），预计等待超 10 分钟必须 run_in_background 或 Monitor（外部 CLAW 考古，2026-07） |
| zsh 通配符无匹配报错中断 | `rm -f xx_* 2>/dev/null \|\| true` |

## 深入阅读（references/）

- `data-pipeline-evm.md` — BSC/ETH 通道决策树、死亡名单、HyperSync/Alchemy/扫块用法
- `data-pipeline-solana.md` — 全量扫描与托管判别（IO 实录核验版：双 RPC 互补矩阵、死亡名单、签名投毒坑）
- `data-pipeline-hyperliquid.md` — 官方 API/Hypurrscan 端点与口径坑
- `data-pipeline-filecoin.md` — Filfox 管道、创世 ID 段标签、multisig 直读
- `analysis-playbook.md` — 链无关方法学（对账/标注/归因/聚类/标签体系与类型三分类 §6a/建仓成本按需工具 §6b/状态评估/复核/措辞）
- `research-workflows.md` — 调研 fan-out（含项目方背景调查标配路线）与对抗复核的 prompt 模板、任务编排纪律
- `report-template.md` — 四问报告结构与 P0/P1 标签体系、三张标准图+全周期流转路径图规范、JSON 附录 schema 与监控抽取硬标准（report-extract 四键）、监控建议两档、措辞对照表、HTML 排版约定
- `update-workflow.md` — /token-update 增量更新六阶段（旧研报资产盘点与兜底、增量起点与重叠窗去重、新庄扫描口径、滚动 JSON、何时该回全量）
- `address-book.md` — 跨分析累积的基础设施地址标签库（手工实战核验层）
- `labels/README.md` — 批量地址标签库（七链 ~46.9 万条 CSV + labels_resolver.py 共享内核 + label_lookup.py 查询器，v4 2026-07-17）：**聚类前把全部候选地址先过一遍**（SERIAL/RISK/RISK-CANDIDATE/RISK-UNKNOWN/EXCLUDE/IDENTITY/PRIVACY 七段输出，`--json` 出 JSONL）；EVM cluster.py / analyze_holdings.py、SOL replay_edges.py / build_evolution.py、HL main_metrics.py 已内置 resolver 自动兜底（`--no-labels` 关闭，缺表显式报 degraded_mode）；决策三维（merge_policy/balance_policy/风险四档白名单）、惯犯 serial-actor 层、Robinhood codehash 指纹（fingerprint_check.py）、实战 miss 队列、增量入库 add_labels.py——用法与纪律见该 README
- `environment.md` — 本机环境坑速查
- `retrospective.md` — 阶段 6 复盘迭代操作手册
