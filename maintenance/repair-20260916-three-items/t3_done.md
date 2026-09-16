# 施工 T3: 完成

施工完成；全套测试未全绿：两项受沙箱 localhost 端口绑定限制失败，未冒充通过。

## 基线与范围

- 分支：`fix/three-items-20260916`；开工及完工 HEAD：`8d8787e67ae1229b3c906e63bcdc421ae9d2cc14`，未变化。
- 已通读仓库工单及四轮复核回复，开工用 `nl -ba` 逐条核对全部指定锚点，一致；开工 `git status --short` 为空。
- 离线；未 commit、未执行 Git 写操作；未读取禁止目录或以禁止 tag 作参考。既有生产代码安装目录 git 探测原样保留。
- `generate/verify/receipt/freeze` 及其他既有生产函数逐字不变。`main()` 仅新增两个 parser 和 dispatch 两项；新增函数位于原 `cmd_freeze` 前，T1 卫生扫描段保留。
- 最终 tracked diff 仅以下四个授权文件；`CHANGELOG`、`VERSION`、`pyproject` 未修改；`git diff --check` PASS。

## 改动文件

1. `scripts/report/handoff_manifest.py`：路径守卫、标准库只读 JSON/JSONL 查询、inspect 分页与深度、lookup 来源索引及分页；parser 在 1902–1920，dispatch 新两项在 1925。
2. `scripts/tests/test_handoff_manifest.py`：七组新增用例及辅助函数；登记在 1328，位于汇总 `print("=" * 40)` 之前、原 finally 清理之后；独立创建、逐一清理案根。
3. `references/split-run.md:72`：仅替换该行。
4. `references/context-discipline.md:27`：仅替换该行。
5. 本工单证据目录：`t3_red_evidence.txt`、`t3_green_evidence.txt`、`t3_docs_lint.txt`、`t3_byte_evidence.txt`、`t3_run_all_evidence.txt`、`t3_scope_evidence.txt`、本文件 `t3_done.md`。

## 新增函数与行号


### scripts/report/handoff_manifest.py

| 新增函数 | 行号范围 |
| --- | --- |
| `_readonly_case_file` | 1402–1408 |
| `_readonly_load` | 1411–1426 |
| `_readonly_page` | 1429–1432 |
| `_readonly_stats` | 1435–1437 |
| `_inspect_item` | 1440–1450 |
| `cmd_inspect` | 1453–1505 |
| `_lookup_address` | 1508–1513 |
| `_lookup_index` | 1516–1550 |
| `_lookup_text` | 1553–1559 |
| `cmd_lookup` | 1562–1610 |

### scripts/tests/test_handoff_manifest.py

| 新增函数 | 行号范围 |
| --- | --- |
| `test_t3_readonly_queries` | 531–863 |
| `invoke` | 546–555 |
| `inspect` | 557–558 |
| `lookup` | 560–561 |
| `test_inspect_tree` | 563–593 |
| `test_inspect_jsonl` | 595–600 |
| `test_inspect_guard` | 602–609 |
| `test_lookup_structures` | 611–642 |
| `test_lookup_complete_json` | 644–651 |
| `test_lookup_guard_and_pages` | 653–675 |
| `snapshot` | 677–690 |
| `test_readonly` | 692–808 |
| 包装脚本 `fd_path` | 706–710 |
| 包装脚本 `belongs` | 712–724 |
| 包装脚本 `hook` | 726–756 |

## RED → GREEN

- 修改生产代码前，按要求执行 inspect / lookup RED 命令；两者均 exit 2，stderr 原文分别含 `invalid choice: 'inspect'` / `invalid choice: 'lookup'`，见 `t3_red_evidence.txt`。
- `python3 -B scripts/tests/test_handoff_manifest.py` 最终结果：`handoff_manifest 契约测试全部通过（283 项）`，exit 0；完整输出见 `t3_green_evidence.txt:299`。
- 新增七组共 174 项检查，含参数与路径反例、完整 JSON、来源位置去重、审计监测器自检、所有正例逐条审计、去写位复跑和恢复后快照一致性。审计检测独立于退出码。
- 审计包装脚本及日志均位于案根外 scratch；检测整数 flags、rename 两端、符号链接词法路径、访问目标 realpath、dir_fd、未归属写事件与相邻目录边界；合成事件自检通过。
- 测试案根统一使用真实路径，避免 macOS `/var` 与 `/private/var` 别名影响词法归属；该修正后已完整重跑上述 283 项并通过。
- `python3 -B scripts/tests/docs_lint.py --all`：`PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）`，exit 0；见 `t3_docs_lint.txt`。

## 全套 run_all

按指定 `nohup python3 -B scripts/tests/run_all.py > /tmp/run_all_t3.log 2>&1 &` 启动，等待退出后读取并完整复制日志。证据文件与 `/tmp/run_all_t3.log` 逐字节一致。

run_all：147 项 PASS，2 项 FAIL，exit=1；两项 localhost socket.bind 被沙箱拒绝。

原始结果行：

```text
FAIL(rc=1)  test_batch3_solana_vertical_slice.py (无输出)
FAIL(rc=1)  test_batch3_evm_vertical_slice.py (无输出)
PASS  test_handoff_manifest.py handoff_manifest 契约测试全部通过（283 项）
2 项失败——修完再收工
run_all_exit=1
```

两条异常均为 `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` → `socket.bind` → `PermissionError: [Errno 1] Operation not permitted`：

- Solana 纵切片：`t3_run_all_evidence.txt:1–22`，失败源 `scripts/tests/test_batch3_solana_vertical_slice.py:625`。
- EVM 纵切片：`t3_run_all_evidence.txt:24–48`，失败源 `scripts/tests/test_batch3_evm_vertical_slice.py:281`。
- 汇总失败行位于证据文件 65–66，handoff PASS 在 126，最终失败数及退出码在 201、203。

未为沙箱端口限制修改代码或添加隔离。

## 文档字节

由改前、改后真实 `wc -c` 留证于 `t3_byte_evidence.txt`：

| 文件 | 改前 | 改后 | 差值 |
| --- | ---: | ---: | ---: |
| `references/split-run.md` | 28135 | 28130 | -5 |
| `references/context-discipline.md` | 9257 | 9256 | -1 |

## 与工单差异及遗留

- 功能、允许编辑区域和两条文档替换无偏离；测试使用自建最小查询夹具，不复用已删除的既有 main 案根。另覆盖 `.sealed` 合法目录、编码错误、无效首地址字段不回退、双成员表、非 EVM 大小写等既定行为边界。
- 首次 zsh 后台启动被 `nice(5) failed: operation not permitted` 拒绝，确认进程未存活、日志为空；改用 bash 执行同一 nohup 命令并 `wait` 获取真实退出码。该启动差异已在 `t3_scope_evidence.txt` 记录。
- 遗留：全套的两项端口绑定测试须在允许 localhost bind 的验收环境复核；当前不得宣称全套 PASS。
- FORGGIE 案卷实跑留给验收方（Fable），本次未访问仓库外案卷。
