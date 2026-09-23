# 只读复核任务 r3：工单 W1 v3

纪律：**只读**，不改文件、不 commit；禁读 `~/.codex`（启动自动披露除外）、`~/Documents`、`~/Desktop`。分支 `fix/solana-txv1` 克隆。

材料：`maintenance/repair-20260923-solana-txv1/workorder_W1_v3.md`（施工工单）、`review_W1_r2_report.md`（你上一轮 r2 报告，含 8 条 v3 修订清单）、`workorder_W1_v2.md`。

任务：核对 v3 是否逐条正确吸收 r2 的 8 条修订，以及有无引入新问题。**报告作为你的最终回复文本直接输出**（不要经命令打印），首行 `# 复核 W1 r3: 通过 / 退回`。

要点：
1. r2 修订清单 1–8 逐条：落实/未落实，未落实处给具体改法。
2. v3 新引锚点亲核：`receipt_kernel.py:574-587` `publish_exclusive` 与 `RawBytes:41` 用于 jsonl 台账是否可行（payload 类型、目标目录 fsync、失败时暂存清理）；`_fsync_dir:196`；validator `:1457`、`canonical_json:50`、`sha256_bytes:66`；`sqd_gap_repair.py:595-596`、`:1601`。
3. §2.3 第 4 步「采纳 slot 序列须是 `plan["candidate_slots"]` 的前缀」：与生产者实际的 slot 拉取顺序（`_live_payloads` 的遍历顺序、并发 workers 下的台账写入顺序）是否一致？若并发下台账 seq 顺序 ≠ 候选顺序，该前缀断言会误拒真实旧 pending——请核 `:961-1010` 与 `test_batch8_repair_scale.py` 的 ordered-workers 语义后给结论与替代断言。
4. §4 向量是否仍有矛盾或不可构造（尤其 ⑧⑨⑩ 与「独立验证版本 1 行为」的 transport 夹具路径 `--transport-fixture`/`repair_slot_responses:229-263` 能否放入含 `transactionConfig` 的交易、能否观察实际送出的 body）。
5. 最小化：v3 是否有可再省/省过头之处。
6. 结尾给「v4 修订清单」（通过则写“无”）。
