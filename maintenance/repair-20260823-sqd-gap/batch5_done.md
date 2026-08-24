# 批 5 完成报告

## 结论

批 5 已按 `batch5_workorder.md` 在分支 `fix/sqd-gap-v6520`、冻结 HEAD
`8df0695` 上完成；未 commit、未切分支、未联网。当前机器验收为：两份批 5 主测与
`invariant_scan.py` 全绿，`run_all.py` 124 项中 122 项 PASS，余下两项仅为当前
沙箱禁止监听 `127.0.0.1` 的 `EPERM`。未进入批 6。

## 开工门禁与冻结边界

- `git rev-parse --short HEAD`：`8df0695`，与工单一致。
- 工单、`PLAN_errata_batch0.md` E8/E11/E12/E14/E18/E20/E25–E27、PLAN
  §4.1/§4.2.8/§4.4.3/§4.4.4、scan-schemas §14、两份契约草案均在施工前读取。
- 工单列出的代码锚点逐项以 `grep -n`/`rg -n` 核对，无需猜测改位。
- 未改 `producer_history.py`、`run_all.py`、VERSION/版本文件、references、PLAN、
  errata、契约草案、`fetch_sqd_transfers_v2.py`、`sqd_gap_repair.py`、
  `sqd_repair_core.py`、`sqd_coverage_probe.py`。
- 工单文件 `batch5_workorder.md` 是开工前已有的未跟踪输入，本批未改。

## 改动清单

### 生产与公共消费面

- `scripts/solana/replay_edges.py`
  - `reconcile` 改为 `solana-reconcile/v4` envelope；`--case-root`、
    `--as-of-slot` 强制，`--receipt` 可选且案根内。
  - 绑定 edges/meta/holders/coverage/CURRENT，base 省略 repair 三键；repaired
    三键全在场。
  - coverage/current/组合规则、SQD endpoint 指纹、时点三等式、JSON-int raw、
    PASS/0 与 FAIL/2 三元规则全部 fail-closed。
  - 删除 base meta 回写；同路径 edge/meta 在冻结读取后换包时拒签混合 receipt。
- `scripts/lib/solana_exact_validate.py`
  - 新增 `validate_reconcile_v4`、`validate_verdict_gate_triad`、
    `validate_reconcile_receipt_deep`。
  - 独立重放 edges，重算余额/负余额/mismatch/digest/count/raw、CURRENT 当前性、
    coverage、组合规则、binding、producer 与条件 inputs；repaired 使用案内真实
    canonical base edge 哈希进入 repair 深验。
- `scripts/report/reconciliation_report.py`
  - wrapper 统一 `reconciliation-report/v3`；family 由 target 推导；EVM 四项、
    Solana 五项顺序固定；新增仅 EVM 的 `--reseal`。
- `scripts/report/shared_release_receipt.py`
  - 增加 `exact_reconcile` producer/键集/公共深验；v2 wrapper fail-closed；
    holders_owners 与 supply bundle 同实物；Solana 派生产物 binding 全等。
- `scripts/report/handoff_manifest.py`
  - 自动 gate 改名 `reconciliation_checks`，旧键仅作读取别名；Solana exact receipt
    及其 inputs 同时进入 data_map/artifacts；verify 复用公共深验并核派生产物 binding。
- `scripts/report/audit_release_gate.py`
  - reconciliation 改为复用公共 wrapper/子 receipt 深验与派生产物 binding 深验。
- `scripts/lib/camp_series_provenance.py`
  - v4 现役、v2/v3 legacy fail-closed；sidecar binding 必须与 exact receipt 全等；
    edge size/hash 来源改为 `inputs.soltx_edges`。

### E20 与测试面

- `scripts/tests/test_batch3_solana_vertical_slice.py`：离线 fixture 增加 coverage，
  runner 真执行 `replay_edges.py reconcile` 产 v4 exact receipt，并把 exact/input
  引用接入 data_map/artifacts。
- `scripts/tests/invariant_manifest.json`、`test_batch4_invariant_guards.py`：登记 v4
  producer/validator/E20 纵切片与失败产物。
- `scripts/tests/sqd_v4_test_fixture.py`：增加通用最小 coverage generation/CURRENT
  测试夹具。
- 升级工单点名及 `run_all` 暴露的受影响测试：wrapper v3、Solana 五项、receipt v4、
  coverage 强制输入、sidecar binding、EVM reseal，以及旧 API 夹具。

完整文件级清单以最终 `git diff --name-only` 为准；所有改动均在工单白名单的上述
生产文件、测试/fixture/invariant 文件及本目录两个交付文件内。

## 协议对照

### `solana-reconcile/v3` → `v4`

- 新增标准 envelope：`target`、`mode=formal`、`verdict`、`exit_code`、当前 producer。
- `inputs` 必含 edges/meta/holders/snapshot/coverage map/slot counts/CURRENT；repaired
  才含 resolution/bundle/repair pointer，base 不写 null。
- 新增 `edge_source_binding`、`coverage_effective_verdict`；三 raw 字段改为 JSON int。
- `--as-of-slot == snapshot target.as_of_block == finalized_upper_slot` 使用数值相等。
- `gate_pass=true` 只对应 PASS/0；false 只对应 FAIL/2。
- base 只接受 `NO_KNOWN_NONCE_OMISSION_DETECTED`；repaired 要求有效 verdict 为
  `DEFECTS_CONFIRMED`、repair 深验通过、当前 coverage 候选包含于 census 且 gid
  与当前 pointer/binding 一致；INCONCLUSIVE 不放行。

### `reconciliation-report/v2` → `v3`

- wrapper 一律 v3、单层 checks；family 不接受 job spec 外部声明，由 target.chain 推导。
- EVM 键序为 balance/supply/supply_truth/time，禁止 exact；旧 v2 只能经 `--reseal`
  重新读取并深验四份 receipt 后原子重封。
- Solana 键序为 supply/balance/supply_truth/time/exact_reconcile，exact 引用的 v4
  receipt 必须深验通过。
- v2 wrapper 公共消费面一律 fail-closed；Solana 不 reseal，必须重跑 v4 exact+五项。

## RED → GREEN

逐项原始红、最终命令与输出摘要见 `batch5_green_evidence.txt`。工单点名的
(1)(11)(12)(13)(14)(19)(24)(31)(32)(33) 与 E20 半边均已有对应 GREEN。

最终关键结果：

- `test_reconcile_v4_receipt.py`：exit 0。
- `test_recon_fifth_check.py`：exit 0。
- `invariant_scan.py`：exit 0，75 producers / 112 consumers / 0 exceptions。
- `test_batch4_invariant_guards.py`：exit 0。
- `test_repair_batch_c.py`：227 checks PASS。
- `test_repair_batch_d.py`：全部通过。
- `run_all.py`：124 项，122 PASS；仅两个回环 server `EPERM`，无其他红项。

## 发现项（留批 6）

1. `contracts_draft/reconciliation-report_v3.json` 把
   `checks.exact_reconcile.schema/mode/gate_pass/...` 写成仿佛直接位于 wrapper item
   下；现役 runner 与公共 validator 的真实结构是 wrapper item 绑定
   `{status,exit_code,process_exit_code,producer,receipt}`，再从 `receipt` 引用实物读取
   上述 v4 字段。两者的安全语义一致，但字段路径措辞不一致。按本批纪律未改草案，
   建议批 6 明确为“referenced receipt fields”。
2. 当前沙箱禁止绑定 loopback，Solana/EVM 两个 R9 纵切片未能在此环境越过 fixture
   server 创建点；需要在 Fable 本机复验。静态 runner spec、invariant 与所有非 socket
   逻辑已绿，不能据此声称本机纵切片已执行完成。
3. ARC 26.6M 行真案与性能计时本批未运行：工单要求离线且当前 workspace 未提供 ARC
   案根。coverage 未发布时的预期结果是干净 FAIL，不得把缺 coverage 降级为旧路径。
4. VERSION 当前仍为 `6.51.0`；`producer_history.py`、版本文件与 `run_all.py` 按工单
   明令保持不变，登记/升版留收口批。

## Fable 本机复验命令

以下从仓库根执行；先把三个变量替换为 ARC 真案值：

```zsh
ARC_CASE=/absolute/path/to/ARC-case
ARC_MINT='真实 Solana mint'
ARC_SLOT='holders snapshot slot，同时也是 cache finalized_upper_slot'
```

### 1. coverage 尚未发布时的 fail-closed 探针

使用未占用的新 receipt 名，避免覆盖既有正式件：

```zsh
python3 scripts/solana/replay_edges.py reconcile \
  --mint "$ARC_MINT" \
  --case-root "$ARC_CASE" \
  --as-of-slot "$ARC_SLOT" \
  --receipt data/reconcile_receipt.batch5-probe.json
```

预期：exit 2，明确报告 `coverage 强制输入缺失`（或 coverage 深验具体失败）；不生成
probe receipt。若 coverage 已发布，则该命令应进入全量重放，不再预期缺件失败。

### 2. ARC base 案 26.6M 行全量 reconcile v4 与性能记录

确认 coverage CURRENT 已发布且目标 receipt 不存在后：

```zsh
/usr/bin/time -l python3 scripts/solana/replay_edges.py reconcile \
  --mint "$ARC_MINT" \
  --case-root "$ARC_CASE" \
  --as-of-slot "$ARC_SLOT" \
  --receipt data/reconcile_receipt.json \
  2>&1 | tee /tmp/arc-batch5-reconcile-time.txt
```

记录 `/usr/bin/time -l` 的 elapsed/real time 与 maximum resident set size。若单次超过
5 分钟，按 PLAN §4.5.2 报告实测并另立性能裁决；不得自行增加缓存或绕过深验。

### 3. 对已产 receipt 做独立深验计时

```zsh
/usr/bin/time -l python3 - "$ARC_CASE" <<'PY'
import json
import sys
from pathlib import Path

case = Path(sys.argv[1]).resolve()
repo = Path.cwd().resolve()
sys.path.insert(0, str(repo / "scripts/lib"))
from solana_exact_validate import validate_reconcile_receipt_deep

result = validate_reconcile_receipt_deep(
    case / "data/reconcile_receipt.json", case_root=case)
print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
raise SystemExit(0 if result["ok"] else 2)
PY
```

同样记录 elapsed/real 与 maximum resident set size；大于 5 分钟只报告并另立裁决。

### 4. 本机纵切片与全套

```zsh
python3 scripts/tests/test_batch3_solana_vertical_slice.py
python3 scripts/tests/test_batch3_evm_vertical_slice.py
MPLCONFIGDIR=/tmp/mpl-batch5 python3 scripts/tests/run_all.py
```

Fable 本机应允许 loopback；三条应分别 exit 0，且 `run_all.py` 不再保留沙箱 EPERM。

## 未做

- 未联网、未采集 ARC/链上新数据、未跑 26.6M 行真案。
- 未 commit、未切分支、未改版本/producer history/run_all/PLAN/errata/contracts。
- 未做批 6 的契约草案措辞修订、升版或收口登记。

## 批 5c 微修

Fable 本机 ARC 26.6M 行案实测表明：coverage CURRENT 缺失虽最终 fail-closed，
但旧执行序先进入 `load_edges`，超过 10 分钟后才会走到 `_coverage_inputs` 报缺件。
本微修只调整便宜检查的执行顺序，不改变 reconcile v4 的深验或判定语义：

- `scripts/solana/replay_edges.py` 在正式 reconcile 的 `load_edges` 前执行便宜探针：
  校验 `--as-of-slot` 为非负整数；检查并解析
  `data/sqd_coverage/CURRENT.json`、`data/holders_snapshot_meta.json` 与案根 base meta。
  coverage CURRENT 缺失仍以原文
  `coverage 强制输入缺失: data/sqd_coverage/CURRENT.json` 返回 exit 2。
- `_coverage_inputs` 及 `cmd_reconcile` 内的完整 coverage、cache、snapshot、slot、哈希和
  receipt 深验均保留原位；便宜探针通过不代表深验通过。
- `scripts/tests/test_reconcile_v4_receipt.py` 新增 8 MiB 大边文件顺序回归；monkeypatch
  规定 `load_edges` 一旦被调用即抛
  `AssertionError("edges loaded before cheap preflight")`。

红→绿证据：

- RED：仅加测试时 exit 1，trace 命中 `replay_edges.py:730 load_edges`，随后抛出
  `AssertionError: edges loaded before cheap preflight`。
- GREEN：实现便宜探针后 `test_reconcile_v4_receipt.py` exit 0，并输出
  `GREEN batch5c coverage 缺件在大边文件 load_edges 前 exit 2`。
- 全套：`MPLCONFIGDIR=/tmp/mpl-batch5c python3 scripts/tests/run_all.py` 未新增红；
  仍仅 `test_batch3_solana_vertical_slice.py` 与
  `test_batch3_evm_vertical_slice.py` 因本沙箱
  `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 报
  `PermissionError: [Errno 1] Operation not permitted`。其余项目全部 PASS。

边界：本微修未联网、未 commit、未切分支；除上述实现文件、就近测试和本验收记录外
未写其他文件，未进入批 6。

## 批 5d 微修

### 语义裁定

按本次 Fable 本机验收裁定，PLAN §4.4.2 的“拒 symlink”用于拒绝案根末段本身作为
指向另一案的别名，不用于拒绝 macOS `/var -> /private/var`、`/tmp -> /private/tmp`
这类系统级祖先。输入路径先 canonicalize；安全身份比较在 resolved 域执行；案根原始
末段自身仍用 `is_symlink()` fail-closed。

### 改动清单

- `scripts/solana/sqd_cache_identity.py`：`_case_root` 删除逐祖先 symlink 拒绝；先
  `resolve()`，只拒输入末段自身 symlink，错误文案改为
  `case_root itself must not be a symlink`，返回值仍为 resolved root。
- `scripts/report/wave_scan.py`：resolver 的 edge/meta 身份对表从 `abspath` 字符串比较
  改为双方 `Path.resolve()` 后比较，允许 `/tmp` 与 `/private/tmp` 指向同一实物。
- `scripts/solana/replay_edges.py`：formal `load_edges` 不再把 resolver ValueError 转成
  字符串型 `SystemExit`；异常交给 `main` 既有 fail-closed 捕获，输出干净 `BLOCK:`
  并返回 exit 2。
- `scripts/tests/test_reconcile_v4_receipt.py`：新增 macOS `/tmp` symlink 祖先正例、
  wave resolved-path 正例、完整 reconcile 正例，以及案根自身 symlink 的 exit 2 负例。

### 同型比较 grep 核对表

| 路径 | resolver 身份比较现状 | 处理 |
|---|---|---|
| `scripts/report/wave_scan.py` | 两处 `abspath` 与 resolver resolved Path 比较 | 改为双方 `Path.resolve()` |
| `scripts/report/flow_anomaly_scan.py` | 复用 `wave_scan.load_sol`，无本地同型比较 | 不动 |
| `scripts/report/entity_source_trace.py` | 复用 `wave_scan.load_sol`，无本地同型比较 | 不动 |
| `scripts/solana/curve_cost.py` | 直接消费 resolver 返回 edge/meta，无外来路径相等判断 | 不动 |
| `scripts/solana/audit_closed_accounts.py` | 正式路径直接消费 resolver 返回 edge，无同型比较 | 不动 |
| `scripts/lib/camp_series_provenance.py` | resolver meta 与 receipt meta 已双方 `.resolve()` | 不动 |
| `scripts/solana/replay_edges.py` | reconcile meta 对表已双方 `.resolve()`；evolution 共用 resolver | 比较不动，仅修异常退出语义 |
| `scripts/solana/sqd_gap_repair.py` | 无 lexical-vs-resolved 相等比较；入口已只查 `Path(args.case_root).is_symlink()` | 不动 |
| `scripts/solana/sqd_cache_identity.py` | meta/bundle/generation 身份比较均已在 resolved 域 | 除 `_case_root` 外不动 |

### 红→绿与回归

- RED：只加回归时 `test_reconcile_v4_receipt.py` exit 1，`/tmp/...` 在旧
  `_case_root` 逐祖先检查处抛 `case_root must not contain symlinks`。
- GREEN：目标测试 exit 0；`/tmp/...` resolver/wave/reconcile 接受，案根自身 symlink
  输出 `BLOCK: case_root itself must not be a symlink`、exit 2、零 receipt。
- `test_sqd_gap_repair.py`、`test_batch4_invariant_guards.py`、
  `test_sqd_consumer_v4.py` 均 exit 0；既有 symlink/fail-closed 负例未被放宽。
- Solana 纵切片在本沙箱仍先停于 loopback bind EPERM；`run_all.py` 仍仅 Solana/EVM
  两项同类 EPERM，无新增红。Fable 本机需重新执行纵切片，以确认越过 socket 后的
  exact_reconcile 生产者全链 exit 0。

边界：未联网、未 commit、未切分支；未修改 producer history、run_all、版本、PLAN、
errata 或契约草案；完成批 5d 即停。

## 批 5e 微修

### 根因与裁定

按本次 Fable 本机验收实锤：批 5 将 supply producer 的 `--work-dir` 从
`solana_scan_work` 改为 `data` 后，runner 会正确重建 `data/holders_owners.json`；但
`test_handoff_manifest.make_case` 预登记在 `data_map.json` 的同路径行仍保存旧 sha256，
因此后续 `holder_distribution_scan.py --stage initial` 正确 fail-closed，报
`owner 快照 sha256 与 data_map 不一致`。生产校验器行为正确，本微修只修测试流夹具。

### 改动

仅修改 `scripts/tests/test_batch3_solana_vertical_slice.py`：

- 增加 supply producer 明确再生文件的闭集；刷新器只遍历 `data_map.files` 已存在行，
  只对闭集命中的实物重算 `size`、`sha256`，保留 `source` 和其他字段，不扫描目录，
  不追加未知行，路径缺失或逃逸案根即测试失败。
- `execute_real_slice` 在 reconciliation runner 成功后立即刷新上述预登记行，再继续
  accounting/window/exact 与 distribution 流程。
- 核对 `make_case` 当前 data_map：runner 再生集合与预登记集合的交集只有
  `data/holders_owners.json`。`data/holders_snapshot_meta.json`、`supply_receipt.json`
  等虽由 supply producer 再生，但当前未被 make_case 预登记，因此不会被新增；若未来
  已预登记，则同一窄刷新器会更新其 size/sha256。
- exact receipt inputs 的原有缺项追加逻辑保持不变；本次刷新不代替、不扩张该逻辑。

### 红→绿与验证边界

- RED：先加离线回归时，纵切片在 socket 前以
  `NameError: refresh_runner_regenerated_data_map is not defined` 变红，证明缺少刷新机制。
- GREEN：独立离线回归 exit 0，确认 owners/snapshot 已存在行更新 size/sha256，`source`、
  自定义字段和无关 data_map 行保持原样。
- `test_handoff_manifest.py` 68 项全部通过；`test_batch4_invariant_guards.py` 通过，生产
  `holder_distribution_scan.py`、`handoff_manifest.py` 等均未修改或放宽。
- 本沙箱执行 `test_batch3_solana_vertical_slice.py` 仍先停于
  `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 的 EPERM；新增离线回归已在
  该停点前通过，但无法在此环境执行 runner 后的 distribution 链。
- `MPLCONFIGDIR=/tmp/mpl-batch5e python3 scripts/tests/run_all.py` 未新增红；仍仅 Solana/EVM
  两个纵切片因 loopback EPERM 失败，其余项目全部 PASS。
- 完整纵切片是否已越过 `holder_distribution_scan --stage initial`，由 Fable 本机复跑确认；
  本沙箱不作超出证据的 GREEN 声称。

边界：未联网、未 commit、未切分支；除纵切片测试文件与本验收记录外未写其他文件；
完成批 5e 即停。

## 批 5f 微修

### 根因与安全裁定

按本次 Fable 本机验收实锤，`handoff generate` 的 Solana supply 深验收到 `/var/...`
显示路径，而案根已经 canonicalize 为 `/private/var/...`；旧
`shared_release_receipt._bound_case_ref` 又逐祖先执行 `is_symlink()`，因此把 macOS 系统
alias 当成案外逃逸。批 5d 只覆盖相等比较，不足以覆盖这一族“包含判定”。

本次统一裁定为：外来路径与案根/仓库根做包含判断前，两侧先进入 resolved 域；resolved
实物仍必须落在 resolved 根内。只因祖先是 `/var`、`/tmp` 或案根 alias 不拒绝；文件
末段本身是 symlink 仍显式拒绝，中间 symlink 解析后落到案外仍由包含判定拒绝。因此没有
放宽 `../` 或案内链接指向案外实物的安全边界。

### 改动清单

- `scripts/report/shared_release_receipt.py`：`_bound_case_ref` 不再逐祖先拒绝系统/案根
  alias；仍拒文件自身 symlink，并对 `lexical.resolve(strict=True)` 与 resolved 案根做
  包含判断。`validate_reconciliation_check` 入口先 canonicalize `root`，使 supply
  `holder_outputs.owners`、Solana bundle 及其余分支都处于同一 resolved 域。
- `scripts/report/audit_release_gate.py`：`safe_case_path` 将外来 `case_dir` 与候选路径两侧
  先 `resolve()` 再包含判定。
- `scripts/tests/test_reconcile_v4_receipt.py`：新增 `/private/tmp/real` 与 `alias -> real`
  正例，覆盖 `_safe_case_path`、`_bound_case_ref` 和 `validate_reconcile_receipt_deep`；
  同场加入 `../`、文件 symlink 指向案外、案外 receipt 三类负例。

### 全量 `relative_to/is_relative_to` 核对表

执行：

`grep -rn "relative_to\|is_relative_to" scripts/lib/ scripts/report/ scripts/solana/`

再以 `rg -n "relative_to\(|is_relative_to\(" ... --glob '*.py'` 排除 `__pycache__`；生产
源码共 54 处、无 `is_relative_to` 调用。下表逐一列出全部源码命中；行号为本批最终字节。

| 文件与命中行 | 现状 | 改否 | 理由 |
|---|---|---|---|
| `scripts/lib/anchor_selection.py:94` | resolved 搜索根下的 `rglob` 结果转相对展示 | 不改 | 纯内部构造/展示，不是外来路径包含判定 |
| `scripts/lib/receipt_kernel.py:74,91,108` | cwd/input_base/REPO 均先 resolve，候选也已 resolve | 不改 | 两侧已在 canonical 域；兼有输入 symlink 拒绝 |
| `scripts/lib/receipt_validate.py:46,73` | root 与输入 path 均先 resolve | 不改 | 已满足两侧 canonicalize |
| `scripts/lib/supply_truth_gate.py:189` | `waiver_path` 在入口 `resolve(strict=True)`；引用 path 亦 resolve | 不改 | `waiver_path.parent` 已是 canonical 根，symlink 引用另有显式拒绝 |
| `scripts/lib/time_spotcheck.py:307` | resolved 文件相对 resolved root 生成展示路径 | 不改 | 纯内部展示 |
| `scripts/report/a4_gate.py:79,405` | `safe_case_dir` 的 root/p 均 resolve；verdict 来自 `safe_case_file`，根再次 resolve | 不改 | 已在 canonical 域且逐案内段拒 symlink |
| `scripts/report/a5_report_seal.py:38,46,214,337,341` | root、receipt、charts、image 都在使用前 resolve | 不改 | 纯案内安全解析或相对展示，双方已 canonical |
| `scripts/report/adversarial_review_runner.py:56,72,86,174,293,515` | contained helper 先 resolve root/item；其余是 helper 返回物与 resolved root 的展示/固定名校验 | 不改 | 外来路径包含判定已 canonical，输出路径为内部构造 |
| `scripts/report/audit_release_gate.py:407,578` | `safe_case_path` 原来只 resolve 候选；另一处双方已 resolve | **改 407** | 407 统一先 resolve `case_dir` 与候选；578 已合规 |
| `scripts/report/build_html.py:361,398,414,437,440` | `_case`/`_formal_case`、charts、image、JSON 均先 resolve | 不改 | 内部构造且已在 canonical 域 |
| `scripts/report/distribution_explanation_check.py:40` | `raw.resolve()` 对 `root.resolve()` | 不改 | 已满足两侧 canonicalize |
| `scripts/report/holder_distribution_scan.py:127,134,262` | input/output path 与 case root 均 resolve | 不改 | 已满足两侧 canonicalize |
| `scripts/report/identity_snapshot_receipt.py:26,137,167` | raw 与 root 均 resolve；消费 root 来自 receipt 实物父目录 | 不改 | 已在 canonical 域且末段 symlink 另拒 |
| `scripts/report/reconciliation_report.py:53` | `_case_path` 调用前 `case_dir` 已 resolve，候选再 resolve | 不改 | runner 入口已 canonicalize，逐案内段仍拒 symlink |
| `scripts/report/reproduce_receipt.py:49,115` | main 先 resolve `case_dir`，inside 输出已 resolve | 不改 | 内部安全解析与展示 |
| `scripts/report/shared_release_receipt.py:92,114,348,386,439,735,1294,1480` | 92/114/386/439/735/1480 两侧已 resolve；348 逐祖先误拒 alias；1294 所在 validator 的 root 未先 resolve | **改 348、validator 入口（覆盖 1294）** | 修复本次实锤族；其余已 canonical，且案外 resolved 实物继续拒绝 |
| `scripts/solana/scan_token_accounts.py:138` | resolved 输出相对 `Path.cwd().resolve()` 仅作展示 | 不改 | 纯内部展示 |
| `scripts/solana/sqd_gap_repair.py:328,1085,1268,1269,1277,1279,1306` | `case_root` 入口已 resolve；edge/meta/coverage/final 都由该根内部构造 | 不改 | 纯内部路径登记，不是外来 lexical-vs-root 判断 |

点名但 grep 无命中的同族核对：

| 文件/函数 | 核对结果 | 处理 |
|---|---|---|
| `scripts/lib/solana_exact_validate.py:_safe_case_path` | root 与 candidate 均 resolve，再以 `root in path.parents` 判断；逐案内段拒 symlink | 不改；新增 alias 正例与两类逃逸负例 |
| `scripts/lib/solana_exact_validate.py:validate_reconcile_v4/validate_reconcile_receipt_deep` | case root、receipt path 均 resolve 后做 parents 包含判定 | 不改；新增 alias receipt 正例与案外 receipt 负例 |
| `scripts/report/handoff_manifest.py` | 无 `relative_to/is_relative_to`；包含判定使用 `realpath` 后的 `commonpath` | 不改 |
| `scripts/lib/camp_series_provenance.py` | 无本族包含调用；正式 cache/receipt 路径身份比较已双方 `.resolve()` | 不改 |

### 红→绿与验证

- RED：只加新回归时 `test_reconcile_v4_receipt.py` exit 1，trace 命中
  `_bound_case_ref`，报 `ValueError: alias owners path is a symlink`。
- GREEN：`test_reconcile_v4_receipt.py` exit 0；alias 正例通过，`../`、文件 symlink 指向
  案外、案外 receipt 均被拒绝。
- `test_recon_fifth_check.py` exit 0。
- `test_repair_batch_a.py` exit 0，45/45；既有
  `test_n1_replay_stats_must_live_inside_case_root` 案外/软链负例保持绿。
- `python3 scripts/tests/run_all.py` exit 1：124 项中 122 PASS；仅 Solana/EVM 两个纵切片
  在 fixture server 绑定 `127.0.0.1:0` 时因沙箱 `EPERM` 失败，停止点在 producer 前；
  无新增业务红项。Fable 本机需继续复跑 Solana 纵切片确认越过 handoff supply 深验。

边界：未联网、未 commit、未切分支；未修改契约草案、producer history、run_all、版本、
PLAN 或 errata；完成批 5f 即停。

## 批 5g 微修

### 根因：测试 spec 布局偏离生产惯例

Fable 本机继续执行 Solana 纵切片后，`handoff generate` 仍在 supply 深验报
`holder_outputs.owners file invalid or escapes case root`。本次复算确认不是 validator
路径规则错误：`scan_token_accounts.py` 生成 observation bundle 时，
`holder_outputs.owners.path` 原生写相邻文件名 `holders_owners.json`；消费侧因此必须以
bundle 所在目录为 base。

生产者参数核对结果：`--bundle`/`--receipt` 没有隐式默认文件名，必须显式给出同一个
commit marker；`--work-dir` 只控制 `_supply.json`、GPA、holders、snapshot meta 等实物
目录。旧测试却把 `--work-dir` 迁到 `data` 后仍将 marker 指向案根
`supply_receipt.json`，使相邻引用错误解析成 `case/holders_owners.json`。本批不改
validator，显式把测试 marker 对齐到生产惯例
`data/solana_observation_bundle.json`。

### 改动清单

白名单内仅修改 `scripts/tests/test_batch3_solana_vertical_slice.py`：

- `runner_spec` 的 supply `--bundle` 与 `receipt` 同步改为
  `data/solana_observation_bundle.json`，与 `--work-dir data` 同目录。
- supply_truth 的 `--observation-bundle`、`execute_real_slice` 读取 snapshot slot 的路径、
  `accounting_gate_sol.py --bundle` 全部引用同一 marker。
- `SUPPLY_REGENERATED_DATA_MAP_PATHS` 用新 marker 路径取代旧案根
  `supply_receipt.json`；离线刷新器回归增加已预登记 bundle 行，证明只更新既有行的
  size/sha256，保留 source，且无关行不变。
- handoff/release fixture 清理清单加入新 marker，避免未来 make_case/build_case 预置同名
  文件时污染真实 producer 执行。`reconciliation_supply_receipt.json` 与动态删除的案根
  `supply_receipt.json` 分别属于旧 reconciliation/EVM fixture，语义不同，仍保留清理，
  未误改成 Solana bundle。
- 新增 `test_supply_bundle_layout_contract`：在启动 loopback server 前静态断言
  `--bundle == receipt == supply_truth --observation-bundle ==
  data/solana_observation_bundle.json`，并断言 marker 位于 producer work-dir。

未修改 `scan_token_accounts.py`、`shared_release_receipt.py`、`handoff_manifest.py` 或其他
生产文件；没有放宽任何路径、哈希或案根包含校验。

### 红→绿与验证边界

- RED：仅加入布局回归、尚未迁移 spec 时，
  `python3 scripts/tests/test_batch3_solana_vertical_slice.py` 在 loopback 前 exit 1，命中
  `test_supply_bundle_layout_contract` 的 `assert marker == expected`。
- 静态 GREEN：迁移后同一命令先通过 bundle 布局断言与 data_map 刷新器回归，随后才在
  `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 的 `socket.bind` 处因本沙箱
  `PermissionError: [Errno 1] Operation not permitted` exit 1；未进入 producer，故不声称
  本环境完成纵切片业务 GREEN。
- `python3 scripts/tests/run_all.py` exit 1：124 项中 122 PASS；失败仍恰为 Solana/EVM
  两个纵切片的同一 loopback EPERM，其余全部 PASS，无新增红项。
- Fable 本机需继续复跑 `python3 scripts/tests/test_batch3_solana_vertical_slice.py`，确认
  新布局越过 handoff supply 深验并完成后续 release 链。

边界：未联网、未 commit、未切分支；除上述纵切片测试与本完成记录外未新增批 5g
改动；完成批 5g 即停。

## 批 5h 微修

### 根因：观测 slot 动态漂移而 exact 夹具静态钉死

直接采用本次 Fable 本机实证，不重新归因：旧 `FixtureHandler.slot=100`，并在
`getAccountInfo`、`getTokenSupply`、`getProgramAccounts` 三类 RPC 中继续递增，导致
supply observation bundle 的 snapshot slot 最终为 108；dynamic Solana runner 正确把
observed as-of 108 注入第五项 exact_reconcile。与此同时，`prepare_exact_inputs(...,
slot=103)` 把单边、cache `finalized_upper_slot` 和 coverage 全部钉在 103，因此
`replay_edges.py` 正确以 `108 != 103` fail-closed。生产件与 validator 语义正确，本批只
修纵切片夹具。

### 改动

仅修改 `scripts/tests/test_batch3_solana_vertical_slice.py`：

- 新增模块级 `OBSERVED_SLOT = 103`；`FixtureHandler.slot` 初值与纵切片入口重置值统一
  引用该常数。
- `getAccountInfo`、`getProgramAccounts` 改为
  `max(OBSERVED_SLOT, minContextSlot)`，既固定正常观测为 103，又保留对调用方
  `minContextSlot` 下限的尊重；`getTokenSupply` 固定返回 slot 103。
- `prepare_exact_inputs` 的默认 slot 与 `execute_real_slice` 调用均改用
  `OBSERVED_SLOT`，消除观测夹具与 exact/cache/coverage 间的 103 魔数双写。

### 影响面核对

- SQD coverage 探针仍保持 `--from-slot 100 --to-slot 103`；其 fixture 请求走
  `body["type"] == "solana"`、直接使用 `fromBlock`，不读取 `FixtureHandler.slot`，故不动。
- `getSignaturesForAddress` 仍输出当前 slot 103 与 `slot-10` 即 93；
  `getTransaction` 仍输出当前 slot 103，audit_closed 夹具语义不变。
- `accounting_gate_sol --as-of-slot` 与 `window_fetch(slot, slot)` 继续从 bundle snapshot
  读取 slot；现在该值为 103，与 exact edge/cache/coverage 一致。
- time 检查的 `--ref-slot {observed}` 现在为 103；fixture timestamp 仍为
  `1735689600`，时间锚语义不变。
- 未发现需要扩改的新问题。

### 红→绿与验证边界

- RED（Fable 本机既有实证）：批 5g 树执行纵切片时，四查均 PASS；wrapper 的
  exact_reconcile target 为 108，producer exit 2，原因是 as-of 108 与 cache upper 103
  不等。本批按工单直接引用该已成立红证，未另造变体。
- 静态 GREEN：独立执行 slot/layout/data_map 断言通过，确认 `OBSERVED_SLOT == 103`、
  handler 初值与 `prepare_exact_inputs` 默认值同源；5g 的 bundle 布局和 data_map 回归
  继续通过。
- `python3 scripts/tests/test_batch3_solana_vertical_slice.py` 在本沙箱仍于
  `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 的 `socket.bind` 处得到
  `PermissionError: [Errno 1] Operation not permitted`、exit 1；停止点在 producer 前，
  因此业务 GREEN 由 Fable 本机复跑判定。

边界：未联网、未 commit、未切分支；未修改任何生产脚本、validator、契约草案、其他
测试、run_all、版本、PLAN 或 errata；批 5h 仅改纵切片测试与本完成记录，完成即停。

## 批 5i 微修

### 根因：binding 注入后未同步维护既有下游哈希

直接采用 Fable 本机实证：批 5h 后 Solana 受控对账五查及 handoff 均已 PASS；release
段由 `audit_release_gate.py` 正确拦截
`universe_ref sha256 与 wave_scan 报告实际内容不一致`。release fixture 在创建
`wave_scan_report.json` 后立即把其哈希登记到
`dormant_warehouse_audit.json.universe_ref.sha256`；随后纵切片为满足 exact binding
全等要求，向 wave/flow 两份报告注入 `edge_source_binding` 并改写文件，却没有刷新该
下游引用。生产闸的内容绑定语义正确，本批只修测试突变后的派生引用维护。

### 改动

仅修改 `scripts/tests/test_batch3_solana_vertical_slice.py`：

- 新增 `refresh_binding_mutation_refs(case, rewritten_reports)`；只接受本轮实际改写且仍在
  案根内的报告实物。
- 若既有 `dormant_warehouse_audit.json.universe_ref.path` 指向本轮改写报告，仅重算并
  回写其既有 `sha256`；不新建 audit、不新增 ref、不豁免校验。
- 若既有 `data_map.json.files` 行指向本轮改写的 wave/flow 且原行已有 `sha256`，刷新
  size/sha256；保留 source 与其他字段。无对应行或无 sha256 的行不动，不追加索引行。
- `execute_real_slice` 的 binding 注入循环记录实际改写路径，循环结束后统一调用刷新器，
  保证报告内容与其下游 fixture 引用同一事务点更新。
- 新增 `test_refresh_binding_mutation_refs`：同时覆盖 universe_ref、wave/flow data_map 哈希、
  source/附加字段保留、无关行与无哈希行不变。

未修改 `audit_release_gate.py`、`test_audit_release_gate.py`、handoff 或任何其他生产/测试
文件；所有内容哈希与路径门禁保持原强度。

### 引用面核对

- `test_audit_release_gate.build_case`：同一 release 案根内唯一已知下游内容哈希是
  `dormant_warehouse_audit.universe_ref → wave_scan_report.json`，本批已同步。
- `test_handoff_manifest.make_case`：会创建 wave/flow，但 data_map 当前只登记 transfers、
  Solana edge/meta、holders owners，不含 wave/flow 哈希行；刷新器因此不改现状，未来若
  已有带 sha256 行则会窄刷新。
- flow 报告在该 release fixture 中没有已知下游哈希引用。
- 全测试 grep 另见 adjudication `source_reports` 与 repair-batch-D 的独立案根引用；它们
  不经过本纵切片的 `execute_real_slice` 突变，不属于本次同步链，未改。
- 未发现同一案根内其他需要随 binding 注入刷新的夹具哈希。

### 红→绿与验证边界

- RED（Fable 本机既有实证）：批 5h 树纵切片 rc=1，受控对账五查和 handoff 已通过，
  release stderr 命中 `universe_ref sha256 与 wave_scan 报告实际内容不一致`。本批直接
  引用该已成立红证。
- 静态 GREEN：slot、5g bundle 布局、data_map producer 刷新及新增 binding 下游引用
  刷新回归全部通过；新增回归证明只更新既有引用，不改变 source/其他字段或无关行。
- `python3 scripts/tests/test_batch3_solana_vertical_slice.py` 在本沙箱仍于
  `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 的 `socket.bind` 处得到
  `PermissionError: [Errno 1] Operation not permitted`、exit 1；停止点在 producer 前，
  业务 GREEN 由 Fable 本机继续复跑判定。

边界：未联网、未 commit、未切分支；未修改生产件、validator、其他测试、契约草案、
run_all、版本、PLAN 或 errata；批 5i 仅改纵切片测试与本完成记录，完成即停。

## 批 5j 微修

### 根因：release 段借用了 EVM wave 语义夹具

直接采用 Fable 本机实证：批 5i 后 universe_ref 哈希已通过，release 继续被
`audit_release_gate.py` 正确拦截，报 formal `scan_universe` 语义不成立。原因是
`test_audit_release_gate.build_case` 创建的 wave fixture 使用
`params.edges_evm_v2`；`wave_contract.has_formal_wave_semantics` 对该分支要求报告不得含
`edge_source_binding`。而 Solana release 的公共深验又无条件要求在场 wave/flow binding
与 exact receipt 全等。两条生产规则均正确；Solana 案根不能继续消费 EVM 语义 wave
夹具，本批只在纵切片 release 适配层转换 params。

### 改动

仅修改 `scripts/tests/test_batch3_solana_vertical_slice.py`：

- 新增 `solanaize_release_wave_fixture(case)`：读取 build_case 已创建的
  `wave_scan_report.json`，仅将 params 替换为
  `{"edges_sol":"data/soltx-<sha256(MINT)>.jsonl.gz"}`。key 算法与
  `prepare_exact_inputs` 相同，路径正是随后创建的真实 formal edge 文件。
- release 第二个 with 块在 `build_case(..., historical=False)` 后、
  `execute_real_slice` 前执行语义转换；schema v5、non_formal、order_ambiguous、
  edge_order_granularity、scan_universe/count 等字段保持不变。
- 事务顺序为：先转换 params；`execute_real_slice` 随后注入 exact 五键 binding；5i
  刷新器最后以最终 wave 字节同步 universe_ref 及既有 data_map 哈希。两次突变之间没有
  validator/consumer，因此无需增加中间哈希写入。
- 新增 `test_solanaize_release_wave_fixture`：证明 EVM params＋binding 被
  `has_formal_wave_semantics` 拒绝，Solana params＋base binding（gid=null）被接受；同时
  证明 edge 路径、scan_universe 保持及 universe_ref 最终哈希同步。

未修改 `wave_contract.py`、`audit_release_gate.py`、`shared_release_receipt.py`、
`test_audit_release_gate.py` 或其他生产/测试文件；没有删 binding 或放宽 formal 校验。

### 自查

- exact receipt 的 base binding 原生恰含五键，`cache_kind=base` 且 `gid=null`，符合
  `wave_contract.py` Solana 分支。
- `prepare_exact_inputs` 与语义化 helper 都以 `sha256(MINT).hexdigest()` 构造
  `data/soltx-<key>.jsonl.gz`，不存在路径分叉。
- release build_case 不生成 flow 报告；公共 validator 对缺失 flow 走既有
  FileNotFoundError/continue，不需要夹具转换。
- 既有 universe/candidates 字符串及逐址全集未改，后续对账仍使用原夹具内容。
- 未发现需要扩改的新问题。

### 红→绿与验证边界

- RED（Fable 本机既有实证）：批 5i 树纵切片 rc=1，release stderr 命中
  `wave_scan 报告缺 formal scan_universe 逐址全集`，实际为 EVM params 与注入 binding
  合取后 `has_formal_wave_semantics=False`。本批直接引用该已成立红证。
- 静态 GREEN：slot、bundle 布局、两类 data_map/hash 刷新及 Solana wave 语义化回归
  全部通过；新回归直接调用公共 `has_formal_wave_semantics` 验证 EVM 负例与 Solana 正例。
- `python3 scripts/tests/test_batch3_solana_vertical_slice.py` 在本沙箱仍于
  `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 的 `socket.bind` 处得到
  `PermissionError: [Errno 1] Operation not permitted`、exit 1；停止点在 producer 前，
  业务 GREEN 由 Fable 本机继续复跑判定。

边界：未联网、未 commit、未切分支；未修改生产件、validator、其他测试、契约草案、
run_all、版本、PLAN 或 errata；批 5j 仅改纵切片测试与本完成记录，完成即停。
