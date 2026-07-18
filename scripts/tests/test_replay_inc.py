#!/usr/bin/env python3
"""replay_inc.py 离线 fixture 测试（v3.3：硬关卡行为的机器约束）。

覆盖四条路径（对应 replay_inc 的退出码契约）：
  1. 正常增量重放：余额精确 + 恒等式闭合 → exit 0
  2. 非零地址负余额（数据洞）→ exit 1
  3. 旧快照含 ZERO 负项但恒等式不闭合 → exit 1
  4. 正余额型旧快照（无 ZERO 键，COMPUTE 型实战格式）→ NOTE 降级、exit 0

无网络、无外部依赖；tempdir 内造 config.json + 快照 + 增量文件跑真脚本。
用法：python3 scripts/tests/test_replay_inc.py    退出码 0=PASS / 1=FAIL
"""
import gzip, json, os, subprocess, sys, tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SCRIPT = os.path.join(ROOT, 'scripts', 'update', 'replay_inc.py')
ZERO = '0x' + '0' * 40
E18 = 10 ** 18
A, B, C, X = ('0x' + c * 40 for c in 'abcd')
DEAD = '0x' + 'dead' * 10


def run_case(tag, old_bal, rows, expect_exit, expect_in_out=None, expect_bal=None):
    with tempfile.TemporaryDirectory() as d:
        json.dump({'total_supply_tokens': '1000', 'decimals': 18, 'pools': {}},
                  open(os.path.join(d, 'config.json'), 'w'))
        json.dump({k: str(v) for k, v in old_bal.items()},
                  open(os.path.join(d, 'old.json'), 'w'))
        os.makedirs(os.path.join(d, 'data'), exist_ok=True)
        with gzip.open(os.path.join(d, 'inc.jsonl.gz'), 'wt') as f:
            for r in rows:
                f.write(json.dumps(r) + '\n')
        p = subprocess.run([sys.executable, SCRIPT, '--old-balances', 'old.json',
                            '--inc', 'inc.jsonl.gz', '--cutoff-block', '100'],
                           cwd=d, capture_output=True, text=True)
        fails = []
        if p.returncode != expect_exit:
            fails.append(f'退出码 {p.returncode} != 期望 {expect_exit}\n--- stdout ---\n{p.stdout}')
        if expect_in_out and expect_in_out not in p.stdout:
            fails.append(f'stdout 缺关键字「{expect_in_out}」')
        if expect_bal and p.returncode == 0:
            out = json.load(open(os.path.join(d, 'data', 'balances_new.json')))
            got = {k.lower(): int(v) for k, v in out['balances'].items()}
            for addr, want in expect_bal.items():
                if got.get(addr.lower(), 0) != want:
                    fails.append(f'余额 {addr[:10]}… got {got.get(addr.lower(), 0)} != want {want}')
        if fails:
            print(f'FAIL [{tag}]:');  [print('  ' + x) for x in fails]
            return False
        print(f'ok   [{tag}]')
        return True


def tx(i, frm, to, amt):
    return {'block': 100 + i, 'ts': 1700000000 + i, 'tx': f'0x{i:064x}', 'logi': 0,
            'from': frm, 'to': to, 'amount': str(amt)}


def main():
    ok = True
    # 1. 正常：A→B 100、B→C 50、A→DEAD 10（burn）
    ok &= run_case('正常重放+恒等式闭合',
                   {ZERO: -1000 * E18, A: 600 * E18, B: 400 * E18},
                   [tx(1, A, B, 100 * E18), tx(2, B, C, 50 * E18), tx(3, A, DEAD, 10 * E18)],
                   0, expect_bal={A: 490 * E18, B: 450 * E18, C: 50 * E18})
    # 2. 数据洞：C 只有 50 却转出 100 → 负余额 → exit 1
    ok &= run_case('非零地址负余额=FAIL',
                   {ZERO: -1000 * E18, A: 600 * E18, B: 400 * E18},
                   [tx(1, B, C, 50 * E18), tx(2, C, X, 100 * E18)],
                   1, expect_in_out='FAIL: 非零地址出现负余额')
    # 3. 含 ZERO 的快照自身不闭合（少了 B 的 400）→ exit 1
    ok &= run_case('恒等式不闭合=FAIL',
                   {ZERO: -1000 * E18, A: 600 * E18},
                   [tx(1, A, B, 100 * E18)],
                   1, expect_in_out='FAIL: 全地址余额和')
    # 4. 正余额型快照（无 ZERO）：恒等式不适用，NOTE 降级 → exit 0
    ok &= run_case('正余额型快照 NOTE 降级',
                   {A: 600 * E18, B: 400 * E18},
                   [tx(1, A, B, 100 * E18)],
                   0, expect_in_out='NOTE: 旧快照未保留 ZERO')
    print('PASS: replay_inc 四条路径全过' if ok else 'FAIL: 见上')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
