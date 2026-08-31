# 批 18 完工报告：四条裁决落地 → 6.54.0

## 结论

代码、文档、台账与版本面已按用户 2026-08-30 裁决 1B/2A/3A/4A 落地。定向测试与除沙箱 loopback 外的全量套件均通过；最终状态为 **PARTIAL（实现完成，环境验收尚有两项 localhost bind EPERM）**，不是“全绿”。未 commit、未联网、未读取或写入任何 key、未改案卷目录。

- 开工 HEAD：`532a05408179`
- 开工版本：`6.53.5`
- 交付版本：`6.54.0`
- 开工 `git status --short`：空
- 最终 suite 登记数：145（143 → 145）

## ② manifest 反绑产物豁免

- `CONTRACT_FILES` 移除案根 `provenance_ledger.json`，但已有账本仍经统一 discover 入口输出可见跳过提示。
- 新增 `_reverse_bound_reason(case_dir, rel)`：仅按规范相对路径与内容识别案根账本，以及非案根 `stage=final` 且带 `input_binding.handoff_manifest` 的分布扫描；案根 initial `distribution_scan.json` 保留并继续作为 READY 必备件。
- discover/data_map 走 `add_path`：先做 `safe_case_file` containment/symlink 校验，再对反绑产物打印 `[generate] 跳过反绑产物 ...` 并跳过。
- `--include`/`--gate` 共用 `add_explicit`：反绑产物统一打印 `[generate] 反绑产物禁止进入 manifest: ...` 并 exit 2；不会退化成“产物不存在”。
- verify 的旧 manifest 哈希重验、freeze 前置、entity_freeze、check-unseal、A5、`entity_source_trace.py`、`holder_distribution_scan.py` 均未放宽或修改。
- 文档已登记 freeze 前一次重跑即可收敛，以及 freeze 后必须连锁重跑 trace → freeze revision → 受影响 A4/final scan/A5。

## ③ 共享校验器接口转正

- `_bound_case_ref` 转为公开 `bound_case_ref`，旧名保留为同对象别名；发布闸不再导入私有名。
- 新增 frozen dataclass `DeepReconciliationWitness` 与唯一构造入口 `witness_reconciliation_report`，记录 resolved 案根、wrapper sha256、target、receipts。
- `validate_sources`/`validate_bundle` 新增 keyword-only `reconciliation_provider=`；仅 Solana 分支在原深验位置惰性调用，校验 witness 类型、案根与当前 wrapper sha。EVM expected-target 路径仍真跑深验。
- 发布闸缓存值改为 witness，三个既有消费点取 `witness.target/witness.receipts`；删除运行时替换 `shared_release_receipt.validate_reconciliation_report` 及 finally 还原逻辑。
- provider 异常仍由 `validate_bundle` 原 `except` 收口，闸层前缀保持 `共享发布 receipt: `。
- 兼容两类既有加载夹具：无 `sys.modules` 登记的 importlib loader 使用运行时类型字典声明 dataclass 字段；纯函数 monkeypatch 深验且不落 wrapper 的批 13 夹具记录空指纹哨兵。真实 validator 仍先要求 wrapper 实物，provider 消费仍将空哨兵判为无效，不形成生产旁路。

## ④ 版本规则文字

- `CHANGELOG.md` 与 `references/retrospective.md` 已统一为：主版本=不兼容边界变更；次版本=向后兼容新能力/公开接口/持久化契约扩展；修订号=既定契约内修复、加固、回归与文档。
- `references/retrospective.md` 既有“次版本逢 0/5 整编”规则及 CHANGELOG 6.53.0 历史句未改。
- `VERSION`、`pyproject.toml`、`SKILL.md` 注释、CHANGELOG 索引与 6.54.0 六栏详情已同步。
- 升次版本理由已写入“设计与实现”：manifest 收录契约的向后兼容变化＋共享校验器新增公开接口。

## ① R10-28 登记

- 台账第五节新增 R10-28，按裁决正文写“接受在案”，不写非法状态载体。
- 守卫期望 ID 集合 `range(1, 28)` → `range(1, 29)`，仅改该常量。
- 唯一现役声明更新为 `27 − 15 + 1 = **13**`；追加 2026-08-30 落账说明。
- CHANGELOG 6.54.0 末栏登记“R10-28 接受在案（用户 2026-08-30 裁决）”。

## 先红后绿证据

完整基线证据见 `maintenance/repair-20260823-sqd-gap/batch18_red_evidence.txt`，写入时尚未修改任何生产文件。

共享接口 R1 修前原文（rc=1）：

```text
FAIL test_r1_validate_bundle_accepts_provider_keyword: TypeError: validate_bundle() got an unexpected keyword argument 'reconciliation_provider'
FAIL batch18 shared bundle witness: 1/1
```

manifest R1 修前核心原文：第二次显式 `--run-id B` generate 后重跑 trace，verify/freeze 均 rc=2：

```text
[verify] FAIL（fail-closed，逐条修复或退回 −1）:
  ✗ 哈希/大小漂移: provenance_ledger.json
[freeze] handoff verify 未通过——禁止冻结（fail-closed）:
  ✗ 哈希/大小漂移: provenance_ledger.json
```

修后 R1：共享 1/1 PASS；manifest 1/1 PASS，verify rc=0、freeze rc=0，`entity_freeze.provenance_ledger_sha256` 等于当前账本 sha256。

## 新增 N 系列原文

```text
PASS test_r1_validate_bundle_accepts_provider_keyword
PASS test_n1_public_alias_and_no_runtime_replacement
PASS test_n2_dynamic_provider_and_default_each_deep_validate_once
PASS test_n3_evm_ignores_solana_provider_and_still_deep_validates
PASS test_n4_forged_stale_and_throwing_providers_fail_closed
PASS test_n11_gate_errors_are_byte_for_byte_unchanged
PASS batch18 shared bundle witness: 6/6
```

```text
PASS test_r1_two_generates_then_trace_converge_before_freeze
PASS test_n1_ledger_is_skipped_with_visible_notice_and_ready_preserved
PASS test_n2_explicit_include_and_gate_reject_reverse_binding
PASS test_n3_tampered_ledger_still_blocks_freeze
PASS test_n4_legacy_manifest_ledger_binding_still_verifies_hash
PASS test_n5_final_distribution_is_skipped_but_initial_remains_required
PASS test_n6_same_basename_without_final_binding_is_included
PASS batch18 manifest stage2 loop: 7/7
```

## N11 改前/改后 errors 逐字对照

`reconciliation_report.json` 追加换行：

```json
["共享发布 receipt: shared receipt input hashes changed"]
```

`data/holders_owners.json` 改为 61/39：

```json
["正式发布跨分区 target 不一致: as_of_block 声明矛盾: accounting_mode.json.as_of_block=500, reconciliation_report.json.target.as_of_block=501, shared_release_receipt.json.target.as_of_block=500, identity_bridge/data/identity_holders_receipt.json.as_of_block=500", "共享发布 receipt: observation bundle holder_outputs.owners sha256/size mismatch: holders_owners.json", "记账模型公共 validator 未通过: observation bundle holder_outputs.owners sha256/size mismatch: holders_owners.json", "受控对账公共深验失败: reconciliation exact_reconcile receipt envelope invalid: input holders_owners size mismatch；存量案例须重跑对应生产者获取当前回执", "发布期序列 cutoff 目标: accounting as_of_block=500/wrapper 501：冻结态深验未通过，无法确定对账时点: reconciliation exact_reconcile receipt envelope invalid: input holders_owners size mismatch；存量案例须重跑对应生产者获取当前回执"]
```

两组数组在改前基线与改后断言中逐字全等；正常动态案 `gate.run(profile="new-analysis") == []`。

## 既有回归

- 批 15：12/12 PASS；N9 `calls==1`、N10 两次 run `calls==2` 且 cached/uncached errors 逐字一致。
- `test_r9_batch3_release_guards.py`：6/6 PASS。
- `test_reconcile_v4_receipt.py`：PASS。
- `test_repair_batch1.py`：PASS。
- `test_repair_batch_d.py`：BATCH D 全部通过。
- `test_handoff_manifest.py`：68 项全部通过。
- `test_repair_g1_handoff_containment.py`：16/16 PASS。
- `test_lit_regression_f008.py`：46/46 PASS。
- `test_batch13_accounting_target.py`：8/8 PASS。
- `changelog_lint.py`、`docs_lint.py --all`、`test_version_consistency.py`、`test_repair_batch3_gates.py`：全部 PASS。

施工中两次既有回归拦截均按真缺陷处理：data_map 改走 `add_path` 后遗漏 containment，已把 `safe_case_file` 前置并恢复 16/16；witness 对纯函数夹具强取不存在的 wrapper sha，已加仅夹具可达的空哨兵兼容并恢复 batch13 8/8。未修改任何既有测试断言。

## 全量 run_all（沙箱）

命令：

```text
MPLCONFIGDIR=/private/tmp/batch18-mpl python3 scripts/tests/run_all.py
```

最终真实结果：145 total / 143 PASS / 2 FAIL / rc=1。两项失败均在业务断言前被当前沙箱禁止 loopback bind：

```text
test_batch3_solana_vertical_slice.py:625
server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
PermissionError: [Errno 1] Operation not permitted

test_batch3_evm_vertical_slice.py:281
server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
PermissionError: [Errno 1] Operation not permitted
```

除上述两项外，143 项全部 PASS；新 suite 两项与 batch13 均出现在最终全量汇总中并通过。因此代码验收面完成，但沙箱全量验收状态必须记为 PARTIAL，须在允许 localhost bind 的环境复跑后才能声称全绿。

## diff 与白名单复核

写本报告前 `git diff --stat` 原文（Git 默认不计 untracked 新文件）：

```text
 CHANGELOG.md                                      | 12 ++++-
 SKILL.md                                          |  2 +-
 VERSION                                           |  2 +-
 maintenance/repair-20260813-sixlens/r10_ledger.md |  4 +-
 pyproject.toml                                    |  2 +-
 references/retrospective.md                       |  2 +-
 references/scan-schemas.md                        |  2 +
 references/split-run.md                           |  1 +
 scripts/report/audit_release_gate.py              | 37 ++++++--------
 scripts/report/handoff_manifest.py                | 42 +++++++++++++++-
 scripts/report/shared_release_receipt.py          | 60 ++++++++++++++++++++---
 scripts/tests/run_all.py                          |  6 +++
 scripts/tests/test_repair_batch3_gates.py         |  2 +-
 13 files changed, 137 insertions(+), 37 deletions(-)
```

另有本工单白名单内 untracked 新文件：两份 batch18 测试、`batch18_red_evidence.txt` 与本报告。`git diff --check` PASS。`git diff --name-only` 未出现 `entity_source_trace.py`、`holder_distribution_scan.py`、`solana_exact_validate.py`、`state_from_facts.py`、`camp_series_provenance.py`、`entity_identity_gate.py` 或任何案卷目录；无白名单外改动。
