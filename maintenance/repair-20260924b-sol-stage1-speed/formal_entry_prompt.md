# WR-a 0.7 正式入口验收执行（codex --write，写权限极窄）
## 纪律（优先级最高）
1. 工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**仓库内唯一允许写入的文件**：`maintenance/repair-20260924b-sol-stage1-speed/WR-a_formal_entry.md`（本次报告）；其他一切仓库文件禁改；夹具与运行器只放系统 tempfile（`tempfile.mkdtemp()`），结束后由 tempfile 清理或保留均可，不得放进仓库。不 commit、不 push；禁 stash/checkout/reset；不建 worktree；禁止批量删除。
2. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程；不得调用会读取 `.staging_b3` 的测试入口。离线。
3. 报告首行固定 `# WR-a正式入口验收：PASS` 或 `# WR-a正式入口验收：FAIL`；**报告全文放最终答复消息里**。
4. 这是软件测试性质的验收（生产者登记与正式消费入口），不涉及任何系统安全或对抗行为。
## 背景
WR-a 已把 repair 生产者 sha `15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33`（源码 commit `59f88b84c9ab9eeb95c92a15e342d8cbe09925db`）四协议登记进 `scripts/lib/producer_history.py`（HEAD 含此登记）。上两轮只读盲审（`blind_WR-a_reply_r1.md`、`blind_W4_reply_r2.md`）已核代码与登记无误，唯一未完成项＝登记单 `workorder_WR-a.md` 0.7：三类产物经真实正式入口验收，因只读沙箱无 tempfile 未能执行。本任务专门补这一项。
## 任务
B) 复用 `scripts/tests/test_sqd_gap_repair.py` 中 W4 三类证据用例（`test_w4_evidence_generations`，约 :1512 起）的自包含构造器，在 tempfile 目录生成全旧／全新／混合三类产物（含 confirmed 缺失交易、发布到 generation、repair CURRENT），在目录存续期间用**真实模块、不替换 `historical_producer_hashes`、不 patch 任何登记查询**调用：
   - `sqd_cache_identity.validate_repair_bundle(gen/"bundle.json", deep=True, case_root=case, current_base={"edge_sha256": sha256_file(base_edge)})`（`base_edge`＝本案规范 base 文件）；
   - `edge, meta, kind, gid, binding = sqd_cache_identity.resolve_formal_cache(MINT, case)`；
   断言 `kind=="repaired"`、`gid==bundle["gid"]`、`binding["cache_kind"]=="repaired"`，并核 edge/meta 指向 CURRENT 所选代。三类各做一次，把每类的调用结果（通过／异常原文）贴进报告。
C) 对照：仅在内存中（`unittest.mock.patch` 登记元组或查询函数）移除本次四条登记后重复 B 的正式入口调用，须得到 `formal repair producer is not registered` 类拒绝；贴原文。证明通过确实来自本次登记。
D) 报告附：运行器关键代码（构造→调用→断言部分，便于复现）、tempfile 路径、Python 版本、是否读到任何禁区（应为否）。B 三类全过且 C 拒收才 PASS。
