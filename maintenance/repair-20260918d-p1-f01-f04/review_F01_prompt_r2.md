# 工单 F01 复核提示词（只读，r2）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918d-p1-f01-f04/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F01复核：通过` 或 `# 工单F01复核：退回`。退回时逐条给出：编号（F01-R2-NN）、工单位置、事实、修订建议。通过时列出实际核过的项。
3. 这是修复计划复核（非攻击式验收）。

## 任务
复核 `maintenance/repair-20260918d-p1-f01-f04/workorder_F01_price_nonfinite.md`（**v2**）与 `code_change_pending.md` Q1/Q2/Q4 是否正确消化了 `review_F01_reply_r1.md` 的五条意见，且没有引入新问题。工作目录＝本仓库根（`scripts/` 与 868d3f61 逐字节相同；F04 尚未施工）。只核：
a) R1-01：§2.1 是否改为在 `:175` **之前**插入 `p2 = p2 if p2 is None or math.isfinite(p2) else None`、`:175` 原行不改；按 v2 在内存执行生产者：第二源 `nan`/`inf`/`-inf` 带 `--out` 时是否得到完整收据（`second_price=null`、SKIP、ALL_SKIP 退出 3）、不再抛 ValueError；`:185` 打印行对 `p2=None` 是否无异常；新用例 6c 在基线（NaN 判 PASS 返回 0）与改后（返回 3）是否成立。
b) R1-02：§2.1 `_load_series` 检查是否改为 `not (math.isfinite(p) and p > 0)`（非有限或非正 fatal），与消费者 `ok1` 是否同口径；§1.7 兼容范围与 Q4 存量结论表述是否自洽（复核方不读案卷，只核逻辑与表述是否与代码事实一致）；6b 第二个文件（首价 0.0）与 6e（收据主价改 0.0）在基线/改后是否成立（基线生产者对 0 价：`:175` `p1 <= 0` → SKIP，三日中一日 SKIP 两日 PASS → 汇总 PASS 返回 0 → 6b 基线 RED）。
c) R1-03：6g 阈值相等断言 `(closeout.PRICE_WARN_PCT, closeout.PRICE_FAIL_PCT) == (price_check.WARN_PCT, price_check.FAIL_PCT) == (5.0, 15.0)` 的 `price_check` import 在该测试上下文是否可解析（`:15` sys.path）；WARN 边界 1.0/1.052 → `round(0.052/1.026*100,2)` 是否恰为 5.07 WARN；手改全部点 status＋verdict 为 PASS 后是否精确只命中逐点重算块（错误字段 `points[0].status`、文案含 WARN）；把消费者常量单独改为 6/16 时 6g 是否会红。
d) R1-04/R1-05：§2.2 说明③"0～2 条"与 Q4 表述是否准确；§0.4 CSV 截断口径位置是否订正为 `_load_series:70-72`。
e) 新增段 6c 覆盖主收据为 ALL_SKIP、6d/6f/6g 各自重写收据、6e 复用 6d 收据——段间状态与段 7 前置状态（顶层 `price_source_checks` 在场）是否无影响；`update()` 的 lambda 写法（6g 用元组表达式）是否合法。
f) r1 已通过的项（锚表 11 处、回归面 19 条 mutation、终点判据、白名单、invariant 登记）本轮无需重演，仅确认 v2 未改动这些段落的实质内容；若 v2 新增的 `:175` 前插入行影响锚表（后续锚 `:175`/`:199` 的施工前行号仍按基线 868d3f61），请确认工单口径一致。
