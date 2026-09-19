# 工单R3复核r2：通过

v2 已完整吸收首轮意见，未发现新引入或未吸收的退回项。七条替换文本与首轮建议逐字一致。当前 HEAD 为 `5aadaab`；工单 §0.1 所列内容树相对 `0a53cbd` 无差异。

**1. D1：采纳，整行锚及代码依据成立。**

探针 parser 无 `--live-canary`；[sqd_gap_repair.py:1549](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1549) 将其注册在 `verify`，第 1508 行按 slot 调用 `reference-getBlock`。[solana_exact_validate.py:1390](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:1390) 取排序后的前 N 个 census slot，第 1404–1405 行比较 blockhash 和各交易首个签名组成的列表，没有比较覆盖位图。内存解析也确认：探针拒绝该参数，repair verify 接受。

第 714 行替换文本原文：

```text
- array_monotonic_unique 与 array_in_range 是生产时对原始响应数组的断言结果；任一为 false 则该段 unconfirmed，其 NO_HEADER 保持未确认，有效 verdict 为 INCONCLUSIVE。
```

**2. D2：采纳，只补类型正确。**

[sqd_gap_repair.py:911](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:911) 在没有匹配块时得到 `None`，第 945 行产生空 `sqd_blockhash`，第 1193 行选择 `confirmed_missing_block`，第 1202 行原样写入 census。抽取现行 `_routea_slot()` 内存执行，确认输出该结果及 `sqd_blockhash=null`。“同文件 :690”也已修正。

第 795 行替换文本原文：

```text
| `census[].sqd_blockhash` | string\|null | 是 |  |
```

**3. D3：采纳，过强说明已删除，第 667 行已补齐。**

[sqd_coverage_probe.py:675](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:675) 初始化空元数据与空 canary；第 694–696 行填入元数据，第 757–761 行填入已验证的 64 项 canary；后续失败由第 783–784 行返回当时的 `info`。第 1224 行接收对象，第 1333 行放入 coverage，第 1344 行实际写出产物。工单所述代码事实均存在。

使用现行函数及内存依赖替身复现：

- 初始校验失败：元数据为 null，canary 为 0 项。
- TTL 失败：保留元数据，canary 为 0 项。
- 区间不重叠回退：保留元数据及 64 项 canary。
- 成功复用：canary 为 64 项。

以下替换文本依次对应 **667、688、689、691、695 行**，各行独立替换：

```text
| `shared_map` | object\|null | 是 | asset_path,version,sha256,supersedes,generated_at,reused_ranges,unverified_ranges,recheck_stats,canary{slots,counts_sha256,verified_at} |
| `shared_map.version` | string\|null | 是 |  |
| `shared_map.sha256` | string (sha256 hex)\|null | 是 |  |
| `shared_map.generated_at` | string\|null | 是 |  |
| `shared_map.canary.slots` | array[integer] | 是 | 长度0或64；复用成功时为64 |
```

**4. 锚点与 UTF-8 字节汇总：全部通过。**

直接提取 v2 代码块，逐条执行 `grep -n -F` 和 `grep -n -F -x`，均恰命中一次且行号一致，无首尾空白。下表字节不含未变化的换行符。

| 条目 | 行号 | `-F`／`-Fx` 命中 | 原文 B | 替换 B | 净变化 B |
|---|---:|---:|---:|---:|---:|
| D1 | 714 | 1／1 | 254 | 201 | −53 |
| D2 | 795 | 1／1 | 46 | 52 | +6 |
| D3 总览 | 667 | 1／1 | 179 | 175 | −4 |
| D3 version | 688 | 1／1 | 42 | 48 | +6 |
| D3 sha256 | 689 | 1／1 | 54 | 60 | +6 |
| D3 generated_at | 691 | 1／1 | 47 | 53 | +6 |
| D3 canary.slots | 695 | 1／1 | 63 | 90 | +27 |
| **合计** | **7 行** | **全部唯一** | **685** | **679** | **−6** |

`\|` 按字面计为 **2 B**，`\|null` 为 **6 B**，没有反转义或按渲染结果计数。内存替换仅改变指定七行。

- `SKILL.md`：**8021 B**，不变。
- commands 四份文件：**8789 B**，不变。
- references 三组共 42 个文件：**930079 − 6 = 930073 B ≤ 930260 B**，余量 **187 B**。`attic.md` 仅用 stat 计入 6335 B，未读正文。

**5. 回归面、白名单及范围：通过。**

在禁区外 **49 份 Markdown 文档**检索参数、字段及同义表述，未发现其他同款旧约束遗漏。共享地图资产 README 的 64 项要求有 [validate_shared_map 的检查](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:828) 支持，保留正确。白名单覆盖全部修复及完成报告，无需扩展。

七处均为文本删除或修改；SKILL 与 commands 不变，references 净减，符合不增加 skill 上下文。没有修入范围外问题，也没有把措辞偏好列为漂移。

存在一处**可选等价减字**：第 695 行删去“时”，可再减 3 B。这仅是措辞压缩，不作为退回项；上述预算仍按 v2 原文计算。可选替换：

```text
| `shared_map.canary.slots` | array[integer] | 是 | 长度0或64；复用成功为64 |
```

执行披露：报告已打印至 stdout；全程离线，未修改或新建文件、未 commit，未读 `~/.codex/` 或 memories，其他禁区正文未读。一次 here-document 的隐式临时文件创建被只读沙箱拒绝，未生成文件，随后改用 `python -c`。内存验证使用依赖替身；未运行落盘集成测试或整套施工守卫，不声称守卫全绿。
