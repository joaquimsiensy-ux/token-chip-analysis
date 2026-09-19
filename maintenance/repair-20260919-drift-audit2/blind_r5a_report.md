# 盲审 R5a：2 条发现

审查基线：`c6e01f3dd696d534fc7e9380825effb2f0edb588`；分支 `main`；VERSION=`9.0.1`；git status 前/后：**空/空**。

两条均为 **minor**，均在 R1 施工前已经存在；未确认 R1–R4 修复引入的新不一致。全程离线、只读，未读取 `~/.codex/`、memories 或其他禁读内容，未新建或修改文件。

覆盖声明：46 份必审文档共 6,564 行，逐文件审阅、全文检索；另核对 `CHANGELOG.md` 文件头版本规则及 7.2.0–9.0.1 活跃条目的现行行为描述。术语表从 SKILL、analyze-workflow、split-run 抽取，字面去重 **222 项**，在必审文档中检出 1,258 处；另定向检索数字阈值、角色和链支持档位。对照 `scripts/**`（含 tests）、`agents/openai.yaml`、`pyproject.toml`；以 argparse/分派、字段构造和实际写出点核验机器承诺，并建立 310 份 Python 源文件的静态索引。候选均回查上下文、前四轮台账及修复差异，排除历史、legacy、探索档和合法别名差异。

逐文件覆盖清单：

```text
SKILL.md
CHANGELOG.md（上述限定范围）
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
references/casebook/cex-custody-methods.md
references/casebook/cex-custody.md
references/casebook/entity-clustering-methods.md
references/casebook/entity-clustering.md
references/casebook/supply-accounting-methods.md
references/casebook/supply-accounting.md
references/labels/README.md
references/labels/MAINTENANCE.md
commands-staging/token-analyze.md
commands-staging/token-analyze-1.md
commands-staging/token-analyze-2.md
commands-staging/token-analyze-3.md
```

## 发现（按严重度排序）

### D1 — minor — A 类 — casebook 把“无签名”一律判为不可去重，与现行 Solana v4 交易身份规则冲突

- **位置甲**：[references/casebook/supply-accounting.md:36](/Users/uravvv/.claude/skills/token-chip-analysis/references/casebook/supply-accounting.md:36)，位于 S-04「必做区分检验」：原文「**无 sig 数据不得判重**」。同文件第 35 行另有「把无 sig 去重当无损」的禁止性表述。
- **位置乙**：[references/data-pipeline-solana-capture.md:158](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:158)：原文「SQD 不落盘签名不等于没有数据集内交易身份」；第 160–161 行接着规定「同一身份重复出现且 digest 相同／只留一份」。
- **矛盾点**：前者以“没有签名”为全面禁止条件，后者允许没有签名、但具有 `(slot,tx_index)` 和一致 `tx_digest` 的完整交易去重；执行者可能据 casebook 否定现行 v4 的合法去重。
- **反向验证**：甲侧是现行“必做”动作，没有限定旧五元组；乙侧第 162–163 行明确把禁止按五字段去重限定于旧五元组。代码 [spl_edge_core.py:63](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/spl_edge_core.py:63) 按交易身份分组，第 72–73 行仅在首次出现身份时保存。纯内存复算确认：同身份同内容两份输入保留一份；不同 `tx_index` 保留两份；同身份不同内容抛出 `RuntimeError`。
- **修法建议**：只改文本。将第 35–36 行过宽的“无 sig”限制收窄为“旧五元组不得按五字段去重”；细则继续引用现有 capture 分册，无须新增规则。
- **修复归因**：不是 Rn 修复引入；两份文档相关内容在 `3942c23..HEAD` 无变化。
- **复现**：

```bash
rg -n '无 sig|五元组|5 元组|tx_digest|只留一份' \
  references/casebook/supply-accounting.md \
  references/data-pipeline-solana-capture.md
nl -ba scripts/solana/spl_edge_core.py | sed -n '19,75p'
```

### D2 — minor — B 类 — bloXroute 入口已换成新脚本，操作说明仍承诺旧脚本的补扫、锚点和缓存行为

- **位置甲**：[references/data-pipeline-evm-channels.md:207](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:207)：原文「正式操作入口为 `scripts/evm/scan_bloxroute_seg.py`。旧 `scan_transfers.py` 仅保留历史/诊断用途」。
  
  紧随其后的第 208、210、211 行分别承诺：
  
  - 「扫完自动列 remaining 并补扫」
  - 「同脚本顺带采时间戳锚点」
  - 「`<chain>_scan_meta.json` 缓存 start_block/head，改 config 的 start_time_utc 后必须删除该文件才会重新二分」

- **位置乙**：[scripts/evm/scan_bloxroute_seg.py:26](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/scan_bloxroute_seg.py:26) 原文：

```python
ap.add_argument("--lo", type=int, required=True)
ap.add_argument("--hi", type=int, required=True, help="不含上界 [lo,hi)")
```

  第 45 行实际缓存路径为「`done_f = a.out + ".done.json"`」；第 81 行写出「`rows.append([int(lg["blockNumber"], 16), "", tx,`」，即时间戳留空；第 96–98 行将最终失败段加入 `fails`，第 108–109 行打印「`DONE segs=... fails=...`」后直接返回，没有扫完后的第二轮补扫。

- **矛盾点**：新入口由 CLI 显式提供块界，不读取所述起点缓存，不采集时间戳锚点，也没有文档承诺的收尾补扫阶段；执行者会期待不存在的产物，或沿用无效的缓存处理步骤。
- **反向验证**：旧脚本 [scan_transfers.py:71](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/scan_transfers.py:71) 确实使用 `<chain>_scan_meta.json`；第 165–180 行的 `mode_anchors` 才会调用 `eth_getBlockByNumber` 并写出锚点。这证明是入口与说明错配。bloXroute 的非正式通道档位已另行注明，本条没有把档位差异当作发现。
- **修法建议**：只改文本。删除第 208 行“自动收尾补扫”承诺及第 210–211 行旧脚本操作；需要保留操作提示时，压缩为“显式传 `--lo/--hi`；失败段重跑补采；ts 留空，锚点另采”。无需修改代码。
- **修复归因**：不是 Rn 修复引入；`3942c23..HEAD` 对该文档只修改了第 219 行 Multicall 参数说明，§3.3 未变。
- **复现**：

```bash
nl -ba references/data-pipeline-evm-channels.md | sed -n '205,212p'
nl -ba scripts/evm/scan_bloxroute_seg.py | sed -n '23,113p'
nl -ba scripts/evm/scan_transfers.py | sed -n '52,76p;165,181p'
git diff --no-ext-diff 3942c23 HEAD -- references/data-pipeline-evm-channels.md
```

## 待确认（不计入 N）

**KOGE 撤墙与下跌是否描述同一窗口。**

[references/playbook-state-anomaly.md:184](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-state-anomaly.md:184) 写「2026-04-22 撤墙后跌到 $30.48」；同文件第 194 行写「−54% 暴跌在 04-20、撤墙在 04-22，撤墙是事后止损不是诱因」。

两段存在时间顺序疑点，但文档没有明确 `$30.48` 与 `−54%` 对应同一段下跌，不能排除不同窗口。需原案价格序列与撤池回执确认，故不计发现。

```bash
rg -n '撤墙后跌|暴跌在 04-20' references/playbook-state-anomaly.md
```

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | A 类 | references/casebook/supply-accounting.md | references/data-pipeline-solana-capture.md | 无签名全面禁去重，与 v4 交易身份去重规则冲突 |
| D2 | minor | B 类 | references/data-pipeline-evm-channels.md | scripts/evm/scan_bloxroute_seg.py | 新采集入口仍配旧脚本的补扫、锚点及缓存说明 |
