# 批 C 消化循环第 1 轮工单（F-C1~F-C6 全修）

施工方：Fable 5 直接施工。基线：主施工 `20ed20b`（主工单曾写"未 commit"系回传时序原因——回传后由裁判 commit，本轮起以 `20ed20b` 为基线，历史工单不改）。盲审报告：`batchC_adversarial.md`（6 条，最高 P0）。本轮全部 6 条＋两件随轮小事收口；工作树未 commit，留裁判验收。

---

## 逐条完成态

### F-C1（P0）——来源绑定焊成必经之路 ✅

- `state_from_facts.py` main：**formal（默认）编译 `--series-source` 必填**，缺席 BLOCK exit 2（错误信息点名"闸不挂可选参数"）；显式 `--exploration` 才可豁免，产物 provenance 落 `series_binding="exploration-unbound"` **非正式标记**（参照 supply_truth formal/exploration 双轨先例：mode 如实入产物）。formal 绑定产物落 `series_binding="producer-sidecar"`＋`camp_series_sidecar` 块。
- **防伪闭环**：`source.provenance` 预置 `series_binding`/`camp_series_sidecar` 即拒（标记只能编译器按验证结果生成——否则手编 source 直接自贴 formal 标签绕过整条链）。
- **下游闸接线**（盲审收口建议 1 后半，落在 audit_release_gate new-analysis）：新函数 `check_series_binding`——analysis-state **含 camp_share_series 就必须** `series_binding=="producer-sidecar"`，且 `camp_series_sidecar.series_file` 指向的序列实物（案根与 data/ 两层、拒符号链接）sha256 与登记一致；exploration-unbound／无标记手编 state 在发布闸拦死。无 camp_share_series 的旧简报型 state 不强加（无序列即无绑定对象，p105 fixture 实证不误伤）。
- 盲审原反例转拒实测：手编"项目方 5%→40%→88.8% 吸筹"序列、闭合形态、无 `--series-source` → **exit 2**（修前 rc=0 直通）。
- 边界保持：旧案不经 compile_state 的 fig1 重绘路径零触碰。

### F-C2（P1）——存量普查＋分类定口径 ✅（含上报段，见下）

诊断脚本全库扫描（两案库全部 analysis-state.json，**34 个含 camp_share_series 的 state**，比盲审 13 个口径更全——含 data/ 子层与多链子案）。分类表：

| 类 | 定义 | 案（文件） | 处置口径 |
|---|---|---|---|
| **A：仅白名单拒（口径不兼容·旧标签体系/自造桶名）** | 数值面（有限/值域/闭合/日期轴）**全过**，仅桶名不在 CAMP_ORDER_MODERN | QUQ`['狙击集团']`、ASTEROID`['狙击集团']`、APU 旧版`['项目方(初始分发地址)','狙击集团','跨链桥','销毁(dEaD)']`、TAG×2 份`['大庄Bitget','大庄Gate']` | 不重编译不受影响；重编译须先按**案内证据**把桶归入现代名——**映射是分析判断非机械替换**（"狙击集团"在 QUQ 是历史狙击层、在 PYTHIA 是 63% 波次庄，禁全局映射表）。已文档化 scan-schemas.md §13「存量迁移」 |
| **B：形态整体不合（旧 schema）** | camp_share_series 非 `{dates, series}` 结构 | **21 个**（含 B2、TROLL、PYTHIA×2、KOGE 旧版、EGL1、IQ、GMX、SPX6900 等） | **非本批引入**——compile_state 自 6.13.0 起的结构检查（`结构非法`）对它们同拒；这些 state 由旧工作流手工产出、重绘走 fig1 直读不经 compile。不适用新口径、不需迁移动作 |
| **C：真数据问题（白名单＋数值面双拒）** | 白名单外桶名之外还有数值面硬伤 | KOGE 新版（`['质押设施']`＋**日期轴重复**：dates[8]='2025-06-15' 与前一点同日）、MOG（5 个自造桶名＋**第 93 点合计 99.9440**，差 0.056pp 超 0.05 容差） | 按 F-B5 模式文档化"刻意收紧"：重编译须先修数据或用当前版 producer 重出序列。已入 scan-schemas.md §13 |
| OK | 全过 | AKE、BITCOIN、BULLA、FROGGIE、MAPLE_FINANCE、WILD 等 7 个 | 无动作 |

关键定性修正（对盲审报告的一处细化）：盲审"13 案 7 拒"中的 **B2 属 B 类**——它不是本批数值面误伤，旧编译器同样拒它；本批**新增**的拒绝面实际是 A 类 4 案（5 文件）＋C 类 2 案。

**⚠️ 上报段（裁判条款触发：影响在用流程，不自行拍板）**：
1. **QUQ（A 类，监控在跑）**：现行监控不碰 compile_state 不受影响；但下次 update/重编译 state 即撞白名单闸，"狙击集团"桶归入哪个现代桶（历史大户？散户？）需按 QUQ 案内证据（狙击层已离场的历史定性）人工裁定。
2. **TAG（A 类，HTML 升版重验交接中）**：`大庄Bitget/大庄Gate` 是实体级分桶（图 1 曾按实体拆线）——归并回"大庄"阵营后两条线合一，图形语义变化需案内确认；交接文档 SKILL_PATCH_PROPOSAL.md 的重验流程若走 compile_state 会被拒。
3. **MOG（C 类，freeze 死结复跑高概率）**：除 5 个自造桶名外，第 93 点闭合差 **0.0560pp 超容差 0.05 一线**（数据微洞或舍入累积）——是"修数据"还是"容差边界裁决"归裁判定，施工方不放宽闸。
以上三案重编译前的迁移动作（桶名归并方案/数据修正）均需案内分析判断，超出机械修复权限，待裁决。B2 虽在 MEMORY 有"发布闸重封史"，但属 B 类旧形态，不因本批新增受影响，不列上报。

### F-C3（P1）——登记面命中结构化 ✅

- `registry_anchor_check` evm 分支重写：①supply_truth.json 本身过合法性三验——`schema=="supply-truth-receipt/v3"`（**真实生产者形态**，TAG 案实物核对；修主批时测试夹具用的自造 `supply-truth/v1` 正是批 B 教训里的影子形态，本轮一并矫正为真实 schema）＋`verdict=="PASS"`＋`exit_code==0`（load_supply 先例同款）；②sha 必须命中**特定字段位置** `inputs.replay_stats.sha256`（批 A 哈希绑定的那一格），全文包含式的 `_sha_values` 递归收集**整个删除**（不留死代码）。sol 分支：reconcile 收据加验 `schema=="solana-reconcile/v2"`（真实生产者 cmd_reconcile 形态）＋gate_pass。
- 盲审 1663 字节伪造链转拒实测：`{"sha256": "<sha>"}` 式 supply_truth → **exit 2**（"不是合法供给真值收据"）；带真 schema 但 sha 塞顶层任意位置 → **exit 2**（"缺 inputs.replay_stats.sha256"）；verdict=FAIL → exit 2。

### F-C4（P2）——双式闭合互救关死 ✅

- 新函数 `closure_mode_for(denominator)`：净分母族（current_net_supply/net_supply）→"net" 单式（只认非 burn 之和≈100）；total 族（mint_total_legacy/config_total_supply）→"total" 单式（只认全桶之和≈100）；未知口径拒。`validate_series_payload` 增 `closure_mode` 参数（默认 "dual" 保持手填路径宽式——无 sidecar 无口径信息）。`bind_series_source` 在登记面/末点对账前按 sidecar.denominator 先跑单式严判。
- 盲审两个互救构造转拒实测：净族"非 burn=95＋burn_cum_pct=5 蹭 s_all" → 拒（且同构造在 dual 下确实曾放行，互救实证）；total 族"s_non=100＋锁仓 7=总量 107%" → 拒。burn 合法绿例两族各一照常过。

### F-C5（P2）——check 落收据＋发布闸复验 ✅

- `figures_from_facts check` 每次对账（PASS/FAIL、formal/exploration）落 `figure2_check_receipt.json` 到 **--series 文件同目录**（whale_series 惯例在案根→收据即案根；施工中自查：初版写 cwd 会在任意调用处漏文件，当场改为 series 同目录）：schema/mode/tol_pp/verdict/facts+series 双输入 sha+size/mismatches/UTC 时间戳；tmp+fsync+os.replace。政策拒（exit 2）不产收据。
- `audit_release_gate`：`figure2_check_receipt.json` 加入 **NEW_ANALYSIS_REQUIRED**（必经资产，缺席即"缺必需资产"），新函数 `check_figure2_receipt` 复验 schema＋`mode=="formal"`＋`tol_pp==0.05`＋`verdict=="PASS"`＋series 实物在案根时 sha 加验（对账后改序列被抓）。exploration 放宽的运行有痕且过不了发布闸——不再与 F-02 差留痕面（waiver 级收据裁判未要求，未加）。
- p105 fixture（new-analysis 绿例单点，batch_b/batch3 复用）补件走**真实生产者**：fixture 内真跑 `figures_from_facts check`（空 whale_series 对空 entities 合法 PASS）产收据，零手搓形态。
- 施工中自查②：new-analysis 绿例消费面预检漏了一处——`test_a4_gate.py` P1-05 的 case_new 走 `build_html --mode analysis-new`（内嵌 audit_release_gate），首轮 run_all 抓出缺新必经件（rc=1，"缺必需资产: figure2_check_receipt.json"）；同法补件（fixture 真跑 check 产收据），a4_gate 23 项复绿、run_all 复跑全绿。此例证明 REQUIRED 化真的必经（连自家测试的绿例都逃不掉），也证明 run_all 全量是消化轮不可跳过的收尾。

### F-C6（P3）——producer fail-loud＋fsync ✅

- `replay_pass2.py`/`replay_duck.py`：balances_final.json 缺席从"静默少绑 sidecar"改为**当场硬拒 exit 2**（与缺 camps 同口径；同一批内两处缺件两种态度的不一致消除）。
- `write_series_sidecar`：补 `flush+os.fsync+os.replace`，对齐仓内最强先例 receipt_kernel。

### 随轮两件小事 ✅

1. **变异表第 11 条补强**（盲审更正）：新增"只改序列中间点（末点/桶名/闭合全不变）"反例——输出 sha 闸**单独命中**（test_repair_batch_c `FC 中间点篡改被输出 sha 独立拦截`），主工单第 11 条的"双防线"表述由此细化为"sha 闸有独立命中区间＋末点对账是第二道独立防线"。
2. **pycache 假阴性防护**：本轮变异自检脚本每次变异/还原后全清 `__pycache__`（盲审第一轮 P12 中招的等长替换假阴性），工单如实记录方法。

---

## 消化轮变异法自检（8/8 成立，先清 pycache）

| # | 校验 | 结果 |
|---|---|---|
| 1 | FC1 formal 必经强制 | ✅ 中和后手编序列 rc=0 |
| 2 | FC1 预置绑定标记拒 | ✅（反例初版缺 series 落到结构检查，补全后单点命中） |
| 3 | FC1 下游闸 binding 检查 | ✅（反例带齐全 sidecar 块＋在档实物，单关 binding 一道即放行） |
| 4 | FC3 schema/verdict 三验与位绑定分层独立 | ✅（关 schema+verdict 两道仍被位绑定拦、四道全关才放行） |
| 5 | FC3 sha 特定字段取位 | ✅（取位换回全文自等后"sha 塞顶层"反例放行） |
| 6 | FC4 净分母单式严判 | ✅（单式换回双式后互救构造放行） |
| 7 | FC5 发布闸 mode 复验 | ✅ |
| 8 | FC6 生产侧缺快照硬拒 | ✅（换回修前静默降级三元式后 rc=0） |

## 测试与退出码证据

- `python3 scripts/tests/test_repair_batch_c.py` → **rc=0**（69→**103 checks**，新增 t_fixround1＋t_fc5_receipt_chain 两区）
- `python3 scripts/tests/invariant_scan.py` → **rc=0**（producers=54/consumers=61/atomic=45；本轮 +3 处登记：figures_from_facts producer figure2-check-receipt/v1、camp_series_provenance consumer 扩 supply-truth-receipt/v3＋solana-reconcile/v2、audit_release_gate consumer 扩 figure2-check-receipt/v1、figures_from_facts atomic `_write_check_receipt`）
- `python3 scripts/tests/docs_lint.py --all` → **rc=0**
- 受影响契约组逐一 rc=0：test_repair_batch_b（41/41，new-analysis 放行绿例带新必经件仍绿）/ test_audit_release_gate / test_review_20260804_p105 / test_figures_from_facts / test_state_from_facts / test_review_resume_integrity / test_wave_scan / test_entity_source_trace / test_batch3_evm_vertical_slice / test_batch3_solana_vertical_slice
- `counterexamples/fake_series_dualfeed.py` → **rc=0**（夹具 schema 矫正为真实 supply-truth-receipt/v3 后三场景仍全符合预期）
- `python3 scripts/tests/run_all.py` 全量 → 首跑 **rc=1**（test_a4_gate P1-05 绿例缺新必经件——见 F-C5 自查②，属必经化的预期连带面）→ a4_gate 夹具补件后复跑 **rc=0（"全部通过"，53 项）**

## 改动文件与 finding 对照

| 文件 | owner |
|---|---|
| `scripts/report/state_from_facts.py`（formal 必经/预置拒/exploration 标记/单式接线） | F-C1＋F-C4 |
| `scripts/lib/camp_series_provenance.py`（登记面结构化/closure_mode/fsync/白名单错误信息补迁移指引/_sha_values 删除） | F-C3＋F-C4＋F-C6＋F-C2 |
| `scripts/report/audit_release_gate.py`（NEW_ANALYSIS_REQUIRED+figure2 复验+series_binding 下游闸；**未触碰** :753 起的批 B 第二层函数） | F-C5＋F-C1 |
| `scripts/report/figures_from_facts.py`（check 收据落盘） | F-C5 |
| `scripts/evm/replay_pass2.py`、`scripts/evm/replay_duck.py`（缺快照硬拒） | F-C6 |
| `scripts/tests/test_review_20260804_p105.py`（fixture 真跑 check 补收据＋facts 补最小 token） | F-C5 配套 |
| `scripts/tests/test_a4_gate.py`（P1-05 case_new 同法补收据，断言未动） | F-C5 配套 |
| `scripts/tests/test_repair_batch_c.py`（+34 checks 两区＋夹具 schema 矫正＋F-C3 断言 needle 随消息更新） | 消化轮测试 |
| `maintenance/.../counterexamples/fake_series_dualfeed.py`（夹具 schema 矫正） | F-C3 配套 |
| `scripts/tests/invariant_manifest.json`（+3 处登记） | 配套 |
| `references/scan-schemas.md` §13（formal 必经/探索豁免/单式闭合/结构化登记面/存量迁移三类口径） | F-C1~C4＋F-C2 文档 |
| `references/report-template.md`（机器强制句/figure2 收据句） | F-C1＋F-C5 文档 |

## 边界自查（铁律逐条）

- 版本三处 6.39.5 未动；contract_manifest.json / contract_ids_snapshot.json 未动（新契约面 figure2-check-receipt/v1 与 --exploration CLI 面记账，批 D 一次性登记）；批 D 生产文件（shared_release_receipt.py flip/两阶段区、audit_closed_accounts.py）未动；批 A/B 已收口实现未动（audit_release_gate 仅在 new-analysis 段**新增**独立函数与 REQUIRED 项，:753-816 的批 B 第二层 hunk 零触碰；supply_truth_gate.py/accounting_gate.py/holder_distribution_scan.py 零触碰）。
- 未 git commit。
- 未为绿改弱断言：p105 fixture 是补输入件（facts 补 token、真跑收据）；批 C 测试的 F-C3 断言 needle 随错误消息文本更新（同反例同分支）；F-05 与数值面主体（盲审判"扎实保留"）除白名单错误信息**追加**迁移指引句外零改动。

批C消化轮1施工完成
