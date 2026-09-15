# 盲审 r2 blocker 的处置裁决(Fable 验收方,2026-09-15,替代 r1_fix_ruling.md 中 F1 的数量承诺)

来源:`blind_review_r2.md` 唯一 blocker。Fable 已用其 R1 命令只读复现:`X→A 2^60, X→A 129, A→D 2^60`(供应 10·2^90)下 pro_rata 主策略 Δ = gap704+residual704−gap703 = **−128**,r1 裁决的"0 ≤ Δ ≤ residual704"与"7.0.4 ≥ 7.0.3、更接近整数真值"两句均被推翻。机理:float 合并既可吞位也可向上舍入(129 → +256);分桶后按比例扣减是**逐键舍入**,合计可增可减。两版都是浮点近似,**不存在哪一版更真**。

## 新承诺范围(写入 CHANGELOG 7.0.4 段、scan-schemas §4、done.md,替换 r1 措辞)
精确不变(逐字相同):①每笔短缺入桶数量;②`stock_raw`;③除 data_gap/fp_residual 外每条构成 raw;④闭合 pct(展示精度)。
浮点舍入量级差异(可正可负,不承诺方向):UNRESOLVED 合计(gap704+residual704)与 gap703 之差 Δ 满足经典前向误差界
  **|Δ| ≤ 4 · n · 2^-52 · S + 2**,n = 该实体模拟消费的边数(测试里用边表总数),S = total_supply raw。
含义:差值相对总供应量不超过 n×8.9e-16,任何真实案下都远低于闭合门禁 0.5%(需 n>5e12 才可能触及);APU 210 + PYTHIA 14 锚点实测 Δ 全为 0。

## 测试改动(scripts/tests/test_entity_source_trace.py)
1. T4 通用不变量:非负下界与 residual 上界**删除**,改为上式的 |Δ| 界;①②③④精确断言保留。既有两组样例、T4-mixed(第二笔 1)仍须通过。
2. 新增 T4-mixed-b:第二笔 129,断言 pro_rata Δ = −128、fifo Δ = 0、lifo Δ = +1(以复现值为准,施工时实跑核对),stock_raw 两版 = 2^60,闭合 100.0,|Δ| 在界内。
3. 新增 T4-stress:固定种子 ≥200 组随机混合短缺序列(每组 3–8 笔;大短缺 2^50…2^62、小短缺 1…4096;供应 10·2^90;三策略),对每组断言①②③④精确 + |Δ| 界;把实测 max|Δ| 与出现次数写进测试输出与 done.md。若任一组违反界 → 测试失败,施工 BLOCKED 并报告,不得放宽常数。

## 文档改动
- CHANGELOG 7.0.4 "设计与实现"、scan-schemas §4、done.md:删除"7.0.4 ≥ 7.0.3 / 更接近整数真值 / 上界 = fp_residual raw",改为上面的"精确不变四项 + 舍入量级差异一界"表述,并注明可正可负。
- 生产文件 `entity_source_trace.py` **仍不动**(docstring 的"数量不变"按"逐笔短缺数量"理解,由 CHANGELOG 注明;docstring 措辞留待下一版本修正,记入"已知未修")。
- apu_regression.md / pythia_regression.md:把"新不变量"改称本裁决的界并复核 224 锚点(只读复算,不重跑)。

## 不做
不改生产代码、handoff_manifest.py、受保护测试、fixture;不重跑 APU/PYTHIA;全套 run_all 由 Fable 本机复跑落盘。
