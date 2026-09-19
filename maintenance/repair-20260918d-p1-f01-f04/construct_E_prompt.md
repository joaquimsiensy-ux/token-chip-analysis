# 施工任务 E（codex --write，按下方工单逐条执行）：版本落地 9.0.1

## 派工基线
- 派工基线：main 分支、HEAD 为包含本提示词文件的最新提交（本提示词入库后 HEAD 才定，故**不以具体 SHA 判定**）；基线判定只看工单 §0 第二条开工检查：`git status --short` 为空，且 `git diff --stat 868d3f61 HEAD -- references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 为空（scripts 已含两段五文件属预期，不在本单议题）。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先 `git rev-parse HEAD` 记入完成报告即可。
- 本任务是**施工**，不是复核：按工单 §2 逐文件落地（CHANGELOG 两处插入**逐字**照工单代码块，不得改写措辞）、按 §1 自跑 `test_version_consistency` 与 `wc -c SKILL.md`、按 §3 写完成报告 `E_done.md` 到工单所在目录。
- 纪律以工单 §0 为准（禁读 `~/.codex/`、只改四文件、不 commit/push、禁 stash/checkout/reset）。工单已由 codex 只读复核通过（`review_E_reply_r2.md`）；施工中若发现工单与仓库事实不符，**停工写 `E_done_attempt1_stopped.md`**，不得自行改写事实。
- stdout 首行固定 `# 施工 E：完成` 或 `# 施工 E：停工`；末尾披露是否读过禁读路径。

---

# 工单 E（v2，融合 codex 复核 r1 三条 E-R1-01～03）：版本落地 9.0.1 —— repair-20260918d-p1-f01-f04 收官（F04 EVM 显式散户桶硬拒 / F01 价格非有限值 fail-closed＋收口逐点重算）

> 性质：**纯文档/元数据工单**，零生产代码、零测试代码、零手册改动。**档位＝9.0.1（修）**，用户 09-18 裁决原话「9.0.1」：两段都不改任何收据/序列 schema 或键，旧合法产物全部照常通过；F04 拒的是从未在正式案出现过的配置，F01 拒的是本就不该进报告的坏价格文件（存量按真实解析规则核验 0 命中、且存量无任何 price_check 收据），符合 CHANGELOG 头部"修=既定契约内的修复、加固、回归补充"。
> v2 变更（`review_E_reply_r1.md`）：R1-01 F01 第二源规范化行号改为当前 HEAD 的 `price_check.py:179`（施工前基线为 :175）；R1-02 收官 review 摘要按五组输入/五组收据/retail 分述，真实 WARN 对照两版本均放行不再统称「拒」；R1-03 本机补验断言改为引用同目录 `fable_local_acceptance.md`（命令、被验提交、退出码、尾行、worktree 提交）及 `fable_*.log` 原始输出。
> 内容基线：HEAD 以派工头部为准（不以具体 SHA 判定，按 §0 检查）；两段施工 commit：F04 `de281c6`、F01 `84e70e5`。

## §0 纪律与白名单
- 禁读 `~/.codex/`（启动搜索若已读 memories 披露一次）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本目录（`maintenance/repair-20260918d-p1-f01-f04/`）以外的历史 maintenance 目录、`/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。离线。不 commit（Fable 验收后提交）。禁 stash/checkout/reset。
- 开工检查：`git status --short` 为空；`git diff --stat 868d3f61 HEAD -- references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 为空（scripts 已含两段五文件属预期，不在本单议题）。不符停工写 `E_done_attempt<N>_stopped.md`。
- **只允许修改四个文件**：`CHANGELOG.md`、`VERSION`、`pyproject.toml`（仅 :15 `version =` 一行）、`SKILL.md`（仅 :23 版本注释一行）；另允许新增本目录 `E_done.md`。`references/`、`scripts/` 一字不动。
- 本单是两段的版本登记，不重新评价施工；若 §2 文案与仓库事实不符（行号、字节、命令名、测试名、计数），退回本单而不是自行改写事实。

## §1 目标
VERSION（权威）= `pyproject.toml` `version` = CHANGELOG 最新条目 = `SKILL.md:23` 注释 全部为 `9.0.1`；CHANGELOG 新增索引一行与详细条目一段，体例与 9.0.0/8.0.0 一致；`test_version_consistency` 绿、`wc -c SKILL.md` 改前后相等（8021，`9.0.0`→`9.0.1` 等长）；`changelog_lint`、`docs_lint --all` 因读取 `archive/` 由调度方本机跑（施工方不跑；调度方施工前基线"活跃 79 条"，施工后复跑确认 80）。

## §2 改法（逐文件）
1. `VERSION`：`9.0.0` → `9.0.1`（保持原有换行形态）。
2. `pyproject.toml:15`：`version = "9.0.0"` → `version = "9.0.1"`。
3. `SKILL.md:23`：`<!-- skill-version-source: VERSION; skill-version: 9.0.0 -->` → `… 9.0.1 -->`（字节数不变）。
4. `CHANGELOG.md` 两处插入（施工者不运行 `changelog_lint`）：
   - 在索引区 `:13`（锚 `- **9.0.0**（2026-09-18）codex 8.0.0 六视角 review 三条修复`，行首片段，唯一）**之前**插入一行，逐字：
     ```
     - **9.0.1**（2026-09-18）codex 9.0.0 六视角 review 两条 P1 修复（既定契约内加固，不改任何 schema/键，故记修版本）：F04 `camp_spec.validate_camp_spec` 对 EVM 链族拒 spec 显式配置「散户」（引擎残差桶；原先 replay_pass2/replay_duck 对显式散户同日 append 两次、rc=0 产坏形状序列，靠下游长度检查兜底）；F01 `price_check._load_series` 任一点非有限或非正即 `[fatal]` 退出 1、第二源非有限规范化为 None 走 SKIP、收据 `allow_nan=False`（原先 NaN 主价判 PASS 并写含 NaN 的收据），`stage2_closeout.price_receipt_errors` 逐点按 main/second_price 同规则重算 status 并核声明、主价非有限正数即拒（原先只核 status 集合）。references/SKILL/commands 零改动。F02/F03/F05–F10 用户裁决本轮不修。
     ```
   - 在 `:97`（锚 `## [9.0.0] - 2026-09-18 — codex 8.0.0 六视角 review 三条修复`，行首片段，唯一）**之前**插入下面整段（段后空一行再接原 9.0.0 标题），逐字：
     ```
     ## [9.0.1] - 2026-09-18 — codex 9.0.0 六视角 review 两条 P1 修复（EVM 显式散户桶硬拒 / 价格非有限值 fail-closed＋收口逐点重算）

     - **出处与裁决**：codex 对 9.0.0（868d3f61）的六视角 review 判 PASS 需修复轮（P0 0 / P1 4 / P2 6 / P3 0）。用户 09-18 裁决：①只修 F01/F04；②原则＝skill 上下文不增、能删不增能改不增；③调度方只写工单/验收/调度，代码全由 codex 施工，codex 常规盲审、三次 FAIL 才换 opus；④版本 9.0.1。修的终点＝review 附录 A 两反例（`price_nan`、`retail`）在 HEAD 上必变拒，由盲审方与收官 review 独立复现，不以盲审 PASS 为准。
     - **F04**（`lib/camp_spec.validate_camp_spec`）：`chain_family == "evm" and camp == "散户"` → 既有 `_fail`（`[camp-spec] ` 前缀、exit 2），文案指明残差桶语义与改法；docstring 边界段补一句。四入口调用点、签名、返回形状不变；Solana 不拒（`build_evolution` 以「散户」为默认桶＋标量残差无重复 append，LAYOFF 案 `entity_camps.json` 27 处显式「散户」为存量；`replay_edges` producer 分列显式散户与动态桶、consumer `SOL_DYNAMIC_BUCKET_MERGE` 并桶，显式散户会触发既有末点对账冲突——登记不修）。不改两 EVM 引擎 append 结构（fail-closed 拒配置更小）。测试 `test_repair_batch_c`：`t_f05_unit` 加 EVM 拒/Solana 不误杀 2 check，`t_f05_evm_engines` 加 duck（exit 2 且全新目录不产 `camp_series.json`）/pass2（exit 2）各 1 check。
     - **F01**（`prices/price_check.py`；`report/stage2_closeout.price_receipt_errors`）：生产者 `_load_series` 解析后任一点 `not (isfinite(p) and p > 0)` → `[fatal] 价格文件含非有限或非正价格 N 点…` 退出 1（CSV/JSON/溢出 `1e309` 全覆盖，早于任何写盘）；`price_check.py:179`（施工前基线 :175）判点前 `p2 = p2 if p2 is None or isfinite(p2) else None`（第二源非有限＝对照不可得，走既有 SKIP，收据 `second_price=null` 可序列化）；`json.dump(..., allow_nan=False)` 纵深防御。消费者逐点：`main_price` 须有限正数（否则拒 `points[i].main_price`），`second_price` None/非有限/≤0 → SKIP，否则 `round(|a−b|/((a+b)/2)*100, 2)` 对 5/15 阈值判 PASS/WARN/FAIL，与自报 `status` 不一致拒 `points[i].status`；阈值常量 `PRICE_WARN_PCT/PRICE_FAIL_PCT` 复制自生产者（report 层不 import requests 类脚本），两端相等由测试断言守。汇总 verdict 规则、`price_file_sha256` 绑定、12 项 checks、返回类型不变；不新增收据键。兼容范围：主价格文件各点有限正数、第二源 None 或有限数的输入行为逐字不变；主价 0/负价由基线 SKIP 改为 fatal 属预期变化。测试 `test_stage2_closeout.price_receipt_content_enforced` 加 6b–6g 六段（生产者 NaN/0 fatal、第二源 NaN→ALL_SKIP 可序列化、收据主价 NaN/0 拒、第二价改 2.0 拒、阈值相等＋WARN 边界 1.0/1.052 手改拒）。
     - **工艺**：两份工单先 codex 只读复核（并行）：F04 r1 退回 4 条→v2 r2 通过；F01 r1 退回 5 条→v2 r2 退回 1 条→v3 r3 通过（十条意见全部亲核代码属实后吸收，含 R1 揭穿的第二源 NaN 撞 allow_nan 抛异常、消费者与生产者非正主价口径不一、6d 守不住阈值漂移、存量核验须用真实解析规则）。施工串行 codex `--write`：F04 attempt1 完成；F01 attempt1 按纪律停工（调度方在派工后写入未提交的盲审提示词草稿致 §0.1 树不干净——教训：施工期间对仓库零写入）、attempt2 `--resume-last` 续跑掉回只读沙箱再停工（教训：停工后一律 `--fresh` 重派）、attempt3 完成。每段 Fable 本机验收（diff 与工单逐字对照、RED 分布、定向测试、字节三处）后 commit，再 codex 常规盲审：F04 r1 PASS（反例独立复现 HEAD 拒×2/基线 RED×2/合法产物逐字节一致；6 项沙箱临时目录阻塞由本机 7/7 补验）；F01 r1 PASS（反例独立复现：三天 NaN 及首日 inf/0/−1 主价在 HEAD 均退出 1、无收据、不调第二源；第二源 NaN/inf → 完整收据 `second_price=null`、ALL_SKIP 退出 3 无异常；消费者对 NaN/0 主价、第二价改 2.0 伪报 PASS、WARN 边界 1.0/1.052 伪造 PASS 均拒；基线 6b–6g 逐段 RED；15 组合法输入退出码/stdout/收据字节与基线相同；两端偏差表达式 AST 相同、阈值邻界 8 例一致；5 项沙箱临时目录阻塞由本机 6/6 补验含 `test_stage2_closeout` 30/30）。收官 codex review r1 通过（`final_review_reply_r1.md`：`price_nan` 五组输入——四组坏主价（三天 NaN / 首日 inf / 0 / −1）基线 rc=0 写收据、HEAD `[fatal]` 退出 1 不写收据，第二源 NaN 基线收据含 NaN、HEAD 生成完整 ALL_SKIP 收据退出 3；五组收据——主价 NaN、主价 0.0、第二价 2.0 伪报 PASS、真实 WARN 收据全改 PASS 四组基线放行、HEAD 拒，真实 1.0/1.052 WARN 收据两版本均放行并记 NOTE；`retail` 两引擎基线「散户」长度 4 复现同日重复 append、HEAD exit 2 无 `camp_series.json`，Solana 与三组合法 EVM spec 在两版本逐字节相同；白名单恰五文件 +78/−5、三处字节不变、两段文件集合交集为空、invariant_scan PASS；7 项沙箱临时目录阻塞由本机 run_all 补验，见 `fable_local_acceptance.md` §3）。
     - **字节与测试**：references 930076、SKILL.md 8021、commands-staging 8798 三处零改动（契约由 CHANGELOG 与 docstring 承载；`invariant_manifest`/`contract_manifest` 不动，`invariant_scan` 两段前后均 PASS）。scripts 改动五文件：F04 camp_spec.py/test_repair_batch_c.py（+19/−1）；F01 price_check.py/stage2_closeout.py/test_stage2_closeout.py（+59/−4）。本机验收记录见同目录 `fable_local_acceptance.md`（命令、被验提交、退出码、尾行、worktree 提交；原始 stdout 在 `fable_run_all_84e70e5.log`/`fable_f04_local_tests.log`/`fable_f01_local_tests.log`）：`run_all` 于 84e70e5 上 PASS 151 / FAIL 0、`RUNALL_EXIT=0`（`MPLCONFIGDIR=$HOME/.matplotlib` 下，含 `test_stage2_reseal` 21/21，验收 worktree `/tmp/w3_acceptance` 同步 84e70e5）；九项守卫（`changelog_lint`、`docs_lint --all`、`test_version_consistency`、`invariant_scan`、`test_batch4_invariant_guards`、`test_exemption_guards`、`test_g3_docs_guards`、`casebook_lint`、`fixtures_lint`）于 268026c 上 9/9 rc=0。
     - **档位与存量说明**：9.0.1（修）——不改任何 schema/键。存量核验（调度方本机，真实解析规则）：案卷 28 个可解析价格文件 0 个非有限/非正点；案卷不存在任何 `price_check.py` 生成的收据（0 份含 `points`），故消费者收紧无迁移对象；EVM 正式案 spec 从未显式配置「散户」（review 全量检索记录）。APU 0914 案自定义收据仍按 9.0.0 Q8 在进 −3 时重跑。
     - **成本-质量指标**：生产逻辑文件 3（camp_spec、price_check、stage2_closeout）、新公开入口 0、新增产物输出键 0、新增 SUITE 入口 0；外部网络调用 0（第二源全部替身）；不运行真实案卷判断链，判断结论不自动变更。
     ```

## §3 完成报告 `E_done.md` 必含
①§0 两条检查输出；②四文件 `git diff` 原文；③`python3 -B scripts/tests/test_version_consistency.py` 尾行；④`wc -c SKILL.md` 改前后；⑤`git diff --stat`（须恰为四文件）；⑥禁读披露。stdout 首行 `# 施工 E：完成` 或 `# 施工 E：停工`。
