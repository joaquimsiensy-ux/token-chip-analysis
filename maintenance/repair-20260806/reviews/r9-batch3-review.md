# R9 批三 批内对抗审查报告（Opus 只读子代理，2026-08-08）

> 存档说明（Fable）：本文为 Opus 4.8 只读子代理产出的批三批内对抗审查原始报告。该子代理工具约束禁止写 .md，故由 Fable 代为落盘，内容逐字转录（仅还原 HTML 转义符）。证据脚本 13 个在 `r9-reviews/b3/evidence/`（全部离线可复现）。Fable 逐条核实与裁决见文末「## 七、Fable 总验收裁决」。

- 对象：`/Users/uravvv/Documents/5.6筹码分析/r9-closure-worktree`，`fix/r9-closure-20260807`，区间 `5771419..aadf42d`（46 文件 / +3084 −545）
- 全程零外网请求；网络形态一律用 transport fake / loopback / `127.0.0.1:1` 闭端口；密钥字面量均为假值

## 一、总裁决

**BLOCK** —— 批三不可在当前状态收口，需批内修复循环 2。

依据 `references/maintenance-review-repair.md` §六：「新引入、半修残留不分严重度，都要修复后重审」。15 条 finding 中 1 条 P1 + 6 条 P2 归因「修复中新引入」，其中 P1 是密钥泄漏面，且正落在批内修复循环 1 自称已闭合的 B3FIX-02 上。

| 严重度 | 数量 | 编号 |
|---|---:|---|
| P0 | 0 | — |
| P1 | 1 | B3R9-01 |
| P2 | 7 | B3R9-02 ~ 08 |
| P3 | 7 | B3R9-09 ~ 15 |
| 合计 | **15** | 全部 CONFIRMED（亲手复现） |

归因分布：修复中新引入 11（01,02,03,04,05,06,07,09,11,12,15）／批三未承诺·边界未登记 3（08,10,13）／老问题修复不全 1（14）。

### 批三做对的部分（避免误读为全盘否定）

- `validate_observation_bundle` 字段级校验极严：13 种定向篡改全部 fail-closed，仅合法变体放行。
- 错 mint、错 `--as-of-slot`、错 `--min-context-slot` 三类断言组合全部 fail-closed，ERROR receipt 的 target 是观测值不是声明值。
- `publish_txn` 四个 `os.replace` 失败点全部完整回滚，无半发布窗口、无残留临时文件——批三删掉的「提交后独立自检+手工撤回」确属多余且危险。
- 七条点名负例经变异测试证明为真（M1–M7 全红，M0 基线无假红）。
- 裁判 mainnet 证据 5 个 sha256 与入档文件逐字对上，三件回执 target slot 一致（438,010,504），`diff=0`，五份 JSON 无 key 泄漏。
- 门禁数字与台账全部一致：invariant 51/55/60/38/58/0、docs_lint 58、SKILL 7737B、VERSION 未改。本环境全量 suite `exit=0` 全绿。

## 二、逐 finding

### B3R9-01（P1｜修复中新引入）脱敏口径对 path 型 API key 完全失效，密钥原样落进持久化 ERROR receipt

`scripts/lib/endpoint_identity.py:8-20` 的 `public_endpoint()` 只剥 userinfo/query/fragment，**保留 path 原样**；`redact_endpoint_text()` 以其输出为替换目标，同样无效。

`api-keys.md` §2 登记的 Alchemy（现役备用主力）端点形态就是 `https://<chain>-mainnet.g.alchemy.com/v2/<KEY>`，Infura 同型。B3FIX-02 修的正是「异常/receipt/stderr 持久化完整 endpoint」，只覆盖了 Helius 的 query 形态。

复现：`python3 evidence/atk7_redaction.py` 与 `python3 evidence/atk7b_evm_leak.py`

```
  ok    helius query key           -> https://mainnet.helius-rpc.com/
  LEAK  alchemy PATH key           -> https://base-mainnet.g.alchemy.com/v2/FAKEKEY123
  LEAK  infura PATH key            -> https://mainnet.infura.io/v3/FAKEKEY123
  LEAK  no scheme                  -> rpc.example.com/v2/FAKEKEY123
```
```
[supply_truth] ERROR → .../supply_truth.error.20260808T150451....json
  FAKE_KEY_PRESENT=True
  LEAKED LINE: "error": "eth_chainId failed for http://127.0.0.1:1/v2/FAKEKEY123: ConnectError: ...",
```

替代解释检查：①「只影响 EVM」→ 否，`endpoint_identity` 被 net.py（EVM 全链）、solana_attested_session、`endpoint_fingerprint`、accounting `result["rpc"]`、anchor 行身份共用。②「path 型不在正式路径」→ 否，`--rpc/--endpoint` 无形态白名单。③「B3FIX-02 只承诺 query 形态」→ `b3_progress.md:161` 把「保留 path」写成设计口径，而非承认缺口。

### B3R9-02（P2｜修复中新引入）producer 与 validator 口径不等价：产出下游必拒的 bundle 仍 `exit 0` 且写入正式位

**路径 A**（`solana_observation.py:256-261`）：活动验证中途降级 `complete→lightweight` 时 `break`，但 `checked` 不回退，`sample_size` 保持降级前累计值；validator `:579` 要求 lightweight 的 `sample_size ≤ 50`。

`python3 evidence/atk3a_downgrade.py`（patch `time.monotonic` 模拟 120s 超时，走真实 `scan_token_accounts.main`）：
```
scan exit_code = 0
bundle published to formal slot: True
snapshot published to formal slot: True
activity.mode=lightweight  sample_size=55  complete=False  rpc_calls=56
consumer validator REJECTED: lightweight activity evidence overstates sampled coverage
```

**路径 B**（`:395-396`）：GPA 一跳下达了 `minContextSlot=parsed_slot`，但只校验 `snapshot_slot < pre_slot`，不校验 `< parsed_slot`；validator `:552-555` 要求 `pre ≤ parsed ≤ snapshot`。

`python3 evidence/atk4_fullchain.py`：
```
[4B gpa-slot-below-parsed] scan rc=0
[4B] pre=101 parsed=102 gpa=101 post=104 supply=105
[4B] consumer validator REJECTED: observation bundle jsonParsed slot window invalid
[4B] minContextSlot sent per hop: [... ('getProgramAccounts', None, 102) ...]
```

危害（视角②）：退出码 0 = 假成功；正式位已被 `publish_txn` 占用；下游报错指向 validator 而非根因；更根本的是**约束集不等价**——今天不等价的方向是 fail-closed，同一裂缝反向就是 fail-open。路径 A 真实可达（默认 deadline 120s，对照 G3-0A 实测 29 次 RPC 耗 60s）。

### B3R9-03（P2｜修复中新引入）发布层新增 6 条 Solana 硬断言，零负例覆盖

`shared_release_receipt.py:159-160, 176-187, 246, 249, 254, 257, 260`。grep 证明 6 条断言文案在 `scripts/` 下只出现在生产文件本身。

`python3 evidence/atk8c_release_mutants.py`（镜像内整块删除四个校验块）：
```
D1 drop exploration gate:                  ... ALL GREEN (uncovered)
D2 drop accounting bundle binding block:   ... ALL GREEN (uncovered)
D3 drop supply_truth bundle binding block: ... ALL GREEN (uncovered)
D4 drop solana supply bundle validation:   ... ALL GREEN (uncovered)
```
（覆盖 `test_batch3_solana_vertical_slice`/`test_audit_release_gate`/`test_sixlens_receipts`/`test_review_solana_integrity`/`test_handoff_manifest`/`test_r7_findings`，全 rc=0。）

替代解释检查：「纵切片正例已覆盖」→ 正例只证明合规产物能过，不证明违规产物被拒；整块删掉后正例照绿，正是「先红后绿」要防的。「批四补通用守卫」→ 批四留的是*通用* producer/consumer 守卫，这 6 条是批三自写的业务断言。

### B3R9-04（P2｜修复中新引入）批三新造与注册 target 同名的「影子」纵切片函数

`scripts/tests/test_r9_batch3_solana_observation.py:399-401`：
```python
def test_r9_solana_pythia_mainnet_vertical_slice():
    """Executable evidence target; the full process slice lives in sibling E2E test."""
    test_monotonic_full_and_light_modes()
```
与注册表实际指向的 `test_batch3_solana_vertical_slice.py:223` **同名**，但只跑 7 个单元反例、无进程级编排，且**不在自己 `main()` 的 tests 列表里**（正常跑该文件时从不执行）。

`python3 evidence/atk8b_guard_mutants.py`：
```
V1 production sol target repointed at the SHADOW unit function:
   test_r9_batch2_executable_capabilities=0  test_chain_registry=0
   test_batch2_capability_matrix=0  invariant_scan=0  test_chain_support_matrix=0
```

`python3 evidence/atk5_ready.py` 刻画 probe 判别力：
```
[5a eth target deleted]             ['base','bsc','sol']        <- 正确掉落
[5b bsc -> missing function]        ['base','eth','sol']        <- 正确掉落
[5c base -> unmounted test module]  ['bsc','eth','sol']         <- 正确掉落
[5d sol -> shadow same-named fn]    ['base','bsc','eth','sol']  <- 不掉落
[5e sol -> unrelated helper]        ['base','bsc','eth','sol']  <- 不掉落
[5f eth -> endpoint_identity:public_endpoint]  四链齐全          <- 不掉落
```
5e/5f 属批四 capability 执行守卫，不计 finding。本条只针对 **5d**：批三亲手造了同名、自称 "Executable evidence target"、同 SUITE 目录的空壳函数，把「需有意作恶才能换证据」降级为「一次 import 路径笔误即静默降级」——对批四待修面的**恶化**。

### B3R9-05（P2｜修复中新引入）两个「防 readiness 泄漏／harness 可逆性」守卫退化为恒真断言

`test_batch2_registry_harness_hardening.py:62` 与 `:69` 由 `== set()` 改为 `== {"eth","bsc","base","sol"}`。这两个测试的**全部语义**就是「harness 临时激活必须可逆」「import 顺序不得泄漏 readiness」；基线变四链后，泄漏与不泄漏观测结果相同。

`evidence/atk8b_guard_mutants.py`：
```
H1 harness never restores VERTICAL_SLICE targets: harness_hardening=0  chain_registry=0
H2 harness leaks a CORRUPTED override (missing sol target): harness_hardening=0
```
替代解释检查：目标没错，但可保住语义（测试内先清空 targets 建立 not-ready 基线，再验进入/退出对称性）。批三只改期望值，无补偿性改造。附带：`formal_ready_test_harness.py` 现在安装的 target 与生产注册表逐字相同，整个 harness 已成 no-op。

### B3R9-06（P2｜修复中新引入）R7-04 守卫的 `observed_context_slot` 断言从精确值弱化为 `is None`

`test_r7_findings.py:156` 与 `:186`（原为 `!= 321` / `!= 123`）。

`evidence/atk8b_guard_mutants.py`：
```
R1 supply_truth writes observed_context_slot=0: test_r7_findings.py:rc=0
```
守卫从「值必须正确」退化为「字段必须存在」。替代解释检查：「slot 动态无法写死」不成立——测试已从 bundle 读 `snapshot.slot`，再取 `["supply"]["slot"]` 即可精确断言（`supply_truth_gate.py:185` 正是该值）。弱化可避免。

### B3R9-07（P2｜修复中新引入）「未映射 hunk = 0 候选」与文件事实不符

`ledger.md:166-167` 与 `b3_progress.md:145` 均声明 0 候选。独立复算后，4 个改动文件在**整份 `diff-finding-map.md` 里 0 次出现**：
```
maintenance/repair-20260806/g3_preflight/g3_0b_pythia_gpa.json                    (+130)
maintenance/repair-20260806/g3_preflight/smoke-20260808/accounting_mode.json      (+41)
maintenance/repair-20260806/g3_preflight/smoke-20260808/solana_observation_bundle.json (+142)
maintenance/repair-20260806/g3_preflight/smoke-20260808/supply_truth.json         (+45)
```
复核：`grep -c "smoke-20260808" …/diff-finding-map.md` → 0；`grep -c "g3_0b_pythia_gpa.json"` → 0；对照 `g3_0a_usdc_activity.json` → 1（B3F2-G2 的删除登记）。

第 5 个候选 `scripts/lib/solana_sqd_dataset.py`（批三改 docstring 7 行）只出现在**批二行** `R9-B2-G3`，批三九行无跨批注记，与本表既有「物理落于 X、语义 owner 见 Y」通例不一致。

替代解释检查：「证据入档不是 hunk」→ 它们是 `160a852` 里的真实新增文件；若分母口径排除证据入档，必须显式写明而非记 0。「R9-B3-G6 覆盖裁判环节」→ 该行文件清单只有 `b3_progress.md`。

### B3R9-08（P2｜批三未承诺·边界未登记）手搓 bundle 可让三层 Solana 消费者全部 PASS

零 RPC、从未跑 producer，只手写一份 JSON：
```
PASS receipt envelope and file bindings
[GATE] mode=standard verdict=PASS exit=0 -> accounting_mode.json        (rc=0)
[supply_truth] PASS  重放净供给=12345  链上=12345  差=0（0.0bps）        (rc=0)
RELEASE-LAYER solana supply check: ACCEPTED the fully forged bundle
```
（`evidence/mk_fake_bundle.py` + `evidence/atk1b_release_layer.py`）

原因：`receipt_kernel._producer_ref` 绑定的是「仓库内脚本相对路径 + 该文件 sha256」，两者都是公开可算常量，不是产出凭证；`validate_receipt` 允许 `inputs={}`；其余全部是 bundle 内部自洽性，可整体一致伪造。发布层追加的 `ref_ok(output)` 只需伪造者顺手再写一个 snapshot 文件并填对哈希（实证已照做，仍 ACCEPTED）。

定性：这**不**等于「批三没修 R9-01」——新增的三方闭合、窗口≤512、genesis 常量、活动结构与 13 项字段校验是实质进步。但能力上仍是「人给的数字被记为观测」，载体从 CLI 参数变成文件。`diff-finding-map.md:81` 的「声明 slot 只作断言」在 bundle 存在的前提下成立，读者却易读成「不存在可声明的 slot」。据 PLAN 我**不**要求批三实现防伪，但要求 R9-01（P0）的闭合边界在 ledger 显式登记为「不含防伪，依赖批四通用守卫」——否则「代码侧闭合」会被后续引用者当成更强结论。从严记 P2。

### B3R9-09（P3｜修复中新引入）`--min-context-slot` 在 producer 侧零本地复核

`_observe_once` 把 CLI 下限转发给第一跳后从不校验 `pre_slot >= min_context_slot`；而两个 consumer 都做了复核（`accounting_gate_sol.py:167-169`、`supply_truth_gate.py:152-155`）。
```
[4C node-ignores-min-context-slot] scan rc=0
[4C] pre=5 parsed=6 gpa=7 post=8 supply=9      （CLI 传的是 1000000）
[4C] consumer validator ACCEPTED
```
参数传对了，但返回值无人复核，bundle 落地后 validator 也无从知道 CLI 下限。`b3_progress.md:10` 自述该参数「只是 RPC 下限」，故不定为承诺违约，但与 consumer 侧复核并存构成设计不一致。

### B3R9-10（P3｜批三未承诺·边界）writable 判定器两种静默漏判

`solana_observation.py:121-181`：①`message.addressTableLookups` 非空但 `meta` 无 `loadedAddresses` 时不报错不告警，直接按静态 keys 判定；②`writable.append(explicit[index] if explicit[index] is not None else derived)` —— 自报 `writable:false` 覆盖 header 推导的 `True`（视角①「自报即缺陷」）。
```
ATK-3D: mint_is_writable(alt_tx)    = False
ATK-3E: mint_is_writable(lying_tx)  = False
ATK-3E3: mint_is_writable(mixed_tx) = True   （header 推导路径正确）
```
需节点异常/不诚实才可达，故 P3；但既然做了 genesis attestation 就不完全信任节点，「lookups 非空但 loadedAddresses 缺失」至少应 fail-closed。

### B3R9-11（P3｜修复中新引入）零样本时 `coverage_statement` 与「已全量解析」不可区分

`solana_observation.py:312-316` 在 `is_complete` 为真时固定输出 "all successful referenced transactions in the observed window were parsed; the mint was never writable"。

裁判真实 mainnet 数据：G3-0B 为 `referenced_signatures=0, sample_size=0, complete=true, rpc_calls=1`；G6 smoke 入档 bundle 同样 `mode=complete, sample_size=0, rpc_calls=1`。即两次真实运行中 writable 判定器**一次都没被行使**（0 次 `getTransaction`）。`b3_progress.md:228` 对 G3-0B 诚实写了「窗口内引用 0 笔」，`:234` 对 G6 只写「activity=complete」，省略零样本事实。

### B3R9-12（P3｜修复中新引入）文档/CLI 双向不一致：两个 gate 的 docstring 用法在批三后直接失败

```
accounting_gate_sol.py --mint <mint> --out x.json
  -> error: 正式模式必须给 --bundle；独跑须显式 --exploration
supply_truth_gate.py --chain solana --mint <mint> --as-of-block N --replay-stats s.json
  -> 检测自身失败（exit 1）: solana 链必须给 --observation-bundle
```
同族：`scan_token_accounts.py:2-19` 未提 bundle/`--bundle`/`--min-context-slot`；`formal_capability_probes.py:5-7`「batch 3 must add real test targets」已不成立；`formal_ready_test_harness.py:4`「Production batch 2 has no R9 vertical-slice evidence」已不成立。（`SKILL.md` 已正确同步。）

### B3R9-13（P3｜批三未承诺·边界）`getTokenSupply` 一跳未传 `minContextSlot`，且其「过早」为不可重试硬错

`:417` 是五跳中唯一未下达 `minContextSlot` 的一跳；`:424-426` 在 `supply_slot < snapshot_slot` 时抛 `SolanaObservationError`（**非** Retryable），failover 到落后节点时一次时序抖动直接终结整轮。对比：窗口过宽/raw 变化/writable 命中均为 Retryable。

### B3R9-14（P3｜老问题修复不全）`not complete and not high_activity` 兜底分支不可达且无负例

`:247-248`。变异 M8 删掉该 raise 后**无任何测试转红**。控制流分析：所有循环退出点要么设 `complete=True`，要么设 `pagination_error`，要么令 `references>200`/`budget_limited`/`time_limited`（均进 `high_activity`），故该条件不可达。台账负例④实由上一行 `pagination_error and not high_activity` 挡住，文字无误；记账要点是该行可被静默删除且全量 suite 无感。

### B3R9-15（P3｜修复中新引入）`window_fetch` 先删 partial 再 `publish_txn`

`window_fetch.py:235-236` 把 `partial.unlink()` 从 `publish_txn` 之后提到之前。`publish_txn` 失败时正式位由 kernel 完整回滚，但 partial 已没了、`data_bytes` 只在内存——整轮采集结果丢失，须整段重采（旧顺序不会丢）。同族：`anchor_sampler.py` 的 `partial`（`:161`）已无写入方，仅参与 `assert_distinct_paths`。新顺序在「unlink 失败」时反而更干净，故为取舍而非纯退步，但取舍未登记。

## 三、九项攻击实证汇总

| # | 攻击 | 结果 |
|---|---|---|
| 1 | 伪造 bundle | **得手**（B3R9-08）：producer path/sha 可算、`inputs={}` 合法、字节校验不构成障碍、target/closure/activity 均可整体自洽伪造、发布层 `ref_ok` 只需再造一个文件 |
| 2 | 复用/错配/模式/断言组合 | **18 项全部 fail-closed，0 得手**（错 mint×2、错 as-of-slot、min-context-slot 越界、错 as-of-block、13 字段变体中 12 拒 1 合法放行） |
| 3 | 活动验证边界 | 阈值两侧正确（50 放行/51 拒；250 放行/251 拒）；**中途降级得手**（B3R9-02A）；判定器 2 项缺口（B3R9-10）；零样本措辞（B3R9-11） |
| 4 | 观测序旁路 | parsed<pre / post<snapshot / supply<snapshot 三闸关死；**GPA<parsed 未查**（B3R9-02B）；minContextSlot 四跳传对但**返回值全不复核**（B3R9-09）、getTokenSupply 未传（B3R9-13）；同 slot 全相等正确放行 |
| 5 | 四链 ready 绕过面 | 删 target/摘 SUITE/错函数名正确掉落；**同名影子函数不掉落**（B3R9-04）；两个 evidence target 经源码审读均执行真实进程级编排，**非空壳** |
| 6 | txn 迁移残留 | **无半发布窗口**：四个 replace 失败点全部完整回滚、无残留 tmp；成功后确无二次可失败动作（anchor `:292` 后仅 `return 0`；window `:236` 后仅 print+return）；1 项取舍未登记（B3R9-15） |
| 7 | 脱敏完备性 | userinfo（含密码内含 `@`）/IPv6+端口/大小写 scheme/fragment/多 query key/URL 编码 **均正确**；**path 型 key 与无 scheme URL 泄漏**（B3R9-01）；副作用：query-key 全局替换会破坏正文（`transport`→`tr[redacted-key]nsport`）；四型异常链对外无 `__context__` 残留 |
| 8 | 九负例真实性 | M0 基线无假红；**M1–M7 全部正确转红**；M8 无红（不可达死闸，B3R9-14）。守卫层 R1/H1/H2/V1 与发布层 D1–D4 共 8 项「放松后仍全绿」 |
| 9 | 台账诚实性 | 5/5 哈希逐字对上、三件 target slot 一致、diff=0、无 key 泄漏、G3-0A 双分支与 G3-0B 82,223 账户/63 slots/attempt=1 全部属实、门禁数字全对；**「未映射 hunk=0」不成立**（B3R9-07）；G6 省略零样本（B3R9-11） |

## 四、REFUTED-CANDIDATE

| # | 假设 | 排除依据 |
|---|---|---|
| R-1 | `raise … from None` 使 `__context__` 保留带 key 的原始异常且可被读到 | 实测 `call()` 对外抛的聚合异常 `__cause__=None`、`__suppress_context__=False`、`__context__=None`；中间异常不外泄（我自己的假设被实测推翻） |
| R-2 | window_fetch 的 PASS receipt 引用随后被删的 `.partial` | PASS 分支 envelope 只绑 `{"gaps": gaps_path}`（`:225`） |
| R-3 | `publish_txn` 存在半发布窗口 | 四个 replace 失败点全部完整回滚 |
| R-4 | A 币 bundle 可喂给 B 币 | `expected_mint` 拒 |
| R-5 | exploration 产物可混入 formal | `mode != "formal"` 即拒；scan 只产 formal bundle |
| R-6 | 断言与 bundle 的组合可旁路 | 三种组合全 fail-closed |
| R-7 | 删 target/摘 SUITE/指向不存在函数后 readiness 仍在 | 三种均正确掉落 |
| R-8 | bundle 字段级篡改可过 | 13 变体全拒 |
| R-9 | 裁判 mainnet 哈希与入档文件不符 | 5/5 逐字对上 |
| R-10 | 批三改既有测试期望值是「为让红变绿而放松」 | 多数（capability_matrix / chain_registry / chain_support_matrix 的 `set()`→四链、`formal_chain_error("bsc")` 反转）是四链 ready 后的必然同步，语义未损；仅 harness_hardening 两处与 r7_findings 两处构成真实弱化，已单列 B3R9-05/06 |
| R-11 | evidence target 是空壳 PASS | EVM 三函数与 Solana 函数均执行完整进程级编排 |
| R-12 | `transport-injections.json` 未登记批三新增注入边界 | 新增 3 条（observation/preflight/SQD），口径准确 |
| R-13 | 5e/5f（target 指向任意 callable 仍 ready）应计 finding | 属 PLAN 留给批四的 capability 执行守卫；仅被批三恶化的部分计入 B3R9-04 |

## 五、工作区干净自查

- 本轮**未对仓库做任何写操作**：无 git 写操作、无文件编辑、无删除。
- 变异测试在 `/private/tmp/.../scratchpad/b3atk/mirror`（`cp -R` 的一次性副本）中进行，每个 mutant 用完立即写回原文；审查结束后该副本已整体删除。
- 攻击产物写在 scratchpad 与系统临时目录，未进入仓库工作区。
- 收尾：`git status --short` **无输出**；`git log --oneline -1` → `aadf42d`。**工作区干净，无污染，无需清理。**
- 出网自查：零 mainnet/外网请求；报告与脚本中密钥字面量均为假值（`FAKEKEY123`/`SECRET`），未复写任何真实 key。

## 六、给批内修复循环 2 的最小工单建议（供裁判取舍，非审查结论）

1. **B3R9-01(P1)**：`public_endpoint()` 增加 path 段脱敏，补 path 型/无 scheme 两类负例；`redact_endpoint_text` 的 query-key 全局替换改为只替换 `key=value` 片段。
2. **B3R9-02(P2)**：降级时同步截断 `checked`；GPA 一跳补 `snapshot_slot >= parsed_slot`。根治方向是让 producer 在 `publish_txn` 前**自跑一次 `validate_observation_bundle`**，把「producer/validator 约束集必须等价」变成机器闭合。
3. **B3R9-03(P2)**：为发布层 6 条断言各补一条负例（先红后绿）。
4. **B3R9-04(P2)**：删除或改名影子函数（如 `test_r9_solana_observation_negative_bundle`），去掉其 "Executable evidence target" 自述。
5. **B3R9-05/06(P2)**：恢复守卫判别力（harness 测试内先建 not-ready 基线；R7-04 断言改为 `== bundle["supply"]["slot"]`）。
6. **B3R9-07(P2)**：为 4 个裁判证据 JSON 建 owner 行（或显式声明分母口径），给 `solana_sqd_dataset.py` 补跨批注记。
7. **B3R9-08(P2)**：在 ledger 的 R9-01 最终结果显式登记闭合边界（不含防伪，依赖批四通用守卫）。
8. P3 各项按批四/记账处理；B3R9-11、B3R9-12 建议随手修。
