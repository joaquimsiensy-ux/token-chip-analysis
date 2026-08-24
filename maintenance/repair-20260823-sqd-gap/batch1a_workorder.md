# 批 1a 工单（codex 施工）：契约草案按 errata 全量修订 ＋ 三张继承字段表抄录（准入补丁）

- 分支：`fix/sqd-gap-v6520`（已 checkout；你直接在工作树改文件，**不 commit、不切分支**）
- 基线：代码面 main=f06078e（v6.51.0）；档案面 `maintenance/repair-20260823-sqd-gap/`
- 权威文件：`PLAN.md`（§4.2/§4.4）＋ **`PLAN_errata_batch0.md`（E1–E13，冲突处以 errata 为准）**＋ `batch0_final_review_codex.txt`（终审原文，供对照）
- 目标对齐：只把**契约草案 JSON** 改到与 PLAN＋errata 完全一致、补齐三张"从现役实现抄录"的继承字段表；**不改 PLAN/errata、不改任何仓库代码/测试/文档、不写生产代码**。离线、不 commit、完成即停。

## 白名单（只能改/建这些）
1. `maintenance/repair-20260823-sqd-gap/contracts_draft/*.json`（16 份草案＋INDEX；可改所有受 errata 影响的文件）
2. `maintenance/repair-20260823-sqd-gap/batch1a_done.md`（汇报件，新建）
其余任何文件零写入。

## 任务
### A. 按 errata 逐条修订（每条在 done 报告给出"errata 条 → 文件 → 字段/不变量"对照）
- **E1**：`publish_protocol.json` 步骤①改为 errata 口径；删除"旧冲突"notes；`canonicalization.json` 清单保持（并按 E6 增 `rpc_ledger header`）。
- **E2 重裁**：`sqd-solana-coverage_v1.json` 的 `skipped_confirmation.ranges[]` 每段字段改为 `{from,to,response_sha256,count,response_ok,array_monotonic_unique,array_in_range}`；`complete` 离线合取式按 errata 原话（8 项合取）写入 invariants；notes 去掉"歧义"表述。
- **E6**：`rpc_ledger.json` 增首行 header `{"schema":"sqd-solana-rpc-ledger/v1","plan_digest","reference{kind,endpoint_fingerprint}"}`，逐行字段不变；resume 判据 plan_digest 来源写明；`canonicalization.json` 的 `plan_digest_required_files` 增 `rpc_ledger header`。
- **E8**：`sqd-solana-coverage_v1.json` 的 `era_params` 改 `{window:1000000,min_headers:10000,min_ratio_num:99,min_ratio_den:100}`（整数）；`canonicalization.json` 增不变量"全工程落盘 JSON 禁浮点，比率用分子/分母整数"。
- **E9**：`sqd-solana-coverage-pointer_v1.json` 按 errata E9 字段表**重写**（含 `supersedes`、`inputs` 四项、`probe_id`）；`sqd-solana-coverage_v1.json` 增探针发布协议（pending-<scan_id>→fsync→rename <probe_id>→fsync 父目录→锁内 CAS→锁内 fsync）到 invariants；`solana-reconcile_v4.json` 的 `inputs` 增必填 `coverage_pointer{path,size,sha256}` 并写当前性深验不变量；`composition_rules.json` 增"coverage 当前性"条。
- **E10**：`publish_protocol.json` 与 `sqd-solana-repair-pointer_v1.json` 增同 gid 幂等分支（条件＋行为＋`idempotent-republish`）；探针指针同构（probe_id）写入 `sqd-solana-coverage-pointer_v1.json`。
- **E11**：`solana-reconcile_v4.json` 的 `verdict/exit_code` 字段 constraints 改为明确映射（gate_pass true⇒PASS/0，false⇒FAIL/2，finalize_envelope 强制，三者互洽）。
- **E12**：`reconciliation-report_v3.json` 改为**单层** `checks{<key>}` ＋ 顶层 `family`（由 target 推导）决定键集；删除 `checks.evm/checks.solana` 嵌套写法。
- **E13**：不涉及契约 JSON（先红写法归批 1b），但 `INDEX.json` 的 notes 记一句"先红写法见 errata E13"。
- **E3**：已被 E9 取代，`sqd-solana-coverage-pointer_v1.json` notes 注明"E3 表作废、以 E9 为准"。
- **E4/E5/E7 前移（三张继承表抄录，附源码行号，禁止臆造）**：
  - `sqd-solana-cache_v4_repaired-meta.json` 增 `inherited_fields`：从 `scripts/solana/fetch_sqd_transfers_v2.py` 写出 v4 meta 的代码处抄录**全部字段名**（每字段附 `source_line`），并标注哪些字段在 repaired meta 中取值"同 base"/"生产者重算"/"差异字段（4.2.6）"。
  - `solana-reconcile_v4.json` 增 `inherited_fields`：从 `scripts/solana/replay_edges.py` 的 `cmd_reconcile` 写出 v3 receipt 的代码处抄录**全部键**（附 `source_line`），并把 4.2.8 新增键另列 `added_fields`；唯一删除项（不再回写 base meta）写入 notes。
  - `reconciliation-report_v3.json` 增 `inherited_fields`：从 `scripts/report/reconciliation_report.py` 的 `_base_wrapper` 及其后续填充处抄录 v2 外壳**全部键**（附 `source_line`），`added_fields` 列 `family` 与 schema 升版。
- 全部草案 `draft_status` 改为 `"batch1-frozen"`；`INDEX.json` 增 `errata{file:"PLAN_errata_batch0.md", sha256}`、`final_review{file:"batch0_final_review_codex.txt", sha256}`（实测 sha256），`plan_sha256` 不变。

### B. 自检（写进 done）
- 每份 JSON `python3 -m json.tool` OK；八键结构；`fields` 五键齐全且字段名无重复；INDEX 与文件一一对应。
- 「errata 条 → 文件 → 字段/不变量」对照表 E1–E13 逐条（E13 标"不适用于 JSON"）。
- 三张继承表的源码行号可复核（`sed -n` 命令写进 done）。
- 「发现项」：抄录中发现现役实现与 PLAN/errata 冲突之处（只记录、不改）。
- 「未做」与白名单自述。

## 完成标准
九份必改文件全部落地、三张继承表带行号、全部 JSON 可解析、INDEX 更新、done 报告齐全。完成即停。
