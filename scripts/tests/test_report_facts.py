#!/usr/bin/env python3
"""报告编译化（facts_gate）离线测试（3.18.0）：宏渲染 / 语义 gate 四条契约。"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
FG = os.path.join(HERE, "..", "report", "facts_gate.py")
spec = importlib.util.spec_from_file_location("facts_gate", FG)
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)

FACTS = {
    "token": {"symbol": "TT", "decimals": 18, "total_supply_raw": str(10**9 * 10**18)},
    "entities": {
        "e1": {"label": "大庄#1",
               "addresses": ["0xAA00000000000000000000000000000000000001",
                             "0xAA00000000000000000000000000000000000002"],
               "current_raw": str(278_400_000 * 10**18),
               "peak_raw": str(687_000_000 * 10**18), "peak_date": "2026-05-01"},
    },
    "metrics": {"m_alpha": {"num_raw": str(376_000_000 * 10**18),
                            "den": "total_supply", "desc": "Alpha托管"}},
}
STATE_OK = {"whale_groups": [
    {"label": "大庄#1", "addresses": ["0xaa00000000000000000000000000000000000001",
                                      "0xaa00000000000000000000000000000000000002"]}]}


def facts_obj():
    return fg.Facts(json.loads(json.dumps(FACTS)))


def _r07_write(root, name, value):
    path = root / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _r07_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _r07_case(root):
    snapshot = _r07_write(root, "balances_snapshot.json", {
        "schema": "address-balance-snapshot/v1", "as_of_block": 123,
        "entries": [{"address": "0xabc", "balance_raw": "100"}]})
    source = {"path": snapshot.name, "sha256": _r07_sha(snapshot), "as_of_block": 123}
    _r07_write(root, "membership_ledger.json", {"entries": [{
        "entity_id": "e1", "address": "0xabc", "membership": "strict",
        "as_of_balance_raw": "100", "balance_source": source}]})
    _r07_write(root, "position_ledger.json", {"entries": [{
        "entity_id": "e1", "address": "0xabc", "location_id": "wallet:0xabc",
        "amount_raw": "100"}]})
    _r07_write(root, "economic_control_ledger.json", {
        "entries": [{"entity_id": "e1", "wallet_self_held_raw": "100",
                     "confirmed_facility_claims": [], "confirmed_economic_control_raw": "100",
                     "unresolved_facility_exposure": []}],
        "double_count_check_passed": True, "unresolved_count": 0, "unresolved": []})
    _r07_write(root, "identity_gate.json", {"total_supply_raw": "1000"})
    _r07_write(root, "provenance_ledger.json", {
        "schema": "provenance-ledger/v2", "exploration": False, "total_supply_raw": "1000",
        "entities": [{"entity_id": "e1", "anchors": {
            "current": {"stock_raw": "100"},
            "peak": {"stock_raw": "150", "date": "2026-01-02"}}}]})
    _r07_write(root, "state_source.json", {
        "schema": "analysis-state-source/v1", "facts_inputs": {
            "symbol": "TT", "decimals": 0, "entity_labels": {"e1": "大庄#1"},
            "metrics": {"m1": {"num_raw": "100", "den": "total_supply", "desc": "x"}}}})


def _r07_build_cases():
    sys.path.insert(0, str(Path(FG).resolve().parent))
    gate_spec = importlib.util.spec_from_file_location(
        "audit_release_gate", Path(HERE).parent / "report" / "audit_release_gate.py")
    gate = importlib.util.module_from_spec(gate_spec)
    gate_spec.loader.exec_module(gate)
    failures, results = [], []

    def run(name, test):
        with tempfile.TemporaryDirectory(prefix="r07-facts-", dir="/private/tmp") as raw:
            root = Path(raw)
            _r07_case(root)
            try:
                test(root)
                print("ok    R07 " + name, flush=True)
            except (AssertionError, ImportError, AttributeError) as exc:
                failures.append(name)
                print(f"FAIL  R07 {name}: {type(exc).__name__}: {exc}", flush=True)
            results.append(name)

    def edit(root, name, fn):
        obj = json.loads((root / name).read_text(encoding="utf-8"))
        fn(obj)
        _r07_write(root, name, obj)

    def reject(root, text=""):
        try:
            fg.derive_facts(root)
        except ValueError as exc:
            assert text in str(exc), str(exc)
        else:
            raise AssertionError("derive_facts 应拒绝该输入: " + text)

    def build(root):
        facts = fg.derive_facts(root)
        _r07_write(root, "facts.json", facts)
        return facts

    def cli(root, *args):
        return subprocess.run([sys.executable, "-B", FG, "build", "--case-dir", str(root), *args],
                              capture_output=True, text=True)

    def derive_green(root):
        facts = fg.derive_facts(root)
        assert facts["token"] == {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"}, facts
        assert set(facts["entities"]) == {"e1"}, facts
        assert facts["entities"]["e1"] == {
            "label": "大庄#1", "addresses": ["0xabc"], "current_raw": "100",
            "peak_raw": "150", "peak_date": "2026-01-02"}, facts
        assert facts["metrics"] == {"m1": {"num_raw": "100", "den": "total_supply", "desc": "x"}}, facts
        prov = facts["provenance"]
        assert (prov["schema"], prov["facts_binding"], prov["mode"]) == (
            "facts-provenance/v1", "ledger-derived", "formal"), prov
        names = {"membership_ledger.json", "position_ledger.json", "economic_control_ledger.json",
                 "identity_gate.json", "provenance_ledger.json"}
        assert set(prov["inputs"]) == names, prov
        assert all(prov["inputs"][name] == {"sha256": _r07_sha(root / name)} for name in names), prov
        assert prov["state_source"] == {"path": "state_source.json",
                                        "sha256": _r07_sha(root / "state_source.json")}, prov
        assert prov["peak_overrides"] == {}, prov
        assert prov["producer"]["path"] == "scripts/report/facts_gate.py", prov
        assert prov["producer"]["sha256"] == _r07_sha(Path(FG)), prov

    def cli_idempotent(root):
        proc = cli(root)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        path = root / "facts.json"
        assert json.loads(path.read_text(encoding="utf-8")) == fg.derive_facts(root)
        first = path.read_bytes()
        proc = cli(root)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert path.read_bytes() == first, "同输入 build 字节不一致"
        proc = cli(root, "--source", "other.json")
        assert proc.returncode == 2, proc.stdout + proc.stderr

    def override(root, variant):
        evidence = _r07_write(root, "peak_evidence.json", {"note": "observed peak"})
        ov = {"peak_raw": "160", "peak_date": "2026-01-03",
              "evidence": {"path": evidence.name, "sha256": _r07_sha(evidence)}}
        if variant == "bad_sha":
            ov["evidence"]["sha256"] = "0" * 64
        elif variant == "missing_evidence":
            ov.pop("evidence")
        edit(root, "state_source.json", lambda obj: obj["facts_inputs"].update(peak_overrides={"e1": ov}))
        if variant != "valid":
            reject(root, "evidence")
            return
        facts = fg.derive_facts(root)
        assert facts["entities"]["e1"]["peak_raw"] == "160", facts
        assert facts["entities"]["e1"]["peak_date"] == "2026-01-03", facts
        assert facts["provenance"]["peak_overrides"] == {"e1": ov}, facts

    def no_peak(root):
        (root / "provenance_ledger.json").unlink()
        reject(root, "峰值来源")
        facts = fg.derive_facts(root, exploration=True)
        assert facts["provenance"]["mode"] == "exploration", facts
        ent = facts["entities"]["e1"]
        assert ent["peak_raw"] == ent["current_raw"] and ent["peak_date"] is None, ent

    def preset_binding(root):
        edit(root, "state_source.json", lambda obj: obj["facts_inputs"].update(provenance={}))
        reject(root, "预置")

    def bad_labels(root, variant):
        def change(obj):
            fi = obj["facts_inputs"]
            if variant == "missing":
                fi.pop("entity_labels")
            elif variant == "empty":
                fi["entity_labels"] = {"e1": ""}
            else:
                fi["entity_labels"]["ghost"] = "ghost"
        edit(root, "state_source.json", change)
        reject(root)

    def not_closed(root):
        edit(root, "economic_control_ledger.json", lambda obj:
             obj["entries"][0].update(confirmed_economic_control_raw="90"))
        reject(root, "三账")

    def supply_conflict(root):
        edit(root, "provenance_ledger.json", lambda obj: obj.update(total_supply_raw="999"))
        reject(root, "total_supply_raw")

    def gate_green(root):
        facts = build(root)
        for receipt in (None, {"facts": {"path": "facts.json"}}):
            errors = []
            gate.check_facts_vs_ledgers(root, facts, errors, receipt=receipt)
            assert errors == [], errors

    def hand_edit(root, variant):
        facts = build(root)
        receipt, needle = None, ""
        if variant == "current":
            facts["entities"]["e1"]["current_raw"] = "90"
            needle = "e1"
        elif variant == "provenance":
            facts.pop("provenance")
            needle = "provenance"
        elif variant == "exploration":
            facts["provenance"]["mode"] = "exploration"
            needle = "exploration"
        elif variant == "identity":
            edit(root, "identity_gate.json", lambda obj: obj.update(total_supply_raw="2000"))
        else:
            receipt, needle = {"facts": {"path": "facts_alt.json"}}, "figure2"
        _r07_write(root, "facts.json", facts)
        errors = []
        gate.check_facts_vs_ledgers(root, facts, errors, receipt=receipt)
        assert errors and any(needle in error for error in errors), errors

    def peak_too_low(root):
        edit(root, "provenance_ledger.json", lambda obj:
             obj["entities"][0]["anchors"]["peak"].update(stock_raw="50"))
        reject(root)

    def empty_ledger(root, name, missing):
        _r07_write(root, name, {} if missing else {"entries": []})
        reject(root, "空账")

    def nonfinite(root, literal):
        path = root / "state_source.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        obj["facts_inputs"]["metrics"]["m1"] = {"value": "NONFINITE"}
        path.write_text(json.dumps(obj).replace('"NONFINITE"', literal), encoding="utf-8")
        reject(root, "非有限")

    def nonfinite_facts(root):
        facts = build(root)
        facts["metrics"]["m1"] = {"value": "NONFINITE"}
        path = root / "facts.json"
        path.write_text(json.dumps(facts).replace('"NONFINITE"', "1e999"), encoding="utf-8")
        errors = []
        facts = gate.load_json(path, errors)
        assert errors == [], errors
        gate.check_facts_vs_ledgers(root, facts, errors)
        assert any("metrics" in error for error in errors), errors

    def bad_type(root, field, value, text):
        edit(root, "state_source.json", lambda obj: obj["facts_inputs"].update({field: value}))
        reject(root, text)

    def existing_gate(root):
        for name in ("identity_gate.json", "provenance_ledger.json"):
            edit(root, name, lambda obj: obj.update(total_supply_raw="50"))
        reject(root, "G2")

    run("1 derive 绿例", derive_green)
    run("2 CLI build 幂等", cli_idempotent)
    for variant in ("valid", "bad_sha", "missing_evidence"):
        run("3 override " + variant, lambda root, v=variant: override(root, v))
    run("4 formal 无峰值拒 / exploration 放行", no_peak)
    run("5 预置绑定拒", preset_binding)
    for variant in ("missing", "empty", "extra"):
        run("6 label " + variant, lambda root, v=variant: bad_labels(root, v))
    run("7 三账不闭合拒", not_closed)
    run("8 总量冲突拒", supply_conflict)
    run("9 闸绿例", gate_green)
    for variant in ("current", "provenance", "exploration", "identity", "receipt"):
        run("10 闸拒手改 " + variant, lambda root, v=variant: hand_edit(root, v))
    run("11 peak < current 拒", peak_too_low)
    for name in ("membership_ledger.json", "position_ledger.json"):
        for missing in (False, True):
            run(f"12 空账 {name} missing={missing}",
                lambda root, n=name, m=missing: empty_ledger(root, n, m))
    for literal in ("NaN", "Infinity", "1e999"):
        run("13 非有限输入 " + literal, lambda root, v=literal: nonfinite(root, v))
    run("13 facts 溢出值拒", nonfinite_facts)
    run("14 产物过既有 G2 gate", existing_gate)
    for field, value, text in (("symbol", 123, "symbol"), ("decimals", "18", "decimals"),
                               ("metrics", [{"value": "7"}], "metrics"), ("metrics", {"m1": "7"}, "metrics"),
                               ("dual_basis", "x", "dual_basis"), ("dual_basis", None, "dual_basis")):
        run(f"15 类型非法拒 {field}", lambda root, f=field, v=value, t=text: bad_type(root, f, v, t))
    assert not failures, f"R07 失败 {len(failures)}/{len(results)}: {failures}"
    print(f"PASS: R07 build/derive/发布闸 15 类、{len(results)} 个独立用例", flush=True)


def main():
    # 1) 宏渲染：组合宏格式与百分比精度
    f = facts_obj()
    md = "问1：{{e1.label}} 当前 {{e1.amount_share}}（峰值 {{e1.peak_share}}，{{e1.naddr}} 址）；Alpha {{m:m_alpha}}。\n\n{{appendix_b}}"
    out = f.render(md)
    assert "大庄#1 当前 2.78亿枚【总量27.84%】" in out, out[:120]
    assert "峰值 68.70%" in out and "2 址" in out and "Alpha 37.60%" in out
    assert "`0xAA00000000000000000000000000000000000001`" in out, "附录B应含完整地址"
    errs, notes = fg.gate_check(f, STATE_OK, out)
    assert not errs, f"合法输入不应报错: {errs}"

    # 2) G1 成员集合不一致必炸（state 少一个地址）
    f2 = facts_obj()
    out2 = f2.render(md)
    bad_state = {"whale_groups": [{"label": "大庄#1",
                 "addresses": ["0xaa00000000000000000000000000000000000001"]}]}
    errs, _ = fg.gate_check(f2, bad_state, out2)
    assert any("G1" in e and "成员集合不一致" in e for e in errs), f"应报 G1: {errs}"

    # 3) G4 宏名打错必炸（渲染期抛 KeyError）
    f3 = facts_obj()
    try:
        f3.render("{{e1.shrae}}")
        raise AssertionError("拼错宏字段应抛 KeyError")
    except KeyError:
        pass
    try:
        f3.render("{{e_ghost.share}}")
        raise AssertionError("不存在的实体应抛 KeyError")
    except KeyError:
        pass

    # 4) G5 手写百分比检出（27.84% 来自宏=白名单；99.99% 手写=检出）
    f4 = facts_obj()
    out4 = f4.render("{{e1.share}} 而某处手写了 99.99% 的数字")
    _, notes = fg.gate_check(f4, None, out4)
    g5 = [n for n in notes if "G5" in n]
    assert g5 and "99.99%" in g5[0] and "27.84%" not in g5[0], f"G5 差集错误: {notes}"

    # 5) G2 供给上界：实体持仓超总供应必炸
    over = json.loads(json.dumps(FACTS))
    over["entities"]["e1"]["current_raw"] = str(2 * 10**9 * 10**18)
    over["entities"]["e1"]["peak_raw"] = str(2 * 10**9 * 10**18)
    errs, _ = fg.gate_check(fg.Facts(over))
    assert any("G2" in e for e in errs), f"应报 G2: {errs}"

    # 6) G1 entity_id 主键优先（3.19）：state 组 label 改了措辞但 entity_id 匹配 → 不报 G1
    f6 = facts_obj()
    state_id = {"whale_groups": [
        {"entity_id": "e1", "label": "大庄#1（改了措辞）",
         "addresses": ["0xaa00000000000000000000000000000000000001",
                       "0xaa00000000000000000000000000000000000002"]}],
        "provenance": {"schema_version": "2", "skill_commit": "abc1234",
                       "data_sources": ["hypersync_v2"]}}
    errs, notes6 = fg.gate_check(f6, state_id)
    assert not errs, f"entity_id 匹配时改 label 不应报 G1: {errs}"
    assert not any("G7" in n for n in notes6), f"带 provenance 不应报 G7: {notes6}"
    # entity_id 匹配但成员不一致仍必炸
    state_id_bad = json.loads(json.dumps(state_id))
    state_id_bad["whale_groups"][0]["addresses"].pop()
    errs, _ = fg.gate_check(facts_obj(), state_id_bad)
    assert any("G1" in e and "entity_id=e1" in e for e in errs), f"应按 id 键报 G1: {errs}"

    # 7) A1 时间因果：merged_since 宏渲染；多地址实体缺字段出 G6 NOTE；旧 state 出 G7 NOTE
    with_ts = json.loads(json.dumps(FACTS))
    with_ts["entities"]["e1"]["merge_evidence_earliest"] = "2026-05-03"
    f7 = fg.Facts(with_ts)
    assert f7.render("自 {{e1.merged_since}} 起") == "自 2026-05-03 起"
    _, notes7 = fg.gate_check(f7, STATE_OK)
    assert not any("G6" in n for n in notes7), f"有归并时间不应报 G6: {notes7}"
    assert any("G7" in n for n in notes7), f"旧 state 无 provenance 应出 G7 NOTE: {notes7}"
    _, notes7b = fg.gate_check(facts_obj(), None)
    assert any("G6" in n and "e1" in n for n in notes7b), f"缺归并时间应出 G6 NOTE: {notes7b}"
    try:
        facts_obj().render("{{e1.merged_since}}")
        raise AssertionError("缺 merge_evidence_earliest 时 merged_since 宏应抛 KeyError")
    except KeyError:
        pass

    _r07_build_cases()
    print("PASS: facts 宏渲染/附录B同源/G1集合gate(含entity_id主键)/G4宏名gate/"
          "G5手写检出/G2上界/G6归并时点/G7血缘提示，七契约全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
