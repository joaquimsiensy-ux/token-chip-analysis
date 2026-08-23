# 批 2c 完工报告：探针定期 resume 检查点

## 状态

`DONE_GREEN`

施工基线：分支 `fix/sqd-gap-v6520`，HEAD
`b005a468b919fd8c39108f513db862a2edb84555`。未 commit、未切分支、未联网，未进入批 3。

## 改动点

### `scripts/solana/sqd_coverage_probe.py`

- `_scan_ranges(...)` 新增关键字参数 `checkpoint=None`、`checkpoint_every=0`。
- 新增 `completed_since_checkpoint`，每个已由主线程写入 ledger/counts 的完成页使其加一。
- 触发位置严格位于每个 batch 的 `for _shard_start, pages in sorted(completed)` 处理循环之后；只有 `checkpoint` 非空、阈值为正且累计完成页数达到阈值时才调用。回调异常不捕获，沿现役 `main()` 异常路径返回 2。
- checkpoint 成功后向 stderr 写
  `[sqd-coverage] checkpoint written (completed N requests)`；文本经 `_safe_text(...)` 处理。
- 唯一实际 main 调用点（原 `:829`）传入使用同一组 `pending`、`identity`、`started_at`、`counts`、`ledger` 的 `_write_resume(...)` lambda；首跑和 `--resume` 共用该控制流。
- argparse 新增 `--checkpoint-every N`，类型 `int`、默认 `2000`；`0` 关闭。

未改 `_write_resume`、`_pending_state`、coverage schema、产物字段、发布流程或 `compute_probe_id`。

### `scripts/tests/test_sqd_coverage_probe.py`

- 新增第 11 组 `test_periodic_checkpoint_kill_resume_at_batch_boundary`。
- 动态离线 fixture 覆盖 5 个 SQD 页；`workers=1` 时首 batch 为 4 页。
- `_write_resume` 替身先真实写 checkpoint，再抛 `RuntimeError("injected-kill")`：断言首跑返回 2、checkpoint/resume v1 存在、只持久化首 4 页。
- `--resume` 后断言 SQD 只请求剩余 1 页；最终成功 full 页并集覆盖整个案区间，ledger `seq` 从 0 连续。
- 默认 `--checkpoint-every 2000` 的 5 页成功跑不触发中间 checkpoint，发布代中不存在 `resume_state.json`。

## RED → GREEN

- RED：先只加入第 11 组，运行 `python3 scripts/tests/test_sqd_coverage_probe.py`，退出码 2；现役 argparse 报 `unrecognized arguments: --checkpoint-every 1`。
- GREEN：完成生产实现后重跑同命令，退出码 0，`PASS SQD coverage probe: 11/11 offline groups`。

完整原始摘要见 `batch2c_green_evidence.txt`。

## probe_id / 等价断言说明

未断言中断续跑与一次跑通的 `probe_id` 相同。原因不是 checkpoint 改变契约，而是现役 coverage_map 本来就绑定 `ledger` 的 SHA256 和请求数；resume 会在载入旧 ledger 后追加一次新的 metadata 请求记录，因此续跑 ledger 比一次跑通多一行，内容寻址的 `probe_id` 应当不同。

测试改用工单允许的等价口径：两路最终 `slot_counts.bin.gz` SHA256 相同、`blocks.bin.gz` SHA256 相同、coverage `summary` 相同；另验证成功扫描区间并集和 ledger 序号连续。

## 测试结果

- `python3 scripts/tests/test_sqd_coverage_probe.py`：退出码 0，11/11。
- `python3 scripts/tests/run_all.py`：退出码 1，只有 4 个既有红项，无新增红项：
  - `invariant_scan.py` 的批次先红登记面（当前 16 discrepancies）；
  - `test_batch4_invariant_guards.py:198`；
  - Solana/EVM 两项 vertical slice 在本沙箱绑定回环地址时报 `PermissionError: [Errno 1] Operation not permitted`。

## Fable 本机复验建议

先跑离线回归与全套：

```bash
python3 scripts/tests/test_sqd_coverage_probe.py
python3 scripts/tests/run_all.py
```

ARC 全扫沿用已冻结的 `--mint`、`--case-root`、`--from-slot`、`--to-slot` 与 reference RPC 参数，只增加：

```bash
python3 scripts/solana/sqd_coverage_probe.py \
  --mint <ARC_MINT> --case-root <ARC_CASE_ROOT> \
  --from-slot <FROM_SLOT> --to-slot <TO_SLOT> --full \
  --checkpoint-every 2000 --workers 16 \
  --reference-rpc <REFERENCE_RPC>
```

运行中在另一终端重复核对 mtime/大小滚动更新：

```bash
ls -lT <ARC_CASE_ROOT>/data/sqd_coverage/pending-*/resume_state.json
ls -lT <ARC_CASE_ROOT>/data/sqd_coverage/pending-*/slot_counts.bin.gz
```

终止一次探针后，使用完全相同的冻结参数加 `--resume` 重启，并确认日志只请求 `_missing_ranges` 给出的 UNSCANNED 缺口。
