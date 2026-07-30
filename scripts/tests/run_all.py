#!/usr/bin/env python3
"""守护全家桶一键入口（v3.3）：三个 lint/manifest 守卫 + 核心账本离线测试。

复盘步骤 3"写入后跑守护三件套"扩为本命令；skill 脚本/文档任何改动收工前跑一次。
用法：python3 scripts/tests/run_all.py    退出码 0=全 PASS / 1=有 FAIL
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITE = ['changelog_lint.py', 'docs_lint.py', 'labels_manifest.py', 'env_check.py',
         'casebook_lint.py',
         'test_replay_inc.py', 'test_build_html.py', 'test_engine_equivalence.py',
         'test_collect_lanes.py', 'test_report_facts.py', 'test_fault_injection.py',
         'test_figures_from_facts.py', 'test_cluster_quality.py',
         'test_sqd_merge_equiv.py', 'test_supply_truth_gate.py',
         'test_handoff_manifest.py']


def main():
    results = []
    for name in SUITE:
        p = subprocess.run([sys.executable, os.path.join(HERE, name)],
                           capture_output=True, text=True)
        tail = (p.stdout.strip().splitlines() or ['(无输出)'])[-1]
        results.append((name, p.returncode, tail))
        if p.returncode != 0:
            print(f'--- {name} 完整输出 ---')
            print(p.stdout + p.stderr)
    print('=' * 56)
    bad = 0
    for name, rc, tail in results:
        mark = 'PASS' if rc == 0 else f'FAIL(rc={rc})'
        bad += rc != 0
        print(f'{mark:>10}  {name:<24} {tail[:70]}')
    print(f'{"=" * 56}\n{"全部通过" if not bad else str(bad) + " 项失败——修完再收工"}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
