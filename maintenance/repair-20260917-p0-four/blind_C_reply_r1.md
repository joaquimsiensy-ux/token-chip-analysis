# 盲审 C：FAIL

发现 **1 项 minor，无 blocker**。六项 R07 数值与绑定不变量已实现；FAIL 来自新增输入 schema 与实际校验不一致。未完成的集成测试单列，不计作代码缺陷。

审查范围为 `8dea1ab..1b317b3`。当前 HEAD 为 `48852ae`，相关源码、工单及证据与候选提交一致；开工、收尾工作树均为空。报告全文已打印到 stdout。

**C-01｜minor｜输入类型校验不完整，生成成功后可在宏渲染时报错**

位置：[scripts/report/facts_gate.py:445](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:445)，关联 docstring :63、:69，消费者 :148。

文档声明 `metrics: {}`、`dual_basis: {}`，实际实现为：

```python
"metrics": fi.get("metrics") or {}
if isinstance(fi.get("dual_basis"), dict):
    facts["dual_basis"] = fi["dual_basis"]
```

在正常 C4-d 夹具上，仅把 `facts_inputs.metrics` 改为 `[{"value":"7"}]`，本轮内存文件系统复现：

```text
derive_facts：成功，facts.metrics 为 list
build_main：rc=0，mode=formal
check_facts_vs_ledgers：errors=[]
Facts(facts).render("{{m:m1}}")：
AttributeError: 'list' object has no attribute 'get'
```

另外独立验证：`symbol=123` 被转换为 `"123"`；非对象 `dual_basis` 被静默省略。

修法建议：在 `derive_facts` 内落实 symbol 字符串、metrics/dual_basis 对象的类型约定；非法输入抛出带字段名的 `ValueError`，补普通类型错误反例。无需改动受保护的 `Facts/gate_check`。

归因：**修复中新引入**。替代解释“实现遵循工单示例”成立，因此不是施工越界；但新增生成入口仍与其 schema、消费者不一致。本项不表示三账数值重算可绕过。

**a）六项不变量**

以下生产文件均位于 `scripts/report/`。

| 项目 | 结论与代码位置 |
|---|---|
| ① 来源及 provenance | 成立。facts_gate.py:326、:333、:336、:349 读取并校验三账、identity、state_source；:442–457 生成逐文件 SHA、state_source SHA、mode、override、producer 绑定；:480 调用同一 derive。 |
| ② 实体与峰值口径 | 成立。:374–376 仅收 strict 成员；:383–394 以 economic 条目建实体、取 confirmed current；:337 取 identity 总量。:399–404 验 override evidence 字段、案根常规文件及实物 SHA；:412–423 处理锚点、formal 无来源拒绝和 peak<current 拒绝。 |
| ③ 既有 gate 自检 | 成立。facts_gate.py:459–462 调用 `gate_check(Facts(facts))`；G2/G3 原实现逐字未改。 |
| ④ 非有限 JSON | 成立。facts_gate.py:295–311 同时使用 parse_constant、parse_float，覆盖 NaN、±Infinity、±1e999。 |
| ⑤ new-analysis 重算 | 成立。audit_release_gate.py:53、:1646–1654 将 facts 纳入必需件；:1377 拒绝非常规 facts；:1380–1397 验收据本名和绑定/mode；:1400–1422 重算、逐键/逐实体比较并排除 producer；:1704–1706 接入正式闸。 |
| ⑥ stage2 11→12 | 成立。stage2_closeout.py:576–582 新增 facts_vs_ledgers。机械比对确认原 11 个 record 名称、顺序不变，新项紧随 facts_gate；异常由 :493–503 记录为 BLOCK。 |

输入只改字节而数值不变的内存反例，也被 provenance SHA 比对拒绝。

**b）六视角**

| 视角 | 结论 |
|---|---|
| ① 字段来源 | 通过。比较值来自 derive 重算；override 重新读取证据并验 SHA。证据内容能否证明峰值数学正确性，仍属工单保留的 P4。 |
| ② 失败分支 | 指定的缺件、空账、不闭合、证据不符、预置绑定、非有限分支均拒绝，错误文本可区分；类型校验遗漏见 C-01。独立 schema/binding 错误可累计，不互相覆盖。 |
| ③ 存量迁移 | 符合设计。缺 facts 或缺 provenance 的旧案在 new-analysis 必红；independent-audit 的 required 集合及检查分支未增加此要求。legacy-recompile 仍走原显式降级路径。 |
| ④ 同族调用面 | build_html.py:274/:431/:489 固定标准 facts，analysis-new 必经发布闸，有错误不写 HTML。state_from_facts.py:82–143、figures_from_facts.py:217/:296、独立 Facts 校验、A4/A5 seal、distribution_explanation_check.py:101 不独立重算 provenance；完整 new-analysis 发布和 stage2 check/amend 已覆盖，未发现本段遗漏的最终发布入口。receipt-only 仍只核收据/哈希，不等同完整重算。 |
| ⑤ 双向一致性 | report-template.md:212 的“build 自三账生成”与实现一致；facts_gate 输入类型说明存在 C-01。state_from_facts 按键构建返回值，facts_inputs 不会展开进 state。 |
| ⑥ 检查点可绕性 | 指定项目闭合：--source 另名 rc=2；--out 使用 basename，父路径被收敛到案根；facts 符号链接被拒；formal 拒 exploration ledger；facts_inputs 预置 provenance/facts_binding 被拒；figure2 另名 facts 被拒。 |

A4/A5 核验位置为 a4_gate.py:390/:574、a5_report_seal.py:337/:372。单独封印成功不代表本段发布闸通过。

**c）测试真实性**

- 使用 `git show 8dea1ab:<path>` 核对基线，三个生产文件 SHA256 均与 RED 的 before/after 记录相同；RED 文件 SHA 与 C_done.md:452 一致。基线确实缺少新增 API、共享助手，旧 CLI 要求 --facts，stage2 只有 11 项，记录异常与基线相符。
- C4-d 为 **14 类、28 个变体**，保留输出、确定性、错误类别及 G2 断言，最终汇总失败会触发 AssertionError。本轮以内存文件系统、真实生产函数和直接 build_main 调用执行，28/28 通过；不是原始 CLI 落盘测试。
- stage2 三变体在 test_stage2_closeout.py:605–617 分别要求新 record 为 BLOCK，detail 含 e1/provenance/exploration，同时检查退出码、12 项计数及收据 verdict。已有 seal 错误不能替代这些断言。
- batch_d :1281–1296 先要求完整 new-analysis 零错误，再分别要求“重算不一致”“缺必需资产”特定错误。RED 中助手不存在属于工单允许的接口级 RED，不能夸大为两个业务反例都已在旧实现到达目标分支。
- 四处夹具仍要求真实成功：stage2 :76/:638、batch_d :1205/:1286、P105 :214/:261、A4 case_new :498/:534。共享助手调用真实 build 并要求 rc=0；发布零错误、HTML 生成及收据断言未被删除或降级。
- identity_gate_fixture 默认分支去掉新增包装后，AST 与基线一致；write_binding 源码逐字未改。空/单/多 rows 的纯逻辑调用参数及序列化返回字节均一致；真实 replay 子进程未重跑。
- reseal 搬移 helper 的函数体与基线相同，provenance 已前置到 facts build 前；reseal 整体验收未独立运行。

测试文件均位于 `scripts/tests/`。未发现为拿绿而弱化既有断言。

**d）回归及执行边界**

C_done.md:502–515 齐全记录 §0.8 的 **13 个测试＋invariant_scan**，均列 exit 0 和对应尾行；新增路径另有 GREEN 输出。尾行与测试源码输出形式相符。这是施工证据核对，不能替代本轮独立执行。

| 本轮检查 | 结果 |
|---|---|
| invariant_scan.py | 只读守卫下实际完成，exit 0：producers=80、consumers=117、transport=65、atomic=60、formal_entrypoints=61、exceptions=0。 |
| test_report_facts.py、test_stage2_closeout.py、test_repair_batch_d.py、test_a4_gate.py | 尝试加载执行，在临时目录/文件创建前被只读守卫停止；包装退出码 77，原始集成测试未完成。 |
| C4-d 内存验证 | 28/28；另核链接、exploration、预置绑定、输入 SHA 变化及 --out 路径行为。 |
| 静态机械检查 | 改动 Python 全部 ast.parse 通过；git diff --check 通过；受保护函数及原 argparse 行为未改。 |

未重跑 §0.8 其余集成测试、stage2_reseal、run_all、docs_lint 或 Desktop 存量案。只读限制不作为 FAIL 原因。

**e）工单符合度**

- 提交共 **15 个文件**：13 个源码/测试/登记/模板文件，加两份施工证据，全部命中 §0.3 白名单；SKILL.md、commands-staging 零 diff。
- 逐 hunk 未发现工单外改动。新增注释/docstring、ten→eleven、夹具顺序及成员调整均有工单依据。C_done 生产 diff 仅省略末尾两行空白上下文，可接受。
- invariant_manifest 仅增加规定的 producer、consumer schema、atomic_write。剔除增补后，与基线对象及全部数组顺序一致；minimum_counts 未改。
- 仅以 stat 汇总：**references Markdown 930065 B；SKILL.md 8021 B；commands-staging Markdown 8798 B**。模板唯一替换为 58→53 B，其余字节不变。
- 全程离线、零文件写入、未 commit。禁读内容未通过工具读取；references/attic.md 仅参与获准的 stat 汇总。

Codex session ID: 01a0afc7-dc52-7e11-af0e-f029c053c3a6
Resume in Codex: codex resume 01a0afc7-dc52-7e11-af0e-f029c053c3a6
