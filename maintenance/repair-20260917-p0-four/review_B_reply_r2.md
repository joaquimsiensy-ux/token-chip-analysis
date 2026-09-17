# 工单B复核：通过

v2 对 r1 六项的处置均已闭合，未发现阻断施工的问题。直调 `check_three_ledgers(chain=None)` 成立；上限改验下界符合文档口径，并继续拒绝原始“自报 300”反例。超额上限缺乏来源校验的问题已登记为 P10，本次未修复该缺口。

本次只读、离线，无文件改动。实际在内存中执行了基线函数和工单 B1/B2 原文补丁，文件存储使用内存替身；审计钩子记录写入、网络、禁读尝试均为 0。**未完整运行 `build_case`、`gate.run`、三个测试脚本或 `run_all.py`；以下不是施工验收或完整回归 PASS。**报告全文已打印到 stdout。

**a｜锚点及基线**

两个目标 Python 文件均与 `4cbfe48` 逐字节相同。§2 六个明确施工锚均经实际 `grep -n -F` 验证，各恰一处：

```text
scripts/report/audit_release_gate.py
895:    pos_seen, wallet_by_entity, position_by_address = set(), {}, {}
915:        wallet_by_entity[entity] = wallet_by_entity.get(entity, 0) + amt
962:            errors.append(f"实体 {entity} 经济控制算术不闭合: {confirmed} != {wallet}+{facility_sum}")
964:    active_entities = {entity for entity, status, _ in member_map.values()

scripts/tests/test_audit_release_gate.py
554:        assert any("balance_source sha256" in x for x in errors), errors
556:    # P2-01：零余额成员可用显式 zero_balance_proof，位置账缺行按 0 闭合。
```

题列其他生产区间、`check_ledger:584`，以及测试 `:151/:246/:352–366/:517–554` 均已回读。`:352` 的通用写账语句有 3 处，`:517` 的通用 `with` 有 18 处；v2 没把它们当作唯一施工锚。AST 确认旧块完整范围为 **517–554**。

**b｜B1 分流**

- 合法位置行取得的成员状态可靠。
- `setdefault(entity, 0)` 保留纯 expanded 实体的键，维持 `:966` 的集合语义；内存绿例已验证。
- `position_by_address` 不变，expanded 缺位置行仍报 `逐地址余额与位置账不闭合: 0 != 200`。
- `:907–909` 只追加错误，不 `continue`。跨实体 expanded 坏行仍可能进入 expanded 分支，但已有映射错误确保拒绝。

**c、d｜B2 与文档**

`wallet` 来自自报字段，但 `:938–940` 已与严格成员位置之和比较。原反例的实际内存结果：

```text
基线：[]

拟改后：
实体 e1 钱包自持与位置账不闭合: 300 != 100
实体 e1 expanded 区间不闭合: [300, 300] 须满足下限 == 300（严格自持＋设施）且上限 >= 500（下限＋expanded 成员位置之和）
```

**第一条错误本身就足以阻断。**后续用自报 wallet 计算区间诊断不会清除该错误，不存在原反例漏网。

`has_expanded` 按成员身份判断，零余额 expanded 也要求字段，已用内存负例验证。缺字段、形状错误、有效整数端点关系错误走不同分支；整数解析错误可能与区间错误叠加。显式 `null` 在有、无 expanded 两种情况下均被拒绝。

已核对两份文档的全部指定行：

- 下限为严格成员钱包加已闭合设施权益，expanded 不进入下限。
- 文档允许强关联设施权益增加上限，因此 `[100,350]`、无 expanded 时的 `[100,150]` 可以合法。
- `lo == want_lo and hi >= min_hi` 消除了旧方案强制上限等于成员钱包合计的矛盾。超额部分的证据仍不验证，[P10 登记](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/code_change_pending.md:14)已明确保留此边界。

**e｜B3 夹具与逐例执行**

v2 实际为 **10 例**。`:795–796` 只有在 `chain` 为真时才调用 `_recon_owner_snapshot`。新封装传 `chain=None`，因此无需同步四查 owner、manifest 或发布收据；余额快照自身的 sha、schema、as_of_block、成员余额及逐地址校验仍执行。

对照执行确认：传 `chain="bsc"` 且 owner 快照缺 `0xdef` 时，仍报 `owner 快照 None 不等值`；补齐后该路径无错误。生产 B-7 没有被改弱。

`align_ledgers_to_owner_snapshot:151` 只取首个 owner 并重写三账，仍不适用于双成员夹具；v2 已不再要求使用它。

下表 RED/GREEN 指**工单规定的断言**；用例 9 各分支分别核对：

| 用例 | 基线 | 拟改后 |
|---|---|---|
| 1 默认绿例 | RED：100 != 300 | GREEN：错误为空 |
| 2 原反例 | RED：错误为空 | GREEN：300 != 100，拒绝 |
| 3 上限 250 | RED：无区间诊断 | GREEN：区间错误 |
| 4 下限 90 | RED：无区间诊断 | GREEN：区间错误 |
| 5 上限 350 | RED：100 != 300 | GREEN：错误为空 |
| 6 一元素数组 | RED：无形状诊断 | GREEN：形状错误 |
| 7 显式 null | RED：无形状诊断 | GREEN：形状错误 |
| 8 expanded 缺字段 | RED：无缺字段诊断 | GREEN：缺字段错误 |
| 9 strict 缺字段／上限 99／上限 150 | 合法分支通过；99 为 RED | 合法分支错误为空；99 被拒 |
| 10 expanded 缺位置 | 原有断言通过 | 逐地址断言仍通过 |

独立子函数加逐例捕获 `AssertionError` 能收齐 RED；施工时须落实明确要求的捕获循环。554 后、556 前插入不会拆开旧块。

现有 `:548` 的“逐地址余额”和 `:554` 的“balance_source sha256”断言，在内存三账路径上均成立。新增缺 range 错误不破坏包含式断言。

**f、h｜回归及全套影响**

- batch15 的真实 `write_ledgers:57–83` 在内存生成两组 strict、无 range 账本，基线和拟改后三账错误均为空；没有给其精确错误数量断言新增诊断来源。
- batch_d 的 `build_solana_case:1056` 使用同步函数生成 strict、无 range 三账。该真实同步函数已在内存执行，改前改后三账均闭合；完整 Solana 验证未运行。
- 检索测试 Python/JSON，唯一已有 expanded 成员定义是 `test_audit_release_gate.py:531`，该负例的包含式断言保留。
- 未发现使 `run_all.py` 现有用例新增失败的代码路径。此结论来自静态分析和上述内存验证，**不能替代全套实跑**。

**g｜保护范围及验收边界**

内存应用补丁后可解析，§0.4 所列保护片段均保持原文。仅用元数据统计得到：

```text
SKILL.md                 8021
references/**/*.md     930070
commands-staging/*.md    8798
```

停工报告已进入白名单。§4 把 APU 存量验收交给调度方，与施工方禁读 Desktop 不冲突；本次未验证 APU 成员数、全库唯一性或改前改后结果。

现役脚本中未发现其他 range 消费者。`run()` 在 `check_ledger` 后调用 `check_three_ledgers`（`:1590–1591`），跨账校验放在后者即可，无须重复实现。

**i｜r1 六项闭合清单**

| 编号 | 结论 |
|---|---|
| B-R1-01 | `in row` 区分缺失与 null，闭合。 |
| B-R1-02 | 专用夹具、直调 `chain=None`、绿例断言错误为空，闭合；限单元测试范围。 |
| B-R1-03 | 554／556 锚保住旧块，闭合。 |
| B-R1-04 | 独立用例、逐例捕获并汇总，闭合。 |
| B-R1-05 | 3/4 拒错界，5/9 接受文档允许的增量，原反例仍拒；P10 已登记，按限定范围闭合。 |
| B-R1-06 | 停工报告加入白名单，闭合。 |

两处**非阻断措辞**宜校准：工单 `:40` 的坏行并非一律进入 else，应写“仍按成员状态分流，但已有错误确保拒绝”；`:70` 的非法端点“会同时”报两类错误应改为“可能同时”。下限为 0 时，非法端点转为 0 后可能仅有整数错误，仍会拒绝；负整数则保留负值并登记错误，并非一律返回 0。

开工与收工工作树状态均为空；两个目标文件 SHA-256 前后一致。未读取禁读路径内容。

Codex session ID: 01a0af4d-95f5-7e50-9e42-c371abbdc8e4
Resume in Codex: codex resume 01a0af4d-95f5-7e50-9e42-c371abbdc8e4
