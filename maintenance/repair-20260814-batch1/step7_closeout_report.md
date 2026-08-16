# 批 1 步骤⑦共享面收口施工报告

日期：2026-08-14  
状态：**COMPLETE（⑦b 已修复唯一生产层 BLOCKER；全量 94/96 通过，另 2 项仅为已由裁判在非沙箱环境证实通过的 loopback bind 环境失败）**

## 1. 收口清单逐项结果

### 1.1 invariant manifest

- 基线实跑 `python3 scripts/tests/invariant_scan.py`：exit 1，准确复现 4 项 discrepancy。
- `scripts/report/figures_from_facts.py` 的 producer 元组已登记为
  `figure1-legend/v1` 与 `figure2-check-receipt/v1`。
- `_write_fig1_legend_receipt` 已登记为 `overwrite_single` 原子 writer。
- `mode_fig1` 的 PNG `os.replace` 已登记为 `overwrite_single` 原子 writer。
- scanner 已能从 producer 的 `FIG1_LEGEND_RECEIPT_SCHEMA` 常量解析 schema；
  A5/发布闸继续 import 该常量消费，没有在 consumer 或 scanner 墡写第二份字面量，
  因此 `invariant_scan.py` 零改动。
- 收口实跑：exit 0，`receipt_producers=55`、`receipt_consumers=63`、
  `transport_calls=62`、`atomic_writes=49`、`formal_entrypoints=58`、
  `exceptions=0`。

### 1.2 P1-05 与共享 new-analysis 夹具

- `test_a4_gate.py` 的 P1-05 已生成并绑定 camp series、producer sidecar、
  fig1 PNG、`figure1-legend/v1` receipt、figure2 receipt 与显式
  `a5-report-seal/v3`；identity gate 的 state hash 随夹具 state 同步更新。
- 未增加生产旁路；图 1与两类 seal 均调用真实生产 CLI。
- `test_a4_gate.py`：23/23，exit 0。
- 全量首跑暴露的 EVM 共享 P1-05 helper 已按同一契约升级：
  `test_review_20260804_p105.py` exit 0；其消费者
  `test_repair_batch_b.py` 41/41、exit 0。
- Solana 共享 helper 升级时，真实 producer 暴露生产层日期格式断链；已在⑦b
  按 producer 正式契约于 consumer 侧最小修复并完成回归。

### 1.3 版本 6.41.0 四处同步

- `VERSION`：`6.41.0`。
- `pyproject.toml [project].version`：`6.41.0`。
- `SKILL.md` 版本注释：`6.41.0`。
- `CHANGELOG.md`：首条索引与首个详情条目均为 `6.41.0`，详情覆盖
  RV-07、RV-04＋RV-17、F-03、F-01、F-04 五项及⑦b 日期兼容修复。
- `test_version_consistency.py`：exit 0，输出
  `PASS: M-03 version metadata consistent at 6.41.0`。
- `changelog_lint.py`：exit 0；活跃 27 条、归档 139 条，唯一性与倒排检查通过。

### 1.4 契约与测试登记

- `test_repair_batch1.py` 已在 `run_all.py` 的 `SUITE` 中，实际分母为 96。
- 本批无新增 CT-*，所以未改 `contract_manifest.json`。
- `contract_manifest.json` 与 `contract_ids_snapshot.json` 均为 146 个 ID，
  排序后集合完全相等。
- `test_contract_routes.py`：exit 0，双向登记、快照和锚点闭合。

## 2. 最终快照全量 suite

最后一次完整 `run_all.py` 实跑：**exit 1，94/96 PASS、2/96 FAIL**。

- 两项环境失败：EVM/Solana vertical slice 在受限沙箱绑定
  `127.0.0.1:0` 时 `PermissionError: [Errno 1] Operation not permitted`。
  这是 loopback 能力限制；裁判已在非沙箱环境证实两项通过。
- 其余 94 项全部通过；`test_review_20260804_p105.py`、
  `test_repair_batch_b.py`、`test_repair_batch_d.py` 及新增日期回归所在的
  `test_repair_batch1.py` 均已进入本次最终全量并通过。

### ⑦ 原生产层阻断的修前最小复现

生产 `camp_series_provenance.series_to_state_form(..., "sol-rows")` 输出日期
`2026-01-01T00:00:00Z`；把该值直接交给生产
`figures_from_facts._parse_date()`，实跑得到：

```text
2026-01-01T00:00:00Z
FAIL: 无法解析日期 '2026-01-01T00:00:00Z'
exit 1
```

这证明⑦停工时 Solana formal camp series 的标准转换输出无法被图 1 producer
消费；⑦b 的修复与绿灯证据见第 6 节。

## 3. 收口验证六连退出码

| 验证 | 退出码 | 结果 |
|---|---:|---|
| `python3 scripts/tests/run_all.py` | 1 | 94/96；仅两项沙箱 loopback bind 失败，裁判环境已过 |
| `python3 scripts/tests/invariant_scan.py` | 0 | 4 项 discrepancy 清零 |
| `python3 scripts/tests/docs_lint.py --all` | 0 | 58 个文档通过 |
| `python3 scripts/tests/changelog_lint.py` | 0 | 版本唯一且倒排正确 |
| `python3 scripts/tests/test_version_consistency.py` | 0 | 四锚均为 6.41.0 |
| `python3 -m py_compile`（步骤⑦/⑦b 改动 Python 文件） | 0 | 通过；cache 写入 `/private/tmp` |

补充定向证据：`test_repair_batch1.py` exit 0；`test_repair_batch_d.py` exit 0；
`test_a4_gate.py` exit 0；`test_review_20260804_p105.py` exit 0；
`test_repair_batch_b.py` exit 0。

## 4. 本步改动面

- 登记：`scripts/tests/invariant_manifest.json`。
- 测试/夹具：`scripts/tests/test_a4_gate.py`、
  `scripts/tests/test_review_20260804_p105.py`、`scripts/tests/test_repair_batch_d.py`、
  `scripts/tests/test_repair_batch1.py`。
- 版本与文档：`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`SKILL.md`。
- 报告：本文件。
- ⑦b 生产改动仅 `scripts/report/figures_from_facts.py` 的 `_parse_date` 一处；
  其余生产文件零变更，`invariant_scan.py` 未改，`archive/` 零变更；未执行任何
  git 命令。

## 5. 遗留项

无遗留生产层 BLOCKER。仅余本沙箱固有限制导致的两项 loopback bind 环境失败；
裁判已在非沙箱环境证实通过，不属于代码失败。

## 6. ⑦b 补充修复

### 修复内容

- 保持 `camp_series_provenance.series_to_state_form(..., "sol-rows")` producer
  及其正式落盘契约不变。
- 仅在 consumer `scripts/report/figures_from_facts.py::_parse_date` 的窄格式元组中
  加入与 producer 契约逐字一致的 `%Y-%m-%dT%H:%M:%SZ`；未使用
  `fromisoformat`，未扩大到其他 ISO 变体。
- `test_repair_batch1.py` 增加最小回归：正式值
  `2026-01-01T00:00:00Z` 必须解析为无时区的
  `datetime.datetime(2026, 1, 1, 0, 0)`；非法值 `2026-13-99Txx`
  仍须以 `SystemExit` 拒绝。

### 先红后绿证据

- 修前 `python3 -c` 实跑：同一正式值触发
  `FAIL: 无法解析日期 '2026-01-01T00:00:00Z'`，exit 1。
- 修后同级复现：返回 `datetime.datetime(2026, 1, 1, 0, 0)`，exit 0。
- 新增正反断言随 `python3 scripts/tests/test_repair_batch1.py` 实跑通过，exit 0。

### 最终验证

- `python3 scripts/tests/test_repair_batch_d.py`：exit 0，输出
  `BATCH D 全部通过`。
- `python3 scripts/tests/run_all.py`：exit 1，94/96 PASS；仅
  `test_batch3_solana_vertical_slice.py` 与
  `test_batch3_evm_vertical_slice.py` 在沙箱绑定 `127.0.0.1:0` 时因
  `PermissionError: [Errno 1] Operation not permitted` 失败。裁判环境已证实
  两项通过，其余 94 项全绿。

### 归因

确认属于**历史漏检**：sol-rows state 直喂 fig1 的端到端路径此前没有测试覆盖；
本批共享夹具接入真实 producer 后首次暴露 producer 正式日期契约与 consumer
窄解析列表之间的断链。
