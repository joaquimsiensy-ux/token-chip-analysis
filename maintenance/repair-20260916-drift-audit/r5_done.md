# 施工 R5：完成

按 `maintenance/repair-20260916-drift-audit/workorder_r5.md` v1 执行。D1、D2 已完成；8 次守卫检查全部通过；仅修改两份白名单文档的指定片段，并新建本报告。

## 1. §0.1 内容基线与施工前校验

内容基线：`0e031559f13a4b11608fd94025a447dd645012cc`。施工时 HEAD：`9781d9c34d7c29a3e155ed26baaa3a0278752b86`；VERSION：`7.1.1`。以下两条命令已实际运行，原始输出均为空，退出码均为 0；当前 HEAD 与内容基线之间在指定范围内没有差异。

```text
$ git status --short
```

退出码：0。

```text
$ git diff --stat 0e03155 HEAD -- SKILL.md references scripts commands-staging VERSION
```

退出码：0。

锚点先用 `grep -n -F` 核验，均恰好一处，行号与工单一致。原始输出：

```text
$ grep -n -F 'RobinHoodSettler 0xe72688f7d25d73a2a5e2a4e40d1f0b6b2c5c1e05' references/data-pipeline-robinhood-traps.md
62:17. **平台核心设施地址（Index 分析核验 2026-07-18，已入 address-book）**：`RobinHoodSettler 0xe72688f7d25d73a2a5e2a4e40d1f0b6b2c5c1e05`=App 交易结算器，本案 756 万 transfers、transit_ratio=1.0——**超高换手盘（毛成交/供应 8.6 倍）的毛量主源，必剔除**，否则散户口径被虚高的往返流量污染；`DexAggregatorCore 0x09ad820aac5779683b481c4674208a4e1b024afa`、公共 bot relayer `0x56c262027e0de4aea31d2489529cb25d23e58a8b`（几十种 meme 币 + permit2 multicall）同理，作 gas funder / 中转 funder 时**不可作私有聚类边**（本案曾据中转 funder 0x2ed8 误连 10 条弱边，复核剔除）。
```

退出码：0。

```text
$ grep -n -F '，线超 8 条时可将持仓较小的实体合并成一条（合并了谁在图注写明）' references/report-template.md
162:| 2 | 庄级实体持仓变动 vs 价格（双轴） | `plot_whale_vs_price` | **一、TL;DR 顶部（图1 之后）** | 左轴=各实体占比线（标签制命名，线色按前缀语义色），右轴=价格 USD **线性刻度**（蓝；2026-07-15 用户定，贴近 K 线直觉，勿用对数，图注别再写"对数"）；标签实体各画一线，线超 8 条时可将持仓较小的实体合并成一条（合并了谁在图注写明）；一眼看出建仓后是否平线、拉升期是否出货 |
```

退出码：0。

替换前检查：

```text
references globs: references/*.md, references/labels/*.md, references/casebook/*.md
SKILL.md: 8021 B
commands-staging/*.md: 8798 B
references_three_globs: 929969 B
references/data-pipeline-robinhood-traps.md:62: unique anchor PASS; delta -18 B; authority contracts 0; needle collision NONE
references/report-template.md:162: unique anchor PASS; delta -63 B; authority contracts 8; needle collision NONE
Pre-edit checks: PASS
```

## 2. 逐条改前 → 改后 diff

- D1：第 62 行删除 RobinHoodSettler 重复硬编码地址，改为“址见 address-book”；同行另外两处地址保持原样。净减 18 B。
- D2：第 162 行将“线超 8 条时可合并”的许可改为“本版不支持合并线”。净减 63 B。

以下为实际 `git diff --no-ext-diff --unified=0 -- references/data-pipeline-robinhood-traps.md references/report-template.md` 输出：

```diff
diff --git a/references/data-pipeline-robinhood-traps.md b/references/data-pipeline-robinhood-traps.md
index 57e97d3..9269249 100644
--- a/references/data-pipeline-robinhood-traps.md
+++ b/references/data-pipeline-robinhood-traps.md
@@ -62 +62 @@
-17. **平台核心设施地址（Index 分析核验 2026-07-18，已入 address-book）**：`RobinHoodSettler 0xe72688f7d25d73a2a5e2a4e40d1f0b6b2c5c1e05`=App 交易结算器，本案 756 万 transfers、transit_ratio=1.0——**超高换手盘（毛成交/供应 8.6 倍）的毛量主源，必剔除**，否则散户口径被虚高的往返流量污染；`DexAggregatorCore 0x09ad820aac5779683b481c4674208a4e1b024afa`、公共 bot relayer `0x56c262027e0de4aea31d2489529cb25d23e58a8b`（几十种 meme 币 + permit2 multicall）同理，作 gas funder / 中转 funder 时**不可作私有聚类边**（本案曾据中转 funder 0x2ed8 误连 10 条弱边，复核剔除）。
+17. **平台核心设施地址（Index 分析核验 2026-07-18，已入 address-book）**：`RobinHoodSettler`（址见 address-book）=App 交易结算器，本案 756 万 transfers、transit_ratio=1.0——**超高换手盘（毛成交/供应 8.6 倍）的毛量主源，必剔除**，否则散户口径被虚高的往返流量污染；`DexAggregatorCore 0x09ad820aac5779683b481c4674208a4e1b024afa`、公共 bot relayer `0x56c262027e0de4aea31d2489529cb25d23e58a8b`（几十种 meme 币 + permit2 multicall）同理，作 gas funder / 中转 funder 时**不可作私有聚类边**（本案曾据中转 funder 0x2ed8 误连 10 条弱边，复核剔除）。
diff --git a/references/report-template.md b/references/report-template.md
index 633cdc4..a585a19 100644
--- a/references/report-template.md
+++ b/references/report-template.md
@@ -162 +162 @@ python3 scripts/report/build_html.py --mode analysis-new --md 报告.md --out 
-| 2 | 庄级实体持仓变动 vs 价格（双轴） | `plot_whale_vs_price` | **一、TL;DR 顶部（图1 之后）** | 左轴=各实体占比线（标签制命名，线色按前缀语义色），右轴=价格 USD **线性刻度**（蓝；2026-07-15 用户定，贴近 K 线直觉，勿用对数，图注别再写"对数"）；标签实体各画一线，线超 8 条时可将持仓较小的实体合并成一条（合并了谁在图注写明）；一眼看出建仓后是否平线、拉升期是否出货 |
+| 2 | 庄级实体持仓变动 vs 价格（双轴） | `plot_whale_vs_price` | **一、TL;DR 顶部（图1 之后）** | 左轴=各实体占比线（标签制命名，线色按前缀语义色），右轴=价格 USD **线性刻度**（蓝；2026-07-15 用户定，贴近 K 线直觉，勿用对数，图注别再写"对数"）；标签实体各画一线（本版不支持合并线）；一眼看出建仓后是否平线、拉升期是否出货 |
```

两份文件均与内容基线逐字节比较，确认只有上述单次替换；新锚点行号仍为 62、162。所涉 authority needle 未发生碰撞，未修改契约注册表。

## 3. §1.1 字节实测

| 范围 | 施工前（B） | 施工后（B） | 变化（B） | 约束 |
| --- | ---: | ---: | ---: | --- |
| SKILL.md | 8021 | 8021 | 0 | 等于 8021 |
| commands-staging/*.md | 8798 | 8798 | 0 | 等于 8798 |
| references 三组 glob 合计 | 929969 | 929888 | -81 | ≤ 929888 |

三组 glob 为 `references/*.md`、`references/labels/*.md`、`references/casebook/*.md`。大小全部通过文件 stat 统计；`references/attic.md` 仅计大小，未主动读取其内容。

```text
SKILL.md: 8021 B
commands-staging/*.md: 8798 B
references_three_globs: 929888 B
references/data-pipeline-robinhood-traps.md:62: 20580 -> 20562 B (-18 B); exact replacement PASS
references/report-template.md:162: 42474 -> 42411 B (-63 B); exact replacement PASS
Exact scope and byte checks: PASS
```

字节统计复现命令：

```sh
python3 - <<'PY'
from pathlib import Path
root = Path('.')
def total(pattern):
    return sum(p.stat().st_size for p in root.glob(pattern) if p.is_file())
print('SKILL.md:', Path('SKILL.md').stat().st_size, 'B')
print('commands-staging/*.md:', total('commands-staging/*.md'), 'B')
print('references_three_globs:', sum(total(p) for p in [
    'references/*.md', 'references/labels/*.md', 'references/casebook/*.md'
]), 'B')
PY
```

## 4. §1.2 守卫原始输出

全部使用仓库原有脚本离线执行，没有更改脚本或测试；`PYTHONDONTWRITEBYTECODE=1` 用于避免生成字节码缓存。下列命令均已实际运行，完整原始输出如下。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py
PASS: 45 个文档，引用无断链、粗体配对完整
```

退出码：0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py --all
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

退出码：0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/casebook_lint.py
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

退出码：0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/changelog_lint.py
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 73 条 + 归档 139 条
```

退出码：0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_contract_routes.py
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

退出码：0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_sixlens_docs.py
PASS: 六视角批⑤大小口径与 archive 路由
```

退出码：0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_g3_docs_guards.py
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

退出码：0。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_version_consistency.py
PASS: M-03 version metadata consistent at 7.1.1
```

退出码：0。

## 5. git diff --stat 与白名单

```text
$ git diff --stat
 references/data-pipeline-robinhood-traps.md | 2 +-
 references/report-template.md               | 2 +-
 2 files changed, 2 insertions(+), 2 deletions(-)
```

退出码：0。

本报告为新建、未跟踪文件，原生 `git diff --stat` 不显示它；未为改变统计输出而修改 Git 索引。报告落盘后，最终检查确认工作树仅有两份已修改文档及本报告，均在 §0.3 白名单内。

报告落盘后复跑 `docs_lint.py` 和 `docs_lint.py --all`，原始输出与 §4 所列一致，退出码均为 0。最终范围检查原始输出：

```text
 M references/data-pipeline-robinhood-traps.md
 M references/report-template.md
?? maintenance/repair-20260916-drift-audit/r5_done.md
Final HEAD, baseline, whitelist, report readback and diff checks: PASS
```

```text
$ git diff --check
```

退出码：0。

## 6. 差异与停工点

施工差异：无。停工点：无。D1/D2 精确净减 -18/-63 B，与工单一致；没有 needle 碰撞。定位守卫时曾检索不存在的 `scripts/docs_lint.py`（该次 `rg` 退出码 2），随后定位至 `scripts/tests/docs_lint.py`；此为路径定位失误，未作为守卫验收结果使用，上列 8 次正式守卫均退出 0。

没有 commit、push 或命令部署；没有修改 scripts、contract_manifest.json 或 CSV。工单所列 standard_charts.py 文档串待决事项保持原状。

## 7. 禁读披露

会话启动时已自动提供记忆摘要，已在首次沟通中披露；本次施工未主动读取 `~/.codex/` 下的任何文件，未启动插件搜索或读取记忆文件。

未主动读取本仓库 `archive/`、`blind-reviews/`、`.staging_*` 或 `references/attic.md` 内容。`attic.md` 仅以 stat 计入大小。守卫脚本按工单授权原样运行，其既有文档遍历属于 §0.2/§1.2 明确允许的行为。全程离线。

---
## 附：调度方验收（Fable）

两处新文本各 grep 命中 1、旧文本 0；亲跑九项守卫全 PASS；`git diff --stat` 仅两个白名单文件；references 实测 929888 B = 基线 929969 − 81，与工单 §1.1 一致。施工期间调度方提交过一次仅含 maintenance/ 的 commit（9781d9c），codex 已在报告中记录施工时 HEAD，限定路径基线 diff 为空。
