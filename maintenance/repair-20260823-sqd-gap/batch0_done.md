# 批 0 完成报告

- 工程：`repair-20260823-sqd-gap`
- 基线：`main=f06078e`（`VERSION=6.51.0`）
- 模式：离线、仅新建白名单产物、不 commit
- 完成日期：2026-08-23
- 结论：批 0 冻结件已落盘并通过本报告所列机械验收；完成即停。

## 1. 开工门禁

执行命令：

```sh
cd .staging_b0 && shasum -a 256 -c STAGING_SHA256.txt
```

| 输入 | `STAGING_SHA256.txt` 期望值 | 实测值 | 结果 |
|---|---|---|---|
| `plan_r7_1.md` | `506cdcbe7938ad6e79eb539e793fa0f47081426f3f21d7dada404cb021a9ad93` | `506cdcbe7938ad6e79eb539e793fa0f47081426f3f21d7dada404cb021a9ad93` | OK |
| `arc_evidence_hashes.tsv` | `18cf82c1d7ab9f00694c0d19a3818256a8f67cb1eabbae51704843488160e3c5` | `18cf82c1d7ab9f00694c0d19a3818256a8f67cb1eabbae51704843488160e3c5` | OK |
| `arc_routeA_blocks_hashes.tsv` | `698d5f0b7df7e6230a94221da52ca9e9b85848f0246189c22075c1f24d4800f4` | `698d5f0b7df7e6230a94221da52ca9e9b85848f0246189c22075c1f24d4800f4` | OK |

原始输出：

```text
plan_r7_1.md: OK
arc_evidence_hashes.tsv: OK
arc_routeA_blocks_hashes.tsv: OK
```

门禁全部通过后才开始落盘。

## 2. PLAN.md 正文哈希实证

YAML frontmatter 共 11 行，计划原文从第 12 行开始。执行：

```sh
tail -n +12 maintenance/repair-20260823-sqd-gap/PLAN.md | shasum -a 256
```

输出：

```text
506cdcbe7938ad6e79eb539e793fa0f47081426f3f21d7dada404cb021a9ad93  -
```

另执行字节级比较：

```sh
cmp <(tail -n +12 maintenance/repair-20260823-sqd-gap/PLAN.md) .staging_b0/plan_r7_1.md
```

结果：rc=0，正文逐字节一致。

两份 TSV 副本也分别执行 `cmp`，均 rc=0；副本 sha256 与门禁值一致。

## 3. 产物清单

以下为 `batch0_done.md` 写入前已冻结的全部其他本批新建产物：

| 文件 | bytes | sha256 |
|---|---:|---|
| `PLAN.md` | 85195 | `0a306b5f32651fc5e63d7ae81d1da3b0e4165b82a72cef736fda035feadde059` |
| `arc_evidence_hashes.tsv` | 14807 | `18cf82c1d7ab9f00694c0d19a3818256a8f67cb1eabbae51704843488160e3c5` |
| `arc_evidence_manifest.json` | 11143 | `edc8a87a679e27ba23ef632c66bc576e845fda6bcc7f4c5a4db9dbfb6dcb8f24` |
| `arc_routeA_blocks_hashes.tsv` | 867885 | `698d5f0b7df7e6230a94221da52ca9e9b85848f0246189c22075c1f24d4800f4` |
| `contracts_draft/INDEX.json` | 2397 | `523519e96b4fad3350f3e4c8fb310b73e85951f4e8a4e6654ab9e0565925f6f0` |
| `contracts_draft/canonicalization.json` | 4168 | `c5d2449a62291c8440020de446eedc04df1c363444b619df2533aa2fd39d242a` |
| `contracts_draft/composition_rules.json` | 2903 | `9adf8475d01df807f50a4951730a8baf391f2c8f55194da3427ad65ff7098166` |
| `contracts_draft/edge_source_binding.json` | 1401 | `3b4b00864237d6295f094b8937915814f8e04ccf4a1ff3bdda1b3ae73f9b4a70` |
| `contracts_draft/evidence_tables.json` | 5483 | `9aed9fdb6d32c4b68053d9f907dbbdbc816d78608306de56d8d91433016458e0` |
| `contracts_draft/publish_protocol.json` | 2883 | `c09e9b055abd035b77de5af0906e516efe94cba4f12186f1d4d4e0cac8ed3084` |
| `contracts_draft/reconciliation-report_v3.json` | 2447 | `c19cc9b07f30b9b37d6f21fadab42e20a025c9ca554ebd9a28ecc623b6a39abf` |
| `contracts_draft/rpc_ledger.json` | 2356 | `042a2b080b3d926070ddd1cb8dc60503bc0da767e41ea91d3996121cfbf90d2c` |
| `contracts_draft/solana-reconcile_v4.json` | 10139 | `849378365c8457ef9a8a5ee4e5354d9e0c5f415c3f99ac1673e9a3281b109dd3` |
| `contracts_draft/sqd-solana-cache_v4_repaired-meta.json` | 3616 | `1c559eacdd142d73c7ee9c40ca2ff22fcb8474c0a21d7eb78e75433b062a9e11` |
| `contracts_draft/sqd-solana-coverage-pointer_v1.json` | 791 | `821e766f1deb79d162a08ce3a8022814c44c22ac24e7593b5ca444d78da592f3` |
| `contracts_draft/sqd-solana-coverage-resolution_v1.json` | 4360 | `118f7595a6d8b0f5666e953da32a7322293416f6798aeb5cafc5f9401fb2a72c` |
| `contracts_draft/sqd-solana-coverage_v1.json` | 11684 | `c07e99d9666b74f963ce00e0d449bf21792a6ed40c6eb0d9cb3240fc33e86ca0` |
| `contracts_draft/sqd-solana-repair-bundle_v1.json` | 10347 | `e2442827e9188147a879f12a45ee809328afdac0a4ee22b821f258dcc28d62db` |
| `contracts_draft/sqd-solana-repair-layer_v1.json` | 3699 | `fbbcfde538bca551a0e5a0d4aaf2b0f6a54447e5cf3d3170d45f594c86cfa651` |
| `contracts_draft/sqd-solana-repair-pointer_v1.json` | 3003 | `469f72056025cefcd7307d9056b4aaaefb328623726517837584009cc8156308` |
| `contracts_draft/sqd-solana-slot-index-map_v1.json` | 1644 | `52ce26efa29a900b932cecd006e1330017ad0ff54711556355bed24dca63123d` |
| `batch0_done.md` | 见本文件外部终验 | 见本文件外部终验 |

`batch0_done.md` 无法在自身正文内稳定内嵌自己的最终大小与 sha256：写入该值会再次改变文件本身。最终值应由验收方对完成后的本文件直接执行 `wc -c` 与 `shasum -a 256`；施工方也在最终终验/聊天交接中报告。

## 4. JSON 解析与结构核验

逐文件执行：

```sh
python3 -m json.tool <file> >/dev/null
```

结果：

| JSON | 结果 |
|---|---|
| `arc_evidence_manifest.json` | OK |
| `contracts_draft/INDEX.json` | OK |
| `contracts_draft/canonicalization.json` | OK |
| `contracts_draft/composition_rules.json` | OK |
| `contracts_draft/edge_source_binding.json` | OK |
| `contracts_draft/evidence_tables.json` | OK |
| `contracts_draft/publish_protocol.json` | OK |
| `contracts_draft/reconciliation-report_v3.json` | OK |
| `contracts_draft/rpc_ledger.json` | OK |
| `contracts_draft/solana-reconcile_v4.json` | OK |
| `contracts_draft/sqd-solana-cache_v4_repaired-meta.json` | OK |
| `contracts_draft/sqd-solana-coverage-pointer_v1.json` | OK |
| `contracts_draft/sqd-solana-coverage-resolution_v1.json` | OK |
| `contracts_draft/sqd-solana-coverage_v1.json` | OK |
| `contracts_draft/sqd-solana-repair-bundle_v1.json` | OK |
| `contracts_draft/sqd-solana-repair-layer_v1.json` | OK |
| `contracts_draft/sqd-solana-repair-pointer_v1.json` | OK |
| `contracts_draft/sqd-solana-slot-index-map_v1.json` | OK |

附加结构核验：16 份契约草案均具备统一八键结构；每个 `fields` 项均具备 `name/type/required/description/constraints` 五键且字段名无重复；`INDEX.json` 有 16 个条目并与 16 个契约文件的文件名、schema、source 逐项一致。因此契约目录共有 16 份草案＋1 份 INDEX＝17 份 JSON。

## 5. ARC manifest 对表核验

- `arc_evidence_hashes.tsv`：116 数据行。
- `arc_routeA_blocks_hashes.tsv`：6,759 数据行。
- manifest 内 43 个互异 `{rel_path,size,sha256}` 对象全部逐项命中 general TSV。
- 修复边行数：20＋61＋0＋2＝83。
- Helius blocks：6,759 文件，合计 2,096,692,855 bytes。
- `by_dir`：425＋6,146＋129＋52＋7＝6,759。
- 所有统计均使用整数；未访问 ARC 案目录，未改 TSV 数字。

## 6. 发现项

以下只记录，不修正 PLAN 正文：

1. `plan_digest` 文件清单冲突：PLAN 第 142 行规定 evidence/*、evidence_manifest、merged 边文件不含 `plan_digest`；第 162 行发布步骤却把 evidence/evidence_manifest/merged 边等概括为“各文件含 plan_digest”。契约草案在 canonicalization 中按第 142 行的“统一规定”列清单，在 publish_protocol 中保留第 162 行动作原话并加 notes，不替计划裁决。
2. getBlocks `complete` 口径前后不完全一致：PLAN 第 103 行把“数组严格递增唯一且属于 `[from,to]`”列入机械 complete；第 149 行的离线机械派生合取式未包含这两项，并称其为生产时断言记录。草案同时保留 `array_monotonic_unique` 字段、离线合取式和该歧义，不自行补条件。
3. coverage 指针字段表不完整：PLAN 第 152 行只明确 `CURRENT.json` 为 `sqd-solana-coverage-pointer/v1`、PASS、锁内发布，未逐字段给出其余 kernel receipt 字段。草案只列已明示的 `schema` 与 `verdict`，未套用 repair pointer 字段。
4. repaired meta 继承边界未完全展开：PLAN 第 175 行写“与 base v4 meta 同契约”，但本计划小节未列出 base v4 meta 的完整字段表。草案逐项列出该行明示字段，并在 notes 标记其他继承字段未展开。
5. reconcile v4 继承边界未完全展开：PLAN 第 181 行写“在 v3 字段全保留基础上”，但本计划小节未列出 v3 完整字段表。草案逐项列出新增/明示字段，未自行猜补 v3 字段。
6. RPC ledger 的 resume 绑定来源不明确：PLAN 第 187 行逐行字段对象不含 `plan_digest`，同一行却规定 `--resume` 以 `(plan_digest, params_digest, result_sha256)` 判断已完成。草案没有把 `plan_digest` 擅自加入逐行字段，只在 notes 记录此点。
7. wrapper v3 完整外壳未逐字段展开：PLAN 第 228–230 行明确家族键集、统一 v3、`--reseal` 与 exact_reconcile 分支检查，但未给 `reconciliation-report/v3` 完整外壳字段表。草案只结构化这些明确内容；`family` 类型标为推断。
8. 工单要求产物清单含每个文件的大小/sha256，而清单本身位于 `batch0_done.md`；本文件无法稳定内嵌自己的最终哈希，这是自指约束。未新增白名单外 sidecar，改由完成后的外部终验报告本文件值。

## 7. 未做

- 未写或修改任何生产代码。
- 未写或修改任何测试。
- 未修改 PLAN 正文。
- 未访问 ARC 案目录，未联网，未读取或写入 API key。
- 未修改 `VERSION`、`pyproject.toml`、`SKILL.md`、参考文档或既有 manifest。
- 未运行批 1 施工、测试或发布流程。
- 未 commit，未 push。
- 未做任何顺手优化。

## 8. 工时与白名单自述

- 本批实际施工约 10 分钟（含门禁、字段映射、生成、解析及交叉核验）。
- 只在 `maintenance/repair-20260823-sqd-gap/` 内新建工单白名单文件。
- 开工前已存在的 `maintenance/repair-20260823-sqd-gap/batch0_workorder.md` 未修改。
- 开工前工作区已存在 `.gitignore` 修改；本批未触碰该文件，也未触碰目标目录外任何既有文件。
- 未创建仓库内辅助脚本、临时文件或白名单外 sidecar。
