# 工单 末刀：中心登记独立收口

> 执行者：codex（纯施工，**禁止任何 git 操作**）
> 前置：四刀（F-04/F-10/F-07/F-09 含补充轮）已全部合入本分支。
> 本刀是集中所有"中心文件"改动的独立收口刀，融合方可整刀重放或丢弃自行统一。

## A. run_all.py 挂载新测试

在 `scripts/tests/run_all.py` **文件末尾**按仓库近版惯例新增一个带注释的追加块（不动主列表），挂本工程 4 个新测试：

```python
# repair-20260815-g2（F-04/F-07/F-09/F-10）：观测件收紧/对账深重验/GMGN 黄灯/探索档 CLI
SUITE += [
    'test_evm_observation_nonempty_code.py',
    'test_arbitrum_exploration_cli.py',
    'test_recon_deep_reverify.py',
    'test_gmgn_divergence_note.py',
]
```

## B. 契约注册表新增三条（本组专属前缀 CT-RECON-xx，防并行撞号）

先 `rg -n "gmgn-divergence-note/v1|evm-reconciliation-receipt/v3|time-spotcheck/v3" references/` 确认各串实际所在的权威文档，然后：

1. `scripts/tests/contract_manifest.json` 新增三条 `kind:"required"`：
   - `CT-RECON-01`：needle `gmgn-divergence-note/v1`，authority_file 按 rg 实况（预期 `references/data-pipeline-evm-recon.md`），stages `["A2"]`；
   - `CT-RECON-02`：needle `evm-reconciliation-receipt/v3`，authority_file 按 rg 实况，stages `["A2"]`；
   - `CT-RECON-03`：needle `time-spotcheck/v3`，authority_file 按 rg 实况（若在多个文档中出现，挂语义权威的一处），stages `["A2"]`。
   条目字段严格按既有白名单形状（id/kind/authority_file/needle/stages，不多不少）。
2. `scripts/tests/contract_ids_snapshot.json`：把三个新 ID 插入并**保持整体排序**。

## C. 验收（全部本地命令，逐条落输出到 `final_center_green.log`）

- `python3 scripts/tests/docs_lint.py --all`
- `python3 scripts/tests/test_contract_routes.py`
- `python3 scripts/tests/invariant_scan.py` 与 `python3 scripts/tests/invariant_scan.py --self-test`
- `python3 scripts/tests/run_all.py`（预期 105 项，仅两个 loopback 纵切片在你沙箱内 EPERM，如实记录留调度方）

## D. done 报告

`workorder_FINAL_done.md`：A/B 改动清单、rg 定位结果、验收输出摘要、给融合方的说明（本刀可整刀 cherry-pick/重放；与他组的 run_all 追加块/契约 ID 若冲突按 union 合并，CT-RECON 前缀不会撞号）。

## 硬约束

- 只改：`scripts/tests/run_all.py`（限末尾追加块）、`scripts/tests/contract_manifest.json`、`scripts/tests/contract_ids_snapshot.json`。
- 禁碰：其余一切文件（含 invariant_manifest——四刀已跟刀登记完毕）。
- 禁止一切 git 操作。
