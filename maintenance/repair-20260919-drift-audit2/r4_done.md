# 施工 R4：完成

按 `maintenance/repair-20260919-drift-audit2/workorder_r4.md` v2 的 §0–§3 完成 D1–D4。仅替换三个白名单文档中的四处整行，并新建本报告；9 项守卫全部通过。

## §0 开工基线与整行锚核验

施工 HEAD：`7cd0d9cb636b68d486b72a072df5e72aa5dc63ea`。以下命令均实际执行，退出码均为 0；空代码块表示原始输出为空。

`git status --short`

```text
```

`git rev-parse HEAD`

```text
7cd0d9cb636b68d486b72a072df5e72aa5dc63ea
```

`git diff --stat e3518db HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md`

```text
```

工作区开工时干净，指定内容范围与 `e3518db` 无差异。四处旧锚均通过实际执行的 `grep -n -F -x -- <整行原文> <目标文件>` 核验，恰好命中一次且行号与工单一致：

| 项目 | 文件 | 要求行号 | 实测行号 | 命中数 |
| --- | --- | ---: | ---: | ---: |
| D1 | `references/research-workflows.md` | 125 | 125 | 1 |
| D2 | `references/labels/README.md` | 8 | 8 | 1 |
| D3 | `references/data-pipeline-robinhood-channels.md` | 33 | 33 | 1 |
| D4 | `references/data-pipeline-robinhood-channels.md` | 30 | 30 | 1 |

替换后再次用 `grep -n -F -x` 核验四处新锚，均为原行号且唯一。将四处新行在内存中还原为旧行后，三个文件的 SHA-256 均与改前一致，确认没有修改其他字节。

## §1 字节实测

通过 `Path.stat().st_size` 统计；references 使用工单指定的三个 glob：`references/*.md references/casebook/*.md references/labels/*.md`。`references/attic.md` 仅计文件大小，未直接读取内容。

| 范围 | 改前（B） | 改后（B） | 变化（B） | 约束 |
| --- | ---: | ---: | ---: | --- |
| `SKILL.md` | 8021 | 8021 | 0 | = 8021，通过 |
| `commands-staging/*.md` 合计 | 8789 | 8789 | 0 | = 8789，通过 |
| references 三组 glob 合计 | 930073 | 929965 | -108 | ≤ 930073，通过 |

## §2 逐条改前 → 改后 diff

### D1 — `references/research-workflows.md:125`

```diff
--- a/references/research-workflows.md
+++ b/references/research-workflows.md
@@ -125 +125 @@
-- **prompt＝本节怀疑者骨架的多结论版**：开头声明"你在只读沙箱，可执行 python3 只读重算（禁写盘），必须实际重算、只审文字的复核无效"；逐条列结论原文（含编号与数字）；附数据文件路径+字段/符号/去重说明；要求输出 JSON 数组 `[{id, verdict(CONFIRMED/WEAKENED/REFUTED), evidence, alternative_explanations, corrections}]` + 一段"结论间互相矛盾/全局缺口"观察；裁决标准同骨架（"理论上可能"不算推翻、REFUTED 须自己重算出的硬证据）。COMMON 资源约束照抄进去（duckdb 四项限制/禁大中间件——read-only 沙箱本身拦写盘，双保险）。
+- **prompt＝本节怀疑者骨架的多结论版**：开头声明"你在只读沙箱，可执行 python3 只读重算（禁写盘），必须实际重算、只审文字的复核无效"；逐条列结论原文（含编号与数字）；附数据文件路径+字段/符号/去重说明；另附一段"结论间互相矛盾/全局缺口"观察；裁决标准同骨架（"理论上可能"不算推翻、REFUTED 须自己重算出的硬证据）。COMMON 资源约束照抄进去（duckdb 四项限制/禁大中间件——read-only 沙箱本身拦写盘，双保险）。
```

### D2 — `references/labels/README.md:8`

```diff
--- a/references/labels/README.md
+++ b/references/labels/README.md
@@ -8 +8 @@
-**接入方式（v4）**：`labels_resolver.py` 共享内核——`label_lookup.py`（人工查询）、EVM `cluster.py`/`analyze_holdings.py`、SOL `replay_edges.py`/`build_evolution.py`（阵营体检）均已默认接入；表缺失/加载失败显式报 **degraded_mode**（"没命中"与"没加载"可区分），分析产物落 `labels_meta`。
+**接入方式（v4）**：`labels_resolver.py` 共享内核——`label_lookup.py`（人工查询）、EVM `cluster.py`/`analyze_holdings.py`、SOL `replay_edges.py`/`build_evolution.py`（阵营体检）均已默认接入；表缺失/加载失败显式报 **degraded_mode**（"没命中"与"没加载"可区分）。
```

### D3 — `references/data-pipeline-robinhood-channels.md:33`

```diff
--- a/references/data-pipeline-robinhood-channels.md
+++ b/references/data-pipeline-robinhood-channels.md
@@ -33 +33 @@
-- `pull_lp_events.py` **用法与输出坑（2026-07-17 实测）**：①与其他脚本不同，**`--from-block N` 必传**（漏传直接 usage 报错、串行链会被短路）；`--pools` 可省略则取 config.pools（CLI 优先）；`--out` 默认 data/lp_events.json；②输出是**格式化 JSON 数组**（非 JSONL，逐行 json.loads 会炸）；③Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（WETH 枚/本币枚），不是 wei——按 wei 再除 1e18 会把费流水全算成 0（本次 Collect 62 笔 4.33 WETH 首轮统计因此归零，重读字段才修正）（DUMBMONEY，07-17）
+- `pull_lp_events.py` **用法与输出坑（2026-07-17 实测）**：①与其他脚本不同，**`--from-block N` 必传**（漏传直接 usage 报错、串行链会被短路）；`--pools` 可省略则取 config.pools（CLI 优先）；`--out` 默认 data/lp_events.json；②输出是**格式化 JSON 数组**（非 JSONL，逐行 json.loads 会炸）；③Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（raw/1e18；仅 18 位币为枚数），不是 wei——按 wei 再除 1e18 会把费流水全算成 0（本次 Collect 62 笔 4.33 WETH 首轮统计因此归零，重读字段才修正）（DUMBMONEY，07-17）
```

### D4 — `references/data-pipeline-robinhood-channels.md:30`

```diff
--- a/references/data-pipeline-robinhood-channels.md
+++ b/references/data-pipeline-robinhood-channels.md
@@ -30 +30 @@
-- `cost_engine.py`：**tx 级 swap 对价重建**——本币和报价币分别使用 config 的 `decimals` / `quote_decimals`，不得再写死 18；逐 tx 配对出每实体成本/已实现盈亏。需 data/weth_pool.jsonl + data/quote_usd_hour.json + data/transit_contracts.json；config 可选 fee_distributor。
+- `cost_engine.py`：**tx 级 swap 对价重建**——本币取 config 的 `decimals or 18`（数值 0 也回退），报价币取 `quote_decimals`（缺失/null 用 18）；逐 tx 配对出每实体成本/已实现盈亏。需 data/weth_pool.jsonl + data/quote_usd_hour.json + data/transit_contracts.json；config 可选 fee_distributor。
```

## §3 守卫原始输出

各脚本均原样运行，未修改脚本或参数。执行环境仅设置 `PYTHONDONTWRITEBYTECODE=1`，避免生成 Python 字节码缓存。以下为各命令完整原始输出，均未截断。

### `python3 scripts/tests/docs_lint.py`

退出码：`0`。

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

### `python3 scripts/tests/docs_lint.py --all`

退出码：`0`。

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

### `python3 scripts/tests/casebook_lint.py`

退出码：`0`。

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

### `python3 scripts/tests/changelog_lint.py`

退出码：`0`。

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

### `python3 scripts/tests/test_contract_routes.py`

退出码：`0`。

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

### `python3 scripts/tests/test_sixlens_docs.py`

退出码：`0`。

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

### `python3 scripts/tests/test_g3_docs_guards.py`

退出码：`0`。

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

### `python3 scripts/tests/test_version_consistency.py`

退出码：`0`。

```text
PASS: M-03 version metadata consistent at 9.0.1
```

### `python3 scripts/tests/test_commands_deploy_sync.py`

退出码：`0`。

```text
PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
```

## §4 git diff --stat

`git diff --stat` 实际输出：

```text
 references/data-pipeline-robinhood-channels.md | 4 ++--
 references/labels/README.md                    | 2 +-
 references/research-workflows.md               | 2 +-
 3 files changed, 4 insertions(+), 4 deletions(-)
```

统计仅含白名单内三个已有文档；本报告为新建未跟踪文件，不会出现在 `git diff --stat` 中。`git diff --check` 实际执行退出码为 0，原始输出为空：

```text
```

## §5 差异与停工点

无工单偏差，无停工点。四处整行替换的 UTF-8 净变化为 -108 B，与 v2 预期一致。没有修改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest 或其他白名单外文件。没有删除文件，没有 commit、push 或部署。

## §6 禁读披露

未读取 `~/.codex/` 下任何文件，未读取 memories；本次没有插件启动搜索。未直接读取 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md` 的内容；`maintenance/` 下仅访问本工程目录。`references/attic.md` 在字节统计中仅调用文件大小查询。工单要求的守卫按其既有行为遍历文档，适用 §0.2 明确允许的例外。全程离线，未发起网络请求。

