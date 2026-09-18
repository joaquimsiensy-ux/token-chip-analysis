#!/usr/bin/env python3
"""handoff_manifest 契约测试（离线，黑盒 subprocess 调 CLI）。

覆盖（split-run §2 交接契约的反例集）：
  1. READY 正例全链路：generate → verify exit 0
  2. BLOCKED 拒收：status=BLOCKED → verify exit 2；freeze 对 BLOCKED 案同拒（前置 0）
  3. 哈希漂移：产物被改 → verify exit 2；freeze 同拒（前置 0 内联 verify）
  4. schema 不兼容：consumer_min_schema 超出支持集 → verify exit 2
  5. freeze 前揭盲拒绝：--check-unseal 无 entity_freeze.json → exit 2；freeze 后 → exit 0
  6. gate 语义漂移：accounting_mode.json verdict 被改 → verify exit 2
  7. blocking 异常未解决却报 READY → verify exit 2
  8. generate READY 缺必备契约件 → exit 2
  9. receipt 追加两条且 blind_mode 跟随环境变量
 10. supersede：二次 generate 归档旧 manifest
 12. READY 缺 wave_scan_report.json 即拒（W1 漏检复盘 2026-08-01：波次扫描是 READY 必产件）
 13. wave_scan_report.json 空壳（缺 requires_adjudication 等字段）→ verify exit 2
  18+. freeze 溯源闸内容级反例集（v6.8.1 codex 复核 P0-2/P0-7 修复——旧版把空壳台账当
      正例是在给漏洞背书，本版全部翻成必拒）：v1 schema 拒／空 composition 拒／closure
      自报造假（按 composition 重算）拒／成员哈希错配拒／实体集不一致拒／敏感性不稳拒／
      与边表脱离的人工台账拒／策略明细翻转但 stable=true 拒／重放语义漂移拒／
      provenance-only 变化追加 revision／check-unseal 全绑定哈希复核／
      READY 必备件被手改出 manifest 拒／legacy receipt 机器落盘
用法：python3 scripts/tests/test_handoff_manifest.py   退出码 0=PASS / 1=FAIL
"""
import hashlib
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from test_audit_release_gate import write_deep_recon_fixtures

from formal_ready_test_harness import run_formal_script
from sqd_v4_test_fixture import (EDGE_SOURCE_BINDING, MINT, formal_cli_args,
                                 write_v4_meta)
from test_supply_truth_gate import TOKEN, write_evm_bundle

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "report", "handoff_manifest.py")
DIST_SCAN = os.path.join(HERE, "..", "report", "holder_distribution_scan.py")
FAILS = []
CHECKS = []


def check(name, cond):
    CHECKS.append(name)
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
    else:
        print(f"ok    {name}")


def run(args, env=None):
    """Run handoff inside the backward-compatible immutable registry context."""
    return run_formal_script(SCRIPT, args, env=env)


def write_json(d, name, obj):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def sol_edge_path(d):
    key = hashlib.sha256(MINT.encode("utf-8")).hexdigest()
    return os.path.join(d, "data", f"soltx-{key}.jsonl.gz")


def make_case(d, chain="eth", token=TOKEN, as_of_block=999):
    """最小合法 −1 案目录。"""
    write_json(d, "candidate_universe.json", {"candidates": [
        {"id": "c1", "address": "0xabc", "reasons": ["threshold_current"]},
        {"id": "c2", "address": "0xdef", "reasons": ["dormant"]}]})
    write_json(d, "candidate_screening.json", {"screened": [
        {"id": "c1", "observed_type": "contract", "source": "getCode", "conflict_flags": []},
        {"id": "c2", "observed_type": None, "source": None, "conflict_flags": [], "needs_adjudication": True}]})
    write_json(d, "identity_preflight.json", {"addresses": [{"address": "0xabc", "labels": [], "code": True}]})
    write_json(d, "anomalies.json", [])
    os.makedirs(os.path.join(d, "data"), exist_ok=True)
    balances = {f"owner-{i:03d}": max(1, int(2_000_000 / (1.035 ** i))) for i in range(240)}
    total = sum(balances.values())
    write_json(d, "data/holders_owners.json", balances)
    snapshot_sha = hashlib.sha256(open(os.path.join(d, "data/holders_owners.json"), "rb").read()).hexdigest()
    write_json(d, "data_map.json", {"files": [
        {"path": "data/transfers.csv", "rows": 2, "source": "test"},
        {"path": os.path.relpath(sol_edge_path(d), d), "rows": 2, "source": "test"},
        {"path": "data/holders_owners.json", "sha256": snapshot_sha, "source": "test"}]})
    with open(os.path.join(d, "data", "transfers.csv"), "w") as f:
        f.write("a,b\n1,2\n")
    edge_path = sol_edge_path(d)
    import gzip
    raw_edges = (
        json.dumps([86400, 1, 0, 0, Z, "0xabc", 100]) + "\n"
        + json.dumps([86400, 1, 1, 0, Z, "0xdef", 100]) + "\n"
    ).encode("utf-8")
    Path(edge_path).write_bytes(gzip.compress(raw_edges, mtime=0))
    edge_meta = write_v4_meta(
        edge_path, meta_path=edge_path.replace(".jsonl.gz", ".meta.json"))
    data_map = json.load(open(os.path.join(d, "data_map.json")))
    data_map["files"].append({"path": "data/" + edge_meta.name, "source": "test"})
    write_json(d, "data_map.json", data_map)
    bundle_chain = chain if chain in {"eth", "bsc", "base"} else "eth"
    bundle_path = write_evm_bundle(
        Path(d), token=token, chain=bundle_chain, as_of=as_of_block,
        total=100, zero=0, dead=0)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    write_json(d, "supply_truth.json", {"verdict": "PASS", "exit_code": 0,
                                         "chain": "bsc" if chain != "solana" else "solana",
                                         "onchain_total_supply": str(total), "replay_net": str(total),
                                         "mint_total": str(total), "burn_total": "0",
                                         "decision_rule": "primary_form1",
                                         "total_supply_raw": str(total), "net_supply_raw": str(total)})
    wave = {"schema": "wave-scan/v5",
            "edge_order_granularity": "transaction",
            "order_ambiguous": True, "non_formal": False,
            "params": ({"edges_sol": "data/soltx.jsonl.gz"} if chain == "solana"
                       else {"edges_evm_v2": "data/v2"}),
            "scan_universe_count": 0,
            "scan_universe": [], "must_adjudicate_count": 0,
            "retention_buckets": {"cleared": 0, "partial_exit": 0, "retained": 0},
            "negative_balance_addrs": 0,
            "waves": [], "equal_amount_groups": [],
            "requires_adjudication": False}
    flow = {"schema": "flow-anomaly/v3", "eligible_universe_count": 0,
            "sinks": [], "sprays": [], "requires_adjudication": False}
    if chain == "solana":
        wave["edge_source_binding"] = dict(EDGE_SOURCE_BINDING)
        flow["edge_source_binding"] = dict(EDGE_SOURCE_BINDING)
    write_json(d, "wave_scan_report.json", wave)
    write_json(d, "flow_anomaly_report.json", flow)
    write_json(d, "time_spotcheck.json", {"gate": "time_spotcheck", "schema": "time-spotcheck/v3",
                                          "points": 2, "exact_match": 2, "mismatch": 0,
                                          "rpc_err": 0, "verdict": "PASS", "exit_code": 0})
    repo = Path(HERE).parents[1]
    input_path = Path(d, "data", "holders_owners.json").resolve()

    def file_sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def repo_ref(rel):
        return {"path": rel, "sha256": file_sha(repo / rel)}

    bundle_ref = {"path": str(bundle_path.resolve()), "size": bundle_path.stat().st_size,
                  "sha256": file_sha(bundle_path)}
    write_json(d, "accounting_mode.json", {
        "schema": "accounting-gate/v2", "chain": chain, "token": token.lower(),
        "producer": repo_ref("scripts/evm/accounting_gate.py"),
        "execution_mode": "formal", "as_of_block": as_of_block,
        "tip_block": as_of_block + 20, "model_probe_block": as_of_block + 20,
        "observation_bundle": bundle_ref,
        "observed_anchor": {"block": as_of_block,
                            "block_hash": bundle["anchor"]["block_hash"]},
        "checks": {"proxy": {"is_proxy": False}, "decimals": 0},
        "verdict": "PASS", "exit_code": 0,
    })

    target = {"chain": chain, "token": token.lower(), "as_of_block": as_of_block}
    producers = {"balance": "scripts/evm/verify_recon.py",
                 "supply": "scripts/evm/verify_recon.py",
                 "supply_truth": "scripts/lib/supply_truth_gate.py",
                 "time": "scripts/lib/time_spotcheck.py"}
    bound_input = {"fixture": {"path": str(input_path), "size": input_path.stat().st_size,
                                "sha256": file_sha(input_path)}}
    # supply_truth 的 replay_stats 要能被消费侧重算 mint−burn 对账，必须是真的重放统计；
    # 文件名避开正牌 replay_stats.json，免得跟真跑出来的重放产物撞名互相覆盖。
    write_json(d, "fixture_replay_stats.json",
               {"mint_total_raw": "100", "burn_total_raw": "0"})
    stats_path = Path(d, "fixture_replay_stats.json").resolve()
    replay_input = {"path": str(stats_path), "size": stats_path.stat().st_size,
                    "sha256": file_sha(stats_path)}
    recon_v3, time_v3 = write_deep_recon_fixtures(
        Path(d), target, input_path, total=100, address="0xabc")
    stats_path = Path(d, "fixture_replay_stats.json").resolve()
    replay_input = {"path": str(stats_path), "size": stats_path.stat().st_size,
                    "sha256": file_sha(stats_path)}
    recon_checks = {}
    for key in ("balance", "supply", "supply_truth", "time"):
        receipt_name = f"reconciliation_{key}_receipt.json"
        if key in {"balance", "supply"}:
            receipt = json.loads(json.dumps(recon_v3))
        elif key == "supply_truth":
            receipt = {"schema": "supply-truth-receipt/v4", "target": target,
                       "gate": "supply_truth", "replay_net": "100",
                       "onchain_total_supply": "100", "diff": "0",
                       "diff_bps": 0.0, "tolerance_bps": 10,
                       "decision_rule": "primary_form1", "burn_form": None,
                       "primary_verdict": "PASS", "sink_reconciliation": None}
        else:
            receipt = json.loads(json.dumps(time_v3))
        # A-5（批 D）：真实 verify_recon 的 balance/supply 收据本就绑 replay_stats，
        # 夹具补成真实形态——消费侧三查同源校验（sha 全等）才有账可对。
        if key in {"balance", "supply"}:
            key_inputs = receipt["inputs"]
        elif key == "supply_truth":
            key_inputs = {"replay_stats": replay_input,
                          "observation_bundle": {
                              "path": "evm_observation_bundle.json",
                              "size": bundle_path.stat().st_size,
                              "sha256": file_sha(bundle_path)}}
        else:
            key_inputs = receipt["inputs"]
        receipt.update({"producer": repo_ref(producers[key]), "mode": "formal",
                        "inputs": key_inputs,
                        "verdict": "PASS", "exit_code": 0})
        write_json(d, receipt_name, receipt)
        recon_checks[key] = {"status": "PASS", "exit_code": 0,
                             "receipt": {"path": receipt_name,
                                         "sha256": file_sha(Path(d, receipt_name))},
                             "producer": repo_ref(producers[key])}
    write_json(d, "reconciliation_report.json", {
        "schema": "reconciliation-report/v3",
        "family": "solana" if chain == "solana" else "evm", "target": target,
        "producer": repo_ref("scripts/report/reconciliation_report.py"),
        "verdict": "PASS", "exit_code": 0, "checks": recon_checks})
    os.makedirs(os.path.join(d, "sealed"), exist_ok=True)
    with open(os.path.join(d, "sealed", "stage1_hypotheses.sealed.md"), "w") as f:
        f.write("> −2 实体冻结前禁读\n假说：无\n")
    p = subprocess.run([sys.executable, DIST_SCAN, "--case-dir", d, "--stage", "initial"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"distribution fixture 生成失败: {p.stdout}{p.stderr}")


Z = "0x0000000000000000000000000000000000000000"
GEN = ["--mode", "full", "--producer-model", "test-model", "--chain", "eth", "--contract", TOKEN,
       "--cutoff", "2026-08-01T00:00:00Z", "--frozen-block", "999",
       "--denominators", json.dumps({"total_supply_raw": str(10 ** 12)})]


def members_sha(addrs):
    return hashlib.sha256(",".join(sorted(set(addrs))).encode()).hexdigest()


def make_provenance(d, entity_map, schema="provenance-ledger/v2", stable=True,
                    hollow=False, bad_closure=False, wrong_sha=False, depth_limit=10):
    """从 manifest 绑定的真实边重跑合法台账，再按开关损坏成对应反例。"""
    entity_path = os.path.join(d, "s2_entity_members.json")
    out = os.path.join(d, ".fixture_provenance.json")
    prior = open(entity_path, "rb").read() if os.path.isfile(entity_path) else None
    write_json(d, "s2_entity_members.json", entity_map)
    trace = os.path.join(HERE, "..", "report", "entity_source_trace.py")
    labels_path = os.path.join(d, "fixture_labels.json")
    write_json(d, "fixture_labels.json", {"0xfacility": {"kind": "facility", "name": "fixture"}})
    edge_path = sol_edge_path(d)
    p = subprocess.run([sys.executable, trace, "--edges-sol", edge_path,
                        "--total-supply", str(10 ** 12), "--entity-file", entity_path,
                        "--labels-file", labels_path, "--out", out,
                        "--depth-limit", str(depth_limit)] + formal_cli_args(edge_path),
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"fixture provenance 生成失败: {p.stdout}{p.stderr}")
    obj = json.load(open(out))
    os.unlink(out)
    if prior is not None:
        with open(entity_path, "wb") as f:
            f.write(prior)
    obj["schema"] = schema
    if not stable:
        obj["bounds_sensitivity"]["conservative_vs_aggressive_verdict_stable"] = False
    for ent in obj["entities"]:
        if wrong_sha:
            ent["members_sha256"] = "0" * 64
        for anchor in ent["anchors"].values():
            if hollow:
                anchor["composition"] = []
            elif bad_closure and anchor["composition"]:
                anchor["composition"][0]["raw"] = str(max(0, int(anchor["stock_raw"]) // 2))
    return obj


def setup_freezeable(d, entity_map=None):
    """把一个已 generate READY 的案目录补齐到可 freeze：空候选裁决台账＋合法溯源台账＋名册。"""
    entity_map = entity_map if entity_map is not None else {"E1": ["0xabc"]}
    validator = os.path.join(HERE, "..", "report", "adjudication_validator.py")
    subprocess.run([sys.executable, validator, "template", "--case-dir", d, "--force"],
                   capture_output=True)
    adj = json.load(open(os.path.join(d, "candidate_adjudications.json")))
    adj["adjudicated_at"] = "2026-08-01T00:00:00Z"
    write_json(d, "candidate_adjudications.json", adj)
    write_json(d, "s2_entity_members.json", entity_map)
    write_json(d, "provenance_ledger.json", make_provenance(d, entity_map))
    write_json(d, "analysis-state.json", {"whale_groups": [
        {"id": eid, "members": v} for eid, v in entity_map.items()]})


FRZ = ["--members", "analysis-state.json", "--entity-file", "s2_entity_members.json"]


def make_dust_freeze_case(nonempty=False, total=10 * 2 ** 90,
                          denominator_key="total_supply_raw"):
    """独立合成案：真实精度损失边 → READY manifest → trace；不替换任何生产闸。"""
    import gzip
    from test_entity_source_trace import dust_precision_edges

    d = tempfile.mkdtemp(prefix="handoff_dust_")
    make_case(d)
    edge_path = sol_edge_path(d)
    rows = [json.dumps([ts, i + 1, i, 0, frm, to, amt])
            for i, (ts, frm, to, amt) in enumerate(dust_precision_edges(nonempty))]
    Path(edge_path).write_bytes(gzip.compress(("\n".join(rows) + "\n").encode(), mtime=0))
    write_v4_meta(edge_path, meta_path=edge_path.replace(".jsonl.gz", ".meta.json"))
    gen = GEN[:-2] + ["--denominators", json.dumps({denominator_key: str(total)})]
    p = run(["generate", "--case-dir", d, "--status", "READY"] + gen)
    assert p.returncode == 0, p.stdout + p.stderr
    p = run(["verify", "--case-dir", d])
    assert p.returncode == 0, p.stdout + p.stderr
    emap = {"D": ["D1", "D2"]}
    write_json(d, "s2_entity_members.json", emap)
    write_json(d, "analysis-state.json", {"whale_groups": [
        {"id": "D", "members": emap["D"]}]})
    validator = os.path.join(HERE, "..", "report", "adjudication_validator.py")
    p = subprocess.run([sys.executable, validator, "template", "--case-dir", d, "--force"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    adj = json.load(open(os.path.join(d, "candidate_adjudications.json")))
    adj["adjudicated_at"] = "2026-08-01T00:00:00Z"
    write_json(d, "candidate_adjudications.json", adj)
    write_json(d, "fixture_labels.json", {"FAC": {"kind": "facility"}})
    p = subprocess.run([sys.executable, os.path.join(HERE, "..", "report", "entity_source_trace.py"),
                        "--edges-sol", edge_path, "--total-supply", str(total),
                        "--entity-file", os.path.join(d, "s2_entity_members.json"),
                        "--labels-file", os.path.join(d, "fixture_labels.json"),
                        "--out", os.path.join(d, "provenance_ledger.json")]
                       + formal_cli_args(edge_path), capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    return d, json.load(open(os.path.join(d, "provenance_ledger.json")))


def test_dust_current_formal_freeze_replay():
    for nonempty in (False, True):
        d, ledger = make_dust_freeze_case(nonempty)
        ent = ledger["entities"][0]
        cur = ent["anchors"]["current"]
        check(f"正式 dust nonempty={nonempty} trace 保留库存及诊断构成",
              cur["stock_raw"] == ("2" if nonempty else "1")
              and [c["raw"] for c in cur["composition"]] == (["1"] if nonempty else [])
              and ent["closure_check"]["current_sum_pct"] == (50.0 if nonempty else 0.0)
              and ent["closure_check"].get("current_negligible_skipped") is True
              and cur.get("composition_usable") is False)
        before = Path(d, "provenance_ledger.json").read_bytes()
        p = run(["freeze", "--case-dir", d] + FRZ)
        check(f"正式 dust nonempty={nonempty} 完整重放 freeze exit 0",
              p.returncode == 0 and "current 锚点尘埃库存,闭合重算降级" in p.stdout
              and Path(d, "entity_freeze.json").is_file())
        if p.returncode != 0:
            print(p.stdout + p.stderr)
        check(f"正式 dust nonempty={nonempty} freeze 不改来源台账",
              Path(d, "provenance_ledger.json").read_bytes() == before)
        p = run(["freeze", "--case-dir", d, "--check-unseal"])
        check(f"正式 dust nonempty={nonempty} 封存绑定可复验", p.returncode == 0)


def test_dust_freeze_threshold_and_peak_rejection():
    # 与 trace 阈值测试相同：固定边表，仅隔离闭合门禁的分母选择；不作供应对账结论。
    d, ledger = make_dust_freeze_case(total=10001)
    p = run(["freeze", "--case-dir", d] + FRZ)
    check("freeze 库存 1 / 10001 严格阈值以下通过真实重放", p.returncode == 0)
    manifest = Path(d, "handoff_manifest.json")
    original = manifest.read_bytes()
    sealed = Path(d, "entity_freeze.json").read_bytes()
    for total in (10000, 9999, 0):
        obj = json.loads(original)
        obj["scope"]["denominators"]["total_supply_raw"] = str(total)
        write_json(d, "handoff_manifest.json", obj)
        # ledger 仍声称 10001 且 skip=True；freeze 必须按 manifest 而非自报量/标记判断。
        p = run(["freeze", "--case-dir", d] + FRZ)
        check(f"freeze manifest total={total} 无视伪造豁免 current 空构成拒",
              p.returncode == 2 and "D current 锚点库存 1 > 0 但 composition 为空" in p.stderr
              and Path(d, "entity_freeze.json").read_bytes() == sealed)
    manifest.write_bytes(original)
    bad = copy.deepcopy(ledger)
    bad["entities"][0]["anchors"]["peak"]["stock_raw"] = "1"
    bad["entities"][0]["anchors"]["peak"]["composition"] = []
    write_json(d, "provenance_ledger.json", bad)
    p = run(["freeze", "--case-dir", d] + FRZ)
    check("freeze 尘埃 peak 空构成仍拒",
          p.returncode == 2 and "D peak 锚点库存 1 > 0 但 composition 为空" in p.stderr
          and Path(d, "entity_freeze.json").read_bytes() == sealed)
    bad["entities"][0]["anchors"]["peak"]["composition"] = [
        dict(ledger["entities"][0]["anchors"]["peak"]["composition"][0], raw="2")]
    write_json(d, "provenance_ledger.json", bad)
    p = run(["freeze", "--case-dir", d] + FRZ)
    check("freeze 尘埃 peak 非空失真仍拒",
          p.returncode == 2 and "溯源闭合重算失败: D peak" in p.stderr
          and Path(d, "entity_freeze.json").read_bytes() == sealed)


def test_dust_freeze_tampering_rejected():
    d, ledger = make_dust_freeze_case(nonempty=True)
    p = run(["freeze", "--case-dir", d] + FRZ)
    assert p.returncode == 0, p.stdout + p.stderr
    sealed = Path(d, "entity_freeze.json").read_bytes()
    for attack in ("skip_marker", "composition_usable", "stock", "supply", "source_detail",
                   "policy_detail"):
        bad = copy.deepcopy(ledger)
        ent = bad["entities"][0]
        cur = ent["anchors"]["current"]
        if attack == "skip_marker":
            ent["closure_check"]["current_negligible_skipped"] = False
        elif attack == "composition_usable":
            cur["composition_usable"] = True
        elif attack == "stock":
            cur["stock_raw"] = "1"
        elif attack == "supply":
            bad["total_supply_raw"] = str(20 * 2 ** 90)
            bad["input_binding"]["total_supply_raw"] = bad["total_supply_raw"]
        elif attack == "source_detail":
            cur["composition"][0]["subkind"] = "proven_airdrop"
        else:
            bad["bounds_sensitivity"]["per_entity"]["D"]["anchors"]["current"][
                "policy_details"]["fifo"][0]["terminal"][1] = "proven_airdrop"
        write_json(d, "provenance_ledger.json", bad)
        p = run(["freeze", "--case-dir", d] + FRZ)
        reason = "total_supply 未与" if attack == "supply" else "重放语义摘要"
        check(f"尘埃 {attack} 篡改仍被绑定/真实重放拒绝",
              p.returncode == 2 and reason in (p.stdout + p.stderr)
              and Path(d, "entity_freeze.json").read_bytes() == sealed)
        if p.returncode != 2 or reason not in (p.stdout + p.stderr):
            print(p.stdout + p.stderr)
    write_json(d, "provenance_ledger.json", ledger)
    source = Path(sol_edge_path(d))
    original = source.read_bytes()
    source.write_bytes(original + b"tampered")
    p = run(["freeze", "--case-dir", d] + FRZ)
    check("尘埃原始边文件篡改仍被输入绑定拒绝",
          p.returncode == 2 and "哈希" in (p.stdout + p.stderr)
          and Path(d, "entity_freeze.json").read_bytes() == sealed)
    source.write_bytes(original)
    p = run(["freeze", "--case-dir", d] + FRZ)
    check("全部篡改恢复后 dust freeze 再次真实重放通过", p.returncode == 0)


def test_dust_freeze_supply_aliases():
    for key in ("total_supply", "supply_raw", "nominal_allocation_supply_raw"):
        d, _ = make_dust_freeze_case(denominator_key=key)
        p = run(["freeze", "--case-dir", d] + FRZ)
        check(f"尘埃 freeze 已绑定供应量别名 {key} 真实重放通过", p.returncode == 0)
        if p.returncode != 0:
            print(p.stdout + p.stderr)


def test_history_exclusion_and_hygiene():
    from contextlib import redirect_stderr
    from io import StringIO
    from unittest.mock import patch

    with tempfile.TemporaryDirectory(prefix="handoff_history_") as d:
        make_case(d)
        excluded = ["findings.md.bak_20260913", "report.md.bak",
                    "_history/old.json", "handoff_manifest.r0.superseded.json"]
        kept = ["balances_pre_launch.json", "data/labels.v3.jsonl"]
        os.makedirs(os.path.join(d, "_history"))
        for rel in excluded + kept:
            Path(d, rel).write_text("{}")
        dm = json.loads(Path(d, "data_map.json").read_text())
        dm["files"].extend({"path": rel, "source": "test"} for rel in kept)
        write_json(d, "data_map.json", dm)
        p = run(["generate", "--case-dir", d, "--status", "READY"] + GEN)
        paths = {x["path"] for x in json.loads(Path(d, "handoff_manifest.json").read_text())["artifacts"]}
        check("排除规则保持行为且不误伤 pre/v3", p.returncode == 0
              and not paths.intersection(excluded) and set(kept) <= paths)

    for mode, rel in (("data_map", "x.bak_2026"), ("include", "_history/y.json"),
                      ("gate", "_history/z.json")):
        with tempfile.TemporaryDirectory(prefix="handoff_conflict_") as d:
            make_case(d)
            Path(d, rel).parent.mkdir(exist_ok=True)
            Path(d, rel).write_text("{}")
            extra = []
            if mode == "data_map":
                dm = json.loads(Path(d, "data_map.json").read_text())
                dm["files"].append({"path": rel, "source": "test"})
                write_json(d, "data_map.json", dm)
            elif mode == "include":
                extra = ["--include", rel]
            else:
                extra = ["--gate", "custom:PASS:0:" + rel]
            p = run(["generate", "--case-dir", d, "--status", "READY"] + GEN + extra)
            print(f"显式登记 {mode}: exit={p.returncode}\n{p.stdout}{p.stderr}")
            check(f"显式登记冲突 {mode}", p.returncode == 2 and "命中排除规则" in p.stderr)

    codes = []
    for dirty in (False, True):
        with tempfile.TemporaryDirectory(prefix="handoff_hygiene_") as d:
            make_case(d)
            p = run(["generate", "--case-dir", d, "--status", "READY"] + GEN)
            check(f"卫生夹具 READY dirty={dirty}", p.returncode == 0)
            setup_freezeable(d)
            if dirty:
                Path(d, "report.md.bak_v7d_").write_text("backup")
                Path(d, "data/entity_series.v2.json").write_text("{}")
            p = run(["freeze", "--case-dir", d] + FRZ)
            codes.append(p.returncode)
            if dirty:
                print(f"卫生 freeze: exit={p.returncode}\n{p.stdout}{p.stderr}")
                check("freeze 卫生 WARN 且返回码不变", codes == [0, 0]
                      and "WARN 案根疑似历史副本 2 件" in p.stderr)
                p = run(["freeze", "--case-dir", d, "--check-unseal"])
                check("check-unseal 不扫描卫生", p.returncode == 0 and "疑似历史副本" not in p.stderr)

    sys.path.insert(0, os.path.join(HERE, "..", "report"))
    try:
        from handoff_manifest import case_hygiene_warnings
    except ImportError as e:
        print(f"ImportError: {e}")
        check("卫生扫描失败不改返回码", False)
    else:
        with tempfile.TemporaryDirectory(prefix="handoff_listdir_") as d:
            os.mkdir(os.path.join(d, "data"))
            err = StringIO()
            with redirect_stderr(err), patch("os.listdir", side_effect=PermissionError("x")):
                result = case_hygiene_warnings(d)
            check("卫生扫描失败不改返回码", result == [] and "卫生扫描跳过" in err.getvalue())
    try:
        from handoff_manifest import is_excluded_path
    except ImportError as e:
        print(f"ImportError: {e}")
        check("is_excluded_path 精确规则", False)
    else:
        for rel, want in (("a/_history/b.json", True), ("_history_x/b.json", False),
                          ("x.bak_v7d_", True), ("x.bakup.json", False),
                          ("balances_pre_launch.json", False), ("data/labels.v3.jsonl", False),
                          ("x.superseded", True)):
            check(f"is_excluded_path {rel}", bool(is_excluded_path(rel)) == want)


def test_t3_readonly_queries():
    """T3 七组黑盒契约；独立案根，所有正例复跑 audit 与去写位检查。"""
    import stat
    scratch = Path(tempfile.mkdtemp(prefix="t3-readonly-")).resolve()
    case = scratch / "case"
    case.mkdir()
    (case / "data").mkdir()
    (case / "sealed").mkdir()
    A = "0x" + "abc" * 13 + "a"
    B = "0x" + "999" * 13 + "9"
    C = "0x" + "def" * 13 + "d"
    A_UP = "0x" + A[2:].upper()
    positives = []
    modes = []

    def invoke(sub, args, error=None):
        command = [sys.executable, "-B", SCRIPT, sub, "--case-dir", str(case), *args]
        result = subprocess.run(command, capture_output=True, text=True)
        if error is None:
            check("T3 正例 " + " ".join([sub, *args]), result.returncode == 0)
            positives.append(command)
        else:
            check("T3 反例 " + " ".join([sub, *args]),
                  result.returncode == 2 and error in result.stderr)
        return result.stdout

    def inspect(args=(), file="data/identity_cards.json", error=None):
        return invoke("inspect", ["--file", file, *args], error)

    def lookup(args=(), addr=A, file="data/identity_cards.json", error=None):
        return invoke("lookup", ["--addr", addr, "--in", file, *args], error)

    def test_inspect_tree():
        out = inspect(["--limit", "1"])
        check("T3 inspect 首行、排序与第一页", out.startswith("file=data/identity_cards.json bytes=")
              and sorted([A_UP, C])[0] in out
              and out.rstrip().endswith("total=2 returned=1 truncated=true next_offset=1"))
        out = inspect(["--limit", "1", "--offset", "1"])
        check("T3 inspect 第二页", "returned=1 truncated=false next_offset=2" in out)
        out = inspect(["--offset", "5"])
        check("T3 inspect 超界空页", "returned=0 truncated=false next_offset=2" in out)
        out = inspect(["--path", A_UP + ".kind"])
        check("T3 inspect 标量", "= 'eoa'" in out and "total=1 returned=1" in out)
        out = inspect(["--path", A_UP + ".kind", "--offset", "1"])
        check("T3 inspect 标量空页", not any(line.startswith("= ") for line in out.splitlines())
              and "returned=0" in out)
        out = inspect(["--path", A_UP + ".meta", "--depth", "0"])
        check("T3 inspect depth 0 标量摘要", "k: = 1" in out and "total=1 returned=1" in out)
        shallow = inspect(["--path", A_UP, "--depth", "0"])
        deep = inspect(["--path", A_UP, "--depth", "1"])
        check("T3 inspect 深度与计数解耦", "meta: dict len=1" in shallow
              and "  k:" not in shallow and "  k: = 1" in deep
              and all("total=4 returned=4" in x for x in (shallow, deep)))
        out = inspect(["--limit", "2"], "data/balances_final.json")
        check("T3 inspect list 根分页", "[0]:" in out and "[1]:" in out and "[2]:" not in out
              and "total=3 returned=2 truncated=true next_offset=2" in out)
        out = inspect(["--path", "0.addr"], "data/balances_final.json")
        check("T3 inspect list 路径", "= " + repr(A) in out)
        for path in ("9.addr", "-1"):
            inspect(["--path", path], "data/balances_final.json", "下标")
        for option, value in (("--limit", "0"), ("--offset", "-1"), ("--depth", "-1")):
            inspect([option, value], error=option)
        inspect(["--path", "absent"], error="路径不存在: absent")

    def test_inspect_jsonl():
        out = inspect(file="data/labels.jsonl")
        check("T3 inspect JSONL 坏行继续", "total=2" in out and out.rstrip().endswith("bad_lines=1"))
        inspect(file="data/broken.json", error="读取/解析失败")
        inspect(file="data/invalid_utf8.json", error="读取/解析失败")
        inspect(file="data/addrs.txt", error="只支持 .json/.jsonl")

    def test_inspect_guard():
        for rel in ("sealed/x.json", "SEALED/x.json"):
            inspect(file=rel, error="sealed/")
        for rel in ("./sealed/x.json", "../outside.json", str(scratch / "outside.json"), "data/link.json"):
            inspect(file=rel, error="路径非法")
        inspect(file="data/nope.json", error="路径非法")
        out = inspect(file=".sealed/ok.json")
        check("T3 .sealed 合法目录不误拒", "= 1" in out)

    def test_lookup_structures():
        out = lookup(["--addr", B, "--in", "data/balances_final.json", "--in",
                      "data/entity_registry.json", "--fields", "label,balance"])
        blocks = out.split("\n" + B + "\n")
        check("T3 lookup 三文件字段", len(blocks) == 2 and "label=W1" in blocks[0]
              and "n=2" in blocks[0] and "balance=10" in blocks[0] and "balance=7" in blocks[0]
              and "data/entity_registry.json: {label=MISSING_FIELD" in blocks[0]
              and "data/identity_cards.json: MISSING" in blocks[1]
              and "data/entity_registry.json: {label=MISSING_FIELD" in blocks[1]
              and out.rstrip().endswith("total=2 returned=2 truncated=false next_offset=2 missing=0"))
        out = lookup(addr=C, file="data/entity_registry.json")
        check("T3 lookup 名册 list", "_key=E2" in out and ": MISSING" not in out)
        for addr, count in ((A, 2), (B, 1)):
            obj = json.loads(lookup(["--json"], addr=addr, file="data/mixed.json"))
            check("T3 lookup 混合来源 " + addr, len(obj["rows"][0]["hits"]["data/mixed.json"]) == count)
        lookup(file="data/keyclash.json", error="_key")
        out = lookup(file="data/labels.jsonl")
        check("T3 lookup JSONL 文本坏行计数", "bad_lines=data/labels.jsonl:1" in out)
        obj = json.loads(lookup(["--json"], file="data/labels.jsonl"))
        check("T3 lookup JSONL JSON 坏行计数", obj["bad_lines"] == {"data/labels.jsonl": 1})
        lookup(file="data/broken.json", error="读取/解析失败")
        lookup(file="data/invalid_utf8.json", error="读取/解析失败")
        lookup(file="data/addrs.txt", error="只支持 .json/.jsonl")
        obj = json.loads(lookup(["--json"], file="data/edge_records.json"))
        hits = obj["rows"][0]["hits"]["data/edge_records.json"]
        check("T3 lookup 按来源去重且双成员表", len(hits) == 3)
        obj = json.loads(lookup(["--json"], addr=B, file="data/edge_records.json"))
        check("T3 lookup 无效首字段不回退", obj["rows"][0]["hits"]["data/edge_records.json"] is None)
        for addr, found in (("SolAbC", True), ("solabc", False)):
            obj = json.loads(lookup(["--json"], addr=addr, file="data/edge_records.json"))
            check("T3 lookup 非 EVM 大小写 " + addr,
                  (obj["rows"][0]["hits"]["data/edge_records.json"] is not None) == found)

    def test_lookup_complete_json():
        obj = json.loads(invoke("lookup", ["--addr-file", "data/addrs.txt", "--in",
                              "data/identity_cards.json", "--fields", "label", "--json"]))
        record = obj["rows"][0]["hits"]["data/identity_cards.json"][0]
        check("T3 lookup 地址文件归一与完整 JSON", obj["query"] == [A, B]
              and record["label"] == "W1" and record["note"] == "x" * 100
              and record["meta"] == {"k": 1}
              and obj["rows"][1]["hits"]["data/identity_cards.json"] is None and obj["missing"] == 1)

    def test_lookup_guard_and_pages():
        for rel in ("sealed/x.json", "SEALED/x.json"):
            lookup(file=rel, error="sealed/")
        lookup(file="data/link.json", error="路径非法")
        for rel, error in (("sealed/x.json", "sealed/"), ("SEALED/x.json", "sealed/"),
                           ("data/link.txt", "路径非法"), ("./sealed/x.json", "路径非法"),
                           (str(scratch / "outside.json"), "路径非法")):
            invoke("lookup", ["--addr-file", rel, "--in", "data/identity_cards.json"], error)
        invoke("lookup", ["--in", "data/identity_cards.json"], "--addr")
        lookup(["--addr-file", "data/addrs.txt"], error="--addr-file")
        for option, value in (("--limit", "0"), ("--offset", "-1")):
            lookup([option, value], error=option)
        lookup(addr="", error="无查询地址")
        for offset, expected in ((0, "returned=1 truncated=true next_offset=1"),
                                 (1, "returned=1 truncated=false next_offset=2"),
                                 (9, "returned=0 truncated=false next_offset=2")):
            out = lookup(["--addr", B, "--limit", "1", "--offset", str(offset)])
            check("T3 lookup 分页 " + str(offset), expected in out)
        out = lookup(["--addr", A])
        check("T3 lookup 保留重复", "total=2 returned=2" in out)
        obj = json.loads(lookup(["--addr", B, "--limit", "1", "--offset", "1", "--json"]))
        check("T3 lookup JSON 全 query 与本页 missing", obj["query"] == [A, B]
              and len(obj["rows"]) == 1 and obj["missing"] == 1 and obj["next_offset"] == 2)

    def snapshot():
        result = {}
        for base, dirs, files in os.walk(case, followlinks=False):
            for path in [Path(base)] + [Path(base) / n for n in dirs + files]:
                meta = os.lstat(path)
                mode = stat.S_IMODE(meta.st_mode)
                rel = str(path.relative_to(case))
                if stat.S_ISLNK(meta.st_mode):
                    result[rel] = ("link", mode, os.readlink(path))
                elif stat.S_ISREG(meta.st_mode):
                    result[rel] = ("file", mode, hashlib.sha256(path.read_bytes()).hexdigest())
                else:
                    result[rel] = ("dir", mode)
        return result

    def test_readonly():
        wrapper = scratch / "audit_wrapper.py"
        log = scratch / "audit.json"
        wrapper.write_text(r"""import os
import sys
import json
import runpy
case_real = os.path.realpath(sys.argv[1])
log = sys.argv[2]
mode = sys.argv[3]
script = sys.argv[4]
arguments = sys.argv[5:]
events = []

def fd_path(fd):
    if sys.platform == 'darwin':
        import fcntl
        return os.fsdecode(fcntl.fcntl(fd, 50, bytes(1024)).split(b'\0', 1)[0])
    return os.readlink('/proc/self/fd/' + str(fd))

def belongs(path, dir_fd=None, access=False):
    try:
        if isinstance(path, int):
            path = fd_path(path)
        else:
            path = os.fsdecode(path)
            if not os.path.isabs(path) and dir_fd not in (None, -1):
                path = os.path.join(fd_path(dir_fd), path)
        lexical = os.path.abspath(path)
        paths = (lexical, os.path.realpath(lexical)) if access else (lexical,)
        return any(os.path.commonpath([case_real, p]) == case_real for p in paths)
    except (OSError, ValueError, TypeError):
        return None

def hook(event, args):
    paths = []
    access = False
    if event == 'open':
        path, mode, flags = args
        writes = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if not writes:
            return
        if not isinstance(path, int) and not os.path.isabs(os.fsdecode(path)):
            events.append({'event': 'open', 'args': repr(args), 'scope': '未归属写事件'})
            return
        paths, access = [(path, None)], True
    elif event in ('os.remove', 'os.unlink', 'os.rmdir'):
        paths = [(args[0], args[1] if len(args) > 1 else None)]
    elif event in ('os.rename', 'os.replace'):
        paths = [(args[0], args[2] if len(args) > 2 else None),
                 (args[1], args[3] if len(args) > 3 else None)]
    elif event in ('os.chmod', 'os.mkdir'):
        paths = [(args[0], args[2] if len(args) > 2 else None)]
    elif event == 'os.truncate':
        paths, access = [(args[0], None)], True
    elif event in ('shutil.move', 'shutil.copyfile'):
        paths, access = [(args[0], None), (args[1], None)], True
    elif event == 'shutil.rmtree':
        paths = [(args[0], args[1] if len(args) > 1 else None)]
    elif event in ('tempfile.mkstemp', 'tempfile.mkdtemp'):
        paths, access = [(args[0], None)], True
    else:
        return
    states = [belongs(path, fd, access) for path, fd in paths]
    if True in states or None in states:
        events.append({'event': event, 'args': repr(args),
                       'scope': '未归属写事件' if None in states else 'case'})

sys.addaudithook(hook)
try:
    if mode == 'selftest':
        sys.audit('open', os.path.join(case_real, 'probe'), None, os.O_WRONLY | os.O_CREAT)
        sys.audit('os.rename', os.path.join(case_real + '_sibling', 'x'), os.path.join(case_real, 'x'), -1, -1)
        sys.audit('os.remove', os.path.join(case_real, 'data/link.json'), -1)
        sys.audit('open', case_real + '_sibling/x', None, os.O_WRONLY | os.O_CREAT)
        # dir_fd、无法归属、案外链接指向案内的访问与重命名源端。
        fd = os.open(case_real, os.O_RDONLY)
        try:
            sys.audit('os.remove', 'probe', fd)
        finally:
            os.close(fd)
        sys.audit('os.remove', 'probe', -98765)
        sys.audit('open', os.path.join(os.path.dirname(case_real), 'into_case'), None, os.O_WRONLY)
        sys.audit('os.rename', os.path.join(case_real, 'x'), case_real + '_sibling/x', -1, -1)
        sys.audit('open', 'probe_rel', None, os.O_WRONLY | os.O_CREAT)
    else:
        sys.argv = [script, *arguments]
        runpy.run_path(script, run_name='__main__')
finally:
    with open(log, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False)
""", encoding="utf-8")
        p = subprocess.run([sys.executable, "-B", str(wrapper), str(case), str(log),
                            "selftest", SCRIPT], capture_output=True, text=True)
        alarms = json.loads(log.read_text())
        check("T3 audit 自检 flags/rename 目标/链接词法/相邻边界/dir_fd/未归属/realpath/源端/相对路径",
              p.returncode == 0 and len(alarms) == 8
              and [x["event"] for x in alarms[:3]] == ["open", "os.rename", "os.remove"]
              and alarms[4]["scope"] == "未归属写事件"
              and alarms[7]["event"] == "open" and alarms[7]["scope"] == "未归属写事件")
        for command in positives:
            p = subprocess.run([sys.executable, "-B", str(wrapper), str(case), str(log),
                                "run", SCRIPT, *command[3:]], capture_output=True, text=True)
            check("T3 audit 案目录零写入 " + " ".join(command[3:]),
                  json.loads(log.read_text()) == [])
            check("T3 audit 正例退出码 " + " ".join(command[3:]), p.returncode == 0)
        before = snapshot()
        try:
            for rel, entry in before.items():
                if entry[0] != "link":
                    path = case / rel
                    modes.append((path, entry[1]))
                    os.chmod(path, entry[1] & ~0o222)
            for command in positives:
                p = subprocess.run(command, capture_output=True, text=True)
                check("T3 chmod 正例 " + " ".join(command[3:]), p.returncode == 0)
        finally:
            for path, mode in modes:
                os.chmod(path, mode)
            modes.clear()
        check("T3 案目录快照完全一致", before == snapshot())

    try:
        fixtures = {
            "identity_cards.json": {A_UP: {"kind": "eoa", "label": "W1", "note": "x" * 100,
                                           "meta": {"k": 1}}, C: {"kind": "contract", "label": "P1"}},
            "balances_final.json": [{"addr": A, "balance": "10", "pct": 1.5},
                                    {"addr": B, "balance": "3", "pct": 0.2},
                                    {"addr": A, "balance": "7", "pct": 1.0}],
            "entity_registry.json": {"E1": {"members": [A, B]}, "E2": [C]},
            "mixed.json": {"rows": [{"addr": A}, {"addr": 7}, "junk"], "E1": {"members": [A, B, None, 5]}},
            "keyclash.json": {A: {"_key": "dup", "label": "x"}},
            "edge_records.json": [{"addr": A}, {"addr": A},
                                  {"addr": None, "address": B, "members": [A, A, None],
                                   "addresses": [A, "SolAbC", 9]}],
        }
        for name, value in fixtures.items():
            write_json(str(case), "data/" + name, value)
        (case / "data/labels.jsonl").write_text(
            json.dumps({"address": A, "name": "A"}) + "\n\n" +
            json.dumps({"address": B, "name": "B"}) + "\n{broken\n", encoding="utf-8")
        (case / "data/broken.json").write_text("{broken", encoding="utf-8")
        (case / "data/invalid_utf8.json").write_bytes(b'\xff')
        (case / "data/addrs.txt").write_text("# 注释\n\n" + A_UP + "\n" + B + "\n", encoding="utf-8")
        write_json(str(case), "sealed/x.json", {})
        # 在大小写敏感卷也让 SEALED 路径存在，确保测到首段 casefold。
        if not (case / "SEALED").exists():
            (case / "SEALED").mkdir()
            write_json(str(case), "SEALED/x.json", {})
        (case / ".sealed").mkdir()
        write_json(str(case), ".sealed/ok.json", 1)
        (scratch / "outside.json").write_text("{}", encoding="utf-8")
        for name in ("link.json", "link.txt"):
            (case / "data" / name).symlink_to("../../outside.json")
        (scratch / "into_case").symlink_to(case / "data/identity_cards.json")
        test_inspect_tree()
        test_inspect_jsonl()
        test_inspect_guard()
        test_lookup_structures()
        test_lookup_complete_json()
        test_lookup_guard_and_pages()
        test_readonly()
    finally:
        for path, mode in modes:
            os.chmod(path, mode)
        # 逐一删除明确路径；不使用批量目录删除。
        for base, dirs, files in os.walk(scratch, topdown=False, followlinks=False):
            for name in files:
                (Path(base) / name).unlink()
            for name in dirs:
                path = Path(base) / name
                if path.is_symlink():
                    path.unlink()
                else:
                    path.rmdir()
        scratch.rmdir()


def main():
    test_history_exclusion_and_hygiene()
    root = tempfile.mkdtemp(prefix="handoff_test_")
    try:
        # 1. READY 正例
        d = os.path.join(root, "case_ok")
        os.makedirs(d)
        make_case(d)
        p = run(["generate", "--case-dir", d, "--status", "READY"] + GEN)
        check("generate READY exit 0", p.returncode == 0)
        m = json.load(open(os.path.join(d, "handoff_manifest.json")))
        check("manifest 收录 data_map 索引文件", any(a["path"] == "data/transfers.csv" for a in m["artifacts"]))
        artifact_paths = {a["path"] for a in m["artifacts"]}
        check("EVM manifest 收录 bundle 与 transcript",
              {"evm_observation_bundle.json", "evm_observation_transcript.json"}
              <= artifact_paths)
        check("manifest sealed 只记哈希", m["sealed"] and "sha256" in m["sealed"][0])
        check("manifest 自动 gate 四个", set(m["gates"]) == {"accounting_gate", "supply_truth_gate",
                                                            "time_spotcheck", "reconciliation_checks"})
        p = run(["verify", "--case-dir", d])
        check("verify READY exit 0", p.returncode == 0)

        # accounting_gate.py 的契约明确规定 WARN + exit 0 放行（例如可升级代理）；
        # handoff 只能对 accounting_gate 接受该组合，其他自动 gate 仍须 PASS。
        dwarn = os.path.join(root, "case_accounting_warn")
        os.makedirs(dwarn)
        make_case(dwarn)
        warn_accounting = json.load(open(os.path.join(dwarn, "accounting_mode.json")))
        warn_accounting.update({"mode": "upgradeable-proxy", "verdict": "WARN",
                                "exit_code": 0})
        write_json(dwarn, "accounting_mode.json", warn_accounting)
        p = run(["generate", "--case-dir", dwarn, "--status", "READY"] + GEN)
        p_verify = run(["verify", "--case-dir", dwarn]) if p.returncode == 0 else p
        check("accounting WARN + exit 0 按记账 gate 契约放行", p_verify.returncode == 0)

        dscope = os.path.join(root, "case_scope_required"); os.makedirs(dscope); make_case(dscope)
        base_gen = ["generate", "--case-dir", dscope, "--status", "READY", "--mode", "full",
                    "--producer-model", "test-model"]
        p = run(base_gen + ["--contract", "0x0"])
        check("READY 缺 chain generate 拒", p.returncode == 2)
        p = run(base_gen + ["--chain", "bsc"])
        check("READY 缺 contract generate 拒", p.returncode == 2)
        p = run(base_gen + ["--chain", "unknown-chain", "--contract", "0x0"])
        check("READY 未知 chain generate 拒", p.returncode == 2)
        p = run(["generate", "--case-dir", dscope, "--status", "PARTIAL", "--mode", "full",
                 "--producer-model", "test-model"])
        check("PARTIAL 不强制正式 scope", p.returncode == 0)

        p = run(["generate", "--case-dir", dscope, "--status", "READY"] + GEN)
        check("scope 独立正例生成", p.returncode == 0)
        broken_scope = json.load(open(os.path.join(dscope, "handoff_manifest.json")))
        broken_scope["scope"]["chains"] = []
        write_json(dscope, "handoff_manifest.json", broken_scope)
        p = run(["verify", "--case-dir", dscope])
        check("verify 空 chains scope 拒", p.returncode == 2)

        # 14. EVM 链缺 time_spotcheck.json 拒 READY；错链 reconciliation 不得被豁免
        d14 = os.path.join(root, "case_no_spotcheck")
        os.makedirs(d14)
        make_case(d14)
        os.unlink(os.path.join(d14, "time_spotcheck.json"))
        p = run(["generate", "--case-dir", d14, "--status", "READY"] + GEN)
        check("EVM 链缺 time_spotcheck 拒 READY exit 2", p.returncode == 2)
        p = run(["generate", "--case-dir", d14, "--status", "READY", "--mode", "full",
                 "--producer-model", "test-model", "--chain", "solana", "--contract", "0x0"])
        p_verify = run(["verify", "--case-dir", d14]) if p.returncode == 0 else p
        check("solana 不得复用 bsc reconciliation", p_verify.returncode == 2)

        # READY 从本批起无条件要求 reconciliation wrapper 及四份绑定回执。
        drecon = os.path.join(root, "case_missing_reconciliation")
        os.makedirs(drecon)
        make_case(drecon)
        os.unlink(os.path.join(drecon, "reconciliation_report.json"))
        p = run(["generate", "--case-dir", drecon, "--status", "READY"] + GEN)
        check("READY 缺 reconciliation 拒", p.returncode == 2 and
              "reconciliation" in (p.stdout + p.stderr).lower())

        # 9. receipt（在正例目录顺手验）
        p = run(["receipt", "--case-dir", d, "--step", "A1", "--cmd", "collect", "--exit", "0",
                 "--artifacts", "data/transfers.csv"], env={"CHIP_BLIND_SERIAL": "1"})
        p2 = run(["receipt", "--case-dir", d, "--step", "A2", "--cmd", "recon", "--exit", "0"])
        rows = json.load(open(os.path.join(d, "stage1_receipts.json")))
        check("receipt 追加两条", p.returncode == 0 and p2.returncode == 0 and len(rows) == 2)
        check("receipt blind_mode 跟随环境", rows[0]["blind_mode"] is True and rows[1]["blind_mode"] is False)

        # 5. freeze 前揭盲拒绝 → 四重前置 → freeze → 放行
        p = run(["freeze", "--case-dir", d, "--check-unseal"])
        check("freeze 前揭盲拒绝 exit 2", p.returncode == 2)
        write_json(d, "analysis-state.json", {"whale_groups": [{"id": "E1", "members": ["0xabc"]}]})
        write_json(d, "s2_entity_members.json", {"E1": ["0xabc"]})
        p = run(["freeze", "--case-dir", d, "--members", "analysis-state.json"])
        check("freeze 缺 --entity-file 拒", p.returncode != 0)
        # v6.8.0：freeze 前置裁决闭环——先出裁决台账（候选为空 → 空台账即闭环）
        p = run(["freeze", "--case-dir", d] + FRZ + ["--pending", "c2 待裁决"])
        check("无裁决台账 freeze 拒 exit 2", p.returncode == 2)
        setup_freezeable(d)
        exploratory = json.load(open(os.path.join(d, "provenance_ledger.json")))
        exploratory["exploration"] = True
        exploratory["input_binding"]["mode"] = "exploration"
        exploratory["input_binding"]["labels_file"] = None
        write_json(d, "provenance_ledger.json", exploratory)
        p = run(["freeze", "--case-dir", d] + FRZ)
        check("exploration/null-label provenance freeze 拒", p.returncode == 2)
        write_json(d, "provenance_ledger.json", make_provenance(d, {"E1": ["0xabc"]}))
        p = run(["freeze", "--case-dir", d] + FRZ + ["--pending", "c2 待裁决"])
        if p.returncode != 0:
            print(p.stdout + p.stderr)
        check("四重前置齐备 freeze 初次 exit 0", p.returncode == 0)
        fz0 = json.load(open(os.path.join(d, "entity_freeze.json")))
        check("冻结记录绑定成员/名册/provenance/manifest/data_map 全套哈希",
              fz0.get("entity_file_sha256") and fz0.get("provenance_ledger_sha256")
              and fz0.get("members_sha256") and fz0.get("manifest_sha256")
              and fz0.get("data_map_sha256") and fz0.get("provenance_input_binding_sha256"))
        p = run(["freeze", "--case-dir", d, "--check-unseal"])
        check("freeze 后揭盲放行 exit 0", p.returncode == 0)
        # 名册变更 → 溯源台账逐实体哈希失配 → 拒；重跑溯源（fixture 同步）后 revision 放行
        write_json(d, "analysis-state.json", {"whale_groups": [{"id": "E1", "members": ["0xabc", "0xdef"]}]})
        write_json(d, "s2_entity_members.json", {"E1": ["0xabc", "0xdef"]})
        p = run(["freeze", "--case-dir", d] + FRZ)
        check("名册改动后复用旧溯源台账 freeze 拒 exit 2",
              p.returncode == 2 and "哈希不符" in (p.stderr + p.stdout))
        write_json(d, "provenance_ledger.json", make_provenance(d, {"E1": ["0xabc", "0xdef"]}))
        p = run(["freeze", "--case-dir", d] + FRZ)
        fz = json.load(open(os.path.join(d, "entity_freeze.json")))
        check("重跑溯源后 freeze 变更走 revision 追加", p.returncode == 0 and len(fz["revisions"]) == 1)

        # 10. supersede
        p = run(["generate", "--case-dir", d, "--status", "READY", "--run-id", "s1-second"] + GEN)
        arch = [f for f in os.listdir(d) if f.startswith("handoff_manifest.") and f.endswith(".superseded.json")]
        check("supersede 归档旧 manifest", p.returncode == 0 and len(arch) == 1)

        # 2. BLOCKED 拒收
        d2 = os.path.join(root, "case_blocked")
        os.makedirs(d2)
        make_case(d2)
        p = run(["generate", "--case-dir", d2, "--status", "BLOCKED_CEX_GATE",
                 "--status-reason", "CEX 黑箱超线用户中止"] + GEN)
        check("generate BLOCKED_CEX_GATE exit 0", p.returncode == 0)
        p = run(["verify", "--case-dir", d2])
        check("verify BLOCKED 拒收 exit 2", p.returncode == 2 and "READY" in p.stdout)
        # freeze 前置 0（内联 verify）：BLOCKED 案带齐全部台账也不得冻结
        setup_freezeable(d2)
        p = run(["freeze", "--case-dir", d2] + FRZ)
        check("BLOCKED 案 freeze 同拒 exit 2（前置 0 内联 verify）",
              p.returncode == 2 and "verify" in (p.stderr + p.stdout))

        # 3. 哈希漂移
        d3 = os.path.join(root, "case_drift")
        os.makedirs(d3)
        make_case(d3)
        run(["generate", "--case-dir", d3, "--status", "READY"] + GEN)
        with open(os.path.join(d3, "data", "transfers.csv"), "a") as f:
            f.write("3,4\n")
        p = run(["verify", "--case-dir", d3])
        check("哈希漂移拒收 exit 2", p.returncode == 2 and "漂移" in p.stdout)
        setup_freezeable(d3)
        p = run(["freeze", "--case-dir", d3] + FRZ)
        check("哈希漂移案 freeze 同拒 exit 2（前置 0）", p.returncode == 2)

        # 4. schema 不兼容
        d4 = os.path.join(root, "case_schema")
        os.makedirs(d4)
        make_case(d4)
        run(["generate", "--case-dir", d4, "--status", "READY"] + GEN)
        mp = os.path.join(d4, "handoff_manifest.json")
        m = json.load(open(mp))
        m["consumer_min_schema"] = "handoff/v9"
        json.dump(m, open(mp, "w"))
        p = run(["verify", "--case-dir", d4])
        check("schema 不兼容拒收 exit 2", p.returncode == 2 and "schema" in p.stdout)

        # 6. gate 语义漂移
        d6 = os.path.join(root, "case_gate")
        os.makedirs(d6)
        make_case(d6)
        run(["generate", "--case-dir", d6, "--status", "READY"] + GEN)
        write_json(d6, "accounting_mode.json", {"schema": "accounting-gate/v1", "verdict": "FAIL", "exit_code": 2})
        p = run(["verify", "--case-dir", d6])
        check("gate 语义漂移拒收 exit 2", p.returncode == 2)

        # 7. blocking 异常未解决却 READY
        d7 = os.path.join(root, "case_anom")
        os.makedirs(d7)
        make_case(d7)
        write_json(d7, "anomalies.json", [{"id": "AN-1", "severity": "high", "blocking": True,
                                           "stage": "A1", "status": "open", "evidence": "gap"}])
        run(["generate", "--case-dir", d7, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d7])
        check("blocking 异常未解决拒收 exit 2", p.returncode == 2 and "AN-1" in p.stdout)

        # 8. generate READY 缺必备件
        d8 = os.path.join(root, "case_missing")
        os.makedirs(d8)
        make_case(d8)
        os.unlink(os.path.join(d8, "candidate_universe.json"))
        p = run(["generate", "--case-dir", d8, "--status", "READY"] + GEN)
        check("READY 缺必备件 generate 即拒 exit 2", p.returncode == 2)
        p = run(["generate", "--case-dir", d8, "--status", "PARTIAL"] + GEN)
        check("同目录报 PARTIAL 可出 manifest", p.returncode == 0)

        # 11. READY 缺 gate 产物（supply_truth）即拒——A2 没跑完不得 READY
        d11 = os.path.join(root, "case_nogate")
        os.makedirs(d11)
        make_case(d11)
        os.unlink(os.path.join(d11, "supply_truth.json"))
        p = run(["generate", "--case-dir", d11, "--status", "READY"] + GEN)
        check("READY 缺 supply_truth gate 即拒 exit 2", p.returncode == 2)

        # 12. READY 缺 wave_scan_report 即拒（历史清零层波次扫描必产件）
        d12 = os.path.join(root, "case_nowave")
        os.makedirs(d12)
        make_case(d12)
        os.unlink(os.path.join(d12, "wave_scan_report.json"))
        p = run(["generate", "--case-dir", d12, "--status", "READY"] + GEN)
        check("READY 缺 wave_scan_report 即拒 exit 2", p.returncode == 2)

        # 13. wave_scan_report 空壳 → verify 拒收
        d13 = os.path.join(root, "case_wavehollow")
        os.makedirs(d13)
        make_case(d13)
        write_json(d13, "wave_scan_report.json", {"schema": "wave-scan/v5",
                                                   "edge_order_granularity": "transaction",
                                                   "order_ambiguous": True,
                                                   "non_formal": False,
                                                   "params": {"edges_evm_v2": "data/v2"}})
        run(["generate", "--case-dir", d13, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d13])
        check("wave_scan_report 空壳 verify 拒收 exit 2", p.returncode == 2 and "wave_scan_report" in p.stdout)

        # 15. READY 缺 flow_anomaly_report 即拒（v6.8.0 资金流异常扫描必产件）
        d15 = os.path.join(root, "case_noflow")
        os.makedirs(d15)
        make_case(d15)
        os.unlink(os.path.join(d15, "flow_anomaly_report.json"))
        p = run(["generate", "--case-dir", d15, "--status", "READY"] + GEN)
        check("READY 缺 flow_anomaly_report 即拒 exit 2", p.returncode == 2)

        # 16. wave-scan/v1 旧版产物 → verify 拒收并提示重跑（fail-open 修复）
        d16 = os.path.join(root, "case_wavev1")
        os.makedirs(d16)
        make_case(d16)
        write_json(d16, "wave_scan_report.json", {"schema": "wave-scan/v1", "cleared_layer_count": 0,
                                                  "waves": [], "equal_amount_groups": [],
                                                  "requires_adjudication": False})
        run(["generate", "--case-dir", d16, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d16])
        check("wave-scan/v1 旧版产物 verify 拒收 exit 2",
              p.returncode == 2 and "旧版" in p.stdout and "v5" in p.stdout)

        # 16b. wave-scan/v2 旧版产物（缺 scan_universe 逐址全集）→ verify 同拒（6.9.2）
        d16b = os.path.join(root, "case_wavev2")
        os.makedirs(d16b)
        make_case(d16b)
        write_json(d16b, "wave_scan_report.json", {"schema": "wave-scan/v2", "scan_universe_count": 0,
                                                   "waves": [], "equal_amount_groups": [],
                                                   "requires_adjudication": False})
        run(["generate", "--case-dir", d16b, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d16b])
        check("wave-scan/v2 旧版产物 verify 拒收 exit 2",
              p.returncode == 2 and "旧版" in p.stdout and "scan_universe" in p.stdout)

        # 16c. v5 标签但缺 scan_universe 逐址全集（贴标签不带货同属空壳）
        d16c = os.path.join(root, "case_wavev3hollow")
        os.makedirs(d16c)
        make_case(d16c)
        write_json(d16c, "wave_scan_report.json", {"schema": "wave-scan/v5",
                                                   "edge_order_granularity": "transaction",
                                                   "order_ambiguous": True, "non_formal": False,
                                                   "params": {"edges_evm_v2": "data/v2"},
                                                   "scan_universe_count": 3,
                                                   "waves": [], "equal_amount_groups": [],
                                                   "requires_adjudication": False})
        run(["generate", "--case-dir", d16c, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d16c])
        check("v5 标签缺 scan_universe 全集 verify 拒收 exit 2",
              p.returncode == 2 and "全集不完整" in p.stdout)

        # 16d. v5 count 与逐条标记矛盾（count=0 配 must=true 自相矛盾拒收）
        d16d = os.path.join(root, "case_wavev3contra")
        os.makedirs(d16d)
        make_case(d16d)
        write_json(d16d, "wave_scan_report.json", {
            "schema": "wave-scan/v5", "edge_order_granularity": "transaction",
            "order_ambiguous": True, "non_formal": False, "scan_universe_count": 1,
            "params": {"edges_evm_v2": "data/v2"},
            "scan_universe": [{"addr": "DormantW", "must_adjudicate": True,
                               "must_reasons": ["dormant_ge_30d"]}],
            "must_adjudicate_count": 0,
            "waves": [], "equal_amount_groups": [], "requires_adjudication": False})
        run(["generate", "--case-dir", d16d, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d16d])
        check("v5 count 与逐条 must 标记矛盾 verify 拒收 exit 2",
              p.returncode == 2 and "内部矛盾" in p.stdout)

        # 17. handoff/v1 旧 manifest：默认拒；--legacy-read-only 显式降级放行（只读警告）
        d17 = os.path.join(root, "case_legacy")
        os.makedirs(d17)
        make_case(d17)
        run(["generate", "--case-dir", d17, "--status", "READY"] + GEN)
        mp17 = os.path.join(d17, "handoff_manifest.json")
        m17 = json.load(open(mp17))
        m17["consumer_min_schema"] = "handoff/v2"
        json.dump(m17, open(mp17, "w"))
        p = run(["verify", "--case-dir", d17])
        check("handoff/v2 默认拒收 exit 2", p.returncode == 2 and "legacy-read-only" in p.stdout)
        m17["consumer_min_schema"] = "handoff/v1"
        json.dump(m17, open(mp17, "w"))
        # manifest 内容变了但其不在 artifacts 自身清单（EXCLUDE_NAMES），哈希不受影响
        p = run(["verify", "--case-dir", d17])
        check("handoff/v1 默认拒收 exit 2", p.returncode == 2 and "legacy-read-only" in p.stdout)
        p = run(["verify", "--case-dir", d17, "--legacy-read-only"])
        check("handoff/v1 --legacy-read-only 放行且带只读警告",
              p.returncode == 0 and "LEGACY READ-ONLY" in p.stdout)
        rc17 = os.path.join(d17, "legacy_readonly_receipt.json")
        check("legacy 降级落机器 receipt", os.path.isfile(rc17)
              and json.load(open(rc17)).get("schema") == "legacy-readonly-receipt/v1")
        # legacy 案 freeze 必拒（严格 v2 verify 不认 --legacy-read-only）
        setup_freezeable(d17)
        p = run(["freeze", "--case-dir", d17] + FRZ)
        check("legacy 案 freeze 必拒 exit 2", p.returncode == 2)

        test_dust_current_formal_freeze_replay()
        test_dust_freeze_threshold_and_peak_rejection()
        test_dust_freeze_tampering_rejected()
        test_dust_freeze_supply_aliases()

        # 18. freeze 溯源闸内容级反例集（v6.8.1：空壳/自报值/错哈希全部必须被内容重查打回）
        d18 = os.path.join(root, "case_provgate")
        os.makedirs(d18)
        make_case(d18)
        run(["generate", "--case-dir", d18, "--status", "READY"] + GEN)
        setup_freezeable(d18)
        emap = {"E1": ["0xabc"]}
        write_json(d18, "provenance_ledger.json", make_provenance(d18, emap, schema="provenance-ledger/v1"))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("溯源台账 v1（数学错误版）freeze 拒 exit 2",
              p.returncode == 2 and "v2" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(d18, emap, hollow=True))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("stock>0 而 composition 空壳 freeze 拒 exit 2",
              p.returncode == 2 and "空壳" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(d18, emap, bad_closure=True))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("closure 自报 100 但按 composition 重算不闭合 freeze 拒 exit 2",
              p.returncode == 2 and "重算" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(d18, emap, wrong_sha=True))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("成员集哈希错配 freeze 拒 exit 2", p.returncode == 2 and "哈希不符" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json",
                   make_provenance(d18, {"E1": ["0xabc"], "E_ghost": ["0xdef"]}))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("台账实体集与名册不一致 freeze 拒 exit 2",
              p.returncode == 2 and "实体集" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(d18, emap, stable=False))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("敏感性不稳 freeze 拒 exit 2", p.returncode == 2 and "敏感性" in (p.stderr + p.stdout))

        # high-2 核心反例：金额/成员/closure/stable 全合法、但完全没有原始数据绑定。
        # 旧 freeze 会把这类人工台账当“合法正例”；修复后必须在重放前 fail-closed。
        detached = make_provenance(d18, emap)
        detached.pop("input_binding", None)
        write_json(d18, "provenance_ledger.json", detached)
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("与边表脱离的人工合法台账 freeze 拒 exit 2",
              p.returncode == 2 and "input_binding" in (p.stderr + p.stdout))

        # stable 自报 true，但把 fifo 的策略明细主导终点改掉；freeze 必须从明细重算翻转。
        def scale_anchors(obj, k=10 ** 8):
            """把 fixture 锚点库存放大到非尘埃（v6.39.4 尘埃线后翻转判定只作用于
            ≥总供应 0.01% 的锚点；fixture 原始库存 100/1e12 属尘埃）。"""
            for ent in obj["entities"]:
                for anchor in ent["anchors"].values():
                    anchor["stock_raw"] = str(int(anchor["stock_raw"]) * k)
                    for c in anchor["composition"]:
                        c["raw"] = str(int(c["raw"]) * k)
            for s in obj["bounds_sensitivity"]["per_entity"].values():
                for a_ in (s.get("anchors") or {}).values():
                    for rows in a_["policy_details"].values():
                        for r in rows:
                            r["raw"] = str(int(r["raw"]) * k)

        fake_stable = make_provenance(d18, emap)
        scale_anchors(fake_stable)
        fa = fake_stable["bounds_sensitivity"]["per_entity"]["E1"]["anchors"]["current"]
        fa["policy_details"]["fifo"][0]["terminal"] = ["BOUNDARY", "dex_pool", "0xpool"]
        write_json(d18, "provenance_ledger.json", fake_stable)
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("策略明细翻转但 stable=true 仍由 freeze 重算拒绝",
              p.returncode == 2 and "三策略主导终点翻转" in (p.stderr + p.stdout))

        # 尘埃锚点（<0.01% 供应）的明细翻转不再触发翻转拒——由重放语义摘要兜底伪造
        dust_flip = make_provenance(d18, emap)
        da = dust_flip["bounds_sensitivity"]["per_entity"]["E1"]["anchors"]["current"]
        da["policy_details"]["fifo"][0]["terminal"] = ["BOUNDARY", "dex_pool", "0xpool"]
        write_json(d18, "provenance_ledger.json", dust_flip)
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("尘埃锚点翻转豁免（不因翻转拒；伪造由重放语义摘要兜底）",
              "三策略主导终点翻转" not in (p.stderr + p.stdout)
              and p.returncode == 2 and "重放语义摘要" in (p.stderr + p.stdout))

        # closure/敏感性都保持自洽，只篡改来源类别；唯有从当前原始边重放才能识别。
        stale = make_provenance(d18, emap)
        for anchor in stale["entities"][0]["anchors"].values():
            anchor["composition"][0]["subkind"] = "proven_airdrop"
        for anchor in stale["bounds_sensitivity"]["per_entity"]["E1"]["anchors"].values():
            for rows in anchor["policy_details"].values():
                rows[0]["terminal"] = ["PROVEN_ORIGIN", "proven_airdrop", Z]
            anchor["top_by_policy"] = {p: ["PROVEN_ORIGIN", "proven_airdrop", Z]
                                        for p in ("pro_rata", "fifo", "lifo")}
        write_json(d18, "provenance_ledger.json", stale)
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("内容自洽但与当前原始边重放不一致 freeze 拒",
              p.returncode == 2 and "重放语义摘要" in (p.stderr + p.stdout))

        valid = make_provenance(d18, emap)
        write_json(d18, "provenance_ledger.json", valid)
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("台账修复后 freeze 放行 exit 0", p.returncode == 0)

        # medium-4 自然并修：成员不变，仅 provenance 参数/摘要变化也必须追加 revision。
        valid2 = make_provenance(d18, emap, depth_limit=9)
        write_json(d18, "provenance_ledger.json", valid2)
        p = run(["freeze", "--case-dir", d18] + FRZ)
        fz18 = json.load(open(os.path.join(d18, "entity_freeze.json")))
        check("仅 provenance 变化也追加 freeze revision",
              p.returncode == 0 and len(fz18["revisions"]) == 1
              and fz18["provenance_ledger_sha256"] != fz18["revisions"][0]["provenance_ledger_sha256"])
        # check-unseal 不能再只看 members_sha256：当前 provenance 任一漂移都应拒揭盲。
        drifted = copy.deepcopy(valid2)
        drifted["generated_at"] = "2099-01-01T00:00:00Z"
        write_json(d18, "provenance_ledger.json", drifted)
        p = run(["freeze", "--case-dir", d18, "--check-unseal"])
        check("check-unseal 复核 provenance 当前哈希漂移并拒绝", p.returncode == 2)
        write_json(d18, "provenance_ledger.json", valid2)
        p = run(["freeze", "--case-dir", d18, "--check-unseal"])
        check("check-unseal 全绑定恢复后放行", p.returncode == 0)
        edge_path = sol_edge_path(d18)
        edge_before = open(edge_path, "rb").read()
        with open(edge_path, "ab") as f:
            f.write((json.dumps([172800, 2, 0, 0, Z, "0xabc", 1]) + "\n").encode())
        p = run(["freeze", "--case-dir", d18, "--check-unseal"])
        check("check-unseal 直接复核原始边绑定漂移并拒绝", p.returncode == 2)
        with open(edge_path, "wb") as f:
            f.write(edge_before)
        p = run(["freeze", "--case-dir", d18, "--check-unseal"])
        check("原始边恢复后 check-unseal 放行", p.returncode == 0)

        # 19. manifest artifacts 清单被手改（删掉必备件条目）→ verify 独立重算拒
        d19 = os.path.join(root, "case_handedit")
        os.makedirs(d19)
        make_case(d19)
        run(["generate", "--case-dir", d19, "--status", "READY"] + GEN)
        mp19 = os.path.join(d19, "handoff_manifest.json")
        m19 = json.load(open(mp19))
        m19["artifacts"] = [x for x in m19["artifacts"] if x["path"] != "wave_scan_report.json"]
        json.dump(m19, open(mp19, "w"))
        p = run(["verify", "--case-dir", d19])
        check("手改 manifest 摘掉必备件 verify 拒 exit 2",
              p.returncode == 2 and "必备件" in p.stdout)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    test_t3_readonly_queries()

    print("=" * 40)
    if FAILS:
        print(f"{len(FAILS)} 项失败: {FAILS}")
        return 1
    print(f"handoff_manifest 契约测试全部通过（{len(CHECKS)} 项）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
