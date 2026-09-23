# 盲审T2：PASS

审查 HEAD：`a906cf8267f3b42614a6387bd1188b7461ee49c9`；基线：`d2d6641`；依据工单 v3.1。

独立复现确认：存量文件输入收据的旧哈希在基线被拒，HEAD 四查放行；历史准入没有绕过路径、协议、查项及目录清单校验。b/c 全过，10 项指定测试全部退出 0，无 `SANDBOX-BLOCKED`。

**a）终点判据：通过**

旧生产者取证命令：

```sh
git show b52cbedf230218e5da46334cf99b7111235e8367:scripts/lib/time_spotcheck.py | shasum -a 256
```

输出：

```text
87bbad2246f07afa2db4b37a7289fff2fc6ac16387284411e75104e1109f0a39  -
```

登记条目的哈希、commit、script、protocol 均吻合。对应 `historical_producer_hashes(...)`：基线为空集，HEAD 包含该旧哈希。

独立复现用 `python3 -B -` 从标准输入执行，复用 `make_case`、`_produce_time`、`_produce_recon` 生成临时夹具，未调用新增回归测试函数。基线通过 `git show d2d6641:<文件>` 加载到内存，保留真实仓库的 `__file__`、`REPO`，同时使用基线登记表；没有替换消费者校验函数。

| 独立向量 | 实测结果 |
|---|---|
| 文件输入，收据和 wrapper 均为旧哈希，基线 | wrapper 层拒绝：`reconciliation time producer/runner is not current repository script` |
| 同一双层旧哈希夹具，HEAD | `validate_reconciliation_report` 四查通过 |
| wrapper 当前哈希、收据旧哈希，基线 | envelope 层拒绝：`reconciliation time receipt envelope invalid: producer hash mismatch` |
| 同一夹具，HEAD | 通过 |
| 当前生产者生成的当前哈希收据 | 基线、HEAD 四查均通过 |
| 旧哈希＋收据路径改为 `anchor_plan.py` | 拒绝：`producer hash mismatch` |
| 旧哈希＋wrapper 路径改为 `anchor_plan.py` | 拒绝：`producer/runner path is not whitelisted` |
| balance 收据使用旧时间哈希，分别保留原路径及改成时间脚本路径 | 两组均拒绝：`receipt envelope invalid: producer hash mismatch` |
| 收据哈希为 `"0"*64` | 拒绝：`producer hash mismatch` |
| 仅 wrapper 哈希为 `"0"*64` | 拒绝：`producer/runner is not current repository script` |
| 默认 `validate_receipt`，不传 allowed | 返回恰为 `["producer hash mismatch"]` |
| 收据 JSON 为 `[]` | 基线、HEAD 均抛 `ValueError`，含 `receipt must be an object` |
| EVM 其他全部查项、Solana 全部查项及 `time` | 历史集均为 `None` |
| owner/producer 非对象、path 为 list/dict 或错误脚本 | 返回 `None`，无提前类型异常 |
| 旧哈希＋v2 schema | 哈希关通过后拒绝：`unknown schema` |
| 陌生哈希＋v2 schema | 先拒绝：`producer hash mismatch` |

文件输入独立验证尾行：

```text
INDEPENDENT FILE AND SCOPE: ALL PASS
```

目录组另用 `python3 -B -` 执行：生成真实 Parquet 目录、真实 anchor plan，运行时间生产者及语义重放，仅替换外部 RPC 返回。

| 目录向量 | 实测结果 |
|---|---|
| 当前哈希＋合法目录清单 | 通过，生产者 `13/13` 一致 |
| 改成旧哈希，绑定保持合法 | 通过 |
| `inputs.input` 指向其他合法文件 | 拒绝：`directory input identity is not bound through the signed input manifest` |
| 修改清单正文，只更新时间收据引用 | 拒绝：`plan receipt envelope invalid: ['input input_manifest hash mismatch']` |
| 同步重绑清单、plan、plan receipt 和时间收据全部引用，但清单身份与签名身份不同 | 拒绝：`input manifest identity differs from signed identity` |

目录验证尾行：

```text
INDEPENDENT DIRECTORY TRUST CHAIN: ALL PASS
```

**b）修法一致性：通过**

执行 `git diff d2d6641 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`，并用 Python 做逐字节对照：

- `producer_history.py` 恰追加一条 ACTIVE 登记，六键完整、commit 为 40 位，历史源码可复现。
- `shared_release_receipt.py` 撤去私有 `_time_producer_history` 及基线 `:1221`、`:1459-1460` 两处接线后，与基线逐字节一致。
- `test_producer_registry_current.py` 仅扩充精确 `HISTORICAL_ONLY` 对、将原注释替换为一行；检查逻辑不变。
- `receipt_kernel.py`、`receipt_validate.py`、`time_spotcheck.py`、`handoff_manifest.py` 均与基线逐字节一致；工单其余指定不改文件也无差异。

**c）白名单与字节：通过**

指定 `git diff --stat` 结果：

```text
 CHANGELOG.md                                    |  8 +++
 SKILL.md                                        |  2 +-
 VERSION                                         |  2 +-
 pyproject.toml                                  |  2 +-
 references/data-pipeline-evm-recon.md             |  4 +-
 scripts/lib/producer_history.py                 |  8 +++
 scripts/report/shared_release_receipt.py        | 22 ++++++--
 scripts/tests/test_producer_registry_current.py |  9 ++--
 scripts/tests/test_recon_deep_reverify.py        | 70 +++++++++++++++++++++++++
 9 files changed, 115 insertions(+), 12 deletions(-)
```

| 核对项 | 实测 |
|---|---|
| 白名单 | 恰为指定九文件 |
| `SKILL.md` | 8021→8021 B，仅版本号变化 |
| `commands-staging` | 8789→8789 B，无改动 |
| references 改动 | 仅指定文件第 152、158 行 |
| 第 152 行，不含换行 | 111→110 B |
| 第 158 行，不含换行 | 326→320 B |
| references 总量 | 929092→929085 B；通过 Git blob 大小元数据统计，未读取禁读文档 |
| 四处版本 | 均为 9.0.4 |
| CHANGELOG | 索引行 200 B，详细段齐全 |

静态断言尾行：

```text
STATIC ALL PASS
```

**d）指定测试：全部通过**

统一设置 `PYTHONDONTWRITEBYTECODE=1`，`TMPDIR`、`MPLCONFIGDIR` 指向本次系统临时目录。以下命令退出码均为 **0**；列出结果尾行。

| 命令 | 结果尾行 |
|---|---|
| `python3 -B scripts/tests/test_producer_registry_current.py` | `producer registry: 0 FAIL` |
| `python3 -B scripts/tests/test_recon_deep_reverify.py` | `PASS test_recon_deep_reverify` |
| `python3 -B scripts/tests/test_anchor_plan_v3.py` | `anchor-plan v3: 16/16 PASS` |
| `python3 -B scripts/tests/test_time_spotcheck.py` | `time_spotcheck 契约测试全部通过（20 项）` |
| `python3 -B scripts/tests/test_handoff_manifest.py` | `handoff_manifest 契约测试全部通过（283 项）` |
| `python3 -B scripts/tests/test_audit_release_gate.py` | `PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过` |
| `python3 -B scripts/tests/test_batch4_invariant_guards.py` | `PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `python3 -B scripts/tests/test_exemption_guards.py` | `PASS: exemption guards (EX-01 full-F-03)` |
| `python3 -B scripts/tests/invariant_scan.py` | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0` |
| `python3 -B scripts/tests/changelog_lint.py` | `PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 83 条 + 归档 139 条` |

deep-reverify 与 anchor-plan 测试的 stderr 含预期负例诊断，分别包括非法锚点、`stop-before-rpc`；不属于测试失败。

**e）纪律与收尾**

全程离线、未 commit、未修改或新建仓库文件；未读取禁区及施工/复核自述文件。仅获准的 `changelog_lint.py` 子进程读取 archive。临时夹具、日志已清理，临时根目录不存在；`git diff --quiet HEAD --` 退出 0。

最终 `git status --short` 全文如下，输出为空：

```text
```
