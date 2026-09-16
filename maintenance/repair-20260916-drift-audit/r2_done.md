# 施工 R2：完成

按 `workorder_r2.md` v2 的 §0–§3 执行；D1–D8 与 F2 全部完成。8 个白名单文档已修改，另新增本报告。§1.2 七条命令（含 `docs_lint.py --all`，共 8 次脚本执行）全部退出 0；D7 下载块 `zsh -n` 退出 0。

## 0. 内容基线与锚点核验

内容基线：`445d7acf996c287b78250bb7c8a64614ecf13c36`。施工及交付 HEAD：`36aeaea0a3bad2407369cf6159d6f8b290686b98`。VERSION：`7.1.1`。

```sh
git status --short
```

退出码：`0`。原始输出（空）：

```text
```

```sh
git rev-parse HEAD
```

退出码：`0`。原始输出：

```text
36aeaea0a3bad2407369cf6159d6f8b290686b98
```

```sh
git diff --stat 445d7ac HEAD -- SKILL.md references scripts commands-staging VERSION
```

退出码：`0`。原始输出（空）：

```text
```

全部锚点在任何文档写入前，经 `grep -n -F` 逐项核验；每个锚恰好出现 1 次且行号一致。写入前再次检查 HEAD、干净工作区、内容基线和原文件 SHA-256；同一文件按原行号从后向前修改。

| 项 | 文件 | 原行号 | 匹配数 | 结果 |
|---|---|---:|---:|---|
| D1 | `references/lp-fee-accounting.md` | 62 | 1 | PASS |
| D2 | `references/retrospective.md` | 102 | 1 | PASS |
| D3-34 | `references/data-pipeline-robinhood-channels.md` | 34 | 1 | PASS |
| D3-30 | `references/data-pipeline-robinhood-channels.md` | 30 | 1 | PASS |
| D4-105 | `references/independent-audit-protocol.md` | 105 | 1 | PASS |
| D4-106 | `references/independent-audit-protocol.md` | 106 | 1 | PASS |
| D5 | `references/scan-schemas.md` | 17 | 1 | PASS |
| D6 | `references/data-pipeline-robinhood-channels.md` | 33 | 1 | PASS |
| D7-86 | `references/labels/MAINTENANCE.md` | 86 | 1 | PASS |
| D7-87 | `references/labels/MAINTENANCE.md` | 87 | 1 | PASS |
| D7-70 | `references/labels/MAINTENANCE.md` | 70 | 1 | PASS |
| D7-80 | `references/labels/MAINTENANCE.md` | 80 | 1 | PASS |
| D8 | `references/playbook-state-anomaly.md` | 36 | 1 | PASS |
| F2 | `references/monitoring-package.md` | 43 | 1 | PASS |

## 1. 逐条改前 → 改后 diff

以下按工单编号展示基于冻结改前文件生成的差异；D3 与 D6 分别列示同一文件中各自授权的片段。

### D1

````diff
--- a/references/lp-fee-accounting.md
+++ b/references/lp-fee-accounting.md
@@ -61,3 +61,3 @@
 fee_rate_j = event.fee / 1_000_000
-gross_input_j = 正数一侧的 amount0 或 amount1
+gross_input_j = 经同 tx Transfer 校准的输入腿负值绝对值（data-pipeline-robinhood-traps 第 12 条）
 swap_fee_j ≈ gross_input_j × fee_rate_j
````

### D2

````diff
--- a/references/retrospective.md
+++ b/references/retrospective.md
@@ -101,3 +101,3 @@
 - 新的基础设施地址（CEX/MM/程序ID）→ `address-book.md`，附来源与核验日期
-- **惯犯库回灌（v6.4.1 起挂此处，原为交付后固定动作）**：`python3 scripts/labels/accumulate_offenders.py --apply`——本案庄家实体回灌惯犯库（appendix.json / analysis-state.json 为扫描源，筛查不买入的案子复盘时同样回灌；含 manifest 自动落印）；`sources/serial_conflicts_*.md` 非空时先按 labels/README 三选一裁决再 apply。挪进复盘的原因：结论未经用户复核就入库，错判地址会污染惯犯层——不复盘不回灌
+- **惯犯库回灌（v6.4.1 起挂此处，原为交付后固定动作）**：`python3 scripts/labels/accumulate_offenders.py --apply`——跨案回灌惯犯库（扫描 `DEFAULT_ROOT` 或所传案根父目录；每案优先 appendix.json，否则 analysis-state.json；跨案合并并自动落印）；`sources/serial_conflicts_*.md` 非空时先按 labels/README 三选一裁决再 apply。挪进复盘的原因：结论未经用户复核就入库，错判地址会污染惯犯层——不复盘不回灌
 - **写入后跑守护全家桶**（v3.3：`python3 scripts/tests/run_all.py` 一键=三件套 lint + replay_inc/build_html 离线契约测试；改过账本类脚本必跑）——FAIL 先修再收工
````

### D3

````diff
--- a/references/data-pipeline-robinhood-channels.md
+++ b/references/data-pipeline-robinhood-channels.md
@@ -29,3 +29,3 @@
 - `pull_weth_pool.py`：**主池报价币侧 Transfer**（Pointless 2026-07-13 收编）——cost_engine 的输入；config.pool + 可选 quote_token（默认 WETH）
-- `cost_engine.py`：**tx 级 swap 对价重建**——本币和报价币分别使用 config 的 `decimals` / `quote_decimals`，不得再写死 18；逐 tx 配对出每实体成本/已实现盈亏。需 data/weth_pool.jsonl + data/quote_usd_hour.json + transit_contracts.json；config 可选 fee_distributor。
+- `cost_engine.py`：**tx 级 swap 对价重建**——本币和报价币分别使用 config 的 `decimals` / `quote_decimals`，不得再写死 18；逐 tx 配对出每实体成本/已实现盈亏。需 data/weth_pool.jsonl + data/quote_usd_hour.json + data/transit_contracts.json；config 可选 fee_distributor。
 - `pull_swaps.py` / `pull_swaps_v4.py`：与 Transfer 同样采用身份绑定、末块重叠续拉和事件键去重；V4 有任何解码失败不写完成 receipt。
@@ -33,3 +33,3 @@
 - `pull_lp_events.py` **用法与输出坑（2026-07-17 实测）**：①与其他脚本不同，**不读 config.json 的池子配置**，必须命令行传参 `--from-block N --pools 0x主池 --out data/lp_events.jsonl`（漏传 --from-block 直接 usage 报错、串行链会被短路）；②输出是**格式化 JSON 数组**（非 JSONL，逐行 json.loads 会炸）；③Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（WETH 枚/本币枚），不是 wei——按 wei 再除 1e18 会把费流水全算成 0（本次 Collect 62 笔 4.33 WETH 首轮统计因此归零，重读字段才修正）（DUMBMONEY，07-17）
-  ⚠️ 依赖 `data/ethusdt_1h.json` 为 **list 格式** [[ts_ms,close]...]，而 cost_engine 的 quote_usd_hour.json 是 dict——两文件格式不同需各自生成（一行转换即可），首跑 FileNotFoundError 属预期（BEGGAR，07-17）
+  cost_engine 的 `data/quote_usd_hour.json` 为 `[[ts,o,h,l,c],...]`；`data/ethusdt_1h.json` 属 build_price 输入，列为 `[[ts,close],...]`；pull_lp_events 不读小时线。
 - `pull_ohlcv.py`：GT 分钟K+小时K 翻页（带 UA/退避；pool 从 config.json 读）
````

### D4

````diff
--- a/references/independent-audit-protocol.md
+++ b/references/independent-audit-protocol.md
@@ -104,4 +104,3 @@
 ```bash
-python3 scripts/report/reproduce_receipt.py <案目录> \
-  --output reproduce_output.json --receipt reproduce_receipt.json
+python3 scripts/report/reproduce_receipt.py <案目录>
 ```
````

### D5

````diff
--- a/references/scan-schemas.md
+++ b/references/scan-schemas.md
@@ -16,3 +16,3 @@
 3. **零静默截断**：所有成员/收方/来源数组全量落盘，数组长度必须等于对应 `*_count` 字段（闭合断言）；stdout 只显 top 不代表文件截断。
-4. **本文件＝完整字段登记**（v6.8.1，codex 复核 P2 采纳）：脚本实际输出的每个字段都必须在此登记——未登记字段不得输出，登记了的不得静默删除；公共通用字段（`schema/generated_at/params/total_supply_raw/edges/note`）各产物一律在场，下文不再逐一重复。输入边表的唯一性由采集管线（A2 对账关卡）保证，扫描器不去重。Solana v4 以 `(slot,tx_index)` 标识交易，并对该交易完整边集计算排序后的 `tx_digest`：重复身份且 digest 相同只留一份，digest 不同硬失败。五元组没有交易身份，同字段重复可能是不同真实交易，禁止按五字段去重。
+4. **本文件＝完整字段登记**（v6.8.1，codex 复核 P2 采纳）：脚本实际输出的每个字段都必须在此登记——未登记字段不得输出，登记了的不得静默删除；公共通用字段（`schema/generated_at/params/total_supply_raw/edges/note`）仅 wave-scan／flow-anomaly 保证齐全，其他产物见各自 schema。输入边表的唯一性由采集管线（A2 对账关卡）保证，扫描器不去重。Solana v4 以 `(slot,tx_index)` 标识交易，并对该交易完整边集计算排序后的 `tx_digest`：重复身份且 digest 相同只留一份，digest 不同硬失败。五元组没有交易身份，同字段重复可能是不同真实交易，禁止按五字段去重。
 
````

### D6

````diff
--- a/references/data-pipeline-robinhood-channels.md
+++ b/references/data-pipeline-robinhood-channels.md
@@ -32,3 +32,3 @@
 - `build_price.py`：**全历史 USD 价格重建**——方向由 token/quote 地址排序判定，V3 raw ratio 再乘 `10^(token_decimals-quote_decimals)` 校正单位；GT 分钟 K 没有任何重叠样本时 fail-closed，不得发布无交叉验证的价格序列。输入仍为 `data/ethusdt_1h.json` 与 `data/ohlcv_minute.json`。
-- `pull_lp_events.py` **用法与输出坑（2026-07-17 实测）**：①与其他脚本不同，**不读 config.json 的池子配置**，必须命令行传参 `--from-block N --pools 0x主池 --out data/lp_events.jsonl`（漏传 --from-block 直接 usage 报错、串行链会被短路）；②输出是**格式化 JSON 数组**（非 JSONL，逐行 json.loads 会炸）；③Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（WETH 枚/本币枚），不是 wei——按 wei 再除 1e18 会把费流水全算成 0（本次 Collect 62 笔 4.33 WETH 首轮统计因此归零，重读字段才修正）（DUMBMONEY，07-17）
+- `pull_lp_events.py` **用法与输出坑（2026-07-17 实测）**：①与其他脚本不同，**`--from-block N` 必传**（漏传直接 usage 报错、串行链会被短路）；`--pools` 可省略则取 config.pools（CLI 优先）；`--out` 默认 data/lp_events.json；②输出是**格式化 JSON 数组**（非 JSONL，逐行 json.loads 会炸）；③Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（WETH 枚/本币枚），不是 wei——按 wei 再除 1e18 会把费流水全算成 0（本次 Collect 62 笔 4.33 WETH 首轮统计因此归零，重读字段才修正）（DUMBMONEY，07-17）
   ⚠️ 依赖 `data/ethusdt_1h.json` 为 **list 格式** [[ts_ms,close]...]，而 cost_engine 的 quote_usd_hour.json 是 dict——两文件格式不同需各自生成（一行转换即可），首跑 FileNotFoundError 属预期（BEGGAR，07-17）
````

### D7

````diff
--- a/references/labels/MAINTENANCE.md
+++ b/references/labels/MAINTENANCE.md
@@ -69,2 +69,3 @@
 ```bash
+(cd sources || exit
 P="${CHIP_PROXY:?请先设置 CHIP_PROXY}"   # 代理地址不写死；脚本统一由 proxy_config.py 解析
@@ -80,2 +81,3 @@
 ETH_RPC="https://ethereum-rpc.publicnode.com" python3 ../probe_codetype.py scamsniffer_address.json scamsniffer_codetype.json
+)
 ```
@@ -85,4 +87,4 @@
 ```bash
-cd sources && python3 ../add_labels.py my_additions.csv        # 合并进现库 + 三闸事务（FAIL 还原）
-python3 ../accumulate_offenders.py && cd sources && python3 ../add_labels.py serial_actors.csv
+(cd sources && python3 ../add_labels.py my_additions.csv)        # 合并进现库 + 三闸事务（FAIL 还原）
+python3 accumulate_offenders.py && (cd sources && python3 ../add_labels.py serial_actors.csv)
 ```
````

### D8

````diff
--- a/references/playbook-state-anomaly.md
+++ b/references/playbook-state-anomaly.md
@@ -35,3 +35,3 @@
 
-识别三角（充提开关+多所现价+链上池价）见 data-pipeline-evm-sources §6 表；本节管**解读与呈现**——报告写"多所割裂/脱锚"时必须预答读者必问的常识疑问："既然各所互相断开，价格为什么还出奇一致？"
+识别三角（充提开关+多所现价+链上池价）见 data-pipeline-evm-sources §4 表；本节管**解读与呈现**——报告写"多所割裂/脱锚"时必须预答读者必问的常识疑问："既然各所互相断开，价格为什么还出奇一致？"
 
````

### F2

````diff
--- a/references/monitoring-package.md
+++ b/references/monitoring-package.md
@@ -42,3 +42,3 @@
 - **address 必须完整**，绝对不要缩写省略——一律从落盘数据文件复制；build_html.py 见省略号/星号会 WARN
-- **chain** 小写正式枚举：bsc / eth / base / sol / robinhood。arbitrum 只保留探索采集，
+- **chain** 小写枚举：bsc / eth / base / sol / robinhood（robinhood 为探索档）。arbitrum 只保留探索采集，
   正式门禁未齐，不生成正式监控包；新链适配完成后沿用小写简名
````

## 2. §1.1 字节实测

对每个文件分别执行 `stat -f %z <文件>` 并求和；`references/attic.md` 仅取文件大小，未读取内容。改前、改后均实测。

| 范围 | 文件数 | 改前字节 | 改后字节 | 净变更 | 约束 |
|---|---:|---:|---:|---:|---|
| `SKILL.md` | 1 | 8021 | 8021 | 0 | = 8021，PASS |
| `references/*.md references/casebook/*.md references/labels/*.md` | 42 | 929850 | 929831 | -19 | ≤ 929850，PASS |
| `commands-staging/*.md` | 4 | 8798 | 8798 | 0 | = 8798，PASS |

实测 `references` 合计与工单 v2 的模拟值 `929831` 一致。

## 3. §1.2 守卫原始输出

```sh
python3 scripts/tests/docs_lint.py && python3 scripts/tests/docs_lint.py --all
```

退出码：`0`。原始输出：

```text
PASS: 45 个文档，引用无断链、粗体配对完整
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

```sh
python3 scripts/tests/casebook_lint.py
```

退出码：`0`。原始输出：

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

```sh
python3 scripts/tests/changelog_lint.py
```

退出码：`0`。原始输出：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 73 条 + 归档 139 条
```

```sh
python3 scripts/tests/test_contract_routes.py
```

退出码：`0`。原始输出：

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

```sh
python3 scripts/tests/test_sixlens_docs.py
```

退出码：`0`。原始输出：

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

```sh
python3 scripts/tests/test_g3_docs_guards.py
```

退出码：`0`。原始输出：

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

```sh
python3 scripts/tests/test_version_consistency.py
```

退出码：`0`。原始输出：

```text
PASS: M-03 version metadata consistent at 7.1.1
```

### D7 下载代码块语法检查

以改后 `references/labels/MAINTENANCE.md:70–82` 的整个下载代码块作为 stdin，实际执行 `zsh -n`；只解析语法。原第 70–80 行逐字保持不变。检查器原始输出如下（其中 stdout/stderr 为空即 zsh 的原始空输出）：

```json
{
  "command": "zsh -n (download fenced block via stdin)",
  "file": "references/labels/MAINTENANCE.md",
  "block_first_line": 70,
  "block_last_line": 82,
  "original_lines_70_80_unchanged": true,
  "block_sha256": "5c59d317fabe8e18b43f4c8686aa45a85e48a64b1b4ee4adbec51466d8da5797",
  "exit_code": 0,
  "stdout": "",
  "stderr": ""
}
```

## 4. git diff --stat 与范围复核

```sh
git diff --stat
```

```text
 references/data-pipeline-robinhood-channels.md | 6 +++---
 references/independent-audit-protocol.md       | 3 +--
 references/labels/MAINTENANCE.md               | 6 ++++--
 references/lp-fee-accounting.md                | 2 +-
 references/monitoring-package.md               | 2 +-
 references/playbook-state-anomaly.md           | 2 +-
 references/retrospective.md                    | 2 +-
 references/scan-schemas.md                     | 2 +-
 8 files changed, 13 insertions(+), 12 deletions(-)
```

`git diff --stat` 仅列出以上 8 个已跟踪白名单文件；本报告为未跟踪新文件，因此不在该命令的统计中。交付时工作区状态：

```text
 M references/data-pipeline-robinhood-channels.md
 M references/independent-audit-protocol.md
 M references/labels/MAINTENANCE.md
 M references/lp-fee-accounting.md
 M references/monitoring-package.md
 M references/playbook-state-anomaly.md
 M references/retrospective.md
 M references/scan-schemas.md
?? maintenance/repair-20260916-drift-audit/r2_done.md
```

另用独立的字节位置替换法，从施工 HEAD 重建工单授权结果，与 8 个改后文件逐字节比较，全部一致；没有指定片段外的修改。`git diff --check` 退出 0，输出为空。HEAD 与暂存区未变；`SKILL.md`、`VERSION`、`commands-staging/`、`scripts/`（含 `scripts/tests/contract_manifest.json`）相对 HEAD 无差异。未 commit、push 或部署 `~/.claude/commands/`。

## 5. 差异与停工点

工单内容、范围和交付约束无偏离；无停工点，未碰撞 contract needle。

核验过程记录：首次构造 D4 的校验命令时，施工工具误给锚点多传了一个反斜杠，`grep` 返回 1、stdout/stderr 为空。该次检查尚未写入任何文档。随后直接从工单提取锚点，确认工单原文与目标第 105 行完全相同，末尾均为单个 U+005C（十进制 92）；按原文实际执行 `grep -n -F` 返回唯一的第 105 行。修正校验命令后，重新完成全部 14 项核验，全部通过，才执行修改。未修改工单或猜测目标片段。

首次误构造的命令与结果：

```sh
grep -n -F -- 'python3 scripts/report/reproduce_receipt.py <案目录> \\' references/independent-audit-protocol.md
```

```text
exit_code=1
stdout=""
stderr=""
```

直接提取工单原文的复核结果：

```json
{
  "workorder_anchor": "python3 scripts/report/reproduce_receipt.py <案目录> \\",
  "workorder_anchor_tail_codepoints": [
    30446,
    24405,
    62,
    32,
    92
  ],
  "target_line_105": "python3 scripts/report/reproduce_receipt.py <案目录> \\",
  "target_line_tail_codepoints": [
    30446,
    24405,
    62,
    32,
    92
  ],
  "equal": true,
  "grep_exit": 0,
  "grep_stdout": "105:python3 scripts/report/reproduce_receipt.py <案目录> \\\n",
  "grep_stderr": ""
}
```

## 6. 禁读披露

会话启动时平台已自动提供 memory 摘要文本，已在开工说明中披露。本轮未主动读取 `~/.codex/` 下任何文件，未调用工具读取 memories，也未使用摘要中的历史事实替代本轮实测。

未主动读取本仓库 `archive/`、`blind-reviews/`、`.staging_*` 或 `references/attic.md` 的内容；对 attic.md 仅执行字节大小统计。按工单原样运行的守卫脚本若内部遍历这些路径，属于 §0.2 明确允许的被测代码行为。全程离线，无 API、浏览器或网络请求；未读取 API 登记文件或凭据。
