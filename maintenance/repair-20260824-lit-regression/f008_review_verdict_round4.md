# F-008 盲审 verdict（round 4，codex fresh 只读，2026-08-24）

VERDICT: PASS

1. 守卫收口实证：定义校验按变量名精确冻结（logs→run_*/logs.parquet、blocks→run_*/blocks.parquet），消费端五个读取节点编码"变量名＋语句＋调用类型＋槽位＋f-string 槽位"签名全集精确比对（test_lit_regression_f008.py:530,574,594）。盲审员内存 AST 重放六变体：现状 ACCEPTED；交换文件名映射/交换 SQL 槽位/logs+=/b2=blocks/字符串拼接第三 glob 全部 REJECTED（各轮旁路全数封死）。理论上"保留诱饵读取＋其他 API 引入额外读取"仍可规避，但在 wave_scan/entity_source_trace 被算法哈希锁死、守卫仅提示三处 pattern 同步的边界下无现实意义，不构成 BLOCK（盲审员自判）。
2. 两个 round4 自测反例真实在测（:648,:673,:733），前三轮反例保留（:713）；绿证 46/46＋四组定向回归（68/16/11/十一类契约）EXIT_CODE=0 齐全；done round4 节（:214 起）修正 round3 过度声明且各轮原文未改写。
3. 生产代码零漂移：相对 333144e，scripts/ 跟踪改动仅 case_paths.py＋handoff_manifest.py（既审 diff），四关键文件 SHA 与文书一致，红绿证据哈希与文书一致，git diff --check 空。

审程记录：round1 BLOCK（字符闸漏 C1＋AST 守卫非 fail-closed）→ round2 BLOCK（wave AugAssign 旁路）→ round3 BLOCK（映射/槽位精度）→ round4 PASS。生产代码自 round2 起零改动，后三轮全部是测试守卫与文书精化。
