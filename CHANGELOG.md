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

- **6.8.1** 2026-08-01 codex 独立验收判"不通过"后全面返工（用户批准 P0 全修＋P1 全修＋P2 小件；codex 7 P0/8 P1/3 P2 逐项对照修复，14 项认账、1 项〔freeze 不跑 verify〕系 6.5.0 既有缺口一并还账）：①**溯源 pro-rata 数学错误根治**——entity_source_trace 全文重写为祖先子图正向模拟（逆向 BFS 到 mint/标签/设施终点 → 子图边按 ts＋同秒组内拓扑序逐笔重演，账户流入转移入账/流出等比扣减；codex 反例"收100→出90→再收90"现算对 10/90，v1 会给 52.6/47.4——错因＝比例守恒只在单次流出瞬间成立，v1 把它外推到了全史），schema 升 provenance-ledger/v2（**v1 数字全部作废禁止引用**）、回环天然良定义（same_slot_scc 概念废除，同秒环组计数诚实标注）、closure 构造性守恒降为实现自检；FIFO/LIFO 真上下界同骨架落地，任一锚点主导条目翻转 → exit 2 阻断＋freeze 独立复查；direct_upstream 进货单定稿**毛流入清单口径**（v6.8.1 回测首跑实测教训：周转枢纽的现存库存构成把早期藤蔓等比消耗殆尽——Q1 峰值现存构成 EwUU 100%、W1 藤全部不可见，而 W1 教训的本义是"从谁进过货"这个事实本身）；缓存 KeyError 潜伏崩溃随重写消失；entity/labels 输入类型硬检查（跨实体重复即拒）。②**freeze 升四重内容级前置**：同进程严格 verify（manifest 缺失/BLOCKED/哈希漂移/legacy 一律拒）＋裁决 validate 强制传实体名册＋溯源台账内容级重查（schema=v2＋实体集双向一致＋逐实体 members_sha256＋closure 按 composition 明细重算＋敏感性 stable——**自报值一概不作数**）＋三份哈希入冻结记录；verify 独立重算 READY 必备件与 AUTO_GATES（手改 manifest 摘条目同拒）；legacy-read-only 落机器 receipt（legacy-readonly-receipt/v1）。③**裁决八类拒绝**：新增 verdict 语义交叉约束（confirmed 必须 accepted 非空＋evidence 非空——"确认了协同却全员排除"的矛盾裁决拒；excluded/unresolved 不得收编成员；excluded 逐员必填 reason）＋linked_entity 名册绑定（不在名册/accepted 未真并入全拒，无名册时有 confirmed 即拒）＋源报告 schema 错版/重复候选 ID/candidate_kind/adjudicated_at/nearest_tier_line 全查。④wave_scan：D 指纹改**全事件滑窗**（按收方首收去重会吞掉二轮复收——同批收方分两轮收同面额第二轮全盲，与"任意 7 日窗 ≥N 不同收方"定义不等价）＋top_sender 定稿触达 distinct 收方口径（按事件数会被"对同一收方反复发"绑架——3e11 组实测出度 1 假信号教训）＋负余额升历史最低点口径（"先负后回正"数据缺失自愈假象不再漏，PYTHIA 实抓 1 址 1.2e-6% 粉尘级）。⑤flow：实体抵消按 entity_id 分组（拍平成单一集合会把实体间真实转账当内部边误删）。⑥**测试大翻新**：把给漏洞背书的空壳 provenance 正例全部翻成必拒反例（v1 schema 拒/空 composition 拒/closure 自报造假拒/成员哈希错配拒/实体集不一致拒/敏感性不稳拒/BLOCKED freeze 拒），五测试 45＋27＋23＋16＋13 项全绿；新增 fixtures_lint.py（锚点文件结构入 run_all 守护，D 锚点补 recipients；SUITE 23→24 项）。⑦**PYTHIA 回测**：W1 波次全字段/D 组 7 个 ID/flow 25 sink＋20 spray ID 与 v6.8.0 逐位零漂移；溯源 v2 新基线＝Q1 进货单 20 上家 9 藤（占毛流入 9.43%）＋3yMk 11 上家 10 藤（33.25%）＋EwUU 66.7533% path=1 停靠＋敏感性三策略稳定；Q1 祖先子图 393 万边超 3M 默认预算 fail-closed 正确拒绝（--edge-budget 5M 重跑）。⑧文档：scan-schemas 升"完整字段登记"制（未登记字段不得输出）＋输入唯一性措辞对齐（采集端 four-check 保证，闸内不去重的理由成文）＋split-run handoff/v1 残留清除与 READY 必备件列全＋SKILL"②③"编号勘误为"①③"＋S-04 判例 v6.8.1 段＋docs_lint 守卫 7 升 v6.8.1 关键词矩阵；元规则补一层：**装闸后要请闸外的人试着绕它**——自己造的 fixture 天然顺着自己的实现走，绕闸测试必须由独立视角出（本轮 codex 验收即实证）
- **6.8.0** 2026-08-01 W1 漏检根治·三道互补防线（用户四轮拍板＋@CX codex 三轮复核；迭代计划文件称"v6.7.0"、版本号因当日双闸落地已占 6.7.0 顺延）：数据验尸推翻复盘文档两处事实错误（"无藤可摸"错——Q1 的 20 上家 9 藤/3yMk 的 11 上家 10 藤裸露；"单址峰值 0.05~0.3%"错——实测最大 2.92%、≥1% 有 5 址，真因是 341 址从未进任何判据输入集）。①wave_scan 升 v2：扫描对象改全体历史峰值 ≥0.02%（不限清零层、三桶留存标签）、A 种子窗两层（7 日窗 ≥20 员且合并峰 ≥10% 触发才生长）、C 改峰→30% ≤30 日、D 四条合一（同面额＋单笔 ≥0.001%＋7 日窗 ≥20 收方＋组合计 ≥1%，阈值曲线 1014→478→9→2 组实测定稿）、first_meaningful 抗 dust、负余额升 exit 2、零截断、纯流出地址 JOIN 静默丢弃 bug 修复；②新建 flow_anomaly_scan.py：汇集点（滑窗须同窗双达标——Q1 金额最大窗 4 来源被拒而 14 源/18.8% 双达标窗存在的实现 bug 教训）＋分发点双模式（脉冲滑窗/慢速批发全史——H9 三派发器匀速出货滑窗天然不适配的回测校准）；③新建 entity_source_trace.py 溯源闸：两锚点库存构成（不对毛流入归一化）＋direct_upstream 进货单义务＋终点三类（可证来源/边界带证据等级/未决五种显式记账）＋支路级停止＋pro-rata 主法；④新建 adjudication_validator.py 裁决闭环（template 起草/validate 六类拒绝）接入 freeze 三重机器前置（裁决＋溯源在场闭合＋成员表哈希）；handoff 升 v2（flow 报告进 READY 必产件、旧案仅 --legacy-read-only 显式降级）；camp_jump_audit.py 删除＋**覆盖真空声明（用户确认接受）**：系统不再有"从最终阵营序列反向发现未解释大变化"的输出侧报警器，wave/flow 覆盖不了标签重分类/分母变化/慢速迁移类异常，本轮不做替代闸（不承诺永久）。PYTHIA 原案回测全绿（W1 候选 339/341＋种子窗 158 员/37.06%＋escrow 网 43 仓独立重发现＋D 恰 7 组 44 分仓置顶 33.66%＋Q1 sink 19.85%/12 源＋三派发器慢速模式全中＋Q1 进货单 9 藤/3yMk 十藤现形/EwUU8oi 支路停）；回测仅 PYTHIA（用户拍板），flow 参数缺第二币对照校准如实记录。新分册 scan-schemas.md（四 schema 冻结）；fixtures/pythia_anchors.json 锚点权威档；测试 +59 断言（wave 19/flow 13/trace 13/validator 14）＋handoff 30 项；docs_lint 守卫 7 升三防线版；B 指纹与 cohort_hint/score 保持 v6.6.1 原样（用户撤销删除）
- **6.7.0** 2026-08-01 双闸落地（用户批准两方案＋@CX codex 复核融合）：①A2 时间抽查第二源分层制——新建 time_spotcheck.py（balance 型 archive balanceOf 直查＋tx 型收据五元组，两型都查；EVM 案进 READY 必备件＋AUTO_GATES），全史 SQD 重拉降为例外动作（触发三条件＋pilot 报 ETA；APU 案 103 分钟冗余教训）；②A4→A5 顺序硬闸——新建 a4_gate.py（claims 注册表全覆盖裁决＋终版文件哈希封口＋charts/final 空检查），build_html 加 G9（封口哈希重验＋报告图必须全在 charts/final/；--skip-a4-gate-reason 带理由跳过留痕）＋WARN 不再先落盘（gate 前置原子写）；历史核查 16 案 12 案倒置 7 案返工是本闸依据。测试 +25 项（a4_gate 18＋spotcheck 5＋handoff 2）；原事故回测用户裁定免做、待实战验收
- **6.6.0** 2026-08-01 W1 波次二次漏检复盘落地：历史清零层波次扫描机械闸（用户批准迭代清单 9 项全落地）——新建 wave_scan.py 四指纹扫描器（同窗建仓聚类×喂币专属度×集中清仓窗×等额面额，合并口径；PYTHIA 回测 W1 覆盖 339/341=99.4%＋44 分仓等额组置顶命中，QUQ 1.03 亿边独立重发现库存层/接力交棒）＋camp_jump_audit.py 骤变归因义务＋wave_scan_report.json 进 READY 必产件（契约测试 21→23 项）＋SKILL 双硬闸升三硬闸＋A3.6 硬步骤＋split-run 三处＋S-04 复发记录＋retrospective 元规则第二条"装闸必附原案回测"＋adversarial-review L50/L71 单址阈值 bug 修复＋evals 09 升机械闸回测题＋docs_lint 守卫 7
- **6.5.0** 2026-07-31 codex 独有资产审计后回灌转正（@CX 交叉复核 + 用户三项拍板）：经济控制账与静置仓反扫双硬闸候选转正式（SKILL 新增"实体冻结前双硬闸"节、report-template 三账段【候选】转正＋checklist 收编 4c/4d）+ 收编 codex 侧方法学：economic-control-accounting/lp-fee-accounting/independent-audit-protocol 三分册（协议限定"复核既有报告"作用域、0.5% 线修订为 0.1%/0.2% 双线）+ audit_release_gate 四处修复（WARN 不再当 PASS、补 supply_truth 四查、双线阈值、空账本与嵌套未决暴露阻断）与九类契约测试 + tiering 判级确权边界节/methods 静置仓硬闸版与枢纽两段法/evidence-wording 受益权分离与 LP 四分法等禁写措辞/sources 价格覆盖审计与 Blockscout 完备性/channels LP 增强版 + docs_lint 四层守卫（硬闸关键词跨 SKILL/methods/tiering/report-template 缺一即 FAIL）+ description 补"复核既有报告/LP 手续费"触发词；SUITE 16→17 项
- **6.4.4** 2026-07-31 attic 首批复核裁决落地（用户逐条人工复核）：A-01 社区分发桶女巫化回收识别、A-02 镜像执行扫描法恢复 methods 正文（保留候选身份＋用户复核授权戳），A-03～A-06 维持存档
- **6.4.3** 2026-07-31 变更叙事全库清理（用户人工复核发现＋@CX 双路扫描，三分类口径用户拍板）：一类·纯变更叙事约 45 处清除（"取代旧条款/vX 曾取代/已废止/原条款/历史沿革/拆册搬家史/labels 拆分史/取代 v1"等，机制依据与授权戳保留）+ 二类·狙击集团废止段瘦身归位（tiering 收缩为现行规则+update-workflow 指针，阵营 legacy 行删除）+ 顺修 solana-scan 头部删字残渣与 tiering 粘连行 + 新整编规则入 retrospective 2b（变更叙事进 CHANGELOG、正文只留现行规则+依据、迁移桥唯一归宿 update-workflow）；codex 建议中 6 处活兼容规则（report-template/monitoring/analyze-workflow 的旧文件读取端行为）经裁决保留不搬
- **6.4.2** 2026-07-31 SKILL.md 手工瘦身后 @CX 全库一致性修复（codex 通读 47 文档出 15 项、逐条核裁后用户拍板全修）：残损 2（铁律 1 残字/铁律 7 悬空分号）+ **"零外部代币名"红线全链废止**（用户裁定铁律 1 本意=结论不复用，不禁提代币名；6 文档清理 + build_html cashtag WARN→NOTE 不再拦交付）+ 存量漂移 7（六条铁律、split-run A4–A6、supply-recon 对齐四查、HIGH tag 措辞、"查3"编号、整编触发器、E6 引 E5）+ 低危 4（判级数值副本收归 tiering、casebook C-01/C-05 指针、§7.5 免 key 路线补合同边界、5 处粘连行拆分）
- **6.4.1** 2026-07-31 惯犯库回灌随复盘（6.4.0 挂账项用户裁决落地）：accumulate_offenders --apply 从 E5/checklist 15 交付后固定动作改挂 retrospective 步骤 3——结论未经用户复核不入惯犯库，不复盘不回灌；4 文档同步，脚本与冲突检测机制零变更
- **6.4.0** 2026-07-31 复盘触发机制改制（用户拍板）：A6/E6/U6 复盘从工作流固定末步改为**仅用户明确要求时执行**——分析会话交付即收工，候选教训随手记案目录 retro_notes.md 不动 skill 文件，用户复核确认结论后下令复盘再走 retrospective.md 入库；split-run sealed 自查申报改挂 −2 交付；9 文件 21 处＋命令三份双处同步
- **6.3.1** 2026-07-31 搬迁前全量一致性修复（@CX 交叉审查产出，用户批准 19 项全修）：高危 5（evm-recon 峰值预筛旧 1% 线→现行 0.1%/0.2%、阵营键全集收归 CAMP_ORDER 唯一权威、惯犯库"实锤"残留降级、solana 脚本资产声明整修+README 补登 v2 主线 5 脚本、/token-analyze-1 补 easy|full 档位）+ 中低 14（三查→四查残留 4 处、"SKILL.md 阶段 N"死指针 6 处、铁律 1 两例外成文划界、docs_lint --all 全量模式等）；3 项 Linux 迁移项按用户裁决不修（目标改 Mac mini 云）
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

## [6.7.0] - 2026-08-01 — 双闸落地：时间抽查第二源分层制 + A4→A5 顺序硬闸

背景：用户两问触发核查（本条目即答案存档）。**问 1**：双源比对是否强制？——核查结论：A2 时间抽查（锚点级第二源核对）是强制的，但"全史第二源重采"从来不是任何文件的明文要求。APU(ETH) 案 −1 段照抄 evm-recon §13 的 GMX 全史区间示范命令，SQD 重拉 91.7 万行/244MB——ETH 实测 169 行/s（Arbitrum 的 1/15），103 分钟仍未拉全（sqd_full_coverage=false），而 Alchemy archive balanceOf 锚点直查早已 15/15 PASS 闭环，A3 机械层干完后纯等 SQD 空转 76 分钟；`dual_source_crosscheck` 不在 CHANGELOG/split-run 契约/handoff 收据任何一处＝执行者临场按模板自发加码。**问 2**：A4 完成前提前做 A5 是否浪费？——历史核查 16 个时间戳可判定案：12 案图表/报告先于复核落盘，其中 7 案因翻案实际返工（APU 报告写 3 遍＋4 图重画＋2 图作废；GOAT 阵营图 4 代＋easy 版回炉；PYTHIA/EGL1/IQ/TROLL/KOGE 各有重画作废明细），另 5 案（QUQ/VEX/TRASH/AKE/GMX）结论翻了图没跟着改成错误残留；retrospective/attic 中"返工/重画/白做"零命中——七次返工从未沉淀成规则。制度根源：A4 只有"必做"没有 A2 式准入措辞与 exit-code 硬闸；A4 文本自身预设报告已存在（"查报告缺口""图表措辞同步改"）。两方案经 @CX codex 只读复核融合后用户批准；**原事故回测用户裁定本次免做（成本高），待下一实战验收**。

- **time_spotcheck.py 新建**（scripts/lib/，A2 时间抽查执行器）：读 anchor_plan.json 分两型逐锚点对独立第二源核对——balance 型（矩阵/最大单日净变动/门槛边缘，有 expected_balance_raw）archive `eth_call balanceOf` 历史块直查；tx 型（最大单笔/数据源交界，只有交易记录）`eth_getTransactionReceipt` 核 (token,from,to,value,block) 五元组。**两型都查**（codex 抓出：anchor_plan 强制点两型混布，只查 balance 型＝四类强制覆盖漏验两类）。fail-closed 全集：0 锚点 assert 硬失败（GMX 假 PASS 教训内置）、格式漂移锚点硬退、边缘点缺块必须 --final-block 禁静默跳点、rpc_err>0 exit 1 禁当 PASS。产物 time-spotcheck/v1 带 verdict+exit_code。独立性措辞纪律：状态直查对"余额结果"更直接，**不能替代事件集合完整性验证**（等额抵消/零余额中转层/元数据错误验不出——那些归层 3）。
- **evm-recon §13 重写为分层制**：层 1 默认＝time_spotcheck 锚点直查（有 archive 通道的链）；层 2 BSC 等无 archive 链＝SQD 只拉锚点代表日/窄块窗（BANANAS31 先例；覆盖规则化不固定天数），禁止默认全史；层 3 全史双源重拉＝例外动作，仅限 ①对账他查挂了/主通道可疑 ②翻案排查需事件明细 ③结论依赖精确事件拓扑/逐笔归因/零余额中转层且现异常信号（codex 补充），做前 pilot 1–2 分钟实测当前速率再外推 ETA（禁历史速率常数调度），预计 >30 分钟摆给用户选（交互阈值非豁免阈值）。Etherscan tokentx 禁令与 DuckDB HUGEINT 陷阱原样保留。§5 第 4 查同步现行形态（旧"插值抽几笔对浏览器"表述取代）。
- **handoff 契约收编**（codex：不进 READY 必备件＝新脚本只是"建议运行"关不掉执行漂移）：time_spotcheck.json 进 CONTRACT_FILES＋AUTO_GATES＋**EVM 链 READY 必备**（EVM_CHAINS 白名单法分链：Solana 走 anchor_sampler 通道、hyperliquid/filecoin 形态不同，均不误伤；缺件 generate 即拒）。
- **a4_gate.py 新建**（scripts/report/，A4 封口闸）：`register` 登记稳定 id 的 claims 注册表（与 adversarial-review args.claims 及 split-run §3.3 外部异构路输入同构）；`finalize` 封口校验——裁决 id 集合与注册表**完全相等**（缺=有结论没复核、多=复核了没登记的，都拒）＋三档枚举＋WEAKENED/REFUTED 必带修订摘要＋终版结论文件 sha256 封口＋charts/final/ 为空检查（A5 未开始的物证）→ 产 a4-seal/v1。翻案重封流程：旧图作废清空→改完重跑 finalize。**mtime 不作裁决依据**（codex 否决原 mtime 方案：cp -p 误伤/touch 绕过/管不到报告.md）；哈希封口＋目录切换取代（全套图表血缘 sidecar 记二期可选）。
- **build_html.py G9 ＋写盘语义修复**：`--a4-seal` 触发 G9（显式参数制，不绑 --state——codex：update U4→U5 也用 state 会误伤）——seal 必须 PASS＋sealed_files 逐个重算哈希一致（封口后改结论不重封＝报告物理编不出）＋md 引用图必须全在封口 charts_dir 下＋图 mtime 早于封口仅 NOTE；`--skip-a4-gate-reason` 必填文字理由并写入 HTML 注释持久留痕（非裸开关）。**WARN 时不再写出文件**（codex 读源码抓出既有缺陷：旧行为先落盘再 exit 1，"物理编不出"名不副实）——gate 前置，全过才 tempfile+os.replace 原子写。
- **流程文档六处**：analyze-workflow A2 第 4 查改 time_spotcheck 形态＋A4 节首顺序硬闸措辞（16 案核查数据入文）＋A4 执行序七步（claims 登记开工/finalize 封口收尾）＋A5 前置与 charts/final 约定＋编译行 --a4-seal；easy-workflow E4 同款顺序闸＋state 骨架正名"E4 前置件"（仅限骨架禁连带提前出判定块/图/HTML）＋E5 编译行；split-run §1.3 A2 行＋§3.2 判断主序两处；token-analyze-2 第 8 条（顺补 6.6.0 漏改的 wave_scan 裁决步）；SKILL.md 阶段表 A2/A4/A5 三行；report-template 编译行 G9＋图层同源路径＋checklist 新增 11b。
- **测试**：test_a4_gate.py 新建 18 项（register/finalize 反例集＋G9 联动＋翻案重封流程＋skip 留痕＋update 场景不触发）；test_time_spotcheck.py 新建 5 项（dry-run 分型/0 点硬失败/漂移拒收/fail-closed 全集）；test_handoff_manifest +2 项（EVM 缺件拒 READY/solana 豁免）＝25 项；SUITE 17→19 支。
- 兼容声明：揭盲式独立重做（TROLL/PYTHIA 方法论）盲做版不编 HTML 不受 G9 影响；KOGE 型非 A4 触发的返工不在本闸射程；旧案目录历史重编译走 --skip-a4-gate-reason 留痕通道。

## [6.6.1] - 2026-08-01 — @CX 第二意见复核后两处 bug 修复

背景：6.6.0 落地当日走 @CX 交叉复核（codex 只读逐行核对 wave_scan/camp_jump/handoff/docs_lint 与测试结构），其指控经本侧逐条核实全部属实。当场修复核实为 bug 的两处；结构性建议（候选裁决端到端契约、基线升可执行回归、多尺度扫描替代单组魔法数字、B 命中线未被正例验证等）不属 bug 属设计升级，另立清单待用户拍板后进下一版。

- **camp_jump_audit.py**：①输入不保证有序却直接 zip 相邻点算 Δ——乱序输入全是噪声，现 load 后按 date 排序＋缺 date 拒收；②序列非日频时把相邻点 Δ 一律称"单日"——PYTHIA 500 点序列实测 83 对相邻点跨 2 天，28 条骤变中 9 条实为两天 Δ（含 top1 的历史大户 -12.06pp，07-28→07-30；+7.21pp 为真单日），现逐条标 gap_days、报告级计 non_daily_pairs，note 注明。复跑 PYTHIA 序列 top 骤变排序与数值不变，仅时间跨度措辞得到修正。
- **wave_scan.py**：负余额哨兵——final_bal<0 只可能来自数据缺失/重放不平，却恰好满足"≤峰值×ratio"混入清零层产生伪候选；现扫描前 COUNT 报警（stderr ⚠＋negative_balance_addrs 落盘字段），只报警不修数据（数据问题归采集侧）。改闸重跑 PYTHIA 基线：W1 覆盖/合并峰/等额组置顶逐位一致，negative_balance_addrs=0。

## [6.6.0] - 2026-08-01 — W1 波次二次漏检复盘落地：历史清零层波次扫描机械闸

背景：PYTHIA split-run 首战（v6.1 首战案）交付后，用户追问"历史大户是什么"并凭记忆质疑与旧报告矛盾，触发与旧终裁交叉复验——W1 协同波次（341 址、单址峰值仅 0.05~0.3%、合并峰 63.438%@2025-05-26＝全案史上最大庄）**在判例入库（07-29 S-04）＋三道文字闸装好（07-30 v4.1.0）之后 48 小时，被新 skill 原地二次漏检**（341 址打散进历史兜底桶 246＋散户桶 94＋Q1 系 1；"断崖一无主角集体离场""两代离场庄接力"两处核心定性因此翻案为"W1 组织清仓""三代 W1→Q1→H9"）。复盘定性（复盘_W1波次漏检_2026-08-01.md，用户批准迭代清单后执行）：**文字闸对"单址全在雷达线下的批量协同"结构性无效**——casebook S-04 检验②③内容正确但从未代码化；A4 翻案四问④粒度不够（"兜底桶存在"就算过，问不到桶内）；完整性批评 prompt 点名 W1 却把合并峰值误写成"单址峰值 ≥5%"门槛（物理抓不到单址 0.05~0.3% 的 W1），装闸时无原案回测、阈值 bug 潜伏至复发。

- **wave_scan.py 新建**（scripts/report/，533 行）：对清零层全体（逐日峰值 ≥0.02% 且现仓 ≤峰值×0.1）四指纹机械扫描——A 同窗建仓锚窗生长聚类（7 日窗 ≥20 员，段峰值证据驱动的相邻段合并试探，防波次被段长上限切碎）；B 喂币专属度（主源 ≥90% 且全局喂币对象 ≤2，成员逐条标 feeder_exclusive 供判断层提纯）；C 集中清仓窗（≤14 日净降 ≥50% 峰值——原复盘草案"峰值→10% 峰值 ≤45 日"口径经原案回测证明抓不到 W1 本尊〔实测 81 天〕，当场修正，元规则第二条的首个实践）；D 等额面额时间连通子分组（同精确 raw 面额 ≥5 收方＋组 ≥0.5% 供应；不切时间子组时 44 分仓被全史同面额稀释成 478 天大组失分——回测实证）。三种输入（Solana jsonl.gz／EVM v2 parquet 直读〔hex→HUGEINT 同 replay_duck 口径，run 区间互斥走 VIEW 轻路径免临时盘——1.03 亿行物化去重实测 29.7GB temp OOM〕／已物化 duckdb）。输出 wave_scan_report.json（wave-scan/v1），候选非空即 requires_adjudication；cohort_hint 提示外部驱动用户潮（B≈0 且成员 >500）。
- **回测（装闸必附原案回测）**：PYTHIA 485 万边——候选波次覆盖旧终裁 W1 名单 339/341=99.4%、C 指纹 0.807 命中、exclusive 293 员（232 属 W1）；等额组 100 万枚 ×57 仓 score=2 置顶（命中 Q1 系 35+）；发射窗正确打标。QUQ 1.03 亿边（误报率对照）——4 个波次候选全对应真实批量行为（发射窗＋三波刷分潮，B 全 ≈0 可秒排）、纯噪声 0；12 个等额组**独立重发现**本案已知庄家体系（库存层批量灌仓 286 仓＋015C→2A5A→16F1 接力交棒/寄存原数轮转）。候选数超复盘预设"≤2"字面线但全部有真实结构对应＋可快速排除明细——按报警器宁多勿漏原则不调参压制。TROLL 原始数据缺失（soltx 待重拉）未测。
- **camp_jump_audit.py 新建**（86 行）：阵营序列骤变点机械清单（单日 |Δ|≥3pp），兼容 points/dates+series/裸 list 三 schema；逐条归因到实体/地址群写 facts、无法归因进报告局限性。PYTHIA 序列实测：top 骤变正是本案两个被放过的强信号（07-30 历史大户 -12.06pp＝W1 清仓断崖、04-28 +7.21pp＝W1 建仓首两日）。
- **契约收紧**：wave_scan_report.json 进 CONTRACT_FILES＋REQUIRED_FOR_READY（缺件 generate 即拒；verify 轻校验空壳拒收）；test_handoff_manifest 21→23 项（新增缺件/空壳两反例），检查计数改动态。旧案目录复用须补跑 wave_scan 后重 generate；回退路径＝旧单会话命令。
- **文档与 prompt 六处**：SKILL.md"双硬闸"升"**三硬闸**"（波次扫描与静置仓反扫互补定位：反扫从已知实体摸藤、本闸对清零层全体无藤自摸；分段时跑批归 −1 裁决归 −2）；analyze-workflow A3.6 升双硬闸步骤（wave_scan＋骤变归因）；split-run §1.3 第 7 项/§2.1 产物表/§3.2 判断主序（wave_scan 候选裁决插实体冻结前、camp_jump_audit 挂阵营重放后）；casebook S-04 补"桶存在≠桶内被检验过"禁止推断＋08-01 复发记录＋已装闸状态；retrospective 元规则第二条"**装闸必附原案回测——抓不到原案本尊的闸不算装了**，回测基线随闸落盘（写进闸脚本头注），改闸必重跑"；evals 09 升机械闸回测题（通过标准＝wave_scan 报出候选并完成裁决，人工看榜发现不算）。
- **adversarial-review.js 两处修复**（~/.claude/workflows/，随本版同步）：L71 完整性批评自查②由"重放全期逐址 max 仓位、列单址峰值 ≥5%"改为"读 wave_scan_report.json 逐候选对账、无文件本身即发现"，并写入禁用单址口径的教训；L50 翻案四问④补"桶存在≠桶内被检验过"粒度。
- **防回退**：docs_lint 守卫 7（波次扫描硬闸关键词跨 SKILL/analyze-workflow/split-run/S-04 四层缺一即 FAIL）。SKILL.md 12.5KB 超 10KB 线状态延续（6.5.0 起既存），下次整编统一处理。
- 顺带：miss-queue eth.csv +56 行（他会话 ETH 案 label 查询自动累积，随库提交）。案目录 retro_notes.md 第 3/7 条标注已入库消费；其余 5 条候选仍待用户复核。

## [6.5.0] - 2026-07-31 — codex 独有资产审计后回灌转正（@CX 交叉复核 + 用户三项拍板）

背景：6.4.4 大同步后对 codex 分支独有资产做 @CX 交叉审计，抓到"独有=没人维护"的滞后漂移实锤（0.5% 排查线落后于 07-30 拍板的 0.1%/0.2% 双线、P0/P1 旧措辞残留），codex 立论"平台无关的方法学长期双线必漂移"成立。用户三项拍板：①经济控制账＋静置仓硬闸候选转正式并回灌 main；②删除过期一次性迁移矩阵（codex 侧执行）；③SYNC.md"永不合并"措辞改"禁整分支合并、许定向回灌"（codex 侧执行）。本版为 main 侧回灌工程。

- **双硬闸转正**：SKILL.md 新增"实体冻结前双硬闸"节（经济控制主口径＋静置仓反扫，A3 判级环节强制；分段执行时归 −2 承担）；report-template 三账段"产物【候选】"转"必须交付"、主结论明写"不得拿钱包自持替代"；交付 checklist 收编 4c 经济控制穿透硬闸、4d 历史静置仓反向扫描硬闸。
- **三分册收编**：`economic-control-accounting.md`（三账口径/8 类设施纳入门槛/防双计/economic_control_ledger.json schema）、`lp-fee-accounting.md`（V3/V4 四层口径/逐 tick 分摊/8 项对账 gate）、`independent-audit-protocol.md`（净室复核协议；6.5.0 修订：作用域限定"复核既有报告"任务——净室专用资产以被审报告存在为前提，全新分析走 checklist 4c/4d；0.5% 候选线废止，对齐 tiering §6a 0.1%/0.2% 双线）。
- **audit_release_gate.py 四处修复**（此前更像资产存在性 lint，撑不起 fail-closed 裁决）：①PASS_WORDS 收紧 {pass,passed,ok}，WARN 不再当 PASS（standard 仅记账模型合法）；②对账检查补 supply_truth 成四查；③地址分类阈值 0.5→0.1 总供应＋0.2 流通双线；④经济控制账空账本须 empty_reason、实体内嵌套 unresolved_facility_exposure 未裁决即阻断。test_audit_release_gate 夹具同步＋新增四反例，九类契约全过；run_all SUITE 16→17 项。
- **方法学条目收编**（codex 侧 07-23~26 复盘产物，随分册配套）：tiering"判级确权边界与经济控制口径"节（判级持仓=可证经济控制量/严格·扩展是确权边界/串联边只证 campaign/行为 cohort 分离/官方自报只证角色/日终不能替代事件峰值/静置仓双边界峰值——顺带补上 evidence-wording §口径措辞三件套早已引用但 main 一直缺失的"行为 cohort"条目）；methods 静置仓硬闸版（dormant_warehouse_audit.json 落盘＋候选四并集＋strict/expanded/excluded 裁决，替换 SIREN 案例版）、枢纽两段处理法＋冻结后实体成员卫生审计、FROGGIE 归集边界候选条；evidence-wording ★受益权分离/★证据只够否定停止肯定/★完整阴性高门槛/★LP 收入四分法＋6 行禁写措辞；sources 价格覆盖审计＋Blockscout internal-transactions 完备性纪律；channels LP 费口径鸿沟增强版（tokensOwed 前提/动态费禁静态假设/ownerOf 归属优先级）。
- **防回退自动化**：docs_lint 收编四层守卫——静置仓硬闸与经济控制口径的关键词必须同时出现在 SKILL/methods/tiering/report-template 四层，缺一即 FAIL。
- **触发面**：description 补"复核/审计已有筹码报告""庄家做 LP 赚了多少/LP 手续费怎么计算"。
- 版本轴说明：codex 侧同日 c2.1.1 已先行修复其独有文件内 P0/P1 残留措辞与 SYNC 版本轴描述；本版落地后 codex 侧走同步合入并做 c2.2.0 瘦身（独有清单缩减为平台适配件，方法学重复尾节删除留指针）。

## [6.4.4] - 2026-07-31 — attic 首批复核裁决落地（用户逐条人工复核）

背景：用户人工核对 skill 规则与经验（本批为 attic.md 存留审计第一批 6 条），逐条裁决：A-01/A-02 有用恢复，A-03～A-06 没什么用维持存档。这是 attic 存档制（v6.2.0）建立后首次走恢复流程。

- **A-01"社区分发桶女巫化回收识别"恢复**：迁回 playbook-entity-cluster-methods.md §4 候选条目区（原节"实体归属与定性"已并入 §4）。
- **A-02"镜像执行扫描法（发射窗协同检测独立通道）"恢复**：迁回 methods §6"全景完整性与阴性结论"义务清单，紧随"发射窗口买家全景从第 1 秒扫起"条（原节"发射窗协同"已并入 §6）。
- **成熟度处理**：两条均保留【候选·单案】身份（升正式仍需第二案复现或机制解释，1b 纪律不变；运行权限=只当查证提示）；行尾来源标注追加"2026-07-31 用户人工复核裁定保留"授权戳——本次裁决构成三判据之②（用户终裁背书），后续存留审计不再按"全不占"清出。
- **attic.md 同步**：两节条目移除（原文以 git 历史为准），批次节首加恢复记录；A-03～A-06 原样保留。

## [6.4.3] - 2026-07-31 — 变更叙事全库清理（用户人工复核开题，@CX 双路扫描后用户拍板口径）

背景：用户人工复核 skill 规则文件，在 playbook-entity-cluster-tiering.md 首先发现正文堆积"修改历史/已作废内容"，追问"不会污染上下文吗"。经三分类辨析后用户拍板通用口径并下令全库清理（@CX：codex 只读扫描出清单，我方独立扫描后融合，执行全部由我方完成）。

**三分类口径（用户 2026-07-31 拍板，已沉淀进 retrospective.md 2b 整编模式动作 2b 条）**：
- **一类·纯变更叙事→清除**："取代了什么旧条款/哪版删了什么/原条款是什么"类历史进 CHANGELOG，正文只留现行规则；紧跟的机制依据（门槛数字为什么是这个值）与授权戳（YYYY-MM-DD 用户定）必须保留。
- **二类·新旧桥→归位瘦身**：废止标签的存量数据迁移细节唯一归宿=update-workflow 标准迁移条款，其他文件只留一行指针。
- **三类·保留不动**：行尾来源标注（存留审计追溯锚）、机制依据、翻案实证数字。

**执行明细**：
- 一类清除约 45 处，涉及 22 个文件：SKILL.md（狙击集团废止字样）；analysis-playbook（三问框架版本沿革/P0P1/建仓成本"不再是"句式/历史沿革整段）；tiering（标签体系修订史/双闸"取代旧条款"/门槛"自旧版下调"改"门槛依据"/媒体驱动 v5.0 改写注/首30分钟 cohort"不再是"句式）；report-template（建仓成本/狙击集团/地址截断旧规则/checklist 10 废止公告改正面 cashtag 处置规则/tier 字段）；easy-workflow（问 4 删除史 ×2/E5"移入复盘"史）；cost 标题；hyperliquid（tag 已废止）；methods（翻案改写标题注/3.15.0 转正史 ×2/"本条新增的是"改分工表述）；supply-recon（v6.4.2 对齐戳）；state-anomaly（3.33.0 版本引用）；evidence-wording（tag"全部取消"改禁用/观察哨 v3.2 时机史）；retrospective（废止旧文 ×2）；labels/README（稳定化拆分史/红线废止叙事改正面）；labels/MAINTENANCE（拆分史/补丁标题改维护纪律/补空史）；address-book（v4.2 补录史）；casebook/README（建于 v6.0.0）；attic（v6.2.0 起句式改静态定义）；data-pipeline 十文件（evm 合并调和史+整编戳、solana 来源声明反转史压缩、robinhood 合并时刻史+拆册戳+上移台账整段删、六个分册头部"已拆/原样迁移/最后整编"、solana-capture 整编收拢/取代 v1×2/整编压缩/取代锚点法）。
- 二类归位 2 处：tiering 狙击集团段改写为现行判级规则+一行 update-workflow 指针（迁移细节 update-workflow L11 原已有，未新增内容）；tiering"阵营已废止"行删除（legacy 键权威=CAMP_ORDER 声明已在）。
- 顺修残损 2 处：solana-scan 头部"来源声明与 等标注图例"删字残渣；tiering L101 来源标注与"---"粘连行。
- **裁决与 codex 分歧（6 处否决其清理建议）**：analyze-workflow CAMP_ORDER legacy 注、report-template 图 1 紫色 legacy 注与 price_series 旧基线例外、facts_gate 旧 state 回退、"旧报告重编译不强制回填"、monitoring skill_version 旧版 fallback 与 CAMP_ORDER legacy 注——均为读取端现行兼容行为且已是最小指针形态，非变更叙事；MAINTENANCE 变更史表与扩容路线台账保留（维护会话专用工作资料，不进分析上下文）。
- 明确不动：update-workflow L11（桥的唯一归宿）；split-run（首战前冻结）；easy-workflow L83 案例原始术语注（审计锚）；labels/README L24 CSV 兼容；solana-capture v1 meta 自动迁移与 gaps 机制依据注。

## [6.4.2] - 2026-07-31 — SKILL.md 手工瘦身后 @CX 全库一致性修复

背景：用户手工删减 SKILL.md 5 处（description 链名/触发句、铁律 1/3/5/7 各一段）后发起 @CX 完整审查——codex 通读全部 47 个规范文档（约 780KB，禁抽查）出 15 项发现，Fable 逐条独立取证核裁（11 项完全属实、3 项降级、1 项按意图判），用户逐项拍板。

- **残损修复 2**：铁律 1 删句残留孤字"报"清除；铁律 7 句尾悬空分号改句号。
- **"零外部代币名"红线全链废止**（用户裁定：该条本意="不复用历史标的的结论"，禁止提及其他代币名本身无意义）：analyze-workflow/update-workflow 的 checklist 引用删除、report-template checklist 条 10 废止注记（沿条 15 惯例）、easy-workflow 措辞纪律行删除、casebook/README"红线不变"句删除、labels/README serial-actor 纪律条改写（案名引用不再受限，但**禁止借机展开该案行情或结论**的取证语境约束保留）；**build_html.py token_name_scan 降级**：cashtag 从 WARN（影响退出码拒交付）降为信息性 NOTE，--token-whitelist 保留作降噪参数。铁律 1 的"结论不复用"本体不动。
- **铁律 3/5 删减核验**：分册"无行内置信度 tag"规则保持现状（report-template 为权威源，总纲不再复述——用户确认瘦身非废止）；"免费优先"全库零残留、research-workflows"调研代理只用免费手段"属局部资源约束可并存，均无需处理。
- **存量漂移 7**（与本次手编无关的历史漏改）：easy-workflow"六条铁律"→"全部铁律"；split-run:16 "−2＝A4–A6"→"A4–A5（A6 仅用户要求时）"（6.4.0 漏改）；supply-recon §2 对齐 A2 四查权威分类（EVM"三重校验"标注为查1/查2 细化、Solana"轻量形态"标过时降级——SQD 全量重放后走标准四查）；hyperliquid"给 HIGH 置信度"→"按最高证据级措辞呈现"；evm-channels"对账关卡查3"编号引用→"余额对账/时间抽查"去编号描述；retrospective 整编触发器从盯 analysis-playbook（已拆成 7KB 路由页永不触发）改"任一 playbook 分册 >60KB"（methods 84KB 已超线待整编）；easy-workflow E6"＋E5 固定动作"→"E5 无动作"（6.4.1 漏改）。
- **低危 4**：analyze-workflow A3 步 4 判级门槛数值副本删除（唯一权威源收归 tiering §6a，防漂移）；casebook C-01 指针补 solana-scan §3 集齐率判别法（原指 §2a 不对口）、C-05 改指 §2 托管类型判别；evm-channels §7.5 免 key 三段拼接路线补"不满足完整/easy 交付合同，仅预检用"边界声明；tiering:40/61/66 与 methods:69/88 共 5 处两条目粘连行拆分。
- 验收：run_all 16 项全 PASS（docs_lint --all 60 文档无断链；test_build_html 八条契约全过）。

## [6.4.1] - 2026-07-31 — 惯犯库回灌随复盘（6.4.0 挂账项用户裁决落地）

6.4.0 边界说明里挂账的相邻问题，用户当日裁决"改成复盘时才回灌"。`accumulate_offenders.py --apply` 与 6.4.0 砍掉的自动复盘同病：结论未经用户复核，本案判定的庄家地址就自动写进惯犯库，判错即污染（惯犯库虽已降线索级消费仍是判断输入）。

- **retrospective.md 步骤 3 新增回灌条目**（唯一执行点）：复盘写入环节跑 `accumulate_offenders.py --apply`，双源扫描（appendix.json / analysis-state.json）、筛查不买入的案子复盘时同样回灌、serial_conflicts 非空先按 labels/README 三选一裁决再 apply——细则原样搬运，只挪时机。
- **easy-workflow E5**：交付后固定动作改为迁移注记（交付流程中本步无动作），E0–E7 编号保留。
- **report-template 交付 checklist 条 15**：同款迁移注记，交付时无此步。
- **labels/README serial-actor 纪律条**："每次分析交付后固定动作"改"回灌时机=随复盘"；"双源自动回灌"的"自动"字样去除（脚本双源扫描机制不变，触发不再自动）。
- 不动：accumulate_offenders.py 脚本本体、跨案身份冲突检测与设施硬闸（3.19.1）、MAINTENANCE.md 维护会话命令示例（本就是手动流程）、已入库的 1741 址存量（其案源成色分层消费纪律照旧）。
- 验收：run_all 16 项全 PASS。

## [6.4.0] - 2026-07-31 — 复盘触发机制改制：自动复盘废止，仅用户要求时执行

背景（用户决策，2026-07-31）：原机制"交付报告后立即执行复盘，不可省略"在批量跑币场景下有结构性缺陷——用户对报告只扫一眼、尚未复核结论真伪，教训就已自动沉淀进 skill，等于把可能错误的经验固化（与 v6.2.0 存留审计发现的病灶同源：多数案"扫两眼没再看"）。用户拍板：正确顺序＝交付 → 用户复核确认结论没问题 → 用户明确下令复盘 → 才执行复盘＋更新 skill。

- **retrospective.md 头部触发条款改写（权威源）**：废止"交付后立即执行、不可省略"，改为"仅用户明确要求复盘时执行，任何工作流（A6/E6/U6）不自动进入"；分析会话中的候选教训随手记案目录 `retro_notes.md`（只动案目录，不动 skill 文件），等用户下令复盘的会话消费；candidate 清账扫描的义务方从"复盘/更新会话"收窄为"复盘会话"（更新会话不再自动入库）。
- **三工作流末步同步**：analyze-workflow A6 标题"固定最后一步，不可省略"→"仅用户明确要求时执行，不自动触发"；easy-workflow E6 删除"确无增量→会话末一行 E6：无新增"自动仪式（模型自判增量有无的触发权一并收回），头部"省什么"句同步；update-workflow U6 删除「"无新增"也走流程」，memory 状态指针提醒保留（对用户的提醒、不动 skill，交付时照做），成本纪律段"复盘在轻上下文里做"补"用户要求时"限定。
- **SKILL.md 路由层 5 处**：路由表 A6 行、/token-analyze（A0–A5 全程＋A6 按需）、/token-analyze-2（A4–A5）、/token-update（U0–U5）、references 列表 retrospective 描述行。
- **split-run 四处联动**：§3 标题与 §3.2 判断主序末尾去 A6；**sealed 违规自查申报从复盘改挂 −2 A5 交付时**（§2.3 三层防护表述与 §4 验收指标⑤同步——复盘可能长期不跑，执行披露不能跟着消失）。
- **context-discipline 刀 2 条 9**：复盘轻会话建议改为"用户下令复盘时"语境，机制本身保留。
- **命令三份双处同步**：/token-analyze、/token-analyze-2（description＋判断主序）、/token-update，commands-staging 与 ~/.claude/commands 装机版逐字节一致。
- 边界说明：复盘启动后的内部流程零变更（五类清单/retro_draft 草稿器/AskUserQuestion 逐条确认/分流决策树/candidate 分级/整编/预测追踪/红线全部照旧）——改的只是触发权归属。easy E5 交付后固定动作 accumulate_offenders 惯犯库回灌**本次未动**：属同类风险面（结论未复核即写库）但用户未点名，另行请示待裁决。
- 验收：run_all 16 项全 PASS。

## [6.3.1] - 2026-07-31 — 搬迁前全量一致性修复（@CX 交叉审查产出，19 项全修）

背景：服务器搬迁前用户点名 codex 完整审查全 skill 前后一致性（66 文档全读+45 脚本接口静态抽核），我方（Fable 5）并行独立通读后对 codex 每条发现逐一回原文核实、合并裁决为"该修 19 项"（codex 两条被核实推翻：Helius"无法自动注册 vs 已就位"实为获取方式说明与现状的时间线自洽；"CHANGELOG 声称三查漂移已全库纠正"原文无此声称）。用户全量批准 19 项；审查另列的 **3 项 Linux 阻断项按用户裁决不修**——迁移目标已改为 Mac mini 云，launchd/本机路径/codex 路径继续有效。

- **高危 5 项**：①evm-recon §12c 峰值候选预筛"判级实际只需 ≥1%"旧线改为现行其他大户线 0.1%/0.2%（v5.0 降线时漏同步；照旧文预筛会把 0.1%–1% 候选不可逆滤掉，恰是降线要堵的盲区），预筛门槛与判级门槛分开表述；②阵营键全集收归 `standard_charts.py` CAMP_ORDER 唯一权威——tiering §6a 表补齐 14 现行键（新增 CEX资金通道/CEX托管/疑似CEX托管/历史大户/桥锁仓 五行释义）+权威指针行，analyze-workflow A5"锁仓销毁"改"锁仓/销毁"并补漏键，report-template 章节骨架与图 1 配色要点、monitoring-package camp_share_series 各加"以 CAMP_ORDER 为准勿手抄全集"指针（GMX 静默漏图事故温床拔除；tiering 同文件"资金通道判据要求单列阵营而阵营表没有该阵营"的自相矛盾一并闭合）；③惯犯库"实锤"降级（v6.2.0）漏网清理：labels/MAINTENANCE 数据源表"196 址/最高（实锤定性）"改"随案滚动约 1,740 址/线索级（案内定性、消费纪律见 labels/README）"，accumulate_offenders.py docstring"抽【实锤定性】"与 print"N 个实锤组"中性化为"历史案标记"；④solana 脚本资产声明整修：capture §6 删除不存在的 `classify_top_holders.py` 点名（功能由 scan_token_accounts owner 聚合＋fast_probe_tops 覆盖）、标题改"核心目标已建成+README 另存待建项两批勿混"，scripts/solana/README 条目 1 改 v2 主选化＋文末补登**现役 v2 主线 5 脚本**（fetch_sqd_transfers_v2/decode_txs_v2/accounting_gate_sol/squads_members/hypersync_recon——此前全部漏列，搬迁最依赖的清单文件与仓库实体对齐）＋待建清单口径分节说明；⑤split-run 冻结区解冻修 bug（循 6.1.2"暴露即收紧"先例）：/token-analyze-1 argument-hint 补 `<easy|full>` 必填档位（staging＋装机双处同步），收工条写死 `generate --mode` 取值来源（值＝命令第二参数，未给档位开工前先问禁猜），split-run §2 manifest 身份行同步注明——修复前 −1 收工 generate 必卡（--mode 为 required 却无输入源）。
- **中优先 9 项**："三查→四查"残留 4 处修正（easy 头部"不省"句/solana-capture §12 例行句/evm-recon §13 背景句/solana README 条目 22）＋evals 题 1 场景句顺手中性化为"对账关卡已过"（历史案战报里的"三查"按不改写历史保留）；"SKILL.md 阶段 N"死指针 6 处统一改指 analyze-workflow A0/A1（easy×3/update-workflow/playbook-supply-recon/casebook S-02——docs_lint 只查文件级断链抓不到此类章节级死指针，成因记录在案）；CHANGELOG 6.3.0 验收数字"run_all 14 项"更正为 16 项；/token-update 交付条"滚动 appendix.json"绝对化改双形态（带监控包＝appendix.json，无＝analysis-state.json，staging＋装机双处）；robinhood-channels DS 行 pairCreatedAt 删绝对化、归一到 GT 行"两说并列、以链上主池首笔 Transfer 为准"口径；solana-scan Streamflow"可由受益人转让"无条件句改条件句（transferable_by_* 标志位为唯一裁决，与同段"必查此位"条呼应）；铁律 1"零外部代币名"两个未声明例外成文划界（惯犯案源案名＝受控例外，labels/README 纪律 10 补边界＋report-template checklist 10 白名单机制衔接，除用户点名对比项外零其他例外）；evm-recon §5"标准四件套"实列五项改"四件套＋1 项重放前置检查"并写明与 A2 现行四查的对应关系；easy E5 补"两件套（页面内容两大件）vs 产物三件（落盘文件）"口径注。
- **低优先＋工具 5 项**：attic 头部自述与 SKILL.md 登记关系措辞精化（"不作为分析规则输入"）；update U2 编号重复（两个"4."）修正；report-template 死币复活盘模板句补"观察哨买入后才写"限定；evm-recon §12 DuckDB 用法示例补 `scripts/evm/` 路径前缀（replay_duck/cluster_prep_duck/cluster 三处）；**docs_lint 新增 `--all` 全量模式**——commands-staging 6 份＋evals 10 份纳入引用与格式检查（44→60 文档），run_all 守护调用同步升级为 `--all`（SUITE 条目支持带参数），本轮修的两类漂移的存活盲区永久关闭。
- 裁决驳回不修（防误改）：Helius scan/capture 两条（时间线自洽非矛盾）；channels/capture 历史案战报"三查"（不改写历史）；CHANGELOG 6.1.0 计划文件引用（历史条目保留原貌）；"analysis-playbook §6a"式引用（§ 编号全局体系合法二跳）；solana README"编号跳跃"（核实 1–27 连续，codex 误报）。
- 验收：run_all 16 项全 PASS（docs_lint 已为 --all 60 文档口径）。

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
- 验收：run_all 16 项全 PASS；docs_lint 44 文档无断链；references 文本总量净减约 55KB（真减分析会话读入），robinhood 开局刚性读入 51KB→2.9KB 路由页+按需分册。

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
