# 待决代码改动台账（drift-audit 工程）

用户 2026-09-16 裁决：本工程原则上只改文本；凡必须改代码的项先记录在此，循环结束后统一交用户决策，期间不施工。

| 编号 | 来源 | 位置 | 问题 | 推荐修法 | 牵连面 | 用户裁决 |
|---|---|---|---|---|---|---|
| D1 | 盲审 R1 | `scripts/report/wave_scan.py:735-746` vs `references/analyze-workflow.md:161` | 文档承诺"份额阈值一律整数运算"，代码用浮点算 0.1% 线与必裁决线；已复现 total=10^24、持仓恰 0.1% 时判 False（阈值上浮 131072 raw） | 两处比较改整数交叉相乘（或 Fraction），补"恰好整数份额"回归用例 | wave_scan.py 不在 producer_history 登记；invariant_manifest 只登记脚本名与 schema；测试只绑产物哈希；旧案按当前版本重验需重跑（既定设计） | 待决 |

## D2（R4 盲审 D4 附带）`scripts/solana/decode_txs_v2.py:8` 文头注释"按 sig 前 2 字符分 256 片"
- 性质：仅 docstring 文字，与 `:75` 实际按 sig 前 2 字符（Base58 字母表，可能分片数远多于 256）不符；零行为影响。
- 文档侧同错已由工单 R4 D4 改正；代码文件按用户原则不动，是否顺手订正注释待用户决策。

## D3（R5 盲审 D2 附带）`scripts/report/standard_charts.py:283` `plot_whale_vs_price` 文档串"线超 8 条时可将持仓较小的实体合并成一条避免花屏"
- 性质：仅 docstring 文字；split-run 收口闸 `stage2_closeout.py:197-198` 对 merge_groups 硬拒，merge_groups 属 7.2 遗留清单。零行为影响。
- 文档侧同错已由工单 R5 D2 删除许可；代码文件按用户原则不动，是否顺手订正待用户决策。


## 用户裁决（2026-09-16）

- D1：**选 B**——不改码，文档登记为已知例外（触发评估：翻转窗 ≤1e-16×阈值，需峰值恰等于阈值；APU 案 2753 址中 1 址命中，靠回落理由兜住；每案粗估一至三成概率至少一址静默丢标记）。
- D2、D3：**改注释/docstring**（零逻辑改动）。
- 落地工单：`workorder_r7.md`。
