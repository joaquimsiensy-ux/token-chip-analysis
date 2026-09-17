# 工单E复核：退回

复核对象：[workorder_E_version.md v1](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_E_version.md)（下称 W）。确认 **6 项需修订**。报告全文已打印到 stdout；未修改文件、未 commit、未联网。

**E-01｜版本档位与兼容性规则不符**

- **工单位置**：W:3、11–17、25。
- **事实**：CHANGELOG.md:4 规定“主=不兼容的工作流/schema/入口边界变更”。`audit_release_gate.py:44–53` 将 facts.json 加入必需集合，`:1772–1774` 无版本区分地报缺件，`:1513–1516` 拒绝缺 provenance 的旧 facts；`stage2_closeout.py:581–582` 也增加必经检查。
- **判断**：支持 7.2.0 的理由是新增入口和 schema，原有调用入口仍保留。但原先合法的 facts 现在必须补绑定块、facts_inputs 并重建，已经改变持久化契约和工作流。纯内存验证中，旧 Facts/gate_check 返回 `([], [])`，新增检查对同一对象报“facts.json 缺 provenance 绑定块”。这不是完整发布回归，但足以证明格式兼容性发生变化。
- **修订建议**：按现行规则登记 **8.0.0**，同步四文件目标及 CHANGELOG，说明迁移要求。保留 7.2.0 需要实际兼容路径或明确修订版本规则。

**E-02｜必跑验收命令违反禁读纪律**

- **工单位置**：W:7 与 W:18、40。
- **代码事实**：`changelog_lint.py:16` 指定归档路径，`:41` 执行 `archive = parse(ARCHIVE)`，`:27` 实际读取。`docs_lint.py:268` 收集 references 全部 Markdown，`:272` 收集 archive/evals，`:306` 逐个读取；`:129–134` 还递归读取全库 Markdown。
- **修订建议**：将原版全量守卫交由具备对应读取范围的调度方执行，并提供退出码和日志供 E_done 引用；施工会话的允许范围检查单独标注。不能过滤禁区后仍称全量 PASS。

**E-03｜A 段测试数量写错**

- **工单位置**：W:28，原文“`test_repair_batch_c` 十例”。
- **事实**：`grep -n -F 'def _r08_case_' scripts/tests/test_repair_batch_c.py` 对应 **13 个定义**；`:1497–1510` 的 `t_r08_nonfinite` 调用全部 13 例。A_done.md:497、513 记录完整 batch C 为 **244 checks**。
- **修订建议**：写“新增 R08 13 个用例”；若登记完整模块结果，另注明施工记录为 244 checks。

**E-04｜生产文件数及入口称谓不准确**

- **工单位置**：W:34、3。
- **事实**：W:34 写“生产逻辑文件 5”，但五次 `git show --stat` 的生产文件并集为 **6 个**：figures_from_facts、audit_release_gate、facts_gate、stage2_closeout、peaks_daily、replay_duck。W:3 将两个入口都称为子命令，但 `replay_duck.py:646` 使用 `ap.add_argument("--only-addrs", action="append", ...)`，属于选项。
- **修订建议**：写“生产逻辑文件 6；新增公开入口 2：1 个 build 子命令、1 个 --only-addrs 选项”。

**E-05｜FAIL 收据落盘被写成无条件保证**

- **工单位置**：W:28，“mode_check 把输入失败收敛为 FAIL 收据落盘”。
- **事实**：`figures_from_facts.py:356–360` 仅在两输入文件在场时尝试写收据；写入 OSError 时明确打印“收据未更新”。`:362–363` 对 series 非 list 直接退出。盲审 A r2:26 也明确区分了写入失败和成功落盘。
- **修订建议**：说明非法 pct 的 FAIL 留痕，以及解析失败时尝试覆盖收据的条件；明确写失败会提示未更新并失败退出，保留既有不产收据分支。

**E-06｜trigger 哈希绑定缺少条件说明**

- **工单位置**：W:31，“inputs 绑 needs/trigger sha”。
- **代码原文**：`audit_release_gate.py:1197` 必验 needs；`:1199` 为：
  ```python
  if td_union and bound.get("trigger_days.json") != trig_sha:
  ```
- **事实**：纯内存执行当前检查函数，needs 非空、trigger 候选为空、followup 仅绑定 needs 时，结果为 `errors=[]`。
- **修订建议**：写“必绑 needs sha；触发日候选非空时还须绑定 trigger sha”。仅修订文案，不改变 D 段实现。

**实际核过的其余项目**

| 项目 | 核验结果 |
|---|---|
| CHANGELOG 锚点 | 两条指定 `grep -n -F` 均恰 1 处，行号分别为 :13、:93。 |
| 当前版本 | VERSION:1、pyproject.toml:15、SKILL.md:23 均为 7.1.3；原版 `test_version_consistency.py` exit 0。 |
| 施工提交 | 五个指定提交均为 HEAD 祖先；stat 分别触及 4、4、15、4、12 个文件，文件归属与各段描述相符。 |
| 源码名称 | 题列函数、record、两个 schema、CLI 入口、字段、共享夹具助手、`augment_gate(balances)`、R09 13 例及 `followup_case` 均存在。 |
| 测试与 record 数量 | B 10 例；R07 调度语句展开为 15 类 34 例，与 C7_done:55 一致；stage2 与 C 前源码比较为 11→12，唯一新增 `facts_vs_ledgers`。 |
| D 其他描述 | 全量与 followup 峰值窗口 SQL 字符串相同；原有六条错误文案保留；needs sha 生产及测试断言存在。 |
| 字节 | references 三组 Markdown 为 930070→930061；SKILL 8021、commands-staging 8798。三册分别 −5、−13、+9 B；计数只取 stat/Git 树大小。 |
| manifest | minimum_counts 的 producer/consumer/atomic 为 81/118/61；两个 schema 和两处 overwrite_single 均已登记。 |
| 文档行号 | report-template:212、recon:132、tiering:149 与当前内容一致。 |
| 台账 | 含 P1–P13、P3′/P4′；P11 已明确撤销。 |
| 盲审轮次 | 首行对应 A FAIL→PASS、B PASS、C FAIL→PASS、D PASS；C7 位于 C 两轮之间。 |
| 复核轮次 | 文件数 A=4、B=2、C=3、C7=2、D=4。 |
| 体例与模拟修改 | 日期、破折号、粗体小节和成本-质量段符合既有体例。内存模拟后活跃条目 75→76，活跃区无重复或倒排；版本一致性检查 exit 0；SKILL 8021→8021。 |
| 遗漏与红线 | facts_inputs、balances 参数、reseal 同步验收和并行复核工艺均已写入。reseal 源码确用 `/tmp/w3_acceptance` 并要求 HEAD 相同。未发现新增代币分析结论。 |

**未验证项与范围**

原版 `changelog_lint`、`docs_lint --all` 未运行，原因是 E-02 的禁读冲突。上述活跃区及增量静态检查不等于全量 PASS；拟改四文件未发现额外的版本、粗体或契约 needle 必红点。

SUITE 登记数确为 **151**，reseal TESTS 数确为 **21**；但允许范围内未找到可独立核验“151/151、21/21、九项守卫全 PASS”的完整运行日志。79f9b6c 提交信息仅记录调度方已填入计数，列为**待确认，不计入六项**。真实 APU 对照未重跑，文案数字与台账 P3′/P4′ 一致。

开工 HEAD 为 `79f9b6c`，收尾为 `5e3c05a`；期间外部仅提交 `construct_E_prompt.md`。已确认工单、四个目标文件、scripts/、references/ 在两端无差异，开工与收尾工作树均干净。本次没有打开禁读路径文件，也没有创建报告文件。

工单 SHA-256：`1107e1113d960ef950f3b5c13ffa8590d40849e180816fa76926429e542911e8`。

Codex session ID: 01a0b040-c504-7500-820f-aee896ca6387
Resume in Codex: codex resume 01a0b040-c504-7500-820f-aee896ca6387
