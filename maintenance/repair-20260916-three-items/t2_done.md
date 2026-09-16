# 施工 T2：停工（改动已实施，全套验收受环境阻断）

## 范围与开工核验

- 工单：workorder_t2.md v2；已全文读取，并读取两轮复核记录。
- 分支：fix/three-items-20260916；开工 git status --short 输出为空。
- 已用 nl -ba 核验施工前 :145/:147/:148/:149/:150/:153/:222/:265，全部吻合，无锚点停工情形。
- 离线施工；未执行 commit 或 Git 写操作；本人未读取或修改用户禁止目录。

## 改动文件清单

- references/report-template.md：工单指定七处替换、一处新增。
- scripts/tests/test_repair_batch_d.py：指定位置原样插入九行附录 F 绿例；与 HEAD 对比确认原用例未改。
- maintenance/repair-20260916-three-items/ 证据文件：t2_red_evidence.txt、t2_green_evidence.txt、t2_byte_evidence.txt、t2_docs_lint.txt、t2_docs_lint_all.txt、t2_run_all_evidence.txt、t2_done.md。
- scripts/report/a5_report_seal.py 与 HEAD 字节一致；未改 CHANGELOG/VERSION/pyproject 或其他施工文件。

## 八处 UTF-8 字节差

改前 wc -c：42499；改后：42491；净减 8，满足 ≤42499。

| 施工前行号 | 字节差 |
| --- | ---: |
| 145 | +20 |
| 147 | -6 |
| 148 | -27 |
| 149 | -17 |
| 150 | -15 |
| 153 后新增 F | +120 |
| 222 | -83 |
| 265 | 0 |

## 测试结果

非 RED 型：预期 GREEN（模板改动零代码，闸未变）。先加入测试、保持旧模板 42499 字节运行，再修改模板并复跑；两次结果均为：

```text
ok    2.1 绿例：披露在附录 F、正文只写'见附录 F' → DISCLOSED
BATCH D 全部通过
exit_code=0
```

命令：python3 scripts/tests/test_repair_batch_d.py。完整输出分别在 t2_red_evidence.txt 与 t2_green_evidence.txt。

python3 scripts/tests/docs_lint.py：

```text
PASS: 45 个文档，引用无断链、粗体配对完整
exit_code=0
```

python3 scripts/tests/docs_lint.py --all：

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
exit_code=0
```

## run_all 实际结果

按指定命令启动，并 wait 等进程结束后读取日志；未使用管道 tail：

```sh
nohup python3 scripts/tests/run_all.py > /tmp/run_all_t2.log 2>&1 &
```

共 149 项：147 PASS、2 FAIL。原始日志 /tmp/run_all_t2.log；完整副本 t2_run_all_evidence.txt。结果行：

```text
FAIL(rc=1)  test_batch3_solana_vertical_slice.py (无输出)
FAIL(rc=1)  test_batch3_evm_vertical_slice.py (无输出)
      PASS  test_repair_batch_d.py   BATCH D 全部通过
2 项失败——修完再收工
run_all exit_code=1
```

两个失败均在 ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler) 的 socket.bind 阶段：

```text
PermissionError: [Errno 1] Operation not permitted
```

对应测试行：test_batch3_solana_vertical_slice.py:625；test_batch3_evm_vertical_slice.py:281。当前执行环境阻止本地监听，因此不能报告全套通过。没有修改生产代码、测试隔离或权限配置来绕过限制。
启动 shell 另输出 nice(5) failed: operation not permitted；进程实际完整运行并产生上述汇总。

## 与工单差异及遗留

- 施工文本、插入位置、字节数均无差异；git diff --check 通过。
- 验收差异：run_all 未达到全绿，故最终状态为停工，保留已实施改动。
- 遗留：需要允许本地端口绑定的执行环境完成全套验收；本次没有权限升级或范围外修复。
- 工单指定的 Fable 本机 APU 0914 已封口报告复验不由 Codex 执行，本次未做。
