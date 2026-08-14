# CHANGELOG — token-chip-analysis（活跃窗口）

版本规则（v3.0 起两维制，详见 references/retrospective.md「版本号约定」）：
- **skill 版本**：主=架构级重构；次=每次**分析复盘**迭代 +1；修=文档小修
- **labels 数据版本**：标签库扩容/重建记 `labels vX.Y` 前缀条目，不再占用 skill 次版本号
红线：条目只记工具性知识（数据源/坑/方法/脚本），禁止记录任何代币的分析结论。
每条迭代条目附成本指标（轮次数/Bash 调用数/交付用时）+ 质量指标（初稿关键结论数/复核判定分布/漏检实体数/传播级数字错误数，v3.0 起，见 retrospective 步骤 1）。
**写入前必跑 `python3 scripts/tests/changelog_lint.py`**（防撞号/倒排——两者都实际发生过）。
本文件只保留最近 ~10 版（整编时滚动）；更早的完整迭代史在 `archive/CHANGELOG-archive.md`，考古规则来源先 grep 该文件。

## 版本索引（活跃窗口，新在上；每版一行，详情见下方对应条目）

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
- **R10 台账（本轮未修，台账保留）**：存量 6 条（F-09/10/11/13、GPT-F-07 deploy-sync 弱闸、GPT-F-09 env_check 覆盖）＋加深 2 条（A5 图例集合绑定、F-12 改名降权）＋批 C 终验 3 条（C-R1/2/3）＋批 D 评估 2 条（A-2 approved_tolerance_bps 硬顶待用户裁决、A-4 EVM 链上观测件锚定设计留档）→ `maintenance/repair-20260813-sixlens/r10_ledger.md`。
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
