# 工单A复核：通过

v4 已闭合 r3 唯一退回项 **A-R3-01**，未发现新增阻断项，也未发现确定会使现有 `run_all.py` 用例由绿变红的改动。

这是**工单复核通过**。当前沙箱只读，临时目录 CLI、五个定向测试及 `run_all.py` 均**未实跑**。下述动态证据来自源码纯内存执行：补丁、输入和收据均在内存中，替代文件 I/O；退出码按函数返回值和 CLI 规则映射，不等于真实子进程验收。

复核对象 W＝[workorder_A.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_A.md)，F＝[figures_from_facts.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py)，C＝[test_repair_batch_c.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_c.py)。以下代码行号均为施工前基线。

a）已逐行执行 `grep -n -F`，明确修改锚均唯一、行号一致。

| 核对位置 | 实际结果 |
|---|---|
| F:60、63–65、109、139–144、201–202、257、283–286、306、308、328–330、370–372、406 | 每行各命中 1 处，行号一致 |
| F:282 的 `try:` | 8 处：71、76、114、169、203、282、380、394 |
| F:307 的 `continue` | 3 处：102、303、307 |
| C:37–40、45、54、60、1109、1201、2106 | 每行各命中 1 处，行号一致 |
| C:1111–1120，依行顺序 | 命中数为 2、3、7、8、2、2、2、2、6、3 |

W:16 已排除通用语句作为定位锚，W:99 将 C:1111–1120 定义为参考夹具。A2 使用 F:306 唯一锚定位相邻 F:307/308，未重新引入 A-03。

b）r1 七项、r2 两项及 r3 一项均已核对。

| 项目 | 本轮结论与证据 |
|---|---|
| A-01 | 闭合。fig1 的 `strict=False` 保留字段级报错；内存执行 NaN、Infinity 均含 `burn_cum_pct` 和“非有限”，满足两个原断言。 |
| A-02 | 闭合。`_file_ref` 只读原始字节取 sha，不解析 JSON、不修改输入字节；写 FAIL 收据可覆盖旧 PASS。`isfile` 本身不能保证可读、可写，A3 的 OSError 捕获补齐此边界。 |
| A-03 | 闭合，唯一锚及相邻位置正确。 |
| A-04 | 闭合。独立子函数与逐例捕获 AssertionError 能取得后续 RED；用例 13 也能转换成此类断言失败。 |
| A-05 | 闭合。macOS stat 命令只统计元数据，实得 `8021 / 930070 / 8798`。 |
| A-06 | 闭合。7 次调用分布在 6 行；默认 json.dumps 能输出 NaN；用例 1 基线错误 PASS，三处说明均正确。 |
| A-07 | 闭合。W:14 已将停工报告列入白名单。 |
| A-R2-01 | 闭合。整数转 float 的 OverflowError 被归入非法值；401 位整数及交换顺序均进入 FAIL 收据分支。原 r2 同输入旧 PASS 反例改后变 FAIL、sha 不变、消费者拒绝。 |
| A-R2-02 | 闭合。内存注入输入读取、临时文件创建、fsync、replace 失败，均得到 FAIL SystemExit 和“收据未更新”。 |
| A-R3-01 | 闭合。W:113 的基线描述及双捕获取证成立，直接证据如下。 |

用例 10 证明“换输入后覆盖收据、更新 sha”；用例 12 补足同输入旧 PASS 及消费者拒绝；用例 13 补足写收据失败的异常收敛。

用例 13 的实际定位命令与输出：

```text
grep -n -F '    _write_check_receipt(a, "PASS", okc, [])' scripts/report/figures_from_facts.py
338:    _write_check_receipt(a, "PASS", okc, [])
```

本轮使用工单指定的 `mock.patch.object(..., side_effect=OSError("disk full"))`，双捕获后保存异常对象，再调用 C:54–57 的原始 `check()`，结果为：

```text
基线：F:338 调用 writer(PASS, 1, [])
      → OSError('disk full')
      → AssertionError: case13 exception: OSError('disk full')

v4：调用 writer(FAIL, 0, ...)
    → SystemExit("FAIL: 图 2 对账输入不可用——…")
    → 三条 check 均通过

stderr：'[CHECK-FAIL] 收据未更新（写入失败：disk full）\n'
```

因此 W:115 的外层 `except AssertionError` 可以收集本例 RED。施工时应落实“记录异常”：保存到独立变量后断言，或在 except 块内断言；Python 会在离开 except 块后清除 `as e` 的绑定。

c）已核对 A5 当前全部 13 例，包含提示词所述原十例。

| 用例 | 基线行为 | 按 v4 修改后的内存结果 |
|---|---|---|
| 1 NaN 末点 | rc 0，PASS 收据 | rc 1，“字面量”，FAIL 收据 |
| 2 中间点 1e400 | rc 0，PASS | rc 1，“非有限”，FAIL |
| 3 字符串 pct | rc 0，PASS | rc 1，“非有限”，FAIL |
| 4 null pct | TypeError，无收据 | rc 1，FAIL 收据 |
| 5 Infinity 字面量 | rc 1，FAIL；mismatches 为末点超差 | rc 1，“字面量”；mismatches[0] 含“输入不可用” |
| 6 exploration＋99 | rc 0，PASS | rc 1，FAIL，mode=exploration |
| 7 facts 含 NaN | rc 0，PASS | rc 1，“字面量” |
| 8 dumps_fig2_series(NaN) | 不抛错，输出含 NaN | 抛 ValueError |
| 9 合法 27.8 | rc 0，PASS | rc 0，PASS |
| 10 换输入后重跑 | 第二次仍 PASS | rc 1，FAIL，series.sha256 匹配新输入 |
| 11 1e400＋超大整数＋27.8 | rc 0，PASS | rc 1，FAIL，无 OverflowError |
| 12 同输入手写 PASS | 消费者接受；重跑仍接受 | 重跑写 FAIL；消费者报“非 PASS” |
| 13 写收据抛 OSError | 转成带 OSError 原文的 AssertionError | FAIL SystemExit，三条断言通过 |

1–8、10–13 的基线 RED 均成立；9 是保持 GREEN 的回归例。

用例 5、6 与实际写入字段一致：

```text
264:           "mode": "exploration" if a.exploration else "formal",
267:           "lines_checked": okc, "mismatches": errs,
```

A3 传入 `[f"输入不可用：{exc}"]`，因此 mismatches 断言成立；exploration 模式也如实保留。

d）范围、不改清单、字节约束和登记项自洽。

- **§0.4：** 内存 AST 比较确认 `_file_ref`、`_write_check_receipt`、`build_fig2_series` 未变；默认容差、收据名、匹配逻辑及 fig1 字段校验保留。有限值序列的序列化字节不变。
- **§0.8：** 五个定向测试覆盖直接契约及已发现的 fig1 回归，调度方另跑全套的分工自洽。
- **§1.1：** 三项 stat 实测值与规定完全一致，未读取禁读文档内容。
- **§4：** 台账 P1/P5/P6/P7/P8/P9 对应全部六项登记；`split-run.md:183` 引用正确。stage2 的 :458 经 A4 序列化，:464 经 A1/A2 对账。
- F 单文件的 `invariant_scan.scan_python` 前后结果相同，未发现需修改受保护 manifest 的新增登记项；全量 invariant 验收未运行。

同族点未发现本段新增遗漏：bool、-Infinity、负向指数溢出、字符串“NaN”、对象型 pct 单点及正负超大整数，补充内存验证均生成 FAIL 收据。

消费者空线/覆盖率、stage2 裸读取、fig1 非豁免 NaN、非 pct 字段 1e400、fig1 豁免键整数溢出、普通 PASS/FAIL 分支写收据 OSError，均属已登记的范围外边界。

e）已检查现有测试输入与调用路径。

| 测试 | 核查结果 |
|---|---|
| test_figures_from_facts.py | :146、:337–344 的 NaN/Inf 属 fig1；:150–151 报错契约保持。flow 的 FACTS/SPEC（:22–49）及 check 序列（:174–181）为有限值。 |
| test_repair_batch1.py | :989 实际为 Infinity；:993–994 的字段名及“非有限”断言保持。 |
| test_stage2_closeout.py | facts :52–55、fig2-series :83–85 及相关变体未依赖非有限字面量；:562–574 的非 list、坏 JSON、缺文件契约内存执行保持。 |
| test_repair_batch_d.py | :1207–1212 的空 series 仍 PASS、lines_checked=0；:1597–1607 的序列及其 facts 来源均为有限值。 |
| test_a4_gate.py | :378–381 的 facts 合法，:506–512 使用空 series，无非有限字面量放行依赖。 |
| test_repair_g1_cross_target.py | 不直接调用 flow/check/fig2-series；基础夹具及 :185 收据设置未引入相关非有限输入。 |
| test_review_20260804_p105.py | :199–201 使用正供应量与空 entities，:224–229 使用空 series。 |
| test_repair_batch_c.py | FC5/F04 的 16 条原 check，替代 I/O 和子进程后，基线与 v4 均通过；原断言未改。 |

另核过 `test_batch15_three_ledgers_frozen.py:341–346`，只调用 fig1。

Git 中 v3 `9db4c97` → v4 `78148ec` 的差异确认：A1–A4 方案及用例 1–12 均未变；本次主要修订用例 13，并补登记两项既有边界。

开工、末检工作树均为空；指定内容目录相对 `4cbfe48` 的 Git 对象无差异；W、r1/r2/r3 回复、F、C 六个文件的 SHA-256 前后一致。本轮只读、离线、未改文件、未 commit，工具未读取禁读内容。报告全文已打印到 stdout。

Codex session ID: 01a0af10-67d6-7440-8e83-6461f307390f
Resume in Codex: codex resume 01a0af10-67d6-7440-8e83-6461f307390f
