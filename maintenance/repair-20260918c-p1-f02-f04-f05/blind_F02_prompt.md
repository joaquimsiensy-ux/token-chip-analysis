# 盲审 F02（只读，常规盲审，非攻击式）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；**禁读 `F02_done.md` 与 `F02_red_evidence.txt`**（盲审不看施工方自述，独立判断）。豁免：d) 项测试自身以子进程访问历史 maintenance 目录属测试依赖，允许原样运行，审方本人不主动打开那些历史文件。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 盲审 F02：PASS` 或 `# 盲审 F02：FAIL`。FAIL 时逐条给出：编号（F02-B1-NN）、文件:行、事实、后果、建议。PASS 时列出实际核过的项与实跑的命令/结果尾行。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，以当前 HEAD 为审对象；施工 diff＝`git diff 830ce9f8323b HEAD -- scripts`。`maintenance/` 目录整体不在审查范围。

## 任务
审 F02 施工是否**真正解决**了 review 反例并符合工单 v2（`maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F02_circulating.md`）：
a) **终点判据（必做，独立复现）**：`ruling_20260918.md` 的 `flow_migration` 三分支——①`state_source.facts_inputs.circulating_supply {raw, asof, source}` 经 `facts_gate.derive_facts` 产出 `facts.token.circulating_supply_raw` 与 `circulating_supply_source`，再进 `stage2_closeout.flow_selection_errors` 按流通量分母命中"必画"（用 `test_report_facts._r07_case` 类夹具：total 1000 / e1 current 100 = 10% 不命中，声明流通量 400 → 25% 命中）；②扁平键 `facts_inputs.circulating_supply_raw` 被 derive 明确拒；③发布闸 `audit_release_gate.check_facts_vs_ledgers` 对整 token 字典比对——手改 facts 的 `circulating_supply_raw` 与 state_source 声明不一致时 BLOCK。请自行构造，不得只依赖新增测试的断言。
b) 修法与工单一致：解析块位置（`dual_basis` raise 之后）、六类非法变体（非 dict、raw 非正整数串、raw > total、asof 非严格 ISO、source 空、扁平键）各自的拒绝文案；token dict 只多两键且无声明时字典与基线逐字节相同（同版本幂等：`provenance.producer.sha256` 外不变）；closeout 有流通量时 NOTE 记口径文案；`Facts`/`override`/`build_main` 未动。
c) 白名单：**只核 `git diff --stat 830ce9f8323b HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`**，须恰为 `scripts/report/facts_gate.py`、`scripts/report/stage2_closeout.py`、`scripts/tests/test_report_facts.py`、`scripts/tests/test_stage2_closeout.py` 四文件；`SKILL.md` 8021 B、`references/**/*.md` 合计 930076 B、`commands-staging/*.md` 合计 8798 B 不变。
d) 实跑（贴尾行）。**沙箱口径**：若某测试因只读沙箱临时目录不可写而报 `No usable temporary directory found`，记为 `SANDBOX-BLOCKED`（贴该错误行）而**不计 FAIL**——由调度方本机补验；能跑的须 PASS。命令：`python3 -B scripts/tests/test_report_facts.py`、`test_stage2_closeout.py`、`test_audit_release_gate.py`、`test_state_from_facts.py`、`test_build_html.py`、`test_figures_from_facts.py`、`test_a4_gate.py`、`test_review_20260804_p105.py`、`python3 -B scripts/tests/invariant_scan.py`。**不跑 `test_stage2_reseal.py`**（调度方本机补验）。
e) 结论规则：a)/b)/c) 全过且 d) 无真实 FAIL（SANDBOX-BLOCKED 不算）即 PASS。另核新增用例（test_report_facts 22/23/24、test_stage2_closeout `circulating_supply_producer_to_consumer`）的 RED 是否真能在基线上失败（`git stash` 禁用；用 `git show 830ce9f8323b:scripts/report/facts_gate.py` 等读基线源码做内存对照）。
