# 批 15 盲审 R1 消化工单（1 条 P2）

- 基线：main `3a71c26`（v6.53.1）。开工 `git status --short` 须为空（本工单文件已由调度方 commit 入库后再派工）。
- 盲审结论（codex review-mtfj5i2l，原文要点）：`test_batch15_three_ledgers_frozen.py:205-206` N5"案内绝对
  exact ref 通过"是**假绿**——单元层把 `shared.validate_reconciliation_check` 换成夹具假件，而生产
  `_frozen_consumer_target()` 先调 `validate_reconciliation_report()`，其 `validate_reconcile_receipt_deep()`
  （scripts/lib/solana_exact_validate.py:1905）把 inputs 路径过 `_safe_case_path`（同文件 :354-357），
  **无条件拒绝绝对路径**。所以真实 `gate.run()` 在 `_bound_case_ref()` 之前就已拒绝，N5 正向断言在生产不可达。
- 调度方裁决：**保留"exact 收据 inputs 必须案内相对路径"的既有生产契约**，不动共享深验器；
  把 N5 改为通过真实校验器证明 fail-closed；`_bound_case_ref` 调用保留（规则一致、无害）。

## 改动面（白名单，超出即违规）

1. `scripts/tests/test_batch15_three_ledgers_frozen.py` N5（:201-217 附近，先 `grep -n "def test_n5"` 亲核）：
   - 删除"案内绝对路径通过"的正向断言；
   - 新增/改写为：exact 收据 `inputs.holders_owners.path` 写成案内绝对路径时，**不打 fake_check 补丁**、走真实
     `validate_reconciliation_report`（或直接 `gate.check_three_ledgers` 但不 patch），断言 errors 含
     "冻结态深验未通过"且**不含"不等值"**（不回落）；案外绝对路径断言保持拒绝；
   - 若走真实深验器需要夹具具备真实 exact 收据/边文件等（batch11 fixture 的 fake_check 正是为绕开它），
     允许改用 `test_batch_d` 风格完整两态 fixture 的最小子集，或在 N6 完整动态案上追加一个"exact ref 改绝对
     路径→gate.run 拒且不回落"的变体断言（推荐后者，成本最低）。函数名与 docstring 改成"案内绝对路径也被
     深验器 fail-closed 拒绝"。
2. `maintenance/repair-20260823-sqd-gap/batch15_done.md`：§2a 与 §3 第 8 条把"案根内相对/绝对路径接受"
   改为"生产契约=案内相对路径；案内绝对路径由深验器 fail-closed 拒绝（盲审 R1 P2 修正）"；末尾加"盲审 R1 消化"节。
3. `CHANGELOG.md` 6.53.1 条目"测试"栏：把"案内/案外绝对路径"措辞改为"案内绝对路径亦被深验器拒绝（fail-closed）、
   案外绝对路径拒绝"；"盲审与验收"栏补"codex 盲审 R1 1 条 P2（N5 假绿）已消化"。**不升版本号**（同版本内修测试与文案）。
4. 顺手（同文件、零语义）：`scripts/report/audit_release_gate.py::_frozen_consumer_target` 深验失败错误文案
   `"accounting as_of_block={…} 与 wrapper {…} 不同，但冻结态深验未通过…"` 在 Solana 同块情形措辞不准——改为
   `"accounting as_of_block={…}/wrapper {…}：冻结态深验未通过，无法确定对账时点: {exc}"`。同步所有测试断言
   （grep "冻结态深验未通过" 仍匹配即可，尽量不改断言）。

## 禁改

`shared_release_receipt.py`、`solana_exact_validate.py`、`camp_series_provenance.py`、`holder_distribution_scan.py`、
`_recon_owner_snapshot` 与 series 调用处逻辑、其他任何测试文件、版本号。

## 完成标准

- `python3 scripts/tests/test_batch15_three_ledgers_frozen.py` 全绿且 N5 新断言真实走过深验器（在报告里贴 errors 原文）；
- `python3 scripts/tests/changelog_lint.py`、`docs_lint.py` 过；`python3 scripts/tests/run_all.py` 本机由调度方复跑，
  你在沙箱跑到 139/141（两个 loopback 纵切片 EPERM）即可如实报；
- 不 commit；把改动摘要与 `git diff --stat` 写进 batch15_done.md 的"盲审 R1 消化"节；不写任何 key。
