# 收官 review（只读，repair-20260918d 两段整体：F04/F01 是否真正解决）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918d-p1-f01-f04/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；禁读本工程目录内的 `F0*_done.md`、`F0*_red_evidence.txt`、`blind_*`、`review_*`（不看施工/复核/盲审自述，独立判断）。豁免：测试自身以子进程访问历史 maintenance 目录属测试依赖，允许原样运行。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 收官review：通过` 或 `# 收官review：退回`。退回时逐条给出：编号（FR-NN）、文件:行、事实、后果、建议。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`；审对象＝`git diff 868d3f61 HEAD -- scripts`（9.0.0 基线到当前 HEAD 的全部改动）。`maintenance/` 目录整体不在白名单议题内。

## 任务
以 `maintenance/repair-20260918d-p1-f01-f04/ruling_20260918.md` 的两条终点判据为准，独立复现（自行构造夹具/内存替身，不得只依赖新增测试断言），逐条给出"基线 868d3f61 下的行为 vs HEAD 下的行为"：
a) `price_nan`：三天 `close=NaN` CSV、第二源内存替身固定合法响应 → 基线 `price_check.py` rc=0/PASS/收据含 NaN；HEAD 下 `[fatal]` 退出 1、不写收据（拒在哪行哪句）。另各试首日 `inf`/`0`/`-1` → HEAD 均退出 1。第二源替身返回 `nan` 带 `--out` → HEAD 完整收据、`second_price=null`、ALL_SKIP 退出 3、不抛异常。消费者：其余合法的 −2 工单（可复用 `test_stage2_closeout.build_closeout_case`），points 手改 `main_price=NaN`/`0.0`（status 仍 PASS）→ HEAD `price_receipt_errors` 拒（字段含 `points[i].main_price`）、基线放行；`second_price` 改 2.0 但 status PASS → HEAD 拒（`points[i].status`、含 FAIL）、基线放行；WARN 边界 1.0/1.052 真实收据放行，手改全部 status＋verdict 为 PASS → HEAD 拒。
b) `retail`：mint 100→A、A→B 40，`camps={大庄:[A],散户:[B]}` → 基线 pass1→pass2 与 duck 均 rc=0、「散户」长度 = 2×dates；HEAD 均 exit 2、stderr 含 `[camp-spec]`、全新输出目录不生成 `camp_series.json`。Solana `validate_camp_spec({"散户":[SA]}, chain_family="solana")` 与 `load_addr_camp_json`（默认 solana）对值为「散户」的地址在 HEAD 仍接受；既有合法 EVM spec 行为逐字节不变。
c) 整体白名单：`git diff --stat 868d3f61 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 须恰为 5 个 scripts 文件（`lib/camp_spec.py`、`tests/test_repair_batch_c.py`、`prices/price_check.py`、`report/stage2_closeout.py`、`tests/test_stage2_closeout.py`）；`SKILL.md` 8021 B、`references/**/*.md` 合计 930076 B、`commands-staging/*.md` 合计 8798 B 不变（本轮文档零改动、版本登记另段）。
d) 回归面：两段改动互不触碰（F04 两文件与 F01 三文件无交集）；`python3 -B scripts/tests/invariant_scan.py` PASS。实跑（贴尾行；沙箱临时目录不可写报 `No usable temporary directory found` 的记 `SANDBOX-BLOCKED` 不计 FAIL，由调度方本机 run_all 补验）：`test_repair_batch_c.py`、`test_engine_equivalence.py`、`test_stage2_closeout.py`、`test_a4_gate.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`。
e) 结论规则：a)/b) 两反例在 HEAD 下全部变拒且基线下可复现原缺陷、c)/d) 通过、无真实 FAIL → 通过；否则退回并指出哪条反例未闭合。
