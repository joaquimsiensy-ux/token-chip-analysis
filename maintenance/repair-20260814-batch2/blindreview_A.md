# 工单 A 独立盲审报告（opus 攻击型验收，2026-08-14）

判定：FAIL——击穿 2（F-A1 零宽字符掏空人类证据字段 / F-A2 巨整数 OverflowError 逃逸 policy_reject）＋缺陷 3（F-A3 三值主闸无独立锚 / F-A4 第四值复核 CLI 链不可达无锚 / F-A5 NaN 双防线互遮蔽无单条锚）＋观察 5（F-A6 文档表述强于实现×4 / F-A7 approval 有效期无上限可复用 / F-A8 收据 inputs 不记 approval / F-A9 approval 可兼任 evidence / F-A10 两侧四函数无同源守卫）。

约 133 项攻击全清单（含未击穿）、端到端复现记录、干净快照（git archive 8c9b0f6）复跑确认、破坏性注入反证表——原文由盲审员产出，处置转 fixround1 工单。

关键复现摘录：
- F-A1：偏差 9900bps，approval 四字段全填 "​"→生产 rc=0 落 PASS、消费 ACCEPTED；空串/ASCII 空格/全角空格/NBSP 对照组均正确拒（strip 语义边界=isspace()，U+200B/U+FEFF 是 Cf 类不是空白）。同族扩散：waiver 存量 approved_by/reason 同失守。
- F-A2：observed_diff_bps=10**400＋合法 approval→assert_waiver_covers_diff 的 float() 抛 OverflowError ≠ ValueError，逃出 TolerancePolicyError 接管→exit 1 且预置旧 PASS 收据存活（作废义务失守+退出码两义崩溃）；json 20 万层深嵌套 RecursionError 同族 exit 1。消费侧同字段被 except Exception 兜成 exit 2 未失守=两侧兜底深度不一致。
- F-A4 澄清：CLI 全链上第四值复核不可达（三值闸先拦），但 assert_waiver_covers_diff 作为库函数被单独调用时可达——按"库函数独立防线"保留＋补直调锚测试。
