# 工单R3复核：退回

三条原始发现成立。v1 有三处需要修正：**D1 不是整行锚；D3 把回退初值推广成所有回退结果；遗漏第 667 行的固定 64 项约束。** 原方案字节预算成立。

当前 HEAD 为 `ef52a943d524d2925955f5bb11a3f05761f800a0`，工作区状态为空。以下文档行号均指 [scan-schemas.md](/Users/uravvv/.claude/skills/token-chip-analysis/references/scan-schemas.md)。

1. **D1：采纳删除，修正整行锚。**

工单代码块执行 `grep -n -F` 恰命中第 714 行一次，但只是该行末尾片段；增加 `-x` 后命中为 0。其余五个原锚均为整行、唯一且行号吻合。

代码依据成立：[sqd_gap_repair.py:1549](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1549) 将参数注册到 `verify`，第 1508 行调用 `reference-getBlock`；[solana_exact_validate.py:1390](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:1390) 取排序后前 N 个 census slot，第 1404–1405 行比较 blockhash 和各交易首个签名组成的列表，没有比较覆盖位图。现行探针 parser 无该参数；抽取原 parser 的内存验证也确认探针拒绝、repair verify 接受。

第 714 行应使用完整锚：

```text
- array_monotonic_unique 与 array_in_range 是生产时对原始响应数组的断言结果；任一为 false 则该段 unconfirmed，其 NO_HEADER 保持未确认，有效 verdict 为 INCONCLUSIVE；--live-canary 重拉若干段与位图切片对表。
```

替换文本原文：

```text
- array_monotonic_unique 与 array_in_range 是生产时对原始响应数组的断言结果；任一为 false 则该段 unconfirmed，其 NO_HEADER 保持未确认，有效 verdict 为 INCONCLUSIVE。
```

2. **D2：采纳类型补正；原说明真实，可缩短。**

[sqd_gap_repair.py:911](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:911) 在没有匹配块时得到 `None`，第 945 行据此生成空 hash；第 1193 行选择 `confirmed_missing_block`，第 1202 行原样写入。抽取 `_routea_slot()` 的内存调用确认输出 `result=confirmed_missing_block`、`sqd_blockhash=null`。

原替换没有引入不实断言。第 795 行只补类型即可，替换文本原文：

```text
| `census[].sqd_blockhash` | string\|null | 是 |  |
```

另，依据中的“同表 :690”应改为“同文件 :690”：第 690 行属于 §14.1，第 795 行属于 §14.3。

3. **D3：采纳可空类型，退回“一律为空”的说明，并补第 667 行。**

工单引用的初值、异常返回和产物写入语句均真实存在：[sqd_coverage_probe.py:675](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:675) 初始化空值，第 783–784 行返回 `info`，第 1333、1344 行将其写入产物。遗漏的是中途赋值：

- 第 694–696 行先填入元数据，再执行 TTL、身份及后续校验；失败时不会清空已填值。
- 第 757–761 行先写入 64 项 canary，再检查区间重叠；第 764 行的 `map-does-not-overlap-case` 回退会保留这 64 项。

对未改动的 `_load_known_map()` 使用内存依赖替身，分别复现：

| 回退位置 | 元数据 | canary 项数 |
|---|---|---:|
| 初始校验失败 | null | 0 |
| TTL 失败 | 非空 | 0 |
| canary 后区间不重叠 | 非空 | 64 |

这是分支复现，未执行落盘集成测试。因此，“回退时……为 null”和“回退时为空”不能作为通用约束。

第 667 行还保留 `canary{slots[64],...}`；工单明确不动它，会留下同款矛盾。补充完整锚：

```text
| `shared_map` | object\|null | 是 | asset_path,version,sha256,supersedes,generated_at,reused_ranges,unverified_ranges,recheck_stats,canary{slots[64],counts_sha256,verified_at} |
```

以下五条替换文本依次对应 **667、688、689、691、695 行**，各自独立替换：

```text
| `shared_map` | object\|null | 是 | asset_path,version,sha256,supersedes,generated_at,reused_ranges,unverified_ranges,recheck_stats,canary{slots,counts_sha256,verified_at} |
| `shared_map.version` | string\|null | 是 |  |
| `shared_map.sha256` | string (sha256 hex)\|null | 是 |  |
| `shared_map.generated_at` | string\|null | 是 |  |
| `shared_map.canary.slots` | array[integer] | 是 | 长度0或64；复用成功时为64 |
```

工单 D3 的依据说明建议替换为：

```text
依据 scripts/solana/sqd_coverage_probe.py:675-680 初始化空元数据与空 canary；:694-696 填入元数据，:757-761 填入已验证 canary，后续失败不会清空这些值；:783-784 返回当时的 info，:1333、:1344 写入产物。因此回退允许元数据为 null、canary 为空，也可能保留已填值；同步删除字段总览 :667 的固定长度重复约束。
```

4. **UTF-8 字节与锚点汇总。**

按代码块字面计算，没有反转义或 Markdown 渲染。各 `\|` 实际包含一个反斜杠和一个竖线，占 2 B；增加 `\|null` 为 6 B。

| 条目／行号 | grep 命中／整行命中 | v1 旧→新字节 | v1 净变化 | 建议净变化 | 意见 |
|---|---:|---:|---:|---:|---|
| D1／714 | 1／0 | 87→34 | −53 | −53 | 修正整行锚，采纳删除 |
| D2／795 | 1／1 | 46→113 | +67 | +6 | 原文正确，可缩短 |
| D3／688 | 1／1 | 42→138 | +96 | +6 | 删除过强说明 |
| D3／689 | 1／1 | 54→60 | +6 | +6 | 采纳 |
| D3／691 | 1／1 | 47→53 | +6 | +6 | 采纳 |
| D3／695 | 1／1 | 63→97 | +34 | +27 | 修正回退条件 |
| 补漏／667 | 1／1（补锚） | — | 0 | −4 | 删除重复固定长度 |
| **合计** | | | **+156** | **−6** | **v1 退回** |

D1 表内 87→34 B 是工单片段；完整行是 254→201 B，差额仍为 −53 B。建议方案的七个完整原锚均已用 `grep -n -F -x` 核验唯一及行号。

- `SKILL.md`：**8021 B**；commands 合计：**8789 B**，与工单一致。
- references 三组共 42 个文件，基线 **930079 B**；`attic.md` 仅 stat 计入 6335 B，未读内容。
- v1：930079 + 156 = **930235 B ≤ 930260 B**，余量 **25 B**。
- 上述建议：930079 − 6 = **930073 B**，余量 **187 B**；已完成逐字内存替换校验。

因此，“无可删冗余，净增不可避免”不成立。采用建议方案时，§1.1 替换为：

```text
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 ≤ 930260（基线 930079；七处替换按 UTF-8 字面模拟净减 6 B → 930073，实测数写入报告）。
```

5. **回归面、白名单与范围。**

检索了禁区外 **49 份 Markdown 文档**。确认遗漏的是同文件第 667 行；未发现其他 `live-canary`、`sqd_blockhash` 或案级 `shared_map` 子字段的同款旧约束。共享资产 README 的 64 项要求针对共享地图资产，现行 `validate_shared_map()` 第 828–830 行确有对应要求，不应随案级回退对象一起放宽。

**文件白名单足够，需要补充同文件锚清单。** 三条发现均涉及实际行为或字段约束，不属于措辞偏好。建议方案只改文本、保留删除优先、不扩大问题范围；SKILL 与 commands 不变，references 净减，无需增加 skill 上下文。

执行披露：报告已打印到 stdout。未联网、未创建或修改文件、未 commit；未读 `~/.codex/` 或 memories，其他禁区正文未读。首次系统 git 的工具链缓存写入被沙箱拒绝，未生成文件，随后改用原生 git；工作区状态前后为空。未运行会落盘或遍历禁区的整套守卫，不声称守卫全绿。
