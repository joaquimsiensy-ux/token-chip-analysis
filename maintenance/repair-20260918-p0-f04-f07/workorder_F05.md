# 工单 F05（v1）：facts 小数位绑定链上观测＋峰值 override 证据类型化＋峰值上界 —— repair-20260918-p0-f04-f07 第四段

> 出处：codex 对 7.2.0（311e6c4）的六视角 review F05（P0，**半修复 R07**）：`facts_gate.derive_facts` 证明了 current/addresses/total 来自三账，却让调用者在 `state_source.facts_inputs` 里自由决定 `decimals`（`:358-363` 只验 ≥0 整数）与 `peak_overrides`（`:404-420` 只验证据文件 path/sha 在场，不看证据内容）；`gate_check`（`:191-203`）只验 peak≥current 与 Σcurrent≤total。反例：review 附录 D `repro_core.py` F05（decimals 0→2、证据 `{"note":"fixture"}`、申报 peak=1,000,000/1900-01-01，facts consumer `[]`，宏渲染 `1.00枚 1000000.00% 1900-01-01`）与 `repro_preseal.py`（同输入放在 A4 前，真实 facts→A4→A5→HTML rc=0，HTML 含错误峰值与日期）。R07 本身就是 APU 案 facts_inputs 小数位真实事故的修复。用户 2026-09-18 裁决：修。总原则：**skill 上下文不增**；能删不增、能改不增；不新立 schema。
> 内容基线：`311e6c4` 加本工程前段（F06/F04/F07）落地 commit；`facts_gate.py`、`test_report_facts.py` 与 311e6c4 逐字节相同；`audit_release_gate.py` 经 F04（`:1571` 起插入约 14 行）与 F07（`:1077-1113` 与 `:1191` 后插入）漂移，**本工单对该文件的锚点（`check_facts_vs_ledgers` `:1497-1548` 及 `_run` 调用处 `:1831`）按 F07 落地后的 HEAD 重新 `grep -n -F` 实证后填入 v2**；`test_audit_release_gate.py` 经 F07 段改动（`_r09_followup`、r09_cases），本工单只在 `build_facts_from_ledgers`（`:202-224`）与新增用例处动。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `F05_done.md`：`git status --short`（须为空）；`git rev-parse --short HEAD`（须与 `construct_F05_prompt.md` 首行一致）；`git diff --stat 311e6c4 HEAD -- scripts/report/facts_gate.py scripts/tests/test_report_facts.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不符即停工写 `F05_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
- 0.3 **白名单**：生产 `scripts/report/facts_gate.py`、`scripts/report/audit_release_gate.py`；测试 `scripts/tests/test_report_facts.py`、`scripts/tests/test_audit_release_gate.py`；登记 `scripts/tests/invariant_manifest.json`（只按 `invariant_scan.py` 报出的缺项增补）；本目录新建 `F05_done.md`、`F05_red_evidence.txt`，停工时 `F05_done_attempt1_stopped.md`。
- 0.4 **不改**：`facts_gate.py` 的宏语法/渲染（`:97-186`）、docstring schema 段（`:1-95`，仅允许 `peak_overrides` 一行说明按 §2.2 改证据格式描述）、`_load_case_json`/`_raw_str`/`build_main`；`audit_release_gate.py` 除 `check_facts_vs_ledgers` 及其调用处外一切（含 F04/F07 已落地段）；`stage2_closeout.py`、`shared_release_receipt.py`、`entity_identity_gate.py`、`identity_snapshot_receipt.py`、`accounting_gate*.py`；`FACTS_PROVENANCE_SCHEMA`（不升版）；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`contract_manifest.json`；其他测试只跑不改。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.4 新用例改动前逐例取 RED 写 `F05_red_evidence.txt`。
- 0.8 不跑 `run_all.py`。定向跑：`python3 -B scripts/tests/test_report_facts.py`、`test_audit_release_gate.py`、`test_state_from_facts.py`、`test_a4_gate.py`、`test_repair_batch_d.py`、`test_review_20260804_p105.py`、`test_stage2_closeout.py`（`dry_run_touches_nothing` 属已知 F12，仅此项失败注明）、`test_figures_from_facts.py`、`python3 -B scripts/tests/invariant_scan.py`。除注明项外全 PASS。

## 1. 硬约束

- 1.1 文档三处字节不变：SKILL.md 8021、references 930061、commands-staging 8798（命令同工单 F06 §1.1）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 `derive_facts` 保持纯函数（只读案内文件、不写盘、不带时间戳、不读时钟）；decimals 的链上一致性放在**发布闸消费侧**，不进 `derive_facts`（stage2 收口复用 derive_facts 比对不受影响）。
- 1.4 存量迁移代价（明示）：R07 起用 `peak_overrides` 的案（APU 0801 待重发布案）证据文件须改为 §2.2 格式重 build；`facts.token.decimals` 与链上观测不符的案在发布闸被拒——这正是目标行为。

## 2. 逐条施工

### 2.1 `scripts/report/facts_gate.py` —— `gate_check` 加峰值供给上界（G2 同族）

`:198-199`（锚 `        if cur > peak:` / `            errors.append(f"G3 {eid} current_raw > peak_raw（{cur} > {peak}）")`）之后追加：

```python
        if facts.total_raw and peak > facts.total_raw:
            errors.append(f"G2 {eid} peak_raw {peak} 超过总供应 {facts.total_raw}")
```

覆盖所有 facts 来源（override、provenance 锚、exploration）。历史供应大于当前供应（通缩/销毁后）的币会被误拒——登记 §4 待用户裁决，本段按"总供应为上界"落地。

### 2.2 `scripts/report/facts_gate.py` —— override 证据类型化＋日期校验

替换 `:408-420`（锚起 `            ev = ov.get("evidence")`，锚止 `                                                "sha256": str(ev["sha256"]).lower()}}`）为：

```python
            ev = ov.get("evidence")
            if not isinstance(ev, dict) or not ev.get("path") or not ev.get("sha256"):
                raise ValueError(f"peak_overrides.{eid} 缺 evidence.path/sha256")
            ev_path = _case_file(case_dir, ev["path"], f"peak_overrides.{eid}.evidence")
            if _sha256_path(ev_path) != str(ev["sha256"]).lower():
                raise ValueError(f"peak_overrides.{eid}.evidence sha256 与案内实物不一致")
            peak = _raw_str(ov.get("peak_raw"), f"peak_overrides.{eid}.peak_raw")
            peak_date = str(ov.get("peak_date") or "").strip()
            if not peak_date:
                raise ValueError(f"peak_overrides.{eid} 缺 peak_date")
            # F05（7.2.1）：证据内容须可解释——JSON 对象，以 entity_id 为键，给出与申报相等的
            # peak_raw/peak_date；hash 只证明文件没变，不证明值来自文件。
            ev_obj = _load_case_json(case_dir, ev["path"], f"peak_overrides.{eid}.evidence")
            ev_ent = ev_obj.get(eid) if isinstance(ev_obj, dict) else None
            if (not isinstance(ev_ent, dict)
                    or _raw_str(ev_ent.get("peak_raw"), f"evidence[{eid}].peak_raw") != peak
                    or str(ev_ent.get("peak_date") or "").strip() != peak_date):
                raise ValueError(f"peak_overrides.{eid} 证据内容与申报 peak_raw/peak_date 不一致"
                                 f"（证据须为 {{\"{eid}\": {{\"peak_raw\", \"peak_date\"}}}}）")
            used_overrides[eid] = {"peak_raw": peak, "peak_date": peak_date,
                                   "evidence": {"path": ev_path.name,
                                                "sha256": str(ev["sha256"]).lower()}}
```

在 `:431`（锚 `        if int(peak) < int(current):`）之前插入日期校验（对 override 与 provenance 锚两条路径统一生效；exploration 路径 `peak_date=None` 跳过）：

```python
        if peak_date is not None:
            try:
                peak_day = _dt.date.fromisoformat(peak_date)
            except ValueError as exc:
                raise ValueError(f"实体 {eid} peak_date {peak_date!r} 非 YYYY-MM-DD: {exc}") from exc
            cur_date = str((((ledger_entities.get(eid) or {}).get("anchors") or {})
                            .get("current") or {}).get("date") or "").strip()
            if cur_date and peak_day > _dt.date.fromisoformat(cur_date):
                raise ValueError(f"实体 {eid} peak_date {peak_date} 晚于 provenance 当前锚点日 {cur_date}")
```

顶部 import 段（开工 `grep -n '^import\|^from' scripts/report/facts_gate.py` 核）加 `import datetime as _dt`（若已有 datetime import 则复用，不重复）。docstring 中 `peak_overrides` 行（`grep -n 'peak_overrides' scripts/report/facts_gate.py | head -3` 定位 docstring 内那一行）把证据说明改为 `evidence: {path, sha256}，证据 JSON 须为 {entity_id: {peak_raw, peak_date}} 与申报相等`（一行内改）。

### 2.3 `scripts/report/audit_release_gate.py` —— `check_facts_vs_ledgers` 加 decimals 链上一致性

签名 `def check_facts_vs_ledgers(case_dir: Path, facts, errors: list[str], receipt=None):`（F07 落地后 `grep -n -F` 取行号）改为 `..., receipt=None, accounting=None):`；`_run` 中调用处（锚 `            check_facts_vs_ledgers(case_dir, data["facts.json"], errors,` 与下一行 `receipt=data.get("figure2_check_receipt.json"))`）改为再传 `accounting=data.get("accounting_mode.json")`。函数末尾（锚 `        errors.append("facts.provenance（inputs/state_source/peak_overrides 的 sha 或绑定）与当前案内实物不一致——输入已变，须重新 build")` 之后）追加：

```python
    # F05（7.2.1）：token.decimals 绑定链上观测——Solana 取 accounting_mode.checks.decimals
    # （accounting_gate_sol 写出），EVM 取 balance 对账收据绑定的 verify_recon config.decimals
    # （深验 witness 已缓存，不重跑）；取不到即拒，不让调用者自报数量单位。
    declared = (facts.get("token") or {}).get("decimals")
    chain = str((accounting or {}).get("chain") or "")
    observed = None
    try:
        if chain == "sol":
            observed = ((accounting or {}).get("checks") or {}).get("decimals")
        elif chain:
            import shared_release_receipt
            witness = _validate_reconciliation_report_once(case_dir)
            bal = (witness.receipts or {}).get("balance") or {}
            _, cfg = shared_release_receipt._bound_json_input(case_dir, bal, "config", "verify_recon config")
            observed = cfg.get("decimals")
    except Exception as exc:
        errors.append(f"facts.token.decimals 无法取链上观测值: {exc}")
        return
    if isinstance(observed, bool) or not isinstance(observed, int):
        errors.append("facts.token.decimals 无链上观测来源可核（accounting_mode/对账收据缺 decimals）")
    elif declared != observed:
        errors.append(f"facts.token.decimals={declared!r} 与链上观测 {observed} 不一致——state_source.facts_inputs.decimals 填错")
```

说明：①`_validate_reconciliation_report_once`（`:111-118`）返回 `DeepReconciliationWitness`，其 `receipts` 是 `validate_reconciliation_report(return_receipts=True)` 的 dict——**receipts 的键名（是否为 `"balance"`）由施工前 `grep -n 'return_receipts' scripts/report/shared_release_receipt.py` 核实**，不符按实况改并写进 done；②EVM 夹具 `test_audit_release_gate.build_case` 的 `fixture_recon_config.json` decimals=0 与 `build_facts_from_ledgers` 默认 decimals=0 一致，既有 new-analysis 夹具应仍绿；③witness 已被 `_run` 其他检查消费一次，本处只读其 `receipts`，不调 `_consume_reconciliation_witness`；④Solana `accounting_mode.json` 的 `checks.decimals` 由 `accounting_gate_sol.py:226` 写出，施工前用 `test_repair_batch_d.py` 的 `build_solana_case` 夹具核实其 accounting_mode 含该键（缺则该夹具补 `checks.decimals`，若夹具文件不在白名单则停工汇报）。

### 2.4 测试

- `scripts/tests/test_audit_release_gate.py` `build_facts_from_ledgers`（`:202-224`）：证据文件改为 `{eid: {"peak_raw": <confirmed>, "peak_date": peak_date}}`（全部实体一份文件 `peak_evidence.json`），其余不变。
- `scripts/tests/test_report_facts.py` `_r07_build_cases`（`:77-293`）追加用例（沿用其 `run(name, fn)` 模式；夹具 `_r07_case` 提供 provenance 锚 current `stock_raw 100`、peak `150/2026-01-02`，无 current.date；用例需要 override 时写 `peak_overrides` 与证据文件）：
  16 `F05 证据内容与申报不一致拒`：证据 `{"e1": {"peak_raw": "100", "peak_date": "2026-01-01"}}`，申报 peak 1000000/1900-01-01 → ValueError 含"证据内容与申报"。**RED**。
  17 `F05 证据一致放行（GREEN）`：证据与申报同为 150/2026-01-02 → build 成功且 facts.entities.e1.peak_raw=="150"。
  18 `F05 peak 超总供应拒`：override 一致但 peak 2000（total 1000）→ ValueError 含"超过总供应"。**RED**。
  19 `F05 peak_date 非法拒`：provenance 锚 date 改 `"1900-1-1x"` → ValueError 含"非 YYYY-MM-DD"。**RED**。
  20 `F05 peak_date 晚于当前锚点日拒`：provenance current 锚加 `"date": "2026-01-01"`，peak date `2026-01-02` → ValueError 含"晚于"。**RED**。
  21 `F05 证据非对象拒`：证据文件 `[1,2]` → ValueError 含"证据内容"。**RED**。
  `print` 行 `:293` 的 `15 类` 改 `21 类`。
- `scripts/tests/test_audit_release_gate.py` 新增 decimals 用例（放在 R09 段之后、`:1156` 6.9.2 反例之前，独立 `with tempfile.TemporaryDirectory()` 块，用 `build_case(root, historical=False)`＋`build_facts_from_ledgers(root, decimals=2)`；夹具 recon config decimals=0）：
  a `F05 decimals 与链上观测不符拒`：`gate.run(root, report, profile="new-analysis")` errors 含"与链上观测 0 不一致"。**RED**（基线 `[]`——先核实 build_case 是否满足 new-analysis 全部 required；若 build_case 只满足 independent-audit，改用 `test_stage2_closeout.build_release_case` 夹具并把该用例放进 `test_stage2_closeout.py`——**该文件不在白名单，遇此情形停工汇报**）。
  b `F05 decimals 一致放行（GREEN→GREEN）`：`decimals=0` → 无"decimals"字样错误。

RED 证据：改生产代码前逐例跑 16/18/19/20/21/a 记异常原文（含命令与被测文件 sha256）。

## 3. 完成报告 `F05_done.md` 必含

①0.1 三条命令输出；②2.1–2.4 `git diff` 原文；③RED 摘要；④0.8 各测试结果尾行；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点（含 witness receipts 键名核实结果、Solana 夹具 checks.decimals 核实结果、`check_facts_vs_ledgers` 实际行号）；⑧禁读披露。stdout 首行 `# 施工 F05：完成` 或 `# 施工 F05：停工`。

## 4. 登记不修（`code_change_pending.md`，调度方维护）

- **待用户裁决**：峰值上界用当前总供应一刀切——历史供应更大（大额销毁后）的币，真实历史峰值可能超过当前总供应而被误拒；正解是按 peak_date 时点供应核上界，需要供应历史序列（另单）。
- override 证据只核"值一致"，不复算峰值本身（块级峰值复算属 A4 重放，另单）。
- peak_date 无下界（代币首笔转账日无稳定来源）。
- `decimals` 在 `derive_facts`/stage2 收口不核（只在发布闸核）：发布必经，够用。
