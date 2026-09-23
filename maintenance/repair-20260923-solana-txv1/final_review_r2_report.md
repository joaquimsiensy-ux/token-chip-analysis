[2026-09-23T08:51:06.455Z] Assistant message
# 收官 review r2: PASS

**未发现仍存的 P0/P1；上一轮四条 P2 已按本轮要求处置，无新增 P2。** 三项测试仍被只读沙箱阻断，已实际执行并记录错误尾行；按本轮判定规则，以代码审查和补充内存核验为依据，不将环境阻断算作代码缺陷，也不宣称完整回归已通过。

审查对象：`fix/solana-txv1`，HEAD `2b8d1298`，对比 main `1624b860`。全程离线、未调用 RPC、未读取禁读目录，未修改文件或 commit；结束时工作区干净。

**1. 原问题已解**

- 对 main 的生产代码做 AST 统计：**13 个文件、17 处数字上限**；HEAD 为 **0 处**。
- [endpoint_identity.py:13](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/endpoint_identity.py:13) 定义 `SOLANA_MAX_SUPPORTED_TX_VERSION = 1`。
- [producer `_rpc_body`:639](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:639) 调用共享模板；[repair_getblock_body:1214](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:1214) 默认使用该常量。与 `main...HEAD` 差异一致。
- 全目录搜索仍会命中测试中的数字：版本 1 独立期望体及版本 0 负向夹具。因此准确结论是“**生产代码无写死数字上限**”。

已执行的离线复现核心如下：

```python
with patch.object(repair, "repair_getblock_body",
                  wraps=exact.repair_getblock_body) as template:
    body = json.loads(json.dumps(repair._rpc_body(123456)))
    assert body["params"][1]["maxSupportedTransactionVersion"] == 1
    template.assert_called_once_with(123456)

assert exact.repair_getblock_body(123456)["params"][1][
    "maxSupportedTransactionVersion"] == 1

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

实际输出：

```text
PASS in-memory request: _rpc_body/repair_getblock_body maxSupportedTransactionVersion == 1
PASS in-memory injection rejected: hardcoded tx version: scripts/solana/sqd_gap_repair.py:640
PASS production literal audit: main=13 files/17 numeric literals; HEAD=0
```

**2. 认领机制与校验链**

| 核对点 | 证据与结论 |
|---|---|
| 来源与前代绑定 | [producer:828](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:828) 检查同 parent、目录名、参考源和来源 header 无 `adopted`；遍历已登记 ACTIVE 历史哈希重算前代 digest。没有限定必须是相邻版本。 |
| 最长前缀、保留来源 | [producer:854](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:854) 截取证据对齐的连续候选前缀，保留行字段；来源残尾仅解析时忽略。目标证据全部预验后链接，只有 EXDEV 回退复制，最后发布台账。 |
| 续跑重验 | [producer:729](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:729) 校验 header、认领记录、证据和指纹；`:783` 重算前代 digest，核对来源名与候选前缀。 |
| 发布重验 | [producer:1542](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:1542) 再验 header 和认领记录；`:1611` 调用深验，通过后才更新正式指针。 |
| 独立深验 | [validator:1340](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:1340) 校验认领字段、登记与来源名；`:1357`、`:1387` 核对参考源指纹；`:1523` 重算当前及前代 digest，并校验排序候选前缀。 |

E27(d) 源码覆盖确认：

- [测试:921](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:921) 截获版本 1 请求；`:934` 明确断言只请求 `slots[1:]`。
- [测试:980](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:980) 修改台账并同步外层大小、哈希后，要求深验拒绝八类篡改；包括同时改前代 digest 和 source，能实际触达摘要重算。`:1006` 恢复后正向通过。
- `:1024` 对续跑的前缀乱序、错误来源名分别拒绝并恢复通过；后续还覆盖十二个认领故障向量及提交前后恢复边界。

**覆盖边界：** E27(d) 并未对“续跑／发布／深验 × 每个字段”做完整独立注入矩阵。发布重验由代码链路确认，不能扩大成全部场景均有独立测试。

**自证情况：** `:870` 用生产侧 `compute_plan_digest` 构造旧摘要，`:879` 用共享 `_repair_getblock_params_digest` 构造旧请求摘要；校验侧复用这些函数，这部分不能独立证明摘要算法。`:941` 手写版本 1 请求体并自行哈希，属于独立期望；`:959` 的两套摘要实现比较属于交叉验证。

本轮另执行了内存夹具，真实调用认领、续跑校验和任务调度逻辑，仅替换文件及传输操作：

```text
PASS independent JSON/hash oracle: current/predecessor digest and coverage/beta union
PASS memory-backed adoption/resume: longest prefix=1; original row and torn source bytes preserved
PASS memory resume: 8 tamper vectors rejected/restored; wrong row fingerprint never marked complete
PASS memory scheduling: workers=1/2 fetch only [20,30], completed slot 10 skipped
PASS memory checks complete; filesystem/RPC operations mocked, no end-to-end suite claim
```

未发现放开任意请求摘要、取消同案绑定或跳过发布深验。版本 `0..1` 的接纳范围有界；来源真实性仍是文档明确声明的输入前提。

**3. 回归与 producer 登记**

已先执行 `mkdir -p .staging_b3/tmp`，实际返回：

```text
mkdir: .staging_b3/tmp: Operation not permitted
```

随后各测试均设置 `TMPDIR="$PWD/.staging_b3/tmp"`、`MPLCONFIGDIR="$HOME/.matplotlib"`、`PYTHONDONTWRITEBYTECODE=1`，使用 `python3 -B scripts/tests/…` 执行。三项测试的夹具显式指定 `/private/tmp`，因此也不会被 `TMPDIR` 覆盖。

| 命令 | 退出码 | 实际尾行 |
|---|---:|---|
| `test_sqd_gap_repair.py` | 1 | `PermissionError: [Errno 1] Operation not permitted: '/private/tmp/sqd-repair-cas-8mtjfbec'` |
| `test_batch8_repair_scale.py` | 1 | `PermissionError: [Errno 1] Operation not permitted: '/private/tmp/batch8-keys-hw5cy4us'` |
| `test_batch7_validator_coverage_gaps.py` | 1 | `PermissionError: [Errno 1] Operation not permitted: '/private/tmp/b7-gap1-58tydiga'` |
| `invariant_scan.py` | 0 | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| `test_producer_registry_current.py` | 0 | `producer registry: 0 FAIL` |
| `changelog_lint.py` | 0 | `PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 83 条 + 归档 139 条` |
| `docs_lint.py --all` | 0 | `PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）` |
| `test_version_consistency.py` | 0 | `PASS: M-03 version metadata consistent at 9.1.0` |

前三项均因创建夹具目录失败而终止，**未跑到测试成功尾行，E27(d) 本轮未完整执行**。

[producer_history.py:235](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/producer_history.py:235) 起四条 9.1.0 登记覆盖 cache、bundle、coverage-resolution、pointer，全部 ACTIVE，commit 均为：

```text
7846184f9f2ba758027cd6c5ddb1b21e87b3c16f
```

逐条核验登记值，并实际执行登记 commit、HEAD 的 `git show …:scripts/solana/sqd_gap_repair.py | shasum -a 256` 及工作区文件哈希，全部相等：

```text
3f89aab13054be76711d85d15a3e4f21d6113c35c905f55a8e60edb31ba8446b
```

**4. 文档一致与上一轮 P2 处置**

| 上轮事项 | 本轮结论 |
|---|---|
| CHANGELOG 成本行 | **保留，不再列为缺陷。** [头部第 7 行](/Users/uravvv/.claude/tca-fix-txv1/CHANGELOG.md:7) 明确要求成本与质量指标；`:107` 属于这一规则允许的记录。 |
| “直接前代”歧义 | **已消除。** [CHANGELOG:104](/Users/uravvv/.claude/tca-fix-txv1/CHANGELOG.md:104) 改为“ACTIVE 已登记且 header 无 adopted 的历史 producer pending”，准确对应代码条件。 |
| 残尾处理对象不清 | **已消除。** [scan-schemas:1031](/Users/uravvv/.claude/tca-fix-txv1/references/scan-schemas.md:1031) 区分当前 pending 恢复时截除、来源 pending 仅解析忽略，与两条实现路径一致。 |
| “发现任何一侧后续改写”过满 | **已消除。** CHANGELOG:105 与 [scan-schemas:1029](/Users/uravvv/.claude/tca-fix-txv1/references/scan-schemas.md:1029) 均收窄为核对清单所列证据大小与哈希，同时说明不能隔离共享 inode 的原地改写，与深验行为一致。 |

[data-pipeline-solana-capture.md:198](/Users/uravvv/.claude/tca-fix-txv1/references/data-pipeline-solana-capture.md:198) 对认领接口、登记、深验摘要、可信来源和 producer 换代的说明也与实现一致。三处措辞修订未引入新的不准确；除按规则保留的成本质量记录外，未发现本轮新增施工叙述混入操作说明。

**仍存 P0/P1：无。仍存 P2：无。** `.staging_b3/tmp` 未创建成功，结束时确认不存在，无本轮临时内容需要清理。
[2026-09-23T08:51:06.676Z] Turn completed.

[2026-09-23T08:51:06.837Z] Final output
# 收官 review r2: PASS

**未发现仍存的 P0/P1；上一轮四条 P2 已按本轮要求处置，无新增 P2。** 三项测试仍被只读沙箱阻断，已实际执行并记录错误尾行；按本轮判定规则，以代码审查和补充内存核验为依据，不将环境阻断算作代码缺陷，也不宣称完整回归已通过。

审查对象：`fix/solana-txv1`，HEAD `2b8d1298`，对比 main `1624b860`。全程离线、未调用 RPC、未读取禁读目录，未修改文件或 commit；结束时工作区干净。

**1. 原问题已解**

- 对 main 的生产代码做 AST 统计：**13 个文件、17 处数字上限**；HEAD 为 **0 处**。
- [endpoint_identity.py:13](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/endpoint_identity.py:13) 定义 `SOLANA_MAX_SUPPORTED_TX_VERSION = 1`。
- [producer `_rpc_body`:639](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:639) 调用共享模板；[repair_getblock_body:1214](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:1214) 默认使用该常量。与 `main...HEAD` 差异一致。
- 全目录搜索仍会命中测试中的数字：版本 1 独立期望体及版本 0 负向夹具。因此准确结论是“**生产代码无写死数字上限**”。

已执行的离线复现核心如下：

```python
with patch.object(repair, "repair_getblock_body",
                  wraps=exact.repair_getblock_body) as template:
    body = json.loads(json.dumps(repair._rpc_body(123456)))
    assert body["params"][1]["maxSupportedTransactionVersion"] == 1
    template.assert_called_once_with(123456)

assert exact.repair_getblock_body(123456)["params"][1][
    "maxSupportedTransactionVersion"] == 1

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

实际输出：

```text
PASS in-memory request: _rpc_body/repair_getblock_body maxSupportedTransactionVersion == 1
PASS in-memory injection rejected: hardcoded tx version: scripts/solana/sqd_gap_repair.py:640
PASS production literal audit: main=13 files/17 numeric literals; HEAD=0
```

**2. 认领机制与校验链**

| 核对点 | 证据与结论 |
|---|---|
| 来源与前代绑定 | [producer:828](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:828) 检查同 parent、目录名、参考源和来源 header 无 `adopted`；遍历已登记 ACTIVE 历史哈希重算前代 digest。没有限定必须是相邻版本。 |
| 最长前缀、保留来源 | [producer:854](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:854) 截取证据对齐的连续候选前缀，保留行字段；来源残尾仅解析时忽略。目标证据全部预验后链接，只有 EXDEV 回退复制，最后发布台账。 |
| 续跑重验 | [producer:729](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:729) 校验 header、认领记录、证据和指纹；`:783` 重算前代 digest，核对来源名与候选前缀。 |
| 发布重验 | [producer:1542](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:1542) 再验 header 和认领记录；`:1611` 调用深验，通过后才更新正式指针。 |
| 独立深验 | [validator:1340](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:1340) 校验认领字段、登记与来源名；`:1357`、`:1387` 核对参考源指纹；`:1523` 重算当前及前代 digest，并校验排序候选前缀。 |

E27(d) 源码覆盖确认：

- [测试:921](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:921) 截获版本 1 请求；`:934` 明确断言只请求 `slots[1:]`。
- [测试:980](/Users/uravvv/.claude/tca-fix-txv1/scripts/tests/test_sqd_gap_repair.py:980) 修改台账并同步外层大小、哈希后，要求深验拒绝八类篡改；包括同时改前代 digest 和 source，能实际触达摘要重算。`:1006` 恢复后正向通过。
- `:1024` 对续跑的前缀乱序、错误来源名分别拒绝并恢复通过；后续还覆盖十二个认领故障向量及提交前后恢复边界。

**覆盖边界：** E27(d) 并未对“续跑／发布／深验 × 每个字段”做完整独立注入矩阵。发布重验由代码链路确认，不能扩大成全部场景均有独立测试。

**自证情况：** `:870` 用生产侧 `compute_plan_digest` 构造旧摘要，`:879` 用共享 `_repair_getblock_params_digest` 构造旧请求摘要；校验侧复用这些函数，这部分不能独立证明摘要算法。`:941` 手写版本 1 请求体并自行哈希，属于独立期望；`:959` 的两套摘要实现比较属于交叉验证。

本轮另执行了内存夹具，真实调用认领、续跑校验和任务调度逻辑，仅替换文件及传输操作：

```text
PASS independent JSON/hash oracle: current/predecessor digest and coverage/beta union
PASS memory-backed adoption/resume: longest prefix=1; original row and torn source bytes preserved
PASS memory resume: 8 tamper vectors rejected/restored; wrong row fingerprint never marked complete
PASS memory scheduling: workers=1/2 fetch only [20,30], completed slot 10 skipped
PASS memory checks complete; filesystem/RPC operations mocked, no end-to-end suite claim
```

未发现放开任意请求摘要、取消同案绑定或跳过发布深验。版本 `0..1` 的接纳范围有界；来源真实性仍是文档明确声明的输入前提。

**3. 回归与 producer 登记**

已先执行 `mkdir -p .staging_b3/tmp`，实际返回：

```text
mkdir: .staging_b3/tmp: Operation not permitted
```

随后各测试均设置 `TMPDIR="$PWD/.staging_b3/tmp"`、`MPLCONFIGDIR="$HOME/.matplotlib"`、`PYTHONDONTWRITEBYTECODE=1`，使用 `python3 -B scripts/tests/…` 执行。三项测试的夹具显式指定 `/private/tmp`，因此也不会被 `TMPDIR` 覆盖。

| 命令 | 退出码 | 实际尾行 |
|---|---:|---|
| `test_sqd_gap_repair.py` | 1 | `PermissionError: [Errno 1] Operation not permitted: '/private/tmp/sqd-repair-cas-8mtjfbec'` |
| `test_batch8_repair_scale.py` | 1 | `PermissionError: [Errno 1] Operation not permitted: '/private/tmp/batch8-keys-hw5cy4us'` |
| `test_batch7_validator_coverage_gaps.py` | 1 | `PermissionError: [Errno 1] Operation not permitted: '/private/tmp/b7-gap1-58tydiga'` |
| `invariant_scan.py` | 0 | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| `test_producer_registry_current.py` | 0 | `producer registry: 0 FAIL` |
| `changelog_lint.py` | 0 | `PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 83 条 + 归档 139 条` |
| `docs_lint.py --all` | 0 | `PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）` |
| `test_version_consistency.py` | 0 | `PASS: M-03 version metadata consistent at 9.1.0` |

前三项均因创建夹具目录失败而终止，**未跑到测试成功尾行，E27(d) 本轮未完整执行**。

[producer_history.py:235](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/producer_history.py:235) 起四条 9.1.0 登记覆盖 cache、bundle、coverage-resolution、pointer，全部 ACTIVE，commit 均为：

```text
7846184f9f2ba758027cd6c5ddb1b21e87b3c16f
```

逐条核验登记值，并实际执行登记 commit、HEAD 的 `git show …:scripts/solana/sqd_gap_repair.py | shasum -a 256` 及工作区文件哈希，全部相等：

```text
3f89aab13054be76711d85d15a3e4f21d6113c35c905f55a8e60edb31ba8446b
```

**4. 文档一致与上一轮 P2 处置**

| 上轮事项 | 本轮结论 |
|---|---|
| CHANGELOG 成本行 | **保留，不再列为缺陷。** [头部第 7 行](/Users/uravvv/.claude/tca-fix-txv1/CHANGELOG.md:7) 明确要求成本与质量指标；`:107` 属于这一规则允许的记录。 |
| “直接前代”歧义 | **已消除。** [CHANGELOG:104](/Users/uravvv/.claude/tca-fix-txv1/CHANGELOG.md:104) 改为“ACTIVE 已登记且 header 无 adopted 的历史 producer pending”，准确对应代码条件。 |
| 残尾处理对象不清 | **已消除。** [scan-schemas:1031](/Users/uravvv/.claude/tca-fix-txv1/references/scan-schemas.md:1031) 区分当前 pending 恢复时截除、来源 pending 仅解析忽略，与两条实现路径一致。 |
| “发现任何一侧后续改写”过满 | **已消除。** CHANGELOG:105 与 [scan-schemas:1029](/Users/uravvv/.claude/tca-fix-txv1/references/scan-schemas.md:1029) 均收窄为核对清单所列证据大小与哈希，同时说明不能隔离共享 inode 的原地改写，与深验行为一致。 |

[data-pipeline-solana-capture.md:198](/Users/uravvv/.claude/tca-fix-txv1/references/data-pipeline-solana-capture.md:198) 对认领接口、登记、深验摘要、可信来源和 producer 换代的说明也与实现一致。三处措辞修订未引入新的不准确；除按规则保留的成本质量记录外，未发现本轮新增施工叙述混入操作说明。

**仍存 P0/P1：无。仍存 P2：无。** `.staging_b3/tmp` 未创建成功，结束时确认不存在，无本轮临时内容需要清理。
