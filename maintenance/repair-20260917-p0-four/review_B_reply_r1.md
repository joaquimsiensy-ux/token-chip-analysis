# 工单B复核：退回

发现 6 项需修订。B1 的成员分流及 B2 对原始“自报 300”反例的阻断成立；退回原因涉及区间边界、夹具、测试插入位置和 RED 取证。

本次只读、离线、无文件改动。将基线函数及工单补丁提取到内存执行，文件读取和 owner 来源使用内存夹具；写入、网络尝试均为 0。**未运行完整 `gate.run`、三个测试文件或 `run_all.py`，下述内存结果不代表完整回归 PASS。**

**B-R1-01：显式 `null` 绕过“字段在场必须有效”的裁决**

工单位置：[B2，第 51–66 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_B.md:51)。

代码原文：

```python
rng = row.get("expanded_economic_control_range_raw")
if rng is None:
    if has_expanded:
```

`get()` 无法区分字段缺失与显式 `null`。内存执行确认：仅 strict、wallet/confirmed 均为 100、range 为 `null`，改后三账错误仍为 `[]`，违反第 66 行“在场则必须 `[c,c]`”。

修订建议：用字段成员判断或独立 sentinel 区分缺失；在场的 `null` 进入“两元素数组”错误分支，并补相应用例。

**B-R1-02：推荐同步函数不适用，绿例断言还能漏掉 B-7 错误**

工单位置：[B3，第 70–72 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_B.md:70)。

实际 `grep -n -F` 结果：

```text
159:    addr, raw = next(iter(owners.items()))
167:        {"entity_id": "e1", "address": addr, "membership": "strict",
```

来源：[测试同步函数](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_audit_release_gate.py:151)。它只取 owner 快照第一项，重写余额快照和全部三账，不会保留 `0xdef` expanded 成员，也不会把该地址加入四查 owner 实物。内存执行已确认这一覆盖行为。

另外，漏同步四查 owner 时，拟改函数产生：

```text
membership[0].balance_source 地址 0xdef 余额 200 与四查 owner 快照 None 不等值
```

此错误不含“闭合”“expanded”“区间”，所以工单的绿例断言仍通过。

只更新 owner 文件及哈希也不够：[收据深验](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/shared_release_receipt.py:627)还重算余额总和、Top-N 地址及观测结果；余额从单址 100 变为两址合计 300，需要同步相关收据和 shared receipt。

修订建议：明确建立保留 strict/expanded 两成员的专用夹具，完整同步四查证据及其绑定；绿例改为 `assert errors == [], errors`。不要直接用现有单成员同步函数完成此事。

**B-R1-03：新增测试块的插入边界自相矛盾**

工单位置：[B3，第 70 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_B.md:70)。

工单要求“`:548` 所在 `with` 块结束后、`:550` 之前”，但 AST 确认原块范围是 **517–554**。原文：

```text
548:        assert any("逐地址余额" in x for x in errors), errors
550:        # 来源哈希不能由成员账自报漂移。
...
554:        assert any("balance_source sha256" in x for x in errors), errors
```

`:550–554` 仍使用原块的 `root`、`members`、`report`。在 548 后插入同级 `with` 会改变这些旧语句所属的块及夹具上下文。

修订建议：新块放在 **554 后、556 前**，保持原 517–554 块完整；以 554 的唯一断言作锚。

**B-R1-04：顺序运行新块不能收齐规定的五项 RED**

工单位置：[B3 第 72–81 行及 §3 第 85 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_B.md:72)。

基线执行用例 1 就产生：

```text
实体 e1 钱包自持与位置账不闭合: 100 != 300
```

因此用例 1 的绿例断言先失败。按顺序运行整文件，或仅把整个新块抽成一个函数，都会在这里停止，无法取得要求的用例 **2/3/4/5/7** 的逐例失败证据。

修订建议：各例重建夹具并可独立调用，分别执行并记录所要求的 RED；改后再运行整文件。

**B-R1-05：B2 的上限公式没有覆盖文档允许的扩展设施权益**

工单位置：[B2 第 49、66 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_B.md:49)。

拟改公式：

```python
want_hi = want_lo + expanded_by_entity.get(entity, 0)
```

但文档原文为：

```text
economic-control-accounting.md:41:
强关联扩展范围：地址或设施受益权高度疑似但未达到确权门槛的增量。
```

[tiering 第 145 行](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-tiering.md:145)同样允许“尚未确权的受益权范围”。

例如严格钱包 100、expanded 钱包 200，另有强关联设施权益增量 50，文档允许上限包含该增量；B2 固定要求上限 300，会拒绝 `[100,350]`。没有 expanded 地址时强制退化区间，也会排除单独存在的扩展设施权益。

修订建议：明确并实现扩展设施增量的证据输入及上限算法，补相应用例。当前只能确认**成员钱包部分**与文档一致，不能确认全部经济控制范围已一致；不得把疑似设施权益塞进 confirmed 项凑等式。

**B-R1-06：停工产物未列入白名单**

工单位置：[§0.1、§0.3，第 8–10 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_B.md:8)。

§0.1 要求异常时写 `B_done_attempt1_stopped.md`，§0.3 只允许新建 `B_done.md`、`B_red_evidence.txt`，两条无法同时遵守。

修订建议：把停工报告明确加入白名单。

**实际核验结果**

- **a｜锚点与基线。** 两个目标 Python 文件与 `4cbfe48` 逐字节相同。§2 明确标注的六个锚均经实际 `grep -n -F` 验证，恰一处，行号分别为生产文件 **895、915、962、964**，测试文件 **548、550**。题列其他生产区间、`check_ledger:584`，以及测试 **151、246、352–366、517–548、550** 均已回读。`:517` 的通用 `with` 语句出现 18 次，不能单独作唯一锚；工单明确给出的锚没有此问题。
- **b｜B1。** 合法位置行的成员状态可靠；`setdefault(entity, 0)` 保留纯 expanded 实体在 `wallet_by_entity` 中的键，实体集合闭合语义保住；`position_by_address` 不变，expanded 逐地址闭合仍生效。须纠正第 39 行说明：`:907–909` 是追加错误，**没有 `continue`**，坏行仍会执行汇总；已有错误保证其不能通过，并非所有执行到这里的行都只可能是 strict/expanded。
- **c｜B2。** `wallet` 来自自报字段，但 `:938–940` 已与严格成员重算余额比较。自报 300 的用例改后必含 `钱包自持与位置账不闭合: 300 != 100`，足以阻断；还会报区间 `[300,300] != [300,500]`。这不是漏网点。`has_expanded` 按成员身份判断，零余额 expanded 也要求字段。普通缺失、形状错误、合法整数端点不匹配走不同分支；非法端点可能同时产生 raw 整数错误和区间错误，不能宣称所有数值诊断严格互斥。
- **d｜文档。** 严格成员加已确权设施权益作为下限、expanded 不进入下限，与所列文档一致；完整上限语义存在 B-R1-05。
- **e｜八例。** 在 owner 来源已同步的内存夹具中，执行真实三账函数及工单原样补丁，结果如下。“通过/失败”指工单要求的断言：

| 用例 | 基线断言 | 拟改后断言 |
|---|---|---|
| 1 绿例 | 失败：100 != 300 | 通过，三账无错误 |
| 2 原反例必拒 | 失败：三账无错误 | 通过，300 != 100 |
| 3 上限错误 | 失败：无区间诊断 | 通过 |
| 4 形状错误 | 失败：无形状诊断 | 通过 |
| 5 expanded 缺字段 | 失败：无缺字段诊断 | 通过 |
| 6 strict 缺字段 | 通过 | 通过 |
| 7 strict 非退化区间 | 失败：无区间诊断 | 通过 |
| 8 expanded 缺位置 | 通过 | 通过 |

- **既有 516–548 用例。** 改后仍报 `逐地址余额与位置账不闭合: 0 != 5`，原断言成立；新增缺 range 错误不会破坏该包含式断言。
- **f｜其他回归。** batch15 的 `write_ledgers:57–83`、batch_d 的 `build_solana_case` 均生成 strict 成员且无 range，B1/B2 不为它们新增错误；batch15 的精确错误数量断言因此没有新增错误来源。搜索测试 Python/JSON 后，唯一已有 expanded 成员定义是 `test_audit_release_gate.py:531`。
- **g｜保护范围和同族消费者。** 内存补丁保持 §0.4 所列保护代码片段原文不变。按 `stat` 得到 **8021 / 930070 / 8798**，与 §1.1 一致。现役脚本中未发现其他 range 消费者；`run()` 在 `check_ledger` 后调用 `check_three_ledgers`，无须在前者重复实现跨账区间计算。§4 的 `chain=None` 会跳过 B-7，验收范围仅为三账闭合；APU 的实际成员数、全库唯一性及改前改后结果，本次未验证。
- **h｜全套回归影响。** 静态检查及上述内存执行未发现 B1/B2 必然使既有测试变红；B3 的插入边界必须先修正。完整测试和 `run_all.py` 未运行，不能给出全套 PASS。

开工、收工工作树状态均为空；两个目标文件 SHA-256 前后一致。

Codex session ID: 01a0af41-b227-7d31-9b66-a134af83f6a5
Resume in Codex: codex resume 01a0af41-b227-7d31-9b66-a134af83f6a5
