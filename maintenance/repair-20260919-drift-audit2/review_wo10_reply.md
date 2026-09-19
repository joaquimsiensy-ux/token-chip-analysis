# 工单R10复核：通过

**D1 采纳，v1 可按原替换文本施工，无必须退回项。** 两个条件不能理解成“满足后必能 emit”；新句只陈述必要条件，保留了前文实物绑定与逐条重放要求，因此没有引入这一错误承诺。

审查 HEAD：`590c780a699960e851d4aed0f61efed3410f07f0`。工作区前后均干净，工单指定内容范围相对 `4353454` 的差异为空。

1. **a）锚点：通过。**

   从工单代码块提取整行，分别执行 `grep -n -F` 和 `grep -n -F -x`，均唯一命中 [data-pipeline-solana-scan.md:67](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:67)。内存替换只改变第 67 行，文件仍为 192 行，末句之前逐字不变。

2. **b）代码依据与替换语义：通过。**

   - [identity_snapshot_receipt.py:83](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/identity_snapshot_receipt.py:83) 比较整个 `producer` 对象：`path` 必须正确，`sha256` 必须等于当前扫描器文件哈希。该检查早于 supply 解析（92 行）、GPA 解析（109 行）及账户重放（119 行）。
   - `emit_solana:143` 调用上述校验；`main:188` 将该 `ValueError` 转为 **exit 2 / BLOCK**；check 路径在 `validate_receipt:159` 重用相同校验。
   - [scan_token_accounts.py:265](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/scan_token_accounts.py:265) 写入 `sha256_file(__file__)`，其实现确实读取自身文件字节计算 SHA-256。
   - 对原函数进行了不落盘的隔离验证：旧哈希在 raw/supply 实物核验和重放前被拒，CLI 退出码为 2；当前哈希但 `path` 错误或对象多余字段也被拒。

   “先核 producer”仅指早于 raw/supply 重放，路径和 schema 检查仍在其之前。早期与当前扫描器哈希也已独立复算，确实不同；不能仅凭产物生成时间早就认定需要重扫。

**采纳的整行替换文本原文：**

```text
- **G8 离线重放契约**：`holders_snapshot_meta.json` 绑定的每个 GPA `raw_artifact` 不是“有文件有哈希”即算通过；identity emitter/check 必须调用 `scan_token_accounts.py` 的同一套 `parse_gpa_response`＋`parse_token_accounts`，从原始 RPC JSON 重做 base64 解码、跨 dataSlice/pubkey 去重、账户明细和 owner 聚合，并要求逐条等于 `holders_accounts.json`/`holders_owners.json`；同时解析 supply receipt 的 `result.value.amount` 与 `supply_raw` 闭合。存量产物 producer 哈希须等于当前扫描器且 raw/supply 重放一致，否则必须重跑 `scan_token_accounts.py`，禁止手补 meta/hash。
```

3. **c）UTF-8 字节预算：通过。**

   | 项目 | 当前字节 | v1 替换后字节 | 净变动 |
   |---|---:|---:|---:|
   | D1 整行，不含 LF | 676 | 667 | −9 |
   | 目标文件 | 34,220 | 34,211 | −9 |
   | `SKILL.md` | 8,021 | 8,021 | 0 |
   | `commands-staging/*.md` | 8,789 | 8,789 | 0 |
   | `references/*.md` | 824,176 | 824,167 | −9 |
   | `references/casebook/*.md` | 74,493 | 74,493 | 0 |
   | `references/labels/*.md` | 30,462 | 30,462 | 0 |
   | **references 三组合计** | **929,131** | **929,122** | **−9** |

   含 LF 的整行是 677→668 B。所有声明值吻合；替换后数字来自内存模拟。`attic.md` 仅用 `stat` 计大小，未读内容。

4. **d）回归面、存量与白名单：通过。**

   检索了许可范围内 **50 份非 maintenance Markdown**，并核对本工程记录。同款迁移承诺仅在目标现行条款出现；工程报告、工单中的引文属于审查记录。

   [maintenance-review-repair.md:116](/Users/uravvv/.claude/skills/token-chip-analysis/references/maintenance-review-repair.md:116) 是历史教训，应保留。[analyze-workflow.md:135](/Users/uravvv/.claude/skills/token-chip-analysis/references/analyze-workflow.md:135) 及其后续条款已要求当前扫描器生产、旧 meta 重扫后再 emit，与新句一致。

   许可范围未找到真实 `holders_snapshot_meta.json`，**具体受影响旧案数量未知**。哈希不符的旧产物本来就过不了当前校验，本次文本修复不新增哈希失效。该影响规则与盘点边界可记入已白名单的 `r10_done.md`，无需扩充白名单。

5. **e）文本减量与更短写法：通过。**

   v1 仅替换一行，净减 9 B，不增加 skill 上下文。保留迁移条件和禁手补要求有实际作用。

   存在更短的等价末句：

   > 存量 producer 哈希须匹配当前扫描器且 raw/supply 重放一致，否则重跑 `scan_token_accounts.py`，禁止手补 meta/hash。

   此备选比 v1 再少 12 B：整行 655 B，较旧文净减 21 B，references 合计应为 **929110**。这是可选压缩，不能仅据此退回；本次采纳原 v1，预算仍为 **929122**。

6. **f）范围与归因：通过。**

   D1 是可复现的文档—代码冲突。旧文 blame 为 `4aa98834`，校验 blame 为 `3bc6224b`，均早于本工程，支持历史漏检归因。工单未将盲审待确认项或版本史并入修复。

| 审项 | 结论 | 核心结果 |
|---|---|---|
| a 锚点 | 通过 | 唯一命中第 67 行 |
| b 代码事实与语义 | 通过 | 哈希校验、退出码、自身哈希写入均属实 |
| c 字节与行数 | 通过 | −9 B；总量 929122；192 行不变 |
| d 回归、存量、白名单 | 通过 | 无同款现行残留；具体旧案数量未知；白名单足够 |
| e 文本与上下文 | 通过 | 原 v1 减量；更短方案可选 |
| f 范围与事实性 | 通过 | 历史事实冲突，无范围外修复 |

完整报告已打印到 stdout。本次采用静态核对及内存验证，未运行会写临时文件或遍历禁区的完整施工守卫；§1.2 全绿仍须施工后验收。

未读取 `~/.codex/`、memories 或禁区内容，未联网、未修改或新建文件、未 commit。系统 Git 启动器及 zsh here-doc 的临时写入尝试均被沙箱拒绝，随后改用实路径 Git 与 `python -B -c` 完成核验。
