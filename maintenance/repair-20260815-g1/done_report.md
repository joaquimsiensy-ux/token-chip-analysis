# AI-1「正式边界与守卫组」修复工程 done 报告

日期：2026-08-15

分支：`repair-20260815-g1`（worktree `tca-repair-g1`），基线 `ddba1871`（main v6.44.0）

状态：**COMPLETE — 待融合**（本分支不 merge main，交融合方）

负责 finding：F-01（P1）、F-02（P1）、F-03（P1）、F-11（P2）、F-12（P3）、F-14（P3）

计划蓝本：`~/.claude/plans/ai-1-f-01-f-02-f-03-f-11-f-12-f-14-6-p1-precious-pine.md` v2.0（经 @CX codex 复核融合，用户批准）

## 1. commit 链（7 个，全部在本分支）

| SHA | 内容 | 节拍 |
|---|---|---|
| `2073de4` | 包1 test-only：F-02/F-11/F-12 六预期红实证 | 先红（--no-verify 落盘，红=F-11 契约本身，commit 信息已注明） |
| `a50a3e4` | 包1 fix：F-02 审计闸 report fail-closed + F-11 command v3 文本 + F-12 risk_flags 正向白名单 | 转绿 |
| `eb9bc73` | 包2 test-only：F-01 handoff 案根 containment 12/14 红实证 | 先红 |
| `7b99867` | 包2 fix：F-01 全入口收口（R10-15 本体关账） | 转绿 |
| `55697f2` | 包3 test-only：F-03 跨分区 target 九反例红 + F-14 文本卫生守卫（上线即绿） | 先红 |
| `c9b49a7` | 包3 fix：F-03 三元组等式 + **Solana base58 原串保真（范围外真实生产缺陷，四轮裁决扩围）** | 转绿 |
| `72f0084` | 消化轮 D1-D4：盲审四项裁定修复 | 消化 |

每条 finding 均有 test-only 先行 commit，git 历史独立证明先红（不依赖施工方自报）。

## 2. 六条 finding 逐条收口

| # | 修法一句话 | 状态 | test owner |
|---|---|---|---|
| F-01 | 新建 `scripts/lib/case_paths.py::safe_case_file`（原始字符串分段拒空段/`.`/`..`/abs + 逐段 symlink + realpath containment）；handoff `add()` 拆 discover/add_explicit 双入口、V1/V2 重验过 safe、`resolve_bound_path` 删 isabs、freeze CLI 收紧 | **CLOSED**（R10-15 关账交融合方翻转） | `test_repair_g1_handoff_containment.py`（16/16） |
| F-02 | `audit_release_gate.run()` 对 independent-audit + report=None 直接 errors（:1171-1172）；协议文档补明文 | **CLOSED** | `test_repair_g1_audit_report.py`（含真实 CLI 负测） |
| F-03 | `check_formal_case_chain` 扩为 `{chain, token, as_of_block}` 三元组等式：七源 chain 在场即收、state 双字段不 or 折叠、token/block 经 identity-receipt 桥锚结论分区、a4⇒identity 条件必需、EVM 小写归一/Solana 原串精确比较；消化轮补 state.token.address|mint 入 claims | **CLOSED** | `test_repair_g1_cross_target.py`（r1-r10 + g1-g4） |
| F-11 | staging `A5 seal v2`→`` `a5-report-seal/v3` ``；契约对 CT-SEMANTIC-60 / CT-BANNED-15 入 manifest+snapshot；deploy-sync 语义层单源读 manifest、双侧断言、叠加 SHA 严判 | **CLOSED（部署延后）**：装机版 cp 留融合方，分支期 deploy-sync SHA 项预期红 | `test_commands_deploy_sync.py` |
| F-12 | `risk_flags.py` 裁剪后 `fullmatch [a-z0-9-]+` 否则 raise；validate_labels 逐行 try 覆盖两次调用；resolver 四装载口 eager parse；label_lookup 及三写入侧稳定 `BLOCK: risk_flags 脏数据`+非零无裸 traceback | **CLOSED**（R10-18 关账交融合方翻转） | `test_repair_g1_risk_flags_pipeline.py` |
| F-14 | **政策替代非修复**：证据保真裁决（br104）正式替代"清理日志尾空格"建议，历史证据零改动；有效残余=缺现役守卫，落地 `test_repair_g1_text_hygiene.py`（自建分母、豁免 maintenance/blind-reviews/archive/log/txt/json、防装死分母检查） | **CLOSED（政策替代）**：历史区间 `git diff --check` 非零仍是客观事实，不称"已修" | `test_repair_g1_text_hygiene.py` |

## 3. 范围外扩围（施工中裁决，全部有档）

1. **Solana target 小写化真实生产缺陷**（F-03 新等式抓出，@CX 预言证实）：六个写出点 MINT.lower()→原串（`solana_observation.py` / `scan_token_accounts.py` / `anchor_sampler.py` / `supply_truth_gate.py` / `window_fetch.py`）+ `shared_release_receipt.py` canonical_target 按链族归一（**跨组文件定点破例**，行区间 `:32-33`、`:257-269`、`:862-865`，融合方对账）。rg 全库清零验证。
2. **存量夹具迁移四组**：纵切片/producers 夹具原串化、`test_review_20260804_p105.py` 与 `test_repair_batch_d.py` 补 identity 桥造件（真跑生产 producer 链）、F-D2 fixture 补算法文件绑定（断言判据零改动）。
3. **invariant manifest 登记**：audit_release_gate 消费 `identity-holder-snapshot/v2`（consumers 82→83，floor 78→79），其余分母零漂移。

## 4. 盲审与复验（opus 子代理，两轮）

**Round 1**（基线 c9b49a7）：四条裁定——1 条不采纳（"F-11 没修 suite 必红"为跨组部署延后既定决策的认知差）+ 3 条采纳开消化轮 D1-D4：

- D2/P1：跨分区 token 等式补 state 侧绑定（同链换币旁路封口）
- D3/P2：adjudication_validator 同族 containment 收口（连带 handoff freeze caller 改传案内相对参数，不放宽 validator）
- D1/P3：本轮 workorder 文档自清（18 行尾空格+EOF 收敛）
- D4/P3：labels 三写入侧稳定 BLOCK

**Round 2 聚焦复验**（消化轮 72f0084，独立动态探针）：**D1-D4 + B 全部闭合，无 P0/P1，建议收口**。

- D2 七边界探针全对（含 state 双字段不折叠、EVM 归一不误伤、Solana 大小写变体拦截）
- D3 拒 abs/`../`（rc=2）且 freeze 完整链路不误伤（rc=0）
- D4 三写入脚本均稳定 BLOCK+非零+无裸 traceback（含 build_labels excepthook 只拦 ValueError 的反证）
- B：`check_formal_case_chain` 全库唯一调用点为 `audit_release_gate.py:1403`（run() 内部），build_html 也经 run()，空案被 REQUIRED_BY_PROFILE 兜死——**非 fail-open**
- A：Solana 原串对老件回归面 → 见 §6 存量影响

## 5. 数字账

| 项 | 基线 | 现值 |
|---|---|---|
| run_all SUITE | 101 | 106（+5 新测试） |
| 全量结果 | 101/101 | **105/106**（唯一红=deploy-sync SHA 项，预期红见 §7） |
| invariant 分母 | producers 62 / consumers 82 / transport 63 / atomic 52 / formal 58 | consumers 83（+identity-holder-snapshot/v2），余不变；exceptions=0 |
| invariant floor | consumers 78 | 79 |
| 契约号占用 | — | CT-SEMANTIC-60（required `a5-report-seal/v3`）+ CT-BANNED-15（banned `A5 seal v2`） |
| docs_lint | 45 文档 | 45 文档 rc=0 |
| 新增测试文件 | — | 5 个：`test_repair_g1_audit_report.py` / `test_repair_g1_risk_flags_pipeline.py` / `test_repair_g1_handoff_containment.py` / `test_repair_g1_cross_target.py` / `test_repair_g1_text_hygiene.py` |

两条纵切片（EVM/Solana vertical slice）codex 沙箱 loopback EPERM，调度方本机复跑均 PASS。

## 6. 存量影响声明

1. **含 abs/`../` 绑定的旧案**：check-unseal 将 fail-closed=期望行为；新产 ledger 已案内相对（R10-15 台账原话），已交付案不重跑不受影响。
2. **Solana 原串保真回归面（P2 交接项，opus round 2 定性）**：`_claim_token` 对 Solana 原串精确比较，**无大小写兼容**。安全场景=老案整案统一状态（全小写内部一致 → 放行；整案重跑全原串 → 放行）；风险场景=**老案部分重跑/增量更新致新件（原串）与老件（小写）混存同案** → 新等式硬失配 `token 声明矛盾`。本 worktree 内无真实 Solana 存量案数据可清点（TROLL/PYTHIA/GOAT 在仓外分析目录）——**融合方须用仓外存量数据核查是否有落盘小写 base58 的已交付 Solana 案**，再决定一次性重跑对齐或对存量小写做迁移提示。
3. **案内合法 symlink 一律拒**（safe_case_file over-restriction 方向）：handoff 正常流程不依赖案内 symlink（68/68 绿），实际无害，登记在案。

## 7. 预期红登记

`test_commands_deploy_sync.py` SHA 项红：staging 已改 v3、装机版 `~/.claude/commands` 未动（分支期不 cp 是 @CX 修正采纳的既定决策——避免 canonical main 与另两个并行 AI 环境失配）。**融合方在最终快照冻结后执行真实部署 cp，deploy-sync 即全绿**。仓库有"预期红跨单归属"先例（evmobs 工单 B）。

## 8. 遗留项（不阻断收口）

| 项 | 级别 | 处置 |
|---|---|---|
| F-01 hard link 盲区：realpath containment 对案内 hard link 指向案外文件无效（opus 探针实测放行） | P2/P3 | 威胁模型（提供案目录者需同 FS+读权限）下危害受限；上轮已知遗留，本轮确认未变；**是否加 hard link 检测由用户/融合方裁决** |
| Solana 原串存量回归面 | P2 | 交融合方清点（§6.2） |
| 案内合法 symlink 过严 | 无害 | 登记即可 |

## 9. hunk 映射

逐 hunk 映射表分散在各阶段 workorder（每份含"未映射施工 hunk：0"声明）：

- 包1：`workorder_pack1_testonly_done.md` / `workorder_pack1_fix_done.md`
- 包2：`workorder_pack2_testonly_done.md` / `workorder_pack2_fix_done.md`
- 包3：`workorder_pack3_testonly_done.md` / `workorder_pack3_fix_done.md` / `workorder_pack3_fix2_done.md` / `workorder_pack3_fix3_done.md` / `workorder_pack3_fix4_done.md`
- 消化轮：`workorder_digest1_done.md`

全工程未映射 hunk 总计：**0**。

## 10. F-01 库外同族分类矩阵（三选一处置，计划 §二.2 履约）

| 同族点 | 处置 | 结论 |
|---|---|---|
| `a5_report_seal.py:32-38` safe_file 允许 abs | 豁免候选→**融合方裁决** | abs report 是 build_html 合法调用形态（resolve 后传入），改动牵 A5 语义 |
| `shared_release_receipt.py:65-74` regular | owner=AI-2/AI-3 域→**融合方分派** | 本组仅按 F-03 需要做 canonical_target 定点破例（§3.1），containment 面未动 |
| `distribution_explanation_check.py:34` 与 `holder_distribution_scan.py:121`（逐字节重复） | **融合后合并**归 case_paths | 纯重复无语义分歧，本批不扩面 |
| `adversarial_review_runner.contained_regular` | owner=**AI-3**（其 F-05 主场文件） | 由 AI-3 评估等深或豁免 |
| `receipt_validate._regular_file/_input_file` | **正式豁免** | 独立 validator 刻意不共用 helper（独立重验纪律），盲目共用破坏双链独立性 |
| `identity_snapshot_receipt` 路径面 | **等深证明**：其路径消费经上游 identity_gate/audit gate 的案内校验链，无独立越界入口 | 无需改动 |
| `adjudication_validator.py` 全裸 join 点 | **消化轮 D3 已收口**（原矩阵外，盲审新抓） | 全部接 safe_case_file，freeze 链路不误伤 |

## 11. 融合方交接清单

1. **部署**：cp `commands-staging/token-analyze-2.md`（及同批 command 文件）到 `~/.claude/commands`，deploy-sync 转全绿（§7）。
2. **重冻 SHA 终验**：融合快照上重跑全量 suite + 六条原反例重放 + 契约 ID 双向快照对账。
3. **契约号对齐**：本组占 CT-SEMANTIC-60 / CT-BANNED-15，与 AI-2/AI-3 号段核对防撞。
4. **跨组文件对账**：`shared_release_receipt.py` 破例行区间 `:32-33`、`:257-269`、`:862-865`（canonical_target 链族归一 + evm_family import），与 AI-2/AI-3 改动合并时逐行核对。
5. **版本收口**：VERSION 6.45.0、CHANGELOG、`r10_ledger.md` 翻转 **R10-15、R10-18 → CLOSED**（本组一律未碰这些文件，防撞纪律）。
6. **Solana 存量案清点**（§6.2）：仓外 TROLL/PYTHIA/GOAT 等已交付 Solana 案核查落盘 receipt 大小写状态，裁决重跑对齐或迁移提示。
7. **裁决队列**：F-01 hard link 检测加不加（§8）；a5_report_seal abs 豁免定性（§10）。

## 12. 结论

六条 finding 全部收口（F-14 为政策替代定性），一项范围外真实生产缺陷（Solana 小写化）顺带根治，opus 两轮盲审（round 1 四裁定消化 + round 2 复验全闭合）PASS，全量 105/106（唯一红为登记在案的预期项）。分支冻结在 `72f0084` + 本报告收口 commit，交融合方。
