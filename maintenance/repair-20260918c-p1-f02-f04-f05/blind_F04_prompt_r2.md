# 盲审 F04（只读，常规盲审，非攻击式）—— r2（r1 两条均为提示词口径/沙箱环境问题，本轮口径修正）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；**禁读 `F04_done.md` 与 `F04_red_evidence.txt`**（盲审不看施工方自述，独立判断）。 豁免：d) 项测试自身以子进程访问历史 maintenance 目录属测试依赖，允许原样运行，审方本人不主动打开那些历史文件。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 盲审 F04：PASS` 或 `# 盲审 F04：FAIL`。FAIL 时逐条给出：编号（F04-B2-NN）、文件:行、事实、后果、建议。PASS 时列出实际核过的项与实跑的命令/结果尾行。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，以当前 HEAD 为审对象；施工 diff＝`git diff 2a8ee25d3a8b HEAD -- scripts`。

## 任务
审 F04 施工是否**真正解决**了 review 反例并符合工单 v3（`maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F04_rpc_envelope.md`）：
a) **终点判据（必做，独立复现）**：`ruling_20260918.md` 的 `rpc_missing_result` 反例——单端点、握手 `0x38` 通过、业务响应为 `{"jsonrpc":"2.0","id":1}`（无 result 无 error）——在 HEAD 下经 `RpcPool` 与 `rpc_batch getcode` 是否被判失败（rc 1、该址只记 `error`、摘要"失败 1"、不含 `is_contract`）。请用内存替身自行构造，不得依赖新增测试的断言。
b) 修法与工单一致：`net.py` `_one` 返回形状仍两种、合法 `"result": null` 仍 `ok=True`；`rpc_batch.py` getcode 对 `"0x"`/偶数十六进制/奇数/非十六进制/非字符串/缺失/null 的处理与工单 §2.2 一致；`_run`/`_attest_endpoint`/`receipts`/`raw` 分支未动。
c) 白名单：**只核 `git diff --stat 2a8ee25d3a8b HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`**，须恰为 `scripts/lib/net.py`、`scripts/lib/rpc_batch.py`、`scripts/tests/test_batch1_rpc_attestation.py` 三文件；`maintenance/` 目录整体不在审查范围（调度方的提示词/报告/回复文件随时入库，不属施工白名单议题）；`SKILL.md` 8021 B、`references/**/*.md` 合计 930076 B、`commands-staging/*.md` 合计 8798 B 不变。
d) 实跑（贴尾行）。**沙箱口径**：若某测试因只读沙箱临时目录不可写而报 `No usable temporary directory found`，记为 `SANDBOX-BLOCKED`（贴该错误行）而**不计 FAIL**——这类测试由调度方在本机补验，不属本轮判定；能跑的须 PASS。可先 `python3 -c "import tempfile;print(tempfile.gettempdir())"` 自检。命令：`python3 -B scripts/tests/test_batch1_rpc_attestation.py`、`test_net_result.py`、`test_batch2_capability_matrix.py`、`test_evm_observation.py`、`test_evm_observation_nonempty_code.py`、`test_g3_alt_collectors.py`、`test_exemption_guards.py`、`python3 -B scripts/tests/invariant_scan.py`。
e) 结论规则：a)/b)/c)/e) 全过且 d) 无真实 FAIL（SANDBOX-BLOCKED 不算）即 PASS。既有消费者语义未被改动（工单 §1.4 列的 11 处仍只走各自既有 `ok=False` 分支），新增测试的 RED 是否真能在基线（`git stash` 禁用；请用 `git show 2a8ee25d3a8b:scripts/lib/net.py` 等读基线源码做内存对照）上失败。
