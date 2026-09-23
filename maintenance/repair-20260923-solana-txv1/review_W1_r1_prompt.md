# 只读复核任务：工单 W1 v1（Solana 交易版本常量化 + 修复产物前代认领）

纪律：本任务**只读**，不改任何文件、不 commit；禁读 `~/.codex` 下文件（启动自动披露除外）。仓库为 `fix/solana-txv1` 分支的克隆，不涉及 main。

请通读 `maintenance/repair-20260923-solana-txv1/workorder_W1_v1.md`，对照代码实况逐条复核，然后把报告**全文打印到 stdout**（首行 `# 复核 W1 r1: 通过 / 退回`），不必写文件。

复核要点（每条给出「通过 / 退回：理由 + 修订建议」，引用文件:行号并附锚文本）：
1. **锚点与断言实证**：工单里每个行号、每个「已导入/已存在」断言、17 处字面量清单，用 `grep -n`/`nl -ba` 亲核；不符处列出。
2. **认领机制的安全性**：§2.3 五步校验能否被伪造绕过？（如：伪造旧 pending header、篡改采纳行、跨案/跨 mint/跨 base 认领、重复认领、把不同参考源指纹的证据混入。）指出缺口并给最小补法。特别核 `compute_plan_digest` 物料（`scripts/solana/sqd_repair_core.py:59-82`）是否足以保证「除 producer 外 plan 完全一致 ⇒ 同 base/coverage/候选/参考源」。
3. **版本等价断言**：「低版本参数下成功返回的区块，响应字节与高版本参数下相同」——按 Solana RPC 语义是否成立？若不成立或有边界（如 legacy/v0/v1 的 `version` 字段回显差异），指出对 §2.3 第 3 条接受集合设计的影响。
4. **下游消费者**：改动后是否还有别的校验点会拒绝含 `adopted` header 或含版本 0/1 混合 params_digest 的台账/bundle？（查 `solana_exact_validate.py` 全部读取 rpc_ledger 的地方、`sqd_cache_identity.py`、`replay_edges.py`、`test_batch7/8`、任何 header 键集断言。）漏了的列出。
5. **最小化原则**：用户原则「能删不加、能改不加、references/SKILL.md 上下文尽量不增」。工单哪些地方可以再省（如守卫测试是否必要、常量落点、文档改动幅度）？哪些地方省过头会留隐患？
6. **测试可行性**：§4 E27(d) 向量在现有夹具（`test_sqd_gap_repair.py` 的 `build_batch3b_case`/`write_repair_fixture`/E27(a) 手法，`test_batch8_repair_scale.py` 的 `direct_stream`）下能否在 ≤ 120 行内实现？取 plan 对象的可行路径是什么（指出具体函数）？给出更省的等价手法（若有）。
7. **版本号**：9.1.0（次版本）是否符合 `references/retrospective.md:137-141` 的两维规则？
8. **回归面**：列出改动可能波及的其他测试文件（按 import 关系与 `run_all.py` 套件），以及工单 0.7 定向清单有无遗漏。

输出：先总判定，再按 1–8 逐条，最后一段「建议的工单 v2 修订清单」（逐条、可直接改进工单）。
