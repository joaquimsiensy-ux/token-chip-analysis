# 施工任务 F05（codex --write，按下方工单 v3 逐条执行）

## 派工基线
- 派工基线：main 分支、HEAD 为包含本提示词文件的最新提交（本提示词入库后 HEAD 才定，故**不以具体 SHA 判定**）；基线判定只看工单 §0.1 两项检查：`git status --short` 为空，且 `git diff --stat 8b041842 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 仅含 F04 已入库的三文件（scripts/lib/net.py、scripts/lib/rpc_batch.py、scripts/tests/test_batch1_rpc_attestation.py），F05 白名单文件与 8b041842 逐字节相同。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先 `git rev-parse HEAD` 记入完成报告即可。
- **§0.1 第二项检查的口径修正（F04 已先落地）**：`git diff --stat 8b041842 HEAD -- scripts …` 的输出**只允许**恰好是上述 F04 三文件；F05 白名单三文件（`scripts/prices/price_check.py`、`scripts/report/stage2_closeout.py`、`scripts/tests/test_stage2_closeout.py`）相对 8b041842 必须无差异（`git diff --stat 8b041842 HEAD -- <这三个文件>` 为空）。工单正文 §0.1 写的“须为空”按本条理解，不因 F04 三文件在场而停工。
- 本任务是**施工**，不是复核：按工单 §2 逐条落地、按 §0.7 先取 RED、按 §0.8 跑定向测试、按 §3 写完成报告 `F05_done.md` 到工单所在目录。
- 纪律以工单 §0 为准（禁读 `~/.codex/`、白名单、不 commit/push、禁 stash/checkout/reset、锚不符即停工）。工单已由 codex 只读复核通过（`review_F05_reply_r3.md`），施工中若发现工单与代码不符，**停工写 `F05_done_attempt1_stopped.md`**，不得自行改方案。
- stdout 首行固定 `# 施工 F05：完成` 或 `# 施工 F05：停工`；末尾披露是否读过禁读路径。

---

# 工单 F05（v3，融合 codex 复核 r1 五条 F05-R1-01～05、r2 三条 F05-R2-01～03）：−2 收口真读价格双源收据——重算 verdict、拒 FAIL/ALL_SKIP、收据哈希绑定主源、拒纯申报 —— repair-20260918c-p1-f02-f04-f05 第二段

> 出处：codex 对 8.0.0（8b041842）六视角 review F05（P2，82bb26c/7.0.4 引入时即如此）：`stage2_closeout.py:350-354` 对 `bindings.price_source_checks` 只要求 {path,sha256} 在场（另一分支只查 `price_source.dual_source_check` 是 dict）；`:361-366` 只核引用结构、`:368-381` 只核文件在场与哈希；从不读收据的 `verdict`/`points`。反例：真实 `price_check.py` 在主 50/副 100 时写三点 FAIL 收据并退出 2，人为继续把它绑进工单，`stage2_closeout check` 仍 PASS。夹具 `test_stage2_closeout.py:102` 用手写 `{"status":"PASS"}`，不是生产者 schema，遮蔽了断层。用户 09-18 裁决：修。总原则：skill 上下文不增；能删不增、能改不增；references/SKILL/commands 本段零改动。
> 修法：①`price_check.py` 收据新增 `price_file_sha256`（收据对象唯一构造处 `:181-185`，唯一落盘点 `:187-188`；本段唯一新增字段）；②closeout 新增 `price_receipt_errors`：从 `bindings.price_source_checks` 或内联 `price_source.dual_source_check.receipt` 取收据引用（两者皆无＝纯申报，拒），读收据、按 `price_check.py:178-180` 同规则从 points 重算 verdict 并要求一致、只放行 PASS/WARN（WARN 记 NOTE）、`price_file_sha256` 必须等于 `bindings.price_source.sha256`；③夹具改由真实 `price_check.main()`（第二源离线 stub）生成收据。
> 存量迁移（台账 Q8，v2 按 R1-01 订正）：旧收据（无 `price_file_sha256`）、自定义格式收据、纯申报内联 dict、已绑定的 FAIL/ALL_SKIP 收据一律被拒。迁移步骤＝用当前 `price_check.py` 重跑收据 → 直接更新工单 `bindings.price_source_checks`（或内联 `dual_source_check.receipt`）的 path/sha256 → 完整 `stage2_closeout check` 至 PASS → `--receipt-only` 核验。**不得用 `amend`**（`bindings` 属冻结字段，`amend:727-728` 对 frozen_sha256 漂移直接拒；无旧 PASS 收据时 `:719-720` 亦拒）。用户 09-18 裁决：APU 0914 案暂不重跑，进 −3 时再补。
> v2 变更（`review_F05_reply_r1.md`）：R1-01 迁移步骤改为重跑完整 check、禁用 amend；R1-02 台账 Q8/Q9 表述订正（ARC 内联引用结构可保留但所指旧收据仍须迁移；纯申报 dict 与 FAIL/ALL_SKIP 收据为新增拒收面；Q9 加分支条件），并新登记 Q14（`report-template.md:278` "exit 3 回退人工对 Dexscreener 图"的人工回退路径在本契约下不再能进 −2 收口——待用户裁决）；R1-03 `test_stage2_reseal.py:604-611` overlay 白名单不含本段文件，未提交状态下 `dry_run_touches_nothing` 必红——reseal 补验改由调度方 commit 后在主仓库干净、验收 worktree 同 HEAD 时本机执行，施工方不跑；R1-04 §2.5 段 3 基线预期改为 RED（NOTE 断言基线不可能成立）；R1-05 行号订正（`flow_selection_errors` 返回在 `:235`，`:236-237` 空行；通用引用检查分 `:361-366` 结构与 `:368-381` 文件/哈希两段；`load()` 亦走路径围栏，越界/符号链接收据会得到 helper 与通用遍历两条诊断，可接受，不为消除重复改既有遍历）。
> v3 变更（`review_F05_reply_r2.md`）：R2-01 Q14 受影响范围改为按实际条件描述——`price_check.py:140` 只选一个第二源不自动换源，所选第二源全部抽样日期无有效对照即 ALL_SKIP，四条正式候选链均可能且不限币龄（Robinhood 本就不进正式发布，分开说明）；R2-02 §2.5 RED 准备步骤补齐“先完成 §2.3 全部测试侧变更含 `:100` 三日价格夹具”（否则真实生产者在 `:149-150` 以“价格序列过短”退出 1 无收据，段 1/3/6 会因输入过短而红，不构成 RED 证据），并要求先确认生产者达到各段预期退出码再记消费端断言；R2-03 “双诊断可接受”限定为**收据引用路径**失败，`:522`/`:541-544` 改的是 `bindings.price_source.path` 主源路径、helper 不读主源文件、诊断数仍为 1（§1.4/§2.2 订正）。
> 内容基线：`8b041842`（v8.0.0）加本工程已入库 commit；本段在 F04 落地之后施工，F04 不触碰本段任何文件，行号按 8b041842 核。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `F05_done.md`：`git status --short`（须为空）；`git diff --stat 8b041842 HEAD -- scripts/prices scripts/report/stage2_closeout.py scripts/tests/test_stage2_closeout.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空；`scripts/lib/net.py`、`scripts/lib/rpc_batch.py`、`scripts/tests/test_batch1_rpc_attestation.py` 为 F04 已落地改动，属预期，不在本条范围）。不空即停工写 `F05_done_attempt<N>_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。**豁免（attempt2 停工后补，F04/F05/F02 同款）**：§0.8 指定的测试自身按既有代码以子进程或文件读取方式访问历史 maintenance 目录（如 `test_repair_batch_a.py`/`test_repair_batch_c.py`/`test_exemption_guards.py`/`test_stage2_reseal.py`）属测试依赖，**允许原样运行**、不算违反本条；施工方本人不得主动打开、阅读、复制或修改那些历史文件，完成报告如实披露“仅由测试子进程访问”即可。
- 0.3 **白名单**：生产 `scripts/prices/price_check.py`、`scripts/report/stage2_closeout.py`；测试 `scripts/tests/test_stage2_closeout.py`；本目录新建 `F05_done.md`、`F05_red_evidence.txt`，停工时 `F05_done_attempt<N>_stopped.md`（N＝派工提示词给的尝试序号）。
- 0.4 **不改**：`price_check.py` 的 `_load_series`/`_daily_close`/阈值/退出码/第二源函数（F01/F07 用户裁决不修，本段不顺手改）；`stage2_closeout.py` 的 `fig2_selection_errors`/`flow_selection_errors`/`receipt_document`/`receipt_only_errors`/`fill_workorder`/`amend`/reseal 全部；`:361-366` 与 `:368-381` 通用引用遍历（收据引用仍由它核在场、哈希、越界、符号链接）；`audit_release_gate.py`、`build_html.py`；`scripts/tests/test_stage2_reseal.py`（其 overlay 白名单不在本段权限内）；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`contract_manifest.json`、`invariant_manifest.json`（复核 r1 已投影扫描 0 discrepancies；开工用 `python3 -B scripts/tests/invariant_scan.py` 再证实）。
- 0.5 行号均指施工前基线（8b041842）；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.5 新用例在改生产代码前**逐段独立执行**取 RED 写 `F05_red_evidence.txt`（每段各自 try/except，段 1 失败不得截断后续段取证）。
- 0.8 不跑 `run_all.py`、**不跑 `test_stage2_reseal.py`**（R1-03：其 overlay 白名单不含本段文件，未提交状态必红；由调度方 commit 后本机补验）。定向跑（全部须 PASS）：`python3 -B scripts/tests/test_stage2_closeout.py`、`test_a4_gate.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`python3 -B scripts/tests/invariant_scan.py`。冷字体缓存环境项：`test_a4_gate.py`/`test_stage2_closeout.py` 遇 `data_broken: '_items'` 时保留首次输出写 done，再 `MPLCONFIGDIR="$HOME/.matplotlib" python3 -B …` 重跑，重跑必须真实 PASS。

## 1. 硬约束

- 1.1 文档三处字节不变：`SKILL.md` 8021、`references/**/*.md` 合计 930076、`commands-staging/*.md` 合计 8798（命令同 F04 工单 §1.1）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 closeout 收据仍 12 项 checks（`test_stage2_closeout.py:135` 断言）；本段不新增 check 项，价格收据校验并入既有 `workorder` 项的 errors/notes。
- 1.4 `workorder_reference_contracts`（`:499-544`）全部 19 条既有 mutation 保持 BLOCK 且错误文案含其 field 名（复核 r1 已逐条演练成立）：尤其 `:507` `price_source_checks` pop → 本段新错误文案字段名含 `price_source_checks`；`:522` 绝对路径拒、`:541-544` 符号链接拒改的是 `bindings.price_source.path`（主价格文件路径），由通用遍历继续承担，helper 不读主源文件，路径诊断仍为 1 条（主源路径变化另可能触发图 2 同路径约束，既有行为）。“双诊断可接受”只适用于**收据引用路径**（`price_source_checks.path` 或内联 `receipt.path`）越界/符号链接：helper 内 `load()` 与通用遍历各出 1 条。
- 1.5 `price_check.py` 的 stdout 行、退出码（PASS/WARN 0、FAIL 2、ALL_SKIP 3）不变；收据只多一个键 `price_file_sha256`（其余键与 `:181-185` 逐字相同）。
- 1.6 `workorder_errors` 的返回类型 `(errors, notes)` 不变；`need()`（`:272`）与 `workorder_error()`（`:164`）的错误前缀 `WORKORDER BLOCK: ` 不变。

## 2. 逐条施工

### 2.1 `scripts/prices/price_check.py` —— 收据带主源文件哈希

- `:30`（锚 `import datetime`，唯一）之后插入一行 `import hashlib`。
- `:46`（锚 `def _load_series(path):`，唯一；`:44-45` 为两空行）之前新增：

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

在 `:238`（锚 `def amendment_errors(row, field):`，唯一）之前（即 `flow_selection_errors` 结尾 `:235` `    return errors, notes` 与 `:236-237` 两空行之后）新增：

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

说明：①`errors`/`notes` 在 `workorder_errors:270` 初始化、`required_refs` 在 `:299` 初始化，替换处在其作用域内且先于引用校验（`:401-404` 同款 extend 用法）；②`price_ref` 进 `required_refs` 后由 `:361-366` 核结构、`:368-381` 核在场/哈希/符号链接/越界；helper 内 `load()` 同走 `safe_case_file` 围栏，**收据引用路径**越界/符号链接会出现 helper＋通用遍历两条诊断，可接受（主源路径 `bindings.price_source.path` 的负例不受影响，仍 1 条）；③内联 `dual_source_check` 若为字符串或无 `receipt` 子引用，ref 为 None → 拒（基线：有顶层 `price_source_checks` 时不检查内联；无顶层时字符串拒、`{"status":"PASS"}` 类纯申报 dict 放行——本段关掉后者）。

### 2.3 `scripts/tests/test_stage2_closeout.py` —— 夹具改用真实生产者

- `:15`（锚 `sys.path[:0] = [str(HERE), str(REPO / "scripts/report"), str(REPO / "scripts/lib")]`，唯一）改为 `sys.path[:0] = [str(HERE), str(REPO / "scripts/report"), str(REPO / "scripts/lib"), str(REPO / "scripts/prices")]`。
- `:93`（锚 `def build_closeout_case(root) -> Path:`，唯一）之前新增：

```python
def write_price_receipt(case, second_price, out="price_checks.json", prices="price_series.json"):
    """F05：收据由真实 price_check.py 生成（第二源离线 stub），不手写 PASS。返回退出码（PASS/WARN 0、FAIL 2、ALL_SKIP 3、fatal 1）。"""
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

- `:100`（锚 `    write(case / "price_series.json", [[1767225600, 1.0]])`，唯一）改为 `    write(case / "price_series.json", [[1767225600, 1.0], [1767312000, 1.0], [1767398400, 1.0]])`（price_check 要求 ≥2 天；复核 r1 已确认无断言依赖单点；`test_stage2_reseal.py:21/436/646` 复用 `build_closeout_case` 自动获得新夹具）。
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

说明：偏差口径 `|a-b|/((a+b)/2)`：1.0/2.0 → 66.67% FAIL；1.0/1.08 → 7.69% WARN；`second_price=None` → 三点 SKIP → ALL_SKIP 退出 3（`price_check.py:165/178-180/193-194`；复核 r1 已用真实生产者函数演练确认）。`update()`（`:144`）、`sha()`（`:32`）、`check_result()`（`:131`）为既有 helper。

RED 证据（逐段独立执行，写 `F05_red_evidence.txt`）：**先完成 §2.3 的全部测试侧变更**——`:15` sys.path、`write_price_receipt` helper、**`:100` 三日价格夹具**、`:102` 真实生产者收据、`:534` 内联 receipt——保持生产代码（`price_check.py`/`stage2_closeout.py`）未改（此时收据无 `price_file_sha256`）。若漏改 `:100`，真实生产者在 `price_check.py:149-150` 以“价格序列过短（1 天）”退出 1、不生成收据，段 1/3/6 会因输入过短而红，**不构成本段 RED 证据**。取证顺序：每段先确认生产者达到该段预期退出码（段 1 FAIL 2、段 3 WARN 0、段 6 ALL_SKIP 3、其余 PASS 0）并记录，再逐段 try/except 记录消费端断言结果：段 1、2、**3（NOTE 断言基线不成立）**、4、5、6、7a 基线 **RED**；段 7b 基线 GREEN→GREEN。段 1 失败不得截断后续段取证，7a 不得遮断 7b。

## 3. 完成报告 `F05_done.md` 必含

①0.1 两条命令输出；②§2 各处 `git diff` 原文；③RED 摘要（逐段）；④0.8 各测试结果尾行（含"reseal 未实跑、交调度方本机补验"）；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点（含 §2.2 说明①作用域核实）；⑧禁读披露。stdout 首行 `# 施工 F05：完成` 或 `# 施工 F05：停工`。

## 4. 登记不修（`code_change_pending.md` Q7/Q8/Q9/Q14，调度方维护）

- 不重跑第二源（Q7）；存量迁移按导语步骤（Q8，禁用 amend；APU 暂不重跑为用户裁决）；内联字符串形态在无顶层引用时早已 BLOCK（Q9，分支条件已注明）。
- **Q14（复核 r1 登记、r2 订正范围，待用户裁决）**：`report-template.md:278` 允许“双源都无该币 exit 3 回退人工对 Dexscreener 图”，本契约下 ALL_SKIP 收据不能进 −2 收口。实际条件：`price_check.py:140` 每次只选一个第二源、不在 DefiLlama 失败后自动改试币安；所选第二源在全部抽样日期无有效对照（DefiLlama `:108-110`/币安 `:117-122` 无数据，或 `_get:87-100` 重试耗尽）即 `:165-180` 汇总 ALL_SKIP、`:193-194` 退出 3——**ETH/BSC/Base/Solana 四条正式候选链均可能，且不限币龄**；人工比图不能满足 PASS/WARN 收据契约。Robinhood 类探索链本就不进正式发布，与本轮新增影响分开。范围不扩大为“任何 SKIP 即拒”（部分 SKIP 仍可汇总 PASS/WARN）；缺 `--binance-symbol` 在 `:143-145` 退出 1 无收据，不属 ALL_SKIP。本段按严格口径实施；若用户要开人工旁证口子，另立小工单（需新增字段，违背本轮“不新增”原则，故不自行开）。
- 文档 `split-run.md:158`"价格源 path＋sha256 及双源检查结果"、`report-template.md:278` 不增字；契约由 CHANGELOG 条目（收官段）与 `price_receipt_errors` docstring 承载。
- reseal 补验：本段 commit 后由调度方在主仓库干净、`/tmp/w3_acceptance` 同步 HEAD 时执行 `test_stage2_reseal.py`（R1-03）。
