# 工单 F06 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`（统计大小只用 stat）。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F06复核：通过` 或 `# 工单F06复核：退回`。退回时逐条给出：编号（F06-R1-NN）、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。
3. 这是对**修复计划**的复核，不是攻击式验收：目标是拦住工单里"想得不周"的地方——锚点错、修法有副作用、既有测试会变红、同族入口漏了、迁移代价没说清。

## 任务
复核 `maintenance/repair-20260918-p0-f04-f07/workorder_F06.md`（v1）。工作目录＝本仓库根（HEAD 含本工程工单 commit；`scripts/` 与 311e6c4 逐字节相同，行号按 311e6c4 核）。逐项核：
a) §2.1/§2.2 每个锚文本 `grep -n -F` 在指定文件恰 1 处且行号一致（`entity_identity_gate.py` :88/:89/:115/:257-260/:267-270/:273/:277/:278/:327-345/:336-337；`test_entity_identity_gate.py` :23-34/:42/:65/:67）。
b) 修法正确性：插入位置在 `:277` 之后是否在 `for row in rows` 循环体内且此时 `flag`、`label`、`address`、`expected_entities` 均已定义；`label` 非法（非 dict 或缺 tier）时是否会重复报错或抛异常；非实体大户（`(non-entity big holder)`）带 tier=exclude 标签是否被误拦（应不拦，与 producer :336 对称）。
c) 回归面：`grep -rn "exclude" scripts/tests/*.py` 列出所有夹具里 tier=exclude 的行，逐条判断是否为实体成员且 flag 非 INFRA_IN_ENTITY（会变红）；`identity_gate_fixture.py`、`test_audit_release_gate.py`、`test_a4_gate.py`、`test_stage2_closeout.py`、`test_batch17_identity_chain_alias.py`、`test_round4_identity_emitter.py`、`test_v2_identity_history.py` 有无受影响。
d) §2.2 三个用例的 RED/GREEN 断言在基线与改后是否成立（沙箱允许则实跑 `python3 -B scripts/tests/test_entity_identity_gate.py` 并在临时目录复现用例 1，否则静态推演并注明"未实跑"）。
e) §0.4 不改清单、§0.8 定向测试清单、§1 硬约束、§4 登记项是否自洽；`invariant_scan.py` 是否会因 consumer 新增错误文案要求登记（若会，工单需把 `invariant_manifest.json` 加进白名单）。
f) 有无任何一处会让 `scripts/tests/run_all.py` 现有用例变红。
