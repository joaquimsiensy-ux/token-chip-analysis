# WR-b 0.7 验收执行（codex --write，写权限极窄）
## 纪律（优先级最高）
1. 工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**仓库内唯一允许写入的文件**：`maintenance/repair-20260924b-sol-stage1-speed/WR-b_formal_entry.md`（本次报告）；其他一切仓库文件禁改；夹具与运行器只放系统 tempfile（`tempfile.mkdtemp()`）。不 commit、不 push；禁 stash/checkout/reset；不建 worktree；禁止批量删除。
2. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程。离线。
3. 报告首行固定 `# WR-b验收：PASS` 或 `# WR-b验收：FAIL`；**报告全文放最终答复消息里**。
4. 这是软件测试性质的验收（生产者哈希登记与 coverage 校验器），不涉及任何系统安全或对抗行为。
## 背景
WR-b 已把探针 sha `d4adc0c88f87bc03b3d847db7df9c9f7e588cb503734dfd977b818b581d998d8`（源码 commit `f78b5c4575ebe1db36f2cf3a96e75b79731f3fc6`）登记进 `scripts/lib/producer_history.py`（coverage/v1、coverage-pointer/v1 各一条，HEAD 含此登记；登记单 `workorder_WR-b.md` v2 0.7）。
## 任务
① 用真实 `historical_producer_hashes`（不替换、不 patch）分别查询 `sqd-solana-coverage/v1` 与 `sqd-solana-coverage-pointer/v1`（script 为探针路径），断言上述 sha 同时在两个结果中；贴结果。
② 盲审 `git diff fcf81f062daa004a37862a92cfe1c488a98da2b0 HEAD -- scripts`：仅 producer_history.py 追加两条；既有 38 条逐字不变（AST 或字节比较）；独立复算 `git show "<commit>:scripts/solana/sqd_coverage_probe.py" | shasum -a 256` 相等；亲跑 `test_producer_registry_current.py` 须 0 FAIL。
③ 复用 `scripts/tests/test_sqd_coverage_probe.py` 自包含发布用例（`:205` 附近，或 `_w1_run`/`_w1_check` 动态夹具）在 tempfile 存续期间生成 coverage 产物，跑一次真实 `solana_exact_validate.validate_coverage(case, generation/"coverage_map.json", case/"data/sqd_coverage/CURRENT.json", <from>, <to>)`，断言 ok=True 并贴 reasons；说明该校验器 `:712-722` 允许当前源码 sha 直接通过，故本步只证兼容。
④ 对照：仅内存（`unittest.mock.patch.object(producer_history, "PRODUCER_HISTORY", filtered)`）移除本次两条登记后重复 ①，须查不到该 sha；贴结果。
⑤ 报告附运行器关键代码、tempfile 路径、Python 版本、禁区读取情况（应为否）。①②③④ 全过才 PASS。
