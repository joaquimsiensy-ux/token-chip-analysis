# 登记不修台账 —— repair-20260918-p0-f04-f07（调度方维护）

| 编号 | 段 | 内容 | 处置 |
|---|---|---|---|
| P1 | F06 | consumer 只按 tier=exclude 重推 INFRA（与 producer 对称），不按 category 推导 | 不扩 |
| P2 | F04 | 空 series（lines_checked==0）仍放行 | split-run.md:183 用户 08-18 接受残余 |
| P3 | F04 | 发布闸局部 import figures_from_facts 连带 matplotlib | 一次性成本；拆分属另单 |
| P4 | F04 | stage2_closeout 强检查未成必经 | 7.1.0 遗留清单 |
| P5 | F07 | 全套字段齐全（含正确 producer sha、随案 channels）的手写 followup 仍可过 | 闭合需闸侧按 channels 重放，另单 |
| P6 | F07 | channels 文件内容不验 | 采集侧 channels_preflight 负责 |
| P7 | F07 | 峰值口径无冻结 manifest（不用 peaks_daily 的案可不带四件） | 与现行契约一致 |
| P8 | F05 | **待用户裁决**：峰值上界用当前总供应一刀切，历史供应更大（大额销毁后）的币会误拒；正解按 peak_date 时点供应核上界，需供应历史序列 | 另单 |
| P9 | F05 | override 证据只核值一致，不复算峰值 | 块级复算属 A4 重放 |
| P10 | F05 | peak_date 无下界 | 无稳定来源 |
| P11 | F05 | decimals 只在发布闸核，derive_facts/stage2 收口不核 | 发布必经 |
| P12 | 全局 | F01/F02/F03（仅 independent-audit 净室轨）缓修排 P1；F08 不修（脚本产出无空格图路径） | 用户 09-18 裁决 |
