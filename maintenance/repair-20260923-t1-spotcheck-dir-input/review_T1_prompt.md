# 工单 T1 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260923-t1-spotcheck-dir-input/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/不修改任何文件。报告全文打印到 stdout，首行固定：`# 工单T1复核：通过` 或 `# 工单T1复核：退回`。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（含 f4f80567c21f）。

## 任务
复核 `maintenance/repair-20260923-t1-spotcheck-dir-input/workorder_T1.md`（v1），逐条审：
a) **锚与行号**：工单每个 `:N` 锚按整行 `grep -n -F` 恰 1 处（工单已注明不唯一者除外）且行号一致；`bound_case_ref`（`shared_release_receipt.py:347-377`）、`receipt_kernel._resolved_input`（`:53-78`）、`anchor_plan.py:194-203`、`anchor_selection.input_identity/_detect_input` 目录分支的事实是否如工单所述。
b) **专门核每条"来源/事实"断言**：①`handoff_manifest.py:349`（generate READY）与 `:483`（verify）是否真的调 `validate_reconciliation_report` → `_validate_time_receipt` → `_validated_time_plan_authority`，即"只修生产者、−1 交接仍被拒"是否成立；②`plan["input_manifest"]["path"]` 是否恒为绝对路径（`receipt_kernel._file_ref` 无 input_base 分支）；③`validate_semantic_replay`（`time_spotcheck.py:180-210`）是否对目录输入真的重算 `input_identity` 并与 `plan.input.sha256` 比对（这是 §1.2 信任链的前提）；④`_detect_input` 目录分支所需列名与 §2.3 合成 parquet 列是否一致；`blocks.timestamp` 整数秒是否被 `make_timestamp(ts*1000000)` 正确解析；⑤`anchor_plan.py` 对 §2.3 合成目录（24 行、单 run）是否会因最小覆盖参数（per_cell/edge_max/min coverage）拒收——请实际读 `anchor_selection.generate_anchor_selection` 的覆盖判定给出结论。
c) **修法定形**：§2.1 `bound_input_ref` 放在生产者、§2.2 消费者分支——有无更短/更少新增的等价改法（例如是否可让 `_validated_time_plan_authority` 对目录身份直接复用清单绑定而不读清单正文；是否存在把目录身份哈希重算搬进消费者的诱惑，工单 §1.2 明确禁止，请评估其安全性权衡）；文件输入路径是否真的"逐字节不变"（含错误先后顺序变化是否会让既有测试 needle 失配——请 grep `scripts/tests` 里对 `time plan input identity`/`time plan input manifest`/`signed input identity` 的断言）；§2.2 `Path.is_relative_to` 与 `directory.resolve()` 在 symlink 案根（macOS `/var`→`/private/var`）下是否会误拒（对照 `bound_case_ref` 的处理方式）。
d) **回归面**：是否遗漏其他把"输入必须是文件"写死的消费点（grep `time merged input`、`inputs.get("input")`、`"input"]` 于 `scripts/report`、`scripts/lib`；`handoff_manifest`/`audit_release_gate`/`stage2_*`/`new_analysis_gate` 对时间收据 `inputs.input` 的任何额外要求；`data_map`/`freeze` 是否要求时间收据输入进 manifest）；`invariant_manifest.json` 是否需要因新公开函数登记（`invariant_scan.py` 规则）；`producer_history` 是否需登记 time_spotcheck（工单认定不需要，请核 `PRODUCER_HISTORY` 与 `test_producer_registry_current.py`）。
e) **原则**：skill 上下文不增、能删不增、能改不增——§2.4 +21 B 有无更短等价（含 0 B 改法）；§2.5 CHANGELOG 索引行长度是否与既有条目量级相当；测试是否可更短（如复用 `_produce_plan` 结构）。
f) 是否越界修了范围外问题；版本档位 9.0.3（修）是否恰当（收据 schema/键不变、消费者对目录身份新增放行分支是否构成"契约扩展"应记次版本——给出你的判断与理由）。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文，含行号）＋ 汇总表。
