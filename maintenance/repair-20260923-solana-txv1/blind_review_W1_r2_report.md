[2026-09-23T07:53:43.228Z] Assistant message
# 盲审 W1 r2: PASS

未发现 P0/P1；发现 1 项 P2 测试隔离问题。**两个功能测试被只读沙箱阻断，不能宣称完整回归通过。**

审查范围为 `main...HEAD`（HEAD：`e44551a3`），按要求排除施工报告目录；未读取禁止目录，未修改文件、未 commit，工作树保持干净。

**发现**

- **P2：前代 digest 负向向量未隔离摘要重算。**  
  位置：[scripts/tests/test_sqd_gap_repair.py:987](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:987)。该向量只修改 `predecessor_plan_digest`，保留原 `source`，因此先被 [solana_exact_validate.py:1353](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:1353) 的目录名绑定拒绝，未进入摘要重算。  
  **复现：**在有效内存 bundle 中执行相同篡改，更新台账外层 size/hash，并监测 `_plan_digest_from_generation`：深验返回认领记录无效，但重算调用次数为 **0**。建议该向量同时修改 `source="pending-"+伪造digest`。我已独立测试这一隔离版本，生产者和深验仍正确拒绝，因此不构成运行时 P1。

**r2 专项实测**

以内存文件内容替代磁盘读写、SQLite 使用 `:memory:`；执行真实校验逻辑，包括 coverage 校验，没有替换认领或摘要校验函数。每次篡改均更新台账外层 size/hash。

| 内存向量 | `_verify_adopted_record` | `load_resume_slots` | 完整深验 |
|---|---|---|---|
| 未篡改，候选与台账均为 `[10,20]`，`rows=1` | 通过 | 通过 | 通过 |
| 台账改为 `[20,10]`，重排 seq，保持 `rows=1` | 拒绝 | 拒绝 | 拒绝 |
| `source=""` | 拒绝 | 拒绝 | 拒绝 |
| `source` 为错误 pending 目录名 | 拒绝 | 拒绝 | 拒绝 |
| 每次恢复原始内容后 | 通过 | 通过 | 通过 |

三个专项篡改的深验**唯一失败原因**均为 `RPC ledger adopted record invalid`，没有其他损坏掩盖结果。

**其余核查**

- **常量化完整：**main 的 13 文件、17 处生产代码引用，现为 12 文件、16 处；减少的一处来自请求模板合并。生产请求中未发现数字上限硬编码。版本钉和四项 producer 登记一致。
- **认领检查有效：**内存实测拒绝伪造 header、异 parent、重复认领、带 `adopted` 的前代、证据已对齐但候选集外的 slot，以及目标第二个 slot 的冲突证据；冲突在第一份证据发布前被拒绝。旧台账残尾保持原字节。
- **恢复与绑定：**内存模拟台账提交中断、EXDEV 复制发布中断后，重跑成功。真实文件系统的硬链接、原子发布及持久化行为未能完整实跑。深验重算物料与 `compute_plan_digest` 一致；逐行指纹、header 指纹、bundle 指纹等式齐全，独立篡改行/header 指纹均被拒绝。
- **兼容性：**无 `adopted`、全部版本 0 的内存产物，通过两参数 `load_resume_slots` 和完整深验。已核对 batch7/batch8 相关代码路径，未发现此次改动引入的行为回归。
- **测试真实性：**E27(d) 在传输入口直接断言版本值为 `1`，另用独立请求字典计算预期摘要，不是同源自证。候选集外、目标冲突和中断向量具备对应前置条件；上述 P2 是发现的隔离不足。
- **最小化与文档：**请求模板已去重，`SKILL.md` 字节数保持 **8021**。§14.8、Solana capture 文档及 CHANGELOG 9.1.0 的主要行为描述与实现一致，也明确说明来源可信前提和硬链接边界；未发现需阻断的新增或夸大。

**指定命令的实际结果**

均使用 `MPLCONFIGDIR=$HOME/.matplotlib python3 -B scripts/tests/<文件>` 执行：

```text
test_sqd_gap_repair.py — exit 1，未到达 E27(d)
PermissionError: [Errno 1] Operation not permitted: '/private/tmp/sqd-repair-cas-m2w1u3k4'

test_batch8_repair_scale.py — exit 1
PermissionError: [Errno 1] Operation not permitted: '/private/tmp/batch8-keys-l5qbt3_o'

invariant_scan.py — exit 0
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0

test_producer_registry_current.py — exit 0
producer registry: 0 FAIL
```
