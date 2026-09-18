# 工单 F02（v1）：流通量声明进 facts 生产者——state_source.facts_inputs.circulating_supply {raw, asof, source} → facts.token；发布重算一致；选材消费者贯通 —— repair-20260918c-p1-f02-f04-f05 第三段

> 出处：codex 对 8.0.0（8b041842）六视角 review F02（P1，修复中新引入：consumer 82bb26c/7.0.4 → producer 1b317b3/7.1.3→7.2.0 R07）：`stage2_closeout.flow_selection_errors`（`:202-235`）按"总供应 20% 或流通量 20%"选流转图，`:205` 读 `facts.token.circulating_supply_raw`；但 `facts_gate.derive_facts` 生成的 token 只有 symbol/decimals/total_supply_raw（`:477`），`facts_inputs` 契约（`:63-69`）无流通量；手补 facts.token 被 `audit_release_gate.check_facts_vs_ledgers`（`:1569-1573`）重算比对拒。已知流通量的正常案（锁仓比例高的币）无合规入口，本该画的流转图漏画，且只留 NOTE。用户 09-18 裁决：修。总原则：skill 上下文不增；能删不增、能改不增；references/SKILL/commands 本段零改动（`report-template.md:179` 已写"≥20% 总供应或 ≥20% 流通"）。
> 修法：`facts_inputs` 新增**可选**对象 `circulating_supply: {raw, asof, source}`（第三方口径的人工声明，带出处与时点；台账 Q11）；derive 校验后写入 `facts.token.circulating_supply_raw`（消费者既有键名）与 `facts.token.circulating_supply_source {asof, source}`；不声明时 token 不变；扁平键 `facts_inputs.circulating_supply_raw`（review 反例写法）明确拒，不静默忽略；发布闸 `check_facts_vs_ledgers` 比对整个 token 字典，自动一致，不改；closeout 消费者在有流通量时 NOTE 记口径。
> 内容基线：`8b041842`（v8.0.0）加本工程已入库 commit；本段在 F04、F05 落地之后施工。`facts_gate.py`、`test_report_facts.py` 与 8b041842 逐字节相同（行号按 8b041842 核）；`stage2_closeout.py` `:1-236` 与 8b041842 相同（F05 只在 `:238` 前插入与 `:350-354` 替换，本段锚 `:207/:209` 不受影响）；`test_stage2_closeout.py` 已被 F05 改动，本段对其锚**只按锚文本**核唯一，行号以派工时 HEAD 为准（工单 v2 补精确行号）。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `F02_done.md`：`git status --short`（须为空）；`git diff --stat 8b041842 HEAD -- scripts/report/facts_gate.py scripts/tests/test_report_facts.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不空即停工写 `F02_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。精确读取例外：`scripts/tests/test_repair_batch_c.py` 既有用例会 `importlib` 加载 `maintenance/repair-20260814-batch2/import_pythia_legacy.py`——允许测试进程自行加载，施工方不得主动阅读/引用/改动。
- 0.3 **白名单**：生产 `scripts/report/facts_gate.py`、`scripts/report/stage2_closeout.py`；测试 `scripts/tests/test_report_facts.py`、`scripts/tests/test_stage2_closeout.py`；本目录新建 `F02_done.md`、`F02_red_evidence.txt`，停工时 `F02_done_attempt1_stopped.md`。
- 0.4 **不改**：`facts_gate.py` 的 `Facts` 类（`:108-119`，宏与 G2 上界继续只用 total_supply_raw，台账 Q10）、`gate_check`、峰值/override 段（`:407-460`）、`build_main`；`audit_release_gate.check_facts_vs_ledgers`（`:1532-1583`，整 token 字典比对已覆盖新键）、`check_facts_decimals`；`state_from_facts.py`（只读 total/decimals/symbol，新键不影响）；`stage2_closeout.flow_selection_errors` 的阈值逻辑 `:210-216`；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`contract_manifest.json`、`invariant_manifest.json`（写文件点不变；开工用 `python3 -B scripts/tests/invariant_scan.py` 证实）。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致（`test_stage2_closeout.py` 只核唯一性），不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.4/§2.5 新用例在改生产代码前逐例取 RED 写 `F02_red_evidence.txt`。
- 0.8 不跑 `run_all.py`。定向跑（全部须 PASS）：`python3 -B scripts/tests/test_report_facts.py`、`test_stage2_closeout.py`、`test_audit_release_gate.py`、`test_state_from_facts.py`、`test_build_html.py`、`test_repair_batch_c.py`、`test_figures_from_facts.py`、`test_a4_gate.py`、`test_review_20260804_p105.py`、`python3 -B scripts/tests/invariant_scan.py`。冷字体缓存环境项同 F05 工单 §0.8。

## 1. 硬约束

- 1.1 文档三处字节不变：`SKILL.md` 8021、`references/**/*.md` 合计 930076、`commands-staging/*.md` 合计 8798（命令同 F04 工单 §1.1）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 不声明流通量时 derive 产物逐字节不变：`test_report_facts.py:121`（`facts["token"] == {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"}`）与 `test_audit_release_gate.build_facts_from_ledgers` 全部消费者保持 PASS；`run("2 CLI build 幂等")` 保持 PASS。
- 1.4 `derive_facts` 的异常面不变：新增校验一律 `raise ValueError`（`build_main:513` 与 `check_facts_vs_ledgers:1562` 已捕获）。
- 1.5 `flow_selection_errors` 的返回 `(errors, notes)` 与既有错误文案（`包含下限`、`等于 eligible`）不变；`test_stage2_closeout.py:257` 的 `NOTE: 未声明流通量` 在不声明时继续出现。

## 2. 逐条施工

### 2.1 `scripts/report/facts_gate.py` —— 契约 docstring

- `:10`（锚 `  "token": {"symbol": "QUQ", "decimals": 18, "total_supply_raw": "1000...0"},`，唯一）之后插入一行（同缩进）：`           # 可选（F02）：circulating_supply_raw + circulating_supply_source {asof, source}，来自 facts_inputs.circulating_supply`
- `:66`（锚 `      （可选，优先于 provenance 锚点，证据须为案根常规文件）`，唯一）之后插入一行：`  circulating_supply: {raw, asof, source}（可选；raw 正整数串且 ≤ total_supply_raw、asof 严格 YYYY-MM-DD、source 非空口径说明；写入 token.circulating_supply_raw/circulating_supply_source；扁平键 circulating_supply_raw 拒）`

### 2.2 `scripts/report/facts_gate.py` —— derive 解析流通量声明

`:380`（锚 `        raise ValueError("facts_inputs.dual_basis 须为对象")`，唯一）之后（`:381` 空行之前）插入：

```python
    if "circulating_supply_raw" in fi:
        raise ValueError("facts_inputs.circulating_supply_raw 键名错位——流通量须写成 "
                         "circulating_supply: {raw, asof, source}")
    circ = fi.get("circulating_supply")
    circulating = None
    if circ is not None:
        if not isinstance(circ, dict):
            raise ValueError("facts_inputs.circulating_supply 须为对象 {raw, asof, source}")
        circ_raw = _raw_str(circ.get("raw"), "facts_inputs.circulating_supply.raw")
        if not 0 < int(circ_raw) <= int(total_raw):
            raise ValueError(f"facts_inputs.circulating_supply.raw {circ_raw} 须在 (0, total_supply_raw={total_raw}] 内")
        asof = str(circ.get("asof") or "").strip()
        try:
            asof_ok = _dt.date.fromisoformat(asof).isoformat() == asof
        except ValueError:
            asof_ok = False
        if not asof_ok:
            raise ValueError(f"facts_inputs.circulating_supply.asof {asof!r} 非 YYYY-MM-DD")
        src = circ.get("source")
        if not isinstance(src, str) or not src.strip():
            raise ValueError("facts_inputs.circulating_supply.source 须为非空口径说明（如 'CoinGecko circulating 2026-09-14'）")
        circulating = {"raw": circ_raw, "asof": asof, "source": src.strip()}
```

说明：`_raw_str`（`:317`）对非整数串抛 ValueError、负数拒；`raw="0"` 落到范围检查拒。`_dt` 为既有 `import datetime as _dt`（`:72` 附近，开工核实）。

### 2.3 `scripts/report/facts_gate.py` —— token 写出

`:477`（锚 `    facts = {"token": {"symbol": symbol, "decimals": decimals, "total_supply_raw": total_raw},`，唯一；下一行 `:478` `             "entities": entities, "metrics": metrics}` 不动）改为：

```python
    token = {"symbol": symbol, "decimals": decimals, "total_supply_raw": total_raw}
    if circulating is not None:
        token["circulating_supply_raw"] = circulating["raw"]
        token["circulating_supply_source"] = {"asof": circulating["asof"], "source": circulating["source"]}
    facts = {"token": token,
```

### 2.4 `scripts/report/stage2_closeout.py` —— 消费者记口径

`:209`（锚 `        circulating = int(circulating)`，唯一）之后插入（同缩进，仍在 `else:` 分支内）：

```python
        src = facts.get("token", {}).get("circulating_supply_source") or {}
        notes.append(f"NOTE: 流通量 {circulating}（口径 {src.get('source')}，{src.get('asof')}）")
```

### 2.5 `scripts/tests/test_report_facts.py` —— R07 新用例 22/23/24

在 `:326`（锚 `        root, "150", "2026-01-02", [1, 2], "证据内容"))`，唯一）之后、`:327`（`    assert not failures, …`）之前插入：

```python

    def circ(root, value, needle=None):
        edit(root, "state_source.json", lambda obj: obj["facts_inputs"].update(value))
        if needle:
            reject(root, needle)
            return None
        return build(root)

    def circ_green(root):
        facts = circ(root, {"circulating_supply": {"raw": "400", "asof": "2026-01-03", "source": "test circulating"}})
        assert facts["token"]["circulating_supply_raw"] == "400", facts
        assert facts["token"]["circulating_supply_source"] == {"asof": "2026-01-03", "source": "test circulating"}, facts
        assert set(facts["token"]) == {"symbol", "decimals", "total_supply_raw",
                                       "circulating_supply_raw", "circulating_supply_source"}, facts
        errors = []
        gate.check_facts_vs_ledgers(root, facts, errors)
        assert errors == [], errors

    def circ_hand_edit(root):
        facts = build(root)
        facts["token"]["circulating_supply_raw"] = "400"
        _r07_write(root, "facts.json", facts)
        errors = []
        gate.check_facts_vs_ledgers(root, facts, errors)
        assert any("facts.token" in error for error in errors), errors

    run("22 F02 流通量声明→token 带字段、发布重算一致", circ_green)
    for value, needle in (
            ({"circulating_supply": {"raw": "2000", "asof": "2026-01-03", "source": "x"}}, "total_supply_raw"),
            ({"circulating_supply": {"raw": "0", "asof": "2026-01-03", "source": "x"}}, "total_supply_raw"),
            ({"circulating_supply": {"raw": "400", "asof": "20260103", "source": "x"}}, "非 YYYY-MM-DD"),
            ({"circulating_supply": {"raw": "400", "asof": "2026-01-03", "source": " "}}, "source"),
            ({"circulating_supply": "400"}, "须为对象"),
            ({"circulating_supply_raw": "400"}, "键名错位")):
        run("23 F02 流通量非法拒 " + needle, lambda root, v=value, n=needle: circ(root, v, n))
    run("24 F02 手补 token.circulating_supply_raw 无声明→闸拒（GREEN→GREEN）", circ_hand_edit)
```

`:328`（锚 `    print(f"PASS: R07 build/derive/发布闸 21 类、{len(results)} 个独立用例", flush=True)`，唯一）中 `21 类` 改为 `24 类`。

### 2.6 `scripts/tests/test_stage2_closeout.py` —— producer→consumer 贯通用例

新函数放在锚 `def facts_vs_ledgers_rejects_hand_edit(cases):`（唯一）之前；`TESTS` 列表末尾（F05 落地后末元素为 `price_receipt_content_enforced]`，锚按派工时 HEAD 核唯一）追加 `, circulating_supply_producer_to_consumer`：

```python
def circulating_supply_producer_to_consumer(cases):
    """F02：流通量由 state_source 声明 → facts_gate.derive_facts 产出 → flow_selection_errors 按流通量分母命中必画。
    seed 案 e1 current 100 / total 1000（10%，总量分支不命中）；声明流通量 400 → 25% 命中。不落盘 facts（避免工单绑定漂移）。"""
    import facts_gate
    import stage2_closeout as closeout
    case = cases.fresh()
    baseline = facts_gate.derive_facts(case)
    assert "circulating_supply_raw" not in baseline["token"], baseline["token"]
    errors, notes = closeout.flow_selection_errors(baseline, {"eligible_entity_ids": [], "charts": []})
    assert not any("包含下限" in e for e in errors), errors
    assert any("未声明流通量" in n for n in notes), notes
    update(case, "state_source.json", lambda s: s["facts_inputs"].update(
        circulating_supply={"raw": "400", "asof": "2026-01-01", "source": "fixture circulating"}))
    facts = facts_gate.derive_facts(case)
    assert facts["token"]["circulating_supply_raw"] == "400", facts["token"]
    errors, notes = closeout.flow_selection_errors(facts, {"eligible_entity_ids": [], "charts": []})
    assert any("包含下限 ['e1']" in e for e in errors), errors
    assert any("口径 fixture circulating" in n for n in notes), notes
```

开工核实并写 done：seed 案 facts `token.total_supply_raw` 与 `entities.e1.current_raw`（`grep -n` `test_audit_release_gate.py` 的 `build_release_case`/夹具账本数值），确认 current×5 < total 且 current×5 ≥ 400；不符则把声明值调到满足"总量分支不命中、流通量分支命中"并在 done 说明。

RED 证据：改生产代码前逐例执行：22（基线 derive 忽略未知键，token 无新键）**RED**；23 六变体（基线不拒）**RED**；24 GREEN→GREEN（手补已被拒）；§2.6 前半（基线不含键/NOTE 未声明）GREEN、后半（声明后 token 无键）**RED**。逐例 try/except 各自记录，写 `F02_red_evidence.txt`。

## 3. 完成报告 `F02_done.md` 必含

①0.1 两条命令输出；②§2 各处 `git diff` 原文；③RED 摘要；④0.8 各测试结果尾行；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点（含 §2.2 `_dt` 核实、§2.6 夹具数值核实）；⑧禁读披露。stdout 首行 `# 施工 F02：完成` 或 `# 施工 F02：停工`。

## 4. 登记不修（`code_change_pending.md` Q10/Q11，调度方维护）

- 流通量不进 G2 上界、不进宏（Q10）；来源为人工第三方口径声明，不做链上重算（Q11）。
- 存量迁移：无强制——旧案 facts 不带新键仍合法；要按流通量选材的旧案在 state_source 加声明后重 build facts → 重跑 stage2 收口（facts sha 变动会使工单/A5 下游绑定失效，按既有重封流程）。
