# 批 13 Fable 验收记录（2026-08-27）

裁决依据：延续用户方案 A。ARC handoff verify 实跑暴露同族第五消费点
（会计核定收据产在封账点 vs verify 拿观测时点当期望）。

## 验收项与结论

1. **diff 审查**：中央两态选择器 `accounting_expected_target`（EVM→wrapper；
   Solana 要求 exact 收据在场、chain/token 全等、exact≤wrapper，严格早于才投影
   冻结点）；handoff verify 与 validate_sources（−3 shared 路径）同深接入；
   validate_sources EVM 分支原路径逐字保留、Solana 静态分支保留原
   wrapper==accounting 等式与原报错文案；audit_release_gate 块声明去重的冻结点
   投影以**深验成功**为前提（异常回落原判＝更严方向的 fail-closed）。✅
2. **A4 seal 绑定时点核查**：validate_adversarial_review 改传 accounting target
   ——冻结态=封账点（A4 工作对象是冻结账本，语义正确）；静态与 EVM 两者相等
   零变化。✅
3. **调用点全量核查**：4 处生产面逐处行号结论在 done 报告；下游同型静态假设
   （audit 块声明、shared validate_sources）一并修复=关到同一深度。✅
4. **测试**：R1 红（ARC 同形三时点夹具被旧闸拒）真实留证；G1/N1/N2 绿；
   静态回归（纵切片全链）零变化；**Fable 本机 run_all 137/137 全绿 EXIT=0**
   （codex 沙箱 2 项 loopback 纯环境）。✅
5. **禁改面**：validate_accounting_receipt 本体校验逻辑未放宽（只改调用方期望
   时点取向）；生产者/runner/replay_edges/批 10-12 已改面/版本登记面/密钥/
   ARC 案根零触碰。✅

## 后续

commit v6.52.12 → 重发 ARC handoff 运行器（generate+verify）→ 预期 READY 即停。
