# 工单 E 复核提示词（只读，r2：核 v2 对 r1 两条 E-R1-01/02 的修订）

## 纪律
同 `review_E_prompt.md` 第 1–3 条；报告全文打印到 stdout，首行 `# 工单E复核r2：通过` 或 `# 工单E复核r2：退回`，退回逐条编号 E-R2-NN。

## 任务
只核 `workorder_E_version.md`（v2）对 `review_E_reply_r1.md` 两条的消化：
a) E-R1-01：§2 G2 条目里 schema 计数是否已分清"既有 18 处替换（8+6+1+3）／当前 v2 全量 19 处（含 `check_facts_decimals` docstring 新增 1 处）"，数字与 `grep -rn --exclude-dir=__pycache__ 'evm-observation-bundle/v2' scripts references` 实跑一致。
b) E-R1-02：工艺条里 G2 盲审未整跑是否改为 18 项（17＋1）并与 `blind_G2_reply_r1.md:14` 一致。
c) v2 相对 v1 除标题/变更记录/上述两句外有无其他改动（`git diff HEAD~1 -- <工单>` 应只这四处）；有无引入新问题。
不需重跑 r1 已通过的锚点、来源链、轮次、字节核查。
