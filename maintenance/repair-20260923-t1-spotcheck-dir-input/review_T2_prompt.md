# 工单 T2 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260923-t1-spotcheck-dir-input/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/不修改任何文件。报告全文打印到 stdout，首行固定：`# 工单T2复核：通过` 或 `# 工单T2复核：退回`。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（`d2d6641`，含 9.0.3 与收官 review r1 存档）。

## 任务
复核 `maintenance/repair-20260923-t1-spotcheck-dir-input/workorder_T2.md`（v1），它处置你上一轮收官 review（`final_review_T1_reply_r1.md`）的 FR-01 与 FR-03。逐条审：
a) **锚与行号**：工单每个 `:N` 锚按整行 `grep -n -F -x` 恰 1 处且行号一致（`producer_history.py:241-243`、`shared_release_receipt.py:1221`、`:1459-1460`、`test_recon_deep_reverify.py:593/:601`、`references/data-pipeline-evm-recon.md:152`、`CHANGELOG.md:13/:100`、`SKILL.md:23`、`pyproject.toml:15`）。
b) **来源断言亲核**：①旧哈希 `87bbad22…` 是否真由 `git show b52cbedf230218e5da46334cf99b7111235e8367:scripts/lib/time_spotcheck.py | shasum -a 256` 复现；②`historical_producer_hashes` 的过滤语义（script+protocol+ACTIVE、REVOKED 全局优先）与 `test_producer_registry_current.py` 对新条目的自动核验（六键、40 位 commit、git show 复现）——工单登记条目是否一次通过；③`validate_receipt`（`receipt_validate.py:81-`）与 `repo_ref_ok`（`shared_release_receipt.py:122-135`）在传入历史集后的实际准入语义是否如工单 §2.2 说明；④wrapper 层 `:1448-1461` 的执行顺序（`:1459` 先于 `:1461` 的 envelope 层）是否使两层缺一不可——若只接一层，OPN 类案在 `handoff_manifest verify` 会在哪一层被拒。
c) **修法定形与精确性**：§1.2 把 `script` 取自 ref 自身 `producer.path` 并限定 `in RECON_PRODUCERS["evm"]["time"]`、protocol 固定字面量 `"time-spotcheck/v3"`——对比先例 `:1007-1019`（anchor_plan 用固定 script 名、protocol 取自 plan schema），哪种更精确、有无更短等价；是否存在任何放宽（对其他 key、solana 家族、kind=directory 收据、默认路径）；两处重复的 6 行条件块是否值得抽私有函数（工单 §1.5 禁新增函数——请评估这个禁令在此处是否合理，若你认为抽一个私有函数更好，给出替换文本）。
d) **回归面**：是否还有第三个消费点核 time 生产者哈希（grep `scripts/report`、`scripts/lib` 中对 `time_spotcheck.json`/`checks["time"]`/`RECON_PRODUCERS` 的引用；`audit_release_gate.py`、`handoff_manifest.py` AUTO_GATES 重读、`migrate_legacy_case.py`、stage2/stage3 消费面）；`invariant_manifest`/`contract_manifest` 是否需登记；`invariant_scan.py` 对 `receipt_consumers` 计数是否会因改动变化。
e) **测试**：§2.3 六个向量是否足够且最小；H16 wrapper 真实路径向量——请实际查 `scripts/tests` 是否已有可复用的 EVM 四查 wrapper 夹具（`test_handoff_manifest.py`、`test_repair_batch_d.py`、`test_batch11_frozen_bundle_binding.py` 等调用 `validate_reconciliation_report` 处），给出"能否 ≤30 行搭出"的结论；若有更合适的落点（文件/函数）给出。
f) **FR-03 处置**：工单认定 runner `inputs` 可选、`data_map` 由案内脚本 rglob 叶子、故只改 `references:152` 一行（+1 B）——请核 `reconciliation_report.py` 的 `inputs` 是否确为可选（`_validate_spec`/`snapshot_inputs` 对缺省的处理），以及 skill 文档中是否还有第二处 `--input` 用法说明；替换文 `<同plan的merged文件或data/v2目录>` 是否准确（目录必须是生成 plan 时同一目录），有无等长或更短写法。
g) **原则与档位**：上下文不增（references +1 B、SKILL 0 B、commands 0 B）；CHANGELOG 索引行长度与既有条目量级；版本档位 9.0.4（修）是否恰当（登记历史哈希＝恢复既有契约的兼容性，不改 schema）。
h) 是否越界；工单是否遗漏 FR-01 的任何子项（reviewer 原话："仅添加 producer_history 条目不够"）。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文，含行号）＋ 汇总表。
