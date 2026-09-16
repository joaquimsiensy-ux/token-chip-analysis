<!-- 由 Fable 从 codex 只读盲审任务 task-mu4cvggl-zkykzc 的 Final output 段原样搬运;codex 沙箱只读无法自行落盘 -->
# 盲审 R2：8 条发现

审查基线：`445d7acf996c287b78250bb7c8a64614ecf13c36`；git status 前/后：空/空；结束时 HEAD 未变。

本轮：**2 blocker、5 minor、1 nit**。全部为 R1 未报的既有问题；对照 R1 施工前提交 `402b571`，相关矛盾两侧均已存在，未确认“R1 修复引入”的问题。R1 已修条目与 `code_change_pending.md` 的已知 D1 不重报。

**纪律披露：**全程离线，未修改或新建文件，未 commit。启动上下文已自动包含历史摘要，未打开 `~/.codex/` 下文件。行数统计时误用过 `wc -l references/*.md`，使 `attic.md` 被读取用于计数；未展示或引用正文，但这仍违反了禁读要求。后续读取均显式排除该文件。

覆盖声明：46 份必审文档，共 6,563 行；另查 `CHANGELOG.md` 现行规则文字、`agents/openai.yaml`、`pyproject.toml`。临时术语索引为 **2,080 个去重非空反引号片段**，包含命令、字段、schema 和产物名。全文检索后回读规则上下文；对 310 个 Python 文件静态抽取 CLI、常量和字段，再核对命中处的实际解析、读取与输出。未重跑已知通过的九项守卫。

相对 R1 加深核对：Robinhood 输入格式与配置默认值、V4 费率方向、复盘回灌范围、复现命令参数流向、扫描产物公共字段、标签维护命令的工作目录；并核对监控包、Solana、案例库、章节引用与 R1 文本差异。

文档清单：

```text
SKILL.md
references/address-book.md
references/analysis-playbook.md
references/analyze-workflow.md
references/context-discipline.md
references/data-pipeline-evm.md
references/data-pipeline-evm-channels.md
references/data-pipeline-evm-recon.md
references/data-pipeline-evm-sources.md
references/data-pipeline-robinhood.md
references/data-pipeline-robinhood-channels.md
references/data-pipeline-robinhood-methods.md
references/data-pipeline-robinhood-traps.md
references/data-pipeline-solana.md
references/data-pipeline-solana-capture.md
references/data-pipeline-solana-scan.md
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
references/casebook/cex-custody.md
references/casebook/cex-custody-methods.md
references/casebook/entity-clustering.md
references/casebook/entity-clustering-methods.md
references/casebook/supply-accounting.md
references/casebook/supply-accounting-methods.md
references/labels/README.md
references/labels/MAINTENANCE.md
commands-staging/token-analyze.md
commands-staging/token-analyze-1.md
commands-staging/token-analyze-2.md
commands-staging/token-analyze-3.md
```

## 发现（按严重度排序）

以下复现命令均从仓库根目录执行，只读文件。

### D1 — blocker — A 类 — V4 手续费公式把输出腿当成输入腿

- **位置甲：**[references/lp-fee-accounting.md:62](/Users/uravvv/.claude/skills/token-chip-analysis/references/lp-fee-accounting.md:62) 原文「`gross_input_j = 正数一侧的 amount0 或 amount1`」，下一行用它乘费率。
- **位置乙：**[references/data-pipeline-robinhood-traps.md:53](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-traps.md:53) 原文「a1>0=池流出=用户买入」，并要求「必须用实 tx 的同 tx Transfer 校准符号」。
- **矛盾点：**两处都指 V4 Swap 事件；一处把正数认作输入，另一处明确正数是池子输出。照前者算费会使用错误方向及币种的数量。
- **修法建议：**修改公式为“经方向校准后的输入腿负值绝对值”；保留现有动态费、协议费与 hook 限定。只改文本。
- **复现：**

```sh
nl -ba references/lp-fee-accounting.md | sed -n '56,68p'
nl -ba references/data-pipeline-robinhood-traps.md | sed -n '51,53p'
```

### D2 — blocker — B 类 — “本案回灌”命令实际扫描固定历史根目录

- **位置甲：**[references/retrospective.md:102](/Users/uravvv/.claude/skills/token-chip-analysis/references/retrospective.md:102) 原文「`python3 scripts/labels/accumulate_offenders.py --apply`」及「本案庄家实体回灌惯犯库」。
- **位置乙：**[scripts/labels/accumulate_offenders.py:43](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/labels/accumulate_offenders.py:43) 原文「`DEFAULT_ROOT = os.path.expanduser('~/Desktop/老公用/fable筹码分析')`」；[204 行](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/labels/accumulate_offenders.py:204) 为「`glob.glob(os.path.join(root, '*', fname))`」，226 行为「`root = args[0] if args else DEFAULT_ROOT`」。
- **矛盾点：**示例未传根目录，代码枚举固定根目录下所有案件。317–319 行又把生成结果交给 `add_labels.py` 入库，不能保证只回灌本次复盘确认的案件；当前案在其他目录时也可能完全未被扫描。
- **实证：**仅抽取参数解析与目录枚举函数在内存执行，默认根目录确为上述 Desktop 路径；合成两案列表均被选中。没有访问该历史目录或实际入库。
- **修法建议：**删除无案范围的 `--apply` 示例，改指既有手工入库流程：只把本次复盘确认的地址、标签和证据整理为独立 CSV，再调用 `add_labels.py`。只改文本；不能把父目录批扫参数冒充单案参数。
- **复现：**

```sh
nl -ba references/retrospective.md | sed -n '97,103p'
nl -ba scripts/labels/accumulate_offenders.py | sed -n '43p;200,206p;209,230p;317,319p'
```

### D3 — minor — B 类 — 报价小时线被写成 dict，现行引擎要求二维 list

- **位置甲：**[references/data-pipeline-robinhood-channels.md:34](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-channels.md:34) 原文「cost_engine 的 quote_usd_hour.json 是 dict」。
- **位置乙：**[scripts/robinhood/cost_engine.py:30](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/robinhood/cost_engine.py:30) 原文「`q_ts = [r[0] for r in qk]`」；31 行将首项与整数比较，35 行原文「`return qk[i][4]`」。5 行也声明「`[[ts,o,h,l,c],...]`」。
- **矛盾点：**JSON 对象的键是字符串，按文档准备非空 dict 后，代码迭代得到字符串键，不能作为二维 K 线列表使用。
- **实证：**在内存执行现行 30–35 行，dict 输入触发 `TypeError: '>' not supported between instances of 'str' and 'int'`；二维 list 对照输入正常返回收盘价 2000。
- **修法建议：**把 dict 改为 `[[ts,o,h,l,c],...]`，说明它与 LP 脚本的 `[[ts_ms,close],...]` 都是 list，但列结构不同。只改文本。
- **复现：**

```sh
nl -ba references/data-pipeline-robinhood-channels.md | sed -n '33,34p'
nl -ba scripts/robinhood/cost_engine.py | sed -n '4,5p;29,35p'
```

### D4 — minor — B 类 — 复现命令中的控制器选项被转发给案内脚本

- **位置甲：**[references/independent-audit-protocol.md:105](/Users/uravvv/.claude/skills/token-chip-analysis/references/independent-audit-protocol.md:105) 原文先写「`python3 scripts/report/reproduce_receipt.py <案目录>`」，下一行接「`--output reproduce_output.json --receipt reproduce_receipt.json`」。
- **位置乙：**[scripts/report/reproduce_receipt.py:58](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/reproduce_receipt.py:58) 原文「`ap.add_argument("script_args", nargs=argparse.REMAINDER,`」；[98 行](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/reproduce_receipt.py:98) 原文「`subprocess.run([sys.executable, str(entry)] + script_args, cwd=case_dir,`」。
- **矛盾点：**`case_dir` 后面的词被 `REMAINDER` 全收走，示例中的两项并未设置控制器输出路径，而是原样传给 `reproduce_audit.py`。示例值恰与默认值相同，掩盖了参数流向错误；案内脚本是否拒绝多余参数取决于其实现。
- **实证：**抽取现行 parser 执行，`script_args` 为 `['--output','reproduce_output.json','--receipt','reproduce_receipt.json']`；只传案目录时该数组为空。
- **修法建议：**优先删除与默认值相同的两项，仅保留案目录；确需自定义时，把控制器选项放到案目录之前。只改文本。
- **复现：**

```sh
nl -ba references/independent-audit-protocol.md | sed -n '98,107p'
nl -ba scripts/report/reproduce_receipt.py | sed -n '53,60p;81,99p'
```

### D5 — minor — B 类 — “公共字段各产物一律在场”不符合分布扫描输出

- **位置甲：**[references/scan-schemas.md:17](/Users/uravvv/.claude/skills/token-chip-analysis/references/scan-schemas.md:17) 原文「公共通用字段（`schema/generated_at/params/total_supply_raw/edges/note`）各产物一律在场」。
- **位置乙：**[scripts/report/holder_distribution_scan.py:710](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/holder_distribution_scan.py:710) 原文「`return {"schema": SCHEMA, "stage": stage, "generated_at_utc": utcnow(),`」；866 行的失败输出也使用 `generated_at_utc`。
- **矛盾点：**本文件登记的 `distribution-scan/v2` 生产者使用 `generated_at_utc`，没有承诺的 `generated_at`。已核对返回值展开来源 `analyze()`，其中也没有补入该键。
- **修法建议：**删除“各产物一律在场”的公共字段包办句，字段以各 schema 和现行生产者为准。只改文本。
- **复现：**

```sh
nl -ba references/scan-schemas.md | sed -n '12,17p'
nl -ba scripts/report/holder_distribution_scan.py | sed -n '710,716p;864,870p'
rg -n 'generated_at' scripts/report/holder_distribution_scan.py
```

### D6 — minor — B 类 — LP 采集被写成不读池配置，代码实际提供配置回退

- **位置甲：**[references/data-pipeline-robinhood-channels.md:33](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-channels.md:33) 原文「不读 config.json 的池子配置，必须命令行传参 `--from-block N --pools 0x主池 --out data/lp_events.jsonl`」。
- **位置乙：**[scripts/robinhood/pull_lp_events.py:32](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/robinhood/pull_lp_events.py:32) 原文「`ap.add_argument("--pools", default=None, help="逗号分隔池地址；缺省取 config.pools")`」；44 行原文「`pools = [p.lower() for p in (cfg.get("pools") or {})]`」。
- **矛盾点：**`--pools` 可省略，实际读取 `config.pools`；46 行只在 CLI 与配置都无池地址时失败。文档所称“不读配置、必须传 --pools”与默认行为相反。
- **修法建议：**删除“不读配置”与“--pools 必传”的断言，保留 `--from-block` 必填，注明 CLI 池列表优先于配置。只改文本。
- **复现：**

```sh
nl -ba references/data-pipeline-robinhood-channels.md | sed -n '33p'
nl -ba scripts/robinhood/pull_lp_events.py | sed -n '28,46p'
```

### D7 — minor — A 类 — 标签维护示例的工作目录前后不一致

- **位置甲：**[references/labels/MAINTENANCE.md:52](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/MAINTENANCE.md:52) 原文「在 `scripts/labels/` 目录执行」。
- **位置乙：**[references/labels/MAINTENANCE.md:86](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/MAINTENANCE.md:86) 先写「`cd sources && python3 ../add_labels.py my_additions.csv`」，下一行又写「`python3 ../accumulate_offenders.py && cd sources && python3 ../add_labels.py serial_actors.csv`」。
- **矛盾点：**顺序执行时，第一行已进入 `sources/`，第二行再进入 `sources/` 就指向不存在的 `sources/sources/`；若第二行单独从约定的 `scripts/labels/` 执行，`../accumulate_offenders.py` 又指向错误目录。已只读核实嵌套目录不存在。
- **修法建议：**第一行的 `cd` 放入子 shell；第二行从 `scripts/labels/` 调用 `python3 accumulate_offenders.py`，再用子 shell 进入 `sources/` 执行入库。只修改两行命令文本。
- **复现：**

```sh
nl -ba references/labels/MAINTENANCE.md | sed -n '50,56p;83,88p'
python3 -B -c 'from pathlib import Path; print(Path("scripts/labels/sources").is_dir(), Path("scripts/labels/sources/sources").is_dir())'
```

### D8 — nit — A 类 — CEX 封闭盘识别指向不存在的分册 §6

- **位置甲：**[references/playbook-state-anomaly.md:36](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-state-anomaly.md:36) 原文「识别三角（充提开关+多所现价+链上池价）见 data-pipeline-evm-sources §6 表」。
- **位置乙：**[references/data-pipeline-evm-sources.md:9](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-sources.md:9) 原文「## 4. 辅助数据面速查表」；26 行表项为「CEX 封闭盘识别三角」。该分册目录列出的节号是 §4/§8/§9/§10。
- **矛盾点：**被指向分册没有 §6，对应表项实际在 §4。
- **修法建议：**将引用改为该分册“CEX 封闭盘识别三角”表项，删除错误节号。只改文本。
- **复现：**

```sh
rg -n '识别三角|^## |^### ' references/playbook-state-anomaly.md references/data-pipeline-evm-sources.md
```

## 待确认（不计入 N）

**监控包的“正式枚举”是否仅表示兼容读取值。**

[references/monitoring-package.md:43](/Users/uravvv/.claude/skills/token-chip-analysis/references/monitoring-package.md:43) 写「chain 小写正式枚举：bsc / eth / base / sol / robinhood」，而 [SKILL.md:12](/Users/uravvv/.claude/skills/token-chip-analysis/SKILL.md:12) 写「Robinhood EVM 仅保留 exploration 支持」及「两链均不得进入正式交接或审计发布路径」。

前者可能是在定义历史监控数据的合法字段值，尚不能直接等同正式发布链支持范围，因此不计为确定漂移。建议明确“可读取的历史值”与“当前可新发监控包的链”各自含义。

```sh
nl -ba references/monitoring-package.md | sed -n '41,44p'
nl -ba SKILL.md | sed -n '9,13p'
```

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | blocker | A | references/lp-fee-accounting.md | references/data-pipeline-robinhood-traps.md | V4 输入腿符号相反 |
| D2 | blocker | B | references/retrospective.md | scripts/labels/accumulate_offenders.py | 本案回灌实际跨案批扫 |
| D3 | minor | B | references/data-pipeline-robinhood-channels.md | scripts/robinhood/cost_engine.py | dict 与二维 list 输入冲突 |
| D4 | minor | B | references/independent-audit-protocol.md | scripts/report/reproduce_receipt.py | 控制器选项进入子脚本参数 |
| D5 | minor | B | references/scan-schemas.md | scripts/report/holder_distribution_scan.py | 公共字段必备承诺不成立 |
| D6 | minor | B | references/data-pipeline-robinhood-channels.md | scripts/robinhood/pull_lp_events.py | 池配置默认读取行为相反 |
| D7 | minor | A | references/labels/MAINTENANCE.md | 同文件 | 命令 cwd 连续性错误 |
| D8 | nit | A | references/playbook-state-anomaly.md | references/data-pipeline-evm-sources.md | §6 引用应指 §4 表项 |
