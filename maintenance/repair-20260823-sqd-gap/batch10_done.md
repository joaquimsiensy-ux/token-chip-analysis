# 批 10 施工报告（代码面完成；完整 suite 环境阻断，未宣称全绿）

## 状态

- 基线 HEAD：`db2eff13ae165f5eb5b9ff183efb4b16c05f8a1d`。
- 方案 A 的 runner／公共深验／producer 硬闸三层已关到同一深度。
- **验收未完成**：`run_all.py` 在本受限沙箱为 132/134 PASS；两个既有纵切片都在
  `ThreadingHTTPServer.bind(127.0.0.1)` 处被环境以 `PermissionError: [Errno 1]`
  拒绝，尚未进入业务断言。没有把环境失败写成 PASS，也没有改测试绕过。
- 未 commit、未 push；未改 `VERSION`、`CHANGELOG.md`、`pyproject.toml`、`SKILL.md`；
  未触碰密钥文件，产物不含 API key。

## 改动清单（当前文件行号）

1. `scripts/report/reconciliation_report.py:195-222`
   - dynamic Solana 的 balance／supply_truth／time 继续必须消费
     `{observed_as_of_block}`。
   - `exact_reconcile` 反向禁止该占位符，且要求 `--as-of-slot` 或
     `--as-of-slot=N` 两种写法合计恰好一次，值为非负整数字面量。
   - 同时拒绝嵌入式占位符、缺 flag、重复 flag、负数和非整数字面量。
2. `scripts/report/reconciliation_report.py:288-303`
   - 仅 dynamic Solana `exact_reconcile` 放宽 receipt target：canonical chain/token
     全等，receipt slot 为非 bool 的非负整数且不晚于 wrapper 观测 slot。
   - 其余 check 保留原 `receipt.get("target") != target` 全等分支。
3. `scripts/report/shared_release_receipt.py:1186-1197`
   - 公共发布深验同步同一放宽；else 分支保留其他 Solana check 和全部 EVM check
     的 canonical target 全等。
4. `scripts/tests/test_batch3_solana_vertical_slice.py:479-484`
   - 现役 Solana job spec 夹具把第五查改为缓存冻结 slot 字面量；前三查占位符不动。
5. `scripts/tests/test_r9_batch3_dynamic_runner.py:96-178`
   - 覆盖 G1、N1、N2、runner 层 N3/N4，以及 bool、负 slot、缺／重复 flag、
     `--as-of-slot=` 和嵌入占位符边界。
6. `scripts/tests/test_reconcile_v4_receipt.py:525-567`
   - 覆盖公共深验层 N3/N4、冻结点早于观测点正例，以及 N5 cache upper 正向绑定。
7. `references/analyze-workflow.md:82`、`references/scan-schemas.md:1156,1179-1180`
   - 运行时文档写明三查观测点／第五查冻结点的区别、target 放宽边界与 cache meta
     正向绑定。
8. `scripts/tests/contract_manifest.json:194`、
   `scripts/tests/contract_ids_snapshot.json:168`
   - 新增并登记 `CT-SQDGAP-33`，防第五查占位符旧语义回流。

## 深验正向绑定考据结论

结论：**改前已存在，无需重复实现**。

- `scripts/lib/solana_exact_validate.py:1844-1864`：
  `validate_reconcile_receipt_deep` 从 receipt 的 `inputs.soltx_meta` 绑定实物读取
  `finalized_upper_slot`，并先校验 v4 meta 身份／窗口。
- `scripts/lib/solana_exact_validate.py:1919-1934`：快照 target 必须与 receipt target
  全等；随后明确要求 `receipt.target.as_of_block == finalized_upper_slot`，否则追加
  `as_of_slot must equal snapshot slot and finalized_upper_slot` 并令深验失败。
- N5 回归位于 `scripts/tests/test_reconcile_v4_receipt.py:556-565`：把 receipt slot 从
  cache upper 1 改为 0 后，断言深验失败且原因命中 `finalized_upper_slot`。

## producer 硬闸不动证明

- `scripts/solana/replay_edges.py:393-396` 仍是
  `as_of_slot != cache_meta["finalized_upper_slot"]` 即拒，文案仍为
  `--as-of-slot 必须 == cache finalized_upper_slot`。
- 当前文件 SHA-256 与 HEAD 实物一致：
  `4dc1e4950f128b0a5395ffcd690682194a7f193dbb7fec348d915960b51b5bef`。

## 红绿证据

- 红证据：`maintenance/repair-20260823-sqd-gap/batch10_red_evidence.txt`
  - 改代码前 R1 exit 1；旧 `_validate_spec` 拒绝 literal slot，错误为
    `dynamic solana check exact_reconcile must consume {observed_as_of_block}`。
- targeted 绿证据：
  `maintenance/repair-20260823-sqd-gap/batch10_green_evidence.txt`
  - R1 同语义 spec 已通过；N1-N5、EVM runner 回归、文档／契约守卫、
    `git diff --check` 均通过。

## `run_all.py` 结果

命令：

```text
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/run_all.py
```

真实结果：exit 1，134 项中 132 PASS、2 FAIL。

失败仅为：

1. `test_batch3_solana_vertical_slice.py`：loopback bind 被沙箱拒绝；
2. `test_batch3_evm_vertical_slice.py`：loopback bind 被沙箱拒绝。

两项均在 fixture HTTP server 创建处失败，未进入 runner／producer 业务断言。
完整 suite 中本批改动相关的 `test_r9_batch3_dynamic_runner.py`、
`test_reconciliation_runner.py`、`test_contract_routes.py`、
`test_reconcile_v4_receipt.py`、`test_recon_fifth_check.py`、docs lint 和 invariant scan
全部 PASS。必须在允许 `127.0.0.1` 绑定的环境重跑完整 suite，取得 exit 0 后才可写
“run_all 全绿”。

## 已自查边界

- exact receipt 的 slot 小于或等于观测 slot：runner 与公共深验均接受；大于则两层拒绝。
- exact receipt 的 chain 或 token 不同：两层拒绝。
- exact receipt 的 slot 为 bool、负数或非整数：拒绝。
- exact argv 使用独立参数或 `--as-of-slot=N`：单一非负字面量可接受；缺失、重复、
  嵌入 `{observed_as_of_block}` 均拒绝。
- balance／supply_truth／time 任一缺观测占位符：仍拒绝。
- N5：receipt slot 与绑定 cache `finalized_upper_slot` 不同：独立深验拒绝。
- EVM 四查路径：生产代码仍走原 target 全等 else 分支；现有 EVM controlled-runner
  七反例与完整 suite 中非 loopback EVM 契约全部 PASS。
- `replay_edges.py` 硬闸、供应观测逻辑、版本登记面、密钥面均未改。

## 开工同步说明

技能说明要求的 `sync-from-cc.sh`／`SYNC.md` 在本仓库不存在；已检索并确认，没有伪造
同步成功，也未越权新增或修改同步设施。
