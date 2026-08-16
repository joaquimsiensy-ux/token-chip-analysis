# 【收口工单】批 3 台账同步（F-07）+ 版本收口 6.43.0 + 台账自洽小守卫

> 施工方：codex。**禁一切 git 写命令**；只改文件。完成后写 `maintenance/repair-20260814-batch3/workorder_closeout_done.md`，末行 WORKORDER_CLOSEOUT_COMPLETE。
> 禁触：`maintenance/repair-20260814-evmobs/`、`archive/**`、`blind-reviews/**`、历史 CHANGELOG 条目（只新增 6.43.0，不改 6.42.0 及更早）。

## 1. r10_ledger.md 状态同步（maintenance/repair-20260813-sixlens/r10_ledger.md）

F-07 实锤：批 1（v6.41.0）已修的 4 条在台账仍列开放。逐条改：

- R10-1 行：条目名后加【CLOSED 6.41.0】，修法线索列改为：已闭合——standard_charts.select_fig1_series 白名单外键 raise ValueError（commit c5f3458）；A5 图例绑定并入 R10-7 同批闭合。
- R10-3 行：加【CLOSED 6.41.0】，改为：已闭合——replay_pass1/stream/duck gate false 全 exit 4、pass2 消费 gate_pass fail-closed（commit d78e210）。
- R10-4 行：加【CLOSED 6.41.0】，改为：已闭合——fetch_hypersync_v2 移除位置 api_token，唯一位置参数 from_block，token 走 --token-file/HYPERSYNC_TOKEN/默认文件（commit 253ac79）。
- R10-7 行：加【CLOSED 6.41.0】，改为：已闭合——a5_report_seal 生成并重验 fig1_legend_receipt（commit e5c8043）。
- R10-5 行：加【FIXED_PENDING_REVIEW 6.43.0 批3】——工单 F04 已落地（无界豁免删除+canonical fail-closed），待批 3 盲审转 CLOSED；见 `maintenance/repair-20260814-batch3/workorder_F04_done.md`。
- R10-6 行：加【FIXED_PENDING_REVIEW 6.43.0 批3】——工单 F05 已落地（pyproject 机械派生三层闭合+requires-python），待盲审转 CLOSED；见 workorder_F05_done.md。
- R10-16 行：状态"待用户裁"改【FIXED_PENDING_REVIEW 6.43.0 批3】——用户 08-14 裁决方案 B（findings/non_covered/REFUTED 机械转 blocker 逐条处置），工单 F01 已落地；见 workorder_F01_done.md。
- R10-17 行：状态改【FIXED_PENDING_REVIEW 6.43.0 批3】——用户裁决装 10 实义字符门槛，工单 F01 已落地。**关闭口径必须如实写窄**：本批只关"空壳/极短 evidence"形式面（防呆不防伪）；"结构化 evidence（证据类型/引用对象/复算产物绑定）"不在本批，残余保留在案。
- 第六节"状态"：追加一行 2026-08-14 批 3 状态：批 1 补账 CLOSED 4 条（R10-1/3/4/7，v6.41.0 已修当时未记，F-07 集成漂移修正）；批 3 施工 FIXED_PENDING_REVIEW 4 条（R10-5/6/16/17）；当前现役 = 23 − 4 = **19**（其中 4 条待盲审转 CLOSED 后 → 15）。
- 全文不得出现悬空的"契约 CT-XXX-NN"字样（docs_lint 全库扫）。

## 2. 台账自洽小守卫（追加进 scripts/tests/test_repair_batch3_gates.py 新小节）

防 F-07 根因复发的最小机器面，读真实 r10_ledger.md 校验：

- R10 条目 ID（R10-1…R10-27）唯一无重复。
- 每条状态可机械识别为枚举之一：开放（无标记）/ CLOSED x.y.z / FIXED_PENDING_REVIEW x.y.z 批N / 接受在案类（"接受""留批""待"开头的既有表述归开放类）。
- 按状态机械计算的"现役数"（总条目 − CLOSED 数）与第六节状态行里声明的当前现役数字一致。
- 先红验证：用临时副本注入"重复 ID"与"计数不一致"两个反例各红一次，真台账绿。
- 解析器对台账格式变化要稳健（按行 rg R10-\d+ 与【CLOSED / 【FIXED_PENDING_REVIEW 标记），格式认不出 → FAIL 而非跳过。

## 3. 版本收口 6.43.0（五处同步，test_version_consistency 守着）

1. `VERSION` → 6.43.0
2. `pyproject.toml` [project].version → 6.43.0
3. `CHANGELOG.md` 索引区顶部新增（全角括号式）：
   `- **6.43.0**（2026-08-14）批 3 弱闸三线收口：A4 blocker 语义联动+10 门槛+entrypoint 身份（F-01→R10-16/17）、deploy-sync 严判（F-04→R10-5）、env_check 机械派生（F-05→R10-6）、R10 台账同步+自洽守卫（F-07）`
4. `CHANGELOG.md` 详情区顶部新增 `## [6.43.0] - 2026-08-14 — 批 3 弱闸三线收口（六视角 review F-01/04/05/07）`，总述一句后分条：
   - **F-01 A4 语义联动（工单 F01）**：blocker 必填 source={kind,ref} 机械定位符；validate_blocker_linkage 双向对账（缺账/幽灵/重复拒）两侧独立执行；finalize 账不全 rc2 不落盘、账全未决落盘 BLOCKED；evidence/resolution 10 实义字符门槛（_has_min_meaningful_chars，防呆不防伪）；entrypoint sha 跨角色全局唯一（防误复用，非独立性证明）；adversarial-review/v4 + artifact/v2，存量 v2/v3 须重跑（先报 producer 失效属预期）。先红 25 项。
   - **F-04 deploy-sync 严判（工单 F04）**：删 MIGRATION_CHANGED 无界豁免（归因 ede24d7 解耦隐式过期）；canonical 安装路径缺部署目录 fail-closed rc1，非 canonical checkout 打 SKIP_NON_CANONICAL_CHECKOUT rc0；校验主体纯函数化。先红 4 项。
   - **F-05 env_check 机械派生（工单 F05）**：受检集合唯一来源 pyproject 21 直接依赖；三层闭合（direct→lock 唯一 pin→installed 全等）+ lock pin 须满足 pyproject 下限；PEP503 规范化；受控说明符白名单 fail-closed；requires-python 检查；pre-commit 第二挂载点联动实证。先红 8 项。已知边界：平面 lock 无法判已删直接依赖残留。
   - **R10 台账（F-07）**：批 1 已修 4 条补记 CLOSED 6.41.0（集成漂移修正）；批 3 四条 FIXED_PENDING_REVIEW；现役 23→19（盲审后→15）；新增台账自洽守卫（ID 唯一/状态枚举/计数一致）。
   - **6.43.0 前身冻结基线**：main@83394ab 97 项全绿 rc0；本批收口时 SUITE 99 项（+test_repair_batch3_f01+test_repair_batch3_gates）全绿 rc0。
5. `SKILL.md` 第 23 行版本注释 → `skill-version: 6.43.0`

## 4. plan.md 基线行修正（maintenance/repair-20260814-batch3/plan.md）

首段"基线：main@411bf18（= 83394ab …）"整句改为：
`基线：main@83394ab（六视角 review 冻结基线）。开工时曾误从 evmobs 分支 tip 411bf18 切出，四 commit 已 rebase --onto 83394ab 剥离，与 evmobs 工程彻底解耦（本句为事后修正记录）。`

## 5. 验收标准（裁判执行）

- `python3 scripts/tests/test_version_consistency.py` rc=0；`python3 scripts/tests/changelog_lint.py` rc=0；`python3 scripts/tests/docs_lint.py --all` rc=0；gates 测试（含新台账守卫小节）rc=0；run_all 全量 99 项 rc=0。
