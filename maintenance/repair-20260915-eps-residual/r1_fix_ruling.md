# 盲审 r1 三条发现的处置裁决(Fable 验收方,2026-09-15)

来源:`blind_review_r1.md`(codex 只读盲审,结论 FAIL:F1 blocker / F2 minor / F3 nit)。三条 Fable 均已用其 R1 命令只读复现,全部成立。

## F1(blocker)— 处置:修正承诺与测试,**不改生产代码**
事实:`X→A 2^60, X→A 1, A→D 2^60`(供应 10·2^90)下,7.0.3 把两笔缺口累进同一 float 桶,`float(2^60)+1.0 == 2^60`,int 后 Σ=2^60;7.0.4 分进 data_gap(2^60)与 fp_residual(1)两桶,int 后 Σ=2^60+1。整数真值就是 2^60+1,7.0.4 更接近真值;差异来自 7.0.3 单桶的浮点合并吞位,量级恒 ≤ 该锚点 fp_residual raw(因为只有 ≤gap_eps 的短缺才会被分到第二桶)。APU 210 锚点 + PYTHIA 14 锚点实测差 0。
裁决:
1. plan 里"数量一个单位都不变"改为准确表述:**每笔短缺数量原样保留**;锚点合计在两类缺口共存时可与 7.0.3 相差浮点合并舍入量级,**上界 = 该锚点 fp_residual raw**,方向为 7.0.4 ≥ 7.0.3(更接近整数真值);两案实测差 0。此表述写入 CHANGELOG 7.0.4 段、scan-schemas §4、done.md。
2. T4 不变量改为:`stock_raw` 相同;除 data_gap/fp_residual 外每条构成 raw 相同;`0 ≤ [data_gap(704)+fp_residual(704)] − data_gap(703) ≤ fp_residual(704)`。既有 T4 两组样例断言仍须通过(它们差 0)。
3. 新增 T4-mixed 测试:上述三笔构造,断言三策略 stock_raw 两版 = 2^60;7.0.4 合计 = 2^60+1(整数精确值);差 = 1 ≤ fp_residual raw;闭合 pct 两版均 100.0。对照方式沿用既有 T4 的 7.0.3 对照机制。
4. apu_regression.md / pythia_regression.md 补一行:合计差按新不变量复核,224 锚点差 0。
理由:另一路线(让 fp_residual 也回流同一 float 桶再拆)要引入负数或展示不一致的补丁,违背最小改动,且保住的是错误的舍入。本裁决偏离了已批准 plan 的字面承诺,须在汇报时向用户置顶说明,由用户追认或退回。

## F2(minor)— 处置:缩小措辞范围
CHANGELOG 7.0.4 消费面与 done.md 中"含 data_gap 的锚点旧收据必失配"改为:**三策略 policy_details 实际变化的锚点**其翻转指纹变化、旧裁决收据失配(APU 实测 118/210,全部含旧 data_gap);小供应量(gap_eps==EPS)下真实 data_gap 的锚点明细不变、收据仍匹配;旧账本整体复验另因算法文件哈希漂移被拒,与收据是否匹配无关。

## F3(nit)— 处置:更新结果 JSON
`run_all_fable_result.json` 改为反映实际:status=PASS、pass=147、fail=0、log=run_all_fable.log(或明确标注 historical 并追加 final 记录)。

## 不做
不改 `entity_source_trace.py`;不改 handoff_manifest.py、受保护测试、fixture;不重跑 APU/PYTHIA;全套 run_all 由 Fable 本机复跑落盘。
