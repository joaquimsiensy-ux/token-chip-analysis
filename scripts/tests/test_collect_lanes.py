#!/usr/bin/env python3
"""collect_queue 泳道调度离线测试（3.18.0）：monkeypatch 假采集函数，不发任何网络请求。

验证三件事：
  1. EVM/Solana 双泳道真并行（总墙钟 ≈ max(泳道) 而非 sum）
  2. manifest 逐项记账完整、退出码语义不变（0 全成 / 1 有失败）
  3. --serial 回退可用
"""
import importlib.util
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CQ_PATH = os.path.join(HERE, "..", "collect", "collect_queue.py")

spec = importlib.util.spec_from_file_location("collect_queue", CQ_PATH)
cq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cq)

SLEEP = 0.4


def fake_evm(it, workdir, token, logf):
    time.sleep(SLEEP)
    if it.get("_fail"):
        return {"status": "failed", "error": "注入失败"}
    return {"status": "done", "elapsed_s": SLEEP, "rows": 42,
            "min_block": 1, "max_block": 9}


def fake_sol(it, workdir, logf):
    time.sleep(SLEEP)
    return {"status": "done", "elapsed_s": SLEEP, "rows": 7,
            "outfile": os.path.join(workdir, "data", "fake.jsonl.gz")}


def run_case(items, extra_argv=()):
    """跑一次 main()，返回 (退出码, 墙钟秒, manifest dict)。"""
    tmp = tempfile.mkdtemp(prefix="lanes_")
    plan = {"base_dir": tmp, "items": items}
    plan_path = os.path.join(tmp, "plan.json")
    json.dump(plan, open(plan_path, "w"))
    tok = os.path.join(tmp, "token")
    open(tok, "w").write("fake-token")
    argv_bak = sys.argv
    sys.argv = ["collect_queue.py", plan_path, "--token-file", tok, *extra_argv]
    t0 = time.time()
    code = 0
    try:
        cq.main()
    except SystemExit as e:
        code = int(e.code or 0)
    finally:
        sys.argv = argv_bak
    dur = time.time() - t0
    man = json.load(open(os.path.join(tmp, "collect_manifest.json")))
    return code, dur, man


def main():
    cq.collect_evm = fake_evm
    cq.collect_solana = fake_sol

    A = "0x" + "1" * 40
    B = "0x" + "2" * 40
    items4 = [{"name": "E1", "chain": "bsc", "address": A},
              {"name": "E2", "chain": "eth", "address": B},
              {"name": "S1", "chain": "solana", "address": "MintAaaa1111"},
              {"name": "S2", "chain": "solana", "address": "MintBbbb2222"}]

    # 1) 并行性：串行=4×SLEEP=1.6s，双泳道≈0.8s
    code, dur, man = run_case(items4)
    assert code == 0, f"应全成退出 0，实得 {code}"
    statuses = [v["status"] for v in man["items"].values()]
    assert statuses.count("done") == 4, f"manifest 应 4 done: {statuses}"
    serial_floor = 4 * SLEEP
    assert dur < serial_floor * 0.8, \
        f"墙钟 {dur:.2f}s 未体现并行（串行下限 {serial_floor:.2f}s）"

    # 2) 失败传播：EVM 泳道一项注入失败 → 退出码 1，其余项不受阻塞
    items_f = [dict(items4[0], _fail=True)] + items4[1:]
    code, _, man = run_case(items_f)
    assert code == 1, f"有失败应退出 1，实得 {code}"
    sts = {k.split("|")[0]: v["status"] for k, v in man["items"].items()}
    assert sts["E1"] == "failed" and sts["E2"] == "done", f"失败不应阻塞后续: {sts}"

    # 3) --serial 回退
    code, dur, man = run_case(items4, extra_argv=("--serial",))
    assert code == 0 and len(man["items"]) == 4
    assert dur >= serial_floor * 0.95, f"--serial 应全串行，墙钟 {dur:.2f}s 过短"

    print(f"PASS: 双泳道并行（4 项 {dur:.1f}s 串行 vs 并行提速实证）、"
          "失败传播退出码 1、--serial 回退，三用例全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
