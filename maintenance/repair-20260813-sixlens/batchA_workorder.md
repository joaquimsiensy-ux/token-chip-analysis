# 修复批 A 工单（F-01＋F-02）

基线：`main@2ebd885`（v6.39.5）。本批只处理发布收据验证链里的 F-01、F-02；未提交 git。

## 五栏工单

### ① 不变量

#### F-01：EVM accounting 双时点必须说实话

- 模型探测仍发生在 RPC 当前 tip。`eth_blockNumber` 一取得，立即把同一个整数写入 `tip_block` 和新字段 `model_probe_block`。
- 发布目标仍绑定调用者冻结的 `as_of_block`；未传时才沿用旧行为，令 `as_of_block=tip_block`。
- tip 取得以后，不论随后走 PASS、WARN、BLOCK、无代码 FAIL，还是基础 RPC FAIL，`finish()` 写出的收据都已经有 `tip_block`。tip 本身都没取得时不能伪造该字段。
- `shared_release_receipt` 只对 `family == "evm"` 要求 `tip_block` 是非负整数，并要求 `0 <= as_of_block <= tip_block`。Solana 不套这条 EVM 规则。
- 这只能证明收据内部没有缺字段或时点倒挂。validator 是一致性校验器，不是真实性证明器；它不能单靠两个自报数字证明某台 RPC 真在那个块上执行过。

#### F-02：正式供给真值容差不能由调用者随意放大

- formal 模式无 waiver 时只允许整数 `0 <= tolerance_bps <= 10`；负数直接拒绝，超过 10 必须带 `--tolerance-waiver <文件>`。exploration 不钳制。
- waiver schema 固定为 `tolerance-waiver/v1`。必填：`approved_tolerance_bps`、`approved_by`、`user_decided_at_utc`、三键 `target`、`replay_stats` 文件引用、非空 `evidence_refs`、理由文本。
- 实际容差必须满足 `0 <= tolerance_bps <= approved_tolerance_bps`；target 的 chain/token/as_of_block 必须全等。
- replay_stats 以及每个 evidence_ref 都复核实际文件的 path/size/sha256；符号链接、越界、缺件、错 size、错 sha 一律拒绝。
- waiver 自身作为 `inputs.tolerance_waiver` 进入 supply truth envelope，只绑定输入，不反向绑定尚未生成的 `supply_truth.json`，没有鸡生蛋死锁。
- waiver 只放大 supply truth 的判定容差。本批没有改 holder distribution 的闭合容差，也没有改任何其他阈值。
- shared validator 明确 `from supply_truth_gate import decide`，用收据里的 replay_net、onchain_total_supply、tolerance_bps 重算 primary verdict；它还独立重验 formal 钳制和 waiver 的 target/replay/evidence 绑定。

### ② 同族 rg 清单

已跑完整消费面扫描：

```text
rg -n --glob '*.py' 'tip_block|model_probe_block|as_of_block' scripts
=> 139 行（含测试）；完整输出保存在本次临时件 /private/tmp/batchA_tip_asof_rg.txt

rg -n --glob '*.py' -- '--tolerance-bps|tolerance_bps|--samples|--top-n|--tol-pp|requested_days|covered_days|failed_days|min-context-slot|window-days|anchor.*window' scripts
=> 64 行（含测试）；完整输出保存在本次临时件 /private/tmp/batchA_tolerance_params_rg.txt
```

tip/as_of 的生产消费面摘录：

```text
scripts/evm/accounting_gate.py:434 result["tip_block"] = tip
scripts/evm/accounting_gate.py:435 result["model_probe_block"] = tip
scripts/report/shared_release_receipt.py:382 tip = accounting.get("tip_block")
scripts/report/shared_release_receipt.py:388 "EVM accounting as_of_block must be <= tip_block"
scripts/lib/time_spotcheck.py:287 target = {... "as_of_block": a.final_block}
scripts/evm/verify_recon.py:57 target = {... "as_of_block": a.end_block}
scripts/lib/supply_truth_gate.py:245 tag = hex(int(as_of_block)) ...
scripts/solana/accounting_gate_sol.py:167 result["as_of_block"] = observed_slot
scripts/report/reconciliation_report.py:152-159 校验三键 target 与非负 as_of_block
```

结论：只有 EVM accounting 产生 tip/model_probe；正式冻结块继续由 reconciliation、time、supply truth 各自绑定。Solana 用 observation slot，不应新增 tip 要求。

tolerance/threshold 同族参数摘录：

```text
scripts/evm/accounting_gate.py:388 --samples（默认 8）
scripts/evm/verify_recon.py:51 --top-n（默认 15）
scripts/solana/anchor_sampler.py:142-143 --start/--end
scripts/solana/anchor_sampler.py:277-278 requested_days/covered_days/failed_days
scripts/report/figures_from_facts.py:224 --tol-pp（默认 0.05）
scripts/report/wave_scan.py:556 --window-days（默认 7）
scripts/report/flow_anomaly_scan.py:151,157 --sink-window-days/--spray-window-days（默认 14）
```

查证结论：`--samples`、`--top-n`、anchor 起止日/覆盖天数是证据强度或覆盖窗参数，不直接翻转 supply truth 的数学政策，本批只记录不修。`--tol-pp` 会翻转图表对账判定，已划批 C，本批未动。wave/flow 窗属于分析域参数，也未扩进批 A。

### ③ 三件套测试与先红后绿

新文件 `scripts/tests/test_repair_batch_a.py` 已显式加入 `scripts/tests/run_all.py` 的 `SUITE`，不是依赖自动发现。

先红命令：`python3 scripts/tests/test_repair_batch_a.py`，退出码 `1`。

```text
FAIL test_f01_no_code_failure_receipt_keeps_tip: KeyError: 'tip_block'
FAIL test_f01_shared_evm_timing_and_legal_dual_time: AssertionError: EVM as_of_block > tip_block 被接受
[supply_truth] PASS ... 差=-99（9900.0bps，容差 10000bps）
FAIL test_f02_formal_cap_and_exploration: AssertionError: (0, ... 'verdict': 'PASS' ...)
error: unrecognized arguments: --tolerance-waiver .../waiver.json
BATCH A FAIL 5/6
```

修后同命令退出码 `0`：

```text
PASS test_f01_no_code_failure_receipt_keeps_tip
PASS test_f01_shared_evm_timing_and_legal_dual_time
PASS test_f01_solana_not_subject_to_tip_check
PASS test_f02_formal_cap_and_exploration
PASS test_f02_waiver_negatives_and_failures
PASS test_f02_valid_waiver_and_shared_recompute
PASS batch A F-01/F-02 regressions 6/6
```

覆盖矩阵：

- F-01 原反例：fake RPC 返回 tip=100，随后 `eth_getCode` 返回无代码；失败收据现在有 tip=100、model_probe=100、as_of=1。
- F-01 倒挂：EVM as_of=101、tip=100，被 shared validator 拒绝。
- F-01 缺字段：EVM 收据缺 tip，被 shared validator 拒绝。
- F-01 合法双时点：as_of=1、tip=100，通过。
- F-01 防误伤：Solana accounting 不带 tip/model_probe，仍通过其原有 observation bundle/slot 校验。
- F-02 原反例：formal 10000bps 无 waiver，修后 exit 2 且不产 PASS 收据；formal -1bps 同样 exit 2。
- F-02 waiver 反例：缺 approved_by、实际 10000 超批准 9999、target 不同、replay_stats sha 错、evidence sha 错，分别命中对应拒绝分支。
- F-02 失败分支：waiver 不存在、JSON 损坏都干净返回 exit 2，无 traceback、无 PASS 收据。
- F-02 合法绿例：完整 waiver 令 9900bps 差异在批准的 10000bps 内通过；exploration 的 10000bps 不钳制并通过。
- F-02 shared 攻击变体：从高容差 PASS 收据移除 waiver 绑定会被拒；把 tolerance 偷改为 10 而保留 primary_verdict=PASS，会被 `decide()` 重算抓住。

### ④ 新建代码六视角①②自审

#### 视角①：字段来源

- F-01：`tip_block` 与 `model_probe_block` 都只来自一次 `eth_blockNumber` 返回值；`as_of_block` 只来自 CLI 冻结块或无 CLI 时的同一 tip。没有把调用者 as_of 冒充成探测块。
- F-02：`tolerance_bps` 只来自 argparse 整数；waiver 来自显式文件；target 来自本次链、token、冻结块；replay_stats 来自本次 envelope 输入。shared 不信 producer 自报的 primary_verdict，而是调同一个纯函数 `decide()` 重算。
- 残余边界：`approved_by` 是收据中登记的裁决主体，不带密码学签名；本批按工程总纲的“裁决收据”强度实现，没有虚构它能证明真人身份。

#### 视角②：失败分支

- F-01：tip 获取前失败时没有可诚实填写的 tip；tip 获取后，字段先写入再做 getCode/proxy/窗口/事件/裁决，所有 finish 分支自然继承。无代码路径已做原反例测试。
- F-02：调用政策错误走 exit 2；RPC、输入字段等检测自身错误仍走原 exit 1；真实供给不闭合仍走原 exit 2。三类语义没有混在一起。
- waiver 的缺件、损坏、必填缺失、批准范围、target、replay、evidence 分支逐一 fail-closed。shared 端再次复核，producer 和 consumer 不形成“自己说自己对”的单点信任。
- exploration 不进入正式聚合器；本批没有借 waiver 松动其他容差。

自审结论：未发现需要继续改码的批 A 缺口。发现过一项额外限制——shared 曾要求普通 replay_stats 必须位于案根内，会误伤复制案例；该非工单约束已删除，原有 envelope sha/size 绑定保留，`test_a4_gate.py` 23/23 恢复绿色。

### ⑤ 归因预判

- F-01：6.39.3 修复中新引入。
- F-02：历史漏检，自 v6.0.0 起存在。

## diff-finding-map

| 文件／hunk | finding | 归属说明 |
|---|---|---|
| `scripts/evm/accounting_gate.py` help 与 tip 赋值前移 | F-01 | 新增 model_probe，保证 tip 取得后的所有 finish 收据带 tip |
| `scripts/lib/supply_truth_gate.py` 常量、waiver 解析与文件引用校验 | F-02 | 定义 formal 上限与强绑定裁决收据 |
| `scripts/lib/supply_truth_gate.py` 新 CLI、formal 前置政策、envelope input | F-02 | 无 waiver 高容差 exit 2；合法 waiver 只绑输入 |
| `scripts/report/shared_release_receipt.py` `_validate_tolerance_policy` 与 `decide` import | F-02 | consumer 独立重算、钳制与 waiver 二次复核 |
| `scripts/report/shared_release_receipt.py` EVM tip/as_of 检查 | F-01 | 仅 EVM 拒绝缺 tip 与时点倒挂 |
| `scripts/tests/test_repair_batch_a.py` | F-01＋F-02 | 原反例、变体、失败分支、合法绿例 |
| `scripts/tests/run_all.py` | F-01＋F-02 | 显式挂载新回归文件 |
| `scripts/tests/test_audit_release_gate.py` fixture | F-01＋F-02 | 既有合法 EVM fixture 补双时点与 canonical tolerance 输入 |
| `scripts/tests/test_handoff_manifest.py` fixture | F-02 | 既有合法 supply truth fixture 补 tolerance 与 replay_stats 输入名 |
| `scripts/tests/invariant_manifest.json` | F-02 | 登记两个运行时代码点消费 tolerance-waiver；未改批 D 两份契约快照 |
| 本工单 | F-01＋F-02 | 五栏、证据、边界与未绿原因落盘 |

## 新契约面清单

- 新 CLI：`supply_truth_gate.py --tolerance-waiver <receipt.json>`。
- 新 schema 名：`tolerance-waiver/v1`。
- 新 accounting 字段：`model_probe_block`。
- 既有字段的新强制语义：EVM 正式发布的 `tip_block` 必填，且 `as_of_block <= tip_block`。
- 新 envelope input 名：`tolerance_waiver`。
- waiver 新字段：`approved_tolerance_bps`、`approved_by`、`user_decided_at_utc`、`target`、`replay_stats`、`evidence_refs`、`reason`。
- 新政策：formal `tolerance_bps` 无 waiver 时限定 0..10；exploration 不钳。

按铁律，本批没有改 `scripts/tests/contract_manifest.json` 与 `scripts/tests/contract_ids_snapshot.json`；统一契约快照登记留批 D。

## 验证与最终退出码

- `python3 -m py_compile`：退出码 0。
- `python3 scripts/tests/test_repair_batch_a.py`：退出码 0，6/6。
- `python3 scripts/tests/invariant_scan.py`：退出码 0，52 producers / 57 consumers / 62 transport / 43 atomic writes / 58 formal entrypoints。
- `python3 scripts/tests/test_a4_gate.py`：退出码 0，23/23。
- 既有定向回归：supply truth、audit release、handoff 67 项、round4b provenance、Solana release negatives 均退出码 0。
- `git diff --check`：退出码 0。
- 版本三处 `VERSION`、`SKILL.md`、`pyproject.toml` 均未改，保持 6.39.5。
- 批 B/C/D 生产文件未改；两份批 D 契约快照未改；未 commit。

最终命令：`python3 scripts/tests/run_all.py`。

最终退出码：`1`。SUITE 共 92 项，90 项通过，只有以下 2 项没有进入业务断言：

```text
FAIL(rc=1) test_batch3_solana_vertical_slice.py
PermissionError: [Errno 1] Operation not permitted
  at ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler) -> socket.bind

FAIL(rc=1) test_batch3_evm_vertical_slice.py
PermissionError: [Errno 1] Operation not permitted
  at ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler) -> socket.bind
```

这是当前 managed sandbox 禁止 loopback 监听的能力限制，不是测试断言失败。不能把本次全量结果称为“全绿”；裁判必须在允许本机 `127.0.0.1` bind 的环境重跑同一条 `run_all.py`，退出码 0 后才满足工程总纲的最终验收铁律。没有为追求绿色而改弱或跳过这两条纵切片。

本批完成

## 边界外验收（裁判出题）

### 用例 1：waiver 生成后原地替换

- 已落盘可重放反例：`maintenance/repair-20260813-sixlens/counterexamples/waiver_swap_integrity.py`。
- 构造过程：producer 以合法 waiver 生成 10000bps 高容差 PASS 的 `supply_truth.json`；随后保持该收据字节不变，把案根 `waiver.json` 原地替换为另一份结构自洽、内容不同的 waiver（内部 replay/evidence 引用仍与磁盘实物相符）；wrapper 的 `supply_truth.json` size/sha256 按当前实物重建，堵死"外层哈希先炸"的捷径。
- **结论：校验器已拒绝，不存在需补生产校验的缺口。** 拒绝发生在 `validate_reconciliation_check` 调用的 `receipt_validate.validate_receipt` inputs 三验，早于 `_validate_tolerance_policy` 读取 waiver 内容。

本次验收把反例加强为双场景。原版只构造了变长替换，命中的是 size 一项——那只能证明"长度恰好变了会被发现"，不足以证明绑定校验真的落在内容上。补的 B 场景是边界外一步：只把理由里一个汉字换成同宽度的另一个汉字，文件 614 字节分毫不差，size 完全看不出破绽。

| 场景 | 构造 | 文件大小 | 命中分支 |
|---|---|---|---|
| A 变长替换 | `approved_tolerance_bps` 10000→20000、理由改文 | 614→629 字节 | `size mismatch` |
| B 等长替换 | 只换一个同宽度汉字（"已"→"经"） | 614=614 字节 | `hash mismatch` |

反例脚本退出码：`0`。两条命中错误原文：

```text
[A 变长替换 614→629 字节] reconciliation supply_truth receipt envelope invalid: input tolerance_waiver size mismatch；存量案例须重跑对应生产者获取当前回执
[B 等长替换 614=614 字节] reconciliation supply_truth receipt envelope invalid: input tolerance_waiver hash mismatch；存量案例须重跑对应生产者获取当前回执
```

- 脚本显式断言两条都必须被拒，且分别命中 size / hash 分支；B 场景另断言 `size == bound_size`，等长没构造成功就直接红，不允许悄悄退化成第二个 A。
- 批 A 回归 `test_f02_waiver_swap_integrity_counterexample` 重放该脚本，断言同时加强为两条分支特征都要出现（只加强，未改弱原断言）。

#### 纵深如实标注：这道防线是"单点但必经"

额外做了一次只读打桩探测（纯内存 mock，未改任何仓库文件）：把 `validate_receipt` 打桩成"没有意见"后重跑上面两个场景，**两条都穿透**。

```text
[A 变长替换] 穿透——envelope 三验是唯一拦截点
[B 等长替换] 穿透——envelope 三验是唯一拦截点
```

也就是说 `_validate_tolerance_policy` 自己并不复核 waiver 的 size/sha256，它直接读文件内容；掉包全靠 envelope 三验那一层拦下。按裁判给的判定规则，校验器实际拒绝即走"记录"分支、不走"补"分支，故本批未擅自扩大改动去加第二层。

判它当前合规的依据是**必经之路**，已用 rg 核实，不是靠推测：

```text
rg -n --glob '*.py' '_validate_tolerance_policy' scripts
=> 仅 shared_release_receipt.py:135 定义、:315 调用（唯一调用点）
rg -n 'validate_receipt' scripts/report/shared_release_receipt.py
=> :224 envelope_errors = validate_receipt(receipt)，:225-227 有错立即 raise
```

`_validate_tolerance_policy` 全库只有一个调用点，位于 `validate_reconciliation_check` 内第 315 行，而第 224 行的三验必先执行且不通过就抛错。生产路径上绕不过去。

遗留风险（交裁判判断，本批不动）：这层拦截依赖调用顺序而非 `_validate_tolerance_policy` 自身。将来若有人新增一条直接调用它的路径、或把三验挪到它之后，防线会静默失效而现有测试仍全绿。要根治就得在 `_validate_tolerance_policy` 里对 `inputs.tolerance_waiver` 自行三验后再读内容——即裁判原题里"若放行则补"的那段修法，可作为后续批次的候选。

### 用例 2：formal tolerance 上限常量单源

- `scripts/report/shared_release_receipt.py` 改为从 `supply_truth_gate` 同源导入 `FORMAL_TOLERANCE_BPS_MAX` 与 `decide`，条件从 `tolerance > 10` 改为 `tolerance > FORMAL_TOLERANCE_BPS_MAX`；错误文本也由该常量插值生成。
- `scripts/tests/test_repair_batch_a.py` 新增 `test_f02_tolerance_cap_uses_producer_constant`，守卫断言 shared 暴露的上限值与 `supply.FORMAL_TOLERANCE_BPS_MAX` 相等。
- 运行时代码常量引用清单：

```text
scripts/report/shared_release_receipt.py:20:from supply_truth_gate import FORMAL_TOLERANCE_BPS_MAX, decide
scripts/report/shared_release_receipt.py:157:    if tolerance > FORMAL_TOLERANCE_BPS_MAX:
scripts/report/shared_release_receipt.py:160:                 f"{FORMAL_TOLERANCE_BPS_MAX}bps lacks tolerance waiver")
scripts/lib/supply_truth_gate.py:68:FORMAL_TOLERANCE_BPS_MAX = 10
scripts/lib/supply_truth_gate.py:292:    if (mode == "formal" and a.tolerance_bps > FORMAL_TOLERANCE_BPS_MAX
```

- 清零命令：`rg -n --glob '*.py' --glob '!scripts/tests/**' 'tolerance[^\n]*(>|>=)[[:space:]]*10\b' scripts`，退出码 `1`、输出 0 条；没有第三处把该 10bps 上限手抄进运行时比较。
- 为免漏网，另跑两条更宽的扫描交叉验证：

```text
rg -n --glob '*.py' --glob '!scripts/tests/**' '(>|>=)[[:space:]]*10\b' scripts
=> 5 行，全部与容差无关（handoff_manifest 理由串长度 >=10、scan_bloxroute_seg 文件字节数 >10、
   price_check / cost_engine / build_price 各自的毫秒时间戳 >10**12），无一处是 tolerance 上限。

rg -n --glob '*.py' --glob '!scripts/tests/**' '10[[:space:]]*bps' scripts
=> 1 行：scripts/lib/supply_truth_gate.py:272
```

**诚实标注**：上面这唯一一条命中的不是判定代码，是 argparse 的帮助文本——

```text
scripts/lib/supply_truth_gate.py:272:  help="formal 模式超过 10bps 时必需的 tolerance-waiver/v1 输入收据"
```

它是给人看的说明字符串，不参与任何比较，改动它不会让闸放行或收紧，因此不算"第三处手抄"。但它确实是一处未与常量联动的字面量：将来把 `FORMAL_TOLERANCE_BPS_MAX` 从 10 改成别的值，这句 help 会变成过时的错误提示，而守卫断言只比对两个模块的常量、抓不到它。同一文件第 294 行的 stderr 提示语（"正式模式 --tolerance-bps 上限为 10"）有同样性质。两处都只是文案漂移风险、不是判定漂移，本批按裁判口径不改，如实记录在此供后续批次决定是否改成常量插值。

### 指定验证退出码

全部在本次验收环境实跑采集，非沿用上一轮记录。

| 命令 | 退出码 | 摘要 |
|---|---|---|
| `python3 scripts/tests/test_repair_batch_a.py` | `0` | batch A F-01/F-02 regressions 8/8 |
| `python3 scripts/tests/invariant_scan.py` | `0` | producers=52 / consumers=57 / transport=62 / atomic=43 / formal=58 / exceptions=0 |
| `python3 scripts/tests/test_a4_gate.py` | `0` | 23 项 |
| `python3 scripts/tests/test_supply_truth_gate.py` | `0` | 形态①/②离线契约全过 |
| `python3 scripts/tests/test_audit_release_gate.py` | `0` | 十一类契约全过 |
| `python3 scripts/tests/test_handoff_manifest.py` | `0` | 67 项 |
| `maintenance/.../counterexamples/waiver_swap_integrity.py` | `0` | A/B 双场景均被拒 |
| **`python3 scripts/tests/run_all.py`** | **`0`** | **SUITE 92 项全通过，0 FAIL** |

上一轮记录的两条纵切片未跑，是当时 sandbox 禁止 loopback bind 的能力限制。本次环境允许 `127.0.0.1` bind，两条都真实跑完并通过：

```text
PASS  test_batch3_solana_vertical_slice.py PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release
PASS  test_batch3_evm_vertical_slice.py    PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
```

至此工程总纲的最终验收铁律（全量 `run_all.py` 退出码 0）已满足，且不是靠改弱或跳过任何一条达成的。

- 版本仍为 6.39.5；未改 `VERSION`、`SKILL.md` 版本行、`pyproject.toml version`、两份契约快照或批 B/C/D 生产文件；未 commit。
- 本次边界外验收只动了三个文件：`counterexamples/waiver_swap_integrity.py`（加强为双场景）、`scripts/tests/test_repair_batch_a.py`（断言加一条 hash 分支）、本工单。生产代码 `shared_release_receipt.py` 与 `supply_truth_gate.py` 经独立核验判定已正确，未再改动。

边界外验收完成
