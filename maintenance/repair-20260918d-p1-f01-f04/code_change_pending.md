# 登记不修台账 —— repair-20260918d-p1-f01-f04（调度方维护）

| 编号 | 段 | 内容 | 处置 |
|---|---|---|---|
| Q1 | F01 | 第二源价格非有限（DefiLlama/币安 JSON 里出现 NaN/inf）在 `:175` 前规范化为 `None`，走既有 SKIP 分支（对照不可得），收据 `second_price=null` 可序列化；全部抽样点 SKIP 仍汇总 ALL_SKIP 退出 3、closeout 拒（v2 按 R1-01：v1 只改 status 会让 `p2=nan` 进 results 撞 `allow_nan=False` 抛 ValueError） | 不扩为"第二源坏即 FAIL" |
| Q2 | F01 | closeout 逐点重算用的阈值常量（5/15）复制自 `price_check.py:43`，**不 import** `scripts/prices/price_check.py`：报告层离线，`invariant_manifest.json:779` 把 price_check 登记为 `requests` 类脚本，closeout 引入它会把网络模块拉进发布闸 | 常量旁注明来源；两端相等由 `price_receipt_content_enforced` 段 6g 相等断言（`==(5.0,15.0)`）＋WARN 边界用例守（v2 按 R1-03：仅 66.67% 用例守不住 5/15→6/16 漂移） |
| Q3 | F01 | review F05（P2）同源双源（`--second defillama` 对 defillama 主源）本轮不修 | 用户 0918 只点名 F01/F04 |
| Q4 | F01 | 存量代价（v2 按 R1-05 改用真实解析规则，调度方本机 2026-09-18 执行，复核方禁读案卷）：①案卷目录 `/Users/uravvv/Desktop/老公用/fable筹码分析` maxdepth 4 共 64 个 price 类 json/csv，其中 28 个可被 `price_check._load_series` 解析（其余为收据/非序列格式），按 `not (isfinite(p) and p>0)` 逐点检查 **0 个文件命中**（覆盖 `nan`/`inf` 小写、`1e309` 溢出、0/负价）；②maxdepth 7 检索 `*price*check*.json`/`price_checks.json`/含 `"second_source"` 的 json：**不存在任何 `price_check.py` 生成的收据**（0 份含 `points`；APU 0801 `dual_source_crosscheck.json` 是转账双源交叉非价格收据）→ 消费者对主价"有限正数"收紧（严于基线生产者 p1≤0→SKIP）无实际迁移对象；APU 0914 案自定义格式收据本就待重跑（上轮 Q8） | 用户 0918 裁决 APU 暂不重跑，进 −3 时再补 |
| Q5 | F04 | Solana 不拒显式「散户」：`build_evolution.py:173` 以「散户」为默认桶、`:181` 标量加残差，无重复 append；LAYOFF 案 `data/entity_camps.json` 有 27 处显式「散户」（存量，走 `load_addr_camp_json(chain_family="solana")`，调度方本机核验）。`replay_edges.py`：producer 分列——`camp_of:634-639` 对 spec 内地址返回其阵营名（含显式「散户」）、其余返回动态桶「首30分钟狙击者」/「其他散户」；consumer `camp_series_provenance.py:66/:318` 按 `SOL_DYNAMIC_BUCKET_MERGE` 把两个动态桶并入「散户」。显式「散户」还会触发既有末点对账冲突（`endpoint_reconcile:865` 计入 `spec_sum`、`:875` 又算 `100−spec_sum`，同时报两条不等）——本轮保留、不修（v2 按 R1-02 订正） | 保留桶按 `chain_family=="evm"` 判，与 review"维持 Solana 分格式语义"一致 |
| Q6 | F04 | 不改两 EVM 引擎的 append 结构（"显式散户与残差合并后只 append 一次"）：fail-closed 拒配置改动更小，且「散户」设计上就是残差桶；"正式案从未配置过"为此前 review（868d3f61 六视角 §F04）全量检索记录，本仓库检索命中仅序列字段/输出示例/绘图颜色映射（`standard_charts.py:81`）（v2 按 R1-04 订正） | 能改不增 |
| Q7 | F04 | references 零改动：文档无"散户可在 camps 里配置"的示例（`monitoring-package.md:79` 是序列输出示例、`playbook-entity-cluster-methods.md:126` 为自然语言、`scan-schemas.md:613/621` 已写"散户残差"）；契约由 `camp_spec.py` docstring 边界段承载，CHANGELOG 登记属收官段 | 本轮文档零改动 |
| Q8 | 环境 | 上轮 Q15 沿用：本机跑 `test_stage2_closeout.py`/`test_a4_gate.py` 须 `export MPLCONFIGDIR=$HOME/.matplotlib`（macOS 27 字体枚举空→matplotlib 建缓存 KeyError） | 环境项不改代码 |
| Q9 | 版本 | 9.0.1 vs 10.0.0（`ruling_20260918.md`） | **用户 09-18 裁决：9.0.1** |
