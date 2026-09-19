# 工单 F04 复核提示词（只读，r2）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918d-p1-f01-f04/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F04复核：通过` 或 `# 工单F04复核：退回`。退回时逐条给出：编号（F04-R2-NN）、工单位置、事实、修订建议。通过时列出实际核过的项。
3. 这是修复计划复核（非攻击式验收）。

## 任务
复核 `maintenance/repair-20260918d-p1-f01-f04/workorder_F04_retail_bucket.md`（**v2**）与 `code_change_pending.md` Q5/Q6/Q7 是否正确消化了 `review_F04_reply_r1.md` 的四条意见，且没有引入新问题。工作目录＝本仓库根（`scripts/` 与 868d3f61 逐字节相同；F01 尚未施工）。只核：
a) R1-01：§0.7 与 §2.3 RED 第 3/4 项是否已改为 `len(散户)==2*len(dates)==8`、基线取证用 `expect_rc=0`；四项"三 RED 一 GREEN"表述是否可执行。
b) R1-02：Q5 是否已写明 producer 分列（`replay_edges.py:634-639`）/consumer 并桶（`camp_series_provenance.py:66/:318`）、显式散户触发既有末点对账冲突（`:865/:875`）本轮保留不修；`build_evolution` 标量累加说明是否保留。
c) R1-03：§2.3 说明①是否已改 `:577`，保证是否限定为"全新输出目录不生成 `camp_series.json`"。
d) R1-04：§2.1 说明③与 Q6 是否已把检索命中分类订正（含 `standard_charts.py:81`）、"正式案零实例"标为此前 review 记录、LAYOFF 27 处标为调度方本机核验。
e) r1 已通过的项（修法、锚表六处、回归面、终点判据、白名单）本轮无需重演，仅确认 v2 未改动这些段落的实质内容。
