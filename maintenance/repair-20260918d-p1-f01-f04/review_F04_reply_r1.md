# 工单F04复核：退回

共享校验层硬拒的修法成立，可以阻断两种 EVM 重复追加路径；v1 的取证要求和事实说明有以下四处需要修订。

1. **F04-R1-01：RED 证据要求的序列长度错误。**

   工单位置：[§2.3 RED 第 3 项，第 82 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/workorder_F04_retail_bucket.md:82)，关联 §0.7。

   事实：`build_evm_case` 第 187–190 行生成 **四天**的数据。duck 每天执行以下两次追加：

   ```python
   # replay_duck.py:558
               series[c].append(round(v, 4))
   # replay_duck.py:560
           series["散户"].append(round(max(0, 100 - known), 4))
   ```

   因此该工厂的基线应为 `len(dates)=4`、`len(散户)=8`。内存执行生产 `snap()` 得到：

   ```text
   散户 = [0.0, 0, 40.0, 0, 40.0, 10.0, 36.8421, 10.5263]
   ```

   **修订建议：**改为 `len(散户) == 2 * len(dates) == 8`；若保留“长度 2”，明确另建裁决中的单日两笔转账夹具。§0.7 同步写成“§2.2、§2.3 共四项，三项 RED、一项 GREEN 对照”。基线 duck 取证应直接 `run()`，或调用 `build_evm_case(..., expect_rc=0)`；使用 `expect_rc=2` 会先在工厂第 207 行抛出断言，拿不到返回的 `p`。

2. **F04-R1-02：Q5 混淆 producer 与 consumer，并遗漏既有末点对账限制。**

   工单位置：[台账 Q5，第 9 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/code_change_pending.md:9)，关联工单 §4。

   事实：`replay_edges.py` 原生输出分别保留显式「散户」和动态桶：

   ```python
   # replay_edges.py:634-639
       def camp_of(a):
           if a in addr2camp:
               return addr2camp[a]
           if a in snipers:
               return "首30分钟狙击者"
           return "其他散户"
   ```

   并桶发生在 consumer：

   ```python
   # camp_series_provenance.py:66
   SOL_DYNAMIC_BUCKET_MERGE = {"其他散户": "散户", "首30分钟狙击者": "散户"}
   # :318
                   acc[SOL_DYNAMIC_BUCKET_MERGE.get(key, key)] += float(value)
   ```

   此外，`endpoint_reconcile` 第 865 行把显式「散户」计入 `spec_sum`，第 875 行又计算 `100.0 - spec_sum`。内存验证“大庄 60、显式散户 30、其他散户 10”时，转换后散户为 40，既有末点对账同时报“40≠30”和“40≠10”。

   **修订建议：**Q5 写明“producer 分列，consumer 将两个动态桶并入散户；显式散户还可能触发既有末点对账冲突，本轮保留、不修”。`build_evolution` 的标量累加说明可以保留。

3. **F04-R1-03：duck 序列写盘行号错误。**

   工单位置：[§2.3 说明①，第 77 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/workorder_F04_retail_bucket.md:77)。

   `grep -n -F` 实际结果：

   ```text
   567:    out = {"dates": dates, **series}
   577:    json.dump(out, open(f"{out_dir}/camp_series.json", "w"))
   ```

   **修订建议：**把“`:567` 的序列写盘”改成 `:577`。同时明确保证的是“全新输出目录中不生成序列”：duck 在第 467 行校验前，已经执行 pass1 并写出余额、统计等文件，不能表述为拒收前没有任何写盘。

4. **F04-R1-04：检索结果分类及存量结论范围需收窄。**

   工单位置：[§2.1 说明③，第 40 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918d-p1-f01-f04/workorder_F04_retail_bucket.md:40)，关联 Q6。

   事实：按要求执行 `grep -rn '"散户"\s*:' scripts`，没有发现 EVM camps 地址配置中的「散户」键，但命中并非“全是序列值”，还有：

   ```python
   # scripts/report/standard_charts.py:81
       "散户":      "tab:green",
   ```

   当前仓库检索也不能独立证明案外正式案全部为零实例。

   **修订建议：**改为“本仓库未发现 EVM camps 地址配置显式含散户；命中包括序列字段、输出示例和绘图颜色映射”。正式案零实例应明确标为此前 review 的记录；本次未读取禁区中的案卷，未独立核验该记录及 LAYOFF 的“27 处”。

实际核验结果如下；除明确注明的内存改后位置，行号均为施工前基线。

**a）六个完整施工锚均已执行 `grep -n -F`，全部唯一命中且行号正确。**

| 文件 | 锚的识别内容 | 命中数 | 行号 |
|---|---|---:|---:|
| `camp_spec.py` | `"销毁"阵营由引擎自动补列…` | 1 | 22 |
| `camp_spec.py` | `含非法阵营名: {camp!r}` | 1 | 61 |
| `test_repair_batch_c.py` | `F05 空阵营名硬拒` | 1 | 159 |
| 同上 | `dup_spec = {"camps": …}` | 1 | 251 |
| 同上 | `F05 replay_duck 跨营重复 exit2` | 1 | 256 |
| 同上 | `F05 replay_pass2 合法 spec 绿例` | 1 | 272 |

**b）共享校验和副作用。**已全文读取 [camp_spec.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/camp_spec.py:1)。四个 producer 的 camps 结构、规范化及互斥校验确实汇入同一实现：EVM 两入口直接调用，`replay_edges:612` 直接调用，`build_evolution:82 → load_addr_camp_json:114` 间接调用。consumer 的 `_load_camps_spec:788` 也调用它。

内存应用拟议代码后，Solana 显式「散户」直传及 `load_addr_camp_json` 默认 Solana 反转路径都仍接受。非法 `chain_family="x"` 的报错顺序**不变**：有有效地址才进入 `_normalize` 拒收，空列表仍不会校验链名。改变的是 EVM「散户」同时具有非法值类型或地址时，新增保留桶错误会优先出现，退出码仍为 2。

**c）既有回归面：静态核查未发现会因本段直接变红的既有测试。**已解析 `run_all.py` 登记的全部 **143 个 `test_*.py`**，并扫描 `scripts/` 下 310 个 Python 文件，包括单引号及转义后的字符串键。

| 重点测试 | 实际配置或调用 |
|---|---|
| `test_engine_equivalence.py:67` | 阵营A、阵营B、销毁 |
| `test_fault_injection.py:63` | 不传 `--camps`，不执行 camps 序列校验 |
| `test_repair_batch1.py:760/:822` | 项目方、其他大户；另有空 camps |
| `test_repair_batch_d.py:1602` | EVM 为项目方、大庄；`:1135` 为 Solana 空 spec |
| `test_a4_gate.py:238` | spec 仅大庄；`:241` 散户是输出序列 |
| `test_lit_regression_f007.py:50` | spec 为项目方、锁仓/销毁；RETAIL 地址仅在余额表 |

§0.8 未列的 `test_figures_from_facts.py`、`test_state_from_facts.py` 中相关命中也是序列；`test_review_20260804_p105.py:171` 使用空 camps。

`test_repair_batch_c.py:270–275` 的合法绿例及 sidecar 断言仍成立：新增 duck 用例使用独立临时目录；新增 pass2 用例在合法产物生成后拒收，不覆盖原序列或 sidecar。

**d）新用例的 RED/GREEN 关系成立，但须修正 R1-01 的取证数字。**

| 检查 | 基线 | 拟议改后 |
|---|---|---|
| EVM 单元拒收条件 | False | True |
| Solana 接受条件 | True | True |
| duck | rc=0，四天散户八元素 | rc=2，新目录无序列 |
| pass2 | rc=0 | rc=2 |

`check():54–57` 确实会抛异常，逐项独立取证可执行，不能依靠整测试收齐 RED。当前沙箱不能创建测试临时文件，未实跑 `test_repair_batch_c.py`；上述引擎完整流程结论来自静态路径核查，另已执行生产循环及拒收函数的内存验证。

**e）白名单足够，不改项自洽。**无需修改其他既有测试、四个引擎、consumer 或两个 manifest。已实际运行 invariant 扫描的基线及内存改后版本，两者均 exit 0，登记计数一致：producer 81、consumer 118、transport 65、atomic 61、formal entrypoint 61。

`test_batch4_invariant_guards.py` 未实跑其写文件的注入测试，静态未发现新增登记要求。`test_exemption_guards.py` 三个只读检查实际通过，写文件的注入项未运行；新增条件没有引入豁免模块引用。

**f）裁决反例的终点成立，前提是完整合法输入及全新输出目录。**pass1 本身不写 `camp_series.json`；pass2 在原第 57 行、duck 在原第 467 行进入共享校验，在拟议改后 `camp_spec.py:63` 调用 `_fail`，由第 31–32 行打印并 exit 2：

```text
[camp-spec] camps.json 阵营「散户」是 EVM 引擎的残差桶（100−已知阵营），不得在 spec 里配置——显式配置会让 replay_pass2/replay_duck 同日写两个元素；把这些地址归入其他阵营或删掉
```

拒收早于 pass2 第 146 行和 duck 第 577 行的序列写盘。内存执行这两个实际函数的拒收路径，均得到 exit 2、零输出写入尝试。既存序列不会被删除。Solana `validate_camp_spec({"散户":[SA]}, chain_family="solana")` 改前、改后均接受。

来源断言也已核实：pass2 的 `:94–96/:102–106`、duck 的 `:545–548/:555–560` 在零供应和正供应分支都会重复追加；`build_evolution:173–184` 是桶内标量累加、补残差后每时点追加一行，没有该重复问题。

**g）台账。**Q6 保留引擎追加结构、在入口拒绝配置的选择成立。Q7 在允许读取的文档范围内成立：排除 `references/attic.md` 后，`"散户"` 仅命中 `monitoring-package.md:79` 的序列示例及 `playbook-entity-cluster-methods.md:126` 的自然语言描述；未发现 camps 配置示例。`scan-schemas.md:613/:621` 确有残差说明。Q7 提到的 CHANGELOG 应属于后续收官登记，本段仍遵守零改动。

全程离线、未修改文件、未 commit；未读取 `~/.codex/`、memories 或任何其他指定禁区，也未运行会读取历史 maintenance 的测试子进程。
