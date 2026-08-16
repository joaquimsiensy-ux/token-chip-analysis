# 批 1 步骤 1 施工报告：RV-07 真 FAIL 收据落盘死锁

施工范围仅限已批准计划的 RV-07。未执行任何 git 命令；未施工批 1 后续步骤。

## ① 不变量

合法的真 FAIL（`verdict=FAIL` 且 `exit_code=2`）必须能成为 canonical 收据。旧 PASS 只能在以下条件全部成立时让位：新载荷是合法 FAIL/2；旧件是 PASS；新旧 `target` 完全相等；新旧 schema 均属于调用出口显式声明的同一允许家族。旧 PASS 先以同目录 hard-link 归档为 `<canonical>.superseded-<UTC微秒>.<PID>`，再以 staged+fsync 的新 FAIL 原子替换 canonical；canonical 全程不存在缺失窗口。普通 `publish_overwrite` / `publish_txn` 的 `_reject_pass_downgrade` 调用和拒绝语义保持原样，无归档直接 PASS→FAIL 仍拒绝。

`publish_supersede` 的七条规格已逐项落实：

1. 入口只接受一致的 FAIL/2 Mapping，并检查新 schema 家族与 target 三键。
2. 归档旧件前要求旧 verdict=PASS、新旧 target 全等、新旧 schema 同属显式家族；不匹配时 canonical 字节不变且零归档。
3. 新 FAIL 先写同目录临时件、flush、文件 fsync。
4. 先 hard-link 旧 canonical 为唯一归档，再 `os.replace` staged FAIL；replace 失败撤归档 link，撤 link 也失败则保留并指认可恢复归档。
5. 归档名复用 `_run_id()` 的 UTC 微秒＋PID；碰撞不覆盖，直接 fail-closed。
6. 同 canonical 的 supersede 使用 O_EXCL 非阻塞锁；并发或中断遗留锁均显式拒绝，并在归档前、replace 前复核 canonical identity 未变化。
7. 归档 link、canonical replace、回滚和锁释放后均补父目录 fsync。

`window_fetch` 的 FAIL 多文件顺序单独闭合：

1. partial 完整 flush+fsync；gaps 先写唯一的 `*.gaps.json.failed-<run_id>` 审计证据，FAIL receipt 绑定该不可变文件，不提前改旧 PASS 所绑定的 canonical gaps。
2. 若旧正式 window 数据在场，先为它创建 `.stale.<run_id>` hard-link，但不删除 data canonical；所以旧 PASS 仍在时，它引用的数据始终在原位。
3. 调用 `publish_supersede` 切换 receipt；失败则逐件撤销 data archive link 与本轮 gaps evidence，并 fsync 目录，旧 data、旧 PASS receipt、旧 canonical gaps 均保持原字节。
4. receipt 已成为 FAIL 后才校验 data canonical/归档 inode 未并发变化、删除 data canonical，并更新操作员可见的 canonical gaps。即使后续清理失败，canonical receipt 已是 FAIL，不会出现“旧 PASS 在场而引用数据已移走”的混合状态。

## ② 同族 rg 清单与查证结论

执行命令：

```text
rg -n "def publish_(exclusive|overwrite|supersede|txn|restore_on_fail)|publish_supersede\(|invalidate_stale_receipt\(" scripts --glob '!scripts/tests/test_repair_batch1.py'
```

输出摘要：kernel 五原语分别位于 `receipt_kernel.py`；五个批准的真 FAIL 出口全部命中新原语：

- `scripts/lib/supply_truth_gate.py`：1 处；policy reject 仍单独调用参数化 `invalidate_stale_receipt(..., schema_family=...)`。
- `scripts/evm/verify_recon.py`：1 处。
- `scripts/lib/time_spotcheck.py`：2 处（target 不一致早退、最终 mismatch）。
- `scripts/solana/window_fetch.py`：1 处（gaps FAIL 分支）。

剔除面复核：`window_fetch.py` 的 gaps list 载荷仍走普通 overwrite；PASS 分支仍走 `publish_txn`；`scan_token_accounts.py` 各 PASS 件、`anchor_plan.py` RawBytes/无 verdict、无生产调用方的 `publish_restore_on_fail` 均未接入 supersede。

执行命令：

```text
rg -n "supply_truth\.json|time_spotcheck\.json|window_receipt|evm-reconciliation-receipt|time-spotcheck|solana-window-fetch-receipt" scripts references
rg -n "glob\(|rglob\(" scripts/report scripts/lib scripts/evm scripts/solana | rg "receipt|supply_truth|time_spotcheck|window"
```

查证结论：正式消费者均以 canonical 精确文件名读取（如 `handoff_manifest.py` 的 `supply_truth.json` / `time_spotcheck.json`、shared release receipt 的精确 schema）；第二条现役生产代码搜索未发现以 receipt/superseded 通配符消费归档件的路径。`.superseded-*` 与 run-specific failed gaps 只作审计证据，不自动清理，也不会混入 canonical 消费面。

同步面查证：

```text
rg -n 'CT-SEMANTIC-56|supply_truth.json.superseded-' scripts/tests/contract_manifest.json references/analyze-workflow.md
```

结果：`contract_manifest.json` 的 `CT-SEMANTIC-56` 仍登记 needle `supply_truth.json.superseded-`，`references/analyze-workflow.md` 仍含该 needle；真 FAIL 的 exit 2、hard-link 归档及微秒+PID 语义已同步。`supply_truth_gate.py` 模块 docstring 已同步真 FAIL 归档语义。`invariant_scan.py` 的 `success_primitives` 已登记 `publish_supersede`；`invariant_manifest.json` 新增 `supersede_single` atomic locator，minimum count 从 38 调为 39。

## ③ 三件套测试与先红后绿实跑证据

### a. 原反例：先红后绿

修复前先建立 `scripts/tests/test_repair_batch1.py`，用真实 supply producer 制造“旧 PASS 在场→本轮真实供给不闭合”。首次红测：

```text
$ python3 scripts/tests/test_repair_batch1.py
exit 1
AssertionError: (1, '[supply_truth] receipt 写入失败: existing PASS artifact cannot be downgraded: /private/tmp/.../supply_truth.json\n')
```

为让旧磁盘终态也成为可重放证据，修后测试还以注入方式把 producer 临时切回旧 `publish_overwrite` 路径，实跑输出：

```text
RV07 LEGACY_INJECTION rc=1 canonical=PASS archives=0 error=existing_PASS_cannot_be_downgraded
```

同一测试解除注入、走新原语后的实跑输出：

```text
RV07 FIXED rc=2 canonical=FAIL archives=1 archived_verdict=PASS
PASS v6.41.0 batch1 step1 RV-07
```

因此原反例由“通道故障 exit 1＋磁盘仍 PASS＋零归档”变为“业务 FAIL exit 2＋canonical FAIL＋旧 PASS 一份归档”。归档 inode 也在测试中核对为旧 canonical inode，证明归档确为 hard-link，不是重写副本。

### b. 同族变体：七条反例矩阵

均在 `test_repair_batch1.py` 的 RV-07 分节实跑：

| 反例 | 预期与实测断言 |
|---|---|
| stage 失败 | 无 canonical 改写、无归档、异常上抛 |
| 建归档 link 失败 | 旧 PASS 字节不变、零归档、异常上抛 |
| 新 FAIL replace 失败 | 旧 PASS 原位、刚建 archive link 被撤销 |
| replace 后撤 link 也失败 | 旧 PASS 原位、可恢复 archive 保留，异常文字指认完整路径 |
| 归档名碰撞 | 不覆盖碰撞件、不改 canonical、fail-closed |
| PASS→FAIL→PASS→FAIL 快速循环 | 两份不同 `_run_id()` 归档均为 PASS，canonical 为第二次 FAIL |
| 旧件 target 或 schema 家族不同 | 两个变体均拒绝，零归档，canonical 字节不变 |

另补：非法 PASS、矛盾 FAIL/1 载荷拒绝；同 canonical 锁占用时 supersede 与普通 overwrite 均拒；schema-family 参数化 invalidation 可归档 `time-spotcheck/`，但不误伤 `other/v1`。

### c. 失败分支：window 多文件事务注入

测试先产真实 PASS receipt/data/gaps，再让新一轮扫描得出真 FAIL，并在 data stale hard-link 已准备后注入 `publish_supersede` 失败。实测 producer 返回 exit 1；断言旧 data、旧 PASS receipt、旧 canonical gaps 三者逐字节不变，且无 `.stale.*`、无本轮 `.gaps.json.failed-*` 泄漏。解除注入后同一场景返回 exit 2，canonical receipt=FAIL，旧 PASS receipt 与旧 data 分别留下 superseded/stale 归档。

### 保持红四守卫

未修改以下既有断言；逐一通过对应脚本实跑：

- `test_batch1_receipt_paths.py:87-95`：无归档普通 PASS→FAIL 仍拒且字节不变，脚本 exit 0。
- `test_repair_batch_d.py:627-651`：policy reject 归档且不误伤，脚本 exit 0。
- `test_repair_batch_d.py:1315-1325`：参数错误不归档，脚本 exit 0。
- `test_sixlens_receipts.py:255-264`：写入炸时不留/不改正式产物，脚本 exit 0。

## ④ 新建代码六视角①②自审结论

### ① 字段来源审计

- 新 FAIL 的 verdict/exit_code、schema、target 来自 producer 已 finalize 的内存 receipt；kernel 不接受调用者用单独布尔开关声明“可 supersede”，而是直接读取并校验将落盘的载荷。
- 旧 verdict/schema/target 从 canonical 实物重新解析；归档前后以 stat identity 检查 canonical 未并发变化。
- window 的 gaps、partial、旧 data 都来自本次扫描或磁盘实物；FAIL receipt 通过 `build_envelope` 对唯一 gaps evidence 与 partial 做 path/size/sha256 绑定，没有用手填哈希冒充。
- 归档 run id 复用 kernel `_run_id()`；未新造第二套时间命名器。

结论：未发现关键准入字段依赖调用者自报且无法离线重验的路径。

### ② 失败分支审计

- payload/schema/target 不合法、旧 PASS 身份不匹配、stage/link/replace/fsync/锁冲突均 fail-closed。
- replace 前失败保持旧 canonical；replace 失败撤 link；撤 link 失败保留并指认可恢复归档；父目录 fsync 失败尝试原子恢复旧 PASS，恢复失败同时保留新 canonical 与旧归档并报混合状态。
- 普通 overwrite/txn 的 PASS 降级拒绝未放宽；新原语的并发锁与 identity 复核只增加 fail-closed 拒绝，不形成 warning 后继续成功。
- window 在 receipt 切换前的失败会回滚前置 hard-link/evidence；receipt 切换后的失败最多留下 FAIL canonical 加可审计数据，不会回到旧 PASS 混合态。
- ERROR 仍走唯一 side receipt，不覆盖 canonical。

结论：七矩阵与 window 专门注入均覆盖到目标失败分支；未发现 warning 后装成功或把真实 FAIL 误报为 exit 1 的残留路径。

## ⑤ 归因预判确认

确认归因：**修复中新引入（新引入）**。6.36.0 将 PASS→非 PASS 保护普遍化到普通 publish 原语时，只验证了“不得无归档降级”，没有验证合法真 FAIL 重跑必须落盘；五 producer 的 except 又把 kernel 拒绝统一解释为通道故障 exit 1，形成永久重跑死锁。

最强替代解释是“老问题修复不全”：该缺陷确实长在一次保护性修复之后。但旧不变量“无归档直接降级必须拒绝”在原入口已闭合且四个保持红守卫持续证明；本次故障是 repair diff 新造成合法生产路径不可执行，符合唯一事实源对“修复中新引入”的定义，不按半修残留归因。对应流程动作是：新建/改写 publication primitive 必须做六视角①②自审，并把业务 FAIL 重跑加入反例矩阵，不能只测恶意降级。

## 改动文件清单

- `scripts/lib/receipt_kernel.py`：新增 `publish_supersede`、同 canonical supersede 锁、父目录 fsync 与回滚诊断。
- `scripts/lib/supply_truth_gate.py`：真 FAIL 接入新原语；`invalidate_stale_receipt` schema 家族参数化；docstring 同步。
- `scripts/evm/verify_recon.py`：真 FAIL 接入新原语，保留 FAIL exit 2。
- `scripts/lib/time_spotcheck.py`：两个真 FAIL 出口接入新原语。
- `scripts/solana/window_fetch.py`：FAIL receipt/data/gaps 安全提交顺序与失败回滚。
- `scripts/tests/test_repair_batch1.py`：新建批测试文件，RV-07 原反例、七矩阵、并发/参数化与 window 注入。
- `scripts/tests/run_all.py`：文件末尾新增 `v6.41.0 批1 步骤1 RV-07` SUITE 块。
- `scripts/tests/invariant_scan.py`：登记 `publish_supersede` success primitive 与 `supersede_single` 语义。
- `scripts/tests/invariant_manifest.json`：登记新 atomic locator/minimum。
- `references/analyze-workflow.md`：同步 exit 2 真 FAIL 与 supersede 归档语义。
- `maintenance/repair-20260814-batch1/step1_rv07_report.md`：本报告。

`scripts/tests/contract_manifest.json` 未修改；`CT-SEMANTIC-56` 的 superseded needle 已确认仍在场。

## 验证命令与结果

最终指定验证均在本 worktree 实跑：

| 命令 | exit | 关键末行/结论 |
|---|---:|---|
| `python3 scripts/tests/test_repair_batch1.py` | 0 | `PASS v6.41.0 batch1 step1 RV-07`；含 legacy 注入 rc=1 与 fixed rc=2 两条证据 |
| `python3 scripts/tests/test_batch1_receipt_paths.py` | 0 | `PASS B1-A receipt paths: ... PASS protection` |
| `python3 scripts/tests/test_repair_batch_d.py` | 0 | `BATCH D 全部通过`；同时覆盖两条指定守卫 |
| `python3 scripts/tests/test_sixlens_receipts.py` | 0 | `PASS: 六视角批①结构化回执与 fail-closed` |
| `python3 scripts/tests/test_receipt_kernel.py` | 0 | `PASS receipt kernel: golden + target/hash/disk/concurrency/error/path/txn/restore faults` |
| `python3 scripts/tests/invariant_scan.py` | 0 | `PASS invariant manifest: receipt_producers=54, receipt_consumers=63, transport_calls=62, atomic_writes=47, formal_entrypoints=58, exceptions=0` |

附加同步验证：

| 命令 | exit | 关键末行/结论 |
|---|---:|---|
| `python3 -m py_compile`（六个修改 Python 生产/测试文件） | 0 | 无语法错误 |
| `python3 scripts/tests/docs_lint.py --all` | 0 | `PASS: 58 个文档，引用无断链、粗体配对完整` |
| `python3 scripts/tests/test_contract_routes.py` | 0 | `PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合` |
| `python3 scripts/tests/test_supply_truth_gate.py` | 0 | `supply_truth_gate 形态①/②离线契约测试全部通过` |
| `python3 scripts/tests/test_time_spotcheck.py` | 0 | `time_spotcheck 契约测试全部通过（20 项）` |

本步骤不执行全量 `run_all.py`：批准计划把全量 suite 放在批 1 最终合并快照统一收尾；本步已将新测试手动挂入 SUITE，并完成用户为步骤 1 指定的全部实跑项。
