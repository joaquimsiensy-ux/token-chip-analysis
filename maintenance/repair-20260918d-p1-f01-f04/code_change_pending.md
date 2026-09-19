# 登记不修台账 —— repair-20260918d-p1-f01-f04（调度方维护）

| 编号 | 段 | 内容 | 处置 |
|---|---|---|---|
| Q1 | F01 | 第二源价格非有限（DefiLlama/币安 JSON 里出现 NaN/inf）按 SKIP 处理而非拒：与既有 `None`/`≤0` 同语义＝对照不可得；全部抽样点 SKIP 仍汇总 ALL_SKIP 退出 3、closeout 拒 | 不扩为"第二源坏即 FAIL" |
| Q2 | F01 | closeout 逐点重算用的阈值常量（5/15）复制自 `price_check.py:43`，**不 import** `scripts/prices/price_check.py`：报告层离线，`invariant_manifest.json:779` 把 price_check 登记为 `requests` 类脚本，closeout 引入它会把网络模块拉进发布闸 | 常量旁注明来源；两处漂移由 `price_receipt_content_enforced` 段 6d（真实生产者收据 vs 重算）守 |
| Q3 | F01 | review F05（P2）同源双源（`--second defillama` 对 defillama 主源）本轮不修 | 用户 0918 只点名 F01/F04 |
| Q4 | F01 | 存量代价：案卷目录 `find … price*.json/csv | grep -lE 'NaN|Infinity'` 实证 0 命中（`/Users/uravvv/Desktop/老公用/fable筹码分析`，maxdepth 4，2026-09-18）；存量 PASS/WARN 收据均由真实 `price_check.py` 生成，逐点重算规则逐字同源（含 `round(…, 2)`）故一致；APU 0914 案自定义格式收据本就待重跑（上轮 Q8） | 用户 0918 裁决 APU 暂不重跑，进 −3 时再补 |
| Q5 | F04 | Solana 不拒显式「散户」：`build_evolution.py:173` 以「散户」为默认桶、`:181` 标量加残差，无重复 append；LAYOFF 案 `data/entity_camps.json` 有 27 处显式「散户」（存量，走 `load_addr_camp_json(chain_family="solana")`）。`replay_edges.py` spec 内若配「散户」会与动态桶「其他散户」并桶——未见存量、review 未列，不在本轮 | 保留桶按 `chain_family=="evm"` 判，与 review"维持 Solana 分格式语义"一致 |
| Q6 | F04 | 不改两 EVM 引擎的 append 结构（"显式散户与残差合并后只 append 一次"）：fail-closed 拒配置改动更小，且「散户」设计上就是残差桶、正式案从未配置过（review 全量检索 0 实例） | 能改不增 |
| Q7 | F04 | references 零改动：文档无"散户可在 camps 里配置"的示例（`monitoring-package.md:79` 是序列输出示例、`scan-schemas.md:613/621` 已写"散户残差"）；契约由 `camp_spec.py` docstring 边界段与 CHANGELOG 承载 | 本轮文档零改动 |
| Q8 | 环境 | 上轮 Q15 沿用：本机跑 `test_stage2_closeout.py`/`test_a4_gate.py` 须 `export MPLCONFIGDIR=$HOME/.matplotlib`（macOS 27 字体枚举空→matplotlib 建缓存 KeyError） | 环境项不改代码 |
| Q9 | 版本 | 9.0.1 vs 10.0.0（`ruling_20260918.md`） | **用户 09-18 裁决：9.0.1** |
