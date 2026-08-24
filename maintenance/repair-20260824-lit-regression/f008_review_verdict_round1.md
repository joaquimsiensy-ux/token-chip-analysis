# F-008 盲审 verdict（round 1，codex fresh 只读，2026-08-24）

VERDICT: BLOCK

阻断缺陷两项：
1. 字符闸不完整：实现只拒 ord<32 与 DEL 127（handoff_manifest.py:702），未拒 U+0080–U+009F C1 控制字符；工单要求"控制字符"、done 声称"全部控制字符"（f008_done.md:41）名不副实；测试只有 \x01 反例（test_lit_regression_f008.py:241）。
2. AST 同源守卫非 fail-closed：join_shape() 对不认识的构造返回 None 静默忽略（test_lit_regression_f008.py:310,347）；如新增 glob.glob(a.edges_evm_v2 + "/run_*/extra.parquet") 字符串拼接写法，trace_shapes 仍为两个、测试仍绿——违反工单"不存在第三个 evm glob、结构改写即 fail-closed"（f008_workorder.md:49）；wave 侧亦未盘点全部 glob.glob 调用。done "fail-closed AST 同源守卫"（f008_done.md:49）过度声明。

其余五节通过：主控制流正确（字符闸→safe_case_dir→scandir 两层枚举拒 symlink→结构校验重复拒→双向差集有界报错→才 mkstemp/subprocess；sol/duckdb 逐字不动）；safe_case_dir 独立实现、safe_case_file 函数体 SHA 与 HEAD 一致；hunk 全部有归属；归因"7b99867 收口新引入"成立（旧版 normpath 实证）；红绿证据静态自洽（红证 0/1 修前拒、绿证 40/40＋四组定向回归 EXIT_CODE=0、拒绝分支 helper 同时监控 mkstemp/subprocess/临时文件集合）；九个禁改文件 diff 全空。

最小返工清单（原文）：
1. 字符闸改为拒绝完整 Unicode Cc 类控制字符，并新增至少一个 C1 反例（如 U+0085）；继续断言拒绝发生在 tempfile/subprocess 前。
2. AST 守卫盘点目标函数内全部 glob.glob 调用；除冻结允许形状外，任何额外或无法解析的 glob 构造都必须失败。producer 精确允许一个 sol glob＋两个 evm glob；wave 同时锁定两个 pattern 定义及其全部 glob 消费。
3. 重跑 F-008 测试和四组定向回归，更新绿证；修正 done 中"全部控制字符"和"fail-closed"的证据描述后再送审。
