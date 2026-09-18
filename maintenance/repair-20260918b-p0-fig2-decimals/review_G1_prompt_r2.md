# 工单 G1 复核提示词（只读，r2：核 v2 对 r1 三条的修订）

## 纪律
同 `review_G1_prompt.md` 第 1–3 条（禁读 `~/.codex/`、archive/blind-reviews/.staging_*/attic、本工程与 repair-20260918-p0-f04-f07 以外的历史 maintenance、Desktop/Documents；只读离线不改文件；报告全文打印到 stdout，首行 `# 工单G1复核r2：通过` 或 `# 工单G1复核r2：退回`，退回逐条编号 G1-R2-NN）。

## 任务
复核 `maintenance/repair-20260918b-p0-fig2-decimals/workorder_G1_fig2.md`（v2）对 `review_G1_reply_r1.md` 三条的消化：
a) R1-01：§2.5 用例 1 "先执行再汇总断言"的写法是否真能在基线各自取到 producer 与消费者两条 RED；§0.7 编号是否已订正。
b) R1-02：§2.5 用例 4（e1 大庄#1 + e2 小庄#2，series 只画 e1）在基线放行、按 §2.1/§2.2 改后拒且错误文案含 `['e2']`，补齐两线后放行——静态推演或内存执行确认；数值（e2 current 100 / total 1000 → 10.0，容差 0.05pp）是否自洽。
c) R1-03 已转 G2 工单处理，本轮只确认 G1 v2 没有残留"基线 errors=[]"类不成立前提。
d) v2 其余文字（§0.2 importer 行号 :1641/:2117、§4 迁移说明）是否与代码事实一致；v2 相对 v1 有无引入新的锚点/白名单/回归问题。
只核 v2 变更面，不必重做 r1 已通过的全量核查。
