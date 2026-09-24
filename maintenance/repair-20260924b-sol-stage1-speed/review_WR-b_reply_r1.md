# 登记单WR-b复核r1：通过

本单的填实值、追加方式和验收路径可执行，未发现阻断登记的问题。先纠正两处任务描述：**WR-b 追加两条，不是四条；W4 repair 夹具位于 `test_sqd_gap_repair.py`，不是 probe 测试文件。** 本结论是登记单复核通过，不代表已经施工或完成登记后验收。

**a）commit 与 SHA：通过。**

- HEAD：`96c60c70c60de2ea0465466338ac920a60d722ea`，复核前后工作树均干净。
- `git merge-base --is-ancestor` 确认 `<CODE_COMMIT>` 是 HEAD 的祖先，退出码 0。
- `git log -1 -- scripts/solana/sqd_coverage_probe.py` 得到 `f78b5c4575ebe1db36f2cf3a96e75b79731f3fc6`，确为该脚本最后一次改动的 commit。
- Git 对象与工作树分别计算的 SHA256 均为：

```text
d4adc0c88f87bc03b3d847db7df9c9f7e588cb503734dfd977b818b581d998d8
```

与工单填值完全一致。

**b）注册表追加结构及旧条目状态：通过。**

现有 38 条记录均使用 `script / sha256 / commit / protocol / status / reason` 六字段；元组闭合确在 `:315`。`c4980c984b08d27f5a7e46db50f97c9c16e47ea491f37a459b3773f939218769` 的 coverage、coverage-pointer 两条记录均为 ACTIVE。按相同结构追加两条可行，追加后共 40 条。

**无需撤销旧 ACTIVE。** 文件头 `:3-6` 要求登记哈希能由 Git 复现，没有“一个协议只能有一个 ACTIVE”的要求。查询函数返回所有匹配的 ACTIVE 哈希，并对 REVOKED 作排除；保留历史生产者正是现有机制。因此“保留全部既有条目不改”与登记纪律一致。依据：[producer_history.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/producer_history.py:318)。

**c）0.4 对注册表守卫的覆盖：通过，并做了内存验证。**

真实工作树实跑：

```text
python3 -B scripts/tests/test_producer_registry_current.py
producer registry: 2 FAIL
退出码：1
```

失败恰好是 probe 的两个协议；repair 四协议、其他当前生产者检查及全部 38 条历史记录的 Git 复现检查均通过。

随后仅在 Python 进程内追加工单规定的两条记录，保持 `historical_producer_hashes` 函数不变，再运行同一守卫：

```text
53 项检查通过
producer registry: 0 FAIL
退出码：0
```

这是**内存模拟结果**，没有修改注册表文件，不能替代施工后的真实运行；但足以验证本次两条追加能消除全部现有失败。

其余定向测试是兼容性回归，不能替代这个守卫。`test_sqd_gap_repair.py` 的完整入口会调用读取 `.staging_b3` 的用例，因此必须落实工单已写明的“只跑不触及禁读夹具的用例”。

**d）0.7 的验收路径：可构造，但须分清 probe 与 repair。**

WR-b 的实际要求是两协议真实 ACTIVE 查询，加一次真实 `validate_coverage`。现有 [probe 发布测试](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_sqd_coverage_probe.py:205) 已提供对应构造与调用：

```python
exact.validate_coverage(
    case, generation / "coverage_map.json",
    case / "data/sqd_coverage/CURRENT.json", 100, 103)
```

也可复用该文件 `_w1_run` 与 `_w1_check` 的动态夹具。应在临时目录存续期间断言返回 `ok=True`，并分别确认最终 SHA 位于两个协议的真实 ACTIVE 查询结果。

这里有一个关键区别：[验证器 :712 起](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:712) **允许当前源码 SHA 直接通过**，可能短路历史查询。因此单独 `validate_coverage` 成功不能证明登记有效；工单同时要求真实 ACTIVE 查询，已补足这一点。

任务提到的 `validate_repair_bundle(deep=True)` 和 `resolve_formal_cache` 属于 repair 验收：

- **probe 发布夹具不能直接满足这两个入口。** 它缺少规范 base edge/meta、完整 repair generation 及其证据文件、repair CURRENT 指针和绑定关系。
- 真正的 W4 三类夹具在 [test_sqd_gap_repair.py:1512](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_sqd_gap_repair.py:1512)，通过 `build_batch3b_case` 和 repair 发布流程构造上述材料。WR-a 的四协议登记已在当前注册表中，无需替换历史查询。
- 允许读取的 WR-a 验收运行器也确实按该路径调用了两个真实入口。其已有 PASS 记录属于历史证据，本轮没有重新生成夹具或重跑入口。

因此，不能把“probe 文件没有 W4 repair 夹具”认定为 WR-b 的施工阻断；它是任务描述中的入口混用。

**e）模板残留与行号：有清理项，无实质阻断。**

[工单](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_WR-b.md:3) 开头明确规定本单两条、闭合 `:315`、登记后 `0 FAIL`，并补充 probe 验收要求；后文标明是通用模板。因此按开头的 WR-b 专项规则执行，范围和成功条件可确定。

建议同步清理以下残留，避免执行者只摘录正文：

- `:16` 的闭合 `:283` 已过期；repair 最新登记也已是 `15822564…`，`3f89aab1…` 应称历史 ACTIVE。
- `:28` 仍保留 WR-a 的“四条新增登记”和登记前 `2 FAIL` 说明，应就地改成 WR-b 两条及登记后 `0 FAIL / rc=0`。
- `:30` 正文应同步纳入开头补充的 `validate_coverage`，并将 WR-a 入口明确标为背景。
- producer 判据引用 `:712-716` 少覆盖了第二协议查询所在的 `:717`；引用到 `:722` 更完整。

以上属于已被开头专项说明覆盖的模板残留，不作为退回项。

本轮全程离线，未 commit，未新建或修改文件，未读取所列禁读路径。执行了只读注册表守卫及内存模拟；会生成临时文件的回归测试、发布夹具和正式入口验收未执行，未将其记作本轮 PASS。