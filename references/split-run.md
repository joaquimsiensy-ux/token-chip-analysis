# 分段执行手册（split-run：−1 机械段 / −2 判断段）

> v6.1.0 新增。**本文件是分段执行的唯一权威源**：−1/−2 边界、交接契约、两段开工序全在此，其他文档只指针不重复。
> 命名纪律：展示层叫 **−1 / −2**；schema 与内部枚举一律 ASCII（`stage1_mechanical` / `stage2_judgment`）。不叫"两段制"（该词已被 monitoring-package 报警两段制占用）。
> **适用范围（v1）**：仅新标的 full 分析；既有报告净室复核暂不支持（三账契约接好后再开放）。单会话 `/token-analyze` 作为小盘币一口气跑与分段故障的回退路径。

## 本册路由

- §0 会话流；§1 −1 机械段；§2 handoff；§3 −2 判断段；§4 验收与回退。

## §0 会话流与设计原理

```
用户在 codex CLI（主轨 GPT-5.6）："对 <币> 跑 −1（机械段）"
  或 CC 开 Opus 会话（备轨）跑 /token-analyze-1 <币> [链]
        ↓ 产物全部落 <币>分析/ 工作目录，完成即停
用户手动新开 Fable 5 会话（CC），同目录跑 /token-analyze-2 <币> full
```

- 拆分线对齐 context-discipline 刀 1 既有机械/判断划分（会话级升级，规则语义零变更）：−1＝A0–A2 全部＋A3 机械子层；−2＝A3 判断层＋A4–A5（A6 复盘仅用户明确要求时）。
- 动机排序：①判断段在干净上下文里执行（防长上下文注意力稀释——质量收益）②机械段不烧主力判断模型额度（成本收益）。
- 分工依据（实证）：GPT-5.6 机械段强（逐 wei 对平、gate BLOCK 即停、写什么做什么），判断段弱（其翻案史 REFUTED 全集中在托管定性/实体冻结/口径外推）——**凡出现在其翻案史的环节一律进 −1 停止线**。

## §1 −1 机械段（A0–A2 全部 ＋ A3 机械子层）

### 1.1 开工探针（capability preflight，全部复用现有件；探针不过不启动全量采集）

`scripts/tests/env_check.py`（依赖）＋磁盘余量（`scripts/run_guarded.py` 既有阈值）＋工作目录写权限＋detach 后台冒烟。

### 1.2 双轨互斥锁

开工先抢案级 `.stage1.lock`（复用 `scripts/proclock.py` 机制，锁文件记 pid/run_id/心跳）＋生成本次 `run_id`。主轨（codex/GPT-5.6）与备轨（CC/Opus）**禁止同时写同一案目录**；抢不到锁即退出并报告在跑者信息。

### 1.3 范围（做什么）

- **A0 全部**：合约核定、多链硬关卡（AskUserQuestion 选链范围）、分母口径、链路由、accounting_gate——**exit 2 → −1 停工写 blocker 进 anomalies，禁套标准管线**；vesting 标的产 `unlock_evidence.json`（仅事实：来源/日期/数量/口径/冲突，零质量判断）。
- **CEX 黑箱关卡**（维持点名制，用户命令附加要求时才做）：结论落盘必须含同块分母＋confirmed/suspected/ambiguous 三档分列＋保守上限口径＋用户裁决与时间戳；超线中止 → manifest 状态 `BLOCKED_CEX_GATE`，−2 拒绝消费。
- **A1 全部**：并行采集＋存量产物复用（断点续拉，禁从零重采）；`done_with_gaps` 必须补齐才准出 READY。
- **A2 全部**：四查对账 fail-closed，四个生产者必须由 `scripts/report/reconciliation_report.py` 接收 job spec 后受控启动；runner 校验新鲜 receipt、target、生产者和输入/receipt 哈希，再原子生成 `reconciliation_report.json`，禁止手拼 wrapper。时间抽查跑 `scripts/lib/time_spotcheck.py`（EVM 案 `time_spotcheck.json` 为 READY 必备件＋AUTO_GATES，6.7.0）——**默认锚点级直查即闭环，全史第二源重拉是例外动作**（触发条件与 pilot 报 ETA 纪律见 evm-recon §13；APU 案照旧模板全史重拉 103 分钟纯冗余教训）。

  上述“禁止手拼”是执行纪律，不是聚合器具备单机执行证明：聚合器能拒绝缺 runner 绑定或绑定哈希不符的 wrapper，但无法识别蓄意填写正确 path/SHA-256 并编造自洽观测的 wrapper；内容绑定的作用是把无意漏跑变成必须显式造假的行为，并留下可由仓库 git 历史审计的代码哈希。
- **A3 机械子层**（对照 analyze-workflow A3 主序编号）：
  1. 地址身份标注**批量层**（主序第 1 项前半）：标签库/getCode/Sourcify/外部证据批查。**输出只写观察事实**：`observed_type`＋`source`＋`source_timestamp`＋`conflict_flags`；仅多源无冲突的公共设施可标 `auto_excluded_candidate`，最终排除权在 −2。
  2. 金库与核心实体逐笔归因**跑批**（主序第 1 项中段的脚本执行侧）：产出流水，不定性。
  3. 大户排查**批量层跑满**（主序第 5 项的批量侧）：当前 ≥0.1% 总供应或 ≥0.2% 流通全量＋历史越线＋归零/静置候选（`dormant_candidates` 并入 candidate_universe）× 标签库/惯犯库/指纹/funder 溯源四通道；无法机械定性者标 `needs_adjudication`（批量层跑满是防"候选海"倒灌 −2 的第一道闸）。
  4. 聚类准备（主序第 1 项后半的算法侧）：cluster_prep ＋聚类算法**候选簇**——含拒绝边与孤立点**全量保留**，不只交"算法觉得相关"的簇；合并裁决权在 −2。
  5. `identity_preflight.json`：候选与大仓地址的原始事实层（标签/on-curve/getCode/托管疑点）。**正式 entity_identity_gate 属 −2**——该脚本依赖含实体表的 analysis-state.json，−1 无实体表跑它只会产出假 gate。
  6. 基础序列：`address_bucket_series`（标签桶序列）＋价格序列。**命名禁用"阵营/camp"**——真 camp_share_series 只能 −2 实体冻结后生成。序列产出时顺手标记"价格单日 ±50%"与"单日桶间变动 ≥10pp"的日子清单（供 −2 定峰值逐笔触发日用，无归因义务，2026-08-02）。
  7. **全体持仓波次扫描（v3）**：`scripts/report/wave_scan.py`（原始边表直读，扫描对象＝全体历史峰值 ≥0.02% 地址不限清零层，A 种子窗/B 喂币专属/C 快速清仓/D 等额面额四指纹合并口径）产 `wave_scan_report.json`（wave-scan/v3，含 scan_universe 逐址全集＋must_adjudicate 标记）——**READY 必产件，缺件 generate 即拒**；候选只报警不定性，裁决权在 −2；已知公共设施可经 `--exclude-file` 剔除（取 candidate_screening 的 auto_excluded_candidate）。
  8. **资金流异常扫描**：`scripts/report/flow_anomaly_scan.py`（汇集点＋分发点三口径多命中 v2——pulse／pulse_all 不限新老收方／slow_spray 全史 ≥100）产 `flow_anomaly_report.json`（flow-anomaly/v2）——**READY 必产件**；Q1/3yMk 型进货枢纽与 H9 派发器型出货器由此现形，候选裁决权在 −2。
  9. **当前持仓分布初判**：运行 `holder_distribution_scan.py --stage initial`，产 `distribution_scan.json` 和 `charts/distribution_stage1.png`。JSON 是 READY 必产件，工作图只供 −2 查看，不进 seal 或报告。initial 不绑定 handoff manifest。**快照单一来源硬性**：这一步吃的 owner 快照必须与 A2 四查 `verify_recon --balances` 吃的是同一个文件，别另存一份"内容一样"的副本——发布闸 new-analysis 拿 sha256 做等值比对（EVM 对四查 balance 收据的 `inputs.balances`，Solana 对 observation bundle 的 `holder_outputs.owners`），两份文件哪怕总和相同也会被判"同值换仓"直接拒。initial 记录的 `upstream_receipts` 是 optional 记录性收据：案根还没有 preflight 副本时不记是合法的，但记了就会被逐项三验。
- **初步观察（可选但鼓励）**：−1 执行者的初步定性/怀疑**只准写进 `sealed/stage1_hypotheses.sealed.md`**（密封纪律见 §2.3），主产物区零定性词。

### 1.4 停止线（禁做清单，越线＝流程事故）

聚类合并裁决／实体冻结／判级／casebook 过闸／大户报警深挖／正式 entity_identity_gate／状态评估定性／A4 对抗复核／A5 报告。
**未档异常 → 停下写 blocker 进 anomalies.json，禁自创解法。** 完成即停：打印交接摘要＋下一步指引（提示用户开 −2 会话），不多做一步。

### 1.5 盲化（跨段执行）

−1 全程 `export CHIP_BLIND_SERIAL=1`，惯犯命中只落机器字段（sealed_serial_hits.jsonl 既有机制）；每步 receipt 记录 blind_mode。**揭盲动作属 −2 的 A4，且前置条件＝entity_freeze.json 已落盘**（`handoff_manifest.py freeze --check-unseal` 把关）。

### 1.6 断点恢复

每完成一步用 `handoff_manifest.py receipt` 追加 `stage1_receipts.json` 一条（step/cmd/exit/artifacts/ts_utc/blind_mode）。−1 中断后新会话：读 receipts 定位断点 → 脚本本身幂等续跑（采集续拉增量、对账按 context-discipline 断点五步的"数据不重采/增量后必重跑"规则）。不造大状态机。

## §2 交接契约（handoff）

机器权威源一律 JSON；md 仅渲染层可选。工具：`scripts/report/handoff_manifest.py`（子命令 `generate / verify / receipt / freeze`，schema 常量内嵌，测试 `scripts/tests/test_handoff_manifest.py` 进 run_all）。

### 2.1 产物清单

| 件 | 产者 | 说明 |
|---|---|---|
| `handoff_manifest.json` | −1 | **语义收据而非文件清单**，字段见 §2.2 |
| `stage1_receipts.json` | −1 | 每步执行收据（含 blind_mode），断点恢复与盲化审计双用 |
| `candidate_universe.json` | −1 | 全量候选＋入选原因（当前阈值/历史越线/归零/静置 dormant_candidates）＋稳定 ID |
| `candidate_screening.json` | −1 | 批查四通道结果＋`observed_type/source/conflict_flags`＋`needs_adjudication` 标记；簇/边直接引用 cluster_prep 既有产物路径（在 data_map 登记），不重复造格式 |
| `identity_preflight.json` | −1 | 地址级原始事实（标签/on-curve/code/托管疑点），供 −2 跑正式 gate |
| `anomalies.json` | −1 | 每条 `id/severity/blocking/stage/status/evidence/resolution`——WARN/勉强 PASS/绕过/未档 blocker/缺口处置全在此，**血泪权威源，−2 必读件** |
| `data_map.json` | −1 | 数据索引：路径/schema/行数/块与时间范围/来源/生成命令/哈希＋DuckDB 查询示例 |
| `unlock_evidence.json` | −1 | vesting 事实（按需） |
| `wave_scan_report.json` | −1 | 全体持仓四指纹波次扫描（wave_scan.py，wave-scan/v3）候选波次＋等额组＋scan_universe 全集；READY 必产件，−2 逐条裁决完毕前历史大户兜底桶不准关闸 |
| `flow_anomaly_report.json` | −1 | 资金流异常扫描（flow_anomaly_scan.py，flow-anomaly/v2 三口径多命中）汇集点＋分发点候选；READY 必产件 |
| `distribution_scan.json` | −1 | 当前 cutoff 的 initial 分布扫描（distribution-scan/v2）；READY 必产件，verify 独立重算 |
| `candidate_adjudications.json` | −2 | wave/flow 全候选成员级裁决台账（candidate-adjudications/v1；`adjudication_validator.py template` 起草、`validate` 校验）——freeze 机器前置，缺漏即拒 |
| `distribution_adjudications.json` | −2 | final 异常簇成员级裁决台账；存在时 freeze 必须校验并绑定当前实体名册 |
| `pattern_resolutions.json` | −2 | 盘面机制解释台账；路径 A 被书面排除后才使用，未决项阻断 |
| `distribution_rounds.json` | −2 | final 轮次追加台账；terminal 前不物化终版图 |
| `provenance_ledger.json` | −2 | 已知实体币源溯源台账（entity_source_trace.py，正式模式强制绑定 `--labels-file`；`--allow-no-labels` 仅探索且 freeze 必拒；provenance-ledger/v2 正向模拟＋完整输入绑定）——freeze 从原始边/标签真实重放；v1 一律重跑 |
| `sealed/stage1_hypotheses.sealed.md` | −1 | 初步定性密封件，见 §2.3 |
| `entity_freeze.json` | −2 | 冻结事件物化：成员表哈希/时间/未决项/casebook 检验结果；变更走 revision 追加，不许静默覆盖 |
| 既有产物 | −1 | accounting_mode、链内 done.json/collection_manifest/receipt、四查 producer receipt、由 `reconciliation_report.py` 生成的 `reconciliation_report.json`、cluster_prep、address_bucket_series、价格序列；四查 receipt 格式零改动，wrapper 禁止手拼 |

**findings.md 双义处理**：−1 不写 findings.md（它是 A3 交接包，归 −2 按 context-discipline 现行制度写）；点名式 CEX 黑箱关卡中止时，其结论只作为 `BLOCKED_CEX_GATE` 恢复资产。

### 2.2 handoff_manifest.json 语义（schema `handoff/v3`；v1/v2 只可 `verify --legacy-read-only` 只读降级，机器 receipt 落盘、不得生成新正式报告）

- **身份**：schema_version、case_id、run_id、mode（仅 `full`；**值来源＝/token-analyze-1 命令的档位参数，−1 收工 `generate --mode full` 必填传入**，用户未给档位时 −1 开工前先问、禁猜）、producer_model、CC/codex 两侧 git SHA、consumer_min_schema。
- **口径**：链范围、合约、冻结块/slot、UTC cutoff、三种分母（总供应/调整后/流通）及来源。
- **gate 记录**：每个 gate 的命令＋exit＋语义状态。`accounting_mode.json`、`supply_truth.json`、`time_spotcheck.json` 与 `reconciliation_report.json` 均由 AUTO_GATES 从产物 JSON 自动读 `verdict/exit_code`，禁止 declared 覆盖；其余 declared gate 也必须同时满足 `verdict=PASS|OK` 且 `exit_code=0`，generate 后 verify 会重查。四查必须运行 `reconciliation_report.py`，由 runner 记录四个子进程 exit 并绑定 producer receipt，不接受 −1 手报四查 wrapper。
- **产物 allowlist**：逐件登记路径/字节/sha256（大文件分片哈希＋复用采集侧行数/区间校验，不收尾全盘重哈希）/行数/schema/依赖。排除日志/临时库/含密钥文件（config.json 不入清单内容）。
- **状态机**：`READY | BLOCKED | PARTIAL | SUPERSEDED | BLOCKED_CEX_GATE`——只有 READY 可被 −2 消费；READY 前置＝五件契约 JSON＋accounting_mode.json＋supply_truth.json＋wave_scan_report.json＋flow_anomaly_report.json＋distribution_scan.json 齐全（EVM 家族链另加 time_spotcheck.json）。verify 会调用分布扫描器重算 initial 语义。手改 manifest、scan 或排除来源都不能通过。
- **生成纪律**：原子生成（tmp+rename）、不含自身哈希；generate 后新增产物走 `late_additions`（重跑 generate 产 superseding manifest，旧件自动归档带 run_id 后缀）。

### 2.3 sealed 密封纪律（防锚定）

- 位置：案目录 `sealed/` 子目录＋`.sealed` 后缀＋文件头警示行（"−2 实体冻结前禁读"）；manifest 只记哈希不记内容。
- **−2 禁读令**：entity_freeze.json 落盘前，−2 禁止读取 sealed/ 下任何文件（`--check-unseal` exit 0 才准读）。
- 冻结后读取的用途＝**差异靶单**：sealed 观察与 −2 独立结论的分歧点进 A4 复核靶单——**它只是靶单不是证据、不算复核路数**。
- 隔离非技术强制（macOS 无可靠文件访问审计），靠命名警示＋条文＋−2 交付时自查申报三层（复盘已改为仅用户要求时跑，自查申报不再挂复盘，改挂 A5 交付）；残余风险如实承认。

## §3 −2 判断段（A3 判断层 ＋ A4–A5；A6 复盘仅用户要求时）

### 3.1 开工序（八步，顺序执行，写死进 /token-analyze-2）

1. **模型自检**：非 Fable/主力判断模型 → 警告（不硬停）。
2. **`handoff_manifest.py verify` fail-closed**：文件齐＋哈希对＋语义验证（gate exit 码与状态重查、schema 版本兼容、状态必须 READY——BLOCKED/PARTIAL/BLOCKED_CEX_GATE 一律 exit 2 拒收）。旧版 skill 产的 −1 目录（data_map 哈希带 `sha256:` 前缀、candidate_universe 条目只有 `cid`、anchor_plan 无 kernel receipt，APU 案 ANOM-012 实证）先跑 `scripts/report/migrate_legacy_case.py --case-dir <案目录>` 官方迁移，禁止手拼；anchor receipt 缺失只能用现行 anchor_plan.py 重跑补产，不可补票。
3. **数据保鲜检查（用户定稿口径）**：默认按已有数据跑（cutoff 即分析截止点，报告如实标注数据时点）；仅当 cutoff 距今缺口 **>72h** 才弹警报，AskUserQuestion 停等用户确认是否拉取缺口段——确认拉取则增量拼接、重跑受影响 gate 与候选门槛、产 superseding manifest；用户选按原数据继续则裁决记入 anomalies 后照跑。**绝不自动拉取。**
4. **必读件**：anomalies.json、四查结论、accounting_mode、点名式 CEX 黑箱关卡结论（若有）。
5. **候选覆盖自检（防 candidates 锚定）**：用重放产物独立重算阈值榜单/历史越线/归零/静置清单，比对 candidate_universe 无缺漏才继续；发现缺漏记 anomalies 并补入。
6. **data_map 当索引按需读盘**（禁整读大产物）；candidate_screening 当裁决工作台。
7. **sealed 禁读令生效**（§2.3）。
8. −2 中断续跑沿用 context-discipline 断点恢复五步。

### 3.2 判断主序

casebook C/E 册过闸 → 聚类合并裁决 → 临时实体 → **ET-2 无下限成员完整性扫描** → **EF-3A/EF-3B 候选进入 EF-3C 裁决与溯源闭环** → `handoff_manifest.py freeze` 校验 **EF-3C-P1～P4**，并在存在 `distribution_adjudications.json` 时绑定当前分布裁决 → G8 identity_gate_v3 → 判级 → 阵营演变重放 → A3 落 findings/facts/analysis-state/identity → A4 register/finalize 产 `a4-seal/v4` → final 分布扫描写 `dist_rounds/round_N/` → 新簇回流 A4；已覆盖异常跑解释五判据，未解释进入成员或机制闭环后回流 A4 → 唯一终态物化 `charts/final/holder_distribution_current.png` → `a5-report-seal/v3` → G11 → A5。两轮仍未终态时必须让用户选择第三轮或标准 waiver。A6 仅用户要求时执行。

### 3.3 A4 外部异构路收紧条款（分段模式专属，兼容 codex 侧 c1.1.0 禁自审令）

外部异构怀疑者（research-workflows §2 那一路）在分段模式下必须满足：
- **全新、无 −1 对话上下文的 codex 会话**；
- 输入＝原始数据路径＋冻结 manifest＋claim registry；
- **不给 sealed 观察文件、不让它复核自己 −1 的产出物本身**（数据完整性由 −2 verify＋四查兜底，数据层疑点由 Claude 怀疑者路负责）;
- 该调用只存在 CC 侧流程，codex skill 不新增任何自调复核入口。

## §4 验收与回退

- **首战合并验收指标（分段引入组）**：①verify 一次通过 ②−2 缺件回头补采次数（目标 0）③needs_adjudication 规模实测 ④−2 峰值上下文（目标 <20 万）⑤sealed 违规读取（目标 0，−2 交付时自查申报）⑥保鲜警报触发与用户裁决记录是否顺畅 ⑦候选覆盖自检缺漏数（目标 0）。与 v6 骨架组四指标分开归因。
- **回退**：CC 侧 revert 6.1.0＋删两个命令分发文件即可，单会话命令原样在。**数据零浪费**：−1 产物即标准采集/对账产物，弃用分段时单会话分析流程按"既有采集产物复用"直接接续——最坏结果也只是提前完成一轮标准采集/对账。
