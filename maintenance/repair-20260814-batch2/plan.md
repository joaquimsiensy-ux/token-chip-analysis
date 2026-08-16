# 批 2 修复计划（防伪面：身份键与人工出口）——v1（已融合 @CX codex 复核）

> 状态：已完成代码探索＋@CX codex 只读复核＋意见融合。标注〔CX〕的内容来自 codex 复核采纳；〔CX-改〕为部分采纳并经 Fable 修正；不采纳项见文末融合记录。

## Context（为什么做这批）

2026-08-14 codex 对 token-chip-analysis main（7177beb / v6.40.0）的六视角全量 review 产出 12 项 finding，经 Fable 逐项对代码核实 12/12 属实——全部对应 R10 台账 15 条已知债务（零新发现，性质=独立复核确认）。用户裁定分四批修复：

- 批 1（F-03/F-01/RV-07/RV-04/F-04）：用户另开会话修，**本计划不涉及**。
- **批 2（本计划）**：F-10 waiver 硬顶落地、F-09 Solana reconcile 收据身份键＋真实案端到端（R10-10/11 同批收口）、F-02 对抗复核结构化最低要求。
- 批 3（F-08/F-11 外锚设计族）、批 4（守卫收尾）：后续另行规划。

## 用户政策定案（F-10，2026-08-14 拍板，本计划的政策事实源）

供给对账容差改为**三段分级制**：

| 偏差范围 | 处理 |
|---|---|
| ≤ 10bps（0.1%） | 自动放行（现状不变） |
| 10bps ~ 100bps（1%） | 需人工豁免单（tolerance waiver，现行机制）＋**新增：approved_tolerance_bps 与 observed_diff_bps 双双 ≤100bps 的硬顶校验** |
| > 100bps | **不拦死**：升格为"超顶特批"——必须如实向用户报告偏差原因，用户明确批准后方可放行；waiver 须携带机器可验的升级块（escalation），缺块即 FAIL |

要点：硬顶不是绝对上限而是**分级线**；>100bps 的出口存在但必须走显式特批，普通豁免单在该区间无效。签字人格式不搞实名制/双人复核（单人使用场景，用户已确认）；approved_by 固定为约定标识串。

## 三项修复方向（骨架，待探索结果细化）

### 一、F-10 落地（waiver 分级硬顶）

**不变量**：人工豁免不得成为无界出口——≤100bps 走普通豁免单；>100bps 必须携带"如实报告＋用户批准"的升级凭据；任何一侧（生产/消费）单独失守即整条失守。

代码事实（探索已核）：
- `FORMAL_TOLERANCE_BPS_MAX=10` 仅在无 waiver 路径生效（supply_truth_gate.py:383-385）；waiver 在场后该常量完全退出判断。
- waiver 校验主体：`load_tolerance_waiver`（:123-193，九个 required 字段）＋ `assert_waiver_covers_diff`（:196-207）；消费侧独立重验在 shared_release_receipt.py `_validate_tolerance_policy`（:178-281）。
- 两侧已有 `FORMAL_TOLERANCE_BPS_MAX` 同源断言测试（test_repair_batch_a.py:382），新常量沿用同模式。

修改内容：
1. 新常量 `WAIVER_TOLERANCE_BPS_CAP = 100`（供给容差豁免硬顶，生产/消费两侧同源＋同源断言测试沿用 test_repair_batch_a.py:382 模式）。
2. 〔CX〕**schema 分拆而非 v1 内加条件必填块**：`tolerance-waiver/v1` 语义收紧为只覆盖 ≤100bps 区间（approved 与 observed 双双 ≤100，超出即拒）；>100bps 走独立收据 `over-cap-approval/v1`，由 waiver 引用（path+sha256+size 三验）——与 flip-adjudications/v1 独立裁决收据同款模式，比条件字段更可审计。
3. `over-cap-approval/v1` 内容：绑定规范化 request 摘要（target 三键＋本次实际偏差＋申请容差＋replay_stats/evidence 哈希＋原因详述）的 sha256、nonce、`expires_at_utc` 时效、用户批复原文。机器验：绑定全等（防批复与本次运行脱钩/复用旧批复〔CX〕）、nonce 未重放、未过期、数值一致。流程面：Fable 必须在会话内向用户如实报告偏差原因、取得批复后才可写此收据（与 A4 用户裁决同款协议）。**如实声明边界：此设计防"工作流走捷径/误操作"，不防持有同一 macOS 用户权限的恶意进程**——硬件签名档〔CX 提议〕经评估不采纳（见融合记录）。
4. 〔CX〕**数值有限性收口（codex 抓到的现行新洞，超出原 F-10 范围但同不变量）**：`json.loads` 默认接受 `NaN/Infinity`，而 `observed_diff_bps=NaN` 使"非负检查""覆盖检查"全部静默通过＝现行代码即存在的万能通行证（Fable 已核比较逻辑，成立）。修法：waiver/approval 全部数值字段强制 `math.isfinite()`，JSON 解析层 `parse_constant` 拒绝常量；生产/消费两侧等深。
5. 〔CX〕超顶判定取 `max(申请容差, approved_tolerance_bps, observed_diff_bps, 消费侧重算实际偏差)`，防错位组合（approved 填小、observed 填大之类）。
6. 时效卫生：`user_decided_at_utc` 保留"不得晚于 now+1d"上界＋approval 收据 `expires_at_utc` 必填；〔CX〕砍掉 2026-01-01 下界与 approved_by ≥2 字符下限（纯格式卫生零安全收益，不再伪装成防线）。
7. 政策事实源落文档：`references/analyze-workflow.md:66` 供给真值闸段（全库唯一正式描述 waiver 处）更新三段分级表＋over-cap-approval 流程；CT-SEMANTIC-49 契约 needle 核对不破。

测试（挂 test_repair_batch_a.py 既有夹具族，`write_waiver(mutate=...)` 模式）：
- 红例①原反例：`approved=100000` 裸 waiver → 两侧均拒（当前照过——先红后绿）。
- 红例②：`observed_diff_bps=100000` 预先虚报无 approval 收据 → 拒。
- 〔CX〕红例③族：`NaN`／`Infinity`／`-Infinity` 注入各数值字段 → 全拒（现行代码此例为绿＝新洞先红后绿）。
- 〔CX〕红例④族：边界三点 100／100.0001／101；错位组合（approved≤100 但 observed>100、反向）。
- 红例⑤族：approval 收据 request 哈希被换／nonce 重放／已过期／远期 decided_at。
- 绿例①防误伤：≤100bps 正常 waiver（现行九字段）照常放行。
- 绿例②：>100bps 带完整 over-cap-approval 收据 → 放行（用户政策：不拦死）。
- 〔CX〕生产侧与消费侧**分别直测**每条规则（不允许"前一层先拒"造成的假覆盖）；fixture FIXTURE_DIFF_BPS=9900 落在超顶区，存量用例升级为带 approval 收据，逐条核对防假绿。

### 二、F-09（solana-reconcile 身份键＋真实案端到端）

**不变量**：正式序列链上的每份收据必须携带并被消费侧验证链上身份（chain／mint／数据窗口），跨案复制的收据必拒——身份不齐的收据不得为正式序列作保。

代码事实（探索已核）：
- 命中面窄：producer 仅 `scripts/solana/replay_edges.py:166`（cmd_reconcile）；consumer 仅 `scripts/lib/camp_series_provenance.py`（RECONCILE_SCHEMA :380、sol-rows 锚校验 :464-478、endpoint_reconcile :521-532）；登记 invariant_manifest.json:256,300；测试主场 test_repair_batch_c.py（1005 行）。
- 现收据字段仅计数/供给/快照布尔/gate_pass，零身份零 producer 零输入绑定。
- mint 在 replay_edges main 已解析（--mint／MINT／config.json），加身份键零额外取数；EVM 侧参照＝supply_truth 的 target 三键＋`replay_provenance` producer 模式。
- sidecar（camp-series-provenance/v1）自身无 chain/mint 字段，身份靠 inputs 哈希链间接传递——receipt 补身份键后消费侧才有独立锚。
- R9 纵切片测试（test_batch3_solana_vertical_slice.py）与序列链无关，升版不波及。

修改内容（schema `solana-reconcile/v2 → v3`）：
1. producer cmd_reconcile 收据新增：`chain:"solana"`、`mint`（base58 原文，**大小写敏感——不得复用 EVM 侧会 `.lower()` 的 canonicalization**〔CX〕）、窗口身份〔CX 分层设计〕：`collection_window{from_slot,to_slot}`（取自 collector meta 的采集上界）＋`edge_extrema{first,last}{slot,ts}`（内容事实）——**slot 为主身份、ts 降为辅助事实；消费侧按"extrema ⊆ collection_window ≤ snapshot slot/target cutoff"的关系校验，不得要求末边 slot 等于 cutoff**（窗口尾部可以无转账）、`producer{path,sha256}`、`inputs` 绑定（soltx meta.json＋holders_owners.json＋holders_snapshot_meta.json 三元组）。
2. 〔CX〕**边数据完整性改实测不改声称**：SQD meta 现行并不绑定 gzip 边文件哈希（replay_edges.py:99-101 只验 schema/mint/上界），"完整性由采集收据链保证"不成立——修法＝reconcile 读边重放时**顺手计算规范化逻辑边摘要**（零额外 IO，同一次遍历）写入收据（`edge_digest`＋`edge_count`），供消费侧与 PYTHIA collect_manifest 的逻辑 SHA 对锚。
3. 消费侧 `registry_anchor_check`（camp_series_provenance.py:383——计划初稿函数名有误，已按实核对更正）：新增预期身份参数；〔CX〕**两个调用点都要接**：state_from_facts.py:156（编译时）与 audit_release_gate.py:1055（发布时），预期 chain/mint 从各自持有的案 target 独立传入——否则仍是收据自证。`endpoint_reconcile` 净供给交叉保持。
4. 存量策略：**v2 收据 fail-closed 拒绝**，错误信息指导"重跑 replay_edges reconcile"——重放纯本地零采集成本，全库唯一存量真实案（PYTHIA）连 v2 收据都没有，无兼容负担；同型先例＝distribution v1→v2 重跑声明。
5. 登记同步：invariant_manifest.json 两处 v2 字符串升 v3；contract_ids 快照对账；scan-schemas.md 文档段同步。

**Solana 端到端（两层同批收）**：
- 层 a・夹具级半条（final_acceptance NOTE-1 欠账）：把 test_repair_batch_c 的 Solana 链从止于 compile_state 延到 `state_from_facts→figures→A4 finalize→A5 seal` 同案连续链（EVM 对照件＝test_repair_batch_d.py::t_fd3_e2e_single_case_evm，禁两案拼接——终验抓过一次）。
- 层 b・真实案级（R10-11）：用 PYTHIA 案（/Users/uravvv/Documents/5.6筹码分析/PYTHIA分析/，6.3G 在盘）。〔CX〕codex 实读盘面后指出四个实施级硬坑，全部采纳进方案：
  - ①**文件名/meta 版本不匹配**：现役 replay_edges 要求 `data/soltx-<sha256(mint)>.jsonl.gz`＋`sqd-solana-cache/v3` meta；PYTHIA 实际是 `soltx-<小写mint>-txaware-repaired.jsonl.gz`＋version:2 meta（缺 schema/collection_upper_slot），现役脚本进不了 reconcile。修法＝写 **legacy importer**：验证案内 `collect_manifest.json` 的既有事实（repaired 边路径／逻辑 SHA／4,857,654 行／cutoff slot 436376480／gaps 空）后产 **migration receipt**，明示"迁移件"身份，不冒充 v3 原生采集产物。
  - ②**meta 重建必须真重放**：不得拿 supply.json＋snapshot_manifest.json 包装成现行 holders_snapshot_meta.json（那是"验自洽≠验真实"同族）；盘上有 `snapshot_final/gpa_with_context.json` 原始 GPA 响应，做**无网络确定性重放**重建 meta。
  - ③**隔离输出**：reconcile/evolution 硬编码覆盖 `data/` 下五个产物文件（reconcile_receipt/replay_final_balances/camp_share_series/effective_balances/sniper_set）——不得在历史案根直接跑；在隔离 staging 案目录执行（引用式复制所需输入件），历史案零改动。
  - ④**camps 单源**：从 `analysis-state.json` 的 whale_groups（八组、聚合后无地址重复，codex 已实核）单源机械转换＋绑源 SHA；不得与 s2_entity_members.json 择优拼装。
- 若①②中 collect_manifest 事实验不过或 GPA 重放闭合不了：降级为"真实边数据＋夹具补件"并如实声明，不拿拼接冒充——**此时回报用户裁决是否重采集**（唯一保留的拍板点）。

测试：
- 红例①原反例：另案同净供给 receipt 重绑 sidecar 哈希（跨案复制）→ 拒。
- 红例②③：身份键缺失／mint 与案 target 不符／v2 旧收据 → 拒（信息含重跑指引）。
- 〔CX〕红例④族：同 mint 不同 cutoff；mint 仅改大小写；meta 与 owners 分属两个快照；producer path/sha 错；edge_digest／行数／extrema 被改。
- 〔CX〕覆盖两调用点：编译时与发布时的 `registry_anchor_check` 各自直测命中。
- 〔CX〕importer 失败分支：坏 meta／缺 raw GPA／逻辑哈希不一致 → 三条全 fail-closed。
- 绿例：v3 全链绿；test_repair_batch_c 存量夹具收据升 v3（防误伤）。

### 三、F-02（对抗复核结构化最低要求）

**不变量**：对抗复核产物必须携带机器可验的客观结构（复核了哪些结论、每条的裁决与证据），空洞文本不得满足发布闸——不判断观点对错，只验客观字段在场。

代码事实（探索已核）：
- runner（adversarial_review_runner.py）只验 exit 0＋staging 非空（:63-75），对内容零要求；`adversarial_review.json` 本体是人工手写汇总，无脚本生产。
- 深层校验在 shared_release_receipt.py `validate_sources`（:532-553，验 target 全等/runner 白名单/execution receipt），浅层在 audit_release_gate.py `check_adversarial`（:821-839，只验角色名子串＋自报 resolved）。
- **复核内容 schema 已有现成定义**（references/research-workflows.md:79-81）：`{verdict, confidence_after, evidence, alternative_explanations, corrections}`——结构化要求直接对齐它，不发明新结构。
- independent-audit-protocol.md:115-124 的六条发布否决项在代码零对应字段。
- 测试 fixture 的"合格案"entrypoint 本身就是空壳（test_audit_release_gate.py:271 写一行字符串），修复后必须同步升级，否则假红。

修改内容（schema `adversarial-review/v2 → v3`）：
1. 〔CX-改〕**权威锚＝绑 `a4_claims.json` 的 sha256，不复制 claims 全文**：聚合层必填 `claim_registry{path,sha256,schema}` 指向案内 a4_claims.json（防"id 不变、命题正文被换"的移花接木〔CX〕；防复制冗余）。codex 原提议按 profile 分绑两套 registry——经核 `a4_gate finalize --workflow-type independent-audit` 已强制 claim_registry.json↔a4_claims.json 逐项双向对账（id/规范化文本/verdict/证据/位置，independent-audit-protocol.md:18），两 profile 的执行态表统一是 a4_claims.json，F-02 只绑它即可，不重做对账。
2. 每路 claim-review artifact 从自由文本改为结构化 JSON：`{registry_sha256, role, results:[{claim_id, verdict ∈ {CONFIRMED,WEAKENED,REFUTED}, evidence(非空), alternative_explanations}]}`；artifact 内 registry_sha256/role 与 execution receipt 互绑（防撕裂〔CX〕）。
3. 〔CX〕**覆盖语义＝并集覆盖，不强求每路全覆盖**：全部 claim-review artifacts 的 claim_id **并集**必须 ⊇ registry 全集（每条结论至少被一路复核）；completeness_critic 的 artifact 放宽为全局检查件（必填 `findings` 数组＋`non_covered` 漏报声明），不机械逐条投票——对齐现行"每条关键结论一路怀疑者＋1 完整性批评"方法论（research-workflows.md §二），我原稿"每路全覆盖"与方法论冲突，改。
4. 〔CX〕**新增正式聚合生产器（范围增项）**：现状 adversarial_review.json 靠人工手拼 JSON，升 v3 后继续手拼极易错。新增 finalize 子命令（挂 adversarial_review_runner.py）：读 registry＋各 execution receipt＋artifacts＋blockers，原子产出 v3 聚合件——生产器产、消费侧验，两侧闭环。
5. 生产侧：runner `run_review` staging 落盘后加内容结构校验，不合格拒绝且**清理 staging，不残留半成品**〔CX〕。
6. 消费侧：`validate_sources` 等深重验结构＋并集覆盖＋registry sha；`check_adversarial` 同步升 v3 检查；〔CX〕三处手抄 artifact 校验抽成一个公共纯函数复用（runner/shared/audit 三面同源）。
7. `blocking_findings` 元素：`{id 非空且唯一, resolved}` 必填；`resolved=true` 时 `resolution` 说明非空。
8. 存量策略：v2 fail-closed 拒绝——符合 independent-audit-protocol.md:158 既有纪律。〔CX〕存量影响面实核修正：至少 **AKE/B2/MOG/TAG 四案** v2 在盘（AKE/B2 的 artifact 还是 Markdown，MOG/TAG 是 JSON 但非逐 claim 结构），均不可手补迁移；已交付案不重跑发布闸则无影响，将来重发布须重做对抗复核，CHANGELOG 列全四案。文档同步：independent-audit-protocol.md §复核命令段、analyze-workflow.md A4 章。

测试：
- 红例①原反例：空壳 entrypoint（2 字节 "ok"）→ runner 拒（先红后绿，动态反例存档 blind-reviews/r9/45bf8f3/round-a-sixlens.md）。
- 红例②族：verdict 非法枚举／evidence 空串或 `["", "ok"]` 型〔CX〕／claim 并集缺一条／〔CX〕artifact **多**一条 registry 外的 claim／重复 claim_id。
- 〔CX〕红例③族：registry_sha 与 execution receipt 撕裂；runner 完成后改写 a4_claims.json → 消费侧拒。
- 红例④失败分支：artifact JSON 损坏 → fail-closed 且 staging/正式位零残留〔CX〕。
- 红例⑤：blocker 空 id／重复 id／`resolved:true` 无 resolution → 拒。
- 〔CX〕红例⑥：finalize 聚合器自身的失败路径（缺 receipt／缺 artifact／registry 不在场）逐条 fail-closed。
- 绿例：fixture 升级为产出合规结构化 JSON 的 entrypoint；〔CX〕受影响夹具面比初稿大——共享 build_case 的 test_audit_release_gate.py、test_repair_batch_d.py、test_round4b_provenance.py 及触及发布闸的用例全部排查同步，全链 PASS 不回退。

## 执行编排

- 三个独立工单按 **F-10 → F-02 → F-09** 串行开批（从小到大；F-09 含真实案端到端最重殿后），每单走 maintenance-review-repair.md §三五栏模板（不变量／同族 rg 清单／三件套测试[原反例+同族变体+失败分支，先红后绿]／新建代码六视角①②自审／归因预判）。
- 施工模式沿用既定隔离调度协议：Fable 只做调度裁判（落盘工单＋git diff＋独立复跑退出码验收，不读子代理执行栈帧）；子代理施工；攻击型验收用 opus 子代理；每批独立盲审，消化循环 ≤3 轮。
- 修复批次冻结：批 2 期间不掺新功能；最终合并快照单独整体验收，不拿"每步各自过了"凑数。
- 新测试挂载：run_all.py SUITE 硬编码按批追加（既有模式）；受 invariant_scan `vertical_slice_errors` 与 `formal_capability_probes` 两处反向守卫看护。
- 版本收口：完成后 6.40.0 → 6.41.0，CHANGELOG 按活口径记账（R10 台账 15 条中本批清 R10-2/10/11/12，台账状态同步）。

## 验证（收口标准）

1. run_all 全量 suite 在最终合并快照全绿（〔CX〕基线数字以**施工冻结提交实测**为准——上轮 review 实测 95 项，codex 报告口径 98 为业务断言数，两口径并存易误引，冻结时重生成）。
2. 三项原反例全部转红：approved=100000 裸 waiver 拒／2 字节 "ok" 空壳复核拒／跨案复制 reconcile 收据拒。
3. 绿例防误伤：≤100bps 正常 waiver、合规结构化复核、v3 正常链全放行。
4. Solana 夹具级同案连续链（state→figures→A4→A5）用例入 SUITE 并绿。
5. PYTHIA 真实案端到端产物落盘（reconcile v3 receipt＋序列＋sidecar＋check_series_binding 复算记录），可独立复验。
6. 边界外一步攻击（盲审终验）：站到修复不变量的反例边界外一步再攻一轮，无新击穿。

## 风险与边界

- test_repair_batch_a 夹具 FIXTURE_DIFF_BPS=9900 落在超顶区：存量绿例须升级带 over-cap-approval 收据，逐条核对防假绿/假红。
- F-02 fixture"合格案"本身是空壳 entrypoint，受影响夹具面（build_case 共享者）比初稿大，必须与闸同步升级，否则合并即红。
- adversarial-review v2→v3 使已交付案（AKE/B2/MOG/TAG 至少四案〔CX 实核〕）旧收据不再过闸：不重跑发布闸则无影响；将来 update 重发布本就要求重做对抗复核——符合既有纪律，CHANGELOG 列全。
- PYTHIA 端到端在隔离 staging 目录跑，历史案根零改动；若 collect_manifest 事实验不过或 GPA 重放闭合不了，回报用户裁决是否重采集（唯一保留的拍板点）。
- 范围增项两处（〔CX〕复核追加，体量小但要点名）：F-02 finalize 聚合生产器（~百行级）；F-09 PYTHIA legacy importer＋migration receipt。均为"修完不是假闭合"的必要件，不属功能蔓延。

## @CX 融合记录（codex 复核采纳/不采纳清单）

codex 只读复核结论："不建议按初稿直接施工，存在 4 个会导致修完仍假闭合的缺口"。逐条处置：

**全盘采纳**：①NaN/Infinity 数值绕过（现行新洞，Fable 独立核实成立——本轮复核最大单点价值）；②waiver schema 分拆（v1 限 ≤100，超顶走独立 over-cap-approval/v1）；③超顶判定取四值 max；④F-09 函数名更正（registry_anchor_check）＋两调用点都接预期身份；⑤window 四层分层（slot 主身份，不得要求末边=cutoff）；⑥边文件逻辑摘要实测（SQD meta 不绑边哈希，原豁免理由不成立）；⑦PYTHIA 四硬坑（文件名/meta 版本、GPA 真重放、隔离输出、camps 单源）；⑧F-02 绑 registry sha 防正文替换、并集覆盖语义、finalize 聚合器、staging 清理、存量四案实核；⑨测试盲区全清单；⑩砍 approved_by 长度/2026 下界两条伪防线；⑪基线数字施工冻结时重生成。

**部分采纳（Fable 修正）**：claims 权威锚按 profile 分绑两套 registry——codex 没看到 a4_gate finalize 已做 independent-audit 的 registry↔claims 双向对账，统一绑 a4_claims.json 即可（修正后更简）。

**不采纳（含理由）**：①硬件签名/Touch ID 审批档——威胁模型不符：本工程对手是"工作流走捷径"不是"持同用户权限的恶意进程"（codex 自己也承认后者防不住），对非程序员单人工作流是过度设计；采纳其低配档（request 哈希绑定＋nonce＋时效）并如实声明边界。②"审批件放工作流无写权限位置"——macOS 单用户下不存在这种位置，形同虚设，不写进计划。

## 状态

- [x] 政策定案（用户 2026-08-14 拍板三段分级制）
- [x] 代码探索（F-10/F-02 子代理报告＋F-09 亲查）
- [x] @CX codex 复核＋Fable 逐条核实融合（本节）
- [ ] 交用户审批后开工
