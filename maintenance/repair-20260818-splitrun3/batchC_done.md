# 批 C 完成报告｜版本收口批（v6.50.0 工程）

> 工作目录：`/Users/uravvv/.claude/worktrees/tca-splitrun3`  
> 基线 HEAD：`e1be99ab25c0a6f60091d7a7b635ab6097e532c8`  
> 执行日期：2026-08-18  
> 结论：工单四文件已落盘；版本与 CHANGELOG 验收通过；全量套件除部署同步预期红外，业务测试通过。未执行 git commit。

## 1. 落盘清单

- `VERSION`：`6.48.1` → `6.50.0`
- `pyproject.toml:15`：`version = "6.50.0"`
- `SKILL.md:23`：`skill-version: 6.50.0`
- `CHANGELOG.md`：新增 6.50.0 索引行与详情条目；保留跳过 6.49.0 的占号说明及 CT-SEMANTIC-61/62、CT-BANNED-16 点名；回归行按实跑结果改写。

## 2. 五栏与先红后绿证据

### 写入前

`python3 scripts/tests/changelog_lint.py`：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 38 条 + 归档 139 条
```

`python3 scripts/tests/test_version_consistency.py`：

```text
PASS: M-03 version metadata consistent at 6.48.1
```

同族现状核对确认四个版本锚点均为 6.48.1，CHANGELOG 中无 6.49.0/6.50.0 既有条目。

### 红阶段

仅将 `VERSION` 改为 `6.50.0`、其余版本锚点尚未同步时运行：

```text
$ python3 scripts/tests/test_version_consistency.py
AssertionError
exit=1
```

断言命中 `project["project"]["version"] == version`，证明版本不一致守卫真实转红。

### 绿阶段

四处同步后以及回归行实况改写后，均再次运行：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 39 条 + 归档 139 条
PASS: M-03 version metadata consistent at 6.50.0
```

`git diff --check -- CHANGELOG.md VERSION pyproject.toml SKILL.md`：exit 0，无输出。

## 3. run_all 全量验收

工单原命令完整运行至结束：

```text
$ python3 scripts/tests/run_all.py > /tmp/splitrun3_batchC_suite.log 2>&1
exit=1
114 PASS / 117 total
3 项失败——修完再收工
```

原始失败清单：

1. `test_commands_deploy_sync.py`：工单允许的预期红。`token-analyze-1.md`、`token-analyze-2.md` 的 staging/deployed SHA-256 不一致，部署版 `token-analyze-3.md` 缺失；部署 cp 明确不在本工单内，须合并 main 后在 canonical checkout 执行。
2. `test_batch3_solana_vertical_slice.py`：沙箱内创建 `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 时 `socket.bind` 报 `PermissionError: [Errno 1] Operation not permitted`，未进入业务断言。
3. `test_batch3_evm_vertical_slice.py`：同为 loopback `socket.bind` 的 `PermissionError: [Errno 1] Operation not permitted`，未进入业务断言。

两项环境红在允许 loopback 的环境中按原测试脚本单项复跑：

```text
$ python3 scripts/tests/test_batch3_solana_vertical_slice.py
PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release

$ python3 scripts/tests/test_batch3_evm_vertical_slice.py
PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
```

为严格满足“全量红项清单只有部署同步一项”，在允许 loopback 的环境中再次完整运行 `run_all.py`，没有用单项结果替代全量汇总：

```text
$ python3 scripts/tests/run_all.py > /tmp/splitrun3_batchC_suite_permitted.log 2>&1
exit=1
116 PASS / 117 total
1 项失败——修完再收工
```

该次全量运行中 `test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py` 均 PASS；完整失败清单只有：

```text
test_commands_deploy_sync.py  # EXPECTED RED：部署 cp 待合并 main 后执行
```

最终全量日志同时确认 `docs_lint.py --all`、`changelog_lint.py`、`test_version_consistency.py`、`test_repair_batch3_gates.py` 等其余 116 项均 PASS。受限沙箱首跑日志保存在 `/tmp/splitrun3_batchC_suite.log`，允许 loopback 的最终全量日志保存在 `/tmp/splitrun3_batchC_suite_permitted.log`。

## 4. 自审

- 版本五处同值：VERSION、pyproject、CHANGELOG 索引、CHANGELOG 详情标题、SKILL 注释均为 `6.50.0`。
- CHANGELOG 活跃窗口严格降序；6.49.0 跳号原因按工单保留。
- 新条目仅记录 split-run、ET-1、外包纪律、契约、测试和部署状态，未写入任何代币分析结论。
- CT-SEMANTIC-61/62、CT-BANNED-16 的 manifest 引用检查已由全量 `docs_lint.py --all` PASS 证明无悬空。
- 本批只改工单四个白名单文件，并新增工单明确要求的本 done 报告；未改其他文件。
- 未执行 git commit，未执行部署 cp。

## 5. 后续唯一待办

合并 main 后，在 canonical checkout 执行部署 cp，并复跑 `test_commands_deploy_sync.py` 与 `run_all.py`，使部署同步预期红转绿。
