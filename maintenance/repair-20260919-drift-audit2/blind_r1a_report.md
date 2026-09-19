# 盲审 R1a：5 条发现

审查基线：`d30864944462ae10db38ff7d3b1caaf9a96f9a01`；分支 `main`；`VERSION=9.0.1`；git status 前/后：空/空。

全程离线、只读，未修改或新建文件，未 commit，未读取禁读区或 `attic.md` 正文。

覆盖声明：必审文档 46 份、6,564 行，逐文件检索并读取规范性命中及候选上下文；另审 `CHANGELOG.md` 文件头版本规则、7.2.0–9.0.1 活跃条目的现行行为描述。核心术语表共 **260 项**，按类别内去重：阶段 11、门禁 16、schema/协议 21、脚本 33、CLI 参数 41、产物 92、阈值 19、角色/链/档位 12、子命令 15；门禁计数包含缩写展开项。

检索策略：从三份核心文档提取术语，在全部必审文档中交叉搜索；核对文档点名的 124 个现存生产/辅助脚本及 6 个测试/守卫脚本，对候选读取参数定义、分派、写出点和消费者。解析了 `scripts/` 下 310 份 Python 文件的 AST，并进行了不落盘的函数级复现。另核对 `agents/openai.yaml`、`pyproject.toml`。已排除历史状态、明确的 exploration/legacy 差异及上一轮已裁决的 wave_scan 浮点例外。

逐文件清单：

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
CHANGELOG.md（上述限定范围）
```

## 发现（按严重度排序）

### D1 — blocker — B 类 — 价格双源不可得时的人工回退已无法完成正式收口

- 位置甲：[references/report-template.md:278](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:278) 原文「双源都无该币（Robinhood 链类）exit 3 回退人工对 Dexscreener 图」。
- 位置乙：[scripts/report/stage2_closeout.py:294](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:294) 原文「`if expected not in ("PASS", "WARN"):`」；第 296 行错误原文「PASS|WARN（FAIL/ALL_SKIP 禁入装配：换源或人工裁决后重跑 price_check）」。
- 矛盾点：人工看图不会把 ALL_SKIP 收据变成 PASS/WARN，执行者按模板回退后仍无法完成 −2 收口。内存调用现行消费者已复现 BLOCK；[scripts/tests/test_stage2_closeout.py:655](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_closeout.py:655) 也明确写「全 SKIP → ALL_SKIP 退出 3；绑定后 BLOCK」。反向核验：[CHANGELOG.md:116](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:116) 明确指出四条正式候选链均可能命中，并非仅 Robinhood 探索档差异。
- 修法建议：修改原回退分句为“exit 3 不可完成正式分段收口，须换源并重跑取得 PASS/WARN 收据”。无需改代码。
- 复现：

```bash
rg -n 'exit 3 回退' references/report-template.md
rg -n 'expected not in|FAIL/ALL_SKIP' scripts/report/stage2_closeout.py
rg -n '全 SKIP|ALL_SKIP.*不再能进' scripts/tests/test_stage2_closeout.py CHANGELOG.md
```

### D2 — blocker — B 类 — 峰值宏已可承载块粒度覆盖值，模板仍将其定义为日末峰值

- 位置甲：[references/report-template.md:215](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:215) 原文「`{{e.peak_share}}` 只代表日末序列峰值；日内事件占比禁用宏」。
- 位置乙：[scripts/report/facts_gate.py:441](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:441) 原文「`peak = _raw_str(ov.get("peak_raw"), f"peak_overrides.{eid}.peak_raw")`」；第 480 行「`ent["peak_raw"] = peak`」；[第 131–132 行](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:131)「`if field == "peak_share":`」「`return fmt_pct(peak, self.total_raw)`」。
- 矛盾点：宏直接渲染 override 写入的峰值，不保证它来自日末序列；照模板解释会把块粒度峰值误称为日末峰值。反向核验：[CHANGELOG.md:146](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:146) 明确记录「另两处 A4 块粒度峰值经 override 路径 3/3 复现」，因此不是对任意输入的推测，也不是探索档特例。
- 修法建议：修改“只代表日末序列峰值／日内禁用宏”为“宏跟随 facts 中已绑定峰值来源的粒度，报告据来源标明日末或块粒度”，保留两种口径分别披露的要求。
- 复现：

```bash
rg -n '宏口径边界|逐事件重放值手写' references/report-template.md
rg -n 'ov = overrides|peak = _raw_str|ent\["peak_raw"\]|field == "peak_share"|fmt_pct\(peak' scripts/report/facts_gate.py
rg -n 'A4 块粒度峰值经 override' CHANGELOG.md
```

### D3 — blocker — B 类 — 现行预筛线已降至 0.1%／0.2%，脚本默认仍是总供应 1%

- 位置甲：[references/data-pipeline-evm-recon.md:136](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-recon.md:136) 原文「现行判级体系的最低线＝其他大户线（0.1% 总供应 / 0.2% 流通，权威见 tiering §6a，两口径换算后取更低枚数）」；同一行又明确「今按 1% 预筛会把 0.1%–1% 区间候选不可逆滤掉」。
- 位置乙：[scripts/evm/peaks_daily.py:89](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/peaks_daily.py:89) 原文「`ap.add_argument("--pct", type=float, default=0.01, help="候选门槛（占总供应），默认 1%%")`」；第 97 行「`th = int(TOT * a.pct)`」；[第 121 行](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/peaks_daily.py:121)「`SELECT t2 a FROM ev GROUP BY t2 HAVING SUM(v)::HUGEINT >= {th}`」。
- 矛盾点：使用该替代脚本的默认参数，会筛掉已满足文档最低线的地址。例如总供应 1,000,000、累计流入且仍持有 5,000 的地址占 0.5%，默认 SQL 门槛却为 10,000。参数默认值及该比较已在内存中复现。反向核验：[CHANGELOG.md:149](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:149) 已登记「P2 预筛 0.1% vs 1%」，但现行操作正文仍未说明必须覆盖脚本默认值。
- 修法建议：修改 §12c 现有调用说明，明确必须显式传入按两口径最低枚数换算的 `--pct`，不得沿用默认值；总供应口径为 `0.001`。这是调用文本修正，无需修改默认值代码。
- 复现：

```bash
rg -n '预筛线取|今按 1%' references/data-pipeline-evm-recon.md
rg -n -- '"--pct"|th = int|HAVING SUM' scripts/evm/peaks_daily.py
rg -n 'P2 预筛' CHANGELOG.md
```

### D4 — minor — B 类 — analysis-state 的“≤500 点”约定与现行序列编译行为不符

- 位置甲：[references/report-template.md:200](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:200) 原文「`camp_share_series`（≤500 点，重绘图 1 基线）」。
- 位置乙：[scripts/lib/camp_series_provenance.py:293](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/camp_series_provenance.py:293) 原文「`return {"dates": list(raw["dates"]), "series": series}`」；[scripts/report/state_from_facts.py:141](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/state_from_facts.py:141) 原文「`"camp_share_series": series,`」。
- 矛盾点：正式格式转换完整保留 producer 的日期和数值，状态编译器原样输出，不将序列限制为 500 点。内存复现中，501 点 `evm-dict` 序列通过数值校验并由 `compile_state` 输出 501 点。执行者若依模板手工抽稀，还会与现行来源绑定冲突：该编译器第 173–177 行要求手填序列与转换结果完全一致。
- 修法建议：删除状态文件说明中的“≤500 点”；保留已有 producer 序列同源要求。监控包的独立采样要求不因此改动。
- 复现：

```bash
rg -n '≤500 点' references/report-template.md
rg -n 'dates 原样|return \{"dates": list' scripts/lib/camp_series_provenance.py
rg -n '"camp_share_series": series|manual is not None|要么逐点相等' scripts/report/state_from_facts.py
```

### D5 — nit — A 类 — −2 命令指向不存在的 §3b.3 第⑤条

- 位置甲：[commands-staging/token-analyze-2.md:16](/Users/uravvv/.claude/skills/token-chip-analysis/commands-staging/token-analyze-2.md:16) 原文「交付收口时按 §3b.3 第⑤条自查申报」。
- 位置乙：[references/split-run.md:168](/Users/uravvv/.claude/skills/token-chip-analysis/references/split-run.md:168) 原文「`### 3b.3 −2 收口`」；第 170 行只有一段：「跑 `stage2_closeout --case-dir . --report 报告.md` 至 PASS……sealed/ 读取申报仍人工写进 `stage2_selfcheck`。」第 172 行已进入「`### 3b.4 −3 执行序与修错三分类`」。
- 矛盾点：被引用章节没有第⑤条，执行者无法找到指定编号；实际申报要求仍存在于该节正文。
- 修法建议：删除“第⑤条”，直接引用“§3b.3”。
- 复现：

```bash
rg -n '第⑤条' commands-staging/token-analyze-2.md
rg -n -A4 '^### 3b\.3' references/split-run.md
```

## 待确认（不计入 N）

**Q1 — “均可选”的修饰范围有歧义。**

[CHANGELOG.md:117](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:117) 原文「新增产物输出键 3（收据 `price_file_sha256` 1；facts `token.circulating_supply_raw`、`token.circulating_supply_source` 2，均可选）」。

[scripts/report/stage2_closeout.py:300](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:300) 读取 `price_file_sha256`，第 301–303 行明确拒绝缺失值，错误原文为「在场（旧收据无此字段：用当前 price_check.py 重跑）」。

如果“均可选”只修饰后两个 facts 字段，则没有矛盾；如果修饰全部三个新增字段，则价格收据字段的必填性描述错误。因语法范围不能唯一确定，不计入发现。可将原句改为“facts 两键可选”消歧。

```bash
rg -n '新增产物输出键 3' CHANGELOG.md
rg -n -A3 'bound = receipt.get' scripts/report/stage2_closeout.py
```

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | blocker | B 类 | references/report-template.md | scripts/report/stage2_closeout.py | 人工看图回退不能通过现行价格收口 |
| D2 | blocker | B 类 | references/report-template.md | scripts/report/facts_gate.py | 峰值宏可输出块粒度覆盖值 |
| D3 | blocker | B 类 | references/data-pipeline-evm-recon.md | scripts/evm/peaks_daily.py | 预筛默认 1% 高于现行最低线 |
| D4 | minor | B 类 | references/report-template.md | scripts/lib/camp_series_provenance.py；scripts/report/state_from_facts.py | 状态编译完整保留序列，不限 500 点 |
| D5 | nit | A 类 | commands-staging/token-analyze-2.md | references/split-run.md | §3b.3 不存在第⑤条 |
