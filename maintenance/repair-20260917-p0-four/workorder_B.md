# 工单 B（v2）：R03 扩展成员只进上限区间 —— repair-20260917-p0-four 第二段

> 出处：codex 对 7.0.4 的 review（`REVIEW.md` R03，P0）——三账检查汇总时把 strict 与 expanded 成员一起加进 `wallet_self_held_raw`，再要求进 `confirmed_economic_control_raw`；离线反例 strict=100、expanded=200，confirmed=300 零报错。文档面已在 7.1.x 统一为"严格成员＝可证经济控制下限（判级与 TL;DR 主数字），扩展成员只进上限区间"（`references/economic-control-accounting.md:40-44、:93`；`references/playbook-entity-cluster-tiering.md:145、:150`）。用户 2026-09-17 裁决：**改代码贴合现有文档，文档零改动**。
> v2 变更（对 codex r1 六条，见 `review_B_reply_r1.md`）：B-R1-01 字段在场判定改 `in row`；B-R1-02 新用例直调 `check_three_ledgers(chain=None)` 不走四查；B-R1-03 插入点改 `:554` 后；B-R1-04 逐例独立函数取 RED；B-R1-05 上限改验下界（文档允许"疑似设施受益权增量"进上限，三账无其来源字段，只能验 `hi ≥ 下限＋Σexpanded`）；B-R1-06 白名单加停工报告；§B1 说明订正 `:907-909` 无 `continue`。
> 内容基线：`scripts/report/audit_release_gate.py`、`scripts/tests/test_audit_release_gate.py` 与 commit `4cbfe48`（v7.1.3）逐字节相同（A 段白名单不含这两个文件）；`references/`、`SKILL.md`、`commands-staging/` 与 4cbfe48 相同。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `B_done.md`：`git status --short`（须为空）；`git diff --stat 4cbfe48 HEAD -- scripts/report/audit_release_gate.py scripts/tests/test_audit_release_gate.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不空即停工写 `B_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 在 done 里披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`。**禁读** `/Users/uravvv/Desktop` 下任何文件（沙箱也读不到；存量零影响证明由调度方本机跑）。
- 0.3 **白名单**：生产 `scripts/report/audit_release_gate.py`；测试 `scripts/tests/test_audit_release_gate.py`；本目录新建 `B_done.md`、`B_red_evidence.txt`，停工时新建 `B_done_attempt1_stopped.md`。
- 0.4 **不改**：`check_three_ledgers` 里 membership 解析段（`:865-893`，含 `:870` 枚举与 `:877` 的非 excluded 余额绑定）、position 行校验（`:897-916` 除 `:915` 外）、逐地址闭合（`:918-924`）、设施权益校验（`:941-958`）、`:964-967` 实体集合闭合；`check_ledger`（`:584-601`）；任何文档、VERSION、pyproject、CHANGELOG、contract_manifest、invariant_manifest。**不动** 其他测试文件（batch15/batch_d 只跑不改）。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：B3 新用例改动前先跑取 RED 写 `B_red_evidence.txt`，改后取 GREEN。
- 0.8 本段只跑 `python3 -B scripts/tests/test_audit_release_gate.py`、`python3 -B scripts/tests/test_batch15_three_ledgers_frozen.py`、`python3 -B scripts/tests/test_repair_batch_d.py`（后两个是回归，须仍绿）。不跑 run_all。

## 1. 硬约束

- 1.1 文档三处字节不变：SKILL.md 8021、references 930070、commands-staging 8798（命令同工单 A §1.1，只用 stat 不读内容）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 现有 `:516-554`（expanded 0xdef 余额 5 无位置行 → 断言含"逐地址余额"；随后 sha 漂移断言）在新逻辑下仍绿；其余既有断言不改。

## 2. 逐条施工（`scripts/report/audit_release_gate.py` `check_three_ledgers`，`:782` 起）

### B1 位置账汇总按成员边界分流

- `:895`（锚 `    pos_seen, wallet_by_entity, position_by_address = set(), {}, {}`）改为：
  `    pos_seen, wallet_by_entity, expanded_by_entity, position_by_address = set(), {}, {}, {}`
- `:915`（锚 `        wallet_by_entity[entity] = wallet_by_entity.get(entity, 0) + amt`）改为：

```python
        wallet_by_entity.setdefault(entity, 0)   # 实体集合语义不变（:966 用 set(wallet_by_entity)）
        if member_map.get(addr_key, ("", "", None))[1] == "expanded":
            expanded_by_entity[entity] = expanded_by_entity.get(entity, 0) + amt
        else:
            wallet_by_entity[entity] += amt
```

说明：`addr_key` 在 `:906` 已归一（`address.lower() if 0x…`），`member_map[addr_key]` 为 `(entity, status, balance)`。`:907-909` 对未映射/跨实体/excluded 的位置行**只追加错误、不 `continue`**，这类坏行仍会走到本处汇总；它们落入 `else` 分支计入 `wallet_by_entity`，但由于错误已登记，该案必然 FAIL，汇总值无发布意义——这是既有 fail-closed 行为，本段不改。`position_by_address`（`:916`）不变——逐地址闭合对 expanded 仍然适用（文档：expanded 是确权边界不是存放位置边界）。

### B2 经济控制账：wallet/confirmed 只含 strict，区间字段机器校验

`:938-940`、`:959-962` 不改文本（`wallet_by_entity` 现在只含 strict，等式语义自动变为"钱包自持＝严格成员位置之和"、"confirmed＝严格自持＋设施"）。在 `:962`（锚 `            errors.append(f"实体 {entity} 经济控制算术不闭合: {confirmed} != {wallet}+{facility_sum}")`）之后、`:964`（锚 `    active_entities = {entity for entity, status, _ in member_map.values()`）之前插入（缩进与 `:959` 同级，即仍在 `for i, row in enumerate(economics):` 循环体内）：

```python
        # R03（2026-09-17）：expanded 成员只进上限区间，不进可证下限。区间用重算值校验
        # （不信自报 confirmed）：下限＝严格自持＋已闭合设施；上限 ≥ 下限＋expanded 成员位置之和
        # （文档 economic-control-accounting §3 允许上限再含"疑似但未确权的设施受益权增量"，
        # 三账无该增量的来源字段，故上限只验下界——超出部分属登记的残余风险 P10）。
        want_lo = wallet + facility_sum
        min_hi = want_lo + expanded_by_entity.get(entity, 0)
        has_expanded = any(e == entity and s == "expanded" for e, s, _ in member_map.values())
        if "expanded_economic_control_range_raw" not in row:
            if has_expanded:
                errors.append(f"实体 {entity} 有 expanded 成员但缺 expanded_economic_control_range_raw"
                              f"（须为 [{want_lo}, ≥{min_hi}]）")
        else:
            rng = row.get("expanded_economic_control_range_raw")
            if not isinstance(rng, list) or len(rng) != 2:
                errors.append(f"economic[{i}].expanded_economic_control_range_raw 须为 [下限, 上限] 两元素数组")
            else:
                lo = raw_int(rng[0], f"economic[{i}].expanded_economic_control_range_raw[0]", errors)
                hi = raw_int(rng[1], f"economic[{i}].expanded_economic_control_range_raw[1]", errors)
                if lo != want_lo or hi < min_hi:
                    errors.append(f"实体 {entity} expanded 区间不闭合: [{lo}, {hi}] 须满足下限 == {want_lo}"
                                  f"（严格自持＋设施）且上限 >= {min_hi}（下限＋expanded 成员位置之和）")
```

裁决（已定）：实体有 ≥1 个 expanded 成员 → 字段必填；无 expanded 成员 → 字段可缺；**在场**（含显式 `null`）则必须是两元素数组且 `lo == confirmed 重算值`、`hi ≥ lo`（无 expanded 时 `hi > lo` 的部分＝疑似设施增量，允许）。`raw_int` 为本文件既有辅助（`:601`，非法返回 0 并登记错误；`:914` 同款用法）。非法端点会同时产生 raw 整数错误与区间错误，用例只断言包含式子串。

### B3 测试 `scripts/tests/test_audit_release_gate.py`

**插入点**：`:554`（锚 `        assert any("balance_source sha256" in x for x in errors), errors`，该 `with` 块 `:517-554` 的最后一行）之后、`:556`（锚 `    # P2-01：零余额成员可用显式 zero_balance_proof，位置账缺行按 0 闭合。`）之前，保持 `:517-554` 块完整。新增内容（缩进与 `:556` 同级，仍在 `main()` 内）：

1. 一个夹具函数 `_r03_fixture(root, *, expanded_amount="200", position_expanded=True, econ_overrides=None, drop_range=False)`：`build_case(root, historical=False)`；重写 `balances_snapshot.json` 为 `0xabc:"100"`＋`0xdef:expanded_amount`（`as_of_block` 123，schema 同 `:520`）；membership 各行 `balance_source.sha256` 同步并追加 `0xdef` expanded 行（形如 `:527-533`，`as_of_balance_raw`＝expanded_amount）；position 视 `position_expanded` 追加 `{"entity_id":"e1","address":"0xdef","location_id":"wallet:0xdef","amount_raw":expanded_amount}`；economic e1 行设 `wallet_self_held_raw:"100"`、`confirmed_economic_control_raw:"100"`、`expanded_economic_control_range_raw:["100", str(100+int(expanded_amount))]`，再 `update(econ_overrides or {})`，`drop_range` 时 `pop` 该键。**不必**同步 `audit_input_manifest.json`/`reproduce_receipt.json`/四查 owner 快照——本段用例不走 `gate.run`。
2. 一个直调封装 `_r03_errors(root)`：`data = {n: json.loads((root/n).read_text()) for n in ("membership_ledger.json","position_ledger.json","economic_control_ledger.json")}`；`errors=[]`；`gate.check_three_ledgers(root, data, errors, chain=None)`；返回 `errors`（`chain=None` 跳过 B-7 四查，与 `run()` 对无 chain 案的路径一致；`balance_source` 的 sha 绑定仍在 `:877` 段生效，因此夹具必须同步 sha）。
3. 用例各为独立子函数 `_r03_case_1..10(td)`（各自 `tempfile.TemporaryDirectory()` 内建夹具），由一个循环逐例执行、逐例捕获 `AssertionError` 并汇总（写法照 A 段 `test_repair_batch_c.py` 的 `_r08_case_*`/`t_r08_nonfinite`），最后全部通过才继续：

| # | 名称 | 夹具 | 断言 | 基线 |
|---|---|---|---|---|
| 1 | R03 绿例 | 默认（strict 100 + expanded 200，range ["100","300"]） | `errors == []` | RED：`钱包自持与位置账不闭合: 100 != 300` |
| 2 | R03 原反例必拒 | overrides `wallet:"300"、confirmed:"300"、range:["300","300"]` | 含 `钱包自持与位置账不闭合: 300 != 100` | RED：基线 `[]`（R03 缺陷本体） |
| 3 | R03 上限低于下界拒 | range `["100","250"]` | 含 `expanded 区间不闭合` | RED：基线不验 |
| 4 | R03 下限不等拒 | range `["90","300"]` | 含 `expanded 区间不闭合` | RED |
| 5 | R03 上限含疑似设施增量放行 | range `["100","350"]` | `errors == []` | RED（基线报 100 != 300） |
| 6 | R03 形状错拒 | range `["100"]` | 含 `两元素数组` | RED |
| 7 | R03 显式 null 拒 | range `None`（JSON null，键在场） | 含 `两元素数组` | RED |
| 8 | R03 有 expanded 缺字段拒 | `drop_range=True` | 含 `缺 expanded_economic_control_range_raw` | RED |
| 9 | R03 无 expanded 缺字段放行 / 在场须合法 | `build_case` 原样（仅 strict 0xabc，economic 无 range）→ `_r03_errors` 不含 `expanded`；再给 economic 加 range `["100","99"]` → 含 `expanded 区间不闭合`；加 `["100","150"]` → 不含 `expanded` | 前半基线同（回归）；`["100","99"]` 基线不验（RED） |
| 10 | R03 逐地址闭合对 expanded 仍生效 | `position_expanded=False`（range 照默认） | 含 `逐地址余额` | 基线同报（回归） |

RED 证据：改生产代码前把新块装好后单独跑该循环（每例独立，互不短路），记录每例 `AssertionError` 原文到 `B_red_evidence.txt`（预期 RED：1/2/3/4/5/6/7/8 与 9 的后半；10 与 9 的前半为回归）；改后整文件 PASS。

## 3. 完成报告 `B_done.md` 必含

①0.1 输出；②B1/B2 diff 原文；③RED 摘要（逐例）；④三个测试文件结果尾行；⑤§1.1 三字节数；⑥`git diff --stat`；⑦差异/停工点；⑧禁读披露。stdout 首行 `# 施工 B：完成` / `# 施工 B：停工`。

## 4. 调度方本机验收项（施工方不做）

- 存量零影响：对 `APU分析0801`（全库唯一有三账的案，28 strict/6 excluded/0 expanded）改前改后各跑一次 `check_three_ledgers(chain=None)`，均须 `[]`。
- 登记不修（`code_change_pending.md`）：P10＝上限超出"下限＋Σexpanded"的部分（文档允许的疑似设施受益权增量）无账本来源，发布闸不验其数额与证据。
