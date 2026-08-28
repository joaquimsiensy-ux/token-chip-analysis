# 【消化工单】F-03b 批 3b:盲审两项发现消化(只改点名项)

- 基线:批 3 施工后的当前工作树(未提交;main 仍= 9b1c4b5)。禁 git 写操作。
- 范围铁律:只修下列两项及点名测试;发现新问题只记录进 done 报告。
- 盲审原文:`/private/tmp/claude-502/-Users-uravvv-Desktop-----fable----/a70a76e2-4163-45ef-87cd-b97330a3d440/tasks/b039dybj8.output`(只读参考)。

## 发现 1(必修):重试后 mismatch 误入 `unverified` 审计字段

- `_recheck_known_slots` 重试处理循环(:约 635):非 verified 全部落入 `unverified`,包括 retry mismatch——与 scan-schemas :673 的契约定义(`unverified_ranges` 仅指"首轮失败且重试仍**请求失败**")矛盾,发布产物的 shared_map 会持久化错误失败分类(安全裁决不受影响,仍整体回退)。
- 修法:重试结局三分同首轮——retry mismatch 只进 mismatch 路径(触发整体回退),**不进** `unverified` 列表与 `recheck_stats.unverified` 计数;`recheck_stats` 语义核对一遍与 scan-schemas 定义逐字一致。
- 测试:扩展现有 retry-mismatch 用例(`test_retry_rescues_range_and_retry_mismatch_falls_back`),断言整体回退之外再断言 `info["unverified_ranges"] == []`、`recheck_stats["unverified"] == 0`(以及 stats 其余两键的正确值)。

## 发现 2(必修):案区间外 recheck 撤销防线缺回归测试

- 生产代码(:约 774 的降级循环)方向正确但无测试锁——删掉该循环现有 suite 全绿。
- 修法(只加测试,不改生产代码):在部分复用与纯 full 两个端到端用例里补断言——凡 `from < 案from 或 to > 案to` 的 recheck 行,发布账本中 `counts_coverage` 必须为 false;发布 coverage 的 `scan_ranges` 不得含任何越出案区间的条目。构造夹具时确保存在"完全在案外且成功验证"与"跨案界"两类 recheck 行,两类都要被断言压住。
- 注:若断言暴露生产代码真实缺口(如跨界行降级后 union 等式反而破坏),停工在 done 报告说明,不得自行扩改。

## 顺带澄清(零代码,写 done 报告即可)

盲审指出工单批 3 测试第 6 类"全部 recheck 段 unverified"字面与 canary 整体回退相冲突,施工按"案内全部可复用区间均被非 canary unverified 覆盖"的合理解释执行——此解释被裁判方追认,在 done 报告记一行即可。

## 白名单

`scripts/solana/sqd_coverage_probe.py`(仅重试分类段)、`scripts/tests/test_f03_sharedmap_reuse.py`、`maintenance/repair-20260827-f03-sharedmap/batch3b_done.md`。其余一律禁改。

## 完工标准

两项先红后绿(红=批 3 现态;红例输出附 done 报告);本机 run_all 全量原样贴报告;done 报告含 diff 摘要与工单外发现。
