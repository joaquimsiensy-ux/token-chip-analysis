#!/usr/bin/env python3
"""2026-08-13 修复批 A：F-01/F-02 先红后绿回归。"""
from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "scripts/lib"),
    str(ROOT / "scripts/report"),
    str(ROOT / "scripts/evm"),
    str(ROOT / "scripts/tests"),
]

import accounting_gate  # noqa: E402
import shared_release_receipt as shared  # noqa: E402
import supply_truth_gate as supply  # noqa: E402


TOKEN = "0x" + "9" * 40
TARGET = {"chain": "eth", "token": TOKEN, "as_of_block": 123}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_ref(root: Path, name: str) -> dict:
    path = root / name
    return {"path": name, "size": path.stat().st_size, "sha256": sha256(path)}


@contextlib.contextmanager
def chdir(path: Path):
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


class SupplyPool:
    def __init__(self, total_supply: int):
        self.total_supply = total_supply

    def call(self, method, params):
        assert method == "eth_call", (method, params)
        return {"ok": True, "result": hex(self.total_supply)}


class SinkPool(SupplyPool):
    """形态②用：totalSupply 之外还批量吐 ZERO/dead 两个 sink 的冻结块余额。"""

    def __init__(self, total_supply: int, zero_balance: int, dead_balance: int):
        super().__init__(total_supply)
        self.zero_balance = zero_balance
        self.dead_balance = dead_balance

    def call_many(self, calls):
        assert len(calls) == 3, calls
        return [{"ok": True, "result": hex(value)} for value in
                (self.total_supply, self.zero_balance, self.dead_balance)]


# 夹具固定跑 mint=1/burn=0 对链上 100 → decide() 算出的实际偏差恒为 9900.0bps。
FIXTURE_DIFF_BPS = 9900.0


def write_waiver(root: Path, *, approved=10000, observed=FIXTURE_DIFF_BPS,
                 mutate=None) -> Path:
    (root / "evidence.txt").write_text("human adjudication evidence\n", encoding="utf-8")
    waiver = {
        "schema": "tolerance-waiver/v1",
        "approved_tolerance_bps": approved,
        "approved_by": "risk-committee@example.test",
        "user_decided_at_utc": "2026-08-13T12:00:00Z",
        "observed_diff_bps": observed,
        "target": dict(TARGET),
        "replay_stats": file_ref(root, "replay_stats.json"),
        "evidence_refs": [file_ref(root, "evidence.txt")],
        "reason": "特殊迁移币已人工核对，批准本次供给真值容差。",
    }
    if mutate:
        mutate(waiver)
    path = root / "waiver.json"
    path.write_text(json.dumps(waiver, ensure_ascii=False), encoding="utf-8")
    return path


def run_supply(root: Path, *, tolerance=10000, waiver: Path | None = None,
               exploration=False):
    stats = root / "replay_stats.json"
    stats.write_text(json.dumps({"mint_total_raw": "1", "burn_total_raw": "0"}),
                     encoding="utf-8")
    out = root / "supply_truth.json"
    argv = [
        "--chain", "eth", "--token", TOKEN, "--as-of-block", "123",
        "--rpc", "offline://fixture", "--tolerance-bps", str(tolerance),
        "--out", str(out),
    ]
    if exploration:
        argv += ["--exploration", "--replay-net-raw", "1"]
    else:
        argv += ["--replay-stats", "replay_stats.json"]
    if waiver is not None:
        argv += ["--tolerance-waiver", str(waiver)]
    stderr = __import__("io").StringIO()
    with chdir(root), mock.patch.object(
            supply, "attested_rpc_pool", return_value=SupplyPool(100)), \
            contextlib.redirect_stderr(stderr):
        try:
            rc = supply.main(argv)
        except SystemExit as exc:
            rc = int(exc.code or 0)
    receipt = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
    return rc, receipt, stderr.getvalue()


def expect_waiver_rejection(root: Path, mutate, needle: str):
    stats = root / "replay_stats.json"
    stats.write_text(json.dumps({"mint_total_raw": "1", "burn_total_raw": "0"}),
                     encoding="utf-8")
    waiver = write_waiver(root, mutate=mutate)
    rc, receipt, stderr = run_supply(root, waiver=waiver)
    assert rc == 2 and receipt is None, (rc, receipt, stderr)
    assert needle.lower() in stderr.lower(), stderr


def supply_item(root: Path, name: str = "supply_truth.json") -> dict:
    path = root / name
    return {"status": "PASS", "exit_code": 0,
            "receipt": {"path": name, "size": path.stat().st_size,
                        "sha256": sha256(path)}}


def expect_check_rejection(root: Path, needle, family: str = "evm"):
    needles = (needle,) if isinstance(needle, str) else tuple(needle)
    try:
        shared.validate_reconciliation_check(root, "supply_truth", supply_item(root),
                                             TARGET, family)
    except ValueError as exc:
        assert any(n.lower() in str(exc).lower() for n in needles), (needles, exc)
        return str(exc)
    raise AssertionError(f"消费侧放行了应被拒的收据：{needles}")


def consumer_case(root: Path, *, mutate=None, approved=10000,
                  observed=FIXTURE_DIFF_BPS, prepare=None):
    """先用一张合法 waiver 跑通 producer，再把案根里的 waiver 换成变异版，
    并把收据 inputs 的 size/sha 重新绑到新实物上。

    重绑这一步是关键：不重绑的话，拦下变异的是既有的 receipt_validate 掉包校验，
    根本轮不到消费侧这批新校验出手——F-C 指出的正是这种"看着有测其实没测"。
    """
    (root / "replay_stats.json").write_text(
        json.dumps({"mint_total_raw": "1", "burn_total_raw": "0"}), encoding="utf-8")
    waiver = write_waiver(root)
    rc, receipt, stderr = run_supply(root, waiver=waiver)
    assert rc == 0 and receipt is not None, (rc, stderr)
    if prepare is not None:
        prepare(root)
    write_waiver(root, approved=approved, observed=observed,
                 mutate=(lambda body: mutate(body, root)) if mutate else None)
    bound = receipt["inputs"]["tolerance_waiver"]
    bound["size"] = waiver.stat().st_size
    bound["sha256"] = sha256(waiver)
    (root / "supply_truth.json").write_text(
        json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
    return receipt


def test_f01_no_code_failure_receipt_keeps_tip():
    class NoCodeRpc:
        n_calls = 0

        def call(self, method, params):
            self.n_calls += 1
            if method == "eth_blockNumber":
                return hex(100)
            if method == "eth_getCode":
                return "0x"
            raise AssertionError((method, params))

    with tempfile.TemporaryDirectory(prefix="batch-a-f01-no-code-", dir="/private/tmp") as raw:
        root = Path(raw)
        out = root / "accounting_mode.json"
        argv = ["accounting_gate.py", "--chain", "eth", "--token", TOKEN,
                "--rpc", "offline://fixture", "--as-of-block", "1",
                "--out", str(out)]
        with mock.patch.object(accounting_gate, "Rpc", return_value=NoCodeRpc()), \
                mock.patch.object(accounting_gate.os.path, "exists", return_value=False), \
                mock.patch.object(sys, "argv", argv):
            try:
                accounting_gate.main()
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("无代码失败路径没有退出")
        receipt = json.loads(out.read_text(encoding="utf-8"))
        assert receipt["as_of_block"] == 1
        assert receipt["tip_block"] == 100
        assert receipt["model_probe_block"] == 100


def _retarget_evm_case(root: Path, as_of: int, tip: int | None):
    accounting = json.loads((root / "accounting_mode.json").read_text())
    accounting["as_of_block"] = as_of
    accounting["model_probe_block"] = tip
    if tip is None:
        accounting.pop("tip_block", None)
    else:
        accounting["tip_block"] = tip
    (root / "accounting_mode.json").write_text(json.dumps(accounting), encoding="utf-8")

    target = {"chain": "bsc", "token": "0xtoken", "as_of_block": as_of}
    recon = json.loads((root / "reconciliation_report.json").read_text())
    recon["target"] = target
    for item in recon["checks"].values():
        receipt_path = root / item["receipt"]["path"]
        receipt = json.loads(receipt_path.read_text())
        receipt["target"] = target
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        item["receipt"]["sha256"] = sha256(receipt_path)
    (root / "reconciliation_report.json").write_text(json.dumps(recon), encoding="utf-8")
    adversarial = json.loads((root / "adversarial_review.json").read_text())
    adversarial["target"] = target
    (root / "adversarial_review.json").write_text(json.dumps(adversarial), encoding="utf-8")


def test_f01_shared_evm_timing_and_legal_dual_time():
    from test_audit_release_gate import build_case

    with tempfile.TemporaryDirectory(prefix="batch-a-f01-missing-tip-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_case(root, historical=False)
        _retarget_evm_case(root, 123, None)
        try:
            shared.validate_sources(root)
        except ValueError as exc:
            assert "tip_block" in str(exc), exc
        else:
            raise AssertionError("缺 tip_block 的 EVM accounting 收据被接受")

    with tempfile.TemporaryDirectory(prefix="batch-a-f01-inverted-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_case(root, historical=False)
        _retarget_evm_case(root, 101, 100)
        try:
            shared.validate_sources(root)
        except ValueError as exc:
            assert "tip_block" in str(exc), exc
        else:
            raise AssertionError("EVM as_of_block > tip_block 被接受")

    with tempfile.TemporaryDirectory(prefix="batch-a-f01-legal-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_case(root, historical=False)
        _retarget_evm_case(root, 1, 100)
        assert shared.validate_sources(root)["as_of_block"] == 1


def test_f01_solana_not_subject_to_tip_check():
    from test_r9_batch3_release_guards import (
        AccountingPassed, build_case, validate_accounting_prefix,
    )

    with tempfile.TemporaryDirectory(prefix="batch-a-f01-solana-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_case(root)
        accounting = json.loads((root / "accounting_mode.json").read_text())
        accounting.pop("tip_block", None)
        accounting.pop("model_probe_block", None)
        (root / "accounting_mode.json").write_text(json.dumps(accounting), encoding="utf-8")
        try:
            validate_accounting_prefix(shared, root)
        except AccountingPassed:
            pass
        else:
            raise AssertionError("Solana accounting 被错误套用 EVM tip_block 检查")


def test_f02_formal_cap_and_exploration():
    with tempfile.TemporaryDirectory(prefix="batch-a-f02-cap-", dir="/private/tmp") as raw:
        rc, receipt, stderr = run_supply(Path(raw))
        assert rc == 2 and receipt is None, (rc, receipt, stderr)
    with tempfile.TemporaryDirectory(prefix="batch-a-f02-negative-", dir="/private/tmp") as raw:
        rc, receipt, stderr = run_supply(Path(raw), tolerance=-1)
        assert rc == 2 and receipt is None and "0 <=" in stderr, (rc, receipt, stderr)
    with tempfile.TemporaryDirectory(prefix="batch-a-f02-explore-", dir="/private/tmp") as raw:
        rc, receipt, stderr = run_supply(Path(raw), exploration=True)
        assert rc == 0 and receipt["verdict"] == "PASS", (rc, receipt, stderr)


def test_f02_waiver_negatives_and_failures():
    variants = [
        (lambda w: w.pop("approved_by"), "必填"),
        (lambda w: w.update(approved_tolerance_bps=9999), "批准"),
        (lambda w: w["target"].update(token="0xwrong"), "target"),
        (lambda w: w["replay_stats"].update(sha256="0" * 64), "replay_stats"),
        (lambda w: w["evidence_refs"][0].update(sha256="0" * 64), "evidence"),
    ]
    for index, (mutate, needle) in enumerate(variants):
        with tempfile.TemporaryDirectory(
                prefix=f"batch-a-f02-waiver-{index}-", dir="/private/tmp") as raw:
            expect_waiver_rejection(Path(raw), mutate, needle)

    with tempfile.TemporaryDirectory(prefix="batch-a-f02-missing-", dir="/private/tmp") as raw:
        root = Path(raw)
        rc, receipt, stderr = run_supply(root, waiver=root / "missing.json")
        assert rc == 2 and receipt is None and "不存在" in stderr, (rc, stderr)

    with tempfile.TemporaryDirectory(prefix="batch-a-f02-json-", dir="/private/tmp") as raw:
        root = Path(raw)
        broken = root / "broken.json"
        broken.write_text("{broken", encoding="utf-8")
        rc, receipt, stderr = run_supply(root, waiver=broken)
        assert rc == 2 and receipt is None and "JSON" in stderr, (rc, stderr)


def test_f02_valid_waiver_and_shared_recompute():
    with tempfile.TemporaryDirectory(prefix="batch-a-f02-valid-", dir="/private/tmp") as raw:
        root = Path(raw)
        (root / "replay_stats.json").write_text(
            json.dumps({"mint_total_raw": "1", "burn_total_raw": "0"}), encoding="utf-8")
        waiver = write_waiver(root)
        rc, receipt, stderr = run_supply(root, waiver=waiver)
        assert rc == 0 and receipt["verdict"] == "PASS", (rc, receipt, stderr)
        assert "tolerance_waiver" in receipt["inputs"]
        item = {"status": "PASS", "exit_code": 0,
                "receipt": {"path": "supply_truth.json", "size": (root / "supply_truth.json").stat().st_size,
                            "sha256": sha256(root / "supply_truth.json")}}
        shared.validate_reconciliation_check(root, "supply_truth", item, TARGET, "evm")

        without_waiver = json.loads(json.dumps(receipt))
        without_waiver["inputs"].pop("tolerance_waiver")
        (root / "supply_truth.json").write_text(json.dumps(without_waiver), encoding="utf-8")
        item["receipt"]["size"] = (root / "supply_truth.json").stat().st_size
        item["receipt"]["sha256"] = sha256(root / "supply_truth.json")
        try:
            shared.validate_reconciliation_check(root, "supply_truth", item, TARGET, "evm")
        except ValueError as exc:
            assert "waiver" in str(exc).lower(), exc
        else:
            raise AssertionError("共享校验接受了未绑定 waiver 的高容差收据")

        receipt["tolerance_bps"] = 10
        (root / "supply_truth.json").write_text(json.dumps(receipt), encoding="utf-8")
        item["receipt"]["size"] = (root / "supply_truth.json").stat().st_size
        item["receipt"]["sha256"] = sha256(root / "supply_truth.json")
        try:
            shared.validate_reconciliation_check(root, "supply_truth", item, TARGET, "evm")
        except ValueError as exc:
            assert "重算" in str(exc), exc
        else:
            raise AssertionError("共享校验接受了与重算值矛盾的 primary_verdict")


def test_f02_waiver_swap_integrity_counterexample():
    script = (ROOT / "maintenance/repair-20260813-sixlens/counterexamples"
              / "waiver_swap_integrity.py")
    completed = subprocess.run(
        [sys.executable, str(script)], cwd=ROOT, text=True,
        capture_output=True, check=False,
    )
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    # 变长替换命中 size 一项；等长替换（字节数分毫不差）只能由 sha256 拦下。
    assert "input tolerance_waiver size mismatch" in completed.stdout, completed.stdout
    assert "input tolerance_waiver hash mismatch" in completed.stdout, completed.stdout


def test_f02_tolerance_cap_uses_producer_constant():
    assert (shared.FORMAL_TOLERANCE_BPS_MAX
            == supply.FORMAL_TOLERANCE_BPS_MAX)


def test_fc_producer_waiver_field_level_negatives():
    """F-C：补上只打中"必填组"、绕过字段级校验的两处生产侧漏网（M8/M9）。"""
    variants = [
        ("approved_by 是全空白串", lambda w: w.update(approved_by="   "), "approved_by"),
        ("user_decided_at_utc 少了 Z",
         lambda w: w.update(user_decided_at_utc="2026-08-13T12:00:00"),
         "user_decided_at_utc"),
        ("user_decided_at_utc 是不存在的日期",
         lambda w: w.update(user_decided_at_utc="2026-13-45T00:00:00Z"),
         "user_decided_at_utc"),
        # F-E：裁决人签字时看到的偏差这一项，生产侧同样要拦
        ("必填缺 observed_diff_bps", lambda w: w.pop("observed_diff_bps"), "必填"),
        ("observed_diff_bps 不是数值",
         lambda w: w.update(observed_diff_bps="很大"), "observed_diff_bps"),
        ("本次实际偏差超过裁决人看到的偏差",
         lambda w: w.update(observed_diff_bps=FIXTURE_DIFF_BPS - 1), "observed_diff_bps"),
        ("人工核对证据就是 replay_stats 自身",
         lambda w: w.update(evidence_refs=[dict(w["replay_stats"])]),
         "replay_stats 输入自身"),
    ]
    for index, (label, mutate, needle) in enumerate(variants):
        with tempfile.TemporaryDirectory(
                prefix=f"batch-a-fc-producer-{index}-", dir="/private/tmp") as raw:
            expect_waiver_rejection(Path(raw), mutate, needle), label


def test_fc_consumer_side_waiver_negatives():
    """F-C：反例一份喂两侧——生产侧那 5 条在消费侧重跑，外加消费侧独有的几条。"""
    def write_other_stats(root: Path):
        (root / "other_stats.json").write_text(
            json.dumps({"mint_total_raw": "1", "burn_total_raw": "0"}), encoding="utf-8")

    variants = [
        # 变异编号对应审查者 exp_c2_mutation.py 的 M10–M18
        ("M18 必填组缺 approved_by", lambda w, r: w.pop("approved_by"), None,
         {}, "required fields incomplete"),
        ("M10 approved_by 全空白串", lambda w, r: w.update(approved_by="   "), None,
         {}, "approved_by invalid"),
        ("M11 user_decided_at_utc 少了 Z",
         lambda w, r: w.update(user_decided_at_utc="2026-08-13T12:00:00"), None,
         {}, "user_decided_at_utc invalid"),
        ("M12 waiver target 与本次不全等",
         lambda w, r: w["target"].update(token="0xwrong"), None,
         {}, "target mismatch"),
        ("M15 schema 名写错",
         lambda w, r: w.update(schema="tolerance-waiver/v2"), None,
         {}, "schema invalid"),
        ("M16 批准容差低于收据实际容差", None, None,
         {"approved": 9999}, "exceeds waiver approved_tolerance_bps"),
        ("M14 waiver 的 replay_stats 指向另一份文件",
         lambda w, r: w.update(replay_stats=file_ref(r, "other_stats.json")),
         write_other_stats, {}, "does not bind receipt input"),
        ("M13 evidence sha 改错",
         lambda w, r: w["evidence_refs"][0].update(sha256="0" * 64), None,
         {}, "evidence_refs[0] sha256 mismatch"),
        ("replay_stats sha 改错",
         lambda w, r: w["replay_stats"].update(sha256="0" * 64), None,
         {}, "replay_stats sha256 mismatch"),
        ("F-E 必填缺 observed_diff_bps",
         lambda w, r: w.pop("observed_diff_bps"), None,
         {}, "required fields incomplete"),
        ("F-E 实际偏差超过裁决人看到的偏差", None, None,
         {"observed": FIXTURE_DIFF_BPS - 1}, "实际偏差超过"),
        ("F-E 证据就是 replay_stats 自身",
         lambda w, r: w.update(evidence_refs=[dict(w["replay_stats"])]), None,
         {}, "不得指向 replay_stats 输入自身"),
    ]
    for index, (label, mutate, prepare, kwargs, needle) in enumerate(variants):
        with tempfile.TemporaryDirectory(
                prefix=f"batch-a-fc-consumer-{index}-", dir="/private/tmp") as raw:
            root = Path(raw)
            consumer_case(root, mutate=mutate, prepare=prepare, **kwargs)
            expect_check_rejection(root, needle), label


def test_fa_consumer_reconciles_replay_net_against_bound_stats():
    """F-A：不碰容差、不办 waiver，只把收据自报的 replay_net 改成与链上相等。"""
    with tempfile.TemporaryDirectory(prefix="batch-a-fa-replaynet-", dir="/private/tmp") as raw:
        root = Path(raw)
        rc, receipt, stderr = run_supply(root, tolerance=10)
        assert rc == 2 and receipt["verdict"] == "FAIL", (rc, receipt, stderr)
        forged = json.loads((root / "supply_truth.json").read_text(encoding="utf-8"))
        forged.update({"replay_net": "100", "diff": "0", "diff_bps": 0.0,
                       "tolerance_bps": 0, "primary_verdict": "PASS",
                       "verdict": "PASS", "exit_code": 0})
        forged["inputs"].pop("tolerance_waiver", None)
        assert "replay_stats" in forged["inputs"]
        (root / "supply_truth.json").write_text(
            json.dumps(forged, ensure_ascii=False), encoding="utf-8")
        expect_check_rejection(root, "replay_net 与绑定 replay_stats")

    # 旧格式/解不出 mint-burn 的 stats 必须 fail-closed，而不是"没法核对就放行"。
    with tempfile.TemporaryDirectory(prefix="batch-a-fa-legacy-", dir="/private/tmp") as raw:
        root = Path(raw)
        rc, receipt, stderr = run_supply(root, tolerance=10)
        stats = root / "replay_stats.json"
        stats.write_text(json.dumps({"net_supply": "1"}), encoding="utf-8")
        receipt["inputs"]["replay_stats"].update(
            size=stats.stat().st_size, sha256=sha256(stats))
        receipt.update({"verdict": "PASS", "exit_code": 0, "primary_verdict": "PASS",
                        "tolerance_bps": 10000, "diff_bps": 9900.0})
        (root / "supply_truth.json").write_text(
            json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
        expect_check_rejection(root, "解不出 mint/burn")


def test_fa_sink_fallback_scalars_bound_to_stats():
    """F-A：形态②的 mint_total/burn_total 同样不许自报自验。"""
    stats_doc = {"mint_total_raw": "100", "burn_total_raw": "40",
                 "zero_event_inflow_wei": "25", "dead_event_inflow_wei": "15",
                 "dead_event_outflow_wei": "0", "dead_sink_net_wei": "15"}

    def run_sink(root: Path):
        (root / "replay_stats.json").write_text(json.dumps(stats_doc), encoding="utf-8")
        out = root / "supply_truth.json"
        argv = ["--chain", "eth", "--token", TOKEN, "--as-of-block", "123",
                "--rpc", "offline://fixture", "--tolerance-bps", "10",
                "--replay-stats", "replay_stats.json", "--out", str(out)]
        with chdir(root), mock.patch.object(
                supply, "attested_rpc_pool", return_value=SinkPool(100, 25, 15)):
            rc = supply.main(argv)
        return rc, json.loads(out.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="batch-a-fa-sink-ok-", dir="/private/tmp") as raw:
        root = Path(raw)
        rc, receipt = run_sink(root)
        assert rc == 0 and receipt["decision_rule"] == "sink_fallback_form2", receipt
        # 诚实的形态②收据必须仍然放行，别把闸装成误伤。
        shared.validate_reconciliation_check(root, "supply_truth", supply_item(root),
                                             TARGET, "evm")

    with tempfile.TemporaryDirectory(prefix="batch-a-fa-sink-forged-", dir="/private/tmp") as raw:
        root = Path(raw)
        rc, receipt = run_sink(root)
        # 同步抬高 mint_total 与链上供给：形态②自身的标量闭合仍然自洽，
        # 只有对回 replay_stats 实物才看得出 mint 是编的。
        receipt.update({"mint_total": "200", "onchain_total_supply": "200"})
        (root / "supply_truth.json").write_text(
            json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
        expect_check_rejection(root, "mint_total/burn_total 与绑定 replay_stats")


def test_fb_model_probe_block_has_a_consumer():
    """F-B：时点闸不能只挂 tip_block 一个字段。"""
    from test_audit_release_gate import build_case

    delete = object()
    scenarios = [
        ("单改 tip_block：as_of=101 tip=101 而探测发生在 100", 101, 101, 100,
         "model_probe_block must equal tip_block"),
        ("删除 model_probe_block", 1, 100, delete,
         "model_probe_block missing or invalid"),
        ("model_probe_block=0 与 tip=100 自相矛盾", 1, 100, 0,
         "model_probe_block must equal tip_block"),
        ("model_probe_block 填字符串", 1, 100, "不是数字",
         "model_probe_block missing or invalid"),
    ]
    for index, (label, as_of, tip, probe, needle) in enumerate(scenarios):
        with tempfile.TemporaryDirectory(
                prefix=f"batch-a-fb-{index}-", dir="/private/tmp") as raw:
            root = Path(raw)
            build_case(root, historical=False)
            _retarget_evm_case(root, as_of, tip)
            accounting = json.loads((root / "accounting_mode.json").read_text())
            if probe is delete:
                accounting.pop("model_probe_block", None)
            else:
                accounting["model_probe_block"] = probe
            (root / "accounting_mode.json").write_text(
                json.dumps(accounting), encoding="utf-8")
            try:
                shared.validate_sources(root)
            except ValueError as exc:
                assert needle in str(exc), (label, exc)
            else:
                raise AssertionError(f"时点闸放行了：{label}")


def test_n1_replay_stats_must_live_inside_case_root():
    """N-1：不改收据里任何一个数，只把 replay_stats 改绑一份案外伪造账本。

    案外伪造件不进案目录，就不会出现在 audit_input_manifest 清单里、人工翻案子时
    也看不见——绕过的恰恰是"内容绑定"防线的全部可见性，所以必须在案根内。
    """
    with tempfile.TemporaryDirectory(prefix="batch-a-n1-outside-", dir="/private/tmp") as raw:
        root = Path(raw)
        rc, receipt, stderr = run_supply(root, tolerance=10)
        assert rc == 2 and receipt["verdict"] == "FAIL", (rc, receipt, stderr)
        with tempfile.TemporaryDirectory(
                prefix="batch-a-n1-fake-", dir="/private/tmp") as fake_raw:
            fake = Path(fake_raw) / "replay_stats.json"
            # 伪造账本自身完全自洽：mint=100 让 replay_net=100 与链上 100 对得上，
            # 收据登记的 size/sha 也照实物填，上游 validate_receipt 三验一路放行。
            fake.write_text(json.dumps({"mint_total_raw": "100", "burn_total_raw": "0"}),
                            encoding="utf-8")
            receipt["inputs"]["replay_stats"] = {
                "path": str(fake), "size": fake.stat().st_size, "sha256": sha256(fake)}
            receipt.update({"replay_net": "100", "diff": "0", "diff_bps": 0.0,
                            "tolerance_bps": 0, "primary_verdict": "PASS",
                            "verdict": "PASS", "exit_code": 0})
            receipt["inputs"].pop("tolerance_waiver", None)
            (root / "supply_truth.json").write_text(
                json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
            # 案根里那本真账原封不动，正是它该被读到的那一份。
            assert json.loads((root / "replay_stats.json").read_text())["mint_total_raw"] == "1"
            # 批 D 报错换岗（如实记录）：A-3/B-6 给全部 envelope inputs 上了统一案根约束，
            # 案外绑定被更靠前的 validate_receipt(case_root=…) 先拦（"input escapes case
            # root"）；旧闸 "_bound_replay_totals 不在当前案根内" 仍在其后兜底。两条话术
            # 给的处置指引一致（重跑生产者），同一攻击仍被拒。
            expect_check_rejection(root, ("不在当前案根内", "escapes case root"))

    # 案内软链指向案外同样进不来——这一条由**上游既有**的 receipt_validate 先拦
    # （"path is a symlink"），不是本轮新代码的功劳，如实记在这里，免得日后误以为
    # 案根约束自己扛下了软链逃逸。
    with tempfile.TemporaryDirectory(prefix="batch-a-n1-symlink-", dir="/private/tmp") as raw:
        root = Path(raw)
        rc, receipt, stderr = run_supply(root, tolerance=10)
        with tempfile.TemporaryDirectory(
                prefix="batch-a-n1-slink-", dir="/private/tmp") as fake_raw:
            fake = Path(fake_raw) / "replay_stats.json"
            fake.write_text(json.dumps({"mint_total_raw": "100", "burn_total_raw": "0"}),
                            encoding="utf-8")
            link = root / "linked_stats.json"
            link.symlink_to(fake)
            receipt["inputs"]["replay_stats"] = {
                "path": str(link), "size": link.stat().st_size, "sha256": sha256(link)}
            receipt.update({"replay_net": "100", "diff": "0", "diff_bps": 0.0,
                            "tolerance_bps": 0, "primary_verdict": "PASS",
                            "verdict": "PASS", "exit_code": 0})
            receipt["inputs"].pop("tolerance_waiver", None)
            (root / "supply_truth.json").write_text(
                json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
            expect_check_rejection(root, "symlink")


def _solana_case(case: Path, replay_mint: int):
    """跑一遍真实 Solana 生产链，返回 (bundle, 收据, target)。"""
    from test_r9_batch3_release_guards import MINT, build_case, load, write

    bundle = build_case(case)
    slot = bundle["snapshot"]["slot"]
    supply = load(ROOT / "scripts/lib/supply_truth_gate.py", "batch_a_n2_supply")
    write(case / "replay_stats.json",
          {"mint_total_raw": replay_mint, "burn_total_raw": 0})
    (case / "supply_truth.json").unlink()   # 旧 PASS 收据不许被降级覆盖，先清掉
    with chdir(case):
        rc = supply.main(["--chain", "solana", "--mint", MINT,
                          "--observation-bundle", "bundle.json",
                          "--as-of-block", str(slot),
                          "--replay-stats", "replay_stats.json",
                          "--out", "supply_truth.json"])
    receipt = json.loads((case / "supply_truth.json").read_text(encoding="utf-8"))
    target = {key: receipt["target"][key] for key in ("chain", "token", "as_of_block")}
    return rc, bundle, receipt, target


def test_n2_solana_onchain_bound_to_bundle_amount():
    """N-2 Solana 半：链上供给的实物就在同案 bundle 里，必须比一比。"""
    # 必须用模块级 shared（而不是 r9 的 shared_module()）——后者按路径重新 load，
    # 变异探针注入 sys.modules 的打断版本够不着它，会让这条测试"看着有测其实没测"。
    with tempfile.TemporaryDirectory(prefix="batch-a-n2-solana-") as raw:
        case = Path(raw).resolve()
        # 造 GNT 式局面：重放净供给 1000，bundle 实物只有 100
        rc, bundle, receipt, target = _solana_case(case, 1000)
        assert rc == 2 and receipt["verdict"] == "FAIL", (rc, receipt)
        assert str(bundle["supply"]["amount"]) == "100", bundle["supply"]

        # 伪造：只把 onchain 抬到与重放净供给相等。重放侧一个字不动，
        # 所以 F-A 的实物对账照样过，primary_verdict 重算也自洽——
        # 唯一能拆穿它的就是同案 bundle 里那个 supply.amount。
        receipt.update({"onchain_total_supply": receipt["replay_net"], "diff": "0",
                        "diff_bps": 0.0, "tolerance_bps": 0, "primary_verdict": "PASS",
                        "verdict": "PASS", "exit_code": 0})
        (case / "supply_truth.json").write_text(
            json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
        try:
            shared.validate_reconciliation_check(
                case, "supply_truth", supply_item(case), target, "solana")
        except ValueError as exc:
            assert "bundle supply amount" in str(exc), exc
        else:
            raise AssertionError("Solana 收据自报的链上供给未与 bundle 实物对账")


def test_n2_solana_honest_receipt_still_passes():
    """绿例：诚实的 Solana 收据（重放净供给恰好等于 bundle 实物）必须仍然放行。"""
    with tempfile.TemporaryDirectory(prefix="batch-a-n2-solana-ok-") as raw:
        case = Path(raw).resolve()
        rc, bundle, receipt, target = _solana_case(case, 100)
        assert rc == 0 and receipt["verdict"] == "PASS", (rc, receipt)
        shared.validate_reconciliation_check(
            case, "supply_truth", supply_item(case), target, "solana")


def test_fd_unreadable_files_all_land_on_exit_1():
    """F-D：同一类"文件读不动"故障必须走同一个退出码（检测自身失败＝1）。"""
    if os.getuid() == 0:
        print("  (skip) root 用户下 chmod 000 不生效")
        return
    codes = {}
    for label, victim in (("waiver", "waiver.json"), ("evidence", "evidence.txt")):
        with tempfile.TemporaryDirectory(
                prefix=f"batch-a-fd-{label}-", dir="/private/tmp") as raw:
            root = Path(raw)
            (root / "replay_stats.json").write_text(
                json.dumps({"mint_total_raw": "1", "burn_total_raw": "0"}),
                encoding="utf-8")
            waiver = write_waiver(root)
            target = root / victim
            os.chmod(target, 0o000)
            try:
                rc, receipt, stderr = run_supply(root, waiver=waiver)
            finally:
                os.chmod(target, 0o644)
            assert receipt is None, (label, receipt)
            assert "检测自身失败" in stderr, (label, stderr)
            codes[label] = rc
    assert codes == {"waiver": 1, "evidence": 1}, codes


def main():
    tests = [
        test_f01_no_code_failure_receipt_keeps_tip,
        test_f01_shared_evm_timing_and_legal_dual_time,
        test_f01_solana_not_subject_to_tip_check,
        test_f02_formal_cap_and_exploration,
        test_f02_waiver_negatives_and_failures,
        test_f02_valid_waiver_and_shared_recompute,
        test_f02_waiver_swap_integrity_counterexample,
        test_f02_tolerance_cap_uses_producer_constant,
        test_fc_producer_waiver_field_level_negatives,
        test_fc_consumer_side_waiver_negatives,
        test_fa_consumer_reconciles_replay_net_against_bound_stats,
        test_fa_sink_fallback_scalars_bound_to_stats,
        test_fb_model_probe_block_has_a_consumer,
        test_fd_unreadable_files_all_land_on_exit_1,
        test_n1_replay_stats_must_live_inside_case_root,
        test_n2_solana_onchain_bound_to_bundle_amount,
        test_n2_solana_honest_receipt_still_passes,
    ]
    failed = []
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - 测试汇总需继续跑完两条 finding。
            failed.append((test.__name__, f"{type(exc).__name__}: {exc}"))
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    if failed:
        print(f"BATCH A FAIL {len(failed)}/{len(tests)}")
        return 1
    print(f"PASS batch A F-01/F-02 regressions {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
