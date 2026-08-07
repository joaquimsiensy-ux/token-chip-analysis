#!/usr/bin/env python3
"""守护全家桶一键入口（v3.3）：三个 lint/manifest 守卫 + 核心账本离线测试。

复盘步骤 3"写入后跑守护三件套"扩为本命令；skill 脚本/文档任何改动收工前跑一次。
用法：python3 scripts/tests/run_all.py    退出码 0=全 PASS / 1=有 FAIL
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITE = ['changelog_lint.py', ['docs_lint.py', '--all'], 'labels_manifest.py',
         'invariant_scan.py', 'test_r7_findings.py',
         'test_net_result.py',
         'test_batch1_rpc_attestation.py',
         'test_batch2_p3_hardening.py',
         'test_batch2_capability_matrix.py',
         'test_batch2_ready_reconciliation.py',
         'test_batch2_robinhood_exploration.py',
         'test_receipt_kernel.py',
         'test_batch1_receipt_paths.py',
         'test_reconciliation_runner.py', 'test_chain_registry.py',
         '../labels/check_manual_sync.py', 'env_check.py',
         'test_commands_deploy_sync.py',
         'casebook_lint.py', 'fixtures_lint.py',
         'test_build_html.py', 'test_engine_equivalence.py',
         'test_report_facts.py', 'test_fault_injection.py',
         'test_review_evm_integrity.py',
         'test_review_solana_integrity.py',
         'test_review_labels.py',
         'test_review_robinhood_integrity.py',
         'test_review_resume_integrity.py',
         'test_entity_identity_gate.py',
         'test_review_chain_collectors.py',
         'test_labels_resolver_guards.py',
         'test_batch1_risk_flags.py',
         'test_roundtrip_check.py', 'test_benchmark_labels.py',
         'test_add_labels_rollback.py',
         'test_fetch_failclosed.py', 'test_fetch_gmgn_sh.py', 'test_sixlens_receipts.py',
         'test_sixlens_docs.py',
         'test_token_no_positional.py',
         'test_contract_routes.py',
         'test_version_consistency.py',
         'test_chain_support_matrix.py',
         'test_formal_chain_support.py',
         'test_review_scale_guards.py',
         'test_figures_from_facts.py', 'test_cluster_quality.py',
         'test_sqd_merge_equiv.py', 'test_supply_truth_gate.py',
         'test_handoff_manifest.py', 'test_audit_release_gate.py',
         'test_review_20260804_p0.py',
         'test_review_20260804_p101.py',
         'test_review_20260804_p104.py',
         'test_review_20260804_p105.py',
         'test_review_20260804_p106.py',
         'test_review_20260804_p201.py',
         'test_review_20260804_p202.py',
         'test_round4_csv_adapters.py',
         'test_param_scripts.py',
         'test_round4_a5_seal.py',
         'test_round4_identity_emitter.py', 'test_round4b_provenance.py',
         'test_round4c_solana_provenance.py',
         'test_state_from_facts.py',
         'test_a4_gate.py', 'test_time_spotcheck.py', 'test_peaks_daily.py',
         'test_wave_scan.py', 'test_flow_anomaly.py',
         'test_entity_source_trace.py', 'test_adjudication_validator.py']

# v6.20.0 持仓分布形态硬闸。单列在扫描器与封口链测试之后，任何新绕过都会阻断全量 suite。
SUITE += ['test_distribution_gate.py']


def main():
    results = []
    for item in SUITE:
        args = item if isinstance(item, list) else [item]
        name = ' '.join(args)
        p = subprocess.run([sys.executable, os.path.join(HERE, args[0])] + args[1:],
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
