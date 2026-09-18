# 工单 F05（v1）：−2 收口真读价格双源收据——重算 verdict、拒 FAIL/ALL_SKIP、收据哈希绑定主源、拒纯申报 —— repair-20260918c-p1-f02-f04-f05 第二段

> 出处：codex 对 8.0.0（8b041842）六视角 review F05（P2，82bb26c/7.0.4 引入时即如此）：`stage2_closeout.py:350-354` 对 `bindings.price_source_checks` 只要求 {path,sha256} 在场（另一分支只查 `price_source.dual_source_check` 是 dict）；`:358-379` 通用遍历只核文件在场与哈希；从不读收据的 `verdict`/`points`。反例：真实 `price_check.py` 在主 50/副 100 时写三点 FAIL 收据并退出 2，人为继续把它绑进工单，`stage2_closeout check` 仍 PASS。夹具 `test_stage2_closeout.py:102` 用手写 `{"status":"PASS"}`，不是生产者 schema，遮蔽了断层。用户 09-18 裁决：修。总原则：skill 上下文不增；能删不增、能改不增；references/SKILL/commands 本段零改动。
> 修法：①`price_check.py` 收据新增 `price_file_sha256`（生产者一处写出，本段唯一新增字段）；②closeout 新增 `price_receipt_errors`：从 `bindings.price_source_checks` 或内联 `price_source.dual_source_check.receipt` 取收据引用（两者皆无＝纯申报，拒），读收据、按 `price_check.py:178-180` 同规则从 points 重算 verdict 并要求一致、只放行 PASS/WARN（WARN 记 NOTE）、`price_file_sha256` 必须等于 `bindings.price_source.sha256`；③夹具改由真实 `price_check.main()`（第二源离线 stub）生成收据。
> 存量代价（台账 Q8，明示）：旧收据无 `price_file_sha256` 被拒；APU 0914 案 `price_source_checks.json` 是自定义格式亦被拒——进 −3 前须重跑 price_check 并 amend 工单。
> 内容基线：`8b041842`（v8.0.0）加本工程已入库 commit；本段在 F04 落地之后施工，F04 不触碰本段任何文件，行号按 8b041842 核。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `F05_done.md`：`git status --short`（须为空）；`git diff --stat 8b041842 HEAD -- scripts/prices scripts/report/stage2_closeout.py scripts/tests/test_stage2_closeout.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空；`scripts/lib/net.py`、`scripts/lib/rpc_batch.py`、`scripts/tests/test_batch1_rpc_attestation.py` 三文件为 F04 已落地改动，属预期，不在本条范围）。不空即停工写 `F05_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
- 0.3 **白名单**：生产 `scripts/prices/price_check.py`、`scripts/report/stage2_closeout.py`；测试 `scripts/tests/test_stage2_closeout.py`；本目录新建 `F05_done.md`、`F05_red_evidence.txt`，停工时 `F05_done_attempt1_stopped.md`。
- 0.4 **不改**：`price_check.py` 的 `_load_series`/`_daily_close`/阈值/退出码/第二源函数（F01/F07 用户裁决不修，本段不顺手改）；`stage2_closeout.py` 的 `fig2_selection_errors`/`flow_selection_errors`/`receipt_document`/`receipt_only_errors`/`fill_workorder`/reseal 全部；`:358-379` 通用引用遍历（收据引用仍由它核在场与哈希）；`audit_release_gate.py`、`build_html.py`；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`contract_manifest.json`、`invariant_manifest.json`（price_check 写文件点未增、网络库未换：`--out` 仍是同一处 `json.dump`；开工用 `python3 -B scripts/tests/invariant_scan.py` 证实）。
- 0.5 行号均指施工前基线（8b041842）；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.5 新用例在改生产代码前逐段取 RED 写 `F05_red_evidence.txt`。
- 0.8 不跑 `run_all.py`。定向跑（全部须 PASS）：`python3 -B scripts/tests/test_stage2_closeout.py`、`test_a4_gate.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`python3 -B scripts/tests/invariant_scan.py`。`test_stage2_reseal.py` 依赖 `/tmp/w3_acceptance` 验收 worktree，沙箱内跑不了时在 done 注明"未实跑，交本机补验"。冷字体缓存环境项：`test_a4_gate.py`/`test_stage2_closeout.py` 遇 `data_broken: '_items'` 时保留首次输出写 done，再 `MPLCONFIGDIR="$HOME/.matplotlib" python3 -B …` 重跑，重跑必须真实 PASS。

## 1. 硬约束

- 1.1 文档三处字节不变：`SKILL.md` 8021、`references/**/*.md` 合计 930076、`commands-staging/*.md` 合计 8798（命令同 F04 工单 §1.1）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 closeout 收据仍 12 项 checks（`test_stage2_closeout.py:135` 断言）；本段不新增 check 项，价格收据校验并入既有 `workorder` 项的 errors/notes。
- 1.4 `workorder_reference_contracts`（`:499-544`）全部既有 mutation 保持 BLOCK 且错误文案含其 field 名：尤其 `:507` `price_source_checks` pop → 本段新错误文案字段名须含 `price_source_checks`；`:522` 绝对路径拒、`:541-544` 符号链接拒由 `:358-379` 通用遍历继续承担（收据引用仍进 `required_refs`）。
- 1.5 `price_check.py` 的 stdout 行、退出码（PASS/WARN 0、FAIL 2、ALL_SKIP 3）不变；收据只多一个键 `price_file_sha256`（其余键与 `:181-185` 逐字相同）。
- 1.6 `workorder_errors` 的返回类型 `(errors, notes)` 不变；`need()`（`:272`）与 `workorder_error()`（`:164`）的错误前缀 `WORKORDER BLOCK: ` 不变。

## 2. 逐条施工

### 2.1 `scripts/prices/price_check.py` —— 收据带主源文件哈希

- `:30`（锚 `import datetime`，唯一）之后插入一行 `import hashlib`。
- `:45`（`_load_series` 定义 `def _load_series(path):` 在 `:46`，其前一行 `:45` 为空行）之前新增：

```python
def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


```

- `:185`（锚 `           "points": results, "verdict": verdict}`，唯一）改为：

```python
           "price_file_sha256": _sha256_file(a.price_file),
           "points": results, "verdict": verdict}
```

- docstring：`:27`（锚 `（来源：A9 小工程件，2026-07-22；QUQ CG vs DefiLlama 实测通过）"""`，唯一）之前插入一行：`收据（--out）含 price_file_sha256——stage2_closeout 用它把收据绑定到工单 bindings.price_source，并重算 verdict（F05）。`

### 2.2 `scripts/report/stage2_closeout.py` —— 新增 `price_receipt_errors`

在 `:238`（锚 `def amendment_errors(row, field):`，唯一）之前（即 `flow_selection_errors` 结尾 `:236` `    return errors, notes` 与两空行之后）新增：

```python
PRICE_POINT_STATUSES = ("PASS", "WARN", "SKIP", "FAIL")


def price_receipt_errors(case, bindings):
    """F05：价格双源收据必须是 price_check.py 产物且结论可放行——从 points 按 price_check 同规则
    重算 verdict 并要求一致；只放行 PASS/WARN（WARN 记 NOTE）；price_file_sha256 须等于
    bindings.price_source.sha256；引用取 bindings.price_source_checks，否则取内联
    price_source.dual_source_check.receipt；两者皆无＝纯申报对象，拒。返回 (errors, notes, ref)。"""
    errors, notes = [], []
    price_source = bindings.get("price_source") if isinstance(bindings.get("price_source"), dict) else {}
    ref = bindings.get("price_source_checks")
    if ref is None:
        inline = price_source.get("dual_source_check")
        ref = inline.get("receipt") if isinstance(inline, dict) else None
    if not (isinstance(ref, dict) and isinstance(ref.get("path"), str)
            and isinstance(ref.get("sha256"), str) and ref["sha256"]):
        errors.append(workorder_error("bindings.price_source_checks|price_source.dual_source_check.receipt",
                                      "price_check.py 收据引用 {path,sha256}（纯申报对象不放行）", ref))
        return errors, notes, None
    try:
        receipt = load(case, ref["path"])
    except (OSError, ValueError) as exc:
        errors.append(workorder_error("bindings.price_source_checks.path", "可读取的收据 JSON", str(exc)))
        return errors, notes, ref
    points = receipt.get("points") if isinstance(receipt, dict) else None
    if not isinstance(points, list) or not points:
        errors.append(workorder_error("bindings.price_source_checks.points", "非空 list", points))
        return errors, notes, ref
    statuses = [(p.get("status") if isinstance(p, dict) else None) for p in points]
    expected = ("FAIL" if any(s not in PRICE_POINT_STATUSES or s == "FAIL" for s in statuses)
                else "ALL_SKIP" if all(s == "SKIP" for s in statuses)
                else "WARN" if "WARN" in statuses else "PASS")
    if receipt.get("verdict") != expected:
        errors.append(workorder_error("bindings.price_source_checks.verdict",
                                      f"与 points 重算一致（{expected}）", receipt.get("verdict")))
    if expected not in ("PASS", "WARN"):
        errors.append(workorder_error("bindings.price_source_checks.verdict",
                                      "PASS|WARN（FAIL/ALL_SKIP 禁入装配：换源或人工裁决后重跑 price_check）", expected))
    for key in ("main_source", "second_source"):
        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
            errors.append(workorder_error(f"bindings.price_source_checks.{key}", "非空字符串", receipt.get(key)))
    bound = receipt.get("price_file_sha256")
    if not isinstance(bound, str) or not bound:
        errors.append(workorder_error("bindings.price_source_checks.price_file_sha256",
                                      "在场（旧收据无此字段：用当前 price_check.py 重跑）", bound))
    elif bound != price_source.get("sha256"):
        errors.append(workorder_error("bindings.price_source_checks.price_file_sha256",
                                      f"= bindings.price_source.sha256 {price_source.get('sha256')}", bound))
    if not errors and expected == "WARN":
        notes.append(f"NOTE: 价格双源 WARN 点 {statuses.count('WARN')} 个（>5% 过目口径，见 report-template 2b）")
    return errors, notes, ref


```

`:350-354`（起锚 `    if "price_source_checks" in bindings:`，唯一；止锚 `        need("bindings.price_source_checks|price_source.dual_source_check", "双源检查对象在场", dual, isinstance(dual, dict))`，唯一）替换为：

```python
    price_errors, price_notes, price_ref = price_receipt_errors(case, bindings)
    errors.extend(price_errors)
    notes.extend(price_notes)
    if price_ref is not None:
        required_refs.append(("bindings.price_source_checks", price_ref))
```

说明：①`errors`/`notes` 是 `workorder_errors` 的局部列表（`:401-404` 同款 extend 用法），开工核实 `:265-275` 定义；②`price_ref` 进 `required_refs` 后由 `:358-379` 通用遍历核在场/哈希/符号链接/越界，本函数不重复；③内联 `dual_source_check` 若为字符串或无 `receipt` 子引用，ref 为 None → 拒（现行 HEAD 对字符串已拒，对 `{"status":"PASS"}` 类纯申报 dict 放行——本段关掉后者）。

### 2.3 `scripts/tests/test_stage2_closeout.py` —— 夹具改用真实生产者

- `:15`（锚 `sys.path[:0] = [str(HERE), str(REPO / "scripts/report"), str(REPO / "scripts/lib")]`，唯一）改为 `sys.path[:0] = [str(HERE), str(REPO / "scripts/report"), str(REPO / "scripts/lib"), str(REPO / "scripts/prices")]`。
- `:93`（锚 `def build_closeout_case(root) -> Path:`，唯一）之前新增：

```python
def write_price_receipt(case, second_price, out="price_checks.json", prices="price_series.json"):
    """F05：收据由真实 price_check.py 生成（第二源离线 stub），不手写 PASS。返回退出码。"""
    import price_check
    from unittest import mock
    argv = ["price_check.py", "--price-file", str(case / prices), "--source", "coingecko",
            "--chain", "bsc", "--addr", "0x" + "1" * 40, "--out", str(case / out)]
    with mock.patch.object(sys, "argv", argv), mock.patch.object(
            price_check, "second_llama", return_value=(second_price, "offline")):
        try:
            price_check.main()
            return 0
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 1


```

- `:100`（锚 `    write(case / "price_series.json", [[1767225600, 1.0]])`，唯一）改为 `    write(case / "price_series.json", [[1767225600, 1.0], [1767312000, 1.0], [1767398400, 1.0]])`（price_check 要求 ≥2 天；开工核实 `grep -n price_series scripts/tests/test_stage2_closeout.py` 无其他断言依赖点数，结果写 done）。
- `:102`（锚 `    write(case / "price_checks.json", {"status": "PASS"})`，唯一）改为 `    assert write_price_receipt(case, second_price=1.0) == 0`。
- `:534`（锚 `    obj["bindings"]["price_source"]["dual_source_check"] = {"status": "PASS"}`，唯一）改为：

```python
    obj["bindings"]["price_source"]["dual_source_check"] = {
        "receipt": {"path": "price_checks.json", "sha256": sha(case / "price_checks.json")}, "verdict": "PASS"}
```

### 2.4 说明：`:507` mutation 不改
`("price_source_checks", lambda obj: obj["bindings"].pop("price_source_checks"))` pop 后无内联 → 本段错误字段名 `bindings.price_source_checks|price_source.dual_source_check.receipt` 含 `price_source_checks`，`:528` 断言继续成立。

### 2.5 新用例 `price_receipt_content_enforced`

在 `:605`（锚 `def facts_vs_ledgers_rejects_hand_edit(cases):`，唯一）之前新增；并在 `:631`（锚 `         facts_vs_ledgers_rejects_hand_edit]`，唯一）改为 `         facts_vs_ledgers_rejects_hand_edit, price_receipt_content_enforced]`。

```python
def price_receipt_content_enforced(cases):
    """F05：真实 price_check 收据的结论/绑定被 closeout 语义消费；纯申报对象不放行。"""
    import stage2_closeout as closeout
    case = cases.fresh()

    def rebind():
        obj = read(case / "a5_assembly_workorder.json")
        obj["bindings"]["price_source_checks"]["sha256"] = sha(case / "price_checks.json")
        write(case / "a5_assembly_workorder.json", obj)
        return closeout.workorder_errors(case, "report.md")

    # 1 真实 FAIL 收据（主 1.0/副 2.0 → 66.67%）退出 2；绑定后 workorder 与完整 check 均 BLOCK
    assert write_price_receipt(case, second_price=2.0) == 2
    errors, _ = rebind()
    assert any("price_source_checks.verdict" in e for e in errors), errors
    row = check_result(case, 2)["workorder"]
    assert "price_source_checks.verdict" in detail(row), row
    # 2 手改 verdict=PASS 但 points 含 FAIL → 重算不一致
    update(case, "price_checks.json", lambda r: r.update(verdict="PASS"))
    errors, _ = rebind()
    assert any("重算一致" in e for e in errors), errors
    # 3 WARN 收据（主 1.0/副 1.08 → 7.69%）放行并记 NOTE
    assert write_price_receipt(case, second_price=1.08) == 0
    errors, notes = rebind()
    assert not errors, errors
    assert any("WARN 点 3" in n for n in notes), notes
    # 4 price_file_sha256 与工单主源不一致
    update(case, "price_checks.json", lambda r: r.update(price_file_sha256="0" * 64))
    errors, _ = rebind()
    assert any("price_file_sha256" in e and "= bindings.price_source.sha256" in e for e in errors), errors
    # 5 旧收据（无 price_file_sha256）
    update(case, "price_checks.json", lambda r: r.pop("price_file_sha256"))
    errors, _ = rebind()
    assert any("price_file_sha256" in e and "在场" in e for e in errors), errors
    # 6 全 SKIP → ALL_SKIP 退出 3；绑定后 BLOCK
    assert write_price_receipt(case, second_price=None) == 3
    errors, _ = rebind()
    assert any("ALL_SKIP" in e for e in errors), errors
    # 7 内联纯申报对象拒；内联带 receipt（ARC 形态）放行
    assert write_price_receipt(case, second_price=1.0) == 0
    obj = read(case / "a5_assembly_workorder.json")
    obj["bindings"].pop("price_source_checks")
    obj["bindings"]["price_source"]["dual_source_check"] = {"status": "PASS"}
    write(case / "a5_assembly_workorder.json", obj)
    errors, _ = closeout.workorder_errors(case, "report.md")
    assert any("dual_source_check.receipt" in e for e in errors), errors
    obj["bindings"]["price_source"]["dual_source_check"] = {
        "receipt": {"path": "price_checks.json", "sha256": sha(case / "price_checks.json")}, "verdict": "PASS"}
    write(case / "a5_assembly_workorder.json", obj)
    errors, _ = closeout.workorder_errors(case, "report.md")
    assert not errors, errors
    check_result(case)
```

说明：偏差口径 `|a-b|/((a+b)/2)`：1.0/2.0 → 66.67% FAIL；1.0/1.08 → 7.69% WARN；`second_price=None` → 三点 SKIP → ALL_SKIP 退出 3（`price_check.py:165/178-180/193-194`）。`update()`（`:144`）与 `sha()`（`:32`）、`check_result()`（`:131`）为既有 helper。

RED 证据：改生产代码前（此时 `write_price_receipt` 已可用但收据无 `price_file_sha256`）逐段执行：段 1（FAIL 收据放行，errors 为空）、2、4、5、6、7a 基线 **RED**；段 3、7b 基线 GREEN→GREEN。逐段 try/except 各自记录，写 `F05_red_evidence.txt`。

## 3. 完成报告 `F05_done.md` 必含

①0.1 两条命令输出；②§2 各处 `git diff` 原文；③RED 摘要；④0.8 各测试结果尾行（含未实跑项说明）；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点（含 §2.2 说明①、§2.3 开工核实结果）；⑧禁读披露。stdout 首行 `# 施工 F05：完成` 或 `# 施工 F05：停工`。

## 4. 登记不修（`code_change_pending.md` Q7/Q8/Q9，调度方维护）

- 不重跑第二源（Q7）；存量 APU 0914 案与旧收据须重跑 price_check（Q8）；内联字符串形态存量早已 BLOCK（Q9）。
- 文档 `split-run.md:158`"价格源 path＋sha256 及双源检查结果"、`report-template.md:278` 不增字；契约由 CHANGELOG 条目（收官段）与 `price_receipt_errors` docstring 承载。
