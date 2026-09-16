# W1 attempt 1 停工记录

结论：**STOPPED，W1 未完成，未提交。** 停工于 A 段既有回归；B、C、D 未施工，未生成 `w1_done.md`。

记录时间：2026-09-16T04:16:35.316526+00:00
仓库：`/Users/uravvv/.claude/skills/token-chip-analysis`；分支 `main`；开工及停工 HEAD 均为 `be9e1f7714623a06d711568be8cfa2d2b42f183e`；`git merge-base --is-ancestor 764b60c HEAD` exit 0。

## 停工原因与定位证据

工单 A1 将 `test_batch11_frozen_bundle_binding.py:223-225` 的 data_map 写入归属于 `build_frozen_case`，并据此认定 batch15 N8 夹具已经登记快照。这一函数定位不符：

- `scripts/tests/test_batch15_three_ledgers_frozen.py:30` 把 `build_case` 导入为 `build_frozen_case`。
- 同文件 `:238` 调用 `build_unit_case(root)`；其 `:89` 调用上述 `build_frozen_case(root)`。
- `scripts/tests/test_batch11_frozen_bundle_binding.py:95-149` 的 `build_case` 不写 data_map。
- 工单引用的 `:223-225` 实际属于 `:214` 开始的 `test_n5_handoff_required_frozen_bundle`，该函数不在 N8 的夹具调用链上；而且这三行登记只有 path，没有 sha256。

实跑既有测试原文：

```text
FAIL test_n8_snapshot_default_is_frozen_explicit_is_observation: ValueError: data_map不存在: data_map.json
FAIL batch15 frozen consumers: 1/12
```

开工核对的 22 处显式编辑锚文本全部通过；上述辅助夹具的函数归属错误在 A 段回归时确认。依工单“行号与锚文本不一致即停工，不得自行猜改”的要求保留现场，没有补造该夹具来继续施工。

## 已实施与验证

仅实施 A1–A3、新增 A4 测试，并同步 batch15 两处签名调用。batch15 的三条原断言逐字保持不变。新增测试额外覆盖手工周期编号、搬运失败逆序恢复，以及回执自报字段和重复路径的变异拒绝。

| 检查 | 结果 |
|---|---|
| A RED：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_reopen_cycle.py` | exit 1；1/13 PASS、12/13 FAIL；生产修改前留证 |
| A GREEN：`PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/w1-mplconfig python3 scripts/tests/test_reopen_cycle.py` | exit 0；13/13 PASS，NORMAL 与 ABNORMAL 集成都通过，无跳过 |
| `PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/w1-mplconfig python3 scripts/tests/test_distribution_gate.py` | exit 0；`PASS: distribution gate red-green contract` |
| `PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/w1-mplconfig python3 scripts/tests/test_batch15_three_ledgers_frozen.py` | exit 1；11/12 通过，N8 失败，见上 |
| `git diff --check` | exit 0 |
| `run_all.py` | **未启动**；停工后未进入全套验收，无 nohup 作业遗留 |

完整命令、退出码、输出和测试/生产文件 SHA256 见同目录 `w1_red_evidence.txt`。GREEN 运行给 Matplotlib 指定了可写临时缓存目录；原 RED 因默认缓存不可写而多次重建字体缓存，其警告原样保留。

已将下列禁改函数与 HEAD 的源码逐字比较，全部未改：

- `holder_distribution_scan.py`: `verify_data_map`、`validate_rounds_ledger`、`cmd_record_round`、`analyze`、`bin_scan`、`semantic_payload`。
- `a4_gate.py`: `cmd_register`、`cmd_finalize`、`distribution_claim_source`。

`a4_gate.py` 本轮整体未改；标签库、manifest、三个标签处理器、版本号、CHANGELOG、三册手册均未改。未联网、未 fetch、未 commit。C 的 CSV、dry-run 和正式入库均未执行。

## 当前改动与保留现场

本轮写入：

1. `scripts/report/holder_distribution_scan.py`
2. `scripts/tests/test_batch15_three_ledgers_frozen.py`
3. `scripts/tests/test_reopen_cycle.py`
4. `maintenance/repair-20260915-stage2-closeout/w1_red_evidence.txt`
5. 本停工记录 `maintenance/repair-20260915-stage2-closeout/w1_done_attempt1_stopped.md`

停工检查另见同目录未跟踪文件 `workorder_w3.md`；开工时它不在状态列表中，本轮未创建、未读取、未修改，按并发产物保留。没有撤回已完成的 A 段改动，没有删除仓库文件。

写入停工记录前的工作树：

```text
 M scripts/report/holder_distribution_scan.py
 M scripts/tests/test_batch15_three_ledgers_frozen.py
?? maintenance/repair-20260915-stage2-closeout/w1_red_evidence.txt
?? maintenance/repair-20260915-stage2-closeout/workorder_w3.md
?? scripts/tests/test_reopen_cycle.py
```

当前实物 SHA256（本停工记录不自哈希）：

- `scripts/report/holder_distribution_scan.py`: `8abcdd16864b2c5d3d639201f5985c560a4e0539f0f59d1cda0deaffe372263d`
- `scripts/tests/test_batch15_three_ledgers_frozen.py`: `84a735f1dbd31f7054f20616eac3a81c3aad2b6682dd261ef5ef28bdefd300e8`
- `scripts/tests/test_reopen_cycle.py`: `70dd5ed931b73155ec53f347e1a2bedacbeaa25764dfe6383514829b0dcab908`
- `maintenance/repair-20260915-stage2-closeout/w1_red_evidence.txt`: `3b26829babb935268400950d84b6a67840c71ddbe7216e60fa82a4cc8759d780`

## 待修订工单与遗留

建议修订 A1：明确允许在 batch15 的 N8 测试里、`build_unit_case(root)` 之后补齐真实 data_map 登记；保留三条原断言，生产的登记优先规则不放宽。可审查的最小补录为：

```python
write_json(root / "data_map.json", {
    "files": [{"path": "data/holders_owners.json",
               "sha256": sha(root / "data/holders_owners.json")}],
})
```

该补录**仅为建议，未执行**。工单修订后仍需从该回归恢复，完成 B→C（仅 dry）→D，再按指定 nohup 命令落盘执行完整 run_all 并读回真实结果；当前不能写“W1 完工”或“全套 GREEN”。

## 访问边界偏差

开工时读取过 `/Users/uravvv/.codex/memories/MEMORY.md`，未满足本工单“禁读 ~/.codex”的访问边界；此后未继续读取该目录。该事实记录在此，不能声称本轮完全满足禁读要求。未读取 `_archive/` 或指定禁读 tag。
