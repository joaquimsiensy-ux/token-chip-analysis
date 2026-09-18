# 收官review：通过

审查范围：`8b041842 → f2d02cdffa0b205620c86fa40f82eff49d265f6c` 的全部 scripts 改动。三个指定反例均已闭合，未发现需退回项。原样回归为 **2 PASS、5 SANDBOX-BLOCKED、0 真实 FAIL**；受阻项按约定由调度方本机 `run_all` 补验，未计为 PASS。

全程离线、无文件修改、无 commit，结束时工作区干净。未读取 `~/.codex/`、memories 或其他禁读内容；maintenance 仅读取指定 ruling。报告全文已打印到 stdout。

复现采用两个版本的真实生产源码及自行构造的内存夹具，不依赖新增测试断言。closeout 保留真实入口、工单、哈希、fig2、facts 和发布重算；无关的 release dryrun、A4、identity、A5 bundle 使用固定通过结果的替身，文件输出置于内存。完整原样回归的受阻情况单列如下。

**a) F04：rpc_missing_result**

单端点实际经过 `eth_chainId → eth_getCode`，握手返回 `0x38`，业务返回 `{"jsonrpc":"2.0","id":1}`。

| 观察项 | 基线 | HEAD |
|---|---|---|
| RpcPool | `ok=true, result=null` | `ok=false`，错误为 missing result |
| getcode 退出码 | 0 | 1 |
| 地址结果 | `is_contract=false` | 仅 `error`，没有 `is_contract` |
| 摘要 | EOA 1／失败 0 | EOA 0／失败 1 |
| 合法交易收据 `result:null` | `ok=true` | `ok=true` |

拒绝位置：[net.py:298](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/net.py:298)。另核实合法 `"0x"`、`"0x6080"` 仍成功；getCode 的 null、奇数长度、非十六进制和整数返回均被 HEAD 拒绝。

**b) F05：price_gate_content**

真实 `price_check.py` 主 50／副 100，三点偏差均为 **66.67%**、状态均为 FAIL，退出 **2**。绑定正确收据哈希后：

| 场景 | 基线 closeout | HEAD closeout |
|---|---|---|
| 真实三点 FAIL | PASS／0 | BLOCK／2 |
| 仅手改 verdict=PASS，再重绑收据哈希 | PASS／0 | BLOCK／2，重算不一致 |
| `price_file_sha256` 错绑 | PASS／0 | BLOCK／2 |
| 真实旧版 PASS 收据，缺价格文件哈希 | PASS／0 | BLOCK／2 |
| 真实 ALL_SKIP，生产者退出 3 | PASS／0 | BLOCK／2 |
| 内联纯申报 `{"status":"PASS"}` | PASS／0 | BLOCK／2 |
| 主 50／副 54，三点 WARN | PASS／0 | PASS／0，记 NOTE |
| 正常 PASS、内联有效 receipt | PASS／0 | PASS／0 |
| 收据引用自身哈希错误 | BLOCK／2 | BLOCK／2 |

真实 FAIL 在 [stage2_closeout.py:276](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:276) 拒绝，实际文案：

```text
WORKORDER BLOCK: bindings.price_source_checks.verdict: PASS|WARN（FAIL/ALL_SKIP 禁入装配：换源或人工裁决后重跑 price_check） != FAIL
```

手改 verdict 在第 273 行拒；价格源错绑在第 286 行拒；旧收据在第 283 行拒；纯申报在第 256 行拒。WARN 实际记录：

```text
NOTE: 价格双源 WARN 点 3 个（>5% 过目口径，见 report-template 2b）
```

这些拒绝场景均由 `workorder` 阻断，未借其他错误代替目标拒绝。

**c) F02：flow_migration**

独立三账夹具：total=1000、e1 current=100、peak=150、标签“大庄#1”。

| 分支 | 基线 | HEAD |
|---|---|---|
| 声明 `{raw:"400",asof:"2026-01-03",source:"…"}` | derive 忽略；空 flow 放行 | 产出流通量及来源；发布重算一致；空 flow 拒绝 |
| 扁平 `facts_inputs.circulating_supply_raw` | 静默忽略 | ValueError，明确指出“键名错位” |
| 无声明，手补 facts 流通量 | 发布重算拒绝 | 仍拒绝 |
| 声明 400，facts 手改为 401 | 发布重算拒绝手补字段 | `facts.token` 不一致，BLOCK |
| HEAD 仅手改流通量来源 | — | 同样 BLOCK |

HEAD 中总量占比为 10%，流通量占比为 25%；实际错误：

```text
WORKORDER BLOCK: flow.eligible_entity_ids: 包含下限 ['e1'] != []
```

生产位置：[facts_gate.py:503](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:503)；扁平键拒绝在第 383 行。发布闸 [audit_release_gate.py:1572](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:1572) 比较整个 token 字典，实际报：

```text
facts.token 与三账重算值不一致
```

手改场景在 closeout 聚合中由 `facts_vs_ledgers` 单独 BLOCK，退出 2。

**d) 整体白名单**

指定路径的差异恰为这 8 个文件：

```text
 scripts/lib/net.py                           |   5 +-
 scripts/lib/rpc_batch.py                     |  10 ++-
 scripts/prices/price_check.py                |  11 +++
 scripts/report/facts_gate.py                 |  30 +++++++-
 scripts/report/stage2_closeout.py            |  65 +++++++++++++++--
 scripts/tests/test_batch1_rpc_attestation.py |  71 ++++++++++++++++++
 scripts/tests/test_report_facts.py           |  38 +++++++++-
 scripts/tests/test_stage2_closeout.py        | 103 +++++++++++++++++++++++++--
 8 files changed, 317 insertions(+), 16 deletions(-)
```

| 字节口径 | 基线 | HEAD | 工作区 |
|---|---:|---:|---:|
| SKILL.md | 8021 | 8021 | 8021 |
| references/**/*.md，42 文件 | 930076 | 930076 | 930076 |
| commands-staging/*.md，4 文件 | 8798 | 8798 | 8798 |

文档及 `VERSION`、`pyproject.toml`、`CHANGELOG.md` 均无本段差异。字节核对仅使用对象大小和文件元数据，未读取 attic.md 正文。`git diff --check` 退出 0。

**e) 相互影响与原样回归**

F05 价格检查与 F02 flow 检查均保留，两个新增测试函数均已注册。交叉复现确认：

- 流通量 400＋PASS＋空 flow：因缺图 BLOCK。
- 流通量 400＋FAIL＋空 flow：同时报告价格 verdict 和必画下限错误。
- 流通量 400＋FAIL＋已补图：仍因价格 BLOCK。
- 流通量 400＋WARN＋已补图：PASS，同时保留两类 NOTE。
- 声明 400、facts 改为 401＋WARN＋已补图：发布重算 BLOCK。

以下均原样执行 `python3 -B scripts/tests/<文件>`：

| 文件 | rc | 结果 | 实际尾行 |
|---|---:|---|---|
| invariant_scan.py | 0 | PASS | 见 P1 |
| test_net_result.py | 0 | PASS | 见 P2 |
| test_batch1_rpc_attestation.py | 1 | SANDBOX-BLOCKED | T1 |
| test_stage2_closeout.py | 1 | SANDBOX-BLOCKED | T1 |
| test_audit_release_gate.py | 1 | SANDBOX-BLOCKED | T1 |
| test_report_facts.py | 1 | SANDBOX-BLOCKED | T2 |
| test_state_from_facts.py | 1 | SANDBOX-BLOCKED | T3，异常链先出现 T1 |

```text
P1:
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0

P2:
PASS: net Result 显式状态与 curl_json 失败分类

T1:
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']

T2:
PermissionError: [Errno 1] Operation not permitted: '/private/tmp/r07-facts-gk60w2xx'

T3:
OSError: Matplotlib requires access to a writable cache directory, but there was an issue with the default path ({configdir}), and a temporary directory could not be created; set the MPLCONFIGDIR environment variable to a writable directory
```

T2 是测试显式指定 `/private/tmp` 后的建目录权限拒绝，同属沙箱写权限阻断。五项完整原样回归及本机 `run_all` 仍由调度方补验。
