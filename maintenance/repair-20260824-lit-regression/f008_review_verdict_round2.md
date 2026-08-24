# F-008 盲审 verdict（round 2，codex fresh 只读，2026-08-24）

VERDICT: BLOCK（残余一项）

已闭合：①字符闸改 unicodedata.category=="Cc" 覆盖 C0+DEL+C1，U+0085 反例＋前置拒绝 helper（handoff_manifest.py:701-708；test:153-178,249-256）；②producer 守卫盘点全部三个 glob.glob（一 sol＋两 evm），字符串拼接第三 glob 自测会红（test:343-385,464-479）；③绿证重建 42/42＋四组定向回归 EXIT_CODE=0；round1 原文未改写。round1 已通过项无回退；九个禁改文件相对 333144e diff 全空。

残余阻断：wave 守卫非真 fail-closed——只认顶层 ast.Assign 定义＋ctx=Load 消费（test:411-422,438-451），注入 `logs += "/unexpected"`（AugAssign）既不算重复定义也不进消费统计，盲审员内存 AST 变体实证 guard_wave_globs() 输出 GUARD_ACCEPTED_MUTATED_WAVE EXIT=0；done round2 "任一漂移都会硬失败"（f008_done.md:152-164）仍过度声明。

最小返工清单（原文）：
1. guard_wave_globs() 盘点 logs/blocks 的全部绑定、写入和读取节点；每变量只允许一次冻结形状的直接 Assign，拒绝 AugAssign/NamedExpr/额外或嵌套赋值/删除及其他未白名单消费。
2. 增加 wave 自测反例：至少注入 logs += "/unexpected" 证守卫必红；建议同时覆盖 blocks 重绑定或别名消费。
3. 重跑 F-008 全测试及四组定向回归重建绿证；再次修正 f008_done.md:152-164。生产代码无需改动。
