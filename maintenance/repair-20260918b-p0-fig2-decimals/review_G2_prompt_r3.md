# 工单 G2 复核提示词（只读，r3：核 v3 对 r2 三条的修订）

## 纪律
同 `review_G2_prompt.md` 第 1–3 条；报告全文打印到 stdout，首行 `# 工单G2复核r3：通过` 或 `# 工单G2复核r3：退回`，退回逐条编号 G2-R3-NN。

## 任务
只核 `workorder_G2_decimals.md`（v3）对 `review_G2_reply_r2.md` 三条的消化：
a) R2-01：§0.5 与 §2.5 的 `grep -n -F -x` 规则下，两处 schema 锚是否各恰 1 命中；工单其余整行锚在 `-x` 规则下是否仍全部唯一（逐个跑一遍，列表给出）。
b) R2-02：§2.9 checks 非 dict 回归的断言文案 `checks 非对象` 是否与 §2.6 函数实际输出匹配；EVM 夹具基线 `[]`→改后拒收的 RED→GREEN 是否成立；§2.11 清单是否已订正。
c) R2-03：§4 与 `code_change_pending.md` Q7 的三类失效原因是否与 `receipt_validate.py:115-120`、`shared_release_receipt.py:75/:2145` 一致。
d) v3 相对 v2 有无引入新问题。
