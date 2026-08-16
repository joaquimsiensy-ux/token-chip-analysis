# AI-2「对账与观测证据链组」修复计划 — F-04 / F-07 / F-09 / F-10（@CX 融合定稿）

> 基线：`ddba1871`（main，v6.44.0）；施工分支 `repair-20260815-g2`（git worktree 隔离）
> 来源：codex 六视角 review `token-chip-analysis-main-v6.44.0-sixlens-full-review-2026-08-15.md`
> 本计划已经 codex @CX 只读复核并融合其意见（文末附采纳纪录；标 **[CX]** 的条目来自 codex 复核）

## Context（为什么修）

- **F-04 (P1)**：EVM 观测 bundle 接受冻结块空 runtime code——EOA/未部署地址能产 PASS bundle、供给 0。evmobs 工程（修 R10-13）新引入。
- **F-07 (P1)**：A2 四查的 balance/supply/time/anchor 子收据，消费侧只看自报计数不重算——绑定真实 input 却人为构造 `checked=matched=1, closed=true` 的收据能过发布链。v6.34.0 receipt 化时 consumer 没做等深。
- **F-09 (P2)**：GMGN top10 对表差异算完就丢，verdict 不看 `gmgn_diff`。**用户已裁决黄灯制**：差异不停工，打警告标记；带警告的案发布前必须附人工查证说明（GMGN 滞后/口径不同/上游错误），发布闸验到合格说明才放行；查证发现自己算错 → 必须修数据重跑，不得写说明放行。
- **F-10 (P2)**：SKILL/registry 承诺 Arbitrum 保留探索采集与对账，但四个对账 CLI 的 choices 用 formal 集合构造，`--chain arbitrum` 在 argparse 层 exit 2。v6.36.0 把"正式发布集"误用为"可执行集"。

## 已核实的代码现状（自查＋两路探索代理＋codex 复核三方一致）

- `verify_recon.py`（178 行）：observations 明细完整（supply_closure 五标量+negatives、balance rows 逐行、gmgn rows 逐行）；envelope inputs 绑 config/balances/replay_stats/gmgn 四实物（案根强制）；verdict（:148-155）只看 rpc_errors/supply_closed/mismatched；schema=`evm-reconciliation-receipt/v2`。top-N 现语义=**先截 top_n 再跳过 ZERO/DEAD**（:105-107），且 `top_n` 参数不落收据。gmgn csv 解析用 `float()`（:128），NaN 会静默落 OK。
- `shared_release_receipt.py::validate_reconciliation_check`（:471-662）：EVM balance/supply/time 与 Solana anchor 分支全是自报计数消费；同文件 supply_truth 分支（:529-652）是深重验样板（`_bound_replay_totals`、N-2 bundle 交叉）。此函数无外部副本，handoff/audit 经 `validate_reconciliation_report`/`validate_bundle` 调用链自动继承。audit 浅表 `check_reconciliation` 与 handoff `AUTO_GATES` 是另两条只看 verdict/exit 的加法线，不受影响。既有"EVM 三查同源"约束（:693-707）保留互补。
- `evm_observation.py`：`_HEX_DATA` 的 `*` 量词放过裸 `0x`（producer :196-198、transcript :317-319、validator :392-395 三层都不拒空）；`_eth_call_value`（:66-70）用 `_HEX_VALUE` 接受 `0x0` 短值；**三笔 eth_call 用 EIP-1898 blockHash selector 而 eth_getCode 用块号**（:169-198）——code 指纹与供给读数可属不同分叉 [CX]。
- `receipt_kernel.py`：`VERDICT_EXITS={PASS:0,FAIL:2,ERROR:1}` 白名单；`warnings` 不在 RESERVED_FIELDS，`finalize_envelope(**fields)` 可附加。WARN verdict 需动 kernel/receipt_validate/shared 三处 PASS-only/audit PASS_WORDS/handoff 接受集共 5+ 处且 publish 层无出口——不做。
- `chain_registry.py`：`capability_chains(name, release_tiers=)` 现成分档过滤；Arbitrum `release_tier="exploration"` 但 balance/supply/time/accounting 能力全 True。四 CLI choices：`accounting_gate:392`、`verify_recon:45`、`time_spotcheck:221` 用 `formal_evm_chains`，`supply_truth_gate:526` 用 `formal_reconciliation_chains`。
- `time_spotcheck.py`：rows 明细完整；envelope **只绑 plan**——运行时验过 plan_receipt 与 input 却未绑进收据 [CX]。`anchor_sampler.py`：envelope 绑 config，顶层 `output{path,size,sha256}` 绑采样产物。
- over-cap-approval/v1 先例（无 producer 脚本的人工件）：生产侧 `supply_truth_gate:214`/消费侧 `shared_release_receipt:185` **双写验证器**（语义常数共享、验证逻辑刻意双写）+ request/request_sha256 输入哈希绑定 + `_meaningful_text` 实义 + 两侧行为向量等价守卫（`test_repair_batch_a.py:1583`）。F-09 说明件照此模式。
- build_html 的"有 WARN 不写 HTML"是其本地字符串列表，不读收据字段；收据顶层 `warnings` 不会被它误伤。

## 修复方案（四刀＋中心登记末刀，每刀独立 commit + 先红后绿）

### 第 1 刀 F-04：观测件拒空 code / 拒短值 / getCode 分叉对齐

改 `scripts/lib/evm_observation.py`：

1. producer getCode 后：`code_raw == "0x"` → raise（正式观测目标必须已部署；零供应合法但 code 必非空）。
2. `_eth_call_value`：totalSupply/balanceOf 返回值要求**恰为 66 字符**（0x+64hex 严格 32-byte ABI word）；短值左补零也不接受 [CX 确认不放宽——非标 returndata 合约进 exploration/专用 adapter，不降正式证据标准]。
3. transcript 重验对称收紧：三笔 eth_call 值同要求 66 字符；getCode 结果拒 `0x`。
4. validator：`runtime_code_sha256` ≠ 空字节串哈希常量 `e3b0c442…b855`。
5. **[CX] getCode 与三笔 eth_call 对齐同一 EIP-1898 blockHash selector**（`{"blockHash":…,"requireCanonical":true}`），使 code 指纹与供给读数锚定同一条已确认分叉；transcript 第 7 笔 params 校验同步改。RPC 不支持时走既有 eip1898 硬退路径（formal 不降级）。兼容性定性：bundle 协议校验变严，旧格式 bundle 被新 validator 拒=正确行为（v6.44.0 至今无已发布 EVM 案依赖旧 bundle，重发布本就须重产）。
6. 新测试 `test_evm_observation_nonempty_code.py`（复用 FakePool + `mock.patch.object` 手法）：EOA 负测、`0x0` 短值负测、空 code hash bundle 负测、getCode selector 形状负测、零供应合约+非空 code 绿例。

### 第 2 刀 F-10：Arbitrum 探索档 CLI 兑现 + 消费面等深钉死

原则：先钉死正式消费面，再放宽 CLI（不重蹈 v6.36.0"修复中新引入"覆辙）。

1. `shared_release_receipt.py`：EVM balance/supply/time、Solana anchor 分支补**双断言** `receipt.mode == "formal"` **且** `formal_ready(target.chain)` [CX：mode 单断言挡不住整体改标——探索收据连 wrapper 一起改成 formal 时，target.chain 档位是独立防线]；`validate_reconciliation_report` 的 target 级同补正式链档位断言。shared receipt 自称独立正式发布证据，不依赖 audit/handoff 更晚入口兜底 [CX]。
2. `chain_registry.py` 新 helper：`executable_evm_chains(capability)` 与 `executable_reconciliation_chains(kind)`（tiers={formal, exploration}），复用 `capability_chains`。
3. **[CX] 四 CLI 共用一个纯策略 helper**（放 chain_registry 或 lib 公共处）：统一裁决"formal 链默认 formal；显式 `--exploration` 才 exploration；exploration 档链缺 flag 硬拒；`--bundle` 与 exploration 互斥面保留"——四处各自实现必然漂移。
   - `accounting_gate.py`：choices 换 executable 集＋策略 helper（arbitrum+`--bundle` 拒）。
   - `verify_recon.py` / `time_spotcheck.py`：choices 换 executable 集＋新增 `--exploration` flag（envelope mode 按 flag 写）。
   - `supply_truth_gate.py`：choices 换 executable 版（保留 sol→solana 映射），补非 formal 链强制 flag。
4. **[CX] 存量测试同步**：`test_batch2_capability_matrix.py:53` 硬断言四 CLI 用 formal-only helper，语义变更后必红——同刀改断言为新策略 helper（属"语义变更引发的存量测试更新"，done 报告标注）。
5. 新测试 `test_arbitrum_exploration_cli.py`：四入口 arbitrum 正测（argparse 零网络＋time 走 `--dry-run` 离线模板）；负测=mode=exploration 收据/arbitrum target 收据进 `validate_reconciliation_check` 必拒、formal 四链无 flag 行为不变（绿例回归）。

### 第 3 刀 F-07：四查子收据消费侧深重验＋producer 最小补齐（本组最大块）

**[CX 修正] 撤回"producer 三件不动"**——三处 producer 需最小补齐，否则 consumer 重算有歧义或无绑定可验：

**producer 侧最小改动**：
1. `verify_recon.py`：
   - balance top-N 修语义歧义 [CX 抓漏]：排序加确定性 tie-break（`(-balance, address)`），observations 记 `requested_top_n`——现语义"先截 top_n 再跳 sink"下 `len(rows)` 无法反推 top_n（sink 落窗内时），consumer 无法唯一重算。
   - gmgn csv 解析改 Decimal＋拒 NaN/Inf/非法 pct/重复地址 [CX：`float()` 现会让 NaN 静默判 OK]。
   - **补落 RPC transcript**（照 `evm_observation.py` 的 `_record` 模式）：每笔 balanceOf 的 method/params/result 落 sidecar 文件并绑进 inputs——把 rows.chain_raw 从"行内自洽"抬到"与逐笔调用记录绑定" [CX：不补 transcript 只能关最小反例，不能关 finding]。
   - schema 升版 **`evm-reconciliation-receipt/v2` → `/v3`** [CX：加 warnings/requested_top_n/inputs.divergence_note/transcript 是实质契约变更，静默改 v2 违反"升 schema 必连下游一起升"元规则]。formal 消费只认 v3，v2 拒收带迁移文案（同 supply-truth v4 先例"存量案须重跑"）。
2. `time_spotcheck.py`：envelope 补绑 `plan_receipt` 与 `input`（运行时已验但未绑进收据 [CX]）＋补落 RPC transcript；schema 升 **`time-spotcheck/v2` → `/v3`**。
3. `anchor_sampler.py`：不动（output{path,size,sha256} 绑定已足）。

**consumer 侧深重验**（`shared_release_receipt.py::validate_reconciliation_check`＋新私有 helper，照 supply_truth 分支样板）：
1. **EVM supply**：从绑定 config/replay_stats/balances 实物重算 nominal/mint/burn/balance_sum/negatives（含 negative_addresses 全列）/closed，config token/decimals 与 stats 截止块同验 [CX 扩清单]——杀死 review 最小反例。
2. **EVM balance**：rows 每行 replay_raw==绑定 balances 实物值；地址序列按 producer 新记的 `requested_top_n`+确定性排序完整重算（先截后跳语义对齐）；status/diff_raw 自洽；checked/matched/mismatched 与逐行重算一致；chain_raw 与绑定 transcript 逐笔对照。
3. **EVM time**：rows 对绑定 plan 实物 **multiset 一一对应**——balance 点比 kind/addr/block/expect_raw，tx 点比 kind/tx/from/to/block/expect_raw [CX 补全字段]；plan_receipt→input 绑定链验证；六计数逐行重算；PASS 收据不得含 MISMATCH/RPC_ERR 行。
4. **Solana anchor**：从顶层 output 实物（size+sha 双验）逐行重验——日期范围/日期唯一/身份字段（chain/mint/as_of）/error 状态，重算 covered/failed 与 coverage、failures 对照 [CX 补逐行深度]。
5. **gmgn rows 重验**（为第 4 刀铺底）：gmgn_pct 从绑定 csv 重算（Decimal、拒重复地址）、replay_pct 从 balances/nominal 重算、diff_pp/status/diff_count 全自洽。
6. 新测试 `test_recon_deep_reverify.py`：每子收据一组变异反例＋EVM 夹具与 staging-pythia 真实案绿例回归。
7. **[CX] 存量测试破坏面**：手造浅收据 fixture 的测试（`test_sixlens_receipts`、`test_handoff_manifest`、`test_audit_release_gate`、`test_evm_observation_release`、`test_batch3_evm_vertical_slice`、`test_repair_batch_d` 等）会被深重验打红——逐个跑红修绿（fixture 升为带实物绑定的真语义夹具），清单入 done 报告。

**如实定性（写进代码注释与 done 报告）**：本刀关闭至"transcript/实物绑定"深度；"远端节点真执行"证明与完整 job spec 契约属外部锚定族（R10-9/14，execution ledger 已覆盖 run-role 面），剩余面按台账口径留账，不声称全闭 [CX 措辞采纳：关闭最小反例＋绑定深化，剩余如实标注]。

### 第 4 刀 F-09：GMGN 黄灯 + 查证说明放行制（骑在第 3 刀之上）

1. **producer** `verify_recon.py`：
   - gmgn_diff>0 时 verdict 仍 PASS/0，`finalize_envelope` 附加顶层 `warnings:["gmgn_divergence"]`（零差异 `[]`）；消费侧要求 warnings 为无重复合法元素数组 [CX]。stdout 打印黄灯与补说明指引。
   - 新增可选参数 `--divergence-note`（waiver 同款时序：先跑出黄灯收据 → 人工查证写说明 → 带参重跑绑定）：生产侧验合格后绑进 `inputs.divergence_note`；说明覆盖不了当前差异集合 → 硬退且**不覆盖原黄灯收据** [CX 真值表]；零差异带说明 → 硬退（防预填空说明）。
2. **新件 `gmgn-divergence-note/v1`**（案根 `gmgn_divergence_note.json`，人工查证后手写，无 producer 脚本——over-cap 先例）。**[CX 采纳：绑定强度升级为输入哈希请求契约]**，字段族：
   - `schema` / `request`{ target、**inputs_sha256**{config, balances, replay_stats, gmgn 四实物哈希}、divergences（规范化**有序**差异列表：address/gmgn_pct/replay_pct/diff_pp，数值用 Decimal 规范字符串）} / `request_sha256`（规范 JSON 重算）——同一数值差异不可跨输入版本复用；
   - `findings[]` 与 divergences 按 address 一一对应：cause ∈ `{gmgn_data_lag, methodology_diff, gmgn_upstream_error}`（**故意不设 self_error 放行项**：自己算错→修数据重跑）、explanation（`_meaningful_text` 实义＋≥30 字符）、`evidence_refs` 可选（给则验案根内实物）；
   - `conclusion`（必须含"重放数据经查证无误"承诺语义）/ `investigator` / `investigated_at_utc`（严格 UTC＋合理窗口）[CX]；
   - 解析层拒 NaN/Inf（`_reject_constant` 先例）、地址唯一。
   - 关于 evidence_refs 强制性：codex 倾向强制；本计划定为**可选**——用户裁决语义是"写明白原因"而非"必须留存外部证据"，gmgn_lag 类常见因未必有可存档实物，强制会让黄灯实质变红灯；真查证质量由 A4 对抗复核环兜底（说明件进 claim 面）。此点保留给用户复核时否决的空间。
3. **consumer**（独立重写验证器，与生产侧刻意双写、只共享 schema 常量与阈值——over-cap 双写纪律）：
   - 权威判据=第 3 刀重算的 diff_count；`warnings` 与它严格互锁（防剥离）[CX 确认此设计闭合]；
   - diff_count>0 → `inputs.divergence_note` 必须存在且解析到案根实物：request 四哈希==收据 inputs 四实物哈希、divergences 与重算差异集合**有序相等**（数值逐项）、request_sha256 重算一致、findings 覆盖完整、cause/explanation/conclusion/时间全验；
   - handoff/audit 经调用链自动继承。
4. **文档**：`data-pipeline-evm-recon.md` §5 第 1 条改写黄灯制全流程（四态真值表：有差异无说明=收据 PASS 但发布阻断；有差异合法说明=重跑绑定放行；无效说明=生产侧拒且不覆盖；无差异给说明=拒）[CX]；顺手修正既有文档-代码落差（"top-N RPC 直查"与"GMGN 百分比对表"混写成一件"逐个对到个位数"的 gate——拆开如实写）。保住本册三条契约 needle。不动 `analyze-workflow.md`（AI-3 域）；**发布段指向 recon 分册的流程路由一句留融合方**，建议文案入 done 报告 [CX：操作者只见发布失败不知如何解锁]。
5. 新测试 `test_gmgn_divergence_note.py`：四态真值表逐态测试（**明确拒绝方**：producer 层拒=带参重跑硬退，consumer 层拒=发布链阻断，两层分别断言 [CX 消歧]）；说明件各字段负测（覆盖不全/数值不符/输入哈希不符/cause 非法/explanation 过短/时间非法）；**两侧行为向量等价守卫**（照 `test_repair_batch_a.py:1583`）；合法说明全链绿例＋零差异绿例。

### 第 5 刀（末刀）：中心登记独立收口 [CX 融合方式采纳]

生产代码与专属测试/文档在前四刀；**中心文件改动集中成独立的最后一刀 commit**，融合方可整刀重放或丢弃自行统一：

- `run_all.py`：末尾新增一个带版本注释的 `SUITE += [...]` 追加块挂 4 个新测试（EOF 追加仍可能同上下文冲突 [CX]——独立末刀使融合方处理成本最低）。
- `invariant_manifest.json`：新 schema 消费点按 `invariant_scan.py` 实际扫描 diff 结果登记 [CX：`gmgn-divergence-note/v1` 会被 verify_recon（生产侧验证）与 shared（消费侧）两处 AST 抽出，receipt_consumers 大概率+2 不是+1，勿手拍数字]；recon/time schema 升版串同步；`minimum_counts` 只升不降。
- `contract_manifest.json`+`contract_ids_snapshot.json`：新契约 ID 用本组专属前缀 `CT-RECON-xx`（三 AI 不同前缀防撞号）；recon/time 收据升版的既有 needle（若有）同步改串；snapshot 保持排序。
- CHANGELOG/VERSION/r10_ledger/SKILL.md 仍零改动（融合方域）。

## 测试手法选型（复用现成模板）

- F-04：`test_evm_observation.py` 的 FakePool（transport-only，带故障旋钮）+ `mock.patch.object(cli, "attested_rpc_pool", ...)`。
- F-07/F-09 consumer：案根夹具（真实绿收据+变异副本）直调 `validate_reconciliation_check`；参考 `test_sixlens_receipts.py` 手法。
- F-09 producer：`mock.patch.object(net, "_request_json", side_effect=...)`（`test_batch1_rpc_attestation.py:29-31` 模板）让真 `verify_recon.main()` 全逻辑跑、只假出网一跳。
- F-10：argparse 层零网络；time 正测走 `test_time_spotcheck.py` 纯离线 `--dry-run` 模板。

## 施工与协调纪律（三 AI 并行防撞）

- worktree 分支 `repair-20260815-g2`，基线 `ddba1871`；完成后**不 merge main**，产 done 报告等融合。
- 不碰：VERSION、CHANGELOG、SKILL.md、r10_ledger.md、pyproject。
- `shared_release_receipt.py` 只动 `validate_reconciliation_check`/`validate_reconciliation_report` 及新增私有 helper，不碰 A4/adversarial 函数区（AI-3 域）；`audit_release_gate.py`/`handoff_manifest.py` 零改动（AI-1 域，语义经 import 链继承）。
- 存量测试仅改"语义变更必然打红"的断言与 fixture（第 2/3 刀已列），逐个在 done 报告登记；新测试一律独立新文件。
- 对外措辞用"负向测试/变异复核"，避免触发平台过滤器（0814 教训）。

## 验证（端到端）

1. 每刀 commit 前：新测试对基线先红、对修复后绿，红绿证据落 `maintenance/repair-20260815-g2/`。
2. 绿例回归：EVM 纵切片夹具＋staging-pythia 真实 Solana 案走 shared 消费全绿（深重验不误伤真实案）。
3. 全量 `python3 scripts/tests/run_all.py` 本机全绿（含两项 loopback）；`invariant_scan.py --self-test` 过。
4. done 报告：改动清单、五刀红绿证据、消费面负向测试证据、存量测试修改清单、留融合方事项（analyze-workflow 路由句建议文案、中心登记刀说明、R10 台账定性建议——F-07 剩余面）。

## @CX 复核融合纪录

codex 结论"反对直接按原计划施工，架构方向正确但有 4 个实质缺口"。处置：

| codex 意见 | 处置 | 说明 |
|---|---|---|
| F-09 不引 WARN verdict 正确；warnings 需重算互锁＋数组合法性 | 采纳 | 互锁原计划已有，补数组合法性 |
| 说明件升级为 request/request_sha256 输入哈希契约（四输入 sha+有序差异集+Decimal+时间+investigator） | 采纳 | 原设计"recon_receipt_sha256 反向绑定"有重跑时序矛盾且可跨输入版本复用，改为 over-cap 同构 |
| evidence_refs 应强制 | **部分采纳（定为可选）** | 用户裁决语义+防黄灯变红灯+A4 兜底；保留用户否决空间 |
| F-07 top-N 重算语义与 producer 不等价、top_n 不落收据无法唯一重算 | 采纳（producer 补 requested_top_n+确定性排序，撤回"producer 三件不动"） | codex 抓到的确定性错误 |
| time 收据未绑 plan_receipt/input | 采纳（producer 补绑） | |
| 不补 transcript/job spec 则 F-07 只关最小反例 | 采纳 transcript（verify_recon/time_spotcheck 落逐笔调用记录并绑定）；job spec 全契约维持圈外、如实留账 | 与 evmobs bundle+transcript 模式等深；外锚族按 R10-9/14 定性 |
| supply 重算字段清单扩全、anchor 逐行深验、gmgn Decimal/NaN/重复地址 | 采纳 | NaN 静默 OK 是现有 producer 缺陷，一并修 |
| recon/time schema 静默变更违规，应升 v3 | 采纳（v2→v3，formal 只认 v3，迁移文案） | 十层元规则"升 schema 连下游一起升" |
| F-10 mode 单断言不足，补 formal_ready(target.chain) 双断言＋target 级 | 采纳 | |
| 四 CLI 共用策略 helper | 采纳 | |
| `--exploration` 布尔 flag 优于 `--mode` | 采纳（维持原设计） | |
| `test_batch2_capability_matrix.py` 存量必红 | 采纳（同刀改） | |
| F-04 66 字符不放宽；getCode 对齐 blockHash selector | 采纳 | selector 不一致是 codex 新抓的分叉缝隙 |
| 中心文件集中独立末刀、按扫描实际结果登记、CT ID 防撞 | 采纳 | |
| analyze-workflow 需发布段路由句 | 采纳（留融合方，文案入 done 报告） | |
