# 登记单WR-a复核r1：退回

**退回原因：0.4 漏列直接验证本单登记结果的 `test_producer_registry_current.py`，且未规定 WR-a 阶段的预期失败范围。** 填实值、追加位置和保留旧 ACTIVE 条目的要求均正确；0.7 可利用现有自包含夹具构造，不需要等待 WR-b。

**1. 必改项：0.4 加入登记守卫及逐项判据。**

本轮只读执行：

```text
python3 -I -S -B scripts/tests/test_producer_registry_current.py
producer registry: 6 FAIL
exit 1
```

六项失败恰为 repair 四协议、probe 两协议；全部 34 条既有登记的 Git 哈希复现检查通过。

[守卫源码](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_producer_registry_current.py:44)直接检查当前脚本哈希是否进入对应协议的真实 ACTIVE 集合，并逐条核验登记的 Git 对象。0.4 现列测试不能替代这项检查；0.7 的正式 bundle 入口也只直接查询 repair 的 `sqd-solana-cache/v4`，不能证明另外三个协议均已登记。

应在 0.4 明确：

- 追加后，repair 四协议当前哈希检查全部为 `ok`，四条新增登记的 Git 复现检查全部通过。
- WR-b 尚未执行时，只允许 probe 的 coverage/v1、coverage-pointer/v1 两项 FAIL；在当前基线上预期尾行为 `producer registry: 2 FAIL`、退出码为 1。
- 报告列出剩余失败项，不得只贴尾行或把整个守卫记作 PASS；任何其他失败均须处理。

按现有查询逻辑，正确追加四条即可消除 repair 四项失败。这是源码推导，**本轮未追加登记，也未把追加后结果表述为实测**。

**2. a）填实值：通过。**

独立执行 Git 对象及工作树 SHA-256 计算，两者均为：

```text
15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33
```

与工单填值及 `W4_done.md` 记录一致。

- 当前 HEAD：`fcb374568b3a82edab0ab4bcfd73814aadfe46fb`。
- `<CODE_COMMIT>`：`59f88b84c9ab9eeb95c92a15e342d8cbe09925db`。
- `git merge-base --is-ancestor <CODE_COMMIT> HEAD` 返回 0。
- `git log -1 -- scripts/solana/sqd_gap_repair.py` 返回该 `<CODE_COMMIT>`，确为当前历史中脚本最后一次改动。
- 检查前后 `git status --short` 均为空。

**3. b）条目结构与旧 ACTIVE 状态：通过。**

[注册表](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/producer_history.py:235)现有 34 条记录均使用 `script/sha256/commit/protocol/status/reason` 六字段，元组闭合确在 **:283**。`3f89aab1…`、commit `7846184f…` 的四条 repair 记录位于 :235–266，全部 ACTIVE；没有 shared-map 登记。

0.3 同构追加可行。写入的协议值须沿用完整名称：

```text
sqd-solana-cache/v4
sqd-solana-repair-bundle/v1
sqd-solana-coverage-resolution/v1
sqd-solana-repair-pointer/v1
```

**不需要把旧条目改成非 ACTIVE。** 文件头 :3–6 要求哈希可由 Git 历史复现、禁止录入无法由 Git 证明的脏树哈希，没有规定每协议只能保留一个 ACTIVE。[查询实现](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/producer_history.py:286)返回所有匹配 ACTIVE 哈希，并实行跨协议的哈希级 REVOKED 优先。旧版继续 ACTIVE 与历史产物验证、前代认领机制相容；“保留全部既有条目不改”不冲突。

**4. d）0.7 正式入口：可构造，但现有 W4 测试不会直接完成它。**

[W4 三类证据用例](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_sqd_gap_repair.py:1512)已经具备所需数据：自包含 coverage/base、缺失交易、旧／新／混合 evidence、发布后的 generation 和 CURRENT。`:1576` 只调用 `validate_repair_bundle_deep`；测试退出后临时目录被清理，因此直接运行该测试并取得 PASS，不等于完成 0.7。

缺的是**额外的正式入口调用及断言**，不是新的链上数据或生产功能。登记后应在夹具临时目录仍存在时，以真实模块执行：

```python
bundle = identity.validate_repair_bundle(
    gen / "bundle.json",
    deep=True,
    case_root=case,
    current_base={"edge_sha256": repair.sha256_file(base_edge)},
)
edge, meta, kind, gid, binding = identity.resolve_formal_cache(MINT, case)
assert kind == "repaired"
assert gid == bundle["gid"]
assert binding["cache_kind"] == "repaired"
```

其中 `base_edge` 须为本案规范 base 文件；同时核验返回 edge/meta 指向 CURRENT 所选代。可以由一次性验收运行器复用现有构造器完成，不必修改生产文件或现有测试。

两个入口经过[真实登记检查](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_cache_identity.py:143)。当前未登记时会拒绝新 repair 哈希；追加后该门槛可满足。probe 两协议尚未登记不会阻塞即时生成的夹具，因为 [coverage 校验](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:710)接受当前 probe 文件哈希。

建议 0.7 补明上述调用位置、参数和断言；**它不存在必须另补数据才能执行的阻塞**。本轮未生成夹具或运行这两个入口，结论属于源码可构造性核查。

**5. e）内部一致性与锚：未发现其他阻断项。**

- 填实单嵌入的模板与 `workorder_WR.md` 全文一致。
- `producer_history.py:3–6`、`:283`、`sqd_cache_identity.py:143–147` 均准确。
- `test_sqd_gap_repair.py:322–330` 确实覆盖历史查询替换代码，引用有效。
- “施工者不 commit”与“调度方登记 commit 后验收”分工一致；完成报告允许缺项写待验收，没有强迫施工者报告尚不存在的登记 commit。
- `<REASON>` 只写“α”描述不完整：W4 源码及工单明确覆盖 α/β 共用修复流程。建议改为“9.2.0 α/β 候选修复状态探针并入 census 请求（W4）”；不影响哈希或登记有效性。
- 0.5 排在 0.8 后属于编号整理问题，不影响执行。

本轮保持离线，未新建或修改文件、未 commit；未读取指定禁区。需写入临时夹具的测试未运行，历史完成报告中的 PASS 未当作本轮实测结果。