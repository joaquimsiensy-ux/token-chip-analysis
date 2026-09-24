# W3 盲审提示词（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于你运行的子进程（`test_sqd_gap_repair.py` 触及 `.staging_b3`，不要运行它；调度方本机已跑通并会附结果）。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放最终答复消息里**。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。
3. 首行固定 `# W3盲审：PASS` 或 `# W3盲审：FAIL`。FAIL 必须给可复现的反例（命令/输入/预期 vs 实际）；PASS 也要列出你独立验证了什么、没验证什么。
## 任务
W3 施工已 commit 到 HEAD（施工 commit 为 HEAD 或其祖先，工单 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W3.md` v3，完成报告 `W3_done.md`）。对 `git diff 60c88b88a024bf463e819d846b1ba3a9e06c7ecd HEAD -- scripts` 做独立盲审：
a) diff 范围是否只含白名单（`scripts/lib/net.py`、`scripts/tests/test_net_result.py`），生产 ≤6 行、测试 ≤25 行；
b) `--compressed` 位置紧随 `--fail-with-body`；write-out 尾巴、解析顺序、错误分类（22→http_status、其他非零→transport、0 后空/坏 JSON→decode）、重试与 no_retry_statuses 全部不变；`REGISTERED_TRANSPORT_BACKEND` 不变；四个调用方无需改动；`invariant_scan.py` 对 net.py 的登记不需改；
c) 测试：新用例是否真的约束了工单要求（可在内存中把 `--compressed` 去掉验证测试会失败）；返回码 61 用例语义；
d) 有无引入对未压缩响应的隐性依赖（Content-Length/size_download 等）或与 `sqd_coverage_probe.py:340` 的 decode/200/空正文三元匹配冲突；
e) `W3_done.md` 的陈述是否与 diff 一致（含其自述的未运行项）。
