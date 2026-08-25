# 批 2d 工单·第二段(登记面与版本收口;裁决=两段提交方案 1)

背景:第一段已由验收方 commit——分支 `fix/sqd-gap-batch2d`,commit `55d4efede78f6afb6c1d3c8aa3bbec95b6faa33f`(probe 修复+net 注释+新测试+工单/停工请示/绿证)。本段以该 commit 为冻结锚,恢复原工单"登记面与版本"章节施工。原工单 batch2d_workorder.md 的背景、判据、禁区仍然有效,与本文件冲突处以本文件为准。

## 任务

1. **producer_history**:`scripts/lib/producer_history.py` 中 sqd_coverage_probe.py 的两条登记,按该文件头部明文纪律与既有条目先例更新到当前脚本版本:新条目 sha256=第一段 commit 内脚本字节哈希(自行用 `git show 55d4efede78f6afb6c1d3c8aa3bbec95b6faa33f:scripts/solana/sqd_coverage_probe.py | shasum -a 256` 复算,不抄本文件),commit=上述 40 位全哈希;旧条目处置(保留/REVOKED)按文件纪律与先例定,拿不准停工请示。完成后 `test_anchor_plan_v3.py` 必须 PASS。
2. **run_all 注册**:`scripts/tests/run_all.py` 注册 `test_batch2d_stream_tail.py`;SUITE 机械计数 +1。
3. **版本五处**:VERSION、pyproject.toml、SKILL.md 版本行 → 6.52.3;CHANGELOG 首索引+首详情新条目(批 2d:SQD stream 尾部跳块 200 空体流结束语义、两段提交、SUITE 计数变化)。`changelog_lint.py` 写入前后各跑一次。
4. **全量验收**:`python3 scripts/tests/run_all.py` 全部通过(机械计数自报;若有环境性失败逐条如实记录根因,不得宣称全绿)。
5. **报告**:写正式 `batch2d_done.md`(两段合并叙事:第一段引用 55d4efe,本段逐任务红绿);绿证追加进 `batch2d_green_evidence.txt`。

## 白名单(只许改/新增)

- scripts/lib/producer_history.py(仅 sqd_coverage_probe 相关条目)
- scripts/tests/run_all.py(仅注册行)
- VERSION / pyproject.toml / SKILL.md(仅版本行)/ CHANGELOG.md(仅新增条目)
- maintenance/repair-20260823-sqd-gap/batch2d_done.md(新增)、batch2d_green_evidence.txt(追加)

## 禁区

- 禁改第一段已提交的任何生产/测试文件(probe、net.py、test_batch2d_stream_tail.py);禁 commit/push(Fable 终验后收口);禁联网;发现矛盾停工写 `batch2d_stage2_stopped.md` 请示。
