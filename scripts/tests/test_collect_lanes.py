#!/usr/bin/env python3
"""collect_queue 泳道调度离线测试（3.18.0；3.19 加 C2 锁与 C3 密钥用例）：
monkeypatch 假采集函数，不发任何网络请求。

验证六件事：
  1. EVM/Solana 双泳道真并行（总墙钟 ≈ max(泳道) 而非 sum）
  2. manifest 逐项记账完整、退出码语义不变（0 全成 / 1 有失败）
  3. --serial 回退可用
  4. C2 队列单实例锁：另一进程持 queue.lock 时本进程退出码 3、不动 manifest
  5. C2 每币目录写锁：另一进程持某币 .collect.lock 时该币 skipped_locked、
     其余照跑、退出码 1
  6. C3 密钥出 argv：collect_evm 构造的子进程命令行里无 token 明文、
     用 --token-file 传路径；run_guarded --run-id 进状态文件名并透传退出码
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CQ_PATH = os.path.join(HERE, "..", "collect", "collect_queue.py")
RG_PATH = os.path.join(HERE, "..", "run_guarded.py")

spec = importlib.util.spec_from_file_location("collect_queue", CQ_PATH)
cq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cq)

ORIG_COLLECT_EVM = cq.collect_evm  # 用例 6 要用真函数，先存

SLEEP = 0.4
FAKE_TOKEN = "fake-token-secret-abc123"

# 持锁 helper：子进程 flock 指定路径后打印 LOCKED 并驻留（模拟并发的另一采集进程）
HOLDER_SRC = r"""
import fcntl, json, os, sys, time
p = sys.argv[1]
os.makedirs(os.path.dirname(p), exist_ok=True)
f = open(p, "a+")
fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
f.seek(0); f.truncate()
json.dump({"pid": os.getpid(), "run_id": "holder-test", "role": "test-holder",
           "started": "2026-07-22T00:00:00Z",
           "heartbeat": "2026-07-22T00:00:00Z"}, f)
f.flush()
print("LOCKED", flush=True)
time.sleep(60)
"""


def fake_evm(it, workdir, token, token_file, logf):
    time.sleep(SLEEP)
    if it.get("_fail"):
        return {"status": "failed", "error": "注入失败"}
    return {"status": "done", "elapsed_s": SLEEP, "rows": 42,
            "min_block": 1, "max_block": 9}


def fake_sol(it, workdir, logf):
    time.sleep(SLEEP)
    return {"status": "done", "elapsed_s": SLEEP, "rows": 7,
            "outfile": os.path.join(workdir, "data", "fake.jsonl.gz")}


def hold_lock(path):
    """起一个真进程 flock 住 path，返回 Popen（记得 kill）。"""
    p = subprocess.Popen([sys.executable, "-c", HOLDER_SRC, path],
                         stdout=subprocess.PIPE, text=True)
    line = p.stdout.readline().strip()
    assert line == "LOCKED", f"helper 没锁上: {line!r}"
    return p


def run_case(items, extra_argv=(), tmp=None):
    """跑一次 main()，返回 (退出码, 墙钟秒, manifest dict)。"""
    tmp = tmp or tempfile.mkdtemp(prefix="lanes_")
    plan = {"base_dir": tmp, "items": items}
    plan_path = os.path.join(tmp, "plan.json")
    json.dump(plan, open(plan_path, "w"))
    tok = os.path.join(tmp, "token")
    open(tok, "w").write(FAKE_TOKEN)
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
    mpath = os.path.join(tmp, "collect_manifest.json")
    man = json.load(open(mpath)) if os.path.exists(mpath) else {"items": {}}
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

    # 4) C2 队列单实例锁：另一进程持 queue.lock → 退出 3、manifest 不动
    tmp4 = tempfile.mkdtemp(prefix="lanes_qlock_")
    holder = hold_lock(os.path.join(tmp4, "collect_plans", "queue.lock"))
    try:
        code, _, man = run_case(items4, tmp=tmp4)
        assert code == 3, f"队列锁被占应退出 3，实得 {code}"
        assert not man["items"], f"锁被占不应动 manifest: {man['items']}"
    finally:
        holder.kill()
        holder.wait()
    # holder 死后 flock 自动释放：同目录立即可重跑（陈死接管路径）
    code, _, man = run_case(items4, tmp=tmp4)
    assert code == 0 and len(man["items"]) == 4, \
        f"持锁进程死后应可接管重跑: code={code}"

    # 5) C2 每币写锁：另一进程持 E1 的 .collect.lock → E1 跳过、其余照跑、exit 1
    tmp5 = tempfile.mkdtemp(prefix="lanes_clock_")
    holder = hold_lock(os.path.join(tmp5, "E1分析", "data", ".collect.lock"))
    try:
        code, _, man = run_case(items4, tmp=tmp5)
        sts = {k.split("|")[0]: v["status"] for k, v in man["items"].items()}
        assert code == 1, f"有 skipped_locked 应退出 1，实得 {code}"
        assert sts["E1"] == "skipped_locked", f"E1 应 skipped_locked: {sts}"
        assert sts["E2"] == sts["S1"] == sts["S2"] == "done", \
            f"其余项不应受阻塞: {sts}"
        assert "写锁被占" in man["items"][f"E1|bsc|{A}"]["error"]
    finally:
        holder.kill()
        holder.wait()

    # 6a) C3：真 collect_evm 构造的子进程 argv 里无 token 明文、带 --token-file
    cq.collect_evm = ORIG_COLLECT_EVM
    captured = []

    def spy_call(cmd, **kw):
        captured.append(list(cmd))
        return 0

    orig = (cq.get_deploy_block, cq.subprocess.call, cq.evm_stats)
    cq.get_deploy_block = lambda chain, addr, probe: 123
    cq.subprocess.call = spy_call
    cq.evm_stats = lambda d: {"rows": 5, "min_block": 1, "max_block": 9}
    try:
        code, _, man = run_case([{"name": "E1", "chain": "bsc", "address": A}])
        assert code == 0 and captured, f"argv 用例没跑起来: code={code}"
        joined = " ".join(captured[0])
        assert FAKE_TOKEN not in joined, f"token 明文泄入子进程 argv: {captured[0]}"
        assert "--token-file" in captured[0], f"应传 --token-file: {captured[0]}"
    finally:
        cq.get_deploy_block, cq.subprocess.call, cq.evm_stats = orig
        cq.collect_evm = fake_evm

    # 6b) run_guarded --run-id：进状态文件名 + 退出码透传
    tmp6 = tempfile.mkdtemp(prefix="lanes_rg_")
    p = subprocess.run(
        [sys.executable, RG_PATH, "--name", "t", "--run-id", "ridA",
         "--out-dir", tmp6, "--interval", "0.2", "--",
         sys.executable, "-c", "import os,sys; sys.exit(2)"],
        capture_output=True, text=True)
    st_path = os.path.join(tmp6, "t.ridA.status.json")
    assert os.path.exists(st_path), f"状态文件应带 run_id: {os.listdir(tmp6)}"
    st = json.load(open(st_path))
    assert st["run_id"] == "ridA" and st["exit_code"] == 2
    assert p.returncode == 2, f"run_guarded 应透传退出码 2，实得 {p.returncode}"

    print("PASS: 双泳道并行、失败传播、--serial 回退、队列单实例锁(exit 3+死后接管)、"
          "每币写锁 skipped_locked、token 不进 argv、run_guarded run_id+退出码透传，"
          "七用例全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
