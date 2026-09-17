# 工单 E（v1）：版本落地 7.2.0 —— repair-20260917-p0-four 收官（四条 P0：R08 图 2 有限值、R03 expanded 只进上限、R07 facts 由三账生成、R09 日级峰值闸）

> 性质：**纯文档/元数据工单**，零生产代码、零测试代码、零手册改动。新增公开子命令（`facts_gate.py build`、`replay_duck.py --only-addrs`）与两个持久化 schema（`facts-provenance/v1`、`block-precision-followup/v1`）＝向后兼容的新能力，记 **7.2.0**（次版本）。
> 内容基线：HEAD 以 `construct_E_prompt.md` 派工副本首行标注为准；四段施工 commit：A 212ede1、B 03507cb、C 1b317b3＋C7 eca1131、D f583039。

## §0 纪律与白名单
- 禁读 `~/.codex/`（启动搜索若已读 memories 披露一次）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`/Users/uravvv/Desktop`。离线。不 commit（Fable 验收后提交）。禁 stash/checkout/reset。
- **只允许修改四个文件**：`CHANGELOG.md`、`VERSION`、`pyproject.toml`（仅 :15 `version =` 一行）、`SKILL.md`（仅 :23 版本注释一行）；另允许新增 `maintenance/repair-20260917-p0-four/E_done.md`。`references/`、`scripts/` 一字不动。
- 本单是 A–D 的版本登记，不重新评价四段施工；若 §2 文案与仓库事实不符（行号、字节、命令名、测试名、计数），退回本单而不是自行改写事实。

## §1 目标
VERSION（权威）= `pyproject.toml` `version` = CHANGELOG 最新条目 = `SKILL.md:23` 注释 全部为 `7.2.0`；CHANGELOG 新增索引一行与详细条目一段，体例与 7.1.3/7.1.1 一致；`changelog_lint`、`test_version_consistency`、`docs_lint --all` 全绿；`wc -c SKILL.md` 改前后相等（8021）。

## §2 改法（逐文件）
1. `VERSION`：`7.1.3` → `7.2.0`（保持原有换行形态）。
2. `pyproject.toml:15`：`version = "7.1.3"` → `version = "7.2.0"`。
3. `SKILL.md:23`：`<!-- skill-version-source: VERSION; skill-version: 7.1.3 -->` → `… 7.2.0 -->`（字节数不变）。
4. `CHANGELOG.md` 两处插入（**先跑** `python3 -B scripts/tests/changelog_lint.py` 记基线"活跃 75 条"，改后须 76）：
   - 在索引区 `:13`（锚 `- **7.1.3**（2026-09-16）drift-audit 待决台账三项用户裁决落地`，行首）**之前**插入一行，逐字：
     ```
     - **7.2.0**（2026-09-17）codex 7.0.4 review 四条 P0 修复：R08 图 2 对账拒 NaN/Infinity/非有限末点并落 FAIL 收据；R03 三账汇总 expanded 成员只进 `expanded_economic_control_range_raw` 上限、闸验区间；R07 `facts_gate.py build` 从三账＋identity＋provenance＋`state_source.facts_inputs` 生成 facts.json（带 `facts-provenance/v1` 绑定块，峰值 override 须带证据），new-analysis 闸与 stage2 收口用同一 `derive_facts` 重算比对；R09 日级峰值闸 rglob 定位子目录产物、needs 哈希咬合、`replay_duck.py --only-addrs` 出 `block-precision-followup/v1` 覆盖收据。references 净减 9 B，SKILL/commands 不变。
     ```
   - 在 `:93`（锚 `## [7.1.3] - 2026-09-16 — drift-audit 待决台账三项裁决落地（零逻辑改动）`）**之前**插入下面整段（段后空一行再接原 7.1.3 标题），逐字：
     ```
     ## [7.2.0] - 2026-09-17 — codex 7.0.4 review 四条 P0 修复（图 2 有限值 / expanded 上限 / facts 自三账生成 / 日级峰值闸）

     - **出处与裁决**：codex 对 7.0.4 的整体 review 判定四条 P0 阻断发布（R03/R07/R08/R09），三路探索在 4cbfe48 全部复现。用户 09-17 裁决：R03 改代码贴合既有文档（严格成员＝可证下限、扩展成员只进上限，文档零改动）；R07 facts 由三账自动生成、峰值取 provenance 日粒度锚点、允许显式 override 须带证据、人工字段复用 `state_source.json`；R08 加有限值检查；R09 修三件套；总原则 skill 上下文不增、能删不增能改不增。
     - **A＝R08**（`figures_from_facts.py`）：`_load` 用 `parse_constant` 拒 NaN/Infinity 字面量；图 2 对账对 pct 全序列做类型＋有限值检查（拒 bool/非数/非有限/字符串宽容）；`mode_check` 把输入失败收敛为 FAIL 收据落盘；`dumps_fig2_series` `allow_nan=False`。`test_repair_batch_c` 十例。
     - **B＝R03**（`audit_release_gate.check_three_ledgers`）：位置账按 member_map 分流，strict 进 `wallet_by_entity`、expanded 进 `expanded_by_entity`；实体有 expanded 成员则 `expanded_economic_control_range_raw` 必填，字段在场（含显式 null）须两元素数组、下限＝重算 confirmed、上限 ≥ 下限＋Σexpanded（上限超出部分无账本来源，闸只验下界，登记 P10）；逐地址闭合与实体集合闭合不动。APU 0801 三账改前改后皆零错误。十例。
     - **C＝R07**（`facts_gate.py build`／`derive_facts`；发布闸 `check_facts_vs_ledgers`；stage2 `facts_vs_ledgers` record 11→12）：实体集＝economic 条目、addresses＝strict 成员、current＝confirmed、total＝identity_gate；peak 取 `facts_inputs.peak_overrides`（evidence path/sha 三验）否则 provenance 锚点，formal 无来源拒、peak<current 拒；生成物过既有 `gate_check`（G2/G3）；输入 JSON `parse_constant`＋`parse_float` 拒 NaN/Infinity/1e999；`facts_inputs` 类型约定（symbol 非空字符串、metrics/dual_basis 对象）；产物 `provenance{schema:facts-provenance/v1, facts_binding:ledger-derived, mode, inputs sha, state_source sha, peak_overrides, producer}`，exploration 产物闸必拒；facts.json 进 `NEW_ANALYSIS_REQUIRED`，闸用同一 `derive_facts` 重算逐键/逐实体比对（排除 producer），符号链接／另名 facts／输入漂移一律拒。四处 new-analysis 夹具（stage2/reseal、batch_d `build_solana_case`、P105、a4_gate case_new）改由共享助手 `build_facts_from_ledgers` 从三账 build；`identity_gate_fixture.augment_gate` 加 `balances` 参数使 P105 identity 与 owner 快照同世界。`test_report_facts` 15 类 34 例。`report-template.md:212` "数值从落盘数据复制"→"由 build 自三账生成，禁手抄"（−5 B）。APU 0801 临时目录对照：current 3/3、addresses/label/token 全等、peak 1/3（另两处 A4 块粒度峰值经 override 路径 3/3 复现）。
     - **D＝R09**（`audit_release_gate.check_daily_peaks` 重写；`peaks_daily.py`；`replay_duck.py --only-addrs`）：rglob 定位 `peaks_summary.json`（跳隐藏/`_history`/符号链接），零份 return、多份拒，伴随文件相对产物根解析；summary 新增 `needs_block_precision_file/sha256` 与实物咬合（旧产物＝升级重跑）；needs 各档 ∪ 触发日 `active_candidates`（缺项/null 不作零候选）非空时须 `block_precision_followup.json`（schema `block-precision-followup/v1`、engine replay_duck.py、inputs 绑 needs/trigger sha、addresses 覆盖每址 `{peak, peak_blk}`，peak>0 ⇒ 非负整数区块、peak==0 ⇒ null，两侧小写归一）；生产者 `--only-addrs`（needs 字典/trigger_days/地址列表，可重复）只算并集地址块级峰值（窗口 SQL 与全量逐字同源、无门槛、无事件补 0/null），收据写首个输入所在目录，整段跳过 pass1/merged/pass2、坏事件分支也不写全量 `replay_stats.json`，坏 JSON/空并集/坏形状 exit 2。原六条错误文案逐字保留。`_r09_case_1..13`、`followup_case`、peaks_daily needs sha 断言。`data-pipeline-evm-recon.md:132` −13 B、`playbook-entity-cluster-tiering.md:149` +9 B。APU 0801 对照：改前闸返回 `[]`（子目录产物被绕过），改后报 needs 哈希未登记；该案再发布前须重跑 peaks_daily＋`--only-addrs` 补算。闸不验 followup `channels` 与全量输入同源，登记 P13 另单。
     - **工艺**：每段工单先 codex 只读复核（A 四轮、B 两轮、C 三轮＋C7 两轮、D 四轮），通过后 codex 写模式施工，Fable 本机验收（白名单 diff、定向测试、字节、存量案对照、reseal 同步 worktree）后 commit，再 codex 常规盲审：A r1 FAIL（打包偏差）→r2 PASS、B r1 PASS、C r1 FAIL（1 minor 类型校验）→C7→r2 PASS、D __BLIND_D__。只读复核与盲审并行派、施工串行（用户 09-17 定）。
     - **字节与测试**：references 930070→930061（−9 B），SKILL.md 8021、commands-staging 8798 不变；invariant_manifest 登记两 producer/consumer schema 与两处 overwrite_single，minimum_counts 下限抬至实际计数（81/118/61）；本机 run_all __RUN_ALL__；九项守卫全 PASS。登记不修台账 `maintenance/repair-20260917-p0-four/code_change_pending.md` P1–P13（含 P2 预筛 0.1% vs 1%、P3 APU trigger_days 键、P4 override 数学正确性、P7 `load_json` 1e999、P10 上限来源、P12 producer sha 只记录）。
     - **成本-质量指标**：生产逻辑文件 5（figures_from_facts、audit_release_gate、facts_gate、stage2_closeout、peaks_daily、replay_duck 计 6 处改动）、新公开入口 2、新持久化 schema 2、新增 SUITE 入口 0；外部网络调用 0；不运行真实案卷判断链，判断结论不自动变更；存量案 APU 0801 再发布前须补 `state_source.facts_inputs` 重 build 与峰值补算。
     ```
   - 其他行不动；`archive/CHANGELOG-archive.md` 不动。

## §3 验收（施工者自跑并记入 E_done.md）
- `git status --porcelain=v1 --untracked-files=all` 只列四个文件（M）与 `E_done.md`（??）；`git diff --exit-code HEAD -- references/ scripts/` 退出码 0。
- `python3 -B scripts/tests/changelog_lint.py` PASS（活跃 75→76）；`python3 -B scripts/tests/test_version_consistency.py` exit 0；`python3 -B scripts/tests/docs_lint.py --all` PASS；`wc -c SKILL.md` 改前后均 8021。不跑 run_all（调度方已跑并把计数填入 §2）。

## §4 报告 `E_done.md`
首行 `# 施工 E：完成` 或 `# 施工 E：停工`；列四文件各自 diff 行数、三条验收命令退出码与关键输出行、改前后 changelog_lint 活跃条数、`wc -c SKILL.md` 两值。不 commit。
