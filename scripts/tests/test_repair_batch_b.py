#!/usr/bin/env python3
"""修复批 B 回归：F-03 快照双向闭合（两层）＋F-08 上游收据记录项三验。

反例口径：
- F-03 第一层原反例＝快照只装 1% 的币，build_scan 照样 exit 0（缺口不拦）。
- F-03 第二层原反例＝同值换仓，分布扫描换一份"总和一样、owner 分配不同"的快照，
  发布闸照样放行（不比对四查真正核过的那份快照）。
- F-08 原反例＝把已记录的 upstream_receipts 改成不存在的文件＋伪 sha/size，
  validate_scan 照样返回空错误表。
合法绿例（防误伤）：dead-sink 20%（sum=total≠net）、案根有收据但 scan 没记 → 仍 PASS。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCAN = ROOT / "scripts/report/holder_distribution_scan.py"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts/report"))
sys.path.insert(0, str(ROOT / "scripts/lib"))
import holder_distribution_scan as dist  # noqa: E402

GATE = ROOT / "scripts/report/audit_release_gate.py"
_spec = importlib.util.spec_from_file_location("audit_release_gate_batchb", GATE)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, bool(ok), detail))
    print(("ok   " if ok else "FAIL ") + f"[{name}]" + ("" if ok else f" {detail}"))
    return bool(ok)


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_case(root: Path, balances: dict[str, int], *, total: int | None = None,
              net: int | None = None, excluded: list[dict] | None = None) -> None:
    """最小合法案目录；total/net 可与快照和脱钩，用来造闭合缺口与 dead-sink。"""
    snap = root / "data/holders_owners.json"
    write_json(snap, {owner: str(raw) for owner, raw in balances.items()})
    snapshot_sum = sum(balances.values())
    write_json(root / "supply_truth.json", {
        "schema": "supply-truth/v1", "verdict": "PASS", "exit_code": 0,
        "total_supply_raw": str(snapshot_sum if total is None else total),
        "net_supply_raw": str(snapshot_sum if net is None else net)})
    write_json(root / "data_map.json", {
        "schema": "data-map/v1",
        "files": [{"path": "data/holders_owners.json", "sha256": sha(snap)}]})
    write_json(root / "candidate_screening.json", {
        "schema": "candidate-screening/v1", "auto_excluded_candidate": excluded or []})


def run_scan(case: Path, *extra: str):
    return subprocess.run([sys.executable, str(SCAN), "--case-dir", str(case),
                           "--stage", "initial", *extra], capture_output=True, text=True)


def smooth(n=240, scale=1) -> dict[str, int]:
    return {f"owner-{i:04d}": max(1, int(2_000_000 / (1.035 ** i))) * scale for i in range(n)}


# --------------------------------------------------------------------------
# F-03 第一层：build_scan 快照双向闭合
# --------------------------------------------------------------------------

def test_f03_snapshot_gap_rejected() -> None:
    """原反例：total=100 而快照只有 1 个币，缺口 99% 必须拒。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        make_case(d, {"0xaaa": 1}, total=100, net=100)
        p = run_scan(d)
        out = json.loads((d / "distribution_scan.json").read_text())
        check("F-03/1 快照缺口 99% 被拒", p.returncode == 2
              and out.get("exit_code") == 2
              and out.get("not_evaluable_reason") == "data_broken",
              f"rc={p.returncode} out={out.get('exit_code')} {p.stdout}{p.stderr}")


def test_f03_dead_sink_green() -> None:
    """合法绿例：mint 100 / burn 20 的 dead-sink——sum==total 但 net<total，必须放行。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        rows = smooth(240)
        private = sum(rows.values())
        dead = private // 4                      # 占 total 的 20%
        rows["0x000000000000000000000000000000000000dead"] = dead
        make_case(d, rows, total=private + dead, net=private,
                  excluded=[{"address": "0x000000000000000000000000000000000000dead",
                             "bucket": "burn_sentinel"}])
        p = run_scan(d)
        out = json.loads((d / "distribution_scan.json").read_text()) \
            if (d / "distribution_scan.json").is_file() else {}
        den = out.get("denominators") or {}
        burn = (out.get("bucket_coverage") or {}).get("burn_sentinel") or {}
        check("F-03/1 dead-sink 20% 合法绿例（sum=total≠net）", p.returncode == 0
              and out.get("exit_code") == 0
              and den.get("total_supply_raw") == str(private + dead)
              and den.get("net_supply_raw") == str(private)
              and burn.get("raw") == str(dead),
              f"rc={p.returncode} den={den} burn={burn} {p.stdout}{p.stderr}")


def test_f03_tolerance_boundary_bigint() -> None:
    """同族变体：18 位面额大整数上，10bps 边界必须逐位精确（float 做不到）。"""
    total = 10 ** 24
    allowed = total * 10 // 10000                # 恰好 10bps = 10**21
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        make_case(d, {"0xaaa": total - allowed}, total=total, net=total)
        edge = run_scan(d)
        d2 = Path(td) / "over"
        d2.mkdir()
        make_case(d2, {"0xaaa": total - allowed - 1}, total=total, net=total)
        over = run_scan(d2)
        check("F-03/1 10bps 边界整数精确（内 PASS / 外 1 wei 即拒）",
              edge.returncode == 0 and over.returncode == 2,
              f"edge={edge.returncode} over={over.returncode} {edge.stderr}{over.stderr}")


def test_f03_overshoot_rejected() -> None:
    """失败分支：快照和超过 total 且越过容差，仍然拒（既有强度不得丢）。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        make_case(d, {"0xaaa": 200}, total=100, net=100)
        p = run_scan(d)
        check("F-03/1 快照和超发被拒", p.returncode == 2, f"rc={p.returncode} {p.stdout}")


def test_f03_tolerance_is_independent_knob() -> None:
    """闸的容差写死在本脚本，不读 supply_truth 收据里的 tolerance_bps。"""
    src = SCAN.read_text(encoding="utf-8")
    tolerance_const = getattr(dist, "SNAPSHOT_CLOSURE_TOLERANCE_BPS", None)
    reads = re.findall(r'(?:get\(\s*["\']tolerance|\[["\']tolerance)', src)
    check("F-03/1 闭合容差是独立写死的 10bps 且不读收据容差",
          tolerance_const == 10 and not reads,
          f"const={tolerance_const} 读取点={reads}")


# --------------------------------------------------------------------------
# F-03 第二层：audit_release_gate（new-analysis）交叉检查
# --------------------------------------------------------------------------

BINDING_ERROR = "分布快照未绑定对账 owner 快照"


def _p105():
    import test_review_20260804_p105 as p105
    return p105


def test_f03_gate_evm_same_total_swap() -> None:
    """原反例（EVM）：同值换仓——总和一样、owner 分配不同的快照必须被拒。"""
    p105 = _p105()
    fixture = p105.fixture
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = fixture.build_case(root, historical=False)
        for name in p105.AUDIT_ONLY:
            (root / name).unlink(missing_ok=True)
        p105.add_new_analysis_distribution(root, report)
        errors = fixture.gate.run(root, report, profile="new-analysis")
        check("F-03/2 EVM 合法案（同一份快照喂四查与分布扫描）放行",
              not errors, str(errors))

        truth = json.loads((root / "data/holders_owners.json").read_text())
        keys = sorted(truth)
        swapped = dict(truth)
        swapped[keys[0]], swapped[keys[-1]] = truth[keys[-1]], truth[keys[0]]
        alt = root / "data/holders_owners_alt.json"
        p105.write_json(alt, swapped)
        assert sum(int(x) for x in swapped.values()) == sum(int(x) for x in truth.values())
        data_map = json.loads((root / "data_map.json").read_text())
        data_map["files"].append({"path": "data/holders_owners_alt.json", "sha256": sha(alt)})
        p105.write_json(root / "data_map.json", data_map)
        from formal_ready_test_harness import run_formal_script
        proc = run_formal_script(SCAN, ["--case-dir", str(root), "--stage", "initial",
                                        "--snapshot", "data/holders_owners_alt.json"])
        assert proc.returncode == 0, proc.stdout + proc.stderr
        errors = fixture.gate.run(root, report, profile="new-analysis")
        check("F-03/2 EVM 同值换仓被拒", any(BINDING_ERROR in x for x in errors), str(errors))


def _solana_case(root: Path, owners_sha: str) -> dict:
    """只造第二层要读的两份产物：分布扫描壳＋四查 wrapper 指向 observation bundle。"""
    bundle = root / "supply_receipt.json"
    write_json(bundle, {"schema": "solana-observation-bundle/v1",
                        "holder_outputs": {"accounts": {"path": "holders_accounts.json",
                                                        "size": 1, "sha256": "a" * 64},
                                           "owners": {"path": "holders_owners.json",
                                                      "size": 2, "sha256": owners_sha}}})
    return {
        "distribution_scan.json": {"schema": "distribution-scan/v1", "stage": "initial",
                                   "input_binding": {"snapshot": {
                                       "path": "data/holders_owners.json",
                                       "sha256": "b" * 64, "size": 3}}},
        "reconciliation_report.json": {"schema": "reconciliation-report/v2",
                                       "target": {"chain": "solana", "token": "t",
                                                  "as_of_block": 1},
                                       "checks": {"supply": {"status": "PASS",
                                                             "receipt": {"path": "supply_receipt.json",
                                                                         "sha256": sha(bundle)}}}},
    }


def test_f03_gate_solana_not_skipped() -> None:
    """Solana 不跳过：绑 observation bundle 的 holder_outputs.owners sha。"""
    fn = getattr(gate, "check_distribution_snapshot_binding", None)
    if fn is None:
        check("F-03/2 Solana 分支存在", False, "audit_release_gate 缺 check_distribution_snapshot_binding")
        return
    with tempfile.TemporaryDirectory() as td:
        # 与生产一致：run() 进来就 case_dir.resolve()，这里也传解析后的真实路径
        root = Path(td).resolve()
        data = _solana_case(root, "b" * 64)
        errors: list[str] = []
        fn(root, data, "solana", errors)
        check("F-03/2 Solana 快照 sha 相符放行", not errors, str(errors))

        data = _solana_case(root, "c" * 64)
        errors = []
        fn(root, data, "solana", errors)
        check("F-03/2 Solana 同值换仓被拒", any(BINDING_ERROR in x for x in errors), str(errors))

        data = _solana_case(root, "b" * 64)
        bundle = json.loads((root / "supply_receipt.json").read_text())
        bundle["holder_outputs"].pop("owners")
        write_json(root / "supply_receipt.json", bundle)
        data["reconciliation_report.json"]["checks"]["supply"]["receipt"]["sha256"] = \
            sha(root / "supply_receipt.json")
        errors = []
        fn(root, data, "solana", errors)
        check("F-03/2 Solana bundle 缺 owners 绑定被拒", bool(errors), str(errors))


def test_f03_gate_solana_producer_field_present() -> None:
    """在场率守卫：生产者一旦改名 holder_outputs.owners，本条先红。"""
    src = (ROOT / "scripts/solana/scan_token_accounts.py").read_text(encoding="utf-8")
    check("F-03/2 Solana 生产者仍输出 holder_outputs.owners",
          'holder_outputs={"accounts": ref(accounts_out), "owners": ref(owners_out)}' in src,
          "scan_token_accounts.py 的 holder_outputs 形态已变")


# --------------------------------------------------------------------------
# F-08：validate_scan 对已记录的 upstream_receipts 逐项三验
# --------------------------------------------------------------------------

def _initial_case(td: Path, *, with_preflight=True) -> Path:
    d = td
    make_case(d, smooth(240))
    if with_preflight:
        write_json(d / "channels_preflight.json", {"schema": "channels-preflight/v1"})
    p = run_scan(d)
    assert p.returncode == 0, p.stdout + p.stderr
    return d


def test_f08_forged_records_rejected() -> None:
    """原反例：记录项换成不存在的文件／伪 sha／伪 size，全部必须拒。"""
    variants = {
        "缺件": lambda e: e.update({"path": "does-not-exist.json"}),
        "错 sha": lambda e: e.update({"sha256": "0" * 64}),
        "错 size": lambda e: e.update({"size": e["size"] + 1}),
    }
    for label, mutate in variants.items():
        with tempfile.TemporaryDirectory() as td:
            d = _initial_case(Path(td))
            scan = json.loads((d / "distribution_scan.json").read_text())
            entries = scan["input_binding"]["upstream_receipts"]
            assert entries, "夹具没记上游收据，反例失去意义"
            mutate(entries[0])
            write_json(d / "distribution_scan.json", scan)
            errors = dist.validate_scan(d, "distribution_scan.json", "initial")
            check(f"F-08 记录项{label}被拒", bool(errors), str(errors))


def test_f08_unrecorded_disk_receipt_passes() -> None:
    """合法绿例：案根有 channels_preflight.json 但 scan 记录为空 → 仍 PASS。"""
    with tempfile.TemporaryDirectory() as td:
        d = _initial_case(Path(td), with_preflight=False)
        write_json(d / "channels_preflight.json", {"schema": "channels-preflight/v1"})
        scan = json.loads((d / "distribution_scan.json").read_text())
        assert scan["input_binding"]["upstream_receipts"] == []
        errors = dist.validate_scan(d, "distribution_scan.json", "initial")
        check("F-08 磁盘有收据但 scan 未记录仍 PASS", not errors, str(errors))


def test_f08_absent_receipt_is_skipped_not_fatal() -> None:
    """记录性语义：案根没有这份收据，生产侧照常 exit 0 并记空表。"""
    with tempfile.TemporaryDirectory() as td:
        d = _initial_case(Path(td), with_preflight=False)
        scan = json.loads((d / "distribution_scan.json").read_text())
        check("F-08 收据缺席＝跳过记录不报错",
              scan["input_binding"]["upstream_receipts"] == [] and scan["exit_code"] == 0,
              str(scan["input_binding"]["upstream_receipts"]))


def test_f08_illegal_receipt_producer_rejected() -> None:
    """失败分支拆分：收据存在但非法（符号链接／指到案外）→ 生产侧 exit 2，不再静默跳过。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "case"
        d.mkdir()
        make_case(d, smooth(240))
        outside = Path(td) / "outside_preflight.json"
        write_json(outside, {"schema": "channels-preflight/v1"})
        os.symlink(outside, d / "channels_preflight.json")
        p = run_scan(d)
        check("F-08 上游收据是符号链接 → 生产侧 exit 2",
              p.returncode == 2 and "上游收据" in (p.stdout + p.stderr),
              f"rc={p.returncode} {p.stdout}{p.stderr}")


def test_f08_docs_state_record_semantics() -> None:
    """文档口径同批改：scan-schemas 必须写清"记录性收据（在场即三验）"。"""
    text = (ROOT / "references/scan-schemas.md").read_text(encoding="utf-8")
    check("F-08 scan-schemas 已改口为记录性收据在场即三验",
          "记录性收据" in text and "在场即三验" in text and "optional" in text,
          "scan-schemas.md 未同批改口")


def main() -> int:
    test_f03_snapshot_gap_rejected()
    test_f03_dead_sink_green()
    test_f03_tolerance_boundary_bigint()
    test_f03_overshoot_rejected()
    test_f03_tolerance_is_independent_knob()
    test_f03_gate_evm_same_total_swap()
    test_f03_gate_solana_not_skipped()
    test_f03_gate_solana_producer_field_present()
    test_f08_forged_records_rejected()
    test_f08_unrecorded_disk_receipt_passes()
    test_f08_absent_receipt_is_skipped_not_fatal()
    test_f08_illegal_receipt_producer_rejected()
    test_f08_docs_state_record_semantics()
    failed = [name for name, ok, _ in RESULTS if not ok]
    if failed:
        print(f"BATCH B FAIL {len(failed)}/{len(RESULTS)}: " + "; ".join(failed))
        return 1
    print(f"PASS batch B F-03/F-08 regressions {len(RESULTS)}/{len(RESULTS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
