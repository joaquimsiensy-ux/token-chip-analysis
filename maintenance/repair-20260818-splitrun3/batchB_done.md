# 批 B 完工报告｜外围文档指针批

## 基线与边界

- 工作目录：`/Users/uravvv/.claude/worktrees/tca-splitrun3`
- 分支：`fix/splitrun3-20260818`
- HEAD：`e1be99ab25c0a6f60091d7a7b635ab6097e532c8`
- 开工前五个施工文件相对 HEAD 均无改动；工作树中批 A 的既有未提交改动完整保留。
- 本批人工施工只改工单白名单五文件，并新增工单明确要求的本 done 报告；未执行 `git commit`，未执行 `git push`。

## 同族清单（施工前）

- `rg -n "opus" references/context-discipline.md references/research-workflows.md`：7 处；`context-discipline.md` 3 处，`research-workflows.md` 4 处。§二b 的标题和定位段各自保存档位副本。
- `rg -n "^\d+\." references/context-discipline.md`：刀 1 主序列为 1–6；刀 2 误从 6 开始，形成两个 `6.`；刀 2 后续为 7–10，刀 3 为 11–13。
- `rg -n "报警才人工深挖|人工深挖" references/`：2 处；`analyze-workflow.md:134` 与 `playbook-entity-cluster-tiering.md:44`。
- `rg -n "split-run −1/−2|−1/−2" references/context-discipline.md`：1 处，位于原第 7 条阅读路由。

## 编号修复前后对照

施工前主序列：

```text
刀 1：1, 2, 3, 4, 5, 6
刀 2：6, 7, 8, 9, 10
刀 3：11, 12, 13
```

施工后主序列：

```text
刀 1：1, 2, 2b, 3, 4, 5, 6
刀 2：7, 8, 9, 10, 11
刀 3：12, 13, 14
```

验收 `rg` 显示刀 1–3 主序列 1–14 唯一递增，`2b` 为工单特例。文件后半「断点恢复」是独立有序列表 1–5，不属于刀 1–3 主序列。

## T1～T5 完成情况

- T1：`context-discipline.md` 的刀 1 公告与外包纪律落盘；T1.1 定稿代码块经 `diff` 与工单第 37–53 行逐字比对，无差异。判断档、禁止外包原文未动；分段执行同步到 −3；刀 2、刀 3 编号修复；阅读路由同步为 −1/−2/−3。
- T2：`analyze-workflow.md` 只增两句，分别声明 ET-1 报警地址证据采集归 −1、人工深挖定性归 −2，以及 A5 装配执行归 −3、−2 收口于正文与装配工单；既有句未改。
- T3：`playbook-entity-cluster-tiering.md` 只替换 ET-1 定义句内指定片段，明确观察事实层归 −1、判断层归 −2；该行之外未改。
- T4：`report-template.md` 的交付前 checklist 标题下新增 −2/−3 归属句。
- T5：`research-workflows.md` §二b 删除标题和定位段的独立档位副本，改为指向 `context-discipline` 刀 1；第 1/2/3/4 节模板本体未改。

## 刀 1 公告自审

- 14 项逐项区分机械装配/执行与主线判断：候选收编、支路定性、实体边界、判级、翻转裁决及裁决修改均明确留在主线。
- `verdict`、`accepted_members`、`excluded_members.reason`、`evidence`、`linked_entity_id` 明确由主线亲填，未分配给子代理。
- 子代理只产非权威中间产物；权威台账、seal、freeze、裁决字段仍由主线亲填亲跑。

## 验收输出摘要

- `python3 scripts/tests/docs_lint.py --all`：exit 0；`PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）`。
- `python3 scripts/tests/test_contract_routes.py`：exit 0；`R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合`。
- `rg -n "^\d+\." references/context-discipline.md`：exit 0；刀 1–3 主序列 1–14 唯一递增，`2b` 特例存活。
- `rg -n "报警才人工深挖" references/`：exit 0；只命中 `analyze-workflow.md:134` 的既有句；其新增归属句在 :136，tiering 已改为分层后的「再人工深挖定性」。
- `rg -n "A3 判断层＋A4–A5" SKILL.md references/ commands-staging/ && ...`：exit 0；输出 `旧口径清零`。
- `rg -n "effort.?high" references/research-workflows.md`：exit 0；只命中 :149 的唯一指针句一处。
- `python3 scripts/tests/test_repair_batch_a.py && python3 scripts/tests/test_g3_docs_guards.py`：exit 0；前者 `PASS batch A F-01/F-02 regressions 45/45`，后者 F-08 A0、F-08 A2、F-13、F-05 四项全部 PASS。
- `git diff --check`：exit 0，无输出。

## T5 验收正则收口说明

工单给出的非定稿示例短语 `机械档 opus+high` 本身不匹配验收正则 `effort.?high`。为同时满足「只保留唯一指针」与验收全绿，最终使用等义指针括注 `机械档 model=opus、effort=high`；未恢复标题副本或第二处模型钉法，正则恰好命中一处。

## 最终改动范围

```text
3  0  references/analyze-workflow.md
26 10 references/context-discipline.md
1  1  references/playbook-entity-cluster-tiering.md
2  0  references/report-template.md
2  2  references/research-workflows.md
```

除工单要求的 `batchB_done.md` 外，未人工改动白名单外文件。会话自动日志 `batchB_codex.log` 由运行环境持续记录，不是施工内容。未 commit。
