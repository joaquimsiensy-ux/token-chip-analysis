# 工单C复核：退回

完整 a–k 复核报告已打印到 stdout。工单存在以下问题，不能直接施工：

1. **C-R01：stage2 build 顺序必然失败。**  
   工单 C4-a（:345–361）把 build 放在首次生成 `identity_gate.json` 之前。内存执行实得 `rc=2`，错误含“identity_gate.json 不在案根”。之后 `add_camp_series` 还会改写 identity 的绑定。  
   **修订：**将 build 放在 `add_distribution_initial`、`add_camp_series` 完成之后、A4 finalize 之前。证据：[夹具执行顺序](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_closeout.py:52)。

2. **C-R02：P11 所称在场性保证不成立。**  
   工单设计要点①、C2、§4：A5 重验调用的是 `validate_revision_chain`，没有调用检查 mandatory 文件的 `seal_integrity_errors`。标准 facts 缺失或为符号链接时，新 C2 会因 `regular_case_path` 返回 `None` 而跳过。另名 facts 的 figure2 收据检查实测可返回 `[]`。  
   **修订：**new-analysis 对标准 facts 缺失、非法路径明确 BLOCK；不能用当前理由接受 P11。证据：[A5 重验](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/a5_report_seal.py:360)。

3. **C-R03：空账仍能生成 formal facts。**  
   工单 §1.4、C1：现有三账函数遇空数组直接 `return`：
   `if not all(isinstance(x, list) and x for x in (members, positions, economics)):`  
   分别清空 membership、position 后，拟议 build 均实得 `rc=0`，新比对函数也返回 `[]`。  
   **修订：**derive 先验证三账结构及非空条目，补空账反例。此结果不代表完整发布闸也放行。证据：[提前返回](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:790)。

4. **C-R04：夹具调查错误，并漏掉 P105/batch B 回归。**  
   工单设计要点①、§0.3/0.8：batch15 调用 `build_solana_case(root)`，batch18 又复用 batch15，二者都带 facts。P105 及复用它的 batch B 则带无 provenance 的旧 facts，并要求发布闸零错误，新检查必使这些绿例失败。  
   **修订：**纠正清单，扩白名单并改造、回归 P105/batch B。“增加 REQUIRED 会让所列夹具整体变红”的论据不成立。证据：[batch15 建案](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch15_three_ledgers_frozen.py:267)、[P105 零错误断言](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_review_20260804_p105.py:263)。

5. **C-R05：遗漏 stage2 reseal 的绑定漂移。**  
   工单 C3/C4-a、§0.8：reseal 测试在 facts 建成后新增或改写 `provenance_ledger.json`，随后要求 `check_result` PASS。内存复现得到 provenance 绑定不一致。  
   **修订：**前置 ledger 建案条件，或按真实依赖顺序重建 facts、封印和旁车；补入该测试。证据：[add_reseal_prereqs](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_reseal.py:28)。

6. **C-R06：C4-b 插入点会拆开 Python 调用。**  
   工单 :405 要求插在测试 :1252 后，但该行是 `check("…",`，调用到 :1253 才闭合。按字面插入，`ast.parse` 实报 `SyntaxError`。  
   **修订：**改为完整调用之后，或明确独立 `with` 块。证据：[实际调用](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_d.py:1252)。

7. **C-R07：docs_lint 命令违反禁读纪律。**  
   工单 §0.2 与 §0.8 冲突：默认扫描包含 attic，`--all` 包含 archive，契约检查还递归读取仓库 Markdown。  
   **修订：**明确支持禁读排除的检查方式，并标为限域结果；回退默认命令不能解决。证据：[扫描范围](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/docs_lint.py:266)。

8. **C-R08：开工 HEAD 条件不符。**  
   工单 §0.1 要求 `8ead156`，实际前后均为 `559775b`；新增内容仅工单与提示词，白名单源码仍与指定基线一致。  
   **修订：**更新施工 HEAD，保留源码锚点基线。

已核验：明确锚点及行号；地址重放、封印和消费者调用链；五类手改均被新比对拦截；C4-c 内存断言为基线 **0/11**、拟改后 **11/11**；C5 登记增量符合预期，`minimum_counts` 无须上调；模板替换 **58→53 B**，references Markdown 合计 **930070→930065 B**，粗体、引用及对应契约针脚保持完整。

完整集成测试和 `run_all.py` 未执行，未将内存验证记为集成 GREEN。全程离线、零文件写入，收尾工作树为空。

Codex session ID: 01a0af72-171b-7221-ada7-e4c446057fc5
Resume in Codex: codex resume 01a0af72-171b-7221-ada7-e4c446057fc5
