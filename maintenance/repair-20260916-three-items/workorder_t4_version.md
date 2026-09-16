# 工单 T4（v2.1，r2 非阻断措辞采纳；v2 融合 codex 复核 `t4_review_reply.txt`：查询命令语法、`main` 改动限定、副本件数 78、run_all 全绿条件、porcelain/--exit-code 验收）：版本落地 7.1.1 —— repair-20260916-three-items 收官（分支 `fix/three-items-20260916`，已合并 origin/main=7b820a4「7.1.0 W3」）

> 性质：**纯文档/元数据工单**，零生产代码、零测试代码、零手册改动。另一会话已占 7.1.0，本三项记 **7.1.1**（修版：既定契约内的修复与文档修订）。

## §0 纪律与白名单
- 禁止**施工者本人**读取 `/Users/uravvv/.codex/`、`/Users/uravvv/.claude/skills/_archive/`，禁止 checkout tag `codex-frozen-20260915`；被测生产代码自身对安装目录的 `git rev-parse` 探测是既有行为可原样运行。离线。不 commit（由 Fable 验收后提交）。禁 stash/checkout/reset 等回退他人施工的操作。
- **只允许修改这四个文件**：`CHANGELOG.md`、`VERSION`、`pyproject.toml`（仅 :15 `version =` 一行）、`SKILL.md`（仅 :23 版本注释一行）；另允许**新增** `maintenance/repair-20260916-three-items/t4_done.md`。`references/`、`scripts/` 一字不动。
- 本单是 T1/T2/T3 的版本登记，**不重新评价三项施工**；若 §2 文案与仓库事实不符（行号、字节数、命令名、测试名、附录字母），退回本单而不是自行改写事实。

## §1 目标
VERSION（权威）= `pyproject.toml` `version` = CHANGELOG 最新条目 = `SKILL.md:23` `<!-- skill-version-source: VERSION; skill-version: X -->` 全部为 `7.1.1`；CHANGELOG 新增索引一行与详细条目一段，体例与 7.1.0/7.0.4 条目一致；`changelog_lint`、`test_version_consistency`、`docs_lint --all`、`run_all` 全绿。

## §2 改法（逐文件）
1. `VERSION`：`7.1.0` → `7.1.1`（保持文件原有换行形态）。
2. `pyproject.toml:15`：`version = "7.1.0"` → `version = "7.1.1"`。
3. `SKILL.md:23`：`<!-- skill-version-source: VERSION; skill-version: 7.1.0 -->` → `… 7.1.1 -->`（字节数不变）。
4. `CHANGELOG.md` 两处插入（**先跑** `python3 -B scripts/tests/changelog_lint.py` 记基线，改后再跑）：
   - 在索引区 `:13`（`- **7.1.0**（2026-09-16）…` 行）**之前**插入一行，逐字：
     ```
     - **7.1.1**（2026-09-16）三项修复：seal↔正文零地址打架改由附录 F 承接（seal 零改动）；`handoff_manifest inspect/lookup` 两只读查询子命令；`_members_total` 预填删除改旁车、排除规则精确化、显式登记冲突报错、freeze 案根卫生 WARN；四册手册相对 7.0.4 基线合计净减 42 B，SUITE 入口不变。
     ```
   - 在 `:90`（`## [7.1.0] - 2026-09-16 — −2 收口与重封命令化`）**之前**插入下面整段（段后空一行再接原 7.1.0 标题），逐字：
     ```
     ## [7.1.1] - 2026-09-16 — 三项修复：seal↔零地址、只读查询命令、备份与台账瘦身

     - **出处与根因**：−2 会话实测三处痛点。①`a5_report_seal` 披露检查逐字要求终点完整地址，而 `report-template` 要求正文零地址，执行者被迫在正文写全址表自辩；②五个 −2 会话的 Bash 调用中过半是手写内联 python，以 JSON 键树探测与按地址跨文件查字段为大头，已有命令极少被用；③案根手工 `.bak_*` 副本堆积（三案调研清点 78 件、最大案 32 MB），`EXCLUDE_SUFFIXES` 的 `endswith(".bak")` 对这些名字不匹配，裁决台账 `_members_total` 与 accepted∪excluded 纯冗余、validator 从不读。
     - **披露定为附录（T2，零代码）**：`report-template.md` 把三策略翻转披露表定为**附录 F**（附录允许完整地址；标题含收据 `report_locations` 位置串且唯一），正文实体小节只写"见附录 F"，A5 seal 一行不改、只核该切片；`test_repair_batch_d.py` 加"披露段在附录 F 下"绿例；report-template 42499→42491 B。已封口报告不动。
     - **只读查询命令（T3）**：`handoff_manifest.py` 新增 `inspect --case-dir <案根> --file <file> [--path a.b] [--depth N] [--limit/--offset]`（文本键树/类型/长度/首元素样本，标量样本截 80 字符，列表按分页返回 `next_offset`、不截断条目）与 `lookup --case-dir <案根> --addr …|--addr-file … --in <file>（可重复）[--fields …] [--json]`（跨 identity_cards/balances_final/entity_registry/labels_final/camps 回填地址表，缺址标 MISSING）；两者经 `safe_case_file` 守案根并拒 `sealed/`；既有命令处理函数未改，仅 `main` 新增注册与分派。`test_handoff_manifest.py` 新增 `test_t3_readonly_queries`，内置写事件审计钩子（按案根归属，相对路径写事件记"未归属写事件"不静默跳过，含自检）。不加"禁止手写 python"条文，只替换 split-run/context-discipline 各一行。
     - **备份堆积与台账瘦身（T1）**：`adjudication_validator template/distribution-template` 删 `_members_total` 预填，候选成员清单改写同目录旁车 `<台账名>.members.json`（不进台账不进 schema；旁车先写，失败保留旧台账）；`handoff_manifest` 排除规则改精确：`\.bak(_|$)`、`.superseded` 族、完整目录分量 `_history`（`_pre_`、`.vN.` 不用于排除）；`add_path` 对显式登记或 `--include` 命中排除项报配置冲突 exit 2，不再静默丢弃；`freeze` 加案根卫生 WARN（只提示不拒）；条文"手工历史副本只进 `<案根>/_history/`，活跃路径唯一"、excluded 的 reason 用短句、依据放 evidence（validator 只查 reason 非空，属人工约定非机器保证）；`test_adjudication_validator`/`test_distribution_gate` 改从源 fixture 取成员并保留"老台账带该字段仍 PASS"用例；scan-schemas 104942→104941 B。存量副本搬移是案卷侧动作，不在仓库内。
     - **手册**：相对 7.0.4 基线四册均不增：split-run 28162→28130、context-discipline 9257→9256、report-template 42499→42491、scan-schemas 104942→104941，合计净减 42 B；与 7.1.0 合并后 split-run 为 27772 B。
     - **测试与验收**：三份工单各经 codex 只读复核（T1 三轮、T2 两轮、T3 四轮＋返修单 r1 两轮）后 codex 施工；codex 盲审 T1/T2 PASS，T3 首轮 FAIL（审计钩子对相对路径写事件静默漏记）→ r1 返修 → 定向盲审 PASS，另有 opus 旁证 PASS；`test_handoff_manifest` 283 项通过；与 7.1.0 合并零冲突，合并树全套 `run_all` 通过（计数与环境项处置以 `maintenance/repair-20260916-three-items/t4_done.md` 及调度方验收记录为准）。codex 沙箱无临时目录、不能绑 127.0.0.1 导致的失败项由本机验收覆盖。
     - **成本-质量指标**：生产逻辑文件 2（`handoff_manifest.py`、`adjudication_validator.py`）、新公开子命令 2（均只读）、新增 SUITE 入口 0；外部网络调用 0；不运行真实案卷判断链，判断结论不自动变更。
     ```
   - 索引区与详细条目之外的任何行不动；`archive/CHANGELOG-archive.md` 不动。

## §3 验收（施工者自跑并记入 t4_done.md）
- `git status --porcelain=v1 --untracked-files=all` 只列 §0 四个文件（M）与 `t4_done.md`（??）；`git diff --exit-code HEAD -- references/ scripts/` 退出码 0（记录退出码本身）。
- `python3 -B scripts/tests/changelog_lint.py` PASS（活跃条数比改前 +1）。
- `python3 -B scripts/tests/test_version_consistency.py` exit 0。
- `python3 -B scripts/tests/docs_lint.py --all` PASS。
- `python3 -B scripts/tests/run_all.py`：**只有** 151 PASS、0 FAIL 且四个 Python 验收命令（changelog_lint、test_version_consistency、docs_lint --all、run_all）全部 exit 0，报告才可写「完成」并声明全绿；任何失败（含沙箱环境项：临时目录、127.0.0.1、`/tmp/w3_acceptance` 验收 worktree 缺失）一律写「停工」并逐项列名归因，不得冒充通过；环境项由调度方在**同一最终树**本机补验后才算收口。
- `wc -c SKILL.md` 改前后相等。

## §4 报告 `t4_done.md`
首行 `# 施工 T4: 完成` 或 `# 施工 T4: 停工`；列 §0 四文件各自 diff 行数、四条验收命令的退出码与关键输出行、run_all PASS/FAIL 计数与失败项归因、改前后 `changelog_lint` 活跃条数、`wc -c SKILL.md` 两值。不 commit。
