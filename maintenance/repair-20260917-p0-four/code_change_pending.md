# 登记不修台账（repair-20260917-p0-four，调度方维护）

| # | 来源 | 内容 | 归属 | 状态 |
|---|---|---|---|---|
| P1 | 工单 A §4 | 图 2 收据消费者不验 `lines_checked>0` 与实体线覆盖完整性 | split-run.md:183 用户 2026-08-18 拍板接受的残余风险 | 不修 |
| P7 | 工单 A v3 §4（codex r2） | `parse_constant` 管不住非 pct 字段里的 `1e400` 被解析成 inf | 范围外；pct 由 A2、输出序列由 A4 兜底 | 登记 |
| P8 | 工单 A v4 §4（codex r3） | fig1 豁免键检查 `figures_from_facts.py:141-144` 遇超大整数 `math.isfinite` 抛 OverflowError | 范围外（§0.4 不改） | 登记 |
| P9 | 工单 A v4 §4（codex r3） | 普通对账 PASS/FAIL 分支写收据（`:334`/`:338`）的 OSError 仍直接传播，A3 只收敛新增输入失败分支 | 既有边界 | 登记 |
| P2 | 计划 R09 | `data-pipeline-evm-recon.md:136` 要求预筛 0.1%，`peaks_daily.py:88` 默认 `--pct 0.01`（1%）且 docstring 仍主张 1% | codex review R04（P1），不在本工程 | 待另单 |
| P3 | 计划 R09 | APU分析0801 `data/peaks_daily/trigger_days.json` 的 `days` 键为原因名而非日期（误用第三格式） | 存量输入漂移 | 该案再发布前修正 |
| P4 | 计划 R07 | 发布闸只验 peak override 的证据在位与哈希，不验其数学正确性 | 残余风险 | 登记 |
| P5 | 工单 A v2 §4（codex r1 f 项） | `stage2_closeout.py:63` 裸 `json.loads` 读序列（:459/:468），未经严格解析 | 范围外；:458 序列化经 A4、:464 对账经 A1/A2 兜底 | 登记 |
| P6 | 工单 A v2 §4 | fig1 state 非豁免键含 NaN 仍进绘图（`figures_from_facts.py:109` 保留宽松解析以维持 burn_cum_pct 字段级报错契约） | 基线行为 | 登记 |
| P10 | 工单 B v2 §4（codex r1 B-R1-05） | `expanded_economic_control_range_raw` 上限超出"下限＋Σexpanded"的部分（文档允许的疑似设施受益权增量）无账本来源，闸只验下界 | 残余风险 | 登记 |
