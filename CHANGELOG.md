# CHANGELOG — token-chip-analysis（活跃窗口）

版本规则（v3.0 起两维制，详见 references/retrospective.md「版本号约定」）：
- **skill 版本**：主=架构级重构；次=每次**分析复盘**迭代 +1；修=文档小修
- **labels 数据版本**：标签库扩容/重建记 `labels vX.Y` 前缀条目，不再占用 skill 次版本号
红线：条目只记工具性知识（数据源/坑/方法/脚本），禁止记录任何代币的分析结论。
每条迭代条目附成本指标（轮次数/Bash 调用数/交付用时）+ 质量指标（初稿关键结论数/复核判定分布/漏检实体数/传播级数字错误数，v3.0 起，见 retrospective 步骤 1）。
**写入前必跑 `python3 scripts/tests/changelog_lint.py`**（防撞号/倒排——两者都实际发生过）。
本文件只保留最近 ~10 版（整编时滚动）；更早的完整迭代史在 `CHANGELOG-archive.md`，考古规则来源先 grep 该文件。

已知版本事故存档（保留原貌，不改写历史）：
- **2.21.0 重复 ×2**（2026-07-17 两个并行会话撞号：「标签库 v4.1」与「BEGGAR 复盘」各自 +1 —— git 化前无并发防护的实证；两条均保留原号，引用时注意区分）
- **2.24.0/2.25.0 曾物理倒排**（同日并行会话插入位置错位）——2026-07-18 稳定化时仅调整排列顺序，两条内容一字未动

## 版本索引（活跃窗口，新在上）
- **3.4.0 2026-07-18 VIRTUAL(Base+ETH) 多链全量复盘**：亿级双通道采集工程 5 条（规模基准/二轮高峰坑/再平衡禁忌/丢弃行审计/watchdog 标准件）+方法 5 条（3 候选：做市商身份纪律/组双口径/锁池动态性；2 正式：CEX 冷热伪波动/桥接多链全量版）+脚本收编 2（fetch_hypersync_par/watchdog_dual）
- **3.3.0 2026-07-18 体检修复八项**（自查+codex 交叉复核融合，用户批 1-8 全做）：密钥去硬编码/v3.2 漏改五处收口/三对重复条目消除/导航反向检查、analysis-state.json 默认机器状态文件、对账关卡退出码硬化+离线契约测试（run_all.py 全家桶）、monitoring-package.md 拆册、整编 60KB 线绑定拆分动作
- **3.2.0 2026-07-18 监控包按需化**：观察哨/两档监控建议/appendix.json 默认不随报告生成，用户确认买入后补（新增「买入后监控包」流程）；格式标准原样不动；附录 B 升为不可省支点
- **3.1.0 2026-07-18 成本纪律三刀版**：全量账单解剖(65 会话拆账、63% 缓存读)→机械外包 sonnet 子代理/上下文 30 万线+交接包断点/文档定点读；用户批 A 档全部、否决 B/C 档
- **3.0.0 2026-07-18 稳定化大版本**：git 基线/标签库双真相收敛/复盘机制升级(质量指标+candidate+整编+预测追踪)/playbook 重组/守护三件套/瘦身 287→97MB
- 2.29.0 2026-07-18 jesse(Base) 全量复盘 | 2.28.0 哈基米(BSC) | 2.27.0 Index(Robinhood) | 2.26.0 PING(Base)
- 2.25.0 2026-07-17 标签库 v4.2 round-trip 闭环 | 2.24.0 DUMBMONEY(Robinhood)
- 2.23.0 2026-07-17 Pointless 二次增量 | 2.22.0 TRASH 二次增量 | 2.21.0 标签库 v4.1 ⚠撞号 | 2.21.0 BEGGAR ⚠撞号 | 2.20.0 标签库 v4
- （2.19.0 及更早共 40 条 → CHANGELOG-archive.md）

## [3.4.0] - 2026-07-18 — VIRTUAL(Base+ETH) 多链全量复盘：亿级双通道采集工程+多链全局合并范式

> 单币 1.263 亿条（Base）+76.4 万条（ETH）全量重放的多链分析，采集规模为 skill 历史最大；双通道跨天无人值守+对抗复核 4 路。会话断点接力实录：主会话恰断在"报告 build 成功+质检返回"的瞬间（未发最终总结、未做复盘），收尾会话凭 findings.md+落盘产物+transcript 尾部三件重建全景后补完质检复验/复核数字修正/复盘——交接包断点资产（v3.1 刀 2）首次跨会话实战验证可用。

- **data-pipeline-evm.md §8.1 +5 条**（数据工程，直接正式）：亿级规模基准（1.263 亿条/双通道墙钟 ~30h/HyperSync 高峰段单 key 硬顶 750-820 条/s）、抽样估总量"二轮高峰"坑（先高估一倍再低估一半——生态币活动密度与价格周期脱钩，密度探测必须覆盖最近月份）、双通道再平衡禁忌（plan.json 段边界固化后禁跨通道切分，唯一安全接力=同段 .prog 断点续采）、亿级拼接重放必做丢弃行审计（去重丢行数=重复键数，乱序误杀甄别补放，实测 607+607）、watchdog 守护+Monitor 事件观察哨标准件
- **analysis-playbook.md +5 条**：【候选·单案】CEX 上线事件驱动做市商身份判定纪律（时间强相关≠受托实锤，必查与该 CEX 全部标注地址直接往来，零往来降级"事件驱动做市实体"并列备择）；【候选·单案】非关联组触达庄级门槛的双口径披露；CEX 冷热调仓伪波动剔除（机制两见转正，与 posthold Bitget 热钱包事故同机制）；【候选·单案】锁仓池数字动态性复核（RPC 现值+30 天流速，防漏"迁移进行时"结构信号）；桥接范式多链全量版（全局恒定分母+分链重放合并、桥锁↔桥铸 wei 级闭合、CCIP 背书池所在链必须实查——实测分支背书锁在 Base 侧而非原生链 ETH、未展开分支双处登记）
- **脚本收编 2 个（scripts/evm/，--config 参数化，key 不落 skill 目录）**：fetch_hypersync_par.py（HyperSync 多段并行：plan.json 段计划固化+.prog 断点+指数退避+.aldone 跨通道认领标记）、watchdog_dual.py（双通道守护：第二通道探测自启/死亡重启/段回收兜底/ALL_DONE 退出；通用化自 VIRTUAL 会话产物，py_compile 过）
- **报告层小修（收尾会话）**：附录 C 判定数改如实口径（原始 20 项=10C/6W/4R，合并同类项后净修正 9 条——原稿"9/5/3"易误读为判定分布）；appendix.json review_summary 同步
- **Known Gaps（VIRTUAL 下次 /token-update 验收点）**：Solana 分支 2.65% 未做实体分析；Sablier 流锁受益人未穿透；做市实体A 资金源终极身份（全流水走链上中转仓）；ETH 侧散布 11.7% 仅 top 级识别；官方建池手历史 LP 仓（峰值 4.92%）未入官方系历史曲线（末态结论不受影响）
- 成本：主会话 539 轮次/127 Bash/墙钟 ~44h（含 ~30h 采集挂机，双通道比单通道省 ~12h）+收尾会话轻量接力；质量：初稿 TL;DR 级硬结论 ~15 条，复核 4 路原始 20 判定=10 CONFIRMED/6 WEAKENED/4 REFUTED，复核翻出漏检观察级仓位 1 个（官方建池手 Base LP 峰值 4.92%），传播级数字错误 1 个（金库"9 笔流水"实为 7 笔）

## [3.3.0] - 2026-07-18 — 体检修复八项：一致性收口+硬关卡机器化+监控分册（自查+codex 交叉复核融合，用户批 1-8 全做）

> 触发：v3.2 交付后用户要求全面体检 skill 找优化空间（@CX）。自查+codex 双向复核、每条声明亲手验证后定 13 项清单，用户批 1-8。核心判断（双方一致）：方法本身扎实，真问题是三层失同步——v3.2 按需化没改干净、文档间重复条目开始漂移、文档承诺的"硬关卡"在脚本层不硬。

- **①密钥去硬编码**：probe_codetype.py 内置 dRPC key 明文违反铁律 5（全库扫描仅此 1 处）——改为 ETH_RPC 环境变量必填、缺失报错指路 api-keys.md。key 已随 git 化进历史：仓库纯本机无远程暂不清洗，**分享 skill 目录前必须先处理 git 历史**；轮换 key 受阻于 dRPC 账号未登记（见 api-keys.md 第 3 节⚠）。
- **②v3.2 漏改五处收口**：SKILL.md 工作流总览"JSON 附录"残留、report-template checklist 两个第 13 条撞号、骨架元信息行/JSON 节"必须"措辞未条件化、update-workflow U5 骨架与 checklist 无"无监控包"分支标注、playbook §7 标题与 §11 观察哨机制+retrospective"appendix 即登记处"未跟 v3.2——全部按"监控包 关/开 两分支"统一收口（codex 方案：收口分支而非到处打补丁）。顺带成本纪律条 3 补 `| head` 流式风险限定（SIGPIPE 会提前杀上游进程，流式长任务先落文件再 head）。
- **③三对重复条目消除**：playbook"注资证据分级"+"gas funder 公共性体检"双份（已现措辞分叉——漂移现场证据）、§6a"计数分级+离场庄亚型"双份、update-workflow U3a 巨型段（4585 字符单行）与 playbook §6 跨文档双份——各留一处主本+指针；U3a 独有的"≥1% 候选资金对手方无条件展开"深挖线条款并入 playbook §6 主本后再压缩，零语义丢失。
- **④导航反向检查**：SKILL.md 深入阅读清单补漏列的 data-pipeline-robinhood.md；docs_lint 新增反向漏列检查（references 下存在但 SKILL.md 未列 → FAIL）——正向断链查不出"存在但没列"。
- **★⑤analysis-state.json（默认交付的机器状态文件，codex 提出）**：v3.2 砍 appendix 的连锁缺口——未买入标的做 /token-update 时实体表只能从附录 B 文字反抄地址。新增默认交付物 analysis-state.json=appendix 机器子集（token/whale_groups/vault_addresses/addresses 五字段版/camp_share_series，无一切监控文案），schema 定义在 report-template 新节；verify_balances/analyze_inc 已内置缺 appendix 自动读它；U0 资产表/U5 滚动/checklist 11 条同步。
- **★⑥对账关卡退出码硬化+离线契约测试**：replay_inc 非零地址负余额=exit 1、含 ZERO 快照恒等式不闭合=exit 1（实证两种快照格式并存：GME/BEGGAR 含 ZERO 负项、COMPUTE 正余额型——后者恒等式不适用打 NOTE 降级，防误拦）；verify_balances 归档块口径 MISMATCH=exit 1、latest 口径差异=exit 2 INCONCLUSIVE 不再假 PASS。新增 test_replay_inc.py（四路径 fixture）+ test_build_html.py（WARN 拒交付与 report-extract 四键契约）+ **run_all.py 一键全家桶**（3 lint+2 测试），retrospective 步骤 3 改跑全家桶——"文档说硬"首次变成"退出码硬"。
- **⑦monitoring-package.md 拆册**：JSON schema+买入后监控包节（占 report-template 29%、默认分析用不到）独立成册，report-template 留指针（31.1K→22.8K）；SKILL.md/update-workflow/playbook/build_html 全部引用改指向；SKILL.md 成本纪律砍历史基线数字段（数字在本 CHANGELOG v3.1.0 可考古）。
- **⑧整编 60KB 线绑定动作**：v3.0 整编后 playbook 仍 96KB、触发器永久为真形同虚设——线不动，绑定明确动作：超线整编=四分册主题拆分+路由索引（供给对账/实体聚类/状态异常/证据复核），v3.5 兑现；拆分纪律=先冻结规则清单逐条迁移核对。
- 未做项（用户未批或双方共识不做）：背景调研路线精简（旧案不重开）、"观察哨"双义改名、脚本成熟度元数据、版本号重定义（用户 7-14 规则不翻案）、playbook 立即大拆分（v3.5）、砍复核/换 sonnet 判断环节（B 档否决维持）。
- 守护全家桶 5/5 PASS（docs_lint 20 文档含新册+反向检查）。**验证纪律实录**：codex 两条声明按验证打了折扣——verify_balances"返回 0"是刻意设计（latest 口径天然微差）非 bug，精细化而非推翻；恒等式硬化若按 codex 原方案无条件 FAIL 会误拦 COMPUTE 型快照，实证三个实战产物后才定条件版。

## [3.2.0] - 2026-07-18 — 监控包按需化：观察哨/监控建议/JSON 附录从标配改为买入后生成（用户定）

> 触发：用户复盘"分析了 40 个币，可能不到 10 个买入需要监控"——约 3/4 的监控产物（观察哨清单+两档监控建议+appendix.json）为不买入的标的白做。用户决策：默认报告不带监控包，看完报告确认买入再补生成；**格式标准一律不动**。

- **★交付物两段式**：默认交付=报告 HTML（四问+三图+P0 流转图+附录四件套：验证步骤/标签↔地址对照/复核修正记录/来源），`build_html.py` 不带 `--json`（该参数本就可选，脚本零改动）；报告末尾固定句"如决定买入，回复一声即可补生成监控包"。**附录 B 标签↔完整地址对照升为任何情况不可省**——正文零地址设计的可验证性唯一支点+补生成 JSON 的原料。
- **★新增「买入后监控包」流程（report-template.md 新节）**：触发=用户确认买入/点名监控（可跨会话，材料全在落盘产物：附录 B+data/+第七章状态评估）；产出三件=第七章补写观察哨与两档监控建议、appendix.json（四键/sentinel/monitoring_advice 全按既有 schema）、重跑 build_html --json 出监控版 HTML 覆盖原文件；质检=零 WARN+sentinel 纪律复查+哨与状态评估对齐；新会话执行禁止整读旧报告（成本纪律刀 2）。
- **report-template.md 第七章重构**：状态评估（分析结论本体）保留必做；结论天然检验点正文一句话点出；观察哨清单+两档监控建议标注默认不写；checklist 第 8/11/12 条改默认版+新增第 13 条"买入后监控包交付时追加"检查组。
- **update-workflow.md U0 新增 4c 无监控包兜底**：未买入标的旧报告无 appendix/观察哨不算资产缺失——实体表从附录 B+data/ 重建、U3c 如实写"无观察哨基线"、U5 滚动 JSON 免做；更新时用户表示买入的顺手补包（基线从本次更新起算）。
- **SKILL.md**：frontmatter 与阶段 5 同步（appendix.json 从必做产物中移除、监控包按需引用）。
- 影响与不变项：投后看板衔接不变（买入的币走补包流程后照常喂看板，report-extract 四键/id 约定原样）；/token-update 主流程不变（更新对象基本是已买入币，自带监控包）；预计再省每次分析约 $3-6+对应轮次（观察哨排查与 JSON 编制是逐条人工研判活）。

## [3.1.0] - 2026-07-18 — 成本纪律三刀版：全量账单解剖后的降本机制（用户批 A 档全部、A1 模型定为 sonnet、否决 B/C 档；codex 交叉复核融合）

> 触发：用户 ccusage 统计发现"用了 skill 之后单次分析仍然很贵，和不用 skill 时几乎没区别"。全量拆账（65 会话、逐条 usage 直读+ccusage 内置单价）：**63% 是缓存读**（每轮重读全部会话历史）、19% 缓存写、18% 输出、普通输入≈0；按轮归因执行类轮次占 55%；单次完整分析 $60-160。结论：skill 砍掉了摸索轮次（-75% 有实证）但上下文同步膨胀（实测峰值 40-75 万 tokens，1M 窗口是隐形放大器），成本 ≈ 轮次×平均上下文×单价 的积分没变。codex 定调："真正该优化的是模型反复读取多少东西，以及模型亲自写了多少机器本可生成的字节"。

- **★SKILL.md 成本纪律节重写为三刀结构**（原 8 条全部保留归位）：刀 1 机械活换便宜模型——机械阶段（脚本跑批/对账执行侧/标签 lookup/图表脚本/完整性验证）一律 `model: sonnet` 子代理（单价约主模型 3/10 且不背主线上下文；Workflow 用 opts.model，纯跑批加 effort:'low'），判断环节（聚类/定性/复核裁决/报告撰写）禁止外包；外包 prompt 四要素（目标/脚本与参数/产物路径/≤30 行回报格式）。刀 2 控上下文——playbook/中间稿/旧报告禁止整读（Grep 定位+区间读）、存量脚本输出加 `| head -30` 兜底、**上下文预警线 200k→30 万**（超线在阶段边界建议 /compact 或断点续会话，findings.md 交接包为断点资产）、复盘与更新在轻上下文做（新会话成本约 1/5）。刀 3 省轮次（既有纪律照旧）。参考预算新增"上下文峰值 <30 万"。
- **research-workflows.md 模型选择规则**：机械执行型代理（schema 批量抓取/脚本重试循环/批量余额核查）用 sonnet；判断型代理（调研综合评估/怀疑者复核/完整性批评）保持主模型——B1"复核子代理化"用户已否决，复核维持主线主模型不动。
- **update-workflow.md U6 补引用**：更新会话同执行三刀；更新任务上下文失控多半=违反"U0 只读附录 JSON 与实体表、不整读旧报告正文"。
- **决策存档**：B 档（复核改证据包子代理/复核轮次封顶）、C 档（砍复核/砍覆盖/换弱模型）用户明确否决不做——成本目标让位于准确性（铁律 6）再确认。skill 维护类会话（标签库审计/整编）建议攒批做、不在分析会话 50 万上下文尾部做复盘。
- **量化预期（下次分析验收）**：单次全量分析 $60-100 → $30-50（-40~50%）；分账单验证法=ccusage 看该会话 cacheReadTokens 与 totalCost。此为流程机制类变更，不适用 candidate 分级（数据工程/流程类豁免）。
- 成本：本次为排查+机制写入会话（非分析复盘），拆账脚本 3 个（scratchpad，一次性不入库）、codex 交叉复核 1 路、改动 4 文件（SKILL/research-workflows/update-workflow/CHANGELOG）。

## [3.0.0] - 2026-07-18 — 稳定化大版本：50 版加法之后的第一次系统性减法与校准基建（用户批 A/B/C 全档 + codex 交叉复核共识）

> 触发：用户问"迭代 40+ 次后整体效果如何"。审计结论：成本效率有实证（轮次 266-480→60-95，-75%），但初稿准确率无度量、工程卫生恶化（无版本控制/标签库双真相/文档追加式膨胀）。本版本不加任何分析规则，全部投入是基建与机制。

- **★git 化（A1）**：skill 目录 git init，基线快照原样入库；此后每次复盘一个 commit（retrospective 步骤 3 已挂）。手工 tar.gz 备份时代结束；并行会话版本竞态有了案底可查。
- **★标签库双真相收敛（A2）**：①根因确诊——add_labels（同级覆盖）与 build_labels（同级先到保留）冲突语义不一致，v4.2 期间直改发布库的 12 行精修在全量重建时被泛化行回退（列级 diff 抓出）；②机制修复——SRC_PRIORITY 新增 `curation=-1` 最高层（additions/curation_overrides_*.csv 专用 source），upsert 高优先级源同步覆盖 evidence/verified_at/status（此前只补空）；③12 行精修救回 curation_overrides_20260718.csv；④roundtrip_check.py 进发布流程（发布版 ⊆ 新构建行级门禁，七链 PASS）；⑤benchmark --labels-dir fail-fast（堵住 cwd 错→空表→假 PASS）；⑥发布库 sha256 manifest 落印/验印。发布版与 staging md5 全一致，benchmark 回归 PASS 存档。
- **★复盘机制升级（retrospective v3.0）**：①质量 4 指标（初稿关键结论数/复核判定分布/漏检实体数/传播级数字错误数）与成本 3 指标并列强制——"复核每次都有修正"是初稿缺陷率的反面指标不是胜率，质量指标是"初稿是否在进步"的唯一证据源；②分析方法类新规则 candidate 分级（单案【候选】→两独立案例复现或机制解释才转正；数据工程类豁免）——治事后拟合；③整编模式（版本尾数逢 0/5 或 playbook>60KB 或 docs_lint 漂移 ≥3 处触发，只做减法）——迭代引擎补上减法半边；④预测追踪（观察哨兑现率挂 /token-update U3c，事实归因/行为预测/价格结果三维分开评分，整编时汇总累计兑现率）——分析质量的外部校准。
- **★版本号两维制**：skill 版本（流程+方法）与 labels 数据版本分离，标签库扩容不再占 skill 次版本号；写 CHANGELOG 前必跑 changelog_lint（2.21.0 撞号 ×2 与 2.24/2.25 倒排的历史事故已白名单存档，不改写历史）。
- **★守护三件套（scripts/tests/）**：changelog_lint（版本唯一性+顺序）、docs_lint（引用断链+残缺粗体+SKILL 清单齐全，首跑即抓出 playbook 截断残行与重复条目对）、labels_manifest（发布库指纹落印/验印）；挂进复盘步骤 3/4 与 MAINTENANCE 发布流程。
- **playbook 三区节内重组（B1）**：§6 36 条散点→6 主题组、§6a 25 条→4 组、§7 追加区→3 组；合并 2 处重复条目对、删截断残行、2 条错位条目归位。子代理语义清点（git 旧版逐条对比）：37 关键阈值全在场，抓出 2 条丢失+3 处削弱全部补回。净效果：结构化优先（-4% 字符），检索从线性扫描变主题定位。
- **CHANGELOG 拆分**：活跃窗口 11 条 44KB + CHANGELOG-archive.md 39 条 120KB，头部版本索引一览。
- **labels 文档拆分**：README.md 使用篇 9KB（分析时读）+ MAINTENANCE.md 维护篇 13KB（重建/审计/扩容时读）——分析会话卸掉 2/3 维护内容；serial-actor 纪律明文划界与铁律 1 的张力（惯犯命中=提示线索≠本案定罪，本案独立证据链必备）。
- **SKILL.md**：description 精简 1/3（触发词全保留）；labels 引用漂移修正（v4→v4.2+/47.1 万条）。
- **清理归档（A3，用户照单批准）**：删可重建大文件与缓存垃圾 ~190MB、backup 两项+robinhood 候选池移出至桌面 `skill-archive-20260718/`；工作树 287MB→97MB。sources 大文件按 MAINTENANCE 下载命令随时可重建（dune 两表本地留 .gz）。
- **Known Gaps（v3.0 遗留）**：①留出评测集盲跑（codex C5 建议：冻结 8-12 旧案数据、删案例细节后盲跑对比）——准备成本数十小时，暂缓，若日后要严格验证"规则泛化能力"再启动；②robinhood_verified_contracts.csv 候选池已移出桌面归档，首轮人工审仍待做（P1 余款照旧）；③质量 4 指标与预测追踪从下一次分析/更新开始积累，前 50 版无此数据；④sources/out 已删，下次重建自动再生（roundtrip_check 只在重建时用）。
- 成本：稳定化会话全程约 60 轮、Bash 约 55 次；标签库全量重建 ×3（含修复迭代）+ benchmark ×3；子代理 2 路（codex 交叉复核 + playbook 语义清点 12.7 万 tokens）；A/B/C 三档 14 项全落地。

## [2.29.0] - 2026-07-18 — jesse(Base) 全量分析复盘：Zora CreatorCoin 范式 + 假 wash bot（池子）翻案 + ERC-4626 金库双盲区 + 窗口净额口径原则

- **★Zora CreatorCoin 标的范式（pipeline-evm 新 §8.4a）**：识别（impl 名=CreatorCoin）、50/50 结构（vesting 5 亿锁在**代币合约自身**=锁仓桶单列，5 年纯线性无 cliff、claimVesting→payoutRecipient 可变更）、配对 ZORA 非 ETH、99% 防狙击税仅挡 10 秒（Flashblocks 同块狙击生态照收 20%+）、创作者费以 ZORA 结算不构成本币卖压、退出深度专项（ZORA 计价池 90%+ 集中→账面市值/承接比+双重贬值链）。
- **★"毛流量巨大+净0"指纹先排除池子（playbook §9）**：WETH/本币池吞吐形态与 wash bot 完全同貌，实测 5 个"刷量bot"4 个是池子合约（RPC token0/token1 排除法）；短命池是做量场地证据但操盘者是池中 EOA，识别不出如实写。
- **★ERC-4626 杠杆金库双盲区（playbook §7）**：Deposit+份额未动=保留赎回权的生息仓（非赠与非卖出），但金库币被交易池借出直接卖 DEX——"本人没卖"与"库存成卖压弹药"并列写；最低水位法给流出下限；监控必须加金库份额 token 事件层（只盯本币 Transfer 看不到赎回）。
- **★窗口净额口径原则（playbook §7）**：净额榜=余额变化≠买卖；脉冲归因"事件后24h窗+全窗"双口径（实锤：全窗最大净卖=24h最大净买，卖在崩塌段=止损非派发）；卖方榜逐条实体级检验（移仓剔除）；"借新闻出货"正主看卖出时点价位（公告后135秒闪电清仓的沉睡仓才最像收到风声）。
- **同型协同结构≠同一实体 + 合计数重算义务（playbook §6a）**：狙击生态"买手→卖手"同型是标准作业模式不是合并证据（执行栈指纹互斥可证独立）；"N 组合计 X%"在实体表每次变更后必须重算（18.4%→20.19% 被两路复核同时抓出的教训）。
- **Base 通道补充（pipeline-evm §8.1/8.2）**：HyperSync base 非高峰单通道 213 万条 94 分钟零 429（时段依赖，与 PING 高峰期经验互补）、主采集期间并发探测会 429；分时段密度探测法（发射月密度可为稳态 15 倍）；Blockscout v1 API sort=asc 一次拿最早注资 tx；CoinbaseSmartWallet(4337) txlist 溯源失效改 token 层；Coinbase Bundler=Base App 发射 tx.from（非发行主体，Blockscout is_scam 误标）；7702 的 Blockscout"无名合约"特征。
- **地址入库**：MEXC 15 (Base) 0x4e3ae00e…31b60（address-book；三路复核定性冲突靠 Basescan 官方标签裁决的教学案例——热钱包持币榜形态酷似大户）。
- 本次实战验证（未新增条目）：地址截断补全被数据反查抓获 3 次（自己犯 2 次+消费复核转述拦截 1 次）——"地址一律从落盘文件取"纪律再验证；开工版本自查首次实际派上用场（会话期间 CHANGELOG 被并行会话推进 2.25→2.28，写入前重读避免了重复覆盖 PING 的 Base 条目与 replay 脚本）；5 路对抗复核 1 重大定性纠错+2 传播级数字校正+1 实体表返工——投入产出比最高环节七连验。
- Known Gaps（jesse 案遗留）：①狙击惯犯入标签库 serial-actor 层待办（#2 组 b102/9572+私有合约 0x625c…4150、#4 组 EEe3/8466/b10caf05+新工具 0x1c548dc 同 selector 0x1bfd2ed3——2026-04~07 仍活跃）②数据管道缺 tx.from 字段（transferFrom 模式扫描不可执行，HyperSync transactions 字段补采方案待验）③短命池对倒操盘 EOA 未识别 ④防狙击税负核算未做（hook 事件日志）。
- 成本：全量首战约 5 小时（含 4 路调研+5 路对抗复核 agent），Bash 约 75 次，主上下文一次未断；HyperSync 单通道全量 213 万条 94 分钟。

## [2.28.0] - 2026-07-18 — 哈基米(BSC) 全量分析复盘：HyperSync 限流分段多进程 + blxrbdn 窗口收缩 + 币安Web3路由假实体 + V4 刷量检查 + 换仓检测义务

> 用户 2026-07-18 确认"全部写入"——以下条目已全部落地对应 references/scripts。BSC Alpha 在架币首个 v2.0 框架全量案（436 万条、对账 10/10、四路复核 1 实锤修正+2 WEAKENED）。

- **★HyperSync 免费层 429 收紧（pipeline-evm 通道表+§3.1）**：0.15s 间隔高峰期 429 频发（173 次/时级、吞吐腰斩），0.5s 间隔基本消失；**同 key 2-3 进程按块段分兵并行可行**（互扰有限）——大标的提速正解=分段多进程+断点续拉+事后 (tx,log_index) 去重合并。与 v2.27.0 的"429→RPC getLogs 备选"互补（本案 BSC 公共 RPC 无全史 getLogs 可切，分段自救更通用）。transactions 端点做 BNB 注资溯源：单址全链 ~2.3s（批量×全链会超时，姿势=单址逐查/发射窗小段批量）。
- **★blxrbdn 历史窗口收缩（pipeline-evm §1/§2）**：105M 前块 header not found（二分 100M✗/105M✓ ≈保留 1 个月），"可扫全史"过时——降级为近期段快扫通道（550 万块 7 分钟）；scan_transfers 的 `<chain>_scan_meta.json` 缓存起点坑（改 config 须删）同步记档。
- **★币安 Web3 钱包 DEX Router 串假实体（pipeline-evm §6 坑表）**：`0xb300000b…`（vanity）作"共同首币来源"边把互不相识的币安钱包用户串成 421 址大簇——E3 共源边源地址必须先过标签库；与 LI.FI/对倒 bot 代理同为"度数几十"漏网半枢纽。
- **★Uniswap V4 PoolManager 必入池子清单（pipeline-evm §6 坑表）**：单例合约不在常规 pair 发现流程，漏掉即错过其上 bot 刷量（实测脉冲日占全网笔数 49-88%/毛量 40-76%、池深仅数千美元、与拉升起点精准同步）——量能真实性检查加"V4 毛量占比"维度+四日脉冲定量法。
- **★换仓检测义务（playbook §7）**："完整离场"结论前必对清仓 tx 接收方做两跳内等额沉淀扫描（实测内盘最大买家清仓 7 个月后两跳等额 813.7 万枚续持，初判被复核推翻）——"归零"与"离场"之间隔一次换仓检测。
- **黑箱主导盘"0 庄"量化措辞（playbook §11）**：托管黑箱占比大时结论句必须量化可见范围（"外部可见盘约占 X% 内 0 庄"），单写"链上可证范围内"会让读者高估覆盖面。
- **E2 同块共现参数补强（playbook §6）**：2-buyer 块纳入+wei 同额检测，防漏强指纹对。
- **Alpha Router 月度净流分析件（pipeline-evm §4 Alpha 条）**：托管量月度差分=场内净买卖压力曲线（Alpha 在架币标配）；净流出月归因必查"结算引擎回吐 vs 直接提现"分量。上架时间链上锚点=Router 首收币块。
- **脚本收编**：fetch_fundedby.py（bscscan Funded By 批量抓取器，单线程 0.8s+磁盘缓存，147 址 8 分钟实测）入 scripts/evm/。
- **Known Gaps**：①哈基米待证关联对（第二大外部单址↔0xHeme 系）待 /token-update 验收；②cluster.py miss-queue 新记 89 个高权重未命中地址待回填；③V4 量能哨（单日毛量占比>20%）待实装投后监控。
- 成本指标：约 95 轮 / Bash 约 80 次 / 交付 ~13h（采集长跑 ~10h 含 429 与通道切换 ~1.5h）；复核 4 路 ~70 万 subagent tokens，翻出 1 实锤修正+2 措辞降级——投入产出比再验证。

## [2.27.0] - 2026-07-18 — Index(Robinhood) 全量分析复盘：HyperSync 429→RPC getLogs 备选通道 + 第5类发射结构(外部资产分红盘) + EIP-7702 做市钱包费流陷阱 + 染色闭合口径

> 用户 2026-07-18 确认"全部写入 skill"——pipeline/playbook 正文条目已全部落地（下列各条已写入对应 references 文件）。

- **★HyperSync logs 高峰期整体 429 连败 → 公共 RPC getLogs 备选通道（pipeline-robinhood 待写）**：本次 HyperSync 拉到 ~10.79M 块后 429 连败退出（断点续传循环也救不回=服务端时段性限流），切公共 RPC `eth_getLogs` 拉尾段 12.5 万条速度可观（~20s/35万块）。RPC getLogs 坑：①"log query timed out" 需自适应缩窗（40万块起、超时折半、热点段降 5万）②单响应上限约 1 万条 ③**无块时间戳**，须另拉锚点（每 2 万块一 eth_getBlockByNumber）线性插值（实测误差≤1s）④HyperSync 段 ts=unix int、RPC 段插值也须转 unix int，合并前统一格式（踩坑：插值先写 ISO 字符串致 replay 排序 TypeError）。
- **★第 5 类 Robinhood 发射结构：ReflectionToken 外部资产分红盘（pipeline-robinhood 待写）**：普通 ERC20 + V4 hook 收原生 ETH 税(FEE_BPS constant/treasury immutable) → StockTreasury 买"代币化股票" → Distributor 按链上 holder registry(minShareBalance 门槛，holderCount/holderAt 直读) pro-rata 分发。分析要点：分红是外部资产不污染本币筹码，税=项目方现金流用 StocksBought 事件 ethSpent 求和量化；LpLock 永久锁池(无 removeLiquidity/withdraw、非代理不可升级、seed onlyOwner 一次性、collect 零 delta 只领费)是新 rug-proof 结构。
- **★"费收合约"可能是 EIP-7702 Ambire 做市钱包（playbook §7 待写）**：LpLock.collect(address to) 的 to 由 owner 任意指定；getCode=0xef0100 前缀=7702 委托 EOA。费流去向必须实际追踪（本案 collect Index 只销毁 65% 非"全烧"），"项目方零留仓/纯公益"叙事必查 collect(to) 去向+rewardsExcluded 标志+getCode——做市钱包持币+领分红会被漏归散户。
- **★染色(taint)比例分摊闭合口径（playbook §6b 待写）**：开盘扫货型集团出货量化用"注入%=净退出%+现存%"闭合，比名单口径现仓严谨；区分 gross 卖出(含往返)vs 净退出，避免"已卖77%+现存17%=94%>注入88%"口径不自洽(本案初稿踩坑、复核抓出)。
- **脚本收编（scripts/robinhood/）**：pull_transfers_rpc.py（HyperSync 429 时 RPC getLogs 全量备选，token/rpc 从 config 读、块范围 argv、自适应缩窗）、pull_block_ts_anchors.py（块时间戳锚点插值）、merge_hs_rpc.py（HyperSync gzip+RPC jsonl 合并去重填 ts）——三脚本 py_compile 通过。
- 成本指标：243,420 条 Transfer（HyperSync 到 10.79M + RPC 续 12.5万）+13,546 V4 ModLiq；5 路子代理（2 调研+3 复核，全 CONFIRMED，纠 1 子结论+3 口径+1 新实体）；约 95 轮/75 Bash；定时任务延时 4h 启动 + 3 次会话中断重启。

## [2.26.0] - 2026-07-18 — PING(Base) 全量分析复盘：Base 双通道拓扑反转 + 跨通道去重键陷阱 + AccessControl 口径盲区 + V4 单例池范式

- **★Base 双通道拓扑与 BSC 相反（pipeline-evm 新增 §8）**：HyperSync base 高峰期 429 连败（~250条/s 且不稳定），Alchemy base-mainnet 反而 ~230条/s 稳定零限流（走 clash 代理，免费层 30M CU 充裕）——分段接力法（HyperSync 拉发射段 + Alchemy 按 fromBlock/toBlock 多轮并行拉近段）2:1 提速拉完 239.3 万条。Base 官方 RPC getLogs 限 1 万块/batch 限 10 calls（角色事件全史改走 HyperSync topic 过滤）；Blockscout base 的 token-transfers（双币腿核账）/counters（公共性体检）免 key 可用。
- **★跨通道拼接去重键陷阱（本次最大坑，链无关）**：HyperSync uniqueId 尾号=链上 log_index、Alchemy 尾号=类别内序号——语义不同，跨通道按 (tx,尾号) 去重必然失败，重叠段双计实测造出 5,485 个负余额地址。正解=按块段给通道划唯一归属+段内自家键去重+"负余额=0"放行（replay_pass1.py 固化并内置段重叠校验）。
- **★AccessControl renounce 口径盲区（playbook §1）**：GMGN/GoPlus 的 renounced=true 只读 Ownable owner()——AccessControl 角色须 hasRole eth_call 逐个亲验（selector 0x91d14854）+ RoleGranted 事件从**部署块**起拉全史；"角色在手"与"能否增发"分开验证（mint 计数器 immutable 打满=角色在手也增发不了）。配套：config.json 的 deploy_block 必须记真实部署块而非首笔 transfer 块（pipeline-evm §8.2）。
- **★V4 单例池范式 + x402 mint 型标的（pipeline-evm §8.3/8.4）**：全部 V4 池共享 PoolManager 单例（池子余额=全 V4 池合计，当普通地址会误读成超级大户）、pairAddress 是 32 字节 pool id（GT OHLCV 直接可查）；"LP 锁定"的 V4 形态=token 合约自持 position+源码无撤出函数。x402 币 mint 走 facilitator 批量代执行（一 tx ~47 笔），mint 账本按 from=0x0 接收方记不按 tx.from；此类标的转账笔数与市值异常比极端，数据量预估按事件密度抽样（HyperSync 抽样外推按"服务端每响应条数上限"理解 next_block 推进，首段块跨度外推实测低估 5 倍）。
- **playbook 方法条目 7 条（§6/§7/§11）**：大户入方溯源独立于峰值普查表（低余额高吞吐"隐形管道"盲区，执行合约峰值从不上榜）；DCA 定投服务假分发器（入方 99%+ 是池子即拆穿，用户间无关联）；同模板 bot 路由粘连假实体（设施剔除名单须含"同模板高对手方合约"getCode 哈希分组排查）；registry 标签命中优先级高于行为学（deBridge 履约管道禁并入实体，三源裁决实证）；灰产资金池可为实体 gas 上游（背景画像不作合并边）；挂单式慢出货（收币→加 CL 位→质押 gauge→撤位收对价=限价出货新形态，误读成"分钟级卖出"会错写节奏）；collectLpFees"从池收币"≠买入（method 名+双币腿定性，定向动词第④查）；"名单现持全≈0"群体断言逐址复核（43 址名单混入 1.02% 在场残仓实测）。
- **脚本收编（scripts/evm/）**：fetch_alchemy.py 参数化升级（--config/--from-block/--to-block/--out-dir，key 走 config 不落 skill，支持块段接力+代理字段）；新增 replay_pass1.py（多通道块段互斥拼接去重→merged.csv+终态余额+峰值普查+mint 账本+供给闭合 gate）、replay_pass2.py（merged.csv+camps.json→每日阵营/实体占比序列，分母自动读 replay_stats 的 mint_total）。三脚本 py_compile+真实数据冒烟通过（段重叠校验实测报错、截断样本负余额被 gate 正确拦截）。
- **复核实效**：五路数据级重算（聚类/项目方/大户溯源/量能/完整性）——13 CONFIRMED / 4 WEAKENED / 2 REFUTED；REFUTED 两条全在项目方章节（"从池买入"实为 collectLpFees 领费、"11 分钟内卖出"实为加 CL 流动性+质押挖矿），实体变现口径实质改写。
- Known Gaps（PING 案遗留）：lpGuardHook 现状未闭环（selector 定位失败，不影响增发结论的纯尾巴）；两个策略合约（合计 3.93%）部署者/受益人未穿透；CEX 提币潮 ~1,800 万枚未溯源提币者；小庄#1 的 deBridge 下单源链身份（跨链盲区）。
- 成本：全量首战约 4.5 小时（含 3 路调研 + 5 路对抗复核 agent），Bash 约 80 次，主上下文一次未断；双通道 4 轮采集合计约 55 分钟（HyperSync 高峰限流拖累，Alchemy 三轮接力救场）。

## [2.25.0] - 2026-07-17 — 标签库 v4.2：round-trip 闭环 + 行为守门员 + P0 覆盖面（codex 第四轮交叉复核；"为什么四轮审计还有漏洞"的流程性回答）

**总路线（用户四轮同题复核后拍板）**：审计循环不收敛的根因=①审计是 LLM 注意力采样不是清单穷举②发现没固化成机器断言③修复引入新面积只验正向路径④零实战反馈。对策=封闭问题一次性系统化（不变量+门禁的门禁）+"全"的职责移交行为判别+扩容改实战 miss 驱动。

- **★round-trip 三断环（本轮最重发现，全部实测证伪"重建幂等"）**：①`upsert()` 无 policy 参数——全量重建丢全部手工 merge_policy/balance_policy 覆盖（v4 加列时引入，无 round-trip 测试）；②**v4.1 七份增量文件不在重建源里——全量重建静默丢约 250 条 registry 级设施标签**（modus：add_labels 只写现库不进真源）；③SOL spellbook 21 条"格式合法但链上从无签名"垃圾的删除只做在现库——重建即复活（v4.2 干跑当场抓获 bc1q/DdzFF 地址回魂）。修复=upsert 透传+`sources/additions/` 目录整目录进重建流（add_labels 入库成功自动归档）+清洗审计档 never 名单进构建器；historical 120 条/未归档增量 22 条导出固化文件。**教训：一切"只改现库不改真源"的手术都是定时炸弹；验收必须含全量重建 diff**。
- **★带毒标签比缺标签更危险（codex 第四轮核心发现）**：ETH 17 条 Alchemy/Candide/Stackup bundler+paymaster 因 dawsbot 项目名长尾类目默认 identity——每天代付十万笔 gas 的公共设施在库里"合法"参与聚类与 gas 溯源（建库首日进来，四轮抽查全漏，因为没人 grep 过 bundler）。修复=构建器 AA/Seaport 名字归一+设施类目（cex/bridge/router/mixer/bot-service）identity 矛盾行强制 exclude（规则化后实抓 27+2+7 行，比单点修多 19 行）。
- **★"疑似"条目禁边不剔仓纪律 + suspected-cex 类目**："疑似 OKX/Bitget（未免费确证）"直接 cex+exclude=真大户持仓可被静默藏掉。新类目=identity+no_merge+count；validate 不变量 14 强制"name 含疑似/未确证 ⇒ 不得 exclude"。launchpad 入 NO_MERGE_CATEGORIES（平台地址与用户的边全是公共通道边）。
- **★validate 不变量 11-14 + benchmark 门禁的门禁**：status 枚举白名单（DxLock 源文件半角逗号切爆字段错位值 2026-07-17 实锤放行过）/设施类目≠identity/AA 必须 exclude/疑似不得 exclude；benchmark 七链强制出现（此前只遍历 goldset 已有链——HL/FIL 零金标静默 PASS，"PASS 才发布"对两链是空承诺）+`--labels-dir` 发布前预检+HL 赌池 no_merge 覆盖进金标=policy round-trip 活体断言；goldset 支持 dict/list 形态 appendix。
- **★行为守门员 gatekeeper.py（防线重心从"查全"移向"兜底"）**：漏斗指纹（fan_in≥30 且 fan_out≥30 且净留存≤5% 且笔数≥80 ⇒ FUNNEL 禁边）纯本地零 RPC；bibi(BSC 20.5万转账)+TRASH(RH 9.9万) 双案校准 **47 实体误伤 0**、净增益 8 个库外真漏斗（含 BSC 侧未标的跨链同址服务合约——行为层抓住了静态库的漏）。evm/cluster.py 默认接入（R1+R2 双拦截、serial/team 豁免、gatekeeper_blocked 对账、FUNNEL∧未命中库 ⇒ miss 队列最高优先级回填候选）。miss 队列首次吃到实战数据（bibi 案 13 条）。
- **P0 覆盖面 208 条（全部官方源+链上亲验双纪律）**：Safe 官方部署家族 72（safe-deployments registry+三链 getCode 批量亲验，Robinhood 4663 在官方 registry 有登记；MultiSend=批量分发通道高危）；Relay 22 solver EOA 按链精确收录（api.relay.link 官方 API 亲验，RH 第 5 个 solver 为新发现）+Relay/Across/deBridge/LiFi/Socket 合约层 95 条（LiFi Executor/Receiver **各链不同址**；Across MulticallHandler 三链同址）；**Base bundler 24+paymaster 12**（HyperSync 7 日 33 万 UserOp 聚合，tx.from=bundler、topic3=paymaster——此前 Base AA 层=0 是 gas 溯源假金主最大盲区）；EntryPoint v0.6 四链（getCode 亲验 code 全长一致）。
- **韩所 SOL 调研定论（诚实盲区）**：四所无官方披露、主流标签库全空；唯一链上实证=Upbit 2025-11-27 被黑事件——疑似热钱包 2 条（signer 反查 B 级：6000+ 高频、事发后活跃至今、余额归零画像；主线程 getSignatures 独立复核）入 suspected-cex，攻击者 3 条（Blockmedia 逐字+RPC 时间戳吻合官方通报）入 heist。韩流币的韩所归集靠守门员兜底。**spellbook "Korbit" 5 条=BTC bech32 错标**（never 黑名单已拦）。
- **Filecoin cluster.py 接 resolver**（README 宣称"全链路接入"与事实不符的欠账）；add_labels 自动归档；benchmark --labels-dir。
- **坑（实测）**：python urllib 直连 publicnode 被拦而 curl 通（改 curl batch JSON-RPC，72 地址一链一请求）；safe-deployments 新版 registry 格式 networkAddresses 值是部署类型名（canonical/eip155），真地址在 deployments 段；UserOperationEvent 的 paymaster 在 **topic3**（topic2 是 sender——错读会聚合出 9.3 万"paymaster"=智能钱包全集）；HyperSync 空响应重试勿推进 next_block。
- 成本：单会话三步全交付（机制修复+重建发布 ×3 轮迭代+守门员两案校准+调研员 2 路+链上聚合 2 轮），Bash 约 60 次。

## [2.24.0] - 2026-07-17 — DUMBMONEY(Robinhood) 全量分析复盘：满贯池判级分母 + gas 溯源采样截断坑 + LP/价格脚本 IO 约定

- **★满贯池标的判级分母（playbook §6a）**：铸币 100% 入池标的的历史峰值判级必须并行"池外流通"口径（分母=总量−主池−销毁，逐时点重放），实测同一实体两口径差 2.6 倍（8.33% 总量 vs 21.9% 池外流通，判级结论相反）；发射后极早期（池外 <15% 总量）流通分母病态放大，该窗口瞬时峰值不适用流通口径（防发射 bot 全体误判庄）。
- **★gas_trace_bs per_addr_limit=8 采样截断坑（pipeline-robinhood）**：每址只取最早 8 笔入金会系统性漏采高频双向 funder 关系（实测漏"creator↔关联人 9 笔双向往来"与"埋伏对建仓前 5 ETH 直转"两类关键边，全部靠复核的 Blockscout 全量双向拉取翻案）；纪律=funder 收敛分析须全笔分组（禁"每址最早一笔"）、P0/重点地址一律 Blockscout 双向+internal 全量兜底。
- **HyperSync 并发纪律收紧（pipeline-robinhood 通道表）**：高峰时段 2 路并发也 429 连败（meow 案"≤2 路安全"不恒成立），429 即降级全串行+批间隔 30s。
- **脚本 IO 约定三坑（pipeline-robinhood 脚本节）**：build_price 硬读 `data/ethusdt_1h.json`（[[ts,close]] 升序数组）+`ohlcv_minute.json`；pull_lp_events 不读 config、须命令行 `--from-block/--pools/--out`；其输出是 JSON 数组（非 JSONL）且 amount0/1 为已解码浮点（非 wei，按 wei 解析费流水全归零）。
- 本次实战验证（未新增条目）：serial-actor 惯犯层首次在全量分析中直接命中 3 个历史案集团（身份引用+本案独立判定的边界把握顺畅）；"截断地址禁止补全"纪律 4 次拦截编造地址（两次是自己犯、两次是消费复核转述时拦截）；四路对抗复核 2 REFUTED + 多项 WEAKENED，全部实质改写实体表。
- 成本：全量首战约 5.5 小时（含四路复核与三路调研 agent），Bash 调用约 70 次，主上下文一次未断；HyperSync 全量 Transfer 仅 39 秒（13,711 条，26 天链史新盘的量级参考）。

## [2.23.0] - 2026-07-17 — Pointless(Robinhood) 二次增量更新复盘：协同检验 ETH 资金面纪律 + 定向动词三查（与 v2.22.0 TRASH 案同日互补——两会话独立踩中"分仓贴线漏检"同类坑，对策合并生效）

- **★协同检验双面纪律（playbook §6 + update-workflow U3a）**：token 面四维全阴性≠独立，合并铁证可 100% 在 ETH 资金面（wei 级等额批量注资/同秒多址注资闭环/gas 双向互供；disperse 类分发合约"单批次归属单一操作者"可作合并边）——实锤：九址协同工作室现仓 4.71%、峰值曾破小庄线，初判"双址簇 2.98%"靠对抗复核以 ETH 面证据扩成整族；两个 0.8-0.9% 马甲恰逃 1% 深挖线（与 TRASH 案"低档同秒共现扫描"对策互补）。配套：gas 溯源 first_in **逐笔消化**（只看第一笔漏"三马甲同秒供 gas"）；"旧期零交织"要查**行为交集**（三胞胎旧期 150 条同块协同、持仓端点为零，持仓交集检验完全漏检）；同实体观察哨按合并口径设（单址阈值被分单绕过）。
- **★定向动词三查（playbook §11）**：①"资金经过某合约"≠"进入黑箱"（多身份设施把 swap 误读成提现）②"在场+清仓"≠"收割"（须算完两腿对价——被判"潜伏收割"的惯犯双址实为净亏 78% 割肉）③平台函数动作定性前扫同期全平台调用分布（"主动抢费"实为单日 911 笔的平台级登记浪潮跟随）。宁可只写事实不写动词。
- **Robinhood 新坑 4 条（pipeline）**：0xb92fe925 多身份（App 交付金库兼 RelayRouterV3 swap 路由——出境判定看 RelayDepository 入账不看是否碰过它）；NOXA feeRouter 的 collect/setConfig 均无许可（3/6 轮 collect 系第三方代触发，烧速退化为 collect 频率指标；setConfig 有平台级浪潮）；Blockscout 列表首页 50 条截断活跃地址窗口核查（改 HyperSync 全量）；App 黑箱"清仓-重建仓"覆盖率量化范式（123% 实测入局限性）。
- **update-workflow 哨兵复判补丁**：mode-aware 自动核查漏复合触发条件的"或清仓"腿——人工复判逐条对照 trigger 原文每个"或"分支。
- **标签库/地址簿**：0x243a 热钱包新增入库（add_labels 增量+benchmark PASS）；0xb92fe 双身份、0xd29c=Across SpokePool、0x3f43 批次穿透用法三条补注对齐。SERIAL 惯犯层增量首战命中（另案集团 2 址潜伏仓 3.54%）——回报确凿。
- **实战成果**：无新 P0/P1（4.71% 贴线实体最高显著度披露+合并哨）；旧观察哨 9 条触发 5 条；两路怀疑者复核实质改写 6 处定性（A 路把双址簇扩成九址工作室、B 路推翻"抢费/黑箱提现/惯犯收割"三个动词）；对账三查全过。
- Known Gaps：工作室A 金主层 L1 侧身份未穿透（Relay 桥断头）；场外发币网络与 dev 集团深页历史边未穷尽（597 笔仅扫首页）；分发合约 0x3f43 的其他批次接收方（潜在其他标的马甲网）未扫。
- 成本：约 58 轮、Bash 约 50 次、活跃约 3h（含两路复核 agent 各 35-40 分钟）；U2 曾因旧快照仅存 264 大户地址触发双路径 FAIL，rebuild_wei_balances 标准兜底 10 秒修复。

## [2.22.0] - 2026-07-17 — TRASH(Robinhood) 二次增量更新复盘：新庄扫描两大检测盲区修补 + add_labels 回滚 bug 实测修复

- **★分仓贴线漏检对策=低档同秒共现扫描（playbook §6 新硬步骤 + update-workflow U3a 指针）**：份额候选线（如 ≥0.8%）可被"多址分仓、单址全部压线下"精确钻空（实锤：9 址协同族单址全部 <0.55%，全量+增量两轮分析漏检，合并 3.69%、对抗复核才翻出）。对策：0.1%–候选线档全体地址按"从池买入时间戳"聚集，同秒 ≥5 址即翻整族（等差递减面额=程序化附加指纹）；零额外采集成本。
- **★gas 档案双向用（playbook §6 新硬步骤）**：只正查"候选的金主"漏掉"候选是别人的金主"——实锤：某"独立新面孔"实为已知庄家集团最大成员的 ETH 金主（6 笔 8.7 ETH 发射前），反查即命中。gas_in 档案建 funder→下游反向索引为聚类标准步骤。
- **★暴涨暴跌归因逐笔价格对齐纪律（playbook §7）**："拉升时段内卖出"≠"顶部出货"（实锤：初判"顶部精准出货"的协同组实际卖在主升浪前 12 分钟、约开盘价一半——恐慌卖飞，定性反转）；"顶部出货"只授予均价 ≥顶部 70% 的卖方；崩跌归因看首卖距顶时长与价位（"回砸砸盘"实为距顶 5.7h、-75% 处亏 40% 割肉）。
- **★出金监控盯本尊转出（playbook §7）**：出金模式代际升级（冷藏→冷藏→一次性跳板 nonce=1 即收即 depositNative 跨链），盯历史收款地址的哨兵天然失效——threshold 哨直接盯本尊 value>0 转出。
- **★怀疑者地址转录不可信（research-workflows §2 裁决纪律）**：怀疑者结构性发现可全对（前缀/尾缀/份额/事件秒精确）而 40-hex 中段整批幻觉（实锤 9/9 错）——采纳前必须用其描述的行为特征从本地数据重新检索真实地址。
- **watch_return 条款纳入哨核查循环（update-workflow U3c）**：addresses 级"重新持币=回场"条款不在主哨 monitoring_advice 里,漏查即漏报（实锤：庄#1 集团 8 址回场 1.9 千万枚系该条款触发）。
- **中位价格序列抹极值坑（data-pipeline-robinhood 坑表,链无关）**：小时中位把高点抹低 33%/低点抹高 18-22%+漏二次探底——极值叙事必须 GT high/low 或逐笔,中位序列只画形态。
- **address-book Robinhood +4**：RelayDepository 0x4cd00e（Relay 桥存款库=跨链离场断头,与 0xf70da 同生态反方向）+3 原子中转设施（0xa687/0x2e9b/0x8f10）;gen_manual 同步、check_manual_sync 一致、benchmark PASS。
- **add_labels.py 回滚 bug 实测修复**：旧版先落盘后校验,FAIL 时只打印"从备份恢复"但从未备份——坏行滞留主库（本次增量入库实测踩中,21 条含半角逗号的行污染主库,手术剔除恢复）。修复=写盘前 .bak、FAIL 真回滚、成功后清理;破坏性实测通过（坏行触发 FAIL→自动回滚→主库零残留）。另:additions CSV 的 name/evidence 字段禁半角逗号,生成一律 csv.writer QUOTE_ALL。
- **标签库 serial 层 +21**（TRASH 案协同组:vanity 九胞胎族 10 含 dust 工具、d5ff 网 4、996 网 6、庄#1 第 19 址）;协同观察组用 name="协同建仓组（XX案·组名）"区别于已判级"惯犯庄家"。
- Known Gaps：①矩阵族↔vanity 族并体待定案（跨族直接边监控中,7.16% 若实锤即新庄）②dust 工具 0x5fff 上游未挖 ③TRASH 已连续 2 次增量更新,下次到 3 次触发全量重置基线规则 ④分仓更细（<0.2%/址）的协同结构仍是理论盲区。
- 成本：主会话轮次 ~85、Bash ~55、活跃 ~3h（超更新任务参考预算：HyperSync 并发冲突串行重试 + 对抗复核翻出 vanity 族/庄#1 第 19 址触发简报/appendix/图表全面第二轮修订——修正即质量,符合成本让位准确性铁律）;子代理 4 路（社媒/审计/怀疑者×2）合计 ~53 万 tokens,怀疑者两路合计翻案/加固 12 项。

## [2.21.0] - 2026-07-17 — 标签库 v4.1：覆盖面专项（codex 第三轮交叉复核，P0/P1/P2 全批全落地）

**总判断（双方共识）**：v4 是"高价值种子库"但四主战场设施层偏薄——46.9 万行里 61.9% 是 Tornado 隐私层，SOL 88% 是 validator、HL 82% 是 deployer。本轮火力全部投向"公共通道底座"。

- **spellbook CEX 三链投影分流（codex 硬发现+我方裁决修正）**：cex_evms 4,957 址是同一集合三链展开且无 EOA/合约分流——与 v4 OFAC 分流同构的逻辑洞。裁决"EOA 留+合约分流"否决 codex 激进版"全量重验砍到数百"（EOA 同私钥跨链同控，丢几千条正确标签换不来精度）。三链 getCode 后删合约空投影 531（eth 24/bsc 93/base 414），多源行保留；build_labels spellbook 段防回退。
- **SOL spellbook CEX 垃圾清洗（本轮最大意外战果，双方复核都没预见）**：166 条里 55 条是跨链垃圾——hildobby 表把 BTC bech32/Cardano 切片/Elrond/hex 错录成"Solana 地址"，且**全部恰好通过字符集+长度校验**。双层证据定罪：base58 解码≠32 字节（34 条格式假）+ getSignaturesForAddress 从无签名（21 条从未上链）；14 条有历史签名的真地址标 historical。norm_addr 改 base58 解码必须 32B（validate/add_labels/upsert 全链路生效）。教训：**"人工维护的上游"≠格式可信；地址真伪的最后防线是链上存在性，不是正则**。
- **HL 三连修**：CEX_WORDS 漏 robinhood/bitvavo/coinspot 致 8 条交易所钱包错归 entity 参与聚类（codex 发现，词典+manual 覆盖修正）；HyperCore↔HyperEVM 系统转移地址族 472 条确定性生成入库（官方规则 0x20+token index，PURR 系统地址持 5.1 万亿 wei 实锤"漏标即假大户"；spotMeta 快照进 _EXTRA_SOURCES 防回退）；entity 层词典二审 19 条（Unit 五大资产托管金库→bridge/exclude、HyBridge→bridge、两 MM 归位、3 空投钱包→airdrop-distributor、4 赌池显式 no_merge）。
- **BSC 设施底座**：现役桥 30 条官方亲验（Stargate V1/V2、LZ V1/V2+ULN、Celer 6、deBridge 5、Axelar 4、Wormhole 2）+106 条 Multichain 死桥标 historical（占原 bridge 类 51%）；router 家族 18 条（Pancake 九类角色——**V2 Router 0x10ED 此前竟不在库**、THENA 4、Biswap 3）；locker 17 条还清 README 欠账（FlokiFi 三代厂/DxLock 7/GemPad 2/Mudra 2/DeepLock/CryptEx/UNCX V2）；four.meme 全家族 11 条（官方 gitbook 附件 md 亲验 V1/V2/Helper2/Helper3/AgentIdentifier+fee 推断+部署者锚点+3 impl；**旧登记"0x757e 主合约"证伪**——仅 18 笔 tx 辅助合约，主力是 V2 0x5c95 2846 万笔）。
- **SOL 出货所层**：四所热钱包 23 条全链上亲验（MEXC 主力 40.2 万 SOL/Gate 主力 21.9 万 SOL 实锤；Bitget 12 条 DefiLlama 自报 C 级；OKX 2 条 GMGN/Solscan 增补）；Jupiter Lock+Bonfida vesting（locker 3→5）+Boop 主程序三重验证+Believe 架构结论（无自有程序，平台钱包直调 Meteora DBC——Token Authority 单源 C 级入库）。
- **GoPlus 运行时风险通道（P2）**：goplus_check.py——address_security 是查询式 API 不能拉黑名单，做成候选大户批量体检（30/min 限速+断点缓存）；EVM 实测可用（OFAC 攻击地址命中 stealing_attack/SlowMist），**SOL 覆盖未证实**（制裁地址返回全 0，如实标注）；candidate 纪律挂 README+playbook。
- **Robinhood verified-contracts 增量通道（P1）**：pull_verified_contracts.py 分页拉候选池（增量模式拉到全页已知即停；同名家族统计=克隆工厂线索）；只产候选不自动入库。
- **方法论沉淀**：①GMGN holders API name 字段是 SOL CEX 标签最高效通道（十币 top100 扫一遍覆盖主流所归集地址）；②四调研员并行抓官方源+主线程逐条链上复核（getCode/executable/余额）的分工模式全程零返工；③WebFetch 小模型转述会失真（Wormhole"同地址"误报、BscScan UI 按钮当标签）——**地址类调研必须 curl 原文逐字复核**。
- **坑（实测）**：BscScan curl 需代理+浏览器 UA+间隔≥2s（连发 HTTP 000 冷却 20s）；four.meme 官方地址藏 gitbook 附件 md（渲染页/llms.txt 均无）；deBridge 文档两跳迁移到 docs.debridge.com（靠 sitemap.xml 定位）；LayerZero docs 是 React SPA（用 metadata API+npm 包双源）；dx.app 多链同址部署（跨链复用标签注意链别）；getMultipleAccounts 一批里混非法地址会整批报错（先本地 base58 解码过滤）。
- 成本：单会话全量交付（P0×5+P1×5+P2×1+收尾），4 并行调研员+主线程复核。

## [2.21.0] - 2026-07-17 — BEGGAR(Robinhood) 分析复盘：gas 边"发本金"检查 + 分钟级行情归因两大方法修正

- **★方法修正（playbook）**：①§6 聚类新增 gas 边"发本金"性质检查——「转账 ETH ÷ 下游买入成本」≥1 即母子边（实测漏检致某集团 7→12 址、峰值低估 53%、一个 1.14% 潜伏仓藏身"其他大户"）；②§7 新增"行情归因最小单元=分钟级价格路径时点"（日级净额把'卖飞在日内低点'误判'借涨出货'，三处细节被复核推翻；出货窗口叙事须并列当日净买盘）+"喊单类利好对齐推文精确时刻"（'利好日回补'实为'公告前 4.5h 进场'时序反转）；③§4 新增"平台出纳机器人 ETH 分发名单=官方关联仓发现通道"（借此发现官方系隐性仓 0.15%）。
- **pipeline（robinhood）**：坑 4a 新增——LaunchToken 参数是发射配置项（maxTxBps=10000 即不限单笔）、发射块 deployer 特权**可不行使**（"平台有自买前例"≠"本案必有自买腿"，发射块 transfer 实证）、狙击顶格整数枚=专业指纹、ENS 双向解析（ensdata/ensideas 免费 API）作官方身份链上自认级证据；build_price 依赖 ethusdt_1h.json 为 list 格式（与 cost_engine 的 dict 并存两口径）。
- **address-book/labels**：Robinhood 段 +7 条（NOXA 官方族 treasury.noxa.eth/出纳机器人/LaunchLocker + 4 个公共卖币执行合约）+dev.noxa.eth 补注 ENS；labels-robinhood 增量入库 6 条（新 4 合并 2），check_manual_sync 一致、benchmark PASS（infra 召回 manual 45/45）。
- **复核实效**：4 路（A 聚类/B 项目方/C 归因/D 完整性）——A 两处 WEAKENED 均为方向强化型上修，B 四条全 CONFIRMED＋翻出官方关联仓，C 推翻 3 处细节（含一条 REFUTED："持有至今"实为双程波段客），D 因会话重启中断、独有项由主线程补做（V4 参与者/极端K归因/沉默大户）。修正记录 10 条印进报告附录 C。
- **坑（实测）**：会话重启后 subagent 被判"用户停止不可恢复"——复核路中断优先 SendMessage 续命，彻底丢失则主线程按其 prompt 补做独有项并在局限性声明。
- Known Gaps：BEGGAR 案 8859 集团 4 个弱边波段址未并入（峰值时点仓位 0）；7 个合计 5.33% 大户 gas 经平台内部通道不可观测；0xcdfc08a1…ca90 的"头部 meme 创建者"身份 tx 直验一次失败待补。
- 成本：主会话约 60 轮、Bash 约 55 次、交付约 2.5h（含 1 次会话重启续跑）；subagent 6 个（2 调研+4 复核）。

## [2.20.0] - 2026-07-17 — 标签库 v4：决策语义三维拆分 + 全链路接入 + 惯犯层（codex 第二轮交叉复核全量落地）

**总路线（codex 力主并被采纳）**：先修"语义/接入/基准"三断环，再谈扩地址——SOL 流程此前根本没接 resolver、Base entity 金标为 0 却承担门禁、批量分发工具可合法作合并边，任何"再补十万条"都是给断路电网发电。

- **决策语义**：tier 单字段拆为 merge_policy（no_merge 扩 locker→locker/airdrop-distributor/token-sale/charity 四类公共通道）+ balance_policy（count/bucket/exclude）+ 风险四档白名单（definitive 白名单制修复"未知旗标一律定性"休眠炸弹，unknown 档人工核验；validate_labels 白名单外旗标禁止入库）。
- **全链路接入**：SOL replay_edges（top/sniper/trace 标签标注+miss 队列）与 build_evolution（阵营体检：设施混入实体阵营即拦截）、HL main_metrics（AMAP 兜底+聚类 no_merge）首次接 resolver；全部入口 degraded_mode 显式告警（"没命中"≠"没加载"）；分析产物落 labels_meta。
- **惯犯 serial-actor 层（本方差异化提案）**：accumulate_offenders.py 从 15 份 appendix 聚合实锤收割集团 196 址（自动规则+人工白名单，宁缺毋滥），lookup 七段之首 SERIAL 高亮；首建即抓出 CASHCAT 工作室 2 址现身 NOXA 案的跨案惯犯。
- **金标扩衡**：random-eoa 负样本 120 条（低频交易者 sha256 确定性抽样）摘掉 BSC 弱门禁；余弱门禁链（base/eth）显式 ⚠️ 声明不再假装有防线。
- **Base 定向补录 54 条**（全部官方源亲验带 URL）：Aerodrome 全家+Slipstream 三代、Clanker v3.1/v4 全家、Zora Coins 官方 npm 包全量、Uniswap V4 Base（双源吻合）、Virtuals Base（docs+CoinGecko 双源）。
- **风险层跨链纠偏**：probe_codetype.py 批量 getCode 分流（OFAC 90 EOA/6 合约、ScamSniffer 2389/141）——EOA 才三链注入，BSC/Base 各清理 147 条历史合约误注入（上一轮 codex 建议被这一轮 codex 推翻，裁决取两者交集）。
- **新链**：labels-hyperliquid.csv 首建 464 条（Hypurrscan aliases+WHYPE RPC 亲验）、labels-filecoin.csv 首建 25 条（filfox 官方 tag，f 地址规范化进 resolver）。
- **Robinhood codehash 组合指纹**（fingerprint_check.py：sha256+长度+selector 签名，candidate 语义）：三模板入库，实测揪出"0x68be51 是模板升级版而非同款"的旧记录偏差。
- **B8 审计**：BSC 12.4 万 tornado-user 实锤为真（spellbook 事件级模型 SQL 审计+链上抽验 9/10 命中；0/5 首验失败系 proxy 调用语义——用户 tx.to 是 proxy 不是面额合约）；顺带入库 Tornado BSC 合约本体 5 条（此前 12 万用户在库、合约本体反而不在）。
- **体积治理**：纯 tornado-user 29 万行拆 labels-{eth,bsc}-privacy.csv 子表（resolver 自动合并，主表 ETH 30.7万→14万/BSC 13.9万→1.5万）；v4 六扩展列（policy 覆盖+source_snapshot_at/verified_at/status/raw_labels 时态与溯源）。
- **工程机制**：add_labels.py 增量入库（免重建+自动校验）、check_manual_sync.py 双真源一致性（不过构建失败，首跑抓出 HL 两条漏同步+自身正则 bug）、official_registry.csv 官方注册表源、实战 miss 队列（cluster/analyze/replay-top 自动落盘未命中高权重地址）。
- **坑（实测）**：publicnode/filfox 与 Robinhood 同款 python-UA WAF（403 像限流实为 UA 拦截）；codex-crosscheck.sh 在非交互 shell 须 `< /dev/null` 否则 codex 等 stdin 挂死；HyperSync logs+transactions 联合查询步长骤减（改两段式：纯 logs 大步扫+RPC 批取详情）；dRPC 对 batch JSON-RPC 回 403。
- **重建链路空壳干跑（发布前最后验证）抓出两枚重建时才会引爆的 bug 并修复**：①HL/FIL 表源不在主构建器——月度重建 cp out/ 会把 464 条 HL 表覆盖成 2 条（修复：_EXTRA_SOURCES 机制+缺失告警）；②旧 upsert 地址校验只认 SOL/EVM，FIL f 地址被静默丢弃且 merged 计数照常（修复：统一走 labels_resolver.norm_addr）。教训：**新链入库必须干跑完整重建链路，"增量入库成功"不等于"重建也对"**。
- 成本：单会话全量交付（P0×5+P1×7+P2×5 共 17 项），Bash 调用约 80 次。
