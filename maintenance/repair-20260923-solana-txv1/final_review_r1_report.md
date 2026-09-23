[2026-09-23T08:28:14.674Z] Assistant message
# 收官 review: FAIL

**本轮终局验收未完成：三项必跑测试被只读沙箱阻断，无法确认完整回归通过。** 已完成的代码核对、内存复现和五项检查支持修复有效，未确认仍存在的 P0/P1；不能把环境阻断算成代码缺陷，也不能据此宣告全部通过。文档另有 P2。

审查对象：`fix/solana-txv1`，HEAD `dde8ca9d`，对比 main `1624b860`。全程未调用 RPC，未读取禁读目录，未修改文件或 commit；结束时 `git status --porcelain=v1` 为空。

**1. 原问题：请求修复已确认**

- 对 main 的生产代码做 AST 统计，确为 **13 个文件、17 处数字上限**；HEAD 生产代码为 **0 处**。
- [endpoint_identity.py:13](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/endpoint_identity.py:13) 定义常量为 `1`。
- `git diff main...HEAD` 确认 producer 删除原写死 `0` 的请求体；[_rpc_body:639](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:639) 调用共享模板，[repair_getblock_body:1214](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:1214) 默认参数取该常量。
- 原样 `grep -rn "maxSupportedTransactionVersion" scripts` **仍有数字命中**：`test_sqd_gap_repair.py:945` 的独立版本 1 期望体，以及 `test_batch4_invariant_guards.py:38` 的负向版本 0 夹具。它们不是生产请求遗留，不能将 grep 结果表述为“全目录无数字”。

已执行纯内存复现，核心代码如下；没有联网或写文件：

```python
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
root = Path.cwd()
sys.path[:0] = [str(root / p) for p in
               ("scripts/solana", "scripts/lib", "scripts/tests")]

import sqd_gap_repair as repair
import solana_exact_validate as exact
import invariant_scan as scan

with patch.object(repair, "repair_getblock_body",
                  wraps=exact.repair_getblock_body) as template:
    body = json.loads(json.dumps(repair._rpc_body(123456)))
    assert body["params"][1]["maxSupportedTransactionVersion"] == 1
    template.assert_called_once_with(123456)

assert exact.repair_getblock_body(123456)["params"][1][
    "maxSupportedTransactionVersion"] == 1
assert scan.hardcoded_tx_version_errors() == []

source = root / "scripts/solana/sqd_gap_repair.py"
original = source.read_text()
mutated = original.replace(
    "    return repair_getblock_body(slot)",
    '    return {"maxSupportedTransactionVersion": 0}', 1)
read_text = Path.read_text

def memory_read(path, *args, **kwargs):
    return mutated if path == source else read_text(path, *args, **kwargs)

with patch.object(Path, "read_text", memory_read):
    errors = scan.hardcoded_tx_version_errors(files=[source], root=root)
assert len(errors) == 1 and "hardcoded tx version" in errors[0]
assert source.read_text() == original
```

实际输出尾行：

```text
PASS monkeypatch: producer delegates to shared request template
PASS in-memory injection rejected: hardcoded tx version: scripts/solana/sqd_gap_repair.py:640
PASS production literals=0; repository unchanged
```

守卫实现见 [invariant_scan.py:355](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/invariant_scan.py:355)。

**2. 认领机制：代码链路完整，E27(d) 本轮未跑到**

`MPLCONFIGDIR=$HOME/.matplotlib python3 -B scripts/tests/test_sqd_gap_repair.py` 已执行，另设置 `PYTHONDONTWRITEBYTECODE=1` 防止子进程写字节码。退出码 `1`，尾行：

```text
PermissionError: [Errno 1] Operation not permitted: '/private/tmp/sqd-repair-cas-uolckmte'
```

失败发生在前面的夹具创建，**不是 E27(d) 断言失败**。

源码证据：

| 核对点 | 证据与结论 |
|---|---|
| 仅拉未完成 slot | [测试:921](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:921) 截获请求并断言版本 1；`:934` 断言 `observed == slots[1:]`。生产代码 `sqd_gap_repair.py:1128` 对已完成 slot 直接恢复证据。 |
| 同案、登记前代、最长前缀 | [producer:828](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:828) 检查同 parent、目录名、参考源、来源无 `adopted`；`:842` 遍历 ACTIVE 历史哈希重算 digest；`:854` 取证据对齐的最长连续候选前缀。 |
| 续跑重验 | [producer:729](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:729) 校验 header、调用 `_verify_adopted_record`；`:783` 重算前代 digest，核对候选前缀和来源目录名；`:771` 核对请求摘要与参考源指纹。 |
| 发布重验 | [producer:1542](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:1542) 再验 header 和认领记录；`:1611` 深验通过后才更新正式指针。 |
| 独立深验 | [validator:1340](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:1340) 核对登记、字段类型、来源名；`:1357`、`:1387` 核对参考源指纹；`:1523` 独立重算当前及前代 digest、核对排序候选前缀。 |
| 篡改拒绝、恢复通过 | [测试:980](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:980) 修改台账并同步外层大小/哈希后，要求深验拒绝；包含同时修改前代 digest 与 source 的向量，避免只被目录名检查挡住。`:1006` 恢复后要求通过；`:1024` 对续跑前缀乱序、错误来源名分别拒绝并恢复通过。 |

**覆盖边界：** E27(d) 明确测试了深验的八类篡改、续跑的两类篡改及十二个认领故障向量；没有对“续跑／发布／深验 × 每个字段”全部逐项注入。发布重验的存在由代码证实，不能称为全矩阵独立测试覆盖。

**自证情况：**

- `test_sqd_gap_repair.py:864` 用生产侧 `compute_plan_digest` 构造前代摘要，而认领侧调用同一函数校验；`:872` 用 `_repair_getblock_params_digest` 构造旧请求摘要，验证侧也使用该函数。这些夹具不能独立证明摘要算法正确。
- `:941` 手写版本 1 请求体，再用测试自己的 `canonical_bytes` 和 `hashlib` 算期望值，**不是上述自证**。
- `:958` 将深验自己的摘要实现与 producer 实现比较，是两个实现交叉验证，仍不等于固定、外部已知的摘要答案。

未发现放开任意 `params_digest`、取消同案绑定或跳过发布深验。接受版本 `0..1` 是有界历史兼容。来源真实性本来就是可信输入前提；[测试:1192](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:1192) 还明确展示了同步伪造声明哈希不能靠认领机制鉴真。

**3. 回归与登记**

以下命令均以 `python3 -B scripts/tests/…` 执行，并设置上述两个环境变量：

| 命令 | 退出码 | 实际尾行 |
|---|---:|---|
| `test_batch8_repair_scale.py` | 1 | `PermissionError: [Errno 1] Operation not permitted: '/private/tmp/batch8-keys-pv06clv9'` |
| `test_batch7_validator_coverage_gaps.py` | 1 | `PermissionError: [Errno 1] Operation not permitted: '/private/tmp/b7-gap1-9e6dpu8m'` |
| `invariant_scan.py` | 0 | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| `test_producer_registry_current.py` | 0 | `producer registry: 0 FAIL` |
| `changelog_lint.py` | 0 | `PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 83 条 + 归档 139 条` |
| `docs_lint.py --all` | 0 | `PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）` |
| `test_version_consistency.py` | 0 | `PASS: M-03 version metadata consistent at 9.1.0` |

[producer_history.py:235](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/producer_history.py:235) 起四条 9.1.0 条目分别登记 cache、bundle、coverage-resolution、pointer，均为 ACTIVE，commit 均为：

```text
7846184f9f2ba758027cd6c5ddb1b21e87b3c16f
```

分别执行登记 commit、HEAD 的 `git show …:scripts/solana/sqd_gap_repair.py | shasum -a 256`，以及工作区文件 `shasum -a 256`，三者均与四条登记一致：

```text
3f89aab13054be76711d85d15a3e4f21d6113c35c905f55a8e60edb31ba8446b
```

**4. 中文文档：机制基本一致，有 P2**

| 文档描述 | 与代码对照 |
|---|---|
| 常量 1、共享模板、producer 换代 | [CHANGELOG:103](/Users/uravvv/.claude/tca-fix-txv1/CHANGELOG.md:103) 与实现一致。重复请求体已合并，符合“能改不加”的方向。 |
| 认领条件、最长前缀、保留行字段与 seq | CHANGELOG:104、[scan-schemas:1004](/Users/uravvv/.claude/tca-fix-txv1/references/scan-schemas.md:1004) 与认领实现一致。 |
| 台账提交前重跑认领，提交后普通 resume | 与目标已有台账即拒绝及测试两个中断边界一致。 |
| 可信来源、硬链接共享 inode、EXDEV 复制 | CHANGELOG:105、scan-schemas:1028 与代码一致；[validator:898](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:898) 确实重算证据大小及哈希。 |
| 采集指南中的认领与版本摘要 | [data-pipeline-solana-capture:198](/Users/uravvv/.claude/tca-fix-txv1/references/data-pipeline-solana-capture.md:198) 与详细契约一致，没有额外承诺来源鉴真。 |

P2 建议：

- **施工过程确实混入用户文档。** CHANGELOG:107 的复核轮数、盲审成绩、调用成本和交付起始时间，应移至维护记录。不能确认“没有施工叙述”。
- **“直接前代”容易理解成紧邻的上一个版本。** 代码允许任意符合条件的 ACTIVE 历史 producer，并未检查版本相邻。建议写成“未含认领记录的已登记历史 producer pending”。
- **“残缺尾行丢弃”需区分对象。** scan-schemas:1031 建议明确：来源尾行仅解析时忽略、来源字节不变；当前 pending 的普通恢复会清理残尾。
- **“能发现任何一侧的后续改写”措辞过满。** 建议补充“在已发布清单保持不变时”，与同段声明的“不提供对抗性证明”保持一致。

**仍存在的已确认 P0/P1：无。** 上述文档问题仅为 P2，不足以判代码 FAIL。本次 FAIL 的唯一收官阻断是主测试及两项回归缺少完整执行结果；需要在允许测试临时目录写入、仓库仍保持只读且离线的环境补跑这三项，才能作出无保留的终局 PASS。
