# 批 1b 施工报告（STOPPED：白名单内无法闭合全量 suite）

## 结论

本次按更正后的工单续跑，登记面、四份 errata 草案小修、`scan-schemas` 文档登记和 35 项先红均已落盘；35 项结果为 **35 RED**，另按 E19 单列第 (2) 项顺序敏感事实 **1 GREEN**。四个新测试都以 exit 1 明确先红，无 skip/xfail/静默通过。

批 1b **未达到可交付完成状态，现按 fail-closed 停工**。当前树的 `run_all.py` 有 4 项失败：工单预期的 `invariant_scan.py`、两个沙箱回环监听 `EPERM`，以及一个由本批新增 formal producer 登记直接触发的 `test_batch4_invariant_guards.py` 回归。最后一项不能在本批白名单内诚实修复，详见“阻塞项”。

基线保持：分支 `fix/sqd-gap-v6520`，HEAD `132b20b8c3c385423c30abddd67266e78bef0cbd`，`VERSION=6.51.0`。未 commit、未切分支、未联网。

## 阻塞项

工单要求在 `scripts/tests/invariant_scan.py:81-87` 的 `FORMAL_E2E_REQUIRED_PRODUCERS["sol"]` 增加：

- `scripts/solana/sqd_coverage_probe.py`
- `scripts/solana/replay_edges.py`

该登记会使 `formal_e2e_provenance_errors()` 对现役 Solana 纵切片返回：

```text
formal E2E target lacks registered producer execution for sol: ['scripts/solana/replay_edges.py', 'scripts/solana/sqd_coverage_probe.py']
```

`scripts/tests/test_batch4_invariant_guards.py:198` 同时硬断言默认 `formal_e2e_provenance_errors() == []`，因此现役守卫必然失败。目标纵切片 `scripts/tests/test_batch3_solana_vertical_slice.py` 没有两项可达执行证据，而它不在本批白名单内；`run_all.py` 也明确禁止修改。

合规闭合需要工单方二选一：

1. 把 `scripts/tests/test_batch3_solana_vertical_slice.py` 加入白名单，并要求在注册的 formal target 可达路径真实执行 probe/replay；或
2. 明确修订本批 `run_all.py` 的预期，允许 `test_batch4_invariant_guards.py` 随登记面一同先红，并把其闭合批次写入工单。

没有采用按调用方条件化常量、伪造 producer 字符串或削弱守卫等规避方案。

## 改动清单（本次施工）

| 文件 | 当前行/范围 | 改动 |
|---|---:|---|
| `scripts/tests/invariant_scan.py` | 81-89、123-130 | Sol formal producer 增 probe/replay；failure artifact coverage 墁 replay/repair |
| `scripts/tests/invariant_manifest.json` | 13-19、186-310、564-581、793-799、1107-1117、1186-1187 | 五类登记只增；旧 schema 保留；minimum floor 按新增点数上调到 70/92/65/56/61 |
| `scripts/tests/contract_manifest.json` | 161-178 | 新增 CT-SQDGAP-01…18 required needles |
| `scripts/tests/contract_ids_snapshot.json` | 128-145 | 同步新增 18 个 ID |
| `references/scan-schemas.md` | 8、596-1241 | 更新本册路由；逐字段登记 §14 契约族、差异段和生产者/消费者 |
| `contracts_draft/solana-reconcile_v4.json` | 202-222、515-552 | E14 三 raw 字段进入主 fields，类型为 JSON int；继承类型和 invariant 同步 |
| `contracts_draft/reconciliation-report_v3.json` | 34-101 | E18 路径改为 `checks.exact_reconcile.*`，Solana 条件必填、EVM 必须省略 |
| `contracts_draft/canonicalization.json` | 93-101、125、130 | E17 增 rpc_ledger 节点、依赖、bundle 绑定及不进 gid 规则 |
| `contracts_draft/publish_protocol.json` | 16、90、94 | E17 step ① append-only、step ③ 前 fsync 定稿原话 |
| `contracts_draft/INDEX.json` | 14-17 | 记录 E14/E17/E18 小修 |
| `scripts/tests/test_sqd_coverage_probe.py` | 1-134 | (3)(20)(21)(28)(30) 烟雾红＋oracle |
| `scripts/tests/test_sqd_gap_repair.py` | 1-209 | (2)(4)(5)(6)(7)(8)(10)(15)(16)(18)(25)(26)(27)(29a-c)；(2) 含现役顺序敏感 GREEN 事实 |
| `scripts/tests/test_reconcile_v4_receipt.py` | 1-252 | (9)(11)(12)(13)(17)(23)(31)(32)(33) |
| `scripts/tests/test_recon_fifth_check.py` | 1-147 | (1)(14)(19)(22)(24)；直接调用现役 handoff generate/verify core |
| `batch1b_red_evidence.txt` | 1-527 | 四件逐项全量输出、35 RED 汇总行、1 GREEN 事实、两次 run_all 全量输出 |
| `batch1b_done.md` | 本文件 | 正式停工报告 |

上表中的 `contracts_draft/*` 均位于 `maintenance/repair-20260823-sqd-gap/contracts_draft/`。

## 登记面增项

| 登记面 | 增项 |
|---|---|
| receipt producers | wave v5、flow v3、replay v4、coverage/pointer、repair cache/resolution/bundle/pointer |
| receipt consumers | `sqd_cache_identity` 增 repair bundle/pointer；计划中的 `solana_exact_validate` 增 coverage/repair/exact 八协议 |
| transport calls | probe、repair 各登记 `net.py` |
| atomic writes | probe、repair 各登记 `main / multi_file_txn` |
| formal entrypoints | replay、probe、repair |
| formal E2E required producers | Solana 增 probe、replay |
| failure artifact coverage | replay、repair |
| contract needles | CT-SQDGAP-01…18；authority 均为 `references/scan-schemas.md`；snapshot 集合同步 |

`minimum_counts` 以基线 floor 加本批新增点数同步为：receipt producers 70、receipt consumers 92、transport 65、atomic 56、formal entrypoints 61。

## 35 项映射实况

| 测试文件 | 项号 | 类型/现役证据 |
|---|---|---|
| `test_sqd_coverage_probe.py` | 3, 20, 21, 28, 30 | 目标模块缺失显式 EXPECTED_RED；纯 fixture/oracle 覆盖 sample 冒充、slot_counts、getBlocks 合取式、位图、CAS/幂等/fsync |
| `test_sqd_gap_repair.py` | 2, 4, 5, 6, 7, 8, 10, 15, 16, 18, 25, 26, 27, 29a, 29b, 29c | (2) 直跑现役 curve 与 entity 顺序模拟，先输出 GREEN 事实，再因缺 slot_index_map 机制 RED；其余烟雾＋oracle |
| `test_reconcile_v4_receipt.py` | 9, 11, 12, 13, 17, 23, 31, 32, 33 | 六入口案外 base、upper/snapshot、meta 回写、case-root/symlink、coverage pointer 漂移、raw string 均取现役行为；11/32 附 generic validator 观察和目标 oracle |
| `test_recon_fifth_check.py` | 1, 14, 19, 22, 24 | 现役 handoff generate/verify core 与 audit release checker 语义反例；旧 wave/flow、stale binding、gate_pass=false 均被接受 |

红证在 `batch1b_red_evidence.txt:1-81`：35 条 `RED`，第 (2) 项事实 `GREEN 2-fact` 一条；四件均 `[exit_code=1]`。

## 四份草案 errata 小修对照

| Errata | 草案 | 落地 |
|---|---|---|
| E14 | `solana-reconcile_v4.json` | `minted_raw`、`burned_raw`、`snapshot_supply_raw` 入主 fields；`type="JSON int"`；字符串整数拒收；inherited 标注 v3 string→v4 int |
| E17 | `canonicalization.json` | 依赖图新增 rpc_ledger；bundle 绑定定稿台账；台账不进 gid；header 保持 plan_digest 语义 |
| E17 | `publish_protocol.json` | step_1 增“rpc_ledger 自 step ① 起 append-only 写入，step ③ 前 fsync 定稿” |
| E18 | `reconciliation-report_v3.json` | 五字段改为 `checks.exact_reconcile.*`；`family==solana` 必填；`family==evm` 必须省略 |

`INDEX.json` 已记录三项修订；除此四份草案外未改其他草案。

## 验证结果

- 四个新测试：均 exit 1；汇总 35 RED + 1 GREEN(2-fact)。
- `python3 scripts/tests/docs_lint.py --all`：PASS，59 个文档。
- 四个新测试 `py_compile`：PASS。
- 全部 JSON 草案、manifest：解析 PASS。
- contract manifest/snapshot：175/175，集合相等、snapshot 已排序、ID 唯一。
- `git diff --check`：PASS。
- `python3 scripts/tests/run_all.py` 当前树复跑：exit 1，4 项失败；全量输出见红证 306-527。

### run_all 红项解释

1. `invariant_scan.py`：**工单预期红**。登记了尚不存在的 probe/repair/validator 和尚未升版的 producer/consumer，因此 20 discrepancies。
2. `test_batch3_solana_vertical_slice.py`：环境 `PermissionError: [Errno 1] Operation not permitted`，沙箱禁止 `127.0.0.1` 监听。
3. `test_batch3_evm_vertical_slice.py`：同一回环监听 `EPERM`，不是本批代码回归。
4. `test_batch4_invariant_guards.py`：**本批登记触发的真实回归/当前停工原因**；详见“阻塞项”。

第一次 run_all 后发现 invariant manifest 的旧 wave/flow schema 必须按“只增不删”保留，修正后又对当前树完整复跑一次；两次全量输出均保留在红证，未覆盖历史证据。

## 发现项

1. 工单同时要求新增 Solana formal E2E producers、又要求除 invariant 外 suite 全绿，但现役 `test_batch4_invariant_guards.py:198` 明确要求默认 formal E2E 零错；而真实 Solana vertical slice 未执行这两个 producer。三者在当前白名单下不可同时满足。
2. 当前执行沙箱禁止回环端口监听，导致两个既有 vertical slice 产生 EPERM；第四个新测试已使用纯离线现役核心调用，未把缺端口伪装成语义红。
3. 工单目标段仍写“31 项先红”，E19 和映射实况为 35 项；本次以 E19 权威完成 35 项。

## 未做

- 未修改任何生产脚本。
- 未修改 `PLAN.md`、`PLAN_errata_batch0.md`、`scripts/tests/run_all.py`、其他 reference、其他 contract draft。
- 未新增 banned needles。
- 未 commit、未切分支、未联网。
- 未越权修改 `test_batch3_solana_vertical_slice.py` 或 `test_batch4_invariant_guards.py`，因此批 1b 未宣称完成。

## 批 6 必做硬闸

**批 6 必做：banned needles 4 组与文档修订同 commit。** 本批不加 banned needles；原因是 `docs_lint` 经 pre-commit 调用 `validate_contract_manifest`，文档中的旧句尚未同批修订时会阻断提交。

## 白名单自述

本次施工写入仅限工单白名单：两份 invariant 登记、两份 contract 登记、`references/scan-schemas.md`、四个新测试、四份 errata 草案及 `INDEX.json`、红证和本报告。工作区另有用户在复工前已存在的 `batch1b_workorder.md` 修改、`batch1b_done_attempt1_stopped.md`、`batch2_workorder.md`，均未由本次施工创建或改写。
