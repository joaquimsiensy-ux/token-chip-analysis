# 工单T3复核r2：通过

**v2 已吸收 r1 的必要修订，未发现相对 v1 新增的阻断问题。步骤 6 的 needle 正确；步骤 5 的 needle 经外层包装后仍能命中；索引行实测 176 B。无需再修改工单即可进入施工。**

审查基线：`556dd3bb858e2153448cea3e3c2029d72703e71e`（HEAD）。工作树为空；`2197505` 是 HEAD 祖先，工单指定的代码、文档和版本路径相对该提交无差异。未读取 `~/.codex/`、memories 或其他禁读材料；全程离线，未新建、修改文件，未 commit。

本轮完成整行锚检查、源码调用链核对及纯内存执行探针。没有运行会创建磁盘夹具的 `_produce_plan` 或完整测试套件；以下执行结果来自真实消费者、身份计算和测试 helper，文件系统操作由内存适配层承接，收据信封和文件绑定校验未被替换。

**a）r1 意见逐条吸收情况**

下文行号均指 **v2 工单**；引文为已采纳的替换文本原文，长条目摘录对应审项。无需再次替换。

1. **①入口／缓存／witness 边界：已吸收，接受。** L6 已区分正式 EVM 深验入口、单次运行缓存及 EVM 不使用 provider 的独立深验路径。关键原文：

   > 发布闸内 witness 深验按案根在单次 `run()` 内缓存（`:1833` 建、`:1837` finally 清空），退出即清空；EVM `validate_sources:2120-2123` 不使用该 provider，另行深验——正常一次发布闸因此重算目录两次。

   > 此修复检查本次深验时的目录实物，不扩展 witness 对签发后目录叶子变化的保证

   与当前源码一致。“正常一次发布闸两次”没有继续被误写成一次；同次执行期间持续修改目录、长期持有 witness 后直接消费，也已明确排除在新增保证之外。

2. **1.1 共享发布收据重建：已吸收，接受。** L24 原文：

   > 文件案与目录案的旧 `shared_release_receipt.json` 均须用现有 `create_bundle` 流程重建，不能据此声称共享发布产物字节不变（此影响自 9.0.3 起本已存在，本单不新增类别）。不得为兼容旧共享发布收据放宽校验。

   `create_bundle:2154` 写入本文件 SHA，`validate_bundle:2177-2179` 要求与当前源码一致，故这项存量影响成立。文件时间证据分支不变与共享发布收据必须重建，已作出正确区分。

3. **1.2 身份相等前提：已吸收，接受。** L25 原文：

   > path/kind/size/sha256 四键；生产期与消费期均使用 resolve 后绝对路径。同一物理路径、相同叶子集合和文件字节下，两次身份相等；实际搬移导致旧引用失效时，由既有文件绑定或目录存在性／案根包含检查拒绝，本单不新增迁移支持

   已删除“案根未迁移即相等”的过强表述，也不再保证搬移一定在目录存在性检查处才被拒。L7–8 同时移除了日志无法支持的精确字节数断言，保留日志实际提供的规模、耗时和 `match_signed=True`。

4. **1.3／2.1(c) 两行简化：已吸收，接受。** L26 原文：

   > symlink、无普通文件等 `ValueError` 沿用本函数外层 authority-chain 上下文（`:1080-1081` 统一加 `time plan authority chain broken:` 前缀），不增加局部异常包装。

   L50–51 插入代码原文：

   ```python
               _require(input_identity(directory)[0] == identity,
                        "time plan input directory content differs from signed identity")
   ```

   放置顺序正确：既有目录存在性与案根包含检查先执行，再完整重算。删除局部异常包装不会丢失外层上下文。

5. **0.5 锚核验时点：已吸收，接受。** L17 原文：

   > - 0.5 所有施工锚在首次修改前统一核验：目标文件整行原文以 `grep -n -F -x -- '<整行>' <文件>` 命中恰 1 处且基线行号一致，不符**停工**。修改后的行号允许随插入自然移动（如 import 插入后目录分支行号 +1），完成报告记录实际 diff 行号。

   本轮重新执行整行匹配，以下锚全部唯一且行号一致：

   | 文件 | 已核行号 |
   |---|---|
   | `scripts/report/shared_release_receipt.py` | 39、1047、1055–1059 |
   | `scripts/tests/test_anchor_plan_v3.py` | 600 |
   | `CHANGELOG.md` | 13、101 |
   | `SKILL.md` | 23 |
   | `pyproject.toml` | 15 |

6. **步骤 4：已吸收，接受。** L62 原文：

   > 4. **删除叶子**：将 `source / "run_1" / "blocks.parquet"` rename 到同一案根下且预先不存在的 `root / "blocks.bak"`（已移出身份根 `root/v2`，仍有 logs 故走身份不等而非空目录异常）；调用消费者须以 `time plan input directory content differs from signed identity` 拒绝；移回原路径后再次放行。

   搬移位置明确，确实改变身份根内的叶子集合，同时保留非空目录条件。

7. **步骤 5：已吸收，接受。** L63 原文：

   > 5. **目录内 symlink**：创建 `run_1/link.parquet -> logs.parquet`；调用消费者须以既有 helper 的文本 `input directory contains symlink` 拒绝；删除该链接后再次放行。

   needle 与两行简化实现一致，原先“needle 不含 symlink、括注却要求包含”的矛盾已消除。执行证据见下文。

8. **步骤 6：已吸收，接受。** L64 原文：

   > 6. **文件分支对照**：在已创建的独立 `root2` 中调用 `_produce_plan(root2, directory=False)`；先断言 `_shared_authority` 放行，再同长度翻转 CSV 末字节，断言既有生产错误文本 `time plan input identity sha256 mismatch`（`_shared_authority` 重算输入引用后旧签名 identity 在 `:1037` 被拒）；恢复原字节后再次放行。不得修改文件分支生产错误文本，不刷新计划或收据。

   已明确独立案根、修改前放行、修改后拒绝和恢复后放行，也不再引用不存在的既有测试断言。

9. **原 v1 L61“不刷新”：已吸收，现位于 v2 L58。** 原文：

   > `_ref` 由现有 helper 内部使用；本测试**不需要** `_refresh_receipt`，不得为了让负例通过而刷新签名身份或输入清单

   与步骤 6 的“不刷新计划或收据”一致。注意这里引用的旧 L61 已因前文简化移动，不能按 v2 L61 寻找。

10. **索引及详细段：已吸收，接受。** L79 索引原文：

    ```text
    - **9.0.5**（2026-09-23）修复目录案消费期漏验：重算完整身份，拒叶子覆写、增删及 symlink（FR-02 C）；文件分支、schema 不变，档位 修。
    ```

    L82 成本与存量影响原文：

    > 成本写明 QUQ 日志单次完整身份计算为 3.5 s（7.62 GB / 61 文件），正常 verify 重算一次、EVM 发布闸两次，分别估计增加约 3.5 s／7 s；兼容范围写明文件时间校验分支不变，但所有旧 shared_release_receipt.json 因本文件 producer.sha256 改变须重建（自 9.0.3 起已如此）。

    日志内容支持上述单次测量；3.5 s／7 s 已正确标为增加耗时的估计，没有冒充命令总耗时。

**b）两处 needle 的亲核结果**

**步骤 6：needle 正确，但它是完整异常中的子串。**

纯内存夹具使用与 `_produce_plan(..., directory=False)` 相同的 CSV 行生成规则；先建立通过真实校验的计划、清单和收据，再同长度翻转 CSV 末字节。HEAD 原函数与仅在内存插入 v2 两行代码的函数，均得到同一完整文本：

```text
time plan authority chain broken: time plan input identity sha256 mismatch
```

原因已亲核：`_shared_authority` 每次通过 `_ref(source, root)` 重算当前输入引用，因此先通过 `time merged input` 绑定检查；计划收据中未更新的 `input_identity` 随后在原 `:1037` 调用处被拒。恢复原字节后，两种实现均再次放行。

**步骤 5：外层前缀不影响 `_expect_reject` 命中。**

对仅在内存插入 v2 修改的消费者，目录内加入链接后，完整异常文本为：

```text
time plan authority chain broken: input directory contains symlink: /__T3_MEMORY__/directory/v2/run_1/link.parquet
```

其中 `/__T3_MEMORY__/...` 是探针的虚拟路径，未在磁盘创建。

真实 `_expect_reject` 使用：

```python
if needle and needle not in str(exc):
```

实调该 helper，以 `input directory contains symlink` 为 needle，通过；移除内存链接后，消费者再次放行。该结果来自真实 `input_identity` 的 symlink 拒绝及真实外层异常包装。

**c）新增问题、字节与剩余验证**

未发现 v2 新增的阻断问题：

- 两行简化仍严格落在目录分支，保留文件分支既有校验顺序和错误文本。
- 没有扩大生产白名单，也没有引入新 schema、公开入口或需要登记的 invariant／contract 项。
- 无需补“消费期重算耗时不进收据”测试；新增逻辑没有计时字段或收据写入操作。
- `references`／`commands-staging` 零改动、SKILL 仅改版本号及 9.0.5“修”档位仍成立；当前 SKILL 实测 8021 B。

索引 UTF-8 字节复测：

| 版本 | 不含换行 | 含 LF 换行 | ≤200 B |
|---|---:|---:|---|
| v1 | 233 B | 234 B | 不满足 |
| v2 | **176 B** | **177 B** | **满足** |

本结论是**工单可施工**。施工后的磁盘夹具回归、RED／GREEN 证据和调度方执行的 `changelog_lint.py`，仍按工单验收。

| r1 汇总审项 | r2 判定 | 核验结果 |
|---|---|---|
| a 锚与行号 | 通过 | 全部唯一且准确；首次修改前统一核验已写入 |
| b 来源与入口 | 通过 | EVM 双重深验、单次运行缓存及 witness 边界均已吸收 |
| c 修法定形 | 通过 | 两行全等校验已采纳；外层异常上下文保留 |
| d 回归面 | 通过 | 文件时间校验不变与共享发布收据重建影响已区分 |
| e 六步测试 | 通过 | 步骤 4／5／6 及不刷新要求已修正；两处 needle 执行核验通过 |
| f 原则与档位 | 通过 | 索引 176 B；成本及存量影响已补；“修”档位合理 |
| **总体** | **通过 v2** | **无新增必改项，可按现有白名单施工** |
