#!/usr/bin/env python3
"""批 D（六视角修复工程收口批）回归：F-07 真事务／GPT-F-06 审计收口／F-06 裁决收据链／
台账项 A-1・A-3・A-5・B-1・B-2・B-4・B-5・B-7。

纪律（批 A/B/C 沉淀）：原反例先红后绿；夹具含真实产物形态；fail-closed 分支逐条定向红线；
F-07 注入反例断言**所有已写文件字节回滚原样**（不是只断言报错干净）。
用法：python3 scripts/tests/test_repair_batch_d.py    退出码 0=PASS / 1=FAIL
"""
from __future__ import annotations

import contextlib
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path[:0] = [str(HERE), str(HERE.parent / "report"), str(HERE.parent / "lib"),
                str(HERE.parent / "evm"), str(HERE.parent / "solana")]
from sqd_v4_test_fixture import EDGE_SOURCE_BINDING, formal_cli_args

FAILS: list[str] = []


def check(name, cond, detail=""):
    if cond:
        print(f"ok    {name}")
    else:
        print(f"FAIL  {name}  {detail}")
        FAILS.append(name)


def sha_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


# ---------------------------------------------------------------- F-07 真事务

def t_f07_refresh_transaction():
    """F-07：多 manifest 迁移必须全有或全无——注入 OSError 后字节回滚原样。"""
    import fetch_hypersync_v2 as fh
    from test_apu_legacy_gaps import _make_prehistoric_v2_run

    def log_row(block):
        return (0, "0x" + "1" * 64, "0x" + "2" * 64, block,
                "0x" + format(7, "x").rjust(64, "0"),
                "0x" + "a" * 64, "0x" + "b" * 64)

    def make_two_prehistoric(root: Path):
        _make_prehistoric_v2_run(root, 0, rows=[log_row(5)],
                                 blocks=[(5, hex(1000))])
        _make_prehistoric_v2_run(root, 100, rows=[log_row(105)],
                                 blocks=[(105, hex(2000))])
        fh.recover_identity(root)
        return sorted(root.glob("run_*/done.json"))

    # 绿例：先恢复 identity，正常迁移全部升 v4。
    with tempfile.TemporaryDirectory(prefix="d-f07-green-", dir="/private/tmp") as raw:
        root = Path(raw)
        dones = make_two_prehistoric(root)
        rc = fh.refresh_manifests_cli(["--refresh-manifests", "--outdir", str(root),
                                       "--capture-from", "0"])
        upgraded = [json.loads(p.read_text())["schema"] for p in dones]
        check("F-07 绿例：太古双 run 迁移 exit 0 全升 v4",
              rc == 0 and upgraded == [fh.MANIFEST_SCHEMA] * 2
              and (root / fh.IDENTITY_NAME).is_file(), (rc, upgraded))

    # 原反例：第二个 done 提交时注入 OSError → 两个 done 字节回滚原样
    with tempfile.TemporaryDirectory(prefix="d-f07-inject-", dir="/private/tmp") as raw:
        root = Path(raw)
        dones = make_two_prehistoric(root)
        originals = {p: p.read_bytes() for p in dones}
        real_replace = os.replace
        calls = {"n": 0}

        def inject(src, dst, **kw):
            calls["n"] += 1
            # commit 序列：done1→bak(1) tmp1→done1(2) done2→bak(3) tmp2→done2(4)
            if calls["n"] == 4:
                raise OSError("disk full injected at second commit")
            return real_replace(src, dst, **kw)

        with mock.patch.object(fh.os, "replace", inject), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            rc = fh.refresh_manifests_cli(["--refresh-manifests", "--outdir", str(root),
                                           "--capture-from", "0"])
        # 命中标志：确证注入到达目标分支（提交期，不是 prepare 期）
        check("F-07 注入命中标志（第 4 次 os.replace＝第二文件提交）",
              calls["n"] >= 4 and "disk full injected" in err.getvalue(), err.getvalue()[:200])
        after = {p: p.read_bytes() for p in dones}
        residue = [x.name for x in root.rglob(".*refresh-*")] \
            + [x.name for x in root.rglob("*.recover")]
        check("F-07 原反例：注入后所有 done.json 字节回滚原样＋无临时/备份/恢复残留＋exit 2",
              rc == 2 and after == originals and residue == [],
              (rc, residue, [p.name for p in dones if after[p] != originals[p]]))

    # 回滚失败：保留 .recover 恢复件并 exit 1
    with tempfile.TemporaryDirectory(prefix="d-f07-rollbackfail-", dir="/private/tmp") as raw:
        root = Path(raw)
        dones = make_two_prehistoric(root)
        real_replace = os.replace
        calls = {"n": 0}

        def inject(src, dst, **kw):
            calls["n"] += 1
            if calls["n"] in (4, 5):  # 4=第二文件提交失败；5=第一条回滚（bak→done）也失败
                raise OSError(f"injected at call {calls['n']}")
            return real_replace(src, dst, **kw)

        with mock.patch.object(fh.os, "replace", inject), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            rc = fh.refresh_manifests_cli(["--refresh-manifests", "--outdir", str(root),
                                           "--capture-from", "0"])
        recover = list(root.rglob("*.recover"))
        check("F-07 回滚失败：exit 1＋.recover 恢复件保留＋stderr 指认混合状态",
              rc == 1 and len(recover) == 1 and "rollback-failed" in err.getvalue(),
              (rc, [x.name for x in recover], err.getvalue()[:200]))

    # CLI 捕 OSError：只读 outdir 的迁移 staging 失败不裸 traceback。
    if os.geteuid() != 0:
        with tempfile.TemporaryDirectory(prefix="d-f07-oserr-", dir="/private/tmp") as raw:
            root = Path(raw)
            make_two_prehistoric(root)
            os.chmod(root, 0o500)
            for run_dir in root.glob("run_*"):
                os.chmod(run_dir, 0o500)
            try:
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    rc = fh.refresh_manifests_cli(
                        ["--refresh-manifests", "--outdir", str(root),
                         "--capture-from", "0"])
            finally:
                os.chmod(root, 0o700)
                for run_dir in root.glob("run_*"):
                    os.chmod(run_dir, 0o700)
            check("F-07 CLI 捕 OSError：只读目录 exit 2 不裸 traceback",
                  rc == 2 and "fail-closed" in err.getvalue(), (rc, err.getvalue()[:200]))
    else:
        print("skip  F-07 CLI OSError（root 用户权限位不生效）")


# ------------------------------------------------------- GPT-F-06 审计收口

def _fake_edges(path: Path, rows):
    with gzip.open(path, "wt") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _run_closed_audit(tmp: Path, rpc_mock, argv_extra=()):
    import audit_closed_accounts as aca
    out = tmp / "audit.json"
    out.unlink(missing_ok=True)
    argv = ["audit_closed_accounts.py", "MINTx", "--edges", str(tmp / "edges.jsonl.gz"),
            "--out", str(out), "--mode", "blocks", "--interval", "0",
            "--block-samples", "2", "--sample-inits", "2", "--deep-accounts", "2",
            "--deep-sigs", "5", *argv_extra]
    with mock.patch.object(aca.Rpc, "call", rpc_mock), \
            mock.patch.object(sys, "argv", argv), \
            contextlib.redirect_stderr(io.StringIO()):
        rc = 0
        try:
            aca.main()
        except SystemExit as exc:
            rc = int(exc.code or 0)
    report = json.loads(out.read_text()) if out.exists() else None
    return rc, report


def _block_with_init(slot):
    """一个含目标 mint initializeAccount 的 jsonParsed 块。"""
    return {"parentSlot": slot - 1, "transactions": [{
        "meta": {"err": None, "innerInstructions": [], "preTokenBalances": [],
                 "postTokenBalances": []},
        "transaction": {"message": {"accountKeys": [], "instructions": [
            {"parsed": {"type": "initializeAccount",
                        "info": {"mint": "MINTx", "account": "ACC1", "owner": "OWN1"}}}]}},
    }]}


def t_gptf06_closed_audit():
    """GPT-F-06：audit_closed_accounts fail-open 收口——status 契约与退出码对齐。"""
    with tempfile.TemporaryDirectory(prefix="d-gptf06-", dir="/private/tmp") as raw:
        tmp = Path(raw)
        _fake_edges(tmp / "edges.jsonl.gz",
                    [[1, 100, 0, -1, "OWN1", "OWN2", 5],
                     [2, 200, 0, -1, "OWN2", "OWN3", 5]])

        # ⓪ 原反例：坏行不得被逐行 except:continue 吞掉后继续审计。
        import audit_closed_accounts as aca
        bad_edges = tmp / "bad-edges.jsonl.gz"
        with gzip.open(bad_edges, "wt") as fh:
            fh.write(json.dumps([1, 100, 0, -1, "OWN1", "OWN2", 5]) + "\n")
            fh.write("{bad-json\n")
        try:
            aca.load_edge_index(bad_edges)
            bad_line_rejected = False
            bad_line_detail = ""
        except ValueError as exc:
            bad_line_rejected = "第 2 行" in str(exc)
            bad_line_detail = str(exc)
        check("批3 T4 坏边行带行号整次失败（旧版静默 continue）",
              bad_line_rejected, bad_line_detail)

        # ① getMultipleAccounts 批失败 → exit 1 INVALID_SAMPLE
        def rpc_gma_fail(self, method, params, retries=4):
            if method == "getBlock":
                return _block_with_init(params[0])
            if method == "getMultipleAccounts":
                return None
            return []
        rc, report = _run_closed_audit(tmp, rpc_gma_fail)
        check("GPT-F-06 ① gma 批失败→exit 1 INVALID_SAMPLE（原反例：旧版 continue 假绿）",
              rc == 1 and report and report["status"] == "INVALID_SAMPLE"
              and any("getMultipleAccounts" in x for x in report["invalid_reasons"]),
              (rc, report and report.get("status"), report and report.get("invalid_reasons")))

        # ② closed>0 但深挖零事件（checked=0）→ exit 1
        def rpc_closed_noevents(self, method, params, retries=4):
            if method == "getBlock":
                return _block_with_init(params[0])
            if method == "getMultipleAccounts":
                return {"value": [None for _ in params[0]]}  # 全销户
            if method == "getSignaturesForAddress":
                return []
            return None
        rc, report = _run_closed_audit(tmp, rpc_closed_noevents)
        check("GPT-F-06 ② checked=0 且 closed>0→exit 1（旧版 exit 0 冒充零漏）",
              rc == 1 and report["status"] == "INVALID_SAMPLE"
              and any("checked=0" in x or "核到的区间内事件为 0" in x
                      for x in report["invalid_reasons"]),
              (rc, report.get("invalid_reasons")))

        # ③ closed=0（审计对象为空）→ exit 0 弱结论 NO_CLOSED_SAMPLED（边界显式定案）
        def rpc_all_alive(self, method, params, retries=4):
            if method == "getBlock":
                return _block_with_init(params[0])
            if method == "getMultipleAccounts":
                return {"value": [{"lamports": 1} for _ in params[0]]}
            return None
        rc, report = _run_closed_audit(tmp, rpc_all_alive)
        check("GPT-F-06 ③ closed=0→exit 0 status=NO_CLOSED_SAMPLED（弱结论≠查询失败）",
              rc == 0 and report["status"] == "NO_CLOSED_SAMPLED"
              and report["invalid_reasons"] == [],
              (rc, report.get("status"), report.get("invalid_reasons")))

        _fake_edges(tmp / "edges.jsonl.gz",
                    [[1, 100, "OWN1", "OWN2", 5], [2, 200, "OWN2", "OWN3", 5]])
        rc, legacy_report = _run_closed_audit(
            tmp, rpc_all_alive, argv_extra=("--legacy-sol5",))
        check("批3 T4 legacy 报告强制 non-formal/order-ambiguous",
              rc == 0 and legacy_report
              and legacy_report.get("non_formal") is True
              and legacy_report.get("order_ambiguous") is True,
              (rc, legacy_report))
        _fake_edges(tmp / "edges.jsonl.gz",
                    [[1, 100, 0, -1, "OWN1", "OWN2", 5],
                     [2, 200, 0, -1, "OWN2", "OWN3", 5]])

        # ④ 发现漏边 → exit 2 LEAK_FOUND
        def rpc_leak(self, method, params, retries=4):
            if method == "getBlock":
                return _block_with_init(params[0])
            if method == "getMultipleAccounts":
                return {"value": [None for _ in params[0]]}
            if method == "getSignaturesForAddress":
                return [{"signature": "SIG1", "slot": 150, "err": None}]
            if method == "getTransaction":
                return {"meta": {"err": None,
                                 "preTokenBalances": [{"mint": "MINTx", "accountIndex": 0,
                                                        "owner": "OWNLEAK",
                                                        "uiTokenAmount": {"amount": "9"}}],
                                 "postTokenBalances": [{"mint": "MINTx", "accountIndex": 0,
                                                         "owner": "OWNLEAK",
                                                         "uiTokenAmount": {"amount": "2"}}]},
                        "transaction": {"message": {"accountKeys": ["ACC1"],
                                                     "instructions": []}}}
            return None
        rc, report = _run_closed_audit(tmp, rpc_leak)
        check("GPT-F-06 ④ 漏边实锤→exit 2 LEAK_FOUND（gate 语义保留）",
              rc == 2 and report["status"] == "LEAK_FOUND" and report["events"]["missing"] == 1,
              (rc, report.get("status"), report.get("events")))

        # ⑤ 墙钟截断 → exit 1（有样本也不冒充完整）
        def rpc_slow_block(self, method, params, retries=4):
            if method == "getBlock":
                time.sleep(0.05)
                return _block_with_init(params[0])
            if method == "getMultipleAccounts":
                return {"value": [{"lamports": 1} for _ in params[0]]}
            return None
        rc, report = _run_closed_audit(tmp, rpc_slow_block,
                                       argv_extra=("--wall-min", "0.0005",
                                                   "--sample-inits", "99",
                                                   "--block-samples", "9"))
        check("GPT-F-06 ⑤ 墙钟截断→exit 1（wall_truncated 单列）",
              rc == 1 and report["status"] == "INVALID_SAMPLE"
              and report["sampled"]["wall_truncated"] is True
              and any("墙钟" in x for x in report["invalid_reasons"]),
              (rc, report and report.get("invalid_reasons")))


# ------------------------------------------------------ F-06 收据链（单元＋端到端）

def _flip_case(tmp: Path):
    """真实翻转最小案：E1 先收 CEX（A）100 再收 DEX（B）100，转出 100。
    FIFO 剩 B（dex）、LIFO 剩 A（cex）、pro_rata 各半——三策略 top 分歧＝真实翻转。"""
    edges = tmp / "edges.jsonl.gz"
    rows = [  # 7 元组 [ts,slot,tx,ix,from,to,amt]（精确序，避免 order_ambiguous 干扰）
        [100, 1, 0, 0, "AAAA", "E1E1", 100],
        [200, 2, 0, 0, "BBBB", "E1E1", 100],
        [300, 3, 0, 0, "E1E1", "CCCC", 100],
    ]
    with gzip.open(edges, "wt") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    write_json(tmp / "entities.json", {"E1": ["E1E1"]})
    write_json(tmp / "labels.json", {"AAAA": {"kind": "cex", "name": "cexA"},
                                     "BBBB": {"kind": "dex_pool", "name": "dexB"}})
    return edges


def _run_trace(tmp: Path, *extra):
    edge_path = tmp / "edges.jsonl.gz"
    proc = subprocess.run(
        [sys.executable, str(HERE.parent / "report/entity_source_trace.py"),
         "--edges-sol", str(edge_path), "--total-supply", "1000000",
         "--entity-file", str(tmp / "entities.json"),
         "--labels-file", str(tmp / "labels.json"),
         "--out", str(tmp / "provenance_ledger.json"),
         *formal_cli_args(edge_path), *extra],
        capture_output=True, text=True, cwd=tmp)
    ledger = None
    if (tmp / "provenance_ledger.json").is_file():
        ledger = json.loads((tmp / "provenance_ledger.json").read_text())
    return proc, ledger


def _make_flip_receipt(tmp: Path, ledger, *, fingerprint=None, share_mutate=None,
                       extra_rows=()):
    """按 ledger 明细机械生成合法收据（测试内不手填指纹——与生产同函数）。"""
    import handoff_manifest as hm
    real = hm.ledger_real_flips(ledger)
    (tmp / "evidence.txt").write_text("人工核对：双来源结构经链上浏览器复核。", encoding="utf-8")
    rows = []
    for (eid, anchor), info in sorted(real.items()):
        tbp = {}
        for policy in hm.FLIP_POLICIES:
            share = info["shares"].get(policy)
            if share_mutate:
                share = share_mutate(share)
            tbp[policy] = {"terminal": info["tops"].get(policy) or [],
                           "share_pct": share}
        rows.append({"entity_id": eid, "anchor": anchor,
                     "reason": "真实双来源结构：CEX 与 DEX 两路进货体量相当。",
                     "flip_fingerprint": fingerprint or info["fingerprint"],
                     # F-D1 起 location 串必须命中报告某一 Markdown 标题行（子串匹配）
                     "disclosure": {"top_by_policy": tbp,
                                    "report_locations": ["翻转披露"]}})
    rows.extend(extra_rows)
    entity_path = tmp / "entities.json"
    receipt = {
        "schema": "flip-adjudications/v1",
        "approved_by": "用户",
        "user_decided_at_utc": "2026-08-13T00:00:00Z",
        "entity_file": {"path": "entities.json", "size": entity_path.stat().st_size,
                        "sha256": sha_file(entity_path)},
        "evidence_refs": [{"path": "evidence.txt",
                           "size": (tmp / "evidence.txt").stat().st_size,
                           "sha256": sha_file(tmp / "evidence.txt")}],
        "adjudications": rows,
    }
    return write_json(tmp / "flip_adjudications.json", receipt)


def t_f06_trace_receipt_chain():
    """F-06 主链：无收据拒→旧串格式拒→合法收据放行→数据变化旧收据失效→预防性豁免拒。"""
    import handoff_manifest as hm
    with tempfile.TemporaryDirectory(prefix="d-f06-", dir="/private/tmp") as raw:
        tmp = Path(raw)
        _flip_case(tmp)

        proc, ledger = _run_trace(tmp)
        check("F-06 无收据：真实翻转 exit 2 且 publishable=false（阻断保留）",
              proc.returncode == 2 and ledger
              and ledger["bounds_sensitivity"]["publishable"] is False
              and "裁决收据" in proc.stdout + proc.stderr,
              (proc.returncode, (proc.stdout + proc.stderr)[-300:]))

        proc2, _ = _run_trace(tmp, "--acknowledge-flip", "E1:current:aaaaaaaaaa")
        check("F-06 原反例翻案：6.39.4 旧串格式（任意 10 字符理由）不再解除阻断",
              proc2.returncode == 2, (proc2.returncode, (proc2.stdout + proc2.stderr)[-200:]))

        receipt_path = _make_flip_receipt(tmp, ledger)
        proc3, ledger3 = _run_trace(tmp, "--acknowledge-flip", str(receipt_path))
        binding_ref = (ledger3 or {}).get("input_binding", {}).get(
            "algorithm_params", {}).get("flip_adjudications")
        acks = (ledger3 or {}).get("bounds_sensitivity", {}).get("acknowledged_flips")
        check("F-06 合法收据：指纹＋披露匹配放行 exit 0，收据引用入 input_binding",
              proc3.returncode == 0 and ledger3["bounds_sensitivity"]["publishable"] is True
              and isinstance(binding_ref, dict) and binding_ref.get("sha256")
              and acks and acks[0]["source"] == "flip-adjudications/v1",
              (proc3.returncode, (proc3.stdout + proc3.stderr)[-300:]))

        # freeze 侧同源重验：合法收据下 recompute 零 fail
        fails = hm.recompute_provenance_sensitivity(str(tmp), ledger3)
        check("F-06 freeze recompute：绑定收据独立重验通过（不再信 ledger 自报）",
              fails == [], fails)

        # 收据内容被换（sha 失配）→ freeze 拒
        doc = json.loads(receipt_path.read_text())
        doc["approved_by"] = "别人"
        write_json(receipt_path, doc)
        fails2 = hm.recompute_provenance_sensitivity(str(tmp), ledger3)
        check("F-06 收据换包（sha 失配）→ freeze recompute 拒",
              any("绑定" in x or "哈希" in x for x in fails2), fails2)

        # 底层数据一变→指纹失配→旧收据自动失效（先恢复收据字节）
        receipt_path.write_text(json.dumps(
            json.loads(receipt_path.read_text()) | {"approved_by": "用户"},
            ensure_ascii=False, indent=1), encoding="utf-8")
        old_receipt = _make_flip_receipt(tmp, ledger3)  # 基于旧明细的收据
        with gzip.open(tmp / "edges.jsonl.gz", "wt") as fh:
            for row in [[100, 1, 0, 0, "AAAA", "E1E1", 100],
                        [200, 2, 0, 0, "BBBB", "E1E1", 120],  # 数据变了
                        [300, 3, 0, 0, "E1E1", "CCCC", 100]]:
                fh.write(json.dumps(row) + "\n")
        proc4, _ = _run_trace(tmp, "--acknowledge-flip", str(old_receipt))
        check("F-06 底层数据一变→旧收据指纹自动失效 exit 2（必须重裁）",
              proc4.returncode == 2 and "指纹" in proc4.stdout + proc4.stderr,
              (proc4.returncode, (proc4.stdout + proc4.stderr)[-300:]))

        # 预防性豁免：收据行指向非真实翻转锚点 → 拒
        _flip_case(tmp)  # 恢复原数据
        proc5, ledger5 = _run_trace(tmp)
        receipt5 = _make_flip_receipt(tmp, ledger5, extra_rows=[{
            "entity_id": "E9", "anchor": "current",
            "reason": "预防性豁免一把梭（应被拒绝的行）",
            "flip_fingerprint": "0" * 64,
            "disclosure": {"top_by_policy": {p: {"terminal": ["X"], "share_pct": "1.00"}
                                              for p in hm.FLIP_POLICIES},
                           "report_locations": ["§x"]}}])
        proc6, _ = _run_trace(tmp, "--acknowledge-flip", str(receipt5))
        check("F-06 预防性豁免（收据行指向非真实翻转锚点）→ exit 2",
              proc6.returncode == 2 and "预防性豁免" in proc6.stdout + proc6.stderr,
              (proc6.returncode, (proc6.stdout + proc6.stderr)[-200:]))


def t_f06_receipt_unit_negatives():
    """F-06 收据加载器字段级反例（对齐 waiver 先例强度）。"""
    import handoff_manifest as hm
    with tempfile.TemporaryDirectory(prefix="d-f06u-", dir="/private/tmp") as raw:
        tmp = Path(raw)
        _flip_case(tmp)
        proc, ledger = _run_trace(tmp)
        receipt_path = _make_flip_receipt(tmp, ledger)
        base = json.loads(receipt_path.read_text())

        scenarios = [
            ("schema 错误", lambda d: d.update(schema="flip-ack/v0"), "schema"),
            ("缺裁决主体", lambda d: d.update(approved_by=" "), "approved_by"),
            ("时间非 UTC Z", lambda d: d.update(user_decided_at_utc="2026-08-13 00:00:00"),
             "user_decided_at_utc"),
            ("evidence_refs 空", lambda d: d.update(evidence_refs=[]), "evidence_refs"),
            ("理由过短", lambda d: d["adjudications"][0].update(reason="短"), "reason"),
            ("指纹非 hex", lambda d: d["adjudications"][0].update(flip_fingerprint="z" * 64),
             "flip_fingerprint"),
            ("缺披露位置", lambda d: d["adjudications"][0]["disclosure"].update(
                report_locations=[]), "report_locations"),
        ]
        for label, mutate, needle in scenarios:
            doc = json.loads(json.dumps(base))
            mutate(doc)
            write_json(receipt_path, doc)
            try:
                hm.load_flip_adjudications(receipt_path, current_entity_file=tmp / "entities.json")
                check(f"F-06 单元反例被拒：{label}", False, "放行了")
            except ValueError as exc:
                check(f"F-06 单元反例被拒：{label}", needle in str(exc), exc)

        # 名册改动→收据 entity_file 绑定失效
        write_json(receipt_path, base)
        write_json(tmp / "entities.json", {"E1": ["E1E1", "F2F2"]})
        try:
            hm.load_flip_adjudications(receipt_path, current_entity_file=tmp / "entities.json")
            check("F-06 名册改动后旧收据失效", False, "放行了")
        except ValueError as exc:
            # 名册一改，收据 entity_file ref 的三验（sha/size）先失配即拦——
            # "与本次运行名册内容一致"检查在其后兜底，两条文案都算命中。
            check("F-06 名册改动后旧收据失效",
                  "名册" in str(exc) or "entity_file" in str(exc), exc)


def t_f06_a5_disclosure():
    """F-06 A5：报告实文披露核对＋ledger sha 与 freeze 绑定。"""
    import a5_report_seal as a5
    import handoff_manifest as hm
    with tempfile.TemporaryDirectory(prefix="d-f06a5-", dir="/private/tmp") as raw:
        tmp = Path(raw)
        _flip_case(tmp)
        _, ledger0 = _run_trace(tmp)
        receipt = _make_flip_receipt(tmp, ledger0)
        proc, ledger = _run_trace(tmp, "--acknowledge-flip", str(receipt))
        assert proc.returncode == 0, proc.stdout + proc.stderr
        _, ledger_sha, _ = hm.sha256_file(tmp / "provenance_ledger.json")
        write_json(tmp / "entity_freeze.json", {"schema": "entity-freeze/v1",
                                                "provenance_ledger_sha256": ledger_sha,
                                                "revisions": []})
        real = hm.ledger_real_flips(ledger)
        a4obj = {"workflow_type": "new-analysis"}
        # 报告在披露章节内含全部披露值 → DISCLOSED（F-D1 起核对锚定该章节切片）
        parts = ["# 报告", "## 翻转披露"]
        for info in real.values():
            for policy in hm.FLIP_POLICIES:
                terminal = info["tops"][policy]
                parts.append(f"{policy}: {terminal[2]} 占 {info['shares'][policy]}%")
        parts.append("## 其他章节")
        parts.append("正文其他内容。")
        good_text = "\n".join(parts)
        bundle = a5.provenance_flip_bundle(tmp, good_text, a4obj)
        check("F-06 A5 绿例：披露章节内含三策略名＋top＋份额 → DISCLOSED",
              bundle["status"] == "DISCLOSED" and bundle["anchors"], bundle)
        # 报告缺披露段 → 拒（原反例：只字未提翻转）
        try:
            a5.provenance_flip_bundle(tmp, "# 报告\n只字未提翻转。", a4obj)
            check("F-06 A5 原反例：报告缺披露段被拒", False, "放行了")
        except ValueError as exc:
            check("F-06 A5 原反例：报告缺披露段被拒",
                  "披露位置在报告中不存在" in str(exc), exc)
        # F-D1 盲审攻击原样重放：无关附录含相同地址串＋占位数字（不提翻转/策略）→ 必拒
        attack_text = ("# 某代币筹码分析报告\n"
                       "## 附录 F：随机抽样校验串\n"
                       "本次抽样校验串为 AAAA、BBBB、CCCC，用于比对采集完整性，与结论无关。\n"
                       "## 附录 G：占位数值\n"
                       "下表为排版占位，非真实数据：50.00 / 100.00 / 12.34。\n")
        try:
            a5.provenance_flip_bundle(tmp, attack_text, a4obj)
            check("F-D1 无关附录攻击（同地址串＋同数字）被拒", False, "放行了＝原攻击仍成立")
        except ValueError as exc:
            check("F-D1 无关附录攻击（同地址串＋同数字）被拒",
                  "披露位置在报告中不存在" in str(exc), exc)
        # F-D1 变体：附录标题恰与 location 同名（切片命中）但无策略名——仍拒
        sneaky = ("# 报告\n## 翻转披露\n"
                  "本段仅有地址 AAAA、BBBB 与数字 50.00、100.00，无任何策略并列。\n")
        try:
            a5.provenance_flip_bundle(tmp, sneaky, a4obj)
            check("F-D1 切片命中但缺策略名骨架被拒", False, "放行了")
        except ValueError as exc:
            check("F-D1 切片命中但缺策略名骨架被拒", "缺策略名" in str(exc), exc)
        # F-D1 份额半边独立红例（M2 变异锁）：切片含策略名＋ident 但份额数字错
        wrong_share_parts = ["# 报告", "## 翻转披露"]
        for info in real.values():
            for policy in hm.FLIP_POLICIES:
                terminal = info["tops"][policy]
                wrong_share_parts.append(f"{policy}: {terminal[2]} 占 99.99%")
        try:
            a5.provenance_flip_bundle(tmp, "\n".join(wrong_share_parts), a4obj)
            check("F-D1 份额半边独立红例（ident 在场、份额错）被拒", False, "放行了")
        except ValueError as exc:
            check("F-D1 份额半边独立红例（ident 在场、份额错）被拒",
                  "份额数字" in str(exc), exc)
        # N-D1（收口补丁）：纯中文真实披露写法（盲审变体 D 原文形态）——别名族判据下绿
        zh_parts = ["# 报告", "## 翻转披露",
                    "本实体存在双来源结构，三种库存消耗口径给出的主导终点不一致："]
        zh_names = {"pro_rata": "按比例", "fifo": "先进先出", "lifo": "后进先出"}
        for info in real.values():
            for policy in hm.FLIP_POLICIES:
                zh_parts.append(f"{zh_names[policy]}口径主导终点为 {info['tops'][policy][2]}"
                                f"（{info['shares'][policy]}%）；")
        zh_parts.append("结论按多口径并列披露。")
        bundle_zh = a5.provenance_flip_bundle(tmp, "\n".join(zh_parts), a4obj)
        check("N-D1 绿例①：纯中文披露（按比例/先进先出/后进先出）→ DISCLOSED",
              bundle_zh["status"] == "DISCLOSED", bundle_zh.get("status"))
        # N-D1 绿例②：中英混排（中文段落里保留英文标识符）
        mixed_parts = ["# 报告", "## 翻转披露"]
        for info in real.values():
            mixed_parts.append(f"按比例（pro_rata）口径：{info['tops']['pro_rata'][2]} "
                               f"占 {info['shares']['pro_rata']}%；")
            mixed_parts.append(f"fifo 口径：{info['tops']['fifo'][2]} "
                               f"占 {info['shares']['fifo']}%；")
            mixed_parts.append(f"后进先出（lifo）口径：{info['tops']['lifo'][2]} "
                               f"占 {info['shares']['lifo']}%。")
        bundle_mixed = a5.provenance_flip_bundle(tmp, "\n".join(mixed_parts), a4obj)
        check("N-D1 绿例②：中英混排披露 → DISCLOSED",
              bundle_mixed["status"] == "DISCLOSED", bundle_mixed.get("status"))
        # （绿例③＝上方既有英文 good_text 用例，本补丁零回归——继续在场）
        # N-D1 回归：无关附录攻击在别名族判据下**仍拒**（别名族不放宽位置锚）
        try:
            a5.provenance_flip_bundle(tmp, attack_text, a4obj)
            check("N-D1 回归：无关附录攻击仍拒（别名族不放宽位置锚）", False, "放行了")
        except ValueError as exc:
            check("N-D1 回归：无关附录攻击仍拒（别名族不放宽位置锚）",
                  "披露位置在报告中不存在" in str(exc), exc)
        # N-D1 红例：切片含中文策略词但缺份额（别名族不吞掉份额半边）
        zh_noshare = ["# 报告", "## 翻转披露",
                      "按比例、先进先出、后进先出三口径主导终点分别为 "
                      + "、".join(info["tops"][p][2] for p in hm.FLIP_POLICIES
                                  for info in [next(iter(real.values()))]) + "。"]
        try:
            a5.provenance_flip_bundle(tmp, "\n".join(zh_noshare), a4obj)
            check("N-D1 红例：中文策略词在场但缺份额仍拒", False, "放行了")
        except ValueError as exc:
            check("N-D1 红例：中文策略词在场但缺份额仍拒", "份额数字" in str(exc), exc)
        # F-D1 披露值散落在另一章节（切片外）→ 拒（全文偶然同串不作数）
        split_parts = ["# 报告", "## 翻转披露", "见下方附录。", "## 附录"]
        for info in real.values():
            for policy in hm.FLIP_POLICIES:
                terminal = info["tops"][policy]
                split_parts.append(f"{policy}: {terminal[2]} 占 {info['shares'][policy]}%")
        try:
            a5.provenance_flip_bundle(tmp, "\n".join(split_parts), a4obj)
            check("F-D1 披露值落在切片外章节被拒（同段要求）", False, "放行了")
        except ValueError as exc:
            check("F-D1 披露值落在切片外章节被拒（同段要求）",
                  "披露段" in str(exc), exc)
        # freeze 后换 ledger → sha 绑定拒
        ledger_mut = json.loads((tmp / "provenance_ledger.json").read_text())
        ledger_mut["generated_at"] = "2001-01-01T00:00:00Z"
        write_json(tmp / "provenance_ledger.json", ledger_mut)
        try:
            a5.provenance_flip_bundle(tmp, good_text, a4obj)
            check("F-06 A5：freeze 后换 ledger 被 sha 绑定拒", False, "放行了")
        except ValueError as exc:
            check("F-06 A5：freeze 后换 ledger 被 sha 绑定拒", "哈希不一致" in str(exc), exc)
        # freeze 记录了 sha 但 ledger 被删 → 拒（删件旁路封死）
        (tmp / "provenance_ledger.json").unlink()
        try:
            a5.provenance_flip_bundle(tmp, good_text, a4obj)
            check("F-06 A5：freeze 后删 ledger 旁路封死", False, "放行了")
        except ValueError as exc:
            check("F-06 A5：freeze 后删 ledger 旁路封死", "缺失" in str(exc), exc)


# ------------------------------------------------------------- A-1 旧收据作废

def _run_supply_pass(root: Path):
    """先跑出一份诚实 PASS 收据（replay==onchain==100，容差 10 之内）。"""
    from test_repair_batch_a import SupplyPool, TOKEN, chdir
    from test_supply_truth_gate import write_evm_bundle
    import supply_truth_gate as supply
    (root / "replay_stats.json").write_text(
        json.dumps({"mint_total_raw": "100", "burn_total_raw": "0"}), encoding="utf-8")
    bundle = write_evm_bundle(
        root, token=TOKEN, as_of=123, total=100, zero=0, dead=0)
    argv = ["--chain", "eth", "--token", TOKEN, "--as-of-block", "123",
            "--rpc", "offline://fixture", "--tolerance-bps", "10",
            "--replay-stats", "replay_stats.json",
            "--observation-bundle", str(bundle),
            "--out", str(root / "supply_truth.json")]
    with chdir(root), mock.patch.object(supply, "attested_rpc_pool",
                                        return_value=SupplyPool(100)), \
            contextlib.redirect_stderr(io.StringIO()):
        try:
            rc = supply.main(argv)
        except SystemExit as exc:
            rc = int(exc.code or 0)
    return rc


def t_a1_policy_reject_invalidates_receipt():
    from test_repair_batch_a import run_supply
    with tempfile.TemporaryDirectory(prefix="d-a1-", dir="/private/tmp") as raw:
        root = Path(raw)
        rc = _run_supply_pass(root)
        receipt = json.loads((root / "supply_truth.json").read_text())
        assert rc == 0 and receipt["verdict"] == "PASS", (rc, receipt)
        # 政策拒绝（超钳无 waiver）→ 旧 PASS 收据必须作废归档
        rc2, receipt2, stderr2 = run_supply(root, tolerance=100)
        archived = list(root.glob("supply_truth.json.superseded-*"))
        check("A-1 政策拒绝：exit 2＋旧 PASS 收据作废归档（案内不再有现役收据）",
              rc2 == 2 and receipt2 is None and len(archived) == 1
              and "作废归档" in stderr2,
              (rc2, [x.name for x in archived], stderr2[-200:]))
        old = json.loads(archived[0].read_text())
        check("A-1 归档件即上一轮原收据（内容不销毁）",
              old.get("verdict") == "PASS" and str(old.get("schema", "")).startswith(
                  "supply-truth-receipt/"), old.get("schema"))
        # 非本 gate 文件占位 --out：不误伤
        write_json(root / "supply_truth.json", {"schema": "unrelated/v1"})
        rc3, _, _ = run_supply(root, tolerance=100)
        untouched = json.loads((root / "supply_truth.json").read_text())
        check("A-1 误伤查：占位的非本 gate 文件不动", rc3 == 2
              and untouched == {"schema": "unrelated/v1"}, untouched)


# ---------------------------------------------------- B-4/B-5 锚点绑定红线

def t_b4_b5_bound_stats():
    import holder_distribution_scan as dist
    with tempfile.TemporaryDirectory(prefix="d-b45-", dir="/private/tmp") as raw:
        root = Path(raw)
        stats = root / "data" / "stats.json"
        write_json(stats, {"mint_total_raw": "100", "burn_total_raw": "0"})
        supply_obj = {"inputs": {"replay_stats": {
            "path": "data/stats.json", "size": stats.stat().st_size,
            "sha256": sha_file(stats)}}, "replay_net": "100"}
        anchor, source, _ = dist.mint_closure_anchor(root, supply_obj, "bsc", 100)
        check("B-4 绿例：三验一致的绑定实物作锚点", anchor == 100
              and source == "bound_replay_mint", (anchor, source))
        # 换包（sha 失配）→ 拒（B-4 新增：不引用别人的三验作自己的证据）
        stats.write_text(json.dumps({"mint_total_raw": "999", "burn_total_raw": "0"}),
                         encoding="utf-8")
        try:
            dist.mint_closure_anchor(root, supply_obj, "bsc", 100)
            check("B-4 原反例：绑定实物换包（sha/size 失配）被拒", False, "放行了")
        except ValueError as exc:
            check("B-4 原反例：绑定实物换包（sha/size 失配）被拒",
                  "换包或陈旧" in str(exc), exc)
        # B-5 红线：绑定实物在案根外 → fail-closed（此前该分支变异存活）
        with tempfile.TemporaryDirectory(prefix="d-b5-out-", dir="/private/tmp") as outside:
            fake = Path(outside) / "stats.json"
            write_json(fake, {"mint_total_raw": "100", "burn_total_raw": "0"})
            supply_out = {"inputs": {"replay_stats": {
                "path": str(fake), "size": fake.stat().st_size,
                "sha256": sha_file(fake)}}, "replay_net": "100"}
            try:
                dist.mint_closure_anchor(root, supply_out, "bsc", 100)
                check("B-5 红线：案根外绑定实物 fail-closed", False, "放行了")
            except ValueError as exc:
                check("B-5 红线：案根外绑定实物 fail-closed",
                      "不在当前案根内" in str(exc), exc)


# ------------------------------------------------- A-3 相对路径与搬家绿例

def t_a3_relative_inputs_and_portability():
    from test_repair_batch_a import supply_item, TARGET
    import shared_release_receipt as shared
    import shutil
    with tempfile.TemporaryDirectory(prefix="d-a3-", dir="/private/tmp") as raw:
        root = Path(raw)
        rc = _run_supply_pass(root)
        assert rc == 0, rc
        receipt = json.loads((root / "supply_truth.json").read_text())
        shown = receipt["inputs"]["replay_stats"]["path"]
        check("A-3 生产侧：envelope inputs 记案根相对路径",
              not os.path.isabs(shown) and shown == "replay_stats.json", shown)
        # 搬家绿例：整案复制后消费侧照过（旧绝对路径收据在 N-1 已证被拒）
        moved = Path(raw) / "moved_case"
        shutil.copytree(root, moved)
        try:
            shared.validate_reconciliation_check(moved, "supply_truth", supply_item(moved),
                                                 TARGET, "evm")
            check("A-3 搬家绿例：相对路径收据整案复制后照过", True)
        except ValueError as exc:
            check("A-3 搬家绿例：相对路径收据整案复制后照过", False, exc)


# ------------------------------------------------------- A-5 三查同源反例

def t_a5_same_source_negative():
    import shared_release_receipt as shared
    from test_audit_release_gate import build_case, sha as fixture_sha
    with tempfile.TemporaryDirectory(prefix="d-a5src-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_case(root, historical=False)
        # 给 supply 收据换绑另一本账（内容自洽、sha 合法登记）——三查不再同源
        alt = root / "alt_stats.json"
        write_json(alt, {"mint_total_raw": "100", "burn_total_raw": "0",
                         "max_block": 123, "alt": True})
        receipt_path = root / "supply_receipt.json"
        doc = json.loads(receipt_path.read_text())
        doc["inputs"]["replay_stats"] = {"path": "alt_stats.json",
                                         "size": alt.stat().st_size,
                                         "sha256": fixture_sha(alt)}
        receipt_path.write_text(json.dumps(doc), encoding="utf-8")
        recon = json.loads((root / "reconciliation_report.json").read_text())
        recon["checks"]["supply"]["receipt"]["sha256"] = fixture_sha(receipt_path)
        (root / "reconciliation_report.json").write_text(json.dumps(recon), encoding="utf-8")
        try:
            shared.validate_reconciliation_report(root)
            check("A-5 原反例：三查 replay_stats 不同源被拒", False, "放行了")
        except ValueError as exc:
            check("A-5 原反例：三查 replay_stats 不同源被拒", "不同源" in str(exc), exc)


# ------------------------------------------------------- B-7 三账等值绑定

def t_b7_ledger_snapshot_binding():
    import audit_release_gate as gate
    from test_audit_release_gate import build_case, sha as fixture_sha
    with tempfile.TemporaryDirectory(prefix="d-b7-", dir="/private/tmp") as raw:
        root = Path(raw)
        report = build_case(root, historical=False)
        assert not gate.run(root, report), "基线应 PASS"
        # 时点游离：balance_source 拿别的块高快照
        snap = json.loads((root / "balances_snapshot.json").read_text())
        snap["as_of_block"] = 999
        write_json(root / "balances_snapshot.json", snap)
        ml = json.loads((root / "membership_ledger.json").read_text())
        ml["entries"][0]["balance_source"]["as_of_block"] = 999
        ml["entries"][0]["balance_source"]["sha256"] = fixture_sha(root / "balances_snapshot.json")
        write_json(root / "membership_ledger.json", ml)
        errors = gate.run(root, report)
        check("B-7 原反例①：balance_source 时点与四查冻结块不一致被拒",
              any("冻结" in x and "时点" in x for x in errors), errors[:3])
        # 数值游离：快照数字与四查 owner 快照不等值（三账内部自洽照样拒）
        report = build_case(root, historical=False)
        snap = json.loads((root / "balances_snapshot.json").read_text())
        snap["entries"][0]["balance_raw"] = "99"
        write_json(root / "balances_snapshot.json", snap)
        ml = json.loads((root / "membership_ledger.json").read_text())
        ml["entries"][0]["as_of_balance_raw"] = "99"
        ml["entries"][0]["balance_source"]["sha256"] = fixture_sha(root / "balances_snapshot.json")
        write_json(root / "membership_ledger.json", ml)
        pl = json.loads((root / "position_ledger.json").read_text())
        pl["entries"][0]["amount_raw"] = "99"
        write_json(root / "position_ledger.json", pl)
        el = json.loads((root / "economic_control_ledger.json").read_text())
        el["entries"][0]["wallet_self_held_raw"] = "99"
        el["entries"][0]["confirmed_economic_control_raw"] = "99"
        write_json(root / "economic_control_ledger.json", el)
        errors = gate.run(root, report)
        check("B-7 原反例②：三账内部自洽但与四查 owner 快照不等值被拒",
              any("不等值" in x for x in errors), errors[:4])


# ------------------------------- B-1 bundle holder_outputs 三验 ＋ B-2 Solana e2e

# 本夹具覆盖 B-1/B-2 发布链，不承担 F-09 大小写反例；使用合法且全小写的
# base58 mint，使既有 observation bundle canonical target 与 reconcile/v3 身份一致。
SOL_MINT = "mintcasesensitive" + "1" * 15
SOL_SLOT = 500


def _repo_ref(rel):
    path = REPO / rel
    return {"path": rel, "sha256": sha_file(path)}


def _build_solana_bundle(root: Path):
    """真实形态 observation bundle（过 validate_observation_bundle 全部检查）。"""
    from solana_attested_session import SOLANA_MAINNET_GENESIS_HASH
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    owners = {"ownersol1": 60, "ownersol2": 40}
    accounts = [{"account": "acctsol1", "owner": "ownersol1", "amount_raw": 60},
                {"account": "acctsol2", "owner": "ownersol2", "amount_raw": 40}]
    owners_path = write_json(data / "holders_owners.json", owners)
    accounts_path = write_json(data / "holders_accounts.json", accounts)
    inputs = {}
    for name in ("_supply.json", "_gpa_raw_all.json", "_gpa_raw_all.meta.json"):
        inputs[name] = write_json(data / name, {"fixture": name})
    def ref(path):
        return {"path": Path(path).name, "size": Path(path).stat().st_size,
                "sha256": sha_file(path)}
    bundle = {
        "schema": "solana-observation-bundle/v1",
        "target": {"chain": "solana", "token": SOL_MINT, "as_of_block": SOL_SLOT},
        "producer": _repo_ref("scripts/solana/scan_token_accounts.py"),
        "mode": "formal", "verdict": "PASS", "exit_code": 0,
        "inputs": {"supply_rpc": {"path": str(inputs["_supply.json"]),
                                  "size": inputs["_supply.json"].stat().st_size,
                                  "sha256": sha_file(inputs["_supply.json"])},
                   "gpa_rpc": {"path": str(inputs["_gpa_raw_all.json"]),
                               "size": inputs["_gpa_raw_all.json"].stat().st_size,
                               "sha256": sha_file(inputs["_gpa_raw_all.json"])},
                   "gpa_meta": {"path": str(inputs["_gpa_raw_all.meta.json"]),
                                "size": inputs["_gpa_raw_all.meta.json"].stat().st_size,
                                "sha256": sha_file(inputs["_gpa_raw_all.meta.json"])}},
        "as_of_slot": SOL_SLOT, "as_of_block": SOL_SLOT,
        "observed_context_slot": SOL_SLOT,
        "snapshot": {"slot": SOL_SLOT},
        "mint_pre": {"slot": SOL_SLOT - 2, "json_parsed_slot": SOL_SLOT - 1,
                     "raw_sha256": "f" * 64},
        "mint_post": {"slot": SOL_SLOT + 2, "raw_sha256": "f" * 64},
        "supply": {"slot": SOL_SLOT + 3, "amount": "100", "decimals": 0,
                   "semantics": "cross-check observation only; not the freeze point"},
        "closure": {"gpa_amount": "100", "mint_raw_amount": "100",
                    "token_supply_amount": "100", "closed": True},
        "attestation": {"expected_genesis": SOLANA_MAINNET_GENESIS_HASH,
                        "observed_genesis": SOLANA_MAINNET_GENESIS_HASH},
        "activity": {"mode": "complete", "writable_hits": [], "sample_size": 0,
                     "rpc_calls": 3, "complete": True},
        "holder_outputs": {"accounts": ref(accounts_path), "owners": ref(owners_path)},
        "closed": True, "supply_raw": "100", "sum_accounts_raw": "100",
    }
    snapshot_path = write_json(root / "supply_snapshot.json",
                               {"schema": "solana-holder-snapshot/v3", "owners": owners})
    bundle["output"] = {"path": "supply_snapshot.json",
                        "size": snapshot_path.stat().st_size,
                        "sha256": sha_file(snapshot_path)}
    return write_json(root / "supply_receipt.json", bundle), owners_path


def build_solana_case(root: Path):
    """Solana new-analysis 发布闸 run() 完整端到端夹具（B-2，F-B6② 留账正主）。"""
    from test_audit_release_gate import align_ledgers_to_owner_snapshot
    root = Path(root)
    target = {"chain": "solana", "token": SOL_MINT, "as_of_block": SOL_SLOT}
    bundle_path, owners_path = _build_solana_bundle(root)
    report = root / "report.md"
    report.write_text("# Solana 审计报告\n", encoding="utf-8")
    stats = write_json(root / "fixture_replay_stats.json",
                       {"mint_total_raw": "100", "burn_total_raw": "0"})
    replay_input = {"path": "fixture_replay_stats.json", "size": stats.stat().st_size,
                    "sha256": sha_file(stats)}
    write_json(root / "accounting_mode.json", {
        "schema": "accounting-gate/v1", "chain": "solana", "mint": SOL_MINT,
        "token": SOL_MINT, "as_of_block": SOL_SLOT,
        "producer": _repo_ref("scripts/solana/accounting_gate_sol.py"),
        "verdict": "PASS", "exit_code": 0, "mode": "standard",
        "execution_mode": "formal", "observed_context_slot": SOL_SLOT,
        "observation_bundle": {"path": "supply_receipt.json",
                               "size": bundle_path.stat().st_size,
                               "sha256": sha_file(bundle_path)},
        "checks": {"fot": {"status": "clean"}}})
    producers = {"balance": "scripts/solana/anchor_sampler.py",
                 "supply": "scripts/solana/scan_token_accounts.py",
                 "supply_truth": "scripts/lib/supply_truth_gate.py",
                 "time": "scripts/solana/anchor_sampler.py"}
    anchor_output = root / "fixture_anchors.jsonl"
    anchor_rows = [
        {"date": f"2026-01-0{day}", "chain": "solana", "mint": SOL_MINT,
         "endpoint": "https://portal.sqd.dev", "as_of_slot": SOL_SLOT,
         "from_slot": day, "to_slot": day + 10, "n_rows": 1, "accounts": {}}
        for day in (1, 2, 3)
    ]
    anchor_output.write_text(
        "".join(json.dumps(row) + "\n" for row in anchor_rows), encoding="utf-8")
    anchor_ref = {"path": anchor_output.name, "size": anchor_output.stat().st_size,
                  "sha256": sha_file(anchor_output)}
    checks = {}
    for key in ("balance", "supply", "supply_truth", "time"):
        name = f"{key}_receipt.json"
        if key == "supply":
            checks[key] = {"status": "PASS", "exit_code": 0,
                           "receipt": {"path": "supply_receipt.json",
                                       "sha256": sha_file(bundle_path)},
                           "producer": _repo_ref(producers[key])}
            continue
        if key in {"balance", "time"}:
            doc = {"schema": "solana-anchor-sampler-receipt/v2", "target": target,
                   "date_range": {"start": "2026-01-01", "end": "2026-01-03"},
                   "output": anchor_ref,
                   "coverage": {"requested_days": 3, "covered_days": 3, "failed_days": 0},
                   "failures": [], "verdict": "PASS", "exit_code": 0,
                   "producer": _repo_ref(producers[key]), "mode": "formal",
                   "inputs": {"config": {"path": "fixture_replay_stats.json",
                                          "size": stats.stat().st_size,
                                          "sha256": sha_file(stats)}}}
        else:
            doc = {"schema": "supply-truth-receipt/v3", "target": target,
                   "gate": "supply_truth", "chain": "solana",
                   "replay_net": "100", "onchain_total_supply": "100",
                   "diff": "0", "diff_bps": 0.0, "tolerance_bps": 10,
                   "decision_rule": "primary_form1", "burn_form": None,
                   "primary_verdict": "PASS", "sink_reconciliation": None,
                   "observed_context_slot": SOL_SLOT + 3,
                   "verdict": "PASS", "exit_code": 0,
                   "producer": _repo_ref(producers[key]), "mode": "formal",
                   "inputs": {"replay_stats": replay_input,
                              "observation_bundle": {
                                  "path": "supply_receipt.json",
                                  "size": bundle_path.stat().st_size,
                                  "sha256": sha_file(bundle_path)}}}
        path = write_json(root / name, doc)
        checks[key] = {"status": "PASS", "exit_code": 0,
                       "receipt": {"path": name, "sha256": sha_file(path)},
                       "producer": _repo_ref(producers[key])}
    write_json(root / "reconciliation_report.json", {
        "schema": "reconciliation-report/v2", "target": target,
        "producer": _repo_ref("scripts/report/reconciliation_report.py"),
        "verdict": "PASS", "exit_code": 0, "checks": checks})
    write_json(root / "address_classification.json", {
        "current_owner_threshold_pct": 0.1, "current_owner_float_threshold_pct": 0.2,
        "historical_peak_candidates_included": True,
        "unresolved_count": 0, "unresolved_candidates": []})
    align_ledgers_to_owner_snapshot(root, owners_path)
    write_json(root / "wave_scan_report.json", {
        "schema": "wave-scan/v5", "edge_order_granularity": "transaction",
        "order_ambiguous": True, "non_formal": False,
        "params": {"edges_sol": "data/soltx.jsonl.gz"},
        "edge_source_binding": dict(EDGE_SOURCE_BINDING),
        "scan_universe_count": 1,
        "scan_universe": [{"addr": "ownersol1", "peak_pct": 60.0,
                           "must_adjudicate": True, "must_reasons": ["peak_ge_0.1pct"]}]})
    write_json(root / "dormant_warehouse_audit.json", {
        "non_formal": False,
        "order_ambiguous": False,
        "full_history_event_replay": True,
        "coverage": {k: "PASS" for k in ("historical_peaks", "zeroed_or_drawn_down",
                                          "long_dormant", "critical_window_upstream",
                                          "boundary_ring")},
        "unresolved_count": 0, "unresolved": [],
        "universe_ref": {"path": "wave_scan_report.json",
                         "sha256": sha_file(root / "wave_scan_report.json")},
        "candidates": [{"candidate_address": "ownersol1", "boundary_decision": "strict",
                        "decision_reason": "夹具裁决：owner1 为策略成员"}]})
    # adversarial review 真跑 runner（与 EVM build_case 同法）
    write_json(root / "a4_claims.json", {
        "schema": "a4-claims/v2", "claims": [{"id": "C1"}]})
    runner = REPO / "scripts/report/adversarial_review_runner.py"
    reviews = []
    for role in ("entity_attribution_skeptic", "completeness_critic"):
        entry = root / f"review_{role}.py"
        entry.write_text(
            "import json, os\n"
            f"# adversarial fixture role: {role}\n"
            "role=os.environ['CHIP_REVIEW_ROLE']\n"
            "payload={'schema':'adversarial-review-artifact/v2','role':role,"
            "'registry_sha256':os.environ['CHIP_REVIEW_REGISTRY_SHA256']}\n"
            "if role == 'completeness_critic':\n"
            " payload.update({'findings':[],'non_covered':[]})\n"
            "else:\n"
            " payload['results']=[{'claim_id':'C1','verdict':'CONFIRMED',"
            "'evidence':['fixture recomputation'],'alternative_explanations':[]}]\n"
            "with open(os.environ['CHIP_REVIEW_OUTPUT'],'w') as fh: json.dump(payload,fh)\n",
            encoding="utf-8")
        artifact = root / f"review_{role}.json"
        execution = root / f"review_{role}_execution.json"
        proc = subprocess.run([sys.executable, str(runner), str(root), "--role", role,
                               "--entrypoint", entry.name, "--artifact", artifact.name,
                               "--receipt", execution.name], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        reviews.append({"role": role, "exit_code": 0,
                        "artifact": {"path": artifact.name,
                                     "size": artifact.stat().st_size,
                                     "sha256": sha_file(artifact)},
                        "runner": _repo_ref("scripts/report/adversarial_review_runner.py"),
                        "execution_receipt": {"path": execution.name,
                                              "sha256": sha_file(execution)}})
    write_json(root / "adversarial_blockers.json", [])
    aggregate = root / "adversarial_review.json"
    if aggregate.exists():
        aggregate.unlink()
    proc = subprocess.run([
        sys.executable, str(runner), "finalize", str(root),
        "--claim-registry", "a4_claims.json",
        "--receipt", "review_entity_attribution_skeptic_execution.json",
        "--receipt", "review_completeness_critic_execution.json",
        "--blockers", "adversarial_blockers.json", "--out", "adversarial_review.json",
    ], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    import shared_release_receipt
    shared_release_receipt.create_bundle(root)
    # ---- new-analysis 资产：分布链（快照＝bundle owners 同一份）＋figure2＋A4/A5
    write_json(root / "supply_truth.json", {
        "verdict": "PASS", "exit_code": 0, "chain": "solana",
        "onchain_total_supply": "100", "replay_net": "100"})
    write_json(root / "data_map.json", {"files": [
        {"path": "data/holders_owners.json", "sha256": sha_file(owners_path)}]})
    write_json(root / "candidate_screening.json", {"auto_excluded_candidate": []})
    dist = HERE.parent / "report/holder_distribution_scan.py"
    from formal_ready_test_harness import run_formal_script
    p = run_formal_script(dist, ["--case-dir", str(root), "--stage", "initial"])
    assert p.returncode == 0, p.stdout + p.stderr
    write_json(root / "camp_spec.json", {})
    # 批 2 F-09 之后 sol-rows 只认 replay_edges 真实生产的 reconcile/v3；
    # 夹具不得再手写 v2 收据绕过身份、窗口、输入与边摘要绑定。
    import replay_edges
    from producer_history import historical_producer_hashes
    edge_key = hashlib.sha256(SOL_MINT.encode("utf-8")).hexdigest()
    edge_path = root / "data" / f"soltx-{edge_key}.jsonl.gz"
    edges = [
        [1767225600, SOL_SLOT - 1, 0, -1, replay_edges.ZERO, "ownersol1", 60],
        [1767225601, SOL_SLOT, 0, -1, replay_edges.ZERO, "ownersol2", 40],
    ]
    with gzip.open(edge_path, "wt", encoding="utf-8") as fh:
        for row in edges:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    logical = hashlib.sha256()
    for row in edges:
        logical.update(
            (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
        )
    collector_hashes = historical_producer_hashes(
        "scripts/solana/fetch_sqd_transfers_v2.py", "sqd-solana-cache/v4")
    assert collector_hashes, collector_hashes
    cache_meta = write_json(root / "data" / f"soltx-{edge_key}.meta.json", {
        "schema": "sqd-solana-cache/v4", "version": 4, "mint": SOL_MINT,
        "collector": "fetch_sqd_transfers_v2.py/v4",
        "collector_sha256": next(iter(sorted(collector_hashes))),
        "edge_schema": ["ts", "slot", "tx_index", "instr_index", "from", "to", "amt"],
        "edge_semantics": "owner-net-greedy",
        "order_granularity": "transaction", "order_exact": False,
        "from_slot": SOL_SLOT - 1, "finalized_upper_slot": SOL_SLOT,
        "edge_logical_sha256": logical.hexdigest(), "edge_rows": len(edges),
    })
    owners_ref = {"path": owners_path.name, "size": owners_path.stat().st_size,
                  "sha256": sha_file(owners_path)}
    write_json(root / "data/holders_snapshot_meta.json", {
        "schema": "solana-holder-snapshot-v2", "mint": SOL_MINT,
        "target": target, "closed": True, "supply_raw": "100",
        "outputs": {"holders_owners": owners_ref},
    })
    with contextlib.chdir(root):
        assert replay_edges.cmd_reconcile(
            edges, 1, mint=SOL_MINT, cache_meta_path=cache_meta) is True
    camp_reconcile = root / "data/reconcile_receipt.json"
    series_path = write_json(root / "data/camp_series.json", [
        {"ts": 1767225600, "散户": 100.0, "_supply_raw": "100"},
    ])
    from camp_series_provenance import series_to_state_form, write_series_sidecar
    sidecar_path = write_series_sidecar(
        series_path, producer="scripts/tests/test_repair_batch_d.py",
        series_format="sol-rows", denominator="net_supply",
        camps_spec_path=root / "camp_spec.json", final_balances_path=owners_path,
        inputs={"reconcile_receipt": camp_reconcile},
    )
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    state = {
        "chain": "solana", "token": {"chain": "solana"}, "whale_groups": [],
        "camp_share_series": series_to_state_form(
            json.loads(series_path.read_text(encoding="utf-8")), "sol-rows"),
        "provenance": {"series_binding": "producer-sidecar",
                       "camp_series_sidecar": {
                           "producer": sidecar["producer"],
                           "series_file": sidecar["series_file"],
                           "series_sha256": sidecar["series_sha256"],
                           "series_format": sidecar["series_format"],
                       }},
    }
    for name, value in {
        "handoff_manifest.json": {"consumer_min_schema": "handoff/v3", "status": "READY",
                                  "run_id": "fixture-sol"},
        "identity_snapshot_receipt.json": {"schema": "identity-snapshot-receipt/v1"},
        "entity_freeze.json": {"schema": "entity-freeze/v1", "revisions": []},
        "analysis-state.json": state,
        "facts.json": {"token": {"symbol": "SOLX", "decimals": 0,
                                 "total_supply_raw": "100"}, "entities": {}},
        "evidence.json": {"source": "fixture"},
        "a4_claims.json": {"schema": "a4-claims/v2", "claims": [{"id": "C1"}]},
    }.items():
        write_json(root / name, value)
    import scan_token_accounts
    from identity_snapshot_receipt import emit_solana
    from test_r9_batch3_solana_observation import SolanaTransportFake
    identity_root = root / "identity_bridge"
    identity_root.mkdir()
    identity_transport = SolanaTransportFake()
    identity_transport.slot = SOL_SLOT - 3
    with contextlib.chdir(identity_root):
        identity_rc = scan_token_accounts.main([
            SOL_MINT, "--program", "spl", "--rpc", "fixture://solana",
            "--out", "snapshot.json", "--bundle", "snapshot_receipt.json",
            "--work-dir", "data",
        ], request_json=identity_transport)
    assert identity_rc == 0
    identity_snapshot = identity_root / "data/holders_owners.json"
    identity_meta = identity_root / "data/holders_snapshot_meta.json"
    identity_receipt = identity_root / "data/identity_holders_receipt.json"
    emit_solana(SOL_MINT, SOL_SLOT, identity_snapshot, identity_meta, 100,
                identity_receipt)
    identity_binding = {
        "snapshot_file": "identity_bridge/data/holders_owners.json",
        "snapshot_sha256": sha_file(identity_snapshot),
        "receipt_file": "identity_bridge/data/identity_holders_receipt.json",
        "receipt_sha256": sha_file(identity_receipt),
        "as_of_block": SOL_SLOT, "complete_owner_universe": True,
        "receipt_schema": "identity-holder-snapshot/v2", "adapter": "sol",
    }
    write_json(root / "identity_gate.json", {
        "schema": "identity_gate_v3", "chain": "solana", "verdict": "PASS",
        "state_file": "analysis-state.json",
        "state_sha256": sha_file(root / "analysis-state.json"),
        "share_basis": "total_supply", "total_supply_raw": "100",
        "snapshot_binding": identity_binding, "rows": [],
    })
    write_json(root / "whale_series.json", [])
    fff = HERE.parent / "report/figures_from_facts.py"
    p = subprocess.run([sys.executable, str(fff), "check", "--facts", "facts.json",
                        "--series", "whale_series.json"], cwd=root,
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    write_json(root / "a4_seal.json", {"schema": "a4-seal/v4", "verdict": "PASS",
        "chain": "solana", "workflow_type": "new-analysis", "revision": 1,
        "previous_seal": None, "charts_dir": "charts/final",
        "claims": [{"id": "C1", "verdict": "CONFIRMED"}]})
    p = run_formal_script(dist, ["--case-dir", str(root), "--stage", "final", "--round", "1"])
    assert p.returncode == 0, p.stdout + p.stderr
    p = run_formal_script(dist, ["record-round", "--case-dir", str(root),
                                 "--scan", "dist_rounds/round_1/distribution_scan.json"])
    assert p.returncode == 0, p.stdout + p.stderr
    final_scan = json.loads(
        (root / "dist_rounds/round_1/distribution_scan.json").read_text())
    sentence = ("形态统计因样本不足未做,以逐址集中度事实替代"
                if final_scan.get("not_evaluable_reason") == "low_sample"
                else "当前快照呈正常形态;这只表示本闸未检出结构性畸形,不等于没有庄。")
    report.write_text(report.read_text(encoding="utf-8") + "\n" + sentence
                      + "\n\n![持仓分布](charts/final/holder_distribution_current.png)\n",
                      encoding="utf-8")
    p = subprocess.run([sys.executable, str(fff), "fig1", "--state",
                        "analysis-state.json", "--out", "charts/final/fig1.png"],
                       cwd=root, capture_output=True, text=True)
    assert p.returncode == 0 and (root / "fig1_legend_receipt.json").is_file(), \
        p.stdout + p.stderr
    report.write_text(report.read_text(encoding="utf-8")
                      + "\n![阵营演变](charts/final/fig1.png)\n", encoding="utf-8")
    a5 = HERE.parent / "report/a5_report_seal.py"
    p = run_formal_script(a5, ["--case-dir", str(root), "--report", str(report),
                               "--a4-seal", str(root / "a4_seal.json"),
                               "--out", str(root / "a5_report_seal.json")])
    assert p.returncode == 0, p.stdout + p.stderr
    return report


def t_b1_b2_solana_new_analysis():
    import audit_release_gate as gate
    from solana_observation import validate_observation_bundle
    with tempfile.TemporaryDirectory(prefix="d-sol-e2e-", dir="/private/tmp") as raw:
        root = Path(raw)
        report = build_solana_case(root)
        errors = gate.run(root, report, profile="new-analysis")
        check("B-2 Solana new-analysis run() 端到端绿例（发布闸零 error）",
              errors == [], errors[:6])

        # B-1 原反例：owners 实物换包（同值换仓：总和不变、owner 分配变）
        owners_path = root / "data/holders_owners.json"
        original = owners_path.read_bytes()
        write_json(owners_path, {"ownersol1": 40, "ownersol2": 60})
        bundle = json.loads((root / "supply_receipt.json").read_text())
        try:
            validate_observation_bundle(bundle, bundle_path=root / "supply_receipt.json")
            check("B-1 原反例：holder_outputs.owners 换包被 validator 三验拒", False, "放行了")
        except ValueError as exc:
            check("B-1 原反例：holder_outputs.owners 换包被 validator 三验拒",
                  "holder_outputs.owners" in str(exc), exc)
        errors = gate.run(root, report, profile="new-analysis")
        check("B-2 换仓后发布闸拒（端到端负例）", any("holder_outputs" in x or "owner 快照" in x
                                                    for x in errors), errors[:4])
        # 换包文件删除 → 缺件拒
        owners_path.write_bytes(original)
        assert gate.run(root, report, profile="new-analysis") == []
        owners_path.unlink()
        try:
            validate_observation_bundle(bundle, bundle_path=root / "supply_receipt.json")
            check("B-1 缺件：owners 实物不存在被拒", False, "放行了")
        except ValueError as exc:
            check("B-1 缺件：owners 实物不存在被拒", "not found" in str(exc), exc)


# ================= 消化轮 1（F-D1~F-D8；F-D1 用例并入 t_f06_a5_disclosure）=================

def t_fd2_unseal_binds_flip_receipt():
    """F-D2：冻结绑定清单含 flip 裁决收据——冻结后改写/删除收据 check-unseal 必拒。"""
    import handoff_manifest as hm
    with tempfile.TemporaryDirectory(prefix="d-fd2-", dir="/private/tmp") as raw:
        root = Path(raw)
        receipt = write_json(root / "flip_adjudications.json", {"schema": "flip-adjudications/v1",
                                                                "marker": "frozen-content"})
        members = write_json(root / "analysis-state.json", {"m": 1})
        entity = write_json(root / "entities.json", {"E1": ["a"]})
        manifest = write_json(root / "handoff_manifest.json", {"run_id": "x"})
        data_map = write_json(root / "data_map.json", {"files": []})
        receipt_digest, receipt_size = hm.full_sha256_file(str(receipt))
        trace_path = HERE.parent / "report/entity_source_trace.py"
        trace_digest, trace_size = hm.full_sha256_file(str(trace_path))
        wave_path = HERE.parent / "report/wave_scan.py"
        wave_digest, wave_size = hm.full_sha256_file(str(wave_path))
        ledger = write_json(root / "provenance_ledger.json", {
            "schema": "provenance-ledger/v2",
            "input_binding": {
                "algorithm": {"files": {
                    "entity_source_trace.py": {
                        "path": str(trace_path),
                        "bytes": trace_size,
                        "sha256": trace_digest},
                    "wave_scan.py": {
                        "path": str(wave_path),
                        "bytes": wave_size,
                        "sha256": wave_digest}}},
                "algorithm_params": {
                    "flip_adjudications": {"path": "flip_adjudications.json",
                                           "bytes": receipt_size,
                                           "sha256": receipt_digest}}}})
        def digest(p):
            return hm.sha256_file(p)[1]
        write_json(root / "entity_freeze.json", {
            "schema": "entity-freeze/v1",
            "members_source": "analysis-state.json", "members_sha256": digest(members),
            "entity_file": "entities.json", "entity_file_sha256": digest(entity),
            "provenance_ledger_sha256": digest(ledger),
            "manifest_sha256": digest(manifest), "data_map_sha256": digest(data_map),
            "frozen_at_utc": "2026-08-13T00:00:00Z", "revisions": []})

        def unseal():
            proc = subprocess.run([sys.executable,
                                   str(HERE.parent / "report/handoff_manifest.py"),
                                   "freeze", "--case-dir", str(root), "--check-unseal"],
                                  capture_output=True, text=True)
            return proc.returncode, proc.stdout + proc.stderr
        rc, out = unseal()
        check("F-D2 基线：收据原样 check-unseal 放行", rc == 0, out[-200:])
        original = receipt.read_bytes()
        doc = json.loads(original)
        doc["marker"] = "冻结后偷偷换的内容"
        write_json(receipt, doc)
        rc, out = unseal()
        check("F-D2 原反例①：冻结后改写收据 → check-unseal rc=2",
              rc == 2 and ("漂移" in out or "flip" in out), out[-200:])
        receipt.unlink()
        rc, out = unseal()
        check("F-D2 原反例②：冻结后删除收据 → check-unseal rc=2",
              rc == 2 and "不存在" in out, out[-200:])
        receipt.write_bytes(original)
        rc, _ = unseal()
        check("F-D2 复原后再放行（绑定即字节）", rc == 0, rc)


def t_fd4_receipt_sanity():
    """F-D4：裁决面形式 sanity——占位主体/荒谬时间/垃圾字节证据三红例。"""
    import handoff_manifest as hm
    with tempfile.TemporaryDirectory(prefix="d-fd4-", dir="/private/tmp") as raw:
        tmp = Path(raw)
        _flip_case(tmp)
        _, ledger = _run_trace(tmp)
        receipt_path = _make_flip_receipt(tmp, ledger)
        base = json.loads(receipt_path.read_text())
        scenarios = [
            ("裁决主体单字符占位 x", lambda d: d.update(approved_by="x"), "占位"),
            ("时间 1970（荒谬时间戳）",
             lambda d: d.update(user_decided_at_utc="1970-01-01T00:00:00Z"), "时间范围"),
            ("未来一年（预签收据）",
             lambda d: d.update(user_decided_at_utc="2027-12-31T00:00:00Z"), "时间范围"),
        ]
        for label, mutate, needle in scenarios:
            doc = json.loads(json.dumps(base))
            mutate(doc)
            write_json(receipt_path, doc)
            try:
                hm.load_flip_adjudications(receipt_path,
                                           current_entity_file=tmp / "entities.json")
                check(f"F-D4 被拒：{label}", False, "放行了")
            except ValueError as exc:
                check(f"F-D4 被拒：{label}", needle in str(exc), exc)
        # 1 字节垃圾证据
        junk = tmp / "junk.bin"
        junk.write_bytes(b"j")
        doc = json.loads(json.dumps(base))
        doc["evidence_refs"] = [{"path": "junk.bin", "size": 1, "sha256": sha_file(junk)}]
        write_json(receipt_path, doc)
        try:
            hm.load_flip_adjudications(receipt_path, current_entity_file=tmp / "entities.json")
            check("F-D4 被拒：1 字节垃圾证据文件", False, "放行了")
        except ValueError as exc:
            check("F-D4 被拒：1 字节垃圾证据文件", "过小" in str(exc), exc)


def t_fd5_gptf06_two_missing_cells():
    """F-D5：deep 全 fetch_failed 独立判据锁＋CLEAN 正例格。"""
    with tempfile.TemporaryDirectory(prefix="d-fd5-", dir="/private/tmp") as raw:
        tmp = Path(raw)
        _fake_edges(tmp / "edges.jsonl.gz",
                    [[1, 100, 0, -1, "OWN1", "OWN2", 5],
                     [2, 150, 0, -1, "OWN1", "OWN3", 5],
                     [3, 200, 0, -1, "OWN2", "OWN3", 5]])

        # deep 全 fetch_failed：签名史直接失败（返回 None）
        def rpc_deep_fetch_fail(self, method, params, retries=4):
            if method == "getBlock":
                return _block_with_init(params[0])
            if method == "getMultipleAccounts":
                return {"value": [None for _ in params[0]]}  # 全销户
            if method == "getSignaturesForAddress":
                return None  # 深挖拉取失败 → fetch_failed
            return None
        rc, report = _run_closed_audit(tmp, rpc_deep_fetch_fail)
        check("F-D5 深挖全 fetch_failed → exit 1（独立判据，有测试锁）",
              rc == 1 and report["status"] == "INVALID_SAMPLE"
              and any("全部 fetch_failed" in x for x in report["invalid_reasons"]),
              (rc, report and report.get("invalid_reasons")))

        # CLEAN：销户账户深挖到区间内事件且边集覆盖 → exit 0 充分零漏
        def rpc_clean(self, method, params, retries=4):
            if method == "getBlock":
                return _block_with_init(params[0])
            if method == "getMultipleAccounts":
                return {"value": [None for _ in params[0]]}
            if method == "getSignaturesForAddress":
                return [{"signature": "SIGC", "slot": 150, "err": None}]
            if method == "getTransaction":
                return {"meta": {"err": None,
                                 "preTokenBalances": [{"mint": "MINTx", "accountIndex": 0,
                                                        "owner": "OWN1",
                                                        "uiTokenAmount": {"amount": "9"}}],
                                 "postTokenBalances": [{"mint": "MINTx", "accountIndex": 0,
                                                         "owner": "OWN1",
                                                         "uiTokenAmount": {"amount": "2"}}]},
                        "transaction": {"message": {"accountKeys": ["ACC1"],
                                                     "instructions": []}}}
            return None
        rc, report = _run_closed_audit(tmp, rpc_clean)
        check("F-D5 CLEAN 正例格：checked>0 零漏 → exit 0 status=CLEAN",
              rc == 0 and report["status"] == "CLEAN"
              and report["events"] == {"checked": 1, "covered": 1, "missing": 0,
                                        "out_of_range": 0}
              and report["invalid_reasons"] == [],
              (rc, report and report.get("status"), report and report.get("events")))


def t_fd6_prepare_leak():
    """F-D6：prepare 期失败不泄漏临时件（写到一半的 tmp 也在清理范围内）。"""
    import fetch_hypersync_v2 as fh
    from test_apu_legacy_gaps import _make_prehistoric_v2_run

    def log_row(block):
        return (0, "0x" + "1" * 64, "0x" + "2" * 64, block,
                "0x" + format(7, "x").rjust(64, "0"),
                "0x" + "a" * 64, "0x" + "b" * 64)

    with tempfile.TemporaryDirectory(prefix="d-fd6-", dir="/private/tmp") as raw:
        root = Path(raw)
        _make_prehistoric_v2_run(root, 0, rows=[log_row(5)], blocks=[(5, hex(1000))])
        _make_prehistoric_v2_run(root, 100, rows=[log_row(105)], blocks=[(105, hex(2000))])
        fh.recover_identity(root)
        dones = sorted(root.glob("run_*/done.json"))
        originals = {p: p.read_bytes() for p in dones}
        real_dump = json.dump
        calls = {"n": 0}

        def inject(obj, fp, **kw):
            calls["n"] += 1
            if calls["n"] == 2:  # prepare 第二个 tmp 写到一半
                fp.write("{\"half\":")  # 先污染半截再抛——逼清理面对半成品
                raise OSError("prepare io injected")
            return real_dump(obj, fp, **kw)

        with mock.patch.object(fh.json, "dump", inject), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            rc = fh.refresh_manifests_cli(["--refresh-manifests", "--outdir", str(root),
                                           "--capture-from", "0"])
        residue = list(root.rglob(".*refresh-tmp*")) + list(root.rglob(".*refresh-bak*"))
        after = {p: p.read_bytes() for p in dones}
        check("F-D6 prepare 注入命中标志（第 2 次 json.dump）",
              calls["n"] == 2 and "prepare io injected" in err.getvalue(),
              (calls["n"], err.getvalue()[:150]))
        check("F-D6 prepare 期失败：正式件原样＋零临时件泄漏＋exit 2",
              rc == 2 and after == originals and residue == [],
              (rc, [x.name for x in residue]))


def t_fd7_receipt_path_unification():
    """F-D7：收据三处口径统一（案根内＋ledger sha 互绑）——改名不误伤、换收据必失配。"""
    import a5_report_seal as a5
    import handoff_manifest as hm
    with tempfile.TemporaryDirectory(prefix="d-fd7-", dir="/private/tmp") as raw:
        tmp = Path(raw)
        _flip_case(tmp)
        _, ledger0 = _run_trace(tmp)
        # 改名收据（案根内）：trace 放行、A5 按 ledger 绑定定位——不误伤
        receipt = _make_flip_receipt(tmp, ledger0)
        renamed = tmp / "flips_receipt.json"
        renamed.write_bytes(receipt.read_bytes())
        receipt.unlink()
        proc, ledger = _run_trace(tmp, "--acknowledge-flip", str(renamed))
        assert proc.returncode == 0, proc.stdout + proc.stderr
        _, ledger_sha, _ = hm.sha256_file(tmp / "provenance_ledger.json")
        write_json(tmp / "entity_freeze.json", {"schema": "entity-freeze/v1",
                                                "provenance_ledger_sha256": ledger_sha,
                                                "revisions": []})
        real = hm.ledger_real_flips(ledger)
        parts = ["# 报告", "## 翻转披露"]
        for info in real.values():
            for policy in hm.FLIP_POLICIES:
                parts.append(f"{policy}: {info['tops'][policy][2]} 占 {info['shares'][policy]}%")
        good_text = "\n".join(parts)
        a4obj = {"workflow_type": "new-analysis"}
        bundle = a5.provenance_flip_bundle(tmp, good_text, a4obj)
        check("F-D7 改名收据合法案不再被 A5 误伤（按 ledger 绑定定位）",
              bundle["status"] == "DISCLOSED"
              and bundle["receipt"]["path"] == "flips_receipt.json", bundle.get("receipt"))
        # 换收据（同名另一份、裁决人被换）→ A5 sha 互绑拒（封"甲过 freeze 乙过 A5"）
        doc = json.loads(renamed.read_text())
        doc["approved_by"] = "完全没参与过的另一个人"
        write_json(renamed, doc)
        try:
            a5.provenance_flip_bundle(tmp, good_text, a4obj)
            check("F-D7 换收据（改裁决人）被 A5 sha 互绑拒", False, "放行了")
        except ValueError as exc:
            check("F-D7 换收据（改裁决人）被 A5 sha 互绑拒", "不符" in str(exc), exc)
        # trace 拒案外收据（口径统一第三角）
        with tempfile.TemporaryDirectory(prefix="d-fd7-out-", dir="/private/tmp") as outer:
            outside = Path(outer) / "receipt.json"
            outside.write_bytes(json.dumps(json.loads(
                renamed.read_text()) | {"approved_by": "用户"},
                ensure_ascii=False).encode())
            proc2, _ = _run_trace(tmp, "--acknowledge-flip", str(outside))
            check("F-D7 trace 拒案外收据（三处口径＝案根内）",
                  proc2.returncode == 2 and "案根" in proc2.stdout + proc2.stderr,
                  (proc2.returncode, (proc2.stdout + proc2.stderr)[-150:]))


def t_fd8_boundaries():
    """F-D8：双删由发布闸 final_bindings 锚拦截＋审计早退落报告＋A-1 参数错不归档。"""
    import audit_release_gate as gate
    # ① 完整 new-analysis 案删 freeze → 发布闸红（F-D8 落点＝发布闸重验 A5 seal，
    #    A5 的 final scan 绑定链把 entity_freeze 钉进发布必经路；单元层 NO_LEDGER
    #    是无溯源案语义，双删的机器锚在这一层）
    with tempfile.TemporaryDirectory(prefix="d-fd8-", dir="/private/tmp") as raw:
        root = Path(raw)
        report = build_solana_case(root)
        assert gate.run(root, report, profile="new-analysis") == []
        (root / "entity_freeze.json").unlink()
        errors = gate.run(root, report, profile="new-analysis")
        check("F-D8 双删绕路：删 entity_freeze 后发布闸拒（A5 seal 重验接入发布必经路）",
              any("A5 seal 重验" in x and ("entity_freeze" in x or "final 绑定" in x)
                  for x in errors), errors[:4])
        # 缺 --report 时 fail-closed（A5 seal 在场却无法重验＝拒）
        errors = gate.run(root, None, profile="new-analysis")
        check("F-D8 new-analysis 缺 --report 无法重验 A5 → fail-closed",
              any("--report" in x for x in errors), errors[:3])
    # ② 审计早退也落 status 报告
    with tempfile.TemporaryDirectory(prefix="d-fd8b-", dir="/private/tmp") as raw:
        tmp = Path(raw)

        def rpc_never(self, method, params, retries=4):
            return None
        rc, report = _run_closed_audit(tmp, rpc_never)  # 边集文件不存在
        check("F-D8 早退（边集缺失）也落 INVALID_SAMPLE 报告",
              rc == 1 and report and report["status"] == "INVALID_SAMPLE"
              and any("边集不存在" in x for x in report["invalid_reasons"]),
              (rc, report))
    # ③ A-1 参数错（负容差）不归档旧收据
    with tempfile.TemporaryDirectory(prefix="d-fd8c-", dir="/private/tmp") as raw:
        root = Path(raw)
        rc = _run_supply_pass(root)
        assert rc == 0
        from test_repair_batch_a import run_supply
        rc2, _, stderr2 = run_supply(root, tolerance=-5)
        archived = list(root.glob("supply_truth.json.superseded-*"))
        check("F-D8 参数错误（负容差）exit 2 且**不**作废旧收据",
              rc2 == 2 and archived == [] and (root / "supply_truth.json").is_file()
              and "参数错误" in stderr2, (rc2, archived, stderr2[-150:]))


def t_fd3_e2e_single_case_evm():
    """F-D3：同一案内连续走完 state_from_facts→figures check→A4 finalize→A5 seal（EVM）。

    数据面＝批 C 真实 replay（replay_duck 产 series/sidecar/balances_final，含 burn
    ——mint 1000/burn 50 的 dead-sink 形态）；接缝＝figures 真实产物
    （figure2_check_receipt.json）与 state 编译产物（analysis-state.json）被 A4 finalize
    在**同案**封口，A5 在**同案**收口。plan :95 的连续链不再由两案拼接冒充。"""
    import test_repair_batch_c as batch_c
    from formal_ready_test_harness import run_formal_script
    with tempfile.TemporaryDirectory(prefix="d-fd3-", dir="/private/tmp") as raw:
        root = Path(raw)
        spec = {"camps": {"项目方": [batch_c.A], "大庄": [batch_c.B]},
                "entities": {"e1": [batch_c.B]}}
        batch_c.build_evm_case(root, spec)          # ① 真跑 replay_duck（series+sidecar）
        batch_c.write_supply_truth(root)
        batch_c.write_facts_source(root)
        p = batch_c.compile_state_cli(root, "--series-source", "data/camp_series.json")
        check("F-D3 ① state_from_facts formal 编译（series 绑定链）",
              p.returncode == 0
              and json.loads((root / "analysis-state.json").read_text())
              ["provenance"]["series_binding"] == "producer-sidecar",
              (p.returncode, (p.stdout + p.stderr)[-300:]))
        # ② figures check：图 2 装配数据对 facts 终值（e1 current 350/950）
        want = 350 / 950 * 100
        write_json(root / "whale_series.json",
                   [{"entity_id": "e1", "label": "大庄#1", "pct": [round(want, 4)]}])
        fff = HERE.parent / "report/figures_from_facts.py"
        p = subprocess.run([sys.executable, str(fff), "check", "--facts", "facts.json",
                            "--series", "whale_series.json"], cwd=root,
                           capture_output=True, text=True)
        receipt = root / "figure2_check_receipt.json"
        check("F-D3 ② figures check 末点对账＋留痕收据（同案）",
              p.returncode == 0 and receipt.is_file()
              and json.loads(receipt.read_text()).get("verdict") == "PASS",
              (p.returncode, p.stdout + p.stderr))
        # 分布 initial（A4 finalize 的 new-analysis 分布源要求）：快照＝真实 replay 终态
        write_json(root / "data_map.json", {"files": [
            {"path": "data/balances_final.json",
             "sha256": sha_file(root / "data/balances_final.json")}]})
        write_json(root / "candidate_screening.json", {"auto_excluded_candidate": []})
        dist = HERE.parent / "report/holder_distribution_scan.py"
        p = run_formal_script(dist, ["--case-dir", str(root), "--stage", "initial"])
        assert p.returncode == 0, p.stdout + p.stderr
        # ③ A4 register→finalize：真封 figures/state 两件产物（接缝在同案传递）。
        # MANDATORY_SEAL_FILES 四件（findings/state/facts/identity_gate）补齐后，
        # figure2 收据作为第五件一并封口。
        (root / "findings.md").write_text("# findings\n大庄#1 现仓 350。\n", encoding="utf-8")
        write_json(root / "identity_gate.json", {"chain": "bsc", "verdict": "PASS"})
        gate_cli = HERE.parent / "report/a4_gate.py"
        claims = write_json(root / "claims_in.json", [
            {"id": "C1", "text": "大庄#1 现仓 350（36.84% 供应）",
             "files": ["data/balances_final.json"], "report_locations": ["report.md:1"]}])
        p = subprocess.run([sys.executable, str(gate_cli), "register", "--case-dir",
                            str(root), "--claims-file", str(claims)],
                           capture_output=True, text=True)
        assert p.returncode == 0, p.stdout + p.stderr
        verdicts = write_json(root / "verdicts.json", [{"id": "C1", "verdict": "CONFIRMED"}])
        p = subprocess.run([sys.executable, str(gate_cli), "finalize", "--case-dir",
                            str(root), "--verdicts-file", str(verdicts),
                            "--seal-files",
                            "findings.md,analysis-state.json,facts.json,identity_gate.json,"
                            "figure2_check_receipt.json",
                            "--workflow-type", "new-analysis"],
                           capture_output=True, text=True)
        seal = root / "a4_seal.json"
        check("F-D3 ③ A4 finalize 同案封口 figures/state 产物",
              p.returncode == 0 and seal.is_file()
              and json.loads(seal.read_text()).get("workflow_type") == "new-analysis",
              (p.returncode, (p.stdout + p.stderr)[-400:]))
        # 分布终态链（final scan→record-round→LOW_SAMPLE terminal）
        for name, value in {
            "handoff_manifest.json": {"consumer_min_schema": "handoff/v3",
                                      "status": "READY", "run_id": "fd3"},
            "identity_snapshot_receipt.json": {"schema": "identity-snapshot-receipt/v1"},
            "entity_freeze.json": {"schema": "entity-freeze/v1", "revisions": []},
            "membership_ledger.json": {"rows": []},
            "position_ledger.json": {"rows": []},
            "economic_control_ledger.json": {"rows": []},
            "address_classification.json": {"rows": []},
        }.items():
            write_json(root / name, value)
        p = run_formal_script(dist, ["--case-dir", str(root), "--stage", "final",
                                     "--round", "1"])
        assert p.returncode == 0, p.stdout + p.stderr
        p = run_formal_script(dist, ["record-round", "--case-dir", str(root),
                                     "--scan", "dist_rounds/round_1/distribution_scan.json"])
        assert p.returncode == 0, p.stdout + p.stderr
        final_scan = json.loads(
            (root / "dist_rounds/round_1/distribution_scan.json").read_text())
        sentence = ("形态统计因样本不足未做,以逐址集中度事实替代"
                    if final_scan.get("not_evaluable_reason") == "low_sample"
                    else "当前快照呈正常形态;这只表示本闸未检出结构性畸形,不等于没有庄。")
        report = root / "report.md"
        report.write_text("# 同案端到端报告\n大庄#1 现仓 350。\n" + sentence
                          + "\n\n![持仓分布](charts/final/holder_distribution_current.png)\n",
                          encoding="utf-8")
        fff = HERE.parent / "report/figures_from_facts.py"
        p = subprocess.run([sys.executable, str(fff), "fig1", "--state",
                            "analysis-state.json", "--out", "charts/final/fig1.png"],
                           cwd=root, capture_output=True, text=True)
        check("F-D3 ④前置：fig1 producer 落 legend receipt",
              p.returncode == 0 and (root / "fig1_legend_receipt.json").is_file(),
              (p.returncode, (p.stdout + p.stderr)[-400:]))
        report.write_text(report.read_text(encoding="utf-8")
                          + "\n![阵营演变](charts/final/fig1.png)\n", encoding="utf-8")
        # ④ A5 seal 同案收口
        a5 = HERE.parent / "report/a5_report_seal.py"
        p = run_formal_script(a5, ["--case-dir", str(root), "--report", str(report),
                                   "--a4-seal", str(seal),
                                   "--out", str(root / "a5_report_seal.json")])
        check("F-D3 ④ A5 seal 同案收口（state→figures→A4→A5 全链一案贯通）",
              p.returncode == 0 and (root / "a5_report_seal.json").is_file(),
              (p.returncode, (p.stdout + p.stderr)[-400:]))


def main():
    t_f07_refresh_transaction()
    t_gptf06_closed_audit()
    t_f06_trace_receipt_chain()
    t_f06_receipt_unit_negatives()
    t_f06_a5_disclosure()
    t_a1_policy_reject_invalidates_receipt()
    t_b4_b5_bound_stats()
    t_a3_relative_inputs_and_portability()
    t_a5_same_source_negative()
    t_b7_ledger_snapshot_binding()
    t_b1_b2_solana_new_analysis()
    # 消化轮 1
    t_fd2_unseal_binds_flip_receipt()
    t_fd4_receipt_sanity()
    t_fd5_gptf06_two_missing_cells()
    t_fd6_prepare_leak()
    t_fd7_receipt_path_unification()
    t_fd8_boundaries()
    t_fd3_e2e_single_case_evm()
    print("=" * 48)
    if FAILS:
        print(f"BATCH D FAIL {len(FAILS)}: {FAILS}")
        return 1
    print("BATCH D 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
