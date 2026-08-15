# 工单末刀：中心登记独立收口施工报告

## 状态

末刀施工已按 `workorder_FINAL.md` 与调度方补充裁决完成。中心登记静态校验通过；全量 suite 为 **103/105 PASS**，仅两个 loopback 纵切片在当前沙箱的 `socket.bind` 处触发 `PermissionError: [Errno 1] Operation not permitted`，与工单预告一致，均未进入业务断言。

全程未执行任何 git 命令。

## A. run_all.py 挂载

在既有追加块区末尾、`main()` 定义之前新增工单指定注释与追加块，未改主列表：

- `test_evm_observation_nonempty_code.py`
- `test_arbitrum_exploration_cli.py`
- `test_recon_deep_reverify.py`
- `test_gmgn_divergence_note.py`

静态展开后 `SUITE` 正好 105 项，以上四项位于末四位；全量运行中四项均 PASS。

## B. 契约中心登记

### rg 定位结果

- `gmgn-divergence-note/v1`：`references/data-pipeline-evm-recon.md`。
- `evm-reconciliation-receipt/v3`：原先仅生产/消费代码命中；依补充裁决在 `references/data-pipeline-evm-recon.md` §5 增加自然表述后，该文档成为权威文档命中点。既有黄灯制正文与三条旧 needle 未改。
- `time-spotcheck/v3`：同时命中 `references/analyze-workflow.md` A2 摘要与 `references/data-pipeline-evm-recon.md` §13 完整产物契约。按主工单“多处命中挂语义权威”规则，选择后者；阶段为 A2。

### 新增条目

`scripts/tests/contract_manifest.json` 新增三条 `kind: required`：

| ID | authority_file | needle | stages |
|---|---|---|---|
| CT-RECON-01 | `references/data-pipeline-evm-recon.md` | `gmgn-divergence-note/v1` | A2 |
| CT-RECON-02 | `references/data-pipeline-evm-recon.md` | `evm-reconciliation-receipt/v3` | A2 |
| CT-RECON-03 | `references/data-pipeline-evm-recon.md` | `time-spotcheck/v3` | A2 |

三条均严格只有 `id/kind/authority_file/needle/stages` 五个字段。`scripts/tests/contract_ids_snapshot.json` 已按整体字典序插入三个 ID；manifest 与快照均为 152 个唯一 ID，集合双向一致。

## C. 验收摘要

完整逐条输出与退出码见 `maintenance/repair-20260815-g2/final_center_green.log`。

| 命令 | 结果 |
|---|---|
| `python3 scripts/tests/docs_lint.py --all` | exit 0；58 个文档全量 lint PASS |
| `python3 scripts/tests/test_contract_routes.py` | exit 0；注册表、ID 快照与路由闭合 PASS |
| `python3 scripts/tests/invariant_scan.py` | exit 0；62 producers / 85 consumers / 63 transport / 54 atomic writes / 58 entrypoints / 0 exceptions |
| `python3 scripts/tests/invariant_scan.py --self-test` | exit 0；删除点与新增点两个注入反例均 RED |
| `python3 scripts/tests/run_all.py` | exit 1；103/105 PASS，两个 loopback EPERM |

全量 suite 的两个非业务失败：

1. `test_batch3_solana_vertical_slice.py`：`ThreadingHTTPServer(("127.0.0.1", 0), ...)` 在 `socket.bind` 报 EPERM。
2. `test_batch3_evm_vertical_slice.py`：同一 loopback bind 边界报 EPERM。

需由融合方在允许 loopback 的环境复跑这两项；当前结果不得称作 105/105 全绿。

## D. 改动清单与融合说明

施工文件：

- `scripts/tests/run_all.py`（仅新增末尾追加块）
- `scripts/tests/contract_manifest.json`
- `scripts/tests/contract_ids_snapshot.json`
- `references/data-pipeline-evm-recon.md`（补充裁决追加授权的一句 v3 产物说明）
- `maintenance/repair-20260815-g2/final_center_green.log`
- 本报告

未修改 `references/analyze-workflow.md`、`scripts/tests/invariant_manifest.json` 及其他生产、测试、版本或发布文件。

本刀可由融合方整刀重放；若与其他组的 `run_all.py` 追加块或契约 ID 发生上下文冲突，应按 union 合并，保留本刀四个 suite 项与三条 CT-RECON 条目。`CT-RECON` 专属前缀不会与其他组撞号。
