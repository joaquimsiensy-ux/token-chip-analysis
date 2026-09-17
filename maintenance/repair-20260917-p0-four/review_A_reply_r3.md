# 工单A复核：退回

v3 的生产修复可以闭合 A-R2-01/02，但**用例 13 的基线描述错误，指定的 RED 取证方式也未处理实际异常**。需修订这一处后再施工。未发现确定会使现有 `run_all.py` 用例由绿变红的改动；全套未实跑，不能宣称全绿。

报告全文已打印到 stdout。全程只读、离线，未改文件、未 commit，工具未读取禁读文件内容。

复核对象为 [workorder_A.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_A.md)（W）；F＝[figures_from_facts.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py)，C＝[test_repair_batch_c.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_c.py)。以下均为施工前行号。

权限配置为 read-only，临时目录 CLI、五个定向测试及全套均**未实跑**。补充证据来自源码内存执行：按工单生成内存补丁，替代输入、收据及文件 I/O，未导入绘图库。下文 rc 按返回值、异常及 CLI 退出规则推导，不是实际子进程验收结果。

**A-R3-01〔中〕用例 13 的 RED 路径描述错误，取证方法需同步修订。**

**工单位置：** W:111，用例 13；W:113，RED 取证。

**事实：** W:111 写“基线 `mode_check` 对 `[NaN]` 返回 0 不抛”，但该例同时把 `_write_check_receipt` mock 为无条件抛 `OSError("disk full")`。基线虽然错误接受 NaN，仍会在返回前写 PASS 收据。实际 `grep -n -F` 输出：

```text
338:    _write_check_receipt(a, "PASS", okc, [])
```

因此 mock 在 F:338 抛错，F:342 的 `return 0` 不会执行。保持该 mock 的内存复现结果：

```text
基线：OSError: disk full；未返回 0，未抛 SystemExit
v3：SystemExit("FAIL: 图 2 对账输入不可用——…")
    stderr 含 "[CHECK-FAIL] 收据未更新（写入失败：disk full）"
```

W:113 只规定逐例捕获 `AssertionError`；直接等待 `SystemExit` 的写法会让基线 `OSError` 逃出，无法按指定方式收集断言失败原文。**改后的 GREEN 条件本身成立。**

**修订建议：** 将 RED 描述改为“基线写 PASS 收据时抛出未收敛的 OSError”。用例 13 内分别捕获 `SystemExit` 与 `OSError`，记录异常后用既有 `check()` 断言：

- 异常必须是 `SystemExit`。
- `.code` 必须为 `FAIL:` 开头的字符串。
- stderr 必须含“收据未更新”。

基线的 OSError 应转换成带原始异常详情的 `AssertionError`，供 W:113 收集；不能把任意异常都算 GREEN。

**a）锚文本核验**

已逐行实际执行 `grep -n -F`。明确修改锚均唯一、行号一致；上下文通用行并非全部唯一：

| 文件及行号 | 实际命中 |
|---|---|
| F:60、63–65、109、139–144、201–202、257、283–286、306、308、328–330、370–372、406 | 每行各 1 处，行号一致 |
| F:282 的 `try:` | 8 处：71、76、114、169、203、282、380、394 |
| F:307 的 `continue` | 3 处：102、303、307 |
| C:37–40、45、54、60、1109、1201、2106 | 每行各 1 处，行号一致 |
| C:1111–1120，依行顺序 | 2、3、7、8、2、2、2、2、6、3 处 |

W:14 已排除通用语句作锚，W:97 将 C:1111–1120 定义为参考夹具，因此这些重复不构成新的定位缺陷。A2 使用 F:306 唯一锚，再定位相邻 F:307/308，处置正确。

**b）r1 七条及 r2 两条处置**

| 编号 | 本次结论 |
|---|---|
| A-01 | 已闭合。`strict=False` 保留 fig1 字段级检查；NaN、Infinity 的内存执行均包含 `burn_cum_pct` 和“非有限”，符合两个原断言。其余六次 strict 调用未发现现有成功夹具依赖非有限字面量放行。 |
| A-02 | 正常可读、可写条件下已闭合。`_file_ref` 只读字节取 sha，不解析 JSON、不修改输入。用例 10 证明换输入后覆盖收据及更新 sha；用例 12 补足同输入旧 PASS 场景。 |
| A-03 | 已闭合，明确锚唯一。 |
| A-04 | 原十例的独立子函数与逐例捕获方式可行；新增用例 13 的异常取证问题见 A-R3-01。 |
| A-05 | 已闭合。macOS stat 命令只统计元数据，实得 8021 / 930070 / 8798。 |
| A-06 | 三处订正成立：7 次调用分布于 6 行；默认 json.dumps 能输出 NaN；用例 1 基线确实错误 PASS。 |
| A-07 | 已闭合，停工报告已列入白名单。 |

**A-R2-01：生产修复闭合。** `_pct_value_ok` 先排除 bool、非 int/float，再在 try 内执行 `math.isfinite(float(v))`，能够捕获转换溢出。内存执行确认：

- `10**308` 返回 True；`10**309`、正负 401 位整数返回 False。
- 用例 11 的列表推导会检查到超大整数；交换顺序、单独超大整数也均写 FAIL，无 OverflowError。
- 对 r2 原始组合输入先由基线签 PASS，v3 使用**同一份输入字节**重跑后写 FAIL，series.sha256 仍匹配，消费者报“非 PASS”。

**A-R2-02：A3 新增分支的生产修复闭合。** `isfile` 不能保证输入可读、收据可写；新增 OSError 捕获补上了这一点。分别在内存注入输入读取、临时文件创建、fsync、replace 失败，均得到明确 FAIL SystemExit，并提示“收据未更新”。

用例 10 不覆盖这些 I/O 失败；用例 13 的 GREEN 可以覆盖异常收敛，但 RED 说明须修订。

**c）A5 全部 13 例**

下表均为内存执行；临时目录 CLI **未实跑**。

| 用例 | 基线行为 | 按 v3 修改后的行为 |
|---|---|---|
| 1 NaN 末点 | rc 0，PASS 收据 | rc 1，“字面量”，FAIL 收据 |
| 2 中间点 1e400 | rc 0，PASS | rc 1，“非有限”，FAIL |
| 3 字符串 pct | rc 0，PASS | rc 1，“非有限”，FAIL |
| 4 null pct | TypeError，无收据 | rc 1，FAIL 收据 |
| 5 Infinity 字面量 | rc 1，FAIL；mismatches 为末点超差 | rc 1，“字面量”；mismatches[0] 含“输入不可用” |
| 6 exploration＋99 | rc 0，PASS | rc 1，FAIL，mode=exploration |
| 7 facts 含 NaN | rc 0，PASS | rc 1，“字面量”，FAIL |
| 8 dumps_fig2_series(NaN) | 不抛错，输出含 NaN | 抛 ValueError |
| 9 合法 27.8 | rc 0，PASS | rc 0，PASS |
| 10 合法 PASS 后改为 NaN | 第二次仍 rc 0、PASS | 第二次 rc 1、FAIL，series.sha256 匹配新输入 |
| 11 1e400＋超大整数＋27.8 | rc 0，PASS | rc 1，FAIL，无 OverflowError |
| 12 同输入手写 PASS | 消费者接受；重跑仍 PASS、仍接受 | 重跑写 FAIL；消费者报“非 PASS” |
| 13 收据函数抛 OSError | 抛 OSError，“返回 0”不成立 | FAIL SystemExit，stderr 含“收据未更新” |

1–8、10–12 的预期基线 RED 成立；9 是保持 GREEN 的回归例。13 能区分修复前后，但须按实际异常修订取证。内存补丁满足全部 13 例的改后目标条件，**不等于新增测试已经实现或通过真实验收**。

用例 5、6 的字段断言与写入函数一致：

```python
# F:264
"mode": "exploration" if a.exploration else "formal",
# F:267
"lines_checked": okc, "mismatches": errs,
```

A3 传入 `[f"输入不可用：{exc}"]`，因此 `mismatches[0]` 的断言正确；exploration 模式也会如实保留。

**d）既有测试、范围与同族点**

| 实际检查的测试 | 结论与证据 |
|---|---|
| test_figures_from_facts.py | :146、:337–344 的 NaN/Inf 属 fig1；:150–151 原断言保持。flow 的 FACTS/SPEC（:22–49、:157–170）及 check 输入（:174–181）均为有限值。 |
| test_repair_batch1.py | :989 实际输入为 Infinity；:993–994 的字段名及“非有限”断言由 strict=False 保留。 |
| test_stage2_closeout.py | facts :52–55、fig2-series :83–85 及所查变体未依赖非有限值。:562–574 的非 list、坏 JSON、缺文件契约内存执行前后一致。 |
| test_repair_batch_d.py | :1207–1212 的空 series 仍 rc 0、PASS、lines_checked=0；:1597–1607 使用有限浮点数。 |
| test_a4_gate.py | facts :378–381 合法；:506–512 使用空 series，无非有限字面量放行依赖。 |
| test_repair_g1_cross_target.py | 不直接调用 flow/check/fig2-series；已追查基础夹具及 :185 的收据设置，未见相关非有限输入依赖。 |
| test_review_20260804_p105.py | :199–201 使用正供应量与空 entities；:224–229 使用空 series。 |
| test_repair_batch_c.py | FC5、F04 的 16 条原 check，在内存替代 I/O 和子进程调用后，基线与 v3 均通过；原断言未改。 |

另核过 `test_batch15_three_ledgers_frozen.py:341–346`，仅调用 fig1。

- **§0.4：** 内存 AST 比较确认 `_file_ref`、`_write_check_receipt`、`build_fig2_series` 不变；默认容差、收据名、实体匹配及 fig1 豁免校验保留。有限序列的序列化字节前后一致。
- **§0.8：** 五个定向测试覆盖直接契约及已发现的 fig1 回归；调度方另跑全套的安排自洽。
- **§1.1：** stat 实测 `8021 / 930070 / 8798`，与约束一致，未读取禁读文档内容。
- **§4：** 台账 P1/P5/P6/P7 对应现有四项登记；`split-run.md:183` 引用正确，其中“fig2 必画下限自 7.1.0 由 stage2_closeout 承担”的边界须保留。
- **登记扫描：** F 单文件的 `invariant_scan.scan_python` 结果前后一致，未发现需要修改受保护 manifest 的新增登记项；这不是全量 invariant 验收。

| 同族点 | 归属 |
|---|---|
| bool、-Infinity、负向指数溢出、字符串“NaN”、对象型 pct 单点 | 本段已覆盖；补充内存执行均拒绝并写 FAIL。 |
| fig1 豁免键中的超大整数 | F:141–144 仍可能抛 OverflowError，已复现；§0.4 明确不改，属范围外，可补登记。 |
| 普通对账 PASS/FAIL 分支写收据时发生 OSError | F:334/:338 仍直接传播；A3 只收敛新增输入失败分支内的写入错误。属于本次改动之外的既有边界，可补登记，不能宣称所有收据写入都已收敛。 |
| stage2 裸读取、fig1 非豁免 NaN、非 pct 字段 1e400、消费者空线/覆盖率 | 范围外，已有登记；stage2 :458 经 A4 序列化、:464 经 A1/A2 对账。 |

**e）run_all.py 影响与末检**

未发现确定由 A1–A4 导致的现有用例回归。A-R3-01 是新增用例的 RED 取证缺陷，不是已证明的旧测试回归。真实 CLI、五个定向测试及 `run_all.py` 均未实跑。

开工、末检 `git status --porcelain=v1 --untracked-files=all` 均为空，末检 `git diff --name-only` 为空；指定内容目录相对 `4cbfe48` 的 Git 对象无差异。W、r1/r2 回复、F、C 五个文件的 SHA-256 复查均未变化。

Codex session ID: 01a0aeff-c218-7a52-be90-13121216617b
Resume in Codex: codex resume 01a0aeff-c218-7a52-be90-13121216617b
