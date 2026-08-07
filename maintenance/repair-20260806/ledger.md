# R8 修复闭环主账（准备阶段）

- 当前基线：`6e943486a9e4a6f2b673c7cd7a03093f463da233`（`main@6e94348`，v6.36.0）
- 主账分母：44（full 4 + six-lens 13 + R7 15 + R8 12）。
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

## 二、44 项主表（按 primary INV 行族排列）

| canonical ID | 报告基线 | 严重度 | 原归因 | primary | secondary | 当前生产路径与同族面（6e94348） | 覆盖初判 | 测试/纵切片/豁免证据 | 基线回放 | 最终结果 | 两轮盲审 / Fable |
|---|---|---:|---|---|---|---|---|---|---|---|---|
| `full-F-01` | full@`b0b7744` | P0 | 报告未判定 | INV-01 | INV-10, INV-12 | `shared_release_receipt.py:93-149,173-209`; `reconciliation_report.py:143-229`; `handoff_manifest.py:68-89,218-249` | ② | 待施工 | REPRODUCED (`CMD-FORGE`) |  |  |
| `six-F-03` | six@`fca61ad` | P0 | 历史漏检 | INV-01 | INV-02, INV-10 | 同上 | ② | 待施工 | REPRODUCED (`CMD-FORGE`) |  |  |
| `R7-01` | R7@`d8bd3c5` | P0 | 新引入 | INV-01 | INV-10 | 同上；点名 test 只拒无/错 runner binding | ② | 待施工 | REPRODUCED (`CMD-FORGE`; `CMD-R7` 点名绿不构成执行证明) |  |  |
| `full-F-02` | full@`b0b7744` | P1 | 报告未判定 | INV-02 | INV-06, INV-16, INV-20 | `pull_transfers_rpc.py:13-62`; `pull_block_ts_anchors.py:5-24`; `merge_hs_rpc.py:47-104` | ④ | 待 Fable 批准；见 `robinhood-impact.md` | REPRODUCED (`CMD-RH`) |  |  |
| `R7-03` | R7@`d8bd3c5` | P0 | 半修残留 | INV-02 | INV-05, INV-06 | `anchor_sampler.py:137-179,245-275`; sibling alias in `CMD-R8-ALIAS` | ③ | 待施工 | REPRODUCED（原 resume 反例被拒；同族 data/receipt alias 仍击穿） |  |  |
| `R7-04` | R7@`d8bd3c5` | P0 | 半修残留 | INV-02 | INV-06, INV-08 | `supply_truth_gate.py:103-175`; `shared_release_receipt.py:151-161` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-R7`: formal raw override 拒、file_ref/context slot 在场) |  |  |
| `six-F-02` | six@`fca61ad` | P0 | 历史漏检 | INV-03 | INV-07 | `verify_recon.py:58-144` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-RECEIPT`: mismatch=2, RPC error=1) |  |  |
| `six-F-04` | six@`fca61ad` | P0 | 历史漏检 | INV-03 | INV-09 | `anchor_sampler.py:196-279` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-RECEIPT`: fetch/no-converge 非零且无 canonical PASS) |  |  |
| `R7-08` | R7@`d8bd3c5` | P1 | 历史漏检 | INV-03 | INV-12 | `handoff_manifest.py:228-249,421-447` | ② | 待施工 | REPRODUCED（declared PASS/2 已修；同族 reconciliation gate 可整项省略，`CMD-HANDOFF`） |  |  |
| `six-F-05` | six@`fca61ad` | P0 | 历史漏检 | INV-04 | INV-03, INV-06 | `window_fetch.py:127-231` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-RECEIPT`: gap 只留 partial/stale，exit=2) |  |  |
| `six-F-07` | six@`fca61ad` | P1 | 半修残留 | INV-04 | INV-03 | `fetch_pool_swaps.py:46-114` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-FETCH`: 分页失败不提交正式 CSV) |  |  |
| `six-F-08` | six@`fca61ad` | P1 | 新引入 | INV-04 | INV-03 | `fetch_gmgn.sh:18-49` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-GMGN`: success→failure 旧文件转 `.stale`) |  |  |
| `R8-04` | R8@`6e94348` | P1 | 新引入 | INV-05 | INV-04 | `receipt_kernel.py:192-220,268-273` | ③ | 待施工 | N/A-R8基线即当前 |  |  |
| `R8-12` | R8@`6e94348` | P1 | 半修残留 | INV-05 | INV-02, INV-04 | `anchor_sampler.py:143-150,245-275`; `window_fetch.py:127-215` | ③ | 待施工 | N/A-R8基线即当前 |  |  |
| `six-F-06` | six@`fca61ad` | P0 | 半修残留 | INV-06 | INV-03 | `fetch_pool_swaps.py:46-58` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-FETCH`: 相等/反向/负区间开文件前拒) |  |  |
| `R7-06` | R7@`d8bd3c5` | P1 | 半修残留 | INV-06 | INV-05, INV-10 | `window_fetch.py:127-215` | ③ | 待施工 | REPRODUCED（原反向窗已修；同族 data/receipt alias 仍 PASS，`CMD-R8-ALIAS`） |  |  |
| `R8-08` | R8@`6e94348` | P1 | 半修残留 | INV-06 | INV-08 | `time_spotcheck.py:119-153,162-180` | ② | 待施工 | N/A-R8基线即当前 |  |  |
| `R7-12` | R7@`d8bd3c5` | P1 | 新引入 | INV-07 | INV-11 | `verify_recon.py:49-54,114-119`; sibling `time_spotcheck.py:140-153` | ② | 待施工 | REPRODUCED（verify_recon 原入口已修；time sibling 无 `eth_chainId`，`CMD-R8-TARGET`） |  |  |
| `R8-07` | R8@`6e94348` | P1 | 半修残留 | INV-07 | INV-08 | `time_spotcheck.py:140-153` | ② | 待施工 | N/A-R8基线即当前 |  |  |
| `R8-09` | R8@`6e94348` | P1 | 历史漏检 | INV-07 | INV-02 | `supply_truth_gate.py:84-98` | ② | 待施工 | N/A-R8基线即当前 |  |  |
| `six-F-13` | six@`fca61ad` | P1 | 历史漏检 | INV-08 | INV-12 | `handoff_manifest.py:164-180,212-222,396-419,966-1010` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-HANDOFF`: READY 缺 chain/contract/未知链均拒) |  |  |
| `R7-13` | R7@`d8bd3c5` | P1 | 新引入 | INV-08 | INV-06 | `time_spotcheck.py:119-153`; `anchor_plan.py` target producer | ② | 待施工 | REPRODUCED（plan chain/token/file_ref 已修；final-block 未绑定且查询 cutoff+1，`CMD-R8-TARGET`） |  |  |
| `R8-03` | R8@`6e94348` | P0 | 历史漏检 | INV-08 | INV-10 | `accounting_gate_sol.py:101-124`; `shared_release_receipt.py:173-190` | ② | 待施工 | N/A-R8基线即当前 |  |  |
| `R7-02` | R7@`d8bd3c5` | P0 | 半修残留 | INV-09 | INV-03 | `net.py` Result/curl backend；`anchor_sampler.py:208-223` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-R7`/`CMD-RECEIPT`: curl rc=7 空 stdout → ERROR/nonzero) |  |  |
| `R8-11` | R8@`6e94348` | P1 | 历史漏检 | INV-09 | INV-06, INV-16 | `window_fetch.py:43-111,208-215` | ③ | 待施工 | N/A-R8基线即当前 |  |  |
| `R7-05` | R7@`d8bd3c5` | P1 | 新引入 | INV-10 | INV-01, INV-12 | `reconciliation_report.py:143-229`; `shared_release_receipt.py:25-37` | ② | 待施工 | REPRODUCED（wrapper producer 已有；Solana supply producer CLI/schema 无法被 runner 执行，见 R8-01 当前路径） |  |  |
| `R8-01` | R8@`6e94348` | P0 | 新引入 | INV-10 | INV-01, INV-08 | `scan_token_accounts.py:139-150,253-273`; `reconciliation_report.py:143-169`; `shared_release_receipt.py:93-106` | ② | 待施工 | N/A-R8基线即当前 |  |  |
| `R7-07` | R7@`d8bd3c5` | P1 | 新引入 | INV-11 | INV-20 | `chain_registry.py:6-49,128+`; `handoff_manifest.py:84,164-180`; mandatory CLIs | ② | 待施工 | REPRODUCED（Arbitrum 已正确降级；Robinhood formal=true 但四 CLI 全拒，`CMD-RH-CAP`） |  |  |
| `R8-02` | R8@`6e94348` | P0 | 半修残留 | INV-11 | INV-07, INV-20 | `chain_registry.py:44-49`; four mandatory CLI choices | ④ | 待 Fable 批准；见 `robinhood-impact.md` | N/A-R8基线即当前 |  |  |
| `R8-06` | R8@`6e94348` | P1 | 半修残留 | INV-12 | INV-01, INV-10 | `handoff_manifest.py:59-89,218-249,410-447` | ② | 待施工 | N/A-R8基线即当前 |  |  |
| `six-F-01` | six@`fca61ad` | P0 | 历史漏检 | INV-13 | INV-12, INV-20 | `entity_source_trace.py:206-222,653-679`; `handoff_manifest.py:606-728` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-ENTITY`: 正式缺 labels 拒；探索 freeze 拒) |  |  |
| `R7-09` | R7@`d8bd3c5` | P1 | 半修残留 | INV-13 | INV-15 | 同上，正式有效标签计数双端重算 | ① | 待施工 | FIXED_ON_BASELINE (`CMD-R7`: 空/未知 kind labels formal 拒) |  |  |
| `six-F-09` | six@`fca61ad` | P0 | 半修残留 | INV-14 | INV-15 | `add_labels.py:118-223` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-LABEL-TXN`: validate+benchmark+manifest 强制) |  |  |
| `R7-10` | R7@`d8bd3c5` | P1 | 半修残留 | INV-14 | INV-18 | `add_labels.py:118-223`（archive staging 在三闸前、失败整体回滚） | ① | 待施工 | FIXED_ON_BASELINE (`CMD-LABEL-TXN`: staging/重名/竞态失败均回滚) |  |  |
| `six-F-10` | six@`fca61ad` | P1 | 半修残留 | INV-15 | INV-18 | `roundtrip_check.py:22-57,127-144`; `labels_resolver.py:315-326` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-ROUNDTRIP`: risk_flags 漂移阻断；日期倒退由 R7 test 阻断) |  |  |
| `R7-11` | R7@`d8bd3c5` | P1 | 新引入 | INV-15 | INV-18 | `roundtrip_check.py:25-27,127-144` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-R7`: verified_at 倒退非零) |  |  |
| `R7-14` | R7@`d8bd3c5` | P2 | 新引入 | INV-15 | INV-18 | `roundtrip_check.py:50-57`; sibling add/validate/resolver | ③ | 待施工 | REPRODUCED（roundtrip 自身 trim/dedup 已修；validator/resolver 仍语义分裂，`CMD-R8-FLAGS`） |  |  |
| `R8-10` | R8@`6e94348` | P2 | 半修残留 | INV-15 | INV-14 | `add_labels.py:151-153`; `validate_labels.py:86-98`; `labels_resolver.py:318-326` | ③ | 待施工 | N/A-R8基线即当前 |  |  |
| `full-F-03` | full@`b0b7744` | P1 | 报告未判定 | INV-16 | INV-03, INV-07, INV-20 | `multicall_balances.py:31-35,57-83,85-115` | ④ | 待调用图与防回流证明、Fable 批准 | REPRODUCED (`CMD-MC`) |  |  |
| `R8-05` | R8@`6e94348` | P1 | 新引入 | INV-17 | INV-18 | `invariant_scan.py:174-232,269-329`; `invariant_manifest.json` | ③ | 待施工 | N/A-R8基线即当前 |  |  |
| `full-F-04` | full@`b0b7744` | P3 | 报告未判定 | INV-18 | INV-17 | `data-pipeline-robinhood.md:16`; `scripts/robinhood/` | ③ | 待施工 | REPRODUCED（文档仍“全14件”，当前普通文件 16） |  |  |
| `six-F-11` | six@`fca61ad` | P2 | 半修残留 | INV-18 | — | `retrospective.md:68,91`; `docs_lint.py` 8192B 守卫 | ① | 待施工 | FIXED_ON_BASELINE (`CMD-DOC`: 7.5KB 预警/8192B 硬闸统一) |  |  |
| `R7-15` | R7@`d8bd3c5` | P2 | 半修残留 | INV-18 | INV-15 | `references/labels/MAINTENANCE.md`; `roundtrip_check.py:22-27`; `add_labels.py:180-223` | ① | 待施工 | FIXED_ON_BASELINE (`CMD-R7`: 七字段/三闸文档一致) |  |  |
| `six-F-12` | six@`fca61ad` | P2 | 历史漏检 | INV-19 | INV-18 | `casebook/README.md`; `retrospective.md:93-95`; docs archive guard | ① | 待施工 | FIXED_ON_BASELINE (`CMD-DOC`: casebook 执行路由不再回流 archive；A6 维护动作保留) |  |  |

## 三、逐项详情

以下小节补足主表中压缩的证据。每项“最终结果”和“两轮盲审/Fable”均故意留空，准备阶段不提前裁决。

### full-F-01

- 报告基线/严重度/归因：full@`b0b7744`；P0；报告未判定。
- primary/secondary：INV-01；INV-10、INV-12。
- 当前路径与同族面：`shared_release_receipt.py:93-149,173-209`；`reconciliation_report.py:143-229`；`handoff_manifest.py:68-89,218-249`。
- 覆盖初判：②由纵切片覆盖；施工证据：待施工。
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
- 覆盖初判：③需补独立反例；施工证据：待施工。
- 基线回放：**REPRODUCED**。命令 `find scripts/robinhood -maxdepth 1 -type f | wc -l` 得 16；文档声明 14。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-01

- 报告基线/严重度/归因：six@`fca61ad`；P0；历史漏检。
- primary/secondary：INV-13；INV-12、INV-20。
- 当前路径与同族面：`entity_source_trace.py:653-679` 正式 labels 必填且有效数非零；`handoff_manifest.py:606-728` freeze 重验。
- 覆盖初判：①已被新反例覆盖；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-ENTITY` 实跑“正式缺 labels exit 2；显式无标签仅 exploration”，freeze 侧另有拒收测试。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-02

- 报告基线/严重度/归因：six@`fca61ad`；P0；历史漏检。
- primary/secondary：INV-03；INV-07。
- 当前路径与同族面：`verify_recon.py:58-144` 参数化、chain attestation、结构化 receipt 和分级退出。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-RECEIPT` 得 supply/balance mismatch `exit=2`，RPC error `exit=1`，闭合正例 `exit=0`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-03

- 报告基线/严重度/归因：six@`fca61ad`；P0；历史漏检。
- primary/secondary：INV-01；INV-02、INV-10。
- 当前路径与同族面：与 full-F-01 相同。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：**REPRODUCED**。`CMD-FORGE` 证明未知/空 schema 已被堵，但“当前 producer 真实执行”仍可由手工自洽内容加当前 runner hash 冒充；关键输出为 `FABRICATED_FIXTURE_ACCEPTED_TARGET ...`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-04

- 报告基线/严重度/归因：six@`fca61ad`；P0；历史漏检。
- primary/secondary：INV-03；INV-09。
- 当前路径与同族面：`anchor_sampler.py:196-279`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-RECEIPT` 对 fetch_fail/no_converge 均生成 ERROR side receipt 并非零退出；无 canonical PASS。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-05

- 报告基线/严重度/归因：six@`fca61ad`；P0；历史漏检。
- primary/secondary：INV-04；INV-03、INV-06。
- 当前路径与同族面：`window_fetch.py:127-231`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-RECEIPT` 的 gap 运行输出 `.partial`、旧正式件转 stale、返回 2；成功才正式发布。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-06

- 报告基线/严重度/归因：six@`fca61ad`；P0；半修残留。
- primary/secondary：INV-06；INV-03。
- 当前路径与同族面：`fetch_pool_swaps.py:46-58`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-FETCH` 对 10→10、100→10 和负数均 argparse exit 2、零正式产物。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-07

- 报告基线/严重度/归因：six@`fca61ad`；P1；半修残留。
- primary/secondary：INV-04；INV-03。
- 当前路径与同族面：`fetch_pool_swaps.py:46-114`（temp 写、完整后替换）。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-FETCH` 实际注入“第一页成功、下一页失败”，正式 CSV 不提交。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-08

- 报告基线/严重度/归因：six@`fca61ad`；P1；新引入。
- primary/secondary：INV-04；INV-03。
- 当前路径与同族面：`fetch_gmgn.sh:18-49`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-GMGN` success→failure/invalid 反例均把旧正式文件改名 `.stale`，总退出非零。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-09

- 报告基线/严重度/归因：six@`fca61ad`；P0；半修残留。
- primary/secondary：INV-14；INV-15。
- 当前路径与同族面：`add_labels.py:118-223`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-LABEL-TXN` 逐个注入 validate/benchmark/manifest 失败，表与 manifest 均恢复。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-10

- 报告基线/严重度/归因：six@`fca61ad`；P1；半修残留。
- primary/secondary：INV-15；INV-18。
- 当前路径与同族面：`roundtrip_check.py:22-57,127-144`；resolver 的运行语义在 `labels_resolver.py:315-326`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-ROUNDTRIP` 的 risk_flags 单侧丢失反例转为非零；`CMD-R7` 的日期倒退也非零。后续 parser 同族残留另记 R7-14/R8-10，不反写本项结果。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-11

- 报告基线/严重度/归因：six@`fca61ad`；P2；半修残留。
- primary/secondary：INV-18；无。
- 当前路径与同族面：`retrospective.md:68,91`，`docs_lint.py` 8192B 守卫。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-DOC` 通过；现役两处均为“7.5KB 预警、8192B 硬上限”。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-12

- 报告基线/严重度/归因：six@`fca61ad`；P2；历史漏检。
- primary/secondary：INV-19；INV-18。
- 当前路径与同族面：`casebook/README.md` 不再指 archive；`retrospective.md:93-95` 仅 A6 维护动作登记 evals。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-DOC` 的精确路由守卫通过；执行期 casebook 没有 `archive/evals` 命中。
- 最终结果：
- 两轮盲审与 Fable 结论：

### six-F-13

- 报告基线/严重度/归因：six@`fca61ad`；P1；历史漏检。
- primary/secondary：INV-08；INV-12。
- 当前路径与同族面：`handoff_manifest.py:164-180,212-222,396-419,966-1010`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-HANDOFF` 实跑 READY 缺 chain、缺 contract、未知 chain 均拒，PARTIAL 不误收紧。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-01

- 报告基线/严重度/归因：R7@`d8bd3c5`；P0；新引入。
- primary/secondary：INV-01；INV-10。
- 当前路径与同族面：`shared_release_receipt.py:93-149`；`reconciliation_report.py:143-229`。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：**REPRODUCED**。`CMD-R7` 的点名用例只证明缺/错 runner binding 被拒；`CMD-FORGE` 用正确当前 binding 手工造四项 receipt，仍被接受，原“未执行 producer 也可手工伪造”不变量继续被击穿。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-02

- 报告基线/严重度/归因：R7@`d8bd3c5`；P0；半修残留。
- primary/secondary：INV-09；INV-03。
- 当前路径与同族面：`net.py` Result/curl backend；`anchor_sampler.py:208-223`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-R7`/`CMD-RECEIPT` 对 curl rc=7 + 空 stdout 返回失败，anchor 落 ERROR side receipt、非零。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-03

- 报告基线/严重度/归因：R7@`d8bd3c5`；P0；半修残留。
- primary/secondary：INV-02；INV-05、INV-06。
- 当前路径与同族面：`anchor_sampler.py:137-179,245-275`；路径别名 sibling 同 R8-12。
- 覆盖初判：③；施工证据：待施工。
- 基线回放：**REPRODUCED**。原跨 mint 旧行已由 `CMD-R7` 拒；等价 target/output 身份反例 `CMD-R8-ALIAS` 令 data 与 receipt 同路径，程序 PASS 且发布后 data 不再存在。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-04

- 报告基线/严重度/归因：R7@`d8bd3c5`；P0；半修残留。
- primary/secondary：INV-02；INV-06、INV-08。
- 当前路径与同族面：`supply_truth_gate.py:103-175`；consumer `shared_release_receipt.py:151-161`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-R7`：formal `--replay-net-raw` 被拒；exploration receipt 被 formal aggregator 拒；formal stats file_ref 与 Solana observed context slot 在场。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-05

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；新引入。
- primary/secondary：INV-10；INV-01、INV-12。
- 当前路径与同族面：`reconciliation_report.py:143-229`；Solana supply producer `scan_token_accounts.py:139-150,253-273`。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：**REPRODUCED**。canonical wrapper producer 已存在，但 R8-01 当前代码证明 registry 内 Solana producer 没有 runner 所需 receipt argv，且输出旧 schema；“强制 artifact 必须有唯一可执行 producer”的同族仍断裂。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-06

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；半修残留。
- primary/secondary：INV-06；INV-05、INV-10。
- 当前路径与同族面：`window_fetch.py:127-215`。
- 覆盖初判：③；施工证据：待施工。
- 基线回放：**REPRODUCED**。`CMD-R7` 证明反向范围和 stale 已修；`CMD-R8-ALIAS` 的合法单 segment 同路径运行仍 `rc=0/PASS`，数据被 receipt 覆盖，发布事务不闭合。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-07

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；新引入。
- primary/secondary：INV-11；INV-20。
- 当前路径与同族面：`chain_registry.py:6-49,128+`；handoff/audit 与四个 mandatory CLI。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：**REPRODUCED**。Arbitrum 已由 `CMD-R7` 正确拒 READY；但 `CMD-RH-CAP` 证明 registry 声明 Robinhood formal/recon=evm，而四个强制 CLI 全 exit 2，仍是“能力声明不由可执行闭合导出”。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-08

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；历史漏检。
- primary/secondary：INV-03；INV-12。
- 当前路径与同族面：`handoff_manifest.py:228-249,421-447`。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：**REPRODUCED**。declared `PASS:2` 已由 `CMD-R7` 拒；`CMD-HANDOFF` 生成 BSC READY 时完全没有 reconciliation artifact/gate，generate/verify 仍 0。等价 fail-open 是整道 gate 可省。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-09

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；半修残留。
- primary/secondary：INV-13；INV-15。
- 当前路径与同族面：`entity_source_trace.py:206-222,653-679`；`handoff_manifest.py:606-728`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-R7` 空 object/all unknown kind 在正式模式被拒；freeze 重读标签有效数。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-10

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；半修残留。
- primary/secondary：INV-14；INV-18。
- 当前路径与同族面：`add_labels.py:118-223`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-LABEL-TXN` 注入 archive copy failure、二次重名、独占发布竞态，表/manifest 原字节恢复且归档不覆盖。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-11

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；新引入。
- primary/secondary：INV-15；INV-18。
- 当前路径与同族面：`roundtrip_check.py:25-27,127-144`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-R7` staging `verified_at` 比发布值更早时非零；三日期字段均走 directional compare。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-12

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；新引入。
- primary/secondary：INV-07；INV-11。
- 当前路径与同族面：`verify_recon.py:49-54,114-119` 已 attested；`time_spotcheck.py:140-153` sibling 未 attested。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：**REPRODUCED**。`CMD-R7` 证明 verify_recon 错链在 eth_call 前拒；`CMD-R8-TARGET` 的 time sibling 只有 `eth_call`、没有 `eth_chainId`，仍 PASS。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-13

- 报告基线/严重度/归因：R7@`d8bd3c5`；P1；新引入。
- primary/secondary：INV-08；INV-06。
- 当前路径与同族面：`time_spotcheck.py:119-153`；plan producer `anchor_plan.py`。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：**REPRODUCED**。chain/token 和 plan file_ref 已由 `CMD-R7` 修复；`CMD-R8-TARGET` 仍以 target block 10 查询 plan block 11 并 PASS，final-block 没有进入 plan/execution exact binding。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-14

- 报告基线/严重度/归因：R7@`d8bd3c5`；P2；新引入。
- primary/secondary：INV-15；INV-18。
- 当前路径与同族面：`roundtrip_check.py:50-57`; `add_labels.py:151-153`; `validate_labels.py:86-98`; `labels_resolver.py:318-326`。
- 覆盖初判：③；施工证据：待施工。
- 基线回放：**REPRODUCED**。roundtrip 自身 dedup/trim 已由 `CMD-R7` 转绿；但 `CMD-R8-FLAGS` 证明 canonical 集合语义未进入 add/validate/resolver 同族，前导空格绕过 validator 后被 resolver 激活。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R7-15

- 报告基线/严重度/归因：R7@`d8bd3c5`；P2；半修残留。
- primary/secondary：INV-18；INV-15。
- 当前路径与同族面：`references/labels/MAINTENANCE.md`; `roundtrip_check.py:22-27`; `add_labels.py:180-223`。
- 覆盖初判：①；施工证据：待施工。
- 基线回放：**FIXED_ON_BASELINE**。`CMD-R7` 实际检查文档写七字段并点名 validate+benchmark+manifest 三闸，结果 PASS。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-01

- 报告基线/严重度/归因：R8@`6e94348`；P0；新引入。
- primary/secondary：INV-10；INV-01、INV-08。
- 当前路径与同族面：`shared_release_receipt.py:25-37,93-106`; `reconciliation_report.py:143-169`; `scan_token_accounts.py:139-150,253-273`。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-02

- 报告基线/严重度/归因：R8@`6e94348`；P0；半修残留。
- primary/secondary：INV-11；INV-07、INV-20。
- 当前路径与同族面：`chain_registry.py:44-49`; `accounting_gate.py:65-79`; `verify_recon.py:58-65`; `supply_truth_gate.py:103-116`; `time_spotcheck.py:71-80`。
- 覆盖初判：④正式发布路径外豁免；影响/失效条件见 `robinhood-impact.md`，待 Fable 批准。
- 基线回放：`N/A-R8基线即当前`；补充实测 `CMD-RH-CAP` 四个 CLI 均 exit 2。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-03

- 报告基线/严重度/归因：R8@`6e94348`；P0；历史漏检。
- primary/secondary：INV-08；INV-10。
- 当前路径与同族面：`accounting_gate_sol.py:101-124`; `shared_release_receipt.py:173-190`; anchor/supply producer target。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-04

- 报告基线/严重度/归因：R8@`6e94348`；P1；新引入。
- primary/secondary：INV-05；INV-04。
- 当前路径与同族面：`receipt_kernel.py:192-220,268-273` 四类发布/恢复 primitive。
- 覆盖初判：③；施工证据：待施工。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-05

- 报告基线/严重度/归因：R8@`6e94348`；P1；新引入。
- primary/secondary：INV-17；INV-18。
- 当前路径与同族面：`invariant_scan.py:174-232,269-329`; `invariant_manifest.json`。
- 覆盖初判：③；施工证据：待施工。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-06

- 报告基线/严重度/归因：R8@`6e94348`；P1；半修残留。
- primary/secondary：INV-12；INV-01、INV-10。
- 当前路径与同族面：`handoff_manifest.py:59-89,218-249,410-447`。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：`N/A-R8基线即当前`；补充 `CMD-HANDOFF`/定向 fixture 得 `generate=0, verify=0, reconciliation artifact=false`，gates 仅 accounting/supply/time。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-07

- 报告基线/严重度/归因：R8@`6e94348`；P1；半修残留。
- primary/secondary：INV-07；INV-08。
- 当前路径与同族面：`time_spotcheck.py:140-153`。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：`N/A-R8基线即当前`；补充 `CMD-R8-TARGET` 方法序列仅 `['eth_call']`，仍 PASS。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-08

- 报告基线/严重度/归因：R8@`6e94348`；P1；半修残留。
- primary/secondary：INV-06；INV-08。
- 当前路径与同族面：`time_spotcheck.py:119-153,162-180`。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：`N/A-R8基线即当前`；补充 `CMD-R8-TARGET` target=10、实际 query/row=11、rc=0。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-09

- 报告基线/严重度/归因：R8@`6e94348`；P1；历史漏检。
- primary/secondary：INV-07；INV-02。
- 当前路径与同族面：`supply_truth_gate.py:84-98` 的 EVM `totalSupply()` 直接 eth_call。
- 覆盖初判：②；施工证据：待施工。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-10

- 报告基线/严重度/归因：R8@`6e94348`；P2；半修残留。
- primary/secondary：INV-15；INV-14。
- 当前路径与同族面：`add_labels.py:151-153`; `validate_labels.py:86-98`; `roundtrip_check.py:50-57`; `labels_resolver.py:318-326`。
- 覆盖初判：③；施工证据：待施工。
- 基线回放：`N/A-R8基线即当前`；补充 `CMD-R8-FLAGS` validator `errors=[]`、resolver 激活 privacy。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-11

- 报告基线/严重度/归因：R8@`6e94348`；P1；历史漏检。
- primary/secondary：INV-09；INV-06、INV-16。
- 当前路径与同族面：`window_fetch.py:43-111,208-215`，`timestamp or 0` 后仍 complete。
- 覆盖初判：③；施工证据：待施工。
- 基线回放：`N/A-R8基线即当前`。
- 最终结果：
- 两轮盲审与 Fable 结论：

### R8-12

- 报告基线/严重度/归因：R8@`6e94348`；P1；半修残留。
- primary/secondary：INV-05；INV-02、INV-04。
- 当前路径与同族面：`anchor_sampler.py:143-150,245-275`; `window_fetch.py:127-215`; `receipt_kernel.py:204-220`（producer 未用 txn 联合提交）。
- 覆盖初判：③；施工证据：待施工。
- 基线回放：`N/A-R8基线即当前`；补充 `CMD-R8-ALIAS` 两 producer 都 rc=0，最终路径只剩 receipt。
- 最终结果：
- 两轮盲审与 Fable 结论：

## 四、supplementary claims（不计 44 分母）

| ID | 原严重度/类型 | 链接主 finding / INV | 当前路径 | 准备阶段判断与证据 |
|---|---|---|---|---|
| `full-C-01` | P1 CONFLICT | `full-F-02`; INV-16 | `merge_hs_rpc.py:62-89`; `data-pipeline-robinhood-channels.md:16` | 仍成立；`CMD-RH` 输出 `int/str` 混合。随 Robinhood exploration 影响台账处理，不丢弃。 |
| `full-C-02` | P0 CONFLICT/FAIL-OPEN | `full-F-01`, `six-F-04`; INV-03/INV-09 | `anchor_sampler.py:196-279` | 原反例已修；`CMD-RECEIPT` fetch/no-converge 非零。链接主账，不另增分母。 |
| `full-C-03` | P1 AMBIGUOUS | `full-F-01`, `R7-05`, `R8-01`, `R8-03`; INV-10/INV-18 | Solana A2 docs、registry、runner、producer | 当前由 R8-01/R8-03 继续成立；纳入 Solana 纵切片。 |
| `full-C-04` | P2 ROUTE CONFLICT | INV-18/INV-20 | `data-pipeline-evm-channels.md`; `scan_bloxroute_seg.py` | 未单列主 finding；批二能力矩阵需把 bloXroute 明确为 nonformal 并补防回流。 |
| `full-C-05` | P2 AMBIGUOUS/DRIFT | `full-F-02`; INV-02/INV-20 | `merge_hs_rpc.py:91-104`; Robinhood channels 文档 | 仍只有 stdout 摘要，无持久 receipt；随 RH exploration 豁免台账处理。 |
| `full-C-06` | P2 DRIFT | INV-19/INV-18 | `data-pipeline-solana-capture.md` 外部 GOAT 三脚本路由 | 准备阶段保留为 supplementary；批四方法论/路由守卫裁决，不改 44 分母。 |
| `full-C-07` | P3 DRIFT | `full-F-02`; INV-18/INV-19 | Robinhood 三采集器模块头、`resume_guard.py` | supplementary 保留；Robinhood 降级不改写历史，未来恢复 formal 前必须清理。 |
| `full-C-08` | P3 DRIFT | `R8-05`; INV-17/INV-18 | `retrospective.md`; `run_all.py` | supplementary 保留；批四以 registry/自动清单消除手写测试数量。 |

## 五、补充观察

`PREP-OBS` 数：**0**。本轮新增实测均可归入既有 finding 或同族残留，没有为凑问题数新开分母。

## 六、准备阶段回放计数

| 结果 | 数量 | finding |
|---|---:|---|
| REPRODUCED | 14 | `full-F-01`～`full-F-04`; `six-F-03`; `R7-01`,`R7-03`,`R7-05`,`R7-06`,`R7-07`,`R7-08`,`R7-12`,`R7-13`,`R7-14` |
| FIXED_ON_BASELINE | 18 | `six-F-01`,`six-F-02`,`six-F-04`～`six-F-13`（不含 `six-F-03`）；`R7-02`,`R7-04`,`R7-09`,`R7-10`,`R7-11`,`R7-15` |
| CHANGED | 0 | — |
| N/A-R8基线即当前 | 12 | `R8-01`～`R8-12` |
| **合计** | **44** |  |
