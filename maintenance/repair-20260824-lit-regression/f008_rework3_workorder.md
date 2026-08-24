# 工单 F-008 返工（round 4）：wave 守卫映射与槽位签名精确化（fresh 会话可独立执行）

一句话目标：消化盲审 round3 两个残余精度缺口（verdict=本目录 f008_review_verdict_round3.md），按最小清单四条返工。仅动 scripts/tests/test_lit_regression_f008.py 与档案文书，生产代码零改动。

## 【开工门禁】
仓库 /Users/uravvv/.claude/skills/token-chip-analysis；分支 fix/lit-regression-v6522；在现有未提交改动之上继续。

## 施工（四条）
1. guard_wave_globs() 定义校验改按变量名精确映射：logs 的唯一 Assign 必须是 os.path.join(dir_,"run_*","logs.parquet")、blocks 必须是 os.path.join(dir_,"run_*","blocks.parquet")——不允许用无身份的 set(shapes) 比较。
2. 消费校验为每个 logs/blocks 读取节点建立精确签名（变量名＋所属语句/调用类型＋槽位，如"glob.glob 第一实参=logs"、"read_parquet SQL f-string 槽位 N=logs"），冻结签名全集精确比对；禁止按数量验收。
3. 新增两个内存 AST 自测反例："交换 logs/blocks 文件名映射"必红、"交换 logs 与 blocks 的 SQL 消费槽位"必红（验证方式同现有注入自测，不改生产文件）。
4. 重跑 F-008 全部测试＋四组定向回归（test_handoff_manifest.py、test_repair_g1_handoff_containment.py、test_evm_observation_release.py、test_audit_release_gate.py），覆盖重建 f008_green_evidence.txt（红证不动）；f008_done.md 仅追加 round4 节，修正 round3 :181/:200 两处过度声明（不改写既有各 round 原文）。

## 边界
白名单：scripts/tests/test_lit_regression_f008.py＋本工程档案目录；**其余一切文件禁改**。不 commit、不联网。
