# F-008 盲审 verdict（round 3，codex fresh 只读，2026-08-24）

VERDICT: BLOCK（残余两个精度缺口，均在测试守卫，生产代码零漂移已核）

已闭合：AugAssign/AnnAssign/NamedExpr/for-target/with-as/del/嵌套赋值全部拒（盲审内存重放 logs+= 与 b2=blocks 均 REJECTED）；两个注入自测真实存在且要求守卫抛 AssertionError；绿证 44/44＋四组定向回归重建；round1/2 原文未改写；生产代码零改动（四文件 SHA 与 done 记录一致、git diff --check 空）。

残余阻断（盲审内存 AST 实证两个放行反例）：
1. 定义校验用 set(shapes) 丢失变量身份映射——交换 logs/blocks 两赋值的文件名后守卫 ACCEPTED（test_lit_regression_f008.py:487）。
2. 消费校验只比较 logs=3/blocks=1 总数、未冻结每个 SQL 槽位——交换 logs 与 blocks 的 SQL 消费位置后守卫 ACCEPTED（test:507）。
done round3 第 181/200 行"逐项分类/fail-closed"随之仍属过度声明。

最小返工清单（原文）：
1. 按变量名精确映射替代 set(shapes)：固定 logs→logs.parquet、blocks→blocks.parquet。
2. 每个 SQL 读取建立含变量名、所属语句/调用及槽位的精确签名，禁止按 3/1 计数验收。
3. 增加"交换文件名映射"与"交换 SQL 消费位置"两个内存 AST 自测（修前红、修后绿）。
4. 重建绿证；仅追加 round4 文书修正 round3 :181/:200 过度声明。生产代码无需改动。
