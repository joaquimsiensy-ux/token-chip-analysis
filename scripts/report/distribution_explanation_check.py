#!/usr/bin/env python3
"""对终判异常簇执行位置、成员、数量、证据和传播五项机器检查。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import holder_distribution_scan as distribution

SCHEMA = "distribution-explanation/v1"
MEMBER_COVERAGE_MIN = 0.8
RESIDUAL_CLUSTER_PCT_MAX = 1.0
ACCEPTED = {"CONFIRMED", "WEAKENED"}


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_file(root: Path, rel: str, label: str) -> Path:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError(f"{label}路径非法: {rel!r}")
    raw = root / rel
    if raw.is_symlink():
        raise ValueError(f"{label}拒绝符号链接: {rel}")
    path = raw.resolve(); path.relative_to(root.resolve())
    if not path.is_file():
        raise ValueError(f"{label}不存在: {rel}")
    return path


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, ensure_ascii=False, indent=2); fh.write("\n")
            fh.flush(); os.fsync(fh.fileno())
        os.replace(name, path)
    except BaseException:
        if os.path.exists(name): os.unlink(name)
        raise


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sealed_paths(seal: dict) -> set[str]:
    values = {str(x.get("path")) for x in seal.get("sealed_files", []) if isinstance(x, dict)}
    values |= {str(x) for x in seal.get("claim_files", [])}
    values.add(str((seal.get("registry") or {}).get("path")))
    return {x for x in values if x and x != "None"}


def _claim_registry(case: Path, seal: dict):
    rel = str((seal.get("registry") or {}).get("path", "a4_claims.json"))
    path = safe_file(case, rel, "A4 claim registry")
    if sha(path) != (seal.get("registry") or {}).get("sha256"):
        raise ValueError("A4 claim registry 与当前 seal 哈希不符")
    obj = load(path)
    rows = obj.get("claims")
    if obj.get("schema") != "a4-claims/v2" or not isinstance(rows, list):
        raise ValueError("A4 claim registry schema/claims 非法")
    return {str(x.get("id")): x for x in rows if isinstance(x, dict)}


def evaluate(case: Path, scan_rel: str, seal_rel: str):
    scan_path = safe_file(case, scan_rel, "终判 scan")
    seal_path = safe_file(case, seal_rel, "A4 seal")
    errors = distribution.validate_scan(case, scan_rel, "final")
    scan = load(scan_path); seal = load(seal_path)
    if scan.get("verdict") != "ABNORMAL_SHAPE":
        errors.append("解释检查只接受 ABNORMAL_SHAPE 终判")
    if seal.get("schema") != "a4-seal/v4" or seal.get("verdict") != "PASS":
        errors.append("A4 seal 必须是 PASS a4-seal/v4")
    try:
        bound = ((scan.get("input_binding") or {}).get("final_bindings") or {}).get("a4_seal.json") or {}
        if bound.get("sha256") != sha(seal_path):
            errors.append("终判 scan 绑定的是过期 A4 seal")
        registry = _claim_registry(case, seal)
    except Exception as exc:
        errors.append(str(exc)); registry = {}
    verdicts = {str(x.get("id")): str(x.get("verdict", "")).upper()
                for x in seal.get("claims", []) if isinstance(x, dict)}
    sealed = _sealed_paths(seal)
    facts = case / "facts.json"; state = case / "analysis-state.json"
    results = []
    for cluster in scan.get("abnormal_clusters", []):
        cid = str(cluster.get("cluster_id")); claim_id = f"dist-{cid}"
        claim = registry.get(claim_id) or {}
        detail = claim.get("distribution_explanation") if isinstance(claim, dict) else None
        detail = detail if isinstance(detail, dict) else {}
        cluster_members = {str(x.get("owner")): int(x.get("raw"))
                           for x in cluster.get("members", []) if isinstance(x, dict)}
        explained = set(map(str, detail.get("members") or []))
        alien = sorted(explained - set(cluster_members))
        covered = explained & set(cluster_members)
        coverage = len(covered) / len(cluster_members) if cluster_members else 0.0
        explained_raw = sum(cluster_members[x] for x in covered)
        cluster_raw = int(cluster.get("raw_balance", 0))
        residual_raw = cluster_raw - explained_raw
        residual_pct = residual_raw * 100.0 / cluster_raw if cluster_raw else 100.0
        position_ok = (claim_id in registry and verdicts.get(claim_id) in ACCEPTED
                       and cid in set(map(str, detail.get("cluster_ids") or []))
                       and bool(covered))
        members_ok = not alien and coverage >= MEMBER_COVERAGE_MIN
        quantity_ok = (str(explained_raw) == str(detail.get("explained_raw"))
                       and residual_raw >= 0 and residual_pct <= RESIDUAL_CLUSTER_PCT_MAX)
        evidence_refs = detail.get("evidence_refs") or []
        evidence_ok = bool(evidence_refs)
        for rel in evidence_refs:
            try:
                safe_file(case, rel, "解释证据")
                if rel not in sealed:
                    evidence_ok = False
            except ValueError:
                evidence_ok = False
        propagation = detail.get("propagation") or {}
        propagation_ok = (facts.is_file() and state.is_file()
                          and propagation.get("facts_sha256") == sha(facts)
                          and propagation.get("analysis_state_sha256") == sha(state)
                          and "facts.json" in sealed and "analysis-state.json" in sealed)
        checks = {"position": position_ok, "members": members_ok, "quantity": quantity_ok,
                  "evidence": evidence_ok, "propagation": propagation_ok}
        results.append({"cluster_id": cid, "claim_id": claim_id, "checks": checks,
                        "member_coverage": coverage, "alien_members": alien,
                        "explained_raw": str(explained_raw), "residual_raw": str(residual_raw),
                        "residual_cluster_pct": residual_pct,
                        "verdict": "EXPLAINED" if all(checks.values()) else "UNEXPLAINED"})
    verdict = "EXPLAINED" if results and all(x["verdict"] == "EXPLAINED" for x in results) \
        and not errors else "UNEXPLAINED"
    return {"schema": SCHEMA, "generated_at_utc": utcnow(), "verdict": verdict,
            "scan": {"path": scan_rel, "sha256": sha(scan_path)},
            "a4_seal": {"path": seal_rel, "sha256": sha(seal_path)},
            "thresholds": {"member_coverage_min": MEMBER_COVERAGE_MIN,
                           "residual_cluster_pct_max": RESIDUAL_CLUSTER_PCT_MAX},
            "cluster_results": results, "errors": errors}


def validate_explanation(case: Path, explanation_rel: str) -> list[str]:
    errors = []
    try:
        path = safe_file(case, explanation_rel, "解释产物")
        obj = load(path)
        if obj.get("schema") != SCHEMA:
            return ["解释产物 schema 非 distribution-explanation/v1"]
        rebuilt = evaluate(case, (obj.get("scan") or {}).get("path"),
                           (obj.get("a4_seal") or {}).get("path"))
        for key in ("verdict", "scan", "a4_seal", "thresholds", "cluster_results", "errors"):
            if obj.get(key) != rebuilt.get(key):
                errors.append(f"解释产物 {key} 与独立重验不一致")
    except Exception as exc:
        errors.append(f"解释产物不可重验: {exc}")
    return errors


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["validate"]:
        argv.pop(0); ap = argparse.ArgumentParser()
        ap.add_argument("--case-dir", required=True); ap.add_argument("--explanation", required=True)
        a = ap.parse_args(argv); errors = validate_explanation(Path(a.case_dir).resolve(), a.explanation)
        if errors:
            print("BLOCK: distribution explanation validate")
            for item in errors: print(f"- {item}")
            return 2
        print("PASS: distribution explanation 独立重验一致"); return 0
    ap = argparse.ArgumentParser(description="分布异常解释五判据机器检查")
    ap.add_argument("--case-dir", required=True); ap.add_argument("--scan", required=True)
    ap.add_argument("--a4-seal", default="a4_seal.json"); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv); case = Path(a.case_dir).resolve()
    try:
        out = evaluate(case, a.scan, a.a4_seal); atomic_json(case / a.out, out)
    except Exception as exc:
        print(f"BLOCK: explanation check: {exc}", file=sys.stderr); return 2
    if out["verdict"] != "EXPLAINED":
        print("BLOCK: distribution UNEXPLAINED")
        for item in out["errors"]: print(f"- {item}")
        return 2
    print("PASS: distribution EXPLAINED"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
