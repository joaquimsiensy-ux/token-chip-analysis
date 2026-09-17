# 工单 C（v5）：R07 facts.json 由三账自动生成＋发布闸/收口重算 —— repair-20260917-p0-four 第三段

> 出处：codex 对 7.0.4 的 review（`REVIEW.md` R07，P0）——facts.json（报告宏的唯一数字源）与三账之间没有任何数值等式，手抄/手改 facts 不会被任何闸拦。用户 2026-09-17 裁决：**facts 由三账自动生成**；峰值取 `provenance_ledger.json` 的实体峰值锚点、允许显式 override（须带证据）；人工字段（label/symbol/decimals/metrics 等）**复用 `state_source.json`**，不新建文件；总原则"能不新增不新增、skill 上下文不增"。
> 内容基线：本段白名单源码文件与 commit `8ead156`（A/B 落地）逐字节相同；开工 HEAD 以 `construct_C_prompt.md` 首行标注为准（工单/提示词提交会推进 HEAD，源码不变）。行号均指施工前基线。
> v2 变更（对 codex r1 八条，见 `review_C_reply_r1.md`）：C-R02/C-R04 → **撤销"在场即验"与 P11**，facts.json 加进 `NEW_ANALYSIS_REQUIRED`（复核实证：真正要求 new-analysis 闸零错误的夹具——batch_d `build_solana_case`（batch15/batch18_shared_bundle_witness/batch18_review_digest 复用；batch13 用 test_r9_batch3 的 build_case、recon_fifth 自建夹具，r3 校准）、P105（batch B 复用）、stage2/reseal——都带 facts，只是手写；一律改为共享助手 `build_facts_from_ledgers` 从三账 build）；C-R01 → stage2 build 放在 `add_camp_series` 之后、A4 finalize 之前；C-R03 → derive 先验三账非空；C-R05 → provenance_ledger 前移进 `build_release_case`，reseal prereq 幂等；C-R06 → batch_d 反例独立 with 块；C-R07 → docs_lint 移出施工方清单（调度方 pre-commit 跑）；C-R08 → HEAD 表述改为随施工提示词。另补：figure2 收据绑定的 facts 必须是本名 `facts.json`（复核指出另名 facts 可让图 2 对账绕开三账重算）。
> v3 变更（对 codex r2 五条，见 `review_C_reply_r2.md`）：C-R04-r2 → 新增 C4-e：`test_a4_gate.py` 的 `case_new`（唯一走 `build_html --mode analysis-new` 的夹具）改用共享助手 build；C-R05-r2 → reseal 的 overlay 白名单是 W3 专用**不改**，等价验收路径＝调度方 commit 后把 `/tmp/w3_acceptance` worktree 同步到新 HEAD、树干净、overlay 为空再跑（§0.8/§4）；C-R09 → C3 说明移出代码块、§0.4 计数改 11、C4-b 反例改为独立函数 `t_r07_facts_vs_ledgers` 并登记到 `main()`；C-R10 → `derive_facts` 末尾用既有 `gate_check(Facts(facts))` 自检（G2/G3 等）不过即拒（build 出的 facts 必须过既有 facts gate，fail-closed），P105 的 identity 用真实 owner 快照建绑定（`identity_gate_fixture.augment_gate` 加 `balances` 关键字参数，C4-c′）；C-R11 → C1 输入 JSON 严格解析：`parse_constant` 拒 NaN/Infinity 字面量、`parse_float` 拒溢出成 inf 的 `1e999`（§1.5，C4-d 用例 13/14）。
> v4 变更（盲审 r1 唯一 minor C-01，见 `blind_C_reply_r1.md`）：追加 **C7**——`derive_facts` 落实 `facts_inputs` 的类型约定（symbol 必为非空字符串、metrics 必为对象且每项为对象、dual_basis 若给必为对象），非法即带字段名的 ValueError；补用例 15。C1–C6 已落地于 1b317b3，v4 只施工 C7；行号指 1b317b3 基线。
> v5 变更（C7 复核 r1 唯一 minor C7-R01，见 `review_C7_reply_r1.md`）：dual_basis 校验改为按键在场判断（显式 `null` 也拒），用例 15 加 `None` 变体。
> 设计要点：①`state_source.json` 只新增**一个**顶层块 `facts_inputs`（`state_from_facts.compile_state` :95-142 按键取值、不展开 source，新块不会漏进 analysis-state.json）。②文档只改 `references/report-template.md:212` 一处（−5 B）；`analyze-workflow.md:147` 不改。③夹具 facts 的峰值一律走 override（夹具无 provenance 锚点）＝confirmed 值，证据文件 `peak_evidence.json` 随案。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `C_done.md`：`git status --short`（须为空）；`git rev-parse --short HEAD`（须与 `construct_C_prompt.md` 首行标注一致）。不符即停工写 `C_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 在 done 里披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`；**禁读** `/Users/uravvv/Desktop` 下任何文件（沙箱也读不到；存量案对照由调度方本机跑）。
- 0.3 **白名单**：生产 `scripts/report/facts_gate.py`、`scripts/report/audit_release_gate.py`、`scripts/report/stage2_closeout.py`；测试 `scripts/tests/test_report_facts.py`、`scripts/tests/test_stage2_closeout.py`、`scripts/tests/test_stage2_reseal.py`、`scripts/tests/test_repair_batch_d.py`、`scripts/tests/test_review_20260804_p105.py`、`scripts/tests/test_a4_gate.py`（只改 import 与 `case_new` 一处，C4-e）、`scripts/tests/identity_gate_fixture.py`（只给 `augment_gate` 加 `balances=None` 关键字参数，C4-c′）、`scripts/tests/test_audit_release_gate.py`（只加共享助手 `build_facts_from_ledgers`，不动既有用例）；登记 `scripts/tests/invariant_manifest.json`（只按 invariant_scan 报出的缺项增补，见 C5）；文档 `references/report-template.md`（只改 :212 一处）；本目录新建 `C_done.md`、`C_red_evidence.txt`，停工时 `C_done_attempt1_stopped.md`。
- 0.4 **不改**：`facts_gate.py` 现有 `Facts`/`gate_check`/`load_and_check` 与 `main()` 的 argparse 行为（只在 main 顶部加 `build` 分派）；`audit_release_gate.py` 的 `check_figure2_receipt`（:1368-1390）、`check_three_ledgers`；`stage2_closeout.py` 现有 11 个 record 的名称与顺序；`state_from_facts.py`（不在白名单）；`analyze-workflow.md`、`SKILL.md`、`commands-staging/`、VERSION、pyproject、CHANGELOG、contract_manifest。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：C4 新用例改动前先跑取 RED 写 `C_red_evidence.txt`（逐例独立、逐例捕获 AssertionError，写法照 A/B 段），改后取 GREEN。
- 0.8 本段只跑：`python3 -B scripts/tests/test_report_facts.py`、`test_stage2_closeout.py`、`test_repair_batch_d.py`、`test_review_20260804_p105.py`、`test_repair_batch_b.py`、`test_audit_release_gate.py`、`test_batch15_three_ledgers_frozen.py`、`test_batch18_shared_bundle_witness.py`、`test_batch13_accounting_target.py`、`test_recon_fifth_check.py`、`test_state_from_facts.py`、`test_figures_from_facts.py`、`test_a4_gate.py`、`python3 -B scripts/tests/invariant_scan.py`。`test_stage2_reseal.py` **施工方不跑**：它从当前仓库运行时会把未提交改动 overlay 到 `/tmp/w3_acceptance` 且只认 W3 白名单（`:614-621`，本段不改），由调度方 commit 后同步 worktree 到新 HEAD、overlay 为空再跑（§4）。docs_lint 由调度方在 pre-commit 跑（其扫描面含禁读目录，施工方不跑）。不跑 run_all。

## 1. 硬约束

- 1.1 文档字节：SKILL.md 8021 不变、commands-staging 8798 不变、references **930065**（930070 − 5；命令同工单 A §1.1，只用 stat 不读内容）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 `facts_gate.py build` 输出确定性：同输入两次 build 逐字节相同（不写时间戳）。
- 1.5 输入 JSON 严格解析：`_load_case_json` 用 `parse_constant` 拒 `NaN/Infinity/-Infinity` 字面量、`parse_float` 拒解析后非有限的数（`1e999`→inf 不经 parse_constant，须在 parse_float 拦），任一命中即 ValueError；facts 的全部值都来自这些输入，故产物不可能含非有限值。发布闸侧装载 facts.json 的既有 `load_json` 仍只拒字面量（P7 既有漏口），但 C2 逐键比对会把 facts 里的 `1e999` 与重算值判不一致，闭合本段。
- 1.4 三账缺件/空账/不闭合的案不得生成 facts：derive 先验三个账本各含非空 `entries|entities` 列表（`check_three_ledgers` 对空账直接 return，:790），再跑 `check_three_ledgers(chain=None)`，任一有错即 exit 2。

## 2. 逐条施工

### C1 `scripts/report/facts_gate.py`：新增 `build` 子命令与纯函数 `derive_facts`

- `:8`（锚 `facts.json schema（每案一份，阶段 3 结束时从落盘数据构建；数值一律**原始整数字符串**）：`）改为 `facts.json schema（每案一份，阶段 3 结束时由 build 子命令从三账生成，禁手抄；数值一律**原始整数字符串**）：`；并在 docstring 末尾"用法"段（`:59` 锚 `  python3 facts_gate.py --facts facts.json --state analysis-state.json   # 纯校验` 之后）追加两行：
  `  python3 facts_gate.py build [--case-dir .] [--source state_source.json] [--out facts.json] [--exploration]`
  `      # 从三账＋identity_gate＋provenance_ledger＋state_source.facts_inputs 生成 facts.json（7.2.0，R07）`
  再追加 `state_source.facts_inputs` 块的 schema 说明（≤12 行）：`symbol`(str 必)、`decimals`(int≥0 必)、`entity_labels{eid:label}`(必，覆盖全部实体，非空)、`peak_overrides{eid:{peak_raw,peak_date,evidence{path,sha256,note?}}}`(可选，优先于 provenance 锚点)、`merge_evidence{eid:{earliest,note}}`(可选)、`role_notes{eid:{addr:note}}`(可选)、`metrics{}`(可选透传)、`dual_basis{}`(可选透传)；**不得**含 `provenance`/`facts_binding` 键（预置绑定即拒，镜像 `state_from_facts.py:211-215`）。
- `:61`（锚 `import argparse`）之后按字母序补 `import hashlib`、`import os`；`:64`（锚 `import sys`）之后补 `from pathlib import Path`。
- 在 `:250`（锚 `def load_and_check(facts_path, state_path=None, md_text=None):`）之前插入：

```python
FACTS_PROVENANCE_SCHEMA = "facts-provenance/v1"
STATE_SOURCE_SCHEMA = "analysis-state-source/v1"
FACTS_INPUTS_KEY = "facts_inputs"
FACTS_LEDGER_INPUTS = ("membership_ledger.json", "position_ledger.json",
                       "economic_control_ledger.json", "identity_gate.json")


def _sha256_path(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_addr(value):
    v = str(value or "").strip()
    return v.lower() if v.lower().startswith("0x") else v


def _case_file(case_dir, rel, label):
    """案内常规文件：basename 相对案根、非符号链接、必须在场；否则 ValueError。"""
    name = Path(str(rel or "")).name
    if not name or name != str(rel):
        raise ValueError(f"{label} 路径必须是案根内 basename: {rel!r}")
    p = Path(case_dir) / name
    if p.is_symlink() or not p.is_file():
        raise ValueError(f"{label} 不在案根或是符号链接: {name}")
    return p


def _reject_constant(value):
    raise ValueError(f"JSON 含非有限常量 {value}（NaN/Infinity 不允许）")


def _finite_float(text):
    v = float(text)
    if v != v or v in (float("inf"), float("-inf")):
        raise ValueError(f"JSON 浮点非有限: {text}")
    return v


def _load_case_json(case_dir, rel, label):
    with open(_case_file(case_dir, rel, label), encoding="utf-8") as fh:
        try:
            return json.load(fh, parse_constant=_reject_constant, parse_float=_finite_float)
        except ValueError as exc:
            raise ValueError(f"{label} 解析失败: {exc}") from exc


def _raw_str(value, label):
    n = _int(value)
    if n < 0:
        raise ValueError(f"{label} 不得为负: {value!r}")
    return str(n)


def derive_facts(case_dir, *, exploration=False):
    """R07（7.2.0）：从三账＋identity_gate＋（可选）provenance_ledger＋state_source.facts_inputs
    重算 facts.json。纯函数：只读案内文件，不写盘，不带时间戳；build 与发布闸/收口共用，
    闸用它重算后与落盘 facts 逐字段比对。任何缺件/不闭合/证据不符一律 ValueError（fail-closed）。"""
    case_dir = Path(case_dir)
    data = {n: _load_case_json(case_dir, n, n) for n in FACTS_LEDGER_INPUTS[:3]}
    for name, obj in data.items():
        rows = obj.get("entries", obj.get("entities")) if isinstance(obj, dict) else None
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{name} 缺 entries/entities 或为空——空账不得生成 facts")
    import audit_release_gate  # 同目录；三账闭合复用发布闸同一实现
    errs = []
    audit_release_gate.check_three_ledgers(case_dir, data, errs, chain=None)
    if errs:
        raise ValueError("三账不闭合，拒绝生成 facts: " + "; ".join(errs[:3]))
    identity = _load_case_json(case_dir, "identity_gate.json", "identity_gate.json")
    total_raw = _raw_str(identity.get("total_supply_raw"), "identity_gate.total_supply_raw")
    if int(total_raw) <= 0:
        raise ValueError("identity_gate.total_supply_raw 必须为正")
    ledger_path = case_dir / "provenance_ledger.json"
    ledger = None
    if ledger_path.is_file() and not ledger_path.is_symlink():
        ledger = _load_case_json(case_dir, "provenance_ledger.json", "provenance_ledger.json")
        if not exploration and ledger.get("exploration") is True:
            raise ValueError("provenance_ledger 为探索产物，formal build 拒绝")
        lt = ledger.get("total_supply_raw")
        if lt is not None and _raw_str(lt, "provenance_ledger.total_supply_raw") != total_raw:
            raise ValueError(f"total_supply_raw 冲突: identity_gate {total_raw} != provenance_ledger {lt}")
    source = _load_case_json(case_dir, "state_source.json", "state_source.json")
    if source.get("schema") != STATE_SOURCE_SCHEMA:
        raise ValueError(f"state_source.schema 必须是 {STATE_SOURCE_SCHEMA}")
    fi = source.get(FACTS_INPUTS_KEY)
    if not isinstance(fi, dict):
        raise ValueError(f"state_source 缺 {FACTS_INPUTS_KEY} 对象")
    if "provenance" in fi or "facts_binding" in fi:
        raise ValueError("state_source.facts_inputs 不得预置 provenance/facts_binding——绑定块只能由 build 生成")
    symbol = str(fi.get("symbol") or "").strip()
    decimals = fi.get("decimals")
    if not symbol or isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
        raise ValueError("facts_inputs.symbol/decimals 缺失或非法")
    labels = fi.get("entity_labels")
    if not isinstance(labels, dict) or not labels:
        raise ValueError("facts_inputs.entity_labels 缺失或为空")
    overrides = fi.get("peak_overrides") or {}
    merges = fi.get("merge_evidence") or {}
    roles = fi.get("role_notes") or {}
    if not all(isinstance(x, dict) for x in (overrides, merges, roles)):
        raise ValueError("facts_inputs.peak_overrides/merge_evidence/role_notes 须为对象")

    members = data["membership_ledger.json"]
    members = members.get("entries", members.get("entities", []))
    strict_by_entity = {}
    for row in members:
        if str(row.get("membership", "")).strip() == "strict":
            strict_by_entity.setdefault(str(row.get("entity_id", "")).strip(), set()).add(
                _norm_addr(row.get("address")))
    ledger_entities = {}
    if ledger is not None:
        for item in ledger.get("entities") or []:
            if isinstance(item, dict) and item.get("entity_id"):
                ledger_entities[str(item["entity_id"])] = item

    econ = data["economic_control_ledger.json"]
    econ = econ.get("entries", econ.get("entities", []))
    entities, used_overrides = {}, {}
    for row in econ:
        eid = str(row.get("entity_id", "")).strip()
        label = str(labels.get(eid) or "").strip()
        if not label:
            raise ValueError(f"facts_inputs.entity_labels 缺实体 {eid} 的 label")
        current = _raw_str(row.get("confirmed_economic_control_raw"),
                           f"economic {eid}.confirmed_economic_control_raw")
        ent = {"label": label, "addresses": sorted(strict_by_entity.get(eid, set())),
               "current_raw": current}
        ov = overrides.get(eid)
        if ov is not None:
            if not isinstance(ov, dict):
                raise ValueError(f"peak_overrides.{eid} 须为对象")
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
            used_overrides[eid] = {"peak_raw": peak, "peak_date": peak_date,
                                   "evidence": {"path": ev_path.name,
                                                "sha256": str(ev["sha256"]).lower()}}
        elif eid in ledger_entities:
            anchor = ((ledger_entities[eid].get("anchors") or {}).get("peak") or {})
            peak = _raw_str(anchor.get("stock_raw"), f"provenance_ledger {eid}.anchors.peak.stock_raw")
            peak_date = str(anchor.get("date") or "").strip()
            if not peak_date:
                raise ValueError(f"provenance_ledger {eid}.anchors.peak 缺 date")
        elif exploration:
            peak, peak_date = current, None
        else:
            raise ValueError(f"实体 {eid} 无峰值来源（provenance_ledger 锚点或 peak_overrides）——formal build 拒绝")
        if int(peak) < int(current):
            raise ValueError(f"实体 {eid} peak_raw {peak} < current_raw {current}")
        ent["peak_raw"] = peak
        ent["peak_date"] = peak_date
        m = merges.get(eid)
        if isinstance(m, dict) and m.get("earliest"):
            ent["merge_evidence_earliest"] = str(m["earliest"])
            if m.get("note"):
                ent["merge_evidence_note"] = str(m["note"])
        r = roles.get(eid)
        if isinstance(r, dict) and r:
            ent["role_notes"] = {str(k): str(v) for k, v in r.items()}
        entities[eid] = ent
    unknown = sorted(set(labels) - set(entities))
    if unknown:
        raise ValueError(f"facts_inputs.entity_labels 含三账之外的实体: {unknown[:5]}")
    unknown = sorted(set(overrides) - set(entities))
    if unknown:
        raise ValueError(f"facts_inputs.peak_overrides 含三账之外的实体: {unknown[:5]}")

    inputs = {n: {"sha256": _sha256_path(case_dir / n)} for n in FACTS_LEDGER_INPUTS}
    if ledger is not None:
        inputs["provenance_ledger.json"] = {"sha256": _sha256_path(ledger_path)}
    facts = {"token": {"symbol": symbol, "decimals": decimals, "total_supply_raw": total_raw},
             "entities": entities, "metrics": fi.get("metrics") or {}}
    if isinstance(fi.get("dual_basis"), dict):
        facts["dual_basis"] = fi["dual_basis"]
    facts["provenance"] = {
        "schema": FACTS_PROVENANCE_SCHEMA, "facts_binding": "ledger-derived",
        "mode": "exploration" if exploration else "formal",
        "inputs": inputs,
        "state_source": {"path": "state_source.json",
                         "sha256": _sha256_path(case_dir / "state_source.json")},
        "peak_overrides": used_overrides,
        "producer": {"path": "scripts/report/facts_gate.py",
                     "sha256": _sha256_path(Path(__file__).resolve())},
    }
    # 生成物必须过既有 facts gate（G2 供给上界/G3 内部一致等；无 state/渲染文本时 G1/G5 自然跳过）
    gate_errors, _notes = gate_check(Facts(facts))
    if gate_errors:
        raise ValueError("生成的 facts 未过既有 facts gate: " + "; ".join(gate_errors[:3]))
    return facts


def build_main(argv):
    ap = argparse.ArgumentParser(prog="facts_gate.py build")
    ap.add_argument("--case-dir", default=".")
    ap.add_argument("--source", default="state_source.json",
                    help="人工输入文件（basename，须在案根；读取其 facts_inputs 块）")
    ap.add_argument("--out", default="facts.json")
    ap.add_argument("--exploration", action="store_true",
                    help="允许缺峰值来源（peak=current）；产物 provenance.mode=exploration，发布闸/收口必拒")
    a = ap.parse_args(argv)
    case_dir = Path(a.case_dir)
    if a.source != "state_source.json":
        print("FAIL: --source 只接受案根 state_source.json（人工字段复用该文件，不另立文件）")
        return 2
    try:
        facts = derive_facts(case_dir, exploration=a.exploration)
    except (KeyError, ValueError, OSError, TypeError) as exc:
        print(f"FAIL: facts 生成失败——{exc}")
        return 2
    out = case_dir / Path(a.out).name
    payload = json.dumps(facts, ensure_ascii=False, indent=2) + "\n"
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, out)
    mode = facts["provenance"]["mode"]
    print(f"PASS: facts 生成 {out.name}（mode={mode}，实体 {len(facts['entities'])} 个，"
          f"override {len(facts['provenance']['peak_overrides'])} 个）")
    if mode == "exploration":
        print("[exploration] 产物带非正式标记，new-analysis 发布闸与 stage2 收口必拒")
    return 0


```

- `:259-260`（锚 `def main():` 与其下一行 `    ap = argparse.ArgumentParser()`）之间插入：

```python
    if sys.argv[1:2] == ["build"]:
        return build_main(sys.argv[2:])
```

说明：`_int`（`:73`）、`Facts`（`:93`）、`gate_check`（`:177`）为本文件既有；`gate_check` 定义在 `derive_facts` 之前（插入点 `:250` 在其后），直接引用即可。`derive_facts` 与发布闸互相延迟 import（gate 在检查函数内 `import facts_gate`，本函数内 `import audit_release_gate`），两文件同目录、`stage2_closeout.py:31-33` 已同时 import 两者，无循环导入问题。入口 `--source` 只接受固定名（用户裁决"复用 state_source.json 不新建文件"）。

### C2 `scripts/report/audit_release_gate.py`：facts.json 进 new-analysis 必需件，新增 `check_facts_vs_ledgers`

- `:51`（锚 `    "figure2_check_receipt.json",`，`NEW_ANALYSIS_REQUIRED` 末项）之后插入两行：
  `    # R07（7.2.0）：facts.json 必须由 facts_gate build 从三账生成，发布闸重算比对`
  `    "facts.json",`
- `:1343`（锚 `FIGURE2_DEFAULT_TOL_PP = 0.05`）之后插入一行 `FACTS_PROVENANCE_SCHEMA = "facts-provenance/v1"`。
- `:1368`（锚 `def check_figure2_receipt(case_dir: Path, d: dict, errors: list[str]):`）之前插入：

```python
def check_facts_vs_ledgers(case_dir: Path, facts, errors: list[str], receipt=None):
    """R07（7.2.0）：facts.json 必须是 facts_gate build 从三账生成的产物——
    验 provenance 绑定块（schema/binding/mode=formal），再用 facts_gate.derive_facts 按案内
    三账＋identity_gate＋provenance_ledger＋state_source 重算，与落盘 facts 逐字段比对
    （producer.sha256 只记录不比对；inputs/state_source/evidence 的 sha 由重算侧复核）。
    receipt＝figure2 对账收据（给了就验其 facts 绑定的是本名 facts.json，防另名 facts 绕开）。"""
    if isinstance(receipt, dict):
        bound = Path(str((receipt.get("facts") or {}).get("path") or "")).name
        if bound != "facts.json":
            errors.append(f"figure2 收据绑定的 facts 是 {bound!r}——必须是案根 facts.json（三账重算比对的对象）")
    if not isinstance(facts, dict):
        errors.append("facts.json 顶层必须是对象")
        return
    prov = facts.get("provenance")
    if not isinstance(prov, dict):
        errors.append("facts.json 缺 provenance 绑定块——须由 facts_gate.py build 从三账生成，禁手写")
        return
    if prov.get("schema") != FACTS_PROVENANCE_SCHEMA:
        errors.append(f"facts.provenance.schema 必须是 {FACTS_PROVENANCE_SCHEMA}")
    if prov.get("facts_binding") != "ledger-derived":
        errors.append("facts.provenance.facts_binding 必须是 ledger-derived")
    if prov.get("mode") != "formal":
        errors.append(f"facts.provenance.mode={prov.get('mode')!r}——exploration 构建不得进正式发布")
        return
    try:
        import facts_gate
        rebuilt = facts_gate.derive_facts(case_dir, exploration=False)
    except (KeyError, ValueError, OSError, TypeError) as exc:
        errors.append(f"facts 按三账重算失败: {exc}")
        return
    got, want = dict(facts), dict(rebuilt)
    got_prov, want_prov = dict(got.pop("provenance") or {}), dict(want.pop("provenance") or {})
    got_prov.pop("producer", None)
    want_prov.pop("producer", None)
    for key in sorted(set(got) | set(want)):
        if key == "entities":
            continue
        if got.get(key) != want.get(key):
            errors.append(f"facts.{key} 与三账重算值不一致")
    ge, we = got.get("entities") or {}, want.get("entities") or {}
    if set(ge) != set(we):
        errors.append(f"facts 实体集合与三账不一致: 多 {sorted(set(ge) - set(we))[:3]} "
                      f"少 {sorted(set(we) - set(ge))[:3]}")
    for eid in sorted(set(ge) & set(we)):
        if ge[eid] != we[eid]:
            diff = sorted(k for k in set(ge[eid]) | set(we[eid]) if ge[eid].get(k) != we[eid].get(k))
            errors.append(f"facts 实体 {eid} 字段 {diff[:4]} 与三账重算值不一致")
    if got_prov != want_prov:
        errors.append("facts.provenance（inputs/state_source/peak_overrides 的 sha 或绑定）与当前案内实物不一致——输入已变，须重新 build")


```

- `:1644-1645`（锚 `        if profile == "new-analysis" and "figure2_check_receipt.json" in data:` 与下一行 `            check_figure2_receipt(case_dir, data["figure2_check_receipt.json"], errors)`）之后插入：

```python
        # R07（7.2.0）：facts.json（new-analysis 必需件，已随 required 装载）按三账重算复核
        if profile == "new-analysis" and "facts.json" in data:
            check_facts_vs_ledgers(case_dir, data["facts.json"], errors,
                                   receipt=data.get("figure2_check_receipt.json"))
```

facts.json 进 `NEW_ANALYSIS_REQUIRED` 后由 `_run` 的 required 循环（:1589-1596）用 `load_json`（严格非有限策略）装载；缺件由既有"缺必需资产"错误覆盖，符号链接由 `_run` 既有装载逻辑处理（复核实证：`load_json` 会跟随符号链接而 `regular_case_path` 返回 None——**必须**在 `check_facts_vs_ledgers` 开头补 `if regular_case_path(case_dir, "facts.json") is None: errors.append("facts.json 不是案根常规文件（符号链接/越界）"); return`，`regular_case_path` 为本文件既有 `:482`）。`load_json` 对 `1e999` 的处理见 §1.5。

### C3 `scripts/report/stage2_closeout.py`：收口新增 `facts_vs_ledgers` 检查（11→12 项）

- `:575`（锚 `    record("facts_gate", facts_check)`）之前插入：

```python
    def facts_vs_ledgers():
        errors = []
        audit_release_gate.check_facts_vs_ledgers(case, load(case, "facts.json"), errors)
        return errors, [], "PASS"

```

（stage2 收口不传 receipt；图 2 收据绑定由发布闸验。）

- 同一锚行之后插入 `    record("facts_vs_ledgers", facts_vs_ledgers)`（保持 facts_gate 在前）。`load`（`:62`）、`audit_release_gate`（`:31`）既有。

### C4 测试

**C4-0 共享夹具助手 `scripts/tests/test_audit_release_gate.py`**（供 stage2/batch_d/P105 三处 import；本文件既有用例不动）

在 `:202`（锚 `def refresh_adversarial(root):`）之前插入：

```python
def build_facts_from_ledgers(root, *, symbol="TT", decimals=0, labels=None, peak_date="2026-01-01"):
    """R07（7.2.0）：夹具的 facts.json 一律由 facts_gate.py build 从三账生成（禁手写）。
    夹具无 provenance 锚点，峰值走 override＝confirmed 值，证据文件 peak_evidence.json 随案。"""
    root = Path(root)
    econ = json.loads((root / "economic_control_ledger.json").read_text(encoding="utf-8"))
    rows = econ.get("entries", econ.get("entities", []))
    (root / "peak_evidence.json").write_text(
        json.dumps({"note": "fixture: peak == confirmed"}) + "\n", encoding="utf-8")
    evidence = {"path": "peak_evidence.json", "sha256": sha(root / "peak_evidence.json")}
    names, overrides = {}, {}
    for row in rows:
        eid = str(row["entity_id"])
        names[eid] = (labels or {}).get(eid, eid)
        overrides[eid] = {"peak_raw": str(int(str(row["confirmed_economic_control_raw"]))),
                          "peak_date": peak_date, "evidence": evidence}
    write_json(root, "state_source.json", {
        "schema": "analysis-state-source/v1",
        "facts_inputs": {"symbol": symbol, "decimals": decimals, "entity_labels": names,
                         "peak_overrides": overrides, "metrics": {}}})
    proc = subprocess.run([sys.executable, str(HERE.parent / "report" / "facts_gate.py"),
                           "build", "--case-dir", str(root)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return root / "facts.json"


```

`write_json`/`sha`/`HERE`/`subprocess`/`sys`/`json`/`Path` 均为本文件既有。

**C4-a `scripts/tests/test_stage2_closeout.py`**

- `:19`（锚 `from test_audit_release_gate import build_case, gate`）改为 `from test_audit_release_gate import build_case, build_facts_from_ledgers, gate`。
- `:48-49`：`state` 的 `"addresses": [fixture.ENTITY_ADDR]` → `"addresses": ["0xabc"]`（与 `build_case` 三账成员一致）。
- `:52-55`（锚 `    write(case / "facts.json", {` 起四行）整块删除。
- `:58`：identity `rows` 的 `"address": fixture.ENTITY_ADDR` → `"address": "0xabc"`。
- `:64`（锚 `    fixture.add_camp_series(str(case))`）之后、`:65`（锚 `    proc = fixture.run(fixture.GATE, ["finalize", "--case-dir", str(case),`）之前插入：

```python
    add_provenance_ledger(case)   # reseal prereq 同款，先于 facts build 落盘（facts.provenance.inputs 绑它）
    build_facts_from_ledgers(case, labels={"e1": "大庄#1"})
```

- 新增模块级函数 `add_provenance_ledger(case)`（放在 `:36`（锚 `def build_release_case(root):`）之前），函数体逐字搬自 `test_stage2_reseal.py:28-39` `add_reseal_prereqs`（`REPO` 常量本文件已有；写法用本文件 `read`/`write`/`sha`）。
- `:123`、`:352`、`:590` 三处 `== 11` → `== 12`；`:586` 注释（锚 `    # A failing check cannot short-circuit the other ten checks or receipt emission.`）`ten` → `eleven`（r3 顺手校准，不影响执行）。
- 新增用例函数（放在 `:593`（锚 `TESTS = [dryrun_profile_exempts_stage3_artifacts, only_findings_changed_is_rejected,`）之前）并登记到 `TESTS` 列表末尾：

```python
def facts_vs_ledgers_rejects_hand_edit(cases):
    case = cases.fresh()
    update(case, "facts.json", lambda obj: obj["entities"]["e1"].update(current_raw="90"))
    checks = check_result(case, 2)
    assert checks["facts_vs_ledgers"]["status"] == "BLOCK" and "e1" in "".join(checks["facts_vs_ledgers"]["detail"]), checks
    case = cases.fresh()
    update(case, "facts.json", lambda obj: obj.pop("provenance"))
    checks = check_result(case, 2)
    assert checks["facts_vs_ledgers"]["status"] == "BLOCK" and "provenance" in "".join(checks["facts_vs_ledgers"]["detail"]), checks
    case = cases.fresh()
    update(case, "facts.json", lambda obj: obj["provenance"].update(mode="exploration"))
    checks = check_result(case, 2)
    assert checks["facts_vs_ledgers"]["status"] == "BLOCK" and "exploration" in "".join(checks["facts_vs_ledgers"]["detail"]), checks
```

RED：基线无 `facts_vs_ledgers` 键 → KeyError/AssertionError；`check_result` 的 12 计数在基线为 11 → AssertionError。

**C4-a′ `scripts/tests/test_stage2_reseal.py`**：`:28-39` `add_reseal_prereqs` 函数体改为一行 `w2.add_provenance_ledger(case)`（保留函数名与所有调用点；`w2` 为本文件既有别名）。语义：seed 案已由 `build_release_case` 写入同款 ledger，此处幂等重写字节不变，facts.provenance.inputs 不漂移。

**C4-b `scripts/tests/test_repair_batch_d.py`（`build_solana_case`）**

- `:963`（锚 `    from test_audit_release_gate import align_ledgers_to_owner_snapshot`）改为 `    from test_audit_release_gate import align_ledgers_to_owner_snapshot, build_facts_from_ledgers`。
- `:1167-1168`（锚 `        "facts.json": {"token": {"symbol": "SOLX", "decimals": 0,` 与 `                                 "total_supply_raw": "100"}, "entities": {}},`）两行删除。
- `:1207`（锚 `    write_json(root / "whale_series.json", [])`）之前插入 `    build_facts_from_ledgers(root, symbol="SOLX")`（identity_gate.json 已在 :1200-1206 写出）。
- 反例：新增**独立函数** `t_r07_facts_vs_ledgers()`，放在 `:1282`（锚 `def t_fd2_unseal_binds_flip_receipt():`）之前；函数体：`import audit_release_gate as gate`，`with tempfile.TemporaryDirectory(prefix="d-r07-", dir="/private/tmp") as raw:` 内 `root = Path(raw)`、`report = build_solana_case(root)`、先断言 `gate.run(root, report, profile="new-analysis") == []`；再把 `facts.json` 的 e1 `current_raw` 改 `"1"` → errors 含 `三账重算值不一致`；再删 `facts.json` → errors 含 `缺必需资产: facts.json`。用 `check(...)` 登记两条。在 `main()` 的 `:1700`（锚 `    t_b1_b2_solana_new_analysis()`）之后加一行 `    t_r07_facts_vs_ledgers()`。

**C4-c `scripts/tests/test_review_20260804_p105.py`**

- `:200-201`（锚 `        "facts.json": {"token": {"symbol": "FX", "decimals": 0,` 与 `                                 "total_supply_raw": "1"}, "entities": {}},`）两行与其上一行注释 `:199`（锚 `        # facts 带最小 token（figure2 check 真跑需要 total_supply_raw>0）`）删除。
- `:209`（锚 `    identity = augment_gate(bridge_root, {`）：给该调用追加关键字参数 `balances=balances`（`balances`＝本函数 `:142` 的 240-owner 字典，同一作用域）——identity 的 total_supply_raw/收据/绑定从此与 owner 快照同一世界（否则 identity total=100 而三账 e1=owner-000 的 2,000,000，build 自检 G2 必拒；同类失真 `test_a4_gate.py:190-197` 注释已记）。
- `identity_gate.json` 写出行（锚 `    write_json(root / "identity_gate.json", identity)`，本文件恰 1 处）之后插入 `    fixture.build_facts_from_ledgers(root, symbol="FX")`（`fixture`＝test_audit_release_gate 模块别名，本文件既有）。

**C4-c′ `scripts/tests/identity_gate_fixture.py`**

- `:52`（锚 `def augment_gate(root, gate_obj, *, chain, token="0x" + "a" * 40):`）签名末尾加 `, balances=None`；`:55-57`（锚 `    balances = {row["address"]: 100 for row in rows}` 起三行）改为：

```python
    if balances is None:
        balances = {row["address"]: 100 for row in rows}
        if not balances:
            balances = {"0x" + "f" * 40: 100}
    else:
        balances = {str(k): int(v) for k, v in balances.items()}   # 调用方保证 rows 地址 ⊆ balances
```

  其余不动（`write_binding` 真跑 `replay_pass1`，对地址只 `lower()` 不校验格式，`replay_pass1.py:79`）。默认行为逐字节不变，既有调用点零影响。

**C4-e `scripts/tests/test_a4_gate.py`（`case_new` 走 `build_html --mode analysis-new`＝new-analysis 闸，`build_html.py:254/:434/:489-493`）**

- `:30`（锚 `from test_audit_release_gate import build_case, refresh_adversarial, sha`）改为 `from test_audit_release_gate import build_case, build_facts_from_ledgers, refresh_adversarial, sha`。
- `:497`（锚 `    add_camp_series(new_d)`）之后、`:498`（锚 `    p = run(GATE, ["finalize", "--case-dir", new_d,`）之前插入 `    build_facts_from_ledgers(new_d, labels={"e1": "实体1"})`。三账成员已由 `add_distribution_initial` 对齐到 `balances_final.json`（＝identity 世界，`{ENTITY_ADDR:100}`），与 state `whale_groups` 一致（G1）。`:378-381` d 案手写 facts **保留**（d 只走 analysis-audit，不进 new-analysis 闸；case_new 复制后被 build 覆盖）。P1-05 断言 `p_build.returncode == 0` 与 HTML 生成不变。

**C4-d `scripts/tests/test_report_facts.py`（build/derive/闸 单元）**

- 头部补 `import hashlib`、`import subprocess`、`from pathlib import Path`（按现有 import 顺序插入）。
- 在 `:115`（锚 `    print("PASS: facts 宏渲染/附录B同源/G1集合gate(含entity_id主键)/G4宏名gate/"`）之前插入 `_r07_build_cases()` 调用；其定义放 `main()` 之前。夹具函数 `_r07_case(root)`：写 `balances_snapshot.json`（schema `address-balance-snapshot/v1`，as_of_block 123，`0xabc:"100"`）、三账（照 batch15 `write_ledgers` :57-83 形状，owner `0xabc`、amount 100、balance_source sha 绑定）、`identity_gate.json` `{"total_supply_raw":"1000"}`、`provenance_ledger.json` `{"schema":"provenance-ledger/v2","exploration":false,"total_supply_raw":"1000","entities":[{"entity_id":"e1","anchors":{"current":{"stock_raw":"100"},"peak":{"stock_raw":"150","date":"2026-01-02"}}}]}`、`state_source.json` `{"schema":"analysis-state-source/v1","facts_inputs":{"symbol":"TT","decimals":0,"entity_labels":{"e1":"大庄#1"},"metrics":{"m1":{"num_raw":"100","den":"total_supply","desc":"x"}}}}`。闸模块用 importlib 从 `HERE/../report/audit_release_gate.py` 装载（照 `test_audit_release_gate.py:16-22`）。用例（各自独立临时目录、逐例捕获 AssertionError）：

| # | 名称 | 断言 |
|---|---|---|
| 1 | derive 绿例 | `fg.derive_facts(root)`：token=={TT,0,"1000"}；entities 键 {"e1"}；e1 addresses ["0xabc"]、current "100"、peak "150"、peak_date "2026-01-02"、label "大庄#1"；metrics 透传；provenance schema/binding/mode=="formal"、inputs 五键 sha 与实际文件一致、peak_overrides=={}、producer.path 正确 |
| 2 | CLI build 幂等 | `facts_gate.py build --case-dir root` rc 0 且 facts.json == derive；再 build 一次字节相同；`--source other.json` rc 2 |
| 3 | override 优先＋证据 | 写 `peak_evidence.json`，facts_inputs 加 peak_overrides e1 {160,"2026-01-03",evidence 正确 sha} → peak "160"、provenance.peak_overrides 含 e1；evidence sha 错 → ValueError 含 "evidence"；缺 evidence → ValueError |
| 4 | formal 无峰值来源拒 / exploration 放行 | 删 provenance_ledger.json → `derive_facts(root)` ValueError 含 "峰值来源"；`derive_facts(root, exploration=True)` mode=="exploration"、peak==current、peak_date None |
| 5 | 预置绑定拒 | facts_inputs 含 `"provenance": {}` → ValueError 含 "预置" |
| 6 | label 缺/空拒；entity_labels 多余实体拒 | 分别 ValueError |
| 7 | 三账不闭合拒 | economic e1 confirmed 改 "90" → ValueError 含 "三账" |
| 8 | 总量冲突拒 | provenance_ledger total_supply_raw 改 "999" → ValueError 含 "total_supply_raw" |
| 9 | 闸绿例 | build 后 `errors=[]; gate.check_facts_vs_ledgers(root, facts, errors)` → `[]`；传 `receipt={"facts":{"path":"facts.json"}}` 仍 `[]` |
| 10 | 闸拒手改 | facts e1 current_raw "90" → errors 含 "e1"；删 provenance → 含 "provenance"；mode 改 exploration → 含 "exploration"；改 identity_gate total_supply_raw 为 "2000"（不重 build）→ errors 非空；`receipt={"facts":{"path":"facts_alt.json"}}` → 含 "figure2" |
| 11 | peak<current 拒 | provenance peak stock_raw "50" → ValueError |
| 12 | 空账拒 | membership `entries: []`（或整键缺失）→ ValueError 含 "空账"；position 同 |
| 13 | 非有限输入拒 | state_source 的 metrics 值分别写成字面量 `NaN`、`Infinity`、`1e999`（三变体各自独立目录，用字符串拼 JSON 写盘）→ `derive_facts` ValueError 含 "非有限"；闸侧：state_source 正常 build 后把 facts.json 的 metrics 值改写成 `1e999` → `check_facts_vs_ledgers` errors 含 "metrics" |
| 14 | 产物须过既有 gate | identity_gate total_supply_raw 改 "50"（< current 100，provenance_ledger total 同改 "50"）→ `derive_facts` ValueError 含 "G2" |

RED：基线 `fg` 无 `derive_facts`/`gate` 无 `check_facts_vs_ledgers` → AttributeError 记为该例失败原文。C4-b/C4-e 的 RED＝基线 `test_audit_release_gate` 无 `build_facts_from_ledgers` → ImportError（记原文）。

### C5 `scripts/tests/invariant_manifest.json`

施工完成后跑 `python3 -B scripts/tests/invariant_scan.py`；按其报出的缺项**逐条增补**（预期：`receipt_producers` 加 `{"schemas":["facts-provenance/v1"],"script":"scripts/report/facts_gate.py"}`；`receipt_consumers` 加 facts_gate.py 的 `analysis-state-source/v1` 与 audit_release_gate.py 条目里加 `facts-provenance/v1`；`atomic_writes` 加 facts_gate.py `build_main` overwrite_single；`minimum_counts` 若因此要涨按实际涨）。**不得**整体回填/重排其他条目；diff 只含新增行与必要的计数改动。

### C6 文档 `references/report-template.md:212`

该行内唯一子串 `数值一律**原始整数字符串**从落盘数据复制` → `由 \`facts_gate.py build\` 自三账生成，禁手抄`（58 B → 53 B，−5 B）。其余不动。

### C7（v4，盲审 C-01）`facts_gate.py` 输入类型约定落实＋用例 15

**生产 `scripts/report/facts_gate.py`**（行号＝1b317b3）

- `:357-360`（锚首行 `    symbol = str(fi.get("symbol") or "").strip()`，末行 `        raise ValueError("facts_inputs.symbol/decimals 缺失或非法")`）四行替换为：

```python
    symbol = fi.get("symbol")
    decimals = fi.get("decimals")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("facts_inputs.symbol 必须是非空字符串")
    symbol = symbol.strip()
    if isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
        raise ValueError("facts_inputs.decimals 必须是 ≥0 的整数")
```

- `:368`（锚 `        raise ValueError("facts_inputs.peak_overrides/merge_evidence/role_notes 须为对象")`）之后插入：

```python
    metrics = fi.get("metrics", {})
    if not isinstance(metrics, dict) or any(not isinstance(v, dict) for v in metrics.values()):
        raise ValueError("facts_inputs.metrics 须为对象且每项为对象")
    dual_basis = fi.get("dual_basis")
    if "dual_basis" in fi and not isinstance(dual_basis, dict):
        raise ValueError("facts_inputs.dual_basis 须为对象")
```

- `:446`（锚 `             "entities": entities, "metrics": fi.get("metrics") or {}}`）改为 `             "entities": entities, "metrics": metrics}`；`:447-448`（锚 `    if isinstance(fi.get("dual_basis"), dict):` 与 `        facts["dual_basis"] = fi["dual_basis"]`）改为 `    if dual_basis is not None:` 与 `        facts["dual_basis"] = dual_basis`。
- `:69`（锚 `  metrics: {}（可选透传）；dual_basis: {}（可选透传）`）改为 `  metrics: {mid: {...}}（可选；对象且每项为对象）；dual_basis: {}（可选；对象）`。
- 既有用例 1（`:121` 断言 token）与 C4-d 夹具（symbol "TT"、decimals 0、metrics m1 对象）不受影响；全仓测试无断言旧文案 `缺失或非法`（施工方 `grep -rn -F` 复核）。

**测试 `scripts/tests/test_report_facts.py`**

- `:257`（锚 `    def existing_gate(root):`）之前插入：

```python
    def bad_type(root, field, value, text):
        edit(root, "state_source.json", lambda obj: obj["facts_inputs"].update({field: value}))
        reject(root, text)

```

- `:283`（锚 `    run("14 产物过既有 G2 gate", existing_gate)`）之后插入：

```python
    for field, value, text in (("symbol", 123, "symbol"), ("decimals", "18", "decimals"),
                               ("metrics", [{"value": "7"}], "metrics"), ("metrics", {"m1": "7"}, "metrics"),
                               ("dual_basis", "x", "dual_basis"), ("dual_basis", None, "dual_basis")):
        run(f"15 类型非法拒 {field}", lambda root, f=field, v=value, t=text: bad_type(root, f, v, t))
```

- `:285`（锚 `    print(f"PASS: R07 build/derive/发布闸 14 类、{len(results)} 个独立用例", flush=True)`）`14 类` → `15 类`。
- RED：基线 symbol=123 被 `str()` 吞、metrics 列表/字符串项直通、dual_basis "x"/`null` 静默丢弃 → `reject` 抛 "derive_facts 应拒绝该输入"；decimals "18" 基线已拒（文案含 "decimals"）——该变体基线即绿，记为回归例。
- §0.8 本次只跑 `test_report_facts.py`、`test_stage2_closeout.py`、`test_repair_batch_d.py`、`test_review_20260804_p105.py`、`test_a4_gate.py`、`invariant_scan.py`；§1.1 三字节数不变（930065）；白名单只 `facts_gate.py`、`test_report_facts.py`、`C7_done.md`、`C7_red_evidence.txt`。完成报告写 `C7_done.md`，stdout 首行 `# 施工 C7：完成`/`停工`。

## 3. 完成报告 `C_done.md` 必含

①0.1 输出；②C1/C2/C3 diff 原文与 C4/C5/C6 diff 摘要；③RED 摘要（逐例）；④0.8 各测试结果尾行；⑤§1.1 三字节数；⑥`git diff --stat`；⑦差异/停工点；⑧禁读披露。stdout 首行 `# 施工 C：完成` / `# 施工 C：停工`。

## 4. 调度方本机验收项（施工方不做）

- APU 0801 对照：把三账＋identity_gate＋provenance_ledger 复制到临时目录，补最小 state_source.json（三实体 label 抄现有 facts），跑 `build --exploration`：current_raw 须 3/3 等于现有 facts；peak 与现有 facts 对照（预期 1/3 相等，另两处需 override）。不写回案目录。
- `test_stage2_reseal.py`：commit 后 `git -C /tmp/w3_acceptance checkout --detach <新 HEAD>`（worktree 内不得留 `__pycache__`），确认本仓库 `git status --short` 为空，再 `python3 -B scripts/tests/test_stage2_reseal.py`。
- 登记 `code_change_pending.md`：P7 扩注（发布闸 `load_json` 对 `1e999` 的漏口由 C2 逐键比对兜底，facts_gate 输入侧已严格）；P11 撤销（改为 REQUIRED，不再有"在场即验"口子）；P12＝producer.sha256 只记录不比对（facts_gate.py 升级后旧 facts 不强制重 build）；P4 保留（override 数学正确性不验）；APU 0801 再发布须补 state_source.facts_inputs 重 build。
