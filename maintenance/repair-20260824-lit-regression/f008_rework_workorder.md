# 工单 F-008 返工（round 2）：字符闸补 C1＋AST 守卫 fail-closed（fresh 会话可独立执行）

一句话目标：消化盲审 round1 两项 BLOCK（verdict 全文=本目录 f008_review_verdict_round1.md），按最小清单三条返工。

## 【开工门禁】
- 仓库：/Users/uravvv/.claude/skills/token-chip-analysis；分支 `fix/lit-regression-v6522`
- `git status --short` 应可见 F-008 round1 未提交改动（case_paths.py / handoff_manifest.py 修改＋test_lit_regression_f008.py 新增）——在其上继续，不还原

## 施工（盲审最小清单三条，逐条闭合）
1. **字符闸补全**：handoff_manifest.py 的 argument 字符闸改为拒绝完整 Unicode `Cc` 类控制字符（用 unicodedata.category(ch)=="Cc" 或等价判定，天然覆盖 C0+DEL+C1），glob 元字符/单引号/反斜杠拒绝保持；测试新增至少一个 C1 反例（如 U+0085），断言拒绝发生在 tempfile/subprocess 之前。
2. **AST 守卫 fail-closed**：重写同源守护测试——对 entity_source_trace.source_binding 与 wave_scan.load_evm_v2 两个目标函数，盘点函数体内**全部** glob.glob 调用（含任何写法）；每个调用的参数构造必须能被解析器识别且落在冻结允许形状集内（producer=恰好一个 sol glob＋两个 evm glob；wave=恰好两个 evm glob 定义及其全部消费点），出现额外调用、无法解析的构造、形状偏离任一情况即 FAIL（fail-closed）；对"字符串拼接第三 glob"写法造一个自测反例验证守卫会红（可在测试内部用样例源码字符串验证解析器，不改生产文件）。
3. **绿证重建＋done 修正**：重跑 F-008 全部测试＋四组定向回归（test_handoff_manifest.py、test_repair_g1_handoff_containment.py、test_evm_observation_release.py、test_audit_release_gate.py），原始输出覆盖写 f008_green_evidence.txt（红证不动）；f008_done.md 增补 round2 节（不改写 round1 原文）：修正"全部控制字符""fail-closed"两处过度声明为与实现一致的准确表述，附前后对照与行号。

## 边界
- 白名单：scripts/report/handoff_manifest.py、scripts/tests/test_lit_regression_f008.py、本工程档案目录。
- **本轮禁改**：scripts/lib/case_paths.py（round1 已定型）；原工单九个禁改文件照旧（wave_scan.py/entity_source_trace.py/sqd_cache_identity.py/replay_pass2.py/replay_duck.py/replay_edges.py/camp_series_provenance.py/state_from_facts.py/build_evolution.py）。
- 不 commit、不联网；工单外发现只记录。
