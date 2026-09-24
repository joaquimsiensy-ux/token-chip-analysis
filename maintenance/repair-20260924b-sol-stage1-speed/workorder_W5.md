# 工单 W5（v2）：收官 review P2/P3 文档修正（find-known-map 异常分支采纳纪律＋CHANGELOG 9.2.0 归并最终验收）—— 纯文本，不升版本

> v2 变更：吸收 `review_W5_reply_r1.md` 三条必改——①W4 对照结论按 fable_probes P3 写准三个比较关系；②§2.2/§2.3 补"合法 JSON"前提与"其余先处理错误"；③§0.7 规定测试临时目录保留、禁自动删除（与 §0.6 禁批量删除一致）；另完成报告写全路径。
> 出处：`review_final_reply_r1.md`（收官 review PASS，P2＝执行文档未限定"只有 exit 0 才能采用 chosen"，与 `_find_known_map` 扫描级故障 exit 1 仍保留非空 chosen 的程序契约不一致；P3＝CHANGELOG 9.2.0 四条仍是施工期"待验收"状态）。
> 事实（调度方本机亲核，基线 `ef20dd825a0f3698bee79b6adfae59befcf6285d`）：`references/split-run.md:41` 尾部含 W2 追加句；`commands-staging/token-analyze-1.md:12` 尾部含 W2 追加句；`assets/sqd-solana-coverage-map/README.md:5` 为 W2 追加段；`CHANGELOG.md:108-110` 为 9.2.0 改法／字节与测试／成本-质量指标三条；`references/data-pipeline-solana-capture.md` 不含 find-known-map 采纳句（不改）。W2 工单 §2.1 已定契约：仅 exit 0 可采用 chosen；仅 exit 2 且合法 JSON 中 chosen=null 才按无图 `--full`；其他先处理错误、不得采用 exit 1 的部分结果。fable_probes_20260924.md P5：W3 联网单 slot 对照 identity 4,516,539 B / compressed 736,729 B，gzip，规范化结果 sha 相同；P3：W4 合并查询对照（probe-only／census-only／combined 三种查询）：header 三方全等；transactions combined 与 census-only 两方全等；instructions combined 与 probe-only 两方全等。

## 0. 纪律
- 0.1 工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`；固定 `W5_BASE=ef20dd825a0f3698bee79b6adfae59befcf6285d`；开工贴 `git status --short`（空）、`git rev-parse HEAD`、`git merge-base --is-ancestor "$W5_BASE" HEAD`（exit 0）、`git diff --quiet "$W5_BASE" HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets`（exit 0）。不符停工。
- 0.2 禁读同 W1 §0.2（`~/.codex/`、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、本目录以外的 maintenance、Desktop、Documents；含子进程）。
- 0.3 **白名单**：`references/split-run.md`（仅 `:41` 一行内的指定片段）、`commands-staging/token-analyze-1.md`（仅 `:12` 指定片段）、`assets/sqd-solana-coverage-map/README.md`（仅 `:5` 指定片段）、`CHANGELOG.md`（仅 `:108-110` 三条内的指定片段）、完成报告 `maintenance/repair-20260924b-sol-stage1-speed/W5_done.md`。
- 0.4 **不改**：任何 `scripts/`、`SKILL.md`、`VERSION`、`pyproject.toml`、CHANGELOG 索引 `:13` 与其他版本段、`references/data-pipeline-solana-capture.md`、资产数据文件、仓库外 commands。**版本保持 9.2.0**（尚未发布，纯文档修正不升版）。
- 0.5 每处替换以 §2 给出的**旧片段整段** `grep -n -F -e "<旧片段>"` 定位（各恰 1 处，行内片段不必 `-x`）；替换为新片段；不得改动同行其他文字。
- 0.6 离线、不 commit/push、禁 stash/checkout/reset、不建 worktree；测试用系统 tempfile；禁止批量删除。
- 0.7 定向：`test_g3_docs_guards.py`、`test_review_scale_guards.py`、`test_sqd_coverage_probe.py`、`test_exemption_guards.py`（均须 exit 0）。这些测试默认用 `TemporaryDirectory()`，退出时会 `rmtree`；为与 §0.6 一致，须在内存运行器中（`python3 -B -c`，`PYTHONDONTWRITEBYTECODE=1`）以 `patch.object(tempfile.TemporaryDirectory, "cleanup", lambda self: None)` 或等价方式禁用自动删除、保留目录并在报告记录路径；不修改测试源码、断言或判定，不扩展写白名单；`test_commands_deploy_sync.py` 预期 FAIL（staging 改后待调度方同步本机，报告如实写）；`docs_lint.py`/`changelog_lint.py` 读禁区交调度方。

## 1. 硬约束
- 1.1 references 本单净增 ≤260 B、commands ≤140 B、资产 README ≤160 B（UTF-8，以 `"$W5_BASE"` 比较，`wc -c`）；CHANGELOG 三条只做语义归并，不新增待办、不预填未发生的 PASS。
- 1.2 `git diff --stat "$W5_BASE" -- . ':!maintenance'` 只含 0.3 白名单四文件。

## 2. 逐条施工（旧片段 → 新片段，逐字）
- 2.1 `references/split-run.md:41`：
  旧：`chosen 非空必用 `--known-map <chosen.path>`；扫描正常且 chosen=null 才用 `--full`，记非阻断 INFO。`
  新：`**仅 exit 0** 才采用 chosen 并必用 `--known-map <chosen.path>`；**仅 exit 2 且合法 JSON 中 chosen=null** 才用 `--full`，记非阻断 INFO；exit 1（扫描级故障，即便 chosen 非空）或无合法 JSON 一律先处理错误，不得采用部分结果。`
- 2.2 `commands-staging/token-analyze-1.md:12`：
  旧：`有 chosen 必带 --known-map；`
  新：`仅 exit 0 才采用 chosen 并带 --known-map；仅 exit 2 且合法 JSON 中 chosen=null 才全扫；其余先处理错误；`
- 2.3 `assets/sqd-solana-coverage-map/README.md:5`：
  旧：`有 chosen 必用 --known-map，完整加载失败时按探针规则回退。`
  新：`仅 exit 0 才采用 chosen 并用 --known-map；仅 exit 2 且合法 JSON 中 chosen=null 才全扫；其余先处理错误，不得采用部分结果。完整加载失败时按探针规则回退。`
- 2.4 `CHANGELOG.md:108`（改法）：
  旧：`WR-b 探针最终 sha 登记待调度方执行，本单未登记。`
  新：`probe 两协议登记 d4adc0c8…（WR-b），旧 c4980c98… 保持 ACTIVE。`
- 2.5 `CHANGELOG.md:109`（字节与测试）：
  旧：`docs_lint.py、changelog_lint.py、run_all.py 待调度方本机验收，不记 PASS；WR-a 报告中 probe 两协议未登记失败留待 WR-b。`
  新：`调度方本机：docs_lint/changelog_lint PASS；run_all 150/151（唯一红＝test_stage2_reseal 验收 worktree 缺失，环境项）；producer 登记守卫 0 FAIL；WR-a/WR-b 真实入口验收 PASS（[WR-a_formal_entry.md](maintenance/repair-20260924b-sol-stage1-speed/WR-a_formal_entry.md)、[WR-b_formal_entry.md](maintenance/repair-20260924b-sol-stage1-speed/WR-b_formal_entry.md)）；收官 review PASS（P0/P1 空，P2/P3 已按 W5 修正）。`
- 2.6 `CHANGELOG.md:110`（成本-质量指标）：
  旧：`W3 压缩联网验收及 W4 合并查询线上实测未记录，待调度方补录；`
  新：`W3 联网单 slot 对照：传输字节 4,516,539→736,729（gzip，规范化结果摘要相同，fable_probes P5）；W4 合并查询对照（fable_probes P3）：header 在 probe-only／census-only／combined 三方全等，transactions combined＝census-only，instructions combined＝probe-only；完整生产链路吞吐收益未证明；`

## 3. 完成报告 `maintenance/repair-20260924b-sol-stage1-speed/W5_done.md`
首行 `# W5 完成：…`；§0.1 输出；六处 grep 定位行号与 `--numstat "$W5_BASE"`；三文件 `wc -c` 前后；§0.7 尾行（含 deploy_sync 预期 FAIL 原文）；披露禁读。
