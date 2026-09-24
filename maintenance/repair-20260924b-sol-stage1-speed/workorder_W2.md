# 工单 W2（v1）：−1 执行者强制使用共享覆盖地图（`find-known-map` 子命令＋流程硬性＋文档）＋ 版本 9.2.0 登记 —— 本工程收官单

> 出处：用户 2026-09-24 裁决第 2 条「让 codex/opus 跑 −1 阶段时使用共享地图」。
> 事实（调度方本机亲核，基线＝W3 收官 commit，行号派工时重核）：
> ① PYTHIA 0919 案覆盖普查未带 `--known-map`：`sqd_coverage_probe.py` 只在**新任务**开始时经 `--known-map` 加载一张地图（`:1222-1224` `if not args.resume and args.known_map`），`--resume` 不支持中途换图/叠图（案卷 PYTHIA-RAW-002 与 `scripts/cross_case_coverage_reuse_review.md` 已考证）；执行者事后无法补救，只能全扫 20 h。TROLL 0905 地图当时可覆盖 PYTHIA 窗口 92%。
> ② 现役唯一入库资产 `assets/sqd-solana-coverage-map/20260827.json`（ARC 导出，`generated_at` 决定 30 天 TTL；TTL 校验在 `_load_known_map` 与 `validate_shared_map`）。案侧导出的地图散落各案 `data/shared_sqd_coverage/`，没有目录级索引或发现命令。
> ③ 流程文档：`references/split-run.md:41`（A2 段，Solana 五查与 coverage 探针）；`commands-staging/token-analyze-1.md:12`（第 3 条范围）；`references/data-pipeline-solana-capture.md:202`（共享地图生命周期段）与 `:107`（§13a 压缩实测）。`~/.claude/commands/token-analyze-1.md` 与 `commands-staging/` 逐字一致，由调度方在收官后同步（仓库外）。
> ④ 版本四处：`VERSION`、`pyproject.toml:15` `version = "9.1.1"`、`SKILL.md:23` `<!-- skill-version-source: VERSION; skill-version: 9.1.1 -->`、`CHANGELOG.md:13` 索引行与 `:104` 详细段头 `## [9.1.1] - 2026-09-24 — flow 扫描候选边物化`。`changelog_lint.py`/`docs_lint.py` 由调度方与本单定向跑。
> ⑤ producer_history（`scripts/lib/producer_history.py`）：`sqd_coverage_probe.py` 现役 `c4980c98…`（commit `cdc4f87f…`）登记于 `sqd-solana-coverage/v1`、`sqd-solana-coverage-pointer/v1`（另 `sqd-solana-shared-coverage-map/v1` 见 invariant_manifest `:631`，历史条目按实况 grep）；`sqd_gap_repair.py` 现役 `3f89aab1…`（commit `7846184f…`）登记于 `sqd-solana-cache/v4`、`sqd-solana-repair-bundle/v1`、`sqd-solana-coverage-resolution/v1`（其余协议按实况 grep `"sha256": "3f89aab1…"`）。W1/W4 收官后两脚本 sha 变化；新 sha 与其施工 commit 由调度方填入本单 v2 后再派（登记纪律：`git show <commit>:<script> | shasum -a 256` 可复算）。

## 0. 开工纪律

- 0.1/0.2/0.5/0.6 同 W1（基线派工时填入）。本目录可读：`README.md`、`workorder_W*.md`、`*_done.md`、`review_W2_reply_*.md`。
- 0.3 **白名单**：生产 `scripts/solana/sqd_coverage_probe.py`（仅新增 `find-known-map` 子命令及其解析器）、`scripts/lib/producer_history.py`（仅追加条目）；测试 `scripts/tests/test_sqd_coverage_probe.py`（仅新增 find 用例）；文档 `references/split-run.md`、`references/data-pipeline-solana-capture.md`、`commands-staging/token-analyze-1.md`、`assets/sqd-solana-coverage-map/README.md`；版本 `VERSION`、`pyproject.toml`、`SKILL.md:23`、`CHANGELOG.md`；完成报告 `W2_done.md`。
- 0.4 **不改**：`scripts/lib/solana_exact_validate.py`、`scripts/solana/sqd_gap_repair.py`、`scripts/lib/net.py`、`scripts/tests/invariant_manifest.json`、`references/scan-schemas.md`（W1 已改）、其他。
- 0.7 定向跑：`test_sqd_coverage_probe.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`test_g3_docs_guards.py`、`docs_lint.py`、`changelog_lint.py`、`test_review_scale_guards.py`。

## 1. 硬约束

- 1.1 `find-known-map` 只读、离线可测（纯文件扫描＋轻校验）；不做 `validate_shared_map` 全量重算（138M slot 逐 slot 分类耗时数分钟），文档明写「全量校验在 `--known-map` 加载时进行」。
- 1.2 文档改动只加硬性句，不重写段落；`references/` 净增 ≤ 1,800 B；`commands-staging/token-analyze-1.md` 净增 ≤ 260 B。
- 1.3 版本档位 **9.2.0**（次版本：新增子命令/字段与 producer 换代，契约向后兼容）。
- 1.4 producer_history 只追加，不改既有条目；前代 `c4980c98…`/`3f89aab1…` 保持 ACTIVE（现役已发布案继续被接受）。

## 2. 逐条施工

- 2.1 `sqd_coverage_probe.py` 新子命令 `find-known-map --from-slot N --to-slot M [--search-dir DIR]...`（默认搜索目录＝仓库 `assets/sqd-solana-coverage-map/`，相对本脚本定位）：遍历各目录 `[0-9]{8}.json`，每份轻校验：`schema` 为 `sqd-solana-shared-coverage-map/v1`、`version` 八位数字、`ttl_days==30`、`generated_at+30d > now`、`slot_counts.from_slot/to_slot` 与 `[N,M]` 有交集、三件套文件存在且 size 与 JSON 声明一致、`sqd.query_body_sha256 == sqd_query_template_sha256()`；通过者按 `(overlap_slots desc, generated_at desc)` 排序。stdout 一行 JSON：`{"chosen": {path, version, generated_at, expires_at, overlap_slots, overlap_ratio, candidate_count, refuted_count}|null, "accepted": [...同结构...], "rejected": [{path, reason}]}`；有 chosen exit 0，无 exit 2。入口接线在 `main(argv)`（锚 `    if argv and argv[0] == "export-shared-map":` 旁同款分支）。测试：临时目录三份资产（一份过期、一份不重叠、一份合格）→ chosen 正确、rejected 原因正确、无资产 exit 2。
- 2.2 `references/split-run.md:41`（锚整行以 `- **A2 全部**：EVM 四查；` 开头）末尾追加：「**Solana coverage 探针开工硬性（9.2.0）**：先跑 `sqd_coverage_probe.py find-known-map --from-slot <案起> --to-slot <冻结 slot>`（默认搜 skill `assets/sqd-solana-coverage-map/`，可 `--search-dir` 追加案侧目录）并把输出记 receipt；有 `chosen` 必须带 `--known-map <path>` 启动，禁止 `--full`；无 `chosen` 才 `--full`，并在 anomalies 记一条 INFO 说明无可用地图。探针不支持中途换图，漏带只能全扫。修复代发布（或 coverage 已为 NO_KNOWN…）后必须 `export-shared-map --repair-gid <gid>`（无代用 `--no-repair`）导出到 skill `assets/sqd-solana-coverage-map/`（导出目录由调度方 commit），供后案继承驳回。」
- 2.3 `commands-staging/token-analyze-1.md:12`（锚整行以 `3. **范围**＝A0–A2 全部＋A3 机械子层` 开头）末尾追加一句：「Solana 案 coverage 探针开工前必跑 `find-known-map`，有地图必带 `--known-map`（split-run §1.3 A2 硬性）；修复发布后必 `export-shared-map` 回填。」
- 2.4 `references/data-pipeline-solana-capture.md:202`（锚整行以 `**共享地图生命周期**` 开头）改写为含以下要点的一段（≤ 900 B，大白话）：TTL 30 天；`refuted_slots` 由修复 census 填充（W1）；后案复用地图时对 refuted slot 只做一次 SQD 重查，值相同即记 `INHERITED_REFUTED` 不进候选、不拉 Helius；SQD 值一变整图回退；refuted-only 案无修复代，其自有驳回不可导出、只能链式带出继承部分；每案修复发布后必导出回填并 commit 到 skill assets；`find-known-map` 开工必跑；残余风险＝「来源可信是前提，导出不深验源案全量证据」。`:107`（锚整行以 `- **gzip 压缩 = 21 倍**` 开头）末尾追加「（9.2.0 起 `scripts/lib/net.py::curl_json` 内置 `--compressed`，Helius getBlock 与 SQD 走该层的请求自动协商 gzip；ledger 字节/哈希均按解码后 JSON 计算不受影响）」。
- 2.5 `assets/sqd-solana-coverage-map/README.md` 首段后加「使用与回填义务」三句（find-known-map 开工必跑；有图必用；修复后必导出）；W1 已加的 `refuted_evidence` 段不动。
- 2.6 版本：`VERSION` `9.1.1`→`9.2.0`；`pyproject.toml:15`；`SKILL.md:23`；`CHANGELOG.md:13` 前插索引行（≤ 220 B）：`- **9.2.0**（2026-09-2X）Solana −1 提速四项：共享地图驳回继承（refuted_slots/INHERITED_REFUTED）、find-known-map 开工硬性、curl_json 压缩、修复 α 路径单次 SQD 请求；producer 换代登记，档位 次。`；`:104` 前插 `## [9.2.0] - 2026-09-2X — Solana −1 机械段提速` 详细段（四条：出处与裁决 / 改法（分 W1–W4）/ 字节与测试（引用四份 `W*_done.md` 的行数与测试尾行）/ 成本-质量指标（调度方填 codex 轮次；沙箱外部调用 0））。
- 2.7 `producer_history.py`：在元组末尾（锚 `)` 单行，倒数唯一）前追加：`scripts/solana/sqd_coverage_probe.py` 新 sha（commit＝W1 施工 commit）× 协议 `sqd-solana-coverage/v1`、`sqd-solana-coverage-pointer/v1`、`sqd-solana-shared-coverage-map/v1`（按现有该脚本条目的协议集合逐一对应，`grep -n '"script": "scripts/solana/sqd_coverage_probe.py"' -A3` 列出）；`scripts/solana/sqd_gap_repair.py` 新 sha（commit＝W4 施工 commit）× 现有该脚本 `3f89aab1…` 所登记的全部协议；`reason` 各写一句（9.2.0 驳回继承 / 9.2.0 α 单次 SQD 请求）。**sha 与 commit 由调度方在本单 v2 填入，施工者以 `git show <commit>:<path> | shasum -a 256` 复算一致后才写入，不一致停工。**

## 3. 完成报告 `W2_done.md`

首行 `# W2 完成：…`；§0.1 输出；find 用例输出样例；文档字节净增（`wc -c` 前后）；版本四处 grep；producer_history 复算记录；§0.7 尾行；披露禁读路径。
