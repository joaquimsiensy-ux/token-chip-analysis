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
        return sorted(root.glob("run_*/done.json"))

    # 绿例：正常迁移全部升 v3 且 identity 建立
    with tempfile.TemporaryDirectory(prefix="d-f07-green-", dir="/private/tmp") as raw:
        root = Path(raw)
        dones = make_two_prehistoric(root)
        rc = fh.refresh_manifests_cli(["--refresh-manifests", "--outdir", str(root)])
        upgraded = [json.loads(p.read_text())["schema"] for p in dones]
        check("F-07 绿例：太古双 run 迁移 exit 0 全升 v3",
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
            rc = fh.refresh_manifests_cli(["--refresh-manifests", "--outdir", str(root)])
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
            rc = fh.refresh_manifests_cli(["--refresh-manifests", "--outdir", str(root)])
        recover = list(root.rglob("*.recover"))
        check("F-07 回滚失败：exit 1＋.recover 恢复件保留＋stderr 指认混合状态",
              rc == 1 and len(recover) == 1 and "rollback-failed" in err.getvalue(),
              (rc, [x.name for x in recover], err.getvalue()[:200]))

    # CLI 捕 OSError（罩住 ensure_outdir_identity 的 IO 故障）：只读 outdir 写 identity 失败
    if os.geteuid() != 0:
        with tempfile.TemporaryDirectory(prefix="d-f07-oserr-", dir="/private/tmp") as raw:
            root = Path(raw)
            make_two_prehistoric(root)
            os.chmod(root, 0o500)
            try:
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    rc = fh.refresh_manifests_cli(
                        ["--refresh-manifests", "--outdir", str(root)])
            finally:
                os.chmod(root, 0o700)
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
                    [[1, 100, "OWN1", "OWN2", 5], [2, 200, "OWN2", "OWN3", 5]])

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
    proc = subprocess.run(
        [sys.executable, str(HERE.parent / "report/entity_source_trace.py"),
         "--edges-sol", str(tmp / "edges.jsonl.gz"), "--total-supply", "1000000",
         "--entity-file", str(tmp / "entities.json"),
         "--labels-file", str(tmp / "labels.json"),
         "--out", str(tmp / "provenance_ledger.json"), *extra],
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
                     "disclosure": {"top_by_policy": tbp,
                                    "report_locations": ["report.md §翻转披露"]}})
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
        # 报告含全部披露值 → DISCLOSED
        parts = ["# 报告", "## 翻转披露"]
        for info in real.values():
            for policy in hm.FLIP_POLICIES:
                terminal = info["tops"][policy]
                parts.append(f"{policy}: {terminal[2]} 占 {info['shares'][policy]}%")
        good_text = "\n".join(parts)
        bundle = a5.provenance_flip_bundle(tmp, good_text, a4obj)
        check("F-06 A5 绿例：报告实文含三策略 top 与份额 → DISCLOSED",
              bundle["status"] == "DISCLOSED" and bundle["anchors"], bundle)
        # 报告缺份额数字 → 拒（原反例：只验 claim 在场挡不住无关文本）
        try:
            a5.provenance_flip_bundle(tmp, "# 报告\n只字未提翻转。", a4obj)
            check("F-06 A5 原反例：报告缺披露值被拒", False, "放行了")
        except ValueError as exc:
            check("F-06 A5 原反例：报告缺披露值被拒", "并列披露" in str(exc), exc)
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
    import supply_truth_gate as supply
    (root / "replay_stats.json").write_text(
        json.dumps({"mint_total_raw": "100", "burn_total_raw": "0"}), encoding="utf-8")
    argv = ["--chain", "eth", "--token", TOKEN, "--as-of-block", "123",
            "--rpc", "offline://fixture", "--tolerance-bps", "10",
            "--replay-stats", "replay_stats.json", "--out", str(root / "supply_truth.json")]
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
        write_json(alt, {"mint_total_raw": "100", "burn_total_raw": "0", "alt": True})
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

SOL_MINT = "mintsol1111111111111111111111111111111111111"
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
        "schema": "wave-scan/v3", "scan_universe_count": 1,
        "scan_universe": [{"addr": "ownersol1", "peak_pct": 60.0,
                           "must_adjudicate": True, "must_reasons": ["peak_ge_0.1pct"]}]})
    write_json(root / "dormant_warehouse_audit.json", {
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
    runner = REPO / "scripts/report/adversarial_review_runner.py"
    reviews = []
    for role in ("entity_attribution_skeptic", "completeness_critic"):
        entry = root / f"review_{role}.py"
        entry.write_text("import os\nfrom pathlib import Path\n"
                         "Path(os.environ['CHIP_REVIEW_OUTPUT']).write_text("
                         "'review evidence for '+os.environ['CHIP_REVIEW_ROLE']+'\\n')\n",
                         encoding="utf-8")
        artifact = root / f"review_{role}.md"
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
    write_json(root / "adversarial_review.json", {
        "schema": "adversarial-review/v2", "target": target, "reviews": reviews,
        "blocking_findings": [], "release_decision": "PASS"})
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
    for name, value in {
        "handoff_manifest.json": {"consumer_min_schema": "handoff/v3", "status": "READY",
                                  "run_id": "fixture-sol"},
        "identity_snapshot_receipt.json": {"schema": "identity-snapshot-receipt/v1"},
        "entity_freeze.json": {"schema": "entity-freeze/v1", "revisions": []},
        "analysis-state.json": {"chain": "solana", "whale_groups": []},
        "facts.json": {"token": {"symbol": "SOLX", "decimals": 0,
                                 "total_supply_raw": "100"}, "entities": {}},
        "evidence.json": {"source": "fixture"},
        "a4_claims.json": {"schema": "a4-claims/v2", "claims": [{"id": "C1"}]},
    }.items():
        write_json(root / name, value)
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
    print("=" * 48)
    if FAILS:
        print(f"BATCH D FAIL {len(FAILS)}: {FAILS}")
        return 1
    print("BATCH D 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
