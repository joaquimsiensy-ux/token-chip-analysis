# 施工 R4：完成

按 `maintenance/repair-20260916-drift-audit/workorder_r4.md` v1 的 §0–§3 完成 D1–D4。四处均为指定片段的逐字替换；全部指定守卫通过。

## 0. 施工前基线与锚点

工单内容基线：`388eed618c2426e476da30516f508dfe6fe9e782`。施工前及逐字复核时的 HEAD：`aff4d2a95195351256b13e52836b211620480a5b`；VERSION `7.1.1`。

以下为实际执行的 §0.1 命令及原始输出；两项均为空，符合开工条件。

```sh
git status --short
```

原始输出为空，退出码 `0`：

```text

```

```sh
git diff --stat 388eed6 HEAD -- SKILL.md references scripts commands-staging VERSION
```

原始输出为空，退出码 `0`：

```text

```

四个锚先以 `grep -n -F` 核验，均恰好命中一行且行号与工单一致；随后按 UTF-8 字节计数确认每个锚全文仅出现一次。

```sh
grep -n -F '出图后机械比较“图例条数＝传入阵营数”。' references/casebook/supply-accounting.md
grep -n -F '写入对应文件＋CHANGELOG 次版本＋1' references/analyze-workflow.md
grep -n -F 'getLogs 与历史状态一律被拒' references/data-pipeline-evm-channels.md
grep -n -F '按 sig 前 2 字符 256 片' references/data-pipeline-solana-capture.md
```

原始输出，退出码 `0`：

```text
82:- **必做区分检验**：阵营名逐字取自 `standard_charts.py::CAMP_ORDER`，出图后机械比较“图例条数＝传入阵营数”。
198:**默认交付 A5 报告即收工，不进入本阶段**——结论未经用户复核就自动沉淀教训，会把可能错误的经验固化进 skill（2026-07-31 用户定）。会话中发现的候选教训随手记案目录 `retro_notes.md`（只动案目录，不动 skill 文件）。用户复核确认结论没问题、明确下令复盘后，按 `retrospective.md` 执行：五类复盘清单 → AskUserQuestion 确认 → **教训分流决策树**定归宿（gate 代码/casebook/pipeline/workflow/SKILL.md 最后手段）→ 写入对应文件＋CHANGELOG 次版本＋1 → 跑 `scripts/tests/run_all.py` 全 PASS → git commit。质量 4 指标＋成本 3 指标、candidate 分级、逢 0/5 整编——细则全在 retrospective.md。
245:| dataseed 只能做轻查询 | eth_blockNumber / eth_getBlockByNumber / eth_call / eth_getCode（latest 状态）正常，可做时间戳锚点与工厂 getPair；getLogs 与历史状态一律被拒 | （OPN/SIREN，07） |
169:JSON-RPC batch + 跨地址共享 sig 缓存（`--cache-dir`,按 sig 前 2 字符 256 片）+ `--rpc` 端点可换。**mainnet-beta 实测硬墙**：batch 内子请求被**按方法逐个限流**（"Too many requests for a specific RPC call"）——batch 默认 8,429 子请求自动收回重试，绝不能记 decode_fail。公共节点净速度收益约 1.5 倍；**真价值=①缓存**（关联地址重复交易第二址起零请求）**②Helius key 存在即切**。**运行前检测 `~/.config/helius/api-key`**：存在则按下列 Helius 参数跑，缺失则降级公共 RPC（key 注册沿革见 CHANGELOG）；端点国内直连免代理；**实测免费层不支持 batch**（403 码 -32403,单元素数组同拒），账号级上限 **10 RPS**——正解=`--rpc https://mainnet.helius-rpc.com/?api-key=<key> --workers 6 --interval 0.12` 单笔并发贴近上限；archival 10 credits/笔,免费月额≈10 万笔。更高套餐能力未经本管线实测，不得把 50 RPS 或可 batch 当通用口径。
```

| 条目 | 文件 | 行号 | 锚出现次数 | 实测净变化 |
| --- | --- | ---: | ---: | ---: |
| D1 | `references/casebook/supply-accounting.md` | 82 | 1 | +24 B |
| D2 | `references/analyze-workflow.md` | 198 | 1 | +18 B |
| D3 | `references/data-pipeline-evm-channels.md` | 245 | 1 | +24 B |
| D4 | `references/data-pipeline-solana-capture.md` | 169 | 1 | −2 B |

## 1. 逐条改前 → 改后 diff

以下为四个白名单文档的实际 `git diff --unified=0` 输出，分别对应 D2、D1、D3、D4。

```diff
diff --git a/references/analyze-workflow.md b/references/analyze-workflow.md
index b5215a0..a0d6526 100644
--- a/references/analyze-workflow.md
+++ b/references/analyze-workflow.md
@@ -198 +198 @@ A4 finalize 后，用同一 cutoff 快照运行 `holder_distribution_scan.py --s
-**默认交付 A5 报告即收工，不进入本阶段**——结论未经用户复核就自动沉淀教训，会把可能错误的经验固化进 skill（2026-07-31 用户定）。会话中发现的候选教训随手记案目录 `retro_notes.md`（只动案目录，不动 skill 文件）。用户复核确认结论没问题、明确下令复盘后，按 `retrospective.md` 执行：五类复盘清单 → AskUserQuestion 确认 → **教训分流决策树**定归宿（gate 代码/casebook/pipeline/workflow/SKILL.md 最后手段）→ 写入对应文件＋CHANGELOG 次版本＋1 → 跑 `scripts/tests/run_all.py` 全 PASS → git commit。质量 4 指标＋成本 3 指标、candidate 分级、逢 0/5 整编——细则全在 retrospective.md。
+**默认交付 A5 报告即收工，不进入本阶段**——结论未经用户复核就自动沉淀教训，会把可能错误的经验固化进 skill（2026-07-31 用户定）。会话中发现的候选教训随手记案目录 `retro_notes.md`（只动案目录，不动 skill 文件）。用户复核确认结论没问题、明确下令复盘后，按 `retrospective.md` 执行：五类复盘清单 → AskUserQuestion 确认 → **教训分流决策树**定归宿（gate 代码/casebook/pipeline/workflow/SKILL.md 最后手段）→ 写入对应文件＋CHANGELOG（版本号见 retrospective） → 跑 `scripts/tests/run_all.py` 全 PASS → git commit。质量 4 指标＋成本 3 指标、candidate 分级、逢 0/5 整编——细则全在 retrospective.md。
diff --git a/references/casebook/supply-accounting.md b/references/casebook/supply-accounting.md
index 1198ce4..abe7a8f 100644
--- a/references/casebook/supply-accounting.md
+++ b/references/casebook/supply-accounting.md
@@ -82 +82 @@
-- **必做区分检验**：阵营名逐字取自 `standard_charts.py::CAMP_ORDER`，出图后机械比较“图例条数＝传入阵营数”。
+- **必做区分检验**：阵营名逐字取自 `standard_charts.py::CAMP_ORDER`，出图后核对 `fig1_legend_receipt.json`：实绘＋豁免键＝传入阵营键。
diff --git a/references/data-pipeline-evm-channels.md b/references/data-pipeline-evm-channels.md
index efd981b..3a2f7eb 100644
--- a/references/data-pipeline-evm-channels.md
+++ b/references/data-pipeline-evm-channels.md
@@ -245 +245 @@ size 与 SHA-256；全部通过后才原子将 v2/v3/pre-schema done 升为
-| dataseed 只能做轻查询 | eth_blockNumber / eth_getBlockByNumber / eth_call / eth_getCode（latest 状态）正常，可做时间戳锚点与工厂 getPair；getLogs 与历史状态一律被拒 | （OPN/SIREN，07） |
+| dataseed 只能做轻查询 | eth_blockNumber / eth_getBlockByNumber / eth_call / eth_getCode（latest 状态）正常，可做时间戳锚点与工厂 getPair；getLogs 被拒；历史 state 仅浅窗口可查（§3.6） | （OPN/SIREN，07） |
diff --git a/references/data-pipeline-solana-capture.md b/references/data-pipeline-solana-capture.md
index ae39f91..905f484 100644
--- a/references/data-pipeline-solana-capture.md
+++ b/references/data-pipeline-solana-capture.md
@@ -169 +169 @@ SQD 不落盘签名不等于没有数据集内交易身份：请求与响应已
-JSON-RPC batch + 跨地址共享 sig 缓存（`--cache-dir`,按 sig 前 2 字符 256 片）+ `--rpc` 端点可换。**mainnet-beta 实测硬墙**：batch 内子请求被**按方法逐个限流**（"Too many requests for a specific RPC call"）——batch 默认 8,429 子请求自动收回重试，绝不能记 decode_fail。公共节点净速度收益约 1.5 倍；**真价值=①缓存**（关联地址重复交易第二址起零请求）**②Helius key 存在即切**。**运行前检测 `~/.config/helius/api-key`**：存在则按下列 Helius 参数跑，缺失则降级公共 RPC（key 注册沿革见 CHANGELOG）；端点国内直连免代理；**实测免费层不支持 batch**（403 码 -32403,单元素数组同拒），账号级上限 **10 RPS**——正解=`--rpc https://mainnet.helius-rpc.com/?api-key=<key> --workers 6 --interval 0.12` 单笔并发贴近上限；archival 10 credits/笔,免费月额≈10 万笔。更高套餐能力未经本管线实测，不得把 50 RPS 或可 batch 当通用口径。
+JSON-RPC batch + 跨地址共享 sig 缓存（`--cache-dir`,按 sig 前 2 字符分片）+ `--rpc` 端点可换。**mainnet-beta 实测硬墙**：batch 内子请求被**按方法逐个限流**（"Too many requests for a specific RPC call"）——batch 默认 8,429 子请求自动收回重试，绝不能记 decode_fail。公共节点净速度收益约 1.5 倍；**真价值=①缓存**（关联地址重复交易第二址起零请求）**②Helius key 存在即切**。**运行前检测 `~/.config/helius/api-key`**：存在则按下列 Helius 参数跑，缺失则降级公共 RPC（key 注册沿革见 CHANGELOG）；端点国内直连免代理；**实测免费层不支持 batch**（403 码 -32403,单元素数组同拒），账号级上限 **10 RPS**——正解=`--rpc https://mainnet.helius-rpc.com/?api-key=<key> --workers 6 --interval 0.12` 单笔并发贴近上限；archival 10 credits/笔,免费月额≈10 万笔。更高套餐能力未经本管线实测，不得把 50 RPS 或可 batch 当通用口径。
```

## 2. §1.1 字节实测

统计使用文件大小元数据 `Path.stat().st_size` 求和，不打开文件内容；`references/attic.md` 只计大小。

| 统计范围 | 施工前 | 施工后 | 变化 | 工单要求 |
| --- | ---: | ---: | ---: | --- |
| `SKILL.md` | 8021 B | 8021 B | 0 B | = 8021 B |
| references 三组 glob | 929905 B | 929969 B | +64 B | ≤ 929969 B |
| `commands-staging/*.md` | 8798 B | 8798 B | 0 B | = 8798 B |

references 三组 glob 为 `references/*.md`、`references/casebook/*.md`、`references/labels/*.md`。四处实测合计 `+24 +18 +24 −2 = +64 B`，与工单一致。

逐字复核以内容基线中四个文件的原始字节各替换一次指定锚生成期望值，并与工作树完整文件逐字节比较；同时核对行号、锚次数、文件变化量、HEAD 和索引。原始输出（退出码 `0`）：

```text
PASS: D1 references/casebook/supply-accounting.md:82; exact replacement only; byte_delta=+24
PASS: D2 references/analyze-workflow.md:198; exact replacement only; byte_delta=+18
PASS: D3 references/data-pipeline-evm-channels.md:245; exact replacement only; byte_delta=+24
PASS: D4 references/data-pipeline-solana-capture.md:169; exact replacement only; byte_delta=-2
PASS: changed tracked files match the four-document whitelist; index unchanged
SKILL.md: 8021 B
references 三组 glob: 929969 B
commands-staging/*.md: 8798 B
```

## 3. §1.2 守卫原始输出

离线运行，守卫代码和参数保持原样。执行环境设置 `PYTHONDONTWRITEBYTECODE=1`，避免生成 Python 字节码缓存。共七条命令、八次脚本执行，退出码均为 `0`。

```sh
python3 scripts/tests/docs_lint.py && python3 scripts/tests/docs_lint.py --all
```

原始输出，退出码 `0`：

```text
PASS: 45 个文档，引用无断链、粗体配对完整
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

```sh
python3 scripts/tests/casebook_lint.py
```

原始输出，退出码 `0`：

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

```sh
python3 scripts/tests/changelog_lint.py
```

原始输出，退出码 `0`：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 73 条 + 归档 139 条
```

```sh
python3 scripts/tests/test_contract_routes.py
```

原始输出，退出码 `0`：

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

```sh
python3 scripts/tests/test_sixlens_docs.py
```

原始输出，退出码 `0`：

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

```sh
python3 scripts/tests/test_g3_docs_guards.py
```

原始输出，退出码 `0`：

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

```sh
python3 scripts/tests/test_version_consistency.py
```

原始输出，退出码 `0`：

```text
PASS: M-03 version metadata consistent at 7.1.1
```

## 4. git diff --stat 与范围

```sh
git diff --stat
```

原始输出，退出码 `0`：

```text
 references/analyze-workflow.md             | 2 +-
 references/casebook/supply-accounting.md   | 2 +-
 references/data-pipeline-evm-channels.md   | 2 +-
 references/data-pipeline-solana-capture.md | 2 +-
 4 files changed, 4 insertions(+), 4 deletions(-)
```

上述 `git diff --stat` 仅含四个白名单文档。另新建白名单报告 `maintenance/repair-20260916-drift-audit/r4_done.md`；该文件未暂存，因此不出现在 `git diff --stat` 中。

```sh
git diff --check
```

原始输出为空，退出码 `0`：

```text

```

## 5. 差异与停工点

无偏离工单的修改，无停工点，未出现 needle 冲突。仅四处指定片段与本报告发生写入；未修改 `scripts/` 或 `scripts/tests/contract_manifest.json`，未 commit、push 或部署 `~/.claude/commands/`。未新增测试，也未执行工单范围外的全量测试。

工单列出的 `scripts/solana/decode_txs_v2.py:8` 文头注释留在原状态，未扩大本次施工范围。

## 6. 禁读披露

会话启动上下文自动提供了历史记忆摘要，开工时已向用户披露一次；本次未主动读取 `~/.codex/` 下任何文件，未用历史摘要替代工单或当前证据。

未主动读取本仓库 `archive/`、`blind-reviews/`、`.staging_*` 或 `references/attic.md` 的内容。字节统计对 attic.md 仅调用文件大小元数据；指定守卫运行中自行遍历文档的既有行为按工单 §0.2 的明确例外执行。全程未联网。


---
## 附：调度方验收（Fable）

四处新文本各 grep 命中 1、旧文本 0；亲跑九项守卫（docs_lint 含 --all、casebook_lint、changelog_lint、test_version_consistency、test_g3_docs_guards、test_sixlens_docs、test_commands_deploy_sync、test_contract_routes）全 PASS；`git diff --stat` 仅四个白名单文件；references 实测 929969 B = 基线 929905 + 64，与工单 §1.1 一致。
