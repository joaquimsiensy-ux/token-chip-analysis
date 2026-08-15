# 工单 A 完成报告（repair-20260815-g3）

## 施工结果

工单四项任务已按 1→2→3→4 顺序完成。文档与代码现状不存在实质性冲突；工单所列行号有正常漂移，均按标题和内容定位施工。未改变任何运行时代码，也未注册新测试到 `run_all.py`。

## 改动文件清单

- `references/analyze-workflow.md`：A0 EVM 记账预检改用 `--exploration` 和固定探索文件名，保留原 exit 码语义及 Solana 流程。
- `references/analyze-workflow.md`：A2 在 `observe_supply.py` 与 `supply_truth_gate.py` 之间加入 bundle formal 重跑，并声明 A2 formal 为唯一 canonical 结果。
- `references/analyze-workflow.md`：A4 第 5 步后补入机器已强制、机器未强制及路数与异构性责任边界。
- `references/research-workflows.md`：JSON 骨架改为 entrypoint 从 runner 环境变量逐字写入 artifact，runner 只校验、不静默补入。
- `references/research-workflows.md`：claim-review 产物约束后补入与 `analyze-workflow.md` 一致的机器化边界声明。
- `scripts/tests/test_g3_docs_guards.py`：新增纯标准库独立守卫，覆盖 F-08 A0/A2 分段与顺序、F-13 runner 边界、F-05 两文档边界词。
- `maintenance/repair-20260815-g3/workorder_A_done.md`：记录本工单实际改动、验收输出与边界自查。

## 验收输出摘要

### `python3 scripts/tests/docs_lint.py --all`

```text
exit code: 0
PASS: 58 个文档
引用无断链、粗体配对完整（--all 全量模式）
```

### `python3 scripts/tests/test_g3_docs_guards.py`

```text
exit code: 0
PASS: F-08 A0 exploration command / F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

### `python3 scripts/tests/test_commands_deploy_sync.py`

```text
exit code: 0
PASS: 3 份 staging/部署命令
SHA-256 逐文件一致
```

### `python3 scripts/tests/test_repair_batch_a.py`

```text
exit code: 0
预期负向用例按设计打印 argparse error、gate FAIL 与拒绝信息
各具名回归均打印 PASS
PASS batch A F-01/F-02 regressions 45/45
```

### 附加语法检查：`python3 -m py_compile scripts/tests/test_g3_docs_guards.py`

```text
exit code: 0
stdout: empty
stderr: empty
```

## 边界自查

- 未动边界外文件；有意施工的仓库文件仅为工单白名单中的上述四个路径。
- 未修改 `SKILL.md`、`VERSION`、`CHANGELOG.md`、`scripts/tests/run_all.py`、`maintenance/repair-20260813-sixlens/r10_ledger.md` 或任何运行时代码。
- 未执行 add、commit、push，也未删除或覆盖既有文件。
- 所有新增文字与注释均使用中性的负向测试、守卫和边界表述。
