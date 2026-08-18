# 批 A 工单｜split-run 三段化：权威文档＋命令＋契约原子批（v6.50.0 工程）

> 执行者：codex（workspace-write）。工作目录：`/Users/uravvv/.claude/worktrees/tca-splitrun3`（分支 fix/splitrun3-20260818，基线 main=e1be99a/6.48.1）。
> 你只改本工单白名单内的文件；白名单外任何文件被改动＝违规。**不 commit**（裁判代 commit）。
> 本工单给出的【定稿文本】逐字落盘，不得改写措辞（防口径漂移是本工程的核心要求）；给出【改动要点】的部分按要点成文，保持原文件风格。

## 白名单（本批可改文件，共 8 个）

1. `commands-staging/token-analyze-3.md`（新建）
2. `references/split-run.md`
3. `commands-staging/token-analyze-2.md`
4. `commands-staging/token-analyze-1.md`
5. `SKILL.md`
6. `scripts/tests/contract_manifest.json`
7. `scripts/tests/contract_ids_snapshot.json`
8. `scripts/tests/test_commands_deploy_sync.py`、`scripts/tests/test_repair_batch3_gates.py`（测试常量与 fixture）

## 五栏

**① 不变量**：(a) split-run.md 既有 10 条契约 needle 逐字存活（清单见验收）；(b) token-analyze-2.md 的 4 条契约（required `三问一异常`/`a5-report-seal/v3`，banned `三问框架`/`A5 seal v2`）改后仍成立；(c) SKILL.md ≤8192 bytes；(d) contract_manifest 与 contract_ids_snapshot 双向精确相等；(e) −1/−2 既有语义零变更（只扩容不改既有规则），唯一语义变更点＝停止线拆分与 −2 收口点前移，均以本工单定稿文本为准。

**② 同族清单**（施工前逐条跑，结果记录进 done 报告）：
```
rg -n "A4–A5|A4-A5" SKILL.md references/split-run.md commands-staging/   # −2 范围旧口径出现点，全部按定稿处理
rg -n "四入口" SKILL.md scripts/tests/                                    # 确认无契约/测试锚定后改五入口
rg -n "大户报警深挖" references/ commands-staging/                        # 应恰两处（split-run:56、token-analyze-1:13），同步拆分
rg -n "token-analyze-1|token-analyze-2" scripts/tests/*.py               # 命令名硬编码出现面，判断是否需同步 token-analyze-3
```

**③ 三件套测试（文档工程适配版）**：
(a) 先红后绿实证：新契约 3 条先落 manifest＋snapshot、`commands-staging/token-analyze-3.md` 尚未创建时跑 `python3 scripts/tests/docs_lint.py --all` 必须红（required needle 无宿主文件）——把这次红的输出片段记进 done 报告；创建命令文件后复跑转绿。
(b) 同族变体：`test_repair_batch3_gates.py` 为 −3 补四类负例（见 T8），与既有 −2 负例等深。
(c) 失败分支：负例必须实际跑红（fixture 内部断言），不许只写不跑。

**④ 新建代码自审**：token-analyze-3.md 与 §3b 按六视角①②自查——所有"自检/核对"步骤是否都写明了失败时的去向（停下报用户/退回 −2），有没有静默继续的分支。

**⑤ 归因预判**：本批为新功能引入；风险集中在 needle 误删（历史漂移三型之一）与 SKILL.md 超字节。

---

## 施工任务（按序执行）

### T1｜新建 `commands-staging/token-analyze-3.md`——【定稿文本，逐字落盘】

```markdown
---
description: 分段执行·装配段（−3）：消费 −2 装配工单跑 A5 装配（三图＋流转图＋a5-report-seal/v3＋build_html G11＋发布闸），完成即停（适配 Opus 执行）
argument-hint: <代币名或合约地址> full [补充信息]
---

调用 token-chip-analysis skill 的**分段执行·装配段（−3）**，标的与档位：**$ARGUMENTS**（档位只支持 `full`，缺失或不符时先问我）

唯一权威源＝`references/split-run.md` §3b，逐条照做，硬性要点：

1. **模型自检**：本段设计给 Opus 执行（省判断模型额度）；检测到自己是 Fable/主力判断模型 → 提示"装配段建议换 Opus 会话"后继续（不硬停）。
2. **装配工单检查**：案根 `a5_assembly_workorder.json` 在场且可解析；缺件即停，提示先跑 −2 收口，禁自造工单。
3. **A5 链前置产物自检（只读核对，禁重造禁补票）**：a4_seal.json（a4-seal/v4 且 PASS）＋报告.md（sha256 与工单一致）＋distribution_rounds.json 已到唯一终态＋charts/final/holder_distribution_current.png 已物化＋facts.json 与 analysis-state.json 在场；任一缺失或漂移 → 停下报我裁决退回 −2，禁带病开工。
4. **执行序（split-run §3b.4）**：fig1（figures_from_facts.py fig1 从 state 直出，overlay 按工单）→ fig2（按工单 required_entity_ids 装配 whale_series.json **落案根**，figures_from_facts.py check 产 figure2_check_receipt 后出图）→ fig3（按工单 events 清单出图）→ 流转图逐张按工单 spec 指针 figures_from_facts.py flow 渲染 → 报告图片引用三方核对（工单有序清单／报告 IMG 正则重取／实产文件，三方精确一致）→ a5_report_seal.py 产 `a5-report-seal/v3` → build_html --mode analysis-new 过 G10/G11 与发布闸 exit 0。输出一律限 `charts/final/`，禁写案外路径。
5. **修错循环三分类**：图渲染/路径/receipt 类红灯 → 自修重跑；报告.md 的逐字模板句或图路径字符串错 → 最小机械修正并逐条记工单 amendments 哈希链；**涉及数字/实体名/结论措辞的改动一律停工退回 −2**。
6. **收工**：报 G11 与发布闸结果＋交付自查申报（图 2 实体线=工单 required 清单、流转图张数=工单 eligible 清单、amendments 全记录），完成即停；A6 复盘仅我明确要求时执行。
```

注意：文件全文不得出现 `A5 seal v2`、`三问框架` 字样；不得出现形如 U0～U6、E0 的独词缩写（docs_lint 禁词正则）。

### T2｜`references/split-run.md` 逐处修改

**T2.1（:1 标题＋:3）**：标题改为 `# 分段执行手册（split-run：−1 机械段 / −2 判断段 / −3 装配段）`；:3 权威声明句中"−1/−2 边界"改"−1/−2/−3 边界"。

**T2.2（:4 命名纪律）**：在 `stage1_mechanical / stage2_judgment` 后补 ` / stage3_assembly`；"展示层叫 **−1 / −2**"改"展示层叫 **−1 / −2 / −3**"。

**T2.3（:9 本册路由）**：改为 `- §0 会话流；§1 −1 机械段；§2 handoff；§3 −2 判断段；§3b −3 装配段；§4 验收与回退。`

**T2.4（§0 会话流图，:13-18）**：代码块内追加两行（在"跑 /token-analyze-2 <币> full"行之后）：
```
        ↓ −2 判断收口：报告正文成稿＋产 a5_assembly_workorder.json，完成即停
用户手动新开 Opus 会话（CC），同目录跑 /token-analyze-3 <币> full（A5 装配）
```

**T2.5（:20 拆分线 bullet）**：改为"−1＝A0–A2 全部＋A3 机械子层；−2＝A3 判断层＋A4/A4.5＋报告正文成稿＋装配工单（A6 复盘仅用户明确要求时）；−3＝A5 装配（三图＋流转图渲染＋双 receipt＋seal＋HTML＋发布闸）"。动机排序句补第三条：`③装配段是机械渲染与编译循环，独立会话执行不烧主力判断模型额度（成本收益）`。

**T2.6（:45 §1.3 A3 机械子层第 3 项尾部）**：在"（批量层跑满是防"候选海"倒灌 −2 的第一道闸）"后追加【定稿文本】：
`对四通道报警地址，就地产 ET-1 证据采集包：分母＝报警地址的保守超集（−1 阶段无最终"其他大户"集合，宁多采不漏采），逐址采资金源/gas 注资/互转边/对手方清单，只记观察事实零定性，落 et1_evidence_packs.json；该件为 optional 产物，存在时必须经 generate 纳入 manifest allowlist 并登记 data_map 与 stage1_receipts（防交接后被改写）。归属定性深挖仍归 −2。`

**T2.7（:56 §1.4 停止线）**：清单中"大户报警深挖"改为"大户报警**归属定性**深挖"；本行末追加一句：`报警地址的证据采集（观察事实层）属 §1.3 第 3 项范围，可做。`

**T2.8（§2.1 产物表）**：表中追加两行（放 `wave_scan_report.json` 行组附近，格式对齐既有行）：
```
| `et1_evidence_packs.json` | −1 | ET-1 报警地址证据采集包（观察事实零定性；optional，不进 READY 前置；存在即入 manifest allowlist＋data_map） |
| `a5_assembly_workorder.json` | −2 | A5 装配工单（§3b；非正式件、无 validator、不进 handoff manifest；−3 消费） |
```

**T2.9（:113 §3 标题）**：改为 `## §3 −2 判断段（A3 判断层 ＋ A4/A4.5 ＋ 报告正文；收口＝装配工单；A6 复盘仅用户要求时）`。

**T2.10（:128 §3.2 主序）**：两处改动——
(a) 在"casebook C/E 册过闸"前补一句（作为 §3.2 首句）：`实体冻结后与 −1 的 et1_evidence_packs.json（若在场）双向对账：最终其他大户集合缺谁补谁。`（若行文更顺可放冻结步之后，语义不变。）
(b) 主序尾部自"唯一终态物化 `charts/final/holder_distribution_current.png`"之后改为：`→ 报告正文（报告.md 含附录文字）亲笔成稿 → §3b.3 收口自查 → 产 a5_assembly_workorder.json 即停。A5 装配（`a5-report-seal/v3` → G11 → 发布闸）归 −3，本段不画三标准图、不跑 seal、不编 HTML。两轮仍未终态时必须让用户选择第三轮或标准 waiver。A6 仅用户要求时执行。`
⚠ needle 保全：`holder_distribution_current.png` 与 `a4-seal/v4` 必须在改后文本中逐字存活。

**T2.11（§3.3 之后新增 §3b）**——【定稿文本，逐字落盘】：

```markdown
## §3b −3 装配段（A5 装配执行；消费 −2 装配工单）

### 3b.1 范围

−3＝A5 的装配执行侧：三张标准图＋流转路径图渲染、fig1_legend_receipt.json 与 figure2_check_receipt.json 双收据、a5_report_seal.py（`a5-report-seal/v3`）、build_html.py --mode analysis-new（G10/G11＋发布闸）及其修错循环。报告正文与全部判断性选材归 −2；−3 是纯机械渲染与编译会话（建议 Opus 执行）。−2 内其余机械环节的外包按 context-discipline 刀 1 公告（唯一权威源），本册不复制清单。

### 3b.2 装配工单（a5_assembly_workorder.json 字段约定）

案根 JSON，−2 收口时由判断执行者亲笔写（选材是判断产物，不设模板脚本）。非正式件：无 schema 版本、无 validator、不进 handoff manifest。字段约定：

- `note`：固定声明"非权威中间产物，兜底边界见 split-run §3b.5"；
- `meta`：case_id／token／chain／contract／cutoff／produced_at_utc／producer（值 stage2_judgment）／workorder_version；
- `bindings`（知情性绑定，−3 比对到漂移即停问用户；拒收权在 seal 链）：report_md{path,sha256}（此即 −2 原稿锚，永不覆盖）、a4_seal_sha256、entity_freeze_revision、distribution_terminal{status,round_n}、facts/state/rounds/终态分布图各自 path＋sha256、价格源 path＋sha256 及双源检查结果；
- `report_image_refs`：报告正文引用图片的有序清单（保留重复次数）；
- `fig1`：state 路径／price_csv（或 null）／overlay 判断选材／out 文件名；
- `fig2`：required_entity_ids ＋逐线 {entity_id, 展示标签, 序列源 path＋key＋sha256, 时间范围} ＋price 源＋out；
- `fig3`：events 判断清单（日期/标签/序号）＋price、volume、events 输入各自 path＋sha256＋granularity＋out；
- `flow`：eligible_entity_ids（−2 按判级结果列出的流转图门槛实体全集）＋逐张 {entity_id, spec 路径指针＋sha256, out}；两清单必须双向相等；
- 路径围栏：所有输入须为案内普通文件（拒 symlink），输出仅限 charts/final/ 下的 png；
- `stage2_selfcheck`：−2 收口自查申报（§3b.3 四条＋刀 1 公告遵守申报）；
- `amendments[]`：−3 机械修正哈希链，每条 {before_sha256, after_sha256, 触发的闸报错, exact_change}；中断恢复以最后一条 after_sha256 为报告.md 当前合法状态。

### 3b.3 −2 收口自查（写工单前四条，逐条核对）

①报告图片引用与工单 report_image_refs 一致，且终态分布图 charts/final/holder_distribution_current.png 在正文恰引用一次；②分布终态固定句式按 status 逐字核对 a5_report_seal.py 的三条句式常量（正常形态句／检出畸形句／样本不足句）；③存在已确认 provenance 翻转时，报告含完整披露章节（三策略＋终点标识＋份额）；④报告.md 的 sha256 写入工单 bindings。

### 3b.4 −3 执行序与修错三分类

执行序：fig1 → fig2 → fig3 → 流转图逐张 → 图片三方核对（工单有序清单／报告 IMG 正则重取／实产文件）→ a5_report_seal → build_html。要点：

- whale_series.json 必须落案根：figure2_check_receipt.json 落在 --series 参数所在目录，而发布闸只认案根，放错目录会导致 check 通过但 G11 缺件。
- 图 2/图 3 无独立 CLI：standard_charts.py 是库。现场 Python 调 plot_whale_vs_price(whale_series, price_series, out_png, token) 与 plot_price_events(price_series, volume_series, events, out_png, token, granularity)，全部参数从工单声明的源文件读取装配，禁手抄数字、禁自由发挥选材。
- 输出一律写 charts/final/，禁写案外路径。

修错三分类：①图渲染/路径/receipt 类红灯 → 自修重跑；②报告.md 的逐字模板句或图路径字符串错 → 最小机械修正＋amendments 哈希链留痕；③涉及数字/实体名/结论措辞 → 一律停工退回 −2。

### 3b.5 兜底声明（诚实边界）

既有 A5 链闸（a5_report_seal／build_html／audit_release_gate，全 fail-closed）验证的是已引用资产的完整性与漂移：a4 revision 链、分布终态链、图实物、facts/state 绑定、终态图唯一引用、固定句式。不覆盖：图表应有基数（少画图仍可能过闸）、fig2 实体线覆盖完整性（figure2_check 只验已提供的线）、渲染输入与 check 输入的同一性、工单字段完备性——这些由工单字段约定＋−3 自检＋交付自查申报承担，属用户已接受的残余风险（不设 validator 系用户 2026-08-18 拍板；首战后评估是否升级）。
```

**T2.12（:141 §4 回退）**："CC 侧 revert 6.1.0＋删两个命令分发文件即可"改为"CC 侧 revert 对应 commit＋删三个命令分发文件（token-analyze-1/2/3.md）即可"；§4 验收指标清单追加：`⑧−3 前置自检一次通过（报告 sha 与图清单零漂移） ⑨−3 对正文机械修正次数与 amendments 申报完整性`。

### T3｜`commands-staging/token-analyze-2.md` 三处

- :2 description 改为：`分段执行·判断段（−2）：verify fail-closed 后接 A3 判断层＋A4/A4.5＋报告正文，收口于装配工单（Fable 冷启动，消费 −1 交接契约）`
- :17 第 8 步主序尾部：自"唯一终态才物化 `charts/final/holder_distribution_current.png`"之后改为 `→ 报告正文亲笔成稿＋§3b.3 收口自查 → 产 a5_assembly_workorder.json 即停；A5 装配（`a5-report-seal/v3` → build_html G11 → 发布闸）归新开 Opus 会话跑 /token-analyze-3 <币> full`。两轮终态句与 A6 句保留。
- :19 改为：`三问一异常框架与铁律 7 条全程有效（同 /token-analyze）；只支持 full 档；本段交付＝报告正文＋装配工单，HTML 由 −3 编译；监控包默认不生成。`
⚠ 全文四条契约核验：`三问一异常` 与 `a5-report-seal/v3` 逐字在；`三问框架` 与 `A5 seal v2` 不出现。

### T4｜`commands-staging/token-analyze-1.md` 一处

:13 停止线句与 split-run :56 改后逐字等深：清单中"大户报警深挖"→"大户报警**归属定性**深挖"，行末追加 `报警地址证据采集（观察事实）按 §1.3 第 3 项执行可做。`（:10/:16 不动。）

### T5｜`SKILL.md` 三处（:23 版本注释归批 C，本批不动）

- :58 `## 四入口` → `## 五入口`
- :62 改为：`- **/token-analyze-2**：handoff verify 后接 A3 判断层＋A4/A4.5＋报告正文，收口于装配工单；仅支持 full。`
- :62 之后插入新行：`- **/token-analyze-3**：消费 −2 装配工单跑 A5 装配（图/seal/HTML/发布闸）；建议 Opus 会话，A6 仍须用户要求。`
- :68 "split-run −1/−2 先读" → "split-run −1/−2/−3 先读"
⚠ 改完立刻 `wc -c SKILL.md`，必须 ≤8192；超了先压 :62/:63 措辞（禁动 :52-56 契约 needle 段），仍超则报告停工。

### T6｜`scripts/tests/contract_manifest.json` 新增 3 条

对照文件内既有条目的字段格式（严格五字段 id/kind/authority_file/needle/stages，多一字段即 lint FAIL），在恰当位置插入：
- `CT-SEMANTIC-61`｜required｜`commands-staging/token-analyze-3.md`｜needle `a5-report-seal/v3`｜stages ["A5"]
- `CT-SEMANTIC-62`｜required｜`commands-staging/token-analyze-3.md`｜needle `G11`｜stages ["A5"]
- `CT-BANNED-16`｜banned｜`commands-staging/token-analyze-3.md`｜needle `A5 seal v2`｜stages ["A5"]
kind 字段的实际取值以文件内既有 required/banned 条目为准照抄格式。

### T7｜`scripts/tests/contract_ids_snapshot.json` 同步

按文件既有排序规则插入三个新 id，保证与 manifest ID 集合双向精确相等。

### T8｜两个测试文件

- `test_commands_deploy_sync.py:17-21`：EXPECTED 集合加 `token-analyze-3.md`（RETIRED 不动）。
- `test_repair_batch3_gates.py`：
  - :21 COMMANDS 三元组加 `token-analyze-3.md`；
  - seed_commands（:82-86 附近）contents 加 `"token-analyze-3.md"`，内容极简且满足契约（含 `a5-report-seal/v3` 与 `G11`，不含 banned 词）；
  - fixture 的合成 contract manifest 若只含 −2 契约，补 −3 的 required/banned 三条同构条目；
  - 为 −3 补四类负例（对照既有 −2 负例结构复制改造）：①deployed 缺 token-analyze-3.md；②SHA 不一致；③required needle（a5-report-seal/v3）从 staging 版删除后应 FAIL；④banned needle（A5 seal v2）注入后应 FAIL。每个负例实际执行并断言红。
  - 测试内注释/文案里"三文件/三命令"字样同步为四。

---

## 验收命令（全部通过才算本批完成；把每条输出摘要记进 done 报告）

```
cd /Users/uravvv/.claude/worktrees/tca-splitrun3
python3 scripts/tests/docs_lint.py --all
python3 scripts/tests/test_repair_batch3_gates.py
python3 scripts/tests/test_contract_routes.py
wc -c SKILL.md
rg -c "wave_scan_report.json" references/split-run.md && rg -c "flow_anomaly_report.json" references/split-run.md && rg -c "EF-3A/EF-3B" references/split-run.md && rg -c "EF-3C" references/split-run.md && rg -c "provenance_ledger.json" references/split-run.md && rg -c "distribution_scan.json" references/split-run.md && rg -c "handoff/v3" references/split-run.md && rg -c "holder_distribution_current.png" references/split-run.md && rg -c "a4-seal/v4" references/split-run.md
rg -c "a5-report-seal/v3" commands-staging/token-analyze-2.md commands-staging/token-analyze-3.md
rg -c "G11" commands-staging/token-analyze-3.md
rg -c "三问一异常" commands-staging/token-analyze-2.md
rg -n "三问框架|A5 seal v2" commands-staging/ && echo "BANNED HIT!" || echo "banned clean"
```
注：`test_commands_deploy_sync.py` 本批**预期红**（staging 已改、部署 cp 在批 C 末），不跑、不修。
`EF-3C-P1～P4` 计数并入 `EF-3C` 检查（前者包含后者）。

## 完成标准

八文件改动全部落盘；验收命令全绿（除声明的预期红项）；先红后绿实证（③a）已记录；done 报告写 `maintenance/repair-20260818-splitrun3/batchA_done.md`（改动清单/验收输出摘要/先红后绿证据/发现的问题）。**不 commit。**
