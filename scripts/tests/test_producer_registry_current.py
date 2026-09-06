#!/usr/bin/env python3
"""离线守卫：当前生产者必登记，所有登记必须由本地 git 对象复现。"""
import hashlib
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts/lib"))
from producer_history import PRODUCER_HISTORY, historical_producer_hashes

CURRENT_PRODUCERS = {
    "scripts/solana/sqd_gap_repair.py": {
        "sqd-solana-cache/v4", "sqd-solana-repair-bundle/v1",
        "sqd-solana-coverage-resolution/v1", "sqd-solana-repair-pointer/v1"},
    "scripts/solana/fetch_sqd_transfers_v2.py": {"sqd-solana-cache/v4"},
    "scripts/solana/sqd_coverage_probe.py": {
        "sqd-solana-coverage/v1", "sqd-solana-coverage-pointer/v1"},
    "scripts/solana/window_fetch.py": {"solana-window-fetch-receipt/v3"},
}
# receipt_validate.py:115-116 默认以当前文件哈希为允许集；登记表两条只是
# 历史 anchor-plan/v2。test_anchor_plan_v3.py:376-377 的 assert not
# validate_receipt(...) 证明当前哈希无错误。豁免仅限下述精确协议对。
HISTORICAL_ONLY = {("scripts/lib/anchor_plan.py", "anchor-plan/v2")}


def main():
    fails = []

    def check(name, cond):
        print(f"{'ok' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    scripts = {row["script"] for row in PRODUCER_HISTORY}
    check("登记脚本集合与守卫清单一致",
          scripts == set(CURRENT_PRODUCERS) | {s for s, _ in HISTORICAL_ONLY})
    for script in sorted(scripts):
        found = {row["protocol"] for row in PRODUCER_HISTORY if row["script"] == script}
        if script in CURRENT_PRODUCERS:
            check(f"必要协议在场: {script}",
                  bool(found) and CURRENT_PRODUCERS[script] <= found)
        current = hashlib.sha256((REPO_ROOT / script).read_bytes()).hexdigest()
        for protocol in sorted(found):
            if (script, protocol) in HISTORICAL_ONLY:
                continue
            check(f"当前哈希 {script} {protocol} {current}: "
                  "改了生产者文件必须同步登记 scripts/lib/producer_history.py"
                  "(git show <commit>:<script> 可复现的哈希)",
                  current in historical_producer_hashes(script, protocol))

    cache = {}
    for row in PRODUCER_HISTORY:
        commit, script = row["commit"], row["script"]
        key = (commit, script)
        if key not in cache:
            cache[key] = subprocess.run(
                ["git", "show", f"{commit}:{script}"],
                cwd=REPO_ROOT, capture_output=True)
        result = cache[key]
        if result.returncode != 0:
            check("git 对象不可用(需要完整 git 仓库,浅克隆或源码包不满足): "
                  f"{commit}:{script}", False)
            continue
        actual = hashlib.sha256(result.stdout).hexdigest()
        check(f"登记与 git 历史{'一致' if actual == row['sha256'] else '不符'}: "
              f"{script} {commit} 登记 {row['sha256']} 实得 {actual}",
              actual == row["sha256"])
    print(f"producer registry: {len(fails)} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
