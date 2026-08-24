# 批 0 验收记录（Fable，2026-08-23）

- 工单：`batch0_workorder.md`；施工方：codex（companion task-mt5szylv-4jt0tc，后台 11 分钟，哨兵终态 completed 双确认）；汇报件：`batch0_done.md`。
- 验收方式：只看产物与机器检查，不读施工过程。

## 机器检查（全部通过）
| 项 | 结果 |
|---|---|
| 白名单 | `git status` 仅 `.gitignore`（Fable 本人加 `.staging_*/` 一行）＋本目录新文件；无既有文件改动 |
| PLAN.md 正文 | frontmatter 11 行（验收后加 1 行 errata 指针→12 行）；`tail -n +13 PLAN.md \| shasum -a 256` = `506cdcbe…ad93` == 已批准计划 r7.1 原文 |
| TSV 副本 | `arc_evidence_hashes.tsv` `18cf82c1…e3c5`、`arc_routeA_blocks_hashes.tsv` `698d5f0b…00f4`，与 `.staging_b0/STAGING_SHA256.txt` 一致 |
| JSON | 17 份 contracts_draft ＋ manifest 共 18 份 `python3 -m json.tool` 全 OK |
| 契约抽查 | `canonicalization.json`、`composition_rules.json` 字段/不变量与 PLAN §4.2.0／§4.1／§4.4.3 一致 |
| manifest 数值 | 83＝20＋61＋0＋2；blocks 6,759 文件 2,096,692,855 bytes；与 Fable 本机 shasum 脚本输出一致 |
| 自指项（发现项 8） | `batch0_done.md` 9,950 bytes，sha256 `64b3aba836a666cac9e8cb76ab69d7312a2b735430e4430a58d8e4ea128181d3` |

## 发现项裁定
codex 报告 §6 发现项 1–7 经 Fable 按原文行号逐条核对**全部属实**，裁定见 `PLAN_errata_batch0.md`（E1–E7；PLAN 正文不改，冲突处以 errata 为准，批 1 契约冻结按 errata 修订四份草案并给三份加 note）。

## 结论
批 0 产物**验收通过**，作为设计冻结件提交；下一步＝codex 只读终审（批 1 准入闸）。
