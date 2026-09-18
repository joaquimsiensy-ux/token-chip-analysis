# 工单 F02 复核提示词（只读，r2）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F02复核：通过` 或 `# 工单F02复核：退回`。退回时逐条给出：编号（F02-R2-NN）、工单位置、事实、修订建议。通过时列出实际核过的项。
3. 这是修复计划复核（非攻击式验收）。

## 任务
复核 `maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F02_circulating.md`（**v2**）是否正确消化了 `review_F02_reply_r1.md` 的两条意见，且没有引入新问题。工作目录＝本仓库根（`scripts/` 与 8b041842 逐字节相同；F04/F05 尚未施工，`test_stage2_closeout.py` 锚只核唯一性）。逐项核：
a) R1-01：§2.6 改用 `from test_report_facts import _r07_case` 独立 tempdir 夹具——核 `test_report_facts` 模块级 import 是否确无副作用（`:12-32`）、`_r07_case` 夹具在 `derive_facts` 下是否 formal 且 e1 current 100/total 1000；`update()`（`test_stage2_closeout.py` 既有 helper）对 `root / "state_source.json"` 是否可用；`tempfile`/`Path` 是否已导入；`dir="/private/tmp"` 在沙箱/本机是否可写（对照 `test_report_facts.py:86` 同款用法）；用例前半 baseline 断言（无键、NOTE 未声明、无"包含下限"）在 `_r07_case` 上是否成立。
b) R1-02：§1.3 表述是否准确（producer sha 例外、token 三键、同版本幂等）；§4 迁移说明是否覆盖 r1 列出的 A4/图 2 旁车/工单/closeout/A5 绑定重建。
c) 重核 §2 全部锚文本命中数与行号；§0.8 新增 `test_repair_batch_d.py` 是否与本段相关（r1 提到 `:1205` 夹具）。
d) 终点判据（`ruling_20260918.md` `flow_migration` 三分支）在 v2 下是否仍必然成立；§2.6 是否真正固化了分支①的 producer→consumer 贯通。
e) 版本档位：用户已裁决 9.0.0（`ruling_20260918.md` 追加裁决），无需再议。
