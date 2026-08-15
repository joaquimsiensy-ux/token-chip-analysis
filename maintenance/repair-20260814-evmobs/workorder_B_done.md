# 工单 B 完工摘要：生产侧接入 supply_truth v4(EVM) + accounting v2(EVM)

> 完工日期：2026-08-14（America/New_York）
> 边界：只完成工单 B；未改 `shared_release_receipt.py`、`handoff_manifest.py`、纵切片 producer 链、契约注册表、正式能力表、文档或版本。
> 施工纪律：施工期间未执行任何 git 命令；因该禁令优先，也未运行会触发 git 的 skill 同步/提交步骤。

## 1. 改动文件清单

| 文件 | 动作 | 本单内容 |
|---|---|---|
| `scripts/lib/supply_truth_gate.py` | 修改 | EVM formal 强制消费并验证 `evm-observation-bundle/v1`；totalSupply/ZERO/dead 三值只读 bundle；formal 产 v4、exploration 保持 v3 现场 RPC；收据双处绑定 bundle |
| `scripts/evm/accounting_gate.py` | 修改 | 新增 `--bundle` / `--exploration` 互斥入口；formal 的 as-of 从 bundle anchor 派生并产 v2；exploration 留 v1；写入 `execution_mode`、bundle ref、`observed_anchor` |
| `scripts/lib/camp_series_provenance.py` | 修改 | `SUPPLY_TRUTH_SCHEMAS={v3,v4}` 双接受，兼容 Solana v3 与 EVM v4 |
| `scripts/tests/test_supply_truth_gate.py` | 修改 | 新增可被工单 A 公共 validator 实验的 bundle+transcript 夹具；补 EVM formal 缺件/token/as-of/零 RPC/v4 绑定负测与 exploration 回归 |
| `scripts/tests/test_repair_batch_a.py` | 修改 | 现役 accounting 夹具补 bundle；新增 formal/exploration 参数门禁、as-of 派生、v2 字段与 bundle 三验回归 |
| `scripts/tests/invariant_manifest.json` | 修改 | 两 producer 增加 v4/v2；两 consumer 增加 observation bundle；按 AST 实况调整 camp consumer；minimum floor 52→54、55→56 |
| `maintenance/repair-20260814-evmobs/workorder_B_done.md` | 新建 | 本完工证据与移交清单 |

## 2. 施工首步 rg 同族复核实况

在任何代码/测试写入前执行工单 §2 四条命令：

- `supply-truth-receipt/v3`：命中生产者、camp 固定常量、shared 单一消费断言、2 份参考文档、invariant 登记及 12 个测试文件。
- `accounting-gate/v1`：命中 EVM/Solana 两 producer、shared 与 audit_release 两消费断言、参考文档、invariant 登记及 4 个测试文件。
- `SUPPLY_TRUTH_SCHEMA`：仅 `camp_series_provenance.py` 的定义、断言与错误文案三处。
- `fetch_onchain_supply`：仅 `supply_truth_gate.py` 的定义与 EVM 调用点；修后调用点只在 exploration 分支可达。

## 3. 实现结果与口径

### 3.1 supply_truth

- EVM formal 缺 `--observation-bundle` 即 exit 1；bundle schema、磁盘信封、producer、token、chainId、anchor、transcript 与内容哈希均走工单 A 的 `validate_evm_observation_bundle`。
- `target.as_of_block` 取 bundle `anchor.number`；CLI `--as-of-block` 仍为必给的一致性断言，值不等 exit 1。
- `onchain_total_supply`、fallback ZERO/dead 三值只取 bundle；formal 分支不创建 `evm_pool`，不调用 `fetch_onchain_supply` 或 `fetch_sink_reconciliation`。
- EVM formal schema 为 `supply-truth-receipt/v4`；Solana 与 EVM exploration 继续为 v3。
- `inputs.observation_bundle` 与顶层 `observation_bundle` 均按真实 path/size/sha256 绑定同一文件；EVM formal 语义串为 `frozen-block eth_call via evm-observation-bundle (EIP-1898 block-hash binding)`。

### 3.2 accounting

- 无 `--bundle` 且未显式 `--exploration`：argparse exit 2；两者同时给：argparse exit 2。
- formal 读/验 bundle 后，将 `as_of_block` 固定为 `anchor.number`；CLI 值仅作一致性断言；写入绝对路径 bundle ref 与 `{block, block_hash}` 锚。
- `tip_block`、`model_probe_block` 仍来自当前模型探测 RPC，未被 bundle 的 tip 冒充；formal 产 v2。
- exploration 保留原现场探测和 `as_of=CLI 或 tip` 行为，schema 留 v1；按工单显式要求新增 `execution_mode="exploration"`。这是“v1 且探测逻辑不变”的取舍，不把 exploration 升成发布新契约。

## 4. 测试红 → 绿证据

### 4.1 supply_truth 专项

实现前：

```text
python3 scripts/tests/test_supply_truth_gate.py
exit 1
7 项失败
```

真实红项：

1. `APU EVM formal receipt v4`：仍产 v3。
2. `formal fallback uses bundle and zero RPC`：仍发生现场 `call/call_many`。
3. `EVM formal missing observation bundle rejected`：缺 bundle 仍 PASS。
4. `EVM formal bundle token mismatch rejected`：错 token bundle 被忽略。
5. `EVM formal declared as_of mismatch rejected`：错 anchor bundle 被忽略。
6. `EVM formal main path zero RPC`：仍调用现场 RPC。
7. `EVM formal bundle binding and semantics`：缺 v4/ref/新语义串。

实现后：

```text
python3 scripts/tests/test_supply_truth_gate.py
exit 0
supply_truth_gate 形态①/②离线契约测试全部通过
```

逐项转绿事实：缺 bundle exit 1；错 token exit 1；CLI 123 对 anchor 124 命中 `--as-of-block assertion mismatch`；v4/ref/语义在位；formal fake pool 的 `calls==many_calls==[]`；exploration v3 且继续单次 live totalSupply；旧 fallback RPC 故障断言迁至 exploration 后仍以 ERROR/1 fail-closed。

### 4.2 accounting 专项

实现前：

```text
python3 scripts/tests/test_repair_batch_a.py
exit 1
test_workorder_b_accounting_mode_and_bundle_contract:
formal missing --bundle returned 1, expected argparse 2
```

实现后独立执行本单新增函数：

```text
python3 -c '...; t.test_workorder_b_accounting_mode_and_bundle_contract(); ...'
exit 0
PASS workorder B accounting bundle contract
```

逐项转绿事实：formal 缺 bundle exit 2；bundle+exploration exit 2；CLI 124 对 anchor 123 落同路径 FAIL/1 且原因含 `assertion mismatch`；无 CLI as-of 时收据派生 123、schema v2、formal mode、bundle 三验与 observed anchor 在位；exploration schema v1、as-of 77 保留。

### 4.3 invariant 登记

生产代码写入、登记更新前：

```text
python3 scripts/tests/invariant_scan.py
exit 1
4 discrepancy(s)
```

红项为 accounting/supply_truth producer schema 元组变化，以及 camp consumer AST 实况变化。登记后：

```text
python3 scripts/tests/invariant_scan.py
exit 0
PASS invariant manifest: receipt_producers=61, receipt_consumers=76,
transport_calls=63, atomic_writes=52, formal_entrypoints=58, exceptions=0
```

## 5. run_all 预期红清单（逐条归属）

沙箱内 `python3 scripts/tests/run_all.py`：98 个入口，exit 1，汇总 6 个失败。其中两个纵切片最初被 loopback `socket.bind EPERM` 拦截；允许 loopback 后 Solana 单测 exit 0，EVM 单测进入真实业务路径并按预期红在缺 `--bundle`。剔除已复验消除的环境项后，代码态为 93/98 通过、5 个预期红，全部归工单 D；没有意外代码红。

| 预期红 | 首个真实失败 | 归属 |
|---|---|---|
| `test_batch1_rpc_attestation.py` | supply_truth formal 旧错链夹具未先提供 bundle，业务 methods 从预期 `eth_chainId` 变为 `[]` | **D**：§3c 更新错链 callsite/正式能力夹具 |
| `test_batch3_evm_vertical_slice.py` | accounting CLI 未传 `--bundle`；允许 loopback 后稳定复现 | **D**：§3a 真跑 observe_supply 并给两 producer 传 bundle |
| `test_repair_batch_a.py` | 30 个旧 EVM formal supply/waiver 夹具未提供 observation bundle | **D**：§3b “其余因 v4/v2 红的测试夹具逐一升级” |
| `test_repair_batch_d.py` | A-1 supply producer 夹具缺 bundle，未产 `supply_truth.json` | **D**：§3b 旧 formal 夹具升级 |
| `test_repair_batch1.py` | RV-07 supply formal 夹具缺 bundle，原 PASS 步骤 rc=1 | **D**：§3b 旧 formal 夹具升级 |

工单 C 当前预期红为 **0 条**：C 的 shared/handoff 新负测尚未施工、未挂入本单 suite；现存消费侧仍接受 EVM v3/v1，所以本单不能把“未红”冒充消费链已闭合。C 完工后应按其工单 §5 更新清单，届时只保留 D 红。

环境项不列入“预期红”：`test_batch3_solana_vertical_slice.py` 在默认沙箱因 loopback EPERM 失败，允许 loopback 后 exit 0；这不属于 C 或 D。

## 6. 剩余 v3/v1 引用点移交清单

### 6.1 `supply-truth-receipt/v3`

**工单 C：**

- `scripts/report/shared_release_receipt.py:525`：当前无分链地只接受 v3，须改为 EVM v4 / Solana v3 并接 bundle N-2。
- `scripts/tests/test_handoff_manifest.py:139`：handoff EVM 夹具与 C 的双路线负测。
- `scripts/tests/invariant_manifest.json:469`：shared consumer 当前 v3 登记，随 C 的 AST 实况改 v4/bundle。

**工单 D：**

- 文档：`references/data-pipeline-evm-recon.md:18`、`references/analyze-workflow.md:66`。
- EVM/通用正式夹具：`test_a4_gate.py:152`、`test_audit_release_gate.py:200`、`test_batch3_evm_vertical_slice.py:294`、`test_distribution_gate.py:36`、`test_repair_batch_b.py:88,563`、`test_repair_batch_c.py:178,964`、`test_review_20260804_p105.py:66`。
- 上述夹具须按 D §3b 生成真实 bundle/transcript 与 v4 绑定，不得只换 schema 字符串。

**合法保留：**

- `scripts/lib/supply_truth_gate.py:93`：Solana/EVM exploration v3 producer。
- `scripts/lib/camp_series_provenance.py:402`：双接受集合中的 v3。
- `scripts/tests/test_supply_truth_gate.py:284`：exploration v3 回归。
- `scripts/tests/test_repair_batch_d.py:896`、`test_repair_batch_c.py:553`：明确 Solana v3 夹具。
- `scripts/tests/invariant_manifest.json:119`：producer 同时登记 v3/v4。

### 6.2 `accounting-gate/v1`

**工单 C：**

- `scripts/report/shared_release_receipt.py:756`：须分 EVM v2 / Solana v1 并抽公共 validator。
- `scripts/tests/test_handoff_manifest.py:87,264,409`：handoff 消费夹具与负测。
- `scripts/tests/invariant_manifest.json:461`：shared consumer v1 登记随 C 更新。

**工单 D：**

- 文档：`references/independent-audit-protocol.md:164`。
- EVM 正式夹具：`scripts/tests/test_audit_release_gate.py:163`。
- `scripts/report/audit_release_gate.py:240` 是独立生产消费断言，当前仍只收 v1；C 若不把它改为复用公共 accounting validator，D 集成收尾必须同步改为 EVM v2/Solana v1，否则 D 的 v2 fixture 会被旧断言拒绝。此点是 C/D 交界，禁止漏项。

**合法保留：**

- `scripts/evm/accounting_gate.py:78`：exploration v1。
- `scripts/solana/accounting_gate_sol.py:137`：Solana formal v1。
- `scripts/tests/test_repair_batch_d.py:865`：Solana v1 夹具。
- `scripts/tests/test_repair_batch_a.py:360`：exploration v1 回归。
- `scripts/tests/invariant_manifest.json:23,247,400`：EVM producer 双版、Solana producer v1及相关现役登记。

## 7. 六视角①②自审

### ① 字段来源审计：PASS

- supply formal 的链/token/as-of 先由 CLI 声明，但 chain 受 registry、token 受 bundle target、as-of 受 bundle anchor 与 CLI 一致性断言三方约束；权威供给与 ZERO/dead 只来自已重验 transcript 的 bundle 字段。
- supply receipt 的 bundle input ref 由 receipt kernel 对真实文件生成 path/size/sha256，顶层 ref 从同一 `bundle_path` 重算；formal 分支静态可见不创建 pool，专项 fake 也证明业务 RPC 为零。
- accounting formal 的 as-of、observed block/hash 来自同一已验证 bundle；CLI as-of 不能改写，只能断言。tip/probe 仍来自本次模型探测 RPC，未与冻结锚混源。
- accounting bundle ref 使用解析后的绝对路径并重算 size/sha256，与后续 `_bound_case_ref` 的绝对/相对兼容要求一致。
- camp 只扩大 schema 接受集合到 `{v3,v4}`，没有放松 PASS/exit/target/input/provenance 其余检查。
- 诚实边界不变：bundle 只证明案内内容绑定，不证明案外 blockHash 真实性或远端 producer 真执行。

### ② 失败分支审计：PASS

- supply：缺件、坏 JSON、错 schema/producer/token/chainId/anchor/transcript/hash、缺 as-of 或声明不等均 exit 1；正式容差政策仍按原 exit 2；主判定 FAIL 仍产 canonical FAIL/2；formal 没有 warning 后降级现场 RPC 的路径。
- supply 在 envelope 建立前的 bundle 打开/身份失败不产 canonical；建立后的 as-of/业务错误走唯一 ERROR side receipt。旧 PASS 作废/归档语义未改。
- accounting：缺 mode 或 bundle+exploration 冲突在 argparse exit 2；bundle 非法/锚不符写同路径 FAIL/1；模型探测、HyperSync、无代码、样本不足及 BLOCK 裁决沿旧 finish 语义，schema 只由 execution mode 决定。
- exploration 两 producer 均继续走原现场 RPC/模型探测；本单未把 exploration 产物伪装为 formal 新版。
- invariant 的 producer/consumer/transport/atomic/formal 五个分母最终闭合；没有以删登记或加 exception 消红。

## 8. 结论

工单 B 范围完工：两个 EVM producer 已真实消费工单 A bundle；formal v4/v2、bundle 绑定、as-of 派生与供给业务阶段零 RPC均有先红后绿证据。全量剩余代码红均为工单 D 夹具升级；消费链旁路仍由工单 C 关闭，本单未越界提前修改。
