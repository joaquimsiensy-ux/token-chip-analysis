# 工单T3复核：退回

**C 限目录案的修法成立，生产落点正确；v1 需要修正文案、测试指令和兼容范围后再施工。** 明确问题是：CHANGELOG 索引超出自身字节上限，symlink needle 前后矛盾，步骤 6 指向不存在的既有测试断言，以及遗漏共享发布收据因源码哈希变化而需重建的影响。

审查基线：`544e86486f0f0f79eeb1ca0405f7634f8fc14659`。工作树为空；`2197505` 是 HEAD 祖先，工单指定生产、测试及版本路径相对该提交无差异。未读取 `~/.codex/`、memories 或其他禁读材料；离线，未新建、修改文件，未 commit。未运行会创建夹具的测试；执行了整行锚检查、静态调用链核对和纯内存缓存探针。

下文“工单行号”均指 `workorder_T3.md` v1。

**a）锚与行号：通过**

逐项实际执行 `grep -n -F -x`，结果全部恰好一处，行号一致：

| 文件 | 已核行号 |
|---|---|
| `scripts/report/shared_release_receipt.py` | 39、1047、1055、1056、1057、1058、1059 |
| `scripts/tests/test_anchor_plan_v3.py` | 600 |
| `CHANGELOG.md` | 13、101 |
| `SKILL.md` | 23 |
| `pyproject.toml` | 15 |

施工前应一次核完基线锚，插入 import 后不能再要求后续锚仍处于旧行号。建议工单 **L16** 替换为：

> - 0.5 所有施工锚在首次修改前统一核验：目标文件整行原文以 `grep -n -F -x -- '<整行>' <文件>` 命中恰 1 处且基线行号一致，不符停工。修改后的行号允许随插入自然移动，完成报告记录实际 diff 行号。

**b）来源断言：主体成立，入口与缓存表述需精确化**

① **各正式 EVM 入口都会到达目录重算，但不是所有路径都依赖 witness。**

实际调用链：

- READY：`handoff_manifest.py:349` → `validate_reconciliation_report`。
- verify：`handoff_manifest.py:483` → 同上。
- EVM `validate_bundle`：`shared_release_receipt.py:2172` → `validate_sources:2122` → 同上。
- 发布闸对账检查：`audit_release_gate.py:543` → `_validate_reconciliation_report_once` → `witness_reconciliation_report:2068` → 同上。
- 随后均经 `validate_reconciliation_check:1421` → `_validate_time_receipt:1085` → `_validated_time_plan_authority`。

**缓存确实复用旧结果，但限同一次 `run()`。** `audit_release_gate.py:1833` 每次建立新缓存，`:1837` 在 `finally` 清空；缓存同时保存成功结果和异常。纯内存执行这两个真实函数，连续两次 `run()`、每次请求两遍，实得深验两次，每次内部复用同一结果，结束后缓存为 `None`。

另一个关键事实是：**EVM 的 `validate_sources:2120-2123` 无条件重新深验，不使用传入的 provider**；provider 分支属于 Solana。因此正常 EVM 发布闸包含两次目录完整重算。

witness 本身没有因此获得目录叶子的持续新鲜度保证：`:1895-1902` 明确只覆盖直接引用，`:2059-2061` 不打开引用的清单；签发后修改目录叶子，既有 witness 仍可能复用。对此：

- 对“修改发生在下一次 READY／verify／发布之前”的 FR-02，当前修法足够。
- 对“同一次发布执行中继续修改目录”或“长期保留 witness 后直接消费”，当前修法不提供新保证。
- **本单可以接受这个边界**，沿用既有单次运行缓存即可，不必扩展修改其他消费者。

工单 **L5** 建议替换为：

> > ① 正式 EVM READY、verify、validate_bundle 与发布闸均会通过 validate_reconciliation_report → _validate_time_receipt → _validated_time_plan_authority 到达目录分支。发布闸内 witness 深验按案根在单次 run() 内缓存，退出即清空；EVM validate_sources 不使用该 provider，另行深验。正常一次发布闸因此重算目录两次。此修复检查本次深验时的目录实物，不扩展 witness 对签发后目录叶子变化的保证。

② **身份形态相同。**

`anchor_selection.py:75-103` 返回 `(identity, files)`，其中 `identity` 恰为四键：

```text
path / kind / size / sha256
```

目录 `path` 来自 `expanduser().resolve(strict=True)`，是绝对路径；摘要包含排序后的相对叶子路径、大小和逐文件完整 SHA-256。`anchor_plan.py:148` 直接取该 dict，`:176`、`:195`、`:207` 分别写入 plan、manifest 和 receipt，没有改形态。

“案根未迁移即相等”应补上**目录内容未变、签名身份未经改写**的前提。真正搬移后，旧绝对路径通常会在更早的文件绑定检查或目录存在性／包含关系检查中被拒，不能保证错误一定发生在 `:1056-1059`。

工单 **L24** 括号内的身份说明建议替换为：

> path/kind/size/sha256 四键；生产期与消费期均使用 resolve 后绝对路径。同一物理路径、相同叶子集合和文件字节下，两次身份相等；实际搬移导致旧引用失效时，由既有文件绑定或目录存在性／案根包含检查拒绝，本单不新增迁移支持。

QUQ 的 **7.62 GB、61 文件、3.5 s、match_signed=True** 在允许读取的日志中存在；日志没有工单 L6 所写的精确字节数或完整身份。建议删除 L6 的括注，改为：

> （QUQ 的规模、耗时与身份相等结果见 T3_cost_quq_v2_identity.log；本单未展示该案完整身份。）

③ **import 无项目内循环。** `shared_release_receipt.py:21` 已把 lib 放入 `sys.path`；`anchor_selection` 的项目内依赖只有 `anchor_point_contract`，后者仅导入标准库 `json`。新增顶层 import 会引入 `duckdb`，该依赖已在 `pyproject.toml:20` 声明。

④ **`_require` 确实抛 `ValueError`。** 定义在 `shared_release_receipt.py:145-147`；目标函数外层 `:1080-1081` 还会统一添加 `time plan authority chain broken:` 上下文。

**c）修法定形与性能：接受落点，建议去掉重复异常包装**

支持本方案的最强理由成立：复用身份定义、完整读叶子并重新枚举集合，只改一个既有验证落点，就能覆盖这些正式入口。

反对意见主要是完整读盘成本、发布闸重复重算，以及不能扩大宣称 witness 的保证。源码与现有测量表明，这些不足以推翻用户已经选定的 C。

原六行插入可以工作，但**更短的两行等价实现更合适**。不在局部捕获 `ValueError`，最终错误仍有外层上下文，例如：

```text
time plan authority chain broken: input directory contains symlink: ...
time plan authority chain broken: input directory contains no regular files: ...
```

已足够定位问题。原包装也没有覆盖 `OSError`，并不增加该方面的保证。

建议工单 **L25** 替换为：

> - 1.3 重算放在 :1056-1059 既有目录检查之后；直接调用 input_identity 并全等比较。symlink、无普通文件等 ValueError 沿用本函数外层 authority-chain 上下文，不增加局部异常包装。

工单 **L49-54** 替换为：

```python
            _require(input_identity(directory)[0] == identity,
                     "time plan input directory content differs from signed identity")
```

这仍只改变目录块。原案和简化案均满足生产改动不超过 12 行。

按日志每次 **3.5 s** 线性估算：

| 正常成功路径 | 完整目录重算次数 | 新增读盘耗时估计 |
|---|---:|---:|
| 一次 `validate_reconciliation_report` | 1 | 约 3.5 s |
| 一次 READY | 1 | 约 3.5 s |
| 一次 verify | 1 | 约 3.5 s |
| 一次 EVM `validate_bundle` | 1 | 约 3.5 s |
| 一次 EVM 发布闸 `run()` | 2 | 约 7 s |
| READY → verify → 发布闸 | 4 | 约 14 s |

这是**新增目录哈希耗时**，不是命令总耗时；提前拒收时可能少于这些次数。缓存状态和存储速度也会影响结果。不得继续沿用裁决页“每次几分钟起”的旧估计。

**d）回归面：目录夹具无冲突；“文件行为不变”必须限定范围**

拟议新增块不进入文件分支，原 `:1036-1039` 及后续既有检查保持原文。内存中插入工单代码后，文件分支 AST 也一致。

但不能把它扩展为“所有文件案既有发布行为、产物字节都不变”：

**`shared_release_receipt.py` 自身也是生产者。** `create_bundle:2154` 把本文件 SHA 写入共享发布收据；`validate_bundle:2177-2179` 要求它与当前源码完全一致。修改此文件后，**目录案和文件案的旧 `shared_release_receipt.json` 都会报 `shared receipt producer mismatch`，需要重建**。这不要求重跑时间生产者，也不需要扩展生产改动面，但工单必须如实说明。

工单 **L23** 建议替换为：

> - 1.1 身份校验逻辑只改 kind=directory 块；文件分支 :1036-1039 与其后既有逻辑逐字不变，文件时间证据的校验顺序、放行/拒收和错误文本保持不变。修改本文件会改变共享发布收据的 producer.sha256；文件案与目录案的旧 shared_release_receipt.json 均须用现有 create_bundle 流程重建，不能据此声称共享发布产物字节不变。不得为兼容旧共享发布收据放宽校验。

指定夹具核对如下：

| 测试 | 实际输入及消费前变化 | 新增目录校验影响 |
|---|---|---|
| `test_16` | 真正目录夹具，经实际 `anchor_plan` 生成身份；输出位于 `root/plan`，不在 `v2` 内 | 正例叶子未改；反例在更早的绑定／清单正文检查拒收，预期不变 |
| `test_recon_deep_reverify` | `:162-199` 使用手工构造的 `kind=file` 身份 | 不进入新分支 |
| `test_handoff_manifest` | `:175` 调用 `write_deep_recon_fixtures`；该 helper `:102` 明确生成 `kind=file` | 不进入新分支 |
| `test_batch3_evm_vertical_slice` | `:156-162` 实际生产者读取 `transfers_evm.csv` | 不进入新分支 |

所以，不能说这些测试的 identity “全部由同一 `input_identity` 生成”；只有其中真实生产者路径如此。也没有发现目录夹具在正向消费前新增叶子而导致误拒的问题。

**`invariant_manifest` 无需登记。** 没有新 schema、生产者、消费者文件、正式入口、网络调用或原子写点；新增调用是既有消费者内部的身份计算。`contract_manifest` 同样无需新增入口。

**e）§2.2：六步基本足够，修正三处即可**

六步覆盖正常放行、同长度覆写、集合增加、集合减少、symlink、文件分支对照；无需扩大成新测试套件。

- **步骤 4 可行。** 将 `blocks.parquet` 移至 `root/blocks.bak`，确实移出了身份根 `root/v2`。仍有 logs 文件，因此会进入身份不等，而不是空目录异常。固定使用此方式更明确，也避免“root 外临时位置”可能跨文件系统导致 `rename` 失败。
- **步骤 5 原文不自洽。** 给出的 needle 不含 `symlink`，但括注要求包含；helper 只检查一个字符串子串。
- **步骤 6 的既有测试 needle 不存在。** 当前测试中没有 `time plan input identity` 这一断言；`test_time_spotcheck` 的 `input sha256 mismatch` 属于另一条语义重放路径，不能直接套用。使用 `_shared_authority` 时，输入引用会重新计算，随后旧签名 identity 在 `:1037` 被拒，准确文本为 `time plan input identity sha256 mismatch`。

采用上面的两行简化案后，工单 **L65-67** 建议分别替换为：

> 4. **删除叶子**：将 `source / "run_1" / "blocks.parquet"` rename 到同一案根下且预先不存在的 `root / "blocks.bak"`；调用消费者须以 `time plan input directory content differs from signed identity` 拒绝；移回原路径后再次放行。

> 5. **目录内 symlink**：创建 `run_1/link.parquet -> logs.parquet`；调用消费者须以既有 helper 的文本 `input directory contains symlink` 拒绝；删除该链接后再次放行。

> 6. **文件分支对照**：在已创建的独立 `root2` 中调用 `_produce_plan(root2, directory=False)`；先断言 `_shared_authority` 放行，再同长度翻转 CSV 末字节，断言既有生产错误文本 `time plan input identity sha256 mismatch`；恢复原字节后再次放行。不得修改文件分支生产错误文本，不刷新计划或收据。

如果保留原六行包装，步骤 5 的 needle 应明确写成：

```text
time plan input directory identity recompute failed: input directory contains symlink
```

**不需要补“消费期重算耗时不进收据”的断言。** 新增路径没有计时字段和写收据操作，相关生产者不变；这不是本单新增契约。也不必专门增加空目录、搬案或缓存机制的新回归来扩大范围。

不过，应在 L61 明确：`_ref` 由现有 helper 使用；本测试不需要 `_refresh_receipt`，不得为了让负例通过而刷新签名身份或输入清单。

**f）原则与版本：修版本合理；索引必须缩短**

references、commands 零改动，SKILL 只替换等长版本号，均可实现；当前 SKILL 为 **8021 B**。

**9.0.5 记“修”合适。** 它拒绝的是与既定签名身份不一致的目录证据，没有新 schema、键或公开接口。与 `CHANGELOG.md:16/:126-133` 的 9.0.1“既定契约内消费者加固”先例一致。共享发布收据需要按既有源码绑定规则重建，应登记影响，不必因此改档位。

工单 **L82** 拟插入行实测 **233 B，不含换行；含换行为 234 B**，违反 L27/L79 的 ≤200 B 硬约束。替换为以下原文：

```text
- **9.0.5**（2026-09-23）修复目录案消费期漏验：重算完整身份，拒叶子覆写、增删及 symlink（FR-02 C）；文件分支、schema 不变，档位 修。
```

替换行 **176 B，含换行为 177 B**。

工单 **L85** 的详细段要求应补入：

> 成本写明 QUQ 日志单次完整身份计算为 3.5 s，正常 verify 重算一次、EVM 发布闸两次，分别估计增加约 3.5 s／7 s；兼容范围写明文件时间校验分支不变，但所有旧 shared_release_receipt.json 因本文件 producer.sha256 改变须重建。

| 审项 | 判定 | 必要处理 |
|---|---|---|
| a 锚与行号 | 通过 | 全部唯一且准确；施工前统一核验 |
| b 来源与入口 | 修订后通过 | 说明 EVM 双重深验、单次运行缓存和 witness 边界 |
| c 修法定形 | 通过，建议简化 | 采用两行全等校验；去掉重复异常包装 |
| d 回归面 | 需修订说明 | 区分文件时间校验不变与共享发布收据必须重建 |
| e 六步测试 | 需修订 | 固定搬移位置，修正 symlink 与文件分支 needle |
| f 原则与档位 | 档位通过，字节退回 | 索引 233 B 缩至 176 B；详细段补成本与存量影响 |
| **总体** | **退回 v1** | **保留 C 限目录案及现有生产白名单，按上述文本修订** |
