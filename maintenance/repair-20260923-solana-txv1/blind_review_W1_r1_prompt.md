# 盲审任务 r1：W1 修复（分支 fix/solana-txv1 vs main）

纪律：**只读**，不改文件、不 commit；禁读 `~/.codex`（启动自动披露除外）、`~/Documents`、`~/Desktop`。报告**作为最终回复文本直接输出**，首行 `# 盲审 W1 r1: PASS / FAIL`。

你是独立审查者，不看工单、不看施工报告（`maintenance/repair-20260923-solana-txv1/` 下文件一律不读），只看**问题陈述**与**代码实况**：

问题陈述：Solana 主网出现交易版本 1。本 skill 13 个 Solana 脚本 17 处把 `maxSupportedTransactionVersion` 写死为 0，`scripts/solana/sqd_gap_repair.py` 遇含 v1 交易的区块直接报错退出。修复目标：①统一为可升级的常量且不再写死；②给 `sqd_gap_repair.py repair` 加「认领前代 pending 产物」机制——producer 改动后 plan_digest 变化，旧 pending 中已完成 slot 的证据（在版本 0 下成功读出、逻辑上不含 v1 交易）应能被新 producer 经审计后继承，只补拉剩余 slot；认领记录须可复验且不削弱既有防伪绑定；③中文文档同步；④原则「能删不加、能改不加、skill 上下文尽量不增」。

审查内容（`git diff main...HEAD` 全部改动，含测试与文档）：
1. **正确性**：常量化是否遗漏（`grep -rn maxSupportedTransactionVersion scripts`）；认领流程能否被以下情形误判/绕过：伪造 header、跨案/跨 mint 目录、重复认领、已认领过的前代、候选集外 slot、目标已有冲突证据、复制/链接中断后重跑、旧台账残尾；深验（`scripts/lib/solana_exact_validate.py`）对 `header.adopted` 的重算是否与生产者 `compute_plan_digest` 物料一致；参考源指纹等式是否完整。
2. **回归**：旧无 `adopted` 台账与版本 0 bundle 是否仍兼容（`test_batch8`、`test_batch7` 逻辑）；`load_resume_slots` 两参数调用；是否有任何既有行为被无意改变。
3. **测试真实性**：新增 E27(d) 等向量是否真的验证了声称的行为（例如版本 1 请求是否独立断言而非同源自证；负向向量失败原因是否被隔离）。自己跑 `MPLCONFIGDIR=$HOME/.matplotlib python3 -B scripts/tests/test_sqd_gap_repair.py`、`test_batch8_repair_scale.py`、`invariant_scan.py`、`test_producer_registry_current.py` 并贴尾行。
4. **最小化**：有无多余新增（可删的代码/文档/测试），有无该删未删的重复。
5. **文档**：`references/scan-schemas.md` §14.8、`references/data-pipeline-solana-capture.md`、`CHANGELOG.md` 9.1.0 与代码是否一致，中文措辞是否准确不夸大。

输出：总判定 PASS/FAIL；逐条发现按 P0（会导致错误结果/绕过）、P1（回归或误导）、P2（措辞/冗余）分级，每条附文件:行与复现方法；FAIL 的条件＝存在任一 P0 或 P1。
