# 盲审 T1 r2：PASS

审查 HEAD：`7e461a78a511f5f1af8ab50155cef8c6d2b3a66a`；基线：`b52cbed`。

四组终点独立复现通过，修法、白名单与字节约束全部通过。指定测试七项 PASS，一项按规则记为 **SANDBOX-BLOCKED**，无真实 FAIL。报告全文已打印到 stdout。

指定工单文件当前标题为 v4，注明的唯一增量是临时目录路径归一化；本轮仍按你明确列出的 v3 判据核验。

**独立终点**

自行创建 24 行 v2 Parquet 目录和对应 CSV，未调用新增测试的夹具或断言。两种输入均实际执行：

```text
python3 -B scripts/lib/anchor_plan.py --input <目录或CSV> --chain bsc --token 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --total-supply 10000 --decimals 0 --min-pct 0 --final-block 300 --boundary-blocks 110 --out-dir <临时案根>/plan
```

均 exit 0，产出计划、清单及收据，尾行显示 `矩阵点 4 + 强制点 9`。基线源码通过 `git show b52cbed:<源码路径>` 在内存加载。

1. **生产者**：mock 模块全局 `build_envelope`，运行真实非 dry-run `main()`，使用指定 RPC 参数，在任何 RPC 前受控终止。基线传入目录，真实收据核拒绝 `input is not a regular file`；HEAD 传入清单绝对路径，真实收据核成功封装。网络连接尝试为 0。
2. **目录消费者放行**：构造 plan、plan_receipt、input 三验引用。基线拒绝 `time plan input identity is not a regular file`；HEAD 放行并返回原计划。
3. **目录消费者拒收**：错绑计划文件，HEAD 拒绝 `directory input identity is not bound through the signed input manifest`；篡改清单正文并同步更新引用及计划输出哈希，保持计划身份不变，HEAD 拒绝 `input manifest identity differs from signed identity`。
4. **CSV 不变**：两版生产者均绑定 CSV 并成功封装；消费者正常放行、错绑拒收及错误文本一致。未重签清单篡改均拒绝；自洽更新引用后的清单正文篡改，两版文件分支均放行，保持既有行为。

独立脚本尾行：

```text
INDEPENDENT ENDPOINTS: ALL PASS; network attempts=0
TEMP FIXTURES REMOVED: PASS
```

**修法、白名单及字节**

- 生产者仅新增 `_bound_input_ref`、既有 try 内一行赋值及 `"input": bound_input`。AST 逆向还原后与基线一致。
- 消费者文件分支保留 identity → 同一实物 → manifest 顺序；目录分支核清单绑定和正文身份，检查案根内目录及末级非 symlink，不重算目录哈希。无新增函数或 import。
- 七个指定冻结生产文件全部零差异。
- 指定 `git diff --stat b52cbed HEAD -- …` 恰为八个白名单文件，合计 **137 insertions、18 deletions**。
- `SKILL.md`：**8021→8021 B**；`references/**/*.md`：**929092→929092 B**；`commands-staging/*.md`：**8789→8789 B**。
- references 第 158 行：**326→326 B**，仅将 `merged input ` 换成 `文件/清单`。
- 三处版本均为 **9.0.3**；CHANGELOG 索引、详细段在场，lint PASS。

**指定测试**

运行时设置 `PYTHONDONTWRITEBYTECODE=1 TMPDIR=/private/tmp`，子进程继承。

| 实跑命令 | 退出码及结果尾行 |
|---|---|
| `python3 -B scripts/tests/test_anchor_plan_v3.py` | 0；`anchor-plan v3: 16/16 PASS` |
| `python3 -B scripts/tests/test_time_spotcheck.py` | 0；`time_spotcheck 契约测试全部通过（20 项）` |
| `python3 -B scripts/tests/test_recon_deep_reverify.py` | 0；`PASS test_recon_deep_reverify` |
| `python3 -B scripts/tests/test_handoff_manifest.py` | 0；`handoff_manifest 契约测试全部通过（283 项）` |
| `python3 -B scripts/tests/test_audit_release_gate.py` | 0；`PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过` |
| `python3 -B scripts/tests/test_batch3_evm_vertical_slice.py` | 1；**SANDBOX-BLOCKED**；`PermissionError: [Errno 1] Operation not permitted` |
| `python3 -B scripts/tests/invariant_scan.py` | 0；`PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0` |
| `python3 -B scripts/tests/changelog_lint.py` | 0；`PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 82 条 + 归档 139 条` |

唯一受限点是 `test_batch3_evm_vertical_slice.py:283` 创建 `127.0.0.1` 测试服务器时，`socket.bind` 被沙箱拒绝；依规则不计 FAIL，留待调度方本机补验。

未读取 `~/.codex/` 或 memories，未主动读取禁读路径；指定测试自身依赖读取除外。未修改或新建仓库文件，未 commit。独立夹具及测试遗留的七个临时目录均已清理。

最终 `git status --short` 全文（空）：

```text
```
