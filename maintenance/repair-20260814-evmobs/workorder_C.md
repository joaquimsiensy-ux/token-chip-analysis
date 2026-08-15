# 工单 C（F-02/F-03）：消费侧公共 validator + shared/handoff 双消费 + 消费负测

> 观测锚修复工程第 3/4 单，依赖工单 A（bundle 契约）与工单 B（v4/v2 生产者）。总计划见 plan.md。
> 施工纪律：只改文件，**禁止任何 git 命令**；完成后写 `workorder_C_done.md`。
> 本单**不改**纵切片/audit_release_gate 夹具与文档版本（工单 D）。

## 0. 背景一句话

@CX 复核抓到的真实旁路：handoff READY（split-run stage-1 交接闸）对 accounting 只重读 verdict/exit_code（handoff_manifest.py:477），不走 shared 深验——bundle 绑定若只加在 shared_release_receipt，伪造件仍能拿到 READY。本单抽公共 validator，shared 与 handoff 同函数双消费，并落 EVM 三处绑定与 N-2 数值对账。

## 1. 不变量

EVM formal 发布与 READY 两条路线消费同一套校验函数：accounting 必绑 bundle 且 as_of==anchor.number；supply_truth(v4) 必绑 bundle 且 onchain==bundle.total_supply_raw、anchor.number==target.as_of_block；accounting 与 supply_truth 绑定的 bundle sha256 必须相等（同源）；EVM formal 只接受 v4/v2，v3/v1 EVM 收据 fail-closed 红＋迁移提示；Solana 路线零行为变化。

## 2. 同族清单（施工首步 rg 复核）

```bash
rg -n "supply-truth-receipt/v3" scripts/report/ scripts/lib/   # 消费断言点全集
rg -n "accounting-gate/v1" scripts/report/
rg -n "_verify_light_schema|AUTO_GATE" scripts/report/handoff_manifest.py
rg -n "validate_sources|validate_reconciliation_check" scripts/report/shared_release_receipt.py
rg -n "MIGRATION_HINT" scripts/report/shared_release_receipt.py   # 迁移提示机制现成
```

对标（必读）：shared_release_receipt.py 的 Solana 三处绑定（:784-802 accounting bundle、:514-523 supply 查、:575-603 supply_truth N-2）、`_bound_case_ref`（:265-289）、replay_stats 三查同源写法（:643-658）；handoff_manifest.py :333（wrapper 深验点）与 :477（AUTO_GATE 浅读点）。

## 3. 施工内容

### 3a. `scripts/report/shared_release_receipt.py`——抽公共函数＋EVM 分支

新增两个模块级公共函数（供本文件与 handoff_manifest 共同 import 调用，**不在 handoff 手抄第二套**）：

- `validate_accounting_receipt(root, accounting=None, expected_target=None)`：现 validate_sources 里 accounting 的 schema/exit/verdict/checks 基本校验＋family 分流——EVM 分支：schema 必须 `accounting-gate/v2`（v1 → 红＋MIGRATION_HINT 风格提示"存量案须以 observe_supply.py + accounting_gate --bundle 重跑"）；`execution_mode=="formal"`；tip/probe/as_of 现有四条 `_require` 保留；**新增**：`observation_bundle` ref → `_bound_case_ref` 三验 → 读 bundle → `validate_evm_observation_bundle(bundle, bundle_path=…, expected_token=token, expected_chain_id=evm_chain_id_for(chain))` → `_require(accounting["as_of_block"] == bundle["anchor"]["number"])` → `_require(accounting["observed_anchor"]["block_hash"] == bundle["anchor"]["block_hash"])`。Solana 分支照旧（v1＋既有 bundle 校验，原 :784-802 逻辑整体移入本函数）。返回 (target, accounting, bundle_sha_or_None)
- `validate_evm_observation_source_chain(root, accounting, supply_truth_receipt)`：**同源强制**——accounting 绑定的 bundle sha256 == supply_truth inputs.observation_bundle 的 sha256（对标 replay_stats 三查同源 :643-658 写法）

`validate_sources` 改为调用 `validate_accounting_receipt`；在 supply_truth 收据取到后调用同源函数。

supply_truth 家族分支（:524-603）：
- schema 断言按 family 分：EVM 只受 `supply-truth-receipt/v4`（v3 EVM → 红＋迁移提示）；Solana 只受 v3
- `if family == "solana"` 的 bundle 块保持；**新增 `elif family == "evm"`**：inputs.observation_bundle 案内解析（相对/绝对双兼容照 Solana 写法）→ `validate_evm_observation_bundle(...)` → `_require(int(receipt["onchain_total_supply"]) == int(bundle["supply"]["total_supply_raw"]))`（N-2 对称，注释点名）→ `_require(bundle["anchor"]["number"] == canonical_target(target)["as_of_block"])`
- sink_fallback_form2 语义段（:543-570）核对：三值现由 bundle 供给（工单 B），消费侧对 receipt.sink_reconciliation 的重算逻辑与 bundle 三值的关系要自洽（zero/dead 的 onchain_raw 应等于 bundle 的 zero/dead raw——加对账）

### 3b. `scripts/report/handoff_manifest.py`——READY 路线接入

- import 上述公共函数；在 READY 校验流（`_verify_light_schema` 或其调用层，以现行结构为准）对 accounting 调 `validate_accounting_receipt(root, expected_target=…)`，对 supply_truth wrapper 内收据加同源检查 `validate_evm_observation_source_chain`
- **bundle 与 transcript 进 handoff artifact 必备/传递面**：rg handoff 的 artifact allowlist/manifest 清单机制，把 `evm_observation_bundle.json` 与 transcript 文件按 EVM formal 必备件登记（Solana 案不受影响），搬案不漏被收据间接引用的实物
- Solana 案 READY 行为零变化（负例防误伤）

### 3c. 测试（先红后绿，新建 `scripts/tests/test_evm_observation_release.py` 或扩展既有消费测试文件——优先扩展，减少挂载面；若新建须挂 SUITE）

消费侧负测（对标 test_r9_batch3_release_guards.py:114-175 的 build_case 真跑生产者套路；EVM 生产者可用工单 B 的 mock-bundle 夹具路径）：
| 用例 | 断言 needle |
|---|---|
| a. accounting 缺 observation_bundle | "does not bind" 类 |
| b. accounting.as_of_block 与 anchor.number 不符 | anchor mismatch 类 |
| c. supply_truth(v4) inputs 缺 bundle | "does not bind" |
| d. onchain_total_supply 与 bundle.total_supply_raw 不符 | N-2 needle |
| e. accounting 与 supply_truth 绑不同 bundle（sha 不等） | 同源 needle |
| f. EVM v3 supply_truth / v1 accounting 进 formal | 迁移提示 needle |
| g. **handoff verify** 对 a/b/e 三种同样拒绝 | 【CX 反例 2——READY 路线等深证明】 |
| h. Solana 全案 READY＋发布 | 全绿（防误伤） |
| i. **原 F-02 反例复刻**：同步改 replay_stats+replay_net+onchain=777、更新全部绑定 hash、不加 bundle | 被拒 |
| j. **原 F-03 反例复刻**：as_of/tip/probe＋四收据 target 同抬 999999、重算案内全部 hash | 被拒，且 done 报告须证明**死在 bundle anchor mismatch 而非旧 target mismatch**（【CX 反例 1】——逐层放行验证：先把 target 全对齐只留 bundle 锚不符，确认新闸独立拦截） |

## 4. 登记（本单范围）

- `invariant_manifest.json`：receipt_consumers——shared_release_receipt 条目加 `evm-observation-bundle/v1`＋v4/v2；handoff_manifest 条目按扫描实况；以 invariant_scan diff 报错补齐
- 新测试文件若新建：run_all.py SUITE 挂载
- **本单不动**：契约注册表/文档/版本/FORMAL_E2E/capability probes（工单 D）

## 5. 完工自查

- 本单全部新负测绿；Solana 防误伤用例绿
- run_all 预期红清单更新（只剩工单 D 地盘的夹具/文档红），意外红为零
- 六视角①②自审＋"shared 与 handoff 消费同一函数"的 rg 证据（不存在手抄第二套）
