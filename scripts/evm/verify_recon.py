#!/usr/bin/env python3
"""EVM 对账生产器：余额、供给闭合与 GMGN 对表，产绑定目标的 v3 回执。

退出码：0=全部硬检查 PASS；2=供给/余额硬不一致；1=输入、RPC 或写入失败。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from chain_registry import (executable_evm_chains, resolve_execution_mode)
from net import RpcChainMismatch, attested_rpc_pool
from receipt_kernel import (assert_distinct_paths, build_envelope, finalize_envelope,
                            publish_error_receipt, publish_txn)
from supply_semantics import DEAD, ZERO
SCHEMA = "evm-reconciliation-receipt/v3"
SCHEMA_FAMILY = "evm-reconciliation-receipt/"
GMGN_DIVERGENCE_NOTE_SCHEMA = "gmgn-divergence-note/v1"
GMGN_DIVERGENCE_WARNING = "gmgn_divergence"
GMGN_EXPLANATION_MIN_CHARS = 30
GMGN_DIVERGENCE_CAUSES = {
    "gmgn_data_lag", "methodology_diff", "gmgn_upstream_error",
}


class ReconFailure(ValueError):
    """A completed hard check failed (exit 2), as distinct from producer ERROR."""


class DivergenceNoteError(ValueError):
    """A supplied GMGN investigation note is invalid and must not replace output."""


def _json_bytes(payload):
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _future_input_ref(path, case_root, payload):
    resolved = Path(path).expanduser().resolve()
    root = Path(case_root).expanduser().resolve()
    try:
        shown = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("--transcript-out 必须落在 receipt 案根目录内") from exc
    data = _json_bytes(payload)
    return {"path": shown, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _file_input_ref(path, case_root):
    root = Path(case_root).expanduser().resolve()
    raw = Path(path).expanduser()
    lexical = raw if raw.is_absolute() else root / raw
    try:
        relative = lexical.relative_to(root)
    except ValueError as exc:
        raise ValueError("GMGN 查证说明必须落在 receipt 案根目录内") from exc
    if not relative.parts or ".." in relative.parts:
        raise ValueError("GMGN 查证说明必须使用案根内安全路径")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("GMGN 查证说明不得是符号链接")
    try:
        resolved = lexical.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError("GMGN 查证说明不存在或越出案根") from exc
    if not resolved.is_file():
        raise ValueError("GMGN 查证说明必须是普通文件")
    data = resolved.read_bytes()
    return {"path": relative.as_posix(), "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def _meaningful_codepoint(char):
    point = ord(char)
    return (
        0x21 <= point <= 0x7E
        or (0x00A1 <= point <= 0x024F and point != 0x00AD)
        or 0x2010 <= point <= 0x2027
        or 0x3001 <= point <= 0x3029
        or 0x3030 <= point <= 0x303D
        or 0x3041 <= point <= 0x3096
        or 0x309B <= point <= 0x30FF
        or 0x3400 <= point <= 0x4DBF
        or 0x4E00 <= point <= 0x9FFF
        or 0xAC00 <= point <= 0xD7A3
        or 0xFF01 <= point <= 0xFF5E
    )


def _meaningful_text(value):
    return isinstance(value, str) and any(_meaningful_codepoint(char) for char in value)


def _meaningful_length(value):
    if not isinstance(value, str):
        return 0
    return sum(_meaningful_codepoint(char) for char in value)


def _reject_constant(value):
    raise ValueError(f"JSON 非有限数值 {value} 不允许")


def _canonical_request_sha256(request):
    raw = json.dumps(request, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _strict_utc(value, label):
    try:
        if not isinstance(value, str) or len(value) != 20:
            raise ValueError
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"{label} 必须是 YYYY-MM-DDTHH:MM:SSZ") from exc
    if parsed > datetime.now(timezone.utc) + timedelta(days=1):
        raise ValueError(f"{label} 不得晚于当前时间 1 天")
    return parsed


def _decimal_string(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须是 Decimal 规范字符串")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} 不是合法 Decimal") from exc
    if not parsed.is_finite() or str(parsed) != value:
        raise ValueError(f"{label} 必须是有限 Decimal 规范字符串")
    return value


def _validate_divergences(value, label):
    if not isinstance(value, list):
        raise ValueError(f"{label} 必须是有序数组")
    normalized = []
    seen = set()
    keys = {"address", "gmgn_pct", "replay_pct", "diff_pp"}
    for index, row in enumerate(value):
        if not isinstance(row, dict) or set(row) != keys:
            raise ValueError(f"{label}[{index}] 字段不完整或含额外项")
        address = row.get("address")
        if not isinstance(address, str) or not address or address != address.lower():
            raise ValueError(f"{label}[{index}].address 必须是非空小写字符串")
        if address in seen:
            raise ValueError(f"{label} 地址重复: {address}")
        seen.add(address)
        normalized.append({
            "address": address,
            "gmgn_pct": _decimal_string(row.get("gmgn_pct"),
                                         f"{label}[{index}].gmgn_pct"),
            "replay_pct": _decimal_string(row.get("replay_pct"),
                                           f"{label}[{index}].replay_pct"),
            "diff_pp": _decimal_string(row.get("diff_pp"),
                                        f"{label}[{index}].diff_pp"),
        })
    return normalized


def _validate_gmgn_divergence_note(case_root, note_path, target, input_refs,
                                   divergences):
    """Producer-side independent validator for the manual GMGN note."""
    root = Path(case_root).expanduser().resolve()
    note_ref = _file_input_ref(note_path, root)
    path = root / note_ref["path"]
    try:
        note = json.loads(path.read_text(encoding="utf-8"),
                          parse_constant=_reject_constant)
    except (OSError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"GMGN 查证说明 JSON 非法: {exc}") from exc
    required = {
        "schema", "request", "request_sha256", "findings", "conclusion",
        "investigator", "investigated_at_utc",
    }
    if not isinstance(note, dict) or set(note) != required:
        raise ValueError("GMGN 查证说明字段必须完整且无额外项")
    if note.get("schema") != GMGN_DIVERGENCE_NOTE_SCHEMA:
        raise ValueError(f"GMGN 查证说明 schema 必须是 {GMGN_DIVERGENCE_NOTE_SCHEMA}")
    request = note.get("request")
    if not isinstance(request, dict) or set(request) != {
            "target", "inputs_sha256", "divergences"}:
        raise ValueError("GMGN 查证说明 request 字段必须完整且无额外项")
    if request.get("target") != target:
        raise ValueError("GMGN 查证说明 request.target 与本次目标不全等")
    hashes = request.get("inputs_sha256")
    hash_keys = {"config", "balances", "replay_stats", "gmgn"}
    if not isinstance(hashes, dict) or set(hashes) != hash_keys:
        raise ValueError("GMGN 查证说明 inputs_sha256 字段不完整")
    for key in sorted(hash_keys):
        shown = hashes.get(key)
        expected = (input_refs.get(key) or {}).get("sha256")
        if (not isinstance(shown, str) or len(shown) != 64
                or any(char not in "0123456789abcdef" for char in shown)
                or shown != expected):
            raise ValueError(f"GMGN 查证说明 inputs_sha256.{key} 与本次输入不一致")
    shown_divergences = _validate_divergences(
        request.get("divergences"), "GMGN 查证说明 request.divergences")
    expected_divergences = _validate_divergences(divergences, "本次 GMGN divergences")
    if shown_divergences != expected_divergences:
        raise ValueError("GMGN 查证说明未完整覆盖当前重算差异集合")
    if note.get("request_sha256") != _canonical_request_sha256(request):
        raise ValueError("GMGN 查证说明 request_sha256 与 request 重算不一致")
    findings = note.get("findings")
    if not isinstance(findings, list) or len(findings) != len(expected_divergences):
        raise ValueError("GMGN 查证说明 findings 未逐项覆盖 divergences")
    for index, (finding, divergence) in enumerate(zip(findings, expected_divergences)):
        if not isinstance(finding, dict) or set(finding) not in (
                {"address", "cause", "explanation"},
                {"address", "cause", "explanation", "evidence_refs"}):
            raise ValueError(f"GMGN 查证说明 findings[{index}] 字段非法")
        if finding.get("address") != divergence["address"]:
            raise ValueError(f"GMGN 查证说明 findings[{index}] 地址覆盖不一致")
        if finding.get("cause") not in GMGN_DIVERGENCE_CAUSES:
            raise ValueError(f"GMGN 查证说明 findings[{index}].cause 非法")
        explanation = finding.get("explanation")
        if (not _meaningful_text(explanation)
                or _meaningful_length(explanation) < GMGN_EXPLANATION_MIN_CHARS):
            raise ValueError(
                f"GMGN 查证说明 findings[{index}].explanation 至少需 "
                f"{GMGN_EXPLANATION_MIN_CHARS} 个实义字符")
        if "evidence_refs" in finding:
            refs = finding["evidence_refs"]
            if not isinstance(refs, list):
                raise ValueError(f"GMGN 查证说明 findings[{index}].evidence_refs 非法")
            for ref_index, ref in enumerate(refs):
                evidence_raw = Path(str((ref or {}).get("path") or ""))
                if evidence_raw.is_absolute() or not evidence_raw.parts or ".." in evidence_raw.parts:
                    raise ValueError("GMGN 查证说明 evidence_refs 必须是安全相对路径")
                evidence_path = path.parent / evidence_raw
                actual = _file_input_ref(evidence_path, root)
                if (not isinstance(ref, dict) or not {"path", "size", "sha256"} <= set(ref)
                        or ref.get("size") != actual["size"]
                        or ref.get("sha256") != actual["sha256"]):
                    raise ValueError(
                        f"GMGN 查证说明 findings[{index}].evidence_refs[{ref_index}] 绑定不一致")
    conclusion = note.get("conclusion")
    if (not _meaningful_text(conclusion)
            or "重放数据经查证无误" not in conclusion):
        raise ValueError("GMGN 查证说明 conclusion 缺少重放数据经查证无误承诺")
    if not _meaningful_text(note.get("investigator")):
        raise ValueError("GMGN 查证说明 investigator 必须含实义字符")
    _strict_utc(note.get("investigated_at_utc"),
                "GMGN 查证说明 investigated_at_utc")
    return note


def rpc_balance_of(pool, token, address, block, transcript):
    data = "0x70a08231" + "0" * 24 + address.lower().replace("0x", "")
    params = [{"to": token, "data": data}, hex(int(block))]
    response = pool.call("eth_call", params)
    raw = response.get("result")
    if not response.get("ok") or not isinstance(raw, str) or raw in ("", "0x"):
        raise ValueError(f"eth_call 无有效 result: {response.get('error') or raw!r}")
    transcript.append({"seq": len(transcript), "method": "eth_call",
                       "params": params, "result": raw})
    return int(raw, 16)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--balances", required=True)
    ap.add_argument("--replay-stats", required=True)
    ap.add_argument("--gmgn", required=True)
    ap.add_argument("--chain", required=True,
                    choices=sorted(executable_evm_chains("balance_producer")))
    ap.add_argument("--exploration", action="store_true",
                    help="探索模式；正式聚合器拒收 exploration 回执")
    ap.add_argument("--token", required=True)
    ap.add_argument("--end-block", required=True, type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--transcript-out")
    ap.add_argument("--divergence-note",
                    help="GMGN 黄灯人工查证说明（gmgn_divergence_note.json）")
    ap.add_argument("--rpc")
    ap.add_argument("--proxy")
    ap.add_argument("--top-n", type=int, default=15)
    args = ap.parse_args(argv)
    try:
        args.execution_mode = resolve_execution_mode(
            args.chain, args.exploration, "balance")
    except ValueError as exc:
        ap.error(str(exc))
    return args


def main(argv=None):
    a = parse_args(argv)
    if a.transcript_out is None:
        a.transcript_out = str(Path(a.out).expanduser().resolve().parent
                               / "verify_recon_transcript.json")
    try:
        assert_distinct_paths(a.out, a.transcript_out)
    except Exception as exc:
        print(f"[verify_recon] output/transcript 路径冲突: {exc}", file=sys.stderr)
        return 1
    target = {"chain": a.chain, "token": a.token.lower(), "as_of_block": a.end_block}
    base_envelope = build_envelope(SCHEMA, target, __file__, a.execution_mode)
    envelope = base_envelope
    transcript = []
    try:
        if a.end_block < 0 or a.top_n <= 0:
            raise ValueError("end-block 必须非负且 top-n 必须为正")
        config_path, balances_path = Path(a.config), Path(a.balances)
        stats_path, gmgn_path = Path(a.replay_stats), Path(a.gmgn)
        # A-3：inputs 记相对路径（相对收据落盘目录＝案根），案目录可整体搬家。
        envelope = build_envelope(SCHEMA, target, __file__, a.execution_mode, inputs={
            "config": config_path, "balances": balances_path,
            "replay_stats": stats_path, "gmgn": gmgn_path},
            input_base=Path(a.out).expanduser().resolve().parent)
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        balances_raw = json.loads(balances_path.read_text(encoding="utf-8"))
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        if not isinstance(balances_raw, dict) or not balances_raw:
            raise ValueError("balances 必须是非空 address->raw 映射")
        balances = {str(k).lower(): int(str(v)) for k, v in balances_raw.items()}
        cfg_token = str(cfg.get("token") or "").lower()
        if cfg_token and cfg_token != target["token"]:
            raise ValueError("config token 与 --token 不一致")
        stats_end = stats.get("max_block") or stats.get("last_block")
        if stats_end is None or int(stats_end) != a.end_block:
            raise ValueError("replay_stats 截止块与 --end-block 不一致")
        decimals = int(cfg["decimals"])
        nominal = int(Decimal(str(cfg["total_supply_human"])) * (Decimal(10) ** decimals))
        mint = int(str(stats.get("mint_total_wei", stats.get("mint_total_raw", 0))))
        burn = int(str(stats.get("burn_total_wei", stats.get("burn_total_raw", 0))))
        balance_sum = sum(balances.values())
        negatives = sorted(k for k, v in balances.items() if v < 0)
        # Replay credits sink recipients while separately recording burn_total.
        # Therefore terminal balances close to mint; burn remains an observation.
        supply_closed = mint == nominal and balance_sum == mint and not negatives

        rpc = a.rpc or str((cfg.get("alchemy") or {}).get("url", "")) + str(
            (cfg.get("alchemy") or {}).get("key", ""))
        if not rpc:
            raise ValueError("缺 RPC：给 --rpc 或 config.alchemy.url/key")
        proxy = a.proxy if a.proxy is not None else cfg.get("proxy")
        pool = attested_rpc_pool(rpc, a.chain, formal=True, proxy=proxy,
                                 rps=8, concurrency=1)
        try:
            pool.attest()
        except RpcChainMismatch as exc:
            raise ReconFailure(str(exc)) from exc
        rows, matched, mismatched, rpc_errors = [], 0, 0, 0
        top = sorted(balances.items(), key=lambda kv: (-kv[1], kv[0]))[:a.top_n]
        for address, replay_raw in top:
            if address in {ZERO, DEAD}:
                continue
            try:
                chain_raw = int(rpc_balance_of(pool, target["token"], address,
                                               a.end_block, transcript))
                ok = chain_raw == replay_raw
                matched += int(ok); mismatched += int(not ok)
                rows.append({"address": address, "replay_raw": str(replay_raw),
                             "chain_raw": str(chain_raw), "diff_raw": str(chain_raw - replay_raw),
                             "status": "OK" if ok else "MISMATCH"})
            except Exception as exc:
                rpc_errors += 1
                rows.append({"address": address, "replay_raw": str(replay_raw),
                             "status": "RPC_ERROR", "error": str(exc)[:300]})

        gmgn_rows, gmgn_diff, gmgn_seen = [], 0, set()
        with gmgn_path.open(newline="", encoding="utf-8") as f:
            for row in list(csv.DictReader(f))[:10]:
                address = str(row.get("address") or "").lower()
                if not address:
                    continue
                if address in gmgn_seen:
                    raise ValueError(f"GMGN 前 10 行地址重复: {address}")
                gmgn_seen.add(address)
                try:
                    gmgn_fraction = Decimal(str(row.get("pct") or "0"))
                except Exception as exc:
                    raise ValueError(f"GMGN pct 非法: {row.get('pct')!r}") from exc
                if not gmgn_fraction.is_finite():
                    raise ValueError(f"GMGN pct 必须为有限数: {row.get('pct')!r}")
                gmgn_pct = gmgn_fraction * Decimal(100)
                replay_pct = (Decimal(balances.get(address, 0)) * Decimal(100)
                              / Decimal(nominal) if nominal else Decimal(0))
                diff_pp = abs(gmgn_pct - replay_pct)
                gmgn_diff += int(diff_pp >= Decimal("0.15"))
                gmgn_rows.append({"address": address, "gmgn_pct": str(gmgn_pct),
                                  "replay_pct": str(replay_pct), "diff_pp": str(diff_pp),
                                  "status": "OK" if diff_pp < Decimal("0.15") else "DIFF"})

        observations = {
            "supply_closure": {"mint_total_raw": str(mint), "burn_total_raw": str(burn),
                               "nominal_supply_raw": str(nominal),
                               "balance_sum_raw": str(balance_sum),
                               "negative_count": len(negatives), "negative_addresses": negatives,
                               "closed": supply_closed},
            "balance_reconciliation": {"requested_top_n": a.top_n,
                                       "selection": "top_n_then_skip_sinks",
                                       "checked": len(rows), "matched": matched,
                                       "mismatched": mismatched, "rpc_errors": rpc_errors,
                                       "rows": rows},
            "gmgn_comparison": {"checked": len(gmgn_rows), "diff_count": gmgn_diff,
                                "tolerance_pp": 0.15, "rows": gmgn_rows},
        }
        envelope["inputs"]["transcript"] = _future_input_ref(
            a.transcript_out, Path(a.out).expanduser().resolve().parent, transcript)
        divergences = [
            {key: row[key] for key in ("address", "gmgn_pct", "replay_pct", "diff_pp")}
            for row in gmgn_rows if row["status"] == "DIFF"
        ]
        if a.divergence_note is not None:
            if not gmgn_diff:
                raise DivergenceNoteError(
                    "GMGN 零差异时禁止预填 --divergence-note；无需人工说明")
            note_path = Path(a.divergence_note).expanduser()
            try:
                _validate_gmgn_divergence_note(
                    Path(a.out).expanduser().resolve().parent, note_path, target,
                    envelope.get("inputs") or {}, divergences)
                envelope["inputs"]["divergence_note"] = _file_input_ref(
                    note_path, Path(a.out).expanduser().resolve().parent)
            except ValueError as exc:
                raise DivergenceNoteError(str(exc)) from exc
        if rpc_errors:
            raise ValueError(f"{rpc_errors} 个 RPC 观测失败")
        elif not supply_closed or mismatched:
            receipt = finalize_envelope(envelope, "FAIL", 2,
                                        observations=observations, error=None,
                                        warnings=[])
        else:
            warnings = [GMGN_DIVERGENCE_WARNING] if gmgn_diff else []
            receipt = finalize_envelope(envelope, "PASS", 0,
                                        observations=observations, error=None,
                                        warnings=warnings)
    except ReconFailure as exc:
        envelope["inputs"]["transcript"] = _future_input_ref(
            a.transcript_out, Path(a.out).expanduser().resolve().parent, transcript)
        receipt = finalize_envelope(envelope, "FAIL", 2, observations={}, error=str(exc),
                                    warnings=[])
    except DivergenceNoteError as exc:
        # 人工说明无效属于调用错误；保留此前黄灯收据，不写 ERROR 回执覆盖证据。
        print(f"[verify_recon] divergence note ERROR exit=1（原黄灯收据未覆盖）: {exc}",
              file=sys.stderr)
        return 1
    except Exception as exc:
        try:
            error_path = publish_error_receipt(a.out, envelope, exc)
            print(f"[verify_recon] ERROR exit=1 → {error_path}")
        except Exception as write_exc:
            print(f"[verify_recon] ERROR receipt 写入失败: {write_exc}", file=sys.stderr)
        return 1
    try:
        publish_txn(a.transcript_out, transcript, a.out, receipt)
    except Exception as exc:
        print(f"[verify_recon] receipt 写入失败: {exc}", file=sys.stderr)
        return 1
    print(f"[verify_recon] {receipt['verdict']} exit={receipt['exit_code']} → {a.out}")
    if GMGN_DIVERGENCE_WARNING in receipt.get("warnings", []):
        if "divergence_note" in (receipt.get("inputs") or {}):
            print("[verify_recon] 黄灯 gmgn_divergence：查证说明已绑定；发布侧将独立重验")
        else:
            print("[verify_recon] 黄灯 gmgn_divergence：收据 PASS，但发布前必须补 "
                  "gmgn_divergence_note.json")
            print("[verify_recon] 查证后按原命令追加 "
                  "--divergence-note gmgn_divergence_note.json 重跑绑定")
    return receipt["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
