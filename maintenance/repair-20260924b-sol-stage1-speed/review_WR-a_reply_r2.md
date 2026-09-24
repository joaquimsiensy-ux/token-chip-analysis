# 登记单WR-a复核r2：通过

**未发现阻断登记执行或正式验收构造的问题。** r1 必改项已吸收；四条同构追加可行，旧 ACTIVE 条目应保留。存在一处非阻断的模板措辞残留，详见第 5 点。

本结论针对登记单的正确性与可执行性；本轮未施工，也未把登记后的预期结果当作实测。

**1. r1 意见逐条核对**

| r1 意见 | v2 吸收情况 |
|---|---|
| 0.4 必跑登记守卫 | 已明确加入 `test_producer_registry_current.py` |
| repair 四协议当前哈希与新增条目的 Git 复现须通过 | 已逐项规定 |
| WR-a 阶段只允许 probe 两项失败 | 已列明协议、`2 FAIL`、退出码 1，并要求报告失败明细；其他失败停工 |
| REASON 覆盖 α/β | 顶部填实值已改为“α/β 候选修复状态探针并入 census 请求” |
| 0.7 补正式入口、参数、断言和调用时机 | 已规定登记 commit 后、临时目录存续期间调用两个真实入口，覆盖全旧／全新／混合三类，并检查 CURRENT 所选代 |

依据：[工单填实值](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_WR-a.md:3)、[0.4—0.7](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_WR-a.md:26)。

**2. a）提交与哈希：通过**

独立复算 Git 对象和工作树文件，均得到：

```text
15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33
```

与工单 `<SHA256>`、`W4_done.md` 记录一致。

- 当前 HEAD：`fe9a00643b54e89fa88bb4e0f49fa083c4211baa`。
- `<CODE_COMMIT>`：`59f88b84c9ab9eeb95c92a15e342d8cbe09925db`。
- `git merge-base --is-ancestor <CODE_COMMIT> HEAD` 返回 **0**。
- `git log -1 -- scripts/solana/sqd_gap_repair.py` 返回该 `<CODE_COMMIT>`，确为当前历史中脚本最后一次改动。
- 检查前后工作树状态均为空。

**3. b）追加结构与旧 ACTIVE 状态：通过**

[注册表](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/producer_history.py:235)现有 34 条记录使用 `script/sha256/commit/protocol/status/reason` 六字段；元组闭合 `)` 确在 **:283**。`3f89aab1…`、commit `7846184f…` 对应的四条 repair 登记位于 :235–266，全部 ACTIVE；没有 shared-map 条目。

0.3 可按现有字典结构追加四条，协议值应沿用完整名称：

```text
sqd-solana-cache/v4
sqd-solana-repair-bundle/v1
sqd-solana-coverage-resolution/v1
sqd-solana-repair-pointer/v1
```

**不需要把旧条目改为非 ACTIVE。** 文件头 :3–6 约束的是 Git 可复现性，没有规定每协议只能有一个 ACTIVE。[查询函数](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/producer_history.py:286)返回全部匹配的 ACTIVE 哈希，并执行哈希级 REVOKED 优先规则。“保留全部既有条目不改”与登记纪律一致，也保留了旧产物及前代认领的验证能力。

**4. c）0.4 登记守卫：通过；d）0.7 正式入口：可构造**

本轮只读执行：

```text
python3 -I -S -B scripts/tests/test_producer_registry_current.py
producer registry: 6 FAIL
退出码：1
```

六项失败恰为 repair 四协议与 probe 两协议；**34 条既有登记的 Git 哈希复现检查全部通过**。

[守卫源码](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_producer_registry_current.py:44)直接检查当前哈希是否进入对应协议 ACTIVE 集合。因此正确追加四条后，repair 四项应转为 `ok`，留下 probe 两项失败，符合 v2 的明确判据。这是源码推导，未实际追加。其他定向测试和正式入口均不能替代该守卫对四协议的完整检查；v2 已正确将其列为必跑项。

0.7 所需数据已齐备：

- [自包含构造器](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_sqd_gap_repair.py:171)生成规范 base、coverage 及 coverage CURRENT。
- [W4 三类证据用例](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_sqd_gap_repair.py:1512)构造全旧／全新／混合 evidence，包含 confirmed 缺失交易，能够进入 generation 发布路径并取得 repair CURRENT。
- 全旧／混合用例依赖的前代 `25f04ff1…` 已真实登记，无须替换历史查询。
- [coverage 校验](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:710)接受当前 probe 源码哈希，因此即时构造的夹具不必等待 WR-b。
- [正式 bundle 入口](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_cache_identity.py:124)及 [resolver](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_cache_identity.py:247)要求的登记、base 绑定、merged 文件和 CURRENT 绑定，均有对应构造与发布路径。

**登记后，按 0.7 的一次性运行器方案可以构造验收，不缺新的链上数据或生产功能。** 但直接运行现有 W4 测试仍不等于完成验收：`:1576` 只调用深验 helper，且退出后清理临时目录。运行器仍须在目录存续期间取得 `base_edge`、保存正式校验返回的 `bundle`，调用 resolver 并执行工单所列断言。v2 已明确安排这部分工作。

本轮未创建夹具、未执行这两个正式入口；上述为源码可构造性结论。

**5. e）内部一致性与锚：无阻断项，一处文字残留**

- `producer_history.py:3–6`、`:283`、`sqd_cache_identity.py:143–147` 均准确。
- `test_sqd_gap_repair.py:322–330` 确实覆盖历史查询替换代码，引用有效。
- “施工者不 commit”与“调度方登记 commit 后验收”职责一致；报告允许缺项写待验收。
- **非阻断建议：**[工单 :20](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_WR-a.md:20)模板仍写“α 修复状态探针”，与顶部 α/β 填实值未完全统一。`:7` 已明确占位符按顶部填实值理解，故实际写入值无歧义；建议同步更新模板文字。
- 0.5 排在 0.8 后仅属编号顺序问题。

全程离线、只读，未新建或修改文件、未 commit；未读取 memories、`~/.codex/` 或其他指定禁区。会生成临时文件的测试未运行，历史报告的 PASS 未计为本轮实测。