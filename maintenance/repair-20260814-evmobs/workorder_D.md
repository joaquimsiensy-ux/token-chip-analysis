# 工单 D（F-02/F-03）：集成收尾——夹具升级 + 正式能力登记 + 文档 + 版本

> 观测锚修复工程第 4/4 单，依赖 A/B/C 全部完工。总计划见 plan.md。
> 施工纪律：只改文件，**禁止任何 git 命令**；完成后写 `workorder_D_done.md`。
> 本单收口后 `python3 scripts/tests/run_all.py` 必须**全绿**（分母含全部新增项）。

## 0. 背景一句话

生产/消费链已闭合（A/B/C），本单把三链纵切片与全部案夹具升到新契约、补齐正式能力/失败产物登记、改写文档明示局限段、升版收账。

## 1. 不变量

正式 EVM 三链（eth/bsc/base）纵切片必须真跑 observe_supply.py 并端到端绿；全部守卫（invariant_scan/契约双向/docs_lint/changelog_lint/version）绿；文档与代码双向一致（升版串、明示局限、存量迁移口径）；R10 台账按 @CX 定论关账（R10-13 CLOSED / R10-9 MITIGATED 仍 OPEN）。

## 2. 同族清单（施工首步 rg 复核）

```bash
rg -n "supply-truth-receipt/v3|accounting-gate/v1" scripts/tests/ references/  # 残余引用全集（工单 B done 移交清单核对）
rg -n "FixtureHandler" scripts/tests/test_batch3_evm_vertical_slice.py
rg -n "build_case" scripts/tests/test_audit_release_gate.py
rg -n "FORMAL_E2E_REQUIRED_PRODUCERS|ACCOUNTING_SUPPLY_ADAPTER_TARGETS" scripts/
```

## 3. 施工内容

### 3a. 纵切片夹具 `scripts/tests/test_batch3_evm_vertical_slice.py`

- FixtureHandler：补 `eth_getBlockByNumber` 分支（返回固定 number/hash/parentHash/timestamp，同 number 恒同 hash——前后夹验过）；`eth_call` 分支支持 **EIP-1898 dict 块参数**（`{"blockHash":…,"requireCanonical":true}` 按 hash 分流，与既有块号分流并存）；`eth_getCode` 已有
- `execute_real_slice`：在 accounting 之前**真跑** `scripts/evm/observe_supply.py`（subprocess，产 bundle+transcript）；accounting 加 `--bundle`；`spec()` 的 supply_truth argv 加 `--observation-bundle`，`spec["inputs"]` 登记 bundle 与 transcript（runner 执行前后快照）
- wrong-chain 负测保持零业务断言（观测件的错链用例已在 test_evm_observation.py，此处确认切片前置探针覆盖新 producer）

### 3b. 案夹具升级

- `scripts/tests/test_audit_release_gate.py` `build_case`（:140-230，全仓 EVM 案夹具唯一来源）：新增合法 bundle+transcript 夹具文件；accounting_mode.json 升 v2（execution_mode/observation_bundle/observed_anchor）；supply_truth 收据升 v4（inputs 加 observation_bundle）；全部绑定 hash 重算
- `scripts/tests/test_repair_batch_a.py`：`_retarget_evm_case` 同步改 bundle 及其绑定（retarget 时 anchor.number 也要动，涉及 bundle 重算——按夹具生成函数化处理）；`test_fb_model_probe_block_has_a_consumer` 扩为第五场景"改 tip/probe 不改 bundle 即被拦"
- 其余因 v4/v2 红的测试夹具（工单 B/C done 报告的预期红清单）逐一升级；**升级原则：夹具跟新契约走，不放松任何断言**

### 3c. 正式能力与失败产物登记（【CX 必改项 F】）

- `scripts/tests/invariant_scan.py`：`FORMAL_E2E_REQUIRED_PRODUCERS` 的 eth/bsc/base 三个 frozenset 各加 `scripts/evm/observe_supply.py`（切片已真跑，A 单的 FAILURE_ARTIFACT_COVERAGE/CONTRACTS 登记核对收尾）
- `scripts/lib/formal_capability_probes.py`：`ACCOUNTING_SUPPLY_ADAPTER_TARGETS` EVM 集合加新 producer
- `scripts/lib/chain_registry.py`：EVM 正式三链 `accounting_supply_adapter` 由 `evm-accounting-supply-v1` 升 `evm-accounting-supply-v2`（反映新闭包）；rg 该串全部引用同升
- `scripts/tests/test_batch1_rpc_attestation.py`：错链零业务 callsite 集合加 `observe_supply.py`（断言 `methods==["eth_chainId"]`）
- `invariant_manifest.json`：minimum_counts 抬地板到新实际值；formal_entrypoints 按扫描实况补

### 3d. 契约注册表

- `scripts/tests/contract_manifest.json` 追加（下一可用号起）：`evm-observation-bundle/v1`（authority=references/data-pipeline-evm-recon.md）、`supply-truth-receipt/v4`、`accounting-gate/v2` 三条 required（stages 按既有同族条目口径）；**v3/v1 不加 banned**（Solana 现役）
- `contract_ids_snapshot.json` 排序插入同名 ID
- needle 字符串必须真出现在 authority 文档（3e 同步写入）

### 3e. 文档

- `references/independent-audit-protocol.md`：**:166 "明示局限（EVM 侧链上供给）"段改写**——EVM 供给一半已闭合（bundle N-2 对账），保留并更新诚实边界："bundle 是内容绑定，不是块真实性或 producer 真执行证明；blockHash 与 transcript 供第三方外部验真"；写明分链版本（EVM v4/v2，Solana v3/v1）与 handoff/发布双路线等深；**:182 存量迁移段**补 evm-observation 口径（存量 EVM 案重发布须先跑 observe_supply.py 重做两收据，禁手工补字段）；**不得删除任何现有 needle**（本文件是 9 条契约 authority）
- `references/data-pipeline-evm-recon.md`：§供给真值段更新（v4、bundle 供给、EIP-1898 绑定、零现场 RPC）；写入三个新 needle 串
- `references/scan-schemas.md:341-345`：onchain_total_supply EVM 语义段与新来源对齐
- 全部文档改动过 docs_lint（断链/粗体配对/无孤立 E0、U1~U6/无 archive 引用）

### 3f. 版本与台账

- VERSION → `6.43.0`；pyproject.toml version 同步；SKILL.md 版本注释同步（若动 SKILL.md 正文注意 ≤8192B）
- CHANGELOG.md：索引行＋详情块 `## [6.43.0] - 2026-08-14 — EVM 链上观测锚（F-02 闭合/F-03 缓解）`（全角 —）；正文含：工程目录点名 `maintenance/repair-20260814-evmobs/`、分链升版说明、**存量影响段**（已交付 EVM 案不重跑不受影响；重发布须 observe_supply.py＋v2/v4 重做；禁手工迁移）、**suite 分母段**（run_all 入口数与全绿数）、R10 关账行
- `maintenance/repair-20260813-sixlens/r10_ledger.md`：**最小行编辑**（其他分支会大改此文件）——R10-13 行尾加【CLOSED 6.43.0】＋出处；R10-9 行尾加【MITIGATED 6.43.0，案内观测缓解，外部真实性锚仍 OPEN】；总数行不动（留 F-07 线统一重算）

## 4. 完工自查（终态）

- `python3 scripts/tests/run_all.py` **全绿**，rc=0；分母数记入 done 报告
- `git diff --check` 干净（无尾空格/EOF 空行——工单产物文档也检查）
- 三链纵切片逐链绿；`invariant_scan.py --self-test` 过
- codex 报告原 F-02/F-03 反例最终复验被拒（引用工单 C 用例 i/j 结果）
- done 报告：改动全清单、每步红→绿、六视角①②自审、剩余已知边界（R10-9 OPEN 依据）
