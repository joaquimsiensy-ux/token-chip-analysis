# 修复批 3 计划（repair-20260814-batch3）

基线：main@411bf18（= 83394ab 六视角 review 冻结基线 + evmobs 开工提交，生产代码与 83394ab 逐字节一致）。
来源：codex 六视角全量 review（`maintenance/review-20260814/`，BLOCK，8 findings）→ Fable 逐条验证全部属实 → 用户裁决分工与两个策略点 → 本 plan 经 Plan agent 评审 + codex @CX 复核（CONDITIONAL BLOCK 四条必改已全部融合）。

## 用户裁决（2026-08-14）

- R10-16 → 方案 B：completeness critic 的每条 findings/non_covered、claim 复核的每个 REFUTED verdict，必须机械对应 blocker 并逐条处置，否则不得 PASS。
- R10-17 → evidence 每条装 10 实义字符门槛（定位=防呆不防伪，台账如实记）。

## 范围重排映射表（防串单，@CX 要求）

| review finding | R10 条目 | 负责会话/分支 | 本批状态 |
|---|---|---|---|
| F-01 A4 语义联动 | R10-16/17（已裁决） | **本批 batch3** | 工单 F01 |
| F-02 EVM 供给观测锚 | R10-13 | evmobs 会话（repair-20260814-evmobs） | 本批禁触 |
| F-03 as_of_block 外锚 | R10-9 | evmobs 会话 | 本批禁触 |
| F-04 deploy-sync 弱闸 | R10-5（原批 4 项，升格提前） | **本批 batch3** | 工单 F04 |
| F-05 env_check 覆盖 | R10-6（原批 4 项，升格提前） | **本批 batch3** | 工单 F05 |
| F-06 不可见字符 | R10-18 | 留批 4 | 不动 |
| F-07 R10 台账漂移 | （新发现） | **本批 batch3** | 收口步 |
| F-08 whitespace | （新发现） | 留批 4（仅 proxy_config.py EOF 属活代码可修） | 不动 |

原 batch2 plan 所写"批 3=F-08/F-11 外锚设计族"已由 evmobs 会话承接；原"批 4 守卫收尾"中 R10-5/6 因升格提前到本批。此为有意重排，非漂移。

## 禁改清单（本批一切施工不得触碰）

- `maintenance/repair-20260814-evmobs/`（另一会话工作区）及未跟踪文件 `scripts/tests/test_evm_observation.py`
- `archive/**`、`blind-reviews/**`、历史 CHANGELOG 条目（含 6.42.0 及更早的 v3 表述）
- `scripts/lib/supply_truth_gate.py` 与 `scripts/report/shared_release_receipt.py` 的两份 `_meaningful_text` 本体（行为向量守卫锁定）
- `shared_release_receipt.py` 约 490 行、`audit_release_gate.py` 约 839 行的 `schema = receipt.get("schema")` 直赋值行（invariant_scan 消费者探测锚点）
- evmobs 正在施工的 supply_truth/observation 相关区段（本批工单不涉及）

## 工单与执行编排

按批准计划的 commit 划分串行执行，每单一 commit，收工点全量 suite 绿：

1. **工单 F01**（`workorder_F01.md`）：A4 语义联动全量一次落地（门槛+linkage+entrypoint+v4/artifact v2+manifest+文档+f02 适配+新测试 A~E 族）。
2. **工单 F04**（`workorder_F04.md`）：deploy-sync 重写+注入反例。
3. **工单 F05**（`workorder_F05.md`）：env_check 三层对账+注入反例。
4. **收口**：r10_ledger 施工期状态（R10-1/3/4/7 标 CLOSED 6.41.0 → 现役 19；R10-5/6/16/17 标 FIXED_PENDING_REVIEW）+ 台账自洽小守卫 + CHANGELOG/VERSION 五处升版（6.43.0，若 evmobs 先合并则让号 6.44.0）。
5. 盲审（codex 独立线程）→ 消化轮 ≤3 → closure（台账终态：现役 15）→ 合并 main → push。

## 执行纪律

- 施工方：codex（exec 后台任务，workspace-write 沙箱）。**工单头统一约束：禁一切 git 写命令**；commit 由裁判（Fable 本会话）代做，add 用精确路径。
- 裁判验收：git diff 逐 hunk 审查（diff→finding 映射，未映射 hunk=0）+ 独立复跑测试退出码；不读施工过程栈帧。
- 哨兵纪律：委派后必挂状态轮询；后台 codex exec 必须 `</dev/null`；僵死则 cancel+resume，首条指令=先把已有进度落盘。
- 版本件（VERSION/CHANGELOG/SKILL.md 版本注释）工单 commit 不动，收口统一 bump（test_version_consistency 才不红）。
