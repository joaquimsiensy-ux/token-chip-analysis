# 工单F01复核：退回

v1 能阻断裁决中的三个反例，但不能直接施工：第二源非有限值会触发序列化异常，破坏 Q1 约定；兼容性、阈值测试和诊断条数也有事实性表述需要修订。

复核 HEAD 为 `fe720803ba2c62f808d9294163d11fdddfc8c495`，代码行号按 `868d3f61`。全程只读、离线，未修改文件、未 commit，未读取 `~/.codex/`、memories 或其他禁读内容；开始、结束时工作区均无变更。

完整测试 `python3 -B scripts/tests/test_stage2_closeout.py` 在第 17 行创建临时目录时失败，错误为 `FileNotFoundError: No usable temporary directory found`，尚未执行用例。以下区分源码静态核对与源码在内存中的执行结果，不将其称为完整回归通过。

**F01-R1-01：第二源非有限值仍进入收据，Q1 的退出码约定无法兑现。**

工单位置：[§2.1，第 41 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/workorder_F01_price_nonfinite.md:41)、第 42、44 行；台账 Q1。

事实：新增条件只设置 `status="SKIP"`、`dev=None`，没有改变 `p2`。生产者仍执行以下原文：

```text
183:        results.append({"day": day, "main_price": p1, "second_price": p2,
184:                        "second_note": src2, "deviation_pct": dev, "status": status})
198:        with open(a.out, "w") as f:
```

因此，`allow_nan=False` 的异常路径并非“不可能”。按工单在内存中执行生产者，主价三天均为 `1.0`，得到：

| 第二源 | 带 `--out` | 不带 `--out` |
|---|---|---|
| `nan`、`inf`、`-inf` | `ValueError`；CLI 退出 1；输出已打开并留下不完整 JSON | ALL_SKIP，退出 3 |
| `None`、`0.0`、`-1.0` | 完整收据，ALL_SKIP，退出 3 | ALL_SKIP，退出 3 |

异常文案示例：`ValueError: Out of range float values are not JSON compliant: nan`。这不能作为符合 Q1 的结果接受。此外，测试 helper 第 104 行只捕获 `SystemExit`，遇到此路径会直接传播 `ValueError`。

修订建议：将非有限第二价规范化为可序列化的缺失值，例如在写入点记录前转成 `None`，保留 SKIP 语义；补充带 `--out` 的第二源 NaN/±inf 用例，并改掉“只剩不可能路径”的说明。无需增加收据键。

**F01-R1-02：消费者同时收紧了有限但非正的主价，旧收据兼容性承诺过强。**

工单位置：[§2.2，第 65 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/workorder_F01_price_nonfinite.md:65)、台账 Q4、裁决“版本档位”。

事实：生产者原文包含：

```python
if p2 is None or p2 <= 0 or p1 <= 0:
    status, dev = "SKIP", None
```

工单消费者则要求：

```python
ok1 = isinstance(p1, (int, float)) and not isinstance(p1, bool) and math.isfinite(p1) and p1 > 0
```

主价为 `[0.0, 1.0, 1.0]`、第二源固定 `1.0` 时，真实生产者仍返回 0，产出 `SKIP/PASS/PASS`、总 verdict 为 PASS；旧消费者放行，新消费者拒绝 `points[0].main_price`。将首价换成 `-1.0` 结果相同。

因此，“同规则”只对正常正数比较分支成立；“真实生产者生成，故旧 PASS/WARN 收据必然一致”不成立。这不是现有测试变红，而是未交代清楚的兼容范围变化。

修订建议：明确消费者额外拒绝非正主价，并将兼容性承诺限定到满足新条件的收据，补充迁移说明；如果目标是保持原有 SKIP 兼容性，则需调整逐点规则。不能同时保留当前规则与无条件兼容承诺。

**F01-R1-03：6d 不能守住两处阈值漂移。**

工单位置：[台账 Q2](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/code_change_pending.md:6)、工单 §2.3 第 96、100 行。

事实：6d 只验证 `1.0/2.0 → 66.67% → FAIL`，断言原文为：

```python
assert any("points[1].status" in e and "FAIL" in e for e in errors), errors
```

将消费者阈值单独改成 `6.0/16.0` 后，内存执行确认：6d 仍通过，既有 `0% PASS`、`7.69% WARN`、`66.67% FAIL` 样例的分类也不变。

修订建议：保留复制常量的方案，但在测试层显式检查两端阈值相等及固定值，并覆盖阈值附近；否则删除 Q2 中“由 6d 守漂移”的保证。

**F01-R1-04：“最多多出一条汇总诊断”应为最多两条。**

工单位置：[§2.2 说明③，第 80 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/workorder_F01_price_nonfinite.md:80)。

事实：消费者现有两项检查独立执行：

```text
272:    if receipt.get("verdict") != expected:
273:        errors.append(workorder_error("bindings.price_source_checks.verdict",
274:                                      f"与 points 重算一致（{expected}）", receipt.get("verdict")))
275:    if expected not in ("PASS", "WARN"):
276:        errors.append(workorder_error("bindings.price_source_checks.verdict",
277:                                      "PASS|WARN（FAIL/ALL_SKIP 禁入装配：换源或人工裁决后重跑 price_check）", expected))
```

一个点 `main_price=NaN`、自报 `status=FAIL`，收据声明 `verdict=PASS` 时，共三条错误：一条主价错误、两条 verdict 错误。它们分别说明数值非法、声明与汇总不符、汇总结论不可放行，并不矛盾。

修订建议：改成“逐点主价错误之外，汇总层还可能产生 0～2 条诊断”。无需修改现有汇总代码。

**F01-R1-05：Q4 的文本检索不能证明零迁移成本。**

工单位置：[台账 Q4](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/code_change_pending.md:8)、工单第 4、113 行。

事实：Q4 所列检查是有限目录深度下的 `grep -lE 'NaN|Infinity'`。而生产者第 75、79、81 行均使用 `float(p)`；默认 JSON 解析也接受溢出为 infinity 的数值。内存核验：

| 文件内容 | 该正则命中 | 新 `_load_series` 拒绝 |
|---|---:|---:|
| CSV `nan`、`inf`、`-inf` | 否 | 是 |
| JSON 数值 `1e309` | 否 | 是 |

此外，这项检索没有覆盖 R1-02 的有限非正主价问题。本轮遵守禁读约束，没有打开台账所列 Desktop 案卷，因此也没有独立确认其历史“0 命中”。

修订建议：将结论限定为“所述文本检索范围内 0 命中”，不要据此推出零迁移成本。由调度方按实际解析规则核验存量，并另核收据主价是否满足新条件；本轮无需突破禁读范围。

**其余逐项核对结果如下。**

**a）§2 锚点全部正确。** 实际执行了每个完整锚文本的 `grep -n -F`；下表长文本仅为展示缩写。

| 文件 | 锚文本 | 预期／实际行号 | 命中数 |
|---|---|---:|---:|
| `price_check.py` | `import os` | 34／34 | 1 |
| 同上 | `时间戳 >1e12 自动判毫秒。` | 18／18 | 1 |
| 同上 | `out = [(t // 1000 …) for t, p in out]` | 84／84 | 1 |
| 同上 | `if p2 is None or p2 <= 0 or p1 <= 0:` | 175／175 | 1 |
| 同上 | `json.dump(out, f, ensure_ascii=False, indent=1)` | 199／199 | 1 |
| `stage2_closeout.py` | `import os` | 15／15 | 1 |
| 同上 | `PRICE_POINT_STATUSES = ("PASS", "WARN", "SKIP", "FAIL")` | 240／240 | 1 |
| 同上 | docstring 起锚 | 244／244 | 1 |
| 同上 | docstring 止锚 | 245／245 | 1 |
| 同上 | `statuses = [(p.get("status") …) for p in points]` | 268／268 | 1 |
| `test_stage2_closeout.py` | `# 7 内联纯申报对象拒；内联带 receipt（ARC 形态）放行` | 659／659 | 1 |

**b）来源断言与主要分支。**

- 就 `price_check.py --price-file` 而言，`_load_series` 是唯一价格内容解析入口；第 50 行另有原文件哈希读取，不是价格解析。第 175、180 行是唯一逐点判级分支，第 197～199 行是唯一收据文件写入位置。
- CSV 的 NaN/±inf，以及 JSON 列表、`{"prices": …}` 两种结构中的 NaN/±Infinity，均经过新增有限性检查。它检查全部解析点，早于按日取价及抽样。`sys.exit(str)` 退出 1，与原第 61、66、83 行一致。
- `load():63` 的默认 `json.loads` 确实把 `NaN` 解析成 float nan。实测 `json.dumps(float("nan")) == "NaN"`，读回后 `math.isnan(...)` 为真。
- 全生产脚本检索未发现另一条价格收据语义判定路径。`price_receipt_errors` 同时处理顶层引用和内联 `receipt`；调用点为 `workorder_errors:405`。引用哈希另由 `workorder_errors` 的通用路径核验承担，不能将所有收据读取、哈希消费都归于该函数。
- 两处偏差表达式的 AST 完全相同。bool 明确排除于有效价格之外；主价 bool 被拒，第二价 bool/None 按 SKIP 重算。非 dict 点仍由原汇总逻辑拒绝。
- Q2“不 import”的依赖隔离理由成立：生产者第 38 行导入 `requests`，第 41 行导入 `llama_price`。但登记为 requests 脚本不等于扫描器追踪传递导入。内存核验 `from price_check import WARN_PCT, FAIL_PCT` 时，消费者的扫描结果仍无 transport；直接 `import requests` 才被识别。`invariant_scan.py:1159/:1164` 只检查直接导入。

阈值边界推演与内存计算一致：

| 主价／第二价 | `round(..., 2)` | 两端分类 |
|---|---:|---|
| 204.99／195.01 | 4.99% | PASS |
| 205／195 | 5.00% | PASS |
| 205.01／194.99 | 5.01% | WARN |
| 214.99／185.01 | 14.99% | WARN |
| 215／185 | 15.00% | WARN |
| 215.01／184.99 | 15.01% | FAIL |

**c）既有测试回归面：未发现会由本段必然造成的既有测试失败。** 这是静态核对及函数内存执行结论，完整测试受沙箱限制。

`price_receipt_content_enforced` 段 1～7：

| 段 | 核验结果 |
|---|---|
| 1 | 真实 FAIL 收据仍退出 2，消费者报 verdict 禁入 |
| 2 | FAIL points 搭配 PASS verdict 仍报重算不一致 |
| 3 | `1.0/1.08` 为 7.69% WARN；无 errors，保留 `WARN 点 3` NOTE |
| 4 | 错误 `price_file_sha256` 仍报绑定不一致 |
| 5 | 缺少 `price_file_sha256` 仍报“在场” |
| 6 | 第二价 None 仍为 ALL_SKIP、退出 3，消费者拒绝 |
| 7 | 纯内联声明仍拒；含合法 receipt 引用仍放行 |

19 条 mutation 不改点价格；其种子收据全为 `1.0/1.0 PASS`，新循环不增加错误。`workorder_errors` 前后 AST 不变，相关缺失绑定、缺失哈希、内联引用分支的消费者输出也经内存比对一致。以下全部仍 BLOCK，且保留表中 field 名：

| 测试行 | mutation／错误 field |
|---:|---|
| 519 | 删除 `bindings.price_source` |
| 520 | 删除 `fig2.price_source` → `fig2.price_source\|price` |
| 521 | 改为 volume 路径 → `fig2.price_source\|price` |
| 522 | 删除 `price_source_checks` |
| 523 | 删除主源 sha → `bindings.price_source` |
| 524 | 删除序列 sha → `fig2.lines[0].series_source` |
| 525 | spec sha=None → `flow.charts[0].spec` |
| 526 | 删除 `fig3.volume` |
| 527 | 自引用 key 错误 → `fig3.events_input` |
| 528 | 非法自引用 → `bindings.bad_self` |
| 529 | 删除 `fig1.overlay` |
| 530 | state 路径错误 → `fig1.state` |
| 531 | 未验证 CSV 引用 → `fig1.price_csv` |
| 532 | 删除 `fig2.out` |
| 533 | 空事件 → `fig3.events` |
| 534 | 报告路径错误 → `bindings.report_md.path` |
| 535 | 重复图片引用 → `report_image_refs` |
| 536 | 输出路径穿越 → `fig2.out` |
| 537 | 主价绝对路径 → `bindings.price_source.path` |

全 `scripts/tests` 检索四个指定词，命中仅在 `test_stage2_closeout.py`：主价构造在第 115 行，三点均为 `1.0`；收据生成 helper 在第 93 行，调用点为 117、633、643、656、660；收据修改在 639、648、652；其余命中是引用、绑定和哈希操作。现有测试没有 `main_price` 非有限值构造。

`test_stage2_reseal.py:436/:646` 复用 `build_closeout_case`；未发现另造非有限价格。`test_a4_gate.py`、`test_audit_release_gate.py` 也没有这类夹具。

**d）新增 6b／6c／6d 成立。**

按工单在内存中替换源码、以内存流替代文件读写，结果为：

| 用例 | 基线 | 按工单修改后 |
|---|---|---|
| 6b | 返回 0、生成收据，断言 RED | 返回 1、未打开收据输出 |
| 6c | `errors=[]`，断言 RED | 一条 `points[0].main_price` 错误 |
| 6d | `errors=[]`，断言 RED | 一条 `points[1].status` 错误，预期 FAIL |

6d 重算为 `round(1 / 1.5 * 100, 2) = 66.67`。

插入位置正确：顶层 `price_source_checks` 到原第 662 行才移除。6b 使用独立文件名；6c、6d 各自重建 PASS 收据；段 7 第 660 行再次重建，随后内联引用使用新哈希，前置状态不受影响。

**e）白名单和登记守卫足够。**

当前修法及上述最小修订均可限于白名单内的两个生产文件、一个测试文件。新增 `math`、两个数值常量不新增 schema、transport、原子写入点或正式入口，无需修改两个 manifest。

实际执行结果：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

对工单修改后的内存源码再次扫描，两文件的登记项目与基线相同，完整 `validate_manifest` 返回 `[]`；`exemption_violations()` 也返回 `[]`。`test_batch4_invariant_guards.py`、`test_exemption_guards.py` 未整套运行；源码未显示新增 math／常量需登记。

§0.4 的 `load()`、汇总规则、哈希绑定、12 项 checks 和返回类型可保持不变；但它不能掩盖 R1-01 的退出行为冲突。另，CSV 日期截断实际在 `_load_series:71`，不是 `_daily_close` 本体；拟议代码确实没有修改该口径。

**f）三个终点判据均能命中指定拒绝点。**

以下新行号为严格按 v1 文本插入后的预测行号，代码未落盘：

- 三天 `close=NaN` CSV：在基线第 84 行后的新增检查拒绝，预计 `price_check.py:88`。以 2026-01-01、02、03 为例，文案为：

  ```text
  [fatal] 价格文件含非有限值（NaN/inf）3 点（首个 ts=1767225600）：主价格文件先清洗再抽查
  ```

  退出 1；早于第 157 行调用返回及任何输出文件打开，独立新收据路径不会产生文件。

- `main_price=NaN`、声明 PASS：在基线 `stage2_closeout.py:268` 后新增块、工单第 68 行拒绝；预计代码第 278 行：

  ```text
  WORKORDER BLOCK: bindings.price_source_checks.points[0].main_price: 有限正数 != nan
  ```

- 第二价改为 `2.0`、声明 PASS：在工单第 76 行追加错误；预计代码第 286 行：

  ```text
  WORKORDER BLOCK: bindings.price_source_checks.points[1].status: 与 main/second_price 重算一致（FAIL） != PASS
  ```

**g）台账及文档结论。**

Q1 必须按 R1-01 修正实现；Q2 的依赖隔离理由成立，但阈值漂移保证不成立；Q4 必须限定检索证据和兼容范围。

`report-template.md:278` 的 `>5% WARN`、`>15% FAIL` 与新计算一致，也未承诺接受非有限主价，可以零改动。该行“exit 3 回退人工核对”不代表 closeout 可放行 ALL_SKIP；基线消费者已经拒绝 ALL_SKIP，这不是本段新增的冲突。
