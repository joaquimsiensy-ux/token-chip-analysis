# 持仓分布图修复红绿证据

## RED（基线生产代码未修改）

- 命令：`python3 scripts/tests/test_distribution_chart.py`
- 退出码：`1`
- 日期：2026-08-27
- 基线：工单声明的 `252a11b`；执行时只新增测试文件并在 `run_all.py` 登记，尚未修改 `holder_distribution_scan.py`。

```text
FAIL [_chart_series 已提供]
FAIL [normal 渲染合法 PNG 且 1800x840] valid=True, size=(800, 420)
ok   [write_png 不修改 scan 对象]
FAIL [initial 标准生产路径产 1800x840 PNG] PASS: initial NOT_EVALUABLE -> .../case/distribution_scan.json
 size=(800, 420)
FAIL [无 base_bins 判为 low_sample] {}
FAIL [low_sample note 明示原因]
FAIL [final→record-round 标准拷贝链产终版图] PASS: final NOT_EVALUABLE -> .../dist_rounds/round_1/distribution_scan.json
PASS: round 1 -> LOW_SAMPLE
FAIL [matplotlib 缺失显式失败且不产降级图]
FAIL: distribution chart contract
```

结论：旧实现确实缺少数据序列契约，且生产路径只产 800×420 裸 PNG；缺 matplotlib 时不会显式失败，反而继续产降级图。反例能够咬住本工单要修的行为。

## GREEN（施工后追加）

- 命令：`python3 scripts/tests/test_distribution_chart.py`
- 退出码：`0`

```text
ok   [_chart_series 已提供]
ok   [bars 按 index 保留零值档]
ok   [expected 按 index 对齐]
ok   [right_pct 按净供应且保留零值档]
ok   [x 刻度使用数据推导的对数位置]
ok   [final 标题含轮次与私人主桶]
ok   [normal 渲染合法 PNG 且 1800x840]
ok   [write_png 不修改 scan 对象]
ok   [initial 标准生产路径产 1800x840 PNG]
ok   [无 base_bins 判为 low_sample]
ok   [low_sample note 明示原因]
ok   [final→record-round 标准拷贝链产终版图]
ok   [matplotlib 缺失显式失败且不产降级图]
PASS: distribution chart contract
```

点名消费面回归：

- `test_distribution_gate.py`：退出码 0，`PASS: distribution gate red-green contract`
- `test_a4_gate.py`：退出码 0，`a4_gate 契约测试全部通过（23 项）`
- `test_repair_batch_c.py`：退出码 0，`PASS: repair batch C (F-05+F-04+fixround1+fixround2) 227 checks`
- `test_repair_batch_d.py`：退出码 0，`BATCH D 全部通过`
