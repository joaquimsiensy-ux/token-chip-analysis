# Batch 12 完成报告

## 结论

- 工单实现完成；未 commit。
- 本批真实代码／契约失败为 **0**。
- 最终 `run_all.py` 共登记 136 项：**134 PASS / 2 FAIL**。两项 FAIL 均在业务代码执行前创建 `127.0.0.1` fixture server 时被当前沙箱拒绝，错误同为 `PermissionError: [Errno 1] Operation not permitted`；不得记作 PASS，也不是本批回归。
- 静态态零变化硬闸通过：既有 `test_distribution_gate.py` 修前、修后均逐项 PASS；新增 N4 对 EVM/BSC 与 Solana 分别确认原分母、闭合锚点及无漂移字段。

## RED 证据

- 证据：`maintenance/repair-20260823-sqd-gap/batch12_red_evidence.txt`。
- 修前命令：`PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_batch12_frozen_supply_drift.py`。
- 修前退出码：1。
- 唯一 RED：ARC 同形 `PASS/exit 0` 收据、`replay_net > onchain_total_supply`、`diff=26135` 且 10bps 内，仍被旧硬拒 `供给真值 onchain/net 非法`。
- 同次运行 N1、N2、N3、EVM 静态态、Solana 静态态均已是绿，证明修复面只需覆盖冻结态容差内分支。

## 改动与行号

1. `scripts/report/holder_distribution_scan.py:225-257`
   - 保留 `PASS/exit 0`、正整数与静态态原硬拒。
   - 仅在 `net > onchain` 时要求收据 `diff`、`tolerance_bps` 在场；复算 `net-onchain == diff`，再用整数不等式 `drift*10000 <= tolerance_bps*onchain` 判定。
   - 任一条件失败仍以原句 `供给真值 onchain/net 非法` 开头，并追加冻结态例外边界说明。
2. `scripts/report/holder_distribution_scan.py:574-584,626-644`
   - `replay_net` 继续作为全部分布百分比分母；未改成活观测 `onchain`。
   - 仅合法漂移向在 `denominators.supply_drift_raw` 留痕；静态态不新增该字段。
   - Solana 快照闭合仍走 `mint_closure_anchor(..., onchain)` 与零容差精确等式，未读取 supply 漂移容差作为快照容差。
3. `scripts/tests/test_batch12_frozen_supply_drift.py:12-134`
   - G1/R1 使用 ARC 同形数值；N1 覆盖 diff 失配；N2 用 `10**30+1` 与边界外 1 raw 证明判定不经浮点；N3 覆盖非 PASS 与 exit 非 0；N4 覆盖 EVM/BSC 与 Solana 静态态。
4. `scripts/tests/run_all.py:174-175`
   - 新测试已登记进守护全套。
5. `references/scan-schemas.md:364-370,434-437`
   - 记录冻结态容差条件、整数公式、`supply_drift_raw` 可选字段、分母与快照闭合不变。
6. `references/analyze-workflow.md:107-120`
   - A3 分布扫描步骤同步冻结态语义。

未新增 CT-SQDGAP 编号：现有 `CT-DISTRIBUTION-01` 已以 `distribution-scan/v2` 权威段为锚；本批是 v2 向后兼容的可选留痕和既有 PASS 收据消费修正，没有新增独立契约面或 schema 版本。

## 波及面逐处核查

全库生产代码对 `replay_net|onchain_total_supply` 的直接命中只有三个文件：生产者、公共深验、分布扫描器。逐处结论如下。

1. `scripts/lib/supply_truth_gate.py:444-451`：生产者按绝对差与 tolerance 判 PASS，不含 `net <= onchain` 方向假设。本批禁改，未动。
2. `scripts/report/shared_release_receipt.py:405-425`：公共深验独立重算 tolerance verdict，并把 `replay_net` 对绑定 `replay_stats` 的 `mint-burn`；不要求 `net <= onchain`。批 10 已关，未动。
3. `scripts/report/shared_release_receipt.py:1234-1297`：发布深验要求正式 schema、完整字段、decision rule、PASS 语义并调用上述 tolerance 复算；没有静态方向拒绝。未动。
4. `scripts/report/shared_release_receipt.py:1315-1326,1343-1352`：分别把 Solana/EVM `onchain_total_supply` 绑定到 observation bundle 实物；只验证观测值来源，不拿它与 `replay_net` 做静态等式。批 11 已关，未动。
5. `scripts/report/holder_distribution_scan.py:295-342`：EVM 的 `mint-burn == replay_net` 是冻结账本内部闭合；Solana 快照锚仍是 `onchain`。两者均不是 `net <= onchain` 假设，保留。
6. `scripts/report/reconciliation_report.py:198-207,355-370`：runner 只绑定动态观测 slot，并把收据交给公共深验；不自行比较 net/onchain。未动；`test_reconciliation_runner.py` 在全套 PASS。
7. `scripts/report/handoff_manifest.py:188-191,448-456,501-508`：自动 gate 只读 verdict/exit；READY 深验复用公共 validator；distribution 通过当前扫描器独立重算。无第二套静态等式。`test_handoff_manifest.py` 68 项 PASS。
8. `scripts/report/audit_release_gate.py:1073-1161,1441-1450`：new-analysis 只把 initial/final scan 的 `input_binding.snapshot.sha256` 与四查 owner 快照 SHA 对等，并调用扫描器 validator；没有读取 `supply_drift_raw`，也没有 net/onchain 方向假设。该 SHA 绑定来源未变；`test_audit_release_gate.py` PASS。
9. `scripts/report/a5_report_seal.py:261-326`：A5 只重验 rounds 与终态 scan，并绑定终态 JSON/图；额外可选 denominator 字段由扫描器语义重算覆盖，不存在静态等式。未动。
10. `scripts/report/build_html.py:308-314,475-479`：G10/G11 分别委托 A5 seal 与发布闸；不直接解释 net/onchain。未动。
11. `scripts/lib/camp_series_provenance.py:467-542`：EVM 序列侧只校验 supply_truth 的 schema、PASS/exit、target 与 replay_stats 绑定，不比较 net/onchain。Solana 序列走 reconcile v4，不消费本字段。未动。
12. `references/split-run.md:150-178`：−3 装配工单只知情绑定 distribution terminal；真正拒收权在 A5 seal/build_html/发布闸，已由上面第 8-10 项覆盖。无需改。

发布闸 `holder_outputs.owners` 结论：`audit_release_gate.py:1073-1080,1099-1161` 只比较 owner 快照 SHA；本批仍消费同一活观测 owner 快照，路径与 SHA 来源均未改变，影响为零。

## 测试结果

- `test_batch12_frozen_supply_drift.py`：PASS（G1、N1、N2、N3×2、N4 EVM、N4 Solana）。
- `test_distribution_gate.py`：PASS；修前与修后终端输出均为 `PASS: distribution gate red-green contract`。
- `test_repair_batch_b.py`：41/41 PASS。
- `test_handoff_manifest.py`：68 项 PASS。
- `test_audit_release_gate.py`：PASS。
- `test_batch11_frozen_bundle_binding.py`：PASS。
- `test_contract_routes.py`：PASS。
- `invariant_scan.py`：PASS，exceptions=0。
- `docs_lint.py --all`：PASS，59 个文档。
- `py_compile`：PASS。
- 最终 `run_all.py`：134 PASS / 2 环境 FAIL；新增 batch12 测试在全套中 PASS，所有其余非 loopback 项 PASS。

两项环境 FAIL 的准确位置：

- `scripts/tests/test_batch3_solana_vertical_slice.py:625`：`ThreadingHTTPServer(("127.0.0.1", 0), ...)` 在 `socket.bind` 被沙箱拒绝。
- `scripts/tests/test_batch3_evm_vertical_slice.py:281`：同一 `socket.bind` 沙箱拒绝。

## 边界自查

- 未改 supply_truth 生产者、五查 runner、公共发布深验、`replay_edges`、handoff、A5 或 −3 装配实现。
- 未改 `VERSION`、`pyproject.toml`、`SKILL.md`、`CHANGELOG.md` 或任何版本登记面。
- 未读取、修改或输出任何密钥；未触碰 ARC 案根。
- 工单 `batch12_workorder.md` 保持原样。
- 未 commit、未切分支。
