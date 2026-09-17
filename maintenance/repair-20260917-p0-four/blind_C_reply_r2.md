# 盲审 C：PASS

r2 结论：**C-01 已闭合，C7 未发现新增问题，r1 已判 PASS 项未被破坏。** 完整报告已打印到 stdout，未写报告文件。

审查范围为 `8dea1ab..eca1131 -- scripts/ references/`；C1–C6 对照工单 v3，C7 对照 v5。期间 HEAD 从 `8faa1a8` 推进到 `1a5e832`，审查范围内文件仍与 `eca1131` 一致；开工、收尾工作树均干净。

**C-01 闭合**

[facts_gate.py:357](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:357) 校验非空字符串 symbol；:362 校验非负整数 decimals；:372 校验 metrics 及每项均为对象；:376 使用 `"dual_basis" in fi`，显式 null 也拒绝。输出使用已经校验的值，docstring :69 同步。

内存实测复现 C7 基线 **5 RED、1 既有 GREEN**。改后六种非法输入均得到字段明确的 ValueError，build 返回 2，发布闸重算拒绝。缺省字段、合法空对象、正常 dual_basis、指标宏渲染及旧 producer SHA 的兼容性通过。

**a）六项不变量**

以下生产文件均位于 `scripts/report/`。

| 项目 | 结论与核对位置 |
|---|---|
| ① 来源与绑定 | 成立。facts_gate.py:326、:333、:336、:349 读取并校验三账、identity、state_source；:342 处理可选 provenance ledger；:451、:458 生成逐文件 SHA、state_source SHA、schema、ledger-derived、mode、peak_overrides、producer；:489 调用同一 derive。 |
| ② 实体与峰值 | 成立。facts_gate.py:383 只取 strict 成员；:395、:400 以 economic 条目建实体并取 confirmed current；:337 取 identity 总量。:408–420 验 override 证据字段、案根常规文件及实物 SHA；:421 取 provenance 峰值；:430 拒绝 formal 无来源；:431 拒绝 peak<current。 |
| ③ 既有 gate | 成立。[facts_gate.py:469](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:469) 对生成物调用既有 gate_check；G2/G3 原实现逐字未改。 |
| ④ 严格 JSON | 成立。facts_gate.py:295、:299、:306 使用 parse_constant 和 parse_float，拒绝非有限字面量及指数溢出；NaN、Infinity、1e999 反例本轮通过。 |
| ⑤ 发布重算 | 成立。audit_release_gate.py:53 将 facts 纳入必需件；:1377 拒绝非常规 facts；:1380 校验图 2 收据本名；:1388–1397 校验绑定及 formal；:1400 用同一 derive 重算；:1406–1422 排除 producer 后逐键、逐实体、逐绑定比较；:1704 接入正式闸。 |
| ⑥ stage2 收口 | 成立。[stage2_closeout.py:576](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:576) 新增 facts_vs_ledgers，:582 登记。原 11 项名称、顺序不变，新项紧随 facts_gate；异常由 record 转为 BLOCK。 |

**b）六视角**

| 视角 | 结论 |
|---|---|
| ① 字段来源 | 通过。比较值来自 derive 重算；override 证据重新读取并验 SHA。证据内容能否证明峰值数学正确性，仍是工单明确保留的 P4 边界。 |
| ② 失败分支 | 通过。缺件、空账、不闭合、证据不符、预置绑定、非有限输入均拒绝；C7 补齐字段类型错误。单项反例可按指定错误文本断言；多个独立错误可累计，未发现覆盖错误后放行。 |
| ③ 存量迁移 | 符合设计。无 facts、无绑定的手写 facts 在 new-analysis 必红。audit_release_gate.py:56 的 independent-audit 必需集合及对应分支未增加此要求；build_html.py:303 的 legacy-recompile 降级路径未改。 |
| ④ 同族调用面 | 通过本段范围核验。build_html.py:274 固定正式标准输入，:433 调用发布闸，:489 在错误时禁止输出 HTML。state_from_facts.py:85/:133、figures_from_facts.py:217/:296、distribution_explanation_check.py:101、独立 Facts 校验及 A4/A5 seal 不各自重算 provenance；完整 new-analysis 发布与 stage2 check/amend 已覆盖，未发现遗漏的必经最终发布入口。 |
| ⑤ 双向一致性 | 通过。report-template.md:212 与 build 行为一致；facts_gate.py:63/:69 的类型说明与 :357–377 一致。state_from_facts.py:133 显式组装输出，facts_inputs 不会展开进 state。 |
| ⑥ 检查点可绕性 | 指定项目成立。facts_gate.py:485 拒绝另名 --source；:493 将 --out 收敛为案根 basename；发布闸拒绝 facts 符号链接及图 2 另名 facts；formal 拒 exploration ledger；facts_inputs 预置 provenance/facts_binding 被拒。C7 未改变这些分支。 |

A4/A5 核过 a4_gate.py:390/:574、a5_report_seal.py:337/:372：封印或修订链成功本身不等于 facts 重算通过。stage2_closeout.py:616 的 receipt-only 仍用于收据与文件哈希核验，未将其当作完整重算。

**c）测试真实性**

- 使用 `git show 8dea1ab:<path>` 核对基线：新增 derive/build/check API、共享助手确实不存在，旧 CLI 要求 --facts，stage2 只有 11 项。三个生产文件 SHA 与 C_red_evidence 的 before/after 一致；两份 RED 文件 SHA 均与各自 done 报告一致。
- C4-d 原 **14 类、28 变体**，C7 后为 **15 类、34 变体**。本轮内存执行全部通过，既有宏/gate 断言也通过；CLI 子进程替换为直接调用 build_main，未计作真实落盘 CLI 验收。测试 :292 仍断言零失败。
- [test_stage2_closeout.py:605](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_closeout.py:605) 三变体分别要求新 record 为 BLOCK，detail 含 e1/provenance/exploration；同时保留退出码、12 项计数和总 verdict 断言。其他 seal 错误不能替代这些断言。
- [test_repair_batch_d.py:1281](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_d.py:1281) 先要求完整 new-analysis 零错误，再分别要求“重算不一致”“缺必需资产”特定错误。原 RED 属于工单允许的助手缺失接口级 RED，不能解释为旧实现已经执行到两个业务反例的目标分支。
- 四处夹具保留真实成功要求：共享助手 :223 要求 build rc=0；stage2 :638 要求 seed PASS；batch_d :1286、P105 :261 要求发布闸零错误；A4 :534 要求 analysis-new 成功且 HTML 存在。未发现跳过检查或弱化既有断言。
- identity_gate_fixture.py:55 默认分支机械还原后的 AST 与旧实现一致，write_binding 源码逐字未改；空、单、多 rows 的默认调用参数及返回序列化字节一致。该调用核验使用固定 binding 返回值，真实 replay 子进程未重跑。
- reseal helper 搬移的函数体与基线逐字相同；provenance ledger 已前置于 facts build。C7 两份源码逐字等于工单指定替换结果，包含注释、docstring、空白；原 28 个变体及其他既有断言未改。

测试文件均位于 `scripts/tests/`。

**d）回归与执行边界**

[C_done.md:502](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/C_done.md:502) 至 :515 完整记录 §0.8 的 13 个测试与 invariant_scan，均有 exit 0 和结果尾行；尾行与源码输出形式相符。[C7_done.md:47](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/C7_done.md:47) 的六项检查同样完整。这是施工记录核验，不替代本轮独立执行。

| 本轮执行 | 结果 |
|---|---|
| invariant_scan.py | 只读守卫下实跑 exit 0：producers=80、consumers=117、transport=65、atomic=60、formal_entrypoints=61、exceptions=0。 |
| test_report_facts.py、test_stage2_closeout.py、test_repair_batch_d.py、test_a4_gate.py | 尝试执行，在临时目录或文件创建前被只读守卫停止；包装退出码 77，原始集成测试未完成。 |
| 内存验证 | R07 34/34、既有宏/gate 断言、C7 六变体基线对照及合法输入兼容性通过。 |
| 静态检查 | 11 个改动 Python 文件 ast.parse 通过；范围 diff --check 通过；受保护函数和原 argparse 行为未变。 |

未实跑 §0.8 其余九个测试、stage2_reseal、run_all、docs_lint 或 Desktop 存量案对照。只读限制不作为代码 FAIL。

**e）工单符合度**

- 指定 `scripts/ references/` diff 为 **13 个文件、705 行新增、37 行删除**，全部命中白名单；未发现工单外源码、注释、docstring 或空白改动。施工提交 1b317b3 为 15 个白名单文件，eca1131 为 C7 指定四文件。
- 完整区间共 30 个文件，另含四份 C/C7 交付证据及 13 份调度元数据：`blind_C_prompt.md`、`blind_C_reply_r1.md`、`construct_C7_prompt.md`、`review_C7_prompt.md`、`review_C7_reply_r1.md`、`review_C7_reply_r2.md`、`workorder_C.md`、`code_change_pending.md`，以及 D 的 `blind_D_prompt.md`、`construct_D_prompt.md`、`review_D_prompt.md`、`review_D_reply_r1.md`、`workorder_D.md`。均位于本次 maintenance 目录；按给定源码范围可接受，D 文件仅核路径，未审内容。
- invariant_manifest 仅增补规定 producer、consumer schema、atomic_write。移除这些增补后，对象和全部数组顺序与基线一致，minimum_counts 未改。
- 仅以 stat 汇总：**references Markdown=930065 B，SKILL.md=8021 B，commands-staging Markdown=8798 B**。模板唯一替换为 58→53 B；SKILL.md、commands-staging 零 diff。

全程离线、零文件写入、未 commit。启动上下文预载了记忆摘要，本轮未通过工具读取 `~/.codex/`；其他禁读内容未读取，`references/attic.md` 仅参与获准的 stat 汇总。

Codex session ID: 01a0aff2-3d0c-76e0-8a9c-a474f6cbb6b4
Resume in Codex: codex resume 01a0aff2-3d0c-76e0-8a9c-a474f6cbb6b4
