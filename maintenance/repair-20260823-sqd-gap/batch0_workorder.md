# 批 0 工单（codex 施工）：工程档案落盘 —— SQD 覆盖闸 ＋ 修复生产者窄门（skill v6.52.0 施工前冻结件）

- 工程目录：`maintenance/repair-20260823-sqd-gap/`（本工单所在目录）
- 基线：main=`f06078e`（v6.51.0）。**本批不得改动仓库内任何既有文件**，只在本目录新建文件。
- 模式：离线（companion 沙箱不通外网，本批也不需要网络）；**不 commit**（Fable 验收后代 commit）；不得写入任何 API key（输入里本来就没有）。
- 目标对齐：本批只做"把已批准的计划与 ARC 证据哈希**原样、可核验地**落进仓库"，不做任何设计修改、不写任何代码、不改任何测试。发现计划内部有不一致之处 → **只记录到 done 报告的「发现项」**，不得自行修正计划正文。

## 0. 开工门禁（先做，不过即停工）
输入在仓库内只读临时区 `.staging_b0/`（已 .gitignore，不入库）：
- `.staging_b0/plan_r7_1.md` —— 已批准计划 r7.1 全文（用户 2026-08-23 批准）
- `.staging_b0/arc_evidence_hashes.tsv` —— ARC 案 base/快照/83 修复边/证据文件 sha256 清单（Fable 本机只读产生，116 文件）
- `.staging_b0/arc_routeA_blocks_hashes.tsv` —— ARC 案 Helius 原始块文件 sha256 清单（6,759 文件）
- `.staging_b0/STAGING_SHA256.txt` —— 上述三份的 sha256

门禁：`cd .staging_b0 && shasum -a 256 -c STAGING_SHA256.txt`（或逐个 `shasum -a 256` 比对）全部 OK 才开工；任一不符 → 停工，写 `batch0_done.md` 报告"输入校验失败"并列出实测值。

## 1. 产物白名单（全部新建，仅限本目录）
1. `PLAN.md`
2. `contracts_draft/INDEX.json` ＋ `contracts_draft/*.json`（见 §3 清单）
3. `arc_evidence_manifest.json`
4. `arc_evidence_hashes.tsv`、`arc_routeA_blocks_hashes.tsv`（从 `.staging_b0/` **逐字节复制**入库，复制后 sha256 必须与 STAGING_SHA256.txt 一致）
5. `batch0_done.md`
超出白名单的任何写入＝违规。

## 2. PLAN.md 规格
- 内容＝`.staging_b0/plan_r7_1.md` **逐字节原文**（一个字都不改、不删、不重排），顶部加 YAML frontmatter，frontmatter 之后紧接原文第一行：
```
---
project: repair-20260823-sqd-gap
title: SQD 覆盖闸 ＋ 修复生产者窄门（token-chip-analysis skill v6.52.0）
status: batch0-frozen（待 codex 只读终审 → 批 1 准入）
baseline: main=f06078e (v6.51.0)
target_version: 6.52.0
source_plan: ~/.claude/plans/codex-id-019ff65c-98f8-71a0-a73c-102b53-quizzical-zebra.md (r7.1, user-approved 2026-08-23)
source_plan_sha256: 506cdcbe7938ad6e79eb539e793fa0f47081426f3f21d7dada404cb021a9ad93
frozen_at: 2026-08-23
note: 正文为计划原文逐字节落盘；frontmatter 之后的内容 sha256 == source_plan_sha256（见 batch0_done.md 实证）
---
```
- done 报告必须给出实证：`tail -n +<N> PLAN.md | shasum -a 256` 的输出（N＝frontmatter 行数＋1）== `506cdcbe…`。

## 3. contracts_draft/ 规格（契约草案 JSON，批 1 冻结前的机器可读底稿）
每份 JSON 统一结构（缺一不可）：
```json
{
  "schema": "<协议名/版本 或 规则名>",
  "draft_status": "batch0-draft",
  "source": "PLAN.md §4.2.x（或 §4.1/§4.4.x）",
  "producer": "<生产脚本路径 或 n/a>",
  "consumers": ["<消费脚本/入口>", "..."],
  "fields": [ {"name": "...", "type": "...", "required": true, "description": "...", "constraints": "..."} ],
  "invariants": ["...", "..."],
  "notes": ["..."]
}
```
- `fields` 必须**逐字段**忠实于 PLAN.md 对应小节（字段名、类型、必填/可省略、约束原话），**不得自行增删字段或改语义**；PLAN 没写明的类型按最保守理解写（如 `"type":"string (sha256 hex)"`）并在 `notes` 说明"类型为推断"。
- 清单（15 份＋INDEX）：
  1. `canonicalization.json` —— §4.2.0：规范化 JSON 规则、整数/金额 JSON int、表排序键、`plan_digest` 定义、`gid` 定义、**无环绑定依赖图**（按顺序列出节点与边）、"必须含 / 不含 plan_digest 的文件清单"。
  2. `sqd-solana-coverage_v1.json` —— §4.2.1 `coverage_map.json`（含 `slot_counts` 编码、`skipped_confirmation` 子结构与 `complete` 机械派生条件、`shared_map`、`ledger`、`verdict` 三值＋"展示值须重算"）。
  3. `sqd-solana-coverage-pointer_v1.json` —— §4.2.1 探针 `CURRENT.json`（kernel PASS 收据）。
  4. `sqd-solana-repair-layer_v1.json` —— §4.2.2（header 字段＋每行交易字段＋edges 7 元组语义＋唯一键 signature）。
  5. `sqd-solana-repair-bundle_v1.json` —— §4.2.3 `bundle.json` 字段表＋恒等式。
  6. `sqd-solana-repair-pointer_v1.json` —— §4.2.3 `CURRENT.json`（字段＋CAS 条件）。
  7. `publish_protocol.json` —— §4.2.3 发布协议九步、崩溃恢复三段、代的生命周期（用 `fields` 记步骤编号/动作/持久化要求，`invariants` 记 CAS/幂等/作废规则）。
  8. `sqd-solana-coverage-resolution_v1.json` —— §4.2.4（含 census 行字段、四种 result、有效 verdict 重算规则）。
  9. `evidence_tables.json` —— §4.2.5（`<slot>.sqd.json` / `<slot>.ref.json` / `evidence_manifest.json` 三张表）。
  10. `sqd-solana-cache_v4_repaired-meta.json` —— §4.2.6（与 base v4 meta 同契约＋差异字段；明确"不含 gid、不含 bundle 哈希"）。
  11. `sqd-solana-slot-index-map_v1.json` —— §4.2.7。
  12. `solana-reconcile_v4.json` —— §4.2.8（envelope 字段、inputs 键、base 模式省略键、`edge_source_binding`、CLI 新旗标、不再回写 base meta）。
  13. `edge_source_binding.json` —— §4.2.9（字段＋承载产物与升版 wave-scan/v5、flow-anomaly/v3＋"在场或被引用即强制绑定并验证"规则）。
  14. `rpc_ledger.json` —— §4.2.10。
  15. `composition_rules.json` —— §4.1 A2.1 ＋ §4.4.3：cache_kind × 有效 verdict 组合合法性、INCONCLUSIVE 一律 FAIL、`--as-of-slot == 快照 slot == finalized_upper_slot`、coverage 强制输入条件、止损纪律（β≤3/残差不降即停/禁 BFS）、配额停工（§4.4.6）。
  16. `reconciliation-report_v3.json` —— §4.4.4：家族键集（EVM 四项/Solana 五项 `exact_reconcile`）、wrapper 一律 v3、`--reseal` 条件、`validate_reconciliation_check` 的 exact_reconcile 分支检查项。
  17. `INDEX.json` —— `{ "schema":"contracts-draft-index/v1", "plan_sha256":"506cdcbe…", "files":[{"file":..., "schema":..., "source":...}, ...] }`。
- 全部 JSON 须能被 `python3 -m json.tool` 解析；UTF-8；`ensure_ascii=False` 风格（中文原样）。

## 4. arc_evidence_manifest.json 规格
从两份 TSV 整理（不得改数字），结构：
```json
{
  "schema": "arc-evidence-manifest/v1",
  "case": {"token":"ARC","chain":"solana","mint":"61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump","case_root":"~/Documents/5.6筹码分析/ARC分析"},
  "generated": {"by":"Fable 本机只读 shasum（脚本 arc_hash_manifest.py）","date":"2026-08-23","note":"仅记路径/size/sha256，未复制任何内容；路径相对 case_root"},
  "staging_inputs": {"arc_evidence_hashes.tsv": {"rows": <数据行数>, "sha256": "<STAGING_SHA256.txt 值>"}, "arc_routeA_blocks_hashes.tsv": {...}},
  "base_cache": {"edges": {"rel_path","size","sha256"}, "meta": {...}},
  "legacy_non_formal": {"note":"codex 08-18 owner-correction 旧产物，非正式、不可消费，仅存档", "txaware_repaired_edges": {...}, "txaware_repaired_meta": {...}},
  "snapshot": {"holders_owners": {...}, "holders_snapshot_meta": {...}, "holders_accounts": {...}},
  "reconcile_state_before_repair": {"reconcile_receipt": {...}, "replay_final_balances": {...}, "residual_profile": {...}, "anomalies": {...}},
  "repair_edges_83": {"pilot": {..., "rows": 20}, "full": {..., "rows": 61}, "extra_gaps": {..., "rows": 0}, "hunt_remaining": {..., "rows": 2}, "all_repairs_done": {...}, "total_rows": 83},
  "root_cause_evidence": {"findings_md": {...}, "dense_map_final": {...}, "sqd_probe_ledger": {...}, "sqd_census": [ ... 4 份 ... ], "stage_files": [ ... stage1~7 ... ], "nonce_window_scan": {...}, "helius_full_blocks": {"count": <n>, "bytes": <n>}},
  "acceptance": {"fable_indep_after_check": {...}, "fable_baseline_replay_log": {...}, "shadow_manifest": {...}, "shadow_reconcile": {...}, "shadow_report": {...}},
  "hunt": {"bisect_result": {...}, "continuity_result": {...}, "bracket_nonce_probe": {...}, "header_vs_nonce_classification": {...}},
  "rpc_ledgers": {"diagnosis_rpc_ledger": {...}},
  "helius_blocks": {"file_count": 6759, "total_bytes": <sum>, "list": "arc_routeA_blocks_hashes.tsv", "list_sha256": "<值>", "by_dir": {"routeA_pilot/blocks": n, "routeA_full/blocks": n, "routeA_full/extra_gaps/blocks": n, "routeA_full/hunt_remaining/blocks": n, "sqd_query_variants/helius_full_blocks": n}},
  "all_general_files": "arc_evidence_hashes.tsv（116 文件全量清单，见同目录）"
}
```
- 每个 `{...}` 都是 `{"rel_path":..., "size":<int>, "sha256":...}`，值**必须**从 TSV 原样取；`rows` 以 TSV 中 repair_edges 文件的行数为准（20/61/0/2 已在 ALL_REPAIRS_DONE.json 自记，与 TSV 大小一致；你只需照 PLAN §1.2 与本工单填，不需要也不能访问案目录——沙箱读不到）。
- `helius_blocks.by_dir` 与 `total_bytes` 从 blocks TSV 统计。

## 5. batch0_done.md 规格（汇报件）
- 输入校验结果（三份 sha256 实测 vs STAGING_SHA256.txt）
- PLAN.md 正文 sha256 实证命令与输出
- 产物清单（文件、大小、sha256）
- `python3 -m json.tool` 对每份 JSON 的解析结果（OK/失败）
- 「发现项」：落盘过程中发现的 PLAN 内部不一致/歧义/字段表前后冲突（只记录、附 PLAN 行号引用，不修正）
- 「未做」：明确写出本批没有做的事（不写代码、不改测试、不 commit）
- 工时与是否触碰白名单外文件（自述）

## 6. 完成标准
白名单文件齐全；PLAN.md 正文哈希实证通过；17 份 JSON 全部可解析且 `fields` 与 PLAN 对应小节逐字段一致；manifest 数值与 TSV 一致；两份 TSV 入库副本哈希一致；done 报告齐全。**完成即停**，不做任何"顺手优化"。
