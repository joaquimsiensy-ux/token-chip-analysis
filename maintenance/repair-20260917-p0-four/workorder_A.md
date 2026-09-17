# 工单 A（v4，融合 codex 复核 r1 七条＋r2 两条＋r3 一条）：R08 图 2 对账有限值检查 —— repair-20260917-p0-four 第一段

> v4 变更（`review_A_reply_r3.md` A-R3-01）：用例 13 的基线描述订正为"基线在 `:338` 写 PASS 收据时被 mock 的 OSError 炸出、未收敛"，取证改为同时捕获 `SystemExit`/`OSError` 后用 `check()` 断言；新登记两处范围外同族边界（fig1 豁免键超大整数溢出、普通 PASS/FAIL 分支写收据 OSError 仍直接传播）。

> 出处：codex 对 7.0.4 的 review（`REVIEW.md` R08，P0）——`fig2_check_errors` 的末点比较 `abs(NaN - want) > tol` 恒为 False，NaN 末点落进 PASS 分支签收据；用户 2026-09-17 裁决"加有限值检查"。总计划 `~/.claude/plans/r09-p0-codex-codex-codex-starry-feigenbaum.md`。原则：**不增加 skill 上下文**（本段文档零改动）；能删不增、能改不增。
> v3 变更（`review_A_reply_r2.md`）：A-R2-01 数值检查改用 `_pct_value_ok` 辅助，超大整数的 `OverflowError` 归入非法值进 FAIL 收据分支，新增用例 11/12；A-R2-02 写 FAIL 收据的 `OSError` 收敛为"收据未更新"提示仍 FAIL 退出，新增用例 13；split-run 引用行订正为 `:183`。
> v2 变更（`review_A_reply_r1.md`）：A-01 fig1 state 路径保留宽松解析；A-02 失败分支写 FAIL 收据覆盖陈旧 PASS，用例 10；A-03 A2 锚改 `:306`；A-04 用例拆独立子函数；A-05 字节统计改 stat；A-06 说明订正；A-07 停工报告入白名单。
> 内容基线：`scripts/`、`references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md` 与 commit `4cbfe48`（v7.1.3）逐字节相同；本工单与提示词已单独 commit，HEAD 会晚于 4cbfe48。

## 0. 开工纪律

- 0.1 工作目录＝本仓库物理路径 `/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并把输出贴进 `A_done.md`：`git status --short`（须为空）和 `git diff --stat 4cbfe48 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。任一不空即停工写 `A_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/` 下任何文件（插件启动搜索若已读 memories，在 done 里如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容（§1.1 只按元数据统计大小）。
- 0.3 **白名单**（只允许改/建这些文件）：生产 `scripts/report/figures_from_facts.py`；测试 `scripts/tests/test_repair_batch_c.py`；本目录新建 `A_done.md`、`A_red_evidence.txt`，停工时 `A_done_attempt1_stopped.md`。RED 取证用内联 Python（`python3 -c` 或 heredoc），不新建其他文件。
- 0.4 **不改**：`scripts/report/audit_release_gate.py`（收据消费者 `check_figure2_receipt` 本段不动；`lines_checked>0`/实体线覆盖属用户已接受残余，split-run.md:183，只登记不修）；`scripts/report/stage2_closeout.py`（`:63` 的裸 `json.loads` 属范围外，登记）；`figures_from_facts.py` 里 `DEFAULT_TOL_PP`、`CHECK_RECEIPT_NAME`、`_write_check_receipt`（`:257`）与 `_file_ref`（`:223`）的 schema/字段/写法、fig2 线↔实体匹配逻辑（`:289-303`）、fig1 的豁免键有限值检查（`:139-144`）；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`scripts/tests/contract_manifest.json`、`scripts/tests/invariant_manifest.json`；其他测试文件只跑不改。
- 0.5 行号均指施工前基线；改动前先 `grep -n -F '<锚文本>'` 核验恰 1 处且行号一致，不符**停工**不猜改（通用语句如 `continue`/`try:` 不作锚）。删除 > 修改 > 新增。
- 0.6 离线；不 commit（Fable 代 commit）、不 push、不部署 `~/.claude/commands/`；禁 stash/checkout/reset。
- 0.7 先红后绿：A5 新用例先在改动前逐个跑取 RED 证据写入 `A_red_evidence.txt`，再改生产代码，再跑取 GREEN。
- 0.8 不跑全套 `run_all.py`（由调度方在树静止后本机跑）。本段定向跑五个：`python3 -B scripts/tests/test_repair_batch_c.py`、`python3 -B scripts/tests/test_stage2_closeout.py`（含 `fig2_check_errors` 坏 JSON 须抛 ValueError 的契约，:569-574）、`python3 -B scripts/tests/test_figures_from_facts.py`（:150-151 要求 fig1 的 NaN 报错含 `burn_cum_pct` 与 `非有限`）、`python3 -B scripts/tests/test_repair_batch1.py`（:993-994 同款契约）、`python3 -B scripts/tests/test_repair_batch_d.py`（:1207-1212 空 series `[]` 端到端）。五个须全 PASS。

## 1. 硬约束

- 1.1 文档三处字节不变：`SKILL.md` 8021、`references/**/*.md` 合计 930070、`commands-staging/*.md` 合计 8798。统计只用元数据：`stat -f %z SKILL.md`；`find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'`；`stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'`。改后三数原样贴进 done。
- 1.2 `git diff --stat` 只含 0.3 白名单文件。
- 1.3 现有 `t_fc5_receipt_chain`（:1109-1198）与 `t_f04_tolpp_clamp`（:1201 起）所有既有 `check(...)` 断言不改且全 PASS。

## 2. 逐条施工（`scripts/report/figures_from_facts.py`）

### A1 `_load` 加 strict 参数：check/flow/fig2-series 路径拒 NaN/Infinity 字面量，fig1 state 路径保留宽松；同时新增 pct 数值合法性辅助

`:63-65`（锚 `def _load(p):` / `    with open(p, encoding="utf-8") as f:` / `        return json.load(f)`）。在 `:63` 之前、`:60`（锚 `FIG1_LEGEND_RECEIPT_SCHEMA = "figure1-legend/v1"`）之后新增两个模块级函数，并把 `_load` 改为：

```python
def _reject_constant(token):
    """JSON 的 NaN/Infinity/-Infinity 字面量一律拒（标准 JSON 不允许；Python json 默认放行）。"""
    raise ValueError(f"JSON 非有限数值字面量 {token} 拒收（NaN/Infinity）")


def _pct_value_ok(v):
    """pct 单点合法：非 bool 的 int/float，且可转为有限 float（超大整数转 float 的
    OverflowError 也算非法——不能让它在检查阶段抛异常绕过 FAIL 收据分支）。"""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    try:
        return math.isfinite(float(v))
    except OverflowError:
        return False


def _load(p, strict=True):
    with open(p, encoding="utf-8") as f:
        return json.load(f, parse_constant=_reject_constant if strict else None)
```

调用点（已核，7 次调用分布在 6 行）：`:109` fig1 state、`:201` flow facts、`:202` flow spec、`:283` check facts、`:284` check series、`:406` fig2-series 的 series 与 facts。**只把 `:109`**（锚 `    state = _load(a.state)`）改为 `    state = _load(a.state, strict=False)`，其余 6 处不动即默认 strict。理由：fig1 路径已有字段级有限值检查（`:139-144`），且 `test_figures_from_facts.py:150-151`、`test_repair_batch1.py:993-994` 断言报错文本含字段名 `burn_cum_pct`——解析层拒会丢字段名而破坏这两条契约；fig1 非豁免键的 NaN 行为维持基线（不属本段）。`_reject_constant` **必须抛 ValueError**（`fig2_check_errors` `:282-286` 已把 ValueError 透传，`test_stage2_closeout.py:569-574` 要求坏 JSON 抛 ValueError），不得抛 SystemExit。

### A2 `fig2_check_errors` 对 pct 全序列做合法性检查

定位锚：`:306`（锚 `            errs.append(f"{key} 线无 pct 数据")`，全文件唯一）。其下一行 `:307` 是该分支的 `continue`，再下一行 `:308` 是 `        last = float(pct[-1])`（唯一）。在 `:307` 之后、`:308` 之前插入：

```python
        bad = [i for i, v in enumerate(pct) if not _pct_value_ok(v)]
        if bad:
            errs.append(f"{key} 线 pct[{bad[0]}] 非有限/非法数值 {pct[bad[0]]!r}"
                        "（NaN/±Inf/bool/非数/超大整数一律拒，容差不豁免）")
            continue
```

`:308` `last = float(pct[-1])` 保持原样（此时已保证可转为有限 float）。理由：全序列而非只末点——pct 是 producer 数值面，任一点非法即 producer 坏，O(n) 零成本；检查阶段**不得抛异常**（否则 A3 只捕获 ValueError、陈旧 PASS 收据留存），一切非法都走 errs → FAIL 收据。

### A3 `mode_check` 把 ValueError 收敛为 FAIL 并覆盖陈旧收据，收据写入失败也 FAIL 退出

`:328`（锚 `    errs, okc = fig2_check_errors(Path(a.facts), Path(a.series), a.tol_pp)`）改为：

```python
    try:
        errs, okc = fig2_check_errors(Path(a.facts), Path(a.series), a.tol_pp)
    except ValueError as exc:
        # 输入不可用也要留痕：覆盖同目录里可能残留的陈旧 PASS 收据（其输入 sha 仍匹配，
        # 否则发布闸 check_figure2_receipt 会继续接受它）。两输入任一缺失/非常规文件时
        # 无法取 sha，只报错不写收据；收据写入过程本身的 OSError（输入不可读、目录不可写、
        # fsync/replace 失败）也不得吞掉 FAIL 退出——如实提示"收据未更新"。
        if os.path.isfile(a.facts) and os.path.isfile(a.series):
            try:
                _write_check_receipt(a, "FAIL", 0, [f"输入不可用：{exc}"])
            except OSError as io_exc:
                print(f"[CHECK-FAIL] 收据未更新（写入失败：{io_exc}）", file=sys.stderr)
        raise SystemExit(f"FAIL: 图 2 对账输入不可用——{exc}")
```

（`os`/`sys` 已在 `:47-48` import；`_write_check_receipt` `:257` 只经 `_file_ref` `:223` 对文件取字节 sha，不重新解析 JSON。）效果：基线上 NaN 字面量末点**错误 PASS**；加 A1 后解析层抛 ValueError；A3 把它转为 `FAIL:` 行、退出码 1，并把收据写成 `verdict=FAIL`（覆盖陈旧 PASS）；写收据失败时仍退出 1 并提示。`:329-330` 的 `--series 应为 …` 特判不受影响。

### A4 `dumps_fig2_series` 生产侧封口

`:370-372`（锚 `def dumps_fig2_series(lines) -> bytes:` / `    return json.dumps(lines, ensure_ascii=False, sort_keys=True,` / `                      separators=(",", ":")).encode("utf-8")`）：`json.dumps(...)` 加 `allow_nan=False`（基线 `json.dumps(float("nan"))` 会写出 `NaN` 字面量；改后抛 ValueError）。

### A5 测试 `scripts/tests/test_repair_batch_c.py`

在 `t_fc5_receipt_chain` 结束后、`:1201`（锚 `def t_f04_tolpp_clamp():`）之前新增：**每个用例一个独立子函数** `_r08_case_1()` … `_r08_case_13()`（各自建 tempdir、写 facts/ws、跑 CLI 或进程内调用、用既有 `check(name, cond, detail)` 断言），再加汇总函数 `t_r08_nonfinite()` 依次调用十三个子函数；在 `main()` 的 `:2106`（锚 `    t_fc5_receipt_chain()`）之后紧接一行 `    t_r08_nonfinite()`。夹具照 `:1111-1120`（`fff = ROOT / "scripts/report/figures_from_facts.py"` 是函数局部变量，各子函数自行初始化；`facts.json` 同内容：e1 current 278 / total 1000 → want 27.8；`run(cmd, cwd)` `:60`、`check` `:54`、地址常量 `A` `:45` 为既有；`import audit_release_gate as gate` 同 `:1112`）。**series/facts 文件一律 `write_text` 写原文**——精确控制输入文本（`1e400` 不被重编码成 `Infinity`、`NaN` 字面量与 401 位整数原样落盘）。用例与断言（rc＝`p.returncode`，`out=p.stdout+p.stderr`，收据＝tempdir 下 `figure2_check_receipt.json`）：

1. `R08 NaN 末点必 FAIL`：ws `[{"entity_id":"e1","ts":["2026-01-01"],"pct":[NaN]}]` → `rc != 0`、`"字面量" in out`、收据存在且 `verdict == "FAIL"`。**RED**：基线 rc 0、收据 PASS（R08 缺陷本身）。
2. `R08 中间点 Inf 全序列拒`：ws pct `[1e400, 27.8]`（Python json 把 `1e400` 解析为 inf，不经 parse_constant，走 A2）→ `rc == 1`、`"非有限" in out`、收据 `verdict == "FAIL"`。**RED**：基线只看末点 27.8 → PASS。
3. `R08 字符串 pct 拒`：ws pct `["27.8"]` → `rc == 1`、`"非有限" in out`、收据 `verdict == "FAIL"`。**RED**：基线 `float("27.8")` 宽容 → PASS。
4. `R08 null pct 拒且留痕`：ws pct `[null]` → `rc == 1`、收据存在且 `verdict == "FAIL"`。**RED**：基线 `float(None)` TypeError traceback、无收据。
5. `R08 Infinity 字面量解析层拒`：ws pct `[Infinity]` → `rc != 0`、`"字面量" in out`、收据 `verdict == "FAIL"` 且 `mismatches[0]` 含 `输入不可用`。RED：基线 inf 末点走末点分支报"≠ facts 当前"，收据 mismatches 不含"输入不可用"。
6. `R08 exploration 放宽容差不豁免`：用例 1 的 ws，命令加 `--exploration --tol-pp 99` → `rc != 0`、收据 `verdict == "FAIL"` 且 `mode == "exploration"`。**RED**：基线 PASS。
7. `R08 facts 含 NaN 字面量同拒`：facts.json 原文在 `"peak_raw": "300"` 后追加 `, "x": NaN`（其余合法）→ `rc != 0`、`"字面量" in out`。RED：基线放行。
8. `R08 dumps_fig2_series 拒 NaN`：`import figures_from_facts as ffm`（`:37-40` 已把 `scripts/report` 加进 sys.path）；`ffm.dumps_fig2_series([{"entity_id":"e1","ts":["d"],"pct":[float("nan")]}])` 须抛 `ValueError`。RED：基线不抛，输出含 `"pct":[NaN]`。
9. `R08 合法序列仍 PASS`：ws pct `[27.8]` → `rc == 0`、收据 `verdict == "PASS"`（回归）。
10. `R08 陈旧 PASS 收据被 FAIL 覆盖（换输入）`：同一 tempdir 先用 ws `[27.8]` 跑一次得 PASS 收据；再把 ws 原文改为 `[NaN]` 跑一次 → `rc != 0`、收据 `verdict == "FAIL"`、收据 `series.sha256` 等于新 ws 文件的 sha256。**RED**：基线第二次仍 PASS。
11. `R08 超大整数不抛异常、走 FAIL 收据`：ws pct 原文 `[1e400, 1` + 400 个 `0` + `, 27.8]`（401 位整数）→ `rc == 1`、`"非法数值" in out or "非有限" in out`、`"OverflowError" not in out`、收据 `verdict == "FAIL"`。**RED**：基线只看末点 → PASS。（本例专门对 v2 写法：`math.isfinite(10**400)` 抛 OverflowError。）
12. `R08 同输入陈旧 PASS 收据被覆盖且消费者拒`：ws 原文 `[NaN]`；**手写**一份 PASS 收据到 tempdir（schema `figure2-check-receipt/v1`、mode formal、tol_pp 0.05、verdict PASS、facts/series 的 `{path, sha256}` 用当前文件真实 sha，写法照 `:1170-1196` NC1 段）；先断言基线消费者接受：`errs=[]; gate.check_figure2_receipt(td, 手写收据, errs); errs == []`；再跑 check → `rc != 0`；重读收据 `verdict == "FAIL"`；再 `gate.check_figure2_receipt(td, 重读收据, errs2)` → `any("非 PASS" in x for x in errs2)`。**RED**：基线 check 对 `[NaN]` 仍 PASS，收据 verdict 保持 PASS、消费者不拒。
13. `R08 收据写入失败仍 FAIL 退出`：进程内：`import argparse, io, contextlib; from unittest import mock`；ws 原文 `[NaN]`；`ns = argparse.Namespace(facts=str(td/"facts.json"), series=str(td/"ws.json"), tol_pp=0.05, exploration=False)`；`with mock.patch.object(ffm, "_write_check_receipt", side_effect=OSError("disk full")), contextlib.redirect_stderr(buf):` 调 `ffm.mode_check(ns)`，**用 `try/except (SystemExit, OSError) as e` 捕获并记录异常**，再用既有 `check()` 断言三条：`isinstance(e, SystemExit)`；`isinstance(e.code, str) and e.code.startswith("FAIL:")`；`"收据未更新" in buf.getvalue()`。基线上捕获到的是 `OSError("disk full")`（基线错误接受 NaN 后在 `:338` `_write_check_receipt(a, "PASS", okc, [])` 处被 mock 炸掉，`return 0` 不会执行），第一条 `check` 即以 AssertionError 记 FAIL（异常原文进证据）；不得把任意异常都算 GREEN。**RED**：基线抛未收敛的 OSError。

RED 证据（改生产代码前）：用内联 Python 逐个调用 `_r08_case_1` … `_r08_case_13`，每个 `try/except AssertionError` 打印用例名与异常原文（不要顺序调用 `t_r08_nonfinite()`——既有 `check` 在首个失败即抛），把 1/2/3/4/6/10/11/12/13 的 FAIL 原文写入 `A_red_evidence.txt`（含命令、被测文件与测试文件 sha256）。改后跑整文件 `test_repair_batch_c.py` 全 PASS。

## 3. 完成报告 `A_done.md` 必含

①0.1 两条命令原始输出；②A1–A5 逐条改前→改后 diff（`git diff` 原文）；③`A_red_evidence.txt` 路径与 RED 摘要；④0.8 五个测试的结果尾行；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点（若有）；⑧禁读披露。stdout 首行 `# 施工 A：完成` 或 `# 施工 A：停工`。

## 4. 登记不修（`code_change_pending.md`，调度方维护）

- 收据消费者不验 `lines_checked>0` 与实体线覆盖完整性：split-run.md:183 用户 2026-08-18 拍板接受的残余；`test_repair_batch_d.py:1207-1212` 端到端夹具用空 series。
- `stage2_closeout.py:63` 裸 `json.loads` 读序列（`:459/:468`）：范围外；其 `:458` 序列化经 A4、`:464` 对账经 A1/A2 兜底。
- fig1 state 非豁免键含 NaN 仍进绘图（基线行为，本段不动）。
- `parse_constant` 管不住其他字段里的 `1e400` 被解析成 inf：pct 由 A2 兜、输出序列由 A4 兜；非 pct 字段范围外。
- fig1 豁免键（`:141-144`）遇超大整数 `math.isfinite` 仍抛 OverflowError：§0.4 明确不改，范围外。
- 普通对账 PASS/FAIL 分支写收据（`:334`/`:338`）发生 OSError 仍直接传播：既有边界，A3 只收敛新增的输入失败分支。
