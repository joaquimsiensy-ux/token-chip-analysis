# 工单D复核：退回

发现 8 项需修订。特别纠正：**h 例不会“必红”，而会漏掉新增错误、继续假绿。**

复核期间 HEAD 从 `afed1ca` 前进至 `6baac56`；已核实工单 D、全部施工白名单及相关生产代码均未变化。开工、收尾工作树均为空。全程离线、只读，未修改文件。

以下工单位置均指 [workorder_D.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_D.md)。

1. **D-01〔P1〕失败路径仍会覆盖全量 `replay_stats.json`。**

   **工单位置：** §1.3:21；D3:259–263；D4-b:282。

   **事实：** `--only-addrs` 分流位于现有 `:587`，但坏事件分支在此前执行：
   ```text
   577:        json.dump(receipt, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)
   ```
   对修改后 `main` 的原文进行内存分支执行，令 `n_bad_fields=1`，观察到写入 `/virtual/new/replay_stats.json`，原字节被覆盖。正常路径能跳过 pass1/merged/pass2，失败路径违反 §1.3。

   **修订建议：** 保留坏事件拒收，但 `--only-addrs` 模式不得执行这次全量收据写入；增加坏事件反例，核验 §1.3 所列产物全部保持原字节。不要通过提前绕过事件校验来修复。

2. **D-02〔P1〕错形状输入会被当成空并集放行。**

   **工单位置：** D2:120–134；D4-a:270–280。

   **事实：** 原文只收集符合类型的部分，其余静默跳过：
   ```python
   if isinstance(need, dict):
       for bucket in need.values():
           if isinstance(bucket, list):
               union.update(str(x) for x in bucket)
   ```
   将文件哈希正确登记后，以下内存反例均返回 `errors=[]`：
   - needs 顶层为 `["0xabc"]`；
   - needs 为 `{"0.0100":"0xabc"}`；
   - trigger 的某日内容为字符串，未提供合法日对象。

   另有归一遗漏：D2 保留 `0xABC`，D3 输出 `0xabc`，会错误报告未覆盖。

   **修订建议：** 在计算并集前严格验证 needs、档位列表、触发日对象和 `active_candidates` 的形状；非法结构明确报错。生产者和消费者采用一致的地址归一，并补充这些反例。日期键语义仍可按 P3 留待另单。

3. **D-03〔P1〕收据形状检查不完整，部分放行、部分直接崩溃。**

   **工单位置：** D2:141–169；D4-a。

   **事实：**
   ```python
   for item in fu.get("inputs") or []:
   ...
   blk = entry.get("peak_blk")
   if blk is not None and (isinstance(blk, bool) or not isinstance(blk, int)):
   ```
   原文内存执行结果：
   - `{"peak":"1"}`、`{"peak":"1","peak_blk":null}`、`peak_blk=-1` 均无错误；
   - `inputs=7` 抛 `TypeError`；
   - followup 顶层为 `[]` 抛 `AttributeError`。

   后两项不会放行，但无法返回工单要求的、可用子串断言的错误集合。

   **修订建议：** 先验证收据顶层及 `inputs` 结构，再验证每址两个必需字段；正峰值必须对应非负整数区块，零峰值采用生产者约定的 `0/null`。结构错误应加入 `errors` 并结束相关分支。补齐对应负例。

4. **D-04〔P1〕D5 指定的消费者登记会使 `invariant_scan` 失败。**

   **工单位置：** D2:142；D5:298。

   **事实：**
   ```python
   if str(fu.get("schema")) != BLOCK_PRECISION_FOLLOWUP_SCHEMA:
   ```
   扫描器 `_is_schema_access` 只识别直接的 `.get("schema")` 或下标访问，不识别外包 `str(...)`。实际内存叠加 D2/D3/D5 后，出现两条 `receipt_consumers` 登记差异。

   **修订建议：** 在验证 `fu` 为字典后直接比较：
   ```python
   if fu.get("schema") != BLOCK_PRECISION_FOLLOWUP_SCHEMA:
   ```
   已用同一扫描器验证：改为直接比较后，拟议 manifest 校验错误为 `[]`，无需改扫描器。

5. **D-05〔P2〕坏 JSON、空并集退出码是 1，不是要求的 2。**

   **工单位置：** D3:185–202；D4-b:282。

   **事实：**
   ```python
   raise SystemExit(f"[only-addrs] 读不了 {p}: {exc}")
   raise SystemExit("[only-addrs] 地址并集为空——无需补算（needs 与触发日活跃候选均空）")
   ```
   `SystemExit` 携带字符串导致进程退出码 1。D4 只断言“rc 非 0”，会漏掉这个契约错误。

   **修订建议：** 错误信息打印到 stderr，随后 `raise SystemExit(2)`；两项测试明确断言 `returncode == 2`，并保留收据未更新检查。

6. **D-06〔P2〕h 例假绿；应补夹具，不能豁免旧 summary。**

   **工单位置：** D4-a:270。

   **事实：** 实际锚：
   ```text
   970:        assert not any(("trigger" in x or "上界" in x) for x in errors), errors
   ```
   新闸对现有 h 夹具返回 needs 哈希错误，但该文案不含上述两个子串，因此旧断言仍通过。

   **修订建议：** 选择“**h 夹具补字段**”：写入合法空 needs 字典，summary 补实算哈希及 `needs_block_precision_file`；保留原断言，同时增加完整放行断言。保留缺哈希拒收策略，才能与 §4 APU“改后须报错”一致。

   `_r09_write_peaks` 指定的哈希字段名与 D1 一致，但其字段清单漏列 `needs_block_precision_file`，也应补齐。

7. **D-07〔P2〕内容基线声明不实。**

   **工单位置：** 开头第 4 行。

   **事实：** 原文称 `test_audit_release_gate.py` 与 `4cbfe48` 逐字节相同；实际：
   ```text
   git diff --numstat 4cbfe48 HEAD -- scripts/tests/test_audit_release_gate.py
   181     0       scripts/tests/test_audit_release_gate.py
   ```
   差异包含现有 R03 用例和 facts 夹具助手。其余六个被声明相同的文件确实无差异；全部 D 白名单文件与 `1b317b3` 无差异。

   **修订建议：** 将该测试文件明确列入 C 落地后的基线，删除其“与 `4cbfe48` 相同”的声明。

8. **D-08〔P2〕部分定位文本不满足“唯一锚”。**

   **工单位置：** §0.5；D3:176；D4-a:270。

   **事实：**
   ```text
   grep -n -F '    con.execute(f"""' scripts/evm/replay_duck.py
   190:    con.execute(f"""
   237:        con.execute(f"""
   267:        con.execute(f"""
   353:    con.execute(f"""COPY (SELECT b AS block, ts, tx, li AS log_index,
   ```
   h 的 `:964–968` summary 整块也出现两次，另一处是 `:953–957`。h 末尾 `:970` 和后续注释 `:972` 则均唯一。

   **修订建议：** deltas 抽取使用唯一的 `:191 CREATE VIEW deltas AS` 与 `:194` 定界；h 夹具使用唯一 h 注释及 `:970` 定界，不把重复 summary 文本作为唯一锚。

**其余实际核验结果：**

| 核验项 | 结果 |
|---|---|
| a：其余锚点 | `peaks_daily` 的 60–63、171、202、213；gate 的 408、457、603、1074/1103、1676；replay 的 36、330、556、587；测试的 970、972、236、113，均与指定位置一致。两处文档子串均唯一。 |
| b：定位与旧行为 | 子目录 summary 能命中；隐藏目录、`_history`、符号链接及 `.duck_tmp` 被排除；零份 return、多份拒；三个伴随文件均相对 `pd`。原有 **6 条错误文案逐字保留**。schema、engine、绑定错误可同时累计，并非全局互斥。 |
| c：重放计算 | deltas SQL 抽取前后相同，pass1 剩余 AST 相同；窗口 SQL 字符串与 `:285–290` **逐字节相同**。三种地址输入均能解析并小写化，与 `build_events` 一致；Python 回退只读 `ab`，`peak_min=0` 保留所有正峰值，零值由补齐逻辑处理。 |
| d：七例预期 | 按表构造内存夹具，直接调用旧/新 `check_daily_peaks`：1、3、4、5、6、7 前半满足 RED→GREEN；2 为 GREEN→GREEN；7 补齐收据后放行。未将这些结果冒充完整 `gate.run` 测试。 |
| e：登记 | producer 与 `followup_peaks` 的 `os.replace` 能被识别，原子写应登记 `overwrite_single`。修正 D-04 后登记计数为 producer 81、consumer 118、atomic 61；transport 65、formal 61 不变。`minimum_counts` 是下限，现有值无需因新增点强制修改。 |
| f：文档 | 实算替换分别为 61→48 B、30→39 B；当前 stat 为 `8021 / 930065 / 8798`，替换后 references 恰为 **930061**。两份修改后文本通过 docs_lint 同规则的粗体、引用检查，相关契约 needle 均保留。 |
| g：同族与回归 | 全量搜索 `scripts/` 后，相关生产语义点只有 `peaks_daily.py` 与 `audit_release_gate.py`；没有发现遗漏的其他具名消费者。手写 summary 夹具仅在现有 e/f/k/g/h 段；e/f/k/g 原断言仍成立，h 见 D-06。`run_all` 中已确定的新增变红点是按原文登记后的 invariant 校验。 |
| i：范围 | D1 不改变 L1/L2、默认门槛及原格式；D3 正常分流不改 merged/pass2 逻辑。P2/P3 保留、P13 另单的边界自洽。收据覆盖只能承接“并集内每址补算”；修复 D-02/D-03 前不能宣称这一义务已完整落实。 |

真实 DuckDB 内存执行所得结果：

| 地址 | peak | peak_blk |
|---|---:|---:|
| `ADDRS[1]` | `10000000000000000000` | 102 |
| `ADDRS[2]` | `5000000000000000000` | 103 |
| `ADDRS[5]` | `0` | null |

前两址与全量 `peaks.json` 对应值一致；正常补算下内存中的全量产物字节不变，逐输入 SHA 和 channels SHA 均复算一致。消费者不验证 channels 同源，仍属于已明确延期的 P13。

**§4 APU 预期有条件成立。** 案根残留 `trigger_days.json` 不是 summary，不会触发“多份 summary”。若子目录 trigger 存在且登记正确，新闸错误集合为：

```text
needs_block_precision.json 缺失或与 peaks_summary 登记的 sha256 不咬合（旧版 peaks_daily 未登记该哈希＝升级脚本重跑）
```

但若只有案根残留、子目录 trigger 缺失，则提前返回：

```text
peaks_summary 声称产出触发日但 trigger_days.json 缺失
```

因此 §4 应补明子目录 trigger 及 summary 其他字段的前提；仅凭“旧格式、无 needs sha”不能确定唯一错误集合。未读取 Desktop，未对真实 APU 文件作现场结论。

验证边界：基线 `invariant_scan` 实跑 **PASS**；其余六个完整测试需要落盘夹具，受只读要求未运行，`run_all` 未运行。D2/D3 取证使用原文函数、内存文件替身及真实 DuckDB SQL；完整 `docs_lint` 会读取禁读内容，故仅核验两份目标文档。

Codex session ID: 01a0afd7-4274-7c81-8c41-3a9001748246
Resume in Codex: codex resume 01a0afd7-4274-7c81-8c41-3a9001748246
