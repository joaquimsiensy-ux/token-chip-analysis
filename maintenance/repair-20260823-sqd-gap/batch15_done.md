# 批 15 完工报告：B-7 三账对账源与 series cutoff 冻结态投影

## 结论

- 施工基线：`main@363ef4a088cbfc6ae0981433ad6f08e81168a720`，开工 `git status --short` 为空。
- 工单所写生产基线 `d50b2f3` 到当前 HEAD 的唯一差异是调度方提交的 `batch15_workorder.md`；生产代码基线未漂移。
- 版本：`6.53.0 → 6.53.1`。
- Batch 15 新测试：10/10 PASS；完整动态 N6 `gate.run(..., profile="new-analysis") == []`。
- 全套：141 total / 139 PASS / 2 FAIL / rc=1；两项均为沙箱禁止绑定 `127.0.0.1` 的环境失败，故本报告状态为 PARTIAL，不冒充全绿。
- 止损：未触发。N6 两态化绑定/重签点计数 12，未超过 `>12` 门槛；施工未超过 90 分钟。
- commit/push：未做，留给 Fable 验收。

## 逐节对照

### §0 先红

已做。

- 修生产代码前运行：`python3 scripts/tests/test_batch15_three_ledgers_frozen.py --r1`。
- HEAD：`363ef4a088cbfc6ae0981433ad6f08e81168a720`；rc=1。
- R1 `errors` 恰好两条：一条“与四查冻结时点 501 不一致”，一条逐址“不等值”；缺件/其它错误为 0。
- N6 完整动态案修前恰好命中 B-7 两类＋series cutoff 一类，无缺件或旁路错误。
- 原始证据见 `batch15_red_evidence.txt`。

### §1 共用助手

已做，见 `scripts/report/audit_release_gate.py:566-616`。

- `_frozen_consumer_target(...) -> tuple[dict | None, dict | None, dict | None]` 统一经
  `_validate_reconciliation_report_once(...)` 取得单次 `run()` 缓存的深验结果，再调用
  `accounting_expected_target(...)`；缓存不写入 `data`。
- 深验异常追加带 label、accounting/wrapper 块高与原异常的 fail-loud 错误，返回三空；调用方不回落观察点。
- accounting target 与中央选择器结果做 canonical 自闭合；不一致只追加指定错误并停止消费点。
- 动态态返回 `(expected, canonical wrapper, receipts)`；EVM 仍直接走原路径。
- formal 必需件缺失时，`REQUIRED_BY_PROFILE` 已独立 fail-closed；助手返回三空，让旧 series 校验继续暴露自身物理 SHA 错误，避免次生 target 错误遮住原根因。该行为由 `test_repair_batch_c.py` N02 锁定。

工单内部有一处不可同时满足的字面冲突，已按更强 fail-closed 负测执行：

- §1 第 1 步写“accounting.as_of_block == wrapper 即静态并直接返回”；
- N4b 又要求“动态案把 accounting 错填 wrapper 不得称静态，必须被中央选择器自闭合拒绝”。

若仅按前者短路，N4b 必然放行。实现因此仅对 EVM 同块直接返回；Solana 同块仍先深验 actual exact，只有中央选择器也返回 wrapper 才判真静态。N4b 已锁定该行为。

### §2a B-7 对账源

已做，见 `scripts/report/audit_release_gate.py:680-705`。

- 动态 Solana 用 `receipts["exact_reconcile"]["inputs"]["holders_owners"]`。
- 生产模块按工单直接导入既有私有 `_bound_case_ref`；生产契约是案内相对路径，案内绝对路径亦由深验器 fail-closed 拒绝（盲审 R1 P2 修正）；`..`、案外、文件 symlink、size、sha256 任一失败均拒。
- owners 实物转为 `str -> int`，返回冻结块；解析错误 fail-loud。
- EVM 分支、原 Solana 静态 observation bundle 段、`check_three_ledgers` 本体均与 HEAD 字节全等。

禁改面 SHA256（HEAD 与工作树一致）：

- EVM 分支：`7b35fb77cc2a62d2dde8cb8c2c625ce46d18583159e8353fb7c783529f6f208e`
- Solana 原静态段：`8b94756ee1b5d85ceafa2f57f07e9e4086dab9d7a05ed75177fb9b8ba14a2455`
- `check_three_ledgers` 本体：`e6b938a7bfee3f24d115341a6e000005e360a945d1bc6e3c0caf850c215fde88`
- `SNAPSHOT_BINDING_BY_FAMILY` 至分布绑定面：`e3b5db47dd934c6ddeb157f04ba3108e44491866b95135066035c66273613c23`

### §2b series cutoff

已做，见 `scripts/report/audit_release_gate.py:1564-1580`。

- 非两态沿用 wrapper target。
- 冻结态只在助手无新增错误时调用 `check_series_binding`，并把中央选择器的冻结 `as_of_block` 投影下去；助手报错时不再追加 cutoff 噪音。
- N6 暴露表示层差异：`canonical_target` 把 Solana 规范成 `sol`，但禁改的
  `camp_series_provenance.py` 与 exact 收据要求原始链名 `solana`。若把 canonical expected 整对象直传会新报
  `reconcile_receipt.chain='solana' 与案 target.chain='sol' 不一致`。因此调用点保留已深验 wrapper 的 chain/token 表示，只投影中央选择器的冻结块高；这不改变 cutoff 语义，也不触碰禁改校验器。

### §2c 文档

已做。

- `references/analyze-workflow.md:117-120`：动态 Solana 显式观察快照完整命令。
- `references/split-run.md:54`：同一命令与默认冻结件陷阱。
- `references/scan-schemas.md:380,1190`：分布吃观察 owners；B-7/series/accounting 吃 exact owners＋冻结块。
- `python3 scripts/tests/docs_lint.py`：PASS（45 个文档）。
- 未改 `holder_distribution_scan.py`。

### §3 测试与 SUITE

已做。

`scripts/tests/test_batch15_three_ledgers_frozen.py` 共 10 组：

1. R1/G1 冻结三账读取 exact owners 后通过；修前精确两类红。
2. N6 完整动态 new-analysis 零 error。
3. N1 活观察三账在冻结案被时点＋逐址等值双拒。
4. N2 冻结 owners 内容篡改，深验拒且无“不等值”回落噪音。
5. N3 冻结 owners symlink 拒绝。
6. N4a 真静态案通过。
7. N4b 错填 wrapper 的 accounting 无法伪装静态。
8. N5 exact ref 的案内绝对路径也被真实深验器 fail-closed 拒绝，案外绝对路径保持拒绝，且均不回落逐址“不等值”检查。
9. N8 默认 snapshot 选冻结件，显式参数选观察件。
10. N7 注入错误 cutoff 投影，series provenance 拒绝。

`scripts/tests/run_all.py` 已登记 Batch 15，`SUITE_COUNT=141`（140→141）。

### §4 版本与 CHANGELOG

已做。

- `VERSION`、`pyproject.toml`、`SKILL.md` 同步为 `6.53.1`。
- CHANGELOG 索引和六栏详情已新增；盲审栏原样写入“@CX 施工前复核＋codex 施工后盲审＋Fable 独立验收”。
- `changelog_lint.py`：PASS。
- `test_version_consistency.py`：PASS，metadata consistent at 6.53.1。

### §5 完工报告与边界

已做本报告；完整套件结果见末节。未 commit，未联网，未读或改 ARC/桌面/Documents 案卷，未读取密钥文件。

首次完整套件真实发现 `test_repair_batch_c.py` 回归：缺 accounting 的 N02 partial fixture 被助手新增错误抢先，导致原 series 物理 SHA 检查未执行。该问题没有归为环境失败；在助手内恢复“必需件缺失由 profile 报错、series 沿原 wrapper 继续校验”后，`test_repair_batch_c.py` 227 checks PASS。最终全套只剩两项 loopback 环境失败。

当前改动路径全部在白名单内；工单文件本身为 HEAD 已跟踪文件且未修改。没有任何禁改文件出现在 `git status --short`。

## as_of_block 消费点全扫

执行范围：`scripts/report`、`scripts/lib`、`scripts/solana`、`scripts/evm` 全部 Python；29 个生产文件、165 个 `as_of_block|expected_cutoff_slot|accounting_expected_target` 命中逐类复核。

结论：同意调度方“本批是方案 A 第七/第八消费点”的初稿；未发现第九个仍把动态 wrapper 当冻结账时点的发布消费者。

- 中央选择器定义：`shared_release_receipt.py:1489-1504`。
- 既有 handoff accounting 消费：`handoff_manifest.py:452-455`，已选 exact/静态 wrapper。
- 既有 shared release accounting 消费：`shared_release_receipt.py:1821-1833`，已选 exact/静态 wrapper。
- 既有发布闸跨分区 target 消费：`audit_release_gate.py:284-311`，深验后把动态 block claim 投到 exact。
- 本批共用助手：`audit_release_gate.py:566-616`；B-7 消费位于 `:680-705`，series cutoff 消费位于 `:1564-1580`。
- `reconciliation_report.py`、`shared_release_receipt.py` 其余命中是 wrapper/receipt 生产与深验；`replay_edges.py`、`solana_exact_validate.py` 是 exact 冻结生产/验证；不应改投影。
- `holder_distribution_scan.py` 是观察 owners 消费点，按方案 A 明确保留观察态；不应改为冻结态。
- identity、adversarial、accounting 的其它 target 命中来自已冻结 accounting/identity 收据或其独立深验，不直接消费 wrapper cutoff。
- EVM 生产/验证命中没有 exact 两态，继续使用唯一 wrapper/accounting 块；零变化回归通过。

## 治理债

1. `_bound_case_ref` 是私有名，却被 `audit_release_gate.py` 生产模块导入。建议下批在 `shared_release_receipt.py` 增加公开别名并迁移调用；本批按白名单禁止修改共享模块。
2. CHANGELOG 书面规则称“修订号只用于文档小修”，但批 10–15 已用修订号承载生产行为修复。本批按批准工单升 `6.53.1`，建议单独统一版本规则与实践，避免验收时双重标准。

## 定向验收

- `python3 scripts/tests/test_batch15_three_ledgers_frozen.py`：10/10 PASS。
- `python3 scripts/tests/test_repair_batch_d.py`：PASS，含 B-7、静态 Solana new-analysis 与 A5 全链。
- `python3 scripts/tests/test_audit_release_gate.py`：PASS。
- `python3 scripts/tests/test_batch13_accounting_target.py`：8/8 PASS。
- `python3 scripts/tests/test_batch14_accounting_bundle_fallback.py`：9/9 PASS。
- `python3 scripts/tests/test_evm_observation_release.py`：11/11 PASS。
- `python3 scripts/tests/test_reconcile_v4_receipt.py`：PASS。
- `MPLCONFIGDIR=/private/tmp/batch15-matplotlib-cache python3 scripts/tests/test_repair_batch_c.py`：227 checks PASS。
- `python3 scripts/tests/docs_lint.py`：PASS。
- `python3 scripts/tests/changelog_lint.py`：PASS。
- `python3 scripts/tests/test_version_consistency.py`：PASS。
- `git diff --check`：PASS。

## git diff --stat

命令原文（Git 不显示未跟踪文件）：

```text
 CHANGELOG.md                         | 10 ++++
 SKILL.md                             |  2 +-
 VERSION                              |  2 +-
 pyproject.toml                       |  2 +-
 references/analyze-workflow.md       |  4 ++
 references/scan-schemas.md           |  3 ++
 references/split-run.md              |  1 +
 scripts/report/audit_release_gate.py | 102 +++++++++++++++++++++++++++++++++--
 scripts/tests/run_all.py             |  3 ++
 9 files changed, 123 insertions(+), 6 deletions(-)
```

另有白名单内未跟踪新文件（交由 Fable 验收后提交）：

- `scripts/tests/test_batch15_three_ledgers_frozen.py`：415 行。
- `maintenance/repair-20260823-sqd-gap/batch15_red_evidence.txt`：38 行。
- `maintenance/repair-20260823-sqd-gap/batch15_done.md`：本报告。

## 完整 run_all

最终命令（仅在 shell 会话中把 matplotlib 缓存指到 `/private/tmp`，不改仓库或系统配置）：

```sh
python3 scripts/tests/run_all.py > /tmp/batch15_runall.txt 2>&1; echo rc=$?
```

结果：`rc=1`；`141 total / 139 PASS / 2 FAIL`。仅失败项：

- `test_batch3_solana_vertical_slice.py:625`：`ThreadingHTTPServer(("127.0.0.1", 0), ...)` → `PermissionError: [Errno 1] Operation not permitted`。
- `test_batch3_evm_vertical_slice.py:281`：同一 loopback bind → 同一 `PermissionError`。

两项都在 fixture server bind 阶段失败，尚未进入业务断言；不得称全绿，需在允许 localhost bind 的环境复跑。

`tail -n 30 /tmp/batch15_runall.txt` 原文：

```text
      PASS  test_repair_g1_text_hygiene.py PASS real repository: 349 tracked active files, zero hits
      PASS  test_evm_observation_nonempty_code.py PASS F-04 EVM nonempty code and ABI word checks: 5/5
      PASS  test_arbitrum_exploration_cli.py PASS F-10: exploration CLI execution + formal consumer isolation
      PASS  test_recon_deep_reverify.py PASS test_recon_deep_reverify
      PASS  test_gmgn_divergence_note.py PASS test_gmgn_divergence_note
      PASS  test_g3_docs_guards.py   PASS: F-05 machine boundary
      PASS  test_g3_alt_collectors.py SUMMARY: 13 passed, 0 failed, 0 skip-red
      PASS  test_collector_history.py PASS: every registry entry is git-verifiable
      PASS  test_v2_identity_history.py PASS: R-3 v2 historical identity maintenance/consumer parity
      PASS  test_anchor_plan_v3.py   anchor-plan v3: 15/15 PASS
      PASS  test_done_v4_collector.py PASS: U2 done/v4 collector + C12 recovery (24/24)
      PASS  test_csv_resume_collector_gate.py PASS: hash-wide REVOKED rejects current collector at startup
      PASS  test_sqd_coverage_probe.py PASS SQD coverage probe: 12/12 offline groups
      PASS  test_f03_sharedmap_reuse.py PASS F-03 shared-map reuse: 15/15 groups
      PASS  test_batch2d_stream_tail.py PASS batch2d SQD stream tail: 4/4 groups
      PASS  test_sqd_gap_repair.py   GREEN 29c implemented validate_current_candidates 已实现
      PASS  test_reconcile_v4_receipt.py GREEN 32 verdict/exit_code/gate_pass 三元互洽
      PASS  test_recon_fifth_check.py GREEN 22 wave-scan/v4 与 flow-anomaly/v2 旧产物被 v5/v3 验收拒收
      PASS  test_batch3c_census_fields.py PASS batch3c census fields match the SQD contract
      PASS  test_batch8_repair_scale.py PASS batch8: key-neutral identity/pool failover/ordered workers/resume
      PASS  test_batch7_validator_coverage_gaps.py 批7 validator 覆盖缺口加固回归全部 GREEN (缺口1遍历主键 + 缺口3边slot窗口)
      PASS  test_batch11_frozen_bundle_binding.py PASS batch11 frozen/live binding regressions
      PASS  test_batch12_frozen_supply_drift.py PASS: batch12 frozen supply drift contract
      PASS  test_batch13_accounting_target.py PASS batch13 accounting target regressions: 8/8
      PASS  test_batch14_accounting_bundle_fallback.py batch14 tests=9 failed=0
      PASS  test_batch15_three_ledgers_frozen.py PASS batch15 frozen consumers: 10/10
      PASS  test_lit_regression_f007.py SUMMARY: 15/15 PASS
      PASS  test_lit_regression_f008.py SUMMARY: 46/46 PASS
========================================================
2 项失败——修完再收工
```

## 盲审 R1 消化

### 结论与改动摘要

- 施工基线核对：开工 `git status --short` 为空；当前 `main@9ae8a0b` 的父提交是工单基线 `3a71c26`，唯一新增内容是调度方已提交的 `batch15_blind_r1_digest.md`。
- N5 删除“案内绝对 exact ref 通过”的夹具假绿，改用 N6 的完整动态两态案；篡改真实 `data/reconcile_receipt.json` 的 `inputs.holders_owners.path`，同步 wrapper 对该收据的 size/sha256 引用，再由未打补丁的 `gate.check_three_ledgers()` 进入真实 `validate_reconciliation_report()`。
- 案内绝对路径穿过 envelope 后由 `validate_reconcile_receipt_deep()` 的 case-relative 契约 fail-closed 拒绝；案外绝对路径由 envelope 案根约束拒绝。两种错误都包含“冻结态深验未通过”，且都不包含“不等值”，证明没有回落到观察 owners 的逐址比较。
- `_frozen_consumer_target()` 的深验失败文案改准为 `accounting as_of_block=…/wrapper …：冻结态深验未通过…`，未改控制流。
- `batch15_done.md` 与 `CHANGELOG.md` 同步生产契约及 codex 盲审 R1 1 条 P2（N5 假绿）消化结果；版本仍为 `6.53.1`。

### N5 真实 errors 原文

案内绝对路径：

```text
["三账 balance_source 对账源: accounting as_of_block=500/wrapper 501：冻结态深验未通过，无法确定对账时点: Solana exact_reconcile 独立深验失败: artifact path must be case-relative: '/private/tmp/batch15-n5-proof-odhzx3ju/data/holders_owners.json'; reconcile snapshot_supply_raw does not recompute; reconcile snapshot_mismatch_count does not recompute; reconcile snapshot presence/closure facts mismatch; gate_pass does not recompute from exact reconciliation; verdict/exit_code do not match recomputed gate_pass"]
```

案外绝对路径：

```text
["三账 balance_source 对账源: accounting as_of_block=500/wrapper 501：冻结态深验未通过，无法确定对账时点: reconciliation exact_reconcile receipt envelope invalid: input holders_owners invalid: input escapes case root；存量案例须重跑对应生产者获取当前回执"]
```

### 验收

- `python3 scripts/tests/test_batch15_three_ledgers_frozen.py`：PASS，10/10；N5 使用完整动态夹具和真实校验器，无 `fake_check` 补丁。
- `python3 scripts/tests/changelog_lint.py`：PASS。
- `python3 scripts/tests/docs_lint.py`：PASS，45 个文档。
- `python3 scripts/tests/run_all.py`：`rc=1`，141 total / 139 PASS / 2 FAIL。仅 `test_batch3_solana_vertical_slice.py:625` 与 `test_batch3_evm_vertical_slice.py:281` 在绑定 `127.0.0.1` 时触发 `PermissionError: [Errno 1] Operation not permitted`；均未进入业务断言，须由调度方在允许 loopback bind 的本机复跑。
- `git diff --check`：PASS。
- 未 commit，未改版本号，未读取或写入任何 key。

### 本轮 git diff --stat

```text
 CHANGELOG.md                                       |  4 +-
 .../repair-20260823-sqd-gap/batch15_done.md        | 47 +++++++++++++++++++++-
 scripts/report/audit_release_gate.py               |  4 +-
 scripts/tests/test_batch15_three_ledgers_frozen.py | 43 +++++++++++++-------
 4 files changed, 78 insertions(+), 20 deletions(-)
```

## 盲审 R2 消化

### 结论与改动摘要

- 施工基线核对：开工 `git status --short` 为空；当前 `main@cfbdfc6` 的直接父提交是工单基线 `345c9d5`，唯一新增内容是调度方已提交的 `batch15_blind_r2_digest.md`。
- `audit_release_gate.py` 新增 `_RUN_DEEP_CACHE`，键为 `case_dir.resolve()`，值为深验 `(checked_target, receipts)` 或捕获到的异常对象；缓存命中异常时执行 `raise cached`，重新抛出同一对象，不把失败改成豁免。
- `run()` 成为薄包装器：入口创建空缓存，`finally` 清为 `None`；原闸体移入 `_run()`，因此正常返回、profile 参数错误或任何未捕获异常都不会把缓存带到下次 `run()`。
- 跨分区冻结态投影、`check_reconciliation`、B-7 与 series 均走同一助手。`check_reconciliation` 的参数形态同为 `case_dir, return_receipts=True`，且深验本身无消费方特有副作用，因此接入缓存；其后的 `validate_solana_derived_bindings` 仍逐次执行，原错误语义不变。
- N9 首轮实测发现 `shared_release_receipt.validate_bundle()` 内部的 `validate_sources()` 还有一条同参数深验调用，盲审文字未列出该既有消费者。发布闸只在调用 `validate_bundle()` 的窄窗口把该同参数调用代理到当前 run 缓存，并在 `finally` 恢复原函数；带 `expected_target` 的 EVM 参数形态仍直调原函数，`shared_release_receipt.py` 零改动。
- 未改 `check_three_ledgers` 本体、EVM 分支、Solana 静态段、`_recon_owner_snapshot` 冻结分支或任何禁改文件；版本保持 `6.53.1`。

### N9/N10 计数与 errors 原文

N9（一次完整动态 `new-analysis` run）：

```text
calls=1
errors=[]
```

N10（同目录先绿跑、篡改 `data/holders_owners.json` 后再跑）：

```text
first_calls=1
first_errors=[]
second_calls=1
second_errors=["正式发布跨分区 target 不一致: as_of_block 声明矛盾: accounting_mode.json.as_of_block=500, reconciliation_report.json.target.as_of_block=501, shared_release_receipt.json.target.as_of_block=500, identity_bridge/data/identity_holders_receipt.json.as_of_block=500", "共享发布 receipt: observation bundle holder_outputs.owners sha256/size mismatch: holders_owners.json", "记账模型公共 validator 未通过: observation bundle holder_outputs.owners sha256/size mismatch: holders_owners.json", "受控对账公共深验失败: reconciliation exact_reconcile receipt envelope invalid: input holders_owners size mismatch；存量案例须重跑对应生产者获取当前回执", "发布期序列 cutoff 目标: accounting as_of_block=500/wrapper 501：冻结态深验未通过，无法确定对账时点: reconciliation exact_reconcile receipt envelope invalid: input holders_owners size mismatch；存量案例须重跑对应生产者获取当前回执"]
```

第二次 run 的真实深验计数为 1 且明确拒绝篡改，证明第一次绿结果没有跨 run 残留；同一第二次 run 内各消费者复用同一失败对象，errors 次序与文案保持 fail-closed。

### 验收

- `python3 scripts/tests/test_batch15_three_ledgers_frozen.py`：PASS，12/12；N9 `calls=1, errors=[]`，N10 两次 run 各 `calls=1` 且第二次拒绝篡改，并与缓存关闭的对照 `errors` 逐字相同。
- `python3 scripts/tests/test_repair_batch_d.py`：`BATCH D 全部通过`。
- `python3 scripts/tests/test_audit_release_gate.py`：PASS。
- `python3 scripts/tests/test_batch13_accounting_target.py`：PASS，8/8。
- `MPLCONFIGDIR=/private/tmp/batch15-r2-mpl-cache python3 scripts/tests/test_repair_batch_c.py`：PASS，227 checks。
- `python3 scripts/tests/changelog_lint.py`：PASS，版本号唯一且顺序正确。
- `python3 scripts/tests/docs_lint.py`：PASS，45 个文档；全套内 `docs_lint.py --all` 亦 PASS，59 个文档。
- `git diff --check`：PASS。
- `MPLCONFIGDIR=/private/tmp/batch15-r2-runall-mpl-cache python3 scripts/tests/run_all.py`：`rc=1`，141 total / 139 PASS / 2 FAIL。仅失败项为 `test_batch3_solana_vertical_slice.py:625` 与 `test_batch3_evm_vertical_slice.py:281`，均在 `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 绑定阶段触发 `PermissionError: [Errno 1] Operation not permitted`，未进入业务断言；故本轮状态为 PARTIAL，需调度方在允许 loopback bind 的本机复跑，不冒充全绿。
- 未 commit，未改版本号，未读取或写入任何 key。

### 本轮 git diff --stat

最终原文：

```text
 CHANGELOG.md                                       |  4 +-
 .../repair-20260823-sqd-gap/batch15_done.md        | 62 +++++++++++++++-
 scripts/report/audit_release_gate.py               | 83 ++++++++++++++++++----
 scripts/tests/test_batch15_three_ledgers_frozen.py | 54 ++++++++++++++
 4 files changed, 184 insertions(+), 19 deletions(-)
```
