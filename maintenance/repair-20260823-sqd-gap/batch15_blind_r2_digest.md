# 批 15 盲审 R2 消化工单（1 条 P2：深验结果复用）

- 基线：main `345c9d5`（v6.53.1）。开工 `git status --short` 须为空（本工单已由调度方 commit 入库）。
- 盲审结论（codex review-mtfo3qpf 原文要点）：`audit_release_gate.py:597-598` 的
  `_frozen_consumer_target()` 在 Solana `new-analysis` 一次 `run()` 里被 B-7 路径与 series 路径各调一次，
  每次都完整执行 `validate_reconciliation_report()`；该深验会读取并重算整本边账本（ARC 约 2,660 万条边），
  而闸内 `check_formal_case_chain`（:295 冻结态）与 `check_reconciliation`（:501）本已各跑一次。生产规模案
  由此多出 2 次全量扫描，是有意义的性能回退。要求：**一次 `run()` 只深验一次，结果传给/缓存给这些消费者**。
- 调度方裁决：本批修，方式＝**run() 作用域缓存**，不动 `shared_release_receipt.py`，不改深验语义。

## 改动面（白名单，超出即违规）

1. `scripts/report/audit_release_gate.py`（先 `grep -n` 亲核行号）：
   - 新增 run()-作用域的深验结果缓存，供三处消费：`check_formal_case_chain` 的冻结态投影（:295 附近
     `validate_reconciliation_report(case_dir, return_receipts=True)`）、`_frozen_consumer_target()`（B-7 与
     series 两次调用）。缓存键＝case_dir 解析后的绝对路径；缓存值＝`(checked_target, receipts)` 或该次抛出的
     异常（异常也缓存：同一 run 内输入不变，重跑只会同样失败；**缓存命中异常时必须重新 raise 同一异常对象**，
     不得把失败变成豁免）。
   - 缓存生命周期＝**单次 `run()`**：在 `run()` 入口创建、出口清理（`try/finally`），不得跨 run 残留（测试进程内
     多次 `gate.run()` 用不同临时目录/同目录改文件后再跑，必须各自重新深验——N1/N2/N3 等毒丸测试正是靠
     "改文件后再跑"）。实现自选：模块级 `_RUN_DEEP_CACHE` 由 run() 显式 reset，或 contextvar，或把 cache 挂在
     `run()` 局部并显式传参；**禁止**把私有键塞进 `data` 字典（`data` 被按文件名遍历，会污染缺件/多件判定）。
   - `check_reconciliation`（:501 附近）**本体不动**；若它调用 `validate_reconciliation_report` 的参数形态与缓存
     键一致且无副作用差异，可让它也走缓存（同一深验、同一 case_dir），否则不动并在 done 说明。
   - 语义零变化：缓存命中与不命中的 errors 列表逐字相同（测试锁定）。
2. `scripts/tests/test_batch15_three_ledgers_frozen.py`：
   - 新增 N9：在 N6 完整动态案上，monkeypatch/计数 `shared_release_receipt.validate_reconciliation_report`
     的调用次数（包装原函数，不改语义），断言一次 `gate.run(..., profile="new-analysis")` 内该函数被调用
     **恰好 1 次**（若 `check_reconciliation` 未接缓存则恰好 2 次——按你的实现写死并注明理由），且 errors==[]；
   - 新增 N10：同一进程内先 run 一次（绿），再篡改 `data/holders_owners.json`，再 run 一次 → 必须重新深验并拒
     （证明缓存不跨 run 残留；可直接复用 N2 的篡改手法）；
   - 既有 R1/N1–N8 不改断言。
3. `maintenance/repair-20260823-sqd-gap/batch15_done.md`：加"盲审 R2 消化"节（改动摘要、N9/N10 errors/计数原文、
   `git diff --stat`）；§1 里"本批不做缓存"的表述改掉。
4. `CHANGELOG.md` 6.53.1 条目："设计与实现"栏补一句"深验结果在单次 run() 内缓存，B-7/series/跨分区投影共用一次
   深验"；"盲审与验收"栏改为"codex 盲审 R1 1 条 P2（N5 假绿）、R2 1 条 P2（深验重复扫描）均已消化"。
   **不升版本号**。

## 禁改

`shared_release_receipt.py`、`solana_exact_validate.py`、`camp_series_provenance.py`、`holder_distribution_scan.py`、
`check_three_ledgers` 本体、EVM 分支、Solana 静态段、`_recon_owner_snapshot` 冻结分支逻辑、其他任何测试文件、版本号。

## 完成标准

- `python3 scripts/tests/test_batch15_three_ledgers_frozen.py` 全绿（12 组）；`test_repair_batch_d.py`、
  `test_audit_release_gate.py`、`test_batch13_accounting_target.py`、`test_repair_batch_c.py`（用
  `MPLCONFIGDIR=/private/tmp/...`）定向复跑全绿；`changelog_lint.py`、`docs_lint.py`、`git diff --check` 过；
  沙箱 run_all 到 139/141（两个 loopback EPERM）如实报，本机全套由调度方复跑。
- 不 commit；不写任何 key；行号与描述不一致即停工汇报。
