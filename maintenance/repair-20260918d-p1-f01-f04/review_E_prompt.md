# 工单 E 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918d-p1-f01-f04/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单E复核：通过` 或 `# 工单E复核：退回`。退回时逐条给出：编号（E-R1-NN）、工单位置、事实、修订建议。通过时列出实际核过的项。
3. 这是版本登记工单的事实核对（非攻击式验收）。工作目录＝本仓库根。

## 任务
复核 `maintenance/repair-20260918d-p1-f01-f04/workorder_E_version.md`（v1）能否原样派施工。逐项核：
a) §2 四处锚：`VERSION` 现值（含换行形态）、`pyproject.toml:15`、`SKILL.md:23` 注释行、`CHANGELOG.md:13`（索引锚）与 `:97`（详细段锚）的行号与唯一性；`9.0.0`→`9.0.1` 等长使 `SKILL.md` 字节不变（现 8021）。
b) §2.4 索引行与详细段的**每一处事实断言**对照仓库：函数名/文件名/行号/文案（`git diff 868d3f61 HEAD -- scripts` 与本目录 `ruling_20260918.md`、`code_change_pending.md` Q1–Q9、工单 F04 v2 / F01 v3、`blind_F0*_reply_r1.md`、`review_F0*_reply_r*.md`、`F0*_done.md`、`F01_done_attempt1_stopped.md`、`final_review_reply_r1.md`）；数字（两段 diff 行数 +19/−1、+59/−4；定向测试 F04 7 项、F01 6 项；`test_stage2_closeout` 30/30；reseal 21/21；run_all 151/151；复核轮次 F04 4→通过、F01 5→1→通过；盲审 F04 r1 PASS、F01 r1 PASS；停工两次原因；存量 28 文件 0 命中、0 份 price_check 收据；LAYOFF 27 处）；三处字节 930076/8021/8798 与 868d3f61 相同；九项守卫名单与 `scripts/tests/` 实际文件对应。
c) 档位理由（9.0.1 修：不改 schema/键，旧合法产物照常通过）与 CHANGELOG 头部版本规则是否相符；用户裁决原话「9.0.1」见 `ruling_20260918.md`。
d) §0/§1/§3 施工纪律是否可执行（施工者不跑 changelog_lint/docs_lint 的理由、四文件白名单、完成报告要件）。
e) 结论规则：a)–d) 无事实错误且无阻断项 → 通过；否则退回并逐条列出。
