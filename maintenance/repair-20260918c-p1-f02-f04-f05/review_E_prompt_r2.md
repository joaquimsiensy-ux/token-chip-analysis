# 工单 E 复核提示词（只读，r2）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单E复核：通过` 或 `# 工单E复核：退回`。退回时逐条给出：编号（E-R2-NN）、工单位置、事实、修订建议。通过时列出实际核过的项。
3. 这是版本登记工单的事实核对（非攻击式验收）。工作目录＝本仓库根。

## 任务
复核 `maintenance/repair-20260918c-p1-f02-f04-f05/workorder_E_version.md`（**v2**）是否正确消化了 `review_E_reply_r1.md` 六条意见（E-R1-01 严重级 P1×2/P2×1；R1-02 流通量分支归属 `stage2_closeout.flow_selection_errors`；R1-03 8 RED→GREEN＋1 GREEN→GREEN；R1-04 存量按 Q8 四类、ARC 引用与所指收据分述、Q9 条件、删全量概括；R1-05 F02 免迁移条件与重 build 刷新清单；R1-06 输出键 3），且未引入新错。r1 已通过的项（锚点/字节/diff 行数/轮次/测试数字/档位理由/体例）只确认 v2 未改动其实质。逐项核：
a) §2 四处锚：`VERSION` 现值、`pyproject.toml:15`、`SKILL.md:23` 注释行、`CHANGELOG.md:13`（索引锚）与 `:96`（详细段锚）的行号与唯一性；`8.0.0`→`9.0.0` 等长使 `SKILL.md` 字节不变（现 8021）。
b) §2.4 索引行与详细段的**每一处事实断言**对照仓库：函数名/文件名/文案（`git diff 8b041842 HEAD -- scripts` 与本目录 `ruling_20260918.md`、`code_change_pending.md` Q1–Q15、三份工单 v3/v3/v2、`blind_F0*_reply_*.md`、`review_F0*_reply_*.md`、`F0*_done.md`、`final_review_reply_r1.md`）；数字（三段 diff 行数 +82/−4、+144/−10、+92/−3；定向测试 14/6/11；reseal 21/21；run_all 151/151；复核轮次 F04 3→2→通过、F05 5→3→通过、F02 2→通过；盲审 F04 r1 FAIL→r2 PASS、F05 r1 PASS、F02 r1 PASS；停工两次原因）；三处字节 930076/8021/8798 与 8b041842 相同。
c) 档位理由（F05 契约收紧使存量旧收据 BLOCK＝不兼容持久化契约）与 CHANGELOG 头部版本规则是否相符；迁移说明与工单 F05 导语/台账 Q8/Q14 是否一致（禁 amend、APU 暂不重跑、ALL_SKIP 影响范围）。
d) 成本-质量指标一行（生产逻辑文件 5、新公开入口 0、新持久化字段 2、SUITE 入口 0、外部网络 0）是否与 diff 事实一致。
e) 与 8.0.0/7.2.1 条目体例是否一致（索引一行＋详细段六个 bullet 顺序）；不重新评价三段施工本身。
