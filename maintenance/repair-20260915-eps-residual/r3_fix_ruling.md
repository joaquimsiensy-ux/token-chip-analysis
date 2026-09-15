# 盲审 r3 blocker 的处置裁决(Fable 验收方,2026-09-15,替代 r2_fix_ruling.md 的"四项精确不变")

来源:`blind_review_r3.md` 唯一 blocker(codex 盲审连续第三次 FAIL;按用户纪律,本轮修复后的盲审改由 opus 执行,施工仍 codex)。
反例 A:`X→A H, Z→A H, X→A 257, A→D H`(H=2^60,S=10·2^90)→ D 的 **mint raw** 7.0.3=576460752303423488、7.0.4=576460752303423360(−128);反例 B:第四笔改 `A→D 2H+512` → pro_rata 逐笔短缺 7.0.3=512、7.0.4=0。机理:拆桶改变 float 求和次序 → 可用余额与比例扣减系数的舍入都变 → **所有键**(含 mint 等非 UNRESOLVED 键)与逐笔短缺都会有 ulp 级扰动。结论:在 float 之上"改标签"不可能对任何逐键数量做精确承诺;唯一严格精确的是整数边表算出的 `stock_raw`。

## 最终承诺范围(写入 CHANGELOG 7.0.4 段、scan-schemas §4、done.md,替换 r2 的"四项精确")
- **精确不变(唯一)**:`stock_raw`(整数路径,与策略无关)。
- **舍入量级扰动(可正可负,不承诺方向)**:以下每一项与 7.0.3 之差 Δ 满足 |Δ| ≤ B,B = 4·n·2^-52·S + 2(n=模拟消费边数,S=total_supply raw):①每条构成 raw(含 mint 等非 UNRESOLVED 键);②UNRESOLVED 合计(gap704+residual704 对 gap703);③构成 Σraw;④逐笔短缺量。闭合 pct 差 ≤ B/stock_raw×100,展示值在舍入边界上可能不同,**不承诺展示值相同**。
- 事件计数(data_gap_events/fp_residual_events)、三策略 policy_details、翻转指纹:均可能因舍入扰动而变,不承诺不变;F2 的"实际变化的锚点收据失配"表述照旧(它是对实测的陈述)。
- 量级说明:B/S = n×8.9e-16;真实案(APU n≤5.8e5、PYTHIA n≤4.9e6)下 B/S ≤ 4.3e-9,远低于闭合门禁 0.5%;两案 224 锚点实测所有键 Δ=0。合成对抗样例实测 |Δ| 最大数百 raw(≈1e-25 S)。

## 测试改动(scripts/tests/test_entity_source_trace.py)
1. T4 通用比较器:精确断言只保留 `stock_raw`;①②③④改为 |Δ| ≤ B 逐项断言;闭合 pct 断言改为 |pct 差| ≤ B/stock×100(允许展示值不同)。既有具体断言(两组旧样例、T4-mixed、T4-mixed-b 的具体 Δ 值)保留。
2. 新增 T4-mixed-c(反例 A)与 T4-mixed-d(反例 B):断言以施工实跑为准并记录两版 mint raw / 逐笔短缺值;须在 B 界内;stock_raw 两版相同。
3. T4-stress 生成器扩展:mint 与外部转入可落到**中间账户**(参与混合扣减),转出可超余额制造真实短缺;组数 ≥300,固定种子;逐组断言 stock_raw 精确 + ①②③④与 pct 的界;输出 max|Δ|(分键类:UNRESOLVED 合计 / 非 UNRESOLVED 键 / 逐笔短缺)与超界次数。任一超界 → 失败,BLOCKED 汇报,不放宽常数。

## 文档改动
CHANGELOG 7.0.4 "设计与实现"、scan-schemas §4、done.md:删除"四项精确不变",改为上面"唯一精确 + 四项界 + pct 界 + 计数/明细/指纹不承诺"表述;明确写一句"改标签在 float 之上会对全部构成产生 ulp 级扰动,7.0.3 与 7.0.4 都是浮点近似,无优劣"。apu/pythia 回归文件按新范围复核 224 锚点全部键(只读复算)。生产文件仍不动(SHA-256 须仍为 e85acee4…)。

## 不做
不改生产代码、handoff_manifest.py、受保护测试、fixture;不重跑 APU/PYTHIA;全套 run_all 由 Fable 本机复跑落盘。

## 勘误(Fable,r4 BLOCKED 后补,2026-09-15)
①"每条构成 raw"的键对齐口径明确为:**非 UNRESOLVED 键逐键比较**;`UNRESOLVED/data_gap` 与 `UNRESOLVED/fp_residual` **合桶后作为一个量比较**(即 ②),不做原始标签逐键比较——标签从 data_gap 迁到 fp_residual 是本版目的,原始逐键差不是承诺项,也不写成"差全为 0"。r4 已实测的"原始标签逐键 684 次超界"如实保留在 done.md 作为"标签迁移量"的记录,不算失败。据此把 T4 比较器与 T4-stress 的原始逐键判界改为记录不判界,其余判界不变;终态按其余全部 0 超界判定。
