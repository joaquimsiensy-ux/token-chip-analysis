# 工单E复核：退回

复核对象：[workorder_E_version.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_E_version.md) v1。HEAD 前后均为 `ec55860a80dbf23babe4b4394b63ebbc642ba1e9`，工作树均干净。

退回 **5 项文案修订**。不重新评价四段施工；版本档位意见另列，不阻断。

**E-R1-01｜日期上界漏写生效条件**

工单位置：第 21、31 行，“且不晚于 provenance 当前锚点日”。

事实：[facts_gate.py:452](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:452) 原文：

```python
if cur_date and peak_day > _dt.date.fromisoformat(cur_date):
```

没有 `current.date` 时不检查该上界。`F05_done.md:557` 也明确写着“日期上界仅在 current 锚显式给出 date 时生效”。

修订建议：两处同步改成“peak_date 严格 YYYY-MM-DD；provenance 当前锚点显式提供 date 时，不得晚于该日”。

**E-R1-02｜“stage2 收口/reseal 不受影响”范围过宽**

工单位置：第 31 行，“共享 check_facts_vs_ledgers 一字不动（stage2 收口/reseal 不受影响）”。

事实：共享函数源码确实未变，但调用链会消费已经改变的规则：

```python
# scripts/report/stage2_closeout.py:578
audit_release_gate.check_facts_vs_ledgers(case, load(case, "facts.json"), errors)
# scripts/report/audit_release_gate.py:1561
rebuilt = facts_gate.derive_facts(case_dir, exploration=False)
# scripts/report/facts_gate.py:492
gate_errors, _notes = gate_check(Facts(facts))
```

证据格式、日期和峰值上界收紧会传递到 stage2；仅新增 decimals 核验未接入这条共享路径。`F05_done.md:555` 也要求迁移后重建 stage2 收口收据。

修订建议：改成“共享函数源码未改；stage2 收口/reseal 未新增 decimals 核验，但沿既有调用同步采用峰值、日期和证据校验”。

**E-R1-03｜将实物重算写成了全面拒绝手写收据**

工单位置：第 29 行，“同 schema 手写 PASS 收据不再放行”。

事实：[audit_release_gate.py:1645](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:1645) 及第 1649 行：

```python
errs, _okc = figures_from_facts.fig2_check_errors(facts_p, series_p, FIGURE2_DEFAULT_TOL_PP)
errors.extend(f"figure2 发布期重算: {e}" for e in errs)
```

函数检查绑定、模式、容差及实物重算结果，没有识别“手写来源”的判定；字段与实物均合规的收据不会仅因手写而被拒。`F04_done.md:350` 亦说明合法同源旧 PASS 仍可通过。

修订建议：改成“输入非有限或末点不同源时，即使提供同 schema 的手写 PASS 收据也拒绝；PASS 自报不能替代实物重算”。

**E-R1-04｜followup 迁移不能按“7.2.0 之前”划分**

工单位置：第 34 行，迁移说明①。

事实：`followup_peaks` 随 `f583039` 的 R09 引入；7.2.0 基线 `311e6c4` 的 `replay_duck.py` 已写出以下字段，且该脚本与当前 HEAD 逐字一致：

```python
"producer": {"path": os.path.basename(__file__), "sha256": self_sha},
"value_type": vt,
"channels": {"path": os.path.basename(a.channels), "sha256": chan_sha},
"count": len(addresses), "addresses": addresses
```

这也与工单第 30 行“这些字段 7.2.0 的 --only-addrs 已写出”一致。实际迁移条件见 `F07_done.md:467`：缺绑定字段或 producer SHA256 不匹配当前引擎；channels 还须满足案内唯一实物及哈希绑定。

修订建议：删去版本截断，按实际缺字段、绑定失配等条件描述重跑；保留现有含 `--out-dir`、两次 `--only-addrs` 的命令。迁移说明②建议补上 `F05_done.md:555` 已登记的后续步骤：重算证据 SHA256、更新 override 绑定，再重建 facts 及下游收据。

**E-R1-05｜“通过后施工”缺少对应复核记录**

工单位置：第 32 行，工艺段。

事实：复核文件数确为 F06 一轮、F04/F07/F05 各两轮，但以下命令查得现存七份回复首行全部为“退回”：

```sh
grep -n -F '# 工单F' maintenance/repair-20260918-p0-f04-f07/review_F0[4567]_reply_r*.md
```

现有记录不能支持“codex 只读复核通过后施工”的历史叙述；施工报告实际对应 F06 v2，以及 F04/F07/F05 v3。

修订建议：改成“经所列轮次只读复核、按意见修订后施工”；如确有后续 PASS，引用实际记录。

**实际核过且相符的项目**

- **锚点、版本**：两条指定 `grep -n -F` 分别只命中 `CHANGELOG.md:13`、`:94`；`VERSION:1`、`pyproject.toml:15`、`SKILL.md:23` 均为 7.2.0。
- **提交范围**：五个指定提交均为 HEAD 祖先，逐个核过 `git show --stat`。四段生产文件、测试及施工记录与登记对应；`bf60b50` 仅修迁移文案并归档盲审。生产逻辑文件合计 3，无新增 SUITE 入口。
- **标识与行为**：任务列出的全部函数、常量和测试函数存在。已核 F06 tier 推导、F04 默认 0.05pp 与六类异常、F07 三件产物定位及绑定、F05 证据相等与 decimals 两类观测来源；需收窄的描述见上列。
- **测试登记**：F06 三例；F04 四函数增加 5 个 check，244→249，与 `F04_done.md:231` 一致；F07 用例 14–22 为 7 RED＋2 GREEN；facts 用例 16–21，其中用例 19 含两种日期；P105 a/b 两例。按源码和施工报告核对，本轮未重跑施工测试。
- **字节**：仅用 stat 元数据汇总，references＝930061、SKILL.md＝8021、commands-staging＝8798。
- **台账与盲审**：P1–P12 齐全，P8 明标“待用户裁决”。盲审首行分别为 F06/F04/F05 r1 PASS，F07 r1 FAIL→r2 PASS；r1 唯一 minor 确为漏 `--out-dir`。
- **迁移参数**：`--channels`、`--out-dir` 必填，`--only-addrs` 为 `action="append"`；工单现有命令符合源码。
- **体例与检查**：当前 `test_version_consistency.py` 实跑 exit 0。按工单逐字在内存模拟四文件改动，执行原测试的 `main`，通过 7.2.1 一致性检查；活跃条目 76→77，无撞号、倒排，日期、标题、粗体小节及成本-质量小节符合；SKILL 8021→8021。改动涉及的 19 条 manifest 契约检查通过，拟议增量未见 docs_lint 必红点。
- **遗漏与红线**：四段改动、残余台账、测试及迁移均有覆盖；应补的条件、stage2 联动和迁移步骤已列上文。拟议索引与详细段未出现具体代币分析结论。

**版本档位意见——不计入退回项**

支持“修”的依据：F06/F04 落实既有身份和对账义务；F07 消费生产者已经输出的绑定字段；正确 decimals 本就应与观测一致；未新增公开入口或 schema 标识。

反对“四段全部只是修”的最强依据是 F05：旧实现及正向夹具允许 `{"note":"observed peak"}` 这样的证据内容，新实现强制按 entity_id 提供 peak_raw/peak_date，并要求迁移。这改变了原先接受的输入契约，schema 名不变不能证明兼容。

按 `CHANGELOG.md:4` 的规则，我倾向整体应为 **8.0.0（主）**。关键分歧是旧自由格式证据是否属于受支持契约；现有源码与正向测试支持“属于”。若仍按裁决登记 7.2.1，建议保留档位异议和迁移影响；此意见不阻断本单。

**验证边界**

完整 `changelog_lint`、`docs_lint --all` 会读取禁区，本轮未运行；上述为活跃文件和拟议增量检查，不代表完整 lint 已通过。

工单第 33 行的 run_all 150/151＋补验 21/21、九项守卫全 PASS，未在本目录其他记录中找到独立输出，本轮也未重跑，列为调度方验收记录待核，不据此认定失败。

报告全文已打印到 stdout。全程离线，未改文件、未 commit。最初系统 git 触发的 xcrun 临时缓存写入尝试被沙箱拒绝；随后改用实际 git 可执行文件完成只读核对。