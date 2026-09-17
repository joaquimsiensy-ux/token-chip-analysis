# 工单 E 复核提示词（只读，r2：对 v2 复核；r1 六条见 `review_E_reply_r1.md`——E-01 档位按批准计划保持 7.2.0 并把异议写进条目"档位说明"待用户追认（本轮只核该说明与仓库事实一致，不再争档位）；E-02 两条读 archive 的守卫归调度方；E-03～E-06 文案订正。只需确认六处处置闭合、条目与仓库事实一致、未引入新错

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容；禁读 `/Users/uravvv/Desktop` 下任何文件。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单E复核：通过` 或 `# 工单E复核：退回`。退回时逐条给出：编号、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。

## 任务
复核 `maintenance/repair-20260917-p0-four/workorder_E_version.md`（v2）。工作目录＝本仓库根（HEAD 含 A–D 四段及 C7 落地）。逐项核：
a) 锚点：CHANGELOG.md :13 索引首行与 :93 详细段标题 `grep -n -F` 恰 1 处且行号一致；VERSION、pyproject.toml:15、SKILL.md:23 当前值均为 7.1.3；`changelog_lint` 当前"活跃 75 条"。
b) **文案与仓库事实逐项核对**（这是本单重点，任何不符退回本单而非改事实）：四段施工 commit 哈希（A 212ede1、B 03507cb、C 1b317b3、C7 eca1131、D f583039）各自 `git show --stat` 触及文件与文案描述相符；引用的函数/子命令/字段/schema 名（`facts_gate.py build`、`derive_facts`、`check_facts_vs_ledgers`、`facts_vs_ledgers` record、`facts-provenance/v1`、`block-precision-followup/v1`、`replay_duck.py --only-addrs`、`needs_block_precision_file/sha256`、`expanded_economic_control_range_raw`、`build_facts_from_ledgers`、`augment_gate` 的 `balances` 参数、`_r09_case_1..13`、`followup_case`）在源码中存在；测试计数（batch_c 十例、B 十例、`test_report_facts` 15 类 34 例、stage2 record 11→12）与源码/测试输出一致；字节（references 930070→930061、SKILL 8021、commands-staging 8798，只 stat）；manifest minimum_counts 81/118/61；文档行号 report-template:212、recon:132、tiering:149 与当前内容一致；台账 `code_change_pending.md` 含 P1–P13（含 P3′/P4′）；盲审轮次（A r1 FAIL→r2 PASS、B r1 PASS、C r1 FAIL→C7→r2 PASS、D r1 PASS）与 `blind_*_reply_*.md` 首行一致；复核轮次（A 四轮、B 两轮、C 三轮＋C7 两轮、D 四轮）与 `review_*_reply_r*.md` 文件数一致。
c) 版本号档位：新公开子命令＋两个持久化 schema＋REQUIRED 集合扩展是否符合 CHANGELOG 头部"次版本＝向后兼容的新能力/持久化契约扩展"规则；facts.json 进 `NEW_ANALYSIS_REQUIRED` 使旧案 new-analysis 必红是否构成"不兼容"须升主版本（给出判断与依据）。
d) 体例：索引行与详细段格式与 7.1.3/7.1.1 条目一致（日期、破折号、粗体小节、成本-质量指标）；`changelog_lint` 改后应 76 条无撞号倒排；`test_version_consistency`、`docs_lint --all` 无必红点；`SKILL.md` 字节不变。
e) 是否遗漏应登记的事项（如 `state_source.json` 新增 `facts_inputs` 块、`identity_gate_fixture` 参数、reseal 验收路径、用户"只读复核并行"工艺）；有无不该写进 CHANGELOG 的代币分析结论（红线）。
