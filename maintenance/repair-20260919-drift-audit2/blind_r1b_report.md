# 盲审 R1b：6 条发现

审查基线：`d30864944462ae10db38ff7d3b1caaf9a96f9a01`；git status 前/后：空/空

覆盖声明：`main`，`VERSION=9.0.1`。全程离线只读；未读取 `~/.codex/`、禁读目录及 `attic.md` 正文，未新建或修改文件、未 commit。已核对 `SKILL.md:86` 对 attic 禁读身份的描述。上一轮台账仅阅读获准的 `code_change_pending.md`，未重报已裁决的 wave_scan 浮点阈值例外。

必审文档 46 份，另审 CHANGELOG 指定现行段，共 47 份。全部逐文件检索，对命中变更脚本、字段及行为的段落读取上下文：

- 根目录：`SKILL.md`；`CHANGELOG.md`。
- `references/`：`address-book.md`；`analysis-playbook.md`；`analyze-workflow.md`；`context-discipline.md`；`data-pipeline-evm-channels.md`；`data-pipeline-evm-recon.md`；`data-pipeline-evm-sources.md`；`data-pipeline-evm.md`；`data-pipeline-robinhood-channels.md`；`data-pipeline-robinhood-methods.md`；`data-pipeline-robinhood-traps.md`；`data-pipeline-robinhood.md`；`data-pipeline-solana-capture.md`；`data-pipeline-solana-scan.md`；`data-pipeline-solana.md`；`economic-control-accounting.md`；`environment.md`；`independent-audit-protocol.md`；`lp-fee-accounting.md`；`maintenance-review-repair.md`；`monitoring-package.md`；`playbook-entity-cluster-cost.md`；`playbook-entity-cluster-methods.md`；`playbook-entity-cluster-tiering.md`；`playbook-evidence-wording.md`；`playbook-state-anomaly.md`；`playbook-supply-recon.md`；`report-template.md`；`research-workflows.md`；`retrospective.md`；`scan-schemas.md`；`split-run.md`。
- `references/casebook/`：`README.md`；`cex-custody-methods.md`；`cex-custody.md`；`entity-clustering-methods.md`；`entity-clustering.md`；`supply-accounting-methods.md`；`supply-accounting.md`。
- `references/labels/`：`README.md`；`MAINTENANCE.md`。
- `commands-staging/`：`token-analyze.md`；`token-analyze-1.md`；`token-analyze-2.md`；`token-analyze-3.md`。

术语表条目数：**79**。检索顺序为“变更脚本名 → 函数名 → 字段/schema → 中文行为与旧口径”，反查链族、formal/exploration、历史叙述及合法 CLI 简写；检索排除 `attic.md` 和备份件。

指定 Git 差异确认：**38 个文件，+2806/−118**。其中生产文件 16 个：

- `scripts/evm/`：`accounting_gate.py`、`observe_supply.py`、`peaks_daily.py`、`replay_duck.py`。
- `scripts/lib/`：`camp_spec.py`、`evm_observation.py`、`net.py`、`rpc_batch.py`、`supply_truth_gate.py`。
- `scripts/prices/price_check.py`。
- `scripts/report/`：`audit_release_gate.py`、`entity_identity_gate.py`、`facts_gate.py`、`figures_from_facts.py`、`shared_release_receipt.py`、`stage2_closeout.py`。

另核对 `scripts/tests/` 下 22 个变更文件的登记、夹具及相关断言，并读取 `agents/openai.yaml`、`pyproject.toml`。运行核验采用现行函数/AST 与纯内存输入，没有运行需要落临时文件的完整测试套件。

覆盖复现命令：

```sh
git rev-parse HEAD
git status --short
git log --oneline 4cbfe48..HEAD -- scripts/
git diff --stat 4cbfe48..HEAD -- scripts/
git diff --name-only 4cbfe48..HEAD -- scripts/
rg -n '^## \[' CHANGELOG.md
```

增量机器行为核查清单：

| 版本 | 已核对的新行为、字段与拒收条件 |
|---|---|
| 7.2.0 | 图 2 拒非有限/非法 pct，输入解析失败时按条件尝试写 FAIL 收据，序列序列化禁 NaN；strict/expanded 位置金额分流并校验扩展区间；facts build 从三账、identity、provenance、facts_inputs 派生，校验输入类型、非有限数及峰值来源，生成 `facts-provenance/v1`，发布/收口重算，checks 11→12；日峰产物递归定位、needs 哈希绑定、候选并集须有 `block-precision-followup/v1`，`--only-addrs` 无门槛补算、零事件给 0/null、输出到首个输入目录、跳过全量产物，坏输入退出 2。 |
| 7.2.1 | `tier=exclude` 成员消费侧必须保留 `INFRA_IN_ENTITY`；图 2 发布期按实物重算；summary/needs/followup 任一定位产物根，缺 summary/多根拒，followup 核当前 producer、唯一 channels 实物、value_type、count；facts 峰值上界、override 证据内容相等、严格 ISO 日期及 current 日期约束、decimals 核验。 |
| 8.0.0 | 图 2 按四种 label 前缀确定必画实体，缺线/重复线拒，选材共用规则；EVM bundle v2 增冻结块 `decimals()`，uint8、9 笔 transcript，旧 v1 拒，`accounting.checks.decimals` 绑定 `bundle.supply.decimals`，发布侧核 facts/config decimals。 |
| 9.0.0 | RPC 缺 result 失败，显式 result:null 留给方法消费者判断；getcode 仅接受 0x/偶数十六进制，非法返回记 error、退出 1；价格收据要求引用、非空 points、来源及匹配的 `price_file_sha256`，重算 verdict，仅接 PASS/WARN，拒旧收据/纯申报/FAIL/ALL_SKIP；流通量输入为 `{raw,asof,source}`，核数值、日期及来源，拒扁平键，派生 token 字段并影响流转图选材。 |
| 9.0.1 | EVM 显式“散户”配置退出 2，Solana 不套该禁令；主价格任一点非有限/非正退出 1，第二源非有限转 null/SKIP，收据禁 NaN，收口逐点重算 status 后核声明，5%/15% 阈值一致。 |

## 发现（按严重度排序）

### D1 — blocker — B 类 — 净室协议的钱包自持公式仍把 expanded 位置金额计入下限

- 位置甲：[references/independent-audit-protocol.md:162](/Users/uravvv/.claude/skills/token-chip-analysis/references/independent-audit-protocol.md:162) 原文「发布闸从明细重算 `wallet_self_held_raw == Σ position.amount_raw`」。同文件 :160 允许 membership 为「`strict|expanded|excluded`」，:161 的位置账要求映射到「同一实体的有效成员」，没有将 expanded 排除出位置账。
- 位置乙：[scripts/report/audit_release_gate.py:918](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:918) 原文「`if member_map.get(addr_key, ("", "", None))[1] == "expanded":`」，:919 原文「`expanded_by_entity[entity] = expanded_by_entity.get(entity, 0) + amt`」；只有 else 分支 :921 执行「`wallet_by_entity[entity] += amt`」，:944 按该结果核 wallet。
- 矛盾点：文档要求汇总全部有效成员的位置金额，代码要求钱包自持仅计 strict。照文档把 strict=100、expanded=200 填成 wallet=300，会高估可证下限并被拒收。纯内存核验：同一输入在 `4cbfe48` 无错误，HEAD 报「钱包自持与位置账不闭合: 300 != 100」；改为 wallet=100 后通过。
- 修法建议：只修改原公式为“Σ strict 成员的 position.amount_raw”，与 `economic-control-accounting.md:40` 的严格下限定义对齐。
- 复现：

```sh
rg -n 'wallet_self_held_raw ==|membership.*strict|position_ledger.json.entries' references/independent-audit-protocol.md
rg -n -A5 'if member_map.get\(addr_key' scripts/report/audit_release_gate.py
rg -n -A3 'if wallet != wallet_by_entity' scripts/report/audit_release_gate.py
```

### D2 — blocker — B 类 — state_source 的排他性字段说明与 facts build 必填输入冲突

- 位置甲：[references/report-template.md:203](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:203) 原文「`facts.json` 唯一拥有 entity_id/label/成员/current_raw/peak_raw；`state_source.json` 只承载它没有的分析时点、实体 type/status、逐址快照余额、vault 与 provenance」。
- 位置乙：[scripts/report/facts_gate.py:357](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:357) 原文「`fi = source.get(FACTS_INPUTS_KEY)`」，:358–359 为「`if not isinstance(fi, dict):`」「`raise ValueError(f"state_source 缺 {FACTS_INPUTS_KEY} 对象")`」；:369–371 明确读取并要求非空的「`labels = fi.get("entity_labels")`」。
- 矛盾点：新生产链必须先在 state_source.facts_inputs 中声明 symbol、decimals 和 entity_labels，随后生成 facts。按“只承载 facts 没有的字段”装配 source 会缺必填输入，build 中止。纯内存调用已得到「state_source 缺 facts_inputs 对象」。
- 修法建议：删除“唯一拥有／只承载它没有的”这组过时排他句，改为说明 facts 是生成结果、人工声明复用 state_source.facts_inputs；schema 继续指向现有 docstring，不复制字段全集。
- 复现：

```sh
rg -n '唯一拥有|只承载' references/report-template.md
rg -n -F -A20 'fi = source.get(FACTS_INPUTS_KEY)' scripts/report/facts_gate.py
```

### D3 — blocker — B 类 — 人工对图回退仍被写成可完成价格检查的路径

- 位置甲：[references/report-template.md:278](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:278) 原文「双源都无该币（Robinhood 链类）exit 3 回退人工对 Dexscreener 图」。
- 位置乙：[scripts/report/stage2_closeout.py:294](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:294) 原文「`if expected not in ("PASS", "WARN"):`」，:296 拒收文案为「PASS|WARN（FAIL/ALL_SKIP 禁入装配：换源或人工裁决后重跑 price_check）」。
- 矛盾点：exit 3 对应 ALL_SKIP，人工看图不能使它通过现行正式 −2 收口，照清单回退后仍跑不通。括号是链示例，原句没有限定 exploration；`CHANGELOG.md:116` 也明确记载该回退失效、四条正式候选链均可能遇到。纯内存收口校验已确认 ALL_SKIP 被拒。
- 修法建议：删除正式路径的人工对图回退许可，将尾句改为“exit 3 换源重跑；正式 −2 仅接 PASS/WARN”。
- 复现：

```sh
rg -n -F 'exit 3 回退人工' references/report-template.md
rg -n -F -A8 'expected = ("FAIL"' scripts/report/stage2_closeout.py
rg -n -F -A2 'if verdict == "ALL_SKIP"' scripts/prices/price_check.py
```

### D4 — blocker — B 类 — peak_share 宏仍被保证为日末峰值，但会直接输出合法 override 的峰值

- 位置甲：[references/report-template.md:215](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:215) 原文「`{{e.peak_share}}` 只代表日末序列峰值；日内事件占比禁用宏」。
- 位置乙：[scripts/report/facts_gate.py:441](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:441) 原文「`peak = _raw_str(ov.get("peak_raw"), f"peak_overrides.{eid}.peak_raw")`」，:480 写入「`ent["peak_raw"] = peak`」；:131–132 的宏分支为「`if field == "peak_share":`」「`return fmt_pct(peak, self.total_raw)`」。
- 矛盾点：宏读取最终 peak_raw，不会另取日末峰值。合法 override 可替换 provenance 锚点，`CHANGELOG.md:146` 还明确记录“A4 块粒度峰值经 override 路径”复现。纯内存核验中，锚点 150/1000 产生 15.00%，合法 override=160 后同一宏产生 16.00%；继续保证它是日末值会错标粒度。
- 修法建议：将原宏边界句改为“代表 facts 所绑定的峰值，粒度按峰值来源声明”，删除绝对的“只代表日末”与“日内禁用宏”承诺；需要并列时分别提供日末、日内数据。
- 复现：

```sh
rg -n -F '宏口径边界' references/report-template.md
rg -n -F 'peak = _raw_str(ov.get("peak_raw")' scripts/report/facts_gate.py
rg -n -F -A2 'if field == "peak_share"' scripts/report/facts_gate.py
rg -n -F 'A4 块粒度峰值经 override' CHANGELOG.md
```

### D5 — minor — A 类 — 9.0.0 同一条目同时把主价格哈希写成必填和可选

- 位置甲：[CHANGELOG.md:117](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:117) 原文「新增产物输出键 3（收据 `price_file_sha256` 1；facts `token.circulating_supply_raw`、`token.circulating_supply_source` 2，均可选）」。
- 位置乙：[CHANGELOG.md:112](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:112) 原文「`price_file_sha256` 在场且等于 `bindings.price_source.sha256`」；现行代码 `scripts/report/stage2_closeout.py:300–303` 也明确拒绝该字段缺失。
- 矛盾点：“均可选”包含实际必填的收据哈希，会让收据构造或迁移者误以为可以省略；两句属于同一个 9.0.0 条目，不是不同历史版本的规则变迁。
- 修法建议：删除“均可选”，或将“可选”仅限定到流通量两字段。
- 复现：

```sh
rg -n '新增产物输出键 3|price_file_sha256.*在场且等于' CHANGELOG.md
rg -n -F -A6 'bound = receipt.get("price_file_sha256")' scripts/report/stage2_closeout.py
```

### D6 — minor — B 类 — “每次 check 都落收据”与格式拒绝分支不符

- 位置甲：[references/report-template.md:222](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:222) 原文「每次 check（PASS/FAIL、formal/exploration）都落 `figure2_check_receipt.json` 留痕收据」。
- 位置乙：[scripts/report/figures_from_facts.py:381](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py:381) 原文「`if errs and errs[0] == "--series 应为图 2 whale_series JSON（list of lines）":`」，:382 为「`raise SystemExit("FAIL: " + errs[0])`」；通常的 FAIL 收据写入到 :386 才执行。
- 矛盾点：两输入可读，但 series 顶层是对象而非数组时，命令 FAIL 退出且不写收据。真实 fig2_check_errors 与 mode_check 的纯内存联调已确认该输入退出、收据写入调用次数为 0。
- 修法建议：收窄原文为“终值对账结果（PASS/FAIL）落收据，格式/政策前置拒绝除外”。本项在 `4cbfe48` 已存在，是沿改动脚本回查发现的既存不符，不归因于本区间新增代码。
- 复现：

```sh
rg -n -F '每次 check' references/report-template.md
rg -n -F -A2 'if not isinstance(series, list):' scripts/report/figures_from_facts.py
rg -n -F -A8 'if errs and errs[0] ==' scripts/report/figures_from_facts.py
git show 4cbfe48:scripts/report/figures_from_facts.py | rg -n -F -A2 'if errs and errs[0] =='
```

## 待确认（不计入 N）

`CHANGELOG.md:15` 的「缺线/重复线/空 series 一律拒」可能被读成无条件拒空数组；同文件 :122 明确「既有非必画实体（观察实体/默认 label）的空 series 绿例保持绿」。现行 `figures_from_facts.py:351–356` 按必画集合缺失才报错；纯内存核验“观察实体＋空数组”为 `errors=[]`。

但索引前半句已给出四类标签条件，可以解释为条件内的简写，故不直接计为漂移。

```sh
rg -n '空 series 一律拒|非必画实体.*空 series' CHANGELOG.md
```

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | blocker | B 类 | references/independent-audit-protocol.md:162 | scripts/report/audit_release_gate.py:918 | 钱包自持公式未排除 expanded |
| D2 | blocker | B 类 | references/report-template.md:203 | scripts/report/facts_gate.py:357 | source 排他说明与必填 facts_inputs 冲突 |
| D3 | blocker | B 类 | references/report-template.md:278 | scripts/report/stage2_closeout.py:294 | 人工对图不能替代正式价格收据 |
| D4 | blocker | B 类 | references/report-template.md:215 | scripts/report/facts_gate.py:441 | 峰值宏不保证日末粒度 |
| D5 | minor | A 类 | CHANGELOG.md:117 | CHANGELOG.md:112 | 主价格哈希被同时标必填与可选 |
| D6 | minor | B 类 | references/report-template.md:222 | scripts/report/figures_from_facts.py:381 | 格式拒绝不保证落收据；既存不符 |
