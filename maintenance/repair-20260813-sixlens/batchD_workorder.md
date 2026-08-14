# 修复批 D 工单（收口批：F-06＋F-07＋GPT-F-06＋台账清理＋版本收口＋验收件）

施工基线 main@97b2c65（v6.39.5，批 A/B/C 已收口）。定案输入＝plan.md「批 D」节＋batchD_ledger.md 全文＋batchA_fixround2_workorder.md §六。本工单五栏制；末行为完成标记。

---

## ① 不变量（每道修复各自守什么）

| 项 | 不变量 |
|---|---|
| F-07 | 多 manifest 迁移**全有或全无**：任何失败路径上，磁盘要么全部新版、要么全部字节回滚原样；回滚失败必须留下可辨识的恢复件并以独立退出码（1）区别于干净拒绝（2） |
| F-06 | 真实三策略翻转的唯一放行通道＝`flip-adjudications/v1` 裁决收据；收据经**翻转指纹**绑定到该锚点三策略明细——底层数据一变收据自动失效；披露不再是无人执行的承诺（A5 对报告实文核对三策略 top 与份额）；freeze 只认绑定收据不信 ledger 自报 |
| GPT-F-06 | 审计退出码对齐脚本自身契约：查不出来≠没有漏（五类样本无效一律 exit 1）；closed=0 是弱结论不是查询失败，也不冒充零漏强证明 |
| A-1 | 政策拒绝后案内不得残留上一轮现役收据（作废归档；归档失败＝义务副作用未完成，升格 exit 1） |
| A-3/B-6 | envelope inputs 在正式消费线上**解析必落案根内**（相对基于案根、绝对也强制 relative_to）；生产侧记相对路径使案可搬家 |
| A-5 | EVM balance/supply/supply_truth 三查绑定的 replay_stats 必须同一份实物（sha 全等）——三查核同一本账 |
| B-1 | Solana `holder_outputs.accounts/owners` 在消费侧（bundle_path 在场）有文件级三验实物锚，与 EVM 等深 |
| B-4/B-5 | 分布扫描器自带绑定实物 sha/size 自验（不引用别人的三验作自己的证据）；案根遏制分支有定向红线 |
| B-7 | 三账 `balance_source` 与四查核过的 owner 快照**时点一致＋逐址数值等值**（三账内部自洽不再够） |
| B-3 | `distribution-scan/v2`：`denominators.mint_total_raw` 键名与语义一致（铸造总量含已销毁） |

## ② 同族 rg 清单与查证结论

- `rg "acknowledged_flips|acknowledge_flip|acknowledge-flip"` 全库：生产面仅 entity_source_trace.py＋handoff_manifest.py（两处全改）；**测试面零引用**（6.39.4 引入时无测试覆盖——F-06 归因"修复中新引入"的旁证）；文档面零引用（本批在 scan-schemas §4a 新建权威定义）。
- `rg "atomic_write_json" scripts/evm/fetch_hypersync_v2.py`：三调用点——generate 主流程单文件（原子性够）、ensure_outdir_identity 单文件（够）、refresh_manifests 循环多文件（F-07 战场，已改真事务）。同族多文件写手 `receipt_kernel.publish_txn` 已是 rollback 事务（对齐其 committed 语义：提交完成后收尾失败不回滚、保留备份报错）。
- `rg "getMultipleAccounts|wall_dl" scripts/solana/audit_closed_accounts.py`：批失败 1 处、墙钟检查 4 处（sigs 拉取/主抽样/blocks 抽样/深挖）——全部接 wall_flag/gma_batch_failed，无漏点。
- `rg "inputs\.get\(|\"balances\"" scripts/report scripts/lib`（A-3 消费面）：shared_release_receipt 的 replay_stats/tolerance_waiver/observation_bundle 三处相对路径解析已补；holder_distribution_scan._bound_replay_stats 原生兼容相对路径；audit_release_gate._recon_owner_snapshot 新增点自带绝对/相对双兼容。
- `rg "balance_source"`：生产语义仅 audit_release_gate.check_three_ledgers 一处消费（B-7 已钉）；夹具四处（build_case＋align helper 统一）。
- `rg "distribution-scan/v1"` 修后清零（代码/契约/文档全升 v2；test_distribution_gate 保留一处 **v1 作负例字面量**——升版后旧 schema 必拒的既有反例，注释已标明）。
- 记录不修类照抄批 A 结论：accounting `--samples`、verify_recon `--top-n`、anchor_sampler 覆盖窗（证据强度参数非判定翻转参数）。

## ③ 三件套测试（原反例先红后绿＋同族变体＋失败分支）

全部落 `scripts/tests/test_repair_batch_d.py`（已入 run_all SUITE 显式清单），反例脚本另落 `counterexamples/`（flip_receipt_chain.py / refresh_txn_rollback.py / closed_audit_failopen.py，均独立可重放 rc=0）。

**F-07**：
- 原反例（审查原样）：两 legacy done、第二次提交注入 OSError——修前 run_1=v3/run_2=legacy 混合态；修后断言**两个 done.json 字节回滚原样**＋无 tmp/bak/recover 残留＋exit 2。注入带命中标志（os.replace 调用序第 4 次＝第二文件提交，stderr 含注入串——先证到达提交分支，不以非零退出码凑数）。
- 失败分支：回滚也失败（第 5 次调用注入）→ `.recover` 恢复件保留＋exit 1（RefreshRollbackError 独立通道）。
- CLI OSError：只读目录令 ensure_outdir_identity 的写 identity 抛 PermissionError → exit 2 无裸 traceback（root 用户跳过，批 A 先例）。
- 绿例：太古双 run 正常迁移全升 v3＋identity 建立。

**GPT-F-06**（mock RPC 失败路径，进 run_all；采集工具本体不进——需网络）：
①gma 批失败→exit 1；②checked=0 且 closed>0→exit 1；③closed=0→exit 0 NO_CLOSED_SAMPLED 且 invalid_reasons 空（边界显式定案的绿例）；④漏边→exit 2 LEAK_FOUND；⑤墙钟截断→exit 1 且 wall_truncated 单列。undetermined 过半与"深挖全 fetch_failed"由②的 mock 一并覆盖（invalid_reasons 多条并列如实记）。LEAK_FOUND 优先于 INVALID_SAMPLE（漏边是实锤证据，样本无效只是不能证明——报告里两类信息都在场）。

**F-06**（真跑 trace 的双来源翻转最小案：E1 收 CEX 100→收 DEX 100→转出 100，FIFO/LIFO/pro_rata top 三分歧）：
- 原反例翻案：`--acknowledge-flip E1:current:aaaaaaaaaa`（任意 10 字符旧格式）→ exit 2（修前 exit 0＋publishable=true）。
- 无收据→exit 2 阻断保留；合法收据（指纹＋披露由 `ledger_real_flips` 同函数机械生成）→exit 0＋收据引用入 `input_binding.algorithm_params.flip_adjudications`。
- **指纹自动失效**：改边表一笔金额、旧收据原样→exit 2 报指纹失配（"底层数据一变必须重裁"的机器面）。
- 预防性豁免（收据行指向不存在翻转的锚点）→exit 2。
- 收据加载器字段级反例 ×7（schema/裁决主体/UTC 时间/证据空/理由短/指纹非 hex/缺披露位置）＋名册改动失效（ref 三验先拦、名册内容比对兜底，两文案都算命中——报错换岗如实记录）。
- freeze 端：recompute 绑定收据独立重验绿例；收据换包（sha 失配）拒。
- A5：报告实文含三策略 top 标识与份额→DISCLOSED；缺披露值→拒（原反例：只验 claim 在场挡不住无关文本）；freeze 后换 ledger→sha 绑定拒；freeze 后删 ledger→旁路封死。
- 既有 handoff 67 项全绿（两处断言 needle 随文案更新："机器从明细重算"→"三策略主导终点翻转"，语义不变——翻转仍拒、尘埃仍豁免）。

**台账项**：
- A-1：PASS 收据在场→政策拒绝→exit 2＋`supply_truth.json.superseded-<UTC>` 归档＋案内无现役收据；归档件即原收据（不销毁）；误伤查＝非本 gate 文件占位 --out 不动。
- A-3：生产侧断言收据 inputs 记相对路径（`replay_stats.json` 无案根前缀）；**搬家绿例**＝整案复制后 validate_reconciliation_check 照过（存量绝对路径复制案被拒已由批 A N-1 用例覆盖，本批报错换岗如实更新断言：更靠前的 `validate_receipt(case_root)` 先响 "input escapes case root"，旧闸兜底在后，处置指引一致）。
- A-5：supply 收据换绑另一本自洽账（sha 合法登记）→ "不同源" 拒；绿例＝build_case 全链（夹具补成真实形态：verify_recon 型收据本就绑 replay_stats 四件套——夹具失真修复，断言零放宽）。
- B-4：绑定实物换包（内容改、收据登记未更）→"换包或陈旧"拒；绿例＝三验一致放行。
- B-5：案根外绑定实物→"不在当前案根内" 定向红线（此前该分支变异存活，现有独立用例钉死）。
- B-7：①balance_source 拿 999 块高快照（快照自身 sha 三验全对）→"冻结时点不一致"拒；②三账整套改 99（内部完全自洽闭合）→"与四查 owner 快照不等值"拒——三账自洽不再是通行证。
- B-1＋B-2：**Solana new-analysis 发布闸 run() 完整端到端夹具**（build_solana_case：真形态 observation bundle 全字段自洽＋anchor sampler 双收据＋solana supply_truth＋真跑分布扫描/figure2 check/A5 seal/adversarial runner）——run(profile="new-analysis") 零 error 绿例；owners 同值换仓（总和不变分配变）→bundle 三验拒＋发布闸拒；owners 实物删除→缺件拒。

**变异法自检（删掉即红，每次清 __pycache__）**：
1. 中和 F-07 回滚段（except 改直接 raise）→ t_f07 字节回滚断言红；
2. 中和 verify_flip_receipt_against_ledger 的指纹比对行 → "数据一变旧收据失效"用例红；
3. 中和 A5 报告实文比对（`ident not in report_text` 恒 False）→ "缺披露值被拒"用例红；
4. 中和 B-7 数值比对段 → B-7 原反例②红；
5. 中和 B-1 holder_outputs 三验段 → B-1 换包用例红。
（实测记录见 §五验证；5/5 全部"删掉即红"后恢复原样重跑全绿。）

## ④ 新建代码六视角①②自审

- **字段来源**：flip 收据的指纹/份额全部由消费侧从 ledger `policy_details` **独立重排重算**（`ledger_real_flips` 不信 producer 行序自报——伪造者重排行序装"无翻转"会被 recompute 既有独立重排检查抓，装"有翻转"会被指纹/披露比对抓，两向闭合）；收据自报的 share_pct/terminal 必须与重算相等（防收据写假数）；A-1 只作废 schema 前缀命中的本 gate 收据（防误伤占位文件）；B-7 数值源＝四查收据绑定实物（案根遏制后加载），非三账自报。
- **失败分支**：F-07 prepare 失败＝零正式件被动（清 tmp 原样抛）；commit 失败＝回滚＋字节验证；回滚失败＝.recover＋exit 1；**commit 全部完成后的收尾（fsync/清备份）失败不回滚**（对齐 receipt_kernel.publish_txn committed 语义：新件已就位，回滚反而制造第二次状态翻转，保留备份报错）。GPT-F-06 五类无效逐条独立 reason 入报告。F-06 收据不合法统一 exit 2（文件不存在也是调用错误，不落 exit 1——load 前置到 source_binding 之前）。
- **残余边界（如实声明）**：①F-06 的 handoff 重放装配层"旧式 acknowledged_flips 拒收"分支，在"有真实翻转"场景永远被 recompute 先拦（recompute 在装配之前跑且 fail 即 return）——该分支只在"无翻转但携带旧式参数"的畸形 ledger 上可达，属纵深第二道，无独立端到端用例（构造成本＝全套 freeze 前置），如实标注；②B-7 Solana 分支的数值源定位复用 B-1 搜索逻辑（inputs 实物目录→bundle 同目录→data/），bundle 与 holder 文件被人工挪到第四种目录布局时报"实物不可用"拒（fail-closed 方向正确，但报错不指路，工单记录）；③A5 flip 披露核对只覆盖 new-analysis（independent-audit 单段流程不承载溯源披露链，与 distribution_bundle 同口径 NOT_APPLICABLE）；④F-07 "commit 全部完成后收尾（fsync/清备份）失败→不回滚、保留备份报错"分支无独立注入用例（注入面在 os.fsync/unlink 非 os.replace，边际价值低）——该行为逐字对齐 receipt_kernel.publish_txn 的 committed 语义先例，如实标注。

## ⑤ 归因预判

- F-06/F-07 归因＝**修复中新引入**（6.39.4/6.39.0）——两条都是"装闸时给自己留的软出口"（字符串理由通道/逐个写非事务），印证十层元规则"装闸后请闸外的人绕它"。
- GPT-F-06 归因＝fail-open 家族半修残留（CHANGELOG 曾修同族采集器，正式审计入口未等深）——同族等深纪律的又一例。
- 台账族（A-3/A-5/B-6/B-7）共同根因＝"绑定"只做了存在性/哈希自洽，未做**同源等值**——与批 A F-A"自报数字互相印证"同族，本批把"案内三处 owner 余额声明"全部钉到四查同一实物上收口。

---

## 五、验证证据（实跑采集）

- `python3 scripts/tests/test_repair_batch_d.py` → rc=0（F-07 4 场景/GPT-F-06 5 场景/F-06 主链 7＋单元 8＋A5 4/A-1 3/B-4 B-5 3/A-3 2/A-5 1/B-7 2/B-1 B-2 4——全 ok）。
- 变异法自检 5/5 删掉即红（③栏清单），恢复后全绿。
- 受影响既有测试逐一 rc=0：test_handoff_manifest（67 项）/ test_entity_source_trace / test_round4b_provenance / test_round4c_solana_provenance / test_round4_a5_seal / test_a4_gate / test_audit_release_gate / test_review_20260804_p105 / test_repair_batch_a / test_repair_batch_b / test_repair_batch_c / test_distribution_gate / test_adjudication_validator / test_supply_truth_gate / test_receipt_kernel。
- 三守卫：changelog_lint PASS（6.40.0 唯一且序正确）；docs_lint --all PASS（58 文档）；invariant_scan PASS（consumers 63、atomic 46，新登记 flip-adjudications/v1 消费点＋refresh_manifests=multi_file_txn 新原子语义）。
- 契约：test_contract_routes PASS——manifest 146 条与 contract_ids_snapshot 146 条**双向相等**；新增 CT-SEMANTIC-49~56 八条（批 A：tolerance-waiver/v1＋model_probe_block；批 B/D：mint_total_raw；批 C：camp-series-provenance/v1＋figure2-check-receipt/v1；批 D：flip-adjudications/v1＋NO_CLOSED_SAMPLED＋superseded 归档语义），每条 needle 实测在权威文档在场。
- counterexamples/ 五脚本独立重放全 rc=0（含批 A/B 存量两个回归无损）。
- **全量首跑抓获三处收尾（B-7 掀出的跨夹具失真面，全部按"补真实形态"修复）**：
  1. batch3 Solana 切片：build_case 编造三账（0xabc@123）与真实四查（slot 动态、owners 真产物）不同源——切片补 align（对齐 solana_scan_work/holders_owners.json）；
  2. batch3 EVM 切片：同因——对齐 balances_evm.json；连带 align helper 同步 audit_input_manifest 登记与 reproduce receipt 的 input_manifest sha（三账重写是夹具动作，冻结输入链必须跟着一致，否则制造第二处假红）；
  3. test_repair_batch_b F-B6③ 文档断言：批 B 时实况＝Solana 无实物锚（文档如实写差异），B-1 落地后实况变了——断言随事实更新为"已对齐＋文件级三验"，守的不变量（文档与实况一致）不变，不是把旧差异钉成永久事实。
- 全量 `python3 scripts/tests/run_all.py`（收尾后复跑）：EXIT=0（见回传实测值）。

## 六、端到端绿例与六卡死点覆盖（plan 验证方案 4）

本轮落法（如实声明）：`state_from_facts→figures` 连续段由批 C `test_repair_batch_c`（EVM t_f04_evm_chain＋Solana 含 burn t_f05_f04_solana_chain，均真跑 replay producer）承载；`figures check→A4 finalize→A5 seal→build_html` 连续段由 `test_a4_gate` new-analysis 全链承载（两段共享 figures check 节点）；批 D 新增 **Solana new-analysis 发布闸 run() 端到端**（build_solana_case，B-2 正主）补齐 plan 指出的"batch3 纵切片只到 audit release"缺口，并把 A5 新 flip 实文核对接入该链（case 无 ledger 走 NO_LEDGER 分支绿、有翻转案走 DISCLOSED 分支绿）。

| 卡死点 | 绿例载体（实测 rc=0） |
|---|---|
| Solana tip（F-01 限 EVM 不误伤 Solana） | test_repair_batch_d B-2 端到端（validate_sources 对 solana accounting 无 tip 要求照过）＋test_batch3_solana_vertical_slice |
| A5 终态重验不死锁 | test_a4_gate new-analysis 链＋test_round4_a5_seal＋本批 A5 flip 三分支（NOT_APPLICABLE/NO_LEDGER/DISCLOSED）绿例 |
| Solana series（sol-rows 转换） | test_repair_batch_c t_f05_f04_solana_chain（replay_edges 真跑产物） |
| 末点对账 | test_repair_batch_c figures check（camps spec 机械派生末点）＋figure2 收据链 |
| dead-sink 闭合（sum=mint≠net） | test_repair_batch_b 锚点c 合成 dead-sink 20% 绿例（mint_total_raw 键名升版后重跑仍绿） |
| burn 合计（非 burn 桶 ≈100%） | test_repair_batch_c Solana burn 案（锁仓/销毁桶口径感知通过） |

## 七、改了哪些文件（范围与铁律自查）

生产：fetch_hypersync_v2.py（F-07）/ audit_closed_accounts.py（GPT-F-06）/ entity_source_trace.py＋handoff_manifest.py＋a5_report_seal.py（F-06 同批同 hunk 组：重放装配与收据消费同文件同批改）/ supply_truth_gate.py（A-1＋A-3 生产侧）/ receipt_kernel.py＋receipt_validate.py（A-3 kernel 面）/ verify_recon.py（A-3 生产侧）/ shared_release_receipt.py（A-3 消费侧＋A-5＋相对路径兼容三处）/ solana_observation.py（B-1）/ holder_distribution_scan.py（B-4＋B-3 v2）/ audit_release_gate.py（B-7）。
测试：test_repair_batch_d.py（新）/ run_all.py（挂载）/ invariant_scan.py（multi_file_txn 枚举）/ invariant_manifest.json / contract_manifest.json＋contract_ids_snapshot.json（D-2 授权）/ test_audit_release_gate.py＋test_handoff_manifest.py＋test_review_20260804_p105.py＋test_a4_gate.py（夹具补真实形态＋B-7 对齐 helper）/ test_repair_batch_a.py（报错换岗断言）/ test_repair_batch_b.py＋test_distribution_gate.py（v2 键名）。
文档：scan-schemas.md（§4a flip 收据权威定义＋§6 v2＋B-1 等深改口＋迁移声明）/ analyze-workflow.md（A-1 作废语义＋双时点契约句）/ report-template.md（figure2 schema 名）/ data-pipeline-solana-capture.md（status 契约）/ split-run.md（v2）。
版本与台账：VERSION/SKILL.md/pyproject.toml→6.40.0；CHANGELOG 6.40.0 全条目（四批＋D-1 追认＋D-3 迁移＋R10 声明）；r10_ledger.md（13 条）；counterexamples/ 三新脚本。【终验勘误（BLOCKER-1）：消化轮 1 追加 R10-14/15 后实为 15 条，见 final_acceptance.md；本句为主施工时点的历史记录，原文保留】

铁律自查：**未 git commit**（HEAD 仍 97b2c65）；批 A/B/C 已收口实现除台账授权点外未动——**台账授权点清单**：B-4/B-5＝holder_distribution_scan._bound_replay_stats 指定点（批 B 主改文件，R2-O1/O2 点名）；B-1＝solana_observation.validate_observation_bundle（F-B6① 点名）；B-7＝audit_release_gate.check_three_ledgers（:335-356 点名）；A-1/A-3＝supply_truth_gate／shared_release_receipt（批 A 台账 F-D 后半/F-G 后半点名）；A-5＝shared_release_receipt（N-1 第二建议点名）。批 A/B/C 的判定语义零放宽（报错换岗两处如实记录，被拒面不减）；无为绿改弱断言（夹具修复均为"补成真实生产形态"，既有断言零删改——test_handoff_manifest 两处 needle 更新语义等价）。

## 八、A-2／A-4 评估结论（任务点名回传项）

- **A-2（approved_tolerance_bps 硬顶＋observed_diff_bps 预先虚报）**：核批 A 工单原始语境（batchA_fixround2_workorder §六＋batchA_adversarial_recheck 尾表）后判定——**未被现行 FORMAL_TOLERANCE_BPS_MAX 消费侧钳制实质覆盖**：现行钳制只管"无 waiver 时容差 ≤10"，有 waiver 时 approved 无上限、observed_diff_bps 可预先写大值覆盖未来一切偏差，两数合起来 waiver 可成万能通行证；且"批多大/要不要二人复核"是政策决定（复核者原话）。**不做，标"待用户裁决"留 R10**（r10_ledger R10-12，含完整核证）。
- **A-4（EVM 链上观测件锚定）**：属新功能面设计活（对标 Solana bundle 须新造 attested 观测 producer＋消费绑定链），与 A-3 的路径语义改造**不顺手**；批 A 已有"明示局限"入 independent-audit-protocol.md 兜底。**不做，设计要点四条留 R10**（r10_ledger R10-13）。

## 九、R10 弱闸旁证（plan 验证方案 6，实测输出、不引用弱闸 rc=0）

三命令 staging/部署 SHA 实测（shasum -a 256，2026-08-13）：

```
token-analyze    staging=f227da3bddcee26b6a5d89fd325026a46bd208dd4f18017b670bf97f1280296e deployed=同值 EQUAL
token-analyze-1  staging=9832eace6960bb6626a2b6e55f4c88745c5ffa33c640bc7eb97c71544aa0f215 deployed=同值 EQUAL
token-analyze-2  staging=510152a8a40efcc3f9b9a166b17d612b5166365baca22a6554771014cadebce6 deployed=同值 EQUAL
```

解释器与全部 21 个直接依赖（pyproject dependencies）version＋import 实测：Python 3.14.6（满足 requires-python >=3.14）；duckdb 1.5.4 / pyarrow 25.0.0 / pandas 3.0.3 / numpy 2.5.0 / hypersync 1.2.0 / requests 2.34.2 / certifi 2026.6.17 / httpx 0.28.1 / tenacity 9.1.4 / msgspec 0.21.1 / networkx 3.6.1 / rustworkx 0.18.0 / hypothesis 6.158.1 / psutil 7.2.2 / matplotlib 3.11.0 / reportlab 5.0.0 / pypdf 6.14.2 / PyMuPDF 1.27.2.3 / openpyxl 3.1.5 / google-cloud-bigquery 3.42.2（import google.cloud.bigquery OK）/ pydata-google-auth 1.9.1——**21/21 import OK**。

批D施工完成
