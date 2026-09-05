# 批 18 盲审消化工单 b18r1 — done

日期：2026-08-31
状态：**定向施工与工单点名回归完成；未 commit；全量 146 项按工单留给验收方本机 nohup。**

## 1. 基线、锚点与边界

- 工单基线为 `main@19c0fa6`（v6.54.0）。开工时当前 `HEAD=2d99351`；祖先检查确认 `19c0fa6` 是 HEAD 祖先，二者唯一树差异是新增本工单 `batch18_review_workorder.md`，全部允许修改目标文件与 `19c0fa6` 字节一致。
- 工单列明的全部锚点逐行吻合：`shared_release_receipt.py` 的 1179、1424–1433、1450–1494、1820–1829、1832–1848、1858–1864；`handoff_manifest.py` 的 123–147、249–253、284–298。
- 施工只发生在白名单。`scripts/report/audit_release_gate.py` 无需一行适配，实际零改动；ARC 案根、禁改生产文件、API key、既有测试断言均未触碰。

## 2. 先红证据

原文证据统一位于 `maintenance/repair-20260823-sqd-gap/batch18_review_red_evidence.txt`。

- **F1 直构伪造**：未签发的值全等 `DeepReconciliationWitness(...)` 身份不同，但 `validate_bundle_errors=[]`。
- **F1 replace 伪造**：`dataclasses.replace(合法 witness, target=值全等拷贝)` 身份不同，但 `validate_bundle_errors=[]`。
- **F2 receipt 过期**：合法签发后只改 `data/reconcile_receipt.json`、wrapper sha 不变，旧 witness 仍得 `validate_bundle_errors=[]`。
- **F2 owners 过期**：合法签发后改 `data/holders_owners.json`，旧三验为 `True`，隔离旁路独立 accounting 复验后 witness 消费点仍为 `[]`；完整路径另有既有 accounting bundle mismatch，红证已同时保留，未把该独立防线冒充 witness 已闭合。
- **F3 分类截断**：首个 data_map 条目为合法 JSON 数组 `[1,2]` 时触发 `'list' object has no attribute 'get'`；generate rc=0，但该条目和其后的普通条目均未进 artifacts。

以上 RED 全部在任何生产代码修改前取得并落盘。

## 3. 修法

### F1：witness 构造私有化

- `DeepReconciliationWitness` 改为 `@dataclasses.dataclass(frozen=True, eq=False)`，恢复对象 identity hash。
- 新增模块私有 `_ISSUED_WITNESSES = weakref.WeakSet()`；仅 `witness_reconciliation_report` 在真实深验、闭包采集与对象构造完成后登记。
- 消费点先按对象身份查登记表；直构、`dataclasses.replace` 与字段值全等拷贝均不是原签发对象，统一拒绝为 `reconciliation witness 无效/过期`。
- 代码注释已用大白话明确：身份而非字段值是防止值等伪造和 replace 拷贝的关键。

### F2：绑定已深验文件闭包

`bound_files` 是按绝对 resolved 路径排序、去重的 `(path, sha256)` 元组。枚举依据严格来自 19c0fa6 的既有深验路径：

1. wrapper 本体：`witness_reconciliation_report` 原 1837–1841。
2. 每个 check 的 receipt 实物：wrapper 的 `checks[key].receipt`，沿用 `validate_reconciliation_check` 原 1179–1186 的 `ref_ok` 解析；逐 check 来源为原 1424–1433。
3. 每份已验 receipt 的 `inputs` 内带 path+sha256 的直接文件引用：沿用案根 `ref_ok` 语义；其中 exact owners 来源为原 1450–1452。
4. 每份已验 receipt 的 `holder_outputs` 内带 path+sha256 的直接文件引用：沿用 `_bound_case_ref(..., base=receipt_path.parent)`；Solana supply owners 的同款基准来源为原 1457–1463。
5. 动态 Solana 另收冻结 bundle `data/solana_observation_bundle_frozen.json`：来源为原 1467–1494，实物解析沿用原 1471 的 `regular`。

构造点位于真实深验完成之后，全部 sha 当场按已验磁盘态重算；磁盘不存在的纯函数夹具 wrapper 继续使用空闭包哨兵。消费时逐文件复核非 symlink、存在与当前 sha，缺失或 sha 漂移统一拒绝为同一 witness 错误；wrapper 原单独 sha 检查保留。

这是**文件级新鲜度指纹**，不会重跑 receipt/owners 的深验逻辑；因此与批 15 缓存语义兼容。实测 N9 `calls==1`、N10 `calls==2` 及缓存态/非缓存态错误逐字等价均未变化。

### F3：manifest 分类器类型防御

- `load_json` 结果不是 dict 时 `_reverse_bound_reason` 直接 `return None`，按普通产物做 sha 绑定。
- `input_binding` 不是 dict 时按空绑定处理，不再调用其 `.get`。
- `handoff_manifest.py:284–298` 的既有 data_map `for`-in-`try` 结构未改；真正 `stage=final` 且带 `input_binding.handoff_manifest` 的扫描仍按批 18 N5 语义跳过。

## 4. 测试与版本

新增 `scripts/tests/test_batch18_review_digest.py`，三组均 PASS：

- F1：直构、replace、值全等拷贝三式拒绝；合法签发照常通过。
- F2：receipt 篡改拒绝、holders 实物篡改在 witness 层拒绝、未改动通过。
- F3：数组 scan 与字符串 input_binding 均收录；普通第二条不再被截断；真正 final 扫描仍跳过。

`scripts/tests/run_all.py` 已登记新入口，机械分母 **145→146**。按工单未运行全量 146；定向结果如下：

| 测试 | 结果 |
|---|---:|
| `test_batch18_review_digest.py` | PASS，3/3 |
| `test_batch18_shared_bundle_witness.py` | PASS，6/6；N2/N4/N11 不改断言 |
| `test_batch18_manifest_stage2_loop.py` | PASS，7/7；N5 不回退 |
| `test_batch15_three_ledgers_frozen.py` | PASS，12/12；N9/N10 调用次数不变 |
| `test_repair_batch1.py` | PASS，rc=0 |
| `test_r9_batch3_release_guards.py` | PASS，6/6 |
| `test_reconcile_v4_receipt.py` | PASS，rc=0 |
| `test_handoff_manifest.py` | PASS，68 项 |
| `changelog_lint.py` | PASS，rc=0 |
| `docs_lint.py --all` | PASS，59 文档 |
| `test_version_consistency.py` | PASS，6.54.1 |

版本五处已同步：`VERSION=6.54.1`、`pyproject.toml=6.54.1`、`SKILL.md:23=6.54.1`、CHANGELOG 索引 6.54.1、CHANGELOG 6.54.1 六栏详情。详情明确来源为批 18 盲审 P1×2＋P2。

## 5. 收尾声明

- 既有任何测试文件的断言逻辑：**零改动**。
- `audit_release_gate.py`：**零改动**。
- `git diff --check`：PASS。
- 白名单外改动：0。
- API key / secret：0。
- commit：未执行。
- 全量 `run_all.py`：未执行，按工单交由验收方本机 nohup 跑 146/146。
