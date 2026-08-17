#!/usr/bin/env python3
"""time_spotcheck 契约测试（离线，--dry-run 黑盒；不打网）。

覆盖（A2 时间抽查执行器的 fail-closed 反例集，6.7.0）：
  1. 两型分型正确：balance 型（matrix+净变动+边缘）与 tx 型（最大单笔/交界块）计数分明
  2. 0 锚点 → assert 硬失败（GMX 案"0 点假 PASS"教训的机器化）
  3. 两型都不匹配的锚点（格式漂移）→ exit 非 0
  4. 边缘点缺 day_end_block 且未传 --final-block → exit 非 0（禁静默跳点）
  5. 非 dry-run 缺 --rpc → exit 非 0
用法：python3 scripts/tests/test_time_spotcheck.py   退出码 0=PASS / 1=FAIL
"""
import json
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "lib", "time_spotcheck.py")
ANCHOR = os.path.join(HERE, "..", "lib", "anchor_plan.py")
LIB = Path(HERE).parent / "lib"
ROOT = Path(HERE).parents[1]
sys.path.insert(0, str(LIB))
from anchor_selection import EXPECTED_PLAN_PRODUCER

FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
    else:
        print(f"ok    {name}")


def run(args):
    return subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def supports_input_arg():
    return "--input" in run(["--help"]).stdout


def run_consumer(source, args):
    """Keep the pre-fix attack runnable, then exercise --input once implemented."""
    prefix = ["--input", str(source)] if supports_input_arg() else []
    return run(prefix + args)


def wj(d, name, obj):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    return p


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def refresh_bundle(plan_path, mutate):
    plan_file = Path(plan_path)
    receipt_file = plan_file.with_name("anchor_plan.receipt.json")
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    mutate(plan)
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    receipt["output"]["size"] = plan_file.stat().st_size
    receipt["output"]["sha256"] = sha(plan_file)
    receipt["probe_count"] = sum(len(plan.get(key) or [])
                                  for key in ("matrix_points", "forced_points"))
    receipt_file.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    return str(plan_file)


def forge_producer_bundle(plan_path):
    """Re-sign a real plan while falsely naming an unrelated repo file as producer."""
    plan_file = Path(plan_path)
    receipt_file = plan_file.with_name("anchor_plan.receipt.json")
    fake_path = "references/maintenance-review-repair.md"
    fake_producer = {
        "path": fake_path,
        "sha256": sha(Path(HERE).parents[1] / fake_path),
    }
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    plan["producer"] = fake_producer
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    receipt["producer"] = fake_producer
    receipt["output"]["size"] = plan_file.stat().st_size
    receipt["output"]["sha256"] = sha(plan_file)
    receipt_file.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")


def forge_registered_one_point_bundle(d, source, token):
    """Reproduce B1R-01 C2: true path/hash, but a fully hand-written one-point plan."""
    root = Path(HERE).parents[1]
    producer = {"path": "scripts/lib/anchor_plan.py", "sha256": sha(root / "scripts/lib/anchor_plan.py")}
    identity = {"path": str(source.resolve()), "kind": "file",
                "size": source.stat().st_size, "sha256": sha(source)}
    manifest_path = Path(d) / "forged-anchor-plan.input.json"
    manifest = {"schema": "anchor-plan-input/v1", "input": identity,
                "files": [identity]}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    manifest_ref = {"path": str(manifest_path.resolve()), "size": manifest_path.stat().st_size,
                    "sha256": sha(manifest_path)}
    generated_at = "2026-08-07T00:00:00Z"
    target = {"chain": "bsc", "token": token, "as_of_block": 300}
    plan = {
        "schema": "anchor-plan/v2", "generated_at": generated_at, "target": target,
        "input": identity, "chain": "bsc", "token": token, "final_block": 300,
        "total_supply": 10000.0, "decimals": 0, "threshold_pct": 1.0,
        "min_pct": 0.0, "per_cell": 1, "edge_max": 5, "seed": 42,
        "date_range": ["2025-01-01", "2025-01-01"],
        "time_cuts": ["2025-01-01", "2025-01-02"],
        "cell_population": {"中·大户": 1}, "boundary_blocks": [],
        "matrix_points": [{"kind": "forged", "addr": "0x" + "1" * 40,
                           "day": "2025-01-01", "day_end_block": 100,
                           "expected_balance_raw": "100"}],
        "forced_points": [], "producer": producer, "input_manifest": manifest_ref,
    }
    plan_path = Path(d) / "forged-anchor-plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    receipt = {
        "schema": "anchor-plan-receipt/v2", "target": target, "producer": producer,
        "mode": "formal", "inputs": {"input_manifest": manifest_ref},
        "plan_schema": "anchor-plan/v2", "generated_at": generated_at,
        "input_identity": identity, "probe_count": 1,
        "output": {"path": str(plan_path.resolve()), "size": plan_path.stat().st_size,
                   "sha256": sha(plan_path)}, "verdict": "PASS", "exit_code": 0,
    }
    plan_path.with_name("forged-anchor-plan.receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(plan_path)


def produce_plan(d, token):
    source = Path(d) / "transfers.csv"
    rows = ["block,ts,tx,from,to,value"]
    for index in range(1, 21):
        rows.append(
            f"{99 + index},2025-01-01T00:00:00Z,0xt{index},0x{'0' * 40},"
            f"0x{index:040x},100")
    source.write_text("\n".join(rows) + "\n", encoding="utf-8")
    p = subprocess.run([sys.executable, ANCHOR, "--input", str(source),
                        "--chain", "bsc", "--token", token, "--total-supply", "10000",
                        "--decimals", "0", "--min-pct", "0", "--final-block", "300",
                        "--out-dir", d], capture_output=True, text=True)
    if p.returncode != 0:
        raise AssertionError(p.stdout + p.stderr)
    return str(Path(d) / "anchor_plan.json"), source


def main():
    with tempfile.TemporaryDirectory(prefix="spotcheck_test_") as d:
        out = os.path.join(d, "out.json")
        token = "0x594daad7d77592a2b97b725a7ad59d7e188b5bfa"
        base = ["--chain", "bsc", "--token", token, "--out", out]
        plan, source = produce_plan(d, token)
        original_plan = Path(plan).read_bytes()
        original_receipt = (Path(d) / "anchor_plan.receipt.json").read_bytes()

        # 1. 正例必须来自真实 producer，receipt 验证后再做两型分型。
        p = run_consumer(source, ["--plan", plan, "--dry-run", "--final-block", "300"] + base)
        expected = json.loads(Path(plan).read_text(encoding="utf-8"))
        exp_bal = sum(1 for key in ("matrix_points", "forced_points")
                      for point in expected.get(key, [])
                      if point.get("expected_balance_raw") is not None and point.get("addr"))
        exp_tx = sum(1 for key in ("matrix_points", "forced_points")
                     for point in expected.get(key, [])
                     if point.get("tx") and point.get("expected_value_raw") is not None)
        ok = p.returncode == 0
        if ok:
            st = json.loads(p.stdout.strip().splitlines()[-1])
            ok = st["balance_points"] == exp_bal and st["tx_points"] == exp_tx
        if not ok:
            print(f"positive consumer rc={p.returncode} stdout={p.stdout!r} stderr={p.stderr!r}")
        check("真实 producer+receipt 的两型分型正确", ok)

        def restore():
            Path(plan).write_bytes(original_plan)
            (Path(d) / "anchor_plan.receipt.json").write_bytes(original_receipt)

        # 2. 0 锚点硬失败（负例允许重签 fixture 以抵达业务分支）。
        refresh_bundle(plan, lambda obj: (obj.__setitem__("matrix_points", []),
                                          obj.__setitem__("forced_points", [])))
        p = run_consumer(source, ["--plan", plan, "--dry-run", "--final-block", "300"] + base)
        check("0 锚点 assert 硬失败", p.returncode != 0)
        restore()

        # 3. 格式漂移锚点。
        refresh_bundle(plan, lambda obj: (obj.__setitem__("matrix_points", [
            {"kind": "怪点", "addr": "0xee", "day": "2025-01-01"}]),
                                          obj.__setitem__("forced_points", [])))
        p = run_consumer(source, ["--plan", plan, "--dry-run", "--final-block", "300"] + base)
        check("格式漂移锚点 exit 非 0", p.returncode != 0)
        restore()

        # 4. final block 是 producer/consumer 双边必填。
        p = run_consumer(source, ["--plan", plan, "--dry-run"] + base)
        check("未传 --final-block exit 非 0", p.returncode != 0)

        # 5. 非 dry-run 缺 --rpc。
        p = run_consumer(source, ["--plan", plan, "--final-block", "300"] + base)
        check("非 dry-run 缺 --rpc exit 非 0", p.returncode != 0)

        # 6. plan 必须精确绑定 final block，且任一查询块不得越过冻结点。
        p = run_consumer(source, ["--plan", plan, "--dry-run", "--final-block", "299"] + base)
        check("plan final_block 与 CLI 不精确一致拒绝", p.returncode != 0)

        def push_beyond(obj):
            points = obj["matrix_points"] + obj["forced_points"]
            point = next(item for item in points
                         if item.get("day_end_block") is not None or item.get("block") is not None)
            key = "day_end_block" if item_has(point, "day_end_block") else "block"
            point[key] = 301

        def item_has(point, key):
            return point.get(key) is not None

        refresh_bundle(plan, push_beyond)
        p = run_consumer(source, ["--plan", plan, "--dry-run", "--final-block", "300"] + base)
        check("查询块越过 final_block 在 RPC 前拒绝", p.returncode != 0)
        restore()

        # 7. plan 字节被替换但 receipt 未同步时，先在 receipt 层拒绝。
        changed = json.loads(Path(plan).read_text(encoding="utf-8"))
        changed["seed"] += 1
        Path(plan).write_text(json.dumps(changed, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
        p = run_consumer(source, ["--plan", plan, "--dry-run", "--final-block", "300"] + base)
        check("plan/receipt 哈希不一致拒绝", p.returncode != 0)

        # 8. plan+receipt 可以自洽重签，但 consumer 必须绑定登记的真实 producer。
        restore()
        forge_producer_bundle(plan)
        p = run_consumer(source, ["--plan", plan, "--dry-run", "--final-block", "300"] + base)
        check("伪造 Markdown producer 的 dry-run 在业务前拒绝",
              p.returncode != 0 and "registered anchor producer" in p.stderr)
        formal_out = os.path.join(d, "formal-out.json")
        p = run_consumer(source, ["--plan", plan, "--rpc", "http://127.0.0.1:1/nope",
                                  "--final-block", "300", "--chain", "bsc", "--token", token,
                                  "--out", formal_out])
        check("伪造 Markdown producer 的正式路径在 RPC 前拒绝",
              p.returncode != 0 and "registered anchor producer" in p.stderr
              and not list(Path(d).glob("formal-out.error.*.json")))

        # 9. 重审 C2 原攻击：producer 路径与 SHA 都真，plan/receipt 完全手写且只留 1 点。
        restore()
        forged = forge_registered_one_point_bundle(d, source, token)
        p = run_consumer(source, ["--plan", forged, "--dry-run", "--final-block", "300"] + base)
        check("真路径真哈希的手写 1 锚点 dry-run 在重放层拒绝",
              p.returncode != 0 and "semantic replay" in p.stderr)
        forged_formal = os.path.join(d, "forged-formal.json")
        p = run_consumer(source, ["--plan", forged, "--rpc", "http://127.0.0.1:1/nope",
                                  "--final-block", "300", "--chain", "bsc", "--token", token,
                                  "--out", forged_formal])
        check("真路径真哈希的手写 1 锚点正式路径在 RPC 前拒绝",
              p.returncode != 0 and "semantic replay" in p.stderr
              and not list(Path(d).glob("forged-formal.error.*.json")))

        # 10. 非同构变形集：每次都自洽重签 receipt，必须由数学重放识破。
        mutations = [
            ("改 expected_balance_raw", lambda obj: next(
                point for key in ("matrix_points", "forced_points")
                for point in obj[key] if point.get("expected_balance_raw") is not None
            ).__setitem__("expected_balance_raw", "999999")),
            ("删一个锚点", lambda obj: (obj["matrix_points"] or obj["forced_points"]).pop()),
            ("换 seed 声明", lambda obj: obj.__setitem__("seed", obj["seed"] + 1)),
            ("改 cell_population 一格", lambda obj: obj["cell_population"].__setitem__(
                next(iter(obj["cell_population"])), 999999)),
            ("缺 per_cell 参数", lambda obj: obj.pop("per_cell", None)),
        ]
        for label, mutate in mutations:
            restore()
            refresh_bundle(plan, mutate)
            p = run_consumer(source, ["--plan", plan, "--dry-run", "--final-block", "300"] + base)
            check(f"重放拒绝变形：{label}",
                  p.returncode != 0 and "semantic replay" in p.stderr)

        # 10b. 即使 plan/receipt 自洽重签，退化参数也要在 SQL 重放前独立拒绝。
        restore()
        refresh_bundle(plan, lambda obj: (obj.__setitem__("per_cell", 1),
                                          obj.__setitem__("edge_max", 1)))
        p = run_consumer(source, ["--plan", plan, "--dry-run",
                                  "--final-block", "300"] + base)
        check("per_cell=1/edge_max=1 弱覆盖参数在重放前拒绝",
              p.returncode != 0 and "minimum coverage" in p.stderr)

        # 11. --input 是真实输入绑定，不得保留旧的无输入消费入口。
        restore()
        p = run(["--plan", plan, "--dry-run", "--final-block", "300"] + base)
        check("consumer --input 必填", supports_input_arg() and p.returncode != 0
              and "--input" in p.stderr)

        # 12. 登记 producer 的唯一常量必须与机器 manifest 双向对账。
        manifest = json.loads((ROOT / "scripts/tests/invariant_manifest.json").read_text(
            encoding="utf-8"))
        registered = [entry for entry in manifest["receipt_producers"]
                      if entry.get("script") == EXPECTED_PLAN_PRODUCER
                      and "anchor-plan/v3" in entry.get("schemas", [])]
        check("EXPECTED_PLAN_PRODUCER 与 invariant_manifest 单源对账",
              len(registered) == 1
              and registered[0].get("script") == EXPECTED_PLAN_PRODUCER)

        # 13. 同 schema/路径类型但内容不同的真实输入必须在 SQL 重放前由身份哈希拒绝。
        wrong_source = Path(d) / "wrong-transfers.csv"
        wrong_source.write_bytes(source.read_bytes() + (
            f"250,2025-01-02T00:00:00Z,0xwrong,0x{'0' * 40},0x{'9' * 40},1\n"
        ).encode("utf-8"))
        p = run_consumer(wrong_source, ["--plan", plan, "--dry-run",
                                        "--final-block", "300"] + base)
        check("实际 --input SHA256 与 plan.input.sha256 不一致拒绝",
              p.returncode != 0 and "semantic replay" in p.stderr
              and "input sha256 mismatch" in p.stderr)

    print("=" * 40)
    if FAILS:
        print(f"time_spotcheck 契约测试 {len(FAILS)} 项失败")
        return 1
    print("time_spotcheck 契约测试全部通过（20 项）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
