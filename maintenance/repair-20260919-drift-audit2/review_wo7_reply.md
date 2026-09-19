# 工单R7复核：退回

三项漂移均成立，锚点和 v1 字节计算均正确。退回点是 **D1“准确性必要的最小增量”不成立**：存在等价写法，可少 12 B，使三处合计从净增 11 B 变为净减 1 B。应修订 D1 与 §1.1；D2、D3 原样采纳。完整报告已打印到 stdout。

**a）锚点：通过。**

从工单代码块直接提取整行，分别执行 `grep -n -F`、`grep -n -F -x`。三条均恰好命中一次，行号分别为 **117、178、119**，与工单一致。

**b）依据与代码事实：成立，但须限定表述。**

- [build_html.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/build_html.py:267) 的参数及模式分支确认：legacy 模式接受 `--facts`，不强制 `--state`，拒绝的是 `--a4-seal`、`--a5-seal`。[facts_gate.py:557](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:557) 确认 `state_path=None` 可正常渲染。
- 使用现行 `main()` 和真实 facts 渲染器做纯内存复现：不传 facts，实体宏和 `{{appendix_b}}` 均残留，退出码 **0、零 WARN**；传有效 facts、不传 state，宏正确展开，退出码 **0、零 WARN**；对没有 facts 文件的老报告强加参数，抛出 `FileNotFoundError`。未生成文件。
- “写宏的报告须加”条件正确，覆盖**无宏且没有 facts.json** 的老报告。含宏但 facts 丢失，仍需恢复事实源；不能改成“有 facts.json 才加”。QUQ 个案未查案卷，不作为本轮证明依据。
- §1.1 的“数字原样输出”应写成“宏不展开”；“零 WARN”应限定为**不因宏残留报警**，不保证缺图、坏 JSON 等其他输入也零 WARN。
- [solana-capture:110](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:110) 确有引用的定论和日期。代码支持公共 datasets、可选认证头，但不能独立证明外部服务当前不存在专属端点。D2 按同页现行规则与待办冲突成立。
- [solana-scan:119](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:119) 的 3a 至 3b 之间，`^\d+\. ` 实测编号 **1–9，共九项**，D3 成立。

**c）字节与整行替换：计算通过。**

UTF-8 复算与 v1 声明完全一致。三处模拟均只改变一行，没有增删行；文件行数保持 **130、250、192**。

`SKILL.md` 为 **8021 B**；四份 commands 合计 **8789 B**；references 三组共 42 文件，基线 **929528 B**。`attic.md` 仅用 `stat` 计大小，未读内容。

**d）回归面：三份 Markdown 白名单够用，但同概念尚未全清。**

- 其他 legacy 提及位于 `report-template.md:218`、`analyze-workflow.md:192`、`split-run.md:150`、`token-analyze-3.md:11`，属于模式说明或参数片段。`build_html.py:10–11` 是历史报告示例，未限定含宏；既有测试也使用无宏输入。未证实为 D1 同款缺陷，不应无条件补 facts。
- `data-pipeline-solana-capture.md:226` 的“三个必踩的坑”下确实只有三项；Solana 总入口没有错误数量，无需联动修改。
- SQD 同款旧说法仍在 [fetch_sqd_transfers_v2.py:26](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/fetch_sqd_transfers_v2.py:26)：“拿到专属端点后 --url 换掉即生效”，以及 [同文件:1301](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/fetch_sqd_transfers_v2.py:1301)：“拿到 key 专属端点后换这里”。应登记为**范围外残留**。
- 不建议直接扩白名单：该脚本 [517–518 行](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/fetch_sqd_transfers_v2.py:517) 对自身全文件计算 `collector_sha256`，只改帮助文字也会改变采集器身份，超出本单三份文档修复范围。

**e、f）最小修改与范围：D1 应压缩，其余通过。**

三项均为事实差异，没有把措辞偏好当漂移。D2 删除失效待办，D3 删除错误数量，符合“删除优先”。D3 的中英文空格不作为退回事由。D1 改成“含宏加”保留条件与操作含义，节省 12 B，无需改变其他行或扩大范围。

采纳的替换文本如下，均为完整一行。

**D1：修改后采纳，替换 monitoring-package.md:117。**

```text
3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`（含宏加 `--facts facts.json`）——这是合法重编译但带显式水印。若要维持正式身份，必须把 `appendix.json` 加入 `a4_gate.py finalize --seal-files ...` 重新封口，再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
```

**D2：原样采纳，替换 data-pipeline-solana-capture.md:178。**

```text
**遗留后续项**：①~~v2 整合 HyperSync 第二引擎~~ ②~~完备性验收~~（均 3.18.0 完成，验收不通过→禁用待 GA 重验）③Helius key 运行时检测（见 §13c）④实时 mint 档案（方案 4,用户暂缓）。
```

**D3：原样采纳，替换 data-pipeline-solana-scan.md:119。**

```text
### 3a. 流水追踪的Solana 特有坑
```

**工单 §1.1 相应替换为：**

```text
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 = 929527（基线 929528；三处整行替换净减 1 B：D1 +36、D2 -30、D3 -7；按 UTF-8 实测并写入报告）。含宏报告须传 `--facts facts.json`；未传时宏不展开且不因此 WARN；无宏老报告不强制补 facts.json。
```

| 条目 | 锚点命中／行号 | v1 行字节：前→后 | v1 净变动 | 建议净变动 | 裁定 |
|---|---|---:|---:|---:|---|
| D1 | 1／117 | 540→588 | +48 B | +36 B | 压缩后采纳 |
| D2 | 1／178 | 272→242 | −30 B | −30 B | 原样采纳 |
| D3 | 1／119 | 46→39 | −7 B | −7 B | 原样采纳 |
| 合计 | 3 行替换，0 行增删 | — | +11 B | −1 B | 修订 v1 |
| references 总量 | 基线 929528 B | — | 929539 B | 929527 B | 更新 §1.1 |

行字节不含换行符；换行保留，净变动不受影响。

执行状态：HEAD 为 `b35bad8c3a1d4cbdee34610377c9196d4c622820`；已比对的允许内容与 `fc704de` 无差异。复核开始 status 为空，结束时出现本工程目录下三个非本轮创建的未跟踪文件：`blind_r8a_prompt.md`、`blind_r8b_prompt.md`、`construct_r7_prompt.md`。**当前不满足 §0.1 的干净工作区开工条件**；本轮未操作这些文件。

未运行 §1.2 九项守卫，不声称守卫全绿。未联网、未修改或新建文件、未 commit；未读 `~/.codex/` 及其 memories、其他禁读内容或其他 maintenance 工程。早期工具启动的缓存与 heredoc 临时文件创建尝试被只读沙箱拒绝，随后改用直接 Git 路径与 `python3 -B -c`，未落盘。
