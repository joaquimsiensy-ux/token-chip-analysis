# 施工 R13：完成

按 `maintenance/repair-20260919-drift-audit2/workorder_r13.md` v2 执行。仅替换 `references/data-pipeline-solana-capture.md` 第 95、96 行，并新建本报告；全部 9 项守卫通过，references 合计净减 13 B。未 commit、push 或部署。

## §0.1 开工基线校验

开工检查的实际命令与原始输出如下；工作区为空，指定内容基线差异为空。

```sh
git status --short
```

退出码：0。原始输出（空）：

```text
```

```sh
git rev-parse HEAD
```

退出码：0。原始输出：

```text
cee2145ee1780a13d0d138c0a8280a060f0a7db9
```

```sh
git diff --stat 16f9c44 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md
```

退出码：0。原始输出（空）：

```text
```

## 锚点核验

修改前以 `grep -n -F -x` 对整行字面核验，两个锚均恰好 1 处，行号分别为 95、96。

```sh
grep -n -F -x -- '- **undetermined 语义（诚实纪律）**：深挖账户按结果分类 events_found / all_zero_delta / fetch_failed——后两类是"没查出来"不是"没事件"（高频中转户 delta 笔可能在 --deep-sigs 窗口外），不构成"无漏"证据；过半 undetermined＝样本无效（批 D GPT-F-06 起 exit 1，不再只告警）。' references/data-pipeline-solana-capture.md
```

退出码：0。原始输出：

```text
95:- **undetermined 语义（诚实纪律）**：深挖账户按结果分类 events_found / all_zero_delta / fetch_failed——后两类是"没查出来"不是"没事件"（高频中转户 delta 笔可能在 --deep-sigs 窗口外），不构成"无漏"证据；过半 undetermined＝样本无效（批 D GPT-F-06 起 exit 1，不再只告警）。
```

```sh
grep -n -F -x -- '- **退出码**：0=抽样零漏边；2=发现漏边（对账 gate 语义，报告 missing_detail 带 tx 级证据）；1=运行失败/样本无效。**样本无效机器判据（批 D GPT-F-06 收口，任一命中即 exit 1）**：任一 getMultipleAccounts 批失败／深挖账户全部 fetch_failed／checked=0 且 closed>0／墙钟截断／undetermined 过半。' references/data-pipeline-solana-capture.md
```

退出码：0。原始输出：

```text
96:- **退出码**：0=抽样零漏边；2=发现漏边（对账 gate 语义，报告 missing_detail 带 tx 级证据）；1=运行失败/样本无效。**样本无效机器判据（批 D GPT-F-06 收口，任一命中即 exit 1）**：任一 getMultipleAccounts 批失败／深挖账户全部 fetch_failed／checked=0 且 closed>0／墙钟截断／undetermined 过半。
```

## ① 改前 → 改后 diff

```sh
git diff -- references/data-pipeline-solana-capture.md
```

退出码：0。原始输出：

```text
diff --git a/references/data-pipeline-solana-capture.md b/references/data-pipeline-solana-capture.md
index a6fd1cb..df8300b 100644
--- a/references/data-pipeline-solana-capture.md
+++ b/references/data-pipeline-solana-capture.md
@@ -92,8 +92,8 @@
 
 - **两种样本发现模式**（`--mode auto|sigs|blocks`，默认 auto）：sigs=mint 签名史抽样（全程边集适用；签名史新→老翻页，历史定向段边集会翻不到区间）；blocks=边集 slot 区间内均匀抽 getBlock 整块提取（定向段正解，免翻页）。auto 3 页探路未进区间自动切 blocks。
 - **判定粒度声明（v4 定稿）**：默认正式入口只接受 v4 7 元组并校验 `tx_index/instr_index`；旧 5 元组只允许显式 `--legacy-sol5` 诊断，报告强制 `non_formal=true/order_ambiguous=true`，不得冒充正式输入。`audit_release_gate.py` 对 `dormant_warehouse_audit.json` 的这两个字段均要求显式 `false`，字段缺失或任一为真都阻断发布。base（未修复原账）的覆盖谓词仍只是“边集中存在同 slot 且 from/to 含该 owner 的边”，同 slot 同 owner 多笔可能误判；7 元组堵住格式降级与 DISTINCT 吃边，但不会把普通销户抽查自动升级为 transaction-exact（逐交易精确）。**缺陷 slot 经修复代替换后则已是 transaction-exact**：修复生产者按签名取参考源交易、统一重编号，`exact_reconcile` 再深验修复 bundle（成套证据包）与边源。跨源身份只认签名，不比较两个来源各自的交易位置编号。`CLEAN` 只按所走路径的已声明强度解释。
-- **undetermined 语义（诚实纪律）**：深挖账户按结果分类 events_found / all_zero_delta / fetch_failed——后两类是"没查出来"不是"没事件"（高频中转户 delta 笔可能在 --deep-sigs 窗口外），不构成"无漏"证据；过半 undetermined＝样本无效（批 D GPT-F-06 起 exit 1，不再只告警）。
-- **退出码**：0=抽样零漏边；2=发现漏边（对账 gate 语义，报告 missing_detail 带 tx 级证据）；1=运行失败/样本无效。**样本无效机器判据（批 D GPT-F-06 收口，任一命中即 exit 1）**：任一 getMultipleAccounts 批失败／深挖账户全部 fetch_failed／checked=0 且 closed>0／墙钟截断／undetermined 过半。
+- **undetermined 语义（诚实纪律）**：深挖账户按结果分类 events_found / all_zero_delta / fetch_failed——后两类是"没查出来"不是"没事件"（高频中转户 delta 笔可能在 --deep-sigs 窗口外），不构成"无漏"证据；过半 undetermined＝样本无效（批 D GPT-F-06 起不再只告警）。
+- **退出码**：0=抽样零漏边；2=发现漏边（对账 gate 语义，报告 missing_detail 带 tx 级证据）；1=运行失败/样本无效。**样本无效机器判据（批 D GPT-F-06 收口，漏边优先 exit 2）**：任一 getMultipleAccounts 批失败／深挖账户全部 fetch_failed／checked=0 且 closed>0／墙钟截断／undetermined 过半。
 - **报告 status 契约（批 D；7.0.0 F4 统一）**：`CLEAN`（checked>0 零漏，exit 0）／`NO_CLOSED_SAMPLED`（抽样内无销户账户，审计对象为空——**弱结论**，exit 0，只证明"这批样本没有销户账户"，不冒充"销户路径零漏"强证明）／`LEAK_FOUND`（exit 2）／`INVALID_SAMPLE`（exit 1，`invalid_reasons` 逐条列明）。5 个早退阶段与主路径使用同一 builder，始终输出完整 `sampled` 键集；`sampling_phase` 固定为 `edges_missing|edges_invalid|edges_empty|signature_discovery|init_discovery|complete`，早退 `counts_complete=false`，只有主路径统一汇总点为 `true`。墙钟与耗时统一用 `time.monotonic()`，`generated` 仍是墙上时间；墙钟触发时 `wall_truncated=true` 且 `invalid_reasons` 同时保留直接失败原因和唯一一条含“墙钟”的截断原因。
 - **定位**：销户抽查仍是补充证据；但 SQD coverage 探针（覆盖健康检查）和 Solana `exact_reconcile` 已是 A2 硬 gate。先由探针判健康或缺陷，再按 §13e 走修复生产者；禁止拿 `window_fetch` 追加几条边冒充缺口闭合。
 
```

替换后与施工 HEAD 的该文件逐字节核对：仅第 95、96 行变化，第 97 行及所有其他字节不变。核验原始输出：

```text
line 95: -10 B
line 96: -3 B
PASS: only complete lines 95 and 96 changed; total -13 B; all other bytes unchanged
```

## ② §1.1 字节实测

| 统计范围 | 修改前（B） | 修改后（B） | 净变动（B） |
| --- | ---: | ---: | ---: |
| `SKILL.md` | 8021 | 8021 | 0 |
| `commands-staging/*.md` 合计 | 8789 | 8789 | 0 |
| `references/*.md references/casebook/*.md references/labels/*.md` 合计 | 929105 | 929092 | -13 |

以 `Path.stat().st_size` 统计文件大小；`references/attic.md` 仅计大小，未读取内容。第 95 行 -10 B，第 96 行 -3 B。三个修改后实测值全部等于工单要求。

统计命令：

```sh
python3 - <<'PY'
from pathlib import Path
import json
r13_groups = {
    'SKILL.md': [Path('SKILL.md')],
    'commands-staging/*.md': sorted(Path('commands-staging').glob('*.md')),
    'references/*.md references/casebook/*.md references/labels/*.md': [p for pattern in ('*.md', 'casebook/*.md', 'labels/*.md') for p in sorted(Path('references').glob(pattern))],
}
print(json.dumps({name: sum(p.stat().st_size for p in paths) for name, paths in r13_groups.items()}, ensure_ascii=False, indent=2))
PY
```

修改前原始输出：

```text
{
  "SKILL.md": 8021,
  "commands-staging/*.md": 8789,
  "references/*.md references/casebook/*.md references/labels/*.md": 929105
}
```

修改后原始输出：

```text
{
  "SKILL.md": 8021,
  "commands-staging/*.md": 8789,
  "references/*.md references/casebook/*.md references/labels/*.md": 929092
}
```

## ③ §1.2 各守卫原始输出

以下 9 项均原样运行，退出码全部为 0。

```sh
python3 scripts/tests/docs_lint.py
```

退出码：0。原始输出：

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

```sh
python3 scripts/tests/docs_lint.py --all
```

退出码：0。原始输出：

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

```sh
python3 scripts/tests/casebook_lint.py
```

退出码：0。原始输出：

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

```sh
python3 scripts/tests/changelog_lint.py
```

退出码：0。原始输出：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

```sh
python3 scripts/tests/test_contract_routes.py
```

退出码：0。原始输出：

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

```sh
python3 scripts/tests/test_sixlens_docs.py
```

退出码：0。原始输出：

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

```sh
python3 scripts/tests/test_g3_docs_guards.py
```

退出码：0。原始输出：

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

```sh
python3 scripts/tests/test_version_consistency.py
```

退出码：0。原始输出：

```text
PASS: M-03 version metadata consistent at 9.0.1
```

```sh
python3 scripts/tests/test_commands_deploy_sync.py
```

退出码：0。原始输出：

```text
PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
```

## ④ git diff --stat

```sh
git diff --stat
```

退出码：0。原始输出：

```text
 references/data-pipeline-solana-capture.md | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
```

本报告为新建未跟踪文件，未暂存；`git diff --stat` 默认不包含未跟踪文件。已跟踪文件的 diff 仅包含白名单内的目标文档。

补充空白错误检查：

```sh
git diff --check
```

退出码：0。原始输出（空）：

```text
```

## ⑤ 差异 / 停工点

无差异、无停工点。开工状态、内容基线、锚点唯一性和行号、两行字面替换、净字节变化及 9 项守卫均符合工单。修改仅限 §0.3 两个白名单路径；未修改 `scripts/`、`commands-staging/`、`CHANGELOG.md` 或两份 manifest；未执行 commit、push、部署或删除操作。

## ⑥ 禁读披露

未读取 `~/.codex/` 下任何文件，未读取 memories；未读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/` 或 `references/attic.md` 的内容。`maintenance/` 下仅访问本工程目录 `maintenance/repair-20260919-drift-audit2/`。所有工作离线完成，未调用网络工具或外部 API。按工单原样运行守卫脚本；脚本自身遍历文档属于工单明确允许的被测代码既有行为。
