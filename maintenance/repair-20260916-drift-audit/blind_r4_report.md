# 盲审 R4：4 条发现

审查基线：`388eed618c2426e476da30516f508dfe6fe9e782`；git status 前/后：空/空。结束时 HEAD 未变。

结果：**3 minor、1 nit**。四条均在工程开工提交 `4445443` 中已存在；对照前三轮报告、工单及修复差分，未确认“Rn 修复引入”的新问题。已修条目及 `code_change_pending.md` 的已知 D1 未重报。报告全文已打印到 stdout。

**审查纪律披露：**行数统计误用了 `wc -l references/*.md`，读取了禁读文件 `references/attic.md` 的字节以统计行数；未展示或引用其正文。这违反了禁读要求，本轮不能声称完全满足访问纪律。之后使用排除名单限定读取路径。启动上下文已有平台预载历史摘要，未主动读取 `~/.codex/` 文件，也未用摘要作发现依据。全程离线，未修改或新建工作区文件，未 commit。

## 覆盖声明

必审文档共 **46 份、6,564 行**；另核对 `CHANGELOG.md:3–9` 的现行规则：

- 仓库根目录：`SKILL.md`。
- references/ 通用文档（15）：`address-book.md`、`analysis-playbook.md`、`analyze-workflow.md`、`context-discipline.md`、`economic-control-accounting.md`、`environment.md`、`independent-audit-protocol.md`、`lp-fee-accounting.md`、`maintenance-review-repair.md`、`monitoring-package.md`、`report-template.md`、`research-workflows.md`、`retrospective.md`、`scan-schemas.md`、`split-run.md`。
- references/ 管线文档（11）：`data-pipeline-evm.md`、`data-pipeline-evm-channels.md`、`data-pipeline-evm-recon.md`、`data-pipeline-evm-sources.md`、`data-pipeline-robinhood.md`、`data-pipeline-robinhood-channels.md`、`data-pipeline-robinhood-methods.md`、`data-pipeline-robinhood-traps.md`、`data-pipeline-solana.md`、`data-pipeline-solana-capture.md`、`data-pipeline-solana-scan.md`。
- references/ 方法文档（6）：`playbook-entity-cluster-cost.md`、`playbook-entity-cluster-methods.md`、`playbook-entity-cluster-tiering.md`、`playbook-evidence-wording.md`、`playbook-state-anomaly.md`、`playbook-supply-recon.md`。
- references/casebook/（7）：`README.md`、`cex-custody.md`、`cex-custody-methods.md`、`entity-clustering.md`、`entity-clustering-methods.md`、`supply-accounting.md`、`supply-accounting-methods.md`。
- references/labels/（2）：`README.md`、`MAINTENANCE.md`。
- commands-staging/（4）：`token-analyze.md`、`token-analyze-1.md`、`token-analyze-2.md`、`token-analyze-3.md`。

术语表为 **1,341 个去重检索项**，来自反引号标识符、阶段编号及门禁编号。检索先定位同词、数字阈值、版本、参数、产物和章节引用，再区间对读两侧上下文；代码侧索引 310 个 Python 文件，对 155 个非测试脚本提取 CLI/常量并定向核对生产者、消费者。另核对 `agents/openai.yaml`、`pyproject.toml`。

相对前三轮新增的核对方向：A6 流程与版本分级；S-10 判例与图例豁免；同册 RPC 能力摘要与详细规则；解码缓存说明与实际分片路径。其他重点项也在当前 HEAD 独立复查：地址簿与 manual CSV 的 206 条记录、15 个字段投影差异为 0；环境依赖、维护及报告命令、schema、判例阈值和证据上限均作了对应核查。

以下复现命令均在仓库根目录执行，只读取文件或在内存中计算。

## 发现（按严重度排序）

### D1 — minor — A 类 — 判例要求图例数等于输入阵营数，与 Solana 烧毁桶豁免冲突

- 位置甲：[references/casebook/supply-accounting.md:82](/Users/uravvv/.claude/skills/token-chip-analysis/references/casebook/supply-accounting.md:82) 原文「出图后机械比较“图例条数＝传入阵营数”。」
- 位置乙：[references/report-template.md:298](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:298) 原文「`sol-rows` 豁免 `burn_cum_pct` 与「锁仓/销毁」（真烧毁轨，净供应分母外，图一按净供应标注、不堆叠仅在报告披露）」。
- 矛盾点：S-10 直接指向模板第 15 条，却要求无条件计数相等。合法 Solana 输入中的「锁仓/销毁」必须豁免，输入阵营数因此可以大于实绘阵营数。内存调用现行纯函数得到：输入「散户」「锁仓/销毁」两键，实绘仅「散户」，豁免「锁仓/销毁」，拒绝键为空。
- 修法建议：删除无条件计数等式，改为「按 report-template 第 15 条核验实绘集合、豁免键与图例收据」。只改文本。
- 复现：

```bash
nl -ba references/casebook/supply-accounting.md | sed -n '78,84p'
nl -ba references/report-template.md | sed -n '298p'
nl -ba scripts/report/standard_charts.py | sed -n '178,192p'
nl -ba scripts/lib/camp_series_provenance.py | sed -n '75,84p'
```

### D2 — minor — A 类 — A6 固定增加次版本，与按变更性质分级的版本约定冲突

- 位置甲：[references/analyze-workflow.md:198](/Users/uravvv/.claude/skills/token-chip-analysis/references/analyze-workflow.md:198) 原文「写入对应文件＋CHANGELOG 次版本＋1」。
- 位置乙：[references/retrospective.md:139](/Users/uravvv/.claude/skills/token-chip-analysis/references/retrospective.md:139) 原文「主版本=不兼容的工作流/schema/入口边界变更；次版本=向后兼容的新能力、新公开接口或持久化契约扩展（含分析复盘迭代）；修订号=既定契约内的修复、加固、回归补充与文档修订。」
- 矛盾点：A6 将所有获准复盘固定导向次版本；实际约定要求区分变更性质。例如仅修正文档应增加修订号，涉及不兼容入口变更应增加主版本。retrospective 第 4 步明确引用该约定，CHANGELOG 第 4 行也采用相同分级。
- 修法建议：将「CHANGELOG 次版本＋1」替换为「按 retrospective.md 的版本号约定更新 CHANGELOG」。只改文本。
- 复现：

```bash
nl -ba references/analyze-workflow.md | sed -n '196,198p'
nl -ba references/retrospective.md | sed -n '106,108p;137,140p'
nl -ba CHANGELOG.md | sed -n '3,5p'
```

### D3 — minor — A 类 — dataseed 历史状态同时被描述为浅窗口可查和一律拒绝

- 位置甲：[references/data-pipeline-evm-channels.md:227](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:227) 原文「**BSC dataseed**：eth_call 历史 state 窗口 **~128 块且节点池深浅抖动**」，并写「gate 的 rebase 两时点已收缩到 64 块保命中」。
- 位置乙：[references/data-pipeline-evm-channels.md:245](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:245) 同一 dataseed 坑表原文「getLogs 与历史状态一律被拒」。
- 矛盾点：同一类 BSC 节点的近端历史 `eth_call`，前者允许在浅窗口内查询，后者明确全部排除。这是手册内部的能力口径冲突；本轮未联网判定节点当前实际能力。
- 修法建议：删除「历史状态一律被拒」，改为「getLogs 被拒；历史 state 受浅窗口限制，范围及探测纪律见 §3.6」，保留实测时效说明。只改文本。
- 复现：

```bash
nl -ba references/data-pipeline-evm-channels.md | sed -n '225,232p;243,246p'
nl -ba scripts/evm/accounting_gate.py | sed -n '305,310p'
```

### D4 — nit — B 类 — 签名缓存并非固定 256 个分片

- 位置甲：[references/data-pipeline-solana-capture.md:169](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:169) 原文「跨地址共享 sig 缓存（`--cache-dir`,按 sig 前 2 字符 256 片）」。
- 位置乙：[scripts/solana/decode_txs_v2.py:75](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/decode_txs_v2.py:75) 原文 `fp = self.root / f"{row['sig'][:2]}.jsonl"`；第 76 行以追加模式打开该路径。
- 矛盾点：文件名直接取签名字符串前两字符，没有固定 256 桶的映射。提取现行路径表达式，对 4,096 个合成的 64 字节 Base58 编码输入离线计算，得到 **898 个不同 JSONL 路径**。这里只计算路径，未实际创建缓存文件。
- 修法建议：删除「256 片」，保留「按 sig 前 2 字符分片」；脚本第 8 行的同文头注可同步订正。无需改变缓存逻辑。
- 复现：

```bash
nl -ba references/data-pipeline-solana-capture.md | sed -n '169p'
nl -ba scripts/solana/decode_txs_v2.py | sed -n '71,77p'
```

复算分片路径数（不导入业务模块、不写文件）：

```bash
python3 -B -c 'import ast, hashlib
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
p = Path("scripts/solana/decode_txs_v2.py")
tree = ast.parse(p.read_text())
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SigCache")
put = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "put")
expr = next(n.value for n in put.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "fp" for t in n.targets))
code = compile(ast.Expression(expr), str(p), "eval")
alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def b58(data):
    number, chars = int.from_bytes(data, "big"), ""
    while number:
        number, r = divmod(number, 58)
        chars = alphabet[r] + chars
    return "1" * (len(data) - len(data.lstrip(b"\0"))) + chars
samples = [b58(hashlib.sha512(i.to_bytes(8, "big")).digest()) for i in range(4096)]
paths = {str(eval(code, {"self": SimpleNamespace(root=PurePosixPath("cache")), "row": {"sig": sig}})) for sig in samples}
print("path_expression_line:", expr.lineno)
print("synthetic_64byte_base58_samples:", len(samples))
print("distinct_jsonl_paths:", len(paths))
print("exceeds_256:", len(paths) > 256)
print("module_imported: False; filesystem_writes: 0")'
```

输出关键值：`synthetic_64byte_base58_samples: 4096`、`distinct_jsonl_paths: 898`、`exceeds_256: True`。

## 待确认（不计入 N）

无。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | A | `references/casebook/supply-accounting.md:82` | `references/report-template.md:298` | 图例计数未扣除明确豁免的烧毁桶 |
| D2 | minor | A | `references/analyze-workflow.md:198` | `references/retrospective.md:139` | 固定增加次版本与变更性质分级冲突 |
| D3 | minor | A | `references/data-pipeline-evm-channels.md:227` | 同文件 `:245` | 历史状态浅窗口与一律拒绝冲突 |
| D4 | nit | B | `references/data-pipeline-solana-capture.md:169` | `scripts/solana/decode_txs_v2.py:75` | 缓存分片数量不是固定 256 |
