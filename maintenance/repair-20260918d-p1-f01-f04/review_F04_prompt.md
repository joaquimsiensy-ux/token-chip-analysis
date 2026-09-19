# 工单 F04 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918d-p1-f01-f04/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F04复核：通过` 或 `# 工单F04复核：退回`。退回时逐条给出：编号（F04-R1-NN）、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。
3. 这是对**修复计划**的复核，不是攻击式验收：目标是拦住工单里"想得不周"的地方——锚点错、修法有副作用、既有测试会变红、同族入口漏了、迁移代价没说清、**工单前提与代码事实不符**（专门核"来源/事实"断言：`validate_camp_spec` 是否真是四入口唯一共享校验、`replay_pass2.py:96/:106` 与 `replay_duck.py:548/:560` 是否真会对显式「散户」重复 append、`build_evolution.py:173/:181` 是否真是标量相加无重复）。

## 任务
复核 `maintenance/repair-20260918d-p1-f01-f04/workorder_F04_retail_bucket.md`（v1）与同目录 `ruling_20260918.md`、`code_change_pending.md`。工作目录＝本仓库根（HEAD 含本工程工单 commit；`scripts/`、`references/` 与 868d3f61 逐字节相同，行号按 868d3f61 核；F01 尚未施工）。逐项核：
a) §2 每个锚文本 `grep -n -F` 的命中数与行号是否与工单一致。
b) 修法正确性与副作用：读 `camp_spec.py` 全文，判断在 `:61` 之后按 `chain_family == "evm" and camp == "散户"` 硬拒是否会误伤——①`load_addr_camp_json`（`:83-115`，默认 `chain_family="solana"`）反转后调用 `validate_camp_spec` 的路径；②`camp_series_provenance._load_camps_spec:780-789`（consumer 侧末点对账重读 spec，`chain_family` 由调用者传）对存量 EVM 正式案 spec 的影响——全 `scripts/`、`scripts/tests/` 检索是否存在任何 EVM camps spec 显式含「散户」键（`grep -rn '"散户"\s*:' scripts` 并区分"配置键"与"序列值"）；③`_normalize` 对 `chain_family` 的校验只在有地址时触发，新判断放在其前是否改变非法 chain_family 的报错顺序（可接受但须指出）。
c) 回归面：列出所有会因本段变红的既有测试（含 run_all.py 登记的全部 test_*.py 里工单 §0.8 未列的）——重点 `test_engine_equivalence.py`、`test_fault_injection.py`、`test_repair_batch1.py`、`test_repair_batch_d.py`、`test_a4_gate.py`、`test_lit_regression_f007.py` 构造的 camps spec；`test_repair_batch_c.py` 的 `t_f05_evm_engines` 在插入两条用例后，后续 `:270-275` 合法绿例与 sidecar 断言是否仍成立（`data/` 目录状态）。
d) 新用例 RED/GREEN 在基线与改后是否成立（沙箱允许则实跑 `python3 -B scripts/tests/test_repair_batch_c.py`，否则静态推演注明）；`check()`（`:54-57`）是 raise 型——工单 §0.7 要求施工方逐表达式独立取 RED 而不是跑整测试，表述是否可执行；引擎级用例 `build_evm_case(..., expect_rc=2)` 在 duck 拒收时 `data/camp_series.json` 是否确实不会落盘（核 `replay_duck.py:467` 相对于任何写盘点的顺序）。
e) §0.3 白名单是否足够、§0.4 不改项是否自洽；`invariant_scan.py`/`test_batch4_invariant_guards.py`/`test_exemption_guards.py` 是否会因 `camp_spec.py` 改动要求登记或报错。
f) 终点判据：`ruling_20260918.md` 的 `retail` 反例（mint 100→A、A→B 40、`camps={大庄:[A],散户:[B]}`）按工单改后是否**必然**使 pass1→pass2 与 replay_duck 都 exit 2 且不产 `camp_series.json`——给出拒在哪一行、哪句文案；Solana `validate_camp_spec({"散户":[SA]}, chain_family="solana")` 是否仍接受。
g) 台账 Q5/Q6/Q7 表述是否准确：Solana 两入口（`replay_edges.py:612` / `build_evolution.py:82`）显式「散户」的实际行为；references 是否真无"散户可配置"示例（`grep -rn '"散户"' references SKILL.md commands-staging`）。
