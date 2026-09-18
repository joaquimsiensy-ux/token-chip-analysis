# 工单F05复核：退回

v1 存在确定回归和不可执行的测试前提，不能按现文本施工。共 **8 项修订意见**。完整报告已打印到 stdout；本轮未修改文件、未执行完整测试套件。

受审文件：[workorder_F05.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F05.md)。

开工 HEAD 为 `4931098e`，复核期间变为 `dae44c39`；两提交间受审工单及 `scripts/` 无差异。前后工作树均干净，`scripts/` 与 `311e6c4` 无差异。

**F05-R1-01｜P1：decimals 检查会进入 stage2，破坏现有绿例。**

工单位置：§2.3 第 84、90–108 行；§1.3 第 21 行；§4 第 139 行。

事实：[stage2_closeout.py:578](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:578) 实际调用：

```python
audit_release_gate.check_facts_vs_ledgers(case, load(case, "facts.json"), errors)
```

`test_report_facts.py:206–207` 同样不传 accounting，并断言 `errors == []`。拟议参数默认 `None`，但新增检查仍执行，必然追加：

```text
facts.token.decimals 无链上观测来源可核（accounting_mode/对账收据缺 decimals）
```

内存隔离演算确认：相同合法输入，原函数返回 `[]`，拟议函数返回上述错误。stage2 的 `facts_vs_ledgers` record 会变 BLOCK；`test_stage2_reseal.py:21、54` 复用该路径，也受影响。这不属于 F12。

修订建议：将 decimals 检查限定在 `_run` 的 `new-analysis` 分支，保留共享函数的原用途；同步明确 §0.4 允许修改该调用块。§0.8 增加 `test_stage2_reseal.py` 的相关回归检查，无须修改 stage2 生产代码或放宽断言。

**F05-R1-02｜P1：Solana 链名未归一化，会误走 EVM 分支。**

工单位置：§2.3 第 91–101 行。

事实：

```text
scripts/solana/accounting_gate_sol.py:137
    result = {"schema": "accounting-gate/v1", "chain": "solana", "mint": a.mint,
scripts/tests/test_repair_batch_d.py:976
        "schema": "accounting-gate/v1", "chain": "solana", "mint": SOL_MINT,
```

工单直接判断 `chain == "sol"`，因此真实链名 `"solana"` 会进入 EVM 分支。现有 Solana 夹具的 `balance.inputs.config` 指向 `fixture_replay_stats.json`（`:1018–1020`），其中只有 mint/burn 字段，没有 decimals。

**即使补齐 accounting.checks.decimals，当前代码仍取不到它。**

修订建议：复用已有 `normalize_chain`／`resolve_alias`，归一化后分支；增加使用生产者实际链名 `"solana"` 的正例。

**F05-R1-03｜P1：Solana 夹具确定缺 decimals，白名单必须扩展。**

工单位置：§0.3–0.4 第 10–11 行；§2.3 说明④第 111 行。

事实：正式生产者 `accounting_gate_sol.py:226` 确实写：

```python
result["checks"]["decimals"] = info.get("decimals")
```

但 `test_repair_batch_d.py:984` 的夹具只有：

```python
"checks": {"fot": {"status": "clean"}}})
```

该测试文件不在白名单。修复链名后，B-2、R07、F-D8 发布绿例仍会因缺 decimals 失败，见 `:1250–1252、:1286、:1557`。

修订建议：将 `scripts/tests/test_repair_batch_d.py` 纳入白名单，仅允许在 `build_solana_case` 的 accounting checks 中增加 `decimals=0`，与观测夹具 `:893` 和 facts 默认值一致。应在收据绑定前完成，无须改生产者。

**F05-R1-04｜P1：证据迁移漏掉现有 R07 合法 override 用例。**

工单位置：§2.4 第 115–123 行；§1.4 第 22 行。

事实：[test_report_facts.py:153](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_report_facts.py:153) 仍使用旧格式：

```python
evidence = _r07_write(root, "peak_evidence.json", {"note": "observed peak"})
ov = {"peak_raw": "160", "peak_date": "2026-01-03",
```

`:164` 随后直接调用 `derive_facts`。内存演算确认原实现成功，拟议实现抛“证据内容与申报”错误；`run` 的 `:92` 没有捕获 `ValueError`，脚本会中断。

修订建议：明确将此证据迁移为：

```json
{"e1":{"peak_raw":"160","peak_date":"2026-01-03"}}
```

保留合法、坏哈希、缺证据三种断言。该文件已在白名单。

§1.4 还应补齐迁移链：重建 facts 后，至少须重出 Figure 2 收据；`audit_release_gate.py:1572` 会复核 facts 哈希，已有 stage2 收据也通过 `stage2_closeout.py:605、657` 绑定 facts。“重 build”没有覆盖全部迁移成本。

**F05-R1-05｜P1：decimals a/b 的起点夹具不成立，备用夹具也不完整。**

工单位置：§2.4 第 124–126 行；§0.3 白名单。

事实：`NEW_ANALYSIS_REQUIRED` 位于 `audit_release_gate.py:44–54`，逐项核对如下：

| 必需资产 | `build_case(..., historical=False)` | `build_release_case(root)` |
|---|---|---|
| `distribution_scan.json` | 无 | 有 |
| `distribution_rounds.json` | 无 | 有 |
| `a5_report_seal.json` | 无 | 无 |
| `fig1_legend_receipt.json` | 无 | 无 |
| `figure2_check_receipt.json` | 无 | 无 |
| `facts.json` | 无 | 有 |

更早的阻断是：`build_case :271–476` 不生成 `identity_gate.json`，而 `facts_gate.py:336` 必读它。因此原定两个助手连用会先在 facts 构建处失败，不能取得 a 所称的“基线 `[]`”。

备用 `build_release_case` 是阶段 2 夹具；`test_stage2_closeout.py:177–180` 明确检查三个阶段 3 资产不存在。仅换该函数仍不够。b 只断言“没有 decimals 字样”也不能证明放行。

修订建议：采用已有完整 EVM 路径：

```text
build_case
→ test_review_20260804_p105.add_new_analysis_distribution
```

后者位于 `:141–251`，`:261` 已有 new-analysis 零错误断言。给它增加默认 `decimals=0` 参数，在 `:214` 构建 facts 时传入，使 0/2 两案都在 Figure 2、A5 产出前形成目标 facts。

需要将 `scripts/tests/test_review_20260804_p105.py` 的夹具参数及传参行加入白名单；新增 a/b 可继续留在 `test_audit_release_gate.py`。基线先证明两案均 `errors == []`；修后 a 只出现目标错误，b 仍须 `errors == []`。

**F05-R1-06｜P2：日期解析未落实宣称的 YYYY-MM-DD 格式。**

工单位置：§2.2 第 69–77 行；§2.4 用例 19。

事实：当前解释器的 `date.fromisoformat` 实测接受：

```text
20260102    → 2026-01-02
2026-W01-5  → 2026-01-02
```

拟议代码仍把原字符串写入 `facts.peak_date`。用例 19 只能证明明显非法日期被拒。

修订建议：若要求严格 `YYYY-MM-DD`，解析后再要求 `peak_day.isoformat() == peak_date`，并补非标准拼写负例；若允许其他 ISO 日期写法，应修改工单及错误文案，并明确是否归一化产物。

**F05-R1-07｜P2：峰值上界的裁决对象和执行顺序未写清。**

工单位置：§2.1 第 35 行；§4 第 136 行。

事实：同一行为一处要求“本段按总供应为上界落地”，另一处标为“待用户裁决”。规则覆盖所有来源及共享 `gate_check` 消费者。

准确的误拒条件是：**真实 `peak_raw` 超过当前采用的 `total_supply_raw`**。历史供应较大或发生过销毁，并不必然满足这一条件。例如真实历史峰值 150、当前供应 100，才会被此规则拒绝。

修订建议：将裁决点明确为“是否接受对真实历史峰值超过当前供应的案例采取保守阻断”，在施工版写明选定规则及范围。若仍待裁决，应将依赖它的 §2.1 移出无条件施工步骤。普通转入销毁地址也不能一概等同于 `totalSupply` 下降。

**F05-R1-08｜P3：docstring 保护行范围与新增 import 指令冲突。**

工单位置：§0.4 第 11 行；§2.2 第 80 行。

事实：`facts_gate.py` 的模块 docstring 实际为 `:2–71`；imports 为 `:72–78`，没有 datetime。§0.4 写成 `:1–95` 且仅放行一行，按行号执行会覆盖 §2.2 要修改的 import 区。

修订建议：将 docstring 范围校正为 `:2–71`，只允许修改 `:65`；另行明确允许 import 区增加 `datetime as _dt`。

**实际核过的其他项目**

- **锚点：**执行了 44 条 `grep -n -F` 定位，全部恰 1 处且行号一致。全部指定区间均已回读：

| 文件 | 核对区间 |
|---|---|
| `facts_gate.py` | 97–186、191–203、198–199、306–311、314–318、321、357–363、404–420、408、420、421–426、431、454–467；imports 72–78；docstring 锚 65 |
| `audit_release_gate.py` | 111–118、1497–1502、1547–1548、1830–1832 |
| `test_audit_release_gate.py` | 59–60、202–224、271、1156 |
| `test_report_facts.py` | 49–74、77、278–293 |
| `shared_release_receipt.py` | 559–567、592–593、1834–1848、2031–2050 |

- **EVM 收据选择正确：**`shared_release_receipt.py:71、1445、1508、2034–2045` 证明键为 `"balance"`，对象是完整 verify_recon 收据，包含 `inputs.config`。`_bound_json_input` 可直接使用；`:593` 已有相同调用。
- **缓存及异常行为正确：**`run :1755` 建缓存，`:1792` 对账检查早于 `:1831` facts 检查。缓存保存成功对象或异常；后续返回缓存或重抛异常，拟议 `except` 会将异常写入 errors。完整发布路径不会因此重跑深验。
- **真实 provenance 日期不会被格式检查误拒：**`entity_source_trace.py:638` 的 peak 日期来自 `wave_scan.py:87–88`，为 `%Y-%m-%d`。但 `:639` 的 current 锚没有传 date，真实产物通常没有 `anchors.current.date`。因此用例 20 只验证显式补充该字段的分支，不能证明生产产物已有日期上界保护。
- **用例 21 文案成立：**数组证据导致条件短路，抛“证据内容与申报”，不会进入 `_raw_str`。对象内非法 raw 则不同：`None`／`"abc"` 抛 `invalid literal for int()`，负数抛“不得为负”，均不含“证据内容”。
- **现有正例满足 G2：**`facts_obj` 和图表测试峰值占供应 68.7%；`_r07_case` 为 150/1000，合法 override 为 160/1000；state 测试为 4000/10000。共享助手用 confirmed 作为 peak，stage2/a4、Solana、P105 对应夹具均不超供应。额外检查了 batch C 的手写 peak，未发现新增超供给正例。
- **共享助手调用均已核：**stage2 `:76`、batch D `:1205`、P105 `:214`、a4 `:498`。正确迁移助手后都会继承新证据格式；EVM 默认 decimals 与 recon config 均为 0。stage2、Solana 的其他回归仍须分别修复。
- **文档与登记：**R07 CHANGELOG 没有承诺任意 JSON 均可作证据，无须改写历史条目。文档字节数实际为 `8021 / 930061 / 8798`。内存拼接拟议代码后，现有 `invariant_scan.scan_python` 对两个生产文件得到的登记集合均未变化，当前改法无需新增 manifest 项；未运行完整 scanner。

**新增用例的局部 RED/GREEN 核对**

以下演算使用实际 facts 源码及工单代码块，文件 I/O 和三账前置检查使用内存替身，不是端到端发布测试。

| 用例 | 基线行为 | 拟议行为 | 判断 |
|---|---|---|---|
| 16 | 接受 peak=1000000 | 拒绝，包含指定文案 | RED→GREEN 成立 |
| 17 | 接受 peak=150 | 接受 peak=150 | GREEN→GREEN |
| 18 | 接受 peak=2000 | 拒绝，包含“超过总供应” | RED→GREEN 成立 |
| 19 | 接受非法日期 | 拒绝，包含指定文案 | RED→GREEN 成立 |
| 20 | 接受晚于 current.date 的日期 | 拒绝，包含“晚于” | 条件分支成立 |
| 21 | 接受数组证据 | 拒绝，包含“证据内容” | RED→GREEN 成立 |
| a/b | 原夹具无法完成 facts 构建 | 无有效发布对照 | 按 R1-05 重写方案 |

**`run_all.py` 现有用例会变红**：已定位 `test_report_facts`、`test_repair_batch_d`、`test_stage2_closeout`，以及复用 closeout 正例的 `test_stage2_reseal`。这来自源码调用链和局部演算，未冒充 suite 实跑结果。

本轮保持离线、未修改文件、未 commit。首次系统 git 包装器尝试建立 `/tmp/xcrun_db` 缓存，被沙箱拒绝；随后改用实际 CommandLineTools git 完成核验。该环境信息不计入退回条目。