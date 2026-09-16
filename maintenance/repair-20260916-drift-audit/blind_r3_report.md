<!-- 由 Fable 从 codex 只读盲审任务 task-mu4fbe6d-xnfqns 的 Final output 段原样搬运;codex 沙箱只读无法自行落盘 -->
# 盲审 R3：2 条发现

审查基线：`66f45e4c6cc05be2d80278d81589b1ddb304b745`；git status 前/后：空/空。结束时 HEAD 未变。

## 覆盖声明

全程离线、只读，未新建或修改文件，未 commit。报告全文已打印到 stdout。

覆盖 **46 份必审文档，另审 CHANGELOG 的现行规则文字**：

- 根目录：`SKILL.md`、`CHANGELOG.md`。
- `references/` 执行与交付：`analyze-workflow.md`、`split-run.md`、`context-discipline.md`、`environment.md`、`report-template.md`、`research-workflows.md`、`independent-audit-protocol.md`、`retrospective.md`、`maintenance-review-repair.md`、`monitoring-package.md`。
- `references/` 方法与契约：`address-book.md`、`analysis-playbook.md`、`economic-control-accounting.md`、`lp-fee-accounting.md`、`scan-schemas.md`、`playbook-entity-cluster-cost.md`、`playbook-entity-cluster-methods.md`、`playbook-entity-cluster-tiering.md`、`playbook-evidence-wording.md`、`playbook-state-anomaly.md`、`playbook-supply-recon.md`。
- `references/` 数据通道：`data-pipeline-evm.md`、`data-pipeline-evm-channels.md`、`data-pipeline-evm-recon.md`、`data-pipeline-evm-sources.md`、`data-pipeline-robinhood.md`、`data-pipeline-robinhood-channels.md`、`data-pipeline-robinhood-methods.md`、`data-pipeline-robinhood-traps.md`、`data-pipeline-solana.md`、`data-pipeline-solana-capture.md`、`data-pipeline-solana-scan.md`。
- `references/casebook/`：`README.md`、`cex-custody.md`、`cex-custody-methods.md`、`entity-clustering.md`、`entity-clustering-methods.md`、`supply-accounting.md`、`supply-accounting-methods.md`。
- `references/labels/`：`README.md`、`MAINTENANCE.md`。
- `commands-staging/`：`token-analyze.md`、`token-analyze-1.md`、`token-analyze-2.md`、`token-analyze-3.md`。

术语表共 **1,277 个去重标识符**，按反引号技术名及阶段、门禁编号提取。以 `rg -n` 定位名称、阈值、schema、字段和命令，再读取上下文；对 310 个 Python 文件建立 AST 索引，核对 CLI、schema 常量，并定向读取生产者与消费者。另核对 `agents/openai.yaml`、`pyproject.toml`。

本轮补强方向：地址簿与 labels 来源逐行对照（206 行 manual 数据，投影字段差异 0）；环境依赖与 env_check/pyproject；复盘、维护及报告命令与真实参数解析；判例与正式方法的阈值和证据上限；schema 字段约束与实际生成、校验逻辑。

已与 R1/R2 报告、工单及待决台账去重。以下两条的文档原句及对应生产者行为在 R1 施工前的 `01296ab^` 已存在；生产者文件从该点至 HEAD 无差分。**本轮未确认 R1/R2 修复引入的新不一致。**

## 发现（按严重度排序）

### D1 — minor — B 类 — Helius 密钥来源被文档写成单文件，实际默认优先读取多密钥文件

- 位置甲：[references/environment.md:18](/Users/uravvv/.claude/skills/token-chip-analysis/references/environment.md:18) 原文：「Solana SQD 修复生产者正式运行依赖 Helius key：只从 `~/.config/helius/api-key` 读取」。
- 位置乙：[scripts/solana/sqd_gap_repair.py:47](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:47) 原文：`KEYS_FILE = Path.home() / ".config/helius/api-keys"`；同文件第 123、127、130–132 行原文：

  ```python
  keys_file=KEYS_FILE, key_file=KEY_FILE):
  selected = Path(reference_keys_file) if reference_keys_file else Path(keys_file)
  keys = _keys_from_file(selected)
  if not keys:
      keys = _keys_from_file(key_file)
  ```

- 矛盾点：默认先读复数文件 `api-keys`，没有取得 key 才回退到单数文件 `api-key`。多密钥文件有可用条目时，仅按文档更新单密钥文件不会改变默认选中的密钥池。第 125–126、1537–1538 行还允许显式 RPC 或密钥文件覆盖。隔离函数复现确认：默认调用多密钥文件读取分支，未调用单密钥回退；未读取真实凭据。
- 修法建议：**修改文本**，替换“只从”一句为“默认先读取 `~/.config/helius/api-keys`，无 key 时回退到 `~/.config/helius/api-key`；显式参数见生产者 CLI”。无需改代码。
- 复现（以下命令均在仓库根目录执行）：

  ```bash
  rg -n '只从' references/environment.md
  nl -ba scripts/solana/sqd_gap_repair.py | sed -n '46,47p;122,135p;1537,1538p'
  ```

### D2 — nit — B 类 — slot-index-map 的不变量错误要求 signature 列也单调递增

- 位置甲：[references/scan-schemas.md:867](/Users/uravvv/.claude/skills/token-chip-analysis/references/scan-schemas.md:867) 将 `row.map` 定义为「[sqd_index,nonvote_ordinal,signature]」；第 873 行原文：「三列各自唯一双射且单调递增。」
- 位置乙：[scripts/solana/sqd_gap_repair.py:1094](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1094) 第 1094–1095 行原文：

  ```python
  sqd_transactions = sorted(payload["sqd_transactions"],
                            key=lambda row: row["index"])
  ```

  第 1111–1112 行原文：

  ```python
  triples = [[row["index"], ordinal[row["signature"]], row["signature"]]
             for row in sqd_transactions]
  ```

  消费者 [scripts/lib/solana_exact_validate.py:1558](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:1558) 第 1558–1560 行原文：

  ```python
  columns = list(zip(*triples)) if triples else [(), (), ()]
  if any(len(set(column)) != len(column) for column in columns) \
          or triples != sorted(triples, key=lambda row: row[0]):
  ```

- 矛盾点：生产者按 SQD 索引排列，signature 保留对应交易的值；消费者检查各列唯一和第一列排序，没有要求签名按字典序递增。内存样例实际产出 `[[0,0,"5×88"],[1,1,"3×88"]]`（签名缩写），三列均唯一，签名列却递减。按文档原文检查，会把这种生产者输出判为违反不变量。
- 修法建议：**修改文本**为“三列分别唯一；行按 `sqd_index` 递增；`nonvote_ordinal` 按 signature 与参考源非投票交易顺序对应”。无需改代码。
- 原文复现：

  ```bash
  nl -ba references/scan-schemas.md | sed -n '854,874p'
  nl -ba scripts/solana/sqd_gap_repair.py | sed -n '1086,1112p'
  nl -ba scripts/lib/solana_exact_validate.py | sed -n '1558,1581p'
  ```

行为复现：只提取该函数，在内存中传入合成数据，不导入生产模块、不读凭据、不联网、不写文件。

```bash
python3 -B -c '
import ast
from pathlib import Path
path = Path("scripts/solana/sqd_gap_repair.py")
tree = ast.parse(path.read_text())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_routea_slot")
ns = {}
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), ns)
sigs = ["5"*88, "3"*88]
payload = {"slot":1, "missing_full":[], "sqd_sigs":sigs, "helius_sigs":sigs,
"sqd_transactions":[{"index":i,"signature":s,"err":None} for i,s in enumerate(sigs)],
"blockhash":"block", "sqd_blockhash":"block", "blockTime":0,
"census_query_body_sha256":"a"*64, "census_response_sha256":"b"*64,
"reference_response_sha256":"c"*64}
mapping = ns["_routea_slot"](payload, "mint")[2]["map"]
print("map:", [[r[0], r[1], r[2][0] + "x88"] for r in mapping])
print("all_columns_unique:", all(len(set(c)) == len(c) for c in zip(*mapping)))
print("signature_column_increasing:", all(a[2] < b[2] for a,b in zip(mapping, mapping[1:])))
'
```

已执行结果：`all_columns_unique: True`；`signature_column_increasing: False`。

## 待确认（不计入 N）

**质押账本的“精确对表”是否要求零误差。** [references/data-pipeline-solana-scan.md:100](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:100) 原文：「账本净额合计 vs 池链上余额精确对表」；[scripts/solana/stake_decode.py:212](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/stake_decode.py:212) 原文：`closed = abs(onchain - tot) <= 2`，第 214 行以 `verdict="PASS" if closed else "FAIL"` 判定。

代码明确允许 2 个 raw 单位误差，但文档没有明确定义“精确”为差额严格等于零，因此证据不足以直接计为漂移。需确认该词的约定含义。

```bash
nl -ba references/data-pipeline-solana-scan.md | sed -n '100p'
nl -ba scripts/solana/stake_decode.py | sed -n '212,217p'
```

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | B 类 | references/environment.md:18 | scripts/solana/sqd_gap_repair.py:47、122–135 | 文档限定单密钥文件，默认实现优先读取多密钥文件 |
| D2 | nit | B 类 | references/scan-schemas.md:867、873 | scripts/solana/sqd_gap_repair.py:1094–1112；scripts/lib/solana_exact_validate.py:1558–1581 | 文档要求 signature 递增，生成与校验实际按交易索引排列 |
