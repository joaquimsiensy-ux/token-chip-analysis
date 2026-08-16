# 工单 B（F-02/F-03）：生产侧接入——supply_truth 升 v4(EVM) + accounting 升 v2(EVM)

> 观测锚修复工程第 2/4 单，依赖工单 A 的 `scripts/lib/evm_observation.py`（字段契约见 workorder_A.md §3a 与 workorder_A_done.md 实况清单）。总计划见 plan.md。
> 施工纪律：只改文件，**禁止任何 git 命令**；完成后写 `workorder_B_done.md`（改动清单＋红→绿证据＋自审）。
> 本单**不改** shared_release_receipt.py / handoff_manifest.py（工单 C）；不改纵切片夹具与文档版本（工单 D）。

## 0. 背景一句话

观测件已存在（工单 A），本单让两个 EVM 生产者消费它：supply_truth 的链上供给改由 bundle 供给（formal 零现场 RPC），accounting 的 as_of_block 改由 bundle 派生——两收据分别升 `supply-truth-receipt/v4`（EVM）与 `accounting-gate/v2`（EVM），Solana 分别留 v3/v1。

## 1. 不变量

EVM formal 模式下：supply_truth 的 `onchain_total_supply` 与 sink 三值只能来自案内 bundle 实物（业务阶段零 RPC）；accounting 的 `as_of_block` 只能等于 bundle.anchor.number（CLI `--as-of-block` 降为一致性断言）；两收据都以 path/size/sha256 绑定 bundle。exploration 行为与升版前逐字节等价。

## 2. 同族清单（施工首步 rg 复核）

```bash
rg -n "supply-truth-receipt/v3" scripts/ references/   # 升版连锁全集（消费侧断言留给工单 C/D，本单只动生产者）
rg -n "accounting-gate/v1" scripts/ references/
rg -n "SUPPLY_TRUTH_SCHEMA" scripts/                   # camp_series_provenance.py:401 写死 v3——本单必须处理（见 3c）
rg -n "fetch_onchain_supply" scripts/
```

## 3. 施工内容

### 3a. `scripts/lib/supply_truth_gate.py`

- `--observation-bundle` help 改链无关（"formal 模式观测件：Solana=solana-observation-bundle/v1，EVM=evm-observation-bundle/v1"）；**EVM formal 未给即 exit 1**（对称 Solana 现行强制）
- EVM formal 分支（对称 Solana :578-592 结构）：
  - 读 bundle → `validate_evm_observation_bundle(bundle, bundle_path=…, expected_token=a.token, expected_chain_id=evm_chain_id_for(a.chain))`
  - `assert_declared_slot(a.as_of_block, bundle["anchor"]["number"], "--as-of-block")`（as_of 必给且必须与锚一致）
  - `onchain = int(bundle["supply"]["total_supply_raw"])`；**不再调用 fetch_onchain_supply、不建 evm_pool——formal 主路径断言零 RPC**
  - sink fallback（decision_rule=sink_fallback_form2）三值改取 `bundle["supply"]` 的 zero/dead（不再 `fetch_sink_reconciliation` 打网）；原"同冻结块单查与批量观测一致"检查由 bundle 内部 transcript 对账替代
  - `envelope_inputs["observation_bundle"] = bundle_path`（去掉"仅 Solana"条件）
- schema：EVM 产 `supply-truth-receipt/v4`，Solana 维持 `supply-truth-receipt/v3`——`build_envelope(schema_by_family, …)`；`SCHEMA_FAMILY = "supply-truth-receipt/"` 前缀匹配不变
- finalize 字段：`observation_bundle` ref 链无关写入；`supply_observation_semantics` EVM 文案改为 `"frozen-block eth_call via evm-observation-bundle (EIP-1898 block-hash binding)"`；`observed_context_slot` EVM 仍 None
- exploration：完全保留现场 RPC 路径与 v3 行为（fetch_onchain_supply 保留供 exploration 用）
- module docstring 更新（分链版本+bundle 必给）

### 3b. `scripts/evm/accounting_gate.py`

对标 `scripts/solana/accounting_gate_sol.py:118-178`：
- 加 `--bundle`（formal 必给）与 `--exploration`（互斥；二者都缺 → 报错；对标 sol :132-135）
- `result["execution_mode"] = "formal"|"exploration"`
- formal：读 bundle → `validate_evm_observation_bundle(bundle, bundle_path=…, expected_token=token, expected_chain_id=evm_chain_id_for(a.chain))` → `result["as_of_block"] = bundle["anchor"]["number"]`；`--as-of-block` 给了则断言与锚一致（`assert_declared_slot` 语义），**不再是权威源**；`result["observation_bundle"] = {path(案内相对或绝对均可，但要与消费侧 _bound_case_ref 兼容——用绝对路径对标 sol :174-177), size, sha256}`；`result["observed_anchor"] = {"block": number, "block_hash": …}`
- `tip_block`/`model_probe_block` 语义不变（模型探测仍在当前 tip）；exploration 保持旧行为（as_of=CLI 或 tip）
- schema：formal 产 `accounting-gate/v2`；**exploration 也升 v2 还是留 v1？→ 留 v1**（exploration 行为零变化，消费侧本就拒 exploration；done 报告里说明该取舍）
- 写盘机制不动（tmp+os.replace，本轮不迁 kernel——plan.md 决策 D2）

### 3c. 升版连锁（本单范围内的生产侧+库）

- `scripts/lib/camp_series_provenance.py:401` `SUPPLY_TRUTH_SCHEMA` 写死 v3：改为按收据链分（EVM=v4/Solana=v3）或双接受集合 `{v3,v4}` ——**选双接受集合**（该模块消费两链收据，v3 仍是 Solana 现役；实现为 `SUPPLY_TRUTH_SCHEMAS = {"supply-truth-receipt/v3","supply-truth-receipt/v4"}` 并更新断言点），rg 该常量全部引用点一起改
- 其余 v3/v1 字符串引用点（消费侧 shared/handoff、文档、契约）**本单不动**——工单 C/D 地盘；但 done 报告须附本单 rg 后的"剩余引用点清单"移交

### 3d. 测试（先红后绿）

- `scripts/tests/test_supply_truth_gate.py`：FakePool 场景改造——EVM formal 用例改为提供 mock bundle（手搓合法 bundle 夹具，对标 test_repair_batch_d._build_solana_bundle 思路做 EVM 版）；新增负例：EVM formal 缺 `--observation-bundle` → exit 1；bundle 的 token 与 `--token` 不符 → 拒；declared as_of 与 anchor.number 不符 → 拒；**formal 主路径零 RPC 断言**（fake pool 记录调用，断言业务方法零调用）；exploration 用例保持原样全绿（防误伤）
- accounting 侧：在既有 accounting 测试所在文件（rg `accounting_gate` scripts/tests/ 找现役夹具位）加：formal 缺 --bundle 拒；--bundle+--exploration 互斥拒；as_of 从 bundle 派生（改 CLI 值断言被拦）；v2 schema 字段在位
- 红态依据逐条记 done 报告

## 4. 登记（本单范围）

- `invariant_manifest.json`：`receipt_producers` 中 supply_truth_gate 条目 schemas 数组加 v4（注意 key 是 (script, 全 schemas 元组)——整条改）；accounting_gate 条目加 v2；`receipt_consumers`：supply_truth_gate/accounting_gate 各加 `evm-observation-bundle/v1`（validator 调用处的 schema 比较）；camp_series_provenance 条目按扫描实况
- 以 `python3 scripts/tests/invariant_scan.py` 的 diff 报错为准补齐
- **本单不动**：契约注册表/文档/版本/SUITE 之外的守卫表

## 5. 完工自查

- `python3 scripts/tests/run_all.py`：**预期非全绿**——依赖消费侧（工单 C）与夹具（工单 D）的测试会红；done 报告必须列出"预期红清单"（每条红注明属于 C 还是 D 的地盘），除此之外零意外红
- 本单新增/改造测试全绿；exploration 全绿零回归
- 六视角①②自审 + 剩余 v3/v1 引用点移交清单
