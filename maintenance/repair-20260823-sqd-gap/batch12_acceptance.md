# 批 12 Fable 验收记录（2026-08-27）

裁决依据：延续用户方案 A。ARC A3 第 8 项实跑暴露时点矛盾第四消费点
（holder_distribution_scan `net > onchain` 静态硬拒 vs 封账后微量销毁）。

## 验收项与结论

1. **diff 审查**：`load_supply` 漂移分支＝PASS/exit 0（既有 :235 检查）＋收据 diff
   逐位复算相等＋整数容差 `drift*10000 <= tolerance_bps*onchain`（无浮点）；任一不满足
   原句硬拒＋边界说明。静态向（net ≤ onchain）零变化；快照闭合锚（Solana
   sum==onchain 精确等式、SNAPSHOT_CLOSURE_TOLERANCE_BPS=0）不动；分母语义不变
   （net 仍为分布分母），漂移留痕 `denominators.supply_drift_raw`（可选字段，
   v2 schema 兼容）。✅
2. **codex 汇报与代码一致性核查**：其"仅在 PASS/exit 0 放行"声明与 diff 表面不符
   的疑点核实为**既有代码**（:235 早于本批存在）——非虚报。✅
3. **波及面核查**（done 报告逐处行号）：supply_truth_gate 生产者无方向假设、
   shared_release_receipt 深验（批 10 已关）无 net≤onchain 假设、发布闸 sha 比对
   与 distribution 快照来源无关——全库无第五个静态假设点。✅
4. **契约**：不新增编号的论证成立（v2 向后兼容可选留痕，无新 schema 面；
   CT-DISTRIBUTION-01 既有锚不变）。✅
5. **测试**：R1 红=ARC 同形数值被旧闸拒（真实红证据）；G1/N1-N4 绿（N2 用
   10^30+1 与边界外 1 raw 证明整数判定）；静态回归 test_distribution_gate 修前后
   逐项 PASS。**Fable 本机 run_all 136/136 全绿 EXIT=0**（codex 沙箱 2 项 loopback
   纯环境）。✅
6. **禁改面**：生产者/runner/深验/handoff/版本登记面/密钥/ARC 案根零触碰。✅

## 后续

commit v6.52.11 → ARC 第 8 项重跑（distribution initial）→ data_map 终验 →
handoff generate → verify READY 即停 → 销账。
