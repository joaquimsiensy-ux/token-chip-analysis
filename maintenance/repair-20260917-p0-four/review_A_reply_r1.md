# 工单A复核：退回

v1 不能直接施工：A1 会破坏两个现有测试；A2 的明确锚文本不唯一；A3 可能保留仍被消费者接受的旧 PASS 收据；RED 取证方式和禁读规则也需要修订。

复核对象：[workorder_A.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_A.md)。以下行号均为当前基线。简称 F＝`scripts/report/figures_from_facts.py`，C＝`scripts/tests/test_repair_batch_c.py`。

全程离线、未改文件、未 commit，报告全文已打印到 stdout。当前沙箱只读，临时目录 CLI 和整套测试**未实跑**。补充证据来自源码内存执行：输入、收据 I/O 和拟议补丁均在内存中；退出码按现有 `main()/sys.exit` 规则推导，不作为真实子进程验收。

1. **A-01〔高〕A1 会使两个已有测试变红。**

   **工单位置：** A1，第 27–40 行；验收清单第 15 行。

   **事实：** F:109 的 `state = _load(a.state)` 先于 F:139–144 的字段级校验。新增解析钩子只报告 token，丢失 `burn_cum_pct`。现有断言原文：

   ```python
   # scripts/tests/test_figures_from_facts.py:150-151
   assert r.returncode != 0 and "burn_cum_pct" in (r.stdout + r.stderr) \
       and "非有限" in (r.stdout + r.stderr), r.stdout + r.stderr

   # scripts/tests/test_repair_batch1.py:993-994
   assert p.returncode != 0 and "burn_cum_pct" in (p.stdout + p.stderr)
   assert "非有限" in (p.stdout + p.stderr)
   ```

   内存复现：基线报 `FAIL: 豁免键「burn_cum_pct」[0] 为非有限数值 …`；按 A1 修改后报 `ValueError: JSON 非有限数值字面量 …`，不含字段名。输入前后都被拒绝，但两项测试从通过变为失败。两文件均已列入 `run_all.py:63/:100`。

   **修订建议：** 保留 fig1 的字段定位契约；严格解析若全局启用，应提供准确字段上下文，或调整严格解析的调用范围。将这两个测试加入定向验收，保留旧断言。

2. **A-02〔高〕“不写新收据”不能保证旧 PASS 失效。**

   **工单位置：** A3，第 59–68 行；A5，第 76 行。

   **事实：** A3 捕获异常后直接退出，没有处理已有收据。消费者原文：

   ```python
   # scripts/report/audit_release_gate.py:1361-1364
   if d.get("verdict") != "PASS":
       errors.append(f"figure2 对账收据 verdict={d.get('verdict')!r} 非 PASS")
   _figure2_input_check(case_dir, d.get("series"), "series", errors)
   _figure2_input_check(case_dir, d.get("facts"), "facts", errors)
   ```

   对同一份 NaN 输入先执行基线、再执行拟议补丁，内存复现：

   ```text
   baseline_rc 0
   patched_rc 1
   receipt_unchanged True
   check_figure2_receipt_errors []
   ```

   旧 PASS 的输入哈希仍匹配，因此该收据检查函数继续接受它。这里未声称完整发布闸通过。A5 每次预先清掉收据会避开此场景。

   **修订建议：** 在 producer 输入失败分支使旧收据失效，并增加“已有同输入 PASS 后失败重跑”的用例。若决定保留，应明确登记残余并修正第 68 行的保证；它不属于已登记的空线/覆盖率残余。

3. **A-03〔中〕A2 明确指定的锚不唯一，按 §0.5 应停工。**

   **工单位置：** §0.5，第 12 行；A2，第 44 行。

   **事实，实际命令和输出：**

   ```text
   grep -n -F '            continue' scripts/report/figures_from_facts.py
   102:            continue
   303:            continue
   307:            continue
   ```

   **修订建议：** 改用唯一的 `errs.append(f"{key} 线无 pct 数据")`（F:306）定位，再核对紧邻的 continue 和 `last = float(pct[-1])`。

4. **A-04〔中〕直接顺序复用 check()，无法一次取得指定五例的 RED 原文。**

   **工单位置：** A5，第 76、88 行；§0.7，第 14 行。

   **事实，C:54–57：**

   ```python
   def check(name, cond, detail=""):
       if not cond:
           raise AssertionError(f"{name}: {detail}")
       PASSED.append(name)
   ```

   用例 1 在基线首先抛异常；内存验证的已访问编号为 `[1]`，2/3/4/6 不再执行。第 88 行给出的单次函数调用，若直接顺序复用辅助函数，取不到全部要求的证据。

   **修订建议：** 明确逐例独立运行，或逐例捕获 AssertionError、打印原始结果，最后汇总抛错；保留既有 check()。

5. **A-05〔中〕§1.1 的字节验收命令会读取禁读文件。**

   **工单位置：** §1.1，第 19 行；§0.2，第 9 行。

   **事实，工单命令：**

   ```sh
   find references -name '*.md' -print0 | xargs -0 cat | wc -c
   ```

   文件名枚举确认它包含 `references/attic.md`，执行 cat 会违反禁读要求。本次未执行该内容读取命令。

   **修订建议：** 改为汇总 stat 字节大小。按元数据汇总，三数确为 `8021 / 930070 / 8798`；字节约束本身与改动范围相容。

6. **A-06〔低〕三处说明存在事实错误。**

   **工单位置：** A1 第 40 行、A3 第 68 行、A5 第 76 行。

   **事实与修订建议：**

   - `_load` 实际有 **7 次调用，分布在 6 行**；补齐 flow facts 和 fig2-series 双输入。
   - “json.dumps 写不出 NaN 字面量”不成立：本机实测 `json.dumps(float("nan"))` 输出 `NaN`。保留 write_text 要求，但理由应改为控制精确输入文本，尤其确保 `1e400` 不被重新编码为 Infinity。
   - “NaN 字面量由 traceback 变为 FAIL”未准确描述完整基线：用例 1 原本 PASS。应明确“基线错误 PASS；加入 A1 后产生 ValueError，A3 再转换为明确失败退出”。

7. **A-07〔低〕停工报告路径未列入写入白名单。**

   **工单位置：** §0.1，第 8 行；§0.3，第 10 行。

   **事实：** §0.1 要求新建 `A_done_attempt1_stopped.md`，§0.3 只允许两个代码文件以及 `A_done.md`、`A_red_evidence.txt`。

   **修订建议：** 将停工报告列入白名单，或明确声明停工时的例外。

**a）锚点核验。** 全部引用原文均位于所标行号，没有发现行号漂移。逐行 `grep -n -F` 结果：

| 文件及原行号 | 命中数 |
|---|---|
| F:60、63–65、139–144、283–286、304–306、308、328、370–372 | 每行均 1 |
| F:282 的 `    try:` | 8：71、76、114、169、203、282、380、394 |
| F:307 的 `            continue` | 3：102、303、307 |
| C:1109、1201、2106 | 每行均 1 |
| C:1111→1120，按行顺序 | 2、3、7、8、2、2、2、2、6、3 |

片段引用中的通用语句不能直接当作唯一定位锚。

**b）_load 调用及异常契约。**

| 调用点 | 输入与结论 |
|---|---|
| F:109 | fig1 state；存在 A-01 的确定测试回归 |
| F:201 | flow facts；解析范围收紧，所查合法成功夹具未见受影响 |
| F:202 | flow spec；同上 |
| F:283 | check facts；用例 7 按预期从放行改为拒绝 |
| F:284 | check series；NaN/Infinity 按预期在解析层拒绝 |
| F:406，第一个 `_load` | fig2-series 的 entity_series；合法有限值夹具不变 |
| F:406，第二个 `_load` | fig2-series 的 facts；同上 |

`_reject_constant` 抛 ValueError 与 F:285–286 的透传一致，也符合 `test_stage2_closeout.py:569–574`。内存执行确认：缺文件、坏 JSON 前后均抛 ValueError；CLI 层才将其转换为退出。

**c–d）A2/A3 控制流。** A2 插在 F:307 之后、308 之前正确，math 已在 F:46 import。本机实测解析 `1e400` 得到 inf，`parse_constant` 回调次数为 0，确实进入 A2。

A3 不改变 F:329–330 的非 list 特判；`{}` 仍退出 1、不写收据。正常对账的 PASS/FAIL 写入分支、schema 和字段保留。无旧收据时，NaN 路径为 stderr 的 FAIL 消息、退出 1、无新收据；旧收据问题见 A-02。

**e）九例基线行为。** 以下为源码内存执行及 CLI 退出规则推导；临时目录 CLI **未实跑**。

| 用例 | 基线行为 | 按 A1–A4 修改后的行为 |
|---|---|---|
| 1 NaN 末点 | 0，PASS 收据 | 1，字面量报错，无新收据 |
| 2 中间点 1e400 | 0，PASS 收据 | 1，非有限报错，FAIL 收据 |
| 3 字符串 `"27.8"` | 0，PASS 收据 | 1，非有限报错，FAIL 收据 |
| 4 null | TypeError，预期 CLI 1，无收据 | 1，FAIL 收据 |
| 5 Infinity | 1，末点超差报错，FAIL 收据 | 1，字面量报错，无新收据 |
| 6 exploration＋99 | 0，PASS 收据 | 1，无新收据 |
| 7 facts 未使用字段含 NaN | 0，PASS 收据 | 1，字面量报错 |
| 8 dumps_fig2_series | 不抛错，输出包含 `"pct":[NaN]` | 抛 ValueError |
| 9 合法 27.8 | 0，PASS 收据 | 0，PASS 收据 |

1–8 的预期 RED 判断成立，9 是保持通过的回归例。用例 4 的异常原文：

```text
TypeError: float() argument must be a string or a real number, not 'NoneType'
```

辅助设施：C:60 的 `run(cmd, cwd, env=None)`、C:54 的 check、C:45 的 A 可复用。C:1111 的 fff 是函数局部变量，新函数需照抄初始化。C:37–40 已加入 report 路径；模块定位确实解析到本仓库的 F，用例 8 的导入写法可行。本次验证了模块定位和函数行为，未执行完整绘图库导入。

**f）范围与同族点。** 拟议改动保留 DEFAULT_TOL_PP、CHECK_RECEIPT_NAME、收据写入函数和 F:289–303 匹配逻辑。F 内只有 :65 这一处裸 json.load，所有相关 JSON 输入均经过 `_load`，没有漏掉第二处独立加载器。

相关的另一处裸读取是 `scripts/report/stage2_closeout.py:63` 的 json.loads；:459 读取源 series，:468 再读 whale_series。它属于**本段范围外**，且 :458 的重放序列化经过 A4，:464 的对账经过 A1/A2。消费者不验空线/覆盖率仍按 §0.4 登记不修。

**g）现有测试影响。**

| 测试 | 复核结论 |
|---|---|
| test_repair_batch_c.py | 所查有限值、容差和收据断言未见被拟议改动破坏；整文件未实跑 |
| test_stage2_closeout.py | 非 list、坏 JSON、缺文件契约保持；有限值序列化不变；整文件未实跑 |
| test_repair_batch_d.py | :1207–1212 的空 series `[]` 仍返回 0、写 0 条线的 PASS；内存确认，端到端未实跑 |
| test_figures_from_facts.py | :150 的字段名断言会失败 |
| test_repair_batch1.py | :993 的字段名断言也会失败 |

工作树末检：已跟踪文件 `git diff --name-only` 为空。开工时 status 为空，末检出现 `?? maintenance/repair-20260917-p0-four/construct_A_prompt.md`；本次未创建、读取或修改该文件。该末检状态不满足后续施工 §0.1 的空工作树要求。

Codex session ID: 01a0aeda-c98d-7400-a766-c8157396070d
Resume in Codex: codex resume 01a0aeda-c98d-7400-a766-c8157396070d
