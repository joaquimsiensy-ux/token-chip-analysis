#!/usr/bin/env python3
"""供给真值闸（supply truth gate）——重放终态对链上 totalSupply 的硬校验。

背景（GNT 实测，2026-07-28）：老合约 migrate() 直接改账本、不发任何 Transfer/Burn
事件，全量重放余额虚高 10 倍，而 mint/burn 闭合、负余额、accounting_gate 全部检测项
均 PASS（模型错但自洽）。唯一暴露手段：重放净供给 mint_total − burn_total 对比链上
实查 totalSupply()。本闸在正式分析重放收尾必跑；主规则成本一次 RPC 调用，
形态②候选另加一次三值批量调用。

判定（fail-closed）:
  |replay_net − onchain| <= onchain × tolerance_bps/10000  → PASS
  超容差 → FAIL：该币余额一律禁用重放结果，改 Multicall3/RPC 实时直查；
  地址全集与转账历史仍可用重放（静默改账不影响历史事件本身）；
  重放余额仅可作"≥阈值超集"筛选（migrate 只减不增，数学严格）。

用法:
  EVM:    python3 supply_truth_gate.py --chain bsc --token 0x... --as-of-block N --replay-stats replay_stats.json
  Solana: python3 supply_truth_gate.py --chain solana --mint <mint> \
           --observation-bundle <bundle.json> --as-of-block <slot> \
           --min-context-slot N --replay-stats stats.json
  绕过 stats 文件直接传数: --replay-net-raw <最小单位整数>
  --rpc URL          不给时用链默认免 key 端点（DEFAULT_RPC，与 accounting_gate 同表）
  --proxy URL        只作用于 RPC（Alchemy 国内走 clash 时传 http://127.0.0.1:7897）
  --tolerance-bps N  容差，默认 10（0.1%）
  --as-of-block N    v3 receipt target 的冻结块/slot；正式发布必填
  --out PATH         结果 JSON 落盘（默认 supply_truth.json，写工作目录）

replay-stats 字段识别（依次尝试，值可为 int 或十进制字符串）:
  mint_total_wei/burn_total_wei → mint_total_raw/burn_total_raw → mint_total/burn_total

退出码: 0 = PASS
        2 = FAIL（终态供给或 sink 逐地址归因不闭合——硬停，处置见上）
        1 = 检测自身失败（网络/字段缺失）——修通道重跑，禁当 PASS
（来源：GNT replay-silent-burn-trap 2026-07-28；v6.0.0 唯一批准代码例外）"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from receipt_kernel import (build_envelope, finalize_envelope, publish_error_receipt,
                            publish_overwrite)
from chain_registry import formal_reconciliation_chains
from net import attested_rpc_pool
from solana_observation import (assert_declared_slot,
                                validate_observation_bundle)
from supply_semantics import DEAD, ZERO

SEL_TOTSUP = "0x18160ddd"  # totalSupply()
SEL_BALANCE = "0x70a08231"  # balanceOf(address)
SINK_STATS_FIELDS = ("zero_event_inflow_wei", "dead_event_inflow_wei",
                     "dead_event_outflow_wei", "dead_sink_net_wei")

DEFAULT_RPC = {
    "bsc": "https://bsc-dataseed.bnbchain.org",
    "eth": "https://ethereum-rpc.publicnode.com",
    "base": "https://mainnet.base.org",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "polygon": "https://polygon-rpc.com",
    "solana": "https://api.mainnet-beta.solana.com",
}

FIELD_PAIRS = [("mint_total_wei", "burn_total_wei"),
               ("mint_total_raw", "burn_total_raw"),
               ("mint_total", "burn_total")]
FORMAL_TOLERANCE_BPS_MAX = 10
TOLERANCE_WAIVER_SCHEMA = "tolerance-waiver/v1"


class TolerancePolicyError(ValueError):
    """正式容差政策或 waiver 不合法（调用错误，exit 2）。"""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _waiver_file_ref(waiver_path: Path, ref, label: str) -> Path:
    if not isinstance(ref, dict) or not {"path", "size", "sha256"} <= set(ref):
        raise TolerancePolicyError(f"waiver {label} 必须绑定 path/size/sha256")
    raw = Path(str(ref.get("path") or ""))
    if raw.is_absolute() or not raw.parts or ".." in raw.parts:
        raise TolerancePolicyError(f"waiver {label} path 必须是收据同目录内的安全相对路径")
    lexical = waiver_path.parent
    for part in raw.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise TolerancePolicyError(f"waiver {label} 不得引用符号链接")
    try:
        path = lexical.resolve(strict=True)
        path.relative_to(waiver_path.parent)
    except (OSError, ValueError) as exc:
        raise TolerancePolicyError(f"waiver {label} 文件不存在或越界") from exc
    if not path.is_file():
        raise TolerancePolicyError(f"waiver {label} 不是普通文件")
    if (isinstance(ref.get("size"), bool) or not isinstance(ref.get("size"), int)
            or ref.get("size") != path.stat().st_size):
        raise TolerancePolicyError(f"waiver {label} size 不匹配")
    if ref.get("sha256") != _sha256_file(path):
        raise TolerancePolicyError(f"waiver {label} sha256 不匹配")
    return path


def load_tolerance_waiver(path, *, target: dict, tolerance_bps: int,
                          replay_stats_path) -> tuple[Path, dict]:
    """加载并验证仅放大 supply truth 容差的输入侧人工裁决收据。"""
    shown = Path(path).expanduser()
    try:
        waiver_path = shown.resolve(strict=True)
    except OSError as exc:
        raise TolerancePolicyError("tolerance waiver 文件不存在") from exc
    if shown.is_symlink() or not waiver_path.is_file():
        raise TolerancePolicyError("tolerance waiver 必须是普通文件且不得为符号链接")
    try:
        waiver = json.loads(waiver_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TolerancePolicyError(f"tolerance waiver JSON 损坏: {exc}") from exc
    required = {
        "schema", "approved_tolerance_bps", "approved_by", "user_decided_at_utc",
        "target", "replay_stats", "evidence_refs", "reason",
    }
    if not isinstance(waiver, dict) or any(
            key not in waiver or waiver.get(key) in (None, "", []) for key in required):
        raise TolerancePolicyError("tolerance waiver schema 或必填字段不完整")
    if waiver.get("schema") != TOLERANCE_WAIVER_SCHEMA:
        raise TolerancePolicyError("tolerance waiver schema 必须是 tolerance-waiver/v1")
    approved = waiver.get("approved_tolerance_bps")
    if isinstance(approved, bool) or not isinstance(approved, int) or approved < 0:
        raise TolerancePolicyError("waiver 批准容差必须是非负整数")
    if tolerance_bps < 0 or tolerance_bps > approved:
        raise TolerancePolicyError(
            f"实际容差 {tolerance_bps}bps 超出 waiver 批准值 {approved}bps")
    if not isinstance(waiver.get("approved_by"), str) or not waiver["approved_by"].strip():
        raise TolerancePolicyError("waiver 裁决主体 approved_by 必填")
    decided_at = waiver.get("user_decided_at_utc")
    try:
        if not isinstance(decided_at, str) or not decided_at.endswith("Z"):
            raise ValueError
        datetime.fromisoformat(decided_at[:-1] + "+00:00")
    except ValueError as exc:
        raise TolerancePolicyError("waiver user_decided_at_utc 必须是有效 UTC 时间") from exc
    if waiver.get("target") != target:
        raise TolerancePolicyError("waiver target 的 chain/token/as_of_block 与本次运行不全等")
    if not isinstance(waiver.get("reason"), str) or not waiver["reason"].strip():
        raise TolerancePolicyError("waiver 理由文本必填")
    replay_ref_path = _waiver_file_ref(waiver_path, waiver.get("replay_stats"), "replay_stats")
    try:
        current_replay = Path(replay_stats_path).expanduser().resolve(strict=True)
    except (OSError, TypeError) as exc:
        raise TolerancePolicyError("waiver 运行必须提供存在的 --replay-stats") from exc
    if replay_ref_path != current_replay:
        raise TolerancePolicyError("waiver replay_stats 未绑定本次实际输入")
    refs = waiver.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise TolerancePolicyError("waiver evidence_refs 必须是非空数组")
    for index, ref in enumerate(refs):
        _waiver_file_ref(waiver_path, ref, f"evidence_refs[{index}]")
    return waiver_path, waiver


def parse_replay_stats(stats: dict):
    """从 replay_stats 字典取 (mint_total, burn_total)，找不到抛 KeyError。"""
    for mk, bk in FIELD_PAIRS:
        if mk in stats:
            return int(str(stats[mk])), int(str(stats.get(bk, 0)))
    raise KeyError(f"replay_stats 缺 mint/burn 字段（认 {FIELD_PAIRS}）")


def decide(replay_net: int, onchain: int, tolerance_bps: int = 10):
    """纯判定：返回 (verdict, diff, diff_bps)。verdict ∈ {PASS, FAIL}。"""
    diff = replay_net - onchain
    if onchain == 0:
        # 链上供给为 0（全部销毁/迁空）：重放净供给也必须为 0 才算一致
        return ("PASS" if replay_net == 0 else "FAIL"), diff, None
    diff_bps = abs(diff) * 10000 / onchain
    return ("PASS" if diff_bps <= tolerance_bps else "FAIL"), diff, diff_bps


def decide_sink_fallback(mint_total, burn_total, onchain,
                         zero_event_inflow, dead_sink_net,
                         onchain_zero_balance, onchain_dead_balance):
    """主判定 FAIL 后的形态②判定。

    全部 wei 级零容差，任何 None 分量均不适用并返回 FAIL 语义。全部成立才 PASS：
    C1 mint_total == onchain；C2a zero_event_inflow == onchain_zero_balance；
    C2b dead_sink_net == onchain_dead_balance；
    C3 zero_event_inflow + dead_sink_net == burn_total。
    返回 (verdict, burn_form)：("PASS", "dead_sink") 或 ("FAIL", None)。
    """
    values = (mint_total, burn_total, onchain, zero_event_inflow,
              dead_sink_net, onchain_zero_balance, onchain_dead_balance)
    if any(value is None for value in values):
        return "FAIL", None
    try:
        mint_total, burn_total, onchain, zero_event_inflow, dead_sink_net, \
            onchain_zero_balance, onchain_dead_balance = map(int, values)
    except (TypeError, ValueError):
        return "FAIL", None
    closed = (
        mint_total == onchain
        and zero_event_inflow == onchain_zero_balance
        and dead_sink_net == onchain_dead_balance
        and zero_event_inflow + dead_sink_net == burn_total
    )
    return ("PASS", "dead_sink") if closed else ("FAIL", None)


def _parse_eth_call_value(response, label):
    if not isinstance(response, dict) or not response.get("ok"):
        error = response.get("error") if isinstance(response, dict) else response
        raise ValueError(f"eth_call {label} RPC 失败: {error}")
    raw = response.get("result")
    if not isinstance(raw, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", raw):
        raise ValueError(f"eth_call {label} 返回非法值: {raw!r}")
    return int(raw, 16)


def _balance_of_data(address):
    return SEL_BALANCE + "0" * 24 + address.removeprefix("0x").lower()


def fetch_sink_reconciliation(pool, token, as_of_block):
    """在同一冻结块批量取得终态标量与两个 sink 的逐地址余额。"""
    tag = hex(int(as_of_block))
    calls = [
        ("eth_call", [{"to": token, "data": SEL_TOTSUP}, tag]),
        ("eth_call", [{"to": token, "data": _balance_of_data(ZERO)}, tag]),
        ("eth_call", [{"to": token, "data": _balance_of_data(DEAD)}, tag]),
    ]
    responses = pool.call_many(calls)
    if not isinstance(responses, list) or len(responses) != len(calls):
        raise ValueError("sink reconciliation RPC 返回数量不完整")
    return tuple(_parse_eth_call_value(response, label) for response, label in zip(
        responses, ("totalSupply", "balanceOf(ZERO)", "balanceOf(DEAD)")))


def fetch_onchain_supply(chain, token=None, mint=None, rpc=None, proxy=None,
                         as_of_block=None, pool=None):
    """返回 (最小单位总供给, Solana observed context slot|None)。"""
    url = rpc or DEFAULT_RPC[chain]
    if chain == "solana":
        raise ValueError(
            "Solana formal supply is consumed from --observation-bundle; direct RPC is forbidden")
    tag = hex(int(as_of_block)) if as_of_block is not None else "latest"
    pool = pool or attested_rpc_pool(url, chain, formal=True, proxy=proxy,
                                    rps=2, concurrency=1)
    response = pool.call("eth_call", [{"to": token, "data": SEL_TOTSUP}, tag])
    return _parse_eth_call_value(response, "totalSupply"), None


def main(argv=None):
    ap = argparse.ArgumentParser(description="供给真值闸：重放净供给 vs 链上 totalSupply")
    supply_chains = formal_reconciliation_chains("supply")
    supply_choices = sorted((supply_chains - {"sol"}) | ({"solana"} if "sol" in supply_chains else set()))
    ap.add_argument("--chain", required=True, choices=supply_choices)
    ap.add_argument("--token", help="EVM 合约地址")
    ap.add_argument("--mint", help="Solana mint")
    ap.add_argument("--replay-stats", help="replay_stats.json 路径")
    ap.add_argument("--replay-net-raw", type=int, help="直接给重放净供给（最小单位）")
    ap.add_argument("--exploration", action="store_true",
                    help="探索模式；仅此模式允许 --replay-net-raw，正式聚合器拒收")
    ap.add_argument("--rpc")
    ap.add_argument("--proxy")
    ap.add_argument("--observation-bundle",
                    help="Solana formal solana-observation-bundle/v1 from scan_token_accounts")
    ap.add_argument("--min-context-slot", type=int, default=0,
                    help="Solana bundle snapshot lower-bound assertion")
    ap.add_argument("--tolerance-bps", type=int, default=10)
    ap.add_argument("--tolerance-waiver",
                    help="formal 模式超过 10bps 时必需的 tolerance-waiver/v1 输入收据")
    ap.add_argument("--as-of-block", type=int, default=None,
                    help="与 accounting target 对齐的冻结块/slot；正式发布必须提供")
    ap.add_argument("--out", default="supply_truth.json")
    a = ap.parse_args(argv)

    mode = "exploration" if a.exploration else "formal"
    bundle = None
    bundle_path = None
    observed_context_slot = None
    envelope = None
    replay_stats = None
    evm_pool = None
    if a.min_context_slot < 0:
        ap.error("--min-context-slot must be non-negative")
    if a.chain == "solana" and not a.mint:
        ap.error("solana 链必须给 --mint")
    if mode == "formal" and a.tolerance_bps < 0:
        print("正式模式 --tolerance-bps 必须满足 0 <= 值", file=sys.stderr)
        return 2
    if (mode == "formal" and a.tolerance_bps > FORMAL_TOLERANCE_BPS_MAX
            and not a.tolerance_waiver):
        print("正式模式 --tolerance-bps 上限为 10；超出必须提供 --tolerance-waiver",
              file=sys.stderr)
        return 2
    try:
        observed_snapshot_slot = a.as_of_block
        if a.chain == "solana":
            if not a.observation_bundle:
                raise ValueError("solana 链必须给 --observation-bundle")
            bundle_path = Path(a.observation_bundle).resolve(strict=True)
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            validate_observation_bundle(
                bundle, bundle_path=bundle_path, expected_mint=a.mint)
            observed_snapshot_slot = bundle["snapshot"]["slot"]
        target = {"chain": a.chain, "token": (a.token or a.mint or "").lower(),
                  "as_of_block": observed_snapshot_slot}
        envelope_inputs = {}
        if a.replay_stats:
            envelope_inputs["replay_stats"] = Path(a.replay_stats)
        if bundle_path is not None:
            envelope_inputs["observation_bundle"] = bundle_path
        if mode == "formal" and a.tolerance_waiver:
            waiver_path, _ = load_tolerance_waiver(
                a.tolerance_waiver, target=target, tolerance_bps=a.tolerance_bps,
                replay_stats_path=a.replay_stats)
            envelope_inputs["tolerance_waiver"] = waiver_path
        envelope = build_envelope(
            "supply-truth-receipt/v3", target, __file__, mode,
            inputs=envelope_inputs or None)
        if a.chain == "solana":
            assert_declared_slot(a.as_of_block, observed_snapshot_slot, "--as-of-block")
            if observed_snapshot_slot < a.min_context_slot:
                raise ValueError(
                    f"bundle snapshot slot {observed_snapshot_slot} < "
                    f"--min-context-slot {a.min_context_slot}")
    except TolerancePolicyError as exc:
        print(f"正式容差政策拒绝（exit 2）: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"检测自身失败（exit 1，修通道重跑）: {exc}", file=sys.stderr)
        if envelope is not None:
            try:
                error_path = publish_error_receipt(a.out, envelope, exc)
                print(f"[supply_truth] ERROR → {error_path}", file=sys.stderr)
            except Exception as write_exc:
                print(f"[supply_truth] ERROR receipt 写入失败: {write_exc}", file=sys.stderr)
        return 1

    try:
        if a.replay_net_raw is not None and not a.exploration:
            raise ValueError("正式模式拒绝 --replay-net-raw；仅可显式加 --exploration 作探索运行")
        if a.chain != "solana" and a.as_of_block is None:
            raise ValueError("EVM 链必须给 --as-of-block，禁止 latest 冒充冻结时点")
        if a.replay_net_raw is not None:
            replay_net, mint_t, burn_t = a.replay_net_raw, None, None
        elif a.replay_stats:
            with open(a.replay_stats) as f:
                replay_stats = json.load(f)
            mint_t, burn_t = parse_replay_stats(replay_stats)
            replay_net = mint_t - burn_t
        else:
            raise ValueError("必须给 --replay-stats 或 --replay-net-raw")
        if a.chain == "solana" and not a.mint:
            raise ValueError("solana 链必须给 --mint")
        if a.chain != "solana" and not a.token:
            raise ValueError("EVM 链必须给 --token")
        if a.chain == "solana":
            onchain = int(bundle["supply"]["amount"])
            observed_context_slot = int(bundle["supply"]["slot"])
        else:
            evm_pool = attested_rpc_pool(
                a.rpc or DEFAULT_RPC[a.chain], a.chain, formal=True, proxy=a.proxy,
                rps=2, concurrency=1)
            observed = fetch_onchain_supply(a.chain, a.token, a.mint, a.rpc, a.proxy,
                                            a.as_of_block, pool=evm_pool)
            if isinstance(observed, tuple):
                onchain, observed_context_slot = observed
            else:  # 兼容 EVM 注入 mock。
                onchain, observed_context_slot = int(observed), None
    except Exception as e:  # 网络/字段/文件——检测自身失败，禁当 PASS
        print(f"检测自身失败（exit 1，修通道重跑）: {e}", file=sys.stderr)
        try:
            error_path = publish_error_receipt(a.out, envelope, e)
            print(f"[supply_truth] ERROR → {error_path}", file=sys.stderr)
        except Exception as write_exc:
            print(f"[supply_truth] ERROR receipt 写入失败: {write_exc}", file=sys.stderr)
        return 1

    primary_verdict, diff, diff_bps = decide(replay_net, onchain, a.tolerance_bps)
    verdict = primary_verdict
    decision_rule = "primary_form1"
    burn_form = None
    sink_reconciliation = None
    fallback_ready = (
        primary_verdict == "FAIL"
        and a.chain != "solana"
        and isinstance(replay_stats, dict)
        and all(field in replay_stats for field in SINK_STATS_FIELDS)
    )
    if fallback_ready:
        try:
            batched_supply, onchain_zero, onchain_dead = fetch_sink_reconciliation(
                evm_pool, a.token, a.as_of_block)
            if batched_supply != onchain:
                raise ValueError(
                    "同一冻结块的 totalSupply 单查与 sink 批量观测不一致")
            split_values = {
                field: int(str(replay_stats[field])) for field in SINK_STATS_FIELDS
            }
            zero_event_inflow = split_values["zero_event_inflow_wei"]
            dead_sink_net = split_values["dead_sink_net_wei"]
            decision_rule = "sink_fallback_form2"
            verdict, burn_form = decide_sink_fallback(
                mint_t, burn_t, batched_supply, zero_event_inflow, dead_sink_net,
                onchain_zero, onchain_dead)
            sink_reconciliation = {
                "zero": {"replay_raw": str(zero_event_inflow),
                         "onchain_raw": str(onchain_zero)},
                "dead": {"replay_raw": str(dead_sink_net),
                         "onchain_raw": str(onchain_dead)},
            }
        except Exception as exc:
            print(f"检测自身失败（exit 1，修通道重跑）: {exc}", file=sys.stderr)
            try:
                error_path = publish_error_receipt(a.out, envelope, exc)
                print(f"[supply_truth] ERROR → {error_path}", file=sys.stderr)
            except Exception as write_exc:
                print(f"[supply_truth] ERROR receipt 写入失败: {write_exc}", file=sys.stderr)
            return 1

    result = finalize_envelope(envelope, verdict, 0 if verdict == "PASS" else 2,
        gate="supply_truth", chain=a.chain,
        token=a.token or a.mint,
        replay_net=str(replay_net), mint_total=str(mint_t) if mint_t is not None else None,
        burn_total=str(burn_t) if burn_t is not None else None,
        onchain_total_supply=str(onchain), diff=str(diff),
        diff_bps=round(diff_bps, 4) if diff_bps is not None else None,
        tolerance_bps=a.tolerance_bps,
        decision_rule=decision_rule,
        burn_form=burn_form,
        primary_verdict=primary_verdict,
        sink_reconciliation=sink_reconciliation,
        observed_context_slot=observed_context_slot if a.chain == "solana" else None,
        observation_bundle=(
            {"path": str(bundle_path), "size": bundle_path.stat().st_size,
             "sha256": __import__("hashlib").sha256(bundle_path.read_bytes()).hexdigest()}
            if bundle_path is not None else None),
        supply_observation_semantics=(
            "bundle getTokenSupply cross-check observed at observed_context_slot; "
            "canonical freeze remains target.as_of_block from GPA context"
            if a.chain == "solana" else "historical eth_call at target.as_of_block"),
        on_fail=("余额禁用重放结果改链上实时直查；地址全集/转账历史仍可用重放；"
                 "重放余额仅可作≥阈值超集筛选" if verdict == "FAIL" else None))
    try:
        publish_overwrite(a.out, result)
    except Exception as exc:
        print(f"[supply_truth] receipt 写入失败: {exc}", file=sys.stderr)
        return 1
    ratio = f"{diff_bps:.1f}bps" if diff_bps is not None else "n/a"
    print(f"[supply_truth] {verdict}  重放净供给={replay_net}  链上={onchain}  差={diff}（{ratio}，容差 {a.tolerance_bps}bps）→ {a.out}")
    if verdict == "FAIL":
        print("[supply_truth] FAIL：终态供给或 sink 逐地址归因不闭合。余额改走链上实时直查，重放余额仅作超集筛选。", file=sys.stderr)
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
