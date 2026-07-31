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
- **3.36.0 重复 ×2**（2026-07-26 并行会话撞号：「EVM 五币 E0b 批量」与「EGL1 复盘」各自 +1；3.37.0 条目的版本号顺延说明即因此而来——两条均保留原号，引用时注意区分）

## 版本索引（活跃窗口，新在上；每版一行，详情见下方对应条目）

- **6.3.0** 2026-07-31 减法整编（服务器搬迁前瘦身，用户逐档批准）：纠错 7 处漂移/已证伪规则（methods 等额归集反向教条改写为"先测中枢身份"、三查→四查、平线示例、外包档位权威源 ×2 等）+ robinhood 拆册（51KB→2.9KB 路由页+三分册）与 18 条通用规则上移 playbook + 来源标注全库治理 −20.5KB + solana-capture 层积岩清理 + report-template 门槛速查副本删除（唯一权威源收归 tiering）+ CHANGELOG 归档 9 条 + entity-cluster 跳转页删除——真减分析会话读入约 55KB
- **6.2.0** 2026-07-31 经验存留审计第一批（用户拍板"没核实的经验删掉"）：候选运行权限收紧（只当查证提示，废止"按正式规则对待"）+ attic.md 存档制落地 + 48 处显式候选三判据快筛（删 6 留 42）+ 惯犯库"实锤"措辞整体降级为案源分层线索级
- **6.1.2** 2026-07-30 split-run 契约收紧（PYTHIA 历史案 dry-run 步 3.5 产出）：READY 前置补 accounting_mode+supply_truth 两 gate 产物（A0/A2 必产件，缺任一 generate 即拒）；dry-run 九步全链路（真实 90MB 分片哈希/真实实体表 freeze/漂移检测/supersede）全过；测试 19→20 项
- **6.1.1** 2026-07-30 camp_share_series schema 文档修正（codex 侧 c1.0.0 实战发现回灌）：monitoring-package.md 示例由"逐日对象列表"改为 `{dates:[],series:{}}`——引擎 figures_from_facts fig1 从不支持前者，属文档-代码漂移；另回灌 codex 侧 BITCOIN 案 miss-queue 85 行
- **6.1.0** 2026-07-30 分段执行（split-run）落地：新增 references/split-run.md（−1 机械段/−2 判断段唯一权威源）+ handoff_manifest.py 四子命令与 19 项契约测试 + /token-analyze-1、/token-analyze-2 两入口（四→六）——−1 交 GPT-5.6/Opus，−2 交 Fable 冷启动，防长上下文注意力稀释；旧单会话命令原样保留为回退路径
- **6.0.0** 2026-07-30 架构级重构（薄骨架+判例库+评测）：SKILL.md 37KB→8.6KB 纯路由层 + analyze-workflow/context-discipline 两手册 + casebook 3 册 12 条判例 + evals 9 题 + 供给真值闸与 casebook_lint（唯一两项代码例外）+ commands 暂存重写 + 教训分流决策树——规则语义零变更
- **5.0.0** 2026-07-30 框架级用户修订：四问→三问（问 4 背景调查整体删除）+ 取消 P0/P1 重要度分级 + 废止"狙击集团"标签 + 其他大户线降至 0.1%/0.2% 并立排查前置双闸 + 流转图/素材装配对象收窄为 ≥20% 大庄/项目方
- **4.2.0** 2026-07-30 TROLL(Solana) 完整版复盘 + PYTHIA 复盘补遗：托管判定反向闸（0.002246=建 ATA 物理常数）+ SQD 同 slot 同额去重丢边缺陷 + pump.fun 长内盘期签名史双索引重建法 + 揭盲式独立重做转正（两案）+ Squads 解析脚本收编 + scan 扫描器 auto 判程序
- **4.1.0** 2026-07-30 PYTHIA 双报告交叉核实复盘：实体身份防复发三闸（label_lookup 并源 address-book / entity_identity_gate+G8 编译门 / 复核 prompt 翻案四问固化）+ 复盘元规则（身份类教训必须以代码收尾）
- **4.0.0** 2026-07-28 大整编（用户点名）：3.0→3.41 四十余版增量迭代的结构清理——路由索引补齐 9 节、结构错位归位 3 处、消重立权威源制 6 组、CHANGELOG 重整归档 29 条；只减不加，规则语义未动
- 更早版本（3.41.0 及以前）→ `CHANGELOG-archive.md`

## [6.3.0] - 2026-07-31 — 减法整编：搬迁服务器前瘦身（四方审查后执行，用户逐档批准）

背景：用户准备把本 skill 整体搬到服务器运行，担心"字数太多/规则太多导致执行 AI 记不住"，点名我方与 codex 联合审查做减法。四方审查（主线+codex 只读复核+3 路精读子代理）→ 用户批准"第 0 档纠错→第一档真减上下文→第二档搬迁瘦身"全量执行（第三档可选项暂缓）。服务器角色定性：**完整自迭代**（跑 A6 复盘+CHANGELOG+git commit），故 .git/evals 题库/archive/attic 全部随迁。

- **纠错 7 处（漂移/已证伪规则，比删字优先）**：①methods「N/N 等额归集→原路返还=最强协同指纹（可单独排除全部备择）」整条改写为「先测中枢身份，再谈协同」——原版已被同文件 SIREN Hedgey 翻案证伪却一字未动，是托管误判族（IQ/LPT/PENGUIN/PYTHIA 同族）的现成复发通道；②report-template「三查过关声明」→四查（v6 供给真值闸）；③report-template 蓝框示例「平线=没有加减仓动作」与 state-anomaly「占比平线≠没出货」硬规则冲突，改为流出核查措辞；④update-workflow 与 ⑤research-workflows 两处「外包档位唯一权威源=SKILL.md 刀 1」→context-discipline.md（v6 后三刀已迁）；⑥evm-channels「HyperSync token 每次让用户现提供」→已固化 ~/.config/hypersync/token 自动读取；⑦entity-cluster 跳转页"四问框架"残留随文件删除消失。
- **robinhood 结构手术（子代理执行+主线验收）**：51KB 单体 → 2.9KB 薄路由页 + 三分册（channels 13.8KB/traps 20.6KB/methods 9.1KB，坑 1–17 原编号保留并注记历史性 8/9 重号）；**18 条自称链无关的通用规则上移** playbook-entity-cluster-methods（13 条，其中 2 条与既有同案条目合并补差异）/playbook-state-anomaly（3 条）/playbook-evidence-wording（2 条）——此前这些规则埋在单链文件里，BSC/Solana 会话读不到；8 处外部引用同步修正。原文 113 行逐行去向核对零丢失。
- **来源标注全库治理（−20.5KB，700 条）**：「（来源：案名(链) 动作，2026-MM-DD）」统一压为「（案名[ 复核]，MM-DD）」——案名/日期/附加说明保留，复核类动作词保留"复核"字样（纠错来源信号），词表白名单制、不认识的形态不动；filecoin（57 条）/hyperliquid（36 条）单一来源整删改头部总声明；solana-scan `[VERIFIED·IO实录]` 反转为默认（32 处删除，母文档图例同步改，非 IO 来源标注保留）。
- **solana-capture 层积岩清理（49→42KB）**：§6"待重建脚本清单"收拢为脚本资产声明（所列脚本已全部建成，三条实现坑完整版本在 §3a）；§8 v1 时代旧吞吐层压缩（1.5-4x 数字已被 §13a 翻案）；13b 两处事故症状叙事压为纪律（伪 scan-fail/OOM 合并，修复与守护测试在案）；13d HyperSync 通道死亡名单化（判决/GA 重验路径/混合分段否决记录三件套保留，POC 细节归 git 考古）。stream 响应语义、TROLL 同 slot 去重坑、口径对齐三条等核心工程规则原样未动。
- **report-template 压缩与速查副本删除**：标签门槛表删除、唯一权威源收归 tiering §6a（原"三处同步"在 v6 后实际只剩两处，本身已是漂移）；三账本病例/图 1 overlay KOGE 叙事/术语节 SIREN 反例/阵营交叉自检案例各压为纪律+一行实锤。
- **其余压缩**：easy/update 案例长括号与成本战报压行（三战基准合并为一条）；environment 三段事故叙事压纪律+新增**平台适用性声明**（macOS 专属条目清单与 Linux 反转项，服务器首战后重建服务器版）；四入口命令压复制体（三问/四查/独立性复述删除，staging+装机版同步，-1/-2 随 split-run 冻结不动）；playbook 双写清理（EIP-7702 三写归一指向 casebook E-01、托管闸背景句、四测段 QUQ/SIREN 叙事压缩+判例指针）+4 处"整编 3.15.0 标疑"尾巴摘除（v6.2 审计已复审，使命完成）；research-workflows §三§五整节删（已收编 analyze-workflow A1，§四改号 §三）。
- **CHANGELOG 归档 9 条**（3.36.0×2–3.41.0 移入 archive，活跃窗口 75.7→33.5KB，含本条恰 10 版合规）。
- **仓库清理**：evals 三份验收记录（walkthrough+两份 PYTHIA 双跑对照）与 v6-migration-audit.md git rm（git 永存）；labels-eth.csv 21MB 过期备份、07-31 备份目录、scratch-3.19 草稿（proclock.py 头注断链同步修复）、.hypothesis、commands 四个 .bak 移入废纸篓。72MB preclean tar 在仓库外不随迁，删除另批。
- 明确不动：casebook/evals 题库/attic/split-run（首战前冻结）/analyze/collect-workflow/tiering 门槛表/死亡名单与静默出错坑/commands-staging/address-book 机制注释。codex 激进重构方案（report-template 41→15-20KB 等）列为 v6 转正后第二轮候选未采纳。
- 验收：run_all 14 项全 PASS；docs_lint 44 文档无断链；references 文本总量净减约 55KB（真减分析会话读入），robinhood 开局刚性读入 51KB→2.9KB 路由页+按需分册。

## [6.2.0] - 2026-07-31 — 经验存留审计第一批（未核实经验清出正文）

背景（用户决策，2026-07-31）：本机 40+ 案中仅少数币（EGL1/TROLL/KOGE/B/AB/QUQ/SIREN/OPN）经用户反复追问复核，多数案"扫两眼没再看"——其单案归纳的判断类经验真伪未经检验，留在正文会以"经验"之名污染判断且占上下文。用户拍板：判断层按"条"审计，**三判据（①机制解释②翻案/用户终裁背书③用户追问检验）全不占的删除**，"当没做过、不知道"；机械层（采集/脚本/数据源）40+ 案全保留不动。

- **候选运行权限收紧（retrospective 1b）**：废止"候选在分析执行时按正式规则对待"——改为**只当查证提示**（提示查哪路、比什么），不得作为任何结论/定性依据；新增存留审计条款（全不占→attic）；2b 整编条款 3 同步（不再等 8 个次版本，审计即分流）。
- **attic.md 存档制**：新建 `references/attic.md`（SKILL.md 深入阅读清单登记为**分析会话禁读**）——正文删除的条目全文存档于此，默认零上下文成本；恢复条件=第二案复现或机制补齐。git 历史为终审档案。
- **第一批快筛（48 处显式【候选】标记逐条过三判据）**：删 6 条入 attic（A-01 AKE 女巫化回收识别、A-02 SPX 镜像执行扫描法、A-03 BUILDon 余额档位双向判据、A-04 LPT 老基础设施币呈现范式〔TransferBond 硬内容在 data-pipeline-evm-sources 权威位保留〕、A-05 ASTEROID 世代阵营划分法、A-06 GOAT 同类前例结局对照法）；留 42 条（各有机制解释/翻案终裁/名单币追问背书，身份仍是候选、消费按新权限）。其中 2 条边缘保留供用户抽查：公共代买枢纽四特征裁决（ASTEROID，援引 CEX 热钱包同款机制族）、死币复活亚型分流（ASTEROID，预埋检验有账本必然性+§9a 盘型库结构配套）。断链清理：两处路由索引摘除"世代阵营法"字样。
- **惯犯库措辞整体降级（labels/README serial-actor 段+纪律 10、label_lookup.py、labels_resolver.py、accumulate_offenders.py、build_labels.py 共 8 处）**："历史分析实锤惯犯"→"历史案标记惯犯（案内定性、多数案源未经用户复核）"——库内 1741 址系双源自动回灌（未复核筛查案也进），定性是案内自评非用户终裁；命中消费统一降为**线索级**（优先深查+调案源判成色），报告引用禁用"实锤"措辞。机制面不动（不剔除不禁边、A5 延迟揭盲、设施冲突硬闸照旧）。
- 范围声明：本批只处理显式【候选】标记与惯犯库措辞。v3.0（2026-07-18）前入库的无标注存量规则须经全库普查（第二步，单独会话）才能识别与分流；address-book 行为学定性条目同留第二步。
- 守护测试 16/16 全过（docs_lint 曾抓 attic 漏登记，已补）；SKILL.md 9.4KB（<10KB 预算）；改动前备份 `~/.claude/skills/token-chip-analysis.bak_20260731_014144/`（10 文件）。

## [6.1.2] - 2026-07-30 — split-run 契约收紧（历史案 dry-run 产出）

计划步 3.5 执行记录：以 PYTHIA 案真实产物在 scratchpad 建 dry-run 目录（零采集零污染），走 handoff 九步全链路——generate READY（真实 accounting_mode 自动适配）→ 90MB 大文件 sha256-sparse 分片哈希（不全盘重哈希实证）→ verify PASS → receipt 盲化字段跟随环境 → freeze 前揭盲拒绝 exit 2 → freeze 真实 72KB 实体表 → 揭盲放行 → 哈希漂移检测 exit 2 → supersede 归档旧 manifest 后新 verify PASS＋receipts 断点可读。全部符合预期。

- **唯一收紧**：dry-run 暴露 v6 前旧案（无 supply_truth.json）也能出 READY——新流程 A0/A2 必产 accounting_mode/supply_truth，两件并入 REQUIRED_FOR_READY（缺任一 generate 即拒，fail-closed 补全）；split-run.md §2.2 状态机行同步；测试补反例 19→20 项。
- 服从性维度（GPT-5.6 对停止线/契约的遵守）不在管线 dry-run 覆盖内，按计划留步 4 首战检验（easy 小标的风险可控）。

## [6.1.1] - 2026-07-30 — camp_share_series schema 文档修正（codex 回灌）

- monitoring-package.md 两处：示例与约定行的 camp_share_series 由"逐日对象列表 `[{ts,阵营:值}]`"改为 `{"dates":[...],"series":{"阵营名":[...]}}`——figures_from_facts.py fig1 的实际输入契约从来是后者（main 侧 L98 报错文案可证），文档写法属笔误级漂移，codex 侧 c1.0.0 独立分享包实战撞出后修正，本次 v6 大同步前回灌。report-template"与 monitoring-package 同构"句自动随正。
- labels: miss-queue/eth.csv 回灌 codex 侧 BITCOIN 案 85 行候选（高度数节点+守门员 FUNNEL，2026-07-28），标签库 CC 真源约定。

## [6.1.0] - 2026-07-30 — 分段执行（split-run）落地：−1 机械段 / −2 判断段跨会话拆分

背景：用户提出把分析拆两个会话——机械段交便宜/额度充足模型，判断段交 Fable 5 同目录冷启动，防长上下文注意力稀释（主动机）＋省主力模型额度（次动机）。GPT-5.6 定为 −1 主轨的实证：codex 侧 `~/Documents/5.6筹码分析/` 十余案机械段战绩（KOGE 3.6 亿条逐 wei 对平、BULLA 五查 PASS、gate BLOCK 即停），其翻案史 REFUTED 全集中在判断层——凡出现在翻案史的环节全部划入 −1 停止线。计划经 codex @CX 复核吸收 20 项意见（entity_identity_gate 因依赖实体表移回 −2 系真 bug 修正；manifest 升级语义收据；sealed 防锚定密封；候选覆盖自检防锚定等），计划文件 plans/opus5-gpt5-6-1-1-fable5-2-fable5-fable5-splendid-shannon.md。

- **references/split-run.md（新建，唯一权威源）**：−1＝A0–A2 全部＋A3 机械子层（标注批量层只写 observed_type/conflict_flags、大户排查批量层跑满防候选海、聚类只出候选簇含拒绝边孤立点、identity_preflight 代正式 gate、序列命名禁"阵营"）；−2＝A3 判断层＋A4–A6（开工序八步：verify fail-closed→保鲜 >72h 弹警报停等用户绝不自动拉→候选覆盖自检→sealed 禁读令；冻结序列：临时实体→无下限成员扫描→反证→entity_freeze 物化→正式 gate）；停止线/盲化跨段（揭盲前置＝freeze 落盘）/断点 receipts/双轨 .stage1.lock 互斥/A4 外部异构路三条收紧（全新会话、不给 sealed、不复核自己 −1 产出）。适用范围 v1 仅新标的 easy/full。
- **scripts/report/handoff_manifest.py（新建）**：generate/verify/receipt/freeze 四子命令，schema `handoff/v1` 内嵌。generate＝语义收据（gate 状态自动从产物 JSON 读 verdict/exit_code 防手报、产物 allowlist 哈希（>64MB 分片）、sealed 只记哈希、data_map 索引即白名单、READY 缺必备件即拒、supersede 归档制）；verify＝fail-closed（缺件/哈希漂移/gate 语义漂移/schema 不兼容/状态非 READY/blocking 异常未解决/candidate_universe 空壳一律 exit 2）；freeze --check-unseal 把关揭盲。exit 语义对齐现有 gate（0/2/1）。测试 19 项进 run_all（SUITE 15→16）。
- **commands 六入口（四→六）**：token-analyze-1（模型自检提示不硬停/探针与锁/停止线/未档异常写 blocker 禁自创解法/完成即停）、token-analyze-2（档位必填/开工序八步写死）。staging 与 ~/.claude/commands 双处同步；旧四命令零改动＝回退路径。
- SKILL.md 四入口→六入口＋深入阅读补 split-run.md；context-discipline 刀 1 补第 6 条指针（分段＝两档制会话级形态，−2 会话内两档制不变）。
- 后续（计划 §四）：codex 侧 c2.0 迁移矩阵→v6 大同步→c2.1.0 −1 条文；冻结历史案 dry-run；首战试点合并验收（分段引入组 7 指标与 v6 骨架组分开归因）。
- 守护：run_all 16/16 PASS。

## [6.0.0] - 2026-07-30 — 架构级重构：薄骨架 + 判例库 + 评测题库（规则语义零变更）

背景：40+ 版追加式迭代后 SKILL.md 37KB 规则/履历混写、单条规则遵守率被上下文稀释；4 个 commands 漂移到两代前口径（"五问/P0P1"现行实证）；判定类教训散在按币组织的 memory 导致 IQ/LPT/PENGUIN/PYTHIA 四案托管误判同族复发；质量不可测量。三轮讨论＋codex @CX 外部复核后用户批准白纸重构（计划 skill-bright-storm，worktree rebuild/v6 隔离施工）。**v5 终版基线＝087ccec；规则语义零变更＋两项批准代码例外。**

- **新 SKILL.md（8,574B，≤10KB 硬指标）**：使命三问＋铁律 7 条一行断言制（封顶：新进＝旧出或代码化）＋阶段路由表（必读/硬闸 exit/产物）＋四入口一行路由＋上下文预算；细节全部下沉。frontmatter description 原样保留。
- **references/analyze-workflow.md（新建）**：完整版 A0–A6 唯一权威源，承接旧 SKILL.md 全部阶段细节；迁移三动作＝剥履历（留一行来源）、剥已代码化复述（gate 段→调用+exit 语义）、判定叙事改指 casebook。
- **references/context-discipline.md（新建）**：成本三刀 13 条＋断点恢复五步原文重组，定位从"省钱"改为"质量机制"（干净上下文＝复核有效性）；外包两档制唯一权威源随迁。
- **references/casebook/ 判例库（新建，例外②守护）**：按判定环节组织（不按币——四案复发的结构性根治），六字段结构（ID+成熟度/触发现象/禁止推断/必做区分检验/证据不足时/权威与出处）；首批 3 册 12 条全部来自已终裁翻案：cex-custody 5 条（Alpha 库存仓/ATA 常数反例/Upbit 跨链/Bitvavo 质押产品/Squads escrow）、entity-clustering 3 条（EIP-7702+通用实现/设施先验三测/循环论证）、supply-accounting 4 条（静默改账/镜像恒等式/分母恒等/历史清零层全盲——S-04 为验收期用户挑错补录，PYTHIA W1 案）。A3 实体冻结前全册过闸、A4 作备择解释弹药。单册 ≤25KB/25 条超限先合并。
- **evals/ 评测题库（新建，references 外防污染）**：9 题＝历史确证翻案（PYTHIA 9Z/TROLL ATA/IQ Upbit/IQ 7702/QUQ 设施/GNT 静默迁移/GMX 镜像/IQ 分母/PYTHIA W1 漏检——第 9 题为验收期用户挑错补录），每题 A 节执行输入（零泄漏可投喂）＋B 节考官侧（当年确证错误/唯一失败原因/禁止输出/必做证据动作/缺证据结论上限/预期拦截点）。评测哲学：历史结论不可当金标准，唯一标尺＝被翻过案的错误确定是错的；验收只验拦住旧错误。
- **供给真值闸（例外①）**：`scripts/lib/supply_truth_gate.py`——重放净供给 vs 链上 totalSupply（EVM eth_call/Solana getTokenSupply），fail-closed exit 0/2/1；治 GNT 型静默改账盲区（重放虚高 10 倍全自检 PASS，2026-07-28 实测，机制成立直接转正）。挂载 A2 第 3 查/easy E2/update U2.4；离线契约测试 11 项进 run_all。
- **casebook_lint（例外②）**：ID 唯一/六字段/成熟度标记/README 登记/单册上限，fail-closed（0 册 0 条不算过），进 run_all（SUITE 13→15 项）。
- **commands-staging/ 四入口重写（merge 后安装）**：入口只做三件事（声明标的/指向 workflow/列用户拍板硬性）；token-analyze 从"五问/官推/JSON 附录"废止口径对齐三问；collect-data 操作细节全量迁入新建 `references/collect-workflow.md`（原细节只活在 git 外命令文件＝权威源不受保护的实证）。
- **retrospective.md 增补**：2c 教训分流决策树（gate→casebook→pipeline/environment→workflow/checklist→SKILL.md 最后手段；元规则推广到一切达标教训）＋整编触发线 2 条（SKILL.md>10KB/casebook 单册超限）＋翻案默认登记 evals 候选题。
- **坑表 18 条逐条分流**（汇总表不再保留）：environment 已有 5＋本次补 1（sleep/until）、pipeline 已有 2（Etherscan/DuckDB）、casebook 5、analyze-workflow 内嵌 5——分流表见 v6-migration-audit.md §二。
- **冻结-核销双向审计**：`v6-migration-audit.md`——正向（旧义务→新位置）/反向（新义务→旧来源或例外）/gate exit 逐字比对；存疑清单逐项验证后清零，两条语义微增透明申报（A3.6 恒等自检＝IQ 教训收编、历史清零层＝v4.2 复核义务前移）。
- 守护：run_all 15/15 PASS（含新增两测试）；docs_lint 40 文档零断链。

## [5.0.0] - 2026-07-30 — 框架级用户修订：三问框架 / 去分级 / 狙击集团标签废止 / 大户排查前置双闸

背景：用户 2026-07-30 对分析框架一次性修订七条＋大户线调整（全部用户拍板，非复盘迭代）。主版本号 +1（架构级：固定命题与标签体系双变更）。

**框架变更（权威源 tiering §6a / report-template / SKILL.md 三处已同步）：**
1. **四问 → 三问**：问 4 项目方背景调查整体删除（创始人黑历史/社媒运营/大V/水军整路退役；research-workflows §1 原路线 5 删除、官推回收账号侦测段删除）；解锁日程情报（原路线 1）保留服务问 3 的 vesting 小节；路线 2/3/4/6 降为按需分析工具。TL;DR 开放条款改"第 4 条特有发现"。报告章节：原第六章删除，状态评估/局限性前移为六/七章。
2. **取消 P0/P1 重要度分级**：标签表删"重要度"列；TL;DR 问 1 按标签逐项计数（实锤/高度疑似仍分开）；第三章按标签顺序呈现（项目方→大庄→小庄→离场庄→刷量）。
3. **"狙击集团"标签废止**：发射窗协同实体按普通门槛判入大庄/小庄/离场庄，不再单独打标签/单独分析；识别与合并方法全保留（bundle 三件套/拍卖型资金硬边/流量存量双口径改挂"发射窗/bundle 分析"）；同秒/同块全景纪律、行为 cohort P1 实体化门槛（QUQ 案 GPT5.6 条款）两条随体系删除。阵营表删该阵营；旧 state 该标签按 update 标准迁移条款重判。
4. **其他大户排查前置双闸（取代"不单独分析、不逐个溯源"）**：门槛 1%/2% → **0.1% 总供应 / 0.2% 流通**（上所标的市值体量下旧线是几十万美元级盲区，分仓单址常压 0.3–0.5% 档躲线）；闸一=每个其他大户过完批量排查层（标签库+惯犯库+指纹扫描+funder 批量溯源）才准定性归阵营，报警者才人工深挖；闸二=每个已识别实体做不设持仓下限的成员完整性扫描（防分仓漏判的正确方向是从庄向外挖）。排查记录落盘、阴性小节报覆盖数。
5. **流转路径图对象收窄**：原"每个 P0 必配"→ **当前持仓 ≥20% 总供应或 ≥20% 流通的大庄/项目方**（低于线的项目方不强制）；图 2 删"P0 逐个单线/P1 可合并"规则，改"标签实体各一线、超 8 条可合并较小实体并图注注明"。
6. **素材装配外包对象**＝流转图门槛实体（research-workflows §二b 同步）。

**机器件与脚本（全部向后兼容旧产物）：** analysis-state/appendix schema 的 whale_groups.tier 字段废止（新文件不写，读取端忽略旧值）；camp_share_series 删"狙击集团"键（旧序列重绘走 legacy 兼容色）；standard_charts CAMP_ORDER/CAMP_COLORS 该键降为旧体系兼容键；cluster_sensitivity 判级改 label 前缀制（大庄/小庄/未达标，CLI 参数 --big-pct/--small-pct/--small-circ-pct 取代 --p0-pct/--p1-pct/--p1-circ-pct，旧 tier state 仍可读）；holdout_diff 判级从 label 前缀推导；analyze_inc 四态表去 tier 透传；lifecycle_flow/facts_gate/camp_series_inc docstring 同步；test_cluster_quality/test_report_facts/test_figures_from_facts fixture 同步。守护测试 9/9 PASS、docs_lint PASS。

成本指标：纯文档/脚本修订会话，无采集；轮次约 40。质量指标：不适用（非分析案）。

## [4.2.0] - 2026-07-30 — TROLL(Solana) 完整版复盘 + PYTHIA 复盘补遗

背景：TROLL 07-29 Fable5 从零独立重做（揭盲式，不读 07-28 会话结论文件）交付完整版；与 PYTHIA 双报告交叉核实同期构成一对镜像案——PYTHIA 把币安 Alpha 托管仓判成小庄（4.1.0 已治），TROLL 中期把私人四钱包组判成"Coinbase 托管体系"（方向相反同罪），本版补上反向的闸。

**方法类（转正，机制解释明确）：**
1. **托管判定反向闸**（playbook-entity-cluster-methods 托管判据段）：判"托管"与判"庄家"同样要硬证据——TROLL 中期三条"托管判据"逐条入册为反例：**0.002246 SOL 到账额=Solana 建 ATA 物理常数**（免租金 2,039,280+fee 206,500 lamports，对照组散户提币完全同值，零区分力）；"托管仓只囤不动"是行为假设不是证据；中间判定标签不作证据。判托管正证据清单（标签库/Vybe 链根/PoR/gas supplier 体系/批次伪影+集齐率）+ **跨所作业一票排除**（币安 gas 养 Coinbase 提币仓≠任何单所托管）。同步进 entity_identity_gate docstring（BIG_UNLABELED resolution 纪律）。
2. **Solana 1-raw 级粉尘投毒**（投毒段第三场景）：非零值 dust（1 raw~0.1 枚）使 `value>0` 过滤失效，污染 last_ts/共现统计造伪实体指纹（TROLL 39,705 条边、"2026-05 群同分钟共现"被证伪为投毒伪像）——活动性/共现统计过滤收紧为 `amount≤1 raw` 剔除。
3. **时点净库存差 ≠ 累计流出**（playbook-supply-recon §2）："缺口期净差仅 8.54% 藏不下达标实体"被推翻——期间换手可任意多轮，正解=回补数据（curve ATA postTokenBalances 直读）或如实声明不可排除。
4. **截断地址禁补全升为全链硬规则**（§6 硬规则；FIL+TROLL 两案、TROLL 主分析与复核 agent 同案双踩）；**中间判定产物不作标签源**（§3：cex_map.json 类派生文件里的判定条目≠标签，跨会话只信主库+address-book）。
5. **揭盲式独立重做流程转正（两案）**（playbook-evidence-wording §10）：盲做（复用数据不读结论）→揭盲（只给分歧位置）→分歧点链上硬证据定向裁决——PYTHIA 两版各对一半、TROLL 重做反向犯错被揭盲复核钉死，独立重做的价值在"两版错误不相关，分歧点即高危区坐标"。
6. **极值清单第三维：日内瞬时峰值**（research-workflows 完整性批评）：日末口径对"当日买卖回"整体失明（TROLL 内盘 7 轮做量脉冲峰值和最高 113.7%/日，日末恒零）——与 4.1.0"全期 max 仓位重放"构成日级+日内双层口径盲区检查。

**方法类（候选·单案，playbook-entity-cluster-methods 手法库）：** 高换手日峰值和重复计算陷阱（累计买入≫峰值=换手指纹，峰值和 252% 不等于 N 个囤仓实体）；LP 费复投仓识别（四池同刻领费归集零卖出=隐身大额 LP 的唯一暴露面）；整额自转倒仓链=反追踪指纹（净额账本不可见，逐边流水定位压盘方）；按美元面额开票=场外交割指纹（PYTHIA 补遗：枚数各异美元档窄聚 ±2%+测试笔，裁决"自我分仓 vs 对外交割"）。

**数据工程类（正式）：**
7. **SQD「同 slot 同额多笔去重丢边」系统性缺陷**（capture.md §13b 新子节）：边无 sig 字段，同 slot 同两方同金额多笔只剩一条（TROLL 真值账本逐 slot 对表实锤：不一致 slot 主边集恰=真值一半；对账 |diff| 8.127% 供应的主因）。与 GOAT gap 合并坑成对偶（dedup 既是解药也是毒药）。检测指纹（差异正负成对+集中高频地址）+修复 SOP（差异地址 ATA 全史 decode 替换式合并，锚点 1760/1760 验证）入册；丢失层定位（服务端 or 本地 set()）列 Known Gaps。
8. **pump.fun 长内盘期全量重建=签名史双索引法**（capture.md 新 §15）：curve PDA 签名史∪mint 签名史 decode+差异地址 ATA 迭代补边（2 轮收敛），比 SQD 扫 8 千万 slot 快两个量级、decode 零失败；配套：大空洞单 worker 最快（并发单位=空洞段）、高频 ATA 翻页 CAP、ATA PDA 纯 Python 推导。
9. **RugCheck detectedAt=索引器首见≠发射时间**（scan.md）：TROLL 差 145 天，据此定发射窗漏掉整段早期史——发射时点唯一正解=curve/mint ATA 最早签名核实到秒。
10. decode_txs_v2 urllib 对 Helius sock_connect 挂死坑（capture.md §13c）：http.client keep-alive 绕行（TROLL 存档待二案收编），根治=lib/net.py。

**脚本：** `scripts/solana/squads_members.py` 新收编（Squads v4 multisig borsh 手解，成员/阈值/跨仓共享密钥矩阵——identity_gate PDA_UNRESOLVED 的标准 resolution 工具；PYTHIA 单案成熟度已标注）；`scan_token_accounts.py` --program 默认改 **auto**（getAccountInfo 判 mint owner，根治"token2022 默认对标准 SPL 币空扫"）+ 零账户对账 FATAL exit 2（防"合法空 result"当无持有人）；retrospective.md/entity_identity_gate.py 的"v4.2"版本号笔误统一为 v4.1.0。

成本指标（TROLL 重做会话，文件时间戳口径）：07-28 23:12 开工 → 07-29 17:49 交付，墙钟 ≈18.6h（含夜间采集挂机与 1,079 万边修复重放）；轮次/Bash 数未采（复盘于独立会话执行）。
质量指标（TROLL）：初稿关键结论 8 条（TL;DR 五问+三件事）；复核判定 CONFIRMED 5 / WEAKENED 7 / REFUTED 2（4 内部+codex 外部 5 条全同向零新增推翻）；复核翻出漏检实体/观察组 4（毕业日幸存仓 0.58%、同人对 B 换仓源头前推、压盘真身四跳倒仓链、LP 费复投仓 1.18%）；传播级数字错误：终版 0（中期稿 3 处大翻案——发射时点/缺口期上限/托管 20.19%→6.13%——均在揭盲定向复核阶段修正，未出交付门）。

## [4.1.0] - 2026-07-30 — PYTHIA 双报告交叉核实复盘：实体身份防复发三闸 + 复盘元规则

背景：同族错误第四次复发实锤——IQ（Upbit 托管 58.5% 判大庄）、LPT（Bitvavo 质押判巨鲸）、PENGUIN（Alpha 库存仓判别法只入 easy 未入完整版）三案教训全是文字形态，未能阻止 PYTHIA 案把地址簿里已登记的币安 Alpha 库存仓 9ZPsR… 判成"小庄#1"、40 个 Squads 多签仓判成"个人空壳冷储"、W1 波次 341 址峰值 63.44% 整体漏检（跟踪集按现仓筛的盲区）。用户令给出"最可靠的保证"——答案=全部变机械闸。

1. **label_lookup 并源 address-book.md**（labels_resolver v4.2）：`references/address-book.md` 手工核验层永久并入解析器数据源（markdown 表格解析、按链形态过滤、section→category 映射、CSV 主库同址覆盖）——"跑过 label_lookup"从此等价于"查过地址簿"，消除"一个步骤两个数据源、工具只盖其一"的结构漏洞。9Z 实测一查即中。
2. **entity_identity_gate.py + build_html G8 编译门**：实体表冻结前强制身份四查（标签双源/ed25519 曲线判定/托管假设），INFRA_IN_ENTITY / PDA_UNRESOLVED / BIG_UNLABELED 三类 flag 逐条填 resolution 才可过闸；G8 在 `--state` 时自动校验（缺 gate / 地址未全入闸 / flag 未解决均 WARN 拒交付；历史重编译 `--skip-identity-gate` 显式跳过留痕）。PYTHIA 回测：9Z 触发 INFRA_IN_ENTITY 红线、40 个 escrow 仓全部触发 PDA_UNRESOLVED——三案错误全部会被本闸拦截。test_build_html 补 G8 四条契约（共八条）。
3. **复核 prompt 翻案四问固化**（adversarial-review.js）：怀疑者必查①交易所托管/质押产品②off-curve PDA③托管指纹组④历史清零层；完整性批评加"全期 max 仓位重放"漏检自查（W1 模式检测）。
4. **SKILL.md 阶段 3 补身份闸硬步骤**（修复 PENGUIN 教训只入 easy 的流程不对称）；**retrospective.md 立元规则**：实体身份类教训必须以代码/门禁 diff 收尾，纯文字不算闭环（判断口诀："下一个会话不读这段文字，错误还会发生吗？会，就必须上闸"）。
5. 新脚本：`scripts/report/entity_identity_gate.py`（生成+校验双模式，ed25519 判定内置零依赖）。备份：labels_resolver.py.bak_20260730_pregate、build_html.py.bak_20260730_g8。

质量指标（本次交叉核实）：核实分歧点 4 组全裁决（9Z 归属/多签仓定性/静置盘/W1+美元开票）；新增链上铁证 3 项（15/15 多签共享托管密钥 2FLpNeST、11 仓 4.73% 原数退回 H9、W1→Q1 7.85% 资金承接）；两报告各对一半的终裁与终版报告已交付。

## [4.0.0] - 2026-07-28 — 大整编（用户点名）：40 余版增量迭代的结构清理——消重、一致性、归档；只减不加，规则语义未动

用户点名升 4.0 的专项整编会话（非分析复盘；主版本号为用户指定，工作流骨架未变更）。目标=减少重复表述、消除前后不一致、恢复条理。**①路由索引全面补齐（索引与正文脱节 9 节，40 版追加式迭代的典型漂移）**：analysis-playbook.md 路由表补 supply-recon §1b（多链分母判据）/§8b（嵌套质押穿透）、entity-cluster §6.5（节拍指纹）/§6.6（否证检验）、state-anomaly §13（回购链识别）/§14（净持仓曲线陷阱）；playbook-entity-cluster.md 子路由补 §6.5/§6.6；data-pipeline-evm.md 补 recon §13（时间抽查第二源）；data-pipeline-solana.md 补 capture §14（日级余额快照重建）；SKILL.md 深入阅读行同步；各路由页加"新增章节必须同步回填本表"义务行。**②结构错位归位 3 处**：methods 的"6.5.1 秩相关修正"（自称"本节最重要的一条"却被塞在 §6.6 B 小节之后）移回 §6.5 内成"秩相关修正"小节；state-anomaly 的"观察窗起点选择偏差"（减持归因主题）从 §9d（名人互动叙事开关）名下移入 §7"行为归因纪律"块；tiering 末尾孤悬的"资金通道一票否决判据"bullet 升为 §6a 正式子小节。**③消重与权威源制（同一规则多处全文重复→保一处权威源、余处缩为引用；合并自——两档模型制：SKILL.md 刀 1×research-workflows 模型选择段×update-workflow U6×easy E3 四处，权威源=刀 1，"3.39.1 误记当日勘误"历史包袱三处全清、只留净规则；措辞对照表：evidence-wording §11×report-template 两张表重叠 3 行，§11 为唯一权威源、report-template 改"报告格式对照表"只留呈现层专属行；P0/P1 门槛表：tiering §6a 为唯一权威源，SKILL.md 阶段 3 与 report-template 表标注速查副本+三处同步义务；外部异构怀疑者：research-workflows §2 为权威源，SKILL.md 阶段 4 压缩为主干+指向；监控包 v3.2 按需化：SKILL.md 开头段压缩，执行细节归 report-template+monitoring-package；地址转录纪律：evidence-wording §10 条 10 的八犯史长文压缩为纪律本体+一行犯例索引（细节 CHANGELOG 可考古））**。**④CHANGELOG 结构重整**：9 条只存在于"版本索引区长文"的版本（3.41.0/3.40.0/3.39.2/3.39.1/3.39.0/3.38.0/3.37.0/3.36.0-EGL1/3.29.0，近期记法漂移所致）转为标准正文条目；**3.36.0 撞号 ×2 首次入"已知版本事故存档"并加 changelog_lint 白名单**（EVM 五币 E0b 批量 × EGL1 复盘，2026-07-26 并行会话，此前未记录）；索引区恢复一行一版；归档滚动 3.12.0–3.35.1 共 29 条入 archive（活跃窗口回到约定的 ~10 版）。**⑤一致性理顺**：铁律 5"免费数据源优先"改"已登记通道直接用（含付费额度内 HyperSync Starter）+新增免费优先"（消除与主力付费通道的表面矛盾，纪律实质未变）；六个 playbook 分册头部的"零改写迁移"拆分历史声明统一为简洁分册说明；report-template/update/easy 头部历史叙事压缩。**⑥整编纪律执行说明**：全程只减不加、无新规则；候选条目（含 3.15.0 标疑各条）本次不做转正/降档裁决（留给下次分析复盘按两案标准处理）；git diff 逐条可追溯。改动文件：SKILL.md、CHANGELOG.md、CHANGELOG-archive.md、scripts/tests/changelog_lint.py（白名单）、references/ 下 analysis-playbook / playbook-entity-cluster 及其三分册 / playbook-supply-recon / playbook-state-anomaly / playbook-evidence-wording / report-template / research-workflows / update-workflow / easy-workflow / data-pipeline-evm / data-pipeline-solana。成本指标：整编专项会话，轮次约 60、Bash 约 25、零采集零付费额度。质量指标：修复索引漂移 9 节、结构错位 3 处、消重 6 组、CHANGELOG 记法漂移 9 条+撞号入档 1 组
