# 包 3 test-only 施工完成报告（F-03 / F-14）

日期：2026-08-15
阶段：test-only
结论：F-03 预期红成立；F-14 守卫与既有发布闸回归为绿。未改生产代码，未改既有测试，未登记 `run_all.py`，未执行任何 git 命令。

## 1. 文件清单

本包只新建以下文件：

1. `scripts/tests/test_repair_g1_cross_target.py`
2. `scripts/tests/test_repair_g1_text_hygiene.py`
3. `maintenance/repair-20260815-g1/workorder_pack3_testonly_done.md`

明确未动：`scripts/report/audit_release_gate.py`、其他生产代码、`scripts/tests/` 既有文件、`scripts/tests/run_all.py`、历史证据文件。

## 2. F-03 跨分区 target 测试实况

执行：

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_repair_g1_cross_target.py
rc=1
```

总况：`r1-r8` 与 `g3` 共 9 例按 test-only 预期为红；`g1/g2` 为绿。红的统一、准确原因不是 `run()` 完全没有错误，而是其 `errors` 中没有专属的“跨分区 target 不一致”错误类。测试刻意不把既有分区内 validator 的偶然错误当成 F-03 已闭合。

| 用例 | 实况 | 红/绿原因 |
|---|---|---|
| r1 | RED | state/identity/A4/A5 全改为 `eth`，accounting/recon/shared 保持 `bsc`；`errors` 无跨分区 target 不一致项。现有 A5 深验错误只涉及手写单元 fixture 的图例/分布件，不识别两分区错链。 |
| r2 | RED | 只把 accounting/recon/shared 证据组改为 `eth`，结论组保持 `bsc`；现有 observation bundle 与 adversarial 的分区内绑定会报错，但无结论分区对证据分区的等式错误。 |
| r3 | RED | identity snapshot receipt 在同一 `bsc` 下把 token 改为另一 EVM 地址；receipt 字节哈希同步回绑 identity gate 后，仍无跨分区 token 不一致错误。 |
| r4 | RED | identity snapshot receipt 的 `as_of_block` 改为 `456`，binding 同步更新；仍无跨分区冻结点不一致错误。 |
| r5 | RED | 仅 `a5_report_seal.json.chain` 改为 `eth`；现有 A5 局部 validator 会报 `A5 seal chain 未绑定当前 A4 seal`，但没有统一跨分区 target 错误，故不能把局部命中冒充 F-03 闭合。 |
| r6 | RED | 仅 `shared_release_receipt.target.chain` 改为 `eth`；现有 shared validator 会报 `shared receipt schema/target invalid`，但没有统一跨分区 target 错误。 |
| r7 | RED | `analysis-state.json` 同时保留顶层 `chain=bsc` 与 `token.chain=eth`；现状 `or` 式消费未暴露双字段矛盾，缺跨分区错误。 |
| r8 | RED | 证据 token=`So111...112`，identity receipt token=`so111...112`，两者是仅大小写不同且都可解为 32 字节的 base58 mint；现状无 Solana 原串精确比较错误。 |
| g1 | PASS | accounting 使用别名 `solana`、identity/A4/A5 使用 canonical `sol`，token/block 相同；未出现跨分区误报。此断言是“修后仍不得误报”，不把该手写案的其他深层 validator 结果当作本例目标。 |
| g2 | PASS | 原始 `build_case` 以 `independent-audit` 运行且无 state/identity/A4，`errors=[]`；证明“缺席不硬要”的现状基线。 |
| g3 | RED | new-analysis 案保留 A4、逐个删除 identity gate/receipt/snapshot 后，未出现 A4⇒identity 的跨分区错误，旁路仍在。 |

脚本会累积执行全部用例，最后统一以非零退出，不会在 r1 首红后停止。专属错误识别要求同时具备跨分区/正式发布 target 语义和“不一致/矛盾/漂移”语义，因此 r5、r6 的既有局部错误不会造成假绿。

## 3. F-14 文本卫生守卫实况

执行：

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_repair_g1_text_hygiene.py
rc=0
PASS h1: 行尾空格、行尾 tab、全空白行逐个检出
PASS h2: br104 证据路径与 log/txt/json 后缀反向豁免
PASS h3: 不存在扫描根与空分母均 fail-closed
PASS real repository: 301 tracked active files, zero hits
```

分母严格为：

- `references/**/*.md`
- `commands-staging/*.md`
- 仓库根 `*.md`
- `scripts/**/*.py`
- `**/*.sh`
- `**/*.toml`

豁免写死为：`maintenance/**`、`blind-reviews/**`、`archive/**`、`*.log`、`*.txt`、`*.json`。出处为 br104 的证据保真裁决；守卫没有清理或改写任何存量命中字节。

为遵守本包“禁止一切 git 操作”，真实库的 tracked 分母不是通过 git 子进程取得，而是只读解析 worktree `.git` 指针及 index v2/v3。索引缺失、非法、截断、不支持或最终分母为空都会 fail-closed。h1/h2 用显式模拟 tracked 清单验证坏例与豁免，不依赖测试临时目录存在 git 元数据。

## 4. 既有回归

执行：

```text
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/tca-repair-g1-mpl \
  python3 scripts/tests/test_audit_release_gate.py
rc=0
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
```

这项回归只证明新增测试文件没有破坏既有发布闸测试；F-03 的 9 个预期红仍是 fix 阶段的生产缺口。

## 5. 手写 fixture 字段依据

本测试按“单元 schema fixture，测发布闸对字节的解释”处理，不把手写件宣称为端到端生产者输出。

- `identity_snapshot_receipt.py:33-40` 的 `base()` 定义 `identity-holder-snapshot/v2`、`status=PASS`、`complete_owner_universe`、`producer`、`adapter`、`token`、`as_of_block`、`total_supply_raw`、`snapshot.path/sha256` 与 `source`。
- `entity_identity_gate.py:115-157` 的 `load_snapshot_binding()` 验证 receipt schema/status/完整 owner 集、snapshot 文件哈希、total supply、adapter，并导出 `snapshot_file/snapshot_sha256/receipt_file/receipt_sha256/as_of_block/receipt_schema/adapter`。
- `entity_identity_gate.py:171-209` 要求 `identity_gate_v3`、canonical identity chain、`snapshot_binding`，并把 binding 与当前 receipt 字节重算结果等值比较。
- `a4_gate.py:458-469` 的 producer 形状为 `a4-seal/v4`、`verdict=PASS`、`chain`、`workflow_type`、revision 与 claims。
- `a5_report_seal.py:17,341-347` 定义 `a5-report-seal/v3`，创建时 `chain` 从 A4 复制；`:364` 已有 A5↔A4 局部 chain 绑定校验。

fixture 每次改写 state 或 identity receipt 后都会重算并更新 identity gate 的 `state_sha256` / `receipt_sha256`；改写 A4 后也刷新 A5 的 `a4_seal` 字节引用。这样 r3/r4/r7 的红因不是陈旧哈希，而是待实现的目标等式缺失。

## 6. Hunk 映射

| 文件与行段 | finding / 作用 |
|---|---|
| `test_repair_g1_cross_target.py:1-47` | importlib 白盒加载 audit gate 与既有 `build_case` fixture；用 `test_vertical_slices` 包裹 `run()`。 |
| `test_repair_g1_cross_target.py:50-189` | 手写 identity receipt/gate、A4/A5/state 及精确 SHA256 binding 的 new-analysis 单元 fixture。 |
| `test_repair_g1_cross_target.py:193-233` | 结论分区和 evidence target 的定点变异与 binding 刷新。 |
| `test_repair_g1_cross_target.py:236-246` | F-03 专属跨分区错误分类，排除既有局部 validator 假绿。 |
| `test_repair_g1_cross_target.py:253-336` | r1-r8、g1-g3 的独立变异实现。 |
| `test_repair_g1_cross_target.py:339-403` | 全例累积执行、逐例输出、test-only 统一红退出。 |
| `test_repair_g1_text_hygiene.py:13-16` | br104 固定豁免表及出处注释。 |
| `test_repair_g1_text_hygiene.py:23-72` | 无 git 命令的 worktree index v2/v3 只读 tracked 枚举。 |
| `test_repair_g1_text_hygiene.py:75-126` | 分母、fail-closed 枚举与逐行 bytes 行尾空白扫描。 |
| `test_repair_g1_text_hygiene.py:129-190` | h1 注入反证、h2 反向豁免、h3 空分母/不存在根防装死。 |
| `test_repair_g1_text_hygiene.py:193-207` | 三层自证与真实仓库零命中入口。 |

## 7. 问题决策与阶段边界

1. F-03 当前仍是生产缺口，不能因 r5/r6 已有局部 validator 错误而称为已修；fix 阶段必须让统一 target 等式错误命中 r1-r8+g3，并保持 g1/g2。
2. `state.chain` 与 `state.token.chain` 必须分别收集；测试不接受 `or` 折叠。
3. token 规范化按链族决定：EVM 可小写归一，Solana base58 必须原串精确比较。
4. A4 在场而 identity bridge 缺席必须 fail-closed；independent-audit 无 A4 时不硬要。
5. F-14 的性质仍是“政策替代 + 预防性守卫”，本包不声称历史区间文本检查已经变绿，也未运行任何 git 历史/diff 命令。
6. `run_all.py` 登记明确留到 fix 阶段；本包没有越界提前登记。
