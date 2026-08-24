# 工单 F-008 返工（round 3）：wave AST 守卫真 fail-closed（fresh 会话可独立执行）

一句话目标：消化盲审 round2 唯一残余 BLOCK（verdict=本目录 f008_review_verdict_round2.md），按最小清单三条返工。仅测试与文书，生产代码零改动。

## 【开工门禁】
仓库 /Users/uravvv/.claude/skills/token-chip-analysis；分支 fix/lit-regression-v6522；git status 应见 F-008 未提交改动，在其上继续。

## 施工（三条）
1. 重写 test_lit_regression_f008.py 的 guard_wave_globs()：对 wave_scan.load_evm_v2 函数体做全节点盘点——logs/blocks 两个名字的**一切**绑定（Assign/AugAssign/AnnAssign/NamedExpr/for-target/with-as/del 等）与**一切**读取消费逐一枚举；每变量恰好一次冻结形状的直接 Assign（os.path.join(dir_, "run_*", <常量文件名>)），其余任何绑定形式即 FAIL；读取消费只允许出现在白名单形状（glob.glob(logs)、read_parquet SQL f-string 等现有消费点逐一冻结），未白名单消费或无法解析节点即 FAIL（fail-closed）。
2. wave 自测反例：在测试内部用源码字符串变体（不改生产文件）至少验证 `logs += "/unexpected"` 注入后守卫必红；再加一个 blocks 重绑定或别名消费（如 b2 = blocks）变体证必红。
3. 重跑 F-008 全部测试＋四组定向回归（test_handoff_manifest.py、test_repair_g1_handoff_containment.py、test_evm_observation_release.py、test_audit_release_gate.py），覆盖重建 f008_green_evidence.txt（红证不动）；f008_done.md 增补 round3 节修正 :152-164 的过度声明（不改写 round1/round2 原文）。

## 边界
白名单：scripts/tests/test_lit_regression_f008.py＋本工程档案目录。**其余一切文件禁改**（含 handoff_manifest.py/case_paths.py——本轮生产代码零改动）。不 commit、不联网。
