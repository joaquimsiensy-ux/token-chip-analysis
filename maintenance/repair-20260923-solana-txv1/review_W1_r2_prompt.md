# 只读复核任务 r2：工单 W1 v2

纪律：**只读**，不改文件、不 commit；禁读 `~/.codex`（启动自动披露除外）、`~/Documents`、`~/Desktop`。分支 `fix/solana-txv1` 克隆。

材料：`maintenance/repair-20260923-solana-txv1/workorder_W1_v2.md`（施工工单）、同目录 `review_W1_r1_report.md`（你上一轮 r1 的报告）、`workorder_W1_v1.md`（上一版）。

任务：核对 v2 是否**逐条正确吸收** r1 的 12 条修订清单，以及吸收后有无引入新问题。报告**全文打印到 stdout**，首行 `# 复核 W1 r2: 通过 / 退回`。

要点：
1. r1 修订清单 1–12 逐条：v2 对应段落是否落实？落实不到位处给出具体改法。
2. v2 新增的锚点与断言（`_plan :584`、`reference_endpoint_identity :101/:1607`、`_live_payloads` 的 plan 参数 `:962`、`_read_ledger_prefix :682-706` 落盘点 `:703`、`_publish_bytes_exclusive :204-210`、`test_batch8 :203-204`、validator `:1328-1331`、bundle 写出键 `:1341-1347`/`:1430-1452`）用 grep/nl 亲核。
3. §2.5 深验「重建摘要物料」：从 bundle/resolution 现有键能否**完整**得到 `compute_plan_digest` 的物料（base.edge_sha256/meta_sha256、coverage.probe_id/map_sha256、candidate_slots、mode、reference.kind/endpoint_fingerprint、producer.sha256）？逐项指出取自哪个文件哪个键（文件:行）；若某项取不到，给最小可行替代。validator 导入 `sqd_repair_core` 的层级可行性也核一下。
4. §2.3 第 5 步硬链接：在「发布后 evidence_manifest 深验重算文件哈希」前提下，硬链接相对复制是否引入**额外**风险？给结论。
5. §1.2 producer 换代触发器（`REPAIR_TX_VERSION` 常量+导入时断言）是否达成目的、有无更省写法。
6. §4 测试向量是否可在现有夹具下实现；是否有向量互相矛盾或不可构造。
7. 最小化原则：v2 是否有可再省之处、或省过头之处。
8. 结尾给「v3 修订清单」（若通过则写“无”）。
