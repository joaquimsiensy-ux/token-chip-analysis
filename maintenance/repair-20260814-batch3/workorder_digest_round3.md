# 【消化轮 3 工单】盲审 Round 3 BR3-01 修复（1 项 P2，单点）

> 施工方：codex。**禁一切 git 写命令**；只改文件。完成后写 `maintenance/repair-20260814-batch3/workorder_digest_round3_done.md`，末行 WORKORDER_DIGEST_ROUND3_COMPLETE。
> 禁触：同 workorder_digest_round1.md 头部清单。版本件本单不动。
> 裁判已独立复验三反例全部漏过（U+200B 插词 / CLOSED_PENDING 未知关键字 / HTML 实体，均返回 []）。

## BR3-01（P2）：R10 守卫未知/隐形状态载体静默归 OPEN

**根因**：`r10_ledger_failures` 的状态识别是"严格/宽松正则都没命中 → OPEN"，把"没有状态标记的合法 OPEN"与"存在但无法识别的非法状态载体"混为一态，违反 F-07 工单"格式认不出 → FAIL"根不变量。

**修法（统一载体规则，裁判定案）**：改 `scripts/tests/test_repair_batch3_gates.py`：

1. 每个 R10 条目行**全行提取所有 `【...】` 载体**（全角括号对，非贪婪逐个）。
2. 每个载体必须同时满足：(a) 位于该节合法状态列（既有 section 表：第五节 cell 3、其余 cell 2）；(b) **fullmatch 严格状态枚举**（`CLOSED x.y.z` / `FIXED_PENDING_REVIEW x.y.z 批N`，ASCII 空格）。任一不满足 → FAIL。
   - 违反 (a)（合法枚举出现在正文列）→ 保持既有错误文本"正文列出现状态样式标记"（既有回归断言依赖）；
   - 违反 (b)（载体存在但非枚举：零宽/不可见字符插词、未知关键字、HTML 实体、全角空格等一切变体）→ 新错误文本"状态载体无法识别为枚举"，消息附载体原文（repr 形式，便于看见不可见字符）。
3. 合法状态列**无任何载体**才判 OPEN。
4. 既有 statusish/裸词扫描保留（继续抓无括号变体与裸词）；本条载体规则在其之上，两者命中其一即 FAIL。
5. 载体提取正则注意：`【[^】]*】` 逐个；嵌套/未闭合括号（有【无】）出现在条目行 → FAIL"状态载体括号不配对"。

## 测试（先红后绿，进 gates F07 小节追加）

- **三反例正式回归**（先红：HEAD 均返回 []，与裁判复验一致）：
  1. `【CLO<U+200B>SED 6.41.0】` + 现役 19→20 → FAIL；
  2. `【CLOSED_PENDING 6.41.0】` + 同步现役 → FAIL；
  3. `【CLO&#83;ED 6.41.0】` + 同步现役 → FAIL。
- 未闭合括号反例：`【CLOSED 6.41.0`（缺右括号）→ FAIL。
- 绿例不回退：真台账 27 条全绿；Round 1 三反例、Round 2 组合/竖线/全角结构反例语义与错误文本不变（若统一规则改变了某反例的命中闸序，允许错误文本为新旧任一，但必须仍 FAIL——正式回归断言按实际收敛后文本更新并在 done 说明）。

## 验收标准（裁判执行）

- 裁判三反例复现脚本复跑 → 全拒。
- `test_repair_batch3_gates.py`、`invariant_scan.py`、`run_all.py` 全量 rc=0。
- done 文件含先红清单、映射、自审、未修事项。
