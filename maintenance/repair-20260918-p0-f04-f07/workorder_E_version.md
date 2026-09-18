# 工单 E（v1）：版本落地 7.2.1 —— repair-20260918-p0-f04-f07 收官（四条主轨 P0：F06 exclude 标签重推 INFRA / F04 图 2 收据发布期重算 / F07 峰值产物定位＋followup 绑定 / F05 facts 峰值-日期-decimals 校验）

> 性质：**纯文档/元数据工单**，零生产代码、零测试代码、零手册改动。四段均为既定契约内的闸加固（消费侧从"信收据/字段自报"改为"按实物重算或绑定"），无新公开入口、无新持久化 schema，**档位＝7.2.1（修）**。存量迁移代价写进条目"档位与迁移说明"。
> 内容基线：HEAD 以 `construct_E_prompt.md` 派工副本首行标注为准；四段施工 commit：F06 8df17dd、F04 b794325、F07 a201c63（＋文本修复 bf60b50）、F05 332a582。

## §0 纪律与白名单
- 禁读 `~/.codex/`（启动搜索若已读 memories 披露一次）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。离线。不 commit（Fable 验收后提交）。禁 stash/checkout/reset。
- **只允许修改四个文件**：`CHANGELOG.md`、`VERSION`、`pyproject.toml`（仅 :15 `version =` 一行）、`SKILL.md`（仅 :23 版本注释一行）；另允许新增 `maintenance/repair-20260918-p0-f04-f07/E_done.md`。`references/`、`scripts/` 一字不动。
- 本单是 F04–F07 的版本登记，不重新评价四段施工；若 §2 文案与仓库事实不符（行号、字节、命令名、测试名、计数），退回本单而不是自行改写事实。

## §1 目标
VERSION（权威）= `pyproject.toml` `version` = CHANGELOG 最新条目 = `SKILL.md:23` 注释 全部为 `7.2.1`；CHANGELOG 新增索引一行与详细条目一段，体例与 7.2.0/7.1.3 一致；`test_version_consistency` 绿、`wc -c SKILL.md` 改前后相等（8021）；`changelog_lint`、`docs_lint --all` 因读取 `archive/` 由调度方本机跑（施工方不跑；调度方施工前基线"活跃 76 条"，施工后复跑确认 77）。

## §2 改法（逐文件）
1. `VERSION`：`7.2.0` → `7.2.1`（保持原有换行形态）。
2. `pyproject.toml:15`：`version = "7.2.0"` → `version = "7.2.1"`。
3. `SKILL.md:23`：`<!-- skill-version-source: VERSION; skill-version: 7.2.0 -->` → `… 7.2.1 -->`（字节数不变）。
4. `CHANGELOG.md` 两处插入（施工者不运行 `changelog_lint`）：
   - 在索引区 `:13`（锚 `- **7.2.0**（2026-09-17）codex 7.0.4 review 四条 P0 修复`，行首）**之前**插入一行，逐字：
     ```
     - **7.2.1**（2026-09-18）codex 7.2.0 六视角 review 主轨四条 P0 修复（闸从信自报改为按实物核）：F06 G8 身份闸消费侧对带 `tier=exclude` 标签的实体成员重推 `INFRA_IN_ENTITY`（清空 flag 不再解除 INFRA 义务）；F04 new-analysis 闸对图 2 收据在两输入实物在场时用 `fig2_check_errors` 发布期重算（收据自报 PASS 不作数）；F07 日级峰值闸按 summary/needs/followup 三件任一定位产物目录（改名 summary 不再绕闸），followup 须绑定当前 `replay_duck.py` sha、案内唯一 channels 实物、`value_type`、`count`；F05 facts 每实体 `peak_raw≤total_raw`、`peak_overrides` 证据须为 `{entity_id:{peak_raw,peak_date}}` 且与申报相等、`peak_date` 严格 ISO 且不晚于 provenance 当前锚点日、闸侧 `token.decimals` 绑链上观测。references/SKILL/commands 字节全部不变。
     ```
   - 在 `:94`（锚 `## [7.2.0] - 2026-09-17 — codex 7.0.4 review 四条 P0 修复（图 2 有限值 / expanded 上限 / facts 自三账生成 / 日级峰值闸）`）**之前**插入下面整段（段后空一行再接原 7.2.0 标题），逐字：
     ```
     ## [7.2.1] - 2026-09-18 — codex 7.2.0 六视角 review 主轨四条 P0 修复（exclude 标签重推 INFRA / 图 2 收据发布期重算 / 峰值产物定位与 followup 绑定 / facts 峰值-日期-decimals 校验）

     - **出处与裁决**：codex 对 7.2.0（311e6c4）的六视角 review 判 BLOCK、P0×8。用户 09-18 裁决：威胁模型＝自己人（AI 执行者抄近路/脚本 bug/人填字段/文件搬运），不是外人造假；只修主轨（new-analysis）四条 F04/F05/F06/F07；F01/F02/F03 只在"复核既有报告"净室轨（independent-audit）生效，缓修排 P1；F08（含空格图路径）不修，脚本产出无此形态。总原则：skill 上下文不增、能删不增、能改不增——本轮 references/SKILL/commands 零改动。
     - **F06**（`entity_identity_gate.validate_gate`）：实体成员若带 `tier=exclude`（公共设施）标签而 flag 不是 `INFRA_IN_ENTITY`，闸侧直接拒——原先只认 producer 自报的 flag，清空 flag 即解除 INFRA 义务；与 producer 推导对称，只按 tier 不按 category。`test_entity_identity_gate` 三例（清空 flag 拒／无 resolution 仍拒／带 resolution 放行）。
     - **F04**（`audit_release_gate.check_figure2_receipt`）：series/facts 两输入实物＋sha 检查无新增错误后，按收据绑定的实物调用 `figures_from_facts.fig2_check_errors`（容差 `FIGURE2_DEFAULT_TOL_PP`）发布期重算，重算失败（六类异常）或不符即拒；同 schema 手写 PASS 收据不再放行。`test_repair_batch_c` 新增 `_f04_case_1..4` 挂进 `t_r08_nonfinite`，`_r08_case_12` 断言反转（NaN 手写 PASS 收据现拒），完整模块 249 checks。空 series（lines_checked==0）放行属既接受残余（P2）。
     - **F07**（`audit_release_gate.check_daily_peaks`）：定位改 `_find_peaks_dirs`——`PEAKS_DAILY_PRODUCTS`（summary/needs/followup）三件任一在场即认定峰值产物目录（单次 `rglob("*.json")`，跳隐藏/`_history`/符号链接），多目录拒，目录内缺 summary 拒（改名 summary 不再零命中绕闸；`trigger_days.json` 既是输入名也是输出名，不作定位依据）；followup 须绑定 `producer{path=replay_duck.py, sha256=当前 scripts/evm/replay_duck.py}`、`channels{path,sha256}` 命中案内恰一个常规文件且 sha 一致、`value_type∈{HUGEINT,VARINT}`、`count==len(addresses)`（这些字段 7.2.0 的 `--only-addrs` 已写出，闸侧此前不消费）。`test_audit_release_gate` 用例 14–22（7 真 RED＋2 GREEN 保持），用例 6 文案随"多个峰值产物目录"。原六条错误文案与 inputs/addresses 校验保留。
     - **F05**（`facts_gate.py`；`audit_release_gate.check_facts_decimals`）：`gate_check` G2 加每实体 `peak_raw≤total_raw`；`derive_facts` 对 `peak_overrides` 证据文件读 JSON，须为 `{entity_id:{peak_raw,peak_date}}` 且与申报相等（hash 只证文件没变，不证值来自文件）；`peak_date` 严格 `YYYY-MM-DD`（`fromisoformat` 回写相等）且不晚于 provenance `anchors.current.date`；新增 `check_facts_decimals` 只挂 `_run` 的 new-analysis 分支：solana 家族取 `accounting_mode.checks.decimals`，evm 家族取 balance 对账收据绑定的 verify_recon config `decimals`（复用已缓存 witness），取不到或与 `facts.token.decimals` 不等即拒；共享 `check_facts_vs_ledgers` 一字不动（stage2 收口/reseal 不受影响）。`test_report_facts` 用例 16–21（证据不一致／一致／峰值超总供应／坏日期两形／晚于当前锚点／证据为数组），`test_review_20260804_p105` decimals a/b 两例，batch_d 与 audit_release_gate 夹具补 `decimals`。
     - **工艺**：每段工单先 codex 只读复核（F06 一轮、F04 两轮、F07 两轮、F05 两轮），通过后 codex 写模式施工，Fable 本机验收（白名单 diff 对照工单、定向测试、字节）后 commit，再 codex 常规盲审：F06 r1 PASS、F04 r1 PASS、F07 r1 FAIL（1 minor：迁移命令漏必填 `--out-dir`，纯文本）→r2 PASS、F05 r1 PASS。只读复核与盲审并行派、施工串行；施工中不 commit；施工与盲审同碰一文件时串行。
     - **字节与测试**：references 930061、SKILL.md 8021、commands-staging 8798 全部不变；`invariant_manifest` 无需增补；本机 run_all 150/151＋`test_stage2_reseal` 补验 21/21（验收 worktree `/tmp/w3_acceptance` 重建并同步 HEAD 后）＝151/151；九项守卫全 PASS。登记不修台账 `maintenance/repair-20260918-p0-f04-f07/code_change_pending.md` P1–P12（P8 **待用户裁决**：峰值上界用当前总供应一刀切，大额销毁后历史峰值大于当前供应的币会被保守阻断，正解需时点供应序列另单）。
     - **档位与迁移说明**：记 7.2.1（修）——四段皆既定契约内加固，无新入口/schema。存量迁移代价：①7.2.0 之前产出的 `block_precision_followup.json` 缺绑定字段，须用当前引擎 `replay_duck.py --channels <通道清单> --out-dir <补算工作目录> --only-addrs <产物目录>/needs_block_precision.json --only-addrs <产物目录>/trigger_days.json` 重跑补算（升级引擎即重跑）；②`peak_overrides` 自由格式证据文件须改写为 `{entity_id:{peak_raw,peak_date}}` JSON；③`state_source.facts_inputs.decimals` 须与链上观测一致，填错即 BLOCK。旧案在 HEAD 下 BLOCK 由钉版机制承接（`~/.claude/skill-pins/`）。
     - **成本-质量指标**：生产逻辑文件 3（entity_identity_gate、audit_release_gate、facts_gate）、新公开入口 0、新持久化 schema 0、新增 SUITE 入口 0；外部网络调用 0；不运行真实案卷判断链，判断结论不自动变更。
     ```
   - 其他行不动；`archive/CHANGELOG-archive.md` 不动。

## §3 验收（施工者自跑并记入 E_done.md）
- `git status --porcelain=v1 --untracked-files=all` 只列四个文件（M）与 `E_done.md`（??）；`git diff --exit-code HEAD -- references/ scripts/` 退出码 0。
- `python3 -B scripts/tests/test_version_consistency.py` exit 0；`wc -c SKILL.md` 改前后均 8021。**不跑** `changelog_lint`、`docs_lint --all`（读 archive/，调度方本机跑并记 76→77）、不跑 run_all（调度方已跑并填入 §2）。

## §4 报告 `E_done.md`
首行 `# 施工 E：完成` 或 `# 施工 E：停工`；列四文件各自 diff 行数、`test_version_consistency` 退出码与输出行、`wc -c SKILL.md` 两值。不 commit。
