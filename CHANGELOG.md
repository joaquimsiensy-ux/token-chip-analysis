# CHANGELOG — token-chip-analysis（活跃窗口）

版本规则（v3.0 起两维制，详见 references/retrospective.md「版本号约定」）：
- **skill 版本**：主=架构级重构；次=每次**分析复盘**迭代 +1；修=文档小修
- **labels 数据版本**：标签库扩容/重建记 `labels vX.Y` 前缀条目，不再占用 skill 次版本号
红线：条目只记工具性知识（数据源/坑/方法/脚本），禁止记录任何代币的分析结论。
每条迭代条目附成本指标（轮次数/Bash 调用数/交付用时）+ 质量指标（初稿关键结论数/复核判定分布/漏检实体数/传播级数字错误数，v3.0 起，见 retrospective 步骤 1）。
**写入前必跑 `python3 scripts/tests/changelog_lint.py`**（防撞号/倒排——两者都实际发生过）。
本文件只保留最近 ~10 版（整编时滚动）；更早的完整迭代史在 `archive/CHANGELOG-archive.md`，考古规则来源先 grep 该文件。

## 版本索引（活跃窗口，新在上；每版一行，详情见下方对应条目）

- **6.53.3**（2026-08-30）序列来源链登记路径兜底收窄为唯一案根：序列 sidecar 恢复 basename-only；仅 reconcile inputs 可按显式案根或 `data/` 收据推导案根解析深层登记路径，阻断相邻案件越界命中；盲审 R3 P1 消化，SUITE 142 不变
- **6.53.2**（2026-08-30）序列来源链登记路径按案根解析兜底：保留两层 basename 优先语义，未命中时安全解析案根内相对登记路径，使 sqd_repair 深层 soltx meta 与 resolver 身份一致；新增逃逸、绝对路径、symlink、指纹与 registry anchor 回归，SUITE 141→142
- **6.53.1**（2026-08-30）发布闸 B-7 三账对账源与 series cutoff 冻结态投影：动态 Solana 的三账改吃 exact owners＋冻结块，序列 cutoff 改投冻结点；新增篡改、symlink、绝对路径、静态零变化、完整两态案与错 cutoff 回归，SUITE 140→141
- **6.53.0**（2026-08-27）持仓分布图升级为 matplotlib 双轴带标签图：修复裸 PNG 哑图导致柱高被误读的根因，横轴明确为单地址持仓占私人可入箱供应 %，取消 `struct/zlib` 裸 PNG；新增数据对齐、标准生产链、low_sample 与缺依赖显式失败回归，SUITE 139→140
- **6.52.15**（2026-08-27）F-03b 共享 SQD 地图复用失败分级：ARC live 92,643 次 recheck 中 1,182 次限流失败且零 mismatch，暴露“任一请求失败即整体回退”使复用必然失败；mismatch 整体回退不变，请求失败末尾重试后只剔除该段转 full，canary 段失败仍整体回退；map-reuse 按已验证子区间逐段声明，案外 recheck 撤销覆盖并以杀变异测试固守；新增 `unverified_ranges`/`recheck_stats` 审计字段且 retry mismatch 不污染；盲审 R1 BLOCK 两项消化后 R2 PASS；SUITE 139 不变，既有 F-03 测试组 9→15
- **6.52.14**（2026-08-27）F-03 共享 SQD 地图复用闸修复（codex 六视角 review P1，修复中新引入 b005a468）：身份三分类＋历史锚＋head 单调＋模板绑定；已知点只连续合并并发重验，失败整体回退且撤销本轮 recheck 覆盖声明；`validate_shared_map` 同深扩全，`validate_coverage` 按 D1 用户裁决接 producer_history；CT-SQDGAP-35；20260827 资产零字节改动即刻可复用；盲审 R1 BLOCK 三项消化后 R2 PASS；两段提交完成 producer 双协议登记，SUITE 138→139
- **shared-map 20260827**（2026-08-27）Solana SQD 共享覆盖地图首版入库：源=ARC 全史普查 probe 32dc03effa707da1（306,451,717→440,368,381 共 1.339 亿 slot 100% 覆盖、getBlocks 位图全程、defect_candidate=153,667 已全普查驳回/确认），TTL 30 天、消费按 capture §13e 生命周期（已知 slot 仍逐个复核+canary）；三件=json+counts.bin.gz(97.7MB)+blocks.bin.gz
- **6.52.13**（2026-08-27）批 14 accounting 观测 bundle 绑定冻结态内容寻址兜底：正式路径现物指纹不匹配（仅 size/sha mismatch 两种）时按收据记录的同一 size+sha256 到冻结件 `data/solana_observation_bundle_frozen.json` 寻址（哈希是身份、路径只是地址；兜底命中后深验零跳过），安全类失败（逃逸/symlink/缺件）不兜底、兜底失败回抛原错；方案 A 同族第六消费点（ARC handoff 第 2 发暴露：封账期收据绑定的正式路径被活观测占用）；SUITE 138 全绿
- **6.52.12**（2026-08-27）批 13 accounting 期望时点两态：中央选择器 `accounting_expected_target`（Solana 冻结态取 exact 收据冻结点、静态与 EVM 零变化），handoff verify/validate_sources/audit 块声明三消费面同深接入（audit 投影以深验成功为前提，异常回落原判）；方案 A 同族第五消费点（ARC handoff 实跑暴露：A0 会计核定产在封账点 vs verify 拿观测时点当期望）；SUITE 137 全绿
- **6.52.11**（2026-08-27）批 12 分布扫描器冻结态供应漂移容差：`load_supply` 的 `net>onchain` 静态硬拒改两态——漂移向仅当 supply_truth 收据 PASS/exit 0、diff 逐位复算相等、整数容差内（`drift*10000<=tolerance_bps*onchain`）放行并留痕 `supply_drift_raw`；静态向/快照闭合锚/分母语义零变化；方案 A 同族第四消费点（ARC A3 第 8 项实跑暴露：封账后 26,135 raw 微量销毁使冻结净额高于链上现值）；SUITE 136 全绿
- **6.52.10**（2026-08-26）批 11 五查冻结快照与活观测分家：发布深验 solana 同文件绑定改两态（静态态原语义逐字保留；冻结态哈希绑定案内密封冻结观测 bundle `data/solana_observation_bundle_frozen.json`，信封+观测深验+sha256/size 双绑三重防伪）；handoff 冻结态必进 data_map/artifacts；job spec supply --work-dir 分家防覆盖封账件（ARC 真实覆盖事故+密封指纹逐字节恢复驱动）；CT-SQDGAP-34；SUITE 135 全绿
- **6.52.9**（2026-08-26）批 10 五查 exact_reconcile 活链协议修正（方案 A·用户裁决）：第五查从"消费观测到的当前 slot"改为"钉账本缓存冻结点字面量"，观测点与冻结点的现值差由 supply_truth 10bps 容差兜底；runner 占位符校验反转＋receipt target 三层同深放宽（chain/token 全等、冻结 slot ≤ 观测 slot）＋深验既有正向绑定（receipt.as_of == cache finalized_upper_slot）考据确认；先红后绿 N1-N5＋CT-SQDGAP-33 防回流；SUITE 134 全绿
- **6.52.8**（2026-08-26）solana_observation jsonParsed 兼容：v0+ALT 交易在 jsonParsed 编码下公共 RPC（publicnode/api.mainnet-beta）不带 meta.loadedAddresses（地址已并入 dict 形态 accountKeys），原校验一律报错致五查观测在公共端点全断；改为仅当 accountKeys 为 str 键（裸 json 编码）时仍强制 loadedAddresses，dict 键豁免；ARC 五查实跑验证
- **6.52.7**（2026-08-26）批 9 repair 深验校验侧流式/惰性化：`validate_repair_bundle_deep` evidence 惰性读盘＋三 jsonl 流式＋SQLite 临时索引，语义与 reasons 逐字不变；16GB 本机首次跑通 15.4 万 slot 正式代发布（旧实现三轮内存超限被杀）；SUITE 134 全绿
- **6.52.6**（2026-08-25）批 8 SQD repair 生产者规模化：key 无关指纹与 key 池热降级、并发保序拉取、流式装配；两段提交锚定四项 producer 登记，SUITE 133→134
- **6.52.5**（2026-08-25）facts_gate 宏正则补连字符：ENT-PROJ 型实体键宏此前为死宏（不渲染且 G4 不检出、以字面量漏进正文），字符类扩 `-` 属收紧修复，flow spec 宏同源通道同步受益；SUITE 133 全绿
- **6.52.4**（2026-08-25）批 3c SQD census 字段契约修复：删除服务端拒收且无消费方的 `parentSlot`，两段提交锚定四项 producer 登记；SUITE 132→133
- **6.52.3**（2026-08-24）批 2d SQD stream 尾部跳块收口：HTTP 200 空体按严格三条件判定流结束、两段提交完成可考证 producer 登记；SUITE 131→132
- **6.52.2**（2026-08-24）F-007/F-008 LIT 回归修复收口：阵营序列按 series_format 固定堆叠语义，evm_v2 目录重放前补字符闸与集合闸；SUITE 129→131、契约 195→197
- **6.52.1**（2026-08-24）F-005 文档漂移更正：外部全量审查发现的三处 Solana reconcile v3 正向旧口径改为 v4 envelope／v2-v3 legacy 拒收，并新增 banned needle 防再漂守卫
- **6.52.0**（2026-08-23）Solana SQD 覆盖健康闸与修复生产者窄门收口：A2 升五查，wave v5／flow v3／wrapper v3／reconcile v4 同步，契约 175→194、SUITE 124→128；正式勘误跨源位置编号假象
- **6.51.0**（2026-08-20）labels v4.3：Arbitrum 730 行 CEX-only 初版建表并接通六表守卫，Base +51／ETH +1；修复 additions 重放 `source_snapshot_at` round-trip 断环；Arbitrum 仍为 exploration，不授予正式交接或审计发布
- **6.50.0**（2026-08-18）split-run 三段化＋刀 1 外包公告：新增 /token-analyze-3 装配段（−2 收口前移至报告正文＋装配工单，A5 装配独立 Opus 会话）；ET-1 报警证据采集前置 −1（停止线拆采集/定性）；刀 1 机械档扩为 14 项公告＋6 条纪律（唯一权威源）；新契约 CT-SEMANTIC-61/62、CT-BANNED-16，命令四元；版本号跳过 6.49.0（已被并行 SQD 工程占用）
- **6.49.0**（2026-08-18）Solana SQD transaction-net v4 五批根治：7 元组交易身份＋tx_digest 冲突硬拒、owner 双侧记账与输入卫生、正式/legacy 两态分立、采集摘要/producer 登记/invariant 闭环、ARC 双窗口真采与破坏性注入收口；冻结 parts 域内实证 DISTINCT 损失 11,502 行/8,487 组（最高 23 倍），124,816 更正为两版全史行数差的混合口径
- **6.48.1**（2026-08-17）单元3 盲审消化轮＝三单元收口工程收官：盲审判 CONDITIONAL（闸体 9 项 DEFENDED 全攻不破），消化本单元引入债（签发点 schema 字面量收敛、怪写法等价重构、--out/--receipt 同路径前置拒、文档"保证覆盖全部 segments"过度声称收窄到 hypersync 签发者＋方案B 永久登记维护债申明）；BREACH-01（SQD 侧同 schema 签发者无 TOCTOU，非本单元引入）等四项移交第四单元候选清单
- **6.48.0**（2026-08-17）HyperSync CSV 同哈希续采闸·方案B（三单元收口工程·单元3）：正式 CSV 仅允许同一启动冻结哈希续采（脚本升级须封盘另开新 channel 段，preflight 多 channel 拼接既有支持）；TOCTOU 启动冻结+写前漂移拒签+receipt 用启动哈希；hash-wide REVOKED 拒启动；resume 读入接严格 JSON+全字段类型收口；cea82c77 按唯一签发 protocol 补登（考证 2d69373）；全盘清点 105 份存量回执全单段零迁移
- **6.47.1**（2026-08-17）单元2 盲审消化轮：4 BREACH 关洞（收据标签去"验证"语义防零成本洗白、维护纪律按 protocol 逐条补登+断链固化测试、inventory 残件分类报错给人工出路、staged_capture 首采三态放行）＋5 WEAK 修复（.DS_Store 唯一豁免三处等深、REVOKED 压过当前脚本、recovered 身份收据透传、symlink 根死代码、CSV 回执接严格 JSON）＋1 注（迁移哈希定性留痕）；APU 0801 原始形态全链重演练闭环
- **6.47.0**（2026-08-17）HyperSync Parquet done v4 逐段采集者归属＋C12 显式恢复（三单元收口工程·单元2）：每段 done 带 collector{path,sha256} 启动冻结哈希+写前 TOCTOU 复验；旧段迁移 legacy-unattributed 三件套（源 schema/迁移前哈希/migrator 可验）+原生/迁移判别联合互斥；identity 自动签发收严至真空目录、遗留目录走 --recover-identity 签 hypersync-capture-identity/v2（recoverer 取代 collector、lineage=unknown），先 recover 后 refresh；collector_history 按 protocol 过滤（REVOKED 保持 hash-wide）；U1 盲审三条跨单元传染修复随单落地；APU/EGL1/NES 实件演练三态闭合
- **6.46.1**（2026-08-17）单元1 盲审消化轮：2 BREACH 关洞（重复 JSON 键人机分裂伪装、producer 历史 protocol 硬编码致 v3 plan 可挂 v2 时代签名）＋7 WEAK 修复（schema 分派 fail-open 转显式白名单、v2 点拒 v3 说谎字段、单源守卫恢复全局语义等）；五项维持两项旧账另立裁决在案；NES 存量与盲审向量回打全绿
- **6.46.0**（2026-08-17）anchor-plan v3 机器字段与 producer 历史登记（三单元收口工程·单元1）：余额点必带 balance_block_source 正向白名单、balance/tx 严格 XOR，kind 中文文案退出一切语义判定；新建 producer_history 六字段登记表修复存量 receipt producer 哈希深验基线即断；v2 存量不重签，语义重放 schema-aware 投影兼容，NES 三份存量件先红后绿实证
- **6.45.1**（2026-08-17）NES 双链首案实证后四修复、四批收口：R-1 anchor_point_contract 四处等深与 block_of fail-fast；R-2 collector_history 六字段迁表并按 HEAD 祖先定案；R-3 identity 三入口认历史、两键规范形与维护补登；R-4 producer 真件直过发布闸及缺失/矛盾负例
- **6.45.0**（2026-08-15）三 AI 并行修复 v6.44.0 review 14 findings 全处置：g1 边界守卫六项（handoff 案根 containment/审计闸 report 必填/跨分区三元组等式/command v3/risk_flags 白名单/文本卫生守卫＋Solana 原串保真）、g2 证据链四项（观测拒空 code/对账五路深重验/GMGN 黄灯查证说明制/Arbitrum 探索档恢复）、g3 通道与文档四项（A0 探索预检两阶段/SQD 收紧＋Alchemy 正式除名/F-05 用户裁决不加闸如实写边界/F-13 文档对齐）；R10-15/18 转 CLOSED 现役 12；三组独立 opus 盲审全收口
- **6.44.0**（2026-08-15）EVM 链上观测锚：三链正式纵切片真跑 bundle producer，accounting v2/supply_truth v4 双收据与 shared/handoff N-2 闭合；F-02 CLOSED、F-03/R10-9 MITIGATED 仍 OPEN；独立盲审 31 伪造向量全拒 PASS
- **6.43.0**（2026-08-14）批 3 弱闸三线收口：A4 blocker 语义联动+10 门槛+entrypoint 身份（F-01→R10-16/17）、deploy-sync 严判（F-04→R10-5）、env_check 机械派生（F-05→R10-6）、R10 台账同步+自洽守卫（F-07）；三轮盲审+三轮消化全闭（execution ledger 哈希链等 7 项收编），R10-5/6/16/17 转 CLOSED 现役 15
- **6.42.0**（2026-08-14）批 2 三线收口：F-10 waiver 三段硬顶＋用户超顶批复、F-02 对抗复核结构化 v3、F-09 solana-reconcile/v3 身份链与 PYTHIA 实证；三轮盲审残留锚、R10 清账/新登记及文档边界统一封口
- **6.41.0**（2026-08-14）批 1 五项修复收口：RV-07 receipt supersede＋五出口真 FAIL 落盘；RV-04/RV-17 proxy 单源解析＋stake_decode fail-closed；F-03 replay 三引擎 gate 语义统一；F-01 图 1 白名单/legend receipt/A5 v3 双层信任根；F-04 四入口位置 token 移除且 sentinel 不进输出
- **6.40.0**（2026-08-13）六视角 BLOCK 修复工程 A-D 四批收口：发布收据验证链（F-01/02）＋分布扫描族（F-03/08）＋阵营序列 producer 链（F-04/05）＋flip 裁决收据制（F-06）/refresh 真事务（F-07）/销户审计收口（GPT-F-06）＋台账八项＋distribution-scan/v2；R10 存量台账本轮未修、台账保留（r10_ledger.md）
- **6.39.5**（2026-08-12）distribution 语义重验剔除记录性 upstream_receipts（split-run G8/audit_release_gate 三闸死环修复，TAG 案实撞；同步补 6.39.4 漏 bump 的 pyproject）
- **6.39.4**（2026-08-11）provenance 敏感性闸粒度修复：尘埃锚点线（<0.01% 供应不入翻转判定）＋ --acknowledge-flip 翻转书面确认通道（freeze 重放同参还原）
- **6.39.3**（2026-08-09）accounting_gate 加 --as-of-block 目标块绑定（存量案重跑 tip 漂移死锁修复）
- **6.39.2**（2026-08-09）entity_source_trace 进货单并列序非确定性修复（freeze 重放对账假阴性）
- **6.39.1** 2026-08-09 分布扫描 validate 可移植性修复：semantic_payload 剔除 labels_manifest 宿主绝对路径（内容漂移仍由 sha256 抓）
- **6.39.0** 2026-08-09 APU 案 ANOM-012 存量迁移三工单：replay_stats 覆盖截止块契约闭合（三引擎单点等深）、太古 done 官方迁移全链、旧 −1 产物格式迁移命令 migrate_legacy_case
- **6.38.0** 2026-08-09 供给真值闸补齐 dead 沉没形态：sink 统计单源与逐地址闭合、receipt v3、verify_recon 余额恒等式修正、APU/GNT 对照与非零 dead 纵向回归
- **6.37.0** 2026-08-09 R9 收敛修复工程收口：五 finding 四批闭环（Solana 观测协议+mainnet 实证/anchor 语义重放/双采集器进程边界 fail-closed/attestation 可执行化+四链纵切片）；F-B4-01 静态元守卫经用户裁决降级诚实记账；两轮盲审=台账重放 43/49 一致（full-F-03 豁免手续补全）+六视角六条存量 finding 立 R10 候选
- **6.36.0** 2026-08-06 结构收敛工程阶段 3+4 收口：receipt kernel+独立 validator、EVM/Solana 五件垂直切片迁移、net.py Result+curl 后端；R7 十五项 15/15 全绿、四零机器复算达成（kernel 采用 5/35 逐版推进）
- **6.35.0** 2026-08-06 结构收敛工程阶段 1+2：invariant manifest 实施面分母+R7 十五项先红测试防装死隔离；受控 runner 编排执行四查+聚合器只认 runner 绑定；链能力注册表单源（同名异义 KNOWN_CHAINS 消灭），R7-01/05/07 转绿
- **6.34.0** 2026-08-06 六视角首战修复轮：13 项五批全修（发布证据链 receipt 化/采集器原子产物/标签门禁等深/正式输入必填/文档口径），验收返工 1 项 risk_flags 规范化
- **6.33.0** 2026-08-06 维护方法论文档化：六视角 review 清单与修复工单模板沉淀为维护件 maintenance-review-repair.md（零判据变更）
- **6.32.0** 2026-08-06 第五轮外部审查 13 项修复：标签发布与采集器 fail-open 关闭、密钥取用契约统一、SKILL/casebook 路由漂移收口
- **6.31.0** 2026-08-06 第四轮瘦身修复：旧案硬编码清除、孤儿与 SQD v1 退役、运行时文档按需化、契约 ID 快照封口
- **6.30.0** 2026-08-05 第三轮瘦身收口：入口按需路由、退役资产迁档、案例史外置、地址簿单源与 manifest 防线合一
- **6.29.0** 2026-08-05 第二轮修复工程第 4 步：canonical 契约注册表与 SKILL 二级路由
- **6.28.0** 2026-08-05 第二轮修复工程第 3 步：现役文档案例史迁出、casebook 六字段收敛、报告管道与旧阶段名修正、CHANGELOG 活跃窗口兑现、确认死物删除
- **6.27.0** 2026-08-05 Arbitrum 降为探索支持：
  正式编译全链拒绝，正式链声明/发布闸/标签能力三向闭合守卫
- **6.26.0** 2026-08-05 三项 P0 活故障修复：手工标签唯一真源与 suite 守卫、A3 依赖序统一、既有报告净室复核入口补齐
- **6.25.0** 2026-08-05 references 长行保序拆分（瘦身第 6 步）：30 条语义断行，3 条 Markdown 表格行按结构约束保留
- **6.24.0** 2026-08-05 零引用脚本归档与 Solana gas 双实现合并（瘦身第 5 步）：gas_origin 单入口保留限页/全量双模式与字段闸
- **6.23.0** 2026-08-05 深入阅读清单 manifest 化（瘦身第 4 步）：现役路由与维护文档双向对账，维护件不再被 lint 强迫进入口
- **6.22.0** 2026-08-05 archive/ 考古区分层（瘦身第 3 步）：旧 CHANGELOG、评测题库与已闭环冲突审计快照退出执行路由
- **6.21.0** 2026-08-05 数据管线两册案例史外移与重复合并（瘦身第 2 步）
- **6.20.1** 2026-08-05 修 5 处阻断级文档漂移（A4 前禁写报告冲突/easy 残留/惯犯回灌 docstring/批量预采集残留/旧 Par 路线历史降级）＋docs_lint 增中文禁词与 Python module docstring 扫描

更早版本（6.20.0 及以前）详见 `archive/CHANGELOG-archive.md`。

## [6.53.3] - 2026-08-30 — 序列来源链登记路径兜底收窄为唯一案根（盲审 R3 P1）

- **出处与根因**：codex 盲审发现 6.53.2 的登记路径兜底把 `search_dirs` 每个 base 都当 containment 根；序列位于案根时，`[case_dir, case_dir.parent]` 会把案件父目录当根，攻击者可登记 `sibling-case/data/x.json` 并以相邻案件实物的 size/sha256 通过三验，打穿发布闸“只吃本案产物”的隔离保证。
- **设计与实现**：`_resolve_ref` 新增仅限关键字的 `case_root=None`；两层 basename 逻辑逐字保留，登记路径兜底仅在显式给定唯一案根时执行，只构造 `case_root / registered` 一个候选，并继续执行相对路径卫生、逐段 symlink、resolve containment、is_file、size 与 sha256 全等校验。未给案根时不执行兜底，错误文案也不声称尝试过登记路径。
- **消费面与防回流**：series sidecar 的 `camps_spec`、`final_balances`、`inputs.*` 均由 producer 只登记文件名，故 `load_series_with_sidecar` 不传案根并恢复批 16 前语义；只有 reconcile v4 收据 inputs 传案根，显式值优先，否则仅当收据直属 `data/` 时推导其父目录为案根。发布闸显式传 `case_dir`；`state_from_facts.py` 不改，沿 `data/` 推导路径。
- **测试**：R3 RED 真实返回相邻 `caseB/data/x.json`；修后 R2 覆盖显式本案根与 `None` 双拒，既有 R1/N1–N6 保持，新增 N7 `data/` 推导深层命中、N8 案根收据不推导、N9 显式案根覆盖推导值。发布闸完整案回归与版本/CHANGELOG/全量 suite 结果见 `batch16_done.md`。
- **盲审与验收**：codex 盲审 R3 1 条 P1（兜底越出本案）已消化；白名单内离线施工，不改 `state_from_facts.py`、独立深验器、共享收据或发布闸其它行，不 commit。
- **成本-质量指标**：生产实现 1 轮；外部网络调用 0；新增 suite 入口 0；新增测试场景 4（R2、N7–N9）；生产 schema 改动 0；传播级数字错误 0。

## [6.53.2] - 2026-08-30 — 序列来源链登记路径按案根解析兜底（sqd_repair 修复缓存深层路径）

- **出处与根因**：ARC −2 正式编译在 1.5 小时后被 `reconcile.inputs.soltx_meta` 缺件阻断；`solana-reconcile/v4` 按案根登记 `data/sqd_repair/<sha>/gen-<gid>/soltx-….repaired.meta.json`，深验器能按完整相对路径解析，但 `camp_series_provenance._resolve_ref` 只取 basename 到序列目录与案根两层查找，所有使用 sqd_gap_repair 深层修复缓存的 Solana 案都会结构性失败。
- **设计与实现**：原有两层 basename 搜索、symlink 拒收、size/sha256 三验及首命中即返回/不匹配即拒的代码段保持不变；仅在两层均未命中后，按 `search_dirs` 原顺序尝试登记路径。兜底只接受非绝对且无空段、`.`、`..` 的相对路径，从 base 起逐段拒 symlink，`resolve()` 后强制 containment，并在首个实物命中时全等复验 size/sha256；sha256 仍是权威身份。
- **消费面与防回流**：调用点、resolver 等值检查、`solana_exact_validate.py` 与既有测试均未改；深层 meta 返回原登记实物，故 `resolver_meta_path.resolve() == meta_path.resolve()` 继续成立。全库同族核查发现 `audit_release_gate._recon_owner_snapshot` 静态段也只按 basename 搜索，遵守批 15 禁改边界仅记录待调度裁决；其它同族点按各自登记协议分类，未扩改动面。
- **测试**：先红精确复现旧异常“两层内都找不到”；新增 7 组覆盖 sqd_repair 深层正例、`..`、绝对路径、中间目录 symlink、size/sha256 错配、basename 两层老形态与命中错哈希不降级、`registry_anchor_check` 深层 meta 与 resolver 同实物。N6 使用真实独立深验器；因完整 repaired cache producer 布局成本过高，按工单允许仅 monkeypatch `resolve_formal_cache` 返回该深层 meta，路径等值检查与其余 registry 逻辑真实执行。SUITE 141→142。
- **盲审与验收**：白名单内离线施工；点名既有回归、版本一致性、CHANGELOG lint 与完整 run_all 结果见 `batch16_done.md`，允许 loopback 的本机全套由调度方复跑。
- **成本-质量指标**：生产实现 1 轮；外部网络调用 0；新增 suite 入口 1；新增测试场景 7；生产 schema 改动 0；传播级数字错误 0。

## [6.53.1] - 2026-08-30 — 发布闸 B-7 三账对账源与 series cutoff 冻结态投影

- **出处与根因**：批 10–14 已把六个动态 Solana 冻结账消费点接到 `accounting_expected_target`，但发布闸 B-7 仍从 supply observation bundle 取观察 owners＋wrapper 块，series binding 仍把 wrapper 块当 cutoff；exact=500、wrapper=501 时，按冻结账建三账会被时点与逐址等值拒绝，冻结 `holders_snapshot_meta` 也会被 series cutoff 拒绝。
- **设计与实现**：新增 `_frozen_consumer_target`，先走 `validate_reconciliation_report(..., return_receipts=True)` 深验，再由 `accounting_expected_target` 选冻结目标并与 accounting 自闭合；B-7 以 `_bound_case_ref` 打开 exact 收据 `inputs.holders_owners`，保留案根、绝对案内路径、symlink、size、sha256 全部硬闸；series 只把中央选择器的冻结 `as_of_block` 投到既有 wrapper chain/token 表示。深验结果在单次 `run()` 内缓存，B-7/series/跨分区投影共用一次深验。
- **消费面与防回流**：动态 Solana 三账与序列消费冻结点，分布 initial/final 仍消费 observation owners；真静态 Solana 与 EVM 沿原 wrapper 路径不变。冻结深验、accounting 自闭合、exact 实物任一失败均停止该消费点，不回落观察 owners；`holder_distribution_scan.py`、`camp_series_provenance.py`、三账本体与共享深验器均未改。
- **测试**：R1 修前精确命中 B-7 时点不一致＋逐址不等值且无其它错误；新增 10 组覆盖 live 三账反例、冻结件篡改、symlink、真静态、伪静态 accounting、案内绝对路径亦被深验器拒绝（fail-closed）、案外绝对路径拒绝、默认/显式分布快照、完整动态 new-analysis 零错误及错 cutoff 变异拒绝；文档、版本和既有 EVM/静态发布闸回归纳入验收，SUITE 140→141。
- **盲审与验收**：@CX 施工前复核＋codex 盲审 R1 1 条 P2（N5 假绿）、R2 1 条 P2（深验重复扫描）均已消化＋Fable 独立验收；具体后续轮次由调度方验收后补。
- **成本-质量指标**：生产实现 1 轮；fixture 路由校准 2 次后取得完整动态红；外部网络调用 0；新增 suite 入口 1；新增测试场景 10；生产 schema 改动 0；传播级数字错误 0。

## [6.53.0] - 2026-08-27 — 持仓分布图升级为 matplotlib 双轴带标签图

- **出处与根因**：BTW·BSC 报告的“当前持仓分布”最高蓝柱实际表示地址数最多的空投残留档，却因旧 `write_png` 只是 800×420 灰底蓝柱裸 PNG、没有轴/刻度/标题/图例，被读者误当成大筹码档；问题在表现层，不在分布判定或 scan JSON。
- **设计与实现**：新增纯数据 `_chart_series`，按 bin index 对齐地址数、泊松期望人数、该档 raw 占净供应百分比与从数据推导的对数横轴刻度；`write_png` 改为函数内导入 matplotlib/chart_style，输出 1800×840 双轴中文图，low_sample 输出居中说明；删除 `struct/zlib` 裸 PNG，异常路径以 `finally` 关闭 figure。
- **消费面与防回流**：`write_png(path: Path, scan: dict) -> None` 签名、唯一调用行、三个 PNG 路径、scan/record-round/analyze/validate/semantic 判定代码及 payload 均不变；final 仍由真实 `--stage final --round 1` 产轮次图，再由 record-round 拷到唯一终版路径；缺 matplotlib 显式失败，不允许静默降级。
- **测试**：先红证明旧实现无 `_chart_series`、尺寸仅 800×420 且 matplotlib 毒丸仍会产降级图；后绿覆盖零值档保留、百分比分母、对数刻度、initial/final 标准生产链、无 `base_bins` 的 low_sample、PIL 合法性与 1800×840；点名的 distribution gate、A4 gate、repair batch C/D 全绿，SUITE 139→140。
- **盲审与验收**：按小改裁量免两轮盲审，以 @CX 施工前计划复核＋codex 施工后盲审＋Fable 独立验收替代；版本位按书面规则升次版本（生产行为改变＋复盘驱动）。
- **成本-质量指标**：施工 1 轮；外部网络调用 0；新增回归组 1；判定逻辑改动 0；payload/schema 改动 0；分析结论 0；传播级数字错误 0。

## [6.52.15] - 2026-08-27 — F-03b 共享 SQD 地图复用失败分级与分段补扫

- **出处与根因**：F-03 修复后 ARC live 实测共发出 92,643 个 recheck 请求，其中 91,461 成功，1,182 失败全部来自 SQD 服务端限流（529×1,034、429×148），零数据 mismatch。旧规则把请求失败和数据不一致都当成整图不可信，导致大地图在真实限流环境下几乎必然放弃复用、退回全扫。
- **失败三分级**：每个 range 明分 verified、mismatch、request-failed。成功响应只要有一处 slot 值不一致，仍按 `recheck-mismatch:<slot>` 整体回退；请求失败在首轮结束后统一重试一次，仍失败只把该段剔出复用并转 full 补扫；canary 段请求仍失败或值变化，仍整体回退，不允许部分复用。
- **覆盖声明与防回流**：map-reuse 不再用一条大区间笼统声称复用，而是按实际验证通过的案件子区间逐段声明；案外或跨案件边界的 recheck 行一律撤销 `counts_coverage`。新增受控杀变异测试，模拟恢复案外 coverage 声明时必须转 RED，证明测试能咬住这条边界。
- **审计字段**：shared_map 新增 `unverified_ranges` 和 `recheck_stats`（verified/unverified/retried），`reused_ranges` 改记实际复用的子区间；retry 后得到 mismatch 只进入 mismatch 路径并触发整体回退，不污染 unverified 列表或计数。
- **盲审与验收**：盲审第 1 轮判 BLOCK 的两项发现已消化——retry mismatch 审计误分类修正，案外/跨界 coverage 以端到端断言和杀变异测试封口；第 2 轮 PASS。SUITE 维持 139 项，F-03 既有测试文件内测试组由 9 增至 15，未新增 suite 入口。
- **成本/质量指标**：live 实测 6.3 小时；外部网络调用 0（本登记批）；资产改动 0 字节；新增 suite 入口 0；分析结论 0；传播级数字错误 0。

## [6.52.14] - 2026-08-27 — F-03 共享 SQD 地图复用闸身份与重验闭环

- **出处与根因**：codex 六视角 review 2026-08-27 将 F-03 判为 P1；问题由提交 b005a468 在修复中引入——复用闸把会随链前进的动态 head 当成不可变身份，真实 head 前进会误退全扫，也没有用历史块锚证明当前端点与冻结资产仍是同一段历史。
- **身份闭环**：身份拆为稳定字段（数据集/起点/实时性）、动态 head 和未知字段三类；稳定身份严格全等，未知字段 fail-closed，历史锚 slot 的 block hash 必须当次实测一致，finalized head 只准单调不倒退，查询模板哈希必须绑定一致。
- **重验与回退**：canary、candidate、refuted 等全部已知点只做连续区间合并后并发重验；任一请求、身份或重验失败都整体回退全扫，不部分复用。若复用途中失败，本轮已经成功的 recheck 行仍留作审计事实，但撤销其 `counts_coverage` 覆盖声明，保证最终 ledger 声明与实际交付 counts 字节来源一致。
- **消费面与防回流**：`validate_shared_map` 扩到与生产复用闸同深；`validate_coverage` 按 D1 用户裁决接入 `producer_history`，coverage 与原子 CURRENT pointer 两协议分别登记同一冻结探针；新增 CT-SQDGAP-35 和端到端/并发/类型/失败回退矩阵。既有 `assets/sqd-solana-coverage-map/20260827` 三件零字节改动，升级后可立即复用。
- **盲审与验收**：盲审第 1 轮判 BLOCK，三项发现（失败 recheck 覆盖声明、稳定身份类型洗白、anchor transport 裸异常）全部消化；第 2 轮 PASS。两段提交协议第二段完成版本面与 producer 登记，SUITE 138→139。
- **成本/质量指标**：外部网络调用 0；资产改动 0 字节；新增 suite 入口 1；分析结论 0；传播级数字错误 0。

## [6.52.13] - 2026-08-27 — 批 14 accounting bundle 绑定冻结态内容寻址兜底（方案 A 同族第六消费点）

- **根因（ARC handoff verify 第 2 发暴露）**：A0 会计核定收据按 path+size+sha256 绑定其观测 bundle（当时正式路径=data/solana_observation_bundle.json、内容=封账观测）。方案 A 后该路径被五查活观测占用且 supply_truth 也按此路径绑活内容——同一路径被两份合法收据绑定两份不同内容，案级无解；`_bound_case_ref` 按路径现物验哈希必炸 size mismatch。
- **修正**：solana accounting 分支局部兜底——`_bound_case_ref` 抛错且错误恰为内容指纹类（size/sha mismatch 两种字符串精确匹配）时，以**收据记录的同一 size+sha256** 改址冻结件重试（复用通用绑定器，指纹权威不变=字节同一才认）；安全类失败（路径逃逸/symlink/缺件）直接回抛不兜底；兜底失败回抛原错。命中后 validate_observation_bundle 深验+slot 绑定检查零跳过。`_bound_case_ref` 本体与 EVM 分支零变化。
- **防回流**：先红后绿 R1（ARC 同形夹具）＋9 项测试（含冻结件被改 1 字节拒/缺件拒/安全失败不进兜底/静态与 EVM 零变化回归）。
- **验收（Fable）**：codex 施工约 20 分钟；本机 run_all 138 全绿；兜底触发条件白名单式（两种精确错误串）审查通过。
- **成本/质量指标**：外部网络调用 0；新增测试 1 文件；分析结论 0；传播级数字错误 0。

## [6.52.12] - 2026-08-27 — 批 13 accounting 期望时点两态（方案 A 同族第五消费点）

- **根因（ARC handoff verify 实跑暴露）**：A0 会计模式核定天然产在封账点（ARC as_of=440368381、checked_at=封账时刻），handoff verify 却把五查 wrapper 的观测时点（441940997）当 expected_target 传给 `validate_accounting_receipt` → canonical 全等必炸 "accounting target mismatch"。静态案两时点相等从未暴露。
- **修正**：新增中央选择器 `accounting_expected_target(recon_target, receipts)`——EVM→wrapper 不变；Solana 要求 exact 收据在场且 chain/token 全等、exact≤wrapper（违反即拒），严格早于才返回冻结点。三消费面同深接入：handoff `_verify_light_schema`、shared `validate_sources`（−3 路径；EVM 分支与 Solana 静态分支原语义逐字保留，A4 seal 绑定时点随 accounting target=冻结账本语义）、audit_release_gate 块声明去重（冻结点投影仅在深验成功后授予，异常回落原判 fail-closed）。`validate_accounting_receipt` 本体校验零放宽。
- **防回流**：先红后绿 R1（ARC 同形三时点夹具）＋N1 accounting 双非时点拒＋N2 chain/token 错配拒＋静态/EVM 纵切片回归零变化。
- **验收（Fable）**：codex 施工约 30 分钟；本机 run_all 137 全绿；audit 投影的 fail-closed 方向核查（except 回落=更严）。
- **成本/质量指标**：外部网络调用 0；新增测试 1 文件；分析结论 0；传播级数字错误 0。

## [6.52.11] - 2026-08-27 — 批 12 分布扫描器冻结态供应漂移容差（方案 A 同族第四消费点）

- **根因（ARC A3 第 8 项实跑暴露）**：`holder_distribution_scan.load_supply` 硬拒 `net > onchain`——静态时点假设（冻结重放净额不可能高于链上现值）。方案 A 冻结态下 onchain 取自观测时点，封账后一笔 26,135 raw 微量销毁使 onchain(现在) < net(冻结点)；supply_truth 闸自己按 10bps 容差判 PASS（diff_bps=0.0），扫描器却把这份 PASS 收据在门口再拒一遍 → distribution initial 全案 BLOCKED。
- **修正**：漂移向（net>onchain）仅当同一收据 PASS/exit 0（既有 :235 检查）＋`diff` 字段与 net−onchain 逐位复算相等＋整数容差 `drift*10000 <= tolerance_bps*onchain` 时放行，并在 denominators 留痕 `supply_drift_raw`（v2 兼容可选字段）；任一不满足原句硬拒。静态向、Solana 快照闭合精确等式（容差 0）、分布分母语义零变化。
- **波及面核查（关到同一深度）**：全库 rg 确认无第五个静态方向假设点（supply_truth_gate 生产者/shared_release_receipt 深验/发布闸 sha 比对，行号在 batch12_done.md）。
- **防回流**：先红后绿 R1（ARC 同形数值）＋N1 diff 失配拒＋N2 边界外 1 raw 整数判定拒＋N3 非 PASS 拒＋N4 EVM/Solana 静态零变化；契约不新增编号（v2 向后兼容留痕，CT-DISTRIBUTION-01 既有锚不变）。
- **验收（Fable）**：codex 施工约 25 分钟；本机 run_all 136 全绿；"PASS/exit 0"声明与 diff 表面不符疑点核实为既有代码非虚报。
- **成本/质量指标**：外部网络调用 0；新增测试 1 文件；分析结论 0；传播级数字错误 0。

## [6.52.10] - 2026-08-26 — 批 11 五查冻结快照与活观测分家（方案 A 收尾层）

- **根因（ARC 五查实跑第 4 发暴露，活链死结最后一层）**：发布深验要求第五查消费的持有人快照与 supply 观测产物**同一文件**（防伪本意），方案 A 后两者天然分裂（观测=链上现在，第五查=冻结点）；同文件绑定逼第五查吃活快照 → 活跃币必然 mismatch（ARC 实测 966 户差=封账后 6 天正常交易）。更重者：supply 观测按旧 job spec 写 `--work-dir data`，多轮重跑将封账快照三件与三 inputs **全部覆盖**为活链版（真实事故）。
- **恢复（验收方，全程哈希对照密封指纹）**：五件从案内密封复合快照/同构模板逐字节重建全部 sha256 MATCH；唯 `_gpa_raw_all.json` 封账版（43MB，含 18 万户全量）不可重建（复合快照仅存 4.6 万非零行），待本机 TM 快照提取（已请用户协助）。
- **修正**：①shared_release_receipt 同文件绑定改两态——静态态（exact==wrapper 时点）原代码原文案逐字保留；冻结态（exact<wrapper）改为哈希绑定案内密封冻结 bundle：信封（inputs 实物重哈希）＋validate_observation_bundle 深验（producer/genesis/closure/holder_outputs 文件级三验）＋owners sha256+size 双绑，防伪强度≥原路径同一；②handoff generate/verify 共用 required-set，冻结态必进 data_map/artifacts；③文档两态契约+job spec 分家要求（supply --work-dir 独立子目录）。
- **防回流**：先红后绿 R1＋N1-N5（缺件/target 错配/指纹错配/静态零变化/handoff 清单）＋CT-SQDGAP-34；ARC 实物实测新闸精准咬中唯一真实缺口（gpa_rpc 双 mismatch）＝判别力真事故验证。
- **验收（Fable）**：codex 施工（沙箱 133/135，2 项 loopback 环境）；本机 run_all 135 全绿；防伪链闭合逐环核实（validate_receipt 实物重哈希+B-1 holder 三验+canonical bytes 对账）。
- **成本/质量指标**：codex 单会话约 50 分钟＋Fable 验收与案内恢复；外部网络调用 0；新增测试 1 文件+契约 1 条；分析结论 0；传播级数字错误 0。

## [6.52.9] - 2026-08-26 — 批 10 五查 exact_reconcile 活链协议修正（方案 A）

- **根因（ARC 首个真实活链案暴露）**：五查 runner 强制第五查消费 `{observed_as_of_block}`（观测到的链上当前 slot），而生产者 `replay_edges.py` 硬闸要求对账 slot == 账本缓存 `finalized_upper_slot`（冻结点）。活链每 0.4s 前进一格，"当前"结构性追不上"冻结点"——两规则互斥，第五查在任何活跃币上必死。此前只有静态夹具跑过（观测点与冻结点人为对齐）未暴露。协议内部亦自相矛盾：supply_truth 以 10bps 容差接受时点差，exact_reconcile 却禁止任何时点差。
- **修正哲学（用户 2026-08-26 裁决方案 A）**：第五查改为对冻结点对账（严格性不降：仍为冻结点上 45,883 owner 级全量逐值相等）；观测点与冻结点的现值差继续由 supply_truth 容差兜底。
- **三层同深**：①runner `_validate_spec` 前三查维持占位符强制，exact 反向禁止占位符、要求恰一个 `--as-of-slot` 非负 ASCII 整数字面量（isdigit 单用会放行非 ASCII 数字，Fable 验收攻击 A5 抓获后亲修收紧）；②runner `run_job` 与公共深验 `validate_reconciliation_check` 对 solana exact 同步放宽 receipt target（chain/token canonical 全等、冻结 slot ≤ 观测 slot），其余 check 与全部 EVM 维持全等；③生产者硬闸不动（SHA-256 与 HEAD 全等验证），深验既有正向绑定（`solana_exact_validate.py:1919-1934` receipt.as_of == 所绑 soltx_meta.finalized_upper_slot）考据确认为防"旧时点收据冒充"的权威闸。
- **防回流**：先红后绿（R1 红证据留档）＋N1-N5 负向守卫两层各测＋EVM 回归＋契约 CT-SQDGAP-33 登记；文档（analyze-workflow §5/scan-schemas）大白话写明"前三查问链上现在、第五查问冻结账本自洽"。
- **验收（Fable）**：codex 施工（沙箱 132/134，2 失败纯属沙箱禁 loopback）；Fable 本机 run_all 134 全绿×2（施工树＋亲修后终树）、6 发边界攻击 5 拦 1 化妆级瑕疵亲修、深验绑定逐行核实。
- **成本/质量指标**：codex 单会话约 40 分钟＋Fable 验收；外部网络调用 0；新增测试 3 文件扩展＋契约 1 条；分析结论 0；传播级数字错误 0。

## [6.52.8] - 2026-08-26 — solana_observation jsonParsed 编码兼容（loadedAddresses 豁免）

- **根因**：观测器 `_account_keys_and_writable` 对带 addressTableLookups 的 v0 交易一律强制 `meta.loadedAddresses` 存在；但 jsonParsed 编码下节点把地址表解析结果直接并入 `accountKeys`（dict 形态、带逐键 writable），公共 RPC（publicnode / api.mainnet-beta）此时可完全不带 `meta.loadedAddresses`——键集已完整却被误判缺失，五查 supply 观测在公共端点对含 v0+ALT 交易的块全断（ARC 五查实跑首次暴露；Helius 大 GPA 政策墙迫使观测改走 publicnode 后触发）。
- **修法（3 行收窄豁免）**：仅当 `accountKeys` 为 str 键（裸 json 编码，地址表确需 loadedAddresses 补全）时维持强制报错；全 dict 键（jsonParsed）豁免。dict 分支后续 writable 归并逻辑不变，语义零放宽——裸编码缺字段仍 fail-closed。
- **验收（Fable 本机）**：ARC 五查 runner 实跑通过（supply 观测 45,883 owner 快照成功、四查 PASS）；run_all 全量通过。
- **成本/质量指标**：Fable 亲修 3 行；外部网络调用＝ARC 五查实跑；新增测试 0（观测契约既有守卫覆盖）；分析结论 0；传播级数字错误 0。

## [6.52.7] - 2026-08-26 — 批 9 repair 深验校验侧流式/惰性化

- **根因（批 8 F4 的同族缺口）**：生产侧装配已流式化，但发布必经的 `validate_repair_bundle_deep` 仍整载全部产物——evidence 6.5 万文件全量驻留字典、`slot_index_map.jsonl` 2.3GB 整载为列表——ARC 正式代（153,667 slot）深验在 16GB 本机连续三轮内存超限被系统终止（EXIT=137，采样栈显示大部分时间在 gc 遍历千万级对象图），发布路径完全不可用。
- **改造（语义零变更）**：evidence manifest 仍逐项路径/哈希/JSON/canonical 校验但不驻留内容，后续按 slot 惰性读盘（LRU=2）；`repair_layer`/`slot_index_map`/`rpc_ledger` 三 jsonl 逐行流式校验，跨行聚合仅留紧凑集合/计数；有序代按 slot 流式联结 map 与 base edge，乱序输入走标准库临时 SQLite 回退保留旧排序语义；GID 增量哈希流式消费；批 7 全部加固检查与 reasons 文本逐字保留；仅标准库无新依赖。
- **验收（Fable 本机）**：三守卫（sqd_gap_repair/批7缺口/批8规模化）复跑全绿、run_all 全量通过；施工方 HEAD 旧实现 vs 新实现同一 formal 夹具四情形逐字段等价；真实代终验＝runner 第四轮直接用新实现完成正式发布（80 分钟、入口阶段峰约 8.4GB 后回落 3-5GB 稳定，旧实现死于 12GB+；`status=published`、repair_edges=83、CURRENT verdict=PASS）。峰值超工单 6GB 期望值但发布完整跑通，目标本质（16GB 本机可发布）达成。
- **成本/质量指标**：codex 单会话施工约 1 小时；外部网络调用 0；新增测试 0（既有守卫覆盖）；分析结论 0；传播级数字错误 0。

## [6.52.6] - 2026-08-25 — 批 8 SQD repair 生产者规模化

- **根因一（换 key 指纹断裂）**：live plan 原先对含 key 的完整 endpoint URL 取指纹，换免费 key 会改变 plan digest 与 pending 目录并使既有 ledger 校验失败，配额接力无法续跑；现改为 public endpoint 的 key 无关指纹，并用 key 池轮转及 quota 热摘除保持同 plan 原位续跑。
- **根因二（串行 15 天不可行）**：153,667 个候选按实测约 428 slot/h 串行需要约 14.9 天；新增默认 1、可显式调高的有界 worker 池，slot 内调用顺序不变，主线程严格按 candidate 顺序落 evidence 与 ledger，并为 SQD 瞬断提供有限退避。
- **根因三（装配内存死结）**：旧 `_live_payloads` 先累积全部 payload 再装配，全量预计需要 100GB 以上常驻内存；现改为逐 payload 生成、持久化、装配即丢弃，常驻量收敛为聚合结构与有界重排缓冲。
- **两段提交与登记**：第一段由验收方冻结为 `ddfeec1b307f33e4ca9c22d129ad554d33ef426d`；第二段据此为 cache、repair bundle、coverage resolution 与 CURRENT repair pointer 四个 protocol 新增可由 `git show` 复算的 ACTIVE producer 记录，旧哈希继续保留 ACTIVE。
- **回归与版本**：批 8 规模化回归注册到全量 SUITE，机械分母 133→134；允许本地 loopback 的全量实测 134/134 PASS。版本声明同步至 6.52.6，并将基线滞后的 `pyproject.toml=6.52.4` 一并对齐。
- **成本/质量指标**：两段施工；外部网络调用 0；新增回归组 1；分析结论 0；传播级数字错误 0。

## [6.52.5] - 2026-08-25 — facts_gate 宏正则补连字符（死宏静默漏检修复）

- **根因**：`MACRO_RE` 字符类 `[A-Za-z0-9_.:]` 不含连字符，而实体键约定（3.19 起 entities 字典键＝stable entity_id）未禁连字符命名——`{{ENT-PROJ.share}}` 型宏既不被 `render()` 渲染、也不被 G4 残留检出（同一正则的盲区），死宏以字面量静默漏进正文。SPORTFUN −2 案实踩：报告 17 处实体宏全为死宏，flow spec 宏化时暴露。
- **修复与方向**：字符类扩为 `[A-Za-z0-9_.:-]+`（连字符置尾无范围歧义），求值路径 `partition(".")` 本已支持该键型。属**收紧**修复：原漏检死宏开始被渲染/检出，G5 白名单同步收编实体宏渲染值；无键名含连字符的旧案行为零变化。消费方 facts_gate（render/G4）与 figures_from_facts（flow leftovers）同步受益。
- **回归与版本**：test_report_facts / test_figures_from_facts 单跑 PASS；全量 SUITE 133 全绿（分母不变）。版本 6.52.5。
- **成本/质量指标**：单文件 4 行改动；外部网络调用 0；新增回归组 0（既有七契约覆盖）；分析结论 0；传播级数字错误 0。

## [6.52.4] - 2026-08-25 — 批 3c SQD census 字段契约修复

- **根因与修复**：`sqd_gap_repair.py` 的 census 请求把 Solana RPC 响应字段 `parentSlot` 混入 SQD portal 的 block 字段选择；SQD 以 HTTP 400 拒收，且 census 响应与 payload 均不消费该字段。第一段仅删除这个无消费方字段，保留 Helius 响应侧四处合法 `parentSlot`，并新增离线字段白名单守卫。
- **两段提交与登记**：第一段由验收方冻结为 `80ab2a380952bf63eb01bb896c9d7e260bc8055f`；第二段据此为 cache、repair bundle、coverage resolution 与 CURRENT repair pointer 四个 protocol 新增可由 `git show` 复算的 ACTIVE producer 记录，旧哈希继续保留 ACTIVE。
- **回归与版本**：新守卫注册到全量 SUITE，机械分母 132→133；版本三件同步至 6.52.4，第二段保持不 commit，留待验收方冻结。
- **成本/质量指标**：两段施工；外部网络调用 0；新增回归组 1；分析结论 0；传播级数字错误 0。

## [6.52.3] - 2026-08-24 — 批 2d SQD stream 尾部跳块语义收口

- **根因与修复**：SQD 游标续页落入全跳块尾段时会返回 HTTP 200 零字节 body，通用传输层将其归为 decode 失败，导致尾部 slot 永久停在 UNSCANNED。probe 现仅在 `category=decode`、`http_status=200`、`message="curl returned empty stdout"` 三条件全等时复用空数组语义，整段记 NO_HEADER；529 空体、200 非法 JSON、其他 decode/transport 失败仍 fail-closed，`net.py` 逻辑不变。
- **两段提交与登记**：第一段由验收方冻结为 `55d4efede78f6afb6c1d3c8aa3bbec95b6faa33f`，第二段据此为 coverage map 与 CURRENT pointer 两个 protocol 各新增可由 `git show` 复算的 ACTIVE producer 记录；旧哈希继续保留 ACTIVE，维持历史正式收据兼容。
- **回归与版本**：真实 RED 证明旧 probe 会把 200 空体尾段留作失败；新测试覆盖精确正例、三类防误伤、正常块数组与 CLI/validator 端到端，并注册到全量 SUITE，机械分母 131→132；版本三件同步至 6.52.3。
- **成本/质量指标**：两段施工；外部网络调用 0；新增回归组 4；分析结论 0；传播级数字错误 0。

## [6.52.2] - 2026-08-24 — LIT 阵营序列与 evm_v2 重放回归修复收口

- **F-007 阵营序列闭合修复**：正式序列不再按 denominator 名称猜 burn 语义，改由 producer 的 `series_format` 固定实际堆叠集合。`evm-dict` 的「锁仓/销毁」参与堆叠与散户残差、只豁免 `burn_cum_pct`，且 legacy 序列不得含该键；`sol-rows` 的「锁仓/销毁」仍是分母外披露桶；`sol-anchor-rows` 无堆叠豁免。无 format 的手填路径保留历史 dual 行为。
- **F-008 evm_v2 重放前置闸**：`source.argument` 明确按 kind 分家，sol/duckdb 绑定文件、evm_v2 绑定目录；evm_v2 在创建临时文件或启动子进程前先做完整 Unicode `Cc`／glob／SQL 字符闸、不跟随符号链接的固定两 pattern 枚举，并要求当前命中集合与 `source.files` 登记集合双向精确相等。
- **登记面收齐**：新增 F-007/F-008 两个回归测试并将 SUITE 129→131；新增 `CT-BANNED-23` 防旧 denominator 一刀切句式回流、`CT-SEMANTIC-63` 固定 evm_v2 集合闸文案，契约 195→197；版本三件与现役文档同步至 6.52.2。
- **成本/质量指标**：施工轮数 1；外部网络调用 0；新增回归用例 61（F-007 15＋F-008 46）；分析结论 0；传播级数字错误 0。

## [6.52.1] - 2026-08-24 — F-005 Solana reconcile v3/v4 文档漂移更正

- **外审 finding 更正**：外部全量审查指出 `scan-schemas.md` 同一份现役文档一边把 v4 写对，另一边仍把 v3 当 current。现已更正 inputs、consumer 登记面、formal 来源链三处：正式链只接受 `solana-reconcile/v4` formal envelope，v2/v3 都是 legacy，必须重跑。
- **按代码写清语义**：v4 保留 v3 业务字段并收紧三项供应量 raw 值为 JSON int；consumer 还要验 target/mode/verdict/exit_code、producer、base/repaired 条件 inputs、当前 resolver 的 `edge_source_binding`，以及窗口、边摘要和终态闭合，不再沿用“三输入＋cache meta 物理指纹”的旧说法。
- **防再漂守卫**：新增 `CT-BANNED-22`，在 `references/scan-schemas.md` 禁止把“只认 `solana-reconcile/v3`”写回正向 current 口径；contract ID 快照 194→195。施工轮数 1；外部网络调用 0；分析结论 0；传播级数字错误 0。

## [6.52.0] - 2026-08-23 — SQD 覆盖健康闸与修复生产者窄门收口

- **覆盖与修复窄门**：正式记录 durable-nonce 缺陷区段、四态 coverage 指纹、共享地图 30 天 TTL/逐 slot 复核/canary、Helius 唯一参考源与额度停工语义；A2 的 Solana 路径升为四查＋`exact_reconcile` 第五查，base、resolution、repair bundle、CURRENT 指针和 ACTIVE producer 缺一即拒。
- **协议升版**：wave `wave-scan/v5`、flow `flow-anomaly/v3`、wrapper `reconciliation-report/v3`、exact receipt `solana-reconcile/v4` 全链对齐；Solana 派生产物必带与 exact receipt 全等的 `edge_source_binding`，EVM 必须省略。旧 wave v4/flow v2 正式件需重跑；EVM 旧 wrapper 迁移用 `reconciliation_report.py --reseal` 从四份现役 receipt 重建，不信旧 wrapper。
- **正式勘误**：撤回 ARC 诊断中“硬下界 13,425 笔／Meteora-Raydium CPI 特征／218 漏-739 伪影分类”；根因是把 SQD 去投票 `transactionIndex` 当链上绝对位置。抽 80 块 404 笔改按签名复核后 404/404 均在 SQD，跨源身份此后只认签名。
- **契约与文档**：新增 S-12 判例和 capture §13e；contract manifest 新增 14 required＋5 banned，ID 快照由 175 升 194；批 5 wrapper 草案改为 referenced receipt fields，与现役 runner/validator 结构一致。
- **producer 与回归**：登记 coverage probe 2 条、gap repair 4 条 ACTIVE 历史哈希；`run_all.py` 注册 coverage probe、gap repair、reconcile v4 receipt、第五查四项，SUITE 124→128。施工轮数 1；外部网络调用 0；分析结论 0；传播级数字错误 0。
- **深验健壮性加固（批7，同版未升）**：修复代深验 `validate_repair_bundle_deep` 补三处校验覆盖缺口——缺口1 formal 逐 slot 严格校验遍历主键由"候选集"改为"候选集∪census确认集∪修复层 slot"，并加 confirmed⊆候选集反向包含、干净 verdict 零修复边、formal 拒 exploration 指纹、ledger 请求数≥修复 slot 数（此前一条自报 confirmed census 行即可让凭空修复边通过深验、抬高余额/供应）；缺口3 补 merged 边 slot⊆声明 coverage 窗口[from,to] 且 upper==base.finalized_upper（此前 slot>声明 upper 的超窗口边被夹带）。缺口2（自扫 coverage 无真实性复查）裁定为离线 validator 固有信任边界、不加假闸（详见 maintenance/repair-20260823-sqd-gap/batch7_done.md）。新增 `test_batch7_validator_coverage_gaps.py`，SUITE 128→129；exploration 与合法 formal/repaired 路径回归全绿不误伤。施工轮数 1；外部网络调用 0；分析结论 0；传播级数字错误 0。

## [6.51.0] - 2026-08-20 — labels v4.3／Arbitrum CEX-only 建表与 round-trip 收口

- **Arbitrum 建表**：新增 `labels-arbitrum.csv` 730 行 CEX-only 初版，chain registry 只打开 `labels_table`，`release_tier=exploration` 与其余能力不变；benchmark/round-trip/GoPlus/goldset/invariant/release 文案及消费侧回归接通。resolver 不再因缺表 degraded 不等于覆盖完整，基础设施/协议/桥/池仍靠动态识别，不得正式交接或审计发布。
- **round-trip 修复**：`build_labels.py::upsert()` 与 additions 重放路径透传 `source_snapshot_at`，行级值优先、空值才回落源级默认；新增先红后绿回归与 Arbitrum 消费侧端到端回归。
- **数据入库**：Arbitrum +730、Base +51、ETH +1、Solana 0；新增 8 条 Arbitrum infrastructure 金标与 10 条 GMX 案 random-eoa 负样本，补录源由 `add_labels.py` 事务入库并自动归档，manifest 重写。
- **验收口径**：沙箱 run_all 121/123，两项 vertical slice 仅因 loopback bind EPERM 阻断；验收方本机分别代跑 Solana/EVM vertical slice 均 rc=0 PASS。独立 invariant scan PASS。
- **盲审消化 F-01/F-03**：新增受跟踪候选真源 `benchmark/goldset_curated.csv`，构建器在自动分类/重抽样后按 `(chain,address)` 优先合并；真实重建 1,017 条后 Arbitrum 裁决金标 18/18 逐语义保留、random-eoa 10 条、`weak_gate=false`。补齐 snapshot 高优先覆盖与低优先补空两条分支回归，并以删赋值突变证明测试会红。
- **盲审消化 F-02/F-04/F-05/F-06**：R7-11 fixture 从 registry 派生六张 labels-table 表并精确断言日期倒退；Arbitrum 权威路由改为 CEX-only/coverage incomplete/exploration；round-trip 文案改称 labels-table 登记链；根 `.gitattributes` 仅对 `references/labels/*.csv` 关闭 whitespace 检查，发布表未重规范化，goldset 构建器显式 LF 收敛。
- **修复轮验收**：新增测试后沙箱 run_all 为 122/124，唯一两项失败仍是 Solana/EVM vertical slice 的 loopback bind EPERM，其余全绿；验收方本机修复前 123/123 原始输出继续作为允许 loopback 环境机器证据，本轮不改 runner 超时。

## [6.50.0] - 2026-08-18 — split-run 三段化＋刀 1 外包公告体系

- **−3 装配段**：新增 /token-analyze-3 命令＋split-run §3b（A5 装配执行侧：三图/流转图/双 receipt/a5-report-seal/v3/build_html G11/发布闸；建议 Opus 会话）；−2 收口前移＝报告正文亲笔成稿＋四条收口自查＋产 a5_assembly_workorder.json 即停（非正式件无 validator，兜底=既有 A5 链闸；图表基数与工单完备性属文字纪律，残余风险用户拍板接受、首战后评估）
- **ET-1 前置**：−1 停止线"大户报警深挖"拆分——证据采集（保守超集分母、观察事实零定性、落 et1_evidence_packs.json，optional 但存在即入 manifest allowlist）归 −1，归属定性深挖留 −2；−2 冻结后与 packs 双向对账
- **刀 1 公告**：context-discipline 机械档扩为 14 项完整清单＋6 条外包纪律（sealed 禁读/盲化对子代理生效、装配线程不当 A4 怀疑者、非权威中间产物边界、零结果自证、禁手抄、交付自查申报），唯一权威源制；research-workflows §二b 钉法改指针消双源；刀 2/刀 3 编号重号 bug 顺手修复
- **契约与测试**：新增 CT-SEMANTIC-61（token-analyze-3 required a5-report-seal/v3）/CT-SEMANTIC-62（required G11）/CT-BANNED-16（banned A5 seal v2），contract_ids_snapshot 同步 157 条；deploy-sync EXPECTED 与 batch3 gates COMMANDS 扩四元＋−3 四类负例等深
- **版本**：跳过 6.49.0（被并行 fix/sqd-solana-v4 工程占用，避免合并撞号）
- **回归**：run_all 在允许 loopback 环境 116/117 PASS，唯一红项 test_commands_deploy_sync（部署 cp 待合并后执行）；受限沙箱首跑两项 vertical slice 遇 loopback bind EPERM，获准环境全量复跑均转绿（合并 main 后 cp＋复跑绿）
- **盲审消化**：codex 正常盲审 F-01/02/03＋opus 攻击 7 WEAK 中 5 项修复入盘（契约锚句化＋负例加深、report-template 物化两态、旧完成案分流、sealed 申报回填、三分类收窄、needle 稀释回收、权威源三源化）；W-03（banned 字面变体穿透）与 W-04（契约 needle 值无守卫、快照只锁 ID 集合）属契约体系存量固有形态，接受在案登记为后续升级候选
## [6.49.0] - 2026-08-18 — Solana SQD transaction-net v4 五批根治

- **缺陷与证据边界**：旧 `fetch_sqd_transfers_v2.py` 请求中已有 `transactionIndex`，却落盘为 `[ts,slot,from,to,amt]` 五元组并按五字段 DISTINCT 合并，同 slot/同额/同 owner 的不同真实交易会被误删。批 4 独立 oracle 对 ARC 冻结的 1,348 个 parts 复算：multiset 1,775,858 行、DISTINCT 1,764,356 行，域内机械可证损失为 **11,502 行／8,487 碰撞组／最高 23 倍率**。早期 124,816 是两版全史边表的行数差，混入两次采集间其他差异，**不是纯 DISTINCT 损失**。
- **@CX 三项设计拦截**：①`pair_tx` 等额时不能继承 SQD 返回序，排序键补 owner 后才字节确定；②transaction-net 没有 instruction 顺序，`instr_index=-1` 必须对应 `order_exact=false`，不得伪造交易内因果；③owner 净额贪心配对只证明 owner 级余额变化，正式声明 `edge_semantics="owner-net-greedy"`，不得冒充链上精确 from→to。
- **五批结构**：批 1 冻结语义并抽取共享核；批 2 将采集器升为 v4 7 元组、按 `(slot,tx_index)` 完整边集 `tx_digest` 去重，修 owner authority 双侧记账与七条输入硬规则；批 3 把正式 v4 与显式 `--legacy-sol5` 诊断彻底分立，并把交易内未决传导为 `UNRESOLVED/order_ambiguous`；批 4 让采集成功 meta 绑定逻辑摘要/行数，登记 ACTIVE producer、清零 invariant 并完成 ARC parts oracle；批 5 用 ARC 高碰撞窗与无碰撞绿例窗真采、SQD＋Solana `getBlock` 三组抽样、端到端破坏性注入三连和全仓 grep 白名单收口。
- **纵深防线**：v4 meta 绑定 mint/endpoint/finalized 上界/启动冻结 collector SHA；同交易跨 source 同 digest 留一、异 digest 硬失败；非法 tx/account/mint/owner/amount 整段失败；v3 meta、孤儿 cache 与旧/混合 parts 在网络及 v4 parts 创建前拒绝并要求全量重采；HyperSync 正式入口硬禁；replay/camp 对 ACTIVE producer 登记、逻辑摘要、行数和边实物对表；legacy 产物强制 non-formal/order-ambiguous 且不得进入 reconcile/evolution/READY/发布。
- **实弹验收**：碰撞窗 16,199 slots 真采 5,696 条 v4 边，5 元组投影与案内 tx-aware 表逐边 multiset 零差，保留 85 组碰撞/114 条额外边/最高 5 倍；绿例窗 12,814 slots 真采 142 条，逐边零差且碰撞为 0。三组碰撞经 SQD 原始 `transactionIndex` 与主网 `getBlock` 六个互异签名确认。边内容单一逻辑字节、未登记 collector hash、v3 meta 三种注入均在各自目标分支拒绝；正式非白名单 5 元组解析残留为 0。
- **范围**：不追溯改写旧 v3 案或旧缓存；旧缓存留盘但只可显式诊断。ARC owner-authority 全量扫描未发现可用变更窗，因此按工单保留批 2 fixture＋案内扫描证据，不虚构真链实例。施工 codex；验收与 main 合并/push 由 Fable/opus 后续执行。

## [6.48.1] - 2026-08-17 — 单元3 盲审消化轮（三单元收口工程收官）

- **源起**：6.48.0 收口后独立 opus 盲审（9 攻击向量实跑＋基线对照＋破坏性注入三连验测试非装死）判 CONDITIONAL：1 BREACH／3 WEAK／4 NOTE／9 DEFENDED，**闸体本身攻不破**——跨版本续采拒、10 个类型向量全拒、"另开新 channel 段"出路经真实 replay+gate 端到端验证可达；所有得手攻击落在单元3 射程外。施工 codex（工单 U3b）。
- **BREACH-01 归属裁决**：`evm-collector-run/v2` 全库两个签发者，单元3 焊死了 fetch_hypersync.py，但 SQD 侧 `csv_collector_receipt.py/emit_native_receipt` 仍为写时实时哈希、无启动冻结/写前复验/REVOKED 拒启动，采集期改档可致归属谎报端到端假 PASS——**非本单元引入**（工单明文将该文件划为不改），代码修复另立第四单元；本轮只收窄其被单元3 文档过度涵盖的声称面。
- **本轮消化（本单元引入债）**：签发点 schema 字面量收敛到 COLLECTOR_RECEIPT_SCHEMA 常量＋channels_preflight 副本维护路标；`{CONST: True}[schema]` 怪写法改常规比较（四次实跑错误面逐字一致的等价重构；重构撞出 invariant 扫描器把 `.get("schema")` 比较识别为消费面的边界，暂以 `dict.get(prev,…)` 等价形式绕行，正名归第四单元）；`--out` 与 `--receipt` 同路径前置拒（对齐 SQD 既有范式，修前未捕获 FileExistsError＋临时件残留）；文档"顶层 collector 保证覆盖全部 segments"**过度声称收窄**——保证主语仅限 fetch_hypersync.py 签发且受同哈希闸＋TOCTOU 保护者，SQD 侧签发不在保证内（置信度＝顶层自报）；方案 B 永久维护债申明（历史哈希从续采瞬时依赖升级为 preflight 永久依赖，升级漏登＝该版本存量段全拒）。
- **第四单元候选清单（待用户裁决）**：①SQD 侧 TOCTOU 收口（emit_native_receipt 收启动冻结哈希参数＋fetch_sqd_evm 入口冻结/写前复验/REVOKED 拒启动）；②反向断链守卫（"HEAD 前一版必须已登记"回归）；③跨文件 schema 常量统一＋扫描器 `.get("schema")` 消费面模式正名；④SQD REVOKED 前置拒（现仅消费侧兜底）。N-03/N-04 记录不修。
- **回归**：test_csv_resume_collector_gate 9→10 用例全绿；suite 分母 117 不变，117/117 PASS rc=0（本机含两项 loopback）。盲审 opus，调度验收 Fable。

## [6.48.0] - 2026-08-17 — HyperSync CSV 同哈希续采闸·方案B（三单元收口工程·单元3）

- **源起**：三单元收口方案第 3 单元，关 CSV 通道归属重写账——`--resume-receipt` 跨版本续采会把旧段整体收进当前脚本署名的新回执。定案方案 B（@CX 复核在案）：同一 CSV 只许同 collector 哈希续采，脚本升级后以前驱覆盖终点另开新 CSV 作为新 channel 段接入（preflight 多 channel 连续性拼接为既有生产路线）。施工 codex（工单 U3），基线 aadbe59。
- **生产侧闸**：resume 分支在既有 `_csv_collector_provenance` 重验之后独立校验前驱 `collector.sha256 == 启动冻结哈希`，不等 fail-closed 且错误信息含"另开 CSV/新 channel 段"指引全文；prior receipt 顶层/schema/collector/query/边界/segments 全字段先收类型（含 bool≠int 边界），schema 白名单仅 evm-collector-run/v2、未知值拒；不改 `_csv_collector_provenance` 本体（消费场景历史哈希放行是合法语义）。
- **TOCTOU 与吊销**：进程入口计算 `collector_start_hash` 并按 collector_history 全表 hash-wide REVOKED 拒启动（"当前脚本版本已被吊销"，U2b/R6 等深延伸）；写 receipt 前重算哈希，运行期漂移即删临时 CSV 拒签；receipt 的 collector.sha256 一律用启动冻结哈希（替换写时即时哈希）。
- **U1 盲审传染修复**：resume 读入接 `strict_json_loads`（重复 collector 键人机分裂拒于读入层，引用共享件勿复制）。
- **登记与考证**：被替换的 `cea82c77…` 版本补登 collector_history（protocol=evm-collector-run/v2，commit=2d69373 全哈希，git blob 复算闭环）；按 U2b/B-02 纪律核证该版本生前唯一签发 protocol 即此一线，一条即全。SQD 通道单 segment＋fresh_output 既有保证固化为防退化断言（如实标注为既有正确行为，非旧代码漏过）。
- **存量清点**：Desktop 工作区＋Documents 归档区全盘清点 105 份 evm-collector-run/v2 存量回执，segments 全部单段、零多段件——方案 B"零迁移"前提在全量口径成立，无需 legacy confidence 标注；文档语义声明为前瞻性闭合、不宣称修复历史。
- **suite 分母**：117 个入口（116＋test_csv_resume_collector_gate 九用例，先红 6 漏过后绿 9/9），117/117 PASS rc=0（本机含两项 loopback）。调度验收 Fable。

## [6.47.1] - 2026-08-17 — 单元2 盲审消化轮（4 BREACH＋5 WEAK 修复＋1 注）

- **源起**：6.47.0 收口后独立 opus 盲审（20 攻击向量实跑＋基线对照＋27 个真实采集根扫描）判 BLOCK：4 BREACH／6 WEAK／2 NOTE／11 DEFENDED；按裁决消化，施工 codex（工单 U2b）。
- **B-01 收据标签去"验证"语义**：迁移段删 legacy 键＋填公开可算的当前脚本哈希即可把 preflight 收据从 UNKNOWN_LEGACY 洗成 VERIFIED（零成本，无需伪造脚本）。修＝原生段标签改 `SELF_REPORTED`＋`collector_sha256` 哈希透传，迁移段保持 UNKNOWN_LEGACY；闸只做自报绑定核对，置信判定交上层，`scripts/` 内 VERIFIED 字样清零。声明边界：改写后的联合仍被判别闸放行（自报绑定的既有边界），本项修标签语义不加真伪鉴别。
- **B-02 升级断链纪律补齐**：done/v4 与 identity/v2 两条新 protocol 线历史集为空，脚本一升级存量全误拦——NES 0816「169 份正版 receipt 误拦」同族，本单元新挖两个。修＝maintenance-review-repair 纪律条款改写（被替换版本按其生前签发过的**每个 protocol 各补一条**，一版多 protocol＝多条目）＋断链固化测试（模拟升级后未补登的原生 v4 done 与 recovered identity 双双被拒，测试注释指向纪律条款）。附带边界：6.47.0 版脚本被本消化轮替换，其在世期间无正式签发产物（仅临时演练件），按纪律无需补登；盲审期间的临时演练副本重验被拒属预期。
- **B-03 inventory 残件分类出路**：quarantine/（staged_capture 自建）、`*.recover`（refresh 回滚特意保留件）、`.refresh-tmp/.refresh-bak` 崩溃残件全被"未识别残件"一刀拒且无指引；真实回归＝APU 0801 案主目录（基线 PASS）被人工诊断目录卡死。修＝分类报错逐类给人工处置指引（全部仍拒、不提供自动清理防洗白）＋数据管线文档新增"遗留目录残件处置手册"。
- **B-04 staged_capture 首采死路**：identity 检查一刀切，全新目录 FATAL→指向 recover→recover 对空目录又拒。修＝三态放行（outdir 不存在/真空目录/identity 普通文件在场），非真空遗留缺 identity 仍 FATAL。
- **WEAK 五修一注**：`.DS_Store` 唯一豁免（精确名，无通配）在 inventory/C12 真空/staged shell 三处等深，其他隐藏文件仍拒；REVOKED 压过当前脚本哈希（吊销当前版本即拒签发/校验，fetch＋preflight v2/CSV 三线同步）；recovered 身份透传收据（identity_schema/recovered/lineage，恢复目录不再与原生同形）；symlink 采集根修死代码（resolve 前判定，recover/refresh 双入口拒）；CSV collector receipt 读入接 strict_json_loads（重复键跨通道等深，U2 传染修复漏网点）；pre_migration_sha256 定性"迁移时点自报留痕、原件覆盖后事后不可独立复验"（仅改口，逻辑不动）。
- **NOTE 两条落账**：N-01 盲审实测证明 U2 工单 §13"consumer 替换 v4"判断有误、施工方保留 v3 是机器必需（invariant_scan 依赖），维持现状；N-02 演练样本选择性批评成立——本轮以 APU 0801 案主目录原始形态重演练闭环（诊断目录在场被拒且报错带分类指引，移出后 refresh 升 v4 全通，原目录零改动）。
- **回归**：test_done_v4_collector 17→24 用例全绿；suite 分母 116 不变，116/116 PASS rc=0（本机含两项 loopback）。盲审 opus，调度验收 Fable。

## [6.47.0] - 2026-08-17 — HyperSync Parquet done v4 逐段采集者归属＋C12 显式恢复（三单元收口工程·单元2）

- **源起**：三单元收口方案第 2 单元，关闭两笔账——Parquet 通道每段 done.json 无采集脚本指纹（脚本升级续采/删 identity 重建都能把旧数据"改姓"），以及 identity 缺失时自动补签的洗归属窗口（C12，6.45.1 批 C 注释自认）。施工 codex（工单 U2，maintenance/closure-20260817-threeunit/），基线 837baa8。
- **done v4 逐段归属**：`hypersync-v2-done/v4` 起每段 done 带 `collector{path, sha256}`，哈希为 main() 启动冻结值；写 done 前重算，漂移即拒写（自报绑定防误漂移，不宣称防可同时伪造脚本与收据的攻击者）。v2/v3 入 legacy 集合；旧段经 --refresh-manifests 升 v4 时如实标 `collector: null`＋`collector_provenance: "legacy-unattributed"`＋迁移三件套（`refreshed_from_schema` 沿用既有键名／`pre_migration_sha256` 读一次字节流同时算哈希与解析、commit 前复验原件／`migrator` 身份哈希须∈当前∪protocol 过滤后历史）。validate 侧判别联合互斥：原生 v4 禁 legacy 族键、迁移 v4 必 collector null 且三件套齐全，两态互换即拒；下游展示 UNKNOWN_LEGACY 不渲染成已验证。多段 pre-schema 无法唯一推导公共起点时拒猜、要求显式 --capture-from。
- **C12 收严＋显式恢复**：identity 自动签发仅限真空目录（`not any(iterdir())`，任何隐藏件/残段都算遗留）；遗留目录走新 CLI `--recover-identity`——共享 inventory 精确闸（每 run 恰普通文件三件套，拒 symlink/孤儿/空 run/残件）＋逐 run 重验同一性后签 `hypersync-capture-identity/v2`（recovered=true、lineage="unknown"、recovery_time、`recoverer` 取代 collector 键，query_schema 记现行值）；先 recover 后 refresh，refresh 不再自动补 identity。staged_capture.sh skip 路径补根 identity 检查（缺失 FATAL 指向 recover，假成功收口）。
- **protocol 隔离**：`historical_script_hashes(name, protocol)` 按协议过滤，REVOKED 保持 hash-wide 跨 protocol 否决；全部生产调用点显式传 protocol（done v4 新线首版历史集为空／identity v1 线／CSV 线 evm-collector-run/v2）；被替换的 f544a196 版本按维护纪律同单元补登（考证 commit 0ec6d1e 全哈希）。preflight 侧镜像段升级为共享引用（inventory/actor 闸/常量从 fetch 侧 import，判定骨架仍两份）。
- **U1 盲审跨单元传染修复**：done/identity 全部读入点接 `strict_json_loads` 拒重复键（done v4 判别联合是键存在性判定，重复 collector 键可人机分裂——V-31 同构）；schema 分派显式枚举禁 fail-open；枚举判定前收类型。
- **实件演练（拷贝到临时区，三源 pristine diff 零改动）**：APU data_lp 单段太古全链走通（recover 签 v2 → refresh 唯一推导升 v4 三件套齐全）；EGL1 三段太古目录被 inventory 闸如实拦截（run_0 真实缺 logs.parquet 的残段）；NES bsc/v2_segments 被拦（源固有空壳 run_100459662，重用该目录前须人工处置）。
- **suite 分母**：116 个入口（115＋test_done_v4_collector 十七用例，先红 16/17 后绿 17/17），116/116 PASS rc=0（本机含两项 loopback）。调度验收 Fable。

## [6.46.1] - 2026-08-17 — 单元1 盲审消化轮（2 BREACH＋7 WEAK 修复）

- **源起**：6.46.0 收口后独立 opus 盲审 38 向量实跑，判 2 BREACH／16 WEAK／20 DEFENDED；按"BREACH 必修、WEAK 逐条裁决"消化，施工 codex（工单 U1b，maintenance/closure-20260817-threeunit/）。
- **BREACH ①重复 JSON 键人机分裂**：同一 plan 对象里 `balance_block_source` 键写两遍（前值给人看、`json.loads` 取后值），重签 receipt 后深验、语义重放、发布闸全链绿灯。修法＝`anchor_point_contract` 新增 `strict_json_loads`（object_pairs_hook 逐层拒重复键），接入 anchor plan/receipt 消费链全部读入点（执行侧 `load_validated_plan`＋发布侧 `_validated_time_plan_authority`）；范围仅 anchor plan 链，未全库扩散。
- **BREACH ②protocol 硬编码**：producer 历史查询两调用点硬编码 `anchor-plan/v2`，"v3 plan 挂 v2 时代 producer 签名"这一逻辑上不可能的组合被接受。修法＝先严格解析 plan→schema 白名单校验→按被验 plan 实际 schema 动态取历史集→再验 receipt（执行/发布两侧同序）。
- **WEAK 七修**：schema 分派三处（classify／balance_query_block／发布 `_plan_point`）fail-open else 改显式白名单＋未知 schema 拒；v2 点携带 `balance_block_source` 说谎字段即拒（共享谓词收口，签发/执行/发布/分型四路等深）；枚举判定前 isinstance 收类型（list 型由 TypeError 统一为 ValueError）；单源对账守卫恢复全 manifest 全局语义＋显式豁免表带理由（字面量收敛到共享常量后扫描器不再误列 time_spotcheck，manifest 同步真实扫描面）；producer_history status 枚举运行时守卫（错拼即抛不静默失效）；登记表 commit 统一 40 位全哈希＋守卫正则收紧；`validate_receipt` 补 `allowed_producer_hashes` 调用方责任 docstring。
- **维持与遗留**：五项维持裁决在案（REVOKED 不认当前哈希＝设计语义、无 .git 自禁用＝部署边界、闸严于执行器＝安全侧等）；发布闸不重放/不查探测块越界经 6.45.1 基线复跑证实为旧账，语义重放入发布闸另行立项，本轮不动其校验深度。
- **回归**：NES 三份存量深验＋dry-run 重放继续全绿；盲审攻击脚本回打六向量全部由过转拒、kind 文案免疫正例仍过；suite 分母 115（test_anchor_plan_v3 12→15 用例）115/115 PASS。盲审 opus，调度验收 Fable。

## [6.46.0] - 2026-08-17 — anchor-plan v3 机器字段与 producer 历史登记（三单元收口工程·单元1）

- **源起**：NES 收口工程（6.45.1）遗留立项经 @CX 复核融合定案三单元；本单元关闭两笔账——锚点计划靠 kind 中文文案精确匹配推断块源（改措辞即误拦），以及存量 receipt 的 producer 哈希被强制等于当前脚本（6.45.1 批 A 改动后 NES 三份存量件深验已断，`producer hash mismatch` 基线即红）。
- **v3 契约**：`anchor-plan/v3` 起余额点必带 `balance_block_source ∈ {day_end_block, final_block}` 正向白名单；balance/tx 点型严格 XOR（互斥判据+各自禁键，混合点拒）；`final_block` 源仅限 forced_points 且日期锚保留；kind 降纯展示（本轮文案一字未改）。契约入口 `anchor_point_contract.balance_block_source_of` 四处消费方（签发/执行/发布深验/classify）按 plan.schema 分派，v2 存量走原文案兼容路径零变化、一律不重签。
- **producer 历史登记**：新建 `scripts/lib/producer_history.py`（六字段条目式，git show 可复现考证纪律，REVOKED hash-wide 跨 protocol 否决）；登记 `e5168a…`（NES 签发者，考证至 3b76db8）与 `1a461169…`（6.45.1 被替换版本）。`receipt_validate.validate_receipt` 增可选参 `allowed_producer_hashes`（默认 None 行为逐字不变，仅 anchor plan receipt 消费点传入登记集），time_spotcheck 与 shared_release_receipt（含 repo_ref_ok）三处共用单源。
- **重放兼容**：`validate_semantic_replay` 改 schema-aware——生成器只产 v3 形态；重放 v2 plan 时仅投影重算结果（先逐点过 v3 XOR 断言再剥 balance_block_source 单键，禁静默 pop），逐点 multiset 比对语义不变。receipt schema 保持 anchor-plan-receipt/v2，配对矩阵收紧为 receipt.plan_schema 必须与 plan.schema 精确相等。
- **存量实证**：NES 三份真实 v2 plan/receipt 深验+完整 dry-run 语义重放先红后绿（施工前三份全部 `producer hash mismatch`，施工后全 exit 0），只读验证未重签。
- **suite 分母**：`run_all.py` 115 个入口（114＋test_anchor_plan_v3 十二用例，先红 0/12 后绿 12/12），收口标准 115/115 PASS、rc=0（本机含两项 loopback 纵切片）。施工 codex（开工门禁自查抓获工单一处行号笔误后勘误放行），调度验收 Fable。

## [6.45.1] - 2026-08-17 — NES 双链首案四修复、四批收口

- **源起与审查**：NES 双链首案实证触发四笔修复 commit（`dd248ca`/`0cbda66`/`08c5b09`/`af816d1`）；codex 全量审查结论为 2 缺陷、1 疑点、1 缺测试，原修复零测试。随后按 codex 施工、Fable 调度验收分四批收口。
- **批 A／R-1 补位收窄**：`anchor_point_contract` 契约化边缘点判定在签发、执行、深验、构造四处等深；`block_of` 改精确匹配并 fail-fast；保留 9 条红实证。
- **批 B／R-2 登记表迁移**：历史采集器登记表迁入 `collector_history.py`，改为条目式六字段；按 HEAD 祖先口径定案为 4/5/2 条 ACTIVE，先前 `--all` 口径的 19 条预算含未合并分支版本，已排除；文档 121 行改口并保留契约 needle，维护纪律写入 maintenance 文档。
- **批 C／R-3 identity 维护链闭合**：`ensure_outdir_identity` 三入口识别历史版本，两侧都只接受两键规范形并拒绝额外键；collector 语义修正为目录 lineage 签发者（done v4 逐段 collector 列为后续立项）；维护纪律首次适用补登 `887c0f58`。
- **批 D／R-4 producer→gate 真件对测**：`compile_state` 的真实返回产物落盘后直接调用 `audit_release_gate.check_formal_case_chain`；正式 BSC 正例必须无错误过闸，删除顶层 `chain` 与顶层/token 链矛盾两负例必须被闸拒绝，封住 producer 与 consumer 各自自洽却组合断链的测试逃逸面。
- **成本与质量**：四批线性施工；批 D 新增 3 条 producer-consumer 端到端回归，版本登记统一至 6.45.1。施工署名 codex，调度验收 Fable。
- **独立盲审与批 E 消化**：独立攻击型盲审约 40 向量实跑，终局 0 BREACH / 7 WEAK；五项修码收口 tx 分支等深、collector 类型混淆受控拒绝、REVOKED 压过 ACTIVE、git 考证补 HEAD 祖先机器闸、v2 URL 交叉比对，并补两项诚实边界注释。C14 混版目录续采维持知情放宽，done v4 逐段 collector 另行立项。

## [6.45.0] - 2026-08-15 — 三 AI 并行修复工程融合（v6.44.0 review 14 findings 全处置）

工程目录：`maintenance/repair-20260815-g1/`、`repair-20260815-g2/`、`repair-20260815-g3/`（三组各含 plan/工单/盲审/done 报告全档案）。三组从同一基线 ddba187 并行施工（调度铁三角：Fable 调度验收 commit／codex 纯施工／opus 攻击型盲审），融合方按 g1→g2→g3 顺序合并，5 处冲突全部 union 解决（run_all 注册／契约 manifest／invariant floor／两处 chain_registry import）。

- **g1 正式边界与守卫**（F-01/02/03/11/12/14）：`safe_case_file` 案根 containment 全入口（handoff generate/verify/data_map/include/freeze＋adjudication_validator，R10-15 关账）；审计闸 independent-audit 缺 `--report` 直接 errors；`check_formal_case_chain` 升 `{chain, token, as_of_block}` 三元组跨分区等式并抓出 Solana target 小写化真实生产缺陷（六写出点原串保真＋shared canonical_target 链族归一）；command 文本 a5-report-seal/v3＋CT-SEMANTIC-60/CT-BANNED-15 契约；risk_flags 正向白名单 `[a-z0-9-]+`（R10-18 关账）；F-14 政策替代＝历史证据零改动＋现役文本卫生守卫。opus 两轮盲审 PASS。
- **g2 对账与观测证据链**（F-04/07/09/10）：观测件拒空 runtime code＋66 字符 ABI word 三层等深；recon/time schema 升 v3，consumer 五路深重验（supply 实物重算/balance top-N 逐笔/time plan multiset/anchor 逐行/gmgn Decimal）；**GMGN 黄灯制（用户裁决）**＝差异不硬停、receipt 落 `warnings`＋必须附 `gmgn-divergence-note/v1` 查证说明（cause 枚举 gmgn_data_lag/methodology_diff/gmgn_upstream_error，自算错误不在枚举内＝必须修数据不可说明放行），发布闸重算差异并强制说明件在场且逐项覆盖；Arbitrum 探索档四 CLI 恢复（executable helper＋resolve_execution_mode，正式消费面双断言先钉死）。opus 盲审 209 向量 BREACH 终态 0。
- **g3 采集通道与复核契约**（F-05/06/08/13）：A0 改 `--exploration` 预检产 `accounting_mode.exploration.json`，A2 三步 observe_supply→accounting `--bundle` formal 重跑→supply_truth（formal 唯一 canonical，工作流断裂修复）；SQD 区间闭校验＋log 逐字段 66 位 hex＋空响应五连硬退＋receipt 游标 provider 派生；**Alchemy 正式资格除名（用户裁决选型 B）**——无 provider 侧完成证据，`--receipt` argparse 拒绝，恢复候选＝升分型收据；**F-05 用户裁决不加闸（ACCEPTED_RISK）**，两分册"机器化边界"段如实写明六项已强制/四项未强制，机器闸 PASS 不等于 N 路已落实；F-13 文档对齐 entrypoint 环境变量读取现实。盲审 round1 BLOCK（SQD 上界缺失 P0）→消化→round2 PASS。
- **存量影响**：EVM 案重发布须以 verify_recon v3/time_spotcheck v3 重跑对账（v2 收据消费面拒收）；旧 SQD/Alchemy 备用通道 receipt 重验必拒（按契约应零正式存量）；含 abs/`../` 绑定的旧案 check-unseal fail-closed 属期望行为；已交付案不重跑均不受影响。Solana 原串保真对"老案部分重跑致大小写混存"有硬失配面，存量清点结论见融合记录。
- **suite 分母**：融合树 `run_all.py` 共 112 个入口（101＋g1 五测试＋g2 四测试＋g3 两测试），收口标准 112/112 PASS、rc=0；invariant consumers floor 82（g1+1/g2+3 增量之和）。

## [6.44.0] - 2026-08-15 — EVM 链上观测锚（F-02 闭合/F-03 缓解）

工程目录：`maintenance/repair-20260814-evmobs/`。ETH/BSC/Base 正式纵切片在 reconciliation 前真跑 `scripts/evm/observe_supply.py`，落 `evm-observation-bundle/v1` 与规范化 RPC transcript；accounting 与 supply_truth 分别升 `accounting-gate/v2`、`supply-truth-receipt/v4` 并绑定同一冻结块观测件，Solana 继续使用 v1/v3。shared 发布与 READY handoff 共用 validator，对锚块、bundle 文件三验、供给/sink N-2 和两收据同源做等深复验。

- **正式能力与失败产物**：三链 E2E producer 集合和 `evm-accounting-supply-v2` capability 加入 observation producer；错链回归证明只发生 `eth_chainId`，业务调用为零；双件 producer 的 failure coverage/contract 明确 `canonical_artifacts=2`，旧 bundle/transcript 均先 quarantine。
- **诚实边界与 R10**：R10-13/F-02 由裸标量升级为案内可复算观测实物，标 CLOSED；R10-9/F-03 仅标 MITIGATED 且仍 OPEN。bundle 提高同步伪造成本并给第三方留下 blockHash/transcript 外验材料，但不证明块头案外真实或 producer 真执行。
- **独立盲审（opus 线程）**：31 个伪造/篡改向量全部 fail-closed（transcript 逐位/信封哈希/bundle 自洽三道防线）；消费第三条旁路、exploration 冒充 formal、legacy 逃逸门、夹具直拼绕闸、登记装样五路攻击均未得手；0 P0/P1/P2、2 P3 消化完毕（R10-13 措辞缀句采纳、camp_series 双接受确认为设计）。证据 `maintenance/repair-20260814-evmobs/blindreview_OBS_round1.md`。
- **存量影响**：QUQ/AKE/B2/TAG/MOG/APU/EGL1 等已交付 EVM 案不重跑发布闸时不受影响；未来重发布必须先跑 `observe_supply.py`，再按 v2/v4 重做 accounting 与 supply_truth，禁止手工补字段或只改 schema。QUQ posthold 独立监控体系不受影响。
- **suite 分母**：与批 3（6.43.0）融合后 `run_all.py` 共 101 个入口；本版收口标准为 101/101 PASS、rc=0，包含 eth/bsc/base 三链纵切片、Solana 控制组、契约双向守卫、版本/CHANGELOG/docs/invariant 守卫及 F-02/F-03 原反例。


## [6.43.0] - 2026-08-14 — 批 3 弱闸三线收口（六视角 review F-01/04/05/07）

批 3 按用户裁决完成 A4 语义联动、deploy-sync 严判、env_check 机械派生与 R10 台账同步，并为集成漂移补上可执行自洽守卫。

- **F-01 A4 语义联动（工单 F01）**：blocker 必填 source={kind,ref} 机械定位符；validate_blocker_linkage 双向对账（缺账/幽灵/重复拒）两侧独立执行；finalize 账不全 rc2 不落盘、账全未决落盘 BLOCKED；evidence/resolution 10 实义字符门槛（_has_min_meaningful_chars，防呆不防伪）；entrypoint sha 跨角色全局唯一（防误复用，非独立性证明）；adversarial-review/v4 + artifact/v2，存量 v2/v3 须重跑（先报 producer 失效属预期）。先红 25 项。
- **F-04 deploy-sync 严判（工单 F04）**：删 MIGRATION_CHANGED 无界豁免（归因 ede24d7 解耦隐式过期）；canonical 安装路径缺部署目录 fail-closed rc1，非 canonical checkout 打 SKIP_NON_CANONICAL_CHECKOUT rc0；校验主体纯函数化。先红 4 项。
- **F-05 env_check 机械派生（工单 F05）**：受检集合唯一来源 pyproject 21 直接依赖；三层闭合（direct→lock 唯一 pin→installed 全等）+ lock pin 须满足 pyproject 下限；PEP503 规范化；受控说明符白名单 fail-closed；requires-python 检查；pre-commit 第二挂载点联动实证。先红 8 项。已知边界：平面 lock 无法判已删直接依赖残留。
- **R10 台账（F-07）**：批 1 已修 4 条补记 CLOSED 6.41.0（集成漂移修正）；批 3 四条修复经盲审转 CLOSED；现役 23→19→15；新增台账自洽守卫（ID 唯一/状态枚举/计数一致，消化轮迭代为按节列解析+统一状态载体规则 fail-closed）。
- **三轮盲审+三轮消化+addendum（全程 codex 独立线程）**：R1 判 BLOCK（BR1-01 P1 finalize 可省略不利 receipt+BR1-02 假 HOME 逃逸 canonical+BR1-03 台账守卫可伪+BR1-04 基线证据漂移）→消化轮 1 落 execution ledger 哈希链（run-role 落账 O_APPEND+flock、finalize/消费侧有效集精确对账；防事后省略不防整册重造，边界如实）、canonical 改 getpwuid、守卫收紧、83394ab 真基线重建（`br104_evidence_rebuild.md`）；R2 判 CONDITIONAL（BR2-01 大小写别名计数失真+BR2-02 竖线全角组合绕）→消化轮 2 落实物 inode 判重+三方基数闸+receipt basename 受控字符集+按节列数 fail-closed；R3 判 CONDITIONAL（BR3-01 未知/隐形状态载体静默归 OPEN）→消化轮 3 统一载体规则（全行【...】载体须合法列+fullmatch 枚举否则 FAIL）；addendum 终判 PASS。全程证据 `maintenance/repair-20260814-batch3/blindreview_round{1,2,3}.md`+`blindreview_round3_addendum.md`。
- **6.43.0 前身冻结基线**：main@83394ab 97 项全绿 rc0（重建证据 `baseline_run_all_83394ab.log` 带 SHA 头）；本批收口时 SUITE 99 项（+test_repair_batch3_f01+test_repair_batch3_gates）全绿 rc0。

## [6.42.0] - 2026-08-14 — 批 2 防伪面三线三轮盲审收口

批 2 在 6.40.0 上完成 F-10/F-02/F-09 三线施工与三轮盲审，A/B/C 终态均 CLOSED；工程目录与逐轮证据见 `maintenance/repair-20260814-batch2/`。

- **F-10 waiver 政策硬顶（工单 A）**：以 approved/observed/request/消费侧实算四值最大值执行 ≤10bps 自动、>10 且 ≤100bps 普通 waiver、>100bps 再强制独立 `over-cap-approval/v1` 的三段政策；approval 绑定 target、replay_stats、request 规范哈希、nonce、30 天有效期、用户批复和独立 evidence，生产/消费两侧独立重验。三轮盲审从零宽击穿扩到 13 码位，再翻转为正向白名单并以全码位差分/行为向量闭合。
- **F-02 对抗复核结构化闭环（工单 B）**：`adversarial-review/v2` 升 `v3`，以 `a4_claims.json` 的 path/size/sha256/schema 为权威锚；每路 `adversarial-review-artifact/v1` 机器验证三档 verdict、非空 evidence、registry 内 id、全部 claim-review 并集覆盖及 execution/artifact/entrypoint 内容身份。受控 runner 对坏件 fail-closed 清理 staging，原子 `finalize` 与 shared/audit 消费侧分别重验。三轮盲审从零宽击穿族推进到 claim_id all 语义、对账键黑名单方向；收口再封同一 completeness critic entrypoint 三次注水及 0o500 staging 清理吞原拒绝理由。
- **F-09 Solana 身份链与真实案（工单 C）**：`solana-reconcile/v2` 升 `v3`，绑定 chain/mint/collection window、producer 与三份输入；补同案 `state→figures→A4→A5` 连续链及 PYTHIA 真实案纵向复验。三轮盲审从布尔精确判定族、16 项假覆盖清零推进到 symlink/物理 SHA/严格 JSON 接线锚；收口补 reproduce output 未消费字段 NaN 的严格 loader 接线锚。
- **存量影响**：AKE/B2/MOG/TAG 至少四案仍为 adversarial-review v2；已交付案不重跑发布闸不受影响，未来重发布必须按当前 runner 重做结构化 artifacts、execution receipts 与 v3 finalize，禁止手工补字段迁移。
- **文档与方法**：两侧 `_meaningful_text` docstring 明列白名单覆盖与刻意双写纪律；A4 对账键诚实声明 Mn/Me 可见组合符取舍，净室协议限制依赖组合符承载语义的文字，超顶用户批复明确要求白名单文字；casebook E-19 固化“实义判定漏网须白名单收严、对账键漏网须黑名单保全”的相反安全方向。
- **R10 台账**：清账 R10-2/R10-10/R10-11/R10-12；新增 R10-16～27 并逐条绑定三线盲审出处。原 15 条余 11 条，加 12 条后现役保留/接受项 23 条。
- **6.42.0 前身冻结基线**：批 2 独立分支收口时 `run_all.py` 共 96 个 suite 入口，其中 88 个 `test_*.py` 业务断言入口、8 个 lint/manifest/env 守卫；终验 96/96 PASS、rc=0。合并批 1 后的 6.42.0 最终分母与验证证据见 `maintenance/repair-20260814-batch2/merge_resolution_done.md`。`test_repair_batch_a.py` 44/44，F-02 定向套件全绿；invariant census、docs lint 与独立分支终态 SHA 见最终完工记录。

## [6.41.0] - 2026-08-14 — repair batch 1 五项共享面收口

按 `maintenance/repair-20260814-batch1/plan.md` 的七步协议收口批 1；本版只汇总已批准的五项修复，不扩张生产范围。

- **RV-07**：`publish_supersede` 成为 receipt kernel 原语，五个出口在失败时都落真实 `FAIL` 产物，旧成功件不再残留冒充当前结果。
- **RV-04＋RV-17**：`proxy_config` 统一代理解析与大小写/优先级口径；`stake_decode` 对缺失、截断和不完整输入一律 fail-closed。
- **F-03**：pass1、pass2、DuckDB 三个 replay 引擎统一 gate 失败的退出与正式产物隔离语义，诊断件不得混入可发布序列。
- **F-01**：图 1 阵营白名单单源化，producer 落 `figure1-legend/v1` 收据；A5 v3 同时绑定 state 与实际报告 PNG，形成发布闸与 seal 的双层信任根。
- **日期兼容**：图 1 consumer 精确补认 Solana `sol-rows` producer 的正式 UTC 序列格式 `%Y-%m-%dT%H:%M:%SZ`，不扩大其他日期解析面。
- **F-04**：四个入口移除位置 token，统一显式 token 来源优先级；sentinel 只参与内部控制，不进入正式输出。
- **质量**：新增 `test_repair_batch1.py` 已手动挂入 `run_all.py`；共享 invariant、P1-05 new-analysis 夹具、版本四锚与最终全量 suite 在步骤⑦统一验收。
- **盲审消化**：supersede 锁崩溃恢复原语＋token-file 回显抑制。

## [6.40.0] - 2026-08-13 — 六视角 BLOCK 修复工程四批收口（codex 13 findings＋GPT 5.6 Pro 交叉对账）

外部双审查（codex 六视角 13 findings 判 BLOCK＋GPT 5.6 Pro 11 findings 交叉对账）后，按用户定案范围（5 P0＋6.39.x 新引入 F-06/07/08＋GPT-F-06 用户裁决纳入＋流程债）分 A→B→C→D 四批修复，硬闸人工出口统一改**裁决收据**模式。工程目录 `maintenance/repair-20260813-sixlens/`（plan/工单/对抗审查/反例全落盘）。

- **批 A（发布收据验证链）**：F-01 EVM `tip_block` 双时点诚实记录（`model_probe_block==tip_block` 消费侧双字段验）；F-02 supply_truth formal 容差钳 ≤10bps、超出唯一通道＝`tolerance-waiver/v1` 人工裁决收据（裁决主体/UTC 时间/target 全等/replay_stats 与证据 sha 绑定/`observed_diff_bps` 覆盖检查）；消费侧 `decide()` 同源重算不手抄公式。
- **批 B（分布扫描族）**：F-03 快照对铸造总量 mint 逐 wei 闭合（分母绝不取影子键）＋发布闸快照 sha 与四查等值绑定（EVM=balance 收据 inputs.balances / Solana=bundle holder_outputs.owners，initial 与终态 final 双绑）；F-08 记录性 `upstream_receipts` 在场即三验＋path 白名单。
- **批 C（阵营序列 producer→consumer 链）**：F-05 四族 `validate_camp_spec` 共享互斥（跨阵营重复/大小写变体/JSON 重复键硬拒）；F-04 producer sidecar（`camp-series-provenance/v1`）＋burn 桶闭合口径分族＋camps spec 末点机械对账＋`--tol-pp` formal 写死 0.05（`figure2-check-receipt/v1` 留痕，发布闸复验）。
- **批 D（本批收口）**：
  - **F-06 flip 裁决收据制**：`--acknowledge-flip` 从"任意 10 字符理由"升级为 `flip-adjudications/v1` 收据文件（scan-schemas §4a）——每锚点行 `flip_fingerprint`＝三策略 policy_details 规范化 sha（底层数据一变收据自动失效必须重裁）＋三策略 top/份额披露；freeze 前置 3 只认 input_binding 绑定收据（不再信 ledger 自报 `acknowledged_flips`），重放装配同收据还原；A5 对报告 Markdown 实文核对披露值（消化轮 1 起锚定 report_locations 章节切片）＋ledger sha 与 freeze 记录绑定（封死单边改/删 ledger）。
  - **F-07 refresh 真事务**：`fetch_hypersync_v2 --refresh-manifests` 两阶段提交（prepare 全写临时件+fsync → commit 逐个备份+os.replace）；commit 失败逐文件回滚并按字节哈希验证，回滚失败保留 `.recover` 且 exit 1；CLI 补捕 OSError。全有或全无恢复由注入测试断言**字节回滚原样**。
  - **GPT-F-06 销户审计收口**：`audit_closed_accounts` 报告加 `status` 契约（CLEAN/NO_CLOSED_SAMPLED/LEAK_FOUND/INVALID_SAMPLE）；五类样本无效（gma 批失败/深挖全 fetch_failed/checked=0 且 closed>0/墙钟截断/undetermined 过半）一律 exit 1；closed=0 边界显式定案＝弱结论非查询失败。
  - **台账八项**：A-1 政策拒绝时旧收据作废归档（`supply_truth.json.superseded-<UTC>`，归档失败升格 exit 1）；A-3 envelope inputs 相对路径根治（`build_envelope(input_base=…)` 案内输入记相对路径＋消费侧 `validate_receipt(case_root=…)` 全部 inputs 强制解析在案根内，B-6 EVM `inputs.balances` 同族一并收口）；A-5 EVM balance/supply/supply_truth 三查 replay_stats sha 同源强制；B-1 Solana `holder_outputs` 文件级三验（validate_observation_bundle 消费侧，与 EVM 等深）；B-2 Solana new-analysis 发布闸 run() 完整端到端夹具落地；B-4 扫描器对绑定 replay_stats 补 sha/size 自验＋docstring 过度宣称改准；B-5 案根遏制分支定向红线；B-7 三账 `balance_source` 与四查 owner 快照等值绑定（冻结时点一致＋逐址数值等值，两链族）。
  - **schema 升版（B-3）**：`distribution-scan/v1`→`v2`，`denominators.total_supply_raw`→`mint_total_raw`（旧键名在真 `_burn` 案语义误导，IQ 差 34.9%）。
- **流程债追认（D-1）**：`11193f6`/`b9f8871` 两笔无版本号提交在此追认（B2 案 freeze 分母键修复系列，内容已含于 6.39.x 线，禁止倒插历史版本号）。
- **存量迁移后果（D-3）**：①6.39.4 后用过旧式 `--acknowledge-flip` 字符串的案（已知 MOG）重 freeze 会被"旧确认不再受理"拦下，须造 flip-adjudications/v1 收据重跑 trace（已冻结终态不追溯）；②6.39.5 及以前的 `distribution_scan.json` 是 v1 产物，重验必拒须重跑 initial/final scan（与"改扫描器即重跑"的既有算法绑定语义同款）；③存量绝对路径收据整案复制后被案根约束拒（原 N-1 语义，本就该拒），原地重验不受影响；新收据记相对路径可搬家。
- **R10 台账（本轮未修，台账保留）**：存量 6 条（F-09/10/11/13、GPT-F-07 deploy-sync 弱闸、GPT-F-09 env_check 覆盖）＋加深 2 条（A5 图例集合绑定、F-12 改名降权）＋批 C 终验 3 条（C-R1/2/3）＋批 D 评估 2 条（A-2 approved_tolerance_bps 硬顶待用户裁决、A-4 EVM 链上观测件锚定设计留档）＋批 D 消化轮 1 追加 2 条（R10-14 entity_freeze 案外 sha 锚设计、R10-15 check_bound_file 绝对路径案根强制），合计 15 条 → `maintenance/repair-20260813-sixlens/r10_ledger.md`（终验 BLOCKER-1 勘误：此前枚举漏计消化轮追加两条）。
- 成本：批 D 单会话施工（前三批 codex 分批施工＋对抗审查另计）；质量：run_all 全量绿、契约 146 条双向闭合、invariant 46 原子写登记、反例矩阵落 counterexamples/ 可重放。

## [6.39.5] - 2026-08-12 — distribution 语义重验假阳性修复（split-run 三闸死环）

- **坑**：initial `distribution_scan.json` 由 −1 生成（案根尚无 preflight 副本）；−2 按 G8 同目录要求把 `channels_preflight.json` 拷入案根；A5 `audit_release_gate` 重验 initial 时重算收录该副本 → `upstream_receipts` 与存档漂移报"语义与独立重算不一致"。G8 与该重验对同一文件的案根存在性要求相反，`build_html --state` 又锁死案根布局——三闸物理互斥，split-run 案必卡（TAG 案实撞，用户批准修复）。
- **修**：`holder_distribution_scan.semantic_payload()` 把记录性收据 `input_binding.upstream_receipts` 剔出语义比较（同款先例=labels_manifest.path 剔除）。收据不参与五桶分区/阈值/判定计算；final 对 handoff_manifest 的强绑定由 validate_scan 显式检查承担，不受影响。
- 顺手修存量断链：6.39.4 漏 bump pyproject（test_version_consistency 红）。
- 成本：A5 卡闸排查约 20 轮 Bash；质量：SUITE 全绿后案子交付恢复，无判定语义变化。

## [6.39.4] - 2026-08-11 — provenance 敏感性闸粒度修复（MOG 案随案落地）

- **触发**：MOG-ETH-BASE −2 freeze 前置三型翻转全无出口：①清零实体残渣库存（0.00003% 供应）来源排序翻转卡死整案；②现仓翻转仅在 Coinbase 同所双热钱包终点之间（语义等价）；③项目方峰值 mint 直分 vs 主池回收双来源量级接近＝真实混合结构。
- **修复**（trace/freeze 两侧同步，fail-closed 保持）：`NEGLIGIBLE_STOCK_PCT=0.01`——锚点库存 <总供应 0.01% 不入翻转/顺序判定（明细照记标 `negligible_stock`）；`--acknowledge-flip ENTITY:ANCHOR:理由`（≥10 字符、禁预防性豁免）书面确认真实多来源翻转，确认不改 stable 真实布尔、新增 `publishable` 承载 exit 语义，确认进 `acknowledged_flips`+`algorithm_params` 随 freeze 重放还原；`recompute_provenance_sensitivity` 同步两豁免（未确认翻转仍拒）。
- **测试**：翻转 fixture 放大至非尘埃保持"未确认必拒"原意；新增尘埃翻转豁免用例（伪造由重放语义摘要兜底）；trace 套件 TOTAL 1e12→1e6。handoff 67 项、trace、run_all 全绿。
- **纪律**：确认过的翻转锚点，报告构成结论必须按三策略并列披露，不得发布单一主导来源。

## [6.39.3] - 2026-08-09 — accounting_gate 目标块绑定参数：存量案升级死锁修复

- `shared_release_receipt` 要求 accounting 与 reconciliation 的三键 target（chain/token/as_of_block）
  全等，但 `accounting_gate.py` 硬写 `as_of_block=tip` 且无钉块参数——存量案按 §157 重跑当前
  accounting 时 tip 必然漂离冻结块，聚合器永拒（APU 0801 案首触发；R9 纵切片同环境一次跑完
  tip 恰同故测不到）。
- 修复：加 `--as-of-block`（收据 target 绑定块）。模型探测语义不变仍在当前 tip 执行，
  `tip_block` 字段忠实记录探测时点；两字段并存=目标绑定与探测时点分离，无语义撒谎。

## [6.39.2] - 2026-08-09 — entity_source_trace 进货单并列序非确定性修复

- `direct_upstream` 进货单 SQL `ORDER BY SUM DESC` 无次级键：金额并列的上家在 DuckDB
  并行聚合下跨进程顺序漂移，freeze 的 provenance 重放语义 sha 与台账对不上，fail-closed
  误拒合法冻结（APU 0801 案 12 址实体、68 上家多组并列首次触发）。
- 修复：`ORDER BY 2 DESC, 1` 加地址字典序 tie-break。语义零变更（集合与金额不变，仅并列序固定）。

## [6.39.1] - 2026-08-09 — 分布扫描 validate 可移植性修复：宿主 checkout 绝对路径不得进语义比较

- **根因（APU −2 开工 verify 实弹暴露）**：`_label_manifest()` 把运行时脚本所在 skill checkout 的绝对路径写进 `input_binding.labels_manifest.path`，而 `semantic_payload` 把整个 input_binding 纳入语义比较——−1 在 worktree 下补齐、−2 在主目录 verify，labels 内容哈希逐字节一致仍被"scan 语义与独立重算不一致"误拦；即 validate 隐含要求"验证必须在生成时的同一 checkout 路径下跑"，违背案产物自包含可审计原则。
- **修复**：`semantic_payload` 比较前浅拷贝剔除 `labels_manifest.path`，保留 `sha256/size` 内容身份——labels 内容漂移仍被重算 sha256 抓获，宿主路径不再影响语义。落盘产物仍记完整 path 供溯源，零字段删除。
- **连锁处置**：`input_binding.algorithm.sha256` 为脚本自哈希（设计如此，fail-closed：算法变更→旧产物须重产），本修复后 APU 案 initial 扫描按新脚本重产＋superseding manifest，重产前 diag 已证明重算语义与原落盘逐字段一致（唯一差异即 labels path），零信息损失。SUITE 全绿（含 distribution gate red-green 契约）。

## [6.39.0] - 2026-08-09 — APU 案 ANOM-012 存量迁移三工单：首个真实 EVM 受控全链暴露的缺口收口

- **工单一（replay_stats 覆盖截止块契约，归因=修复中新引入）**：6.34.0 给 `verify_recon` 加"replay_stats 截止块==--end-block"必读断言时未同步任何生产者——三 replay 引擎从不写 `max_block`，断契约存活 4 个版本，测试全绿全靠 fixture 手写 stats 掩盖（7.5 手写 receipt 反面实证），APU 真实首跑必断。修复=单点注入 `replay_provenance()`：`max_block = 重验过的 preflight expected_to − 1`（采集覆盖语义而非最后事件块，尾部空块不缩小覆盖；值取自 `validate_preflight_artifact` 重验产物，非引擎自报），`replay_duck`/`replay_pass1`/`replay_stream` 三引擎自动同深度；`max_block` 入黄金基线 STATS_CONTRACT 对表键。真实引擎产物直连 verify_recon 的消费连线测试补上（修前死于截止块、修后推进到 RPC 段），篡改 max_block 拒绝负例留档。
- **工单二（太古 done 官方迁移，归因=历史漏检）**：`--refresh-manifests` 只认 `hypersync-v2-done/v2`，无 schema 字段的太古五键 done（from_block/next_block/token/url/elapsed_s，v1 采集时代）被"不支持迁移的旧 schema: None"拒绝，新版 channels preflight 对存量数据直接 BLOCK 且无官方出路（APU −2 现场手拼被正确否决后只能回退）。修复=`_prehistoric_refresh_candidate`：parquet 列集经 `inspect_run_files` 实读硬验与现行采集器查询形态一致（列集是查询形态的物理证据，非对旧声明的信任）后重建全部边界与文件指纹，`capture_from=from_block`、`to_block=next_block`，留痕 `refreshed_from_schema=pre-schema-v1`；显式 `"schema": null` 的畸形件不走此分支照旧拒绝。`ensure_outdir_identity` 挪到 done 升级落盘后（其迁移预检要求磁盘 done 已带现行 query_schema，太古升级前不满足；唯一性已在收集阶段验证，ensure 幂等可自愈）。两阶段全验证-或-全不写事务保持：越界 run 使整体拒绝且好 run 的 done 字节不变。真实 APU 存量（943,807 行）副本实弹：迁移→receipt→preflight→`replay_stream` 真跑 gate_pass 全链通过，partial_run_ 前缀目录正确忽略。
- **工单三（旧 −1 产物格式迁移命令，归因=历史漏检）**：新增 `scripts/report/migrate_legacy_case.py` 作为旧案目录唯一官方迁移路径（禁手拼）：①data_map 哈希剥 `sha256:` 前缀（仅精确形态 `sha256:<64hex>`，其余值原样），剥后对在场登记文件重验哈希——失配整文件拒迁（不把腐坏账本洗白成合规格式），登记文件已清理只计数不阻断；②candidate_universe 条目补 `id=cid` 保留 cid（与 APU −2 现场修法同型），既无 id 也无 cid 拒迁；③anchor_plan 无 kernel receipt 只报 NEEDS_RERUN 指引现行 anchor_plan.py 重跑——receipt 是执行证据不可补票。分文件独立原子处置（改前 `.bak_migrate_<UTC>` 备份），全合规 exit 0 / 有拒绝或待重跑项 exit 2。消费连线：迁移前 `verify_data_map` 拒、迁移后同校验器通过；幂等重跑不重复改写。
- **登记与文档**：`test_apu_legacy_gaps.py`（23 项契约测试）入 SUITE；`atomic_write_with_backup` 登记 invariant manifest（atomic_writes 43）；data-pipeline-evm-channels §迁移段与 split-run §3.1 步 2 补官方迁移指引。本次为工具工程，无代币分析结论；全部反例离线 fixture，正例由真实 producer 现场生成。

## [6.38.0] - 2026-08-09 — 供给真值闸 dead 沉没形态适配与闭合口径修正

- **sink 语义与重放统计单源**：新增 `supply_semantics.py`，统一 ZERO/dead 与“burn 另记、sink 余额照加”语义；`replay_duck`、`replay_pass1`、`replay_stream` 全部保留旧字段并新增 ZERO 流入、dead 流入/流出/净额四个 wei 级统计，黄金基线契约同步逐字段对表。
- **形态②自动回退与 v3 receipt**：主 `decide()` 及形态①容差行为不变；仅 EVM 主 FAIL 且拆分统计齐全时，在同一冻结块和同一 attested pool 批量读取 totalSupply/ZERO/dead 三值，按总量与逐地址四条件零容差闭合。混合形态、旧 stats、1 wei 偏差、地址间补偿及 RPC 部分失败全部 fail-closed；回执升级 `supply-truth-receipt/v3` 并记录 decision rule、burn form、主判定与 sink 对账。
- **余额闭合公式修正**：`verify_recon` 从 `sum_balances==mint−burn` 改为与 replay 记账一致的 `sum_balances==mint`，burn 继续独立落盘；shared release validator、invariant manifest、正式 fixtures 与持仓分布消费面完成兼容核验，v2 仅保留显式 legacy 拒收负例。
- **回归门禁**：先红留档后实现；真实量级 dead 沉没反例转 PASS，GNT 式 mint 与链上供给不等仍 FAIL，并新增 burn>0 纵向闭环覆盖 `verify_recon → supply_truth v3 → shared_release_receipt`。本次为工具工程，无代币分析结论；新增/扩展反例均为离线 mock。

## [6.37.0] - 2026-08-09 — R9 收敛修复工程收口：五 finding 四批＋两轮盲审，止损纪律与诚实降级首次全程落地

- **五 finding 处置**：R9-01（Solana accounting 以 CLI 声明冒充观测）→ 八步观测协议 `solana_observation.py`（GPA context.slot 唯一真值/前后 raw 一致/窗口重试/三方 supply 闭合/producer publish 前自跑 consumer 同一 validator），裁判 mainnet 实证 PYTHIA GPA 82k 账户 diff=0；R9-02（anchor plan↔spotcheck 断契约）→ consumer 语义重放（`anchor_selection.py` 单实现，plan 参数对真实输入确定性重算逐位比对，伪造等价于真跑 producer）+per_cell>=2/edge_max>=3 下界双端共享；R9-03/04（fetch_pool_swaps/scan_token_accounts 失败 exit 0+stale 旧件冒充当前成功）→ 退出码传播+启动先隔离+ERROR side receipt+CSV/marker 迁 receipt-kernel 联合事务；R9-05（solana-cluster attestation 纯声明）→ 可执行适配器键（真 import 到 callable）+六能力探针+`@formal_evidence_target` 错身份零业务前置探针+四链真实纵切片，formal_ready 自然导出。
- **批四防复发守卫**（AST/机器判据挂 validate_manifest+SUITE 必经）：main 退出码传播（含顶层裸调）/formal E2E 现场 producer 调用图/capability 错身份执行/失败产物登记分母自动派生/anchor 弱覆盖下界。**F-B4-01（G2 执行证据静态守卫）三轮修复三次被 opus 复审攻穿（未 import 裸名→函数内遮蔽→模块层/外层作用域重绑定），触止损 3/3 冻结，用户裁决降级接受**：定位=内部元守卫尽力挡低级伪造，模块层伪造 KNOWN-OPEN 无独立运行时兜底，docstring/ledger 诚实记账（教训:静态 AST 判运行时执行原理不可闭合，逐层堵语法是打地鼠；真闭合方向=runner 进程指纹收据，列后续立项）。
- **两轮 codex 全库盲审（互盲,基线 45bf8f3）**：Round B 台账重放 49 项=43 CONSISTENT/1 INCONSISTENT/5 环境不可复核——full-F-03「豁免已登记」先行于事实被抓，整改=第四类豁免独立台账 `exemptions.md`（调用图/formal registry/能力矩阵三证据+四条自动失效条件）+`test_exemption_guards.py` 防回流负测挂 SUITE+§7 批三 B3F_COMPLETE 履约登记+SHA 回放工具 `sha_replay.py` 入库（口径/时点声明）。Round A 六视角判 BLOCK：六条存量 finding（git blame 全早于 R9 基线,replay→state→figures 呈现层等 R9 未触子系统）全部读码坐实,登记 final_acceptance「R10 候选清单」用户裁决下轮修——**重点 RA-01(P0) 图 1 阵营序列自报无值域/闭合/绑定校验、RA-02(P0) 阵营互斥无 validator 重复地址后项静默覆盖**；RA-06 即 F-B4-01 降级项,盲审独立复现并自评「已诚实登记不夸大」=降级记账经受住外部检验。
- **维护方法论新增（R9 章,均已写回 maintenance-review-repair.md）**：批内修复循环本身必须过攻击式审查（codex 自报修完≠闭合,三轮「换语法就穿」实证）；opus 复审工单四预案（禁 du/find 全盘、第一命令建最小镜像脱离大 worktree、连续 2 次无响应即交付、Write 后 ls 确认落盘）；密钥/脱敏降档纪律（安全边界够用即可,不外溢质量残留）；producer/validator 约束机器同源范式。
- **收口台账**：ledger 49 项主表/详情零空栏,diff→finding map 37 唯一 SHA 全链回放 PASS,全量 suite 90 项（含新豁免守卫）Fable 环境全绿,invariant_scan exceptions=0,四链 formal ready。R9 campaign 止损记录：批一 2 循环/批三 2 循环/批四 3 循环触冻结（首例走完冻结→用户裁决全流程）。

## [6.36.0] - 2026-08-06 — 结构收敛工程阶段 3+4 收口：receipt kernel＋垂直切片迁移＋net.py 演进，15/15 全绿

- **阶段 3（九项摘牌，commit 6a9204b）**：新建分层 `receipt_kernel.py`——envelope 层（target 三键必填/producer 自动绑当前哈希/inputs file_ref 含 symlink+逃逸防护/mode 必填/verdict-exit 一致表）+四型原子发布原语（exclusive 硬链接独占/overwrite 单文件/txn 双文件事务回滚/restore_on_fail 失败还原），ERROR 一律走 `<name>.error.<run_id>.json` side receipt 不覆盖既有 PASS；独立 `receipt_validate.py` 不 import kernel、哈希/路径/语义表全独立实现防"同错同过"；golden+故障注入测试（坏 target/文件改写/磁盘满/并发写/旧 PASS 保护/逃逸/双文件回滚）。EVM 三件垂直切片迁移（verify_recon/supply_truth_gate/time_spotcheck）换 kernel envelope，同 fixture 旧新对表业务字段零漂移；嵌 R7-12（eth_chainId 启动对表，错链 exit 2 不发 eth_call）、R7-04（--replay-net-raw 与 --exploration 互锁，EVM as-of-block 必填，Solana 如实记 observed_context_slot+"当前观测非冻结时点"语义声明，聚合器强校验）、R7-13（plan chain/token 与 CLI target 对照+plan file_ref）。个案修 R7-08（declared gate 硬查 exit 0，reconciliation_report.json 纳入 AUTO_GATES）/09（正式空标签双端 exit 2）/10（归档三闸前 staging+os.link 独占转正，绝不覆盖既有归档）/11（三日期字段方向性比较：staging 早于发布=FAIL）/14（risk_flags 去重+strip；非作者对抗审首例=codex 审 Fable 上轮亲修代码）/15（MAINTENANCE.md 七字段指向 DECISION_FIELDS+三闸事务描述）。
- **阶段 3 验收返工（Fable 边界外攻击 4/4 得手）**：①`finalize_envelope` 业务字段 kwargs 可静默覆盖 producer/mode/inputs 全部身份绑定（疏忽即可绕）——修为七保留键冲突拒绝；②`publish_txn`/`publish_restore_on_fail` 回滚二次失败时 finally 连备份一起删（旧正式产物零残骸丢失）——修为 committed 标志分路+回滚失败保留 `.rollback.` 备份+异常带人工恢复路径；4 新反例先红后绿，攻击复跑 4/4 SAFE。
- **阶段 4（最后三项摘牌）**：`net.py` 新增 frozen `Result`（`__bool__` 一律 raise 禁隐式真值）与登记式 `curl_json` 后端（`REGISTERED_TRANSPORT_BACKEND` 常量供 invariant_scan 识别；rc=22 归 http_status、其他非零归 transport、空 stdout/坏 JSON/NDJSON 任一行失败归 decode；重试耗尽返回 error 不伪装；"成功空数据是否可信"明确留给 adapter），旧 RpcPool/http_get_many 接口零改动。`anchor_sampler.py` 迁移（R7-02/03）：传输失败/空响应/不可解析绝不表达"无活动"（失败分型 fetch_fail/unproven_empty/observed_slot_beyond_cutoff/no_converge），任一日失败走 kernel ERROR side+exit 2；每行绑定 chain/mint/endpoint/as_of_slot，resume 逐行验身份+日期唯一+slot≤cutoff，旧格式（无身份列）一律拒绝复用提示重采（存量三币本在重采清单）。`window_fetch.py` 迁移（R7-06）：正式窗口必须 0≤from≤to 且 segments≥1，非法范围开文件前 exit 2；gap 时旧正式文件原子改名 `.stale.<run_id>` 防被下游消费；receipt 迁 kernel。R7-06 消费面评估裁决：不无条件扩 handoff（window_fetch 为按需补采件，强制槽位会误伤未调用案例），正确路线=collection plan 声明式条件消费，留独立切片。
- **工程收口台账**：R7 15/15 全绿（EXPECTED_RED 清空，防装死终态验证）；五个零复算——手拼 wrapper=0/未登记 transport=0/重复链能力定义=0/无期限白名单=0 四项机器达成，手写 envelope 在已迁切片内=0、全库 35 个登记 producer 已迁 5（A2 三件+anchor/window），其余 30 个按垂直切片逐版推进（一次全迁=大改新代码成下轮缺陷源，正是本工程诊断要避免的）；invariant 44/51/36/37/54/0（transport +1=curl 后端登记，atomic 净减 2）；SUITE 67 入口全绿。成功判据第 4 条（连续两轮盲审新引入=0 且半修残留=0）待用户择期发起盲审裁决。

本次为结构收敛工程（维护轮），无代币分析轮次或结论质量指标；15 项全部转绿，四阶段两 commit（6a9204b+本版）收口。

## [6.35.0] - 2026-08-06 — 结构收敛工程阶段 1+2：分母清单＋先红隔离＋受控 runner＋链能力单源

- **背景**：第七轮六视角 review（codex 新线程审 main@d8bd3c5）出 15 项，Fable 复核 15/15 属实（修正 2 项定级、3 项归因、1 处 Solana 修法物理不可行），归因新引入 5/半修残留 7/历史漏检 3——用户判定逐点修复模式失效，要求彻底方案。诊断（@CX codex 交叉复核修正后）：病根=横切不变量的实施面分散（receipt/失败语义/原子写各 20-40 处手工实现）且**分母从未被机器证明完整**，同族 rg 半径随反例漂移；每轮修复自身又新增手工实现（本轮 5 项新引入全部长在上轮改写代码里）。codex 复核另贡献：否决新建 transport.py（库内已有 net.py，再建=第二套公共网络层）、runner 从"验刚落盘"升级为编排执行、三集合升级为能力注册表、白名单加清偿到期；Fable 坚持成功判据收窄（连续两轮"新引入=0 且半修残留=0"，历史漏检类不计入——探测器视角进化的产物不可达零）。方案四阶段，本版=阶段 1+2；15 项先红测试逐阶段转绿，全绿+五个零机器复算=工程收口（judged at 6.36.0）。
- **阶段 1（零生产变更，commit 77dba73）**：`invariant_manifest.json`+`invariant_scan.py` AST 级双向对账守卫——receipt 生产/消费、transport、原子写（人工判定四类语义）、正式入口全量登记，删/加两路注入 self-test 常驻；分母从一次性 rg 变机器可复算。`test_r7_findings.py` 15 项按"修好后目标行为"写断言基线全红，expected-red 隔离三态（红+集合=计数、绿+集合=FAIL 强制摘牌、红+集合外=FAIL）防测试装死。验收返工 1：SCOPE 漏 labels（18 件）/prices/根部（任务书目录清单遗漏=Fable 责），补录后 transport 32→35、atomic 30→36、入口 46→54。
- **阶段 2（R7-01/05/07 转绿摘牌）**：新建受控 runner `reconciliation_report.py`——读 job spec 在 case 目录编排执行四查 producer 子进程（producer 白名单+当前哈希、receipt 执行前必须不存在、argv 只作参数不可换执行体、路径逃逸/符号链接拒、输入与 receipt 前后双快照、失败也落 FAIL wrapper、落盘失败 exit 2 不留半成品），wrapper 顶层绑定 runner 自身 path+sha256；聚合器 `shared_release_receipt.py` 新增 RECON_RUNNERS 校验（无绑定/哈希不符拒）+wrapper 顶层 PASS/0 硬查。7 条拒绝反例测试全建（`test_reconciliation_runner.py`）。新建 `chain_registry.py` 单源：每链 canonical/aliases/formal/exploration/capture_evm_family/has_labels_table/recon_adapter/identity_adapter，派生函数供 audit_release_gate（本地 FORMAL_CHAINS/KNOWN_CHAINS/CHAIN_ALIASES 删除）、handoff_manifest（READY 只认 formal——arbitrum 等探索/采集链拒，R7-07 转绿；EVM 时间抽查家族判定改 evm_family）与身份闸两件派生；`test_chain_registry.py` 一致性+破坏性传导反证。split-run/independent-audit-protocol 同步"wrapper 禁止手拼、旧案重跑 runner"。
- **验收（Fable，注入攻击制）**：阶段 1 四路注入全拦（摘牌未修/manifest kind 错位/schema 删项/semantics 非法）；阶段 2 别名大小写攻击全防（ethereum/ETH 解析 READY、Arbitrum/avalanche 拒）、runner 代码逐段审读。**边界外攻击战果两项返工**：①协议文档声称拒绝"手拼自报 wrapper"过强——实测填对 runner 哈希的手拼仍过（设计内诚实边界），措辞压回如实并明写"内容绑定非单机执行证明，防线=疏忽可绕升为必须显式造假+git 追踪"；②同族清单漏两处身份闸本地链集合（identity_snapshot_receipt/entity_identity_gate，5 链 EVM 快照与 6 链全链闸语义不同），按各自语义派生化+一致性断言补齐，全库残留复扫零命中。
- 测试面：新增 invariant_scan self-test、test_r7_findings（15）、test_reconciliation_runner（7）、test_chain_registry；SUITE 全绿，r7 隔离剩 12 红。阶段 3（receipt kernel+个案修 R7-03/04/08/09/10/11/12/13/14/15）、阶段 4（net.py 演进+anchor_sampler/window_fetch 迁移=R7-02/06）待续。

本次为结构收敛工程（维护轮），无代币分析轮次或结论质量指标；15 项中 3 项转绿、12 项在册待阶段 3/4。

## [6.34.0] - 2026-08-06 — 六视角首战修复轮：13 项五批全修＋验收返工 1 项

- **背景**：6.33.0 沉淀的六视角方法论当日首战——codex 按标准指令模板对 main@fca61ad 全库 review，出 13 项（7P0+4P1+2P2）判 BLOCK；Fable 逐项复核 13/13 全属实零否决（F-06 相等/反向区间假成功亲手复现坐实；F-10 补强证据=labels_resolver 确实消费 risk_flags 四档）。修复轮 codex 续 review 线程施工（首次发起经 companion --resume 掉"丢 --write 只读回退"已知坑，codex 零副作用停手报告，改 `codex exec resume <会话ID>` 显式 workspace-write 后单 turn 完成），工单纪律全程履约（每项五栏工单+RED/GREEN 记录，样本归档 `archive/fix-worklogs/fix_sixlens_20260806.md`）。
- **批①发布证据链（F-02/03/04/05）**：`verify_recon.py` 从 70 行零退出码打印脚本重写为参数化 receipt 生产器（`evm-reconciliation-receipt/v2`：绑定 chain/token/end_block/四输入文件哈希/供给闭合+逐地址对账+GMGN 观测；不一致 exit 2、RPC/输入错误 exit 1、恒落盘 ERROR 回执）；`anchor_sampler.py` 失败日聚合 exit 2+receipt（绑定 mint/日期范围/覆盖/失败明细）；`window_fetch.py` gaps 非空只留 `.partial`+exit 2，空才原子发布正式文件+覆盖 receipt；`shared_release_receipt.py` 新增 `validate_reconciliation_check` 逐类 schema+语义验证（target 绑定、观测硬断言、wrapper 与 receipt verdict/exit 双向一致、未知 schema 拒），wrapper 自报降级为比较对象。
- **批②采集器产物纪律（F-06/07/08）**：`fetch_pool_swaps.py` 区间前置校验（0<=from<to，违者 exit 2 零产物）+临时文件原子提交；同族等深覆盖 `fetch_hypersync.py`/`fetch_hypersync_logs.py`；`fetch_gmgn.sh` 失败时旧正式文件 mv `.stale`（标记失败也算 FAIL）。
- **批③标签发布等深（F-09/10）**：`add_labels.py` 增量路径升为 validate+benchmark+manifest 三闸机器串联事务（任一 FAIL 全回滚含 manifest 备份恢复）；`roundtrip_check.py` 决策字段 6→7（risk_flags 硬比）+六 provenance 字段白名单 WARN 明细禁静默。
- **批④正式输入必填（F-01/13）**：`entity_source_trace.py` 正式模式缺 `--labels-file` exit 2、`--allow-no-labels` 探索旗标与标签互斥、ledger 带 exploration 标记且 freeze 必拒；`handoff_manifest.py` READY 必须显式已知 `--chain`+非空 `--contract`，verify 侧空/未知 scope 拒；`commands-staging/token-analyze-1.md` 收工步同步新契约（已部署同步，SHA 一致）。
- **批⑤文档（F-11/12）**：retrospective 10KB 双口径改"7.5KB 预警、8192B 硬上限"（rg 确认无第三处）；casebook README 回流文本改指复盘流程登记，分析会话不触 archive（Fable 小手术版）。
- **验收（Fable，不采信自报）**：SUITE 亲跑全绿；F-06 两条原始反例+负数边界外变体亲手重放全拦；聚合器/verify_recon/anchor_sampler diff 逐段审读（字段来源=receipt 本体+RPC 实测、失败分支三级闭合）；**边界外攻击命中 1 项新引入返工**——risk_flags 为 `|` 拼接集合语义，现役 privacy 表实测 59 行历史未排序串,codex 版裸串比较会在增量 sorted 与存量原序相遇时误伤合法发布：`_decision` 增规范化（拆分/滤空/排序重拼），先红后绿闭环（stash 旧实现新测试 exit 1、修复版 exit 0，绿例+空段变体+真实子集差异红例三连）。
- **同族裁决（8 项 default=None，全部维持现状）**：fetch_sqd_evm/fetch_alchemy/fetch_hypersync_v2(collect)/pull_lp_events/cluster_sensitivity/price_check/decode_txs/anchor_plan 均为采集或分析辅助件，不直接进入 READY/freeze/发布链，范围完整性由下游必经闸（finalize/receipt/preflight/entity_source_trace/handoff）锁死——上游保持灵活、闸装必经之路，不扩大改动面。
- 测试：新增 `test_sixlens_receipts.py`（伪造回执/target 漂移/verdict 矛盾/recon 不闭合/anchor 失败日/window gaps）+`test_sixlens_docs.py`，扩展 9 个既有测试文件；33+2 文件改动。归因分布 1 新引入/6 半修残留/6 历史漏检+验收再抓 1 新引入——"修复代码是重灾区"两轮连证。

本次为修复工程，无代币分析轮次或结论质量指标；review 发现 13/13 修复+验收返工 1/1 闭环，发布证据链自报字段清零。

## [6.33.0] - 2026-08-06 — 维护方法论文档化：六视角 review 清单与修复工单模板沉淀为维护件

- **背景**：三轮全库 review 实战（6.11.0→6.13.0→6.14.0）复盘出的仓库维护方法论（六视角 review 清单、发现强制归因、按不变量修的修复工单模板、防屎山三方向、连轴收口标准），此前只散落在 CHANGELOG 叙事与会话记忆里靠人记，6.15.0 起历轮实际执行所依据的方法一直没有权威落点。用户拍板沉淀为文档。
- **新增 `references/maintenance-review-repair.md`（维护件）**：六视角清单逐条带出处事故（字段来源自报/fail-open 装成功/存量迁移两问/同族调用面/双向一致性/闸可绕性）；两个可直接复制的模板（标准 review 指令、修复工单五栏）；归因三分类（新引入/半修残留/历史漏检）定为 review 报告必填栏；防屎山三方向标注已落地版本；收口标准与提出后五层实战进化（同族等深/边界外一步/破坏性注入/grep 清零/升 schema 连下游）。
- **登记**：`runtime_docs_manifest.json` maintenance 名单第 3 件（与 attic.md、labels/MAINTENANCE.md 并列，不进分析上下文、不占两跳路由）。曾尝试在 SKILL.md 加一行身份声明，被 docs_lint「maintenance 禁列」守卫拦下（豁免仅 attic.md 一条）——顺闸撤回，维护件可发现性以本 CHANGELOG 条目与 manifest 为准，不污染分析路由。

本次为方法论文档化，零判据变更、零代码变更；SUITE 全绿见验证。

## [6.32.0] - 2026-08-06 — 第五轮外部审查 13 项修复：发布门禁假成功关闭与路由漂移收口

- **第一批｜标签发布安全（F-01/F-02/F-05）**：`roundtrip_check.py` 任一正式链缺表 exit 2（此前五链 staging 全缺仍打"可安全发布"exit 0，实测复现），同键行升级行级比对（category/tier/merge_policy/balance_policy/status/name 六决策字段，退化明细＋--dump 落盘）；`benchmark_labels.py` 五主表齐全且非空硬闸（默认与 --labels-dir 双模式，header-only 算空），manual 设施召回不足计入 total_violation（补齐 MAINTENANCE 已承诺未执行的硬断言）；`add_labels.py` 回滚区分原有/新建目标，validate FAIL 时新建坏表直接删除不再滞留发布目录。
- **第二批｜采集器 fail-closed（F-03/F-04/F-06）**：`fetch_pool_swaps.py` 请求耗尽/游标缺失/停滞一律 exit 2，唯一正常出口＝游标到达 --to-block；`fetch_hypersync_logs.py` 缺 next_block 未达 tip、游标停滞（原为原地死循环）、非法类型均 exit 2，[COMPLETE] 收紧为确认到 tip；`fetch_gmgn.sh` 先写临时文件、JSON 校验通过才原子落名，失败聚合 exit 1 并输出成败清单（原固定 GMGN DONE exit 0 且留半截 JSON）。
- **第三批｜密钥取用契约（F-07）**：三支 HyperSync v1 脚本移除 token 位置参数（进程参数/shell 历史可见），统一取用优先级＝显式 --token-file > HYPERSYNC_TOKEN > 默认 ~/.config/hypersync/token；`data-pipeline-evm-channels.md` §3.1"自动读取（fetch_hypersync 内置）"不实表述改为真实行为，正式命令示例与 config.example 注释同步；两个既有 collector 测试连带升级到新参数形态。
- **第四批｜文档漂移（F-08/C-01～C-05）**：SKILL.md 路由表补 A4.5 行与 G11/终版分布图（此前停在 v6.20.0 前旧骨架）、Arbitrum 句改准确口径（G8 探索档已具备，真 blocker＝labels-arbitrum.csv 与正式标签门禁）；casebook 三续册进入 A3 过闸点名与 runtime manifest（scope 增 casebook glob＋7 文件入 listed），contract routes 增 SKILL 原子阶段双向对账；MAINTENANCE"七链强制出现"改五链 goldset 准确口径；retrospective 删 84KB 过期动态快照（实值 48KB）、10KB 死触发线改 7.5KB 预警线（先于 8192B 硬闸）；context-discipline 管道兜底 head -30 统一为 head -20。
- **决策留痕**：外部审查三处论断经验收方复核修正后执行——C-02"三册未路由进 A4"减弱（research-workflows §2 原有该路由，实际缺口＝A3 过闸点名与 manifest 覆盖）；F-03 不新增上界参数（--to-block 原为 required，缺的是用它判完成）；F-04 补审查未发现的游标停滞死循环。验收方增补：casebook README supply 行同步续册名。
- **验证**：六个新增反例测试先红后绿挂入 suite（roundtrip 缺表/退化、benchmark 缺链/空表/manual 注入、add_labels 双型回滚、fetch 三场景 fail-closed、gmgn 假 CLI 三场景、token 无位置参数）；验收方独立重放两项原始复现均转红、六项边界外攻击（pool 停滞与倒退、logs 双缺与非法类型 next_block、0 字节 staging 表、privacy 子表缺失）未击穿，另亲验半截 JSON 拒收与 token 优先级链；真实发布库默认 benchmark 绿例未误伤。全量 suite 全 PASS、docs_lint 57 文档 PASS、SKILL.md 7522B（8192B 硬闸内）。

本次为工具工程，无代币分析轮次或结论质量指标；发布/采集侧可复现假成功路径 6→0，casebook 六分册全部进入执行路由，suite 新增 6 项反例测试。执行分工＝codex 改文件、Fable 验收代 commit（v6.20.0 模式）。

## [6.31.0] - 2026-08-06 — 第四轮瘦身修复：代码、文档与契约基线收口

- **stepA1｜三现役脚本参数化**：`cadence_rank.py`、`multicall_balances.py`、`probe_escrows.py` 改为 argparse 注入必需输入，`cadence_rank.py` 的 stdout 与 `tier_final.json` 增 identity 段绑定 pools、parquet、total_supply、formation_cutoff；新增 `test_param_scripts.py` 覆盖无参失败、旧案字面量清除和 identity 回显。修复背景是三脚本仍硬编码 EGL1 池、SIREN token/scratchpad、CLUDE targets，而 playbook 又把它们列为必跑脚本，在新标的上会静默算错对象。
- **stepA2｜孤儿删除与 SQD v1 退役**：删除零现役残引的 `probe_wallet_batch.py`、`probe_token_account_history.py`、`accumulate_gmgn.py`；`fetch_sqd_transfers.py` 退役至 `archive/solana-sqd-v1/`，明确其缓存路径与 v3 meta schema 不兼容，恢复须先写一次性 importer。`replay_edges.py` 曾错误提示先跑 v1，现改指向 v2；`fetch_sqd_transfers_v2.py` 删除只会在 v2 hashed 路径打开时出现的 v1 meta 迁移死分支。
- **stepB1｜文档小修与叙事压缩**：labels README 的动态计数改以同目录 `manifest.json` 为准，`address-book.md` 改为 manual 命中后按地址精查、禁止整本加载，并把 runtime stage 收紧为 `on-hit`；Helius 环境断言改为运行时检测 key，另修 capture §6 锚点、v1 `next_slot` 残留与 `decode_txs.py` 自引用。`report-template.md`、`research-workflows.md`、`retrospective.md` 只留现行规则、机制依据与废止防回流声明，变更史统一指向 CHANGELOG。
- **stepC1｜契约完整性封口**：删除 `>=138` 数字下限，新增 `contract_ids_snapshot.json` 保存 138 个排序契约 ID；测试要求 `contract_manifest.json` 的真实 ID 集合与快照完全相等，并分别逐名报告缺失项和新增项，契约增删须同步快照并在 CHANGELOG 留记录。五组锚在场断言保持不变。
- **决策留痕**：第四轮外部审查建议“138 条契约压为 5 个契约族”，经复核否决：needle 实测为短机制锚（中位 13 字符），锁的是 schema 名、产物名和门禁编号，且 `contract_manifest.json` 不进入 AI 运行时上下文，合并没有上下文收益，反而拆弱逐针防线。同理否决 runtime selector 脚本提案：AI 路由权威已是 `SKILL.md` 两跳，增加第三层路由信号只会增加歧义。
- **验证**：三批均由定向反例和文档守卫验收，最终全量 suite 53/53 PASS；判据算法、`contract_manifest.json` 结构与五组锚均未改变。

本次为工具工程，无代币分析轮次或结论质量指标；现役脚本旧案硬编码 3→0，孤儿脚本 3→0，契约完整性基线由数字下限升级为 138 个 ID 的双向集合快照。

## [6.30.0] - 2026-08-05 — 第三轮瘦身收口：运行时上下文与守卫单源化

- **批次 A｜入口与退役面**：开局读取按完整版、split-run、净室复核四入口分派，环境手册改为 preflight 扫坑、异常时深读；HyperSync Par/watchdog 旧族与 M-01 守卫迁入 archive，现役 M-02 标签守卫拆留，正式 v2 主线不动；报告图路径示例和 EVM 主册链标题三处漂移修正。
- **批次 B｜现役文档减负**：Solana 脚本 README 收敛为 26 项薄索引，旧流水账完整快照迁档，curve_cost 校准规则回填管线分册；入口文档只留当前规则与失败后果，新增 S-09、S-10、E-18 三条六字段判例；address-book 删除人工双录表，以含机制注释的 CSV 为唯一结构源并提供按需人读渲染，运行时 206 行逐字节不变，sync 守卫升为 `(chain,address)` 复合键。
- **批次 C｜守卫与清理**：逐路径清理 ignored `.pyc`、8 个 `__pycache__` 与空 `scripts/collect/`；`contract_manifest.json` 升 `contract-manifest/v2`，原 76 条 required 契约、48 条语义针脚和 14 条 banned 针脚统一为 138 条单源注册表，删除 summary 并严格拒绝未知字段；runtime docs stages 收紧为受控枚举，唯一 `all` 改为真实范围 `A0-A6`。
- **反例与验收**：14 条 banned needle 逐条注入均由对应契约 ID 阻断；required 删除、banned 文件缺失/回捡、未知 summary、未知 stage 与旧 `all` 均有负向回归。三批各包提交前全量 suite 均为 52/52，VERSION、pyproject、SKILL 版本锚与 CHANGELOG 在本收口提交统一升至 6.30.0。

本次为工具工程，无代币分析轮次或结论质量指标；contract manifest 76→138 条，casebook 32→35 条，运行时 suite 52→52 项。

## [6.29.0] - 2026-08-05 — 第二轮修复工程第 4 步：契约注册表与二级路由

- **R-02 canonical contract manifest**：把原 `docs_lint.py` 五组 85 个 `(文件, needle)` 对逐根分类为 76 个权威 needle 与 9 个报告 checklist 复述 needle；新增 `contract_manifest.json` 作为稳定契约 ID、权威路径、适用阶段和语义的单点注册表。lint 改为验证权威路径/needle 与全库 Markdown 契约引用，报告复述层收敛成摘要＋契约 ID，不再把复制长句固化为发布条件。
- **R-01 SKILL 二级路由**：深入阅读段只保留全流程、分段、净室复核、三链主册、A3/A5/A6、标签和环境入口；`runtime_docs_manifest.json` 升 v2，为每份现役文档登记入口归属和阶段，并由机器验证 `SKILL.md → 入口 → 分册` 两跳可达。SKILL.md 其余执行语义不变，尺寸保持在 8192B 内。
- **反例与验收**：新增 `test_contract_routes.py`，覆盖删除权威 needle、悬空契约 ID、权威路径不存在、manifest 幽灵条目和入口删引用导致孤儿五类负向输入；全量 SUITE 51→52 项，三个 pre-commit 守卫与全量 suite 均须通过。
- **验收加固（Fable，同日）**：攻击式验收发现第六类负向未关——真实 `contract_manifest.json` 的条目可被静默删除（lint 只查在表契约的权威在场，不守表自身完整性；与旧版硬编码等强度但更易被"顺手清理"）。`test_contract_routes.py` 增真实注册表基线：条目数 ≥76＋五组首根锚 ID 在场，删条目/删整组立红；红绿反证复现通过。另程序化对账：旧 lint 140 根 needle=76 入表＋9 报告复述取消（权威等价物逐根在场，其中低样本披露句由 `a5_report_seal.py` 代码闸强制）＋55 根其他检查组原样未动，无静默丢失。

本次为工具工程，无代币分析轮次或结论质量指标；权威 needle 76→76，复述强制 9→0，SKILL 深读平铺分册 32→二级入口 11。

## [6.28.0] - 2026-08-05 — 第二轮修复工程第 3 步：瘦身主体

- **R-04/R-05**：八份现役文档迁出案例史；casebook 全条目收敛为六字段，S-04 保留 12 个触发场景与回归指纹，升级返工史原样归档；methods B 类判例一次性迁入 C/E/S 续册（README 登记为只出不进的迁移特例，日常"不拆新册"纪律不变）。
- **P1-01/P1-02**：报告管道改为 A4 finalize 后 A5 一次物化 `charts/final/`；清理旧阶段名、旧 schema 名和幽灵脚本名，不改执行逻辑。
- **CHANGELOG/死物**：活跃窗口收至最近 10 版，旧版本块与撞号注记原样归档；删除获批的 pycache、根层重复 curation 文件和旧根层 manual_labels.csv，保留构建流输入与现役生成物。
- **验证**：casebook/docs/changelog/manual-sync/version 与全量 suite 均纳入发版验收。
- **验收返工（Fable，同日）**：修三处交付硬伤——README"不拆新册"与三续册的规则矛盾（改为登记迁移特例并只出不进）；E 续册 SIREN 判例内"详见本文件「层数封顶原理」"随迁移失效的指针（改指 methods 现役段名）；address-book 指向 casebook E-14 的错误判例指针（该判例不存在，删句留规则）。迁移原样性经程序化对照：7 文档 96 实质行迁出全部原样命中迁入地，判据数字集合 75/75 零丢失，旧归档 104 版本块零改动。

## [6.27.0] - 2026-08-05 — 第二轮修复工程第 2 步：Arbitrum 降为探索支持

- **支持矩阵纠偏**：正式深度管线移除 Arbitrum，现役路由与 EVM 手册明确其只保留探索档；
  采集、对账、identity snapshot receipt 与 G8 生成/校验能力不删除。降级原因固定为
  `labels-arbitrum.csv` 缺失，目标链设施剔除与合并拦截无法按正式口径闭合。
- **正式轨 fail-closed**：`audit_release_gate` 统一正式链集合与错误语义；A4 finalize 绑定
  state/G8 链并写入 seal，revision 链拒绝链漂移；A5 seal 绑定 A4 链；`build_html` 的
  `analysis-new` / `analysis-audit` 在正式资产校验前拒绝 Arbitrum。探索档仍可重放存量数据，
  但不得产 A4/A5 seal 或正式 analysis。
- **三向闭合守卫**：`test_chain_support_matrix.py` 同时核对 SKILL frontmatter、release gate
  `FORMAL_CHAINS`、`build_labels.py` 构建集合，并逐链要求目标 CSV 存在且含数据、
  `LabelResolver` 非 degraded。受控回归把 Arbitrum 同时塞回三处旧声明后，守卫以
  `labels-arbitrum.csv missing, empty, or header-only` 阻断；还原后通过。

本次为工具工程，无代币分析轮次或结论质量指标；正式支持错配 1→0，
新增正式链回归测试 1 项，
全量 SUITE 50→51 项。

## [6.26.0] - 2026-08-05 — 第二轮修复工程第 1 步：三项 P0 活故障收口

- **P0-04 手工标签层漂移**：`address-book.md` 增机器可读规范区，生成器改为确定性解析唯一人工真源；18 个差异逐址裁决为 16 个运行时标签＋2 个带独立理由的 record-only 豁免，9ZPsR 币安 Alpha 库存仓恢复命中。`check_manual_sync.py` 改为逐行生成物校验＋地址集合双向闭合，并作为第 50 项正式进入 `run_all.py`；resolver 注释同步实际生成链。
- **P0-02 A3 依赖序统一**：`analyze-workflow.md` 对齐 `split-run.md` §3.2，把 casebook、聚类裁决、临时实体、ET-2、EF-3、EF-1/2、freeze、G8、判级/ET-1、阵营演变和 A3 落盘按产物依赖重排；当前持仓分布初判保持在 EF-3A/B 后，代码 gate 输入契约不变。
- **P0-01 净室复核入口**：SKILL 路由增加自然语言复核既有报告入口；`analyze-workflow.md` 固化唯一权威分流，共用 A0–A2 采集对账骨架，A3 起走 `independent-audit-protocol.md`，A5 只用 `build_html --mode analysis-audit`。

本次为工具工程，无代币分析轮次或结论质量指标；缺陷验收为手工层漏同步 18→0、复核入口 0→1、全量 SUITE 49→50 项且全部通过。

## [6.25.0] - 2026-08-05 — references 长行保序拆分（瘦身第 6 步）

按 HEAD `9622798` 的唯一清单处理 17 份 references 文档中的 33 条目标长行：30 条在中文分号、句号、步骤箭头等自然语义边界插入换行与空格续行缩进，共 81 个断点；`references/report-template.md` L158、`references/address-book.md` L171、`references/data-pipeline-evm-channels.md` L229 为 Markdown 表格行，按结构约束不拆。每个修改文件均以去空白字符流和 HEAD 对比，结果零差异；判据、阈值、地址、路径、命令及 fail-closed 语义均未改变。

## [6.24.0] - 2026-08-05 — 零引用脚本归档与 Solana gas 双实现合并（瘦身第 5 步）

B 组两个全库零现役引用脚本退出执行目录，普通移动且不删除：`scripts/evm/trace_network.py` → `archive/scripts/trace_network.py`，`scripts/evm/fetch_fundedby.py` → `archive/scripts/fetch_fundedby.py`。两者除自身外只在历史归档中出现，无现役文档需要同步。

C 组 gas 双实现收敛为 `scripts/solana/gas_origin.py` 单入口，`scripts/solana/gas_fast.py` → `archive/scripts/gas_fast.py`。合并版保留 gas_origin 原有位置参数、`data/gas_origins.json` 累积格式、`first_txs` 与完整 `deltas`，并统一提供 gas_fast 的增强能力：`max_pages` 默认 2（沿用 gas_fast 实战校准值）、达到上限的超深地址标 `approx=true`、每笔继续输出 `sig/ts/my_sol_delta/funder`，目标 `my_sol_delta≈0` 时仍保留 fee payer funder 供先决字段闸裁决，RPC 429 显式退避；新增 `--full` 取消翻页上限，恢复 gas_origin 旧版一直翻到最老的全量行为，且会重查已有 `approx` 记录。实况核查发现 gas_origin 在本轮前已提前拥有默认 2 页、approx、my_sol_delta 与 deltas，本轮补齐剩余行为并正式移除双入口。

文档同步三处：`scripts/solana/README.md` 条目 10 改为合并版说明、删除 gas_fast 条目并将后续脚本序号 17–27 顺移为 16–26；`references/data-pipeline-solana-capture.md` 删除遗留 TODO，改为默认 2 页/approx/`--full` 已回填口径并保留 gas_fast 加固历史来源；`references/playbook-entity-cluster-methods.md` 的 my_sol_delta 判据仅把 `gas_fast/gas_origins` 权威脚本名替换为 `gas_origin/gas_origins`，其余判据、阈值与阻断语义不动。

审查后决定不动两项：①旧 Par 三件套 `fetch_hypersync_par.py`、`watchdog_dual.py`、`merge_parts.py` 原地保留，因为 `scripts/tests/test_review_medium_guards.py` 直接 import `fetch_hypersync_par.py` 的断点续传函数做守卫断言，移动会破坏现有防回退测试；②`scripts/solana/hypersync_recon.py` 原地保留，因为它是 HyperSync Solana 官方 GA 后的重验资产，且本就不在执行路由，移动没有上下文收益。

## [6.23.0] - 2026-08-05 — 深入阅读清单 manifest 化（瘦身第 4 步）

以 `scripts/tests/runtime_docs_manifest.json` 作为 SKILL.md 深入阅读清单的唯一事实源，落实 S-01 的仓库内解法：`references/*.md` 与 `references/labels/*.md` 每份文档必须先归入 `listed`（现役路由）或 `maintenance`（维护件），新增文档不再由旧反向漏列逻辑一律强迫进入 SKILL.md。

`docs_lint.py` 检查 4 改为 fail-closed manifest 守卫：JSON 解析、schema、scope、必需字段和数组结构任一异常即失败；磁盘实际集合与 `listed ∪ maintenance` 双向对账，未归类文档、幽灵条目及两类交集分别失败；`listed` 仍须按相对路径或文件名出现在 SKILL.md。`maintenance` 反向禁列，其中 `labels/MAINTENANCE.md` 无例外，`attic.md` 只允许保留一条含“禁读”的负向边界声明。全部失败信息携带 manifest 路径并提示“新增文档须先在 manifest 归类”。

当前闭合结果为磁盘 34 份 = listed 32 份 + maintenance 2 份，未归类/幽灵/交集均为 0。SKILL.md 的“标签/环境”入口移除 `labels/MAINTENANCE.md`，其余项目不动；`attic.md` 既有禁读声明原样保留。动机是让 SKILL.md 只路由现役文档，维护手册不再因 lint 反向检查被迫占用入口与上下文。判据、阈值与 fail-closed 分析语义零变更。

## [6.22.0] - 2026-08-05 — archive/ 考古区分层（瘦身第 3 步）

以仓库内 `archive/` 分区作为 S-02「拆两层包」的替代方案：历史资产仍随仓库保存、可维护和恢复，但不再参与执行路由；`archive/README.md` 明确执行会话与现役 references 文档禁读禁引用，资产恢复回现役必须留下 CHANGELOG 记录。判据、阈值与 fail-closed 语义零变更，评测题目内容零改动。

三组资产移动清单（旧路径 → 新路径）：
- `CHANGELOG-archive.md` → `archive/CHANGELOG-archive.md`
- `evals/` → `archive/evals/`
- `scripts/labels/sources/serial_conflicts_2026-07-22.json` → `archive/serial-conflicts/serial_conflicts_2026-07-22.json`
- `scripts/labels/sources/serial_conflicts_2026-07-22.md` → `archive/serial-conflicts/serial_conflicts_2026-07-22.md`
- `scripts/labels/sources/serial_conflicts_2026-07-25.json` → `archive/serial-conflicts/serial_conflicts_2026-07-25.json`
- `scripts/labels/sources/serial_conflicts_2026-07-25.md` → `archive/serial-conflicts/serial_conflicts_2026-07-25.md`
- `scripts/labels/sources/serial_conflicts_2026-07-26.json` → `archive/serial-conflicts/serial_conflicts_2026-07-26.json`
- `scripts/labels/sources/serial_conflicts_2026-07-26.md` → `archive/serial-conflicts/serial_conflicts_2026-07-26.md`
- `scripts/labels/sources/serial_conflicts_2026-07-28.json` → `archive/serial-conflicts/serial_conflicts_2026-07-28.json`
- `scripts/labels/sources/serial_conflicts_2026-07-28.md` → `archive/serial-conflicts/serial_conflicts_2026-07-28.md`
- `scripts/labels/sources/serial_conflicts_2026-07-29.json` → `archive/serial-conflicts/serial_conflicts_2026-07-29.json`
- `scripts/labels/sources/serial_conflicts_2026-07-29.md` → `archive/serial-conflicts/serial_conflicts_2026-07-29.md`

活引用同步：`CHANGELOG.md` 头部考古指针、`references/retrospective.md` 的 CHANGELOG 归档与题单维护路径、`references/casebook/README.md` 的候选题单路径、`scripts/tests/changelog_lint.py` 的 ARCHIVE 常量、`scripts/tests/docs_lint.py` 的全量评测扫描路径与归档豁免路径均指向新位置；`SKILL.md` 路由层新增考古区禁读边界。`scripts/labels/accumulate_offenders.py` 的活输出路径与 `references/labels/README.md` 规则保持不动，新冲突快照继续写入 `scripts/labels/sources/`。

`docs_lint.py` 新增考古区防回流守卫：现役 `SKILL.md` 与 `references/` 文档出现 `archive/` 路由引用即失败；仅维护记录、archive 自身、`references/attic.md`、`references/casebook/`、`references/retrospective.md` 豁免，另只允许 `SKILL.md` 的单行“执行会话禁读”边界声明，防止未来把考古资料重新拉入执行上下文。

6.21.0 遗留裁决闭环:methods 的 B 类 38 行判例,用户 2026-08-05 裁决放弃迁移 casebook、原地保留(S 册容量上限+必读到必读搬家净省有限)

## [6.21.0] - 2026-08-05 — 数据管线两册案例史外移与重复合并（瘦身第 2 步）

瘦身第 2 步（codex 按 Fable 验收通过的 111 条逐字引句盘点施工，Fable 逐项机器验收）：A4 复核强度配置与备择解释指引四处合一（analyze-workflow / evidence-wording / research-workflows 单一权威源化，40f88a0）；data-pipeline-evm-channels.md 与 data-pipeline-solana-capture.md 的 A 类战报子句与 C 类考古行外移至下方归档（两册净减 6,090 字节；现役参数/阈值/fail-closed/死亡名单/在役 fallback/守卫 needles 零变更；CH-53 Alpha 政策线与 CH-66 GMX 比例两条切出段含分析结论定性，按「CHANGELOG 禁记代币分析结论」红线停手留正文）。

批次 2——B 类 39 条方法级失败模式入 casebook（两册再净减 19,330 字节，正文原位换「权威短规则＋判例指针」43 处零断链）：S 册 4→7 条（S-04 扩为 12 场景覆盖盲区族＋新增 S-05 税币/毛流/曲线成本、S-06 时间边界、S-07 LP/TVL 归属）；E 册扩写 E-01/E-02/E-04/E-05/E-10/E-12；C 册扩写 C-01/C-04/C-06。三册 25.1KB→38.0KB（casebook_lint 26 条六字段全过）；既有条目判据语义逐行验证只增未改（50 处重写行 48 处前缀保留、2 处为插入新案源的假阳性）。执行过程 codex 进程三次中断，按「cancel+resume-last 蚂蚁搬家」分四段续跑完成。

批次 3——report-template.md 案例细节收敛（Fable 亲手盘点＋施工；codex 盘点任务两次进程中断后改自营）：规则全数保留，10 处行内案例细节压缩为短案源注（明细见下方归档），GMX 留存率设施污染案入 S-05（触发现象第④场景＋4.7%→34.8% 反转数字）；三账本分离宪法段、术语验收标准、比喻库、checklist 全部判定现役不动。

批次 4——playbook-entity-cluster-methods.md A 类拆句（Fable 亲手施工，按已验收 methods 盘点 57 条台账）：12 处行内案例数字/翻案过程压缩为短案源注（明细见下方归档），规则句、用户裁定记录（SPX6900 三次拍板等）与守卫锚点（① 候选发现档）逐字保留；B 类 38 行入册与否单列为用户裁决项（casebook 容量账见收尾汇报），本批不动。

#### report-template.md（批次 3 拆句归档）

- (原 L158) 图 1 混合重建图注纪律案源：GOAT 案末日封口 -12/+13pp 跳变仅解释了主实体的 2.8pp（外部复核抓出）；compose_evolution 读去重前发射窗致 LP 桶高估 0.83pp。
- (原 L162) KOGE overlay 实测：挂墙日账面 −75.9 万、同期池 +83.4 万、合计几乎不动。
- (原 L178) SIREN 流转图自解释验收：初版缺平行网四仓与卡片占比，用户对照正文仍"一头雾水"，返工 4 版才达标。
- (原 L187) SIREN 账目行加法自检：净出漏算四仓 15.2pp，被用户一个加法抓出。
- (原 L211) EGL1 宏口径边界：发射窗协同实体单笔买入 47.11% vs 日末峰值宏 40.21%，TL;DR 与正文两处误用。
- (原 L212) EGL1 序列末点纪律：散户残差手写 10.75% 实为 2026-01 中段值，末点真值 10.37%。
- (原 L261) SIREN 时区双标实锤：回测"UTC 凌晨 00:00~03:39 场内先崩"被用户对照 GMGN 图质疑"早上 9-10 点才崩"。
- (原 L271) GME 单一成员集合对账：verdict 摘曲线端数字把在场庄合计低估 1.21pct，增量更新旧账抽验才抓到。
- (原 L291) GMX 图例静默过滤：自定义名（"项目方·官方系""质押池（用户筹码）"等）传 8 阵营只画出命中标准名的 2 个（CEX托管/散户）。
- (原 L294) GMX 留存率设施污染明细：质押合约收 575 万枚、DEX 池收 173 万枚（判例正文入 S-05）。
- (原 L299) KOGE 阵营归属互斥：一个 2.867% 账户正文算进项目方注入、阵营表却归散户。

#### playbook-entity-cluster-methods.md（批次 4 拆句归档；规则句全数留正文并带短案源注）

- (原 L30) TROLL 中间判定污染细节：昨日中间判定的"Coinbase 托管分仓"被独立重做会话误当标签引用，恰是后来被翻案成小庄的四钱包（07-29）。
- (原 L56) SQD PoR 方法起源：Bybit PoR 2026-04-22 PDF 命中 3 址，直接把"疑似官方场外仓"实体翻案为 CEX 托管（07-20）。
- (原 L64) PUB 程序归属反转规模：13.57% 供应的"疑似 dev 系分仓"实为官方质押池（07-14）。
- (原 L95) BEGGAR 出纳名单战果：发现官方系隐性仓位 0.15%，利好日/风波日三次买入零卖出（07-17）。
- (原 L126) CASHCAT 两跳体检战报：132 址体检出 14 个合约，剔除后口径 21.9%→12.7%；96 址 53.97% 大集群清洗后拆为 40/15/5 三星座（07-13）。
- (原 L130) TROLL 截断地址双踩经过：主分析与一路复核 agent 均把 route JSON 截断串补全后空跑，靠空结果异常才暴露（07-29）。
- (原 L143) CASHCAT/NOXA 前缀补全事故：曾补出后 32 位全错地址险些进监控名单；LPT 手敲 TransferBond topic0 错一段扫出 0 笔（07-13/15/21）。
- (原 L152) TRASH 分仓贴线族明细：9 址协同族单址全部压 0.55% 以下，合并 3.69%（07-17）。
- (原 L173) meow 发射窗快闪客明细：头 60 秒项目方马甲 5.10%、金主同源闪电簇 5.06%（07-15）。
- (原 L177) SPX6900 同秒共现方法起源实测：53 仓 1378 对全扫唯二命中，双双被 first-funder/热钱包同源旁证坐实，一组合并后即发射窗真实第一大仓（07-25）。
- (原 L203) ASTEROID 半枢纽假簇数字：3367 址假簇按判据②剔边后 3367→136 正常长尾（07-18）。
- (原 L223) KOGE 同步动作分母检验数字：大庄取 800,000 枚、60 秒后项目方签名人取 300,000 枚，该三天全链 >50,000 枚转账仅此两笔，置换检验 p≈5×10⁻⁴。

### 战报与案史归档（自 data-pipeline-evm-channels.md / data-pipeline-solana-capture.md 外移）

#### data-pipeline-evm-channels.md

- (原 L17) HyperSync 官方客户端 v2 Rust 自动并发+Parquet 直写，实测 ~1 万条/s = 手写轮询 18 倍。
- (原 L20) SQD Portal 薄采集器实测 ~280 条/s。
- (原 L29) PING 案 uniqueId 双计 5485 负余额，促成集合级对账 fail-closed 防线。
- (原 L86) QUQ 完整版增量（07-22）：付费档实测 7 万块、2.3 万条仅 4s。
- (原 L107) HyperSync 官方客户端 v2 Starter 付费档 CAKE 实测 10,080 条/s。
- (原 L108) HyperSync v1：免费层 0.5s 间隔基本无 429（2026-07-18）；Starter 付费档 0.12s 间隔 429=0，单进程 552-792 条/s（ETH RTT~0.2s/BSC~0.6s）；免费层约 1000-1300 logs/2s、1568 万条约 5.2h，付费单进程 ETH 792 条/s、BSC 552 条/s（SIREN 07；哈基米 07-18；v3.11.2 07-21）。
- (原 L109) SQD Portal：CAKE 21,857 行/79s；BANANAS31(BSC) 四代表日 67,731 行六元组与 HyperSync 零差集全等（2026-07-22）。
- (原 L111) Alchemy getAssetTransfers 实测 ~46 万条/10 分钟。
- (原 L113) Etherscan V2 tokentx 7 万余行顺利拉完。
- (原 L114) envio HyperSync ETH 主网 0.25s 间隔仅 11 次 429、全部退避成功；139.9 万条 33 分钟单进程拉完，均速 ~700 条/s（ASTEROID，07-18）。
- (原 L153) 多会话共享 key 案史：SQD 案 83.2 万条 56 分钟、429×20 次全部自愈；LPT 案 eth+arbitrum 三进程并发时 arbitrum 429 密集，串行后恢复（SQD，07-20；LPT，07-21）。
- (原 L156) KOGE 案 82 个交易几十秒取得全部 81 次 LP 操作，对比 HyperSync 全链扫需几十小时（KOGE 第二轮追加取证，07-25）。
- (原 L164) Alchemy 平台级 429 曾整夜零进展（SIREN，07）。
- (原 L170) bloXroute 某次 3392 段中 92 段失败，后以 remaining 补扫闭合（OPN，07）。
- (原 L183) Multicall3 放量前未做小样本，因地址文件混入余额尾巴、动态偏移解码错、吞异常三连 bug，三轮 990/990 全失败（SIREN，07）。
- (原 L200) BANANAS31 转正后 Alpha Router 余额仅剩 ≈101 枚（07-22），作为 Router 随转正清空迁移的实测记录。
- (原 L203) dRPC 免费 key 未探测即让用户注册，实测基本不可用，白费一次注册（SIREN，07）。
- (原 L204) 2026-07 用户中国网络快照：drpc/alchemy/getblock/bitquery=200，app.envio.dev/nodereal=000，dune=403；bsc.hypersync.xyz 直连通（SIREN，07）。
- (原 L205) 数据量曾由几十万条误估至实际 2150 万条，造成耗时预估连环跳票（SIREN，07）。
- (原 L208) 通道切换未清观察哨曾空挂十几小时，并触发用户追问任务存活状态（SIREN，07）。
- (原 L210/L223) 旧 `scan_transfers.py` 毒段无限回队且 8 worker×curl 可零产出，后由 fill/现役 requests 扫描器取代（bibi，07-12；SIREN，07-19）。
- (原 L230) QUQ 案 `key_edges.csv` 7.3GB，采用逐行流式写出（07-22）。
- (原 L231) 2026-07-22 Alpha `mulPoint` 分布快照：645 币=1x、11 币=4x，后者均为 30 天内新 TGE Points Plus 加成（QUQ 投后，07-22）。
- (原 L234) QUQ 池腿法互验：LP 加撤剔除 2%；费反推与池腿实算吻合 103%；链上/CG≈83% 属正常带（QUQ 投后，07-22）。
- (原 L254) BscScan 省略号地址防错纪律源自 QUQ 07-22 案源记录。
- (原 L285) 图表叙事技巧：大户建仓时间线图上"创世期区域完全空白"= 没有任何创世钱包还留在前排的可视化证明（老庄已清仓的直观证法）。

#### data-pipeline-solana-capture.md

- (原 L15) IO 原始会话实录曾存档于 `~/Desktop/老公用/fable筹码分析/windows IO筹码分析会话记录/26a24d6c-*.jsonl`。
- (原 L19/L21) 验证清单在 2026-07-12 经 IO 实录考古大幅勾销；getProgramAccounts、组合过滤、Squads ID、Solscan 不可直读与情报源可达多数已回答，Token-2022 大扫描已实战收编（CLUDE 07-13）。
- (原 L34/L35) PUB 07-15 续拉后重放与链上快照逐地址零差异；CLUDE 07-13 的 CPMM 数学重建中段端点偏差实测达 35~49%。
- (原 L37) 公共 RPC gas 溯源 45 地址约 4 分钟。
- (原 L48) LAYOFF 锚点法工程规模：138 万签名、失败率 33% 属 pump AMM 正常、只用成功笔；约 550 个池余额锚点、约 65 个核心实体、约 400 个插值时间点。
- (原 L49) requests.Session 连接复用比 curl 逐发快约 3 倍；dRPC 免费层 Solana 返回 `chain is not available on freetier`，需付费。
- (原 L50) `oldest_sigs` 遇高频中转（数千签名）会卡死；LAYOFF 20 地址运行 15 分钟仍卡死，促成 `max_pages=2`。
- (原 L59) 快照对比法 1.8 天窗口全程数据成本 <1 小时。
- (原 L73) GOAT 案 `compose_evolution.py` 与 `GOAT分析/` 为 07-22 专属存档，实体分组、发射日、价格文件名按案硬编码。
- (原 L74) SQD 高密度期战报：大段 120 分钟只推进 3.4 链上小时；小段 29 秒拉完 1 万 slot，发射日 24h（16.5 万边）82 分钟；GOAT gap 追加产生 9,212 行重复，负余额账户 534 → dedup 后 1（GOAT，07-22）。
- (原 L75) GOAT 完整性复核 4 条 must_add 有 3 条半源于缺两扫描：历史离场大仓×2、离场庄扩容、事件日调拨（GOAT，07-22）。
- (原 L77) whale_deep 单案测速：USELESS（07-21）；5 进程时单笔 decode 拖到 0.6-1.2s（GOAT，07-22）。
- (原 L92) 销户账户覆盖首轮实证：PUB 全程边集 93/93、USELESS 定向段 7/7 全覆盖（2026-07-21）。
- (原 L98) v1/window_fetch 未开压缩导致错误判定 SQD 单流 1.5-4x 实时、全程重放不可行；13a–13b 启用 gzip/v2 后恢复可行。
- (原 L110) BONK 顶级密度战报：40 万 slot（约 28 链上小时）+22.3 万边，三跑约 11 分钟，稳态 639 slots/s≈255 倍实时；对照 window_fetch 82 分钟，约 7 倍。
- (原 L149) mainnet-beta batch 20 笔仅约 9 笔放行，首测 22/40 假失败；缓存 18/40 命中；Helius 于 2026-07-21 经 Google OAuth 注册，40 笔 5.3s=7.5 笔/s，45 地址溯源由旧 4 分钟约降至 35 秒。
- (原 L150) TROLL 实测（2026-07-29）：Helius keep-alive 版 8 线程约 7 笔/s 稳定，工作目录存档，待第二案复现后收编。
- (原 L181/L182) GOAT 拉签名实测 1,600 笔/秒，11.3 万笔池 ATA 仅 70 秒；45 万笔按日压缩为 8,302 个采样点（1.8%）。
- (原 L197) TROLL 长内盘规模：13 个月仅约 1,600 笔，跨 8 千万 slot（2026-07-29）。
- (原 L199/L203/L204) TROLL 双索引重建 decode 零失败、1,413 边；2 轮收敛，一笔 6 边归集 tx 解决 38.6pp 差异；创建窗独立抽验 14/14 一致（2026-07-29）。
- (原 L206) TROLL 衔接缝曾有 119 枚差，定位为缝内协议销毁（2026-07-29）。

## [6.20.1] - 2026-08-05 — 修 5 处阻断级文档漂移＋docs_lint 中文禁词与 Python docstring 扫描

全库瘦身与一致性审查（codex 2026-08-05 报告，Fable 逐条实证复核）第 1 步：先修误导执行的漂移，再做瘦身。codex 改文件、Fable 验收并 commit。

- **漂移修复五处**：①`playbook-evidence-wording.md` 报告写作顺序段与 6.7.0 A4→A5 硬闸冲突——"框架与纯事实章节可先写"改为"A4 finalize 封口前禁止创建任何报告正文/图/HTML，并行可先写的只有 findings.md/facts 层"（SIREN 案源保留，叙述转为支持硬闸）；②easy（6.17.0 已删）执行性残留三处清除——`data-pipeline-evm-recon.md` "峰值非必需场景（easy 初筛）仍可跳"整句删、`data-pipeline-solana-capture.md` 锚点复用步"easy/混合重建"改"混合重建"、`evals/cases/06` 考官答案"analyze/easy/update 三条 workflow"改"analyze workflow"；③`accumulate_offenders.py` module docstring 旧"每次分析交付后固定跑 --apply"（含 easy E5 残词）改 v6.4.0/v6.4.1 现行规则——仅用户明确下令复盘时随 retrospective.md 步骤 3 执行、分析交付后不自动回灌（split-run 机械段模型读旧 docstring 会误跑 --apply 污染全局惯犯库，本条是第 1 步里危害最直接的一处）；④批量预采集（6.18.0 已删）残留两处——`data-pipeline-evm.md` 分册索引"批量预采集/增量拉取"改"断点续拉"、`split-run.md` A1"预采集衔接"改"存量产物复用"；⑤`data-pipeline-evm-sources.md` 旧 `fetch_hypersync_par` CSV 分片"跨天无人值守标准件"条标【历史降级·新案禁用】——与 `merge_parts.py` deprecated 口径对齐，主线=HyperSync v2 Parquet+done.json manifest，watchdog"守护巡检+断点续传+事件词叫醒"方法学与历史战报数字原样保留。
- **docs_lint 守卫扩展**：REMOVED_FEATURE_TERMS 增中文禁词「批量预采集」「预采集衔接」「easy 初筛」「easy E5」（此前正则纯英文，中文语义残留全部漏检——本轮五处漂移长期全绿的根因）；新增 scripts 树递归全部 .py 的 module docstring 扫描（ast.get_docstring 提取，排除 scripts/tests/，语法解析失败容错跳过）；E0 正则未扩为 E[0-6]——`report-template.md:210` 合法实体宏 `{{e1.*}}` 在 re.I 下必误伤，按预案改精确禁词 easy E5 覆盖旧 docstring 场景。
- **验收**：9 文件 diff 逐条对任务书口径核过；反例攻击两路均被拦（活跃 md 塞「批量预采集」FAIL、py module docstring 塞「easy E5」FAIL）——攻击测试中 git checkout 还原误回滚未提交修复一次，已按原 diff 重打并终验；`run_all.py` 49 项全 PASS。成本：codex 单会话 12 分钟；质量：判据阈值变更 0、代码逻辑变更 0（仅 docstring 与文档）、误伤保留概念 0。
