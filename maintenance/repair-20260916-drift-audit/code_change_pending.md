# 待决代码改动台账（drift-audit 工程）

用户 2026-09-16 裁决：本工程原则上只改文本；凡必须改代码的项先记录在此，循环结束后统一交用户决策，期间不施工。

| 编号 | 来源 | 位置 | 问题 | 推荐修法 | 牵连面 | 用户裁决 |
|---|---|---|---|---|---|---|
| D1 | 盲审 R1 | `scripts/report/wave_scan.py:735-746` vs `references/analyze-workflow.md:161` | 文档承诺"份额阈值一律整数运算"，代码用浮点算 0.1% 线与必裁决线；已复现 total=10^24、持仓恰 0.1% 时判 False（阈值上浮 131072 raw） | 两处比较改整数交叉相乘（或 Fraction），补"恰好整数份额"回归用例 | wave_scan.py 不在 producer_history 登记；invariant_manifest 只登记脚本名与 schema；测试只绑产物哈希；旧案按当前版本重验需重跑（既定设计） | 待决 |
