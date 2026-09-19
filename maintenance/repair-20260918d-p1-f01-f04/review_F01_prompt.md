# 工单 F01 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918d-p1-f01-f04/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F01复核：通过` 或 `# 工单F01复核：退回`。退回时逐条给出：编号（F01-R1-NN）、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。
3. 这是对**修复计划**的复核，不是攻击式验收：目标是拦住工单里"想得不周"的地方——锚点错、修法有副作用、既有测试会变红、同族入口漏了、迁移代价没说清、**工单前提与代码事实不符**（专门核"来源/事实"断言：`_load_series:56-85` 是否是主价格文件唯一解析点、`:175-180` 是否是唯一判点处、`:197-199` 是否是唯一落盘点、closeout `load():62-63` 用 `json.loads` 默认是否真会把 `NaN` 字面量解析成 float nan、`price_receipt_errors` 是否是收据唯一消费点）。

## 任务
复核 `maintenance/repair-20260918d-p1-f01-f04/workorder_F01_price_nonfinite.md`（v1）与同目录 `ruling_20260918.md`、`code_change_pending.md`。工作目录＝本仓库根（HEAD 含本工程工单 commit；`scripts/`、`references/` 与 868d3f61 逐字节相同，行号按 868d3f61 核；F04 段将先施工但不触碰本段任何文件）。逐项核：
a) §2 每个锚文本 `grep -n -F` 的命中数与行号是否与工单一致。
b) 修法正确性与副作用：①`_load_series` 在 `:84` 之后拒非有限——CSV 路径 `float("NaN")`/`float("inf")`/`float("-inf")` 与 JSON 路径 `NaN`/`Infinity` 字面量是否都落到该检查；`[fatal]` 走 `sys.exit(str)` 退出码 1 与既有 `:61/:66/:83` 一致；②`:175` 加 `not math.isfinite(p2)` 后 SKIP 语义与台账 Q1 是否自洽；③`:199` `allow_nan=False` 在何种残余路径会抛 `ValueError`（是否只剩"不可能"路径，抛出时退出码/文案是否可接受）；④closeout `:268` 之后逐点重算块——`round(…, 2)` 与 `price_check.py:179` 是否逐字同规则（边界 5.00/15.00 两侧各取一值静态推演）、bool 排除、`p2 is None` 落 SKIP、主价非有限时 `continue` 后 `statuses` 仍参与汇总是否会产生重复/矛盾诊断（可接受但须指出条数）；⑤`PRICE_WARN_PCT/PRICE_FAIL_PCT` 常量与 Q2"不 import price_check"的理由是否成立（核 `invariant_manifest.json:779` 与 `invariant_scan.py` 对 report 层 import 网络模块的守卫是否真会拦）。
c) 回归面：列出所有会因本段变红的既有测试——重点：`test_stage2_closeout.py` 现有 `price_receipt_content_enforced` 段 1-7 与 `workorder_reference_contracts:514-561` 的 19 条 mutation 在逐点重算下是否仍 BLOCK 且文案含 field 名；`test_stage2_reseal.py`（复用 `build_closeout_case`）、`test_a4_gate.py`、`test_audit_release_gate.py` 是否构造过含非有限价格的夹具；全 tests 检索 `price_series.json`/`price_checks.json`/`main_price`/`second_price` 的构造点。
d) 新用例 6b/6c/6d 在基线与改后是否成立（沙箱允许则实跑 `python3 -B scripts/tests/test_stage2_closeout.py`，否则静态推演注明）：6b 的 `write_price_receipt(..., prices="price_nan.json", out="price_nan_checks.json")` 是否真返回 1 且不落盘（`_load_series` 在 `:157` 早于任何写盘）；6c `write()` 用 `json.dumps` 默认 `allow_nan=True` 是否真写出 `NaN` 字面量、closeout 读回是否为 nan；6d 手改 `points[1].second_price=2.0` 后重算 66.67% FAIL 与声明 PASS 不一致的错误字段名是否恰为 `points[1].status`；插入位置（段 6 之后、段 7 之前）对段 7 的前置状态（顶层 `price_source_checks` 仍在场）是否无影响。
e) §0.3 白名单是否足够、§0.4 不改项是否自洽；`invariant_scan.py`/`test_batch4_invariant_guards.py`/`test_exemption_guards.py` 是否会因新增 `import math` 或常量要求登记。
f) 终点判据：`ruling_20260918.md` 的 `price_nan` 反例（三天 `close=NaN` CSV、第二源固定合法响应）按工单改后是否**必然**使 `price_check.py` 退出 1 且不写收据——给出拒在哪一行、哪句文案；人为构造 `main_price=NaN` 收据 → `price_receipt_errors` 拒在哪一行；手改 `second_price` 偏差 >15% 但 status PASS → 拒在哪一行。
g) 台账 Q1/Q2/Q4 表述是否准确；文档 `report-template.md:278`（零改动）与新行为是否冲突。
