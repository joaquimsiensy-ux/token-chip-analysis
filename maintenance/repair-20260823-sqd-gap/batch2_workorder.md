# 批 2 工单（codex 施工）：SQD 覆盖探针 `sqd_coverage_probe.py` ＋ 共享地图生命周期 ＋ getBlocks 确认 ＋ coverage validator（分支 fix/sqd-gap-v6520）

- 前置：批 1b 验收通过（分支 HEAD=0b93d34；先红 35 项红证在档 `batch1b_red_evidence.txt`；预期先红＝`invariant_scan.py` 20 项登记缺口＋`test_batch4_invariant_guards.py:198`，见 errata **E20**）。
- 权威：`PLAN.md` §4.1 A2.0／§4.2.1／§4.3.1／§4.4.1／§4.4.2（guard）／§4.4.6 ＋ `PLAN_errata_batch0.md` E2/E8/E9/E10/E13/**E20** ＋ 契约草案 `contracts_draft/sqd-solana-coverage_v1.json`、`sqd-solana-coverage-pointer_v1.json`、`canonicalization.json`（冲突：errata ＞ 草案 ＞ PLAN 正文）。
- 目标对齐：交付**可在本机联网运行**的探针与**离线可重算**的 coverage validator；本批不碰修复生产者/代/bundle（批 3）、不碰 reconcile（批 5）。离线施工（沙箱无网）：联网冒烟由 Fable 本机代跑。不 commit、完成即停。
- 开工门禁：`cd .staging_b2 && shasum -a 256 -c STAGING_B2_SHA256.txt` 全 OK；否则停工写 done。

## 参考实现（只读，`.staging_b2/arc_reference/`；不入库）
- `sqd_query_variants/probe_lib.py`（SQD 查询封装）、`scan_nonce_windows.py`（`nonce_count`）、`dense_nonce_map.py`（`nonce_block_map`）、`finalize_after_dense.py`（`presence()`）——ARC 案实测 6/6 命中 0 误报的判定逻辑，**移植语义、重写成 skill 风格**（经 `scripts/lib/net.py` transport、kernel 原子写、脱敏）。
- `routeA_full/run_full.py`：只借 Helius 调用形态、`redact`、ledger 写法；探针用的是 `getBlocks`（不是 getBlock）。
- `sqd_query_variants/FINDINGS_sqd_omission_rootcause.md`：缺陷事实与指纹（"有块头但零 AdvanceNonce"）。
- 离线样本：`sqd_census_*.json`（4 份 SQD 整块普查响应：3 缺陷块＋1 健康块）、`dense_map_final.json`、`nonce_window_scan.json`、`stage4_era_sample_nonce.json`、`short_gaps_9_19.json`——可抽小样本做入库 fixture（`scripts/tests/fixtures/sqd_coverage/`，合计 ≤200KB）。
- `fetch_sqd_transfers_v2.py`（仓库现役）：SQD 端点常量/分页游标/metadata 指纹的现成写法，只读复用。

## 白名单
1. 新件 `scripts/solana/sqd_coverage_probe.py`（producer：`sqd-solana-coverage/v1`＋`sqd-solana-coverage-pointer/v1`）
2. 新件 `scripts/lib/solana_exact_validate.py`——**本批只实现 coverage 段**（模块顶部分段注释：coverage 段（批 2）/repair 段（批 3）/reconcile 段（批 5））；**不 import `replay_edges`/`sqd_repair_core`**；纯函数，输入路径＋案区间，返回 `{ok, reasons[], recomputed{...}}`
3. `scripts/lib/net.py`：`curl_json` 的 error 负载增 `http_status:int|None`（用 curl `-w '%{http_code}'` 或等价解析）与 `retryable:bool`；新增参数 `no_retry_statuses=()`；**默认行为对现有调用方零变化**（现 `_curl_error` :62-66、重试循环 :115-130）；`scripts/tests/test_net_result.py` 增对应断言
4. `scripts/hooks/guard_file_ops.py` `RAW_PATTERNS`（:25-29）增 `/data/sqd_coverage/` 下规范件（`coverage_map.json`、`slot_counts.bin.gz`、`blocks.bin.gz`、`ledger.jsonl`、`CURRENT.json`、`.lock`、`pending-*/…`）——按既有机制只允许生产者写
5. `assets/sqd-solana-coverage-map/README.md`（目录说明＋资产 schema＝4.2.1 去 mint 超集＋`supersedes`＋`ttl_days:30`＋`canary{slots[64],counts}`＋`.counts.bin.gz`/`.blocks.bin.gz` 伴随文件；**首版数据由 Fable 本机 ARC 全扫后入库，本批不放数据**）
6. `scripts/tests/test_sqd_coverage_probe.py`：(3)(20)(21)(28)(30) 由红变绿（红证对照）＋探针单测（离线 mock transport 用 fixture 喂 SQD/Helius 响应）：四态判定、E8 整数时代校准、UNSCANNED 残留拒、长度/台账无洞/并集 ⊇ 案区间、getBlocks complete 八项合取式逐项反例、位图编解码、probe_id 重算、发布协议（pending→fsync→rename→fsync→锁内 CAS→锁内 fsync；monkeypatch `os.fsync` 记录目录 fd 三次）、E10 同 probe_id 幂等、STOPPED 配额停工（mock 402/429）、`--resume`、redact（断言 key 字符串不出现在任何落盘/日志）、禁止游程阈值法（源码守卫）
7. `scripts/tests/fixtures/sqd_coverage/`（小样本）
8. `scripts/tests/invariant_manifest.json`：把批 1b 为 probe 预登记的条目**核对到实际实现**（locator/semantics 一致；不得为绿而删条目）
9. **E20 闭合（probe 半边）**：`scripts/tests/test_batch3_solana_vertical_slice.py`——只增不删：在 `VERTICAL_SLICE_EVIDENCE_TARGETS["r9-solana-pythia-mainnet-vertical-slice"]` 注册的 target 函数（及其 `main` 可达闭包）里**真实 subprocess 执行** `scripts/solana/sqd_coverage_probe.py`（离线 fixture transport 模式）产出 coverage 产物＋指针，使 `invariant_scan.formal_e2e_provenance_errors()` 的 sol 缺口从 `['replay_edges.py','sqd_coverage_probe.py']` 收窄为仅 `['replay_edges.py']`（replay 半边批 5 闭合）；做法参照该纵切片对现役 producer（scan_token_accounts/anchor_sampler/window_fetch 等）用 fixture 跑 formal 路径的既有方式；`_reachable_execution_evidence` 是 AST 静态可达分析——调用形态要与现役纵切片一致（字面脚本路径）。为此探针需提供**离线 fixture transport**（如 `--transport-fixture <dir>`：SQD/Helius 响应按请求摘要从目录读；仅测试使用；产物协议不变）。
10. `maintenance/repair-20260823-sqd-gap/batch2_done.md` ＋ `batch2_green_evidence.txt`（含：四新测试中 probe 项由红变绿对照、`run_all.py` 全量输出——预期仍红：`invariant_scan.py`（缺口应从 20 降到只剩 repair/validator-repair 段/wave v5/flow v3/reconcile v4 相关）＋`test_batch4_invariant_guards.py:198`（仅剩 replay 半边）；其余全绿）
**不动**：`fetch_sqd_transfers_v2.py`、`replay_edges.py`、`spl_edge_core.py`（只读复用）、`producer_history.py`、`run_all.py`、`VERSION/pyproject/CHANGELOG/SKILL.md`、references 文档（批 6；`scan-schemas.md` 已在批 1b 登记，如实现与登记字段冲突只记录不改）、上述以外的其他测试、PLAN/errata/契约草案。
- 工作方式：小步；每完成一个模块就跑对应测试；`run_all.py` 最后跑一遍并把红项逐条解释为"预期先红（E20/登记缺口）"或"本批回归（必须修）"；发现工单与文件实况不符（行号/函数名）→ 停工写 done 报告。

## 功能规格（与契约草案逐字段对齐；差异以 errata ＞ 草案 为准）
- CLI：`sqd_coverage_probe.py --mint <mint> --case-root <dir> --from-slot A --to-slot B [--full | --known-map <asset.json>] [--sample N] [--workers 4] [--reference-rpc <url>] [--resume] [--no-getblocks] [--dry-run]`；产物 `<case-root>/data/sqd_coverage/<probe_id>/{coverage_map.json,slot_counts.bin.gz,blocks.bin.gz,ledger.jsonl}` ＋ `<case-root>/data/sqd_coverage/CURRENT.json`；`--dry-run` 只打印预计请求数/slot 数/地图复用计划。
- SQD 查询体＝4.3.1 原话（`includeAllBlocks:true`，`instructions:[{programId:[System],d4:["0x04000000"]}]`，fields block.number＋instruction.transactionIndex），游标分页≈450 slot/请求；每请求写 ledger（4.2.1 字段）并填 u8 阵列（0=UNSCANNED,1=NO_HEADER,2=HEADER_ZERO_NONCE,n≥3→nonce_count=n−2，255 饱和）；`--workers` 线程池，区间分片互不重叠；SQD HTTP 错误经 net.py 重试后仍失败 ⇒ ledger `ok:false`、对应 slot 保持 UNSCANNED ⇒ 探针结束时若存在 UNSCANNED 则**不发布**（不写 CURRENT），退出码 2 并打印缺口区间（`--resume` 只补缺口）。
- 四态（HEALTHY/NO_HEADER/DEFECT_CANDIDATE/ERA_UNCERTAIN）与时代校准：1,000,000-slot 窗，`min_headers:10000`、`min_ratio_num/den=99/100`，整数交叉相乘（E8）；候选清单 `candidate_slots` 升序去重；`verdict` 三值展示值。
- NO_HEADER 确认：参考源 `getBlocks(from,to)` commitment finalized，每次 ≤500,000 slot，先 `getSlot(finalized)` 记 `reference_head_at_check`；逐段 `{from,to,response_sha256,count,response_ok,array_monotonic_unique,array_in_range}`（E2 重裁）；位图 `blocks.bin.gz`（u1/slot）；`complete` 不落盘为布尔，validator 按八项合取式重算；`--no-getblocks` ⇒ `skipped_confirmation:null`（NO_HEADER 全 unconfirmed ⇒ INCONCLUSIVE）。在列表中的 NO_HEADER ⇒ MISSING_BLOCK 候选；不在 ⇒ SKIPPED_CONFIRMED。
- 共享地图（`--known-map`）：TTL 未过期、`sqd.metadata_normalized`＋端点指纹一致、**已知 defect/refuted slot 逐 slot 复核**、canary 64 slot 计数一致 ⇒ 复用 `reused_ranges`（mode map-reuse）＋对地图未覆盖/新增区间全扫（mode full）＋复核段（mode recheck）；任一不符 ⇒ 升全扫并记 `shared_map.fallback_reason`；`sample_ranges` 只作附加证据不计并集。**禁止游程阈值法**（单 slot 判定）。
- 发布协议（E9/E10）：`pending-<scan_id>/`（scan_id＝sha256(mint,scan_ranges,sqd 指纹,启动 UTC)[:16]）写齐四文件并逐文件 fsync → fsync 目录 → `os.rename` 为 `<probe_id>/`（probe_id＝coverage_map 去 `probe_id` 字段规范化内容 sha256[:16]，写入前算出） → fsync 父目录 → `.lock`（flock 独占）→ CAS（`supersedes == CURRENT.probe_id`，无 CURRENT 时 null）→ `receipt_kernel.publish_overwrite` 写 CURRENT（PASS 收据，字段按 pointer 草案）→ 锁内 fsync 指针父目录；同 probe_id＋同哈希 ⇒ 幂等（只补 fsync，`idempotent-republish`，退出 0）；CAS 失败 ⇒ 目录保留、报错退出。探针产物不可变（再跑＝新 probe_id）。
- 配额/限流（4.4.6）：getBlocks/getSlot 遇 402/429 或 Helius 配额错误体 ⇒ 首次确定性即停止派发，在途完成后落账，写 `pending-<scan_id>/STOPPED.json{reason,cursor}`，退出码 3；`--resume` 续。
- key 只从 `~/.config/helius/api-key` 读（`--reference-rpc` 可覆盖；不自动降级公共 RPC）；沙箱无该文件——单测 mock；所有异常/URL/ledger 经 `endpoint_identity.redact_endpoint_text` 脱敏，测试断言 key 字符串零落盘。
- 原子写一律走 `receipt_kernel.publish_exclusive/publish_overwrite`（二进制文件用同级 tmp＋fsync＋rename 语义）。
- validator（coverage 段）：重算四态/候选/时代/有效 verdict；UNSCANNED 残留/解压长度≠to−from+1/ledger 成功并集有洞或≠scan_ranges 并集/并集不 ⊇ 案区间 ⇒ 拒；getBlocks 八项合取式、位图长度/popcount/范围；probe_id 重算一致；pointer inputs 哈希与文件一致、`supersedes` 链可追溯；返回结构化结果。
- 性能：全区间 1.34 亿 slot ≈30 万请求；u8 阵列 ≈134MB 内存可接受；进度日志节流（每 500 请求一行）；`--dry-run` 输出预计。

## 验收口径（Fable）
离线单测绿＋红证→绿证对照；`run_all.py` 除预期先红外全绿；Fable 本机联网冒烟：ARC 已知缺陷区段（426,649,000–426,670,000）＋健康块 439,000,000±1,000 ＋ 一段含 NO_HEADER 的区间，对照 `dense_map_final.json`（staging）逐 slot 一致；然后全区间后台扫（≈1 天）产共享地图首版。done 报告附"本机冒烟建议命令"。
