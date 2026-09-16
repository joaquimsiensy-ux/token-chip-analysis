# T4 本机补验（Fable，2026-09-16，树=49b628e，验收 worktree /tmp/w3_acceptance HEAD 同步）

codex 沙箱 run_all 148/151 的三项失败在提交后的同一内容树本机单跑：
- test_batch3_solana_vertical_slice.py → PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release
- test_batch3_evm_vertical_slice.py → PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
- test_stage2_reseal.py → stage2_reseal: 21/21 PASS

结论：148（沙箱）＋3（本机）= 151/151；合并树（567dac9）本机全套 150/151 唯一失败同为 reseal 预建 worktree 缺失，预建后 21/21（t4_reseal_merged_fable.log）。

## 补充（盲审 t4_blind_reply.txt ④ 指出原始日志未入库）
三项在树 49b628e 单跑的原始输出已入库：`t4_post_49b628e_test_batch3_solana_vertical_slice.py.log`、`t4_post_49b628e_test_batch3_evm_vertical_slice.py.log`、`t4_post_49b628e_test_stage2_reseal.py.log`，退出码均为 0（运行命令 `python3 -B scripts/tests/<名>`，cwd＝仓库根，验收 worktree HEAD＝49b628e）。
另：`t4_accept_static_fable.txt` 末段 docs_lint 一行是验收脚本把 `docs_lint.py --all` 当文件名的引号错误（exit 2），随后单独实跑 `python3 -B scripts/tests/docs_lint.py --all` PASS 59 文档（见 t4_done.md 与盲审 ③ 复跑）。
