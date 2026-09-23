# 收官review：退回

**目录输入的两处修复已生效，但整体收官条件未满足。** 正确适配输入登记后，目录案能够贯通；旧文件案的既有时间收据会被 HEAD 拒收，目录内容生产后的误覆盖也缺少必经防线。

审查 HEAD：`bb4359113d177bf4204a2c2f0be86f705c267fac`，基线：`b52cbed`。完整报告已打印到 stdout。未读取 `~/.codex/`、memories 或被禁材料；测试依赖按你的豁免执行。全程离线、未 commit、未修改仓库。

**发现与分级**

P0：无。P1：FR-01、FR-02。P2：FR-03。

**FR-01 [P1]：旧文件案时间收据不兼容。**

- **文件:行：** [time_spotcheck.py:430](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/time_spotcheck.py:430)、[shared_release_receipt.py:1221](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/shared_release_receipt.py:1221)、[shared_release_receipt.py:1459](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/shared_release_receipt.py:1459)。
- **事实：** 修改改变了时间生产者源码哈希。收据 envelope 和 wrapper producer 两层均只接受当前哈希；没有接入该生产者的历史哈希。
- **实证：** 从 Git 载入基线时间生产者，使用 `test_recon_deep_reverify.py` 夹具生成文件输入收据，并重建该源码的真实自哈希。沿用夹具的 RPC/语义重放替身，HEAD 消费校验保持原样。旧源码身份视图通过，同一收据在 HEAD 报：
  ```text
  reconciliation time receipt envelope invalid: producer hash mismatch；存量案例须重跑对应生产者获取当前回执
  ```
  `test_handoff_manifest.py` 夹具恢复旧时间生产者身份后，READY 报：
  ```text
  [generate] reconciliation READY 深验失败: reconciliation time producer/runner is not current repository script
  ```
- **后果：** 未改输入的旧文件案升级后不能继续交接，任务 c) 不成立。现有测试每次使用当前源码哈希，未覆盖这一兼容性。
- **建议：** 登记经 Git 验证的旧 `time-spotcheck/v3` 哈希，并在 envelope、wrapper 两层精确接线。仅添加 `producer_history` 条目不够。基线哈希：
  ```text
  87bbad2246f07afa2db4b37a7289fff2fc6ac16387284411e75104e1109f0a39
  ```

**FR-02 [P1]：目录误覆盖可带着陈旧 PASS 通过发布。**

- **文件:行：** [shared_release_receipt.py:1045](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/shared_release_receipt.py:1045)、[shared_release_receipt.py:1880](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/shared_release_receipt.py:1880)、[handoff_manifest.py:301](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/handoff_manifest.py:301)。
- **事实：** 时间收据绑定清单文件；发布期不核叶子实物，witness 不展开清单。EVM READY 未强制将时间目录的叶子集合关联到 `data_map` 或冻结登记。
- **实证：** 完整目录案通过后，用 DuckDB 将 `logs.parquet` 覆写成另一份有效 parquet，不改计划、清单和收据。重新语义重放报 `input sha256 mismatch`，但 READY、verify、发布闸仍均 exit 0，`validate_bundle` 返回 `[]`，已有 witness 仍可消费。其 14 个指纹文件中没有 parquet。文件输入做同长度修改，则立即报 `time merged input sha256 mismatch`。
- **后果：** 自己人重新采集、覆盖缓存即可让当前原始数据与已通过的对账证据脱节，目录输入明显弱于文件输入。
- **建议：** **另开目录冻结与登记闭环工单。** 强制关联生产时叶子清单与冻结登记，明确文件集合变化和冻结后写入如何拦截。此项承认 §1.2“不在发布期重算目录身份”的边界，但该边界没有提供同等防误操作保证；若需消费期读取叶子，应明确重议边界。

**FR-03 [P2]：目录参数与文件登记接口仍需人工适配。**

- **文件:行：** [reconciliation_report.py:56](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/reconciliation_report.py:56)、[reconciliation_report.py:85](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/reconciliation_report.py:85)、[handoff_manifest.py:310](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/handoff_manifest.py:310)。
- **事实：** time 的 `--input v2` 可用，但 runner 顶层 `inputs.time_input="v2"` 仍拒收：
  ```text
  input file missing: v2
  ```
  `data_map.files` 直接登记目录也拒收：
  ```text
  [generate] data_map.json 显式文件路径非法: 路径不是常规文件: 'v2'
  ```
- **后果：** 不能宣称整条链已没有普通文件约束；机械替换原文件路径仍会失败。这些是既有文件登记契约。
- **建议：** 提供明确模板：两个 CLI 传目录，runner 登记 `anchor_plan.input.json` 及必要叶子，`data_map` 登记叶子。不要放宽 `receipt_kernel`。

**a) 独立端到端复现**

自行构造 `v2/run_1/logs.parquet`、`blocks.parquet`，包含 block 123 的一笔铸币事件；将 B3 同款流程的 anchor_plan 和 runner time 检查均改为 `--input v2`。合并 handoff/release 夹具，在同一个案目录执行。

真实 loopback 监听被沙箱拒绝：

```text
PermissionError: [Errno 1] Operation not permitted
```

因此真实本地桩路径记 **SANDBOX-BLOCKED**。替代实验仅将 httpx/requests 传输接到原 `FixtureHandler` 的内存响应，实际运行 CLI 子进程、runner 和 HEAD 校验器，没有绕过目录重算或收据校验。

| 关口 | 实测结果 |
|---|---|
| `anchor_plan --input v2` | PASS |
| runner 顶层 inputs 直接登记目录 | exit 2：`input file missing: v2` |
| runner 登记清单，time 参数仍传目录 | 四查全部 PASS/0 |
| `generate --status READY` | exit 0 |
| `handoff_manifest verify` | exit 0；18 件产物、4 个 gate |
| `create_bundle` / `validate_bundle` | PASS；返回 `[]` |
| `audit_release_gate --report` | 补齐夹具旧引用后 exit 0 |

发布闸首次报：

```text
universe_ref sha256 与 wave_scan 报告实际内容不一致
```

原因是合并夹具时 `make_case` 覆写了 `build_case` 的 wave_scan 文件。最小补法是在临时 `dormant_warehouse_audit.json` 更新 `universe_ref.sha256`；补后通过，无须改生产代码或 RPC 桩数据。

内存实验覆盖参数传递、链身份检查、RPC 响应解释、收据生成和消费链，不证明真实 socket/HTTP 通信。发布闸使用 B3 同款默认 `independent-audit` profile，未扩大为完整 `new-analysis`/A5 流程证明。

**b) 信任链与实际边界**

| 防线 | 能保证什么 | 局限 |
|---|---|---|
| `anchor_selection.input_identity` | 枚举文件，记录路径、大小、哈希并形成目录摘要；拒绝目录内 symlink | 生产时快照 |
| anchor_plan 清单及 receipt | 清单、计划输出、输入身份相互绑定 | 不阻止后续目录写入 |
| 时间生产者语义重放 | 重算目录摘要、选点及预期值；内容改变会拒 | 仅生产时执行 |
| 时间收据与发布 authority | plan、plan receipt、清单、身份一致；重核 transcript | 保护清单字节，不核当前叶子 |
| runner 输入快照 | 登记文件在执行前后不变 | 只登记清单时不覆盖叶子 |
| witness | 收据与直接引用文件保持一致 | 不展开清单；实测无 parquet |
| data_map / handoff manifest | 已登记叶子在 verify 时核大小、哈希 | 没有 EVM 时间目录必登集合约束 |
| provenance / entity freeze | 对其绑定的 v2 源核叶子、集合并重放 | 未强制与时间输入同源，属于条件性防线 |
| audit_input_manifest | 重核逐条登记文件 | 未强制覆盖时间目录全部叶子 |

正控制已通过：逐叶登记两个 parquet，刷新 distribution scan、重新生成 READY 后，verify 通过；随后修改 `logs.parquet`，verify exit 2，仅报：

```text
哈希/大小漂移: v2/run_1/logs.parquet
```

已有冻结机制有效，缺少的是必经关联和完整覆盖。需要另开工单，见 FR-02。

**c) 文件回归与登记结论**

- 固定时钟和相同 producer 身份后，基线与 HEAD 的文件分支收据、transcript、stdout/stderr、退出码一致；缺文件和路径越界错误一致。
- 消费侧比较合法件、错大小、错哈希、缺文件、plan/input 同时损坏五组，错误文本与优先顺序一致。
- **实际兼容行为并非完全不变：** 真实 producer 哈希改变，旧收据触发 FR-01。
- `receipt_kernel.py`、`receipt_validate.py` 相对基线字节未变，普通文件契约没有放宽。
- `invariant_manifest` 无需新增登记：未新增生产/消费 schema、传输或发布入口，扫描通过。
- 为满足旧文件案兼容，`producer_history` 需要处理，并接入两层消费者；“无需登记”结论不成立。

**d) 指定回归实跑尾行**

所有 PASS 项退出码均为 0。预期负例的 fatal/RED 输出不算失败。

| 脚本 | 结果及尾行 |
|---|---|
| `test_anchor_plan_v3.py` | `anchor-plan v3: 16/16 PASS` |
| `test_time_spotcheck.py` | `time_spotcheck 契约测试全部通过（20 项）` |
| `test_recon_deep_reverify.py` | `PASS test_recon_deep_reverify` |
| `test_handoff_manifest.py` | `handoff_manifest 契约测试全部通过（283 项）` |
| `test_audit_release_gate.py` | `PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过` |
| `test_batch3_evm_vertical_slice.py` | **SANDBOX-BLOCKED**，exit 1；`PermissionError: [Errno 1] Operation not permitted` |
| `test_batch4_invariant_guards.py` | `PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `test_exemption_guards.py` | `PASS: exemption guards (EX-01 full-F-03)` |
| `invariant_scan.py` | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0` |
| `changelog_lint.py` | `PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 82 条 + 归档 139 条` |

B3 补充内存实验跑完 ETH/BSC/Base 的 full_chain 与非零 dead 分支：

```text
PASS MEMORY B3 eth/bsc/base + nonzero dead (socket and shared handler method-list assertions excluded)
```

它不替代原样 B3 的监听及共享 handler 调用列表断言。

**e) 收官判定**

a) 正确适配后贯通；b) 存在已复现 P1；c) 旧文件案兼容失败。**按给定规则退回。**

临时夹具、脚本和日志已全部清理。`git status --short` 全文如下，输出为空：

```text
```
