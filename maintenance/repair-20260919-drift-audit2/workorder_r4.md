# 工单 R4：v9.0.1 口径漂移与文档-代码不符 4 条纯文本修复 v2

内容基线：`e3518db`（R3 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R4a 4 条（`blind_r4a_report.md`）＋ R4b 2 条（`blind_r4b_report.md`），两路独立重合 2 条，去重后 4 条，全 minor，Fable 逐条亲核两侧原文属实。本单全部为纯文本修复，零代码改动；v2 吸收 codex 复核 r1（`review_wo4_reply.md`）：四处锚改为整行、D2 改为删句、D4 写准回退条件、D1/D3 用更短稿；**所有锚与替换文本均为目标文件整行原文，按代码块内整行字面处理**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat e3518db HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/research-workflows.md`、`references/labels/README.md`、`references/data-pipeline-robinhood-channels.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r4_done.md`。
0.4 删除 > 修改 > 新增；每处锚必须是目标文件整行原文，以 `grep -n -F -x` 核验恰 1 处且行号一致；不符停工；按整行替换，其他行不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 ≤ 930073（基线 930073；四处整行替换按 UTF-8 字面模拟净减 108 B → 929965，复核 r1 独立重算一致，实测数写入报告，须不高于基线）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r4_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均为**整行**，已由 Fable 逐行匹配验为恰 1 处；行号以 `e3518db` 内容态为准）

### D1（R4a D1）外部异构复核模板要求裸数组，与同节 v2 对象 schema 冲突
`references/research-workflows.md:125`。锚（整行）：
```
- **prompt＝本节怀疑者骨架的多结论版**：开头声明"你在只读沙箱，可执行 python3 只读重算（禁写盘），必须实际重算、只审文字的复核无效"；逐条列结论原文（含编号与数字）；附数据文件路径+字段/符号/去重说明；要求输出 JSON 数组 `[{id, verdict(CONFIRMED/WEAKENED/REFUTED), evidence, alternative_explanations, corrections}]` + 一段"结论间互相矛盾/全局缺口"观察；裁决标准同骨架（"理论上可能"不算推翻、REFUTED 须自己重算出的硬证据）。COMMON 资源约束照抄进去（duckdb 四项限制/禁大中间件——read-only 沙箱本身拦写盘，双保险）。
```
→
```
- **prompt＝本节怀疑者骨架的多结论版**：开头声明"你在只读沙箱，可执行 python3 只读重算（禁写盘），必须实际重算、只审文字的复核无效"；逐条列结论原文（含编号与数字）；附数据文件路径+字段/符号/去重说明；另附一段"结论间互相矛盾/全局缺口"观察；裁决标准同骨架（"理论上可能"不算推翻、REFUTED 须自己重算出的硬证据）。COMMON 资源约束照抄进去（duckdb 四项限制/禁大中间件——read-only 沙箱本身拦写盘，双保险）。
```
依据同文件 `:102-106`（v2 对象：schema/role/registry_sha256/results[].claim_id）、`references/analyze-workflow.md:170`（所有落盘件必须用 v2）、`scripts/report/adversarial_review_runner.py:30`（`ARTIFACT_SCHEMA = "adversarial-review-artifact/v2"`）、`:310-311`（非 dict 或 schema 不符即拒）、`:330`（取 `claim_id`）。本行开头已声明"本节怀疑者骨架的多结论版"，旧格式要求整段删除，只保留全局观察要求。

### D2（R4a D2）labels 使用篇把 `labels_meta` 落盘无条件推广到全部入口
`references/labels/README.md:8`。锚（整行）：
```
**接入方式（v4）**：`labels_resolver.py` 共享内核——`label_lookup.py`（人工查询）、EVM `cluster.py`/`analyze_holdings.py`、SOL `replay_edges.py`/`build_evolution.py`（阵营体检）均已默认接入；表缺失/加载失败显式报 **degraded_mode**（"没命中"与"没加载"可区分），分析产物落 `labels_meta`。
```
→
```
**接入方式（v4）**：`labels_resolver.py` 共享内核——`label_lookup.py`（人工查询）、EVM `cluster.py`/`analyze_holdings.py`、SOL `replay_edges.py`/`build_evolution.py`（阵营体检）均已默认接入；表缺失/加载失败显式报 **degraded_mode**（"没命中"与"没加载"可区分）。
```
依据 `scripts/solana/replay_edges.py`、`scripts/solana/build_evolution.py` 中 `labels_meta`/`.meta(` 均 0 处；EVM 侧 `scripts/evm/cluster.py:227` 写产物内字段，`scripts/evm/analyze_holdings.py:190` 以 `resv is not None and resv.table` 为前提才在 `:251` 写独立 `{chain}_labels_meta.json`——形态与条件各异，删句优于补限定。

### D3（R4a D3＝R4b D2）Robinhood LP 事件字段固定除 1e18，却被写成"本币枚"
`references/data-pipeline-robinhood-channels.md:33`。锚（整行）：
```
- `pull_lp_events.py` **用法与输出坑（2026-07-17 实测）**：①与其他脚本不同，**`--from-block N` 必传**（漏传直接 usage 报错、串行链会被短路）；`--pools` 可省略则取 config.pools（CLI 优先）；`--out` 默认 data/lp_events.json；②输出是**格式化 JSON 数组**（非 JSONL，逐行 json.loads 会炸）；③Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（WETH 枚/本币枚），不是 wei——按 wei 再除 1e18 会把费流水全算成 0（本次 Collect 62 笔 4.33 WETH 首轮统计因此归零，重读字段才修正）（DUMBMONEY，07-17）
```
→
```
- `pull_lp_events.py` **用法与输出坑（2026-07-17 实测）**：①与其他脚本不同，**`--from-block N` 必传**（漏传直接 usage 报错、串行链会被短路）；`--pools` 可省略则取 config.pools（CLI 优先）；`--out` 默认 data/lp_events.json；②输出是**格式化 JSON 数组**（非 JSONL，逐行 json.loads 会炸）；③Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（raw/1e18；仅 18 位币为枚数），不是 wei——按 wei 再除 1e18 会把费流水全算成 0（本次 Collect 62 笔 4.33 WETH 首轮统计因此归零，重读字段才修正）（DUMBMONEY，07-17）
```
依据 `scripts/robinhood/pull_lp_events.py:92`（`a0 / 1e18, a1 / 1e18` 固定缩放）、`:37-40`（config 读取无 decimals）。

### D4（R4a D4＝R4b D1）Robinhood 成本脚本本币 `decimals=0` 被回退成 18
`references/data-pipeline-robinhood-channels.md:30`。锚（整行）：
```
- `cost_engine.py`：**tx 级 swap 对价重建**——本币和报价币分别使用 config 的 `decimals` / `quote_decimals`，不得再写死 18；逐 tx 配对出每实体成本/已实现盈亏。需 data/weth_pool.jsonl + data/quote_usd_hour.json + data/transit_contracts.json；config 可选 fee_distributor。
```
→
```
- `cost_engine.py`：**tx 级 swap 对价重建**——本币取 config 的 `decimals or 18`（数值 0 也回退），报价币取 `quote_decimals`（缺失/null 用 18）；逐 tx 配对出每实体成本/已实现盈亏。需 data/weth_pool.jsonl + data/quote_usd_hour.json + data/transit_contracts.json；config 可选 fee_distributor。
```
依据 `scripts/robinhood/cost_engine.py:17`（`int(cfg.get('decimals') or 18)`：缺失/null/0 皆回退 18）、`:18`（`quote_decimals` 用 `is not None`：仅缺失/null 回退 18，0 保留）。

## §3 完成报告 `r4_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
