[2026-09-23T08:02:07.606Z] Assistant message
# 复核 W3 v1: 通过

核心修法正确，未发现遗漏的同类测试遮挡。先纠正数量：该循环共有 **8 个向量，目标之外还有 7 个**。

本次只读、离线，未改文件、未 commit、未读取禁止目录。补充执行了原始校验代码片段的纯内存核验；未运行会写临时文件的完整回归。

1. **① 根因描述准确。**

   [test_sqd_gap_repair.py:987](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:987) 只改前代 digest，保留原 `source`。目录名绑定在 [solana_exact_validate.py:1353](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:1353) 不成立，使 `adopted_valid=False`，并在 `:1356` 添加错误；后面的 `:1523` 因此跳过摘要重算。

   严格说，这是**认领校验失败后跳过重算**，不是整个深验函数立即返回。与 [blind_review_W1_r2_report.md:11](/Users/uravvv/.claude/tca-fix-txv1/maintenance/repair-20260923-solana-txv1/blind_review_W1_r2_report.md:11) 的结论一致。

2. **② §1 改法有效，reason 子串仍匹配。**

   同步修改 `predecessor_plan_digest` 和 `source` 后，目录名绑定通过；其他字段及候选前缀不变，能够通过 `:1525`，执行当前代和前代两次重算，最终在前代摘要比较处失败，见 [solana_exact_validate.py:1523](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:1523)。

   `:1534` 仍添加 `RPC ledger adopted record invalid`，包含测试要求的 `"adopted record invalid"`。内存核验结果是 **原向量 0 次，修正后 2 次**。

   建议采用工单已允许的 `wrong_digest` 版本，复用 [test_sqd_gap_repair.py:974](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:974)：
   ```python
   lambda rows: rows[0]["adopted"].update(
       predecessor_plan_digest=wrong_digest,
       source="pending-" + wrong_digest)
   ```
   若要完全排除碰撞条件，隔离核验时再断言伪值同时不同于当前代和真实前代 digest；当前代相等检查位于 `solana_exact_validate.py:1347`。

3. **③ §2 方法可行，但必须按单个向量计数。**

   [workorder_W3_v1.md:15](/Users/uravvv/.claude/tca-fix-txv1/maintenance/repair-20260923-solana-txv1/workorder_W3_v1.md:15) 的“该向量”应明确限定为 [test_sqd_gap_repair.py:1002](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:1002) 的那一次 `deep_check`。整段测试已经包含正向深验和 `:959、:966` 的直接重算，总调用次数不会是 0。

   建议把证据要求写成：**原向量调用 0 次；修正向量调用 2 次，参数依次为当前代 SHA、前代 SHA；两者均断言原 reason 子串。** `≥1` 单独看不足以区分两次调用；记录参数能直接证明前代重算已执行。

   更简做法：从同一有效基线复制两份输入，在一次内存核验中分别应用旧、新 mutation，每次独立重置 spy；无需为了比较重复运行整套测试。spy 应使用 `wraps` 执行真实函数，并照原循环更新台账外层 size/hash。完整回归另跑一次即可。

4. **④ 行号、锚文本一致；另有施工前置条件待处理。**

   工单引用的测试 `:987`、`wrong_digest :974`、生产校验 `:1353` 均准确。摘要调用的精确位置是生产文件 `:1527` 和 `:1529`，拒绝 reason 在 `:1534`。

   [workorder_W3_v1.md:6](/Users/uravvv/.claude/tca-fix-txv1/maintenance/repair-20260923-solana-txv1/workorder_W3_v1.md:6) 要求施工开始时工作树为空，但当前有三份未跟踪输入：`blind_review_W1_r2_report.md`、`review_W3_r1_prompt.md`、`workorder_W3_v1.md`。分支正确，HEAD 为 `e44551a`。施工前需由调度方归档这些输入，或明确允许这三份既有未跟踪文件。

   此外，`:16` 的“一文件一处改动”宜注明指**测试代码 diff**；`:19` 还要求新增 `W3_done.md`，最终交付文件数不能也限定为一份。

5. **⑤ 其余 7 个向量逐项通过，没有新增同类遗漏。**

   下表中测试文件为 `scripts/tests/test_sqd_gap_repair.py`，校验文件为 `scripts/lib/solana_exact_validate.py`。调用次数来自原始代码片段的内存核验。

   | 测试位置及向量 | 实际拒绝位置、调用次数 | 判断 |
   |---|---|---|
   | `:983` `reorder_prefix` | 校验 `:1525–1526`；0 次 | 正确命中候选前缀顺序检查。测试 `:969–972` 已重排 seq；换入行的版本 1 参数也被 `:1392–1394` 接受，没有被这些检查遮挡。 |
   | `:984` `change_source` | 校验 `:1353–1356`；0 次 | 目录名绑定就是该向量的目标。 |
   | `:985` 未登记 producer SHA | 校验 `:1350–1356`；0 次 | 正确命中历史 producer 准入检查；测试 `:826–827` 明确断言该 SHA 未登记。 |
   | `:989` 数据行 fingerprint | 校验 `:1387–1388`；2 次 | 正确命中行与 header 的指纹绑定；添加 reason 后仍继续重算。 |
   | `:991` header fingerprint | 校验 `:1362–1364`，并在 `:1387–1388` 产生行级不一致；2 次 | 正确命中 header 与 bundle 的绑定；后续附加错误不遮挡首次检查。 |
   | `:993` `rows=True` | 校验 `:1352–1356`；0 次 | 正确命中类型检查；`_integer` 在校验文件 `:90–91` 明确排除 `bool`。 |
   | `:994` `adopted=None` | 校验 `:1338、:1342–1356`；0 次 | 键仍存在，进入认领检查后因非字典被拒；不会被当作“没有认领记录”。 |

   这些向量中，提前拒绝的检查本身就是测试目标；只有原 `:987` 向量存在“想测摘要重算，却先被目录名绑定挡住”的问题。
