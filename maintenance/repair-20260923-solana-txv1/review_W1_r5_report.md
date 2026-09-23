# 复核 W1 r5: 通过

v5 已正确修复 r4 唯一阻断项，并落实全部 3 条措辞建议。

1. **§4⑫ EXDEV 注入范围：通过。** [第 118 行](/Users/uravvv/.claude/tca-fix-txv1/maintenance/repair-20260923-solana-txv1/workorder_W1_v5.md:118) 仅对旧 pending evidence → 目标 evidence 的链接注入 EXDEV；其他调用原样转发全部参数，明确放行 `publish_exclusive` 内部暂存发布。重试保留限定 EXDEV 替身，仅撤销首次发布失败注入，并要求验证实际经过原子复制、目标与源哈希一致。已消除 r4 指出的内部发布被误伤问题。
2. **v1 请求字段位置：已落实。** [第 114 行](/Users/uravvv/.claude/tca-fix-txv1/maintenance/repair-20260923-solana-txv1/workorder_W1_v5.md:114) 明确断言 `body["params"][1]["maxSupportedTransactionVersion"] == 1`。
3. **摘要合成向量：已落实。** [第 120 行](/Users/uravvv/.claude/tca-fix-txv1/maintenance/repair-20260923-solana-txv1/workorder_W1_v5.md:120) 指定 `coverage=[10,20]`、`beta=[20,30]`，包含 beta 独有候选，并保留当前、前代两种 sha 的一致性验证。
4. **共享 inode 表述：已落实。** [第 91 行](/Users/uravvv/.claude/tca-fix-txv1/maintenance/repair-20260923-solana-txv1/workorder_W1_v5.md:91) 限定为硬链接成功的采纳证据，明确 EXDEV 复制不共享 inode；§5 文档要求同步采用该限定。

本次仅对照指定两份材料核验上述四项，未重新全量复核、未运行测试；未改文件、未 commit、未读取禁读目录。结论仅针对工单修订文本。

**v6 修订清单：无**
