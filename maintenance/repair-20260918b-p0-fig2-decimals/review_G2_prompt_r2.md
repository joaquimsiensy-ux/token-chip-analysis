# 工单 G2 复核提示词（只读，r2：核 v2 对 r1 七条的修订）

## 纪律
同 `review_G2_prompt.md` 第 1–3 条（禁读 `~/.codex/`、archive/blind-reviews/.staging_*/attic、本工程与 repair-20260918-p0-f04-f07 以外的历史 maintenance、Desktop/Documents；只读离线不改文件；报告全文打印到 stdout，首行 `# 工单G2复核r2：通过` 或 `# 工单G2复核r2：退回`，退回逐条编号 G2-R2-NN）。

## 任务
复核 `maintenance/repair-20260918b-p0-fig2-decimals/workorder_G2_decimals.md`（v2）对 `review_G2_reply_r1.md` 七条的消化，只核 v2 变更面：
a) R1-01 两处 schema 锚按缩进（12/8 空格）是否各恰 1 命中；§2.6 起止锚 :1586/:1610 是否准确。
b) R1-02 `nonempty_code.py:129-134` 断言修订是否足以让该文件全绿。
c) R1-03 §2.9 c 例：按工单步骤（`add_new_analysis_distribution(decimals=2)` → config 改 decimals=2/human=N/100 → 重绑两收据 inputs.config 与 wrapper sha → create_bundle）**基线是否真放行 `[]`**（内存执行或静态推演；注意 `_recon_bound_reality` nominal 闭合、supply_closure 绑定、F-03 快照交叉检查是否会先报错）；改后是否同时出现 facts 与 config 两条错误。若步骤仍走不到目标，给出可行的最小改法。
d) R1-04 新函数对 `checks` 非 dict 的处理是否不再抛异常；回归用例设计是否成立。
e) R1-05/06 §0.2 例外、§0.8 守卫点名、§1.3 排除式 grep 是否与代码事实一致（`docs_lint.py` 读取范围、四个守卫脚本名）。
f) R1-07 §4 与 `code_change_pending.md` Q7 的迁移表述是否准确（`receipt_validate.py:115-116`）。
g) v2 相对 v1 有无引入新的锚点/白名单/回归问题。
