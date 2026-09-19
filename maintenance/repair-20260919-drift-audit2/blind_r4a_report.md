# 盲审 R4a：4 条发现

审查基线：`8d92dae2943d2018291516ec38b0db0dfaacd4ad`；main，VERSION=9.0.1；git status 前/后：空/空。审查结束时 HEAD 未变，两次 `git status --short` 均退出 0、stdout 为空。

4 条均为 minor：A 类 1 条，B 类 3 条。未确认 R1–R3 修复引入的新不一致。下列发现涉及的原文及实现文件，相对 R1 施工前基线 `198abf60bf65b10202066628b9bdad7701267536` 均无 diff；不重复前三轮已修的 15 条。报告全文已打印到 stdout，未保存文件。

## 覆盖声明

覆盖 46 份必审文档及 CHANGELOG 的现行规则部分，逐文件如下。采用全文术语检索、脚本引用检查和重点段落人工对照。

```text
SKILL.md
references/address-book.md
references/analysis-playbook.md
references/analyze-workflow.md
references/context-discipline.md
references/data-pipeline-evm-channels.md
references/data-pipeline-evm-recon.md
references/data-pipeline-evm-sources.md
references/data-pipeline-evm.md
references/data-pipeline-robinhood-channels.md
references/data-pipeline-robinhood-methods.md
references/data-pipeline-robinhood-traps.md
references/data-pipeline-robinhood.md
references/data-pipeline-solana-capture.md
references/data-pipeline-solana-scan.md
references/data-pipeline-solana.md
references/economic-control-accounting.md
references/environment.md
references/independent-audit-protocol.md
references/lp-fee-accounting.md
references/maintenance-review-repair.md
references/monitoring-package.md
references/playbook-entity-cluster-cost.md
references/playbook-entity-cluster-methods.md
references/playbook-entity-cluster-tiering.md
references/playbook-evidence-wording.md
references/playbook-state-anomaly.md
references/playbook-supply-recon.md
references/report-template.md
references/research-workflows.md
references/retrospective.md
references/scan-schemas.md
references/split-run.md
references/casebook/README.md
references/casebook/cex-custody-methods.md
references/casebook/cex-custody.md
references/casebook/entity-clustering-methods.md
references/casebook/entity-clustering.md
references/casebook/supply-accounting-methods.md
references/casebook/supply-accounting.md
references/labels/README.md
references/labels/MAINTENANCE.md
commands-staging/token-analyze-1.md
commands-staging/token-analyze-2.md
commands-staging/token-analyze-3.md
commands-staging/token-analyze.md
CHANGELOG.md（版本规则与 7.2.0–9.0.1 当前行为描述）
```

术语表共 **230 项**：阶段/门禁 27、协议版本 22、脚本名 33、CLI 参数 41、产物名 88、阈值 19。从 SKILL、analyze-workflow、split-run 抽取，展开阶段和门禁范围后，在上述白名单逐文件检索；另外提取全部文档中的 147 个不同脚本引用，检查仓内实现或“逐案脚本/历史示例”等限定。

重点核对了 reconcile/wave/flow/wrapper 的 schema、字段和生产者常量，以及 seal/handoff 在流程册中的契约；实体判级、状态判断、经济控制账和 casebook 的互引；monitoring、LP fee、research workflow、labels 与 Robinhood 探索脚本。代码侧核对相关生产者、消费者、argparse、写出语句及测试，并检查 `agents/openai.yaml`、`pyproject.toml`。候选均反查历史叙述、合法别名、formal/exploration 边界及前三轮工单。已裁决的 wave_scan 浮点阈值例外未计入。

采用静态读取及内存 AST 复现，未运行会写产物或联网的业务脚本；全程未修改、新建文件或 commit，未访问网络。

**范围偏差披露**：开工时一次 `wc -l references/*.md` 误把 `references/attic.md` 纳入计行，wc 读取了其内容，但只输出行数、未展示正文。这不符合禁读要求，已在过程中披露并改用明确排除它的白名单；其内容未用于任何发现。未读取 `~/.codex/`（含 memories），也未读取其他禁读目录内容。maintenance 的读取限于本工程和指定的上一轮裁决台账。

## 发现（按严重度排序）

### D1 — minor — A 类 — 外部异构复核模板仍要求裸数组，与现行 v2 产物格式冲突

- 位置甲：[references/research-workflows.md:125](/Users/uravvv/.claude/skills/token-chip-analysis/references/research-workflows.md:125) 原文「要求输出 JSON 数组 `[{id, verdict(CONFIRMED/WEAKENED/REFUTED), evidence, alternative_explanations, corrections}]` + 一段"结论间互相矛盾/全局缺口"观察」。
- 位置乙：[references/research-workflows.md:103](/Users/uravvv/.claude/skills/token-chip-analysis/references/research-workflows.md:103) 原文「{ "schema": "adversarial-review-artifact/v2", "role": "entity_attribution_skeptic",」；第 104–105 行要求 `registry_sha256` 和 `"results": [{"claim_id": "..."`。另 [references/analyze-workflow.md:170](/Users/uravvv/.claude/skills/token-chip-analysis/references/analyze-workflow.md:170) 在包含外部异构路的同一条中明确：「所有落盘件必须使用 `adversarial-review-artifact/v2` 绑定当前 `a4_claims.json` sha」。
- 代码佐证：[scripts/report/adversarial_review_runner.py:310](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/adversarial_review_runner.py:310) 原文「`if not isinstance(data, dict) or data.get("schema") != ARTIFACT_SCHEMA:`」，下一行抛出格式错误；第 330 行取 `item.get("claim_id")`。从源码提取纯校验函数，把模板裸数组送入，实际得到 `review artifact must use adversarial-review-artifact/v2`。
- 矛盾点：照外部路专用模板交付会生成旧根结构和旧 id 字段，不能作为现行复核 artifact 消费。该册第 128 行允许外部增强路失败后降级交付，因此定 minor。
- 修法建议：**删除**第 125 行独立规定的旧输出结构，复用本节已有 v2 输出骨架。
- 复现：

```sh
rg -n '要求输出 JSON 数组|输出 JSON schema|adversarial-review-artifact/v2' references/research-workflows.md references/analyze-workflow.md
rg -n 'ARTIFACT_SCHEMA =|not isinstance\(data, dict\)|claim_id = item.get' scripts/report/adversarial_review_runner.py
```

### D2 — minor — B 类 — labels 使用篇承诺分析产物落 labels_meta，但列出的 SOL 两入口未写该字段

- 位置甲：[references/labels/README.md:8](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/README.md:8) 原文「SOL `replay_edges.py`/`build_evolution.py`（阵营体检）均已默认接入」以及同句末尾「分析产物落 `labels_meta`」。
- 位置乙：[scripts/solana/replay_edges.py:684](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/replay_edges.py:684) 原文「`json.dump(series, open("data/camp_share_series.json", "w"))`」；[scripts/solana/build_evolution.py:188](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/build_evolution.py:188) 原文「`json.dump(series, f, ensure_ascii=False, indent=1)`」。后者第 190–205 行另写 input manifest，前者第 706–712 行、后者第 211–218 行另写序列 sidecar，均未传入 labels 元信息。
- 反向验证：两个 SOL 脚本中 `labels_meta` 字符串和 `.meta()` 调用均为 0；共享 sidecar 构造器 [scripts/lib/camp_series_provenance.py:147](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/camp_series_provenance.py:147) 的输出字段也没有该项。EVM 的 `cluster.py:227` 明写 `labels_meta`，`analyze_holdings.py:251` 明写独立的 `{chain}_labels_meta.json`，因此不是字段别名。
- 矛盾点：文档将已实现于 EVM 的落盘行为无条件覆盖到 SOL，执行者会误以为 SOL 分析产物已留存标签库元信息。这属于明确输出承诺未实现。
- 修法建议：优先**删除**无条件的「分析产物落 `labels_meta`」；如保留，应限定到对应 EVM 入口。
- 复现：第一条对两个 SOL 文件无输出；其余命令显示实际写出点。

```sh
rg -n 'labels_meta|[.]meta[(]' scripts/solana/replay_edges.py scripts/solana/build_evolution.py
rg -n 'json.dump|write_series_sidecar|manifest =|doc =' scripts/solana/replay_edges.py scripts/solana/build_evolution.py scripts/lib/camp_series_provenance.py
rg -n 'labels_meta' references/labels/README.md scripts/evm/cluster.py scripts/evm/analyze_holdings.py
```

### D3 — minor — B 类 — Robinhood LP 字段承诺为币枚数，代码却固定除以 1e18

- 位置甲：[references/data-pipeline-robinhood-channels.md:33](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-channels.md:33) 原文「Mint/Burn/Collect 的 `amount0/amount1` 是**已解码浮点**（WETH 枚/本币枚），不是 wei」。
- 位置乙：[scripts/robinhood/pull_lp_events.py:92](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/robinhood/pull_lp_events.py:92) 原文「`"amount0": a0 / 1e18, "amount1": a1 / 1e18,`」。第 79–84 行从事件数据解码 raw 整数，第 37–44 行读取配置时没有读取两腿 decimals。
- 矛盾点：仅两腿都为 18 位精度时，这些值才是文档所说的枚数。源码表达式的内存复现中，6 位精度的 raw=1,000,000 应为 1 枚，实际输出 `1e-12`；按文档直接汇总会错算数量。
- 边界核验：同册第 5 行明确所有脚本仅用于 exploration，故不定为正式路径 blocker；探索档限定也不等于限定两腿必须为 18 位精度。
- 修法建议：**修改**「WETH 枚/本币枚」为「raw/1e18；仅两币均为 18 位精度时是枚数」，收窄单位承诺。
- 复现：

```sh
rg -n 'amount0/amount1|exploration' references/data-pipeline-robinhood-channels.md
rg -n 'decimals|a0, a1|amount0.*1e18|amount1.*1e18' scripts/robinhood/pull_lp_events.py
```

### D4 — minor — B 类 — Robinhood 成本脚本没有遵守显式 decimals=0 配置

- 位置甲：[references/data-pipeline-robinhood-channels.md:30](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-channels.md:30) 原文「本币和报价币分别使用 config 的 `decimals` / `quote_decimals`，不得再写死 18」。
- 位置乙：[scripts/robinhood/cost_engine.py:17](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/robinhood/cost_engine.py:17) 原文「`dec = int(cfg.get('decimals') or 18)`」；下一行报价币则使用「`cfg.get('quote_decimals') if cfg.get('quote_decimals') is not None else 18`」。
- 矛盾点：本币显式配置整数 0 会被 `or 18` 当作缺省值；报价币显式 0 则会保留。提取现行赋值表达式实际计算得到 `config.decimals=0 -> dec=18`。该 dec 后续用于第 19 行供应阈值和第 71、87 行枚数换算。这是探索脚本的配置默认值不符，与 D3 的 LP 固定单位是两个独立实现点。
- 修法建议：**修改**现有描述，明确「本币 decimals=0 或缺省时回退 18；报价币仅缺省时回退 18」，删除覆盖全部显式配置值的无条件承诺。
- 复现：以下只读取并计算 AST 中的赋值表达式，不加载业务脚本、不写文件；输出为 `18`。

```sh
rg -n 'cost_engine.py|quote_decimals' references/data-pipeline-robinhood-channels.md scripts/robinhood/cost_engine.py
python3 -B -c 'import ast,pathlib; t=ast.parse(pathlib.Path("scripts/robinhood/cost_engine.py").read_text()); n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=="dec" for x in n.targets)); print(eval(compile(ast.Expression(n.value),"<audit>","eval"),{"cfg":{"decimals":0}}))'
```

## 待确认（不计入 N）

**“对手方总数”是否要求跨方向去重。** [references/labels/MAINTENANCE.md:106](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/MAINTENANCE.md:106) 写「`FUNNEL_CANDIDATE` = 对手方总数≥120 且留存≤15%」；[scripts/labels/gatekeeper.py:96](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/labels/gatekeeper.py:96) 实际为「`p['fan_in'] + p['fan_out'] >= TH['CAND_DEG']`」。

内存复现：同一组 60 个对手各有入账、出账，留存 10%，得到 fan_in=60、fan_out=60、`FUNNEL_CANDIDATE`。但文档没有明确“总数”指两个方向分别去重后求和，还是合并地址后去重；现有证据足以证明实现口径，尚不足以证明文档采用另一口径，故不计发现。

复现：

```sh
rg -n '对手方总数|CAND_DEG|fan_in.*fan_out|peers_in|peers_out' references/labels/MAINTENANCE.md scripts/labels/gatekeeper.py
```

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | A 类 | references/research-workflows.md:125 | references/research-workflows.md:103；references/analyze-workflow.md:170 | 外部模板裸数组与 v2 对象格式冲突 |
| D2 | minor | B 类 | references/labels/README.md:8 | scripts/solana/replay_edges.py:684；scripts/solana/build_evolution.py:188 | SOL 产物未兑现 labels_meta 落盘承诺 |
| D3 | minor | B 类 | references/data-pipeline-robinhood-channels.md:33 | scripts/robinhood/pull_lp_events.py:92 | 固定 raw/1e18 被描述为通用币枚数 |
| D4 | minor | B 类 | references/data-pipeline-robinhood-channels.md:30 | scripts/robinhood/cost_engine.py:17 | 本币显式 decimals=0 被改成 18 |
