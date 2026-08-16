# 工单 A（F-02/F-03）：EVM 观测件协议库 + CLI producer + 协议负测

> 观测锚修复工程第 1/4 单。总计划见同目录 plan.md（已含 @CX 融合五项必改）。
> 施工纪律：只改文件，**禁止执行任何 git 命令**（commit 由裁判代做）；边做边保存；
> 完成后把完工摘要写到本目录 `workorder_A_done.md`（改动文件清单＋每条测试的红→绿证据＋六视角①②自审结论＋schema 字段实况清单）。
> 本单**不改**任何现有生产文件（supply_truth_gate/accounting_gate/shared_release_receipt/handoff 均属后续工单）。

## 0. 背景一句话

EVM 正式链缺"冻结块链上观测实物"：supply_truth 的 `onchain_total_supply` 是自报标量（F-02），accounting 的三个块高字段同源自证（F-03）。本单新造观测件 producer 与 validator，后续工单把它绑进生产/消费链。

## 1. 不变量

正式 EVM 案内必须存在一份可独立复算的链上观测件：链身份（chainId 双值+端点指纹）、冻结块身份（blockHash 前后夹验）、冻结块供给三值（totalSupply/ZERO/DEAD，按块哈希执行）、全部调用的 request/result transcript 实物；producer 落盘前用消费侧同一 validator 自验；任何字段与 transcript 实物不一致即 fail-closed。

## 2. 同族清单（施工首步 rg 复核）

```bash
rg -l "solana-observation-bundle" scripts/          # 对标模板全集
rg -n "evm-observation" scripts/ references/        # 施工前应为空（新 schema 无占用）
rg -n "endpoint_fingerprint" scripts/               # 现仅 3 个 Solana 文件用（EVM 首用）
rg -n "def attest" scripts/lib/net.py               # pool.attest() 现无人调用
```

对标模板（必读后再动工）：
- `scripts/lib/solana_observation.py`（协议+validator 结构；:54-61 `assert_declared_slot` 链无关直用；:515-526 build；:529-637 validator 四层）
- `scripts/solana/scan_token_accounts.py`（CLI 骨架：:178-187 quarantine 隔离旧件、:197/:218-222 error envelope 先建后重建、:297 发布前自验、:298 publish_txn 双件原子、:299-307 publish_error_receipt）
- `scripts/lib/receipt_kernel.py`（build_envelope:126 / finalize_envelope:159 / publish_txn:740 / publish_error_receipt:880 / assert_distinct_paths:732）
- `scripts/lib/receipt_validate.py:81-133`（独立信封验证器，validator 内调用）
- `scripts/lib/endpoint_identity.py`（endpoint_fingerprint:52 / public_endpoint:37 / redact_endpoint_text:60）
- `scripts/lib/net.py`（attested_rpc_pool:375-389 / RpcPool.attest():363-365 / call_many:367-369）
- `scripts/lib/supply_truth_gate.py`（`_parse_eth_call_value`:473-480、`_balance_of_data`:483-484、`fetch_sink_reconciliation`:487-499 的 call_many 三元组写法——**复制逻辑，不 import 该模块**，避免循环依赖；sink 常量从 `scripts/lib/supply_semantics.py` 取 ZERO/DEAD）
- 测试对标：`scripts/tests/test_r9_batch3_solana_observation.py`（transport fake 注入+畸形开关+expect_error 套路）

## 3. 施工内容

### 3a. 新建 `scripts/lib/evm_observation.py`

模块级：`BUNDLE_SCHEMA = "evm-observation-bundle/v1"`。**不需要** Solana 的 activity 验证/pre-post 窗口/三方闭合（EVM archive 冻结块直查即终态）。

`observe_evm_supply(pool, chain, token, as_of_block, *, expected_chain_id)`——观测序列（每笔业务调用按序记入 transcript 列表 `{seq, method, params, result}`，result 存节点返回的原始 result 值）：
1. `pool.attest()` → observed_chain_id（int）；transcript 记 `{method:"eth_chainId", params:[], result:<hex 或 int 原样>}`
2. `eth_getBlockByNumber(hex(as_of_block), False)` → 取 number/hash/parentHash/timestamp（number 必须==as_of_block，hex 解析）
3. `eth_blockNumber` → tip（必须 ≥ as_of_block）
4. 三笔 `eth_call`（totalSupply `0x18160ddd` / balanceOf(ZERO) / balanceOf(DEAD)），**块参数用 EIP-1898 `{"blockHash": <步骤2的hash>, "requireCanonical": true}`**；节点不支持（报错/-32602 等）→ 抛异常 fail-closed，**禁止静默降级回块号**；返回值经 `_parse_eth_call_value` 同款严格解析
5. `eth_getCode(token, hex(as_of_block))` → sha256 摘要
6. 再取一次 `eth_getBlockByNumber(hex(as_of_block), False)` → recheck_block_hash，必须与步骤 2 的 hash 全等（前后夹验，防重组/节点漂移）

返回 core dict，业务字段**定死如下**（后续工单按这些字段名消费，不得改名）：
```jsonc
"attestation": {"expected_chain_id": int, "observed_chain_id": int,
                "endpoint": {"public_origin": str, "sha256": str}},   // endpoint_fingerprint(pool.url)
"anchor": {"number": int, "block_hash": "0x..", "parent_hash": "0x..", "timestamp": int,
           "recheck_block_hash": "0x..", "tip_block": int, "confirmations": int},
"supply": {"total_supply_raw": "十进制字符串", "zero_balance_raw": "..", "dead_balance_raw": "..",
           "block_binding": "eip1898-block-hash"},
"code": {"runtime_code_sha256": str},   // 命名如实：内容完整性指纹，不承诺代理升级防护
```

`build_evm_observation_bundle(core, transcript_path, target, producer_file, *, input_base)`：`build_envelope(BUNDLE_SCHEMA, target, producer_file, "formal", inputs={"transcript": transcript_path}, input_base=input_base)` + core 字段并入 + `finalize_envelope(...,"PASS",0)`。

`validate_evm_observation_bundle(bundle, *, bundle_path=None, expected_token=None, expected_chain_id=None, expected_producer="scripts/evm/observe_supply.py")`——校验清单（对标 Solana validator 四层，全部违反即 raise ValueError）：
- 信封：schema 全等；`receipt_validate.validate_receipt(bundle, case_root=bundle_path.parent)`（bundle_path 在场时；不在场时不传 case_root）；verdict==PASS、exit_code==0、mode==formal；producer.path==expected_producer
- 身份：expected_token 给定时 target.token==其小写；expected_chain_id 给定时 attestation 两值与其三方相等；observed==expected 恒须成立；endpoint 两键非空
- 锚：anchor.number==target.as_of_block；block_hash/parent_hash/recheck_block_hash 是 `0x`+64hex；**block_hash==recheck_block_hash**；tip_block≥number；confirmations==tip_block−number；timestamp 正整数
- 供给：三个 raw 是非负十进制字符串；block_binding=="eip1898-block-hash"
- transcript 对账（bundle_path 在场时读 inputs.transcript 实物）：逐条 seq 连续、method 序列与观测协议一致；**eth_call 三笔的 params 里 to==target.token、calldata 与对应 selector 匹配、blockHash 参数==anchor.block_hash**；transcript 各 result 解析后与 supply 三值/anchor 各字段/code 摘要一致（`getCode` 的 result sha256==runtime_code_sha256）——**只对 result 不对 method/params 是不合格的**
- 字节等值：bundle_path 在场时磁盘重解析的 canonical sha256==传入对象的（照抄 solana_observation.py:592-600 的写法）

### 3b. 新建 `scripts/evm/observe_supply.py`（CLI producer）

参数：`--chain`（choices 来自 `chain_registry.formal_evm_chains()`）、`--token`（必给，lower）、`--as-of-block`（必给 int）、`--rpc`、`--proxy`、`--out`（默认 `evm_observation_bundle.json`）、`--transcript-out`（默认 `evm_observation_transcript.json`）。

骨架照抄 scan_token_accounts.py：
1. `assert_distinct_paths(out, transcript_out)`；`quarantine_current()` 隔离两个旧件
2. error envelope 观测前先建（target 用 CLI 断言值兜底），观测拿到真锚后**重建**（error receipt 的 target 也要真实）
3. `attested_rpc_pool(rpc or DEFAULT, chain, formal=True, proxy=…, rps=2, concurrency=1)`（proxy 解析照 supply_truth_gate 现行写法）
4. `observe_evm_supply(...)` → transcript 先写临时文件 → `build_evm_observation_bundle(...)`
5. **发布前自验**：`validate_evm_observation_bundle(bundle, expected_token=…, expected_chain_id=…)`（不传 bundle_path——还没落盘；注释写明与消费侧同契约）
6. `publish_txn(transcript_out, transcript_json, out, bundle)` 双件原子
7. 任何异常：`publish_error_receipt(out, envelope, exc)` + stderr 经 `redact_endpoint_text` 脱敏 + exit 1；成功 exit 0，`sys.exit(main())` 传播
8. module docstring 写明用途与 `--as-of-block` 断言语义（`assert_declared_slot` 风格：声明值与观测 anchor.number 不符即 FAIL）

### 3c. 新建 `scripts/tests/test_evm_observation.py`（协议负测，先红后绿）

夹具：transport fake 注入（对标 test_r9_batch3_solana_observation 的思路，但 EVM 走 `RpcPool` —— 用 `mock.patch` 替换 pool 的请求层或注入 fake pool 对象，**只替换 transport，不 mock 业务逻辑**）。畸形开关至少覆盖：

| 用例 | 断言 |
|---|---|
| a. 错 chainId | 抛错且**零业务调用**（attest 之外无任何方法被调） |
| b. eth_call 返回非法（非 0x hex） | 拒 |
| c. 前后块头 hash 不等（模拟重组） | 拒 |
| d. EIP-1898 不被节点支持（-32602） | 抛异常 fail-closed，无静默降级（断言未落任何产物） |
| e. declared --as-of-block 与观测 number 不符 | 拒 |
| f. transcript 只换 method/params 保留 result（validator 侧） | 拒（【CX 反例 3】） |
| g. 发布前自验被 mock 为 raise | 两件都不落盘 + error receipt 落盘 |
| h. error 路径端点 query 脱敏 | stderr 与 error receipt 无 api-key/secret 字样 |
| i. 合法全流程 | bundle+transcript 双件落盘，validate 通过（绿例） |

每个负例用 expect_error(needle) 套路；**先证红**（在未实现对应校验的中间态跑一次确认会漏放，或用注释说明红态依据），实现后转绿。

## 4. 登记（本单范围）

- `scripts/tests/invariant_manifest.json`：`receipt_producers` 加 `{"script":"scripts/lib/evm_observation.py","schemas":["evm-observation-bundle/v1"]}` 与 `{"script":"scripts/evm/observe_supply.py","schemas":["evm-observation-bundle/v1"]}`（以 AST 实际扫描为准——`invariant_scan.py` 跑一遍看 diff 报错补齐）；`receipt_consumers` 按扫描实况（validator 里的 schema 比较会被计入）；`transport_calls` 加新 CLI；`atomic_writes` 加 publish_txn 调用函数
- `scripts/tests/invariant_scan.py` 的 `FAILURE_ARTIFACT_COVERAGE`：加 `scripts/evm/observe_supply.py` 条目（canonical/marker/error/protections，protections 含 `self_quarantine`；对标 scan_token_accounts 现有条目）；若双 canonical 触发 `FAILURE_ARTIFACT_CONTRACTS` 亦补（canonical_artifacts=2）
- `scripts/tests/run_all.py`：SUITE 末尾新增 `SUITE += ["test_evm_observation.py"]` 带注释
- **本单不动**：FORMAL_E2E_REQUIRED_PRODUCERS、capability probes、契约注册表、文档、版本（均属工单 D，避免中间态红）

## 5. 完工自查

- `python3 scripts/tests/run_all.py` 全绿（含新测试；现有测试零回归）
- `python3 scripts/tests/invariant_scan.py` 单跑无 FAIL
- 六视角①②自审：新文件每个字段有源头、每个失败分支 fail-closed
- done 报告列出：bundle 实际字段清单（后续工单据此消费）、rg 复核输出、每条测试红→绿证据
