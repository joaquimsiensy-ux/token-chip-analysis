# 工单 F-07：四查子收据消费侧深重验 + producer 最小补齐 + schema 升版（本工程最大刀）

> 执行者：codex（纯施工，**禁止任何 git 操作**）
> 前置：第 1 刀（F-04）、第 2 刀（F-10）已合入本分支——shared 的对账分支已带 mode+formal_ready 双断言，本刀在其上加深观测语义。
> 总计划：同目录 plan.md 第 3 刀节。

## 背景

外部审查 F-07（P1）：A2 四查的 balance/supply/time/anchor 子收据，消费侧（`shared_release_receipt.py::validate_reconciliation_check`）只看自报计数（balance :检查 checked/matched/mismatched/rpc_errors 四计数；supply :只看 closed 布尔；time :只看 points/exact_match/mismatch/rpc_err；anchor :只看 coverage 三计数）——绑定真实 input 却人为构造计数字段的收据能过发布链。同文件 supply_truth 分支（:529-652）已是深重验样板（`_bound_replay_totals` 对回绑定实物、N-2 交叉），本刀把其余分支做到等深。

## A. producer 最小补齐

### A1. `scripts/evm/verify_recon.py`

1. **schema 升版**：`SCHEMA = "evm-reconciliation-receipt/v2"` → `"/v3"`（SCHEMA_FAMILY 不变）。
2. **top-N 语义可重算化**：排序键从 `-balance` 改为 `(-balance, address)` 确定性 tie-break；`observations.balance_reconciliation` 新增 `requested_top_n`（= CLI `--top-n` 实参）与 `selection`（固定串 `"top_n_then_skip_sinks"`，声明"先截 top_n 再跳过 ZERO/DEAD"的现语义）。
3. **gmgn 解析收紧**：csv 前 10 行解析改用 `decimal.Decimal`（拒 NaN/Inf/非数值 pct，非法即 raise）；重复地址 raise；`gmgn_pct`/`replay_pct`/`diff_pp` 写入 rows 时用 Decimal 规范字符串（`str()`），阈值比较用 Decimal("0.15")。
4. **RPC transcript 落盘绑定**（参照 `scripts/lib/evm_observation.py` 的 `_record`/transcript 模式与 `scripts/evm/observe_supply.py` 的双件 publish 写法）：
   - 每笔 balanceOf 调用记 `{seq, method:"eth_call", params, result}`（result 为原始 hex 字符串）；
   - 落 sidecar 文件（默认 `--out` 同目录 `verify_recon_transcript.json`，可加 `--transcript-out` 参数）；
   - 绑进 envelope `inputs.transcript`；receipt 与 transcript 用与 observe_supply 同级的原子双件发布语义。

### A2. `scripts/lib/time_spotcheck.py`

1. **schema 升版**：`time-spotcheck/v2` → `"/v3"`。
2. **inputs 补绑**：envelope inputs 从只绑 `plan` 扩为绑 `plan` + `plan_receipt`（现 `--plan-receipt` 已解析并验证但未绑）+ `input`（`--input` merged 数据文件）。
3. **RPC transcript 落盘绑定**：calls 的 (method, params, result) 逐笔落 sidecar（`--transcript-out`，默认 out 同目录 `time_spotcheck_transcript.json`）并绑进 inputs。

### A3. `scripts/solana/anchor_sampler.py` 不动。

## B. consumer 深重验（`shared_release_receipt.py::validate_reconciliation_check` + 新私有 helper）

照 supply_truth 分支既有样板（实物重读、`_bound_case_ref`、逐字段对照）。新增的 helper 一律私有函数放本文件对账区，**不碰 A4/adversarial 函数区**。

1. **EVM balance/supply 分支**（schema 断言改 `/v3`，v2 拒收并给迁移文案"存量案须以 verify_recon v3 重跑对账"）：
   - **supply_closure 全字段重算**：从 `inputs.config` 重算 nominal（`total_supply_human×10^decimals`）并核 config token==target token；从 `inputs.replay_stats` 重算 mint/burn（复用 `_bound_replay_totals`）并核 stats 截止块==target.as_of_block；从 `inputs.balances` 重算 balance_sum、negative_count、negative_addresses 全列；closed 语义独立重算（mint==nominal && balance_sum==mint && 无负值）；与 observations.supply_closure 自报值逐一对照。
   - **balance_reconciliation rows 重验**：requested_top_n 存在且为正 int；按绑定 balances 实物以 `(-balance, address)` 排序重算"先截 requested_top_n 再跳 ZERO/DEAD"的期望地址序列，与 rows 地址序列**有序相等**；每行 replay_raw==balances 实物值；每行 status/diff_raw 与 chain_raw−replay_raw 自洽；checked==len(rows)，matched/mismatched/rpc_errors 与逐行 status 重计一致；PASS 收据不得含 MISMATCH/RPC_ERROR 行。
   - **chain_raw 对 transcript**：从 `inputs.transcript` 读实物，seq 连续、method 全 eth_call、params 的地址/块与 rows 逐行对应、result 解析值==rows.chain_raw。
   - **gmgn_comparison 重验**：从 `inputs.gmgn` csv 前 10 行以 Decimal 重算 gmgn_pct（拒重复地址/NaN/Inf），从 balances/nominal 重算 replay_pct，diff_pp/status/diff_count 逐项自洽。
2. **EVM time 分支**（schema 断言改 `/v3`，v2 拒收带迁移文案）：
   - 从 `inputs.plan` 实物做 **multiset 一一对应**：balance 点比 kind/addr/block/expect_raw，tx 点比 kind/tx/from/to/block/expect_raw；
   - `inputs.plan_receipt` 存在且其绑定的 input 与本收据 `inputs.input` 同一实物（sha 相等）；
   - points/balance_points/tx_points/exact_match/mismatch/rpc_err 六计数与 rows 逐行重计一致；PASS 收据不得含 MISMATCH/RPC_ERR 行；balance 行 status 与 chain_raw/expect_raw 自洽；
   - rows 的 chain 实测值对 `inputs.transcript` 逐笔绑定（同 balance 分支手法）。
3. **Solana anchor 分支**：从顶层 `output`（{path,size,sha256}，size+sha 双验，`ref_ok` 先例）读采样产物逐行重验——日期在 target 范围内、日期唯一、身份字段与 target 一致、error 行与 failures 数组对应；covered_days/failed_days 重计与 coverage 对照。（anchor 收据 schema 不升版。）

## C. schema 升版全库级联收口（十层元规则：升 schema 必连下游一起升）

执行 `rg -n "evm-reconciliation-receipt/" --type py` 与 `rg -n "time-spotcheck/" --type py`（含 md），逐个处置：

- 生产/消费代码与测试中的串：升 v3（或按用例语义保留 v2 作拒收负测）；
- `scripts/tests/invariant_manifest.json`：**本刀授权改动**——把本组两个 schema 串按新实况替换/并列（v2 若仍被拒收路径比较则两串都列，以 `invariant_scan.py` 的 diff 输出为准），`minimum_counts` 只升不降；
- `scripts/tests/contract_manifest.json` 若有旧串 needle：同步改串（ID 不变则 snapshot 不动）；权威文档正文若含旧串同步；
- 其余中心登记（run_all 挂载、新契约条目）仍归末刀，本刀不做。

## D. 存量测试适配（授权范围）

因 schema 升版与深重验语义**必然打红**的存量测试与夹具授权适配（夹具升为带实物绑定的真语义形态，每处在 done 报告列理由）。已预计的红名单：`test_sixlens_receipts.py`（:53,120 硬编码 v2）、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_evm_observation_release.py`、`test_batch3_evm_vertical_slice.py`、`test_repair_batch_d.py`、`test_batch1_rpc_attestation.py`、`test_reconciliation_runner.py`、`test_r7_findings.py`、`test_repair_batch1.py`。名单外打红：停下写进 done 报告请示，不扩面。

## E. 新测试 `scripts/tests/test_recon_deep_reverify.py`

自建 main() runner。夹具：构造完整案根（config/balances/replay_stats/gmgn/plan/transcript 实物+真 producer 逻辑生成的绿收据），负向用例用"复制绿收据后单点篡改"法：

- supply：自报 closed=true 但 balances 实物和≠nominal → 拒（审查报告的最小反例）；
- balance：rows 少一行/replay_raw 与实物不符/matched 计数虚报/requested_top_n 缺失/地址序列与重算不符 → 各拒；
- transcript：result 与 chain_raw 不一致/缺 transcript → 拒；
- time：rows 与 plan 不对应/tx 行 from-to 改动/计数虚报/plan_receipt 缺失 → 各拒；
- anchor：output 行数与 covered 不符/日期重复 → 拒；
- gmgn：diff_count 与实物重算不符 → 拒；
- 绿例：真 producer 全链生成的收据全部通过（EVM 用离线夹具；Solana anchor 用最小 output 实物）。

## 先红后绿纪律

新测试对基线（本刀施工前）跑：深重验负向用例应体现"基线只看计数、不拒篡改件"（红），落 `f07_red.log`；施工后全绿落 `f07_green.log`。

## 验收标准

- 新测试绿；D 节红名单逐个转绿；`python3 scripts/tests/run_all.py` 期望全绿（loopback 沙箱 EPERM 项如实记录留调度方）；
- done 报告 `workorder_F07_done.md`：改动清单、红绿证据、级联收口清单（rg 结果逐项处置表）、存量适配理由表、"如实定性"段（本刀关闭至 transcript/实物绑定深度；远端真执行证明与完整 job spec 契约属外部锚定族 R10-9/14，剩余面留台账）。

## 硬约束

- 只改：`scripts/evm/verify_recon.py`、`scripts/lib/time_spotcheck.py`、`scripts/report/shared_release_receipt.py`（限对账区）、新测试、C/D 节授权文件。
- 禁碰：VERSION、CHANGELOG、SKILL.md、r10_ledger.md、pyproject、`run_all.py`、`audit_release_gate.py`、`handoff_manifest.py`、`anchor_sampler.py`、shared 的 A4/adversarial 函数区、`contract_ids_snapshot.json`（除非 C 节 rg 确需，先在 done 报告说明）。
- 禁止一切 git 操作。
