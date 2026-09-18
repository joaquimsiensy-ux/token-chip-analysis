# 工单 E 复核提示词（只读，r2：对 v2 复核；r1 五条 E-R1-01…05 已按意见修订，档位意见已写进条目待用户追认；只需核五处修订是否闭合、与源码/施工报告事实相符、索引行与详细段仍互相一致，其余 r1 已核项不必重跑）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`（统计大小只用 stat）。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单E复核：通过` 或 `# 工单E复核：退回`。退回时逐条给出：编号（E-R2-NN）、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。
3. 这是对**版本登记文案**的复核，不是攻击式验收，也不重新评价四段施工本身。

## 任务
复核 `maintenance/repair-20260918-p0-f04-f07/workorder_E_version.md`（v2；变更点见文件头 v2 变更行与 `review_E_reply_r1.md`）。工作目录＝本仓库根（HEAD 含 F06/F04/F07/F05 四段落地）。逐项核：
a) 锚点：CHANGELOG.md :13 索引首行与 :94 详细段标题 `grep -n -F` 恰 1 处且行号一致；VERSION、pyproject.toml:15、SKILL.md:23 当前值均为 7.2.0。
b) **文案与仓库事实逐项核对**（本单重点，任何不符退回本单而非改事实）：四段施工 commit（F06 8df17dd、F04 b794325、F07 a201c63＋bf60b50、F05 332a582）各自 `git show --stat` 触及文件与文案相符；引用的函数/常量/字段名（`validate_gate`、`check_figure2_receipt`、`fig2_check_errors`、`FIGURE2_DEFAULT_TOL_PP`、`_find_peaks_dirs`、`PEAKS_DAILY_PRODUCTS`、`check_daily_peaks`、`check_facts_decimals`、`check_facts_vs_ledgers`、`derive_facts`、`gate_check`、`_f04_case_1..4`、`_r08_case_12`、`t_r08_nonfinite`）在源码中存在且行为与描述一致；测试计数（F06 三例、batch_c 249 checks、F07 用例 14–22、test_report_facts 用例 16–21、P105 a/b）与测试源码/施工报告 `F0x_done.md` 一致；字节（references 930061、SKILL 8021、commands-staging 8798，只 stat）；台账 `code_change_pending.md` 含 P1–P12 且 P8 标注待裁决；盲审轮次与 `blind_F0x_reply_r*.md` 首行一致；复核轮次与 `review_F0x_reply_r*.md` 文件数一致；迁移命令与 `scripts/evm/replay_duck.py` 参数定义一致（`--out-dir` 必填、`--only-addrs` 可重复）。
c) 版本号档位：四段是否都属 CHANGELOG 头部"修＝既定契约内的修复、加固"；`peak_overrides` 证据格式收紧、followup 绑定字段必填、decimals 必核是否构成"不兼容契约变更"须升次/主版本（给出判断与依据；如认为应改档位，作为意见列出，不阻断）。
d) 体例：索引行与详细段格式与 7.2.0/7.1.3 条目一致（日期、破折号、粗体小节、成本-质量指标）；`changelog_lint` 改后应 77 条无撞号倒排；`test_version_consistency`、`docs_lint --all` 无必红点；`SKILL.md` 字节不变。
e) 是否遗漏应登记事项；有无不该写进 CHANGELOG 的代币分析结论（红线）。
