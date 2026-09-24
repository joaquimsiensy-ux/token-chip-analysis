# W1盲审r3：PASS

未发现本次审查范围内的阻断问题。**r2 两类反例均已在 HEAD 关闭**；W1F 保留了首块事实检查，未发现补值引入的回归。

审查范围：`6b36dcdd043d0b2b51c03de9ab0bb555b25f436a..cfe2f41132bd3f162f3d356f359c9eba72a500d3`，限定指定文件及工单。

**r2 阻断项的独立复核**

使用自行构造的内存文件夹具调用完整 `validate_coverage()`；逐次重算响应、ledger、coverage、probe_id 和 CURRENT 引用。仅替换文件读取接口，未替换校验逻辑。

| 输入 | W1F_BASE | HEAD |
|---|---|---|
| 正确值 2 的证明＋完整空响应 | 错误接受，`reasons=[]` | 拒收 |
| 正确值 2 的证明＋仅返回相邻 slot 的非空完整响应 | 错误接受，`reasons=[]` | 拒收 |

HEAD 两例均包含完整理由：

```text
inherited refuted recheck results conflict
```

附加回归也符合预期：

- 请求 `[500,501]`、仅返回 501：正确 `returned_from=501` 解码为 `{500:1,501:2}`。
- 同一响应伪报 `returned_from=500`：以 `inherited refuted recheck complete response facts invalid` 拒收。
- 两个跨案请求仅在案外 slot 发生值冲突：仍以完整冲突理由拒收。
- 单条正确证明、两条一致证明、跨案且 `counts_coverage=False` 的完整证明、部分继承及正常 canary 记录：均通过。
- 对四个 slot 的 81 种计数组合，将专用解码器与探针解码结果比较：完整响应一致，短尾响应拒收。

[修复位置](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:532)确实先完成事实检查，再补值 1；非目标早退分支和冲突合并逻辑未变。

**a–h 审查结果**

| 项目 | 结果与证据 |
|---|---|
| a：白名单、不改清单、schema | 差异仅指定的 8 个文件；repair 生产文件仅改指定函数。未修改 manifest、producer_history、版本文件或资产二进制。探针未新增 schema 字符串比较。`git diff --check`、独立运行 `invariant_scan.py` 均通过。 |
| b：无继承兼容 | 48 组分类调用与基线完整返回值全等，summary 无新增键；旧 producer 哈希的无继承内存产物通过。仓库旧资产 `20260827.json` 通过新校验器，153,667 个候选、空 refuted。探针空 refuted、回退及全部证据过期路径均不写继承键。 |
| c：六条件与时效 | 静态确认六条件齐全，并独立执行正常继承、部分案范围、未验证段排除、失败后重试、canary 失败、计数 mismatch、过期、空 refuted、不同证据项分别过期九组探针测试，结果符合工单。 |
| d：独立拒收 | 下列不一致 coverage 输入全部拒收，均到达继承检查并产生 `inherited refuted` 理由；详见下方。 |
| e：helper 与导出 | helper 正常输入通过，正确区分 own refuted 与 β confirmed；24 类来源绑定或 census 不一致输入拒收。静态确认 `--no-repair` 仍调用相同 helper 并剔除 confirmed。链式转换清空修复字段、更新当前来源身份、保留原始时间，`origin_asset_sha256` 首次填入后保留，最终重新编号并计数。 |
| f：β 兼容 | 独立执行 16 组状态输入：β 仅接受有块头且严格整数零 nonce，α 保留拒绝；`_repair_state_matches` 同步。 |
| g：副本发布 | 静态确认副本先于 probe_id 落盘，加入 `_same_generation/_clear_pending`，无 pointer.inputs 新键，原 fsync 顺序保留。独立内存比较确认：相同副本通过，缺失或不同副本产生 generation 差异。 |
| h：测试及报告 | W1 六组新增 coverage 测试、W1F 两组测试及独立 β 测试均登记 main。源码覆盖工单 (a)–(f) 的主要要求，W1F 补齐两类冲突与首块检查。两份完成报告的改动职责、行数及限制与各自 diff 一致。F-03 旧夹具修改已明确披露，原回归场景保留。 |

独立 invariant 输出：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118,
transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0
```

**§2.4 已独立执行的拒收检查**

以下均通过完整 `validate_coverage()` 验证，外层引用同步更新：

- 副本三方摘要不一致、缺副本、实物大小或摘要不符。
- coverage evidence 与副本不全等；错误缩减部分继承的 evidence 计数；副本完整映射计数错误。
- origin 为负数、bool、越界或合法索引错绑；本案 slot 不属于副本 refuted 成员。
- 空声明、非法或重复 slot、bool count；本案 counts 改为 3，并同步重算复用摘要。
- 自报 reused 区间与账本不一致、移除 map-reuse、复用摘要错误、继承点落入 unverified。
- 缺重查、失败、短返回、mismatch、错误 HTTP 状态、查询或响应绑定错误、重复块顺序；响应重新计算摘要后实际值仍不为 2。
- 非空继承与 fallback 并存。
- 仅修改 coverage 自报原始时间、副本原始证据过期、无时区验证时间。

时效边界另行确认：**原始时间＋30 天通过，超过 1 秒拒收**。部分继承保留来源完整 evidence、其 `refuted_count` 大于本案继承数量时通过。

**未独立执行的范围**

本次未运行会创建临时文件的完整测试入口，也未执行真实发布/fsync、真实 resume、完整导出链及 base/repaired 端到端流程；这些部分进行了源码核对，验收文件中的运行结果仅作为调度方证据。

未运行 `run_all.py`、`docs_lint.py`、`changelog_lint.py` 或任何触及 `.staging_b3` 的用例；未重新核验旧发布案实物。上述未运行项目不冒充本次独立 PASS。

全程离线、未新建或修改文件、未 commit；工作区前后均干净。未读取 `~/.codex/`、memories 或其他指定禁读内容；maintenance 仅读取获准目录中的指定工单、报告及验收材料。