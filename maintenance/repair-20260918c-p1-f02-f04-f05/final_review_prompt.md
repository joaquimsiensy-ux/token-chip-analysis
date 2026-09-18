# 收官 review（只读，repair-20260918c 三段整体：F04/F05/F02 是否真正解决）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；禁读本工程目录内的 `F0*_done.md`、`F0*_red_evidence.txt`、`blind_*`、`review_*`（不看施工/复核/盲审自述，独立判断）。豁免：测试自身以子进程访问历史 maintenance 目录属测试依赖，允许原样运行。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 收官review：通过` 或 `# 收官review：退回`。退回时逐条给出：编号（FR-NN）、文件:行、事实、后果、建议。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`；审对象＝`git diff 8b041842 HEAD -- scripts`（8.0.0 基线到当前 HEAD 的全部改动）。`maintenance/` 目录整体不在白名单议题内。

## 任务
以 `maintenance/repair-20260918c-p1-f02-f04-f05/ruling_20260918.md` 的三条终点判据为准，独立复现（自行构造夹具/内存替身，不得只依赖新增测试断言），逐条给出"基线 8b041842 下的行为 vs HEAD 下的行为"：
a) `rpc_missing_result`：单端点、握手 `0x38` 通过、业务响应 `{"jsonrpc":"2.0","id":1}` → HEAD 下 `RpcPool` 判失败、`rpc_batch getcode` rc 1、该址只记 error、摘要"失败 1"；合法 `"result": null` 仍 ok。
b) `price_gate_content`：真实 `price_check.py` 主 50/副 100 三点 FAIL 收据（退出 2）绑进其余合法的 −2 工单 → HEAD 下 `stage2_closeout check` BLOCK（拒在哪行哪句）；同时核 verdict 手改/哈希错绑/旧收据/ALL_SKIP/内联纯申报各拒，WARN 放行记 NOTE。
c) `flow_migration` 三分支：①`facts_inputs.circulating_supply {raw,asof,source}` → `facts.token.circulating_supply_raw` → `flow_selection_errors` 按流通量分母命中必画（用 total 1000/current 100/声明 400 的夹具）；②扁平键 `circulating_supply_raw` 被 derive 拒；③发布闸整 token 字典比对——手改 facts 流通量与声明不一致 BLOCK。
d) 整体白名单：`git diff --stat 8b041842 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 须恰为 8 个 scripts 文件（net.py、rpc_batch.py、test_batch1_rpc_attestation.py、price_check.py、stage2_closeout.py、test_stage2_closeout.py、facts_gate.py、test_report_facts.py）；`SKILL.md` 8021 B、`references/**/*.md` 合计 930076 B、`commands-staging/*.md` 合计 8798 B 不变（本轮文档零改动、版本登记另段）。
e) 回归面：三段改动之间无相互破坏（F05 与 F02 共改 `stage2_closeout.py`/`test_stage2_closeout.py`，核两段插入互不覆盖）；`python3 -B scripts/tests/invariant_scan.py` PASS。实跑（贴尾行；沙箱临时目录不可写报 `No usable temporary directory found` 的记 `SANDBOX-BLOCKED` 不计 FAIL，由调度方本机 run_all 补验）：`test_batch1_rpc_attestation.py`、`test_stage2_closeout.py`、`test_report_facts.py`、`test_audit_release_gate.py`、`test_net_result.py`、`test_state_from_facts.py`。
f) 结论规则：a)/b)/c) 三反例在 HEAD 下全部变拒且基线下可复现原缺陷、d)/e) 通过、无真实 FAIL → 通过；否则退回并指出哪条反例未闭合。
