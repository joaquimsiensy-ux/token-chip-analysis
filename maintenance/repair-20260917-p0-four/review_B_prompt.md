# 工单 B 复核提示词（只读，r2：对 v2 复核；r1 六条见 `review_B_reply_r1.md`，逐条核 v2 处置是否闭合——尤其 B-R1-02 改为直调 `check_three_ledgers(chain=None)` 是否成立、B-R1-05 改为上限只验下界是否与文档一致且 fail-closed 于原缺陷）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容（统计大小只用 stat）。禁读 `/Users/uravvv/Desktop` 下任何文件。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单B复核：通过` 或 `# 工单B复核：退回`。退回时逐条给出：编号、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。

## 任务
复核 `maintenance/repair-20260917-p0-four/workorder_B.md`（v2）。工作目录＝本仓库根。逐项核：
a) §2 每个锚文本 `grep -n -F` 在 `scripts/report/audit_release_gate.py` 恰 1 处且行号一致（:782/:870/:877/:895/:906/:907-908/:914-916/:918-924/:938-940/:959-962/:964-967；`check_ledger` :584）；`scripts/tests/test_audit_release_gate.py` :151/:246/:352-366/:517-548/:550。
b) B1 分流逻辑：`member_map.get(addr_key, ...)[1]` 在 position 循环里取到的状态是否可靠（`:907-908` 已拒 excluded/未映射，故只剩 strict/expanded）；`wallet_by_entity.setdefault` 是否保住 `:966` 的实体集合语义；`position_by_address` 不变是否使逐地址闭合对 expanded 仍生效。
c) B2 区间校验：`want_lo = wallet + facility_sum` 用的是自报 `wallet` 还是重算值——注意 `:938` 已断言 `wallet == wallet_by_entity[entity]`，若不等已报错；请判断用自报 `wallet` 是否会让"自报 300 且 range [300,300]"的反例漏网（用例 2 期望的错误是 `:939` 的"钱包自持与位置账不闭合"，是否足够 fail-closed）；`has_expanded` 的计算、字段缺失/形状/数值三类错误信息是否互斥且可被用例断言。
d) 文档一致性：`references/economic-control-accounting.md:40-44、:80、:93`、`references/playbook-entity-cluster-tiering.md:145、:150` 的口径与 B1/B2 语义是否一致（本段文档零改动，只需确认代码改后与文档不再矛盾）。
e) B3 八个用例：夹具手法是否可行——尤其绿例要让 B-7 四查 owner 快照包含 `0xdef`（`:849-869` 的时点/数值绑定，`_recon_owner_snapshot` `:663-781`），`align_ledgers_to_owner_snapshot` `:151` 是否适用；每例的 RED/GREEN 断言在基线与改后是否成立（沙箱允许则实跑，否则静态推演注明未实跑）；现有 `:516-548` 用例在新逻辑下是否仍绿。
f) 回归：`scripts/tests/test_batch15_three_ledgers_frozen.py`（`write_ledgers` :57-83 无 range 字段、无 expanded）与 `scripts/tests/test_repair_batch_d.py`（`build_solana_case` 三账）在新逻辑下是否仍绿；其他调用 `check_three_ledgers` 的测试有无 expanded 成员。
g) §0.4 不改清单、§1.1 字节约束、§4 调度方验收项是否自洽；有无遗漏同族点（如 `expanded_economic_control_range_raw` 在 `check_ledger` 或其他消费者里是否也该验）。
h) 有无任何一处会让 `scripts/tests/run_all.py` 现有用例变红。
i) v2 对 r1 六条的处置是否各自闭合（B-R1-01 `in row`；B-R1-02 直调封装与夹具；B-R1-03 `:554`/`:556` 锚；B-R1-04 逐例函数；B-R1-05 `lo == want_lo and hi >= min_hi` 及用例 3/4/5/9；B-R1-06 白名单）。
