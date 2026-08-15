#!/usr/bin/env python3
"""A2 时间抽查执行器（EVM）——按 anchor_plan.json 逐锚点对独立第二源核对，产 time_spotcheck.json。

痛点定位：时间抽查此前无固化脚本，每案现场手写对照实现（违反"禁止现场重写已有能力"
总纪律）；且第二源选型被 GMX 案 §13 的全史区间示范命令带偏——APU(ETH) 案在锚点直查
15/15 PASS 之外又照模板 SQD 全史重拉 94 万行，169 行/s 跑了 103 分钟仍覆盖不全，
纯冗余（2026-08-01 复盘定）。本脚本把"锚点级第二源直查"固化为默认路径：
  - balance 型锚点（矩阵点/最大单日净变动/门槛边缘地址，有 expected_balance_raw）：
    archive eth_call balanceOf(addr) at 历史块——状态直查绕开一切事件索引商，
    对"余额结果"的验证比换一家事件索引商更直接；但不能替代事件集合完整性验证
    （等额进出抵消、零余额中转层、元数据错误它天然验不出——需要事件明细审计时
    走 data-pipeline-evm-recon §13 的全史重拉例外条款）。
  - tx 型锚点（全史最大单笔/数据源交界块，有 tx 无余额期望）：eth_getTransactionReceipt
    独立取收据，核对该 Transfer log 的 (token, from, to, value, block) 五元组。
    ⚠ 两型必须都跑——只跑 balance 型等于四类强制覆盖点漏验两类（codex 复核抓出）。

第二源要求：--rpc 必须是**独立于主采集通道**的 archive 节点（主采集 HyperSync 时，
Alchemy archive / 公共 archive 节点均可；APU 案 Alchemy archive 15/15 精确一致实证）。
Solana 案不适用本脚本（时间抽查走 solana/anchor_sampler.py 通道）。

用法:
  python3 time_spotcheck.py --plan anchor_plan.json --input <transfers.csv|parquet|v2目录> \
      --rpc <archive_rpc_url> \
      --chain bsc --token 0x... --out time_spotcheck.json --final-block N [--rps 8]
  dry-run 可省 --chain/--rpc，但仍须真实 --input 与 --final-block；不生成正式 receipt。

  --final-block  数据截止块，也是 v2 receipt target.as_of_block；正式运行必填。
  --dry-run      只解析计划分型统计（不打网），供预检与契约测试。

退出码（对齐 skill gate 惯例）: 0=全点一致 PASS / 2=存在 mismatch FAIL /
  1=RPC 错误或脚本自身失败（检测自身失败，禁当 PASS）。
产物 time_spotcheck.json 带 verdict+exit_code，供 handoff_manifest AUTO_GATES 重读防手报。
（来源：APU SQD 全史重拉冗余复盘 + codex 交叉复核，2026-08-01）"""
import argparse
from collections import Counter
import datetime
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anchor_selection import (EXPECTED_PLAN_PRODUCER, REPLAY_PARAMETER_FIELDS,
                              generate_anchor_selection, input_identity,
                              sha256_file, validate_anchor_coverage_parameters)
from chain_registry import (executable_evm_chains, resolve_execution_mode)
from receipt_validate import validate_receipt
from receipt_kernel import (build_envelope, finalize_envelope, publish_error_receipt,
                            publish_overwrite, publish_supersede)

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
BALANCEOF_SELECTOR = "0x70a08231"
SCHEMA = "time-spotcheck/v2"
SCHEMA_FAMILY = "time-spotcheck/"
PLAN_SCHEMA = "anchor-plan/v2"
PLAN_RECEIPT_SCHEMA = "anchor-plan-receipt/v2"


def _default_plan_receipt(plan_path):
    path = Path(plan_path)
    suffix = path.suffix or ".json"
    stem = path.name[:-len(suffix)] if path.name.endswith(suffix) else path.name
    return path.with_name(f"{stem}.receipt{suffix}")


def load_validated_plan(plan_path, receipt_path):
    plan_file = Path(plan_path)
    receipt_file = Path(receipt_path)
    if plan_file.is_symlink() or receipt_file.is_symlink():
        raise ValueError("plan/receipt symlink rejected")
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    errors = validate_receipt(receipt)
    if errors:
        raise ValueError("plan receipt invalid: " + "; ".join(errors))
    if plan.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"plan schema must be {PLAN_SCHEMA}")
    if receipt.get("schema") != PLAN_RECEIPT_SCHEMA or receipt.get("verdict") != "PASS":
        raise ValueError("plan receipt schema/verdict invalid")
    producer = receipt.get("producer")
    producer_path = producer.get("path") if isinstance(producer, dict) else None
    normalized_producer = (Path(os.path.normpath(producer_path)).as_posix()
                           if isinstance(producer_path, str) and producer_path else None)
    if normalized_producer != EXPECTED_PLAN_PRODUCER:
        raise ValueError(
            f"plan receipt must name registered anchor producer {EXPECTED_PLAN_PRODUCER}")
    if plan.get("target") != receipt.get("target"):
        raise ValueError("plan target differs from receipt target")
    target = plan["target"]
    if (plan.get("chain") != target.get("chain")
            or plan.get("token") != target.get("token")
            or plan.get("final_block") != target.get("as_of_block")):
        raise ValueError("plan compatibility target fields diverge")
    if plan.get("producer") != receipt.get("producer"):
        raise ValueError("plan producer differs from receipt producer")
    if plan.get("input") != receipt.get("input_identity"):
        raise ValueError("plan input identity differs from receipt")
    manifest = (receipt.get("inputs") or {}).get("input_manifest")
    if not isinstance(manifest, dict) or plan.get("input_manifest") != manifest:
        raise ValueError("plan input manifest differs from receipt binding")
    output = receipt.get("output")
    if not isinstance(output, dict):
        raise ValueError("plan receipt output missing")
    if Path(str(output.get("path", ""))).resolve() != plan_file.resolve():
        raise ValueError("plan receipt output path mismatch")
    if (output.get("size") != plan_file.stat().st_size
            or output.get("sha256") != sha256_file(plan_file)):
        raise ValueError("plan receipt output size/hash mismatch")
    if receipt.get("plan_schema") != PLAN_SCHEMA:
        raise ValueError("plan receipt plan_schema mismatch")
    if receipt.get("generated_at") != plan.get("generated_at"):
        raise ValueError("plan generated_at differs from receipt")
    point_count = sum(len(plan.get(key) or []) for key in ("matrix_points", "forced_points"))
    if receipt.get("probe_count") != point_count:
        raise ValueError("plan receipt probe_count mismatch")
    return plan


def _strict_int(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"replay parameter {field} must be an integer")
    return value


def _strict_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value):
        raise ValueError(f"replay parameter {field} must be a finite number")
    return value


def _point_multiset(value, field):
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{field} must be a list of point objects")
    return Counter(json.dumps(item, ensure_ascii=False, sort_keys=True,
                              separators=(",", ":")) for item in value)


def validate_semantic_replay(plan, raw_input, *, mem_limit="6GB", threads=4):
    """Recompute selection from the real input and compare all deterministic results."""
    missing = [field for field in REPLAY_PARAMETER_FIELDS if field not in plan]
    if missing:
        raise ValueError("missing replay parameters: " + ", ".join(missing))
    if not isinstance(plan["chain"], str) or not plan["chain"]:
        raise ValueError("replay parameter chain must be a non-empty string")
    if not isinstance(plan["token"], str) or not plan["token"]:
        raise ValueError("replay parameter token must be a non-empty string")
    for field in ("final_block", "decimals", "per_cell", "edge_max", "seed"):
        _strict_int(plan[field], field)
    validate_anchor_coverage_parameters(plan["per_cell"], plan["edge_max"])
    for field in ("total_supply", "threshold_pct", "min_pct"):
        _strict_number(plan[field], field)
    bounds = plan["boundary_blocks"]
    if not isinstance(bounds, list):
        raise ValueError("replay parameter boundary_blocks must be a list")
    for index, value in enumerate(bounds):
        _strict_int(value, f"boundary_blocks[{index}]")

    actual_identity, _ = input_identity(raw_input)
    declared_identity = plan.get("input")
    if not isinstance(declared_identity, dict) or not declared_identity.get("sha256"):
        raise ValueError("plan input.sha256 missing")
    if actual_identity["sha256"] != declared_identity["sha256"]:
        raise ValueError(
            f"input sha256 mismatch: actual {actual_identity['sha256']} "
            f"!= plan {declared_identity['sha256']}")

    replayed = generate_anchor_selection(
        input_path=raw_input, chain=plan["chain"], token=plan["token"],
        total_supply=plan["total_supply"], decimals=plan["decimals"],
        threshold_pct=plan["threshold_pct"], min_pct=plan["min_pct"],
        boundary_blocks=bounds, per_cell=plan["per_cell"], edge_max=plan["edge_max"],
        seed=plan["seed"], mem_limit=mem_limit, threads=threads)
    for field in ("date_range", "time_cuts", "cell_population", "boundary_blocks"):
        if plan.get(field) != replayed[field]:
            raise ValueError(f"{field} differs from deterministic replay")
    for field in ("matrix_points", "forced_points"):
        declared = _point_multiset(plan.get(field), field)
        expected = _point_multiset(replayed[field], field)
        if declared != expected:
            missing_count = sum((expected - declared).values())
            extra_count = sum((declared - expected).values())
            raise ValueError(
                f"{field} differs from deterministic replay "
                f"(missing={missing_count}, extra={extra_count})")
    return actual_identity


def classify(plan):
    """anchor_plan 锚点分型：balance 型（可查余额）/ tx 型（查收据核五元组）。
    分型判据＝字段形态而非 kind 文案（kind 是给人看的，字段才是契约）。"""
    bal, txp, odd = [], [], []
    for src in ("matrix_points", "forced_points"):
        for p in plan.get(src, []) or []:
            if p.get("expected_balance_raw") is not None and p.get("addr"):
                bal.append(p)
            elif p.get("tx") and p.get("expected_value_raw") is not None:
                txp.append(p)
            else:
                odd.append(p)
    return bal, txp, odd


def hexblock(n):
    return hex(int(n))


def addr_word(addr):
    return addr.lower().replace("0x", "").rjust(64, "0")


def main():
    ap = argparse.ArgumentParser(description="A2 时间抽查执行器（EVM 锚点级第二源直查）")
    ap.add_argument("--plan", required=True, help="anchor_plan.json（anchor_plan.py 产物）")
    ap.add_argument("--input", required=True,
                    help="生成 plan 所用的真实 merged 转账数据；consumer 会全量重放")
    ap.add_argument("--plan-receipt",
                    help="anchor plan receipt；默认取 plan 同目录的 anchor_plan.receipt.json")
    ap.add_argument("--chain", choices=sorted(executable_evm_chains("time_producer")),
                    help="正式回执目标链；非 dry-run 必填")
    ap.add_argument("--exploration", action="store_true",
                    help="探索模式；正式聚合器拒收 exploration 回执")
    ap.add_argument("--rpc", help="独立第二源 archive RPC（--dry-run 时可省）")
    ap.add_argument("--token", required=True, help="代币合约地址")
    ap.add_argument("--out", required=True, help="输出 time_spotcheck.json")
    ap.add_argument("--final-block", type=int, default=None,
                    help="数据截止块（边缘地址点无 day_end_block 时用）")
    ap.add_argument("--rps", type=int, default=8)
    ap.add_argument("--mem-limit", default="6GB", help="DuckDB 重放内存上限")
    ap.add_argument("--threads", type=int, default=4, help="DuckDB 重放线程数")
    ap.add_argument("--dry-run", action="store_true", help="只解析分型统计，不打网")
    a = ap.parse_args()
    execution_mode = None
    if a.chain:
        try:
            execution_mode = resolve_execution_mode(a.chain, a.exploration, "time")
        except ValueError as exc:
            ap.error(str(exc))

    plan_receipt = a.plan_receipt or _default_plan_receipt(a.plan)
    try:
        plan = load_validated_plan(a.plan, plan_receipt)
    except Exception as e:
        print(f"[fatal] anchor_plan/receipt 校验失败: {e}", file=sys.stderr)
        return 2
    try:
        validate_semantic_replay(
            plan, a.input, mem_limit=a.mem_limit, threads=a.threads)
    except Exception as e:
        print(f"[fatal] anchor_plan semantic replay failed: {e}", file=sys.stderr)
        return 2
    bal_pts, tx_pts, odd_pts = classify(plan)
    total = len(bal_pts) + len(tx_pts)
    # GMX 案实锤教训：0 个点循环零次 bad==0 直接打 PASS——必须硬失败
    assert total > 0, "[fatal] 抽查点数为 0——anchor_plan 为空或解析失败，禁当 PASS"
    if odd_pts:
        sys.exit(f"[fatal] {len(odd_pts)} 个锚点两型都不匹配（缺 expected_balance_raw 且缺 tx）——"
                 f"anchor_plan 格式漂移，先修计划再跑: {json.dumps(odd_pts[0], ensure_ascii=False)[:120]}")
    need_final = [p for p in bal_pts if p.get("day_end_block") is None]
    if need_final and a.final_block is None:
        sys.exit(f"[fatal] {len(need_final)} 个 balance 锚点无 day_end_block（门槛边缘地址型），"
                 "必须传 --final-block <数据截止块>——静默跳点=覆盖缩水，fail-closed")
    plan_final = plan.get("final_block")
    if (isinstance(plan_final, bool) or not isinstance(plan_final, int)
            or a.final_block is None or plan_final != a.final_block):
        print("[fatal] anchor_plan final_block 必须与 CLI --final-block 精确一致", file=sys.stderr)
        return 2
    query_blocks = [p.get("day_end_block") for p in bal_pts
                    if p.get("day_end_block") is not None]
    query_blocks += [p.get("block") for p in tx_pts if p.get("block") is not None]
    if any(isinstance(block, bool) or not isinstance(block, int)
           or block < 0 or block > a.final_block for block in query_blocks):
        print("[fatal] anchor_plan 查询块非法或越过 final_block", file=sys.stderr)
        return 2

    if a.dry_run:
        plan_chain = str(plan.get("chain") or "").lower()
        plan_token = str(plan.get("token") or "").lower()
        if not plan_chain or not plan_token or plan_token != a.token.lower() \
                or (a.chain and plan_chain != a.chain):
            print("[fatal] anchor_plan chain/token 与 CLI target 不一致或缺失", file=sys.stderr)
            return 2
        print(json.dumps({"dry_run": True, "balance_points": len(bal_pts),
                          "tx_points": len(tx_pts), "total": total,
                          "need_final_block": len(need_final)}, ensure_ascii=False))
        return 0
    if not a.rpc:
        sys.exit("[fatal] 非 --dry-run 必须给 --rpc（独立第二源 archive 节点）")
    if not a.chain:
        sys.exit("[fatal] 非 --dry-run 必须给 --chain，receipt target 禁止自报空链")
    if a.final_block is None:
        sys.exit("[fatal] 非 --dry-run 必须给 --final-block，receipt target 必须冻结截止块")

    token = a.token.lower()
    target = {"chain": a.chain, "token": token, "as_of_block": a.final_block}
    try:
        envelope = build_envelope(SCHEMA, target, __file__, execution_mode,
                                  inputs={"plan": a.plan})
    except Exception as exc:
        print(f"[fatal] receipt envelope 构建失败: {exc}", file=sys.stderr)
        return 1
    plan_chain = str(plan.get("chain") or "").lower()
    plan_token = str(plan.get("token") or "").lower()
    if plan_chain != a.chain or plan_token != token:
        result = finalize_envelope(
            envelope, "FAIL", 2, gate="time_spotcheck", error=(
                f"anchor_plan target {plan_chain}/{plan_token} 与 CLI {a.chain}/{token} 不一致"))
        try:
            publish_supersede(a.out, result, schema_family=SCHEMA_FAMILY)
        except Exception as exc:
            print(f"[time_spotcheck] FAIL receipt 写入失败: {exc}", file=sys.stderr)
            return 1
        return 2

    try:
        from net import attested_rpc_pool
        pool = attested_rpc_pool(
            a.rpc, a.chain, formal=True, rps=a.rps, concurrency=min(a.rps, 8))

        calls = []
        for p in bal_pts:
            blk = p.get("day_end_block")
            blk = int(blk) if blk is not None else a.final_block
            calls.append(("eth_call", [{"to": token,
                                        "data": BALANCEOF_SELECTOR + addr_word(p["addr"])},
                                       hexblock(blk)]))
        for p in tx_pts:
            calls.append(("eth_getTransactionReceipt", [p["tx"]]))
        results = pool.call_many(calls)
    except Exception as exc:
        try:
            error_path = publish_error_receipt(a.out, envelope, exc)
            print(f"[time_spotcheck] ERROR → {error_path}", file=sys.stderr)
        except Exception as write_exc:
            print(f"[time_spotcheck] ERROR receipt 写入失败: {write_exc}", file=sys.stderr)
        return 1

    rows, exact, mism, rpc_err = [], 0, 0, 0
    for p, r in zip(bal_pts, results[:len(bal_pts)]):
        blk = p.get("day_end_block")
        blk = int(blk) if blk is not None else a.final_block
        row = {"type": "balance", "kind": p.get("kind"), "addr": p["addr"], "block": blk,
               "expect_raw": str(p["expected_balance_raw"])}
        if not r.get("ok"):
            rpc_err += 1
            row.update(status="RPC_ERR", error=str(r.get("error"))[:200])
        else:
            got = int(r["result"], 16) if r["result"] not in (None, "0x") else 0
            exp = int(p["expected_balance_raw"])
            row.update(chain_raw=str(got), diff_raw=str(got - exp))
            if got == exp:
                exact += 1
                row["status"] = "OK"
            else:
                mism += 1
                row["status"] = "MISMATCH"
        rows.append(row)
    for p, r in zip(tx_pts, results[len(bal_pts):]):
        row = {"type": "tx", "kind": p.get("kind"), "tx": p["tx"],
               "expect_raw": str(p["expected_value_raw"]),
               "from": p.get("from"), "to": p.get("to"), "block": p.get("block")}
        if not r.get("ok") or r.get("result") is None:
            rpc_err += 1
            row.update(status="RPC_ERR", error=str(r.get("error") or "收据为 null")[:200])
        else:
            rc = r["result"]
            exp = int(p["expected_value_raw"])
            hit = False
            for lg in rc.get("logs", []):
                if (lg.get("address", "").lower() == token
                        and (lg.get("topics") or [""])[0].lower() == TRANSFER_TOPIC
                        and len(lg.get("topics", [])) >= 3
                        and lg["topics"][1][-40:].lower() == p.get("from", "").lower().replace("0x", "").rjust(40, "0")[-40:]
                        and lg["topics"][2][-40:].lower() == p.get("to", "").lower().replace("0x", "").rjust(40, "0")[-40:]
                        and int(lg.get("data", "0x0"), 16) == exp):
                    hit = True
                    break
            rblk = int(rc.get("blockNumber", "0x0"), 16)
            if hit and (p.get("block") is None or rblk == int(p["block"])):
                exact += 1
                row.update(status="OK", receipt_block=rblk)
            else:
                mism += 1
                row.update(status="MISMATCH", receipt_block=rblk,
                           note="收据中无匹配的 (token,from,to,value) Transfer log" if not hit
                                else f"块号不符: 收据 {rblk} vs 计划 {p.get('block')}")
        rows.append(row)

    if rpc_err:
        verdict, exit_code = "ERROR", 1     # 检测自身失败，禁当 PASS
    elif mism:
        verdict, exit_code = "FAIL", 2
    else:
        verdict, exit_code = "PASS", 0
    fields = {"gate": "time_spotcheck", "second_source": a.rpc, "token": token,
              "points": total, "balance_points": len(bal_pts), "tx_points": len(tx_pts),
              "exact_match": exact, "mismatch": mism, "rpc_err": rpc_err,
              "generated_at": datetime.datetime.now(datetime.timezone.utc)
                  .strftime("%Y-%m-%dT%H:%M:%SZ"), "rows": rows}
    if verdict == "ERROR":
        try:
            error_path = publish_error_receipt(a.out, envelope,
                                               f"{rpc_err} 个 RPC 观测失败")
            print(f"[time_spotcheck] ERROR → {error_path}", file=sys.stderr)
        except Exception as exc:
            print(f"[time_spotcheck] ERROR receipt 写入失败: {exc}", file=sys.stderr)
        return 1
    out = finalize_envelope(envelope, verdict, exit_code, **fields)
    try:
        if verdict == "FAIL":
            publish_supersede(a.out, out, schema_family=SCHEMA_FAMILY)
        else:
            publish_overwrite(a.out, out)
    except Exception as exc:
        print(f"[time_spotcheck] receipt 写入失败: {exc}", file=sys.stderr)
        return 1
    print(f"[time_spotcheck] {verdict}  {exact}/{total} 一致"
          f"（balance {len(bal_pts)} + tx {len(tx_pts)}；mismatch {mism}，rpc_err {rpc_err}）→ {a.out}")
    if mism:
        print("[time_spotcheck] 对不上＝数据有洞＝回去补——按 recon §5 对账差额排查步骤走，不许只改单点")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
