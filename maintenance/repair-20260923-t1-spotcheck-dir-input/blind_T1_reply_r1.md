# 盲审 T1：FAIL

审对象：HEAD `38d547f53f68ddd5dfbe63f7fbffa1ddbc226de1`，基线 `b52cbed`。

**b)/c) 静态核验通过，未发现已证实的代码缺陷；但 a) 四组独立终点验证均受沙箱阻塞，未满足 e) 的 PASS 条件。** d) 的临时目录错误按要求豁免，不计真实 FAIL。报告全文已打印到 stdout，未写文件。

**T1-B1-01：a) 终点验收未闭合**

- 文件:行：`scripts/lib/time_spotcheck.py:431`；`scripts/report/shared_release_receipt.py:1045`。
- 事实：独立脚本已通过 `git show b52cbed:...` 将基线生产者、消费者载入内存，未调用新增测试帮助函数。目录生产者、目录消费者及错绑、清单自洽重绑、CSV 兼容性四组均在创建临时夹具时阻塞，未进入计划生成及真实调用。
- 结果尾行：`INDEPENDENT ENDPOINT: completed=0/4, SANDBOX-BLOCKED=4/4`。
- 后果：基线缺陷、HEAD 放行／拒收以及 CSV 错误文本一致性，均缺少独立运行证据。
- 建议：调度方在允许创建临时夹具的本机环境补跑 a) 四组，再判最终 PASS。目前没有据此要求修改生产代码。

**T1-B1-02：d) 纵切片测试受环境阻塞**

- 文件:行：`scripts/tests/test_batch3_evm_vertical_slice.py:283`。
- 事实：`ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 绑定端口时报 `PermissionError: [Errno 1] Operation not permitted`。
- 后果：纵切片验证未完成。该错误未证明产品缺陷，也不属于本轮明确豁免的临时目录错误。
- 建议：在允许 loopback 监听的本机环境原样补跑。

实际核过的项目：

- 生产者严格只有私有 `_bound_input_ref`、既有 try 内一行接线及 `"input": bound_input` 三处变化；撤销三处后与基线逐字一致。
- 消费者文件分支保留 identity → 同一实物 → manifest 顺序，并通过 AST 对照确认；目录分支按要求核清单身份、案根内目录及末级非 symlink，不重算目录哈希。
- 指定七个核心文件相对基线零改动。
- diff 恰为指定八文件，尾行：`8 files changed, 137 insertions(+), 18 deletions(-)`。
- 基线与 HEAD 均为：`SKILL.md` **8021 B**、references Markdown **929092 B**、commands-staging Markdown **8789 B**。总量使用 Git 对象大小元数据核算，未读取 attic 正文。
- references 第 158 行仅替换 `merged input ` → `文件/清单`，**326 → 326 B**。
- 三处版本均为 **9.0.3**；CHANGELOG 索引与详细段在场。
- 八个文件的工作树内容与 HEAD 一致；开始、结束的 `git status --short` 均无状态条目。

实跑命令与结果：

| 命令 | 结果／尾行 |
|---|---|
| `python3 -B scripts/tests/test_anchor_plan_v3.py` | SANDBOX-BLOCKED；`anchor-plan v3: 9/16 PASS`，其余七项均为临时目录错误 |
| `python3 -B scripts/tests/test_time_spotcheck.py` | SANDBOX-BLOCKED；临时目录错误 |
| `python3 -B scripts/tests/test_recon_deep_reverify.py` | SANDBOX-BLOCKED；临时目录错误 |
| `python3 -B scripts/tests/test_handoff_manifest.py` | SANDBOX-BLOCKED；临时目录错误 |
| `python3 -B scripts/tests/test_audit_release_gate.py` | SANDBOX-BLOCKED；临时目录错误 |
| `python3 -B scripts/tests/test_batch3_evm_vertical_slice.py` | 环境阻塞；`PermissionError: [Errno 1] Operation not permitted` |
| `python3 -B scripts/tests/invariant_scan.py` | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0` |
| `python3 -B scripts/tests/changelog_lint.py` | `PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 82 条 + 归档 139 条` |

五个测试的共同错误原文：

```text
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']
```

工单差异：指定 `workorder_T1.md:1` 当前为 **v4**，其声明相对 v3 仅增加夹具根路径 `Path(td).resolve()`。本次按你明确列出的验收条件判断，未将该归一化判为缺陷。

纪律披露：未读取 `~/.codex/` 或 memories，未直接读取禁读历史目录、施工／复核报告或证据文件；指定测试按原命令运行。未修改文件、未 commit、未发出外部网络请求。
