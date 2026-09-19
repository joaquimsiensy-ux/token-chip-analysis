# 施工 R2：完成

按 `maintenance/repair-20260919-drift-audit2/workorder_r2.md`（v2）完成 D1a、D1b、D2、D3 四处纯文本替换。9 项守卫全部通过，references 净减 66 B；锚外字节保持不变。

## 0. 开工基线（§0.1）

施工 HEAD：`5d3fd0b2c0c979d114dace3747c8fd31a50ed0ee`。以下命令均实际运行，退出码均为 0；`git status --short` 与指定内容基线差异命令的输出均为空。空代码块表示真实空输出。

命令：`git status --short`

```text

```

命令：`git rev-parse HEAD`

```text
5d3fd0b2c0c979d114dace3747c8fd31a50ed0ee
```

命令：`git diff --stat 07c97d6 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md`

```text

```

## 1. 锚核验与逐条改前 → 改后 diff

编辑前对每处锚实际执行 `grep -n -F`，均恰好命中 1 处，行号与工单一致；随后按字节替换。编辑后逐文件与 `HEAD` 原文的唯一指定替换结果比较，验证锚外一字不动。

| 项目 | 文件 | 工单行号 | 实测行号 | 命中数 | 字节变化 |
| --- | --- | ---: | ---: | ---: | ---: |
| D1a | `references/data-pipeline-evm-channels.md` | 219 | 219 | 1 | +28 B |
| D1b | `references/data-pipeline-evm-sources.md` | 28 | 28 | 1 | -113 B |
| D2 | `references/playbook-evidence-wording.md` | 18 | 18 | 1 | -7 B |
| D3 | `references/analyze-workflow.md` | 50 | 50 | 1 | +26 B |

下列为实际 `git diff --no-ext-diff --unified=0` 输出，范围限定为四个施工文件，覆盖 D1a、D1b、D2、D3 的全部改前、改后整行。

```diff
diff --git a/references/analyze-workflow.md b/references/analyze-workflow.md
index dd3630c..db91298 100644
--- a/references/analyze-workflow.md
+++ b/references/analyze-workflow.md
@@ -50 +50 @@
-**记账模型准入 gate（链路由定型后、采集开工前必跑）**：fee-on-transfer/rebase/Token-2022 扩展会让"Transfer 流水重建余额"整体算错且供给闭合发现不了（模型错但自洽）。一条命令 1 分钟出裁决——EVM `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --exploration --out accounting_mode.exploration.json`（eth 侧 --rpc 传 Alchemy 检测更强）；Solana `python3 scripts/solana/accounting_gate_sol.py --mint <mint> --out accounting_mode.json`。A0 是模型预检：EVM 使用探索档并产 `accounting-gate/v1`，文件名固定为 `accounting_mode.exploration.json`，不得占用正式名；正式 `accounting_mode.json` 在 A2 生成 observation bundle 后重跑产出（见 A2 第 3 查）。**exit 0（standard/WARN 级）＝放行**，WARN 逐条抄进报告数据底座节；**exit 2（BLOCK）＝硬停**——向用户报模式与证据，要继续必须人工定制记账模型，禁止套标准管线；**exit 1（检测自身失败）＝修通道重跑，禁止当 standard 放行**。检测原理与判定表见脚本头注。EVM 正式发布产物须带**双时点诚实记录**（批 A F-01/F-B）：`tip_block`（探测时链头）必填且 `as_of_block <= tip_block`，探测块另记 `model_probe_block` 且必须等于 `tip_block`——消费侧两个字段都验，想抬时点必须同时改两处且保持自洽。
+**记账模型准入 gate（链路由定型后、采集开工前必跑）**：fee-on-transfer/rebase/Token-2022 扩展会让"Transfer 流水重建余额"整体算错且供给闭合发现不了（模型错但自洽）。一条命令 1 分钟出裁决——EVM `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --exploration --out accounting_mode.exploration.json`（eth 侧 --rpc 传 Alchemy 检测更强）；Solana `python3 scripts/solana/accounting_gate_sol.py --mint <mint> --exploration --out accounting_mode.exploration.json`。A0 是模型预检：EVM 使用探索档并产 `accounting-gate/v1`，文件名固定为 `accounting_mode.exploration.json`，不得占用正式名；正式 `accounting_mode.json` 在 A2 生成 observation bundle 后重跑产出（见 A2 第 3 查）。**exit 0（standard/WARN 级）＝放行**，WARN 逐条抄进报告数据底座节；**exit 2（BLOCK）＝硬停**——向用户报模式与证据，要继续必须人工定制记账模型，禁止套标准管线；**exit 1（检测自身失败）＝修通道重跑，禁止当 standard 放行**。检测原理与判定表见脚本头注。EVM 正式发布产物须带**双时点诚实记录**（批 A F-01/F-B）：`tip_block`（探测时链头）必填且 `as_of_block <= tip_block`，探测块另记 `model_probe_block` 且必须等于 `tip_block`——消费侧两个字段都验，想抬时点必须同时改两处且保持自洽。
diff --git a/references/data-pipeline-evm-channels.md b/references/data-pipeline-evm-channels.md
index 3a2f7eb..abf4074 100644
--- a/references/data-pipeline-evm-channels.md
+++ b/references/data-pipeline-evm-channels.md
@@ -219 +219 @@ size 与 SHA-256；全部通过后才原子将 v2/v3/pre-schema done 升为
-- 参数化调用：`python3 scripts/evm/multicall_balances.py --token 0x... --input addresses.txt --out balances.json [--rpc URL ...]`。默认 4 个公共节点仅适用于 BSC；跨链必须显式传对应链的 `--rpc`，禁止改源码注入标的。
+- 参数化调用：`python3 scripts/evm/multicall_balances.py --token 0x... --input addresses.txt --out balances.json [--chain <链> --rpc URL ...]`。默认 4 个公共节点仅适用于 BSC；跨链必须显式传对应链的 `--chain` 与 `--rpc`，禁止改源码注入标的。
diff --git a/references/data-pipeline-evm-sources.md b/references/data-pipeline-evm-sources.md
index 56cd00b..fe7a053 100644
--- a/references/data-pipeline-evm-sources.md
+++ b/references/data-pipeline-evm-sources.md
@@ -28 +28 @@
-| 千级地址现时余额 | scripts/evm/multicall_balances.py | 见 §3.5；用 `--token/--input/--out` 注入本案参数，非 BSC 链另显式传 `--rpc`，禁止改源码注入标的 | （SIREN，07） |
+| 千级地址现时余额 | scripts/evm/multicall_balances.py | 见 §3.5 | （SIREN，07） |
diff --git a/references/playbook-evidence-wording.md b/references/playbook-evidence-wording.md
index 09e7747..a92a70b 100644
--- a/references/playbook-evidence-wording.md
+++ b/references/playbook-evidence-wording.md
@@ -18 +18 @@
-| 措辞 | 事实将被写入 TL;DR、正文、图题或表格 | 按 §11 唯一权威表选择措辞，区分运营控制/链上位置/最终受益权 | 黑箱、截断样本、未决候选或全史未闭合时不得发布完整阴性 | `report_facts.json`、措辞表、facts gate |
+| 措辞 | 事实将被写入 TL;DR、正文、图题或表格 | 按 §11 唯一权威表选择措辞，区分运营控制/链上位置/最终受益权 | 黑箱、截断样本、未决候选或全史未闭合时不得发布完整阴性 | `facts.json`、措辞表、facts gate |
```

锚外字节一致性核验原始输出（退出码 0）：

```text
D1a: PASS (prescribed replacement only; anchor-external bytes unchanged)
D1b: PASS (prescribed replacement only; anchor-external bytes unchanged)
D2: PASS (prescribed replacement only; anchor-external bytes unchanged)
D3: PASS (prescribed replacement only; anchor-external bytes unchanged)
```

## 2. §1.1 字节实测

| 统计范围 | 开工前 | 完工后 | 约束 | 结果 |
| --- | ---: | ---: | --- | --- |
| `SKILL.md` | 8021 B | 8021 B | = 8021 B，不变 | PASS |
| `commands-staging/*.md` 合计 | 8789 B | 8789 B | = 8789 B，不变 | PASS |
| `references/*.md references/casebook/*.md references/labels/*.md` 合计 | 930145 B | 930079 B | ≤ 930160 B | PASS |

采用 `Path.stat().st_size` 计数；`references/attic.md` 仅计文件大小，未读取内容。总变化为 −66 B，与工单模拟值一致，距上限余 81 B。

实测原始输出：

```text
SKILL.md: 8021 B
commands-staging/*.md: 8789 B
references (three globs): 930079 B
```

可复现统计代码：

```python
from pathlib import Path
p=Path('.')
values={'SKILL.md':(p/'SKILL.md').stat().st_size,'commands-staging/*.md':sum(f.stat().st_size for f in p.glob('commands-staging/*.md')),'references (three globs)':sum(f.stat().st_size for pattern in ('references/*.md','references/casebook/*.md','references/labels/*.md') for f in p.glob(pattern))}
for label,size in values.items(): print(f'{label}: {size} B')
```

## 3. §1.2 守卫原始输出

以下 9 条命令均实际运行，退出码均为 0。执行时仅附加环境变量 `PYTHONDONTWRITEBYTECODE=1`，避免生成 Python 字节码；守卫脚本与参数原样执行。代码块保留原始输出。

### 1. `python3 scripts/tests/docs_lint.py`

退出码：`0`。

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

### 2. `python3 scripts/tests/docs_lint.py --all`

退出码：`0`。

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

### 3. `python3 scripts/tests/casebook_lint.py`

退出码：`0`。

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

### 4. `python3 scripts/tests/changelog_lint.py`

退出码：`0`。

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

### 5. `python3 scripts/tests/test_contract_routes.py`

退出码：`0`。

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

### 6. `python3 scripts/tests/test_sixlens_docs.py`

退出码：`0`。

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

### 7. `python3 scripts/tests/test_g3_docs_guards.py`

退出码：`0`。

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

### 8. `python3 scripts/tests/test_version_consistency.py`

退出码：`0`。

```text
PASS: M-03 version metadata consistent at 9.0.1
```

### 9. `python3 scripts/tests/test_commands_deploy_sync.py`

退出码：`0`。

```text
PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
```

## 4. git diff --stat 与文件范围

`git diff --stat` 实际输出（退出码 0）：

```text
 references/analyze-workflow.md           | 2 +-
 references/data-pipeline-evm-channels.md | 2 +-
 references/data-pipeline-evm-sources.md  | 2 +-
 references/playbook-evidence-wording.md  | 2 +-
 4 files changed, 4 insertions(+), 4 deletions(-)
```

上列已跟踪文件均属于 §0.3 白名单。另按要求新建本报告 `maintenance/repair-20260919-drift-audit2/r2_done.md`；报告未暂存，因此不计入 `git diff --stat`。

`git diff --check`（限定四个施工文件）退出码 0，原始输出为空：

```text

```

## 5. 差异 / 停工点

无工单偏离，无停工点。实际替换与四处指定片段逐字一致，锚唯一且行号一致；基线、三组字节约束及全部守卫均满足。

仅修改白名单内四个文档并新建本报告。未修改 `scripts/`、`commands-staging/`、`CHANGELOG.md` 或两份 manifest；未删除文件，未暂存、commit、push 或部署。全程离线完成。

## 6. 禁读披露

本轮未读取 `~/.codex/` 下任何文件（含 memories），未发生插件启动搜索读取。未直接读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/` 或 `references/attic.md` 的内容；attic.md 仅用文件元数据计大小。`maintenance/` 下只读取本工程目录 `maintenance/repair-20260919-drift-audit2/`。

按工单明示例外原样运行守卫；守卫自身既有的文档遍历属于被测代码行为。
