# 工单 F01（v2，融合 codex 复核 r1 五条 F01-R1-01～05）：主价格文件非有限/非正值 fail-closed、第二源非有限按无数据、收据序列化拒 NaN、−2 收口逐点重算价格状态 —— repair-20260918d-p1-f01-f04 第二段

> 出处：codex 对 9.0.0（868d3f61）六视角 review F01（P1，A2/B2；半修复 8e566ef2→47e9efb0）：`scripts/prices/price_check.py:75/:79/:81` 把价格 `float()` 后不核有限性；`:175` 只判 `None/≤0`（NaN 与 0 比较为假，不落 SKIP），`:179` 偏差算成 NaN，`:180` 两个 `>` 比较均为假 → **PASS**；`:199` `json.dump` 默认 `allow_nan=True` 写出含 `NaN` 字面量的收据。`scripts/report/stage2_closeout.py:268-271` 只从各点自报 `status` 汇总 verdict，不看 `main_price/second_price` 数值。反例：三天 `close=NaN` CSV → 真实生产者 `rc=0, verdict=PASS`、三点 `main_price/deviation_pct=NaN`、收口 `errors=[]`。用户 09-18 裁决：修。总原则：skill 上下文不增；能删不增、能改不增；references/SKILL/commands 本段零改动。
> 修法：①生产者 `_load_series` 解析后任一点**非有限或非正** → `[fatal]` 退出 1（主价格文件是报告图 1 正式输入，含 NaN/0/负价本身就是坏文件，抽查前先清洗；存量按真实解析规则核验 0 命中，台账 Q4）；②`:175` 之前把非有限的第二源价规范化为 `None`（既有 SKIP 分支接手，收据可序列化，台账 Q1）；③`:199` `allow_nan=False`（收据层纵深防御）；④closeout `price_receipt_errors` 逐点用 `main_price/second_price` 按 `price_check.py:175-180` 同规则重算 status 并要求与声明一致，主价非有限正数直接拒（与①同口径；严于基线生产者"p1≤0→SKIP"，存量无任何 price_check 收据故零实际影响，Q4）；阈值常量复制自 `price_check.py:43`、不 import（Q2），两端相等由测试 6g 断言守。
> v2 变更（`review_F01_reply_r1.md`）：R1-01 第二源非有限值原会以 `p2=nan` 进 results 撞 `allow_nan=False` 抛 `ValueError`——改为 `:175` 前规范化为 `None`，并加带 `--out` 的用例 6c；R1-02 消费者拒有限非正主价严于基线生产者——生产者 `_load_series` 同步拒非正（两端同口径），兼容范围与存量代价按 Q4 实证明写；R1-03 阈值漂移改由 6g 相等断言＋WARN 边界用例守；R1-04 汇总层诊断改"0～2 条"；R1-05 Q4 存量核验改用 `price_check._load_series` 真实解析规则由调度方本机执行；另 §0.4 CSV 日期截断口径位置订正为 `_load_series:70-72`。
> 内容基线：`868d3f61`（v9.0.0）加本工程已入库 commit；本段在 F04 落地之后施工，F04 不触碰本段任何文件，行号按 868d3f61 核。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `F01_done.md`：`git status --short`（须为空）；`git diff --stat 868d3f61 HEAD -- scripts/prices scripts/report scripts/tests/test_stage2_closeout.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空；`scripts/lib/camp_spec.py`、`scripts/tests/test_repair_batch_c.py` 为 F04 已落地改动，属预期，不在本条范围）。不空即停工写 `F01_done_attempt<N>_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。**豁免**：§0.8 指定的测试自身按既有代码以子进程或文件读取方式访问历史 maintenance 目录（如 `test_exemption_guards.py`）属测试依赖，**允许原样运行**、不算违反本条；施工方本人不得主动打开、阅读、复制或修改那些历史文件，完成报告如实披露"仅由测试子进程访问"即可。
- 0.3 **白名单**：生产 `scripts/prices/price_check.py`、`scripts/report/stage2_closeout.py`；测试 `scripts/tests/test_stage2_closeout.py`；本目录新建 `F01_done.md`、`F01_red_evidence.txt`，停工时 `F01_done_attempt<N>_stopped.md`。
- 0.4 **不改**：`price_check.py` 的 `_daily_close` 与 `_load_series:70-72` 的 CSV 日期截断取值口径（上轮用户裁决不修）、`:175` 原判点行本身、`second_llama`/`second_binance`/`_get`、`--second` 选源与同源提示（review F05 本轮不修）、阈值数值、既有退出码；`stage2_closeout.py` 的 `PRICE_POINT_STATUSES`、汇总 verdict 规则（`:269-277`）、`price_file_sha256` 绑定（`:281-287`）、`workorder_errors` 其余全部、`load()`（`:62-63`，`json.loads` 默认解析 NaN 字面量为 float，正好让 closeout 读到坏收据后拒）；`scripts/tests/test_stage2_reseal.py`；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`contract_manifest.json`、`invariant_manifest.json`（开工用 `python3 -B scripts/tests/invariant_scan.py` 证实无需登记）。
- 0.5 行号均指施工前基线（868d3f61）；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.3 六段新用例（6b–6g）在改生产代码前**逐段独立执行**取证写 `F01_red_evidence.txt`（每段各自 try/except，前段失败不得截断后段取证）。
- 0.8 不跑 `run_all.py`、**不跑 `test_stage2_reseal.py`**（硬依赖预建验收 worktree；由调度方 commit 后本机补验）。定向跑（全部须 PASS）：`python3 -B scripts/tests/test_stage2_closeout.py`、`test_a4_gate.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`python3 -B scripts/tests/invariant_scan.py`。冷字体缓存环境项：`test_a4_gate.py`/`test_stage2_closeout.py` 遇 `data_broken: '_items'` 时保留首次输出写 done，再 `MPLCONFIGDIR="$HOME/.matplotlib" python3 -B …` 重跑，重跑必须真实 PASS。

## 1. 硬约束

- 1.1 文档三处字节不变：`SKILL.md` 8021、`references/**/*.md` 合计 930076、`commands-staging/*.md` 合计 8798（命令同 F04 工单 §1.1）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 closeout 收据仍 12 项 checks（`test_stage2_closeout.py:618` 断言）；本段不新增 check 项，逐点重算错误并入既有 `workorder` 项的 errors。
- 1.4 `workorder_reference_contracts`（`:514-561`）全部 19 条既有 mutation 保持 BLOCK 且错误文案含其 field 名；`price_receipt_content_enforced` 段 1-7 断言不变（段 3 WARN 收据仍放行并记 NOTE：1.0/1.08 重算 7.69% WARN 与声明一致）。
- 1.7 兼容范围（明写）：消费者要求每点 `main_price` 为有限正数、`status` 与重算一致；基线生产者对 `p1≤0` 判 SKIP 并可汇总 PASS 的收据在新消费者下被拒——存量案卷经 Q4 核验**不存在任何 `price_check.py` 生成的收据**（0 份含 `points`），故无实际迁移对象；今后收据一律由改后生产者生成，两端同口径。
- 1.5 `price_check.py` 对**合法**输入（全有限）的 stdout 行、退出码（PASS/WARN 0、FAIL 2、ALL_SKIP 3）、收据键集合逐字不变；本段**不新增收据键**。
- 1.6 `price_receipt_errors` 返回类型 `(errors, notes, ref)` 不变；`workorder_error()` 前缀 `WORKORDER BLOCK: ` 不变。

## 2. 逐条施工

### 2.1 `scripts/prices/price_check.py` —— 非有限值 fail-closed

- `:34`（锚 `import os`，唯一）之前插入一行 `import math`。
- `:18`（锚 `  时间戳 >1e12 自动判毫秒。`，唯一）改为 `  时间戳 >1e12 自动判毫秒；任一点非有限（NaN/inf）或非正即 [fatal] 退出 1，先清洗主价格文件再抽查（F01）。`
- `:84`（锚 `    out = [(t // 1000 if t > 10 ** 12 else t, p) for t, p in out]`，唯一）之后插入：

```python
    bad = [t for t, p in out if not (math.isfinite(p) and p > 0)]
    if bad:
        sys.exit(f"[fatal] 价格文件含非有限或非正价格 {len(bad)} 点（首个 ts={bad[0]}）：主价格文件先清洗再抽查")
```

- `:175`（锚 `        if p2 is None or p2 <= 0 or p1 <= 0:`，唯一）**之前**插入一行（`:175` 原行不改）：
  `        p2 = p2 if p2 is None or math.isfinite(p2) else None  # 第二源非有限→按无数据 SKIP（收据可序列化）`
- `:199`（锚 `            json.dump(out, f, ensure_ascii=False, indent=1)`，唯一）改为 `            json.dump(out, f, ensure_ascii=False, indent=1, allow_nan=False)`

说明：①CSV 路径 `float("NaN")`/`float("inf")`/`float("-inf")`、JSON 路径 `NaN`/`Infinity`/`-Infinity` 字面量（`json.load` 默认接受）与溢出数值（如 `1e309`→inf）都落到 `:84` 之后的检查；`sys.exit(str)` 退出码 1，与 `:61/:66/:83` 同款；②`p1` 经①保证有限正数；第二源非有限经②置 `None` 后走既有 `p2 is None` SKIP 分支，results 里 `second_price=null`、`second_note` 仍为源函数返回值（不改 `src2`）；③`allow_nan=False` 在①②之后不再有已知触发路径，属纵深防御（若触发则 `ValueError` 退出 1，可接受）；④`:185` 打印行对 `p2=None` 已有分支，不改。

### 2.2 `scripts/report/stage2_closeout.py` —— 逐点重算

- `:15`（锚 `import os`，唯一）之前插入一行 `import math`。
- `:240`（锚 `PRICE_POINT_STATUSES = ("PASS", "WARN", "SKIP", "FAIL")`，唯一）之后插入一行：
  `PRICE_WARN_PCT, PRICE_FAIL_PCT = 5.0, 15.0  # 与 scripts/prices/price_check.py:43 同值；report 层离线不 import 该 requests 类脚本`
- `:244-245`（起锚 `    """F05：价格双源收据必须是 price_check.py 产物且结论可放行——从 points 按 price_check 同规则`，唯一；止锚 `    重算 verdict 并要求一致；只放行 PASS/WARN（WARN 记 NOTE）；price_file_sha256 须等于`，唯一）替换为：

```python
    """F05/F01：价格双源收据必须是 price_check.py 产物且结论可放行——逐点用 main/second_price 按 price_check
    同规则重算 status（主价非有限正数即拒）再汇总 verdict，均须与声明一致；只放行 PASS/WARN（WARN 记 NOTE）；price_file_sha256 须等于
```

- `:268`（锚 `    statuses = [(p.get("status") if isinstance(p, dict) else None) for p in points]`，唯一）之后插入：

```python
    for i, p in enumerate(points):
        if not isinstance(p, dict):
            continue
        p1, p2 = p.get("main_price"), p.get("second_price")
        ok1 = isinstance(p1, (int, float)) and not isinstance(p1, bool) and math.isfinite(p1) and p1 > 0
        ok2 = isinstance(p2, (int, float)) and not isinstance(p2, bool) and math.isfinite(p2) and p2 > 0
        if not ok1:
            errors.append(workorder_error(f"bindings.price_source_checks.points[{i}].main_price", "有限正数", p1))
            continue
        if not ok2:
            status = "SKIP"
        else:
            dev = round(abs(p1 - p2) / ((p1 + p2) / 2) * 100, 2)
            status = "FAIL" if dev > PRICE_FAIL_PCT else ("WARN" if dev > PRICE_WARN_PCT else "PASS")
        if p.get("status") != status:
            errors.append(workorder_error(f"bindings.price_source_checks.points[{i}].status",
                                          f"与 main/second_price 重算一致（{status}）", p.get("status")))
```

说明：①`round(…, 2)` 与 `price_check.py:179` 逐字同规则，边界 5.00/15.00 两侧判定一致；②非 dict 元素由既有 `statuses` None→FAIL 汇总拒，本块跳过；③主价非有限/非正时 `continue`，该点自报 status 仍进汇总——汇总层（`:272-277` 两项独立检查）还可能产生 0～2 条诊断，各自说明不同事实，不矛盾；④`p2 is None` 与非有限/≤0 同落 SKIP，与改后生产者（`:175` 前规范化＋原 SKIP 分支）一致；⑤block 内只用既有 `errors`/`workorder_error`，返回值不变。

### 2.3 `scripts/tests/test_stage2_closeout.py` —— 六段新用例（改既有函数，不新增函数）

`:659`（锚 `    # 7 内联纯申报对象拒；内联带 receipt（ARC 形态）放行`，唯一）之前插入：

```python
    # 6b F01：主价格文件含 NaN 或 0 → 生产者 [fatal] 退出 1、不写收据
    for name, first in (("price_nan.json", float("nan")), ("price_zero.json", 0.0)):
        write(case / name, [[1767225600, first], [1767312000, 1.0], [1767398400, 1.0]])
        assert write_price_receipt(case, second_price=1.0, prices=name, out="price_bad_checks.json") == 1, name
        assert not (case / "price_bad_checks.json").exists(), name
    # 6c F01：第二源返回 NaN → 按无数据 SKIP，ALL_SKIP 退出 3，收据可序列化且 second_price 为 null
    assert write_price_receipt(case, second_price=float("nan")) == 3
    assert all(q["second_price"] is None and q["status"] == "SKIP" for q in read(case / "price_checks.json")["points"])
    # 6d F01：收据主价被改成 NaN（status 仍 PASS）→ 消费者拒"有限正数"
    assert write_price_receipt(case, second_price=1.0) == 0
    update(case, "price_checks.json", lambda r: r["points"][0].update(main_price=float("nan")))
    errors, _ = rebind()
    assert any("points[0].main_price" in e for e in errors), errors
    # 6e F01：收据主价被改成 0.0（status 仍 PASS）→ 同样拒（消费者与改后生产者同口径：有限正数）
    update(case, "price_checks.json", lambda r: r["points"][0].update(main_price=0.0))
    errors, _ = rebind()
    assert any("points[0].main_price" in e for e in errors), errors
    # 6f F01：收据第二价被改成 2.0（偏差 66.67%）但 status 仍 PASS → 逐点重算不一致
    assert write_price_receipt(case, second_price=1.0) == 0
    update(case, "price_checks.json", lambda r: r["points"][1].update(second_price=2.0))
    errors, _ = rebind()
    assert any("points[1].status" in e and "FAIL" in e for e in errors), errors
    # 6g F01：两端阈值相等；WARN 边界（1.0/1.052 → 5.07% WARN）真实收据放行，手改 status=PASS 后拒
    import price_check
    assert (closeout.PRICE_WARN_PCT, closeout.PRICE_FAIL_PCT) == (price_check.WARN_PCT, price_check.FAIL_PCT) == (5.0, 15.0)
    assert write_price_receipt(case, second_price=1.052) == 0
    errors, _ = rebind()
    assert not errors, errors
    update(case, "price_checks.json", lambda r: ([q.update(status="PASS") for q in r["points"]], r.update(verdict="PASS")))
    errors, _ = rebind()
    assert any("points[0].status" in e and "WARN" in e for e in errors), errors
```

说明：①`write()`（`:28-29`）用 `json.dumps` 默认 `allow_nan=True`，写出 `NaN` 字面量；`update()`（`:159-162`）读改写同款；`read()`（`:24-25`）默认解析 `NaN`；②6b 用独立文件名 `price_nan.json`/`price_zero.json`/`price_bad_checks.json`，不污染主夹具与工单绑定；`_load_series` 在 `price_check.py:157` 早于任何写盘；③插在段 6（ALL_SKIP）之后、段 7 之前：此时顶层 `price_source_checks` 仍在场，`rebind()` 可用；6c 覆盖主收据为 ALL_SKIP，6d/6f/6g 各自先重写收据；段 7 起始 `:660` 亦重写收据，不受影响；④`rebind()`/`update()`/`read()`/`sha()`/`write_price_receipt()` 均为既有 helper；`closeout` 为该函数 `:623` 已 import 的模块别名；`price_check` 模块路径由 `:15` sys.path 已含 `scripts/prices`；⑤6g 偏差 `round(0.052/1.026*100, 2)=5.07` WARN；手改全部点 status 与 verdict 为 PASS 使汇总一致、只剩逐点重算不一致，精确命中新块。

RED 证据（改生产代码前逐段独立执行，写 `F01_red_evidence.txt`）：6b 两个文件基线均返回 0 且收据落盘（RED）；6c 基线返回 0（NaN 不落 SKIP、判 PASS）（RED）；6d 基线 errors 为空（RED）；6e 基线 errors 为空（RED）；6f 基线 errors 为空（RED）；6g 阈值断言基线 `AttributeError`（常量不存在）（RED），WARN 边界放行基线 GREEN、手改后基线 errors 为空（RED）。每段记录返回码/errors 原文。

## 3. 完成报告 `F01_done.md` 必含

①0.1 两条命令输出；②§2 各处 `git diff` 原文；③RED 摘要（逐段）；④0.8 各测试结果尾行（含"reseal 未实跑、交调度方本机补验"）；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点；⑧禁读披露。stdout 首行 `# 施工 F01：完成` 或 `# 施工 F01：停工`。

## 4. 登记不修（`code_change_pending.md` Q1–Q4，调度方维护）

- 第二源非有限规范化为 None 走 SKIP（Q1）；阈值常量复制不 import、相等由 6g 守（Q2）；review F05 同源双源不修（Q3）；存量按真实解析规则 0 命中且无任何 price_check 收据、APU 暂不重跑（Q4）。
- 文档 `report-template.md:278` 不增字；契约由 CHANGELOG 条目（收官段）与 `price_receipt_errors` docstring 承载。
- reseal 补验：本段 commit 后由调度方在主仓库干净、`/tmp/w3_acceptance` 同步 HEAD 时执行 `test_stage2_reseal.py`。
