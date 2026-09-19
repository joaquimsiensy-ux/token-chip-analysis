# 工单 R4：v9.0.1 口径漂移与文档-代码不符 4 条纯文本修复 v1

内容基线：`e3518db`（R3 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R4a 4 条（`blind_r4a_report.md`）＋ R4b 2 条（`blind_r4b_report.md`），两路独立重合 2 条，去重后 4 条，全 minor，Fable 逐条亲核两侧原文属实。本单全部为纯文本修复，零代码改动；**所有锚与替换文本均为代码块内片段（非整行处已注明），不含首尾空白**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat e3518db HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/research-workflows.md`、`references/labels/README.md`、`references/data-pipeline-robinhood-channels.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r4_done.md`。
0.4 删除 > 修改 > 新增；每处锚先 `grep -n -F` 核验恰 1 处且行号一致；不符停工；只动指定片段，锚外一字不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 ≤ 930160（基线 930073；四处替换按 UTF-8 字面模拟净增 +53 B → 930126，实测数写入报告）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r4_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均已由 Fable `grep -c -F` 验为恰 1 处；行号以 `e3518db` 内容态为准）

### D1（R4a D1）外部异构复核模板要求裸数组，与同节 v2 对象 schema 冲突
`references/research-workflows.md:125`（行内片段）。锚：
```
要求输出 JSON 数组 `[{id, verdict(CONFIRMED/WEAKENED/REFUTED), evidence, alternative_explanations, corrections}]` + 一段"结论间互相矛盾/全局缺口"观察
```
→
```
要求按本节上方 `adversarial-review-artifact/v2` 输出 schema 落盘 + 一段"结论间互相矛盾/全局缺口"观察
```
依据同文件 `:102-106`（v2 对象：schema/role/registry_sha256/results[].claim_id）、`references/analyze-workflow.md:170`（所有落盘件必须用 v2）、`scripts/report/adversarial_review_runner.py:30`（`ARTIFACT_SCHEMA = "adversarial-review-artifact/v2"`）、`:310-311`（非 dict 或 schema 不符即拒）、`:330`（取 `claim_id`）。

### D2（R4a D2）labels 使用篇把 EVM 的 `labels_meta` 落盘无条件推广到 SOL 入口
`references/labels/README.md:8`（行内片段）。锚：
```
分析产物落 `labels_meta`
```
→
```
EVM 两入口的分析产物落 `labels_meta`
```
依据 `scripts/evm/cluster.py:227`、`scripts/evm/analyze_holdings.py:250-251`（写 `labels_meta`）；`scripts/solana/replay_edges.py`、`scripts/solana/build_evolution.py` 中 `labels_meta`/`.meta(` 均 0 处，`scripts/lib/camp_series_provenance.py` sidecar 亦无该字段。

### D3（R4a D3＝R4b D2）Robinhood LP 事件字段固定除 1e18，却被写成"本币枚"
`references/data-pipeline-robinhood-channels.md:33`（行内片段）。锚：
```
是**已解码浮点**（WETH 枚/本币枚），不是 wei
```
→
```
是**已解码浮点**（固定 raw/1e18；仅 18 位精度币等于枚），不是 wei
```
依据 `scripts/robinhood/pull_lp_events.py:92`（`a0 / 1e18, a1 / 1e18` 固定缩放）、`:37-40`（config 读取无 decimals）。

### D4（R4a D4＝R4b D1）Robinhood 成本脚本本币 `decimals=0` 被回退成 18
`references/data-pipeline-robinhood-channels.md:30`（行内片段）。锚：
```
本币和报价币分别使用 config 的 `decimals` / `quote_decimals`，不得再写死 18
```
→
```
本币和报价币分别使用 config 的 `decimals`（缺省或 0 时回退 18）/ `quote_decimals`（仅缺省回退 18），不得再写死 18
```
依据 `scripts/robinhood/cost_engine.py:17`（`int(cfg.get('decimals') or 18)`）、`:18`（`quote_decimals` 用 `is not None` 判缺省）。

## §3 完成报告 `r4_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
