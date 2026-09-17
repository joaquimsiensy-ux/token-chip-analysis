# 工单 B（v1）：R03 扩展成员只进上限区间 —— repair-20260917-p0-four 第二段

> 出处：codex 对 7.0.4 的 review（`REVIEW.md` R03，P0）——三账检查汇总时把 strict 与 expanded 成员一起加进 `wallet_self_held_raw`，再要求进 `confirmed_economic_control_raw`；离线反例 strict=100、expanded=200，confirmed=300 零报错。文档面已在 7.1.x 统一为"严格成员＝可证经济控制下限（判级与 TL;DR 主数字），扩展成员只进上限区间"（`references/economic-control-accounting.md:40-44、:93`；`references/playbook-entity-cluster-tiering.md:145、:150`）。用户 2026-09-17 裁决：**改代码贴合现有文档，文档零改动**。
> 内容基线：`scripts/report/audit_release_gate.py`、`scripts/tests/test_audit_release_gate.py` 与 commit `4cbfe48`（v7.1.3）逐字节相同（A 段白名单不含这两个文件）；`references/`、`SKILL.md`、`commands-staging/` 与 4cbfe48 相同。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `B_done.md`：`git status --short`（须为空）；`git diff --stat 4cbfe48 HEAD -- scripts/report/audit_release_gate.py scripts/tests/test_audit_release_gate.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不空即停工写 `B_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 在 done 里披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`。**禁读** `/Users/uravvv/Desktop` 下任何文件（沙箱也读不到；存量零影响证明由调度方本机跑）。
- 0.3 **白名单**：生产 `scripts/report/audit_release_gate.py`；测试 `scripts/tests/test_audit_release_gate.py`；本目录新建 `B_done.md`、`B_red_evidence.txt`。
- 0.4 **不改**：`check_three_ledgers` 里 membership 解析段（`:865-893`，含 `:870` 枚举与 `:877` 的非 excluded 余额绑定）、position 行校验（`:897-916` 除 `:915` 外）、逐地址闭合（`:918-924`）、设施权益校验（`:941-958`）、`:964-967` 实体集合闭合；`check_ledger`（`:584-601`）；任何文档、VERSION、pyproject、CHANGELOG、contract_manifest、invariant_manifest。**不动** 其他测试文件（batch15/batch_d 只跑不改）。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：B3 新用例改动前先跑取 RED 写 `B_red_evidence.txt`，改后取 GREEN。
- 0.8 本段只跑 `python3 -B scripts/tests/test_audit_release_gate.py`、`python3 -B scripts/tests/test_batch15_three_ledgers_frozen.py`、`python3 -B scripts/tests/test_repair_batch_d.py`（后两个是回归，须仍绿）。不跑 run_all。

## 1. 硬约束

- 1.1 文档三处字节不变：SKILL.md 8021、references 930070、commands-staging 8798（命令同工单 A §1.1）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 现有 `:516-548`（expanded 0xdef 余额 5 无位置行 → 断言含"逐地址余额"）在新逻辑下仍绿；其余既有断言不改。

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

说明：`addr_key` 在 `:906` 已归一（`address.lower() if 0x…`），`member_map[addr_key]` 为 `(entity, status, balance)`；`:907-908` 已保证位置行地址映射到同实体的非 excluded 成员，故此处只会遇到 strict/expanded。`position_by_address`（`:916`）不变——逐地址闭合对 expanded 仍然适用（文档：expanded 是确权边界不是存放位置边界）。

### B2 经济控制账：wallet/confirmed 只含 strict，区间字段机器校验

`:938-940`、`:959-962` 不改文本（`wallet_by_entity` 现在只含 strict，等式语义自动变为"钱包自持＝严格成员位置之和"、"confirmed＝严格自持＋设施"）。在 `:962`（锚 `            errors.append(f"实体 {entity} 经济控制算术不闭合: {confirmed} != {wallet}+{facility_sum}")`）之后、`:964`（锚 `    active_entities = {entity for entity, status, _ in member_map.values()`）之前插入（缩进与 `:959` 同级，即仍在 `for i, row in enumerate(economics):` 循环体内）：

```python
        # R03（2026-09-17）：expanded 成员只进上限区间，不进可证下限——
        # 区间用重算值校验（不信自报 confirmed），文档 economic-control-accounting §3/§5。
        want_lo = wallet + facility_sum
        want_hi = want_lo + expanded_by_entity.get(entity, 0)
        has_expanded = any(e == entity and s == "expanded" for e, s, _ in member_map.values())
        rng = row.get("expanded_economic_control_range_raw")
        if rng is None:
            if has_expanded:
                errors.append(f"实体 {entity} 有 expanded 成员但缺 expanded_economic_control_range_raw"
                              f"（须为 [{want_lo}, {want_hi}]）")
        elif not isinstance(rng, list) or len(rng) != 2:
            errors.append(f"economic[{i}].expanded_economic_control_range_raw 须为 [下限, 上限] 两元素数组")
        else:
            lo = raw_int(rng[0], f"economic[{i}].expanded_economic_control_range_raw[0]", errors)
            hi = raw_int(rng[1], f"economic[{i}].expanded_economic_control_range_raw[1]", errors)
            if (lo, hi) != (want_lo, want_hi):
                errors.append(f"实体 {entity} expanded 区间不闭合: [{lo}, {hi}] != [{want_lo}, {want_hi}]"
                              "（下限＝严格自持＋设施，上限＝下限＋expanded 成员位置之和）")
```

裁决（已定）：实体有 ≥1 个 expanded 成员 → 字段必填；无 expanded 成员 → 字段可缺，在场则必须 `[c, c]`。`raw_int` 为本文件既有辅助（`:914` 同款用法）。

### B3 测试 `scripts/tests/test_audit_release_gate.py`

在 `:548`（锚 `        assert any("逐地址余额" in x for x in errors), errors`）所在 `with` 块结束后、`:550`（锚 `        # 来源哈希不能由成员账自报漂移。`）之前，新增一个 `with tempfile.TemporaryDirectory() as td:` 块（夹具手法照 `:517-546`：`build_case(root, historical=False)`、改 `balances_snapshot.json` 加 `0xdef`、同步 membership 各行 `balance_source.sha256`、同步 `audit_input_manifest.json` 的 size/sha 与 `reproduce_receipt.json` 的 manifest sha；四查 owner 快照绑定（B-7）若要求 `0xdef` 在 owner 快照内，用本文件 `align_ledgers_to_owner_snapshot(root, snap)`（`:151`）或同法同步，使绿例除本段关注点外无其他错误）。用例：

1. `R03 绿例`：membership 加 `{"entity_id":"e1","address":"0xdef","membership":"expanded","as_of_balance_raw":"200",balance_source 同上}`；position 加 `{"entity_id":"e1","address":"0xdef","location_id":"wallet:0xdef","amount_raw":"200"}`；economic e1 改 `wallet_self_held_raw:"100"、confirmed_economic_control_raw:"100"、expanded_economic_control_range_raw:["100","300"]` → `gate.run` 的 errors 中**不含**任何含 `闭合`、`expanded`、`区间` 字样的条目。
2. `R03 原反例必拒`（**RED**）：同上但 economic e1 写 `wallet:"300"、confirmed:"300"、range:["300","300"]` → errors 含 `钱包自持与位置账不闭合: 300 != 100`。基线上此案三账检查零错误（即 R03 缺陷）。
3. `R03 区间上限错拒`：绿例但 range `["100","250"]` → errors 含 `expanded 区间不闭合`。RED：基线不验该字段。
4. `R03 区间形状错拒`：range `["100"]` → errors 含 `两元素数组`。RED 同上。
5. `R03 有 expanded 缺字段拒`：绿例删掉 range 字段 → errors 含 `缺 expanded_economic_control_range_raw`。RED 同上。
6. `R03 无 expanded 缺字段放行`：`build_case` 原样（仅 strict 0xabc）→ errors 不含 `expanded`（基线也如此，非 RED，回归）。
7. `R03 无 expanded 非退化区间拒`：`build_case` 原样但 economic 加 range `["100","101"]` → errors 含 `expanded 区间不闭合`。RED：基线不验。
8. `R03 逐地址闭合对 expanded 仍生效`：绿例但删掉 0xdef 的 position 行（range 改 `["100","100"]`）→ errors 含 `逐地址余额`（基线同样报，回归）。

RED 证据：改生产代码前只跑新块（可临时把新块抽成函数或直接跑整文件记录相关 assert 失败原文），写 `B_red_evidence.txt`；改后整文件 PASS。

## 3. 完成报告 `B_done.md` 必含

①0.1 输出；②B1/B2 diff 原文；③RED 摘要（用例 2/3/4/5/7）；④三个测试文件结果尾行；⑤§1.1 三字节数；⑥`git diff --stat`；⑦差异/停工点；⑧禁读披露。stdout 首行 `# 施工 B：完成` / `# 施工 B：停工`。

## 4. 调度方本机验收项（施工方不做）

- 存量零影响：对 `APU分析0801`（全库唯一有三账的案，28 strict/6 excluded/0 expanded）改前改后各跑一次 `check_three_ledgers`，均须 `[]`：
  `python3 - <<'EOF'` … `sys.path[:0]=['scripts/report','scripts/lib']; import audit_release_gate as g; c=Path('…/APU分析0801'); d={n:json.load(open(c/n)) for n in (三账)}; e=[]; g.check_three_ledgers(c,d,e,chain=None); print(e)` `EOF`
