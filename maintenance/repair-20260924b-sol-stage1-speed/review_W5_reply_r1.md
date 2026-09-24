# 工单W5复核r1：退回

六处替换锚点和字节预算均通过，但有 **3 项必改**：W4 对照结论扩大了证据范围、两处简写遗漏合法 JSON 前提、测试默认清理行为与禁止批量删除冲突。

**必改项**

1. **纠正 W4“三方全等”的概括。**  
   [工单第 4 行及 §2.6](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_W5.md:37) 将结论写成“header/tx/instr 三方全等”或“三组内容对照三方全等”。但 [fable_probes P3](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/fable_probes_20260924.md:25) 实际证明：
   
   - `header`：probe-only、census-only、combined 三方全等；
   - `transactions`：combined 与 census-only 两方全等；
   - `instructions`：combined 与 probe-only 两方全等。

   两处均须明确这三个比较关系；“三组”指三种查询，不能理解成只有三个 slot 样本。保留“完整生产链路吞吐收益未证明”。

2. **§2.2、§2.3 补齐“合法 JSON”及其他错误的处理。**  
   §2.1 新片段正确；commands 和 README 的简写仍未完整表达 [W2 §2.1](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_W2.md:66) 要求。`exit 2` 同时用于“正常扫描无图”和 argparse 参数错误，后者没有结果 JSON；现有测试明确覆盖 `(2, None)`。[依据](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_sqd_coverage_probe.py:1528)

   建议逐字改为：

   §2.2：
   > 仅 exit 0 才采用 chosen 并带 --known-map；仅 exit 2 且合法 JSON 中 chosen=null 才全扫；其余先处理错误；

   §2.3：
   > 仅 exit 0 才采用 chosen 并用 --known-map；仅 exit 2 且合法 JSON 中 chosen=null 才全扫；其余先处理错误，不得采用部分结果。完整加载失败时按探针规则回退。

   上述两个建议相对原旧片段分别净增 **95 B、122 B**，仍在预算内。

3. **§0.7 明确测试临时目录的保留方式，消除与 §0.6 的冲突。**  
   要求执行的三个测试使用默认 `TemporaryDirectory()`：
   [review_scale](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_review_scale_guards.py:82)、[coverage_probe](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_sqd_coverage_probe.py:1507)、[exemption](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_exemption_guards.py:92)。本机标准库源码确认，其退出清理会调用 `shutil.rmtree`，属于批量删除，与工单“禁止批量删除”冲突。

   工单应规定：在内存运行器中禁用临时目录自动删除、保留目录并记录路径；同时禁写 Python 字节码。不修改测试源码、断言或判定，也不扩展仓库写白名单。

**其余核验结果**

当前 HEAD 为 `9f266eaf3e6fc0f5e67cd2666a527f1c728435bd`，工作树干净。基线祖先检查及 §0.1 指定路径的基线差异检查均为 **exit 0**。

对 `git show HEAD:<文件>` 输出逐条执行 `grep -n -F -e`，并独立计算 UTF-8 长度：

| 条目／目标行 | 命中次数 | 旧片段 B | 新片段 B | 净增 B |
|---|---:|---:|---:|---:|
| §2.1 split-run:41 | 1 | 116 | 275 | 159 |
| §2.2 commands:12 | 1 | 32 | 109 | 77 |
| §2.3 README:5 | 1 | 77 | 177 | 100 |
| §2.4 CHANGELOG:108 | 1 | 67 | 78 | 11 |
| §2.5 CHANGELOG:109 | 1 | 146 | 456 | 310 |
| §2.6 CHANGELOG:110 | 1 | 85 | 231 | 146 |

行号全部一致。按当前工单在内存替换后：

- references：`28,064 → 28,223 B`，净增 **159 ≤260 B**。
- commands：`2,382 → 2,459 B`，净增 **77 ≤140 B**。
- 资产 README：`6,601 → 6,701 B`，净增 **100 ≤160 B**。
- CHANGELOG 合计净增 **467 B**。

退出码源码确认：先保留并输出 `chosen`，再优先返回扫描故障 `1`；无扫描故障时，有 chosen 返回 `0`，否则返回 `2`。因此 **exit 1 即使 chosen 非空也不得采用**，§2.1 修正与真实契约一致。[源码](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:1686)

CHANGELOG 新增事实逐项核对如下：

| 事实 | 核验结果与依据 |
|---|---|
| probe 两协议登记 `d4adc0c8…`，旧 `c4980c98…` 保持 ACTIVE | 成立；`WR-b_acceptance.md:3`、`WR-b_formal_entry.md:12`，并核对当前注册表 |
| docs_lint、changelog_lint PASS | 有历史依据：`W2_acceptance.md:5`；不代表 W5 修改后的验收 |
| run_all 150/151，唯一红为 reseal worktree 缺失 | 与 `WR-b_acceptance.md:10` 一致；“环境项”是既有验收记录的归因，本轮未动态复验 |
| producer 守卫 0 FAIL | `WR-b_acceptance.md:4`、`WR-b_formal_entry.md:45` 支持 |
| WR-a／WR-b 正式入口验收 PASS | 两份 `formal_entry` 报告支持；WR-b 明确区分登记有效性与当前源码产物兼容性 |
| 收官 review PASS，P0/P1 空 | `review_final_reply_r1.md` 支持；“P2/P3 已按 W5 修正”须待实际修正完成后才成立 |
| W3 字节 `4,516,539→736,729`、gzip、规范化摘要相同 | `fable_probes` P5 支持 |
| 完整生产链路吞吐收益未证明 | 新片段明确保留，与收官 review 一致 |

除必改项 1 外，未发现凭空新增的历史 PASS；这些历史结果不能作为 W5 修改后的测试结果。

文档门禁方面：

- 亲跑 `test_g3_docs_guards.py`：**4 项 PASS，exit 0**。它只读取 analyze/research 两份文档，不检查 CHANGELOG。
- `docs_lint.py:317` 明确豁免 CHANGELOG 断链检查；新增两个链接的目标也实际存在。
- 内存替换后的 CHANGELOG 三行各含 **2 个 `**`**；split-run 修改行含 **10 个**，均配对，不会因这些替换触发残缺粗体。
- 未运行完整 docs_lint/changelog_lint；它们读取禁区，交调度方运行的安排正确。

不升版本可接受：这是尚未 push 的 **9.2.0 同批次收尾修订**。`CHANGELOG.md:4` 将文档修订归入“修”档，但不要求未发布版本每次修改都另起版本。若另行发布独立修订，才应按修版本处理。本地远端跟踪引用仍停在此前基线；未联网核验远端。

除必改项 3 外，四文件白名单、指定片段限制和不改清单没有冲突；部署同步测试预期 FAIL 与“仓库外 commands 不改、由调度方同步”一致。建议把完成报告写成完整路径 `maintenance/repair-20260924b-sol-stage1-speed/W5_done.md`，消除落在仓库根目录的歧义。

本轮全程离线，未新建或修改文件、未 commit；未读取 `~/.codex/`、memories 或其他指定禁区。一次 here-document 命令因 shell 临时文件创建被拒，随后改用内存 `python3 -B -c` 完成核算；结束时工作树仍干净。