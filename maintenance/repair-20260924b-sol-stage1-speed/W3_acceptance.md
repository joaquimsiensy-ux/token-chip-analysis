# W3 收官验收（调度方，2026-09-24）

- 施工 commit：`6b36dcd`（生产 `scripts/lib/net.py` +2，测试 `scripts/tests/test_net_result.py` +18/−2）；工单 v3；施工报告 `W3_done.md`。
- 调度方本机定向 8 项（工单 §0.7）：全部 PASS，含施工方受禁读拦截未跑成的 `test_sqd_gap_repair.py`（rc=0）。
- `run_all.py`：**150/151 PASS**；唯一失败 `test_stage2_reseal.py` 的 `dry_run_touches_nothing`＝「验收 worktree 缺失；须调度方预建」——7.1.0 起已知环境项（硬依赖预建 worktree），与本单改动无关（日志 scratchpad `run_all_W3.log`）。
- codex 盲审 r1：**PASS**（`blind_W3_reply_r1.md`）——独立验证 diff 范围/行数、参数位置、解析顺序与错误分类不变、去掉 `--compressed` 后测试必失败、四调用方与 manifest 无需改、SQD 空尾三元匹配不受影响。
- 联网验收：`fable_probes_20260924.md` §P5（gzip 实际协商、传输 6.1×、解析摘要相等）。
- 未做：真实链路吞吐测试（非本单范围）。
