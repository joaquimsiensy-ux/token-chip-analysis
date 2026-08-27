# Batch 3c 第一段完成报告

日期：2026-08-25

## 开工门禁

- 基线 HEAD：`985690edc81a8357b657f4de51278353dc7960e8`，匹配工单 `985690e`。
- `_census_body()` 锚点匹配：非法字段位于工单所述 `scripts/solana/sqd_gap_repair.py:556`。
- 开工时第一段白名单目标无既有改动。
- 工作树原有未跟踪文件 `E21_E22_decision_final.md` 与 `batch3c_workorder.md` 保持不动。

## 第一段施工

1. `scripts/solana/sqd_gap_repair.py`
   - 仅从 `_census_body()` 的 `fields.block` 删除 `"parentSlot": True`。
   - 未改名为 `parentNumber`，未加入无消费方字段。
2. `scripts/tests/test_batch3c_census_fields.py`
   - 新增离线守卫，约束 block 字段必须属于 SQD HTTP 400 明文给出的白名单，并精确等于当前消费所需 `{number, hash}`。
   - 约束 transaction 字段精确等于已实测且被消费的 `{transactionIndex, signatures, err}`。

## 先红后绿

- RED：先新增守卫、保留生产代码中的 `parentSlot`，测试退出码 `1`，精确拒绝 `unsupported SQD block fields: ['parentSlot']`。
- GREEN：删除非法字段后，同一命令退出码 `0`，输出 `PASS batch3c census fields match the SQD contract`。
- 完整原始证据见 `batch3c_green_evidence.txt`。

## 边界复核

- 生产代码差异只有 `_census_body()` 一处删除。
- Helius 响应侧四处合法 `parentSlot` 保持不动。
- 未联网，未 commit/push，未改第二段白名单。
- 未改 `producer_history.py`、`run_all.py`、版本文件或 `CHANGELOG.md`，也未运行 `run_all.py`。

## 发现项

无工单矛盾。

## 停工点

第一段完成。按两段提交协议停工，等待验收方 commit 并写入 `batch3c_stage2_anchor.txt`；本次不执行第二段。
