# CHANGELOG — token-chip-analysis（活跃窗口）

版本规则（v3.0 起两维制，详见 references/retrospective.md「版本号约定」）：
- **skill 版本**：主=架构级重构；次=每次**分析复盘**迭代 +1；修=文档小修
- **labels 数据版本**：标签库扩容/重建记 `labels vX.Y` 前缀条目，不再占用 skill 次版本号
红线：条目只记工具性知识（数据源/坑/方法/脚本），禁止记录任何代币的分析结论。
每条迭代条目附成本指标（轮次数/Bash 调用数/交付用时）+ 质量指标（初稿关键结论数/复核判定分布/漏检实体数/传播级数字错误数，v3.0 起，见 retrospective 步骤 1）。
**写入前必跑 `python3 scripts/tests/changelog_lint.py`**（防撞号/倒排——两者都实际发生过）。
本文件只保留最近 ~10 版（整编时滚动）；更早的完整迭代史在 `archive/CHANGELOG-archive.md`，考古规则来源先 grep 该文件。

## 版本索引（活跃窗口，新在上；每版一行，详情见下方对应条目）

- **6.29.0** 2026-08-05 第二轮修复工程第 4 步：canonical 契约注册表与 SKILL 二级路由
- **6.28.0** 2026-08-05 第二轮修复工程第 3 步：现役文档案例史迁出、casebook 六字段收敛、报告管道与旧阶段名修正、CHANGELOG 活跃窗口兑现、确认死物删除
- **6.27.0** 2026-08-05 Arbitrum 降为探索支持：
  正式编译全链拒绝，正式链声明/发布闸/标签能力三向闭合守卫
- **6.26.0** 2026-08-05 三项 P0 活故障修复：手工标签唯一真源与 suite 守卫、A3 依赖序统一、既有报告净室复核入口补齐
- **6.25.0** 2026-08-05 references 长行保序拆分（瘦身第 6 步）：30 条语义断行，3 条 Markdown 表格行按结构约束保留
- **6.24.0** 2026-08-05 零引用脚本归档与 Solana gas 双实现合并（瘦身第 5 步）：gas_origin 单入口保留限页/全量双模式与字段闸
- **6.23.0** 2026-08-05 深入阅读清单 manifest 化（瘦身第 4 步）：现役路由与维护文档双向对账，维护件不再被 lint 强迫进入口
- **6.22.0** 2026-08-05 archive/ 考古区分层（瘦身第 3 步）：旧 CHANGELOG、评测题库与已闭环冲突审计快照退出执行路由
- **6.21.0** 2026-08-05 数据管线两册案例史外移与重复合并（瘦身第 2 步）
- **6.20.1** 2026-08-05 修 5 处阻断级文档漂移（A4 前禁写报告冲突/easy 残留/惯犯回灌 docstring/批量预采集残留/旧 Par 路线历史降级）＋docs_lint 增中文禁词与 Python module docstring 扫描
- **6.20.0** 2026-08-05 持仓分布形态硬闸：五桶分账、双分箱统计、头部集中度、小样本模式、A4 回流轮次链与 A5 报告封口全链落地

更早版本（6.19.0 及以前）详见 `archive/CHANGELOG-archive.md`。

## [6.29.0] - 2026-08-05 — 第二轮修复工程第 4 步：契约注册表与二级路由

- **R-02 canonical contract manifest**：把原 `docs_lint.py` 五组 85 个 `(文件, needle)` 对逐根分类为 76 个权威 needle 与 9 个报告 checklist 复述 needle；新增 `contract_manifest.json` 作为稳定契约 ID、权威路径、适用阶段和语义的单点注册表。lint 改为验证权威路径/needle 与全库 Markdown 契约引用，报告复述层收敛成摘要＋契约 ID，不再把复制长句固化为发布条件。
- **R-01 SKILL 二级路由**：深入阅读段只保留全流程、分段、净室复核、三链主册、A3/A5/A6、标签和环境入口；`runtime_docs_manifest.json` 升 v2，为每份现役文档登记入口归属和阶段，并由机器验证 `SKILL.md → 入口 → 分册` 两跳可达。SKILL.md 其余执行语义不变，尺寸保持在 8192B 内。
- **反例与验收**：新增 `test_contract_routes.py`，覆盖删除权威 needle、悬空契约 ID、权威路径不存在、manifest 幽灵条目和入口删引用导致孤儿五类负向输入；全量 SUITE 51→52 项，三个 pre-commit 守卫与全量 suite 均须通过。
- **验收加固（Fable，同日）**：攻击式验收发现第六类负向未关——真实 `contract_manifest.json` 的条目可被静默删除（lint 只查在表契约的权威在场，不守表自身完整性；与旧版硬编码等强度但更易被"顺手清理"）。`test_contract_routes.py` 增真实注册表基线：条目数 ≥76＋五组首根锚 ID 在场，删条目/删整组立红；红绿反证复现通过。另程序化对账：旧 lint 140 根 needle=76 入表＋9 报告复述取消（权威等价物逐根在场，其中低样本披露句由 `a5_report_seal.py` 代码闸强制）＋55 根其他检查组原样未动，无静默丢失。

本次为工具工程，无代币分析轮次或结论质量指标；权威 needle 76→76，复述强制 9→0，SKILL 深读平铺分册 32→二级入口 11。

## [6.28.0] - 2026-08-05 — 第二轮修复工程第 3 步：瘦身主体

- **R-04/R-05**：八份现役文档迁出案例史；casebook 全条目收敛为六字段，S-04 保留 12 个触发场景与回归指纹，升级返工史原样归档；methods B 类判例一次性迁入 C/E/S 续册（README 登记为只出不进的迁移特例，日常"不拆新册"纪律不变）。
- **P1-01/P1-02**：报告管道改为 A4 finalize 后 A5 一次物化 `charts/final/`；清理旧阶段名、旧 schema 名和幽灵脚本名，不改执行逻辑。
- **CHANGELOG/死物**：活跃窗口收至最近 10 版，旧版本块与撞号注记原样归档；删除获批的 pycache、根层重复 curation 文件和旧根层 manual_labels.csv，保留构建流输入与现役生成物。
- **验证**：casebook/docs/changelog/manual-sync/version 与全量 suite 均纳入发版验收。
- **验收返工（Fable，同日）**：修三处交付硬伤——README"不拆新册"与三续册的规则矛盾（改为登记迁移特例并只出不进）；E 续册 SIREN 判例内"详见本文件「层数封顶原理」"随迁移失效的指针（改指 methods 现役段名）；address-book 指向 casebook E-14 的错误判例指针（该判例不存在，删句留规则）。迁移原样性经程序化对照：7 文档 96 实质行迁出全部原样命中迁入地，判据数字集合 75/75 零丢失，旧归档 104 版本块零改动。

## [6.27.0] - 2026-08-05 — 第二轮修复工程第 2 步：Arbitrum 降为探索支持

- **支持矩阵纠偏**：正式深度管线移除 Arbitrum，现役路由与 EVM 手册明确其只保留探索档；
  采集、对账、identity snapshot receipt 与 G8 生成/校验能力不删除。降级原因固定为
  `labels-arbitrum.csv` 缺失，目标链设施剔除与合并拦截无法按正式口径闭合。
- **正式轨 fail-closed**：`audit_release_gate` 统一正式链集合与错误语义；A4 finalize 绑定
  state/G8 链并写入 seal，revision 链拒绝链漂移；A5 seal 绑定 A4 链；`build_html` 的
  `analysis-new` / `analysis-audit` 在正式资产校验前拒绝 Arbitrum。探索档仍可重放存量数据，
  但不得产 A4/A5 seal 或正式 analysis。
- **三向闭合守卫**：`test_chain_support_matrix.py` 同时核对 SKILL frontmatter、release gate
  `FORMAL_CHAINS`、`build_labels.py` 构建集合，并逐链要求目标 CSV 存在且含数据、
  `LabelResolver` 非 degraded。受控回归把 Arbitrum 同时塞回三处旧声明后，守卫以
  `labels-arbitrum.csv missing, empty, or header-only` 阻断；还原后通过。

本次为工具工程，无代币分析轮次或结论质量指标；正式支持错配 1→0，
新增正式链回归测试 1 项，
全量 SUITE 50→51 项。

## [6.26.0] - 2026-08-05 — 第二轮修复工程第 1 步：三项 P0 活故障收口

- **P0-04 手工标签层漂移**：`address-book.md` 增机器可读规范区，生成器改为确定性解析唯一人工真源；18 个差异逐址裁决为 16 个运行时标签＋2 个带独立理由的 record-only 豁免，9ZPsR 币安 Alpha 库存仓恢复命中。`check_manual_sync.py` 改为逐行生成物校验＋地址集合双向闭合，并作为第 50 项正式进入 `run_all.py`；resolver 注释同步实际生成链。
- **P0-02 A3 依赖序统一**：`analyze-workflow.md` 对齐 `split-run.md` §3.2，把 casebook、聚类裁决、临时实体、ET-2、EF-3、EF-1/2、freeze、G8、判级/ET-1、阵营演变和 A3 落盘按产物依赖重排；当前持仓分布初判保持在 EF-3A/B 后，代码 gate 输入契约不变。
- **P0-01 净室复核入口**：SKILL 路由增加自然语言复核既有报告入口；`analyze-workflow.md` 固化唯一权威分流，共用 A0–A2 采集对账骨架，A3 起走 `independent-audit-protocol.md`，A5 只用 `build_html --mode analysis-audit`。

本次为工具工程，无代币分析轮次或结论质量指标；缺陷验收为手工层漏同步 18→0、复核入口 0→1、全量 SUITE 49→50 项且全部通过。

## [6.25.0] - 2026-08-05 — references 长行保序拆分（瘦身第 6 步）

按 HEAD `9622798` 的唯一清单处理 17 份 references 文档中的 33 条目标长行：30 条在中文分号、句号、步骤箭头等自然语义边界插入换行与空格续行缩进，共 81 个断点；`references/report-template.md` L158、`references/address-book.md` L171、`references/data-pipeline-evm-channels.md` L229 为 Markdown 表格行，按结构约束不拆。每个修改文件均以去空白字符流和 HEAD 对比，结果零差异；判据、阈值、地址、路径、命令及 fail-closed 语义均未改变。

## [6.24.0] - 2026-08-05 — 零引用脚本归档与 Solana gas 双实现合并（瘦身第 5 步）

B 组两个全库零现役引用脚本退出执行目录，普通移动且不删除：`scripts/evm/trace_network.py` → `archive/scripts/trace_network.py`，`scripts/evm/fetch_fundedby.py` → `archive/scripts/fetch_fundedby.py`。两者除自身外只在历史归档中出现，无现役文档需要同步。

C 组 gas 双实现收敛为 `scripts/solana/gas_origin.py` 单入口，`scripts/solana/gas_fast.py` → `archive/scripts/gas_fast.py`。合并版保留 gas_origin 原有位置参数、`data/gas_origins.json` 累积格式、`first_txs` 与完整 `deltas`，并统一提供 gas_fast 的增强能力：`max_pages` 默认 2（沿用 gas_fast 实战校准值）、达到上限的超深地址标 `approx=true`、每笔继续输出 `sig/ts/my_sol_delta/funder`，目标 `my_sol_delta≈0` 时仍保留 fee payer funder 供先决字段闸裁决，RPC 429 显式退避；新增 `--full` 取消翻页上限，恢复 gas_origin 旧版一直翻到最老的全量行为，且会重查已有 `approx` 记录。实况核查发现 gas_origin 在本轮前已提前拥有默认 2 页、approx、my_sol_delta 与 deltas，本轮补齐剩余行为并正式移除双入口。

文档同步三处：`scripts/solana/README.md` 条目 10 改为合并版说明、删除 gas_fast 条目并将后续脚本序号 17–27 顺移为 16–26；`references/data-pipeline-solana-capture.md` 删除遗留 TODO，改为默认 2 页/approx/`--full` 已回填口径并保留 gas_fast 加固历史来源；`references/playbook-entity-cluster-methods.md` 的 my_sol_delta 判据仅把 `gas_fast/gas_origins` 权威脚本名替换为 `gas_origin/gas_origins`，其余判据、阈值与阻断语义不动。

审查后决定不动两项：①旧 Par 三件套 `fetch_hypersync_par.py`、`watchdog_dual.py`、`merge_parts.py` 原地保留，因为 `scripts/tests/test_review_medium_guards.py` 直接 import `fetch_hypersync_par.py` 的断点续传函数做守卫断言，移动会破坏现有防回退测试；②`scripts/solana/hypersync_recon.py` 原地保留，因为它是 HyperSync Solana 官方 GA 后的重验资产，且本就不在执行路由，移动没有上下文收益。

## [6.23.0] - 2026-08-05 — 深入阅读清单 manifest 化（瘦身第 4 步）

以 `scripts/tests/runtime_docs_manifest.json` 作为 SKILL.md 深入阅读清单的唯一事实源，落实 S-01 的仓库内解法：`references/*.md` 与 `references/labels/*.md` 每份文档必须先归入 `listed`（现役路由）或 `maintenance`（维护件），新增文档不再由旧反向漏列逻辑一律强迫进入 SKILL.md。

`docs_lint.py` 检查 4 改为 fail-closed manifest 守卫：JSON 解析、schema、scope、必需字段和数组结构任一异常即失败；磁盘实际集合与 `listed ∪ maintenance` 双向对账，未归类文档、幽灵条目及两类交集分别失败；`listed` 仍须按相对路径或文件名出现在 SKILL.md。`maintenance` 反向禁列，其中 `labels/MAINTENANCE.md` 无例外，`attic.md` 只允许保留一条含“禁读”的负向边界声明。全部失败信息携带 manifest 路径并提示“新增文档须先在 manifest 归类”。

当前闭合结果为磁盘 34 份 = listed 32 份 + maintenance 2 份，未归类/幽灵/交集均为 0。SKILL.md 的“标签/环境”入口移除 `labels/MAINTENANCE.md`，其余项目不动；`attic.md` 既有禁读声明原样保留。动机是让 SKILL.md 只路由现役文档，维护手册不再因 lint 反向检查被迫占用入口与上下文。判据、阈值与 fail-closed 分析语义零变更。

## [6.22.0] - 2026-08-05 — archive/ 考古区分层（瘦身第 3 步）

以仓库内 `archive/` 分区作为 S-02「拆两层包」的替代方案：历史资产仍随仓库保存、可维护和恢复，但不再参与执行路由；`archive/README.md` 明确执行会话与现役 references 文档禁读禁引用，资产恢复回现役必须留下 CHANGELOG 记录。判据、阈值与 fail-closed 语义零变更，评测题目内容零改动。

三组资产移动清单（旧路径 → 新路径）：
- `CHANGELOG-archive.md` → `archive/CHANGELOG-archive.md`
- `evals/` → `archive/evals/`
- `scripts/labels/sources/serial_conflicts_2026-07-22.json` → `archive/serial-conflicts/serial_conflicts_2026-07-22.json`
- `scripts/labels/sources/serial_conflicts_2026-07-22.md` → `archive/serial-conflicts/serial_conflicts_2026-07-22.md`
- `scripts/labels/sources/serial_conflicts_2026-07-25.json` → `archive/serial-conflicts/serial_conflicts_2026-07-25.json`
- `scripts/labels/sources/serial_conflicts_2026-07-25.md` → `archive/serial-conflicts/serial_conflicts_2026-07-25.md`
- `scripts/labels/sources/serial_conflicts_2026-07-26.json` → `archive/serial-conflicts/serial_conflicts_2026-07-26.json`
- `scripts/labels/sources/serial_conflicts_2026-07-26.md` → `archive/serial-conflicts/serial_conflicts_2026-07-26.md`
- `scripts/labels/sources/serial_conflicts_2026-07-28.json` → `archive/serial-conflicts/serial_conflicts_2026-07-28.json`
- `scripts/labels/sources/serial_conflicts_2026-07-28.md` → `archive/serial-conflicts/serial_conflicts_2026-07-28.md`
- `scripts/labels/sources/serial_conflicts_2026-07-29.json` → `archive/serial-conflicts/serial_conflicts_2026-07-29.json`
- `scripts/labels/sources/serial_conflicts_2026-07-29.md` → `archive/serial-conflicts/serial_conflicts_2026-07-29.md`

活引用同步：`CHANGELOG.md` 头部考古指针、`references/retrospective.md` 的 CHANGELOG 归档与题单维护路径、`references/casebook/README.md` 的候选题单路径、`scripts/tests/changelog_lint.py` 的 ARCHIVE 常量、`scripts/tests/docs_lint.py` 的全量评测扫描路径与归档豁免路径均指向新位置；`SKILL.md` 路由层新增考古区禁读边界。`scripts/labels/accumulate_offenders.py` 的活输出路径与 `references/labels/README.md` 规则保持不动，新冲突快照继续写入 `scripts/labels/sources/`。

`docs_lint.py` 新增考古区防回流守卫：现役 `SKILL.md` 与 `references/` 文档出现 `archive/` 路由引用即失败；仅维护记录、archive 自身、`references/attic.md`、`references/casebook/`、`references/retrospective.md` 豁免，另只允许 `SKILL.md` 的单行“执行会话禁读”边界声明，防止未来把考古资料重新拉入执行上下文。

6.21.0 遗留裁决闭环:methods 的 B 类 38 行判例,用户 2026-08-05 裁决放弃迁移 casebook、原地保留(S 册容量上限+必读到必读搬家净省有限)

## [6.21.0] - 2026-08-05 — 数据管线两册案例史外移与重复合并（瘦身第 2 步）

瘦身第 2 步（codex 按 Fable 验收通过的 111 条逐字引句盘点施工，Fable 逐项机器验收）：A4 复核强度配置与备择解释指引四处合一（analyze-workflow / evidence-wording / research-workflows 单一权威源化，40f88a0）；data-pipeline-evm-channels.md 与 data-pipeline-solana-capture.md 的 A 类战报子句与 C 类考古行外移至下方归档（两册净减 6,090 字节；现役参数/阈值/fail-closed/死亡名单/在役 fallback/守卫 needles 零变更；CH-53 Alpha 政策线与 CH-66 GMX 比例两条切出段含分析结论定性，按「CHANGELOG 禁记代币分析结论」红线停手留正文）。

批次 2——B 类 39 条方法级失败模式入 casebook（两册再净减 19,330 字节，正文原位换「权威短规则＋判例指针」43 处零断链）：S 册 4→7 条（S-04 扩为 12 场景覆盖盲区族＋新增 S-05 税币/毛流/曲线成本、S-06 时间边界、S-07 LP/TVL 归属）；E 册扩写 E-01/E-02/E-04/E-05/E-10/E-12；C 册扩写 C-01/C-04/C-06。三册 25.1KB→38.0KB（casebook_lint 26 条六字段全过）；既有条目判据语义逐行验证只增未改（50 处重写行 48 处前缀保留、2 处为插入新案源的假阳性）。执行过程 codex 进程三次中断，按「cancel+resume-last 蚂蚁搬家」分四段续跑完成。

批次 3——report-template.md 案例细节收敛（Fable 亲手盘点＋施工；codex 盘点任务两次进程中断后改自营）：规则全数保留，10 处行内案例细节压缩为短案源注（明细见下方归档），GMX 留存率设施污染案入 S-05（触发现象第④场景＋4.7%→34.8% 反转数字）；三账本分离宪法段、术语验收标准、比喻库、checklist 全部判定现役不动。

批次 4——playbook-entity-cluster-methods.md A 类拆句（Fable 亲手施工，按已验收 methods 盘点 57 条台账）：12 处行内案例数字/翻案过程压缩为短案源注（明细见下方归档），规则句、用户裁定记录（SPX6900 三次拍板等）与守卫锚点（① 候选发现档）逐字保留；B 类 38 行入册与否单列为用户裁决项（casebook 容量账见收尾汇报），本批不动。

#### report-template.md（批次 3 拆句归档）

- (原 L158) 图 1 混合重建图注纪律案源：GOAT 案末日封口 -12/+13pp 跳变仅解释了主实体的 2.8pp（外部复核抓出）；compose_evolution 读去重前发射窗致 LP 桶高估 0.83pp。
- (原 L162) KOGE overlay 实测：挂墙日账面 −75.9 万、同期池 +83.4 万、合计几乎不动。
- (原 L178) SIREN 流转图自解释验收：初版缺平行网四仓与卡片占比，用户对照正文仍"一头雾水"，返工 4 版才达标。
- (原 L187) SIREN 账目行加法自检：净出漏算四仓 15.2pp，被用户一个加法抓出。
- (原 L211) EGL1 宏口径边界：发射窗协同实体单笔买入 47.11% vs 日末峰值宏 40.21%，TL;DR 与正文两处误用。
- (原 L212) EGL1 序列末点纪律：散户残差手写 10.75% 实为 2026-01 中段值，末点真值 10.37%。
- (原 L261) SIREN 时区双标实锤：回测"UTC 凌晨 00:00~03:39 场内先崩"被用户对照 GMGN 图质疑"早上 9-10 点才崩"。
- (原 L271) GME 单一成员集合对账：verdict 摘曲线端数字把在场庄合计低估 1.21pct，增量更新旧账抽验才抓到。
- (原 L291) GMX 图例静默过滤：自定义名（"项目方·官方系""质押池（用户筹码）"等）传 8 阵营只画出命中标准名的 2 个（CEX托管/散户）。
- (原 L294) GMX 留存率设施污染明细：质押合约收 575 万枚、DEX 池收 173 万枚（判例正文入 S-05）。
- (原 L299) KOGE 阵营归属互斥：一个 2.867% 账户正文算进项目方注入、阵营表却归散户。

#### playbook-entity-cluster-methods.md（批次 4 拆句归档；规则句全数留正文并带短案源注）

- (原 L30) TROLL 中间判定污染细节：昨日中间判定的"Coinbase 托管分仓"被独立重做会话误当标签引用，恰是后来被翻案成小庄的四钱包（07-29）。
- (原 L56) SQD PoR 方法起源：Bybit PoR 2026-04-22 PDF 命中 3 址，直接把"疑似官方场外仓"实体翻案为 CEX 托管（07-20）。
- (原 L64) PUB 程序归属反转规模：13.57% 供应的"疑似 dev 系分仓"实为官方质押池（07-14）。
- (原 L95) BEGGAR 出纳名单战果：发现官方系隐性仓位 0.15%，利好日/风波日三次买入零卖出（07-17）。
- (原 L126) CASHCAT 两跳体检战报：132 址体检出 14 个合约，剔除后口径 21.9%→12.7%；96 址 53.97% 大集群清洗后拆为 40/15/5 三星座（07-13）。
- (原 L130) TROLL 截断地址双踩经过：主分析与一路复核 agent 均把 route JSON 截断串补全后空跑，靠空结果异常才暴露（07-29）。
- (原 L143) CASHCAT/NOXA 前缀补全事故：曾补出后 32 位全错地址险些进监控名单；LPT 手敲 TransferBond topic0 错一段扫出 0 笔（07-13/15/21）。
- (原 L152) TRASH 分仓贴线族明细：9 址协同族单址全部压 0.55% 以下，合并 3.69%（07-17）。
- (原 L173) meow 发射窗快闪客明细：头 60 秒项目方马甲 5.10%、金主同源闪电簇 5.06%（07-15）。
- (原 L177) SPX6900 同秒共现方法起源实测：53 仓 1378 对全扫唯二命中，双双被 first-funder/热钱包同源旁证坐实，一组合并后即发射窗真实第一大仓（07-25）。
- (原 L203) ASTEROID 半枢纽假簇数字：3367 址假簇按判据②剔边后 3367→136 正常长尾（07-18）。
- (原 L223) KOGE 同步动作分母检验数字：大庄取 800,000 枚、60 秒后项目方签名人取 300,000 枚，该三天全链 >50,000 枚转账仅此两笔，置换检验 p≈5×10⁻⁴。

### 战报与案史归档（自 data-pipeline-evm-channels.md / data-pipeline-solana-capture.md 外移）

#### data-pipeline-evm-channels.md

- (原 L17) HyperSync 官方客户端 v2 Rust 自动并发+Parquet 直写，实测 ~1 万条/s = 手写轮询 18 倍。
- (原 L20) SQD Portal 薄采集器实测 ~280 条/s。
- (原 L29) PING 案 uniqueId 双计 5485 负余额，促成集合级对账 fail-closed 防线。
- (原 L86) QUQ 完整版增量（07-22）：付费档实测 7 万块、2.3 万条仅 4s。
- (原 L107) HyperSync 官方客户端 v2 Starter 付费档 CAKE 实测 10,080 条/s。
- (原 L108) HyperSync v1：免费层 0.5s 间隔基本无 429（2026-07-18）；Starter 付费档 0.12s 间隔 429=0，单进程 552-792 条/s（ETH RTT~0.2s/BSC~0.6s）；免费层约 1000-1300 logs/2s、1568 万条约 5.2h，付费单进程 ETH 792 条/s、BSC 552 条/s（SIREN 07；哈基米 07-18；v3.11.2 07-21）。
- (原 L109) SQD Portal：CAKE 21,857 行/79s；BANANAS31(BSC) 四代表日 67,731 行六元组与 HyperSync 零差集全等（2026-07-22）。
- (原 L111) Alchemy getAssetTransfers 实测 ~46 万条/10 分钟。
- (原 L113) Etherscan V2 tokentx 7 万余行顺利拉完。
- (原 L114) envio HyperSync ETH 主网 0.25s 间隔仅 11 次 429、全部退避成功；139.9 万条 33 分钟单进程拉完，均速 ~700 条/s（ASTEROID，07-18）。
- (原 L153) 多会话共享 key 案史：SQD 案 83.2 万条 56 分钟、429×20 次全部自愈；LPT 案 eth+arbitrum 三进程并发时 arbitrum 429 密集，串行后恢复（SQD，07-20；LPT，07-21）。
- (原 L156) KOGE 案 82 个交易几十秒取得全部 81 次 LP 操作，对比 HyperSync 全链扫需几十小时（KOGE 第二轮追加取证，07-25）。
- (原 L164) Alchemy 平台级 429 曾整夜零进展（SIREN，07）。
- (原 L170) bloXroute 某次 3392 段中 92 段失败，后以 remaining 补扫闭合（OPN，07）。
- (原 L183) Multicall3 放量前未做小样本，因地址文件混入余额尾巴、动态偏移解码错、吞异常三连 bug，三轮 990/990 全失败（SIREN，07）。
- (原 L200) BANANAS31 转正后 Alpha Router 余额仅剩 ≈101 枚（07-22），作为 Router 随转正清空迁移的实测记录。
- (原 L203) dRPC 免费 key 未探测即让用户注册，实测基本不可用，白费一次注册（SIREN，07）。
- (原 L204) 2026-07 用户中国网络快照：drpc/alchemy/getblock/bitquery=200，app.envio.dev/nodereal=000，dune=403；bsc.hypersync.xyz 直连通（SIREN，07）。
- (原 L205) 数据量曾由几十万条误估至实际 2150 万条，造成耗时预估连环跳票（SIREN，07）。
- (原 L208) 通道切换未清观察哨曾空挂十几小时，并触发用户追问任务存活状态（SIREN，07）。
- (原 L210/L223) 旧 `scan_transfers.py` 毒段无限回队且 8 worker×curl 可零产出，后由 fill/现役 requests 扫描器取代（bibi，07-12；SIREN，07-19）。
- (原 L230) QUQ 案 `key_edges.csv` 7.3GB，采用逐行流式写出（07-22）。
- (原 L231) 2026-07-22 Alpha `mulPoint` 分布快照：645 币=1x、11 币=4x，后者均为 30 天内新 TGE Points Plus 加成（QUQ 投后，07-22）。
- (原 L234) QUQ 池腿法互验：LP 加撤剔除 2%；费反推与池腿实算吻合 103%；链上/CG≈83% 属正常带（QUQ 投后，07-22）。
- (原 L254) BscScan 省略号地址防错纪律源自 QUQ 07-22 案源记录。
- (原 L285) 图表叙事技巧：大户建仓时间线图上"创世期区域完全空白"= 没有任何创世钱包还留在前排的可视化证明（老庄已清仓的直观证法）。

#### data-pipeline-solana-capture.md

- (原 L15) IO 原始会话实录曾存档于 `~/Desktop/老公用/fable筹码分析/windows IO筹码分析会话记录/26a24d6c-*.jsonl`。
- (原 L19/L21) 验证清单在 2026-07-12 经 IO 实录考古大幅勾销；getProgramAccounts、组合过滤、Squads ID、Solscan 不可直读与情报源可达多数已回答，Token-2022 大扫描已实战收编（CLUDE 07-13）。
- (原 L34/L35) PUB 07-15 续拉后重放与链上快照逐地址零差异；CLUDE 07-13 的 CPMM 数学重建中段端点偏差实测达 35~49%。
- (原 L37) 公共 RPC gas 溯源 45 地址约 4 分钟。
- (原 L48) LAYOFF 锚点法工程规模：138 万签名、失败率 33% 属 pump AMM 正常、只用成功笔；约 550 个池余额锚点、约 65 个核心实体、约 400 个插值时间点。
- (原 L49) requests.Session 连接复用比 curl 逐发快约 3 倍；dRPC 免费层 Solana 返回 `chain is not available on freetier`，需付费。
- (原 L50) `oldest_sigs` 遇高频中转（数千签名）会卡死；LAYOFF 20 地址运行 15 分钟仍卡死，促成 `max_pages=2`。
- (原 L59) 快照对比法 1.8 天窗口全程数据成本 <1 小时。
- (原 L73) GOAT 案 `compose_evolution.py` 与 `GOAT分析/` 为 07-22 专属存档，实体分组、发射日、价格文件名按案硬编码。
- (原 L74) SQD 高密度期战报：大段 120 分钟只推进 3.4 链上小时；小段 29 秒拉完 1 万 slot，发射日 24h（16.5 万边）82 分钟；GOAT gap 追加产生 9,212 行重复，负余额账户 534 → dedup 后 1（GOAT，07-22）。
- (原 L75) GOAT 完整性复核 4 条 must_add 有 3 条半源于缺两扫描：历史离场大仓×2、离场庄扩容、事件日调拨（GOAT，07-22）。
- (原 L77) whale_deep 单案测速：USELESS（07-21）；5 进程时单笔 decode 拖到 0.6-1.2s（GOAT，07-22）。
- (原 L92) 销户账户覆盖首轮实证：PUB 全程边集 93/93、USELESS 定向段 7/7 全覆盖（2026-07-21）。
- (原 L98) v1/window_fetch 未开压缩导致错误判定 SQD 单流 1.5-4x 实时、全程重放不可行；13a–13b 启用 gzip/v2 后恢复可行。
- (原 L110) BONK 顶级密度战报：40 万 slot（约 28 链上小时）+22.3 万边，三跑约 11 分钟，稳态 639 slots/s≈255 倍实时；对照 window_fetch 82 分钟，约 7 倍。
- (原 L149) mainnet-beta batch 20 笔仅约 9 笔放行，首测 22/40 假失败；缓存 18/40 命中；Helius 于 2026-07-21 经 Google OAuth 注册，40 笔 5.3s=7.5 笔/s，45 地址溯源由旧 4 分钟约降至 35 秒。
- (原 L150) TROLL 实测（2026-07-29）：Helius keep-alive 版 8 线程约 7 笔/s 稳定，工作目录存档，待第二案复现后收编。
- (原 L181/L182) GOAT 拉签名实测 1,600 笔/秒，11.3 万笔池 ATA 仅 70 秒；45 万笔按日压缩为 8,302 个采样点（1.8%）。
- (原 L197) TROLL 长内盘规模：13 个月仅约 1,600 笔，跨 8 千万 slot（2026-07-29）。
- (原 L199/L203/L204) TROLL 双索引重建 decode 零失败、1,413 边；2 轮收敛，一笔 6 边归集 tx 解决 38.6pp 差异；创建窗独立抽验 14/14 一致（2026-07-29）。
- (原 L206) TROLL 衔接缝曾有 119 枚差，定位为缝内协议销毁（2026-07-29）。

## [6.20.1] - 2026-08-05 — 修 5 处阻断级文档漂移＋docs_lint 中文禁词与 Python docstring 扫描

全库瘦身与一致性审查（codex 2026-08-05 报告，Fable 逐条实证复核）第 1 步：先修误导执行的漂移，再做瘦身。codex 改文件、Fable 验收并 commit。

- **漂移修复五处**：①`playbook-evidence-wording.md` 报告写作顺序段与 6.7.0 A4→A5 硬闸冲突——"框架与纯事实章节可先写"改为"A4 finalize 封口前禁止创建任何报告正文/图/HTML，并行可先写的只有 findings.md/facts 层"（SIREN 案源保留，叙述转为支持硬闸）；②easy（6.17.0 已删）执行性残留三处清除——`data-pipeline-evm-recon.md` "峰值非必需场景（easy 初筛）仍可跳"整句删、`data-pipeline-solana-capture.md` 锚点复用步"easy/混合重建"改"混合重建"、`evals/cases/06` 考官答案"analyze/easy/update 三条 workflow"改"analyze workflow"；③`accumulate_offenders.py` module docstring 旧"每次分析交付后固定跑 --apply"（含 easy E5 残词）改 v6.4.0/v6.4.1 现行规则——仅用户明确下令复盘时随 retrospective.md 步骤 3 执行、分析交付后不自动回灌（split-run 机械段模型读旧 docstring 会误跑 --apply 污染全局惯犯库，本条是第 1 步里危害最直接的一处）；④批量预采集（6.18.0 已删）残留两处——`data-pipeline-evm.md` 分册索引"批量预采集/增量拉取"改"断点续拉"、`split-run.md` A1"预采集衔接"改"存量产物复用"；⑤`data-pipeline-evm-sources.md` 旧 `fetch_hypersync_par` CSV 分片"跨天无人值守标准件"条标【历史降级·新案禁用】——与 `merge_parts.py` deprecated 口径对齐，主线=HyperSync v2 Parquet+done.json manifest，watchdog"守护巡检+断点续传+事件词叫醒"方法学与历史战报数字原样保留。
- **docs_lint 守卫扩展**：REMOVED_FEATURE_TERMS 增中文禁词「批量预采集」「预采集衔接」「easy 初筛」「easy E5」（此前正则纯英文，中文语义残留全部漏检——本轮五处漂移长期全绿的根因）；新增 scripts 树递归全部 .py 的 module docstring 扫描（ast.get_docstring 提取，排除 scripts/tests/，语法解析失败容错跳过）；E0 正则未扩为 E[0-6]——`report-template.md:210` 合法实体宏 `{{e1.*}}` 在 re.I 下必误伤，按预案改精确禁词 easy E5 覆盖旧 docstring 场景。
- **验收**：9 文件 diff 逐条对任务书口径核过；反例攻击两路均被拦（活跃 md 塞「批量预采集」FAIL、py module docstring 塞「easy E5」FAIL）——攻击测试中 git checkout 还原误回滚未提交修复一次，已按原 diff 重打并终验；`run_all.py` 49 项全 PASS。成本：codex 单会话 12 分钟；质量：判据阈值变更 0、代码逻辑变更 0（仅 docstring 与文档）、误伤保留概念 0。

## [6.20.0] - 2026-08-05 — 持仓分布形态硬闸

- **统计与分账**：新增 `holder_distribution_scan.py`。扫描器从当前 owner 快照重新派生私人主箱、私人 dust、公共设施、未识别合约和销毁哨兵五桶；基础分箱与半档平移分箱同时复算，局部鼓包采用单调 Poisson 零假设与 Holm-Bonferroni 校正，另行检查 top-1/3/5/10、HHI 和相邻质量跃迁。私人主箱少于 100 个 owner 时不作分箱结论，改为完整输出逐址分类、top-k、HHI 和等额组。
- **冻结参数**：分箱覆盖私人可入箱供应的 0.000001% 至 100%，相邻边界为 `sqrt(2)`，单档至少 5 个 owner，基础与平移成员 Jaccard 至少 0.8，异常簇须达到净供应 2%，未识别合约达到净供应 1% 时强制披露，同轮族错误率固定为 1%。所有参数写入产物并绑定哈希，CLI 不提供覆盖入口。
- **判断与回流**：新增 `distribution-explanation/v1`、`distribution-adjudications/v1`、`pattern-resolutions/v1`、`distribution-rounds/v1`、`distribution-exception-receipt/v1`。final scan 绑定 READY handoff、当前 A4、实体冻结和三账；异常解释必须同时闭合位置、成员、数量、证据封口和传播五项。新增异常簇必须回流 A4，轮次台账按前向哈希严格递增，唯一 terminal 之后禁止继续生成。
- **封口链升版**：handoff 升 `handoff/v3`，A4 升 `a4-seal/v4` 并增加可逐级验哈希的 revision 归档链，A5 升 `a5-report-seal/v2` 并绑定唯一终态 final scan、唯一终版分布图和固定报告句式。默认消费者拒收 handoff/v1/v2、a4-seal/v3 和 a5-report-seal/v1。
- **工作流与验证**：全新分析在 handoff 前生成 initial scan，A4 后按 final scan、解释检查、回流复封或终态封口循环；独立复核维持单阶段不适用状态。新增合成盘覆盖正常长尾、等额鼓包、头部集中、低于经济门、dust 假长尾、CEX 遮罩、未识别合约披露、小样本、输入漂移、重复 owner、台账删除、terminal 重开、伪解释和 waiver 缺字段。历史定标只沿用已留存探索值，不把旧案产物作为现役 fixture；保留集启动覆盖不完整时明确不纳入定标。
