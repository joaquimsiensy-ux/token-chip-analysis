# 盲审 F05：PASS

审查 HEAD：`979568fa573efe2dc8525580928ec5094bb4d49c`。已确认运行的 scripts 与 HEAD 一致。**a／b／c 全过；d 为 1 项 PASS、5 项 SANDBOX-BLOCKED，无真实 FAIL。**报告全文已打印到 stdout。

独立复现采用纯内存文件系统，复用 `build_closeout_case`，执行真实 `price_check.main()` 和 closeout 的 `check` 命令入口。第二源使用离线替身；文件 I/O、Python 子进程在内存中适配，生产校验函数未替换。各次完整检查均保留 12 项 checks，其他 11 项无 BLOCK。

下表行号均指 [stage2_closeout.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py)。

| 独立复现情形 | 实际结果 | 行号 |
|---|---|---|
| 主 50／副 100，三点 FAIL | 生产者退出 2；基线 check PASS；HEAD check BLOCK、退出 2 | 274 |
| verdict 改 PASS，points 仍 FAIL | BLOCK，提示“与 points 重算一致（FAIL）” | 271、274 |
| 主源哈希不一致 | BLOCK，指向 `price_file_sha256` | 284 |
| 旧收据缺 `price_file_sha256` | BLOCK，要求重跑生产者 | 281 |
| ALL_SKIP | 生产者退出 3；check BLOCK、退出 2 | 274 |
| 内联纯申报 dict，无 receipt | BLOCK，提示“纯申报对象不放行” | 254 |
| 主 50／副 54，三点 WARN | check PASS、退出 0，NOTE 记录 3 点 | 287 |
| 内联有效 receipt 引用 | check PASS、退出 0 | 250 |

核心反例实际拒绝文案：

```text
WORKORDER BLOCK: bindings.price_source_checks.verdict: PASS|WARN（FAIL/ALL_SKIP 禁入装配：换源或人工裁决后重跑 price_check） != FAIL
```

WARN 实际文案：

```text
NOTE: 价格双源 WARN 点 3 个（>5% 过目口径，见 report-template 2b）
```

实际核过的工单约束：

- price_check 收据仅新增 `price_file_sha256`；解析、第二源、阈值与退出逻辑未改。
- 穷举 **340 组**合法状态组合全部一致：PASS 26、WARN 90、FAIL 220、ALL_SKIP 4；基线与 HEAD 的 stdout、退出码一致。
- closeout 保持 **12 项 checks**；`workorder_errors` 仍返回 `(errors, notes)`，前缀保持 `WORKORDER BLOCK: `。
- **19 条既有 mutation 全部 BLOCK**，文案均含对应 field 名；主源绝对路径和符号链接各保持一条主源路径诊断。
- AST 对照确认：除 `workorder_errors` 接入 helper 外，closeout 其他既有函数未改。

新增测试 [price_receipt_content_enforced](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_closeout.py:621) 在 HEAD 完整 GREEN。通过 `git show` 载入基线生产源码后，同一测试在第 **635 行**语义断言处 RED，消费端 errors 为 `[]`。逐段独立核验：**1／2／3／4／5／6／7a 均 RED，7b GREEN**；生产者均先达到预期退出码。

单日夹具在基线和 HEAD 均退出 1、不生成收据：

```text
[fatal] 价格序列过短（1 天），抽不成首/中/尾
```

HEAD 的[价格夹具](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_closeout.py:115) 已改成三日，本次 RED 来自消费端语义断言。

白名单核验命令及结果：

```text
git diff --stat 87f962b65310 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md

 scripts/prices/price_check.py         | 11 +++++
 scripts/report/stage2_closeout.py     | 63 ++++++++++++++++++++++++---
 scripts/tests/test_stage2_closeout.py | 80 ++++++++++++++++++++++++++++++++---
 3 files changed, 144 insertions(+), 10 deletions(-)
```

仅用文件元数据统计，三处字节数全部吻合：`SKILL.md = 8021 B`、`references/**/*.md = 930076 B`、`commands-staging/*.md = 8798 B`。

指定回归命令已原样实跑：

| 命令 | 结果 |
|---|---|
| `python3 -B scripts/tests/test_stage2_closeout.py` | SANDBOX-BLOCKED |
| `python3 -B scripts/tests/test_a4_gate.py` | SANDBOX-BLOCKED |
| `python3 -B scripts/tests/test_audit_release_gate.py` | SANDBOX-BLOCKED |
| `python3 -B scripts/tests/test_batch4_invariant_guards.py` | SANDBOX-BLOCKED |
| `python3 -B scripts/tests/test_exemption_guards.py` | SANDBOX-BLOCKED |
| `python3 -B scripts/tests/invariant_scan.py` | PASS，退出 0 |

五项受阻测试的共同错误尾行，临时目录自检亦相同：

```text
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']
```

invariant_scan 尾行：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

补充内存核验通过 `python3 -B -c '<内存审查代码>'` 执行，最终结果尾行：

```text
STATIC_AND_340_COMBINATIONS: PASS
F05_MEMORY_AUDIT: PASS; zero real filesystem writes; real checks unmodified
```

未运行 `test_stage2_reseal.py`；五项受阻测试及 reseal 由调度方本机补验。全程离线、未改文件、未 commit、未使用 stash；未读取 `~/.codex/`、memories 或两份禁读施工自述，未主动读取其他禁区。maintenance 仅阅读获准工单和裁决作为判据。
