# 持仓分布图 matplotlib 双轴升级完工报告

## 结论

工单白名单内施工完成。基线 `252a11b`；未执行任何 git 写操作。版本五处统一为 `6.53.0`，新增分布图回归后 SUITE 为 140；允许 loopback 的完整环境执行 `python3 scripts/tests/run_all.py` 退出码 0，140/140 全部通过。

## 改动文件清单

- `scripts/report/holder_distribution_scan.py`
  - 新增纯数据函数 `_chart_series(scan)`：按 bin index 生成 bars、expected、right_pct、对数 xticks、title 与 low_sample note。
  - 重写 `write_png(path, scan)`：函数内导入 chart_style/matplotlib；normal 输出柱、期望阶梯线、净供应百分比右轴；low_sample 输出单轴说明；1800×840；异常路径 `finally` 关闭 figure。
  - 删除旧裸 PNG 实现及孤儿 import `struct`、`zlib`；`shutil` 保留。
- `scripts/tests/test_distribution_chart.py`
  - 新增三件套回归：原反例与数据契约、initial/final 标准生产路径及 low_sample 同族变体、matplotlib 毒丸失败分支。
- `scripts/tests/run_all.py`
  - 仅新增一行 `test_distribution_chart.py` 登记，SUITE 139→140。
- `VERSION`
  - `6.52.15`→`6.53.0`。
- `pyproject.toml`
  - 仅 `[project] version` 同步为 `6.53.0`。
- `SKILL.md`
  - 仅第 23 行 skill-version 注释同步为 `6.53.0`。
- `CHANGELOG.md`
  - 版本索引顶部新增 6.53.0 一行；新增 6.53.0 六栏详情段。
- `maintenance/repair-20260827-distchart-axes/red_evidence.md`
  - 保存真实 RED、施工后 GREEN 与点名消费面测试证据。
- `maintenance/repair-20260827-distchart-axes/done.md`
  - 本完工报告。

`maintenance/repair-20260827-distchart-axes/workorder.md` 为施工前已有的未跟踪工单输入，不是本次施工改写。

## 红绿证据摘要

### RED

- 命令：`python3 scripts/tests/test_distribution_chart.py`
- 退出码：1。
- 关键反例：无 `_chart_series`；旧 PNG 合法但尺寸为 800×420；initial 与 final→record-round 标准链均保持旧尺寸；matplotlib 毒丸下仍成功产降级图。
- 同时确认一项既有正性质：旧 `write_png` 不修改传入 scan 对象。

### GREEN

- 同命令退出码：0。
- 13 项检查全绿：bars/expected/right_pct 对齐且保留零值档、数据推导对数刻度、final 轮次标题、normal/initial/final 均为合法 1800×840 PNG、scan 不变、无 `base_bins` 判 low_sample、record-round 真拷贝链、缺 matplotlib 显式失败且零降级图。
- 点名消费回归全绿：
  - `test_distribution_gate.py`：退出码 0。
  - `test_a4_gate.py`：退出码 0，23 项通过。
  - `test_repair_batch_c.py`：退出码 0，227 checks。
  - `test_repair_batch_d.py`：退出码 0。

完整逐行摘录见 `red_evidence.md`。

## 版本与 lint

- `python3 scripts/tests/changelog_lint.py`：退出码 0；`PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 58 条 + 归档 139 条`。
- `python3 scripts/tests/test_version_consistency.py`：退出码 0；`PASS: M-03 version metadata consistent at 6.53.0`。
- 五处一致：`VERSION`、`pyproject.toml`、`SKILL.md:23`、CHANGELOG 索引行、CHANGELOG 详情段均为 6.53.0。

## run_all 证据

第一次在受限沙箱内执行同一原命令：138 PASS / 2 FAIL。仅 `test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py` 在 `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 绑定 loopback 时收到 `PermissionError: [Errno 1] Operation not permitted`；其余 138 项全绿。该次不作为完工绿。

按权限规则在允许 loopback 的环境用原命令完整重跑：

```text
      PASS  test_batch3_solana_vertical_slice.py PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release
      PASS  test_batch3_evm_vertical_slice.py PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
      PASS  test_distribution_gate.py PASS: distribution gate red-green contract
      PASS  test_distribution_chart.py PASS: distribution chart contract
      PASS  test_version_consistency.py PASS: M-03 version metadata consistent at 6.53.0
========================================================
全部通过
```

- 命令：`python3 scripts/tests/run_all.py`
- 机械分母：140。
- 最终退出码：0。
- 最终结果：140 PASS / 0 FAIL，`全部通过`。

## 工单五栏自审

### 1. 不变量：通过

- `write_png(path: Path, scan: dict) -> None` 签名未变；唯一调用行 `atomic_json(out, scan); write_png(chart, scan)` 逐字未动。
- 三个 PNG 路径字面量逐字未动：`charts/distribution_stage1.png`、`holder_distribution_round.png`、`charts/final/holder_distribution_current.png`。
- `scan_output_paths`、`cmd_record_round`、`analyze`、`validate_scan`、`semantic_payload` 及判定/校验代码未改。
- low_sample 缺整个 `base_bins` 键时不抛异常；`write_png` 不修改 scan；生产侧仍先原子写同一 scan JSON，再只写指定 PNG。
- 未新增 payload/schema 字段；未新增模块顶层第三方 import。

### 2. 消费面：通过

- record-round、A5 seal、build_html、audit_release_gate 均未修改。
- final 测试使用真实 `--stage final --round 1` 与 `record-round`，未用 `--chart` 冒充；轮次图与终版图哈希相等。
- 工单点名的四个既有测试文件全部退出码 0。

### 3. 三件套测试：通过

- 原反例真实 RED 已先留档；施工后同测试 GREEN。
- initial/final 标准路径与无 base_bins 的 low_sample 变体全绿。
- 子进程 matplotlib 毒丸显式失败且不产降级图。

### 4. 新建代码自审：通过

- `from chart_style import setup` 与 `import matplotlib.pyplot as plt` 均只在 `write_png` 函数体内。
- 未新增 payload 字段。
- 未触碰三个路径字面量与唯一调用行。
- figure 由 `try/finally` 保证异常路径也执行 `plt.close(fig)`。
- 新实现无任何 `1e18`/decimals 换算字面量；横轴直接使用百分比。
- 裸 PNG 代码已删除；`struct`、`zlib` import 已删除；`shutil` 保留供 record-round 使用。

### 5. 归因预判：通过

- 缺 matplotlib 时新测试证明显式失败；全量 `env_check.py` 已确认三层依赖满足。
- 数据错位由 `_chart_series` 的 bars/expected/right_pct/xticks 定点断言防回流。
- matplotlib 首次导入与字体缓存导致的预期耗时未通过改 runner、挪 import 或降级图片规避。

## 白名单与遗留

- `git diff --check`：通过，无 whitespace 错误。
- `git status --short` 所示改动均属于工单白名单；无白名单外跟踪文件改动。
- 测试生成的目标 `.pyc` 已按明确路径逐个清理，未批量删除文件或目录。
- 遗留：无代码或测试遗留。首轮两项 loopback 失败已由允许 loopback 的完整 140 项重跑消解，不作为残留失败。
