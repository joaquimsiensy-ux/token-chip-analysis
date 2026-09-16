# token-chip-analysis 7.1.0 修复计划（缩减版 v2，2026-09-15）

> 状态：用户 2026-09-15 拍板范围（五项）＋施工原则（不增上下文）；codex 第二轮只读复核 22 条已全部融合（§6）；待用户审批 → 分批工单再各自 codex 复核 → codex 施工 → Fable 验收。
> 当前 skill 版本 7.0.4（main）。目标版本 **7.1.0**。
> 上一版（含全部问题定位、四批方案、codex 第一轮复核记录）已被本版替代；定位证据摘要保留在 §1，未纳入本轮的候选见附录 A。

## Context（为什么做）

最近十案（FORGGIE / EGL1 / MELANIA / FUN / KAITO / COLLECT / LIT / BTW / TAG / MOG）−3 装配段打回事件 13 次，其中 11 次的检查逻辑 −2 侧本来就能跑，只是所有拒收权都在 −3。每次打回一个新会话冷启动、且常牵动"名册冻结 → A4 封口 → 分布终态 → 报告封口"整条连锁重封，五案手工重复同一套顺序。另有压缩钩子把快照副本写错案卷（五个案卷副本里三个装的是别案内容）。

用户 09-15 讨论后的方向：**不加文字规则、不加事后计数闸**；把 −3 的检查搬到 −2 交卷前并做成一条命令；连锁重封做成一条命令；只修拍板的五项，其余候选另立。

## 施工原则（用户 09-15 追加，凌驾于下面所有条款）

**避免 skill 上下文增加：能删除的不新增，能修改的不新增。** 落实为三条硬规矩：
1. **手册净字数不增**：split-run.md、analyze-workflow.md、report-template.md 每处改动记"删 N 行／加 M 行"，三册合计 M ≤ N；SKILL.md 与 context-discipline.md 不动。规则能编码进命令的就不写进手册（例如"重封三坑"不写条文，写成 `reseal` 的行为与报错文案）。
2. **新命令名最少**：本轮**只新建一个脚本** `scripts/report/stage2_closeout.py`，子命令 `check`（默认）/`fill-workorder`/`amend`/`reseal`；−2 执行者要记的新命令只有 `stage2_closeout` 与 `stage2_closeout reseal`。其余（dryrun profile、fig2-series、downstream-check、limits-extract、reopen-cycle）全部是现有脚本的新子命令或内部函数。
3. **以替代换新增**：closeout 收据替代 §3b.3 五条人工自查与工单 `stage2_selfcheck` 的长篇申报（APU 工单该段 9 条每条数百字，−3 全读）；`fig2-series` 替代 §3b.4 现场写 Python 的整段说明；reseal 替代 B2/FUN/FORGGIE 三份手工顺序笔记在手册里的转述。

验收加一条：施工后 `wc -c` 三册手册与改前比不增；新增测试文件不计（不进上下文）。

## 0. 本轮范围（用户 09-15 拍板）与不做清单

| # | 项 | 家族 |
|---|---|---|
| 一 | 压缩钩子：留主存档、删案目录副本、回退收紧 | 钩子（③ 档全局文件） |
| 二 | 连锁重封：−2 收口命令 `stage2_closeout` ＋ 重封命令 `reseal` | 家族 1 核心 |
| 三-1 | 家族 1：−2 交卷前不跑 −3 的检查（D①–⑥） | 并入"二" |
| 三-2 | 家族 3：工单 `entity_freeze_revision` 手算、fig2 实体 ID 写展示名（D⑳） | 工单 validator |
| 三-3 | 家族 5：终态受控重开 `reopen-cycle`、快照从绑定解析（D⑬⑰） | 分布台账 |
| 三-4 | 家族 9：完整性复核脚本硬编码"局限"文案（D⑭） | 完整性路 |
| 三-5 | 家族 10：标签库补录 CCIP 池 / UniV2 Router02、订正两个 Universal Router 误标 | 标签库数据 |

**本轮不做**（见附录 A）：报告可读性 lint、上下文减负条文与计数、seal↔钱包标签制打架（1.2）、家族 2/4/6/7/8/11、−1 采集覆盖类、绑定细粒度化（连锁重封第三层）。

## 1. 定位证据摘要（详细数字在各案卷与记忆档，引用前回读）

- **打回口径**：有 −3 段 8 案中 7 案被打回；事件 13 次（LIT 3、EGL1/MELANIA/FUN/COLLECT 各 2、KAITO/FORGGIE 各 1、BTW 0）；11 次 −2 能拦，2 次是 skill 自身缺陷。"−2 收口干跑发布闸"在 COLLECT/KAITO/FUN/EGL1/FORGGIE 被提 5 次未落地。
- **连锁重封的机制（已核实源码）**：freeze 记 manifest sha/run_id/成员表哈希；a4_seal 不直接绑 freeze，靠 final scan 的 `final_bindings`（`holder_distribution_scan.py:673-696`）与 rounds entry 的 `entity_freeze_revision`/`a4_seal_sha`（`:1138-1146`）耦合；a5 绑报告 sha＋a4 seal＋rounds terminal。**只改措辞不触发连锁**（MELANIA v3 实证），动名册/裁决才触发。
- **手工重封的三个坑（源码级）**：①`a4_gate register` 无条件重写 `a4_claims.json` 且带时间戳（`a4_gate.py:325-329`），claims 未变重跑 register 也会让对抗复核链的 registry sha 失效（`adversarial_review_runner.py:673`、`shared_release_receipt.py:1605-1613`）；②`freeze` 的 `--pending/--casebook-note` 不传即清空并平白新增 revision（`handoff_manifest.py:1581-1593`）；③`a4_gate finalize` 要求 `charts/final` 为空（`:415-429`），而 record-round 终态时已把分布图放进去（`holder_distribution_scan.py:1148-1155`），顺序错一次就全废。手册两册均未写这三点。
- **终态后无重开入口**：terminal 后 scan 抛"禁止再生成 final scan"（`:893-894`）、record 报 BLOCK（`:1096-1098`）；FORGGIE 实测"截回轮 1"必败，只能整周期归档重开（`casebook_gate_log.md:221-226`）；EGL1 重开三次。
- **快照误命中**：`find_snapshot` 按固定顺序找文件不查 data_map 登记（`:187-197`），案内未登记副本永远先命中；权威记录在 initial 扫描 `input_binding.snapshot{path,sha256}`（`:646`）。FUN/FORGGIE/APU 三案踩。
- **完整性脚本**：`review_completeness.py` 不在 skill，是逐案手写脚本（FORGGIE 版 702 行），LIM-01～19、NC-01～12 文案硬编码（`:639-668`），取节靠正则锚死 `## 10 `（`:492`），findings 改标题即崩、改措辞即静默失配。
- **标签库误标（ETH）**：`0x0577eccc…5a55` 漏收（实为 Chainlink CCIP LockReleaseTokenPool，APU 案被当实体）；`0x7a250d56…488d` **误标**为 Flashbots User（实为 Uniswap V2 Router02，codex 核出）；`0x3fc91a3a…7fad`、`0x66a9893c…8af` 被外部源标 sandwich-bot（实为 Uniswap Universal Router，APU findings 因此误写"MEV 操作者"）。APU 只做了案内补录（`data/labels_final_v3.jsonl`），全局库未补。
- **压缩钩子**：`~/.claude/hooks/compact_state.py` 按路径频次猜案目录写副本（`guess_case_dirs` :103-114，`do_save` :178-184）；恢复注入只读主存档（`do_inject` :187-210）从不读副本。副本来源核查：EGL1 案根 42 段中 35 段来自 FORGGIE 会话；MELANIA 副本来自 TROLL 会话。

## 2. 修复方案

### 2.1 压缩钩子（③ 档：全局文件，改前备份 `compact_state.py.bak_<时间戳>`，需用户批准）

- 删除 `do_save` 里案目录副本段（`:176-184`）与 `guess_case_dirs` 及快照文本里"推断的活跃案目录"段（`:126-127`）。
- `do_inject` 回退逻辑（`:194-202`"十分钟内最新文件"）改为：找不到本会话主存档就不注入。
- 已污染的五个副本文件（EGL1 案根与 data、FORGGIE、MELANIA、PYTHIA 各一）属删文件，**本计划只列不删**，单独请示。
- 验证（codex 指出 `COMPACT_STATE_NO_COPY` 在旧代码里本就阻止副本，用它演练形不成改前红改后绿）：不设该变量、用一份含多案路径的模拟 transcript 跑 save，改前案目录出现副本、改后不出现；另验"本会话存档缺失而另一会话十分钟内有存档时不注入"。

### 2.2 −2 收口命令 `scripts/report/stage2_closeout.py`（家族 1；D①②③④⑤⑥）

设计原则：**检查逻辑共用一份，−2 与 −3 只是调用时机不同**；不新增可独立声称权威的 PASS 文件；成功状态措辞"可进入装配"并列出待 −3 执行项。

| 子检查 | 复用（函数级调用，不落 −3 产物） | 拦的打回 |
|---|---|---|
| 发布闸干跑 | `audit_release_gate._run(..., profile="stage2-dryrun")`：新增 profile＝SHARED_REQUIRED＋distribution_scan/rounds，豁免 a5_report_seal / fig1_legend_receipt / figure2_check_receipt；把 `_run` 两处 `profile == "new-analysis"`（`:1606`、`:1616`）改成 `profile in (...)`，其中 figure2 收据、fig1 legend、A5 seal 重验三段保持仅 new-analysis | FORGGIE dormant、EGL1#2 三账/收据链、COLLECT/FUN 机器件层 |
| seal 可前移子项 | `a5_report_seal.provenance_flip_bundle(root, report_text, a4obj)`＋`distribution_bundle(root, report, a4obj)`（`:263` 起，含 final 重验链、三句式、终态图唯一引用） | MELANIA#2 |
| 图 2 对账 | 新增 `figures_from_facts.py fig2-series --entity-series --keys --out whale_series.json`（确定性装配，写 sha）；`check` 现在**会写** `figure2_check_receipt.json`（`:256-278`，codex 指出），须把纯校验逻辑拆成函数供 closeout 调用而不落收据；−3 只消费同一文件、核 sha 不再现场装配（split-run §3b.4 第 177 行改） | COLLECT#2 |
| A4 封口实物重验 | **codex 补的漏项**：把 build_html G9 的非图片部分（`build_html.py:366` 起：sealed_files/registry/verdicts 全部实物 sha 重验）提成共用函数，closeout 与 build_html 同调；否则只改 findings.md 能过前移检查却在 −3 被 G9 拒 | 所有"改了封印内文件"的返修 |
| 身份闸 | `entity_identity_gate.validate_gate(gate, state, require_resolved=True)` | LIT#2、KAITO |
| 图注同源 | 从 rounds terminal 的 final scan 读五桶数字，按**报告固定格式**（百分比两位小数，极小值按现行图注写法）渲染后再比对，不拿 JSON 浮点原串逐字比（BTW 图注 `24.02%`/`0.0001%` 是合法写法，codex 指出） | MELANIA#2 |
| 双口径句 | 不按 metric 名含 strict/expanded 判断（BTW 的可证下限叫 `m_econ_confirmed`）；改为 facts 里显式声明 `dual_basis:{lower:<宏名>, upper:<宏名>}`，报告须同时含两宏 | EGL1 |
| A4 下游过期清单 | 新增 `a4_gate.py downstream-check`（只读）：`adversarial_review.claim_registry.sha256` vs 当前 `a4_claims.json`；`shared_release_receipt.inputs["adversarial_review.json"].sha256` vs 实物；rounds terminal `a4_seal_sha` vs 当前 `a4_seal.json`；final scan `entity_freeze_revision` vs `len(revisions)+1`；dormant `universe_ref` vs wave_scan 实物。输出过期清单＋修复顺序，不自动补 | LIT#3、EGL1#2 |
| 工单 | 2.4 的工单校验（同脚本内函数） | COLLECT#1/#2、KAITO、MELANIA |

**设计代理核细的实现要点**（已按源码核对）：`_run` 第 1616 行大块改成 `profile in {...}` 后，内部 figure2 收据（:1618）、fig1 legend（:1636）、A5 seal 重验（:1648）三段各加 `if profile == "new-analysis"` 围栏，series binding（:1634）保留；`:1558` 的"缺 --report"判定对 stage2-dryrun 同样 fail-closed。`distribution_bundle` 对 independent-audit 返回 NOT_APPLICABLE，closeout 须显式当失败。`fig2-series` 子命令：`--entity-series data/entity_series.json --keys <逗号键> --labels-from facts.json --out whale_series.json`，label 取 `facts.entities[eid].label`，同时写 `whale_series.provenance.json{source_sha,keys,out_sha}`。选材下限集合的判定字段见 2.4（用 A4 封口后最终 `label`，不用 `whale_groups.type`）。

**收据 `stage2_closeout_receipt.json`**（schema `stage2-closeout/v1`，字段：verdict、report_md{path,sha}、workorder_effective_sha、facts/state sha、freeze_revision、a4_seal_sha、rounds{sha,terminal_round_n,status}、whale_series_sha、skill_commit、checks[{name,status,detail}]、pending_for_stage3[]）：不进发布闸必需资产。绑定范围固定：报告.md sha、工单有效内容 sha（剔除 `stage2_selfcheck` 后规范化）、facts/state sha、entity_freeze revision、a4_seal sha、rounds terminal、skill commit。−3 前置自检 §3b.1 加第六项：收据在场、verdict=PASS、绑定重验一致，否则退回 −2。**amendments 规则**（codex 指出：合法修正会同时改正文 sha 与工单有效 sha，若不定义更新规则，−3 获准修正后下次恢复又被退回）：−3 每写一条 amendment 后运行 `stage2_closeout --amend`，只重跑受影响子检查（宏、图注同源、句式、G9 非图片部分），收据追加 `amendment_chain[]`（before/after sha），前置自检按最后一条 after_sha 校验。

### 2.3 重封命令 `stage2_closeout.py reseal`（家族 1；固化 B2/FUN/FORGGIE 手工顺序；与 2.2 同一文件，不另建脚本）

- 入口：`--from freeze | a4 | rounds`，`--dry-run` 先列出将失效的下游件与将执行的步骤。
- 固定顺序（以 `--from freeze` 为全序，其余从对应层起；**归档动作统一由 reseal 安排**，reopen-cycle 只做台账层，避免两处搬同一张终态图——codex 指出的冲突）：
  0. 预检并 `--dry-run` 列全停点与将失效件；`charts/final/` 与 `distribution_adjudications.json` 的归档在此统一执行（`mv` 到 `data/stage2/_history/<utc>/`，禁 rm），并在回执里写明裁决文件失效原因与"终态后重新承接"的位置（不是取消校验）
  1. freeze：从当前 `entity_freeze.json` 顶层回读 `members_source`、`entity_file`、`pending_items`（`;` 拼接）、`casebook_note` 原样回传；**回传只是必要条件**，freeze 四道前置（READY manifest 深验、候选裁决闭合、在场分布裁决校验、provenance 成员一致性与真实重放，`handoff_manifest.py:1432-1560`）任一不过即停，算法内容哈希也须一致
  2. A4：若台账已有 terminal，走 2.5 的条件分支（**先归档旧周期**，再决定 finalize 时机——`a4_gate finalize` 见 terminal 直接拒，`a4_gate.py:282`）；register 跳过条件见下；变了则停下提示"按 runner 记录的**实际路数**重跑受影响复核 → runner finalize → shared_release_receipt"（不能固定写"两路"，runner 不允许漏传有效 receipt，`adversarial_review_runner.py:652`）
  3. rounds：final scan `--round N`，`--snapshot` 从 initial 扫描 `input_binding.snapshot.path` 解析并核 sha
  4. record-round 前的机械步骤：用**已有裁决内容**重新生成 explanation receipt（旧解释绑旧 scan 与旧 A4，不能复用，`distribution_explanation_check.py:147`）；WAIVED 同理须重新绑定当前 scan/seal/台账，不机械继承
  5. record-round：REQUIRES_A4_REFLOW 即停；UNEXPLAINED 须区分"未带解释（非终态锚）"与"解释检查失败"（同名状态，按 `explanation_path` 与检查结果区分，`holder_distribution_scan.py:1113-1136`），后者才停；NORMAL/LOW_SAMPLE/EXPLAINED 终态后物化分布图
  6. 停：三图、A5 seal、HTML 归 −3；reseal 末尾自动跑 `stage2_closeout check`
- 停点用 exit 3 并列原因：A4 verdict 与上版有差异、final scan 出现 `new_clusters`、解释检查失败。`--dry-run` 输出表"层｜动作｜将失效下游件"（a4 层：adversarial_review/shared_release_receipt/rounds 全部行/a5 seal；freeze 层再加 final scan；注意 shared receipt 的直接输入不含 a4 seal，`shared_release_receipt.py:50`，失效判断按 registry sha 而非 seal revision）。
- **跳过 register 的条件（codex 修正）**：同时满足①待登记 claims 经同一规范化函数（剔除 `registered_at_utc`）后与当前 `a4_claims.json` 相同；②当前 `a4_claims.json` 的**原始文件 sha** 仍与 `adversarial_review.claim_registry.sha256` 一致。比较基准就是当前磁盘 registry，不依赖历史 sha。且 claims 文本不变≠引用证据未变：reseal 只保证不破坏复核链，"受影响复核路是否要重跑"由 A4 判断执行者按 downstream-check 清单决定（FORGGIE 即在不 register 情况下重跑了受影响路）。rounds 层必须排在 a4 层之后。
- reseal **不自动补裁决、不自动写解释、不重跑对抗复核、不重画图**，只做机械顺序与停点。
- 硬约束：必须在与 freeze 记录同一 checkout 下运行（算法文件 realpath 校验，`handoff_manifest.py:806-829`）。

### 2.4 工单校验与机械字段生成（家族 3；D⑳）——并入 `stage2_closeout.py --fill-workorder / 默认 check`，不另建脚本

- `--fill-workorder`：机械字段由脚本填——`bindings` 各 sha、`entity_freeze_revision=len(revisions)+1`、`report_image_refs`（复用 `a5_report_seal.IMG_RE` 重取）、`meta.skill_version`/`skill_commit`；**只限 −2 新一轮收口，不覆盖已存在的原稿锚 `bindings.report_md`**（codex 指出）；选材字段仍 −2 亲笔，缺则留 null 并列出。
- check：§3b.2 字段完备；机械字段重算等值；`fig2.lines[].entity_id ∈ facts.entities` 键。**必画集合改用 A4 已封口的最终标签判断**，不用 `whale_groups.type`（codex 以 BTW 实证反驳：BTW 项目方的 `label` 是项目方、`type` 是"类型②·多地址明牌"，按 type 公式必画集合为空集；`CAMP_ORDER_MODERN` 是阵营序列白名单不是实体 type 枚举）：`required`＝facts/state 同源 `label` 归入 {项目方, 大庄, 小庄, 离场庄} 的实体，标签解析不了的报定位错误而不是放行；合并线用 `merge_groups[].member_entity_ids` 表示覆盖；`required` 是**下限**，允许已声明的额外选材；`flow` 同理按现行门槛条文导出下限集合，允许"未达门槛但承载关键结论"的图（report-template.md:178 现行允许），不做"门槛集合＝所有图"的误拒；工单字段兼容 BTW 现存 `flow.items` 与新 `flow.charts`（机械迁移或双认）；每条 `series_source.sha256` 与实物一致且 key 存在；路径围栏。失败文案统一 `WORKORDER BLOCK: <字段路径>: <期望> != <实际>`。
- 手册：§3b.2 把"entity_freeze_revision 手填"改为"由 closeout 填"（改一行不加行）；§3b.5 残余风险段删"工单字段完备性"一句。

### 2.5 终态受控重开 `holder_distribution_scan.py --mode reopen-cycle` 与快照解析（家族 5；D⑬⑰）

- `reopen-cycle --case-dir --reason "<文>" [--dry-run]`：把当前 `distribution_rounds.json`、各轮 `dist_rounds/round_k/`、`charts/final/holder_distribution_current.png` 整体 `shutil.move` 到 `data/stage2/dist_cycle<N>/`（N＝已有 dist_cycle 数＋1），写回执 `reopen_receipt.json{cycle,reason,archived[{from,to,sha}],prior_terminal,prior_a4_seal_sha,new_a4_seal_sha,ts}`；**不新建台账**（record-round 在无台账时自建且要求 round 1），不改旧台账以保哈希链与首轮 snapshot_sha 约束；新周期首轮 final scan 的 `input_binding` 加 `reopened_from_cycle`。拒绝条件：台账无 terminal；`charts/final` 有其他文件；目标 `dist_cycle<N>` 已存在。**不设"a4 revision 须已提高"前置**（上一稿此条与 `a4_gate finalize` 见 terminal 即拒互为死锁，codex 指出并经 FORGGIE 案簿 `:221` 核实：实际成功顺序是先归档旧周期→在旧 rev2 下建新周期轮 1→重跑受影响复核→封 rev3→轮 2 终态；"截回轮 1"失败的根因是轮 1 绑 rev1 而磁盘已是 rev2）。归档范围含被引用的解释文件、waiver、证据文件，防止旧台账路径指向新周期同名文件。输出失效下游件清单（a5 seal、工单 bindings.rounds/终态图）。
- 重开后的条件分支（写进手册与 reseal）：若现有 claims 能与 initial scan 闭合 → 可先 finalize 再生成新轮 1；若需要 final scan 作 claim source → 先在当前 seal 下建立轮 1 非终态锚（状态按源码可能是 NORMAL/LOW_SAMPLE 直接终态，或不带解释的 UNEXPLAINED；**不是一律 UNEXPLAINED**），完成受影响证据与复核后 finalize，再生成下一轮。
- 新增 `input_binding.reopened_from_cycle` 必须同步改 validator 的独立重算路径（`holder_distribution_scan.py:1045` 现只补回 `round_binding` 等既有字段），从经验证的 reopen 回执重建该字段，不复制自报值也不忽略。
- `find_snapshot` 改为：显式 `--snapshot` 最优先但**仍须过 data_map 校验**；final 自动选 initial 已绑定的快照并核 sha，绑定损坏即停不换文件；无绑定时取 data_map 中**唯一符合快照用途**的登记项；固定顺序自动发现仅作回退且必须命中登记，否则报"快照未在 data_map 唯一登记"（不写"请显式指定"，显式指定也绕不过登记）。现有最小夹具登记了 `data/holders_owners.json`（`test_distribution_gate.py:30`），不受影响；新增正例"存在未登记优先副本时仍选中已登记权威快照"。

### 2.6 完整性路"局限"条目从 findings 提取（家族 9；D⑭）——做成 `a4_gate.py limits-extract` 子命令，不新建脚本

- `a4_gate.py limits-extract --findings findings.md --out limits.json [--heading <正则>]`：抽取"局限/观测边界"节的编号条目为 `[{id, text}]`，处理续行、标题多匹配、无匹配、空提取四种情况均报错，输出绑定 findings sha（防消费旧文件）。
- 范围限定（codex 修正）：只共用**已有局限条目的原文来源**（LIM-xx）；"应加未加"（NC-xx）与复核评价按定义不能从 findings 提取，仍由案内复核脚本产生。条目重排后 blocker 定位关系须重做（`adversarial_review_runner.py:402`）。
- 手册：analyze-workflow A4 完整性路现有那句"覆盖面对账"后改写为"局限条目取 limits-extract 输出，禁硬编码"（改句不加句）。仓库无通用 completeness 脚本模板，工单注明示例消费者放 `scripts/tests/` 用例里，不进手册。

### 2.7 标签库补录（家族 10；数据改动，不改代码）

- 源文件 `curation_overrides_20260915_apu.csv`（source=`curation`，四行 ETH）先放在正式 additions 目录**之外**的 staging 位置，交 `scripts/labels/add_labels.py` 走三闸＋staging 事务后由它归档进 `scripts/labels/sources/additions/`（codex 更正：目录是 scripts 下不是 references 下，`add_labels.py:29-41`；直接预置进 additions 会跳过源文件 staging）：
  - `0x0577eccc8fbe54b321d3bc8d4f1d09deb94d5a55` Chainlink CCIP LockReleaseTokenPool，category=bridge，exclude/no_merge/exclude
  - `0x7a250d5630b4cf539739df2c5dacb4c659f2488d` Uniswap V2 Router02，router，exclude/no_merge/exclude（**订正而非补录**：当前库标成 `Flashbots User`/identity，`labels-eth.csv:115182`，codex 指出）
  - `0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad`、`0x66a9893cc07d91d95644aedd05d03f95e1dba8af` Uniswap Universal Router，category=router，**exclude/no_merge/exclude**（不照抄 APU 案内的 identity/allow/count：`validate_labels.py:126` 明确拒绝设施类目配 tier=identity，全量重建也会改成 exclude；不改校验器放行）
- evidence 列写能从全局库定位到的权威出处（Sourcify 合约名＋APU 案卷路径），不只写案内相对路径。
- 入库后**重建 `sources/out` 再跑 `roundtrip_check`**（add_labels 三闸本身不刷新重建结果，MAINTENANCE.md:50），`tests/labels_manifest.py --write`；验证 `label_lookup` 四址命中、`benchmark_labels` PASS。
- 注意：标签 manifest 变化会让钉版案（BTW 钉 6.50.0）绑定漂移，见 §4 第 1 条。

### 2.8 手册文本修订（按施工原则：只替换，净字数不增；坑写进命令报错文案不写进手册）

| 位置 | 删 | 改/加 | 净值 |
|---|---|---|---|
| split-run §3.2 第 136 行判断主序 | 删 "A4 register/finalize … 新簇回流 A4 … 唯一终态物化" 的手工顺序描述 | 改为 "A4 封口与分布终态一律 `reseal`（重封）/`stage2_closeout`（收口）" 一句 | 减 |
| split-run §3b.3 第 170 行五条自查 | 删五条 | 改为 "跑 `stage2_closeout` PASS；sealed 申报改为'冻结前未读；冻结后何时、为何读取'" | 减 |
| split-run §3b.1 第 150 行前置五项 | — | 第⑤项后并写 "⑥closeout 收据绑定一致" | 持平（同一行内） |
| split-run §3b.2 第 158 行 bindings | 删 "entity_freeze_revision 手填" 说明 | 改 "由 closeout --fill-workorder 生成" | 持平 |
| split-run §3b.4 第 176–177 行图 2/3 现场 Python 说明 | 删两行 | 改为 "图 2 序列消费 −2 产的 whale_series.json（核 sha）" 一行 | 减 |
| split-run §3b.5 第 184 行残余风险 | 删 "工单字段完备性…不设 validator" 分句 | — | 减 |
| analyze-workflow A4.5 第 185 行 | 删 "删除台账后从非首轮继续…都会被拒绝" 分句 | 改 "终态后重开用 `reopen-cycle`" | 持平 |
| analyze-workflow A4 完整性路 | — | 现有句改写加 "局限条目取 limits-extract" | 持平 |

- 重封三坑（register 时间戳、freeze 参数回读、charts/final 归档）、周期 2 条件分支、快照登记要求：**全部编码进 reseal/reopen-cycle 的行为与报错文案**，不写条文。
- CHANGELOG 7.1.0 一条；`docs_lint`、`changelog_lint`、`test_version_consistency` 过；三册 `wc -c` 不增。

## 3. 施工组织

| 批 | 内容 | 前置 |
|---|---|---|
| W0 | 2.1 钩子（Fable 亲改，③ 档，用户批准后备份再改） | 用户批准 |
| W1 | 2.5 reopen-cycle＋find_snapshot；2.6 `a4_gate limits-extract`；2.7 标签库 | 互不依赖，可并行派 codex |
| W2 | 2.2＋2.4 `stage2_closeout`（含 stage2-dryrun profile、fig2-series、downstream-check、G9 共用函数、fill-workorder、--amend） | W1 |
| W3 | 2.3 `stage2_closeout reseal` 子命令；2.8 手册（含 `wc -c` 不增验收）；CHANGELOG/VERSION 7.1.0 | W1、W2 |

每批：Fable 写工单（白名单文件、行号、先红后绿、完成标准、不 commit）→ codex 只读复核工单 → codex `task --write --fresh` 施工 → Fable 验收（diff 对照工单、run_all、原案回测）→ commit＋push。盲审默认 codex 常规盲审。

## 4. 验证

1. **原案回测（改前红、改后绿，并注明是修输入还是修规则变绿）**：FORGGIE dormant 绑错 → closeout FAIL；EGL1#1 flow spec 旧稿/#2 runner 链缺 → dryrun FAIL；MELANIA 图注不同源 → 五桶检查 FAIL；COLLECT off-by-one、fig2 展示名 → check FAIL；LIT resolution 空 → validate_gate FAIL；**"只改 findings.md 后 closeout 必拒"**（证明 G9 拒收权真前移）。**防误伤分两层（codex 修正）**：BTW 钉在 6.50.0，标签 manifest 与扫描器一改其绑定必漂移（`holder_distribution_scan.py:644/1051`），所以"BTW 原件在 7.1.0 跑发布闸仍 PASS"不是成立的前提；改为①BTW 原钉版基线不动、只用其 facts/state/工单结构跑 closeout 的**纯规则部分**（fig2 必画集合、flow 下限、图注格式）必须 PASS；②另取一份完成声明迁移的案（APU 0914，7.0.4 产）跑完整 closeout 必须 PASS。
1b. **codex 建议的五组施工前验收**：终态重开到再封口的完整路径；canonical claims 相同但原始 registry sha 漂移时 register 不被跳过；BTW 实际 label/type 与选材结构；`reopened_from_cycle` 独立重验；curation 入库后重建结果与 roundtrip 一致。
2. **负例与正例用例**（tempdir 最小案卷，夹具参照 `test_distribution_gate.py:89` 的 state 结构；全部登记进 `run_all.py` SUITE）：`test_stage2_closeout.py`（stale_claims_sha：改 registered_at 后 downstream-check 报过期；dryrun_profile_exempts_a5：缺三件 −3 产物仍 PASS；旧收据配新正文被拒）；`test_stage2_reseal.py`（skip_register_when_claims_same：canonical 相同且 registry sha 一致时仅 finalize、revision+1；registry_sha_drift_forces_register：canonical 相同但原始 sha 漂移时不跳过；freeze_readback_no_new_revision：回读 pending 后 revisions 长度不变）；`test_reopen_cycle.py`（archives_and_allows_round1：归档后 record-round 轮 1 成功；rejects_when_no_terminal；未登记副本快照被拒；reopened_from_cycle 由 validator 独立重建）；工单校验用例并入 `test_stage2_closeout.py`（fig2_required_from_label：BTW 结构下 required 非空且被 lines 覆盖；空 lines 被拒；flow 下限允许额外图；`flow.items` 兼容）；LOW_SAMPLE/WAIVED 合法终态不误拦；amend 后前置自检按 after_sha 通过。
3. **回归**：`scripts/tests/run_all.py` 全 PASS（新用例登记进 SUITE）；FORGGIE 已发布案复跑 `audit_release_gate --profile new-analysis` 仍 PASS。
4. **标签库**：四址 `label_lookup` 命中；`roundtrip_check`、`benchmark_labels`、`labels_manifest` PASS。
5. **下一案指标**：−3 前置自检一次通过、真打回 0；重封链一次跑通不手工排序。

## 5. 需用户拍板

1. 2.1 钩子改动（③ 档，改前备份）；五个污染副本的删除另单请示，本计划不删。
2. `reseal` 在 A4 claims 变化时直接停、由执行者按 downstream-check 清单决定重跑哪些路（推荐停，不自动重跑对抗复核）。
3. 标签库四条：两个 Universal Router **不照抄** APU 案内的 identity/allow/count，改用 exclude/no_merge/exclude（校验器硬拒设施类目配 identity，改校验器放行属加规则，违反施工原则）；Router02 按误标订正。推荐照此。
4. 新脚本只留一个 `stage2_closeout.py`（check/fill-workorder/amend/reseal 四子命令），limits-extract 挂 `a4_gate.py`、reopen-cycle 挂 `holder_distribution_scan.py`。推荐照此。

## 6. codex 复核记录（@CX，第二轮，2026-09-15；原文 `scratchpad/cx_reply2.txt`，基准 main 764b60cd / 7.0.4）

codex 总评："不建议按这版直接施工"，方向（缩范围、共用检查、claims 变化即停）合理，但有三处确定性错误：重封死锁、标签入库必败、BTW 误伤。逐条处置（引用的源码位置我方抽查了 `a4_gate.py:282`、`validate_labels.py:126`、`labels-eth.csv` Router02 行、additions 目录位置，全部属实）：

| # | codex 意见 | 处置 |
|---|---|---|
| 1a | dryrun 分支改法正确，但 A5 段判断看磁盘文件在不在，须整段围栏；`:1558` 缺报告判断也要改；建议调公开 `run()` 保留深验缓存 | 采纳，写进 2.2 |
| 1b | closeout 漏 G9 对 A4 封口实物（sealed_files/registry/verdicts）的重验，只改 findings 能过前移检查却在 −3 被拒；应提共用函数 | 采纳，2.2 新增一行 |
| 1c | `figures_from_facts check` 会写收据，与"不落 −3 产物"矛盾 | 采纳，拆纯校验函数 |
| 2 | "先封新 A4 再重开"与 `finalize` 见 terminal 即拒互为死锁；FORGGIE 实际顺序是先归档→旧 rev 下建轮 1→复核→封新 rev→轮 2 | 采纳，2.5 删该前置，改条件分支；设计代理这条被推翻 |
| 3a | 周期 2 轮 1 不是一律 UNEXPLAINED；"未带解释"与"解释失败"同名，"上轮 UNEXPLAINED 即停"会卡住自己的非终态锚 | 采纳，2.3 第 5 步区分 |
| 3b | reseal 缺"用已有裁决重生成 explanation receipt"步骤；WAIVED 不能机械继承 | 采纳，2.3 第 4 步 |
| 3c | freeze 回读还须 members_source/entity_file；四道前置任一不过即停；算法内容哈希须一致；回传≠no-op | 采纳，2.3 第 1 步 |
| 3d | charts/final 归档与 reopen 搬同一张图冲突；adjudications"在场就移走"等于取消校验 | 采纳，归档统一由 reseal 第 0 步安排并写失效原因与承接位置 |
| 4a | 跳过 register 须同时满足 canonical 相同＋当前 registry 原始 sha 与复核链一致；比较基准要说清 | 采纳，2.3 |
| 4b | claims 不变≠引用证据未变；A4 revision 增加不自动使 shared receipt 失效（其输入不含 seal）；停下提示不能固定"两路" | 采纳，2.3 |
| 5a | 无台账自建路径成立；`reopened_from_cycle` 须同步 validator 独立重算；归档要含解释/waiver/证据 | 采纳，2.5 |
| 5b | find_snapshot：显式指定仍须过登记；"唯一登记"指唯一符合用途；提示文案改；现有夹具不受影响 | 采纳，2.5 |
| 6 | `whale_groups.type` 不可靠，BTW 按此公式必画集合为空；应用 A4 封口后的最终标签；补离场庄、合并线 member_entity_ids、下限语义、flow 允许关键结论图、兼容 `flow.items` | 采纳，2.4 整段重写；设计代理这条被推翻 |
| 7 | limits 只限已有 LIM 条目，NC"应加未加"不能提取；提取器四种边界＋绑 findings sha；blocker 定位重做；MAINTENANCE.md 不是此项门禁 | 采纳，2.6 |
| 8 | Universal Router 用 router+identity 会被 validate_labels 拒；目录是 scripts/labels/sources/additions；须先 staging 再归档；入库后重建再 roundtrip；Router02 是误标非漏收 | 采纳，2.7 整段改 |
| 9a | BTW 钉 6.50.0，标签与扫描器一改必漂移，"原件跑新闸仍 PASS"不成立 | 采纳，§4 第 1 条改两层 |
| 9b | 五桶逐字含须先定精度格式；双口径不能靠宏名含 strict/expanded | 采纳，2.2 表两行改 |
| 9c | `--fill` 不得覆盖原稿锚；amendments 后收据更新规则缺失 | 采纳，2.2/2.4 |
| 10 | `COMPACT_STATE_NO_COPY` 演练形不成改前红改后绿 | 采纳，2.1 验证改 |
| — | 施工前五组验收＋"仅改 findings 后 closeout 必拒" | 采纳，§4 1/1b |

**我方不采纳**：无。codex 未涉及、我方新增的：施工原则段（用户 09-15 追加）及据此把 workorder_check、findings_limits 并入现有脚本、手册改为净减。

**结论**：第二轮意见全部融合后，本计划才具备派工条件。

## 附录 A　本轮不做的候选（保留供下轮）

- 可读性 lint 与三策略披露表模板（原批 2）；seal 逼正文写全址与钱包标签制打架（原 1.2）。
- 上下文减负：阅读清单、断点换会话、A4 summary、多版本落 `_history/`（原批 3）；计数闸已作废。
- 家族 2（facts 键名严格化、strict-text-numbers）、家族 4（收据绝对路径存量）、家族 6（底稿冻结）、家族 7（台账生产指引、a4_gate 样例、price_check schema）、家族 8（G8 标签冲突、bot 军批量 resolution）、家族 11（键名统一）。
- −1 采集覆盖类（D㉓–㉚、APU 的合约名核/事件粒度/静置仓硬边/camp_series 跳日）另立工程。
- 连锁重封第三层"绑定细粒度化"留 7.2。
- 已修勿重提：TAG 三闸死环第一刀、LIT F-007/F-008、FUN MACRO_RE 连字符、B2 分母键、链名别名归一。

---
---

# 第二部分（另一会话，2026-09-15）：三项修复计划——seal↔零地址打架 / 高频机械活稳定命令 / 备份堆积与台账瘦身

> 本部分由另一会话追加，独立副本在 `/Users/uravvv/.claude/plans/tca-three-items-20260915.md`（以副本为准，本处为审批用镜像）。与上面五项并行，重叠点见本部分 §4。
> 状态：codex 只读复核（@CX）已完成并逐条融合（§6），待用户审批。
> 修复原则（用户 09-15）：**不增加 skill 上下文；能删的不新增，能改的不新增。**

## Context

用户从上一版大计划里点了三项本会话就修：①封口检查（a5_report_seal）逼报告正文写 40 位全址，与报告模板"正文零地址"打架；②−2 主线手写内联 python 太多（事后计数没用），把高频机械活做成稳定命令；③案根多版本备份堆积、裁决台账大字段过大。

## 1. 定位（三路只读调研实测）

**1.1 打架真相**：打架点在 `report-template.md` 内部（:53/265/284 零地址 ↔ :222 要求写"终点标识"且示例是缩址）；`a5_report_seal.py:253` 逐字要 `terminal[2]` 全址。**终点几乎从不属于 `facts.entities`**（是池子/CEX/聚合器/发射合约），钱包标签制套不上、附录 B 也查不到。FORGGIE/EGL1 在正文写全址表并自辩；APU 挪进附录 C 自称"附录允许"（模板无依据）。溯源台账 `input_binding.labels_file` 已三验绑定一份标签文件（每终点有 name），链 freeze→a4→a5 已封口。

**1.2 内联 python**：五个 −2 会话主线 2,739 条 Bash 里 1,411 条手写脚本（52%，200 万字符）。形态：schema 探测 495（纯探测 338）、按地址清单跨文件查字段 335、聚合 318、跨文件核对 211、duckdb 查 parquet 189、文本替换 163；另 339 次 `cut/head` 截断回显。**已有命令没人用**：`facts_gate --facts --state --md`、`adjudication_validator template/validate`、`figures_from_facts check`。**确实没有**：JSON 键树探测、地址批量查字段、只读 SQL、台账按 id 打补丁、claim dump/patch。

**1.3 备份堆积**：skill 里**没有任何脚本产 `.bak_*`**（只有 manifest superseded / a4_seals revision / 收据 superseded 三类归档）。案根 FORGGIE 12 件 2 MB、EGL1 3 件 3 MB、**APU 0914 63 件 32 MB**，全是主线 Claude 手工 cp（命名 skill 零命中）。`handoff_manifest.py:119` `EXCLUDE_SUFFIXES` 用 `endswith(".bak")` 对这些名字不匹配（防线失效，没出事只因收录是白名单无 glob）；无任何"案根不得有额外文件"断言。

**1.4 台账大字段**：`_members_total` ≡ accepted∪excluded 纯冗余，validator 从不读（`scan-schemas.md:207` 已说可删），四案占 18–33%；EGL1 `distribution_adjudications.json` 12.97 MB 只 1 条记录，excluded 32,709 条占 81%，reason 只 5 种、最多重复 27,624 次。消费点只有 freeze 子进程调 validate 看返回码＋整文件哈希。外链化要改 7 处且开哈希后门。

## 2. 修复方案

### 2.1 seal ↔ 零地址（零代码：披露表定为附录；codex 备选，我方采纳）

seal 一行不改。report-template 把"三策略翻转披露表"定为**附录 E**（附录允许完整地址），收据 `report_locations` 指向该附录标题（`_disclosure_slice` 只认标题不认层级，APU 已实证）。正文实体小节一句"完整披露见附录 E"，正文提池子可自由写名字。
- **改** `report-template.md:222`：改为"附录 E《溯源三策略翻转披露》（仅存在真实翻转时）……每策略主导终点完整地址与两位小数份额"；:147 附录骨架加一行 E。两处合计字数持平。:53/265/284 不动。
- FORGGIE/EGL1/APU 已封口报告不动；`scan-schemas.md:366`、`split-run.md:170` 不必改。
- **不采纳原稿"seal 接受标签名"**：codex 指出同名、空串恒真、子串碰撞三种误放行（`entity_source_trace.py:241` 标签读取不查 name 非空唯一，已核实）；且附录 B 宏只遍历 `facts.entities`，读者无处查名称↔地址。列附录 A 候选（前提：复用 `check_bound_file()` 三验、名称非空全文件唯一、防子串、绑定损坏即拒、mint 按完整三元组固定别名）。
- **不做**逐行配对核对：现有检查只证三者同现不证对应，是既有缺口，留 seal 加严批。
- **测试**：`t_f06_a5_disclosure` 加"披露段在 `## 附录 E` 下"绿例。

### 2.2 高频机械活稳定命令（本轮只加两个只读子命令；codex 复核后缩减）

挂 `handoff_manifest.py`（复用 data_map 路径解析 :286-303，守案根与 `sealed/` 边界），输出用**分页**不用截断：
- `inspect <file> [--path a.b] [--depth 2] [--limit N]`：键树/类型/长度/首元素样本（覆盖 495 条探测）。
- `lookup --addr …|--addr-file … --in <files…> [--fields …]`：跨 identity_cards/balances_final/entity_registry/labels_final/camps 回填地址表（覆盖 335 条）。

**本轮不做**（codex，采纳）：`q` 只读 SQL（不适合交接契约工具，副作用验收面大）；`apply --patch`、`claims-patch` 写入入口（合并/原子/哈希前置未定义；`claims-patch` 须复用 `validate_claim_rows()` 并与 reseal 约定边界）；`claims-dump`（最易闲置）。
**条文**：不加"禁止手写 python"文字规则；只改 `context-discipline.md` 刀 1 现有清单两条措辞与 `split-run.md` §3 工具表对应行，零新增行。
**`--session-jsonl`**：留另一会话 closeout 实现，统计缺失记"未统计"。
**配套**：删预填后 −2 要查候选成员，`template`/`distribution-template` 改为把成员清单写旁车文件 `<台账名>.members.json`（不进台账不进 schema）。

### 2.3 备份堆积与台账瘦身

- **删** `adjudication_validator.py:238/:417` `_members_total` 预填；**改** `scan-schemas.md:207/:524` 注释。已核 validate 只读 accepted/excluded，老台账仍 PASS。
- **改** `handoff_manifest.py:119` 排除规则为**精确规则**：`.bak` 改正则 `\.bak(_|$)`；新增 `.superseded` 族与完整目录分量 `_history`。`_pre_`、`.vN.` **不**用于排除（会误伤 `balances_pre_launch.json`、`labels.v3.jsonl`）。
- **改** `add_path()`（:254）：显式登记或 `--include` 命中排除时**报配置冲突**，不静默丢弃。
- **改** `freeze` 加案根卫生 **WARN**（不拒）：列出案根与 `data/` 一级匹配 `\.bak(_|$)` / `_pre_` / `\.v\d+\.` / `.superseded` 的文件，提示放 `_history/`。closeout 可复用。
- **改** 条文各一行：`split-run.md:109`"手工历史副本只进 `<案根>/_history/`，活跃路径保持唯一"（允许 cp 快照，不强制 mv）；`token-analyze-2.md` 同句。
- **台账理由**：`split-run.md:90-91` 加半句"excluded 的 reason 用简短可直读一句（≤20 字，同类成员同句），详细依据放 `evidence`"。如实标边界：validator 只查 reason 非空，不查 evidence、不查释义——人工约定非机器保证；不用不透明代码。EGL1 型预估 13 MB → 约 3 MB。
- **不做**：外链化；存量台账改写（改哈希须走修订链）。存量 78 件副本建议 `mv` 进 `_history/`（§5 由用户批）。
- **测试联动**（codex 发现）：`test_adjudication_validator.py:101` 直接 `pop` 该字段、`test_distribution_gate.py:377` 默认取它，两处改为从源 fixture 取成员并保留"老台账带该字段仍 PASS"用例；CLI 帮助与 schema 示例同步。

## 3. 验证

1. 2.1：新绿例 PASS，原用例不动；APU 报告复跑 `a5_report_seal` PASS；`docs_lint` PASS。
2. 2.2：`inspect`（分页、`sealed/` 拒绝、案外拒绝）、`lookup`（三文件回填、缺址标 MISSING）夹具用例；FORGGIE 案卷实跑。下一案主线内联 python <200（FORGGIE 486），探测类 <50。
3. 2.3：template 无 `_members_total` 且旁车在场；EGL1/FORGGIE 现有台账 validate PASS；夹具 `x.bak_2026`、`_history/y.json` 不收录，显式登记时报冲突，`balances_pre_launch.json` 正常收录；freeze 只 WARN；两处联动测试 PASS。
4. **上下文不增长实测**：`split-run.md`、`context-discipline.md`、`report-template.md`、`scan-schemas.md`、`token-analyze-2.md` 改前改后字节数，任一不得增长，写进工单完成标准。
5. `run_all.py` 全 PASS。

## 4. 与第一部分五项的关系

| 本部分项 | 重叠 | 处理 |
|---|---|---|
| 2.1 | closeout 调 `provenance_flip_bundle` | seal 不改；closeout 直接调该函数，勿另复制"必须含地址"逻辑 |
| 2.2 子命令 | `figures_from_facts fig2-series` | 只碰 `handoff_manifest.py` 新增段，无冲突 |
| 2.3 `_history/` | reseal 归档到 `stage2/_history/charts_final_<ts>/` | 按目录分量识别，两处都能处理；只约定新产物位置，不迁移已有归档 |
| 2.3 freeze 卫生函数、`add_path` 冲突报错 | closeout 复用 | 本部分先落 |
| 版本号与公共文档 | 7.1.0 | 由一个会话统一：本三项先落地记 7.1.0 CHANGELOG 三条，否则 7.1.1 |

施工顺序：2.3 → 2.1 → 2.2。每项一份 codex 工单（白名单＋行号＋先红后绿＋不 commit），Fable 验收后 commit＋push。

## 5. 需用户拍板

1. 2.1 走"披露表定为附录、seal 不改"（推荐，零代码）还是"seal 接受标签名"（约 30 行代码＋补对照展示位）。
2. 存量 78 件手工副本：`mv` 进各案 `_history/`（推荐，可逆）、删除、或不动。
3. 2.2 是否接受本轮只做 `inspect`/`lookup`，`q` 与两个写入入口留后（推荐接受）。

## 6. codex 复核记录（@CX，2026-09-15）

codex 总评"不建议原样落地"：2.1 可做但须收紧、更小备选是披露表放附录（**采纳为主方案**）；2.2 减少入口、写入型暂缓、截断改分页、不写"禁止手写"条文、删预填后要有成员查询入口（全部采纳）；2.3 支持删冗余与 WARN，反对 `_pre_`/`.vN.` 宽泛排除、指出 `add_path` 静默丢弃与两处测试依赖预填（全部采纳）；另指出 reason 短代码释义不受校验须如实标边界、版本号与公共文档由一个会话统一、"不增上下文"要实测字节（采纳）。我方无整条不采纳项；codex 未提但保留：存量副本只 mv 不删、外链化不做、存量台账不改写。逐条表见独立副本 §6。

## 附录 A　本轮不做、留候选

seal 接受受绑定标签名（含收紧条件）；披露逐行配对核对；三策略披露表固定模板（可读性批）；`q` 只读 SQL、`apply --patch`、`claims-patch`；台账 `members_ref` 外链；存量台账瘦身；`--session-jsonl` 统计。
