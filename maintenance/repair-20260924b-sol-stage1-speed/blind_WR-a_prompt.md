# WR-a 盲审 兼 0.7 正式入口验收提示词（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程。
2. 只读仓库、离线、不 commit、不新建/修改仓库文件；夹具只能建在系统 tempfile 目录。**报告全文放最终答复消息里**。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。
3. 首行固定 `# WR-a盲审：PASS` 或 `# WR-a盲审：FAIL`。FAIL 必须给可复现反例；PASS 也要列独立验证了什么、没验证什么。
4. 这是软件测试性质的正确性审查（生产者哈希登记与正式消费入口），不涉及任何系统安全或对抗行为。
## 任务
WR-a 登记已 commit 到 HEAD（登记单 `workorder_WR-a.md` v2、完成报告 `WR-a_done.md`、调度方验收 `WR-a_acceptance.md`）。
A) 盲审 `git diff c3660b1f05398bd9a0015c353db399f6361c65ce HEAD -- scripts`：仅 `producer_history.py` 追加四条；sha/commit 由 `git show "<commit>:scripts/solana/sqd_gap_repair.py" | shasum -a 256` 独立复算相等；既有条目逐条未变；`test_producer_registry_current.py` 你亲跑并逐项判读（预期仅 probe 两协议 FAIL）。
B) **执行登记单 0.7 正式入口验收**：复用 `scripts/tests/test_sqd_gap_repair.py` 中 W4 三类证据用例（全旧/全新/混合，约 :1512 起）的自包含构造器，在系统 tempfile 目录内生成夹具并保持存续，用**真实模块、不替换 `historical_producer_hashes`** 调用 `sqd_cache_identity.validate_repair_bundle(gen/"bundle.json", deep=True, case_root=case, current_base={"edge_sha256": sha256_file(base_edge)})` 与 `edge, meta, kind, gid, binding = sqd_cache_identity.resolve_formal_cache(MINT, case)`，断言 `kind=="repaired"`、`gid==bundle["gid"]`、`binding["cache_kind"]=="repaired"`，并核 edge/meta 指向 CURRENT 所选代；三类各做一次。把每类的调用结果（通过/异常原文）贴进报告。任一类未通过即 FAIL。
C) 对照检查：把登记条目临时（仅内存）移除后重复 B 的正式入口调用，应得到 `formal repair producer is not registered` 类拒绝——证明通过确实来自本次登记而非其他豁免。
