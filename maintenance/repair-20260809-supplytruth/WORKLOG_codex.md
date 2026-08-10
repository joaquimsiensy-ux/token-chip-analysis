[2026-08-09 07:39:43 EDT] A1 完成：新增 supply_semantics 单源并将 replay_duck/replay_pass1/replay_stream/verify_recon 的供给 sink 字面量收敛为 import；supply_truth_gate 原无该字面量，按工单暂不动。
[2026-08-09 07:42:10 EDT] A2 判断：replay_duck.py 直接计算 burn_total 并写 replay_stats，故同深度新增 zero/dead inflow、dead outflow、dead net 四字段。
[2026-08-09 07:42:10 EDT] A2 判断：replay_pass1.py 逐事件计算 burn_total 并写 replay_stats，故同深度逐事件累计四个拆分字段。
[2026-08-09 07:42:10 EDT] A2 判断：replay_stream.py 聚合 burn_total 并写 replay_stats，故同深度用过滤聚合新增四字段；不是仅引用 sink 作排除。
[2026-08-09 07:42:10 EDT] A2 完成：三种 replay 生产器的旧统计键全部保留，四个新字段一致，engine_equivalence 与 resume_integrity 离线测试通过。
[2026-08-09 07:43:00 EDT] A3 完成：decide 原样保留；EVM 主 FAIL 在四拆分字段齐全时复用同一 pool 批量对账 totalSupply/ZERO/DEAD，APU 回退 PASS，GNT/混合/1 wei/地址补偿均 FAIL，RPC 部分失败为 ERROR。
[2026-08-09 07:44:00 EDT] A4 完成：verify_recon 供给闭合改为 mint==nominal 且 balance_sum==mint 且无负值；burn_total_raw 仍独立落盘，下游仅消费 closed/negative_count，接口兼容。
[2026-08-09 07:46:00 EDT] A5 证据：holder_distribution_scan 仍优先读取 net_supply_raw、兼容读取 v3 保留的 replay_net，形态②分母语义不变。
[2026-08-09 07:46:00 EDT] A5 证据：handoff_manifest AUTO_GATES 的 read_gate_artifact 只取 verdict/exit_code，不读取 schema，对 v3 无感无需改码。
[2026-08-09 07:46:00 EDT] A5 完成：生产者/共享校验器/invariant manifest/正例 fixtures 全升 supply-truth-receipt/v3；v2 仅剩带 legacy 注释的拒收负例，supply/handoff/audit/invariant 测试通过。
[2026-08-09 07:48:00 EDT] A6 完成：先红证据已存；APU/GNT/混合/1 wei/地址补偿/旧 stats/形态①/RPC 失败/Solana 全部离线绿，burn=20 纵向闭环通过 verify_recon→supply_truth v3→shared validator。
[2026-08-09 07:52:00 EDT] A7 完成：EVM recon/A2 workflow/S-11/CHANGELOG 同步两形态与降级措辞，VERSION/SKILL/pyproject 一致升 6.38.0，docs/casebook/changelog/version 四闸全绿。
