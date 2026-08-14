# 批 1 步骤③施工报告：F-03 replay 三引擎 gate 语义统一（fail-closed）

施工范围严格限定为 `maintenance/repair-20260814-batch1/plan.md` 的“修复 1：F-03 replay gate fail-closed”。未执行任何 git 命令，未改 `archive/`，未触碰步骤①②的 receipt/proxy/stake 实现，未改 fig1/A5/token、版本号、CHANGELOG、`invariant_manifest.json` 或 `contract_manifest.json`。

## ① 不变量

1. 任一重放 pass1 引擎算出布尔 `gate_pass=false` 后，基础重放证据照常落盘，但进程必须以 exit 4 终止调用链。
2. 独立 `replay_pass2.py` 必须在写任何序列或 sidecar 前读取 `replay_stats.json`：只有 `gate_pass is True` 才能编译正式序列。
3. 独立 pass2 遇到真实 `gate_pass is False` 时 exit 4；字段缺失、非布尔、JSON 损坏或必要分母字段非法属于产物/schema 故障，exit 2，不得伪装成一次正常 gate FAIL。
4. `replay_duck.py --camps` 的 gate PASS 路径维持正式 `camp_series.json`、`entity_series.json` 与两份 provenance sidecar；gate FAIL 路径只允许在 `diagnostics/gate-failed/` 写两份诊断序列，且每份顶层标 `status=DIAGNOSTIC_GATE_FAILED`，不得写任何正式 sidecar。
5. pass1 preflight 通过后若通道文件消失，必须当场非零退出，不能 warning 后继续消费残缺通道集。
6. `state_from_facts --series-source` 只接受带正式 provenance sidecar 的序列；诊断序列没有 sidecar，不能进入正式 consumer。

## ② 同族 rg 清单与查证结论

### 施工命令

```bash
rg -n 'gate_pass|sys.exit\(0 if .*gate_pass|sys.exit\(4\)|DIAGNOSTIC_GATE_FAILED|diagnostics/gate-failed|replay_stats.*schema|preflight 后消失|replay_pass2' \
  scripts/evm/replay_pass1.py scripts/evm/replay_pass2.py scripts/evm/replay_duck.py \
  scripts/evm/replay_stream.py scripts/tests/test_engine_equivalence.py scripts/tests/test_repair_batch1.py

rg -n 'replay_pass1.py|replay_pass2.py|replay_duck.py|replay_stream.py|camp_series.json|entity_series.json' \
  scripts --glob '*.py' --glob '!archive/**'

rg -n 'except FileNotFoundError|缺文件.*跳过|warn.*缺文件' \
  scripts/evm/replay_pass1.py scripts/evm/replay_duck.py scripts/evm/replay_stream.py
```

### 同族实施点

| 同族面 | 文件 | 查证/处置 |
|---|---|---|
| 纯 Python pass1 | `scripts/evm/replay_pass1.py` | 四类 JSON/CSV 基础证据保持原落盘顺序；末尾新增与 duck 逐字一致的 `[gate]` 文案和 `0/4` 退出；TOCTOU 缺文件改 exit 2 |
| DuckDB 合一引擎 | `scripts/evm/replay_duck.py` | 原有 gate exit 4 保留；内嵌 pass2 按 gate 分流，FAIL 只写诊断目录并在 sidecar 前返回 |
| 流式 pass1 | `scripts/evm/replay_stream.py` | 原有 `gate_pass=false -> exit 4` 保持不动；无 pass2，不扩大施工 |
| 独立 pass2 | `scripts/evm/replay_pass2.py` | 新增 stats JSON/schema/gate 前置检查，所有正式写入均在检查之后；没有放行参数 |
| sidecar producer/consumer | `scripts/lib/camp_series_provenance.py`、`scripts/report/state_from_facts.py` | 正式消费者仍要求 `<series>.provenance.json`；诊断分支不调用 `write_series_sidecar()`，因此不能被正式接收 |
| 黄金对表 | `scripts/tests/test_engine_equivalence.py`、`scripts/bench/golden_baseline.py` | hypothesis 同一语义事件盘对表三引擎 gate/退出码；正式六产物只在 gate PASS 比较；gate FAIL 单验零正式序列 |
| preflight 保持红 | `scripts/tests/test_fault_injection.py` | 三引擎共用四类 preflight 负例继续通过 |

额外查证：`replay_duck.py::build_events()` 仍有“preflight 后路径消失则 warning”的旧文本，但随后 `replay_provenance()` 会在内嵌 pass2 前重验输入并非零中止，不会发布正式序列。本任务书只授权关闭 `replay_pass1.py` 的该窗口，故未擅自扩大步骤③生产改动；该点如要统一“当场退出”的错误文案，应另立工单。

## ③ 三件套测试与先红后绿实跑证据

### a. 原反例：先红后绿

只追加 `scripts/tests/test_repair_batch1.py` 的 F-03 反例、尚未改生产代码时执行：

```bash
python3 scripts/tests/test_repair_batch1.py
```

真实红态命令退出码：`1`。反例内部捕获到的生产进程退出码与产物：

```text
F03 OBSERVED pass1_rc=0 pass1_products=5/5
pass2_rc=0 pass2_formal=['camp_series.json', 'entity_series.json',
 'camp_series.provenance.json', 'entity_series.provenance.json']
duck_rc=4 duck_formal=['camp_series.json', 'entity_series.json',
 'camp_series.provenance.json', 'entity_series.provenance.json']
duck_diagnostics=[]
```

同一负余额盘在修复后再次执行同命令，真实命令退出码：`0`。关键输出：

```text
F03 OBSERVED pass1_rc=4 pass1_products=5/5 pass2_rc=4 pass2_formal=[]
duck_rc=4 duck_formal=[] duck_diagnostics=['camp_series.json', 'entity_series.json']
F03 SCHEMA observed_rc={'missing': 2, 'nonbool': 2, 'malformed': 2}
F03 TOCTOU observed_rc=2 immediate=True
PASS v6.41.0 batch1 steps 1-3 RV-07/RV-04/RV-17/F-03
```

这同时证明：pass1 gate FAIL 仍保留 `merged.csv`、`balances_final.json`、`peaks.json`、`mint_ledger.json`、`replay_stats.json`；独立 pass2 零正式产物；duck 只写诊断两件且零正式 sidecar。

### b. 同族变体

- hypothesis 实跑 10 例随机 mint/burn/自转/同块/零值/大整数/负余额盘；相同语义事件盘转成 v1 CSV 与正式 receipted v2 parquet，`replay_pass1`、`replay_duck`、`replay_stream` 的 `gate_pass` 与退出码逐例一致。
- gate PASS 输入限定执行 pass2 正式六产物对表：merged、balances、peaks、mint ledger、camp series、entity series。
- gate FAIL 输入断言独立 pass2 exit 4、零正式序列/sidecar；duck 正式路径同样零件，诊断两文件均带 `DIAGNOSTIC_GATE_FAILED`。
- 流式引擎声明不支持 VARINT；保留一例 `10**45` 的 pass1/duck `--force-varint` 确定性六产物对表，避免为三引擎公共域测试而丢失既有大值覆盖。

### c. 失败分支

- `gate_pass` 缺失、字符串 `"false"`、损坏 JSON 分别实跑，三者均 exit 2 且零正式序列件。
- `gate_pass=false` 是正常计算出的 gate FAIL，独立 pass2 exit 4，与 schema 故障明确分码。
- pass1 的 preflight 返回后删除真实通道文件，立即 exit 2，输出含“preflight 后消失”且不再出现旧 `[warn] 缺文件`。
- duck gate FAIL 诊断输出函数在 sidecar 逻辑前返回；诊断目录中 `*.provenance.json` 数量为零。
- 三引擎 preflight 的 missing file、interval hole、empty without native completion、uncovered bounds 四类旧负例保持通过。

## ④ 新建代码六视角①②自审

### ① 字段来源审计

- `replay_pass1.gate_pass` 仍只由本次重放整数账本的 `sum_balances == mint_total` 与 `neg_balance_addrs == 0` 计算；新增代码只消费该本地产生的布尔值决定退出码，没有新增调用者自报字段。
- 独立 pass2 不接受 CLI 覆盖值，直接从指定 data dir 的 `replay_stats.json` 读取；以 `type(gate_pass) is bool` 严格区分真实布尔与 `0/1`、字符串、null、缺字段。
- duck 的诊断分流读取同一进程刚计算并落盘的 `stats["gate_pass"]`；诊断状态由失败分支常量写入，不作为放行证据。
- 正式 consumer 的准入证据仍是 producer sidecar 对序列、camps spec、replay stats、终态余额的哈希/大小绑定；诊断分支不具备该证据链。

结论：本步没有把关键准入改成自报值；gate 来源、类型和 consumer 证据链均可离线重验。

### ② 失败分支审计

- pass1 的负余额/供给不闭合在所有基础产物写完后稳定 exit 4；通道文件在 preflight 后消失则在读取前 exit 2，不进入空账本重放。
- pass2 的 gate/schema 检查位于 camps spec 读取、序列构造、JSON 写入、sidecar 写入之前；两类失败均零新增正式产物。
- duck 只有 `stats["gate_pass"] is true` 才把原 out dir 交给正式 pass2；false 时使用固定子目录并显式关闭 sidecar 路径，最终仍走原 exit 4。
- 诊断分支本身若目录创建或文件写入失败，异常向上形成非零，不会回落到正式路径或 exit 0。
- 没有 `--allow-gate-fail`、环境变量或空参数绕过；gate 是 pass2 的无条件必经点。

结论：新分流未发现 warning 后继续成功、异常降级为正式产物或可选参数绕闸。

## ⑤ 归因预判确认

推翻计划中的“历史漏检”预判，按从严规则归为：**老问题修复不全（半修残留）**。

证据：`references/maintenance-review-repair.md` 的历史判例原文已明确记录“6.13.0：replay 缺文件只打 warning 仍 gate_pass=true”。本次仍能在同一 `replay_pass1` 正式入口击穿“错误必须拒绝退出”的旧不变量；同时 `gate_pass` 虽然后来已写入 stats，却没有接到 pass1 退出条件，独立 pass2 也未消费它，说明修复深度没有闭合到调用链和正式消费者。按替代解释从严规则①，只要无法排除旧 finding 的 invariant 在原入口/同族正式入口仍被击穿，就必须判半修残留。

最强替代解释是“历史漏检”：缺文件 warning 自初始实现即存在，pass1 的退出遗漏也早于本批 repair 基线，表面符合“老代码”。不采纳理由是“早于本批基线”只是历史漏检的必要条件，不是充分条件；已有 6.13.0 判例点名同一 replay fail-open 不变量，不能用代码年龄绕过既有 finding 的闭合责任。

流程动作：今后修 gate 不只检查“是否写出 gate 字段”，必须同时列 producer 退出码、独立消费者、合一入口、诊断产物隔离四层，并由 gate FAIL 反例逐层证明调用链已终止。

## 改动文件清单

- `scripts/evm/replay_pass1.py`
- `scripts/evm/replay_pass2.py`
- `scripts/evm/replay_duck.py`
- `scripts/tests/test_engine_equivalence.py`
- `scripts/tests/test_repair_batch1.py`
- `references/data-pipeline-evm-recon.md`
- `references/maintenance-review-repair.md`
- `maintenance/repair-20260814-batch1/step3_f03_report.md`

## 验证命令与结果

| 命令 | 退出码 | 结果摘要 |
|---|---:|---|
| `python3 scripts/tests/test_repair_batch1.py` | 0 | F-03 主反例、schema 三变体、TOCTOU 全绿；步骤①②既有回归保持通过 |
| `python3 scripts/tests/test_engine_equivalence.py` | 0 | hypothesis 10 例实跑；三引擎 gate/退出码全等，PASS 六产物对表，FAIL 零正式序列，VARINT 确定性对表通过 |
| `python3 scripts/tests/test_fault_injection.py` | 0 | F0–F5、P0-02 四类 preflight×三引擎、R1 receipt 漂移全过 |
| `python3 scripts/tests/invariant_scan.py` | 0 | `receipt_producers=54, receipt_consumers=63, transport_calls=62, atomic_writes=47, formal_entrypoints=58, exceptions=0` |
| `python3 scripts/tests/docs_lint.py --all` | 0 | 58 个文档引用无断链、粗体配对完整 |
| `python3 -m py_compile scripts/evm/replay_pass1.py scripts/evm/replay_pass2.py scripts/evm/replay_duck.py scripts/tests/test_engine_equivalence.py scripts/tests/test_repair_batch1.py` | 0 | 全部改动 Python 文件语法通过 |

本步骤没有运行 `run_all.py`，因为任务书本步指定的是上述六项验证；全量 suite 与版本/manifest 收口按计划留给步骤⑦统一执行。
