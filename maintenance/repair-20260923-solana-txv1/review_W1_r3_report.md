# 复核 W1 r3: 退回

v3 已吸收 r2 的大部分修订，**候选前缀检查与当前生产者的并发写入顺序一致，不构成退回理由**。剩余问题主要是：跨卷复制仍可能留下阻止重跑的半文件；证据目录同步不完整；§4 缺少认领台账提交后的恢复向量，部分夹具构造还需写清。

本次只读复核：分支 `fix/solana-txv1`，HEAD `6928bce`；所核生产及测试文件相对 `813ca6d` 无差异，起止工作区均干净。未改文件、未 commit，未读取三个禁读目录。执行了抽取源码函数的纯内存验证，未运行会创建文件的测试，也未跑 `run_all.py`。

用户真正要解决的是：升级请求版本后，保留前代已完成工作的证据身份，并能可靠续跑。支持 v3 的最强依据是，现有产物足以重建摘要，现有发布原语也能原子提交台账；反对直接施工的最强依据是，**台账原子提交尚未覆盖证据复制的中断恢复**。关键变量是中断发生在哪个阶段，而非是否使用硬链接。

**一、r2 修订清单 1–8**

| 项 | 结论 | 核对结果 |
|---|---|---|
| 1. 来源可信措辞 | **落实** | §2.1、§5 均改为输入前提，未再将目录归属或深验称为来源真实性证明。 |
| 2. 全部目标冲突预验、零落盘定义 | **落实** | §2.3 第 5 步明确在首个 link/copy 前检查全部采纳目标；§4 改为失败前后目标状态不变。该状态应明确限于认领目标，见下文 ERROR 回执说明。 |
| 3. 原子 ledger、目录同步、恢复边界、EXDEV | **落实所列修订** | `publish_exclusive + RawBytes`、`_fsync_dir(pending)`、提交前后恢复方式及仅 EXDEV 回退均已写入。但复制分支仍存在新的恢复缺口，详见第二部分。 |
| 4. 固定摘要映射、独立函数、数据行上下文 | **落实** | `coverage.map.sha256`、两组候选并集、validator 私有函数、排除 header、两参数兼容及一致性向量均明确。 |
| 5. 硬链接联动边界 | **落实** | §2.3 第 8 步及 §5 明确共享 inode、禁止原地改写。无需因此改成全面复制。 |
| 6. 版本钉与共享模板换代 | **落实** | 显式 `if/raise` 不受 `-O` 影响；常量和模板语义变化都要求同步修改 producer 并登记。 |
| 7. 修正负测构造与 fixture 身份 | **落实** | 已修正已有 ledger 的断言、未登记 sha 的摘要构造、候选外 slot 的身份对齐，并固定 `fixture://helius`。⑧的拒绝阶段可准确命中。 |
| 8. 补齐关键向量 | **未完整落实** | 残尾、最长前缀、目标冲突、提交前中断、同步篡改边界、v1 输入均已列出；**提交后恢复向量缺失**。实际 body 的观察方法和两行来源的准备还需具体化。 |

**二、新引锚点与提交机制**

亲核 [receipt_kernel.py](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/receipt_kernel.py:574)、[sqd_gap_repair.py](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:196) 后：

| 锚点 | 结论 |
|---|---|
| `RawBytes:41`、`_json_bytes:181–184` | **适用于 JSONL。**`RawBytes.data` 直接作为 bytes 写出，不会将多行台账再序列化成单个 JSON 值。repair 的 `_jsonl_bytes:229–230` 确实返回 bytes。 |
| `_stage:327–340` | 同目录暂存，写完后 flush、fsync 文件；可捕获异常时清理暂存文件。 |
| `publish_exclusive:574–587` | 暂存完成后硬链接到最终名字，已有目标拒绝；正常异常路径通过 `finally` 清理暂存。**函数本身没有目录 fsync。** |
| `_fsync_dir:196–201` | 实际打开指定目录并 fsync；因此工单在 ledger 发布后调用 `_fsync_dir(pending)` 正确且必要。 |
| validator `canonical_json:50`、`sha256_bytes:66` | 可复用，合法摘要物料的编码与 core 一致。不能据此声称两者对所有非法输入的检查完全相同。 |
| validator `:1457` | 位置合适，但锚文本 `all_candidates = ...` 实际始于 **1456**，1457 是续行。应写 `:1456–1457` 之后，避免触发 §0.5 的行号不符停工规则。 |
| repair `:595–596`、`:1601` | 前者确为 coverage/beta 候选排序去重并集，后者确为 `fixture://helius`。 |

补充两项边界：

- SIGKILL 或掉电不会执行 Python 清理逻辑，可能留下 `.tmp.*`。最终 ledger 仍不会因此变成半文件；不可把“异常清理”描述为任何中断后都无暂存残留。
- link 成功后再报错，不代表没有提交。恢复判断应依据最终 ledger 是否存在且完整，而不能只依据函数是否正常返回。

**需要修正的复制恢复缺口：**

§2.3 第 6 步的 `shutil.copy2(src, dst)` 直接写最终证据路径。若复制中途停止：

1. ledger 尚不存在，但 `dst` 已是半文件；
2. 重跑首先执行目标冲突预验；
3. 半文件无法解析或与旧文件不等；
4. 命令拒绝，违背第 7 步“重跑同命令即可”的承诺。

最小修法是仅在 EXDEV 分支复用已有原语：

```python
publish_exclusive(dst, RawBytes(src.read_bytes()))
```

继续保留复制后的哈希复核。这样无需新增复制框架，也可删除不再使用的 `shutil` 导入。若采用流式复制，也必须先写暂存文件并同步，再发布最终路径。

此外，证据全部就位后应先 `_fsync_dir(pending / "evidence")`，再提交 ledger，最后同步 pending。**同步 pending 不等于同步 evidence 子目录内的新目录项。**当前 `_persist_live_slot:856` 已单独同步 evidence，认领路径不应省掉对应步骤。

**三、候选前缀与 ordered-workers**

结论：**当前实现不会因 worker 完成乱序而写出乱序台账。**

在 [sqd_gap_repair.py](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:980) 中：

- `:1299–1303` 将 `plan["candidate_slots"]` 原样传入 `_live_payloads`。
- 单 worker 在 `:989–1002` 按候选顺序拉取并持久化。
- 多 worker 在 `:1012–1022` 并发提交，但主线程在 **`:1026–1035` 按候选顺序取对应 future 的结果，再调用 persist**。
- seq 在 `:982` 持久化前赋值；worker 自身不写台账。

只核到 `:1010` 尚不足以判定顺序，决定性代码在后面的消费循环。

[test_batch8_repair_scale.py](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_batch8_repair_scale.py:190) 的测试也明确覆盖：

- `:51–52` 人为制造完成时间差；
- workers=4；
- `:197–201` 同时断言 payload 顺序、连续 seq、台账 slot 顺序等于输入候选顺序。

本次抽取真实 `_live_payloads`，以纯内存替身代替持久化，得到：

```text
worker 完成顺序：30, 20, 10
台账写入顺序：10, 20, 30
seq：0, 1, 2
```

因此 v3 可保留：

```python
adopted_slots == plan["candidate_slots"][:len(adopted_rows)]
```

这里必须区分“旧台账的数据行前缀”和“worker 的完成顺序”。

若将来明确支持按完成顺序写台账的历史 producer，替代条件才应是：

- 仍取旧台账从头连续、证据对齐的最长前缀；
- seq 连续且保持原值；
- slot 唯一；
- 每个 slot 属于当前候选集合。

即集合包含加连续台账前缀，**不排序旧行、不重编 seq**。本次没有证据要求放宽当前断言。

**四、§4 向量的可构造性**

- **⑧候选集外 slot：可构造。**同步修改行 slot、对应请求摘要、两份证据文件名及内部 slot，同时保留正确 seq、指纹和相等的响应摘要，能够通过现有身份对齐检查，再命中候选前缀拒绝。此处不必先让整份证据通过发布后的全部语义深验。

- **⑨第二个采纳 slot 冲突：可构造，但不能原样复用第 110 行的单行旧 pending。**须另备两行均可采纳的来源。最长前缀测试也需要两行来源，但其第二行随后被故意破坏，不能直接充当⑨的来源。最省说明是：三候选 slot，前两项成功、第三项配额停止，得到两行旧 pending；各向量独立复制后修改。不能把“两候选全部成功并已经发布”的 gen 直接当 pending。

- **⑩提交前中断：可构造，但应限定注入路径。**`publish_exclusive` 同时用于证据 JSON 和 ERROR 回执，不能在准备旧 pending 之前无条件替换它。先完成来源准备，再仅针对目标 `rpc_ledger.jsonl` 注入失败，其他路径调用原函数。该向量证明认领函数的提交前恢复，不能单独证明原语内部写入失败的清理。

- **缺少提交后向量。**应让真实发布函数完整提交认领 ledger 后再注入中断，断言重复认领拒绝、普通 `--resume` 成功、已采纳 slot 不重拉、`adopted` 与采纳行不变。现有 E27(b) 测的是 generation rename 后恢复，没有 adopted，不能代替这一项。

- **同步篡改边界：构造成立。**在其他检查保持有效时，同时替换行与 ref 的对应摘要，当前模型无法仅凭两者相等证明其虚假。v3 将其作为可信输入边界，符合 r2 要求。

**v1/`transactionConfig` 夹具路径可用，但不会自动记录请求 body。**

`repair_slot_responses:229–263` 将传入的 `missing_tx` 直接放入响应的 transactions；`RepairFixtureTransport:72–79` 按请求索引返回该值，不会删除 `version` 或 `transaction.message.transactionConfig`。本次内存验证确认两个字段原样保留。

然而 `repair_slot_responses:258` 使用生产 `_rpc_body` 生成索引，普通 fixture 成功仍可能同源自证。建议在测试内：

1. 深拷贝第二个 slot 的交易，再添加 v1 字段，避免污染用于旧版本成功证据的交易对象。
2. 包裹 `RepairFixtureTransport.call(self, kind, body)`，对实际 `reference-getBlock` 调用断言版本为 1，然后调用原方法；并断言确实观察到第二个 slot。
3. 新行摘要继续与测试内显式写定的完整版本 1 body 比较。

也可包裹 `ReferenceEndpointPool.get_block`，但应调用原方法继续走 transport，不能直接返回伪造结果。

**五、摘要映射与最小化**

§2.5 的映射正确，无需扩展 bundle。使用抽取的真实 core 函数，配合 v3 指定映射，本次内存验证了含 coverage/beta 重叠候选的当前、前代两组摘要，结果一致。

建议把§4 已有一致性向量补成“非空 beta 并集＋当前/前代两个 sha”；只比较默认 beta 为空的发布案例，不能有效发现漏合并 beta 的实现错误。这是增强现有向量，不需新增测试框架。

可以继续省：

- 不新增迁移框架、共享模块或依赖哈希体系。
- 不修改 core、bundle 顶层或 ordered-workers 实现。
- 修好 EXDEV 分支后，可去掉 `shutil`。
- 不要求暂存文件在不可捕获中断后绝对无残留。

不能省掉复制的原子发布、evidence 目录同步和提交后恢复测试。

另需收窄“产物状态不变”的表述：CLI 的 `main:1629–1634` 会调用 `publish_error_receipt:1561–1577`，在 repair parent 新建 `ERROR-*.json`。应明确验证拒绝不改变**旧来源及目标 pending 内的产物文件**，允许既有错误回执机制运行，避免测试错误地比较整个 parent 必须完全不变。

**v4 修订清单**

1. EXDEV 回退改为暂存后原子发布证据；优先复用 `publish_exclusive + RawBytes`，保留哈希复核；提交 ledger 前同步 evidence 目录。
2. §4 明确最长前缀及⑨各自的两行来源构造；⑩仅针对目标 ledger 注入失败，并补提交后普通 resume 的恢复向量及复制中断重试向量。
3. v1 测试明确包裹实际调用并继续执行原 transport；深拷贝新拉取交易，保留独立完整 body 摘要断言。
4. 扩强现有摘要一致性向量，覆盖非空 beta 并集及当前、前代两个 producer sha。
5. validator 插入锚点改为 `:1456–1457`；状态不变限定于来源与目标 pending，明确允许 ERROR 回执及不可捕获中断后的暂存残留。
