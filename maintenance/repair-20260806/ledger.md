# R9 修复闭环主账（49 项）

- R8 准备基线：`6e943486a9e4a6f2b673c7cd7a03093f463da233`（`main@6e94348`）。
- 当前冻结基线：`63cf715cb6d11f6669f4370c77574930da655891`（`main@63cf715`，v6.36.0）。
- 主账分母：49（full 4 + six-lens 13 + R7 15 + R8 12 + R9 5）。
- supplementary：`full-C-01`～`full-C-08` 不计分母，见文末附表。
- 归因纪律：第一次 full review 没有给 F-01～F-04 判“新引入/半修残留/历史漏检”，本账写“报告未判定”，不自行补造；其余照抄各报告。
- 覆盖分类初判已由 Fable 复核冻结（2026-08-06）。四类：①已被新反例覆盖；②由纵切片覆盖；③需补独立反例；④正式发布路径外豁免。
- **Fable 冻结注记（覆盖分类①的双重口径）**：对回放为 FIXED_ON_BASELINE 的项，①指"既有负向回归测试已覆盖原反例"（该测试历史上先红后绿，今在 suite 常驻），本轮验收动作=两轮盲审重放确认不回退；对本轮施工项，①指"本轮新增反例基线红、候选绿"。②③④口径照 PLAN 原文。
- **Fable 读码复核样本（2026-08-06）**：CMD-FORGE（validate_reconciliation_check 为纯语义验证、无执行证明，shared_release_receipt.py:93-149 亲读确认，另确认 Solana supply 分支 envelope 校验与旧 schema 要求互相矛盾＝R8-01 深层证据）；CMD-RH-CAP（chain_registry.py:44-49 formal=True 与 evm_chain_id=None 并存亲读确认）；CMD-R8-TARGET（time_spotcheck.py:140-153 无 eth_chainId、day_end_block 直接使用无上界校验亲读确认）。三样本全部坐实，回放台账采信。

## 一、基线回放命令索引

所有命令均在仓库根运行，设置 `PYTHONDONTWRITEBYTECODE=1`；所有 fixture、fake transport 和输出位于 `tempfile`/系统临时目录，没有真实 RPC/API。

| 命令 ID | 实际命令/动作 | 关键输出 |
|---|---|---|
| `CMD-R7` | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r7_findings.py` | `PASS R7 regression suite: 15/15 observed green; EXPECTED_RED=0`。该结果只证明点名入口；同族残留另用下列 fake 重放。 |
| `CMD-RECEIPT` | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_sixlens_receipts.py` | recon supply mismatch/balance mismatch `exit=2`；RPC error `exit=1`；anchor fetch/no-converge 走 ERROR side receipt；最终 `PASS: 六视角批①结构化回执与 fail-closed`。 |
| `CMD-FETCH` | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_fetch_failclosed.py` | 空/反向/负区间均 argparse 拒绝；`PASS: HyperSync 采集器失败与游标异常均 fail-closed`。 |
| `CMD-GMGN` | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_fetch_gmgn_sh.py` | `PASS: GMGN 临时文件、JSON 校验和失败聚合生效`。 |
| `CMD-LABEL-TXN` | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_add_labels_rollback.py` | validate/benchmark/manifest/归档 staging/竞态失败均回滚；`PASS: add_labels validate/benchmark/manifest 三闸与失败回滚`。 |
| `CMD-ROUNDTRIP` | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_roundtrip_check.py` | `PASS: round-trip 缺表与行内退化均 fail-closed`。 |
| `CMD-DOC` | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_sixlens_docs.py` | `PASS: 六视角批⑤大小口径与 archive 路由`。 |
| `CMD-ENTITY` | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_entity_source_trace.py` | `正式 provenance 缺 --labels-file exit 2`；`显式无标签探索模式落 exploration 标记`；29 个场景 0 失败。 |
| `CMD-HANDOFF` | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_handoff_manifest.py` | READY 缺 chain/contract/未知链均拒；但 BSC 正例只自动 gate 三个且缺 reconciliation 仍 generate/verify 成功。 |
| `CMD-FORGE` | Python tempfile harness：`from test_audit_release_gate import build_case; build_case(case); shared_release_receipt.validate_sources(case)`；没有运行四个 producer | `FABRICATED_FIXTURE_ACCEPTED_TARGET {'chain':'bsc','token':'0xtoken','as_of_block':123}`；wrapper 只需填写当前 `reconciliation_report.py` SHA。 |
| `CMD-RH` | tempfile 写 1 条 HS gzip（block 100, ts int）、1 条 RPC 行（block 300）、锚点 100→1000/200→2000；执行 `python3 scripts/robinhood/merge_hs_rpc.py --input ... --rpc ... --anchors ... --output ...` | `rc=0`；`ts_values=[1000,'1970-01-01T00:33:20Z']`；`ts_types=['int','str']`；越界 300 被钳到末锚点。 |
| `CMD-MC` | Python fake `requests/decode_aggregate3` 调 `multicall_balances.query()`，再 fake 全失败调 `main()` | raw `1000000` 被输出 `1e-12`（6 decimals 正确人类值应为 1）；全失败仍 `main_return=None`、正式 JSON 含 `null` 并打印 `[done]`。 |
| `CMD-R8-TARGET` | fake `RpcPool` 执行 `time_spotcheck.py`：plan `day_end_block=11`，CLI `--final-block 10`，返回余额 100 | `rc=0`；RPC 方法只有 `eth_call`，查询 tag `0xb`；receipt target=10、row block=11。 |
| `CMD-R8-ALIAS` | fake 成功 transport，分别令 anchor/window 的 data 路径与 receipt 路径相同 | 两者均 `rc=0`；最终文件 schema 分别为 `solana-anchor-sampler-receipt/v2`、`solana-window-fetch-receipt/v2`，原数据已被 receipt 覆盖。 |
| `CMD-R8-FLAGS` | 临时 ETH labels CSV：`tier=exclude,risk_flags=" tornado-user"`；调用 `validate_file` 与 `LabelResolver.risk_partition` | validator `errors=[]`；resolver 激活 `privacy=['tornado-user']`。 |
| `CMD-RH-CAP` | 对 accounting/verify_recon/supply_truth/time_spotcheck 执行最小 `--chain robinhood` CLI | 四个脚本均在业务调用前 argparse `exit=2`，而 registry 仍 `formal=True`。 |

## 二、49 项主表（按 primary INV 行族排列）

| canonical ID | 报告基线 | 严重度 | 原归因 | primary | secondary | 当前生产路径与同族面（6e94348） | 覆盖初判 | 测试/纵切片/豁免证据 | 基线回放 | 最终结果 | 两轮盲审 / Fable |
|---|---|---:|---|---|---|---|---|---|---|---|---|
| `full-F-01` | full@`b0b7744` | P0 | 报告未判定 | INV-01 | INV-10, INV-12 | `shared_release_receipt.py:93-149,173-209`; `reconciliation_report.py:143-229`; `handoff_manifest.py:68-89,218-249` | ② | `B3-RUNNER-FRESH-01`; `B3-EVM-E2E-ETH/BSC/BASE`; `B3-SOL-E2E` | REPRODUCED (`CMD-FORGE`) |  |  |
| `six-F-03` | six@`fca61ad` | P0 | 历史漏检 | INV-01 | INV-02, INV-10 | 同上 | ② | `B3-RUNNER-FRESH-01`; 四链真实 controlled runner 纵切片 | REPRODUCED (`CMD-FORGE`) |  |  |
| `R7-01` | R7@`d8bd3c5` | P0 | 新引入 | INV-01 | INV-10 | 同上；点名 test 只拒无/错 runner binding | ② | `B3-RUNNER-FRESH-01`; 未运行 producer/预置 receipt 不得通过 runner | REPRODUCED (`CMD-FORGE`; `CMD-R7` 点名绿不构成执行证明) |  |  |
| `full-F-02` | full@`b0b7744` | P1 | 报告未判定 | INV-02 | INV-06, INV-16, INV-20 | `pull_transfers_rpc.py:13-62`; `pull_block_ts_anchors.py:5-24`; `merge_hs_rpc.py:47-104` | ④ | 待 Fable 批准；见 `robinhood-impact.md` | REPRODUCED (`CMD-RH`) |  |  |
| `R7-03` | R7@`d8bd3c5` | P0 | 半修残留 | INV-02 | INV-05, INV-06 | `anchor_sampler.py:137-179,245-275`; sibling alias in `CMD-R8-ALIAS` | ③ | `B3-SOL-PROD-03`; `B3-SOL-E2E` | REPRODUCED（原 resume 反例被拒；同族 data/receipt alias 仍击穿） |  |  |
| `R7-04` | R7@`d8bd3c5` | P0 | 半修残留 | INV-02 | INV-06, INV-08 | `supply_truth_gate.py:103-175`; `shared_release_receipt.py:151-161` | ① | `test_supply_truth_gate.py`; `test_r7_findings.py::R7-04`; shared-release 语义回归 | FIXED_ON_BASELINE (`CMD-R7`: formal raw override 拒、file_ref/context slot 在场) |  |  |
| `six-F-02` | six@`fca61ad` | P0 | 历史漏检 | INV-03 | INV-07 | `verify_recon.py:58-144` | ① | `test_sixlens_receipts.py`; `B1-RPC-CALLSITE-recon` | FIXED_ON_BASELINE (`CMD-RECEIPT`: mismatch=2, RPC error=1) |  |  |
| `six-F-04` | six@`fca61ad` | P0 | 历史漏检 | INV-03 | INV-09 | `anchor_sampler.py:196-279` | ① | `test_sixlens_receipts.py::test_anchor_sampler`; `B3F-TXN-02` | FIXED_ON_BASELINE (`CMD-RECEIPT`: fetch/no-converge 非零且无 canonical PASS) |  |  |
| `R7-08` | R7@`d8bd3c5` | P1 | 历史漏检 | INV-03 | INV-12 | `handoff_manifest.py:228-249,421-447` | ② | `B2-REC-01`; `B3-EVM-E2E-ETH/BSC/BASE`; `B3-SOL-E2E` | REPRODUCED（declared PASS/2 已修；同族 reconciliation gate 可整项省略，`CMD-HANDOFF`） |  |  |
| `six-F-05` | six@`fca61ad` | P0 | 历史漏检 | INV-04 | INV-03, INV-06 | `window_fetch.py:127-231` | ① | `test_sixlens_receipts.py::test_window_fetch`; `test_r7_findings.py::R7-06`; `B3F-TS-01` | FIXED_ON_BASELINE (`CMD-RECEIPT`: gap 只留 partial/stale，exit=2) |  |  |
| `six-F-07` | six@`fca61ad` | P1 | 半修残留 | INV-04 | INV-03 | `fetch_pool_swaps.py:46-114` | ① | `test_fetch_failclosed.py` 分页/旧产物保护反例 | FIXED_ON_BASELINE (`CMD-FETCH`: 分页失败不提交正式 CSV) |  |  |
| `six-F-08` | six@`fca61ad` | P1 | 新引入 | INV-04 | INV-03 | `fetch_gmgn.sh:18-49` | ① | `test_fetch_gmgn_sh.py` 临时文件/JSON/失败聚合回归 | FIXED_ON_BASELINE (`CMD-GMGN`: success→failure 旧文件转 `.stale`) |  |  |
| `R8-04` | R8@`6e94348` | P1 | 新引入 | INV-05 | INV-04 | `receipt_kernel.py:192-220,268-273`; `anchor_sampler.py`; `window_fetch.py` | ③ | kernel 路径反例；R9 B3 producer 迁移；提交后独立自检反例 | N/A-R8基线即当前 | 批三代码侧闭合：两 producer 以 `publish_txn` 作最后可失败的 data+receipt 操作 |  |
| `R8-12` | R8@`6e94348` | P1 | 半修残留 | INV-05 | INV-02, INV-04 | `anchor_sampler.py:143-150,245-275`; `window_fetch.py:127-215` | ③ | `B1-RK-01`～`B1-RK-06`; `B3-SOL-PROD-03`; R9 B3 提交后无独立自检 | N/A-R8基线即当前 | 批三代码侧销账；Solana E2E 本沙箱受 loopback bind 限制待裁判复跑 |  |
| `six-F-06` | six@`fca61ad` | P0 | 半修残留 | INV-06 | INV-03 | `fetch_pool_swaps.py:46-58` | ① | `test_fetch_failclosed.py` 相等/反向/负区间 transport 前拒绝 | FIXED_ON_BASELINE (`CMD-FETCH`: 相等/反向/负区间开文件前拒) |  |  |
| `R7-06` | R7@`d8bd3c5` | P1 | 半修残留 | INV-06 | INV-05, INV-10 | `window_fetch.py:127-215` | ③ | `B3-SOL-PROD-02/03`; `B3-SOL-E2E` | REPRODUCED（原反向窗已修；同族 data/receipt alias 仍 PASS，`CMD-R8-ALIAS`） |  |  |
| `R8-08` | R8@`6e94348` | P1 | 半修残留 | INV-06 | INV-08 | `time_spotcheck.py:119-153,162-180` | ② | `B3-TIME-01/02`; `B3-EVM-E2E-ETH/BSC/BASE` | N/A-R8基线即当前 |  |  |
| `R7-12` | R7@`d8bd3c5` | P1 | 新引入 | INV-07 | INV-11 | `verify_recon.py:49-54,114-119`; sibling `time_spotcheck.py:140-153` | ② | `B1-RPC-01`～`B1-RPC-06`; `B3-EVM-E2E/Wrong-ETH/BSC/BASE` | REPRODUCED（verify_recon 原入口已修；time sibling 无 `eth_chainId`，`CMD-R8-TARGET`） |  |  |
| `R8-07` | R8@`6e94348` | P1 | 半修残留 | INV-07 | INV-08 | `time_spotcheck.py:140-153` | ② | `B1-RPC-CALLSITE-time`; `B3-EVM-WRONG-ETH/BSC/BASE` 业务 RPC=0 | N/A-R8基线即当前 |  |  |
| `R8-09` | R8@`6e94348` | P1 | 历史漏检 | INV-07 | INV-02 | `supply_truth_gate.py:84-98` | ② | `B1-RPC-CALLSITE-supply`; `B3-EVM-E2E-ETH/BSC/BASE` totalSupply 复验 | N/A-R8基线即当前 |  |  |
| `six-F-13` | six@`fca61ad` | P1 | 历史漏检 | INV-08 | INV-12 | `handoff_manifest.py:164-180,212-222,396-419,966-1010` | ① | `test_handoff_manifest.py` 65 项；`B2F-LG-01`～`05` legacy 补闸 | FIXED_ON_BASELINE (`CMD-HANDOFF`: READY 缺 chain/contract/未知链均拒) |  |  |
| `R7-13` | R7@`d8bd3c5` | P1 | 新引入 | INV-08 | INV-06 | `time_spotcheck.py:119-153`; `anchor_plan.py` target producer | ② | `B3-TIME-01/02`; plan↔CLI final-block 精确绑定 | REPRODUCED（plan chain/token/file_ref 已修；final-block 未绑定且查询 cutoff+1，`CMD-R8-TARGET`） |  |  |
| `R8-03` | R8@`6e94348` | P0 | 历史漏检 | INV-08 | INV-10 | `accounting_gate_sol.py:101-124`; `shared_release_receipt.py:173-190` | ② | `B3-SOL-PROD-01/05/06`; `B3-SOL-E2E` slot=77 单源 | N/A-R8基线即当前 |  |  |
| `R7-02` | R7@`d8bd3c5` | P0 | 半修残留 | INV-09 | INV-03 | `net.py` Result/curl backend；`anchor_sampler.py:208-223` | ① | `test_net_result.py`; `test_r7_findings.py::R7-02`; `test_sixlens_receipts.py` | FIXED_ON_BASELINE (`CMD-R7`/`CMD-RECEIPT`: curl rc=7 空 stdout → ERROR/nonzero) |  |  |
| `R8-11` | R8@`6e94348` | P1 | 历史漏检 | INV-09 | INV-06, INV-16 | `window_fetch.py:43-111,208-215` | ③ | `B3-SOL-PROD-02`; `B3-SOL-E2E` timestamp segment summary | N/A-R8基线即当前 |  |  |
| `R7-05` | R7@`d8bd3c5` | P1 | 新引入 | INV-10 | INV-01, INV-12 | `reconciliation_report.py:143-229`; `shared_release_receipt.py:25-37` | ② | `B3-SOL-PROD-04`; `B3-SOL-E2E` 真实 runner 执行 supply | REPRODUCED（wrapper producer 已有；Solana supply producer CLI/schema 无法被 runner 执行，见 R8-01 当前路径） |  |  |
| `R8-01` | R8@`6e94348` | P0 | 新引入 | INV-10 | INV-01, INV-08 | `scan_token_accounts.py:139-150,253-273`; `reconciliation_report.py:143-169`; `shared_release_receipt.py:93-106` | ② | `B3-SOL-PROD-04`; `B3-SOL-E2E` current envelope+consumer | N/A-R8基线即当前 |  |  |
| `R7-07` | R7@`d8bd3c5` | P1 | 新引入 | INV-11 | INV-20 | `chain_registry.py:6-49,128+`; `handoff_manifest.py:84,164-180`; mandatory CLIs | ② | `B2-CAP-01`～`B2-CAP-04`; `B3-EVM-E2E-ETH/BSC/BASE`; `B3-SOL-E2E` | REPRODUCED（Arbitrum 已正确降级；Robinhood formal=true 但四 CLI 全拒，`CMD-RH-CAP`） |  |  |
| `R8-02` | R8@`6e94348` | P0 | 半修残留 | INV-11 | INV-07, INV-20 | `chain_registry.py:44-49`; four mandatory CLI choices | ④ | `B2-RH-01`; `RH-EX-01/02`; `B3-EVM-E2E-*` + `B3-SOL-E2E` 证明仅四链 readiness 闭合 | N/A-R8基线即当前 |  |  |
| `R8-06` | R8@`6e94348` | P1 | 半修残留 | INV-12 | INV-01, INV-10 | `handoff_manifest.py:59-89,218-249,410-447` | ② | `B2-REC-01`; `B3-EVM-E2E-ETH/BSC/BASE`; `B3-SOL-E2E` READY 必经 recon | N/A-R8基线即当前 |  |  |
| `six-F-01` | six@`fca61ad` | P0 | 历史漏检 | INV-13 | INV-12, INV-20 | `entity_source_trace.py:206-222,653-679`; `handoff_manifest.py:606-728` | ① | `test_entity_source_trace.py`; `test_handoff_manifest.py` strict freeze | FIXED_ON_BASELINE (`CMD-ENTITY`: 正式缺 labels 拒；探索 freeze 拒) |  |  |
| `R7-09` | R7@`d8bd3c5` | P1 | 半修残留 | INV-13 | INV-15 | 同上，正式有效标签计数双端重算 | ① | `test_entity_source_trace.py`; `test_r7_findings.py::R7-09` | FIXED_ON_BASELINE (`CMD-R7`: 空/未知 kind labels formal 拒) |  |  |
| `six-F-09` | six@`fca61ad` | P0 | 半修残留 | INV-14 | INV-15 | `add_labels.py:118-223` | ① | `test_add_labels_rollback.py` validate/benchmark/manifest 三闸 | FIXED_ON_BASELINE (`CMD-LABEL-TXN`: validate+benchmark+manifest 强制) |  |  |
| `R7-10` | R7@`d8bd3c5` | P1 | 半修残留 | INV-14 | INV-18 | `add_labels.py:118-223`（archive staging 在三闸前、失败整体回滚） | ① | `test_add_labels_rollback.py`; `test_r7_findings.py::R7-10` | FIXED_ON_BASELINE (`CMD-LABEL-TXN`: staging/重名/竞态失败均回滚) |  |  |
| `six-F-10` | six@`fca61ad` | P1 | 半修残留 | INV-15 | INV-18 | `roundtrip_check.py:22-57,127-144`; `labels_resolver.py:315-326` | ① | `test_roundtrip_check.py`; `test_batch1_risk_flags.py` | FIXED_ON_BASELINE (`CMD-ROUNDTRIP`: risk_flags 漂移阻断；日期倒退由 R7 test 阻断) |  |  |
| `R7-11` | R7@`d8bd3c5` | P1 | 新引入 | INV-15 | INV-18 | `roundtrip_check.py:25-27,127-144` | ① | `test_roundtrip_check.py`; `test_r7_findings.py::R7-11` | FIXED_ON_BASELINE (`CMD-R7`: verified_at 倒退非零) |  |  |
| `R7-14` | R7@`d8bd3c5` | P2 | 新引入 | INV-15 | INV-18 | `roundtrip_check.py:50-57`; sibling add/validate/resolver | ③ | `B1-RF-01`～`B1-RF-03`；`B2-P3-RF-01/02` invisible 空白+非字符串 fail-closed；OB-2 merge 共用 | REPRODUCED（roundtrip 自身 trim/dedup 已修；validator/resolver 仍语义分裂，`CMD-R8-FLAGS`） |  |  |
| `R8-10` | R8@`6e94348` | P2 | 半修残留 | INV-15 | INV-14 | `add_labels.py:151-153`; `validate_labels.py:86-98`; `labels_resolver.py:318-326` | ③ | `B1-RF-01`～`B1-RF-03`；`B2-P3-RF-01/02`；`test_batch2_p3_hardening.py` | N/A-R8基线即当前 |  |  |
| `full-F-03` | full@`b0b7744` | P1 | 报告未判定 | INV-16 | INV-03, INV-07, INV-20 | `multicall_balances.py:31-35,57-83,85-115` | ④ | 待调用图与防回流证明、Fable 批准 | REPRODUCED (`CMD-MC`) |  |  |
| `R8-05` | R8@`6e94348` | P1 | 新引入 | INV-17 | INV-18 | `invariant_scan.py`; `invariant_manifest.json`; `formal_capability_probes.py` | ③ | `B4-INV17-01/02`; R9 B3 将五个 attested Solana callsite 纳入 census，四个纵切片 target 与 SUITE 双绑定 | N/A-R8基线即当前 | 批四既有销账保持；批三新增 census `51/55/60/38/58` 通过 |  |
| `full-F-04` | full@`b0b7744` | P3 | 报告未判定 | INV-18 | INV-17 | `data-pipeline-robinhood.md:16`; `scripts/robinhood/` | ③ | `B2-DOC-RH-COUNT`; `B4-RH-COUNT-01` 文档 16/15 与磁盘实数动态对表 | REPRODUCED（文档仍“全14件”，当前普通文件 16） |  |  |
| `six-F-11` | six@`fca61ad` | P2 | 半修残留 | INV-18 | — | `retrospective.md:68,91`; `docs_lint.py` 8192B 守卫 | ① | `docs_lint.py --all`; `test_sixlens_docs.py` | FIXED_ON_BASELINE (`CMD-DOC`: 7.5KB 预警/8192B 硬闸统一) |  |  |
| `R7-15` | R7@`d8bd3c5` | P2 | 半修残留 | INV-18 | INV-15 | `references/labels/MAINTENANCE.md`; `roundtrip_check.py:22-27`; `add_labels.py:180-223` | ① | `test_roundtrip_check.py`; `test_add_labels_rollback.py`; docs lint | FIXED_ON_BASELINE (`CMD-R7`: 七字段/三闸文档一致) |  |  |
| `six-F-12` | six@`fca61ad` | P2 | 历史漏检 | INV-19 | INV-18 | `casebook/README.md`; `retrospective.md:93-95`; docs archive guard | ① | `docs_lint.py --all`; `test_sixlens_docs.py` archive/runtime 路由 | FIXED_ON_BASELINE (`CMD-DOC`: casebook 执行路由不再回流 archive；A6 维护动作保留) |  |  |
| `R9-01` | R9@`63cf715` | P0 | 老问题修复不全 | INV-08 | INV-02, INV-11 | `solana_observation.py`; `scan_token_accounts.py`; `accounting_gate_sol.py`; `supply_truth_gate.py`; `shared_release_receipt.py` | ② | `R9-B3-SOL-OBS-01..09`; declared 77≠observed 103；同 bundle 三消费者；`B3-SOL-E2E` | REPRODUCED（旧实现 CLI 77/RPC 999 仍 PASS） | 批三闭合“声明当观测”的观测协议；不含 bundle 防伪，须由批四 producer/consumer 通用守卫保证测试关键输入由登记生产者现场生成 |  |
| `R9-02` | R9@`63cf715` | P1 | 修复中新引入 | INV-10 | INV-06, INV-08 | `anchor_plan.py`; `time_spotcheck.py`; EVM 正式纵切片 | ② | `B1-R9-02-PRODUCER-CONSUMER`; `test_batch3_evm_vertical_slice.py` 真实 producer | REPRODUCED（真实旧 producer 无 final_block，consumer rc=2） |  |  |
| `R9-03` | R9@`63cf715` | P1 | 老问题修复不全 | INV-03 | INV-04, INV-06 | `fetch_pool_swaps.py` 进程入口、tmp/canonical/stale | ① | `B1-R9-03-PROCESS/STALE`; `test_fetch_failclosed.py` | REPRODUCED（缺 next_block fatal，但 subprocess rc=0 且旧 CSV current） |  |  |
| `R9-04` | R9@`63cf715` | P1 | 老问题修复不全 | INV-03 | INV-01, INV-04, INV-10 | `scan_token_accounts.py` 四个 return 分支、snapshot/receipt marker 发布 | ① | `B1-R9-04-PROCESS/MARKER`; `test_batch3_solana_producers.py` | REPRODUCED（路径冲突 fatal，但 subprocess rc=0） |  |  |
| `R9-05` | R9@`63cf715` | P1 | 修复中新引入 | INV-11 | INV-02, INV-08 | Solana capability 声明、正式 JSON-RPC callsite、SQD scope 与纵切片 | ② | 批一 session；批二六探针/SQD adapter；批三 observation/accounting/SQD callsite + 四链真实 target | REPRODUCED（旧 formal-ready 无 getGenesisHash） | callsite 与 target 注册代码侧闭合；四链自然 ready；批内循环 1 消化 session CA/query secret，循环 2 消化 path secret 半修残留并统一持久化身份；两份 loopback E2E/裁判 mainnet 重跑后最终销账 |  |

## 三、逐项详情

以下小节补足主表中压缩的证据。每项“最终结果”和“两轮盲审/Fable”均故意留空，最终验收前不提前裁决。

### full-F-01

- 报告基线/严重度/归因：full@`b0b7744`；P0；报告未判定。
- primary/secondary：INV-01；INV-10、INV-12。
- 当前路径与同族面：`shared_release_receipt.py:93-149,173-209`；`reconciliation_report.py:143-229`；`handoff_manifest.py:68-89,218-249`。
- 覆盖初判：②由纵切片覆盖；施工证据：`B3-RUNNER-FRESH-01`；`B3-EVM-E2E-ETH/BSC/BASE`；`B3-SOL-E2E`。
- 基线回放：**REPRODUCED**。`CMD-FORGE` 未运行任何 reconciliation producer，仅由测试 fixture 手写四份 receipt 和 wrapper、填写当前 runner SHA，`validate_sources` 接受 target `{bsc,0xtoken,123}`。这不是 CHANGELOG/worklog 推断。
- 最终结果：
- 两轮盲审与 Fable 结论：

### full-F-02

- 报告基线/严重度/归因：full@`b0b7744`；P1；报告未判定。
- primary/secondary：INV-02；INV-06、INV-16、INV-20。
- 当前路径与同族面：`pull_transfers_rpc.py:13-62` 无 target/range receipt；`pull_block_ts_anchors.py:5-24` 硬编码且部分成功；`merge_hs_rpc.py:47-104` 无双侧 receipt，端点外推钳平并写 ISO 字符串。
- 覆盖初判：④正式发布路径外豁免；证据待 Fable 批准，影响台账见 `robinhood-impact.md`。
- 基线回放：**REPRODUCED**。`CMD-RH` 对 block 300 使用最大锚 block 200，命令 `rc=0`，输出混合 `int/str` 时间戳，且 RPC 行无 token 身份可核。
- 最终结果：
- 两轮盲审与 Fable 结论：

### full-F-03

- 报告基线/严重度/归因：full@`b0b7744`；P1；报告未判定。
- primary/secondary：INV-16；INV-03、INV-07、INV-20。
- 当前路径与同族面：`multicall_balances.py:31-35` 允许单 call 失败；`:57-83` 固定 `/1e18` 且失败转 `None`；`:85-115` 无 decimals/block/receipt，仍写正式 JSON 并 `[done]`。
- 覆盖初判：④正式发布路径外豁免；需调用图、能力矩阵与防回流负测后由 Fable 批准。
- 基线回放：**REPRODUCED**。`CMD-MC` 令 raw=1,000,000，输出 `1e-12`；令全批失败，`main_return=None`、JSON 含 `null` 且仍打印 `[done]`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### full-F-04

- 报告基线/严重度/归因：full@`b0b7744`；P3；报告未判定。
- primary/secondary：INV-18；INV-17。
- 当前路径与同族面：`references/data-pipeline-robinhood.md:16` 仍写“全 14 件”；`find scripts/robinhood -maxdepth 1 -type f` 实数 16。
- 覆盖初判：③需补独立反例；施工证据：`B2-DOC-RH-COUNT`；`B4-RH-COUNT-01` 对文档 16/15 与磁盘普通文件/Python 实数动态双向校验。
- 基线回放：**REPRODUCED**。命令 `find scripts/robinhood -maxdepth 1 -type f | wc -l` 得 16；文档声明 14。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-01

- 报告基线/严重度/归因：six@`fca61ad`；P0；历史漏检。
- primary/secondary：INV-13；INV-12、INV-20。
- 当前路径与同族面：`entity_source_trace.py:653-679` 正式 labels 必填且有效数非零；`handoff_manifest.py:606-728` freeze 重验。
- 覆盖初判：①已被新反例覆盖；施工证据：`test_entity_source_trace.py`；`test_handoff_manifest.py` strict freeze。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-ENTITY` 实跑“正式缺 labels exit 2；显式无标签仅 exploration”，freeze 侧另有拒收测试。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-02

- 报告基线/严重度/归因：six@`fca61ad`；P0；历史漏检。
- primary/secondary：INV-03；INV-07。
- 当前路径与同族面：`verify_recon.py:58-144` 参数化、chain attestation、结构化 receipt 和分级退出。
- 覆盖初判：①；施工证据：`test_sixlens_receipts.py`；`B1-RPC-CALLSITE-recon`。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-RECEIPT` 得 supply/balance mismatch `exit=2`，RPC error `exit=1`，闭合正例 `exit=0`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-03

- 报告基线/严重度/归因：six@`fca61ad`；P0；历史漏检。
- primary/secondary：INV-01；INV-02、INV-10。
- 当前路径与同族面：与 full-F-01 相同。
- 覆盖初判：②；施工证据：`B3-RUNNER-FRESH-01`；四链真实 controlled runner 纵切片。
- 基线回放：**REPRODUCED**。`CMD-FORGE` 证明未知/空 schema 已被堵，但“当前 producer 真实执行”仍可由手工自洽内容加当前 runner hash 冒充；关键输出为 `FABRICATED_FIXTURE_ACCEPTED_TARGET ...`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-04

- 报告基线/严重度/归因：six@`fca61ad`；P0；历史漏检。
- primary/secondary：INV-03；INV-09。
- 当前路径与同族面：`anchor_sampler.py:196-279`。
- 覆盖初判：①；施工证据：`test_sixlens_receipts.py::test_anchor_sampler`；`B3F-TXN-02`。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-RECEIPT` 对 fetch_fail/no_converge 均生成 ERROR side receipt 并非零退出；无 canonical PASS。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-05

- 报告基线/严重度/归因：six@`fca61ad`；P0；历史漏检。
- primary/secondary：INV-04；INV-03、INV-06。
- 当前路径与同族面：`window_fetch.py:127-231`。
- 覆盖初判：①；施工证据：`test_sixlens_receipts.py::test_window_fetch`；`test_r7_findings.py::R7-06`；`B3F-TS-01`。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-RECEIPT` 的 gap 运行输出 `.partial`、旧正式件转 stale、返回 2；成功才正式发布。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-06

- 报告基线/严重度/归因：six@`fca61ad`；P0；半修残留。
- primary/secondary：INV-06；INV-03。
- 当前路径与同族面：`fetch_pool_swaps.py:46-58`。
- 覆盖初判：①；施工证据：`test_fetch_failclosed.py` 相等/反向/负区间开文件前拒绝。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-FETCH` 对 10→10、100→10 和负数均 argparse exit 2、零正式产物。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-07

- 报告基线/严重度/归因：six@`fca61ad`；P1；半修残留。
- primary/secondary：INV-04；INV-03。
- 当前路径与同族面：`fetch_pool_swaps.py:46-114`（temp 写、完整后替换）。
- 覆盖初判：①；施工证据：`test_fetch_failclosed.py` 分页失败与旧产物保护。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-FETCH` 实际注入“第一页成功、下一页失败”，正式 CSV 不提交。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-08

- 报告基线/严重度/归因：six@`fca61ad`；P1；新引入。
- primary/secondary：INV-04；INV-03。
- 当前路径与同族面：`fetch_gmgn.sh:18-49`。
- 覆盖初判：①；施工证据：`test_fetch_gmgn_sh.py` 临时文件、JSON 与失败聚合。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-GMGN` success→failure/invalid 反例均把旧正式文件改名 `.stale`，总退出非零。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-09

- 报告基线/严重度/归因：six@`fca61ad`；P0；半修残留。
- primary/secondary：INV-14；INV-15。
- 当前路径与同族面：`add_labels.py:118-223`。
- 覆盖初判：①；施工证据：`test_add_labels_rollback.py` 三闸与回滚。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-LABEL-TXN` 逐个注入 validate/benchmark/manifest 失败，表与 manifest 均恢复。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-10

- 报告基线/严重度/归因：six@`fca61ad`；P1；半修残留。
- primary/secondary：INV-15；INV-18。
- 当前路径与同族面：`roundtrip_check.py:22-57,127-144`；resolver 的运行语义在 `labels_resolver.py:315-326`。
- 覆盖初判：①；施工证据：`test_roundtrip_check.py`；`test_batch1_risk_flags.py`。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-ROUNDTRIP` 的 risk_flags 单侧丢失反例转为非零；`CMD-R7` 的日期倒退也非零。后续 parser 同族残留另记 R7-14/R8-10，不反写本项结果。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-11

- 报告基线/严重度/归因：six@`fca61ad`；P2；半修残留。
- primary/secondary：INV-18；无。
- 当前路径与同族面：`retrospective.md:68,91`，`docs_lint.py` 8192B 守卫。
- 覆盖初判：①；施工证据：`docs_lint.py --all`；`test_sixlens_docs.py`。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-DOC` 通过；现役两处均为“7.5KB 预警、8192B 硬上限”。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-12

- 报告基线/严重度/归因：six@`fca61ad`；P2；历史漏检。
- primary/secondary：INV-19；INV-18。
- 当前路径与同族面：`casebook/README.md` 不再指 archive；`retrospective.md:93-95` 仅 A6 维护动作登记 evals。
- 覆盖初判：①；施工证据：`docs_lint.py --all`；`test_sixlens_docs.py` archive/runtime 路由。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-DOC` 的精确路由守卫通过；执行期 casebook 没有 `archive/evals` 命中。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-13

- 报告基线/严重度/归因：six@`fca61ad`；P1；历史漏检。
- primary/secondary：INV-08；INV-12。
- 当前路径与同族面：`handoff_manifest.py:164-180,212-222,396-419,966-1010`。
- 覆盖初判：①；施工证据：`test_handoff_manifest.py` 65 项；`B2F-LG-01`～`05`。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-HANDOFF` 实跑 READY 缺 chain、缺 contract、未知 chain 均拒，PARTIAL 不误收紧。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-01

- 报告基线/严重度/归因：R7@`d8bd3c5`；P0；新引入。
- primary/secondary：INV-01；INV-10。
- 当前路径与同族面：`shared_release_receipt.py:93-149`；`reconciliation_report.py:143-229`。
- 覆盖初判：②；施工证据：`B3-RUNNER-FRESH-01`；预置 receipt 在 producer 启动前被拒。
- 基线回放：**REPRODUCED**。`CMD-R7` 的点名用例只证明缺/错 runner binding 被拒；`CMD-FORGE` 用正确当前 binding 手工造四项 receipt，仍被接受，原“未执行 producer 也可手工伪造”不变量继续被击穿。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-02

- 报告基线/严重度/归因：R7@`d8bd3c5`；P0；半修残留。
- primary/secondary：INV-09；INV-03。
- 当前路径与同族面：`net.py` Result/curl backend；`anchor_sampler.py:208-223`。
- 覆盖初判：①；施工证据：`test_net_result.py`；`test_r7_findings.py::R7-02`。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-R7`/`CMD-RECEIPT` 对 curl rc=7 + 空 stdout 返回失败，anchor 落 ERROR side receipt、非零。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-03

- 报告基线/严重度/归因：R7@`d8bd3c5`；P0；半修残留。
- primary/secondary：INV-02；INV-05、INV-06。
- 当前路径与同族面：`anchor_sampler.py:137-179,245-275`；路径别名 sibling 同 R8-12。
- 覆盖初判：③；施工证据：`B3-SOL-PROD-03`；`B3-SOL-E2E`。
- 基线回放：**REPRODUCED**。原跨 mint 旧行已由 `CMD-R7` 拒；等价 target/output 身份反例 `CMD-R8-ALIAS` 令 data 与 receipt 同路径，程序 PASS 且发布后 data 不再存在。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-04

- 报告基线/严重度/归因：R7@`d8bd3c5`；P0；半修残留。
- primary/secondary：INV-02；INV-06、INV-08。
- 当前路径与同族面：`supply_truth_gate.py:103-175`；consumer `shared_release_receipt.py:151-161`。
- 覆盖初判：①；施工证据：`test_supply_truth_gate.py`；`test_r7_findings.py::R7-04`。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-R7`：formal `--replay-net-raw` 被拒；exploration receipt 被 formal aggregator 拒；formal stats file_ref 与 Solana observed context slot 在场。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-05

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；新引入。
- primary/secondary：INV-10；INV-01、INV-12。
- 当前路径与同族面：`reconciliation_report.py:143-229`；Solana supply producer `scan_token_accounts.py:139-150,253-273`。
- 覆盖初判：②；施工证据：`B3-SOL-PROD-04`；`B3-SOL-E2E` 真实 runner supply。
- 基线回放：**REPRODUCED**。canonical wrapper producer 已存在，但 R8-01 当前代码证明 registry 内 Solana producer 没有 runner 所需 receipt argv，且输出旧 schema；“强制 artifact 必须有唯一可执行 producer”的同族仍断裂。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-06

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；半修残留。
- primary/secondary：INV-06；INV-05、INV-10。
- 当前路径与同族面：`window_fetch.py:127-215`。
- 覆盖初判：③；施工证据：`B3-SOL-PROD-02/03`；`B3-SOL-E2E`。
- 基线回放：**REPRODUCED**。`CMD-R7` 证明反向范围和 stale 已修；`CMD-R8-ALIAS` 的合法单 segment 同路径运行仍 `rc=0/PASS`，数据被 receipt 覆盖，发布事务不闭合。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-07

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；新引入。
- primary/secondary：INV-11；INV-20。
- 当前路径与同族面：`chain_registry.py:6-49,128+`；handoff/audit 与四个 mandatory CLI。
- 覆盖初判：②；施工证据：`B2-CAP-01`～`B2-CAP-04`，不可变 release tier+能力事实矩阵，缺任一事实均不 ready；下游 choices/handoff/release 从矩阵派生。
- 基线回放：**REPRODUCED**。Arbitrum 已由 `CMD-R7` 正确拒 READY；但 `CMD-RH-CAP` 证明 registry 声明 Robinhood formal/recon=evm，而四个强制 CLI 全 exit 2，仍是“能力声明不由可执行闭合导出”。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-08

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；历史漏检。
- primary/secondary：INV-03；INV-12。
- 当前路径与同族面：`handoff_manifest.py:228-249,421-447`。
- 覆盖初判：②；施工证据：`B2-REC-01`，READY 从此无条件要求 wrapper 及四份当前 producer 回执深验。
- 基线回放：**REPRODUCED**。declared `PASS:2` 已由 `CMD-R7` 拒；`CMD-HANDOFF` 生成 BSC READY 时完全没有 reconciliation artifact/gate，generate/verify 仍 0。等价 fail-open 是整道 gate 可省。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-09

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；半修残留。
- primary/secondary：INV-13；INV-15。
- 当前路径与同族面：`entity_source_trace.py:206-222,653-679`；`handoff_manifest.py:606-728`。
- 覆盖初判：①；施工证据：`test_entity_source_trace.py`；`test_r7_findings.py::R7-09`。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-R7` 空 object/all unknown kind 在正式模式被拒；freeze 重读标签有效数。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-10

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；半修残留。
- primary/secondary：INV-14；INV-18。
- 当前路径与同族面：`add_labels.py:118-223`。
- 覆盖初判：①；施工证据：`test_add_labels_rollback.py`；`test_r7_findings.py::R7-10`。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-LABEL-TXN` 注入 archive copy failure、二次重名、独占发布竞态，表/manifest 原字节恢复且归档不覆盖。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-11

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；新引入。
- primary/secondary：INV-15；INV-18。
- 当前路径与同族面：`roundtrip_check.py:25-27,127-144`。
- 覆盖初判：①；施工证据：`test_roundtrip_check.py`；`test_r7_findings.py::R7-11`。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-R7` staging `verified_at` 比发布值更早时非零；三日期字段均走 directional compare。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-12

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；新引入。
- primary/secondary：INV-07；INV-11。
- 当前路径与同族面：`verify_recon.py:49-54,114-119` 已 attested；`time_spotcheck.py:140-153` sibling 未 attested。
- 覆盖初判：②；施工证据：`B1-RPC-01`～`B1-RPC-06`；10 个正式调用点均有错链零业务调用反例。
- 基线回放：**REPRODUCED**。`CMD-R7` 证明 verify_recon 错链在 eth_call 前拒；`CMD-R8-TARGET` 的 time sibling 只有 `eth_call`、没有 `eth_chainId`，仍 PASS。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-13

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；新引入。
- primary/secondary：INV-08；INV-06。
- 当前路径与同族面：`time_spotcheck.py:119-153`；plan producer `anchor_plan.py`。
- 覆盖初判：②；施工证据：`B3-TIME-01/02` plan↔execution final-block 精确绑定。
- 基线回放：**REPRODUCED**。chain/token 和 plan file_ref 已由 `CMD-R7` 修复；`CMD-R8-TARGET` 仍以 target block 10 查询 plan block 11 并 PASS，final-block 没有进入 plan/execution exact binding。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-14

- 报告基线/严重度/归因：R7@`d8bd3c5`；P2；新引入。
- primary/secondary：INV-15；INV-18。
- 当前路径与同族面：`roundtrip_check.py:50-57`; `add_labels.py:151-153`; `validate_labels.py:86-98`; `labels_resolver.py:318-326`。
- 覆盖初判：③；施工证据：`B1-RF-01`～`B1-RF-03`；`B2-P3-RF-01/02` 补零宽/不可见边界空白与非字符串 fail-closed，OB-2 `build_labels` 复用 canonical merge。
- 基线回放：**REPRODUCED**。roundtrip 自身 dedup/trim 已由 `CMD-R7` 转绿；但 `CMD-R8-FLAGS` 证明 canonical 集合语义未进入 add/validate/resolver 同族，前导空格绕过 validator 后被 resolver 激活。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-15

- 报告基线/严重度/归因：R7@`d8bd3c5`；P2；半修残留。
- primary/secondary：INV-18；INV-15。
- 当前路径与同族面：`references/labels/MAINTENANCE.md`; `roundtrip_check.py:22-27`; `add_labels.py:180-223`。
- 覆盖初判：①；施工证据：`test_roundtrip_check.py`；`test_add_labels_rollback.py`；docs lint。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-R7` 实际检查文档写七字段并点名 validate+benchmark+manifest 三闸，结果 PASS。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-01

- 报告基线/严重度/归因：R8@`6e94348`；P0；新引入。
- primary/secondary：INV-10；INV-01、INV-08。
- 当前路径与同族面：`shared_release_receipt.py:25-37,93-106`; `reconciliation_report.py:143-169`; `scan_token_accounts.py:139-150,253-273`。
- 覆盖初判：②；施工证据：`B3-SOL-PROD-04`；`B3-SOL-E2E` current envelope+consumer。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-02

- 报告基线/严重度/归因：R8@`6e94348`；P0；半修残留。
- primary/secondary：INV-11；INV-07、INV-20。
- 当前路径与同族面：`chain_registry.py:44-49`; `accounting_gate.py:65-79`; `verify_recon.py:58-65`; `supply_truth_gate.py:103-116`; `time_spotcheck.py:71-80`。
- 覆盖初判：④正式发布路径外豁免；`B2-RH-01` 覆盖 READY/A4/A5/build/audit、四回执自洽仍拒、labels/旧 seal 不抬升与豁免失效哨兵；影响/失效条件见 `robinhood-impact.md`，待 Fable 批准。
- 基线回放：`N/A-R8基线即当前`；补充实测 `CMD-RH-CAP` 四个 CLI 均 exit 2。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-03

- 报告基线/严重度/归因：R8@`6e94348`；P0；历史漏检。
- primary/secondary：INV-08；INV-10。
- 当前路径与同族面：`accounting_gate_sol.py:101-124`; `shared_release_receipt.py:173-190`; anchor/supply producer target。
- 覆盖初判：②；施工证据：`B3-SOL-PROD-01/05/06`；`B3-SOL-E2E` slot=77 单源。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-04

- 报告基线/严重度/归因：R8@`6e94348`；P1；新引入。
- primary/secondary：INV-05；INV-04。
- 当前路径与同族面：`receipt_kernel.py:192-220,268-273` 四类发布/恢复 primitive。
- 覆盖初判：③；施工证据：`B1-RK-01`～`B1-RK-06`；`B2-P3-RK-01` 证明 producer 路径中间目录 symlink 也拒绝；R9 批三已把 anchor/window producer 迁到 txn 联合提交。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：批三代码侧闭合；两 producer 的 `publish_txn` 是最后可失败的 data+receipt 操作，提交后不再执行独立内容自检。
- 两轮盲审与 Fable 结论：

### R8-05

- 报告基线/严重度/归因：R8@`6e94348`；P1；新引入。
- primary/secondary：INV-17；INV-18。
- 当前路径与同族面：`invariant_scan.py`; `invariant_manifest.json`; `formal_capability_probes.py`。
- 覆盖初判：③；施工证据：`B4-INV17-01/02` transport/正式入口 census 与分母 floor；R9 批三把 attested Solana 会话使用者纳入 transport census，并维持纵切片 target/SUITE 双绑定。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：既有批四销账保持；R9 批三 census 输出 `receipt_producers=51, receipt_consumers=55, transport_calls=60, atomic_writes=38, formal_entrypoints=58`。
- 两轮盲审与 Fable 结论：

### R8-06

- 报告基线/严重度/归因：R8@`6e94348`；P1；半修残留。
- primary/secondary：INV-12；INV-01、INV-10。
- 当前路径与同族面：`handoff_manifest.py:59-89,218-249,410-447`。
- 覆盖初判：②；施工证据：`B2-REC-01`，READY 必含 reconciliation wrapper，其 target/当前 runner/四 producer/四份 receipt 实体内容与哈希全部深验。
- 基线回放：`N/A-R8基线即当前`；补充 `CMD-HANDOFF`/定向 fixture 得 `generate=0, verify=0, reconciliation artifact=false`，gates 仅 accounting/supply/time。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-07

- 报告基线/严重度/归因：R8@`6e94348`；P1；半修残留。
- primary/secondary：INV-07；INV-08。
- 当前路径与同族面：`time_spotcheck.py:140-153`。
- 覆盖初判：②；施工证据：`B1-RPC-CALLSITE-time`；fake wrong-chain 只记录 `eth_chainId`，无 `eth_call`。
- 基线回放：`N/A-R8基线即当前`；补充 `CMD-R8-TARGET` 方法序列仅 `['eth_call']`，仍 PASS。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-08

- 报告基线/严重度/归因：R8@`6e94348`；P1；半修残留。
- primary/secondary：INV-06；INV-08。
- 当前路径与同族面：`time_spotcheck.py:119-153,162-180`。
- 覆盖初判：②；施工证据：`B3-TIME-01/02`；`B3-EVM-E2E-ETH/BSC/BASE`。
- 基线回放：`N/A-R8基线即当前`；补充 `CMD-R8-TARGET` target=10、实际 query/row=11、rc=0。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-09

- 报告基线/严重度/归因：R8@`6e94348`；P1；历史漏检。
- primary/secondary：INV-07；INV-02。
- 当前路径与同族面：`supply_truth_gate.py:84-98` 的 EVM `totalSupply()` 直接 eth_call。
- 覆盖初判：②；施工证据：`B1-RPC-CALLSITE-supply`；fake wrong-chain 只记录 `eth_chainId`，无 totalSupply `eth_call`。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-10

- 报告基线/严重度/归因：R8@`6e94348`；P2；半修残留。
- primary/secondary：INV-15；INV-14。
- 当前路径与同族面：`add_labels.py:151-153`; `validate_labels.py:86-98`; `roundtrip_check.py:50-57`; `labels_resolver.py:318-326`。
- 覆盖初判：③；施工证据：`B1-RF-01`～`B1-RF-03`；`B2-P3-RF-01/02` 补零宽/不可见边界空白、list/int 拒绝和 `build_labels` canonical merge。
- 基线回放：`N/A-R8基线即当前`；补充 `CMD-R8-FLAGS` validator `errors=[]`、resolver 激活 privacy。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-11

- 报告基线/严重度/归因：R8@`6e94348`；P1；历史漏检。
- primary/secondary：INV-09；INV-06、INV-16。
- 当前路径与同族面：`window_fetch.py:43-111,208-215`，`timestamp or 0` 后仍 complete。
- 覆盖初判：③；施工证据：`B3-SOL-PROD-02`；`B3F-TS-01`；`B3-SOL-E2E` timestamp summary。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-12

- 报告基线/严重度/归因：R8@`6e94348`；P1；半修残留。
- primary/secondary：INV-05；INV-02、INV-04。
- 当前路径与同族面：`anchor_sampler.py:143-150,245-275`; `window_fetch.py:127-215`; `receipt_kernel.py:204-220`（producer 未用 txn 联合提交）。
- 覆盖初判：③；施工证据：`B1-RK-01`～`B1-RK-06` 及 R9 批三真实 producer 迁移；anchor/window 均以 `publish_txn` 作最后可失败的 data+receipt 操作，删除提交后独立哈希自检/手工撤回面。
- 基线回放：`N/A-R8基线即当前`；补充 `CMD-R8-ALIAS` 两 producer 都 rc=0，最终路径只剩 receipt。
- 最终结果：R9 批三代码侧销账；联合提交后无独立自检 raise。
- 两轮盲审与 Fable 结论：

### R9-01

- 报告基线/严重度/归因：R9@`63cf715`；P0；老问题修复不全。
- primary/secondary：INV-08；INV-02、INV-11。
- 主覆盖类别：②正式链纵切片覆盖；批三已以 GPA `context.slot` 为唯一 canonical snapshot，CLI slot 降为断言，accounting/supply truth 消费同一 bundle。
- 基线回放：**REPRODUCED**。RPC `context.slot=999`，CLI `--as-of-slot 77`，当前 receipt 仍以 77 PASS。
- 最终结果：批三 observation bundle 已闭合“CLI 声明当观测”这一 P0 病根：RPC 观测值是唯一真值，绑定 mainnet genesis 常量、前后 raw 一致、GPA snapshot 与三方 supply 闭合，并由 13 项字段约束及三消费者复核。闭合边界**不含 bundle 防伪**：producer path/sha 与内部自洽字段不是不可伪造的产出凭证；测试中的关键输入必须由登记生产者现场生成，这一必经性依赖批四 producer/consumer 通用守卫。裁判 mainnet 证据已入档并由 B3F3-G5 补 owner，但不把内容绑定误写为执行来源证明。
- 两轮盲审与 Fable 结论：批三批内两循环收口——循环 2 复审 ALL-CLEAR（15/15 finding CLOSED：opus 攻击 4 + mutant 4、Fable 读码/台账 7，见 reviews/r9-batch3-rereview3-mutants.md 与 rereview-partial.md）。R9-01 观测协议批三代码侧闭合、裁判 mainnet 实证 diff=0，最终两轮全库盲审复验后彻底销账。

### R9-02

- 报告基线/严重度/归因：R9@`63cf715`；P1；修复中新引入。
- primary/secondary：INV-10；INV-06、INV-08。
- 主覆盖类别：②正式链纵切片覆盖；批一已把 EVM 正例改成现场运行 producer。
- 基线回放：**REPRODUCED**。真实旧 producer rc=0，但 plan 无 final_block；consumer `--final-block 300` rc=2。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R9-03

- 报告基线/严重度/归因：R9@`63cf715`；P1；老问题修复不全。
- primary/secondary：INV-03；INV-04、INV-06。
- 主覆盖类别：①新反例覆盖；`B1-R9-03-PROCESS/STALE`。
- 基线回放：**REPRODUCED**。缺 next_block fatal，真实进程 rc=0，旧 canonical CSV 留在正式路径。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R9-04

- 报告基线/严重度/归因：R9@`63cf715`；P1；老问题修复不全。
- primary/secondary：INV-03；INV-01、INV-04、INV-10。
- 主覆盖类别：①新反例覆盖；`B1-R9-04-PROCESS/MARKER`。
- 基线回放：**REPRODUCED**。out/receipt 路径冲突在 main 返回 2，但真实进程 rc=0。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R9-05

- 报告基线/严重度/归因：R9@`63cf715`；P1；修复中新引入。
- primary/secondary：INV-11；INV-02、INV-08。
- 主覆盖类别：②正式链纵切片覆盖；批三已接入 Solana observation/accounting 与 SQD state-anchor callsite，并注册 eth/bsc/base/sol 四个可执行 target。
- 基线回放：**REPRODUCED**。Solana formal-ready 正例无任何 cluster identity 请求仍通过。
- 最终结果：callsite 与 target 注册代码侧闭合；`formal_ready_chains()=={"eth","bsc","base","sol"}` 由证据自然导出。批内循环 1 消化 B3FIX-01/02：共享 urllib transport 复用 certifi CA context（缺包回退系统 CA），已污染 G3-0A 报告删除待裁判重跑；循环 2 消化 path 型 key 半修残留，异常/正式身份/cache meta 统一只保留脱敏 public origin 与不可逆 endpoint digest。当前 codex 沙箱两份真实 loopback 编排在首个 `socket.bind` 被系统 `EPERM` 阻断，**裁判环境全量 suite exit=0 已复跑通过**、PYTHIA mainnet smoke 全链 PASS（diff=0）。
- 两轮盲审与 Fable 结论：批三批内两循环收口——循环 2 复审 ALL-CLEAR（15/15 CLOSED）。callsite/target 注册与四链 ready 批三代码侧闭合，最终两轮全库盲审复验后彻底销账。

## 四、supplementary claims（不计 49 分母）

| ID | 原严重度/类型 | 链接主 finding / INV | 当前路径 | 准备阶段判断与证据 |
|---|---|---|---|---|
| `full-C-01` | P1 CONFLICT | `full-F-02`; INV-16 | `merge_hs_rpc.py:62-89`; `data-pipeline-robinhood-channels.md:16` | 仍成立；`CMD-RH` 输出 `int/str` 混合。随 Robinhood exploration 影响台账处理，不丢弃。 |
| `full-C-02` | P0 CONFLICT/FAIL-OPEN | `full-F-01`, `six-F-04`; INV-03/INV-09 | `anchor_sampler.py:196-279` | `B3-SOL-PROD-02/03` + `B3-SOL-E2E`；fail-closed 与联合发布已进真实纵切片。链接主账，不另增分母。 |
| `full-C-03` | P1 AMBIGUOUS | `full-F-01`, `R7-05`, `R8-01`, `R8-03`; INV-10/INV-18 | Solana A2 docs、registry、runner、producer | `B3-SOL-E2E`；Solana A2 producer→runner→consumer→READY→release 已闭环。 |
| `full-C-04` | P2 ROUTE CONFLICT | INV-18/INV-20 | `data-pipeline-evm-channels.md`; `scan_bloxroute_seg.py` | 未单列主 finding；批二能力矩阵需把 bloXroute 明确为 nonformal 并补防回流。 |
| `full-C-05` | P2 AMBIGUOUS/DRIFT | `full-F-02`; INV-02/INV-20 | `merge_hs_rpc.py:91-104`; Robinhood channels 文档 | 仍只有 stdout 摘要，无持久 receipt；随 RH exploration 豁免台账处理。 |
| `full-C-06` | P2 DRIFT | INV-19/INV-18 | `data-pipeline-solana-capture.md` 外部 GOAT 三脚本路由 | 准备阶段保留为 supplementary；批四方法论/路由守卫裁决，不改 49 分母。 |
| `full-C-07` | P3 DRIFT | `full-F-02`; INV-18/INV-19 | Robinhood 三采集器模块头、`resume_guard.py` | supplementary 保留；Robinhood 降级不改写历史，未来恢复 formal 前必须清理。 |
| `full-C-08` | P3 DRIFT | `R8-05`; INV-17/INV-18 | `retrospective.md`; `run_all.py` | supplementary 保留；批四以 registry/自动清单消除手写测试数量。 |

## 五、补充观察

`PREP-OBS` 数：**0**。本轮新增实测均可归入既有 finding 或同族残留，没有为凑问题数新开分母。

## 六、准备阶段回放计数

| 结果 | 数量 | finding |
|---|---:|---|
| REPRODUCED | 19 | `full-F-01`～`full-F-04`; `six-F-03`; `R7-01`,`R7-03`,`R7-05`,`R7-06`,`R7-07`,`R7-08`,`R7-12`,`R7-13`,`R7-14`; `R9-01`～`R9-05` |
| FIXED_ON_BASELINE | 18 | `six-F-01`,`six-F-02`,`six-F-04`～`six-F-13`（不含 `six-F-03`）；`R7-02`,`R7-04`,`R7-09`,`R7-10`,`R7-11`,`R7-15` |
| CHANGED | 0 | — |
| N/A-R8基线即当前 | 12 | `R8-01`～`R8-12` |
| **合计** | **49** |  |

## 七、批次裁决记录

> 主表"最终结果/两轮盲审"两栏留到总验收（两轮盲审后）统一回填；本节记每批批内审查这个中间里程碑，是批次级权威结论落点。

### 批一（公共原语）— 批内审查裁决：**PASS**

- 候选 SHA：`e657732`（区间 `66d7ba7..e657732`，含四施工 commit + 台账回填）。
- 批内审查执行者：**opus 子代理**（不用 codex——codex 做对抗审查触发 OpenAI 网络安全风控，见 project 记忆）。审查报告存 `/Users/uravvv/Documents/5.6筹码分析/r8-closure-reviews/batch1/batch1-review.md`（独立于修复 worktree）。
- 审查结论：无新引入、无半修残留、无历史 P0/P1；边界外一步 47 项守住 / 0 真实失效；④同族 rg 独立复列确认 10 个 EVM RPC 调用点全走 attested session、无第 11 个漏网、生产无裸 RpcPool；risk_flags `split("|")` 仅 `risk_flags.py:10` 一处；未映射 hunk 独立复算=0；suite 70/70。
- Fable 读码复核样本（2 处，亲读坐实）：`finalize_envelope` 用 `RESERVED_FIELDS.intersection(fields)`+verdict/exit 一致性+"已 finalize 拒重入"三重堵死历史先例（kwargs 覆盖身份绑定）；生产侧唯一 `RpcPool()` 构造在 `attested_rpc_pool` 工厂内（`net.py:373`），`formal and expected is None` 拒。
- 批一覆盖 finding 的批内状态：
  - `R8-04`（INV-05 kernel 路径身份）→ 批内已修，覆盖①；
  - `R7-12`/`R8-07`/`R8-09`（INV-07 attested session）→ 批内已修，覆盖②（纵切片证据接批三）；
  - `R7-14`/`R8-10`（INV-15 canonical parser）→ 批内已修，覆盖③已补反例；
  - `R8-12`（INV-05）→ **当批仅 kernel 能力闭合，producer 迁移当时留批三**；该尾巴现已由 R9 批三代码侧销账。
- 4 项 P3 处置（分层收口：历史 P2/P3 记录+修复+限定复核，不重置两轮）：
  - `B1R-01` 裸 `RpcPool(expected_chain_id=None)` 无自动守卫、invariant_scan 不区分裸池/工厂 → **归批四**（scanner 加"生产文件直接构造 RpcPool 即告警"）；当前生产代码干净（无裸池），仅缺防未来回退守卫。
  - `B1R-02` 同 endpoint 跨 call_many 复用首次 attestation → 设计权衡非缺陷，**记录不修**（endpoint 切换/failover 已重 attest）。
  - `B1R-03` `parse_risk_flags` 对零宽空格/非字符串宽进产生畸形单 flag → **并入批二开头就地修**（本批新建代码不留已知瑕疵，成本极低）。
  - `B1R-04` `_producer_ref` 中间目录 symlink 未逐级检 → **并入批二开头就地修**（kernel 内加固收尾，producer 现为可信 `__file__`）。
- 范围外观察（opus 报告 OB-1~OB-3）：OB-1 各命令 --chain choices 硬编码漂移=批二正题；OB-2 build_labels 本地拼接 risk_flags（有 canonical 兜底）=批二 B1R-03 一并核；OB-3 validate_labels strict 按目录字符串比较=批二能力矩阵顺带核。

### 批二（能力矩阵）— 批内审查裁决：**PASS**（三循环收口：BLOCK→消化→BLOCK→消化二→PASS）

- 候选 SHA：`db0b17d`（施工区间 `553806b..5924cd5` 五组+回填；消化一 `5924cd5..3ca824e` 三组+回填；消化二 `3ca824e..db0b17d` 单组+回填）。
- 批内审查执行者：**opus 子代理**（同一代理跨三轮续跑，上下文连续故可精准复测自己的攻击变体）。三份报告入库 `maintenance/repair-20260806/reviews/`：`batch2-review.md`（首轮 BLOCK）、`batch2-rereview.md`（增量重审 BLOCK）、`batch2-review3.md`（三审 PASS）。
- **首轮审查（BLOCK：P2=1 P3=4）**：核心不变量"formal-ready 由真实能力闭合导出"经最强攻击未击穿（三层 MappingProxyType 全 TypeError、生产零 harness import、READY 深验 C0-C10 十一变体全拒、RH 防回流八面守住、choices 10/10 单源派生）；但 B2R-01 legacy 旁路跳三重检查（P2 半修残留）、B2R-02 `_record_from` 自报 Mapping 后门、B2R-03 harness 无 teardown+自报表述不实、B2R-04 缺字节码防护、B2R-05 map 归组偏差（均 P3 新引入）。审查插曲：opus 曾凭印象虚构不存在的 tuple 版 chain_registry，自纠后重来（此后三轮"每论断先读磁盘"零复发）。
- **消化一（B2F-G1~G3=`138b707`/`ee7d4d5`/`af92a91`+回填 `3ca824e`）**：legacy 改 registry release_tier 长期语义准入（Fable 工单预判并规避了 opus 原修复建议的 READY_CHAINS 恒空误伤陷阱）+在场深验+OB-A audit 消费点；readiness API 字符串-only；harness contextmanager 可逆+三层只读；字节码 setdefault；反例 B2F-LG-01~04。
- **增量重审（BLOCK：P3=4，全新引入）**：上轮 5 项+2 观察全闭合、C0-C10 零回归、存量旧案不误伤（含大写别名）、入库报告逐字未篡改；但消化代码自身引入 B2FR-01 "在场"判据取 manifest 自报清单可摘登记绕深验（伪缺席第三态，新测试摘登记+unlink 绑死故不可达）、B2FR-02 generate set 去重/verify 列表长度口径漂移、B2FR-03 台账漏列+表述张力、B2FR-04 Fable 区间末端未取 tip（OB-D 同族重犯）。OB-E（formal_ready(None) 行为变化生产面安全）/OB-F（源码字符串弱断言）/OB-G（marker 子目录设计内）三观察记录不修。
- **消化二（B2F2-G1=`9609655`+回填 `db0b17d`，最小改动面恰四文件+85/-6）**：wrapper_present 改"清单登记或磁盘 isfile"取或+B2F-LG-05 伪缺席反例；generate 判重后 `sorted(set(chains))`+duplicate-chain 反例；台账补列/区间修正；回填区间行改文字自指"至本回填 commit"（规避回填 commit 无法预知自身 SHA 的悖论——前两轮区间滞后的根因）。
- **三审（PASS：全零，不触发止损线）**：四项 B2FR 闭合（伪缺席 rc=2/真缺席 rc=0/bsc,bsc 自产自验过）；新判据 `os.path.isfile` 四边界变体全守住（目录冒充退化为等价缺席且下游独立拒；案外/案内/严格路径 symlink 均被 `shared_release_receipt.regular()` 的 symlink+越界防护拦）；`sorted(set)` 单链路径零影响、handoff 65 项不回退；未映射 hunk 复算=0；suite 76/76 独立复跑；台账零自报不实；自指写法获裁决"满足通例意图且优于机械填 SHA"。三审为聚焦审查，全库扫描留两轮盲审。
- Fable 读码复核（三轮均亲核后才发工单/代 commit）：首轮 5/5 属实（含抓出 opus 两个修复建议均会误伤旧案的陷阱）；重审 4/4 属实（含抽查 generate 侧代码坐实口径漂移）；消化二 diff 逐 hunk 核+亲测 76/76 绿（三轮各一次）。
- 批二覆盖 finding 的批内状态：
  - `R7-07`/`R8-02`（INV-11 能力矩阵+RH exploration）→ 批内已修，覆盖①③；RH 豁免 `RH-EX-01/02` 台账七要素齐备待总验收裁决；
  - `R8-06`（INV-12 READY reconciliation 必经）→ 批内已修（含 legacy 通道补闸），覆盖①；纵切片证据接批三；
  - `R7-08`（同族）→ 随 INV-12 闭合；
  - 批一遗留 `B1R-03`/`B1R-04` → B2-G0 已就地修毕销账。
- 工艺记录：批一 P3 收尾（B2-G0）与本批主体同批施工；三轮审查报告均分段落盘（opus 长会话写长报告流中断两次后的硬性要求）；消化二首次发射静默死（进程活/日志 31min 零输出），kill 重发即成。

### 批三（正式链纵切片）— 批内审查裁决：**代码侧收口 PASS**（两循环：BLOCK→消化→重审代码零发现；台账 P3 由 Fable 即时修正、核验交批四）

- 候选 SHA：`d889e72`（施工 `62efbf9..3df1234` 四组+回填；消化一 `3df1234..a0481e2` 三组+回填；B3FR-01 台账修正 `d889e72`=Fable）。
- 批内审查执行者：**opus 子代理**（同一代理续跑，跨批上下文连续）。两份报告入库 `reviews/`：`batch3-review.md`（首轮 BLOCK）、`batch3-rereview.md`（重审）。
- **首轮审查（BLOCK：P2=1 P3=2，全新引入）**：批三主体质量好——三个纵切片测试验真（真实生产 CLI+loopback transport、零禁令 mock、无手写 PASS 正例、"先删后真造"排除 fixture 残留）、Solana slot 缺失三形态与 timestamp 四边界全 fail-closed、EVM 错链计数机制 server 端可信、八处既有测试适配全属必然无放松、"临时产物已清理"自报属实。缺陷：B3R-01（P2）window/anchor 联合事务**提交后**独立自检 raise 不撤回——`published_current` 死变量致撤回恒假（Fable 亲核零赋值坐实），坏数据+PASS receipt 双残留 exit=1 矛盾，违反 INV-03/04，坏边表会进正式分析链；B3R-02 生产代码留 2 元组 legacy test adapter+timestamps 证据零消费者可被清空；B3R-03 map B3-G3 行多列一文件。
- **点名问题 B3R-Q1（vertical_slice_verified 落真绑定）判 P3 归批四，与 Fable 预判一致**：判非 R7-07 族病（12 项闭合之一、缺任一即假、不构成短路），但是 12 项中唯一动态事实（断言"测试跑通过"而非"代码存在"）最需第二道绑定；定 P3 决定性依据=纵切片测试已验真、声明有据，run_all 挂载一道防线非零、反向绑定（改 False 即红）已在。批四守卫形态已登记 §八。
- **消化一（B3F-G1=`75d112f`/B3F-G2=`7c04b72`/B3F-G3=`a85974d`+回填 `a0481e2`，恰 9 文件）**：committed 显式标志+撤回顺序"先 unlink PASS receipt（消费者 fail-closed 优先）再移数据出正式位"+withdrawal_errors 如实拼入 exc+死变量清除+kernel 零改动；五处 scan_seg mock 改 3 元组+生产兼容分支删除+complete 段数与每段 min/max 齐备为 PASS 前置；OB-H resume 权衡论证/OB-I 登记措辞收窄/OB-J 计数盲区记录；反例 B3F-TXN-01/02+B3F-TS-01。
- **增量重审（代码零发现；唯一 P3=B3FR-01 纯台账）**：上轮全部闭合且高于最低要求——window/anchor **双注入实测**四项终态全满足（exit≠0/数据不在正式位/receipt.json 不存在/error receipt 为 ERROR），anchor 补上首轮静态判定的实测证实同族等深；撤回中间态（receipt 已删、移数据失败）仍 fail-closed 且错误文本如实；timestamps append 在锁内、核对在 join 后，FAIL 路径未误伤；disk-full 两断言原样保留；suite 79/79。B3FR-01=map B3F-G2 行与真实 commit 边界错位（根源：一文件多 owner hunk vs 文件级 commit 的固有张力+Fable 回填未校正清单，与 B2R-05/B3R-03 同族第三犯）。
- **Fable 裁决（止损计数口径）**：采纳"代码新引入"口径判批三代码侧收口。理由：止损线目的是防"代码修不干净的循环"，纯台账文字错位不构成该风险；opus 备齐两种口径事实依据并建议台账并入下批维护；B3FR-01 由 Fable 即时修正（`d889e72`：B3F-G1/G2 行物理/语义 owner 互注+通例补"回填时校正清单"规则防第四犯），修正核验交批四批内审查顺带核对（非自说自话闭环）。
- 批三覆盖 finding 的批内状态：`R8-01`/`R8-03`/`R8-11`/`R8-12`/`R7-03`/`R7-06`（Solana producer 族）与 `R8-07`/`R8-08`/`R8-09`/`R7-13`（EVM 执行面）→ 批内已修+纵切片证据在案；`R8-06`/`R7-08` 纵切片验证必经性完成；`full-F-01`/`six-F-03`/`R7-01` 由"未运行 producer 无法通过 aggregator"真实编排承接；`full-C-02`/`full-C-03` Solana A2 闭环完成；`R7-05` runner 可执行 envelope 收口。批一 `R8-12` producer 迁移面本批销账。
- 工艺记录：opus 首轮方法自纠（mktemp 根被批一 symlink 防护拦、换 realpath 根）反向印证批一防护真实生效；批三消化发射一次成功（无静默死）；重审 anchor 实测补齐是"同族关到同一深度"纪律的执行范例。

### 批四（守卫/fixture/方法论）— 批内审查裁决：**PASS**（一循环：BLOCK(2 P3)→消化→重审全零）

- 候选 SHA：`0f53b68`（施工 `f2a6e41..6b7ab8d` 三组+回填；消化 `B4F-G1`=`13d76c0`+回填 `0f53b68`）。
- 批内审查执行者：**opus 子代理**（同一代理续跑）。两份报告入库 `reviews/`：`batch4-review.md`（首轮 BLOCK）、`batch4-rereview.md`（重审 PASS）。
- **首轮审查（BLOCK：P3=2+2 观察，全新引入）**：批四主体质量高——九个边界变体七个守住（含批三"删测试+摘 SUITE"两步绕过被双条件堵死、分母整键删除比反例声称更强、SUITE 检查用 AST 非 grep）；8 注入反例真实且配绿例防误伤；fixture 零过时三面独立抽查通过（solana-holder-snapshot-v2 确认为与 v3 并存现役非过时）；六脚本"发布路径外"机器判据+消费链双验属实；方法论 41 行纯追加含对施工方不利的止损条款零美化；B3FR-01 修正核验闭合；零自报不实。缺陷：B4R-01 LABEL_CHAIN_SURFACES 七面遗漏第八同形态面 accumulate_offenders.py:249（对照注入实测：覆盖面红/未覆盖面静默；**opus 自我反证降级范例**——初判 P2 依据 archive 工单，按"archive 不得作为验收证据"改用 registered_formal_entrypoints() 机器判据确认发布路径外，下调 P3）；B4R-02 派生源缺键抛裸 KeyError 缺明确诊断（方向已 fail-closed，缺陷在可诊断性）。观察：OB-K 裸池守卫对 import-as 别名不可见（威胁模型内，措辞收窄）；OB-L 方法论缺"注入须自证到达目标分支"条（opus 批三两次踩坑教训）。
- **消化（B4F-G1=`13d76c0`，恰五文件）**：第八面收编（membership:chain:1）+复列无第九面；派生源缺键/family 不同步/空 runner 抛 FormalEntrypointSourceError 带"两侧不同步"诊断；措辞收窄；方法论补条。
- **重审（PASS 全零）**：修复深度超最低要求——labels 对表升级**双向**（注入 polygon 与摘 robinhood 都红且精确定位）、原七面不误伤、locator 判据泛化；派生源三类注入全出明确诊断零 Traceback，opus 另加测第四类（整键删除 ADVERSARIAL_RUNNERS）同样守住，正常路径 16 项不变；"无第九面"自报经同法独立复列核验通过（其余 rg 命中均为别名映射/外部服务能力表/业务子集，不构成声明面）；B4F-FORMAL-01 断言诊断文本而非仅非零退出=方法论新条自我践行；未映射=0 清单逐文件吻合；suite 80/80。
- 批四覆盖 finding 的批内状态：`R8-05`（INV-17 scanner 分母）→ 销账；`full-F-04` 动态计数守卫补齐；`B1R-01`/`OB-B`/`B3R-Q1` 三守卫欠账全部落地收口；fixture 审计与六脚本判定入档。
- 工艺记录：守卫本身作为被审对象过了独立可绕性检验；批四消化一次循环收口（全工程最快）。

### R9 批三（正式纵切片重建）— 当前裁决：**B3F_BLOCKED（环境验真未闭）**

- 代码侧：observation bundle、三消费者、动态 Solana runner、SQD scope callsite、anchor/window txn 尾巴、四链 evidence target、G3-0 双载体壳和裁判 smoke 命令均已落地。
- 门禁：全量 `run_all.py` 共 87 项，85 项 PASS；唯二失败是 Solana/EVM 正式纵切片 fixture 在创建 `ThreadingHTTPServer` 时被本沙箱 `socket.bind(127.0.0.1)` 以 `EPERM` 拒绝，尚未进入任何生产业务断言。
- 不降级：没有用 skip、声明型 PASS 或手写 plan 取代真实编排；因此四链 target 已挂载并自然导出 ready，但 R9-05 最终执行证据及 R9-01 mainnet 证据仍保留裁判待登记位。
- 批内循环计数：`2`。循环 1 为裁判 mainnet 首跑发现的 B3FIX-01/P2、B3FIX-02/P1；循环 2 为 Opus 攻击审查确认的 B3R9-01～15（P1=1/P2=7/P3=7）。两轮 finding 均已进入正式反例与代码侧修复，循环 2 仍须以本轮全量门禁及裁判 loopback/mainnet 复跑作最终执行证据。
- 裁判复跑：先在允许 loopback bind 的离线环境重跑两份纵切片及全量 suite，再按 `b3_progress.md` 执行 G3-0 与 PYTHIA mainnet smoke；全部满足后方可改写为 `B3F_COMPLETE`。

## 八、批四自动守卫待办

- `B1R-01`：已由 `B4-RPC-01` 落地；`invariant_scan` 扫生产文件，除 `net.py:attested_rpc_pool` 外任何直接 `RpcPool(` 构造即红，临时生产样本注入已验。
- `OB-B`：已由 `B4-LABEL-01/02` 落地；known 路由面与 formal+exploration 六链对表，资产表面与 `labels_table=True` 五链对表，多链/漏链双向均红。
- `B3R-Q1`：已由 `B4-VS-01/02` 落地；所有 `vertical_slice_verified=True` 链同时绑定显式测试映射、磁盘文件和 `run_all.SUITE`，缺任一即红。
- `R8-05/full-F-04`：已由 `B4-INV17-01/02`、`B4-RH-COUNT-01` 落地；transport census 覆盖 requests/urllib/httpx/net/变量 curl，正式必经最小集由能力矩阵和 producer registry 推导，五类分母低于 floor 即红，Robinhood 文档数量与磁盘 16/15 实数动态对表。
- 批三六个未迁脚本判定：`trace_wallet.py`、`gas_origin.py`、`probe_escrows.py` 无生产 consumer；`stake_decode.py` 只喂 `whale_deep.py`，`whale_deep.py` 只喂 `build_evolution.py`，而其 `camp_series.json` 无 release consumer；`scan_sharded.py` 仅产与正式 `scan_token_accounts.py` 兼容的手工作业文件，未进 producer registry。六者当前均为发布路径外工具；未来接入 formal runner/required artifact 前必须迁 current envelope/attestation，并由 INV-17 新入口守卫触发登记。
