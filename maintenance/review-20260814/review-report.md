# 六视角全量 review 报告（2026-08-14）

- **基线**：main @ 7177beb（v6.40.0 终验收官后，工作区 clean）
- **指令模板**：references/maintenance-review-repair.md §一末尾标准 review 指令模板（六视角逐条＋实查文件清单＋强制归因＋最小反例/文件:行号）
- **执行者**：Claude Fable 5 主线亲读（非委派），边读边落盘台账 findings-draft.md 防上下文丢失
- **已知遗留对照**：maintenance/repair-20260813-sixlens/r10_ledger.md 十五条——撞上标"复核属实"不计新发现
- **收口判定**：P0 = 0；**P2 = 3、P3 = 9——新发现不全是边角料，按模板收口标准本轮 review 应转入修复轮**（工单建议见文末）

---

## 一、审查范围与方法（全量声明）

**全文精读（逐行）**：
- 顶层：SKILL.md / CHANGELOG.md（含 offset 补读）/ VERSION / pyproject.toml / requirements.lock / .gitignore；commands-staging 全部 3 件
- references/ 全部 36 份 md（analyze-workflow、split-run、independent-audit-protocol、scan-schemas、analysis-playbook、playbook 5 分册、casebook 7 件、data-pipeline evm 4 件＋solana 3 件＋robinhood 4 件、labels README＋MAINTENANCE、report-template、research-workflows、retrospective、monitoring-package、context-discipline、economic-control-accounting、lp-fee-accounting、address-book、environment、attic）
- scripts/lib 全部 19 件；scripts/report 全部 26 件；scripts/evm 全部 35 件；scripts/solana 全部 24 件；scripts/robinhood 全部 16 件；scripts/labels 全部 20 件；scripts/prices 2 件；scripts/bench 2 件；scripts/hooks 1 件；顶层 proclock.py / run_guarded.py
- scripts/tests 守卫本体 11 件全文（run_all / invariant_scan 1381 行 / docs_lint 443 行 / casebook_lint / changelog_lint / env_check / fixtures_lint / labels_manifest / formal_ready_test_harness / evm_channel_fixture / identity_gate_fixture）＋ 4 个 manifest JSON 结构校验

**89 个 test_\* 的全量三重覆盖（如实声明非逐行精读）**：①机器模式全量扫描——恒真断言 0、EXPECTED_FAIL 0、pytest.skip/xfail 0、mock 仅 2 处且均为健康用法（offline://mock 桩、注释）；②SUITE 对账——磁盘 87 个 test_\* vs run_all SUITE 87 项，零漏收零幽灵；③docstring 全量过目——全族自述为先红后绿/负向反例/契约测试。加 run_all 实跑行为级验证。

**跳过（含理由）**：__pycache__/.hypothesis/.DS_Store（机器生成物）；references/examples/lifecycle-flow-sample.png（二进制样图）；references/labels/\*.csv 数据体（结构经 labels_manifest 指纹验印＋validate_labels 14 项不变量机器校验，本轮 run_all 实跑通过）；maintenance/blind-reviews/archive 档案区逐字历史内容（审查其在位与隔离而非重审历史——r10_ledger 与 maintenance-review-repair.md 等运行相关件已全读，隔离性由 docs_lint 考古区越界守卫机器保证并经实跑验证）。

**横切实测**：run_all.py 全量实跑（95 PASS / 0 FAIL / exit 0，含 invariant_scan 五分母对账、docs_lint --all、labels_manifest 验印、deploy-sync、check_manual_sync）；rg 全库同族清单（7897 / CHIP_PROXY / publish_overwrite / RawBytes / CHIP_LEGACY_CAMP_DENOM / meta gaps / areas eng）；RV-07 kernel 最小反例实测复现；RV-06 第二部署实体核查；版本一致性四处对齐（6.40.0）。

---

## 二、六视角逐条结论

### ① 字段来源审计（自报即缺陷）
主检：全部 receipt producer（envelope/finalize 链）、collector 自报字段、gate 输入来源。
**结论**：receipt kernel 体系（build_envelope 身份绑定、reproduce_receipt nonce/inode 新鲜性、观测协议八步）大面积消灭了自报；发现 3 项残留——RV-16（transferFeeConfig 只读 newerTransferFee，降费过渡期漏放）、RV-14（cadence_rank 建仓窗口重言式自相关计入证据）、RV-10（(block,tx,log_index) 弱键使同 (tx,li) 双块行漏检）。R10-9（as_of_block 无真实对锚）复核属实不新计。

### ② 失败分支审计（warning 后装成功即缺陷）
主检：全部 producer 的 FAIL/ERROR 出口、探索件失败形态、下游对失败信号的消费。
**结论**：正式链路 fail-closed 质量高（ERROR side receipt、quarantine、gaps 不发正式产物的 window_fetch 范式）；发现 4 项——**RV-07（真 FAIL 收据被 kernel PASS 保护拒绝，五出口，实测复现）**、**RV-15（sol 采集器 gaps/eng 机器信号全库零消费）**、RV-13（gatekeeper 导入失败静默禁用与零命中同形）、RV-17（stake_decode 闭合验证两边同源，通道全死时 0==0 假"[闭合]"）。另 RV-04 的失败形态（死代理下四件探索工具无逃生门）。

### ③ 存量迁移（旧数据怎么迁、新产物谁生成）
主检：fetch_hypersync_v2 太古 done 迁移（F-07 真事务）、migrate_legacy_case、handoff 旧格式准入、decode 缓存 v2/v3 身份、anchor_sampler resume 身份校验、add_labels/additions 回放、roundtrip 收敛。
**结论**：迁移面闭合良好（refresh_manifests prepare/commit/rollback、normalize_cache_identity 凭据剥离重写、resume 全字段身份校验、additions 永不删除全量回放）。RV-07 的触发场景属本视角（存量案 QUQ 型 update 重采后 gate 翻 FAIL 必撞）；RV-06（0809 工程旧快照部署未清理）亦属存量清理欠账。

### ④ 同族调用面（rg 全库列同族入口）
主检：rg 实测清单——7897（代码级 10 文件）、publish_overwrite（FAIL 出口 5 处）、RawBytes（4 处全合法）、CHIP_LEGACY_CAMP_DENOM（provenance 白名单闭合）、(block,tx,li) 键族（3 处）。
**结论**：RV-04 同族最广（10 文件），RV-07 同族 5 出口，RV-10 同族 3 处；RV-08（RawBytes 可绕 PASS 降级保护）现役调用面全部合法，维持边界内侧观察；RV-09（http_get_many 无 proxy 形参与 RpcPool 不等深）观察级。

### ⑤ 双向一致性（文档/schema/CLI/测试互核）
主检：版本四处对齐、SUITE↔磁盘对账、manifest↔实态（invariant/contract/runtime_docs/labels 四本经实跑验证）、文档自述↔实现。
**结论**：机器对账面全绿（含 contract 146 条与 snapshot 对齐）；文档↔实现的发现——RV-02（report-template 批 C 版本误标 6.39.5，实为 6.40.0）、RV-01（CHANGELOG 头部自称"保留最近 ~10 版"实际活跃 26 版）、RV-03（data-pipeline-evm-channels L77-78 孤立围栏，且 docs_lint 围栏翻转逻辑会被其毒化跳过后续行检查）、RV-12（transfers_lib 头注去重键口径滞后于 2026-07-22 修复）、RV-06（同名 frontmatter 双部署）。

### ⑥ 闸可绕性（必经之路证明或绕过路径）
主检：G8-G11 链、发布闸 REQUIRED_BY_PROFILE、freeze 四重前置、kernel 原语、A7 惯犯硬闸、--empty-proof 废止、AUTO_GATES。
**结论**：正式发布链闸密度与不可绕性为全库最强面（build_html 有 WARN 不写文件、series 重转换逐点比对、fixture 走真实链路而非 mock）；绕过路径类发现——RV-15（HS 引擎"禁止正式采集"仅停留在文档声明与 meta 留痕，重放侧零检查）、RV-06（路由二义可整体绕过 6.40.0 的全部闸修复——选中旧部署即旧闸）、RV-08（RawBytes 载荷绕 PASS 降级保护，属"必须显式造假"边界内侧但未在 kernel 文档声明）。invariant_scan 静态守卫的可绕性已由其自身诚实声明（accepted-downgrade，R10 已知）。

---

## 三、发现明细（P2/P3 正式清单）

### P2-1（RV-04）代理环境漂移：skill 全库写死已弃用的 clash 7897，Surge 6152 适配为零
- **视角**：②＋⑤｜**证据**：rg 全库——代码级 10 文件：scripts/evm/accounting_gate.py（对 `.g.alchemy.com` URL **自动注入** `http://127.0.0.1:7897`）、scripts/solana/fetch_sqd_transfers_v2.py:101（HS_CLASH_PROXY）、audit_closed_accounts.py:41（DEF_PROXY 默认值）、whale_deep.py:23、probe_escrows.py:20、probe_window_moves.py:65（以上可覆盖/可关）、**stake_decode.py:23 / fast_probe_tops.py:16 / gas_origin.py:19 / trace_wallet.py:15（写死无覆盖参数，当前环境完全不可用）**。`CHIP_PROXY` 全库零命中——用户记忆中的探测链不存在于 skill。
- **后果**：Solana 探索/溯源工具族（gas 溯源、单钱包流水、质押账本、top 画像、销户审计）在 08-12 环境迁移后系统性瘫痪；accounting_gate 的 Alchemy 通道不显式传 --proxy 必挂（fail-closed 方向，无假 PASS）。
- **归因**：历史漏检（环境 08-12 变更引发的存量失配；变更后首轮全量 review 即本轮，此前无人扫描适配面）。
- **修复方向**：统一代理解析器进 scripts/lib（CHIP_PROXY 环境变量 > 显式 --proxy > 直连，探测式回退），10 文件收编；docstring 示例同步（supply_truth_gate/fetch_alchemy/decode_txs_v2/price_check）。

### P2-2（RV-07）合法的真 FAIL 收据无法落盘：kernel PASS 降级保护无 FAIL 重跑出口（已实测复现）
- **视角**：②＋③｜**证据**：实测——旧 PASS 收据在场时 `publish_overwrite` 抛 "existing PASS artifact cannot be downgraded"。同族五出口：scripts/lib/supply_truth_gate.py:544、scripts/evm/verify_recon.py:165、scripts/lib/time_spotcheck.py:301+402、scripts/solana/window_fetch.py:233（FAIL 分支）。
- **失败场景**：存量案增量重采后 gate 判真 FAIL（QUQ 型 update 必撞）→ producer 报"receipt 写入失败" exit 1（通道故障语义而非 FAIL 语义）→ 重跑每次撞同一保护，真 FAIL 永远落不了盘、无人能从收据面看到质量翻转。A-1 旧收据作废归档只挂在政策拒绝出口（supply_truth_gate policy_reject），真 FAIL 出口无归档步骤。
- **归因**：修复中新引入（6.36.0 kernel `_reject_pass_downgrade` 普遍化时未评估"合法 FAIL 重跑"路径）。
- **修复方向**：五出口在真 FAIL 落盘前复用 invalidate_stale_receipt 语义（旧 PASS 改名 `.superseded-UTC` 归档再写 FAIL），保留对"无归档直接降级"的拒绝。

### P2-3（RV-06）同名旧版第二部署存活：~/.claude/skills/tca-supplytruth-fix 路由二义
- **视角**：⑤＋⑥｜**证据**：实体目录 110MB 非 symlink；VERSION=6.39.0（落后五个版本）；frontmatter `name: token-chip-analysis` 与主 skill **同名同 description**（会话 skill 列表两条同文案的根源）。
- **后果**：skill 路由按 name/description 匹配时二义；选中旧部署＝用 0809 快照跑分析，整体绕过 6.39.1→6.40.0 的全部修复（provenance 敏感性闸、distribution 语义重验、六视角四批、批 C/D 收口）。
- **归因**：修复中新引入（repair-20260809-supplytruth 工程部署临时副本收官后未清理）。
- **修复方向**：确认该副本无未回灌的独有改动后删除（③档操作，删除前备份、须用户批准）；今后临时部署副本须改 frontmatter name 并在工程收口清单加"清理部署"项。

### P3-1（RV-15）Solana 采集器 gaps/HS-引擎机器信号在重放侧断链
- **视角**：②＋⑥｜**证据**：fetch_sqd_transfers_v2 缺口时 exit 2＋meta.gaps 留痕＋stdout"gaps 清零前不得进重放"；HS 段 meta.areas[].eng="hs" 留痕＋"禁止正式采集"声明。replay_edges.load_edges（scripts/solana/replay_edges.py:92-110）只验 schema/mint/collection_upper_slot，不查 gaps、不查 eng——六个子命令照常重放。rg 确认两信号全库零消费。evolution（正式编译链输入件）无 gaps 检查且 launch_ts 默认取首见铸造边——缺发射段时狙击窗整体错判。
- **最小反例**：meta.json 手工加 `"gaps":[[100,200,"scan-fail"]]` → replay_edges evolution 照常产出 camp_share_series.json＋合法 sidecar。
- **部分兜底**：reconcile 快照全对账兜终态（不兜中段序列）；同 skill 的 window_fetch 已实现正确收口范式（gaps 非空只留 .partial＋FAIL receipt）。
- **归因**：老问题修复不全（v6.36 receipt 化收口覆盖 window_fetch 未同步 v2 缓存链——同族未关到同一深度）。
- **修复方向**：load_edges 增加 gaps 非空硬拒＋eng=hs 段硬拒（探索豁免须显式 flag）；launch_ts 缺铸造边时要求显式 --launch-ts。

### P3-2（RV-13）cluster.py 行为守门员导入失败静默禁用，与零命中同形
- **视角**：②｜**证据**：scripts/evm/cluster.py:30-34 `except Exception: funnel_scan=None`→守门员整体禁用，clusters.json gatekeeper_blocked=[] 与"跑了零命中"不可分辨，无 stderr 警告、无 meta 降级标记。对照同文件 labels_resolver 的 v4 修复（"没命中≠没加载"显式 degraded 警告＋labels_meta 落盘），gatekeeper（v4.2 后加入）未享同款防线。
- **最小反例**：改坏 gatekeeper.py 语法→跑 cluster.py→输出无任何警告、假聚类头号防线静默缺席。
- **归因**：老问题修复不全（v4 降级显式化只覆盖 labels 层）。

### P3-3（RV-14）cadence_rank.py 建仓窗口检测是死代码，必填参数功能为零
- **视角**：①＋⑤｜**证据**：scripts/evm/cadence_rank.py:131-132 `if fb[0]==o[0] and … and c[0][0][:10]<=args.formation_cutoff: pass`——语句体 pass。后果一：纯建仓窗口 o≡fb、ρ=+1、p=0 的重言式自相关计入 hits 并进传递闭包，与头注纪律"单批次顺序不构成证据"矛盾。后果二：--formation-cutoff 被 parser.error 强制必填并做格式校验，但除 identity 记录外唯一逻辑用途在死分支。
- **最小反例**：构造 ≥6 址单一批量首买窗口（cutoff 前）→产出 ρ=+1.000 hit 并合并为"实体"。
- **归因**：历史漏检（EGL1 二稿 2026-07-26 引入，疑为未写完的排除逻辑）。

### P3-4（RV-16）accounting_gate_sol transferFeeConfig 只读 newerTransferFee，降费过渡期漏放
- **视角**：①｜**证据**：scripts/solana/accounting_gate_sol.py:71-81 只取 newerTransferFee 判级。Token-2022 费率切换按 epoch 延迟生效：降费过渡期（older=269bps 仍在收、newer=0 未生效）gate 按 0bps 判 WARN 放行→重放到账额≠事件额静默算错，恰是本闸要防的事故类。反向调费不受影响。窗口 ≤2 epoch（约 4-5 天）。
- **最小反例**：state={olderTransferFee:{transferFeeBasisPoints:269}, newerTransferFee:{transferFeeBasisPoints:0}, transferFeeConfigAuthority:null} → 返回 WARN 而非 BLOCK。
- **归因**：历史漏检（v3.19 引入时 BERN 实测样本恰为"现役 newer"场景，未覆盖过渡态）。修复=取 max(older.bps, newer.bps) 判级。

### P3-5（RV-17）stake_decode 闭合验证两边同源，通道全死时恒"[闭合]"
- **视角**：②｜**证据**：scripts/solana/stake_decode.py——账本净额与池链上余额同走一个 rpc()（且 L23 代理写死 7897 无覆盖参数）。通道全死时 ledger 空 tot=0、getTokenAccountBalance 失败 onchain=0 → 差=0≤2 → 打印"**[闭合]**"。头注纪律"对不上=签名史没拉全…勿进分析"依赖此判定，通道级故障让它恒过。当前环境默认必触发。
- **最小反例**：断网跑（holders_accounts.json 在场供 ATA）→"0 个用户…差=0 [闭合]"。
- **归因**：历史漏检（PUB 案 07-14 收编时通道活着）。修复=onchain 查询失败时硬拒判闭合＋并入 RV-04 代理收编。

### P3-6（RV-02）report-template 批 C 版本溯源误标
- **视角**：⑤｜**证据**：references/report-template.md:202 "（F-04，v6.39.5 批 C）"；CHANGELOG L43-49 确认批 C（F-04/F-05）落地于 6.40.0，6.39.5 是 distribution 语义重验修复。按版本考古时错档。
- **归因**：修复中新引入（6.40.0 工程写模板时误标）。

### P3-7（RV-01）CHANGELOG 头部自述失真
- **视角**：⑤｜**证据**：头部声明"本文件只保留最近 ~10 版"，实际活跃窗口 6.20.1–6.40.0 共 26 个版本条目（超限 2.6 倍）。滚动归档未执行或声明失真。
- **归因**：历史漏检。修复=执行一次滚动归档或把声明改为实际策略。

### P3-8（RV-03）data-pipeline-evm-channels 孤立围栏毒化 docs_lint 检查状态
- **视角**：⑤｜**证据**：references/data-pipeline-evm-channels.md:77-78 连续两个 ``` 孤立围栏；docs_lint L307-310 的围栏翻转逻辑（`in_code = not in_code`）被孤立围栏反转后，后续正文被当代码块跳过断链等检查——文档缺陷同时削弱守卫覆盖。
- **归因**：历史漏检。修复=删孤立围栏＋docs_lint 增加"文件末围栏状态必须闭合"检查。

### P3-9（RV-10）(block,tx,log_index) 弱去重键三处：同 (tx,li) 双块行漏检
- **视角**：①＋④｜**证据**：链上事件真唯一键是 (tx,log_index)（一笔 tx 只属一个块）。replay_stream.py:743-746 按三元组查重、transfers_lib.py:112-113 dedup_key 同构——同 (tx,li) 不同 block 的损坏行（reorg 双记录/采集器错块号）被当两个键双双保留并报"0 重复"；replay_duck L165-174 对同键不同内容有硬退（不等深）。普通行重复不破坏 su==mint_total 恒等，gate 可仍 PASS。触发面被 anchor 确认深度协议压低。merge_sources 跨源检查反而用了正确的 (tx,li) 键。
- **归因**：历史漏检（2026-07-25 引入时即如此）。

### 撤销记录（防误报）
- **RV-05 撤销**：build_html.py:477-478 正式模式自动把 --md 透传给发布闸 report 参数，analyze-workflow 声明的 fail-closed 成立。
- **RV-11 撤销**：CHIP_LEGACY_CAMP_DENOM 旧分母是被显式建模的合法口径——camp_series_provenance DENOMINATORS 白名单（L66/109-111）＋closure_mode_for 按口径单式严判（L287-299）＋state_from_facts F-C4 绑定路径按 sidecar denominator 选闭合单式，防线闭合。

---

## 四、已知遗留撞上记录（复核属实，不计新发现）

R10-1（figures_from_facts fig1 无白名单＋plot_camp_evolution 静默跳非标键，figures_from_facts.py/standard_charts.py:174 读码坐实）、R10-4（fetch_hypersync_v2 resolve_token 位置参数优先级最高）、R10-12（waiver approved_tolerance_bps 无上限，supply_truth_gate 在码）、R10-13（EVM onchain 观测件局限，independent-audit-protocol 明示）、R10-14/15（handoff_manifest 在码）。R10-2（adversarial_review_runner 可空壳）在码属实。invariant_scan 静态守卫可绕性=其 L650-667 自身诚实声明的 accepted-downgrade（用户裁决 2026-08-09 在案）。

## 五、观察堆（P4/P5，不进修复清单，供顺手清理）

探索/辅助层：multicall_balances /1e18 浮点落盘且 decimals 假设未声明；scan_bloxroute_seg 失败段仅打印仍 return 0；fetch_etherscan 错误响应当空批 break（部分数据像完整数据，FORMAL 不可入兜底）；fetch_alchemy rawContract 缺失时 value*1e18 浮点回退（供给闭合兜底）；cluster_prep_duck 重叠去重无 payload 冲突检测（duck 有，不等深）；cluster/analyze_holdings total_supply_m 静默默认 1000；analyze_holdings 对账 MISMATCH 不阻断（头注声明人工纪律）；whale_deep RPC 全挂形态偏 fail-open（"未找到 ATA"）；fetch_sqd_transfers_v2 merge-fail 打印"完成：0 条边"exit 2 措辞扭曲；scan_sharded leaf_fail 无收口（对账 diff 人工兜）；fetch_pool_sigs RPC 失败 break 仅 stderr 留痕。
残留物：pull_lp_events.py:89 `tok_is_0 = … or True` 占位死码且头注声称"自动判"与实现不符；pull_block_ts_anchors 写死块范围 range(1670000,12366461)；build_evolution L177 注释残留 LAYOFF 标的名；hypersync_recon 常量写死 BONK（验收工具已声明用法）；fast_probe_tops L69 `json.dumps(...)[:0]` 死码；invariant_scan L1255 空 continue；accumulate_offenders/build_goldset DEFAULT_ROOT 写死本机用户路径（多设备同步下他机默认扫空）；transfers_lib 头注去重键口径滞后（RV-12）；transfers_lib merge_sources payload 含 block_hash 使老 CSV×v2 混源必 exit 3（fail-closed 错杀）；peaks_daily 候选 SUM 无 VARINT 回退（duck 有）；config.example.json alchemy 默认 bnb-mainnet 而用户 app 未开通（attestation 兜底）；net.py http_get_many 无 proxy 形参与 RpcPool 不等深（RV-09）；RawBytes 可绕 PASS 降级保护未在 kernel 文档声明（RV-08，现役 4 处调用全合法）。

## 六、正面确认（防线在位，实跑验证）

run_all 95 PASS / 0 FAIL / exit 0（93 项含四 manifest 对账、deploy-sync、考古区隔离、契约 146 条闭合）；SUITE↔磁盘 87/87 零漏收；版本 6.40.0 四处一致；89 个测试文件零恒真断言/零 skip/零 EXPECTED_FAIL，fixture 走真实生产链路（make_receipt/replay_pass1 真跑）而非 mock。全库质量高地：labels 族（A7 硬闸/三闸事务真回滚/roundtrip 收敛/盲化整行剥离）、receipt kernel＋观测协议生产件（scan_token_accounts/window_fetch/anchor_sampler/fetch_pool_swaps）、发布闸链（WARN 不写文件/series 重转换逐点比对/--empty-proof 自报废止）、resume_guard 身份绑定族、invariant_scan（双向对账＋injection 自测＋边界诚实声明）。

## 七、修复工单建议（按 maintenance-review-repair.md §三模板开单）

1. **工单 A（P2-1，RV-04）**：代理解析统一收编——lib 层探测器（CHIP_PROXY > --proxy > 直连），10 文件迁移＋4 处 docstring 同步；验收=断代理环境下四件无逃生门工具可用性恢复＋RV-17 连锁场景消失。
2. **工单 B（P2-2，RV-07）**：五出口真 FAIL 落盘前归档旧 PASS（复用 invalidate_stale_receipt 语义）；验收=本报告实测反例转绿（FAIL 可落盘且旧 PASS 有 .superseded 归档），PASS 防覆盖保护保持红。
3. **工单 C（P2-3，RV-06）**：确认 tca-supplytruth-fix 无独有未回灌改动后删除（③档，须用户批准＋备份）；流程面在 maintenance-review-repair.md 收口清单加"临时部署清理"项。
4. **工单 D（P3-1，RV-15）**：load_edges 硬拒 gaps 非空/eng=hs＋launch_ts 显式化。
5. **工单 E（P3 批量）**：RV-13/14/16/17/02/01/03/10 逐项小修（每项已给最小反例，先红后绿）。

——以上工单未经用户批准不动手；本报告只审不修。
