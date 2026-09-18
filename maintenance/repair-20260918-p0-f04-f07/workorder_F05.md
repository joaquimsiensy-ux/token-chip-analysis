# 工单 F05（v2，融合 codex 复核 r1 八条 F05-R1-01..08）：facts 小数位绑定链上观测＋峰值 override 证据类型化＋峰值上界 —— repair-20260918-p0-f04-f07 第四段

> 出处：codex 对 7.2.0（311e6c4）的六视角 review F05（P0，**半修复 R07**）：`facts_gate.derive_facts` 证明了 current/addresses/total 来自三账，却让调用者在 `state_source.facts_inputs` 里自由决定 `decimals`（`:358-363` 只验 ≥0 整数）与 `peak_overrides`（`:404-420` 只验证据文件 path/sha 在场，不看证据内容）；`gate_check`（`:191-203`）只验 peak≥current 与 Σcurrent≤total。反例：review 附录 D `repro_core.py` F05（decimals 0→2、证据 `{"note":"fixture"}`、申报 peak=1,000,000/1900-01-01，facts consumer `[]`，宏渲染 `1.00枚 1000000.00% 1900-01-01`）与 `repro_preseal.py`（同输入放在 A4 前，真实 facts→A4→A5→HTML rc=0，HTML 含错误峰值与日期）。R07 本身就是 APU 案 facts_inputs 小数位真实事故的修复。用户 2026-09-18 裁决：修。总原则：**skill 上下文不增**；能删不增、能改不增；不新立 schema。
> v2 变更（`review_F05_reply_r1.md`，八条全采纳）：R1-01 decimals 检查改为独立函数 `check_facts_decimals` 只挂 `_run` 的 new-analysis 分支，共享 `check_facts_vs_ledgers` 一字不动（stage2_closeout:578 与 test_report_facts:206 直接调用它）；R1-02 链名经 `shared_release_receipt.chain_family` 归一（真实 Solana 链名为 `"solana"`）；R1-03 白名单加 `test_repair_batch_d.py`（仅 `:984` 补 `"decimals": 0`）；R1-04 `test_report_facts.py:153` 既有 override 用例证据迁移为新格式，§1.4 补完整迁移链；R1-05 decimals a/b 用例改放 `test_review_20260804_p105.py`（`add_new_analysis_distribution` 加 `decimals` 参数），白名单加该文件；R1-06 日期严格 `YYYY-MM-DD`（`isoformat()` 回写相等）并补 `20260102` 负例；R1-07 裁决点改为"真实峰值超过当前总供应的案被保守阻断"，施工按此落地；R1-08 docstring 范围订正 `:2-71` 只改 `:65`，import 区 `:72-78` 允许加 `datetime`。
> 内容基线：`311e6c4` 加本工程前段（F06/F04/F07）落地 commit；`facts_gate.py`、`test_report_facts.py` 与 311e6c4 逐字节相同；`audit_release_gate.py` 经 F04（`:1571` 起插入约 14 行）与 F07（`:1077-1113` 与 `:1191` 后插入）漂移，**本工单对该文件的锚点（`check_facts_vs_ledgers` `:1497-1548` 及 `_run` 调用处 `:1831`）按 F07 落地后的 HEAD 重新 `grep -n -F` 实证后填入 v2**；`test_audit_release_gate.py` 经 F07 段改动（`_r09_followup`、r09_cases），本工单只在 `build_facts_from_ledgers`（`:202-224`）与新增用例处动。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `F05_done.md`：`git status --short`（须为空）；`git rev-parse --short HEAD`（须与 `construct_F05_prompt.md` 首行一致）；`git diff --stat 311e6c4 HEAD -- scripts/report/facts_gate.py scripts/tests/test_report_facts.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不符即停工写 `F05_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
- 0.3 **白名单**：生产 `scripts/report/facts_gate.py`、`scripts/report/audit_release_gate.py`；测试 `scripts/tests/test_report_facts.py`、`scripts/tests/test_audit_release_gate.py`（仅 `build_facts_from_ledgers` 证据格式）、`scripts/tests/test_repair_batch_d.py`（仅 `:984` 一行补 `"decimals": 0`）、`scripts/tests/test_review_20260804_p105.py`（仅 `add_new_analysis_distribution` 加 `decimals=0` 参数、`:214` 传参、文末新增 a/b 用例）；登记 `scripts/tests/invariant_manifest.json`（只按 `invariant_scan.py` 报出的缺项增补）；本目录新建 `F05_done.md`、`F05_red_evidence.txt`，停工时 `F05_done_attempt1_stopped.md`。
- 0.4 **不改**：`facts_gate.py` 的宏语法/渲染（`:97-186`）、模块 docstring（`:2-71`，仅允许 `:65` 一行按 §2.2 改证据格式描述）、`_load_case_json`/`_raw_str`/`build_main`；import 区 `:72-78` 只允许新增 `import datetime as _dt` 一行；`audit_release_gate.py` 的 `check_facts_vs_ledgers` **一字不动**，只允许在其后新增 `check_facts_decimals` 与 `_run` 内一行调用，其余（含 F04/F07 已落地段）不动；`stage2_closeout.py`、`shared_release_receipt.py`、`entity_identity_gate.py`、`identity_snapshot_receipt.py`、`accounting_gate*.py`；`FACTS_PROVENANCE_SCHEMA`（不升版）；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`contract_manifest.json`；其他测试只跑不改。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.4 新用例改动前逐例取 RED 写 `F05_red_evidence.txt`。
- 0.8 不跑 `run_all.py`。定向跑：`python3 -B scripts/tests/test_report_facts.py`、`test_audit_release_gate.py`、`test_state_from_facts.py`、`test_a4_gate.py`、`test_repair_batch_d.py`、`test_review_20260804_p105.py`、`test_stage2_closeout.py`、`test_figures_from_facts.py`、`python3 -B scripts/tests/invariant_scan.py`。全部须 PASS。（F12 环境项 `test_stage2_reseal.py::dry_run_touches_nothing` 与 reseal 全套由调度方全套验收处理，reseal 复用 closeout 正例，本段共享函数不动即不受影响。）

## 1. 硬约束

- 1.1 文档三处字节不变：SKILL.md 8021、references 930061、commands-staging 8798（命令同工单 F06 §1.1）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 `derive_facts` 保持纯函数（只读案内文件、不写盘、不带时间戳、不读时钟）；decimals 的链上一致性放在**发布闸 new-analysis 分支的独立函数**，不进 `derive_facts` 也不进共享 `check_facts_vs_ledgers`（stage2 收口与 reseal 复用后者，必须零行为变化）。
- 1.4 存量迁移代价（明示）：R07 起用 `peak_overrides` 的案（APU 0801 待重发布案）证据文件须改为 §2.2 格式，随后整条链重做：`facts_gate.py build` 重出 facts → `figures_from_facts.py check` 重出图 2 收据（闸复核 facts 哈希）→ stage2 收口收据/A4/A5 按各自绑定重封；`facts.token.decimals` 与链上观测不符的案在发布闸被拒——这正是目标行为。

## 2. 逐条施工

### 2.1 `scripts/report/facts_gate.py` —— `gate_check` 加峰值供给上界（G2 同族）

`:198-199`（锚 `        if cur > peak:` / `            errors.append(f"G3 {eid} current_raw > peak_raw（{cur} > {peak}）")`）之后追加：

```python
        if facts.total_raw and peak > facts.total_raw:
            errors.append(f"G2 {eid} peak_raw {peak} 超过总供应 {facts.total_raw}")
```

覆盖所有 facts 来源（override、provenance 锚、exploration）。准确的误拒条件＝**真实 peak_raw 超过当前采用的 `total_supply_raw`**（历史供应更大不必然触发；例如真实峰值 150、当前供应 100 才被拒）。本段按该保守规则落地，§4 P8 登记为用户可撤销的裁决点。

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
            if peak_day.isoformat() != peak_date:
                raise ValueError(f"实体 {eid} peak_date {peak_date!r} 非 YYYY-MM-DD（fromisoformat 接受 20260102/周格式，此处严格）")
            cur_date = str((((ledger_entities.get(eid) or {}).get("anchors") or {})
                            .get("current") or {}).get("date") or "").strip()
            if cur_date and peak_day > _dt.date.fromisoformat(cur_date):
                raise ValueError(f"实体 {eid} peak_date {peak_date} 晚于 provenance 当前锚点日 {cur_date}")
```

import 区 `:72-78`（锚 `import argparse` … `from pathlib import Path`，无 datetime）在 `import argparse` 之后加 `import datetime as _dt`。docstring `:65`（锚 `  peak_overrides: {eid: {peak_raw, peak_date, evidence: {path, sha256, note?}}}`，唯一）把证据说明改为 `evidence: {path, sha256}，证据 JSON 须为 {entity_id: {peak_raw, peak_date}} 与申报相等`（一行内改）。

### 2.3 `scripts/report/audit_release_gate.py` —— new-analysis 分支新增 `check_facts_decimals`（共享 `check_facts_vs_ledgers` 不动）

在 `check_facts_vs_ledgers` 函数体结束后（其末行锚 `        errors.append("facts.provenance（inputs/state_source/peak_overrides 的 sha 或绑定）与当前案内实物不一致——输入已变，须重新 build")`，唯一；F07 落地后行号漂移，施工前 `grep -n -F` 取行号）新增：

```python
def check_facts_decimals(case_dir: Path, facts, accounting, errors: list[str]):
    """F05（7.2.1）：token.decimals 绑定链上观测——solana 家族取 accounting_mode.checks.decimals
    （accounting_gate_sol 写出），evm 家族取 balance 对账收据绑定的 verify_recon config.decimals
    （深验 witness 已缓存，不重跑）；取不到即拒，不让调用者自报数量单位。只挂 new-analysis，
    不进共享 check_facts_vs_ledgers（stage2 收口/reseal 复用后者）。"""
    declared = ((facts or {}).get("token") or {}).get("decimals")
    chain = str((accounting or {}).get("chain") or "")
    observed = None
    try:
        import shared_release_receipt
        family = shared_release_receipt.chain_family(chain)
        if family == "solana":
            observed = ((accounting or {}).get("checks") or {}).get("decimals")
        else:
            witness = _validate_reconciliation_report_once(case_dir)
            bal = (witness.receipts or {}).get("balance") or {}
            _, cfg = shared_release_receipt._bound_json_input(case_dir, bal, "config", "verify_recon config")
            observed = cfg.get("decimals")
    except Exception as exc:
        errors.append(f"facts.token.decimals 无法取链上观测值: {exc}")
        return
    if isinstance(observed, bool) or not isinstance(observed, int):
        errors.append("facts.token.decimals 无链上观测来源可核（accounting_mode.checks/对账收据 config 缺 decimals）")
    elif declared != observed:
        errors.append(f"facts.token.decimals={declared!r} 与链上观测 {observed} 不一致——state_source.facts_inputs.decimals 填错")
```

`_run` 中（锚两行 `            check_facts_vs_ledgers(case_dir, data["facts.json"], errors,` / `                                   receipt=data.get("figure2_check_receipt.json"))`，唯一）在该调用之后、同一 `if profile == "new-analysis" and "facts.json" in data:` 块内追加一行 `            check_facts_decimals(case_dir, data["facts.json"], data.get("accounting_mode.json"), errors)`。

说明：①`chain_family`（`shared_release_receipt.py:138-142`）经 `recon_adapter_for` 归一化，真实 Solana 链名为 `"solana"`（`accounting_gate_sol.py:137`、夹具 `test_repair_batch_d.py:976`），**不得直接比较 `"sol"`**；未登记链抛 ValueError → 进 errors；②witness `receipts` 键 `"balance"` 已由复核 r1 核实（`shared_release_receipt.py:71/1445/1508`），对象即含 `inputs.config` 的 verify_recon 收据，`_bound_json_input`（`:559-567`）可直接用（`:593` 同款调用）；③`_validate_reconciliation_report_once`（`:111-118`）在 `_run` 更早处（`:1792` 对账检查）已调用并缓存，异常会重抛 → 本函数 except 转 errors，不重跑深验；④EVM 夹具 `fixture_recon_config.json` decimals=0 与 `build_facts_from_ledgers` 默认 0 一致；Solana 夹具 `test_repair_batch_d.py:984` 缺 `checks.decimals`，§2.4 补 0（与观测夹具 `:893` 一致）。

### 2.4 测试

- `scripts/tests/test_audit_release_gate.py` `build_facts_from_ledgers`（`:202-224`）：证据文件改为 `{eid: {"peak_raw": <confirmed>, "peak_date": peak_date}}`（全部实体一份文件 `peak_evidence.json`），其余不变。
- `scripts/tests/test_report_facts.py:153`（锚 `        evidence = _r07_write(root, "peak_evidence.json", {"note": "observed peak"})`，唯一）：既有合法 override 用例证据迁移为 `{"e1": {"peak_raw": "160", "peak_date": "2026-01-03"}}`；其合法/坏哈希/缺证据三种断言保留。
- `scripts/tests/test_report_facts.py` `_r07_build_cases`（`:77-293`）追加用例（沿用其 `run(name, fn)` 模式；夹具 `_r07_case` 提供 provenance 锚 current `stock_raw 100`、peak `150/2026-01-02`，无 current.date）：
  16 `F05 证据内容与申报不一致拒`：证据 `{"e1": {"peak_raw": "100", "peak_date": "2026-01-01"}}`，申报 peak 1000000/1900-01-01 → ValueError 含"证据内容与申报"。**RED**。
  17 `F05 证据一致放行（GREEN）`：证据与申报同为 150/2026-01-02 → build 成功且 `facts.entities.e1.peak_raw == "150"`。
  18 `F05 peak 超总供应拒`：override 一致但 peak 2000（total 1000）→ ValueError 含"超过总供应"。**RED**。
  19 `F05 peak_date 非法拒`：provenance 锚 date 改 `"1900-1-1x"` → 含"非 YYYY-MM-DD"；再改 `"20260102"`（fromisoformat 可解析但非严格格式）→ 含"非 YYYY-MM-DD"。**RED**（两例）。
  20 `F05 peak_date 晚于当前锚点日拒`：provenance current 锚加 `"date": "2026-01-01"`，peak date `2026-01-02` → 含"晚于"。**RED**（条件分支：真实 `entity_source_trace.py:639` current 锚不写 date，此上界只在显式提供时生效，§4 登记）。
  21 `F05 证据非对象拒`：证据文件 `[1,2]` → 含"证据内容"（数组短路，不进 `_raw_str`）。**RED**。
  `print` 行 `:293` 的 `15 类` 改 `21 类`。
- `scripts/tests/test_repair_batch_d.py:984`（锚 `        "checks": {"fot": {"status": "clean"}}})`，唯一）改为 `        "checks": {"fot": {"status": "clean"}, "decimals": 0}})`。
- `scripts/tests/test_review_20260804_p105.py`：`add_new_analysis_distribution(root: Path, report: Path)`（`:141`）加参数 `decimals=0`；`:214`（锚 `    fixture.build_facts_from_ledgers(root, symbol="FX")`，唯一）改为 `    fixture.build_facts_from_ledgers(root, symbol="FX", decimals=decimals)`。文末（`:261` 已有 new-analysis 零错误断言之后、`main` 收尾之前，开工 `nl -ba` 定位）追加两个独立 tempdir 用例：
  a `F05 decimals 与链上观测不符拒`：`build_case(root)` → `add_new_analysis_distribution(root, report, decimals=2)` → `gate.run(root, report, profile="new-analysis")` errors 含"与链上观测 0 不一致"。**RED**（基线 `[]`——先用同一夹具证明基线两案均 `errors == []`，写进证据）。
  b `F05 decimals 一致放行（GREEN→GREEN）`：`decimals=0` → `errors == []`。

RED 证据：改生产代码前逐例跑 16/18/19/20/21/a 记异常原文（含命令与被测文件 sha256），a/b 基线 `[]` 一并记。

## 3. 完成报告 `F05_done.md` 必含

①0.1 三条命令输出；②2.1–2.4 `git diff` 原文；③RED 摘要；④0.8 各测试结果尾行；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点（含 `check_facts_vs_ledgers` 末行与 `_run` 调用块实际行号、p105 用例实际落点行号）；⑧禁读披露。stdout 首行 `# 施工 F05：完成` 或 `# 施工 F05：停工`。

## 4. 登记不修（`code_change_pending.md`，调度方维护）

- **P8 用户可撤销的裁决点**：G2 峰值上界＝当前 `total_supply_raw`，真实历史峰值超过当前总供应的案（如大额销毁后）会被保守阻断；施工按此落地。正解是按 peak_date 时点供应核上界，需要供应历史序列（另单）。普通转入销毁地址不等同于 totalSupply 下降。
- 真实 provenance 产物 current 锚不带 date（`entity_source_trace.py:639`），peak_date 上界只在显式提供时生效；provenance peak 锚 date 来自 `wave_scan.py:87-88` 的 `%Y-%m-%d`，严格格式不会误拒真实产物。
- override 证据只核"值一致"，不复算峰值本身（块级峰值复算属 A4 重放，另单）。
- peak_date 无下界（代币首笔转账日无稳定来源）。
- `decimals` 在 `derive_facts`/stage2 收口不核（只在发布闸核）：发布必经，够用。
