# repair-20260814-batch3 Round 3 终审补充确认（Addendum）

## 最终判定：PASS

Round 3 唯一未决项 BR3-01 已闭合，未发现新的必修项。批 3 终审由
`CONDITIONAL` 正式翻转为 **PASS**。

据此，R10-5、R10-6、R10-16、R10-17 可转 `CLOSED`；可执行批 3 closure，
并可合并 main。本补充确认不代替后续 closure 施工本身，也未在本轮改写台账状态。

## 复核范围

- 修复提交：`25f893d63d4552ec165ea097473824017a603a94`。
- diff 基线：`cdbac109f1d749d8fd4b907dab1ce99101496c37..25f893d63d4552ec165ea097473824017a603a94`。
- 隔离副本：`/tmp/tca-r3-addendum.Z5K3O9/repo`；副本无 `.git`，并在复制时明确排除
  `maintenance/repair-20260814-evmobs/` 与 `scripts/tests/test_evm_observation.py`。
- 独立复现脚本：`/tmp/tca_r3_addendum_repro.py`，SHA-256
  `cc6f4901afd69a29ca090d93a350d3261879ce3d9d088a62d225d8037b7c5dfc`。
- 仓库测试目标与隔离副本对应文件 SHA-256 均为
  `ee0347e1f9b95fe631b01f3f69ad730e6edabd000ee627a265656bb9489f2957`。

## 验证清单

### 1. BR3-01 最小复现与真实台账

真实 `r10_ledger.md` 独立解析得到 27 条、27 个唯一 ID，
`r10_ledger_failures()` 返回 `[]`。

以下反例均以真实台账为基底，仅替换 R10-1 的首个状态载体；会改变 CLOSED 计数的反例
同时把现役声明从 19 改为 20，以排除计数闸代替状态闸拒绝的可能：

| 反例 | 实测结果 | 命中错误 |
|---|---|---|
| U+200B 插词 `【CLO\u200bSED 6.41.0】` | 拒绝 | `状态载体无法识别为枚举` |
| 未知关键字 `【CLOSED_PENDING 6.41.0】` | 拒绝 | `状态载体无法识别为枚举` |
| HTML 实体 `【CLO&#83;ED 6.41.0】` | 拒绝 | `状态载体无法识别为枚举` |
| 未闭合括号 `【CLOSED 6.41.0` | 拒绝 | `状态载体括号不配对` |

四例均由目标守卫本身返回非空 failure，未依赖正式测试脚本的外层断言代判。

### 2. 载体边界抽查

- 合法状态列内枚举带尾随字符 `【CLOSED 6.41.0x】`：拒绝，命中
  `状态载体无法识别为枚举`。
- 同一合法状态列含两个合法载体
  `【CLOSED 6.41.0】【CLOSED 6.42.0】`：拒绝，命中 `状态标记不唯一`。
- 实现对条目行逐 cell 提取全部 `【...】`，不存在 first-match-wins；严格枚举必须对单个
  载体 `fullmatch`，合法状态列没有载体时才可归 OPEN。
- 合法枚举落在非状态列仍由既有 `正文列出现状态样式标记` 拒绝；既有 statusish、裸状态词、
  列数、ID 集合/唯一性与现役计数守卫均保留。

### 3. diff 授权与禁触核对

`git diff cdbac10..25f893d` 共 4 个文件：

- 新增 Round 3 报告、消化轮 3 工单和完工记录 3 份流程证据文件；
- 唯一业务 hunk 为 `scripts/tests/test_repair_batch3_gates.py`，71 行新增、1 行替换；
- 替换行仅把状态列的原正则 `findall` 改为“已提取载体＋合法列＋严格枚举”的过滤结果；
  未删除、放宽或改写其他既有守卫；
- `git diff --check cdbac10..25f893d` 为 rc=0；
- 禁触目录/文件 `maintenance/repair-20260814-evmobs/`、
  `scripts/tests/test_evm_observation.py`、`archive/**`、`blind-reviews/**` 在该 diff 中均为零。

结论：业务改动只对应 BR3-01 授权修法与回归 owner，没有混入额外功能或既有守卫放宽。

### 4. 定向测试与全量 suite

在同一隔离副本执行：

```text
python3 scripts/tests/test_repair_batch3_gates.py  rc=0
```

输出包含真实台账绿例、BR3-01 三项裁判反例、未闭合与嵌套括号回归，以及既有
F04/F05/F07 全部回归，最终为：

```text
PASS: 批3 deploy-sync/env-check/R10-ledger gates 回归全部通过
```

`python3 scripts/tests/run_all.py` 在受限沙箱内完成 99 项枚举：97 PASS；仅下列两项在业务
断言前因 `socket.bind(("127.0.0.1", 0))` 返回 `PermissionError: [Errno 1] Operation not permitted`
而 rc=1：

```text
test_batch3_solana_vertical_slice.py
test_batch3_evm_vertical_slice.py
```

随后在允许 loopback 的同一隔离副本按原命令分别完整复跑：

```text
python3 scripts/tests/test_batch3_solana_vertical_slice.py  rc=0
PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release

python3 scripts/tests/test_batch3_evm_vertical_slice.py     rc=0
PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
```

因此业务测试结果合成为 99/99 通过；两项初始失败是已复验的 loopback 沙箱能力限制，
不是测试断言或 BR3-01 回归失败。`run_all.py` 内含的 `invariant_scan.py` 同样 PASS。

## Findings

无新 finding；无必修项。

## 终审处置

- BR3-01：`CLOSED`。
- 批 3 Round 3 终审：`PASS`（由原 `CONDITIONAL` 翻转）。
- R10-5 / R10-6 / R10-16 / R10-17：可转 `CLOSED`。
- 批 3 closure：可执行。
- 合并 main：可执行。

BLINDREVIEW_R3_ADDENDUM_COMPLETE
