# 批 1a 完成报告：契约草案 errata 冻结与继承字段表

## 1. 结论与施工边界

- 结果：**PASS，批 1a 已完成；完成即停。**
- 分支：`fix/sqd-gap-v6520`；未切分支、未 commit、未联网。
- 当前 HEAD：`64d9dc19adc3992a398572cf21a9bd3c600afe8e`。档案提交位于代码基线之后；三份抄录源码相对 `f06078ef0bbf6d693baf2186212c1e0a4634f578` 的 `git diff --exit-code` 为 0，故代码面仍是指定 v6.51.0 基线。
- 权威顺序：先完整读取 `PLAN_errata_batch0.md` E1–E13，再对照 `PLAN.md` §4.2/§4.4 与 `batch0_final_review_codex.txt`。
- 写入范围：仅 `contracts_draft/*.json` 与本文件。未改 PLAN、errata、代码、测试或其他文档。
- 16 份契约草案的 `draft_status` 均已冻结为 `batch1-frozen`；INDEX 不属于八键契约草案，按工单只更新索引元数据。

权威文件实测哈希：

| 文件 | sha256 |
|---|---|
| `PLAN_errata_batch0.md` | `c8f2baca9dcd8cbe08e81542d9767daa7279a0a4dd4a024532864c49466b400e` |
| `batch0_final_review_codex.txt` | `f0070ef1d6ad7436dfe8d240a7d9220b10fb61e206f77d42cea0dce25004e440` |

`INDEX.json.plan_sha256` 保持原值 `506cdcbe7938ad6e79eb539e793fa0f47081426f3f21d7dada404cb021a9ad93`，未改。

## 2. errata → 文件 → 字段/不变量对照

| errata | 文件 | 落地字段/不变量 |
|---|---|---|
| E1 | `publish_protocol.json`; `canonicalization.json` | `step_1` 改为仅 resolution、layer header、map header、merged meta 含 `plan_digest`，全部文件不含 gid/bundle 哈希；删除旧冲突 note；规范化清单保留。 |
| E2 重裁 | `sqd-solana-coverage_v1.json` | `skipped_confirmation.ranges[]` 冻结为七字段；新增 `array_in_range`；`complete` 写成 errata 的八项离线合取式；删除歧义表述。 |
| E3 | `sqd-solana-coverage-pointer_v1.json` | notes 明记“E3 字段表作废，以 errata E9 为准”；字段表按 E9 重写。 |
| E4 | `sqd-solana-cache_v4_repaired-meta.json` | 新增 `inherited_fields` 25 项，每项含 `source_line` 与 repaired 取值分类；来源为现役 v4 meta 写出点。 |
| E5 | `solana-reconcile_v4.json` | 新增 `inherited_fields` 41 项（含嵌套键）与 `added_fields` 14 项；notes 写明唯一删除的是 base meta 回写副作用，不是 receipt 字段。 |
| E6 | `rpc_ledger.json`; `canonicalization.json` | 新增首行 header 的 `schema/plan_digest/reference{kind,endpoint_fingerprint}`；resume 的 plan_digest 来源与三方相等式；必含清单新增 `rpc_ledger header`。 |
| E7 | `reconciliation-report_v3.json` | 新增 v2 外壳 `inherited_fields` 8 项和 `added_fields`（schema 升 v3、family）。 |
| E8 | `sqd-solana-coverage_v1.json`; `canonicalization.json` | `era_params` 改四个整数字段；加入整数交叉相乘判据；加入“全工程落盘 JSON 禁浮点、比率用整数分子/分母”。 |
| E9 | `sqd-solana-coverage-pointer_v1.json`; `sqd-solana-coverage_v1.json`; `solana-reconcile_v4.json`; `composition_rules.json` | 指针按 E9 全字段重写，含 `supersedes`、四项 inputs、`probe_id`；coverage 加 pending→fsync→rename→父目录 fsync→锁内 CAS→锁内 fsync 协议；reconcile 新增必填 `coverage_pointer{path,size,sha256}` 与当前性深验；组合规则加入 coverage 当前性。 |
| E10 | `publish_protocol.json`; `sqd-solana-repair-pointer_v1.json`; `sqd-solana-coverage-pointer_v1.json` | repair 同 gid 与 probe 同 probe_id 幂等分支均写明条件、行为、退出码 0 和日志 `idempotent-republish`；不满足才进入原 CAS。 |
| E11 | `solana-reconcile_v4.json` | `verdict/exit_code` constraints 与 invariant 明确 true⇒PASS/0、false⇒FAIL/2；由 `receipt_kernel.finalize_envelope` 强制并由 validator 校验三者互洽。 |
| E12 | `reconciliation-report_v3.json` | 删除 `checks.evm/checks.solana` 字段，冻结单层 `checks{<key>}`；顶层 `family` 由 target 推导并决定固定键集/顺序。 |
| E13 | JSON 契约不适用；`INDEX.json` 仅登记 | notes 已写“先红写法见 errata E13”；未写批 1b 测试。 |

## 3. 三张继承字段表

### 3.1 base v4 cache meta → repaired meta

- 文件：`sqd-solana-cache_v4_repaired-meta.json.inherited_fields`。
- 共 25 个现役顶层字段：身份 12 项、fresh meta 5 项、`dataset_scope`、finalize 补充 7 项。
- 每项含 `source_line`；repaired 取值按 `同 base`、`生产者重算`、`差异字段（4.2.6）` 标注。
- `edge_logical_sha256`、`edge_rows` 按实际动作标为“生产者重算”，notes 同时注明二者属于 §4.2.6 差异字段。

### 3.2 solana-reconcile/v3 → v4

- 文件：`solana-reconcile_v4.json.inherited_fields`。
- 共 41 项，覆盖 v3 receipt 的全部顶层键及代码直接构造的嵌套键；`_file_ref` 的 `path/size/sha256` 也逐项列入。
- `added_fields` 共 14 项，列出 schema 升版、envelope/target、边源与 coverage 绑定、E9 `coverage_pointer` 等 4.2.8 增量。

### 3.3 reconciliation-report/v2 → v3

- 文件：`reconciliation-report_v3.json.inherited_fields`。
- `_base_wrapper` 六个常驻外壳键全部列入；后续可选填充 `inputs`、`error` 也列入，共 8 项。
- `added_fields` 仅列 schema v2→v3 与新增 `family`。

源码行号复核命令：

```bash
nl -ba scripts/solana/fetch_sqd_transfers_v2.py | sed -n '521,537p;996,999p;1023,1026p;1241,1249p'
nl -ba scripts/solana/replay_edges.py | sed -n '120,123p;261,270p;292,314p;354,371p'
nl -ba scripts/report/reconciliation_report.py | sed -n '117,125p;200,209p;226,231p;268,276p'
```

## 4. 自检

| 检查 | 结果 |
|---|---|
| `python3 -m json.tool` 逐份解析 | 17/17 OK（16 契约＋INDEX） |
| 八键结构 | 16/16 均含 `schema,draft_status,source,producer,consumers,fields,invariants,notes`；三份工单授权的继承/新增表为附加键 |
| `fields` 五键 | 16/16 每项恰含 `name,type,required,description,constraints` |
| `fields[].name` 唯一 | 16/16 无重复 |
| INDEX 一一对应 | 16 个索引项与 16 个契约文件双射，schema 全相等 |
| draft status | 16/16 为 `batch1-frozen` |
| errata/final review 哈希 | 均与 INDEX 登记值一致 |
| INDEX plan digest | 与修改前值一致 |
| 落盘 JSON 实际数值类型 | 17 份均无 JSON float 值 |
| E1/E2/E6/E8–E12 语义断言 | PASS |
| `git diff --check` | PASS |
| 三份抄录源码 vs `f06078e` | `git diff --exit-code` PASS |

核心复核命令：

```bash
for f in maintenance/repair-20260823-sqd-gap/contracts_draft/*.json; do python3 -m json.tool "$f" >/dev/null || exit 1; done
git diff --exit-code f06078e -- scripts/solana/fetch_sqd_transfers_v2.py scripts/solana/replay_edges.py scripts/report/reconciliation_report.py
sha256sum maintenance/repair-20260823-sqd-gap/PLAN_errata_batch0.md maintenance/repair-20260823-sqd-gap/batch0_final_review_codex.txt
git diff --check
```

机械检查汇总输出：

```text
json_ok=17 contracts=16 core8_ok=16 fields5_ok=16 unique_names_ok=16 index_bijection_ok=16
semantic_errata_assertions=PASS
plan_sha256_unchanged=PASS:506cdcbe7938ad6e79eb539e793fa0f47081426f3f21d7dada404cb021a9ad93
source_baseline_f06078e=PASS
```

## 5. 发现项（只记录，不改代码）

1. 现役 `fetch_sqd_transfers_v2.py` 本身写出的 v4 meta 不含 `edge_file_size` / `edge_file_sha256`；这两键由当前 `replay_edges.py:312-314` 在 reconcile 时回写 base meta。它与 PLAN §4.2.6 所要求的“repaired 生产者同时写出、消费端不回写”存在明确实施差异，留待后续代码批处理。
2. 现役 v3 receipt 在 `replay_edges.py:365,369` 把 `minted_raw`、`burned_raw`、`snapshot_supply_raw` 写成字符串，而 `net_supply_raw` 是 JSON int（:366）。v4 继承键名与全工程整数口径落地时必须明确迁移类型，不能把现役字符串悄悄当成已满足新口径。
3. 现役 reconciliation wrapper 从 job spec 接受外部 `family`（`reconciliation_report.py:143-146`），且 `CHECK_KEYS` 固定四项（:19,160-162）；errata E7/E12 要求 v3 的 `family` 由 target 推导、Solana 使用五项。这是预期的后续生产代码差异，本批未改。

## 6. 未做与白名单自述

- 未改 `PLAN.md`、`PLAN_errata_batch0.md`、`batch0_final_review_codex.txt`。
- 未改任何仓库代码、测试、说明文档或 producer registry。
- 未执行批 1b 先红测试，未实现任何生产逻辑。
- 未 commit、未 push、未切分支、未联网。
- 工作树另有 `batch1a_workorder.md`、`batch1b_workorder.md` 未跟踪文件；本批未写、未删、未纳入 diff。
