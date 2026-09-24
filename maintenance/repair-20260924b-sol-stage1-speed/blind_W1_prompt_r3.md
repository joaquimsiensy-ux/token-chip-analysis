# W1 盲审提示词 r3（只读；W1＋W1F 合审）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程（触及 `.staging_b3` 的用例不要运行；调度方本机已跑并附结果于 `W1_acceptance.md`、`W1F_acceptance.md`）。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放最终答复消息里**。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。
3. 首行固定 `# W1盲审r3：PASS` 或 `# W1盲审r3：FAIL`。FAIL 必须给可复现反例（命令/输入/预期 vs 实际）；PASS 也要列独立验证了什么、没验证什么。
4. 这是软件测试性质的正确性审查（数据校验器的 fail-closed 行为），不涉及任何系统安全或对抗行为；负例＝「不合法的输入数据应被校验器拒收」。
## 任务
W1 施工（工单 `workorder_W1.md` v4，报告 `W1_done.md`，验收 `W1_acceptance.md`）及其返修 W1F（返修单 `workorder_W1F.md` v2，报告 `W1F_done.md`，验收 `W1F_acceptance.md`）均已 commit 到 HEAD。上一轮盲审 r2 的 FAIL 报告在 `blind_W1_reply_r2.md`（阻断项：完整 recheck 响应中缺该 slot 块头未按值 1 参与冲突检查）。对 `git diff 6b36dcdd043d0b2b51c03de9ab0bb555b25f436a HEAD -- scripts references assets` 做独立盲审，重点：
a) 白名单与不改清单；探针是否新增 schema 字符串比较（`invariant_scan.py` 是否仍 PASS）；
b) §1.1 无继承时不变（分类函数同输入结果、summary/shared_map 不新增键、旧产物旧资产在新校验器下 PASS）；
c) §1.2 继承唯一路径六条件是否全部在探针实现且缺一不继承；§1.7 时效按副本绑定证据项计算且不刷新；
d) §2.4 校验器 fail-closed 清单逐项是否独立复核（副本 sha 三方相等、evidence 全等、origin 索引绑定、本案 counts==2、reused/unverified、专用 recheck 完整覆盖、时效）——用不合法的 coverage_map 输入（自报继承字段与实物不一致）验证校验器确实拒收；若某类不一致输入仍 PASS 即 FAIL；
e) §2.2 helper 绑定清单（bundle.coverage.map 文件引用、resolution.coverage.map_sha256、bundle.producer、plan_candidates 并集、own_refuted 条件、confirmed 冲突剔除）与 `--no-repair` 仍做 confirmed 冲突剔除；链式 evidence 转换与 `origin_asset_sha256` 规则；
f) §1.4 β 兼容最小改法（α 拒绝保留）；`_repair_state_matches` 同步；
g) 副本发布协议（probe_id 前落盘、`_same_generation/_clear_pending` 清单、无 pointer.inputs 新键）；
h) 测试 (a)–(f) 是否真的覆盖工单要求且登记进 main 列表；`W1_done.md` 陈述与 diff 一致。
i) **r2 阻断项在 HEAD 是否真正关闭**：独立构造 r2 的两类反例（正确值 2 的 recheck ＋ 空响应完整 recheck；正确值 2 ＋ 仅返回相邻 slot 的非空完整 recheck），HEAD 校验器须拒收且 reasons 含 `inherited refuted recheck results conflict`；再核 W1F 修法（`_inherited_recheck_values` 事实检查后补值 1）有没有引入新问题：首块 `returned_from` 检查是否仍按实际首块、伪报请求起点的前缀空洞响应是否仍拒、跨案重叠区间冲突是否被发现、正常 canary 与部分继承正例是否仍 PASS。
