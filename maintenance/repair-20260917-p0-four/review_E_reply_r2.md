# 工单E复核：退回

复核对象：`maintenance/repair-20260917-p0-four/workorder_E_version.md`（v2）。确认 **1 项未闭合：E-02**。其余五项订正与已核证据相符；档位按本轮要求保留 7.2.0。

**E-02-r2｜§2 仍残留要求施工者运行禁读守卫的指令**

- **工单位置**：[workorder_E_version.md:19](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_E_version.md:19)。
- **事实**：第 4、13、42 行已明确由调度方运行，但第 19 行仍写“先跑”。实际命中：

```text
$ grep -n -F '先跑' maintenance/repair-20260917-p0-four/workorder_E_version.md
19:4. `CHANGELOG.md` 两处插入（**先跑** `python3 -B scripts/tests/changelog_lint.py` 记基线"活跃 75 条"，改后须 76）：
```

[原版 changelog_lint.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/changelog_lint.py:16) 的读取链仍为：

```python
# :16
ARCHIVE = os.path.join(ROOT, 'archive', 'CHANGELOG-archive.md')
# :41
archive = parse(ARCHIVE)
# :27，parse 内
for i, line in enumerate(open(path, encoding='utf-8'), 1):
```

- **修订建议**：将第 19 行括号内容明确改为“调度方施工前运行原版 changelog_lint，提供活跃 75 条基线；施工后复跑确认 76 条；施工者不运行”。与 §1、§3 统一即可。

**六项处置核验**

| 编号 | 结果与证据 |
|---|---|
| E-01 | 档位说明已登记异议及待追认。`audit_release_gate.py:53` 将 facts.json 列为必需件，`:1513–1516` 拒绝无 provenance 的旧 facts；说明中的兼容性事实与源码、CHANGELOG:4 规则一致。按本轮授权保留 7.2.0。 |
| E-02 | 未闭合，见上。§3 和最新施工提示词已订正，§2:19 漏改。 |
| E-03 | 已闭合。R08 定义及调度均为 13 例；`A_done.md:513` 记录完整 batch C 为 244 checks。 |
| E-04 | 已闭合。五个提交的生产文件并集为 6 个；公开入口是 build 子命令及 --only-addrs 选项。 |
| E-05 | 已闭合。`figures_from_facts.py:356–360` 确认两输入在场才尝试覆盖 FAIL 收据，写失败提示“收据未更新”；`:362–363` 保留 series 非 list 不产收据分支。 |
| E-06 | 已闭合。`audit_release_gate.py:1197` 必验 needs 哈希，`:1199` 仅在 `td_union` 非空时要求 trigger 哈希绑定。 |

**实际核过的其余项目**

| 项目 | 核验结果 |
|---|---|
| 锚点与版本 | 两条指定 `grep -n -F` 均恰 1 处，分别位于 CHANGELOG:13、:93；VERSION:1、pyproject.toml:15、SKILL.md:23 均为 7.1.3。 |
| 施工提交 | A 212ede1、B 03507cb、C 1b317b3、C7 eca1131、D f583039 均为 HEAD 祖先；stat 分别触及 4、4、15、4、12 文件，与文案归属相符。 |
| 源码与计数 | 题列函数、子命令、选项、字段、schema、record、共享夹具助手和 balances 参数均存在；B 10 例、R07 调度展开为 15 类 34 例、stage2 record 11→12，唯一新增 facts_vs_ledgers；R09 13 例及 followup_case 存在。 |
| D 段描述 | 两处峰值窗口 SQL 字符串完全相同，原六条错误文案均保留；needs 哈希生产字段与测试断言存在。 |
| 字节与文档 | 仅用 stat/Git 树大小核算：references 930070→930061，SKILL 8021、commands-staging 8798；三册分别 −5、−13、+9 B。report-template:212、recon:132、tiering:149 内容相符。 |
| manifest | minimum_counts 对应 producer schema／consumer schema／atomic 为 81／118／61；两个 schema 及两处 overwrite_single 均已登记。 |
| 台账与轮次 | 台账含 P1–P13、P3′/P4′，P11 标为撤销。复核文件数 A=4、B=2、C=3、C7=2、D=4；盲审首行对应 A FAIL→PASS、B PASS、C FAIL→C7→PASS、D PASS。 |
| 体例及模拟 | 日期、破折号、粗体小节和成本-质量指标与既有体例相符。内存模拟活跃条目 75→76，无重复或倒排；原版版本检查在当前文件及内存模拟文件上均返回 0；SKILL 8021→8021。增量文档检查未发现粗体或契约 needle 必红点。 |
| 遗漏与红线 | facts_inputs、identity 夹具参数、reseal 同步验收、并行只读复核工艺均已登记。reseal 源码确认使用 `/tmp/w3_acceptance` 并校验 HEAD 一致。未发现新增代币分析结论。 |

**验证边界**：未运行原版 `changelog_lint`、`docs_lint --all`，两者会读取禁区；上述活跃区和增量检查不代表全量 PASS。历史“run_all 151/151、reseal 21/21、九项守卫全 PASS”仍缺本轮可独立核验的完整日志；源码登记数确为 151、21。真实 APU 对照未重跑，数字与允许读取的台账一致。钉版目录存在，但未验证其实际承接旧案的运行效果。这些均未计入退回项。

全程只读、离线，未修改文件、未 commit、未打开禁读路径内容。开工 HEAD 为 `9edded1`，收尾为 `e5b30c1`；期间外部仅更新施工提示词，工单、四个目标文件、scripts/、references/ 在两端无差异，开工与收尾工作树均干净。报告全文已打印到 stdout。

工单 SHA-256：`47c58cc793e4d50709a74eb5b1ee9e751ea6c525f64cb54c173d480c91a9a654`。

Codex session ID: 01a0b050-627c-7351-9404-ae3bd218fe49
Resume in Codex: codex resume 01a0b050-627c-7351-9404-ae3bd218fe49
