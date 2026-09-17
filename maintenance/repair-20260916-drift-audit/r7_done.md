# 施工 R7：完成

按 `workorder_r7.md` v1 的 §0–§3 完成 D1/D2/D3。三处修改均逐字符合工单；两处 Python 仅改 docstring 文字，零逻辑改动。§1.2 十条命令及两次 `ast.parse` 全部退出码 0。

## 0. 施工前置核验

内容基线：`33548fc5e257014a6f30533094a911a50fe25972`；开工 HEAD：`a4571049ca540abb3fca4c8e84db3e484ba5bb10`；VERSION：`7.1.2`。以下 §0.1 两条命令实际运行，均为空输出，满足开工条件。

命令：

```sh
git status --short
```

原始输出（退出码 0；空输出）：

```text
```

命令：

```sh
git diff --stat 33548fc HEAD -- SKILL.md references scripts commands-staging VERSION
```

原始输出（退出码 0；空输出）：

```text
```

三处锚点均用工单要求的 `grep -n -F` 实测；每条只输出一行，且另以原文 `count` 确认每个锚恰好出现一次。

命令：

```sh
grep -n -F '来源：meow 案 2026-07-15）。' references/analyze-workflow.md
```

原始输出（退出码 0）：

```text
158:数据先验结构再分析（榜单唯一性断言、多档抽查），批量脚本先 2 个样本验证编解码再放量、绝不吞异常。**份额阈值一律整数运算**（`TOTAL//100`，浮点比较会把"恰好整数枚"大户判漏——那本身还是橱窗仓指纹，漏它双重损失；来源：meow 案 2026-07-15）。
```

命令：

```sh
grep -n -F '按 sig 前 2 字符分 256 片' scripts/solana/decode_txs_v2.py
```

原始输出（退出码 0）：

```text
8:  2. 跨地址共享 sig 结果缓存(--cache-dir,按 sig 前 2 字符分 256 片)——庄家关联地址间
```

命令：

```sh
grep -n -F '标签实体各画一线；线超 8 条时可将持仓较小的实体合并成一条避免花屏。' scripts/report/standard_charts.py
```

原始输出（退出码 0）：

```text
283:                  标签实体各画一线；线超 8 条时可将持仓较小的实体合并成一条避免花屏。
```

## 1. 逐条改前 → 改后 diff

### D1：`references/analyze-workflow.md:158`

按裁决 B 登记 `wave_scan.py` 浮点阈值为已知例外，净增 237 B。

```diff
diff --git a/references/analyze-workflow.md b/references/analyze-workflow.md
index a0d6526..dd3630c 100644
--- a/references/analyze-workflow.md
+++ b/references/analyze-workflow.md
@@ -155,7 +155,7 @@
 - **现有轻量信号**：阵营重放标记单日阵营变动 ≥10pp 的日期，作为峰值逐笔触发日之一，但不承担归因义务。
 - **报告义务**：无法归因的骤变和上述覆盖边界必须写入报告局限性，不得把未报警表述为不存在异常。
 
-数据先验结构再分析（榜单唯一性断言、多档抽查），批量脚本先 2 个样本验证编解码再放量、绝不吞异常。**份额阈值一律整数运算**（`TOTAL//100`，浮点比较会把"恰好整数枚"大户判漏——那本身还是橱窗仓指纹，漏它双重损失；来源：meow 案 2026-07-15）。
+数据先验结构再分析（榜单唯一性断言、多档抽查），批量脚本先 2 个样本验证编解码再放量、绝不吞异常。**份额阈值一律整数运算**（`TOTAL//100`，浮点比较会把"恰好整数枚"大户判漏——那本身还是橱窗仓指纹，漏它双重损失；来源：meow 案 2026-07-15）。已知例外：`wave_scan.py` 必裁决四标记的 0.1%/0.05% 线仍用浮点，恰好等于阈值的地址可能丢标记（用户 2026-09-16 裁决暂不改码，见 maintenance/repair-20260916-drift-audit/code_change_pending.md）。
 
 ## A4 对抗复核（必做）
 
```

### D2：`scripts/solana/decode_txs_v2.py:8`

删除文头说明中的固定分片数 `256`，净减 5 B。

```diff
diff --git a/scripts/solana/decode_txs_v2.py b/scripts/solana/decode_txs_v2.py
index cf47ece..43f8eb0 100644
--- a/scripts/solana/decode_txs_v2.py
+++ b/scripts/solana/decode_txs_v2.py
@@ -5,7 +5,7 @@
 相对 v1:
   1. getTransaction 改 JSON-RPC batch(公共 mainnet-beta 默认 8 笔/POST)——单笔串行 0.75s 间隔≈1.3 笔/s,
      批量后同样限速礼貌下 10-20 倍
-  2. 跨地址共享 sig 结果缓存(--cache-dir,按 sig 前 2 字符分 256 片)——庄家关联地址间
+  2. 跨地址共享 sig 结果缓存(--cache-dir,按 sig 前 2 字符分片)——庄家关联地址间
      重复交易极多,第二个地址起大量命中零请求
   3. --rpc 可换端点:默认 api.mainnet-beta(须 --proxy);Helius 免费层免代理但不支持
      JSON-RPC batch，须改用 --workers 单笔并发并遵守账号级 10 RPS
```

### D3：`scripts/report/standard_charts.py:283`

将 docstring 改为本版不支持合并线，净减 42 B。

```diff
diff --git a/scripts/report/standard_charts.py b/scripts/report/standard_charts.py
index f7c86ed..e978179 100644
--- a/scripts/report/standard_charts.py
+++ b/scripts/report/standard_charts.py
@@ -280,7 +280,7 @@ def plot_whale_vs_price(whale_series, price_series, out_png, token):
                    {"label": "大庄#1", "ts": [...], "pct": [...]}, ...]
                   label 用标签制（项目方/大庄#N/小庄#N/离场庄#N），
                   pct=占总供应量百分数；线色按前缀自动取语义色。
-                  标签实体各画一线；线超 8 条时可将持仓较小的实体合并成一条避免花屏。
+                  标签实体各画一线（本版不支持合并线）。
     price_series: {"ts": [...], "usd": [...]}
     """
     setup()
```

## 2. §1.1 字节实测

| 范围 | 改前 B | 改后 B | 差值 B | 工单要求 |
| --- | ---: | ---: | ---: | --- |
| `SKILL.md` | 8021 | 8021 | 0 | = 8021 |
| `commands-staging/*.md` | 8798 | 8798 | 0 | = 8798 |
| references 三组 glob 合计 | 929833 | 930070 | +237 | ≤ 930070 |
| `scripts/solana/decode_txs_v2.py` | 16952 | 16947 | -5 | = 16947 |
| `scripts/report/standard_charts.py` | 23051 | 23009 | -42 | = 23009 |

三组 glob 为 `references/*.md`、`references/labels/*.md`、`references/casebook/*.md`，按匹配文件的 `stat().st_size` 求和；该口径见 `r6_done.md:49`。`references/attic.md` 仅计大小，未主动读取内容。D1 的 +237 B 为工单明确登记的已知例外，实际总量恰为上限。

改前字节与锚点断言原始输出（退出码 0）：

```text
references globs: references/*.md, references/labels/*.md, references/casebook/*.md
SKILL.md: 8021 B
commands-staging/*.md: 8798 B
references_three_globs: 929833 B
scripts/solana/decode_txs_v2.py: 16952 B
scripts/report/standard_charts.py: 23051 B
references/analyze-workflow.md:158: unique anchor PASS; planned delta 237 B
scripts/solana/decode_txs_v2.py:8: unique anchor PASS; planned delta -5 B
scripts/report/standard_charts.py:283: unique anchor PASS; planned delta -42 B
preflight bytes and exact replacements: PASS
```

改后字节、逐字替换、逻辑与受保护文件断言原始输出（退出码 0）：

```text
references/analyze-workflow.md:158: exact replacement PASS; delta 237 B
scripts/solana/decode_txs_v2.py:8: exact replacement PASS; delta -5 B
scripts/solana/decode_txs_v2.py: AST excluding docstrings unchanged PASS
scripts/report/standard_charts.py:283: exact replacement PASS; delta -42 B
scripts/report/standard_charts.py: AST excluding docstrings unchanged PASS
SKILL.md: 8021 B
commands-staging/*.md: 8798 B
references_three_globs: 930070 B
scripts/solana/decode_txs_v2.py: 16947 B
scripts/report/standard_charts.py: 23009 B
SKILL.md: original SHA-256 unchanged PASS
VERSION: original SHA-256 unchanged PASS
scripts/tests/contract_manifest.json: original SHA-256 unchanged PASS
scripts/tests/invariant_manifest.json: original SHA-256 unchanged PASS
section 1.1 bytes and section 0.3 scope: PASS
```

上述比对使用各白名单文件的 `git show HEAD:<path>` 原文，确认当前文件恰等于指定锚的单次替换，且只在指定行发生变化；去除 docstring 后的两份 Python AST 均与改前相同。

## 3. §1.2 守卫原始输出

以下十条命令均在仓库根目录离线执行既有脚本，未修改守卫。`PYTHONDONTWRITEBYTECODE=1` 用于避免生成字节码缓存；没有省略、改写或隐藏测试输出。

### 1. `docs_lint`

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py
```

原始输出（退出码 0）：

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

### 2. `docs_lint_all`

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py --all
```

原始输出（退出码 0）：

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

### 3. `casebook_lint`

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/casebook_lint.py
```

原始输出（退出码 0）：

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

### 4. `changelog_lint`

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/changelog_lint.py
```

原始输出（退出码 0）：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 74 条 + 归档 139 条
```

### 5. `contract_routes`

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_contract_routes.py
```

原始输出（退出码 0）：

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

### 6. `sixlens_docs`

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_sixlens_docs.py
```

原始输出（退出码 0）：

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

### 7. `g3_docs_guards`

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_g3_docs_guards.py
```

原始输出（退出码 0）：

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

### 8. `version_consistency`

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_version_consistency.py
```

原始输出（退出码 0）：

```text
PASS: M-03 version metadata consistent at 7.1.2
```

### 9. `figures_from_facts`

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_figures_from_facts.py
```

原始输出（退出码 0）：

```text
/Users/uravvv/.matplotlib is not a writable directory
Matplotlib created a temporary cache directory at /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/matplotlib-qi2j3fsg because there was an issue with the default path ({configdir}); it is highly recommended to set the MPLCONFIGDIR environment variable to a writable directory, in particular to speed up the import of Matplotlib and to better support multiprocessing.
Matplotlib is building the font cache; this may take a moment.
findfont: Failed to find font weight normal, now using 300.
findfont: Failed to find font weight normal, now using 300.
findfont: Failed to find font weight normal, now using 300.
ok series_format=sol-rows: rendered=['大庄', '散户'], excluded=[{'key': '锁仓/销毁', 'reason': 'non_stacked_metric'}]
ok series_format=evm-dict: rendered=['大庄', '散户', '锁仓/销毁'], excluded=[]
ok 两消费方拒绝 rendered: ["图 1 legend rendered_camps 与当前 state 重算不一致（期望 ['大庄', '散户']）"]; ["图 1 legend 实绘集合与发布闸从 state 重算不一致（期望 ['大庄', '散户']）"]
ok 两消费方拒绝 missing-exemption: ["图 1 legend excluded_series 与当前 state 重算不一致（期望 [{'key': '锁仓/销毁', 'reason': 'non_stacked_metric'}]）"]; ["图 1 legend 排除键与发布闸从 state 重算不一致（期望 [{'key': '锁仓/销毁', 'reason': 'non_stacked_metric'}]）"]
ok 两消费方拒绝 overlay: ["图 1 legend overlay[0] 含当前 state 非实绘 camp: ['锁仓/销毁']"]; ["图 1 legend overlay[0] 含 state 非实绘 camp: ['锁仓/销毁']"]
ok fig1 拒绝豁免桶 nan: rc=1
ok fig1 拒绝豁免桶 inf: rc=1
ok fig1 拒绝豁免桶 non-numeric: rc=1
PASS: figures_from_facts fig1白名单/legacy销毁键/legend receipt/burn豁免/overlay组成/价格绑定/flow宏同源/check终值对账全过
```

### 10. `review_solana_integrity`

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_review_solana_integrity.py
```

原始输出（退出码 0）：

```text
[fast-decode] total=1 done=0 todo=1
[fast-decode] DONE ok=1 fail=0 耗时0.0min
[fast-decode] total=1 done=0 todo=1
[fast-decode] DONE ok=0 fail=1 耗时0.0min
[decode2] total=1 done=0 cache_hit=0 todo=1
[decode2] DONE ok=0 fail=1 cache_hit=0 耗时0.0min
PASS: B-06/B-07/B-08 + P1-03 v1/v2 decode retry, identity and failure receipts
```

## 4. 两处 ast.parse 与 diff 检查

命令：

```sh
python3 -c "import ast; p='scripts/solana/decode_txs_v2.py'; ast.parse(open(p).read()); print(p + ': ast.parse PASS')"
```

原始输出（退出码 0）：

```text
scripts/solana/decode_txs_v2.py: ast.parse PASS
```

命令：

```sh
python3 -c "import ast; p='scripts/report/standard_charts.py'; ast.parse(open(p).read()); print(p + ': ast.parse PASS')"
```

原始输出（退出码 0）：

```text
scripts/report/standard_charts.py: ast.parse PASS
```

命令：

```sh
git diff --check
```

原始输出（退出码 0；空输出）：

```text
```

## 5. git diff --stat 与修改范围

命令：

```sh
git diff --stat
```

原始输出（退出码 0）：

```text
 references/analyze-workflow.md    | 2 +-
 scripts/report/standard_charts.py | 2 +-
 scripts/solana/decode_txs_v2.py   | 2 +-
 3 files changed, 3 insertions(+), 3 deletions(-)
```

以上 `git diff --stat` 仅含三个已跟踪的白名单文件。另新建白名单报告 `maintenance/repair-20260916-drift-audit/r7_done.md`；报告未跟踪，故不计入该命令的统计。最终工作树状态在本报告末尾记录。

## 6. 差异与停工点

无施工偏差，未触发停工；三处锚点唯一且行号匹配，未撞 needle，所有要求的守卫均通过。未 commit、push 或部署 `~/.claude/commands/`。未修改 `contract_manifest.json`、`invariant_manifest.json`；两份清单、`SKILL.md`、`VERSION` 的 SHA-256 与开工记录一致。

图表测试实际出现默认 Matplotlib 缓存目录不可写、临时缓存目录及字体回退提示，随后测试完成并返回 0；原始提示已完整保留在第 3 节。未将这些提示隐去，也未据此改动测试或额外重跑。

## 7. 禁读披露

会话初始化时系统已自动注入历史记忆摘要，首次施工说明已如实披露。施工期间未主动读取 `~/.codex/` 下任何文件，也未主动读取本仓库 `archive/`、`blind-reviews/`、`.staging_*` 或 `references/attic.md` 的内容；attic 仅按 §1.1 统计大小。守卫脚本原样运行时的文档遍历属于工单明确允许的被测代码既有行为。

## 8. 最终工作树核验

命令：

```sh
git status --porcelain=v1 --untracked-files=all
```

原始输出（退出码 0）：

```text
 M references/analyze-workflow.md
 M scripts/report/standard_charts.py
 M scripts/solana/decode_txs_v2.py
?? maintenance/repair-20260916-drift-audit/r7_done.md
```

最终状态仅含 §0.3 四个白名单路径：三个已跟踪文件修改、一个新建报告。全部测试运行后的源码 diff 与测试前逐字相同，`git diff --stat` 未变。报告已逐字回读验证，十条验收命令的原始输出均完整保留。

---
## 附：调度方验收（Fable）

三处新文本落地、字节 930070/16947/23009 与工单 §1.1 一致；两脚本去 docstring 后 AST 与改前一致；九项守卫＋test_figures_from_facts＋test_review_solana_integrity 全 PASS；升版 7.1.3。
