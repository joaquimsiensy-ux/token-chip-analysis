# 批 2c 工单 v2（codex 施工；v1 因'三处调用'锚文本与实况不符被 codex fail-closed 停工，见 batch2c_done_attempt1_stopped.md——实况仅一处调用）：探针定期 resume 检查点（E23）（分支 fix/sqd-gap-v6520，基线 b005a46）

- 目标对齐：ARC 全区间扫（1.34 亿 slot，16 线程≈22 小时）中途被杀不能全丢。现役 `scripts/solana/sqd_coverage_probe.py` 只在整趟扫完仍有 UNSCANNED（:849-850 `_write_resume(pending, identity, started_at, counts, ledger)`）或 getBlocks 配额停工（:862）时写 `resume_state.json`。本批只加"主线程定期检查点"，**不改任何契约/产物语义/probe_id 计算**。
- 权威：`PLAN_errata_batch0.md` E23；`batch2b_fable_acceptance.md` §5。
- 离线、不 commit、不联网、完成即停；行号/锚文本与实况不符即停工报告。

## 实况锚点（b005a46）
- `_scan_ranges(transport, counts, base_slot, ranges, workers, ledger, endpoints, *, mode="full")` :307-358；主线程在 `for _shard_start, pages in sorted(completed):` 循环内把每页 `part` 写进 `counts` 并 `completed_count += 1`（:346-353）；`PROGRESS_EVERY` 进度打印（:354-357）。
- `_write_resume(pending, identity, started_at, counts, ledger, stopped=None)` :681-690：写 `slot_counts.bin.gz`/`ledger.jsonl`/`resume_state.json`（identity/started_at）并 `_fsync_dir(pending)`。
- `_pending_state(parent, args, sqd_identity)` :658-678：`--resume` 时按 identity 匹配 `pending-*/resume_state.json`。
- main 里 `--resume` 分支读 `started_at = resume["started_at"]`（:792）、`missing = _missing_ranges(counts, args.from_slot)` 后只扫缺口（:826-829）。
- 参数：`--workers` :983、`--resume` :985、`--no-getblocks` :986。

## 白名单
1. `scripts/solana/sqd_coverage_probe.py`：
   - `_scan_ranges` 新增关键字参数 `checkpoint=None, checkpoint_every=0`：在**每个 batch 的 `sorted(completed)` 处理循环结束后**（即该 batch 全部页已落 ledger 与 counts，主线程、无并发写），若 `checkpoint is not None and checkpoint_every > 0` 且自上次检查点起累计完成页数 ≥ `checkpoint_every`，调用 `checkpoint()`（失败按异常抛出，不吞）。**只在 batch 边界触发**（避免半 batch 状态）。
   - 新参数 `--checkpoint-every N`（int，默认 2000；0＝关闭）。main 里**所有实际**的 `_scan_ranges(...)` 调用（b005a46 实况：仅一处 `:829`，对 `_missing_ranges(counts, args.from_slot)` 的统一缺口结果调用 `mode="full"`；known-map/recheck 等路径不经 `_scan_ranges`，不接）传入 `checkpoint=lambda: _write_resume(pending, identity, started_at, counts, ledger)` 与 `checkpoint_every=args.checkpoint_every`；**`identity`/`started_at`/`pending` 用 main 里已算出的同一批变量**（首跑与 `--resume` 两路都要能工作）。
   - 检查点写出的 `resume_state.json` 格式不变（`sqd-coverage-resume-v1`），`--resume` 读回后 `_missing_ranges` 只补 UNSCANNED——不需要改 `_pending_state`。
   - stderr 进度行加一条 `[sqd-coverage] checkpoint written (completed N requests)`（经 `_safe_text`/无密钥内容）。
2. `scripts/tests/test_sqd_coverage_probe.py`：新增一组（第 11 组）：fixture transport 跑 `--full --checkpoint-every 1 --workers 1` 于一个多页区间，用 monkeypatch 让 transport 在第 k 页之后抛异常（或让 `_write_resume` 计数后 `os._exit` 替身：推荐 monkeypatch transport 第 k+1 次 call 抛 `RuntimeError("injected-kill")`，并断言 main 返回 2 且 `pending-*/resume_state.json` 存在、`slot_counts.bin.gz` 中已扫 slot 非 0）；然后 `--resume` 同参数续跑，断言：(a) 续跑 transport 调用次数 == 剩余页数（不重扫已成功页）；(b) 最终 `probe_id` 与"一次不中断跑通"的 `probe_id` **相同**（产物内容寻址，不含时间戳）——若现役 coverage_map 含 `generated_at` 之类时间字段致 probe_id 不同，改为断言 `slot_counts.bin.gz`/`blocks.bin.gz` sha256 相同与 summary 相同，并在 done 报告说明；(c) ledger 中成功页覆盖并集 == 案区间、seq 连续。默认 `--checkpoint-every 2000` 在小 fixture 下不触发也要有一条断言（不写中间检查点，`resume_state.json` 不存在于成功发布后的 gen 目录）。
3. `maintenance/repair-20260823-sqd-gap/batch2c_done.md` ＋ `batch2c_green_evidence.txt`（红→绿：先写测试证明现役无检查点＝RED，再改码转 GREEN；`test_sqd_coverage_probe.py` 全组；`run_all.py` 不新增红）。
**不动**：其他一切文件；coverage 契约草案、validator、scan-schemas 不改（检查点不是契约面）。

## 验收口径（Fable）
离线 11/11；本机用 fixture 复现"杀-续"；然后以 `--checkpoint-every 2000 --workers 16` 起 ARC 全扫并在运行中 `ls pending-*/resume_state.json` 看到检查点滚动更新。
