# Round B：维护台账逐项重放

## 复核范围与冻结状态

- 仓库：`/Users/uravvv/Documents/5.6筹码分析/r9-closure-worktree`
- 分支/HEAD：`fix/r9-closure-20260807` / `45bf8f31fde258af833697510bb3aadc51e3f88a`
- 方法：只按 `maintenance/repair-20260806/ledger.md` 的 49 个 canonical ID 对表；未做自由全库审查。
- 起始状态已有未跟踪 `r9-reviews/`；复核期间未触碰。测试统一设置 `PYTHONDONTWRITEBYTECODE=1`，测试后状态仅新增本报告所在的 `blind-reviews/`。
- 测试判定口径：`run_all.py` 确实逐个子进程执行 SUITE 文件。89 个 SUITE 项中 87 PASS；两项 loopback 纵切片在 `socket.bind(127.0.0.1)` 被沙箱 `EPERM` 拦截，按任务书登记为环境阻断，不算业务 FAIL。
- 场景 ID 口径：`B1/B2/B3/B4/R9-*` 若非 Python 函数名，须由 `diff-finding-map.md`、`transport-injections.json` 或批次报告唯一映射到 `scripts/tests/` 中的具体文件/函数；只有文档别名而无实现映射时不采信。

## 结构一致性

- 主表数据行：49；canonical ID 唯一数：49。
- 详情节：49；详情 ID 唯一数：49。
- 主表减详情：空；详情减主表：空。
- 49 个详情节均含「基线回放」「最终结果」「两轮盲审与 Fable 结论」。
- 台账明确点名的 17 个测试/守卫文件均真实存在于 `scripts/tests/`，且全部挂入 `run_all.py` 的 89 项 SUITE；场景别名已按上列映射口径逐项落到具体测试函数。
- 结构结论：49↔49 一一对应，结构一致。

## 逐项 verdict 总表

| ID | verdict | 一句话依据 |
|---|---|---|
| `full-F-01` | UNVERIFIABLE | controlled-runner freshness 负例 PASS、代码确实现场启动 producer；但其声称的 EVM/Solana 真实纵切片均被本沙箱 loopback `EPERM` 阻断。 |
| `six-F-03` | UNVERIFIABLE | 与 `full-F-01` 共用执行真实性闭环；runner 负例可证，四链真实纵切片在本环境不能完成。 |
| `R7-01` | UNVERIFIABLE | `test_reconciliation_runner.py` 证明预置 receipt 在 producer 前被拒，但真实四链 producer→runner→release 纵切片无法在本沙箱闭合。 |
| `full-F-02` | CONSISTENT | Robinhood 当前为 `release_tier=exploration`、`evm_chain_id=None`，`test_batch2_robinhood_exploration.py` PASS，且 RH-EX-02 失效条件在案。 |
| `R7-03` | CONSISTENT | anchor/window alias 反例与 Solana producer 单测 PASS；两 producer 均以 `publish_txn` 联合提交。 |
| `R7-04` | CONSISTENT | `test_r7_findings.py` 与 `test_supply_truth_gate.py` PASS，formal raw override/slot/file binding 仍在。 |
| `six-F-02` | CONSISTENT | `test_sixlens_receipts.py::test_verify_recon` PASS，mismatch/RPC error 保持非零关闭。 |
| `six-F-04` | CONSISTENT | `test_sixlens_receipts.py::test_anchor_sampler` PASS；`B3F-TXN-02` 可映射到现役 anchor post-commit/txn 反例，失败不留 canonical PASS。 |
| `R7-08` | CONSISTENT | READY reconciliation 缺件负例、handoff 65 项与深验代码均通过。 |
| `six-F-05` | CONSISTENT | `test_window_fetch` PASS；gap 只留 partial/stale，正式 PASS 不发布。 |
| `six-F-07` | CONSISTENT | `test_fetch_failclosed.py` PASS；分页失败不提交正式 CSV。 |
| `six-F-08` | CONSISTENT | `test_fetch_gmgn_sh.py` PASS；临时文件、JSON 校验、失败聚合与旧件 stale 契约存在。 |
| `R8-04` | CONSISTENT | receipt-kernel 路径反例 PASS；anchor/window 的最后可失败 data+receipt 操作为 `publish_txn`。 |
| `R8-12` | CONSISTENT | kernel/producer 反例 PASS，anchor/window 联合提交后没有反转 canonical PASS 的独立内容自检。 |
| `six-F-06` | CONSISTENT | `test_fetch_failclosed.py` PASS；相等/反向/负区间在 transport 前拒绝。 |
| `R7-06` | CONSISTENT | window alias/timestamp producer 反例 PASS，成功路径联合提交且失败路径不留 current canonical。 |
| `R8-08` | CONSISTENT | `test_time_spotcheck.py` 20 项 PASS，plan/CLI final block 精确绑定且探测块不得越界。 |
| `R7-12` | CONSISTENT | `test_batch1_rpc_attestation.py` PASS，正式 EVM 调用点均先 attestation，错链业务 RPC 为零。 |
| `R8-07` | CONSISTENT | time callsite 使用 attested session；对应 wrong-chain 负例 PASS。 |
| `R8-09` | CONSISTENT | supply callsite 的 `eth_chainId` 前置与零 `eth_call` 负例 PASS。 |
| `six-F-13` | CONSISTENT | handoff 65 项和 B2 legacy 加固测试 PASS，READY 缺 target/chain/contract 均拒绝。 |
| `R7-13` | CONSISTENT | anchor-plan v2 producer 与 time consumer 均绑定 `final_block`，20 项 spotcheck PASS。 |
| `R8-03` | CONSISTENT | Solana accounting/supply producer 单测 PASS，观察 bundle 的 snapshot/supply slot 被消费者交叉绑定。 |
| `R7-02` | CONSISTENT | net Result、R7 与 six-lens receipt 测试均 PASS，curl rc=7 空 stdout 仍 ERROR/nonzero。 |
| `R8-11` | CONSISTENT | `B3F-TS-01` 现役函数存在且 PASS，complete segment 缺 timestamp min/max 会失败。 |
| `R7-05` | CONSISTENT | runner freshness、动态 slot adoption 与 Solana producer envelope 测试 PASS，supply producer 可被 controlled runner 执行。 |
| `R8-01` | CONSISTENT | scan 产出 current observation bundle/snapshot envelope，runner/consumer 单测 PASS。 |
| `R7-07` | CONSISTENT | immutable capability matrix 测试 PASS，formal readiness 由能力事实派生。 |
| `R8-02` | CONSISTENT | Robinhood 为 exploration 且防回流测试 PASS；eth/bsc/base/sol 四链 readiness 由代码自然导出。 |
| `R8-06` | CONSISTENT | READY 无条件要求 reconciliation wrapper/四回执的代码与负例均在，相关测试 PASS。 |
| `six-F-01` | CONSISTENT | entity provenance 与 handoff strict-freeze 测试 PASS，formal 缺 labels 会拒绝。 |
| `R7-09` | CONSISTENT | R7/identity 测试 PASS，空或未知 kind labels 无法进入 formal。 |
| `six-F-09` | CONSISTENT | add-labels 三闸和回滚测试 PASS，validate/benchmark/manifest 均为事务前置。 |
| `R7-10` | CONSISTENT | staging/重名/竞态失败回滚反例 PASS。 |
| `six-F-10` | CONSISTENT | round-trip 与 risk-flags 回归 PASS，risk_flags 漂移/日期倒退均阻断。 |
| `R7-11` | CONSISTENT | R7 回归 PASS，`verified_at` 倒退仍非零退出。 |
| `R7-14` | CONSISTENT | canonical risk_flags parser 被 add/validate/resolver/build 共用，零宽/非字符串负例 PASS。 |
| `R8-10` | CONSISTENT | B1/B2 risk_flags 加固测试 PASS，原 validator/resolver 语义分裂已闭合。 |
| `full-F-03` | INCONSISTENT | 主表称“路径外豁免保持、影响与自动失效条件已登记”，但详情仍称需证明/批准，且现有 RH 台账明确要求另建非 RH 影响台账；仓库没有该台账。 |
| `R8-05` | CONSISTENT | `invariant_scan.py` 与注入守卫 PASS；ledger 的 51/55/60/38/58 是批三历史点，当前计数已增至 52/55/62/42/58，未跌破。 |
| `full-F-04` | CONSISTENT | 当前文档写 16 个普通文件/15 个 Python，磁盘独立计数同为 16/15，动态漂移守卫 PASS。 |
| `six-F-11` | CONSISTENT | docs lint 与 six-lens docs 测试 PASS，7.5KB 预警/8192B 硬闸口径一致。 |
| `R7-15` | CONSISTENT | labels 维护文档、round-trip、add-labels 三闸测试均 PASS。 |
| `six-F-12` | CONSISTENT | casebook/archive 现役路由由 docs lint 与 six-lens docs 测试守住。 |
| `R9-01` | UNVERIFIABLE | observation protocol、三消费者和大量负例均 PASS；但 detail 依赖的裁判 mainnet `diff=0` 不能在本次禁网环境独立重放。 |
| `R9-02` | CONSISTENT | 真子进程 producer→consumer 边界测试、anchor-plan v2 与 time 20 项测试 PASS；弱覆盖下限双端存在。 |
| `R9-03` | CONSISTENT | 真子进程边界与 fetch fail-closed 测试 PASS；入口传播退出码，pool 先隔离旧件并产 ERROR side receipt。 |
| `R9-04` | CONSISTENT | 真子进程边界与 Solana producer 测试 PASS；marker-first 隔离、ERROR receipt、bundle+snapshot 原子提交存在。 |
| `R9-05` | UNVERIFIABLE | target/callsite 注册、六探针及四链 ready 均可静态/单测确认；但两份真实 loopback E2E 本地均 `EPERM`，裁判 mainnet smoke 也不能禁网重放。 |

## INCONSISTENT 详情

### 49 项内：`full-F-03`

矛盾不是 Multicall 缺陷是否仍存在——详情与 `CMD-MC` 都承认它仍存在；矛盾在“处置已闭合”的声称：

1. 主表最终结果写“正式发布路径外豁免保持；影响与自动失效条件已登记”。
2. 同 ID 详情却写“需调用图、能力矩阵与防回流负测后由 Fable 批准”。
3. `maintenance/repair-20260806/robinhood-impact.md:114` 明确写 `full-F-03` 是通用 Multicall 工具，若走第四类豁免应另建非 Robinhood 影响台账，不得混入 RH 台账。
4. 仓库内对 `full-F-03` 的全文检索只落到 ledger、invariant merge 和上述“应另建”说明，没有独立豁免台账、Fable 批准或自动失效负测闭环。
5. `multicall_balances.py` 仍是从 formal EVM choices 派生的现役 attested 工具；“已证明发布路径外”也不能由 RH exploration 证据替代。

因此该项处置结果与当前仓库证据矛盾，判 `INCONSISTENT`。

### 整体验收台账：`final_acceptance.md` 第 3 节

这不是额外第 50 项，不计入 49 项 verdict 分母，但其现状声称不一致：

- 声称工具 `scratchpad/sha_replay.py` 当前不存在，无法按原命令复跑。
- 当前“分组 → commit SHA 对照”表实算为 **67 行、71 个 SHA 提及、41 个唯一 SHA**；不是声称的 62 行、37 个唯一 SHA。41 个唯一 SHA 均存在且都是 HEAD 祖先。
- `git diff --name-only 63cf715..HEAD` 当前为 **83 个文件**；不是声称的 82 个。新增差额至少包含已经进入当前 HEAD 的验收台账自身，因此原快照口径没有随 HEAD 更新。
- 49 主表/49 详情、详情三字段完整这一部分可独立复现并成立。

结论：第 3 节的 A/D 数量与工具可复跑性不符合当前仓库；B/C 成立。

## UNVERIFIABLE 详情

### `full-F-01` / `six-F-03` / `R7-01`

三项共享的关键声称是“手写/预置四回执不能替代真实 producer 执行，且四链真实纵切片已通过”。本次已确认：

- `reconciliation_report.py` 会拒绝 pre-existing receipt，逐个 `subprocess.run` 白名单 producer，并在 wrapper 前复验 receipt/target/verdict；
- `test_reconciliation_runner.py::test_01_preexisting_receipt_rejected` 随 SUITE PASS；
- EVM/Solana 纵切片文件存在、均在 SUITE，测试源码确实创建 loopback server 并运行生产 CLI。

但两个真实纵切片都在 `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 的 `socket.bind` 处被 `PermissionError: [Errno 1] Operation not permitted` 阻断，尚未进入生产业务断言。缺少允许 loopback bind 的离线执行环境，故三项不判业务失败，但也不能判完整 `CONSISTENT`。

### `R9-01`

本地可证部分：observation bundle 以 RPC `context.slot` 为真值；声明 slot 只作相等断言；mainnet genesis、前后 raw、GPA、supply 三方闭合与三消费者绑定代码均存在；`test_r9_batch3_solana_observation.py`、dynamic runner、release guards、Solana producers 全部 PASS。

不可证部分：详情把实际数据正确性落到“裁判 mainnet diff=0”。本任务禁网，不能重新访问 mainnet 或独立重放该实证；仓库内 JSON 只能证明有归档产物，不能单独证明其外部执行来源。因此判 `UNVERIFIABLE`，缺少可联网的裁判重放环境/原始响应重放包。

### `R9-05`

本地可证部分：`formal_ready_chains()` 当前确为 `{eth,bsc,base,sol}`；callsite/target、六探针、SQD scope、endpoint 脱敏与相关单测均通过。

不可证部分：EVM/Solana 两份真实纵切片均被 loopback `EPERM` 阻断，裁判 mainnet smoke 也因禁网不能重放。ledger 第七节仍保留旧的 `B3F_BLOCKED（环境验真未闭）` 段，而 R9-05 详情称裁判已经完成；在没有可复跑日志/允许环境时，本次不能独立消除这项执行证据不确定性。

### `final_acceptance.md` 第 1 节（整体，不计 49 分母）

当前本地复跑是 87 PASS + 2 loopback `EPERM`，与任务书预告一致；因此不能复现“Fable 环境 89/89 PASS”，但也没有观察到业务断言失败。缺少允许 loopback bind 的环境。

## 跑过的命令与结果

以下均在仓库根执行；Python 测试统一带 `PYTHONDONTWRITEBYTECODE=1`。

| 命令/动作 | 结果 |
|---|---|
| `git branch --show-current` | `fix/r9-closure-20260807` |
| `git rev-parse HEAD` | `45bf8f31fde258af833697510bb3aadc51e3f88a` |
| `git status --short --branch`（前/后） | 前：仅既有 `?? r9-reviews/`；测试后：另有本任务允许的 `?? blind-reviews/`，无 tracked 修改。 |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py` | rc=1；89 项中 87 PASS；仅 `test_batch3_solana_vertical_slice.py`、`test_batch3_evm_vertical_slice.py` 在 loopback `socket.bind` 处 `EPERM`。 |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py` | rc=0；`receipt_producers=52, receipt_consumers=55, transport_calls=62, atomic_writes=42, formal_entrypoints=58, exceptions=0`。 |
| ledger 结构只读解析 | 主表 49/49 unique；详情 49/49 unique；双向 ID 差集均空；49 个详情三字段齐全。 |
| `run_all.py` SUITE 只读解析 | 89 项、89 unique；ledger 明确点名的 17 个测试/守卫文件均存在且在 SUITE。 |
| `rg` 场景 ID → `diff-finding-map.md` / `transport-injections.json` / `scripts/tests/` | B1/B2/B3/B4/R9 场景均可落到具体测试文件/函数；共享文件只跑一次，结果引用到各 owner ID。 |
| `PYTHONDONTWRITEBYTECODE=1 python3 -c ... formal_ready_chains()` | `{'bsc', 'sol', 'eth', 'base'}`。 |
| Robinhood 文件只读计数（`Path.iterdir()`，非 `find`） | 16 个普通文件，其中 15 个 `.py`；与当前文档一致。 |
| SHA 对照表只读解析 + `git cat-file -e` + `git merge-base --is-ancestor` | 67 行、71 次 SHA 提及、41 unique；missing=0，non-ancestor=0。 |
| `git diff --name-only 63cf715..HEAD` | 83 个变更文件。 |
| `rg/sed` 抽读生产结构 | 已核对 runner freshness、READY reconciliation、txn 联合提交、错误 side receipt、attested RPC、anchor final-block、能力矩阵、risk_flags 单 parser、R9 observation/slot/supply 与入口退出码。 |

`final_acceptance.md` 第 2 节结论可复现并一致；第 1 节受 loopback 环境限制；第 3 节存在上述数量/工具矛盾。

## 最终摘要

CONSISTENT/INCONSISTENT/UNVERIFIABLE：43 / 1 / 5（分母 49）。
需要维护方回应的事项：补齐或撤销 `full-F-03` 的第四类豁免声称；修正/重跑 `final_acceptance.md` 第 3 节（当前 67/41/83 且工具缺失）；提供允许 loopback bind 的 2 个纵切片复跑证据及 R9 mainnet 可复核证据。
报告路径：`blind-reviews/r9/45bf8f3/round-b-ledger-replay.md`
