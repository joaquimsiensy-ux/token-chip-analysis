# 工单A复核：退回

v2 修复了 r1 的主要问题，但仍有两项需要修订：新增有限值检查可能抛出 `OverflowError`，保留仍被收据检查函数接受的旧 PASS；A3 的 `isfile` 守卫不足以保证失败收据可写。

未发现确定会使现有 `run_all.py` 用例由绿变红的改动，但全套**未实跑**，不能宣称全绿。报告全文已打印到 stdout。

复核对象：[workorder_A.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_A.md)（下称 W）。F＝[figures_from_facts.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py)，C＝[test_repair_batch_c.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_c.py)。以下均为施工前基线行号。

全程只读、离线，未改文件、未 commit。沙箱禁止写入，因此临时目录 CLI、五个定向测试和 `run_all.py` 均**未实跑**。补充证据来自源码内存执行：拟议补丁、输入和收据均在内存中；未导入绘图库。以下 rc 按 CLI 退出规则推导，不算真实子进程验收。

1. **A-R2-01〔高〕A2 检查超大整数时抛 OverflowError，仍可留下有效绑定的旧 PASS。**

   **工单位置：** W:48–53、63–71；A5 W:84–95。

   **事实，实际 grep 输出：**

   ```text
   grep -n -F 'if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)' maintenance/repair-20260917-p0-four/workorder_A.md
   49:               if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)]

   grep -n -F '    except ValueError as exc:' maintenance/repair-20260917-p0-four/workorder_A.md
   65:    except ValueError as exc:
   ```

   超大整数本身有限，但 `math.isfinite` 会将它转换成浮点数。本机执行 `math.isfinite(10**400)` 抛出：

   ```text
   OverflowError: int too large to convert to float
   ```

   使用 A5 的 facts，pct 原文由以下表达式生成：

   ```python
   "[1e400," + "1" + "0" * 400 + ",27.8]"
   ```

   `1e400` 解析为 inf，不经过 `parse_constant`；列表推导式随后遇到 401 位整数便溢出，尚未进入追加 errs 的分支。A3 只捕获 `ValueError`，因此不会更新收据。

   对**同一份输入字节**先执行基线签收据，再执行 v2，内存结果：

   ```text
   baseline_rc: 0
   baseline_check_figure2_receipt_errors: []
   v2_exception: OverflowError
   receipt_unchanged: True
   receipt_verdict: PASS
   series_sha_matches: True
   v2_check_figure2_receipt_errors: []
   ```

   调换超大整数与 `1e400` 的顺序，结果相同。这里证明的是 `check_figure2_receipt` 仍接受收据，未声称完整发布闸通过。

   **修订建议：** 在 A2 将数值检查的转换溢出归入输入错误，进入既有 errs／FAIL 收据分支；保留纯 helper 不写收据的边界。增加上述组合输入及“同输入旧 PASS 后失败重跑”断言，覆盖退出码、FAIL 收据、当前输入 sha 和消费者拒绝。此项属于本段。

2. **A-R2-02〔中〕isfile 只验证文件类型，写 FAIL 收据时仍可能再次抛出未处理异常。**

   **工单位置：** W:65–74。

   **事实，代码原文：**

   ```python
   # W:69-71
   if os.path.isfile(a.facts) and os.path.isfile(a.series):
       _write_check_receipt(a, "FAIL", 0, [f"输入不可用：{exc}"])
   raise SystemExit(f"FAIL: 图 2 对账输入不可用——{exc}")

   # F:223-227
   def _file_ref(path):
       with open(path, "rb") as fh:
           data = fh.read()
       return {"path": os.path.basename(str(path)),
               "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
   ```

   F:285–286 将读取失败的 `OSError` 转成 `ValueError`；A3 随后调用 `_write_check_receipt`，F:266 又通过 `_file_ref` 读取两个输入。常规文件不等于可读文件。

   内存故障注入“`isfile=True`、读取抛 `PermissionError`”得到：

   ```text
   exception: PermissionError
   new_receipt: absent
   output: PermissionError: [Errno 13] Permission denied ...
   ```

   最后的明确 FAIL 退出语句未执行。收据临时文件的创建、`fsync`、`replace` 同样没有异常收敛。用例 10 的可读、可写 tempdir 不覆盖这些分支。

   **修订建议：** 区分“JSON 无法解析但字节可读”和“输入读取／收据写入失败”；捕获收据写入过程的 `OSError`，仍明确 FAIL 退出，并如实说明收据未更新。增加故障注入断言，无需改变收据 schema。

r1 七条处置结果：

| r1 编号 | v2 复核结果 |
|---|---|
| A-01 | 原回归已闭合。`strict=False` 保留字段级拒绝；NaN、Infinity 的内存执行均包含 `burn_cum_pct`、`非有限`，符合两个旧断言。 |
| A-02 | 原始 NaN 场景已闭合：同输入先由基线签 PASS，再用 v2 重跑，会写 FAIL，消费者报“非 PASS”。异常边界仍有上述两项缺口。 |
| A-03 | 已闭合。A2 明确锚改为唯一的 F:306，紧邻 F:307/308 正确。 |
| A-04 | 已闭合。独立子函数加逐例捕获 `AssertionError`，可以取得后续用例的 RED；既有 `check()` 不必改。取证可用内联 Python，避免新增白名单外文件。 |
| A-05 | 已闭合。macOS stat 命令只读元数据；实得 `8021 / 930070 / 8798`。 |
| A-06 | 三处订正成立：7 次调用分布于 6 行；`json.dumps` 默认能输出 NaN；用例 1 基线确实错误 PASS。 |
| A-07 | 已闭合。W:11 已将 `A_done_attempt1_stopped.md` 列入白名单。 |

锚点已逐行实际执行 `grep -n -F`。明确修改锚均唯一、行号一致；上下文片段不能全部当作唯一锚：

| 文件及基线行号 | 实际命中 |
|---|---|
| F:60、63–65、109、139–144、201–202、257、283–286、306、308、328–330、370–372、406 | 每行各 1 处，均在所标行 |
| F:282 的 `try:` | 8 处：71、76、114、169、203、282、380、394 |
| F:307 的 `continue` | 3 处：102、303、307 |
| C:37–40、45、54、60、1109、1201、2106 | 每行各 1 处，均在所标行 |
| C:1111–1120，按行顺序 | 2、3、7、8、2、2、2、2、6、3 处 |

v2 §0.5 已排除通用语句作锚，C:1111–1120 被标为参考夹具，因此这些重复不构成新的停工点。C:1111 的 `fff` 确为局部变量，各新增子函数自行初始化的要求正确。

A5 十例断言核对如下，均为**内存执行，临时目录 CLI 未实跑**：

| 用例 | 基线行为 | 按 v2 修改后的行为 |
|---|---|---|
| 1 NaN 末点 | rc 0，PASS 收据 | rc 1，字面量报错，FAIL 收据 |
| 2 中间点 1e400 | rc 0，PASS | rc 1，非有限报错，FAIL |
| 3 字符串 pct | rc 0，PASS | rc 1，非有限报错，FAIL |
| 4 null pct | TypeError，无收据 | rc 1，FAIL 收据 |
| 5 Infinity 字面量 | rc 1，FAIL；mismatches 为末点超差 | rc 1，字面量报错；`mismatches[0]` 含“输入不可用” |
| 6 exploration＋99 | rc 0，PASS | rc 1，FAIL，`mode=exploration` |
| 7 facts 未使用字段含 NaN | rc 0，PASS | rc 1，字面量报错，FAIL |
| 8 dumps_fig2_series(NaN) | 不抛错，输出含 NaN | 抛 ValueError |
| 9 合法序列 | rc 0，PASS | rc 0，PASS |
| 10 合法 PASS 后改为 NaN | 第二次仍 rc 0、PASS | 第二次 rc 1、FAIL，series.sha256 匹配新输入 |

1–8、10 的基线 RED 断言成立，9 是保持 GREEN 的回归例；v2 对这十例的预期断言全部成立，但未覆盖 A-R2-01/02。

用例 5、6 的字段与写入函数一致，实际 grep 输出：

```text
264:           "mode": "exploration" if a.exploration else "formal",
267:           "lines_checked": okc, "mismatches": errs,
```

用例 10 能证明“既存收据被覆盖且新 sha 正确”；但它先改变输入，旧 PASS 的 sha 在第二次运行前已失配，单凭它不能证明 r1 的“旧 PASS 对当前输入仍有效”前提。本次已额外在内存验证普通 NaN 的同输入场景能够正确覆盖。

A3 的普通解析失败路径可行：`_file_ref` 二进制读取原始字节，不重新解析 JSON、不改输入；坏 JSON、NaN/Infinity、无效 UTF-8 都可在字节可读时生成 FAIL 收据。写收据是 `_write_check_receipt` 的预期副作用，并非取 sha 的副作用。缺文件、目录输入会被 `isfile` 挡住；不可读常规文件见 A-R2-02。

现有测试及 `run_all.py` 影响：

| 测试 | 实际核对结果 |
|---|---|
| `test_figures_from_facts.py` | :146/:150–151 的 NaN、:337–344 的 NaN/Inf 均属 fig1。flow 的 FACTS/SPEC（:22–49、157–170）和 check 序列（:174–181）未含非有限字面量。 |
| `test_repair_batch1.py` | :989 实际为 Infinity；:993–994 的字段名／非有限断言由 `strict=False` 保留。 |
| `test_stage2_closeout.py` | :52–55 的 facts、:83–85 的 fig2-series 输入为有限值；所查变体没有 NaN/Infinity。:562–574 的非 list、坏 JSON、缺文件契约内存核对保持。 |
| `test_repair_batch_d.py` | :1167–1168 的 facts 合法；空 series 仍 rc 0、PASS、lines_checked=0；:1597–1607 使用有限浮点数。 |
| `test_a4_gate.py` | :378–381 的 facts 合法，:506–512 使用空 series；没有依赖非有限字面量放行。 |
| `test_repair_g1_cross_target.py` | 未直接调用 flow/check/fig2-series；核过基础夹具来源和收据设置，未见相关非有限输入。 |
| `test_review_20260804_p105.py` | :199–201 的 facts 为 total_supply_raw=1、entities={}，:224–229 使用空 series。 |
| `test_repair_batch_c.py` | FC5 收据链、F04 容差断言与拟议代码相容；默认 PASS、超差 FAIL、formal 改容差 exit 2、exploration 放宽 PASS 的内存结果均保持。 |

另查到 `test_batch15_three_ledgers_frozen.py:341–346` 只调用 fig1，不受六次 strict 调用收紧影响。对 F 单文件实际执行 `invariant_scan.scan_python`，拟议修改前后的 schema、原子写入等登记扫描结果一致；这不是全量 invariant 或 suite 验收。

范围与登记核对：

- §0.4：拟议改动只需 F、C 两个代码文件；默认容差、收据名、schema/字段、实体匹配 F:289–303、fig1 豁免校验 F:139–144 均可保持原样。内存 AST 比较确认 `_file_ref`、`_write_check_receipt`、`build_fig2_series` 未变，合法序列化字节也相同。
- §0.8：五个定向测试覆盖直接调用和 r1 已发现的回归；调度方另跑全套的分工自洽。
- §1.1：三项字节数与约束完全一致。
- §4：`code_change_pending.md:5/:9/:10` 已对应登记空线／覆盖率、stage2 裸读取、fig1 非豁免键 NaN。stage2 的 :458 序列化经过 A4，:464 对账经过 A1/A2。
- 非阻断文字订正：W:12/:103 和台账引用的 `split-run.md:184` 是空行，实际残余说明在 :183；建议修正引用，并保留其中“fig2 必画下限自 7.1.0 由 stage2_closeout 承担”的边界。

同族点及归属：

- **本段遗漏：** A-R2-01 的数值检查溢出、A-R2-02 的失败收据 I/O 异常。
- **本段已覆盖、A5 未单列：** bool、-Infinity、负向指数溢出和字符串 `"NaN"`；内存补充验证均拒绝并写 FAIL。
- **范围外：** `parse_constant` 不能阻止其他字段中的 `1e400` 解析成 inf；pct 由 A2、输出序列由 A4 继续检查。fig1 非豁免字段、stage2 裸读取及消费者空线／覆盖率按现有范围登记。

开工、末检 `git status --porcelain=v1 --untracked-files=all` 均为空，`git diff --name-only` 为空；指定内容目录相对 `4cbfe48` 的 Git 对象无差异。W、r1 报告、F、C 的 SHA-256 复查均未变化。本次工具操作未读取禁读内容。

Codex session ID: 01a0aeec-3d57-7ec0-b5c9-f33b0b1930f6
Resume in Codex: codex resume 01a0aeec-3d57-7ec0-b5c9-f33b0b1930f6
