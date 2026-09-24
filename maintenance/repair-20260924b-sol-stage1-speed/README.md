# 工程 repair-20260924b：Solana −1 机械段提速（共享地图驳回继承 / 强制用地图 / Helius 压缩 / 修复阶段单次 SQD 探针）→ 版本 9.2.0

出处：用户 2026-09-24 裁决（原话摘要）：「1.驳回过的 slot 记进共享地图,后案只做一次便宜的 SQD 状态确认就继承 2.让codex/opus跑-1阶段时使用共享地图 3.Helius 下载也开压缩 4.同一个候选 slot 被 SQD 探两次，看看怎么修复。1-4 现在就改 skill」。流程＝每单：写工单→codex 只读复核→融合→codex 施工→codex 盲审（连败三次换 opus）→全部完成后 codex 收官 review。调度方（Fable）只写工单/验收/commit，不写代码。

调度方实证（PYTHIA 0919 案，案卷在调度方本机，本仓库不含）：−1 纯机器时间 ≈85 h＝转账采集 22.5 h＋覆盖普查 20 h＋α 修复 37 h＋其余 ≈5 h。α 修复 157,700 候选中 155,642（98.7%）与 TROLL 0905 共享地图候选相同；修复 census refuted 150,133 / confirmed 7,567；补边 0 条；Helius getBlock 下载 366.7 GB（均 2.33 MB/块，未压缩，带宽瓶颈 92 slot/min）；普查未带 `--known-map`（开工失误，中途不可换图）。

| 单 | 内容 | 生产文件 | 顺序 |
|---|---|---|---|
| W1 | 共享地图 `refuted_slots` 由修复 census 填充；探针复用地图时对重查未变的 refuted slot 记 `INHERITED_REFUTED`，不再进候选；校验器同步重算 | `scripts/solana/sqd_coverage_probe.py`、`scripts/lib/solana_exact_validate.py` | 1 |
| W4 | 修复阶段每候选 slot 的 SQD 请求由 2 次（探针＋census）合并为 1 次 | `scripts/solana/sqd_gap_repair.py` | 2 |
| W3 | `net.py::curl_json` 加 `--compressed` | `scripts/lib/net.py` | 3 |
| W2 | `find-known-map` 子命令；split-run/命令/分册/README 文档硬性；版本 9.2.0；源码提交后由 WR-b 登记 probe | 文档＋`sqd_coverage_probe.py`＋版本四处；producer_history 仅由 WR 修改 | 4 |

施工严格串行（同一工作树）；复核/盲审只读可并行。基线：W1＝`cc6298b`（9.1.1）；后续各单基线＝前一单收官 commit（派工时更新工单 §0.1 与行号）。


## 顺序调整（2026-09-24，r2 复核后）

实际施工顺序：**W3（已通过复核，先行）→ W1 → W4 → WR-a（登记 repair sha）→ W2 → WR-b（登记 probe sha）→ 收官 codex review**。W3 与 W1/W4 无文件交集；WR 登记单见 `workorder_WR.md`。每单：工单 → codex 只读复核（通过才派）→ codex `--write` 施工 → 调度方本机验收（定向测试＋run_all）→ commit → codex 只读盲审（PASS 才进下一单；连败三次换 opus）。
