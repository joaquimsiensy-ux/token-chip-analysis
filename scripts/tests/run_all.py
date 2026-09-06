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
         'test_batch2_legacy_hardening.py',
         'test_batch2_registry_harness_hardening.py',
         'test_batch3_solana_producers.py',
         'test_batch3_solana_vertical_slice.py',
         'test_batch3_evm_vertical_slice.py',
         'test_r9_batch1_boundaries.py',
         'test_r9_solana_attested_session.py',
         'test_r9_batch2_attestation_adapters.py',
         'test_r9_batch2_executable_capabilities.py',
         'test_r9_batch2_solana_sqd_adapter.py',
         'test_r9_batch3_solana_observation.py',
         'test_r9_batch3_dynamic_runner.py',
         'test_r9_batch3_preflight.py',
         'test_r9_batch3_release_guards.py',
         'test_batch4_invariant_guards.py',
         'test_exemption_guards.py',
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
         'test_roundtrip_check.py', 'test_label_snapshot_roundtrip.py',
         'test_goldset_curated_rebuild.py',
         'test_arbitrum_label_consumers.py', 'test_benchmark_labels.py',
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
         'test_sqd_merge_equiv.py', 'test_spl_edge_core.py',
         'test_sqd_collector_meta_v4.py', 'test_sqd_consumer_v4.py',
         'test_supply_truth_gate.py',
         'test_repair_batch_a.py',
         'test_repair_batch_b.py',
         'test_repair_batch_c.py',
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
SUITE += ['test_distribution_chart.py']

# v6.39.0 APU 案（ANOM-012）存量迁移三工单：replay_stats 覆盖截止块契约、
# 太古 done 官方迁移全链、旧 −1 产物格式迁移命令。
SUITE += ['test_apu_legacy_gaps.py']

# v6.40.0 六视角 BLOCK 修复工程批 D（F-06/F-07/GPT-F-06＋台账 A-1/A-3/A-5/B-1/B-2/B-4/B-5/B-7）
SUITE += ['test_repair_batch_d.py']

# v6.41.0 批1 步骤1 RV-07：真 FAIL 收据显式归档旧 PASS 后成为 canonical。
SUITE += ['test_repair_batch1.py']

# SQD Solana v4 批6：opus 攻击型盲审点名的 producer→formal gate 交叉回归。
SUITE += ['test_batch6_sqd_v4_blind_review.py']

# v6.42.0 批2 工单 B：F-02 对抗复核 v3 结构与绑定闭环。
SUITE += ['test_repair_batch2_f02.py']

# 批3 工单 F01：A4 blocker 语义联动、文本门槛与 entrypoint 身份闭环。
SUITE += ['test_repair_batch3_f01.py']

# 批3工单 F04/F05：deploy-sync 与 env_check fail-closed 注入回归。
SUITE += ['test_repair_batch3_gates.py']

# EVM 观测锚工程工单 A：bundle/transcript 协议、producer 与 fail-closed 负测。
SUITE += ['test_evm_observation.py']

# EVM 观测锚工程工单 C：shared/handoff/audit 公共消费、N-2 与原 F-02/F-03 反例。
SUITE += ['test_evm_observation_release.py']

# AI-1 正式边界与守卫组 test-only 包1/包2/包4 登记（2026-08-15 修复计划）。
SUITE += ['test_repair_g1_audit_report.py',
          'test_repair_g1_risk_flags_pipeline.py',
          'test_repair_g1_handoff_containment.py']

# AI-1 包3 F-03/F-14：跨分区 target 等式与现役文本卫生（2026-08-15 修复计划）。
SUITE += ['test_repair_g1_cross_target.py',
          'test_repair_g1_text_hygiene.py']

# repair-20260815-g2（F-04/F-07/F-09/F-10）：观测件收紧/对账深重验/GMGN 黄灯/探索档 CLI
SUITE += [
    'test_evm_observation_nonempty_code.py',
    'test_arbitrum_exploration_cli.py',
    'test_recon_deep_reverify.py',
    'test_gmgn_divergence_note.py',
]

# repair-20260815-g3（F-05/F-06/F-08/F-13）：文档守卫与备用采集器（融合方登记）
SUITE += [
    'test_g3_docs_guards.py',
    'test_g3_alt_collectors.py',
]

# R-2 采集器历史哈希登记表：状态过滤、CSV provenance 与 git 考证守卫。
SUITE += ['test_collector_history.py']

# R-3 v2 identity 历史兼容：维护/消费链同判定、严格形状与混合目录边界。
SUITE += ['test_v2_identity_history.py']

# U1 anchor-plan/v3：机器块源/XOR 契约、v2 重放投影与 producer 历史兼容。
SUITE += ['test_anchor_plan_v3.py']

# U2 done/v4：逐段 collector 归属、legacy-unattributed 迁移与 C12 显式恢复。
SUITE += ['test_done_v4_collector.py']
SUITE += ['test_csv_resume_collector_gate.py']

# v6.52.0 SQD coverage/repair producer、reconcile v4 receipt 与 Solana A2 第五查收口。
SUITE += [
    'test_sqd_coverage_probe.py',
    'test_f03_sharedmap_reuse.py',
    'test_batch2d_stream_tail.py',
    'test_sqd_gap_repair.py',
    'test_reconcile_v4_receipt.py',
    'test_recon_fifth_check.py',
]
SUITE += ['test_batch3c_census_fields.py']  # v6.52.4 batch3c SQD census field contract
SUITE += ['test_batch8_repair_scale.py']  # v6.52.6 Batch 8 producer scale and streaming contract

# 批7 修复代深验三处校验覆盖缺口加固：缺口1(遍历主键绑定候选集致 confirmed-only slot
# 严格校验被跳过)、缺口3(深验未校验边 slot ⊆ 声明窗口)；缺口2(自扫 coverage 无真实性
# 复查)判定为离线信任边界仅在 batch7_done.md 记录，不进本 suite 断言。
SUITE += ['test_batch7_validator_coverage_gaps.py']

# Batch 11：Solana 静态态同文件绑定不变；冻结态改绑案内 frozen bundle 指纹与 handoff 清单。
SUITE += ['test_batch11_frozen_bundle_binding.py']

# Batch 12：distribution scanner 尊重 supply_truth PASS 收据的冻结态容差，静态态零变化。
SUITE += ['test_batch12_frozen_supply_drift.py']

# Batch 13：handoff/shared/audit 的 accounting 期望 target 支持静态/冻结两态。
SUITE += ['test_batch13_accounting_target.py']

# Batch 14：Solana accounting 冻结态 bundle 按 size+sha256 内容寻址，安全失败不兜底。
SUITE += ['test_batch14_accounting_bundle_fallback.py']

# Batch 15：发布闸 B-7 三账对账源＋series cutoff 冻结态投影（方案 A 第七/八消费点）。
SUITE += ['test_batch15_three_ledgers_frozen.py']

# v6.52.2 repair-20260824-lit-regression：F-007 series_format 堆叠语义与 F-008 evm_v2 集合闸。
SUITE += ["test_lit_regression_f007.py", "test_lit_regression_f008.py"]  # v6.52.2 repair-20260824-lit-regression

# Batch 16：序列来源链登记路径按案根解析兜底（sqd_repair 深层缓存）。
SUITE += ['test_batch16_resolve_ref_case_path.py']

# Batch 17：G8 链名别名归一
SUITE += ['test_batch17_identity_chain_alias.py']

# Batch 18：共享 reconciliation witness/provider 正式接口。
SUITE += ['test_batch18_shared_bundle_witness.py']

# Batch 18：handoff manifest 反绑产物单向排除与 −2 收敛。
SUITE += ['test_batch18_manifest_stage2_loop.py']

# Batch 18 盲审消化：witness 身份/文件闭包防伪与 manifest 分类器类型防御。
SUITE += ['test_batch18_review_digest.py']
# repair-20260906-main-threefix：生产者当前哈希必登记 + 登记 git 可复现守卫。
SUITE += ['test_producer_registry_current.py']


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
