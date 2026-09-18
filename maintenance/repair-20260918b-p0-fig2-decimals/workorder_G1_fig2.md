# 工单 G1（v2，融合 codex 复核 r1 三条 G1-R1-01/02/03；r2 通过，含 r2 标题勘误）：图 2 校验器补必画下限——空 series／缺线／重复线拒 —— repair-20260918b-p0-fig2-decimals 第一段

> 出处：codex 对 7.2.1（f1f473f3）六视角 review F01（P0，半修复）：`figures_from_facts.fig2_check_errors`（`:296-337`）对 `whale_series=[]` 返回 `([], 0)`，producer `check` 写 PASS 收据、发布闸 `check_figure2_receipt` 发布期重算同样 `[]`、`build_html --mode analysis-new` rc=0 出正式 HTML——facts 里明明有"大庄#1"实体却一条线都没画。7.2.1 F04 工单把它登记为 P2 残余的依据是 split-run.md 3b.5"fig2 必画下限由 stage2_closeout 承担"，但普通 build_html 不消费 closeout 收据，该兜底在主轨上实际不存在。用户 09-18 裁决：修。总原则：skill 上下文不增；能删不增、能改不增；references/SKILL/commands 本段零改动。
> 修法：必画规则已存在于 `stage2_closeout.fig2_selection_errors`（`:168-178`：label 以 项目方/大庄/小庄/离场庄 起头即必画）。把它提为 `figures_from_facts` 的共享函数，`fig2_check_errors` 在末尾核"必画集合 ⊆ 已匹配线集合"并拒重复线；closeout 改为调用同一函数（单一来源）。发布闸 `check_figure2_receipt`（7.2.1 F04）已调用 `fig2_check_errors`，自动继承，不改。
> v2 变更（`review_G1_reply_r1.md`）：R1-01 §2.5 用例 1 的 producer/消费者两断言改为"先执行并记录、末尾汇总断言"，避免 `check()` 首断言抛错截断 RED 取证；§0.7 编号订正为 §2.4/§2.5；R1-02 §2.5 新增用例 4"两必画实体、非空 series 只画一个"（缺线 RED→补齐 GREEN）；R1-03 属 G2 §2.9 前提，随 G2 v2 修订；另按 r1 订正 §0.2 importer 引用行号（:1641/:2117），§4 补旧 PASS 收据迁移说明。
> 内容基线：`f1f473f3`（v7.2.1）加本工程已入库的裁决/工单 commit；`scripts/` 与 f1f473f3 逐字节相同。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `G1_done.md`：`git status --short`（须为空）；`git diff --stat f1f473f3 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不空即停工写 `G1_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918-p0-f04-f07/` 与本目录以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。精确读取例外：`scripts/tests/test_repair_batch_c.py:1641`／`:2117` 的既有用例会 `importlib` 加载 `maintenance/repair-20260814-batch2/import_pythia_legacy.py`——允许测试进程自行加载，施工方不得主动阅读/引用/改动。
- 0.3 **白名单**：生产 `scripts/report/figures_from_facts.py`、`scripts/report/stage2_closeout.py`；测试 `scripts/tests/test_figures_from_facts.py`、`scripts/tests/test_repair_batch_c.py`；本目录新建 `G1_done.md`、`G1_red_evidence.txt`，停工时 `G1_done_attempt1_stopped.md`。
- 0.4 **不改**：`audit_release_gate.py`（`check_figure2_receipt` 通过 `fig2_check_errors` 自动继承）、`build_html.py`、`a5_report_seal.py`、`facts_gate.py`；`figures_from_facts.py` 的 `mode_check`（`:340-375`）、`build_fig2_series`（`:378-400`）、`_write_check_receipt`、收据 schema；`stage2_closeout.fig2_series_errors`（`:409` 起）；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`contract_manifest.json`、`invariant_manifest.json`；其他测试只跑不改。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.4/§2.5 新用例在改生产代码前逐例取 RED 写 `G1_red_evidence.txt`（逐例捕获 AssertionError／非零 rc，按真实基线记 RED 或 GREEN→GREEN）。
- 0.8 不跑 `run_all.py`。定向跑（全部须 PASS）：`python3 -B scripts/tests/test_figures_from_facts.py`、`test_repair_batch_c.py`、`test_stage2_closeout.py`、`test_a4_gate.py`、`test_repair_batch_d.py`、`test_review_20260804_p105.py`、`test_repair_batch_b.py`、`test_audit_release_gate.py`、`test_repair_g1_cross_target.py`、`python3 -B scripts/tests/invariant_scan.py`。冷字体缓存环境项：`test_a4_gate.py`/`test_stage2_closeout.py` 自设 `MPLCONFIGDIR` 遇 `data_broken: '_items'` 时保留首次输出写 done，再 `MPLCONFIGDIR="$HOME/.matplotlib" python3 -B …` 重跑，重跑必须真实 PASS。

## 1. 硬约束

- 1.1 文档三处字节不变：`SKILL.md` 8021、`references/**/*.md` 合计 930061、`commands-staging/*.md` 合计 8798。只用元数据：`stat -f %z SKILL.md`；`find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'`；`stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'`。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 既有空 series 绿例不得变红：`test_a4_gate.py:498/507`（labels `{"e1":"实体1"}`）、`test_repair_batch_d.py:1205/1206`（默认 label＝entity_id `e1`）、`test_review_20260804_p105.py:214/222`（默认 label）——三处实体 label 均不以必画前缀起头，按 §2.1 规则不属必画，空 series 仍 PASS。开工核实这三处 facts 实体 label 确实不带前缀（读 `test_audit_release_gate.py:202-226` `build_facts_from_ledgers` 的 `names[eid] = (labels or {}).get(eid, eid)`），核实结果写 done。
- 1.4 `test_stage2_closeout.py` 全部用例（含 `fig2_required_from_label` `:235`、`:259` 的 `观察实体` 非必画、`:459-466` 的额外线 e2）保持 PASS——closeout 改为复用共享函数后规则语义不变。
- 1.5 `fig2_check_errors` 的返回类型、异常面（装载阶段 OSError/ValueError → ValueError；非 list series 返回固定句）不变，`mode_check:362` 的固定句判断继续成立。

## 2. 逐条施工

### 2.1 `scripts/report/figures_from_facts.py` —— 共享必画规则

在 `:60`（锚 `FIG1_LEGEND_RECEIPT_SCHEMA = "figure1-legend/v1"`，唯一）之后新增：

```python
FIG2_REQUIRED_LABEL_PREFIXES = ("项目方", "大庄", "小庄", "离场庄")


def fig2_required_entity_ids(entities) -> set:
    """图 2 必画下限：facts.entities 中 label 以 项目方/大庄/小庄/离场庄 起头的实体
    （与 stage2_closeout 工单选材同一规则；刷量地址/观察实体不在下限内）。"""
    return {str(eid) for eid, ent in (entities or {}).items()
            if isinstance(ent, dict)
            and str(ent.get("label") or "").strip().startswith(FIG2_REQUIRED_LABEL_PREFIXES)}
```

### 2.2 `scripts/report/figures_from_facts.py` —— `fig2_check_errors` 补覆盖与重复检查

- `:307`（锚 `    errs, okc = [], 0`，唯一）改为 `    errs, okc, seen = [], 0, set()`。
- `:320`（锚 `        pct = line.get("pct") or []`，唯一）之前、即 `:316-319` "无匹配" `else` 分支的 `continue` 之后插入：

```python
        if eid in seen:
            errs.append(f"{key} 线重复出现（同一实体只能一条线）")
            continue
        seen.add(eid)
```

- `:337`（锚 `    return errs, okc`，唯一）改为：

```python
    missing = sorted(fig2_required_entity_ids(facts.entities) - seen)
    if missing:
        errs.append(f"图 2 缺必画实体线 {missing}（label 以 "
                    f"{'/'.join(FIG2_REQUIRED_LABEL_PREFIXES)} 起头的实体必须各有一条线；"
                    "空 series 不得放行）")
    return errs, okc
```

- 模块 docstring `:29`（锚 `         series 条目带 entity_id 的按 id 对 facts 实体；否则按 label 匹配。`，唯一）之后追加一行（同缩进）：`         必画下限：label 以 项目方/大庄/小庄/离场庄 起头的实体须各有一条线，缺线/重复线/空 series 拒。`

说明：①`seen` 收集的是**已匹配到 facts 实体**的 eid（按 entity_id 或 label 匹配后的 facts 键），线在 pct 校验失败时仍计入 seen（缺线与坏数据分开报，不重复报）；②"无匹配"的线不进 seen；③非 list series 的早退句 `:304` 不变；④`Facts.entities`（facts_gate `Facts` 类）就是 facts["entities"] dict，开工核实属性名（`grep -n "self.entities" scripts/report/facts_gate.py`）。

### 2.3 `scripts/report/stage2_closeout.py` —— `fig2_selection_errors` 复用共享规则

`:171-178`（位于 `:168` `def fig2_selection_errors(facts, fig2):` 内；起锚 `    required = set()`、止锚 `            required.add(entity_id)` 在文件内各出现 2 次，**只改 fig2_selection_errors 内的第 1 处**，`flow_selection_errors` 内的同名片段不动）替换为：

```python
    for entity_id, entity in entities.items():
        label = entity.get("label")
        if not isinstance(label, str) or not label.strip():
            errors.append(workorder_error(f"facts.entities.{entity_id}.label",
                                         f"实体 {entity_id} 无标签，无法判定必画", label))
    import figures_from_facts
    required = figures_from_facts.fig2_required_entity_ids(entities)
```

说明：局部 import 与同文件 `:410`（`fig2_series_errors` 内 `    import figures_from_facts`）同款惯例，不加模块级 import（避免 closeout 装载即拉 matplotlib 的行为变化）；`:179` 起其余逻辑不动。

### 2.4 `scripts/tests/test_figures_from_facts.py` —— check 段补两例

在 `:182`（锚 `        assert r.returncode != 0 and "不同源" in r.stdout, f"偏 0.5pp 应挂: {r.stdout}"`，唯一）之后插入（同缩进；facts 夹具 `fp` 含 e1 label `大庄#1`——开工核实 `FACTS` 夹具定义，写 done）：

```python
        # 4b) G1：facts 有必画实体（大庄#1）而 series 为空 → FAIL（不得 PASS 0 条）
        json.dump([], open(ser_p, "w"))
        r = run(["check", "--facts", fp, "--series", ser_p])
        assert r.returncode != 0 and "缺必画实体线" in r.stdout, f"空 series 应挂: {r.stdout}"
        # 4c) G1：同一实体两条线 → FAIL
        json.dump([{"entity_id": "e1", "ts": ["2026-01-03"], "pct": [27.84]}] * 2,
                  open(ser_p, "w"))
        r = run(["check", "--facts", fp, "--series", ser_p])
        assert r.returncode != 0 and "重复出现" in r.stdout, f"重复线应挂: {r.stdout}"
```

### 2.5 `scripts/tests/test_repair_batch_c.py` —— 新用例 `_g1_case_1..4` 挂进 `t_r08_nonfinite`

在 `:1563`（锚 `def _f04_case_4():`，唯一）所在函数结束后、`:1584`（锚 `def t_r08_nonfinite():`，唯一）之前新增四个子函数（各自 tempdir；`check`/`run`/`write_json`/`ROOT`/`A` 为既有；facts 夹具照 `:1502-1505`）；在 `:1601`（锚 `    _f04_case_4()`，唯一）之后紧接四行调用 `_g1_case_1()` … `_g1_case_4()`。`main()` 不动。

1. `G1 空 series 对非空必画实体：producer FAIL＋消费者拒`：facts e1 label `大庄#1`；ws `[]`；**先执行再断言**（`check()` `:54-56` 首断言即抛错，若先断 producer 则消费者 RED 取不到证据——R1-01）：`p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)` 记 `prod_rc, prod_out`；再手写 PASS 收据（写法照 `:1508-1513`，sha 用真实文件）→ `errs = []; gate.check_figure2_receipt(td, rcpt, errs)`；最后两条 `check`：`check("G1 空 series producer 拒", prod_rc != 0 and "缺必画实体线" in prod_out, prod_out)`、`check("G1 空 series 消费者拒", any("缺必画实体线" in x for x in errs), str(errs))`。RED 取证时逐条 try/except 各自记录。两断言基线均 **RED**（基线 rc 0、errs `[]`）。
2. `G1 重复线拒`：ws `[{"entity_id":"e1","ts":["2026-01-01"],"pct":[27.8]}] * 2` → producer rc != 0 且 stdout 含 `重复出现`。**RED**。
3. `G1 非必画实体空 series 仍放行（GREEN→GREEN）`：facts e1 label `观察实体`；ws `[]` → producer rc == 0；收据 verdict PASS；消费者 errs `[]`。
4. `G1 非空 series 漏必画实体拒→补齐放行`（R1-02）：facts 两实体 `e1` label `大庄#1`（current 278）、`e2` label `小庄#2`（current 100，total 1000 → 10.0）；ws 只含 e1 一条（pct `[27.8]`）→ producer rc != 0 且 stdout 含 `缺必画实体线 ['e2']`；手写 PASS 收据喂消费者 → errs 含 `['e2']`（同样先执行后汇总断言）；再把 ws 补成 e1+e2 两条（e2 pct `[10.0]`）→ producer rc == 0、消费者 errs `[]`。缺线两断言基线 **RED**，补齐段 GREEN→GREEN。

RED 证据：改生产代码前逐个调用 `_g1_case_1/2/4`（用例内各断言独立捕获）与 §2.4 两条 assert，记录 AssertionError／rc 原文（含命令与被测文件 sha256）。

## 3. 完成报告 `G1_done.md` 必含

①0.1 两条命令输出；②§2 各处 `git diff` 原文；③RED 摘要；④0.8 各测试结果尾行；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点（含 §1.3/§2.2④/§2.4 开工核实结果）；⑧禁读披露。stdout 首行 `# 施工 G1：完成` 或 `# 施工 G1：停工`。

## 4. 登记不修（`code_change_pending.md` Q3/Q4，调度方维护）

- 文档 `report-template.md:222` 不增字；必画下限只按 label 前缀（与 closeout 同源），不按 tier/category。
- 存量迁移（明示）：旧案若 whale_series 缺必画线或有重复线，其既有 PASS 收据在新发布闸重算时失效——须修序列（`fig2-series` 重装配）→ 重跑 `check` → 重建 A4/stage2 收口/A5 下游封口；schema 不升版，合法完整的旧收据仍过。CHANGELOG 登记由收官段 E 承担（本段禁改 CHANGELOG）。
