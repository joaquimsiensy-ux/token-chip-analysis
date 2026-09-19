# 工单R4复核：退回

四条原始发现的核心代码依据均成立，v1 的字节预算也正确。**退回原因：四个锚均非整行；D2 的替换仍保留过宽的落盘承诺。** D4 应明确回退条件。现有三份文档白名单够用。

复核 HEAD：`769e8ba9e213b88c85c4bcaf5b7d6200011442eb`。前后工作树均干净；主内容与 `e3518db` 基线一致。完整报告已打印至 stdout。

**锚点与 v1 字节复算**

| 条目 | 目标位置 | `grep -n -F` | 加 `-x` 整行匹配 | 原片段→替换片段 | 净变化 |
|---|---|---|---:|---:|---:|
| D1 | research-workflows.md:125 | 1 处，行号一致 | 0 | 170→126 B | −44 B |
| D2 | labels/README.md:8 | 1 处，行号一致 | 0 | 29→45 B | +16 B |
| D3 | data-pipeline-robinhood-channels.md:33 | 1 处，行号一致 | 0 | 59→87 B | +28 B |
| D4 | data-pipeline-robinhood-channels.md:30 | 1 处，行号一致 | 0 | 92→145 B | +53 B |

四个目标的**现行完整行**另行核验均恰好一处，行号正确。工单 v2 应把完整原行放入锚代码块，并同步修改总述中的“片段／不含首尾空白”。§0.4 建议替换为：

```text
0.4 删除 > 修改 > 新增；每处锚必须是目标文件整行原文，保留首尾空白，以 `grep -n -F -x` 核验恰 1 处且行号一致；不符停工；按整行替换文本修改，其他行不动。
```

**D1：采纳发现；v1 替换正确，但存在更短改法。**

[adversarial_review_runner.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/adversarial_review_runner.py:305) 的事实均核实：第 30 行定义 v2 schema；310–315 行检查对象、schema、role 和 registry SHA；330–349 行检查 `claim_id`、重复及越界。

抽取现行纯函数复现：裸数组拒收、仅有 `id` 的结果拒收、正确 v2 对象通过。原行已经声明复用“本节怀疑者骨架”，可删除重复的旧格式要求，保留全局观察。

[research-workflows.md:125](/Users/uravvv/.claude/skills/token-chip-analysis/references/research-workflows.md:125) 整行替换为：

```text
- **prompt＝本节怀疑者骨架的多结论版**：开头声明"你在只读沙箱，可执行 python3 只读重算（禁写盘），必须实际重算、只审文字的复核无效"；逐条列结论原文（含编号与数字）；附数据文件路径+字段/符号/去重说明；另附一段"结论间互相矛盾/全局缺口"观察；裁决标准同骨架（"理论上可能"不算推翻、REFUTED 须自己重算出的硬证据）。COMMON 资源约束照抄进去（duckdb 四项限制/禁大中间件——read-only 沙箱本身拦写盘，双保险）。
```

**D2：采纳发现，退回 v1 替换；建议删除句尾承诺。**

两个 SOL 脚本中的 `labels_meta`、`.meta(` 均为零；实际 JSON、manifest 和 sidecar 调用未传入标签元信息。共享 sidecar 的固定字段也没有该项。

EVM 两入口确有相关输出，但形态和条件不同：

- `cluster.py:227` 写产物内的 `labels_meta` 字段。
- [analyze_holdings.py:190](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/analyze_holdings.py:190) 以 `if resv is not None and resv.table` 为前提，随后在第 251 行写独立的 `{chain}_labels_meta.json`。resolver 不存在或标签表为空时不会新写该文件。

因此，“EVM 两入口的分析产物落 `labels_meta`”仍缺少成立条件。按删除优先，直接删除该分句，比继续补限定语更合适。

[labels/README.md:8](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/README.md:8) 整行替换为：

```text
**接入方式（v4）**：`labels_resolver.py` 共享内核——`label_lookup.py`（人工查询）、EVM `cluster.py`/`analyze_holdings.py`、SOL `replay_edges.py`/`build_evolution.py`（阵营体检）均已默认接入；表缺失/加载失败显式报 **degraded_mode**（"没命中"与"没加载"可区分）。
```

**D3：采纳；v1 替换正确，可用更短等价文字。**

[pull_lp_events.py:92](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/robinhood/pull_lp_events.py:92) 两腿固定除以 `1e18`；配置读取没有获取 decimals，写出前没有精度校正。

源码表达式复现：`raw=1000000` 输出 `1e-12`，而对 6 位币实际对应 1 枚。该发现有明确数量差异。

[data-pipeline-robinhood-channels.md:33](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-channels.md:33) 整行替换为：

```text
- `pull_lp_events.py` **用法与输出坑（2026-07-17 实测）**：①与其他脚本不同，**`--from-block N` 必传**（漏传直接 usage 报错、串行链会被短路）；`--pools` 可省略则取 config.pools（CLI 优先）；`--out` 默认 data/lp_events.json；②输出是**格式化 JSON 数组**（非 JSONL，逐行 json.loads 会炸）；③Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（raw/1e18；仅 18 位币为枚数），不是 wei——按 wei 再除 1e18 会把费流水全算成 0（本次 Collect 62 笔 4.33 WETH 首轮统计因此归零，重读字段才修正）（DUMBMONEY，07-17）
```

**D4：采纳发现；明确两种回退条件。**

[cost_engine.py:17](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/robinhood/cost_engine.py:17) 的 `or 18` 与下一行的 `is not None` 均属实。直接计算现行表达式：

| 配置值 | 本币 `dec` | 报价币 `quote_dec` |
|---|---:|---:|
| 缺失 | 18 | 18 |
| 显式 `null` | 18 | 18 |
| 数值 `0` | 18 | 0 |
| 数值 `6` | 6 | 6 |

本币判断所有假值；报价币对缺失或 `None` 回退。“仅缺省”没有明确显式 `null` 的行为。建议保留源码表达式、点明数值零，同时删去重复的“不得再写死 18”。

[data-pipeline-robinhood-channels.md:30](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-channels.md:30) 整行替换为：

```text
- `cost_engine.py`：**tx 级 swap 对价重建**——本币取 config 的 `decimals or 18`（数值 0 也回退），报价币取 `quote_decimals`（缺失/null 用 18）；逐 tx 配对出每实体成本/已实现盈亏。需 data/weth_pool.jsonl + data/quote_usd_hour.json + data/transit_contracts.json；config 可选 fee_distributor。
```

**预算与上下文**

三组 references 基线分别为 `825088 B`、`74491 B`、`30494 B`，合计 `930073 B`；`attic.md` 仅通过 `stat` 计大小。

- **v1：**净增 `53 B`，得到 `930126 B ≤ 930160 B`，余量 `34 B`。
- **上述较短稿：**D1 `−116 B`、D2 `−32 B`、D3 `+15 B`、D4 `+25 B`，合计 **净减 `108 B`**，得到 **`929965 B`**，余量 `195 B`。D2 删除范围包含前导中文逗号。
- `SKILL.md = 8021 B`、commands 合计 `8789 B`，均保持不变。

v1 未增加 `SKILL.md`，但 references 确实增长了 `53 B`，不能据此声称整体文档上下文零增长。较短稿同时满足删除优先和总量不增长。

**回归面与范围**

检索了 49 份允许读取的文档：盲审列出的 46 份、`CHANGELOG.md` 和两份项目 README。未确认白名单外还有同款旧表述。

`independent-audit-protocol.md:167` 已使用 v2；第 179 行的数组属于 blockers 输入，不能误改。`playbook-state-anomaly.md:84` 的币本位原则和 LP 分解公式、Robinhood methods 第 14 行的 VEX 专案说明，没有作出本次涉及的通用单位或零精度保留承诺，不列为确定漂移。**三文档白名单够用。**

四项均有代码证据，未把措辞偏好计为漂移；无需扩大为代码修复、历史个案改写或其他精度规则整顿。

完成了静态对照、纯函数／表达式复现、锚检查和 UTF-8 内存模拟；建议稿通过 G3 的 `check_f13`、`check_f05` 纯检查。**未运行整套守卫**：其中包含读取禁区及创建临时文件的行为，工单中的施工例外不作为本次复核授权，因此不声称 §1.2 全绿。

| 审查项 | 结论 | 处理 |
|---|---|---|
| a 整行锚 | 退回 | 四处换成完整原行，保留空白 |
| b 代码事实及替换 | 部分退回 | 依据均成立；D2 删除过宽承诺，D4 明确回退条件 |
| c 字节预算 | 通过 | v1 `+53 B` 正确，未超上限 |
| d 回归面／白名单 | 通过 | 未确认白名单外同款漂移 |
| e 文本与上下文 | 采用较短稿 | 净减 `108 B`，无新增章节或入口 |
| f 范围与必要性 | 通过 | 四项确有不符，不扩为代码修复 |

执行披露：离线，未修改、新建文件或 commit；未读取 `~/.codex/` 或 memories。初次文件名枚举曾显示 archive 与 attic 路径，未打开正文，随后明确排除。系统 git 缓存及 shell here-document 临时文件创建尝试均被只读沙箱拒绝，未生成文件；后续使用直接 git 二进制和 `python -B -c`。maintenance 正文读取仅限本工程指定三份文件。
