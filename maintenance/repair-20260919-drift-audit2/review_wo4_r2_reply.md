# 工单R4复核r2：通过

v2 已正确吸收第一轮的四处整行锚、D2 删句、D4 回退条件及 D1/D3 短稿。四段替换文本与第一轮建议逐字一致，**未发现新增或未吸收的退回项**。完整报告已打印到 stdout，未创建文件。

复核 HEAD：`22e9843c7eeec1a6ba09b7cb8784d00a644c5c2d`，前后不变；指定主内容路径相对 `e3518db` 的提交树差异为空。

**D1：通过，采纳原稿。**

[adversarial_review_runner.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/adversarial_review_runner.py:305) 第 30 行定义 v2 schema；310–315 行校验对象、schema、role 和 registry SHA；330–349 行读取并校验 `claim_id`、重复及越界。内存执行现行纯函数确认：裸数组、仅含 `id`、错误 schema/role/SHA、重复或越界 claim 均拒收，正确 v2 对象通过。

删除旧结构要求后，仍复用同节 102–106 行的对象骨架，与 analyze-workflow:170 一致。

[research-workflows.md:125](/Users/uravvv/.claude/skills/token-chip-analysis/references/research-workflows.md:125) 采纳的整行替换原文：

```text
- **prompt＝本节怀疑者骨架的多结论版**：开头声明"你在只读沙箱，可执行 python3 只读重算（禁写盘），必须实际重算、只审文字的复核无效"；逐条列结论原文（含编号与数字）；附数据文件路径+字段/符号/去重说明；另附一段"结论间互相矛盾/全局缺口"观察；裁决标准同骨架（"理论上可能"不算推翻、REFUTED 须自己重算出的硬证据）。COMMON 资源约束照抄进去（duckdb 四项限制/禁大中间件——read-only 沙箱本身拦写盘，双保险）。
```

**D2：通过，采纳删句。**

SOL 两脚本中的 `labels_meta`、`.meta(` 均为 0 处；序列、manifest 与 sidecar 写出路径也未附标签元信息。[cluster.py:227](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/cluster.py:227) 写产物内字段；[analyze_holdings.py:190](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/analyze_holdings.py:190) 确以 `resv is not None and resv.table` 为条件，在第 251 行写独立文件。删句消除了无条件落盘承诺。

[labels/README.md:8](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/README.md:8) 采纳的整行替换原文：

```text
**接入方式（v4）**：`labels_resolver.py` 共享内核——`label_lookup.py`（人工查询）、EVM `cluster.py`/`analyze_holdings.py`、SOL `replay_edges.py`/`build_evolution.py`（阵营体检）均已默认接入；表缺失/加载失败显式报 **degraded_mode**（"没命中"与"没加载"可区分）。
```

**D3：通过，采纳短稿。**

[pull_lp_events.py:92](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/robinhood/pull_lp_events.py:92) 两腿均固定除以 `1e18`；配置读取未取 decimals，写出前没有精度修正。源码表达式复现：`raw=1000000` 输出 `1e-12`，而对 6 位币应为 1 枚。新括注准确限定了单位。

[data-pipeline-robinhood-channels.md:33](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-channels.md:33) 采纳的整行替换原文：

```text
- `pull_lp_events.py` **用法与输出坑（2026-07-17 实测）**：①与其他脚本不同，**`--from-block N` 必传**（漏传直接 usage 报错、串行链会被短路）；`--pools` 可省略则取 config.pools（CLI 优先）；`--out` 默认 data/lp_events.json；②输出是**格式化 JSON 数组**（非 JSONL，逐行 json.loads 会炸）；③Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（raw/1e18；仅 18 位币为枚数），不是 wei——按 wei 再除 1e18 会把费流水全算成 0（本次 Collect 62 笔 4.33 WETH 首轮统计因此归零，重读字段才修正）（DUMBMONEY，07-17）
```

**D4：通过，采纳回退条件稿。**

[cost_engine.py:17](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/robinhood/cost_engine.py:17) 确为 `int(cfg.get('decimals') or 18)`；第 18 行对报价币使用 `is not None`。现行表达式复现结果：

| 配置值 | 本币 dec | 报价币 quote_dec |
|---|---:|---:|
| 缺失 | 18 | 18 |
| null | 18 | 18 |
| 数值 0 | 18 | 0 |
| 数值 6 | 6 | 6 |
| 字符串 `"0"` | 0 | 0 |

v2 的“数值 0”限定及缺失/null 回退描述准确。

[data-pipeline-robinhood-channels.md:30](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-channels.md:30) 采纳的整行替换原文：

```text
- `cost_engine.py`：**tx 级 swap 对价重建**——本币取 config 的 `decimals or 18`（数值 0 也回退），报价币取 `quote_decimals`（缺失/null 用 18）；逐 tx 配对出每实体成本/已实现盈亏。需 data/weth_pool.jsonl + data/quote_usd_hour.json + data/transit_contracts.json；config 可选 fee_distributor。
```

四处锚均实际执行了 `grep -n -F` 和 `grep -n -F -x`，两种检查均恰好命中 1 处，行号一致。下表 UTF-8 字节数不含未改变的行尾 LF。

| 条目 | 目标行 | 两种 grep 命中数 | 原整行 B | 替换整行 B | 净变化 B |
|---|---|---|---:|---:|---:|
| D1 | research-workflows.md:125 | 1 / 1 | 684 | 568 | −116 |
| D2 | labels/README.md:8 | 1 / 1 | 350 | 318 | −32 |
| D3 | data-pipeline-robinhood-channels.md:33 | 1 / 1 | 621 | 636 | +15 |
| D4 | data-pipeline-robinhood-channels.md:30 | 1 / 1 | 316 | 341 | +25 |
| 合计 | 四行、三文件 | 全部一致 | 1971 | 1863 | **−108** |

字节预算独立复算如下，替换仅在内存模拟：

| 统计范围 | 基线 B | 替换后 B |
|---|---:|---:|
| `references/*.md` | 825088 | 825012 |
| `references/casebook/*.md` | 74491 | 74491 |
| `references/labels/*.md` | 30494 | 30462 |
| references 合计 | **930073** | **929965** |
| `SKILL.md` | 8021 | 8021 |
| `commands-staging/*.md` | 8789 | 8789 |

**净减 108 B 成立；929965 ≤ 930073，余量 108 B。**

回归检索覆盖 49 份允许读取的现行 Markdown 文档，未确认白名单外还有同款旧表述：

- `independent-audit-protocol.md:167` 已使用 v2；第 179 行的数组属于 blockers 输入。
- `labels/README.md:54` 是 `meta()` API 用法，没有承诺全部入口自动落盘。
- `playbook-state-anomaly.md:84` 是币本位原则和 LP 分解方法；Robinhood methods 第 14 行是 VEX 专案说明，均未作通用枚数或保留零精度的承诺。

三份文档白名单够用。D1/D2 删除重复或过宽要求，D3/D4 修正事实；没有代码修复、新增章节或新增 skill 入口，上下文总量下降。第一轮短稿已落实，无需因进一步缩字的措辞偏好再次改稿。

| 审查项 | 结论 | 核验结果 |
|---|---|---|
| a 整行锚与行号 | 通过 | 四处均唯一，行号正确 |
| b 依据与替换事实 | 通过 | 代码事实及引用行号成立，无新增不实断言 |
| c UTF-8 字节预算 | 通过 | 净减 108 B；929965 ≤ 930073 |
| d 回归面与白名单 | 通过 | 未确认同款遗漏，白名单够用 |
| e 删除优先与上下文 | 通过 | 短稿已吸收，总量下降 |
| f 范围与必要性 | 通过 | 无越界修复或将措辞偏好计为漂移 |

执行披露：全程离线、只读，未修改或新建文件、未 commit；未读取 `~/.codex/`、memories 或其他禁读正文。`attic.md` 仅 stat 计大小；maintenance 正文仅读取指定四份文件。内存替换稿通过 G3 的 `check_f13`、`check_f05` 纯检查；未运行会写盘或遍历禁区的整套守卫，本结论不代表施工验收全绿。
