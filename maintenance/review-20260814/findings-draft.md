# 六视角全量 review 工作台账（2026-08-14，进行中）

- 执行者：Claude Fable 5（主线亲读，非委派）
- 基线：main @ 7177beb（v6.40.0 终验收官后，工作区 clean）
- 指令模板：references/maintenance-review-repair.md §一末尾标准模板（六视角逐条＋实查文件清单＋强制归因＋最小反例/文件:行号）
- 已知遗留对照：maintenance/repair-20260813-sixlens/r10_ledger.md 十五条——撞上记"已知遗留（R10-N）"，不计新发现
- 状态：🏁 已收口（2026-08-14）。本文件为过程台账；正式交付=同目录 review-report.md（P2×3＋P3×9＋撤销×2＋观察堆＋工单建议）

## 阅读进度（实查文件清单，随读随记）

- [x] SKILL.md（87 行全读）
- [x] maintenance/repair-20260813-sixlens/r10_ledger.md（全读）
- [x] references/maintenance-review-repair.md（全读，模板出处）
- [x] 顶层：CHANGELOG.md（380 行全读）/ VERSION / pyproject.toml / requirements.lock / .gitignore / .hypothesis/.gitignore
- [x] commands-staging/ 全部 3 件
- [x] references/ 全部 36 份 md 全读（analyze-workflow / split-run / independent-audit-protocol / scan-schemas / analysis-playbook / context-discipline / economic-control-accounting / playbook 5 分册 / report-template / research-workflows / retrospective / monitoring-package / address-book / environment / attic / lp-fee-accounting / casebook 7 件 / data-pipeline evm 4 件 + solana 3 件 + robinhood 4 件 / labels README + MAINTENANCE）
- 未逐读：references/examples/lifecycle-flow-sample.png（二进制样图，非文本）；references/labels/*.csv 数据体（结构与 manifest 对账在横切步做）

## 发现累积（编号 RV-NN，随读随记，归因三选一待终审定稿）

- RV-01【⑤一致性，候选 P3】CHANGELOG.md 头部自称"本文件只保留最近 ~10 版"，实际活跃窗口含 6.20.1–6.40.0 共 26 个版本条目，超限 2.6 倍。整编滚动没执行或声明失真。
- RV-02【⑤一致性，候选 P3】report-template.md「阵营序列两道闸（F-04，v6.39.5 批 C）」版本标注疑错：CHANGELOG 中批 C（F-04/F-05）属 6.40.0 工程，6.39.5 是 distribution 语义重验修复。待复核后定稿。
- RV-03【⑤一致性，候选 P3】data-pipeline-evm-channels.md L77-78 连续两个 ``` 围栏（json 块关闭后多一个孤立围栏），markdown 渲染会把后续正文吞进代码块。docs_lint 无围栏平衡检查。
- RV-04【⑤一致性，候选，级别待验证】代理配置漂移：用户环境 08-12 已迁 Surge 6152（clash 7897 弃用），references 多处写死"clash 代理 / 127.0.0.1:7897"（solana-capture §9 decode_txs --proxy 示例、labels/MAINTENANCE.md 重下载命令 P=…7897、evm-sources 多处"走 clash 代理"）。若脚本已有 CHIP_PROXY>6152>7897 探测链则文档滞后为 P3；若脚本写死 7897 则为 P2。→ 代码审查时验证。
- RV-05【⑥闸可绕性/⑤一致性，验证项】analyze-workflow 称"new-analysis 发布闸必须带 --report，缺 --report 时 A5 seal 在场即 fail-closed 拒"，而 report-template.md 的标准 build_html 示例命令未见 --report 参数传递路径。→ 审 build_html.py / audit_release_gate.py 时验证示例命令是否会撞闸或 --md 自动透传。
- RV-06【⑤一致性，验证项】~/.claude/skills/ 下疑存在与本 skill 同 description 的第二部署 tca-supplytruth-fix（会话 skill 列表两条同文案），若为 repair-20260809-supplytruth 工程遗留部署，触发路由竞争。→ 横切步 ls 验证。

## scripts/evm 全 35 件审毕小结（2026-08-14）

已全读：verify_recon / channels_preflight / accounting_gate / fetch_hypersync_v2 / replay_duck / replay_stream / replay_pass1 / replay_pass2 / transfers_lib / peaks_daily / prep_cluster_inputs / fetch_hypersync / fetch_hypersync_logs / fetch_alchemy / cluster / cluster_prep_duck / analyze_holdings / cadence_fingerprint / cadence_rank / cluster_sensitivity / lp_positions / pierce_stake / fetch_pool_swaps / scan_transfers / multicall_balances / scan_bloxroute_seg / fetch_etherscan / fetch_bigquery / fetch_sqd_evm / csv_collector_receipt / make_channel_receipt / staged_capture.sh / fetch_gmgn.sh / config.example.json（__pycache__ 机器生成物跳过）。

正面确认：fetch_pool_swaps=receipt kernel 全链路正面样例（envelope→quarantine→publish_txn→ERROR side receipt）；scan_transfers/fetch_etherscan/fetch_bigquery 均带 FORMAL_CHANNEL_ELIGIBLE=False 显式声明；csv_collector_receipt SUPPORTED 白名单+fresh_output 强制；make_channel_receipt --empty-proof 自报废止硬拒；fetch_gmgn.sh 失败标 .stale 防旧数据冒充。

P4 观察（探索/辅助层，不进正式清单，报告观察段汇总）：multicall_balances L73 硬编码 /1e18 浮点落盘且 decimals 假设未声明（pierce_stake 同场景有声明）；scan_bloxroute_seg 失败段仅打印 fails 列表仍 return 0（pierce_stake 同场景 exit 1，不等深）；fetch_etherscan call() 非 rate-limit 错误返回错误字符串→tokentx 当空批 break=部分数据像完整数据（FORMAL 不可入兜底）；config.example.json alchemy url 默认 bnb-mainnet 而用户 app 未启用 BNB_MAINNET（attestation fail-loud 兜住）。

## scripts/solana 全 24 件审毕小结（2026-08-14）

已全读：README / fetch_sqd_transfers_v2 / replay_edges / accounting_gate_sol / scan_token_accounts / decode_txs_v2 / audit_closed_accounts / anchor_sampler / window_fetch / build_evolution / whale_deep / stake_decode / probe_escrows / probe_window_moves / hypersync_recon / squads_members / scan_sharded / fast_probe_tops / gas_origin / trace_wallet / curve_cost / fetch_pool_sigs / snapshot_diff / decode_txs（__pycache__ 跳过）。

正面确认：scan_token_accounts/window_fetch/anchor_sampler/fetch_pool_swaps 同为 receipt kernel+观测协议生产化正面样例；window_fetch gaps 收口是正确范式（反衬 RV-15）；decode_txs_v2 缓存身份绑定+失败不缓存+finalize BLOCK receipt；audit_closed_accounts GPT-F-06 四态收口；squads_members/snapshot_diff/curve_cost/decode_txs 干净。

RV-04 代码级同族终计（10 例）：evm/accounting_gate（自动注入）、sol/fetch_sqd_transfers_v2（HS_CLASH_PROXY）、audit_closed_accounts（默认可关）、whale_deep（--proxy none 可关）、probe_escrows+probe_window_moves（默认可覆盖）、**stake_decode/fast_probe_tops/gas_origin/trace_wallet（写死无覆盖参数，当前环境完全不可用）**。探索层 Solana 工具族系统性瘫痪坐实 P2。
P4 观察补充：hypersync_recon 常量写死 BONK（验收工具已声明改常量用法）；build_evolution L177 注释残留 LAYOFF 标的名（代码已参数化）；fast_probe_tops L69 `json.dumps(...)[:0]` 死代码；scan_sharded leaf_fail 记账但 main 不收口（对账 diff 人工兜）；fetch_pool_sigs RPC 失败 break 部分落盘仅 stderr 留痕。

## scripts/robinhood 全 16 件审毕小结（2026-08-14）

已全读：amounts / build_price / cost_engine / gas_trace / gas_trace_bs / merge_hs_rpc / pull_block_ts_anchors / pull_lp_events / pull_ohlcv / pull_swaps / pull_swaps_v4 / pull_transfers / pull_transfers_rpc / pull_weth_pool / resume_guard / config.example.json（__pycache__ 跳过）。

正面确认：resume_guard 身份绑定+重叠回拉体系被三个采集器共用；pull_swaps_v4 解码失败 bad>0 不写完成 receipt 硬退；merge_hs_rpc 全程 fail-closed（gzip 完整性/dup key/写后重读验证）；gas_trace_bs 桥别名自检+retry queue exit 2；build_price GT 交叉验证无重叠即硬退。

P4/P5 观察：pull_lp_events.py L89 `tok_is_0 = token < pool or True` 占位死代码（`or True` 恒真且变量从未被使用），头注 L9-10 声称"amount 腿按地址大小自动判"与实现不符——实际靠末尾 stdout 提醒人工校准（⑤形态，探索件有人工兜底）；pull_block_ts_anchors.py 写死块范围 range(1670000,12366461,20000)（历史案残留，复用新案不适配且无参数）；gas_trace.py/pull_weth_pool.py archive_height 缺失时 `nb >= (ah or 0)` 恒真→静默只拉一页（HyperSync 正常必带该键，触发面极窄）。

## scripts/labels+prices+bench+hooks+顶层 全 27 件审毕小结（2026-08-14）

已全读：labels 20 件（labels_resolver / gatekeeper / risk_flags / build_labels / validate_labels / label_lookup / check_manual_sync / gen_manual_from_addressbook / add_labels / roundtrip_check / accumulate_offenders / benchmark_labels / build_goldset / fingerprint_check / goplus_check / probe_codetype / pull_verified_contracts / sourcify_check / dune_fetch_results + sources 目录结构）；prices 2 件（llama_price / price_check）；bench 2 件（golden_baseline / scan_script_forks）；hooks 1 件（guard_file_ops）；顶层 2 件（proclock / run_guarded）。

正面确认：labels 族是全库质量最高的目录之一（v4 多轮 codex 复核痕迹全在）——degraded 判定"只看 CSV 不被地址簿掩盖"、A7 惯犯×设施冲突硬闸、add_labels 三闸事务真回滚、roundtrip 收敛+日期倒退方向检查、benchmark 弱门禁显式声明、goldset ARBITRATED 仲裁层、盲化整行剥离防 RISK 段泄露。price_check ALL_SKIP exit 3 不许当 PASS。golden_baseline 缺=不等 fail-closed。proclock flock 设计推理（rename 换 inode 双持锁坑）。guard_file_ops 载荷异常放行=守卫不阻塞（声明式设计）。

P4 观察：accumulate_offenders/build_goldset `DEFAULT_ROOT=~/Desktop/老公用/fable筹码分析` 写死本机用户路径（可被位置参数覆盖；GitHub 多设备同步下其他机器默认参数扫空目录）。price_check 文档示例 --proxy 7897（显式参数，RV-04 文档面）。

## scripts/tests 104 项审毕小结（2026-08-14）

审查方法（如实声明）：守卫本体 11 件全文精读（run_all / invariant_scan 1381 行 / docs_lint 443 行 / casebook_lint / changelog_lint / env_check / fixtures_lint / labels_manifest / formal_ready_test_harness / evm_channel_fixture / identity_gate_fixture）+ 4 个 manifest JSON 结构校验（contract 146 条与 snapshot 146 对齐、invariant 五分母、runtime_docs 39+3）+ 89 个 test_* 全量三重覆盖：①机器模式扫描（恒真断言 0、EXPECTED_FAIL 0、pytest.skip/xfail 0、mock 仅 2 处且为健康用法）②SUITE 对账（磁盘 87 个 test_* vs run_all SUITE 87 项，零漏收零幽灵）③docstring 全量过目（全族自述为先红后绿/负向反例/契约测试）。run_all 实跑见横切段。

正面确认：invariant_scan 双向对账+五分母 floor+injection 自测+8 专项守卫，静态守卫边界诚实声明（"accepted-downgrade boundary, user decision 2026-08-09"=R10 已知）；docs_lint 11 项检查含考古区越界守卫与已删功能回捡（含 py docstring 层）；fixture 库走真实生产链路（make_receipt/replay_pass1 真跑）而非 mock 装死；formal_ready_test_harness 用 context manager 精确还原而非布尔旁路。

P5 观察：invariant_scan L1252-1256 循环尾 `continue` 空操作死码。docs_lint L307-310 围栏翻转逻辑对孤立 ``` 敏感（RV-03 的放大器：孤立围栏会把后续正文当代码块跳过断链检查——RV-03 佐证加强）。

## 横切验证结果（2026-08-14 实测定稿）

- **RV-04 定稿 P2**：rg 全库确认——代码级 7897 注入/默认值 10 文件（accounting_gate 自动注入 + solana 9 件，其中 stake_decode/fast_probe_tops/gas_origin/trace_wallet 四件无覆盖参数）；supply_truth_gate/fetch_alchemy/decode_txs_v2/price_check 仅 docstring 示例（代码干净）。**`CHIP_PROXY` 全库零命中**——记忆中"CHIP_PROXY>6152>7897>直连"探测链不存在于 skill（6152 命中全是 CSV 地址串巧合），skill 完全未适配 08-12 Surge 迁移。
- **RV-07 定稿 P2（实测复现）**：kernel 拒绝信息 "existing PASS artifact cannot be downgraded"。同族五出口：supply_truth_gate.py:544 / verify_recon.py:165 / time_spotcheck.py:301+402 / window_fetch.py:233（FAIL 分支）。真 FAIL 表现为收据写入失败 exit 1（通道故障语义），重跑每次撞同一保护；A-1 归档通道只挂政策拒绝出口。修复方向=真 FAIL 落盘前复用 invalidate_stale_receipt 归档旧 PASS。归因定稿：修复中新引入（6.36.0 kernel PASS 保护普遍化未给合法 FAIL 重跑留出口）。
- **RV-06 定稿 P2**：~/.claude/skills/tca-supplytruth-fix 为实体目录（110MB 非 symlink），VERSION=6.39.0（落后主 skill 五个版本），frontmatter `name: token-chip-analysis` 与主 skill **同名**——skill 路由二义，选中即用 0809 旧快照跑分析（缺 6.39.1→6.40.0 全部修复）。归因：修复中新引入（0809 supplytruth 工程部署临时副本后未清理）。
- **RV-02 定稿 P3**：CHANGELOG L43-49 确认批 C（F-04/F-05）落地于 6.40.0；6.39.5 是 distribution 语义重验修复。report-template.md L202 "（F-04，v6.39.5 批 C）"版本溯源标注错误。归因：修复中新引入（6.40.0 工程写模板时误标）。
- **RV-11 撤销**：camp_series_provenance DENOMINATORS 白名单（L66/109-111）+closure_mode_for 按口径单式严判（L287-299，legacy 归 total 族闭合）+state_from_facts F-C4 绑定路径按 sidecar denominator 选单式。legacy 是被显式建模的合法口径非绕闸，防线闭合。
- **RV-15 定稿 P3（偏 P2）**：rg 确认 meta["gaps"] 与 areas[].eng 全库零消费（除产者自身）——机器信号完全断链。部分兜底：reconcile 快照全对账兜终态（不兜中段序列与 launch_ts 错位）；升格条件=若正式编译链对 sol-rows 不强制 reconcile gate_pass 在场则升 P2。
- **RV-05 已撤销**（build_html L477-478 自动透传）。
- 版本一致性：VERSION=6.40.0=pyproject=CHANGELOG 首条 ✓。
- 四 manifest 对账+deploy-sync SHA+考古区隔离：由 run_all 实跑内的 invariant_scan/docs_lint/labels_manifest/test_commands_deploy_sync 机器验证（结果见下）。
- Task#7 档案区过目：maintenance 5 工程目录（4 repair+本 review）、blind-reviews/r9、archive 11 项——结构在位；执行路由隔离由 docs_lint 考古区越界守卫保障（run_all 验证）。

## ~~待横切验证清单~~（已全部执行，见上）

- run_all.py 全套守护测试实跑
- 版本一致性：VERSION / SKILL.md 注释 / CHANGELOG 头 / pyproject（初查一致=6.40.0）
- runtime_docs_manifest / contract_manifest / invariant_manifest 与磁盘实态对账
- R10-1 声称"旧 state 直喂 fig1 重绘路径仍开着"复核
- labels manifest 与 CSV 实态对账
- RV-04 代理探测链代码验证；RV-05 --report 传递验证；RV-06 第二部署验证
- deploy-sync：commands-staging 与 ~/.claude/commands 实态 SHA 对比（R10-5 弱闸旁证复验）
- ~~sol 采集→重放衔接两问~~ 已验证→升格 RV-15（见发现区）；剩横切项：rg 全库谁消费 meta["gaps"] / areas[].eng（确认是否有别处兜底再定稿级别）
- fetch_sqd_transfers_v2 收尾 merge-fail 分支：print "完成：0 条转账边"+exit 2（缺口语义）而非失败语义，措辞扭曲但退出码非 0（P4 观察）

- RV-07【②失败分支/③存量迁移，P2 候选】supply_truth_gate 真 FAIL 无法落盘：旧收据为 PASS 时，重跑得出 FAIL 判定 → `publish_overwrite` 被 kernel `_reject_pass_downgrade` 拒绝 → "receipt 写入失败" exit 1（通道故障语义），重跑无解（每次撞同一保护）。A-1 归档通道只挂在政策拒绝出口（policy_reject），真 FAIL 出口没有归档步骤。场景：存量案增量重采后 gate 翻 FAIL（QUQ 型 update 必撞）。同族：全部用 publish_overwrite 的 producer 待 rg。归因预判：修复中新引入（6.36.0 kernel PASS 保护普遍化未评估合法 FAIL 重跑）。
- RV-08【⑥可绕性，P3 候选】receipt_kernel RawBytes 载荷绕过 PASS 降级保护：_reject_pass_downgrade 只对 Mapping 载荷生效，RawBytes 可 publish_overwrite 覆盖既有 PASS 收据。属"必须显式造假"接受边界内侧但未声明。调用面 rg 待查。
- RV-09【④同族，P4 观察】net.py http_get_many 无 proxy 形参（RpcPool 有），trust_env=False 下环境代理也不生效，两 API 不等深。调用面影响待查。
- RV-04 升级【②失败分支+⑤一致性，P2 候选】代理漂移代码级确证：accounting_gate.py main() 对 `.g.alchemy.com` URL 自动注入 `http://127.0.0.1:7897`（clash，用户 08-12 已弃用迁 Surge 6152）。当前环境下不显式传 --proxy 跑 Alchemy 通道必然 RPC 全挂 exit 1。fail-closed 方向安全（不产假 PASS）但通道死。同族第 2 例：fetch_sqd_transfers_v2.py L101 `HS_CLASH_PROXY="http://127.0.0.1:7897"`（HyperSync 第二引擎直连断自动切 clash——当前环境切过去也死，段回落 SQD，fail-closed 但实验通道彻底失效）。同族第 3 例：audit_closed_accounts.py L41 `DEF_PROXY="http://127.0.0.1:7897"` 为 --proxy 默认值——当前环境默认跑必全 RPC 失败→INVALID_SAMPLE exit 1（GPT-F-06 修复后不产假 CLEAN，但现役审计件默认不可用）。同族第 4-7 例（solana 探查件重灾区）：whale_deep.py L23 PROXY 默认 7897（--proxy none 可关，失败形态偏 fail-open="未找到 ATA"）；stake_decode.py L23 写死且**无覆盖参数**（连锁出 RV-17 假闭合）；probe_escrows.py L20 / probe_window_moves.py L65 默认 7897 可覆盖。另 decode_txs_v2.py docstring 用法示例含 7897（显式参数，代码干净）。同族 rg "7897" 全库待做；CHIP_PROXY 探测链是否存在于 skill 内待验证。
- RV-07 同族扩充：verify_recon.py FAIL 收据同走 publish_overwrite（旧 PASS 在场时 FAIL 写不进），time_spotcheck.py 同。同族 rg publish_overwrite 待做。
- 复核属实（已知遗留，不新计）：R10-1 figures_from_facts fig1 直读 state 无白名单+plot_camp_evolution 静默跳非标键（S-10 同源）——读码坐实与台账描述一致。
- RV-10【①来源/②失败分支，P3 候选】replay_stream.py 去重验证键弱于 replay_duck 冲突检测：stream L743-746 按 `(block_number, transaction_hash, log_index)` 三元组查重，而链上事件真唯一键是 `(tx, log_index)`（一笔 tx 只属一个块）。同 (tx,li) 不同 block 的损坏行（reorg 双记录/采集器写错块号）在 stream 下被当作两个不同键→报"0 重复"假阴性→两行都进聚合；replay_duck L165-174 对同 (tag,tx,li) 不同内容硬退。普通行重复不破坏 su==mint_total 恒等（+v/−v 对称），gate 可仍 PASS。触发面被 anchor 确认深度协议压低但防线强度确实不等深。归因预判：历史漏检（2026-07-25 引入时即如此）。
- RV-11【⑥可绕性，验证项】replay_duck pass2 `CHIP_LEGACY_CAMP_DENOM=1` 环境变量可切回 mint_total 旧分母（3.36 修复前口径，IQ 案散户虚高 44pp 的源头）。sidecar 会记 denominator=mint_total_legacy——发布闸/camp_series_provenance 是否对 denominator 值白名单校验（拒 legacy 进正式案）待横切验证。rg CHIP_LEGACY_CAMP_DENOM + 读 sidecar 校验分支。
- 观察（不计/待定）：replay_duck build_events L96-98 通道缺文件仅 [warn] 跳过（fail-open 形态），但 preflight_channels 在 main L550 先行——若 preflight 已保证文件存在则此为死防线；待复核 channels_preflight 存在性检查（replay_pass1 L45-47 同形态）。replay_stream 自述"等价性回归待补"（未与 duck 做黄金对表）+stats.engine 字段下游不区分——已声明局限，观察级。--no-verify-dedup 显式开关可关去重验证但 stats 留痕（dedup_verified_segments=None），显式造假边界内侧，P4。
- RV-10 同族扩充：transfers_lib.py `dedup_key()` L112-113 同为 `(block, tx, log_index)`，dedup_iter 冲突检测对"同 (tx,li) 不同 block"的行视为两个不同键双双保留（merge_sources 的跨源全局检查 L265-275 反而用了正确的 (tx,li) 键）。同族三处：replay_stream 验证键 / transfers_lib.dedup_key / （duck 的 (tag,tx,li) 因 tag=段与块绑定，暴露面同类但段内仍以 (tx,li) 实务去重）。
- RV-12【⑤一致性，P4 候选】transfers_lib.py 头注 L13-15 仍写"去重键（防链重组，v3.11.2 起标准）: (block_hash or block, tx, log_index)"，实现已按 2026-07-22 修复改为 (block,tx,li)+payload 冲突检测（dedup_iter docstring 自述修复动机=旧键含 hash 导致混源双计）。头注滞后于实现，照抄头注重写下游会复活双计坑。归因预判：老问题修复不全（修复改了函数 docstring 没改文件头注）。
- RV-15【②失败分支+⑥可绕性，P2-P3 候选】Solana 采集器 gaps/eng 机器信号在重放侧断链。采集侧（fetch_sqd_transfers_v2）：缺口时 exit 2+meta.gaps 留痕+stdout"gaps 清零前不得进重放"；HyperSync 段（完备性验收不通过通道）meta.areas[].eng="hs" 留痕+stdout"禁止正式采集"。重放侧（replay_edges.load_edges L92-110）：只验 schema/mint/collection_upper_slot 三项，**不查 meta.gaps 非空，不查 eng=hs**——六个子命令对带缺口/带 HS 段的缓存照常重放。下游兜底不全：reconcile 有快照全对账兜（对称缺口理论可漏但概率低）；**evolution（正式编译链输入件）无任何 gaps 检查**，且 launch_ts 默认取首见铸造边——缺发射段时发射时刻错位→首30分钟狙击窗整体错判。sidecar 的 reconcile_receipt 是"在场即绑"（L343-344），不在场静默不绑（下游闸是否强制其在场待横切）。最小反例：meta.json 手工加 gaps:[[100,200,"scan-fail"]] → replay_edges evolution 照常产出 camp_share_series.json+合法 sidecar。归因预判：历史漏检（重放件 07-14 收编早于采集器 gaps 语义 07-21 引入，衔接闸缺位）→读 window_fetch.py 后改判候选为**老问题修复不全**：window_fetch（同为 SQD 采集件）在 receipt/v2 化时已实现正确收口——gaps 非空只留 .partial、正式 out 不落盘、receipt FAIL exit 2；fetch_sqd_transfers_v2 的缓存链（v6.36 已做 dataset_scope attestation 改造）未同步这一收口，重放侧也无补偿检查。同族未关到同一深度（第十层元规则形态）。
- RV-14【①来源/⑤一致性，P3 候选】cadence_rank.py L131-132 建仓窗口检测 `if fb[0]==o[0] and … and c[0][0][:10]<=args.formation_cutoff: pass`——语句体是 pass（死代码，注释称"仍参与比对"）。后果一：纯建仓窗口（窗口内成员全部首买）的 o≡fb，ρ=+1、p=0，重言式自相关照样计入 hits 并进传递闭包——与本文件头注纪律"单批次顺序不构成证据"直接矛盾。后果二：--formation-cutoff 被 parser.error 强制必填并做格式校验，但除 identity 记录外唯一逻辑用途就在这个死分支=必填参数功能为零。最小反例：构造 ≥6 址单一批量首买窗口（cutoff 前），跑出 ρ=+1.000 的 hit 并合并成"实体"。归因预判：历史漏检（EGL1 二稿 2026-07-26 引入时疑为未写完的排除逻辑）。
- RV-17【②失败分支，P3 候选】stake_decode.py 闭合验证两边同源导致假"[闭合]"：账本净额（来自 RPC 签名史+decode）与池链上余额（来自 RPC getTokenAccountBalance）走同一 rpc() 通道。通道全死时（如默认死代理 7897，L23 且**无 --proxy 覆盖参数**）：all_sigs 全失败→ledger 空→tot=0；getTokenAccountBalance 失败 res=None→onchain 累计 0→差=0-0≤2→打印"**[闭合]**"。头注纪律"对不上=签名史没拉全…勿进分析"依赖此判定，而通道级故障恰好让它恒过。0 用户的输出人工可疑，但"[闭合]"是误导性通过信号。当前环境（7897 弃用）默认必触发。最小反例：断网跑 stake_decode（holders_accounts.json 在场提供 ATA）→输出"0 个用户…差=0 [闭合]"。归因预判：历史漏检（PUB 案 07-14 收编时通道活着，无人试全挂形态）。
- RV-16【①来源，P3 候选（触发窗口窄）】accounting_gate_sol.py classify_ext L71-81 对 transferFeeConfig 只读 `newerTransferFee`，不看 `olderTransferFee`。Token-2022 费率切换按 epoch 延迟生效：降费过渡期（older=269bps 仍在收费、newer=0bps 未到生效 epoch）时 gate 按 bps=0 判 WARN 放行——正式采集/重放照跑，到账额≠事件额静默算错，恰是本闸要防的事故类型。反向调费（0→高）不受影响（newer 高值正确 BLOCK）。缓解：窗口 ≤2 epoch（约 4-5 天）且需项目方恰在分析期降费。保守正解=取 max(older.bps, newer.bps) 判级。最小反例：构造 state={olderTransferFee:{transferFeeBasisPoints:269}, newerTransferFee:{transferFeeBasisPoints:0}, transferFeeConfigAuthority:null} → 返回 WARN 而非 BLOCK。归因预判：历史漏检（v3.19 2026-07-22 引入，BERN 实测样本恰为"现役 newer"场景未覆盖过渡态）。
- RV-13【②失败分支，P3 候选】cluster.py L30-34 gatekeeper 导入失败静默置 None→守门员整体禁用，clusters.json 里 gatekeeper_blocked=[] 与"跑了但零命中"完全同形（无 stderr 警告、无 meta 降级标记）。对照同文件 labels_resolver 的 v4 修复（"没命中≠没加载"显式 degraded 警告+labels_meta 落盘），gatekeeper（v4.2 加入）未享受同款防线。假聚类头号防线可静默缺席。归因预判：老问题修复不全（v4 降级显式化只覆盖 labels 不覆盖后加入的 gatekeeper）。最小反例：改坏 gatekeeper.py 语法→跑 cluster.py→输出无任何警告、gatekeeper_blocked=[]。
- 观察（探索层，P4 级）：cluster.py/analyze_holdings.py `CFG.get("total_supply_m", 1000)` 静默默认 10 亿枚——config 漏填时 R1/准入阈值错 3 个量级不报错（探索层+对账纪律兜底）。analyze_holdings.py 对账段打印 MISMATCH! 但不 exit（头注声明为人工纪律，正式链路另有机器闸）。cluster_prep_duck.py v2 重叠段去重 ANY_VALUE 无 payload 冲突检测（replay_duck 同位置有 fail-closed 硬退，不等深）。analyze_holdings eth_csv 路径无排序依赖上游升序。
- 观察补充：transfers_lib.merge_sources canonical_payload 含 block_hash 字段——老 CSV（无 hash=""）与 v2 parquet（有 hash）混源重叠区必 payload 不等→exit 3 错杀合法混源场景（fail-closed 方向，可用性缺陷非安全缺陷，P4）。peaks_daily.py L119-120 cand 门槛 SUM(v) HUGEINT 无 VARINT 回退（replay_duck 同位置有 try/except 回退），溢出 fail-loud 安全但不等深，P4。prep_cluster_inputs.py L29-30 坏 gmgn json `except Exception: continue` 静默跳过——其头注警告的"R2 gas 同源静默失效"可由自身此分支引入（探索层辅助件，P4）。replay_pass1/pass2 与 duck 的已声明语义差异（段外行/空 ts/同键 keep-last）均在 duck docstring 声明为"旧引擎行为"，黄金基准角色不改，不计。
