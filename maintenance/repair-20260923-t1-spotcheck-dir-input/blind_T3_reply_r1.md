# 盲审T3：PASS

审对象：`0c58cd27d81d498401a4514044fcb1b837bf0188`；对照基线：`2197505`。a–e 均闭合，无真实 FAIL。

全程离线，未读取 `~/.codex/`、禁读历史材料或案卷；仅 `changelog_lint.py` 子进程按授权读取 archive。未修改或新建仓库文件，未 commit，临时夹具已清理。

**a）独立终点复现：通过**

自行创建包含 `run_1/{logs,blocks}.parquet` 的 v2 目录，调用真实 `anchor_plan.py --input <目录>` 生成计划、清单、收据；时间收据的 `inputs.input` 绑定清单。直接调用 `_validated_time_plan_authority`，未依赖新增测试的断言。

基线模块通过 `git show 2197505:scripts/report/shared_release_receipt.py` 获取并在内存执行，`__file__` 保持真实仓库路径，没有从临时文件加载被审模块。

| 情形 | 基线 | HEAD | 恢复后 HEAD |
|---|---|---|---|
| 原始目录 | 放行 | 放行 | — |
| 同长度翻转 `logs.parquet` 末字节 | 放行 | 拒收 | 放行 |
| 新增叶子 | 放行 | 拒收 | 放行 |
| 将 `blocks.parquet` 移至目录身份根外 | 放行 | 拒收 | 放行 |
| 目录内 symlink | 放行 | 拒收 | 放行 |

HEAD 四组完整错误文本，依次为：

```text
time plan authority chain broken: time plan input directory content differs from signed identity
time plan authority chain broken: time plan input directory content differs from signed identity
time plan authority chain broken: time plan input directory content differs from signed identity
time plan authority chain broken: input directory contains symlink: /private/tmp/t3-independent-ubneg4oi/directory/v2/run_1/link.parquet
```

完整入口采用 `test_handoff_manifest.make_case`，换入独立目录计划，经真实 `time_spotcheck.main()` 完成语义重放、13/13 抽查及收据产出，再运行交接 CLI。

loopback 状态：

```text
LOOPBACK SANDBOX-BLOCKED: PermissionError(1, 'Operation not permitted')
```

仅 RPC 池使用内存替身，按夹具转账计算余额及交易回执；未验证真实网络传输及链身份握手。计划、收据和发布消费者的验证逻辑没有替换；交接使用测试已有的 formal harness。

原始目录：READY、verify 均 exit 0。覆写叶子后，两条入口均 exit 2，完整拒收文本：

```text
[generate] reconciliation READY 深验失败: time plan authority chain broken: time plan input directory content differs from signed identity
```

```text
[verify] FAIL（fail-closed，逐条修复或退回 −1）:
  ✗ reconciliation/accounting 公共深验失败: time plan authority chain broken: time plan input directory content differs from signed identity
```

恢复叶子后 verify 再次 exit 0。

**b）文件分支：通过**

CSV 原始输入及恢复后，HEAD 与基线均放行。以下反例逐字比较结果一致；同时设置多个错误后逐项解除，确认拒收顺序一致：

| 情形 | 两版本一致的完整错误 |
|---|---|
| 同长度覆写，保留旧时间输入引用 | `time plan authority chain broken: time merged input sha256 mismatch` |
| 同长度覆写，刷新时间输入引用、保留原签名身份 | `time plan authority chain broken: time plan input identity sha256 mismatch` |
| 长度变化，刷新时间输入引用 | `time plan authority chain broken: time plan input identity size mismatch` |
| plan、receipt、input 同时哈希错误 | `time plan authority chain broken: time plan sha256 mismatch` |
| 解除 plan 错误 | `time plan authority chain broken: time plan receipt sha256 mismatch` |
| 再解除 receipt 错误 | `time plan authority chain broken: time merged input sha256 mismatch` |
| 再解除 input 错误，保留 target 错误 | `time plan authority chain broken: signed target differs from time receipt target` |

**c）修法：通过**

以基线文本施加工单指定替换后，与 HEAD 整文件逐字相等：

- 新增一行 `from anchor_selection import input_identity`。
- 订正基线 `:1047` 注释。
- 目录分支末尾新增两行身份 dict 全等校验。
- 无局部异常包装，无其他生产改动，合计 `+4/-1`。

`anchor_selection.py`、`receipt_kernel.py`、`receipt_validate.py`、`time_spotcheck.py`、`anchor_plan.py`、`handoff_manifest.py`、`audit_release_gate.py` 均与基线字节一致。

**d）白名单、字节及版本：通过**

指定范围的 `git diff --stat 2197505 HEAD`：

```text
 CHANGELOG.md                             |  8 +++++
 SKILL.md                                 |  2 +-
 VERSION                                  |  2 +-
 pyproject.toml                           |  2 +-
 scripts/report/shared_release_receipt.py |  5 ++-
 scripts/tests/test_anchor_plan_v3.py     | 58 ++++++++++++++++++++++++++++++++
 6 files changed, 73 insertions(+), 4 deletions(-)
```

- `references/**`、`commands-staging/**` 零改动。
- `references` Markdown 文档合计：`929085 → 929085 B`。该数字不是包含 CSV、图片等资产的全目录大小；通过 Git 对象大小元数据核验，未读取 `attic.md` 正文。
- `commands-staging`：`8789 → 8789 B`。
- `SKILL.md`：`8021 → 8021 B`，仅版本号变化。
- 四处版本登记均为 `9.0.5`。
- CHANGELOG 索引正文为 `176 B`，不含换行；详细段包含成本、旧共享收据重建要求及保证边界。

**e）指定实跑：全部 exit 0**

均以 `python3 -B scripts/tests/<文件>` 执行，并将缓存、临时目录置于仓库外。结果尾行：

```text
test_anchor_plan_v3.py:
anchor-plan v3: 17/17 PASS

test_time_spotcheck.py:
time_spotcheck 契约测试全部通过（20 项）

test_recon_deep_reverify.py:
PASS test_recon_deep_reverify

test_handoff_manifest.py:
handoff_manifest 契约测试全部通过（283 项）

test_audit_release_gate.py:
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过

test_batch4_invariant_guards.py:
PASS B4-G1: bare pool / labels / vertical slice / denominator injections

test_exemption_guards.py:
PASS: exemption guards (EX-01 full-F-03)

invariant_scan.py:
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0

changelog_lint.py:
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 84 条 + 归档 139 条
```

测试中的预期负例诊断及 `INJECT … RED` 均未导致测试失败。

**f）结论**

基线缺陷已复现；HEAD 四组目录反例全部拒收且恢复放行，READY 和 verify 完整入口均确认拒收。文件分支、指定修法、白名单与版本字节约束全部通过，符合 PASS 判据。

结束时 `git status --short` 全文如下，输出为空：

```text
```
