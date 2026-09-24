# W2 完成：共享地图轻筛、−1 开工纪律及 9.2.0 登记已施工，六项离线检查通过

本单按 W2 v3.2 完成白名单内施工。未触发停工条件；未 commit、push。WR-b 探针登记、仓库外 commands 同步及本机全量验收留给调度方。

**§0.1 开工核验**

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。

```text
W2_BASE=97e888df0a5cfeb88a0b94285475c8845d7aac40
$ git status --short
（空，exit 0）
$ git rev-parse HEAD
b268582a05b9acd65f86decb764b9eef8fef556b
$ git merge-base --is-ancestor "$W2_BASE" HEAD
（空，exit 0）
$ git diff --quiet "$W2_BASE" HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets
（空，exit 0）
$ git merge-base --is-ancestor cc6298b HEAD
（空，exit 0）
```

六处整行锚均以 `grep -n -F -x -e "<整行>"` 重核，分别唯一命中 split-run:41、commands:12、capture:202/:107/:198、资产 README:3。W1_done.md 已提供 invariant_scan 通过及探针消费者仅 shared-map 的前置证据，本单未修改 manifest。

**施工结果与边界**

- 新增 `find-known-map --from-slot N --to-slot M [--search-dir DIR]...`：默认资产目录独立于 cwd，追加目录及候选 resolve 去重，只扫描直接子文件；校验 JSON、TTL、元数据、二进制路径与大小、候选/驳回成员、W1 来源证据、canary 和查询模板。只 stat 二进制，不读内容、不重算其摘要、不解压、不逐 slot 分类。
- 按交集 slot 数、交集驳回数、UTC 发布时间降序，再按绝对路径升序排序；输出单行固定结构 JSON。扫描级故障优先 exit 1，保留部分 accepted；正常有图 exit 0，无图 exit 2。argparse 错误为 exit 2＋stderr，没有结果 JSON。调用方只有 exit 0 可采用 chosen；只有 exit 2 且合法 JSON 中 chosen=null 才可按无图执行。
- 生产 +156/−1 行，新增私有 helper 4 个；测试 +238/−0 行，新增 find 4 组。AST 对比确认所有既有生产函数/类除 main 外不变，所有既有测试/helper 除 main 登记外不变；导出、加载、dry-run 与查询模板未改。
- 文档按指定原文更新；§2.4 三段分别为 890、192、278 B（均不含分隔空格及 LF）。资产 README 保留 W1 驳回继承段。版本升至 9.2.0，CHANGELOG 日期 2026-09-24、索引 173 B，按 W3→W1→W4→WR-a→W2→WR-b 记录，待办未写成通过。
- `git diff --check` 通过；最终仅修改十份白名单文件及本报告。producer_history、校验器、修复生产者、net.py、manifest、scan-schemas、资产数据及仓库外 commands 未修改。

**find 输出样例**

使用系统 tempfile 小资产，固定当前时间为 `2026-09-24T00:00:00+00:00`，请求范围 `[100,199]`。exit 0，stdout 实际单行：

```json
{"chosen": {"path": "/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/w2-find-example-csw8q0dv/assets/sqd-solana-coverage-map/20260901.json", "version": "20260901", "generated_at": "2026-09-01T00:00:00+00:00", "expires_at": "2026-10-01T00:00:00+00:00", "overlap_slots": 100, "overlap_ratio": 1.0, "candidate_count": 2, "refuted_count": 1}, "accepted": [{"path": "/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/w2-find-example-csw8q0dv/assets/sqd-solana-coverage-map/20260901.json", "version": "20260901", "generated_at": "2026-09-01T00:00:00+00:00", "expires_at": "2026-10-01T00:00:00+00:00", "overlap_slots": 100, "overlap_ratio": 1.0, "candidate_count": 2, "refuted_count": 1}], "rejected": []}
```

空目录样例为 exit 2、`{"chosen": null, "accepted": [], "rejected": []}`。合格地图＋模拟不可读目录返回 exit 1，保留 chosen/accepted，测试调用方不采用；缺失目录＋合格地图返回 exit 0。新增测试还覆盖 38 类非法形态、损坏 JSON/UTF-8、候选读取失败、迭代中途失败、TTL 临界点、旧图空 refuted 缺两键、多目录去重和 cwd 独立。网络、完整校验、二进制解压/读取、二进制哈希及分类均设为调用即失败的桩。

**文档 UTF-8 字节核算**

基线内容经 `git show <基线>:<文件>` 输入 `wc -c`，当前文件同样用 `wc -c`；仅读取允许文件。

| 文件 | cc6298b | W2_BASE | 完成后 | 本单净增 | 全工程净增 |
|---|---:|---:|---:|---:|---:|
| references/split-run.md | 27,422 | 27,422 | 28,064 | 642 | 642 |
| references/data-pipeline-solana-capture.md | 39,368 | 39,368 | 40,442 | 1,074 | 1,074 |
| references/scan-schemas.md（本单未改） | 106,700 | 108,815 | 108,815 | 0 | 2,115 |
| commands-staging/token-analyze-1.md | 2,261 | 2,261 | 2,382 | 121 | 121 |
| assets/sqd-solana-coverage-map/README.md | 2,761 | 6,436 | 6,601 | 165 | 3,840 |
| SKILL.md | 8,021 | 8,021 | 8,021 | 0 | 0 |

references 本单净增 **1,716 B ≤1,800 B**，全工程相对 cc6298b 净增 **3,831 B**；commands 本单及全工程均 **121 B ≤260 B**。SKILL.md 仅版本号等长替换，**8,021 B ≤8,192 B**。VERSION 与 pyproject.toml 也仅作等长版本替换。

**版本四处 grep**

```text
VERSION:1:9.2.0
pyproject.toml:15:version = "9.2.0"
SKILL.md:23:<!-- skill-version-source: VERSION; skill-version: 9.2.0 -->
CHANGELOG.md:13:- **9.2.0**（2026-09-24）Solana −1 提速：驳回继承、find-known-map 开工硬性、curl_json 压缩、修复 α 合并 SQD 请求；producer 登记，档位 次。
CHANGELOG.md:105:## [9.2.0] - 2026-09-24 — Solana −1 机械段提速
```

**§0.7 定向检查**

每个代码/文档施工点后即执行对应 find 测试、原文/字节断言或既有文档回归。下列六项均使用 `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/<文件>`，exit 0；g3 仅代表既有文档回归。

| 检查 | 实际输出尾行 |
|---|---|
| test_sqd_coverage_probe.py | `PASS SQD coverage probe: 24/24 offline groups` |
| invariant_scan.py | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| test_batch4_invariant_guards.py | `PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| test_exemption_guards.py | `PASS: exemption guards (EX-01 full-F-03)` |
| test_g3_docs_guards.py | `PASS: F-05 machine boundary` |
| test_review_scale_guards.py | `PASS: M-04 bounded helpers, streaming parquet batches, and bound input manifests` |

`docs_lint.py`、`changelog_lint.py`、`run_all.py` **未运行，待调度方验收**；未修改检查器或运行清单外测试。changelog 的局部原文/日期/字节核验不替代原版 lint。测试日志和禁读/离线拦截器位于系统 tempfile：`/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/w2-checks-h8j9u38z/`。拦截器经环境传给 Python 子进程；临时目录保留以避免批量删除，日志无禁读、网络或批量删除拦截事件。

**禁读披露与调度方收官项**

本轮未读取 `~/.codex/` 或 memories；未读取 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、Desktop、Documents 或指定目录之外的 maintenance。指定 maintenance 目录内仅读取允许文件内容。未读取 API 密钥登记文件，沙箱外部网络调用 0；未 stash/checkout/reset、创建 worktree 或批量删除。

调度方须完成：

1. 本机运行原版 docs_lint.py、changelog_lint.py、run_all.py 并记录结果。
2. WR-b 登记本单最终探针 sha256：`d4adc0c88f87bc03b3d847db7df9c9f7e588cb503734dfd977b818b581d998d8`；本单没有运行注册表测试或将过渡失败记作通过。
3. 同步 commands-staging/token-analyze-1.md 至 `~/.claude/commands/token-analyze-1.md`，记录逐字比较。
4. 按实际结果补录 W3 压缩联网验收与 W4 合并查询实测；本单没有线上收益数据。
