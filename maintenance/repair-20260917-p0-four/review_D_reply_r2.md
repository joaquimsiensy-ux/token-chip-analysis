# 工单D复核：退回

v2 尚有 **4 项需修订，另有 1 项诊断建议**。坏事件写入分支已修，但新增反例会假绿；形状校验仍有遗漏；用例 12 的基线预期不成立。

以下“工单位置”均指 [workorder_D.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_D.md)。报告全文已打印到 stdout，未写文件。

**D-R2-01〔P1〕D2 仍把不完整触发日当成空候选放行。**

工单位置：D2:108–145；D4-a:331。

事实，工单原文：

```python
cands = day.get("active_candidates")
cands = [] if cands is None else cands
```

执行原文函数，needs 为空、summary 两个 SHA 均正确，触发日为：

```json
{"schema":"trigger-days-replay/v1",
 "days":{"2026-01-01":{"reason":"launch","count":1,"active_candidates":null}}}
```

结果为 `errors=[]`，不要求 followup；删除 `active_candidates` 字段也同样放行。正常生产者输出列表，不能把缺项/null 自动解释成没有候选。

另有同族遗漏：summary 或 trigger 顶层为 `[]`、`null` 时，:91/:109 在类型检查前调用 `.get`，直接抛 `AttributeError`。此弱点原函数已有，但属于本次 D2 重写内可处理的范围。

修订建议：首次 `.get` 前检查两个顶层对象；逐日要求 `active_candidates` 存在且为列表，合法空列表 `[]` 才表示零候选。补缺项、null、非对象顶层反例，均加入 errors 后返回。

**D-R2-02〔P1〕D3 没有验证 active_candidates 的列表形状。**

工单位置：D3:219–231；D4-b:336。

事实，工单原文：

```python
found = [x for d in days.values()
         for x in (d.get("active_candidates") or [])]
```

原文函数的内存执行结果：

| active_candidates 输入 | 实际结果 |
|---|---|
| `7` | `TypeError`，未经过 `_fail`，不能兑现 exit 2 |
| `"0xABC"` | 拆成地址集合 `["0","a","b","c","x"]`，解析成功 |
| `{"0xABC":1}` | 当成 `["0xabc"]`，解析成功 |
| `null`，另一个 needs 文件含有效地址 | 畸形触发日被忽略，解析成功 |

修订建议：展平前逐日检查字段存在、类型为 list、每项为非空字符串；失败统一调用 `_fail`。与 D2 使用相同规则，补上述反例，断言 exit 2、收据字节未变。

**D-R2-03〔P2〕坏事件反例不能识别“重复覆盖相同字节”。**

工单位置：D4-b:336。

事实：工单先用坏输入全量运行生成拒收 `replay_stats.json`，再用同一坏输入跑 only-addrs，只比较收据字节。内存执行 main 分支结果：

```text
恢复旧的无条件写入：write_calls=1，same_bytes=True
v2 的条件写入：    write_calls=0，same_bytes=True
```

两者都非零退出、都不产生 followup，拟议断言无法抓住 r1 D-01 的原缺陷。

修订建议：先保留一次成功全量运行的产物，再用另一个含坏事件、收据绑定正确的通道执行 only-addrs，比较原产物字节。

坏输入可直接传给 `_write_inputs`，例如增加 `value="BAD"` 的事件：它在 CSV 写完后生成 collector/channel 两层收据，`_csv_stats` 只统计行数和区块，不会提前拒绝坏 value。若先追加 CSV，必须重建两层收据，否则只会命中 preflight SHA 错误，覆盖不到 :577 分支。

同时明确坏例首个 only-addrs 文件所在目录，避免混入前一个成功例遗留的 followup。

**D-R2-04〔P2〕用例 12 的 RED 声明错误。**

工单位置：D4-a:319、324、334；§0.7:15。

事实，:334 写的是“RED（基线报未覆盖）”。当前基线没有 needs/followup 覆盖检查；执行同一夹具：

```text
case12 baseline: errors=[]
case12 v2:       errors=[]
```

它是 **GREEN→GREEN** 的归一回归例。用例 2 同样如此，虽然括注已解释，表格仍以“RED”开头。:319 还只要求 `_r09_case_1..7`，与十二例表格不一致。

修订建议：2、12 均明确标为 GREEN→GREEN；函数和逐例循环范围改为 1..12。§0.7 按各例真实基线记录结果，不要求制造 RED。

**D-R2-05〔P3，诊断建议〕非法 peak 会引出虚假的“peak==0”错误。**

工单位置：D2:191–197；现有辅助 [raw_int](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:603)。

事实：

```python
peak = raw_int(...)
...
elif blk is not None:
    errors.append(... "在 peak==0 时须为 null")
```

输入 `peak="x"`、`peak_blk=9`，得到：

```text
block_precision_followup.addresses[0xabc].peak 不是整数 raw amount
块级补算收据 0xabc.peak_blk 在 peak==0 时须为 null
```

第二条把解析失败的替代值 0 当成真实峰值；负 peak 也会落入该分支。这里应只报 peak 根因。

修订建议：调用 raw_int 前记录 errors 长度；若它追加错误，立即 continue，跳过依赖峰值的区块判定。无需改通用辅助函数。该问题不会错误放行，不单独作为退回依据。

**r1 八项闭合状态**

| r1 编号 | v2 结论 |
|---|---|
| D-01 | :577 条件写入已闭合；坏事件反例未闭合，见 D-R2-03。 |
| D-02 | needs 两种错误形状及小写归一已修；触发日形状仍有遗漏。 |
| D-03 | 原列收据顶层、inputs、缺字段、正峰值区块、零峰值区块反例均已修；另见诊断建议。 |
| D-04 | 裸 `fu.get("schema")` 被扫描器识别，闭合。 |
| D-05 | 坏 JSON、空并集、坏 needs 均 stderr＋exit 2；其他非法形状尚未统一。 |
| D-06 | h 补 needs、两字段及新断言后放行；未豁免旧 summary，闭合。 |
| D-07 | 六文件与 `4cbfe48` 相同；测试文件改列 C 后基线，声明正确。 |
| D-08 | :191/:194、:960/:970 均为唯一锚，闭合。 |

**其余实际核验结果**

| 核验项 | 结果与证据 |
|---|---|
| a：全部锚点 | 实际执行 `grep -n -F`：peaks_daily 的 60–63、171、202、213；gate 的 408、457、603、1074/1103、1676；replay 的 36、191、194、330、556、577、587；测试的 960、970、972、236、113；文档的 132、149，指定文本均恰一处且行号相符。 |
| b：定位与绑定 | APU 型 `data/peaks_daily/` 命中；隐藏目录、`_history`、`.duck_tmp`、文件及父目录符号链接排除；零份 return、多份拒。三个伴随文件均相对 pd。needs 缺 SHA 明确提示“升级脚本重跑”。原有六条错误文案逐字保留。 |
| b/j：错误分支 | 结构或路径失败后的 return 会遮住后续检查，但已有错误，且后续依赖无效数据，属于可接受的拒收短路。schema、engine、绑定错误可同时累计，不应要求全局互斥。大小写重复键检测有效。 |
| c：受保护逻辑 | build_events、emit_merged、replay_pass2 原文未变；pass1 除抽取调用外剩余 AST 相同，deltas SQL 相同；followup 窗口 SQL 与原 :285–290 逐字节相同。 |
| c/j：入口与退出 | `_fail` 定义位置可用，sys 已 import；:577 位于 main 内，不违反 §0.4。正常 only-addrs 在 pass1 前 SystemExit；坏事件仍先拒收，v2 分支不写 replay_stats。 |
| c：计算与收据 | 真实 DuckDB 内存执行 HUGEINT、VARINT；Python 回退只读 ab，peak_min=0 保留所有正峰值，缺事件地址补 0/null。首输入目录、每输入 SHA、channels SHA 均复算一致。 |
| d：D4-a | 1、3–6、7 前半、8–11 为 RED→GREEN；2、12 为 GREEN→GREEN；7 补齐绑定与覆盖后放行。执行的是峰值子闸，未冒充完整 gate.run。 |
| d：旧夹具 | 原 e/f/k/g 断言继续成立。h 不改会报 needs 错误，但旧断言漏检而假绿；按 v2 补夹具后错误为空，新断言通过。g 仍命中原 empty_reason 文案。 |
| d：D1/D4-c | needs 写后 SHA 实算语句正确；summary、夹具助手、新断言字段一致。原 summary 缺字段会使新增断言失败；完整 test_peaks_daily 未运行。 |
| e：D5 | 基线 invariant_scan 实跑 PASS。内存叠加 D1–D3 并补三处登记后，validate_manifest 返回 `[]`。计数为 producer 81、consumer 118、atomic 61；transport 65、formal 61 不变。minimum_counts 是下限，无需修改。 |
| f：文档 | 两处替换实算 61→48 B、30→39 B；stat 基线 8021 / 930065 / 8798，替换后 references 恰 **930061**。两文档的粗体、引用规则及其 13 条契约 needle 均通过；未运行会读取禁读内容的完整 docs_lint。 |
| f/i：语义与范围 | 对合法输入，并集每址覆盖承接补算义务；形状漏洞修复前不能宣称闭合。L1/L2、门槛、既有格式及契约针不变。P2/P3 维持、P13 由调度方另行登记，与白名单边界自洽。 |

真实 SQL 对表结果：

| 地址 | peak | peak_blk |
|---|---:|---:|
| ADDRS[1] | 10000000000000000000 | 102 |
| ADDRS[2] | 5000000000000000000 | 103 |
| ADDRS[5]，无事件 | 0 | null |

前两址与全量 peaks 对应字段一致；内存文件替身中的全量产物字节未变。坏 JSON、空并集、坏 needs 均 exit 2，旧 followup 字节未更新。

**g：回归与同族搜索**

全量搜索 `scripts/`、`scripts/tests/`：手写 peaks_summary 仅见现有 e/f/k/g/h 五处；未发现其他具名生产语义消费者。test_peaks_daily 读取两文件作验证，属于本段；test_repair_batch1 另有对子闸的 mock。§0.8 其余三个测试使用的案夹具未发现 summary，仍走零份 return。这是源码检查，不是全套通过结论。

run_all 另有既有流程约束：[test_stage2_reseal.py:516](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_reseal.py:516) 会进入 W3 专用 overlay 验收；其 :604–611 白名单不允许 D 的生产、测试和文档改动。因此在 D 施工后的未提交工作树跑全套，即使通过前面的验收目录/HEAD 检查，也会在这里失败。这属于旧 W3 验收耦合，不是 v2 新引入的业务回归，不建议扩 D 白名单顺带修改。

**h/j：APU 两种前提**

在 ub_formula 正确、trigger_days_file=True、子目录 trigger 的 schema/空声明合法的前提下，内存执行结果与 §4 一致：

- 子目录 trigger 存在且 SHA 咬合：报 needs 缺 SHA，文案含“升级脚本重跑”。
- 子目录 trigger 缺失：先报“peaks_summary 声称产出触发日但 trigger_days.json 缺失”并返回。

案根残留 trigger_days.json 不是 summary，不计入“多份”，也不会代替子目录 trigger。其他字段也坏时，错误可能叠加；v2 已要求记录实际原文。未访问真实 APU 案。

**验证边界与工作树**

全程只读、离线，工具未读取禁读路径。六个需要落盘夹具的完整测试未运行；run_all 未运行。除基线 invariant_scan 外，执行取证采用原文函数、内存文件替身和真实 DuckDB SQL，不代表完整 CLI 或发布验收通过。

开工工作树为空，HEAD 为 `487cb1d`；收尾 HEAD 为 `72430e9`，并发状态为：

```text
 M scripts/report/facts_gate.py
 M scripts/tests/test_report_facts.py
?? maintenance/repair-20260917-p0-four/C7_done.md
?? maintenance/repair-20260917-p0-four/C7_red_evidence.txt
```

这些不是本次写入。D 工单和九个施工白名单文件相对开工快照均无差异，九文件与 C 基线 `1b317b3` 亦无差异。当前工作树不满足 §0.1 的施工前置条件；此状态单列，不计作工单缺陷。

Codex session ID: 01a0afe5-67b3-7942-8834-3646d9915103
Resume in Codex: codex resume 01a0afe5-67b3-7942-8834-3646d9915103
