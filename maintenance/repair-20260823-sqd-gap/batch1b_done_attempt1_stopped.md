# 批 1b 施工报告：前置核验停工

## 结论

**STOPPED_LINE_MISMATCH。** 未进入批 1b 施工。

工单明确要求“发现工单行号与文件实况不符 → 停工写 done 报告（不要猜）”。前置核验发现：

- 工单白名单第 2 项把 `FORMAL_E2E_REQUIRED_PRODUCERS["sol"]` 标为“现 `:85-91`”。
- 当前 `scripts/tests/invariant_scan.py` 实况中，`"sol": frozenset({` 位于第 **81** 行，条目止于第 **87** 行。
- `PLAN.md` §4.5.2 第 263 行同样把该位置登记为 `invariant_scan.py:81 FORMAL_E2E_REQUIRED_PRODUCERS["sol"]`。
- 同一文件的 `FAILURE_ARTIFACT_COVERAGE` 位于第 99 行，与工单该处行号一致；因此前一处不能在“不要猜”的约束下自行按整体漂移解释。

据此按硬停工线停止，没有把 `:85-91` 猜改为 `:81-87`，也没有继续核验或执行后续施工项。

## 前置冻结实况

| 项 | 实况 |
|---|---|
| 分支 | `fix/sqd-gap-v6520` |
| HEAD | `132b20b8c3c385423c30abddd67266e78bef0cbd` |
| 代码面基线 | `f06078ef0bbf6d693baf2186212c1e0a4634f578`（提交主题含 `v6.51.0`） |
| VERSION | `6.51.0` |
| 开工前工作树 | `git status --short --branch` 仅输出 `## fix/sqd-gap-v6520`，无既有修改 |

已完整读取：

- `maintenance/repair-20260823-sqd-gap/PLAN_errata_batch0.md` 全文（E1–E19，含 E13、E17–E19）
- `maintenance/repair-20260823-sqd-gap/PLAN.md` §4.5.2 与 §5

## 改动清单

仅新增本报告：

- `maintenance/repair-20260823-sqd-gap/batch1b_done.md`

没有改动或新建其他白名单文件。

## 登记面增项表

未执行；0 项。停工发生在第一次登记面编辑之前。

## 35 项映射实况

未编写、未运行。四个新测试文件均未创建，`batch1b_red_evidence.txt` 未创建。

## 四份草案 errata 小修对照

未执行；E14/E17/E18 对应四份草案均未改动，`contracts_draft/INDEX.json` 未改动。

## 校验与红证

- 未运行四件先红测试：测试文件尚未创建。
- 未运行 `docs_lint.py --all`：没有文档施工可验。
- 未运行 `run_all.py`：硬停工发生在施工前；不存在本批引入回归需要收口。
- 未创建 `batch1b_red_evidence.txt`，避免伪造“已施工”的红证载体。

## 发现项

1. 工单 `invariant_scan.py` 第一处亲核行号与当前文件实况不符：工单 `:85-91`，实际 `:81-87`；PLAN §4.5.2 支持实际起点 `:81`。

## 未做

- 未改 `invariant_manifest.json`、`invariant_scan.py`、contract manifest/snapshot、`scan-schemas.md`。
- 未创建四个测试文件，未实现 35 项先红。
- 未改任何生产脚本。
- 未改 PLAN、errata、版本文件、CHANGELOG、SKILL.md 或其他 references 文档。
- 未改四份 errata 草案或 INDEX。
- 未改 `run_all.py`、`producer_history.py`。
- 未联网、未 commit、未切分支。

## 白名单自述

本次唯一写入是工单白名单内的 `maintenance/repair-20260823-sqd-gap/batch1b_done.md`。停工后没有继续探索性施工，也没有写白名单外文件。

## 批 6 硬闸登记

批 6 必做：**banned needles 4 组与文档修订同 commit**。本批按工单不得提前添加；本次又因前置行号不符而未进入施工。

## 复工所需裁决

请权威方二选一后重发/修订工单：

1. 将 `FORMAL_E2E_REQUIRED_PRODUCERS["sol"]` 的亲核位置更正为当前实况 `scripts/tests/invariant_scan.py:81-87`；或
2. 明确授权以符号定位为准、行号仅作非约束提示。

在得到该裁决前，不应继续批 1b。
