原始缺陷已解决；在本单“仅修 CLI、按结构化标记精确匹配”的范围内，未发现同类遗漏。审查对象为 `main@7cf53ae`，包含 `e1fa33f`，相关 CLI 代码此后未变。

- **P0：无。**
- **P1：无。**
- **P2：两项文档问题。**
  1. [README:9](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260925-label-blind-leak/README.md:9) 将多个出口统称为“无盲化判断”，不够准确。`replay_edges.py`、`build_evolution.py` 已有盲化分支，但仅看 `serial`；后者还有设施检查先于封存的问题。文件与行号均正确，后续单应订正缺陷描述。
  2. [analyze-workflow.md:88](/Users/uravvv/.claude/skills/token-chip-analysis/references/analyze-workflow.md:88) 的矛盾仍存在：“serial-actor 命中”不足以描述新判据，“设施类标签照常输出”对混合行不成立。施工方登记准确，应另单修正文档，不阻断本单收官。

**反例复现与修复验证**

临时 CSV 使用公共 `labels-sol.csv` 的真实 15 列表头，地址 `11111111111111111111111111111112` 已验证为 Base58 解码后恰好 32 字节。父版脚本通过指定的 `git show 84006ae:scripts/labels/label_lookup.py` 提取到临时目录，`PYTHONPATH` 指向仓库 `scripts/labels`。

| 模式 | 父提交 `84006ae` | 当前 HEAD |
|---|---|---|
| `--blind-serial --json` | `hit:true`，泄露 `category:"infra"`、`risk_flags:"serial-offender"`、`source:"serial-offenders+curation"` | 仅返回 `chain/address/hit:false` |
| `--blind-serial` 文本 | RISK、EXCLUDE 两段均输出 `<infra>`、风险旗标和来源 | 仅输出 `0/1 命中…` |

四次均退出 0。父版未封存；HEAD 两种模式各封存完整一行，保留风险、来源及派生的 `no_merge/exclude`，stdout 不含两个惯犯标记、`category` 字段或设施类别值。

**同族变体**

以下均实际运行 HEAD 的 JSON、文本两种模式：

| 输入变化 | 是否整行封存 | 裁决 |
|---|---|---|
| `risk_flags=" scam \| serial-offender \t\| mixer "` | 是 | 分项去空白后精确命中 |
| 空风险，`source="serial-offenders"` | 是 | 来源单独足以触发 |
| 空风险，`source=" curation + serial-offenders "` | 是 | 来源分项精确命中 |
| 只有 `serial="True"`，无其他标记 | 否 | 符合严格 `is True`，不是缺陷 |
| 只有 `serial=1`，无其他标记 | 否 | 同上 |
| 上述字符串或整数，同时保留原始风险/来源标记 | 是 | 其他判据仍生效 |
| 布尔 `serial=True` | 是 | 正对照 |
| 仅相似子串 `not-serial-offender`、`non-serial-offenders` | 否 | 符合不做子串匹配的裁决 |
| 干净设施行 | 否 | 正常保留 |

`serial` 由 resolver 派生，并非 CSV 输入列，因此字符串、整数场景通过临时进程注入 resolver 返回值，再执行 HEAD CLI 主流程；未修改仓库代码。

共完成 **27 次 CLI 调用**，全部符合预期；另验证环境变量盲化、`--chain all` 不追加 misses、非盲化正常输出。

**后续出口登记核对**

| 已登记位置 | 核验结果 |
|---|---|
| `analyze_holdings.py:192–224` | 准确；198 行仅判断 `r["serial"]`，混合行可进入风险输出 |
| `replay_edges.py:64–79` | 行号准确；72–77 行已有盲化，混合行绕过后在 79 行输出名称、类别 |
| `build_evolution.py:107–121` | 行号准确；108–109 行先收集设施信息，110–113 行才处理 serial 封存 |
| `cluster.py:200–242` | 准确；名称及设施信息输出未做盲化 |
| `entity_identity_gate.py:334–361` | 准确；名称、类别、来源直接写入产物 |
| resolver `get/policy/resolve_file` | 准确；接口本身不盲化。`is_serial()` 仍仅依赖类别派生值 |
| `--unseal` 与盲化同时指定 | 文档待明确的登记成立；代码实际由 `--unseal` 优先处理并返回 |

检索 `scripts/` 的 `blind/serial`、封存函数及 resolver 调用点，**未发现未登记的、同样仅按 serial 判断盲化封存的消费者**。上述范围外出口仅核验登记，未修复。

[CHANGELOG 9.2.1:109](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:109) 对代价的描述与行为一致：混合行的设施身份和策略字段在 CLI 盲化输出中一起隐藏，完整信息留在封存记录；不代表其他消费者也已同步修复。四处版本登记一致，版本一致性测试通过。

全程未联网、未读取真实案目录、未执行 Git 写操作；写入仅在系统临时目录。结束时 `git status --porcelain` 输出为空。

PASS