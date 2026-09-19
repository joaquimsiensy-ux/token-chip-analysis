# 工单R1复核：退回

原案 references **净增 346 B，超预算 92 B**；D4 尚未明确消除日内峰值宏的使用冲突；D2 锚含一个会导致精确匹配失败的前导空格。代码事实总体有据，但 D5 应定性为消歧，不能认定为已证实的行为漂移。

核查 HEAD：`6c8d9dadcc1cd30c793eba60a13901263151eeea`，VERSION：`9.0.1`。相对 `3942c23` 的指定内容差异为空，工作区前后干净。

**D1：采纳。**

[audit_release_gate.py:918](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:918) 确实将 expanded 金额分流，944–946 行按钱包分支核验 `wallet_self_held_raw`。在有效成员范围内，替换与代码一致。文档 161 行的逐地址闭合仍覆盖 strict 和 expanded，应保持不动。

替换文本：

```text
wallet_self_held_raw == Σ strict 成员的 position.amount_raw
```

**D2：事实成立；修正锚，压缩替换文本。**

[facts_gate.py:357](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:357) 至 371 行确实要求 `facts_inputs` 对象及有效的 `symbol`、`decimals`、`entity_labels`。

工单第 23 行的双反引号代码跨度只有前置空格，没有配对的尾部填充空格。保留该空格执行 `grep -n -F`，命中 **0**；去除后才在 203 行命中一次。应将锚明确写为下列原文，首字符就是反引号：

```text
`facts.json` 唯一拥有 entity_id/label/成员/current_raw/peak_raw；`state_source.json` 只承载它没有的分析时点、实体 type/status、逐址快照余额、vault 与 provenance。
```

建议替换文本：

```text
`facts.json` 由 `facts_gate.py build` 生成；人工声明置于 `state_source.facts_inputs`，其余状态字段见编译器 schema。
```

这避免复制已有 schema 字段清单，净减 56 B。

**D3：采纳修复方向；删除不准确的触发条件。**

[price_check.py:209](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/prices/price_check.py:209) 的 ALL_SKIP 确实退出 3；[stage2_closeout.py:294](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:294) 确实只接 PASS/WARN。

但 ALL_SKIP 指所选第二源全部抽样点 SKIP，并不要求证明“双源都无该币”。直接按退出结果表述更准确：

```text
exit 3（ALL_SKIP）须换源重跑，−2 收口只接 PASS/WARN
```

**D4：退回原替换，改成条件化边界。**

工单引用的 441、480、131–132 行均属实：override 写入最终 `peak_raw`，宏直接渲染该值。内存调用现行宏函数，`peak_raw=160`、总供应 `1000`，得到 `16.00%`。

“默认日末”也有常规生产路径依据：[entity_source_trace.py:529](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/entity_source_trace.py:529) 按日聚合，599–606 行取其峰值。问题在于原替换仍写“日内事件占比不得套用宏”，接着 216 行要求手写，却没有排除已经由 override 绑定的日内峰值。

若本意是禁止拿峰值宏代替其他事件值，应直接写清。替换 215 行原锚为：

```text
`{{e.peak_share}}` 代表 facts 绑定的峰值，粒度按来源标明；未绑定该峰值的日内事件占比，
```

216 行可保持原样。这样既允许正确引用绑定峰值，也保留其他事件值的披露纪律，不暗示代码会验证“粒度”字段。

**D5：仅作为消歧采纳，不计硬漂移。**

`price_file_sha256` 必填属实，但原句“均可选”可以就近修饰分号后的两个 facts 字段。R1a 将其列为待确认，比 R1b 直接认定矛盾更严谨。

按“删除优先”，将原锚替换为：

```text
2）
```

同版本 113 行已经说明流通量输入可选，无须重复。

**D6：依据属实；可用更短文本，不必罗列例外。**

[figures_from_facts.py:359](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py:359) 的分支及内存复现一致：

- 政策拒绝、输入缺失、series 顶层非数组：不调用收据写入。
- 两输入文件存在但 JSON 解析失败：尝试写 FAIL 收据。
- 终值对账 PASS/FAIL，包括 exploration：调用收据写入。

因此不能扩大成“格式错误一律不写收据”。原案列出的具体例外没有错，但可压缩为：

```text
**终值对账结果（PASS/FAIL、formal/exploration）均写 `figure2_check_receipt.json` 收据**
```

该替换净增 **0 B**。

**D7：依据属实；建议直接写换算式。**

[peaks_daily.py:89](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/peaks_daily.py:89) 默认值确为 `0.01`；97 行乘总供应量；121 行筛选的是**累计流入**。工单的操作修复成立。

建议删去重复的历史区间说明和容易被照抄的示例值：

```text
**须显式传 `--pct`＝上述最低枚数/总供应量，勿沿用默认 0.01（1%）**
```

`0.001` 只有在总供应口径给出较低枚数时才适用。未读取工单点名的其他 maintenance 台账；可读的 `CHANGELOG.md:149` 已旁证 P2 登记。

**D8：采纳。**

`camp_series_provenance.py:293` 保留日期序列；`state_from_facts.py:141` 原样输出；[172–177 行](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/state_from_facts.py:172) 确实比较手填序列与转换结果。

内存复现中，501 点通过转换、数值校验和状态编译；手填抽成 500 点后，被实际相等性检查拒绝。

替换文本：

```text
`camp_share_series`（重绘图 1 基线）
```

**D9：采纳。**

[split-run.md:168](/Users/uravvv/.claude/skills/token-chip-analysis/references/split-run.md:168) 的 §3b.3 只有一段正文，172 行即进入下一节，确无第⑤条。

替换文本：

```text
按 §3b.3 自查申报
```

**预算核算。**

逐文件 `stat -f %z` 求和结果：

- references 三组：`825091 + 74491 + 30494 = 930076 B`；当前无 `*.bak_*`。`attic.md` 仅统计大小，未读正文。
- 原方案：`930076 + 346 = 930422 B`，超过 `930330 B` **92 B**。“约 +140 B”不成立。
- commands-staging：`8798 − 9 = 8789 B`，成立。
- SKILL.md：`8021 B`，不变。

上述建议文本已逐项在内存中替换核算：references **930073 B**，净减 **3 B**；commands-staging **8789 B**；CHANGELOG 净减 **12 B**。无需增加运行时上下文。

**回归面、白名单与范围。**

已对允许范围内的 SKILL、现役 references、四份 commands、CHANGELOG 和脚本 README 做同概念检索：

- 钱包旧公式、价格人工回退、第⑤条未发现其他现役同款断言。
- `economic-control-accounting.md:26` 的泛称受同文 40、93 行严格成员及扩展边界限定，不据此追加措辞修改。
- `report-template.md:210` 的“不重复”可以指合并职责，不足以另判一条排他性字段漂移。
- `monitoring-package.md:103` 的 ≤500 点属于独立监控包，保留正确；历史案例中的日末峰值、1% 门槛也不应统一清洗。
- 现有文件白名单够用。无需修改代码、门禁、结构或 manifests；新增维护完成报告也不属于运行时上下文。

本轮仅做静态核查和现行函数的内存复现，I/O 与外部来源绑定使用替身；未执行会读取禁区或创建夹具的完整守卫，因此不宣称 §1.2 已全绿。全程离线，未读 `~/.codex/`、memories 或禁读正文，未修改、新建文件或 commit；启动器及 here-document 的临时文件创建尝试均被只读沙箱拒绝。

| 项目 | 原锚 `grep -n -F` | 原方案净增 B | 建议方案净增 B | 意见 |
|---|---|---:|---:|---|
| D1 | 162 行，1 处 | +17 | +17 | 采纳 |
| D2 | 含前导空格 0 处；去除后 203 行 1 处 | +49 | −56 | 修正锚并压缩 |
| D3 | 278 行，1 处 | +6 | −13 | 按 ALL_SKIP 结果表述 |
| D4 | 215 行，1 处 | +100 | +37 | 原替换退回，明确条件 |
| D5 | 117 行，1 处 | +6 | −12 | 仅作消歧 |
| D6 | 222 行，1 处 | +88 | 0 | 事实采纳，压缩 |
| D7 | 136 行，1 处 | +99 | +25 | 事实采纳，压缩 |
| D8 | 200 行，1 处 | −13 | −13 | 采纳 |
| D9 | 16 行，1 处 | −9 | −9 | 采纳 |
| **references 小计** | D1/D2/D3/D4/D6/D7/D8 | **+346** | **−3** | **原案超限 92 B；建议方案满足预算** |
