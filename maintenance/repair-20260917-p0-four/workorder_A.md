# 工单 A（v1）：R08 图 2 对账有限值检查 —— repair-20260917-p0-four 第一段

> 出处：codex 对 7.0.4 的 review（`REVIEW.md` R08，P0）——`fig2_check_errors` 的末点比较 `abs(NaN - want) > tol` 恒为 False，NaN 末点落进 PASS 分支签收据；用户 2026-09-17 裁决"加有限值检查"。总计划 `~/.claude/plans/r09-p0-codex-codex-codex-starry-feigenbaum.md`。原则：**不增加 skill 上下文**（本段文档零改动）；能删不增、能改不增。
> 内容基线：`scripts/`、`references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md` 与 commit `4cbfe48`（v7.1.3）逐字节相同；本工单与提示词已单独 commit，HEAD 会晚于 4cbfe48。

## 0. 开工纪律

- 0.1 工作目录＝本仓库物理路径 `/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并把输出贴进 `A_done.md`：`git status --short`（须为空）和 `git diff --stat 4cbfe48 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。任一不空即停工写 `A_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/` 下任何文件（插件启动搜索若已读 memories，在 done 里如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`。
- 0.3 **白名单**（只允许改这些文件）：生产 `scripts/report/figures_from_facts.py`；测试 `scripts/tests/test_repair_batch_c.py`；本目录新建 `A_done.md`、`A_red_evidence.txt`。
- 0.4 **不改**：`scripts/report/audit_release_gate.py`（收据消费者 `check_figure2_receipt` 本段不动；`lines_checked>0`/实体线覆盖属用户已接受残余，split-run.md:184，只登记不修）；`figures_from_facts.py` 里 `DEFAULT_TOL_PP`、`CHECK_RECEIPT_NAME`、`_write_check_receipt` 的 schema 与字段、fig2 线↔实体匹配逻辑（`:289-303`）；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`scripts/tests/contract_manifest.json`、`scripts/tests/invariant_manifest.json`。
- 0.5 行号均指施工前基线；改动前先 `grep -n -F '<锚文本>'` 核验恰 1 处且行号一致，不符**停工**不猜改。删除 > 修改 > 新增。
- 0.6 离线；不 commit（Fable 代 commit）、不 push、不部署 `~/.claude/commands/`；禁 stash/checkout/reset。
- 0.7 先红后绿：A5 新用例先在改动前跑一次取 RED 证据（命令、退出码、输出原文、测试文件与被测文件 sha256）写入 `A_red_evidence.txt`，再改生产代码，再跑取 GREEN。
- 0.8 不跑全套 `run_all.py`（约 11 分钟，由调度方在树静止后本机跑）；本段只跑 `python3 -B scripts/tests/test_repair_batch_c.py` 与 `python3 -B scripts/tests/test_stage2_closeout.py`（后者含 `fig2_check_errors` 坏 JSON 须抛 ValueError 的契约，:569-574）。

## 1. 硬约束

- 1.1 文档三处字节不变：`SKILL.md` 8021、`references/**/*.md` 合计 930070、`commands-staging/*.md` 合计 8798（`wc -c SKILL.md`；`find references -name '*.md' -print0 | xargs -0 cat | wc -c`；`cat commands-staging/*.md | wc -c`）。改后三数原样贴进 done。
- 1.2 `git diff --stat` 只含 0.3 白名单文件。
- 1.3 现有 `t_fc5_receipt_chain`（:1109-1198）与 `t_f04_tolpp_clamp`（:1201 起）所有既有 `check(...)` 断言不改且全 PASS。

## 2. 逐条施工（`scripts/report/figures_from_facts.py`）

### A1 `_load` 拒 NaN/Infinity 字面量

`:63-65`（锚 `def _load(p):` / `    with open(p, encoding="utf-8") as f:` / `        return json.load(f)`）。在 `:63` 之前、`:60`（锚 `FIG1_LEGEND_RECEIPT_SCHEMA = "figure1-legend/v1"`）之后新增模块级函数，并把 `:65` 改为带 `parse_constant`：

```python
def _reject_constant(token):
    """JSON 的 NaN/Infinity/-Infinity 字面量一律拒（标准 JSON 不允许；Python json 默认放行）。"""
    raise ValueError(f"JSON 非有限数值字面量 {token} 拒收（NaN/Infinity）")


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f, parse_constant=_reject_constant)
```

说明（已核）：`_load` 服务 fig1 state、flow spec、check 双输入、fig2-series 五路；fig1 路径本已对豁免键做 isfinite（`:139-144`），提前在解析层拒更严、无回归；`fig2_check_errors` 的 `:282-286` 已把 `ValueError` 透传（`raise ValueError(str(exc)) from exc`），`test_stage2_closeout.py:569-574` 要求坏 JSON 抛 ValueError，故 `_reject_constant` **必须抛 ValueError**，不得抛 SystemExit。

### A2 `fig2_check_errors` 对 pct 全序列做类型＋有限值检查

`:304-308`（锚 `        pct = line.get("pct") or []` … `        last = float(pct[-1])`）。在 `:307`（锚 `            continue`，即"线无 pct 数据"分支的 continue）之后、`:308`（锚 `        last = float(pct[-1])`）之前插入：

```python
        bad = [i for i, v in enumerate(pct)
               if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)]
        if bad:
            errs.append(f"{key} 线 pct[{bad[0]}] 非有限数值 {pct[bad[0]]!r}"
                        "（NaN/±Inf/bool/非数一律拒，容差不豁免）")
            continue
```

`:308` `last = float(pct[-1])` 保持原样（此时已保证为有限数）。写法与 `:139-144` 同族（`math` 已在 `:46` import）。理由：全序列而非只末点——pct 是 producer 数值面，任一点非有限即 producer 坏，O(n) 零成本；中间点断线虽不是末点对账的职责，但"非有限值"是数据契约层面的拒收。

### A3 `mode_check` 把 ValueError 收敛为 FAIL

`:328`（锚 `    errs, okc = fig2_check_errors(Path(a.facts), Path(a.series), a.tol_pp)`）改为：

```python
    try:
        errs, okc = fig2_check_errors(Path(a.facts), Path(a.series), a.tol_pp)
    except ValueError as exc:
        raise SystemExit(f"FAIL: 图 2 对账输入不可用——{exc}")
```

效果：NaN 字面量在 check 路径由 traceback 变为 `FAIL:` 行、退出码 1、**不写收据**（解析层已拒，无 PASS 收据可被发布闸消费＝fail-closed）。

### A4 `dumps_fig2_series` 生产侧封口

`:370-372`（锚 `def dumps_fig2_series(lines) -> bytes:` / `    return json.dumps(lines, ensure_ascii=False, sort_keys=True,` / `                      separators=(",", ":")).encode("utf-8")`）：`json.dumps(...)` 加 `allow_nan=False`（NaN 进序列时 `json.dumps` 抛 ValueError，不再写出 `NaN` 字面量）。

### A5 测试 `scripts/tests/test_repair_batch_c.py`

新增函数 `t_r08_nonfinite()`，放在 `t_fc5_receipt_chain` 结束后、`:1201`（锚 `def t_f04_tolpp_clamp():`）之前；在 `main()` 的 `:2106`（锚 `    t_fc5_receipt_chain()`）之后紧接一行 `    t_r08_nonfinite()`。夹具照 `:1111-1120`（`fff`、`facts.json` 同内容：e1 current 278 / total 1000 → want 27.8；`run(cmd, cwd)` 与 `check(name, cond, detail)` 为本文件既有辅助，`A` 为既有地址常量）。**series 文件一律用 `write_text` 写原文**（`json.dumps` 写不出 NaN 字面量）。每个用例独立 tempdir 或改写同一 tempdir 前先删旧收据。用例与断言：

1. `R08 NaN 末点必 FAIL`：ws `[{"entity_id":"e1","ts":["2026-01-01"],"pct":[NaN]}]` → `p.returncode != 0`，且 `"非有限" in p.stdout or "字面量" in p.stdout+p.stderr`，且收据文件不存在或 `verdict != "PASS"`。**RED**：基线上 `returncode == 0`、收据 `verdict == "PASS"`（这就是 R08 缺陷本身）。
2. `R08 中间点 Inf 全序列拒`：ws pct `[1e400, 27.8]`（原文写 `1e400`，Python json 解析为 inf，不经 parse_constant，走 A2）→ `returncode == 1`、stdout 含 `非有限`、收据 `verdict == "FAIL"`。**RED**：基线只看末点 27.8 → PASS。
3. `R08 字符串 pct 拒`：ws pct `["27.8"]` → `returncode == 1`、stdout 含 `非有限`、收据 `verdict == "FAIL"`。**RED**：基线 `float("27.8")` 宽容 → PASS。
4. `R08 null pct 拒且留痕`：ws pct `[null]` → `returncode == 1`、收据存在且 `verdict == "FAIL"`。**RED**：基线 `float(None)` TypeError traceback、无收据。
5. `R08 Infinity 字面量解析层拒`：ws pct `[Infinity]` → `returncode != 0`、`p.stdout + p.stderr` 含 `字面量`、收据文件不存在（解析层拒、未到写收据）。（基线 inf 末点本已 FAIL 但走的是末点分支且会写 FAIL 收据；本例断言"含字面量且无收据"在基线上不成立＝RED。）
6. `R08 exploration 放宽容差不豁免`：用例 1 的 ws，命令加 `--exploration --tol-pp 99` → `returncode != 0`。**RED**：基线 PASS。
7. `R08 facts 含 NaN 字面量同拒`：facts.json 原文把 `"peak_raw": "300"` 后追加 `, "x": NaN`（保持其余合法）→ `returncode != 0`、输出含 `字面量`。RED：基线 Python json 放行 NaN。
8. `R08 dumps_fig2_series 拒 NaN`：`import figures_from_facts as ffm`（本文件已把 `scripts/report` 加进 sys.path，同 `:1112` 的 `import audit_release_gate` 方式）；`ffm.dumps_fig2_series([{"entity_id":"e1","ts":["d"],"pct":[float("nan")]}])` 须抛 `ValueError`。RED：基线不抛、写出 `NaN` 字面量。
9. `R08 合法序列仍 PASS`：ws pct `[27.8]` → `returncode == 0`、收据 `verdict == "PASS"`（回归）。

RED 证据：改生产代码前跑一次本函数（只跑它：可临时用 `python3 -c "import sys; sys.path.insert(0,'scripts/tests'); import test_repair_batch_c as t; t.t_r08_nonfinite()"` 或等价方式），把用例 1/2/3/4/6 的 FAIL 原文写入 `A_red_evidence.txt`；改后再跑同命令全 PASS。

## 3. 完成报告 `A_done.md` 必含

①0.1 两条命令原始输出；②A1–A5 逐条改前→改后 diff（`git diff` 原文）；③`A_red_evidence.txt` 路径与用例 1/2/3/4/6 的 RED 摘要；④`python3 -B scripts/tests/test_repair_batch_c.py` 与 `test_stage2_closeout.py` 的结果尾行；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点（若有）；⑧禁读披露。stdout 首行 `# 施工 A：完成` 或 `# 施工 A：停工`。

## 4. 登记不修（写入本目录 `code_change_pending.md`，由调度方维护，施工方不建）

- 收据消费者不验 `lines_checked>0` 与实体线覆盖完整性：split-run.md:184 用户 2026-08-18 拍板接受的残余风险；`test_repair_batch_d.py:1207-1212` 端到端夹具用空 series。
