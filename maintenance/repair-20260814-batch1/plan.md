# 批 1 修复计划：数据与报告真实性＋现役回归（R11 工程·第一批）

> 状态：定稿（三路施工面探索完成 → @CX codex 复核完成并融合 → 待用户批准开工）
> ⚠ 开工前置：skill 仓库当前 checkout 停在 `repair-20260814-batch2` 分支（codex 复核时发现）——开工第一步先核对该分支来历、切回 main@c41ed07 再开工程分支，确保基线正确。

## Context（为什么做这一批）

**输入**：两轮独立六视角 review 的合并结论——
1. codex 2026-08-14 全量 review（`~/Documents/5.6筹码分析/token-chip-analysis-main-sixlens-full-review-2026-08-14.md`）：12 项 finding，经 Fable 逐项对 main@c41ed07 代码核实 **12/12 属实**，且与 `maintenance/repair-20260813-sixlens/r10_ledger.md` 的 15 条已知债务完全对应（零新发现，性质=对 R10 台账的独立复核确认）。
2. Fable 2026-08-14 全量 review（`maintenance/review-20260814/review-report.md`，commit c41ed07）：P2×3＋P3×9，其中 RV-07（真 FAIL 落盘死锁）与 RV-04（代理写死 7897）为现役回归。

**用户裁决（2026-08-14）**：
- RV-06 已执行：`~/.claude/skills/tca-supplytruth-fix` 旧快照已移出扫描区（备份 `~/.claude/tca-supplytruth-fix.bak_20260814_033733`），路由二义解除。
- F-10 政策定型（**批 2 施工，本批不动**，此处只记录防丢）：
  - 偏差 ≤10bps：自动放行（现状）；
  - 10bps＜偏差 ≤100bps：普通豁免单（现行 tolerance-waiver/v1）放行；
  - **偏差 ＞100bps：升级特批——必须如实报告原因＋用户显式批准才放行，且交付报告中如实披露特批事实**。
- 批 1 范围用户已认可，开工无需再拍板。

**批 1 五项**（按"实害概率×爆炸半径×修复成本"选入，全部低成本高收益）：

| 项 | 来源 | 一句话 | 为什么进批 1 |
|---|---|---|---|
| F-03 | codex（=R10-3） | EVM 小样本 replay：gate_pass=false 仍写四产物且 exit 0，pass2 不看 gate | 坏数据可静默流进正式序列——结论真实性层面的洞 |
| F-01 | codex（=R10-1＋R10-7） | 图 1 静默丢未知阵营＋A5 不绑图例集合 | 交付报告图上数据可无声消失 |
| RV-07 | Fable review | 真 FAIL 收据被 kernel `_reject_pass_downgrade` 拒绝落盘（实测复现） | 6.36.0 修复中新引入回归，真实 FAIL 场景卡死工作流 |
| RV-04 | Fable review | skill 全库写死 clash 7897，08-12 Surge 迁移（6152）完全未适配 | 下次跑 Alchemy 等代理通道必踩 |
| F-04 | codex（=R10-4） | fetch_hypersync_v2 仍收位置明文 token 且优先级最高 | token 进 ps 的安全面；修复成本极低顺手带走 |

## 工程纪律（沿用既有惯例）

- 工程目录：`maintenance/repair-20260814-batch1/`（结构对齐 repair-20260813-sixlens）。
- 每项按 `references/maintenance-review-repair.md` 工单模板：不变量、全库同族 rg、原反例＋同族变体＋失败分支、先红后绿、六视角自审、归因预判。
- 施工完成 → 独立盲审 → run_all 全量 suite → commit（用户已授权 commit 后自动 push）。
- 版本号：6.40.0 → 6.41.0（CHANGELOG 同步）。

## 施工细节

### 修复 1：F-03 replay gate fail-closed

**不变量**：重放引擎算出 `gate_pass=false` 时，进程必须以非零退出码终止调用链；正式序列编译（pass2）不得消费 gate 未通过的 replay_stats。

**现状**（探索核实）：三引擎中 `replay_pass1.py` 是唯一 fail-open 孤例——`replay_duck.py:587-588` 与 `replay_stream.py:251-252` 都已是"产物照落＋`sys.exit(0 if gate_pass else 4)`"；pass1 四产物落盘后隐式 exit 0，仅打印口头警告。`replay_pass2.py:31` 只读 `mint_total_wei` 不看 gate。缺文件 `FileNotFoundError` → warn＋continue（preflight 与 open 之间有 TOCTOU 窗口）。

**改法**：
1. **pass1 对齐 duck/stream**：四产物保持落盘（`golden_baseline.snapshot()` 依赖产物在场，duck/stream 也是先落盘再退出），末尾加 `print("[gate]", ...)` ＋ `sys.exit(0 if gate_pass else 4)`，文案与码逐字对齐 [replay_duck.py:587](../../.claude/skills/token-chip-analysis/scripts/evm/replay_duck.py:587)。
2. **pass1 缺文件 fail-closed**：`FileNotFoundError` 的 warn＋continue 改 `SystemExit`——preflight 已保证文件在场，之后消失＝环境异常必须停（关 TOCTOU 窗口；这也是 `maintenance-review-repair.md:18` 列为经典判例的活体残留）。
3. **pass2 前置 gate 检查**：读 replay_stats 后按值分流【codex 补强】——`gate_pass is False` → 真 gate FAIL，exit 4；**字段缺失/非布尔/JSON 损坏 → 产物或 schema 故障，exit 2**（不得把产物故障伪装成一次正常算出的 gate FAIL）。均零产物落盘。**不设放行参数**（"闸须为必经之路不可挂可选参数"教训直接适用）。报错文案风格对齐 pass2 现有 F-C6 前置检查（[replay_pass2.py:131-136](../../.claude/skills/token-chip-analysis/scripts/evm/replay_pass2.py:131)）。
4. **duck 内嵌 pass2 改诊断隔离**【codex 复核推翻我原方案"行为不动"，采纳】：原方案的漏洞——duck gate-fail 时按**正式文件名**写 `camp_series.json`/`entity_series.json`＋sidecar，外形与正式件相同，可进 `state_from_facts --series-source`；而编译期主要验 supply-truth PASS，supply-truth 只对总供给闭合，**负余额盘可以供给闭合照样 PASS**——正式编译真的能消费 gate-fail 序列，违反本项不变量（更晚的 verify_recon/identity 拦截是另一层，不豁免本层）。改法：duck 调内嵌 pass2 前判 gate；PASS → 照常产正式命名序列＋sidecar；FAIL → 序列输出到显式诊断命名（`diagnostics/gate-failed/` 目录），文件内标 `status=DIAGNOSTIC_GATE_FAILED`，**不产任何可被正式 consumer 接受的 sidecar**，退出码仍 4。
5. **等价性契约重述**（最硬施工约束）：`test_engine_equivalence.py:96-100` 现断言 pass1/pass2 rc==0，而 hypothesis 会随机生成负余额盘。改为：pass1 断言 `rc in (0,4)` 且与 duck/stream 同输入同 gate 同码；pass2 六产物对表**限定在 gate PASS 输入**；gate-fail 输入上断言独立 pass2 exit 4＋零产物、duck 无正式命名序列产物＋无正式 sidecar【codex 补强】。
6. **新反例测试**：负余额盘 → pass1 exit 4＋四产物在场；独立 pass2 exit 4＋零产物；duck gate-fail → 诊断目录产物＋正式路径零序列件；replay_stats 缺 gate_pass 字段/非布尔 → pass2 exit 2；preflight 后删通道文件 → pass1 非零。写法样板照 `test_review_evm_integrity.py:98`。

**文档同步**：`data-pipeline-evm-recon.md:122`（"新引擎内建，比旧引擎严"差异句要消掉）＋`:62`（黄金基准角色句补退出码语义）；`maintenance-review-repair.md:18` 判例回填"已修复"注记（历史判例原文不改）。

**先红后绿反例**：负余额/供给不闭合数据 → 修前 pass1 exit 0＋pass2 照产序列；修后 pass1 exit 4、pass2 exit 4 零产物。

**归因预判**：历史漏检（缺文件 warn＋continue 自初始实现存在；gate_pass 后加但未接退出条件）。

### 修复 2：F-01 图 1 白名单＋A5 图例集合绑定

**不变量**：fig1 输入的每个阵营键要么被画出，要么被显式豁免跳过，要么硬拒——不存在"接受但不画"的静默丢弃；发布链能机器验证"图上画的阵营集合＝state 声明的阵营集合"。

**现状**（探索核实）：`mode_fig1` 收任意键只验长度；`plot_camp_evolution` 取 `CAMP_ORDER` 交集静默丢（[standard_charts.py:172](../../.claude/skills/token-chip-analysis/scripts/report/standard_charts.py:172)）；文档明写"非标准阵营名静默跳过不报错＋出图后必须目检"（防错留给人工）；图例集合无任何持久化载体（只存在于 PNG 像素）；A5 只绑 PNG 哈希。批 C 白名单只装在 compile_state 路径，"旧 state 直喂 fig1 重绘"是文档显式豁免的活路径。

**改法**：
1. **fig1 入口白名单**（`figures_from_facts.py` mode_fig1）：`allowed = set(CAMP_ORDER)`（19 键＝MODERN 14＋LEGACY 5）**＋ `销毁`**【codex 抓到的真洞：`replay_pass2.py:63` EVM legacy 分母模式实际产名为"销毁"的堆叠桶，不在 19 键且无配色——不补则带 burn 的旧 EVM 基线从静默丢变硬拒，"旧案重绘兼容"承诺变假。采纳方案＝把"销毁"列为显式 legacy 绘图键并在 `CAMP_COLORS` 补配色（与"锁仓/销毁"同色系）】`| {"burn_cum_pct"}`；未知键 `SystemExit(2)`，报错文案对齐 `camp_series_provenance.py:326-331` 句式（列出坏键＋可用集合＋迁移口径指引）。
   - `burn_cum_pct` 豁免跳过必须**结构化落进收据**【codex 补强：只打印一行则"实际绘制＝state 键集"仍是假命题】：收据记 `excluded_series=[{"key":"burn_cum_pct","reason":"non_stacked_metric"}]`（含在场性/长度/有限值检查），发布闸只允许这一个豁免键被排除。
   - **与 compile_state 白名单（仅 MODERN）不等深是有意的**，理由写进工单 §①：fig1 承担旧案基线重绘（`scan-schemas.md:571` 显式豁免口径），LEGACY 键可画、不属静默丢弃面；"新报告禁 legacy"由编译路径的闸负责。白名单来源 import `CAMP_ORDER`（唯一权威，禁手抄清单）。
   - 退出码：白名单拒用 exit 2（对齐 `state_from_facts` BLOCK/2 与 `camp_spec`/2），`figures_from_facts.py:33-34` 退出码 docstring 同步重划。
2. **抽共享纯函数 `select_fig1_series()`**【codex 补强，采纳：防第二份实现漂移】：`plot_camp_evolution` 现自筛实绘集合只返回路径——把"输入 series → (实绘 camps 有序列表, 豁免键列表, 拒绝键列表)"抽成纯函数，绘图与收据同源消费真实绘制清单，mode_fig1 不得独立推算第二份。
3. **fig1 落图例收据**：`mode_fig1` 出图后落 `fig1_legend_receipt.json`（schema `figure1-legend/v1`）：实绘 camps 有序列表＋`excluded_series`＋**overlay 冻结"标签＋组成 camps"（非只标签文本）＋价格 CSV 的 path/size/sha256 绑定（如有）**【codex 补强】＋输出 PNG sha256＋输入 state sha256；落盘范式照抄同文件 `_write_check_receipt`（:169-195，tmp＋fsync＋replace）。
4. **A5 seal 冻结图例收据**（实物层）：`SCHEMA` 升 `a5-report-seal/v3`（`producer` 串同升 `/v3`【codex 补强】）；`create_seal` 把 legend receipt 以 `entry()` 三元组纳入 payload；`validate_seal` 增交叉核对【codex 补强，四条】：收据绑定的 PNG ∈ 报告 images 集合、收据 state hash＝当前标准 `analysis-state.json`、收据内 PNG hash＝当前 PNG、camps/豁免键/overlay 组成可从当前 state 经 `select_fig1_series()` 重算一致。
   - **workflow profile 范围**【codex 抓到的矛盾，采纳】：A5 seal 同时服务 new-analysis 与 independent-audit——legend 段仅 new-analysis 强制；independent-audit 走结构化 `NOT_APPLICABLE`（对齐 `provenance_flip_bundle` 现有范式 [a5_report_seal.py:73-74](../../.claude/skills/token-chip-analysis/scripts/report/a5_report_seal.py:73)）。
   - **v2→v3 存量迁移语义写明**【codex 补强】：已生成的旧 HTML 不受影响；v2 不得冒充 v3；存量案要维持正式身份必须重出 legend receipt＋v3 seal；无法重出只能走带水印的 legacy-recompile。升版连带 5 处同步：`invariant_manifest.json` 4 处、`contract_manifest.json` CT-DISTRIBUTION-11 needle、`test_distribution_gate.py:151` 源码字面量守卫、文档 4 处（`analyze-workflow.md:162,166`、`split-run.md:128`、`report-template.md:13-14,289`）。
5. **发布闸做语义重算**（信任根层，防"收据自报自洽"）：`audit_release_gate` 把 `fig1_legend_receipt.json` 列入 `NEW_ANALYSIS_REQUIRED`（:40-47），并用发布闸已有的 state 消费面经 `select_fig1_series()` 重算期望集合与收据逐字段比对——收据实物由 A5 冻结、语义由发布闸对 state 重算，两层合拢。消费范式照 `audit_release_gate.py:933-981`。
6. **文档同步**：`analyze-workflow.md:164` 与 `report-template.md:294`（"静默跳过＋人工目检"改为机器闸口径）；`scan-schemas.md:571` 重绘豁免句补"白名单硬拒已覆盖 fig1 入口"；`playbook-entity-cluster-tiering.md:117` 同句式更新。
7. **测试**：`test_figures_from_facts.py` 补未知阵营反例（现 fixture 全是合法键，零未知键用例）＋"销毁"legacy 键绿例；A5 v3 与 legend receipt 的先红后绿；发布闸缺收据/收据与 state 不符/豁免键外的排除三条拒绝反例；independent-audit 的 NOT_APPLICABLE 绿例。

**先红后绿反例**（codex 原反例）：state 含 `大庄=[60]`＋`未知阵营=[40]` → 修前 wrapper 报"2 阵营"exit 0、图上只有大庄；修后 exit 2 硬拒并列出坏键。

**归因预判**：历史漏检（行为自 2026-07-22 起存在，早于修复基线；按归因从严规则③需排除前两类——批 C 白名单的不变量声明面明确不含 fig1 重绘路径，可排除半修残留升格，维持历史漏检）。

### 修复 3：RV-07 真 FAIL 落盘死锁

**不变量**：合法的真 FAIL 结果必须能落盘成为当前收据；旧 PASS 只能经显式归档（`.superseded-<UTC>`）让位，"无归档直接降级"仍必须被拒绝。

**根因**：`receipt_kernel.py:313-317` 的 `_reject_pass_downgrade` 在 `publish_overwrite`（:355）/`publish_txn`（:378-379）里无条件拦下 PASS→FAIL；producer 的 except 把它当"通道故障"报 exit 1，旧 PASS 原地不动，重跑永远撞同一保护（实测复现在案）。已有解锁语义 `invalidate_stale_receipt`（`supply_truth_gate.py:208-233`，`path.replace(f"{name}.superseded-<UTC>")` 原子归档）只挂在 policy_reject 出口。

**改法**：
1. **kernel 层加显式原语**（codex 复核同判：明显优于五出口散装归档）：新增 `publish_supersede`。原语规格【codex 补强七条，采纳】：
   - 只允许新载荷为合法 `FAIL/exit 2`（verdict/exit_code 一致性沿用 kernel 现有校验）；
   - 旧件必须是 PASS，且新旧 **target 完全相同、schema 属同一允许家族**（target/schema 不同的旧件不得被误归档）；
   - 先 stage＋fsync 新 FAIL；
   - **归档用同目录 hard-link（先对旧 canonical 建唯一 link，再 `os.replace` 新 FAIL 到 canonical）**——canonical 全程无缺失窗口；最终 replace 失败时旧 PASS 原位未动，只需撤归档 link 即回滚（优于我原方案"先改名再写"——那有 canonical 缺失窗口）；
   - 归档名用现有微秒＋PID 的 `_run_id()`（防同秒碰撞），不用秒级 UTC；
   - 同一 canonical 的并发写显式检测并 fail-closed；
   - 父目录 fsync 补齐。
   `_reject_pass_downgrade` 对普通 `publish_overwrite/publish_txn` 保持原样拒绝——"归档后才准降级"的不变量集中在 kernel 一处。
2. `invalidate_stale_receipt` 的 schema 白名单泛化（现只认 `supply-truth-receipt/` 前缀，`supply_truth_gate.py:228-230`）：改为按各出口自己的 schema 家族传入，防误伤占位文件的保护保留。归档件**不自动清理**【codex 建议，采纳：体积小且是审计证据】——同时确认 handoff/glob/消费者只认 canonical 精确文件名（工单里 rg 点验）。
3. **五个真 FAIL 出口接入**：`supply_truth_gate.py:544`、`verify_recon.py:165`、`time_spotcheck.py:301`＋`:402`、`window_fetch.py:233`（FAIL 分支）——真 FAIL 落盘改走新原语；退出码语义修正（FAIL=exit 2，不再是通道故障 exit 1）。
4. **window_fetch 出口单独设计**【codex 抓到的多文件事务问题，采纳】：它在发布 FAIL receipt **之前**已移动旧正式数据、写 partial/gaps——若 receipt 发布再失败，会留下"旧 PASS receipt 仍在、其引用的正式数据已被移走"的混合状态。单文件 `publish_supersede` 不覆盖这个场景：该出口的提交顺序（先归档 receipt 还是先动数据）与失败回滚需专门设计＋专门注入测试。
5. 确认剔除面（不动）：`window_fetch.py:203`（list 载荷不受检）、`scan_token_accounts.py` 各 PASS 件、`anchor_plan.py`（RawBytes/无 verdict）、`publish_restore_on_fail`（无生产调用方）。
6. **反例矩阵**【codex 补强，采纳】：stage 失败／建归档 link 失败／新 FAIL replace 失败／回滚失败／归档名碰撞／PASS→FAIL→PASS→FAIL 快速循环／旧件 target 或 schema 不同不得被归档——七条全部入 counterexamples。

**必须保持红**（回归锚）：`test_batch1_receipt_paths.py:87-95`（无归档直接 PASS→FAIL 仍拒＋字节不变）、`test_repair_batch_d.py:627-651`（policy_reject 归档不误伤）、`test_repair_batch_d.py:1315-1325`（参数错不归档）、`test_sixlens_receipts.py:255-264`（写入炸时不留正式产物）。

**先红后绿反例**：旧 PASS 在场 → producer 判真 FAIL → 修前：exit 1＋"receipt 写入失败"＋磁盘仍 PASS；修后：exit 2＋FAIL 收据落盘＋旧 PASS 变 `.superseded-<UTC>` 归档件。

**同步面**：`references/analyze-workflow.md:66`（exit 语义句）、`supply_truth_gate.py:36-43` docstring、契约 `contract_manifest.json:149`（CT-SEMANTIC-56 的 superseded needle 保持在场）、`invariant_scan.py:959` 的 success_primitives 分母推导不被新原语破坏（新原语需登记）。

**归因预判**：修复中新引入（6.36.0 kernel 普遍化时未评估合法 FAIL 重跑路径）。

### 修复 4：RV-04 代理统一解析器（含 RV-17 连锁收编）

**不变量**：skill 内所有出网脚本的代理取值走同一解析器；用户换代理软件只改一处环境变量（`CHIP_PROXY`）即全库生效；任何脚本不再写死端口。

**现状**（探索核实）：`CHIP_PROXY` 全库零实现；`6152`/Surge 适配为零；代码级 10 文件写死 7897——其中 4 件**无覆盖参数**（`stake_decode.py:23`、`fast_probe_tops.py:16`、`gas_origin.py:19`、`trace_wallet.py:15`，全是 `subprocess curl -x PROXY`，当前环境完全不可用）；6 件可覆盖但默认值已失效（`accounting_gate.py:403` 对 Alchemy URL 自动注入、`fetch_sqd_transfers_v2.py:101`、`audit_closed_accounts.py:41`、`whale_deep.py:23`、`probe_escrows.py:20`、`probe_window_moves.py:65`）。

**不变量表述缩窄**【codex 指出原表述"所有出网脚本统一"与实际收编面不一致，采纳】：现役代码不得硬编码代理端口；凡取代理值必经 `resolve_proxy()`。已有 `--proxy` 参数但无写死默认的脚本（`verify_recon`/`supply_truth_gate`/`time_spotcheck` 等）不在本批强制收编面，工单 §② 点名登记。

**改法**：
1. **新建 `scripts/lib/proxy_config.py`**（lib 内无既有实现可改造）：`resolve_proxy(cli_value=None)`，优先序＝**显式 CLI `--proxy`（非默认值）＞ `CHIP_PROXY` 环境变量 ＞ 端口探测（127.0.0.1:6152 → 7897，TCP connect 短超时）＞ 直连（None）**。
   - `--proxy ''` 显式直连并压过环境变量与探测；兼容既有 `--proxy none` 写法【codex 补强】；scheme 校验＋日志对含账密的代理 URL 脱敏【codex 补强】。
   - **探测的失败模式如实声明**【codex 建议正式链禁探测，此处部分否决】：TCP connect 只证明端口有人监听，不证明是可用代理（上游死/协议不符时会选中僵尸端口）。保留探测的理由：①探测选错的后果是请求失败→各脚本 fail-closed 报错退出，**不会假成功**；②迁移初衷就是"用户不配置也能用"，砍掉探测则初衷落空。缓解：使用探测结果时打印一行"经端口探测选用 <url>，建议固化 CHIP_PROXY 环境变量"；文档把 CHIP_PROXY 固化写为推荐姿势。否决 codex 的"错误驱动换路"备选（transport 错误判别要在 httpx/curl/subprocess-curl 三种后端各做一遍，复杂度不成比例，且透明重试会掩盖网络问题）。
2. **10 个代码点收编**：4 件无参数件补 `--proxy` 参数＋走解析器；6 件默认值件改 default=None＋走解析器；`accounting_gate.py` 的 Alchemy 自动注入改为"未显式给且 CHIP_PROXY 未设时走探测"，不再写死 7897。`fetch_sqd_transfers_v2` 保留其"直连优先、异常后切代理"的粘住语义【codex 补强：只把候选代理从写死 7897 换成解析器结果，不得无意改成代理优先】。
3. **两个隐性阻塞点**：①`net.py:309` `RpcPool` 的 `trust_env=False` **保留**（显式代理管理是有意设计），解析器结果经 `proxy=` 形参显式传入——不靠 shell 环境变量隐式生效；②`curl_json`（net.py:83-140）无 `-x` 支持——扩 `proxy` 参数（curl 后端补 `-x`）。
4. **RV-17 独立修复**【codex 复核推翻我原判断"随代理收编消失"，采纳——我原判断是错的】：`stake_decode.py:26` RPC 全失败返回 `None` → 空账本 `tot=0` → 链上余额默认 `onchain=0` → 打印"[闭合]"——这是 fail-open 结构缺陷，代理修好只解决"当前环境连得上"，上游再失效仍假闭合。独立修：任一签名页/交易解码/余额观测失败 → 闭合结论标记为不可计算、不得用默认 0 顶替、exit 非零；诊断 JSON（若保留）标 `complete=false`/`verdict=ERROR`，不得输出正式"[闭合]"字样。反例：断网/坏代理下跑 stake_decode，修前打"[闭合]"exit 0，修后 exit 非零＋ERROR 标记。
5. **文档同步**：7 处 docstring/CLI help（`supply_truth_gate.py:23`、`accounting_gate.py:22`、`fetch_alchemy.py:12`、`decode_txs_v2.py:14`、`probe_window_moves.py:11`、`price_check.py:21`＋`:136`）＋3 处 references 命令示例（`data-pipeline-solana-capture.md:49`、`labels/MAINTENANCE.md:65`；`environment.md:64-65` 是坑记录不改）＋"走 clash 代理"叙述族（`data-pipeline-evm-channels.md:192` 等）统一改为"代理经 CHIP_PROXY/--proxy 解析"表述。
6. **范围控制**：`http_get_many` 无 proxy 形参（RV-09，P4 观察项）——本批**顺手补**（成本一行级）但不展开重构；archive 件（`archive/scripts/gas_fast.py`）不动。

**先红后绿反例**：无 clash 环境（当前真实环境）下 `stake_decode.py` 等四件——修前 curl 连不上 7897 超时/报错；修后经 CHIP_PROXY 或 6152 探测正常出数。RV-17 反例见上。

**验收**：断代理环境四件工具可用性恢复；`CHIP_PROXY=http://127.0.0.1:6152` 一变量全库生效实测；新增守卫测试（全库 rg 无裸 7897 残留＋解析器优先序单测＋`--proxy ''`/`none` 语义单测）。

**归因预判**：RV-04 历史漏检（08-12 环境迁移后的存量失配）；RV-17 历史漏检（fail-open 自实现起存在）。

### 修复 5：F-04 v2 位置 token 移除

**不变量**：任何现役 HyperSync 采集入口不得让 secret 进入 argv/ps；token 取用优先序全族统一为 **显式 `--token-file` ＞ `HYPERSYNC_TOKEN` 环境变量 ＞ 默认 token 文件**。

**现状**（探索核实）：v2 是全库最后一个漏网入口（grep 确认唯一）。v2 现行优先序与 v1 完全相反（位置参数＞env＞文件）；argparse 在 `async def main()` 体内、无独立可测 parse 函数；`--token-file` default 写死路径（无法区分"显式给"与"没给"，env 优先序对 v2 恒假）。

**改法**（对齐 v1 原型 `fetch_hypersync.py:20-63` 的结构契约）：
1. 删 `api_token` 位置参数（[fetch_hypersync_v2.py:435-436](../../.claude/skills/token-chip-analysis/scripts/evm/fetch_hypersync_v2.py:435)）——删后剩 `from_block`（int）一个位置参数，argparse 结构性拒绝明文 token，与 v1 逐字对齐，无需显式检查分支。
2. 从 `async def main()` 抽出模块级同步 `parse_args(argv=None)`；`resolve_token` 改为 v1 的 `_load_token(ap, token_file)` 形态（失败走 `ap.error()`＝exit 2，不再 `sys.exit(str)`）。
3. `--token-file` default 改 `None`＋新增模块常量 `DEFAULT_TOKEN_FILE`（易漏的关键机械点：不改这个，"无 --token-file 时读 env"恒假）。
4. `__main__` 的 argv 嗅探分发（verify-done / --refresh-manifests）保持不动；已核实唯一 shell 调用方 `staged_capture.sh` 不传位置 token，删除不破下游。
5. **回归测试**：`test_token_no_positional.py`（已挂 SUITE）把 v2 纳入；按 GPT 复核建议改为**自动枚举 HyperSync 入口**替代手写三文件白名单——枚举分母用**组合判据**（HyperSync import／endpoint 串／正式入口登记面），不得只扫"出现 `HYPERSYNC_TOKEN` 的脚本"【codex 补强：否则新采集器恰好没实现 env 读取就漏出分母，枚举器自身 fail-open】。文件头 docstring"三支"字样同步。
   - **sentinel secret 不得出现在 stdout/stderr**【codex 补强，采纳】：argparse 默认错误会把非法值回显（`invalid int value: 'plaintext-secret'`／`unrecognized arguments: ...`），secret 经 stderr 进 shell/CI 日志。四支脚本（v2＋v1 三支，同族等深）统一最小方案：`from_block` 用自定义 type（解析失败报"须为整数（输入值已隐去）"）＋parser.error 对多余参数的回显抑制（共享 15 行级 SafeParser 助手入 lib 或各文件内联，施工时定）。回归断言升级为"退出码非零 **且** sentinel 串不出现在 stdout/stderr"。
6. **同族外围点名不改**（工单 §② 给理由）：`accounting_gate.py:385` `--hypersync-token-file`（文件形态不进 ps，无 env 回落属口径漂移非本体）；`robinhood/pull_transfers.py:28`＋`gas_trace.py:25`（env 名为 `HYPERSYNC_KEY`、首选 config.json，exploration 支持不进正式面）。
7. **文档同步**：v2 模块 docstring:6-11＋`resolve_token` docstring:415（口径反转必改）；`references/data-pipeline-evm-channels.md:153`（"三支 v1"表述改为覆盖 v2）；`config.example.json:21` 已是正确口径核对即可。

**先红后绿反例**（复用 r9 盲审原反例）：`parse_args(["plaintext-secret", "0", ...])` 修前接受且 token 进 ps；修后 SystemExit≠0。

**归因预判**：老问题修复不全（半修残留）——上轮 RA-07 已点名同族未关到同一深度，按归因从严规则①。

## 工程结构与执行协议

- **施工顺序**【codex 建议，采纳】：①RV-07 kernel 原语＋故障注入 → ②RV-04 解析器＋RV-17 独立修 → ③F-03 replay 语义统一 → ④F-01 绘图 manifest＋legend receipt → ⑤A5 v3 与发布闸消费同批接入＋v2 迁移负例 → ⑥F-04 token CLI → ⑦**共享冲突面统一收尾**：`invariant_manifest.json`/`contract_manifest.json`/`invariant_scan.py`/A5 相关文档/版本串被多项共同触碰，一次性对齐后对最终合并快照跑全量 suite——不允许每项各落一半就宣布通过。
- 工程目录 `maintenance/repair-20260814-batch1/`：`plan.md`（含本计划＋@CX 复核记录）→ 每项一份五栏工单（合并为 `batch1_workorder.md`，五项各自五栏）→ 施工 → `batch1_adversarial.md` 独立盲审 → 消化轮（如需）→ `final_acceptance.md`。可重放反例入 `counterexamples/`。
- 五栏工单模板与归因三分类按 `references/maintenance-review-repair.md` §三/§二执行（缺一栏不开工；归因从严规则强制）。
- 修复批次冻结：期间不掺新功能；最终快照单独验收（不拿"每步各自过了"凑数）。
- 新测试登记动作按九步清单：测试文件（main+非零退出）→ 手动进 `run_all.py` SUITE（无自动发现）→ 契约面如有新 CT-* 双向登记 `contract_manifest.json`＋`contract_ids_snapshot.json` → `invariant_manifest.json` 仅在新增 receipt/transport/原子写/正式入口时动 → 版本四处同步（VERSION/pyproject/CHANGELOG 索引＋详情/SKILL.md 注释）→ run_all 全绿后 commit。
- 版本：6.40.0 → 6.41.0。

## 验证方案

1. **每项先红后绿**：各节"先红后绿反例"在修复 commit 前实跑确认红、修后确认绿；可重放脚本入 `counterexamples/`。
2. **保持红回归**：RV-07 的四个既有守卫（`test_batch1_receipt_paths.py:87-95` 等，见修复 3 节）必须继续红；F-03 的 `test_fault_injection` 三引擎 preflight 负例不受影响。
3. **全量 suite**：最终合并快照跑 `python3 scripts/tests/run_all.py` 全绿（基线 98/98，新增测试后分母上调）；`invariant_scan`/`docs_lint --all`/`changelog_lint` 随 suite 过。
4. **真实环境实测**（RV-04 专属）：当前无 clash 环境下四件无参数工具实际出数；`CHIP_PROXY` 单变量全库生效；断网下 stake_decode 不再打"[闭合]"。
5. **独立盲审**：施工完成后 `batch1_adversarial.md` 盲审轮（边界外一步攻击），消化循环≤3 轮；最终 `final_acceptance.md` 按反例矩阵逐条重放＋破坏性注入抽查。
6. **版本收口**：VERSION/pyproject/CHANGELOG（索引＋详情）/SKILL.md 注释四处 6.41.0 一致，`test_version_consistency` 过。

## @CX codex 复核记录（2026-08-14）

codex 以只读沙箱读库复核了本计划（原文存 `${TMPDIR}/codex-crosscheck/last.txt`），总裁决"方向正确、补强后开工"。逐点处置：

**采纳（已融合进上文各节，正文标【codex 补强/复核】处）**：
- A（F-03）：duck gate-fail 产物外形与正式件相同可进 `state_from_facts --series-source`，且 supply-truth 只验总供给闭合、负余额盘可 PASS——我原方案"duck 行为不动"被推翻，改诊断命名隔离＋无正式 sidecar；pass2 对 gate_pass 缺失/非布尔与 False 分流退出码。
- B（F-01）：`replay_pass2.py:63` 的"销毁"桶不在 19 键——补为显式 legacy 绘图键＋配色；burn_cum_pct 豁免结构化入收据。
- C（F-01/A5）：抽 `select_fig1_series()` 防双实现；overlay 冻结组成＋价格 CSV 绑定；A5 四条交叉核对；independent-audit 走 NOT_APPLICABLE（原计划只写 NEW_ANALYSIS_REQUIRED 有 profile 矛盾）；v2 迁移语义五条；producer 串同升。
- D（RV-07）：hard-link 归档再 replace（canonical 无缺失窗口，优于我原"先改名再写"）；微秒＋PID 命名；并发 fail-closed；七条反例矩阵；归档不自动清理；window_fetch 多文件事务单独设计。
- E（RV-04）：**RV-17 必须独立修——我原判断"随代理收编消失"是错的**（fail-open 结构缺陷，代理修好上游再失效仍假闭合）；`--proxy ''`/`none` 语义、scheme 校验、URL 脱敏；sqd 粘住语义保留；不变量表述缩窄。
- F（整体）：施工顺序按依赖排；共享冲突面统一收尾；F-04 枚举分母组合判据＋sentinel 不进 stdout/stderr。

**部分否决（1 处，理由在 RV-04 节正文）**：codex 建议"正式链禁端口探测（CLI＞CHIP_PROXY＞直连）"或"错误驱动换路"——保留探测作为未配置时的兜底（探测错→fail-closed 不假成功；砍掉则迁移初衷落空），以打印提示＋文档推荐固化 CHIP_PROXY 缓解；"错误驱动换路"因三后端各实现一遍复杂度不成比例而否决。

**codex 环境注记**：其 checkout 在 `repair-20260814-batch2@9ca51d3` 分支，但已核实本批目标文件与 `c41ed07` 零差异，判断适用于所述基线。
