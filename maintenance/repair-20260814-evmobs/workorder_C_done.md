# 工单 C 完工摘要：消费侧公共 validator + shared/handoff 双消费

> 完工日期：2026-08-14（America/New_York）  
> 边界：只完成工单 C；未迁纵切片、audit_release_gate 旧综合夹具、文档、版本、正式能力表或契约注册表（工单 D）。

## 1. 改动清单

| 文件 | 动作 | 本单内容 |
|---|---|---|
| `scripts/report/shared_release_receipt.py` | 修改 | 抽出 `validate_accounting_receipt` 与 `validate_evm_observation_source_chain`；EVM accounting v2 / supply_truth v4 分链消费；bundle 三验、anchor/hash 绑定、N-2 totalSupply 对账、ZERO/dead 对账与双收据同源 |
| `scripts/report/handoff_manifest.py` | 修改 | READY 路线调用同一公共 accounting/source-chain 函数；EVM bundle 与 transcript 纳入契约件和 READY 必备件 |
| `scripts/report/audit_release_gate.py` | 修改 | 删除独立 `accounting-gate/v1` 消费断言，`check_accounting` 改调公共 `validate_accounting_receipt`，EVM v2 不再被旧断言拒绝 |
| `scripts/tests/test_evm_observation_release.py` | 新建 | 11 项 C 消费回归：a-f、handoff a/b/e、原 F-02/F-03、Solana 防误伤、audit 公共函数 spy |
| `scripts/tests/test_handoff_manifest.py` | 修改 | EVM READY 夹具升级为真实 bundle/transcript + accounting v2 + supply_truth v4；新增传递面断言 |
| `scripts/tests/invariant_manifest.json` | 修改 | shared consumer 登记 v2/v4/`evm-observation-bundle/v1`；audit 按 AST 实况移除已删除的本地 v1 断言 |
| `scripts/tests/run_all.py` | 修改 | 挂载 `test_evm_observation_release.py` |

## 2. 实现结果

- `validate_accounting_receipt(root, accounting=None, expected_target=None)` 是 accounting 唯一深验函数：
  - EVM 只接受 `accounting-gate/v2`，旧 v1 带 `observe_supply.py + accounting_gate --bundle` 迁移提示拒绝；
  - Solana 继续只接受 v1；两族都要求 formal；
  - EVM 对 bundle ref 做 contained path/size/sha256 三验，调用 `validate_evm_observation_bundle`，并对齐 target token/chainId、`as_of_block == anchor.number`、observed block/hash；
  - Solana 原 bundle/snapshot slot 校验整体移入该函数，行为不变。
- EVM supply_truth 只接受 v4；读取 `inputs.observation_bundle` 实物并调用公共 bundle validator，强制：
  - `anchor.number == target.as_of_block`；
  - `onchain_total_supply == bundle.supply.total_supply_raw`（N-2）；
  - fallback 时 ZERO/dead 的 `onchain_raw` 分别等于 bundle 的两项 raw。
- accounting 与 supply_truth 的 bundle 以磁盘实际 SHA-256 比较同源，不信两个 ref 自报字符串。
- `validate_sources` 与 handoff `_verify_light_schema` 都先走 `validate_accounting_receipt`，再走 `validate_evm_observation_source_chain`；handoff 没有手抄第二套。
- `audit_release_gate.check_accounting` 同样调用公共函数，关闭工单 B §6.2 点名的 C/D 交界漏项。
- `_bound_case_ref` 兼容生产者现有的案根内绝对路径与相对路径，同时继续拒绝越界、`..`、symlink、size/hash 不符。

## 3. 测试红 → 绿证据

### 3.1 C 新消费专项

测试文件先落盘、生产函数尚不存在时：

```text
python3 scripts/tests/test_evm_observation_release.py
exit 1
FAIL workorder C EVM observation release: 10/10
```

红态实况包括：两个公共函数不存在；EVM v4 被旧 v3 断言拒绝；handoff 只报旧 reconciliation schema；F-03 先死于旧 accounting schema，未命中新 anchor 闸。首轮另暴露两个测试夹具缺陷（alt 目录未建、重写 replay_stats 后 time 输入 ref 陈旧），先修夹具再施工，未把夹具错误记为生产漏洞证据。

最终专项：

```text
python3 scripts/tests/test_evm_observation_release.py
exit 0
PASS workorder C EVM observation release: 11/11
```

逐项绿：accounting 缺 bundle、accounting anchor 不符、supply_truth 缺 bundle、N-2 数值不符、双收据不同源、EVM v1/v3 迁移拒绝、handoff 对缺件/anchor/不同源等深拒绝、F-02 原标量改写拒绝、F-03 逐层放行拒绝、Solana 控制组、audit 公共函数 spy。

F-03 最终实际错误串：

```text
F03_LAYER=EVM accounting bundle anchor mismatch: as_of_block != bundle anchor.number
```

该用例先同步抬高 accounting as_of/tip/probe、reconciliation target 与四份 receipt target，并重算 wrapper 内全部 receipt hash；测试另外断言错误串不含 `target mismatch`。因此它独立死在 bundle anchor mismatch，不是旧 target mismatch。

说明：原 F-02 用例在首轮红态中还夹有上述 time ref 测试缺陷；缺陷修正后没有在“生产代码仍为旧版”的快照上单独复跑一次。最终反例确实绿且会在删除 v2/v4/bundle 公共闸时失效，但这一条不冒充具备独立的干净先红日志。

### 3.2 handoff 与 invariant

handoff 加入 EVM 两个必备 artifact、旧夹具尚未升级时：

```text
python3 scripts/tests/test_handoff_manifest.py
exit 1
generate READY exit 0 失败；manifest 未生成
```

夹具升级后：

```text
python3 scripts/tests/test_handoff_manifest.py
exit 0
handoff_manifest 契约测试全部通过（68 项）
```

其中新增绿项明确检查 manifest 同时收录 `evm_observation_bundle.json` 与 `evm_observation_transcript.json`。

invariant 在生产代码完成、登记未改时真实报 4 个 consumer discrepancy；登记后：

```text
python3 scripts/tests/invariant_scan.py
exit 0
PASS invariant manifest: receipt_producers=61, receipt_consumers=78,
transport_calls=63, atomic_writes=52, formal_entrypoints=58, exceptions=0
```

### 3.3 其他定向绿

```text
python3 scripts/tests/test_r9_batch3_release_guards.py
exit 0
PASS R9 B3F3-G3: Solana release negatives 6/6

python3 -m py_compile scripts/report/shared_release_receipt.py \
  scripts/report/handoff_manifest.py scripts/report/audit_release_gate.py \
  scripts/tests/test_evm_observation_release.py scripts/tests/test_handoff_manifest.py
exit 0
```

## 4. shared / handoff / audit 同函数 rg 证据

```text
scripts/report/shared_release_receipt.py:795:def validate_accounting_receipt(...)
scripts/report/shared_release_receipt.py:891:def validate_evm_observation_source_chain(...)
scripts/report/shared_release_receipt.py:917:    ... validate_accounting_receipt(root)
scripts/report/shared_release_receipt.py:920:    validate_evm_observation_source_chain(...)
scripts/report/handoff_manifest.py:42:from shared_release_receipt import (validate_accounting_receipt,
scripts/report/handoff_manifest.py:43:                                    validate_evm_observation_source_chain,
scripts/report/handoff_manifest.py:353:                ... validate_accounting_receipt(...)
scripts/report/handoff_manifest.py:355:                validate_evm_observation_source_chain(...)
scripts/report/audit_release_gate.py:242:        from shared_release_receipt import validate_accounting_receipt
scripts/report/audit_release_gate.py:243:        validate_accounting_receipt(case_dir, accounting=d)
```

复核结论：定义只有 shared 两处；handoff 与 audit 均 import/call，没有第二套 accounting schema/anchor/bundle 业务断言。

## 5. 更新后的预期红清单（只剩工单 D）

本轮 `run_all.py` 未完成：运行超过 10 分钟后仍停在后半段入口，人工中断，不能记为完整汇总或全绿。中断前出现的代码红均落在 D 已移交的旧 EVM 夹具/正式集成面：

1. `test_batch1_rpc_attestation.py`：错链夹具未先提供 observation bundle（B §5 / D §3c）。
2. `test_batch3_evm_vertical_slice.py`：需真跑 observe_supply 并传给 accounting/supply_truth（D §3a）；同轮 Solana vertical slice 是 sandbox loopback `socket.bind EPERM` 环境项，不列代码红。
3. 复用 `test_audit_release_gate.build_case` 的旧 v1/v3 夹具：已实际命中 `test_r7_findings.py`、`test_batch2_robinhood_exploration.py`、`test_batch2_legacy_hardening.py`、`test_reconciliation_runner.py`、`test_formal_chain_support.py`、`test_repair_batch_b.py`；同族后续预期还包括 `test_audit_release_gate.py`、`test_a4_gate.py`、`test_distribution_gate.py`、`test_review_20260804_p105.py`（D §3b / B §6）。
4. `test_repair_batch_a.py`：旧 EVM formal waiver/supply/shared 夹具缺 bundle；实际 32/45 红，均在 B 已移交 D 的范围。
5. B 已登记但本次中断前尚未走到的 D 项：`test_repair_batch_d.py`、`test_repair_batch1.py`，以及 `test_repair_batch_c.py` 中的 EVM v3 夹具。

C 自有入口 `test_evm_observation_release.py`、`test_handoff_manifest.py`、`test_r9_batch3_release_guards.py`、`invariant_scan.py` 均独立全绿；没有已知 C 地盘红。

## 6. 六视角①②自审

### ① 字段来源审计：PASS

- accounting 的 chain/token/as-of 先来自生产 receipt，但必须再与 chain registry、bundle target、bundle anchor 和 `expected_target` 交叉一致；CLI/receipt 自报不能单独抬时点。
- bundle ref 的 path/size/sha256 对当前案根磁盘实物重算；随后 bundle 自身再走 A 工单公共 validator，transcript、chainId、block hash、三笔 supply 与 runtime code 的来源链不在 C 重写。
- supply_truth 的 onchain total 与 ZERO/dead 不信收据自报，均回到同一已验证 bundle 对账；replay_net 继续回到 replay_stats 实物重算。
- 双 producer 同源比较取磁盘 bundle 实际 sha，不比较两个可同步伪造的 ref 字段。
- handoff 先把 reconciliation target 与唯一 READY scope 链/token 绑定，再把同一 target 交给 accounting 公共 validator；bundle 与 transcript 又进入 manifest 哈希传递面。
- audit_release_gate 不再拥有旧 v1 私有判断；运行时 spy 证明 EVM v2 调用公共函数一次。
- 诚实边界不变：bundle 是案内内容绑定，不证明案外 RPC/blockHash 真实性；F-03 仍是 MITIGATED，不冒充 CLOSED。

### ② 失败分支审计：PASS（含一项纪律偏差披露）

- EVM v1/v3、exploration、缺 bundle、路径越界/symlink、size/hash 漂移、bundle schema/业务 validator 失败、target/anchor/hash/N-2/sink/同源不一致均 raise；shared 发布 exit 2、handoff 收集为 verify FAIL、audit 收集为发布 errors，没有 warning 后继续。
- handoff 对 EVM READY 同时强制 bundle/transcript 在 artifact 清单；缺任一在 generate/verify fail-closed。Solana 不进入这两个 EVM required 项。
- 公共函数调用失败不会被 handoff AUTO_GATE 的 verdict/exit 浅读覆盖；深验在 READY 路径必达。
- `validate_evm_observation_source_chain` 在 shared/handoff 中只在 accounting 与 supply_truth 各自完成深验后调用，不能用“同一份坏 bundle”只靠 sha 相等过闸。
- **施工纪律偏差**：没有直接键入或调用任何 git 命令，也没有做 commit/push/checkout；但运行 `test_handoff_manifest.py`/`run_all.py` 时，生产脚本 `handoff_manifest.git_sha()` 内部会执行只读 `git rev-parse`。因此按“禁止任何 git 命令”的字面要求，本轮测试间接触发了 git，不能宣称完全遵守。该调用只读且未修改仓库，但事实必须披露。

## 7. 结论

工单 C 的代码范围已实现：shared/handoff/audit 使用同一 accounting validator，EVM v2/v4/bundle 三处绑定与 N-2 闭合，handoff artifact 传递面在位，C 专项、handoff、Solana 控制组与 invariant 全绿。全量 suite 尚未闭合且只观察到 D 夹具红；必须由工单 D 完成旧夹具/纵切片/正式登记迁移后再跑最终全绿。
